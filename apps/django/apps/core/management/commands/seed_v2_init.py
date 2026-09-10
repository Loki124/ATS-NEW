"""Seed V2 权限基础数据. Idempotent — 重复跑 update_or_create.
T15: 60 resources + 4 templates + 1 tenant config.
"""
from django.core.management.base import BaseCommand
from django.db import transaction


SYSTEM = 'recruit'


RESOURCES = [
    # --- module: candidate ---
    ('recruit:candidate:menu:view', '候选人菜单', 'MENU', 'candidate'),
    ('recruit:candidate:list', '候选人列表', 'BUTTON', 'candidate'),
    ('recruit:candidate:create', '新增候选人', 'BUTTON', 'candidate'),
    ('recruit:candidate:edit', '编辑候选人', 'BUTTON', 'candidate'),
    ('recruit:candidate:export', '导出候选人', 'BUTTON', 'candidate'),
    ('recruit:candidate:delete', '删除候选人', 'BUTTON', 'candidate'),
    # --- module: offer ---
    ('recruit:offer:menu:view', 'Offer菜单', 'MENU', 'offer'),
    ('recruit:offer:list', 'Offer列表', 'BUTTON', 'offer'),
    ('recruit:offer:create', '发起Offer', 'BUTTON', 'offer'),
    ('recruit:offer:edit', '编辑Offer', 'BUTTON', 'offer'),
    ('recruit:offer:approve', '审批Offer', 'BUTTON', 'offer'),
    ('recruit:offer:approve_l1', '一级审批', 'BUTTON', 'offer'),
    ('recruit:offer:approve_l2', '二级审批', 'BUTTON', 'offer'),
    # --- module: interview ---
    ('recruit:interview:menu:view', '面试菜单', 'MENU', 'interview'),
    ('recruit:interview:list', '面试列表', 'BUTTON', 'interview'),
    ('recruit:interview:schedule', '安排面试', 'BUTTON', 'interview'),
    ('recruit:interview:feedback', '提交反馈', 'BUTTON', 'interview'),
    ('recruit:interview:export', '导出面试', 'BUTTON', 'interview'),
    # --- module: demand ---
    ('recruit:demand:menu:view', '需求菜单', 'MENU', 'demand'),
    ('recruit:demand:list', '需求列表', 'BUTTON', 'demand'),
    ('recruit:demand:create', '创建需求', 'BUTTON', 'demand'),
    ('recruit:demand:edit', '编辑需求', 'BUTTON', 'demand'),
    ('recruit:demand:approve', '审批需求', 'BUTTON', 'demand'),
    # --- module: position ---
    ('recruit:position:menu:view', '岗位菜单', 'MENU', 'position'),
    ('recruit:position:list', '岗位列表', 'BUTTON', 'position'),
    ('recruit:position:create', '创建岗位', 'BUTTON', 'position'),
    ('recruit:position:edit', '编辑岗位', 'BUTTON', 'position'),
    ('recruit:position:publish', '发布岗位', 'BUTTON', 'position'),
    ('recruit:position:close', '关闭岗位', 'BUTTON', 'position'),
    # --- module: application ---
    ('recruit:application:menu:view', '申请菜单', 'MENU', 'application'),
    ('recruit:application:list', '申请列表', 'BUTTON', 'application'),
    ('recruit:application:create', '创建申请', 'BUTTON', 'application'),
    ('recruit:application:edit', '编辑申请', 'BUTTON', 'application'),
    ('recruit:application:advance', '推进流程', 'BUTTON', 'application'),
    ('recruit:application:reject', '拒绝申请', 'BUTTON', 'application'),
    # --- module: onboarding ---
    ('recruit:onboarding:menu:view', '入职菜单', 'MENU', 'onboarding'),
    ('recruit:onboarding:list', '入职列表', 'BUTTON', 'onboarding'),
    ('recruit:onboarding:create', '创建入职', 'BUTTON', 'onboarding'),
    ('recruit:onboarding:edit', '编辑入职', 'BUTTON', 'onboarding'),
    # --- module: referral ---
    ('recruit:referral:menu:view', '内推菜单', 'MENU', 'referral'),
    ('recruit:referral:list', '内推列表', 'BUTTON', 'referral'),
    ('recruit:referral:create', '发起内推', 'BUTTON', 'referral'),
    ('recruit:referral:approve', '审批内推', 'BUTTON', 'referral'),
    # --- module: invitation ---
    ('recruit:invitation:menu:view', '邀约菜单', 'MENU', 'invitation'),
    ('recruit:invitation:list', '邀约列表', 'BUTTON', 'invitation'),
    ('recruit:invitation:create', '发起邀约', 'BUTTON', 'invitation'),
    # --- module: talent_pool ---
    ('recruit:talent_pool:menu:view', '人才库菜单', 'MENU', 'talent_pool'),
    ('recruit:talent_pool:list', '人才库列表', 'BUTTON', 'talent_pool'),
    ('recruit:talent_pool:create', '入库', 'BUTTON', 'talent_pool'),
    ('recruit:talent_pool:export', '导出人才库', 'BUTTON', 'talent_pool'),
    # --- module: mou ---
    ('recruit:mou:menu:view', 'MOU菜单', 'MENU', 'mou'),
    ('recruit:mou:list', 'MOU列表', 'BUTTON', 'mou'),
    ('recruit:mou:create', '创建MOU', 'BUTTON', 'mou'),
    ('recruit:mou:edit', '编辑MOU', 'BUTTON', 'mou'),
    ('recruit:mou:approve', '审批MOU', 'BUTTON', 'mou'),
    # --- module: role ---
    ('recruit:role:menu:view', '角色菜单', 'MENU', 'role'),
    ('recruit:role:list', '角色列表', 'BUTTON', 'role'),
    ('recruit:role:create', '创建角色', 'BUTTON', 'role'),
    ('recruit:role:edit', '编辑角色', 'BUTTON', 'role'),
    ('recruit:role:delete', '删除角色', 'BUTTON', 'role'),
    ('recruit:role:assign', '分配角色', 'BUTTON', 'role'),
    # --- module: user_role ---
    ('recruit:user_role:menu:view', '用户授权菜单', 'MENU', 'user_role'),
    ('recruit:user_role:list', '用户授权列表', 'BUTTON', 'user_role'),
    ('recruit:user_role:create', '新增授权', 'BUTTON', 'user_role'),
    ('recruit:user_role:edit', '编辑授权', 'BUTTON', 'user_role'),
    ('recruit:user_role:delete', '撤销授权', 'BUTTON', 'user_role'),
    # --- module: mgmt_unit ---
    ('recruit:mgmt_unit:menu:view', '管理单元菜单', 'MENU', 'mgmt_unit'),
    ('recruit:mgmt_unit:list', '管理单元列表', 'BUTTON', 'mgmt_unit'),
    ('recruit:mgmt_unit:create', '新增管理单元', 'BUTTON', 'mgmt_unit'),
    ('recruit:mgmt_unit:edit', '编辑管理单元', 'BUTTON', 'mgmt_unit'),
]


TEMPLATES = [
    {
        'code': 'TMPL_ADMIN',
        'name': '超级管理员',
        'codes': [],
    },
    {
        'code': 'TMPL_DIRECTOR',
        'name': '招聘总经理',
        'codes': [
            'recruit:candidate:menu:view', 'recruit:candidate:list',
            'recruit:candidate:export',
            'recruit:offer:menu:view', 'recruit:offer:list',
            'recruit:offer:approve', 'recruit:offer:approve_l1', 'recruit:offer:approve_l2',
            'recruit:interview:menu:view', 'recruit:interview:list',
            'recruit:demand:menu:view', 'recruit:demand:list',
            'recruit:demand:create', 'recruit:demand:approve',
            'recruit:position:menu:view', 'recruit:position:list',
            'recruit:position:create', 'recruit:position:publish',
            'recruit:application:menu:view', 'recruit:application:list',
            'recruit:application:advance',
            'recruit:referral:menu:view', 'recruit:referral:list',
            'recruit:talent_pool:menu:view', 'recruit:talent_pool:list',
            'recruit:mou:menu:view', 'recruit:mou:list',
            'recruit:role:menu:view', 'recruit:role:list',
            'recruit:user_role:menu:view', 'recruit:user_role:list',
            'recruit:mgmt_unit:menu:view', 'recruit:mgmt_unit:list',
        ],
    },
    {
        'code': 'TMPL_SPECIALIST',
        'name': '招聘专员',
        'codes': [
            'recruit:candidate:menu:view', 'recruit:candidate:list',
            'recruit:candidate:create', 'recruit:candidate:edit',
            'recruit:offer:menu:view', 'recruit:offer:list',
            'recruit:offer:create',
            'recruit:interview:menu:view', 'recruit:interview:list',
            'recruit:interview:schedule',
            'recruit:demand:menu:view', 'recruit:demand:list',
            'recruit:position:menu:view', 'recruit:position:list',
            'recruit:application:menu:view', 'recruit:application:list',
            'recruit:invitation:menu:view', 'recruit:invitation:list',
            'recruit:invitation:create',
            'recruit:talent_pool:menu:view', 'recruit:talent_pool:list',
        ],
    },
    {
        'code': 'TMPL_INTERVIEWER',
        'name': '面试官',
        'codes': [
            'recruit:candidate:menu:view', 'recruit:candidate:list',
            'recruit:interview:menu:view', 'recruit:interview:list',
            'recruit:interview:feedback',
            'recruit:application:menu:view', 'recruit:application:list',
        ],
    },
]


TENANT_DEFAULTS = [
    ('GLOBAL_DEFAULT_DATA_SCOPE', 'SELF', '全局默认数据范围: 仅本人'),
]


class Command(BaseCommand):
    help = 'Seed V2 权限基础数据 (resources + templates + tenant config). Idempotent.'

    @transaction.atomic
    def handle(self, *args, **opts):
        from apps.core.models_permission_v2 import (
            PermissionResource, PermissionTemplate, TenantConfig,
        )

        created_resources = updated_resources = 0

        for code, name, rtype, module in RESOURCES:
            obj, created = PermissionResource.objects.update_or_create(
                resource_code=code,
                defaults={
                    'system_code': SYSTEM,
                    'resource_name': name,
                    'resource_type': rtype,
                    'module': module,
                    'status': 1,
                },
            )
            if created:
                created_resources += 1
            else:
                updated_resources += 1

        for tpl in TEMPLATES:
            PermissionTemplate.objects.update_or_create(
                template_code=tpl['code'],
                defaults={
                    'system_code': SYSTEM,
                    'template_name': tpl['name'],
                    'is_system': 1,
                    'status': 1,
                    'permission_codes': tpl['codes'],
                },
            )

        all_codes = list(PermissionResource.objects.filter(
            system_code=SYSTEM, status=1,
        ).values_list('resource_code', flat=True))
        PermissionTemplate.objects.filter(
            template_code='TMPL_ADMIN', system_code=SYSTEM,
        ).update(permission_codes=all_codes)

        for key, val, desc in TENANT_DEFAULTS:
            TenantConfig.objects.update_or_create(
                config_key=key, system_code=SYSTEM,
                defaults={'config_value': val, 'description': desc},
            )

        admin_created = self.init_admin_user()

        total = len(RESOURCES)
        self.stdout.write(self.style.SUCCESS(
            f'Seed OK: {created_resources} created, {updated_resources} updated, '
            f'{total} total resources, {len(all_codes)} in TMPL_ADMIN, '
            f'{len(TEMPLATES)} templates, {len(TENANT_DEFAULTS)} tenant config, '
            f'admin {"created" if admin_created else "updated"}'
        ))

    def init_admin_user(self):
        """创建/更新 admin 超级管理员并绑定 SUPER_ADMIN 角色."""
        from apps.core.models import User
        from apps.core.models_permission_v2 import (
            ManagementUnit, PermissionTemplate, RoleV2, UserRoleV2,
        )

        admin, created = User.objects.update_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'first_name': '系统',
                'last_name': '管理员',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True,
            },
        )
        admin.set_password('admin123')
        admin.save()

        # 确保 TMPL_ADMIN 模板存在（正常 seed_v2_init 已创建）
        tmpl_admin = PermissionTemplate.objects.filter(
            system_code=SYSTEM, template_code='TMPL_ADMIN', status=1,
        ).first()
        if not tmpl_admin:
            self.stdout.write(self.style.WARNING(
                'TMPL_ADMIN 模板不存在, 跳过 SUPER_ADMIN 角色创建'))
            return created

        # 创建/更新 SUPER_ADMIN 角色
        RoleV2.objects.update_or_create(
            system_code=SYSTEM, role_code='SUPER_ADMIN',
            defaults={
                'role_name': '超级管理员',
                'template_code': 'TMPL_ADMIN',
                'description': '系统所有权限',
                'is_system': 1,
                'status': 1,
            },
        )

        # 创建 ROOT_MGMT 管理单元
        root_mgmt, _ = ManagementUnit.objects.update_or_create(
            system_code=SYSTEM, unit_name='全公司',
            defaults={
                'unit_type': 'org',
                'org_scope': {'level': 'ROOT', 'name': '全公司'},
                'include_children': 1,
                'status': 1,
            },
        )

        # 绑定 admin -> SUPER_ADMIN
        UserRoleV2.objects.update_or_create(
            user_id=admin.id, role_code='SUPER_ADMIN', system_code=SYSTEM,
            defaults={
                'management_unit_ids': [root_mgmt.id],
                'granted_by_id': admin.id,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ admin 初始化完成（{"新建" if created else "已存在, 重置密码"}）'
                ' → SUPER_ADMIN / admin123'
            )
        )
        return created