"""T3 死代码守卫：``versioning.upgrade_application_to_latest_version`` 不得复活。

为什么用函数级守卫而不是进 ``tests/test_no_dead_service_modules.py``
====================================================================
那份 ratchet 是**模块级**账本（``DeadModule(rel_path, symbol, reason)``），判据是
「文件还在不在」。本次删的是一个**函数**，宿主文件 ``versioning.py`` 必须继续存在，
模块级账本表达不了这个约束——硬塞进去只会让守卫对整个文件误报。故在此单开函数级守卫。

被删的是什么
------------
``upgrade_application_to_latest_version(application, target_process, actor)``：
零调用方、零测试覆盖，且自带 **V5 读后写缺陷**——先把 ``application.workflow_version``
赋成目标版本，之后才把**同一个字段**读作返回值里的 ``from_version``，导致
``from_version`` 恒等于 ``to_version``，升版本审计从上线起就一直在撒谎。零调用正是
它长期没被发现的原因。

「候选人升版本」的活实现只有一份：
``apps.application.services.ApplicationService.upgrade_workflow_version``。

这个守卫拦的是什么
------------------
有人（或某次 revert / merge）把这个函数原样搬回来。它一旦回归，读后写缺陷会跟着回归，
而且会与活实现形成两份语义相近但行为不同的升版本入口——这正是本项目反复治理的
「同一职责两处实现」。
"""
from __future__ import annotations

import inspect

from apps.process.services import versioning


def test_dead_upgrade_function_is_gone() -> None:
    """符号必须彻底消失（不是改名藏起来，也不是留个空壳）。"""
    assert not hasattr(versioning, 'upgrade_application_to_latest_version'), (
        'upgrade_application_to_latest_version 复活了 —— 它零调用零测试且含 V5 读后写缺陷'
        '（from_version 恒等于 to_version）。升版本的唯一实现是 '
        'apps.application.services.ApplicationService.upgrade_workflow_version。'
    )


def test_no_lookalike_upgrade_helper_sneaks_back_in() -> None:
    """连「换个名字搬回来」也拦住：本模块不得出现任何 ``upgrade_*`` 的公开函数。

    只断言原名会被一次改名绕过。流程版本服务的职责是「流程线怎么长出新版本」，
    「某条申请怎么迁到新版本」属于 application 域，本模块本来就不该有这类函数。
    """
    offenders = [
        name for name, obj in vars(versioning).items()
        if inspect.isfunction(obj)
        and obj.__module__ == versioning.__name__
        and name.lstrip('_').startswith('upgrade')
    ]
    assert offenders == [], (
        f'versioning 模块出现了升版本类函数 {offenders} —— 该职责属于 '
        'apps.application.services.ApplicationService.upgrade_workflow_version，'
        '不要在流程版本服务里开第二份实现'
    )


def test_versioning_module_still_exposes_its_real_api() -> None:
    """反向自检：确认上面两条断言不是因为整个模块被删/改名而「白通过」。"""
    for symbol in (
        'archive_process',
        'clone_process_with_new_version',
        'list_process_versions',
        'is_process_referenced',
        '_compute_next_version',
        '_compute_next_version_seq',
    ):
        assert hasattr(versioning, symbol), (
            f'versioning.{symbol} 不见了 —— 本文件的死代码守卫已退化为哑巴断言'
        )
