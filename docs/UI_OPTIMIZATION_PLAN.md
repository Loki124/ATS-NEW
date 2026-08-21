# ATS-NEW UI 优化方案（液态玻璃改造清单 · 研发交接）

> 设计系统架构师 Diana · 2026-08-21 · 依赖 `web/app/DESIGN.md` + `docs/UI_DIAGNOSIS.md`
> 目标：将全站统一到液态玻璃单系统，消除 4 套视觉/3 套品牌色。
> 交付节奏：**先全局（token+主题），后逐页**，灰度推进，CampusControl 作对齐样板。

## 0. 决策点（已确认）
- **品牌色**：默认 `--brand:#6366F1`（靛紫，对齐 CampusControl 新方向）。**支持运行时自定义换肤**——`--brand` 为唯一输入，hover/pressed/dark 经 `color-mix` 自动派生，渐变端可覆盖（见 DESIGN.md §2）。腾讯 CI 备选 `#0052D9`（仅改一处）。
- **暗色模式**：**已纳入交付**。变量集见 DESIGN.md §2 Dark Mode Token Set，切 `body.dark` 一键生效，组件 CSS 不变；开关持久化 + 跟随系统。
- **本文档与 DESIGN.md 经 PM 确认后，转研发团队执行。**

## 1. 改造路线图（4 阶段）

### 阶段 1 — 统一事实来源（全局生效，低风险）【P0】
| 项 | 动作 | 文件 | 产出 |
|---|---|---|---|
| 1.1 | `tokens.css` 增补玻璃/极光/品牌变量（§2 全量），保留旧 orange 变量做过渡别名 | `src/styles/tokens.css` | 单一 token 源 |
| 1.2 | `uno.config.ts`：`primary` 改 `#6366F1`，`shortcuts.card-base` 改 `.glass-card`；删金色 | `uno.config.ts` | UnoCSS 全站联动 |
| 1.3 | `App.vue` `themeOverrides`：primary→`#6366F1`、文字色 `#fff`、圆角统一 `16px`；Card/Button/Input/Modal/Drawer 加玻璃 override | `src/App.vue` | Naive 组件玻璃化 |
| 1.4 | 新增 `src/styles/glass.css`：`.glass-panel/.glass-card/.glass-input/.btn-*`/极光层 `.app-aurora` + `::before` 高光 | `src/styles/glass.css`（main.ts 引入） | 玻璃原子类 |
| 1.5 | `Layout.vue`：侧栏/顶栏改玻璃材质，激活态金→品牌靛；删 `#1f2937` 实底 | `src/pages/Layout.vue` | 框架入系统 |
| 1.6 | **自定义品牌色运行时机制**：`tokens.css` 以 `--brand` 为唯一输入 + `color-mix` 派生 hover/pressed/dark；提供运行时注入点（设置接口 / `:root` style 设 `--brand`，白标换肤）；`App.vue` `themeOverrides` 由同一品牌值 JS 计算 | `src/styles/tokens.css` + `src/App.vue` + 设置页入口 | 换肤能力 |
| 1.7 | **暗色模式**：`tokens.css` 增补 `body.dark` 变量集（DESIGN.md §2）；主题开关（持久化 + 跟随系统 `prefers-color-scheme`） | `src/styles/tokens.css` + `App.vue`/设置 | 暗色交付 |

> 阶段 1 完成后，**全站颜色与基础组件立即统一**，白标换肤与暗色一键生效，无需改业务页。

### 阶段 2 — 应用框架与底色【P0】
| 项 | 动作 | 文件 |
|---|---|---|
| 2.1 | `body`/根容器挂 `.app-aurora` 极光背景（z-index 0），内容区透明（替换 `#f9fafb`） | `App.vue`/`App.css` |
| 2.2 | 全局搜索 Modal、通知、用户下拉：包玻璃容器 + 模态毛玻璃遮罩 | `Layout.vue` + `components/common/GlobalSearch.vue` |
| 2.3 | `Login.vue`：金渐变底 → 极光底；登录卡改有效玻璃（透出极光） | `src/pages/Login.vue` |

### 阶段 3 — 业务页迁移（逐页替换白卡→玻璃）【P1】
| 批次 | 范围 | 关键改动 |
|---|---|---|
| 3.1 工作台 | `Dashboard.vue` + `components/dashboard/*` | `n-card` → `.glass-card`；StatBar 多色(amber/rose/sky/emerald)→品牌+语义四态；Hero 标题改渐变文字 |
| 3.2 校招管控对齐 | `CampusControl.vue` | 已玻璃，仅把散落硬编码（`blur(20px)`/`#6366F1`/`18px`）抽成 `tokens.css` 变量，消除魔法值 |
| 3.3 设置中心 | `pages/settings/*`（25+ 页） | `card-base`/白卡 → `.glass-card`；表单/表格玻璃化 |
| 3.4 招聘主流程 | candidate/interview/offer/onboarding/invitation/resume/scraped/* | 列表表格玻璃化、Modal/Drawer 玻璃、按钮 `.btn-*` |
| 3.5 列表通用件 | `components/common/*`（StatusTag/ScorePanel/ResumeCard…） | tag/卡片玻璃化、状态色走语义变量 |

> 每批遵循「先对齐 DESIGN.md 再批量替换」，不动 Naive 组件源码。

### 阶段 4 — 响应式 / 动效 / 收口【P2】
| 项 | 动作 | 文件 |
|---|---|---|
| 4.1 | KPI 行 `repeat(4,1fr)` → `4→2→1` 响应式；全站统一断点 | `CampusControl.vue` + `tokens.css` |
| 4.2 | 动效统一 `var(--ease-out)`，删 `transition:all .2s` 裸值 | 各组件 |
| 4.3 | 全量补 `-webkit-backdrop-filter` 前缀巡检 | grep 扫描 |
| 4.4 | 删历史颜色：金 `#FBCE5B`、橙 `oklch(...45)` 别名与残留硬编码 | 全局 grep |
| 4.5 | ~~暗色模式~~（已并入阶段 1.7，此处删除） | — |

## 2. 落地约束（给研发）
- **单一事实来源**：任何新颜色/模糊/圆角必须先进 `tokens.css`，组件只引用变量。
- **不改 Naive 源码**：仅通过 `themeOverrides` + 包裹 class 调整，避免升级冲突。
- **灰度顺序**：CampusControl(已有玻璃) 先对齐规范 → 再外推，降低返工。
- **退路**：玻璃底统一保留不透明兜底，`backdrop-filter` 失效也不崩可读性。
- **验证**：每阶段跑 `npm run build` + 关键页视觉回归（截图对比）；`vue-tsc` 零错误。

## 3. 工作量估算（人日，粗）
| 阶段 | 估时 | 风险 |
|---|---|---|
| 1 全局 token+主题 | 1.5d | 低（配置层） |
| 2 框架+底色 | 1d | 低 |
| 3 业务页迁移 | 4–6d | 中（页多，需逐批回归） |
| 4 响应/动效/收口 | 1.5d | 低 |
| 合计 | ~8–10d | — |

## 4. 验收清单（转研发后回检）
- [ ] 全站仅 1 个品牌色（金/橙硬编码数为 0）。
- [ ] 所有 `n-card`/容器为玻璃材质，无扁平白卡与玻璃混排。
- [ ] 侧栏/顶栏为玻璃，激活态为品牌靛（非金）。
- [ ] **自定义换肤**：运行时改 `--brand` 全站联动（含 Naive 组件与原生渐变），无残留硬编码色。
- [ ] **暗色模式**：`body.dark` 切换正常，玻璃呈拉丝深玻璃；开关可持久化 + 跟随系统。
- [ ] KPI/卡片在 ≤768px 正常折叠。
- [ ] `backdrop-filter` 全带 `-webkit-` 前缀。
- [ ] 视觉回归：Login/工作台/校招管控/设置 四处（浅色 + 暗色）风格一致。
