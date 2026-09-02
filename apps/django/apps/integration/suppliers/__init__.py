"""背调供应商适配器包（T6）。

对外导出统一契约与默认工厂，便于 services / tests 直接引用。
"""
from .base import (
    BaseBackgroundCheckSupplier,
    BackgroundCheckResult,
    CreateOrderRequest,
    verify_callback_signature,
    replay_allowed,
)
from .hmac_adapter import HmacBackgroundCheckSupplier
from .factory import get_supplier, register_provider

__all__ = [
    'BaseBackgroundCheckSupplier',
    'BackgroundCheckResult',
    'CreateOrderRequest',
    'verify_callback_signature',
    'replay_allowed',
    'HmacBackgroundCheckSupplier',
    'get_supplier',
    'register_provider',
]
