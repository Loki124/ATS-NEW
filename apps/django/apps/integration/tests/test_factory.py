"""T6 供应商工厂路由测试（离线）。

覆盖 ``get_supplier`` 按 provider 路由：
- '' / 'hmac' / 'HMAC' → 默认 HmacBackgroundCheckSupplier
- 未知 provider → 回退 HmacBackgroundCheckSupplier（行为向后兼容）
- 已注册自定义 provider → 返回对应适配器类
"""
import pytest

from apps.integration.suppliers.base import BaseBackgroundCheckSupplier
from apps.integration.suppliers.factory import get_supplier, register_provider
from apps.integration.suppliers.hmac_adapter import HmacBackgroundCheckSupplier


class _DummyConfig:
    """最小配置桩：仅暴露 provider / config 供 _resolve_provider 读取。"""
    def __init__(self, provider='', cfg_provider=''):
        self.provider = provider
        self.config = {'provider': cfg_provider}


class _DummySupplier(BaseBackgroundCheckSupplier):
    """自定义适配器桩（注册后应由 get_supplier 返回）。"""
    def __init__(self, config=None):
        self._config = config
        self._cfg = {}
        self._secret = {}
        self._app_id = 'dummy'
        self._app_key = 'dummy'
        self._base_url = ''

    def create_order(self, req):
        raise NotImplementedError

    def cancel_order(self, order_number):
        raise NotImplementedError

    def query_order(self, order_number):
        raise NotImplementedError

    def query_products(self, product_token=None):
        raise NotImplementedError

    def fetch_report(self, order):
        raise NotImplementedError


@pytest.fixture(autouse=True)
def _cleanup_dummy():
    yield
    # 避免污染其它测试 / 真实路由表
    from apps.integration.suppliers.factory import _PROVIDERS
    _PROVIDERS.pop('dummy', None)


def test_empty_provider_defaults_to_hmac(bg_config):
    assert isinstance(get_supplier(bg_config), HmacBackgroundCheckSupplier)


def test_hmac_provider_routes_to_hmac(bg_config):
    bg_config.provider = 'hmac'
    assert isinstance(get_supplier(bg_config), HmacBackgroundCheckSupplier)


def test_uppercase_hmac_provider_routes_to_hmac(bg_config):
    bg_config.provider = 'HMAC'
    assert isinstance(get_supplier(bg_config), HmacBackgroundCheckSupplier)


def test_unknown_provider_falls_back_to_hmac(bg_config):
    bg_config.provider = 'does-not-exist'
    assert isinstance(get_supplier(bg_config), HmacBackgroundCheckSupplier)


def test_registered_custom_provider_routes_to_custom():
    register_provider('dummy', _DummySupplier)
    sup = get_supplier(_DummyConfig(cfg_provider='dummy'))
    assert isinstance(sup, _DummySupplier)


def test_unregistered_custom_provider_model_field_falls_back():
    # config.provider 指向未注册名 → 回退默认，不抛异常
    sup = get_supplier(_DummyConfig(provider='ghost'))
    assert isinstance(sup, HmacBackgroundCheckSupplier)
