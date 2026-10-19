/**
 * templateRegistry.ts — 前端组件规范元数据注册表（单一真源）
 *
 * 2026-10-18 兵哥「前端组件规范」体系立项。本文件是模板清单的**唯一权威数据源**：
 * 模板中心页面（index.vue）按此渲染分类导航、代码结构、渲染预览与用法说明。
 * 新增模板 / 修改模板规格 → 只改本文件，不改页面渲染逻辑。
 *
 * 设计约束（与 docs/04-ui/frontend-layout-standard.md 同步）：
 *   1. 间距只用 8 的整数倍（--space-2=8px / --space-4=16px / --space-6=24px）。
 *   2. 颜色一律走语义令牌（--brand / --ink / --ink-soft / --border-hairline），禁硬编码 hex。
 *   3. 结构类优先复用 glass.css 全局类，不在页面 scoped 重复定义。
 *   4. 列对齐走 useTableColumns.column(col, tier) 四档工厂，禁手写 align。
 */

/** 模板分类标识（2026-10-19 起按 TDesign 开源设计系统分类：基础/导航/输入/数据展示/反馈/规范/样式文档） */
export type TemplateCategory = 'base' | 'nav' | 'entry' | 'data' | 'feedback' | 'spec' | 'doc';

/** 单个模板的元数据 */
export interface TemplateMeta {
  /** 模板唯一标识（同时作为 Demo 组件的注册 key） */
  key: string;
  /** 分类 */
  category: TemplateCategory;
  /** 中文名 */
  name: string;
  /** 一句话用途说明 */
  summary: string;
  /** 标准骨架代码（template 片段，可直接复制） */
  code: string;
  /** 必须遵守的约束清单 */
  rules: string[];
  /** 已落地该模板的参考页面（file:line 或页面名） */
  references: string[];
  /** 已知例外 / 不适用场景 */
  caveats?: string[];
}

/** 速查表行（三类速查表统一形状，便于页面统一渲染） */
export interface SpecRow {
  /** 主标识（tier / width / 类名） */
  key: string;
  /** 补充说明 */
  desc: string;
  /** 是否等宽显示（类名 / 代码标识用 true） */
  mono?: boolean;
}

/** 分类元信息（渲染左侧导航用） */
export interface CategoryMeta {
  key: TemplateCategory;
  label: string;
  desc: string;
}

/**
 * 分类定义（顺序即左侧导航顺序）
 * 注：枚举筛选统一用 n-select；单选语义强、需一眼可见全貌的（如主题模式三态图示）才用 radio。
 * doc 为特殊页签：不挂模板，直接输出《前端组件规范样式文档》（结构化规则全文）。
 */
export const CATEGORIES: CategoryMeta[] = [
  { key: 'base', label: 'uiTemplates.cat.base', desc: '主/次/幽灵/危险四态与交互六状态，图标间距固定 4px' },
  { key: 'nav', label: 'uiTemplates.cat.nav', desc: '可复用组件与 composable 的引用约定，分页为统一模板' },
  { key: 'entry', label: 'uiTemplates.cat.entry', desc: '表单与配置项的统一写法：label 排布、栅格、分组与校验' },
  { key: 'data', label: 'uiTemplates.cat.data', desc: '以身份管理为范本：工具条 + flex-height 表格' },
  { key: 'feedback', label: 'uiTemplates.cat.feedback', desc: '卡片式编辑弹窗与确认对话框的两类标准形态' },
  { key: 'spec', label: 'uiTemplates.cat.spec', desc: '全站硬规则的活演示：列对齐 / 弹窗宽度 / 间距 / 按钮状态 / 令牌' },
  { key: 'doc', label: 'uiTemplates.cat.doc', desc: '《前端组件规范样式文档》结构化全文输出' },
];

/** 全局类清单（模板依赖的基础设施，渲染为速查表） */
export const GLOBAL_CLASSES: SpecRow[] = [
  { key: '.panel-shell', desc: '列表面板容器：flex 列 + 撑满高 + 8px 内衬（2026-10-18 提升为全局）', mono: true },
  { key: '.toolbar', desc: '工具条：flex + gap 8px + 下边距 8px + 换行', mono: true },
  { key: '.toolbar .spacer', desc: 'flex:1 占位，把右侧操作按钮推到行尾', mono: true },
  { key: '.table-wrap', desc: '表格滚动链：flex:1 + min-height:0，配合 flex-height 实现仅表体滚动', mono: true },
  { key: '.rule-filter-search', desc: '搜索框宽度 240px（含 max-width 压住 n-input 的 100%）', mono: true },
  { key: '.rule-filter-select', desc: '筛选下拉宽度 136px', mono: true },
  { key: '.glass-panel', desc: '玻璃面板：背景/模糊/圆角/边框，无内边距', mono: true },
  { key: '.glass-panel--card', desc: '卡片变体：用于表单分组卡片', mono: true },
  { key: '.gradient-btn', desc: '主操作按钮渐变底（primary 按钮挂此 class）', mono: true },
  { key: '.content-shell', desc: '超宽屏内容收束（max-width + 居中），已定义待推广', mono: true },
  { key: '.grid-auto', desc: '自适应栅格 auto-fit + minmax，替代硬编码列数', mono: true },
  { key: '.page-container', desc: '页面根：flex 列 + height 100%', mono: true },
  { key: '.page-header', desc: '标题区：仅标题 + 副标题，flex-shrink:0', mono: true },
];

/** 列对齐四档（单一真源：composables/useTableColumns.ts） */
export const COLUMN_TIERS: SpecRow[] = [
  { key: 'short', desc: '居中 · 短值/枚举/标识（编码、状态、类型）' },
  { key: 'control', desc: '居中 · 控件/操作列（按钮、开关、行内编辑）' },
  { key: 'numeric', desc: '居中 · 数值（数量、金额、百分比）' },
  { key: 'text', desc: '左对齐 · 长文本（描述、规则表达式、拒绝原因）—— 禁居中，居中毁扫读' },
];

/** 弹窗宽度档位（收敛自站内存量 20+ 种） */
export const MODAL_WIDTHS: SpecRow[] = [
  { key: '420px', desc: '2 个字段的简单编辑' },
  { key: '520px', desc: '3–4 个字段（最常用）' },
  { key: '640px', desc: '5–8 个字段 / 含分组' },
  { key: '960px', desc: '多 tab / 字段编排型' },
];

/**
 * 分页统一模板规格（单一真源：composables/useTablePagination.ts）
 * 兵哥 2026-10-18 16:00 指定：分页组件纳入组件模板作为全站统一模板
 */
export const PAGINATION_SPEC: SpecRow[] = [
  { key: '共 N 条', desc: 'prefix 固定文案，由 totalPrefix() 统一渲染', mono: true },
  { key: '‹ 1 2 3 ›', desc: '页码器：当前页品牌色实心 + 圆角', mono: true },
  { key: '20 / 页 ▾', desc: '每页条数选择器，档位固定 [10, 20, 50, 100]', mono: true },
  { key: '跳至 [__]', desc: '跳页器（showQuickJumper），大结果集必备', mono: true },
  { key: 'localPagination()', desc: '客户端分页：一口气取全量，组件自行切片；用非受控 defaultPage/defaultPageSize', mono: true },
  { key: 'remotePagination()', desc: '服务端分页：page + itemCount 由调用方 Ref 维护；⚠️ naive 远程分页用 itemCount（非 total）', mono: true },
  { key: '禁手写', desc: '页面内不得出现 { pageSize: N } 字面量、自造 prefix、或直接给表格传 pagination 对象', mono: true },
];

/**
 * 按钮 6 态判定标准（兵哥 2026-10-18 16:00：4 类 6 态需可并排对比）
 * 配套强制态类 .stpl-btn--force-*，见 templates/button-skin.css
 */
export const BUTTON_STATES: SpecRow[] = [
  { key: '默认 default', desc: '该类基色：主 = --brand-button，次 = 内嵌底，幽灵 = 透明，危险 = --c-error', mono: true },
  { key: '悬浮 hover', desc: '基色 + 12% 反色混合；主按钮用 --brand-hover，危险用 12% 白', mono: true },
  { key: '激活 active', desc: '基色 + 14% 墨色混合（明显更深）；主按钮用 --brand-pressed，危险用 --c-error-deep', mono: true },
  { key: '聚焦 focus', desc: '底色同默认 + 2px 品牌色焦点环（offset 2px）—— naive 默认只换文字色，必须补', mono: true },
  { key: '加载 loading', desc: '底色同默认 + spinner + cursor:wait；🔴 必须同时 disabled 防重复提交', mono: true },
  { key: '失效 disabled', desc: '底色降 30% 不透明 + 文字降 --ink-faint + cursor:not-allowed', mono: true },
];

/**
 * 按钮尺寸四档（兵哥 2026-10-19 批准引入，对齐 TDesign size 体系）
 * 此前系统只有 OP_ACTION_BUTTON_SIZE（小号）一档，563 个 n-button 无尺寸语义。
 * 用 .stpl-btn--xs|sm|md|lg 修饰，与类型类（--primary 等）正交叠加。
 */
export const BUTTON_SIZES: SpecRow[] = [
  { key: 'xs', desc: '行内紧凑：表格行内编辑/删除、标签旁微型操作，高 24px', mono: true },
  { key: 'sm', desc: '工具条默认：列表页/弹窗 footer 常规按钮，高 28px（= OP_ACTION_BUTTON_SIZE）', mono: true },
  { key: 'md', desc: '主 CTA：新建/保存/提交等每区唯一主操作，高 32px', mono: true },
  { key: 'lg', desc: '页眉/落地页主操作：视觉权重最高的一级入口，高 38px', mono: true },
  { key: 'OP_ACTION_BUTTON_SIZE', desc: '当前唯一落地的基准（= sm 小号），操作列统一引用，禁写字面量', mono: true },
];

/** 全部模板 */
export const TEMPLATES: TemplateMeta[] = [
  // ══════════════════════ 1. 数据展示（列表）模板 ══════════════════════
  {
    key: 'list-standalone',
    category: 'data',
    name: '独立设置页列表（乙系 · 全站唯一标准）',
    summary: '设置中心标准列表页结构：页头 + 玻璃面板 + 工具条 + flex-height 表格，表格撑满面板、表体内部滚动。',
    code: `<div class="page-container">
  <div class="page-header">
    <div>
      <h1 class="page-title">{{ t('title') }}</h1>
      <p class="page-subtitle">{{ t('subtitle') }}</p>
    </div>
  </div>

  <div class="page-body">
    <div class="glass-panel panel-shell">
      <!-- 工具条：左=搜索/筛选，spacer，右=操作按钮 -->
      <div class="toolbar">
        <n-input v-model:value="kw" :placeholder="t('ph.search')"
                 class="rule-filter-search" clearable>
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <n-select v-model:value="statusFilter" :options="statusOptions"
                  :placeholder="t('ph.status')" class="rule-filter-select" clearable />
        <div class="spacer"></div>
        <!-- 工具按钮：幽灵按钮 quaternary，主操作实色 primary -->
        <n-button class="stpl-btn stpl-btn--ghost" quaternary @click="onRefresh">
          <template #icon><n-icon :component="RefreshOutline" /></template>{{ t('act.refresh') }}
        </n-button>
        <n-button class="stpl-btn stpl-btn--primary" quaternary type="primary" @click="onCreate">
          <template #icon><n-icon :component="AddOutline" /></template>{{ t('act.create') }}
        </n-button>
      </div>

      <div class="table-wrap">
        <n-data-table :columns="columns" :data="rows" :loading="loading"
                      :row-key="(r: Row) => r.id" :pagination="localPagination()"
                      :bordered="false" flex-height>
          <template #empty>
            <n-empty :description="rows.length === 0 ? t('empty.noData') : t('empty.noMatch')" />
          </template>
        </n-data-table>
      </div>
    </div>
  </div>
</div>

/* ── 皮肤规范 v2（2026-10-18 兵哥专项调整，模板级局部，全局推行时搬入 glass.css）──
 * 令牌（纯色三级分区，背景色差异区分，无边框）：
 *   --stpl-page-bg : color-mix(in srgb, var(--ink) 3%, var(--surface))   页底
 *   --stpl-inset-bg: color-mix(in srgb, var(--ink) 6%, var(--surface))   内嵌
 *   --stpl-panel-bg: var(--surface)                                       面板
 *   --stpl-gap-*   : --space-1/2/4/6 = 4/8/16/24px
 * 按钮皮肤（quaternary 基底 + .stpl-btn--primary|default|ghost|danger，
 *   纯色、无渐变、无阴影、图标间距 --space-1）：
 *   .stpl-btn--primary      { background: var(--brand); color: var(--on-brand) }
 *   .stpl-btn--default      { background: var(--stpl-inset-bg); color: var(--ink) }
 *   .stpl-btn--ghost        { background: transparent; color: var(--ink-soft) }
 *   .stpl-btn--danger       { background: var(--c-error); color: var(--on-brand) }
 *   .stpl-btn { border:none; box-shadow:none; --n-icon-margin: var(--space-1) }
 * 提示：quaternary 基底不渲染 __border，不会被设置页全局渐变注入规则命中。 */`,
    rules: [
      '【全站唯一标准 · 2026-10-18 兵哥拍板】新列表页一律用乙系；甲系仅为存量形态，不得在新页面使用',
      '.page-header 只放标题 + 副标题，操作控件一律移入面板内 .toolbar',
      '.toolbar 必须用 <div class="spacer"></div> 推右，不用 n-space 分组',
      'n-data-table 必须包 .table-wrap 并加 flex-height，否则面板下方留白、表体不滚动',
      '搜索/筛选用类 .rule-filter-search / .rule-filter-select，禁行内 style="width:NNNpx"',
      '枚举筛选统一 n-select（穷举可见时才用 radio-group）',
      '操作列走 column(col, "control")：size 用 OP_ACTION_BUTTON_SIZE、quaternary、删除 type="error"',
      '必须提供 #empty 空态，并区分「无数据」与「筛选无结果」两态',
      '长列表（超过一屏）必须表头吸顶：依赖 flex-height + 定高父链，naive 默认固定表头，不得关掉；否则滚动丢失列上下文',
      '分页用 localPagination()，禁内联 { pageSize: N } 对象',
      '【皮肤 v2 · 2026-10-18】背景一律纯色（页底<内嵌<面板三级），禁渐变、禁 backdrop 模糊',
      '【皮肤 v2】组件 box-shadow 一律清除；不用边框线分区，只用背景色差异',
      '【皮肤 v2】容器边距成对出现：padding 上下、左右各自对称，取值只用 --space-*（8 的倍数）',
      '【皮肤 v2】按钮四态固定：主=brand 实色 / 次=内嵌底实色 / 幽灵=透明 / 危险=c-error 实色',
      '【皮肤 v2】按钮图标与文字间距固定 4px（--n-icon-margin: var(--space-1)）',
    ],
    references: [
      'pages/settings/DepartmentManagement.vue（标杆）',
      'pages/settings/JobLevelManagement.vue',
      'pages/settings/RecruitmentStage.vue',
      'ui-templates/templates/ListTemplate.vue（皮肤 v2 落地载体）',
    ],
    caveats: [
      '页面根需保证 flex 链完整：.page-container(height:100%) → .page-body(flex:1) → .panel-shell(flex:1) → .table-wrap(flex:1)',
      '皮肤 v2 当前仅落地在模板中心（ListTemplate.vue scoped），业务页面仍为全局玻璃外观；全局推行时把 .stpl-* 样式搬入 glass.css 即可',
    ],
  },
  {
    key: 'list-embedded',
    category: 'data',
    name: 'Tab 内嵌列表（甲系 · 存量形态）',
    summary: '历史存量形态：被父页以 tab 嵌入的列表组件，不加玻璃面板，滚动与内衬交给父页。仅供存量页对照，新页面禁用。',
    code: `<div class="xxx-tab">   <!-- scoped: flex:1; min-height:0; gap:var(--space-2) -->
  <div class="toolbar">
    <n-input v-model:value="kw" class="rule-filter-search" clearable />
    <n-select v-model:value="f" :options="opts" class="rule-filter-select" />
    <div class="spacer"></div>
    <n-button type="primary" class="gradient-btn" @click="onCreate">新建</n-button>
  </div>

  <div class="table-wrap">
    <n-data-table :columns="columns" :data="rows" :pagination="localPagination()"
                  :row-key="(r: Row) => r.id" flex-height>
      <template #empty><n-empty description="暂无数据" /></template>
    </n-data-table>
  </div>
</div>`,
    rules: [
      '⚠️ 新页面禁用本形态（2026-10-18 兵哥拍板乙系统一）；确有 tab 嵌入场景时，应由父页直接渲染乙系结构',
      '根节点不加 .glass-panel / .panel-shell —— 父页已提供面板外壳，再加会多一层内衬',
      '根节点必须 flex 列 + flex:1 + min-height:0 + gap:var(--space-2)，否则 flex-height 找不到确定高度',
      '.toolbar 与 .table-wrap 的内部写法与乙系完全一致',
    ],
    references: [
      'pages/settings/permission/RolesTab.vue（存量 · 模板原点）',
      'pages/settings/permission/ResourcesTab.vue（存量）',
      'pages/settings/reason-library/tags.vue（存量）',
      'pages/settings/reason-library/rules.vue（存量）',
    ],
    caveats: ['存量 4 页暂不改造，随各页迭代时收口为乙系；新页面误用甲系一律打回'],
  },
  {
    key: 'list-columns',
    category: 'data',
    name: '列定义四档对齐工厂',
    summary: '所有表格列必须走 column(col, tier) 工厂声明对齐档位，禁止手写 align 属性。',
    code: `import { h, NSpace, NButton, NIcon } from 'naive-ui'
import { CreateOutline, TrashOutline } from '@vicons/ionicons5'
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'
import { localPagination } from '@/composables/useTablePagination'

const columns = [
  // A 档 short：短值/枚举/标识 → 居中
  column({ title: '编码', key: 'code', width: 160 }, 'short'),
  // C 档 numeric：数值 → 居中
  column({ title: '权限码数', key: 'count', width: 100 }, 'numeric'),
  // D 档 text：长文本 → 左对齐（禁居中）
  column({ title: '描述', key: 'desc', width: 320 }, 'text'),
  // B 档 control：操作列 → 居中 + 固定右侧
  column({
    title: '操作', key: 'actions', width: 176, fixed: 'right',
    render: (row: Row) => h(NSpace, { size: 8, wrap: false }, () => [
      h(NButton, {
        size: OP_ACTION_BUTTON_SIZE, quaternary: true, type: 'primary',
        onClick: () => onEdit(row),
      }, {
        icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
        default: () => '编辑',
      }),
      h(NButton, {
        size: OP_ACTION_BUTTON_SIZE, quaternary: true, type: 'error',
        onClick: () => onDelete(row),
      }, {
        icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
        default: () => '删除',
      }),
    ]),
  }, 'control'),
]`,
    rules: [
      "tier 四档：short（短值/枚举）· control（控件/操作）· numeric（数值）· text（长文本，左对齐）",
      '长文本列必须用 text 档（左对齐），居中会毁掉扫读效率',
      '操作列固定 fixed:"right"，宽度按按钮数裁定：2 个→176px，3 个→210px，4 个→260px',
      '按钮 size 一律引用 OP_ACTION_BUTTON_SIZE 常量，禁写字面量 "small"/"tiny"',
      '同组按钮必须全有 icon 或全无 icon（frontend-layout-standard §1.8.1）',
      'NSpace 必须 wrap:false，防止按钮折行',
      '删除按钮保留 type="error" —— 危险色是安全信号，不许去掉',
    ],
    references: [
      'composables/useTableColumns.ts（唯一真源，166 行）',
      'styles/__tests__/table-alignment-rules.test.ts（对齐规则单测）',
    ],
  },

  // ══════════════════════ 2. 反馈（弹窗）模板 ══════════════════════
  {
    key: 'modal-card',
    category: 'feedback',
    name: '卡片式编辑弹窗',
    summary: '承载表单的编辑弹窗标准形态：preset="card" + 宽度分档 + 遮罩守卫 + 右对齐 footer。',
    code: `<n-modal
  :show="show" preset="card" :title="title"
  style="width: 520px; max-width: 92vw"
  :mask-closable="false" :close-on-esc="false"
  :on-mask-click="requestClose"
  @update:show="(v: boolean) => !v && requestClose()"
>
  <n-form ref="formRef" :model="form" :rules="rules"
         label-placement="top" size="medium">
    <n-form-item label="名称" path="name">
      <n-input v-model:value="form.name" placeholder="请输入名称" />
    </n-form-item>
    <n-form-item label="类型" path="type">
      <n-select v-model:value="form.type" :options="typeOptions" clearable />
    </n-form-item>
  </n-form>

  <template #footer>
    <div class="drawer-footer">
      <n-button :disabled="saving" @click="requestClose">取消</n-button>
      <n-button type="primary" class="gradient-btn"
                :loading="saving" @click="handleSave">保存</n-button>
    </div>
  </template>
</n-modal>`,
    rules: [
      '宽度只用 4 档：420 / 520 / 640 / 960px，并统一带 max-width: 92vw 兜底窄屏',
      '必须 :mask-closable="false" + :close-on-esc="false" + :on-mask-click="requestClose" 三件套',
      '关闭走 useCloseGuard composable，脏数据时弹二次确认',
      'footer 用全局 .drawer-footer（右对齐），禁各页 scoped 重复定义 footer 类',
      '主操作 type="primary" class="gradient-btn" + :loading，且 loading 期间禁重复提交',
      '多选控件必须加 max-tag-count（frontend-layout-standard §1.8.5 阻塞项）',
      '⚠️ naive preset="card" 把 .n-modal 直接打在 card 元素上（.n-card.n-modal 同元素），全局样式须用复合选择器',
    ],
    references: [
      'pages/settings/RecruitmentStage.vue',
      'pages/settings/RecruitmentRound.vue',
      'pages/settings/DepartmentManagement.vue',
    ],
    caveats: ['960px 档用于多 tab / 字段编排型弹窗，字段超单屏时不要降到 640px 以下，否则出现双滚动'],
  },
  {
    key: 'modal-confirm',
    category: 'feedback',
    name: '确认对话框',
    summary: '二次确认与结果告知的标准形态：preset="dialog" + 内置按钮联动，不要改写成 card。',
    code: `<n-modal
  :show="show" preset="dialog" :title="title"
  :positive-text="confirmText" :negative-text="cancelText"
  :loading="submitting"
  :positive-button-props="{ type: isDanger ? 'error' : 'primary', loading: submitting }"
  :mask-closable="false" :close-on-esc="false"
  @positive-click="handleConfirm" @negative-click="requestClose"
>
  <n-space vertical>
    <n-alert :type="isDanger ? 'error' : 'warning'" :show-icon="true">
      {{ impactText }}
    </n-alert>
  </n-space>
</n-modal>`,
    rules: [
      'preset="dialog" 依赖 Naive 内置的 positive-button loading/disabled 联动，改成 card 会丢掉该能力',
      '危险操作通过 :positive-button-props 传 type:"error"，不要自己拼按钮',
      '文案必须说明具体后果与影响范围，不写「是否确认」',
      '禁止触发原生 confirm()，统一走 n-modal / useDialog',
    ],
    references: [
      'components/reason-library/RiskConfirmModal.vue',
      'pages/talent/TalentPool.vue:262',
      'pages/resume/SpecialApproval.vue:66',
    ],
  },

  // ══════════════════════ 3. 输入（表单）模板 ══════════════════════
  {
    key: 'form-standard',
    category: 'entry',
    name: '标准表单区块',
    summary: '字段的标准排布：label 在上、控件在下、说明文字用统一类，支持 1–2 列自适应栅格。',
    code: `<n-form ref="formRef" :model="form" :rules="rules"
         label-placement="top" size="medium">
  <!-- 单列 -->
  <n-form-item label="名称" path="name">
    <n-input v-model:value="form.name" placeholder="请输入名称" />
    <p class="field-hint">用于列表展示与搜索匹配</p>
  </n-form-item>

  <!-- 双列：优先 .grid-auto 自适应，禁硬编码列数 -->
  <div class="grid-auto">
    <n-form-item label="类型" path="type">
      <n-select v-model:value="form.type" :options="typeOptions" clearable />
    </n-form-item>
    <n-form-item label="生效日期" path="date">
      <n-date-picker v-model:formatted-value="form.date" value-format="yyyy-MM-dd"
                     type="date" clearable style="width: 100%" />
    </n-form-item>
  </div>
</n-form>`,
    rules: [
      'label-placement 全站收敛为 top；确需左排布的独立配置页，label-width 统一 180px',
      '说明文字统一用 .field-hint（色值 --ink-soft），禁私建 switch-tip / input-tip 等 19 种命名',
      '同语义字段必须同控件：枚举一律 n-select、日期一律 n-date-picker',
      '多选必须加 max-tag-count，避免标签撑破弹窗',
      '校验三件套齐全：n-form 上 :model + :rules，n-form-item 上 path，提交前 formRef.validate()',
      '双列布局用 .grid-auto（auto-fit + minmax），禁 n-grid :cols="2" 硬编码（窄屏不折叠）',
      '禁 n-row / n-col（全站 0 使用，勿引入新写法）',
    ],
    references: [
      'pages/settings/CompanyBrand.vue',
      'pages/settings/permission/RoleEditModal.vue',
    ],
  },

  // ══════════════════════ 4. 输入（配置项）模板 ══════════════════════
  {
    key: 'config-page',
    category: 'entry',
    name: '配置项页面',
    summary: '以分组卡片承载配置项，配脏检查与统一保存栏，保存前给出明确反馈。',
    code: `<div class="page-container">
  <!-- 模型 B：header 必须是 page-body 的兄弟节点 -->
  <div class="page-header">
    <div>
      <h1 class="page-title">{{ t('title') }}</h1>
      <p class="page-subtitle">{{ t('subtitle') }}</p>
    </div>
    <div class="page-header-actions">
      <n-button size="small" @click="onReset">重置</n-button>
      <n-button type="primary" class="gradient-btn" size="small"
                :loading="saving" :disabled="!isDirty" @click="onSave">保存</n-button>
    </div>
  </div>

  <div class="page-body">
    <section v-for="g in groups" :key="g.key" class="glass-panel glass-panel--card">
      <div class="glass-panel__title">
        <span>{{ t(g.titleKey) }}</span>
        <n-tag v-if="g.badge" type="info" size="small">{{ t(g.badge) }}</n-tag>
      </div>
      <div class="glass-panel__body">
        <n-form :model="form" label-placement="top" size="small">
          <n-form-item v-for="f in g.fields" :key="f.key" :label="t(f.labelKey)" :path="f.key">
            <component :is="f.widget" v-bind="f.props" v-model="form[f.key]" />
            <p v-if="f.hintKey" class="field-hint">{{ t(f.hintKey) }}</p>
          </n-form-item>
        </n-form>
      </div>
    </section>
  </div>
</div>`,
    rules: [
      '保存交互三选一，全站不混用：统一保存按钮 / watch 自动保存（须有保存状态提示）/ switch 即时保存',
      '必须实现脏检查 isDirty，未改动时保存按钮 disabled',
      '「恢复默认」等破坏性操作必须二次确认 —— 尤其影响全局状态（品牌色走 store，跨用户共享）的操作',
      '离开路由前需脏检查拦截（onBeforeRouteLeave），否则左侧菜单一切换编辑即丢',
      '控件 size 全站收敛为 small',
      '分组用 glass-panel--card + glass-panel__title，禁各页私建 pane-caption 之类',
      '可切换预览型页面用 .content-shell 收束超宽内容',
    ],
    references: [
      'pages/settings/DemandConfig.vue（统一保存范本）',
      'pages/settings/CandidateInfoTable.vue',
      'pages/settings/ThemeSettings.vue（三段式 section）',
    ],
    caveats: ['自动保存型页面须在页内显示「保存中/已自动保存/未保存」三态提示，不发 message 弹窗打断'],
  },

  // ══════════════════════ 5. 导航（组件契约）模板 ══════════════════════
  {
    key: 'component-contracts',
    category: 'nav',
    name: '可复用组件与 composable 契约',
    summary: '组件层必须接入 glass.css 全局类体系；通用逻辑下沉到 composable，禁止在页面内重复实现。分页组件（useTablePagination）为全站唯一分页模板。',
    code: `// composables/useTableColumns.ts —— 列对齐与操作列规格的唯一真源
import { column, columns, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'
import type { ColumnAlignTier, ColumnInput } from '@/composables/useTableColumns'

// composables/useTablePagination.ts —— 分页统一入口
import { localPagination, remotePagination, TABLE_PAGE_SIZE } from '@/composables/useTablePagination'

// composables/useCloseGuard.ts —— 弹窗脏数据关闭守卫（15 处已复用）
import { useCloseGuard } from '@/composables/useCloseGuard'`,
    rules: [
      '🔴 分页组件 = useTablePagination，是全站唯一分页模板（兵哥 2026-10-18 16:00 指定）：外观固定「共 N 条 │ ‹ 1 2 3 › │ 20 / 页 ▾ │ 跳至 [__]」',
      '🔴 页面内禁出现 { pageSize: N } 字面量、自造 prefix、或直接给 n-data-table 传 pagination 对象；一律 import localPagination / remotePagination',
      'naive 远程分页用 itemCount（非 total）表达总数，remotePagination 已对齐；切页在 onPageChange 里重新拉取',
      '组件内禁止自建 .toolbar / .table-wrap / .glass-panel 同名样式，一律用全局类',
      '已定型 composable：useTableColumns（28 页）、useTablePagination（24 页 · 系统唯一）、useCloseGuard（15 页）',
      '单页专用逻辑应下沉为 composable（如草稿、脏检查），禁多页各写各的',
      '通用组件放 components/common/ 且不耦合业务 API；业务组件留在域目录',
      '组件的 props 类型必须导出，供调用方类型标注',
      '新组件必须实现 loading / empty / disabled 三态（AGENTS.md R-104、R-111）',
      '状态展示优先复用 components/common/StateView.vue（七态统一状态机）',
    ],
    references: [
      'composables/useTableColumns.ts',
      'composables/useTablePagination.ts（分页统一模板唯一真源）',
      'composables/useCloseGuard.ts',
      'components/common/StateView.vue（loading/empty/error/partial/no-permission/offline/limit）',
      'ui-templates/demos/ComponentDemo.vue（分页本地/远程双形态活演示）',
    ],
    caveats: ['StateView 目前硬编码中文且不接受 t() 注入，接入前需先改造'],
  },

  // ══════════════════════ 6. 基础（按钮）模板 ══════════════════════
  {
    key: 'button-states',
    category: 'base',
    name: '按钮 4 类 6 态',
    summary: '主/次/幽灵/危险 4 类 × 默认/悬浮/激活/聚焦/加载/失效 6 态。仅幽灵按钮默认态无背景，其余三类均为实色底；纯色、无阴影、无边框，图标与文字间距固定 4px。',
    code: `<!-- 4 类按钮：统一基于 quaternary 基底 + .stpl-btn--* 皮肤类 -->
<n-button class="stpl-btn stpl-btn--primary" quaternary type="primary">
  <template #icon><n-icon :component="AddOutline" /></template>新建角色
</n-button>
<n-button class="stpl-btn stpl-btn--default" quaternary>取消</n-button>
<n-button class="stpl-btn stpl-btn--ghost" quaternary>刷新</n-button>
<n-button class="stpl-btn stpl-btn--danger" quaternary type="error">
  <template #icon><n-icon :component="TrashOutline" /></template>删除
</n-button>

/* 🔴 皮肤（落地见 templates/button-skin.css）：
 * 必须同时钉死 --n-color*，否则 naive 的 quaternary inline style 会盖掉 class 里的背景色
 * .stpl-btn { --n-color: var(--stpl-inset-bg); --n-icon-margin: var(--space-1); border:none; box-shadow:none }
 * .stpl-btn--primary { --n-color: var(--brand-button); color: var(--on-brand) }  主：每区仅一个
 * .stpl-btn--default { --n-color: var(--stpl-inset-bg); color: var(--ink) }       次：取消/返回
 * .stpl-btn--ghost   { --n-color: transparent;      color: var(--ink-soft) }     幽灵：🔴唯一默认无底
 * .stpl-btn--danger  { --n-color: var(--c-error);   color: var(--on-brand) }      危险：破坏性操作
 * .stpl-btn--danger-text { --n-color: transparent; color: var(--c-error-deep) }   行内删除（危险类紧凑变体）
 * .stpl-btn:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px } 焦点环统一
 *
 * 🔴 使用前提：组件根节点必须挂 .stpl-root —— 皮肤令牌定义在其上，
 * 漏挂会导致 var(--stpl-inset-bg) 解析失败、按钮底色消失 */`,
    rules: [
      '概念是「4 类 6 态」：类 = 主/次/幽灵/危险；态 = 默认/悬浮/激活/聚焦/加载/失效。每类都必须实现全部 6 态',
      '🔴 仅幽灵按钮默认态无背景（透明底）；主/次/危险三类默认态必须是实色底 —— 缺一层底色会让按钮在浅底上「消失」',
      '主按钮唯一性：同一工具栏/弹窗 footer 只放一个主按钮，其余降级为次/幽灵，避免多主争抢',
      '主按钮用规范令牌 --brand-button（R-210 禁锁 --brand），hover/pressed 用既有 --brand-hover / --brand-pressed，禁自造 color-mix',
      '危险操作按钮保留 type="error" —— 危险色是安全信号，不允许改成中性色或降级为幽灵按钮',
      '焦点态必须可见：naive 默认 focus 只换文字色、看不出焦点位置，统一补 outline: 2px solid var(--brand) + outline-offset: 2px',
      '表格行内操作用幽灵 + danger-text（危险类的紧凑变体，无底红字），不用实色块，保持行内扫读',
      '异步提交必须 loading + disabled 同时出现，只转圈不禁用会被重复点击',
      '尺寸四档：行内操作 xs / 工具条 sm / 主 CTA md / 页眉 lg；用 .stpl-btn--xs|sm|md|lg 修饰，不依赖 naive size prop，保证与皮肤类共存',
      '图标与文字间距固定 4px（--n-icon-margin: var(--space-1)），不随按钮尺寸变化',
      '同组按钮要么全有 icon 要么全无；操作列 size 一律引用 OP_ACTION_BUTTON_SIZE',
      '按钮基于 quaternary 基底（不渲染 __border），避开 .settings-scroll 全局渐变注入规则',
      '🔴 6 态必须能在同一屏并排对比：hover/active/focus 是交互伪类，同一时刻只有一个按钮能进入 → 模板中心用 .stpl-btn--force-{hover|active|focus|loading|disabled} 把伪类固化成类做实拍矩阵',
      '🔴 .stpl-btn--force-* 仅供模板中心演示与设计走查，业务页面禁止挂（业务靠真实交互触发伪类）',
    ],
    references: [
      'ui-templates/templates/button-skin.css（4 类 6 态皮肤唯一载体 + 强制态类）',
      'ui-templates/demos/ButtonDemo.vue（六态矩阵实拍 + 五个场景化 mock）',
      'docs/04-ui/frontend-layout-standard.md §1.8.1/§1.10（同组 icon 一致性 · 皮肤规范）',
      'composables/useTableColumns.ts（OP_ACTION_BUTTON_SIZE 唯一真源）',
    ],
    caveats: [
      '行内删除用 danger-text（无底红字）而非 danger（实色红底）：表格行内实色块会严重干扰扫读；它是危险按钮的紧凑变体，不是第 5 类',
      'naive 以 inline style 注入 --n-color / --n-text-color，优先级高于 class 选择器：不显式钉死这些变量，自定义背景会被静默盖掉',
      '皮肤令牌（--stpl-inset-bg 等）定义在 .stpl-root 上，组件根节点必须挂 .stpl-root，否则 var() 解析失败导致底色消失',
    ],
  },

  // ══════════════════════ 7. 规范（活演示） ══════════════════════
  {
    key: 'rules-playground',
    category: 'spec',
    name: '规则标准活演示',
    summary: '把全站硬规则做成可操作的实物：列对齐四档、弹窗宽度 4 档、8px 间距体系、按钮六态、语义令牌——改 Demo 里的值就等于违反规则，可用来对照排查。',
    code: `// 规则引用速查：写页面时这些就是「规则的入口」
// 1. 列对齐    → import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'
// 2. 分页      → import { localPagination, remotePagination } from '@/composables/useTablePagination'
// 3. 关闭守卫  → import { useCloseGuard } from '@/composables/useCloseGuard'
// 4. 结构类    → .panel-shell / .toolbar / .table-wrap / .grid-auto / .field-hint / .drawer-footer（glass.css 全局）
// 5. 筛选宽    → .rule-filter-search(240px) / .rule-filter-select(136px)
// 6. 间距      → var(--space-1/2/3/4/6) = 4/8/12/16/24px，只用 8 的倍数
// 7. 颜色      → var(--brand*) / var(--ink*) / var(--c-success|warning|error|info)，禁硬编码 hex
// 8. 弹窗宽度  → 420 / 520 / 640 / 960px + max-width:92vw，其它值不允许`,
    rules: [
      '间距：所有 margin/padding/gap 用 8 的整数倍（--space-2=8 / --space-4=16 / --space-6=24）',
      '颜色：一律语义令牌，禁硬编码 hex；禁 var(--x, #hex) 兜底写法（暗色回落浅色必崩）',
      '列对齐：column(col, tier) 四档，禁手写 align；长文本 text 档左对齐，禁居中',
      '弹窗宽度：只用 420/520/640/960 四档 + max-width:92vw；存量 40 个无 max-width 弹窗随迭代补齐',
      '按钮六态：交互组件必须实现 default/hover/active/focus-visible/loading/disabled；异步提交 loading 期间 disabled',
      '同组按钮要么全有 icon 要么全无；危险操作删除红 type="error" 是安全信号，不许去掉',
      '空态双态：数据视图必须区分「暂无数据」与「筛选无结果」',
      '多选控件必须加 max-tag-count，禁 n-grid :cols 硬编码列数、禁 n-row/n-col',
      '破坏性操作按 R-106 分级：可逆直接执行、中等 Toast 撤销、高危确认框；禁一律 confirm 弹窗',
    ],
    references: [
      'styles/glass.css（全局类与令牌定义）',
      'docs/04-ui/frontend-layout-standard.md（规范全文）',
      'AGENTS.md（机器约束，RFC 2119）',
      'composables/useTableColumns.ts（列对齐唯一真源）',
    ],
    caveats: ['本模板的 Demo 即规则本身：Demo 里的每个控件都按规则渲染，可直接对照自己的页面排查偏差'],
  },
];

/** 按分类取模板 */
export function templatesByCategory(cat: TemplateCategory): TemplateMeta[] {
  return TEMPLATES.filter(t => t.category === cat);
}

/** 取单个模板 */
export function getTemplate(key: string): TemplateMeta | undefined {
  return TEMPLATES.find(t => t.key === key);
}
