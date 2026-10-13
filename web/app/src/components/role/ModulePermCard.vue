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

    <!-- 三选一互斥 -->
    <n-radio-group
      :value="module.mode"
      :disabled="disabled"
      class="mode-group"
      @update:value="(v: DataPermMode) => emit('update:mode', v)"
    >
      <n-radio-button value="none">{{ t('dataperm.mode.none') }}</n-radio-button>
      <n-radio-button value="all">{{ t('dataperm.mode.all') }}</n-radio-button>
      <n-radio-button value="scope">{{ t('dataperm.mode.scope') }}</n-radio-button>
    </n-radio-group>

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

    <!-- ===== v2 写范围（操作权限）=====
         fail-closed 语义必须在 UI 显式传达：配置写范围后未勾选的动作一律拒绝。
         mode!=='none' 时强制展开，防止管理员漏看已生效的收紧。 -->
    <div class="write-section" :class="{ open: writeOpen || writeActive }">
      <div class="write-head" role="button" @click="writeOpen = !writeOpen">
        <span class="write-title">{{ t('dataperm.write.title') }}</span>
        <n-tag size="small" :bordered="false" :type="writeBadgeType" class="write-badge">
          {{ writeBadgeText }}
        </n-tag>
        <span class="write-toggle">{{ writeOpen ? t('dataperm.write.collapse') : t('dataperm.write.expand') }}</span>
      </div>

      <template v-if="writeOpen || writeActive">
        <n-alert
          :type="writeActive ? 'warning' : 'default'"
          :bordered="false"
          class="write-alert"
        >
          {{ writeActive ? t('dataperm.write.failClosedHint') : t('dataperm.write.noneHint') }}
        </n-alert>

        <n-radio-group
          :value="module.write?.mode || 'none'"
          :disabled="disabled"
          class="write-mode-group"
          @update:value="(v: WriteMode) => emit('update:write-mode', v)"
        >
          <n-radio-button value="none">{{ t('dataperm.write.mode.none') }}</n-radio-button>
          <n-radio-button value="all">{{ t('dataperm.write.mode.all') }}</n-radio-button>
          <n-radio-button value="owner">{{ t('dataperm.write.mode.owner') }}</n-radio-button>
          <n-radio-button value="scope">{{ t('dataperm.write.mode.scope') }}</n-radio-button>
        </n-radio-group>

        <template v-if="writeActive">
          <n-select
            :value="null"
            size="small"
            :placeholder="t('dataperm.write.presetPlaceholder')"
            :options="presetOptions"
            :disabled="disabled"
            class="preset-select"
            @update:value="onPresetPick"
          />
          <div class="action-checks">
            <n-checkbox-group
              :value="module.write?.actions || []"
              :disabled="disabled"
              @update:value="(v: Array<string | number>) => emit('update:write-actions', v.map(String))"
            >
              <n-checkbox
                v-for="a in writableActions"
                :key="a.key"
                :value="a.key"
                class="action-check"
              >
                {{ a.label }}
                <n-tag v-if="a.destructive" size="tiny" :bordered="false" type="error" class="destructive-tag">
                  {{ t('dataperm.write.destructive') }}
                </n-tag>
              </n-checkbox>
            </n-checkbox-group>
          </div>
          <div v-if="module.write?.mode === 'scope'" class="summary-actions">
            <n-button
              size="small"
              secondary
              type="primary"
              :disabled="disabled || !canConfig"
              @click="emit('open-write-rule')"
            >
              {{ t('dataperm.write.configScope') }}
            </n-button>
          </div>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ModulePermCard.vue — 单个业务模块的数据权限卡（抽屉内 5 张纵排）。
 *
 * props.module 直接是 useRoleDataPerm.draft 中的响应式元素（引用），
 * 切模式通过 emit('update:mode') 由抽屉调用 composable.setMode 处理（保持语义单一来源）。
 *
 * 规则摘要区（mode==='scope'）展示 previewOf(module) 可读布尔表达式 + 条件组数徽标 + 配置规则入口。
 * disabled 时整卡置灰（超管 / 功能权限未分配），disabledReason 显示原因。
 */
import { computed, ref } from 'vue'
import {
  NRadioGroup, NRadioButton, NButton, NTag, NText, NAlert,
  NSelect, NCheckbox, NCheckboxGroup,
} from 'naive-ui'
import type { TemplateDrift } from '@/api/data-permission'
import {
  previewOf, type DataPermMode, type ModulePerm, type WriteMode,
  type ActionDictItem, type ActionPreset,
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
  /** v2 可配置动作字典（options 下发；勿在前端硬编码动作清单） */
  actionRegistry?: ActionDictItem[]
  /** v2 动作预设包（一键填充 actions） */
  presetPackages?: ActionPreset[]
}>()

const emit = defineEmits<{
  (e: 'update:mode', v: DataPermMode): void
  (e: 'open-rule'): void
  /** 升级某个漂移条件组到模板最新版（父组件负责重绑定并替换草稿组） */
  (e: 'upgrade-template', d: TemplateDrift): void
  (e: 'update:write-mode', v: WriteMode): void
  (e: 'update:write-actions', v: string[]): void
  (e: 'open-write-rule'): void
}>()

/** 正在升级中的条件组下标（驱动按钮 loading），-1 表示空闲 */
const upgradingGroup = ref(-1)
defineExpose({ upgradingGroup })

// ===== v2 写范围 =====

/** 折叠状态；write 已激活（mode!=none）时视为强制展开 */
const writeOpen = ref(false)
const writeActive = computed(() => (props.module.write?.mode || 'none') !== 'none')

/** 写范围可勾选的动作 = 字典中启用且类别为 write/destructive 的项（view/export 归读路径，不进写范围） */
const writableActions = computed(() =>
  (props.actionRegistry || []).filter(
    (a) => a.enabled && (a.category === 'write' || a.category === 'destructive'),
  ),
)

const presetOptions = computed(() =>
  (props.presetPackages || []).map((p) => ({ label: p.label, value: p.key })),
)

/** 选预设包 = 用包内动作集合整体覆盖当前勾选（再可手动微调） */
function onPresetPick(presetKey: string) {
  const preset = (props.presetPackages || []).find((p) => p.key === presetKey)
  if (preset) emit('update:write-actions', [...preset.actionKeys])
}

const writeBadgeType = computed(() => (writeActive.value ? 'success' : 'default') as 'success' | 'default')
const writeBadgeText = computed(() => {
  if (!writeActive.value) return t('dataperm.write.badge.none')
  const n = (props.module.write?.actions || []).length
  return t('dataperm.write.badge.active', { n })
})

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

.card-head { margin-bottom: 12px; }
.card-title-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.card-title { font-size: 15px; font-weight: 700; color: var(--ink, #1e293b); }
.lock-tag { font-weight: 600; }
/* 模板状态偏差标记：与 lock-tag 同级，靠文字+颜色双通道表达 */
.drift-tag { font-weight: 600; max-width: 100%; }
.orphan-hint {
  margin: 6px 0 0;
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

.mode-group { width: 100%; }

.rule-summary {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-hairline, #e2e8f0);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.inline-error { margin: 0; }
.summary-line { display: flex; }
.summary-text {
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}
.summary-actions { display: flex; align-items: center; gap: 8px; }
.count-badge { font-weight: 600; }

/* ===== v2 写范围区 ===== */
.write-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-hairline, #e2e8f0);
}
.write-head {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}
.write-title { font-size: 13px; font-weight: 700; color: var(--ink, #1e293b); }
.write-badge { font-weight: 600; }
.write-toggle {
  margin-left: auto;
  font-size: 12px;
  color: var(--ink-soft, #64748b);
}
.write-alert { margin: 10px 0 0; }
.write-mode-group { width: 100%; margin-top: 10px; }
.preset-select { margin-top: 10px; max-width: 260px; }
.action-checks {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
}
.action-check { margin: 2px 0; }
.destructive-tag { margin-left: 4px; font-weight: 600; }
</style>
