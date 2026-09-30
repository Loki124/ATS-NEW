<template>
  <div class="page-container interview-round">
<div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.RecruitmentRound.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.RecruitmentRound.s2') }}</p>
      </div>
    </div>

    <div class="toolbar">
      <n-input v-model:value="keyword" :placeholder="t('pages.settings.RecruitmentRound.s3')" clearable style="width: 200px">
        <template #prefix><n-icon :component="SearchOutline" /></template>
      </n-input>
      <div class="spacer"></div>
      <n-button type="primary" class="gradient-btn" @click="showModal = true">
        <template #icon><n-icon :component="AddOutline" /></template>
        {{ t('pages.settings.RecruitmentRound.s4') }}
      </n-button>
    </div>

    <div class="table-wrap">
    <n-data-table
      :columns="columns"
      :data="rounds"
      :loading="loading"
      :pagination="localPagination()"
      :row-key="(r) => r.id"
      :max-height="tableMaxHeight"
      :row-height="TABLE_ROW_HEIGHT"
    />
    </div>
</div><!-- /.page-body -->
<n-modal v-model:show="showModal" preset="card" :title="editing ? t('pages.settings.RecruitmentRound.s13') : t('pages.settings.RecruitmentRound.s4')" style="width: 520px; max-width: 90vw" :bordered="false" :segmented="{ content: true, footer: true }">
      <n-form :model="form" label-placement="top">
        <n-form-item :label="t('pages.settings.RecruitmentRound.s5')" required>
          <n-input v-model:value="form.name" :placeholder="t('pages.settings.RecruitmentRound.s6')" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.RecruitmentRound.s7')">
          <n-input v-model:value="form.evaluationFormName" :placeholder="t('pages.settings.RecruitmentRound.s8')" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.RecruitmentRound.s9')">
          <n-switch v-model:value="form.isUniversal" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.RecruitmentRound.s10')">
          <n-input v-model:value="form.description" type="textarea" :rows="2" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="showModal = false">{{ t('pages.settings.RecruitmentRound.s11') }}</n-button>
          <n-button type="primary" class="gradient-btn" :loading="saving" @click="handleSave">{{ t('pages.settings.RecruitmentRound.s12') }}</n-button>
        </div>
      </template>
    </n-modal>
</div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { localPagination } from '@/composables/useTablePagination'
import { ref, reactive, onMounted, h, computed } from 'vue'
import { useMessage, NButton, NTag, NPopconfirm, NIcon, NSpace, NInput, NSwitch, NForm, NFormItem, NModal, NDataTable } from 'naive-ui'
import { AddOutline, PowerOutline, SearchOutline } from '@vicons/ionicons5'
import { listRounds, createRound, updateRound, updateRoundStatus } from '../../api/recruitment-process'
const { t } = useI18n()

const message = useMessage()
const keyword = ref('')
const rounds = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showModal = ref(false)
const editing = ref<any>(null)
// 2026-08-29 UX 整改：表头固定 + 行高统一
// 2026-08-30 UX 二改：56→44 + td 垂直 padding 10→6，压缩行间距（兵哥嫌"行间距太大"）
const TABLE_ROW_HEIGHT = 44
const tableMaxHeight = computed(() => {
  if (typeof window === 'undefined') return 560
  // 预留分页器 64 + page-header 80 + toolbar 56 + page-body gap 32 ≈ 232
  return Math.max(320, window.innerHeight - 232)
})
const form = reactive({
  name: '',
  description: '',
  evaluationFormName: '',
  isUniversal: false,
})

const columns = [
  { title: t('pages.settings.RecruitmentRound.s15'), key: 'code', width: 100 },
  { title: t('pages.settings.RecruitmentRound.s5'), key: 'name', width: 140 },
  { title: t('pages.settings.RecruitmentRound.s7'), key: 'evaluationFormName', width: 160, render: (r: any) => r.evaluationFormName || '-' },
  {
    title: t('pages.settings.RecruitmentRound.s18'),
    key: 'isUniversal',
    width: 110,
    render: (r: any) => r.isUniversal ? h(NTag, { type: 'warning', size: 'small' }, { default: () => t('pages.settings.RecruitmentRound.s19') }) : '-',
  },
  {
    title: t('pages.settings.RecruitmentRound.s20'),
    key: 'status',
    width: 90,
    render: (r: any) => h(NTag, { type: r.status === 'ACTIVE' ? 'success' : 'default', size: 'small' }, { default: () => r.status === 'ACTIVE' ? t('pages.settings.RecruitmentRound.s21') : t('pages.settings.RecruitmentRound.s22') }),
  },
  {
    title: t('pages.settings.RecruitmentRound.s23'),
    key: 'action',
    width: 200,
    fixed: 'right' as const,
    render: (row: any) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { size: 'small', text: true, onClick: () => handleEdit(row) }, { default: () => t('pages.settings.RecruitmentRound.s24') }),
      h(NButton, { size: 'small', text: true, onClick: () => handleToggleStatus(row) }, { default: () => row.status === 'ACTIVE' ? t('pages.settings.RecruitmentRound.s22') : t('pages.settings.RecruitmentRound.s21') }),
    ]),
  },
]

async function loadList() {
  loading.value = true
  try {
    rounds.value = await listRounds({ keyword: keyword.value || undefined })
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.RecruitmentRound.s25'))
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editing.value = null
  Object.assign(form, { name: '', description: '', evaluationFormName: '', isUniversal: false })
  showModal.value = true
}

function handleEdit(row: any) {
  editing.value = row
  Object.assign(form, {
    name: row.name,
    description: row.description || '',
    evaluationFormName: row.evaluationFormName || '',
    isUniversal: row.isUniversal,
  })
  showModal.value = true
}

async function handleSave() {
  if (!form.name.trim()) {
    message.error(t('pages.settings.RecruitmentRound.s26'))
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await updateRound(editing.value.id, form)
      message.success(t('pages.settings.RecruitmentRound.s27'))
    } else {
      await createRound(form)
      message.success(t('pages.settings.RecruitmentRound.s28'))
    }
    showModal.value = false
    loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.RecruitmentRound.s29'))
  } finally {
    saving.value = false
  }
}

async function handleToggleStatus(row: any) {
  const newStatus = row.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
  try {
    await updateRoundStatus(row.id, newStatus)
    message.success(`已${newStatus === 'ACTIVE' ? t('pages.settings.RecruitmentRound.s21') : t('pages.settings.RecruitmentRound.s22')}`)
    loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.RecruitmentRound.s30'))
  }
}

onMounted(() => loadList())
</script>

<style scoped>
/* 模型 B：固定标题 + 内部滚动三件套（与 AccountSettings/DemandConfig 同款） */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header {
  flex-shrink: 0;
  /* 顶部/底部间距由全局 .settings-scroll .page-header（glass.css）统一提供：
     margin-top:0、padding-top:0，底部走 .page-body 的 gap（全局 .page-body>.page-header{margin-bottom:0} 兜底）。
     scoped 不再写 padding/margin，避免与全局叠加造成跨页顶部留白不一致（2026-09-30）。 */
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  /* 2026-08-30 UX 四改：gap 16px→12px，缓解 11 层嵌套 + 多 padding 叠加的视觉膨胀 */
  gap: var(--space-3);
}

.interview-round {
  /* 2026-08-30 UX 五改：容器外边距交还 SettingsLayout 统一管控（.settings-scroll 20px + 清零规则 !important），
     本处不再设 padding，避免与 .settings-scroll 叠加成 32px（见 SETTINGS_LAYOUT_DIAGNOSIS.md §2） */
}

/* 2026-08-29 UX 整改：行高统一 + 标签列中线对齐；X-05 严禁硬编码颜色 */
/* 2026-08-30 UX 三改：补 padding:6px 12px !important 把行内垂直空白从 Naive 默认 ~10px 收到 6px，让 row-height=44 真正生效。
   Naive UI 当前版本 themeOverrides 类型不含 tdPaddingMedium/thPaddingMedium（cssr vars 存在但未暴露给类型），
   全靠此 scoped CSS 兜底。 */
.interview-round :deep(.n-data-table .n-data-table-tr .n-data-table-td) {
  vertical-align: middle;
  padding: 6px 12px !important;
}
</style>
