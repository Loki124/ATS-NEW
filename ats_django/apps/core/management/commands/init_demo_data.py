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

        # 4 套流程模板
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
        # 权限字典（精简版，覆盖核心场景）
        perms = [
            ('candidate:read', '查看候选人', 'candidate'),
            ('candidate:write', '编辑候选人', 'candidate'),
            ('application:read', '查看申请', 'application'),
            ('application:write', '编辑申请', 'application'),
            ('demand:read', '查看需求', 'demand'),
            ('demand:write', '编辑需求', 'demand'),
            ('process:read', '查看流程', 'process'),
            ('process:write', '编辑流程', 'process'),
            ('automation:read', '查看自动化规则', 'automation'),
            ('automation:write', '编辑自动化规则', 'automation'),
            ('analytics:read', '查看数据分析', 'analytics'),
            ('audit:read', '查看审计日志', 'audit'),
            ('system:admin', '系统管理', 'system'),
        ]
        perm_objs = {}
        for code, name, module in perms:
            obj, _ = Permission.objects.update_or_create(
                code=code,
                defaults={'name': name, 'module': module, 'description': name},
            )
            perm_objs[code] = obj

        # 角色权限映射
        role_perm_map = {
            'SUPER_ADMIN': [p for p in perm_objs.keys()],
            'CHO': ['analytics:read', 'audit:read', 'candidate:read', 'application:read', 'process:read', 'demand:read'],
            'HR_DIRECTOR': ['candidate:read', 'candidate:write', 'application:read', 'application:write',
                            'demand:read', 'demand:write', 'process:read', 'process:write',
                            'analytics:read', 'automation:read'],
            'HRBP': ['candidate:read', 'candidate:write', 'application:read', 'application:write',
                     'demand:read', 'process:read', 'analytics:read'],
            'HR': ['candidate:read', 'candidate:write', 'application:read', 'application:write',
                   'demand:read', 'process:read'],
            'HIRING_MANAGER': ['candidate:read', 'application:read', 'demand:read', 'demand:write'],
            'INTERVIEWER': ['candidate:read', 'application:read'],
            'REFERRER': ['candidate:read', 'candidate:write'],
            'AUDITOR': ['audit:read', 'candidate:read', 'application:read', 'process:read'],
        }

        for code, perms_to_grant in role_perm_map.items():
            role = Role.objects.get(code=code)
            for perm_code in perms_to_grant:
                RolePermission.objects.get_or_create(role=role, permission=perm_objs[perm_code])

        self.stdout.write(f'✓ 角色 + 权限初始化完成（{len(role_perm_map)} 个角色）')

    def init_users(self):
        from apps.core.models import Department, Role, User, UserRole
        from apps.channel.models import Channel

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
        channels = [
            ('BOSSWHIP', 'BOSS 直聘', '招聘网站', True, True),
            ('LAGOU', '拉勾网', '招聘网站', True, True),
            ('LIEPIN', '猎聘', '招聘网站', True, True),
            ('ZHILIAN', '智联招聘', '招聘网站', True, True),
            ('WECOM', '企业微信', '内推渠道', True, True),
            ('CAMPUS', '校园招聘', '校招渠道', True, True),
            ('HEADHUNTER', '猎头推荐', '猎头渠道', True, True),
            ('INTERNAL', '内部推荐', '内部渠道', True, True),
        ]
        for code, name, ctype, builtin, active in channels:
            Channel.objects.update_or_create(
                code=code,
                defaults={'name': name, 'type': ctype, 'is_builtin': builtin, 'is_active': active},
            )
        self.stdout.write(f'✓ 渠道初始化完成（{len(channels)} 个）')
