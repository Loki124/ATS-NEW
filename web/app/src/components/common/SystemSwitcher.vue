<template>
  <n-dropdown
    trigger="click"
    placement="bottom-start"
    :options="options"
    :show-arrow="false"
    :menu-props="menuProps"
    :theme-overrides="SYSTEM_SWITCHER_THEME_OVERRIDES"
    @update:show="onUpdateShow"
    @select="onSelect"
  >
    <!-- 展开态（侧栏固定 240px / 顶部横排）：系统图标 + 系统名 + 箭头 -->
    <button
      v-if="!collapsed"
      class="sys-switch"
      :class="{ 'sys-switch--open': open }"
      type="button"
      :aria-label="switchAriaLabel"
      :title="switchAriaLabel"
    >
      <NIcon :size="15" class="sys-switch__icon" aria-hidden="true">
        <component :is="currentIcon" />
      </NIcon>
      <span class="sys-switch__label">{{ systemStore.label }}</span>
      <NIcon :size="13" class="sys-switch__chevron" aria-hidden="true"><ChevronDown /></NIcon>
    </button>

    <!-- 折叠态（侧栏 64px）：单字标识 + 箭头（纵向紧凑） -->
    <button
      v-else
      class="sys-switch sys-switch--collapsed"
      :class="{ 'sys-switch--open': open }"
      type="button"
      :aria-label="switchAriaLabel"
      :title="switchAriaLabel"
    >
      <span class="sys-switch__short">{{ systemStore.meta.short }}</span>
      <NIcon :size="11" class="sys-switch__chevron" aria-hidden="true"><ChevronDown /></NIcon>
    </button>
  </n-dropdown>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NDropdown, NIcon, useMessage } from 'naive-ui'
import { ChevronDownOutline as ChevronDown } from '@vicons/ionicons5'
import { useSystemStore, RECRUIT_SYSTEMS, type RecruitSystemKey } from '../../stores/system'
import {
  buildSystemSwitcherOptions,
  SYSTEM_ICONS,
  SYSTEM_SWITCHER_THEME_OVERRIDES,
  REFERRAL_KEY,
} from '../../utils/systemSwitcher'

/**
 * SystemSwitcher — 「社会招聘 / 校园招聘」双系统切换入口
 *
 * 位置：Layout 品牌 logo 下方（side 折叠态独占一行；展开态 / top 横排在 logo 文本右侧）。
 * 状态：useSystemStore（localStorage 持久化）；Phase 1 仅切换前端上下文，
 * 数据隔离待后端 recruit_type 维度落地后接入（见 docs/02-architecture/DUAL_SYSTEM_DESIGN.md）。
 *
 * 2026-10-21 兵哥反馈「不好用 + 导致页面波动」后的改造要点：
 *  1. 选项整行自绘（图标槽 / 文字 / 右侧勾）→ 文字永远左对齐、勾永远靠右；
 *  2. 面板紧凑化（行高 32 / 字号 13 / 内边距 4 / 轻投影）→ 不再大面积遮挡下方菜单；
 *  3. 触发器补系统图标 + 箭头随开合旋转 → 一眼看出「这是系统切换」；
 *  4. 切换系统**不跳路由**（DUAL_SYSTEM_DESIGN.md D5），菜单增删的抖动由 Layout 侧淡入消化。
 */
defineProps<{ collapsed?: boolean }>()

const systemStore = useSystemStore()
const message = useMessage()
const router = useRouter()

/** 下拉是否展开（用于箭头旋转） */
const open = ref(false)

const options = computed(() => buildSystemSwitcherOptions(systemStore.current))

const currentIcon = computed(() => SYSTEM_ICONS[systemStore.current])

const switchAriaLabel = computed(() => `当前系统：${systemStore.label}，点击切换系统`)

/** 下拉菜单挂到 body（teleport），用 class 精确命中做紧凑化 */
const menuProps = () => ({ class: 'sys-switch-dropdown' })

function onUpdateShow(value: boolean) {
  open.value = value
}

function onSelect(key: string) {
  // 内推助手：跳转内推中心页，不切换招聘系统
  if (key === REFERRAL_KEY) {
    router.push(REFERRAL_KEY)
    return
  }
  if (key === systemStore.current) return
  systemStore.switchTo(key as RecruitSystemKey)
  const target = RECRUIT_SYSTEMS.find((s) => s.key === key)
  message.success(`已切换到「${target?.label}」系统`)
}
</script>

<style scoped>
.sys-switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  height: 32px;
  max-width: 100%;
  padding: 0 var(--space-2);
  /* ⚠️ 玻璃侧栏上不用 --surface（不透明白块显重），改用发丝边框表达「这是个控件」，
     悬停再叠品牌淡底 */
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink-soft);
  font-size: var(--fs-13);
  line-height: 1;
  cursor: pointer;
  user-select: none;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
}
.sys-switch:hover {
  background: var(--brand-tint);
  border-color: var(--brand-a12);
  color: var(--ink);
}
.sys-switch:focus-visible {
  outline: 2px solid var(--brand-button);
  outline-offset: 2px;
}
/* 折叠态 32px 小按钮：焦点环改为内描边 —— 外扩 2px 会形成一个 40×40 的独立方框，
   正好压在下方弹出的浮层左上角上，看着像「多了一个框」（兵哥 2026-10-22 反馈） */
.sys-switch--collapsed:focus-visible {
  outline-offset: -2px;
}
.sys-switch--open {
  background: var(--brand-tint);
  border-color: var(--brand-a12);
  color: var(--ink);
}
.sys-switch__icon {
  flex-shrink: 0;
  color: var(--brand-fg);
}
.sys-switch__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}
.sys-switch__chevron {
  flex-shrink: 0;
  opacity: 0.7;
  transition: transform var(--duration-fast) var(--ease-out);
}
.sys-switch--open .sys-switch__chevron {
  transform: rotate(180deg);
}

/* 侧栏折叠态：64px 宽度内居中，纵向单字 + 箭头 */
.sys-switch--collapsed {
  width: 32px;
  height: 32px;
  padding: 0;
  flex-direction: column;
  justify-content: center;
  gap: 0;
  font-size: var(--fs-12);
}
/* 视觉 32px，命中区扩到 44×44（R-102：图标按钮触控目标下限） */
.sys-switch--collapsed::after {
  content: '';
  position: absolute;
  inset: -6px;
}
.sys-switch--collapsed .sys-switch__short {
  font-weight: 600;
}
</style>

<!--
  下拉面板与选项行是 teleport 到 body 的内容，scoped 样式打不中，
  必须走全局样式（与 Layout.vue 里 .user-menu-dropdown 的处理方式一致）。
  ⚠️ 面板级视觉（圆角 / 阴影 / 内边距）不在这里 —— 那部分由
  glass.css §下拉弹窗规范 的紧凑型变体 `.n-dropdown-menu.sys-switch-dropdown` 统一负责
  （L2/L3 用 !important 锁了标准值，组件内覆盖会被压掉）。
  这里只放**本组件自有**的三段行结构（图标槽 / 文字 / 勾）。
-->
<style>
/* === 选项行：图标槽 / 文字 / 勾 三段固定宽度 → 文字始终左对齐、勾始终靠右 ===
   ⚠️ 本行是「自绘内容」（不走 naive 的 prefix 槽），所以**必须自带水平内边距**：
   naive 的行内容盒左右各有 4px 在行高亮块外面（见下方 .sys-opt 的注释），
   不补内边距就会让图标越出高亮块。左侧锚点基准仍由 glass.css 的
   `.n-dropdown-option { padding: 0 var(--space-3) }` 统一提供，这里只补「高亮块内侧」的量。 */
.sys-opt {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 100%;
  /* ⚠️ 2026-10-22 兵哥反馈「hover 时样式很奇怪」的根因修复：
   *   naive 的行高亮层（`.n-dropdown-option-body::before`）是 `inset: 0 4px`（在行内容盒内缩 4px），
   *   而行内容盒本身已被 `.n-dropdown-option { padding: 0 8px }` 从面板边缘内缩 8px。
   *   → 内容盒左右各有 4px 在高亮块**外面**。本行是自绘内容（不再走 naive 的 prefix 槽），
   *   图标紧贴内容盒左边缘 → 正好落进那 4px 的「沟」里 → hover 时图标看起来「跑到高亮块外面」，
   *   高亮块的左边缘还会在图标旁形成一条突兀的竖线。
   *   这里给自绘行补 8px 内边距（= --space-2）→ 内容整体落进高亮块内侧 4px，
   *   图标与右侧的勾都不再越界，与全站其它下拉的行内边距观感一致。 */
  padding: 0 var(--space-2);
  line-height: 1.4;
}
.sys-opt__icon {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: var(--ink-faint);
}
.sys-opt__text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sys-opt__check {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  color: var(--brand-fg);
}
/* 当前生效的系统：品牌色 + 加粗（勾在右侧，状态一目了然；规范 §5：激活态用 --brand） */
.sys-opt--current .sys-opt__icon,
.sys-opt--current .sys-opt__text {
  color: var(--brand-fg);
  font-weight: 600;
}
</style>
