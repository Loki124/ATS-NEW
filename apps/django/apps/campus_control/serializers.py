"""人员比例管控系统 v2.4 — 序列化器与校验。

校验要点：
- Rule：(bu, position, level, dimension, indicator, year) 唯一；indicator 须属于 dimension；
  target 0~1；年/月人数目标归一；单条编辑仅拦「超 100%」（防溢出），恰好 ==100% 由批量端点强制。
- 适用范围：bu/position/level 均可空（空 = 不限 / 全局）。
- 取消原 lo/hi 上下限配置；人数目标（annual_target / monthly_targets）直接承载于规则。
"""
import re
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.validators import UniqueTogetherValidator

from .constants import (
    DEGREES,
    DEPTS,
    EDUCATIONS,
    EMPLOYED_STATUSES,
    EMPLOYEE_ID_PATTERN,
    LEVELS,
    MAJORS,
    PENDING_STATUSES,
    POSITIONS,
    SCHOOLS,
    SEXES,
    STATUS,
    STRENGTH,
)
from .models import (
    BatchNaming,
    BatchRule,
    ControlDimension,
    ControlIndicator,
    ControlRule,
    Person,
    PersonEducation,
)


class PersonEducationSerializer(serializers.ModelSerializer):
    """教育经历子记录（聂荣 2026-10-23 口径：个人档案「教育经历 · 院校标签就高原则」）。

    院校标签 / 学历都是枚举 → 用 ChoiceField 把默认英文报错换成中文业务提示（R-203）。
    """

    school_tag = serializers.ChoiceField(
        choices=[(s, s) for s in SCHOOLS],
        required=False, allow_blank=True, default='',
        error_messages={'invalid_choice': '院校标签非法'},
    )
    education = serializers.ChoiceField(
        choices=[(e, e) for e in EDUCATIONS],
        required=False, allow_blank=True, default='',
        error_messages={'invalid_choice': '学历非法'},
    )

    class Meta:
        model = PersonEducation
        fields = ['id', 'school_name', 'school_tag', 'major_name', 'education']
        read_only_fields = ['id']


def _to_decimal(v):
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _validate_scope_fields(attrs):
    """校验适用范围字段（bu/position/level 均可空，非空时须在枚举内）。"""
    bu = attrs.get('bu')
    if bu and bu not in DEPTS:
        raise DRFValidationError({'bu': ['部门非法']})
    pos = attrs.get('position')
    if pos and pos not in POSITIONS:
        raise DRFValidationError({'position': ['职务非法']})
    lvl = attrs.get('level')
    if lvl and lvl not in LEVELS:
        raise DRFValidationError({'level': ['职级非法']})
    # 归一为空串
    attrs['bu'] = bu or ''
    attrs['position'] = pos or ''
    attrs['level'] = lvl or ''


class ControlDimensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlDimension
        fields = ['id', 'name', 'code', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('维度名称必填')
        qs = ControlDimension.objects.filter(name=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('该维度已存在')
        return value


class ControlIndicatorSerializer(serializers.ModelSerializer):
    dimension_name = serializers.SerializerMethodField()

    class Meta:
        model = ControlIndicator
        fields = ['id', 'dimension', 'dimension_name', 'name', 'is_active',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'dimension_name', 'created_at', 'updated_at']

    def get_dimension_name(self, obj):
        return obj.dimension.name if obj.dimension_id else ''

    def validate(self, attrs):
        dim = attrs.get('dimension')
        if dim is None and self.instance:
            dim = self.instance.dimension
        name = attrs.get('name')
        if name is None and self.instance:
            name = self.instance.name
        if dim is None or name is None:
            raise DRFValidationError({'dimension': ['维度与指标名称必填']})
        qs = ControlIndicator.objects.filter(dimension=dim, name=name)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise DRFValidationError({'name': ['该维度下指标已存在']})
        return attrs


class ControlRuleSerializer(serializers.ModelSerializer):
    dimension_name = serializers.SerializerMethodField()
    indicator_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ControlRule
        fields = [
            'id', 'code', 'is_active', 'bu', 'position', 'level', 'dimension', 'dimension_name',
            'indicator', 'indicator_name', 'year', 'target', 'strength',
            'annual_target', 'monthly_targets',
            'rollover_enabled',  # v2.10：月度浮动目标开关（默认 False；DRF camelCase 渲染 → rolloverEnabled）
            'created_by_name', 'created_at', 'updated_by_name', 'updated_at',
        ]
        read_only_fields = [
            'id', 'code', 'dimension_name', 'indicator_name',
            'created_by_name', 'created_at', 'updated_by_name', 'updated_at',
        ]

    def get_dimension_name(self, obj):
        return obj.dimension.name if obj.dimension_id else ''

    def get_indicator_name(self, obj):
        return obj.indicator.name if obj.indicator_id else ''

    def get_created_by_name(self, obj):
        u = getattr(obj, 'created_by', None)
        return u.full_name if u else ''

    def get_updated_by_name(self, obj):
        u = getattr(obj, 'updated_by', None)
        return u.full_name if u else ''

    # （说明）DRF ModelSerializer 会从 model.Meta.unique_together 自动注入
    # UniqueTogetherValidator，默认 message 是「字段 X, Y, Z 必须能构成唯一集合。」，
    # 对用户不友好。我们在这里覆盖 get_validators，把所有 UniqueTogetherValidator
    # 替换为业务友好 message，并避免与默认的重复校验（DRF 不会去重）。
    _UNIQUE_TOGETHER_FRIENDLY_MESSAGE = (
        '该组合（适用范围 / 维度 / 指标 / 生效年度 / 启用状态）已存在同名规则副本；'
        '请先在「规则列表」中停用或删除同名副本后再新建，'
        '或调整「适用范围 / 维度 / 指标 / 生效年度」任意一项后再试。'
    )

    def get_validators(self):
        validators_ = super().get_validators()
        rewritten = []
        for v in validators_:
            if isinstance(v, UniqueTogetherValidator):
                rewritten.append(UniqueTogetherValidator(
                    queryset=v.queryset,
                    fields=v.fields,
                    message=self._UNIQUE_TOGETHER_FRIENDLY_MESSAGE,
                ))
            else:
                rewritten.append(v)
        return rewritten

    def validate(self, attrs):
        _validate_scope_fields(attrs)

        dimension = attrs.get('dimension')
        if dimension is None and self.instance:
            dimension = self.instance.dimension
        indicator = attrs.get('indicator')
        if indicator is None and self.instance:
            indicator = self.instance.indicator
        if not (dimension and indicator):
            raise DRFValidationError({'dimension': ['请先选择「维度」与「指标」后再保存']})
        if indicator.dimension_id != dimension.id:
            raise DRFValidationError({'indicator': [f'所选指标「{indicator.name}」不属于已选维度「{dimension.name}」，请重新选择']})

        # v2.9 扁平模型：target 写库恒为 1.0，前端永远传 1.0；保留 0~1 范围校验仅为向后兼容
        target = _to_decimal(attrs.get('target'))
        if target is None:
            raise DRFValidationError({'target': ['目标占比必填且为数值（0~1，如 1 表示 100%）']})
        if not (Decimal('0') <= target <= Decimal('1')):
            raise DRFValidationError({'target': ['目标占比须在 0~1 之间（前端默认 1 表示该指标占 100%）']})
        strength = attrs.get('strength')
        if strength is None and self.instance:
            strength = self.instance.strength
        if strength not in STRENGTH:
            raise DRFValidationError({'strength': [f'控制强度「{strength}」非法（须为 硬约束 / 软约束）']})

        bu = attrs.get('bu') or ''
        position = attrs.get('position') or ''
        level = attrs.get('level') or ''

        # year 默认当前规划年
        year = attrs.get('year')
        if year is None:
            year = self.instance.year if self.instance else 2026
        try:
            year = int(year)
        except (TypeError, ValueError):
            raise DRFValidationError({'year': ['规划年度须为 4 位整数（如 2026）']})
        attrs['year'] = year

        # 人数目标归一
        at = attrs.get('annual_target')
        if at is None and self.instance:
            at = self.instance.annual_target
        try:
            attrs['annual_target'] = max(int(at or 0), 0)
        except (TypeError, ValueError):
            raise DRFValidationError({'annualTarget': ['年度目标人数须为非负整数']})
        mt = attrs.get('monthly_targets')
        if mt is None and self.instance:
            mt = self.instance.monthly_targets
        norm = [0] * 12
        if isinstance(mt, (list, tuple)):
            for i in range(12):
                v = mt[i] if i < len(mt) else 0
                try:
                    norm[i] = max(int(v), 0)
                except (ValueError, TypeError):
                    norm[i] = 0
        attrs['monthly_targets'] = norm

        # v2.9 校验：12 个月目标之和 须等于 年度目标人数
        monthly_sum = sum(norm)
        if monthly_sum != attrs['annual_target']:
            raise DRFValidationError({
                'monthlyTargets': [
                    f'12 个月目标之和（{monthly_sum}）与年度目标人数（{attrs["annual_target"]}）不一致；'
                    f'请调整 1月..12月 列使加和 = 年度目标，或点击「按年度均分」自动分配'
                ]
            })

        # 唯一含状态：仅校验启用(is_active=True)规则，允许「启用原规则 + 未启用副本」共存
        qs = ControlRule.objects.filter(
            bu=bu, position=position, level=level, dimension=dimension,
            indicator=indicator, year=year, is_active=True,
        )
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise DRFValidationError({
                'indicator': [
                    f'已存在适用范围「{bu or "全局"} · {position or "职务不限"} · {level or "职级不限"}」、'
                    f'维度「{dimension.name}」、指标「{indicator.name}」、年度「{year}」的启用规则；'
                    f'请直接编辑原规则，或先在列表中停用该规则后再新建'
                ]
            })

        # v2.9：删除「占比加和不得超过 100%」校验（扁平模型下 target 恒为 1.0，每条规则独占组合）

        attrs['target'] = target
        return attrs


class CampusCandidateLinkField(serializers.PrimaryKeyRelatedField):
    """关联招聘系统候选人（校招分区）。

    - 延迟取 queryset：candidate app 依赖 campus_control.constants，模块级互 import 会成环；
    - 只允许「校招」分区候选人（recruit_type='campus'），软删候选人由默认 manager 过滤掉。
    """

    def get_queryset(self):
        from apps.candidate.models import Candidate
        return Candidate.objects.filter(recruit_type='campus')


def auto_match_candidate(name, phone):
    """在「招聘系统 · 候选人管理」（校招分区）里自动认出这个人对应的候选人。

    口径（2026-10-21 兵哥口径：编号自动获取，不需要人工选候选人）：
    - 唯一同名 → 认（候选人的手机号为空表示「没冲突」；与档案手机号不一致则不认）；
    - 同名多人 → 只有档案手机号与候选人手机号**精确一致**时才认
      （候选人手机号是加密存储的，走 hash 盲索引列比对）；
    - 认不出 → 返回 None（档案走本地补号，行为与从前一致，绝不猜人）。

    :return: Candidate 实例；认不出返回 None
    """
    from apps.candidate.models import Candidate

    name = (name or '').strip()
    phone = (phone or '').strip()
    if not name:
        return None
    qs = Candidate.objects.filter(recruit_type='campus', name=name)
    hits = list(qs[:2])
    if not hits:
        return None
    if len(hits) == 1:
        cand = hits[0]
        if phone and cand.phone and cand.phone != phone:
            return None  # 手机号对不上 → 不认（宁可不同源，也不挂错人）
        return cand
    # 同名多人 → 只能靠手机号精确匹配
    if not phone:
        return None
    # ⚠️ 2026-10-23 (决策 A 回灌 J5): 必须走**双读** hash 匹配，不能用单形态等值。
    #    `hash_for_search(phone)` 只产出**当前**形态（配了 PII_HASH_SALT → `v2_`），
    #    而库里还躺着**历史 v1 形态**（无前缀，64 字符）的存量哈希
    #    （实测 ats_dev：phone_hash v1 1 行 / v2 6 行）
    #    ⇒ 单形态 `phone_hash=` 对 v1 行**永远查不到**，而且是**静默**查不到（返回 None、不报错）
    #    ⇒ `auto_match_candidate` 返回 None → 校招档案走**本地补号**（编号与候选人不同源），
    #      肉眼完全看不出问题。
    #    改用 `encrypted_field_eq_q`（= `phone_hash__in=hash_candidates_for_search(phone)`，
    #    与 candidate/services.py 的主查重路径同款）⇒ v1/v2 都能命中。
    from apps.common.encryption import encrypted_field_eq_q
    return qs.filter(encrypted_field_eq_q('phone_hash', phone)).first()


class PersonSerializer(serializers.ModelSerializer):
    """人员主数据序列化器（全局人员主数据，一行一人）。"""

    # 候选人编号：前端不填（表单里是只读的「自动生成（C+8位）」），
    # 由 Person.save() 事务内补号。序列化层必须允许缺省，
    # 否则新建/编辑档案会被「该字段是必填项」拦死（模型层的自动补号形同虚设）。
    code = serializers.CharField(required=False, allow_blank=True, max_length=32)

    # 2026-10-21：编号与「招聘系统 · 候选人管理」同源 —— 关联候选人后，
    #   档案编号直接取该候选人的编号（两系统同号，同号即同人）。
    candidate = CampusCandidateLinkField(required=False, allow_null=True)
    candidate_code = serializers.SerializerMethodField()
    candidate_name = serializers.SerializerMethodField()

    position = serializers.CharField(required=False, allow_blank=True, default='')
    level = serializers.CharField(required=False, allow_blank=True, default='')
    # 2026-10-22：招聘月份不再由表单录入 → 可空（核算月份以入职日期为准）
    month = serializers.CharField(required=False, allow_blank=True, default='', max_length=8)
    # 意向部门：显式声明 ChoiceField，把默认英文报错换成中文业务提示（R-203）
    intent_bu = serializers.ChoiceField(
        choices=[(d, d) for d in DEPTS],
        required=False, allow_blank=True, allow_null=True, default='',
        error_messages={'invalid_choice': '意向部门非法'},
    )
    # 学位：与学历同口径（枚举 + 中文报错）
    degree = serializers.ChoiceField(
        choices=[(d, d) for d in DEGREES],
        required=False, allow_blank=True, allow_null=True, default='',
        error_messages={'invalid_choice': '学位非法'},
    )

    # 2026-10-19 S5-10：外键展示名（FK 本身只出 PK）
    head_teacher_name = serializers.SerializerMethodField()
    class_room_name = serializers.SerializerMethodField()
    # 2026-10-21 二期：导师展示名 + 档案详情所需基础字段
    mentor_name = serializers.SerializerMethodField()
    # 2026-10-22：HRBP 展示名（FK 本身只出 PK）
    hrbp_name = serializers.SerializerMethodField()
    # 2026-10-23（聂荣口径）：班长展示名 + 身份完整性标记
    class_monitor_name = serializers.SerializerMethodField()
    identity_incomplete = serializers.SerializerMethodField()
    # 2026-10-23（聂荣口径）：教育经历（多条；档案详情按「院校标签就高原则」取用）
    educations = PersonEducationSerializer(many=True, required=False)
    # 2026-10-22：列表新增的三个轮岗维度指标（由 ViewSet 按页批量聚合后经 context 下发，
    #   口径见 `campus_control.person_rotation_stats`，与档案详情完全一致）
    rotation_status = serializers.SerializerMethodField()
    rotation_status_label = serializers.SerializerMethodField()
    rotation_dept = serializers.SerializerMethodField()
    overall_score = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = [
            'id', 'code', 'name', 'employee_id', 'bu', 'intent_bu', 'school', 'sex', 'major',
            'month', 'status', 'expected_entry_date', 'actual_entry_date',
            'position', 'level', 'counted',
            'head_teacher', 'head_teacher_name', 'class_room', 'class_room_name',
            'class_monitor', 'class_monitor_name',
            'mentor', 'mentor_name',
            'school_name', 'education', 'phone', 'major_name', 'degree', 'hrbp', 'hrbp_name', 'batch',
            'rotation_status', 'rotation_status_label', 'rotation_dept', 'overall_score',
            'identity_incomplete',
            'educations',
            'candidate', 'candidate_code', 'candidate_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    # 2026-10-22：轮岗维度指标统一从 context 的批量聚合结果里取（无分页场景 → 空）
    def _rotation_entry(self, obj):
        stats = (self.context or {}).get('rotation_stats') or {}
        return stats.get(str(obj.id)) or {}

    def get_rotation_status(self, obj):
        return self._rotation_entry(obj).get('rotation_status', '')

    def get_rotation_status_label(self, obj):
        return self._rotation_entry(obj).get('rotation_status_label', '')

    def get_rotation_dept(self, obj):
        return self._rotation_entry(obj).get('rotation_dept', '')

    def get_overall_score(self, obj):
        """综合评分（轮岗均分）；无评分返回 None —— 前端显示「—」，不臆造 0 分。"""
        score = self._rotation_entry(obj).get('overall_score')
        return round(float(score), 1) if score is not None else None

    # 2026-10-19 S5-10：外键展示名（FK 本身只出 PK）
    def get_head_teacher_name(self, obj):
        return obj.head_teacher.full_name if obj.head_teacher_id else ''

    def get_class_room_name(self, obj):
        return obj.class_room.name if obj.class_room_id else ''

    def get_mentor_name(self, obj):
        return obj.mentor.full_name if obj.mentor_id else ''

    def get_class_monitor_name(self, obj):
        return obj.class_monitor.full_name if obj.class_monitor_id else ''

    def get_identity_incomplete(self, obj):
        """身份字段完整性（聂荣 2026-10-23 取数规则）。

        需求原文：「简历编号与员工工号应取尽取，历史非招聘系统入职人员可不显示简历编号，
        在途校招生可不显示工号，**其他必须完整**」。

        - **简历编号**（`code`）：历史非招聘系统入职人员可缺 → 不算缺失；
        - **工号**（`employee_id`）：待入职（在途）人员可缺；**在职 / 离职必须完整**。

        返回 True 表示该行存在"必须完整却缺失"的字段，供列表打标记提醒补录。
        """
        if not obj.employee_id and obj.status not in PENDING_STATUSES:
            return True
        return False

    def _suggested_hrbp_id(self, obj):
        """当前轮岗 BU 部门的 HRBP id（自动填充的建议值）。

        - 列表场景：直接取 ViewSet 按页批量聚合的结果（零额外查询）；
        - 单条场景（retrieve / 无分页）：单查一次兜底。
        """
        ctx = self.context or {}
        if 'rotation_stats' in ctx:
            entry = (ctx.get('rotation_stats') or {}).get(str(obj.id)) or {}
            return entry.get('suggested_hrbp_id', '') or ''
        from apps.campus_control.person_rotation_stats import suggested_hrbp_id_for_person
        return suggested_hrbp_id_for_person(obj)

    def get_hrbp_name(self, obj):
        """HRBP 展示名：人工指定优先；未指定时回落到轮岗 BU 部门的 HRBP（自动填充口径）。"""
        if obj.hrbp_id:
            return obj.hrbp.full_name
        suggested = self._suggested_hrbp_id(obj)
        if suggested:
            from apps.core.models import User
            user = User.objects.filter(id=suggested).first()
            return user.full_name if user else ''
        return ''

    def to_representation(self, instance):
        """把「自动填充后的 HRBP」回写进响应（否则前端编辑弹窗拿到的仍是空值）。

        只在**未人工指定**且确有建议值时回写；已指定的一律原样返回。
        """
        data = super().to_representation(instance)
        if not data.get('hrbp'):
            suggested = self._suggested_hrbp_id(instance)
            if suggested:
                data['hrbp'] = suggested
        return data


    def get_candidate_code(self, obj):
        """关联候选人的编号（= 本档案编号，同源）。"""
        return obj.candidate.code if obj.candidate_id else ''

    def get_candidate_name(self, obj):
        return obj.candidate.name if obj.candidate_id else ''

    def validate_code(self, value):
        qs = Person.objects.filter(code=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('候选人编号已存在')
        return value

    def validate_bu(self, value):
        if value not in DEPTS:
            raise serializers.ValidationError('部门非法')
        return value

    def validate_intent_bu(self, value):
        """意向部门：与 bu 同枚举（可空）。"""
        if value and value not in DEPTS:
            raise serializers.ValidationError('意向部门非法')
        return value or ''

    def validate_school(self, value):
        if value not in SCHOOLS:
            raise serializers.ValidationError('院校标签非法')
        return value

    def validate_sex(self, value):
        if value not in SEXES:
            raise serializers.ValidationError('性别非法')
        return value

    def validate_major(self, value):
        if value not in MAJORS:
            raise serializers.ValidationError('专业标签非法')
        return value

    def validate_status(self, value):
        if value not in STATUS:
            raise serializers.ValidationError('状态非法')
        return value

    def validate_employee_id(self, value):
        """工号：8 位纯数字，且非空时全校唯一（存量 36 条在职数据均已是 8 位数字）。"""
        value = (value or '').strip()
        if value and not re.fullmatch(EMPLOYEE_ID_PATTERN, value):
            raise serializers.ValidationError('工号须为 8 位纯数字')
        if value:
            qs = Person.objects.filter(employee_id=value)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('该工号已被占用')
        return value

    def validate(self, attrs):
        """工号 / 入职日期 / 预计入职日期 三字段的形态随在职状态走（2026-10-21 兵哥口径）。

        - 未入职（待入职）：无工号、无实际入职日期，有预计入职日期；
        - 已入职（在职 / 离职）：有工号、有实际入职日期。

        未入职状态下若带了工号 / 实际入职日期，服务端**自动清空**而不是报错——
        业务上「待入职本来就没有工号」，前端切换状态时残留值不该变成一次失败保存。

        另含**编号同源**口径（关联招聘系统候选人 → 编号取候选人编号）：
        - 忽略前端传入的 code（表单里编号是只读的，编号一律以候选人为准）；
        - 该候选人的编号若已被别的档案占用 → 明确报错（不静默撞 unique 约束）。
        """
        cand = attrs.get('candidate')
        if cand is not None:
            attrs.pop('code', None)
            qs = Person.objects.filter(code=cand.code)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'candidate': [f'该候选人的编号「{cand.code}」已被其他档案占用'],
                })

        status = attrs.get('status', getattr(self.instance, 'status', None))
        employee_id = attrs.get('employee_id', getattr(self.instance, 'employee_id', '')) or ''
        expected = attrs.get(
            'expected_entry_date', getattr(self.instance, 'expected_entry_date', None)
        )
        actual = attrs.get(
            'actual_entry_date', getattr(self.instance, 'actual_entry_date', None)
        )

        # ---- 聂荣 2026-10-23 口径：班长 / HRBP 的「自动填充，可修改」 ----
        #
        # ① 班长（基于班级自动带出可修改）：档案上的班长为空时，取所选班级的班长。
        #    ⚠️ 只在**为空**时填 —— 人工指定过的班长不得被班级变更覆盖（那是"可修改"的语义）。
        if 'class_monitor' not in attrs and not getattr(self.instance, 'class_monitor_id', None):
            class_room = attrs.get('class_room') or getattr(self.instance, 'class_room', None)
            if class_room is not None and class_room.class_monitor_id:
                attrs['class_monitor'] = class_room.class_monitor

        # ② HRBP（基于轮岗 BU 部门的 HRBP 自动填充，可修改）：档案上的 HRBP 为空时，
        #    取该生当前轮岗 BU 部门的 Department.hrbp。
        if 'hrbp' not in attrs and not getattr(self.instance, 'hrbp_id', None):
            instance = self.instance
            if instance is not None:
                from apps.campus_control.person_rotation_stats import (
                    suggested_hrbp_id_for_person,
                )
                from apps.core.models import User
                suggested = suggested_hrbp_id_for_person(instance)
                if suggested:
                    user = User.objects.filter(id=suggested).first()
                    if user is not None:
                        attrs['hrbp'] = user

        if status in PENDING_STATUSES:
            attrs['employee_id'] = ''
            attrs['actual_entry_date'] = None
            if not expected:
                raise serializers.ValidationError({
                    'expected_entry_date': ['待入职人员须填写预计入职日期'],
                })
        elif status in EMPLOYED_STATUSES:
            if not employee_id:
                raise serializers.ValidationError({
                    'employee_id': ['在职 / 离职人员须填写工号（8 位纯数字）'],
                })
            if not actual:
                raise serializers.ValidationError({
                    'actual_entry_date': ['在职 / 离职人员须填写实际入职日期'],
                })
        return attrs

    def validate_education(self, value):
        # 学历可为空（未采集）；非空时须在枚举内
        if value and value not in EDUCATIONS:
            raise serializers.ValidationError('学历非法')
        return value

    # ================= 编号自动获取（无需人工选候选人） =================

    def _auto_candidate(self, attrs):
        """自动认人：显式传了 candidate 就用它；否则按 姓名(+手机号) 去候选人管理里认。

        认得出且该候选人编号未被别的档案占用 → 返回该候选人（保存时编号取候选人编号）；
        认不出 / 编号已被占用 → 返回 None（档案保持自己的编号，保存不失败）。
        """
        if attrs.get('candidate') is not None:
            return attrs['candidate']
        instance = self.instance
        if instance is not None and instance.candidate_id:
            return instance.candidate  # 已认定过，不换人
        name = attrs.get('name', getattr(instance, 'name', ''))
        phone = attrs.get('phone', getattr(instance, 'phone', ''))
        cand = auto_match_candidate(name, phone)
        if cand is None:
            return None
        occupied = Person.objects.filter(code=cand.code)
        if instance is not None:
            occupied = occupied.exclude(pk=instance.pk)
        if occupied.exists():
            # 候选人编号已被别的档案占用 → 这次不换源（不因自动匹配让用户的保存失败）
            return None
        return cand

    def _save_educations(self, person, educations):
        """同步该生的教育经历（增量按 id 更新 / 新增，其余软删）。

        ⚠️ 档案详情按「院校标签就高原则」取用 → 教育经历是**有序集合**，
        全量替换最不容易出错；但仍保留按 id 更新，避免前端改一条就整段重写（丢 created_at，
        进而影响「同标签同学历时取最早录入」这条稳定性规则）。
        """
        keep_ids = []
        for item in educations:
            payload = dict(item)
            eid = payload.pop('id', None)
            if eid:
                obj = PersonEducation.objects.filter(id=eid, person=person).first()
                if obj is not None:
                    for key, value in payload.items():
                        setattr(obj, key, value)
                    obj.save()
                    keep_ids.append(obj.id)
                    continue
            obj = PersonEducation.objects.create(person=person, **payload)
            keep_ids.append(obj.id)
        person.educations.exclude(id__in=keep_ids).delete()

    def create(self, validated_data):
        educations = validated_data.pop('educations', None)
        cand = self._auto_candidate(validated_data)
        if cand is not None:
            validated_data['candidate'] = cand
        instance = super().create(validated_data)
        if educations is not None:
            self._save_educations(instance, educations)
        return instance

    def update(self, instance, validated_data):
        educations = validated_data.pop('educations', None)
        cand = self._auto_candidate(validated_data)
        if cand is not None:
            validated_data['candidate'] = cand
        instance = super().update(instance, validated_data)
        if educations is not None:
            self._save_educations(instance, educations)
        return instance


__all__ = [
    'ControlDimensionSerializer', 'ControlIndicatorSerializer',
    'ControlRuleSerializer', 'PersonSerializer', 'IntegrityError',
    'BatchRuleSerializer', 'BatchNamingSerializer',
]


# ===========================================================================
# 批次规则引擎（契约 §4.2）—— 追加于本文件末尾
# ===========================================================================
class BatchRuleSerializer(serializers.ModelSerializer):
    """批次规则（逆向清单 §4.4 ②）。

    校验：区间起止必须合法（开始日 ≤ 结束日）；批次号唯一性由视图层提示（同名次允许重复
    ——「批次号」是展示编号，人员归属以日期命中为准）。
    """

    class Meta:
        model = BatchRule
        fields = [
            'id', 'code', 'name', 'start_date', 'end_date', 'enabled', 'sort',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and start > end:
            raise serializers.ValidationError({'end_date': '区间结束日不能早于开始日'})
        return attrs


class BatchNamingSerializer(serializers.ModelSerializer):
    """批次命名配置（单例）。模板变量白名单在 validate_template 里校验。"""

    #: 命名模板支持的变量（逆向清单 §4.4 ①）
    TEMPLATE_VARS = ('{YYYY}', '{YY}', '{MM}', '{M}', '{DD}', '{SEQ}', '{N}')

    class Meta:
        model = BatchNaming
        fields = [
            'id', 'template', 'seq_width', 'seq_start', 'cycle', 'date_field', 'auto_apply',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_template(self, value):
        """模板只允许白名单变量；未知占位符会被静默留在批次号里 → 直接拦掉。"""
        text = value or ''
        for token in re.findall(r'\{[^{}]*\}', text):
            if token not in self.TEMPLATE_VARS:
                raise serializers.ValidationError(
                    '命名模板只支持 %s 这些变量' % ' '.join(self.TEMPLATE_VARS)
                )
        return text

    def validate_seq_width(self, value):
        if not 1 <= int(value) <= 4:
            raise serializers.ValidationError('序号位数须在 1 ~ 4 之间')
        return value

    def validate_seq_start(self, value):
        if not 1 <= int(value) <= 99:
            raise serializers.ValidationError('序号起始值须在 1 ~ 99 之间')
        return value
