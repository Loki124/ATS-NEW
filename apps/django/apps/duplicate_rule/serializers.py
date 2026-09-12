"""重复候选人规则序列化器

⚠️ 字段名一律使用 **snake_case**：项目全局启用
``djangorestframework_camel_case`` 的 CamelCaseJSONRenderer / CamelCaseJSONParser，
API 边界自动完成 snake_case ↔ camelCase 转换（含嵌套 dict 的键）。
在序列化器里手写 camelCase 字段名会导致写路径解析不到字段（入参已被下划线化）。

约束（截图「新建候选人查重规则」）：
1. 至少添加 1 项强查重项或中查重项
2. 「任意 N 项」的 N 不得大于勾选的查重项数量
"""
from rest_framework import serializers

from .catalog import (
    FIELD_BY_KEY,
    LOGIC_ALL,
    LOGIC_ANY,
    LOGIC_CHOICES,
    SCOPE_CHOICES,
    STRENGTH_REQUIRED_ANY,
)
from .models import DuplicateRule
from .services import rule_condition_text, rule_items_text


def normalize_items(raw_items) -> list[dict]:
    """校验并归一化查重项。

    - 未知 key → 报错（避免脏 key 落库）
    - strength 一律以服务端 catalog 为准，忽略客户端传值
    - 去重（同 key 只保留一项）

    校验失败抛 ValueError，由调用方转成字段级 ValidationError。
    """
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError('至少添加 1 项查重项')

    seen: list[str] = []
    for item in raw_items:
        key = item.get('key') if isinstance(item, dict) else item
        if not key:
            raise ValueError('查重项缺少 key')
        if key not in FIELD_BY_KEY:
            raise ValueError(f'未知查重项：{key}')
        if key not in seen:
            seen.append(key)

    return [{'key': key, 'strength': FIELD_BY_KEY[key]['strength']} for key in seen]


class DuplicateRuleSerializer(serializers.ModelSerializer):
    """候选人查重规则序列化器"""

    scope = serializers.ChoiceField(choices=SCOPE_CHOICES, required=False)
    condition_logic = serializers.ChoiceField(choices=LOGIC_CHOICES, required=False)
    any_count = serializers.IntegerField(required=False, min_value=1)
    is_enabled = serializers.BooleanField(required=False)
    order_index = serializers.IntegerField(required=False)
    items = serializers.JSONField(required=False)
    # 只读展示列（前端表格直接用，避免两侧重复实现文案拼接）
    condition_text = serializers.SerializerMethodField()
    items_text = serializers.SerializerMethodField()

    class Meta:
        model = DuplicateRule
        fields = [
            'id', 'name', 'scope', 'is_system', 'condition_logic', 'any_count',
            'items', 'is_enabled', 'order_index',
            'condition_text', 'items_text', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_system', 'created_at', 'updated_at']

    def get_condition_text(self, obj) -> str:
        return rule_condition_text(obj)

    def get_items_text(self, obj) -> list[str]:
        return rule_items_text(obj)

    def validate_name(self, value: str) -> str:
        name = (value or '').strip()
        if not name:
            raise serializers.ValidationError('规则名称不能为空')
        if len(name) > 128:
            raise serializers.ValidationError('规则名称不超过 128 字')
        return name

    def validate(self, attrs):
        items = attrs.get('items')
        if items is not None:
            try:
                attrs['items'] = normalize_items(items)
            except ValueError as exc:
                raise serializers.ValidationError({'items': str(exc)}) from exc
            items = attrs['items']
        else:
            items = self.instance.items if self.instance else []

        # 截图约束：至少添加 1 项强查重项或中查重项
        strengths = {item.get('strength') for item in items if isinstance(item, dict)}
        if not strengths & set(STRENGTH_REQUIRED_ANY):
            raise serializers.ValidationError(
                {'items': '至少添加 1 项强查重项或中查重项'}
            )

        logic = attrs.get(
            'condition_logic',
            self.instance.condition_logic if self.instance else LOGIC_ALL,
        )
        any_count = attrs.get(
            'any_count',
            self.instance.any_count if self.instance else 1,
        )
        if logic == LOGIC_ANY and int(any_count) > len(items):
            raise serializers.ValidationError(
                {'any_count': f'任意项数不能大于勾选的查重项数量（{len(items)}）'}
            )
        if logic == LOGIC_ALL:
            attrs['any_count'] = 1
        return attrs
