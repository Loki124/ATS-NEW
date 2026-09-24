<template>
  <!-- 2026-08-30 六改：原 n-layout(has-sider) 冗余层已删（App 主布局 n-layout-content 已包裹本组件，has-sider 在此无实际作用，sider 已是自定义 .settings-sider div）。
       改用普通 div 净减 2 层嵌套（n-layout + Naive 自动注入的 n-layout-scroll-container）。flex 布局改由 CSS .settings-layout{display:flex} 接管。 -->
  <div class="settings-layout">
    <!-- 左侧子菜单：n-menu 取代自写 menu-group（阶段 D 决策 2 配套）
         ⚠️ 不再用 n-layout-sider：它会自动把 header + menu 一起包进内部 .n-layout-scroll-container，
         导致 Naive 的 scrollbar 竖向跨整个容器、覆盖在 header 上方（用户反馈"滚动条覆盖header"）。
         改为自定义 .settings-sider（flex column），header 固定、menu 单独 overflow-y:auto，
         scrollbar 只出现在菜单区，不接触 header。 -->
    <div
      class="settings-sider glass-sidebar"
      :class="{ collapsed }"
      :style="`width: ${collapsed ? 64 : 220}px; flex-shrink: 0;`"
    >
      <div class="sider-header" :class="{ collapsed: collapsed }">
        <h2 v-if="!collapsed" class="sider-title gradient-title">{{ t('pages.settings.SettingsLayout.s1') }}</h2>
        <button
          class="collapse-btn"
          :class="{ collapsed: collapsed }"
          type="button"
          :aria-label="t('pages.settings.SettingsLayout.s2')"
          @click="collapsed = !collapsed"
        >
          <n-icon :component="collapsed ? ChevronForwardOutline : ChevronBackOutline" />
        </button>
      </div>

      <div class="settings-sider-menu">
        <n-menu
          :collapsed="collapsed"
          :collapsed-width="64"
          :collapsed-icon-size="22"
          :indent="18"
          :options="subMenuOptions"
          :value="activeKey"
          :expanded-keys="expandedKeys"
          :theme-overrides="settingsMenuThemeOverrides"
          class="settings-menu"
          @update:value="handleMenuClick"
          @update:expanded-keys="onExpandedKeysChange"
        />
      </div>
    </div>

    <!-- 右侧内容（原 n-layout-content 已降级为 div，flex:1 由 CSS 接管） -->
    <div class="settings-content">
      <div class="settings-aurora" aria-hidden="true">
        <span class="blob blob-a"></span>
        <span class="blob blob-b"></span>
        <span class="blob blob-c"></span>
      </div>
      <div class="settings-scroll">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
// ★ v1.1 补全 imports（文档 §8.2 P0-3）
import { ref, computed, watch, nextTick, h, type Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon, NMenu } from 'naive-ui'
import {
  ChevronForwardOutline, ChevronBackOutline,
  PersonCircleOutline, PersonOutline, PersonAddOutline, BusinessOutline, PeopleOutline, BookOutline, BookmarkOutline,
  ClipboardOutline, StarOutline, SchoolOutline, GitNetworkOutline, GitBranchOutline,
  StopwatchOutline, ConstructOutline, LayersOutline, InformationCircleOutline,
  CloudUploadOutline, ServerOutline, SearchOutline, AnalyticsOutline,
  ColorPaletteOutline, LocationOutline, VideocamOutline, MailOutline,
  ShieldOutline, ShieldCheckmarkOutline, LockClosedOutline, PeopleCircleOutline, OptionsOutline,
  DocumentTextOutline, FileTrayFullOutline, GridOutline, CopyOutline,
  BriefcaseOutline, CalendarOutline, GiftOutline, PricetagsOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()

// 设置侧边栏折叠状态
const collapsed = ref(false)

// ★ v1.1 修复：subMenuOptions 用 Naive UI 官方 MenuOption 类型
//   group 项：type: 'group' + 必填 children
//   叶子项：可选 icon render 函数
import type { MenuOption } from 'naive-ui'
const { t } = useI18n()
type MenuItem = MenuOption

// ★ v1.1 修复：subMenuOptions 列全 5 个分组（基本信息/过程管理/招聘提速/内容管理/其他）
//   + 每组 children 完整迁移（22 项菜单）
//   icon 渲染：保持 render 函数形式（与 Layout.vue 一致）
const subMenuOptions: MenuItem[] = [
  {
    key: 'g-basic',
    type: 'group',
    label: '基本信息',
    children: [
      { key: '/settings/account', label: '个人信息管理', icon: () => h(NIcon, null, { default: () => h(PersonCircleOutline) }) },
      {
        key: 'g-company',
        label: '公司信息管理',
        icon: () => h(NIcon, null, { default: () => h(BusinessOutline) }),
        children: [
          { key: '/settings/company', label: '公司信息', icon: () => h(NIcon, null, { default: () => h(BusinessOutline) }) },
          { key: '/settings/company/address', label: '公司地址', icon: () => h(NIcon, null, { default: () => h(LocationOutline) }) },
          { key: '/settings/company/meeting-rooms', label: '公司会议室', icon: () => h(NIcon, null, { default: () => h(VideocamOutline) }) },
          { key: '/settings/company/resume-mailbox', label: '接收简历邮箱', icon: () => h(NIcon, null, { default: () => h(MailOutline) }) },
          { key: '/settings/company/brand', label: '品牌信息管理', icon: () => h(NIcon, null, { default: () => h(ColorPaletteOutline) }) },
        ],
      },
      { key: '/settings/department', label: '组织管理', icon: () => h(NIcon, null, { default: () => h(PeopleOutline) }) },
      {
        // ★ 北森风格重构：用户管理迁移自「组织信息管理」，承载内部/外部/全部用户 + 注册审核 + 用户组
        key: 'g-user',
        label: '用户管理',
        icon: () => h(NIcon, null, { default: () => h(PeopleCircleOutline) }),
        children: [
          { key: '/settings/users/all', label: '用户管理', icon: () => h(NIcon, null, { default: () => h(PeopleCircleOutline) }) },
          { key: '/settings/registrations', label: '注册审核', icon: () => h(NIcon, null, { default: () => h(PersonAddOutline) }) },
          { key: '/settings/user-groups', label: '用户组管理', icon: () => h(NIcon, null, { default: () => h(PeopleCircleOutline) }) },
        ],
      },
      {
        // 权限管理 —— 「基本信息」下的子菜单（可展开父菜单项，无自身路由）
        // 2026-09-18 首次调整：由顶层分组归入「基本信息」分组内。
        // 2026-09-23 二次调整：原 type:'group' 会在「基本信息」内部再渲染一条独立的分组标题，
        //   视觉上与父级割裂（看起来像另一个分类而非子菜单）。去掉 type 后与同级
        //   「公司信息管理」(g-company)、「用户管理」(g-user) 完全一致：带图标的可展开父菜单项。
        //   点击仅展开子项、不导航 —— handleMenuClick 只处理以 '/' 开头的 key，
        //   因此 g-permission 不构成死链（与 g-company / g-user 同款行为）。
        // 排序：置于「基本信息」末位 —— 个人信息 → 公司信息 → 组织 → 用户 → 权限
        //   （先有组织与人，再配置权限，符合配置递进逻辑）。
        key: 'g-permission',
        label: '权限管理',
        icon: () => h(NIcon, null, { default: () => h(ShieldOutline) }),
        children: [
          { key: '/settings/permissions', label: '身份管理', icon: () => h(NIcon, null, { default: () => h(ShieldCheckmarkOutline) }) },
          { key: '/settings/permissions/resources', label: '资源管理', icon: () => h(NIcon, null, { default: () => h(GridOutline) }) },
          { key: '/settings/mou', label: '管理单元', icon: () => h(NIcon, null, { default: () => h(GitNetworkOutline) }) },
          { key: '/settings/field-acl', label: '字段权限', icon: () => h(NIcon, null, { default: () => h(LockClosedOutline) }) },
        ],
      },
    ],
  },
  {
    key: 'g-process',
    type: 'group',
    label: '过程管理',
    children: [
      {
        key: 'g-candidate-info',
        label: '候选人信息管理',
        icon: () => h(NIcon, null, { default: () => h(FileTrayFullOutline) }),
        children: [
          { key: '/settings/candidate-dynamic-fields', label: '候选人字段管理', icon: () => h(NIcon, null, { default: () => h(ConstructOutline) }) },
          { key: '/settings/standard-resume', label: '标准简历设置', icon: () => h(NIcon, null, { default: () => h(DocumentTextOutline) }) },
          { key: '/settings/application-form', label: '申请表和登记表设置', icon: () => h(NIcon, null, { default: () => h(ClipboardOutline) }) },
          { key: '/settings/candidate-info-table', label: '候选人信息表', icon: () => h(NIcon, null, { default: () => h(GridOutline) }) },
          { key: '/settings/duplicate-candidate', label: '简历查重规则', icon: () => h(NIcon, null, { default: () => h(CopyOutline) }) },
        ],
      },
      {
        // 「招聘需求管理」纯分组（key 不带路径不可点击）：原「招聘需求设置」
        // 页面降为子项「需求规则设置」，与评分规则并列
        key: 'g-demand',
        label: '招聘需求管理',
        icon: () => h(NIcon, null, { default: () => h(ClipboardOutline) }),
        children: [
          { key: '/settings/demand-dynamic-fields', label: '需求字段管理', icon: () => h(NIcon, null, { default: () => h(ConstructOutline) }) },
          { key: '/settings/demand-config', label: '需求规则设置', icon: () => h(NIcon, null, { default: () => h(ClipboardOutline) }) },
          { key: '/settings/scoring', label: '评分规则', icon: () => h(NIcon, null, { default: () => h(StarOutline) }) },
        ],
      },
      {
        // 2026-09-14 动态字段拆分：职位信息管理作为分组，容纳占位页与「动态字段」子项
        key: 'g-position-info',
        label: '职位信息管理',
        icon: () => h(NIcon, null, { default: () => h(BriefcaseOutline) }),
        children: [
          { key: '/settings/position-dynamic-fields', label: '职位字段管理', icon: () => h(NIcon, null, { default: () => h(ConstructOutline) }) },
          { key: '/settings/position-info', label: '职位信息管理', icon: () => h(NIcon, null, { default: () => h(BriefcaseOutline) }) },
        ],
      },
      { key: '/settings/interview-management', label: '面试管理', icon: () => h(NIcon, null, { default: () => h(CalendarOutline) }) },
      { key: '/settings/offer-management', label: 'Offer管理', icon: () => h(NIcon, null, { default: () => h(GiftOutline) }) },
      { key: '/settings/campus-control', label: '校招管控', icon: () => h(NIcon, null, { default: () => h(SchoolOutline) }) },
      {
        // 2026-09-14 新增：招聘分类信息，数据字典收为其子项（兵哥未列入排序清单，保留并置于末尾）
        // 2026-09-20 补充：原因库加入子项，作为原因标签 / 场景规则的配置入口
        key: '/settings/recruit-category',
        label: '招聘分类信息',
        icon: () => h(NIcon, null, { default: () => h(PricetagsOutline) }),
        children: [
          { key: '/settings/dictionary', label: '数据字典', icon: () => h(NIcon, null, { default: () => h(BookmarkOutline) }) },
          { key: '/settings/reason-library', label: '原因库', icon: () => h(NIcon, null, { default: () => h(BookmarkOutline) }) },
        ],
      },
    ],
  },
  {
    key: 'g-speedup',
    type: 'group',
    label: '招聘提速',
    children: [
      { key: '/settings/recruitment-stage', label: '招聘阶段配置', icon: () => h(NIcon, null, { default: () => h(LayersOutline) }) },
      { key: '/settings/recruitment-process', label: '招聘流程', icon: () => h(NIcon, null, { default: () => h(GitNetworkOutline) }) },
      { key: '/settings/recruitment-round', label: '面试轮次', icon: () => h(NIcon, null, { default: () => h(StopwatchOutline) }) },
    ],
  },
  {
    key: 'g-content',
    type: 'group',
    label: '内容管理',
    children: [
      { key: '/settings/announcements', label: '制度公告', icon: () => h(NIcon, null, { default: () => h(BookOutline) }) },
    ],
  },
  {
    key: 'g-misc',
    type: 'group',
    label: '其他',
    children: [
      { key: '/settings/theme', label: '主题外观', icon: () => h(NIcon, null, { default: () => h(ColorPaletteOutline) }) },
      {
        // 2026-09-18 基础数据：分为静态数据（标准码表，只读）/ 动态数据（公司库+院校库，可维护）
        key: 'g-basic-data',
        label: '基础数据',
        icon: () => h(NIcon, null, { default: () => h(ServerOutline) }),
        children: [
          { key: '/settings/code-tables', label: '静态数据', icon: () => h(NIcon, null, { default: () => h(BookmarkOutline) }) },
          { key: '/settings/dynamic-data', label: '动态数据', icon: () => h(NIcon, null, { default: () => h(PeopleCircleOutline) }) },
        ],
      },
      { key: '/settings/dynamic-fields', label: '动态字段', icon: () => h(NIcon, null, { default: () => h(ConstructOutline) }) },
      { key: '/settings/scraped-resumes', label: '我找的简历', icon: () => h(NIcon, null, { default: () => h(SearchOutline) }) },
      { key: '/settings/data-dashboard', label: '数据中心', icon: () => h(NIcon, null, { default: () => h(AnalyticsOutline) }) },
      { key: '/settings/external', label: '生态对接', icon: () => h(NIcon, null, { default: () => h(GitNetworkOutline) }) },
      { key: '/settings/public', label: '公共设置', icon: () => h(NIcon, null, { default: () => h(CloudUploadOutline) }) },
      { key: '/settings/rule-engine', label: '统一规则引擎', icon: () => h(NIcon, null, { default: () => h(OptionsOutline) }) },
    ],
  },
]

// n-menu themeOverrides（让 Naive n-menu 字色走 CSS 变量，单一来源）
const settingsMenuThemeOverrides = {
  itemTextColor: 'var(--ink-soft)',
  itemTextColorHover: 'var(--ink)',
  itemTextColorActive: 'var(--brand)',
  itemTextColorActiveHover: 'var(--brand)',
  itemIconColor: 'var(--ink-soft)',
  itemIconColorHover: 'var(--ink)',
  itemIconColorActive: 'var(--brand)',
  itemColorActive: 'var(--brand-soft)',
  itemColorActiveHover: 'var(--brand-soft)',
  borderRadius: '6px',
  groupTextColor: 'var(--ink-faint)',
}

// ★ v1.1 修复：expandCurrent 改为累计 ancestor 链（3 嵌套必须展开中间层 + 最外层 group）
//   2026-09-02：MenuOption.key 是 Key|undefined，未定义项直接跳过（保持返回类型严格）
function findPathToKey(items: MenuItem[], target: string, currentPath: Array<string | number> = []): Array<string | number> | null {
  for (const item of items) {
    if (item.key === undefined) continue
    const newPath = [...currentPath, item.key]
    if (item.key === target) return newPath
    if (item.children?.length) {
      const found = findPathToKey(item.children, target, newPath)
      if (found) return found
    }
  }
  return null
}

function expandCurrentTo(path: string) {
  const chain = findPathToKey(subMenuOptions, path)
  if (!chain) return
  // chain 是从最外层 group 到目标 key 的完整路径，剔除目标本身
  const ancestors = chain.slice(0, -1)
  const merged: Array<string | number> = [...expandedKeys.value, ...ancestors]
  expandedKeys.value = merged
}

const expandedKeys = ref<Array<string | number>>([])
function onExpandedKeysChange(keys: Array<string | number>) {
  expandedKeys.value = keys
}

// 当前路由对应的菜单 key —— 优化：computed 兜底 + optimisticKey 覆盖
const optimisticKey = ref('')
const optimisticTimer = ref<number>()

const activeKey = computed(() => {
  if (optimisticKey.value) return optimisticKey.value
  return route.path
})

watch(() => route.path, () => expandCurrentTo(route.path), { immediate: true })

function handleMenuClick(key: string) {
  if (typeof key === 'string' && key.startsWith('/')) {
    nextTick(() => { optimisticKey.value = key })
    if (optimisticTimer.value) window.clearTimeout(optimisticTimer.value)
    optimisticTimer.value = window.setTimeout(() => { optimisticKey.value = '' }, 1000)
    router.push(key)
  }
}

// 路由 commit 后清掉 optimisticKey
watch(() => route.path, () => {
  if (optimisticTimer.value) { window.clearTimeout(optimisticTimer.value); optimisticTimer.value = undefined }
  optimisticKey.value = ''
})
</script>

<style scoped>
/* 阶段 D 保留旧 CSS 兜底（下一轮删）—— 玻璃激活态覆盖：利用 settings-sider 已有 class="glass-sidebar"（glass.css 全局接管）*/
.settings-layout { display: flex; height: 100%; background: transparent; overflow: hidden; }
.settings-layout { height: 100% !important; }

/* ⚠️ 自定义 .settings-sider（取代 n-layout-sider）：
   - flex column 让 header / menu 上下分区
   - position:relative 给之后可能的 footer absolute 定位预留
   - border-right 视觉边界（与右内容分隔），圆角顶部对齐 panel */
.settings-sider {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;        /* 关键：sider 自身不滚，滚动职责下放到 .settings-sider-menu */
  position: relative;
  border-right: 1px solid var(--border-hairline);
  transition: width var(--duration-base) var(--ease-out);
}
/* 滚动区：占据 header 之外剩余高度，scrollbar 只在这里出现 */
.settings-sider-menu {
  flex: 1;
  min-height: 0;            /* flex 子项 min-height 默认 auto 会撑爆，必须 0 */
  overflow-y: auto;         /* 原生滚动，glass.css 全局 ::-webkit-scrollbar 已美化 */
  overflow-x: hidden;
  /* iOS 弹性滚动 + 桌面端丝滑 */
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;

  /* === 该元素自身的 scrollbar 显隐规则（兵哥反馈 global ::- 不够稳）===
     - 默认 thumb 完全透明（看不到滚动条，但仍在 DOM 里可滚）
     - 自身被 hover 时，thumb 呈 brand 紫（与项目其它滚条统一）
     - 直接选择器（.settings-sider-menu:hover::-webkit-scrollbar-thumb）可靠，
       不依赖 parent :hover 传递（webkit 不支持 parent:hover → 伪元素传递）
     - 颜色统一用 glass.css 的 --scrollbar-color-* 系列 token，单源 */
  scrollbar-color: transparent transparent;             /* Firefox 默认透明 */
  scrollbar-width: thin;
  transition: scrollbar-color 0.2s var(--ease-out);
}
.settings-sider-menu::-webkit-scrollbar {
  width: 5px;
  height: 5px;
  background: transparent;
  /* 关键：scrollbar 自身不接收点击。
     真实 Chromium classic scrollbar 的 rail(5px) 紧贴 n-menu 子菜单箭头，
     点击箭头时若略微偏移到 rail，浏览器触发 "jump to here" 滚动
     → 菜单内容移动几像素 → 鼠标按下/抬起落到不同元素 → n-menu click 被吞，
     表现为"折叠/展开要点好几次"。
     headless Chromium 无此 hit-test 行为，所以自动化不重现、但用户每次都遇到。
     thumb 单独恢复 pointer-events: auto 以保留拖动。 */
  pointer-events: none;
}
.settings-sider-menu::-webkit-scrollbar-thumb {
  background: transparent;                              /* webkit 默认透明 */
  border-radius: 3px;
  transition: background 0.2s var(--ease-out);
  pointer-events: auto;          /* thumb 仍可拖动（hover 显色后） */
}
.settings-sider-menu:hover {
  scrollbar-color: var(--scrollbar-color-hover) transparent;   /* Firefox 显色（统一 token） */
}
.settings-sider-menu:hover::-webkit-scrollbar-thumb {
  background: var(--scrollbar-color-hover);           /* webkit 显色（统一 token） */
}
.settings-sider-menu:hover::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-color-drag);            /* 自身 thumb hover 更深 */
}
/* 折叠态：菜单区也要保持 64px 内不溢出 */
.settings-sider.collapsed .settings-sider-menu { overflow-y: auto; }

.sider-header {
  position: sticky; top: 0; z-index: 10;
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-4) var(--space-4) var(--space-3) 20px;
  flex-shrink: 0;            /* header 不让位，永远在顶部 */
  /* ⚠️ 22:35 兵哥反馈"设置主标题作为固定头部展示，仅让标题下方列表支持滚动"：
     - position: sticky + top: 0 已实现（实测滚 367px 后 y 仍 64），但背景半透明
       rgba(255,255,255,.55) 让用户视觉上感觉'跟着滚'
     - 改用 var(--glass-bg-elevated) (.72) 更不透明，明确'固定头部'的视觉边界 */
  border-bottom: 1px solid var(--border-hairline);
  background: var(--glass-bg-elevated);
  backdrop-filter: blur(var(--glass-blur-panel));
  -webkit-backdrop-filter: blur(var(--glass-blur-panel));
}
.sider-header.collapsed { justify-content: center; padding: var(--space-4) var(--space-2) var(--space-3); }
.sider-title { margin: 0; font-size: var(--fs-16); font-weight: 600; color: var(--ink); }
.collapse-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 28px;
  border-radius: var(--radius-md);
  background: transparent; border: 1px solid transparent;
  color: var(--ink-soft); cursor: pointer; font-size: var(--fs-16);
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out);
}
.collapse-btn:hover { background: var(--brand-tint); color: var(--brand); border-color: var(--glass-border); }
.collapse-btn.collapsed { width: 32px; height: 32px; }

/* 右侧内容区 */
.settings-content {
  position: relative; padding: 0;
  overflow: hidden;
  display: flex; flex-direction: column;
  flex: 1;
  min-height: 0; height: 100%;
  background: transparent;
}
.settings-scroll {
  position: relative; z-index: 1;
  flex: 1; min-height: 0; height: 100%;
  /* ⚠️ 桌面端保持 overflow: hidden：本层只作 20px padding 包裹 + aurora 背景上下文，
     真正的滚动视口下放到各页 .page-body（单一滚动职责，防双重滚动）。
     若改回 overflow: auto 会与 .page-body 形成双重滚动。 */
  overflow: hidden;
  padding: 20px;
}
@media (max-width: 767px) {
  .settings-scroll { overflow: auto; }
}

/* === 滚动契约（布局层统一托管，根治「整页不可滚」常态化缺陷）===
   2026-09-13 复盘：实测全部 34 个设置页 scoped 样式均未实现 .page-body{overflow-y:auto}，
   而 .settings-scroll 又是 overflow:hidden，结果内容超视口即被裁切、整页冻结（兵哥反馈"做出来的页面全部不能滚动"）。
   根因：原设计让"各页自行给 .page-body 加滚动"，但该约定从未被任何页面落地，且 .page-container
   仅为 block+min-height:100%，无受限高度的 flex 列，即使某页加了 overflow 也形不成滚动视口。
   修复：布局层用 :deep() 强制 .page-container 为高度受限的 flex 列，
   .page-header(flex-shrink:0, 见 glass.css) 固定、.page-body(flex:1;overflow-y:auto) 滚动。
   → 单文件改动修好全部设置页；后续新增页面自动继承，无需逐页重复实现，杜绝回归。 */
.settings-scroll :deep(.page-container) {
  padding: 0 !important;
  min-height: 100%;
  height: 100%;
  display: flex !important;
  flex-direction: column !important;
}
.settings-scroll :deep(.page-body) {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  overflow-y: auto !important;
  /* 滚动条外观不在此重复定义：统一走 glass.css 全局 ::-webkit-scrollbar（5px / 默认透明 / hover 显品牌色），
     保持全项目单源，避免 6px vs 5px 不一致。 */
}

/* === 阶段 D 第 2 轮：旧自写 menu CSS 已删除（DOM 已被 n-menu 取代）
   仅保留 n-menu wrapper 微调（settings-menu 是 n-menu 的 class 容器）=== */
.settings-menu { padding: var(--space-2) 0 var(--space-4); }
.settings-menu.collapsed { padding: var(--space-2) 0; }

/* === 折叠态 CSS 补丁：Naive UI 自身 .menu-item-group-title 在 :collapsed=true 下未做隐藏 ===
   现象：折叠 64px 时 group label "基本信息/过程管理/招聘提速/内容管理" 被 CSS 强竖排成「基/本/信/息」单字一行
   根因：MenuOptionGroup.mjs 第 47-53 行无条件渲染 group title；cssr.mjs 第 102 行只把 .n-menu-item-content-header 设 opacity:0
   方案：display:none 强制藏 group title + children label，children 之间用 hairline 隔开，icon 居中 === */
.settings-sider.collapsed :deep(.settings-menu.n-menu--collapsed .n-menu-item-group-title),
.settings-sider.collapsed :deep(.settings-menu.n-menu--collapsed .n-menu-item-content-header),
.settings-sider.collapsed :deep(.settings-menu.n-menu--collapsed .n-menu-item-content__arrow) {
  display: none !important;
}
/* 折叠态：让 item content 整体居中（Naive UI 用 grid 三列 22px|41px|0px 把 icon 钉在第 1 列偏左，改单列 + items 居中） */
.settings-sider.collapsed :deep(.settings-menu.n-menu--collapsed .n-menu-item-content) {
  display: grid !important;
  grid-template-columns: 1fr !important;
  justify-items: center !important;
  align-items: center !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
}
.settings-sider.collapsed :deep(.settings-menu.n-menu--collapsed .n-menu-item-content__icon) {
  margin: 0 auto !important;
}
.settings-sider.collapsed :deep(.settings-menu.n-menu--collapsed .n-menu-item-group + .n-menu-item-group) {
  border-top: 1px solid var(--border-hairline);
  margin-top: var(--space-2);
  padding-top: var(--space-2);
}
.settings-sider.collapsed :deep(.settings-menu.n-menu--collapsed .n-menu-item) {
  margin-top: var(--space-1) !important;
}

</style>