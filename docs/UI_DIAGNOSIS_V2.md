# UI 诊断报告 V2（2026-08-21 · 框架/组件/交互/体验 四维度）

> 范围：`web/app/src/**`（Vue3 + Naive UI + UnoCSS，Django 后端不动）。
> 基线：DESIGN.md v2 液态玻璃 + tokens.css v2 单一事实来源。
> 摸底数据：`grep` 命中 **Ant Design 硬编码色 99 处** / `font-size: 数字px` **401 处** / `padding: 数字px` **126 处** / `border-radius: 数字px` **165 处**。
> 优先级：**P0 阻塞产品体验 / P1 明显可见但可短期共存 / P2 可在迭代中持续打磨**。
> 与 `docs/UI_DIAGNOSIS.md`（V1）关系：V1 聚焦"为什么分散"，本报告聚焦"还要再补哪些维度"。

## PM 拍板（v2.7 · 2026-08-22 09:32）

PM 截图反馈 v2.6 错误页「太奇怪了」：

**v2.6 错误页问题**（截图硬证据）：
- 🗺️ emoji 64px 独立悬在最上，无视觉锚点
- 404 字号 96px + 紫蓝撞色渐变 → 像孤立图标
- 玻璃面板透明看不到边框，整个卡片「飘」在空中
- 按钮 3 个挤在最底部无主次
- 整体视觉碎片化、与玻璃风格不调和

**v2.7 修复**：错误页/占位页统一**双列布局**（左大数字右说明）：
- 删 emoji + 巨大 404 → 字号 96→72px
- 紫蓝三色渐变 → 品牌色透明渐变（`linear-gradient(135deg, var(--brand), color-mix(in srgb, var(--brand) 40%, transparent))`，单色系）
- 玻璃面板 `border: 1.5px solid var(--glass-border-strong)` 加粗可见
- 数字下加 `err-tag` 小标签（`PAGE NOT FOUND` / `ACCESS DENIED` / `PLACEHOLDER` 等宽字间距大写）增加语义
- 占位页对齐同一双列结构（左侧 emoji + tag，右侧标题 + 描述 + 开发中 + ETA + Issue + 按钮）
- ≤560 折叠为单列居中
- 写入 `UI_STYLE_RECONCILIATION.md` §4.3 + 在 §四 末尾加「禁止」段（≤80px / 不允许第二色相 / 不允许垂直堆叠 / 占位错误同布局）

## PM 拍板（v2.6 · 2026-08-21 23:59）

PM 在 v2.5 预览基础上反馈 2 点修正 + 批准其余建议：
1. **弹窗内边距太小** —— 原 `.modal { padding: var(--space-6) }` = 24px 视觉局促
2. **响应式布局时搜索框换行** —— `.search { flex: 1; max-width: 420px }` 在窄屏被挤小或与工具按钮挤一行

其余 38 个问题按 `UI_STYLE_RECONCILIATION.md` 的 8 阶段顺序处理**（PM 批准「其他按建议来」）**。

修复已落地 v2.6：
- 弹窗 padding 24→32px + header/body/footer 三段分区 + footer `border-top` 分隔
- 搜索框 `min-width: 200px; white-space: nowrap; flex-wrap: wrap; ≤768 时换行占满`
- 同步写入 `UI_STYLE_RECONCILIATION.md` §4.1 + §4.2（研发参照规范）
- 预览 `liquid-glass-preview.html` 升至 v2.6（4 Scene + 弹窗升级 + 搜索框响应式）

---

## 一、框架应用问题（Framework）

| 编号 | 问题 | 铁证 | 优先级 |
|---|---|---|---|
| **F1** | **5 个路由指向占位页 `Placeholder.vue`，用户无感知是开发中还是正式页** | `router/index.ts` L124-136 + L164：`onboarding / approval / external / public / report` 5 处子路由均 `Placeholder.vue` | **P0** |
| **F2** | **404 路由静默跳 `/dashboard`，无 404 错误页** | `router/index.ts` L169-171：`{ path: '/:pathMatch(.*)*', redirect: '/dashboard' }` —— 输错 URL 用户不知道跳到了首页 | **P1** |
| **F3** | **`Forbidden.vue` 仅用 Naive UI 默认 `n-result`，未与全站玻璃风对齐** | `pages/Forbidden.vue` L1-23：纯白底无玻璃，`n-result` 样式无 token 化；SettingsLayout 已经有大量 :deep 玻璃规则，Forbidden 反而是孤儿 | **P1** |
| **F4** | **SettingsLayout 的"校招管控视觉锚点全局注入"是 hack** | `SettingsLayout.vue` L391-515：通过 `:deep(.page-title) / .page-header / .n-card-header / .filter-row / .n-button--primary-type` **一次性覆盖 25+ 设置子页**；子页面零侵入但绕过子页面作者意图，未来子页面改动会被静默压回玻璃风 | **P1** |
| **F5** | **侧栏导航两套实现** | `Layout.vue` L32-43：n-menu；`SettingsLayout.vue` L1-53：自写 n-layout-sider + div.menu-group（手动渲染 active、toggle、optimisticKey）；两套并行维护成本高 | **P2** |
| **F6** | **Layout 缺面包屑 / 当前路径提示** | `Layout.vue` 完整文件搜索 `breadcrumb / Breadcrumb` 0 命中；用户在深路径（`/settings/permission/RolesTab`）迷失 | **P1** |
| **F7** | **路由 meta.roles 仅 5 个 settings 页声明，列表页/详情页全开** | `router/index.ts` 全文 `meta: { roles:` 只出现 5 处；候选人/职位/需求等敏感页所有登录用户都可见 | **P2**（业务确认） |

---

## 二、组件应用问题（Components）

### 2.1 视觉一致性（颜色 token 化）

| 编号 | 问题 | 铁证 | 优先级 |
|---|---|---|---|
| **C1** | **Ant Design 色硬编码 99 处** | `pages/offer/OfferList.vue` L139-144 `statusColor()` 硬编码 `#1890ff #fa8c16 #52c41a #722ed1 #f5222d #8c8c8c` 7 色；`pages/candidate/CandidateList.vue` L932-996 含 `#8c8c8c #595959 #262626 #1890ff #52c41a #ff4d4f #bfbfbf #999` 8 色；`pages/demand/DemandList.vue` L758-1060 含 `#1890ff #f0f2f5 white #333 #999 #666 #fafafa #f0f0f0` | **P0** |
| **C2** | **主按钮字色冲突** | `App.vue` L56-62 `textColorPrimary: '#ffffff'` 设主按钮白字；`pages/candidate/CandidateList.vue` L856-860 `.add-button, .batch-notify-btn, .send-btn-primary { color: var(--ink) !important; }` 强制黑字覆盖 | **P0** |
| **C3** | **n-card 玻璃化仅靠 `.n-card.n-card` 全局规则救场，业务页自己不用 glass-card** | grep 命中 `.glass-card` / `.glass-panel` 仅 CampusControl / ThemeSettings / Login / Dashboard hero 共 ~5 处；OfferList/DemandList/OnboardingList/InterviewList/CandidateList 均无 glass 类；唯一玻璃化是 `glass.css` L109-114 全局选择器 | **P0** |
| **C4** | **`body { background-color: #f5f5f5 }` 暗色下不切换** | `index.css` L17-23 写死浅灰底，body.dark 下仍是 `#f5f5f5`，与 tokens.css 的 `--aurora-base` 冲突；玻璃面板透出的"底"不一致 | **P1** |
| **C5** | **滚动条硬编码 `#d9d9d9` / `#bfbfbf`，暗色下看不清** | `index.css` L46-51 硬编码滚动条，未走 `--ink-faint` 或独立 token | **P2** |
| **C6** | **`@deprecated` 旧 token 别名仍在被使用（应逐步清空）** | `EmptyState.vue` L46-69 用 `--color-ink-soft` `--color-surface-sunk`；`tokens.css` L142-159 保留这些别名是兼容策略，但应迁回 v2 token | **P2** |

### 2.2 尺寸 token 化（font / padding / radius）

| 编号 | 问题 | 铁证 | 优先级 |
|---|---|---|---|
| **C7** | **`font-size: 数字px/rem` 401 处** | 包含 `font-size: 22px / 24px / 18px / 16px / 14px / 13px / 12px` 等硬编码，应替换为 `--text-h1..h4/body/small/meta`；如 `OfferList.vue` L285 `.stat-value { font-size: 22px; font-weight: 600 }`（应 `--text-h2`） | **P1** |
| **C8** | **`padding: 数字px` 126 处** | 包含 `padding: 24px / 16px / 20px / 12px / 8px`，应替换 `var(--space-6/4/...)`；如 `OfferList.vue` L279 `.page-container { padding: 24px }`（应 `--space-6`） | **P1** |
| **C9** | **`border-radius: 数字px` 165 处** | 包含 `8px / 10px / 12px / 16px`，应替换 `var(--radius-sm/md/lg)`；如 `OfferList.vue` 缺省、CandidateList L874 `.candidate-row { border-radius: 12px }`（应 `--radius-md`） | **P1** |
| **C10** | **主圆角漂移** | tokens.css L130 设 `--radius-md: 16px`，但 `CandidateList L874 .candidate-row { border-radius: 12px }`、`OnboardingList/InterviewList L155 .page-container { padding: 24px }` 多个文件用 12px | **P1** |

### 2.3 表格 / 表单 / 弹窗

| 编号 | 问题 | 铁证 | 优先级 |
|---|---|---|---|
| **C11** | **数据表表头未走玻璃** | `glass.css` L341-358 定义了 `.glass-table` 类（表头半透明白 + hover 行品牌浅底），但所有列表页（Offer/Demand/Onboarding/Interview/Candidate）`<n-data-table>` 都未加 `class="glass-table"` | **P1** |
| **C12** | **批量通知弹窗完全自写样式** | `CandidateList.vue` L226-373 弹窗内 `modal-header/close-btn/info-callout/editor-section` 等 8+ 个 class 全自写，混 Ant Design 蓝色 `#e6f7ff/#91d5ff/#1890ff`；应统一用 `n-modal preset="card"` + `glass-modal.css` 已落地的玻璃底 | **P1** |
| **C13** | **状态颜色映射函数散布各页** | OfferList L138-144 `statusColor()`、DemandList L480-490 `getStatusType/Text()`、CandidateList L730-748 `channelMap/stageMap` —— 同一语义重复定义，应抽公共 `composables/useStatusTag.ts` 收口 | **P2** |
| **C14** | **表单 label 散见 `color: #666/#999`，未走 token** | DemandList L787/L887/L914/L919、L946/L949、L1019/L1025/L1037、L1065；Login L422、L432；OfferList 等多处 label 用硬编码灰色 | **P1** |
| **C15** | **`<n-button :bordered="false">` 多页重复** | OfferList/OnboardingList/InterviewList 等多处取消 bordered 后没补玻璃底样式，靠 `.n-card.n-card` 全局规则救场；显式声明 `.glass-card` 更好 | **P2** |

---

## 三、交互形式问题（Interaction）

| 编号 | 问题 | 铁证 | 优先级 |
|---|---|---|---|
| **I1** | **表格行无键盘可达** | grep `tabindex` / `@keydown.enter` 在 `OfferList / DemandList / OnboardingList / InterviewList / CandidateList` 0 命中；仅 StatBar / Dashboard announcement-item 有 | **P1** |
| **I2** | **状态强调色不统一** | `StatBar.vue` L88-92 定义 amber/rose/sky/emerald 四态走 `--c-warning/error/info/success`；`Dashboard.vue` `matter-tab__count` 走 `--brand-soft + --brand`（品牌色，不分语义）；`OfferList.statusColor` 走硬编码 Ant Design 色 —— 同类强调色三套规范并存 | **P1** |
| **I3** | **操作列按钮过多** | `OfferList.vue` L171-196 单行最多 5 个按钮 + `NSpace size=4`，列宽 320px；`OnboardingList.vue` L57-88 单行最多 4 个按钮，列宽 360px；`CandidateList.vue` L191-198 文字链 4 个 + Ellipsis icon —— 用户认知负担重 | **P1** |
| **I4** | **入场动效只在 Dashboard** | `Dashboard.vue` 用 `.workbench-card + .workbench-card--stagger-1..6` 6 级 stagger；其他 50+ 页无任何换页过渡，路由切换生硬 | **P1** |
| **I5** | **Loading 状态三套** | Dashboard 用 `defineAsyncComponent` + SkeletonCard 占位；OfferList/DemandList 等用 `:loading="loading"` + `<n-spin>`；CandidateList `loading` 不展示（mockData 假数据） —— 用户感知不连贯 | **P1** |
| **I6** | **Hero 搜索与全局搜索 ⌘K 不联动** | `Layout.vue` L74-92 `⌘K / Ctrl+K` 打开 `globalSearchOpen` Modal；`Dashboard.vue` L13-23 hero 内嵌搜索是独立的 `searchKeyword` —— 同一搜索词不同行为 | **P2** |
| **I7** | **占位页"开发中"无差异化提示** | `Placeholder.vue`（`/settings/onboarding` 等 5 处）打开后用户不知道是开发中还是正式空页 —— 无进度标识、无 ETA、无文档链 | **P1** |
| **I8** | **关闭按钮自写未对齐** | `CandidateList.vue` L236-239 `.close-btn { background: none; border: none; ... }` 自写关闭按钮；应统一走 `n-modal` 自身的 close icon | **P2** |
| **I9** | **`n-menu` 300ms transition 硬关闭（Layout.vue L495-505）** | 注释说"避免新旧 active 叠在一起 300ms"——这本来就是设计预期，硬关可能引起 Naive 后续版本兼容问题 | **P2** |
| **I10** | **快捷键仅 ⌘K** | grep `addEventListener('keydown'` 仅有 Layout 的 ⌘K；缺常用快捷键（`/` 聚焦搜索、`g+d` 跳工作台、`?` 帮助） | **P2** |

---

## 四、用户体验问题（UX）

### 4.1 响应式 & 设备

| 编号 | 问题 | 铁证 | 优先级 |
|---|---|---|---|
| **U1** | **5 个列表页仅 CandidateList 有响应式（1024/768 断点）** | `OfferList / DemandList / OnboardingList / InterviewList` 0 `@media` 命中；`StatBar 4→2→1` / `Login <600/<380` / `ThemeSettings <900/700` 已落 —— 表格在 <1024px 直接溢出 | **P0** |
| **U2** | **侧栏在 <768px 无折叠为抽屉的策略** | `Layout.vue` 完整文件搜索 `@media` 0 命中；移动端访问会挤占 ~240px 侧栏，主内容只余 ~500px | **P0** |
| **U3** | **数据表横向溢出无内部滚** | n-data-table 默认不自滚，业务页靠 `card` 容器自滚；OfferList 等 9 列在 <1280px 时表头必横滚但未给用户提示 | **P2** |

### 4.2 暗色模式

| 编号 | 问题 | 铁证 | 优先级 |
|---|---|---|---|
| **U4** | **业务页硬编码颜色暗色下不切** | tokens.css L161-208 已落完整暗色变量集；但 C1 列出的 99 处 Ant Design 硬编码色在 body.dark 下仍是浅色 —— 暗色模式"白纸黑字 + 暗色玻璃" 强烈冲突 | **P0** |
| **U5** | **业务页 `#fff / white / #f5f5f5` 容器底暗色下不切** | `DemandList L698 .demand-container { background: #f0f2f5 }` / `DemandList L725 .demand-card { background: white }` / `CandidateList L814 / L872` 等 —— 暗色下出现"白色卡片漂浮在深色玻璃" | **P0** |
| **U6** | **body 背景硬编码覆盖暗色 token** | `index.css` L21 `background-color: #f5f5f5` 写在 `body { }` 不在 `body.dark` 内；暗色下仍是浅灰 | **P1** |
| **U7** | **滚动条暗色下不变** | `index.css` L46-51 未提供 `body.dark ::-webkit-scrollbar-thumb` 覆写 | **P2** |

### 4.3 信息密度 & 引导

| 编号 | 问题 | 铁证 | 优先级 |
|---|---|---|---|
| **U8** | **页头"管理 X"文案过于平铺** | 7 个页 page-title 都是「候选人管理 / Offer 管理 / 面试管理 / 待入职管理」单层，无副标题、无数据量、无快捷入口 | **P2** |
| **U9** | **空状态组件分散 + 默认值过简** | `EmptyState.vue` 组件已有但默认文案"暂无内容 / 当前没有需要处理的事项"过于通用；`CandidateList / DemandList / OnboardingList` 多处直接用 `n-empty`（Naive UI 默认），未走 EmptyState 组件 —— 视觉/文案不统一 | **P1** |
| **U10** | **mockData 含明显错误数据** | `CandidateList.vue` L643-666：mockData 中"张三，CDD005878，**8 岁**，本科，**1 年**经验" —— 给真实用户演示时会造成专业性怀疑 | **P1** |
| **U11** | **错误态不友好** | `main.ts` L102-107 全局 error 仅 console.error；API 404/500 没有 UI 兜底（只有 axios 拦截器 404 console.warn，UI 无反馈）；用户遇到后端 bug 看到空白 | **P0** |
| **U12** | **关键操作无二次确认** | `OfferList.handleTransition()` L255-272 状态转移只校验 reason 必填；`OnboardingList.handleTransition` L109-117 直接调用无确认 —— 误操作风险 | **P1** |
| **U13** | **toast / 通知不规范** | grep `message.success / error / warning` 各页随意调用，无统一的"成功 2s 自动消失、错误需手动关闭"规范；toast 文案有时英文有时中文 | **P2** |

### 4.4 可访问性 (a11y)

| 编号 | 问题 | 铁证 | 优先级 |
|---|---|---|---|
| **A1** | **`color: #8c8c8c` 与 `--ink-soft #475569` 对比度差距大** | WCAG AA 要求正文 ≥ 4.5:1，`#8c8c8c` 对白底约 3.5:1 **不达标**；应统一走 `--ink-soft`（4.6:1）或更深 | **P1** |
| **A2** | **状态强调色对比度** | `--c-warning #F59E0B` 对白底约 2.4:1 **不达标**；Tag 内文字用纯色时需配 `--c-warning-soft` 浅底 | **P2** |
| **A3** | **占位 emoji 大量使用** | `Login.vue` L145-159 `📊👥📋🔔` / `DemandList.vue` L255-281 `🎓💼🏢👥🌟📍` 等用 emoji 替代图标 —— 不可被屏幕阅读器朗读、无 ARIA、无悬停态 | **P2** |
| **A4** | **缺全局 skip-to-content** | 完整 Layout.vue 无 `skip-link` / `role="navigation"` 等 a11y landmark；键盘用户无法跳过侧栏直接进主内容 | **P2** |
| **A5** | **图标按钮无 aria-label** | `Layout.vue` L74-92 搜索按钮已有 `aria-label="全局搜索"` ✓；但 CandidateList L196-198 Ellipsis icon、DemandList L84-85 编辑/详情按钮等未声明 | **P1** |

---

## 五、问题分布总览（按优先级）

| 优先级 | 数量 | 代表问题 |
|---|---|---|
| **P0** | 9 | F1 占位页无感、C1 99 处硬编码色、C2 主按钮字色冲突、C3 业务页未用 glass 类、U1 5 列表页无响应式、U2 侧栏无移动折叠、U4 暗色下 99 处 Ant 色冲突、U5 暗色下白色卡漂浮、U11 错误态仅 console |
| **P1** | 16 | F2 404 跳首页、F3 Forbidden 无玻璃、F4 SettingsLayout :deep hack、F6 无面包屑、C4 body 浅灰底覆盖暗色、C7-C10 401+126+165 处尺寸硬编码、C11 表头未走玻璃、C12 自写弹窗、C14 label 灰色硬编码、I1 表格行无键盘、I2 强调色三套规范、I3 操作列按钮过多、I4 入场动效仅 Dashboard、I5 Loading 三套、I7 占位无差异化、U6 body 浅灰、CandidateList 列表页 768 断点、U9 空状态分散、U10 mockData 错数据、U12 关键操作无二次确认、A1 `#8c8c8c` 对比度不达标、A5 图标按钮无 aria-label |
| **P2** | 13 | F5/F7 两套导航实现、列表页 RBAC 缺、C5/C6 滚动条与旧 token、C13/C15 状态函数散布、I6/I8/I9/I10 联动/快捷键、U3 表横滚、U7 滚动条暗色、U8 页头文案、U13 toast 规范、A2/A3/A4 a11y |

---

## 六、已落地能力（不算问题，列出用于参考）

| 模块 | 文件 | 状态 |
|---|---|---|
| **设计 token v2 液态玻璃** | `styles/tokens.css` | ✓ 单一事实来源，品牌/玻璃/语义/阴影/极光/z-index/间距/字体/圆角/缓动/暗色全齐 |
| **玻璃原子类** | `styles/glass.css` | ✓ `.glass-panel / .glass-card / .glass-input / .glass-tag / .btn-primary / .btn-secondary / .btn-ghost / .btn-danger / .gradient-title / .glass-table / .glass-sidebar / 全局 .n-card.n-card` |
| **Modal/Drawer 玻璃化** | `styles/glass-modal.css` | ✓ `.n-modal / .n-drawer / .n-modal-mask / .n-drawer-mask` 毛玻璃遮罩 |
| **运行时主题 store** | `stores/theme.ts` | ✓ hex→rgb→hsl 工具 + 持久化 + DOM 应用 + auto 模式监听 |
| **品牌自定义 UI** | `pages/settings/ThemeSettings.vue` | ✓ 6 推荐色 + 12 色板 + 取色器 + 派生色预览 + 实时预览 |
| **登录/工作台玻璃化** | `Login.vue / Dashboard.vue / Layout.vue` | ✓ T2.1-T2.3 标注，玻璃极光底+卡片+输入+stagger 动效 |
| **SettingsLayout 视觉锚点** | `pages/settings/SettingsLayout.vue` | ⚠️ `:deep` 一次性覆盖 25 子页（是 hack 不是方案） |
| **空状态组件** | `components/dashboard/EmptyState.vue` | ✓ 组件已存在，但旧 token（应迁移） |
| **状态 Tag 组件** | `components/common/StatusTag.vue` | ✓ 4 态语义 tag + pulse 动效 |
| **StatBar 组件** | `components/dashboard/StatBar.vue` | ✓ 4 强调色 + ARIA + 4→2→1 响应式 + 键盘 |
| **全局 axios 拦截器** | `main.ts` L21-37 | ✓ 404/500/401/403 区分 + console 区分 |
| **暗色模式切换** | tokens.css §14 + ThemeSettings.vue | ✓ 变量集 + 三模式 + 持久化 |
| **⌘K 全局搜索** | Layout.vue L167-92 | ✓ 键盘可达 + Modal 打开 |

---

## 七、改造优先级建议（与研发执行清单一一对应）

```
阶段 1（0.5 人日）  全局 token 强制 + 浅色基线      → 解决 U6 / C4 / U7 / 滚动条
阶段 2（0.5 人日）  业务列表页硬编码颜色全替换       → 解决 C1 / C14 / U4 / U5 / A1
阶段 3（1.0 人日）  5 列表页响应式 + 侧栏移动折叠    → 解决 U1 / U2 / U3
阶段 4（1.0 人日）  框架组件对齐（按钮字色、表头玻璃、操作列瘦身） → 解决 C2 / C3 / C11 / I2 / I3
阶段 5（1.0 人日）  交互增强（入场动效、键盘可达、占位差异化、二次确认） → 解决 F1 / F6 / I1 / I4 / I7 / U12 / A5
阶段 6（0.5 人日）  错误态与 a11y（错误页、skip-link、aria-label） → 解决 F2 / F3 / U11 / A1 / A4
阶段 7（0.5 人日）  SettingsLayout 去 hack、表格/弹窗 token 化   → 解决 F4 / F5 / C12
阶段 8（持续）      a11y 打磨、快捷键、toast 规范                 → 解决 P2
```

总计 **5–6 人日**可解 9 个 P0 + 11 个 P1（占总数 64%）。