"""人员比例管控系统 v2.1 — 视图与 API 端点（均挂在 /api/v1/campus/ 下）。

端点：
  GET    /dimensions/              维度列表
  POST   /dimensions/              新建维度
  GET/PUT/DELETE /dimensions/{id}/
  GET    /indicators/?dimension=   指标列表（可按维度过滤）
  POST   /indicators/              新建指标
  GET/PUT/DELETE /indicators/{id}/
  GET    /rules/?bu=&position=&level=       规则列表（按适用范围过滤）
  POST   /rules/                   新建规则（单条仅拦溢出）
  PUT/DELETE /rules/{id}/
  GET    /rules/ratio/?bu=&position=&level=       实时看板（适用范围过滤）
  POST   /rules/validate/?year=    录入校验（draft 含 bu/position/level）
  POST   /rules/batch/             批量保存某适用范围+维度的全部规则（100% 硬校验）
  GET    /headcounts/?bu=&position=&level=&year=  人数目标列表
  POST   /headcounts/              新建/编辑人数目标
  GET/PUT/DELETE /headcounts/{id}/
  GET    /persons/                 人员主数据
  POST/PUT/DELETE /persons/{id}/

v2.9 拆分说明：
  - 巨型业务方法（>50 行）下沉到 services.py；ViewSet 仅保留「@action 装饰器 + 1~3 行转发」。
  - 共享私有 helper（_rule_to_dict / _build_person_dim_map / _person_to_dict / _jsonify）保留在
    views.py（被 services.py 通过 _views_helpers 惰性 import 复用，避免循环依赖）。
"""
from decimal import Decimal
from io import BytesIO

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import SoftDeleteRestoreMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.common.views import EnvelopeWriteMixin
from apps.core.permissions import IsHROrAbove
from apps.core.permissions_v2 import ScopeQuerysetMixin, V2Permission

from . import class_formation, person_profile, person_rotation_stats, services
from .calc import _COUNTED_STATUSES, compute_ratio, simulate
from .constants import DATA_SCOPE_ENTRY_YEAR_MIN, STATUS
from .io_indicator import (
    build_indicator_export_csv,
    build_indicator_export_workbook,
    build_indicator_template_csv,
    build_indicator_template_workbook,
)
from .io_xlsx import (
    build_export_workbook,
    build_template_workbook,
)
from .models import (
    BatchNaming,
    BatchRule,
    ControlDimension,
    ControlIndicator,
    ControlRule,
    Person,
)
from .serializers import (
    BatchNamingSerializer,
    BatchRuleSerializer,
    ControlDimensionSerializer,
    ControlIndicatorSerializer,
    ControlRuleSerializer,
    PersonSerializer,
)


def _jsonify(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


def _rule_to_dict(r):
    return {
        'bu': r.bu or '',
        'position': r.position or '',
        'level': r.level or '',
        'dimension': r.dimension.name,
        'indicator': r.indicator.name,
        'year': r.year,
        'target': float(r.target),
        'strength': r.strength,
        'annual_target': r.annual_target,
        'monthly_targets': list(r.monthly_targets) if isinstance(r.monthly_targets, (list, tuple)) else [0] * 12,
        # v2.10：浮动目标开关（默认 False；compute_rollover_target 入口防御已确保跨年=0）
        'rollover_enabled': getattr(r, 'rollover_enabled', False),
    }


def _build_person_dim_map():
    """预加载人员动态维度取值：{person_id: {维度名: 取值}}。"""
    from .models import PersonDimensionValue
    m = {}
    for pv in PersonDimensionValue.objects.select_related('dimension'):
        m.setdefault(pv.person_id, {})[pv.dimension.name] = pv.value
    return m


def _person_to_dict(p, dim_map=None):
    d = {
        'bu': p.bu,
        'school': p.school,
        'sex': p.sex,
        'major': p.major,
        'month': p.month,
        'status': p.status,
        'expected_entry_date': p.expected_entry_date.isoformat() if p.expected_entry_date else None,
        'actual_entry_date': p.actual_entry_date.isoformat() if p.actual_entry_date else None,
        'counted': p.counted,
        'position': p.position or '',
        'level': p.level or '',
    }
    # 动态维度（非 legacy）取值注入为 __dim__<维度名>，供 calc 通用过滤
    for dim_name, val in (dim_map or {}).get(p.id, {}).items():
        d[f'__dim__{dim_name}'] = val
    return d


class CampusCRUDMixin:
    """写操作统一兜底：带入当前用户；软删（instance.soft_delete）；审计埋点（需求 5-6）。"""

    def _audit_entity(self) -> str:
        """审计实体标识：优先用子类声明的 audit_entity，否则回退模型名。"""
        return getattr(self, 'audit_entity', self.queryset.model.__name__)

    def perform_create(self, serializer):
        try:
            instance = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError({'detail': f'数据库约束冲突：{e}'})
        from apps.common.audit_helper import log_action
        log_action(self.request, 'create', self._audit_entity(), instance.pk)

    def perform_update(self, serializer):
        try:
            instance = serializer.save(updated_by=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError({'detail': f'数据库约束冲突：{e}'})
        from apps.common.audit_helper import log_action
        log_action(self.request, 'update', self._audit_entity(), instance.pk)

    def perform_destroy(self, instance):
        pk = instance.pk
        instance.soft_delete()
        from apps.common.audit_helper import log_action
        log_action(self.request, 'delete', self._audit_entity(), pk)


class ControlDimensionViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    queryset = ControlDimension.objects.all()
    serializer_class = ControlDimensionSerializer
    permission_classes = [V2Permission]
    # G2: 校招管控配置此前对任意登录用户开放, 现改为资源码校验
    permission_required = 'recruit:campus:campus_control:list'
    permission_required_map = {
        'create': 'recruit:campus:campus_control:edit',
        'update': 'recruit:campus:campus_control:edit',
        'partial_update': 'recruit:campus:campus_control:edit',
        'destroy': 'recruit:campus:campus_control:edit',
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return ControlDimension.objects.filter(deleted_at__isnull=True)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """R-106 撤销：恢复已软删维度。"""
        # M07 长尾: 原为 self.queryset.model.objects.get(pk=pk) —— 直接走默认
        # manager, 绕过 ViewSet 的 queryset 解析(含任何范围过滤)。改用
        # get_object() 复用 queryset 语义; 未配置写范围时行为不变 (fail-open)。
        #
        # 2026-10-21 卡 D3: get_object() 走 get_queryset(), 而后者按 deleted_at 过滤
        # → **恢复软删对象必然 404** (既有缺陷, 非本次引入)。
        # SoftDeleteRestoreMixin 让 restore 动作下的 get_object() 能取到已软删行,
        # 同时保留 get_object() 的行级隔离语义 (守卫要求 restore 必须走 get_object())。
        instance = self.get_object()
        instance.restore()
        return Response({'success': True, 'id': str(instance.id)})

    @action(detail=True, methods=['put'], url_path='rules')
    def set_rules(self, request, pk=None):
        """原子替换某 (bu, position, level, dimension, year) 下的全部规则。

        与 /rules/batch/ 同源逻辑：硬校验「目标占比加和 == 100%」，不等于 100% 直接 400；
        通过则事务内删除旧规则并重建。

        入参: {
          bu, position, level, year,
          totalTarget?,  // 维度年度管控人数：各指标 annualTarget 加和须 == 此值，否则 400（人数加和硬拦）
          rules: [{indicator, target, strength, annualTarget?, monthlyTargets?}],
        }
          - rules 为空数组 [] → 显式清空该 (适用范围, 维度, 年度) 规则集（跳过 100% 校验与互斥守卫，写审计）。
          - 未出现在 rules 中的指标即视为删除（原子替换语义）。
          - target 为 0~1 小数；strength ∈ STRENGTH。
          - 年度人数 annualTarget 与 12 个月度 monthlyTargets **成对可选**：
            · 两者都未传 → 从旧规则继承（调整占比不丢人数目标）。
            · 两者都传 → 用前端传入的，并校验 monthlyTargets 是长度 12 的非负整数数组，
                       且 monthly_targets 之和 = annualTarget（任一不满足 400）。
            · 仅传其中一个 → 400（避免数据不一致）。
          - 若传入 totalTarget，则 Σ(各规则 annualTarget) 须 == totalTarget，否则 400（人数加和硬拦）。
        """
        dimension = self.get_object()
        result = services.set_rules_for_dimension(
            user=request.user, dimension=dimension, payload=request.data, request=request,
        )
        return Response(result.payload, status=result.status_code)


class ControlIndicatorViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    queryset = ControlIndicator.objects.all()
    serializer_class = ControlIndicatorSerializer
    permission_classes = [V2Permission]
    # G2: 校招管控配置此前对任意登录用户开放, 现改为资源码校验
    permission_required = 'recruit:campus:campus_control:list'
    permission_required_map = {
        'create': 'recruit:campus:campus_control:edit',
        'update': 'recruit:campus:campus_control:edit',
        'partial_update': 'recruit:campus:campus_control:edit',
        'destroy': 'recruit:campus:campus_control:edit',
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = ControlIndicator.objects.filter(deleted_at__isnull=True)
        dim = self.request.query_params.get('dimension')
        if dim:
            qs = qs.filter(dimension_id=dim)
        # #9 (2026-10-09): ControlIndicatorSerializer.get_dimension_name 逐行查
        # obj.dimension.name -> 列表 N 行 N 次查询。select_related 一次 join。
        return qs.select_related('dimension')

    # ---- 权限：导入/导出/模板 需 HR 及以上；其余沿用已认证 ----
    def get_permissions(self):
        if self.action in ('export_indicators', 'template_indicators', 'import_indicators'):
            return [IsHROrAbove()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """R-106 撤销：恢复已软删指标。"""
        # M07 长尾: 原为 self.queryset.model.objects.get(pk=pk) —— 直接走默认
        # manager, 绕过 ViewSet 的 queryset 解析(含任何范围过滤)。改用
        # get_object() 复用 queryset 语义; 未配置写范围时行为不变 (fail-open)。
        instance = self.get_object()
        instance.restore()
        return Response({'success': True, 'id': str(instance.id)})

    @action(detail=False, methods=['get'], url_path='export')
    def export_indicators(self, request):
        """导出全部指标为 xlsx / csv（含完整字段：维度、指标名称、是否启用）。"""
        fmt = (request.query_params.get('file_format') or 'xlsx').lower()
        rows = [
            {'dimension_name': i.dimension.name, 'name': i.name, 'is_active': i.is_active}
            for i in ControlIndicator.objects.select_related('dimension').all().order_by('dimension__name', 'name')
        ]
        if fmt == 'csv':
            content = build_indicator_export_csv(rows)
            resp = HttpResponse(content, content_type='text/csv; charset=utf-8-sig')
            resp['Content-Disposition'] = 'attachment; filename="campus_indicators_export.csv"'
        else:
            wb = build_indicator_export_workbook(rows)
            buf = BytesIO()
            wb.save(buf)
            buf.seek(0)
            resp = HttpResponse(
                buf.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            resp['Content-Disposition'] = 'attachment; filename="campus_indicators_export.xlsx"'
        services._log_indicator_audit(
            request.user, 'EXPORT', f'导出指标 {len(rows)} 条（{fmt}）', request=request,
        )
        return resp

    @action(detail=False, methods=['get'], url_path='template')
    def template_indicators(self, request):
        """下载指标导入模板（xlsx / csv，含表头 + 示例 + 填写说明）。"""
        fmt = (request.query_params.get('file_format') or 'xlsx').lower()
        if fmt == 'csv':
            content = build_indicator_template_csv()
            resp = HttpResponse(content, content_type='text/csv; charset=utf-8-sig')
            resp['Content-Disposition'] = 'attachment; filename="campus_indicators_template.csv"'
        else:
            wb = build_indicator_template_workbook()
            buf = BytesIO()
            wb.save(buf)
            buf.seek(0)
            resp = HttpResponse(
                buf.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            resp['Content-Disposition'] = 'attachment; filename="campus_indicators_template.xlsx"'
        services._log_indicator_audit(
            request.user, 'EXPORT', f'下载指标导入模板（{fmt}）', request=request,
        )
        return resp

    @action(detail=False, methods=['post'], url_path='import')
    def import_indicators(self, request):
        """批量导入指标：数据校验 + 重复项处理（mode=skip|update|error）。

        校验：维度须存在；指标名称非空且 ≤32；是否启用须可解析；文件内同 (维度,指标名称) 不可重复。
        与库内重复按 mode 处理：skip=跳过 / update=更新 is_active / error=整批拒绝（原子回滚）。
        任一硬校验错误 → 整体 400 并附错误报告（xlsx，base64）。
        """
        f = request.FILES.get('file')
        mode = request.data.get('mode') or request.query_params.get('mode') or 'skip'
        result = services.import_indicators(
            user=request.user, file_obj=f, mode=mode,
            filename=(f.name if f else ''), request=request,
        )
        return Response(result.payload, status=result.status_code)


class ControlRuleViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    queryset = ControlRule.objects.all()
    serializer_class = ControlRuleSerializer
    permission_classes = [V2Permission]
    # G2: 校招管控配置此前对任意登录用户开放, 现改为资源码校验
    permission_required = 'recruit:campus:campus_control:list'
    permission_required_map = {
        'create': 'recruit:campus:campus_control:edit',
        'update': 'recruit:campus:campus_control:edit',
        'partial_update': 'recruit:campus:campus_control:edit',
        'destroy': 'recruit:campus:campus_control:edit',
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = ControlRule.objects.filter(deleted_at__isnull=True)
        bu = self.request.query_params.get('bu')
        position = self.request.query_params.get('position')
        level = self.request.query_params.get('level')
        if bu is not None:
            qs = qs.filter(bu=bu)
        if position is not None:
            qs = qs.filter(position=position)
        if level is not None:
            qs = qs.filter(level=level)
        # #9 (2026-10-09): ControlRuleSerializer 4 个 MethodField 逐行查
        # dimension.name / indicator.name / created_by.full_name / updated_by.full_name,
        # 列表 N 行 -> 4N 次查询。select_related 一次 join 全部吸收。
        return qs.select_related('dimension', 'indicator', 'created_by', 'updated_by')

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """R-106 撤销：恢复已软删规则。"""
        # M07 长尾: 原为 self.queryset.model.objects.get(pk=pk) —— 直接走默认
        # manager, 绕过 ViewSet 的 queryset 解析(含任何范围过滤)。改用
        # get_object() 复用 queryset 语义; 未配置写范围时行为不变 (fail-open)。
        instance = self.get_object()
        instance.restore()
        return Response({'success': True, 'id': str(instance.id)})

    @action(detail=False, methods=['get'], url_path='ratio')
    def ratio(self, request):
        """实时看板：展示全部规则（每条按自身适用范围独立计算）。"""
        rules = [_rule_to_dict(r) for r in ControlRule.objects.all()]
        dim_map = _build_person_dim_map()
        persons = [_person_to_dict(p, dim_map) for p in Person.objects.all()]
        result = compute_ratio(persons, rules)
        return Response({
            'success': True,
            'data': {
                'total': result['total'],
                'rows': _jsonify(result['rows']),
            },
        })

    @action(detail=False, methods=['post'], url_path='validate')
    def validate(self, request):
        draft = request.data or {}
        required = ['bu', 'school', 'sex', 'major']
        missing = [k for k in required if not draft.get(k)]
        if missing:
            return Response({'success': False, 'detail': f'缺少字段：{",".join(missing)}'}, status=400)
        rules = [_rule_to_dict(r) for r in ControlRule.objects.all()]
        dim_map = _build_person_dim_map()
        persons = [_person_to_dict(p, dim_map) for p in Person.objects.all()]
        year = request.query_params.get('year')
        year = int(year) if year else 2026
        result = simulate(draft, rules, persons, year, month=draft.get('month'))
        return Response({'success': True, 'data': _jsonify(result)})

    @action(detail=True, methods=['post'], url_path='copy')
    def copy_rule_action(self, request, pk=None):
        """复制规则为「未启用副本」（is_active=False，自动补新 code）。

        返回 200 + 副本；若源已 is_active=False 再复制导致两条未启用同键 → 409「该组合已存在未启用副本」。
        """
        rule = self.get_object()
        try:
            clone = services.copy_rule(rule)
        except IntegrityError:
            return Response(
                {'success': False, 'detail': '该组合已存在未启用副本'},
                status=409,
            )
        return Response({'success': True, 'data': ControlRuleSerializer(clone).data})

    @action(detail=True, methods=['post'], url_path='toggle')
    def toggle_rule_action(self, request, pk=None):
        """启用/停用规则。body: { is_active: bool }。

        停用(False)：直接置 is_active=False。
        启用(True)：先跑统一校验（services.validate_rule_unique）——唯一含状态 + 占比≤100%。
          冲突 → 409「该组合已存在启用规则，请改键或停用原规则」
          占比超 → 400「该适用范围下此维度指标目标占比之和不得超过 100%」
        """
        rule = self.get_object()
        raw = request.data.get('is_active')
        is_active = raw in (True, 'true', 'True', 1, '1')
        try:
            updated = services.toggle_rule(rule, is_active)
        except services.ControlRuleViolation as e:
            return Response(
                {'success': False, 'detail': e.message},
                status=e.status_code,
            )
        return Response({'success': True, 'data': ControlRuleSerializer(updated).data})

    @action(detail=False, methods=['post'], url_path='batch')
    def batch(self, request):
        """批量保存某 (bu, position, level, dimension, year) 下全部规则（原子替换）。

        硬校验「目标占比加和 == 100%」，不等于 100% 直接 400；通过则事务内删除旧规则重建。
        v2.4：取消上下限；人数目标（annual_target / monthly_targets）默认 0，可在规则中单独编辑。
        """
        result = services.batch_replace_rules(
            user=request.user, payload=request.data, request=request,
        )
        return Response(result.payload, status=result.status_code)

    @action(detail=False, methods=['post'], url_path='with-targets')
    def with_targets(self, request):
        """批量配置规则 + 人数目标（一次性原子操作）。

        入参: { bu, position, level, dimension, year, totalTarget,
                 rules: [{indicator, target, strength, monthly_targets?}] }
        行为（v2.4）：取消上下限；人数目标直接承载于规则上。
          - 校验 100% 加和 + 0<=target<=1 + indicator∈dimension
          - 事务内: 删除该(适用范围, 维度, 年度)旧规则 → 创建新规则
          - 每条规则 annual_target 由「最大余数法」按 totalTarget×target 精确分配（保证 Σannual == totalTarget，杜绝 round 加和漂移）
          - monthly_targets 优先取前端传入；未传则按年度目标均分 12 个月
          - 校验 monthly_targets 为长度 12 的非负整数数组且加和=annual_target
        """
        result = services.replace_rules_with_targets(
            user=request.user, payload=request.data, request=request,
        )
        return Response(result.payload, status=result.status_code)

    @action(detail=False, methods=['get'], url_path='export')
    def export_xlsx(self, request):
        """导出全部规则为 xlsx（列结构与导入模板一致）。"""
        rules = [_rule_to_dict(r) for r in ControlRule.objects.all().order_by(
            'bu', 'position', 'level', 'dimension__name', 'indicator__name', 'year'
        )]
        wb = build_export_workbook(rules)
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = 'attachment; filename="campus_rules_export.xlsx"'
        return resp

    @action(detail=False, methods=['get'], url_path='template')
    def template_xlsx(self, request):
        """下载规则导入模板（含表头 + 示例 + 填写说明）。"""
        wb, _ = build_template_workbook()
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = 'attachment; filename="campus_rules_template.xlsx"'
        return resp

    @action(detail=False, methods=['post'], url_path='import')
    def import_xlsx(self, request):
        """导入 xlsx 规则文件：按 (适用范围, 维度, 年度) 分组，校验 100% 与月度一致性，事务原子替换。

        复用 with_targets 的校验语义；每组独立事务，任一组失败则该组回滚并计入错误。
        返回 { success, data: { groups, saved_rules, errors } }。
        """
        f = request.FILES.get('file')
        result = services.import_rules_from_xlsx(
            user=request.user, file_obj=f,
            filename=(f.name if f else ''), request=request,
        )
        return Response(result.payload, status=result.status_code)

    def _import_group(self, g, user):
        """委托 services.import_rule_group（保持 1:1 行为；供历史单测调用，tests/test_calc.py 仍直连 ViewSet 测互斥守卫）。"""
        return services.import_rule_group(g, user)


class PersonViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, ScopeQuerysetMixin,
    viewsets.ModelViewSet
):
    """人员主数据 CRUD（全局主数据，一行一人；counted 控制是否计入核算）。

    get_queryset 仅对 list 生效（retrieve/update/delete 不套过滤，保证按 id 仍可查可改）：
      - ?staffed=1                  → 仅返回占编人员（status ∈ _COUNTED_STATUSES）
      - ?status=X                   → 按精确状态过滤（X 须为 STATUS 合法值）
      - ?bu=&position=&level=       → 适用范围 3 项精确过滤（可选）
      - ?school=&sex=&major=        → 维度 3 项精确过滤（可选）
      - ?month=X                    → 招聘月份精确过滤（X ∈ ALL_MONTHS，如 "8月"）
      - ?year=YYYY                  → 入职年度过滤：按 expected_entry_date 或 actual_entry_date 的年份
                                       （两者都为空的人员不出现在年度筛中；等价 EXTRACT(YEAR FROM...) OR 逻辑）
      - ?search=keyword             → 模糊搜索：code__icontains OR name__icontains
      - 其余（无参）                 → 返回全部人员
    实时看板/录入校验仍走 Person.objects.all() 自行按 _COUNTED_STATUSES 计数，不受影响。
    """

    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [V2Permission]
    # 校招生档案属校招业务域，权限码走 recruit:campus:person:*（不再是 campus-control 配置域），
    # 避免校招 HR 需要「校招管控配置」权限才能维护本域档案。
    permission_required = 'recruit:campus:person:list'
    permission_required_map = {
        'create': 'recruit:campus:person:create',
        'update': 'recruit:campus:person:edit',
        'partial_update': 'recruit:campus:person:edit',
        'destroy': 'recruit:campus:person:delete',
        'restore': 'recruit:campus:person:edit',
        # 2026-10-23（聂荣口径）一键成班：属写操作（建班级 + 挂人）→ 走编辑权限码
        'form_classes': 'recruit:campus:person:edit',
    }
    pagination_class = StandardResultsSetPagination
    # 🔴 S5-24（需求 1-2）：行级隔离配置（与 core/entity_scope.py 的
    # ENTITY_SCOPE['campus_person'] 对应，tests/test_entity_scope.py 会断言不漂移）
    # scope_field = head_teacher__department —— 经班主任带出部门
    # （Person.bu 是 CharField choices 非 Department FK，不能直接用作 scope_field）
    scope_field = 'head_teacher__department'
    scope_creator_field = 'created_by'
    data_perm_entity = 'campus_person'

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """R-106 撤销：恢复已软删人员。"""
        # M07 长尾: 原为 self.queryset.model.objects.get(pk=pk) —— 直接走默认
        # manager, 绕过 ViewSet 的 queryset 解析(含任何范围过滤)。改用
        # get_object() 复用 queryset 语义; 未配置写范围时行为不变 (fail-open)。
        instance = self.get_object()
        instance.restore()
        return Response({'success': True, 'id': str(instance.id)})

    @action(detail=True, methods=['get'], url_path='profile')
    def profile(self, request, pk=None):
        """个人档案详情（2026-10-21 二期）。

        一次返回详情弹窗所需的全部聚合：档案基础信息 + 班级（班主任/HRBP/批次）+
        当前轮岗安排 + 轮岗期考核结果 + 四项统计（轮岗均分 / 月度综合均分 /
        综合排名 / 综合评级）。

        口径与聚合逻辑见 `campus_control.person_profile`。
        读操作沿用 `permission_required = 'recruit:campus:person:list'`（V2Permission
        对 GET 直接用声明码，无需在 permission_required_map 中另行登记）。
        """
        person = self.get_object()
        return Response({
            'success': True,
            'data': person_profile.build_person_profile(person),
        })

    @action(detail=False, methods=['post'], url_path='form-classes')
    def form_classes(self, request):
        """一键成班（聂荣 2026-10-23 口径）。

        需求原文：「班级（按照当前批次每30-35人成立一个班级，默认30人成班，
        若剩余人数低于10人则均分至所有班级，超过10人则独立成班，
        若均分后单个班级人数超过35人，则不均分，独立成班）」。

        请求体::

            { "batch": "260701", "dry_run": false }

        - `dry_run=true` → 只算方案不落库（前端「预览成班方案」用）；
        - 已分配班级的人员**不重复分班**（幂等）。

        权限：走 `recruit:campus:person:edit`（写操作：建班级 + 挂人）。
        """
        batch = str(request.data.get('batch') or '').strip()
        if not batch:
            raise DRFValidationError({'batch': ['请指定批次号']})
        dry_run = str(request.data.get('dry_run', '')).strip().lower() in (
            '1', 'true', 'yes',
        )
        try:
            result = class_formation.form_classes_for_batch(batch, dry_run=dry_run)
        except ValueError as exc:
            raise DRFValidationError({'batch': [str(exc)]})
        return Response({'success': True, 'data': result})

    # 整数精确筛的合法集合（防止用户传 ?year=abc 触发 FieldError）
    _SAFE_INT_FILTERS = {'year'}

    def paginate_queryset(self, queryset):
        """分页后按**本页人员**批量聚合轮岗维度指标（2026-10-22 列表新增三列）。

        为什么放这里而不是序列化器里逐行查：逐行查 = 每行 2 次查询（N+1），
        200 行就是 400 次。批量聚合固定 2 次查询，与页大小无关。
        口径见 `campus_control.person_rotation_stats`（与档案详情完全一致）。
        """
        page = super().paginate_queryset(queryset)
        if page is not None:
            self._rotation_stats = person_rotation_stats.build_rotation_stats_map(page)
        return page

    def get_serializer_context(self):
        """把批量聚合结果交给序列化器（列表才有；retrieve 无分页 → 空 map）。"""
        ctx = super().get_serializer_context()
        ctx['rotation_stats'] = getattr(self, '_rotation_stats', None) or {}
        return ctx

    def get_queryset(self):
        qs = Person.objects.all()
        if self.action != 'list':
            return qs
        qs = qs.filter(deleted_at__isnull=True)  # 列表隐藏软删（retrieve/restore 仍可按 id 取）
        params = self.request.query_params

        # 状态过滤（与 staffed 二选一）
        # 2026-10-21 二期：支持多值（逗号分隔）—— 「待入职」页签口径 =
        # 「待入职」为单值状态（2026-10-21 兵哥口径三态收敛），多值写法仍向后兼容。
        status = params.get('status')
        staffed = params.get('staffed')
        if status:
            wanted = [s.strip() for s in str(status).split(',') if s.strip() in STATUS]
            if wanted:
                qs = qs.filter(status__in=wanted)
        elif staffed in ('1', 'true', 'True'):
            qs = qs.filter(status__in=_COUNTED_STATUSES)

        # 适用范围 3 项（bu / position / level）+ 维度 3 项（school / sex / major）
        for f in ('bu', 'position', 'level', 'school', 'sex', 'major'):
            v = params.get(f)
            if v:
                qs = qs.filter(**{f: v})

        # 2026-10-19 S5-10（需求 2-2）：班主任 / 班级 核心筛选
        head_teacher = params.get('head_teacher')
        if head_teacher:
            qs = qs.filter(head_teacher_id=head_teacher)
        class_room = params.get('class_room')
        if class_room:
            qs = qs.filter(class_room_id=class_room)
        # 2026-10-21 二期：导师筛选（档案级带教导师；轮岗期各段导师明细见档案详情）
        mentor = params.get('mentor')
        if mentor:
            qs = qs.filter(mentor_id=mentor)
        # 2026-10-23（聂荣口径）：班长筛选（档案级班长；字段新增于 Person.class_monitor）
        class_monitor = params.get('class_monitor')
        if class_monitor:
            qs = qs.filter(class_monitor_id=class_monitor)
        # 2026-10-23（聂荣口径）：批次筛选
        batch = params.get('batch')
        if batch:
            qs = qs.filter(batch=batch)

        # 2026-10-23（聂荣口径）取数范围：**26 年及以后入职或预计入职**。
        #   「数据范围（26年及以后入职或预计入职数据）」——
        #   ⚠️ 两个日期都空的人员**保留**（无从判定归属年份，宁留勿删；
        #      招聘系统刚认领的档案两个日期都还没有）。
        #   ⚠️ `?entry_scope=all` 显式关闭该过滤（查历史数据 / 编制管控旁路核对用）。
        entry_scope = (params.get('entry_scope') or 'current').strip().lower()
        if entry_scope not in ('all', 'current'):
            entry_scope = 'current'
        if entry_scope == 'current':
            qs = qs.filter(
                Q(expected_entry_date__year__gte=DATA_SCOPE_ENTRY_YEAR_MIN)
                | Q(actual_entry_date__year__gte=DATA_SCOPE_ENTRY_YEAR_MIN)
                | Q(expected_entry_date__isnull=True, actual_entry_date__isnull=True)
            )

        # 2026-10-22：轮岗状态筛选（按人）——该生**存在**处于该阶段的轮岗安排。
        #   口径与 person_rotation_stats.build_rotation_stats_map / person_profile 完全一致：
        #   优先 campus_person（Person 主键 nanoid 口径），回退 person_id（Person.user_id 旧口径）。
        #   两个口径同时命中才算命中，避免筛选结果与列表列显示的轮岗状态对不上。
        #   ⚠️ 非法值按「未过滤」处理（不报错）：下拉只可能给出合法值，
        #   而列表接口对未知查询参数保持宽容，避免手输参数直接把页面打成 400。
        rotation_status = (params.get('rotation_status') or '').strip().upper()
        if rotation_status and rotation_status in person_rotation_stats.STAGE_CODES:
            from apps.campus_rotation.models import RotationArrangement
            arrangements = RotationArrangement.objects.filter(
                stage=rotation_status, deleted_at__isnull=True,
            )
            campus_person_ids = list(
                arrangements.exclude(campus_person_id=None).values_list('campus_person_id', flat=True),
            )
            legacy_user_ids = list(
                arrangements.exclude(person_id=None).values_list('person_id', flat=True),
            )
            qs = qs.filter(Q(id__in=campus_person_ids) | Q(user_id__in=legacy_user_ids))

        # 月份精确匹配
        month = params.get('month')
        if month:
            qs = qs.filter(month=month)

        # 年度过滤：按 expected_entry_date 或 actual_entry_date 的年份（两者任一命中即计入）
        year_raw = params.get('year')
        if year_raw:
            try:
                year_int = int(year_raw)
            except (TypeError, ValueError):
                year_int = None
            if year_int:
                qs = qs.filter(
                    Q(expected_entry_date__year=year_int)
                    | Q(actual_entry_date__year=year_int)
                )

        # 模糊搜索：code 或 name 任一命中
        search = (params.get('search') or '').strip()
        if search:
            qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))

        # 2026-10-22：轮岗维度指标（轮岗状态 / 当前轮岗部门 / 综合评分）**不在此处预取**——
        #   统一由 paginate_queryset 后的 person_rotation_stats.build_rotation_stats_map
        #   按页批量聚合（固定 2 次查询，与页大小无关），结果经 serializer context 下发。
        #   此处再 prefetch 会与批量聚合重复查询，且 to_attr 与聚合口径两套易漂移。

        # 🔴 S5-24（需求 1-2）：行级隔离收口 —— 校招生档案按班主任/班级/HRBP 维度隔离。
        #    scope_field 走 ENTITY_SCOPE['campus_person']（head_teacher__department），
        #    CUSTOM 维度（head_teacher / campus_class / hrbp）走
        #    MODULE_DIMENSION_FIELDS['campus_person']，由管理员在数据权限规则中配置。
        #    口径与 campus_rotation 的三个 ViewSet 一致：行级隔离只作用于 list，
        #    retrieve/update/delete 保持按 id 可取（不因不可见而 404，避免前端
        #    详情页打不开却无法判断原因）。
        return self.scope_queryset(qs)


# ===========================================================================
# 批次规则引擎（契约 §4.2）—— 追加于本文件末尾，不改动上方既有端点
#
# 逆向依据：`docs/03-product/校招生管理_逆向功能清单与差距矩阵_2026-10-23.md`
#   §4.4「批次规则引擎」① 自动命名规则 / ② 批次定义 / ④ 命中统计 / ⑤ 应用
#   算法 A10 批次匹配（区间唯一）/ A11 批次号生成（模板 + 序号按循环粒度归零 + 位宽补零）
#
# 端点（挂既有 `/api/v1/campus/`）：
#   GET/POST/…  /batch-rules/            批次规则 CRUD
#   GET/PUT     /batch-naming/           命名配置（单例）
#   GET         /batch-rules/preview/    实时预览（样例 + 每规则命中人数 + 未命中 + 无批次）
#   POST        /batch-rules/apply/      按规则回写人员批次（只补空值）
#   POST        /batch-rules/recalc/     重算批次号（先预览，body {"apply": true} 才落库）
# ===========================================================================

#: 批次号模板支持的变量（逆向清单 §4.4 ①）
BATCH_TEMPLATE_VARS = ('{YYYY}', '{YY}', '{MM}', '{M}', '{DD}', '{SEQ}', '{N}')

#: 批次规则域权限码（资源码由父会话在 core 迁移统一登记）
PERM_BATCH_RULE_LIST = 'recruit:campus:batch_rule:list'
PERM_BATCH_RULE_CREATE = 'recruit:campus:batch_rule:create'
PERM_BATCH_RULE_EDIT = 'recruit:campus:batch_rule:edit'
PERM_BATCH_RULE_DELETE = 'recruit:campus:batch_rule:delete'
PERM_BATCH_RULE_IMPORT = 'recruit:campus:batch_rule:import'
PERM_BATCH_RULE_SYNC = 'recruit:campus:batch_rule:sync'


def render_batch_no(template, start_date, seq, seq_width):
    """按命名模板渲染批次号（算法 A11）。

    变量口径（逆向清单 §4.4 ①）：
    - `{YYYY}` 四位年 / `{YY}` 两位年 / `{MM}` 两位月 / `{M}` 月（不补零）/ `{DD}` 两位日
    - `{SEQ}` 序号（按 `seq_width` 补零）
    - `{N}` 「第1批」形（取整数序号，**不补零**，含第/批字样）

    ⚠️ 日期部分取**区间起始日**（逆向清单 A11 原文：「批次号 = 命名模板 ＋ 区间起始日 ＋ 批次序号」）。
    """
    if start_date is None:
        return ''
    text = template or ''
    # 替换顺序：长变量在前（{YYYY} 先于 {YY}、{MM} 先于 {M}），否则会被截断匹配
    text = text.replace('{YYYY}', '{:04d}'.format(start_date.year))
    text = text.replace('{YY}', '{:02d}'.format(start_date.year % 100))
    text = text.replace('{MM}', '{:02d}'.format(start_date.month))
    text = text.replace('{M}', str(start_date.month))
    text = text.replace('{DD}', '{:02d}'.format(start_date.day))
    text = text.replace('{SEQ}', str(int(seq)).zfill(int(seq_width or 1)))
    text = text.replace('{N}', '第{}批'.format(int(seq)))
    return text


def batch_cycle_key(start_date, cycle):
    """序号归零粒度的分桶键（逆向清单 §4.4 ①：每月归零 / 每年归零 / 全局递增）。"""
    if cycle == BatchNaming.Cycle.MONTH:
        return (start_date.year, start_date.month)
    if cycle == BatchNaming.Cycle.YEAR:
        return (start_date.year,)
    return ()


def assign_batch_sequences(rules, cycle, seq_start):
    """按 cycle 粒度给批次规则分配序号。

    口径（逆向清单 A11 + 契约 §4.2）：「序号 = seq_start + 计数，宽度 = seq_width 补零」，
    其中**计数 = 该周期内已分配的条数**（0 起）→ 同一周期内的第一条拿到 `seq_start`。

    Args:
        rules: 已按 `sort / start_date / code` 排序的 `BatchRule` 列表（顺序决定序号）。
        cycle: month / year / none。
        seq_start: 序号起始值。

    Returns:
        `{rule_id: seq}`。
    """
    counters = {}
    result = {}
    for rule in rules:
        key = batch_cycle_key(rule.start_date, cycle)
        seq = int(seq_start or 1) + counters.get(key, 0)
        counters[key] = counters.get(key, 0) + 1
        result[rule.id] = seq
    return result


def match_batch_rule(rules, target_date):
    """按日期区间命中批次规则（算法 A10）。

    口径：按 `start_date ≤ 日期 ≤ end_date` 命中；**命中区间必须唯一** ——
    同时命中多条（区间重叠）时返回 None（不归属），避免同一人被两个批次号抢走。
    """
    if target_date is None:
        return None
    hits = [
        rule for rule in rules
        if rule.start_date and rule.end_date and rule.start_date <= target_date <= rule.end_date
    ]
    return hits[0] if len(hits) == 1 else None


def person_batch_date(person, date_field):
    """取人员用于批次归属的判定日期。

    - `entryDate`（入职日期）：实际入职日期优先，回落预计入职日期
      （与 `campus_control.calc._accounting_month` / `Person._entry_date_for_batch()` 同口径）；
    - `hireDate`（录用日期）：本仓人员档案**没有独立的录用日期字段** → 用预计入职日期兜底。
    """
    if date_field == BatchNaming.DateField.HIRE:
        return person.expected_entry_date or person.actual_entry_date
    return person.actual_entry_date or person.expected_entry_date


def _batch_naming_config():
    """取命名配置（单例）；未落库时用模型默认值（**不写库**）。"""
    obj = BatchNaming.objects.first()
    return obj if obj is not None else BatchNaming()


def _enabled_batch_rules():
    """参与命中与编号的批次规则（启用的），顺序 = sort → start_date → code。"""
    return list(
        BatchRule.objects.filter(deleted_at__isnull=True, enabled=True)
        .order_by('sort', 'start_date', 'code')
    )


class BatchRuleViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """批次规则（契约 §4.2 `batch-rules/`）+ 4 个自定义端点。"""

    queryset = BatchRule.objects.all()
    serializer_class = BatchRuleSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_BATCH_RULE_LIST
    permission_required_map = {
        'create': PERM_BATCH_RULE_CREATE,
        'update': PERM_BATCH_RULE_EDIT,
        'partial_update': PERM_BATCH_RULE_EDIT,
        'destroy': PERM_BATCH_RULE_DELETE,
        'restore': PERM_BATCH_RULE_EDIT,
        'preview': PERM_BATCH_RULE_LIST,
        'apply': PERM_BATCH_RULE_IMPORT,
        'recalc': PERM_BATCH_RULE_SYNC,
    }
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = BatchRule.objects.filter(deleted_at__isnull=True)
        params = self.request.query_params
        enabled = params.get('enabled')
        if enabled not in (None, ''):
            qs = qs.filter(enabled=str(enabled).lower() in ('1', 'true', 'yes'))
        code = (params.get('code') or '').strip()
        if code:
            qs = qs.filter(code=code)
        return qs

    # -- 实时预览（逆向清单 §4.4 ①「实时预览」+ ④「命中统计」）--------------
    @action(detail=False, methods=['get'], url_path='preview')
    def preview(self, request):
        """生成样例 + 每规则命中人数 + 未命中人数 + 无批次人数。

        查询参数可临时覆盖命名配置（template / seq_width / seq_start / cycle / date_field），
        不传则用单例配置。
        """
        naming = _batch_naming_config()
        params = request.query_params
        template = params.get('template') or naming.template
        seq_width = int(params.get('seq_width') or naming.seq_width)
        seq_start = int(params.get('seq_start') or naming.seq_start)
        cycle = params.get('cycle') or naming.cycle
        date_field = params.get('date_field') or naming.date_field

        rules = _enabled_batch_rules()
        seqs = assign_batch_sequences(rules, cycle, seq_start)
        generated = {
            rule.id: render_batch_no(template, rule.start_date, seqs[rule.id], seq_width)
            for rule in rules
        }

        from .visibility import visible_persons

        hit_counts = {rule.id: 0 for rule in rules}
        no_date_count = 0
        no_batch_count = 0
        total = 0
        for person in visible_persons(request.user):
            total += 1
            if not person.batch:
                no_batch_count += 1
            target = person_batch_date(person, date_field)
            if target is None:
                no_date_count += 1
                continue
            rule = match_batch_rule(rules, target)
            if rule is None:
                continue
            hit_counts[rule.id] += 1

        hit_total = sum(hit_counts.values())
        samples = [
            {
                'id': rule.id,
                'code': rule.code,
                'name': rule.name,
                'start_date': rule.start_date,
                'end_date': rule.end_date,
                'seq': seqs[rule.id],
                'generated': generated[rule.id],
                'hit_count': hit_counts[rule.id],
            }
            for rule in rules
        ]
        return success_response({
            'template': template,
            'seq_width': seq_width,
            'seq_start': seq_start,
            'cycle': cycle,
            'date_field': date_field,
            'samples': samples,
            'hit_total': hit_total,
            # 未命中人数 = 命中不到任何规则的人数（含无判定日期的人员 —— 同样无法归属）
            'unmatched_count': total - hit_total,
            'no_date_count': no_date_count,
            'no_batch_count': no_batch_count,
            'person_count': total,
        })

    # -- 应用（逆向清单 §4.4 ⑤「按规则回写人员批次」）------------------------
    @action(detail=False, methods=['post'], url_path='apply')
    def apply(self, request):
        """按规则回写人员批次 —— **只补空值**，不覆盖人工填过的批次。"""
        naming = _batch_naming_config()
        rules = _enabled_batch_rules()

        from .visibility import visible_persons

        filled = []
        skipped = 0
        unmatched = 0
        for person in visible_persons(request.user):
            if person.batch:
                # 已有批次值（人工填过 / 已被自动回填）→ 一律不覆盖
                skipped += 1
                continue
            target = person_batch_date(person, naming.date_field)
            rule = match_batch_rule(rules, target)
            if rule is None:
                unmatched += 1
                continue
            person.batch = rule.code
            person.save(update_fields=['batch', 'updated_at'])
            filled.append({
                'person_id': person.id,
                'code': person.code,
                'name': person.name,
                'batch': person.batch,
            })
        return success_response({
            'filled': len(filled),
            'skipped': skipped,
            'unmatched': unmatched,
            'details': filled,
        })

    # -- 重算（逆向清单 §4.4 ⑤「按命名规则重算全部批次号」）------------------
    @action(detail=False, methods=['post'], url_path='recalc')
    def recalc(self, request):
        """按命名规则重算全部批次号，返回「原批次 → 新批次」变更清单。

        ⚠️ **先返回预览，不落库**；body `{"apply": true}` 时才落库
        （落库 = 更新批次规则的批次号 + 同步人员批次）。
        """
        naming = _batch_naming_config()
        rules = _enabled_batch_rules()
        seqs = assign_batch_sequences(rules, naming.cycle, naming.seq_start)
        new_codes = {
            rule.id: render_batch_no(naming.template, rule.start_date, seqs[rule.id], naming.seq_width)
            for rule in rules
        }
        old_to_new = {
            rule.code: new_codes[rule.id]
            for rule in rules
            if rule.code != new_codes[rule.id]
        }

        from .visibility import visible_persons

        person_changes = []
        for person in visible_persons(request.user):
            if person.batch and person.batch in old_to_new:
                person_changes.append({
                    'person_id': person.id,
                    'code': person.code,
                    'name': person.name,
                    'old': person.batch,
                    'new': old_to_new[person.batch],
                })

        per_rule = {}
        for change in person_changes:
            per_rule[change['old']] = per_rule.get(change['old'], 0) + 1
        changes = [
            {
                'id': rule.id,
                'name': rule.name,
                'old': rule.code,
                'new': new_codes[rule.id],
                'person_count': per_rule.get(rule.code, 0),
            }
            for rule in rules
            if rule.code != new_codes[rule.id]
        ]

        apply_flag = bool((request.data or {}).get('apply'))
        if apply_flag:
            with transaction.atomic():
                for rule in rules:
                    if rule.code != new_codes[rule.id]:
                        rule.code = new_codes[rule.id]
                        rule.save(update_fields=['code', 'updated_at'])
                for person in visible_persons(request.user):
                    if person.batch and person.batch in old_to_new:
                        person.batch = old_to_new[person.batch]
                        person.save(update_fields=['batch', 'updated_at'])

        return success_response({
            'applied': apply_flag,
            'changes': changes,
            'person_changes': person_changes,
            'total': len(person_changes),
        })


class BatchNamingViewSet(
    SoftDeleteRestoreMixin, EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet
):
    """批次命名配置（**单例**，契约 §4.2 `batch-naming/`）。

    - `GET /batch-naming/`  → 当前配置（未落库时返回默认值的虚拟对象，不写库）；
    - `PUT /batch-naming/`  → 覆盖配置（存在则覆盖，不存在则新建）。
    """

    queryset = BatchNaming.objects.all()
    serializer_class = BatchNamingSerializer
    permission_classes = [V2Permission]
    permission_required = PERM_BATCH_RULE_LIST
    permission_required_map = {
        'create': PERM_BATCH_RULE_EDIT,
        'update': PERM_BATCH_RULE_EDIT,
        'partial_update': PERM_BATCH_RULE_EDIT,
        'destroy': PERM_BATCH_RULE_EDIT,
        'restore': PERM_BATCH_RULE_EDIT,
    }
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        """单例读取：不存在时返回默认配置（**不落库**，避免 GET 产生副作用）。"""
        obj = BatchNaming.objects.first()
        if obj is None:
            return success_response(BatchNamingSerializer(BatchNaming()).data)
        return success_response(BatchNamingSerializer(obj).data)

    def update(self, request, *args, **kwargs):
        """单例覆盖（PUT）：只覆盖传入的字段，其余保持原值。"""
        obj = BatchNaming.objects.first()
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if obj is None:
            obj = serializer.save(
                created_by=request.user, updated_by=request.user,
            )
        else:
            obj = serializer.save(updated_by=request.user)
        from apps.common.audit_helper import log_action
        log_action(request, 'update', 'BatchNaming', obj.pk)
        return success_response(BatchNamingSerializer(obj).data)
