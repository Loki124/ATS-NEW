"""
init_demo_users.py — 初始化 ATS 演示用户

用法:
  cd apps/django
  python manage.py shell < scripts/init_demo_users.py

场景:
  - 全新部署后, DB 只有 createsuperuser 建的 admin (密码丢失或不知道)
  - seed 07_demo_user.json 的密码是占位符 "pbkdf2...lder", 不能直接 loaddata
  - 跑这个脚本会重置 4 个 demo 用户密码为已知值

用户表 (所有密码都是 demo123 的格式):
  admin / admin123456    - 系统管理员
  hr_zhang / hr123456     - HR 招聘专员
  hm_li / hm123456         - 技术部经理
  interview_wang / iv123456 - 面试官

2026-06-29: 花无缺写. 替代原来 seed fixture 的占位符密码方案.
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()

from apps.core.models import User  # noqa: E402

DEMO_USERS = [
    {"pk": 1, "username": "admin",         "password": "admin123456", "email": "admin@example.com",   "is_superuser": True,  "is_staff": True,  "first_name": "系统",   "last_name": "管理员",  "employee_id": "EMP-0001", "phone": "13800138000", "position_title": "系统管理员"},
    {"pk": 2, "username": "hr_zhang",      "password": "hr123456",    "email": "hr.zhang@example.com", "is_superuser": False, "is_staff": True,  "first_name": "张",     "last_name": "HR",     "employee_id": "EMP-1001", "phone": "13800138001", "position_title": "HR 招聘专员"},
    {"pk": 3, "username": "hm_li",         "password": "hm123456",    "email": "hm.li@example.com",   "is_superuser": False, "is_staff": False, "first_name": "李",     "last_name": "经理",   "employee_id": "EMP-2001", "phone": "13800138002", "position_title": "技术部经理"},
    {"pk": 4, "username": "interview_wang", "password": "iv123456",   "email": "wang@example.com",   "is_superuser": False, "is_staff": False, "first_name": "王",     "last_name": "面试官", "employee_id": "EMP-3001", "phone": "13800138003", "position_title": "高级工程师"},
]

for d in DEMO_USERS:
    pw = d.pop("password")
    obj, created = User.objects.update_or_create(
        pk=d["pk"],
        defaults={**d, "is_active": True, "deleted_at": None},
    )
    obj.set_password(pw)
    obj.save()
    print(f"[user] pk={obj.pk} username={obj.username!r} created={created} pw={pw}")

print("\n=== 当前活跃用户 ===")
for u in User.objects.filter(is_active=True, deleted_at__isnull=True).order_by("pk"):
    print(f"  pk={u.pk:3d} username={u.username:18s} emp={u.employee_id} pw_usable={u.has_usable_password()}")

print("\n✅ Demo 用户初始化完成。生产部署建议立刻改密码或删 demo 用户。")
