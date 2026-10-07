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
from django.http import HttpResponse
from io import BytesIO
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.common.views import EnvelopeWriteMixin
from apps.rule_engine.models import UnifiedOperator

from .io_template import (
    _log_template_audit,
    build_template_export_rows,
    build_template_export_workbook,
    build_template_export_csv,
    build_template_template_workbook,
    build_template_template_csv,
    import_templates,
)
from .models import AtomicMetric, DerivedMetric, MetricRule, MetricTemplate
from .services.template_impact import get_template_affected_rules
from .serializers import (
    AtomicMetricSerializer,
    DerivedMetricSerializer,
    MetricRuleSerializer,
    MetricTemplateSerializer,
    MetricTemplateVersionSerializer,
    RuleExecuteSerializer,
)
from .services.candidate_snapshot import (
    build_candidate_snapshot,
    build_demand_snapshot,
    build_position_snapshot,
    list_candidate_paths,
)
from .services.derived_registry import get as get_derived_func, list_funcs
from .services.metric_engine import MetricEngine
from .services.operator_matrix import operators_for
from .services.template_version import (
    SEMANTIC_FIELDS,
    RollbackBlocked,
    TemplateVersionError,
    TemplateVersionNotFound,
    create_version_snapshot,
    list_versions,
    rollback_template,
)
from .services.rule_trigger import (
    _build_rule_context,
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


class AtomicMetricViewSet(EnvelopeWriteMixin, _RefCheckMixin, viewsets.ModelViewSet):
    queryset = AtomicMetric.objects.all().order_by('name')
    serializer_class = AtomicMetricSerializer
    pagination_class = StandardResultsSetPagination


class DerivedMetricViewSet(EnvelopeWriteMixin, _RefCheckMixin, viewsets.ModelViewSet):
    queryset = DerivedMetric.objects.all().order_by('name')
    serializer_class = DerivedMetricSerializer
    pagination_class = StandardResultsSetPagination


class MetricTemplateViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
    queryset = MetricTemplate.objects.all().select_related(
        'atomic_metric', 'derived_metric'
    ).order_by('name')
    serializer_class = MetricTemplateSerializer
    pagination_class = StandardResultsSetPagination

    def destroy(self, request, *args, **kwargs):
        """软删除：仅置 deleted_at，不物理删行（D1：允许删除被规则引用的模板）。

        - 删除前的事前披露（受影响规则清单）由前端 LIVE-2 弹窗负责，后端不再 400 拦截；
          因此此处不再调用 get_template_affected_rules 做闸门，避免重复拦截。
        - 软删后列表/详情（默认 manager 过滤 deleted_at）自动隐藏；版本快照表
          on_delete=CASCADE 不会触发（行仍在），规则 conditions 里存的模板 id 字符串
          依旧有效，引用不断。
        - soft_delete() 内部只落 deleted_at / updated_at，不写 updated_by，
          故另存一次 updated_by 记录操作人（D2：零新增字段，复用 updated_by）。
        """
        obj = self.get_object()
        obj.updated_by = request.user
        obj.soft_delete()
        obj.updated_by = request.user
        obj.save(update_fields=['updated_by'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, *args, **kwargs):
        """真撤销：把已软删的模板恢复回原 id（引用规则 / 版本快照天然保住）。

        用 all_objects 取（默认 objects 已过滤软删，取不到已删行）。清掉 deleted_at 并
        记录 updated_by。前端 8s 撤销 action 调此端点即可原样恢复，而非新建一个全新 id
        （旧 createMetricTemplate(restorePayload) 会生成新 id，导致规则引用悬空）。
        """
        obj = MetricTemplate.all_objects.get(id=kwargs['pk'])
        obj.deleted_at = None
        obj.updated_by = request.user
        obj.save(update_fields=['deleted_at', 'updated_by', 'updated_at'])
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ===== LIFE-1 版本化：写路径覆盖 =====
    def perform_create(self, serializer):
        """新建模板：version 默认=1，落一条 kind='create' 基线快照（与 0019 存量回填语义一致）。"""
        instance = serializer.save()
        create_version_snapshot(instance, self.request.user, kind='create', note='初始创建')
        return instance

    def perform_update(self, serializer):
        """更新模板：仅当语义字段（SEMANTIC_FIELDS）真正变更时才 version+1 并落快照。

        用「旧值 vs 新值」比较，而非「payload 是否含该 key」——
        否则 PUT 全字段提交会把未变字段也算作变更，导致无谓 bump。
        非语义字段（status / description 等）变更不 bump、不落快照（方案 C / D4-4a）。
        """
        instance = serializer.instance
        old_values = {f: getattr(instance, f) for f in SEMANTIC_FIELDS}
        super().perform_update(serializer)
        changed = [f for f in SEMANTIC_FIELDS if old_values[f] != getattr(instance, f, None)]
        if changed:
            from django.db import transaction

            # B-3 修复：version bump + 落快照整体原子化。配合 create_version_snapshot 的
            # get_or_create，彻底消除并发更新撞 uniq_tpl_version 唯一约束导致的 IntegrityError→500。
            with transaction.atomic():
                instance.version += 1
                instance.save(update_fields=['version'])
                create_version_snapshot(
                    instance, self.request.user, kind='update',
                    note='语义变更: ' + ','.join(changed),
                )
        return instance

    @action(detail=True, methods=['get'], url_path='versions')
    def versions(self, request, pk=None):
        """GET 某模板的版本历史（倒序，最近在前）。"""
        instance = self.get_object()
        rows = list_versions(instance.id)
        return success_response(MetricTemplateVersionSerializer(rows, many=True).data)

    @action(detail=True, methods=['post'], url_path='versions/rollback')
    def rollback_version(self, request, pk=None):
        """POST 回滚到指定版本：body {version_no: int}。

        异常映射：版本不存在 → 404；引用指标失效/其它版本错误 → 400。
        """
        instance = self.get_object()
        raw = (request.data or {}).get('version_no')
        try:
            version_no = int(raw)
        except (TypeError, ValueError):
            return Response(
                {'error': 'version_no 必须为整数'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rollback_template(instance, version_no, self.request.user)
        except TemplateVersionNotFound:
            return Response(
                {'error': f'版本 {version_no} 的快照不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except RollbackBlocked as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except TemplateVersionError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return success_response(MetricTemplateSerializer(instance).data)

    @action(detail=False, methods=['get'], url_path='export')
    def export_templates(self, request):
        """导出全部指标模板为 xlsx / csv（业务字段 8 列）。"""
        fmt = (request.query_params.get('file_format') or 'xlsx').lower()
        rows = build_template_export_rows()
        if fmt == 'csv':
            content = build_template_export_csv(rows)
            resp = HttpResponse(content, content_type='text/csv; charset=utf-8-sig')
            resp['Content-Disposition'] = 'attachment; filename="metrics_templates_export.csv"'
        else:
            wb = build_template_export_workbook(rows)
            buf = BytesIO()
            wb.save(buf)
            buf.seek(0)
            resp = HttpResponse(
                buf.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            resp['Content-Disposition'] = 'attachment; filename="metrics_templates_export.xlsx"'
        _log_template_audit(
            request.user, 'EXPORT', f'导出指标模板 {len(rows)} 条（{fmt}）', request=request,
        )
        return resp

    @action(detail=False, methods=['get'], url_path='template')
    def template_templates(self, request):
        """下载指标模板导入模板（xlsx / csv，含表头 + 示例 + 填写说明）。"""
        fmt = (request.query_params.get('file_format') or 'xlsx').lower()
        if fmt == 'csv':
            content = build_template_template_csv()
            resp = HttpResponse(content, content_type='text/csv; charset=utf-8-sig')
            resp['Content-Disposition'] = 'attachment; filename="metrics_templates_template.csv"'
        else:
            wb = build_template_template_workbook()
            buf = BytesIO()
            wb.save(buf)
            buf.seek(0)
            resp = HttpResponse(
                buf.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            resp['Content-Disposition'] = 'attachment; filename="metrics_templates_template.xlsx"'
        _log_template_audit(
            request.user, 'TEMPLATE', f'下载指标模板导入模板（{fmt}）', request=request,
        )
        return resp

    @action(detail=False, methods=['post'], url_path='import')
    def import_templates_action(self, request):
        """批量导入指标模板：数据校验 + 重复项处理（mode=skip|update|error）。

        校验：模板名称非空且 ≤64；引用指标必须存在；指标类型非法 → 报错；
        运算符按中文→code 归一化，非法 code → 报错；允许为空/状态解析；文件内重名 → 报错。
        与库内重复按 mode 处理；任一硬校验错误整体 400 并附错误报告（xlsx，base64）。
        """
        f = request.FILES.get('file')
        mode = request.data.get('mode') or request.query_params.get('mode') or 'skip'
        result = import_templates(
            user=request.user, file_obj=f, mode=mode,
            filename=(f.name if f else ''), request=request,
        )
        return Response(result.payload, status=result.status_code)

    @action(detail=True, methods=['get'], url_path='affected-rules')
    def affected_rules(self, request, pk=None):
        """禁用/删除前枚举引用该模板的全部规则（进入条件 ORM + skip/archive JSON）。

        LIFE-2 事前披露：前端在禁用/删除确认弹窗前调用，展示受影响规则清单 +
        处理建议。返回体经 CamelCaseJSONRenderer 转 camelCase（entryConditions /
        ruleId / processName / templateStatus 等），前端读 camelCase。
        """
        from .services.template_impact import get_template_affected_rules

        try:
            data = get_template_affected_rules(pk)
        except MetricTemplate.DoesNotExist:
            return Response(
                {'error': '指标模板不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data)


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
        return success_response(evaluate_scene(scene, candidate_id))


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
        except Exception as exc:  # noqa: BLE001 — 无 Celery worker / broker 时明确报错 (503), 不静默假装成功
            return Response(
                {'error': f'异步任务启动失败（请确认 Celery worker 已启动）: {exc}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return success_response({'taskId': task_id})


class FilterStatusView(APIView):
    """GET /api/v1/metrics/rules/filter-status/?taskId= —— 查询异步筛选进度/结果。"""

    def get(self, request):
        task_id = request.query_params.get('taskId') or request.query_params.get('task_id')
        if not task_id:
            return Response({'error': '缺少 taskId'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from .tasks import read_progress
        except Exception as exc:  # noqa: BLE001 — 任务模块导入失败 (通常因依赖缺失/循环), 显式 503
            return Response({'error': f'任务模块不可用: {exc}'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        data = read_progress(task_id)
        if data is None:
            return Response({'status': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        return success_response(data)


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
        except Exception:  # noqa: BLE001 — 缓存读失败返 None 回退到无缓存路径, 不阻断筛选
            cached = None
        if cached is not None:
            return success_response(cached)

        result = filter_candidates_by_scene(scene, candidate_ids)
        result['scanned'] = len(candidate_ids)
        result['total'] = total
        # 同步扫描有上限；超出时前端应改走异步任务拿全量结果，避免静默截断
        result['truncated'] = len(candidate_ids) < total

        try:
            cache.set(cache_key, result, FILTER_CACHE_TTL)
        except Exception:  # noqa: BLE001 — 缓存写失败不应阻断结果返回 (筛选结果可重算, 缓存是性能优化)
            pass
        return success_response(result)


class MetricRuleViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
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
        return success_response({'id': rule.id, 'enabled': rule.enabled})

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
        # 并入规则绑定的需求/职位快照，使 demand.* / position.* 指标可真实求值
        data = {**snapshot, **_build_rule_context(rule)}
        result = MetricEngine.execute(
            rule.to_engine_conditions(), data, rule.logic or 'AND',
        )
        return success_response(result)




class RuleExecuteView(APIView):
    """POST /api/v1/metrics/rules/execute/ —— 配置即执行，不落库。"""

    def post(self, request):
        payload = self._normalize(request.data or {})
        serializer = RuleExecuteSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        conditions = self._to_engine_conditions(payload.get('conditions') or [])
        eval_data = data.get('data') or {}
        # 配置即执行时允许前端传入 demandId/positionId 以测试 demand.* / position.* 指标
        raw = request.data or {}
        demand_id = raw.get('demandId') or raw.get('demand_id')
        position_id = raw.get('positionId') or raw.get('position_id')
        if demand_id:
            try:
                eval_data.update(build_demand_snapshot(demand_id))
            except Exception:  # noqa: BLE001 — 需求快照失败不阻断评估 (降级到缺数据, 让 MetricEngine 单条 FAIL)
                pass
        if position_id:
            try:
                eval_data.update(build_position_snapshot(position_id))
            except Exception:  # noqa: BLE001 — 职位快照失败不阻断评估 (同上)
                pass
        result = MetricEngine.execute(conditions, eval_data, data.get('logic') or 'AND')
        return success_response(result)

    @staticmethod
    def _normalize(payload: dict) -> dict:
        """把 camelCase 条件归一化为 serializer 需要的 snake_case。

        🔴 right_template_id 必须一起归一化，否则方案 B 的「对比指标」既过不了
        ConditionInputSerializer 的类型一致性校验，也到不了引擎。
        """
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
                'right_template_id': cond.get('right_template_id') or cond.get('rightTemplateId'),
            })
        payload = dict(payload)
        payload['conditions'] = normalized
        return payload

    @staticmethod
    def _to_engine_conditions(raw_conditions: list) -> list:
        """引擎侧契约（同时兼容 templateId / template_id 两种拼写）。

        🔴 rightTemplateId 必须透传（方案 B）；引擎 :157 读 cond.get('rightTemplateId')。
        """
        out = []
        for cond in raw_conditions:
            if not isinstance(cond, dict):
                continue
            out.append({
                'templateId': cond.get('template_id') or cond.get('templateId'),
                'operator': cond.get('operator'),
                'value': cond.get('value'),
                'meta': cond.get('meta') or {},
                'rightTemplateId': cond.get('right_template_id') or cond.get('rightTemplateId'),
            })
        return out


class OperatorCatalogView(APIView):
    """GET 运算符目录（复用统一规则引擎的 11 种运算符）。"""

    def get(self, request):
        return success_response([
            {'value': value, 'label': label}
            for value, label in UnifiedOperator.choices
        ])


class DerivedFuncCatalogView(APIView):
    """GET 派生计算函数目录 —— 运营据此零代码新增派生指标。"""

    def get(self, request):
        return success_response(list_funcs())


@api_view(['GET'])
def sample_data(request):
    return success_response(SAMPLE_CANDIDATE)


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
        return success_response(snapshot)


class CandidateFieldCatalogView(APIView):
    """GET /api/v1/metrics/candidate-fields/ —— 可引用的字段路径清单。

    供配置原子指标时下拉选择（path/label/dataType），避免手填路径导致解析失败。
    """

    def get(self, request):
        return success_response(list_candidate_paths())


class MetricDefinitionViewSet(APIView):
    """GET /api/v1/metrics/definitions/ —— 统一「指标定义」视图（原子 + 派生合并）。

    将原子指标与派生指标整合为一张清单，列与产品截图一致：
        指标定义 / 取值方式（对象路径 | 参数化 Handler）/ 数据源配置 /
        支持的运算符（能力白名单）/ 参数 / 返回类型

    关键约束（用户诉求）：
        - 取值方式：原子=object_path（对象路径）；派生=parametric_handler（参数化 Handler）
        - 支持的运算符依据字段类型由 operator_matrix 计算，且全部为引擎真实实现
        - 参数化指标（派生函数带 param_schema）不在「新增字段自动映射」之列，
          此处仍展示已存在的派生定义，由用户手动指派后另行添加
    """

    def get(self, request):
        rows: list = []

        # 入参类型判定（PRD 指标定义列「入参类型(离散/连续)」）：
        #   数值/日期 → 连续（可在区间内连续取值）；枚举/布尔/文本 → 离散（取离散值）
        def _param_type(data_type: str, is_enum: bool) -> str:
            if is_enum:
                return 'discrete'
            return 'continuous' if data_type in ('number', 'date') else 'discrete'

        # 原子指标（对象路径）
        for m in AtomicMetric.objects.all().order_by('name'):
            ops = operators_for(m.data_type, getattr(m, 'is_enum', False))
            rows.append({
                'id': m.id,
                'kind': 'atomic',
                'name': m.name,
                'valueMode': 'object_path',
                'dataSource': m.source_path,
                'params': {},
                'returnType': m.data_type,
                'unit': m.unit or '',
                'isEnum': getattr(m, 'is_enum', False),
                'enumValues': list(m.enum_values or []),
                'paramType': _param_type(m.data_type, getattr(m, 'is_enum', False)),
                'supportedOperators': ops,
                'description': m.description,
                'autoGenerated': getattr(m, 'auto_generated', False),
            })

        # 派生指标（参数化 Handler）
        for m in DerivedMetric.objects.all().order_by('name'):
            func = get_derived_func(m.calc_func)
            is_param = bool(func and func.get('param_schema'))
            ops = operators_for(m.data_type, False)
            rows.append({
                'id': m.id,
                'kind': 'derived',
                'name': m.name,
                'valueMode': 'parametric_handler',
                'dataSource': m.base_path,
                # 定义层不再持有计算参数值（已下沉到模板 calc_params）；保留空 params 兼容旧契约
                'params': {},
                'returnType': m.data_type,
                'unit': m.unit or '',
                'isEnum': False,
                'enumValues': [],
                'paramType': _param_type(m.data_type, False),
                'supportedOperators': ops,
                'description': m.description,
                'calcFunc': m.calc_func,
                'isParametric': is_param,
                # 派生函数的参数声明（前端据此渲染类型化参数编辑，如 recent_n）
                'paramSchema': (func.get('param_schema') or []) if func else [],
                'autoGenerated': False,
            })

        return success_response(rows)

