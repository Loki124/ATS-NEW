# 设置页统一结构规范 · 合规审查（2026-08-27）

> 审查对象：`web/app/src/pages/settings/**` 全部 33 个 .vue（含 permission 子模块）
> 对照规范：`docs/ui/SETTINGS_PAGE_STRUCTURE.md` (v1.0, 2026-08-24)
> 审查方式：静态扫描（grep file:line + 人工确认）+ `vite build` 绿灯
> 结论：**符合（2026-08-27 续复核）**。外壳/标题/工具条/弹窗/视觉一致性执行良好；原 1 处规范-代码漂移（滚动模型）与 2 处局部偏差（含 DataDashboard KPI hex）均已消解，仅余 🔵 非阻塞建议项。

**修订状态（2026-08-27 续）**：兵哥拍板「仅修订规范、不改码」。已更新 `SETTINGS_PAGE_STRUCTURE.md` 至 v1.1：
> - 问题 1（17 页 height:100% 三件套）✅ **已通过规范修订消解**——新增「模型 B 固定标题+内部滚动三件套」为合法变体，取消 `height:100%` 禁止项。17 页即刻合规。
> - 问题 2（DataDashboard KPI 硬编码 hex）✅ **已修复（2026-08-27 续）**：DataDashboard 改用全局 `.kpi-card.kpi-card--accent`（glass.css 新增变量化强调变体），删除私有 `.kpi-*` 与硬编码 hex `#4f46e5`/`#6b7280`；`vite build` 绿灯。
> - 🔵 建议项（table-wrap 包裹 / h1 / ThemeSettings 主标题）维持原建议，非阻塞。

---

## 一、总览

| 清单项（规范 §） | 结果 | 说明 |
|---|---|---|
| §2 根元素 `.page-container` | ✅ 通过 | 除 Placeholder(err-page) 与 permission/*Tab(子组件) 外，全部用 `.page-container` |
| §1 无私有极光 | ✅ 通过 | 仅 `SettingsLayout.vue` 持有 `.settings-aurora`/`.blob-*`（外壳，正确）；内容页零私有极光 |
| §3 标题结构 + 无 scoped 覆盖 | ✅ 通过 | 25+ 页用 `.page-header>.page-title+.page-subtitle`；无 `.page-title`/`.page-subtitle` 字号/颜色覆盖残留 |
| §3 底部分隔线通栏 | ✅ 通过 | 无 `.page-header{margin-bottom}` 覆盖，全局负 margin 生效 → 通栏一致 |
| §4 工具条 `<div class="toolbar">` | ✅ 通过 | 全部为 `<div class="toolbar">`，无 `<n-card class="toolbar">` 残留 |
| §4 无私有 `.table-wrap`/`.gradient-btn` | ✅ 通过 | 无私有重定义 |
| §6 弹窗零样式 | ✅ 通过 | 仅 CampusControl `.rule-modal` 为表单紧凑微调（规范允许）；居中/滚动/边框由全局 `.n-modal .n-card` 兜底 |
| §2 禁止 `height:100%` on `.page-container` | 🟡 **违反（17 页）** | 普遍使用 `.page-container{height:100%;display:flex}` + 内部 `.page-body{overflow}` 三件套，与规范默认滚动模型冲突 |
| §4 KPI 用全局 `.kpi-card--accent`（变量化） | ✅ 通过 | DataDashboard 已迁至全局 `.kpi-card.kpi-card--accent`，无私有 hex（2026-08-27 续修复） |
| §4 表格包 `.table-wrap` | 🔵 建议 | 仅 CampusControl 包裹；其余靠全局 `.settings-scroll .n-data-table` 兜底（视觉 OK，非规范字面） |

**严重等级分布**：🔴 0 · 🟡 0 · 🔵 1（+ 若干 🔵 细节；问题 1/2 已于 2026-08-27 续消解）

---

## 二、🟡 问题详述

### 🟡 问题 1：`.page-container { height:100% }` 三件套 vs 规范 §2 漂移（17 页）

**现象**：以下页面在 scoped 中把根容器写成 flex 列并写死 `height:100%`，再配 `.page-header{flex-shrink:0}` + `.page-body{flex:1;overflow-y:auto}` 的「内部滚动」模型：

```
SchoolLibrary.vue:171      ScoringRules.vue:30        DepartmentManagement.vue:596
ProcessStageRules.vue:514  PermissionManagement.vue:64 DynamicFieldSettings.vue:306
ProcessStageEditor.vue:295 DataDashboard.vue:254      RecruitmentProcess.vue:156
UserManagement.vue:158     MouManagement.vue:1416     RecruitmentRound.vue:179
AccountSettings.vue:287    CompanyLibrary.vue:167     CompanySettings.vue:126
FieldAclSettings.vue:156   RecruitmentStage.vue:341
```

**与规范冲突点**：
- 规范 §2 明确写「**禁止** 自写 `height:100%`」「布局模式 默认 block 流（标题→KPI→工具条→表格→弹窗）」。
- 规范 §3 的吸顶是依赖「`.settings-scroll` 整体滚动 + `.page-header` sticky」；而上述三件套改为「`.page-container` 锁高 + `.page-body` 内部滚动」，sticky 实际不生效（滚动发生在 `.page-body` 内）。

**性质**：这是一个**规范与代码双向漂移**——
- 代码侧：三件套是 2026-08-24 与 AccountSettings/DemandConfig 同期落地的「固定标题 + 内容区自滚」成熟模式，视觉与交互均正常，并非 bug。
- 规范侧：我当天写的 `SETTINGS_PAGE_STRUCTURE.md` 只描述了「默认 block + sticky」一种模型，**遗漏了三件套**，且误把 `height:100%` 列为禁止项。

**判定**：规范该补，不该让 17 页回退。建议把三件套作为规范的「§2.1 固定标题 + 内部滚动」合法变体写进去（见第四节建议）。

### ✅ 问题 2（已修复）：DataDashboard KPI 私有重定义 + 硬编码色（DataDashboard.vue，2026-08-27 续修复）

**代码**：
```html
<n-card class="kpi-card" :bordered="false" embedded>   <!-- L13 -->
```
```css
.kpi-card { text-align:center; background:linear-gradient(135deg,var(--brand-tint),var(--brand-soft)); } /* L306 */
.kpi-value { font-size:28px; font-weight:700; color:#4f46e5; }   /* L313 硬编码 hex */
.kpi-label { font-size:13px; color:#6b7280; }                    /* L318 硬编码 hex */
```

**与规范冲突**：
- §4 要求 KPI 用「`.kpi-row > .kpi-card`」，`.kpi-card` 是全局无边框玻璃卡（borderless 融入）。
- 此处用 `<n-card class="kpi-card" embedded>` 套私有渐变背景，且 `.kpi-value/.kpi-label` 用硬编码 `#4f46e5`/`#6b7280`（非 `var(--brand)`/`--ink-soft`），暗色模式下不会跟随变量集切换。

**性质**：数据看板想做「渐变强调 KPI」是合理设计意图，但原实现走了私有 CSS + 硬编码 hex，违反单一令牌与无边框规格。**状态（2026-08-27 续）：已修复** —— 全局 glass.css 新增 `.kpi-card.kpi-card--accent`（渐变底 + 居中，仅用 `var(--brand-tint)/var(--brand-soft)/var(--ink)`，暗色随 `--brand` 切换），DataDashboard 改为 `<div class="kpi-card kpi-card--accent">` 并删除全部私有 `.kpi-*` 与 hex；`vite build` 绿灯。

---

## 三、🔵 建议项

1. **表格 `.table-wrap` 包裹（§4 字面）**：仅 CampusControl 的 6 处表格包了 `<div class="table-wrap">`；其余页面（UserManagement / CompanyLibrary / SchoolLibrary / DepartmentManagement / DemandConfig / AccountSettings / MouManagement / FieldAclSettings / DataDictionary / Recruitment* / Settings 等）直接写 `<n-data-table>`。功能上靠全局 `.settings-scroll .n-data-table`（glass.css 阶段 F）兜底，视觉/滚动一致；但不符合规范字面。建议存量页逐步补 `<div class="table-wrap">` 包裹以与范本统一（优先级低，纯风格一致性）。

2. **标题语义标签**：`ProcessStageRules.vue:12` / `ProcessStageEditor.vue:12` 用 `<h2 class="page-title">`；规范示例用 `<h1>`。建议统一为 `<h1>`（单页唯一主标题，利于无障碍地标）。

3. **ThemeSettings 缺主标题**：`ThemeSettings.vue:4` 有 `.page-header` 但只有 `.page-subtitle`，无 `<h1 class="page-title">`。建议补主标题（如「主题外观」）。

4. **permission/*Tab.vue 子组件**：`UserRolesTab/RolesTab/ResourcesTab/TemplatesTab` 根直接用 `.xxx-tab` 而非 `.page-container`（它们是 PermissionManagement 内的 tab 内容，由父页提供外壳，属合理例外，但建议注释说明以免误判）。

---

## 四、改进建议（给兵哥拍板）

**A. 修订规范（推荐，零代码改动）**：在 `SETTINGS_PAGE_STRUCTURE.md` 增补「§2.1 固定标题 + 内部滚动三件套」作为合法布局变体：
```css
.page-container { display:flex; flex-direction:column; height:100%; min-height:0; }
.page-header { flex-shrink:0; }              /* 标题固定 */
.page-body  { flex:1; min-height:0; overflow-y:auto; overflow-x:hidden; } /* 内容区自滚 */
```
并把 §2「禁止 height:100%」改为「默认 block 流；需固定标题时可用三件套（height:100% + page-body 自滚）」。这样 17 页立刻合规，规范与代码对齐。

**B. 修 DataDashboard KPI（小改动）**：移除私有 `.kpi-card/.kpi-value/.kpi-label` 硬编码，改用全局 `.kpi-row>.kpi-card` 或新增 `kpi-card--accent` 变体（走 `var(--brand)` 派生，暗色同步）。

**C. 表格包裹（可选收尾）**：存量页的 `<n-data-table>` 逐步加 `<div class="table-wrap">` 包裹。

---

## 五、验证

- `vite build`：exit 0（仅既有 auth.ts 动态导入 warn，非本次相关）。
- 静态扫描覆盖：33 个 .vue 全量 grep（根容器 / 极光 / 标题覆盖 / 工具条 / table-wrap / kpi / modal / page-container 重写）。
- 暗色：本次为静态审查，未跑浏览器；硬编码 hex（DataDashboard）的暗色失效需人工/Playwright 复核。
