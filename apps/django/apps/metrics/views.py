"""指标库 API 视图。

端点（挂在 /api/v1/metrics/ 下）：
    /atomic-metrics/      原子指标 CRUD（删除带引用检查）
    /derived-metrics/     派生指标 CRUD（删除带引用检查）
    /templates/           指标模板 CRUD
    /rules/execute/       POST 一次性执行（不落库），返回分步结果
    /operators/           GET 运算符目录（复用 rule_engine.UnifiedOperator）
    /derived-funcs/       GET 派生计算函数目录（供前端下拉，零代码新增指标的关键）
    /sample-data/         GET 示例候选人数据（规则配置页测试数据区）

非功能约束：任何异常都不许 500 —— 由项目全局 DRF exception_handler + 本层显式
try/except 双重保障，执行类错误降级为该步 FAIL 并在 error 字段给出人话提示。
"""
from typing import List

from django.core.cache import cache
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsSetPagination
from apps.rule_engine.models import UnifiedOperator

from .models import AtomicMetric, DerivedMetric, MetricRule, MetricTemplate
from .serializers import (
    AtomicMetricSerializer,
    DerivedMetricSerializer,
    MetricRuleSerializer,
    MetricTemplateSerializer,
    RuleExecuteSerializer,
)
from .services.candidate_snapshot import build_candidate_snapshot, list_candidate_paths
from .services.derived_registry import list_funcs
from .services.metric_engine import MetricEngine
from .services.rule_trigger import (
    count_candidates,
    default_candidate_ids,
    evaluate_scene,
    filter_candidates_by_scene,
)

# MVP 示例候选人数据（PRD F-08 要求测试数据区；真实接入时替换为业务快照）
SAMPLE_CANDIDATE = {
    'candidate': {
        'name': '张三',
        'age': 32,
        'birthday': '1994-03-12',
        'education': [
            {'degree': '本科', 'school': '某大学'},
            {'degree': '硕士', 'school': '某大学'},
        ],
        'workExperience': [
            {'company': 'A公司', 'start_date': '2018-07-01', 'end_date': '2021-06-30'},
            {'company': 'B公司', 'start_date': '2022-01-01', 'end_date': None},
        ],
    }
}


class _RefCheckMixin:
    """删除前检查是否被模板引用 —— 返回 400 JSON，绝不抛 ProtectedError 造成 500。"""

    ref_related = 'templates'

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        count = getattr(obj, self.ref_related).count()
        if count:
            return Response(
                {'error': f'该指标被 {count} 个模板引用，无法删除'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AtomicMetricViewSet(_RefCheckMixin, viewsets.ModelViewSet):
    queryset = AtomicMetric.objects.all().order_by('name')
    serializer_class = AtomicMetricSerializer
    pagination_class = StandardResultsSetPagination


class DerivedMetricViewSet(_RefCheckMixin, viewsets.ModelViewSet):
    queryset = DerivedMetric.objects.all().order_by('name')
    serializer_class = DerivedMetricSerializer
    pagination_class = StandardResultsSetPagination


class MetricTemplateViewSet(viewsets.ModelViewSet):
    queryset = MetricTemplate.objects.all().select_related(
        'atomic_metric', 'derived_metric'
    ).order_by('name')
    serializer_class = MetricTemplateSerializer
    pagination_class = StandardResultsSetPagination


class EvaluateSceneView(APIView):
    """POST /api/v1/metrics/rules/evaluate-scene/ —— 业务触发点统一入口。

    body: {scene: TALENT_POOL|FILTER|SCORING, candidateId}
    返回是否阻断 + 每条规则的明细，供入池/筛选/评分业务调用。
    """

    def post(self, request):
        payload = request.data or {}
        scene = payload.get('scene')
        candidate_id = payload.get('candidateId') or payload.get('candidate_id')
        if not scene or not candidate_id:
            return Response(
                {'error': '缺少 scene 或 candidateId'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(evaluate_scene(scene, candidate_id), status=status.HTTP_200_OK)


# 未提供 candidateIds 时默认扫描的候选人数上限（规则含派生指标需逐条计算，必须限流）。
# 超出时同步端点返回 truncated=true，前端应改走异步任务（filter-async）拿全量结果。
FILTER_MAX_CANDIDATES = 200
# 同步筛选结果缓存 TTL（秒）—— 避免重复计算
FILTER_CACHE_TTL = 300


def _cache_key(scene: str, candidate_ids: List[str]) -> str:
    """缓存键：场景 + 候选集合指纹。"""
    import hashlib

    digest = hashlib.md5(','.join(candidate_ids).encode('utf-8')).hexdigest()
    return f'metrics:filter:{scene}:{digest}'


class FilterAsyncView(APIView):
    """POST /api/v1/metrics/rules/filter-async/ —— 全量异步筛选。

    候选人规模超过 FILTER_MAX_CANDIDATES 时用（同步端点会截断）。
    返回 taskId，前端轮询 filter-status 拿进度与结果。
    """

    def post(self, request):
        import uuid

        payload = request.data or {}
        scene = payload.get('scene')
        if not scene:
            return Response({'error': '缺少 scene'}, status=status.HTTP_400_BAD_REQUEST)

        raw_ids = payload.get('candidateIds') or payload.get('candidate_ids')
        candidate_ids = [str(i) for i in raw_ids] if isinstance(raw_ids, list) else None

        task_id = uuid.uuid4().hex
        try:
            # 函数内导入，避免 views <-> tasks 循环依赖
            from .tasks import filter_by_scene_task, write_progress

            write_progress(task_id, {'status': 'pending', 'progress': 0, 'total': 0})
            filter_by_scene_task.delay(task_id, scene, candidate_ids)
        except Exception as exc:
            # 无 Celery worker / broker 时明确报错，不静默假装成功
            return Response(
                {'error': f'异步任务启动失败（请确认 Celery worker 已启动）: {exc}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({'taskId': task_id}, status=status.HTTP_200_OK)


class FilterStatusView(APIView):
    """GET /api/v1/metrics/rules/filter-status/?taskId= —— 查询异步筛选进度/结果。"""

    def get(self, request):
        task_id = request.query_params.get('taskId') or request.query_params.get('task_id')
        if not task_id:
            return Response({'error': '缺少 taskId'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from .tasks import read_progress
        except Exception as exc:
            return Response({'error': f'任务模块不可用: {exc}'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        data = read_progress(task_id)
        if data is None:
            return Response({'status': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(data, status=status.HTTP_200_OK)


class FilterBySceneView(APIView):
    """POST /api/v1/metrics/rules/filter/ —— 批量按场景规则筛选候选人。

    两种用法：
      1. 传 candidateIds：对指定候选人执行（分页/已知集合场景）
      2. 不传 candidateIds：对当前在库候选人执行（上限 FILTER_MAX_CANDIDATES 条保护），
         返回 passedIds —— 前端再带 ids= 请求候选人列表，保证分页与总数正确。
    """

    def post(self, request):
        payload = request.data or {}
        scene = payload.get('scene')
        if not scene:
            return Response({'error': '缺少 scene'}, status=status.HTTP_400_BAD_REQUEST)

        raw_ids = payload.get('candidateIds') or payload.get('candidate_ids')
        if raw_ids is None:
            candidate_ids = default_candidate_ids(limit=FILTER_MAX_CANDIDATES)
            total = count_candidates()
        elif isinstance(raw_ids, list):
            candidate_ids = [str(i) for i in raw_ids]
            total = len(candidate_ids)
        else:
            return Response(
                {'error': 'candidateIds 必须是数组'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 缓存：同场景 + 同候选集合直接复用（规则含派生指标，逐条计算较贵）
        cache_key = _cache_key(scene, candidate_ids)
        try:
            cached = cache.get(cache_key)
        except Exception:
            cached = None
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        result = filter_candidates_by_scene(scene, candidate_ids)
        result['scanned'] = len(candidate_ids)
        result['total'] = total
        # 同步扫描有上限；超出时前端应改走异步任务拿全量结果，避免静默截断
        result['truncated'] = len(candidate_ids) < total

        try:
            cache.set(cache_key, result, FILTER_CACHE_TTL)
        except Exception:
            pass
        return Response(result, status=status.HTTP_200_OK)


class MetricRuleViewSet(viewsets.ModelViewSet):
    """指标规则 CRUD + 启停 + 按持久化规则执行。

    与一次性 execute 的区别：本 ViewSet 的规则**落库**，可被业务触发点按 scene
    取用（入池 / 筛选 / 评分），并支持启用停用。
    """

    queryset = MetricRule.objects.all().order_by('-created_at')
    serializer_class = MetricRuleSerializer
    pagination_class = StandardResultsSetPagination

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """启用/停用切换（幂等，返回切换后的状态）。"""
        rule = self.get_object()
        rule.enabled = not rule.enabled
        rule.save(update_fields=['enabled', 'updated_at'])
        return Response({'id': rule.id, 'enabled': rule.enabled})

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """按已保存规则对真实候选人执行（业务触发点的统一入口）。"""
        rule = self.get_object()
        candidate_id = (request.data or {}).get('candidateId') or (request.data or {}).get('candidate_id')
        if not candidate_id:
            return Response({'error': '缺少 candidateId'}, status=status.HTTP_400_BAD_REQUEST)
        snapshot = build_candidate_snapshot(candidate_id)
        if not snapshot.get('candidate'):
            return Response(
                {'error': f'候选人 {candidate_id} 不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )
        result = MetricEngine.execute(
            rule.to_engine_conditions(), snapshot, rule.logic or 'AND',
        )
        return Response(result, status=status.HTTP_200_OK)


class RuleExecuteView(APIView):
    """POST /api/v1/metrics/rules/execute/ —— 配置即执行，不落库。"""

    def post(self, request):
        payload = self._normalize(request.data or {})
        serializer = RuleExecuteSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        conditions = self._to_engine_conditions(payload.get('conditions') or [])
        result = MetricEngine.execute(conditions, data['data'], data.get('logic') or 'AND')
        return Response(result, status=status.HTTP_200_OK)

    @staticmethod
    def _normalize(payload: dict) -> dict:
        """把 camelCase 条件归一化为 serializer 需要的 snake_case。"""
        raw_conditions = payload.get('conditions') or []
        normalized = []
        for cond in raw_conditions:
            if not isinstance(cond, dict):
                continue
            normalized.append({
                'template_id': cond.get('template_id') or cond.get('templateId'),
                'operator': cond.get('operator'),
                'value': cond.get('value'),
                'meta': cond.get('meta') or cond.get('metaJson') or {},
            })
        payload = dict(payload)
        payload['conditions'] = normalized
        return payload

    @staticmethod
    def _to_engine_conditions(raw_conditions: list) -> list:
        """引擎侧契约（同时兼容 templateId / template_id 两种拼写）。"""
        out = []
        for cond in raw_conditions:
            if not isinstance(cond, dict):
                continue
            out.append({
                'templateId': cond.get('template_id') or cond.get('templateId'),
                'operator': cond.get('operator'),
                'value': cond.get('value'),
                'meta': cond.get('meta') or {},
            })
        return out


class OperatorCatalogView(APIView):
    """GET 运算符目录（复用统一规则引擎的 11 种运算符）。"""

    def get(self, request):
        return Response([
            {'value': value, 'label': label}
            for value, label in UnifiedOperator.choices
        ])


class DerivedFuncCatalogView(APIView):
    """GET 派生计算函数目录 —— 运营据此零代码新增派生指标。"""

    def get(self, request):
        return Response(list_funcs())


@api_view(['GET'])
def sample_data(request):
    return Response(SAMPLE_CANDIDATE)


class CandidateSnapshotView(APIView):
    """GET /api/v1/metrics/candidates/{id}/snapshot/ —— 真实候选人数据快照。

    规则引擎的取值入口：把 ORM 组装成嵌套 dict，供原子指标 source_path 解析。
    候选人不存在返回 404 JSON（不抛异常）。
    """

    def get(self, request, candidate_id):
        snapshot = build_candidate_snapshot(candidate_id)
        if not snapshot.get('candidate'):
            return Response(
                {'error': f'候选人 {candidate_id} 不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(snapshot, status=status.HTTP_200_OK)


class CandidateFieldCatalogView(APIView):
    """GET /api/v1/metrics/candidate-fields/ —— 可引用的字段路径清单。

    供配置原子指标时下拉选择（path/label/dataType），避免手填路径导致解析失败。
    """

    def get(self, request):
        return Response(list_candidate_paths())
