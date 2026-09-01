"""人员比例管控系统 v2.4 — 序列化器与校验。

校验要点：
- Rule：(bu, position, level, dimension, indicator, year) 唯一；indicator 须属于 dimension；
  target 0~1；年/月人数目标归一；单条编辑仅拦「超 100%」（防溢出），恰好 ==100% 由批量端点强制。
- 适用范围：bu/position/level 均可空（空 = 不限 / 全局）。
- 取消原 lo/hi 上下限配置；人数目标（annual_target / monthly_targets）直接承载于规则。
"""
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.validators import UniqueTogetherValidator

from .constants import DEPTS, SCHOOLS, MAJORS, SEXES, STRENGTH, STATUS, POSITIONS, LEVELS
from .models import (
    ControlDimension, ControlIndicator, ControlRule, Person,
)


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


class PersonSerializer(serializers.ModelSerializer):
    """人员主数据序列化器（全局人员主数据，一行一人）。"""

    position = serializers.CharField(required=False, allow_blank=True, default='')
    level = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = Person
        fields = [
            'id', 'code', 'name', 'bu', 'school', 'sex', 'major',
            'month', 'status', 'expected_entry_date', 'actual_entry_date',
            'position', 'level', 'counted',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

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


__all__ = [
    'ControlDimensionSerializer', 'ControlIndicatorSerializer',
    'ControlRuleSerializer', 'PersonSerializer', 'IntegrityError',
]
