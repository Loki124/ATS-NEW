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

    def validate(self, attrs):
        _validate_scope_fields(attrs)

        dimension = attrs.get('dimension')
        if dimension is None and self.instance:
            dimension = self.instance.dimension
        indicator = attrs.get('indicator')
        if indicator is None and self.instance:
            indicator = self.instance.indicator
        if not (dimension and indicator):
            raise DRFValidationError({'dimension': ['维度 / 指标 均必填']})
        if indicator.dimension_id != dimension.id:
            raise DRFValidationError({'indicator': ['指标不属于所选维度']})

        target = _to_decimal(attrs.get('target'))
        if target is None:
            raise DRFValidationError({'target': ['目标占比必填且为数值']})
        if not (Decimal('0') <= target <= Decimal('1')):
            raise DRFValidationError({'target': ['目标占比须满足 0 <= 目标 <= 1']})
        strength = attrs.get('strength')
        if strength is None and self.instance:
            strength = self.instance.strength
        if strength not in STRENGTH:
            raise DRFValidationError({'strength': ['控制强度非法']})

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
            raise DRFValidationError({'year': ['规划年度须为整数']})
        attrs['year'] = year

        # 人数目标归一
        at = attrs.get('annual_target')
        if at is None and self.instance:
            at = self.instance.annual_target
        try:
            attrs['annual_target'] = max(int(at or 0), 0)
        except (TypeError, ValueError):
            raise DRFValidationError({'annualTarget': ['年度目标须为整数']})
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

        # 唯一含状态：仅校验启用(is_active=True)规则，允许「启用原规则 + 未启用副本」共存
        qs = ControlRule.objects.filter(
            bu=bu, position=position, level=level, dimension=dimension,
            indicator=indicator, year=year, is_active=True,
        )
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise DRFValidationError({'indicator': ['该适用范围-维度-指标-年度组合已存在启用规则，请直接编辑或停用原规则']})

        # 单条编辑仅拦「超 100%」（防溢出）；恰好 ==100% 由批量端点强制。
        # 占比加和仅统计启用(is_active=True)规则，副本不计入。
        existing = ControlRule.objects.filter(
            bu=bu, position=position, level=level, dimension=dimension, year=year, is_active=True,
        )
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)
        s = sum((r.target for r in existing), Decimal('0')) + target
        if s > Decimal('1') + Decimal('0.0001'):
            pct = (s * 100).quantize(Decimal('0.01'))
            raise DRFValidationError({
                'target': [f'该适用范围下此维度指标目标占比之和不得超过 100%，当前为 {pct}%']
            })

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
            raise serializers.ValidationError('人员编码已存在')
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
