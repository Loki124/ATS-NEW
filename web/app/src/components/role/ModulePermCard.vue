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
      </div>
      <p class="card-desc">{{ desc }}</p>
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
import { computed } from 'vue'
import { NRadioGroup, NRadioButton, NButton, NTag, NText, NAlert } from 'naive-ui'
import { previewOf, type DataPermMode, type ModulePerm } from '@/composables/useRoleDataPerm'
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
}>()

const emit = defineEmits<{
  (e: 'update:mode', v: DataPermMode): void
  (e: 'open-rule'): void
}>()

const totalConditions = computed(() =>
  props.module.groups.reduce((acc, g) => acc + g.conditions.length, 0),
)

const previewText = computed(() => previewOf(props.module))
</script>

<style scoped>
.module-card {
  background: #fff;
  border: 1px solid var(--border-hairline, #e2e8f0);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: all var(--duration-fast, 0.15s) ease-out;
}
.module-card:hover { box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08); }
.module-card.disabled { background: var(--g1, #f8fafc); opacity: 0.85; }

.card-head { margin-bottom: 12px; }
.card-title-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.card-title { font-size: 15px; font-weight: 700; color: var(--ink, #1e293b); }
.lock-tag { font-weight: 600; }
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
</style>
