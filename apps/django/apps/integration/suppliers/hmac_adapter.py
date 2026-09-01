"""HMAC-SHA256 背调供应商适配器（T6 参考实现）

严格沿用既有 services.py 的 wire 行为（§1.4.3 出向签名 / §5.2 回调验签 / 端点路径），
仅把网络职责从 services 收敛到适配器，并补齐 query_order / fetch_report 两个缺失接口。

⚠️ T6 范围边界：``create_order`` 仍只发送 ``{requestId, candidateId, items}``，
以兼容既有后端落库逻辑与前端字段。规范 §3.2 的完整 camelCase 字段（productToken /
candidateName / phone / operatorName / operatorPhone 等）属于 T6.1 范围，本适配器
仅接收 ``CreateOrderRequest`` 中 ``candidate_id`` / ``items`` 两个向后兼容字段。
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

import requests

from .base import (
    BaseBackgroundCheckSupplier,
    BackgroundCheckResult,
    CreateOrderRequest,
    SUCCESS_CODES,
)


def _safe_json(response: 'requests.Response') -> Dict[str, Any]:
    """解析 JSON 响应；失败返回 {}（不抛异常）。"""
    try:
        return response.json()
    except Exception:
        return {}


class HmacBackgroundCheckSupplier(BaseBackgroundCheckSupplier):
    """平台 ↔ 供应商 HMAC-SHA256 双向签名适配器（规范默认供应商）。"""

    # —— 具名端点（D6）—— 与既有 services 行为一致
    CREATE_PATH = '/api/v1/background-check/orders'
    CANCEL_PATH = '/api/v1/background-check/cancel'
    PRODUCTS_PATH = '/api/v1/background-check/products'
    ORDER_DETAIL_PATH = '/api/v1/background-check/orders/{number}'
    HEALTH_PATH = '/api/v1/health'

    # ---------------------------------------------------------- 内部 HTTP 封装
    def _url(self, path: str) -> str:
        return f'{self._base_url.rstrip("/")}{path}'

    def _post_json(self, path: str, params: dict,
                   success_by_http: bool = False) -> BackgroundCheckResult:
        """POST JSON（带签名头）；``success_by_http`` 为 True 时仅按 HTTP 200/201 判定。"""
        url = self._url(path)
        t0 = time.time()
        try:
            headers = self.sign_request(params)
            resp = requests.post(url, json=params, headers=headers, timeout=10)
            duration_ms = int((time.time() - t0) * 1000)
            body = _safe_json(resp)
            if success_by_http:
                ok = resp.status_code in (200, 201)
            else:
                ok = resp.status_code == 200 and self._is_success(body)
            return BackgroundCheckResult(
                success=ok,
                message='OK' if ok else f'HTTP {resp.status_code}',
                data=body,
                duration_ms=duration_ms,
                raw=resp,
            )
        except requests.RequestException as e:
            return BackgroundCheckResult(
                success=False,
                message=f'请求异常: {e}',
                duration_ms=int((time.time() - t0) * 1000),
            )

    def _get_json(self, path: str, query: Optional[dict] = None) -> BackgroundCheckResult:
        """GET（带签名头）；按业务信封 code 判定成功。"""
        url = self._url(path)
        t0 = time.time()
        try:
            headers = self.sign_request({})
            resp = requests.get(url, params=query or {}, headers=headers, timeout=10)
            duration_ms = int((time.time() - t0) * 1000)
            body = _safe_json(resp)
            ok = resp.status_code == 200 and self._is_success(body)
            return BackgroundCheckResult(
                success=ok,
                message='OK' if ok else f'HTTP {resp.status_code}',
                data=body,
                duration_ms=duration_ms,
                raw=resp,
            )
        except requests.RequestException as e:
            return BackgroundCheckResult(
                success=False,
                message=f'请求异常: {e}',
                duration_ms=int((time.time() - t0) * 1000),
            )

    # ---------------------------------------------------------- 抽象方法实现
    def create_order(self, req: CreateOrderRequest) -> BackgroundCheckResult:
        """创建订单（T6 范围：发送 {requestId, candidateId, items}）。"""
        params = {
            'requestId': req.request_id or str(uuid.uuid4()),
            'candidateId': req.candidate_id or '',
            'items': list(req.items or []),
        }
        return self._post_json(self.CREATE_PATH, params, success_by_http=True)

    def cancel_order(self, order_number: str) -> BackgroundCheckResult:
        """取消订单（按业务 code 判定成功）。"""
        params = {'number': order_number}
        return self._post_json(self.CANCEL_PATH, params, success_by_http=False)

    def query_order(self, order_number: str) -> BackgroundCheckResult:
        """轮询订单详情（§6.4 兜底）：GET 详情 → 取最新 status → 映射到规范枚举。

        返回 data 为订单详情内层对象（含 status / statusName / riskLevel / reportUrl /
        completionTime），status 已通过 ``to_canonical_status`` 归一到平台枚举（HMAC 为 identity）。
        """
        path = self.ORDER_DETAIL_PATH.format(number=order_number)
        res = self._get_json(path)
        if not res.success:
            return res
        envelope = res.data or {}
        inner = envelope.get('data') or {}
        normalized = dict(inner)
        normalized['status'] = self.to_canonical_status(inner.get('status'))
        return BackgroundCheckResult(
            success=True,
            message=res.message,
            data=normalized,
            duration_ms=res.duration_ms,
            raw=res.raw,
        )

    def query_products(self, product_token: Optional[str] = None) -> BackgroundCheckResult:
        """套餐查询（§3.4）：``productToken`` 可选，传则只查该套餐。"""
        query: Dict[str, Any] = {}
        if product_token:
            query['productToken'] = product_token
        return self._get_json(self.PRODUCTS_PATH, query=query)

    def fetch_report(self, order: Any) -> BackgroundCheckResult:
        """拉取背调报告：GET ``order.report_url``，normalize 为统一结构。

        真实网络行为；测试通过 MockSupplier 覆写本方法，不触发网络。
        返回 data = {report_url, content_type, fetched_at, size}。
        """
        report_url = getattr(order, 'report_url', '') or ''
        if not report_url:
            return BackgroundCheckResult(
                success=False,
                message='订单无报告地址',
                data={'report_url': ''},
            )
        t0 = time.time()
        try:
            resp = requests.get(report_url, timeout=15)
            duration_ms = int((time.time() - t0) * 1000)
            size = len(resp.content) if resp.content is not None else 0
            ok = resp.status_code == 200
            return BackgroundCheckResult(
                success=ok,
                message='OK' if ok else f'HTTP {resp.status_code}',
                data={
                    'report_url': report_url,
                    'content_type': resp.headers.get('Content-Type', ''),
                    'fetched_at': int(time.time() * 1000),
                    'size': size,
                },
                duration_ms=duration_ms,
                raw=resp,
            )
        except requests.RequestException as e:
            return BackgroundCheckResult(
                success=False,
                message=f'报告拉取异常: {e}',
                data={'report_url': report_url},
                duration_ms=int((time.time() - t0) * 1000),
            )

    # ---------------------------------------------------------- 能力 / 健康
    def capabilities(self) -> dict:
        """能力声明（§8.2）。"""
        return {
            'provider': 'hmac',
            'supports_callback': True,
            'supports_polling': True,    # query_order
            'supports_products': True,
            'supports_report': True,
            'auth_ways': [1, 2, 3],
            'report_format': ['url'],
        }

    def health(self) -> BackgroundCheckResult:
        """GET /api/v1/health 探活（§8.4）。"""
        if not self._base_url:
            return BackgroundCheckResult(
                success=False, message='未配置 BaseURL', data={},
            )
        return self._get_json(self.HEALTH_PATH)
