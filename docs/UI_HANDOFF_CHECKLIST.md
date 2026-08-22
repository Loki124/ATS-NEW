# ATS-NEW 液态玻璃 UI 改造 · 研发执行清单（整合版）

> 状态：**PM 已最终确认（v2.7 · 2026-08-22），转研发执行** · 设计系统架构师 Diana
> 总纲：`web/app/DESIGN.md`（规范 v2）｜`docs/UI_DIAGNOSIS_V2.md`（4 维度诊断 38 个问题）｜`docs/UI_OPTIMIZATION_PLAN.md`（v1 方案）｜`docs/UI_STYLE_RECONCILIATION.md`（替换表）
> 预览：`web/app/liquid-glass-preview.html`（v2.7 · 顶栏含品牌取色器 + 暗色切换 + 4 Scene Tab + 响应式断点切换 + 键盘面板）

---

## 0. 历史背景（已落地，6 commit 推送 Gitee）

v1 阶段 1–4 已收口（`git log --oneline` 可查 6 个 UI commit），本清单专注于 **v2 增量任务**（v2 阶段补 38 个 P0/P1/P2 问题）。

| 阶段 | 工作量 | 状态 |
|---|---|---|
| 阶段 1 全局 token / themeOverrides / 换肤 / 暗色 | 0.5 人日 | ✅ 完成 |
| 阶段 2 极光底 / Login 玻璃化 / 模态玻璃化 | 0.5 人日 | ✅ 完成 |
| 阶段 3.1 Dashboard / 阶段 3.2 校招管控 / 阶段 3.3 设置中心 | 1.5 人日 | ✅ 完成 |
| 阶段 3.4 招聘主流程 / 阶段 3.5 通用件 | 1.0 人日 | ✅ 完成 |
| 阶段 4 动效 / 历史色 / 收口 / 文档 | 0.5 人日 | ✅ 完成 |

---

## 1. 执行原则（v2.7 PM 拍板 · 务必先读）

### 1.1 单一事实来源 + 系统约束（来自 v1）
1. **单一事实来源** = `src/styles/tokens.css` + `App.vue` 的 `themeOverrides`。任何新颜色/模糊/圆角必须先进 token，组件只引用变量。
2. **不改 Naive UI 源码**：仅通过 `themeOverrides` + 包裹 class 调整。
3. **退路**：玻璃底统一保留不透明兜底，`backdrop-filter` 失效也不崩可读性。
4. **品牌换肤**：只动 `--brand` 一处；暗色切 `body.dark`。

### 1.2 PM 拍板的强制约束（v2.6 / v2.7）
5. **弹窗**：padding **32px** + 拆 `header / body / footer` 三段 + footer `border-top` 视觉分隔（**禁止** 24px 紧凑布局）。
6. **搜索框响应式**：`.search { flex: 1 1 240px; min-width: 200px; white-space: nowrap }`；`.topbar { flex-wrap: wrap }`；≤768 搜索换行占满（**禁止** 在窄屏被挤小或与其他按钮挤一行）。
7. **错误页/占位页统一双列布局**（左大数字右说明）：
   - **禁止** 错误页字号 > 80px；
   - **禁止** 紫蓝撞色三色渐变（必须**单色透明渐变** `linear-gradient(135deg, var(--brand), color-mix(in srgb, var(--brand) 40%, transparent))`）；
   - **禁止** 垂直堆叠 emoji + 数字 + 标题；
   - **禁止** 占位页与错误页用不同布局（系统级一致性）。
8. **玻璃面板错误页必须加粗边框**：`border: 1.5px solid var(--glass-border-strong)`（1px 看不见）。
9. **强调色规范统一**：四态（amber/rose/sky/emerald）= `var(--c-warning/error/info/success)`，**禁止** 业务页自定义强调色。
10. **表格行键盘可达**：`<tr tabindex="0" role="button" aria-label="...">`（**禁止** 仅鼠标可达）。

### 1.3 v2 阶段禁忌（来自 38 个问题）
- ❌ Ant Design 硬编码色（99 处）继续放任 —— 暗色下"白纸黑字"漂浮
- ❌ 主按钮字色用 `!important` 覆盖 App.vue 的 `#fff`（与玻璃风格冲突）
- ❌ 业务页 `.demand-card { background: white }` 自写背景（应走 `var(--glass-bg-card)`）
- ❌ SettingsLayout 用 `:deep` 注入批量改 25+ 子页（hack，子页改动会被静默压回）
- ❌ 关键操作（REJECTED / WITHDRAWN / CANCELLED）无 `dialog.warning()` 二次确认
- ❌ 404 / Forbidden / 占位页无 `glass-panel` 玻璃材质
- ❌ 占位页只有"页面建设中"无语义信息（用户误判为正式页）

---

## 2. 环境 / 验证命令

```bash
cd /Users/loki/WorkBuddy/招聘助手/ATS-NEW/web/app
npm run dev          # Vite :5212（launchd 保活，IPv6 localhost）
npm run build        # vue-tsc 类型检查 + 构建（门禁）
npm run lint:ci      # ESLint 零警告

# 视觉回归（v2.7 预览对照）
open http://127.0.0.1:5212   # 实测应用
open web/app/liquid-glass-preview.html  # 设计稿对照

# 探针（v2 阶段验收用）
/tmp/test-t2-probe.mjs       # 阶段 1-2 探针
/tmp/test-theme.mjs          # 换肤 + 暗色探针
```

---

## 3. v2 任务清单（按 8 阶段顺序 · 总工作量 5–6 人日）

> **起点判断**：v2 阶段所有任务**都依赖** v1 阶段 1（token + themeOverrides + glass.css）已就位。

### ★ 阶段 5 — 业务页硬编码颜色全替换（T5.1 / P0 杠杆最大 · 建议先行）

#### T5.1.1 OfferList.vue 颜色 token 化
- **文件**：`src/pages/offer/OfferList.vue` L139-144、L255、L856-860
- **动作**：5 个状态色 `#1890ff / #52c41a / #ff4d4f / #fa8c16 / #722ed1` → `var(--c-info / c-success / c-error / c-warning / c-info)`；移除 `L856-860` 的 `color: var(--ink) !important` 覆盖（与 App.vue `#fff` 主按钮字色冲突）；主按钮字色由 `App.vue` themeOverrides 统一。
- **完成标准**：`grep -E '#1890ff|#52c41a|#ff4d4f|#fa8c16|#722ed1' src/pages/offer/OfferList.vue` 返回 0 行。

#### T5.1.2 DemandList.vue 颜色 + 容器 token 化
- **文件**：`src/pages/demand/DemandList.vue` L698、L725、L787-L1079
- **动作**：
  - `.demand-container { background: #f0f2f5 }` → `background: transparent`（让 `--aurora-base` 透出）
  - `.demand-card { background: white }` → `background: var(--glass-bg-card); border: 1px solid var(--glass-border)`
  - `#666` (8 处) → `var(--ink-soft)`；`#999` (4 处) → `var(--ink-faint)`；`#333` (4 处) → `var(--ink)`
- **完成标准**：grep `white|#f0f2f5|#666|#999|#333` 全部 0。

#### T5.1.3 OnboardingList.vue 颜色 token 化
- **文件**：`src/pages/onboarding/OnboardingList.vue`
- **动作**：`#8c8c8c / #1890ff / #52c41a / #ff4d4f` 全部 → token。
- **完成标准**：grep 全部 0。

#### T5.1.4 InterviewList.vue 颜色 token 化
- **文件**：`src/pages/interview/InterviewList.vue`
- **动作**：`#8c8c8c / #1890ff / #52c41a / #fa8c16` → token；表格行加 `tabindex="0" role="button" aria-label="..."`。
- **完成标准**：grep 全部 0；Playwright 测试键盘 Enter 可达。

#### T5.1.5 CandidateList.vue 颜色 token 化（最复杂）
- **文件**：`src/pages/candidate/CandidateList.vue` L814-L1004、L872
- **动作**：
  - `.candidate-row { background: #fff }` → `var(--glass-bg-card)` + `border: 1px solid var(--glass-border)`
  - `#8c8c8c` (10 处) → `var(--ink-faint)`；`#595959` (6 处) → `var(--ink-soft)`；`#262626` (2 处) → `var(--ink)`
  - 5 个状态色全部 → token
  - `mockData` L644-647 张三 `age:8 / experience:'1年'` → `age:28 / experience:'5年'`（mockData 真实化 T5.8）
- **完成标准**：grep `white|#8c8c8c|#595959|#262626|#1890ff|#52c41a|#ff4d4f` 全部 0；Playwright 测候选人卡片暗色下背景 = `rgba(30,41,59,.62)`。

#### T5.1.6 index.css body 浅灰去除（v1 已做完，此处仅作回归）
- **文件**：`src/styles/index.css` L17-23
- **动作**：`background-color: #f5f5f5` → `background: transparent`（让 `--aurora-base` 生效）；`color: rgba(0,0,0,.88)` → `var(--ink)`。
- **完成标准**：body 透出极光底；切换暗色正常。

> **阶段 5 门禁**：`grep -rE '#8c8c8c|#f0f0f0|#595959|#262626|#f0f2f5|#bfbfbf|#1890ff|#52c41a|#ff4d4f|#fa8c16|#722ed1|#f5222d' src/pages/{offer,demand,onboarding,interview,candidate}` 返回 0 行。

---

### ★ 阶段 6 — 5 列表页响应式 + 侧栏移动折叠（T6.1 / P0）

#### T6.1 列表页响应式 patch（OfferList / DemandList / OnboardingList / InterviewList / CandidateList）
- **文件**：5 列表页 `<style scoped>` 末尾
- **动作**：粘统一 patch（来自 `UI_STYLE_RECONCILIATION.md` §四）：
  ```css
  @media (max-width: 1280px) {
    .page-container { padding: var(--space-4); }
    .page-title { font-size: var(--text-h2); }
    :deep(.n-data-table-wrapper) { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  }
  @media (max-width: 768px) {
    .page-container { padding: var(--space-3); }
    .page-header { flex-direction: column; align-items: stretch; gap: var(--space-3); }
    .stats-row { grid-template-columns: repeat(2, 1fr) !important; }
  }
  @media (max-width: 480px) {
    .stats-row { grid-template-columns: 1fr !important; }
  }
  ```
- **完成标准**：Playwright 测 768 / 480 viewport 无横向滚动条 / stats-row 2 列 / 1 列正常。

#### T6.2 Layout.vue 侧栏移动折叠
- **文件**：`src/pages/Layout.vue`
- **动作**：
  1. `<script setup>` 加 `const isMobile = ref(window.innerWidth < 768); const mobileMenuOpen = ref(false)` + resize 监听
  2. `<n-layout-sider>` 加 `v-if="!isMobile"`；新增 `<n-drawer v-model:show="mobileMenuOpen" placement="left" :width="280">` + `<n-menu>` 渲染相同菜单项
  3. 顶栏左侧加汉堡按钮（v-if="isMobile"）：`.hamburger-btn` 用 `.glass-input` 玻璃化
- **完成标准**：768 / 375 viewport 侧栏默认隐藏；汉堡按钮点击展开 drawer；菜单点击跳路由 + 关闭 drawer。

> **阶段 6 门禁**：Playwright 跑 1440 / 1024 / 768 / 375 四档视口截图 + DOM 校验（侧栏显隐、KPI 列数、Drawer 开关）。

---

### ★ 阶段 7 — 框架组件对齐（T7.1-T7.3 / P0-P1）

#### T7.1 主按钮字色冲突修复（C2 / P0）
- **文件**：`src/pages/candidate/CandidateList.vue` L856-860；其他 6 处业务页
- **动作**：移除所有 `!important` 覆盖；如确需暗底白字 → 用专用 modifier 类 `.btn-primary--on-light { color: var(--ink) }`（不覆盖主按钮全局）。
- **完成标准**：`grep -rn 'color: var(--ink) !important' src/pages` 返回 0 行；App.vue themeOverrides `textColorPrimary: '#fff'` 生效。

#### T7.2 表头玻璃化（C11 / P1）
- **文件**：`src/styles/glass.css` 增补
- **动作**：
  ```css
  .n-data-table .n-data-table-th { background: rgba(255,255,255,.5); backdrop-filter: blur(8px); }
  body.dark .n-data-table .n-data-table-th { background: rgba(255,255,255,.06); }
  ```
- **完成标准**：5 列表页表头在浅/暗模式下均为半透明玻璃。

#### T7.3 强调色规范统一（I2 / P1）
- **文件**：`Dashboard.vue` matter-tab__count 等
- **动作**：所有强调色统一为 `var(--c-info-soft / c-info)`；"紧急/逾期" 用 `.matter-tab__count--urgent` (c-error-soft/c-error)；**禁止** 自定义品牌色强调。
- **完成标准**：grep `var(--brand-soft)` 用作"未读计数"返回 0 行；grep `--brand-grad-a` 作通用状态色返回 0 行。

#### T7.4 操作列瘦身（I3 / P1）
- **文件**：5 列表页 + DemandList
- **动作**：表格操作列从「3-4 个按钮」收为「详情 + 更多」下拉；按钮 > 3 个走 `<n-dropdown>`。
- **完成标准**：每行操作列宽 ≤ 160px；视觉不拥挤。

---

### ★ 阶段 8 — 错误态 + 交互增强（T8.1-T8.5 / P0-P1）

#### T8.1 错误态路由 + 页面（U11 / F2 / F3 / F1 · P0）
- **文件**：
  - 新建 `src/pages/errors/NotFound.vue`（双列布局：左 404 大数字 + 右说明）
  - 新建 `src/pages/errors/Forbidden.vue`（双列布局：左 403 大数字）
  - 新建 `src/pages/errors/Placeholder.vue`（双列布局：左 🚧 emoji + PLACEHOLDER tag，右标题 + 描述 + 开发中 + ETA + Issue）
  - 修改 `src/router/index.ts`：404 路由 → NotFound；wildcard redirect → '/404'；5 个 settings 路由的 component 改 Placeholder
- **动作**：完全按 `UI_STYLE_RECONCILIATION.md` §4.3 双列布局模板实现：
  ```vue
  <template>
    <div class="err-page">
      <div class="glass-panel err-card">
        <div class="err-left">
          <h1 class="err-code">{{ status }}</h1>
          <span class="err-tag">{{ statusTag }}</span>
        </div>
        <div class="err-right">
          <h2 class="err-title">{{ title }}</h2>
          <p class="err-desc">{{ description }}</p>
          <div class="err-actions">
            <button class="btn btn-primary" @click="$router.replace('/dashboard')">返回工作台</button>
            <button class="btn btn-secondary" @click="$router.back()">返回上一页</button>
          </div>
        </div>
      </div>
    </div>
  </template>
  ```
  CSS 来自 `UI_STYLE_RECONCILIATION.md` §4.3（已完整列出）。
- **完成标准**：
  - Playwright 测 `/xxx` 跳 `/404` 显示 NotFound 双列布局
  - 占位页 5 个路由（`/settings/onboarding` 等）显示开发中 + ETA
  - 玻璃面板 `border: 1.5px solid var(--glass-border-strong)` 可见
  - ≤560 折叠为单列居中
  - 暗色下数字渐变仍为品牌色透明（不撞色）

#### T8.2 全局 axios 错误兜底（U11 / P0）
- **文件**：`src/main.ts` 或新建 `src/utils/axiosInterceptors.ts`
- **动作**：
  ```ts
  import { createDiscreteApi } from 'naive-ui'
  const { message } = createDiscreteApi(['message'])
  axios.interceptors.response.use(
    (resp) => resp,
    (err) => {
      const status = err?.response?.status
      const url = err?.config?.url ?? '<unknown>'
      if (status === 404) {
        console.warn(`[API 404] ${url}`)
        message.warning(`接口不存在：${url.split('?')[0]}`)
      } else if (status === 500) {
        console.error(`[API 500] ${url}`, err?.response?.data)
        message.error('服务异常，请稍后再试')
      } else if (status === 401) {
        // 触发 logout（已有逻辑，保留）
      }
      return Promise.reject(err)
    }
  )
  ```
- **完成标准**：Playwright 测 mock 404 / 500 接口，前端能看到 message 提示。

#### T8.3 关键操作二次确认（U12 / P1）
- **文件**：`OfferList.vue handleTransitionSubmit()`、`InterviewList.vue handleCancel()`、`OnboardingList.vue handleReject()`
- **动作**：危险状态（`REJECTED / WITHDRAWN / EXPIRED / CANCELLED`）操作前 `await dialog.warning({ title:'确认操作', content:'将 ... 状态变更为 ...', positiveText:'确认', negativeText:'取消' })`，用户取消则 return。
- **完成标准**：Playwright 测危险状态变更弹 dialog；点取消不调 API。

#### T8.4 表格行键盘可达（I1 / P1）
- **文件**：5 列表页 `<n-data-table :row-props="rowProps">`
- **动作**：
  ```ts
  function rowProps(row: any) {
    return {
      tabindex: 0,
      role: 'button',
      'aria-label': `${row.name} 详情`,
      onKeydown: (e: KeyboardEvent) => {
        if (e.key === 'Enter') router.push(`/candidates/${row.id}`)
      },
      style: 'cursor: pointer',
      onClick: () => router.push(`/candidates/${row.id}`),
    }
  }
  ```
- **完成标准**：Playwright 测试 Tab 焦点在表格行；按 Enter 跳详情页。

#### T8.5 面包屑（F6 / P1）
- **文件**：新建 `src/components/common/Breadcrumb.vue`；挂到 `Layout.vue` 顶栏下沿
- **动作**：从 `useRoute().matched` 算出 crumbs（路由 meta.title 链），n-breadcrumb 渲染。
- **完成标准**：深路径（如 `/settings/permission/RolesTab`）显示面包屑。

#### T8.6 入场动效扩展（I4 / P1）
- **文件**：`src/styles/tokens.css`（已有 `wb-fade-up`）+ 5 列表页
- **动作**：列表页 `.page-container { animation: wb-fade-up var(--duration-slow) var(--ease-out) both }`；卡片 stagger `.fade-up.stagger-N` 6 级。
- **完成标准**：刷新页面看到淡入上移动效。

#### T8.7 快捷键扩展（I10 / P2）
- **文件**：新建 `src/composables/useShortcuts.ts`，main.ts 启用
- **动作**：`/` 聚焦搜索；`G D` 跳工作台（1.5s 内按 D）；`?` 打开帮助面板。
- **完成标准**：在非输入框中按 `/` 聚焦搜索框。

> **阶段 8 门禁**：Playwright 跑 404 / 占位 / 危险操作 / 键盘可达 / 面包屑 / 快捷键 6 项验收。

---

### ★ 阶段 9 — SettingsLayout 去 hack（F4 / P1）

#### T9.1 删除 `:deep` 注入
- **文件**：`src/pages/settings/SettingsLayout.vue` L391-515
- **动作**：删除全部 `:deep(.page-title / .n-card / .n-tabs / .filter-row / .n-button--primary-type)` 注入；依赖 v1 已落地的 `glass.css` 全局 `.n-card.n-card` + `.n-button--primary-type` + `.gradient-title` 自动接管。
- **完成标准**：`grep ':deep' src/pages/settings/SettingsLayout.vue` 返回 0 行；设置 25+ 子页视觉与 Dashboard / 校招管控一致。

#### T9.2 设置中心导航两套合一（F5 / P2）
- **文件**：`SettingsLayout.vue` 自写 `.menu-group / .menu-item`
- **动作**：改用 `<n-menu :options="menuOptions">`（与 Layout.vue 一致），统一两套实现。
- **完成标准**：`grep 'class="menu-group"' src/pages/settings/SettingsLayout.vue` 返回 0 行。

---

### ★ 阶段 10 — 体验收口（P2 持续打磨）

#### T10.1 滚动条暗色（U7 / P2）
- **文件**：`src/styles/index.css`
- **动作**：滚动条 thumb `var(--ink-faint)` / hover `var(--ink-soft)`；`body.dark` 下 `rgba(255,255,255,.18/.28)`。
- **完成标准**：暗色下滚动条可见且不刺眼。

#### T10.2 图标按钮 aria-label（A5 / P1）
- **文件**：5 列表页 + 设置页所有 `n-icon-button`
- **动作**：所有图标按钮加 `aria-label`（"编辑候选人"/"删除规则" 等）。
- **完成标准**：`grep '<n-icon-button' -A1 src/pages | grep 'aria-label'` 全部命中。

#### T10.3 Loading 收口（I5 / P1）
- **文件**：`src/components/common/` 新建 `LoadingState.vue`
- **动作**：替换散落的 `n-spin` / `n-skeleton` / 自写 loading div 为统一 `<LoadingState type="page|section|button" />`；类型 = page（全屏玻璃 spinner）/ section（卡片骨架）/ button（按钮内 spinner）。
- **完成标准**：5 列表页加载态一致。

#### T10.4 空状态收口（I5 / U9 / P1）
- **文件**：`src/components/common/` 新建 `EmptyState.vue`
- **动作**：替换散落的 `<n-empty>` 为 `<EmptyState icon title description actionLabel @action />`。
- **完成标准**：5 列表页空状态视觉一致。

---

## 4. 验收清单（v2 阶段回检）

### 4.1 P0 必过（9 项）
- [ ] **C1**：`grep -rE '#8c8c8c|#f0f0f0|#595959|#262626|#f0f2f5|#bfbfbf|#1890ff|#52c41a|#ff4d4f|#fa8c16|#722ed1' src/pages/{offer,demand,onboarding,interview,candidate}` = **0 行**
- [ ] **C2**：所有 `!important` 覆盖移除，主按钮白字生效
- [ ] **C3**：5 列表页全部用 `.glass-card` / `.glass-panel` 容器
- [ ] **U1**：Playwright 768 / 480 viewport stats-row 2 列 / 1 列
- [ ] **U2**：768 / 375 viewport 侧栏 drawer 化
- [ ] **U4**：暗色下业务页无"白纸黑字"漂浮
- [ ] **U5**：暗色下 5 列表页卡片背景 = `rgba(30,41,59,.62)`
- [ ] **U11**：错误态路由 + 全局 axios message 兜底
- [ ] **F1**：5 占位路由显示 PLACEHOLDER 双列布局（开发中 + ETA + Issue）

### 4.2 P1 必过（16 项）
- [ ] **F2**：404 路由显示 NotFound 双列布局（不跳首页）
- [ ] **F3**：Forbidden 双列布局
- [ ] **F4**：SettingsLayout `:deep` 注入 = 0 行
- [ ] **F6**：深路径显示面包屑
- [ ] **C4**：body 透明（让极光底生效）
- [ ] **C7**：`grep 'font-size: [0-9]\+px'` src/pages = 0 行
- [ ] **C8**：`grep 'padding: [0-9]\+px'` src/pages = 0 行
- [ ] **C9**：`grep 'border-radius: [0-9]\+px'` src/pages = 0 行
- [ ] **C11**：表头玻璃化生效
- [ ] **C12**：批量通知弹窗走 n-modal（不自写）
- [ ] **C14**：业务页 label 灰色硬编码 = 0
- [ ] **I1**：表格行 tabindex + Enter 跳详情
- [ ] **I2**：强调色统一为 c-info/c-success/c-warning/c-error
- [ ] **I3**：操作列 ≤ 160px
- [ ] **I4**：入场动效 fade-up 生效
- [ ] **I5**：Loading/EmptyState 统一组件
- [ ] **I7**：占位页含 dev 中 + ETA + Issue
- [ ] **U6 / U9**：滚动条暗色 + 空状态收口
- [ ] **U10**：mockData 张三 `age:28 / experience:'5年'`
- [ ] **U12**：危险操作 dialog.warning 二次确认
- [ ] **A1 / A5**：#8c8c8c = 0 / 图标按钮 aria-label 全

### 4.3 P2 可选（13 项）
- F5/F7 两套导航合一 · C5/C6/C13/C15 散落 token/函数 · I6/I8/I9 提示位置 · I10 快捷键扩展 · U3 表横滚 · U7 滚动条暗色 · U8 页头文案 · U13 toast 规范 · A2/A3/A4 a11y

### 4.4 PM 强制约束（v2.6 / v2.7）
- [ ] **弹窗**：padding = 32px + header/body/footer 三段 + footer border-top
- [ ] **搜索框**：min-width: 200px / nowrap / ≤768 换行占满
- [ ] **错误页**：双列布局 + 字号 ≤ 80px + 单色透明渐变 + 玻璃 border: 1.5px
- [ ] **占位页**：与错误页同双列结构

### 4.5 门禁
- [ ] `npm run build` 通过 + `vue-tsc --noEmit` 0 errors
- [ ] `npm run lint:ci` 零警告
- [ ] Playwright 7 路由 × 2 模式 + 4 视口 = 56 截图全部成功
- [ ] 视觉回归：Login / 工作台 / 候选人 / Offer / 需求 / 面试 / 待入职 / 设置 / 404 / 占位 10 个场景风格一致

---

## 5. 风险与回滚

### 5.1 阶段风险
| 阶段 | 风险等级 | 回滚方式 |
|---|---|---|
| 阶段 5 业务页硬编码 | 中（量大） | 每页单独 commit + 单独 revert |
| 阶段 6 响应式 | 低 | 单文件 revert |
| 阶段 7 框架组件 | 低 | 单文件 revert |
| 阶段 8 错误态/交互 | 中（涉及路由） | NotFound/Forbidden/Placeholder 各为独立 commit |
| 阶段 9 SettingsLayout 去 hack | 中（去 `:deep`） | 测试 25+ 设置子页；如有视觉回归可还原 `:deep` |

### 5.2 性能与兼容性
- **玻璃性能**：低端机 `blur` 可统一降至 10px（改 `tokens.css` 一处）
- **`backdrop-filter`** 必须带 `-webkit-` 前缀（Safari / 微信内置浏览器）
- **极光层**：低端机 `filter: blur(70px)` 改 40px 或关闭

### 5.3 提交规范
- **每阶段独立 commit**，不允许"阶段 5 + 6 一锅端"
- **commit message**：`fix(stage5): 业务页 99 处 Ant 色 → tokens v2` / `feat(stage6): 5 列表页响应式 + 侧栏移动折叠`
- **不允许 `--no-verify`** 跳过 hook
- **不允许 `git push --force`**

---

## 6. 附录

### 附录 A — `glass.css` 骨架（v1 已落地，研发参照）

```css
/* 见 src/styles/glass.css，核心原子类 */
.glass-panel { background: var(--glass-bg-panel); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); border: 1px solid var(--glass-border); border-radius: var(--radius-lg); box-shadow: var(--shadow-panel); }
.glass-card { background: var(--glass-bg-card); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid var(--glass-border); border-radius: var(--radius-md); box-shadow: var(--shadow-card); padding: var(--space-4); }
.glass-input { background: var(--glass-bg-input); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); padding: 9px 12px; backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }
.glass-input:focus { border-color: var(--brand); box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand) 18%, transparent); outline: none; }
.btn-primary { background: linear-gradient(135deg, var(--brand), var(--brand-grad-a)); color: #fff; border: 1px solid rgba(255,255,255,.35); border-radius: var(--radius-md); padding: 10px 18px; font-weight: 600; box-shadow: 0 4px 14px color-mix(in srgb, var(--brand) 32%, transparent), inset 0 1px 0 rgba(255,255,255,.4); }
.btn-primary:hover { box-shadow: 0 6px 20px color-mix(in srgb, var(--brand) 45%, transparent); transform: translateY(-1px); }
.btn-secondary { background: var(--glass-bg-card); border: 1px solid var(--glass-border); color: var(--ink); border-radius: var(--radius-md); padding: 10px 18px; }
.btn-secondary:hover { border-color: var(--brand); color: var(--brand); }
.btn-ghost { background: transparent; color: var(--ink-soft); border: 1px solid transparent; border-radius: var(--radius-md); }
.btn-ghost:hover { background: rgba(15,23,42,.04); color: var(--ink); }
.btn-danger { background: var(--c-error-soft); border: 1px solid rgba(239,68,68,.3); color: var(--c-error); border-radius: var(--radius-md); padding: 10px 18px; }
.gradient-title { background: linear-gradient(135deg, var(--brand), var(--brand-grad-a) 55%, var(--brand-grad-b)); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.app-aurora { position: fixed; inset: 0; z-index: 0; pointer-events: none; background: var(--aurora-base); }
```

### 附录 B — 错误页双列布局（v2.7 · 直接复制）

```css
.err-page { display: flex; align-items: center; justify-content: center; min-height: 60vh; padding: var(--space-6); text-align: left; }
.err-card {
  padding: var(--space-8);
  display: grid; grid-template-columns: auto 1fr;
  gap: var(--space-8); align-items: center;
  max-width: 620px;
  border: 1.5px solid var(--glass-border-strong);   /* ★ 加粗玻璃边框 */
}
.err-left  { display: flex; flex-direction: column; gap: 6px; min-width: 140px; }
.err-right { display: flex; flex-direction: column; gap: var(--space-3); align-items: flex-start; }
.err-code {
  font-size: 72px; font-weight: 800; line-height: 1; margin: 0;
  letter-spacing: -.04em;
  background: linear-gradient(135deg, var(--brand) 0%, color-mix(in srgb, var(--brand) 40%, transparent) 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  font-feature-settings: "tnum";
}
.err-tag { font-size: var(--text-meta); color: var(--ink-faint); font-weight: 600; letter-spacing: .08em; text-transform: uppercase; }
.err-title { font-size: var(--text-h2); font-weight: 700; color: var(--ink); margin: 0; line-height: 1.3; }
.err-desc  { color: var(--ink-soft); font-size: var(--text-body); margin: 0; line-height: 1.7; max-width: 36ch; }
.err-actions { display: flex; gap: var(--space-3); margin-top: var(--space-3); flex-wrap: wrap; }
@media (max-width: 560px) {
  .err-card { grid-template-columns: 1fr; gap: var(--space-5); padding: var(--space-6); }
  .err-left, .err-right { align-items: center; text-align: center; }
  .err-code { font-size: 56px; }
}
```

### 附录 C — 弹窗 32px 三段分区（v2.6 · 直接复制）

```css
.modal {
  width: 480px; max-width: 92vw;
  padding: var(--space-8) var(--space-8) var(--space-6);   /* ★ 32px */
  background: var(--glass-bg-elevated);
  backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border-strong);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-elevated);
  display: flex; flex-direction: column; gap: var(--space-5);
}
.modal-header { display: flex; flex-direction: column; gap: 10px; }
.modal-body   { display: flex; flex-direction: column; gap: var(--space-4); }
.modal-footer {
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-hairline);     /* ★ 视觉分隔 */
  display: flex; justify-content: flex-end; gap: var(--space-3);
}
.modal h3 { font-size: var(--text-h3); font-weight: 600; margin: 0; }
.modal p  { color: var(--ink-soft); font-size: var(--text-body); line-height: 1.6; margin: 0; }
```

### 附录 D — 搜索框响应式（v2.6 · 直接复制）

```css
.search {
  flex: 1 1 240px; min-width: 200px; max-width: 420px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.topbar { flex-wrap: wrap; }
@media (max-width: 768px) {
  .topbar { padding: 10px var(--space-3); gap: 10px; }
  .search { flex: 1 1 100%; max-width: none; order: 10; }   /* ★ 搜索换行占满 */
  .seg { gap: 4px; }
}
@media (max-width: 480px) {
  .topbar { padding: 8px 10px; gap: 6px; }
  .toggle { font-size: 11px; padding: 4px 6px; }
  .seg .sw { width: 14px; height: 14px; }
}
```

---

## 7. 任务编号速查

| 编号 | 任务 | 工作量 | 优先级 | 依赖 |
|---|---|---|---|---|
| T5.1.1 | OfferList 颜色 token 化 | 0.1 | P0 | T1.1 |
| T5.1.2 | DemandList 颜色 + 容器 | 0.1 | P0 | T1.1 |
| T5.1.3 | OnboardingList 颜色 | 0.1 | P0 | T1.1 |
| T5.1.4 | InterviewList 颜色 + 键盘 | 0.1 | P0 | T1.1 / T8.4 |
| T5.1.5 | CandidateList 颜色 + mockData | 0.1 | P0 | T1.1 |
| T6.1 | 5 列表页响应式 patch | 0.5 | P0 | — |
| T6.2 | 侧栏移动折叠 drawer | 0.5 | P0 | T1.5 |
| T7.1 | 主按钮字色 !important 修复 | 0.2 | P0 | T1.3 |
| T7.2 | 表头玻璃化 | 0.1 | P1 | T1.4 |
| T7.3 | 强调色规范统一 | 0.3 | P1 | — |
| T7.4 | 操作列瘦身 | 0.4 | P1 | — |
| T8.1 | 错误页 + 占位页 + 路由 | 1.0 | P0 | T1.4 / T2.3 |
| T8.2 | axios 错误兜底 | 0.2 | P0 | — |
| T8.3 | 关键操作二次确认 | 0.3 | P1 | — |
| T8.4 | 表格行键盘可达 | 0.2 | P1 | — |
| T8.5 | 面包屑 | 0.3 | P1 | — |
| T8.6 | 入场动效扩展 | 0.2 | P1 | T1.x |
| T8.7 | 快捷键扩展 | 0.3 | P2 | — |
| T9.1 | SettingsLayout 去 `:deep` | 0.3 | P1 | T1.x |
| T9.2 | 设置中心导航合一 | 0.2 | P2 | — |
| T10.1 | 滚动条暗色 | 0.1 | P2 | — |
| T10.2 | 图标按钮 aria-label | 0.2 | P1 | — |
| T10.3 | Loading 收口 | 0.3 | P1 | — |
| T10.4 | 空状态收口 | 0.3 | P1 | — |

**总计：5.4 人日可解 9 个 P0 + 16 个 P1（占 64%）**

---

**研发执行入口**：
```bash
cd /Users/loki/WorkBuddy/招聘助手/ATS-NEW
git checkout -b feat/ui-v2-reconciliation
git push -u origin feat/ui-v2-reconciliation
# 从 T5.1.1 OfferList 开始，每任务一个 commit
```