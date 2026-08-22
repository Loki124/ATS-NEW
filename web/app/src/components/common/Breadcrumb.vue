<template>
  <n-breadcrumb v-if="crumbs.length > 1" class="ats-breadcrumb">
    <n-breadcrumb-item v-for="(c, i) in crumbs" :key="c.path">
      <a v-if="i < crumbs.length - 1" @click.prevent="$router.push(c.path)">{{ c.label }}</a>
      <span v-else>{{ c.label }}</span>
    </n-breadcrumb-item>
  </n-breadcrumb>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
const crumbs = computed(() =>
  route.matched
    .filter(r => r.meta?.title)
    .map(r => ({ path: r.path, label: r.meta.title as string }))
)
</script>

<style scoped>
.ats-breadcrumb { font-size: var(--text-small); padding: var(--space-2) 0; color: var(--ink-faint); }
.ats-breadcrumb a { color: var(--ink-soft); cursor: pointer; }
.ats-breadcrumb a:hover { color: var(--brand); }
</style>