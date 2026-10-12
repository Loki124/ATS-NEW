# T5 · UI v2 设计系统收敛 — 诊断与执行报告
> 最后更新：2026-09-07（依据 git 最后提交）

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

### 1.3 执行清单（P1 已按方案 B 执行；P2/P3 已于 §5.1 收口）

| 级别 | 项 | 位置 | 根因 / 约束 | 推荐方案 |
|---|---|---|---|---|
| **P1 ✅ 已执行（方案 B，2026-10-12 已再收敛为 `type="error"`）** | n-button 危险按钮 Ant 红 `#ff4d4f` → `#EF4444` | `ConditionTreeEditor.vue:80`、`AnnouncementSettings.vue:131/202/209`、`ProcessStageEditor.vue:54`、`DataDashboard.vue:236`、`ProcessDetailModal.vue:641`（共 7 处） | n-button `color` prop 走 Naive `parseColor`，**不能**直接 `var()` 化；故值对齐令牌 `#EF4444`（= 当时的 `--c-error`），保留实心红 + 白字外观 | ✅ 已完成真单源：7 处均改为 `type="error"`，继承 `themeOverrides.errorColor`（现 `#C62828`），不再硬编码 |
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

---

## 5. T5.1 残留 + Django 遗留项 收口（2026-09-01）

用户指令「把残留项和遗留项先做掉，再确认推进」。两项均已完成、验证、独立提交。

### 5.1 前端 T5.1 P2/P3（commit 25f609b，4 文件，eslint 0 error）
- **P2** Step1Single/Step1Batch `.replace-banner` 渐变：`var(--bl) → #DBEAFE` 改为 `var(--c-info-bg) → var(--c-info-soft)`。
  - 关键发现：`--bl` / `--b` / `--s` / `--p` / `--d` / `--dl` 在源码中**从未定义**（仅出现在编译产物 dist/ 与 vendor），原渐变实际渲染为 `transparent → #DBEAFE`，属「假绿」。本修复同时消除未定义令牌与硬编码蓝。
- **P3** RuleConfigDrawer：`--primary → --brand`、`--ink/--ink-soft` 去硬编码兜底；ExternalSettings：`--error → --c-error`。

### 5.2 Django 遗留 bugfix（commit f549721，+420/−10）
- 真实 bugfix：`ready()` 进程级钩子在 migrate 前查业务表 → 全新 SQLite 库 `migrate` 崩 `OperationalError: no such table: permission_templates`。
- bootstrap.py 三道闸门（跳过初始化命令 / DB 不可达 / 表未建），仅「表存在但数据缺失」raise `ImproperlyConfigured`；apps.py 仅记录跳过原因不阻断启动。
- 新增 test_bootstrap_startup.py 原稿有 4 处测试缺陷（REQUIRED_TABLES 未定义 / e2e 路径错一级 / test.py 默认关闭守卫致 ready() 短路 / SQLite 事务内 DROP 表 FK 报错），已全部修复。
- 验证：pytest 8 例全绿，含端到端 `test_migrate_on_brand_new_sqlite_db_exits_zero`（全新库 migrate 退出码 0，无 no such table）。

### 5.3 「幽灵令牌」遗留项 —— ✅ 已收敛（2026-10-12 复扫）

**原发现**：`--bl`/`--b`/`--s`/`--p`/`--d`/`--dl` 等跨 6 个文件大量使用（ApplyPositionSelector / CheckBanner / Step1*/Step2Assign / AsyncResult 的 `.pfill.*`、`.nbar.*`、`.cb.*`），源码未定义 → 运行时解析为初始值（透明/无背景）。属「假绿」类缺陷。

**复扫结论**：已全部定义，不再是幽灵令牌。

| 项 | 结果 |
|---|---|
| 扫描范围 | `src/` 下 **171** 个 `.vue`/`.css` 文件 |
| 统计 | 引用 **182** 个令牌，定义 **214** 个 |
| 幽灵令牌 | **12** 处残留，逐个核对后**均无活跃高危项** |

**12 处残留分类**（逐个打开确认）：

| 类别 | 数量 | 说明 |
|---|---|---|
| 有 fallback | 7 | `var(--n-border-color, …)`、`var(--cat-tint, …)`、`var(--n-text-color-3, …)` 等，降级安全 |
| 已修复 + 注释留痕 | 4 | `--pc`→`--brand-fg`（CompanyBrand）、`--border`→`--g2`（EntryConditionCard）、`--shadow-elev`→`--shadow-elevated`（EntryRuleEditModal）、`--color-border`→`--glass-border`（glass.css），各处均已注明「原 X 未定义，声明会被丢弃」 |
| 误报：Naive UI 运行时变量 | 1 | `index.css:50` `var(--n-color)` —— 由 Naive UI 在运行时注入，非源码定义，**不应改** |

> ⚠️ **扫描器局限**：本核查基于源码静态匹配，**无法识别运行时注入的 CSS 变量**（如 Naive UI 的 `--n-*`、UnoCSS 的 `--un-*`）。这类命中需人工判断，不宜自动化删除。

### 5.4 新增关联遗留：文字对比度专项（2026-10-12）

本轮全站文字对比度治理与本文件同属「令牌收敛」，一并记录：

| 项 | 详见 |
|---|---|
| 令牌规范与选阶规则 | `frontend-DESIGN.md` §2 / §2.5 / §2.6 |
| 合规矩阵与验收状态 | `UI_COMPLIANCE_SELFCHECK.md` §2.1、R-03 / R-05 / R-08 |
| `R-109` 复算结论 | `accessibility-and-gating-diagnosis.md` §5 |
| 未收口项 | 见下方 §5.5 |

### 5.5 遗留项（2026-10-12 运行时回归后）

静态扫描（按 CSS 源码匹配）报 0 FAIL，但**运行时逐元素实测**发现了静态方法覆盖不到的类别：

| # | 遗留项 | 实测 | 归属 | 处置 |
|---|---|---|---|---|
| 1 | **JS 内联样式的颜色字符串** —— `statusColor()` 返回 `var(--c-info)` 等主色，用作 22px/600 统计数字 | 2.15–3.98:1 | `OfferList.vue`、`InvitationCenter.vue` | ✅ **本轮已修**（改 `-deep` 阶） |
| 2 | `background: var(--brand)` + 文字前景 —— 实底应用选阶后的 `--brand-button` | 4.47:1 → 6.16:1 | 10 文件 12 处 | ✅ **本轮已修**（批量改） |
| 3 | **Naive UI Badge 数字** —— error 底 `#EF4444` + 白字 | 3.76:1 → **5.62:1** | `App.vue` 的 `themeOverrides` | ✅ **已修**（2026-10-12）：`errorColor` `#EF4444` → `#C62828`；详见 §5.6 |
| 4 | Naive placeholder / `n-empty__description` | 1.78:1 | Naive 默认色 | ⏸ 未修：WCAG 对 placeholder 无强制要求，但建议改善 |
| 5 | 侧边栏激活项 `itemTextColorActive: 'var(--brand)'` 等 15 处 | 源码待修（见下方注 1） | `Layout.vue:321-359` | ⏸ 未修：Naive menu `themeOverrides`，需与 #3 一并处理 |
| 6 | 浅色 `--ink-faint` 压 `--g1` | 4.34:1（差 0.16） | `tokens.css` | ✅ **本轮已修**（见下方注 2） |

**注 1（#5 复核，2026-10-12）**：在 `/candidates` 实测，**全页没有任何元素计算出 `rgb(99,102,241)`**（即 `--brand` 未被解析为生效色）。说明 Naive menu 的 `themeOverrides` 对 `'var(--brand)'` 字符串的解析行为与 CSS 上下文不同，实际观感需截图复核后再定性 —— 在拿到确定结论前，**源码 15 处仍按未修对待**，不计入"已达标"。

**注 2（#6 处置，2026-10-12）**：`#64748B` → `#5B6B84`，**白底 4.76→5.41:1、压 `--g1` 4.34→4.94:1、压 `--g2` 4.55→5.17:1**。取值留有余量而非卡线 4.5，且视觉上仍属辅助灰档。
同值同角色的 `--g5`（37 处，含 `AnnouncementList/Detail` 作 `color:`）与 6 个遗留别名 `--n-350/380/400/440/450/500`（50 处）一并对齐，否则只改 `--ink-faint` 会留下 87 处同样的不达标。
运行时复核：`--ink-faint` 直用样本实测 **5.41:1**，三页（`/settings/metrics`、`/candidates`、`/announcements`）截图目视无破损。

**⚠️ 复核方法提醒**：`color: var(--brand)` 的**静态扫描结果为 0 不代表 #5 已修** —— #5 是 `themeOverrides` 里的 JS 字符串，不是 CSS 声明，两者只能分别查。

#### ⚠️ 治理方法论：两类方法的覆盖差异

| 方法 | 能发现 | 发现不了 |
|---|---|---|
| 静态 CSS 扫描（按 `color: var(--x)` 匹配） | `<style>` 块内的声明 | ① JS 里的颜色字符串（`statusColor()`）② 模板内联 `:style` / `color="var(--x)"` |
| 运行时逐元素实测 | 上述全部 + opacity 合成后的真实值 | 受扫描器精度限制：Naive 玻璃层 `backdrop-filter` 会导致背景穿透，产生假阳性 |

> 运行时扫描在本轮报出暗色 127 条 FAIL，但**截图逐页目视确认视觉正常** —— 绝大部分是玻璃层穿透导致的假阳性。**运行时扫描适合"发现线索"，结论必须经截图复核，不可直接当验收依据。**

### 5.6 Naive UI 全局主题覆盖缺口（2026-10-12 实测新发现）

在 `/candidates` 复测时另发现两项**不经过 CSS 令牌、直接来自 Naive 默认值**的文字色。它们与 #3（Badge）、#4（placeholder）同源：**`App.vue` 的 `themeOverrides` 未覆盖到位，Naive 退回自己的默认色**。

**#3 / #7 / #8 已于 2026-10-12 合并为一次 Naive 主题专项修复完毕**（三项同处 `App.vue` 的 `themeOverrides`，不可分三次改同一对象）：

| # | 元素 | 改前实测 | 计算样式（改前） | 根因 | 处置 | 改后实测 |
|---|---|---|---|---|---|---|
| 3 | Naive Badge 数字（红底白字，如侧栏通知「5」） | **3.76:1** | 背景 `rgb(239,68,68)` = `#EF4444` | `themeOverrides.errorColor` 用 `#EF4444`，白字不达 AA | `errorColor` → **`#C62828`** | **5.62:1** ✅ |
| 7 | `n-text` 副标题「管理所有候选人信息…」 | **2.56:1**（22px 常规字重，**不适用大文本豁免**） | `--n-text-color: rgba(148,163,184,1)` = `#94A3B8` | `themeOverrides.textColor3` 浅色值仍是 `#94A3B8`，未随 `--ink-faint` 一起下调 | `textColor3` 浅 `#5B6B84` / 暗 `#93A0B5`（与 `--ink-faint` 同源） | **5.41:1** ✅ |
| 8 | 输入框占位符「在当前页面搜索关键词」 | **1.78:1** | `rgb(194,194,194)` = `#C2C2C2` | Naive placeholder 默认色，**独立于 `textColor3`**，需单独覆盖 | 新增 `common.placeholderColor`（浅 `#5B6B84` / 暗 `#93A0B5`） | **5.41:1** ✅ |

**连带同步**：`--c-error` 令牌由 `#EF4444` → `#C62828`（与 `errorColor` 保持同源，避免令牌/Naive 双源漂移）。7 处 n-button 危险按钮此前已收敛为 `type="error"`，自动继承新值；`--c-error` 的 3 处 CSS 用法（`StatusTag.td-error` / PDF 附件图标 / glass 错误面）均为白字压底，同向改善。

**运行时复核**（`/candidates`，浅/暗双模式截图确认）：
- 徽标计算样式 `background: rgb(198,40,40)` + 白字 → 5.62:1，`#EF4444` 残留 **0 处**
- 三级文字色 `rgb(91,107,132)`（`#5B6B84`）命中 **46 处**（含副标题），`#94A3B8` 作为文字色残留 **0 处**
- 占位符 `#C2C2C2` 残留 **0 处**；`vue-tsc` exit 0、`eslint` 0 error

> ⚠️ **`App.vue` 顶部 `errorColor` 行 / `textColor3` 行 / `placeholderColor` 行三处必须同时改**：只改 `textColor3` 不管 `placeholderColor` 时，placeholder 仍走 Naive 默认 `#C2C2C2`（两者在 Naive 中**不是同一个键**，这是本轮最易踩的坑）。

> ⚠️ **为什么 Naive 侧要单独列**：Naive 的 `themeOverrides` 解析 `var()` 的行为与 CSS 上下文不同（见 §5.5 注 1），所以**"令牌改了"不等于"Naive 组件跟着改了"**。凡是走 `themeOverrides` 传值的颜色，都必须单独实测，不能靠扫描 CSS 令牌推断。
