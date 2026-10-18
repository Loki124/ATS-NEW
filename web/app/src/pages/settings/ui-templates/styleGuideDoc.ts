/**
 * styleGuideDoc.ts — 《前端UI样式文档》结构化数据
 *
 * 2026-10-18 兵哥要求「加个页签输出前端UI样式文档说明」。本文件是该文档的**唯一数据源**，
 * 由模板中心「样式文档」页签渲染；与以下权威文件保持同源（改规则必须同步）：
 *   - docs/04-ui/frontend-layout-standard.md（布局规范全文）
 *   - AGENTS.md（机器约束，RFC 2119）
 *   - styles/glass.css + styles/tokens.css（令牌与全局类真源）
 *
 * 设计约束：条目分三级 —— MUST（强制）/ NEVER（禁止）/ NOTE（说明），
 * 渲染时用语义色区分；新增规则优先改本文件，不要在页面里另起一份。
 */

/** 条目级别：must=必须这样做 · never=禁止这样做 · note=补充说明 */
export type DocLevel = 'must' | 'never' | 'note'

export interface DocItem {
  level: DocLevel
  text: string
  /** 可选：等宽展示的代码/类名/令牌 */
  code?: string
}

export interface DocSection {
  key: string
  title: string
  intro?: string
  items: DocItem[]
}

export const STYLE_GUIDE_DOC: DocSection[] = [
  {
    key: 'skeleton',
    title: '一、页面骨架与列表标准',
    intro: '2026-10-18 兵哥拍板：列表页统一乙系（独立设置页列表）为全站唯一标准，甲系（Tab 内嵌列表）仅为存量形态。',
    items: [
      { level: 'must', text: '列表页一律用乙系结构：.page-container > .page-header + .page-body > .glass-panel.panel-shell > .toolbar + .table-wrap' },
      { level: 'must', text: '页头 .page-header 只放标题 + 副标题，操作控件一律移入面板内 .toolbar；页头与内容区间禁加额外 margin 制造留白带' },
      { level: 'never', text: '新页面不得使用甲系「Tab 内嵌列表」形态；确有 tab 嵌入场景时由父页直接渲染乙系结构' },
      { level: 'must', text: 'n-data-table 必须包 .table-wrap 并加 flex-height，保证表格撑满面板、仅表体内部滚动' },
      { level: 'note', text: '存量 4 个甲系页面（RolesTab / ResourcesTab / reason-library 两页）暂不改造，随各页迭代收口' },
    ],
  },
  {
    key: 'spacing',
    title: '二、间距与布局令牌',
    intro: '间距只用 8 的整数倍；页面安全边距与弹窗内边距已全局 token 化，页面不得自行覆盖。',
    items: [
      { level: 'must', text: '间距阶梯 --space-1/2/3/4/5/6/8/12/16 = 4/8/12/16/20/24/32/48/64px；区块 24、卡片内 16、表单项 12、紧密元素 8' },
      { level: 'never', text: '裸像素间距（margin-top:20px 之类）与 var(--x, #hex) 兜底写法（暗色回落浅色必崩）' },
      { level: 'must', text: '页面安全边距：--page-pad-x/y = 24px（≤767px 自动降 16px），由 .page-container 全局注入，页面 scoped 不得清零' },
      { level: 'must', text: '弹窗三区内边距已 token 化（--modal-pad-x/y），禁止 scoped 清零；抽屉底部操作栏统一 .drawer-footer' },
      { level: 'must', text: '自适应栅格用 .grid-auto（auto-fit + minmax 280px）；禁 n-grid :cols="2" 硬编码列数、禁 n-row/n-col' },
      { level: 'never', text: '手写固定列数 + 媒体查询栅格；发明 480/920/1100 等非标断点（只用 768/1024/1280 三档）' },
    ],
  },
  {
    key: 'color',
    title: '三、颜色与令牌',
    items: [
      { level: 'must', text: '颜色一律语义令牌：品牌 --brand* / 文本 --ink* / 状态 --c-success|warning|error|info，暗色模式自动联动' },
      { level: 'never', text: '硬编码 hex；从品牌色推导语义色；页面 scoped 重复定义全局已有类' },
      { level: 'must', text: '弱化说明文字统一 .field-hint（--ink-soft + --text-meta），禁私建 switch-tip / input-tip 等私有命名' },
    ],
  },
  {
    key: 'table',
    title: '四、表格与列对齐',
    intro: '列对齐唯一真源 composables/useTableColumns.ts，四档工厂 column(col, tier)。',
    items: [
      { level: 'must', text: 'short 短值/枚举/标识（编码、状态、类型）→ 居中；control 控件/操作 → 居中；numeric 数值 → 居中' },
      { level: 'must', text: 'text 长文本（描述、规则表达式、拒绝原因）→ 左对齐，禁居中（居中毁扫读）' },
      { level: 'never', text: '手写 align / className 指定列对齐；操作列按钮 size 写字面量 "small"/"tiny"' },
      { level: 'must', text: '操作列固定 fixed:"right"，宽度按按钮数裁定（2 个 176px / 3 个 210px / 4 个 260px）；NSpace 必须 wrap:false' },
      { level: 'must', text: '同组按钮全有 icon 或全无；删除保留 type="error"（危险色是安全信号）；size 引用 OP_ACTION_BUTTON_SIZE' },
      { level: 'must', text: '分页用 localPagination() / remotePagination()，禁内联 { pageSize: N } 对象' },
    ],
  },
  {
    key: 'modal',
    title: '五、弹窗规范',
    intro: '宽度由站内存量 20+ 种收敛为 4 档；关闭必须守卫脏数据。',
    items: [
      { level: 'must', text: '宽度只用 420/520/640/960px 四档（2 字段/3-4 字段/5-8 字段/多 tab），统一带 max-width: 92vw 兜底窄屏' },
      { level: 'must', text: '编辑弹窗三件套：:mask-closable="false" + :close-on-esc="false" + :on-mask-click="requestClose"' },
      { level: 'must', text: '关闭走 useCloseGuard composable，脏数据弹二次确认；footer 用全局 .drawer-footer 右对齐' },
      { level: 'must', text: '确认对话框用 preset="dialog"（依赖内置按钮 loading 联动），危险操作传 :positive-button-props="{ type: \'error\' }"' },
      { level: 'never', text: '把 dialog 改写成 card（丢内置按钮联动）；触发原生 confirm()；文案写「是否确认」而不说明具体后果' },
      { level: 'must', text: '主操作 type="primary" class="gradient-btn" + :loading，loading 期间禁用防止重复提交' },
    ],
  },
  {
    key: 'form',
    title: '六、表单规范',
    items: [
      { level: 'must', text: 'label-placement 全站收敛 top；确需左排布的独立配置页 label-width 统一 180px' },
      { level: 'must', text: '同语义字段同控件：枚举一律 n-select、日期一律 n-date-picker；多选必须加 max-tag-count（responsive 或固定 N）' },
      { level: 'must', text: '校验三件套：n-form 上 :model + :rules、n-form-item 上 path、提交前 formRef.validate()' },
      { level: 'never', text: '单选按钮组承担枚举筛选（列表筛选统一 n-select；仅穷举可见场景用 radio）' },
    ],
  },
  {
    key: 'state',
    title: '七、空态与状态机',
    items: [
      { level: 'must', text: '数据视图空态双态：「暂无数据」与「筛选无结果」分开展示（#empty 插槽按数据源区分）' },
      { level: 'must', text: '交互组件六态齐全：default / hover / active / focus-visible / loading / disabled；异步提交 loading 期间 disabled' },
      { level: 'must', text: '异步操作四类反馈：加载 / 空态 / 成功 / 失败，禁静默失败；通用状态优先复用 StateView 七态组件' },
      { level: 'must', text: '配置页必须实现 isDirty 脏检查（未改动保存 disabled）+ 离开路由前拦截；自动保存型须显示「保存中/已自动保存/未保存」三态' },
    ],
  },
  {
    key: 'a11y',
    title: '八、交互与可访问性',
    items: [
      { level: 'must', text: '触控目标 ≥44×44px（图标按钮用 padding/伪元素扩大命中区）；320px 视口无横向溢出' },
      { level: 'must', text: '交互元素可 Tab 访问、语义化标签（button/a）、禁 tabindex>0；错误信息不仅依赖颜色（颜色+图标+文字）' },
      { level: 'must', text: '动态文本不得撑破布局：overflow-wrap:anywhere / ellipsis 截断且提供 title 查看完整内容' },
      { level: 'never', text: '用户输入经 v-html / dangerouslySetInnerHTML 直出（默认文本渲染即转义）' },
      { level: 'must', text: '破坏性操作分级：可逆直接执行 + Toast 撤销（5-8s）/ 中等确认框 / 高危确认框 + 影响预览；预计填写 >1 分钟的表单自动存草稿（敏感字段禁入持久化介质）' },
    ],
  },
  {
    key: 'naming',
    title: '九、命名与代码约束',
    items: [
      { level: 'must', text: '结构类优先复用 glass.css 全局类（.panel-shell/.toolbar/.table-wrap/.grid-auto/.field-hint/.drawer-footer 等），页面 scoped 不重复定义' },
      { level: 'must', text: '搜索/筛选用全局宽度类 .rule-filter-search(240px) / .rule-filter-select(136px)，禁行内 style="width:NNNpx"' },
      { level: 'must', text: '单页专用逻辑（草稿、脏检查）下沉为 composable，禁多页各写各的；通用组件放 components/common/ 且不耦合业务 API' },
      { level: 'note', text: '模板中心自身即规范的活文档：/settings/ui-templates 可按分类查看模板的代码结构与渲染效果' },
    ],
  },
  {
    key: 'skin',
    title: '十一、设置页列表模板皮肤规范（v3 · 2026-10-18 兵哥专项调整）',
    intro: '页面骨架之上的视觉皮肤规范。当前仅落地在模板中心（ListTemplate.vue scoped 布局 + button-skin.css 按钮皮肤），兵哥确认后搬入 glass.css 全局推行，结构零改动。',
    items: [
      { level: 'must', text: '背景一律纯色：分区三级（页底 < 内嵌 < 面板），由背景色差异区分，禁渐变、禁 backdrop 模糊' },
      { level: 'never', text: '按钮与组件的 box-shadow / 投影；用边框线对不同分区做视觉分隔' },
      { level: 'must', text: '间距只用 --space-*（4/8/16/24…），容器边距成对出现：padding 上下、左右各自对称' },
      { level: 'must', text: '最大容器内边距固定 16px（--stpl-gap-page）；页头与 body 间距 16px（--stpl-gap-inner）；容器内元素间距 8px（--stpl-gap-tight）' },
      { level: 'must', text: '表格标题行背景色常驻（--stpl-th-bg），数据行用斑马纹（--stpl-row-alt-bg）区分，去掉所有横竖边线 —— 纯靠底色分区' },
      { level: 'must', text: '列表必须带分页组件，且必须引用 composables/useTablePagination（兵哥 2026-10-18 16:00 定为全站唯一分页模板）：外观固定「共 N 条 │ ‹ 1 2 3 › │ 20 / 页 ▾ │ 跳至 [__]」' },
      { level: 'never', text: '页面内出现 { pageSize: N } 字面量、自造 prefix、或直接给 n-data-table 传 pagination 对象（禁绕开 useTablePagination）' },
      { level: 'must', text: '每页条数用 TABLE_PAGE_SIZE（20）与 TABLE_PAGE_SIZE_OPTIONS（10/20/50/100），禁页面私加档位' },
      { level: 'must', text: '数据表变化时（搜索/筛选/删除）回到第 1 页，避免停留在越界页码显示空表' },
      { level: 'note', text: 'naive 远程分页用 itemCount（非 total）表达总数，remotePagination 已对齐；切页在 onPageChange 里重新拉取' },
      { level: 'must', text: '按钮概念是「4 类 6 态」：类 = 主/次/幽灵/危险；态 = 默认/悬浮/激活/聚焦/加载/失效。每类都必须实现全部 6 态' },
      { level: 'must', text: '🔴 仅幽灵按钮默认态无背景（透明底）；主/次/危险三类默认态必须是实色底 —— 缺一层底色会让按钮在浅底上「消失」' },
      { level: 'must', text: '主按钮用 --brand-button（R-210 禁锁 --brand），hover/pressed 用既有 --brand-hover / --brand-pressed；危险按钮用 --c-error / --c-error-deep' },
      { level: 'must', text: '焦点态必须可见：统一 outline: 2px solid var(--brand) + outline-offset: 2px（naive 默认 focus 只换文字色，看不出焦点位置）' },
      { level: 'must', text: '按钮图标与文字间距固定 4px（--n-icon-margin: var(--space-1)）' },
      { level: 'never', text: 'naive 按钮自定义皮肤时只写 class 里的 background 而不钉死 --n-color / --n-text-color —— naive 以 inline style 注入同名变量，优先级更高会静默盖掉' },
      { level: 'must', text: '按钮 6 态必须能在同一屏并排对比：hover/active/focus 是交互伪类，同一时刻只有一个按钮能进入该态。模板中心用 .stpl-btn--force-{hover|active|focus|loading|disabled} 把伪类固化成类做实拍矩阵（⚠️ 该类仅供演示与设计走查，业务页面禁挂）' },
      { level: 'note', text: '按钮 4 类 6 态已独立为「按钮」页签（四类速览 + 六态实拍矩阵 + 工具条/弹窗 footer/表格行内/破坏性确认/加载流转五个场景的模拟数据演示）' },
      { level: 'note', text: '实现要点：按钮基于 quaternary 基底（不渲染 __border，天然避开设置页全局渐变注入规则），皮肤用 .stpl-btn--* 类自绘，冲突零风险' },
      { level: 'note', text: '皮肤令牌（--stpl-inset-bg 等）定义在 .stpl-root 上，组件根节点必须挂 .stpl-root，否则 var() 解析失败导致底色消失' },
      { level: 'note', text: '令牌从现有语义色派生（color-mix），不新增设计令牌、不硬编码 hex' },
    ],
  },
  {
    key: 'checklist',
    title: '十二、新增页面检查清单',
    intro: '新建页面前逐条过一遍；任何一条不过，Code Review 打回。',
    items: [
      { level: 'must', text: '① 从模板中心复制乙系骨架（?cat=list&tpl=list-standalone），未自造页面结构' },
      { level: 'must', text: '② 间距只用 --space-*（8 的倍数），颜色只用语义令牌，无硬编码 hex' },
      { level: 'must', text: '③ 列走 column(col, tier) 四档，操作列 size 引用 OP_ACTION_BUTTON_SIZE' },
      { level: 'must', text: '④ 弹窗宽度 4 选 1 + 92vw + 三件套，关闭走 useCloseGuard' },
      { level: 'must', text: '⑤ #empty 空态双态 + 加载/失败反馈齐全' },
      { level: 'must', text: '⑥ 多选 max-tag-count，栅格 .grid-auto，无 n-grid 硬编码列数' },
      { level: 'must', text: '⑦ 浏览器实测 320/768/1200 三档无溢出，表体滚动、行高、列对齐肉眼核对' },
    ],
  },
]

/** 页脚说明：文档权威来源 */
export const DOC_SOURCE_NOTE =
  '本页内容与 docs/04-ui/frontend-layout-standard.md、AGENTS.md 机器约束、styles/glass.css 全局类定义同源；三处任一更新，本文件必须同步（2026-10-18 起作为唯一结构化出口）。'
