"""M07 grep 守卫测试（eval 文档 §4.1 风险 V3：WRITE 执行链漏接导致动作不受限）。

用 AST 解析各业务实体 views 源码，断言「已知单实例写入口方法」的方法体内
存在 ensure_writable 调用。漏接即测试失败，迫使补接。

设计取舍：
- 仅对「单实例行级写入口」（拿到 self.get_object() 确定实例的那些）做强校验，
  因为它们适配 ensure_writable(user, entity, instance, action)。
- 列表/批量/创建类入口（create / merge / import / batch_*）走长尾：它们没有单一
  instance，需要「逐实例过滤写范围」(filter_writable) 而非 ensure_writable，
  语义不同，本守卫不硬校验，避免误伤。
- 只读方法（retrieve / histories / records / list_versions 等）同样不纳入。
"""
import ast
import inspect
import os
import re

# (views 模块相对路径, 类名, 方法名) —— 硬要求：方法体内必须含 ensure_writable(
GUARD_TARGETS = [
    # 样板（M07 首批）
    ('apps.candidate.views', 'CandidateViewSet', 'update'),
    ('apps.candidate.views', 'CandidateViewSet', 'transition'),
    ('apps.candidate.views', 'CandidateViewSet', 'blacklist'),
    ('apps.candidate.views', 'CandidateViewSet', 'unblacklist'),
    # 长尾：单实例行级写入口
    ('apps.application.views', 'ApplicationViewSet', 'advance'),
    ('apps.application.views', 'ApplicationViewSet', 'check_stage_transition'),
    ('apps.application.views', 'ApplicationViewSet', 'soft_reject'),
    ('apps.application.views', 'ApplicationViewSet', 'withdraw'),
    ('apps.application.views', 'ApplicationViewSet', 'pause'),
    ('apps.application.views', 'ApplicationViewSet', 'resume'),
    ('apps.application.views', 'ApplicationViewSet', 'upgrade_version'),
    ('apps.application.views', 'ApplicationViewSet', 'change_process'),
    ('apps.application.views', 'ApplicationViewSet', 'grab'),
    ('apps.application.views', 'ApplicationViewSet', 'release'),
    ('apps.demand.views', 'DemandViewSet', 'transition'),
    ('apps.offer.views', 'OfferViewSet', 'transition'),
    ('apps.onboarding.views', 'OnboardingViewSet', 'transition'),
    ('apps.position.views', 'PositionViewSet', 'update'),
    ('apps.position.views', 'PositionViewSet', 'transition'),
    ('apps.process.views', 'RecruitmentStageViewSet', 'destroy'),
    ('apps.process.views', 'RecruitmentStageViewSet', 'disable'),
    ('apps.process.views', 'RecruitmentStageViewSet', 'enable'),
    ('apps.process.views', 'RecruitmentProcessViewSet', 'archive'),
    ('apps.invitation.views', 'InvitationViewSet', 'transition'),
    ('apps.invitation.views', 'InvitationViewSet', 'grab'),
]

# 批量 / 恢复类写入口：没有单一 instance 可挂 ensure_writable，改用
# 「作用域内取数 + 逐条 is_writable」或「复用 get_object()」。这里断言它们
# **不得**退回全表 `Model.objects.get(pk=...)` —— 那会绕过行级范围，
# 等于「列表看不到，换个接口就能改」。
BATCH_OR_RESTORE_TARGETS = [
    # (module, class, method) -> 必须出现的守卫标记
    ('apps.process.views', 'RecruitmentProcessViewSet', 'batch_screen', '_writable_candidate_map'),
    ('apps.process.views', 'RecruitmentProcessViewSet', 'batch_recommend', '_writable_candidate_map'),
    ('apps.candidate.views', 'CandidateViewSet', 'merge', 'assert_candidates_writable'),
    ('apps.campus.views', 'CampusAmbassadorViewSet', 'restore', 'self.get_object()'),
    ('apps.campus.views', 'CampusSessionViewSet', 'restore', 'self.get_object()'),
    ('apps.campus_control.views', 'ControlDimensionViewSet', 'restore', 'self.get_object()'),
    ('apps.campus_control.views', 'ControlIndicatorViewSet', 'restore', 'self.get_object()'),
    ('apps.campus_control.views', 'ControlRuleViewSet', 'restore', 'self.get_object()'),
    ('apps.campus_control.views', 'PersonViewSet', 'restore', 'self.get_object()'),
]

# 允许出现但**不要求**接守卫的入口（记录型 create —— 新建对象无既有行可判定，
# 归属"谁建的"由 created_by 语义决定，不属于行级写范围问题）。
KNOWN_UNGUARDED_BY_DESIGN = {
    ('apps.candidate.views', 'CandidateViewSet', 'create'),
    ('apps.application.views', 'ApplicationViewSet', 'create'),
    ('apps.application.views', 'InvitationViewSet', 'create'),
}


def _load(module_dotted: str):
    import importlib
    return importlib.import_module(module_dotted)


def _method_source(module_dotted: str, cls_name: str, method: str) -> str | None:
    """取指定类指定方法的源码片段；类/方法不存在返回 None。"""
    fn = _find_method(module_dotted, cls_name, method)
    if fn is None:
        return None
    try:
        return inspect.getsource(fn)
    except (OSError, TypeError):
        return None


def _find_method(module_dotted: str, cls_name: str, method: str):
    """返回指定类指定方法的函数对象；不存在返回 None（供 AST 扫描用）。"""
    mod = _load(module_dotted)
    cls = getattr(mod, cls_name, None)
    if cls is None:
        return None
    return getattr(cls, method, None)


def test_write_entries_guarded():
    """所有登记在 GUARD_TARGETS 的单实例写入口都必须调用 ensure_writable。"""
    missing = []
    for module_dotted, cls_name, method in GUARD_TARGETS:
        src = _method_source(module_dotted, cls_name, method)
        if src is None:
            missing.append(f'{cls_name}.{method} (定位失败: 类或方法不存在)')
            continue
        if 'ensure_writable(' not in src:
            missing.append(f'{cls_name}.{method} ({module_dotted})')
    assert not missing, (
        '以下单实例行级写入口未接入 ensure_writable 守卫（M07 读写分离缺口）:\n  - '
        + '\n  - '.join(missing)
    )


def test_guard_targets_still_exist():
    """反向守卫：若这些方法被改名/删除，提醒同步更新本守卫清单。"""
    vanished = []
    for module_dotted, cls_name, method in GUARD_TARGETS:
        if _method_source(module_dotted, cls_name, method) is None:
            vanished.append(f'{cls_name}.{method}')
    assert not vanished, (
        f'GUARD_TARGETS 中以下方法已不存在: {vanished}\n'
        '（如确已重构/删除，请同步更新本守卫清单；'
        '若该写入口仍然存在只是改名，也必须同步迁移 ensure_writable 守卫）'
    )


def test_guarded_methods_use_known_actions():
    """守卫里传的 action 必须是 action_map 已注册动作（拼错会运行时早失败）。"""
    from apps.data_permission.action_map import is_known_action
    import re
    bad = []
    for module_dotted, cls_name, method in GUARD_TARGETS:
        src = _method_source(module_dotted, cls_name, method)
        if not src:
            continue
        for m in re.finditer(r"ensure_writable\([^)]*?action='([a-z_]+)'\)", src):
            action = m.group(1)
            if not is_known_action(action):
                bad.append(f'{cls_name}.{method}: action={action!r} 未在 ACTION_REGISTRY 注册')
    assert not bad, '守卫使用了未注册动作（validate_action 会在运行时抛错）:\n  - ' + '\n  - '.join(bad)


def _method_ast(fn):
    """把函数对象的源码 dedent 后解析成 AST 模块。

    注意: 必须传**函数对象**, 不能直接把函数丢给 ast.walk —— ast.walk 只吃 AST
    节点, 传函数会 AttributeError: 'function' object has no attribute '_fields'。
    """
    import textwrap
    src = inspect.getsource(fn)
    return ast.parse(textwrap.dedent(src))


def _raw_pk_lookups(fn) -> list[str]:
    """AST 扫描函数体, 返回形如 `X.objects.get(pk=...)` 的全表取调用（忽略注释/字符串）。

    必须用 AST 而非正则: 这些入口的注释里往往**正描述**被修掉的坏写法
    （"原为 Candidate.objects.get(pk=cid)"），正则会误伤注释而假红。
    """
    hits: list[str] = []
    try:
        tree = _method_ast(fn)
    except (OSError, TypeError, SyntaxError, IndentationError):
        return hits
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != 'get':
            continue
        # 形如 <something>.objects.get(...)
        val = func.value
        if not (isinstance(val, ast.Attribute) and val.attr == 'objects'):
            continue
        for kw in node.keywords:
            if kw.arg in ('pk', 'id'):
                hits.append(ast.unparse(node)[:80])
    return hits


def test_batch_and_restore_entries_not_bypassing_scope():
    """批量 / 恢复类写入口不得用全表 `Model.objects.get(pk=)` 绕过行级范围。

    这类入口没有单一 instance 可挂 ensure_writable，必须走
    「作用域内取数 + 逐条 is_writable」或复用 get_object()。
    若退回全表取，等于「列表看不到，换个接口就能改」。
    """
    missing, bypassed = [], []
    for module_dotted, cls_name, method, marker in BATCH_OR_RESTORE_TARGETS:
        fn = _find_method(module_dotted, cls_name, method)
        if fn is None:
            missing.append(f'{cls_name}.{method} (定位失败: 类或方法不存在)')
            continue
        if marker not in (inspect.getsource(fn) or ''):
            missing.append(f'{cls_name}.{method}: 缺少 `{marker}`')
        raw = _raw_pk_lookups(fn)
        if raw:
            bypassed.append(f'{cls_name}.{method}: {raw}')
    assert not missing, (
        '以下批量/恢复写入口缺少作用域守卫:\n  - ' + '\n  - '.join(missing))
    assert not bypassed, (
        '以下入口仍在用全表 `objects.get(pk=)` 取数，绕过行级范围:\n  - '
        + '\n  - '.join(bypassed))


def test_batch_and_restore_targets_exist():
    """反向守卫：入口被改名/删除时提醒同步更新清单。"""
    vanished = []
    for module_dotted, cls_name, method, _marker in BATCH_OR_RESTORE_TARGETS:
        if _method_source(module_dotted, cls_name, method) is None:
            vanished.append(f'{cls_name}.{method}')
    assert not vanished, (
        f'BATCH_OR_RESTORE_TARGETS 中以下方法已不存在: {vanished}\n'
        '（如仍存在只是改名，必须同步迁移作用域守卫）'
    )