"""动作/预设包管理接口护栏测试（权限 v2 B7，决策④审计）。

覆盖：
- 自定义动作强制 custom_ 前缀（系统 key 空间保护）；
- 系统动作：不可删、key/category/destructive 不可改（key 是代码契约）；
- 被 WRITE 规则引用的动作不可删；
- 预设包 actionKeys 必须指向已启用动作；
- 全部变更写审计（AuditLog 落库，决策④）；
- 非超管 403。
"""
from django.test import TestCase

from apps.audit.models import AuditLog
from apps.core.models import User
from apps.core.models_permission_v2 import RoleV2, UserRoleV2
from apps.data_permission.action_registry import invalidate_cache
from apps.data_permission.models import (
    DataPermissionAction,
    DataPermissionRule,
    RowScopeAccess,
    RowScopeType,
)


class ActionManageApiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create(username='dp_admin', is_superuser=True)
        cls.plain = User.objects.create(username='dp_plain')
        RoleV2.objects.create(system_code='recruit', role_code='DP_R', role_name='r', status=1)
        UserRoleV2.objects.create(user_id=cls.plain.pk, role_code='DP_R', system_code='recruit')

    def setUp(self):
        invalidate_cache()
        self.client = self.client_class()

    def _call(self, method, path, body=None, user=None):
        import json
        data = json.dumps(body).encode() if body is not None else None
        return getattr(self.client, method)(
            path, data=data, content_type='application/json',
            HTTP_AUTHORIZATION=self._token(user or self.admin),
        )

    @staticmethod
    def _token(user):
        from rest_framework_simplejwt.tokens import RefreshToken
        return 'Bearer ' + str(RefreshToken.for_user(user).access_token)

    # --- 创建护栏 ---

    def test_create_requires_custom_prefix(self):
        r = self._call('post', '/api/v1/data-permissions/actions/',
                       {'key': 'evil_key', 'label': 'x'})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(DataPermissionAction.objects.filter(pk='evil_key').exists())

    def test_create_custom_action_ok_and_audited(self):
        r = self._call('post', '/api/v1/data-permissions/actions/',
                       {'key': 'custom_mark_star', 'label': '标星'})
        self.assertEqual(r.status_code, 201)
        self.assertTrue(DataPermissionAction.objects.filter(pk='custom_mark_star').exists())
        self.assertTrue(AuditLog.objects.filter(
            entity='dp_action', entity_id='custom_mark_star', action='CREATE').exists())

    # --- 系统动作护栏 ---

    def test_system_action_cannot_be_deleted(self):
        r = self._call('delete', '/api/v1/data-permissions/actions/edit/')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(DataPermissionAction.objects.filter(pk='edit').exists())

    def test_system_action_cannot_change_locked_fields(self):
        r = self._call('patch', '/api/v1/data-permissions/actions/edit/', {'key': 'hacked'})
        self.assertEqual(r.status_code, 400)
        r = self._call('patch', '/api/v1/data-permissions/actions/edit/', {'label': '编辑改'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(DataPermissionAction.objects.get(pk='edit').label, '编辑改')

    def test_referenced_action_cannot_be_deleted(self):
        DataPermissionAction.objects.create(
            key='custom_x', label='x', category='write', is_system=False)
        DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value='DP_R', level='ROW',
            row_access=RowScopeAccess.WRITE, entity='candidate',
            scope_type=RowScopeType.ALL, actions=['custom_x'], status=1)
        r = self._call('delete', '/api/v1/data-permissions/actions/custom_x/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('引用', r.json()['message'])

    # --- 预设包护栏 ---

    def test_preset_action_keys_must_be_enabled(self):
        r = self._call('post', '/api/v1/data-permissions/action-presets/',
                       {'key': 'custom_preset', 'label': 'p', 'actionKeys': ['no_such']})
        self.assertEqual(r.status_code, 400)

    def test_preset_create_ok(self):
        r = self._call('post', '/api/v1/data-permissions/action-presets/',
                       {'key': 'custom_preset', 'label': 'p', 'actionKeys': ['view', 'edit']})
        self.assertEqual(r.status_code, 201)
        self.assertTrue(AuditLog.objects.filter(entity='dp_action_preset', action='CREATE').exists())

    # --- 权限 ---

    def test_non_superadmin_forbidden(self):
        r = self._call('get', '/api/v1/data-permissions/actions/', user=self.plain)
        self.assertEqual(r.status_code, 403)

    # --- options 下发字典 ---

    def test_options_contains_action_registry(self):
        r = self._call('get', '/api/v1/roles/1/data-permissions/options/')
        self.assertEqual(r.status_code, 200)
        body = r.json()
        keys = {a['key'] for a in body['data']['actionRegistry']}
        self.assertTrue({'recommend', 'eliminate', 'talent_pool_add', 'notify'} <= keys)
        # presetPackages 为数组形态（key 作值不被 camelCase 转换，契约稳定）
        preset_keys = {p['key'] for p in body['data']['presetPackages']}
        self.assertIn('owner_restricted', preset_keys)
