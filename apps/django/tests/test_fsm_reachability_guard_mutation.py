"""守卫的守卫 —— 对 test_fsm_state_reachability_guard.py 做常驻变异验证。

为什么需要这个文件
==================
``tests/test_fsm_state_reachability_guard.py`` 里的死枚举守卫是"断言某个集合为空"
形式的。这类守卫有一个众所周知的腐烂模式：**内省逻辑悄悄失效后，集合恒为空，
测试永远绿，而它其实什么都没在检查**。django_fsm 是已停止维护的包
（启动就打 deprecation warning，官方建议迁移到 viewflow.fsm），
未来任何一次升级都可能改动 ``_django_fsm`` / ``transitions`` / ``target``
这些本守卫赖以工作的私有属性，让内省静默返回空集。

守卫文件内部已有一条基于**合成数据**的反向自检
（``test_detector_flags_synthetic_unreachable_state``），验证纯函数
``compute_unreachable`` 的判定逻辑。但它绕开了 Django 内省这一层 ——
恰恰是最容易随依赖升级而失效的那一层。

本文件补上这个缺口：对**真实模型注册表**施加变异，验证守卫在真实内省链路上
确实会变红。这是完整的 green-red-green：

  变异 A  摘掉一个真实 transition → 出现新死枚举 → 守卫必须红
  变异 B  给台账里的真实条目补上 transition（模拟"缺陷修好了但没清台账"）
          → 台账陈旧检测必须红
  变异 B' 往台账塞一个已可达的状态 → 台账陈旧检测必须红（B 的镜像方向）
  变异 C  还原后 → 全部回绿

全部变异都通过 pytest ``monkeypatch`` 在运行时施加、用例结束自动还原，
**不修改任何业务源码文件**。

2026-08-08 改造记录（严过关）
=============================
原变异 B 用的锚点是"往台账里塞一个本来就不在台账里的可达状态"
（``demand.Demand.state: {CANCELLED}``）。它能跑，但**没有触碰真实台账内容** ——
台账怎么变它都绿，证明力偏弱。

Application 的 WITHDRAWN / TIMEOUT 修复后从台账中移除，正好暴露了一个更真实的
腐烂场景：**条目还在台账里，但对应缺陷已经被修好**。因此把变异 B 改造成
直接对台账中**仍然存活**的条目（``offer.Offer.state`` 的 ``WITHDRAWN``）动手：
运行时给 ``Offer`` 注入一条 ``target=WITHDRAWN`` 的 transition，
让这个台账条目当场变陈旧，验证守卫真的会红。

选 ``offer.Offer.state`` 的理由：它是台账 4 项存量里唯一"目标状态语义明确、
且当前确实零 transition 指向"的干净锚点，注入一条 transition 的效果完全确定。

⚠️ 本文件刻意不用 ``from ... import TestNoUnreachableFsmStates``（不带别名）——
那会让 pytest 在本模块里**重复收集**整个守卫测试类，同一条用例跑两遍、
失败时在两个文件名下各报一次，干扰定位。统一用 ``_GuardTests`` 别名规避。

实测记录::

    2026-08-07  变异 A: GREEN → 摘掉 Demand.cancel → RED，准确定位
                        demand.Demand.state: ['CANCELLED']
                变异 B: GREEN → 台账塞入 demand.Demand.state:{CANCELLED} → RED
                变异 C: 还原后 3 条守卫全部 GREEN
    2026-08-08  变异 B 改锚点为 offer.Offer.state/WITHDRAWN（真实台账条目）：
                        GREEN → 注入 Offer.withdraw transition → RED
                变异 B' 保留原 demand 路径作为镜像验证
"""
from __future__ import annotations

from typing import Optional, Tuple

import tests.test_fsm_state_reachability_guard as guard
# 带别名导入：避免 pytest 在本模块重复收集守卫测试类（见模块 docstring）。
from tests.test_fsm_state_reachability_guard import (
    KNOWN_UNREACHABLE,
    TestNoUnreachableFsmStates as _GuardTests,
)


def _run(test_name: str) -> Tuple[str, Optional[str]]:
    """执行真实守卫用例，返回 ('GREEN', None) 或 ('RED', 断言消息)。"""
    try:
        getattr(_GuardTests(), test_name)()
        return 'GREEN', None
    except AssertionError as exc:
        return 'RED', str(exc)


def _inject_transition(monkeypatch, model, method_name, source, target):
    """运行时给 ``model`` 注入一条 ``@transition``，用例结束由 monkeypatch 自动摘除。

    走的是 django_fsm 真正的 ``transition()`` 装饰器，因此守卫的内省链路
    （``getattr(model, attr)._django_fsm.transitions``）会像对待源码里写死的
    transition 一样看到它 —— 这正是本文件想验证的那条链路。
    """
    from django_fsm import transition

    def _synthetic(self):  # pragma: no cover - 只用于内省，从不被调用
        pass

    _synthetic.__name__ = method_name
    decorated = transition(
        field=model._meta.get_field('state'), source=source, target=target,
    )(_synthetic)
    monkeypatch.setattr(model, method_name, decorated, raising=False)
    return decorated


# ============================================================
# 变异 A —— 摘掉真实 transition，新死枚举必须被抓到
# ============================================================
def test_guard_turns_red_when_a_transition_disappears(monkeypatch):
    """变异 A：摘掉 ``Demand.cancel``（唯一 target=CANCELLED 的 transition），
    ``CANCELLED`` 随即变成台账之外的新死枚举，守卫必须抓到。

    选 Demand 是因为它当前 0 死枚举（干净基线），且 ``cancel`` 是
    ``CANCELLED`` 的唯一入口，摘掉后效果确定。
    """
    from apps.demand.models import Demand

    state, _ = _run('test_no_new_unreachable_state_values')
    assert state == 'GREEN', (
        '基线就不是绿的，本变异验证无意义 —— 请先让 test_no_new_unreachable_state_values 通过'
    )

    monkeypatch.delattr(Demand, 'cancel')

    state, message = _run('test_no_new_unreachable_state_values')
    assert state == 'RED', (
        '摘掉了唯一指向 CANCELLED 的 transition，守卫却仍然是绿的 —— '
        '说明 Django 内省链路已失效（很可能是 django_fsm 私有属性变更），'
        '死枚举守卫此刻是个哑巴，不再提供任何保护'
    )
    assert 'demand.Demand.state' in message and 'CANCELLED' in message, (
        f'守卫变红了，但没有准确指出是 demand.Demand.state 的 CANCELLED，'
        f'报错信息可用性不足:\n{message}'
    )


def test_guard_turns_red_when_application_withdraw_transition_disappears(monkeypatch):
    """变异 A'：摘掉本轮刚补上的 ``Application.withdraw``，
    ``WITHDRAWN`` 立刻退回死枚举，且它已**不在**台账里 → 守卫必须红。

    这条直接守住本轮修复本身：将来谁把 withdraw 删了或改名，
    不会悄无声息地回到 2026-08-07 那个"撤回端点必 500"的状态。
    """
    from apps.application.models import Application

    state, _ = _run('test_no_new_unreachable_state_values')
    assert state == 'GREEN', '基线就不是绿的，本变异验证无意义'

    monkeypatch.delattr(Application, 'withdraw')

    state, message = _run('test_no_new_unreachable_state_values')
    assert state == 'RED', (
        '摘掉了唯一指向 WITHDRAWN 的 transition，守卫却仍然是绿的 —— '
        'A4 的修复此刻没有任何回归保护'
    )
    assert 'application.Application.state' in message and 'WITHDRAWN' in message, (
        f'守卫变红了，但没准确指出 application.Application.state 的 WITHDRAWN:\n{message}'
    )


# ============================================================
# 变异 B —— 台账条目变陈旧，必须被抓到
# ============================================================
def test_guard_turns_red_when_ledger_entry_becomes_stale(monkeypatch):
    """变异 B：给台账里**真实存活**的条目 ``offer.Offer.state: {WITHDRAWN}``
    注入一条 transition，让它当场变成"已修好但没清台账"，陈旧检测必须抓到。

    这是本文件里最贴近真实腐烂场景的一条：Application 的 WITHDRAWN/TIMEOUT
    正是这样被修好的，如果当时没人清台账，这两个状态就会从此永久豁免检查。
    """
    from apps.offer.models import Offer, OfferState

    # 前置：该条目必须真的还在台账里，且当前确实不可达 —— 否则变异无意义
    assert 'offer.Offer.state' in KNOWN_UNREACHABLE, (
        'offer.Offer.state 已不在台账中（可能已被修复并清理）。'
        '请把本变异的锚点换成台账里另一个仍然存活的条目，'
        '不要把这条用例改成永远绿的空壳。'
    )
    assert KNOWN_UNREACHABLE['offer.Offer.state'] == {'WITHDRAWN'}, (
        f'台账中 offer.Offer.state 的内容已变为 '
        f'{sorted(KNOWN_UNREACHABLE["offer.Offer.state"])}，本变异需要同步调整'
    )
    assert guard.collect_unreachable().get('offer.Offer.state') == {'WITHDRAWN'}, (
        '实测 offer.Offer.state 的 WITHDRAWN 已经可达，台账应当已被清理 —— '
        '此时 test_known_unreachable_ledger_has_no_stale_entries 本身就该是红的'
    )

    state, _ = _run('test_known_unreachable_ledger_has_no_stale_entries')
    assert state == 'GREEN', '基线就不是绿的，本变异验证无意义'

    # 变异：注入 SENT → WITHDRAWN，让 WITHDRAWN 变可达
    _inject_transition(
        monkeypatch, Offer, 'withdraw_synthetic',
        source=OfferState.SENT, target=OfferState.WITHDRAWN,
    )
    assert guard.collect_unreachable().get('offer.Offer.state') is None, (
        '前置条件：注入 transition 后 offer.Offer.state 应已无死枚举，'
        '变异未生效则本用例证明不了任何事'
    )

    state, message = _run('test_known_unreachable_ledger_has_no_stale_entries')
    assert state == 'RED', (
        '台账里挂着一个明明已经可达的状态，陈旧检测却没报 —— '
        '台账将退化成一张过时的免罪符'
    )
    assert 'offer.Offer.state' in message and 'WITHDRAWN' in message, (
        f'守卫变红了，但没准确指出是 offer.Offer.state 的 WITHDRAWN:\n{message}'
    )


def test_guard_turns_red_when_ledger_gains_an_already_reachable_entry(monkeypatch):
    """变异 B'：镜像方向 —— 不动模型，往台账里塞一个本来就可达的状态。

    与变异 B 互补：B 改模型让台账条目失效，B' 改台账引入无效条目。
    两条一起保证陈旧检测对"台账 ⊄ 实际"的两种成因都敏感。
    """
    state, _ = _run('test_known_unreachable_ledger_has_no_stale_entries')
    assert state == 'GREEN', '基线就不是绿的，本变异验证无意义'

    polluted = {**KNOWN_UNREACHABLE, 'demand.Demand.state': {'CANCELLED'}}
    monkeypatch.setattr(guard, 'KNOWN_UNREACHABLE', polluted)

    state, message = _run('test_known_unreachable_ledger_has_no_stale_entries')
    assert state == 'RED', (
        '台账里挂着一个明明已经可达的状态，陈旧检测却没报 —— '
        '台账将退化成一张过时的免罪符'
    )
    assert 'CANCELLED' in message


def test_ledger_ceiling_guard_turns_red_when_ledger_inflates(monkeypatch):
    """变异 B''：台账规模上限守卫必须真的会红。

    ``LEDGER_SIZE_CEILING`` 在本轮从 6 收紧到 4。如果这条上限断言是个摆设，
    被清掉的名额就成了新死枚举的免费额度。这里直接把台账撑爆来验证。
    """
    state, _ = _run('test_ledger_matches_measured_baseline')
    assert state == 'GREEN', '基线就不是绿的，本变异验证无意义'

    inflated = {
        **KNOWN_UNREACHABLE,
        'fake.Model.state': {'A', 'B', 'C', 'D', 'E'},
    }
    monkeypatch.setattr(guard, 'KNOWN_UNREACHABLE', inflated)

    state, message = _run('test_ledger_matches_measured_baseline')
    assert state == 'RED', (
        f'台账被撑到 {sum(len(v) for v in inflated.values())} 项，'
        f'上限 {guard.LEDGER_SIZE_CEILING} 却没拦住 —— 上限断言形同虚设'
    )
    assert '台账已膨胀' in message


# ============================================================
# 变异 C —— 可逆性
# ============================================================
def test_all_guards_green_after_mutations_reverted():
    """变异 C：monkeypatch 已由 pytest 自动还原，三条守卫必须全部回绿。

    证明前面所有用例的变异是**可逆**的，没有污染同一 session 里的其他测试。
    """
    for test_name in (
        'test_no_new_unreachable_state_values',
        'test_known_unreachable_ledger_has_no_stale_entries',
        'test_ledger_matches_measured_baseline',
    ):
        state, message = _run(test_name)
        assert state == 'GREEN', (
            f'变异还原后 {test_name} 仍是红的，说明 monkeypatch 泄漏到了其他用例: {message}'
        )


def test_mutated_models_are_restored_to_baseline():
    """变异 C'：被动过手脚的三个模型必须回到基线形态。

    ``test_all_guards_green_after_mutations_reverted`` 只看守卫是否回绿，
    看不出"注入的 transition 是否还挂在类上"。这条直接检查模型本身，
    防止注入物泄漏后污染后续用例的内省结果。
    """
    from apps.application.models import Application
    from apps.demand.models import Demand
    from apps.offer.models import Offer

    assert hasattr(Demand, 'cancel'), 'Demand.cancel 未被还原'
    assert hasattr(Application, 'withdraw'), 'Application.withdraw 未被还原'
    assert not hasattr(Offer, 'withdraw_synthetic'), (
        'Offer.withdraw_synthetic 注入物泄漏，后续用例的内省结果会被污染'
    )

    actual = guard.collect_unreachable()
    assert actual.get('offer.Offer.state') == {'WITHDRAWN'}, (
        f'offer.Offer.state 的死枚举未回到基线: {actual.get("offer.Offer.state")}'
    )
    assert 'application.Application.state' not in actual, (
        'application.Application.state 又出现死枚举，说明 withdraw/timeout_archive '
        '的还原不完整'
    )
