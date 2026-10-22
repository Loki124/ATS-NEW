<template>
  <!--
    校招生管理 · 示例数据提示与切换。
    展示示例数据时必须显式告知用户（避免把示例行误当真实数据），
    并提供一键切回真实数据；生产环境不暴露切换入口。
  -->
  <n-space v-if="isMock" align="center" :size="8" class="campus-mock-bar">
    <n-tag type="warning" size="small" :bordered="false">示例数据</n-tag>
    <n-button v-if="showToggle" size="small" quaternary @click="onShowReal">看真实数据</n-button>
  </n-space>
  <n-button v-else-if="showToggle" size="small" quaternary @click="onShowMock">看示例数据</n-button>
</template>

<script setup lang="ts">
import { useCampusMock } from '../../composables/useCampusMock'

defineProps<{ isMock: boolean }>()
const emit = defineEmits<{ (e: 'change'): void }>()

const { showMock, showReal } = useCampusMock()

/** 切换入口只在开发环境暴露（生产环境不该给终端用户看「示例数据」开关）。 */
const showToggle = import.meta.env.DEV

function onShowMock() {
  showMock()
  emit('change')
}
function onShowReal() {
  showReal()
  emit('change')
}
</script>

<style scoped>
.campus-mock-bar {
  flex-shrink: 0;
}
</style>
