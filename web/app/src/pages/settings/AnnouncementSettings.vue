<template>
  <div class="announcement-admin">
    <div class="page-header">
      <div>
        <h1 class="page-title">制度公告</h1>
        <p class="page-desc">维护招聘专家可见的制度、公告与流程内容（HR 及以上可管理）。</p>
      </div>
      <n-button type="primary" @click="openCreate">新建公告</n-button>
    </div>

    <n-card class="config-card" :bordered="false">
      <div class="config-row">
        <div class="config-text">
          <div class="config-title">在工作台展示制度公告</div>
          <div class="config-desc">关闭后，招聘专家的工作台右侧将不再显示「制度公告」模块。</div>
        </div>
        <n-switch
          :value="configShowOnWorkbench"
          :loading="configSaving"
          @update:value="onToggleWorkbench"
        >
          <template #checked>展示</template>
          <template #unchecked>隐藏</template>
        </n-switch>
      </div>
    </n-card>

    <n-card class="admin-card" :bordered="false">
      <div class="table-toolbar">
        <n-segmented
          v-model:value="filterMode"
          :options="filterOptions"
          size="small"
          @update:value="onFilterChange"
        />
        <span class="table-toolbar__hint">此处展示全部历史公告（含已下架）</span>
      </div>
      <n-data-table
        :columns="columns"
        :data="rows"
        :loading="loading"
        :row-key="(row: any) => row.id"
        :pagination="false"
        size="small"
      />
    </n-card>

    <!-- 新建 / 编辑 弹窗 -->
    <n-modal
      v-model:show="showModal"
      :title="editingId ? '编辑公告' : '新建公告'"
      preset="card"
      style="width: 640px; max-width: 92vw;"
    >
      <n-form :model="form" :rules="rules" ref="formRef" label-placement="top">
        <n-form-item label="标题" path="title">
          <n-input v-model:value="form.title" placeholder="如：招聘需求提报规范（2026 版）" />
        </n-form-item>
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="分类" path="category">
              <n-select v-model:value="form.category" :options="categoryOptions" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="受众" path="audience">
              <n-select v-model:value="form.audience" :options="audienceOptions" />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-form-item label="正文" path="body">
          <n-input
            v-model:value="form.body"
            type="textarea"
            :autosize="{ minRows: 4, maxRows: 10 }"
            placeholder="支持多行文本"
          />
        </n-form-item>
        <n-form-item label="概述" path="summary">
          <n-input
            v-model:value="form.summary"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 5 }"
            placeholder="列表/工作台仅展示概述，建议一句话概括（可选）"
          />
        </n-form-item>
        <n-form-item label="附件">
          <div class="attach-block">
            <div v-for="att in currentAttachments" :key="att.id" class="attach-row">
              <span class="attach-name">📎 {{ att.originalName }} <em>{{ formatSize(att.fileSize) }}</em></span>
              <n-button size="tiny" text type="error" @click="removeExistingAttachment(att)">移除</n-button>
            </div>
            <div v-for="(f, i) in pendingFiles" :key="`new-${i}`" class="attach-row">
              <span class="attach-name">📎 {{ f.name }} <em>{{ formatSize(f.size) }}</em></span>
              <n-button size="tiny" text type="error" @click="pendingFiles.splice(i, 1)">移除</n-button>
            </div>
            <n-upload
              :show-file-list="false"
              multiple
              @before-upload="onBeforeUpload"
            >
              <n-button size="small" tertiary>选择文件</n-button>
            </n-upload>
            <p class="attach-hint">支持 PDF / Word / Excel / PPT / 图片 / 压缩包，单文件 ≤ 10MB</p>
          </div>
        </n-form-item>
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="发布时间" path="publishedAt">
              <n-date-picker
                v-model:value="form.publishedAt"
                type="datetime"
                clearable
                style="width: 100%;"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="置顶 / 上架">
              <n-space align="center">
                <n-switch v-model:value="form.pinned"><template #checked>置顶</template><template #unchecked>普通</template></n-switch>
                <n-switch v-model:value="form.isActive"><template #checked>上架</template><template #unchecked>下架</template></n-switch>
              </n-space>
            </n-form-item>
          </n-grid-item>
        </n-grid>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="save">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 查看详情 抽屉（只读） -->
    <n-drawer v-model:show="detailVisible" :width="460" placement="right" :trap-focus="false">
      <n-drawer-content :native-scrollbar="false">
        <template #header>
          <span class="ann-detail__title">{{ detailItem?.title }}</span>
        </template>
        <div v-if="detailItem" class="ann-detail">
          <div class="ann-detail__meta">
            <n-tag size="small" :type="detailItem.category === 'NOTICE' ? 'success' : detailItem.category === 'PROCESS' ? 'warning' : 'info'" round>{{ detailItem.categoryDisplay }}</n-tag>
            <n-tag size="small" round>{{ detailItem.audienceDisplay }}</n-tag>
            <span class="ann-detail__time">{{ fmtTime(detailItem.publishedAt) }}</span>
          </div>
          <p class="ann-detail__body">{{ detailItem.body }}</p>
          <div v-if="detailItem.attachments && detailItem.attachments.length" class="ann-detail__attachments">
            <div class="ann-detail__attach-title">附件</div>
            <a
              v-for="att in detailItem.attachments"
              :key="att.id"
              class="ann-detail__attach"
              :href="att.fileUrl"
              target="_blank"
              rel="noopener"
            >
              <span class="ann-detail__attach-name">📎 {{ att.originalName }}</span>
              <span class="ann-detail__attach-size">{{ formatSize(att.fileSize) }}</span>
            </a>
          </div>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NTag,
  NSpace,
  NSwitch,
  useDialog,
  useMessage,
} from 'naive-ui'
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

const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const saving = ref(false)
const rows = ref<Announcement[]>([])

// 附件上传：待上传文件 / 编辑时标记删除的已有附件 / 当前已有的附件
const pendingFiles = ref<File[]>([])
const removedAttachmentIds = ref<string[]>([])
const currentAttachments = ref<AnnouncementAttachment[]>([])
// 查看详情抽屉
const detailVisible = ref(false)
const detailItem = ref<Announcement | null>(null)

// 模块设置：工作台展示开关（后台配置）
const configShowOnWorkbench = ref(true)
const configSaving = ref(false)

// 历史筛选：全部(含已下架) / 仅上架
const filterMode = ref<'all' | 'active'>('all')
const filterOptions = [
  { label: '全部历史', value: 'all' },
  { label: '仅上架', value: 'active' },
]

async function onToggleWorkbench(value: boolean) {
  configSaving.value = true
  try {
    const cfg = await updateAnnouncementConfig({ showOnWorkbench: value })
    configShowOnWorkbench.value = cfg.showOnWorkbench
    message.success(value ? '已在工作台展示制度公告' : '已隐藏工作台制度公告模块')
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '配置保存失败')
  } finally {
    configSaving.value = false
  }
}

function onFilterChange() {
  void refresh()
}

const categoryOptions = [
  { label: '制度', value: 'SYSTEM' },
  { label: '公告', value: 'NOTICE' },
  { label: '流程', value: 'PROCESS' },
]
const audienceOptions = [
  { label: '招聘专家', value: 'RECRUIT_EXPERT' },
  { label: '全员', value: 'ALL' },
]

function fmtTime(iso?: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

const columns = [
  {
    title: '置顶',
    key: 'pinned',
    width: 64,
    render: (row: Announcement) =>
      row.pinned ? h(NTag, { type: 'error', size: 'small', round: true }, { default: () => '置顶' }) : h('span', {}, '-'),
  },
  { title: '标题', key: 'title', ellipsis: { tooltip: true } },
  {
    title: '概述',
    key: 'summary',
    ellipsis: { tooltip: true },
    render: (row: Announcement) => row.summary || '-',
  },
  {
    title: '分类',
    key: 'categoryDisplay',
    width: 90,
    render: (row: Announcement) => h(NTag, { size: 'small', type: 'info' }, { default: () => row.categoryDisplay }),
  },
  {
    title: '受众',
    key: 'audienceDisplay',
    width: 100,
    render: (row: Announcement) => h(NTag, { size: 'small' }, { default: () => row.audienceDisplay }),
  },
  {
    title: '上架',
    key: 'isActive',
    width: 80,
    render: (row: Announcement) =>
      h(NSwitch, {
        value: row.isActive,
        onUpdateValue: (v: boolean) => toggleActive(row, v),
      }),
  },
  { title: '发布时间', key: 'publishedAt', width: 140, render: (row: Announcement) => fmtTime(row.publishedAt) },
  {
    title: '操作',
    key: 'actions',
    width: 130,
    render: (row: Announcement) =>
      h(NSpace, {}, {
        default: () => [
          h(NButton, { size: 'small', tertiary: true, onClick: () => openDetail(row) }, { default: () => '查看' }),
          h(NButton, { size: 'small', tertiary: true, onClick: () => openEdit(row) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', tertiary: true, type: 'error', onClick: () => remove(row) }, { default: () => '删除' }),
        ],
      }),
  },
]

// ===== 弹窗表单 =====
const showModal = ref(false)
const editingId = ref<string | null>(null)
const formRef = ref<any>(null)
const defaultForm = () => ({
  title: '',
  category: 'SYSTEM' as AnnouncementCategory,
  audience: 'RECRUIT_EXPERT' as AnnouncementAudience,
  body: '',
  summary: '',
  pinned: false,
  isActive: true,
  publishedAt: Date.now(),
})
const form = reactive(defaultForm())

const rules = {
  title: { required: true, message: '请输入标题', trigger: 'blur' },
  body: { required: true, message: '请输入正文', trigger: 'blur' },
}

function openCreate() {
  editingId.value = null
  Object.assign(form, defaultForm())
  pendingFiles.value = []
  removedAttachmentIds.value = []
  currentAttachments.value = []
  showModal.value = true
}

function openEdit(row: Announcement) {
  editingId.value = row.id
  Object.assign(form, {
    title: row.title,
    category: row.category,
    audience: row.audience,
    body: row.body,
    summary: row.summary || '',
    pinned: row.pinned,
    isActive: row.isActive,
    publishedAt: row.publishedAt ? new Date(row.publishedAt).getTime() : Date.now(),
  })
  pendingFiles.value = []
  removedAttachmentIds.value = []
  currentAttachments.value = row.attachments ? [...row.attachments] : []
  showModal.value = true
}

function openDetail(row: Announcement) {
  detailItem.value = row
  detailVisible.value = true
}

function formatSize(bytes: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

// 选文件时仅收集到 pendingFiles，保存时统一上传（阻止 n-upload 自动上传）。
function onBeforeUpload(data: { file: { file?: File } }): boolean {
  const f = data?.file?.file
  if (f) pendingFiles.value.push(f)
  return false
}

function removeExistingAttachment(att: AnnouncementAttachment) {
  currentAttachments.value = currentAttachments.value.filter((a) => a.id !== att.id)
  if (editingId.value) removedAttachmentIds.value.push(att.id)
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
    summary: form.summary.trim(),
    body: form.body,
    pinned: form.pinned,
    isActive: form.isActive,
    publishedAt: form.publishedAt ? new Date(form.publishedAt).toISOString() : new Date().toISOString(),
  }
  try {
    let saved: Announcement
    if (editingId.value) {
      saved = await updateAnnouncement(editingId.value, payload)
      // 删除被标记的已有附件
      for (const aid of removedAttachmentIds.value) {
        await deleteAnnouncementAttachment(editingId.value, aid)
      }
    } else {
      saved = await createAnnouncement(payload)
    }
    // 上传待上传附件
    for (const f of pendingFiles.value) {
      await uploadAnnouncementAttachment(saved.id, f)
    }
    message.success('已保存')
    showModal.value = false
    await refresh()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleActive(row: Announcement, value: boolean) {
  try {
    await updateAnnouncement(row.id, { isActive: value })
    message.success(value ? '已上架' : '已下架')
    await refresh()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '操作失败')
  }
}

function remove(row: Announcement) {
  dialog.warning({
    title: '删除公告',
    content: `确定删除「${row.title}」？删除后将从列表移除（可保留审计）。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteAnnouncement(row.id)
        message.success('已删除')
        await refresh()
      } catch (e: any) {
        message.error(e?.response?.data?.detail || '删除失败')
      }
    },
  })
}

async function refresh() {
  loading.value = true
  try {
    rows.value = await listAnnouncements({ show_inactive: filterMode.value === 'all' })
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '加载失败')
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
.announcement-admin {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
}
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
}
.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}
.page-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}
.admin-card {
  flex: 1;
  min-height: 0;
}

/* ===== 模块设置卡片 ===== */
.config-card {
  flex-shrink: 0;
}
.config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.config-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}
.config-desc {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
}

/* ===== 表格工具条 ===== */
.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.table-toolbar__hint {
  font-size: 12px;
  color: #9ca3af;
}
</style>
