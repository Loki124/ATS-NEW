# T5 · UI v2 设计系统收敛 — 诊断与执行报告

> 分支：`workbuddy/main-5f436540` ｜ 日期：2026-08-31 ｜ 范围：前端视觉语言/品牌色散落点收敛
> 依据：`AGENTS.md` v2.0.0（X-05 禁硬编码颜色 / X-13 禁手写品牌色 / R-214 令牌由 CLI 生成）+ `brand-tokens.mjs`

## 0. 结论先行

前端视觉语言**实际已高度收敛**，并非前序假设的"4 套视觉语言 + 3 套品牌色"重度碎片化。已建立完整的品牌色单源链路：

```
brand-tokens.mjs (OKLCH #6366F1 → 50..900 色阶 + 自动选阶)
   └─ tokens.css        (@import './brand-tokens.css')
        └─ index.css     --primary-color: var(--brand)   ← 单源代理
             └─ stores/theme.ts  setBrand() → document 写 --brand (runtime 换肤)
```

`glass.css` 经审计**零硬编码 6 位 hex**；`App.vue` 的 Naive `themeOverrides` 语义色已带同步注释（line 53）。

本次 T5 收敛清掉的是**最后一类散落的 Ant Design 调色板硬编码**（状态色映射 + 内联样式），并校准令牌系统门禁。剩余发散点已列入执行清单（§1.3），其中 n-button 危险按钮因 Naive `parseColor` 约束需视觉确认，本次未擅自改动。

---

## 1. 诊断发现

### 1.1 已收敛（无需改动）

| 项 | 证据 | 状态 |
|---|---|---|
| 品牌色单源链路 | `brand-tokens.css` → `tokens.css:1 @import` → `index.css:6 --primary-color` → `theme.ts` | ✅ |
| `glass.css` 零硬编码 | 全量审计（grep 6位hex）：仅 `var(--brand)` / `var(--glass-*)` / `var(--glow-brand)` + rgba | ✅ |
| Naive 语义色同步注释 | `App.vue:53` `// === 语义色（与 tokens.css §4 语义色同步...）===` | ✅ |
| campus 模块独立语言 | 审计 `CampusControl.vue`：未发现 aceternity / 金色 `#FBCE5B` 独立语言 | ✅ |

### 1.2 本次已修复（17 处 Ant 调色板泄漏 → `--c-*` 令牌）

映射原则：Ant 调色板值替换为语义/强调令牌；消费侧均为浏览器原生 `:style` 绑定或 `n-icon :color`（后者 `ReferralCenter.vue:208` 已用 `var(--brand)` 喂 `n-icon`，证明 `var()` 可用）。

| # | 文件:行 | 原值 (Ant) | 令牌 | 语义 | 消费侧 |
|---|---|---|---|---|---|
| 1 | `referral/ReferralCenter.vue:203` | `#1890ff` | `var(--c-info)` | 蓝 | `n-icon :color` + `:style` |
| 2 | `referral/ReferralCenter.vue:204` | `#52c41a` | `var(--c-success)` | 绿 | 同上 |
| 3 | `referral/ReferralCenter.vue:205` | `#722ed1` | `var(--c-purple)` | 紫 | 同上 |
| 4 | `referral/ReferralCenter.vue:206` | `#fa8c16` | `var(--c-warning)` | 橙 | 同上 |
| 5 | `referral/ReferralCenter.vue:207` | `#13c2c2` | `var(--c-cyan)` | 青 | 同上 |
| 6 | `invitation/InvitationCenter.vue:144` | `#fa8c16` | `var(--c-warning)` | 橙 | `:style` (line 22) |
| 7 | `invitation/InvitationCenter.vue:144` | `#1890ff` | `var(--c-info)` | 蓝 | 同上 |
| 8 | `invitation/InvitationCenter.vue:144` | `#722ed1` | `var(--c-purple)` | 紫 | 同上 |
| 9 | `invitation/InvitationCenter.vue:145` | `#52c41a` | `var(--c-success)` | 绿 | 同上 |
| 10 | `invitation/InvitationCenter.vue:145` | `#f5222d` | `var(--c-error)` | 红 | 同上 |
| 11 | `invitation/InvitationCenter.vue:145` | `#fa8c16` | `var(--c-warning)` | 橙 | 同上 |
| 12 | `invitation/InvitationCenter.vue:147` | `#8c8c8c`(回退) | `var(--n-400)` | 中性 | 同上 |
| 13 | `components/DraggableList.vue:103` | `#1890ff` | `var(--c-info)` | 蓝 | CSS `box-shadow` |
| 14 | `settings/ProcessDetailModal.vue:943` | `#2080f0` | `var(--c-info)` | 蓝 | `:style` (line 753) |
| 15 | `settings/ProcessDetailModal.vue:944` | `#f0a020` | `var(--c-warning)` | 橙 | 同上 |
| 16 | `settings/ProcessDetailModal.vue:945` | `#722ed1` | `var(--c-purple)` | 紫 | 同上 |
| 17 | `settings/ProcessDetailModal.vue:946` | `#18a058` | `var(--c-success)` | 绿 | 同上 |
| 18 | `settings/ProcessDetailModal.vue:947` | `#0090ba` | `var(--c-cyan)` | 青 | 同上 |
| 19 | `settings/ProcessDetailModal.vue:1704` | `#666`(回退) | `var(--n-400)` | 中性 | 同上 |
| 20 | `pages/Login.vue:237` | `#16a34a` + `rgba(22,163,74,.18/.35)` | `var(--c-success)` + `color-mix(...)` | 成功绿 | Naive `message` 内联 `containerStyle` |

> 注：`DemandList.vue:771/861/912/1071` 的 `#1890ff → var(--c-info)` 仅出现在**注释**中（历史修复标注），非活跃代码，未改动。

### 1.3 执行清单（P1 已按方案 B 执行；P2/P3 待执行）

| 级别 | 项 | 位置 | 根因 / 约束 | 推荐方案 |
|---|---|---|---|---|
| **P1 ✅ 已执行（方案 B）** | n-button 危险按钮 Ant 红 `#ff4d4f` → `#EF4444` | `ConditionTreeEditor.vue:80`、`AnnouncementSettings.vue:131/202/209`、`ProcessStageEditor.vue:54`、`DataDashboard.vue:236`、`ProcessDetailModal.vue:641`（共 7 处） | n-button `color` prop 走 Naive `parseColor`，**不能**直接 `var()` 化；故值对齐令牌 `#EF4444`（= `--c-error`），保留实心红 + 白字外观 | 真单源（`type="error"`）留作 T5.1 视觉评审项 |
| P2 | 渐变端点硬编码浅蓝 `#DBEAFE` | `addCandidate/Step1Single.vue:482`、`Step1Batch.vue:476` | 渐变 `linear-gradient(90deg, var(--bl) 0%, #DBEAFE 100%)` 第二端点非令牌 | 引入浅色品牌 tint 令牌（如 `--brand-50` 或新增 `--brand-tint`）替换；需确认视觉 |
| P3 | 防御性 fallback 含硬编码 hex | `RuleConfigDrawer.vue:334-335/353` `var(--primary,#6366f1)`、`ExternalSettings.vue:1048` `var(--error,#d03050)` | `--primary` / `--error` 非当前定义令牌，靠字面量兜底 | 改为 `var(--brand)` / `var(--c-error)`（无 fallback 或 fallback 用令牌值） |
| — 留 | Naive `#ffffff` 表面字面量 | `App.vue:63-66` cardColor/modalColor 等 | 属 Naive 第二视觉语言的 surface 覆盖，已文档化（暗色 `transparent` 联动 glass.css） | 维持现状，纳入架构注释 |

---

## 2. 验证证据（硬证据）

| 项 | 命令 / 方法 | 结果 |
|---|---|---|
| 令牌对比度门禁 | `node brand-tokens.mjs --brand "#6366F1" --ci` | ✅ 通过（button=600, ratio=6.16:1, exit 0） |
| 改动文件 lint | `eslint` 5 个改动文件 | ✅ **0 error**；15 warning 均为 `ProcessDetailModal.vue` 模板既有属性排序（line 286–371，非本次改动） |
| 活跃 Ant 泄漏复核 | grep 全部 Ant 调色板 hex（`.vue`） | ✅ 活跃 0 处（仅 `DemandList.vue` 4 行注释） |
| n-button Ant 红复核 | grep `#ff4d4f`（`.vue`） | ✅ 0 处（7 → 0，已统一为 `#EF4444`） |

> ⚠️ 运行时渲染（暗色下 `--c-purple`/`--c-cyan` 显色、Login `--c-success` color-mix 生效）属 `[R]` 项，需浏览器 `getComputedStyle` 硬证据，本次未做（无渲染器），建议你在 dev server 目测确认。

---

## 3. 提交范围（本次 commit）

分两次提交（均仅含 T5 前端令牌收敛，未带入工作区中遗留的 Django 改动 `apps/django/apps/core/apps.py`、`bootstrap.py`、`test_bootstrap_startup.py`，属前序 T3 工作，另行处理）：
- **commit 1（令牌收敛）**：5 文件 — DraggableList / Login / InvitationCenter / ReferralCenter / ProcessDetailModal（status 色映射 → `--c-*`）
- **commit 2（方案 B：n-button Ant 红 → `#EF4444`）**：5 文件 — ConditionTreeEditor / AnnouncementSettings / ProcessStageEditor / DataDashboard / ProcessDetailModal

```
web/app/src/components/DraggableList.vue
web/app/src/pages/Login.vue
web/app/src/pages/invitation/InvitationCenter.vue
web/app/src/pages/referral/ReferralCenter.vue
web/app/src/pages/settings/ProcessDetailModal.vue
web/app/src/components/ConditionTreeEditor.vue
web/app/src/pages/settings/AnnouncementSettings.vue
web/app/src/pages/settings/ProcessStageEditor.vue
web/app/src/pages/settings/DataDashboard.vue
```

## 4. 后续（T5.1）

- **全量 X-05 hex 审计**：本次仅覆盖 Ant 调色板 + 语义/品牌硬编码。rgba 阴影、渐变、`#ffffff` 等中性字面量需更大范围审计（建议 `stylelint` 配 `color-no-hex` 规则做 CI 门禁，兜底 X-05）。
- 执行 §1.3 P2–P3 收敛；P1 真单源（`type="error"`）待视觉评审后决定是否替换。
