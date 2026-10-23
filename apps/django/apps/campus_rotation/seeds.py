"""campus_rotation 种子数据。

- 字典种子：LIVE_ROOM_PLATFORM（轮岗平台）/ LOCATION（地点），范式照搬
  apps/dictionary/seeds.py 的 _seed_type（update_or_create(type__code, key)，幂等）。
- 角色种子：CAMPUS_MENTOR（校园导师）/ HEAD_TEACHER（班主任），RoleV2 系统预置，
  幂等 update_or_create(system_code='recruit', role_code=...)。

字典种子在 AppConfig.ready() 经 register_dictionary_seed 注册，由 dictionary 的
post_migrate 信号统一注入（dictionary 模块零改动）。
角色种子因涉及写库，挂在 campus_rotation 自身的 post_migrate 回调，避免在 makemigrations
等表未就绪阶段误写（与 data_permission/apps.py 同款容错范式）。

⚠️ 2026-10-22 兵哥指令「直播间 + 客服部门整合为轮岗资源」后，以下字典**已不再绑定任何模型字段**
（字段随需求下线，字典本身保留为可运营维护的目录，不会删历史数据）：
  · BRAND（品牌）           → 原客服部门 / 直播间的 brand 字段已下线
  · CS_TYPE（客服类型）     → 原客服部门的 cs_type 字段已下线
  · WORKSTATION_TYPE（工位类型）→ 原客服部门的 workstation_type 字段已下线
  · LOCATION（地点）        → 轮岗资源的 location 已改为**自由文本**，不再查字典
保留它们而非删除，是因为字典是**运营可维护的目录**（运营可能已在字典页增改过条目），
删种子只会让新环境缺目录、却不会清理老环境的历史数据 —— 两头不讨好。
真正生效的只有 LIVE_ROOM_PLATFORM（轮岗资源的 platform 字段）。
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

# 客服部门「品牌」字典（方案 §5.3 原拟 FK→apps.brand.Brand，但 BrandInfo 为单例雇主品牌，
# 无法做可选品牌目录 → 改为存字典 key，与 platform/location 同构；业务方可在字典页增改）。
BRAND_ITEMS = [
    ('CORE', '核心品牌', 'Core Brand', 10),
    ('ECOMMERCE', '电商品牌', 'E-commerce Brand', 20),
    ('FINANCE', '金融品牌', 'Finance Brand', 30),
]

# 客服部门「客服类型」字典（方案 §5.3 专属项）。
CS_TYPE_ITEMS = [
    ('ONLINE', '在线', 'Online', 10),
    ('OUTBOUND', '外呼', 'Outbound', 20),
    ('AFTER_SALES', '售后', 'After-sales', 30),
]

# 客服部门「工位类型」字典（方案 §5.3 专属项）。
WORKSTATION_TYPE_ITEMS = [
    ('SEAT', '坐席', 'Seat', 10),
    ('NON_SEAT', '非坐席', 'Non-seat', 20),
]


def seed_live_room_platform_type():
    """轮岗平台字典（系统预置，可扩展）。

    2026-10-23 闸口1 裁决 Q2：字典**沿用** LIVE_ROOM_PLATFORM（零迁移、零数据风险），
    但**展示名改为中性口径** —— 平台字段自本次起对直播间 / 客服部门 / 其他
    三类形态均可填写，不再是直播间专属 → 展示名不能继续叫「直播间平台」。
    字典项仍是「视频号 / 腾讯会议 / 企微直播」三项，本次**不加项**（运营可在字典页自行维护）。
    """
    _seed_type(
        'LIVE_ROOM_PLATFORM', '轮岗平台', 'Rotation Platform',
        '轮岗资源所属平台枚举（视频号/腾讯会议/企微直播）',
        LIVE_ROOM_PLATFORM_ITEMS,
    )


def seed_location_type():
    """地点字典（系统预置，可扩展）。"""
    _seed_type(
        'LOCATION', '地点', 'Location',
        '直播间/轮岗地点枚举',
        LOCATION_ITEMS,
    )


def seed_brand_type():
    """客服部门品牌字典（系统预置，可扩展）。"""
    _seed_type(
        'BRAND', '品牌', 'Brand',
        '客服部门/直播间所属品牌枚举（方案 §5.3；原拟 FK 改字典 key）',
        BRAND_ITEMS,
    )


def seed_cs_type_type():
    """客服类型字典（系统预置，可扩展）。"""
    _seed_type(
        'CS_TYPE', '客服类型', 'CS Type',
        '客服部门客服类型枚举（在线/外呼/售后）',
        CS_TYPE_ITEMS,
    )


def seed_workstation_type_type():
    """工位类型字典（系统预置，可扩展）。"""
    _seed_type(
        'WORKSTATION_TYPE', '工位类型', 'Workstation Type',
        '客服部门工位类型枚举（坐席/非坐席）',
        WORKSTATION_TYPE_ITEMS,
    )


def seed_campus_roles():
    """幂等创建校招轮岗所需身份角色（RoleV2 系统预置）。

    2026-10-19 新增 HRBP（需求 1-1「增加 HRBP 应用端口」+ 需求 5-1
    「HRBP 进行信息确认」的载体）。此前 HRBP 仅作为 ClassRoom.hrbp 的 FK 字段
    存在，无角色定义 → user_has_campus_role(user, 'HRBP') 恒为 False。

    default_data_scope_type 口径（对齐 resolve_scope L2 scope_resolver.py:117-136）：
      HRBP          DEPT_AND_SUB —— 看本部门及所有下级
      CAMPUS_MENTOR SELF         —— 仅自己创建/被指派的数据（配合 CUSTOM 规则收窄）
      HEAD_TEACHER  SELF         —— 同上
    注：DEPT/DEPT_AND_SUB 依赖用户挂 department_id；未挂部门时按
    scope_resolver 既有逻辑 continue 落到 L3/L4 保守兜底，非本函数引入的行为。
    """
    from apps.core.models_permission_v2 import RoleV2

    RoleV2.objects.update_or_create(
        system_code='recruit', role_code='CAMPUS_MENTOR',
        defaults={
            'role_name': '校园导师',
            'template_code': None,
            'description': '校招轮岗直播间/安排导师',
            'default_data_scope_type': 'SELF',
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
            'default_data_scope_type': 'SELF',
            'is_system': 1,
            'status': 1,
        },
    )
    RoleV2.objects.update_or_create(
        system_code='recruit', role_code='HRBP',
        defaults={
            'role_name': 'HRBP',
            'template_code': None,
            'description': '校招待入职信息确认与审批（需求 5-1/5-5）',
            'default_data_scope_type': 'DEPT_AND_SUB',
            'is_system': 1,
            'status': 1,
        },
    )
    RoleV2.objects.update_or_create(
        system_code='recruit', role_code='CLASS_MONITOR',
        defaults={
            'role_name': '班长',
            'template_code': None,
            'description': '校招班级班长（需求 2-3 删字段后续：仅保留角色，班级不再维护班长）',
            'default_data_scope_type': 'SELF',
            'is_system': 1,
            'status': 1,
        },
    )
