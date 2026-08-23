<template>
  <div class="policy-admin">
    <!-- 左侧分类树 -->
    <aside class="policy-admin__side">
      <div class="policy-admin__side-header">政策制度</div>
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
          <p class="page-subtitle">制度公告的新增、编辑、推送与版本管理</p>
          <p class="policy-admin__desc">维护招聘专家可见的制度、公告与流程内容</p>
          <div class="kpi-row">
            <div class="kpi-card"><span class="kpi-label">公告总数</span><span class="kpi-value">{{ rows.length }}</span></div>
          </div>
        </div>
        <n-space>
          <n-button type="primary" @click="openCreate">添加文档</n-button>
        </n-space>
      </div>

      <!-- 工作台展示开关（模块总开关） -->
      <div class="policy-admin__config">
        <span class="policy-admin__config-text">工作台展示政策制度模块</span>
        <n-switch
          :value="configShowOnWorkbench"
          :loading="configSaving"
          @update:value="onToggleWorkbench"
        >
          <template #checked>展示</template>
          <template #unchecked>隐藏</template>
        </n-switch>
      </div>

      <!-- 筛选栏 -->
      <div class="policy-admin__filter">
        <n-input
          v-model:value="searchKeyword"
          placeholder="搜索文档名称"
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
          placeholder="发布状态"
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
                  <th class="col-name">文档名称</th>
                  <th class="col-scope">发布范围</th>
                  <th class="col-editor">最近修改人</th>
                  <th class="col-time">修改时间</th>
                  <th class="col-publish">是否发布</th>
                  <th class="col-place">展示位置</th>
                  <th class="col-actions">操作</th>
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
                        <span v-if="row.pinned" class="policy-doc-pinned">置顶</span>
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
                        :style="{ background: '#3b82f6', color: '#fff' }"
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
                      <n-tag v-if="row.showOnWorkbench" size="small" type="info" :bordered="false">工作台</n-tag>
                      <span v-else class="policy-place__none">不展示</span>
                    </div>
                  </td>
                  <td class="col-actions">
                    <div class="policy-actions">
                      <n-button tertiary type="primary" size="small" @click="openPush(row)">推送</n-button>
                      <n-button tertiary type="primary" size="small" @click="openEdit(row)">编辑</n-button>
                      <n-button color="#ff4d4f" text-color="#fff" size="small" @click="remove(row)">删除</n-button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <n-empty v-else description="暂无文档" />
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
          <span class="drawer-title">{{ editingId ? '编辑文档' : '添加文档' }}</span>
        </template>

        <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="84px">
          <n-form-item label="文档名称" path="title">
            <n-input v-model:value="form.title" placeholder="请输入文档名称" />
          </n-form-item>

          <n-form-item label="文档说明" path="body">
            <rich-editor v-model:html="form.body" placeholder="请输入文档说明" />
          </n-form-item>

          <n-form-item label="发布范围" path="audience">
            <n-radio-group v-model:value="form.audience">
              <n-space>
                <n-radio value="ALL">全体员工</n-radio>
                <n-radio value="RECRUIT_EXPERT">招聘专家</n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>

          <n-form-item label="分类" path="category">
            <n-select v-model:value="form.category" :options="categoryOptions" />
          </n-form-item>

          <n-form-item label="置顶文档" path="pinned">
            <n-radio-group v-model:value="form.pinned">
              <n-space>
                <n-radio :value="true">是</n-radio>
                <n-radio :value="false">否</n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>

          <n-form-item label="工作台展示">
            <n-radio-group v-model:value="form.showOnWorkbench">
              <n-space>
                <n-radio :value="true">是</n-radio>
                <n-radio :value="false">否</n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>

          <n-form-item label="上传附件">
            <div class="attach-block">
              <div v-for="att in currentAttachments" :key="att.id" class="attach-row">
                <div class="attach-row__icon">
                  <n-icon :component="DocumentTextOutline" :size="16" />
                </div>
                <span class="attach-name">{{ att.originalName }} <em>{{ formatSize(att.fileSize) }}</em></span>
                <n-button size="tiny" color="#ff4d4f" text-color="#fff" @click="removeExistingAttachment(att)">移除</n-button>
              </div>
              <div v-for="(f, i) in pendingFiles" :key="`new-${i}`" class="attach-row">
                <div class="attach-row__icon">
                  <n-icon :component="DocumentTextOutline" :size="16" />
                </div>
                <span class="attach-name">{{ f.name }} <em>{{ formatSize(f.size) }}</em></span>
                <n-button size="tiny" color="#ff4d4f" text-color="#fff" @click="pendingFiles.splice(i, 1)">移除</n-button>
              </div>
              <n-upload :show-file-list="false" multiple @before-upload="onBeforeUpload">
                <n-button size="small" tertiary>
                  <template #icon>
                    <n-icon :component="CloudUploadOutline" />
                  </template>
                  点击上传
                </n-button>
              </n-upload>
              <p class="attach-hint">支持 PDF、DOCX、PPT、ZIP 等格式，单文件 ≤ 10MB</p>
            </div>
          </n-form-item>

          <n-form-item label="发布时间" path="publishedAt">
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
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="save">确定</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <!-- 推送弹窗 -->
    <n-modal
      v-model:show="pushVisible"
      title="推送政策制度"
      preset="dialog"
      positive-text="确定"
      negative-text="取消"
      @positive-click="confirmPush"
      @negative-click="pushVisible = false"
    >
      <div class="push-body">
        <p class="push-desc">推送后，发布范围内的员工进入系统后将收到弹窗推送。</p>
        <n-checkbox v-model:checked="pushWithIM">IM 通知</n-checkbox>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
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

const message = useMessage()
const dialog = useDialog()

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
    { key: 'ALL', label: '全部文件', icon: GridOutline, count: rows.value.length },
    { key: 'SYSTEM', label: '制度', icon: FolderOpenOutline, count: counts.SYSTEM },
    { key: 'NOTICE', label: '公告', icon: FolderOpenOutline, count: counts.NOTICE },
    { key: 'PROCESS', label: '流程', icon: FolderOpenOutline, count: counts.PROCESS },
  ]
})

const currentFolderLabel = computed(() => {
  const node = treeNodes.value.find((n) => n.key === currentKey.value)
  return node?.label || '全部文件'
})

// 搜索与状态筛选
const searchKeyword = ref('')
const filterStatus = ref<boolean | null>(null)
const statusOptions = [
  { label: '已发布', value: true },
  { label: '已停用', value: false },
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
    message.success(value ? '已在工作台展示政策制度' : '已隐藏工作台政策制度模块')
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '配置保存失败')
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
const pendingFiles = ref<File[]>([])
const removedAttachmentIds = ref<string[]>([])
const currentAttachments = ref<AnnouncementAttachment[]>([])

const categoryOptions = [
  { label: '制度', value: 'SYSTEM' },
  { label: '公告', value: 'NOTICE' },
  { label: '流程', value: 'PROCESS' },
]

const rules = {
  title: { required: true, message: '请输入文档名称', trigger: 'blur' },
  body: { required: true, message: '请输入文档说明', trigger: 'blur' },
}

function openCreate() {
  editingId.value = null
  Object.assign(form, defaultForm())
  pendingFiles.value = []
  removedAttachmentIds.value = []
  currentAttachments.value = []
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
    message.success('已保存')
    drawerVisible.value = false
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
    message.success(value ? '已发布' : '已停用')
    await refresh()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '操作失败')
  }
}

function remove(row: Announcement) {
  dialog.warning({
    title: '删除文档',
    content: `确定删除「${row.title}」？删除后将从列表移除。`,
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
  message.success(`已向「${pushRow.value?.audienceDisplay || '发布范围'}」推送「${pushRow.value?.title}」`)
  pushVisible.value = false
}

async function refresh() {
  loading.value = true
  try {
    rows.value = await listAnnouncements({ show_inactive: true })
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
.policy-admin {
  display: flex;
  height: 100%;
  min-height: 0;
  background: #f5f7fa;
}

/* 左侧边栏 */
.policy-admin__side {
  width: 220px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #f0f0f0;
  padding: 20px 0;
}

.policy-admin__side-header {
  padding: 0 20px 16px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.policy-tree {
  display: flex;
  flex-direction: column;
}

.policy-tree__node {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  margin: 0 8px;
  border-radius: 6px;
  cursor: pointer;
  color: #4b5563;
  font-size: 14px;
  transition: background 0.15s, color 0.15s;
}

.policy-tree__node:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.policy-tree__node.active {
  background: #eff6ff;
  color: #2563eb;
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
  font-size: 12px;
  color: #9ca3af;
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 10px;
}

.policy-tree__node.active .policy-tree__count {
  background: #dbeafe;
  color: #2563eb;
}

/* 右侧主内容 */
.policy-admin__main {
  flex: 1;
  min-width: 0;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: auto;
}

.policy-admin__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.policy-admin__title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.policy-admin__desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.policy-admin__config {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.policy-admin__config-text {
  font-size: 14px;
  color: #374151;
}

.policy-admin__filter {
  display: flex;
  align-items: center;
  gap: 12px;
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
  font-size: 14px;
}

.policy-table th {
  text-align: left;
  color: #9ca3af;
  font-weight: 500;
  padding: 10px 12px;
  border-bottom: 1px solid #f0f0f0;
  white-space: nowrap;
  background: #fafafa;
}

.policy-table td {
  padding: 14px 12px;
  border-bottom: 1px solid #f5f5f5;
  color: #4b5563;
  vertical-align: middle;
}

.policy-table__row {
  transition: background 0.15s;
}

.policy-table__row:hover {
  background: #f8fafc;
}

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
  font-size: 12px;
  color: #9ca3af;
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
  background: #eff6ff;
  color: #3b82f6;
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
  gap: 8px;
}

.policy-doc-title {
  color: #1f2937;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.policy-doc-pinned {
  flex-shrink: 0;
  font-size: 11px;
  color: #ef4444;
  background: #fef2f2;
  padding: 1px 6px;
  border-radius: 4px;
}

.policy-editor {
  display: flex;
  align-items: center;
  gap: 8px;
}

.policy-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 抽屉内样式 */
.drawer-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.attach-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attach-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: #f9fafb;
  border-radius: 6px;
}

.attach-row__icon {
  color: #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
}

.attach-name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attach-name em {
  color: #9ca3af;
  font-style: normal;
  margin-left: 6px;
}

.attach-hint {
  margin: 0;
  font-size: 12px;
  color: #9ca3af;
}

/* 推送弹窗 */
.push-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.push-desc {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
}

@media (max-width: 900px) {
  .policy-admin__side {
    display: none;
  }
  .policy-admin__main {
    padding: 16px;
  }
}
</style>
