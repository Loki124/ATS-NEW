"""GDPR Views (DRF) - PRD v4 §4.4

2026-08-03 S2 改造:
- 流程变成 5 步:
  1) 候选人 POST /api/v1/gdpr/requests/ 提交 (无需登录, 走 service.submit_request)
  2) system 生成 8 位 hex verification code, hash 存, 通过邮件/SMS 发给候选人
  3) 候选人 POST /api/v1/gdpr/requests/{id}/verify/ 提交 code 验证身份
  4) 超管看到 status=PENDING 才能 process (ApproveAndForget/ApproveAndExport/Reject)
  5) reject 不需要候选人 verify (信息不全也能拒)
- API 暴露:
  - GET  /api/v1/gdpr/requests/            - 超管列表
  - POST /api/v1/gdpr/requests/            - 候选人提交 (返回 _plaintext_code, 走邮件)
  - GET  /api/v1/gdpr/requests/{id}/       - 详情
  - POST /api/v1/gdpr/requests/{id}/verify/ - 候选人验证
  - POST /api/v1/gdpr/requests/{id}/process/ - 超管处理 (approve_forget/approve_export/reject)
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status as drf_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.common.views import EnvelopeReadOnlyMixin
from apps.core.permissions import IsSuperAdmin

from .models import GDPRRequest
from .serializers import (
    GDPRProcessSerializer,
    GDPRRequestCreateSerializer,
    GDPRRequestSerializer,
    GDPRVerifySerializer,
)
from .services import GdprService, send_verification_code


class GDPRRequestViewSet(AuditMixin, EnvelopeReadOnlyMixin, viewsets.ModelViewSet):
    """GDPR 请求 ViewSet"""
    queryset = GDPRRequest.objects.all()
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['request_type', 'status', 'candidate']
    search_fields = ['candidate__name', 'submitted_email']
    ordering_fields = ['created_at', 'processed_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ('create',):
            return GDPRRequestCreateSerializer
        return GDPRRequestSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('candidate', 'processed_by')

    def get_permissions(self):
        # 候选人提交 / 验证 不需要登录 (通过 verification code 验证身份)
        if self.action in ('create', 'verify'):
            return [AllowAny()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """候选人提交 GDPR 请求 — 公开, 无需登录.

        验证码**只**通过邮件/短信下发给候选人登记邮箱, 绝不在 HTTP 响应里返回。
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = GdprService.submit_request(
            candidate_id=serializer.validated_data['candidate'],
            request_type=serializer.validated_data['request_type'],
            submitted_email=serializer.validated_data['submitted_email'],
        )
        # 2026-10-08: 此前把明文验证码放进响应体 —— 匿名调用者只要知道候选人 id
        #   和任意邮箱就能拿到验证码, 再调公开的 verify 把请求置为"已验证",
        #   让审批人误以为是候选人本人发起的删除/导出。验证码不得出现在响应里。
        plaintext_code = getattr(req, '_plaintext_code', None)
        if plaintext_code:
            send_verification_code(req, plaintext_code)
        out = GDPRRequestSerializer(req, context={'request': request}).data
        out['verification_code_expires_at'] = req.verification_code_expires_at
        out['verification_message'] = '验证码已发送至候选人登记邮箱, 15 分钟内 verify 有效'
        # 2026-09-30 信封 initiative: 收敛到 success_response 补齐 code
        return success_response(out, status_code=drf_status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """超管编辑 GDPR 请求 — 包 {success, data} 信封 (create/verify/process 为自定义, 不动)."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, pk=None):
        """候选人验证身份 — 公开 (走 verification code 验证)."""
        # 注: 不用 self.get_object() 因为 AllowAny 看不到 list/retrieve
        serializer = GDPRVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = GdprService.verify_code(
            request_id=pk,
            plaintext_code=serializer.validated_data['verification_code'],
        )
        out = GDPRRequestSerializer(req, context={'request': request}).data
        return Response({'success': True, 'data': out})

    @action(detail=True, methods=['post'], url_path='process')
    def process(self, request, pk=None):
        """超管处理 GDPR 请求.

        action:
          - approve_forget: 匿名化候选人 (走 service.approve_and_forget)
          - approve_export: 数据导出 (走 service.approve_and_export)
          - reject: 拒绝 (无需候选人 verify)
        """
        instance = self.get_object()
        serializer = GDPRProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_name = serializer.validated_data['action']

        if action_name == 'approve_forget':
            req = GdprService.approve_and_forget(instance.id, request.user)
        elif action_name == 'approve_export':
            req = GdprService.approve_and_export(instance.id, request.user)
        else:  # reject
            req = GdprService.reject(
                instance.id,
                reason=serializer.validated_data.get('reject_reason', ''),
                processor=request.user,
            )

        out = GDPRRequestSerializer(req, context={'request': request}).data
        return Response({'success': True, 'data': out})
