"""停用两族僵尸资源码（2026-10-18）。

## 第一族：10 条 DB 孤儿资源（seed 真源里已不存在，功能早已下线）

`recruit:settings:data-permission:*` 与 `recruit:settings:user-management:*`

下线铁证（git 提交，非「零引用」这种弱证据）：
  - `84db5095`（2026-09-17）refactor: 字段权限收敛为 field_acl 单一系统
    → 删除 /settings/data-permission 路由、DataPermissionSettings.vue（321 行）、
      api/data-permission.ts（105 行），并把 seed 里 data-permission:* 5 条
      **整体替换为** field_acl:* 5 条。
  - `20484c1f`（2026-09-17）refactor: 合并团队成员管理→内部员工，数据权限管理→字段权限
    → 删除 UserManagement.vue（586 行）与 user-management 路由/菜单项，
      commit message 原文「能力由用户目录『全部用户』覆盖」。

现存的 field_acl / users:all 链路是活的，本迁移不动它们。

## 第二族：4 条纯僵尸按钮码

`recruit:settings:permissions:{create,edit,delete,export}`

与 `recruit:role:{create,edit,delete}` 名称含义完全重复（都是「新增/编辑/删除角色」），
但：
  - `recruit:role:*` 是**后端在役鉴权真源**：`views_permission_v2.py:109`
    `permission_required = 'recruit:role:list'` + `permissions_v2.py:133-149`
    按 action 自动派生 create/edit/delete；停用会让角色管理页对所有非超管 403。
  - `recruit:settings:permissions:{create,edit,delete,export}` 全仓**零消费**
    （前端无 v-permission / 后端无 permission_required），是 2026-09-18
    「角色管理」更名为「身份管理」后遗留的旧路径码。

🔴 处置一律 `status=0` 而非物理删除：
   - 这 4 条 menu:view 已被真实角色授权（实测 role_permission 有值），
     删行会留下孤儿授权 + 丢历史可追溯性；
   - 停用后默认查询面 `status=1` 会自动过滤，退出权限配置页的勾选候选，
     但历史授权记录仍可审计。
"""
from django.db import migrations

# 第一族：功能已下线的孤儿资源（DB-only，seed 真源里不存在）。
# 🔴 注意：core.0028 已把它们从连字符段名改为下划线段名
#    （data-permission → data_permission / user-management → user_management）。
#    故此处必须用改名后的下划线码，否则 0028 改名后这 10 条会残留为「启用态下划线僵尸」。
ORPHAN_CODES = [
    'recruit:settings:data_permission:menu:view',
    'recruit:settings:data_permission:create',
    'recruit:settings:data_permission:edit',
    'recruit:settings:data_permission:delete',
    'recruit:settings:data_permission:export',
    'recruit:settings:user_management:menu:view',
    'recruit:settings:user_management:create',
    'recruit:settings:user_management:edit',
    'recruit:settings:user_management:delete',
    'recruit:settings:user_management:export',
]

# 第二族：语义重复但零消费的僵尸按钮码
# ⚠️ 刻意不含 `recruit:settings:permissions:menu:view` —— 它被前端
#    web/app/src/utils/permissionMenu.ts:59 用于 /settings/permissions 菜单守卫，是活的。
ZOMBIE_BUTTON_CODES = [
    'recruit:settings:permissions:create',
    'recruit:settings:permissions:edit',
    'recruit:settings:permissions:delete',
    'recruit:settings:permissions:export',
]

ALL_CODES = ORPHAN_CODES + ZOMBIE_BUTTON_CODES

assert len(set(ALL_CODES)) == len(ALL_CODES), '清单内存在重复资源码'


def _disable(apps, codes):
    Resource = apps.get_model('core', 'PermissionResource')
    return Resource.objects.filter(
        resource_code__in=codes, status=1,
    ).update(status=0)


def forward(apps, schema_editor):
    hit = _disable(apps, ALL_CODES)
    # 只计数告警不硬校验：新库/测试库是历史迁移重放的干净空库，天然无这些业务码，
    # 硬校验会让 pytest 建库即失败（0026 曾踩过这个坑）。
    if hit != len(ALL_CODES):
        print(
            f'[0029] 预期停用 {len(ALL_CODES)} 条，实际 {hit} 条'
            f'（新库或已部分停用属正常）'
        )


def backward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    Resource.objects.filter(resource_code__in=ALL_CODES).update(status=1)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_unify_resource_code_segments'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
