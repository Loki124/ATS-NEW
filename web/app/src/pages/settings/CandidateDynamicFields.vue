<template>
  <!-- 候选人 · 动态字段：embedded 模式，仅字段定义/分组/联动规则 3 个 Tab，后端自动建默认模块 -->
  <DynamicFieldManager mode="embedded" resource="Candidate" :display-name="t('pages.settings.CandidateDynamicFields.s1')" />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import DynamicFieldManager from './DynamicFieldManager.vue';

const { t } = useI18n()
</script>
