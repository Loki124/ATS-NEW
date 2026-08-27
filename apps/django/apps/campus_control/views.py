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
"""
import base64
import json
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsHROrAbove
from apps.audit.models import AuditLog

from .calc import compute_ratio, simulate, check_dimension_sums, _largest_remainder_allocate
from .constants import STRENGTH
from .io_indicator import (
    build_indicator_export_workbook, build_indicator_export_csv,
    build_indicator_template_workbook, build_indicator_template_csv,
    build_indicator_error_report_workbook, build_indicator_error_report_csv,
    parse_indicator_file, _parse_bool,
)
from .io_xlsx import (
    build_export_workbook, build_template_workbook, parse_import_workbook,
    build_error_report_workbook,
)
from .models import (
    ControlDimension, ControlIndicator, ControlRule, Person,
)
from .serializers import (
    ControlDimensionSerializer, ControlIndicatorSerializer,
    ControlRuleSerializer, PersonSerializer, _to_decimal,
)
from . import services


def _scope_mutex_guard(dimension, year, bu, position, level, exclude_scope=None):
    """「全局 / 指定范围」非对称互斥守卫（set_rules 与所有导入入口共用）。

    同一 (dimension, year) 下不可同时持有「全局」与「指定范围」规则集（否则 calc 重复计数）。
    非对称策略（按产品澄清「只删全局、其他指定范围不动」）：
      - 保存/导入【指定范围】→ 删除该维度年度下的【全局】规则，其余指定范围保留；
      - 保存/导入【全局】→ 若存在其他指定范围规则则【拦截 400】，避免静默清空。

    入参 exclude_scope: (bu, position, level, year) 元组，重定位时排除原 scope。
    返回 None 表示放行（已执行必要的删除）；返回 Response 表示拦截。
    """
    if bu or position or level:
        # 指定范围：删除全局规则（其他指定范围保留）
        ControlRule.objects.filter(
            dimension=dimension, year=year,
            bu='', position='', level='',
        ).delete()
        return None
    # 全局：若存在其他指定范围规则则拦截
    specified_qs = ControlRule.objects.filter(
        dimension=dimension, year=year,
    ).exclude(bu='', position='', level='')
    if exclude_scope is not None:
        ebu, epos, elev, eyear = exclude_scope
        specified_qs = specified_qs.exclude(bu=ebu, position=epos, level=elev, year=eyear)
    if specified_qs.exists():
        return Response(
            {'success': False, 'detail': '该维度年度下已存在其他指定范围规则集，保存全局会清空这些指定范围，请先删除指定范围或改用指定范围保存。'},
            status=400,
        )
    return None


def _jsonify(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


def _normalize_monthly_targets(raw, annual, indicator_name):
    """校验并返回 12 个月度目标数组。annual 为该指标年度管控人数（由调用方分配好，含最大余数法结果）。"""
    annual = int(annual)
    if raw is None:
        # 未传则均分年度目标
        base = annual // 12
        rem = annual - base * 12
        return [base + (1 if i < rem else 0) for i in range(12)]
    if not isinstance(raw, list) or len(raw) != 12:
        return Response(
            {'success': False, 'detail': f'指标 {indicator_name} 的 monthly_targets 须为长度 12 的数组'},
            status=400,
        )
    try:
        monthly = [int(v) for v in raw]
    except (TypeError, ValueError):
        return Response(
            {'success': False, 'detail': f'指标 {indicator_name} 的 monthly_targets 每项须为整数'},
            status=400,
        )
    if any(v < 0 for v in monthly):
        return Response(
            {'success': False, 'detail': f'指标 {indicator_name} 的月度目标不能为负数'},
            status=400,
        )
    if sum(monthly) != annual:
        return Response(
            {
                'success': False,
                'detail': (
                    f'指标 {indicator_name} 的 12 个月度目标之和({sum(monthly)})'
                    f'须等于年度目标({annual})'
                ),
            },
            status=400,
        )
    return monthly


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
    """写操作统一兜底：带入当前用户；硬删（instance.delete）。"""

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
        instance.delete()


class ControlDimensionViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlDimension.objects.all()
    serializer_class = ControlDimensionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def _log_rule_audit(self, action, detail, entity_id=None):
        """规则类写操作审计（清空/保存维度规则集等）。审计失败不阻断主流程。"""
        try:
            AuditLog.objects.create(
                user=self.request.user,
                action=action,
                entity='ControlRule',
                entity_id=entity_id,
                new_value=detail[:1000],
                ip=self.request.META.get('REMOTE_ADDR') or '',
                user_agent=(self.request.META.get('HTTP_USER_AGENT') or '')[:500],
            )
        except Exception:  # noqa: BLE001 - 审计失败不应阻断主流程
            pass

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
        bu = request.data.get('bu', '') or ''
        position = request.data.get('position', '') or ''
        level = request.data.get('level', '') or ''
        year_in = request.data.get('year')
        rules_in = request.data.get('rules')
        total_target_in = request.data.get('total_target')

        try:
            year = int(year_in)
        except (TypeError, ValueError):
            return Response({'success': False, 'detail': 'year 必填且为整数'}, status=400)
        if not isinstance(rules_in, list):
            return Response({'success': False, 'detail': 'rules 须为数组'}, status=400)

        # ---- G5 清空分支：空 rules 数组 = 显式清空该 (适用范围, 维度, 年度) 规则集 ----
        if rules_in == []:
            original_in = request.data.get('original')
            obu = opos = olev = ''
            oyear = year
            if isinstance(original_in, dict):
                obu = original_in.get('bu', '') or ''
                opos = original_in.get('position', '') or ''
                olev = original_in.get('level', '') or ''
                try:
                    oyear = int(original_in.get('year', year))
                except (TypeError, ValueError):
                    return Response({'success': False, 'detail': 'original.year 须为整数'}, status=400)
            if (obu or opos or olev) and (obu != bu or opos != position or olev != level or oyear != year):
                ControlRule.objects.filter(
                    bu=obu, position=opos, level=olev, dimension=dimension, year=oyear
                ).delete()
            deleted = ControlRule.objects.filter(
                bu=bu, position=position, level=level, dimension=dimension, year=year
            ).delete()
            self._log_rule_audit(
                'DELETE',
                f'清空维度「{dimension.name}」{year}年 适用范围[{bu}/{position}/{level}] 规则集（{deleted[0]} 条）',
            )
            return Response({'success': True, 'data': {'saved': 0, 'cleared': True}})

        total = Decimal('0')
        prepared = []
        seen = set()
        existing_by_ind = {
            r.indicator_id: r
            for r in ControlRule.objects.filter(
                bu=bu, position=position, level=level, dimension=dimension, year=year
            )
        }
        for r in rules_in:
            if not isinstance(r, dict):
                return Response({'success': False, 'detail': 'rules 项须为对象'}, status=400)
            indicator_id = r.get('indicator')
            if indicator_id in seen:
                return Response({'success': False, 'detail': f'指标 {indicator_id} 重复提交'}, status=400)
            seen.add(indicator_id)
            indicator = ControlIndicator.objects.filter(pk=indicator_id, dimension_id=dimension.id).first()
            if not indicator:
                return Response({'success': False, 'detail': f'指标 {indicator_id} 不属于该维度'}, status=400)
            target = _to_decimal(r.get('target'))
            strength = r.get('strength', '硬约束')
            if target is None:
                return Response({'success': False, 'detail': f'指标 {indicator.name} 目标占比必填且为数值'}, status=400)
            if not (Decimal('0') <= target <= Decimal('1')):
                return Response({'success': False, 'detail': f'指标 {indicator.name} 目标占比须满足 0<=目标<=1'}, status=400)
            if strength not in STRENGTH:
                return Response({'success': False, 'detail': f'控制强度非法：{strength}'}, status=400)

            # 年度/月度目标解析（成对可选）
            # 注意：djangorestframework-camel-case parser 已把前端 camelCase 转换为 snake_case，
            # 后端需用 snake_case 读取（annual_target / monthly_targets）。
            annual_in = r.get('annual_target', None)
            monthly_in = r.get('monthly_targets', None)
            if (annual_in is None) != (monthly_in is None):
                return Response({
                    'success': False,
                    'detail': f'指标 {indicator.name} 的 annual_target 与 monthly_targets 必须同时传入或不传',
                }, status=400)
            if annual_in is None:
                # 从旧规则继承
                old = existing_by_ind.get(indicator.id)
                annual_target = int(old.annual_target) if old else 0
                if old and isinstance(old.monthly_targets, (list, tuple)):
                    monthly_targets = [int(v) for v in old.monthly_targets]
                else:
                    monthly_targets = [0] * 12
            else:
                # 前端传入，做严格校验
                try:
                    annual_target = int(annual_in)
                except (TypeError, ValueError):
                    return Response({
                        'success': False,
                        'detail': f'指标 {indicator.name} 的 annual_target 须为整数',
                    }, status=400)
                if annual_target < 0:
                    return Response({
                        'success': False,
                        'detail': f'指标 {indicator.name} 的 annual_target 不能为负数',
                    }, status=400)
                if not isinstance(monthly_in, list) or len(monthly_in) != 12:
                    return Response({
                        'success': False,
                        'detail': f'指标 {indicator.name} 的 monthly_targets 须为长度 12 的数组',
                    }, status=400)
                try:
                    monthly_targets = [int(v) for v in monthly_in]
                except (TypeError, ValueError):
                    return Response({
                        'success': False,
                        'detail': f'指标 {indicator.name} 的 monthly_targets 每项须为整数',
                    }, status=400)
                if any(v < 0 for v in monthly_targets):
                    return Response({
                        'success': False,
                        'detail': f'指标 {indicator.name} 的 monthly_targets 不能为负数',
                    }, status=400)
                if sum(monthly_targets) != annual_target:
                    return Response({
                        'success': False,
                        'detail': (
                            f'指标 {indicator.name} 的 12 个月度之和({sum(monthly_targets)})'
                            f'须等于 annual_target({annual_target})'
                        ),
                    }, status=400)

            total += target
            prepared.append((indicator, target, strength, annual_target, monthly_targets))

        if abs(total - Decimal('1')) > Decimal('0.0001'):
            pct = (total * 100).quantize(Decimal('0.01'))
            return Response({
                'success': False,
                'detail': f'该适用范围下此维度指标目标占比之和须为 100%，当前为 {pct}%',
            }, status=400)

        # ---- G7-② 年度人数加和硬拦 ----
        # 前端传入 totalTarget 时，Σ(各规则 annual_target) 必须 == totalTarget，否则 400（不允许加和不一致的脏数据入库）。
        if total_target_in is not None:
            try:
                total_target_val = int(total_target_in)
            except (TypeError, ValueError):
                return Response({'success': False, 'detail': 'totalTarget 须为非负整数'}, status=400)
            if total_target_val < 0:
                return Response({'success': False, 'detail': 'totalTarget 不能为负数'}, status=400)
            annual_sum = sum(p[3] for p in prepared)
            if annual_sum != total_target_val:
                return Response({
                    'success': False,
                    'detail': (
                        f'各指标年度管控人数加和({annual_sum})'
                        f'须等于「维度年度管控人数」({total_target_val})'
                    ),
                }, status=400)

        # ---- 「重定位」支持：编辑态下适用范围被改 ----
        # original 为编辑打开时的原适用范围快照；若与当前 scope 不同，则删除原 scope 规则集、在新 scope 重建。
        # 目标 scope 已存在规则集 → 冲突拦截（避免覆盖）。
        relocate = False
        obu = opos = olev = ''
        oyear = year
        original_in = request.data.get('original')
        if isinstance(original_in, dict):
            obu = original_in.get('bu', '') or ''
            opos = original_in.get('position', '') or ''
            olev = original_in.get('level', '') or ''
            try:
                oyear = int(original_in.get('year', year))
            except (TypeError, ValueError):
                return Response({'success': False, 'detail': 'original.year 须为整数'}, status=400)
            relocate = (obu != bu or opos != position or olev != level or oyear != year)

        # ---- 「全局 / 指定范围」互斥（非对称，守卫统一处理） ----
        _block = _scope_mutex_guard(
            dimension, year, bu, position, level,
            exclude_scope=(obu, opos, olev, oyear) if relocate else None,
        )
        if isinstance(_block, Response):
            return _block

        with transaction.atomic():
            if relocate:
                # 重定位：先删原 scope 规则集（同事务原子，失败整体回滚）
                ControlRule.objects.filter(
                    bu=obu, position=opos, level=olev, dimension=dimension, year=oyear
                ).delete()
            ControlRule.objects.filter(
                bu=bu, position=position, level=level, dimension=dimension, year=year
            ).delete()
            for indicator, target, strength, annual_target, monthly_targets in prepared:
                ControlRule.objects.create(
                    bu=bu, position=position, level=level, dimension=dimension, indicator=indicator,
                    year=year, target=target, strength=strength,
                    annual_target=annual_target, monthly_targets=monthly_targets,
                    created_by=request.user, updated_by=request.user,
                )
        return Response({'success': True, 'data': {'saved': len(prepared)}})


class ControlIndicatorViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlIndicator.objects.all()
    serializer_class = ControlIndicatorSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = ControlIndicator.objects.all()
        dim = self.request.query_params.get('dimension')
        if dim:
            qs = qs.filter(dimension_id=dim)
        return qs

    # ---- 权限：导入/导出/模板 需 HR 及以上；其余沿用已认证 ----
    def get_permissions(self):
        if self.action in ('export_indicators', 'template_indicators', 'import_indicators'):
            return [IsHROrAbove()]
        return [IsAuthenticated()]

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
        self._log_indicator_audit('EXPORT', f'导出指标 {len(rows)} 条（{fmt}）')
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
        self._log_indicator_audit('EXPORT', f'下载指标导入模板（{fmt}）')
        return resp

    @action(detail=False, methods=['post'], url_path='import')
    def import_indicators(self, request):
        """批量导入指标：数据校验 + 重复项处理（mode=skip|update|error）。

        校验：维度须存在；指标名称非空且 ≤32；是否启用须可解析；文件内同 (维度,指标名称) 不可重复。
        与库内重复按 mode 处理：skip=跳过 / update=更新 is_active / error=整批拒绝（原子回滚）。
        任一硬校验错误 → 整体 400 并附错误报告（xlsx，base64）。
        """
        f = request.FILES.get('file')
        if not f:
            return Response({'success': False, 'detail': '缺少 file 文件字段'}, status=400)
        mode = (request.data.get('mode') or request.query_params.get('mode') or 'skip').strip().lower()
        if mode not in ('skip', 'update', 'error'):
            return Response({'success': False, 'detail': 'mode 仅支持 skip / update / error'}, status=400)

        rows, parse_errors, original_rows, errors_by_line = parse_indicator_file(f)

        if parse_errors:
            return Response(
                {'success': False, 'data': self._indicator_error_payload(parse_errors, {}, [], f.name)},
                status=400,
            )
        if not rows:
            return Response(
                {'success': False, 'data': self._indicator_error_payload(['文件中未解析到任何有效指标行'], {}, [], f.name)},
                status=400,
            )

        # 预构建维度映射，避免逐行查库
        dim_map = {d.name: d for d in ControlDimension.objects.all()}

        seen_in_file = {}
        for rec in rows:
            line = rec['line']
            dim_name = rec['dimension_name']
            name = rec['name']
            dimension = dim_map.get(dim_name)
            if dimension is None:
                errors_by_line[line] = f'维度「{dim_name}」不存在'
                continue
            if not name:
                errors_by_line[line] = '指标名称为空'
                continue
            if len(name) > 32:
                errors_by_line[line] = f'指标名称过长（须 ≤32，当前 {len(name)}）'
                continue
            is_active = _parse_bool(rec['is_active_raw'])
            if is_active is None:
                errors_by_line[line] = f'是否启用非法：{rec["is_active_raw"]!r}（填写 是/否/true/false/1/0）'
                continue
            key = (dimension.id, name)
            if key in seen_in_file:
                errors_by_line[line] = f'与第 {seen_in_file[key]} 行重复（同维度同指标名称）'
                continue
            seen_in_file[key] = line
            existing = ControlIndicator.objects.filter(dimension=dimension, name=name).first()
            if existing and mode == 'error':
                errors_by_line[line] = f'指标「{dim_name}/{name}」已存在，mode=error 拒绝导入'

        if errors_by_line:
            return Response(
                {'success': False, 'data': self._indicator_error_payload([], errors_by_line, original_rows, f.name)},
                status=400,
            )

        # 第二遍：写库（此阶段已无硬错误）
        created = updated = skipped = 0
        with transaction.atomic():
            for rec in rows:
                dimension = dim_map[rec['dimension_name']]
                name = rec['name']
                is_active = _parse_bool(rec['is_active_raw'])
                existing = ControlIndicator.objects.filter(dimension=dimension, name=name).first()
                if existing:
                    if mode == 'skip':
                        skipped += 1
                        continue
                    existing.is_active = is_active
                    existing.updated_by = request.user
                    existing.save(update_fields=['is_active', 'updated_by'])
                    updated += 1
                    continue
                ControlIndicator.objects.create(
                    dimension=dimension, name=name, is_active=is_active,
                    created_by=request.user, updated_by=request.user,
                )
                created += 1

        action = 'CREATE' if created else ('UPDATE' if updated else 'READ')
        detail = f'导入指标完成：新建 {created} / 更新 {updated} / 跳过 {skipped}（mode={mode}）'
        self._log_indicator_audit(action, detail)
        return Response({
            'success': True,
            'data': {'created': created, 'updated': updated, 'skipped': skipped, 'failed': 0, 'errors': []},
        })

    def _indicator_error_payload(self, parse_errors, errors_by_line, original_rows, filename=''):
        """构造失败响应 data：融合错误文本 + xlsx 错误报告（base64）。"""
        errs = list(parse_errors) + [f'第 {ln} 行：{msg}' for ln, msg in sorted(errors_by_line.items())]
        payload = {
            'created': 0, 'updated': 0, 'skipped': 0, 'failed': len(errs),
            'errors': errs, 'error_file': None,
        }
        if original_rows:
            try:
                buf = BytesIO()
                wb = build_indicator_error_report_workbook(original_rows, errors_by_line)
                wb.save(buf)
                payload['error_file'] = base64.b64encode(buf.getvalue()).decode('ascii')
            except Exception:  # noqa: BLE001 - 报告生成失败不影响主错误返回
                payload['error_file'] = None
        return payload

    def _log_indicator_audit(self, action, detail, entity_id=None):
        try:
            AuditLog.objects.create(
                user=self.request.user,
                action=action,
                entity='ControlIndicator',
                entity_id=entity_id,
                new_value=detail[:1000],
                ip=self.request.META.get('REMOTE_ADDR') or '',
                user_agent=(self.request.META.get('HTTP_USER_AGENT') or '')[:500],
            )
        except Exception:  # noqa: BLE001 - 审计失败不应阻断主流程
            pass


class ControlRuleViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlRule.objects.all()
    serializer_class = ControlRuleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = ControlRule.objects.all()
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

    @action(detail=False, methods=['get'], url_path='ratio')
    def ratio(self, request):
        """实时看板：展示全部规则（每条按自身适用范围独立计算）+ 各(适用范围,年度)的 100% 加和。"""
        rules = [_rule_to_dict(r) for r in ControlRule.objects.all()]
        dim_map = _build_person_dim_map()
        persons = [_person_to_dict(p, dim_map) for p in Person.objects.all()]
        result = compute_ratio(persons, rules)
        sums = []
        seen = set()
        for r in rules:
            sk = (r['bu'], r['position'], r['level'])
            yk = (sk, r.get('year'))
            if yk in seen:
                continue
            seen.add(yk)
            for s in check_dimension_sums(rules, sk, r.get('year')):
                sums.append({'bu': sk[0], 'position': sk[1], 'level': sk[2], 'year': r.get('year'), **s})
        return Response({
            'success': True,
            'data': {
                'total': result['total'],
                'rows': _jsonify(result['rows']),
                'sumChecks': _jsonify(sums),
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
        bu = request.data.get('bu', '') or ''
        position = request.data.get('position', '') or ''
        level = request.data.get('level', '') or ''
        dimension_id = request.data.get('dimension')
        year = int(request.data.get('year') or 2026)
        rules = request.data.get('rules')
        if not dimension_id:
            return Response({'success': False, 'detail': '缺少 dimension 参数'}, status=400)
        dimension = ControlDimension.objects.filter(pk=dimension_id).first()
        if not dimension:
            return Response({'success': False, 'detail': '维度不存在'}, status=404)
        if not isinstance(rules, list) or not rules:
            return Response({'success': False, 'detail': 'rules 不能为空'}, status=400)

        total = Decimal('0')
        prepared = []
        seen = set()
        for r in rules:
            if not isinstance(r, dict):
                return Response({'success': False, 'detail': 'rules 项须为对象'}, status=400)
            indicator_id = r.get('indicator')
            indicator = ControlIndicator.objects.filter(pk=indicator_id, dimension_id=dimension_id).first()
            if not indicator:
                return Response({'success': False, 'detail': f'指标 {indicator_id} 不属于该维度'}, status=400)
            if indicator_id in seen:
                return Response({'success': False, 'detail': f'指标 {indicator.name} 重复提交'}, status=400)
            target = _to_decimal(r.get('target'))
            strength = r.get('strength', '硬约束')
            if target is None:
                return Response({'success': False, 'detail': f'指标 {indicator.name} 目标占比必填且为数值'}, status=400)
            if not (Decimal('0') <= target <= Decimal('1')):
                return Response({'success': False, 'detail': f'指标 {indicator.name} 目标占比须满足 0<=目标<=1'}, status=400)
            if strength not in STRENGTH:
                return Response({'success': False, 'detail': f'控制强度非法：{strength}'}, status=400)
            total += target
            prepared.append((indicator, target, strength))
            seen.add(indicator_id)

        if abs(total - Decimal('1')) > Decimal('0.0001'):
            pct = (total * 100).quantize(Decimal('0.01'))
            return Response({
                'success': False,
                'detail': f'该适用范围下此维度指标目标占比之和须为 100%，当前为 {pct}%',
            }, status=400)

        # ---- 「全局 / 指定范围」互斥（非对称，与 set_rules 一致） ----
        _block = _scope_mutex_guard(dimension, year, bu, position, level)
        if isinstance(_block, Response):
            return _block

        with transaction.atomic():
            ControlRule.objects.filter(bu=bu, position=position, level=level, dimension=dimension, year=year).delete()
            for indicator, target, strength in prepared:
                ControlRule.objects.create(
                    bu=bu, position=position, level=level, dimension=dimension, indicator=indicator,
                    year=year, target=target, strength=strength,
                    created_by=request.user, updated_by=request.user,
                )
        return Response({'success': True, 'data': {'saved': len(prepared)}})

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
        bu = request.data.get('bu', '') or ''
        position = request.data.get('position', '') or ''
        level = request.data.get('level', '') or ''
        dimension_id = request.data.get('dimension')
        year_in = request.data.get('year')
        total_target_in = request.data.get('total_target')
        rules_in = request.data.get('rules')

        if not dimension_id:
            return Response({'success': False, 'detail': '缺少 dimension 参数'}, status=400)
        dimension = ControlDimension.objects.filter(pk=dimension_id).first()
        if not dimension:
            return Response({'success': False, 'detail': '维度不存在'}, status=404)
        try:
            year = int(year_in)
        except (TypeError, ValueError):
            return Response({'success': False, 'detail': 'year 必填且为整数'}, status=400)
        try:
            total_target = int(total_target_in)
        except (TypeError, ValueError):
            return Response({'success': False, 'detail': 'totalTarget 必填且为非负整数'}, status=400)
        if total_target < 0:
            return Response({'success': False, 'detail': 'totalTarget 不能为负数'}, status=400)
        if not isinstance(rules_in, list) or not rules_in:
            return Response({'success': False, 'detail': 'rules 不能为空'}, status=400)

        total = Decimal('0')
        prepared = []   # (indicator, target, strength, raw_monthly)
        weights = []    # 各指标占比（和须=1），用于最大余数法分配 annual_target
        seen = set()
        for r in rules_in:
            if not isinstance(r, dict):
                return Response({'success': False, 'detail': 'rules 项须为对象'}, status=400)
            indicator_id = r.get('indicator')
            if indicator_id in seen:
                return Response({'success': False, 'detail': f'指标 {indicator_id} 重复提交'}, status=400)
            seen.add(indicator_id)
            indicator = ControlIndicator.objects.filter(pk=indicator_id, dimension_id=dimension_id).first()
            if not indicator:
                return Response({'success': False, 'detail': f'指标 {indicator_id} 不属于该维度'}, status=400)
            target = _to_decimal(r.get('target'))
            strength = r.get('strength', '硬约束')
            if target is None:
                return Response({'success': False, 'detail': f'指标 {indicator.name} 目标占比必填且为数值'}, status=400)
            if not (Decimal('0') <= target <= Decimal('1')):
                return Response({'success': False, 'detail': f'指标 {indicator.name} 目标占比须满足 0<=目标<=1'}, status=400)
            if strength not in STRENGTH:
                return Response({'success': False, 'detail': f'指标 {indicator.name} 控制强度非法'}, status=400)
            total += target
            prepared.append((indicator, target, strength, r.get('monthly_targets')))
            weights.append(float(target))

        if abs(total - Decimal('1')) > Decimal('0.0001'):
            pct = (total * 100).quantize(Decimal('0.01'))
            return Response({
                'success': False,
                'detail': f'该维度下所有指标目标占比之和须为 100%，当前为 {pct}%',
            }, status=400)

        # 最大余数法：把维度总人数精确分配为各指标 annual_target，保证 Σannual == total_target
        annuals = _largest_remainder_allocate(total_target, weights)

        # 逐指标校验/归一化月度目标（annual 已分配好）
        monthly_by_idx = []
        for i, (indicator, target, strength, raw_monthly) in enumerate(prepared):
            monthly = _normalize_monthly_targets(raw_monthly, annuals[i], indicator.name)
            if isinstance(monthly, Response):
                return monthly
            monthly_by_idx.append(monthly)

        # ---- 「全局 / 指定范围」互斥（非对称，与 set_rules 一致） ----
        _block = _scope_mutex_guard(dimension, year, bu, position, level)
        if isinstance(_block, Response):
            return _block

        with transaction.atomic():
            # 删除该 (适用范围, 维度, 年度) 旧规则
            ControlRule.objects.filter(bu=bu, position=position, level=level, dimension=dimension, year=year).delete()
            for i, (indicator, target, strength, _raw) in enumerate(prepared):
                ControlRule.objects.create(
                    bu=bu, position=position, level=level, dimension=dimension, indicator=indicator,
                    year=year, target=target, strength=strength,
                    annual_target=annuals[i], monthly_targets=monthly_by_idx[i],
                    created_by=request.user, updated_by=request.user,
                )
        return Response({
            'success': True,
            'data': {'saved': len(prepared), 'totalTarget': total_target, 'year': year},
        })

    @action(detail=False, methods=['get'], url_path='export')
    def export_xlsx(self, request):
        """导出全部规则为 xlsx（列结构与导入模板一致）。"""
        rules = [_rule_to_dict(r) for r in ControlRule.objects.all().order_by(
            'bu', 'position', 'level', 'dimension__name', 'indicator__name', 'year'
        )]
        wb = build_export_workbook(rules)
        from io import BytesIO
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        from django.http import HttpResponse
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
        from io import BytesIO
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        from django.http import HttpResponse
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
        if not f:
            return Response({'success': False, 'detail': '缺少 file 文件字段'}, status=400)
        if not f.name.lower().endswith(('.xlsx', '.xlsm')):
            return Response({'success': False, 'detail': '仅支持 .xlsx 文件'}, status=400)

        try:
            groups, parse_errors, original_rows, errors_by_line = parse_import_workbook(f)
        except Exception as e:  # noqa: BLE001 - 解析异常统一返回
            return Response({'success': False, 'detail': f'文件解析失败：{e}'}, status=400)

        def _error_payload(extra_errors):
            """构造失败响应：除 errors 文本列表外，附融合后的错误报告 xlsx（base64）。"""
            errs = list(parse_errors) + list(extra_errors)
            payload = {'groups': 0, 'saved_rules': 0, 'errors': errs, 'error_file': None}
            if original_rows:
                try:
                    from io import BytesIO
                    import base64
                    wb = build_error_report_workbook(original_rows, errors_by_line)
                    buf = BytesIO()
                    wb.save(buf)
                    payload['error_file'] = base64.b64encode(buf.getvalue()).decode('ascii')
                except Exception:  # noqa: BLE001 - 报告生成失败不影响主错误返回
                    payload['error_file'] = None
            return payload

        if parse_errors:
            return Response({
                'success': False,
                'data': _error_payload([]),
            }, status=400)

        if not groups:
            return Response({
                'success': False,
                'data': _error_payload(['文件中未解析到任何有效规则行']),
            }, status=400)

        saved_rules = 0
        group_errors = []
        for g in groups:
            ok, msg, n = self._import_group(g, request.user)
            if not ok:
                group_errors.append(msg)
            else:
                saved_rules += n

        if group_errors:
            return Response({
                'success': False,
                'data': _error_payload(group_errors),
            }, status=400)

        return Response({
            'success': True,
            'data': {'groups': len(groups), 'saved_rules': saved_rules, 'errors': []},
        })

    def _import_group(self, g, user):
        """导入单个 (适用范围, 维度, 年度) 组，事务原子替换。返回 (ok, msg, saved_count)。"""
        bu = g.get('bu', '') or ''
        position = g.get('position', '') or ''
        level = g.get('level', '') or ''
        dimension_name = g.get('dimension')
        year = int(g.get('year') or 2026)
        rules_in = g.get('rules') or []

        dimension = ControlDimension.objects.filter(name=dimension_name).first()
        if not dimension:
            return False, f'组[{dimension_name}]：维度不存在', 0

        total = Decimal('0')
        prepared = []
        seen = set()
        for r in rules_in:
            indicator_name = r.get('indicator')
            if indicator_name in seen:
                return False, f'组[{dimension_name}]：指标「{indicator_name}」重复', 0
            seen.add(indicator_name)
            indicator = ControlIndicator.objects.filter(name=indicator_name, dimension=dimension, is_active=True).first()
            if not indicator:
                return False, f'组[{dimension_name}]：指标「{indicator_name}」不属于该维度或未启用', 0
            target = _to_decimal(r.get('target'))
            if target is None:
                return False, f'组[{dimension_name}]：指标「{indicator_name}」目标占比非法', 0
            if not (Decimal('0') <= target <= Decimal('1')):
                return False, f'组[{dimension_name}]：指标「{indicator_name}」目标占比须 0~1', 0
            strength = r.get('strength', '硬约束')
            if strength not in STRENGTH:
                return False, f'组[{dimension_name}]：控制强度非法：{strength}', 0
            monthly = r.get('monthly_targets') or [0] * 12
            if len(monthly) != 12:
                return False, f'组[{dimension_name}]：指标「{indicator_name}」月度目标须为长度 12', 0
            if any(v < 0 for v in monthly):
                return False, f'组[{dimension_name}]：指标「{indicator_name}」月度目标不能为负', 0
            total += target
            prepared.append((indicator, target, strength, monthly))

        if abs(total - Decimal('1')) > Decimal('0.0001'):
            pct = (total * 100).quantize(Decimal('0.01'))
            return False, f'组[{dimension_name}]：目标占比之和须=100%，当前 {pct}%', 0

        # ---- 「全局 / 指定范围」互斥（非对称，与 set_rules 一致） ----
        _block = _scope_mutex_guard(dimension, year, bu, position, level)
        if isinstance(_block, Response):
            return False, _block.data.get('detail', '适用范围互斥冲突'), 0

        with transaction.atomic():
            ControlRule.objects.filter(bu=bu, position=position, level=level, dimension=dimension, year=year).delete()
            for indicator, target, strength, monthly in prepared:
                annual = int((Decimal(str(g.get('total_target', 0))) * target).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
                ControlRule.objects.create(
                    bu=bu, position=position, level=level, dimension=dimension, indicator=indicator,
                    year=year, target=target, strength=strength,
                    annual_target=annual, monthly_targets=monthly,
                    created_by=user, updated_by=user,
                )
        return True, '', len(prepared)


class PersonViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    """人员主数据 CRUD（全局主数据，一行一人；counted 控制是否计入核算）。"""

    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
