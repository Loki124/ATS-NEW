<template>
  <n-modal
    :show="show"
    preset="dialog"
    :title="title"
    :bordered="false"
    :mask-closable="false"
    :close-on-esc="!loading"
    :positive-text="confirmText"
    :negative-text="cancelText"
    :loading="loading"
    :positive-button-props="{ type: 'error', disabled: !acknowledged || loading }"
    :negative-button-props="{ disabled: loading }"
    @update:show="onUpdateShow"
    @positive-click="onPositiveClick"
    @negative-click="onNegativeClick"
  >
    <div class="rl-risk-confirm">
      <p class="rl-risk-confirm__text">{{ riskContent }}</p>
      <n-checkbox v-model:checked="acknowledged" class="rl-risk-confirm__ack">
        {{ acknowledgeText }}
      </n-checkbox>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NModal, NCheckbox } from 'naive-ui'

const props = defineProps<{
  show: boolean
  title: string
  riskContent: string
  confirmText: string
  cancelText: string
  acknowledgeText: string
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

// 每次打开都重置勾选状态，强制「二次确认」必须重新勾选
const acknowledged = ref(false)
watch(
  () => props.show,
  (v) => {
    if (v) acknowledged.value = false
  },
)

function onUpdateShow(v: boolean) {
  if (!v) emit('cancel')
}

function onPositiveClick() {
  if (!acknowledged.value) return false
  emit('confirm')
  // 返回 false 阻止 Naive UI 自动关闭, 由父组件控制 show (含 loading 态)
  return false
}

function onNegativeClick() {
  emit('cancel')
  // 返回 false 阻止 Naive UI 自动关闭, 由父组件控制 show
  return false
}
</script>

<style scoped>
.rl-risk-confirm {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 4px;
}
.rl-risk-confirm__text {
  margin: 0;
  line-height: 1.6;
  color: var(--ink);
  font-size: 14px;
}
.rl-risk-confirm__ack {
  align-self: flex-start;
}
</style>
