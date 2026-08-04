"""动态字段定义 (G42) 的序列化器。

2026-08-04 修复 (寇豆码) — 重复 field_key 保存返回 500:
    ``DynamicField.Meta.unique_together = [('resource', 'field_key')]``,
    但 ``resource`` 在 ``read_only_fields`` 里, 不属于 ``_writable_fields``,
    DRF 的 ``get_unique_together_validators()`` 因此**跳过**了这条约束
    (它要求约束涉及的全部字段都可写)。结果校验层完全放行, 冲突一路撞到 DB,
    抛 ``IntegrityError (1062, Duplicate entry ...)`` → DRF 不认识 → HTTP 500。

    这里手写 ``validate()`` 把唯一性检查补回校验层, 冲突时返回 400 友好错误。
"""
from rest_framework import serializers

from .models import DynamicField

#: (resource, field_key) 冲突时返回给前端的友好提示
DUPLICATE_FIELD_KEY_MESSAGE = '资源 {resource} 下已存在字段 Key "{field_key}", 请更换 Key 或直接编辑已有字段。'


class DynamicFieldSerializer(serializers.ModelSerializer):
    """动态字段定义序列化器。

    ``resource`` 由 URL 决定 (见 ``DynamicFieldViewSet.perform_create``), 因此是只读的;
    校验阶段通过 ``context['resource']`` 拿到它来做唯一性预检。
    """

    class Meta:
        model = DynamicField
        fields = '__all__'
        read_only_fields = ['id', 'resource', 'created_at', 'updated_at']

    def _resolve_resource(self) -> str:
        """解析当前请求作用的 resource。

        优先级: 已有实例 (update) > serializer context > view kwargs。
        create 时 ``resource`` 还没写进实例, 只能从 URL 侧的 context 取。

        Returns:
            str: resource 名称; 解析不到时返回空字符串。
        """
        if self.instance is not None and getattr(self.instance, 'resource', None):
            return self.instance.resource

        resource = self.context.get('resource')
        if resource:
            return str(resource)

        view = self.context.get('view')
        if view is not None:
            return str(getattr(view, 'kwargs', {}).get('resource') or '')

        return ''

    def validate_field_key(self, value: str) -> str:
        """去空白 + 非空校验。

        Args:
            value: 客户端提交的 field_key。

        Returns:
            str: 规整后的 field_key。

        Raises:
            serializers.ValidationError: field_key 为空或全空白。
        """
        field_key = (value or '').strip()
        if not field_key:
            raise serializers.ValidationError('字段 Key 不能为空。')
        return field_key

    def validate(self, attrs: dict) -> dict:
        """在校验层拦截 (resource, field_key) 唯一冲突, 避免 DB 层 IntegrityError → 500。

        - create: 检查该 resource 下是否已有同名 field_key 的**存活**记录。
        - update: 同上, 但排除自身 (改其它字段而不改 Key 时不能误报)。

        Args:
            attrs: DRF 逐字段校验后的数据。

        Returns:
            dict: 原样返回 attrs。

        Raises:
            serializers.ValidationError: 该 resource 下 field_key 已存在。
        """
        resource = self._resolve_resource()
        field_key = attrs.get('field_key') or getattr(self.instance, 'field_key', '')

        if not resource or not field_key:
            return attrs

        conflicts = DynamicField.objects.filter(
            resource=resource,
            field_key=field_key,
            deleted_at__isnull=True,
        )
        if self.instance is not None:
            conflicts = conflicts.exclude(pk=self.instance.pk)

        if conflicts.exists():
            raise serializers.ValidationError({
                'field_key': [
                    DUPLICATE_FIELD_KEY_MESSAGE.format(resource=resource, field_key=field_key)
                ]
            })

        return attrs
