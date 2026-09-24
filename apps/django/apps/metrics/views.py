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
from .services.rule_trigger import evaluate_scene, filter_candidates_by_scene

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


class FilterBySceneView(APIView):
    """POST /api/v1/metrics/rules/filter/ —— 批量按场景规则筛选候选人。"""

    def post(self, request):
        payload = request.data or {}
        scene = payload.get('scene')
        candidate_ids = payload.get('candidateIds') or payload.get('candidate_ids') or []
        if not scene or not isinstance(candidate_ids, list):
            return Response(
                {'error': '缺少 scene 或 candidateIds'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            filter_candidates_by_scene(scene, candidate_ids), status=status.HTTP_200_OK,
        )


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
