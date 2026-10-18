<template>
  <div
    class="module-card"
    :class="{ disabled: disabled }"
  >
    <!-- 头部：模块名 + 职责说明 + 模块禁用说明 -->
    <div class="card-head">
      <div class="card-title-row">
        <span class="card-title">{{ label }}</span>
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
      <p class="card-desc">{{ desc }}</p>
      <p v-if="hasOrphaned" class="orphan-hint">
        {{ t('dataperm.drift.orphanedHint') }}
      </p>
    </div>

    <!-- 段① 看得见什么（读范围）—— 三选一互斥 -->
    <div class="perm-segment">
      <span class="seg-label">{{ t('dataperm.read.title') }}</span>
      <!-- 🔴 'unset'（未配置）**不能只靠 n-radio-group 表达**：
             三个 n-radio-button（none/all/scope）里没有 unset 这一档，
             绑定 'unset' 时三个按钮全不亮 -> 管理员看到的是"这卡什么都没选"，
             像加载失败，而不像一个明确的"未配置"状态。故单独渲染一张虚线卡。 -->
      <div v-if="module.mode === 'unset'" class="unset-panel">
        <div class="unset-head">
          <span class="unset-tag">{{ t('dataperm.mode.unset') }}</span>
          <span class="unset-hint">
            {{ t('dataperm.card.unset.hint', { scope: defaultScopeLabel }) }}
          </span>
        </div>
        <!-- 未授予功能权限的模块仍允许进入编辑（见 cardDisabled 的 unset 例外）：
             否则「未配置 + 未授予」叠加会让管理员连配置入口都点不到，权限被锁死。 -->
        <n-button
          size="small"
          secondary
          type="primary"
          :disabled="!canConfigure"
          @click="emit('start-configure')"
        >
          {{ t('dataperm.card.unset.start') }}
        </n-button>
      </div>
      <n-radio-group
        v-else
        :value="module.mode"
        :disabled="disabled"
        class="mode-group"
        @update:value="(v: DataPermMode) => emit('update:mode', v)"
      >
        <n-radio-button value="none">{{ t('dataperm.mode.none') }}</n-radio-button>
        <n-radio-button value="all">{{ t('dataperm.mode.all') }}</n-radio-button>
        <n-radio-button value="scope">{{ t('dataperm.mode.scope') }}</n-radio-button>
      </n-radio-group>
      <!-- T09（§10.1 D8）：模块级数据范围与角色级默认范围是两套独立设置，不合并 -->
      <p class="scope-note">{{ t('dataperm.card.scopeNote') }}</p>
    </div>

    <!-- 规则摘要区：仅 scope 模式展开 -->
    <div v-if="module.mode === 'scope'" class="rule-summary">
      <n-alert
        v-if="error"
        type="error"
        :bordered="false"
        class="inline-error"
      >
        {{ error }}
      </n-alert>

      <template v-else>
        <div class="summary-line">
          <n-text depth="3" class="summary-text">
            <template v-if="totalConditions === 0">
              {{ t('dataperm.card.summary.empty') }}
            </template>
            <template v-else>
              {{ previewText }}
            </template>
          </n-text>
          <n-tag v-if="module.mode === 'scope'" size="small" :bordered="false" type="warning" class="narrow-tag">
            {{ t('dataperm.read.narrowed') }}
          </n-tag>
        </div>
        <div class="summary-actions">
          <n-tag v-if="totalConditions > 0" size="small" :bordered="false" type="info" class="count-badge">
            {{ t('dataperm.card.ruleCount', { n: module.groups.length }) }}
          </n-tag>
          <n-button
            size="small"
            secondary
            type="primary"
            :disabled="disabled || !canConfig"
            @click="emit('open-rule')"
          >
            {{ t('dataperm.card.configRule') }}
          </n-button>
        </div>
      </template>
    </div>
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
 * props.module 直接是 useRoleDataPerm.draft 中的响应式元素（引用），
 * 切模式通过 emit('update:mode') 由弹窗调用 composable.setMode 处理（保持语义单一来源）。
 * disabled 时整卡置灰（超管 / 功能权限未分配），disabledReason 显示原因。
 */
import { computed, ref } from 'vue'
import {
  NRadioGroup, NRadioButton, NButton, NTag, NText, NAlert,
} from 'naive-ui'
import type { TemplateDrift } from '@/api/data-permission'
import {
  previewOf, type DataPermMode, type ModulePerm,
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
}>()

const emit = defineEmits<{
  (e: 'update:mode', v: DataPermMode): void
  (e: 'open-rule'): void
  /** 从「未配置」态点「开始配置」：进入编辑态（父组件负责切mode 为 scope） */
  (e: 'start-configure'): void
  /** 升级某个漂移条件组到模板最新版（父组件负责重绑定并替换草稿组） */
  (e: 'upgrade-template', d: TemplateDrift): void
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

const previewText = computed(() => previewOf(props.module))

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
/* 2026-10-11 暗色修复：背景原为硬编码 #fff。
   文字令牌（--ink / --ink-soft）在 body.dark 下已反转为浅色，浅色字压在白底上
   对比度约 1.3:1，几乎不可读（截图里"招聘需求 / 控制…可见范围"全糊）。
   改用 --surface：浅色下恒为 #FFFFFF，与原值一致（浅色零变化）；
   深色下为 #1E293B，正好比弹窗底 --surface-elevated(#0F172A) 抬高一档，
   与 --ink-soft(#AEB8CC) 对比度 7.3:1，达 WCAG AA。 */
.module-card {
  background: var(--surface);
  border: 1px solid var(--border-hairline, #e2e8f0);
  border-radius: 12px;
  padding: 16px;
  box-shadow: var(--shadow-xs);
  transition: box-shadow var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out);
}
.module-card:hover { box-shadow: var(--shadow-sm); }
/* 置灰改用透明度表达：底色与可用态保持一致。原先的 --g1 在深色下是 #0B1220，
   比卡片底更暗，会被读成"凹陷"而非"禁用"。 */
.module-card.disabled { opacity: 0.6; }

.card-head { margin-bottom: 8px; }
.card-title-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.card-title { font-size: 15px; font-weight: 700; color: var(--ink, #1e293b); }
.lock-tag { font-weight: 600; }
/* 模板状态偏差标记：与 lock-tag 同级，靠文字+颜色双通道表达 */
.drift-tag { font-weight: 600; max-width: 100%; }
.orphan-hint {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--c-error-deep, #b91c1c);
}
.card-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--ink-soft, #64748b);
  line-height: 1.5;
}

/* ===== 分段标签（读范围独立成段，视觉分层）===== */
.perm-segment { display: flex; flex-direction: column; gap: 6px; }
.seg-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-soft, #64748b);
  letter-spacing: 0.02em;
}
.mode-group { width: 100%; }

/* ===== 「未配置」显式卡（卡 1.2）=====
   虚线而非实线：视觉上与"已配置"的三选一分段区明确区分，
   避免管理员把"没配过"误读成"配了但没选"。
   背景沿用 --surface 系列令牌以兼容深色模式，不硬编码 #fff（参见 .module-card 暗色修复注释）。 */
.unset-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border: 1px dashed var(--border-hairline, #e2e8f0);
  border-radius: 8px;
  background: var(--surface-elevated, #f8fafc);
}
.unset-head { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.unset-tag { font-size: 13px; font-weight: 600; color: var(--ink, #1e293b); }
.unset-hint {
  font-size: 12px;
  line-height: 1.5;
  color: var(--ink-soft, #64748b);
}

.rule-summary {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--border-hairline, #e2e8f0);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.inline-error { margin: 0; }
.summary-line { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
/* 「已收窄」徽标：mode=scope 即权限被收紧，warning 色（--c-warning-deep 对白底 7.09:1） */
.narrow-tag { font-weight: 600; }
.summary-text {
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}
.summary-actions { display: flex; align-items: center; gap: 8px; }
.count-badge { font-weight: 600; }
.scope-note {
  margin: 6px 0 0;
  font-size: var(--fs-12, 12px);
  line-height: 1.5;
  color: var(--ink-faint);
}
</style>
