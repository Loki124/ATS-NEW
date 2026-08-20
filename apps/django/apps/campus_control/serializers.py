"""人员比例管控系统 v2 — 序列化器与校验。

校验要点：
- Rule：(scope, dimension, indicator) 唯一；indicator 须属于 dimension；
  lo<=target<=hi 且 0~1；保存时校验「同一 (scope, dimension) 下所有 indicator 的
  target 之和 == 1.0」，不等于 100% 硬拦截（见决策 q-2 / q-3）。
- Headcount：(scope, indicator, year) 唯一；monthly_targets 归一到长度 12。
"""
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError

from .constants import DEPTS, SCHOOLS, MAJORS, SEXES, DIMS, STRENGTH, STATUS, POSITIONS, LEVELS
from .models import (
    ControlScope, ControlDimension, ControlIndicator, ControlRule, ControlHeadcount, Person,
)


def _to_decimal(v):
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return None


class ControlScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlScope
        fields = ['id', 'name', 'bu', 'position', 'level', 'is_active',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        qs = ControlScope.objects.filter(name=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('方案名称已存在')
        return value

    def validate_bu(self, value):
        if value not in DEPTS:
            raise serializers.ValidationError('BG部门非法')
        return value


class ControlDimensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlDimension
        fields = ['id', 'name', 'code', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        if value not in DIMS:
            raise serializers.ValidationError('维度非法')
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
    scope_name = serializers.SerializerMethodField()
    dimension_name = serializers.SerializerMethodField()
    indicator_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ControlRule
        fields = [
            'id', 'scope', 'scope_name', 'dimension', 'dimension_name',
            'indicator', 'indicator_name', 'target', 'lo', 'hi', 'strength',
            'created_by_name', 'created_at', 'updated_by_name', 'updated_at',
        ]
        read_only_fields = [
            'id', 'scope_name', 'dimension_name', 'indicator_name',
            'created_by_name', 'created_at', 'updated_by_name', 'updated_at',
        ]

    def get_scope_name(self, obj):
        return obj.scope.name if obj.scope_id else ''

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
        scope = attrs.get('scope')
        if scope is None and self.instance:
            scope = self.instance.scope
        dimension = attrs.get('dimension')
        if dimension is None and self.instance:
            dimension = self.instance.dimension
        indicator = attrs.get('indicator')
        if indicator is None and self.instance:
            indicator = self.instance.indicator

        if not (scope and dimension and indicator):
            raise DRFValidationError({'scope': ['适用范围 / 维度 / 指标 均必填']})
        if indicator.dimension_id != dimension.id:
            raise DRFValidationError({'indicator': ['指标不属于所选维度']})

        # 区间与强度
        target = _to_decimal(attrs.get('target'))
        lo = _to_decimal(attrs.get('lo'))
        hi = _to_decimal(attrs.get('hi'))
        if None in (target, lo, hi):
            raise DRFValidationError({'target': ['目标/下限/上限必填且为数值']})
        if not (Decimal('0') <= lo <= target <= hi <= Decimal('1')):
            raise DRFValidationError({'lo': ['需满足 0 <= 下限 <= 目标 <= 上限 <= 1']})
        strength = attrs.get('strength')
        if strength is None and self.instance:
            strength = self.instance.strength
        if strength not in STRENGTH:
            raise DRFValidationError({'strength': ['控制强度非法']})

        # 唯一 (scope, dimension, indicator)，排除自身
        qs = ControlRule.objects.filter(scope=scope, dimension=dimension, indicator=indicator)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise DRFValidationError({'indicator': ['该适用范围-维度-指标组合已存在，请直接编辑']})

        # 100% 加和硬校验（q-2 / q-3）：单条编辑仅拦截「超 100%」（防溢出），
        # 「恰好 == 100%」的完整性由批量保存端点 /rules/batch/ 强制（见 views.batch）。
        existing = ControlRule.objects.filter(scope=scope, dimension=dimension)
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)
        s = sum((r.target for r in existing), Decimal('0')) + target
        if s > Decimal('1') + Decimal('0.0001'):
            pct = (s * 100).quantize(Decimal('0.01'))
            raise DRFValidationError({
                'target': [f'该维度下所有指标目标占比之和不得超过 100%，当前为 {pct}%']
            })

        attrs['target'] = target
        attrs['lo'] = lo
        attrs['hi'] = hi
        return attrs


class ControlHeadcountSerializer(serializers.ModelSerializer):
    scope_name = serializers.SerializerMethodField()
    dimension_name = serializers.SerializerMethodField()
    indicator_name = serializers.SerializerMethodField()

    class Meta:
        model = ControlHeadcount
        fields = [
            'id', 'scope', 'scope_name', 'indicator', 'indicator_name',
            'dimension_name', 'year', 'annual_target', 'monthly_targets',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'scope_name', 'indicator_name', 'dimension_name',
            'created_at', 'updated_at',
        ]

    def get_scope_name(self, obj):
        return obj.scope.name if obj.scope_id else ''

    def get_indicator_name(self, obj):
        return obj.indicator.name if obj.indicator_id else ''

    def get_dimension_name(self, obj):
        return obj.indicator.dimension.name if obj.indicator_id else ''

    def validate(self, attrs):
        scope = attrs.get('scope')
        indicator = attrs.get('indicator')
        year = attrs.get('year')
        if not (scope and indicator and year):
            raise DRFValidationError({'scope': ['适用范围 / 指标 / 年度 均必填']})
        qs = ControlHeadcount.objects.filter(scope=scope, indicator=indicator, year=year)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise DRFValidationError({'year': ['该适用范围-指标-年度的人数目标已存在，请直接编辑']})

        # monthly_targets 归一到长度 12 的非负整数列表
        mt = attrs.get('monthly_targets')
        norm = [0] * 12
        if isinstance(mt, (list, tuple)):
            for i in range(12):
                v = mt[i] if i < len(mt) else 0
                try:
                    norm[i] = max(int(v), 0)
                except (ValueError, TypeError):
                    norm[i] = 0
        attrs['monthly_targets'] = norm
        at = attrs.get('annual_target')
        attrs['annual_target'] = max(int(at or 0), 0)
        return attrs


class PersonSerializer(serializers.ModelSerializer):
    """人员主数据序列化器（全局人员主数据，一行一人）。

    position / level 允许为空（「不限」），不强制 choices 以免空值被拒。
    """

    position = serializers.CharField(required=False, allow_blank=True, default='')
    level = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = Person
        fields = [
            'id', 'code', 'name', 'bu', 'school', 'sex', 'major',
            'month', 'status', 'position', 'level', 'counted',
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
    'ControlScopeSerializer', 'ControlDimensionSerializer', 'ControlIndicatorSerializer',
    'ControlRuleSerializer', 'ControlHeadcountSerializer', 'PersonSerializer', 'IntegrityError',
]
