"""动态字段定义 (G42) 的序列化器。

2026-08-04 修复 (寇豆码) — 重复 field_key 保存返回 500:
    ``DynamicField.Meta.unique_together = [('resource', 'field_key')]``,
    但 ``resource`` 在 ``read_only_fields`` 里, 不属于 ``_writable_fields``,
    DRF 的 ``get_unique_together_validators()`` 因此**跳过**了这条约束
    (它要求约束涉及的全部字段都可写)。结果校验层完全放行, 冲突一路撞到 DB,
    抛 ``IntegrityError (1062, Duplicate entry ...)`` → DRF 不认识 → HTTP 500。

    这里手写 ``validate()`` 把唯一性检查补回校验层, 冲突时返回 400 友好错误。

2026-09-08 增强 — 模块/分组/联动规则配置化:
    新增 ``FieldModuleSerializer`` / ``FieldGroupSerializer`` /
    ``FieldLinkageRuleSerializer``; ``DynamicFieldSerializer`` 读时嵌套返回
    ``module`` / ``group``, 写时通过 ``module_id`` / ``group_id`` 指定归属。
"""
from rest_framework import serializers

from .models import DynamicField, FieldGroup, FieldLinkageRule, FieldModule
from .system_fields import SYSTEM_FIELD_LOCKED_KEYS
from .validators import normalize_validation

#: (resource, field_key) 冲突时返回给前端的友好提示
DUPLICATE_FIELD_KEY_MESSAGE = '资源 {resource} 下已存在字段 Key "{field_key}", 请更换 Key 或直接编辑已有字段。'


class FieldModuleSerializer(serializers.ModelSerializer):
    """字段模块(父级) 序列化器。

    ``resource`` 由 URL 决定 (见 ``FieldModuleViewSet.perform_create``), 因此只读。
    """

    class Meta:
        model = FieldModule
        fields = '__all__'
        read_only_fields = ['id', 'resource', 'created_at', 'updated_at']


class FieldGroupSerializer(serializers.ModelSerializer):
    """字段分组(子级, 隶属模块) 序列化器。

    读: 嵌套返回所属 ``module``; 写: 通过 ``module_id`` 指定隶属模块。
    2026-09-24 (兵哥): 分组编码改由系统自动生成, 用户无需填写 —
    code 留空时 create 按 name 生成 (slugify; 中文名回退 grp_<nanoid>),
    模块内唯一 (含软删行, 因 unique_together 是 DB 级约束); update 不改动编码。
    """

    module = FieldModuleSerializer(read_only=True)
    module_id = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    code = serializers.CharField(required=False, allow_blank=True, max_length=128)

    class Meta:
        model = FieldGroup
        fields = [
            'id', 'module', 'module_id', 'code', 'name', 'order_index',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'module']

    @staticmethod
    def _generate_code(name: str, module_id) -> str:
        """按名称推导 snake_case code; 中文名推导为空时回退 grp_<nanoid>。

        查重用 _base_manager: unique_together ('module','code') 是 DB 级唯一索引,
        软删行同样占位, 必须一并排除才能避免 IntegrityError。
        """
        import re

        from django.utils.text import slugify
        from nanoid import generate as nanoid_generate

        base = re.sub(r'[^a-z0-9_]+', '_', slugify(name or '').replace('-', '_')).strip('_')
        if not base:
            base = 'grp_' + nanoid_generate('0123456789abcdefghijklmnopqrstuvwxyz', size=8)
        code, n = base, 2
        while FieldGroup._base_manager.filter(module_id=module_id, code=code).exists():
            code = f'{base}_{n}'
            n += 1
        return code[:128]

    def create(self, validated_data: dict):
        # 仅当显式传入 module_id 时才写入; 未传时不硬塞 None (交由 DB 层约束暴露真实必填问题)。
        # 原实现无条件 pop + 置 None, 会在「未传 module_id」时绕过 DRF 校验并退化为 IntegrityError。
        if 'module_id' in validated_data:
            validated_data['module_id'] = validated_data.pop('module_id') or None
        if not (validated_data.get('code') or '').strip():
            validated_data['code'] = self._generate_code(
                validated_data.get('name') or '', validated_data.get('module_id'),
            )
        return super().create(validated_data)

    def update(self, instance, validated_data: dict):
        # PATCH 部分更新: 仅当调用方**显式传入** module_id 时才改动, 否则保持原值。
        # 原实现无条件 pop + 置 None, 导致任何只带 order_index 的 PATCH 都会把
        # module_id 清空 → IntegrityError(1048, "Column 'module_id' cannot be null") → HTTP 500。
        if 'module_id' in validated_data:
            validated_data['module_id'] = validated_data.pop('module_id') or None
        # 编码不允许经编辑改动; 空值直接丢弃, 防止误清空已有编码。
        if not (validated_data.get('code') or '').strip():
            validated_data.pop('code', None)
        return super().update(instance, validated_data)


class FieldLinkageRuleSerializer(serializers.ModelSerializer):
    """同模块字段联动规则 序列化器(多条件 + 多动作)。

    读: 嵌套返回所属 ``module``; 写: 通过 ``module_id`` 指定隶属模块。
    conditions / actions 直接以 JSON 数组存取, 由前端保证结构。
    """

    module = FieldModuleSerializer(read_only=True)
    module_id = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = FieldLinkageRule
        fields = [
            'id', 'module', 'module_id', 'name', 'condition_mode',
            'conditions', 'actions', 'order_index',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'module']

    def create(self, validated_data: dict):
        # 仅当显式传入 module_id 时才写入; 未传时不硬塞 None (交由 DB 层约束暴露真实必填问题)。
        # 原实现无条件 pop + 置 None, 会在「未传 module_id」时绕过 DRF 校验并退化为 IntegrityError。
        if 'module_id' in validated_data:
            validated_data['module_id'] = validated_data.pop('module_id') or None
        return super().create(validated_data)

    def update(self, instance, validated_data: dict):
        # PATCH 部分更新: 仅当调用方**显式传入** module_id 时才改动, 否则保持原值。
        # 原实现无条件 pop + 置 None, 导致任何只带 order_index 的 PATCH 都会把
        # module_id 清空 → IntegrityError(1048, "Column 'module_id' cannot be null") → HTTP 500。
        if 'module_id' in validated_data:
            validated_data['module_id'] = validated_data.pop('module_id') or None
        return super().update(instance, validated_data)


class DynamicFieldSerializer(serializers.ModelSerializer):
    """动态字段定义序列化器。

    ``resource`` 由 URL 决定 (见 ``DynamicFieldViewSet.perform_create``), 因此是只读的;
    校验阶段通过 ``context['resource']`` 拿到它来做唯一性预检。

    2026-09-08 增强:
      - 读: 嵌套返回 ``module`` / ``group`` 配置对象。
      - 写: 通过 ``module_id`` / ``group_id`` 指定归属(可配置下拉);
            若指定 group, 自动同步 ``group_name``(兼容旧列表列)。
    """

    module = FieldModuleSerializer(read_only=True)
    group = FieldGroupSerializer(read_only=True)
    module_id = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    group_id = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    # 2026-09-27 系统内置字段: is_system 只读落库值; is_locked = is_system 且属核心标识三键
    is_system = serializers.BooleanField(read_only=True)
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = DynamicField
        fields = [
            'id', 'resource', 'field_key', 'label', 'field_type', 'is_required',
            'is_visible', 'placeholder', 'help_text', 'default_value', 'validation',
            'order_index', 'group_name', 'status', 'options', 'options_source',
            'module', 'group',
            'module_id', 'group_id',
            # 2026-09-14 增强: 英文字段名 + 确认题内容/声明 + 可见权限
            'label_en', 'confirmation_content', 'confirmation_content_en',
            'confirmation_declaration', 'confirmation_declaration_en',
            'visibility_permission',
            # 2026-09-15 行政区划型字段开关
            'with_country',
            # 2026-09-15 日期型字段格式精度(年/年月/年月日)
            'date_format',
            # 2026-09-15 行政区划型字段层级精度(省/省市/省市区)
            'region_level',
            # 2026-09-16 (兵哥): 组合字段子结构定义(仅 COMPOSITE 使用)
            'sub_fields',
            # 2026-09-27 (兵哥): 系统内置字段标记 + 核心标识锁定标记
            'is_system', 'is_locked',
        ]
        read_only_fields = ['id', 'resource', 'created_at', 'updated_at', 'module', 'group', 'is_system']

    def get_is_locked(self, obj) -> bool:
        return bool(obj.is_system) and obj.field_key in SYSTEM_FIELD_LOCKED_KEYS

    def to_representation(self, instance):
        """读时若配置了 ``options_source``, 按数据源解析并回填 ``options``。

        现有预览渲染器均消费 ``row.options``, 故在序列化层统一替换,
        渲染层零改动。解析失败/未配置时 ``resolve_options_source`` 返回 None, 保留手动 options。
        """
        data = super().to_representation(instance)
        resolved = DynamicField.resolve_options_source(getattr(instance, 'options_source', None))
        if resolved is not None:
            data['options'] = resolved
        return data

    def _apply_module_group(self, validated_data: dict) -> dict:
        """应用模块/分组归属, 并同步 ``group_name`` 冗余列。

        2026-09-09 修复: 原来只在 ``group_id`` 非空时写 ``group_name``,
        把字段的分组清空后冗余列仍留旧值, 列表回退显示
        ``row.group?.name || row.groupName`` 会展示已移除的分组名。
        现改为: 分组清空时同步清空 ``group_name``, 保持两者一致。
        """
        module_id = validated_data.pop('module_id', None) or None
        group_id = validated_data.pop('group_id', None) or None
        validated_data['module_id'] = module_id
        validated_data['group_id'] = group_id
        # 同步 group_name (兼容旧列表列显示)
        if group_id:
            grp = FieldGroup.objects.filter(id=group_id, deleted_at__isnull=True).first()
            if grp:
                validated_data['group_name'] = grp.name
            else:
                validated_data['group_name'] = ''
        else:
            # 分组被清空 → 冗余列一并清空, 避免残留旧分组名
            validated_data['group_name'] = ''
        return validated_data

    def create(self, validated_data: dict):
        validated_data = self._apply_module_group(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data: dict):
        validated_data = self._apply_module_group(validated_data)
        return super().update(instance, validated_data)

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
        """去空白 + 非空校验。"""
        field_key = (value or '').strip()
        if not field_key:
            raise serializers.ValidationError('字段 Key 不能为空。')
        return field_key

    def validate_validation(self, value):
        """按字段类型规范化 ``validation`` 限制条件 (2026-09-24 兵哥)。

        复用并规范化: 数字类容错旧 ``{min,max}`` 形态, 文本类/选项类规整为结构化 dict,
        非法键丢弃, message 缺省置空。空值/非 dict 直接归为 {} (无约束)。
        字段类型取自本次输入的 ``fieldType``/``field_type``; 编辑未改类型时回退实例类型。
        """
        raw_type = (
            self.initial_data.get('fieldType')
            or self.initial_data.get('field_type')
            or (getattr(self.instance, 'field_type', None))
        )
        return normalize_validation(raw_type, value)

    def validate(self, attrs: dict) -> dict:
        """在校验层拦截:

        - COMPOSITE 组合字段子结构合法性(**与 resource 无关, 始终执行**);
        - (resource, field_key) 唯一冲突, 避免 DB 层 IntegrityError → 500。
          create: 检查该 resource 下是否已有同名 field_key 的**存活**记录;
          update: 同上, 但排除自身 (改其它字段而不改 Key 时不能误报)。
        """
        # 2026-09-16 (兵哥): COMPOSITE 组合字段子结构校验(独立, 不依赖 resource 解析,
        #   否则无 context 场景下 resource 解析为空会提前 return, 漏掉本应拦截的非法子结构)
        field_type = attrs.get('field_type') or getattr(self.instance, 'field_type', '')
        if field_type == DynamicField.FieldType.COMPOSITE:
            subs = attrs.get('sub_fields')
            if not isinstance(subs, list) or not subs:
                raise serializers.ValidationError({
                    'sub_fields': ['组合字段至少需要 1 个子字段']
                })
            allowed = {
                DynamicField.FieldType.TEXT, DynamicField.FieldType.NUMBER,
                DynamicField.FieldType.MULTILINE_TEXT, DynamicField.FieldType.ATTACHMENT,
                DynamicField.FieldType.DATE, DynamicField.FieldType.PHONE,
                DynamicField.FieldType.EMAIL,
            }
            seen = set()
            for i, sub in enumerate(subs):
                if not isinstance(sub, dict):
                    raise serializers.ValidationError({'sub_fields': [f'子字段 #{i+1} 结构非法']})
                skey = (sub.get('key') or '').strip()
                stype = sub.get('type')
                if not skey:
                    raise serializers.ValidationError({'sub_fields': [f'子字段 #{i+1} 缺少 key']})
                if skey in seen:
                    raise serializers.ValidationError({'sub_fields': [f'子字段 key 重复: {skey}']})
                seen.add(skey)
                if stype not in allowed:
                    raise serializers.ValidationError({
                        'sub_fields': [f'子字段 {skey} 类型 {stype} 不支持, 仅允许 {sorted(allowed)}']
                    })

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
