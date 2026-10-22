"""add_candidate 端点 V2 资源码接线回归（G2 补齐）。

背景: b07f99dc 声称把 add_candidate 从 IsHROrAbove 切到 V2Permission + 显式读写码,
但提交进仓库的 views.py 仍是 IsHROrAbove 版(用陈旧副本覆盖), 该模块实际未接入资源码。
本文件锁定接线后的口径, 防止再次退回"只看角色不看资源码"。

关键断言是「POST 但语义为读」的端点: DuplicateCheckView 若不显式给 method 键,
V2Permission 会把 POST 派生为 recruit:candidate:edit, 从而要求编辑码 —— 与语义不符,
只持读取码的专员会被误拒。这里用「只持 list 码也能查重」把它钉住。

与 test_v2_permission_wiring_g2.py 的区别: 那份测的是端点有无声明码(无码即 403),
这里测的是具体码映射是否正确(哪个 HTTP method 对应哪个资源码)。
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models_permission_v2 import RolePermissionV2
from tests.fixtures_common import _attach_role, _create_role_v2

UPLOAD = '/api/v1/candidates/add-candidate/upload-and-parse/'
PARSE_STATUS = '/api/v1/candidates/add-candidate/parse-status/nonexist/'
DUP_CHECK = '/api/v1/candidates/add-candidate/duplicate-check/'
REPLACE_FILE = '/api/v1/candidates/add-candidate/replace-file/nonexist/'
MANUAL_CREATE = '/api/v1/candidates/add-candidate/manual-create/'
BULK_CREATE = '/api/v1/candidates/add-candidate/bulk-create/'
SCORING_START = '/api/v1/candidates/add-candidate/scoring/start/'
PARSER_CONFIG = '/api/v1/candidates/add-candidate/resume-parser-config/'


def _client_for(user) -> APIClient:
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


def _user_with_codes(department, username: str, codes: tuple[str, ...]):
    """造一个「非超管 + 只持指定资源码」的用户。

    必须非超管: is_super_admin 会 bypass 整个 V2Permission, 用超管测等于没测。
    """
    User = get_user_model()
    user = User.objects.create_user(
        username=username, password='Test@1234',
        employee_id=username.upper()[:20], department=department,
    )
    role = _create_role_v2(f'CUST_{username.upper()}'[:64], username)
    _attach_role(user, role)
    RolePermissionV2.objects.bulk_create([
        RolePermissionV2(role_code=role.role_code, resource_code=c, system_code='recruit')
        for c in codes
    ])
    return user


@pytest.mark.django_db
class TestRoleTemplateMappingKeepsHRAbleToCreate:
    """锁死风险守卫: 旧的 IsHROrAbove 允许 SUPER_ADMIN/HRBP/HR 建档。

    切到资源码后能否建档取决于角色回填到哪个模板。HRBP 若被误映射到
    TMPL_DIRECTOR (只读+导出), 全公司 HRBP 会在上传简历时集体 403,
    且前端尚未按资源码隐藏上传按钮 → 表现为"能点但必失败"。
    """

    def test_old_hr_tier_templates_grant_candidate_create(self):
        import importlib.util
        import pathlib

        seed_spec = importlib.util.spec_from_file_location(
            'seed_probe_ac',
            pathlib.Path(__file__).resolve().parents[1]
            / 'apps/core/management/commands/seed_v2_init.py',
        )
        seed = importlib.util.module_from_spec(seed_spec)
        seed_spec.loader.exec_module(seed)
        tpl_codes = {t['code']: set(t['codes']) for t in seed.TEMPLATES}

        from apps.core.management.commands.backfill_role_permissions import (
            ROLE_TEMPLATE_FALLBACK,
        )
        from apps.core.role_v2_query import HR_TIER

        for role in HR_TIER:
            tpl = ROLE_TEMPLATE_FALLBACK.get(role)
            assert tpl, f'{role} 没有模板映射, 回填后将拿不到任何权限码'
            if tpl == 'TMPL_ADMIN':
                continue  # 超管走 is_super_admin bypass
            assert 'recruit:candidate:create' in tpl_codes[tpl], (
                f'{role} → {tpl} 不含 recruit:candidate:create, '
                'HR 将无法上传简历/手动建档'
            )

    def test_read_only_templates_are_not_used_by_hr_tier(self):
        """TMPL_DIRECTOR(只读) 不应被 HR_TIER 命中 —— 双保险。"""
        import importlib.util
        import pathlib

        seed_spec = importlib.util.spec_from_file_location(
            'seed_probe_ac2',
            pathlib.Path(__file__).resolve().parents[1]
            / 'apps/core/management/commands/seed_v2_init.py',
        )
        seed = importlib.util.module_from_spec(seed_spec)
        seed_spec.loader.exec_module(seed)
        director = next(t for t in seed.TEMPLATES if t['code'] == 'TMPL_DIRECTOR')
        assert 'recruit:candidate:create' not in director['codes']

        from apps.core.management.commands.backfill_role_permissions import (
            ROLE_TEMPLATE_FALLBACK,
        )
        from apps.core.role_v2_query import HR_TIER

        for role in HR_TIER:
            assert ROLE_TEMPLATE_FALLBACK.get(role) != 'TMPL_DIRECTOR'


@pytest.mark.django_db
class TestAddCandidateWriteEndpointsRequireCode:
    """建档类写操作: 必须持 recruit:candidate:create, 读取码不足以放行。"""

    def test_upload_denied_for_list_only(self, department):
        u = _user_with_codes(department, 'ac_upload_denied', ('recruit:candidate:list',))
        assert _client_for(u).post(UPLOAD).status_code == 403

    def test_upload_allowed_with_create_code(self, department):
        """过了权限层才会走到入参校验 → 400 NO_FILES, 而不是 403。"""
        u = _user_with_codes(department, 'ac_upload_ok', ('recruit:candidate:create',))
        resp = _client_for(u).post(UPLOAD)
        assert resp.status_code == 400
        assert resp.data['code'] == 'NO_FILES'

    def test_manual_create_denied_for_list_only(self, department):
        u = _user_with_codes(department, 'ac_manual_denied', ('recruit:candidate:list',))
        assert _client_for(u).post(MANUAL_CREATE, {}, format='json').status_code == 403

    def test_bulk_create_denied_for_list_only(self, department):
        u = _user_with_codes(department, 'ac_bulk_denied', ('recruit:candidate:list',))
        assert _client_for(u).post(BULK_CREATE, {}, format='json').status_code == 403

    def test_scoring_start_denied_for_list_only(self, department):
        """评分改写候选人字段, 按 edit 校验, 不能靠读取码启动。"""
        u = _user_with_codes(department, 'ac_score_denied', ('recruit:candidate:list',))
        resp = _client_for(u).post(SCORING_START, {}, format='json')
        assert resp.status_code == 403

    def test_replace_file_denied_for_list_only(self, department):
        u = _user_with_codes(department, 'ac_replace_denied', ('recruit:candidate:list',))
        assert _client_for(u).post(REPLACE_FILE).status_code == 403


@pytest.mark.django_db
class TestAddCandidateReadSemantics:
    """读取语义端点: 只持读取码即可, 且 POST 不应被派生为 :edit。"""

    def test_parse_status_allowed_with_list_code(self, department):
        u = _user_with_codes(department, 'ac_status_ok', ('recruit:candidate:list',))
        resp = _client_for(u).get(PARSE_STATUS)
        # job 不存在 → 404, 证明已通过权限层(403 才说明没通过)
        assert resp.status_code == 404

    def test_duplicate_check_allowed_with_list_code_only(self, department):
        """回归钉子: POST 查重语义为读, 不要求 :edit。

        若去掉 DuplicateCheckView 的 method 键覆盖, V2Permission 会把 POST
        派生为 recruit:candidate:edit, 本例即 403。
        """
        u = _user_with_codes(department, 'ac_dup_ok', ('recruit:candidate:list',))
        resp = _client_for(u).post(
            DUP_CHECK,
            {'draft_id': 'draft_perm_probe', 'phone': '13800000000'},
            format='json',
        )
        assert resp.status_code == 200

    def test_scoring_stream_allowed_with_list_code(self, department):
        u = _user_with_codes(department, 'ac_stream_ok', ('recruit:candidate:list',))
        resp = _client_for(u).get(
            '/api/v1/candidates/add-candidate/scoring/stream/unknown-task/')
        # 未知 task → 404 (owner 校验在应用层), 证明已通过资源码层;
        # 无 list 码时会是 403
        assert resp.status_code == 404


@pytest.mark.django_db
class TestParserConfigIsScopedToSettingsResource:
    """解析引擎配置属「简历解析引擎」资源, 候选人码不得越权读写。"""

    def test_candidate_create_cannot_read_parser_config(self, department):
        u = _user_with_codes(department, 'ac_cfg_cross', ('recruit:candidate:create',))
        assert _client_for(u).get(PARSER_CONFIG).status_code == 403

    def test_resume_parser_engine_menu_code_can_read_config(self, department):
        # 2026-10-21 卡 B5：资源码口径更新 —— core.0030（2026-10-18）把简历解析引擎
        # 从 standard_resume **拆码**为 resume_parser_engine，ResumeParserConfigView 的
        # 守卫也随之改指 resume_parser_engine（apps/add_candidate/views.py:487）。
        # 本用例仍持旧的 standard_resume 码 → 403，属**陈旧测试**（不是权限回归）。
        u = _user_with_codes(
            department, 'ac_cfg_read',
            ('recruit:settings:resume_parser_engine:menu:view',),
        )
        assert _client_for(u).get(PARSER_CONFIG).status_code == 200

    def test_menu_code_cannot_switch_backend(self, department):
        """只读菜单码不能改配置: POST/PUT 必须落到 :edit。"""
        u = _user_with_codes(
            department, 'ac_cfg_write_denied',
            ('recruit:settings:resume_parser_engine:menu:view',),
        )
        resp = _client_for(u).post(PARSER_CONFIG, {'backend': 'career_core'}, format='json')
        assert resp.status_code == 403
