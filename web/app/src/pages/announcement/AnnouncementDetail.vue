<template>
  <div class="ann-detail-page">
    <n-spin :show="loading" class="ann-detail-spin">
      <div v-if="!loading && !announcement" class="ann-detail-empty">
        <n-empty :description="errorMsg || '公告不存在或已被下架'" />
        <n-space class="back-btn" justify="center">
          <n-button quaternary @click="goBack">
            <template #icon>
              <n-icon :component="ArrowBackOutline" />
            </template>
            返回制度公告
          </n-button>
          <n-button type="primary" @click="loadDetail">
            <template #icon>
              <n-icon :component="RefreshOutline" />
            </template>
            重新加载
          </n-button>
        </n-space>
      </div>

      <div v-else-if="announcement" class="ann-detail-layout">
        <!-- 顶部返回 + 面包屑 -->
        <div class="ann-detail-topbar">
          <n-button quaternary size="small" @click="goBack">
            <template #icon>
              <n-icon :component="ArrowBackOutline" />
            </template>
            返回制度公告
          </n-button>
        </div>

        <!-- 正文卡片 -->
        <div class="ann-detail-card">
          <h1 class="ann-detail-title">{{ announcement.title }}</h1>

          <div class="ann-detail-meta">
            <n-avatar
              v-if="announcement.createdByName"
              class="ann-detail-avatar"
              :style="{ background: 'var(--c-info)', color: 'var(--g1)' }"
              round
              :size="28"
            >
              {{ initials(announcement.createdByName) }}
            </n-avatar>
            <span v-if="announcement.createdByName" class="ann-detail-author">{{ announcement.createdByName }}</span>
            <span class="ann-detail-dot">·</span>
            <span class="ann-detail-time">{{ fmtTime(announcement.publishedAt) }}</span>
            <n-tag size="small" :type="announcement.isActive ? 'success' : 'default'" round>
              {{ announcement.isActive ? '已发布' : '已下架' }}
            </n-tag>
            <n-tag size="small" type="info" round>{{ announcement.audienceDisplay }}</n-tag>
          </div>

          <!-- 公告正文：sanitizeHtml 已白名单消毒（utils/sanitizeHtml.ts 8 个 XSS 向量测试覆盖），通过 <SafeHtml> 组件封装 v-html 让 lint 闸门自动 catch 其他页面新增的 v-html -->
          <SafeHtml class="ann-detail-body" :html="announcement.body" />

          <!-- 附件 -->
          <div v-if="announcement.attachments?.length" class="ann-detail-attachments">
            <div class="ann-detail-attachments__title">
              附件（{{ announcement.attachments.length }}）
            </div>
            <div class="ann-detail-attachments__list">
              <a
                v-for="att in announcement.attachments"
                :key="att.id"
                class="ann-attach-item"
                :href="att.fileUrl"
                target="_blank"
                rel="noopener"
              >
                <div class="ann-attach-icon" :class="fileIconClass(att.originalName)">
                  <n-icon :component="DocumentTextOutline" :size="22" />
                </div>
                <div class="ann-attach-info">
                  <div class="ann-attach-name" :title="att.originalName">{{ att.originalName }}</div>
                  <div class="ann-attach-size">{{ formatFileSize(att.fileSize) }}</div>
                </div>
                <div class="ann-attach-action">
                  <n-icon :component="DownloadOutline" :size="18" />
                </div>
              </a>
            </div>
          </div>
        </div>
      </div>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowBackOutline, DocumentTextOutline, DownloadOutline, RefreshOutline } from '@vicons/ionicons5'
import { getAnnouncement, type Announcement } from '../../api/announcement'
import SafeHtml from '../../components/SafeHtml.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const announcement = ref<Announcement | null>(null)
const errorMsg = ref('')

function goBack() {
  router.push('/announcements')
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

function formatFileSize(bytes: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

function fileIconClass(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  if (ext === 'pdf') return 'pdf'
  if (['doc', 'docx'].includes(ext)) return 'word'
  if (['xls', 'xlsx'].includes(ext)) return 'excel'
  if (['ppt', 'pptx'].includes(ext)) return 'ppt'
  if (['png', 'jpg', 'jpeg', 'gif'].includes(ext)) return 'image'
  return 'default'
}

async function loadDetail() {
  const id = route.params.id as string
  if (!id) return
  loading.value = true
    errorMsg.value = ''
    try {
    const data = await getAnnouncement(id)
    announcement.value = data
    if (data) {
      // 记录到最近浏览
      recordRecentView(data)
    } else {
      // 请求成功但响应为空（如返回了 HTML 而非 JSON），属于异常形态
      errorMsg.value = '接口返回了空数据（可能非 JSON 响应）'
    }
  } catch (err: any) {
    announcement.value = null
    const status = err?.response?.status
    if (status === 404) {
      errorMsg.value = '公告不存在或已被下架'
    } else if (status === 403) {
      errorMsg.value = '暂无权限查看该公告'
    } else if (status >= 500) {
      errorMsg.value = '服务器异常，请稍后重试'
    } else {
      errorMsg.value = '加载失败，请检查网络后重试'
    }
    console.error('[AnnouncementDetail] load failed:', status, err?.response?.data || err?.message)
  } finally {
    loading.value = false
  }
}

function recordRecentView(item: Announcement) {
  try {
    const key = 'ann_recent_views'
    const raw = localStorage.getItem(key)
    let list: { id: string; title: string; categoryDisplay: string; viewedAt: string }[] = raw
      ? (JSON.parse(raw) as { id: string; title: string; categoryDisplay: string; viewedAt: string }[])
      : []
    list = list.filter((x) => x.id !== item.id)
    list.unshift({
      id: item.id,
      title: item.title,
      categoryDisplay: item.categoryDisplay,
      viewedAt: new Date().toISOString(),
    })
    localStorage.setItem(key, JSON.stringify(list.slice(0, 10)))
  } catch {
    /* noop */
  }
}

onMounted(loadDetail)
</script>

<style scoped>
.ann-detail-page {
  min-height: 100%;
  background: var(--g1);
  padding: var(--space-6);
}

.ann-detail-spin {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
}

.ann-detail-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  padding: 80px 0;
}

.ann-detail-layout {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.ann-detail-topbar {
  display: flex;
  align-items: center;
}

.ann-detail-card {
  background: var(--glass-bg-card);
  border-radius: 12px;
  padding: var(--space-8) 40px;
  box-shadow: 0 2px 12px var(--overlay-scrim-weak);
}

.ann-detail-title {
  margin: 0 0 var(--space-4);
  font-size: var(--fs-24);
  font-weight: 600;
  color: var(--n-800);
  line-height: 1.4;
}

.ann-detail-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: var(--space-6);
  color: var(--g5);
  font-size: var(--fs-14);
}

.ann-detail-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-13);
  font-weight: 500;
}

.ann-detail-author {
  color: var(--n-700);
  font-weight: 500;
}

.ann-detail-dot {
  opacity: 0.5;
}

.ann-detail-time {
  color: var(--g5);
}

.ann-detail-body {
  color: var(--n-700);
  font-size: var(--fs-15);
  line-height: 1.8;
  margin-bottom: var(--space-8);
}

.ann-detail-body :deep(p) {
  margin: 0 0 var(--space-3);
}

.ann-detail-body :deep(ul),
.ann-detail-body :deep(ol) {
  margin: var(--space-3) 0;
  padding-left: var(--space-6);
}

.ann-detail-body :deep(li) {
  margin-bottom: 6px;
}

.ann-detail-body :deep(a) {
  color: var(--c-info);
  text-decoration: underline;
}

/* 附件 */
.ann-detail-attachments {
  border-top: 1px solid var(--g1);
  padding-top: var(--space-6);
}

.ann-detail-attachments__title {
  font-size: var(--fs-15);
  font-weight: 600;
  color: var(--n-800);
  margin-bottom: var(--space-3);
}

.ann-detail-attachments__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ann-attach-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--g1);
  border-radius: 8px;
  background: var(--g1);
  text-decoration: none;
  transition: background 0.15s, border-color 0.15s;
}

.ann-attach-item:hover {
  background: var(--g1);
  border-color: var(--g6);
}

.ann-attach-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--g1);
}

.ann-attach-icon.default { background: var(--c-info); }
.ann-attach-icon.pdf { background: var(--c-error); }
.ann-attach-icon.word { background: var(--c-info); }
.ann-attach-icon.excel { background: var(--c-success); }
.ann-attach-icon.ppt { background: var(--c-warning); }
.ann-attach-icon.image { background: var(--brand); }

.ann-attach-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ann-attach-name {
  color: var(--n-800);
  font-size: var(--fs-14);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ann-attach-size {
  color: var(--n-380);
  font-size: var(--fs-12);
}

.ann-attach-action {
  color: var(--n-380);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  transition: background 0.15s, color 0.15s;
}

.ann-attach-item:hover .ann-attach-action {
  color: var(--c-info);
  background: var(--g1);
}

.back-btn {
  margin-top: var(--space-2);
}
</style>
