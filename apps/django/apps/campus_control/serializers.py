"""人员比例管控系统 — 序列化器与 §4.1 校验。"""
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .constants import DEPTS, SCHOOLS, MAJORS, SEXES, DIMS, STRENGTH, STATUS, GROUP_CHOICES
from .models import ControlRule, Person


class RuleSerializer(serializers.ModelSerializer):
    """管控规则（占比以小数 0~1 存储；前端以百分比输入后 ÷100 传入）。"""

    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ControlRule
        fields = [
            'id', 'dim', 'group', 'target', 'lo', 'hi', 'strength',
            'whole', 'month_target',
            'created_by_name', 'created_at',
            'updated_by_name', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_by_name', 'created_at', 'updated_by_name', 'updated_at',
        ]

    def get_created_by_name(self, obj) -> str:
        u = getattr(obj, 'created_by', None)
        return u.full_name if u else ''

    def get_updated_by_name(self, obj) -> str:
        u = getattr(obj, 'updated_by', None)
        return u.full_name if u else ''

    def validate(self, attrs: dict) -> dict:
        dim = attrs.get('dim')
        if dim is None and self.instance:
            dim = self.instance.dim
        group = attrs.get('group')
        if group is None and self.instance:
            group = self.instance.group

        if dim is None:
            raise ValidationError({'dim': ['维度必填']})
        if group is None:
            raise ValidationError({'group': ['分组必填']})
        if dim not in DIMS:
            raise ValidationError({'dim': ['维度非法']})
        if group not in GROUP_CHOICES.get(dim, []):
            raise ValidationError({'group': [f'分组「{group}」不属于维度「{dim}」的合法取值']})

        target = attrs.get('target')
        if target is None and self.instance:
            target = self.instance.target
        lo = attrs.get('lo')
        if lo is None and self.instance:
            lo = self.instance.lo
        hi = attrs.get('hi')
        if hi is None and self.instance:
            hi = self.instance.hi
        if None not in (target, lo, hi):
            if not (0 <= float(lo) <= float(target) <= float(hi) <= 1):
                raise ValidationError({'lo': ['必须满足 0 <= 下限 <= 目标 <= 上限 <= 1']})

        strength = attrs.get('strength')
        if strength is None and self.instance:
            strength = self.instance.strength
        if strength is not None and strength not in STRENGTH:
            raise ValidationError({'strength': ['控制强度非法']})

        whole = attrs.get('whole')
        if whole is None and self.instance:
            whole = self.instance.whole
        if whole is not None and int(whole) < 0:
            raise ValidationError({'whole': ['整体目标需为非负整数']})

        month_target = attrs.get('month_target')
        if month_target is None and self.instance:
            month_target = self.instance.month_target
        if month_target is not None and int(month_target) < 0:
            raise ValidationError({'month_target': ['本月目标需为非负整数']})

        # (dim, group) 唯一（排除自身编辑）
        qs = ControlRule.objects.filter(dim=dim, group=group)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError({'group': ['该维度-分组已存在，请直接编辑现有规则']})

        return attrs


class PersonSerializer(serializers.ModelSerializer):
    """人员主数据。"""

    class Meta:
        model = Person
        fields = [
            'id', 'code', 'name', 'bu', 'school', 'sex', 'major',
            'month', 'status', 'counted', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_code(self, value: str) -> str:
        if not value or not value.strip():
            raise ValidationError('人员编码不能为空')
        return value

    def validate_bu(self, value: str) -> str:
        if value not in DEPTS:
            raise ValidationError('部门非法')
        return value

    def validate_school(self, value: str) -> str:
        if value not in SCHOOLS:
            raise ValidationError('院校标签非法')
        return value

    def validate_sex(self, value: str) -> str:
        if value not in SEXES:
            raise ValidationError('性别非法')
        return value

    def validate_major(self, value: str) -> str:
        if value not in MAJORS:
            raise ValidationError('专业标签非法')
        return value

    def validate_status(self, value: str) -> str:
        if value not in STATUS:
            raise ValidationError('状态非法')
        return value

    def validate(self, attrs: dict) -> dict:
        code = attrs.get('code')
        if code:
            qs = Person.objects.filter(code=code)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError({'code': ['人员编码已存在']})
        return attrs
