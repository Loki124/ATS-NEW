<template>
  <div class="page-container dynamic-data-library">
    <div class="page-header">
      <h1 class="page-title">动态数据</h1>
      <p class="page-subtitle">院校库 / 专业库 / 公司库维护（用户可维护，随业务增长）</p>
    </div>

    <div class="data-body">
      <n-tabs v-model:value="activeTab" type="line" animated class="data-tabs">
        <n-tab-pane name="school" tab="院校库">
          <SchoolLibrary />
        </n-tab-pane>
        <n-tab-pane name="major" tab="专业库">
          <MajorLibrary />
        </n-tab-pane>
        <n-tab-pane name="company" tab="公司库">
          <CompanyLibrary />
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import SchoolLibrary from './SchoolLibrary.vue';
import MajorLibrary from './MajorLibrary.vue';
import CompanyLibrary from './CompanyLibrary.vue';

const activeTab = ref<'school' | 'major' | 'company'>('school');
</script>

<style scoped>
/* 「只滚数据列表行内」布局链（与 CodeTableLibrary / CampusControl 同款）：
   .page-header 固定 → .data-body 填高不滚动 → .data-tabs 撑满、tab 导航固定 →
   pane 不滚、嵌入页（院校库/专业库/公司库）填高 → 仅嵌入页表格体内部滚动。
   内层用 .data-body 而非 .page-body，规避 SettingsLayout 对 .page-body 的 overflow:auto!important 强制。 */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header { flex-shrink: 0; }
.data-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.data-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.data-tabs :deep(.n-tabs-nav) {
  background: transparent;
  flex-shrink: 0;
}
.data-tabs :deep(.n-tabs-pane-wrapper) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.data-tabs :deep(.n-tab-pane) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
/* 嵌入页填高：其 .page-container 撑满 pane，自身 .data-body 不滚、仅表体内部滚 */
.data-tabs :deep(.n-tab-pane) > .page-container {
  flex: 1;
  min-height: 0;
}
/* 嵌入态：子页自带 .page-header 与聚合页主标题重复且随滚动会穿透，隐藏之（tab 已承担标题） */
.data-tabs :deep(.school-library > .page-header),
.data-tabs :deep(.major-library > .page-header),
.data-tabs :deep(.company-library > .page-header) {
  display: none;
}
</style>
