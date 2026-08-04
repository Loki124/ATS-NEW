"""通用 ViewSet Mixins"""
import logging

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class BulkCreateMixin:
    """批量创建 Mixin

    2026-07-02: 每行独立事务, 失败不阻塞其它行, 返回 207 多状态响应。
    之前一行失败全 roll back, 客户端拿不到哪条出错。
    """
    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list):
            serializer = self.get_serializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            results = self.perform_bulk_create(serializer)
            return Response(results, status=status.HTTP_207_MULTI_STATUS)
        return super().create(request, *args, **kwargs)

    def perform_bulk_create(self, serializer):
        results = []
        for item in serializer.validated_data:
            try:
                with transaction.atomic():
                    instance = serializer.child.create(item)
                    results.append({
                        'success': True,
                        'data': serializer.child.to_representation(instance),
                    })
            except IntegrityError as e:
                logger.warning('Bulk create integrity error: %s', e)
                results.append({
                    'success': False,
                    'error': 'INTEGRITY_ERROR',
                    'detail': str(e),
                })
            except Exception as e:
                logger.exception('Bulk create row failed: %s', e)
                results.append({
                    'success': False,
                    'error': 'CREATE_FAILED',
                    'detail': str(e),
                })
        return results


class SoftDeleteViewSetMixin:
    """软删除 ViewSet Mixin"""
    def perform_destroy(self, instance):
        instance.soft_delete()


class AuditMixin:
    """审计 Mixin - 自动记录创建人/修改人

    2026-08-04 (寇豆码): 修复 POST/PUT 必 500 的缺陷。
    之前无条件 `serializer.save(created_by=..., updated_by=...)`, 但本工程里
    只有继承 FullAuditModel 的模型才有这两个 FK; 大量模型只继承 TimestampedModel
    (field_acl.FieldACL / gdpr.GDPRRequest / notification.NotificationTemplate /
    integration.IntegrationConfig / analytics.ReportSnapshot / analytics.ExportTask),
    对它们 `Model.objects.create(created_by=...)` 会抛 TypeError → HTTP 500。

    现在改为: 只注入目标模型**确实存在**的审计字段。
    - 模型有 created_by/updated_by → 行为与之前完全一致, 照常记录;
    - 模型没有 → 静默跳过该 kwarg, 正常落库, 不再 500。
    这样无需给每张表加列/加 migration, 也不牺牲已有模型的审计能力。
    """

    #: 审计字段名, 子类可覆盖以适配非标准命名。
    audit_created_by_field = 'created_by'
    audit_updated_by_field = 'updated_by'

    def get_audit_user(self):
        """取当前请求用户; 未认证(如匿名/内部调用)返回 None。"""
        user = getattr(getattr(self, 'request', None), 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            return user
        return None

    def _resolve_audit_model(self, serializer):
        """定位序列化器背后的模型; 拿不到则返回 None(此时不注入任何审计字段)。"""
        model = getattr(getattr(serializer, 'Meta', None), 'model', None)
        if model is not None:
            return model
        queryset = getattr(self, 'queryset', None)
        return queryset.model if queryset is not None else None

    def build_audit_kwargs(self, serializer, field_names):
        """构造 save() 的审计 kwargs, 自动剔除模型上不存在的字段。

        Args:
            serializer: 即将 save() 的序列化器。
            field_names: 想要写入的审计字段名序列。

        Returns:
            dict: 仅包含模型真实拥有的字段, 值为当前请求用户(或 None)。
        """
        model = self._resolve_audit_model(serializer)
        if model is None:
            return {}
        # 只看具体字段(含 FK), 避免反向关联名误判。
        concrete_fields = {f.name for f in model._meta.concrete_fields}
        user = self.get_audit_user()
        return {name: user for name in field_names if name in concrete_fields}

    def perform_create(self, serializer):
        audit_kwargs = self.build_audit_kwargs(
            serializer,
            (self.audit_created_by_field, self.audit_updated_by_field),
        )
        serializer.save(**audit_kwargs)

    def perform_update(self, serializer):
        audit_kwargs = self.build_audit_kwargs(
            serializer,
            (self.audit_updated_by_field,),
        )
        serializer.save(**audit_kwargs)
