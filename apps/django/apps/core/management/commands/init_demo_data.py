"""
初始化系统演示数据
Initialize System Demo Data

一键创建演示环境所需的所有基础数据：
1. 部门（根部门 + 3 个子部门）
2. 角色（9 个预置角色 + 默认权限绑定）
3. 用户（管理员 + HR + 面试官 + 候选人）
4. 渠道（4 个常用招聘渠道）
5. 流程模板（4 套：社招/校招/猎头/内部转岗）
"""
from __future__ import annotations

import logging
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '一键初始化演示环境（部门/角色/用户/渠道/模板）'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='清空所有演示数据再重建')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('重置模式: 将删除全部演示数据'))

        self.init_departments()
        self.init_roles()
        self.init_users()
        self.init_channels()
        self.init_stages()

        # 4 套流程模板 (依赖 RecruitmentStage 行, 已由 init_stages 保证)
        from django.core.management import call_command
        call_command('load_process_templates')

        self.stdout.write(self.style.SUCCESS('\n✅ 演示数据初始化完成！'))
        self.stdout.write('默认账号:')
        self.stdout.write('  - 超级管理员: admin / admin123')
        self.stdout.write('  - HR: hr_zhang / Pass@1234')
        self.stdout.write('  - 面试官: interview_wang / Pass@1234')

    def init_departments(self):
        from apps.core.models import Department
        root, _ = Department.objects.update_or_create(
            code='ROOT',
            defaults={'name': '集团总部', 'sort_order': 0, 'path': '/集团总部', 'is_active': True},
        )
        children = [
            ('TECH', '技术中心', 1),
            ('PRODUCT', '产品中心', 2),
            ('OPERATION', '运营中心', 3),
        ]
        for code, name, order in children:
            Department.objects.update_or_create(
                code=code,
                defaults={
                    'name': name, 'sort_order': order,
                    'parent': root,
                    'path': f'/集团总部/{name}',
                    'is_active': True,
                },
            )
        self.stdout.write('✓ 部门初始化完成')

    def init_roles(self):
        from apps.core.models import Permission, Role, RolePermission
        # 权限字典 — 2026-07-02 扩到业务全量
        # 命名约定:
        #   :read   — 菜单/读权限 (前端 menuPermissions 复选框)
        #   :export — 菜单/导出
        #   :create — 功能/新增
        #   :update — 功能/编辑
        #   :delete — 功能/删除
        #   :approve — 功能/审批
        #   :assign — 功能/分配
        perms = [
            # ─── 候选人 (candidate) ───
            ('candidate:read', '查看候选人', 'candidate'),
            ('candidate:export', '导出候选人', 'candidate'),
            ('candidate:create', '新增候选人', 'candidate'),
            ('candidate:update', '编辑候选人', 'candidate'),
            ('candidate:delete', '删除候选人', 'candidate'),
            ('candidate:assign', '分配面试官', 'candidate'),
            # ─── 申请 (application) ───
            ('application:read', '查看申请', 'application'),
            ('application:export', '导出申请', 'application'),
            ('application:create', '新建申请', 'application'),
            ('application:update', '编辑申请', 'application'),
            ('application:delete', '删除申请', 'application'),
            ('application:approve', '审批申请', 'application'),
            # ─── 需求 (demand) ───
            ('demand:read', '查看需求', 'demand'),
            ('demand:export', '导出需求', 'demand'),
            ('demand:create', '新建需求', 'demand'),
            ('demand:update', '编辑需求', 'demand'),
            ('demand:delete', '删除需求', 'demand'),
            ('demand:approve', '审批需求', 'demand'),
            # ─── 职位 (position) ───
            ('position:read', '查看职位', 'position'),
            ('position:export', '导出职位', 'position'),
            ('position:create', '新建职位', 'position'),
            ('position:update', '编辑职位', 'position'),
            ('position:delete', '删除职位', 'position'),
            # ─── 面试 (interview) ───
            ('interview:read', '查看面试', 'interview'),
            ('interview:create', '安排面试', 'interview'),
            ('interview:update', '编辑面试', 'interview'),
            ('interview:delete', '取消面试', 'interview'),
            ('interview:approve', '提交面试评价', 'interview'),
            # ─── Offer ───
            ('offer:read', '查看 Offer', 'offer'),
            ('offer:export', '导出 Offer', 'offer'),
            ('offer:create', '发起 Offer', 'offer'),
            ('offer:update', '编辑 Offer', 'offer'),
            ('offer:approve', '审批 Offer', 'offer'),
            ('offer:delete', '撤销 Offer', 'offer'),
            # ─── 入职 (onboarding) ───
            ('onboarding:read', '查看入职', 'onboarding'),
            ('onboarding:create', '发起入职', 'onboarding'),
            ('onboarding:update', '编辑入职信息', 'onboarding'),
            ('onboarding:approve', '审批入职', 'onboarding'),
            # ─── 推荐 (referral) ───
            ('referral:read', '查看内推', 'referral'),
            ('referral:create', '提交内推', 'referral'),
            ('referral:approve', '审批内推奖励', 'referral'),
            # ─── 自动化规则 (automation) ───
            ('automation:read', '查看自动化规则', 'automation'),
            ('automation:create', '新建自动化规则', 'automation'),
            ('automation:update', '编辑自动化规则', 'automation'),
            ('automation:delete', '删除自动化规则', 'automation'),
            # ─── 招聘流程 (process) ───
            ('process:read', '查看流程', 'process'),
            ('process:create', '新建流程', 'process'),
            ('process:update', '编辑流程', 'process'),
            ('process:delete', '删除流程', 'process'),
            # ─── 人才池 (talent_pool) ───
            ('talent_pool:read', '查看人才池', 'talent_pool'),
            ('talent_pool:create', '加入人才池', 'talent_pool'),
            ('talent_pool:update', '编辑人才池', 'talent_pool'),
            # ─── 数据分析 (analytics) ───
            ('analytics:read', '查看数据分析', 'analytics'),
            ('analytics:export', '导出报表', 'analytics'),
            # ─── 审计 (audit) ───
            ('audit:read', '查看审计日志', 'audit'),
            ('audit:export', '导出审计日志', 'audit'),
            # ─── 系统 (system) ───
            ('system:admin', '系统管理', 'system'),
        ]
        perm_objs = {}
        for code, name, module in perms:
            obj, _ = Permission.objects.update_or_create(
                code=code,
                defaults={'name': name, 'module': module, 'description': name},
            )
            perm_objs[code] = obj

        # 角色元数据 (code → name, description)
        # 修复: 之前直接 Role.objects.get(code=code) 假定 Role 行已存在 ⇒ 新库会抛 DoesNotExist ⇒
        #        @transaction.atomic 全量回滚 ⇒ init_users 永不执行 ⇒ admin 没 UserRole ⇒
        #        /auth/me/ 返回 roles=[] ⇒ 前端 RBAC guard 永久拒绝 (即使 localStorage 干净)
        # 修复后: 用 update_or_create 幂等创建 Role 行 (id=code, code=code, name=中文显示名)
        role_meta = {
            'SUPER_ADMIN':    ('超级管理员',  '系统所有权限'),
            'ADMIN':          ('管理员',     '系统管理'),
            'CHO':            ('CHO',       '高管视角, 只读分析'),
            'HR_DIRECTOR':    ('HR 负责人',  'HR 体系管理'),
            'HRBP':           ('HRBP',      '业务伙伴'),
            'HR':             ('HR 招聘专员', '招聘日常操作'),
            'HIRING_MANAGER': ('用人经理',   '业务侧用人方'),
            'INTERVIEWER':    ('面试官',     '面试评估'),
            'REFERRER':       ('推荐人',     '内推渠道'),
            'AUDITOR':        ('审计人员',   '合规审计'),
        }

        # 角色权限映射 — 2026-07-02 跟随新命名 :read/:update/:create/:approve/:delete
        role_perm_map = {
            'SUPER_ADMIN': [p for p in perm_objs.keys()],
            'CHO': ['analytics:read', 'audit:read', 'candidate:read', 'application:read', 'process:read', 'demand:read'],
            'HR_DIRECTOR': ['candidate:read', 'candidate:update', 'application:read', 'application:update',
                            'demand:read', 'demand:update', 'process:read', 'process:update',
                            'analytics:read', 'automation:read', 'offer:read', 'interview:read'],
            'HRBP': ['candidate:read', 'candidate:update', 'application:read', 'application:update',
                     'demand:read', 'process:read', 'analytics:read', 'offer:read', 'interview:read'],
            'HR': ['candidate:read', 'candidate:update', 'application:read', 'application:update',
                   'demand:read', 'process:read', 'offer:read'],
            'HIRING_MANAGER': ['candidate:read', 'application:read', 'demand:read', 'demand:update'],
            'INTERVIEWER': ['candidate:read', 'application:read', 'interview:read', 'interview:approve'],
            'REFERRER': ['candidate:read', 'candidate:create', 'referral:read', 'referral:create'],
            'AUDITOR': ['audit:read', 'audit:export', 'candidate:read', 'application:read', 'process:read'],
            # ADMIN 不在 role_perm_map 中: 它是系统管理员角色, 权限通过 is_staff/is_superuser 直接放行
            #                              如果将来要给 ADMIN 也配 perm, 在此添加
        }

        # Step 1: 幂等创建/更新 Role 行 (覆盖 role_meta 全集, 包括没在 role_perm_map 中的 ADMIN)
        # 注意 Role.id 是 CharField 无默认值, 不能直接 update_or_create(id=code,...) 因为
        #     已有的 Role 行可能由历史代码用别的 id 创建过 (e.g. uuid), 再 INSERT 会触发
        #     UNIQUE constraint failed: roles.code. 这里 split: 不存在则建 id=code, 存在则只 update 元数据.
        for code, (name, desc) in role_meta.items():
            try:
                role = Role.objects.get(code=code)
                role.name = name
                role.description = desc
                role.is_builtin = True
                role.is_active = True
                role.save(update_fields=['name', 'description', 'is_builtin', 'is_active', 'updated_at'])
            except Role.DoesNotExist:
                Role.objects.create(
                    id=code,
                    code=code,
                    name=name,
                    description=desc,
                    is_builtin=True,
                    is_active=True,
                )

        # Step 2: 绑定权限 (此时 Role 已确保存在, .get 安全)
        for code, perms_to_grant in role_perm_map.items():
            role = Role.objects.get(code=code)
            for perm_code in perms_to_grant:
                RolePermission.objects.get_or_create(role=role, permission=perm_objs[perm_code])

        self.stdout.write(f'✓ 角色 + 权限初始化完成（{len(role_meta)} 个角色, {len(role_perm_map)} 个绑权限）')

    def init_users(self):
        from apps.core.models import Department, Role, User, UserRole

        # 默认密码（开发环境用）
        default_pwd = 'Pass@1234'

        users = [
            ('admin', '系统', '管理员', 'admin@example.com', 'EMP-0001',
             '13800138000', 'ROOT', 'SUPER_ADMIN', True, True),
            ('hr_zhang', '张', 'HR', 'hr.zhang@example.com', 'EMP-1001',
             '13800138001', 'ROOT', 'HR', False, True),
            ('hrbp_liu', '刘', 'HRBP', 'hrbp.liu@example.com', 'EMP-1002',
             '13800138002', 'TECH', 'HRBP', False, True),
            ('hm_li', '李', '经理', 'hm.li@example.com', 'EMP-2001',
             '13800138003', 'TECH', 'HIRING_MANAGER', False, False),
            ('hm_wang', '王', '经理', 'hm.wang@example.com', 'EMP-2002',
             '13800138004', 'PRODUCT', 'HIRING_MANAGER', False, False),
            ('interview_zhao', '赵', '面试官', 'zhao@example.com', 'EMP-3001',
             '13800138005', 'TECH', 'INTERVIEWER', False, False),
            ('interview_chen', '陈', '面试官', 'chen@example.com', 'EMP-3002',
             '13800138006', 'TECH', 'INTERVIEWER', False, False),
        ]

        for (username, first, last, email, eid, phone, dept_code,
             role_code, is_super, is_staff) in users:
            dept = Department.objects.filter(code=dept_code).first()
            role = Role.objects.filter(code=role_code).first()
            user, created = User.objects.get_or_create(
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
                }
            )
            if created:
                user.set_password('admin123' if username == 'admin' else default_pwd)
                user.save()
            UserRole.objects.get_or_create(user=user, role=role, department=None)
            self.stdout.write(f'  {"新建" if created else "已存在"}: {username}')

        self.stdout.write('✓ 用户初始化完成')

    def init_channels(self):
        from apps.channel.models import Channel
        # 2026-06-17: 修复 — Channel 模型字段是 `category` (枚举 CAMPUS/SOCIAL/HEADHUNTER/REFERRAL/AGENCY/OTHER),
        #             无 `type`/`is_builtin` 字段. 之前的中文 tuple 第三元素直接当 ctype 塞 'type' → FieldError → @atomic 全量回滚.
        # 现在: tuple 第三元素改为枚举值; defaults 用 category; 删掉 is_builtin.
        channels = [
            ('BOSSWHIP',   'BOSS 直聘',   'SOCIAL',     True),
            ('LAGOU',      '拉勾网',      'SOCIAL',     True),
            ('LIEPIN',     '猎聘',        'SOCIAL',     True),
            ('ZHILIAN',    '智联招聘',    'SOCIAL',     True),
            ('WECOM',      '企业微信',    'REFERRAL',   True),
            ('CAMPUS',     '校园招聘',    'CAMPUS',     True),
            ('HEADHUNTER', '猎头推荐',    'HEADHUNTER', True),
            ('INTERNAL',   '内部推荐',    'REFERRAL',   True),
        ]
        for code, name, category, active in channels:
            Channel.objects.update_or_create(
                code=code,
                defaults={'name': name, 'category': category, 'is_active': active},
            )
        self.stdout.write(f'✓ 渠道初始化完成（{len(channels)} 个）')

    def init_stages(self):
        """系统预置阶段库 (8 个).

        历史: seeds/01_system_stages.json 走 loaddata 直接 INSERT, 不经过 model.save() →
              auto_now_add 字段 (created_at/updated_at) 未被填充 → NOT NULL constraint 错误.
        现在: 程序化 create/update, model.save() 正常触发 auto_now_add. 幂等 (按 code 查).
        """
        from apps.process.models import RecruitmentStage
        # (id, code, name, stage_type, is_builtin, description, default_features, optional_features)
        stages = [
            ('stg_001_initial_review', 'P001', '初评',       'SCREEN',     True,
             '对简历进行初步评估，是候选人进入流程的第一道关卡',
             ['RESUME_REVIEW', 'AUTO_MATCH', 'BULK_IMPORT'], ['SCORE_RANK', 'DUPLICATE_CHECK']),
            ('stg_002_resume_eval',    'P002', '简历评估',   'SCREEN',     False,
             'HR 对简历进行深入评估',
             ['RESUME_REVIEW', 'SCORING'], ['AI_SCORE']),
            ('stg_003_phone_interview','P003', '电话沟通',   'INVITATION', False,
             'HR 与候选人电话沟通意向、薪资、到岗时间',
             ['PHONE_CALL', 'NOTES', 'CANDIDATE_INFO'], ['VOICE_RECORD']),
            ('stg_004_hr_interview',   'P004', 'HR 面',      'INTERVIEW',  False,
             'HR 初面，了解候选人综合素质',
             ['INTERVIEW_SCHEDULE', 'EVALUATION_FORM'], ['VIDEO_RECORD', 'MULTI_ROUND']),
            ('stg_005_tech_interview_1','P005', '技术一面',   'INTERVIEW',  False,
             '技术能力初筛',
             ['INTERVIEW_SCHEDULE', 'EVALUATION_FORM', 'CODE_EDITOR'], ['VIDEO_RECORD', 'JOINT_INTERVIEW']),
            ('stg_006_tech_interview_2','P006', '技术二面',   'INTERVIEW',  False,
             '深度技术考察',
             ['INTERVIEW_SCHEDULE', 'EVALUATION_FORM'], ['VIDEO_RECORD', 'JOINT_INTERVIEW']),
            ('stg_007_hm_interview',   'P007', '用人经理面', 'INTERVIEW',  False,
             '用人经理综合面试',
             ['INTERVIEW_SCHEDULE', 'EVALUATION_FORM'], ['VIDEO_RECORD']),
            ('stg_008_offer',          'P008', '正式录用',   'OFFER',      True,
             '发放 Offer，进入入职准备阶段',
             ['OFFER_GENERATION', 'OFFER_APPROVAL', 'CANDIDATE_RESPONSE'],
             ['SALARY_NEGOTIATION', 'BACKGROUND_CHECK']),
        ]
        for sid, code, name, stype, is_builtin, desc, defaults_f, opt_f in stages:
            try:
                obj = RecruitmentStage.objects.get(code=code)
                obj.name = name
                obj.stage_type = stype
                obj.is_builtin = is_builtin
                obj.description = desc
                obj.default_features = defaults_f
                obj.optional_features = opt_f
                obj.status = 'ENABLED'
                obj.save()
            except RecruitmentStage.DoesNotExist:
                RecruitmentStage.objects.create(
                    id=sid, code=code, name=name, stage_type=stype,
                    is_builtin=is_builtin, description=desc,
                    default_features=defaults_f, optional_features=opt_f,
                    status='ENABLED',
                )
        self.stdout.write(f'✓ 阶段库初始化完成（{len(stages)} 个）')
