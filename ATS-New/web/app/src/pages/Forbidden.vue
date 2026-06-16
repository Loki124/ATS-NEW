<template>
  <div class="forbidden">
    <n-result status="403" title="403" description="您没有访问该页面的权限">
      <template #footer>
        <n-button @click="$router.push('/dashboard')">返回首页</n-button>
      </template>
    </n-result>
  </div>
</template>

<script setup lang="ts">
// 403 forbidden page - 路由角色守卫拒绝时跳转到这里
</script>

<style scoped>
.forbidden {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}
</style>
