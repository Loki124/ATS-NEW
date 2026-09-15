from django.db import models
from nanoid import generate as nanoid_generate

from apps.common.models import TimestampedModel, SoftDeleteModel


class DynamicField(TimestampedModel, SoftDeleteModel):
    """动态字段定义 — 允许管理员为不同 resource (Candidate/Position等) 自定义字段"""

    class VisibilityPermission(models.TextChoices):
        """字段可见权限（图3 权限管理弹窗的两个选项）。"""
        ALL_VISIBLE = 'ALL_VISIBLE', '全员可见'
        MANAGER_HIDDEN = 'MANAGER_HIDDEN', '用人经理端不可见'

    class FieldType(models.TextChoices):
        TEXT = 'TEXT', '文本'
        NUMBER = 'NUMBER', '数字'
        DATE = 'DATE', '日期'
        SELECT = 'SELECT', '单选'
        MULTISELECT = 'MULTISELECT', '多选'
        BOOLEAN = 'BOOLEAN', '布尔'
        # 2026-09-08 新增专用类型
        ATTACHMENT = 'ATTACHMENT', '附件'
        ID_CARD = 'ID_CARD', '身份证'
        BANK_CARD = 'BANK_CARD', '银行卡'
        PHONE = 'PHONE', '手机号'
        EMAIL = 'EMAIL', '邮箱'
        # 2026-09-09 新增列表型(非下拉, 选项以列表渲染, 容器宽度自适应横/纵)
        LIST_SINGLE = 'LIST_SINGLE', '列表单选'
        LIST_MULTI = 'LIST_MULTI', '列表多选'
        # 2026-09-14 动态字段拆分后新增「确认题」(带确认内容与确认声明)
        CONFIRM = 'CONFIRM', '确认题'
        # 2026-09-14 新增「多行文本」(长文本输入, 渲染为多行 textarea)
        MULTILINE_TEXT = 'MULTILINE_TEXT', '多行文本'
        # 2026-09-15 新增「地址」(单行文本输入, 预览/申请表独占整行; 后端无专属校验)
        ADDRESS = 'ADDRESS', '地址'
        # 2026-09-15 新增行政区划级联型(省/省市/省市区)
        # 存储为 JSON: {country?: {code,name}, province: {code,name}, city?: {code,name}, district?: {code,name}}
        REGION_PROVINCE = 'REGION_PROVINCE', '省'
        REGION_PROVINCE_CITY = 'REGION_PROVINCE_CITY', '省市'
        REGION_PROVINCE_CITY_DISTRICT = 'REGION_PROVINCE_CITY_DISTRICT', '省市区'

    # 需要选项配置(下拉/列表)的字段类型
    OPTION_TYPES = [
        FieldType.SELECT, FieldType.MULTISELECT,
        FieldType.LIST_SINGLE, FieldType.LIST_MULTI,
    ]

    # 确认题类型(带确认内容/确认声明)
    CONFIRM_TYPES = [FieldType.CONFIRM]

    id = models.CharField(
        max_length=32, primary_key=True, editable=False, help_text='唯一标识'
    )
    resource = models.CharField(max_length=128, db_index=True, help_text='资源类型 (Candidate/Position/...)')
    field_key = models.CharField(max_length=128, help_text='字段 key (snake_case)')
    label = models.CharField(max_length=256, help_text='显示名称')
    field_type = models.CharField(max_length=32, choices=FieldType.choices, default=FieldType.TEXT)
    is_required = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    placeholder = models.CharField(max_length=512, blank=True, default='')
    help_text = models.CharField(max_length=512, blank=True, default='')
    default_value = models.CharField(max_length=512, blank=True, default='')
    validation = models.JSONField(default=dict, blank=True, help_text='校验规则 JSON')
    order_index = models.IntegerField(default=0)
    group_name = models.CharField(max_length=128, blank=True, default='')
    # 2026-09-08: 模块(父)/分组(子) 配置化, 字段新增/编辑时可直接下拉选择
    module = models.ForeignKey(
        'FieldModule', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fields', help_text='归属模块(可配置)',
    )
    group = models.ForeignKey(
        'FieldGroup', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fields', help_text='字段分组(可配置)',
    )
    status = models.CharField(max_length=32, default='active')
    options = models.JSONField(default=list, blank=True, help_text='选项列表 [{value, label}]')
    # 2026-09-15 选项来源 (兵哥): 下拉/列表型字段除手动维护选项外, 可指定数据源动态解析
    # 结构: {"type": "custom"|"dictionary"|"library"|"code_table", "key": "..."}
    #   - custom / 空 => 使用本字段的 options (手动维护)
    #   - dictionary   => key = 字典类型 code, 取该字典下 is_active 的 item (value=item.key, label=item.value)
    #   - library      => key = major (专业库), 未来可扩展 school/company
    #   - code_table   => 预留: 国标码表 (regions/countries/ethnicities/languages)
    # 读时由 serializer.to_representation 按此解析并回填 options, 使现有预览渲染器零改动。
    options_source = models.JSONField(
        default=dict, blank=True,
        help_text='选项来源 {type, key}; 非空时选项由对应数据源动态解析并覆盖手动 options',
    )
    # 2026-09-14 动态字段拆分增强: 英文字段名 + 确认题内容/声明 + 可见权限
    label_en = models.CharField(max_length=256, blank=True, default='', help_text='字段名称(英文)')
    confirmation_content = models.TextField(blank=True, default='', help_text='确认题-确认内容(中文)')
    confirmation_content_en = models.TextField(blank=True, default='', help_text='确认题-确认内容(英文)')
    confirmation_declaration = models.TextField(blank=True, default='', help_text='确认题-确认声明(中文)')
    confirmation_declaration_en = models.TextField(blank=True, default='', help_text='确认题-确认声明(英文)')
    visibility_permission = models.CharField(
        max_length=32, choices=VisibilityPermission.choices,
        default=VisibilityPermission.ALL_VISIBLE, help_text='可见权限(字段权限管理弹窗)',
    )
    # 2026-09-15 行政区划型字段专用: 是否先选国家(影响渲染层是否首列下拉国家, 与字段类型独立)
    with_country = models.BooleanField(
        default=False, help_text='行政区划型字段是否先选国家(仅 REGION_* 渲染时参考)',
    )

    class Meta:
        db_table = 'dynamic_fields'
        unique_together = [('resource', 'field_key')]
        ordering = ['resource', 'order_index']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.resource}/{self.field_key}'

    @staticmethod
    def resolve_options_source(options_source: dict | None) -> list | None:
        """按 ``options_source`` 解析出选项列表; 不支持 / 未配置 / 解析失败均返回 ``None``。

        返回 ``None`` 时调用方应回退到手动维护的 ``options`` 字段, 不改变既有行为。
        支持类型:
          - ``dictionary``: key = 字典类型 code, 取该字典 is_active 的 item
                            (value=item.key, label=item.value, 按 sort_order/key 排序)
          - ``library``   : key = ``major``(专业库) / ``school``(院校库)
                            取 library_major (value=code, label=name)
          - ``code_table``: key = ``country`` / ``ethnicity`` / ``language``
                            取 G46 码表库对应表 (country: name_cn; ethnicity/language: name 或 name_cn)

        延迟导入 dictionary/library/code_table 模型, 避免模块加载期循环依赖。
        """
        if not options_source or not isinstance(options_source, dict):
            return None
        src_type = options_source.get('type')
        key = options_source.get('key')
        if not src_type or src_type == 'custom' or not key:
            return None
        try:
            if src_type == 'dictionary':
                from apps.dictionary.models import DictionaryItem
                items = (
                    DictionaryItem.objects
                    .filter(
                        type__code=key,
                        type__deleted_at__isnull=True,
                        deleted_at__isnull=True,
                        is_active=True,
                    )
                    .select_related('type')
                    .order_by('sort_order', 'key')
                )
                return [{'value': it.key, 'label': it.value} for it in items]
            if src_type == 'library':
                if key == 'major':
                    from apps.library.models import Major
                    majors = (
                        Major.objects
                        .filter(deleted_at__isnull=True)
                        .order_by('name', 'code')
                    )
                    return [{'value': m.code, 'label': m.name} for m in majors]
                if key == 'school':
                    # 2026-09-15 院校库: 2744 所一次性返回, 走 library/ 端点 keyword 服务端过滤
                    from apps.library.models import School
                    schools = (
                        School.objects
                        .filter(deleted_at__isnull=True)
                        .order_by('name', 'code')
                    )
                    return [{'value': s.code, 'label': s.name} for s in schools]
                # 公司库 (company) 走下一轮
            if src_type == 'code_table':
                # 2026-09-15 码表库 (G46): 民族/语言/国家, 端点已在 apps/code_table/views.py 暴露
                if key in ('country', 'ethnicity', 'language'):
                    from apps.code_table.models import Country, Ethnicity, Language
                    if key == 'country':
                        qs = Country.objects.all().order_by('name_cn')
                        return [{'value': c.code, 'label': c.name_cn} for c in qs]
                    if key == 'ethnicity':
                        qs = Ethnicity.objects.all().order_by('code')
                        return [{'value': e.code, 'label': e.name} for e in qs]
                    if key == 'language':
                        qs = Language.objects.all().order_by('code')
                        return [{'value': l.code, 'label': l.name_cn} for l in qs]
        except Exception:  # noqa: BLE001 — 解析失败安全降级到手动 options
            return None
        return None


class FieldModule(TimestampedModel, SoftDeleteModel):
    """字段模块(父级) — 可配置, 字段归属某个模块。

    例: resource=Candidate, module=「候选人信息」「教育经历」。
    """

    id = models.CharField(max_length=32, primary_key=True, editable=False, help_text='唯一标识')
    resource = models.CharField(max_length=128, db_index=True, help_text='资源类型 (Candidate/Position/...)')
    code = models.CharField(max_length=128, help_text='模块 code (snake_case)')
    name = models.CharField(max_length=256, help_text='模块显示名称')
    description = models.CharField(max_length=512, blank=True, default='')
    order_index = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'dynamic_field_modules'
        unique_together = [('resource', 'code')]
        ordering = ['resource', 'order_index']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.resource}/{self.code}'


class FieldGroup(TimestampedModel, SoftDeleteModel):
    """字段分组(子级, 隶属于模块) — 字段新增/编辑时可直接下拉选择。"""

    id = models.CharField(max_length=32, primary_key=True, editable=False, help_text='唯一标识')
    module = models.ForeignKey(FieldModule, on_delete=models.CASCADE, related_name='groups')
    code = models.CharField(max_length=128, help_text='分组 code (snake_case)')
    name = models.CharField(max_length=256, help_text='分组显示名称')
    order_index = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'dynamic_field_groups'
        unique_together = [('module', 'code')]
        ordering = ['module', 'order_index']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.module.code}/{self.code}'


class FieldLinkageRule(TimestampedModel, SoftDeleteModel):
    """同模块字段联动规则(多条件 + 多动作)。

    参考设计: 条件区域支持「满足全部/满足任一」; 一条条件 = 字段 + 操作符 + 值;
    动作区域支持多条, 每条 = 目标字段 + 动作类型 + 值 + 是否只读。

    condition_mode: 多条件之间的组合方式
    conditions: [{field_key, op, value}]
    actions:    [{target_field_key, action_type, value, read_only}]
    """

    class ConditionMode(models.TextChoices):
        ALL = 'ALL', '满足以下所有条件'
        ANY = 'ANY', '满足以下任一条件'

    class ConditionOp(models.TextChoices):
        EQ = 'EQ', '等于'
        NE = 'NE', '不等于'
        IN = 'IN', '包含'
        NOT_IN = 'NOT_IN', '不包含'
        GT = 'GT', '大于'
        LT = 'LT', '小于'
        GTE = 'GTE', '大于等于'
        LTE = 'LTE', '小于等于'
        CONTAINS = 'CONTAINS', '包含文本'

    class ActionType(models.TextChoices):
        SHOW = 'SHOW', '显示'
        HIDE = 'HIDE', '隐藏'
        REQUIRE = 'REQUIRE', '设必填'
        SET_VALUE = 'SET_VALUE', '赋值'
        READONLY = 'READONLY', '只读'
        CASCADE_OPTIONS = 'CASCADE_OPTIONS', '级联选项'

    id = models.CharField(max_length=32, primary_key=True, editable=False, help_text='唯一标识')
    module = models.ForeignKey(FieldModule, on_delete=models.CASCADE, related_name='linkage_rules')
    name = models.CharField(max_length=256, blank=True, default='', help_text='规则名称')
    condition_mode = models.CharField(
        max_length=16, choices=ConditionMode.choices, default=ConditionMode.ALL,
        help_text='多条件组合方式',
    )
    conditions = models.JSONField(
        default=list, blank=True,
        help_text='条件列表 [{field_key, op, value}]',
    )
    actions = models.JSONField(
        default=list, blank=True,
        help_text='动作列表 [{target_field_key, action_type, value, read_only}]',
    )
    order_index = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'dynamic_field_linkage_rules'
        ordering = ['module', 'order_index']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.module.code}/{self.name or "未命名规则"}'
