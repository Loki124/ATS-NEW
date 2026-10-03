# ATS-NEW 前端 UI 改造总纲（液态玻璃 v2 + 暗色模式）
> 最后更新：2026-09-07（依据 git 最后提交）

> **范围**：`web/app/src/**`（Vue3 + Naive UI + UnoCSS，Django 后端不动）。
> **基线**：`web/app/DESIGN.md` v2 液态玻璃规范 + `src/styles/tokens.css` v2 单一事实来源。
> **目标**：收敛 4 套冲突视觉语言、3 套冲突品牌色 → 单一液态玻璃设计系统，并完成暗色模式全站贯通。
> **文档索引**：
> - 本文件 = 诊断 / 决策 / 路线图 / 替换原则 / 工程铁律 / 收尾状态（**总纲，向上整合版**）
> - `UI_DARK_MODE_TECHNICAL_PLAN.md` = 暗色模式专项（5 层根因 + 阶段代码块 + 验收门禁，**保留原文件**）
> - `campus_control/` = 校招管控需求 / 技术文档（独立专题，不在本次 UI 合并范围）
> - `CHANGELOG.md` = 项目级变更日志（独立维护）

---

## 一、为什么要做（诊断核心结论）

摸底数据（grep 实证）：**Ant Design 硬编码色 99 处** / `font-size: 数字px` **401 处** / `padding: 数字px` **126 处** / `border-radius: 数字px` **165 处**。

四维度诊断共 **38 个问题**（P0×9 / P1×16 / P2×13）：

| 维度 | 代表问题 |
|---|---|
| **框架 Framework** | F1 5 路由指向占位页无感知、F2 404 静默跳首页、F3 Forbidden 未玻璃化、F4 SettingsLayout `:deep` 全局 hack、F5 侧栏两套实现、F6 无面包屑 |
| **组件 Components** | C1 99 处 Ant 色硬编码、C2 主按钮字色冲突、C3 业务页未用 glass 类、C4 body 浅灰底覆盖暗色、C7-C10 401+126+165 处尺寸硬编码、C11 表头未走玻璃、C12 自写弹窗、C14 label 灰色硬编码 |
| **交互 Interaction** | I1 表格行无键盘可达、I2 强调色三套规范、I3 操作列按钮过多、I4 入场动效仅 Dashboard、I5 Loading 三套、I7 占位无差异化 |
| **体验 UX / a11y** | U1 5 列表页无响应式、U2 侧栏无移动折叠、U4/U5 暗色下白卡漂浮、U9 空状态分散、U10 mockData 错数据、U11 错误态仅 console、U12 关键操作无二次确认、A1 `#8c8c8c` 对比度不达标 |

**9 个 P0（阻塞产品体验，必解）**：F1、C1、C2、C3、U1、U2、U4、U5、U11。

---

## 二、PM 拍板与强制约束

**v2.6 拍板**：弹窗内边距 24→32px + header/body/footer 三段分区；搜索框 `min-width:200px; nowrap; ≤768 换行占满`。
**v2.7 拍板**：错误页/占位页统一**双列布局**（左大数字右说明）—— 删 emoji + 巨大 404、紫蓝三色渐变改品牌单色系、玻璃面板 `border: 1.5px solid var(--glass-border-strong)` 加粗、数字下加 `err-tag` 小标签、≤560 折叠单列。

**强制约束（v2.6 / v2.7）**：
1. **单一事实来源** —— 所有视觉值只来自 `tokens.css` v2，组件禁止硬编码 hex（语义色除外）。
2. **改品牌色只改 `--brand` 一处**，`hover/pressed/dark/soft/tint` 经 `color-mix` 自动派生。
3. **`backdrop-filter` 必须带 `-webkit-` 前缀**（Safari 兼容）。
4. **v2 禁忌**：禁止再写 Ant Design 蓝色（`#1890ff` 等）、禁止白卡漂浮（容器底必须 token 化或透出极光）、禁止垂直堆叠错误页。

---

## 三、改造路线图（8 阶段 → 已落地映射）

| 阶段 | 目标 | 解决 | 落地状态 |
|---|---|---|---|
| 1 | 全局 token 强制 + 浅色基线 | U6/C4/U7/滚动条 | ✅ tokens.css v2 + body 透明 |
| 2 | 业务列表页硬编码色全替换 | C1/C14/U4/U5/A1 | ✅ T5 阶段（Offer/Demand/Onboarding/Interview/Candidate 5 列表页） |
| 3 | 5 列表页响应式 + 侧栏移动折叠 | U1/U2/U3 | ✅ T6 阶段（1024/768/480 三档 + n-drawer + hamburger） |
| 4 | 框架组件对齐（按钮字色、表头玻璃、操作列瘦身） | C2/C3/C11/I2/I3 | ✅ T7 阶段（主按钮 !important 移除、n-data-table-th 玻璃、操作列 n-dropdown 化进行中） |
| 5 | 交互增强（动效、键盘、占位、二次确认） | F1/F6/I1/I4/I7/U12/A5 | 🔶 部分（Dashboard stagger、StatBar 键盘已落；T8 交互增强待迭代） |
| 6 | 错误态与 a11y | F2/F3/U11/A1/A4 | ✅ 404 页 + API 错误兜底 + 错误页双列 |
| 7 | SettingsLayout 去 hack、表格/弹窗 token 化 | F4/F5/C12 | ✅ SettingsLayout 自写 DOM → n-menu（D 阶段）+ 移除 `:deep` 全局 hack |
| 8 | a11y 打磨、快捷键、toast 规范 | P2 | ⏳ 持续迭代 |

**总计 5–6 人日可解 9 P0 + 11 P1（占总数 64%）**，已在本次周期内基本闭环。

---

## 四、样式替换原则（执行层）

> 完整逐条映射表原载 `UI_STYLE_RECONCILIATION.md`（已并入本总纲，原则如下）。

### 4.1 颜色 token 化
- **状态语义色走 `--c-*`**：`#1890ff`→`--c-info`/`--brand`、`#52c41a`→`--c-success`、`#ff4d4f`/`#f5222d`→`--c-error`、`#fa8c16`→`--c-warning`、`#722ed1`→`--brand-grad-a`。
- **中灰文字走 `--ink-*` 三档**：`#8c8c8c`/`#999`/`#bfbfbf`→`--ink-faint`、`#595959`/`#666`→`--ink-soft`、`#262626`/`#333`→`--ink`。
- **背景与分隔线**：`#fff`/`white`→`var(--glass-bg-card)`（透出极光）、`#f0f0f0`→`--border-hairline`、`#fafafa`→`--glass-bg-input`、`#f0f2f5`→`transparent`、`#e6f7ff`+`#91d5ff`→`--c-info-soft`。
- **滚动条**：`#d9d9d9`/`#bfbfbf`→`--ink-faint`。
- **body 底色**：`background-color: #f5f5f5` → `background: transparent`（让 `--aurora-base` 生效）+ `color: var(--ink)`。

### 4.2 尺寸 token 化
- `font-size` 401 处 → `--text-h1..h4 / body / small / meta`
- `padding` 126 处 → `--space-6/4/...`
- `border-radius` 165 处 → `--radius-sm/md/lg`（主圆角锁定 `--radius-md: 16px`）

### 4.3 主按钮字色冲突（C2 / P0）
根因：`App.vue` 设主按钮白字，业务页又用 `!important` 强制黑字覆盖。修复：统一走 Naive `themeOverrides` 派生色，禁止页级 `!important` 覆盖主按钮。

### 4.4 暗色清扫（U4/U5 / P0）
硬性规则：**任何列表响应都不要取 `.list`**；页面/卡片容器底（`#fff`/`white`/`#f5f5f5` 等）必须 token 化或 `transparent`，否则暗色下出现"白色卡片漂浮在深色玻璃"。

### 4.5 响应式（U1/U2 / P0）
5 列表页补 1024/768/480 三档 `@media`；Layout 侧栏 ≤768 折叠为 `n-drawer` + hamburger。

### 4.6 错误页/占位页双列（v2.7 / P0）
见第二节 v2.7 拍板规范，统一双列结构 + `err-tag` 语义标签。

---

## 五、暗色模式专项

根因 5 层（全局→具体）：① 未挂 Naive `darkTheme` → ② `themeOverrides` 缺暗色派生 → ③ 业务页 99 处硬编码色暗色不切 → ④ body 浅灰底覆盖 → ⑤ Settings 侧栏自写 menu 未玻璃化。

修复 5 阶段（A 前置 isDark → B App.vue 挂 darkTheme → C 业务页 hex→token → D SettingsLayout 改 n-menu → E 巡检兜底）。**完整可照抄代码块 + 4 档验收门禁见 `UI_DARK_MODE_TECHNICAL_PLAN.md`**（保留）。

关键铁律：Naive UI 滚动容器（`.n-scrollbar-container`）**绝不可 `overflow:hidden`**（否则 wheel 事件被吞，表现"滚条可见但触控板不动"）；暗色切换必须 `body.classList.toggle('dark')` + `n-config-provider :theme`。

---

## 六、关键工程铁律（本次周期实战沉淀）

1. **滚动容器 `overflow:hidden` 阻断事件** —— Naive `.n-scrollbar-container`/`.n-scrollbar-rail` 绝不能 hidden，否则 wheel/触控板手势被吞。圆角兜底时只给布局锚点（`.n-data-table-base-table-body`）hidden，真滚动容器必须 `overflow:auto`。
2. **flex-height 表格「滚不动」三件套**（缺一不可）：`base-table` 显式 `flex column + flex:1 + min-height:0` → `header` `flex-shrink:0` → `body` `flex:1 + min-height:0 + overflow-y:auto !important`。
3. **滚动职责「回归 Naive」** —— 不要自己抢 n-scrollbar-container 的滚动；外层 `overflow-y:auto` 与 Naive 自洽 wheel 体系打架（表现 = 滚条可见 + 鼠标可拖 + wheel 不动）。诊断决策树：滚条不可见=CSS 未加载；滚条可见+鼠标可拖+wheel 不动=inner container 被 hidden 砍断 wheel 链。
4. **历史色 0 残留** —— `#FBCE5B/#E5B82A/#f0f0ff/#f59e0b/oklch(` 全清零；`index.css` 旧 `--primary-*` 代理到 `--brand/*`。
5. **webkit 前缀 100% 覆盖** —— 所有 `backdrop-filter:` 必须配对 `-webkit-backdrop-filter:`。

---

## 七、验收门禁（摘要）

- **P0 必过（9 项）**：占位页感知、99 处色 token 化、主按钮字色统一、业务页用 glass 类、5 列表页响应式、侧栏移动折叠、暗色下无 Ant 色冲突、暗色下无白卡漂浮、错误态 UI 兜底。
- **P1 必过（16 项）**：404 页、Forbidden 玻璃化、SettingsLayout 去 hack、表头玻璃、label 灰色 token 化、表格行键盘可达、强调色统一、操作列瘦身、入场动效、Loading 统一、占位差异化、mockData 真实、二次确认、a11y 对比度、图标 aria-label 等。
- **P2 可选（13 项）**：两套导航合并、RBAC 补全、滚动条暗色、状态函数抽公共、快捷键、toast 规范、面包屑、skip-link 等。

---

## 八、本次周期收尾状态（2026-08-21 ~ 08-24）

**commit 链（已合并 `main` 并推送 `origin/main`）**：

| 主题 | 代表 commit |
|---|---|
| 暗色模式前置（isDark / App.vue darkTheme / 业务页 hex→token / 巡检兜底） | `9491d5e` → `5ca9459` |
| SettingsLayout 自写 DOM → n-menu（去 hack） | `6c860a2` / `3194592` |
| 校招管控 UI 修复（圆角 / KPI 边界 / 表格滚动 v1→v4 / 移除 aurora-base 盖底） | `70a0b88` → `b10a8e3` / `ae0e0d2` |
| 设置页内容区 margin 收口 | `14cf55a` |
| 数据字典横向溢出（n-data-table `scroll-x`） | `7def677` |
| 招聘需求设置视觉对齐校招管控 | `e7943b3` |
| **公告制度 AnnouncementSettings 暗黑适配（遗留项收口）** | **`b5ea6ea`** |

**已闭环能力**：液态玻璃 token 体系、暗色模式全站贯通、SettingsLayout n-menu 重构、校招管控/数据字典/招聘需求/公告制度 4 个设置页 UI 修复、表格滚动 v4（回归 Naive 方案）。

**仍可迭代（P2）**：操作列 n-dropdown 化（Demand/Candidate 为 card 模式待补）、T8 交互增强（错误页/拦截器/键盘/动效）、T9 SettingsLayout 反向删 `:deep` 注入、T10 a11y + 滚动条 + 状态组件。

---

## 九、后续迭代清单（P2）

- [ ] 操作列统一 n-dropdown 化（OfferList/OnboardingList/InterviewList 已 width 化，Demand/Candidate 卡模式待补）
- [ ] T8 交互增强：错误页精细化、API 拦截器统一、键盘快捷键、入场动效扩展
- [ ] T9 SettingsLayout 反向清理 `:deep` 注入（高风险，需视觉回归保护）
- [ ] T10 a11y（skip-link / aria-label）、滚动条暗色样式、状态组件收口
- [ ] 强调色 / 状态函数抽公共 `composables/useStatusTag.ts`
- [ ] toast 规范统一（成功 2s 自动消失、错误需手动关闭、中英文案规范）

---

*本总纲由 `UI_DIAGNOSIS(V1/V2/V3)`、`UI_OPTIMIZATION_PLAN`、`UI_STYLE_RECONCILIATION`、`UI_HANDOFF_CHECKLIST`、`FIX_REPORT_2026-08-22`、`CHECK_REPORT_2026-08-22` 于 2026-08-24 向上整合而成；暗色模式细节请见 `UI_DARK_MODE_TECHNICAL_PLAN.md`。*
