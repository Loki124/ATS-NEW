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
            'id', 'code', 'name', 'en_name', 'tip', 'type', 'enabled',
            'created_at', 'updated_at', 'created_by_name',
        ]
        read_only_fields = ['id', 'code', 'type', 'created_at', 'updated_at', 'created_by_name']
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
        fields = ['id', 'parent_id', 'name', 'order', 'allow_custom', 'level', 'color', 'tag_ids']
        read_only_fields = ['id', 'level', 'color']

    def get_tag_ids(self, obj):
        # 业务只返回 enabled + 未软删的标签 id (Q-A5 缓存口径一致)
        return list(
            obj.assignments.filter(tag__enabled=True, tag__deleted_at__isnull=True)
            .order_by('order').values_list('tag_id', flat=True)
        )


class SceneAssignmentSerializer(serializers.ModelSerializer):
    """规则 ↔ 场景(入口)+类型。"""

    class Meta:
        model = RuleSceneAssignment
        fields = ['id', 'scene', 'recruit_type']
        read_only_fields = ['id']


class SceneAssignmentInputSerializer(serializers.Serializer):
    """wizard/save 的 scene_assignments 入参 (与输出用的 SceneAssignmentSerializer 区分):

    - 用纯 Serializer 而非 ModelSerializer, 避免 DRF 自动附加 UniqueTogetherValidator
      (RuleSceneAssignment 在 (scene, recruit_type) 上有全局 UNIQUE 约束, 自动校验器会
      把「被其他规则占用的组合」直接 400 拒绝, 而该冲突本应由服务层 _check_scene_conflicts
      排除当前规则后判定 → 抛 409 RULE_SCENE_CONFLICT)。
    - 合法性 (scene/recruit_type 取值 + 组合去重) 由 WizardSaveSerializer.validate_scene_assignments 统一校验。
    """

    scene = serializers.CharField()
    recruit_type = serializers.CharField()


class SceneRuleListSerializer(serializers.ModelSerializer):
    """规则列表 (轻量, 无嵌套)。"""

    scenes = serializers.SerializerMethodField()
    # camelCase 别名 (sandbox 用了 stub renderer 不做 snake↔camel 转换,
    # 这里手动暴露两种命名, 让前端 camelCase 调用也能命中)
    isSystem = serializers.BooleanField(source='is_system', read_only=True)
    maxSelectableTags = serializers.IntegerField(source='max_selectable_tags', read_only=True)
    # 终端用户选择原因弹窗的标题文案 (空=默认「选择原因」) — camelCase 别名
    modalTitle = serializers.CharField(source='modal_title', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    # 「预置默认规则」标识 (is_system AND name=='预置默认规则'): 覆盖全部场景×类型,
    # 不可调整 覆盖/名称/状态, 仅描述/可选标签上限/分类树可改。前端据此锁定 UI。
    isPresetDefault = serializers.SerializerMethodField()
    # 「原因数量」: 该规则绑定的「启用且未软删」标签 distinct 数量
    # (业务口径与 RuleCategoryFlatSerializer.get_tag_ids 一致:
    #  tag__enabled=True & tag__deleted_at__isnull=True, 关联路径
    #  categories__assignments__tag)。列表接口由 SceneRuleViewSet.get_queryset
    #  annotate 同名属性, 单实例 (retrieve/partial_update) 回退 ORM 查询。
    tag_count = serializers.SerializerMethodField()
    # camelCase 别名 (sandbox stub renderer 不做 snake↔camel 转换, 手动暴露)
    tagCount = serializers.SerializerMethodField()

    class Meta:
        model = SceneRule
        fields = [
            'id', 'name', 'is_system', 'isSystem', 'enabled', 'description',
            'max_selectable_tags', 'maxSelectableTags',
            'modal_title', 'modalTitle',
            'created_at', 'createdAt', 'updated_at', 'updatedAt', 'scenes',
            'tag_count', 'tagCount', 'isPresetDefault',
        ]
        read_only_fields = ['id', 'is_system', 'isSystem', 'created_at', 'createdAt', 'updated_at', 'updatedAt', 'isPresetDefault']

    def get_isPresetDefault(self, obj) -> bool:
        return bool(getattr(obj, 'is_preset_default', False))

    def get_scenes(self, obj) -> list:
        # 同一 scene 可能跨多个 recruit_type 出现, 去重后返回入口(场景)列表
        return list(dict.fromkeys(obj.scene_assignments.values_list('scene', flat=True)))

    def get_tag_count(self, obj) -> int:
        """snake_case 字段 — 该规则绑定的「启用且未软删」标签 distinct 数量。"""
        return self._tag_count(obj)

    def get_tagCount(self, obj) -> int:  # noqa: N802 - camelCase 别名, 与 isSystem 同风格
        """camelCase 别名 — 前端 rules 列表列 key='tagCount' 命中。"""
        return self._tag_count(obj)

    def _tag_count(self, obj) -> int:
        """核心取值逻辑 (snake / camel 两个字段共用, 避免重复查询)。

        - 列表接口 (list) 由 SceneRuleViewSet.get_queryset 用
          Count(..., distinct=True) annotate 了同名属性 tag_count, 优先读取,
          彻底规避 N+1;
        - 未 annotate 的单实例 (retrieve / partial_update 直接用
          SceneRuleListSerializer(rule) 序列化) 回退 ORM 查询,
          并缓存到实例属性 _cached_tag_count, 避免 get_tag_count 与
          get_tagCount 各查一次。
        """
        annotated = getattr(obj, 'tag_count', None)
        if annotated is not None:
            return annotated
        cached = getattr(obj, '_cached_tag_count', None)
        if cached is not None:
            return cached
        count: int = CategoryAssignment.objects.filter(
            category__rule=obj,
            tag__enabled=True,
            tag__deleted_at__isnull=True,
        ).values('tag').distinct().count()
        obj._cached_tag_count = count
        return count


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
        fields = ['id', 'name', 'is_system', 'enabled', 'description', 'max_selectable_tags', 'modal_title']
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
        fields = ['name', 'enabled', 'description', 'max_selectable_tags', 'modal_title']
        extra_kwargs = {
            'name': {'required': False},
            'enabled': {'required': False},
            'description': {'required': False},
            'max_selectable_tags': {'required': False},
            'modal_title': {'required': False},
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
    color = serializers.CharField(required=False, allow_blank=True, default='', allow_null=True)
    tag_ids = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
    )
    tagIds = serializers.ListField(
        child=serializers.CharField(), required=False, default=list, write_only=True,
    )

    def to_internal_value(self, data):
        """归一化 camelCase → snake_case, None → '', 走标准 is_valid 流程。"""
        normalized = dict(data)
        # 把 None 转为 '' (前端常见: 顶级分类 parentClientId=null / 未设色 color=null)
        for k in ('client_id', 'clientId', 'parent_client_id', 'parentClientId', 'color'):
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
    max_selectable_tags = serializers.IntegerField(required=False, default=5, min_value=0)
    # 终端用户选择原因弹窗的标题文案 (空=默认「选择原因」, 前端占位展示)
    modal_title = serializers.CharField(max_length=64, required=False, allow_blank=True, default='')
    categories = WizardCategorySerializer(many=True, required=False, default=list)
    scenes = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
    )
    recruit_types = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
    )
    # 显式 (场景,类型) 成对 — 优先于 scenes×recruit_types 笛卡尔积 (2026-09-22 重构)。
    # 数据结构: [{scene, recruit_type}, ...]; 与 RuleSceneAssignment 逐行存储口径一致。
    # 服务层约定: 非空列表 → 用作权威成对 (支持「场景A仅社招」这类子集);
    #           空列表/未提供 → 回退 scenes×recruit_types 笛卡尔积 (向后兼容旧前端)。
    scene_assignments = SceneAssignmentInputSerializer(many=True, required=False, default=list)
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

    def validate_recruit_types(self, value: list) -> list:
        from .models import RECRUIT_TYPES
        for r in value:
            if r not in RECRUIT_TYPES:
                raise serializers.ValidationError({'recruit_types': [f'非法招聘类型: {r}']})
        # 去重 + 保序
        return list(dict.fromkeys(value))

    def validate_scene_assignments(self, value: list) -> list:
        """校验显式 (场景,类型) 成对: scene/recruit_type 合法性 + 组合去重。

        与 scenes/recruit_types 笛卡尔积语义对齐, 但允许表达「场景A仅社招、场景B仅校招」
        这类子集 (笛卡尔积无法表示, 会引入歧义/误冲突)。
        """
        from .models import RECRUIT_TYPES, SCENE_OPTIONS
        seen = set()
        for item in value:
            s = (item or {}).get('scene')
            rt = (item or {}).get('recruit_type')
            if s not in SCENE_OPTIONS:
                raise serializers.ValidationError({'scene_assignments': [f'非法场景: {s}']})
            if rt not in RECRUIT_TYPES:
                raise serializers.ValidationError({'scene_assignments': [f'非法招聘类型: {rt}']})
            key = (s, rt)
            if key in seen:
                raise serializers.ValidationError({'scene_assignments': [f'场景+类型组合重复: {key}']})
            seen.add(key)
        return value


# ---------------------------------------------------------------------------
# Scene 全局视图 (T07)
# ---------------------------------------------------------------------------

class SceneBindingSerializer(serializers.Serializer):
    """GET /scenes/ 返回单条: {scene, recruitType, rule_id, rule_name}.

    兼容 camelCase (ruleId/ruleName/recruitType) — sandbox stub renderer 不做 snake↔camel 转换,
    这里显式归一化。
    """

    scene = serializers.CharField()
    recruit_type = serializers.CharField(required=False, allow_null=True, default='social')
    recruitType = serializers.CharField(required=False, allow_null=True, default='social', write_only=True)
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
        if not normalized.get('recruit_type') and normalized.get('recruitType'):
            normalized['recruit_type'] = normalized['recruitType']
        return super().to_internal_value(normalized)


class SceneBulkUpdateSerializer(serializers.Serializer):
    """PUT /scenes/ payload: [{scene, recruitType, rule_id}] — 全量替换绑定 (按 scene+type 组合)。"""

    items = SceneBindingSerializer(many=True)

    def validate_items(self, value: list) -> list:
        from .models import SCENE_OPTIONS
        seen = set()
        for it in value:
            key = (it['scene'], it.get('recruit_type') or 'social')
            if key in seen:
                raise serializers.ValidationError({'items': [f'场景+类型组合重复: {key}']})
            seen.add(key)
            if it['scene'] not in SCENE_OPTIONS:
                raise serializers.ValidationError({'items': [f'非法场景: {it["scene"]}']})
        return value
