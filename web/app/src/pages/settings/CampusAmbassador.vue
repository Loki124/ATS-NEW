<template>
  <div class="page-container ca-page">
    <!-- 社招环境：显性差异 —— 此配置为校招专属，不呈现 -->
    <EmptyState
      v-if="!systemStore.isCampus"
      :title="t('pages.settings.CampusAmbassador.s2')"
      description="「校园大使」配置仅在切换到「校园招聘」系统后呈现。请在左上角系统切换器中选择「校园招聘」。"
    />

    <!-- 校招环境：校园大使配置（Phase 2 样板 —— 后续接后端 campus_ambassador 模块） -->
    <template v-else>
      <header class="ca-header">
        <div>
          <h1 class="page-title">{{ systemStore.label }} · 校园大使</h1>
          <p class="page-subtitle">{ t('pages.settings.CampusAmbassador.s1') }</p>
        </div>
        <n-switch
          :value="enabled"
          :loading="savingEnabled"
          @update:value="onToggleEnabled"
        >
          <template #checked>已启用</template>
          <template #unchecked>未启用</template>
        </n-switch>
      </header>

      <n-card class="ca-card" :bordered="false">
        <div class="ca-card__toolbar">
          <n-input
            v-model:value="keyword"
            placeholder="搜索学校 / 大使姓名"
            clearable
            class="ca-search"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <n-button type="primary" :disabled="!enabled" @click="openCreate">
            <template #icon><n-icon :component="PersonAddOutline" /></template>
            添加大使
          </n-button>
        </div>

        <n-data-table
          :columns="columns"
          :data="filteredRows"
          :row-key="(row: any) => row.id"
          :loading="loading"
          flex-height
          class="ca-table"
        />

        <n-empty v-if="!loading && filteredRows.length === 0" description="暂无校园大使" class="ca-empty" />
      </n-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { computed, h, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NEmpty,
  NIcon,
  NInput,
  NSwitch,
  useMessage,
} from 'naive-ui'
import { SearchOutline, PersonAddOutline, TrashOutline } from '@vicons/ionicons5'
import EmptyState from '../../components/common/EmptyState.vue'
import { useSystemStore } from '../../stores/system'
const { t } = useI18n()

/**
 * CampusAmbassador — 校园招聘专属配置样板（G-2026-09-23 Phase 2-3）
 *
 * 体现「显性配置差异」范式：
 * - 整页用 v-if="systemStore.isCampus" 包裹，社招环境直接展示 EmptyState 说明，
 *   不暴露任何校招专属配置 UI（即使通过 URL 直达也能正确拦截）。
 * - 菜单入口也仅在 isCampus 时由 Layout.menuOptions 追加，双重保证。
 *
 * 后续 Phase 4 接后端 campus_ambassador 模块（受 recruit_type='campus' 隔离）。
 * 当前数据为前端占位，用于跑通 UI 范式与真机验收。
 */
const systemStore = useSystemStore()
const message = useMessage()

const enabled = ref(false)
const savingEnabled = ref(false)
const loading = ref(false)
const keyword = ref('')
const rows = ref<any[]>([
  { id: 1, school: '上海交通大学', name: '张同学', region: '华东', status: 'active' },
  { id: 2, school: '浙江大学', name: '李同学', region: '华东', status: 'active' },
  { id: 3, school: '武汉大学', name: '王同学', region: '华中', status: 'pending' },
])

const filteredRows = computed(() => {
  const k = keyword.value.trim()
  if (!k) return rows.value
  return rows.value.filter(
    (r) => r.school.includes(k) || r.name.includes(k),
  )
})

const columns = [
  { title: '高校', key: 'school' },
  { title: '大使姓名', key: 'name' },
  { title: '区域', key: 'region' },
  {
    title: '状态',
    key: 'status',
    render: (row: any) =>
      h(
        'span',
        { class: row.status === 'active' ? 'ca-tag ca-tag--on' : 'ca-tag ca-tag--off' },
        row.status === 'active' ? '已激活' : '待审核',
      ),
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: any) =>
      h(
        NButton,
        { size: 'small', quaternary: true, type: 'error', onClick: () => remove(row.id) },
        { default: () => '移除' },
      ),
  },
]

function onToggleEnabled(val: boolean) {
  savingEnabled.value = true
  // 模拟保存（占位）
  setTimeout(() => {
    enabled.value = val
    savingEnabled.value = false
    message.success(val ? '已启用校园大使模块' : '已停用校园大使模块')
  }, 400)
}

function openCreate() {
  message.info('「添加大使」表单（Phase 4 接入后端）')
}

function remove(id: number) {
  rows.value = rows.value.filter((r) => r.id !== id)
  message.success('已移除该大使')
}
</script>

<style scoped>
.ca-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}
.ca-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.ca-card {
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
}
.ca-card__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
.ca-search {
  max-width: 280px;
}
.ca-table {
  min-height: 240px;
}
.ca-empty {
  padding: var(--space-10) 0;
}
.ca-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: var(--fs-12);
  line-height: 1.4;
}
.ca-tag--on {
  background: color-mix(in oklch, var(--color-success) 16%, transparent);
  color: var(--color-success);
}
.ca-tag--off {
  background: color-mix(in oklch, var(--color-warning) 16%, transparent);
  color: var(--color-warning);
}
</style>
