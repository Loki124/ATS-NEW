"""Application 状态变更链路缺陷 — HTTP 层 / 服务层 / Celery 层实测回归。

背景（2026-08-07 严过关）
========================
``Application.state`` 是 ``FSMField(..., protected=True)``。protected 语义：**任何**
对已实例化对象的 ``instance.state = X`` 赋值都会抛
``AttributeError: Direct state modification is not allowed``（django_fsm/__init__.py:296），
只有被 ``@transition`` 装饰的方法才能改状态。

围绕这个约束，本文件锁死三类互相独立的缺陷：

D1 — 撤回 / 暂停 / 恢复三个端点必 500
-------------------------------------
``apps/application/views.py`` 调用了 ``ApplicationService`` 上**根本不存在**的三个方法::

    views.py:331  ApplicationService.withdraw_application(...)   # 不存在
    views.py:352  ApplicationService.pause_application(...)      # 不存在
    views.py:373  ApplicationService.resume_application(...)     # 不存在

同名函数只作为 ``services/__init__.py`` 的**模块级**便捷函数存在（第 760/765/770 行），
从未挂到类上。实测 ``POST /api/v1/applications/{id}/withdraw/`` 得到::

    AttributeError: type object 'ApplicationService' has no attribute
                    'withdraw_application'. Did you mean: 'start_application'?
      at apps/application/views.py:331 in withdraw

view 只 ``except StateTransitionError``，``AttributeError`` 穿透到
``apps.common.exceptions.custom_exception_handler`` 的兜底分支 → HTTP 500
``{"success":false,"code":"internal_error"}``。

⚠️ 关键：**这掩盖了第二层 bug。** ``ApplicationService.withdraw()`` 内部第 606 行有一句
裸赋值 ``application.state = ApplicationState.WITHDRAWN``，它同样必炸（protected 字段）。
但因为调用在第一层就 AttributeError 了，第 606 行**从未被执行过**。
只修 views 的方法名会让 500 换个堆栈继续 500；两层必须一起修。

D2 — 超时归档静默失败
---------------------
``ApplicationService.timeout_archive()``（services/__init__.py:716）同样裸赋值
``application.state = ApplicationState.TIMEOUT`` → 必抛 AttributeError。
其唯一调用方 ``apps/application/tasks.py:227`` 把它包在
``try/except Exception: logger.warning(...)`` 里，异常被吞。
实测：2 条符合归档条件的记录，任务返回 ``{'archived_count': 0}`` **且不抛异常**，
DB 里两条记录状态原封不动。监控看到的是"成功执行、归档 0 条"，没有任何告警。
（补充：该任务当前不在 ``CELERY_BEAT_SCHEDULE`` 中，尚未被调度，所以线上暂未发作。）

D3 — 死枚举 WITHDRAWN / TIMEOUT
-------------------------------
见 ``tests/test_fsm_state_reachability_guard.py``。D1/D2 是 D3 的直接后果：
因为没有 ``@transition`` 指向这两个状态，开发者只能退而裸赋值，而裸赋值在
protected 字段上必炸。

修复状态（2026-08-08 严过关复核）
================================
D1 / D2 / D3 **均已修复**，本文件 7 个 ``xfail(strict=True)`` 装饰器已全部摘除，
断言体一字未改就直接转绿 —— 这正是下面"红绿策略"想要的结果。

    D1  views.py 331/352/368 → ``.withdraw(`` / ``.pause(`` / ``.resume(``
    D1  ApplicationService.withdraw() 裸赋值 → ``application.withdraw()`` 状态机方法
    D2  ApplicationService.timeout_archive() 裸赋值 → ``application.timeout_archive()``
    D3  补 ``withdraw`` / ``timeout_archive`` 两条 @transition，死枚举清零

本文件的红绿策略（重要，供后续沿用）
====================================
所有"尚未实现的正确行为"一律用 ``@pytest.mark.xfail(strict=True)`` 标注，
**断言体直接写目标行为**（200 / 状态真的变了 / archived_count 真的等于待归档条数）。

选这种方式而不是"断言当前的 500"，理由有三：

1. **断言体已经是修复后的正确断言。** 源码修好后只需删掉一行装饰器，测试立刻
   成为有效回归测试，不需要重写断言，不会变成需要删掉的垃圾。
   （本轮实测：7 条全部只删装饰器即转绿，零断言改写。）
2. **strict=True 是自曝机制。** 修复落地的那一刻测试变 XPASS，而 strict 会把
   XPASS 判为 **失败** → 全量立刻变红 → 强制有人回来摘掉装饰器。
   不存在"改好了但测试还在假装缺陷仍在"的静默腐烂窗口。
3. **绝不写"断言 500 通过"这种绿灯。** 一个绿色的 ``assert status == 500``
   在 CI 报表里与"撤回端点工作正常"无法区分，是主动误导。缺陷现状记录在
   docstring 与 ``reason=`` 里，不占用绿灯语义。

⚠️ 测试作者注意：**不要对 Application 实例调用 ``refresh_from_db()``。**
Django 的 ``refresh_from_db`` 内部走 ``setattr(self, field.attname, ...)``
(django/db/models/base.py:765)，对 protected FSMField 同样触发
``AttributeError: Direct state modification is not allowed``。
本文件统一用 ``_reload(app).state`` 重新查库。
"""
from __future__ import annotations

import ast
import importlib
from datetime import timedelta
from pathlib import Path
from typing import List, Tuple

import pytest
from django.utils import timezone

from apps.application.models import Application, ApplicationStageRecord, ApplicationState
from apps.candidate.models import Candidate
from apps.position.models import Position, PositionState
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageRule,
    StageType,
)

DJANGO_ROOT = Path(__file__).resolve().parent.parent
APPS_ROOT = DJANGO_ROOT / 'apps'

APPLICATIONS_URL = '/api/v1/applications/'


def _reload(app: Application) -> Application:
    """重新查库拿最新状态。

    不能用 ``app.refresh_from_db()`` —— protected FSMField 会让它抛
    ``AttributeError: Direct state modification is not allowed``。
    """
    return Application.objects.get(pk=app.pk)


# ============================================================
# Fixtures — 完整外键链（Process → Stage → Link → Position → Candidate → Application）
# ============================================================
@pytest.fixture
def defect_process(db):
    return RecruitmentProcess.objects.create(
        id='proc-state-defect',
        code='STATE_DEFECT',
        name='状态缺陷回归流程',
        current_version='1.0',
        is_template=False,
        is_enabled=True,
    )


@pytest.fixture
def defect_stage(db):
    return RecruitmentStage.objects.create(
        id='stage-state-defect',
        code='PSDEF901',
        name='状态缺陷回归阶段',
        stage_type=StageType.SCREEN,
    )


@pytest.fixture
def defect_link(db, defect_process, defect_stage):
    link = ProcessStageLink.objects.create(
        id='link-state-defect',
        process=defect_process,
        stage=defect_stage,
        order=1,
        is_required=True,
    )
    StageRule.objects.create(id='rule-state-defect', link=link, is_grab_mode=False)
    return link


@pytest.fixture
def defect_position(db, department, super_user, defect_process):
    """招聘中的职位。复用 department / super_user 使超管 scope 与数据部门一致，
    排除 ScopeQuerysetMixin 的 IDOR 过滤干扰（否则会拿到 404 而不是我们要观察的 500）。
    """
    pos = Position.objects.create(
        id='pos-state-defect',
        code='P_STATE_DEFECT',
        title='状态缺陷回归职位',
        description='用于验证 withdraw / pause / resume / timeout_archive 链路',
        department=department,
        hiring_manager=super_user,
        owner=super_user,
        headcount=5,
        filled_count=0,
        state=PositionState.DRAFT,
        process=defect_process,
    )
    pos.submit_publish(); pos.save()
    pos.publish(); pos.save()
    pos.start_recruiting(); pos.save()
    return pos


def _make_application(
    code: str, cand_id: str, phone: str, state: str,
    position, process, stage, link, *, days_since_advance: int = 1,
) -> Application:
    """造一条指定状态的真实 Application。

    注意：``state=`` 走的是 ``Model.__init__``，不触发 FSMField 的 protected 描述符，
    所以构造期指定任意状态都是合法的 —— 只有对**已存在实例**赋值才会炸。
    """
    candidate = Candidate.objects.create(id=cand_id, name=f'候选人-{code}', phone=phone)
    return Application.objects.create(
        code=code,
        candidate=candidate,
        position=position,
        process=process,
        workflow_version=process.current_version,
        state=state,
        current_link=link,
        current_stage=stage,
        last_advanced_at=timezone.now() - timedelta(days=days_since_advance),
    )


@pytest.fixture
def active_application(db, defect_position, defect_process, defect_stage, defect_link):
    return _make_application(
        'APP-SD-ACTIVE', 'cand-sd-active', '13920000001',
        ApplicationState.ACTIVE, defect_position, defect_process, defect_stage, defect_link,
    )


@pytest.fixture
def paused_application(db, defect_position, defect_process, defect_stage, defect_link):
    return _make_application(
        'APP-SD-PAUSED', 'cand-sd-paused', '13920000002',
        ApplicationState.PAUSED, defect_position, defect_process, defect_stage, defect_link,
    )


@pytest.fixture
def onboarded_application(db, defect_position, defect_process, defect_stage, defect_link):
    return _make_application(
        'APP-SD-ONBOARDED', 'cand-sd-onboarded', '13920000003',
        ApplicationState.ONBOARDED, defect_position, defect_process, defect_stage, defect_link,
    )


@pytest.fixture
def stale_applications(db, defect_position, defect_process, defect_stage, defect_link):
    """2 条超过 90 天未推进的申请（ACTIVE + PAUSED），命中 archive_stale_applications 的查询条件。"""
    return [
        _make_application(
            'APP-SD-STALE-A', 'cand-sd-stale-a', '13920000011',
            ApplicationState.ACTIVE, defect_position, defect_process, defect_stage,
            defect_link, days_since_advance=200,
        ),
        _make_application(
            'APP-SD-STALE-B', 'cand-sd-stale-b', '13920000012',
            ApplicationState.PAUSED, defect_position, defect_process, defect_stage,
            defect_link, days_since_advance=200,
        ),
    ]


# ============================================================
# 前置条件 — 防假绿
# ============================================================
@pytest.mark.django_db
class TestPreconditions:
    """如果这些前置断言失败，下面所有用例的结论都不成立。"""

    def test_application_state_is_protected_fsm_field(self):
        """本文件全部缺陷的共同根因：state 是 protected FSMField。

        若哪天有人把 ``protected`` 改成 False，裸赋值就不再抛异常，
        本文件多条用例的失败原因会整体改变 —— 必须第一时间知道。
        """
        field = Application._meta.get_field('state')
        assert field.protected is True, (
            'Application.state 的 protected 已被改动；本文件所有关于'
            '"裸赋值必抛 AttributeError"的推理需要重新评估'
        )

    def test_direct_state_assignment_raises_on_loaded_instance(self, active_application):
        """坐实 protected 语义本身：对已加载实例赋值必抛 AttributeError。"""
        app = _reload(active_application)
        with pytest.raises(AttributeError, match='Direct state modification is not allowed'):
            app.state = ApplicationState.WITHDRAWN

    def test_transition_method_can_change_state(self, active_application):
        """对照组：走 @transition 方法则完全正常，证明上一条不是"状态机整个坏了"。"""
        app = _reload(active_application)
        app.send_offer_state()
        app.save()
        assert _reload(app).state == ApplicationState.OFFER_SENT


# ============================================================
# D1 根因守卫 — views 引用的 Service 方法必须真实存在
# ============================================================
def _collect_missing_service_attrs() -> List[Tuple[str, str, str]]:
    """扫描 apps/ 下所有业务模块里 ``<X>Service.<attr>`` 形式的引用，
    返回目标属性在类上**不存在**的那些。

    判据是运行时 ``hasattr``，不硬编码任何方法名白名单：
    将来任何人新增 Service 或新增调用点都自动纳入检查。

    只检查"在本模块内能解析成一个类对象"的 ``<X>Service`` 名字；
    通过变量/参数传进来的 service 实例无法静态解析，直接跳过（宁可漏报不误报）。
    """
    skip_parts = {'migrations', 'tests', '__pycache__'}
    missing: List[Tuple[str, str, str]] = []

    for py_file in sorted(APPS_ROOT.rglob('*.py')):
        rel = py_file.relative_to(DJANGO_ROOT)
        if skip_parts & set(rel.parts):
            continue

        tree = ast.parse(py_file.read_text(encoding='utf-8'), filename=str(py_file))
        refs = {
            (node.value.id, node.attr)
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id.endswith('Service')
        }
        if not refs:
            continue

        module_name = str(rel.with_suffix('')).replace('/', '.')
        try:
            module = importlib.import_module(module_name)
        except Exception:
            # 模块导入不了是另一类问题，不在本守卫职责内
            continue

        for service_name, attr in sorted(refs):
            service = getattr(module, service_name, None)
            if not isinstance(service, type):
                continue
            if not hasattr(service, attr):
                missing.append((str(rel), service_name, attr))

    return missing


class TestViewServiceContract:
    """静态+运行时混合守卫：调用点引用的服务方法必须真实存在。

    这类 bug 极其隐蔽：Python 的属性查找是运行期行为，模块能 import、
    Django 能启动、``manage.py check`` 全绿，只有那个 action 被真正打到的
    瞬间才 AttributeError。若该端点恰好没有测试覆盖（本例正是如此，
    withdraw/pause/resume 三个端点在 494 条基线里一条覆盖都没有），
    这行代码可以从上线起一次都没执行过。
    """

    def test_scan_actually_covers_service_references(self):
        """前置条件：必须真的扫到足量引用，防止扫描逻辑失效导致的"零违规"假绿。"""
        count = 0
        skip_parts = {'migrations', 'tests', '__pycache__'}
        for py_file in APPS_ROOT.rglob('*.py'):
            rel = py_file.relative_to(DJANGO_ROOT)
            if skip_parts & set(rel.parts):
                continue
            tree = ast.parse(py_file.read_text(encoding='utf-8'), filename=str(py_file))
            count += sum(
                1 for node in ast.walk(tree)
                if isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id.endswith('Service')
            )
        assert count > 50, (
            f'仅扫描到 {count} 处 <X>Service.<attr> 引用，远低于预期（实测 ~74 处），'
            f'说明遍历或解析逻辑已失效，本守卫形同虚设'
        )

    def test_all_service_attributes_referenced_in_apps_exist(self):
        """核心守卫：任何 ``<X>Service.<attr>`` 引用都必须能在类上落地。

        （原为 xfail(strict=True)；views.py 331/352/368 改为 ``.withdraw(`` /
        ``.pause(`` / ``.resume(`` 后转绿，装饰器已于 2026-08-08 摘除。）
        """
        missing = _collect_missing_service_attrs()
        assert not missing, (
            f'\n发现 {len(missing)} 处引用了不存在的 Service 方法'
            f'（属性查找是运行期行为，只有该代码路径被真正执行才会 AttributeError → 500）：\n'
            + '\n'.join(
                f'  {path}: {svc}.{attr} —— {svc} 上不存在该属性'
                for path, svc, attr in missing
            )
        )

    def test_detector_flags_a_known_missing_attribute(self):
        """反向自检：确保检测逻辑不是永远返回空的"哑巴守卫"。"""
        class _FakeService:
            @staticmethod
            def existing():
                return 1

        assert hasattr(_FakeService, 'existing')
        assert not hasattr(_FakeService, 'not_existing')


# ============================================================
# D1 — 撤回 / 暂停 / 恢复 HTTP 端点
# ============================================================
@pytest.mark.django_db
class TestWithdrawEndpoint:
    """POST /api/v1/applications/{id}/withdraw/

    实测现状（2026-08-07）：HTTP **500**，响应体
    ``{"success":false,"code":"internal_error","message":"服务器内部错误"}``，
    异常 ``AttributeError: type object 'ApplicationService' has no attribute
    'withdraw_application'`` 抛自 ``apps/application/views.py:331``。

    异常不会传播到测试进程 —— ``custom_exception_handler`` 的兜底分支把它
    转成了 500 Response，所以这里断言的是 ``response.status_code``，
    不需要 ``pytest.raises``，也不需要 ``raise_request_exception = False``。
    """

    def test_withdraw_active_application_succeeds(self, auth_client, active_application):
        """ACTIVE 的申请应能被撤回：返回 200，且 DB 状态真的变成 WITHDRAWN。

        （原为 xfail(strict=True)；views 方法名 + 服务层裸赋值两层都修好后转绿，
        装饰器已于 2026-08-08 摘除。）
        """
        resp = auth_client.post(
            f'{APPLICATIONS_URL}{active_application.id}/withdraw/',
            {'reason': '候选人已接受其他公司 offer'},
            format='json',
        )

        assert resp.status_code == 200, (
            f'撤回 ACTIVE 申请返回 {resp.status_code}，期望 200。'
            f'响应: {resp.content[:600]}'
        )
        assert _reload(active_application).state == ApplicationState.WITHDRAWN, (
            '端点返回成功，但 DB 里状态没变成 WITHDRAWN —— 状态写入未真正落库'
        )

    def test_withdraw_onboarded_application_returns_409(self, auth_client, onboarded_application):
        """已入职的申请不允许撤回，应返回 409 而不是 500。

        ``ApplicationService.withdraw()`` 对 ONBOARDED / REJECTED / TIMEOUT /
        WITHDRAWN 抛 ``StateTransitionError``，view 捕获后返 409 —— 这是设计约定的契约。

        注意：``OFFER_ACCEPTED`` **不在**拒绝名单里。撤回的 source 覆盖
        PENDING / ACTIVE / PAUSED / OFFER_SENT / OFFER_ACCEPTED 五态 ——
        "接了 Offer 但入职前反悔"是真实高频场景，见
        ``TestWithdrawFromOfferStates``。

        （原为 xfail(strict=True)；2026-08-08 摘除。）
        """
        resp = auth_client.post(
            f'{APPLICATIONS_URL}{onboarded_application.id}/withdraw/',
            {'reason': '尝试撤回已入职申请'},
            format='json',
        )

        assert resp.status_code == 409, (
            f'撤回 ONBOARDED 申请返回 {resp.status_code}，期望 409（业务拒绝）。'
            f'500 意味着这是崩溃而非拒绝。响应: {resp.content[:600]}'
        )
        assert _reload(onboarded_application).state == ApplicationState.ONBOARDED, (
            '被拒绝的撤回不应改动状态'
        )

    def test_withdraw_requires_reason(self, auth_client, active_application):
        """序列化器校验先于服务调用，所以缺 reason 时能正常拿到 400。

        这条**当前就是绿的**，价值在于证明：路由通、鉴权通、序列化器通，
        500 确实发生在"进入 service 调用"这一步，而不是更早的任何环节。
        """
        resp = auth_client.post(
            f'{APPLICATIONS_URL}{active_application.id}/withdraw/', {}, format='json',
        )
        assert resp.status_code == 400, (
            f'缺少 reason 应被序列化器拦成 400，实际 {resp.status_code}: {resp.content[:400]}'
        )


@pytest.mark.django_db
class TestPauseResumeEndpoints:
    """pause / resume 端点 —— 与 withdraw 完全同源的缺陷。

    实测现状（2026-08-07）：两个端点都 **500**::

        views.py:352  AttributeError: ... has no attribute 'pause_application'
        views.py:373  AttributeError: ... has no attribute 'resume_application'

    与 withdraw 不同的是：``ApplicationService.pause()`` / ``resume()`` 内部走的是
    ``@transition`` 方法（``application.pause()`` / ``application.resume()``），
    **没有**裸赋值问题。所以这两个端点只有"方法名挂错"一层 bug，
    把 views 的调用改成 ``ApplicationService.pause(...)`` / ``.resume(...)`` 即可修好。
    """

    def test_pause_active_application_succeeds(self, auth_client, active_application):
        """（原为 xfail(strict=True)；views.py:352 改为 ``.pause(`` 后转绿，2026-08-08 摘除。）"""
        resp = auth_client.post(
            f'{APPLICATIONS_URL}{active_application.id}/pause/',
            {'reason': '候选人要求暂缓'},
            format='json',
        )

        assert resp.status_code == 200, (
            f'暂停 ACTIVE 申请返回 {resp.status_code}，期望 200。响应: {resp.content[:600]}'
        )
        assert _reload(active_application).state == ApplicationState.PAUSED

    def test_resume_paused_application_succeeds(self, auth_client, paused_application):
        """（原为 xfail(strict=True)；views.py:368 改为 ``.resume(`` 后转绿，2026-08-08 摘除。）"""
        resp = auth_client.post(
            f'{APPLICATIONS_URL}{paused_application.id}/resume/', {}, format='json',
        )

        assert resp.status_code == 200, (
            f'恢复 PAUSED 申请返回 {resp.status_code}，期望 200。响应: {resp.content[:600]}'
        )
        assert _reload(paused_application).state == ApplicationState.ACTIVE


# ============================================================
# D2 — 超时归档静默失败
# ============================================================
@pytest.mark.django_db
class TestArchiveTimeout:
    """``ApplicationService.timeout_archive()`` 与 Celery 任务 ``archive_stale_applications``。"""

    def test_timeout_archive_currently_cannot_write_state(self, active_application):
        """根因取证（当前绿）：服务层裸赋值 TIMEOUT 必抛 AttributeError。

        这条断言的是 **protected FSMField 的框架语义**，不是产品行为，
        因此它现在绿、修好之后（改用 @transition）依然应该绿 ——
        因为届时 ``timeout_archive`` 不再走裸赋值，而是走状态机方法。

        它的守卫价值：如果哪天有人把 ``protected`` 关掉来"绕过"这个问题，
        本断言会立刻变红，提醒团队这是在拆掉状态机的保护而非修复问题。
        """
        app = _reload(active_application)
        with pytest.raises(AttributeError, match='Direct state modification is not allowed'):
            app.state = ApplicationState.TIMEOUT

    def test_timeout_archive_sets_state_to_timeout(self, active_application):
        """单元层：timeout_archive 应把状态写成 TIMEOUT 并落库。

        （原为 xfail(strict=True)；改用 ``application.timeout_archive()``
        状态机方法后转绿，2026-08-08 摘除。）
        """
        from apps.application.services import ApplicationService

        ApplicationService.timeout_archive(_reload(active_application))

        assert _reload(active_application).state == ApplicationState.TIMEOUT

    def test_archive_stale_task_actually_archives_stale_records(self, stale_applications):
        """Celery 任务应真的归档掉命中条件的记录，且计数与实际一致。

        这是"静默失败"最致命的地方：任务**成功返回**，只是 count 为 0。
        任何基于"任务是否抛异常"的监控都不会告警。

        （原为 xfail(strict=True)；D2 修复后转绿，2026-08-08 摘除。）
        """
        from apps.application.tasks import archive_stale_applications

        expected = len(stale_applications)
        assert expected == 2, '前置条件：应有 2 条待归档记录'

        result = archive_stale_applications(days=90)

        assert result['archived_count'] == expected, (
            f'任务报告归档 {result["archived_count"]} 条，实际有 {expected} 条命中条件。'
            f'返回值={result}。归档失败被 tasks.py:227 的 except Exception 吞掉了。'
        )
        for app in stale_applications:
            assert _reload(app).state == ApplicationState.TIMEOUT, (
                f'{app.code} 未被归档，DB 状态仍为 {_reload(app).state}'
            )

    def test_archive_stale_task_reports_count_consistent_with_db(self, stale_applications):
        """不变量（修复前后都必须成立）：任务返回的 archived_count
        必须等于 DB 中实际变成 TIMEOUT 的条数。

        当前 0 == 0 成立；修复后 2 == 2 也成立。
        它守的是另一类回归：**任务谎报**（count 报了但状态没落库，或反之）。
        """
        from apps.application.tasks import archive_stale_applications

        before = Application.objects.filter(state=ApplicationState.TIMEOUT).count()
        result = archive_stale_applications(days=90)
        after = Application.objects.filter(state=ApplicationState.TIMEOUT).count()

        assert result['archived_count'] == after - before, (
            f'任务报告归档 {result["archived_count"]} 条，但 DB 中 TIMEOUT 记录只增加了 '
            f'{after - before} 条 —— 返回值与实际落库不一致'
        )

    def test_archive_stale_task_does_not_touch_fresh_applications(
        self, active_application, stale_applications,
    ):
        """负向用例（修复前后都应绿）：未超期的申请不能被误归档。

        修复 D2 时最容易踩的坑就是放宽查询条件，这条把边界钉死。
        """
        from apps.application.tasks import archive_stale_applications

        archive_stale_applications(days=90)

        assert _reload(active_application).state == ApplicationState.ACTIVE, (
            '最近推进过的申请被误归档了'
        )


# ============================================================
# D4 — 状态改了但没落库（"内存绿、数据库红"）
# ============================================================
@pytest.fixture
def current_stage_record(db, active_application, defect_link, defect_stage):
    """给 ACTIVE 申请补一条"当前阶段"记录。

    ``advance_application_to_next_stage`` 会先按 ``link=current_link`` 查这条记录，
    查不到直接抛 ``StateTransitionError('Current stage record not found')``。
    """
    return ApplicationStageRecord.objects.create(
        application=active_application,
        link=defect_link,
        stage=defect_stage,
        state=ApplicationStageRecord.StageState.PROCESSING,
        entered_at=timezone.now() - timedelta(days=3),
    )


@pytest.mark.django_db
class TestStateChangesArePersisted:
    """状态变更必须**真的写进数据库**，而不只是改了内存里的对象。

    背景：``advance_application_to_next_stage`` 的终阶段分支曾经把 ``save()``
    错写在 ``except`` 里 —— 成功路径调用 ``send_offer_state()`` 改完内存状态后
    **从不落库**。这个 bug 逃过了当时全部测试，因为它们清一色断言
    ``result.application.state``（同一个内存对象），拿到的自然是改过的值。

    这类"内存改了但没 save"是本代码库的系统性风险（服务层大量
    ``application.xxx(); application.save()`` 两步写法，漏第二步不会报任何错），
    所以这里统一用**重新查库**的方式立断言，并且对每个状态变更入口都覆盖一条。

    ⚠️ 不能用 ``application.refresh_from_db()``：Django 内部走
    ``setattr(self, field.attname, ...)``，而 django_fsm 的
    ``FSMFieldDescriptor.__set__`` 在 ``protected and name in instance.__dict__``
    时直接抛 ``AttributeError``。已加载实例必然满足这个条件，所以 refresh 必炸。
    本文件统一用 ``_reload(app)`` 重新查询。
    """

    # ---------- 自检：断言手段本身必须有效 ----------
    def test_reload_really_requeries_database(self, active_application):
        """前置条件：``_reload`` 必须返回**新对象**并真的读库。

        如果它因为某种缓存返回同一个内存对象，下面所有"落库"断言都会
        退化成"内存断言"，整组用例静默失效。
        """
        first = _reload(active_application)
        second = _reload(active_application)
        assert first is not second, '_reload 返回了同一个对象，没有真的重新查库'
        assert first is not active_application

        # 绕过 ORM 直接改库，_reload 必须能看到变化
        Application.objects.filter(pk=active_application.pk).update(
            state=ApplicationState.PAUSED,
        )
        assert _reload(active_application).state == ApplicationState.PAUSED, (
            '_reload 没有反映出数据库里的真实值 —— 它读到的是缓存'
        )

    def test_refresh_from_db_is_unusable_on_protected_fsm_field(self, active_application):
        """坐实上面 docstring 的警告：refresh_from_db 在 protected FSMField 上必炸。

        这条防的是"好心人"把全文件的 ``_reload`` 换成看起来更地道的
        ``refresh_from_db``，结果整组用例集体报 AttributeError。
        """
        app = _reload(active_application)
        assert 'state' in app.__dict__, (
            '前置条件：state 应已加载进 __dict__，否则 protected 检查不会触发'
        )
        with pytest.raises(AttributeError, match='Direct state modification is not allowed'):
            app.refresh_from_db()

    # ---------- 核心：三个状态变更入口的落库断言 ----------
    def test_advance_to_terminal_stage_persists_offer_sent(
        self, active_application, current_stage_record,
    ):
        """终阶段推进后，**数据库里**的 state 必须是 OFFER_SENT。

        这正是"成功路径没 save"那个 bug 的专属回归用例：
        当时 ``send_offer_state()`` 改了内存、``save()`` 只在 except 分支里，
        内存断言全绿而 DB 原封不动。
        """
        from apps.application.services import ApplicationService

        result = ApplicationService.advance_application_to_next_stage(
            _reload(active_application), actor=None, reason='终阶段推进落库验证',
        )

        assert result.to_stage_name == 'OFFER', (
            f'前置条件：应推进到终阶段（无下一必经阶段），实际 {result.to_stage_name}'
        )
        # 内存对象改了 —— 这是原来唯一被断言的东西
        assert result.application.state == ApplicationState.OFFER_SENT
        # 数据库真的改了 —— 这才是本用例的意义
        assert _reload(active_application).state == ApplicationState.OFFER_SENT, (
            '推进到终阶段后内存状态是 OFFER_SENT，但数据库里不是 —— '
            'save() 没被调用（历史 bug：save 被写在 except 分支里，成功路径不落库）'
        )
        # 最强判据：走 SQL WHERE 过滤，彻底排除任何 Python 侧缓存
        assert Application.objects.filter(
            pk=active_application.pk, state=ApplicationState.OFFER_SENT,
        ).exists(), 'SQL 层面查不到 OFFER_SENT，状态确实没落库'

    def test_withdraw_persists_withdrawn_state(self, active_application):
        """``ApplicationService.withdraw`` 后数据库必须是 WITHDRAWN。"""
        from apps.application.services import ApplicationService

        returned = ApplicationService.withdraw(
            _reload(active_application), reason='落库验证', actor=None,
        )

        assert returned.state == ApplicationState.WITHDRAWN
        assert _reload(active_application).state == ApplicationState.WITHDRAWN, (
            'withdraw 改了内存状态但没落库'
        )
        assert Application.objects.filter(
            pk=active_application.pk, state=ApplicationState.WITHDRAWN,
        ).exists()

    def test_timeout_archive_persists_timeout_state(self, active_application):
        """``ApplicationService.timeout_archive`` 后数据库必须是 TIMEOUT。"""
        from apps.application.services import ApplicationService

        returned = ApplicationService.timeout_archive(_reload(active_application))

        assert returned.state == ApplicationState.TIMEOUT
        assert _reload(active_application).state == ApplicationState.TIMEOUT, (
            'timeout_archive 改了内存状态但没落库'
        )
        assert Application.objects.filter(
            pk=active_application.pk, state=ApplicationState.TIMEOUT,
        ).exists()

    def test_pause_and_resume_persist_each_step(self, active_application):
        """pause / resume 每一步都要落库，不能只在最后一步 save。"""
        from apps.application.services import ApplicationService

        ApplicationService.pause(_reload(active_application), reason='落库验证', actor=None)
        assert _reload(active_application).state == ApplicationState.PAUSED, (
            'pause 未落库'
        )

        ApplicationService.resume(_reload(active_application), actor=None)
        assert _reload(active_application).state == ApplicationState.ACTIVE, (
            'resume 未落库'
        )

    def test_withdraw_via_http_persists_state(self, auth_client, active_application):
        """端到端补一刀：HTTP 200 之后数据库必须真的变了。

        与 ``TestWithdrawEndpoint.test_withdraw_active_application_succeeds``
        的区别在于这里额外用 SQL WHERE 过滤确认，且断言响应体与 DB 一致 ——
        防"接口回显的是内存对象、DB 其实没写"这种最难发现的形态。
        """
        resp = auth_client.post(
            f'{APPLICATIONS_URL}{active_application.id}/withdraw/',
            {'reason': 'HTTP 落库验证'},
            format='json',
        )
        assert resp.status_code == 200, resp.content[:600]

        body_state = resp.json().get('state')
        db_state = _reload(active_application).state
        assert db_state == ApplicationState.WITHDRAWN, (
            f'HTTP 返回 200，但 DB 状态是 {db_state}'
        )
        assert body_state == db_state, (
            f'响应体回显 state={body_state}，DB 里却是 {db_state} —— '
            f'接口在拿未落库的内存对象糊弄调用方'
        )

    # ---------- 负向：状态机拒绝时不得留下半截写入 ----------
    def test_rejected_withdraw_leaves_state_untouched_in_db(self, onboarded_application):
        """被拒绝的撤回不能在 DB 里留下任何状态改动。"""
        from apps.common.exceptions import StateTransitionError
        from apps.application.services import ApplicationService

        with pytest.raises(StateTransitionError):
            ApplicationService.withdraw(
                _reload(onboarded_application), reason='应当被拒', actor=None,
            )

        assert _reload(onboarded_application).state == ApplicationState.ONBOARDED, (
            '撤回被拒绝，但 DB 状态却被改动了'
        )

    def test_timeout_archive_is_idempotent_and_does_not_write(self, onboarded_application):
        """状态不在 TIMEOUT_ARCHIVABLE_STATES 内时原样返回、不写库（幂等契约）。"""
        from apps.application.services import ApplicationService

        returned = ApplicationService.timeout_archive(_reload(onboarded_application))

        assert returned.state == ApplicationState.ONBOARDED
        assert _reload(onboarded_application).state == ApplicationState.ONBOARDED, (
            'timeout_archive 对不可归档状态应当完全不写库'
        )


# ============================================================
# 撤回 source 扩展 —— OFFER_SENT / OFFER_ACCEPTED
# ============================================================
@pytest.fixture
def offer_sent_application(db, defect_position, defect_process, defect_stage, defect_link):
    return _make_application(
        'APP-SD-OFFERSENT', 'cand-sd-offersent', '13920000004',
        ApplicationState.OFFER_SENT, defect_position, defect_process, defect_stage, defect_link,
    )


@pytest.fixture
def offer_accepted_application(db, defect_position, defect_process, defect_stage, defect_link):
    return _make_application(
        'APP-SD-OFFERACC', 'cand-sd-offeracc', '13920000005',
        ApplicationState.OFFER_ACCEPTED, defect_position, defect_process, defect_stage, defect_link,
    )


@pytest.fixture
def pending_application(db, defect_position, defect_process, defect_stage, defect_link):
    return _make_application(
        'APP-SD-PENDING', 'cand-sd-pending', '13920000006',
        ApplicationState.PENDING, defect_position, defect_process, defect_stage, defect_link,
    )


@pytest.mark.django_db
class TestWithdrawFromOfferStates:
    """撤回的 source 覆盖 5 态，其中 OFFER_ACCEPTED 是本轮最需要说清楚的一元。

    "接了 Offer 但入职前违约"是真实高频场景。把它压成 ``REJECTED``
    （语义是"本流程未通过"）会歪曲漏斗统计 —— 明明是候选人反悔，
    报表上看起来像是公司把人刷掉了。所以 ``withdraw`` 的 source 纳入
    OFFER_SENT / OFFER_ACCEPTED，只把真正的终态
    （ONBOARDED / REJECTED / TIMEOUT / WITHDRAWN）挡在外面。

    本类逐态锁死这个边界，防止将来有人"顺手收紧"回 3 态。
    """

    @pytest.mark.parametrize('fixture_name,expected_source', [
        ('pending_application', ApplicationState.PENDING),
        ('active_application', ApplicationState.ACTIVE),
        ('paused_application', ApplicationState.PAUSED),
        ('offer_sent_application', ApplicationState.OFFER_SENT),
        ('offer_accepted_application', ApplicationState.OFFER_ACCEPTED),
    ])
    def test_withdraw_succeeds_from_every_allowed_source(
        self, request, auth_client, fixture_name, expected_source,
    ):
        """5 个允许的 source 逐一走 HTTP 撤回，都必须 200 且落库为 WITHDRAWN。"""
        app = request.getfixturevalue(fixture_name)
        assert _reload(app).state == expected_source, '前置条件：fixture 状态不对'

        resp = auth_client.post(
            f'{APPLICATIONS_URL}{app.id}/withdraw/',
            {'reason': f'从 {expected_source} 撤回'},
            format='json',
        )

        assert resp.status_code == 200, (
            f'从 {expected_source} 撤回返回 {resp.status_code}，期望 200。'
            f'响应: {resp.content[:600]}'
        )
        assert _reload(app).state == ApplicationState.WITHDRAWN, (
            f'从 {expected_source} 撤回后 DB 状态未变成 WITHDRAWN'
        )

    def test_withdraw_from_offer_accepted_is_not_downgraded_to_rejected(
        self, offer_accepted_application,
    ):
        """语义守卫：OFFER_ACCEPTED 撤回必须落到 WITHDRAWN，不能被压成 REJECTED。

        REJECTED 的业务含义是"本流程未通过"（公司刷掉候选人），
        WITHDRAWN 是"候选人主动撤回"。两者在招聘漏斗统计里是完全不同的口径，
        混用会让"我们的 Offer 违约率"这类指标彻底失真。
        """
        from apps.application.services import ApplicationService

        ApplicationService.withdraw(
            _reload(offer_accepted_application), reason='入职前收到更好 offer', actor=None,
        )

        final = _reload(offer_accepted_application).state
        assert final == ApplicationState.WITHDRAWN, (
            f'从 OFFER_ACCEPTED 撤回后状态是 {final}。'
            f'若为 REJECTED，说明有人把候选人主动违约错误归类成"本流程未通过"，'
            f'会污染漏斗统计口径。'
        )

    # 显式写死手机号后缀，不要用 hash() —— str 的 hash 受 PYTHONHASHSEED 影响，
    # 每次进程启动都不同，会让 phone 变成不可复现的值（并带来极低概率的碰撞）。
    @pytest.mark.parametrize('terminal_state,phone_suffix', [
        (ApplicationState.ONBOARDED, '13920000101'),
        (ApplicationState.REJECTED, '13920000102'),
        (ApplicationState.WITHDRAWN, '13920000103'),
        (ApplicationState.TIMEOUT, '13920000104'),
    ])
    def test_withdraw_rejected_from_terminal_states(
        self, defect_position, defect_process, defect_stage, defect_link,
        terminal_state, phone_suffix,
    ):
        """4 个终态一律不允许撤回 —— 这是 source 的另一侧边界。"""
        from apps.common.exceptions import StateTransitionError
        from apps.application.services import ApplicationService

        app = _make_application(
            f'APP-SD-T-{terminal_state}', f'cand-sd-t-{terminal_state.lower()}',
            phone_suffix,
            terminal_state, defect_position, defect_process, defect_stage, defect_link,
        )

        with pytest.raises(StateTransitionError):
            ApplicationService.withdraw(_reload(app), reason='应当被拒', actor=None)

        assert _reload(app).state == terminal_state, (
            f'从终态 {terminal_state} 撤回被拒后，状态不应改变'
        )
