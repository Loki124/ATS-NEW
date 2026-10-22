"""campus_rotation app config。

ready() 负责：
- 注册两个字典种子（LIVE_ROOM_PLATFORM / LOCATION）到数据字典注册表；
- 将角色种子（CAMPUS_MENTOR / HEAD_TEACHER）挂到本 app 的 post_migrate 回调，
  确保仅在迁移完成后写库（容错：种子失败不影响 migrate）。
"""
import logging

from django.apps import AppConfig


def _seed_campus_roles_on_post_migrate(**kwargs):
    """post_migrate 回调：幂等预置身份角色。

    为什么挂信号而非只在 ready() 直接写：makemigrations / 表未就绪阶段直接写会抛
    OperationalError；挂在 post_migrate（sender=本 app）保证 RoleV2 表已就绪时注入。
    必须用具名函数（post_migrate.connect 默认 weak=True，匿名对象会被 GC 致回调失效）。
    容错：种子失败不得拖垮 migrate（对齐 data_permission/apps.py）。
    """
    try:
        from .seeds import seed_campus_roles

        seed_campus_roles()
    except Exception:  # noqa: BLE001 — 种子失败不影响 migrate
        logging.getLogger(__name__).exception(
            'campus_rotation 角色种子预置失败（不影响 migrate；可稍后重新 migrate 补种）'
        )


class CampusRotationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.campus_rotation'
    label = 'campus_rotation'
    verbose_name = '校招轮岗'

    def ready(self):
        from django.db.models.signals import post_migrate

        from apps.dictionary.registry import register_dictionary_seed

        from .seeds import (
            seed_brand_type,
            seed_cs_type_type,
            seed_live_room_platform_type,
            seed_location_type,
            seed_workstation_type_type,
        )

        register_dictionary_seed(seed_live_room_platform_type)
        register_dictionary_seed(seed_location_type)
        register_dictionary_seed(seed_brand_type)
        register_dictionary_seed(seed_cs_type_type)
        register_dictionary_seed(seed_workstation_type_type)

        post_migrate.connect(
            _seed_campus_roles_on_post_migrate, sender=self, weak=False,
        )
