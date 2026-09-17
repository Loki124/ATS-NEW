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
    # --- module: settings ---
    # 用户管理 (用户集中入口: 内部员工/外部用户/全部用户; 注册审核/用户组迁入)
    # 顶层菜单 + 三个子菜单
    ('recruit:settings:users:menu:view', '用户管理菜单', 'MENU', 'settings'),
    ('recruit:settings:users:internal:menu:view', '内部员工菜单', 'MENU', 'settings'),
    ('recruit:settings:users:external:menu:view', '外部用户菜单', 'MENU', 'settings'),
    ('recruit:settings:users:all:menu:view', '全部用户菜单', 'MENU', 'settings'),
    # 操作按钮 (共享粒度: 内部/外部/全部统一授权)
    ('recruit:settings:users:list', '用户列表', 'BUTTON', 'settings'),
    ('recruit:settings:users:create', '新增用户', 'BUTTON', 'settings'),
    ('recruit:settings:users:edit', '编辑用户', 'BUTTON', 'settings'),
    ('recruit:settings:users:delete', '删除用户', 'BUTTON', 'settings'),
    ('recruit:settings:users:export', '导出用户', 'BUTTON', 'settings'),
    # 按用户类型独立授权 (必要时做更细粒度控制)
    ('recruit:settings:users:internal:list', '内部员工列表', 'BUTTON', 'settings'),
    ('recruit:settings:users:external:list', '外部用户列表', 'BUTTON', 'settings'),
    ('recruit:settings:users:all:list', '全部用户列表', 'BUTTON', 'settings'),
    # 个人信息管理 (config)
    ('recruit:settings:account:menu:view', '个人信息管理菜单', 'MENU', 'settings'),
    ('recruit:settings:account:edit', '编辑个人信息', 'BUTTON', 'settings'),
    # 公司信息 (config)
    ('recruit:settings:company:menu:view', '公司信息菜单', 'MENU', 'settings'),
    ('recruit:settings:company:edit', '编辑公司信息', 'BUTTON', 'settings'),
    # 公司地址 (占位)
    ('recruit:settings:company-address:menu:view', '公司地址菜单', 'MENU', 'settings'),
    # 公司会议室 (占位)
    ('recruit:settings:company-meeting-rooms:menu:view', '公司会议室菜单', 'MENU', 'settings'),
    # 接收简历邮箱 (占位)
    ('recruit:settings:company-resume-mailbox:menu:view', '接收简历邮箱菜单', 'MENU', 'settings'),
    # 品牌信息管理 (config)
    ('recruit:settings:company-brand:menu:view', '品牌信息管理菜单', 'MENU', 'settings'),
    ('recruit:settings:company-brand:edit', '编辑品牌信息', 'BUTTON', 'settings'),
    # 组织职责管理 (management)
    ('recruit:settings:department:menu:view', '组织职责管理菜单', 'MENU', 'settings'),
    ('recruit:settings:department:create', '新增组织职责', 'BUTTON', 'settings'),
    ('recruit:settings:department:edit', '编辑组织职责', 'BUTTON', 'settings'),
    ('recruit:settings:department:delete', '删除组织职责', 'BUTTON', 'settings'),
    ('recruit:settings:department:export', '导出组织职责', 'BUTTON', 'settings'),
    # 权限管理 (分组顶层: 角色管理/管理单元/字段权限)
    ('recruit:settings:permission:menu:view', '权限管理菜单', 'MENU', 'settings'),
    # 角色管理 (management)
    ('recruit:settings:permissions:menu:view', '角色管理菜单', 'MENU', 'settings'),
    ('recruit:settings:permissions:create', '新增角色', 'BUTTON', 'settings'),
    ('recruit:settings:permissions:edit', '编辑角色', 'BUTTON', 'settings'),
    ('recruit:settings:permissions:delete', '删除角色', 'BUTTON', 'settings'),
    ('recruit:settings:permissions:export', '导出角色', 'BUTTON', 'settings'),
    # 字段权限 (management) —— field_acl 引擎 (序列化层真实生效的 PII 脱敏), 单一字段权限入口
    ('recruit:settings:field-acl:menu:view', '字段权限菜单', 'MENU', 'settings'),
    ('recruit:settings:field-acl:create', '新增字段权限', 'BUTTON', 'settings'),
    ('recruit:settings:field-acl:edit', '编辑字段权限', 'BUTTON', 'settings'),
    ('recruit:settings:field-acl:delete', '删除字段权限', 'BUTTON', 'settings'),
    ('recruit:settings:field-acl:export', '导出字段权限', 'BUTTON', 'settings'),
    # 注册审核 (config/审核)
    ('recruit:settings:registrations:menu:view', '注册审核菜单', 'MENU', 'settings'),
    ('recruit:settings:registrations:approve', '审核注册', 'BUTTON', 'settings'),
    # 用户组 (迁移到「用户管理」下, 标记占位)
    ('recruit:settings:user-groups:menu:view', '用户组管理菜单', 'MENU', 'settings'),
    # 标准简历设置 (config)
    ('recruit:settings:standard-resume:menu:view', '标准简历设置菜单', 'MENU', 'settings'),
    ('recruit:settings:standard-resume:edit', '编辑标准简历', 'BUTTON', 'settings'),
    # 申请表和登记表设置 (config)
    ('recruit:settings:application-form:menu:view', '申请表和登记表设置菜单', 'MENU', 'settings'),
    ('recruit:settings:application-form:edit', '编辑申请表设置', 'BUTTON', 'settings'),
    # 候选人信息表 (config)
    ('recruit:settings:candidate-info-table:menu:view', '候选人信息表菜单', 'MENU', 'settings'),
    ('recruit:settings:candidate-info-table:edit', '编辑候选人信息表', 'BUTTON', 'settings'),
    # 简历查重规则 (management)
    ('recruit:settings:duplicate-candidate:menu:view', '简历查重规则菜单', 'MENU', 'settings'),
    ('recruit:settings:duplicate-candidate:create', '新增查重规则', 'BUTTON', 'settings'),
    ('recruit:settings:duplicate-candidate:edit', '编辑查重规则', 'BUTTON', 'settings'),
    ('recruit:settings:duplicate-candidate:delete', '删除查重规则', 'BUTTON', 'settings'),
    ('recruit:settings:duplicate-candidate:export', '导出查重规则', 'BUTTON', 'settings'),
    # 候选人字段管理 (management)
    ('recruit:settings:candidate-dynamic-fields:menu:view', '候选人字段管理菜单', 'MENU', 'settings'),
    ('recruit:settings:candidate-dynamic-fields:create', '新增候选人字段', 'BUTTON', 'settings'),
    ('recruit:settings:candidate-dynamic-fields:edit', '编辑候选人字段', 'BUTTON', 'settings'),
    ('recruit:settings:candidate-dynamic-fields:delete', '删除候选人字段', 'BUTTON', 'settings'),
    ('recruit:settings:candidate-dynamic-fields:export', '导出候选人字段', 'BUTTON', 'settings'),
    # 需求规则设置 (config)
    ('recruit:settings:demand-config:menu:view', '需求规则设置菜单', 'MENU', 'settings'),
    ('recruit:settings:demand-config:edit', '编辑需求规则', 'BUTTON', 'settings'),
    # 评分规则 (占位: 页面仅 n-empty "功能开发中")
    ('recruit:settings:scoring:menu:view', '评分规则菜单', 'MENU', 'settings'),
    # 需求字段管理 (management)
    ('recruit:settings:demand-dynamic-fields:menu:view', '需求字段管理菜单', 'MENU', 'settings'),
    ('recruit:settings:demand-dynamic-fields:create', '新增需求字段', 'BUTTON', 'settings'),
    ('recruit:settings:demand-dynamic-fields:edit', '编辑需求字段', 'BUTTON', 'settings'),
    ('recruit:settings:demand-dynamic-fields:delete', '删除需求字段', 'BUTTON', 'settings'),
    ('recruit:settings:demand-dynamic-fields:export', '导出需求字段', 'BUTTON', 'settings'),
    # 职位信息管理 (占位)
    ('recruit:settings:position-info:menu:view', '职位信息管理菜单', 'MENU', 'settings'),
    # 职位字段管理 (无路由, 占位)
    ('recruit:settings:position-dynamic-fields:menu:view', '职位字段管理菜单', 'MENU', 'settings'),
    # 面试管理 (占位)
    ('recruit:settings:interview-management:menu:view', '面试管理菜单', 'MENU', 'settings'),
    # Offer管理 (占位)
    ('recruit:settings:offer-management:menu:view', 'Offer管理菜单', 'MENU', 'settings'),
    # 校招管控 (config)
    ('recruit:settings:campus-control:menu:view', '校招管控菜单', 'MENU', 'settings'),
    ('recruit:settings:campus-control:edit', '编辑校招管控', 'BUTTON', 'settings'),
    # 数据字典 (management)
    ('recruit:settings:dictionary:menu:view', '数据字典菜单', 'MENU', 'settings'),
    ('recruit:settings:dictionary:create', '新增字典项', 'BUTTON', 'settings'),
    ('recruit:settings:dictionary:edit', '编辑字典项', 'BUTTON', 'settings'),
    ('recruit:settings:dictionary:delete', '删除字典项', 'BUTTON', 'settings'),
    ('recruit:settings:dictionary:export', '导出字典项', 'BUTTON', 'settings'),
    # 招聘阶段配置 (config)
    ('recruit:settings:recruitment-stage:menu:view', '招聘阶段配置菜单', 'MENU', 'settings'),
    ('recruit:settings:recruitment-stage:edit', '编辑招聘阶段', 'BUTTON', 'settings'),
    # 招聘流程 (config)
    ('recruit:settings:recruitment-process:menu:view', '招聘流程菜单', 'MENU', 'settings'),
    ('recruit:settings:recruitment-process:edit', '编辑招聘流程', 'BUTTON', 'settings'),
    # 面试轮次 (config)
    ('recruit:settings:recruitment-round:menu:view', '面试轮次菜单', 'MENU', 'settings'),
    ('recruit:settings:recruitment-round:edit', '编辑面试轮次', 'BUTTON', 'settings'),
    # 制度公告 (config)
    ('recruit:settings:announcements:menu:view', '制度公告菜单', 'MENU', 'settings'),
    ('recruit:settings:announcements:edit', '编辑制度公告', 'BUTTON', 'settings'),
    # 主题外观 (config)
    ('recruit:settings:theme:menu:view', '主题外观菜单', 'MENU', 'settings'),
    ('recruit:settings:theme:edit', '编辑主题外观', 'BUTTON', 'settings'),
    # 公司库 (management)
    ('recruit:settings:company-library:menu:view', '公司库菜单', 'MENU', 'settings'),
    ('recruit:settings:company-library:create', '新增公司', 'BUTTON', 'settings'),
    ('recruit:settings:company-library:edit', '编辑公司', 'BUTTON', 'settings'),
    ('recruit:settings:company-library:delete', '删除公司', 'BUTTON', 'settings'),
    ('recruit:settings:company-library:export', '导出公司', 'BUTTON', 'settings'),
    # 院校库 (management)
    ('recruit:settings:school-library:menu:view', '院校库菜单', 'MENU', 'settings'),
    ('recruit:settings:school-library:create', '新增院校', 'BUTTON', 'settings'),
    ('recruit:settings:school-library:edit', '编辑院校', 'BUTTON', 'settings'),
    ('recruit:settings:school-library:delete', '删除院校', 'BUTTON', 'settings'),
    ('recruit:settings:school-library:export', '导出院校', 'BUTTON', 'settings'),
    # 动态字段 (management)
    ('recruit:settings:dynamic-fields:menu:view', '动态字段菜单', 'MENU', 'settings'),
    ('recruit:settings:dynamic-fields:create', '新增字段', 'BUTTON', 'settings'),
    ('recruit:settings:dynamic-fields:edit', '编辑字段', 'BUTTON', 'settings'),
    ('recruit:settings:dynamic-fields:delete', '删除字段', 'BUTTON', 'settings'),
    ('recruit:settings:dynamic-fields:export', '导出字段', 'BUTTON', 'settings'),
    # 我找的简历 (management)
    ('recruit:settings:scraped-resumes:menu:view', '我找的简历菜单', 'MENU', 'settings'),
    ('recruit:settings:scraped-resumes:create', '新增简历', 'BUTTON', 'settings'),
    ('recruit:settings:scraped-resumes:edit', '编辑简历', 'BUTTON', 'settings'),
    ('recruit:settings:scraped-resumes:delete', '删除简历', 'BUTTON', 'settings'),
    ('recruit:settings:scraped-resumes:export', '导出简历', 'BUTTON', 'settings'),
    # 数据中心 (management)
    ('recruit:settings:data-dashboard:menu:view', '数据中心菜单', 'MENU', 'settings'),
    ('recruit:settings:data-dashboard:create', '新增数据订阅', 'BUTTON', 'settings'),
    ('recruit:settings:data-dashboard:edit', '编辑数据订阅', 'BUTTON', 'settings'),
    ('recruit:settings:data-dashboard:delete', '删除数据订阅', 'BUTTON', 'settings'),
    ('recruit:settings:data-dashboard:export', '导出数据', 'BUTTON', 'settings'),
    # 生态对接 (management)
    ('recruit:settings:external:menu:view', '生态对接菜单', 'MENU', 'settings'),
    ('recruit:settings:external:create', '新增生态对接', 'BUTTON', 'settings'),
    ('recruit:settings:external:edit', '编辑生态对接', 'BUTTON', 'settings'),
    ('recruit:settings:external:delete', '删除生态对接', 'BUTTON', 'settings'),
    ('recruit:settings:external:export', '导出生态对接', 'BUTTON', 'settings'),
    # 公共设置 (占位)
    ('recruit:settings:public:menu:view', '公共设置菜单', 'MENU', 'settings'),
    # 统一规则引擎 (config)
    ('recruit:settings:rule-engine:menu:view', '统一规则引擎菜单', 'MENU', 'settings'),
    ('recruit:settings:rule-engine:edit', '编辑规则引擎', 'BUTTON', 'settings'),
    # 码表库 (management)
    ('recruit:settings:code-tables:menu:view', '码表库菜单', 'MENU', 'settings'),
    ('recruit:settings:code-tables:create', '新增码表', 'BUTTON', 'settings'),
    ('recruit:settings:code-tables:edit', '编辑码表', 'BUTTON', 'settings'),
    ('recruit:settings:code-tables:delete', '删除码表', 'BUTTON', 'settings'),
    ('recruit:settings:code-tables:export', '导出码表', 'BUTTON', 'settings'),
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