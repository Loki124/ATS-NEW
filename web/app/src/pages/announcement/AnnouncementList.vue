<template>
  <div class="ann-page">
    <!-- 页头 -->
    <header class="ann-page__header">
      <div class="ann-page__title-row">
        <h1 class="ann-page__title">制度公告</h1>
        <span class="ann-page__subtitle">招聘相关的制度、公告与流程指引</span>
      </div>
      <n-tabs
        v-model:value="categoryFilter"
        type="segment"
        size="small"
        class="ann-page__filter"
      >
        <n-tab-pane name="ALL" tab="全部" />
        <n-tab-pane name="SYSTEM" tab="制度" />
        <n-tab-pane name="NOTICE" tab="公告" />
        <n-tab-pane name="PROCESS" tab="流程" />
      </n-tabs>
    </header>

    <!-- 列表 -->
    <section class="ann-page__list">
      <n-spin :show="loading">
        <div
          v-for="item in filteredAnnouncements"
          :key="item.id"
          class="ann-row"
          role="button"
          tabindex="0"
          @click="openDetail(item)"
          @keydown.enter="openDetail(item)"
        >
          <div class="ann-row__head">
            <n-tag v-if="item.pinned" size="tiny" type="error" round>置顶</n-tag>
            <n-tag size="tiny" :type="categoryType(item.category)" round>{{ item.categoryDisplay }}</n-tag>
            <span class="ann-row__title">{{ item.title }}</span>
            <span v-if="item.attachments?.length" class="ann-row__attach" title="含附件">📎</span>
          </div>
          <p class="ann-row__summary">{{ item.summary || '（暂无概述）' }}</p>
          <div class="ann-row__meta">
            <span>{{ item.audienceDisplay }}</span>
            <span class="ann-row__dot">·</span>
            <span>{{ fmtTime(item.publishedAt) }}</span>
          </div>
        </div>

        <div v-if="!loading && filteredAnnouncements.length === 0" class="ann-page__empty">
          <n-empty :description="categoryFilter === 'ALL' ? '暂无制度公告' : '该分类下暂无公告'" />
        </div>
      </n-spin>
    </section>

    <!-- 详情抽屉 -->
    <n-drawer
      v-model:show="detailVisible"
      :width="480"
      placement="right"
      :trap-focus="false"
    >
      <n-drawer-content :native-scrollbar="false">
        <template #header>
          <span class="ann-detail__title">{{ detail?.title }}</span>
        </template>
        <div v-if="detail" class="ann-detail">
          <div class="ann-detail__meta">
            <n-tag size="small" :type="categoryType(detail.category)" round>{{ detail.categoryDisplay }}</n-tag>
            <n-tag size="small" round>{{ detail.audienceDisplay }}</n-tag>
            <span class="ann-detail__time">{{ fmtTime(detail.publishedAt) }}</span>
          </div>
          <p class="ann-detail__body">{{ detail.body }}</p>
          <div v-if="detail.attachments && detail.attachments.length" class="ann-detail__attachments">
            <div class="ann-detail__attach-title">附件</div>
            <a
              v-for="att in detail.attachments"
              :key="att.id"
              class="ann-detail__attach"
              :href="att.fileUrl"
              target="_blank"
              rel="noopener"
            >
              <span class="ann-detail__attach-name">📎 {{ att.originalName }}</span>
              <span class="ann-detail__attach-size">{{ formatFileSize(att.fileSize) }}</span>
            </a>
          </div>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { listAnnouncements, type Announcement, type AnnouncementCategory } from '../../api/announcement'

const loading = ref(false)
const announcements = ref<Announcement[]>([])
const categoryFilter = ref<'ALL' | AnnouncementCategory>('ALL')

// 详情抽屉
const detailVisible = ref(false)
const detail = ref<Announcement | null>(null)

function openDetail(item: Announcement) {
  detail.value = item
  detailVisible.value = true
}

const filteredAnnouncements = computed(() => {
  if (categoryFilter.value === 'ALL') return announcements.value
  return announcements.value.filter((a) => a.category === categoryFilter.value)
})

function categoryType(c: AnnouncementCategory): 'info' | 'success' | 'warning' {
  if (c === 'NOTICE') return 'success'
  if (c === 'PROCESS') return 'warning'
  return 'info'
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

async function refresh() {
  loading.value = true
  try {
    // 公开列表仅取上架公告（默认行为），与管理后台「全部历史」区分
    announcements.value = await listAnnouncements()
  } catch {
    announcements.value = []
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
</script>

<style scoped>
.ann-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: 880px;
  margin: 0 auto;
  width: 100%;
}

.ann-page__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.ann-page__title-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.ann-page__title {
  margin: 0;
  font-size: var(--text-h2);
  font-weight: 600;
  color: var(--color-ink);
}

.ann-page__subtitle {
  color: var(--color-ink-soft);
  font-size: var(--text-small);
}

.ann-page__filter {
  align-self: flex-start;
}

.ann-page__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-height: 200px;
}

.ann-row {
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.05s ease;
}

.ann-row:hover {
  border-color: var(--color-accent);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.ann-row:active {
  transform: scale(0.997);
}

.ann-row__head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.ann-row__title {
  color: var(--color-ink);
  font-size: var(--text-h4);
  font-weight: 500;
  line-height: 1.4;
  flex: 1;
  min-width: 0;
}

.ann-row__attach {
  font-size: 13px;
  flex-shrink: 0;
}

.ann-row__summary {
  margin: var(--space-2) 0 0;
  color: var(--color-ink-soft);
  font-size: var(--text-body);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ann-row__meta {
  margin-top: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-ink-soft);
  font-size: var(--text-small);
}

.ann-row__dot {
  opacity: 0.5;
}

.ann-page__empty {
  padding: var(--space-10) 0;
  display: flex;
  justify-content: center;
}

/* ===== 详情抽屉 ===== */
.ann-detail__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-ink);
}
.ann-detail__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-bottom: var(--space-4);
}
.ann-detail__time {
  color: var(--color-ink-soft);
  font-size: var(--text-small);
}
.ann-detail__body {
  margin: 0;
  color: var(--color-ink);
  font-size: var(--text-body);
  line-height: 1.7;
  white-space: pre-wrap;
}
.ann-detail__attachments {
  margin-top: var(--space-6);
  border-top: 1px solid var(--color-border-hairline);
  padding-top: var(--space-4);
}
.ann-detail__attach-title {
  font-size: var(--text-small);
  color: var(--color-ink-soft);
  margin-bottom: var(--space-2);
}
.ann-detail__attach {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-surface-sunk);
  color: var(--color-ink);
  text-decoration: none;
  margin-bottom: var(--space-2);
  transition: background 0.15s ease;
}
.ann-detail__attach:hover {
  background: var(--color-border-hairline);
}
.ann-detail__attach-size {
  color: var(--color-ink-soft);
  font-size: var(--text-small);
  flex-shrink: 0;
}
</style>
