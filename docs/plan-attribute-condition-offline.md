# 方案：数据权限「属性条件」下线

> 决策依据：`docs/EVAL_ARCH_指标行级过滤源_可行性评估.md` §2.3
> 「context 右值三形态：静态 / 上下文变量 / **属性条件（下线保留代码）**」
> 状态：**已实施**（前端入口关闭 + 存量只读兼容），后端能力保留未删。

---

## 1. 为什么下线

架构评估已给出结论：属性条件（复用指标目录标量字段做行级过滤）与「维度 + 布尔组合」
的能力边界重叠，且它是 `filterable` 红线的唯一 UI 消费入口 —— 红线本身是**后端性能护栏**，
不该由一个已下线的功能来决定是否保留。

同时它带来真实的认知负担：管理员要理解「关系维度」和「属性条件」两套平行词汇，
而绝大多数权限诉求（我的部门 / 我的管理单元 / 某几个负责人）用维度组合即可表达。

## 2. 下线策略：关入口、保兼容、不删代码

| 层 | 处理 | 理由 |
|---|---|---|
| 前端新建入口 | **移除**「属性条件」单选项（条件类型切换器只剩「关系维度」） | 停止新建能力 |
| 前端存量渲染 | `attr-body` 改为**只读**（全部控件 `disabled`），并加「属性条件 · 已下线」标签 | 存量规则仍需可读、可原样回传 |
| 前端处理器 | 删除 8 个已无调用方的处理器（`onKindChange` / `onAttrFieldChange` / `onAttrOperatorChange` / `onAttrEnumSingle` / `onAttrEnumMulti` / `onAttrNumber` / `onAttrRangeMin` / `onAttrRangeMax`） | 下线的实际收口 |
| 后端编译器 | **保留** `expr_compiler` 的 `kind='attribute'` 分支 | 存量快照仍靠它执行 |
| 后端保存校验 | **保留** `validate_scope_payload` 对 attribute 的接受 | 往返回传不得被 400 拒绝 |
| 后端字段目录 | **保留** `attribute_fields` + `metrics.0031 filterable` | filterable 是后端性能红线，与是否暴露 UI 无关 |
| `newCondition('attribute')` | **保留分支**，加注释说明仅供存量反序列化 | 防止存量条件被降级成 relationship 造成静默损坏 |

## 3. 关键决策：为什么不直接删干净

1. **往返编辑会静默损坏已保存规则**：前端若不认识 `kind='attribute'`，读回后回传会把
   属性条件降级成关系维度 → 已保存的权限规则语义被改写。在权限系统里这是事故级缺陷。
2. **"看不见但仍在生效" 比 "看不见且不能新建" 更危险**：管理员必须能看到存量规则
   确实还在生效（只读 + 已下线标签），否则会去排查不存在的权限问题。

因此本方案是**能力下线**，不是**代码清除**。清除需等确认无任何环境存在存量属性条件后再单独做。

## 4. 实施前核查（硬证据）

在真实 DB 上核查（`manage.py shell`，`DataPermissionRule` 扫描）：

- ROW 规则（scope_payload 非空）共 **4** 条，其中 `kind='attribute'` 条件 **0** 条
  → 当前环境**无存量属性条件**，下线无数据风险；
- 但仍按「保兼容」实施，以覆盖其他环境（生产 / 测试库）可能有存量的情况。

后端能力核查（同一 shell）：

| 检查 | 结果 |
|---|---|
| `compile_scope_q(payload, 'demand')` 编译 attribute 条件 | `<Q: (AND: ('state', 'RECRUITING'))>` —— 仍可编译 |
| `validate_scope_payload(...attribute...)` | `None` —— 仍接受（回传不会被拒） |
| `attribute_fields_for('demand', SCENARIO_ROW_FILTER)` | 6 个字段，目录仍可达 |

## 5. 改动清单

| 文件 | 改动 |
|---|---|
| `web/app/src/components/role/RuleConfigModal.vue` | 移除属性条件单选项；存量改只读 + 已下线标签；删 8 个处理器并留下线说明注释 |
| `web/app/src/composables/useRoleDataPerm.ts` | `newCondition` 的 attribute 分支加注释（仅存量反序列化） |
| `web/app/src/locales/domains/zh-CN.DATA_PERM_ZH.ts` | 新增 `dataperm.modal.deprecatedBadge` = 已下线 |
| `web/app/src/locales/domains/en-US.DATA_PERM_EN.ts` | 新增 `dataperm.modal.deprecatedBadge` = Deprecated |
| `web/app/src/composables/__tests__/useRoleDataPerm.dynamic.test.ts` | 新增「属性条件下线（存量兼容）」4 用例 |

后端**零改动**。

## 6. 回归测试

新增用例锁定两条不可回退的性质：

1. `newCondition()` 默认产出关系维度条件（无属性条件新建入口）；
2. 显式 `newCondition('attribute')` 仍可构造，且存量属性条件预览句仍可读、未被降级。

## 7. 验证结果

| 项 | 结果 |
|---|---|
| `vue-tsc --noEmit` | 0 error |
| `eslint`（5 个改动文件） | 0 问题 |
| `vitest`（dynamic + PermissionManagement） | 22 passed |
| 后端 `compile_scope_q` / `validate_scope_payload` / `attribute_fields_for` | 编译/校验/目录 三项均仍可用 |

## 8. 后续（可选，需另行立项）

若要**彻底清除**代码，需先在所有环境确认无存量属性条件，再删除：

- 后端 `expr_compiler` 的 attribute 分支 + `attribute_fields.py`；
- `metrics.0031 filterable` 字段 —— **注意**：不能删，它是后端防全表扫描的红线，
  与指标行级过滤能力绑定而非与属性条件 UI 绑定。

建议本次不做，留待观察期后再评估。
