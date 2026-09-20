<template>
  <n-modal
    :show="show"
    preset="card"
    :title="title"
    style="max-width: 440px"
    :mask-closable="false"
    :bordered="false"
    :segmented="{ content: 'soft', footer: 'soft' }"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <n-alert :type="alertType" :show-icon="true" style="margin-bottom: 12px;">
      {{ message }}
    </n-alert>

    <div v-if="rule" class="rl-delete-detail">
      <p class="rl-delete-name">
        <b>{{ rule.name }}</b>
        <n-tag v-if="rule.isSystem" size="tiny" type="warning" bordered style="margin-left: 8px;">
          {{ t('reasonLibrary.rules.col.systemBadge') }}
        </n-tag>
      </p>
      <p v-if="rule.sceneCount > 0" class="rl-delete-refs">
        {{ t('reasonLibrary.rules.delete.refTitle').replace('N', String(rule.sceneCount)) }}
      </p>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button @click="emit('update:show', false)">{{ t('reasonLibrary.common.cancel') }}</n-button>
        <n-button type="error" :loading="deleting" @click="handleConfirm">
          {{ t('reasonLibrary.common.delete') }}
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * ReasonRuleDeleteConfirm (T-17)
 * - 系统预置规则 (Q-A3): 仅二次确认 (text 警告)
 * - 自定义规则: 直接弹确认, message 简短
 * - 有场景引用的: 不可删 (UI 提示但允许 UI 弹这个 modal — 父组件 disabled delete btn
 *   但仍保留删除流以便测试覆盖; modal 内显示场景数)
 *
 * 实际上层 (rules.vue) 已在 delete 按钮处按 isSystem/sceneCount 拦截, 这里只负责确认弹窗。
 */
import { computed } from 'vue'
import { NModal, NAlert, NTag, NButton, NSpace } from 'naive-ui'
import type { SceneRuleListItem } from '../../types/reason-library'
import { t } from '../../locales/zh-CN'

const props = defineProps<{
  show: boolean
  rule: SceneRuleListItem | null
  deleting?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'confirm'): void
}>()

const title = computed(() => {
  if (!props.rule) return t('reasonLibrary.common.confirmDelete')
  if (props.rule.isSystem) return t('reasonLibrary.rules.delete.systemTitle')
  return t('reasonLibrary.rules.delete.confirm')
})

const message = computed(() => {
  if (!props.rule) return ''
  if (props.rule.isSystem) {
    return t('reasonLibrary.rules.delete.confirmSystem')
  }
  return t('reasonLibrary.rules.delete.confirm')
})

const alertType = computed<'warning' | 'error'>(() => {
  if (!props.rule) return 'warning'
  return props.rule.isSystem ? 'warning' : 'error'
})

function handleConfirm() {
  emit('confirm')
}
</script>

<style scoped>
.rl-delete-detail {
  padding: var(--space-2) 0;
}
.rl-delete-name {
  margin: 0 0 var(--space-2);
  font-size: var(--fs-14);
  color: var(--ink);
}
.rl-delete-name b { font-weight: 600; }
.rl-delete-refs {
  margin: 0;
  font-size: var(--fs-12);
  color: var(--c-warning-deep);
}
</style>
