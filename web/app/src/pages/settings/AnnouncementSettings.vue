<template>
  <div class="page-container policy-admin">
    <!-- 左侧分类树 -->
    <aside class="policy-admin__side">
      <div class="policy-admin__side-header">{{ t('pages.settings.AnnouncementSettings.s1') }}</div>
      <nav class="policy-tree">
        <div
          v-for="node in treeNodes"
          :key="node.key"
          class="policy-tree__node"
          :class="{ active: currentKey === node.key }"
          role="button"
          tabindex="0"
          @click="currentKey = node.key"
          @keydown.enter="currentKey = node.key"
        >
          <n-icon :component="node.icon" :size="16" class="policy-tree__icon" />
          <span class="policy-tree__label">{{ node.label }}</span>
          <span v-if="node.count != null" class="policy-tree__count">{{ node.count }}</span>
        </div>
      </nav>
    </aside>

    <!-- 右侧主内容 -->
    <main class="policy-admin__main">
      <div class="policy-admin__header">
        <div>
          <h1 class="policy-admin__title page-title">{{ currentFolderLabel }}</h1>
          <p class="page-subtitle">{{ t('pages.settings.AnnouncementSettings.s2') }}</p>
          <p class="policy-admin__desc">{{ t('pages.settings.AnnouncementSettings.s3') }}</p>
          <div class="kpi-row">
            <div class="kpi-card"><span class="kpi-label">{{ t('pages.settings.AnnouncementSettings.s4') }}</span><span class="kpi-value">{{ rows.length }}</span></div>
          </div>
        </div>
        <n-space>
          <n-button type="primary" @click="openCreate">{{ t('pages.settings.AnnouncementSettings.s5') }}</n-button>
        </n-space>
      </div>

      <!-- 工作台展示开关（模块总开关） -->
      <div class="policy-admin__config">
        <span class="policy-admin__config-text">{{ t('pages.settings.AnnouncementSettings.s6') }}</span>
        <n-switch
          :value="configShowOnWorkbench"
          :loading="configSaving"
          @update:value="onToggleWorkbench"
        >
          <template #checked>{{ t('pages.settings.AnnouncementSettings.s48') }}</template>
          <template #unchecked>{{ t('pages.settings.AnnouncementSettings.s49') }}</template>
        </n-switch>
      </div>

      <!-- 筛选栏 -->
      <div class="policy-admin__filter">
        <n-input
          v-model:value="searchKeyword"
          :placeholder="t('pages.settings.AnnouncementSettings.s7')"
          clearable
          style="width: 260px;"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
        </n-input>
        <n-select
          v-model:value="filterStatus"
          :options="statusOptions"
          :placeholder="t('pages.settings.AnnouncementSettings.s8')"
          clearable
          style="width: 140px;"
        />
      </div>

      <!-- 表格 -->
      <n-card class="policy-table-card" :bordered="false">
        <n-spin :show="loading">
          <div v-if="filteredRows.length > 0" class="policy-table-wrap">
            <table class="policy-table">
              <thead>
                <tr>
                  <th class="col-name">{{ t('pages.settings.AnnouncementSettings.s9') }}</th>
                  <th class="col-scope">{{ t('pages.settings.AnnouncementSettings.s10') }}</th>
                  <th class="col-editor">{{ t('pages.settings.AnnouncementSettings.s11') }}</th>
                  <th class="col-time">{{ t('pages.settings.AnnouncementSettings.s12') }}</th>
                  <th class="col-publish">{{ t('pages.settings.AnnouncementSettings.s13') }}</th>
                  <th class="col-place">{{ t('pages.settings.AnnouncementSettings.s14') }}</th>
                  <th class="col-actions">{{ t('pages.settings.AnnouncementSettings.s15') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in filteredRows" :key="row.id" class="policy-table__row">
                  <td class="col-name">
                    <div class="policy-doc-cell">
                      <div class="policy-doc-icon">
                        <n-icon :component="DocumentTextOutline" :size="18" />
                      </div>
                      <div class="policy-doc-info">
                        <span class="policy-doc-title" :title="row.title">{{ row.title }}</span>
                        <span v-if="row.pinned" class="policy-doc-pinned">{{ t('pages.settings.AnnouncementSettings.s16') }}</span>
                      </div>
                    </div>
                  </td>
                  <td class="col-scope">{{ row.audienceDisplay }}</td>
                  <td class="col-editor">
                    <div class="policy-editor">
                      <n-avatar
                        v-if="row.updatedByName"
                        round
                        :size="22"
                        :style="{ background: 'var(--c-info)', color: 'var(--g1)' }"
                      >
                        {{ initials(row.updatedByName) }}
                      </n-avatar>
                      <span>{{ row.updatedByName || '-' }}</span>
                    </div>
                  </td>
                  <td class="col-time">{{ fmtDate(row.updatedAt) }}</td>
                  <td class="col-publish">
                    <n-switch :value="row.isActive" @update:value="(v) => toggleActive(row, v)" />
                  </td>
                  <td class="col-place">
                    <div class="policy-place">
                      <n-tag v-if="row.showOnWorkbench" size="small" type="info" :bordered="false">{{ t('pages.settings.AnnouncementSettings.s17') }}</n-tag>
                      <span v-else class="policy-place__none">{{ t('pages.settings.AnnouncementSettings.s18') }}</span>
                    </div>
                  </td>
                  <td class="col-actions">
                    <div class="policy-actions">
                      <n-button tertiary type="primary" size="small" @click="openPush(row)">{{ t('pages.settings.AnnouncementSettings.s19') }}</n-button>
                      <n-button tertiary type="primary" size="small" @click="openEdit(row)">{{ t('pages.settings.AnnouncementSettings.s50') }}</n-button>
                      <n-button type="error" size="small" @click="remove(row)">{{ t('pages.settings.AnnouncementSettings.s20') }}</n-button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <n-empty v-else :description="t('pages.settings.AnnouncementSettings.s21')" />
        </n-spin>
      </n-card>
    </main>

    <!-- 添加/编辑 抽屉 -->
    <n-drawer
      v-model:show="drawerVisible"
      :width="560"
      placement="right"
      :trap-focus="false"
    >
      <n-drawer-content :native-scrollbar="false">
        <template #header>
          <span class="drawer-title">{{ editingId ? t('pages.settings.AnnouncementSettings.s51') : t('pages.settings.AnnouncementSettings.s52') }}</span>
        </template>

        <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="84px">
          <n-form-item :label="t('pages.settings.AnnouncementSettings.s22')" path="title">
            <n-input v-model:value="form.title" :placeholder="t('pages.settings.AnnouncementSettings.s23')" />
          </n-form-item>

          <n-form-item :label="t('pages.settings.AnnouncementSettings.s24')" path="body">
            <rich-editor v-model:html="form.body" :placeholder="t('pages.settings.AnnouncementSettings.s25')" />
          </n-form-item>

          <n-form-item :label="t('pages.settings.AnnouncementSettings.s26')" path="audience">
            <n-radio-group v-model:value="form.audience">
              <n-space>
                <n-radio value="ALL">{{ t('pages.settings.AnnouncementSettings.s27') }}</n-radio>
                <n-radio value="RECRUIT_EXPERT">{{ t('pages.settings.AnnouncementSettings.s28') }}</n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>

          <n-form-item :label="t('pages.settings.AnnouncementSettings.s29')" path="category">
            <n-select v-model:value="form.category" :options="categoryOptions" />
          </n-form-item>

          <n-form-item :label="t('pages.settings.AnnouncementSettings.s30')" path="pinned">
            <n-radio-group v-model:value="form.pinned">
              <n-space>
                <n-radio :value="true">{{ t('pages.settings.AnnouncementSettings.s31') }}</n-radio>
                <n-radio :value="false">{{ t('pages.settings.AnnouncementSettings.s32') }}</n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>

          <n-form-item :label="t('pages.settings.AnnouncementSettings.s33')">
            <n-radio-group v-model:value="form.showOnWorkbench">
              <n-space>
                <n-radio :value="true">{{ t('pages.settings.AnnouncementSettings.s34') }}</n-radio>
                <n-radio :value="false">{{ t('pages.settings.AnnouncementSettings.s35') }}</n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>

          <n-form-item :label="t('pages.settings.AnnouncementSettings.s36')">
            <div class="attach-block">
              <div v-for="att in currentAttachments" :key="att.id" class="attach-row">
                <div class="attach-row__icon">
                  <n-icon :component="DocumentTextOutline" :size="16" />
                </div>
                <span class="attach-name">{{ att.originalName }} <em>{{ formatSize(att.fileSize) }}</em></span>
                <n-button size="tiny" type="error" @click="removeExistingAttachment(att)">{{ t('pages.settings.AnnouncementSettings.s53') }}</n-button>
              </div>
              <div v-for="(f, i) in pendingFiles" :key="`new-${i}`" class="attach-row">
                <div class="attach-row__icon">
                  <n-icon :component="DocumentTextOutline" :size="16" />
                </div>
                <span class="attach-name">{{ f.name }} <em>{{ formatSize(f.size) }}</em></span>
                <n-button size="tiny" type="error" @click="undoRemovePendingFile(i, f)">{{ t('pages.settings.AnnouncementSettings.s37') }}</n-button>
              </div>
              <n-upload :show-file-list="false" multiple @before-upload="onBeforeUpload">
                <n-button size="small" tertiary>
                  <template #icon>
                    <n-icon :component="CloudUploadOutline" />
                  </template>
                  {{ t('pages.settings.AnnouncementSettings.s38') }}
                </n-button>
              </n-upload>
              <p class="attach-hint">{{ t('pages.settings.AnnouncementSettings.s39') }}</p>
            </div>
          </n-form-item>

          <n-form-item :label="t('pages.settings.AnnouncementSettings.s40')" path="publishedAt">
            <n-date-picker
              v-model:value="form.publishedAt"
              type="datetime"
              clearable
              style="width: 100%;"
            />
          </n-form-item>
        </n-form>

        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">{{ t('pages.settings.AnnouncementSettings.s41') }}</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="save">{{ t('pages.settings.AnnouncementSettings.s42') }}</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <!-- 推送弹窗 -->
    <n-modal
      v-model:show="pushVisible"
      :title="t('pages.settings.AnnouncementSettings.s43')"
      preset="dialog"
      :positive-text="t('pages.settings.AnnouncementSettings.s44')"
      :negative-text="t('pages.settings.AnnouncementSettings.s45')"
      @positive-click="confirmPush"
      @negative-click="pushVisible = false"
    >
      <div class="push-body">
        <p class="push-desc">{{ t('pages.settings.AnnouncementSettings.s46') }}</p>
        <n-checkbox v-model:checked="pushWithIM">{{ t('pages.settings.AnnouncementSettings.s47') }}</n-checkbox>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NTag,
  NSwitch,
  NSpace,
  NAvatar,
  NRadio,
  NRadioGroup,
  useDialog,
  useMessage,
} from 'naive-ui'
import {
  SearchOutline,
  DocumentTextOutline,
  FolderOpenOutline,
  GridOutline,
  TimeOutline,
  CloudUploadOutline,
} from '@vicons/ionicons5'
import RichEditor from '../../components/RichEditor.vue'
import {
  listAnnouncements,
  createAnnouncement,
  updateAnnouncement,
  deleteAnnouncement,
  uploadAnnouncementAttachment,
  deleteAnnouncementAttachment,
  getAnnouncementConfig,
  updateAnnouncementConfig,
  type Announcement,
  type AnnouncementAttachment,
  type AnnouncementCategory,
  type AnnouncementAudience,
} from '../../api/announcement'
import { useUndo } from '../../composables/useUndo'
import { useDraft } from '../../composables/useDraft'
const { t } = useI18n()

const message = useMessage()
const dialog = useDialog()
const { undoable } = useUndo()

const loading = ref(false)
const saving = ref(false)
const rows = ref<Announcement[]>([])

// 分类树
const currentKey = ref<string>('ALL')
const treeNodes = computed(() => {
  const counts = {
    SYSTEM: rows.value.filter((r) => r.category === 'SYSTEM').length,
    NOTICE: rows.value.filter((r) => r.category === 'NOTICE').length,
    PROCESS: rows.value.filter((r) => r.category === 'PROCESS').length,
  }
  return [
    { key: 'ALL', label: t('pages.settings.AnnouncementSettings.s54'), icon: GridOutline, count: rows.value.length },
    { key: 'SYSTEM', label: t('pages.settings.AnnouncementSettings.s55'), icon: FolderOpenOutline, count: counts.SYSTEM },
    { key: 'NOTICE', label: t('pages.settings.AnnouncementSettings.s56'), icon: FolderOpenOutline, count: counts.NOTICE },
    { key: 'PROCESS', label: t('pages.settings.AnnouncementSettings.s57'), icon: FolderOpenOutline, count: counts.PROCESS },
  ]
})

const currentFolderLabel = computed(() => {
  const node = treeNodes.value.find((n) => n.key === currentKey.value)
  return node?.label || t('pages.settings.AnnouncementSettings.s54')
})

// 搜索与状态筛选
const searchKeyword = ref('')
const filterStatus = ref<boolean | null>(null)
const statusOptions = [
  { label: t('pages.settings.AnnouncementSettings.s58'), value: true },
  { label: t('pages.settings.AnnouncementSettings.s59'), value: false },
]

const filteredRows = computed(() => {
  let list = rows.value
  if (currentKey.value !== 'ALL') {
    list = list.filter((r) => r.category === currentKey.value)
  }
  if (filterStatus.value !== null) {
    list = list.filter((r) => r.isActive === filterStatus.value)
  }
  if (searchKeyword.value.trim()) {
    const kw = searchKeyword.value.trim().toLowerCase()
    list = list.filter((r) => r.title.toLowerCase().includes(kw))
  }
  return list
})

// 模块设置
const configShowOnWorkbench = ref(true)
const configSaving = ref(false)

async function onToggleWorkbench(value: boolean) {
  configSaving.value = true
  try {
    const cfg = await updateAnnouncementConfig({ showOnWorkbench: value })
    configShowOnWorkbench.value = cfg.showOnWorkbench
    message.success(value ? t('pages.settings.AnnouncementSettings.s60') : t('pages.settings.AnnouncementSettings.s61'))
  } catch (e: any) {
    message.error(e?.response?.data?.detail || t('pages.settings.AnnouncementSettings.s62'))
  } finally {
    configSaving.value = false
  }
}

// 表单
const drawerVisible = ref(false)
const editingId = ref<string | null>(null)
const formRef = ref<any>(null)
const defaultForm = () => ({
  title: '',
  category: 'SYSTEM' as AnnouncementCategory,
  audience: 'ALL' as AnnouncementAudience,
  body: '',
  pinned: false,
  isActive: true,
  showOnWorkbench: true,
  publishedAt: Date.now(),
})
const form = reactive(defaultForm())
const { restore: restoreDraft, clear: clearDraft } = useDraft(form, {
  key: 'announcement-edit',
  isEmpty: (v) => !v.title && !v.body,
})
const pendingFiles = ref<File[]>([])
const removedAttachmentIds = ref<string[]>([])
const currentAttachments = ref<AnnouncementAttachment[]>([])

const categoryOptions = [
  { label: t('pages.settings.AnnouncementSettings.s55'), value: 'SYSTEM' },
  { label: t('pages.settings.AnnouncementSettings.s56'), value: 'NOTICE' },
  { label: t('pages.settings.AnnouncementSettings.s57'), value: 'PROCESS' },
]

const rules = {
  title: { required: true, message: t('pages.settings.AnnouncementSettings.s23'), trigger: 'blur' },
  body: { required: true, message: t('pages.settings.AnnouncementSettings.s25'), trigger: 'blur' },
}

function openCreate() {
  editingId.value = null
  const hadDraft = restoreDraft()
  if (!hadDraft) Object.assign(form, defaultForm())
  pendingFiles.value = []
  removedAttachmentIds.value = []
  currentAttachments.value = []
  drawerVisible.value = true
  if (hadDraft) {
    // Naive UI MessageOptions 无 action 字段，使用官方支持的 render 自定义内容
    let inst: ReturnType<typeof message.info> | undefined
    const doClear = () => {
      clearDraft()
      inst?.destroy()
    }
    inst = message.info('', {
      duration: 5000,
      render: () =>
        h(
          'div',
          { style: 'display:flex;align-items:center;gap:8px;' },
          [
            h('span', { style: 'flex:1;' }, t('pages.settings.AnnouncementSettings.s63')),
            h(
              NButton,
              { size: 'small', text: true, type: 'primary', onClick: doClear },
              { default: () => t('pages.settings.AnnouncementSettings.s64') },
            ),
          ],
        ),
    })
  }
  drawerVisible.value = true
}

function openEdit(row: Announcement) {
  editingId.value = row.id
  Object.assign(form, {
    title: row.title,
    category: row.category,
    audience: row.audience,
    body: row.body,
    pinned: row.pinned,
    isActive: row.isActive,
    showOnWorkbench: row.showOnWorkbench,
    publishedAt: row.publishedAt ? new Date(row.publishedAt).getTime() : Date.now(),
  })
  pendingFiles.value = []
  removedAttachmentIds.value = []
  currentAttachments.value = row.attachments ? [...row.attachments] : []
  drawerVisible.value = true
}

function initials(name: string): string {
  return name.slice(0, 1).toUpperCase()
}

function fmtDate(iso?: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function formatSize(bytes: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

function onBeforeUpload(data: { file: { file?: File } }): boolean {
  const f = data?.file?.file
  if (f) pendingFiles.value.push(f)
  return false
}

function removeExistingAttachment(att: AnnouncementAttachment) {
  currentAttachments.value = currentAttachments.value.filter((a) => a.id !== att.id)
  if (editingId.value) removedAttachmentIds.value.push(att.id)
}

// 中等破坏性操作（R-106）：直接移除待上传附件 + Toast 撤销（5-8s 内可恢复）
function undoRemovePendingFile(i: number, f: File) {
  if (i < 0 || i >= pendingFiles.value.length) return
  pendingFiles.value.splice(i, 1)
  undoable(`t('pages.settings.AnnouncementSettings.s65') + '「' + f.name + '」'`, () => {
    const idx = Math.min(i, pendingFiles.value.length)
    pendingFiles.value.splice(idx, 0, f)
  })
}

async function save() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  saving.value = true
  const payload = {
    title: form.title.trim(),
    category: form.category,
    audience: form.audience,
    summary: '',
    body: form.body,
    pinned: form.pinned,
    isActive: form.isActive,
    showOnWorkbench: form.showOnWorkbench,
    publishedAt: form.publishedAt ? new Date(form.publishedAt).toISOString() : new Date().toISOString(),
  }
  try {
    let saved: Announcement
    if (editingId.value) {
      saved = await updateAnnouncement(editingId.value, payload)
      for (const aid of removedAttachmentIds.value) {
        await deleteAnnouncementAttachment(editingId.value, aid)
      }
    } else {
      saved = await createAnnouncement(payload)
    }
    for (const f of pendingFiles.value) {
      await uploadAnnouncementAttachment(saved.id, f)
    }
    message.success(t('pages.settings.AnnouncementSettings.s66'))
    drawerVisible.value = false
    await refresh()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || e?.message || t('pages.settings.AnnouncementSettings.s67'))
  } finally {
    saving.value = false
  }
}

async function toggleActive(row: Announcement, value: boolean) {
  try {
    await updateAnnouncement(row.id, { isActive: value })
    message.success(value ? t('pages.settings.AnnouncementSettings.s58') : t('pages.settings.AnnouncementSettings.s59'))
    await refresh()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || t('pages.settings.AnnouncementSettings.s68'))
  }
}

function remove(row: Announcement) {
  const btn = reactive({ loading: false })
  dialog.warning({
    title: t('pages.settings.AnnouncementSettings.s69'),
    content: `t('pages.settings.AnnouncementSettings.s70') + row.title + t('pages.settings.AnnouncementSettings.s71')`,
    positiveText: t('pages.settings.AnnouncementSettings.s20'),
    negativeText: t('pages.settings.AnnouncementSettings.s41'),
    positiveButtonProps: btn,
    onPositiveClick: async () => {
      if (btn.loading) return false
      btn.loading = true
      try {
        await deleteAnnouncement(row.id)
        message.success(t('pages.settings.AnnouncementSettings.s72'))
        await refresh()
      } catch (e: any) {
        message.error(e?.response?.data?.detail || t('pages.settings.AnnouncementSettings.s73'))
        return false
      } finally {
        btn.loading = false
      }
    },
  })
}

// 推送
const pushVisible = ref(false)
const pushRow = ref<Announcement | null>(null)
const pushWithIM = ref(false)

function openPush(row: Announcement) {
  pushRow.value = row
  pushWithIM.value = false
  pushVisible.value = true
}

function confirmPush() {
  // TODO: 接入后端推送 API
  message.success(`t('pages.settings.AnnouncementSettings.s74')({ aud: pushRow.value?.audienceDisplay || t('pages.settings.AnnouncementSettings.s10'), title: pushRow.value?.title })`)
  pushVisible.value = false
}

async function refresh() {
  loading.value = true
  try {
    rows.value = await listAnnouncements({ show_inactive: true })
  } catch (e: any) {
    message.error(e?.response?.data?.detail || t('pages.settings.AnnouncementSettings.s75'))
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function fetchConfig() {
  try {
    const cfg = await getAnnouncementConfig()
    if (typeof cfg?.showOnWorkbench === 'boolean') {
      configShowOnWorkbench.value = cfg.showOnWorkbench
    }
  } catch {
    // 读取失败保持默认
  }
}

onMounted(() => {
  void refresh()
  void fetchConfig()
})
</script>

<style scoped>
.policy-admin {
  display: flex;
  height: 100%;
  min-height: 0;
  background: var(--surface);}

/* 左侧边栏 */
.policy-admin__side {
  width: 220px;
  flex-shrink: 0;
  background: var(--glass-bg-card);
  border-right: 1px solid var(--glass-border);
  padding: 20px 0;
}

.policy-admin__side-header {
  padding: 0 20px var(--space-4);
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink);
}

.policy-tree {
  display: flex;
  flex-direction: column;
}

.policy-tree__node {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 10px 20px;
  margin: 0 var(--space-2);
  border-radius: 6px;
  cursor: pointer;
  color: var(--ink-soft);
  font-size: var(--fs-14);
  transition: background 0.15s, color 0.15s;
}

.policy-tree__node:hover {
  background: var(--g1);
  color: var(--n-800);}

.policy-tree__node.active {
  background: var(--brand-a22);
  color: var(--brand);
  font-weight: 500;
}

.policy-tree__icon {
  flex-shrink: 0;
}

.policy-tree__label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.policy-tree__count {
  font-size: var(--fs-12);
  color: var(--n-380);
  background: var(--g1);  padding: 1px 6px;
  border-radius: 10px;
}

.policy-tree__node.active .policy-tree__count {
  background: var(--brand-a22);
  color: var(--brand);
}

/* 右侧主内容 */
.policy-admin__main {
  flex: 1;
  min-width: 0;
  padding: 20px var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  overflow: auto;
}

.policy-admin__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.policy-admin__title {
  margin: 0;
  font-size: var(--fs-18);
  font-weight: 600;
  color: var(--ink);
}

.policy-admin__desc {
  margin: var(--space-1) 0 0;
  font-size: var(--fs-13);
  color: var(--ink-soft);
}

.policy-admin__config {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--glass-bg-card);
  border-radius: 8px;
  border: 1px solid var(--glass-border);
}

.policy-admin__config-text {
  font-size: var(--fs-14);
  color: var(--ink);
}

.policy-admin__filter {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.policy-table-card {
  flex: 1;
  min-height: 0;
  border-radius: 8px;
}

/* 表格 */
.policy-table-wrap {
  overflow-x: auto;
}

.policy-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-14);
}

.policy-table th {
  text-align: left;
  color: var(--ink-faint);
  font-weight: 500;
  padding: 10px var(--space-3);
  border-bottom: 1px solid var(--glass-border);
  white-space: nowrap;
  background: var(--g1);}

.policy-table td {
  padding: 14px var(--space-3);
  border-bottom: 1px solid var(--border-hairline);
  color: var(--ink-soft);
  vertical-align: middle;
}

.policy-table__row {
  transition: background 0.15s;
}

.policy-table__row:hover {
  background: var(--brand-tint);}

.policy-table__row:last-child td {
  border-bottom: none;
}

.col-name {
  width: 32%;
}

.col-scope {
  width: 16%;
}

.col-editor {
  width: 14%;
}

.col-time {
  width: 14%;
  white-space: nowrap;
}

.col-publish {
  width: 12%;
}

.col-place {
  width: 14%;
  white-space: nowrap;
}

.col-actions {
  width: 12%;
  white-space: nowrap;
}

.policy-place {
  display: flex;
  align-items: center;
  gap: 6px;
}

.policy-place__none {
  font-size: var(--fs-12);
  color: var(--ink-faint);
}

.policy-doc-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.policy-doc-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: var(--brand-a22);
  color: var(--c-info);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.policy-doc-info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.policy-doc-title {
  color: var(--ink);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.policy-doc-pinned {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--c-error);
  background: var(--c-error-soft);
  padding: 1px 6px;
  border-radius: 4px;
}

.policy-editor {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.policy-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 抽屉内样式 */
.drawer-title {
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink);
}

.attach-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.attach-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) 10px;
  background: var(--g1);  border-radius: 6px;
}

.attach-row__icon {
  color: var(--c-info);
  display: flex;
  align-items: center;
  justify-content: center;
}

.attach-name {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-13);
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attach-name em {
  color: var(--ink-faint);
  font-style: normal;
  margin-left: 6px;
}

.attach-hint {
  margin: 0;
  font-size: var(--fs-12);
  color: var(--ink-faint);
}

/* 推送弹窗 */
.push-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.push-desc {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--fs-14);
}

@media (max-width: 900px) {
  .policy-admin__side {
    display: none;
  }
  .policy-admin__main {
    padding: var(--space-4);
  }
}
</style>
