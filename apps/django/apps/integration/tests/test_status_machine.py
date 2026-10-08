"""T6 背调订单状态机 测试。

覆盖：
- ALLOWED_ORDER_TRANSITIONS 中每个合法转移都能成功驱动（updated + is_legal_transition=True）
- 一个非法转移被拒绝但仍落库（is_legal_transition=False，订单按供应商权威更新）
"""
from apps.integration.models import (
    ALLOWED_ORDER_TRANSITIONS,
    BGOrderStatus,
)
from apps.integration.services import (
    apply_callback_to_order,
    create_background_check_order,
)
from apps.integration.tests.helpers import make_payload


def test_all_allowed_transitions(bg_config):
    order = create_background_check_order(
        config=bg_config, candidate_id='c', items=[], order_number='SM1',
    )
    for from_status, to_set in ALLOWED_ORDER_TRANSITIONS.items():
        if not to_set:
            continue
        for to_status in to_set:
            # 每次都从 from_status 出发，避免链式累积影响 is_legal 判定
            order.status = from_status
            order.status_name = BGOrderStatus.label_of(from_status)
            order.save()
            _o, ev, action = apply_callback_to_order(make_payload('SM1', to_status), bg_config)
            assert action == 'updated', f'{from_status}->{to_status}'
            assert _o.status == to_status
            assert ev.is_legal_transition is True


def test_illegal_transition_persisted(bg_config):
    create_background_check_order(
        config=bg_config, candidate_id='c', items=[], order_number='SM2',
    )
    # ACCEPTED(0) -> COMPLETED(1) 非法（ALLOWED[0]={2,3,5,6,7,8}）
    _o, ev, action = apply_callback_to_order(make_payload('SM2', 1), bg_config)
    assert action == 'updated'
    assert _o.status == 1
    assert ev.is_legal_transition is False
