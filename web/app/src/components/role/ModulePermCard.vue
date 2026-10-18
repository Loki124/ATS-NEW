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
          <!-- 语义说明 icon + hover（范式同 RuleConfigModal.hint-btn / ModuleActionCard.hint-btn）：
               内容 = 模块职责描述（desc）+ 模块级/角色级两套范围不合并提示（T09 §10.1 D8）。
               原「卡头文字描述行 + 段标签说明行」两处常驻文字收敛到这里，垂直空间减半。 -->
          <n-tooltip trigger="hover" placement="bottom-start">
            <template #trigger>
              <button type="button" class="hint-btn" :aria-label="hintAriaLabel">
                <n-icon :component="InformationCircleOutline" />
              </button>
            </template>
            <div class="mc-tip">
              <p v-if="desc" class="mc-tip-desc">{{ desc }}</p>
              <p class="mc-tip-note">{{ t('dataperm.card.scopeNote') }}</p>
            </div>
          </n-tooltip>
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

    <!-- ===== 第二行：未配置面板 / 虚线规则框（原型 .rule-container，仅 scope 展开）===== -->
    <div v-if="module.mode === 'unset'" class="mc-unset-panel">
      <div class="mc-unset-head">
        <span class="mc-unset-tag">{{ t('dataperm.mode.unset') }}</span>
        <span class="mc-unset-hint">
          {{ t('dataperm.card.unset.hint', { scope: defaultScopeLabel }) }}
        </span>
      </div>
      <!-- 未授予功能权限的模块仍允许进入编辑（见 cardDisabled 的 unset 例外）：
           否则「未配置 + 未授予」叠加会让管理员连配置入口都点不到，权限被锁死。 -->
      <button
        type="button"
        class="mc-btn-configure"
        :disabled="!canConfigure"
        @click="emit('start-configure')"
      >
        {{ t('dataperm.card.unset.start') }}
      </button>
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
 * 2026-10-18 兵哥「同排紧凑版」原型重构（替代原「卡头 + 段标签 + 规则摘要」三区式）：
 *   第一行 .mc-main-row  标题 + ⓘ(desc/scopeNote hover) + 分段选择器 + 重置（仅本卡脏时出现）
 *   第二行 .mc-rule-container（仅 scope）虚线框：条件标签链（组间「或」）+ 修改配置
 *   unset 态第二行换成虚线「未配置」面板（含当前生效的默认范围文案 + 开始配置）。
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
 * disabled 时整卡置灰（超管 / 功能权限未分配），disabledReason 显示原因。
 */
import { computed, ref } from 'vue'
import {
  NButton, NTag, NAlert,
  NTooltip, NIcon,
} from 'naive-ui'
import { InformationCircleOutline } from '@vicons/ionicons5'
import type { TemplateDrift } from '@/api/data-permission'
import {
  previewTags, type DataPermMode, type ModulePerm,
} from '@/composables/useRoleDataPerm'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  module: ModulePerm
  label: string
  desc: string
  disabled: boolean
  disabledReason?: string
  error?: string
  /** 维度选项是否可用（options 接口成功才 true），否则「配置规则」禁用 */
  canConfig: boolean
  /**
   * 角色默认数据范围的**已翻译文案**（如「全部」/「本部门」）。
   * unset 卡片必须说清"当前走的是哪个默认范围" —— 只说"未配置"会让管理员
   * 无法判断现在到底能看到多少数据，等于没解决他点开这张卡想知道的事。
   */
  defaultScopeLabel?: string
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

/** unset 卡上的默认范围文案，缺省兜底为通用说法（不给 undefined 空洞文案） */
const defaultScopeLabel = computed(() => props.defaultScopeLabel || t('dataperm.card.unset.scopeUnknown'))

/** unset 态下能否点「开始配置」：只需维度选项可用。
 *  注意**刻意不看** props.disabled —— 未授予功能权限的模块也必须能进入编辑，
 *  否则「未配置 + 未授予」叠加会把管理员锁死在配置入口之外（跨卡死锁，见 RoleEditModal.cardDisabled）。 */
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

/** ⓘ 的可访问名称：模块职责 + 两套范围不合并提示（tooltip 全文的压缩版，供读屏） */
const hintAriaLabel = computed(() =>
  props.desc ? `${props.desc} — ${t('dataperm.card.scopeNote')}` : t('dataperm.card.scopeNote'),
)

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
 *   ⓘ 次级色             → var(--ink-faint)（hover 升 --brand-fg，范式同既有 hint-btn）
 *   card 阴影            → var(--shadow-xs) / hover var(--shadow-sm)
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

/* ===== 第一行：标题 + ⓘ + 分段选择器 + 重置 ===== */
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
.mc-title {
  font-size: var(--fs-15);
  font-weight: 600;
  color: var(--ink);
  white-space: nowrap;
}
.lock-tag { font-weight: 600; }
/* 模板状态偏差标记：与 lock-tag 同级，靠文字+颜色双通道表达 */
.drift-tag { font-weight: 600; max-width: 100%; }

/* 语义说明 icon（范式对齐 RuleConfigModal.hint-btn / ModuleActionCard.hint-btn：
   button 保键盘可达 + aria-label 供读屏，hover/focus 出 tooltip） */
.hint-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--ink-faint);
  cursor: help;
  padding: 0;
  font-size: 13px;
  transition: color .15s ease, background .15s ease;
}
.hint-btn:hover,
.hint-btn:focus-visible {
  color: var(--brand-fg);
  background: var(--g1);
  outline: none;
}
.hint-btn:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 1px;
}
/* tooltip 内容：模块职责（desc）+ 两套范围不合并提示 */
.mc-tip { max-width: 320px; }
.mc-tip-desc { margin: 0 0 4px; font-size: var(--fs-12); line-height: 1.6; }
.mc-tip-note { margin: 0; font-size: var(--fs-12); line-height: 1.6; color: var(--ink-soft); }

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
