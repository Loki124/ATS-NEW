# Plan K: 招聘提速-招聘流程 补全

> **Date**: 2026-06-09
> **Branch**: worktree-agent-a5dd8a0f944772516
> **Plan ID**: G38 (PRD #38 招聘流程管理 P0)
> **Prototype**: 3 张原型图 (编辑规则 / 自定义流程 / 配置阶段规则)

---

## 范围

按 3 张原型图, 增量增强招聘流程管理功能. **不删任何已有文件**, 仅在现有基础上加 seed / 测试 / 组件.

### 已有基线 (Plan K 不破坏)

| 文件 | 行数 | 状态 |
|---|---|---|
| `backend/src/routes/recruitment-process.routes.js` | 287 | 已实现 7 个端点 (列表/详情/创建/更新/删除/复制/状态) |
| `backend/src/routes/recruitment-process-stage-link.routes.js` | 已实现 | process stage link CRUD |
| `backend/src/routes/recruitment-stage.routes.js` | 已实现 | 阶段模板库 CRUD |
| `backend/src/routes/recruitment-rule.routes.js` | 275 | 阶段规则/进入条件/自动归档 |
| `frontend/src/pages/settings/RecruitmentProcess.vue` | 236 | 主列表 (新增流程/编辑/复制/删除) |
| `frontend/src/pages/settings/ProcessStageEditor.vue` | 346 | 阶段编辑器 |
| `frontend/src/pages/settings/ProcessStageRules.vue` | 509 | 阶段规则 tabs |
| `frontend/src/pages/settings/RecruitmentStage.vue` | 284 | 全局阶段库 |
| `frontend/src/components/ConditionTreeEditor.vue` | 320 | 3 级嵌套 AND/OR 条件编辑器 |

### 数据库 Models (已有, 不动 schema)

- `RecruitmentProcess` (#275): 含 applicableDepartments/PositionLevels/UserIds/Jobs/validateResumeScore/failPrompt
- `RecruitmentStage` (#323): 全局阶段模板
- `ProcessStageLink` (#353): 流程-阶段关联
- `StageRule` (#1830): 含 autoAdvance*/defaultHandler*/timeLimit/interviewRoundIds
- `EntryCondition` (#1879): 进入条件
- `ConditionItem` (#1910): 条件项 (树形)
- `AutoArchiveRule`: 4 种自动归档规则

---

## Tasks (8 个, 5 commits)

### Task 1: 7 阶段默认流程 seed [commit 4fc9f690]
- 文件: `backend/prisma/seed/recruitment-default-process.seed.js` (126 行)
- 幂等 code: `FSTD` (标准招聘流程)
- 7 阶段: 初评(P001)/ HRBP评估(P010) / 用人经理评估(P011) / 邀约面试(P012) / 联合面试(P013) / 待入职(P014) / 正式录用(P002)
- 默认 stageLimit = 72h
- 重复执行会补齐缺失 link, 不重复创建

### Task 2: StageRule defaultAssignee 字段检查 [无 commit]
- 现有 `StageRule` 已含 `defaultHandlerType / defaultHandlerFields / defaultHandlerUserIds` 3 个字段, 完全覆盖"默认处理人"需求
- **结论**: 无需 schema 变更

### Task 3: 自动化规则 routes + 3 测试 [commit 63c7c3ea]
- 文件: `backend/src/services/__tests__/recruitment-rule-route.test.js` (109 行)
- 测试 9 个用例 (≥3 组):
  - `evaluateConditionTree: ALL matchType` (3 cases - 全满足 / 部分失败 / 空 items)
  - `evaluateConditionTree: ANY matchType` (3 cases - IN 命中 / 全部失败 / STAGE_STATUS)
  - `buildFailedPrompt` (3 cases - 自定义优先 / 空 → null / 默认模板)

### Task 4: ConditionTreeEditor 增强 [commit 91035342]
- 现有编辑器已支持 3 级嵌套 AND/OR
- 增量: 顶部加"表达式模板预览" alert, 自动生成形如 `(1 and 2) or (3 and 4)`
- 文件: `frontend/src/components/ConditionTreeEditor.vue` (38 行新增)

### Task 5: RecruitmentProcess 列表增强 [commit 1d6f4611]
- "新增流程"按钮 → 跳到 CustomRecruitmentProcessModal
- 列: 加"适用部门" (formatDepts 函数)
- 复制 / 启用停用 / 删除 全部已存在 (保留)

### Task 6: CustomRecruitmentProcessModal (最大块) [commit 1d6f4611]
- 文件: `frontend/src/pages/settings/CustomRecruitmentProcessModal.vue` (~530 行)
- 基础信息: 流程名称 / 适用部门 (多选) / 启用 (switch) / 简历评分校验 (switch) / 描述
- 7 阶段 (起/5 中/终): 列表展示, 每行可配 stageLimit + "配置阶段规则" / "配置进入条件" / "删除"(起止不可删)
- 新建模式: 用本地 7 阶段标准模板; 编辑模式: 拉 server link
- 提交: 创建 → 先建 process, 再清默认 link, 重建全部 link; 编辑 → 更新基础信息 + 改 stageLimit

### Task 7: StageRuleConfigModal (嵌套) [commit 1d6f4611]
- 文件: `frontend/src/pages/settings/StageRuleConfigModal.vue` (~510 行)
- 5 个 tabs:
  1. **自动化流转**: autoAdvanceType (5 选项) + autoAdvanceTiming (3 选项) + autoAdvanceDays (1-15)
  2. **默认处理人**: data-table 多行 (数据来源/取值字段/处理规则/启停)
  3. **阶段限时**: data-table 多行 (规则名/条件/动作/启停)
  4. **面试轮次 + 形式**: 复选 (仅 INTERVIEW/INVITATION 类型显示)
  5. **进入条件**: matchType (ALL/ANY) + prompt 必填
- 加载: 用 `listStageRules` + `listEntryConditions` 拉 server
- 提交: 调 `upsertStageRule` + `upsertEntryCondition`

### Task 8: 验证 + 文档
- backend test: 412 pass (+9), 1 pre-existing fail (referral - Plan J 领域)
- frontend vue-tsc: baseline errors (无 node_modules) + 2 个真实错误已修
- 此文件即文档

---

## 偏离

1. **StageRule defaultAssignee**: 现有 `defaultHandlerType/Fields/UserIds` 3 字段已覆盖. **不加**新字段 (避免 schema 迁移).
2. **CustomRecruitmentProcessModal "添加前序阶段" 按钮**: 简化实现 - 取 available 第一个直接加, 不弹选择器 (避免再加一个 modal).
3. **StageRuleConfigModal 默认处理人**: 简化 - 把多行 rules 聚合为 flat `defaultHandlerFields` 提交, 不引入新 JSON 字段.
4. **进入条件编辑**: StageRuleConfigModal 中只暴露 matchType + prompt 必填, 实际 items 用现有 ConditionTreeEditor (Tab 5 后续可接更深的 ConditionTreeEditor, 当前提交会带上已有 items).
5. **种子数据库执行**: 受 worktree 沙盒权限限制, 未直接执行 `node prisma/seed/recruitment-default-process.seed.js`. 文件已就位, 父 agent 落地时会执行.

---

## 已知问题

1. **vue-tsc 误报**: `stages: ref<any[]>` 的 `idx + 1` 推断为 string|number. 改用 `Number(idx) + 1` 兜底.
2. **子阶段 (P010-P014) 非系统默认**: 当前 seed 创建的是 isSystem: false, 可在 RecruitmentStage.vue 列表被停用/删除, 但默认流程的 link 不受影响 (link 自己存 stageId).
3. **字段权限 (Plan J 领域)**: StageRuleConfigModal 没接字段权限. 如需粒度控制, 待 Plan J 落地.

---

## 后续 Plan 接手点

- Plan D (Talent): 候选人列表可加"通过自定义流程"入口
- Plan E (External): 对外接口可暴露 `GET /api/recruitment-processes/standard` (即 FSTD)
- Plan G (Onboarding): 用 CustomProcessModal 选流程
- Plan I (Offer): Offer 模板可绑流程

---

## 验证脚本

```bash
# Backend tests
cd backend && NODE_OPTIONS=--experimental-vm-modules npx jest

# Frontend type check (需 node_modules)
cd frontend && npx vue-tsc --noEmit

# Seed (执行)
cd backend && node prisma/seed/recruitment-default-process.seed.js
```
