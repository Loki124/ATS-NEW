<template>
  <div class="ann-kb">
    <!-- 左侧分类树 -->
    <aside class="ann-kb__side">
      <div class="ann-kb__side-header">
        <n-button text class="ann-kb__back" @click="router.push('/dashboard')">
          <n-icon :component="ChevronBackOutline" :size="20" />
        </n-button>
        <span>政策制度</span>
      </div>
      <nav class="ann-kb__tree">
        <div
          v-for="node in treeNodes"
          :key="node.key"
          class="ann-kb__tree-node"
          :class="{ active: currentKey === node.key }"
          :style="{ paddingLeft: `${12 + (node.level ?? 0) * 16}px` }"
          role="button"
          tabindex="0"
          @click="selectNode(node.key)"
          @keydown.enter="selectNode(node.key)"
        >
          <n-icon :component="node.icon" :size="16" class="ann-kb__tree-icon" />
          <span class="ann-kb__tree-label">{{ node.label }}</span>
          <span v-if="node.count != null" class="ann-kb__tree-count">{{ node.count }}</span>
        </div>
      </nav>
    </aside>

    <!-- 右侧内容 -->
    <main class="ann-kb__main">
      <n-spin :show="loading">
        <!-- 最近浏览 -->
        <section class="ann-kb__section">
          <div class="ann-kb__section-title">最近浏览</div>
          <div v-if="recentViews.length > 0" class="ann-kb__recent">
            <div
              v-for="item in recentViews.slice(0, 4)"
              :key="item.id"
              class="ann-kb__recent-card"
              role="button"
              tabindex="0"
              @click="goDetail(item.id)"
              @keydown.enter="goDetail(item.id)"
            >
              <div class="ann-kb__recent-icon">
                <n-icon :component="DocumentTextOutline" :size="22" />
              </div>
              <div class="ann-kb__recent-info">
                <div class="ann-kb__recent-title" :title="item.title">{{ item.title }}</div>
                <div class="ann-kb__recent-meta">{{ item.categoryDisplay }} · {{ fmtRecentTime(item.viewedAt) }}</div>
              </div>
            </div>
          </div>
          <n-empty v-else size="small" description="暂无最近浏览记录" />
        </section>

        <!-- 最近更新 -->
        <section class="ann-kb__section">
          <div class="ann-kb__section-title">最近更新</div>
          <div v-if="tableData.length > 0" class="ann-kb__table-wrap">
            <table class="ann-kb__table">
              <thead>
                <tr>
                  <th class="col-name">文档名称</th>
                  <th class="col-folder">所属文件夹</th>
                  <th class="col-editor">最近修改人</th>
                  <th class="col-time">修改时间</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in tableData"
                  :key="item.id"
                  class="ann-kb__row"
                  @click="goDetail(item.id)"
                >
                  <td class="col-name">
                    <div class="ann-kb__doc-cell">
                      <div class="ann-kb__doc-icon">
                        <n-icon :component="DocumentTextOutline" :size="18" />
                      </div>
                      <div class="ann-kb__doc-info">
                        <span class="ann-kb__doc-title" :title="item.title">{{ item.title }}</span>
                        <span v-if="item.attachments?.length" class="ann-kb__doc-attach" title="含附件">📎</span>
                      </div>
                    </div>
                  </td>
                  <td class="col-folder">
                    <n-tag size="small" :type="categoryType(item.category)" round>{{ item.categoryDisplay }}</n-tag>
                  </td>
                  <td class="col-editor">
                    <div class="ann-kb__editor">
                      <n-avatar
                        v-if="item.updatedByName"
                        :style="{ background: '#3b82f6', color: '#fff' }"
                        round
                        :size="22"
                      >
                        {{ initials(item.updatedByName) }}
                      </n-avatar>
                      <span>{{ item.updatedByName || '-' }}</span>
                    </div>
                  </td>
                  <td class="col-time">{{ fmtTime(item.updatedAt) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <n-empty v-else size="small" description="暂无公告" />
        </section>
      </n-spin>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChevronBackOutline,
  DocumentTextOutline,
  FolderOpenOutline,
  TimeOutline,
  GridOutline,
} from '@vicons/ionicons5'
import { listAnnouncements, type Announcement, type AnnouncementCategory } from '../../api/announcement'

const router = useRouter()

const loading = ref(false)
const announcements = ref<Announcement[]>([])
const currentKey = ref<string>('ALL')
const recentViews = ref<{ id: string; title: string; categoryDisplay: string; viewedAt: string }[]>([])

type TreeNode = {
  key: string
  label: string
  icon: any
  level?: number
  count?: number
}

const treeNodes = computed<TreeNode[]>(() => {
  const nodes: TreeNode[] = [
    { key: 'RECENT', label: '最近动态', icon: TimeOutline },
    { key: 'ALL', label: '全部文件', icon: GridOutline },
  ]
  const counts: Record<string, number> = {
    SYSTEM: announcements.value.filter((a) => a.category === 'SYSTEM').length,
    NOTICE: announcements.value.filter((a) => a.category === 'NOTICE').length,
    PROCESS: announcements.value.filter((a) => a.category === 'PROCESS').length,
  }
  const categoryMeta: Record<AnnouncementCategory, { label: string; icon: any }> = {
    SYSTEM: { label: '制度', icon: FolderOpenOutline },
    NOTICE: { label: '公告', icon: FolderOpenOutline },
    PROCESS: { label: '流程', icon: FolderOpenOutline },
  }
  ;(['SYSTEM', 'NOTICE', 'PROCESS'] as AnnouncementCategory[]).forEach((cat) => {
    nodes.push({
      key: cat,
      label: categoryMeta[cat].label,
      icon: categoryMeta[cat].icon,
      level: 0,
      count: counts[cat],
    })
  })
  return nodes
})

const tableData = computed(() => {
  let list = announcements.value
  if (currentKey.value === 'RECENT') {
    list = [...list].sort((a, b) => new Date(b.updatedAt || b.publishedAt).getTime() - new Date(a.updatedAt || a.publishedAt).getTime())
  } else if (currentKey.value !== 'ALL') {
    list = list.filter((a) => a.category === currentKey.value)
  }
  return list
})

function selectNode(key: string) {
  currentKey.value = key
}

function goDetail(id: string) {
  router.push(`/announcements/${id}`)
}

function categoryType(c: AnnouncementCategory): 'info' | 'success' | 'warning' {
  if (c === 'NOTICE') return 'success'
  if (c === 'PROCESS') return 'warning'
  return 'info'
}

function initials(name: string): string {
  return name.slice(0, 1).toUpperCase()
}

function fmtTime(iso?: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function fmtRecentTime(iso?: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function loadRecentViews() {
  try {
    const raw = localStorage.getItem('ann_recent_views')
    recentViews.value = raw
      ? (JSON.parse(raw) as { id: string; title: string; categoryDisplay: string; viewedAt: string }[])
      : []
  } catch {
    recentViews.value = []
  }
}

async function refresh() {
  loading.value = true
  try {
    announcements.value = await listAnnouncements()
  } catch {
    announcements.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void refresh()
  loadRecentViews()
})
</script>

<style scoped>
.ann-kb {
  display: flex;
  min-height: 100%;
  background: #f5f7fa;
}

/* 左侧边栏 */
.ann-kb__side {
  width: 220px;
  flex-shrink: 0;
  background: var(--glass-bg-card);
  border-right: 1px solid #f0f0f0;
  padding: 20px 0;
}

.ann-kb__side-header {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 20px 16px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.ann-kb__back {
  margin-left: -4px;
  color: #6b7280;
  padding: 4px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.ann-kb__back:hover {
  color: #2563eb;
  background: #eff6ff;
}

.ann-kb__tree {
  display: flex;
  flex-direction: column;
}

.ann-kb__tree-node {
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

.ann-kb__tree-node:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.ann-kb__tree-node.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 500;
}

.ann-kb__tree-icon {
  flex-shrink: 0;
}

.ann-kb__tree-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ann-kb__tree-count {
  font-size: 12px;
  color: #9ca3af;
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 10px;
}

.ann-kb__tree-node.active .ann-kb__tree-count {
  background: #dbeafe;
  color: #2563eb;
}

/* 右侧主内容 */
.ann-kb__main {
  flex: 1;
  min-width: 0;
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.ann-kb__section {
  background: var(--glass-bg-card);
  border-radius: 12px;
  padding: 20px 24px;
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.03);
}

/* 相邻 section 之间增加垂直间距（最近浏览 / 最近更新） */
.ann-kb__section + .ann-kb__section {
  margin-top: 24px;
}

.ann-kb__section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
}

/* 最近浏览卡片 */
.ann-kb__recent {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.ann-kb__recent-card {
  width: 240px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fafafa;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
}

.ann-kb__recent-card:hover {
  background: var(--glass-bg-card);
  border-color: #bfdbfe;
  box-shadow: 0 2px 10px rgba(59, 130, 246, 0.08);
}

.ann-kb__recent-icon {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  background: #eff6ff;
  color: #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ann-kb__recent-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ann-kb__recent-title {
  color: #1f2937;
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ann-kb__recent-meta {
  color: #9ca3af;
  font-size: 12px;
}

/* 表格 */
.ann-kb__table-wrap {
  overflow-x: auto;
}

.ann-kb__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.ann-kb__table th {
  text-align: left;
  color: #9ca3af;
  font-weight: 500;
  padding: 10px 12px;
  border-bottom: 1px solid #f0f0f0;
  white-space: nowrap;
}

.ann-kb__table td {
  padding: 14px 12px;
  border-bottom: 1px solid #f5f5f5;
  color: #4b5563;
  vertical-align: middle;
}

.ann-kb__row {
  cursor: pointer;
  transition: background 0.15s;
}

.ann-kb__row:hover {
  background: #f8fafc;
}

.ann-kb__row:last-child td {
  border-bottom: none;
}

.col-name {
  width: 45%;
}

.col-folder {
  width: 18%;
}

.col-editor {
  width: 18%;
}

.col-time {
  width: 19%;
  white-space: nowrap;
}

.ann-kb__doc-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ann-kb__doc-icon {
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

.ann-kb__doc-info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.ann-kb__doc-title {
  color: #1f2937;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ann-kb__doc-attach {
  font-size: 12px;
  flex-shrink: 0;
}

.ann-kb__editor {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 900px) {
  .ann-kb__side {
    display: none;
  }
  .ann-kb__main {
    padding: 16px;
  }
  .ann-kb__recent-card {
    width: 100%;
  }
}
</style>
