<template>
  <div class="page-container rl-rules-page">
    <div class="page-body">
      <!-- toolbar -->
      <div class="toolbar glass-card">
        <n-space align="center" :wrap="false" :wrap-item="false">
          <n-input
            v-model:value="searchText"
            :placeholder="t('reasonLibrary.rules.search.placeholder')"
            clearable
            style="width: 320px"
            @update:value="onSearchInput"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <n-select
            v-model:value="statusFilter"
            :options="statusOptions"
            :placeholder="t('reasonLibrary.rules.filter.allStatus')"
            style="width: 140px"
            clearable
            @update:value="loadList"
          />
        </n-space>
        <n-space>
          <n-button @click="loadList">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            {{ t('reasonLibrary.common.refresh') }}
          </n-button>
          <n-button type="primary" @click="openCreateWizard">
            <template #icon><n-icon :component="AddOutline" /></template>
            {{ t('reasonLibrary.rules.btn.create') }}
          </n-button>
        </n-space>
      </div>

      <!-- 统计 -->
      <div class="stats-row">
        <span>{{ t('reasonLibrary.common.total') }} <b>{{ totalCount }}</b> {{ t('reasonLibrary.common.rule') }}</span>
        <span>{{ t('reasonLibrary.rules.stats.enabled') }} <b>{{ enabledCount }}</b></span>
        <span>{{ t('reasonLibrary.rules.stats.system') }} <b>{{ systemCount }}</b></span>
      </div>

      <n-data-table
        :columns="columns"
        :data="rows"
        :loading="loading"
        :row-key="(r: SceneRuleListItem) => r.id"
        :pagination="false"
        :scroll-x="1100"
        size="medium"
        striped
      >
        <template #empty>
          <n-empty :description="t('reasonLibrary.rules.empty')" />
        </template>
      </n-data-table>

      <div v-if="totalCount > 0" class="pager-row">
        <n-pagination
          v-model:page="page"
          v-model:page-size="pageSize"
          :item-count="totalCount"
          :page-sizes="[10, 20, 50, 100]"
          show-size-picker
          show-quick-jumper
          @update:page="loadList"
          @update:page-size="loadList"
        />
      </div>

      <!-- Wizard 弹窗 -->
      <ReasonRuleWizard
        v-model:show="wizardShow"
        :rule-id="editingRuleId"
        @saved="onWizardSaved"
      />

      <!-- 删除确认 popconfirm (按 E-03 系统规则仅二次确认) -->
      <ReasonRuleDeleteConfirm
        v-model:show="deleteShow"
        :rule="deletingRule"
        :is-super-admin="isSuperAdmin"
        @confirm="onDeleteConfirm"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 原因库 - 场景规则 Tab (T-15 + T-17)
 *
 * - 列表: 5 列 (规则名/应用场景/原因数量/规则状态/操作)
 * - 系统预置规则: 不可删除/启停, 只能编辑 (超管能力)
 * - 启停按钮 disabled 条件: isSystem || sceneCount > 0 (Q6 规则)
 * - 删除: 自定义规则直接删, 系统规则 (超管) 仅二次确认
 */
import { ref, computed, h, onMounted } from 'vue'
import { useMessage, NButton, NTag, NSwitch, NSpace, NIcon, NDataTable, NInput, NSelect, NEmpty, NPagination } from 'naive-ui'
import { SearchOutline, RefreshOutline, AddOutline, SettingsOutline, LockClosedOutline } from '@vicons/ionicons5'
import { listRules, updateRule, deleteRule, extractReasonApiError } from '../../../api/reason-library'
import type { SceneRuleListItem } from '../../../types/reason-library'
import { BIZ_CODE, ROLE_SUPER_ADMIN } from '../../../types/reason-library'
import { t } from '../../../locales/zh-CN'
import { useUserStore } from '../../../stores/user'
import ReasonRuleWizard from '../../../components/reason-library/ReasonRuleWizard.vue'
import ReasonRuleDeleteConfirm from '../../../components/reason-library/ReasonRuleDeleteConfirm.vue'

const message = useMessage()
const userStore = useUserStore()

const userRoles = computed<string[]>(() => userStore.user?.roles ?? [])
const isSuperAdmin = computed(() => userRoles.value.includes(ROLE_SUPER_ADMIN))

// ============= 查询 =============
const searchText = ref('')
const statusFilter = ref<'on' | 'off' | null>(null)
const page = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)

const rows = ref<SceneRuleListItem[]>([])
const loading = ref(false)
let searchDebounce: number | undefined

const enabledCount = computed(() => rows.value.filter((r) => r.enabled).length)
const systemCount = computed(() => rows.value.filter((r) => r.isSystem).length)

const statusOptions = [
  { label: t('reasonLibrary.rules.filter.enabled'), value: 'on' },
  { label: t('reasonLibrary.rules.filter.disabled'), value: 'off' },
]

// ============= 加载 =============
async function loadList() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      pageSize: pageSize.value,
    }
    if (statusFilter.value === 'on') params.enabled = true
    else if (statusFilter.value === 'off') params.enabled = false
    if (searchText.value.trim()) params.search = searchText.value.trim()

    const res = await listRules(params)
    rows.value = res.items ?? []
    totalCount.value = res.total ?? rows.value.length
  } catch (e: any) {
    message.error(extractReasonApiError(e, t('reasonLibrary.common.failed')))
  } finally {
    loading.value = false
  }
}

function onSearchInput() {
  if (searchDebounce) window.clearTimeout(searchDebounce)
  searchDebounce = window.setTimeout(() => {
    page.value = 1
    loadList()
  }, 300)
}

// ============= 操作 =============
const wizardShow = ref(false)
const editingRuleId = ref<string | null>(null)

function openCreateWizard() {
  editingRuleId.value = null
  wizardShow.value = true
}

function openEditWizard(rule: SceneRuleListItem) {
  editingRuleId.value = rule.id
  wizardShow.value = true
}

async function toggleEnabled(rule: SceneRuleListItem) {
  // Q6: 有场景引用的规则不可停用
  if (rule.sceneCount > 0) {
    message.warning(t('reasonLibrary.rules.toggle.sceneLocked'))
    return
  }
  if (rule.isSystem && !isSuperAdmin.value) {
    message.warning(t('reasonLibrary.rules.toggle.systemImmutable'))
    return
  }
  try {
    await updateRule(rule.id, { enabled: !rule.enabled })
    message.success(rule.enabled ? t('reasonLibrary.rules.toggle.disable') + ' ✓' : t('reasonLibrary.rules.toggle.enable') + ' ✓')
    await loadList()
  } catch (e: any) {
    if (e?.code === BIZ_CODE.RULE_HAS_SCENE_REFS) {
      message.error(t('reasonLibrary.errors.RULE_HAS_SCENE_REFS'))
    } else if (e?.code === BIZ_CODE.SYSTEM_RULE_IMMUTABLE) {
      message.error(t('reasonLibrary.errors.SYSTEM_RULE_IMMUTABLE'))
    } else if (e?.code === BIZ_CODE.OPTIMISTIC_LOCK_FAILED) {
      message.error(t('reasonLibrary.errors.OPTIMISTIC_LOCK_FAILED'))
    } else {
      message.error(extractReasonApiError(e, t('reasonLibrary.common.failed')))
    }
  }
}

// 删除: 弹 ReasonRuleDeleteConfirm
const deleteShow = ref(false)
const deletingRule = ref<SceneRuleListItem | null>(null)
function openDeleteConfirm(rule: SceneRuleListItem) {
  deletingRule.value = rule
  deleteShow.value = true
}
async function onDeleteConfirm() {
  const rule = deletingRule.value
  if (!rule) return
  try {
    await deleteRule(rule.id)
    message.success(t('reasonLibrary.common.success'))
    deleteShow.value = false
    deletingRule.value = null
    await loadList()
  } catch (e: any) {
    if (e?.code === BIZ_CODE.SYSTEM_RULE_IMMUTABLE) {
      message.error(t('reasonLibrary.errors.SYSTEM_RULE_IMMUTABLE'))
    } else if (e?.code === BIZ_CODE.RULE_HAS_SCENE_REFS) {
      message.error(t('reasonLibrary.errors.RULE_HAS_SCENE_REFS'))
    } else {
      message.error(extractReasonApiError(e, t('reasonLibrary.common.failed')))
    }
  }
}

function onWizardSaved() {
  wizardShow.value = false
  loadList()
}

// ============= 列 =============
const columns = computed(() => [
  {
    title: t('reasonLibrary.rules.col.name'),
    key: 'name',
    width: 260,
    ellipsis: { tooltip: true },
    render: (row: SceneRuleListItem) =>
      h('div', { class: 'rl-rule-name' }, [
        h('span', { class: 'rl-name-text' }, row.name),
        row.isSystem
          ? h(
              NTag,
              {
                size: 'tiny',
                type: 'warning',
                bordered: false,
                style: 'margin-left: 8px;',
              },
              { default: () => t('reasonLibrary.rules.col.systemBadge') },
            )
          : null,
      ]),
  },
  {
    title: t('reasonLibrary.rules.col.scenes'),
    key: 'scenes',
    width: 280,
    render: (row: SceneRuleListItem) => {
      if (!row.scenes?.length) {
        return h('span', { class: 'rl-scene-empty' }, t('reasonLibrary.rules.col.emptyScenes'))
      }
      return h(
        NSpace,
        { size: 4 },
        () => row.scenes.map((s) =>
          h(
            NTag,
            {
              size: 'small',
              type: 'info',
              bordered: false,
              class: 'rl-scene-tag',
            },
            { default: () => s },
          ),
        ),
      )
    },
  },
  {
    title: t('reasonLibrary.rules.col.tagCount'),
    key: 'tagCount',
    width: 110,
    align: 'center' as const,
    render: (row: SceneRuleListItem) =>
      h(
        'span',
        { class: 'rl-tag-count' },
        [String(row.tagCount), h('span', { class: 'rl-tag-unit' }, ' 条')],
      ),
  },
  {
    title: t('reasonLibrary.rules.col.status'),
    key: 'enabled',
    width: 110,
    render: (row: SceneRuleListItem) => {
      const sceneLocked = row.sceneCount > 0
      const systemLocked = row.isSystem && !isSuperAdmin.value
      const disabled = sceneLocked || systemLocked
      const tip = sceneLocked
        ? t('reasonLibrary.rules.toggle.sceneLocked')
        : systemLocked
          ? t('reasonLibrary.rules.toggle.systemImmutable')
          : ''
      const sw = h(NSwitch, {
        value: row.enabled,
        size: 'small',
        disabled,
        onUpdateValue: () => toggleEnabled(row),
      })
      if (!tip) return sw
      // 用 title 属性 (Naive UI NSwitch 不内置 tooltip)
      return h('span', { title: tip }, sw)
    },
  },
  {
    title: t('reasonLibrary.rules.col.actions'),
    key: 'actions',
    width: 240,
    fixed: 'right' as const,
    render: (row: SceneRuleListItem) => {
      const editBtn = h(
        NButton,
        {
          size: 'small',
          quaternary: true,
          onClick: () => openEditWizard(row),
        },
        {
          icon: () => h(NIcon, null, { default: () => h(row.isSystem ? LockClosedOutline : SettingsOutline) }),
          default: () => t('reasonLibrary.rules.edit'),
        },
      )
      // 删除按钮: 系统规则仅超管可点
      const deleteBtn = h(
        NButton,
        {
          size: 'small',
          quaternary: true,
          type: 'error',
          disabled: row.isSystem && !isSuperAdmin.value,
          onClick: () => openDeleteConfirm(row),
        },
        { default: () => t('reasonLibrary.common.delete') },
      )
      return h(NSpace, { size: 4 }, () => [editBtn, deleteBtn])
    },
  },
])

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.rl-rules-page { padding: 0; }
.rl-rules-page :deep(.toolbar) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}
.stats-row {
  display: flex;
  gap: var(--space-5);
  font-size: var(--fs-13);
  color: var(--ink-soft);
  padding: 0 var(--space-1) var(--space-2);
}
.stats-row b {
  color: var(--brand);
  font-weight: 600;
  margin: 0 2px;
}
.pager-row {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-3);
}
.rl-rule-name {
  display: flex;
  align-items: center;
  min-width: 0;
}
.rl-name-text {
  font-weight: 500;
  color: var(--ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}
.rl-scene-empty {
  color: var(--ink-faint);
  font-size: var(--fs-12);
}
.rl-scene-tag {
  font-size: var(--fs-11);
}
.rl-tag-count {
  color: var(--brand);
  font-weight: 600;
}
.rl-tag-unit {
  color: var(--ink-soft);
  font-size: var(--fs-12);
  font-weight: 400;
  margin-left: 2px;
}
</style>
