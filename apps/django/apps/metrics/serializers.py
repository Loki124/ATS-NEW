"""指标库序列化器。

字段命名遵循项目约定：内部 snake_case（DRF 字段），对外由全局 CamelCase 渲染器
输出 camelCase（sourcePath / dataType / atomicMetric ...）；请求体由 CamelCaseParser
把 camelCase 转回 snake_case，故前端可两种拼写混发。
"""
import calendar
from datetime import date, timedelta

from rest_framework import serializers

from apps.rule_engine.models import UnifiedOperator

from .models import (
    AtomicMetric,
    DerivedMetric,
    MetricRule,
    MetricTemplate,
    MetricTemplateVersion,
)
from .services.derived_registry import get as get_derived_func
from .services.rule_validators import validate_metric_rule


# ===== 日期型出参：单位即「粒度」，值域即「日期区间约束」 =====
# 日期没有量纲（不像 岁/元/月），所以「单位」唯一有意义的语义是日期精度（年/月/日），
# 它同时决定边界精度与枚举步长单位；值域因此不再是数值刻度，而是一段可选日期区间。
DATE_GRANULARITIES = ('年', '月', '日')
DATE_GRANULARITY_DEFAULT = '日'


def _shift_months(d: date, n: int) -> date:
    """按月偏移日期；日溢出时取该月最后一天（1月31日 +1月 → 2月28/29日）。"""
    total = d.year * 12 + (d.month - 1) + n
    y, m = divmod(total, 12)
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def resolve_date_bound(bound, today: date):
    """把日期边界解析成 date。

    - 绝对：{type:'absolute', date:'1950-01-01'}（按粒度可截断为 YYYY / YYYY-MM）
    - 相对：{type:'relative', n:-30, unit:'年'}，沿用平台 T±N 语义并扩到 年/月/日

    返回 None 表示未设置或无法解析（无法解析的边界交由校验层报错）。
    """
    if not isinstance(bound, dict):
        return None
    if bound.get('type') == 'relative':
        n = bound.get('n')
        if not isinstance(n, int) or isinstance(n, bool):
            return None
        unit = bound.get('unit') or DATE_GRANULARITY_DEFAULT
        if unit == '年':
            return _shift_months(today, n * 12)
        if unit == '月':
            return _shift_months(today, n)
        return today + timedelta(days=n)
    text = str(bound.get('date') or '').strip()
    if not text:
        return None
    # 补齐粒度：年 → YYYY-01-01；月 → YYYY-MM-01
    if len(text) == 4 and text.isdigit():
        text = f'{text}-01-01'
    elif len(text) == 7 and text[:4].isdigit():
        text = f'{text}-01'
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


class AtomicMetricSerializer(serializers.ModelSerializer):
    template_count = serializers.SerializerMethodField(read_only=True)
    # 编号由模型 save() 自动补号（editable=False），对外只读：前端展示，任何写端点改不动
    code = serializers.CharField(read_only=True)

    class Meta:
        model = AtomicMetric
        fields = [
            'id', 'code', 'name', 'source_path', 'data_type', 'unit', 'is_enum',
            'enum_values', 'description', 'status', 'auto_generated',
            'created_at', 'template_count',
        ]
        read_only_fields = ['id', 'code', 'created_at', 'template_count', 'auto_generated']

    def validate_source_path(self, value):
        if '.' not in (value or ''):
            raise serializers.ValidationError('字段路径必须包含 "." ，如 candidate.age')
        return value

    def get_template_count(self, obj):
        return obj.templates.count()


class DerivedMetricSerializer(serializers.ModelSerializer):
    template_count = serializers.SerializerMethodField(read_only=True)
    # 编号由模型 save() 自动补号（editable=False），对外只读
    code = serializers.CharField(read_only=True)

    class Meta:
        model = DerivedMetric
        fields = [
            'id', 'code', 'name', 'calc_func', 'base_path', 'data_type',
            'unit', 'description', 'status', 'created_at', 'template_count',
        ]
        read_only_fields = ['id', 'code', 'created_at', 'template_count']

    def validate_calc_func(self, value):
        if get_derived_func(value) is None:
            raise serializers.ValidationError(f'未注册的计算函数: {value}')
        return value

    def validate_base_path(self, value):
        if '.' not in (value or ''):
            raise serializers.ValidationError('数据来源路径必须包含 "." ，如 candidate.workExperience')
        return value

    def get_template_count(self, obj):
        return obj.templates.count()


class MetricTemplateSerializer(serializers.ModelSerializer):
    metric_name = serializers.SerializerMethodField(read_only=True)
    metric_path = serializers.SerializerMethodField(read_only=True)
    metric_kind = serializers.SerializerMethodField(read_only=True)
    data_type = serializers.SerializerMethodField(read_only=True)
    # LIFE-1：版本化只读字段
    version = serializers.IntegerField(read_only=True)
    version_count = serializers.IntegerField(read_only=True)
    # 编号由模型 save() 自动补号（editable=False），对外只读
    code = serializers.CharField(read_only=True)

    class Meta:
        model = MetricTemplate
        fields = [
            'id', 'code', 'name', 'atomic_metric', 'derived_metric',
            'metric_name', 'metric_path', 'metric_kind', 'data_type', 'unit',
            'param_unit',
            'operators', 'param_config', 'value_domain', 'param_enums',
            'calc_params', 'param_allow_null', 'status', 'description', 'created_at',
            'version', 'version_count',
        ]
        read_only_fields = [
            'id', 'code', 'created_at', 'metric_name', 'metric_path',
            'metric_kind', 'data_type', 'version', 'version_count',
        ]

    def validate(self, attrs):
        instance = self.instance
        atomic = attrs.get('atomic_metric',
                           instance.atomic_metric if instance else None)
        derived = attrs.get('derived_metric',
                            instance.derived_metric if instance else None)
        if (atomic is None) == (derived is None):
            raise serializers.ValidationError('模板必须且只能引用一个指标（原子指标或派生指标）')

        operators = attrs.get('operators')
        if operators is not None:
            if not operators:
                raise serializers.ValidationError('至少选择 1 个运算符')
            invalid = [op for op in operators if op not in UnifiedOperator.values]
            if invalid:
                raise serializers.ValidationError(f'不支持的运算符: {invalid}')

        # 出参类型由引用的指标决定：日期型走「粒度单位 + 日期区间值域」的独立口径
        metric = atomic or derived
        data_type = (metric.data_type if metric else '') or ''
        # 枚举型（is_enum）在存储上也是 string，靠标志位区分「有限候选集」与「自由文本」
        is_enum = bool(metric and getattr(metric, 'is_enum', False))
        is_date_output = data_type == 'date'
        is_free_text = data_type == 'string' and not is_enum
        unit = attrs.get('unit')
        if is_date_output and unit:
            if unit not in DATE_GRANULARITIES:
                raise serializers.ValidationError(
                    f'日期型出参的单位是日期粒度，只能取 {" / ".join(DATE_GRANULARITIES)}'
                )

        # 自由文本（如「职位名称」）无法穷举全集，允许配集合运算必然漏匹配 —— 从源头拦住。
        # 想要「命中一批值」应改用 包含 / 正则匹配（二者对无穷域语义成立）。
        if is_free_text and operators is not None:
            forbidden = [
                op for op in operators
                if op in (UnifiedOperator.IN, UnifiedOperator.NOT_IN)
            ]
            if forbidden:
                raise serializers.ValidationError(
                    '自由文本字段无法枚举全部取值，不能使用「属于集合 / 不属于集合」；'
                    '如需匹配多个值请改用「包含」或「正则匹配」'
                )

        # PRD BR-2/BR-3：离散型 step 必须为整数；自由区间（未设 min/max）允许留空
        self._validate_param_config(attrs.get('param_config'))
        self._validate_value_domain(attrs.get('value_domain'), data_type, is_enum)
        # 枚举候选值是条件目录渲染校验值下拉的唯一来源，此前无校验
        param_enums = attrs.get(
            'param_enums',
            instance.param_enums if instance else None,
        )
        self._validate_param_enums(param_enums, is_enum)

        # V13（指标级校验落地）：calc_params 必须符合引用派生指标的 param_schema 契约
        derived = attrs.get('derived_metric',
                            instance.derived_metric if instance else None)
        self._validate_calc_params(attrs.get('calc_params'), derived)
        return attrs

    @staticmethod
    def _validate_param_config(cfg):
        if cfg is None:
            return
        if not isinstance(cfg, dict):
            raise serializers.ValidationError('参数配置必须是对象')
        step = cfg.get('step')
        if step is not None:
            if not isinstance(step, (int, float)) or isinstance(step, bool):
                raise serializers.ValidationError('参数步长必须是数字')
            # 离散型（未设 min/max 视为自由，不强制整数；否则按 discrete 处理）
            has_range = cfg.get('min') is not None or cfg.get('max') is not None
            if has_range and isinstance(step, float) and not step.is_integer():
                raise serializers.ValidationError('离散型参数步长必须为整数')

    @staticmethod
    def _validate_calc_params(calc_params, derived_metric):
        """V13：模板 calc_params 必须符合引用派生指标（param_schema 契约）。

        对象路径指标（atomic/derived 无 param_schema）无需校验；未引用派生指标直接放行。
        校验项：key 在 schema 内、required 必填、select 取值∈options、类型基本一致。
        """
        if calc_params is None:
            return
        if not isinstance(calc_params, dict):
            raise serializers.ValidationError('计算参数必须是对象')
        if derived_metric is None:
            return
        func = get_derived_func(derived_metric.calc_func)
        schema = (func or {}).get('param_schema') or []
        if not schema:
            return
        allowed = {p['key']: p for p in schema}
        for key, val in calc_params.items():
            spec = allowed.get(key)
            if spec is None:
                raise serializers.ValidationError(f'计算参数「{key}」未在指标定义中声明')
            ptype = spec.get('type')
            if val is None:
                if spec.get('required'):
                    raise serializers.ValidationError(f'计算参数「{key}」为必填项')
                continue
            if ptype == 'number' and not isinstance(val, (int, float)) or isinstance(val, bool):
                raise serializers.ValidationError(f'计算参数「{key}」必须是数值')
            if ptype == 'select':
                options = [o.get('value') for o in (spec.get('options') or [])]
                if options and val not in options:
                    raise serializers.ValidationError(f'计算参数「{key}」取值不在允许范围内')
        for spec in schema:
            if spec.get('required') and calc_params.get(spec['key']) is None:
                raise serializers.ValidationError(f'计算参数「{spec["key"]}」为必填项')

    @staticmethod
    def _validate_date_value_domain(domain):
        """日期型出参的值域校验：值是「可选日期区间」，不是数值刻度。

        与数值分支的差异：
          - 步进必须是正整数（日期按粒度步进，小数步长没有意义）
          - 边界是绝对日期或相对今天的 T±N（年/月/日），必须能解析成真实日期
          - 起始必须早于结束；相邻区间不重叠
        """
        if domain is None:
            return
        if not isinstance(domain, dict):
            raise serializers.ValidationError('值域配置必须是对象')
        segments = domain.get('segments')
        if segments is None:
            return
        if not isinstance(segments, list):
            raise serializers.ValidationError('值域分段必须是数组')
        today = date.today()
        for i, seg in enumerate(segments):
            if not isinstance(seg, dict):
                raise serializers.ValidationError(f'值域分段#{i + 1}格式不正确')
            # 旧口径遗留：日期模板上存着数值 min/max，无法解释为日期，要求重配
            if 'min' in seg or 'max' in seg:
                raise serializers.ValidationError(
                    f'值域分段#{i + 1}为数值格式，日期型出参的值域必须是日期区间（起始/结束）'
                )
            step = seg.get('step')
            if step is None:
                raise serializers.ValidationError(f'值域分段#{i + 1}缺少步长')
            if not isinstance(step, int) or isinstance(step, bool) or step <= 0:
                raise serializers.ValidationError(f'值域分段#{i + 1}步长必须是正整数')
            step_unit = seg.get('stepUnit') or DATE_GRANULARITY_DEFAULT
            if step_unit not in DATE_GRANULARITIES:
                raise serializers.ValidationError(f'值域分段#{i + 1}步进粒度必须是 年/月/日')
            lo = resolve_date_bound(seg.get('from'), today)
            hi = resolve_date_bound(seg.get('to'), today)
            if lo is None and hi is None:
                raise serializers.ValidationError(f'值域分段#{i + 1}至少需要一个边界（起始或结束）')
            if lo is not None and hi is not None and lo >= hi:
                raise serializers.ValidationError(f'值域分段#{i + 1}起始日期必须早于结束日期')
        # 相邻分段不得重叠或共用边界（会枚举出重复的可选日期）
        ranged = []
        for i, seg in enumerate(segments):
            lo = resolve_date_bound(seg.get('from'), today)
            hi = resolve_date_bound(seg.get('to'), today)
            if lo is not None and hi is not None:
                ranged.append((i, lo, hi))
        ranged.sort(key=lambda x: x[1])
        for k in range(1, len(ranged)):
            if ranged[k][1] <= ranged[k - 1][2]:
                raise serializers.ValidationError(
                    f'值域分段#{ranged[k][0] + 1}与第 {ranged[k - 1][0] + 1} 段重叠或共用边界'
                )

    @staticmethod
    def _validate_param_enums(param_enums, is_enum=False):
        """枚举型模板的候选值清单校验（param_enums）。

        该字段是「进入条件字段目录」时渲染校验值下拉的唯一数据源
        （见 process.views._build_metric_template_catalog），此前无任何校验，
        空清单会让规则配置者面对一个空下拉。枚举型必须至少 1 项。
        """
        if param_enums is None:
            if is_enum:
                raise serializers.ValidationError('枚举型模板必须配置候选值列表（param_enums）')
            return
        if not isinstance(param_enums, list):
            raise serializers.ValidationError('候选值列表必须是数组')
        cleaned = []
        for i, v in enumerate(param_enums):
            if not isinstance(v, str):
                raise serializers.ValidationError(f'候选值#{i + 1}必须是文本')
            v = v.strip()
            if not v:
                raise serializers.ValidationError(f'候选值#{i + 1}不能为空')
            if v in cleaned:
                raise serializers.ValidationError(f'候选值「{v}」重复，请合并后重填')
            cleaned.append(v)
        if is_enum and not cleaned:
            raise serializers.ValidationError(
                '枚举型模板必须至少配置 1 个候选值，否则规则配置时无可选值'
            )

    @staticmethod
    def _validate_candidate_value_domain(domain, is_enum=False):
        """字符串类出参（枚举 / 自由文本）的值域校验。

        值域的含义是「有限候选集」—— 只有数值（可按区间枚举）、日期（可按粒度枚举）
        两类成立。字符串不是可枚举刻度：
          - 枚举型的取值集合由 param_enums 承载（并由条件目录直接消费），值域应为空
          - 自由文本是无穷域，没有值域可言，值域同样应为空
        历史脏数据里字符串型模板存着数值 segments（前端旧版把「非日期」一律当数值
        分段渲染导致），这里显式拦截，而不是默默按数值解释成「0 以上」这种无意义的集合。
        """
        if domain is None:
            return
        if not isinstance(domain, dict):
            raise serializers.ValidationError('值域配置必须是对象')
        # 🔴 2026-10-13 (兵哥) 实体引用型值域：人员 / 部门型出参虽以字符串输出，
        # 但对应具体对象，值域语义是「限定为哪些对象」而非数值刻度，
        # 故用顶层 kind 标记 + selector 指定选取方式，独立于 segments 分段。
        # 该键不存在时（即所有历史模板）继续走下方原有拦截逻辑 → 零行为变化。
        kind = domain.get('kind')
        if kind:
            MetricTemplateSerializer._validate_entity_value_domain(domain, str(kind))
            return
        segments = domain.get('segments')
        if segments:
            raise serializers.ValidationError(
                '字符串型出参不接受数值分段的值域配置：字符串不是可枚举刻度，请清空值域'
            )

    # 实体值域的合法取值：kind → {type: 是否需要绑定具体对象}
    #   person     指定人员=绑定用户；指定身份=绑定身份(role)；当前登录人=运行时取值
    #   department 指定部门=绑定管理单元；当前登录人所在部门=运行时取值
    _ENTITY_OPTION_TYPES = {
        'person': {
            'specified': True,
            'identity': True,
            'current_user': False,
        },
        'department': {
            'specified': True,
            'current_user_dept': False,
        },
    }

    @staticmethod
    def _validate_entity_value_domain(domain, kind):
        """实体引用型值域校验（人员 / 部门）。

        结构：{kind, options: [{type, ids: [...], label}]}
        语义与数值型 segments 一致 —— **模板层只限定可选范围（候选清单），
        具体选哪一个由应用方在使用时决定**，故此处不限制只能用一种取值方式。
        约束：type 必须在该 kind 白名单内；需绑定对象的类型必须至少有一个 id；
        当前登录人类型不得携带 id（值由运行时决定）。
        """
        spec = MetricTemplateSerializer._ENTITY_OPTION_TYPES.get(kind)
        if spec is None:
            raise serializers.ValidationError(f'未知的值域类型: {kind}')
        options = domain.get('options')
        if options is None:
            return
        if not isinstance(options, list):
            raise serializers.ValidationError('值域候选必须是数组')
        for i, opt in enumerate(options):
            if not isinstance(opt, dict):
                raise serializers.ValidationError(f'值域候选#{i + 1}格式不正确')
            otype = str(opt.get('type') or '')
            if otype not in spec:
                raise serializers.ValidationError(f'值域类型 {kind} 不支持的取值方式: {otype}')
            ids = opt.get('ids')
            if ids is not None and not isinstance(ids, list):
                raise serializers.ValidationError(f'值域候选#{i + 1} 的 ids 必须是数组')
            cleaned = [str(x).strip() for x in (ids or []) if str(x or '').strip()]
            if spec[otype] and not cleaned:
                raise serializers.ValidationError(f'值域候选#{i + 1} 需要至少选择一个对象')
            if not spec[otype] and cleaned:
                raise serializers.ValidationError(
                    '当前登录人取值由运行时决定，无需指定具体对象'
                )

    @staticmethod
    def _validate_value_domain(domain, data_type='number', is_enum=False):
        if domain is None:
            return
        if not isinstance(domain, dict):
            raise serializers.ValidationError('值域配置必须是对象')
        if data_type == 'date':
            MetricTemplateSerializer._validate_date_value_domain(domain)
            return
        if data_type == 'string':
            MetricTemplateSerializer._validate_candidate_value_domain(domain, is_enum)
            return
        segments = domain.get('segments')
        if segments is not None:
            if not isinstance(segments, list):
                raise serializers.ValidationError('值域分段必须是数组')
            for i, seg in enumerate(segments):
                if not isinstance(seg, dict):
                    raise serializers.ValidationError(f'值域分段#{i + 1}格式不正确')
                if 'min' not in seg or 'max' not in seg:
                    raise serializers.ValidationError(f'值域分段#{i + 1}缺少 min/max')
                if seg['min'] is not None and seg['max'] is not None and seg['min'] > seg['max']:
                    raise serializers.ValidationError(f'值域分段#{i + 1}最小值不能大于最大值')
            # 分段不得重叠或共用边界（否则会枚举出重复的校验值）——按 min 升序检查相邻段
            ranged = [
                (i, seg['min'], seg['max'])
                for i, seg in enumerate(segments)
                if isinstance(seg, dict)
                and isinstance(seg.get('min'), (int, float)) and not isinstance(seg.get('min'), bool)
                and isinstance(seg.get('max'), (int, float)) and not isinstance(seg.get('max'), bool)
            ]
            ranged.sort(key=lambda x: x[1])
            for k in range(1, len(ranged)):
                if ranged[k][1] <= ranged[k - 1][2]:
                    raise serializers.ValidationError(
                        f'值域分段#{ranged[k][0] + 1}与第 {ranged[k - 1][0] + 1} 段重叠或共用边界'
                    )

    def get_metric_name(self, obj):
        return obj.metric.name if obj.metric else ''

    def get_metric_path(self, obj):
        return obj.metric_path

    def get_metric_kind(self, obj):
        return obj.metric_kind

    def get_data_type(self, obj):
        return obj.data_type


class MetricTemplateVersionSerializer(serializers.ModelSerializer):
    """指标模板版本快照（只读）。快照不可经 API 增删改，整个序列化器只读。"""

    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = MetricTemplateVersion
        fields = [
            'id', 'template_id', 'version', 'snapshot', 'changed_fields',
            'change_kind', 'change_note', 'created_at', 'created_by',
        ]
        read_only_fields = fields


# 指标 vs 指标（方案 B）：右操作数为另一个指标模板时，仅允许这些对称比较运算符
METRIC_VS_METRIC_OPS = {'EQ', 'NEQ', 'GT', 'GTE', 'LT', 'LTE'}


class ConditionInputSerializer(serializers.Serializer):
    """单条条件输入（前端可发 templateId，view 层已归一化为 template_id）。"""
    template_id = serializers.CharField()
    operator = serializers.ChoiceField(choices=UnifiedOperator.choices)
    value = serializers.JSONField(required=False, allow_null=True, default=None)
    right_template_id = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=None,
    )
    meta = serializers.JSONField(required=False, default=dict)


class RuleExecuteSerializer(serializers.Serializer):
    """规则执行输入（一次性执行，不落库 —— 避免每次执行都产生垃圾规则记录）。"""
    conditions = ConditionInputSerializer(many=True, allow_empty=False)
    logic = serializers.ChoiceField(choices=[('AND', 'AND'), ('OR', 'OR')], required=False, default='AND')
    data = serializers.JSONField()


class MetricRuleSerializer(serializers.ModelSerializer):
    """指标规则序列化器 —— 持久化规则（支持新增/编辑/删除/启停）。"""

    condition_count = serializers.SerializerMethodField(read_only=True)
    # 关联需求 / 职位（外键，允许为空；前端 camelCase demandId/positionId
    # 经 CamelCaseParser 转为 demand_id/position_id，与字段名一致）。
    demand_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    position_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = MetricRule
        fields = [
            'id', 'name', 'description', 'scene', 'conditions', 'logic',
            'status', 'enabled', 'action_type',
            'demand_id', 'position_id',
            'created_at', 'condition_count',
        ]
        read_only_fields = ['id', 'created_at', 'condition_count']
        # 模型字段带 default=list → ModelSerializer 会生成 required=False，
        # 导致「不传 conditions」绕过 validate_conditions。显式要求必传。
        extra_kwargs = {'conditions': {'required': True}}

    def validate_conditions(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError('至少配置 1 个条件')
        for idx, cond in enumerate(value, start=1):
            if not isinstance(cond, dict):
                raise serializers.ValidationError(f'第 {idx} 个条件格式不正确')
            template_id = cond.get('templateId') or cond.get('template_id')
            operator = cond.get('operator')
            if not template_id:
                raise serializers.ValidationError(f'第 {idx} 个条件缺少 templateId')
            if operator not in UnifiedOperator.values:
                raise serializers.ValidationError(f'第 {idx} 个条件运算符不合法: {operator}')
            if not MetricTemplate.objects.filter(pk=template_id).exists():
                raise serializers.ValidationError(f'第 {idx} 个条件引用的模板不存在: {template_id}')

            # 方案 B：指标 vs 指标（右操作数为另一个指标模板）
            right_template_id = cond.get('rightTemplateId') or cond.get('right_template_id')
            needs_value = operator not in ('IS_EMPTY', 'IS_NOT_EMPTY')
            has_value = needs_value and ('value' in cond and cond.get('value') not in (None, ''))
            if right_template_id:
                if operator not in METRIC_VS_METRIC_OPS:
                    raise serializers.ValidationError(
                        f'第 {idx} 个条件「指标对比」仅支持 {sorted(METRIC_VS_METRIC_OPS)} 运算符')
                if has_value:
                    raise serializers.ValidationError(
                        f'第 {idx} 个条件不可同时设置对比指标与常量值')
                if not MetricTemplate.objects.filter(pk=right_template_id).exists():
                    raise serializers.ValidationError(
                        f'第 {idx} 个条件引用的对比模板不存在: {right_template_id}')
                # 类型一致性：左右模板 data_type 必须相同（均存在时强校验）
                # ⚠️ DB 查询留在 try 内，但**比较与 raise 必须在 try 外**：
                #   ValidationError 继承自 Exception，写在 try 内会被自己的 except 吞掉。
                # 定位过程（2026-10-07 变异测试）：把比较移回 try 内后，本断言仍不红——
                #   因为 services/rule_validators.py:101-112 另有一道独立校验（用 errors.append，
                #   不受 except 影响）。故此处属**冗余加固**，不是唯一防线；
                #   但仍应修正——「存得进 + 第一道防线失效」是脆弱设计，且两处规则需保持一致。
                lt = rt = None
                try:
                    lt = MetricTemplate.objects.filter(pk=template_id).first()
                    rt = MetricTemplate.objects.filter(pk=right_template_id).first()
                except Exception:  # noqa: BLE001 — DB 异常按 best-effort 跳过, 交由 rule_validators 兜底
                    pass
                if lt and rt and lt.data_type != rt.data_type:
                    raise serializers.ValidationError(
                        f'第 {idx} 个条件左右指标类型不一致（{lt.data_type} vs {rt.data_type}）')
            elif needs_value and not has_value:
                raise serializers.ValidationError(f'第 {idx} 个条件缺少比较值或对比指标')
        # T5：数值型条件值统一 coerce 为字符串，避免 JSON number → Python float
        # 序列化时的二进制精度丢失（INV-9）。仅对 int/float 生效，字符串/布尔/日期不动。
        return _coerce_numeric_strings(value)

    def validate(self, attrs):
        """请求态：规则级校验链（防御前端绕过）。

        field 级校验（validate_conditions）先行；此处跑规则级跨条件校验，
        返回人话中文错误，DRF 聚合后给出 400。

        部分更新（PATCH）容错：payload 未携带的字段回退到 self.instance 当前值，
        避免「只改 conditions」这类局部更新被 V05 的 scene 非空校验误杀。
        """
        instance = self.instance
        # 关联需求 / 职位：空串归一为 None（外键允许为空）；并做存在性校验，
        # 避免无效外键触发 DB 级 IntegrityError（500）。无效 id 直接 400 中文报错。
        for _f in ('demand_id', 'position_id'):
            if attrs.get(_f) in (None, ''):
                attrs[_f] = None
        if attrs.get('demand_id'):
            from apps.demand.models import Demand
            if not Demand.objects.filter(pk=attrs['demand_id']).exists():
                raise serializers.ValidationError({'demand_id': '关联需求不存在'})
        if attrs.get('position_id'):
            from apps.position.models import Position
            if not Position.objects.filter(pk=attrs['position_id']).exists():
                raise serializers.ValidationError({'position_id': '关联职位不存在'})
        errors = validate_metric_rule({
            'name': attrs.get('name', instance.name if instance else None),
            'scene': attrs.get('scene', instance.scene if instance else None),
            'logic': attrs.get('logic', instance.logic if instance else None),
            'conditions': attrs.get('conditions', instance.conditions if instance else None),
            'action_type': attrs.get(
                'action_type', getattr(instance, 'action_type', None) if instance else None),
            'id': instance.pk if instance else None,
        })
        if errors:
            raise serializers.ValidationError({'conditions': errors})
        return attrs

    def get_condition_count(self, obj):
        return len(obj.conditions or [])


def _coerce_numeric_strings(conditions):
    """把条件中的数值（int/float）就地转为字符串，保留 Decimal 精度语义。

    - 单值 value（GT/LT/EQ/...）
    - BETWEEN 的 meta.min / meta.max
    - IN / NOT_IN 的 value 数组元素
    bool 不处理（避免 True/False 被当数字）。
    """
    for cond in conditions:
        if not isinstance(cond, dict):
            continue
        operator = cond.get('operator')
        value = cond.get('value')
        if operator in ('IN', 'NOT_IN'):
            if isinstance(value, list):
                cond['value'] = [
                    str(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
                    for v in value
                ]
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            cond['value'] = str(value)
        if operator == 'BETWEEN':
            meta = cond.get('meta') or {}
            if isinstance(meta, dict):
                for k in ('min', 'max'):
                    mv = meta.get(k)
                    if isinstance(mv, (int, float)) and not isinstance(mv, bool):
                        meta[k] = str(mv)
                cond['meta'] = meta
    return conditions
