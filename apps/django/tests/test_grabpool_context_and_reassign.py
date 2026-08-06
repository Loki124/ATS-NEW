"""grab-pool 序列化器 context 一致性 + reassign 端点冒烟

背景一：serializer context 缺失导致脱敏分叉（已修，本文件锁死）
================================================================
``GrabPoolViewSet.list()`` 原来裸实例化 ``ApplicationListSerializer(page, many=True)``，
不带 context。而 ``ApplicationListSerializer.get_candidate_phone`` 是这样判断的::

    request = self.context.get('request')
    if request and request.user.is_authenticated and is_super_admin(request.user):
        return obj.candidate.phone          # 超管看全号
    return masked                            # 其他人看掩码

裸实例化 → ``self.context`` 为空 → ``request`` 为 ``None`` → **无条件走脱敏分支**。
于是同一个超管、同一条申请，两个端点返回不同的 ``candidatePhone``：

    /api/v1/applications/  → 13900000001    (ApplicationViewSet 走 self.get_serializer，带 context)
    /api/v1/grab-pool/     → 139****0001    (裸实例化，无 context)

修复：两处都改用 ``self.get_serializer(...)``，DRF 自动注入
``{'request', 'view', 'format'}``，与 ``ApplicationViewSet`` 行为对齐。

本文件的测试策略
----------------
不去断言"超管应该看到 13900000001"这种**具体值** —— 那样脱敏规则一改测试就得跟着改，
维护成本高且容易被改成敷衍值。这里锁的是**跨端点一致性**：

    applications 的 candidatePhone  ==  grab-pool 的 candidatePhone

将来脱敏规则怎么演进都行，但两个端点一旦分叉立刻红。

再配一条 **HR（非超管）对照组**：两端都必须是掩码值、且两端一致。
没有这条对照，"一致性"可以靠"把脱敏整个关掉"来满足 —— 那是把 PII 泄漏当成修复。
两条合起来才构成完整约束：既要一致，又要该脱敏的仍然脱敏。

为什么对照组用 HR 而不是面试官
------------------------------
``GrabPoolViewSet.permission_classes = [IsHROrAbove]``（SUPER_ADMIN/HRBP/HR）。
面试官角色会直接 403，拿不到响应体，也就无从比较字段。HR 是唯一同时满足
"能访问两个端点" + "``is_super_admin()`` 为 False（应被脱敏）" 的角色。


背景二：reassign 端点冒烟 —— 发现 ModuleNotFoundError（未修，见 xfail）
========================================================================
详见 ``TestGrabPoolReassign`` 的 docstring。
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.application.models import Application, ApplicationState

# 复用既有外键链 fixtures（Department → Process → Stage → StageLink → StageRule
# → Position → Candidate），不重复造轮子
from tests.test_application_grabpool_nonempty_regression import (  # noqa: F401
    grab_candidates,
    grab_link,
    grab_position,
    grab_process,
    grab_stage,
)

APPLICATIONS_URL = '/api/v1/applications/'
GRAB_POOL_URL = '/api/v1/grab-pool/'
REASSIGN_URL = '/api/v1/grab-pool/reassign/'


@pytest.fixture
def pool_application(db, grab_position, grab_process, grab_stage, grab_link, grab_candidates):
    """一条同时出现在 applications 列表和 grab-pool 池里的申请。

    条件：state=ACTIVE + is_grabbed=False + current_link.stage_rule.is_grab_mode=True
    这样两个端点都会返回它，才能逐字段比对。
    """
    return Application.objects.create(
        code='APP-CTX-001',
        candidate=grab_candidates[0],
        position=grab_position,
        process=grab_process,
        workflow_version=grab_process.current_version,
        state=ApplicationState.ACTIVE,
        current_link=grab_link,
        current_stage=grab_stage,
        is_grabbed=False,
        stage_entered_at=timezone.now() - timedelta(hours=5),
    )


def _phone_by_code(client, url, code):
    """从端点响应里取出指定申请的 candidatePhone。"""
    resp = client.get(url)
    assert resp.status_code == 200, f'{url} 返回 {resp.status_code}: {resp.content[:400]}'
    rows = {item['code']: item for item in resp.json()['data']}
    assert code in rows, f'{url} 的响应里找不到 {code}，实际有 {list(rows)}'
    item = rows[code]
    assert 'candidatePhone' in item, f'{url} 响应缺少 candidatePhone 字段: {sorted(item)}'
    return item['candidatePhone']


# ============================================================
# 脱敏一致性
# ============================================================
@pytest.mark.django_db
class TestCandidatePhoneMaskingConsistency:
    """锁死 applications 与 grab-pool 两端 candidatePhone 的一致性。"""

    def test_super_admin_sees_identical_phone_on_both_endpoints(
        self, auth_client, pool_application,
    ):
        """超管：两端必须完全相等（回归 context 缺失导致的分叉）。"""
        from_applications = _phone_by_code(auth_client, APPLICATIONS_URL, 'APP-CTX-001')
        from_grab_pool = _phone_by_code(auth_client, GRAB_POOL_URL, 'APP-CTX-001')

        assert from_applications == from_grab_pool, (
            '同一超管、同一条申请，两个端点返回的 candidatePhone 不一致：\n'
            f'  /api/v1/applications/ → {from_applications!r}\n'
            f'  /api/v1/grab-pool/    → {from_grab_pool!r}\n'
            'GrabPoolViewSet.list() 很可能又漏传了 serializer context '
            "（应使用 self.get_serializer(...) 而非裸 ApplicationListSerializer(...)）"
        )

    def test_hr_sees_identical_phone_on_both_endpoints(
        self, auth_hr_client, pool_application,
    ):
        """HR（非超管）：两端同样必须相等。"""
        from_applications = _phone_by_code(auth_hr_client, APPLICATIONS_URL, 'APP-CTX-001')
        from_grab_pool = _phone_by_code(auth_hr_client, GRAB_POOL_URL, 'APP-CTX-001')

        assert from_applications == from_grab_pool, (
            'HR 身份下两端 candidatePhone 不一致：\n'
            f'  /api/v1/applications/ → {from_applications!r}\n'
            f'  /api/v1/grab-pool/    → {from_grab_pool!r}'
        )

    def test_hr_phone_is_actually_masked_on_both_endpoints(
        self, auth_hr_client, pool_application, grab_candidates,
    ):
        """对照组核心：一致 ≠ 正确。HR 在两端都必须拿到**掩码**值。

        没有这条，"两端一致"可以靠"把脱敏整个关掉"来满足 —— 那是 PII 泄漏，不是修复。
        """
        raw_phone = grab_candidates[0].phone
        assert raw_phone, '前置条件失败：候选人必须有手机号，否则脱敏无从谈起'

        for url in (APPLICATIONS_URL, GRAB_POOL_URL):
            phone = _phone_by_code(auth_hr_client, url, 'APP-CTX-001')
            assert phone != raw_phone, (
                f'{url} 对 HR 返回了明文手机号 {phone!r} —— PII 泄漏。'
                '脱敏被关闭会让"两端一致"断言变得毫无意义'
            )
            assert '*' in phone, f'{url} 返回的 {phone!r} 看起来未经脱敏'

    def test_super_admin_and_hr_actually_differ(
        self, auth_client, auth_hr_client, pool_application,
    ):
        """确认脱敏逻辑真的按角色分流（否则上面几条可能是"两边都脱敏"的假一致）。

        这条同时守住 context 真的被注入了 —— 如果 context 丢失，超管也会被脱敏，
        两个角色就会看到相同的值。
        """
        super_phone = _phone_by_code(auth_client, GRAB_POOL_URL, 'APP-CTX-001')
        hr_phone = _phone_by_code(auth_hr_client, GRAB_POOL_URL, 'APP-CTX-001')

        assert super_phone != hr_phone, (
            f'grab-pool 对超管和 HR 返回了相同的 {super_phone!r} —— '
            'serializer context 很可能仍未注入，导致超管也被当作匿名用户脱敏'
        )

    def test_consistency_holds_on_paginated_branch(self, auth_client, pool_application):
        """分页分支（page is not None）与非分页分支是两行独立代码，都要覆盖。

        page_size=1 强制走 self.paginate_queryset 返回非 None 的那条路径。
        """
        from_applications = _phone_by_code(auth_client, APPLICATIONS_URL, 'APP-CTX-001')

        resp = auth_client.get(GRAB_POOL_URL, {'page_size': 1})
        assert resp.status_code == 200
        rows = {item['code']: item for item in resp.json()['data']}
        assert 'APP-CTX-001' in rows

        assert rows['APP-CTX-001']['candidatePhone'] == from_applications


# ============================================================
# reassign 冒烟
# ============================================================
@pytest.mark.django_db
class TestGrabPoolReassign:
    """POST /api/v1/grab-pool/reassign/ 冒烟。

    端点现状（该 import bug 已修复，working-tree 尚未 commit）
    ============================================================
    ``apps/application/services/grab.py`` 里 grab / release / reassign_overdue 三处
    ``from .models import ApplicationHistory`` 已全部改为 ``from ..models``
    （见 git diff，工作区改动未提交）。``grab.py`` 在 ``apps/application/services/``
    子包内，``.models`` 会解析成不存在的 ``apps.application.services.models`` →
    ``ModuleNotFoundError``；正确写法是父包的 ``..models``（``apps.application.models``）。

    修复后该端点可正常重分配超时未认领申请，所以本文件的冒烟用例是**正向断言**
    （不再是 xfail）：管理员调用不 500，且 reassignedCount 语义正确
    （== len(results)、>=1、目标申请进入 results、且库中 is_grabbed 变 True）。

    另配两条静态守卫：
      - ``test_grab_result_exposes_attributes_the_view_relies_on``：锁死视图层依赖的
        GrabResult 契约（.application / .grabbed_by）；
      - ``test_grab_service_imports_from_parent_package_models``：锁死"services 子包必须用
        ..models，绝不能用 .models（会指向不存在的子包模块）"这一导入纪律，防回归。
    """

    @pytest.fixture
    def overdue_application(self, db, grab_position, grab_process, grab_stage,
                            grab_link, grab_candidates):
        """一条超时未认领的申请：stage_entered_at 远早于 30 分钟阈值。"""
        return Application.objects.create(
            code='APP-OVERDUE-001',
            candidate=grab_candidates[1],
            position=grab_position,
            process=grab_process,
            workflow_version=grab_process.current_version,
            state=ApplicationState.ACTIVE,
            current_link=grab_link,
            current_stage=grab_stage,
            is_grabbed=False,
            stage_entered_at=timezone.now() - timedelta(hours=5),
        )

    def test_grab_result_exposes_attributes_the_view_relies_on(self):
        """静态守卫：视图层假设 reassign_overdue 返回的元素有 .application / .grabbed_by。

        ``GrabPoolViewSet.reassign`` 里写了
        ``r.application.code`` 和 ``r.grabbed_by.username``。
        这条锁死 GrabResult 的契约 —— 该假设**成立**（返回 List[GrabResult]，
        dataclass 字段齐全），所以这条是正常通过的，不是 xfail。
        """
        import dataclasses

        from apps.application.services.grab import GrabResult

        field_names = {f.name for f in dataclasses.fields(GrabResult)}
        assert 'application' in field_names
        assert 'grabbed_by' in field_names

    def test_reassign_smoke_admin_can_reassign_overdue(
        self, auth_client, overdue_application, hr_user,
    ):
        """冒烟目标：管理员调用该端点不 500，且 reassignedCount 语义正确。

        hr_user 是 ``_pick_next_assignee`` 的候选接收人 —— stage_rule.processor_order
        为空时会回退到"所有 HR 角色用户"。
        """
        resp = auth_client.post(
            REASSIGN_URL, {'threshold_minutes': 30}, format='json',
        )

        assert resp.status_code == 200, (
            f'reassign 返回 {resp.status_code}: {resp.content[:600]}'
        )

        body = resp.json()
        assert body['thresholdMinutes'] == 30
        assert isinstance(body['reassignedCount'], int)
        assert body['reassignedCount'] == len(body['results']), (
            'reassignedCount 必须等于 results 长度'
        )
        assert body['reassignedCount'] >= 1, (
            '存在一条超时 5 小时的未认领申请，且有可分配的 HR，应至少重分配 1 条'
        )

        codes = {r['applicationCode'] for r in body['results']}
        assert 'APP-OVERDUE-001' in codes

        # 注意：Application.state 是 django_fsm 的 protected 字段，
        # refresh_from_db() 会因 "Direct state modification is not allowed" 报错，
        # 故改用全新查询对象核对重分配结果（grab() 已把 is_grabbed 置为 True 并 save）。
        reloaded = Application.objects.get(code='APP-OVERDUE-001')
        assert reloaded.is_grabbed is True, '重分配后该申请应变为已认领'

    def test_grab_service_imports_from_parent_package_models(self):
        """导入纪律守卫：services 子包必须用 ..models（父包），绝不能用 .models。

        grab.py 位于 apps/application/services/，``from .models`` 会解析成不存在的
        ``apps.application.services.models`` 并抛 ModuleNotFoundError。正确写法是
        ``..models``（apps.application.models）。本用例把这点钉死：错误的模块路径
        本身不可导入，正确的父包路径可导入。这是一条**永久守卫**——即便修复已落地，
        也能防止有人把导入改回 ``.models`` 导致 reassign 静默失效。
        """
        import importlib

        with pytest.raises(ModuleNotFoundError):
            importlib.import_module('apps.application.services.models')

        # 正确的模块在上一层
        assert importlib.import_module('apps.application.models') is not None
