<template>
  <div class="page-container">
    <div class="page-body">
      <div class="toolbar">
        <div class="filter">
          <span class="filter-label">关键词</span>
          <n-input
            v-model:value="keyword"
            aria-label="关键词"
            class="toolbar-search"
            placeholder="搜索帖子标题或正文"
            clearable
            @keyup.enter="loadPosts"
          >
            <template #prefix><n-icon :component="SearchOutline" /></template>
          </n-input>
        </div>
        <div class="spacer"></div>
        <n-button :loading="postLoading" @click="loadPosts">查询帖子</n-button>
        <n-button type="primary" @click="openPostCreate">
          <template #icon><n-icon :component="AddOutline" /></template>
          发布帖子
        </n-button>
      </div>

      <!-- 板块列表（横向滚动，320px 视口不溢出） -->
      <div class="board-row">
        <n-button
          size="small"
          :type="activeBoard === null ? 'primary' : 'default'"
          :quaternary="activeBoard !== null"
          @click="selectBoard(null)"
        >
          全部板块
        </n-button>
        <n-button
          v-for="b in boardRows"
          :key="b.id"
          size="small"
          :type="activeBoard === b.id ? 'primary' : 'default'"
          :quaternary="activeBoard !== b.id"
          @click="selectBoard(b.id)"
        >
          {{ b.name }}
        </n-button>
      </div>

      <div v-if="postError" class="error-state" role="alert">
        <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
        <div class="error-state-body">
          <div class="error-state-title">帖子列表没有加载出来</div>
          <div class="error-state-desc">
            没有连上服务器，你写的帖子草稿仍保留在本页，不会丢失。重试一次即可恢复。
          </div>
          <details class="error-state-detail">
            <summary>查看详情</summary>
            <pre class="error-state-code">{{ postError }}</pre>
            <n-button size="tiny" quaternary @click="copyText(postError)">复制错误信息</n-button>
          </details>
        </div>
        <n-button size="small" type="primary" ghost :loading="postLoading" @click="loadPosts">重新加载</n-button>
      </div>

      <div class="table-wrap">
        <n-skeleton v-if="postLoading && !postRows.length" :repeat="6" :x-gap="12" />
        <n-data-table
          v-else
          :columns="postColumns"
          :data="postRows"
          :loading="postLoading"
          :bordered="false"
          :scroll-x="POST_SCROLL_X"
          :pagination="{ pageSize: 50, showSizePicker: false }"
          :row-key="(row: ForumPost) => row.id"
          flex-height
        >
          <template #empty>
            <n-empty :description="postEmptyText" size="small">
              <template #extra>
                <n-button v-if="postHasFilter" size="small" @click="clearPostFilter">清空筛选</n-button>
              </template>
            </n-empty>
          </template>
        </n-data-table>
      </div>

      <!-- 发帖 弹窗 -->
      <n-modal
        v-model:show="postFormVisible"
        preset="card"
        title="发布帖子"
        :style="{ width: '720px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(520px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="postForm" label-placement="top">
          <n-form-item label="板块" required>
            <n-select v-model:value="postForm.board" :options="boardOptions" placeholder="请选择板块" />
          </n-form-item>
          <n-form-item label="帖子标题" required>
            <n-input v-model:value="postForm.title" placeholder="请输入帖子标题" />
          </n-form-item>
          <n-form-item label="帖子正文" required>
            <n-input v-model:value="postForm.content" type="textarea" placeholder="写下你想分享的内容" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="postFormVisible = false">取消</n-button>
            <n-button type="primary" :loading="postSaving" :disabled="postSaving" @click="savePost">发布帖子</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 帖子详情 弹窗（只读） -->
      <n-modal
        v-model:show="detailVisible"
        preset="card"
        title="帖子详情"
        :style="{ width: '720px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(480px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <div class="detail-title">{{ detailRow?.title || '—' }}</div>
        <div class="detail-meta">
          <span>{{ detailRow?.authorName || detailRow?.personName || '匿名' }}</span>
          <span>{{ detailRow?.replyCount ?? 0 }} 条回复</span>
          <span v-if="detailRow?.createdAt" :title="absTime(detailRow.createdAt)">{{ relTime(detailRow.createdAt) }}</span>
        </div>
        <div class="detail-body">{{ detailRow?.content || '（无正文）' }}</div>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="detailVisible = false">关闭详情</n-button>
          </div>
        </template>
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NDataTable,
  NEmpty,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NModal,
  NSelect,
  NSkeleton,
  NSpace,
  NTag,
  useMessage,
  useNotification,
} from 'naive-ui'
import { AddOutline, AlertCircleOutline, SearchOutline, TrashOutline } from '@vicons/ionicons5'
import {
  createForumPost,
  deleteForumPost,
  listForumBoards,
  listForumPosts,
  restoreForumPost,
  type ForumBoard,
  type ForumPost,
} from '../../api/campusLearning'
import { extractError } from '../../utils/campus'

const message = useMessage()
const notification = useNotification()

/* ───────────────────────── 通用工具 ───────────────────────── */

function textCell(text: unknown, width = 140) {
  const s = text == null || text === '' ? '—' : String(text)
  return h('span', { title: s, style: { display: 'inline-block', maxWidth: `${width}px`, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, s)
}

/** 相对时间 + hover 绝对时间（R-204）。 */
function relTime(v?: string | null) {
  if (!v) return '—'
  const t = new Date(v).getTime()
  if (Number.isNaN(t)) return String(v)
  const diff = Date.now() - t
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const hour = Math.floor(min / 60)
  if (hour < 24) return `${hour} 小时前`
  const day = Math.floor(hour / 24)
  if (day < 30) return `${day} 天前`
  return new Date(v).toLocaleDateString('zh-CN')
}

function absTime(v?: string | null) {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v)
  return d.toLocaleString('zh-CN')
}

async function copyText(text: string) {
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      message.success('错误信息已复制')
      return
    }
  } catch {
    /* 降级提示 */
  }
  message.warning('复制失败，请手动选中详情内容复制')
}

/* ───────────────────────── 板块 ───────────────────────── */

const boardRows = ref<ForumBoard[]>([])
const activeBoard = ref<string | null>(null)

const boardOptions = computed(() =>
  boardRows.value.map((b) => ({ label: b.name || String(b.id), value: String(b.id) })),
)

async function loadBoards() {
  try {
    boardRows.value = await listForumBoards()
  } catch {
    boardRows.value = []
  }
}

function selectBoard(id: string | null) {
  activeBoard.value = id
  loadPosts()
}

/* ───────────────────────── 帖子 ───────────────────────── */

const postRows = ref<ForumPost[]>([])
const postLoading = ref(false)
const postError = ref('')
const keyword = ref('')

const postHasFilter = computed(() => Boolean(keyword.value.trim() || activeBoard.value))
const postEmptyText = computed(() => (postHasFilter.value ? '没有符合筛选条件的帖子' : '暂无数据'))

async function loadPosts() {
  postLoading.value = true
  postError.value = ''
  try {
    const kw = keyword.value.trim()
    postRows.value = await listForumPosts({
      board: activeBoard.value ?? undefined,
      kw: kw || undefined,
    })
  } catch (e: any) {
    postError.value = extractError(e)
    postRows.value = []
  } finally {
    postLoading.value = false
  }
}

function clearPostFilter() {
  keyword.value = ''
  activeBoard.value = null
  loadPosts()
}

const postColumns = computed(() => [
  {
    title: '标题',
    key: 'title',
    width: 320,
    ellipsis: true,
    render: (row: ForumPost) =>
      h(
        NButton,
        { text: true, type: 'primary', onClick: () => openDetail(row) },
        { default: () => textCell(row.pinned ? `【置顶】${row.title}` : row.title, 290) },
      ),
  },
  { title: '板块', key: 'boardName', width: 130, ellipsis: true, render: (row: ForumPost) => textCell(row.boardName, 110) },
  { title: '作者', key: 'authorName', width: 130, ellipsis: true, render: (row: ForumPost) => textCell(row.authorName || row.personName, 110) },
  {
    title: '回复数',
    key: 'replyCount',
    width: 100,
    render: (row: ForumPost) => h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, String(row.replyCount ?? 0)),
  },
  {
    title: '发布时间',
    key: 'createdAt',
    width: 140,
    render: (row: ForumPost) =>
      h('span', { title: absTime(row.createdAt) }, relTime(row.createdAt)),
  },
  {
    title: '操作',
    key: 'actions',
    width: 110,
    fixed: 'right' as const,
    render: (row: ForumPost) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removePost(row) }, {
            default: () => '删除帖子',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const POST_SCROLL_X = 1030

/* ── 发帖 ── */
const postFormVisible = ref(false)
const postSaving = ref(false)
const postForm = reactive({ board: null as string | null, title: '', content: '' })

function openPostCreate() {
  Object.assign(postForm, { board: activeBoard.value ?? (boardOptions.value[0]?.value ?? null), title: '', content: '' })
  postFormVisible.value = true
}

async function savePost() {
  if (!postForm.board) {
    message.warning('请选择板块')
    return
  }
  if (!postForm.title.trim()) {
    message.warning('请填写帖子标题')
    return
  }
  if (!postForm.content.trim()) {
    message.warning('请填写帖子正文')
    return
  }
  postSaving.value = true
  try {
    await createForumPost({
      board: String(postForm.board),
      title: postForm.title.trim(),
      content: postForm.content.trim(),
    })
    message.success('帖子已发布')
    postFormVisible.value = false
    loadPosts()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    postSaving.value = false
  }
}

/** 删除单条帖子 = 中等破坏性操作 → 直接执行 + 通知撤销（R-106）。 */
async function removePost(row: ForumPost) {
  try {
    await deleteForumPost(row.id)
    notification.create({
      content: `已删除「${row.title}」`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            try {
              await restoreForumPost(row.id)
              message.success('帖子已恢复')
              loadPosts()
            } catch (e: any) {
              message.error(extractError(e))
            }
          },
        }, { default: () => '撤销' }),
    })
    loadPosts()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ── 帖子详情 ── */
const detailVisible = ref(false)
const detailRow = ref<ForumPost | null>(null)

function openDetail(row: ForumPost) {
  detailRow.value = row
  detailVisible.value = true
}

/* ───────────────────────── 生命周期 ───────────────────────── */

onMounted(async () => {
  await loadBoards()
  await loadPosts()
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  flex-wrap: wrap;
}
.toolbar-search {
  width: 280px;
}
.spacer {
  flex: 1;
}
.board-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  overflow-x: auto;
  flex-shrink: 0;
  padding-bottom: var(--space-1);
}
.table-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
.detail-title {
  font-size: var(--text-h3);
  font-weight: 600;
  color: var(--ink);
  overflow-wrap: anywhere;
}
.detail-meta {
  display: flex;
  gap: var(--space-4);
  margin-top: var(--space-2);
  font-size: var(--text-small);
  color: var(--ink-faint);
}
.detail-body {
  margin-top: var(--space-4);
  font-size: var(--text-body);
  color: var(--ink-soft);
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.filter {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.filter-label {
  font-size: var(--text-small);
  color: var(--ink-soft);
  white-space: nowrap;
}

.error-state {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--c-error);
  border-radius: var(--radius-md);
  background: var(--c-error-soft);
  flex-shrink: 0;
}
.error-state-icon {
  color: var(--c-error-deep);
  font-size: var(--text-h4);
  flex-shrink: 0;
}
.error-state-body {
  flex: 1;
  min-width: 0;
}
.error-state-title {
  font-size: var(--text-body);
  font-weight: 600;
  color: var(--c-error-deep);
}
.error-state-desc {
  font-size: var(--text-small);
  color: var(--ink-soft);
  margin-top: var(--space-1);
}
.error-state-detail {
  margin-top: var(--space-2);
  font-size: var(--text-meta);
  color: var(--ink-soft);
}
.error-state-code {
  margin: var(--space-1) 0;
  padding: var(--space-2);
  background: var(--surface);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
