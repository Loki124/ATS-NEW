# ATS-NEW 前端规范与约定汇总（Frontend Rules Catalog）

> 生成时间：2026-10-15
> 适用范围：`web/app`（Vue 3 + TypeScript + Vite 5 + Naive UI 2.44.1 + UnoCSS）
> 文档性质：**规则索引与归纳**，不做逐文件源码讲解；每条给出要求、来源路径、关键正反例。
> 编写方式：全仓配置 + 规范文档 + 实际代码三方交叉验证；无配置的类目显式标注「未配置」。

> ⚠️ **阅读前必读：本仓存在「规范文档 ↔ 代码」已确认漂移。**
> 规范文档多为早期快照，`tokens.css` 已在其后被收紧（2026-10-15）。**冲突时以 `src/styles/tokens.css` 与实际代码为准**，并用 `getComputedStyle` 取真实解析值。
> 已定位的漂移（间距刻度、页面安全边距、弹窗内边距）见 `frontend-layout-standard.md`（§1.7 间距阶梯 / §1.1 页面安全边距 / §1.3 弹窗内边距），其数值以 `src/styles/tokens.css` §8 / §8.5 为准。

---

## 规则总览目录

| # | 章节 | 规则数 | 主要来源 |
|---|------|-------|---------|
| 1 | [技术栈与依赖管理](#1-技术栈与依赖管理) | 8 | `package.json` |
| 2 | [目录结构与文件命名](#2-目录结构与文件命名) | 12 | `src/` 实况 |
| 3 | [代码风格与格式](#3-代码风格与格式) | 7 | `eslint.config.js` |
| 4 | [Lint 与质量门禁](#4-lint-与质量门禁) | 9 | `.stylelintrc.json`、CI |
| 5 | [类型与类型检查](#5-类型与类型检查) | 7 | `tsconfig.json` |
| 6 | [组件编写规范](#6-组件编写规范) | 14 | `AGENTS.md` R-101~R-223 |
| 8 | [状态管理](#8-状态管理) | 6 | Pinia 实践 |
| 9 | [路由与权限守卫](#9-路由与权限守卫) | 8 | `router/index.ts` |
| 10 | [API 与数据层](#10-api-与数据层) | 9 | `utils/request.ts` |
| 11 | [资源与静态资源处理](#11-资源与静态资源处理) | 7 | `vite.config.ts` |
| 12 | [导入与依赖使用](#12-导入与依赖使用) | 7 | 全局 |
| 13 | [国际化（i18n）](#13-国际化i18n) | 6 | `locales/`、`locale-audit.mjs` |
| 14 | [测试与质量验证](#14-测试与质量验证) | 9 | `vitest.config.ts`、`playwright.config.ts` |
| 15 | [可访问性（A11y）](#15-可访问性a11y) | 8 | `UI_DESIGN_SPEC.md` §7 |
| 16 | [提交前检查与 Git 纪律](#16-提交前检查与-git-纪律) | 8 | `ENGINEERING_RULES.md` §8/§11 |
| 17 | [环境变量与配置](#17-环境变量与配置) | 7 | `config/index.ts` |
| 18 | [未配置项清单](#18-未配置项清单) | 9 | 全仓验证 |
| 19 | [来源文件索引](#19-来源文件索引) | — | — |

---

## 1. 技术栈与依赖管理

| 编号 | 要求 | 来源 |
|------|------|------|
| 1.1 | 包管理器为 **npm**（有 `package-lock.json`，CI 用 `npm ci`）。注意 `Makefile` 中 `install`/`web`/`test`/`lint` 目标调用 `pnpm`，与实际 npm 流程不一致，属已知历史遗留。 | `package-lock.json`、`Makefile` |
| 1.2 | `package.json` 设 `"type": "module"`，全部配置文件为 ESM。 | `package.json:5` |
| 1.3 | `postinstall` 跑 `patch-package`，本地补丁统一放 `patches/`（现有 `vueuc+0.4.65.patch`）。升级依赖后需复核补丁是否仍适用。 | `package.json:8`、`patches/` |
| 1.4 | 生产依赖 13 个，核心：vue 3.4 / vue-router 4.2 / pinia 2.1 / naive-ui 2.44.1 / vue-i18n 9.14.5 / axios 1.6 / dayjs / @vueuse/core / @vicons/ionicons5 / @wangeditor/editor / vue-draggable-plus。 | `package.json:31-44` |
| 1.5 | 图标库统一 `@vicons/ionicons5`（UnoCSS `presetIcons` 虽已配置但**未启用**，`warn:false`；实际图标走 vicons）。 | `uno.config.ts:24-27` |
| 1.6 | 升级 naive-ui 后**必须**跑 `npm run build` 并检查 `dist/assets/vendor-misc-*.js` 体积；超过 ~80KB（CI 断言 ≤100KB）说明 `manualChunks` 漏了新的间接依赖。 | `frontend-README.md:206-209`、CI `test-frontend` |
| 1.7 | 禁止 `import { xxx } from 'naive-ui/xxx'` 子路径导入，必须裸 `naive-ui`，否则 `optimizeDeps` 预构建不覆盖。 | `frontend-README.md:207` |
| 1.8 | 提交 `package-lock.json`；CI 中 `npm ci` 强一致安装。 | `.github/workflows/ci.yml` |

---

## 2. 目录结构与文件命名

### 2.1 目录结构（`src/` 共 21 个子目录，≈340 个文件）

```
src/
├── main.ts              # 入口：注册 pinia/naive/i18n/权限指令，hydrate 后才装 router
├── App.vue              # 根组件：n-config-provider / n-message-provider / n-dialog / n-loading-bar
├── App.css / index.css  # 根级样式
├── vite-env.d.ts        # Vite 环境类型声明
├── config/              # 统一配置（端口、API baseUrl、分页默认值）
├── api/         (54)    # 按业务域拆分的 API 客户端
├── pages/      (133)    # 路由页面，按业务域二级目录
├── components/ (80)    # 复用组件，含 common/ role/ dashboard/ metrics/ candidate/ reason-library/
├── composables/(14)    # use* 前缀的组合式函数
├── stores/      (8)     # Pinia store
├── services/    (2)     # 非 store 的服务层（app-version）
├── utils/      (17)     # 纯函数工具
├── router/      (2)     # 路由表 + 守卫
├── styles/      (6)     # tokens.css / glass.css / glass-modal.css / brand-tokens.css
├── locales/           # i18n 语言包
├── directives/         # v-permission 指令
├── plugins/            # naive-ui 全局注册
├── types/              # 全局类型声明
├── generated/          # 构建期生成（appVersion.ts，已 gitignore）
└── __tests__/          # 全局测试 setup
```

### 2.2 命名约定

| 编号 | 要求 | 来源 |
|------|------|------|
| 2.2.1 | Vue 组件：PascalCase，如 `ConditionTreeEditor.vue`、`RegionCascader.vue`。 | `components/` |
| 2.2.2 | Composable：`use` + PascalCase，如 `useTableColumns.ts`、`useCloseGuard.ts`（12/14 个符合）。 | `composables/` |
| 2.2.3 | API 模块：kebab-case 为主（`application-form.ts`、`campus-control` → `campusControl.ts`），**存在混用**（`addCandidate.ts`、`candidate-resume-fields.ts` 与 `candidate-info-table.ts` 并存）。新增建议 kebab-case。 | `api/` |
| 2.2.4 | Store：camelCase 单文件名（`user.ts`、`theme.ts`、`brand.ts`、`system.ts`），无 `useXxxStore.ts` 后缀。 | `stores/` |
| 2.2.5 | 样式文件名：kebab-case 语义名（`tokens.css`、`glass.css`、`glass-modal.css`）。 | `styles/` |
| 2.2.6 | 页面文件 PascalCase，目录按业务域 kebab-case（`pages/settings/`、`pages/candidate/`）。 | `pages/` |
| 2.2.7 | 组件支持二级业务子目录（`components/common/`、`components/role/`），跨域复用放 `common/`。 | `components/` |

---

## 3. 代码风格与格式

| 编号 | 要求 | 来源 |
|------|------|------|
| 3.1 | ESLint 9 flat config，作用域 `src/**/*.{vue,ts,js}` + 测试目录，排除 `dist*` / `node_modules` / `public` / `*.cjs`。 | `eslint.config.js:54-62` |
| 3.2 | 启用 `@eslint/js` recommended + `typescript-eslint` recommended + `vue/flat/recommended`。 | `eslint.config.js:11-13` |
| 3.3 | `ecmaVersion: 2022`，`sourceType: module`，全局环境 `browser` + `node`。 | `eslint.config.js:16-21` |
| 3.4 | 关闭的规则及原因（**有明确注释，非疏漏**）：`no-unused-vars`（存量未用导入多）、`no-explicit-any`（mock 与后端类型不全）、`vue/multi-word-component-names`（`Login`/`Layout` 单字名）、`no-undef`（交 TS 管）。 | `eslint.config.js:24-39` |
| 3.5 | 关闭的**风格类**规则：`html-self-closing`、`max-attributes-per-line`、`singleline-html-element-content-newline`、`html-indent`、`html-closing-bracket-newline`、`first-attribute-linebreak`。 | `eslint.config.js:33-38` |
| 3.6 | `vue/no-v-html: 'error'`（XSS 硬门禁）。需例外时必须 `// eslint-disable-next-line vue/no-v-html` + 安全审计（如 `OfferList.vue` 改用 sandbox iframe、`SafeHtml.vue`）。 | `eslint.config.js:30-32` |
| 3.7 | **未配置 Prettier**，全仓无 `.prettierrc` / `prettier.config.*`。格式化未做强制统一，缩进/引号风格由各文件自律（实际以 2 空格、单引号、无分号为主流）。 | 全仓验证 |

---

## 4. Lint 与质量门禁

| 编号 | 要求 | 来源 |
|------|------|------|
| 4.1 | `npm run lint` = `eslint . --fix`（本地自修）；`npm run lint:ci` = `eslint . --max-warnings=0`（CI 硬门禁，零容忍 warning）。 | `package.json:18-19` |
| 4.2 | `npm run lint:style` / `lint:style:ci` = `stylelint "src/**/*.{vue,css}"`。 | `package.json:22-23` |
| 4.3 | Stylelint 仅启用**自研**规则 `strict-color/strict-color-value`（插件 `stylelint-plugin-strict-color.cjs`），禁止裸像素颜色值。 | `.stylelintrc.json:2,10` |
| 4.4 | Stylelint 忽略 `dist` / `node_modules` / `brand-tokens.css` / `src/styles/tokens.css`（生成物豁免）。 | `.stylelintrc.json:12` |
| 4.5 | Stylelint `defaultSeverity: warning` —— 当前 **warn-only，不阻断合并**；`reportNeedlessDisables: false`。 | `.stylelintrc.json:13-14`、CI 注释 |
| 4.6 | `AGENTS.md` §6.2 建议的 `stylelint-declaration-strict-value`（强制 margin/padding/color/font-size 走令牌）**未实际安装**，属规范建议而非现状。 | `AGENTS.md:642-659` vs `package.json` |
| 4.7 | 品牌色门禁：`npm run tokens` / `npm run tokens:report`，CI 独立 job `brand-tokens` 跑 `node brand-tokens.mjs --brand "${BRAND_COLOR:-#6366F1}" --ci --out src/styles/brand-tokens.css`，退出码非 0 即阻断。 | `package.json:25-26`、`ci.yml` |
| 4.8 | i18n 审计：`npm run locale:audit`（检查 key 缺失/未翻译/空值/格式/key 前缀冲突/术语一致性）；`npm run locale:fix` 自动修。 | `package.json:20-21`、`scripts/locale-audit.mjs` |
| 4.9 | 可访问性门禁：`npm run audit:a11y` = `node e2e/a11y-smoke.mjs`（axe-core 运行时扫描）。 | `package.json:24` |

> ⚠️ `AGENTS.md` §6 明确禁止用 grep 做验证（正则子串匹配会漏报，如 `margin:140px` 因含 `40px` 逃逸），要求 AST/渲染工具。

---

## 5. 类型与类型检查

| 编号 | 要求 | 来源 |
|------|------|------|
| 5.1 | `strict: true` 全量严格模式。 | `tsconfig.json:14` |
| 5.2 | `target: ES2022`、`lib: [ES2022, DOM, DOM.Iterable]`、`module: ESNext`、`moduleResolution: bundler`。 | `tsconfig.json:3-8` |
| 5.3 | 路径别名 `@/*` → `./src/*`（在 `tsconfig.json`、`vite.config.ts`、`vitest.config.ts` 三处**同步声明**）。 | 三处配置 |
| 5.4 | `noUnusedLocals: false`、`noUnusedParameters: false` —— 显式关闭未用变量检查（与 ESLint `no-unused-vars: off` 呼应）。 | `tsconfig.json:15-16` |
| 5.5 | `noFallthroughCasesInSwitch: true`、`isolatedModules: true`、`skipLibCheck: true`、`noEmit: true`。 | `tsconfig.json:7-12,17` |
| 5.6 | 类型检查命令：`npm run typecheck` = `gen:version && vue-tsc --noEmit`；`npm run build` = `gen:version && vue-tsc && vite build`（**先类型后构建**）。 | `package.json:12,14` |
| 5.7 | `@wangeditor/editor-for-vue` 有 path 映射指向其 `dist/src/index.d.ts`（该包无标准类型入口）。 | `tsconfig.json:20` |

> **正例**：`tsconfig.json` 显式关闭两项 + 注释说明原因，属「有意为之」而非遗漏。
> **反例**：CI 曾用 `build:nocheck` 跳过 `vue-tsc`（等于类型检查作废），已修正为 `npm run build`（`ci.yml` 注释 R10/R11）。

---

## 6. 组件编写规范

### 6.1 交互状态完整性（P0）

| 编号 | 要求 | 来源 |
|------|------|------|
| 6.1.1 | 每个可交互组件 MUST 实现 default / hover / active / focus-visible / loading / disabled；按钮类额外实现 selected 与 danger 态。 | `AGENTS.md` R-101 |
| 6.1.2 | 异步提交类组件 MUST 在 loading 期间 `disabled`，防重复提交（`disabled` + `aria-busy`）。 | R-101 |
| 6.1.3 | 异步操作 MUST 覆盖加载/空/成功/失败四类反馈，MUST NOT 静默失败。 | R-104 |
| 6.1.4 | 破坏性操作按四级矩阵处理，**MUST NOT 一律用确认弹窗**：可逆→直接执行+乐观更新（禁确认框）；中等→直接执行+Toast 撤销（停留 5–8s）；高（批量删/清空）→确认框说明后果；不可逆→确认框+影响预览+二次验证。 | R-106 |
| 6.1.5 | 预计填写 >1 分钟的表单 MUST 自动保存草稿（localStorage，TTL ≤24h，提交成功立即清除），返回时提示「已恢复上次填写的内容」并提供「清空」出口。**MUST NOT 弹二次确认框**（草稿已在即弹窗违反 R-106）。 | R-105 |
| 6.1.6 | 含敏感字段（password/token/otp/cvv/idCard 等）的表单**整体禁用**草稿功能（不逐字段过滤）。检测用字段名 + `input[type=password]` 双保险。 | R-105 |
| 6.1.7 | 用户输入 MUST 转义输出，**禁用** `v-html`（ESLint error 门禁）。 | R-107 |
| 6.1.8 | 渲染条目 >200 MUST 虚拟滚动或分页。 | R-108 |
| 6.1.9 | 动态文本 MUST 有长度防御（`overflow-wrap: anywhere` / `ellipsis` / `-webkit-line-clamp`），截断处 MUST 提供查看完整信息途径（`title` 或展开按钮）。 | R-110 |
| 6.1.10 | 数据视图 MUST 覆盖完整状态机：首次引导/骨架屏/有数据/空态/搜索无结果/筛选无结果/**部分失败**/全部失败/离线/无权限/已达上限。部分失败时成功项正常展示、失败项就地给重试入口。 | R-111 |

**反例（R-105）**：
```js
// ❌ 敏感表单仍写草稿 → token 落盘
watch(values, () => saveDraft('login', values))
// ✅ 检测到敏感字段即整体豁免
if (hasSensitiveField(values)) return
```

### 6.2 尺寸与命中区

| 编号 | 要求 | 来源 |
|------|------|------|
| 6.2.1 | 触控目标 ≥44×44px；图标按钮视觉 28–32px，用 padding 或伪元素 `::after { inset: -6px }` 扩到 44px。 | R-102 |
| 6.2.2 | 320px 视口 MUST 无横向溢出，**禁止**固定像素宽度容器（用 `width:100% + max-width`）。 | R-103、X-12 |
| 6.2.3 | 按钮尺寸三档：小 28–32px（表格内/工具栏）/ 中 36–40px（默认推荐）/ 大 44–48px（表单提交、移动端主按钮）；左右内边距 12–24px。 | R-220、`UI_DESIGN_SPEC.md` §5.1 |
| 6.2.4 | 输入框高度三档：28–32 / 36–40（推荐）/ 48px；标签与输入框间距 4–8px，左右内边距 12–16px。 | `UI_DESIGN_SPEC.md` §5.10 |
| 6.2.5 | 多选 `<n-select multiple>` MUST 设 `max-tag-count="responsive"`，禁止手写 nowrap+省略号冒充折叠。**Code Review 把 `multiple` 缺 `max-tag-count` 视为阻塞项。** | `frontend-layout-standard.md` §1.8.5 |

**正例（多选折叠）**：
```vue
<n-select v-model:value="ids" multiple filterable clearable
          size="small" max-tag-count="responsive" />
```

### 6.3 弹窗与抽屉

| 编号 | 要求 | 来源 |
|------|------|------|
| 6.3.1 | 弹窗内容区/头部/底部内边距**已全局 token 化**，MUST NOT 被页面 scoped 清零。 | `frontend-layout-standard.md` §1.3 |
| 6.3.2 | 抽屉底部操作栏统一用全局类 `.drawer-footer`。 | 同上 |
| 6.3.3 | 含页签/步骤切换的弹窗 MUST 用**固定 `height`**（非 `max-height`），上限 `min(680px, calc(88vh - 头部高度))`，避免切换时高度跳动。 | R-223 |
| 6.3.4 | 确认类弹窗统一用 `useDialog().warning(...)`，**禁用原生 `confirm()`/`alert()`**。 | `UI_DESIGN_SPEC.md` §5.6 |
| 6.3.5 | `<n-modal>` 的 `mask-closable` 默认 `true`，含可编辑表单的弹窗 MUST 显式处理关闭守卫（用 `composables/useCloseGuard.ts`），防点遮罩静默丢草稿。 | `NAIVE_UI_PITFALLS.md` §6.1 |
| 6.3.6 | `preset="dialog"` 的 `@positive-click`/`@negative-click` 是**钩子**，返回真值（含 async 的 Promise）会触发自动关闭 → 竞态。正确接法：保留 `v-model:show`，且 `requestClose()` **所有分支 `return false`**，把关闭权完全交给守卫。 | `NAIVE_UI_PITFALLS.md` §6.2 |

**反例（R-223）**：
```vue
<!-- ❌ max-height：内容少时收缩，切页签跳动 -->
:content-style="{ maxHeight: 'calc(88vh - 140px)', overflowY: 'auto' }"
<!-- ✅ 固定 height -->
:content-style="{ height: 'min(680px, calc(88vh - 140px))', overflowY: 'auto' }"
```

### 6.4 Naive UI 组件使用约束

| 编号 | 要求 | 来源 |
|------|------|------|
| 6.4.1 | **无 `NSegmented`**（文档未导出但 vue-tsc 不报错）。替代：`<n-radio-group>` + `<n-radio-button>`。 | `NAIVE_UI_PITFALLS.md` §1.1 |
| 6.4.2 | `<n-card :title="null">` + `#header-extra` → header 整区不渲染。工具条放 body 内。 | §1.2 |
| 6.4.3 | `<n-card>` 内容溢出默认**不滚动**，须主动设滚动容器；flex item MUST `min-height: 0`。 | §1.3 |
| 6.4.4 | `n-radio` 的 `checked` 是 Boolean，MUST 用 `n-radio-group v-model:value`；决策法门：写 radio 先想 group。 | §2.1/§2.2 |
| 6.4.5 | `vue-draggable-plus` MUST `v-for` + 默认 slot，**禁 `#item` slot**（只渲染 `slots.default`，写错整片空白）；props 仅 `modelValue/tag/target`，`item-key` 是脏属性。 | §3.1/§3.2 |
| 6.4.6 | 图标 import 前 MUST 先 `ls node_modules/@vicons/ionicons5/ \| grep -i <kw>` 确认存在（如 `FastForwardOutline` 不存在，最接近的是 `PlaySkipForwardOutline`）。 | §4.1 |
| 6.4.7 | 浮层透明/残留排查 MUST 用 Playwright `getComputedStyle + outerHTML` 看真实层级，不靠 grep 推测。修法优先级：移除样式 > 转移样式 > 兜底隐藏。 | §5.4 |

**反例（v-model 误用）**：
```vue
<!-- ❌ checked 是 Boolean，绑字符串模型会报 type check failed -->
<n-radio v-model:checked="condForm.matchType" value="ALL" />
<!-- ✅ 用 group 绑 value -->
<n-radio-group v-model:value="condForm.matchType">
  <n-radio value="ALL">全部满足</n-radio>
</n-radio-group>
```

### 6.5 按钮与图标一致性

| 编号 | 要求 | 来源 |
|------|------|------|
| 6.5.1 | **同组按钮必须全有 icon 或全无**，禁止「管理权限/编辑/停用/删除」中 2 带 2 不带。 | `frontend-layout-standard.md` §1.8.1 |
| 6.5.2 | 语义化图标映射：管理权限→`ShieldCheckmarkOutline`/`KeyOutline`；编辑→`CreateOutline`；停用→`BanOutline`；删除→`TrashOutline`（+ `type="error"`）。 | 同上 |
| 6.5.3 | 同视图图标 MUST 来自同一图标库、同一视觉风格（线性/面性）、同一笔触粗细，MUST NOT 混用。 | R-216、X-17 |
| 6.5.4 | 无文字图标 MUST 有 `aria-label`/`title`/tooltip 说明含义；纯装饰图标 MUST `aria-hidden="true"`。 | R-217、X-18 |
| 6.5.5 | 图标尺寸 MUST 控制在 ≤4 个固定等级（14–16 / 18–20 / 24 / 32+），禁止无级缩放。 | R-219、X-19 |
| 6.5.6 | 图标与文字间距 4–8px；同组图标视觉重量需平衡。 | `UI_DESIGN_SPEC.md` §5.9 |
| 6.5.7 | **禁止 emoji 当功能图标**（X-02）。 | X-02、`frontend-README.md:128` |
| 6.5.8 | 每屏恰好 1 个 primary action（实心按钮），其余降级为 ghost/text；危险操作与主操作保持 ≥32px 距离。 | R-202 |

## 8. 状态管理

| 编号 | 要求 | 来源 |
|------|------|------|
| 8.1 | 状态管理用 **Pinia 2.1**，store 放 `src/stores/`，按业务域划分（user / theme / brand / system / department / demand / addCandidate）。 | `stores/`、`main.ts:37` |
| 8.2 | 命名 camelCase 单文件名，无 `useXxxStore` 后缀。 | `stores/` |
| 8.3 | `app.use(createPinia())` 在 `app.use(router)` **之前**注册。 | `main.ts:37,124` |
| 8.4 | **启动顺序铁律**：`app.use(router)` MUST 下移到 store hydrate 完成之后。Router install 会立即触发首次导航，若此时 userStore 未 hydrate，守卫读到的 `roles` 是空数组 → 角色受限页误弹 `/forbidden`。 | `main.ts:42-45,121-124` |
| 8.5 | 主题 store MUST 在 Vue mount **之前**调 `init()`（从 localStorage 恢复品牌色 + 暗色），否则初始渲染用旧值闪烁。 | `main.ts:64-66` |
| 8.6 | 用户状态 hydrate 两步：① 同步从 localStorage rehydrate（accessToken/refreshToken/user）→ ② 有 token 时 `await ensureReady()` 调 `/me` 用服务端数据覆盖（防 stale localStorage 卡死 RBAC）。失败 401/403 登出，网络抖动保留快照。 | `main.ts:80-108` |

**正例（启动顺序）**：
```ts
app.use(createPinia())
app.use(naivePlugin); app.use(i18n)
setupPermissionDirective(app)
await _userStore.ensureReady()   // hydrate 先完成
app.use(router)                   // router 最后装
app.mount('#app')
```

---

## 9. 路由与权限守卫

| 编号 | 要求 | 来源 |
|------|------|------|
| 9.1 | Vue Router 4，**history 模式** `createWebHistory()`（**无参**）。注意：其无参形式读页面 `<base href>`，而 `web/app/index.html` **未声明该标签**，故实际回退 `/`，**不读** `import.meta.env.BASE_URL` —— 这使路由 base 与 Vite 的 `base`（生产 `/static/`）解耦，是刻意设计。 | `router/index.ts:1`、`index.html` |
| 9.2 | **全部页面路由 MUST 懒加载**，且每个 `import()` MUST 带 `webpackChunkName` 注释（用于 chunk 分组）。 | `router/index.ts:17` 起 |
| 9.3 | 路由分组：login / forbidden / register → layout（`/`）→ dashboard / list-[domain] / settings 嵌套布局。 | `router/index.ts:13-32,122` |
| 9.4 | `requiresAuth` MUST 挂在**父路由**，守卫用 `to.matched.some(r => r.meta?.requiresAuth)` 检查整条匹配链（子路由不重复声明）。 | `router/index.ts:32,262` |
| 9.5 | `meta.roles` 是**允许访问的角色白名单**；`SUPER_ADMIN` 始终放行。角色取 `userStore.user.roles`（后端 emit `string[]`），兼容读派生的 `roleType`。 | `router/index.ts:286-308` |
| 9.6 | 角色常量 MUST 从 `utils/role.ts` 的 `ROLE_GROUPS` 引用，禁在路由里硬编码角色字符串数组。 | `router/index.ts:136` 等 |
| 9.7 | 守卫内有 `ensureReady()` 门闸兜底（与 `main.ts` 共享同一 in-flight promise），保证 F5/直达 URL 不误判 `/forbidden`。 | `router/index.ts` 注释、`main.ts:101-103` |
| 9.8 | 模块移除时 MUST 保留旧深链 `redirect`（对标 `metric-library → /settings/metrics`、`offers → /candidates`），避免历史链接 404。 | `router/index.ts:84-86` |

**正例（角色引用）**：
```ts
{ path: 'users/all', name: 'UserDirectoryAll',
  component: () => import(/* webpackChunkName: "settings-users-all" */ '...'),
  meta: { roles: [...ROLE_GROUPS.SUPER_ADMIN_ADMIN] } }
```

---

## 10. API 与数据层

| 编号 | 要求 | 来源 |
|------|------|------|
| 10.1 | **统一 HTTP 客户端**：`utils/request.ts` 导出共享单例 `api` + `createApi(opts)` 工厂（供特殊 timeout/baseURL）。业务请求 MUST 走此实例。 | `utils/request.ts:161-199` |
| 10.2 | 请求拦截器集中注入 `Authorization`（从 localStorage 读 `accessToken`/`token`，幂等）与 `X-Recruit-Type`（运行时读 `useSystemStore().current`，切系统下次请求即生效）。 | `request.ts:31-42` |
| 10.3 | 401 MUST 走「refresh 换新 access + 重试原请求」；模块级 `isRefreshing` 保证并发只刷一次，其余请求排队订阅。登录/刷新自身不重试（防循环）。 | `request.ts:112-159` |
| 10.4 | 404 语义为「后端 app 缺」不是「权限问题」，仅 `console.warn` 不弹 toast；500 区分 `db_schema_out_of_sync`（提示跑 migrate）与普通 bug。 | `request.ts:169-192` |
| 10.5 | API 路径用 `'/xxx'` 即可（`baseURL` 已是 `/api/v1`），**不要再加 `/api/` 前缀**。 | `frontend-README.md:177` |
| 10.6 | **禁止 raw fetch**，统一用 `api.get/post/...`。 | `frontend-README.md:131` |
| 10.7 | 成功态裸 JSON 对象由 `normalizeEnvelopeMeta` 补 `success/message/code` 元数据；**不搬迁 payload、不自动 reject `success:false`**（交调用方判定）。数组/Blob/原始值不处理。 | `request.ts:44-71` |
| 10.8 | 错误处理统一用 `useMessage()` 的 `message.error(e.message)`。 | `frontend-README.md:132` |

---

## 11. 资源与静态资源处理

| 编号 | 要求 | 来源 |
|------|------|------|
| 11.1 | `base` 按 mode 分：`development` → `'/'`，生产 → `'/static/'`（对齐 Django `STATIC_URL` + whitenoise）。dev MUST 用 `/`，否则 SPA 深链会被 whitenoise 拦截。 | `vite.config.ts:84` |
| 11.2 | 构建 `target: 'es2022'`（`main.ts` 用 top-level await，es2020 不支持）。`outDir: 'dist'`，`sourcemap: false`。 | `vite.config.ts:127-132` |
| 11.3 | **手动分块**（`manualChunks`）：`vendor-rich-editor`（wangEditor + 约 30 个微包）→ `vendor-naive-ui`（naive-ui 全生态，**必须同 chunk**，否则 TDZ 白屏）→ `vendor-vue` → `vendor-icons` → `vendor-unocss` → `vendor-misc`；`src/utils/`+`src/api/` → `app-utils`。 | `vite.config.ts:136-193` |
| 11.4 | 产物文件名 MUST 含 hash：`assets/[name]-[hash].js`。 | `vite.config.ts:191-192` |
| 11.5 | `optimizeDeps.include: ['naive-ui']`（dev/prod 行为一致，防求值顺序重排触发 TDZ）。 | `vite.config.ts:123-125` |
| 11.6 | dev 代理：`config.api.baseUrl` 与 `/media` 均代理到 `config.backend.url`（避免前端跨端口直连 8000）。 | `vite.config.ts:106-116` |
| 11.7 | **版本文件唯一写入器** `scripts/gen-version.mjs` 双写 `src/generated/appVersion.ts` + `public/version.json`；缺一即失步 → 升级弹窗无限弹。两者 MUST NOT 分开写。 | `vite.config.ts:8,59-76` |
| 11.8 | `public/` 仅放免编译静态资源（现 `version.json`、`vite.svg`）；产物分析用 `ANALYZE=1 npm run analyze` 生成 `dist/stats.html`。 | `vite.config.ts:89-97` |

**正例（手动分块防 TDZ）**：
```ts
// naive-ui 生态 + 间接依赖必须同 chunk，否则 rollup 重排求值顺序 → Cannot access 'ma' before initialization → 白屏
if (id.includes('naive-ui') || id.includes('@css-render') || id.includes('seemly') /* ... */) return 'vendor-naive-ui'
```

---

## 12. 导入与依赖使用

| 编号 | 要求 | 来源 |
|------|------|------|
| 12.1 | 路径别名统一 `@/`（`src/` 内），三处配置同步：`tsconfig.json` paths、`vite.config.ts` resolve.alias、`vitest.config.ts` resolve.alias。 | 三处配置 |
| 12.2 | 样式导入顺序固定（`main.ts:13-18`）：UnoCSS → reset → tokens.css → glass.css → glass-modal.css → index.css。 | `main.ts` |
| 12.3 | 组件导入 MUST 走统一注册（`plugins/naive.ts` 的 `naivePlugin`），保证测试可复用。 | `main.ts:11`、`plugins/naive.ts` |
| 12.4 | **禁止**对 axios 做全局猴子补丁。`X-Recruit-Type` 原由 `main.ts` 劫持 `axios.create` 注入，已于 2026-09-29 移除，改由 `request.ts` 与 `api/auth.ts` 各自的请求拦截器运行时注入。 | `main.ts:28-33` |
| 12.5 | naive-ui 组件 MUST 用 `vue-tsc` 能校验到的实际导出；不确定存在性先查（无 `NSegmented`）。 | `NAIVE_UI_PITFALLS.md` §1.1 |
| 12.6 | **MUST NOT** 手写 `import { xxx } from 'naive-ui/xxx'` 子路径。 | `frontend-README.md:207` |
| 12.7 | 图标 import 前 MUST `ls` 确认存在（未确认会是 Vite 编译错误而非运行时缺失）。 | `NAIVE_UI_PITFALLS.md` §4.1 |

---

## 13. 国际化（i18n）

| 编号 | 要求 | 来源 |
|------|------|------|
| 13.1 | i18n 用 **vue-i18n 9**，`legacy: false`（Composition API：`useI18n()` 取 t，模板 `$t`）。 | `locales/index.ts:15` |
| 13.2 | 默认语言 **zh-CN**（契合 R-222 用户可见文案优先中文）；en-US 作兜底/可切换，缺失键回退 zh-CN。 | 同上 |
| 13.3 | **必须 `await ensureLocaleLoaded()` 后再 `app.mount()`**，避免首屏闪烁。 | `main.ts:111` |
| 13.4 | 大字典（`REASON_LIBRARY_*`/`DATA_PERM_*`/`APP_UI_*`）已拆到 `locales/domains/<locale>.<CONST>.ts` **按域异步加载**；启动只加载当前语言分片，切换时懒加载。`language.ts` 极小保持静态导入。 | `locales/index.ts:11-19` |
| 13.5 | 扁平 dot-key 字典经 `toNested()` 转嵌套；**key 前缀冲突 MUST 避免**（叶子 key 同时是分组前缀会互吞，vue-i18n 只回显 key），dev 环境有 `console.warn` 守卫。 | `locales/index.ts:21-52`、`locale-audit.mjs` 检查项 5 |
| 13.6 | `locale-audit.mjs` 五项检查：key 缺失 / 未翻译（英文值残留中文）/ 空值 / 格式不一致（中英标点混用、全半角括号）/ key 前缀冲突。另有**术语表一致性**检查（同一概念必须同一译法，如「原因库」→`Reason Library`）。 | `scripts/locale-audit.mjs` |
| 13.7 | R-222：用户可见文案 MUST 用简体中文，禁非必要英文。白名单：品牌/产品名、文件格式名（PDF/CSV）、技术协议与路径（URL/HTTP 头名）、行业缩写与系统代码（ID/HRBP/`SUPER_ADMIN`）、表达式关键字、设计代码术语（仅开发者界面）。 | `AGENTS.md` R-222 |

**现状提示**：i18n 已接入 110 个文件，但页面层仍有大量硬编码中文文案，i18n 覆盖率推进中（项目待办 P2）。

---

## 14. 测试与质量验证

### 14.1 单元测试（Vitest）

| 编号 | 要求 | 来源 |
|------|------|------|
| 14.1.1 | Vitest 2.1，`environment: 'happy-dom'`，`globals: true`，`setupFiles: ['./src/__tests__/setup.ts']`。 | `vitest.config.ts:13-18` |
| 14.1.2 | 测试文件纳入 `src/**/*.{test,spec}.ts`；排除 `node_modules`/`dist`/`e2e`。 | 同上 |
| 14.1.3 | 测试文件放**被测模块同级的 `__tests__/`**（`composables/__tests__/`、`utils/__tests__/`、`components/common/__tests__/` 等），统一 `.test.ts` 后缀（少数 `.spec.ts` 如 `utils/permissionMenu.spec.ts`）。 | 全仓 |
| 14.1.4 | **覆盖率门禁**：statements 70 / branches 55 / functions 65 / lines 70，低于阈值 CI 失败（防「测试越写越少还判绿」）。 | `vitest.config.ts:19-30` |
| 14.1.5 | `npm test` = `vitest run`；CI 用 `npm test -- --coverage`（html 报告落 artifact）。 | `package.json:9`、`ci.yml` |

### 14.2 E2E（Playwright）

| 编号 | 要求 | 来源 |
|------|------|------|
| 14.2.1 | Playwright `testDir: './e2e'`，`fullyParallel: true`，`timeout: 30s`，`reporter: 'list'`；CI 下 `forbidOnly` + `retries: 2` + `workers: 1`。 | `playwright.config.ts:14-22` |
| 14.2.2 | `baseURL: 'http://127.0.0.1:5212'`；`webServer` 自动起 `npx vite --host 127.0.0.1`，超时 60s，本地 `reuseExistingServer: !CI`。 | 同上 |
| 14.2.3 | **全局一次性登录**：`globalSetup: './e2e/auth.setup.ts'` + `storageState: e2e/.auth/state.json`，避免 e2e 反复登录触发后端 429 限流。 | `playwright.config.ts:22-27` |
| 14.2.4 | `trace: 'on-first-retry'`，`screenshot: 'only-on-failure'`；报告上传 artifact（`if: always()`）。 | 同上、`ci.yml` |
| 14.2.5 | 仅 chromium 项目（`Desktop Chrome`）。 | `playwright.config.ts:31-33` |
| 14.2.6 | e2e 截图 `e2e/__shots__/` 与 `e2e/.auth/`（含 token）**禁止提交**，已 gitignore。 | `web/app/.gitignore` |
| 14.2.7 | 命令：`npm run e2e` / `e2e:ui` / `e2e:install`（装 chromium）。 | `package.json:27-29` |

### 14.3 运行时验证纪律

| 编号 | 要求 | 来源 |
|------|------|------|
| 14.3.1 | UI 交互改动 MUST 用 headless Chromium 实测真实 DOM/拖拽/console，**不得以「沙箱无浏览器」为借口**。 | `ENGINEERING_RULES.md` §11 |
| 14.3.2 | 布局/边距改动 MUST 用 `getComputedStyle` 硬证据确认（如 `.page-container` 解析 padding = 24px），**不靠目测**。 | `frontend-layout-standard.md` §4 |
| 14.3.3 | 端到端通过 ≠ 某一行代码生效：多层兜底修复 MUST 按层设计用例隔离证明。 | `ENGINEERING_RULES.md` §6 |
| 14.3.4 | 中文多模式 grep **禁用 Bash grep**（本机反复假空），一律用 Grep 工具。 | `ENGINEERING_RULES.md` §11 |
| 14.3.5 | `AGENTS.md` §0.2 定义三级可验证性：`[S]` static（lint/AST 可判定，MUST 自证）、`[R]` runtime（需浏览器，MUST 输出「未验证」）、`[H]` human（MUST 输出「需人工确认」）。**禁止对 [R]/[H] 打 ✅（验证剧场）。** | `AGENTS.md` §0.2/§7.3/§7.4 |

---

## 15. 可访问性（A11y）

| 编号 | 要求 | 来源 |
|------|------|------|
| 15.1 | 基线 **WCAG 2.1 AA**：普通文字对比度 ≥4.5:1；大文字（≥24px，或 ≥18.66px 且 `font-weight≥700`）可放宽至 3:1。**19px 常规字重不属大文本，仍按 4.5:1。** | `AGENTS.md` R-109、`UI_DESIGN_SPEC.md` §7 |
| 15.2 | 焦点可见：全局 `:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px }`。 | `UI_DESIGN_SPEC.md` §7.2 |
| 15.3 | 所有交互元素 MUST 可 Tab 访问；焦点顺序 MUST 跟随 DOM 顺序；**MUST NOT** 用 `tabindex > 0`，**MUST NOT** 响应式下用 `order`/`grid-template-areas` 重排可聚焦元素。 | R-109 |
| 15.4 | 错误信息 MUST NOT 仅依赖颜色表达（颜色 + 图标 + 文字，至少两种通道）。 | R-109、R-221 |
| 15.5 | 交互元素 MUST 用语义化标签（`<button>`/`<a>`/`<h1>`–`<h6>`）；图片 MUST 有 `alt`；装饰图标 `aria-hidden="true"`。 | R-109、R-217 |
| 15.6 | 语义地标：内容区包 `<main id="main">` + skip-link；极光背景等装饰设 `aria-hidden`。 | `UI_DESIGN_SPEC.md` §5.7/§2.6 |
| 15.7 | 每个输入框 MUST 有可见 `<label>`（非仅 placeholder）；必填项统一 `*`；辅助说明用 `aria-describedby` 关联。 | R-218、X-11 |
| 15.8 | 动效降级：`@media (prefers-reduced-motion: reduce)` 内将 animation/transition-duration 降至近 0。 | `UI_DESIGN_SPEC.md` §7.5 |
| 15.9 | 运行时验证：`npm run audit:a11y`（axe-core，三档视口 320/768/1200）。 | `package.json:24`、`AGENTS.md` §6.4 |

---

## 16. 提交前检查与 Git 纪律

### 16.1 前端门禁链（顺序即 CI 顺序）

```
npm run lint:ci      # eslint --max-warnings=0   零容忍 warning
npm run lint:style    # stylelint（当前 warn-only）
npm run build         # gen:version && vue-tsc && vite build（含类型检查）
npm test -- --coverage # vitest + 覆盖率阈值门禁
node brand-tokens.mjs --ci   # 品牌色对比度门禁
npx playwright test   # e2e（需后端已启动）
```

| 编号 | 要求 | 来源 |
|------|------|------|
| 16.1.1 | CI 用 `lint:ci`（不带 `--fix`）—— CI 里自动改文件会造成「本地干净、CI 也绿，但改动没提交」的幽灵状态。 | `ci.yml` R11 注释 |
| 16.1.2 | CI **不再**使用 `build:nocheck` 逃生口（原跳过 vue-tsc 等于类型检查作废）。 | `ci.yml` R10 注释 |
| 16.1.3 | 品牌色令牌生成独立 job `brand-tokens`，`--ci` 退出码非 0 直接阻断合并。 | `ci.yml` |
| 16.1.4 | e2e job 依赖 `test-frontend`，后端启动**轮询 `/health/`**（最多 60s）而非死等 `sleep 5`。 | `ci.yml` R11 |
| 16.1.5 | 本地 `make test` / `make lint` / `make doctor` 提供与 CI 对齐的能力。 | `Makefile` |
| 16.1.6 | 拉完代码/切分支/加新 app 后先跑 `make doctor`（迁移漂移 + 待应用迁移 + 服务健康）。 | `Makefile` |
| 16.1.7 | 交付前 MUST 跑真实浏览器实测（MUST NOT 只靠静态检查）。 | `ENGINEERING_RULES.md` §11 |
| 16.1.8 | 完成 UI 代码后 MUST 按 `AGENTS.md` §7 输出自检结果表（[S] 给依据、[R] 输出未验证、[H] 输出需人工确认）；**任何 P0 未通过 MUST NOT 交付**。 | `AGENTS.md` §7 |

### 16.2 Git 纪律（项目级，与前端共用）

| 编号 | 要求 | 来源 |
|------|------|------|
| 16.2.1 | **禁 `git add -A`**，逐路径 add。 | `ENGINEERING_RULES.md` §8 |
| 16.2.2 | 同文件连续 Edit，每条之后 grep 验证落盘（避免「以为改了其实没改」的假绿）。 | 同上 |
| 16.2.3 | 提交前必跑 `git log` + `git status` 核实——并行会话会替本会话 commit。 | 同上、§11 |
| 16.2.4 | 同文件混他人改动时禁整文件 add：需按 hunk 精确 `git apply --cached` 裁出自己的改动。 | 项目纪律 |
| 16.2.5 | `push` 待用户授权；未明确说「推」之前不 push。 | 项目纪律 |

### 16.3 产物与忽略

| 编号 | 要求 | 来源 |
|------|------|------|
| 16.3.1 | 忽略：`node_modules/`、`dist*/`、`*.tsbuildinfo`、`*.timestamp-*.mjs`、`coverage/`、`playwright-report/`、`test-results/`、`e2e/.auth/`、`e2e/__shots__/`、`src/generated/`、`public/version.json`。 | `web/app/.gitignore` |
| 16.3.2 | 根 `.gitignore` 另忽略 `.env*`、`*.key`/`*.pem`/`secrets/`、`.workbuddy/`、临时 QA 脚本（`qa-*.mjs`/`test-*.mjs`）、`.run-pids/`/`.run-logs/`。 | `.gitignore` |
| 16.3.3 | 建议清理仓库根目录的 90+ 个 `vite.config.ts.timestamp-*.mjs` 临时产物（虽已 gitignore，但污染工作区）。 | `web/app/` 实况 |

---

## 17. 环境变量与配置

| 编号 | 要求 | 来源 |
|------|------|------|
| 17.1 | 统一配置真源 `src/config/index.ts`，导出 `config` 对象与 default export。**禁止**在业务代码里散写端口/URL。 | `config/index.ts` |
| 17.2 | 前端端口 **5212**（`config.frontend.port`），后端 **8000**（`config.backend.port`）。 | 同上 |
| 17.3 | API baseUrl = `/api/v1`，timeout 15000ms。 | 同上 |
| 17.4 | 分页默认值：`defaultPageSize: 10`，`pageSizeOptions: ['10','20','50','100']`（注：`useTablePagination` 默认 `TABLE_PAGE_SIZE=20`，两处并存）。 | `config/index.ts`、`USE_TABLE_PAGINATION.md` |
| 17.5 | 环境变量：**前端仅 `VITE_BACKEND_URL`** 一个（多 worktree 预览用，`scripts/devstack.sh` 依赖）；兼容 Node `process.env` 与浏览器 `import.meta.env`。 | `config/index.ts:21-27` |
| 17.6 | dev-only 调试钩子：`import.meta.env.DEV` 时挂 `window.__ats.theme.{setBrand,setMode,reset,get}`，供浏览器 console / 自动化测试用。**MUST NOT** 在生产暴露。 | `main.ts:68-78` |
| 17.7 | `import.meta.env.DEV` 亦用于 i18n key 冲突守卫（仅 dev 告警）。 | `locales/index.ts:38,48` |

---

## 18. 未配置项清单

以下类目经全仓验证**确实无配置**，标注为「未配置」而非臆造：

| 类别 | 状态 | 说明 |
|------|------|------|
| **Prettier / 格式化器** | ❌ **未配置** | 全仓无 `.prettierrc*` / `prettier.config.*`，`package.json` 无 `prettier` 依赖。缩进/引号/分号风格无强制统一。 |
| **Git Hooks（Husky / lint-staged）** | ❌ **未配置** | 无 `.husky/`、无 `lint-staged`、无 `pre-commit` 脚本。提交前检查全靠人工自觉 + CI。 |
| **Commitlint / 提交信息规范** | ❌ **未配置** | 无 `commitlint.config.*`，无 `commit-msg` hook。 |
| **EditorConfig** | ❌ **未配置** | 无 `.editorconfig`。 |
| **Storybook / 组件文档站** | ❌ **未配置** | 无 `.storybook/`。组件规范靠 `docs/04-ui/` Markdown 承载。 |
| **ESLint 自动化测试** | ❌ **未配置** | `eslint.config.js` 无 rulesdir/test block，无 `RuleTester`/`FlatCompat` 测试。 |
| **stylelint 令牌强制（间距/字号）** | ⚠️ **建议未落地** | `AGENTS.md` §6.2 要求 `stylelint-declaration-strict-value` 强制 margin/padding/font-size 走令牌，但 `package.json` 未安装该插件；当前只有 `strict-color` 一条自定义规则，且 warn-only。 |
| **E2E 多浏览器** | ⚠️ **仅 chromium** | `playwright.config.ts` 只配 `chromium` 项目，无 firefox/webkit。 |
| **Vitest UI / 浏览器模式** | ❌ **未配置** | 无 `@vitest/ui`，无 `browser` mode；仅 happy-dom。 |
| **bundle 体积硬阈值** | ⚠️ **部分** | `chunkSizeWarningLimit: 1500`（仅 Vite warning）；CI 有 `vendor-misc ≤100KB` 断言，但**无整体 bundle 大小门禁**。 |
| **前端覆盖率趋势 / 逐文件阈值** | ⚠️ **仅全局** | `vitest.config.ts` 只设全局 thresholds，无 `perFile`、无变更覆盖率门禁。 |
| **安全漏洞扫描** | ⚠️ **已配置（CI 层）** | `ci.yml:416` 有 `security-scan` job（Trivy，`severity: CRITICAL,HIGH`，`exit-code: '1'` 真阻断，`ignore-unfixed: true`）。但**本地无 `npm audit` 脚本**，也无 license 检查 / dependabot / 定时扫描（仅 push/PR 触发）。 |

---

## 19. 来源文件索引

### 19.1 权威规范源（以 L0–L5 为准）

> 🔴 UI 规范权威层级**唯一裁决标准**为 `docs/04-ui/README.md` 的 L0–L5 表（2026-10-18 收敛裁定，详见 `docs/06-runbook/ENGINEERING_RULES.md` §14）。下表仅列本索引覆盖文档的**定位**，不再另立优先级；`AGENTS.md` 为 **L1 行为约束**（不写数值），数值真源为 L0 `tokens.css`。

| 层级 | 文件 | 定位 |
|------|------|------|
| L0 | `web/app/src/styles/tokens.css` + `brand-tokens.mjs` | 设计令牌唯一真源（数值只此一处） |
| L1 | `AGENTS.md`（仓库根） | UI 交互约束（R-101~R-223 + X-01~X-19 + P0/P1/P2），**行为/取舍权威，不写数值** |
| L2 | `docs/04-ui/UI_DESIGN_SPEC.md` | 统一设计规范 v2.3：色彩/排版/间距/组件/响应式/A11y/Do-Don't |
| L3 | `docs/04-ui/frontend-layout-standard.md` + `SETTINGS_PAGE_STRUCTURE.md` | 布局契约 / 设置页结构规范 |
| L4 | `NAIVE_UI_PITFALLS.md` / `MODAL_DIVIDER_CONVENTION.md` / `USE_TABLE_PAGINATION.md` / `DROPDOWN_POPOVER_SPEC.md` / `STANDARD_RESUME_SETTINGS.md` / `DATA_DICT_ADD_OBSCURED.md` | 专项规范（独立主题，保留） |
| L5 | `docs/04-ui/README.md` | 04-ui 目录**唯一索引** |
| — | `docs/06-runbook/ENGINEERING_RULES.md` | 工程铁律与代码假绿坑（跨前后端工程规则，非 UI 规范层级内） |
| — | `docs/06-runbook/frontend-README.md` | 前端 README（历史文档，Naive UI 拆分规则仍有效） |

> 📦 以下文档已于 2026-10-18 归档至 `docs/09-archive/ui-docs-2026-10-18/`，**不再作为规范依据**：`frontend-DESIGN.md`、`UI_INDEX.md`、`UI_RECONCILIATION.md`、`UI_REMEDIATION_PLAN.md`、`UI_COMPLIANCE_SELFCHECK.md` 等共 16 份（见 `UI_DOC_AUDIT_2026-10-18.md`）。

### 19.2 配置文件

| 文件 | 作用 |
|------|------|
| `web/app/package.json` | 依赖 + 24 个 script（dev/build/typecheck/lint/test/e2e/tokens/locale 等） |
| `web/app/eslint.config.js` | ESLint 9 flat config |
| `web/app/.stylelintrc.json` | Stylelint + 自研 strict-color 插件 |
| `web/app/stylelint-plugin-strict-color.cjs` | 裸像素颜色检查实现 |
| `web/app/tsconfig.json` / `tsconfig.node.json` | TS 严格模式 + 路径别名 |
| `web/app/vite.config.ts` | base/代理/分块/optimizeDeps/版本插件 |
| `web/app/uno.config.ts` | UnoCSS 主题（映射 CSS 变量）+ safelist |
| `web/app/vitest.config.ts` | happy-dom + 覆盖率门禁 |
| `web/app/playwright.config.ts` | e2e + globalSetup 登录复用 |
| `web/app/brand-tokens.mjs` | 品牌色 OKLCH 生成器（CI 门禁） |
| `web/app/scripts/gen-version.mjs` | 版本文件唯一写入器（双写） |
| `web/app/index.html` | SPA 挂载点 `#app`（**无 `<base href>`**），含 `theme-color` / `color-scheme: light dark` 元信息 |
| `.github/workflows/ci.yml` | 5 个 job：test-frontend / brand-tokens / e2e / test-backend / migration-drift |
| `Makefile` | 本地 make test/lint/doctor/status |

**CI 全量 job（7 个，`.github/workflows/ci.yml`）**：`test-backend`（:17）、`test-frontend`（:110）、`brand-tokens`（:154）、`e2e`（:179）、`test-migrations`（:281）、`migration-drift`（:361）、`security-scan`（:416，Trivy 扫 CRITICAL/HIGH 且 `exit-code: '1'` 真阻断）。触发条件：`push` + `pull_request`。其中 `e2e` / `test-backend` / `test-migrations` / `migration-drift` 均挂 `mysql:8.0` service。

### 19.3 关键源码约定落点

| 文件 | 承载的约定 |
|------|-----------|
| `src/main.ts` | 启动顺序铁律（hydrate → router → mount）、i18n 预载、全局 errorHandler、dev 钩子 |
| `src/config/index.ts` | 配置唯一真源 |
| `src/utils/request.ts` | HTTP 收敛、拦截器注入、401 刷新状态机、信封归一 |
| `src/router/index.ts` | 懒加载 + chunkName、meta.roles 白名单、requiresAuth 匹配链 |
| `src/composables/useTableColumns.ts` | 表格列对齐单一真源（四档规则 + 操作列规格） |
| `src/composables/useTablePagination.ts` | 分页统一（含受控失效坑规避） |
| `src/composables/useCloseGuard.ts` | 弹窗关闭守卫（所有分支 return false） |
| `src/composables/useDraft.ts` / `useFormDraft.ts` | 草稿保存（含敏感字段整体豁免） |
| `src/directives/permission.ts` | `v-permission` 元素级最小权限 |
| `src/plugins/naive.ts` | Naive UI 统一注册 |
| `src/styles/tokens.css` | 设计令牌单一真源（含 §8.5 布局令牌） |
| `src/styles/glass.css` | 玻璃态原子类 + 布局契约 + 弹窗三区内边距 |
| `src/styles/glass-modal.css` | 弹窗/抽屉玻璃化扩展 |
| `src/styles/brand-tokens.css` | 生成物（gitignore，不手改） |
| `src/locales/index.ts` | i18n 实例 + toNested + 按域异步加载 |
| `src/components/SafeHtml.vue` | v-html 的安全替代（ESLint 豁免路径） |

---

## 附：变更影响面速查

改动以下内容时，**MUST** 同步检查的关联点：

| 改动 | 需同步检查 |
|------|-----------|
| 品牌色输入 | `tokens.css` / `brand-tokens.css` / `uno.config.ts` / `App.vue themeOverrides` / `stores/brand.ts` |
| 布局令牌 | `tokens.css §8.5` / `glass.css` / 所有页面 scoped（防 `!important` 被覆盖） |
| 新增 API 模块 | 走 `request.ts` 的 `api`/`createApi`，禁自建 axios 实例 |
| 新增页面 | `router/index.ts`（懒加载+chunkName+meta.roles）/ i18n / 分页走 `useTablePagination` / 表格列走 `useTableColumns` |
| 新增多选框 | `max-tag-count="responsive"`（阻塞项） |
| 新增弹窗 | `useCloseGuard` / 固定 `height`（非 max-height）/ 不清零全局内边距 |
| 升级依赖 | `npm run build` 查 `vendor-misc` 体积 / `patches/` 是否仍适用 |

---

**文档维护建议**：本文档为规则索引，规范细节以 §19.1 各权威源为准。修改规范时 MUST 同步更新对应来源文件与本索引，避免口径分叉。
