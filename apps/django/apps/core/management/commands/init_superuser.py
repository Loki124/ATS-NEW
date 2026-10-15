"""初始化/重置超级管理员（环境变量驱动，幂等）。

部署链路（ats-deploy-infra compose backend command）在 ``migrate`` +
``seed_v2_init`` 之后调用，保证生产环境始终存在一个可用超级管理员，
无需人工进 shell 建账号。这是线上 ``loki`` 登录 401 的根因修复：
原部署只跑 migrate + seed_v2_init + collectstatic，**从不创建/重置管理员**，
线上管理员是人工老账号，密码一旦对不上就只能 401。

环境变量：
  INIT_SUPERUSER_USERNAME   账号名（默认 loki）
  INIT_SUPERUSER_PASSWORD   密码；为空且账号不存在 → 随机生成并只打印一次；
                            账号已存在且未 FORCE → 不动密码
  INIT_SUPERUSER_FORCE      任意非空值 → 即使账号已存在也重置密码、
                            恢复软删/禁用状态，并使旧 refresh token 失效

行为（幂等，可重复跑）：
  - 账号不存在           → 创建（is_superuser/is_staff/is_active=True）
  - 账号存在但被软删     → 恢复 deleted_at=None + 确保超级管理员标志
  - 账号存在且 FORCE     → set_password + bump token_version（旧 token 失效）
  - 账号存在且非 FORCE   → 仅确保超级管理员标志，不碰密码
"""
import logging
import os
import secrets

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '通过环境变量初始化/重置超级管理员（幂等，可重复执行）'

    def _gen_password(self, ctx: str) -> str:
        pwd = secrets.token_urlsafe(20)
        self.stderr.write(
            self.style.WARNING(
                f'{ctx} 未提供 INIT_SUPERUSER_PASSWORD，已生成随机密码（仅此一次）: {pwd}'
            )
        )
        return pwd

    def handle(self, *args, **options):
        username = os.environ.get('INIT_SUPERUSER_USERNAME') or 'loki'
        password = os.environ.get('INIT_SUPERUSER_PASSWORD') or ''
        force = bool(os.environ.get('INIT_SUPERUSER_FORCE'))

        from apps.core.models import User

        # 含软删一起查，避免软删账号查不到导致重复创建
        user = User.objects.filter(username=username).first()

        # ---------- 账号不存在 → 创建 ----------
        if user is None:
            if not password:
                password = self._gen_password(f'账号 {username} 不存在且')
            user = User.objects.create(
                username=username,
                email=f'{username}@local',
                is_staff=True,
                is_superuser=True,
                is_active=True,
            )
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'✓ 已创建超级管理员 {username}'))
            return

        # ---------- 账号已存在 → 按需修复 ----------
        changed: list[str] = []
        if user.deleted_at is not None:
            user.deleted_at = None
            changed.append('恢复软删')
        if not user.is_superuser:
            user.is_superuser = True
            changed.append('提升为超级管理员')
        if not user.is_staff:
            user.is_staff = True
            changed.append('is_staff=True')
        if not user.is_active:
            user.is_active = True
            changed.append('恢复启用')

        if force or not user.has_usable_password():
            if not password:
                password = self._gen_password('FORCE 重置但')
            user.set_password(password)
            # 改密即撤销所有旧 refresh token（与 change_password_view 一致）
            user.token_version = (user.token_version or 0) + 1
            changed.append('重置密码')

        if changed:
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ 账号 {username} 已就绪（{", ".join(changed)}）')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✓ 账号 {username} 已存在且为超级管理员，无需变更')
            )
