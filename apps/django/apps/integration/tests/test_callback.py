"""T6 回调验签 + 状态机驱动 测试。

覆盖 verify_background_check_callback 的错误码分支（40001/40101/40102/40103），
以及 apply_callback_to_order 的 幂等（created/updated/noop）+ 非法转移落库 + 状态名映射。
"""
import time

from apps.integration.services import (
    verify_background_check_callback,
    apply_callback_to_order,
)
from apps.integration.models import BackgroundCheckOrder, BGOrderStatus
from apps.integration.tests.helpers import make_payload


def test_verify_valid(bg_config):
    payload = make_payload('N1', 3)
    ok, code, _msg, cfg = verify_background_check_callback(payload, 'sp_test')
    assert ok is True and code == 0 and cfg is not None


def test_verify_invalid_appid(bg_config):
    payload = make_payload('N1', 3)
    ok, code, _msg, _cfg = verify_background_check_callback(payload, 'sp_unknown')
    assert ok is False and code == 40101


def test_verify_bad_sign(bg_config):
    ts = int(time.time() * 1000)
    payload = {'number': 'N1', 'status': 3, 'timestamp': ts, 'sign': 'bad'}
    ok, code, _msg, _cfg = verify_background_check_callback(payload, 'sp_test')
    assert ok is False and code == 40102


def test_verify_stale_timestamp(bg_config):
    ts = int(time.time() * 1000) - 6 * 60 * 1000
    payload = make_payload('N1', 3, ts=ts)
    ok, code, _msg, _cfg = verify_background_check_callback(payload, 'sp_test')
    assert ok is False and code == 40103


def test_verify_missing_field(bg_config):
    payload = {'number': 'N1', 'status': 3}  # 缺 timestamp / sign
    ok, code, _msg, _cfg = verify_background_check_callback(payload, 'sp_test')
    assert ok is False and code == 40001


def test_apply_idempotency_created_updated_noop(bg_config):
    p1 = make_payload('N2', 3, statusName='背调中', riskLevel=2, reportUrl='', completionTime=123)
    order, _ev, action = apply_callback_to_order(p1, bg_config)
    assert action == 'created'
    assert order.status == 3

    # 同 status/completionTime/risk → 幂等 noop，不重复写事件
    _order2, ev2, action2 = apply_callback_to_order(p1, bg_config)
    assert action2 == 'noop' and ev2 is None

    # 状态变更 → updated
    p3 = make_payload('N2', 1, statusName='已完成', riskLevel=1, reportUrl='http://r', completionTime=456)
    order3, _ev3, action3 = apply_callback_to_order(p3, bg_config)
    assert action3 == 'updated'
    assert order3.status == 1


def test_illegal_transition_persisted(bg_config):
    apply_callback_to_order(make_payload('N3', 3), bg_config)  # ACCEPTED(0)->IN_PROGRESS(3) 合法
    # IN_PROGRESS(3) -> PENDING_AUTH(2) 非法（ALLOWED[3]={1,6,7,8}）
    order, ev, action = apply_callback_to_order(make_payload('N3', 2), bg_config)
    assert action == 'updated'
    assert ev.is_legal_transition is False
    assert order.status == 2  # 仍按供应商权威落库


def test_status_name_mapping(bg_config):
    order, _ev, _action = apply_callback_to_order(make_payload('N4', 3, statusName=''), bg_config)
    assert order.status_name == BGOrderStatus.label_of(3)
