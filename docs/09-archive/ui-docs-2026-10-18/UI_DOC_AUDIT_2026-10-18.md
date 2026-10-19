# 前端 UI 设计文档审查报告（2026-10-18）

> 范围：`docs/04-ui/**` + `docs/02-architecture/design.md` + `docs/03-product/data-permission-ui-design.md` + 根目录 `AGENTS.md`
> 审查方式：读原文 + 与真实代码（`web/app/src/styles/tokens.css`、`brand-tokens.mjs`）逐值比对
> 结论：**不适合合并为单一大文档**（理由见 §5），应改为「一主两辅 + 归档」结构。

---

## 1. 文件清单与内容概要

### 1.1 规范类（会直接约束写代码）

| # | 文件 | 体积 | 定位 | 主要内容 |
|---|---|---|---|---|
| A | `AGENTS.md`（**仓库根**） | 40 KB | Agent 可读约束规范，P0/P1/P2 分级 | §1 令牌结构示意、§2 P0 阻断级（R-1xx）、§3 P1 系统级、§4 品牌色 CLI、§5 P2 反模式黑名单、§6 自动化验证、§7 交付自检 |
| B | `docs/04-ui/UI_DESIGN_SPEC.md` | 22 KB | 人类可读设计规范 v2.3 | 设计原则、色彩、排版、间距/圆角/阴影/动效、组件规范、响应式、WCAG AA 基线、Do/Don't、令牌对照表 |
| C | `docs/04-ui/frontend-layout-standard.md` | 16 KB | 布局契约（活文档，2026-10-18 更新） | 页面安全边距、容器/弹窗内边距、栅格与断点、禁止项、校验门禁、迁移清单 |
| D | `docs/04-ui/frontend-DESIGN.md` | 27 KB | 液态玻璃设计系统 | 视觉主题、调色板与角色、排版、组件样式、布局、深度层级、Do/Don't、响应式、AI 提示指南 |
| E | `docs/04-ui/SETTINGS_PAGE_STRUCTURE.md` | 75 KB | 设置页页面结构 v1.0 | 页面外壳、`.page-container`、标题区、KPI/工具条/表格、卡选择决策树、多 tab 看板、弹窗、自检清单 + 8 段修订记录 |
| F | `docs/04-ui/FRONTEND_RULES_CONSOLIDATED.md` | 54 KB | 规则索引（**元文档**） | 19 节：技术栈、目录命名、代码风格、Lint 门禁、类型、组件、样式令牌、状态、路由、API、i18n、测试、A11y、Git 纪律、配置；**§19.1 权威源优先级表** |
| G | `docs/04-ui/UI_RECONCILIATION.md` | 11 KB | 液态玻璃 v2 / 暗色收敛总纲 | 诊断结论、PM 拍板约束、8 阶段路线图、样式替换原则、暗色专项、工程铁律、验收门禁 |

### 1.2 诊断/计划类（历史记录，非规范）

| 文件 | 体积 | 性质 |
|---|---|---|
| `UI_COMPLIANCE_SELFCHECK.md` | 22 KB | 合规审查报告 + 自检矩阵（2026-09） |
| `UI_REMEDIATION_PLAN.md` | 10 KB | P0→P6 整改实施方案 |
| `UI_DARK_MODE_TECHNICAL_PLAN.md` | 48 KB | 暗色修复技术预案 |
| `accessibility-and-gating-diagnosis.md` | 15 KB | A11y 与工程门禁诊断 |
| `UIUX-DIAGNOSIS-2026-09-03.md` | 21 KB | UI/UX 诊断 |
| `T5-design-token-convergence.md` | 19 KB | v2 令牌收敛执行报告 |
| `FRONTEND_ISSUES_AUDIT.md` | 11 KB | 前端问题审计 |
| `UIUX_REVIEW_CAMPUS_CONTROL_2026-08-27.md`、`SETTINGS_PAGE_COMPLIANCE_CHECK.md`、`DEMAND_LIST_REDESIGN.md`、`SETTINGS_LAYOUT_DIAGNOSIS.md`、`PROCESS_MODAL_DIAGNOSIS.md` 等 | 4–14 KB | 专项走查/诊断快照 |

### 1.3 专项规范类（主题独立，保留）

| 文件 | 主题 |
|---|---|
| `NAIVE_UI_PITFALLS.md` | Naive UI 2.44.1 实战坑与库联动反模式 |
| `DROPDOWN_POPOVER_SPEC.md` | 下拉弹窗三层结构与层叠圆角 |
| `USE_TABLE_PAGINATION.md` | 分页统一组件 |
| `MODAL_DIVIDER_CONVENTION.md` | 弹窗分隔线约定 |
| `DATA_DICT_ADD_OBSCURED.md`、`STANDARD_RESUME_SETTINGS.md` | 专项页面规范 |

### 1.4 索引与元文档

| 文件 | 问题 |
|---|---|
| `docs/04-ui/README.md` | 自称「**唯一权威入口**」，列 4 份文档为必读；但第 1 张表已与实际脱节 |
| `docs/04-ui/UI_INDEX.md` | 自称「UI 文档总纲」，另立一套「权威源」（`UI_DESIGN_SPEC` + `UI_RECONCILIATION`），与 README 的权威集合不一致 |
| `docs/04-ui/FRONTEND_RULES_CONSOLIDATED.md` §19.1 | 第三套权威优先级表（AGENTS.md > UI_DESIGN_SPEC > layout-standard > frontend-DESIGN…） |

---

## 2. 冲突点比对

### 2.1 直接冲突（同一事实两种说法，且都「看起来权威」）

| 议题 | `AGENTS.md`（自称唯一权威） | `UI_DESIGN_SPEC.md` | 真实代码 `tokens.css` | 判定 |
|---|---|---|---|---|
| 语义色令牌名 | `--color-success/warning/error/info` | `--c-success/…` | `--c-success`（`--color-*` 命中数 **0**） | 🔴 **AGENTS.md 错**。照它写代码 = 令牌不存在 = 样式静默失效 |
| 错误色值 | `#EF4444` | `#C62828` | `#C62828`（注释：EF4444+白字仅 3.76:1 不达 AA） | 🔴 **AGENTS.md 错**，UI_DESIGN_SPEC 对 |
| 品牌色输入 | `--brand-h: 39.23; --brand-c: 0.1926`（暖橙） | `--brand: #6366F1`（靛紫） | `#6366F1` | 🔴 **AGENTS.md 整段过期**，其"结构示意"是旧暖橙体系 |
| 间距刻度 | `--space-5: 20px`、`--space-10: 40px` | 4/8/12/16/20/24/32/48/64 | `--space-3:8px`、`--space-5:16px`（向下取整，注释写明"只减不增"） | 🔴 **AGENTS.md 错** |
| 页面安全边距 | 未提 | 未提 | `--page-pad-x: var(--space-4)`=**16px** | ⚠️ `frontend-layout-standard.md` §1.1 仍写 **24px**，FRONTEND_RULES §7.3.1b 已自行标注漂移 |
| 暗色切换 | `:root[data-theme='dark']` | `body.dark` | `body.dark`（`tokens.css:260`） | 🔴 **AGENTS.md 错**，切换机制写错会导致暗色整套失效 |
| 动效时长 | `--dur-fast:120ms / --dur-base:220ms` | `160/240/320ms` | `--duration-fast:160 / base:240 / slow:320`，`--dur-*` 仅兼容别名 | 🔴 **AGENTS.md 数值错** |
| 中性色令牌 | `--color-text-primary:#111827` 等 | `--ink:#0F172A` | `--ink` 系 | 🔴 **AGENTS.md 命名与值均错** |

> **核心风险**：`AGENTS.md` 声明「MUST NOT 因外部文档表述不同而改变行为」，却与真实代码大面积矛盾。AI 代理（及照它学习的新人）按它生成的颜色变量、间距、暗色选择器**全部无效**。

### 2.2 表述不一致但可共存

| 议题 | 差异 | 处理建议 |
|---|---|---|
| 派生色公式 | UI_DESIGN_SPEC 用 `color-mix(--brand 80% #fff)`（srgb）；frontend-DESIGN 用 `color-mix(in oklch, var(--brand-600) 75%, #fff)` | 统一为 **oklch**（frontend-DESIGN 给了感知均匀性的技术理由，UI_DESIGN_SPEC 未采纳） |
| 语义色分层 | UI_DESIGN_SPEC 只有主色+soft；frontend-DESIGN 多 `-deep`（文字专用）与 `--on-c-*-deep`（实底前景） | frontend-DESIGN 更完整（补了 AA 对比度），应升为规范 |
| `--g1…--g7` 中性灰阶梯 | 仅 UI_DESIGN_SPEC 有，且注明"逐步替换为语义令牌" | 标注为**过渡期兼容层**，勿当正式 API |
| `.page-title` 规格 | UI_DESIGN_SPEC：26px/700/渐变；`tokens.css` 有 `--text-h1:32px` | 明确"页面主标题 26px"是刻度外的特例，或纳入刻度 |
| 版本号 | README 写"v2.1"，UI_DESIGN_SPEC 标题写"v2.3" | 统一由文件头单一版本号驱动 |

### 2.3 重复冗余（同一内容多处全文复制）

| 内容 | 重复位置 | 重复量 |
|---|---|---|
| 令牌对照表 | `UI_DESIGN_SPEC` §9、`frontend-DESIGN` §2、`AGENTS.md` §1 三处各一份 | ~3 份 |
| 排版刻度表 | `UI_DESIGN_SPEC` §3、`frontend-DESIGN` §3、`AGENTS.md` §1 | 3 份 |
| 间距阶梯 | `UI_DESIGN_SPEC` §4、`frontend-DESIGN`、`frontend-layout-standard`、`AGENTS.md` | 4 份 |
| Do/Don't 清单 | `UI_DESIGN_SPEC` §8、`frontend-DESIGN` §7、`AGENTS.md` §5、`README.md` 强制约束 | 4 份 |
| 暗色基线 | `UI_DESIGN_SPEC`、`UI_DARK_MODE_TECHNICAL_PLAN`、`UI_RECONCILIATION` §五、`AGENTS.md` §4 | 4 份 |
| 目录/命名约定 | `FRONTEND_RULES_CONSOLIDATED` §2 是唯一完整版，但 `AGENTS.md`、`frontend-DESIGN` §9 也各说一部分 | 3 份 |
| 技术栈版本 | `FRONTEND_RULES` §1（vue 3.4 / naive-ui 2.44.1 等）、`AGENTS.md`、`data-permission-ui-design.md` | 3 份 |

### 2.4 未发现冲突的方面

- **命名约定**：PascalCase 组件 / `use*` composable / kebab-case 样式与目录 —— `FRONTEND_RULES` §2 定义完整且与真实目录一致，其他文档未矛盾表述。
- **技术栈选型**：`FRONTEND_RULES` §1 的依赖清单经核对与 `package.json` 一致（含 `naive-ui 2.44.1`、禁子路径导入、npm 而非 pnpm）。
- **`docs/02-architecture/design.md`**：是 `/dashboard` 单页的设计 DNA（2026-08-03），引用 `frontend/src/styles/tokens.css` 路径已失效（现为 `web/app/src/`）。属历史参考，不构成冲突。

---

## 3. 是否适合合并为一份统一标准文档

### 结论：**不适合合并为单一文档**，应做「收敛」而非「合体」。

**理由：**

1. **受众与加载方式不同**。`AGENTS.md` 是 Agent 每次会话自动注入的（须短、须可判定 P0 阻断）；`UI_DESIGN_SPEC` 是人读的设计规范（须含理由、对比度推导、决策上下文）。合成一份会迫使 Agent 每次吞下 40 KB 设计散文 —— 这正是它现在超载的原因。

2. **冲突的性质是"过期"而非"分歧"**。§2.1 的 8 项直接冲突里，7 项是 `AGENTS.md` 单方面与真实代码脱节，正确答案已由代码和 `UI_DESIGN_SPEC` 给出。这类问题不需要"合并"来解决，需要的是**校正 + 停止复制**。

3. **一半文件根本不是规范**。31 份文档中约 17 份是诊断/整改/走查快照（带日期戳、含"本次改动""已修"等时态）。把它们并入规范文档只会引入过期断言 —— 规范应该是稳定契约，不该每季度重写。

4. **合并会放大已有的"三套权威源"问题**。目前 `README.md`、`UI_INDEX.md`、`FRONTEND_RULES §19.1` 各自列了一套权威优先级，已互相不一致。再合成一份而不先废掉这三套索引，只会让"到底谁说了算"更糊。

5. **有活文档机制，不宜静态化**。`/settings/ui-templates`（`settings → 主题外观 → 前端UI模板`）已是运行时范式中心，`frontend-layout-standard.md` 明确要求与它双向同步。合并成一份静态大文档会与该机制脱节。

**但确实需要"统一"的是三件事**（这才是本次审查的真问题）：

| 要统一的 | 现状 | 目标 |
|---|---|---|
| 权威源唯一性 | 3 套互相不一致的优先级声明 | 只留 1 套，写在一处 |
| 令牌值唯一真源 | 4 份文档各抄一份，4 份都在漂移 | 令牌**只由 `tokens.css` 定义**，文档一律只引用不复制数值 |
| 索引唯一性 | README / UI_INDEX / §19.1 三份索引 | 保留 1 份索引 |

---

## 4. 合并（收敛）方案

### 4.1 权威来源裁定

| 层级 | 权威文件 | 说明 |
|---|---|---|
| **L0 真源** | `web/app/src/styles/tokens.css` + `brand-tokens.mjs` | 令牌**唯一**真源。任何文档与其冲突即文档错，无例外 |
| **L1 约束** | `AGENTS.md` | Agent 注入的可判定约束（R-xxx / P0-P2）。**须先校正到与 L0 一致** |
| **L2 人类规范** | `docs/04-ui/UI_DESIGN_SPEC.md` | 设计理由、对比度推导、组件范式 |
| **L3 布局契约** | `docs/04-ui/frontend-layout-standard.md` | 页面/弹窗边距契约（保持活文档） |
| **L4 专项** | `NAIVE_UI_PITFALLS.md` / `DROPDOWN_POPOVER_SPEC.md` / `USE_TABLE_PAGINATION.md` 等 | 主题独立，各自维护 |
| **L5 元信息** | `docs/04-ui/README.md`（唯一索引） | 角色标注 + 权威层级说明；删除 `UI_INDEX.md` 与 `FRONTEND_RULES §19.1` |

> `frontend-DESIGN.md` 的处置：它是 `UI_DESIGN_SPEC` + `UI_RECONCILIATION` 的**上游重复源**，且已在 `FRONTEND_RULES §19.1` 被标"已废弃"。但其中的 `oklch` 派生理由、`-deep` 语义色分层、`--on-*` 实底前景族**比 UI_DESIGN_SPEC 更完整** → **先把这三块搬进 UI_DESIGN_SPEC，再归档该文件**。

### 4.2 逐文件处置清单

**保留并升级（L1–L3）**

| 文件 | 动作 |
|---|---|
| `AGENTS.md` | **校正令牌节**：删掉过期的暖橙 `--brand-h/-c`、`--color-*` 语义色、`#EF4444`、`20px/40px` 间距、`data-theme` 暗色、`120/220ms` 动效；改为「不复制数值，只声明 MUST 走令牌 + 引用 L2 文档」的指针式写法 |
| `UI_DESIGN_SPEC.md` | **升为 L2 唯一人类规范**：并入 `frontend-DESIGN` 的 oklch 派生 + `-deep`/`--on-*` 族；版本号与 README 对齐；补「与 L0 冲突时的裁决规则」 |
| `frontend-layout-standard.md` | 保留为 L3；**修正 §1.1 的 24px → 16px/8px**（真实值），或改为「以 `tokens.css` 为准」不写死数值 |
| `README.md` | 改为唯一索引，删「唯一权威入口」这种与 §19.1/UI_INDEX 打架的措辞 |

**归档（移 `docs/09-archive/`，保留可追溯）**

| 文件 | 理由 |
|---|---|
| `UI_INDEX.md` | 索引职责与 README 重复，且权威集合不一致 |
| `FRONTEND_RULES_CONSOLIDATED.md` | 元文档/规则索引，价值在 §19.1 之外的技术栈与目录约定 —— **先把这部分（§1、§2）搬到 README 或新 `ENGINEERING` 文档，再归档**；§7 样式令牌节整体删除（已漂移，且违反"不复制数值"） |
| `frontend-DESIGN.md` | 上游重复源；有效内容已搬入 UI_DESIGN_SPEC |
| `UI_RECONCILIATION.md` | 2026-08 收敛已完成，属历史路线图 |
| `T5-design-token-convergence.md` | 执行报告 |
| 全部 17 份诊断/整改/走查快照 | 历史记录，非规范 |

**不动**

- `NAIVE_UI_PITFALLS.md`、`DROPDOWN_POPOVER_SPEC.md`、`USE_TABLE_PAGINATION.md`、`MODAL_DIVIDER_CONVENTION.md` 等专项规范
- `docs/02-architecture/design.md`、`docs/03-product/data-permission-ui-design.md`（模块级设计文档，非全站规范）

### 4.3 目标文档建议章节结构

`UI_DESIGN_SPEC.md`（L2）合并后骨架：

```
1. 文档定位与权威层级     ← 新增：声明 L0>L1>L2>L3>L4 优先级与裁决规则
2. 设计原则
3. 色彩系统
   3.1 品牌色（oklch 派生 + 九阶生成，禁止手写）
   3.2 语义色（主色 / -deep 文字专用 / -soft 浅底 / --on-* 实底前景）
   3.3 中性墨色与边框
   3.4 玻璃表面与模糊层级
   3.5 z-index 比例尺
4. 排版（字体族 / 刻度 / 字重四档 / tabular-nums）
5. 间距 · 圆角 · 阴影 · 动效   ← 数值一律写「见 tokens.css §N」，不复制
6. 组件规范（按钮 / 输入 / 选择 / 表格 / 标签 / 弹窗 …）
7. 布局契约摘要            ← 只摘要，细则指向 frontend-layout-standard.md
8. 响应式断点
9. 可访问性基线（WCAG 2.1 AA）
10. Do / Don't
11. 令牌索引（按用途反查 → tokens.css 行号，不抄数值）
12. 变更记录
```

### 4.4 迁移步骤（建议顺序）

| 步 | 动作 | 验证方式 |
|---|---|---|
| 1 | **校正 `AGENTS.md` 令牌节**（最高优先，因为 AI 每次会话都读它） | 逐项对照 `tokens.css`；`grep -c "\-\-color-success" tokens.css` = 0 的名字不得出现在 AGENTS.md |
| 2 | `frontend-DESIGN.md` 的 oklch / `-deep` / `--on-*` 搬入 `UI_DESIGN_SPEC.md` | 两文件标题结构 diff，确认无遗漏章节 |
| 3 | 修 `frontend-layout-standard.md` §1.1 边距数值（24px → 实际值） | 与 `tokens.css:198-201` 逐值比对 |
| 4 | `FRONTEND_RULES_CONSOLIDATED.md` §1 技术栈 + §2 命名约定搬入 `README.md`，§7 样式令牌节删除 | 目录结构与真实 `src/` 核对 |
| 5 | `README.md` 改写为唯一索引，写入 L0–L5 层级 | 全文搜索「唯一权威」应只剩一处 |
| 6 | 归档批次：`UI_INDEX.md`、`frontend-DESIGN.md`、`UI_RECONCILIATION.md`、`T5-*` + 17 份诊断快照 → `docs/09-archive/ui-docs-2026-10-18/` | 各归档文件顶部加一行 `> 已归档于 2026-10-18，权威内容见 …` |
| 7 | ✅ **已完成** — 新增 `scripts/token-doc-audit.mjs` + `npm run tokens:audit` + CI job `token-docs`（见 §4.5） | 注入不存在的令牌名，门禁应失败 → 已验证捕获 |
| 8 | 更新 `docs/06-runbook/ENGINEERING_RULES.md` 记入本次裁决结论 | — |

### 4.5 防回归门禁：`scripts/token-doc-audit.mjs`（已落地）

**要防的问题**：文档复制令牌数值 → 随代码演进漂移 → AI 照文档写的 CSS 变量不存在 → 静默失效。AGENTS.md 的 `--color-success`/`#EF4444`/`data-theme` 即是此模式的产物（校正前共 19 个悬空令牌名）。

**真源**：`web/app/src/styles/tokens.css` + `brand-tokens.css`（R-214 生成物，git 未忽略）。

**两项检查**：

| 检查 | 判定 | 级别 |
|---|---|---|
| 悬空引用 | 文档出现的令牌名在真源中不存在 | ❌ |
| 数值漂移 | 文档写了 `--name: <值>` 且与真源不一致 | ❌ |

**误报抑制**（实测踩坑后逐条加固，每条都有实例）：

| 规则 | 抑制场景 | 实例 |
|---|---|---|
| `CLI_FLAGS` | 命令行参数 | `--coverage` `--max-warnings` `--ci` |
| `FOREIGN_PREFIX` | 第三方库内部变量 | Naive UI `--n-option-*`、UnoCSS `--un-*` |
| `BEM_CLASS` | CSS 类名修饰符 | `btn--loading` `.section--elements` |
| `RUNTIME_SKIN_EXAMPLE` | 白标换肤示例（另一套输入色） | `[data-brand='a'] { --brand-h: 217 }` |
| `NEGATIVE_EXAMPLE` | 刻意写的反例警示 | 「MUST NOT 使用 `--text-xs`，本项目不存在」 |
| `NON_DECLARATION` | 比较式 / 占位反例 | `--z-dropdown:1000 < --z-modal:1200`、`var(--x, #hex)` |
| 值归一化 | hex 大小写、`rgba()` 内空格、裸数字↔px | `#5050D1`≡`#5050d1`；`4`≡`4px` |

**覆盖范围**：`AGENTS.md` + `docs/04-ui/*.md`，跳过带日期戳的历史快照（纯诊断记录，不含规范承诺）。共 26 份、约 400 处令牌引用。

**当前状态**：存量 **66 个真实问题**待清（`StageRuleConfigModal_验收Spec` 19 个凭空发明的令牌如 `--shadow-modal`/`--radius-xs`/`--z-popup`；`T5-design-token-convergence` 29 个；`UI_RECONCILIATION`/`UI_REMEDIATION_PLAN`/`frontend-DESIGN` 各有数值漂移）。故 CI job 暂设 `continue-on-error: true`，待迁移步骤 ②~⑥ 清零后摘除转为强制阻断。

**自反能力已验证**：向 `USE_TABLE_PAGINATION.md` 注入 `--color-success` 与 `--definitely-not-a-real-token`，门禁精确报出 L98 两处悬空并 `exit 1`；随后完整还原文件。

---

## 5. 一页速查

- 🔴 **最紧急**：`AGENTS.md` 令牌节与真实代码大面积矛盾（语义色名/错误色/品牌色体系/间距/暗色选择器/动效），而它自称"唯一权威、MUST NOT 因外部文档不同而改行为" → Agent 照此写代码会静默失效。
- 🟡 3 套权威优先级声明互相不一致（README / UI_INDEX / FRONTEND_RULES §19.1）。
- 🟡 令牌数值在 4 份文档里各抄一份、4 份都在漂移（间距、页面边距、动效均已发生）。
- ✅ 技术栈与命名约定无冲突，`FRONTEND_RULES` §1/§2 与真实 `package.json`、`src/` 一致 —— 归档前须保留。
- **决策：不合体，做收敛。** 令牌真源回 `tokens.css`，`AGENTS.md` 只留可判定约束并去掉数值复制，`UI_DESIGN_SPEC` 收编上游重复内容，索引归一为 1 份，17 份历史快照归档。
