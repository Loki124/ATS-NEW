"""PermissionResource 增加 sub_module（子模块展示名）+ 候选人管理 10 条置位 (2026-10-21)。

## 背景

资源管理页「子模块」列原纯靠资源码结构推导（五段码第 4 段为 menu 时，第 3 段即
子模块代码、menu 资源名去「菜单」后缀即中文名，见前端 buildSubModuleIndex）。
candidate 的码是四段（recruit:candidate:create / recruit:candidate:offer:create），
无子模块段亦无 menu 锚点，推导恒为「—」。

本迁移为 PermissionResource 加显式 `sub_module` 列，并按兵哥清单给候选人管理的
10 条资源置位：6 条基础操作 →「基础功能」，4 条 offer 操作 →「offer管理」。

## 🔴 双路径（同 strategy_governed / core.0040 模式）

- **存量库（dev / prod 已 seed）** → 本迁移负责置位；
- **全新库（migrate 时 permission_resources 还是空表）** → 本迁移置不到任何行
  （日志打「缺失 N 条」告警，属预期），由 seed_v2_init.Command.handle 承担 ——
  两侧 import **同一份** `RESOURCE_SUB_MODULES`，防清单两处漂移。

## 设计要点

- 只写展示属性，**不改资源码 / status / 授权面**（role_permission、
  permission_templates 均不碰），无需「五处同步」。
- backward 置回 NULL（新增列的原初状态）。
- 幂等：置位为无条件 update，重复执行结果一致。
- 清单核对方式：逐码对照资源管理页实际数据（recruit:candidate:* 共 10 条启用码，
  与截图红框一一对应），不做 LIKE 模糊硬凑。
"""
from django.db import migrations, models

from apps.core.management.commands.seed_v2_init import RESOURCE_SUB_MODULES


def forward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')

    hit = 0
    for code, sub in RESOURCE_SUB_MODULES.items():
        hit += Resource.objects.filter(resource_code=code).update(sub_module=sub)

    # 自检（软）：清单里库内尚不存在的码（新库未 seed 属正常），只告警不阻断
    existing = set(
        Resource.objects.filter(
            resource_code__in=RESOURCE_SUB_MODULES,
        ).values_list('resource_code', flat=True)
    )
    missing = [c for c in RESOURCE_SUB_MODULES if c not in existing]
    if missing:
        print(
            f'[0046] 警告：以下资源码在库内不存在（新库未跑 seed_v2_init 属正常）：{missing}'
        )

    print(
        f'[0046] sub_module 置位：{hit} 条'
        f'（清单 {len(RESOURCE_SUB_MODULES)} 条，缺失 {len(missing)} 条）'
    )


def backward(apps, schema_editor):
    """反向：清单内置回 NULL（新增列的原初状态）。"""
    Resource = apps.get_model('core', 'PermissionResource')
    n = Resource.objects.filter(
        resource_code__in=RESOURCE_SUB_MODULES,
    ).update(sub_module=None)
    print(f'[0046] 回滚：{n} 条 sub_module 已清空')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0045_rename_campus_control_to_campus'),
    ]

    operations = [
        migrations.AddField(
            model_name='permissionresource',
            name='sub_module',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='子模块'),
        ),
        migrations.RunPython(forward, backward),
    ]
