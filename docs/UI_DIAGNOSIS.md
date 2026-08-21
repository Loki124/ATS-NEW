# ATS-NEW 前端 UI 诊断报告

> 设计系统架构师 Diana · 2026-08-21 · 配合 `web/app/DESIGN.md`（液态玻璃 v1.0-draft）
> 探查范围：`web/app/src` 全部页面/组件/主题配置与 `uno.config.ts`、`src/styles/tokens.css`。

## 0. 一句话结论

项目 UI **未形成统一系统**，当前并存 **4 套视觉语言 + 3 套品牌色**，玻璃拟态仅落地在 2 个文件中，其余 ~40 个页面仍是 Naive UI 默认扁平白卡。需以液态玻璃为单一系统，先统一 token 与主题，再逐页迁移。

## 1. 现状：并存的视觉语言（实证）

| # | 视觉语言 | 落地位置 | 关键特征 |
|---|---|---|---|
| A | 深色灰应用框架 | `pages/Layout.vue` | 侧栏 `#1f2937` 实底 + 白色顶栏 + 内容区 `#f9fafb`；菜单激活态**金色** `#FBCE5B` |
| B | 橙色 OKLCH 工作台 | `pages/Dashboard.vue` + `components/dashboard/*` | 用 `tokens.css` 的 `--color-accent: oklch(70% 0.18 45)`（≈`#FF7A45`）；StatBar 每卡换色（amber/rose/sky/emerald） |
| C | 靛紫玻璃（新方向） | `pages/settings/CampusControl.vue` | 极光底 + `backdrop-filter` 玻璃面板/KPI 卡 + 靛紫渐变 `#6366F1` |
| D | 纯金渐变登录 | `pages/Login.vue` | 背景 `linear-gradient(#FBCE5B,#E5B82A)`；登录卡写 `backdrop-filter:blur(10px)` 但压在**实色金底**上 = 无效玻璃 |

**三套品牌色并存的铁证**
- 金：`uno.config.ts` `primary:#FBCE5B` + `App.vue` `themeOverrides.primaryColor:#FBCE5B` + `Layout.vue` 激活菜单/Logo。
- 橙：`tokens.css` `--color-accent: oklch(70% 0.18 45)`（被 StatCard/Hero/AI 头像消费）。
- 靛紫：`CampusControl.vue` 硬编码 `#6366F1/#A855F7/#EC4899`。

## 2. 问题归类（按优先级）

### P0 — 系统性不一致（用户跨页即感知）
1. **品牌色三分裂**：金/橙/靛紫，无主从。用户从 Login(金)→工作台(橙)→校招管控(紫)像换了三个产品。
2. **玻璃是孤岛不是系统**：仅 CampusControl + Login 接触玻璃；Login 的玻璃还因实色底失效。其余页面默认白卡。
3. **应用框架（深灰侧栏）与玻璃系统不兼容**：深灰实底 + 金激活，无法与浅色极光玻璃共存；是「第四套视觉」。
4. **设计 token 三源**：`uno.config.ts`(金) / `tokens.css`(橙 OKLCH) / 组件内硬编码(紫)。改一处全站不联动。

### P1 — 可维护性 / 一致性缺陷
5. **玻璃参数未抽象**：`blur(10/20px)`、`opacity .55/.6/.62`、圆角 `14/16/18px` 在 CampusControl 内散落硬编码，无变量，难复刻。
6. **Naive 主题未延伸玻璃**：`Card/Modal/Drawer/Input/Table` 均无玻璃变体；表格在玻璃面板内仍是实白条纹（玻璃+白卡视觉打架）。
7. **圆角语言冲突**：全局 `borderRadius:8px`、Card `12px`、CampusControl `18px`、Login `16px` —— 无统一节奏。
8. **类型层级未落地**：`tokens.css` 的 `--text-*` 几乎未被消费；页面用任意 px（26/32/13/16…），无排版韵律。

### P2 — 响应式 / 可访问性 / 动效
9. **KPI 行无响应式**：`CampusControl` `.kpi-row{grid-template-columns:repeat(4,1fr)}` 移动端挤压；仅 Login 有一处 `@media`。
10. **动效无统一缓动**：`tokens.css` 有 `--ease-out` 但 CampusControl 用 `transition:all .2s`（无缓动），Login 用 keyframe float，节奏不一。
11. **无暗色模式**：液态玻璃在暗色极光上表现最佳，当前全站仅浅色，未发挥风格优势（可选）。
12. **`backdrop-filter` 前缀**：CampusControl 已带 `-webkit-`；需确保后续组件统一带前缀，覆盖 Safari/微信内核。

## 3. 根因

- 历史：先有「金色 Ant 主题」(`App.vue`/`uno.config`)，后加 `tokens.css`(橙) 做工作台，再在 CampusControl 试水「aceternity 靛紫玻璃」——三次局部演进都只动了自己那块，**从未回头统一全局 token 与主题**。
- 缺单一事实来源：颜色/模糊/圆角散落在三处配置 + 组件硬编码，无治理约束。

## 4. 诊断附带的「已可用资产」

- `CampusControl.vue` 的极光 + 玻璃面板实现，是液态玻璃方向的**现成样板**，可顺势对齐本规范后外推。
- `tokens.css` 已有 4pt 间距、OKLCH 色、缓动变量骨架，扩展成本低。
- `Dashboard.vue` 已有 `2fr/1fr → 单列` 的响应式骨架，可复用。
