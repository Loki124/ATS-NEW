
"""Integration Views (DRF) - PRD v4 §14.4"""
import logging
import time

import requests
from django.db import DatabaseError, OperationalError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsSetPagination
from apps.common.viewsets import EnvelopeAuditModelViewSet, EnvelopeModelViewSet
from apps.core.permissions import IsHROrAbove, IsSuperAdmin

from .models import (
    BackgroundCheckOrder,
    IntegrationConfig,
    IntegrationSyncLog,
    IntegrationType,
)
from .serializers import (
    BackgroundCheckOrderDetailSerializer,
    BackgroundCheckOrderSerializer,
    IntegrationConfigSerializer,
    IntegrationSyncLogSerializer,
)
from .services import (
    aggregate_bg_suggestions,
    apply_callback_to_order,
    bg_callback_envelope,
    cancel_background_check_order,
    fetch_background_check_report,
    get_supplier,
    query_background_check_order,
    request_background_check,
    upload_background_check_report,
    verify_background_check_callback,
)

logger = logging.getLogger(__name__)


class IntegrationConfigViewSet(EnvelopeAuditModelViewSet):
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
                send_email,
                send_sms,
                send_wecom_message,
                sync_candidate_from_moka,
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
        except Exception as e:  # noqa: BLE001 — 集成连通性测试 (ping 外部服务) 异常类型不固定, 统一兜底返 500
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
        except Exception as e:  # noqa: BLE001 — fail-fast: 应用失败回写 FAILED 审计并返 5xx, 让供应商重试, 绝不伪装成功
            log.status = 'FAILED'
            log.error_message = f'apply_callback_to_order failed: {e}'
            log.save(update_fields=['status', 'error_message'])
            logger.exception('apply_callback_to_order failed (number=%s)', number)
            return Response(
                bg_callback_envelope(50002, 'apply failed', data={'number': number, 'status': status_val}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
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
        except (DatabaseError, ValueError, TypeError):  # 审计写入失败不影响主流程响应
            logger.exception('callback FAILED audit log write failed')


class BackgroundCheckOrderViewSet(EnvelopeModelViewSet):
    """背调订单状态机视图（HR/HRBP/超管可读写；供应商回调另走签名端点）。

    - 列表/详情：展示订单当前状态、风险、报告、状态机转移历史(events)
    - suppliers/products：发起前选择供应商与拉取套餐（仅暴露 id/name/provider，不含密钥）
    - create-order：发起背调（委托 request_background_check 创建订单）
    - cancel 动作：平台发起取消（置 status=6，写 CANCEL 事件 + 出向供应商取消接口）
    """
    queryset = BackgroundCheckOrder.objects.all()
    permission_classes = [IsHROrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['config', 'status', 'candidate_id']
    ordering_fields = ['created_at', 'status', 'completion_time']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BackgroundCheckOrderDetailSerializer
        return BackgroundCheckOrderSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('config')

    @action(detail=False, methods=['get'], url_path='suppliers')
    def suppliers(self, request):
        """列出可选背调供应商配置（仅暴露 id/name/provider，不含密钥）。

        mode=self_order  → 自主下单：SELF_CHECK 伪选项（自主背调）+ 所有启用供应商
        mode=system_order → 系统下单：仅系统已对接供应商(is_system_integrated=True)
        不传 mode → 返回所有启用供应商（向后兼容）。
        """
        mode = (request.query_params.get('mode') or '').strip()
        qs = IntegrationConfig.objects.filter(
            type=IntegrationType.BACKGROUND_CHECK, is_active=True,
        )
        if mode == 'system_order':
            qs = qs.filter(is_system_integrated=True)
        cfgs = list(qs.values(
            'id', 'name', 'provider', 'is_system_integrated', 'bg_metadata',
        ))
        if mode == 'self_order':
            # 自主背调：无真实供应商，前端以伪选项呈现（无 metadata → 排名/标签全 null）
            cfgs = [
                {
                    'id': '__SELF__', 'name': '自主背调', 'provider': 'SELF',
                    'is_system_integrated': False, 'bg_metadata': None,
                },
            ] + cfgs
        # 展开 bg_metadata 中的排名/标签；缺失则对应字段为 null（前端优雅降级不渲染）
        for c in cfgs:
            meta = c.get('bg_metadata') or {}
            c['deliveryRank'] = meta.get('delivery_rank')
            c['deliveryTag'] = meta.get('delivery_tag')
            c['usageRank'] = meta.get('usage_rank')
            c['usageTag'] = meta.get('usage_tag')
            c.pop('bg_metadata', None)
        return Response({'success': True, 'data': cfgs})

    @action(detail=False, methods=['get'], url_path='products')
    def products(self, request):
        """拉取指定供应商的套餐/检查项。

        决策（后端）：
        1. 配置优先：``config.bg_metadata.packages`` 非空 → 直接返回标准化套餐（离线可用，不调供应商）。
        2. 否则回退：``supplier.query_products()``；成功则 ``source='supplier'`` 并规范化；
           失败/空 → ``success=false`` 或 ``packages=[]``，前端走手动填检查项兜底。
        """
        config_id = request.query_params.get('config_id')
        if not config_id:
            return Response(
                {'success': False, 'message': '缺少 config_id'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        config = IntegrationConfig.objects.filter(
            id=config_id, type=IntegrationType.BACKGROUND_CHECK, is_active=True,
        ).first()
        if not config:
            return Response(
                {'success': False, 'message': '供应商配置不存在或未启用'},
                status=status.HTTP_404_NOT_FOUND,
            )
        # 1. 配置优先
        metadata = config.bg_metadata or {}
        packages_cfg = metadata.get('packages') or []
        if packages_cfg:
            normalized = []
            for p in packages_cfg:
                if not isinstance(p, dict):
                    continue
                name = p.get('name') or p.get('slug') or ''
                normalized.append({
                    'token': p.get('token') or name,
                    'name': name,
                    'workdays': p.get('workdays'),
                    'features': p.get('features') or [],
                })
            return Response({
                'success': True,
                'message': '',
                'data': {'source': 'config', 'packages': normalized},
            })
        # 2. 回退：调供应商接口
        try:
            supplier = get_supplier(config)
            res = supplier.query_products()
        except (OperationalError, ConnectionError, TimeoutError, OSError,
                requests.RequestException, ValueError) as e:
            # 套餐拉取: ORM + 供应商 HTTP 窄集.
            logger.exception('query_products failed config=%s', config_id)
            return Response(
                {'success': False, 'message': f'套餐拉取失败: {e}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if not res.success:
            return Response({
                'success': False,
                'message': res.message or '套餐拉取失败',
            }, status=status.HTTP_502_BAD_GATEWAY)
        raw = res.data or {}
        raw_list = (
            raw.get('products') or raw.get('list') or raw.get('data') or []
        )
        if not isinstance(raw_list, list):
            raw_list = []
        normalized = []
        for p in raw_list:
            if not isinstance(p, dict):
                continue
            normalized.append({
                'token': p.get('token') or p.get('productToken') or p.get('id')
                or p.get('code') or '',
                'name': p.get('name') or p.get('productName') or p.get('title') or '',
                'workdays': p.get('workdays'),
                'features': p.get('features') or [],
            })
        return Response({
            'success': True,
            'message': res.message or '',
            'data': {'source': 'supplier', 'packages': normalized},
        })

    @action(detail=False, methods=['post'], url_path='create-order')
    def create_order(self, request):
        """发起背调：创建订单（委托 request_background_check）。

        步骤式弹窗扩展入参：
          channel(str)          下单渠道 SELF/SELF_ORDER/SYSTEM_ORDER（前端统一置 SYSTEM_ORDER/SELF_ORDER）
          remark(str)           订单备注（无报告下单时承载背调建议）
          parent_order_id(str)  补充背调时关联父订单
          bg_suggestions(list)  背调建议快照
          has_existing_report(bool) 是否已持有报告（占位，供前端语义一致）
          package_name(str)    冗余存选中套餐名
          bg_result(str)       背调结果（下单分支一般空）
          contactable(bool)    是否可以联系候选人
          subject_snapshot(dict) 背调人信息快照
          expected_onboarding_date(str) 预计入职日期（透传供应商 expect_entry_time）
        """
        candidate_id = (request.data.get('candidate_id') or '').strip()
        if not candidate_id:
            return Response(
                {'success': False, 'message': '缺少 candidate_id'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        items = request.data.get('items') or []
        if not isinstance(items, list):
            items = [items] if items else []
        config_id = request.data.get('config_id') or None
        candidate_name = (request.data.get('candidate_name') or '').strip()
        phone = (request.data.get('phone') or '').strip()
        operator_name = (request.data.get('operator_name')
                         or getattr(request.user, 'name', '') or '').strip()
        operator_phone = (request.data.get('operator_phone') or '').strip()
        channel = (request.data.get('channel') or 'SYSTEM_ORDER').strip()
        remark = (request.data.get('remark') or '').strip()
        parent_order_id = (request.data.get('parent_order_id') or '').strip()
        bg_suggestions = request.data.get('bg_suggestions') or []
        if not isinstance(bg_suggestions, list):
            bg_suggestions = []
        # 步骤式弹窗扩展字段
        package_name = (request.data.get('package_name') or '').strip()
        bg_result = (request.data.get('bg_result') or '').strip()
        contactable = request.data.get('contactable')
        if contactable is not None:
            contactable = bool(contactable)
        subject_snapshot = request.data.get('subject_snapshot') or {}
        if not isinstance(subject_snapshot, dict):
            subject_snapshot = {}
        expected_onboarding_date = (request.data.get('expected_onboarding_date') or '').strip()
        result = request_background_check(
            candidate_id=candidate_id,
            items=items,
            config_id=config_id,
            candidate_name=candidate_name,
            phone=phone,
            operator_name=operator_name,
            operator_phone=operator_phone,
            channel=channel,
            remark=remark,
            parent_order_id=parent_order_id,
            bg_suggestions=bg_suggestions,
            has_existing_report=bool(request.data.get('has_existing_report')),
            package_name=package_name,
            bg_result=bg_result,
            contactable=contactable,
            subject_snapshot=subject_snapshot,
            expected_onboarding_date=expected_onboarding_date,
        )
        if not result.get('success'):
            return Response({
                'success': False,
                'message': result.get('error') or result.get('message') or '发起背调失败',
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True, 'data': result.get('data')})

    @action(detail=False, methods=['post'], url_path='upload-report')
    def upload_report(self, request):
        """已有报告上传 / 自主背调（步骤式弹窗「已有报告」分支）。

        入参：
          candidate_id(str)       候选人 ID（必填）
          candidate_name(str)     候选人姓名
          phone(str)              手机号
          report_url(str)         报告地址（或文件 URL）
          remark(str)             备注
          answers(list)           背调建议回答 [{interviewer, answer}]
          bg_suggestions(list)    背调建议快照（来自 bg-suggestions 接口）
          parent_order_id(str)    补充背调时关联父订单
          package_name(str)       图2 套餐名称
          bg_provider(str)        图2 背调供应商
          bg_time(str)            图2 背调时间（ISO）
          bg_result(str)          图2 背调结果（BGResult）
          subject_snapshot(dict)  背调人信息快照
        """
        candidate_id = (request.data.get('candidate_id') or '').strip()
        if not candidate_id:
            return Response(
                {'success': False, 'message': '缺少 candidate_id'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        report_url = (request.data.get('report_url') or '').strip()
        if not report_url:
            return Response(
                {'success': False, 'message': '请填写报告地址或上传报告'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        candidate_name = (request.data.get('candidate_name') or '').strip()
        phone = (request.data.get('phone') or '').strip()
        operator_name = (request.data.get('operator_name')
                         or getattr(request.user, 'name', '') or '').strip()
        remark = (request.data.get('remark') or '').strip()
        answers = request.data.get('answers') or []
        if not isinstance(answers, list):
            answers = []
        bg_suggestions = request.data.get('bg_suggestions') or []
        if not isinstance(bg_suggestions, list):
            bg_suggestions = []
        parent_order_id = (request.data.get('parent_order_id') or '').strip()
        package_name = (request.data.get('package_name') or '').strip()
        bg_provider = (request.data.get('bg_provider') or '').strip()
        bg_time = (request.data.get('bg_time') or '').strip()
        bg_result = (request.data.get('bg_result') or '').strip()
        subject_snapshot = request.data.get('subject_snapshot') or {}
        if not isinstance(subject_snapshot, dict):
            subject_snapshot = {}
        result = upload_background_check_report(
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            phone=phone,
            report_url=report_url,
            remark=remark,
            answers=answers,
            bg_suggestions=bg_suggestions,
            parent_order_id=parent_order_id,
            operator_name=operator_name,
            package_name=package_name,
            bg_provider=bg_provider,
            bg_time=bg_time,
            bg_result=bg_result,
            subject_snapshot=subject_snapshot,
        )
        if not result.get('success'):
            return Response({
                'success': False,
                'message': result.get('error') or '上传背调报告失败',
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True, 'data': result.get('data')})

    @action(detail=False, methods=['get'], url_path='bg-suggestions')
    def bg_suggestions(self, request):
        """聚合某候选人来自各面试官的背调建议（按面试官去重，取最新一条）。

        查询参数 candidate_id（必填）。
        """
        candidate_id = (request.query_params.get('candidate_id') or '').strip()
        if not candidate_id:
            return Response(
                {'success': False, 'message': '缺少 candidate_id'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            data = aggregate_bg_suggestions(candidate_id)
        except (OperationalError, ValueError) as e:
            logger.exception('aggregate_bg_suggestions failed candidate=%s', candidate_id)
            return Response(
                {'success': False, 'message': f'聚合背调建议失败: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({'success': True, 'data': data})

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
