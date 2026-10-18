# ATS-NEW UI 规范与审查文档
> 最后更新：2026-09-14（依据 git 最后提交）

本目录是 ATS-NEW 前端 UI 的**唯一权威入口**。任何新增 / 修改 UI 之前必须读完本目录下的规范文档，并按规范 + 设计令牌（`tokens.css`）执行。

## 文档结构

| 文档 | 用途 | 阅读顺序 |
|---|---|---|
| `UI_DESIGN_SPEC.md` | 统一设计规范 v2.1：颜色 / 排版 / 间距 / 圆角 / 阴影 / 组件 / 响应式 / 可访问性 / Do-Don't / 令牌对照表。**前端 UI 的宪法**。 | ① 必读 |
| `UI_REMEDIATION_PLAN.md` | 整改技术实施方案：按 P0→P6 推进落地，文件:行号 + 可照抄代码块 + 验收点。 | ② 整改排期 |
| `UI_COMPLIANCE_SELFCHECK.md` | 规范符合性审查报告 + 交付前自检矩阵（S/R/H，已合并原 REPORT）：🔴 关键 / 🟡 重要 / 🔵 建议 三级问题清单（整改方案的源头）。 | ③ 立项参考 |
| `SETTINGS_PAGE_STRUCTURE.md` | **设置页统一页面结构规范 v1.0**：Shell/根/标题/KPI/工具条/表格/弹窗/多 tab 看板/自检清单。所有 `pages/settings/**` 下页面（含 permission 子模块）必读。 | ① 设置页改前必读 |

## 强制约束（强制项，请大声读出来）

1. **唯一输入源是 `tokens.css`**：颜色 / 间距 / 圆角 / 阴影 / 动效时长一律走 CSS 变量；改品牌色只改 `--brand` 一处。**禁止**硬编码 hex / rgb / 模糊值。
2. **暗色靠变量集切换**：组件 CSS 不写 dark 分支；切 `body.dark` 即整体换肤。
3. **玻璃元素必须**带 `-webkit-backdrop-filter` + 不透明兜底。
4. **新组件**必须复用 `.glass-* / .btn-* / .kpi-* / .toolbar / .page-header` 全局类，不另起一套。
5. **禁用原生 `confirm() / alert()`**：用 `useDialog().warning(...)`。

## 实施方案当前阶段

按 `UI_REMEDIATION_PLAN.md` 的 P0→P5 推进。本目录文档与 IMA 知识库 `招聘助手` 中同主题文件保持同步（IMA 为单一来源之一，本目录为落地载体）。

## 维护者

@兵哥（产品 / 前端设计）。改动规范前先在群里过一遍，避免破坏下游 20+ 设置页一致性。

—— 最近一次修订：2026-10-18

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