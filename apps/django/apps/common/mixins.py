"""通用 ViewSet Mixins"""
import logging

from django.db import IntegrityError, transaction
from django.http import HttpResponse
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
            except (IntegrityError, ValueError) as e:  # BulkCreateMixin 单条失败(唯一/校验约束)计入 results 继续, 不应让单行异常中断整次批量
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


class SoftDeleteRestoreMixin:
    """让 restore 端点能取到**已软删**对象, 且不绕过行级隔离。

    背景 (2026-10-21 整改卡 D3): `SoftDeleteModel` 挂上 `SoftDeleteManager` 之后,
    ViewSet 的 `get_queryset()` 默认过滤 `deleted_at` → "恢复软删对象"**必然 404**
    (campus / campus_control 的 restore 就是这个状态, 属既有缺陷);
    而直接用 `Model.all_objects` 取数又会绕过 scope
    (守卫 `apps/data_permission/tests/test_write_guard.py` 明确禁止全表取数)。

    做法: 仅在 restore 动作内, 把取数来源换成含软删行的 manager,
    其余过滤链 (scope / filter_backends) 原样保留
    → 行为 =「可见范围内可恢复软删对象」, 且 restore 端点仍走 `self.get_object()`。

    用法: 把本类放在 ViewSet 基类列表的**最前面**(需先于 DRF 的 get_object 生效),
          并在 restore 动作里调用 `self.get_object()`。
    """

    def get_object(self):
        if getattr(self, 'action', None) != 'restore':
            return super().get_object()

        model = self.queryset.model

        def _get_queryset():
            qs = model.all_objects.all()
            scope = getattr(self, 'scope_queryset', None)
            if callable(scope):
                qs = scope(qs)
            return qs

        self.get_queryset = _get_queryset
        try:
            return super().get_object()
        finally:
            del self.get_queryset   # 还原为类方法


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


XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class ExportMixin:
    """为视图提供统一的文件下载响应构造，消除重复的 HttpResponse + BOM + Content-Disposition 样板。

    - csv_response(content, filename): 带 UTF-8 BOM 的 CSV 下载响应
      (与各处 '\\ufeff' + content + charset=utf-8 等价；metrics 旧用 utf-8-sig 编码产生的字节同为
      BOM + utf-8，Excel 解析一致，行为无变化)。
    - xlsx_response(buf, filename): openpyxl BytesIO 工作簿下载响应。
    """

    @staticmethod
    def csv_response(content: str, filename: str) -> HttpResponse:
        resp = HttpResponse('\ufeff' + content, content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp

    @staticmethod
    def xlsx_response(buf, filename: str) -> HttpResponse:
        resp = HttpResponse(buf.getvalue(), content_type=XLSX_CONTENT_TYPE)
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp
