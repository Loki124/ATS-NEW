# ATS-NEW 前端 UI/UX 全面诊断报告
> 最后更新：2026-09-07（依据 git 最后提交）

- **诊断对象**：`web/app/src`（Vue 3 + Naive UI，97 `.vue` / 101 `.ts` / 6 `.css`）
- **权威规范**：`AGENTS.md` v2.0.0（R-001…R-2xx，UI 交互约束）
- **方法**：5 路并行只读扫描（交互状态 / 异步·错误·草稿·破坏性·微文案 / 无障碍·响应式·v-html·数据态 / 设计令牌 / 硬编码色值枚举），全部基于磁盘静态证据（file:line）。
- **原则**：依 `AGENTS.md §0.2`，标注 `[S]` 静态可判定 / `[R]` 需运行时测量 / `[H]` 需人工判断。**凡 `[R]/[H]` 项一律不勾「通过」，避免验证剧场。**

---

## 0. 总览评分卡

| 约束类别 | 等级 | 状态 | 核心问题数 |
|---|---|---|---|
| R-214 品牌令牌 CLI 生成 | P1 | ✅ 合规 | 0 |
| R-211 语义色独立于品牌 | P1 | ✅ 合规 | 0 |
| R-203 错误三段式（「抱歉」开头） | P1 | ✅ 通过 | 0（但三段式结构缺失） |
| R-109 tabindex / alt | P0 | ✅ 合规 | 0（其余 a11y 失守） |
| R-108 长列表虚拟化/分页 | P0 | ❌ 失守 | 8 处全量渲染 |
| R-103 320px 无横向溢出 | P0 | ❌ 失守 | 6 弹窗 + 7 容器 + 7 筛选栏 |
| R-107 用户输入转义 | P0 | ❌ **安全级** | 1 处 v-html + 弱消毒器 |
| R-101/R-102 交互组件状态 | P0 | ❌ 失守 | 16 提交按钮无守卫 + 11 图标按钮 <44px |
| R-104 异步四态 | P0 | ❌ 失守 | ~28 处静默失败 + 无 ErrorState |
| R-105 草稿自动保存 | P0 | ❌ 失守 | 机制 0 实现 / 15+ 长表单裸奔 |
| R-106 破坏性可撤销 | P0 | ❌ 失守 | 0 撤销 Toast / 9 单删误用确认框 |
| R-111 数据视图状态机 | P0 | ❌ 失守 | 骨架屏 0/14 / 离线 0 / 上限 0 |
| R-001 组件内禁硬编码 | P1 | ❌ 失守 | ~15 处硬编码 hex/灰阶 |
| R-203 错误三段式结构 | P1 | ⚠️ 部分 | ~20 处非三段式 |
| R-204 微文案 | P1 | ⚠️ 部分 | 提交2 + 确定13 + 确认5 + 您7 |

> **一句话结论**：设计令牌体系（R-214/R-211）是项目的最大亮点，已做到单源生成 + 暗色整体切换；但**交互健壮性、异步反馈、数据视图状态机、无障碍、响应式**五条 P0 主线系统性失守，其中 `v-html` 一处可造成 XSS，应作为最高优先修复。

---

## 1. 合规亮点（正面证据，避免只报问题）

- **R-214 品牌令牌 CLI 化**：`package.json` 含 `tokens` / `tokens:report` 脚本；`brand-tokens.mjs` 实现 OKLCH 推导 + 对比度门禁（`--ci` exit code）；`brand-tokens.css` 顶部 `DO NOT EDIT BY HAND`，含 `body.dark` 重排；两文件均 git-tracked。✅ 全仓唯一真正「单源生成」的子系统。
- **R-211 语义色独立**：`tokens.css §4` 语义色与品牌色解耦，`--brand-warm` 明确为品牌外独立 accent。✅
- **R-212 暗色品牌重排**：`brand-tokens.css body.dark` 降明度/降彩度重排，非 `(1-L)` 反转。✅
- **全局 focus-visible**：`glass.css:1162` 定义 `:focus-visible { outline: 2px solid var(--brand) }`。✅（但被若干组件 `outline:none` 覆盖，见 §6）
- **R-203「抱歉」开头**：全仓 0 命中。✅（但三段式结构仍缺，见 §9）
- **tabular-nums**：22 处已应用（`StatCard.vue:124`、`Dashboard.vue:658`、`ScorePanel.vue:63,117` 等）。✅
- **R-106 正例**：`ScreeningList.vue:72-77` 批量删除确认框带 `${selectedIds.length}` 具体数量。✅
- **R-103 正例**：`Layout.vue:185`（`600px; max-width:90vw`）、`InterviewEvaluationModal.vue:258`（`880px; max-width:96vw`）——正确写法库内已存在，仅未推广。
- **R-108 已合规**：`ScreeningList:183`、`OfferList:43`、`InterviewList:324`、`TalentPool:193`、`InvitationCenter:66`、`OnboardingList:221`、`ReferralCenter:72,85`、`PositionList:14-23`。✅
- **prefers-reduced-motion**：`tokens.css:309-321` 已降级。✅
- **无 tabindex>0**：全仓 `tabindex` 均为 `0` 或条件绑定。✅
- **无 `<img>` alt 问题**：全仓无 `<img>`，alt 规则 N/A。✅

---

## 2. 🔴 R-107 用户输入转义 —— P0 安全级（最高优先）

**`web/app/src/pages/announcement/AnnouncementDetail.vue:57`**
```html
<div class="ann-detail-body" v-html="sanitizeHtml(announcement.body)"></div>
```
- `announcement.body` 来自公告接口（管理员/用户可写），属**用户可控数据**。
- `:56` 用 `eslint-disable-next-line vue/no-v-html` 主动绕过 lint 闸门。
- **消毒器本身是黑名单正则（`:128-150`），存在实际绕过**：
  - 白名单外标签（`<style>`/`<form>`/`<math>`/`<base>`）**不被移除，原样透传**；
  - `<a href="javascript:...">` 未校验协议，可直通（`:139-141`）；
  - `<span style="...">` 允许任意 CSS（`:143-146`），可做点击劫持/信息外泄；
  - `<script src=x>`（无闭合标签）不被成对正则命中。
- `package.json` **无 `dompurify` / `sanitize-html` 依赖**（`NO_SANITIZER_DEP`）。

> 修复方向：改用白名单消毒库（DOMPurify），或后端渲染为安全结构、前端仅渲染纯文本/受控富文本；同时移除 `eslint-disable` 注释恢复闸门。**这是唯一能造成 XSS 的 P0，应排在第一位。**

---

## 3. 🔴 R-103 320px 无横向溢出 —— P0 失守

**固定宽弹窗（320px 必然溢出，须加 `max-width`）：**
- `AddCandidateModal.vue:119` `width: 960px`（最严重）
- `PositionList.vue:33` 800px / `:95` 700px
- `ScrapedResumeList.vue:42` 700px
- `SpecialApproval.vue:27` 600px
- `InvitationCenter.vue:73,93` 480px
- 对照正例：`Layout.vue:185`、`InterviewEvaluationModal.vue:258` 已用 `max-width` 写法。

**固定宽侧栏/容器（无 `max-width`）：**
- `CandidateList.vue:1077` `.left-sidebar{width:280px;flex-shrink:0}`
- `CandidateDetail.vue:668` `.left-sidebar{width:340px}`
- `Layout.vue:731` `width:240px !important`
- `Dashboard.vue:494` `width:300px`
- `addCandidate/Step1Single.vue:155` / `Step1Batch.vue:77` / `Step2Assign.vue:91` 均 `width:340px`

**筛选栏内联固定宽（叠加后远超 320px）：** `CandidateList.vue:42,47-51`、`demand/DemandList.vue:9,20`、`screening/ScreeningList.vue:169`、`interview/InterviewList.vue:312`、`onboarding/OnboardingList.vue:209`、`settings/RuleEngine.vue:29-54`、`components/ConditionTreeEditor.vue:36-99`。

> **待运行时确认（非直接判违规）**：`glass.css:1142` 在 `@media(max-width:767px)` 内对表格设 `min-width:960px`，但 `:1137` 已配 `overflow-x:auto` 受控横滚；`DataDictionary.vue:995` 同理。属「允许横滚」而非「布局溢出」，需浏览器实测确认。

---

## 4. 🔴 R-108 长列表虚拟化/分页 —— P0 失守

- `CandidateList.vue:99` `v-for="row in mockData"` 全量渲染卡片行，**无分页/虚拟化/slice**（主列表页，接真实接口后必 >200 条）。
- `ScrapedResumeList.vue:17,:47` `:pagination="false"` 作用于无上限的 RPA 抓取结果。
- **`n-data-table` 完全未传 pagination**（Naive 默认 = 全量渲染）：`NotificationList.vue:7`、`permission/UserRolesTab.vue:8`、`RolesTab.vue:9`、`TemplatesTab.vue:8`、`offer/BackgroundCheckPanel.vue:173`、`AddCandidateModal.legacy.vue:199`。
- 显式 `:pagination="false"`：`ExternalSettings.vue:88,256,310,365,389`、`DataDictionary.vue:46`、`FieldAclSettings.vue:24`、`Settings.vue:10,13,16`、`CampusControl.vue:26,176,406`。

> 修复方向：主列表（CandidateList/ScrapedResumeList）改虚拟滚动（`n-virtual-list` 或 `vue-virtual-scroller`）；所有 `n-data-table` 显式传 `:pagination` 或 `:max-height` + 滚动。

---

## 5. 🔴 R-101 / R-102 交互组件状态 —— P0 失守

### 5.1 异步提交无守卫（双击提交风险）
Naive `Button` 的 `handleClick` 仅 `!disabled && !loading` 守卫 —— **`:loading` 单独能挡功能上的双击，但按钮仍 focusable、AT 不可感知**；而 **`n-dialog` 的 `@positive-click` 无 `:loading` 时 positive 按钮永不 disabled**（Dialog 不接管 promise）。

**无 `:loading`/`:disabled` 的异步 `n-button`：**
- `settings/MouManagement.vue:345` `handleSaveMou` / `:393` `handleSaveContainer` / `:437` `handleSaveRule` / `:472` `handleSaveMutex`
- `demand/DemandList.vue:352-358` `handleSubmitApproval`

**`@positive-click` 无 `:loading`（positive 按钮永不禁用）：**
- `talent/TalentPool.vue:207` `confirmMove`
- `settings/AnnouncementSettings.vue:249` `confirmPush`
- `scraped/ScrapedResumeList.vue:24` `handleScrape`
- `resume/SpecialApproval.vue:73` `handleSubmitApproval`
- `resume/ResumeList.vue:225` `handleAssignConfirm`
- `offer/BackgroundCheckPanel.vue:184` `handleCreate` / `:199` `handleComplete`
- `candidate/CandidateDetail.vue:422` `handleSaveResume` / `:477` `handleUploadResume`
- `settings/ProcessDetailModal.vue:638` `removeStage` / `:700` `confirmClose`

**全局统计**：99/101 处 `:loading` 未同时设 `:disabled`；仅 `DataDictionary.vue:281`、`DataDashboard.vue:36` 合规；全仓唯一重入守卫在 `StageRuleConfigModal.vue:505`；**全仓 0 处 `aria-busy`**。

### 5.2 图标按钮命中区 < 44×44px（R-102）
`src` 内**无 `.icon-btn` 类、无 `inset:` 扩区、无 `min-height/min-width:44`**。典型：
- `dashboard/WeeklySchedule.vue:5,11`（`text size="small"`，~24-28px）
- `common/ResumeCard.vue:36` `.c-chk`（16×16）
- `common/UploadZone.vue:39,40`、 `common/Breadcrumb.vue:4`
- `settings/AnnouncementSettings.vue:202,209`、`DataDictionary.vue:58,77`、`StageRuleConfigModal.vue:156,217`

### 5.3 可聚焦性（R-109 交叉）
**20 个可点击非按钮元素无 `tabindex`，键盘不可达**：`JobCard.vue:2`、`ScreeningListItem.vue:2`、`ResumeCard.vue:35-36`、`UploadZone.vue:39-40`、`Breadcrumb.vue:4`、`Step1Batch.vue:34`、`Step2Assign.vue:31,32,60,64`、`CandidateList.vue:108`、`StageRuleConfigModal.vue:156,217`、`ProcessDetailModal.vue:331,344,363`、`DemandList.vue:40`。

**焦点环被 `outline:none` 清除且无 `:focus-visible` 替代**：`Step1Single.vue:244`、`Step1Batch.vue:281`、`Step2Assign.vue:271`。

---

## 6. 🔴 R-104 异步四态 —— P0 失守

**静默失败（catch 仅 `console.error`/`.catch(()=>{})`，用户零反馈，约 28 处）：**
- `settings/UserManagement.vue:302,317,329,341,353`
- `settings/MouManagement.vue:1151,1207,1262,1314`（连描述都没有）
- `resume/ResumeList.vue:308,325,337`、`settings/DemandConfig.vue:377,388,399`
- `settings/DepartmentManagement.vue:258,273`、`demand/DemandList.vue:605`
- `position/PositionList.vue:347`、`resume/SpecialApproval.vue:166`
- `settings/ProcessStageRules.vue:498,508`（`catch(e){console.warn(...)}` 单行吞）
- `api/users.ts:43`、`stores/user.ts:83`(`.catch(()=>{})` 完全丢弃)

**结构性缺口**：`components/common/` 有 `EmptyState.vue`、`LoadingState.vue`，但**全仓无 `ErrorState` 组件** —— 这是 R-104 与 R-111「部分失败」同时失守的根因。

---

## 7. 🔴 R-105 草稿自动保存 —— P0 失守

- **全仓库 0 草稿机制**：`saveDraft`/`setDraft`/`draft` 零命中；`stores/addCandidate.ts` 无 localStorage persist。
- **>1 分钟表单裸奔（无草稿）**：`AddCandidateModal.vue` + `addCandidate/Step1Single/Step1Batch/Step2Assign`（三步向导）、`MouManagement.vue`（4 表单）、`ProcessDetailModal.vue`、`ExternalSettings.vue`、`CampusControl.vue`、`DynamicFieldSettings.vue`、`AnnouncementSettings.vue`、`DemandList.vue:427`、`UserManagement.vue`、`DepartmentManagement.vue`。
- **用确认框代替草稿**（违反 `AGENTS.md:148`「草稿已存在时 MUST NOT 弹二次确认框」的反向实现）：`AddCandidateModal.vue:22-29`（`isDirty` 时弹「未保存的修改将丢失」）、`ProcessDetailModal.vue:698`（`positive-text="确定离开"`）。
- **敏感字段落盘风险（当前潜在，非已发生）**：一旦补草稿，以下表单须**整体禁用**而非逐字段过滤 —— `AccountSettings.vue:124,127,130`（`oldPassword/newPassword/confirmPassword`）、`UserManagement.vue:69`、`ExternalSettings.vue:143`（apiKey/secret）、`Login.vue:48`。

---

## 8. 🔴 R-106 破坏性可撤销 —— P0 失守

- **全应用 0 个撤销 Toast**（`撤销` 命中全是业务状态文案或富文本 undo）。
- **单条删除误用确认框**（应为「直接执行 + 5-8s 撤销 Toast」）：`composables/useRuleActions.ts:37-39`、`DataDictionary.vue:593`、`DynamicFieldSettings.vue:276`、`CampusControl.vue:1306,1334,1415`、`AnnouncementSettings.vue:506`、`ExternalSettings.vue:1270`、`ProcessDetailModal.vue:643`。
- **确认框缺具体影响范围**（违反 `AGENTS.md:181`）：`MouManagement.vue:776,814,853,900`（「确认删除此MOU？」无名称/数量/后果）、`RecruitmentStage.vue:238`（「确定要删除吗？」）、`DepartmentManagement.vue:565`、`UserManagement.vue:722`、`permission/ResourcesTab.vue:129`。
- **删除既无确认也无撤销（真空）**：`permission/UserRolesTab.vue:105-113`、`RolesTab.vue:188-196`、`DataDashboard.vue:208-216`。
- 正例已存在：`ScreeningList.vue:72-77`（确认框带数量）。

---

## 9. 🟠 R-203 / R-204 错误文案与微文案 —— P1

**R-203 三段式**：「抱歉」开头 0 命中（通过），但**三段式结构基本不存在** —— 错误普遍单行裸展示后端 msg，无「数据是否安全」说明、无可点击恢复、无错误码折叠/复制（`复制错误` 全仓 0 命中）：
- `MouManagement.vue:1105,1108,1186,1189,1241,1244,1293,1296` 光秃秃 `'删除失败'`
- `permission/UserRolesTab.vue:111`、`RolesTab.vue:194`、`ResourcesTab.vue:233` `'删除失败: '+e?.response?.data?.message`（技术错误直出）
- `main.ts:41` 全局 `'服务繁忙，请稍后重试'`（无数据安全说明、无重试按钮）
- `GlobalSearch.vue:98` `'搜索失败,请重试'`（无动作）
- 相对正例：`AnnouncementDetail.vue:185-187` 区分网络/服务端分支，但仍缺 ①②③ 完整三段

**R-204 微文案违规**：
- `提交`：`addCandidate/Step2Assign.vue:75`、`offer/BackgroundCheckPanel.vue:199`
- `确定`（13）：`AccountSettings.vue:136`、`DemandList.vue:427`、`MouManagement.vue:345,393,437,472`、`UserManagement.vue:107`、`AnnouncementSettings.vue:236,247`、`DepartmentManagement.vue:168`、`SpecialApproval.vue:70`、`ResumeList.vue:222`
- `确认`（5）：`InvitationCenter.vue:87,102`、`OfferList.vue:101`、`ScreeningList.vue:75`、`OnboardingList.vue:139`
- `您`（7，UI 内）：`errors/NotFound.vue:9`、`errors/Forbidden.vue:9`、`ProcessDetailModal.vue:712`、`AccountSettings.vue:98`、`addCandidate/AsyncResult.vue:18,22,25`（`CandidateList.vue:490`/`CandidateDetail.vue:580` 为对外邮件模板，可豁免）
- `加载中…`：`components/common/LoadingState.vue:6` 默认文案，作为共享组件全站扩散
- `tabular-nums`：22 处已应用 ✅

---

## 10. 🔴 R-109 / R-111 无障碍与数据视图状态机 —— P0 失守

### R-109 无障碍
- **div/span 当按钮（无 role/键盘响应）**：17 处 / 9 文件。典型 `CandidateList.vue:24-31`（`.pipeline-stat-item` 承担状态筛选主交互）、`ResumeCard.vue`(2)、`Step2Assign.vue`(4)、`ProcessDetailModal.vue`(4)、`UploadZone.vue`(2)、`JobCard.vue`、`ScreeningListItem.vue`。
- **装饰图标缺 `aria-hidden`**：`aria-hidden` 仅出现在 16 文件（多数每文件 1 处），`n-icon` 普遍使用但覆盖率极低。
- **对比度 `[R]` 未验证**：`tokens.css` 注释声称 `#64748B` 对白底 4.8:1、`#94A3B8` 暗底达标，但**对比度需浏览器实测**，本报告不勾「通过」。建议用 axe / 对比度仪对 `--ink-faint`/`--g5`/`--c-warning`/`--brand-warm-deep` 等跑一轮 `[R]` 测量。

### R-111 数据视图完整状态机
- **骨架屏 0/14 列表页**（仅 `Dashboard.vue:187` 用 `SkeletonCard`；其余用 `n-spin` 转圈）。
- **`CandidateList.vue` 只有 happy path**：无 loading/空态/错误态（全文仅 `:459` 一处 catch，服务于 STATUS_SCHEMA）。`NotificationList.vue:7` 同样裸表格。
- **部分失败**：唯一尝试 `CampusControl.vue:1455-1469`（`Promise.allSettled` 聚合 5 请求）但失败仅汇总成一条 `message.error`，无就地重试、成功/失败区块无视觉区分。
- **离线态 0 覆盖**（全仓无 `navigator.onLine` 监听）；**已达上限态 0 覆盖**；**无权限态**仅 `AnnouncementDetail.vue:183`。
- **搜索无结果 vs 筛选无结果**：仅 `CampusControl.vue:102` 区分，其余合并为单一空态。
- **缺空态页面**：CandidateList / OfferList / InterviewList / ScreeningList / ScrapedResumeList / NotificationList / InvitationCenter / PositionList / OnboardingList（主表）。

---

## 11. 🟠 R-001 组件内硬编码原始值 —— P1 失守

**硬证据（应为 token，却写死字面量）：**
- **写死错误红 `#EF4444`**（应 `type="error"` 或 `var(--c-error)`）：`ProcessStageEditor.vue:54`、`AnnouncementSettings.vue:131,202,209`、`DataDashboard.vue:236`、`ConditionTreeEditor.vue:80`、`ProcessDetailModal.vue:641`。
- **写死中性灰阶**（应 `--ink-faint`/`--g5`）：`MouManagement.vue:741`(`#999`)、`UserRolesTab.vue:55`(`#aaa`)、`DataDictionary.vue:526,536`(`#888`)、`DepartmentManagement.vue:456,468,484`(`#bfbfbf`/`#8c8c8c`)。
- **`App.vue:54-57`**：Naive 全局主题覆盖 `successColor/warningColor/errorColor/infoColor` 写死 hex，与 `tokens.css §4` 语义色重复，存在漂移风险（改 token 不会同步）。
- **`CandidateDetail.vue:675`**：`border-radius:8px` 写死（应 `var(--radius-sm/md)`）。
- **`App.vue:63-66`**：`cardColor/modalColor/popoverColor/tableColor` 写死 `#ffffff`（暗色转 `transparent`，属有意为之，低危）。
- **可接受（白字压品牌底）**：`Login.vue:351`、`ResumeCard.vue:124`、`OccupiedActions.vue:31`、`Stepper.vue:55-57`、`ScoringOverlay.vue:167`、`CandidateDetail.vue:671` 的 `color:#fff` 压在 `var(--brand)` 上，等同 `--on-brand`，不计入违规。
- **豁免**：`ThemeSettings.vue` 的 hex 预设为面向用户的取色器数据源。

---

## 12. 修复优先级路线图

### P0-A（安全 + 阻断，当次必做）
1. **R-107**：`AnnouncementDetail.vue` 的 `sanitizeHtml` 换 DOMPurify（白名单），移除 `eslint-disable`。`[S]`
2. **R-103**：6 个固定宽弹窗加 `max-width`（对齐 `Layout.vue:185` 写法）。`[S]`
3. **R-108**：CandidateList / ScrapedResumeList 改虚拟滚动；所有 `n-data-table` 显式分页。`[S]`

### P0-B（交互健壮性，迭代 1）
4. **R-101**：异步 `n-button` 补 `:disabled="isSubmitting"` + `aria-busy`；`n-dialog` 的 `@positive-click` 配 `:loading` 或手动 `disabled` 守卫。`[S]`
5. **R-102**：图标按钮加 `::after{inset:-10px}` 扩至 44px。`[S]`
6. **R-104**：新增 `ErrorState.vue`；清掉 28 处静默 `catch`，统一错误反馈。`[S]`
7. **R-105**：新增 `useDraft` composable（TTL 24h、敏感字段整体禁用、提交即清）。`[S]`
8. **R-106**：单删改「执行 + 撤销 Toast」；批量/不可逆补带范围文案的确认框。`[S]`
9. **R-111**：列表页补骨架屏/空态/部分失败就地重试/离线/上限态。`[S]`

### P1（打磨，迭代 2）
10. **R-001**：6 处 `#EF4444` → `type="error"`；灰阶 → `--ink-faint`；`App.vue` 主题覆盖改引用 token。`[S]`
11. **R-204**：`提交/确定/确认` → 动词+宾语（`创建项目`/`删除这 3 个文件`）；`您`→`你`；`加载中…`→具体文案。`[S]`
12. **R-203**：错误组件统一三段式 + 错误码折叠复制。`[S]`
13. **R-109 对比度 `[R]`**：用 axe 实测 `--ink-faint`/`--g5`/`--c-warning`/`--brand-warm-deep` 对比度，按需调阶。**需运行时工具，本报告不代判。**

---

## 13. 附录：证据索引（按文件）

| 文件 | 涉及规则 |
|---|---|
| `announcement/AnnouncementDetail.vue:56-57,128-150` | R-107 |
| `candidate/AddCandidateModal.vue:22-29,119` | R-105,R-103 |
| `candidate/CandidateList.vue:24-31,42,99,1077` | R-109,R-108,R-103 |
| `candidate/CandidateDetail.vue:668,675,712` | R-103,R-001,R-204 |
| `settings/MouManagement.vue:345,393,437,472,741,776-900,1105-1296` | R-101,R-104,R-106,R-203 |
| `settings/ProcessDetailModal.vue:331,344,363,638,643,698,700` | R-101,R-106 |
| `settings/AccountSettings.vue:98,124-130,136` | R-204,R-105 |
| `settings/ThemeSettings.vue` | （豁免，取色器） |
| `App.vue:54-66` | R-001 |
| `pages/Layout.vue:185,731` | R-103(正/反例) |
| `components/common/*` | R-104(缺 ErrorState) |

> 标注约定：`[S]`=静态可判定（已给 file:line 依据）；`[R]`=需浏览器运行时测量；`[H]`=需人工/主观判断。本报告对所有 `[R]/[H]` 项均**未**勾「通过」。
