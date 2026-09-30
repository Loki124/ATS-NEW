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

from django.db import IntegrityError
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.common.views import EnvelopeWriteMixin
from apps.core.permissions import IsHROrAbove

from .calc import compute_ratio, simulate, _COUNTED_STATUSES
from .constants import STATUS
from .io_indicator import (
    build_indicator_export_workbook, build_indicator_export_csv,
    build_indicator_template_workbook, build_indicator_template_csv,
)
from .io_xlsx import (
    build_export_workbook, build_template_workbook,
)
from .models import (
    ControlDimension, ControlIndicator, ControlRule, Person,
)
from .serializers import (
    ControlDimensionSerializer, ControlIndicatorSerializer,
    ControlRuleSerializer, PersonSerializer,
)
from . import services


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
    """写操作统一兜底：带入当前用户；软删（instance.soft_delete，复用 FullAuditModel.deleted_at）。"""

    def perform_create(self, serializer):
        try:
            serializer.save(created_by=self.request.user, updated_by=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError({'detail': f'数据库约束冲突：{e}'})

    def perform_update(self, serializer):
        try:
            serializer.save(updated_by=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError({'detail': f'数据库约束冲突：{e}'})

    def perform_destroy(self, instance):
        instance.soft_delete()


class ControlDimensionViewSet(EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlDimension.objects.all()
    serializer_class = ControlDimensionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return ControlDimension.objects.filter(deleted_at__isnull=True)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """R-106 撤销：恢复已软删维度。"""
        instance = self.queryset.model.objects.get(pk=pk)
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


class ControlIndicatorViewSet(EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlIndicator.objects.all()
    serializer_class = ControlIndicatorSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = ControlIndicator.objects.filter(deleted_at__isnull=True)
        dim = self.request.query_params.get('dimension')
        if dim:
            qs = qs.filter(dimension_id=dim)
        return qs

    # ---- 权限：导入/导出/模板 需 HR 及以上；其余沿用已认证 ----
    def get_permissions(self):
        if self.action in ('export_indicators', 'template_indicators', 'import_indicators'):
            return [IsHROrAbove()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """R-106 撤销：恢复已软删指标。"""
        instance = self.queryset.model.objects.get(pk=pk)
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


class ControlRuleViewSet(EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlRule.objects.all()
    serializer_class = ControlRuleSerializer
    permission_classes = [IsAuthenticated]
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
        return qs

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """R-106 撤销：恢复已软删规则。"""
        instance = self.queryset.model.objects.get(pk=pk)
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


class PersonViewSet(EnvelopeWriteMixin, CampusCRUDMixin, viewsets.ModelViewSet):
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
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """R-106 撤销：恢复已软删人员。"""
        instance = self.queryset.model.objects.get(pk=pk)
        instance.restore()
        return Response({'success': True, 'id': str(instance.id)})

    # 整数精确筛的合法集合（防止用户传 ?year=abc 触发 FieldError）
    _SAFE_INT_FILTERS = {'year'}

    def get_queryset(self):
        qs = Person.objects.all()
        if self.action != 'list':
            return qs
        qs = qs.filter(deleted_at__isnull=True)  # 列表隐藏软删（retrieve/restore 仍可按 id 取）
        params = self.request.query_params

        # 状态过滤（与 staffed 二选一）
        status = params.get('status')
        staffed = params.get('staffed')
        if status in STATUS:
            qs = qs.filter(status=status)
        elif staffed in ('1', 'true', 'True'):
            qs = qs.filter(status__in=_COUNTED_STATUSES)

        # 适用范围 3 项（bu / position / level）+ 维度 3 项（school / sex / major）
        for f in ('bu', 'position', 'level', 'school', 'sex', 'major'):
            v = params.get(f)
            if v:
                qs = qs.filter(**{f: v})

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
                from django.db.models import Q
                qs = qs.filter(
                    Q(expected_entry_date__year=year_int)
                    | Q(actual_entry_date__year=year_int)
                )

        # 模糊搜索：code 或 name 任一命中
        search = (params.get('search') or '').strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))

        return qs
