"""数据权限规则序列化器。

项目全局启用 djangorestframework-camel-case, 此处一律用 snake_case 字段名,
API 层自动转 camelCase (前端契约: dimensionType / dimensionValue / scopeType ...)。
"""
from rest_framework import serializers

from .expr_compiler import validate_scope_payload
from .field_map import MODULE_ORDER
from .models import DataPermissionRule, DataPermTemplate, RowScopeType
from .scope_templates import TemplateBindError, instantiate, unbound_placeholders


class DataPermissionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataPermissionRule
        fields = [
            'id',
            'dimension_type', 'dimension_value', 'level',
            'scope_type', 'scope_payload',
            'entity', 'field', 'permission',
            'priority', 'status', 'remark', 'created_by',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        scope_type = attrs.get('scope_type')
        payload = attrs.get('scope_payload')
        if scope_type == RowScopeType.CUSTOM:
            if not isinstance(payload, dict):
                raise serializers.ValidationError({'scope_payload': 'CUSTOM 范围需为对象'})
            if 'groups' in payload:
                # 新格式（数据权限向导）：{expr, groups}
                entity = attrs.get('entity')
                if not entity:
                    raise serializers.ValidationError(
                        {'entity': 'CUSTOM 表达式范围需指定 entity（业务模块 key）'})
                reason = validate_scope_payload(payload, entity)
                if reason:
                    raise serializers.ValidationError({'scope_payload': reason})
            else:
                # 兼容旧格式 {"department_ids":[...]} / {"management_unit_ids":[...]}
                if not (payload.get('department_ids') or payload.get('management_unit_ids')):
                    raise serializers.ValidationError(
                        {'scope_payload': 'CUSTOM 范围需提供 groups 或 department_ids/management_unit_ids'})
        return attrs


class DataPermTemplateSerializer(serializers.ModelSerializer):
    """数据权限模板序列化器。

    模板体groups 里允许 ${paramKey} 占位符，因此**不能**直接用
    validate_scope_payload 校验（那会把占位符当非法值）。改为：
      1. 用 default 参数试绑定一次（params[].default）—— 能绑通说明结构合法；
      2. 绑定结果再交给 validate_scope_payload 做完整校验。
    """

    class Meta:
        model = DataPermTemplate
        fields = [
            'id', 'code', 'name', 'module_key', 'description',
            'groups', 'params', 'status', 'version',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'code', 'version', 'created_at', 'updated_at']

    def validate(self, attrs):
        module_key = attrs.get('module_key')
        if module_key and module_key not in MODULE_ORDER:
            raise serializers.ValidationError(
                {'module_key': f'不支持的模块：{module_key}'})

        groups = attrs.get('groups')
        if groups is not None:
            if not isinstance(groups, list) or not groups:
                raise serializers.ValidationError({'groups': '模板需至少 1 个条件组'})
            if not module_key:
                raise serializers.ValidationError(
                    {'module_key': '模板需指定适用模块才能校验条件'})

        params = attrs.get('params')
        if params is not None and not isinstance(params, list):
            raise serializers.ValidationError({'params': '参数声明需为列表'})

        # 用 default 试绑定（绑定失败说明模板结构本身有问题）
        if groups and module_key:
            defaults = {}
            for p in (params or []):
                if isinstance(p, dict) and p.get('key') and p.get('default') is not None:
                    defaults[p['key']] = p['default']
            missing = unbound_placeholders(groups) - set(defaults)
            required_without_default = {
                p['key'] for p in (params or [])
                if isinstance(p, dict) and p.get('key') and p.get('required')
                and p.get('default') is None
            }
            leftover = missing - required_without_default
            if leftover:
                raise serializers.ValidationError(
                    {'groups': f'存在未声明的占位符：{"、".join(sorted(leftover))}'})
            try:
                instantiate(
                    _ProbeTemplate(module_key, groups, params or []),
                    defaults,
                )
            except TemplateBindError as e:
                raise serializers.ValidationError({'groups': str(e)})
        return attrs


class _ProbeTemplate:
    """轻量探针对象：让 instantiate() 能校验「尚未落库」的模板体。"""

    def __init__(self, module_key, groups, params):
        self.module_key = module_key
        self.groups = groups
        self.params = params
        self.code = 'PROBE'
        self.version = 0
        self.name = '探针'


class TemplatePreviewSerializer(serializers.Serializer):
    """模板试算绑定入参（preview-bind 端点）。"""

    bindings = serializers.JSONField(required=False, default=dict)
