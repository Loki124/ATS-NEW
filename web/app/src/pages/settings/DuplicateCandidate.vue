<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="dc-title-row">
          <h1 class="page-title">重复候选人管理</h1>
        </div>
        <p class="page-subtitle">
          配置重复候选人的合并策略、社招重复申请管控，以及判定「两条候选人为同一人」的查重规则。
          查重项按强度分为强 / 中 / 弱三档，规则可全局启用或停用。
        </p>
      </div>
    </div>

    <div class="page-body">
      <n-spin :show="loading">
        <!-- ============ 一、重复候选人合并规则 ============ -->
        <section class="glass-card dc-section">
          <header class="dc-section-head">
            <div class="dc-section-titles">
              <h2 class="dc-section-title">重复候选人合并规则</h2>
              <span class="dc-scope">全局</span>
            </div>
          </header>

          <div class="dc-section-body">
            <div class="dc-row">
              <div class="dc-row-main">
                <div class="dc-row-label">启用合并</div>
                <div class="dc-row-desc">将判定为重复的候选人自动合并，整合为主体候选人信息。</div>
              </div>
              <n-switch v-model:value="merge.enabled" />
            </div>

            <div class="dc-row">
              <div class="dc-row-main">
                <div class="dc-row-label">取消未被接受的猎头候选人</div>
                <div class="dc-row-desc">当候选人被判定为重复时，自动取消未被接受的猎头候选人关联。</div>
              </div>
              <n-switch v-model:value="merge.cancelUnacceptedHeadhunter" />
            </div>

            <div class="dc-subhead">合并规则如下：</div>

            <div v-for="(s, i) in merge.strategies" :key="s.key" class="dc-strategy">
              <span class="dc-strategy-num">{{ i + 1 }}</span>
              <div class="dc-strategy-main">
                <div class="dc-strategy-label">{{ s.label }}</div>
              </div>
              <n-select
                class="dc-strategy-select"
                :options="s.options"
                :value="s.value"
                @update:value="(v: string) => onStrategyChange(s.key, v)"
              />
            </div>

            <div class="dc-actions">
              <n-button tertiary :disabled="savingMerge" @click="resetMerge">恢复默认</n-button>
              <n-button type="primary" :loading="savingMerge" @click="saveMerge">保存合并规则</n-button>
            </div>
          </div>
        </section>

        <!-- ============ 二、重复申请管理（社招） ============ -->
        <section class="glass-card dc-section">
          <header class="dc-section-head">
            <div class="dc-section-titles">
              <h2 class="dc-section-title">重复申请管理</h2>
              <span class="dc-scope dc-scope--social">社招</span>
            </div>
          </header>

          <div class="dc-section-body">
            <div class="dc-row">
              <div class="dc-row-main">
                <div class="dc-row-label">启用重复申请管理</div>
                <div class="dc-row-desc">启用后，候选人在规定时间窗口内重复投递将自动进入管控流程。</div>
              </div>
              <n-switch v-model:value="application.enabled" />
            </div>

            <div class="dc-row">
              <div class="dc-row-main">
                <div class="dc-row-label">重复申请时间窗口</div>
                <div class="dc-row-desc">候选人在该时间窗口内对同一职位的重复投递将被自动管控。</div>
              </div>
              <n-select
                class="dc-window-select"
                :options="application.windowOptions"
                :value="application.windowMonths"
                :disabled="!application.enabled"
                @update:value="(v: number) => (application.windowMonths = v)"
              />
            </div>

            <div class="dc-actions">
              <n-button type="primary" :loading="savingApp" @click="saveApplication">保存申请管理</n-button>
            </div>
          </div>
        </section>

        <!-- ============ 三、候选人查重规则 ============ -->
        <section class="glass-card dc-section">
          <header class="dc-section-head">
            <div class="dc-section-titles">
              <h2 class="dc-section-title">候选人查重规则</h2>
              <span class="dc-scope">全局</span>
            </div>
            <div class="dc-section-actions">
              <n-button text size="small" @click="openAllRules">
                <template #icon><n-icon :component="ListOutline" /></template>
                编辑全部规则
              </n-button>
              <n-button type="primary" size="small" @click="openCreate">
                <template #icon><n-icon :component="AddOutline" /></template>
                新建查重规则
              </n-button>
            </div>
          </header>

          <div class="dc-section-body">
            <n-data-table
              :columns="ruleColumns"
              :data="presetRules"
              :loading="loadingRules"
              :row-key="(row: any) => row.id"
              :bordered="false"
              size="small"
            />
            <p class="dc-footnote">
              共 {{ presetRules.length }} 条可编辑规则；另有 2 条系统内置规则仅可启用 / 停用，点「编辑全部规则」查看。
            </p>
          </div>
        </section>
      </n-spin>
    </div>

    <!-- ============ 编辑全部规则（含系统内置） ============ -->
    <n-modal
      v-model:show="allRulesModal"
      preset="card"
      title="编辑候选人查重规则"
      :bordered="false"
      style="width: 820px; max-width: 92vw;"
    >
      <div class="dc-modal-actions">
        <n-button text size="small" type="error" @click="onResetRules">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          恢复系统默认规则
        </n-button>
        <n-button type="primary" size="small" @click="openCreate">
          <template #icon><n-icon :component="AddOutline" /></template>
          新建查重规则
        </n-button>
      </div>
      <div class="dc-modal-table">
        <n-data-table
          :columns="ruleColumns"
          :data="rules"
          :loading="loadingRules"
          :row-key="(row: any) => row.id"
          :bordered="false"
          size="small"
        />
      </div>
    </n-modal>

    <!-- ============ 新建 / 编辑 查重规则 抽屉 ============ -->
    <n-drawer
      v-model:show="drawerShow"
      :width="540"
      placement="right"
      :mask-closable="true"
      :auto-focus="false"
    >
      <n-drawer-content
        :title="editingRule ? '编辑查重规则' : '新建候选人查重规则'"
        :native-scrollbar="false"
        closable
      >
        <div class="dc-drawer-body">
          <div class="dc-field">
            <label class="dc-field-label">规则名称 <span class="dc-req">*</span></label>
            <n-input
              v-model:value="form.name"
              placeholder="如：基于身份证"
              :maxlength="128"
              show-count
            />
          </div>

          <div v-for="grp in catalogGroups" :key="grp.strength" class="dc-field">
            <label class="dc-field-label dc-field-label--group">
              {{ strengthLabel(grp.strength) }}查重项
              <span class="dc-strength-tag" :class="'dc-strength--' + grp.strength.toLowerCase()">
                {{ strengthLabel(grp.strength) }}
              </span>
            </label>
            <div class="dc-check-grid">
              <label
                v-for="item in grp.items"
                :key="item.key"
                class="dc-check"
                :class="{ 'dc-check--on': isSelected(item.key) }"
              >
                <n-checkbox
                  :checked="isSelected(item.key)"
                  @update:checked="(v: boolean) => toggleItem(item.key, v)"
                />
                <span class="dc-check-label">{{ item.label }}</span>
                <n-tooltip trigger="hover" placement="top">
                  <template #trigger>
                    <n-icon :component="HelpCircleOutline" class="dc-check-hint" />
                  </template>
                  {{ item.hint }}
                </n-tooltip>
              </label>
            </div>
          </div>

          <div class="dc-field">
            <label class="dc-field-label">查重条件</label>
            <n-radio-group v-model:value="form.conditionLogic">
              <n-radio value="ALL">全部一致</n-radio>
              <n-radio value="ANY">任意 N 项一致</n-radio>
            </n-radio-group>
            <div v-if="form.conditionLogic === 'ANY'" class="dc-any-count">
              <span>命中项数 N =</span>
              <n-input-number
                v-model:value="form.anyCount"
                :min="1"
                :max="Math.max(1, selectedKeys.length)"
                size="small"
                style="width: 110px;"
              />
              <span class="dc-any-hint">（最多 {{ Math.max(1, selectedKeys.length) }} 项）</span>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="dc-actions">
            <n-button tertiary @click="closeDrawer">取消</n-button>
            <n-button type="primary" :loading="savingRule" @click="saveRule">保存规则</n-button>
          </div>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, onMounted } from 'vue'
import {
  NButton, NIcon, NSpin, NSwitch, NSelect, NInput, NInputNumber,
  NRadio, NRadioGroup, NCheckbox, NTag, NModal, NDrawer, NDrawerContent,
  NTooltip, NDataTable, NEmpty, useMessage, useDialog,
  type DataTableColumns,
} from 'naive-ui'
import {
  AddOutline, ListOutline, RefreshOutline, HelpCircleOutline,
} from '@vicons/ionicons5'
import {
  getDuplicateCatalog, getDuplicateConfig, updateDuplicateConfig,
  listDuplicateRules, createDuplicateRule, updateDuplicateRule,
  deleteDuplicateRule, toggleDuplicateRule, resetDuplicateRules,
  type DuplicateRule, type DuplicateFieldGroup, type DuplicateConfig,
  type MergeConfig, type ApplicationConfig, type DuplicateStrength,
} from '../../api/duplicate-rule'

const message = useMessage()
const dialog = useDialog()

// ===== 状态 =====
const loading = ref(false)
const loadingRules = ref(false)
const savingMerge = ref(false)
const savingApp = ref(false)
const savingRule = ref(false)
const allRulesModal = ref(false)
const drawerShow = ref(false)
const editingRule = ref<DuplicateRule | null>(null)

const config = ref<DuplicateConfig | null>(null)
const merge = reactive<MergeConfig>({
  enabled: true, cancelUnacceptedHeadhunter: true, strategies: [],
})
const application = reactive<ApplicationConfig>({
  enabled: true, windowMonths: 6, windowOptions: [],
})

const rules = ref<DuplicateRule[]>([])
const catalogGroups = ref<DuplicateFieldGroup[]>([])
const strengthByKey = ref<Record<string, DuplicateStrength>>({})

// 抽屉表单
const form = reactive({
  name: '',
  conditionLogic: 'ALL' as 'ALL' | 'ANY',
  anyCount: 1,
  selected: [] as string[],
})
const selectedKeys = computed(() => form.selected)

const presetRules = computed(() => rules.value.filter((r) => !r.isSystem))

// ===== 查重项目录 =====
function strengthLabel(s: DuplicateStrength): string {
  return s === 'STRONG' ? '强' : s === 'MEDIUM' ? '中' : '弱'
}
function isSelected(key: string): boolean {
  return form.selected.includes(key)
}
function toggleItem(key: string, checked: boolean) {
  if (checked) {
    if (!form.selected.includes(key)) form.selected.push(key)
  } else {
    form.selected = form.selected.filter((k) => k !== key)
  }
}

// ===== 加载 =====
async function loadAll() {
  loading.value = true
  try {
    const [cfg, rl, cat] = await Promise.all([
      getDuplicateConfig(),
      listDuplicateRules(),
      getDuplicateCatalog(),
    ])
    config.value = cfg
    merge.enabled = cfg.merge.enabled
    merge.cancelUnacceptedHeadhunter = cfg.merge.cancelUnacceptedHeadhunter
    merge.strategies = cfg.merge.strategies
    application.enabled = cfg.application.enabled
    application.windowMonths = cfg.application.windowMonths
    application.windowOptions = cfg.application.windowOptions
    rules.value = rl
    catalogGroups.value = cat.groups
    const map: Record<string, DuplicateStrength> = {}
    for (const g of cat.groups) for (const it of g.items) map[it.key] = g.strength
    strengthByKey.value = map
  } catch (e: any) {
    message.error(`加载失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

// ===== 合并规则 =====
function onStrategyChange(key: string, value: string) {
  const s = merge.strategies.find((x) => x.key === key)
  if (s) s.value = value
}
async function saveMerge() {
  savingMerge.value = true
  try {
    const updated = await updateDuplicateConfig({
      merge: {
        enabled: merge.enabled,
        cancelUnacceptedHeadhunter: merge.cancelUnacceptedHeadhunter,
        strategies: merge.strategies.map((s) => ({
          key: s.key, label: s.label, value: s.value, options: s.options,
        })),
      },
    })
    merge.enabled = updated.merge.enabled
    merge.cancelUnacceptedHeadhunter = updated.merge.cancelUnacceptedHeadhunter
    merge.strategies = updated.merge.strategies
    message.success('合并规则已保存')
  } catch (e: any) {
    message.error(`保存失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
  } finally {
    savingMerge.value = false
  }
}
async function resetMerge() {
  dialog.warning({
    title: '恢复默认合并规则',
    content: '将合并规则与策略重置为系统默认，当前自定义修改会丢失。是否继续？',
    positiveText: '恢复默认',
    negativeText: '取消',
    onPositiveClick: async () => {
      savingMerge.value = true
      try {
        const updated = await updateDuplicateConfig({
          merge: { enabled: true, cancelUnacceptedHeadhunter: true, strategies: [] },
        })
        merge.enabled = updated.merge.enabled
        merge.cancelUnacceptedHeadhunter = updated.merge.cancelUnacceptedHeadhunter
        merge.strategies = updated.merge.strategies
        message.success('已恢复默认合并规则')
      } catch (e: any) {
        message.error(`操作失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
      } finally {
        savingMerge.value = false
      }
    },
  })
}

// ===== 重复申请管理 =====
async function saveApplication() {
  savingApp.value = true
  try {
    const updated = await updateDuplicateConfig({
      application: { enabled: application.enabled, windowMonths: application.windowMonths },
    })
    application.enabled = updated.application.enabled
    application.windowMonths = updated.application.windowMonths
    application.windowOptions = updated.application.windowOptions
    message.success('申请管理已保存')
  } catch (e: any) {
    message.error(`保存失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
  } finally {
    savingApp.value = false
  }
}

// ===== 规则表格 =====
function statusTag(row: DuplicateRule) {
  return h(
    NTag,
    { bordered: false, size: 'small', type: row.isEnabled ? 'success' : 'default' },
    { default: () => (row.isEnabled ? '启用中' : '已停用') },
  )
}
function toggleBtn(row: DuplicateRule) {
  return h(
    NButton,
    {
      size: 'tiny',
      tertiary: true,
      onClick: () => onToggle(row),
    },
    { default: () => (row.isEnabled ? '停用' : '启用') },
  )
}
function renderActions(row: DuplicateRule) {
  const children = []
  if (row.isSystem) {
    children.push(toggleBtn(row))
  } else {
    children.push(
      h(NButton, { size: 'tiny', tertiary: true, onClick: () => openEdit(row) }, { default: () => '编辑' }),
      toggleBtn(row),
      h(
        NButton,
        { size: 'tiny', tertiary: true, type: 'error', onClick: () => onDelete(row) },
        { default: () => '删除' },
      ),
    )
  }
  return h('div', { class: 'dc-act' }, children)
}
const ruleColumns: DataTableColumns<DuplicateRule> = [
  {
    title: '规则名称',
    key: 'name',
    render: (row) => (row.isSystem ? `${row.name}（系统）` : row.name),
  },
  { title: '查重条件', key: 'conditionText', width: 110 },
  {
    title: '查重项',
    key: 'itemsText',
    render: (row) => (row.itemsText && row.itemsText.length ? row.itemsText.join('、') : '—'),
  },
  { title: '状态', key: 'isEnabled', width: 96, render: (row) => statusTag(row) },
  { title: '操作', key: 'actions', width: 168, render: (row) => renderActions(row) },
]

function replaceRule(updated: DuplicateRule) {
  const idx = rules.value.findIndex((r) => r.id === updated.id)
  if (idx >= 0) rules.value[idx] = updated
  else rules.value = [...rules.value, updated]
}
async function onToggle(row: DuplicateRule) {
  try {
    const updated = await toggleDuplicateRule(row.id)
    replaceRule(updated)
    message.success(updated.isEnabled ? '已启用' : '已停用')
  } catch (e: any) {
    message.error(`操作失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
  }
}
async function onDelete(row: DuplicateRule) {
  dialog.warning({
    title: '删除查重规则',
    content: `确定删除「${row.name}」？删除后不可在界面恢复，但数据仍保留在后台。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteDuplicateRule(row.id)
        rules.value = rules.value.filter((r) => r.id !== row.id)
        message.success('已删除')
      } catch (e: any) {
        message.error(`删除失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
      }
    },
  })
}
async function onResetRules() {
  dialog.warning({
    title: '恢复系统默认规则',
    content: '将软删全部自定义规则，并把系统内置规则复位为默认值。是否继续？',
    positiveText: '恢复默认',
    negativeText: '取消',
    onPositiveClick: async () => {
      loadingRules.value = true
      try {
        const rl = await resetDuplicateRules()
        rules.value = rl
        message.success('已恢复系统默认规则')
      } catch (e: any) {
        message.error(`操作失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
      } finally {
        loadingRules.value = false
      }
    },
  })
}

// ===== 抽屉（新建 / 编辑）=====
function openCreate() {
  editingRule.value = null
  form.name = ''
  form.conditionLogic = 'ALL'
  form.anyCount = 1
  form.selected = []
  drawerShow.value = true
}
function openEdit(row: DuplicateRule) {
  editingRule.value = row
  form.name = row.name
  form.conditionLogic = row.conditionLogic
  form.anyCount = row.anyCount || 1
  form.selected = (row.items || []).map((i) => i.key)
  drawerShow.value = true
}
function closeDrawer() {
  drawerShow.value = false
  editingRule.value = null
}
async function saveRule() {
  if (!form.name.trim()) {
    message.warning('请填写规则名称')
    return
  }
  const items = form.selected.map((key) => ({ key, strength: strengthByKey.value[key] }))
  const hasStrongMedium = items.some(
    (i) => i.strength === 'STRONG' || i.strength === 'MEDIUM',
  )
  if (!hasStrongMedium) {
    message.warning('至少添加 1 项强查重项或中查重项')
    return
  }
  if (form.conditionLogic === 'ANY' && (form.anyCount || 1) > items.length) {
    message.warning(`任意项数不能大于勾选的查重项数量（${items.length}）`)
    return
  }
  savingRule.value = true
  try {
    const payload = {
      name: form.name.trim(),
      conditionLogic: form.conditionLogic,
      anyCount: form.conditionLogic === 'ANY' ? form.anyCount || 1 : 1,
      items,
    }
    if (editingRule.value) {
      const updated = await updateDuplicateRule(editingRule.value.id, payload)
      replaceRule(updated)
      message.success('规则已更新')
    } else {
      const created = await createDuplicateRule(payload)
      replaceRule(created)
      message.success('规则已创建')
    }
    closeDrawer()
  } catch (e: any) {
    message.error(`保存失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
  } finally {
    savingRule.value = false
  }
}

function openAllRules() {
  allRulesModal.value = true
}

onMounted(loadAll)
</script>

<style scoped>
.page-container {
  min-height: 100%;
  box-sizing: border-box;
  padding: var(--space-6);
}
.page-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  margin-top: var(--space-2);
}
.dc-title-row { display: flex; align-items: center; gap: var(--space-2); }

/* ===== 区块卡片 ===== */
.dc-section { padding: var(--space-5); }
.dc-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.dc-section-titles { display: flex; align-items: center; gap: var(--space-2); }
.dc-section-title {
  margin: 0;
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink);
}
.dc-scope {
  font-size: var(--text-meta);
  padding: 2px var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--c-info-soft);
  color: var(--c-info);
}
.dc-scope--social { background: var(--c-warning-soft); color: var(--c-warning); }
.dc-section-actions { display: flex; align-items: center; gap: var(--space-3); }

.dc-section-body { display: flex; flex-direction: column; gap: var(--space-3); }

/* ===== 合并 / 申请 行 ===== */
.dc-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border-hairline);
}
.dc-row:last-of-type { border-bottom: none; }
.dc-row-main { min-width: 0; }
.dc-row-label { font-size: var(--text-small); font-weight: 600; color: var(--ink); }
.dc-row-desc { font-size: var(--text-meta); color: var(--ink-faint); margin-top: 2px; line-height: 1.5; }

.dc-subhead {
  margin-top: var(--space-2);
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--ink-soft);
}
.dc-strategy {
  display: grid;
  grid-template-columns: 28px 1fr 320px;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
}
.dc-strategy-num {
  width: 24px; height: 24px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: var(--radius-pill);
  background: var(--brand-tint);
  color: var(--brand);
  font-size: var(--text-meta);
  font-weight: 700;
}
.dc-strategy-label { font-size: var(--text-small); color: var(--ink); }
.dc-strategy-select { width: 100%; }
.dc-window-select { width: 240px; flex-shrink: 0; }

.dc-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

/* ===== 规则表格 ===== */
.dc-footnote { font-size: var(--text-meta); color: var(--ink-faint); margin: var(--space-3) 0 0; }
.dc-act { display: flex; align-items: center; gap: var(--space-1); flex-wrap: wrap; }

/* ===== 弹窗 / 抽屉 ===== */
.dc-modal-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}
.dc-modal-table { max-height: 60vh; overflow: auto; }
.dc-drawer-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-2) var(--space-1) var(--space-4);
}
.dc-field { display: flex; flex-direction: column; gap: var(--space-2); }
.dc-field-label { font-size: var(--text-small); font-weight: 600; color: var(--ink); }
.dc-field-label--group { display: flex; align-items: center; gap: var(--space-2); }
.dc-req { color: var(--c-error); margin-left: 2px; }
.dc-strength-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 1px var(--space-2);
  border-radius: var(--radius-pill);
}
.dc-strength--strong { background: var(--c-error-soft); color: var(--c-error); }
.dc-strength--medium { background: var(--c-warning-soft); color: var(--c-warning); }
.dc-strength--weak { background: var(--c-info-soft); color: var(--c-info); }

.dc-check-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-2);
}
.dc-check {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--glass-bg-card);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out);
}
.dc-check:hover { border-color: var(--brand); }
.dc-check--on { border-color: var(--brand); background: var(--brand-tint); }
.dc-check-label { font-size: var(--text-small); color: var(--ink); flex: 1; min-width: 0; }
.dc-check-hint { color: var(--ink-faint); cursor: help; flex-shrink: 0; }

.dc-any-count {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-small);
  color: var(--ink-soft);
}
.dc-any-hint { font-size: var(--text-meta); color: var(--ink-faint); }

@media (max-width: 720px) {
  .dc-strategy { grid-template-columns: 24px 1fr; }
  .dc-strategy-select { grid-column: 1 / -1; }
  .dc-window-select { width: 100%; }
  .dc-check-grid { grid-template-columns: 1fr; }
}
</style>
