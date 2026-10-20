"""受策略管控置位「第二批」3 条（2026-10-20）—— 扩检索捞回的跨 module 资源。

## 为什么另开 0041 而不是改 0040

0040 已随 7d6fe14f 提交到 main，改动已提交的数据迁移等于让不同环境跑出不同结果
（已跑过 0040 的库不会重跑），属于「迁移不可变」红线。故第二批单独成迁移。

## 背景：第一批的检索漏检

0040 只在 `module IN ('demand','position','candidate')` 里比对兵哥清单，漏掉了
三条**资源真实存在、但落在别的 module 下**的功能。扩大到全表检索（精确名匹配 +
中文关键词 LIKE + 资源码英文片段 REGEXP）后捞回：

| 清单项（模块/子模块） | 资源码 | 实际 module | 库内名 |
|---|---|---|---|
| 候选人管理 / 面试管理 → 安排面试 | `recruit:interview:schedule` | **interview** | 安排面试 |
| 候选人管理 / 候选人基础 → 推进流程 | `recruit:application:advance` | **application** | 推进流程 |
| 候选人管理 / 候选人基础 → 放入人才库 | `recruit:talent_pool:create` | **talent_pool** | 入库 |

⚠️ 「放入人才库」第一批被误判为「只有动作 talent_pool_add、没有资源」—— 库内
`recruit:talent_pool:create` 名字叫「入库」，语义同一，是漏检不是缺失。

## 🔴 关键：这 3 条不改 module 字段

它们的 module 分别是 interview / application / talent_pool，但兵哥清单把它们归在
「候选人管理」（策略模块 candidate）。承接方式**不是**改 module（那会违反规范 R2
「第 2 段 == module 字段」，且要同步五处存储），而是由
`views_dynamic_strategy.STRATEGY_MODULE_RESOURCE_MODULES` 做 1:N 映射：
`candidate -> {candidate, interview, application, talent_pool}`（talent_pool:create 并入
candidate，因为兵哥清单把「放入人才库」列在候选人管理下）；talent 策略模块当前无受管控资源。

🔴 该映射是**新建的独立常量**，不复用 `role_scope_api.DATA_PERM_MODULE_RESOURCE_MODULES`
—— 后者被卡 1.3 `featureGranted` 复用（role_scope_api.py:271-273），把它扩成 1:N
会让「只持有面试资源」的角色在角色数据权限页的「候选人管理」卡片也变
`featureGranted=true`，是波及全量角色的无关行为变更。

## 兵哥裁决（2026-10-20）

- 只承接「能对上现有资源」的，本次**不新建资源码**；
- 全表确实不存在的 27 个功能名（背调 5 项 / 简历筛选 3 项 / 面试邀约 2 项 /
  面试管理 5 项 / offer 3 项 / 候选人基础 4 项 / 招聘需求 4 项）记待办，不在本迁移范围；
- 「编辑简历」维持 `recruit:candidate:edit`（证据：前端
  `web/app/src/directives/permission.ts:11` 把该码标注为「编辑简历」）。

## 设计要点

- 与 0040 同款：整表归零 + 按**最新全量清单**置 True（清单从 seed_v2_init 的
  STRATEGY_GOVERNED_CODES import，天然包含第一批 8 条 + 第二批 3 条 = 11 条）。
  即 0041 执行后结果等价于「11 条全量置位」，先跑 0040 与否都不影响终态。
- 幂等 + 双向可逆：backward 整表置回 False。
- 只写 strategy_governed，不碰资源码 / status / role_permission / permission_templates。
- 新库 migrate 时资源表为空 → 置不到行（预期，打告警），由 seed_v2_init 补置位。
"""
from django.db import migrations

from apps.core.management.commands.seed_v2_init import STRATEGY_GOVERNED_CODES


def forward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')

    # ① 归零（幂等基线，同时吸收 0040 已置的 8 条，避免两份清单叠加出错）
    reset = Resource.objects.exclude(strategy_governed=False).update(strategy_governed=False)

    # ② 按最新全量清单置位（11 条）
    hit = Resource.objects.filter(resource_code__in=STRATEGY_GOVERNED_CODES).update(
        strategy_governed=True,
    )

    existing = set(
        Resource.objects.filter(
            resource_code__in=STRATEGY_GOVERNED_CODES,
        ).values_list('resource_code', flat=True)
    )
    missing = [c for c in STRATEGY_GOVERNED_CODES if c not in existing]
    if missing:
        print(
            f'[0041] 警告：以下受管控资源码在库内不存在（新库未跑 seed_v2_init 属正常）：{missing}'
        )

    print(
        f'[0041] 受策略管控置位（第二批）：归零 {reset} 条 / 置 True {hit} 条'
        f'（全量清单 {len(STRATEGY_GOVERNED_CODES)} 条，缺失 {len(missing)} 条）'
    )


def backward(apps, schema_editor):
    """反向：整表置回 False（迁移前本表全为 False，0040/0041 未执行时的语义）。"""
    Resource = apps.get_model('core', 'PermissionResource')
    n = Resource.objects.exclude(strategy_governed=False).update(strategy_governed=False)
    print(f'[0041] 回滚：{n} 条受策略管控标记已清除')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0040_mark_strategy_governed_resources'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
