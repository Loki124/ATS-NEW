"""标记停用资源 + 兜底重申停用状态（2026-10-19）。

## 背景（暴露的真问题）

1. **「明确标记停用」从未落地**：`test_resource_code_convention.py::test_r9_disabled_resources_prefixed`
   注释声称「0030 迁移按库内 status=0 动态打 `[已停用]` 前缀」，但 0030 实为
   `0030_split_campus_resource_codes`（校招码拆分），**前缀迁移根本不存在**。
   后端 grep `[已停用]` 零命中 → 停用资源在管理界面/授权界面没有可见的「已停用」标记，
   test_r9 仅因测试库为空（无 status=0 资源）而假绿。

2. **种子复活风险**：`seed_v2_init.py` 对 RESOURCES 内每条码无条件 `update_or_create(status=1)`。
   一旦某停用码被误写回 seed，下次跑种子即被强制启用 —— 0026/0029 的停用动作被无声推翻。

## 本迁移职责

- **A. 兜底重申**：将 0026 + 0029 的全部已知停用码重申为 `status=0`（幂等；仅更新当前仍为 1 的，
  clean 测试库命中 0 属正常）。这是「最后一道保险」，确保无论迁移/种子执行顺序如何，
  已知下线功能始终处于停用态。
- **B. 加前缀**：给所有 `status=0` 且名称尚无 `[已停用] ` 前缀的资源名补前缀（幂等）。
  使管理员在权限配置/资源管理界面一眼区分「在用 / 已停用」，消除「误导性遗留状态」。
  注意：`[已停用]` 前缀**只来自本迁移**（按库内 status=0 动态打），不来自 seed
  （seed 全量 status=1，见 test_r10）—— 否则重跑 seed 会前缀叠加。

## 处置哲学（与 0026/0029 一致）

- **仅 `status=0`，绝不物理删除**：资源码被 role_permission 引用，物理删除留孤儿授权；
  且历史授权需可追溯（停用 ≠ 删除）。
- **保留 role_permission 残留授权行**：本迁移不动授权行。禁用资源的「不可授权」由
  `permission_check.has_perm` 的停用码缓存拦截（status=0 永拒授权），残留行因此变为
  **惰性 + 已明确标记**，既消除「误导性」，又保留可追溯性，且可逆。
- **反向**：剥离 `[已停用] ` 前缀（纯展示回滚）；并把已知停用码恢复为 `status=1`
  （与 0026/0029 backward 一致），便于在确实需要复活某功能时单独正向处理。
"""
import importlib

from django.db import migrations

DISABLED_PREFIX = '[已停用] '

# 已知停用码汇总 = 0026（内外部用户/注册审核/Offer 两级审批）+ 0029（DB 孤儿 + 僵尸按钮）。
# 用 importlib 加载数字前缀模块，避免硬编码漂移；二者即便被反向迁移也不影响常量引用。
_m26 = importlib.import_module('apps.core.migrations.0026_disable_offline_resources')
_m29 = importlib.import_module('apps.core.migrations.0029_disable_zombie_resources')
KNOWN_DISABLED_CODES = (
    list(_m26.DISABLED_CODES)
    + list(_m29.ORPHAN_CODES)
    + list(_m29.ZOMBIE_BUTTON_CODES)
)


def _reassert_disabled(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    hit = Resource.objects.filter(
        resource_code__in=KNOWN_DISABLED_CODES, status=1,
    ).update(status=0)
    if hit:
        print(f'[0033] 兜底重申停用 {hit} 条（seed/顺序复活拦截）')
    return hit


def _add_prefix(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    n = 0
    for r in Resource.objects.filter(status=0):
        if not r.resource_name.startswith(DISABLED_PREFIX):
            r.resource_name = DISABLED_PREFIX + r.resource_name
            r.save(update_fields=['resource_name'])
            n += 1
    if n:
        print(f'[0033] 为 {n} 条停用资源补 [已停用] 前缀')
    return n


def _strip_prefix(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    n = 0
    for r in Resource.objects.filter(resource_name__startswith=DISABLED_PREFIX):
        r.resource_name = r.resource_name[len(DISABLED_PREFIX):]
        r.save(update_fields=['resource_name'])
        n += 1
    if n:
        print(f'[0033] 回滚剥离 {n} 条 [已停用] 前缀')
    return n


def forward(apps, schema_editor):
    _reassert_disabled(apps, schema_editor)
    _add_prefix(apps, schema_editor)


def backward(apps, schema_editor):
    _strip_prefix(apps, schema_editor)
    Resource = apps.get_model('core', 'PermissionResource')
    Resource.objects.filter(
        resource_code__in=KNOWN_DISABLED_CODES,
    ).update(status=1)
    print('[0033] 已知停用码恢复 status=1（如需真正复活请单独正向处置）')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_dynamic_strategy'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
