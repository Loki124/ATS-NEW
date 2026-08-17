"""数据字典序列化器。"""
import re

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import DictionaryItem, DictionaryType

# code 只允许小写字母 / 数字 / 下划线, 保证可作为 URL / 标识符稳定使用.
CODE_PATTERN = re.compile(r'^[a-z0-9_]+$')


class DictionaryTypeSerializer(serializers.ModelSerializer):
    """字典类型。"""

    class Meta:
        model = DictionaryType
        fields = ['id', 'code', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        # code 在创建时由前端提供 (同时作为 URL lookup), 编辑时随 URL 传入、不在 body 中,
        # 故放宽为非必填, 避免 PUT 整量更新因缺 code 触发 400.
        extra_kwargs = {
            'code': {'required': False},
        }

    def validate_code(self, value: str) -> str:
        """code 非空且只能含小写字母、数字、下划线。"""
        if not value:
            raise serializers.ValidationError('code 不能为空')
        if not CODE_PATTERN.match(value):
            raise serializers.ValidationError('code 只能包含小写字母、数字和下划线')
        return value

    def validate_name(self, value: str) -> str:
        """name 非空。"""
        if not value or not value.strip():
            raise serializers.ValidationError('name 不能为空')
        return value


class DictionaryItemSerializer(serializers.ModelSerializer):
    """字典项 — 含所属类型编码（typeCode）。"""

    type_code = serializers.CharField(source='type.code', read_only=True)

    class Meta:
        model = DictionaryItem
        fields = [
            'id', 'type', 'type_code', 'key', 'value',
            'sort_order', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'type_code']
        # type 在创建时由前端传 id, 编辑时不传 (保持所属类型不变);
        # key / value 在编辑时可能缺省 (只改排序 / 启停), 故均放宽为非必填;
        # 非空校验在 validate_key / validate_value 中按需兜底.
        extra_kwargs = {
            'type': {'required': False},
            'key': {'required': False},
            'value': {'required': False},
        }

    def validate_key(self, value: str) -> str:
        """key 非空。"""
        if not value or not value.strip():
            raise serializers.ValidationError('key 不能为空')
        return value

    def validate_value(self, value: str) -> str:
        """value 非空。"""
        if not value or not value.strip():
            raise serializers.ValidationError('value 不能为空')
        return value

    def get_validators(self):
        """移除自动生成的 UniqueTogetherValidator (默认英文 "must make a unique set"),
        改由下方 ``validate`` 做中文兜底, 错误打到 ``key`` 字段, 更易被前端映射。
        """
        validators = super().get_validators()
        return [
            v for v in validators
            if not (
                isinstance(v, UniqueTogetherValidator)
                and set(getattr(v, 'fields', [])) == {'type', 'key'}
            )
        ]

    def validate(self, attrs: dict) -> dict:
        """(type, key) 唯一性校验: 含软删记录占位 (DB 约束不认 deleted_at)。

        软删行仍占着 unique_together 坑位, 若只依赖 DB 写时拦截会落到
        IntegrityError → 500; 这里在校验阶段提前拦截并给出中文提示, 错误挂到 key 字段.
        """
        attrs = super().validate(attrs)
        instance = self.instance
        type_obj = attrs.get('type') or getattr(instance, 'type', None)
        key = attrs.get('key') or getattr(instance, 'key', None)
        if type_obj is None or key is None:
            return attrs
        qs = DictionaryItem.objects.filter(type=type_obj, key=key)
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {'key': ['该字典项下 key 已存在（同一字典类型下不可重复）']}
            )
        return attrs
