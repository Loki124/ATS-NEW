"""通用守卫：FSM 状态枚举必须可达（不允许死枚举）。

背景（2026-08-07 严过关）
========================
``Application`` 的 ``ApplicationState`` 定义了 9 个枚举值，但模型上的 ``@transition``
只覆盖到 6 个 target。``WITHDRAWN`` 和 ``TIMEOUT`` **没有任何 transition 指向它们**。

而 ``Application.state`` 是 ``FSMField(protected=True)`` —— protected 意味着裸赋值
``instance.state = X`` 必抛 ``AttributeError: Direct state modification is not allowed``。
两件事叠加的后果是：**这两个状态在运行期根本无法被写入**。

开发者遇到"没有 transition 可用"时的自然反应就是退回裸赋值，于是产生了
``services/__init__.py:606``（WITHDRAWN）和 ``:716``（TIMEOUT）两处必炸代码 ——
它们正是 ``tests/test_application_state_transition_defects.py`` 里 D1/D2 两个缺陷的根因。
死枚举不是"代码整洁度问题"，它会直接诱导出生产事故。

修复状态（2026-08-08 严过关复核）
================================
``Application`` 已补上两条 ``@transition``：``withdraw()`` → WITHDRAWN（5 元 source）、
``timeout_archive()`` → TIMEOUT（3 元 source），两个死枚举**已消除**，
台账中 ``application.Application.state`` 条目已按 ratchet 规则清除。
服务层改走状态机方法，不再裸赋值。其余 4 个模型的存量死枚举本轮未动，仍在台账中。

全库实测结论（2026-08-07 首测 / 2026-08-08 复测）
=================================================
本项目共 7 个 FSMField，**全部 ``protected=True``**。因此"没有 transition 指向"
就等价于"运行期完全不可写"，不存在"虽然没有 transition，但可以合法裸赋值"的例外 ——
这让本守卫的判据是**充分**的，不会产生误报。

    模型.字段                              不可达枚举值        08-08 状态
    ------------------------------------  ------------------  ----------
    candidate.Candidate.current_state      PENDING_ONBOARDING  仍存量
    application.Application.state          WITHDRAWN, TIMEOUT  **已修复**
    demand.Demand.state                    （无）              —
    position.Position.state                UNPUBLISHED         仍存量
    offer.Offer.state                      WITHDRAWN           仍存量
    onboarding.Onboarding.state            RESIGNED_DURING_PROBATION  仍存量

即首测 5 个模型共 6 个死枚举值，Application 修复后余 4 个模型共 4 个。

附带发现：7 个 FSMField **没有一个声明 ``choices=``**（``field.choices`` 全为空）。
枚举类与字段之间没有任何绑定关系，只靠 ``default=XxxState.YYY`` 间接关联。
后果是 Django 的模型校验、Admin 下拉、drf-spectacular schema 都拿不到合法取值集合。
本文件正是利用 ``type(field.default)`` 来反推枚举类的 —— 这也说明：
一旦有人把 default 改成裸字符串，本守卫会因为推断不出枚举类而降级失效，
所以下面专门有一条用例守着"每个 FSMField 都必须能推断出枚举类"。

设计：为什么用"债务台账"而不是全量 xfail
========================================
全局守卫如果整条 ``xfail``，在 6 个存量问题修完之前它对**新增**死枚举毫无防护 ——
明天有人再加一个不可达状态，测试照样 xfail，没有任何信号。

所以这里用**自清理债务台账**（ratchet）：

- ``KNOWN_UNREACHABLE`` 显式登记当前 6 个存量死枚举；
- ``test_no_new_unreachable_state_values``：实际 ⊆ 台账。新增死枚举 → **立刻红**。
  这是今天就生效的防护。
- ``test_known_unreachable_ledger_has_no_stale_entries``：台账 ⊆ 实际。
  某个死枚举被修好后台账条目变陈旧 → **立刻红** → 强制回来清理台账。
  台账因此不可能腐烂成一张过时的免罪符。

两条方向相反的断言夹住台账，使它只能随修复而缩小，不能悄悄扩大。
``test_ledger_matches_measured_baseline`` 的上限随每次清理同步收紧
（6 → 4），否则被清掉的名额会变成"可以再塞两个新死枚举"的免费额度。

``test_application_withdrawn_and_timeout_are_reachable`` 原本挂
``xfail(strict=True)``；A4 修复落地后它变 XPASS → strict 判失败 → 装饰器已摘除，
现在它是一条常规回归断言。

常量 ↔ transition source 一致性
================================
``TestServiceConstantsMatchTransitionSources`` 是本轮新增的守卫。
服务层的 ``WITHDRAWABLE_STATES`` / ``TIMEOUT_ARCHIVABLE_STATES`` 与模型上
``withdraw`` / ``timeout_archive`` 的 ``@transition`` source 表达的是同一份知识
（"哪些状态允许做这个动作"），分处两个文件必然漂移。
守卫用运行时内省把两边钉成完全相等 —— 不是 grep 源码文本，而是真的从
``Application.<method>._django_fsm.transitions`` 把 source 集合读出来。

防假绿
======
参照 ``tests/test_no_bad_relative_imports.py`` 的范式，本文件有三道自检：
1. ``test_scan_finds_all_fsm_fields`` —— 扫描必须真的找到 FSMField（空扫描=没测）；
2. ``test_every_fsm_field_has_discoverable_enum`` —— 枚举类必须都能推断出来；
3. ``test_detector_flags_synthetic_unreachable_state`` —— 用合成数据反向验证
   检测函数真的会报警，确保它不是永远返回空列表的哑巴守卫。
新增的一致性守卫同样配了自检（``test_transition_sources_helper_is_not_vacuous``），
防止 ``transition_sources()`` 因 django_fsm 私有属性变更而恒返回空集，
让"两个空集相等"骗过断言。
"""
from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, Sequence, Set, Type

import pytest
from django.apps import apps as django_apps
from django.db.models import Choices
from django_fsm import FSMFieldMixin

# ============================================================
# 债务台账 —— 存量死枚举（2026-08-07 首测 6 项 / 2026-08-08 复核余 4 项）
# ============================================================
# 修好某一项后，请同步从本台账删除对应条目，否则
# test_known_unreachable_ledger_has_no_stale_entries 会红。
#
# 2026-08-08：'application.Application.state': {'WITHDRAWN', 'TIMEOUT'} 已整条移除 ——
# 模型补上 withdraw() / timeout_archive() 两条 @transition 后该 model 已无任何
# 不可达枚举值，所以删的是整个 key 而不是集合里的元素。
# 同步把 LEDGER_SIZE_CEILING 从 6 收紧到 4。
KNOWN_UNREACHABLE: Dict[str, Set[str]] = {
    'candidate.Candidate.current_state': {'PENDING_ONBOARDING'},
    'position.Position.state': {'UNPUBLISHED'},
    'offer.Offer.state': {'WITHDRAWN'},
    'onboarding.Onboarding.state': {'RESIGNED_DURING_PROBATION'},
}

# 台账规模上限。每次清理后必须同步下调，否则腾出来的名额会变成
# "可以再塞 N 个新死枚举而不被 test_ledger_matches_measured_baseline 发现"的免费额度。
LEDGER_SIZE_CEILING = 4


class FsmFieldInfo(NamedTuple):
    """一个 FSMField 的可达性快照。"""

    key: str                    # 'app_label.Model.field'
    enum_cls: Optional[Type]    # 从 default 推断出的 TextChoices 子类
    default_value: Optional[str]
    all_values: List[str]
    targets: Set[str]           # 所有 @transition 的 target
    indeterminate: bool         # 含动态 target（GET_STATE / RETURN_VALUE / '*'），无法静态判定


# ============================================================
# 纯函数 —— 可用合成数据独立验证
# ============================================================
def compute_unreachable(
    all_values: Sequence[str], default_value: Optional[str], targets: Set[str],
) -> List[str]:
    """一个枚举值是"可达"的，当且仅当它是初始默认值、或至少有一个 transition 指向它。

    保持入参为朴素类型，使这个判定逻辑能脱离 Django 用合成数据反向自检。
    """
    return [
        value for value in all_values
        if value != default_value and value not in targets
    ]


def _normalize_target(target) -> Set[str]:
    """把 transition 的 target 归一成字符串集合。

    django_fsm 的 target 可能是：
      - TextChoices 成员或裸字符串 → 直接取值
      - ``RETURN_VALUE(...)`` / ``GET_STATE(...)`` → 有 ``allowed_states``
      - ``None``（表示不改变状态）→ 不贡献任何 target
    """
    if target is None:
        return set()
    allowed = getattr(target, 'allowed_states', None)
    if allowed:
        return {getattr(state, 'value', state) for state in allowed}
    if hasattr(target, 'allowed_states'):
        # 有该属性但为空/None → 动态且不可枚举
        return set()
    return {getattr(target, 'value', target)}


def _is_dynamic_target(target) -> bool:
    """target 是动态解析型（GET_STATE / RETURN_VALUE 且未声明 allowed_states）。"""
    return hasattr(target, 'allowed_states') and not getattr(target, 'allowed_states', None)


def transition_sources(model: Type, method_name: str) -> Set[str]:
    """运行时读出 ``model.<method_name>`` 这条 ``@transition`` 的 source 状态集合。

    django_fsm 把 ``source=[A, B, C]`` 摊平成 ``FSMMeta.transitions`` 字典的三个 key
    （每个 source 一条 Transition 记录），所以 source 集合就是 ``transitions`` 的键集。

    刻意**不**读源码文本、不做 grep —— 那样只能证明"源码里写了这几个字"，
    证明不了状态机运行时真的按这几个 source 工作。这里读的是 django_fsm
    实际用于放行/拒绝转换的同一份数据结构。

    :raises AssertionError: 方法不存在、或它根本不是一个 @transition。
    """
    method = getattr(model, method_name, None)
    assert method is not None, (
        f'{model.__name__} 上不存在方法 {method_name!r} —— '
        f'状态机被改动而本守卫未同步更新'
    )
    spec = getattr(method, '_django_fsm', None)
    assert spec is not None, (
        f'{model.__name__}.{method_name} 存在但没有 _django_fsm 元数据，'
        f'说明它不是 @transition 装饰的方法（或 django_fsm 私有属性已变更）。'
        f'本守卫赖以工作的内省链路已失效，必须先修好它再谈断言。'
    )
    return {getattr(src, 'value', src) for src in spec.transitions.keys()}


def introspect_fsm_fields() -> List[FsmFieldInfo]:
    """运行时内省全库所有 FSMField 的枚举值与 transition target。"""
    results: List[FsmFieldInfo] = []

    for model in django_apps.get_models():
        for field in model._meta.get_fields():
            if not isinstance(field, FSMFieldMixin):
                continue

            key = f'{model._meta.label}.{field.name}'
            default = field.default
            enum_cls = type(default) if isinstance(default, Choices) else None
            default_value = getattr(default, 'value', None) if enum_cls else None
            all_values = [member.value for member in enum_cls] if enum_cls else []

            targets: Set[str] = set()
            indeterminate = False
            for attr_name in dir(model):
                try:
                    candidate = getattr(model, attr_name)
                except Exception:
                    continue
                spec = getattr(candidate, '_django_fsm', None)
                if spec is None or spec.field.name != field.name:
                    continue
                for trans in spec.transitions.values():
                    if _is_dynamic_target(trans.target):
                        indeterminate = True
                    targets |= _normalize_target(trans.target)

            results.append(FsmFieldInfo(
                key=key,
                enum_cls=enum_cls,
                default_value=default_value,
                all_values=all_values,
                targets=targets,
                indeterminate=indeterminate,
            ))

    return sorted(results, key=lambda info: info.key)


def collect_unreachable() -> Dict[str, Set[str]]:
    """全库死枚举清单：``{'app.Model.field': {'STATE', ...}}``（只含非空项）。

    含动态 target 的字段直接跳过 —— 静态判不了就不判，宁可漏报不误报。
    """
    result: Dict[str, Set[str]] = {}
    for info in introspect_fsm_fields():
        if info.enum_cls is None or info.indeterminate:
            continue
        unreachable = compute_unreachable(info.all_values, info.default_value, info.targets)
        if unreachable:
            result[info.key] = set(unreachable)
    return result


def _render(mapping: Dict[str, Set[str]]) -> str:
    return '\n'.join(
        f'  {key}: {sorted(values)}' for key, values in sorted(mapping.items())
    ) or '  （空）'


# ============================================================
# 防假绿自检
# ============================================================
class TestGuardSelfChecks:
    """如果这三条不成立，下面的守卫可能在"什么都没检查"的情况下变绿。"""

    def test_scan_finds_all_fsm_fields(self):
        """前置条件：必须真的扫到 FSMField。空扫描等于没测。"""
        infos = introspect_fsm_fields()
        assert len(infos) >= 7, (
            f'仅扫描到 {len(infos)} 个 FSMField（实测应为 7 个），'
            f'说明内省逻辑已失效，本文件全部守卫形同虚设。'
            f'扫到的是: {[i.key for i in infos]}'
        )

    def test_every_fsm_field_has_discoverable_enum(self):
        """每个 FSMField 都必须能推断出枚举类，否则该字段会被静默跳过。

        本项目所有 FSMField 都没声明 ``choices=``，枚举类只能从
        ``type(field.default)`` 反推。若有人把 default 改成裸字符串
        （如 ``default='PENDING'``），推断失效 → 该字段被跳过 → 守卫对它失明。
        这条用例专门堵这个静默降级的口子。
        """
        blind = [info.key for info in introspect_fsm_fields() if info.enum_cls is None]
        assert not blind, (
            '以下 FSMField 无法从 default 推断出 TextChoices 枚举类，'
            '可达性守卫对它们完全失明：\n'
            + '\n'.join(f'  {key}' for key in blind)
            + '\n修法：把 default 写成枚举成员（如 default=XxxState.PENDING），'
              '或给字段补上 choices=XxxState.choices'
        )

    def test_every_fsm_field_actually_has_transitions(self):
        """每个 FSMField 至少要有一个 transition，否则整个状态机是死的。"""
        dead = [
            info.key for info in introspect_fsm_fields()
            if not info.targets and not info.indeterminate
        ]
        assert not dead, (
            '以下 FSMField 没有任何 @transition，状态永远停在默认值：\n'
            + '\n'.join(f'  {key}' for key in dead)
        )

    def test_detector_flags_synthetic_unreachable_state(self):
        """反向自检（变异验证）：用合成数据确认检测函数真的会报警。

        这是 green-red-green 的**常驻**版本 —— 不需要临时改动任何业务源码，
        每次跑测试都会重新验证一遍"检测器不是哑巴"。
        """
        values = ['DRAFT', 'ACTIVE', 'DONE', 'ORPHAN']

        # 坏例：ORPHAN 既不是默认值、也没有 transition 指向 → 必须被抓出来
        assert compute_unreachable(values, 'DRAFT', {'ACTIVE', 'DONE'}) == ['ORPHAN']

        # 好例：全部可达 → 不得误报
        assert compute_unreachable(values, 'DRAFT', {'ACTIVE', 'DONE', 'ORPHAN'}) == []

        # 边界：默认值本身无需 transition 指向，不算不可达
        assert compute_unreachable(values, 'DRAFT', {'ACTIVE', 'DONE', 'ORPHAN'}) == []
        assert 'DRAFT' not in compute_unreachable(values, 'DRAFT', set())

        # 边界：多个不可达值应全部列出，且保持枚举声明顺序
        assert compute_unreachable(values, 'DRAFT', {'ACTIVE'}) == ['DONE', 'ORPHAN']

    def test_normalize_target_handles_enum_and_dynamic_forms(self):
        """target 归一化：枚举成员 / 裸字符串 / allowed_states / None 四种形态。"""
        class _Dynamic:
            allowed_states = ['A', 'B']

        assert _normalize_target('X') == {'X'}
        assert _normalize_target(None) == set()
        assert _normalize_target(_Dynamic()) == {'A', 'B'}


# ============================================================
# 核心守卫 —— 双向夹逼的债务台账
# ============================================================
class TestNoUnreachableFsmStates:
    """死枚举台账只能缩小，不能扩大。"""

    def test_no_new_unreachable_state_values(self):
        """实际 ⊆ 台账：出现台账之外的新死枚举 → 红。

        这是**今天就生效**的防护：谁再往任何 TextChoices 里加一个没有
        transition 指向的状态，立刻被拦下。
        """
        actual = collect_unreachable()
        new_items: Dict[str, Set[str]] = {}
        for key, values in actual.items():
            extra = values - KNOWN_UNREACHABLE.get(key, set())
            if extra:
                new_items[key] = extra

        assert not new_items, (
            '\n发现台账之外的**新增**死枚举 —— 这些状态值没有任何 @transition 指向，\n'
            '而本项目所有 FSMField 都是 protected=True（裸赋值必抛 AttributeError），\n'
            '因此它们在运行期完全无法被写入：\n'
            + _render(new_items)
            + '\n\n修法二选一：\n'
              '  (a) 为该状态补一个 @transition（若业务确实需要这个状态）；\n'
              '  (b) 从 TextChoices 里删除该枚举值（若它本就是废弃定义）。\n'
              '不要用裸赋值绕过 —— protected FSMField 上那必然是 500。'
        )

    def test_known_unreachable_ledger_has_no_stale_entries(self):
        """台账 ⊆ 实际：某项被修好后台账条目变陈旧 → 红 → 强制清理台账。

        没有这条，台账会腐烂成一张过时的免罪符：状态早就修好了，
        台账还挂着，于是这个状态从此永久豁免检查。
        """
        actual = collect_unreachable()
        stale: Dict[str, Set[str]] = {}
        for key, values in KNOWN_UNREACHABLE.items():
            resolved = values - actual.get(key, set())
            if resolved:
                stale[key] = resolved

        assert not stale, (
            '\n以下状态已经可达（说明缺陷已被修复），但仍挂在 KNOWN_UNREACHABLE 台账里：\n'
            + _render(stale)
            + '\n\n请从本文件顶部的 KNOWN_UNREACHABLE 中删除这些条目，'
              '让台账继续对其余存量项保持有效。'
        )

    def test_ledger_matches_measured_baseline(self):
        """台账规模不得超过当前上限，防止有人整体放宽台账蒙混过关。

        上限随每次清理同步收紧（首测 6 → Application 修复后 4）。
        若只清台账不降上限，被腾出的名额就成了新死枚举的免费额度，
        ``test_no_new_unreachable_state_values`` 会因为"新增项已被登记"而放行。
        """
        total = sum(len(values) for values in KNOWN_UNREACHABLE.values())
        assert total <= LEDGER_SIZE_CEILING, (
            f'台账已膨胀到 {total} 项，超过当前上限 {LEDGER_SIZE_CEILING} 项。'
            f'台账只应随修复缩小，不应扩大。'
            f'如果你是在修复死枚举，请同时下调 LEDGER_SIZE_CEILING。'
        )


# ============================================================
# Application 状态机全量快照
# ============================================================
# 每条 @transition 的完整 (source 集合 → target)。
# 快照的意义是"改状态机必须显式改测试"，所以写全 source，不能只写方法名 ——
# 只对方法名做断言的话，把 withdraw 的 source 悄悄从 5 元缩成 2 元不会被发现。
#
# 2026-08-08：新增 withdraw / timeout_archive 两条，7 条 → 9 条。
EXPECTED_APPLICATION_TRANSITIONS = {
    'start':            ({'PENDING'},                       'ACTIVE'),
    'pause':            ({'ACTIVE'},                        'PAUSED'),
    'resume':           ({'PAUSED'},                        'ACTIVE'),
    'send_offer_state': ({'ACTIVE'},                        'OFFER_SENT'),
    'accept_offer':     ({'OFFER_SENT'},                    'OFFER_ACCEPTED'),
    'mark_onboarded':   ({'OFFER_ACCEPTED'},                'ONBOARDED'),
    'mark_rejected':    ({'ACTIVE', 'PAUSED'},              'REJECTED'),
    'withdraw':         ({'PENDING', 'ACTIVE', 'PAUSED',
                          'OFFER_SENT', 'OFFER_ACCEPTED'},  'WITHDRAWN'),
    'timeout_archive':  ({'PENDING', 'ACTIVE', 'PAUSED'},   'TIMEOUT'),
}


def _application_transition_map() -> Dict[str, tuple]:
    """运行时读出 Application 上全部 state transition 的 ``{方法名: (source集合, target)}``。"""
    from apps.application.models import Application

    field_name = 'state'
    result: Dict[str, tuple] = {}
    for attr_name in dir(Application):
        try:
            attr = getattr(Application, attr_name)
        except Exception:
            continue
        spec = getattr(attr, '_django_fsm', None)
        if spec is None or spec.field.name != field_name:
            continue
        targets = set()
        for trans in spec.transitions.values():
            targets |= _normalize_target(trans.target)
        assert len(targets) == 1, (
            f'Application.{attr_name} 有 {len(targets)} 个 target {sorted(targets)}，'
            f'本快照假定每条 transition 只有单一 target；出现多 target 请扩展快照结构'
        )
        sources = {getattr(src, 'value', src) for src in spec.transitions.keys()}
        result[attr_name] = (sources, targets.pop())
    return result


class TestApplicationStateReachability:
    """A4 专项 —— Application 的 WITHDRAWN / TIMEOUT。

    这两个曾是全部 6 个死枚举里危害最大的：它们**已经有调用方**
    （``ApplicationService.withdraw()`` / ``timeout_archive()``），
    调用方因为拿不到 transition 而退回裸赋值，直接造成 D1/D2 两个生产缺陷。
    2026-08-08 补上 transition 后已修复，本类转为常驻回归守卫。
    其余 4 个死枚举目前没有调用方，属于纯定义冗余，危害等级低得多。
    """

    def test_application_state_enum_and_transitions_snapshot(self):
        """把实测快照钉死，任何一侧变动都会红，便于人工复核。

        它不是断言"缺陷存在"，而是断言"我们对这个状态机的认知是最新的"。
        """
        from apps.application.models import Application, ApplicationState

        info = next(
            i for i in introspect_fsm_fields() if i.key == 'application.Application.state'
        )

        assert info.default_value == ApplicationState.PENDING.value
        assert set(info.all_values) == {
            'PENDING', 'ACTIVE', 'PAUSED', 'OFFER_SENT', 'OFFER_ACCEPTED',
            'ONBOARDED', 'REJECTED', 'WITHDRAWN', 'TIMEOUT',
        }
        assert info.targets == {
            'ACTIVE', 'PAUSED', 'OFFER_SENT', 'OFFER_ACCEPTED', 'ONBOARDED',
            'REJECTED', 'WITHDRAWN', 'TIMEOUT',
        }, f'transition target 集合发生变化: {sorted(info.targets)}'
        assert Application._meta.get_field('state').protected is True, (
            'protected 被关掉了 —— 死枚举将变成"可裸赋值"，本文件的危害性判断需重新评估'
        )

    def test_application_transition_table_full_snapshot(self):
        """全量 transition 表快照：方法名 + 完整 source 集合 + target 都钉死。

        比只断言 ``info.targets`` 严格得多：targets 只看"能到哪些状态"，
        看不出"从哪些状态能到"。把 withdraw 的 source 从 5 元缩成 2 元，
        targets 断言完全不受影响，只有本条会红。
        """
        actual = _application_transition_map()

        assert set(actual) == set(EXPECTED_APPLICATION_TRANSITIONS), (
            f'Application 的 @transition 方法集合发生变化。\n'
            f'  新增: {sorted(set(actual) - set(EXPECTED_APPLICATION_TRANSITIONS))}\n'
            f'  消失: {sorted(set(EXPECTED_APPLICATION_TRANSITIONS) - set(actual))}\n'
            f'改状态机必须同步更新 EXPECTED_APPLICATION_TRANSITIONS。'
        )

        diffs = []
        for name, (exp_sources, exp_target) in sorted(EXPECTED_APPLICATION_TRANSITIONS.items()):
            act_sources, act_target = actual[name]
            if act_sources != exp_sources or act_target != exp_target:
                diffs.append(
                    f'  {name}: 期望 {sorted(exp_sources)} → {exp_target}，'
                    f'实际 {sorted(act_sources)} → {act_target}'
                )
        assert not diffs, (
            'Application transition 表与快照不一致：\n' + '\n'.join(diffs)
            + '\n若这是有意的状态机变更，请更新 EXPECTED_APPLICATION_TRANSITIONS，'
              '并复核服务层 WITHDRAWABLE_STATES / TIMEOUT_ARCHIVABLE_STATES 是否需要同步。'
        )

    def test_application_transition_count_is_nine(self):
        """条数独立成条，便于回归时一眼看出"是不是有人整条删了"。"""
        actual = _application_transition_map()
        assert len(actual) == 9, (
            f'Application 上 state transition 实测 {len(actual)} 条，快照基线为 9 条: '
            f'{sorted(actual)}'
        )

    def test_application_withdrawn_and_timeout_are_reachable(self):
        """WITHDRAWN 与 TIMEOUT 必须各自至少有一个 @transition 可以到达。

        （原为 xfail(strict=True)；A4 修复落地后转 XPASS，装饰器已于 2026-08-08 摘除。）
        """
        info = next(
            i for i in introspect_fsm_fields() if i.key == 'application.Application.state'
        )
        unreachable = compute_unreachable(info.all_values, info.default_value, info.targets)

        assert unreachable == [], (
            f'ApplicationState 中以下状态不可达: {unreachable}。'
            f'当前 transition target 只有 {sorted(info.targets)}。'
        )

    def test_withdrawn_and_timeout_have_dedicated_transitions(self):
        """不止"可达"，还要坐实是由 withdraw / timeout_archive 这两条专门的
        transition 提供的 —— 防止有人图省事把 WITHDRAWN 挂到某条无关 transition
        的 target 上凑数、让可达性守卫变绿。
        """
        from apps.application.models import Application

        actual = _application_transition_map()
        assert actual.get('withdraw', (None, None))[1] == 'WITHDRAWN'
        assert actual.get('timeout_archive', (None, None))[1] == 'TIMEOUT'

        # 且这两个 target 各自只有唯一入口，语义不含糊
        withdrawn_entries = [n for n, (_, t) in actual.items() if t == 'WITHDRAWN']
        timeout_entries = [n for n, (_, t) in actual.items() if t == 'TIMEOUT']
        assert withdrawn_entries == ['withdraw'], (
            f'WITHDRAWN 有多个入口 {withdrawn_entries}，撤回语义被稀释'
        )
        assert timeout_entries == ['timeout_archive'], (
            f'TIMEOUT 有多个入口 {timeout_entries}，超时归档语义被稀释'
        )
        assert Application._meta.get_field('state').protected is True


# ============================================================
# 服务层常量 ↔ transition source 一致性
# ============================================================
# 被守护的成对知识：左边是服务层的业务前置判断，右边是状态机的硬约束。
#   (服务层模块属性名, 模型方法名, 人类可读说明)
CONSTANT_TRANSITION_PAIRS = [
    (
        'WITHDRAWABLE_STATES',
        'withdraw',
        '候选人主动撤回：服务层不满足则直接 409，状态机不满足则拒绝转换',
    ),
    (
        'TIMEOUT_ARCHIVABLE_STATES',
        'timeout_archive',
        '超时归档：服务层不满足则幂等返回，状态机不满足则拒绝转换',
    ),
]


def _constant_values(module, attr_name: str) -> Set[str]:
    """把服务层常量归一成字符串集合，并顺带校验它没被写成会静默出错的形态。"""
    raw = getattr(module, attr_name, None)
    assert raw is not None, (
        f'apps.application.services 上不存在常量 {attr_name} —— '
        f'它要么被删了、要么被改名了，一致性守卫失去锚点'
    )
    assert isinstance(raw, (tuple, list, set, frozenset)), (
        f'{attr_name} 的类型是 {type(raw).__name__}，期望 tuple/list/set。'
        f'若被误写成裸字符串，``state not in {attr_name}`` 会退化成子串匹配 —— '
        f'那是个静默的逻辑炸弹'
    )
    values = [getattr(v, 'value', v) for v in raw]
    assert len(values) == len(set(values)), (
        f'{attr_name} 存在重复项: {sorted(values)}'
    )
    return set(values)


class TestServiceConstantsMatchTransitionSources:
    """服务层"允许做这个动作的状态"必须与状态机 source 完全相等。

    为什么值得单独守
    ================
    同一份知识（"哪些状态允许撤回 / 允许超时归档"）被写在两个文件里：

      apps/application/services/__init__.py   WITHDRAWABLE_STATES / TIMEOUT_ARCHIVABLE_STATES
      apps/application/models.py              @transition(source=[...])

    两边任何一侧单独改动都会产生真实故障，而且**两个方向的故障形态不同**：

    - 常量比 source 宽：服务层放行 → 状态机拒绝 → try/except 转成
      StateTransitionError → 用户拿到 409，但错误信息来自状态机而非业务层，
      且服务层可能已经执行了前置副作用（如 withdraw 里先调了
      ``CandidateService.withdraw``），造成部分写入。
    - 常量比 source 窄：状态机本来允许的转换被业务层提前挡掉 → 功能静默缺失，
      没有任何异常，测不出来。

    所以这里要求**完全相等**（==），不是包含关系。
    """

    def test_withdrawable_states_matches_withdraw_transition_source(self):
        from apps.application import services as app_services
        from apps.application.models import Application

        constant = _constant_values(app_services, 'WITHDRAWABLE_STATES')
        sources = transition_sources(Application, 'withdraw')

        assert constant == sources, (
            '\nWITHDRAWABLE_STATES 与 Application.withdraw 的 @transition source 不一致：\n'
            f'  服务层常量:      {sorted(constant)}\n'
            f'  状态机 source:   {sorted(sources)}\n'
            f'  仅常量有（服务层会放行但状态机会拒绝 → 部分写入后 409）: '
            f'{sorted(constant - sources)}\n'
            f'  仅状态机有（状态机允许但业务层提前挡掉 → 功能静默缺失）: '
            f'{sorted(sources - constant)}\n'
            '两者表达同一份业务知识，必须同改。'
        )

    def test_timeout_archivable_states_matches_timeout_archive_transition_source(self):
        from apps.application import services as app_services
        from apps.application.models import Application

        constant = _constant_values(app_services, 'TIMEOUT_ARCHIVABLE_STATES')
        sources = transition_sources(Application, 'timeout_archive')

        assert constant == sources, (
            '\nTIMEOUT_ARCHIVABLE_STATES 与 Application.timeout_archive 的 '
            '@transition source 不一致：\n'
            f'  服务层常量:      {sorted(constant)}\n'
            f'  状态机 source:   {sorted(sources)}\n'
            f'  仅常量有（timeout_archive 会走到状态机然后抛 StateTransitionError，'
            f'而调用方 tasks.py 把异常吞掉 → 静默失败）: {sorted(constant - sources)}\n'
            f'  仅状态机有（可归档的记录被业务层提前放行掉 → 永远归档不到）: '
            f'{sorted(sources - constant)}\n'
            '两者表达同一份业务知识，必须同改。'
        )

    def test_all_pairs_are_covered_by_explicit_cases(self):
        """台账自检：``CONSTANT_TRANSITION_PAIRS`` 里的每一对都必须有显式用例守着。

        防止有人往列表里加一对却忘了写断言，让"登记了"被误当成"守住了"。
        """
        from apps.application import services as app_services
        from apps.application.models import Application

        mismatches = []
        for const_name, method_name, desc in CONSTANT_TRANSITION_PAIRS:
            constant = _constant_values(app_services, const_name)
            sources = transition_sources(Application, method_name)
            if constant != sources:
                mismatches.append(
                    f'  {const_name} ({desc})\n'
                    f'    常量 {sorted(constant)} != source {sorted(sources)}'
                )
        assert not mismatches, (
            '\n以下常量/transition 对不一致：\n' + '\n'.join(mismatches)
        )

    def test_constants_contain_only_declared_enum_values(self):
        """常量里不能出现 ApplicationState 之外的野字符串（拼错也算）。"""
        from apps.application import services as app_services
        from apps.application.models import ApplicationState

        valid = {m.value for m in ApplicationState}
        for const_name, _, _ in CONSTANT_TRANSITION_PAIRS:
            values = _constant_values(app_services, const_name)
            unknown = values - valid
            assert not unknown, (
                f'{const_name} 含 ApplicationState 未定义的值 {sorted(unknown)} —— '
                f'很可能是拼写错误。合法取值: {sorted(valid)}'
            )


class TestConstantTransitionGuardSelfChecks:
    """上面那组守卫的防假绿自检。

    最危险的失效模式是 ``transition_sources()`` 因 django_fsm 私有属性变更而
    恒返回空集：届时若常量也恰好被清空，"两个空集相等"会让守卫静默通过。
    """

    def test_transition_sources_helper_is_not_vacuous(self):
        """helper 必须真的读出非空 source，且规模与人工核对一致。"""
        from apps.application.models import Application

        withdraw_sources = transition_sources(Application, 'withdraw')
        timeout_sources = transition_sources(Application, 'timeout_archive')

        assert len(withdraw_sources) == 5, (
            f'withdraw 的 source 实测 {len(withdraw_sources)} 个 '
            f'{sorted(withdraw_sources)}，人工核对基线为 5 个。'
            f'若确为有意变更，请同步 EXPECTED_APPLICATION_TRANSITIONS 与本断言。'
        )
        assert len(timeout_sources) == 3, (
            f'timeout_archive 的 source 实测 {len(timeout_sources)} 个 '
            f'{sorted(timeout_sources)}，人工核对基线为 3 个。'
        )
        # 单元素 source 也要能正确读出（防止 helper 只对多元 source 有效）
        assert transition_sources(Application, 'start') == {'PENDING'}

    def test_transition_sources_raises_on_non_transition_method(self):
        """helper 遇到"不是 transition"必须显式炸，而不是返回空集蒙混过关。"""
        from apps.application.models import Application

        with pytest.raises(AssertionError, match='不是 @transition'):
            transition_sources(Application, '__str__')

        with pytest.raises(AssertionError, match='不存在方法'):
            transition_sources(Application, 'no_such_method_at_all')

    def test_guard_turns_red_when_constant_drifts(self, monkeypatch):
        """变异自检：把常量改宽 / 改窄，一致性断言必须真的变红。

        直接对服务层模块属性打 monkeypatch（用例结束自动还原），
        走的是与真实守卫完全相同的比较路径。
        """
        from apps.application import services as app_services
        from apps.application.models import Application, ApplicationState

        checker = TestServiceConstantsMatchTransitionSources()

        # 基线必须绿，否则本变异验证无意义
        checker.test_withdrawable_states_matches_withdraw_transition_source()

        original = tuple(app_services.WITHDRAWABLE_STATES)

        # 变异 1：改宽 —— 塞入一个状态机不接受的 source
        monkeypatch.setattr(
            app_services, 'WITHDRAWABLE_STATES',
            original + (ApplicationState.ONBOARDED,),
        )
        with pytest.raises(AssertionError, match='ONBOARDED'):
            checker.test_withdrawable_states_matches_withdraw_transition_source()

        # 变异 2：改窄 —— 砍掉 OFFER_ACCEPTED（本轮争议最大的那一元）
        narrowed = tuple(s for s in original if s != ApplicationState.OFFER_ACCEPTED)
        assert len(narrowed) == len(original) - 1, '前置条件：OFFER_ACCEPTED 应在常量中'
        monkeypatch.setattr(app_services, 'WITHDRAWABLE_STATES', narrowed)
        with pytest.raises(AssertionError, match='OFFER_ACCEPTED'):
            checker.test_withdrawable_states_matches_withdraw_transition_source()

        # 变异 3：清空 —— 空集不得与非空 source 判等
        monkeypatch.setattr(app_services, 'WITHDRAWABLE_STATES', ())
        with pytest.raises(AssertionError):
            checker.test_withdrawable_states_matches_withdraw_transition_source()

        # 顺带确认状态机侧没被本用例污染
        assert len(transition_sources(Application, 'withdraw')) == 5

    def test_guard_turns_red_when_transition_source_drifts(self, monkeypatch):
        """反方向变异：常量不动，改动状态机 source，断言同样必须红。

        这条覆盖"工程师改了 models.py 但没改 services 常量"的真实场景。
        """
        from django_fsm import transition

        from apps.application import services as app_services
        from apps.application.models import Application, ApplicationState

        checker = TestServiceConstantsMatchTransitionSources()
        checker.test_timeout_archivable_states_matches_timeout_archive_transition_source()

        field = Application._meta.get_field('state')

        def _shrunk(self):
            pass

        # 把 timeout_archive 的 source 从 3 元缩成 1 元
        monkeypatch.setattr(
            Application, 'timeout_archive',
            transition(
                field=field,
                source=ApplicationState.PENDING,
                target=ApplicationState.TIMEOUT,
            )(_shrunk),
        )
        assert transition_sources(Application, 'timeout_archive') == {'PENDING'}, (
            '前置条件：变异未生效，本用例无法证明任何事'
        )

        with pytest.raises(AssertionError, match='ACTIVE'):
            checker.test_timeout_archivable_states_matches_timeout_archive_transition_source()

        # 常量本身没被动过
        assert _constant_values(app_services, 'TIMEOUT_ARCHIVABLE_STATES') == {
            'PENDING', 'ACTIVE', 'PAUSED',
        }
