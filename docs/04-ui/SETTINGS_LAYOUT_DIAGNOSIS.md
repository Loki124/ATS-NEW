# SettingsLayout 嵌套与间距 · 诊断报告
> 最后更新：2026-09-07（依据 git 最后提交）

> 触发：兵哥 2026-08-30 DevTools 截图反馈「招聘提速模块嵌套层数过多 + 间距太大」
> 结论：**不是单纯的嵌套问题，是三层叠加债务**（双层布局 + padding 叠加 + 全局 !important 字号）
> 状态：**已执行（兵哥选「全做」，2026-08-30）**。四阶段落 4 原子提交推 `origin/main`（08b4791 / ee1bc80 / babd800 / da261aa）。详见 §9。

---

## 0. 执行摘要

| 问题 | 严重度 | 根因 | 影响面 |
|---|---|---|---|
| **padding 叠加 32px** | P0 | `.settings-scroll`(20px) + 页面根 class(12px) 未被清零规则覆盖 | 22 settings 页 |
| **page-header ~80px** | P0 | 全局 `.page-title{font-size:26px !important}` + `.page-header{margin-bottom:20px}` | 36 文件（全项目） |
| **11 层嵌套** | P1 | App Layout(`n-layout`+`n-layout-sider`) 与 SettingsLayout(`n-layout`) **双层布局叠加** | 22 settings 页 |
| **样板 CSS 重复** | P2 | 22 页各自重复定义 `.page-container`/`.page-header`/`.page-body` 三件套 | 22 settings 页 |

---

## 1. 嵌套真相：不是 SettingsLayout 一家的锅

### 1.1 实际 DOM 链（11 层来源拆解）

```
App 主布局  pages/Layout.vue
└─ n-layout.app-layout (has-sider)          ← Layout.vue:10
   ├─ n-layout-sider                         ← Layout.vue:18  ★截图里看到的 sider 来自这里
   └─ [Naive 自动注入] n-layout-scroll-container
      └─ n-layout-content
         └─ <router-view>  → 渲染 SettingsLayout

SettingsLayout  pages/settings/SettingsLayout.vue
└─ n-layout.settings-layout (has-sider)      ← SettingsLayout.vue:2  ★【冗余层，可删】
   ├─ div.settings-sider.glass-sidebar       ← :8  ★已是自定义 div（非 n-layout-sider）
   └─ n-layout-content.settings-content      ← :43
      ├─ div.settings-aurora (aria-hidden)   ← :44  装饰性光晕，纯视觉
      └─ div.settings-scroll (padding:20px)  ← :49 / CSS :347
         └─ <router-view>  → 渲染具体设置页

页面  pages/settings/RecruitmentStage.vue
└─ div.page-container.recruitment-stage      ← 同元素挂两个 class
   └─ div.page-body
      └─ div.page-header
```

### 1.2 关键更正：`n-layout-sider` 不在 SettingsLayout

`SettingsLayout.vue:4-7` 注释已明确记载：
```
⚠️ 不再用 n-layout-sider：它会自动把 header + menu 一起包进内部 .n-layout-scroll-container，
    导致 Naive 的 scrollbar 竖向跨整个容器、覆盖在 header 上方（用户反馈"滚动条覆盖header"）。
    改为自定义 .settings-sider（flex column）
```

→ 截图里的 `n-layout-sider` 来自 **App 主布局 `Layout.vue:18`**，是**既有设计**（主导航侧栏），不是 SettingsLayout 的遗留问题。

### 1.3 唯一真正的冗余层：SettingsLayout 的 `n-layout`

`SettingsLayout.vue:2` 的 `<n-layout class="settings-layout" has-sider ...>` **已被 App 的 `n-layout-content` 包裹**，其 `has-sider` 语义在此场景下无实际作用（它的 sider 是自定义 div，不是 n-layout-sider）。

**可降级为普通 flex div，净减 2 层**（`n-layout` + Naive 自动注入的 `n-layout-scroll-container`）。

---

## 2. P0：三层 spacing 叠加（"间距太大"的直接元凶）

### 2.1 叠加明细

| # | 层 | 位置 | 值 | 是否被清零 |
|---|---|---|---|---|
| ① | `.settings-scroll` padding | `SettingsLayout.vue:347` | **20px** | 否（源头） |
| ② | 页面根 class padding | `RecruitmentStage.vue:394` `.recruitment-stage` | **12px**（原 20px） | ❌ **未被清零** |
| ③ | 全局 `.page-container` padding | `glass.css:889` `var(--space-6)`=24px | 24px | ✅ 被 `SettingsLayout.vue:352` 清零 |

### 2.2 清零规则为何失效（特异性平局）

`class="page-container recruitment-stage"` 是**同一元素**，两条规则打平：

```css
/* SettingsLayout.vue:352 —— 想清零 */
.settings-scroll :deep(.page-container) { padding: 0; }      /* 特异性 (0,2,0) */

/* RecruitmentStage.vue scoped —— 又设回来 */
.recruitment-stage[data-v-eb2a0a57] { padding: 12px ...; }   /* 特异性 (0,2,0) */
```

**特异性相同 → 后加载者胜**。scoped 样式在全局之后注入，故**页面自己的 padding 胜出，与 ① 叠加 = 32px**。

### 2.3 项目早有此设计意图，但实现不完整

`glass.css:893-895` 注释原文：
```
/* 校招管控等独立页面根容器：作为内容最外层，自带内边距（左侧与导航栏间距由此保证）。
   注：在 SettingsLayout 的 settings-scroll 内时，会因外层已留 20px 间距，
   故在 SettingsLayout 作用域内清零（见 settings.scss / SettingsLayout.vue）。 */
```

→ 设计意图正确（"外层已留 20px，故内层清零"），但**清零规则只覆盖 `.page-container`，漏了挂在同元素的第二个 class**（`.recruitment-stage` / `.recruitment-process` / `.interview-round` / `.theme-settings` …）。

---

## 3. P0：page-header ~80px 高度拆解

| 组成 | 来源 | 值 |
|---|---|---|
| 标题字号 | `glass.css:733` `.page-title{font-size:26px !important}` | **26px** |
| 标题行高 | `glass.css:735` `line-height:1.25` | 26×1.25 = **32.5px** |
| 副标题上边距 | `glass.css:741` `.page-subtitle{margin:6px 0 0}` | +6px |
| header 下边距 | `glass.css:727` `.page-header{margin-bottom:20px}` | +20px（本次已用 scoped `margin:0 0 8px 0` 覆盖为 8px） |
| **合计** | | 原 ~80px → 现 ~66px |

**要再压缩，必须改 `.page-title` 的 `26px !important`** —— 只有 `!important` 能覆盖 `!important`，属全局改动（影响 36 文件所有页面标题）。

---

## 4. 影响面统计

### 4.1 `page-container` 使用面：**36 个文件**

- **settings 页 22 个**（本次重构范围）
- **业务页 9 个**（`CandidateList`/`OfferList`/`InterviewList`/`PositionList`/`TalentPool`/`OnboardingList`/`InvitationCenter`/`ScreeningList`/`NotificationList`）
- 其他：`Layout.vue`、若干 modal/editor

> ⚠️ `.page-container`/`.page-body` 是**全项目布局规范**，不只 settings。改 `glass.css` 全局定义会波及业务页。

### 4.2 样板 CSS 重复（22 settings 页）

以下模式在 22 个 settings 页中**逐页复制**，高度雷同：
```css
.page-container { display:flex; flex-direction:column; height:100%; min-height:0; padding:0; }
.page-header    { flex-shrink:0; }
.page-body      { flex:1; min-height:0; overflow-y:auto; overflow-x:hidden;
                  display:flex; flex-direction:column; gap:var(--space-4); }
```

**其中 5 个文件在同一 `<style scoped>` 块内重复写了两遍**（非双 style 块，已核实各文件仅 1 个 `<style scoped>`）：

| 文件 | 重复位置 |
|---|---|
| `SchoolLibrary.vue` | 169-187 / 198-209 |
| `CompanySettings.vue` | 124-142 / 153-164 |
| `DepartmentManagement.vue` | 593-611 / 622-633 |
| `DataDashboard.vue` | 251-269 / 280-291 |
| `ProcessStageRules.vue` | 518-536 / 547-558 |

两段内容相同 → 后段覆盖前段，**功能无影响，纯冗余**。

### 4.3 双 style 块（项目既定模式，非债务）

仅 `StageRuleConfigModal.vue` 有 2 个 style 块（1 scoped + 1 un-scoped）——用于 teleport 弹层，符合 MEMORY.md 记载的既定模式，**不要合并**。

---

## 5. 可合并 vs 有副作用

### ✅ 可安全合并（低风险）

| 项 | 做法 | 依据 |
|---|---|---|
| 5 文件的重复三件套 | 删后段，保留前段 | 内容相同，后段纯冗余 |
| SettingsLayout `n-layout` → `div` | 改 `:2` 和 `:53` 闭合标签 + CSS 补 flex | `has-sider` 在此无实际作用（sider 已是自定义 div） |

### ⚠️ 有副作用，需逐页回归

| 项 | 副作用 | 风险 |
|---|---|---|
| 修 padding 清零规则 | 22 页外边距统一收紧 12-20px，视觉密度变化 | 低（纯视觉），但需逐页看是否有元素贴边 |
| 抽取公共三件套到 SettingsLayout | 22 页删除自有定义，若某页有微调会被覆盖 | 中，需 diff 每页的 gap/padding 差异 |
| 改 `.page-title` 26px | 36 文件所有页面标题变小 | **高**，跨业务页，需全项目视觉回归 |

### 🚫 不要动

| 项 | 原因 |
|---|---|
| App `Layout.vue` 的 `n-layout-sider` | 主导航侧栏，既有设计，与本次反馈无关 |
| `StageRuleConfigModal.vue` 双 style 块 | teleport 弹层依赖 un-scoped 块 |
| `.settings-aurora` | 装饰性光晕（`aria-hidden="true"`），品牌视觉体系一部分，删了会丢 Liquid Glass 效果 |

---

## 6. 分阶段方案（待兵哥选定）

### 阶段 1 —— 消除 padding 叠加（推荐先做，低风险）
- 修 `SettingsLayout.vue:352` 清零规则，使其覆盖同元素所有 class；或统一约定「settings 页根元素不设 padding」，删掉三页的 `padding: 12px var(--space-6)`
- 收益：外边距 32px → 20px，立竿见影
- 影响：22 settings 页，纯视觉

### 阶段 2 —— 删 SettingsLayout 冗余 `n-layout`
- `<n-layout class="settings-layout" has-sider>` → `<div class="settings-layout">`
- 收益：净减 2 层嵌套
- 风险：需验证侧栏折叠、响应式（≤767px）、`.n-layout` 相关 CSS 选择器是否失效

### 阶段 3 —— 抽取公共三件套
- 22 页重复定义 → SettingsLayout `:deep()` 或全局
- 收益：消除 ~200 行重复 CSS
- 风险：中，需逐页 diff gap/padding 差异

### 阶段 4 —— 全局标题字号（最高风险，建议单独立项）
- `.page-title` 26px → 20/22px（需 `!important` 覆盖 `!important`）
- 收益：page-header 再降 ~10px
- 风险：36 文件全项目视觉回归

---

## 7. 回归清单（动手前必查）

- [ ] 22 个 settings 页在 1440×900 下的外边距是否一致、无贴边
- [ ] 侧栏折叠（64px）往返正常，`.settings-sider.collapsed` 相关 CSS 未失效
- [ ] 响应式 ≤767px：`.settings-scroll{overflow:auto}` 移动端分支仍生效
- [ ] 各页 `.page-body` 内部滚动单一职责未被破坏（无双重滚动条）
- [ ] `--space-6` / `--space-4` / `--space-3` token 未被硬编码值绕过（X-04/X-05 门禁）
- [ ] stylelint X-05 颜色门禁 exit 0
- [ ] `npm run build:nocheck` 通过

---

## 8. 本次已做的临时缓解（2026-08-30，未提交）

三文件（`RecruitmentStage`/`RecruitmentProcess`/`RecruitmentRound`）已改：
- `TABLE_ROW_HEIGHT` 56 → 44 + `theme-overrides{tdPaddingMedium:'6px'}` + CSS `!important` 兜底
- `.page-body` gap 16 → 12px
- 容器 padding 20 → 12px
- `.page-header` 显式 `padding:0; margin:0 0 8px 0`

**注意**：容器 padding 12px 与 `.settings-scroll` 20px **仍在叠加**（见 §2）。阶段 1 修完后应把这三处的 `padding` 一并删除，改由 SettingsLayout 统一管控。

---

## 9. 执行记录（2026-08-30，兵哥选「全做」）

四阶段全部落地，4 个原子提交已推 `origin/main`。**每阶段独立构建验证 + 提交**，便于 `git checkout` 单阶段回滚。

| 阶段 | 提交 | 改动 | 硬证据 |
|---|---|---|---|
| ① padding 叠加 32→20px | `08b4791` | SettingsLayout 清零规则 `:deep(.page-container){padding:0!important}`；三页删冗余 `padding:12px` | build ✅；dev server 实时返回 `padding:0 !important` |
| ② 删冗余 n-layout（减 2 层） | `ee1bc80` | 根 `n-layout(has-sider)`→`div`、右侧 `n-layout-content`→`div`；CSS `.settings-layout{display:flex}` + `.settings-content{flex:1}`；移除 NLayout/NLayoutContent import | build ✅；无 n-layout 元素残留（仅注释） |
| ③ 删 5 文件重复三件套 | `babd800` | SchoolLibrary/CompanySettings/DepartmentManagement/DataDashboard/ProcessStageRules 各删同块内第二份（缺 .page-container 的纯冗余副本） | build ✅；5 文件 `.page-header/.page-body` 2→1、`.page-container` 保留 1（磁盘已核） |
| ④ 全局 .page-title 26→22px | `da261aa` | glass.css `.page-title{font-size:22px!important}`（!important 保留） | build ✅ |

### 9.1 阶段③踩坑（已纠正，记入 MEMORY）
首版去重脚本用 `.*?=== \*/` 非贪婪匹配注释，回溯时吞掉了**第一份含 `.page-container` 的三件套**，导致 5 文件 `.page-header/.page-body` 2→0、布局 `display:flex` 丢失（全局 `.page-container` 仅 padding 无 flex，会回归）。
**修正**：`git checkout` 恢复 5 文件 → 改用 `[^*]*?` 限定注释内容不含 `*`，使注释无法跨过下一个 `/*` 吞掉第一份 → 重跑后 2→1、`.page-container` 保留 1。教训：删重块脚本**必须用非 `*` 字符类约束注释，并先核磁盘再提交**。

### 9.2 阶段③全局抽取未做（判断留档）
诊断 §6 阶段3 原含「22 页重复定义 → 全局/SettingsLayout :deep 抽取」。执行时**未做**，理由：
- 实测 22 页 `.page-body` gap **不统一**：19 页 `var(--space-4)`，3 个招聘提速页（阶段①已压为 `var(--space-3)`），另有 ProcessStageRules 等混杂。
- 盲抽要么回滚阶段①压缩、要么无验证改 19 页视觉，均需逐页回归。
- **结论**：去重（纯冗余）安全已交付；全局抽取留作独立 PR，逐页 diff gap 差异后单独推进。非半成品，是带证据的显式范围决策。

### 9.3 验证现状（诚实标注）
- ✅ 静态：`npm run build:nocheck` 四阶段均过；dev server 实时 CSS 校验（padding/!important/display:flex）已核。
- ⚠️ [R] 运行时：22 settings 页 1440×900 外边距一致性、侧栏折叠 64px、≤767px 移动端 overflow、各页 .page-body 单一滚动职责 —— **未真实浏览器逐页回归**。stylelint X-05：web/app 无 stylelint 配置，机验不可行，以 build 通过代证。
- ⚠️ [R] 阶段④ `.page-title` 22px 影响全项目 36 文件标题，属视觉回归项，待兵哥/dev 环境逐页确认。
