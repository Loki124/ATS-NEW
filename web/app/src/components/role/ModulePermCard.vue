<template>
  <div
    class="module-card"
    :class="{ disabled: disabled }"
  >
    <!-- ===== 第一行：标题 + ⓘ + 分段选择器 + 重置（2026-10-18 兵哥「同排紧凑版」原型）===== -->
    <div class="mc-main-row">
      <div class="mc-left-group">
        <div class="mc-title-cluster">
          <span class="mc-title">{{ label }}</span>
          <n-tag v-if="disabledReason" size="small" :bordered="false" type="warning" class="lock-tag">
            {{ disabledReason }}
          </n-tag>
          <!-- 权限模板状态偏差：快照语义下规则照常执行，但要让管理员知道模板变了 -->
          <n-tag
            v-for="d in driftTags"
            :key="d.state + d.templateCode + d.groupIndex"
            size="small"
            :bordered="false"
            :type="d.tone"
            class="drift-tag"
          >
            {{ d.label }}
          </n-tag>
          <!-- 仅「版本落后」可一键升级：拿模板最新版重新绑定并替换该组。
               停用/已删除无法自动处理（快照仍有效但语义由管理员决定），故不给按钮。 -->
          <n-button
            v-for="d in upgradableDrifts"
            :key="'up-' + d.templateCode + d.groupIndex"
            size="tiny"
            secondary
            type="warning"
            :loading="upgradingGroup === d.groupIndex"
            @click="emit('upgrade-template', d)"
          >
            {{ t('dataperm.drift.upgradeTo', { to: d.latestVersion ?? '?' }) }}
          </n-button>
        </div>
        <!-- 分段选择器（原型 .segmented-control）：三选一互斥，选中项白底浮起。
             🔴 unset 态**不渲染**：三个按钮全不亮会被读成"加载失败"，
                由下方虚线面板显式表达"未配置 + 当前走哪个默认范围"（见 mc-unset-panel）。 -->
        <div
          v-if="module.mode !== 'unset'"
          class="mc-segmented"
          role="radiogroup"
          :aria-label="t('dataperm.read.title')"
        >
          <button
            v-for="(opt, i) in modeOptions"
            :key="opt.value"
            type="button"
            role="radio"
            class="mc-segment"
            :class="{ active: module.mode === opt.value }"
            :aria-checked="module.mode === opt.value"
            :disabled="disabled"
            @click="emit('update:mode', opt.value)"
            @keydown="onSegKeydown($event, i)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>
      <!-- 重置：仅本卡有未保存改动时出现。页级「重置」是全量还原（会丢掉其它模块的在途
           配置），单卡粒度只撤销这一张卡 —— 与原型 .btn-reset 同位置同样式。 -->
      <button
        v-if="readDirty && !disabled"
        type="button"
        class="mc-btn-reset"
        @click="emit('reset-module')"
      >
        {{ t('dataperm.action.reset') }}
      </button>
    </div>

    <!-- 模板被删的失效提示（fail-closed 常驻，独立于模式：该组权限实际已收紧） -->
    <p v-if="hasOrphaned" class="mc-orphan-hint">
      {{ t('dataperm.drift.orphanedHint') }}
    </p>

    <!-- ===== 第二行：未配置面板 / 模式固定描述 / 虚线规则框（原型 .rule-container，仅 scope 展开）===== -->
    <div v-if="module.mode === 'unset'" class="mc-unset-panel">
      <div class="mc-unset-head">
        <span class="mc-unset-tag">{{ t('dataperm.mode.unset') }}</span>
        <span class="mc-unset-hint">
          {{ t('dataperm.card.unset.hint') }}
        </span>
      </div>
      <!-- 未配置态同样允许进入编辑：数据权限与功能权限已解耦（2026-10-18 兵哥），
           不再看功能权限是否授予 —— 数据范围是独立维度，功能有无由功能权限页签单独管理。 -->
      <button
        type="button"
        class="mc-btn-configure"
        :disabled="!canConfigure"
        @click="emit('start-configure')"
      >
        {{ t('dataperm.card.unset.start') }}
      </button>
    </div>
    <!-- none/all：固定描述（2026-10-18 兵哥）。这两种模式没有可配置规则，
         但第二行不能空着 —— 与 scope 的虚线规则框同视觉同位置，各卡二行结构齐整；
         只放一句状态说明，刻意不给「修改配置」按钮（无可配内容，避免诱导点击）。 -->
    <div v-else-if="module.mode === 'none' || module.mode === 'all'" class="mc-mode-desc">
      {{ module.mode === 'none' ? t('dataperm.card.desc.none') : t('dataperm.card.desc.all') }}
    </div>
    <template v-else-if="module.mode === 'scope'">
      <!-- 校验错误替换规则框（fail-loud：不显示可能已过期的摘要） -->
      <n-alert
        v-if="error"
        type="error"
        :bordered="false"
        class="mc-inline-error"
      >
        {{ error }}
      </n-alert>
      <div v-else class="mc-rule-container">
        <div class="mc-tag-list">
          <template v-if="tagChain.length">
            <span
              v-for="(item, i) in tagChain"
              :key="i"
              :class="item.type === 'tag' ? 'mc-tag' : 'mc-tag-logic'"
            >{{ item.text }}</span>
          </template>
          <span v-else class="mc-rule-empty">{{ t('dataperm.card.summary.empty') }}</span>
          <span v-if="totalConditions > 0" class="mc-rule-count">
            {{ t('dataperm.card.ruleCount', { n: module.groups.length }) }}
          </span>
        </div>
        <!-- 类名 summary-actions 是 RoleEditModal.test.ts 的定位契约（读范围配置入口仍在），勿改 -->
        <div class="summary-actions">
          <button
            type="button"
            class="mc-btn-configure"
            :disabled="disabled || !canConfig"
            @click="emit('open-rule')"
          >
            {{ t('dataperm.card.configRule') }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * ModulePermCard.vue — 单个业务模块的**数据权限（读范围）**卡。
 *
 * 2026-10-15 读/写拆分：原「段② 谁能改（写范围/操作权限）」已整体迁出至
 * `ModuleActionCard.vue`，挂在身份编辑弹窗新增的「操作权限」页签。
 * 本组件自此只负责「看得见什么」，职责单一：
 *   - 读范围 mode 三选一（无权限 / 全部 / 指定范围）
 *   - scope 模式下的规则摘要 + 配置规则入口（RuleConfigModal）
 *   - 权限模板漂移标记 / 一键升级
 *
 * 🔴 本组件**不出现任何操作权限信息**（2026-10-16 兵哥拍板）：读写拆分后曾在此加过一条
 *    「操作权限 + 状态徽标 + 去配置」只读摘要条，拆分完成即属冗余 —— 操作权限已有独立页签，
 *    在本页复述状态只会诱导"两处都能配"的错觉，且把两个维度又混回一张卡。彻底移除。
 *
 * 2026-10-18 兵哥四轮调整（同日，按时间顺序）：
 *   ①「同排紧凑版」原型重构（替代原「卡头 + 段标签 + 规则摘要」三区式，见下方结构说明）；
 *   ② **移除模块级 ⓘ icon + hover 提示**（原 desc 与「两套范围不合并」文案）——
 *      身份不再有角色级默认数据范围，数据范围必须且仅在数据权限页签配置，
 *      卡头只留模块名，各模块的单独提示内容全部撤掉；
 *   ③ **与功能权限解耦**：卡片不再因「未分配功能权限」置灰/挂锁标签，
 *      数据范围是独立维度；功能是否存在由「功能权限」页签单独配置。
 *      故 props 不再有 desc / defaultScopeLabel，disabled 只剩超管一种来源；
 *   ④ **none/all 二行固定描述**：这两种模式无可配置规则，但第二行不能空着——
 *      补与规则框同视觉的固定描述行（无当前模块数据权限 / 可查看当前模块的全部数据），
 *      各卡二行结构齐整；刻意不给「修改配置」按钮（无可配内容，避免诱导点击）。
 *
 * 「同排紧凑版」结构：
 *   第一行 .mc-main-row  标题（min-width 统一，保证各卡分段选择器左对齐）
 *   + 分段选择器 + 重置（仅本卡脏时出现）
 *   第二行：scope → .mc-rule-container 虚线框（条件标签链 + 修改配置）；
 *   unset → 虚线「未配置」面板；none/all → .mc-mode-desc 固定描述（无可配内容故无按钮）。
 * 与原型样例的刻意差异（均因项目令牌纪律，非随意发挥）：
 *   - 间距：原型 12px 20px 卡内边距 / 12px 行距 → 收敛到 8px 基线令牌
 *     （tokens.css §8「只减不增」：--space-3 / --space-5 已由 12/20 收紧为 8/16）；
 *   - 圆角：原型 8/6/4px 混用 → 统一 --radius-sm（tokens.css §11 禁硬编码圆角）；
 *   - 颜色/字号逐项映射语义令牌（见 <style> 顶部映射表），无一处手写色值；
 *   - 原型中无对应物的状态（模板漂移标记 / 升级按钮 / 失效提示 / 校验错误）保留在原位，
 *     以行内标签 + 条件行的形式挂靠，常态（无漂移无错误）下与原型完全一致。
 *
 * props.module 直接是 useRoleDataPerm.draft 中的响应式元素（引用），
 * 切模式通过 emit('update:mode') 由弹窗调用 composable.setMode 处理（保持语义单一来源）。
 * disabled 时整卡置灰（仅超管：超管恒全量可见，无需配置），disabledReason 显示原因。
 */
import { computed, ref } from 'vue'
import {
  NButton, NTag, NAlert,
} from 'naive-ui'
import type { TemplateDrift } from '@/api/data-permission'
import {
  previewTags, type DataPermMode, type ModulePerm,
} from '@/composables/useRoleDataPerm'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  module: ModulePerm
  label: string
  disabled: boolean
  disabledReason?: string
  error?: string
  /** 维度选项是否可用（options 接口成功才 true），否则「配置规则」禁用 */
  canConfig: boolean
  /**
   * 本卡读范围是否有未保存改动（父组件按模块粒度脏检查后下发）。
   * 驱动「重置」按钮显隐：只有真改过才给撤销入口，避免每张卡常驻一个多半禁用的按钮。
   */
  readDirty?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:mode', v: DataPermMode): void
  (e: 'open-rule'): void
  /** 从「未配置」态点「开始配置」：进入编辑态（父组件负责切mode 为 scope） */
  (e: 'start-configure'): void
  /** 升级某个漂移条件组到模板最新版（父组件负责重绑定并替换草稿组） */
  (e: 'upgrade-template', d: TemplateDrift): void
  /** 重置本卡读范围为已保存版本（父组件调 composable.resetModule，只还原本模块） */
  (e: 'reset-module'): void
}>()

/** unset 态下能否点「开始配置」：只需维度选项可用。
 *  数据权限与功能权限已解耦（2026-10-18 兵哥）：不再因未授予功能权限禁用，
 *  未配置态同样可直接进入编辑。 */
const canConfigure = computed(() => props.canConfig)

/** 正在升级中的条件组下标（驱动按钮 loading），-1 表示空闲 */
const upgradingGroup = ref(-1)
defineExpose({ upgradingGroup })

const totalConditions = computed(() =>
  props.module.groups.reduce((acc, g) => acc + g.conditions.length, 0),
)

/**
 * 规则摘要标签链（原型 .tag-list）：每个**有条件**组一个标签，组间插「或」连接词。
 * 数据源是 composable.previewTags —— 与 previewOf 同口径（后端 expr_compiler 对齐），
 * 组间为自定义组合表达式时它是整句单标签，连接词不会出现，逻辑关系不会被拆错。
 */
const tagChain = computed(() => {
  const out: { type: 'tag' | 'logic'; text: string }[] = []
  previewTags(props.module).forEach((text, i) => {
    if (i > 0) out.push({ type: 'logic', text: t('dataperm.card.logicOr') })
    out.push({ type: 'tag', text })
  })
  return out
})

/** 分段选择器选项（顺序即展示顺序：无权限 / 全部 / 指定范围） */
const modeOptions = computed<{ value: DataPermMode; label: string }[]>(() => [
  { value: 'none', label: t('dataperm.mode.none') },
  { value: 'all', label: t('dataperm.mode.all') },
  { value: 'scope', label: t('dataperm.mode.scope') },
])

/**
 * 分段选择器键盘导航（ARIA radiogroup 范式）：左右 / 上下箭头移动焦点并选中。
 * 纯 div 实现没有原生 radio 的方向键行为，必须补齐 —— 否则键盘用户要 Tab 逐个穿过，
 * 与原型"分段控制器"的心智模型（一组互斥、方向键切换）不符。
 */
function onSegKeydown(e: KeyboardEvent, idx: number) {
  if (props.disabled) return
  const dir =
    e.key === 'ArrowRight' || e.key === 'ArrowDown'
      ? 1
      : e.key === 'ArrowLeft' || e.key === 'ArrowUp'
        ? -1
        : 0
  if (!dir) return
  e.preventDefault()
  const next = (idx + dir + modeOptions.value.length) % modeOptions.value.length
  const segs = (e.currentTarget as HTMLElement).parentElement?.querySelectorAll<HTMLButtonElement>('.mc-segment')
  segs?.[next]?.focus()
  emit('update:mode', modeOptions.value[next].value)
}

/**
 * 权限模板状态偏差标记。
 * 文案带模板名与版本号（不写「模板有新版本」这种无信息量的话），
 * 颜色 + 文字双通道表达，不靠颜色单独传意（R-221）。
 */
/** 是否有条件组因模板删除而失效（该组已 fail-closed，权限实际收紧） */
const hasOrphaned = computed(() =>
  (props.module.groups || []).some((g: any) => !!g?.templateRef?.orphaned),
)

/** 可一键升级的漂移：仅 outdated（其余状态无法自动处理） */
const upgradableDrifts = computed(() =>
  (props.module.templateDrifts || []).filter(
    (d) => d.state === 'outdated' && typeof d.groupIndex === 'number',
  ),
)

const driftTags = computed(() =>
  (props.module.templateDrifts || []).map((d) => {
    const name = d.templateName || d.templateCode
    if (d.state === 'outdated') {
      return {
        ...d,
        tone: 'warning' as const,
        label: t('dataperm.drift.outdated', {
          name,
          from: d.snapshotVersion ?? '?',
          to: d.latestVersion ?? '?',
        }),
      }
    }
    if (d.state === 'disabled') {
      return { ...d, tone: 'default' as const, label: t('dataperm.drift.disabled', { name }) }
    }
    return {
      ...d,
      tone: 'error' as const,
      // 说清因果：模板没了 -> 这一组条件已作废 -> 权限实际收紧了
      label: t('dataperm.drift.orphaned', { name }),
    }
  }),
)
</script>

<style scoped>
/* ============================================================================
 * 配置卡 · 「同排紧凑版」（2026-10-18 兵哥原型精确复用）
 * ----------------------------------------------------------------------------
 * 原型规格 → 本项目语义令牌映射表（颜色/字号零手写，间距/圆角按项目纪律收敛）：
 *   --bg-card(#fff)      → var(--surface)        卡面 / 分段选中项 / 修改配置钮底
 *   --bg-gray(#f9fafb)   → var(--g1)             分段槽 / 规则框 / 未配置面板 / 重置 hover
 *   --border-color       → var(--g4)             控件边界（分段槽/规则框虚线/按钮描边）
 *   --text-main(#111827) → var(--ink)            标题 / 分段 hover
 *   --text-secondary     → var(--ink-soft)       分段未选中 / 重置 / 「或」连接词
 *   --primary-color      → var(--brand-fg)       分段选中字 / 修改配置字 / hover 描边
 *   tag 蓝底/蓝字/蓝边   → var(--brand-soft) / var(--brand-fg) / var(--brand-a22)
 *   card 阴影            → var(--shadow-xs) / hover var(--shadow-sm)
 * （2026-10-18：模块级 ⓘ icon + hover 提示已按兵哥要求移除，卡头只留标题。）
 * 间距收敛（tokens.css §8 8px 基线「只减不增」）：原型 12px 20px → var(--space-3) var(--space-5)；
 *   行距 12px → var(--space-3)。控件内部微间距（分段项 4px 14px、标签 2px 8px 等）
 *   按原型比例保留 —— 它们定义控件自身比例，不属于布局边距治理范围。
 * ========================================================================= */
.module-card {
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
  padding: var(--space-3) var(--space-5);
  box-shadow: var(--shadow-xs);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  transition: box-shadow var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out);
}
.module-card:hover { box-shadow: var(--shadow-sm); }
/* 置灰改用透明度表达：底色与可用态保持一致。原先的 --g1 在深色下是 #0B1220，
   比卡片底更暗，会被读成"凹陷"而非"禁用"。 */
.module-card.disabled { opacity: 0.6; }

/* ===== 第一行：标题 + 分段选择器 + 重置 ===== */
.mc-main-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  min-height: 32px;
}
.mc-left-group {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  flex-wrap: wrap;
  min-width: 0;
}
.mc-title-cluster {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  min-width: 0;
}
/* 标题统一宽度（2026-10-18 兵哥）：最长模块名 5 个全角字符（候选人管理），
   取 min-width: 5em 让各卡标题占位一致 → 分段选择器左边缘对齐。
   后端若下发更长标签会自然撑开（不截断），不影响可用性。 */
.mc-title {
  font-size: var(--fs-15);
  font-weight: 600;
  color: var(--ink);
  white-space: nowrap;
  min-width: 5em;
}
.lock-tag { font-weight: 600; }
/* 模板状态偏差标记：与 lock-tag 同级，靠文字+颜色双通道表达 */
.drift-tag { font-weight: 600; max-width: 100%; }

/* 分段选择器（原型 .segmented-control）：灰槽 + 白底浮起选中项 */
.mc-segmented {
  display: inline-flex;
  background: var(--g1);
  padding: 2px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--g4);
  flex-shrink: 0;
}
.mc-segment {
  padding: 4px 14px;
  font-size: var(--fs-13);
  color: var(--ink-soft);
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: pointer;
  white-space: nowrap;
  font-family: inherit;
  transition: color var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out),
    box-shadow var(--dur-fast) var(--ease-out);
}
.mc-segment:hover:not(.active):not(:disabled) { color: var(--ink); }
.mc-segment.active {
  background: var(--surface);
  color: var(--brand-fg);
  font-weight: 500;
  box-shadow: var(--shadow-xs);
}
.mc-segment:disabled { cursor: not-allowed; opacity: .6; }
.mc-segment:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 1px;
}

/* 重置（原型 .btn-reset）：无底文字钮，hover 出灰底 */
.mc-btn-reset {
  background: none;
  border: 0;
  color: var(--ink-soft);
  font-size: var(--fs-13);
  font-family: inherit;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  transition: color var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out);
}
.mc-btn-reset:hover { background: var(--g1); color: var(--ink); }
.mc-btn-reset:focus-visible { outline: 2px solid var(--brand); outline-offset: 1px; }

/* ===== 模板失效提示（fail-closed 常驻，不靠 hover 隐藏）===== */
.mc-orphan-hint {
  margin: 0;
  font-size: var(--fs-12);
  line-height: 1.6;
  color: var(--c-error-deep);
}

/* ===== 第二行：虚线规则框（原型 .rule-container）===== */
.mc-rule-container {
  background: var(--g1);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  border: 1px dashed var(--g4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
/* none/all 模式固定描述（2026-10-18 兵哥）：与规则框同视觉同位置（虚线 + 灰底），
   各卡二行结构齐整；只放一句状态说明，无按钮。 */
.mc-mode-desc {
  background: var(--g1);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  border: 1px dashed var(--g4);
  font-size: var(--fs-12);
  line-height: 1.5;
  color: var(--ink-soft);
}
.mc-tag-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
/* 条件标签（原型 .tag）：品牌浅底 + 品牌字 + 品牌描边，三通道同源 */
.mc-tag {
  background: var(--brand-soft);
  color: var(--brand-fg);
  border: 1px solid var(--brand-a22);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-12);
  line-height: 1.5;
}
.mc-tag-logic {
  font-size: var(--fs-12);
  color: var(--ink-soft);
  padding: 0 2px;
}
.mc-rule-empty {
  font-size: var(--fs-12);
  color: var(--ink-faint);
}
/* 条件组计数：附在标签链尾部的次级文字（替代原 count-badge 徽标，减一件视觉元素） */
.mc-rule-count {
  font-size: var(--fs-12);
  color: var(--ink-faint);
  margin-left: 2px;
}
.summary-actions { display: flex; align-items: center; gap: var(--space-2); flex-shrink: 0; }

/* 修改配置（原型 .btn-configure）/ 开始配置：白底描边 + 品牌字 */
.mc-btn-configure {
  background: var(--surface);
  border: 1px solid var(--g4);
  color: var(--brand-fg);
  padding: 3px 10px;
  font-size: var(--fs-12);
  font-weight: 500;
  font-family: inherit;
  border-radius: var(--radius-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: border-color var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out);
}
.mc-btn-configure:hover:not(:disabled) { border-color: var(--brand-fg); background: var(--g1); }
.mc-btn-configure:disabled { cursor: not-allowed; opacity: .6; }
.mc-btn-configure:focus-visible { outline: 2px solid var(--brand); outline-offset: 1px; }

.mc-inline-error { margin: 0; }

/* ===== 「未配置」显式卡（卡 1.2）=====
   虚线而非实线：视觉上与"已配置"的分段区明确区分，
   避免管理员把"没配过"误读成"配了但没选"。 */
.mc-unset-panel {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px dashed var(--g4);
  border-radius: var(--radius-sm);
  background: var(--g1);
}
.mc-unset-head { display: flex; align-items: baseline; gap: var(--space-2); flex-wrap: wrap; }
.mc-unset-tag { font-size: var(--fs-13); font-weight: 600; color: var(--ink); }
.mc-unset-hint {
  font-size: var(--fs-12);
  line-height: 1.5;
  color: var(--ink-soft);
}
</style>
