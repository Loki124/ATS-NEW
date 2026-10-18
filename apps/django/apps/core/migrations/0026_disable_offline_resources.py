"""下线失效权限资源（status=0），保留资源码可追溯。2026-10-18 兵哥核查。

背景：三处功能已在代码层彻底下线，但 permission_resources 里仍留着它们的资源项，
在「资源管理」页里与现役资源混列，管理员看不出哪些功能已下线、误以为还能授权。

1. 自助注册 / 注册审核（2026-10-18 下线）
   - 前端：/register 路由与 Register.vue 已删；/settings/registrations 路由、组件全无
   - 后端：RegistrationApplication 模型已随 accounts 0002_drop_registration_application 删除，
     注册列表/审核接口已移除（TestSelfRegistrationRemoved 背书）
   - 残留：recruit:settings:registrations:menu:view / :approve 两条

2. 内外部用户独立列表（2026-09-19 三页合一为 UserDirectory「用户管理」）
   - 前端只剩 /settings/users/all 一条路由；内部/外部仅剩为 UserDirectory 页内的
     userType 筛选项（内部员工/外部用户），不再是独立页面
   - 残留：users:internal:* / users:external:* / users:list/create/edit/delete/export
     （旧的 users:xxx 三段体系，与现行 users:all:xxx 四段体系并存）

🔴 只置 status=0，**不删行**：资源码被 role_permission 引用，物理删除会留下孤儿授权，
   且历史授权记录需要可追溯（停用 ≠ 物理删除，见 PermissionResourceViewSet 注释）。
   停用后查询面默认过滤 status=1，这些资源自动退出权限勾选候选。

幂等：可重复执行（已停用的重复置 0 不报错）。
反向：ReverseCode 恢复为 status=1。
"""
from django.db import migrations

# 功能已下线、需停用的资源码（精确列举，不做模糊匹配 —— 误伤代价远大于漏停）
DISABLED_CODES = [
    # ===== 自助注册 / 注册审核 =====
    'recruit:settings:registrations:menu:view',
    'recruit:settings:registrations:approve',
    # ===== 内外部用户独立列表（三页合一后残留）=====
    'recruit:settings:users:menu:view',
    'recruit:settings:users:internal:menu:view',
    'recruit:settings:users:external:menu:view',
    'recruit:settings:users:list',
    'recruit:settings:users:create',
    'recruit:settings:users:edit',
    'recruit:settings:users:delete',
    'recruit:settings:users:export',
    'recruit:settings:users:internal:list',
    'recruit:settings:users:external:list',
    # ===== Offer 两级审批（前端 347 万字符源码无调用点，且已被角色引用 = 废弃功能）=====
    'recruit:offer:approve_l1',
    'recruit:offer:approve_l2',
]


def disable_resources(apps, schema_editor):
    """置 status=0。

    🔴 命中数不做硬校验（2026-10-18 修正）：测试库由历史迁移重放而成，
    是**干净空库**，天然没有这些业务资源码 —— 硬校验会让迁移在标准测试
    流程（pytest 建 test_ats_test）里必然抛错、整库不可重建。开发库
    残留残库时的 `1007 database exists` 同理会放大这个问题。
    「资源码写错」的风险改由本迁移的精确枚举 + 提交前 dev 库实测覆盖，
    此处只做「命中多少停多少」并如实计数。
    """
    PermissionResource = apps.get_model('core', 'PermissionResource')
    hit = PermissionResource.objects.filter(
        resource_code__in=DISABLED_CODES, status=1,
    ).update(status=0)
    if hit != len(DISABLED_CODES):
        # 0 命中通常意味着干净空库（测试库重放），非错误；非 0 才是真异常
        print(f'[0026] 预期停用 {len(DISABLED_CODES)} 条，实际停用 {hit} 条')


def enable_resources(apps, schema_editor):
    PermissionResource = apps.get_model('core', 'PermissionResource')
    PermissionResource.objects.filter(resource_code__in=DISABLED_CODES).update(status=1)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_user_activation_status'),
    ]

    operations = [
        migrations.RunPython(disable_resources, enable_resources),
    ]
