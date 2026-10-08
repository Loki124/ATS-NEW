"""生产环境密码复杂度校验器 (2026-10-01 P2-1).

背景: 原 AUTH_PASSWORD_VALIDATORS 仅用 Django 默认的 MinimumLengthValidator(8) +
CommonPassword + Numeric, 8 位且无复杂度要求, 对以"候选人隐私"为卖点的系统偏弱。
本模块提供 PasswordComplexityValidator, 要求密码至少覆盖小写/大写/数字/特殊字符
中的 N 类 (默认 3 类), 与 MinimumLengthValidator(12) 组合构成生产级策略。

仅 prod.py 引用; base.py (dev/test) 保持宽松以不干扰测试 fixture。
"""
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

_UPPER = re.compile(r'[A-Z]')
_LOWER = re.compile(r'[a-z]')
_DIGIT = re.compile(r'[0-9]')
_SPECIAL = re.compile(r'[^A-Za-z0-9]')


class PasswordComplexityValidator:
    """要求密码至少包含 N 类字符 (小写/大写/数字/特殊), 默认 3 类."""

    def __init__(self, min_classes: int = 3) -> None:
        if not 2 <= min_classes <= 4:
            raise ValueError('min_classes 必须在 2~4 之间')
        self.min_classes = min_classes

    def validate(self, password, user=None) -> None:
        classes = sum(
            bool(p.search(password))
            for p in (_UPPER, _LOWER, _DIGIT, _SPECIAL)
        )
        if classes < self.min_classes:
            raise ValidationError(
                _(
                    '密码复杂度不足: 必须至少包含小写字母、大写字母、数字、'
                    '特殊字符中的 %(min)s 类, 当前仅 %(got)s 类。'
                )
                % {'min': self.min_classes, 'got': classes},
                code='password_too_simple',
            )

    def get_help_text(self) -> str:
        return _(
            '密码长度至少 12 位, 且至少包含小写字母、大写字母、数字、'
            '特殊字符中的 %d 类。' % self.min_classes
        )
