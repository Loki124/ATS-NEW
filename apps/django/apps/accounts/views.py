"""注册审核视图: 自助注册 → 邮箱验证码 → 管理员审核 → 激活登录."""
import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.core.role_v2_query import is_super_admin
from apps.core.views_auth import RegisterRateThrottle

from . import services
from .models import RegistrationApplication
from .serializers import (
    RegisterSerializer,
    RegistrationApplicationSerializer,
    RegistrationReviewSerializer,
    ResendRegisterCodeSerializer,
    VerifyRegisterCodeSerializer,
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegisterRateThrottle])
def register_view(request):
    """自助注册. 建 User(is_active=False) + RegistrationApplication(PENDING), 发邮箱验证码."""
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    full_name = serializer.validated_data.get('full_name', '')

    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        username=email,
        email=email,
        is_active=False,
        deleted_at=None,
    )
    user.set_password(password)
    if full_name:
        # AbstractUser 用 first/last_name 拼 full_name; 中文名整体放 first_name
        user.first_name = full_name
    user.save(update_fields=['password', 'first_name', 'updated_at'])

    RegistrationApplication.objects.create(
        user=user, email=email, full_name=full_name, status='PENDING',
    )

    try:
        services.issue_code(email, full_name)
    except Exception as e:  # noqa: BLE001 — 注册验证码邮件发送失败返 201 (用户已建, 允许后续重发), 不应让注册流程 500
        logger.error('注册验证码发送失败 email=%s err=%s', email, e, exc_info=True)
        # 用户已建, 验证码发送失败允许重试 (resend-register-code)
        return Response(
            {'success': True, 'message': '注册成功，但验证码邮件发送失败，请稍后重新获取验证码',
             'data': {'email': email, 'email_verified': False}},
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {'success': True, 'message': '注册申请已提交，验证码已发送至您的邮箱，请完成邮箱验证后等待管理员审核',
         'data': {'email': email, 'email_verified': False}},
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_register_code_view(request):
    """校验邮箱验证码. 成功则置 email_verified=True."""
    serializer = VerifyRegisterCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']
    ok, reason = services.verify_code(email, serializer.validated_data['code'])
    if not ok:
        code_map = {
            'NO_CODE': '请先获取验证码',
            'EXPIRED': '验证码已过期，请重新获取',
            'LOCKED': '验证码错误次数过多，已锁定，请重新获取',
            'WRONG': '验证码不正确',
        }
        return Response(
            {'success': False, 'code': reason, 'message': code_map.get(reason, '验证失败')},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {'success': True, 'message': '邮箱验证成功，请等待管理员审核',
         'data': {'email': email, 'email_verified': True}},
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_register_code_view(request):
    """重新发送注册验证码 (仅 PENDING 申请可重发)."""
    serializer = ResendRegisterCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']
    app = RegistrationApplication.objects.filter(email=email, status='PENDING').first()
    if app is None:
        return Response(
            {'success': False, 'code': 'NO_APPLICATION', 'message': '没有该邮箱的待审注册申请'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        services.issue_code(email, app.full_name)
    except Exception as e:  # noqa: BLE001 — 重发注册验证码失败返 500 (前端可重试, 但状态明确)
        logger.error('重发注册验证码失败 email=%s err=%s', email, e, exc_info=True)
        return Response(
            {'success': False, 'code': 'SEND_FAILED', 'message': '验证码发送失败，请稍后重试'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return Response({'success': True, 'message': '验证码已重新发送至您的邮箱'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def registration_list_view(request):
    """管理员: 注册申请列表 (默认只看待审). per P1 audit 恢复服务端分页 (替代原 [:200] 截断)."""
    if not is_super_admin(request.user):
        return Response({'success': False, 'message': '无权限'}, status=status.HTTP_403_FORBIDDEN)
    status_filter = request.query_params.get('status', 'PENDING')
    qs = RegistrationApplication.objects.all()
    if status_filter and status_filter != 'ALL':
        qs = qs.filter(status=status_filter)
    qs = qs.order_by('-created_at')
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(qs, request)
    if page is not None:
        return paginator.get_paginated_response(
            RegistrationApplicationSerializer(page, many=True).data
        )
    return Response({'success': True, 'data': RegistrationApplicationSerializer(qs, many=True).data})


def _admin_app_or_403(request, pk):
    if not is_super_admin(request.user):
        return None, Response({'success': False, 'message': '无权限'}, status=status.HTTP_403_FORBIDDEN)
    app = get_object_or_404(RegistrationApplication, pk=pk)
    return app, None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def registration_approve_view(request, pk):
    """管理员: 通过注册申请 → 激活用户. 要求邮箱已验证."""
    app, err = _admin_app_or_403(request, pk)
    if err:
        return err
    if app.status != 'PENDING':
        return Response(
            {'success': False, 'code': 'BAD_STATUS', 'message': f'该申请状态为 {app.status}，无法重复审核'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not app.email_verified:
        return Response(
            {'success': False, 'code': 'EMAIL_NOT_VERIFIED',
             'message': '该申请尚未完成邮箱验证，请先让用户完成邮箱验证码校验'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    app.status = 'APPROVED'
    app.reviewed_by = request.user
    app.reviewed_at = timezone.now()
    app.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
    app.user.is_active = True
    app.user.save(update_fields=['is_active', 'updated_at'])
    return Response({'success': True, 'message': '已通过并激活账号', 'data': {'email': app.email}})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def registration_reject_view(request, pk):
    """管理员: 拒绝注册申请 (保持 is_active=False)."""
    app, err = _admin_app_or_403(request, pk)
    if err:
        return err
    if app.status != 'PENDING':
        return Response(
            {'success': False, 'code': 'BAD_STATUS', 'message': f'该申请状态为 {app.status}，无法重复审核'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    serializer = RegistrationReviewSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    app.status = 'REJECTED'
    app.reviewed_by = request.user
    app.reviewed_at = timezone.now()
    app.reject_reason = serializer.validated_data.get('reject_reason', '')
    app.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'reject_reason', 'updated_at'])
    # 拒绝: 保持 user.is_active=False (已建但未激活)
    return Response({'success': True, 'message': '已拒绝该注册申请', 'data': {'email': app.email}})
