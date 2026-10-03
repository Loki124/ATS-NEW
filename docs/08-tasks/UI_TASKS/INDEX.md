# UI v2 AI 任务包索引（24 个 self-contained 任务 · 调研后基线 v2.7）
> 最后更新：2026-10-02（依据 git 最后提交）

> 状态：**调研完成（2026-08-22 09:44）· 待 PM 确认后转 AI 执行**
> 调研报告：本目录 INDEX.md 末尾「调研基线」段
> 总纲：`docs/UI_HANDOFF_CHECKLIST.md`（整合版 TL 用）
> 规范：`web/app/DESIGN.md` + `docs/UI_STYLE_RECONCILIATION.md`

## 任务速查表（24 个 · 按阶段顺序）

| ID | 文件 | 任务 | 工作量 | 优先级 | 依赖 | 状态 |
|---|---|---|---|---|---|---|
| T5.1.1 | `T5.1.1-OfferList-colors.md` | OfferList L140-141 颜色字典 token 化 | 0.1d | P0 | T1.1 | 待执行 |
| T5.1.2 | `T5.1.2-DemandList-colors.md` | DemandList 颜色 token 化（已被 09:7x 需求重构覆盖，颜色零硬编码达成） | 0.1d | P0 | T1.1 | ✅ 已覆盖（见 DEMAND_LIST_REDESIGN.md） |
| T5.1.3 | `T5.1.3-OnboardingList-colors.md` | OnboardingList L206 #8c8c8c | 0.1d | P0 | T1.1 | 待执行 |
| T5.1.4 | `T5.1.4-InterviewList-colors.md` | InterviewList L114/120/160 三处 | 0.1d | P0 | T1.1 | 待执行 |
| T5.1.5 | `T5.1.5-CandidateList-colors.md` | CandidateList L814-1087 共 21 处颜色 + 行背景 | 0.1d | P0 | T1.1 | 待执行 |
| T5.1.6 | `T5.1.6-CandidateList-mockdata.md` | CandidateList L641-647 张三 age:8→28 / exp:1→5 年 | 0.1d | P1 | T5.1.5 | 待执行 |
| T6.1 | `T6.1-listpages-responsive.md` | 5 列表页响应式 patch | 0.5d | P0 | T1.x | 待执行 |
| T6.2 | `T6.2-Layout-sidebar-drawer.md` | Layout.vue 侧栏 ≤768 折叠为 n-drawer | 0.5d | P0 | T1.5 | 待执行 |
| T7.1 | `T7.1-remove-important-override.md` | CandidateList L856-859 + L1054-1055 主按钮 !important 移除 | 0.2d | P0 | T1.3 | 待执行 |
| T7.2 | `T7.2-glass-table-header.md` | glass.css 追加 n-data-table-th 玻璃 | 0.1d | P1 | T1.4 | 待执行 |
| T7.3 | `T7.3-matter-tab-count-info.md` | Dashboard.vue L646-654 matter-tab__count 改 c-info | 0.3d | P1 | — | 待执行 |
| T7.4 | `T7.4-table-actions-slim.md` | 5 列表页操作列 n-dropdown 化 | 0.4d | P1 | — | 待执行 |
| T8.1.1 | `T8.1.1-NotFound-page.md` | 新建 pages/errors/NotFound.vue（双列布局） | 0.3d | P0 | T1.4 | 待执行 |
| T8.1.2 | `T8.1.2-Forbidden-rewrite.md` | pages/Forbidden.vue → 移到 errors/ + 双列化 | 0.2d | P0 | T8.1.1 | 待执行 |
| T8.1.3 | `T8.1.3-Placeholder-rewrite.md` | pages/settings/Placeholder.vue → 双列化 + ETA/Issue | 0.3d | P0 | T8.1.1 | 待执行 |
| T8.1.4 | `T8.1.4-router-wildcard.md` | router/index.ts L169-170 改 NotFound + 占位路由 component | 0.1d | P0 | T8.1.1-3 | 待执行 |
| T8.2 | `T8.2-axios-message-toast.md` | main.ts L21 拦截器加 message.warning/error | 0.2d | P0 | T1.4 | 待执行 |
| T8.3 | `T8.3-danger-confirm-dialog.md` | OfferList/InterviewList/OnboardingList 危险操作 dialog.warning | 0.3d | P1 | — | 待执行 |
| T8.4 | `T8.4-table-row-keyboard.md` | 5 列表页 n-data-table :row-props 加 tabindex+Enter | 0.2d | P1 | T5.1.x | 待执行 |
| T8.5 | `T8.5-breadcrumb-component.md` | 新建 components/common/Breadcrumb.vue + 挂载 | 0.3d | P1 | — | 待执行 |
| T8.6 | `T8.6-page-fadeup-animation.md` | 5 列表页 .page-container 加 wb-fade-up | 0.2d | P1 | T1.x | 待执行 |
| T8.7 | `T8.7-keyboard-shortcuts.md` | composables/useShortcuts.ts + main.ts 启用 | 0.3d | P2 | — | 待执行 |
| T9.1 | `T9.1-SettingsLayout-cleanup.md` | SettingsLayout.vue L231-L530 删 :deep 300 行 | 0.3d | P1 | T1.x | 待执行 |
| T9.2 | `T9.2-SettingsLayout-menu-unify.md` | SettingsLayout.vue 删 .menu-group 自写改 n-menu | 0.2d | P2 | T9.1 | 待执行 |
| T10.1 | `T10.1-scrollbar-dark-mode.md` | index.css 滚动条 dark 适配 | 0.1d | P2 | T1.7 | 待执行 |
| T10.2 | `T10.2-icon-button-aria.md` | 5 列表页 + 设置 n-icon-button 加 aria-label | 0.2d | P1 | — | 待执行 |
| T10.3 | `T10.3-loading-state.md` | 新建 LoadingState.vue + 替换散落 loading | 0.3d | P1 | — | 待执行 |
| T10.4 | `T10.4-empty-state.md` | 新建 EmptyState.vue + 替换散落 n-empty | 0.3d | P1 | T10.3 | 待执行 |

**合计：5.4 人日 / 24 个 commit**

---

## 调研基线（关键发现）

### 已落地（v1 阶段）· 不用做
- ✅ `index.css` body 浅灰已修（grep `background-color: #f5f5f5` = 0 命中）
- ✅ `tokens.css` v2 全套变量已就位
- ✅ `glass.css` 358 行玻璃原子类齐备
- ✅ `App.vue` themeOverrides hex 字面量兜底

### 已存在但需扩展
- `main.ts:21-37` 拦截器已实现 404 console.warn / 500 console.error，**缺 message toast** → T8.2 只需追加
- `pages/Forbidden.vue` 已存在（在 pages/ 根目录），需**移到 pages/errors/ + 双列化** → T8.1.2
- `pages/settings/Placeholder.vue` 已存在但只是占位文案 → T8.1.3 升级为带 ETA/Issue 的双列布局
- `glass.css` 358 行 → T7.2 追加而非新建

### 真实行号（基于 grep 2026-08-22 09:44）
- `OfferList.vue:140-141` OfferStatusColor 字典（DRAFT/PENDING_APPROVAL/APPROVED/SENT/ACCEPTED/REJECTED/EXPIRED 共 7 色）
- `DemandList.vue:698` `.demand-container { background: #f0f2f5 }`；`:724` `.demand-card { background: white }`；`:770-1098` 共 22 处 `#333/#999/#666`
- `CandidateList.vue:814/872` `.candidate-row { background: #fff }`；`:836-1087` 共 21 处颜色；`:856-859` 主按钮 !important；`:1054-1055` 第二处 !important；`:641-647` mockData 张三 age:8
- `OnboardingList.vue:206` `.stat-label { color: #8c8c8c }`（仅 1 处）
- `InterviewList.vue:114/120/160` 3 处
- `Layout.vue:74` 顶栏搜索是 `<n-button>` 包 `<div class="search-box glass-input">`，点击 `onSearchClick` 弹 Modal（**不是 input**）
- `SettingsLayout.vue:231-530+` :deep 注入 ~300 行；`:19/259` `.menu-group` 自写导航
- `Dashboard.vue:646-654` `.matter-tab__count { background: var(--brand-soft) }`
- `router/index.ts:124-136,164` 5 处占位路由；`:169-170` wildcard → '/dashboard'

### 修正原任务清单
- T5.1.6 body 浅灰 → 已完成，删除
- T6.2 搜索框响应式 → 改写为 `.search-box` 按钮 + `.layout-header__search-trigger` 响应式
- T8.2 axios 拦截器 → 仅追加 message toast（不是新建）
- T8.1 Forbidden → 移位置 + 重写，不是新建

---

## AI 执行通用前置（README.md 引用本段）

### A1. 环境前置
```bash
# 1. 确认在 feat/ui-v2-reconciliation 分支
cd /Users/loki/WorkBuddy/招聘助手/ATS-NEW
git checkout -b feat/ui-v2-reconciliation
git push -u origin feat/ui-v2-reconciliation

# 2. 确认 dev 服务可用（launchd 保活）
curl --noproxy '*' -s -o /dev/null -w "%{http_code}\n" http://localhost:5212
# 期望: 200

# 3. 确认基线构建
cd web/app && npm run build
# 期望: vue-tsc 0 errors + 产物 dist/

# 4. 安装 Playwright（如未）
# node_modules/playwright 已存在（v1 阶段装过）
```

### A2. 执行通用流程
```
1. Read 任务包 .md 全文
2. 跑任务包「§1 前置"三项（git status / curl 5212 / npm run build）
3. 按「§3 具体 diff"修改（用 Edit 工具，old_string 必须完全匹配）
4. 跑「§4 验证"全部 grep / npm run build
5. 跑「§4 验证"的 Playwright 探针（如有）
6. git add + git commit（commit message 用任务包「§5"给的模板）
7. 跑「§6 失败处理"的 git status 确认无残留
8. 报告：commit hash + grep 0 行截图 + build PASS 输出
```

### A3. 通用失败处理
- `npm run build` 失败 → `git checkout <file>` 单文件回滚 → 报告错误日志前 30 行
- `grep` 仍有命中 → 检查是否有同色重复在其他行 → 全部替换 → 重跑
- Playwright 探针失败 → 截图保存到 `/tmp/<task>-fail.png` → 报告 DOM 状态
- 任何一步拿不准 → 立即停手报告 PM，不强行继续

### A4. Commit message 模板（24 任务共用前缀）
```
fix(stage5): OfferList 7 处 OfferStatusColor → tokens v2  [T5.1.1]
fix(stage5): DemandList 24 处 Ant 色 + 2 处容器 → tokens v2  [T5.1.2]
fix(stage5): OnboardingList 1 处 → tokens v2  [T5.1.3]
fix(stage5): InterviewList 3 处 → tokens v2 + 键盘 tabindex  [T5.1.4]
fix(stage5): CandidateList 23 处 → tokens v2  [T5.1.5]
fix(stage5): CandidateList mockData 张三 age:8→28 exp:1→5  [T5.1.6]
feat(stage6): 5 列表页响应式 1024/768/480 三档  [T6.1]
feat(stage6): 侧栏 ≤768 折叠为 n-drawer  [T6.2]
fix(stage7): 主按钮 !important 覆盖移除（7 处）  [T7.1]
fix(stage7): n-data-table-th 玻璃化  [T7.2]
fix(stage7): Dashboard matter-tab__count 改 c-info  [T7.3]
refactor(stage7): 5 列表页操作列 n-dropdown 化  [T7.4]
feat(stage8): NotFound 双列布局  [T8.1.1]
fix(stage8): Forbidden 移到 errors/ + 双列化  [T8.1.2]
feat(stage8): Placeholder 双列 + ETA/Issue  [T8.1.3]
fix(stage8): router wildcard 改 NotFound + 5 占位路由  [T8.1.4]
feat(stage8): axios 拦截器加 message.warning/error  [T8.2]
feat(stage8): 危险操作 dialog.warning 二次确认（3 文件）  [T8.3]
feat(stage8): 表格行 tabindex+Enter 键盘可达  [T8.4]
feat(stage8): Breadcrumb 组件 + 挂载  [T8.5]
feat(stage8): 5 列表页入场动效 wb-fade-up  [T8.6]
feat(stage8): useShortcuts composable + 启用  [T8.7]
refactor(stage9): SettingsLayout 删 :deep 300 行  [T9.1]
refactor(stage9): SettingsLayout 自写导航改 n-menu  [T9.2]
fix(stage10): index.css 滚动条暗色  [T10.1]
fix(stage10): n-icon-button aria-label 全  [T10.2]
feat(stage10): LoadingState 组件统一  [T10.3]
feat(stage10): EmptyState 组件统一  [T10.4]
```

### A5. 探针脚本模板（每个任务按需复制改造）
```js
// /tmp/test-<task>.mjs
import { chromium } from 'playwright'
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto('http://localhost:5212/<route>')
// 检查点：DOM 状态、计算样式、URL
const check = await page.evaluate(() => ({
  // 例如
  bg: getComputedStyle(document.querySelector('.glass-card')).backgroundColor,
  // 例如
  count: document.querySelectorAll('.n-data-table-tr').length,
}))
console.log('PASS:', JSON.stringify(check))
await browser.close()
```