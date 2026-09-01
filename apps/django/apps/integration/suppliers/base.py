"""背调供应商统一适配器抽象层（T6 — 统一背调供应商接口标准规范 v1.0.1）

本模块定义供应商接入的 *统一契约* 与 *公共能力*，把此前散落在 services.py 里的
HMAC 双签公式、appId/appKey 解析、成功判定、路径解析等重复逻辑收敛到一处。

设计要点（对应 brief D1–D9）：
- D1  Adapter 抽象：``BaseBackgroundCheckSupplier`` 定义全部统一契约方法。
- D3  字段回退：``_resolve_app_id`` / ``_resolve_app_key`` 集中处理 camel/snake 回退。
- D4  状态映射：``to_canonical_status`` / ``from_canonical_status``（默认 identity）。
- D5  双签公式：``sign_request``(出向 §1.4.3) / ``verify_callback_signature``(入向 §5.2)。
- D6  路径解析：具名端点常量（由具体 adapter 提供默认值）。
- D2  成功判定：``_is_success`` 统一的业务码判定（create 路径仍按 HTTP 200/201）。

具名端点（create/cancel/products/order-detail/health）的默认值由具体 adapter 提供，
base 只定义占位，避免对 HMAC 细节产生硬依赖。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..crypto import decrypt_secret

#: 成功业务码集合（规范 §3.2 / §4.2：code=0 表示成功）。
SUCCESS_CODES = (0, '0', None)


# ============================================================
# 请求 / 结果数据结构
# ============================================================
@dataclass
class CreateOrderRequest:
    """创建背调订单的统一请求结构（规范 §3.2）。

    全部规范字段均为可选；同时保留与既有后端 wire 格式兼容的
    ``candidate_id`` / ``items`` 两个字段（见 hmac_adapter 说明）。
    """

    # —— 规范 §3.2 必填字段（在统一契约里仍允许缺省，由 adapter 决定必填性）——
    product_token: Optional[str] = None          # 套餐唯一标识（必填）
    candidate_name: Optional[str] = None         # 候选人姓名（必填）
    phone: Optional[str] = None                  # 候选人手机号（必填）
    operator_name: Optional[str] = None          # 委托人/经办人姓名（必填）
    operator_phone: Optional[str] = None         # 委托人手机号（必填）
    # —— 规范 §3.2 可选字段 ——
    email: Optional[str] = None                  # 候选人邮箱
    operator_email: Optional[str] = None         # 委托人邮箱
    id_card: Optional[str] = None                # 候选人身份证号（PII）
    auth_way: Optional[int] = None               # 授权方式 1/2/3
    callback_url: Optional[str] = None           # 回调地址
    expect_entry_time: Optional[str] = None      # 预计入职日期 yyyy-MM-dd
    remark: Optional[str] = None                 # 备注
    contact_candidate: Optional[int] = None      # 是否可联系候选人 1/0
    request_id: Optional[str] = None             # 幂等请求号（UUID）
    # —— 向后兼容（既有后端 wire 格式，T6 保留）——
    candidate_id: Optional[str] = None           # 候选人 ID（平台侧）
    items: List[str] = field(default_factory=list)  # 背调项目列表（平台侧）


@dataclass
class BackgroundCheckResult:
    """供应商调用的统一返回结构。

    services 层据此封装成对外 dict（``{'success', 'message', 'data', ...}``），
    adapter 自身不触碰数据库（审计日志统一在 services 层落库）。
    """

    success: bool
    message: str = ''
    data: Optional[dict] = None
    duration_ms: Optional[int] = None
    raw: Any = None


# ============================================================
# 模块级静态工具（§5.2 验签 + 重放窗口）
# ============================================================
def verify_callback_signature(payload: dict, app_key: str) -> bool:
    """§5.2 回调验签：待签串 ``"number=" + number + "&status=" + status + "&timestamp=" + ts``。

    使用 HMAC-SHA256（十六进制小写），并通过 ``hmac.compare_digest`` 做常量时间比较。
    返回 ``True`` 表示签名通过；缺参 / 非法 timestamp / 签名不符均返回 ``False``。
    """
    if not isinstance(payload, dict):
        return False
    number = payload.get('number')
    status_val = payload.get('status')
    ts = payload.get('timestamp')
    sign = payload.get('sign')
    if not number or status_val is None or ts is None or not sign:
        return False
    try:
        ts_int = int(ts)
    except (TypeError, ValueError):
        return False
    sign_str = "number=" + str(number) + "&status=" + str(status_val) + "&timestamp=" + str(ts_int)
    expected = hmac.new(
        app_key.encode('utf-8'), sign_str.encode('utf-8'), hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, str(sign).lower())


def replay_allowed(ts_int: int, now_ms: Optional[int] = None,
                   window_ms: int = 5 * 60 * 1000) -> bool:
    """§5.2 重放窗口判定：``abs(now - ts) <= window`` 视为合法。

    ``now_ms`` 默认取当前毫秒时间戳，便于测试注入固定值。
    """
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    try:
        ts_int = int(ts_int)
    except (TypeError, ValueError):
        return False
    return abs(now_ms - ts_int) <= window_ms


# ============================================================
# 抽象供应商基类
# ============================================================
class BaseBackgroundCheckSupplier(ABC):
    """背调供应商统一适配器基类。

    具体供应商（如 ``HmacBackgroundCheckSupplier``）继承本类并：
    1. 提供具名端点常量（``CREATE_PATH`` 等）；
    2. 实现 5 个抽象网络方法（create/cancel/query/products/report）；
    3. 按需覆写 ``to_canonical_status`` / ``from_canonical_status`` / ``capabilities`` / ``health``。

    base 已封装：双签公式、appId/appKey 解析、成功判定、路径解析、状态映射。
    """

    # —— 具名端点占位（具体 adapter 必须覆盖为真实路径）——
    CREATE_PATH: str = '/api/v1/background-check/orders'
    CANCEL_PATH: str = '/api/v1/background-check/cancel'
    PRODUCTS_PATH: str = '/api/v1/background-check/products'
    ORDER_DETAIL_PATH: str = '/api/v1/background-check/orders/{number}'
    HEALTH_PATH: str = '/api/v1/health'

    def __init__(self, config: Any) -> None:
        """从 IntegrationConfig 解析出通用连接参数（不发起任何网络请求）。

        参数:
            config: IntegrationConfig 实例（或任意拥有 config/encrypted_secret 属性的对象）。
        """
        self._config = config
        self._cfg: Dict[str, Any] = dict(getattr(config, 'config', None) or {})
        self._secret: Dict[str, Any] = self._load_secret(config)
        self._app_id: str = self._resolve_app_id(self._cfg)
        self._app_key: str = self._resolve_app_key(self._secret)
        env = self._cfg.get('env', 'sandbox')
        self._base_url: str = (
            self._cfg.get('productionBaseUrl') if env == 'production'
            else self._cfg.get('sandboxBaseUrl')
        ) or ''

    # ---------------------------------------------------------- 密钥 / 配置解析（D3）
    @staticmethod
    def _load_secret(config: Any) -> Dict[str, Any]:
        """解密 ``encrypted_secret``（JSON 字符串）→ dict；无效返回 {}。"""
        raw = getattr(config, 'encrypted_secret', '') or ''
        if not raw:
            return {}
        try:
            return json.loads(decrypt_secret(raw))
        except Exception:
            return {}

    @staticmethod
    def _resolve_app_id(cfg: Optional[dict]) -> str:
        """camel/snake 回退：``AppId`` 优先，回退 ``appId``。"""
        if not cfg:
            return ''
        return cfg.get('AppId') or cfg.get('appId') or ''

    @staticmethod
    def _resolve_app_key(secret: Optional[dict]) -> str:
        """camel/snake 回退：``api_key`` 优先，回退 ``apiKey``。"""
        if not secret:
            return ''
        if isinstance(secret, dict):
            return secret.get('api_key') or secret.get('apiKey') or ''
        return ''

    # ---------------------------------------------------------- 成功判定（D2）
    @staticmethod
    def _is_success(resp: Optional[dict], success_codes: tuple = SUCCESS_CODES) -> bool:
        """按业务信封 code 判定成功（默认 code ∈ (0, '0', None)）。"""
        if not isinstance(resp, dict):
            return False
        return resp.get('code') in success_codes

    # ---------------------------------------------------------- 双签公式（D5）
    def sign_request(self, params: dict) -> dict:
        """§1.4.3 出向签名 → 返回含签名的请求头。

        待签串 = 排序业务参数(key=value&连接) + "&timestamp=" + 毫秒时间戳；
        null / 空字符串字段不参与签名；HMAC-SHA256 十六进制小写。

        复合 / 非字符串值按 JSON 紧凑编码（``separators=(',', ':')``、
        ``ensure_ascii=False``），与请求体 JSON 逻辑一致（§1.4.3「业务参数指
        请求体 JSON 的业务字段」），避免 list/dict 等复合值出现 repr / wire 双轨。
        字符串原样；bool → ``true``/``false``；int/float → JSON 字面量。
        """
        ts = str(int(time.time() * 1000))
        biz = {k: v for k, v in (params or {}).items() if v is not None and v != ''}

        def _encode_value(v):
            if isinstance(v, str):
                return v
            if isinstance(v, bool):
                return 'true' if v else 'false'
            if isinstance(v, (int, float)):
                return json.dumps(v)
            return json.dumps(v, separators=(',', ':'), ensure_ascii=False)

        raw = '&'.join(f'{k}={_encode_value(v)}' for k, v in sorted(biz.items()))
        sign_str = f'{raw}&timestamp={ts}' if raw else f'timestamp={ts}'
        sign = hmac.new(
            self._app_key.encode('utf-8'), sign_str.encode('utf-8'), hashlib.sha256,
        ).hexdigest()
        return {
            'X-App-Id': self._app_id,
            'X-Timestamp': ts,
            'X-App-Sign': sign,
            'Content-Type': 'application/json',
        }

    def verify_callback(self, payload: dict, app_key: str) -> bool:
        """§5.2 入向验签：委托模块级 ``verify_callback_signature``（签名公式与重放无关）。"""
        return verify_callback_signature(payload, app_key)

    # ---------------------------------------------------------- 状态映射（D4）
    def to_canonical_status(self, raw: Any) -> Any:
        """供应商原始 status → 平台规范枚举（默认 identity；HMAC 已直接讲我们的枚举）。"""
        if raw is None:
            return raw
        try:
            return int(raw)
        except (TypeError, ValueError):
            return raw

    def from_canonical_status(self, status: Any) -> Any:
        """平台规范枚举 → 供应商原始 status（默认 identity）。"""
        return status

    # ---------------------------------------------------------- 能力协商（§8.2）
    def capabilities(self) -> dict:
        """供应商能力声明；默认空（具体 adapter 覆写）。"""
        return {}

    # ---------------------------------------------------------- 健康检查（§8.4）
    def health(self) -> BackgroundCheckResult:
        """GET /api/v1/health 探活；默认返回未实现（具体 adapter 覆写）。"""
        return BackgroundCheckResult(
            success=False,
            message='health not implemented',
            data={'capability': 'health'},
        )

    # ---------------------------------------------------------- 抽象网络方法
    @abstractmethod
    def create_order(self, req: 'CreateOrderRequest') -> BackgroundCheckResult:
        """创建背调订单。"""

    @abstractmethod
    def cancel_order(self, order_number: str) -> BackgroundCheckResult:
        """取消背调订单。"""

    @abstractmethod
    def query_order(self, order_number: str) -> BackgroundCheckResult:
        """轮询订单详情（§6.4 兜底）；返回内含最新 status 的对象。"""

    @abstractmethod
    def query_products(self, product_token: Optional[str] = None) -> BackgroundCheckResult:
        """套餐查询（§3.4）。"""

    @abstractmethod
    def fetch_report(self, order: Any) -> BackgroundCheckResult:
        """拉取背调报告（GET order.report_url）；normalize 为统一结构。"""
