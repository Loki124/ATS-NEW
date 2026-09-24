"""校招专属功能视图（校园大使 + 宣讲会 + 模块配置）。

端点（挂在 /api/v1/campus-recruit/ 下）：
  GET    /ambassadors/              校园大使列表（按 recruit_type=campus 硬分区）
  POST   /ambassadors/              新建
  GET/PUT/DELETE /ambassadors/{id}/
  POST   /ambassadors/{id}/restore/ 恢复已软删大使
  GET/PUT /ambassadors/config/      模块启用开关（key=ambassador）

  GET    /sessions/                 宣讲会列表
  POST   /sessions/                 新建
  GET/PUT/DELETE /sessions/{id}/
  POST   /sessions/{id}/restore/    恢复已软删宣讲会
  GET/PUT /sessions/config/         模块启用开关（key=session）
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions_v2 import ScopeQuerysetMixin
from apps.reason_library.models import RecruitType

from .models import CampusAmbassador, CampusModuleConfig, CampusSession
from .serializers import CampusAmbassadorSerializer, CampusSessionSerializer


class CampusModelViewSetMixin(ScopeQuerysetMixin):
    """校招专属模型通用基类：

    - recruit_type 硬分区（来自 ScopeQuerysetMixin：读侧过滤 + 写侧权威注入）；
    - 软删（FullAuditModel.deleted_at）+ 审计字段（created_by/updated_by）注入；
    - 列表默认隐藏软删行。
    """

    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = self.queryset.model.objects.filter(deleted_at__isnull=True)
        qs = self.scope_queryset(qs)
        return qs

    def _rt_value(self):
        return getattr(self.request, 'recruit_type', RecruitType.CAMPUS.value)

    def _audit_kwargs(self, serializer, fields):
        """仅注入模型真实拥有的审计字段（复用 AuditMixin 的健壮判定，避免对非审计模型 500）。"""
        model_cls = getattr(getattr(serializer, 'Meta', None), 'model', None)
        if model_cls is None and self.queryset is not None:
            model_cls = self.queryset.model
        if model_cls is None:
            return {}
        concrete = {f.name for f in model_cls._meta.concrete_fields}
        user = self.request.user
        return {name: user for name in fields if name in concrete}

    def perform_create(self, serializer):
        kwargs = {}
        rt = self._rt_field()
        if rt:
            kwargs[rt] = self._rt_value()
        kwargs.update(self._audit_kwargs(serializer, ['created_by', 'updated_by']))
        serializer.save(**kwargs)

    def perform_update(self, serializer):
        kwargs = {}
        rt = self._rt_field()
        if rt:
            kwargs[rt] = self._rt_value()
        kwargs.update(self._audit_kwargs(serializer, ['updated_by']))
        serializer.save(**kwargs)

    def perform_destroy(self, instance):
        instance.soft_delete()


class CampusAmbassadorViewSet(CampusModelViewSetMixin, viewsets.ModelViewSet):
    queryset = CampusAmbassador.objects.all()
    serializer_class = CampusAmbassadorSerializer

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """R-106 撤销：恢复已软删校园大使。"""
        instance = self.queryset.model.objects.get(pk=pk)
        instance.restore()
        return Response({'success': True, 'id': str(instance.id)})


class CampusSessionViewSet(CampusModelViewSetMixin, viewsets.ModelViewSet):
    queryset = CampusSession.objects.all()
    serializer_class = CampusSessionSerializer

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """R-106 撤销：恢复已软删宣讲会。"""
        instance = self.queryset.model.objects.get(pk=pk)
        instance.restore()
        return Response({'success': True, 'id': str(instance.id)})


class CampusModuleConfigView(APIView):
    """校招模块启用开关配置端点（单体 JSON 配置，沿用 DemandConfigView 范式）。

    路由以 kwargs 传入 key（'ambassador' / 'session'），FE 调用 /ambassadors/config/ 或 /sessions/config/。
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _get_or_create(key):
        obj, _ = CampusModuleConfig.objects.get_or_create(key=key)
        return obj

    def get(self, request, *args, **kwargs):
        key = kwargs.get('key', 'ambassador')
        obj = self._get_or_create(key)
        return Response({'success': True, 'data': obj.config or {}})

    def put(self, request, *args, **kwargs):
        key = kwargs.get('key', 'ambassador')
        obj = self._get_or_create(key)
        obj.config = request.data
        if request.user and request.user.is_authenticated:
            obj.updated_by = request.user
        obj.save()
        return Response({'success': True, 'data': obj.config})

    def post(self, request, *args, **kwargs):
        return self.put(request, *args, **kwargs)
