# ATS-NEW UI 规范与审查文档
> 最后更新：2026-10-19（规范合并压缩：UI_DESIGN_SPEC + frontend-layout-standard + 4 份专项 → 单一 `UI_STANDARD.md`）

本目录是 ATS-NEW 前端 UI 规范的**唯一权威索引**。所有 UI 规范、设计令牌、布局契约的权威来源按下列层级组织；新增 / 修改 UI 前须先读对应层级文档，并按设计令牌（`tokens.css`）执行。

## 三步使用法

1. **查层级** —— 先看下方 L0–L5 表，定位这件事该由哪一层裁决。
2. **按场景取文档** —— 查「按场景决策」表：做什么 → 读哪份 → 怎么验证。**不必通读全目录。**
3. **写完验证** —— 跑 `npm run tokens:audit`（必须 exit 0），确认没有复制令牌数值、没有引用不存在的令牌名。

```bash
cd web/app && npm run tokens:audit   # CI 同款门禁，本地改样式前必跑
```

> 只想快速写样式？读 L1 `AGENTS.md` §1–§3（自动注入，行为约束）+ 打开 L0 `tokens.css` 查令牌名即可；规范正文按需查 L2/L3。

## 权威层级（L0 → L5，冲突时自上而下裁决）

| 层级 | 文档 / 文件 | 性质 | 冲突裁决 |
|---|---|---|---|
| L0 | `web/app/src/styles/tokens.css` + `brand-tokens.mjs` | **唯一真源**：颜色/间距/圆角/阴影/动效数值只此一处定义 | 一切以 L0 为准 |
| L1 | `AGENTS.md`（仓库根） | Agent 可读约束：行为取舍、P0/P1/P2 规则，**不写数值** | 数值冲突 → 退回 L0 |
| L2 | `UI_STANDARD.md` | 人类可读设计规范合并版（色彩/排版/布局/组件/弹窗/表格分页/响应式/A11y/Do-Don't + 功能页附录） | 引用 L0，不复制数值 |
| L3 | `UI_STANDARD.md` §5（布局契约）+ `SETTINGS_PAGE_STRUCTURE.md` | 布局契约 / 设置页结构规范 | 数值引用 L0 |
| L4 | 专项规范：`NAIVE_UI_PITFALLS.md` / `DROPDOWN_POPOVER_SPEC.md` | 独立主题，保留 | 不偏离 L0/L2 |
| L5 | 本文件（`docs/04-ui/README.md`） | **唯一索引**，不含规范正文 | — |

> 🔴 **令牌铁律**：数值只允许出现在 L0（`tokens.css`）。任何文档 MUST 只引用令牌名 + 用途，**MUST NOT 复制数值**；与 L0 冲突一律以 `tokens.css` 为准。复制数值会随代码演进漂移 → AI 照文档写的 CSS 变量不存在 → 静默失效。门禁 `npm run tokens:audit` 防回归。

## 按场景决策（做什么 → 读哪份 → 怎么验证）

> 不知道该读哪份时，**先查这张表**，不要通读全目录。

| 我要做的事 | 必读 | 验证方式 |
|---|---|---|
| 写任何样式 / 用设计令牌 | L0 `tokens.css` → L1 `AGENTS.md §1` | `npm run tokens:audit`；令牌名先读文件确认存在 |
| 定颜色 / 品牌色 / 暗色 | L2 `UI_STANDARD.md` §2 | 派生色由 `brand-tokens.mjs` 生成，禁手写 |
| 排版 / 字号 / 行高 / 字体 | L2 `UI_STANDARD.md` §3 | 字号走 `--text-*`，禁写死 px |
| 新建或改页面布局、栅格、断点 | L3 `UI_STANDARD.md` §5 | 页面安全边距走 `--page-pad-*`，禁 scoped 覆盖 |
| 改设置页 | L3 `SETTINGS_PAGE_STRUCTURE.md` | 含 Shell/工具条/表格/弹窗统一结构 |
| 做弹窗 / 抽屉 / 遮罩 | L3 `UI_STANDARD.md` §5.4 + §6（分隔线） | 内边距走 `--modal-pad-*`；禁清零全局内边距 |
| 做表格 / 分页 | L4 `UI_STANDARD.md` §8.2 + L2 `§7.5` | 列对齐走 `useTableColumns.ts` |
| 做下拉 / Select / Popover | L2 `UI_STANDARD.md` §7.8 + L4 `DROPDOWN_POPOVER_SPEC.md` | — |
| 写交互行为 / 状态 / 无障碍 | L1 `AGENTS.md §2–§3` | 交互组件须覆盖 default/hover/active/focus/loading/disabled |
| 踩 naive-ui 坑 / 组件联动异常 | L4 `NAIVE_UI_PITFALLS.md` | — |
| 改依赖 / 构建 / 目录命名 | 本文件下方「技术栈与依赖管理」 | `npm run build` 查 `vendor-misc` 体积 |

## 文档清单

| 文档 | 层级 | 用途 | 阅读顺序 |
|---|---|---|---|
| `UI_STANDARD.md` | L2/L3 | 统一设计规范合并版 v1.0：色彩/排版/布局/组件/弹窗/表格分页/响应式/A11y/Do-Don't/功能页附录 | ① 必读 |
| `SETTINGS_PAGE_STRUCTURE.md` | L3 | 设置页统一页面结构规范 v1.0（Shell/标题/KPI/工具条/表格/弹窗/多 tab/自检） | ① 设置页改前必读 |
| `FRONTEND_RULES_CONSOLIDATED.md` | — | 规则索引（技术栈/命名已迁入本索引下方；其余章节为归纳参考，其 §19.1 权威表以本索引 L0–L5 为准） | ② 参考 |
| `NAIVE_UI_PITFALLS.md` | L4 | naive-ui 组件坑与联动异常专项 | 按需 |
| `DROPDOWN_POPOVER_SPEC.md` | L4 | 下拉 / Select / Popover 统一规范 | 按需 |

## 强制约束（强制项，请大声读出来）

1. **唯一输入源是 `tokens.css`**：颜色 / 间距 / 圆角 / 阴影 / 动效时长一律走 CSS 变量；改品牌色只改 `--brand` 一处。**禁止**硬编码 hex / rgb / 模糊值。
2. **暗色靠变量集切换**：组件 CSS 不写 dark 分支；切 `body.dark` 即整体换肤。
3. **玻璃元素必须**带 `-webkit-backdrop-filter` + 不透明兜底。
4. **新组件**必须复用 `.glass-* / .btn-* / .kpi-* / .toolbar / .page-header` 全局类，不另起一套。
5. **禁用原生 `confirm() / alert()`**：用 `useDialog().warning(...)`。

## 维护者

@兵哥（产品 / 前端设计）。改动规范前先在群里过一遍，避免破坏下游 20+ 设置页一致性。

—— 最近一次修订：2026-10-19

---

## 技术栈与依赖管理

> 以下两节自 `FRONTEND_RULES_CONSOLIDATED.md` §1 / §2 迁入（2026-10-18 收敛），为该内容的**唯一权威落点**；原文件 §1/§2 已删除。技术栈与命名约定经与真实 `package.json`、`src/` 核对无误。

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

## 目录结构与命名约定

### 目录结构（src/ 共 21 个子目录，≈340 个文件）

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
├── utils/      (17)    # 纯函数工具
├── router/      (2)     # 路由表 + 守卫
├── styles/      (6)     # tokens.css / glass.css / glass-modal.css / brand-tokens.css
├── locales/           # i18n 语言包
├── directives/         # v-permission 指令
├── plugins/            # naive-ui 全局注册
├── types/              # 全局类型声明
├── generated/          # 构建期生成（appVersion.ts，已 gitignore）
└── __tests__/          # 全局测试 setup
```

### 命名约定

| 编号 | 要求 | 来源 |
|------|------|------|
| 2.2.1 | Vue 组件：PascalCase，如 `ConditionTreeEditor.vue`、`RegionCascader.vue`。 | `components/` |
| 2.2.2 | Composable：`use` + PascalCase，如 `useTableColumns.ts`、`useCloseGuard.ts`（12/14 个符合）。 | `composables/` |
| 2.2.3 | API 模块：kebab-case 为主（`application-form.ts`、`campus-control` → `campusControl.ts`），**存在混用**（`addCandidate.ts`、`candidate-resume-fields.ts` 与 `candidate-info-table.ts` 并存）。新增建议 kebab-case。 | `api/` |
| 2.2.4 | Store：camelCase 单文件名（`user.ts`、`theme.ts`、`brand.ts`、`system.ts`），无 `useXxxStore.ts` 后缀。 | `stores/` |
| 2.2.5 | 样式文件名：kebab-case 语义名（`tokens.css`、`glass.css`、`glass-modal.css`）。 | `styles/` |
| 2.2.6 | 页面文件 PascalCase，目录按业务域 kebab-case（`pages/settings/`、`pages/candidate/`）。 | `pages/` |
| 2.2.7 | 组件支持二级业务子目录（`components/common/`、`components/role/`），跨域复用放 `common/`。 | `components/` |
