"""按兵哥清单把「受策略管控」资源置位 (strategy_governed=True) (2026-10-20)。

## 背景

动态策略「受限功能」候选区只应展示「受策略管控」的按钮资源。本迁移把该属性
落到库内：全表先归零，再按清单置 True。

## 🔴 清单来源与核对方法（不是拍脑袋写死）

清单由兵哥以「归属模块 / 子模块 / 功能名称」三级给出。核对方式：
1. 从库内导出 `module IN ('demand','position','candidate') AND resource_type='BUTTON'`
   的全部行（21 行），按 (resource_code, resource_name) 逐条比对；
2. 只接受「模块 + 子模块语义 + 功能名称」三者都吻合的行；
3. **找不到对应的功能名一律不入清单**，已在 PR 说明中逐条列出待兵哥裁决，
   绝不用 LIKE 模糊匹配硬凑（会造成「管了不该管的功能」这类静默越权）。

## 已匹配（8 条）

| 模块 / 子模块 | 功能名称 | 资源码 | 库内名称 |
|---|---|---|---|
| 招聘需求 / 招聘需求 | 查看需求 | recruit:demand:list | 需求列表 |
| 招聘需求 / 招聘需求 | 编辑需求 | recruit:demand:edit | 编辑需求 |
| 职位管理 / 职位管理 | 查看职位 | recruit:position:list | 职位列表 |
| 职位管理 / 职位管理 | 编辑职位 | recruit:position:edit | 编辑职位 |
| 候选人管理 / 候选人基础 | 查看候选人 | recruit:candidate:list | 候选人列表 |
| 候选人管理 / 候选人基础 | 编辑简历 | recruit:candidate:edit | 编辑候选人 ⚠️ 见下 |
| 候选人管理 / offer信息 | 创建offer | recruit:candidate:offer:create | 创建Offer |
| 候选人管理 / offer信息 | 发起offer审批 | recruit:candidate:offer:approve | 发起Offer审批 |

⚠️ **「编辑简历」的匹配说明**：库内 module=candidate、子模块为基础信息的操作类
资源只有 `recruit:candidate:edit`（名称「编辑候选人」）。清单写的是「编辑简历」，
两者**名称字面不一致但语义同一**（候选人详情页的简历编辑入口即该码守卫）。
已按语义匹配并在此显式留痕 —— 若兵哥认为「编辑简历」另有所指（例如 settings
模块下 `recruit:settings:scraped_resumes:edit`「编辑简历」，属「我找的简历」页，
不属候选人管理），改本常量即可，回滚路径见 backward。

## 未匹配（已逐条上报，未静默跳过）

清单中以下功能名在 `permission_resources` 表中**查无对应资源**（多数是产品层面的
按钮/动作，从未登记为资源码）：

- 招聘需求：删除需求、编辑画像、开启抢单、批量修改
- 候选人基础：分配职位、转推其他职位、淘汰、放入人才库、推进流程、发送通知
- 简历筛选：邀请筛选简历、撤回筛选邀请、催促筛选
- 面试邀约：标记邀约失败、填写邀约标记
- 面试管理：安排面试、取消面试、修改面试、催促面评、面试邀请、打印面试反馈
  （注：`recruit:interview:schedule`「安排面试」存在但 module=interview，
   不在任何策略模块映射内，故未纳入）
- offer信息：发起背调、重发背调、取消背调、补充背调、添加背调、
  重发offer审批、发送offer、重发offer

⚠️ 其中「转推其他职位 / 淘汰 / 放入人才库 / 推进流程 / 发送通知 / 批量修改」
恰好是 `DataPermissionAction` 动作字典里已有的 key（recommend / eliminate /
talent_pool_add / transition / notify / batch_update）—— 这提示清单可能是
「按模块的动作清单」而非「资源清单」。若兵哥裁决按动作承接，本迁移的置位清单
需整体重做，**不要**直接把动作 key 塞进本常量。

## 设计要点

- **幂等**：整表先置 False 再按清单置 True，重复执行结果一致；清单里的码在库内
  不存在时静默跳过（新库未 seed 属正常，不阻断 migrate），但会打印计数。
- **双向可逆**：backward 整表置回 False（迁移前全表即 False 语义）。
- **不改资源码、不改 status、不碰 role_permission / permission_templates**
  —— 本迁移只写一个新增的展示/筛选属性，不触碰授权面，故无需三处同步。

## 🔴 新库的坑（务必知道）

`migrate` 跑到这里时 `permission_resources` 还是**空表**（资源由 seed_v2_init
在此之后才建出来），所以全新库上本迁移置不到任何行 —— 这是预期行为，日志会打出
「缺失 N 条」告警。新库的置位由 `seed_v2_init.Command.handle` 承担：它 import 了
**同一份** `STRATEGY_GOVERNED_CODES`（本迁移也从那里 import，避免清单两处漂移）。

即两条路径覆盖两种场景：
- **存量库（dev / prod 已 seed）** → 本迁移负责点亮；
- **全新库（CI / 新环境）** → seed 负责点亮。
"""
from django.db import migrations

from apps.core.management.commands.seed_v2_init import STRATEGY_GOVERNED_CODES

SYSTEM = 'recruit'


def forward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')

    # ① 全表归零（幂等基线；同时清理历史脏值）
    reset = Resource.objects.exclude(strategy_governed=False).update(strategy_governed=False)

    # ② 按清单置位
    hit = Resource.objects.filter(resource_code__in=STRATEGY_GOVERNED_CODES).update(
        strategy_governed=True,
    )

    # 自检（软）：清单里库内尚不存在的码（新库未 seed 属正常），只告警不阻断
    existing = set(
        Resource.objects.filter(
            resource_code__in=STRATEGY_GOVERNED_CODES,
        ).values_list('resource_code', flat=True)
    )
    missing = [c for c in STRATEGY_GOVERNED_CODES if c not in existing]
    if missing:
        print(
            f'[0040] 警告：以下受管控资源码在库内不存在（新库未跑 seed_v2_init 属正常）：{missing}'
        )

    print(
        f'[0040] 受策略管控置位：归零 {reset} 条 / 置 True {hit} 条'
        f'（清单 {len(STRATEGY_GOVERNED_CODES)} 条，缺失 {len(missing)} 条）'
    )


def backward(apps, schema_editor):
    """反向：整表置回 False（迁移前全表即 False）。"""
    Resource = apps.get_model('core', 'PermissionResource')
    n = Resource.objects.exclude(strategy_governed=False).update(strategy_governed=False)
    print(f'[0040] 回滚：{n} 条受策略管控标记已清除')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_permissionresource_strategy_governed'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
