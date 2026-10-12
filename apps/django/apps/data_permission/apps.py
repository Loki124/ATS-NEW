"""Data Permission app config."""
import logging

from django.apps import AppConfig


def _seed_scope_templates_on_post_migrate(**kwargs):
    """post_migrate 回调：预置内置数据权限模板（DPT0001 / DPT0002）。

    为什么挂信号而不是只靠部署脚本显式调用：
      部署链路（ats-deploy-infra 的 webhook-deploy.sh [3.5] 步）本来就会跑 migrate，
      挂在 post_migrate 上等于「上线自动预置」，不必要求运维额外记住一条命令；
      也与业务字典的既有做法一致（apps/dictionary/apps.py 同款 post_migrate，
      脚本侧再兜底一次）。

    必须用具名函数而非 lambda：post_migrate.connect 默认 weak=True，匿名临时对象
    会在 ready() 返回后被 GC，回调静默失效 —— dictionary 已踩过这个坑。

    幂等：按 code 判存续，已存在就跳过。所以每次 migrate 都会跑，但既不会重复建行，
    也不会覆盖管理员改过的模板内容（覆盖需显式执行 seed 命令 --reset）。
    """
    try:
        from apps.data_permission.management.commands.seed_data_perm_templates import (
            BUILTIN_TEMPLATES,
        )
        from apps.data_permission.models import DataPermTemplate

        created = 0
        for spec in BUILTIN_TEMPLATES:
            if DataPermTemplate.all_objects.filter(code=spec['code']).exists():
                continue
            DataPermTemplate.objects.create(
                code=spec['code'],
                name=spec['name'],
                module_key=spec['module_key'],
                description=spec['description'],
                params=spec['params'],
                groups=spec['groups'],
                version=1,
            )
            created += 1
        if created:
            logging.getLogger(__name__).info(
                'post_migrate 预置内置数据权限模板 %d 个', created)
    except Exception:  # noqa: BLE001 — 种子失败不得拖垮 migrate
        logging.getLogger(__name__).exception(
            '预置内置数据权限模板失败（不影响 migrate；可稍后手动执行 '
            'manage.py seed_data_perm_templates 补种）')


class DataPermissionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.data_permission'
    label = 'data_permission'
    verbose_name = '字段权限'

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(
            _seed_scope_templates_on_post_migrate, sender=self, weak=False,
        )