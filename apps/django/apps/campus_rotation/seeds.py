"""campus_rotation 种子数据。

- 字典种子：LIVE_ROOM_PLATFORM（直播间平台）/ LOCATION（地点），范式照搬
  apps/dictionary/seeds.py 的 _seed_type（update_or_create(type__code, key)，幂等）。
- 角色种子：CAMPUS_MENTOR（校园导师）/ HEAD_TEACHER（班主任），RoleV2 系统预置，
  幂等 update_or_create(system_code='recruit', role_code=...)。

字典种子在 AppConfig.ready() 经 register_dictionary_seed 注册，由 dictionary 的
post_migrate 信号统一注入（dictionary 模块零改动）。
角色种子因涉及写库，挂在 campus_rotation 自身的 post_migrate 回调，避免在 makemigrations
等表未就绪阶段误写（与 data_permission/apps.py 同款容错范式）。
"""
from apps.dictionary.seeds import _seed_type

# (key, 名称, 英文名, 排序)
LIVE_ROOM_PLATFORM_ITEMS = [
    ('VIDEO_ACCOUNT', '视频号', 'WeChat Channels', 10),
    ('TENCENT_MEETING', '腾讯会议', 'Tencent Meeting', 20),
    ('WECHAT_WORK_LIVE', '企微直播', 'WeCom Live', 30),
]

LOCATION_ITEMS = [
    ('BEIJING', '北京', 'Beijing', 10),
    ('SHANGHAI', '上海', 'Shanghai', 20),
    ('SHENZHEN', '深圳', 'Shenzhen', 30),
    ('CHENGDU', '成都', 'Chengdu', 40),
]


def seed_live_room_platform_type():
    """直播间平台字典（系统预置，可扩展）。"""
    _seed_type(
        'LIVE_ROOM_PLATFORM', '直播间平台', 'Live Room Platform',
        '直播间所属直播平台枚举（视频号/腾讯会议/企微直播）',
        LIVE_ROOM_PLATFORM_ITEMS,
    )


def seed_location_type():
    """地点字典（系统预置，可扩展）。"""
    _seed_type(
        'LOCATION', '地点', 'Location',
        '直播间/轮岗地点枚举',
        LOCATION_ITEMS,
    )


def seed_campus_roles():
    """幂等创建校招轮岗所需身份角色（RoleV2 系统预置）。"""
    from apps.core.models_permission_v2 import RoleV2

    RoleV2.objects.update_or_create(
        system_code='recruit', role_code='CAMPUS_MENTOR',
        defaults={
            'role_name': '校园导师',
            'template_code': None,
            'description': '校招轮岗直播间/安排导师',
            'is_system': 1,
            'status': 1,
        },
    )
    RoleV2.objects.update_or_create(
        system_code='recruit', role_code='HEAD_TEACHER',
        defaults={
            'role_name': '班主任',
            'template_code': None,
            'description': '校招轮岗班级管理班主任',
            'is_system': 1,
            'status': 1,
        },
    )
