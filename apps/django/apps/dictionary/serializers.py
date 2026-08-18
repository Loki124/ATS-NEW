"""数据字典序列化器。"""
import re

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import DictionaryItem, DictionaryType

# code / key 只允许字母、数字、下划线, 保证可作为标识符稳定使用.
CODE_PATTERN = re.compile(r'^[A-Za-z0-9_]+$')


class DictionaryTypeSerializer(serializers.ModelSerializer):
    """字典类型（列表 / 详情基础）。"""

    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DictionaryType
        fields = [
            'id', 'code', 'name', 'english_name', 'description',
            'dict_number', 'is_system', 'is_enabled',
            'created_by_name', 'created_at',
            'updated_by_name', 'updated_at',
        ]
        read_only_fields = [
            'id', 'dict_number', 'is_system',
            'created_by_name', 'created_at',
            'updated_by_name', 'updated_at',
        ]
        # code 创建时由前端提供 (同时作为 URL lookup), 编辑时随 URL 传入、不在 body 中,
        # 故放宽为非必填, 避免 PUT 整量更新因缺 code 触发 400; 创建时的必填在 __init__ 中保证.
        extra_kwargs = {
            'code': {'required': False},
        }

    def __init__(self, *args, **kwargs):
        """创建 (self.instance is None) 时 code 必填, 编辑时保持可选。"""
        super().__init__(*args, **kwargs)
        if self.instance is None:
            self.fields['code'].required = True

    def validate_code(self, value: str) -> str:
        """code 非空且只能含字母、数字、下划线。"""
        if not value or not value.strip():
            raise serializers.ValidationError('code 不能为空')
        if not CODE_PATTERN.match(value):
            raise serializers.ValidationError('code 只能包含字母、数字和下划线')
        return value

    def validate(self, attrs: dict) -> dict:
        """编辑时字典代码不可修改（PRD 4.2：创建后锁定）。"""
        attrs = super().validate(attrs)
        if self.instance is not None and 'code' in attrs:
            if attrs['code'] != self.instance.code:
                raise serializers.ValidationError(
                    {'code': ['字典代码创建后不可修改']}
                )
        return attrs

    def validate_name(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError('name 不能为空')
        return value

    def validate_english_name(self, value: str) -> str:
        # 英文名称允许留空，若填写则校验格式
        if value and not CODE_PATTERN.match(value):
            raise serializers.ValidationError('英文名称只能包含字母、数字和下划线')
        return value

    def get_created_by_name(self, obj) -> str:
        u = getattr(obj, 'created_by', None)
        return u.full_name if u else ''

    def get_updated_by_name(self, obj) -> str:
        u = getattr(obj, 'updated_by', None)
        return u.full_name if u else ''


class DictionaryItemFlatSerializer(serializers.ModelSerializer):
    """字典项（扁平, 含 parent_id, 供前端构建树形）。"""

    parent_id = serializers.PrimaryKeyRelatedField(
        source='parent',
        queryset=DictionaryItem.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = DictionaryItem
        fields = [
            'id', 'parent_id', 'key', 'value',
            'english_name', 'description', 'sort_order', 'is_active',
        ]


class DictionaryTypeDetailSerializer(DictionaryTypeSerializer):
    """字典类型详情, 含元素扁平列表（带 parent_id, 仅 live 项）。"""

    items = serializers.SerializerMethodField()

    class Meta(DictionaryTypeSerializer.Meta):
        fields = DictionaryTypeSerializer.Meta.fields + ['items']

    def get_items(self, obj):
        qs = obj.items.filter(deleted_at__isnull=True).order_by('sort_order', 'key')
        return DictionaryItemFlatSerializer(qs, many=True, context=self.context).data


class DictionaryItemSerializer(serializers.ModelSerializer):
    """字典项 — 含所属类型编码（type_code）与 parent_id。"""

    type_code = serializers.CharField(source='type.code', read_only=True)
    parent_id = serializers.PrimaryKeyRelatedField(
        source='parent',
        queryset=DictionaryItem.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = DictionaryItem
        fields = [
            'id', 'type', 'type_code', 'parent_id', 'key', 'value',
            'english_name', 'description', 'sort_order', 'is_active',
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
        if not value or not value.strip():
            raise serializers.ValidationError('key 不能为空')
        if not CODE_PATTERN.match(value):
            raise serializers.ValidationError('key 只能包含字母、数字和下划线')
        return value

    def validate_value(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError('value 不能为空')
        return value

    def validate_english_name(self, value: str) -> str:
        # 英文名称允许留空, 若填写则校验格式
        if value and not CODE_PATTERN.match(value):
            raise serializers.ValidationError('英文名称只能包含字母、数字和下划线')
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
        """(type, key) 唯一性校验: 含软删记录占位 (DB 约束不认 deleted_at)。"""
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
