"""背调供应商工厂（T6 — D9 provider 路由）

``get_supplier(config)`` 按 ``config.provider``（或 ``config.config['provider']``）选择适配器；
未配置 / 未知 provider 一律回退到默认 ``HmacBackgroundCheckSupplier``。

供应商类通过 ``register_provider`` 注册（provider 名 → 适配器类），默认已注册 hmac 系列。
"""
from __future__ import annotations

from typing import Any, Dict, Type

from .base import BaseBackgroundCheckSupplier
from .hmac_adapter import HmacBackgroundCheckSupplier

#: provider 名 → 适配器类。空字符串 '' 视为默认（HMAC）。
_PROVIDERS: Dict[str, Type[BaseBackgroundCheckSupplier]] = {
    '': HmacBackgroundCheckSupplier,
    'hmac': HmacBackgroundCheckSupplier,
    'HMAC': HmacBackgroundCheckSupplier,
}


def register_provider(name: str, cls: Type[BaseBackgroundCheckSupplier]) -> None:
    """注册一个 provider 名到适配器类的映射。"""
    _PROVIDERS[name] = cls


def _resolve_provider(config: Any) -> str:
    """从 config 解析 provider：优先 ``config.provider`` 模型字段，回退 ``config.config['provider']``。"""
    if config is None:
        return ''
    model_provider = getattr(config, 'provider', '') or ''
    if model_provider:
        return model_provider
    cfg = getattr(config, 'config', None) or {}
    return cfg.get('provider', '') or ''


def get_supplier(config: Any) -> BaseBackgroundCheckSupplier:
    """根据 config 取得背调供应商适配器实例（D9）。

    未知 provider 回退到 ``HmacBackgroundCheckSupplier``，保证行为向后兼容。
    """
    provider = _resolve_provider(config)
    cls = _PROVIDERS.get(provider, HmacBackgroundCheckSupplier)
    return cls(config)
