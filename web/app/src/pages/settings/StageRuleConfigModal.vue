<!--
  2026-09-07: 主实现已迁至 ./stage-rule/StageRuleConfigModal.vue（18 文件拆分重写）。
  本文件保留为 passthrough wrapper，维持 ProcessDetailModal 的 import 路径不变
  （不修改其他 modal）。所有逻辑见 ./stage-rule/。
-->
<script setup lang="ts">
import StageRuleConfigModal from './stage-rule/StageRuleConfigModal.vue'
</script>

<template>
  <StageRuleConfigModal v-bind="$attrs" />
</template>
