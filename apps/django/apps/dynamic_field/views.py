"""动态字段定义 (G42) 的 CRUD 视图。

2026-08-04 修复 (寇豆码) — 编辑 / 重复保存返回 500:

    层 1 · 前后端寻址主键不一致
        ``get_object()`` 原本用 ``field_key`` 解释 detail 端点的 ``<pk>``,
        而前端 ``dynamic-field.ts`` 一直传 ``row.id`` (nanoid) → detail 端点 404,
        前端于是无论新建还是编辑都退回 POST list 端点。

    层 2 · create 路径不处理唯一约束
        ``unique_together = [('resource', 'field_key')]`` 在 DRF 校验层被跳过
        (原因见 ``serializers.py`` 顶部注释), 冲突直落 DB → ``IntegrityError`` → 500。

    修复后契约:
        - detail 端点 ``<pk>`` = ``DynamicField.id`` (与前端对齐);
          为兼容历史调用方, id 查不到时回退按 ``field_key`` 查 (纯增量, 只会把 404 变成命中)。
        - 唯一冲突在 serializer 校验层拦截 → 400 友好错误;
          软删记录占位导致的冲突走"复活"路径; 并发兜底 catch ``IntegrityError`` → 400。
        - create / retrieve / update 与 list 一样统一返回 ``{"data": ...}`` 信封,
          与前端 ``.then(r => r.data.data)`` 的消费方式对齐。
"""
from django.db import IntegrityError, transaction
from django.http import Http404
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import DynamicField
from .serializers import DUPLICATE_FIELD_KEY_MESSAGE, DynamicFieldSerializer


class DynamicFieldViewSet(viewsets.ModelViewSet):
    """动态字段定义 CRUD — 按 resource 过滤, detail 端点按 id 寻址。"""

    serializer_class = DynamicFieldSerializer
    permission_classes = [IsAuthenticated]

    # --- 基础 ---------------------------------------------------------------

    def get_queryset(self):
        """只暴露未软删的记录。"""
        return DynamicField.objects.filter(deleted_at__isnull=True)

    def get_resource(self) -> str:
        """从 URL kwargs 取当前 resource (Candidate / Position / ...)。"""
        return str(self.kwargs.get('resource') or '')

    def get_serializer_context(self) -> dict:
        """把 resource 注入 serializer context, 供唯一性预检使用。

        create 时 ``resource`` 是 read_only, serializer 自己拿不到, 必须由 view 传。
        """
        context = super().get_serializer_context()
        context['resource'] = self.get_resource()
        return context

    def get_object(self) -> DynamicField:
        """按 id 寻址 (主契约), 未命中时回退按 field_key 寻址 (向后兼容)。

        Returns:
            DynamicField: 命中的字段定义。

        Raises:
            Http404: 该 resource 下既没有匹配 id 也没有匹配 field_key 的存活记录。
        """
        queryset = self.get_queryset()
        resource = self.get_resource()
        lookup = self.kwargs.get('pk')

        instance = queryset.filter(resource=resource, id=lookup).first()
        if instance is None:
            # 向后兼容: 历史调用方按 field_key 寻址。id 唯一, 故不存在误命中风险。
            instance = queryset.filter(resource=resource, field_key=lookup).first()

        if instance is None:
            raise Http404(f'字段 {resource}/{lookup} 不存在或已删除')

        self.check_object_permissions(self.request, instance)
        return instance

    # --- 读 ------------------------------------------------------------------

    def list(self, request, *args, **kwargs) -> Response:
        """GET /dynamic-fields/<resource>/fields/ — 按 order_index 升序返回全量。"""
        queryset = self.get_queryset().filter(resource=self.get_resource()).order_by('order_index')
        serializer = self.get_serializer(queryset, many=True)
        return Response({'data': serializer.data})

    def retrieve(self, request, *args, **kwargs) -> Response:
        """GET /dynamic-fields/<resource>/fields/<id>/"""
        serializer = self.get_serializer(self.get_object())
        return Response({'data': serializer.data})

    # --- 写 ------------------------------------------------------------------

    def create(self, request, *args, **kwargs) -> Response:
        """POST /dynamic-fields/<resource>/fields/ → 201 ``{"data": {...}}``"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({'data': serializer.data}, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs) -> Response:
        """PUT / PATCH /dynamic-fields/<resource>/fields/<id>/ → 200 ``{"data": {...}}``"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response({'data': serializer.data})

    def perform_create(self, serializer) -> None:
        """写入新字段定义; 软删记录占位时改为"复活", 并对唯一冲突做兜底。

        软删记录仍然占着 ``unique_together`` 的坑位 (DB 约束不认 ``deleted_at``),
        所以"删了再建同名 Key"必须走复活路径, 否则又是 IntegrityError → 500。

        Args:
            serializer: 已通过校验的 DynamicFieldSerializer。

        Raises:
            drf_serializers.ValidationError: 并发下仍撞唯一约束 → 转 400。
        """
        resource = self.get_resource()
        field_key = serializer.validated_data.get('field_key', '')

        soft_deleted = DynamicField.objects.filter(
            resource=resource,
            field_key=field_key,
            deleted_at__isnull=False,
        ).first()

        try:
            with transaction.atomic():
                if soft_deleted is None:
                    serializer.save(resource=resource)
                    return

                for attr, value in serializer.validated_data.items():
                    setattr(soft_deleted, attr, value)
                soft_deleted.resource = resource
                soft_deleted.deleted_at = None
                soft_deleted.save()
                serializer.instance = soft_deleted
        except IntegrityError as exc:
            raise self._duplicate_error(resource, field_key) from exc

    def perform_update(self, serializer) -> None:
        """更新字段定义, 对唯一冲突做兜底 (例如目标 Key 被软删记录占位)。

        Args:
            serializer: 已通过校验的 DynamicFieldSerializer。

        Raises:
            drf_serializers.ValidationError: 撞唯一约束 → 转 400。
        """
        resource = self.get_resource() or getattr(serializer.instance, 'resource', '')
        field_key = serializer.validated_data.get(
            'field_key', getattr(serializer.instance, 'field_key', '')
        )
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            raise self._duplicate_error(resource, field_key) from exc

    def perform_destroy(self, instance: DynamicField) -> None:
        """DELETE → 软删 (保留历史数据)。"""
        instance.soft_delete()

    # --- 自定义动作 -----------------------------------------------------------

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request, resource=None) -> Response:
        """POST /dynamic-fields/<resource>/fields/reorder/ — 按传入 id 顺序重排。

        注意: 全局启用了 ``CamelCaseJSONParser``, 前端的 ``orderedIds`` 到这里
        已被转成 ``ordered_ids``; 两种 key 都兼容读取, 避免静默不生效。
        """
        ordered_ids = request.data.get('ordered_ids') or request.data.get('orderedIds') or []
        for index, field_id in enumerate(ordered_ids):
            self.get_queryset().filter(id=field_id, resource=resource).update(order_index=index)
        return Response({'success': True})

    # --- 内部工具 -------------------------------------------------------------

    @staticmethod
    def _duplicate_error(resource: str, field_key: str) -> drf_serializers.ValidationError:
        """构造统一的唯一冲突 400 错误。"""
        return drf_serializers.ValidationError({
            'field_key': [DUPLICATE_FIELD_KEY_MESSAGE.format(resource=resource, field_key=field_key)]
        })
