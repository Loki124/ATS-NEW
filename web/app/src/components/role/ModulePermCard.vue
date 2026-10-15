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

    <!-- ===== 段② 谁能改（写范围 / 操作权限）=====
         fail-closed 语义必须在 UI 显式传达，但**只在真正危险时**才报警：
         mode!=='none' 时强制展开，防止管理员漏看已生效的收紧；
         橙色告警仅当「配了范围却一个动作都没勾」才出现（=该模块对所有人只读），
         常态下不再刷屏。mode==='all' 时不渲染动作墙（全部可写无需逐项勾）。 -->
    <div class="write-section" :class="{ open: writeOpen || writeActive }">
      <div class="write-head" role="button" @click="writeOpen = !writeOpen">
        <span class="seg-label">{{ t('dataperm.write.title') }}</span>
        <n-tag size="small" :bordered="false" :type="writeBadgeType" class="write-badge">
          {{ writeBadgeText }}
        </n-tag>
        <span class="write-toggle">{{ writeOpen ? t('dataperm.write.collapse') : t('dataperm.write.expand') }}</span>
      </div>

      <template v-if="writeOpen || writeActive">
        <!-- 常驻语义提示：只在「配了写范围」时给一句总纲，具体风险由下面的 zero 告警承担 -->
        <n-alert
          v-if="writeActive && !showZeroHint"
          :type="'default'"
          :bordered="false"
          class="write-alert"
        >
          {{ t('dataperm.write.failClosedHint') }}
        </n-alert>
        <!-- 危险告警：配了写范围但 0 动作 = 该模块对所有人只读（红色，最高优先） -->
        <n-alert
          v-if="showZeroHint"
          :type="'error'"
          :bordered="false"
          class="write-alert"
        >
          {{ t('dataperm.write.zeroHint') }}
        </n-alert>
        <!-- mode=all：全部可写，无需逐项勾选动作 -->
        <n-alert
          v-if="isWriteAll"
          :type="'default'"
          :bordered="false"
          class="write-alert"
        >
          {{ t('dataperm.write.allHint') }}
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

        <!-- 动作墙：仅在 owner / scope（非 all）时渲染；按 普通/高危 分组，带全选/清空 -->
        <template v-if="showActionWall">
          <!-- 预设包：可见按钮组（替代藏在下拉里的空 placeholder），让用户知道存在预设 -->
          <div v-if="presetOptions.length" class="preset-row">
            <span class="preset-label">{{ t('dataperm.write.presetGroup') }}</span>
            <n-button
              v-for="p in presetOptions"
              :key="p.value"
              size="tiny"
              secondary
              :disabled="disabled"
              @click="onPresetPick(p.value)"
            >
              {{ p.label }}
            </n-button>
          </div>

          <n-checkbox-group
            :value="module.write?.actions || []"
            :disabled="disabled"
            @update:value="(v: Array<string | number>) => emit('update:write-actions', v.map(String))"
          >
            <!-- 常规操作组 -->
            <div v-if="normalActions.length" class="action-group">
              <div class="group-head">
                <span class="group-name">{{ t('dataperm.write.group.normal') }}</span>
                <span class="group-op">
                  <n-button size="tiny" text :disabled="disabled" @click="selectGroup(normalActions)">
                    {{ t('dataperm.write.selectAll') }}
                  </n-button>
                  <n-button size="tiny" text :disabled="disabled" @click="clearGroup(normalActions)">
                    {{ t('dataperm.write.clearAll') }}
                  </n-button>
                </span>
              </div>
              <div class="action-checks">
                <n-checkbox
                  v-for="a in normalActions"
                  :key="a.key"
                  :value="a.key"
                  class="action-check"
                >
                  {{ a.label }}
                </n-checkbox>
              </div>
            </div>

            <!-- 危险操作组（与常规视觉分层，组头常驻警示） -->
            <div v-if="destructiveActions.length" class="action-group danger-group">
              <div class="group-head">
                <span class="group-name danger-name">
                  {{ t('dataperm.write.group.destructive') }}
                  <n-tag size="tiny" :bordered="false" type="error" class="destructive-tag">
                    {{ t('dataperm.write.destructive') }}
                  </n-tag>
                </span>
                <span class="group-op">
                  <n-button size="tiny" text :disabled="disabled" @click="selectGroup(destructiveActions)">
                    {{ t('dataperm.write.selectAll') }}
                  </n-button>
                  <n-button size="tiny" text :disabled="disabled" @click="clearGroup(destructiveActions)">
                    {{ t('dataperm.write.clearAll') }}
                  </n-button>
                </span>
              </div>
              <div class="action-checks">
                <n-checkbox
                  v-for="a in destructiveActions"
                  :key="a.key"
                  :value="a.key"
                  class="action-check danger-check"
                >
                  {{ a.label }}
                </n-checkbox>
              </div>
            </div>
          </n-checkbox-group>

          <div v-if="module.write?.mode === 'scope'" class="summary-actions write-scope-actions">
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
  NCheckbox, NCheckboxGroup,
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
const isWriteAll = computed(() => (props.module.write?.mode || 'none') === 'all')

/** 写范围可勾选的动作 = 字典中启用且类别为 write/destructive 的项（view/export 归读路径，不进写范围） */
const writableActions = computed(() =>
  (props.actionRegistry || []).filter(
    (a) => a.enabled && (a.category === 'write' || a.category === 'destructive'),
  ),
)

/**
 * 动作墙按语义分两组，避免 13 个 checkbox 平铺一屏：
 *   - 常规操作（category=write）：编辑/创建/推进流程…
 *   - 危险操作（category=destructive）：合并/删除… 视觉单独成组并常驻警示
 * 🔴 分组真源是后端下发的 category，**不按动作名硬编码**（动作字典可配置、可增停用）。
 */
const normalActions = computed(() => writableActions.value.filter((a) => a.category !== 'destructive'))
const destructiveActions = computed(() => writableActions.value.filter((a) => a.category === 'destructive'))

/** 只有 owner / scope（真能收紧到动作粒度）才需要动作墙；all=全部可写、none=无需配置 */
const showActionWall = computed(() => {
  const m = props.module.write?.mode || 'none'
  return m === 'owner' || m === 'scope'
})

/** 危险态：配了写范围却一个动作都没勾 = 该模块对所有人只读（必须红色报警） */
const showZeroHint = computed(() => showActionWall.value && (props.module.write?.actions || []).length === 0)

const presetOptions = computed(() =>
  (props.presetPackages || []).map((p) => ({ label: p.label, value: p.key })),
)

/** 当前已勾选的动作集合（供分组全选/清空做差集运算） */
const selectedActions = computed(() => new Set(props.module.write?.actions || []))

/** 组内全选：把该组动作并入已勾选集合（不丢其他组已勾的） */
function selectGroup(group: ActionDictItem[]) {
  const next = new Set(selectedActions.value)
  for (const a of group) next.add(a.key)
  emit('update:write-actions', Array.from(next))
}

/** 组内清空：只移除该组动作，保留其他组已勾选 */
function clearGroup(group: ActionDictItem[]) {
  const keys = new Set(group.map((a) => a.key))
  emit('update:write-actions', Array.from(selectedActions.value).filter((k) => !keys.has(k)))
}

/** 选预设包 = 用包内动作集合整体覆盖当前勾选（再可手动微调） */
function onPresetPick(presetKey: string) {
  const preset = (props.presetPackages || []).find((p) => p.key === presetKey)
  if (preset) emit('update:write-actions', [...preset.actionKeys])
}

/**
 * 徽章三态（原来只看 actions.length，会把「配了但 0 项」显示成绿色 success = 颜色撒谎）：
 *   0 项 且已收紧 → 红 danger「未授权任何操作」（该模块对所有人只读）
 *   n 项         → 中性 default「已授权 n 项动作」
 *   全部可写      → 绿 success「全部可写」
 *   未配置        → 中性「未配置」
 */
const writeBadgeType = computed(() => {
  if (!writeActive.value) return 'default' as const
  if (isWriteAll.value) return 'success' as const
  const n = (props.module.write?.actions || []).length
  return n === 0 ? 'error' as const : 'default' as const
})
const writeBadgeText = computed(() => {
  if (!writeActive.value) return t('dataperm.write.badge.none')
  if (isWriteAll.value) return t('dataperm.write.badge.all')
  const n = (props.module.write?.actions || []).length
  return n === 0
    ? t('dataperm.write.badge.zero')
    : t('dataperm.write.badge.active', { n })
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

/* ===== 分段标签（读 / 写 两段各自回答一个问题，视觉分层）===== */
.perm-segment { display: flex; flex-direction: column; gap: 6px; }
.seg-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-soft, #64748b);
  letter-spacing: 0.02em;
}
.mode-group { width: 100%; }

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

/* ===== v2 写范围区 ===== */
.write-section {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--border-hairline, #e2e8f0);
}
.write-head {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}
.write-badge { font-weight: 600; }
.write-toggle {
  margin-left: auto;
  font-size: 12px;
  color: var(--ink-soft, #64748b);
}
.write-alert { margin: 8px 0 0; }
.write-mode-group { width: 100%; margin-top: 8px; }

/* ===== 预设包：可见按钮组（替代藏在下拉里的空 placeholder）===== */
.preset-row {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.preset-label {
  font-size: 12px;
  color: var(--ink-faint, #94a3b8);
}

/* ===== 动作墙：常规 / 危险 两组分层 ===== */
.action-group { margin-top: 8px; }
.group-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.group-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-soft, #64748b);
}
.group-name.danger-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--c-error-deep, #b91c1c);
}
.group-op { margin-left: auto; display: flex; align-items: center; gap: 2px; }

.action-checks {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  padding-left: 8px;
  border-left: 2px solid var(--border-hairline, #e2e8f0);
}
.danger-group .action-checks { border-left-color: var(--c-error, #ef4444); }
.action-check { margin: 2px 0; }
.destructive-tag { font-weight: 600; }

/* 写范围自定义条件的入口，与动作墙保持间距 */
.write-scope-actions { margin-top: 8px; }
</style>
