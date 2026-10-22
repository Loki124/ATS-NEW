"""停用「用户组管理」资源码（2026-10-21 兵哥：用户组管理功能整体下线）。

## 背景

「用户组管理」（前端占位页 `/settings/user-groups`）是一块从未落地的占位功能：
seed 里只登记了一条菜单码 `recruit:settings:user_groups:menu:view`，后端**无任何端点**
消费它，前端只渲染 `Placeholder.vue`。本次随「用户管理迁入权限管理」一并彻底删除。

删除清单（前后端同步）：
  - 前端路由 `web/app/src/router/index.ts` → `/settings/user-groups` 已删
  - 前端菜单 `web/app/src/pages/settings/SettingsLayout.vue` → 子项已删
  - 前端菜单守卫登记 `web/app/src/utils/permissionMenu.ts` → 登记已删
  - i18n `pages.settings.SettingsLayout.s17` → 已删
  - seed 真源 `seed_v2_init.RESOURCES` → 本码已删（防种子复活）

## 处置哲学（与 core.0026 / 0029 / 0033 一致）

- **仅 `status=0`，绝不物理删除**：资源码被 `role_permission` 引用，物理删除会留下孤儿授权；
  且历史授权记录需可追溯（停用 ≠ 删除）。
- **保留 `role_permission` 残留授权行**：停用码由 `permission_check.has_perm` 永拒授权
  （status=0 即不可授予/不可通过），残留行因此变为**惰性 + 已明确标记**，既消除误导性，
  又保留可追溯性与可逆性。
- **补 `[已停用] ` 前缀**：资源表无独立的「是否停用」展示字段，管理员在资源管理/权限配置
  界面只能从名称辨识；前缀让「在用 / 已停用」一眼可分（规范 R9 由
  `test_resource_code_convention.py::test_r9_disabled_resources_prefixed` 锁死）。
- **从权限模板中剔除该码**：模板 `permission_codes` 是 JSON 数组存码字面量，迁移/级联
  都不覆盖它；模板继续引用一个已停用码，会让该身份**静默持有**一条永不生效的授权
  （与 core.0030 对 mou 族的处理同款）。
"""
from django.db import migrations

DISABLED_PREFIX = '[已停用] '

# 用户组管理菜单码（仅此一条；该功能无任何后端端点消费）
USER_GROUPS_CODES = [
    'recruit:settings:user_groups:menu:view',
]

assert len(set(USER_GROUPS_CODES)) == len(USER_GROUPS_CODES), '清单内存在重复资源码'


def _disable(apps, codes):
    """置 status=0（幂等：已停用的重复置 0 不报错）。"""
    Resource = apps.get_model('core', 'PermissionResource')
    return Resource.objects.filter(
        resource_code__in=codes, status=1,
    ).update(status=0)


def _add_prefix(apps, codes):
    """给本批停用资源补 `[已停用] ` 前缀（幂等：已带前缀的不叠加）。"""
    Resource = apps.get_model('core', 'PermissionResource')
    n = 0
    for r in Resource.objects.filter(resource_code__in=codes, status=0).exclude(
        resource_name__startswith=DISABLED_PREFIX
    ):
        r.resource_name = DISABLED_PREFIX + r.resource_name
        r.save(update_fields=['resource_name'])
        n += 1
    return n


def _strip_from_templates(apps, codes):
    """从权限模板 permission_codes 中剔除已停用码（防模板持有死码）。"""
    Template = apps.get_model('core', 'PermissionTemplate')
    n = 0
    for t in Template.objects.all():
        current = list(t.permission_codes or [])
        kept = [c for c in current if c not in codes]
        if len(kept) != len(current):
            t.permission_codes = kept
            t.save(update_fields=['permission_codes'])
            n += 1
    return n


def forward(apps, schema_editor):
    hit = _disable(apps, USER_GROUPS_CODES)
    # 只计数告警不硬校验：新库/测试库是历史迁移重放的干净空库，天然无这些业务码，
    # 硬校验会让 pytest 建库即失败（core.0026 曾踩过这个坑）。
    if hit != len(USER_GROUPS_CODES):
        print(
            f'[0050] 预期停用 {len(USER_GROUPS_CODES)} 条，实际 {hit} 条'
            f'（新库或已部分停用属正常）'
        )
    prefixed = _add_prefix(apps, USER_GROUPS_CODES)
    if prefixed:
        print(f'[0050] 为 {prefixed} 条停用资源补 [已停用] 前缀')
    tpl = _strip_from_templates(apps, USER_GROUPS_CODES)
    if tpl:
        print(f'[0050] 从 {tpl} 个权限模板中剔除已停用码')


def backward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    # 剥离前缀（纯展示回滚）+ 恢复启用态。
    # 前缀删除无法用 SQL 表达（Concat 只能拼接），故在 Python 侧逐行处理。
    for r in Resource.objects.filter(resource_code__in=USER_GROUPS_CODES):
        if r.resource_name.startswith(DISABLED_PREFIX):
            r.resource_name = r.resource_name[len(DISABLED_PREFIX):]
            r.save(update_fields=['resource_name'])
    Resource.objects.filter(
        resource_code__in=USER_GROUPS_CODES,
    ).update(status=1)
    print('[0050] 用户组管理资源码恢复 status=1（如需真正复活请单独正向处置）')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_alter_rolepermissionv2_resource_code_and_more'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
