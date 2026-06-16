<template>
  <div class="global-search">
    <n-auto-complete
      v-model:value="keyword"
      :options="options"
      :render-label="renderLabel"
      :loading="loading"
      placeholder="搜索候选人 / 需求 / 职位 / 面试 / Offer / 内推..."
      clearable
      :input-props="{ 'aria-label': '全局搜索' }"
      @select="onSelect"
      @update:value="onSearch"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { NAutoComplete, useMessage } from 'naive-ui'
import {
  searchApi,
  entityLabel,
  routeForEntity,
  type SearchEntityType,
  type SearchResponse,
} from '../../api/search'
import { debounce } from '../../utils/debounce'

const keyword = ref('')
const loading = ref(false)
const response = ref<SearchResponse | null>(null)
const error = ref<string | null>(null)
const router = useRouter()
const message = useMessage()

// 转换为 n-auto-complete 的 options 格式 (nested children for groups)
const options = computed(() => {
  if (!response.value || response.value.groups.length === 0) return []
  const result: any[] = []
  for (const group of response.value.groups) {
    if (group.items.length === 0) continue
    // 组: children 是 items
    result.push({
      type: 'group',
      name: entityLabel(group.type),
      key: `group-${group.type}`,
      children: group.items.map((item) => ({
        label: renderItemLabel(group.type, item),
        value: `${group.type}:${item.id}`,
        groupType: group.type,
        itemId: item.id,
      })),
    })
  }
  return result
})

function renderItemLabel(type: SearchEntityType, item: any): string {
  if (type === 'candidate') return `${item.name} · ${item.position?.name ?? ''} · ${item.phone ?? ''}`
  if (type === 'demand') return `${item.title} · ${item.status} · ${item.department?.name ?? ''}`
  if (type === 'position') return `${item.name} · ${item.status} · ${item.department?.name ?? ''}`
  if (type === 'interview') {
    const t = item.scheduledAt ? new Date(item.scheduledAt).toLocaleString('zh-CN') : ''
    return `${item.candidate?.name ?? ''} · ${item.position?.name ?? ''} · ${t}`
  }
  if (type === 'offer') return `${item.candidate?.name ?? ''} · ${item.position?.name ?? ''} · ${item.status}`
  if (type === 'referral') return `${item.candidateName} · 推荐人 ${item.referrer?.realName ?? ''}`
  return JSON.stringify(item)
}

function renderLabel(option: any) {
  if (option.type === 'group') {
    return h('span', { class: 'global-search__group-header' }, option.name)
  }
  return h('span', null, option.label)
}

// ===== 搜索 =====

async function doSearch(q: string) {
  if (!q.trim()) {
    response.value = null
    return
  }
  loading.value = true
  error.value = null
  try {
    response.value = await searchApi({ q, limit: 5 })
  } catch (e: any) {
    error.value = e?.message || '搜索失败'
    message.error('搜索失败,请重试')
  } finally {
    loading.value = false
  }
}

const debouncedSearch = debounce(doSearch, 300)

function onSearch(val: string) {
  keyword.value = val
  if (!val.trim()) {
    response.value = null
    return
  }
  debouncedSearch(val)
}

// ===== 选中 =====

function onSelect(value: string) {
  const [type, id] = value.split(':') as [SearchEntityType, string]
  const route = routeForEntity(type, id)
  router.push(route)
  keyword.value = ''
  response.value = null
}
</script>

<style scoped>
.global-search {
  width: 100%;
  max-width: 360px;
}
.global-search__group-header {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-2);
  padding: 4px 0;
}
</style>
