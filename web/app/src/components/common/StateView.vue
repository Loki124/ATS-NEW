<template>
  <!--
    StateView —— 统一数据视图状态机（覆盖 AGENTS.md R-104 异步四态 / R-111 数据视图状态机）
    使用：父组件按 state 渲染本组件（state !== 'data' 时显示），否则渲染真实数据。
    状态：loading | empty | error | partial | no-permission | offline | limit
    部分失败(partial)为最高频遗漏项：成功项正常展示，失败项就地提供重试入口。
  -->
  <div class="state-view" :class="`state-view--${state}`">
    <n-spin v-if="state === 'loading'" size="large" />

    <n-empty
      v-else-if="state === 'empty'"
      :description="emptyText"
      size="large"
    >
      <template v-if="$slots.emptyExtra" #extra>
        <slot name="emptyExtra" />
      </template>
    </n-empty>

    <n-result
      v-else-if="state === 'error'"
      status="error"
      :title="errorTitle"
      :description="errorDescription || '加载失败，请稍后重试'"
    >
      <template v-if="onRetry" #footer>
        <n-button type="primary" @click="onRetry">重新加载</n-button>
      </template>
    </n-result>

    <n-result
      v-else-if="state === 'partial'"
      status="warning"
      title="部分内容加载失败"
      :description="partialDescription || '其余内容正常显示，可仅重试失败的部分'"
    >
      <template v-if="onRetry" #footer>
        <n-button type="primary" @click="onRetry">重试失败项</n-button>
      </template>
    </n-result>

    <n-result
      v-else-if="state === 'no-permission'"
      status="403"
      title="无权限访问"
      :description="noPermissionText || '当前账号没有查看该内容的权限'"
    />

    <n-result
      v-else-if="state === 'offline'"
      status="error"
      title="网络已断开"
      :description="offlineText || '已为你保留本地内容，恢复网络后可继续'"
    >
      <template v-if="onRetry" #footer>
        <n-button type="primary" @click="onRetry">重试</n-button>
      </template>
    </n-result>

    <n-result
      v-else-if="state === 'limit'"
      status="info"
      title="已达上限"
      :description="limitText || '当前套餐或配置已达到数量上限'"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  state: 'loading' | 'empty' | 'error' | 'partial' | 'no-permission' | 'offline' | 'limit'
  emptyText?: string
  errorTitle?: string
  errorDescription?: string
  partialDescription?: string
  noPermissionText?: string
  offlineText?: string
  limitText?: string
  onRetry?: () => void
}>()
</script>

<style scoped>
.state-view {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  padding: var(--space-8, 32px);
  width: 100%;
}
</style>
