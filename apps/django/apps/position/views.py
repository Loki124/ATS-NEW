"""Position Views (DRF) - PRD v4 §14.2"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.exceptions import ValidationError
from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.common.views import EnvelopeWriteMixin
from apps.core.permissions_v2 import V2Permission, ScopeQuerysetMixin

from .models import Position
from .serializers import (
    PositionCreateSerializer,
    PositionDetailSerializer,
    PositionListSerializer,
    PositionTransitionSerializer,
)


class PositionViewSet(EnvelopeWriteMixin, ScopeQuerysetMixin, AuditMixin, viewsets.ModelViewSet):
    """职位 ViewSet - 按部门 scope 过滤"""
    queryset = Position.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:position:list'
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['state', 'department', 'hiring_manager', 'owner', 'level', 'process']
    search_fields = ['code', 'title', 'description']
    ordering_fields = ['code', 'created_at', 'published_at']
    ordering = ['-created_at']
    scope_field = 'department'
    scope_creator_field = 'created_by'

    def get_serializer_class(self):
        if self.action == 'list':
            return PositionListSerializer
        if self.action == 'retrieve':
            return PositionDetailSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return PositionCreateSerializer
        if self.action == 'transition':
            return PositionTransitionSerializer
        return PositionDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(deleted_at__isnull=True)
        qs = qs.select_related('department', 'hiring_manager', 'owner', 'process')
        # IDOR scope 过滤 (Fix 1)
        qs = self.scope_queryset(qs, entity='position')
        return qs

    def perform_create(self, serializer):
        """职位编号自动生成 (与 PositionService 约定一致: P{YYYYMMDD}{nanoid4})。
        create 序列化器未暴露 code(唯一约束、无默认值), 必须在此注入, 否则落库 code='' 且二次创建撞唯一键。"""
        from django.utils import timezone
        from nanoid import generate as nanoid_generate
        code = f'P{timezone.now().strftime("%Y%m%d")}{nanoid_generate(size=4).upper()}'
        # 写入守卫: recruit_type 由请求上下文(中间件按 X-Recruit-Type 注入)权威决定,
        # 覆盖模型列默认值。否则新建职位恒落 'social', 在 campus 系统下被读侧分区过滤掉。
        serializer.save(code=code, recruit_type=getattr(self.request, 'recruit_type', 'social'))

    def _detail_response(self, instance, status_code=status.HTTP_201_CREATED):
        out = PositionDetailSerializer(instance, context={'request': self.request})
        return success_response(out.data, status_code=status_code)

    def create(self, request, *args, **kwargs):
        # 默认 create 用 PositionCreateSerializer 输出(缺 id/code/state), 前端拿不到新职位标识;
        # 改返回 PositionDetailSerializer 完整数据。
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return self._detail_response(serializer.instance, status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return self._detail_response(instance, status.HTTP_200_OK)

    def perform_destroy(self, instance):
        from django.utils import timezone
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'updated_at'])

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        """状态机流转：submit_publish/publish/start_recruiting/pause/resume/close"""
        instance = self.get_object()
        serializer = PositionTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_name = serializer.validated_data['action']
        method = getattr(instance, action_name, None)
        if not method:
            raise ValidationError(f'不支持的操作：{action_name}')
        method()
        instance.save()
        out = PositionDetailSerializer(instance, context={'request': request})
        return Response({'success': True, 'data': out.data})

    @action(detail=False, methods=['get'], url_path='open')
    def open_positions(self, request):
        """开放中的职位列表"""
        qs = self.get_queryset().filter(state='RECRUITING')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = PositionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PositionListSerializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})
