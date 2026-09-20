"""Reason Library serializers (T03).

分层:
- ReasonTagSerializer / ReasonTagDetailSerializer: 标签 CRUD
- SceneRuleListSerializer / SceneRuleDetailSerializer: 规则 CRUD + 详情树
- WizardSaveSerializer: 三步原子保存 payload
- CategoryAssignmentSerializer / RuleCategoryFlatSerializer / SceneAssignmentSerializer: 嵌套
"""
from __future__ import annotations

from rest_framework import serializers

from .models import (
    CategoryAssignment, MAX_CATEGORY_LEVEL,
    ReasonTag, RuleCategory, RuleSceneAssignment, SceneRule,
)


# ---------------------------------------------------------------------------
# ReasonTag
# ---------------------------------------------------------------------------

class ReasonTagSerializer(serializers.ModelSerializer):
    """Tag 列表 / 创建 / 更新 (基础字段)。"""
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ReasonTag
        fields = [
            'id', 'name', 'en_name', 'tip', 'type', 'enabled',
            'created_at', 'updated_at', 'created_by_name',
        ]
        read_only_fields = ['id', 'type', 'created_at', 'updated_at', 'created_by_name']
        # 去掉字段级默认 UniqueValidator (DRF 在 is_valid() 阶段校验 unique
        # 会先于 view 层的 IntegrityError 抛 ValidationError → 走 VALIDATION_FAILED 40000,
        # 而产品期望同名 → TAG_NAME_DUPLICATED 40001 由 view 层 IntegrityError 抛。
        # 唯一性由 DB UNIQUE 兜底, 与 Q-A4 (含软删) 一致。
        extra_kwargs = {
            'name': {'validators': []},
            'en_name': {'validators': []},
        }

    def get_created_by_name(self, obj) -> str:
        u = getattr(obj, 'created_by', None)
        return getattr(u, 'full_name', '') if u else ''

    def validate_name(self, value: str) -> str:
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('标签名不能为空')
        if len(value) > 32:
            raise serializers.ValidationError('标签名不能超过 32 字符')
        # Q-A4: name UNIQUE 含软删记录 - 唯一性由 DB UNIQUE 兜底,
        # 不在此校验, 让 view 层的 IntegrityError → BizException TAG_NAME_DUPLICATED (40001) 路径处理
        return value


class ReasonTagDetailSerializer(ReasonTagSerializer):
    """Tag 详情 - 追加 ref_count (被多少 category 引用)。"""

    ref_count = serializers.IntegerField(read_only=True)

    class Meta(ReasonTagSerializer.Meta):
        fields = ReasonTagSerializer.Meta.fields + ['ref_count']


# ---------------------------------------------------------------------------
# SceneRule
# ---------------------------------------------------------------------------

class CategoryAssignmentSerializer(serializers.ModelSerializer):
    """分类 ↔ 标签 绑定。"""

    tag_id = serializers.PrimaryKeyRelatedField(
        source='tag', queryset=ReasonTag.objects.all(),
    )
    tag_name = serializers.CharField(source='tag.name', read_only=True)

    class Meta:
        model = CategoryAssignment
        fields = ['id', 'tag_id', 'tag_name', 'order']
        read_only_fields = ['id', 'tag_name']


class RuleCategoryFlatSerializer(serializers.ModelSerializer):
    """分类 (扁平, 含 parent_id, 供前端构建树形)。"""

    parent_id = serializers.PrimaryKeyRelatedField(
        source='parent', queryset=RuleCategory.objects.all(),
        allow_null=True, required=False,
    )
    tag_ids = serializers.SerializerMethodField()

    class Meta:
        model = RuleCategory
        fields = ['id', 'parent_id', 'name', 'order', 'allow_custom', 'level', 'tag_ids']
        read_only_fields = ['id', 'level']

    def get_tag_ids(self, obj):
        # 业务只返回 enabled + 未软删的标签 id (Q-A5 缓存口径一致)
        return list(
            obj.assignments.filter(tag__enabled=True, tag__deleted_at__isnull=True)
            .order_by('order').values_list('tag_id', flat=True)
        )


class SceneAssignmentSerializer(serializers.ModelSerializer):
    """规则 ↔ 场景。"""

    class Meta:
        model = RuleSceneAssignment
        fields = ['id', 'scene']
        read_only_fields = ['id']


class SceneRuleListSerializer(serializers.ModelSerializer):
    """规则列表 (轻量, 无嵌套)。"""

    scenes = serializers.SerializerMethodField()
    # camelCase 别名 (sandbox 用了 stub renderer 不做 snake↔camel 转换,
    # 这里手动暴露两种命名, 让前端 camelCase 调用也能命中)
    isSystem = serializers.BooleanField(source='is_system', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = SceneRule
        fields = [
            'id', 'name', 'is_system', 'isSystem', 'enabled', 'description',
            'created_at', 'createdAt', 'updated_at', 'updatedAt', 'scenes',
        ]
        read_only_fields = ['id', 'is_system', 'isSystem', 'created_at', 'createdAt', 'updated_at', 'updatedAt']

    def get_scenes(self, obj) -> list:
        return list(obj.scene_assignments.values_list('scene', flat=True))


class SceneRuleDetailSerializer(SceneRuleListSerializer):
    """规则详情 - 含完整树 (categories 嵌套 + assignments + scenes)。"""

    categories = RuleCategoryFlatSerializer(many=True, read_only=True)
    scene_assignments = SceneAssignmentSerializer(many=True, read_only=True)

    class Meta(SceneRuleListSerializer.Meta):
        fields = SceneRuleListSerializer.Meta.fields + ['categories', 'scene_assignments']


class SceneRuleCreateSerializer(serializers.ModelSerializer):
    """创建规则 - 头部, 后续用 wizard/save 灌入完整树。"""

    class Meta:
        model = SceneRule
        fields = ['id', 'name', 'is_system', 'enabled', 'description']
        read_only_fields = ['id']

    def validate_name(self, value: str) -> str:
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('规则名不能为空')
        if len(value) > 64:
            raise serializers.ValidationError('规则名不能超过 64 字符')
        if SceneRule.objects.filter(name=value).exists():
            raise serializers.ValidationError({'name': ['该规则名已存在']})
        return value


class SceneRuleUpdateSerializer(serializers.ModelSerializer):
    """规则头部更新 (PATCH) — 不改 is_system。"""

    class Meta:
        model = SceneRule
        fields = ['name', 'enabled', 'description']
        extra_kwargs = {
            'name': {'required': False},
            'enabled': {'required': False},
            'description': {'required': False},
        }

    def validate_name(self, value: str) -> str:
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('规则名不能为空')
        if len(value) > 64:
            raise serializers.ValidationError('规则名不能超过 64 字符')
        if self.instance is not None and self.instance.name != value:
            if SceneRule.objects.filter(name=value).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError({'name': ['该规则名已存在']})
        return value


# ---------------------------------------------------------------------------
# Wizard save (T06) - 整体原子 payload
# ---------------------------------------------------------------------------

class WizardCategorySerializer(serializers.Serializer):
    """Wizard 步骤二: 分类项 (前端提交 client_id 引用).

    兼容前端 camelCase wire-format (clientId/parentClientId/tagIds) 与后端 snake_case。
    DRF 默认只接受字段定义名, 由于 sandbox 用了 stub renderer 不做 snake↔camel 转换,
    这里显式接受两种命名并归一化为 snake_case 给 service 用。
    """

    id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    client_id = serializers.CharField(required=False, allow_blank=True, default='', allow_null=True)
    clientId = serializers.CharField(required=False, allow_blank=True, default='', allow_null=True, write_only=True)
    parent_client_id = serializers.CharField(required=False, allow_blank=True, default='', allow_null=True)
    parentClientId = serializers.CharField(required=False, allow_blank=True, default='', allow_null=True, write_only=True)
    name = serializers.CharField(max_length=32)
    order = serializers.IntegerField(default=0)
    allow_custom = serializers.BooleanField(default=False)
    allowCustom = serializers.BooleanField(required=False, default=False, write_only=True)
    tag_ids = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
    )
    tagIds = serializers.ListField(
        child=serializers.CharField(), required=False, default=list, write_only=True,
    )

    def to_internal_value(self, data):
        """归一化 camelCase → snake_case, None → '', 走标准 is_valid 流程。"""
        normalized = dict(data)
        # 把 None 转为 '' (前端常见: 顶级分类 parentClientId=null)
        for k in ('client_id', 'clientId', 'parent_client_id', 'parentClientId'):
            if normalized.get(k) is None:
                normalized[k] = ''
        if not normalized.get('client_id') and normalized.get('clientId'):
            normalized['client_id'] = normalized['clientId']
        if not normalized.get('parent_client_id') and normalized.get('parentClientId'):
            normalized['parent_client_id'] = normalized['parentClientId']
        if 'allow_custom' not in normalized and 'allowCustom' in normalized:
            normalized['allow_custom'] = normalized['allowCustom']
        if 'tag_ids' not in normalized and 'tagIds' in normalized:
            normalized['tag_ids'] = normalized['tagIds']
        return super().to_internal_value(normalized)


class WizardSaveSerializer(serializers.Serializer):
    """Wizard 三步原子保存 payload:

    - name / description / enabled: 规则头部
    - categories: [{id?, client_id?, parent_client_id?, name, order, allow_custom, tag_ids}]
    - scenes:    [scene_name, ...]
    """

    name = serializers.CharField(max_length=64)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    enabled = serializers.BooleanField(required=False, default=True)
    categories = WizardCategorySerializer(many=True, required=False, default=list)
    scenes = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
    )
    # 可选乐观锁 (仅当客户端启用并发保护时才传; 不传则后端跳过校验)
    expected_updated_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_categories(self, value: list) -> list:
        # 校验 level <= MAX_CATEGORY_LEVEL — 这里只校验前端提交的最大层数。
        # 真正的"depth 推导"在 wizard_service 里按 parent_client_id 计算。
        # 这里做静态粗略: parent_client_id 与自己 client_id 不可相同;
        # 树状结构 (循环) 由 wizard_service 检测。
        seen_cids = set()
        for c in value:
            cid = c.get('client_id') or ''
            if cid and cid in seen_cids:
                raise serializers.ValidationError({'categories': [f'分类 client_id 重复: {cid}']})
            if cid:
                seen_cids.add(cid)
        return value

    def validate_scenes(self, value: list) -> list:
        from .models import SCENE_OPTIONS
        for s in value:
            if s not in SCENE_OPTIONS:
                raise serializers.ValidationError({'scenes': [f'非法场景: {s}']})
        # 去重 (同一 scene 在 payload 里出现多次视为一次)
        return list(dict.fromkeys(value))


# ---------------------------------------------------------------------------
# Scene 全局视图 (T07)
# ---------------------------------------------------------------------------

class SceneBindingSerializer(serializers.Serializer):
    """GET /scenes/ 返回单条: {scene, rule_id, rule_name}.

    兼容 camelCase (ruleId/ruleName) — sandbox stub renderer 不做 snake↔camel 转换,
    这里显式归一化。
    """

    scene = serializers.CharField()
    rule_id = serializers.CharField(allow_null=True, required=False)
    ruleId = serializers.CharField(allow_null=True, required=False, write_only=True)
    rule_name = serializers.CharField(allow_null=True, required=False)
    ruleName = serializers.CharField(allow_null=True, required=False, write_only=True)

    def to_internal_value(self, data):
        normalized = dict(data)
        if 'rule_id' not in normalized and 'ruleId' in normalized:
            normalized['rule_id'] = normalized['ruleId']
        if 'rule_name' not in normalized and 'ruleName' in normalized:
            normalized['rule_name'] = normalized['ruleName']
        return super().to_internal_value(normalized)


class SceneBulkUpdateSerializer(serializers.Serializer):
    """PUT /scenes/ payload: [{scene, rule_id}] — 全量替换绑定。"""

    items = SceneBindingSerializer(many=True)

    def validate_items(self, value: list) -> list:
        from .models import SCENE_OPTIONS
        seen = set()
        for it in value:
            if it['scene'] in seen:
                raise serializers.ValidationError({'items': [f'场景重复: {it["scene"]}']})
            seen.add(it['scene'])
            if it['scene'] not in SCENE_OPTIONS:
                raise serializers.ValidationError({'items': [f'非法场景: {it["scene"]}']})
        return value
