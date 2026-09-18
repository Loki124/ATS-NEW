<template>
  <div class="page-container dynamic-data-library">
    <div class="page-body">
      <n-tabs v-model:value="activeTab" type="line" animated>
        <n-tab-pane name="company" tab="公司库">
          <CompanyLibrary />
        </n-tab-pane>
        <n-tab-pane name="school" tab="院校库">
          <SchoolLibrary />
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import CompanyLibrary from './CompanyLibrary.vue';
import SchoolLibrary from './SchoolLibrary.vue';

const activeTab = ref<'company' | 'school'>('company');
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
/* 中和被嵌入页的固定高度，使其在外层滚动容器内自然流式渲染
   （避免嵌套 .page-body 高度塌陷 / 双重滚动） */
.page-body :deep(.company-library),
.page-body :deep(.school-library) {
  height: auto !important;
  min-height: 0 !important;
}
.page-body :deep(.company-library > .page-body),
.page-body :deep(.school-library > .page-body) {
  flex: none !important;
  overflow: visible !important;
}
</style>
