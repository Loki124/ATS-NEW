"""Reason Library test fixtures (T10-T12).

约定:
- 复用根 conftest 的 hr_user / super_user / auth_client 等基础 fixture
- 本文件只补充 reason_library 专用 fixture (system rule / custom rule / tag fixture)
- 所有 test_*.py 用 @pytest.mark.django_db 显式开 DB

⚠️ 重要: migration 0002 会 seed 53 系统标签 + 3 预置规则 (含 4 个 scene assignment)。
这些 seed 数据会与测试场景冲突 (UNIQUE(scene) 等) — 因为测试假定 fresh DB。
pytest session 启动时清掉 seed 数据 (autouse=True, session 范围)。
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.reason_library.models import (
    CategoryAssignment,
    ReasonTag,
    RuleCategory,
    RuleSceneAssignment,
    SceneRule,
    TagType,
)


@pytest.fixture(scope='session', autouse=True)
def _clear_seed_before_tests(django_db_setup, django_db_blocker):
    """session 启动: 在 DB 已 migrate 完成后, 清掉 0002 seed 数据。
    让 pytest 用 fresh DB (假定测试场景独占 scene 等)。
    """
    with django_db_blocker.unblock():
        from django.db import transaction
        # 删除 seed 灌入的数据 (按业务标识)
        with transaction.atomic():
            # 删除 RuleSceneAssignment (最优先: UNIQUE(scene))
            RuleSceneAssignment.objects.all().delete()
            # 删除 category_assignment + rule_category (依赖顺序)
            CategoryAssignment.objects.all().delete()
            RuleCategory.objects.all().delete()
            # 删除系统预置规则 (CASCADE 删 categories/assignments/scenes)
            SceneRule.objects.filter(is_system=True).delete()
            # 删除系统预置标签
            ReasonTag.objects.filter(type=TagType.SYSTEM.value, deleted_at__isnull=True).delete()


@pytest.fixture
def reason_tag(db):
    """一个普通 custom 标签 - 默认启用、未软删。"""
    return ReasonTag.objects.create(
        name='test-tag-001',
        en_name='Test Tag 001',
        tip='for test',
        type=TagType.CUSTOM.value,
        enabled=True,
    )


@pytest.fixture
def system_tag(db):
    """一个系统预置标签。"""
    return ReasonTag.objects.create(
        name='test-system-tag-001',
        en_name='Test System Tag 001',
        tip='',
        type=TagType.SYSTEM.value,
        enabled=True,
    )


@pytest.fixture
def custom_rule(db):
    """一个 custom 规则 (is_system=False) - 无 categories/assignments。"""
    rule = SceneRule.objects.create(
        name='Test Custom Rule',
        is_system=False,
        enabled=True,
        description='for test',
    )
    return rule


@pytest.fixture
def system_rule(db):
    """一个 system 预置规则 (is_system=True) - 无 categories/assignments。"""
    return SceneRule.objects.create(
        name='Test System Rule',
        is_system=True,
        enabled=True,
        description='system preset',
    )


@pytest.fixture
def auth_api_client(db):
    """已登录普通用户的 APIClient. 不带任何角色 (无超管/HR)."""
    from django.contrib.auth import get_user_model
    user = get_user_model().objects.create_user(
        username='reason_lb_user', password='Test@1234',
    )
    client = APIClient()
    client.force_authenticate(user)
    return client, user


@pytest.fixture
def admin_api_client(db):
    """HR 用户的 APIClient. (走 IsAdminOrReadOnly 放行路径)。"""
    # 直接走 is_super_admin 旁路 — 因为是单测, 不依赖 V2 role 系统完整 setup
    from django.contrib.auth import get_user_model
    user = get_user_model().objects.create_user(
        username='reason_lb_admin', password='Test@1234',
    )
    user.is_staff = True
    user.is_superuser = True  # 让 is_super_admin() 返 True, 绕过 IsAdminOrReadOnly
    user.save()
    client = APIClient()
    client.force_authenticate(user)
    return client, user


@pytest.fixture
def hr_api_client(db):
    """HR (但非超管) 用户的 APIClient. 通过 is_hr_or_above 走 is_admin。"""
    from django.contrib.auth import get_user_model
    user = get_user_model().objects.create_user(
        username='reason_lb_hr', password='Test@1234',
    )
    user.is_staff = True
    user.is_superuser = False
    user.save()
    client = APIClient()
    client.force_authenticate(user)
    return client, user


@pytest.fixture
def seeded_data(db):
    """灌入 53 系统标签 + 3 预置规则 — 调用真实 seed_initial_data()."""
    from apps.reason_library.seed_data import seed_initial_data
    result = seed_initial_data(verbose=False)
    return result
