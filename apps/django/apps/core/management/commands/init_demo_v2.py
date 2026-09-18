"""Init Demo Data V2 — 一键初始化演示环境（V2 RBAC 兼容版）

替代 init_demo_data.py (旧版因 V1 Role/RolePermission/UserRole 被 DROP 而 ImportError).

调用顺序:
  1. seed_v2_init.py  → 建 70 PermissionResource + 4 PermissionTemplate + TenantConfig
  2. init_demo_v2.py  → 建 Department + RoleV2 + User + UserRoleV2 + ManagementUnit + Channel + Stage
  3. load_process_templates.py → 建 4 套 RecruitmentProcess 模板 (本命令自动调用)
  4. init_dictionary.py → 建数据字典 (本命令自动调用)

幂等 — update_or_create / get_or_create, 可重复跑.
"""
from __future__ import annotations

import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

SYSTEM = 'recruit'


# (role_code, role_name, template_code, description)
ROLE_META = [
    ('SUPER_ADMIN',    '超级管理员',  'TMPL_ADMIN',       '系统所有权限'),
    ('ADMIN',          '管理员',     'TMPL_ADMIN',       '系统管理'),
    ('CHO',            'CHO',       'TMPL_DIRECTOR',    '高管视角, 只读分析'),
    ('HR_DIRECTOR',    'HR 负责人',  'TMPL_DIRECTOR',    'HR 体系管理'),
    ('HRBP',           'HRBP',      'TMPL_SPECIALIST',  '业务伙伴'),
    ('HR',             'HR 招聘专员', 'TMPL_SPECIALIST',  '招聘日常操作'),
    ('HIRING_MANAGER', '用人经理',   'TMPL_SPECIALIST',  '业务侧用人方'),
    ('INTERVIEWER',    '面试官',     'TMPL_INTERVIEWER', '面试评估'),
    ('REFERRER',       '推荐人',     'TMPL_INTERVIEWER', '内推渠道'),
    ('AUDITOR',        '审计人员',   'TMPL_DIRECTOR',    '合规审计'),
]


# (username, last_name, first_name, email, employee_id, phone, dept_name, is_super, is_staff)
DEMO_USERS = [
    ('hr_zhang',       '张', 'HR',    'hr.zhang@example.com', 'EMP-1001', '13800138001', '集团总部',   False, True),
    ('hrbp_liu',       '刘', 'HRBP',  'hrbp.liu@example.com', 'EMP-1002', '13800138002', '技术中心',   False, True),
    ('hm_li',          '李', '经理',   'hm.li@example.com',   'EMP-2001', '13800138003', '技术中心',   False, False),
    ('hm_wang',        '王', '经理',   'hm.wang@example.com', 'EMP-2002', '13800138004', '产品中心',   False, False),
    ('interview_zhao', '赵', '面试官', 'zhao@example.com',    'EMP-3001', '13800138005', '技术中心',   False, False),
    ('interview_chen', '陈', '面试官', 'chen@example.com',    'EMP-3002', '13800138006', '技术中心',   False, False),
]


# (username, role_code) — 给 demo user 绑 UserRoleV2
DEMO_USER_ROLES = [
    ('hr_zhang',       'HR'),
    ('hrbp_liu',       'HRBP'),
    ('hm_li',          'HIRING_MANAGER'),
    ('hm_wang',        'HIRING_MANAGER'),
    ('interview_zhao', 'INTERVIEWER'),
    ('interview_chen', 'INTERVIEWER'),
]


# (code, name, category, is_active)
CHANNELS = [
    ('BOSSWHIP',   'BOSS 直聘',   'SOCIAL',     True),
    ('LAGOU',      '拉勾网',      'SOCIAL',     True),
    ('LIEPIN',     '猎聘',        'SOCIAL',     True),
    ('ZHILIAN',    '智联招聘',    'SOCIAL',     True),
    ('WECOM',      '企业微信',    'REFERRAL',   True),
    ('CAMPUS',     '校园招聘',    'CAMPUS',     True),
    ('HEADHUNTER', '猎头推荐',    'HEADHUNTER', True),
    ('INTERNAL',   '内部推荐',    'REFERRAL',   True),
]


# (id, code, name, stage_type, is_builtin, description, default_features, optional_features, is_start, is_end)
STAGES = [
    ('stg_001_initial_review',  'P001', '初评',       'SCREEN',     True,
     '对简历进行初步评估，是候选人进入流程的第一道关卡',
     ['RESUME_REVIEW', 'AUTO_MATCH', 'BULK_IMPORT'], ['SCORE_RANK', 'DUPLICATE_CHECK'],
     True, False),
    ('stg_002_resume_eval',     'P002', '简历评估',   'SCREEN',     False,
     'HR 对简历进行深入评估',
     ['RESUME_REVIEW', 'SCORING'], ['AI_SCORE'],
     False, False),
    ('stg_003_phone_interview', 'P003', '电话沟通',   'INVITATION', False,
     'HR 与候选人电话沟通意向、薪资、到岗时间',
     ['PHONE_CALL', 'NOTES', 'CANDIDATE_INFO'], ['VOICE_RECORD'],
     False, False),
    ('stg_004_hr_interview',    'P004', 'HR 面',      'INTERVIEW',  False,
     'HR 初面，了解候选人综合素质',
     ['INTERVIEW_SCHEDULE', 'EVALUATION_FORM'], ['VIDEO_RECORD', 'MULTI_ROUND'],
     False, False),
    ('stg_005_tech_interview_1','P005', '技术一面',   'INTERVIEW',  False,
     '技术能力初筛',
     ['INTERVIEW_SCHEDULE', 'EVALUATION_FORM', 'CODE_EDITOR'], ['VIDEO_RECORD', 'JOINT_INTERVIEW'],
     False, False),
    ('stg_006_tech_interview_2','P006', '技术二面',   'INTERVIEW',  False,
     '深度技术考察',
     ['INTERVIEW_SCHEDULE', 'EVALUATION_FORM'], ['VIDEO_RECORD', 'JOINT_INTERVIEW'],
     False, False),
    ('stg_007_hm_interview',    'P007', '用人经理面', 'INTERVIEW',  False,
     '用人经理综合面试',
     ['INTERVIEW_SCHEDULE', 'EVALUATION_FORM'], ['VIDEO_RECORD'],
     False, False),
    ('stg_008_offer',           'P008', '正式录用',   'OFFER',      True,
     '发放 Offer，进入入职准备阶段',
     ['OFFER_GENERATION', 'OFFER_APPROVAL', 'CANDIDATE_RESPONSE'],
     ['SALARY_NEGOTIATION', 'BACKGROUND_CHECK'],
     False, True),
]


class Command(BaseCommand):
    help = '一键初始化演示环境（部门/角色/用户/渠道/阶段）— V2 RBAC 兼容版'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='清空演示数据再重建')
        parser.add_argument('--skip-templates', action='store_true', help='跳过 load_process_templates')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('重置模式: 将删除 RoleV2/UserRoleV2/DemoUser/DemoRoleBinding/Channel/Stage/DemoDepartment 数据'))

        self.init_departments()
        self.init_roles_v2()
        self.init_users()
        self.bind_user_roles_v2()
        self.init_channels()
        self.init_stages()

        # 字典 + 流程模板 — 自动 call
        self.stdout.write('\n→ call init_dictionary ...')
        call_command('init_dictionary')

        if not options['skip_templates']:
            self.stdout.write('→ call load_process_templates ...')
            try:
                call_command('load_process_templates')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'load_process_templates 出错 (非阻断): {e}'))

        self.stdout.write(self.style.SUCCESS('\n✅ Demo Data V2 初始化完成'))
        self.stdout.write('默认账号:')
        self.stdout.write('  - 超级管理员: admin / admin123  (已绑 SUPER_ADMIN → TMPL_ADMIN → 全权限)')
        self.stdout.write('  - HR:         hr_zhang / Pass@1234  (已绑 HR → TMPL_SPECIALIST)')
        self.stdout.write('  - HRBP:       hrbp_liu / Pass@1234  (已绑 HRBP → TMPL_SPECIALIST)')
        self.stdout.write('  - 用人经理:    hm_li / Pass@1234      (已绑 HIRING_MANAGER → TMPL_SPECIALIST)')
        self.stdout.write('  - 面试官:      interview_zhao / Pass@1234  (已绑 INTERVIEWER → TMPL_INTERVIEWER)')

    def init_departments(self):
        """4 个部门（树形）— V1 Department 保留给 User.department FK 用.

        按 name 定位部门 (不再按 code), 兼容部门编号已统一为 D###### 的情况;
        新建部门由 Department.save() 自动生成 D###### 编号, 已存在部门不会被改号.
        """
        from apps.core.models import Department
        root, _ = Department.objects.update_or_create(
            name='集团总部',
            defaults={'name': '集团总部', 'sort_order': 0, 'path': '/集团总部', 'is_active': True},
        )
        children = [
            ('技术中心', 1),
            ('产品中心', 2),
            ('运营中心', 3),
        ]
        for name, order in children:
            Department.objects.update_or_create(
                name=name,
                defaults={
                    'name': name, 'sort_order': order,
                    'parent': root,
                    'path': f'/集团总部/{name}',
                    'is_active': True,
                },
            )
        self.stdout.write(f'✓ 部门初始化完成（1 根 + {len(children)} 子 = 4 个）')

    def init_roles_v2(self):
        """9 个 RoleV2 — 每个 role 引用 1 个 PermissionTemplate."""
        from apps.core.models_permission_v2 import PermissionTemplate, RoleV2

        # 校验模板存在
        existing_tpls = set(PermissionTemplate.objects.filter(
            system_code=SYSTEM, status=1,
        ).values_list('template_code', flat=True))
        missing_tpls = {role[2] for role in ROLE_META} - existing_tpls
        if missing_tpls:
            self.stdout.write(self.style.ERROR(
                f'缺模板 {missing_tpls}, 请先跑 seed_v2_init.py'))
            return

        created = updated = 0
        for code, name, template_code, desc in ROLE_META:
            obj, was_created = RoleV2.objects.update_or_create(
                system_code=SYSTEM, role_code=code,
                defaults={
                    'role_name': name,
                    'template_code': template_code,
                    'description': desc,
                    'is_system': 1,
                    'status': 1,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(
            f'✓ RoleV2 初始化完成（{created} 创建 / {updated} 更新 / {len(ROLE_META)} 角色）'
        )

    def init_users(self):
        """6 个 demo user — 不重建 admin (admin 由创建 superuser 时已存在)."""
        from apps.core.models import Department, User

        default_pwd = 'Pass@1234'
        created = updated = 0
        for (username, first, last, email, eid, phone, dept_name,
             is_super, is_staff) in DEMO_USERS:
            dept = Department.objects.filter(name=dept_name).first()
            user, was_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'employee_id': eid,
                    'phone': phone,
                    'first_name': first,
                    'last_name': last,
                    'is_superuser': is_super,
                    'is_staff': is_staff,
                    'is_active': True,
                    'department': dept,
                },
            )
            if was_created:
                user.set_password(default_pwd)
                user.save()
                created += 1
            else:
                updated += 1
        # admin 已存在确认（不重建）— 强制确保密码正确
        admin = User.objects.filter(username='admin').first()
        if admin:
            admin.set_password('admin123')
            admin.is_superuser = True
            admin.is_staff = True
            admin.is_active = True
            admin.save()
        self.stdout.write(
            f'✓ Demo User 初始化完成（{created} 新建 / {updated} 已存在 / admin 密码重置为 admin123）'
        )

    def bind_user_roles_v2(self):
        """建 ROOT_MGMT 管理单元 + 给 admin + 6 demo user 绑 UserRoleV2."""
        from apps.core.models import User
        from apps.core.models_permission_v2 import (
            ManagementUnit, RoleV2, UserRoleV2,
        )

        # 1. 建 ROOT_MGMT（管理单元）
        root_mgmt, _ = ManagementUnit.objects.update_or_create(
            system_code=SYSTEM, unit_name='全公司',
            defaults={
                'unit_type': 'org',
                'org_scope': {'level': 'ROOT', 'name': '全公司'},
                'include_children': 1,
                'status': 1,
            },
        )

        # 2. 给 admin 绑 SUPER_ADMIN（必做 — admin 是超管核心）
        admin = User.objects.get(username='admin')
        UserRoleV2.objects.update_or_create(
            user_id=admin.id, role_code='SUPER_ADMIN', system_code=SYSTEM,
            defaults={
                'management_unit_ids': [root_mgmt.id],
                'granted_by_id': admin.id,
            },
        )

        # 3. 给 6 demo user 绑各自 role
        bound = 0
        for username, role_code in DEMO_USER_ROLES:
            user = User.objects.filter(username=username).first()
            if not user:
                self.stdout.write(self.style.WARNING(f'  跳过: {username} 不存在'))
                continue
            # 校验 role_code 存在
            if not RoleV2.objects.filter(system_code=SYSTEM, role_code=role_code).exists():
                self.stdout.write(self.style.WARNING(f'  跳过: RoleV2 {role_code} 不存在'))
                continue
            UserRoleV2.objects.update_or_create(
                user_id=user.id, role_code=role_code, system_code=SYSTEM,
                defaults={
                    'management_unit_ids': [root_mgmt.id],
                    'granted_by_id': admin.id,
                },
            )
            bound += 1

        self.stdout.write(
            f'✓ UserRoleV2 绑定完成（admin → SUPER_ADMIN + {bound} demo user）'
        )

    def init_channels(self):
        from apps.channel.models import Channel
        created = 0
        for code, name, category, active in CHANNELS:
            obj, was_created = Channel.objects.update_or_create(
                code=code,
                defaults={'name': name, 'category': category, 'is_active': active},
            )
            if was_created:
                created += 1
        self.stdout.write(f'✓ 渠道初始化完成（{created} 新建 / {len(CHANNELS) - created} 已存在 / {len(CHANNELS)} 总）')

    def init_stages(self):
        """8 个 RecruitmentStage — 含 BR-001 is_start/is_end 标志."""
        from apps.process.models import RecruitmentStage
        created = 0
        for sid, code, name, stype, is_builtin, desc, defaults_f, opt_f, is_start, is_end in STAGES:
            try:
                obj = RecruitmentStage.objects.get(code=code)
                obj.name = name
                obj.stage_type = stype
                obj.is_builtin = is_builtin
                obj.description = desc
                obj.default_features = defaults_f
                obj.optional_features = opt_f
                obj.is_start = is_start
                obj.is_end = is_end
                obj.status = 'ENABLED'
                obj.save()
            except RecruitmentStage.DoesNotExist:
                RecruitmentStage.objects.create(
                    id=sid, code=code, name=name, stage_type=stype,
                    is_builtin=is_builtin, description=desc,
                    default_features=defaults_f, optional_features=opt_f,
                    is_start=is_start, is_end=is_end,
                    status='ENABLED',
                )
                created += 1
        self.stdout.write(f'✓ 阶段库初始化完成（{created} 新建 / {len(STAGES) - created} 已存在 / {len(STAGES)} 总）')
