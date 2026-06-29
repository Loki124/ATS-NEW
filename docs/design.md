# ATS 项目设计 DNA (Dashboard / Studied-DNA)

> 来源: 公开的"北森 HR 仪表板"截图 (Beisen ATS HR Dashboard) —— 企业级 HR 招聘工作台参考图。
> 适用页面: `/dashboard` (登录后首页, 由 `pages/Dashboard.vue` 承载)。

## Provenance

- **Image mode**: 北森 HR 工作台截图 (公开 SaaS 参考, 非商业素材)。卡片 widget 网格、左主右辅、信息密度中等、左右非对称。
- **Intent**: 招聘官登录后第一眼看到"今天最重要的几件事 + 关键招聘指标 + 快捷入口"。参考图把"AI 助手问候"放在顶部 (H5 Letter Hero 模式), 把 4 个数字 stat、招聘日程 (周历)、雷达访问职位 (Job Radar)、快捷入口 (Quick Entry)、重要事项 (Tabbed Matters) 放在一起。
- **工作台模式 (Workbench)** 含义: 一个屏幕呈现招聘官今天必看的全部信息; 不需要跳出 dashboard 就能进入下一动作 (查看简历/查看职位/打开面试/处理待办)。

## System

- **Macrostructure**: **Workbench** —— 顶部 AI 助手 hero + 中部 2-column 网格 (左主右辅) + 底部 tabbed matters 面板。
- **Theme**: studied-DNA (锁死的视觉基因, 见 Tokens)。
  - **Display** (h1/h2): `PingFang SC` Medium 500
  - **Body** (正文, 卡片标题, 列表项): `PingFang SC` Regular 400
  - **Label** (stat 数字, 标签, 微文案): `PingFang SC` Medium 500
  - **辅文/meta**: `PingFang SC` Regular 400, ink-faint
- **Type role split**: 一个 sans 家族, 用字重 + 字号分角色 (不引第二个字体家族)。
- **Accents**: warm-orange (`oklch(70% 0.18 45)`, ~`#FF7A45`) 作为"提醒/待办/紧急 stat"小色块; 整页 accent 占比 ≤ 5% (small footprint)。
- **Neutral palette**: paper (`oklch(98% 0.005 240)`) + ink (`oklch(20% 0.02 240)`) + soft (`45%`) + faint (`70%`)。两极对比清晰 (亮纸面 + 暗墨字), 中间靠字重和 spacing 区分层级。
- **Surface depth**: 两种表面 —— `surface-raised` (卡片, 纯白) + `surface-sunk` (区块背景, 极淡冷调灰)。靠背景 + 1px hairline border 区分层级, 不用阴影。

## Tokens

> 集中导出在 `frontend/src/styles/tokens.css`, 用 CSS 变量消费。设计 token 不在 JS 里 (避免动态切换主题的复杂度, 单一企业主题)。

### Color

```css
--color-paper:        oklch(98% 0.005 240);  /* 页面底色, 极淡冷调 */
--color-ink:          oklch(20% 0.02 240);   /* 主文字, 近黑 */
--color-ink-soft:     oklch(45% 0.015 240);  /* 次级文字 */
--color-ink-faint:    oklch(70% 0.01 240);   /* 标签/微文案 */
--color-accent:       oklch(70% 0.18 45);    /* warm-orange, 提醒/数字/图标 */
--color-accent-soft:  oklch(95% 0.05 45);    /* accent 浅背景 (stat 卡片) */
--color-surface-raised: oklch(100% 0 0);     /* 卡片, 纯白 */
--color-surface-sunk:   oklch(96% 0.008 240);/* 区块背景, 卡片之间的灰 */
--color-border-hairline: oklch(92% 0.01 240);/* 1px 分隔线 */
```

### Spacing (4pt scale)

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-6: 24px;
--space-8: 32px;
--space-12: 48px;
--space-16: 64px;
```

卡片间距: `16-24px` (medium-dense)。Hero 内部 padding: `24-32px`。

### Type scale

```css
--text-display: 2.5rem;   /* hero 大标题 (40px) */
--text-h1:      2rem;      /* 页面 h1 (32px) */
--text-h2:      1.5rem;    /* 区块 h2 (24px) */
--text-h3:      1.25rem;   /* 卡片标题 (20px) */
--text-body:    0.875rem;  /* 正文 (14px) */
--text-meta:    0.75rem;   /* 标签/meta (12px) */
```

### Radius

```css
--radius-sm:   6px;       /* 标签、小按钮 */
--radius-md:   12px;      /* 卡片 (标准) */
--radius-lg:   20px;      /* hero / 大面板 */
--radius-pill: 9999px;    /* 头像 / chip */
```

### Easing (motion)

```css
--ease-out:    cubic-bezier(0.16, 1, 0.3, 1);
--ease-in:     cubic-bezier(0.55, 0, 1, 0.45);
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
```

## Layout (Dashboard)

```
┌─────────────────────────────────────────────────────────────────┐
│ Hero (H5 Letter): AI 助手小森 + 问候 + "查看更多" 按钮            │  ← surface-sunk, radius-lg
├──────────────────────────────────────────┬──────────────────────┤
│  4 Stat cards (待初筛/待处理 x3)         │  搜索栏                │
│                                          │  雷达访问职位 (JobCard)│
│  招聘日程 (周历 7 列)                     │  快捷入口 (2x2 grid)   │
│                                          │  我发的筛选 (列表)      │
├──────────────────────────────────────────┴──────────────────────┤
│ 重要事项 (tabbed panel):                                       │
│  招聘需求相关 | 职位相关 | 面试相关 | Offer相关 | 推荐相关 | 其他│
└─────────────────────────────────────────────────────────────────┘
```

- **Asymmetry**: 左主 2/3 (stats + 日历) + 右辅 1/3 (雷达 + 快捷 + 筛选)。
- **Density**: medium-dense, 卡片间距 16px, 内部 padding 16-20px。
- **Stacking**: hero 居顶 (full width), 中部 2-column, 底部 tabbed panel (full width)。

## Notes

- **中文企业 SaaS**: 文案全部中文, 不引 i18n 库。`PingFang SC` / `Microsoft YaHei` fallback chain。
- **Naive UI 集成**: 不替换品牌主色 (保留 `App.vue` 的 `#FBCE5B` 金色主题), Dashboard 内部用 tokens.css 控制"warm-orange accent + paper 背景", 形成"系统主色金黄"与"工作台暖橙"的清晰分工 (主导航 = 系统品牌, 工作台 = 业务内容)。
- **数据流**: 优先用现有 API (`/api/candidates`, `/api/positions`, `/api/demands`, `/api/recruitment-processes`), 数据为空/失败时优雅 fallback mock (不报红, 不阻塞渲染)。所有 fallback 集中于 `frontend/src/api/dashboard.ts`。
- **Motion**: 卡片首次进入用 `fade-up + stagger` (0.04s/step), ease-out, 默认 reveal。`.workbench-card { animation: fade-up 320ms var(--ease-out) both; }`。
- **无 grain / riso / glass / 阴影**: 保持 clean enterprise SaaS 风格, 仅用 hairline border + 表面差区分层级。
- **工作流**: 登录 → 落地 `/dashboard` → 看 stat 决定下一步 (处理 21 份待初筛) → 点 stat 跳 `/candidates?status=PENDING`; 或看右辅快捷入口直达我关注的简历/已锁定的应聘者。
