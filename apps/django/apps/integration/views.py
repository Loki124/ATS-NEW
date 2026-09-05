"""Integration Views (DRF) - PRD v4 §14.4"""
import logging
import time

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.mixins import AuditMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.core.permissions import IsSuperAdmin

from .models import IntegrationConfig, IntegrationSyncLog, BackgroundCheckOrder
from .serializers import (
    IntegrationConfigSerializer,
    IntegrationSyncLogSerializer,
    BackgroundCheckOrderSerializer,
    BackgroundCheckOrderDetailSerializer,
)
from .services import (
    bg_callback_envelope,
    verify_background_check_callback,
    apply_callback_to_order,
    cancel_background_check_order,
    query_background_check_order,
    fetch_background_check_report,
)

logger = logging.getLogger(__name__)


class IntegrationConfigViewSet(AuditMixin, viewsets.ModelViewSet):
    """集成配置 ViewSet - 仅超管可操作"""
    queryset = IntegrationConfig.objects.all()
    serializer_class = IntegrationConfigSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['type', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['type', 'name']

    @action(detail=True, methods=['post'], url_path='test')
    def test(self, request, pk=None):
        """测试集成连接"""
        instance = self.get_object()
        try:
            from .services import (
                send_email, send_sms, send_wecom_message, sync_candidate_from_moka,
                test_background_check_connection,
            )
            if instance.type == 'EMAIL':
                ok = send_email(
                    to=request.user.email or 'test@example.com',
                    subject='[集成测试]',
                    body='集成测试邮件',
                )
            elif instance.type == 'SMS':
                ok = send_sms(phone='13800138000', content='测试短信')
            elif instance.type == 'WECOM':
                ok = send_wecom_message(user_id='', content='测试消息')
            elif instance.type == 'MOKA':
                result = sync_candidate_from_moka(moka_id='test')
                ok = result.get('success', False)
            elif instance.type == 'BACKGROUND_CHECK':
                result = test_background_check_connection(instance)
                ok = result.get('success', False)
            else:
                ok = False
            return Response({
                'success': True,
                'data': {'ok': ok, 'message': '测试完成'},
            })
        except Exception as e:
            logger.exception('集成连通性测试失败 integration_id=%s type=%s', instance.id, instance.type)
            return Response({
                'success': False,
                'message': f'测试失败: {e}',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IntegrationSyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """集成同步日志 ViewSet - 只读"""
    queryset = IntegrationSyncLog.objects.all()
    serializer_class = IntegrationSyncLogSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['config', 'sync_type', 'status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('config')


class BackgroundCheckCallbackView(APIView):
    """背调供应商异步回调入向端点（规范 §5.2 验签 + §5.3 幂等）

    供应商在订单状态变更时主动 POST 此端点。请求体携带 sign 验签,
    端点面向供应商、靠签名保护, 不加 IsSuperAdmin 鉴权。
    path: /api/v1/background-check/callback/
    """

    permission_classes = [AllowAny]

    def post(self, request):
        t0 = time.time()
        payload = request.data if isinstance(request.data, dict) else {}
        app_id = request.headers.get('X-App-Id', '') or ''

        # 1. 验签 + 重放防护（异常按内部错误审计）
        try:
            ok, code, message, config = verify_background_check_callback(payload, app_id)
        except Exception as e:  # noqa: BLE001 - 验签过程异常统一按内部错误返回
            logger.exception('background_check callback verify failed')
            self._audit_failed(None, payload, 50001, f'内部异常: {e}', time.time() - t0)
            return Response(
                bg_callback_envelope(50001, '内部异常'), status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 2. 验签失败 / 重放 / appId 无效 → 审计 + 401 信封
        if not ok:
            self._audit_failed(config, payload, code, message, time.time() - t0)
            return Response(bg_callback_envelope(code, message), status=status.HTTP_401_UNAUTHORIZED)

        # 3. 幂等（§5.3）: 幂等键 (number, status, completionTime)
        #    注意: IntegrationSyncLog.status 存的是审计结果(SUCCESS/FAILED), 订单状态在 request_data 里,
        #    故按 external_ref=number 取出候选后比对回Body中的订单 status / completionTime。
        number = str(payload.get('number', ''))
        status_val = payload.get('status')
        completion_time = payload.get('completionTime')
        existing = IntegrationSyncLog.objects.filter(
            config=config, sync_type='CALLBACK', external_ref=number,
        ).only('request_data')
        for e in existing:
            rd = e.request_data or {}
            if rd.get('status') == status_val and rd.get('completionTime') == completion_time:
                return Response(
                    bg_callback_envelope(0, 'success', data={'number': number, 'status': status_val}),
                    status=status.HTTP_200_OK,
                )

        # 4. 首次到达: 落审计 SUCCESS
        duration_ms = int((time.time() - t0) * 1000)
        log = IntegrationSyncLog.objects.create(
            config=config, sync_type='CALLBACK', direction='IN',
            endpoint='/api/v1/background-check/callback', method='POST',
            status='SUCCESS', request_data=payload, external_ref=number, duration_ms=duration_ms,
        )
        # 5. 驱动订单状态机（规范 §5.3 幂等 + 状态机转移；noop 时不重复落事件）
        try:
            order, _event, action = apply_callback_to_order(payload, config, sync_log=log)
            logger.info('background_check callback applied: order=%s action=%s', order.order_number, action)
        except Exception:
            logger.exception('apply_callback_to_order failed (number=%s)', number)
        return Response(
            bg_callback_envelope(0, 'success', data={'number': number, 'status': status_val}),
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _audit_failed(config, payload, code, message, duration_s):
        """验签失败审计。config 为非空 FK, appId 未匹配到配置时(config=None)无法落审计, 直接跳过。"""
        if config is None:
            return
        try:
            IntegrationSyncLog.objects.create(
                config=config, sync_type='CALLBACK', direction='IN',
                endpoint='/api/v1/background-check/callback', method='POST',
                status='FAILED', error_message=f'[{code}] {message}',
                request_data=payload, external_ref=str(payload.get('number') or ''),
                duration_ms=int(duration_s * 1000),
            )
        except Exception:  # noqa: BLE001 - 审计写入失败不影响主流程响应
            logger.exception('callback FAILED audit log write failed')


class BackgroundCheckOrderViewSet(viewsets.ModelViewSet):
    """背调订单状态机视图（仅超管可读 + 取消）。

    - 列表/详情：展示订单当前状态、风险、报告、状态机转移历史(events)
    - cancel 动作：平台发起取消（置 status=6，写 CANCEL 事件 + 出向供应商取消接口）
    """
    queryset = BackgroundCheckOrder.objects.all()
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['config', 'status']
    ordering_fields = ['created_at', 'status', 'completion_time']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BackgroundCheckOrderDetailSerializer
        return BackgroundCheckOrderSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('config')

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """平台发起取消（状态机置 6 已取消）"""
        order = self.get_object()
        if order.status == 6:  # BGOrderStatus.CANCELLED
            # 已取消，幂等返回
            return Response({
                'success': True,
                'message': '订单已处于已取消状态',
                'data': BackgroundCheckOrderSerializer(order).data,
            })
        result = cancel_background_check_order(order)
        if not result.get('success'):
            return Response({
                'success': False,
                'message': result.get('message', '取消失败'),
            }, status=status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        return Response({
            'success': True,
            'message': '已取消',
            'data': BackgroundCheckOrderSerializer(order).data,
        })

    @action(detail=True, methods=['get'], url_path='query')
    def query(self, request, pk=None):
        """轮询供应商订单最新状态（§6.4 兜底；T6 新增接口，仅超管）。"""
        order = self.get_object()
        result = query_background_check_order(order.order_number, order.config_id)
        if not result.get('success'):
            return Response({
                'success': False,
                'message': result.get('error') or result.get('message', '查询失败'),
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True, 'data': result.get('data')})

    @action(detail=True, methods=['get'], url_path='report')
    def report(self, request, pk=None):
        """拉取背调报告（T6 新增接口，仅超管）。"""
        order = self.get_object()
        result = fetch_background_check_report(order)
        if not result.get('success'):
            return Response({
                'success': False,
                'message': result.get('error') or result.get('message', '拉取失败'),
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True, 'data': result.get('data')})
