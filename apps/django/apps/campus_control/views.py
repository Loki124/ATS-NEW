"""人员比例管控系统 — 视图与 API 端点。

端点（均挂在 /api/v1/campus/ 下）：
  GET    /rules/                 规则列表
  POST   /rules/                 新建规则
  GET    /rules/{id}/            规则详情
  PUT    /rules/{id}/            编辑规则
  DELETE /rules/{id}/            删除规则
  GET    /rules/ratio/           实时看板比例（compute_ratio）
  GET    /rules/plan/?month=     人数规划（compute_count + kpi）
  POST   /rules/validate/        录入校验（simulate，服务端重算作为管控依据）
  GET    /persons/               人员列表
  POST   /persons/               新建人员
  GET    /persons/{id}/          人员详情
  PUT    /persons/{id}/          编辑人员
  DELETE /persons/{id}/          删除人员
  POST   /persons/import/        批量导入人员
"""
from decimal import Decimal

from django.db import IntegrityError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination

from .calc import compute_ratio, compute_count, kpi, simulate
from .models import ControlRule, Person
from .serializers import RuleSerializer, PersonSerializer


def _jsonify(obj):
    """递归把 Decimal 转 float，使其可 JSON 序列化。"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


def _rule_to_dict(r):
    return {
        'dim': r.dim, 'group': r.group,
        'target': float(r.target), 'lo': float(r.lo), 'hi': float(r.hi),
        'strength': r.strength,
        'whole': r.whole, 'month_target': r.month_target,
    }


def _person_to_dict(p):
    return {
        'code': p.code, 'name': p.name, 'bu': p.bu, 'school': p.school,
        'sex': p.sex, 'major': p.major, 'month': p.month,
        'status': p.status, 'counted': p.counted,
    }


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
        # 硬删：规则/人员无恢复需求，且避开 unique_together 软删占位陷阱
        instance.delete()


class RuleViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = ControlRule.objects.filter(deleted_at__isnull=True)
    serializer_class = RuleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def _load(self):
        rules = [_rule_to_dict(r) for r in ControlRule.objects.filter(deleted_at__isnull=True)]
        persons = [_person_to_dict(p) for p in Person.objects.filter(deleted_at__isnull=True)]
        return rules, persons

    @action(detail=False, methods=['get'], url_path='ratio')
    def ratio(self, request):
        """实时看板比例（服务端重算）。"""
        rules, persons = self._load()
        result = compute_ratio(persons, rules)
        return Response({'success': True, 'data': _jsonify(result)})

    @action(detail=False, methods=['get'], url_path='plan')
    def plan(self, request):
        """人数规划（按月份） + KPI。"""
        month = request.query_params.get('month')
        if not month:
            return Response({'success': False, 'detail': '缺少 month 参数'}, status=400)
        rules, persons = self._load()
        rows = compute_count(persons, rules, month)
        k = kpi(persons, rules, month)
        return Response({
            'success': True,
            'data': {'rows': _jsonify(rows), 'kpi': _jsonify(k)},
        })

    @action(detail=False, methods=['post'], url_path='validate')
    def validate(self, request):
        """录入校验（simulate，服务端重算作为管控依据）。"""
        draft = request.data or {}
        required = ['bu', 'school', 'sex', 'major']
        missing = [k for k in required if not draft.get(k)]
        if missing:
            return Response(
                {'success': False, 'detail': f'缺少字段：{",".join(missing)}'}, status=400
            )
        rules, persons = self._load()
        result = simulate(draft, rules, persons, month=draft.get('month'))
        return Response({'success': True, 'data': _jsonify(result)})


class PersonViewSet(CampusCRUDMixin, viewsets.ModelViewSet):
    queryset = Person.objects.filter(deleted_at__isnull=True)
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @action(detail=False, methods=['post'], url_path='import')
    def import_persons(self, request):
        """批量导入人员（每行独立校验，错误不中断其余行）。"""
        rows = request.data.get('rows', []) or []
        if not isinstance(rows, list) or not rows:
            return Response({'success': False, 'detail': 'rows 需为非空数组'}, status=400)
        created = []
        errors = []
        for idx, row in enumerate(rows):
            ser = PersonSerializer(data=row)
            if ser.is_valid():
                ser.save(created_by=request.user, updated_by=request.user)
                created.append(ser.instance.code)
            else:
                errors.append({'row': idx, 'errors': ser.errors})
        return Response({
            'success': True,
            'data': {
                'created': created,
                'created_count': len(created),
                'errors': errors,
            },
        })
