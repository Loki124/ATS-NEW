# ATS-NEW 液态玻璃 UI 改造 · 研发执行清单

> 状态：**PM 已确认，转研发执行** · 设计系统架构师 Diana · 2026-08-21
> 总纲：`web/app/DESIGN.md`（规范）｜`docs/UI_DIAGNOSIS.md`（诊断）｜`docs/UI_OPTIMIZATION_PLAN.md`（方案）
> 预览：`web/app/liquid-glass-preview.html`（顶栏含品牌取色器 + 暗色切换，供逐条对照）

## 执行原则（务必先读）
1. **单一事实来源** = `src/styles/tokens.css` + `App.vue` 的 `themeOverrides`。任何新颜色/模糊/圆角必须先进 token，组件只引用变量。
2. **不改 Naive UI 源码**：仅通过 `themeOverrides` + 包裹 class 调整，避免升级冲突。
3. **灰度顺序**：阶段 1（全局）→ 阶段 2（框架）→ 阶段 3（逐页）→ 阶段 4（收口）。CampusControl 已玻璃，先对齐规范再外推。
4. **退路**：玻璃底统一保留不透明兜底，`backdrop-filter` 失效也不崩可读性。
5. **品牌换肤**：只动 `--brand` 一处（hover/pressed/dark 经 `color-mix` 派生）；暗色切 `body.dark`。

## 环境 / 验证命令
```bash
cd web/app
npm run dev          # 本地预览（Vite :5212，注意仅监听 IPv6 localhost）
npm run build        # vue-tsc 类型检查 + 构建（门禁）
npm run lint:ci      # ESLint 零警告
# 视觉回归：浏览器开 localhost:5212，对照 liquid-glass-preview.html 逐项核对
```

---

## 阶段 1 — 全局统一（低风险，全站即时生效）★ 先行

### T1.1 扩充 `tokens.css`（玻璃/极光/品牌/暗色变量）
- 文件：`src/styles/tokens.css`
- 动作：在 `:root` 增补 §2 全量变量（`--brand` 系列 + `color-mix` 派生 + `--glass-*` + `--aurora-*` + `--shadow-*` + 语义 `--c-*-soft`）；在 `body.dark` 增补暗色变量集（DESIGN.md §2 Dark Mode Token Set）；保留旧 `--color-accent` 橙色做过渡别名，标记 `@deprecated`。
- 完成标准：所有颜色/模糊/圆角均来自变量，无页面内硬编码。

### T1.2 `uno.config.ts` 改品牌 + 卡片快捷类
- 文件：`uno.config.ts`
- 动作：`theme.colors.primary.DEFAULT` 改 `#6366F1`（并 dark/pressed）；`shortcuts.card-base` 由 `bg-white rounded-xl shadow-sm` 改为引用 `.glass-card`（见 T1.4）；`safelist` 增 `text-brand/bg-brand/border-brand`。
- 完成标准：`primary` 全站联动为靛紫；`card-base` 即玻璃。

### T1.3 `App.vue` themeOverrides（Naive 组件玻璃化 + 换肤）
- 文件：`src/App.vue`
- 动作：`common.primaryColor = '#6366F1'`、`primaryColorHover/Pressed/Suppl` 由 `--brand` 同值计算；`textColorPrimary` 改 `#fff`；`borderRadius: '16px'`；`Card/Button/Input/Modal/Drawer/Table` 加玻璃 override（背景 `var(--glass-bg-card)`、圆角、边框 `var(--glass-border)`）。主题从「金」整体切「靛」。
- 完成标准：原生 `n-button/n-card/n-input` 呈玻璃质感，激活态非金。

### T1.4 新增 `src/styles/glass.css`（玻璃原子类）
- 文件：新建 `src/styles/glass.css`，在 `main.ts` 引入（紧接 `tokens.css` 之后）。
- 动作：落地 `.glass-panel / .glass-card / .glass-input / .btn-primary/.btn-secondary/.btn-ghost/.btn-danger / .app-aurora / .gradient-title`，含 `::before` 顶部高光、`-webkit-backdrop-filter` 前缀、不透明兜底。
- 骨架见文末附录 A（可直接复制）。
- 完成标准：原子类可被任意组件 `class="glass-card"` 复用。

### T1.5 `Layout.vue` 框架入系统
- 文件：`src/pages/Layout.vue`
- 动作：侧栏/顶栏改 `.glass-panel` 材质；删 `#1f2937` 实底；菜单激活态金 `#FBCE5B` → 品牌靛（`rgba(99,102,241,.14)` + 3px `--brand` accent bar）；Logo 金渐变 → 品牌渐变；Avatar `bg-primary` 已联动。
- 完成标准：深灰侧栏消失，框架与玻璃系统一致。

### T1.6 自定义品牌色运行时机制（换肤）
- 文件：`src/styles/tokens.css` + `src/App.vue` + 设置页入口
- 动作：确认 `--brand` 为唯一输入、`color-mix` 派生生效；提供运行时注入点（设置接口返回 brand → `document.documentElement.style.setProperty('--brand', v)`；或租户白标初始化时设置）。`App.vue` 的 `themeOverrides` 读同一变量计算。
- 完成标准：运行时改 `--brand` 全站（含 Naive 组件、渐变标题、极光主光斑）即时联动，无残留硬编码色。

### T1.7 暗色模式
- 文件：`src/styles/tokens.css` + `App.vue`/设置
- 动作：`body.dark` 变量集已就绪（T1.1）；实现主题开关（持久化 localStorage + 跟随 `prefers-color-scheme`），切换 `body.dark`。
- 完成标准：🌗 切换正常，玻璃呈拉丝深玻璃；刷新保持；系统切换联动。

> **阶段 1 门禁**：`npm run build` + `npm run lint:ci` 通过；Login/工作台/校招管控/设置四处（浅+暗）风格一致。

---

## 阶段 2 — 应用框架与极光底色
- **T2.1** `App.vue`/`App.css`：根容器挂 `.app-aurora` 极光层（z-index 0），内容区透明（替换 `#f9fafb`）。
- **T2.2** `Layout.vue` + `components/common/GlobalSearch.vue`：全局搜索 Modal、通知、用户下拉包玻璃容器 + 模态毛玻璃遮罩。
- **T2.3** `Login.vue`：金渐变底 → 极光底；登录卡改有效玻璃（透出极光），删无效 `blur(10px)` 压实色。

---

## 阶段 3 — 业务页迁移（逐批：先对齐 DESIGN.md 再替换）
- **T3.1 工作台**：`Dashboard.vue` + `components/dashboard/*` —— `n-card`→`.glass-card`；StatBar 多色(amber/rose/sky/emerald)→品牌+语义四态；Hero 标题改 `.gradient-title`。
- **T3.2 校招管控对齐**：`CampusControl.vue` —— 已玻璃，仅把散落硬编码（`blur(20px)`/`#6366F1`/`18px`）抽成 `tokens.css` 变量，消除魔法值。
- **T3.3 设置中心**：`pages/settings/*`（25+ 页）—— `card-base`/白卡→`.glass-card`；表单/表格玻璃化。
- **T3.4 招聘主流程**：`candidate/interview/offer/onboarding/invitation/resume/scraped/*` —— 列表表格玻璃化、Modal/Drawer 玻璃、按钮 `.btn-*`。
- **T3.5 通用件**：`components/common/*`（StatusTag/ScorePanel/ResumeCard…）—— tag/卡片玻璃化、状态色走语义变量。

---

## 阶段 4 — 响应式 / 动效 / 收口
- **T4.1** `CampusControl.vue`：KPI 行 `repeat(4,1fr)` → `4→2→1` 响应式（≤1024 两列 / ≤560 单列）。
- **T4.2** 动效统一 `var(--ease-out)`，删 `transition:all .2s` 裸值。
- **T4.3** 全量巡检 `backdrop-filter` 带 `-webkit-` 前缀（grep 扫描）。
- **T4.4** 删历史色：金 `#FBCE5B`、橙 `oklch(...45)` 别名与残留硬编码（全局 grep）。
- **T4.5** ~~暗色模式~~（已并入 T1.7）。

---

## 验收清单（回检）
- [ ] 全站仅 1 个品牌色（金/橙硬编码数 = 0）。
- [ ] 所有 `n-card`/容器为玻璃材质，无扁平白卡与玻璃混排。
- [ ] 侧栏/顶栏为玻璃，激活态为品牌靛（非金）。
- [ ] 自定义换肤：运行时改 `--brand` 全站联动（含 Naive 组件与原生渐变），无残留硬编码。
- [ ] 暗色模式：`body.dark` 切换正常、拉丝深玻璃；开关持久化 + 跟随系统。
- [ ] KPI/卡片 ≤768px 正常折叠。
- [ ] `backdrop-filter` 全带 `-webkit-` 前缀。
- [ ] 视觉回归：Login/工作台/校招管控/设置（浅+暗）四处风格一致。
- [ ] `npm run build` + `npm run lint:ci` 通过，`vue-tsc` 零错误。

## 风险与回滚
- 阶段 1 为配置层，风险低；若需回滚，git revert 阶段 1 提交即可，不影响业务页。
- 阶段 3 页多，逐批提交 + 每批视觉回归；单页回滚不影响其他页。
- 玻璃性能：低端机 `blur` 可统一降至 10px（改 `tokens.css` 一处）。

## 附录 A — `glass.css` 落地骨架（可直接复制）
```css
.glass-panel{position:relative;background:var(--glass-bg-panel);backdrop-filter:blur(var(--glass-blur-panel));
  -webkit-backdrop-filter:blur(var(--glass-blur-panel));border:1px solid var(--glass-border);
  border-radius:var(--radius-lg);box-shadow:var(--shadow-panel);}
.glass-panel::before{content:'';position:absolute;inset:0;border-radius:inherit;pointer-events:none;
  background:linear-gradient(180deg,rgba(255,255,255,.5),rgba(255,255,255,0) 40%);}
body.dark .glass-panel::before{background:linear-gradient(180deg,rgba(255,255,255,.08),rgba(255,255,255,0) 40%);}
.glass-card{position:relative;background:var(--glass-bg-card);backdrop-filter:blur(var(--glass-blur-card));
  -webkit-backdrop-filter:blur(var(--glass-blur-card));border:1px solid var(--glass-border);
  border-radius:var(--radius-md);box-shadow:var(--shadow-card);padding:var(--space-4);}
.glass-input{background:var(--glass-bg-input);border:1px solid var(--glass-border);border-radius:var(--radius-sm);
  padding:9px 12px;color:var(--ink);backdrop-filter:blur(var(--glass-blur-input));-webkit-backdrop-filter:blur(var(--glass-blur-input));}
.glass-input:focus{border-color:var(--brand);box-shadow:0 0 0 3px color-mix(in srgb,var(--brand) 18%,transparent);outline:none;}
.btn-primary{background:linear-gradient(135deg,var(--brand),var(--brand-grad-a));color:#fff;border:1px solid rgba(255,255,255,.35);
  border-radius:var(--radius-md);padding:10px 18px;font-weight:600;box-shadow:0 4px 14px color-mix(in srgb,var(--brand) 32%,transparent),inset 0 1px 0 rgba(255,255,255,.4);
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);transition:all var(--duration-base) var(--ease-out);}
.btn-primary:hover{box-shadow:0 6px 20px color-mix(in srgb,var(--brand) 45%,transparent);transform:translateY(-1px);}
.btn-secondary{background:var(--glass-bg-card);border:1px solid var(--glass-border);color:var(--ink);border-radius:var(--radius-md);padding:10px 18px;}
.btn-secondary:hover{border-color:var(--brand);color:var(--brand);}
.btn-ghost{background:transparent;color:var(--ink-soft);border:1px solid transparent;border-radius:var(--radius-md);}
.btn-ghost:hover{background:rgba(15,23,42,.04);color:var(--ink);} body.dark .btn-ghost:hover{background:rgba(255,255,255,.06);}
.btn-danger{background:var(--c-error-soft);border:1px solid rgba(239,68,68,.3);color:var(--c-error);border-radius:var(--radius-md);padding:10px 18px;}
.gradient-title{background:linear-gradient(135deg,var(--brand),var(--brand-grad-a) 55%,var(--brand-grad-b));
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;}
.app-aurora{position:fixed;inset:0;z-index:0;pointer-events:none;background:var(--aurora-base);}
.app-aurora::before,.app-aurora::after,.app-aurora span{content:'';position:absolute;border-radius:50%;filter:blur(70px);}
```
