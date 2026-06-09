<template>
  <div class="scraped-resume-list">
    <n-page-header title="我找的简历" subtitle="G30 - 通过 RPA 从招聘网站抓取的简历, 待人工导入" />

    <n-card class="mt-4">
      <template #header-extra>
        <n-button type="primary" @click="showScrapeModal = true">
          <template #icon>+</template>
          开始抓取
        </n-button>
        <n-button @click="reload" :loading="loading" style="margin-left: 8px">刷新</n-button>
      </template>

      <n-data-table
        :columns="columns"
        :data="items"
        :pagination="false"
        :loading="loading"
        size="small"
      />
    </n-card>

    <!-- 抓取弹窗 -->
    <n-modal v-model:show="showScrapeModal" preset="dialog" title="开始 RPA 抓取" positive-text="抓取" @positive-click="handleScrape">
      <n-form>
        <n-form-item label="数据源">
          <n-select v-model:value="scrapeForm.source" :options="sourceOptions" />
        </n-form-item>
        <n-form-item label="职位关键词">
          <n-input v-model:value="scrapeForm.jobTitle" placeholder="例: 前端工程师" />
        </n-form-item>
        <n-form-item label="城市">
          <n-input v-model:value="scrapeForm.city" placeholder="例: 北京" />
        </n-form-item>
        <n-form-item label="RPA Bot 名">
          <n-input v-model:value="scrapeForm.scraperJobName" placeholder="例: ZhaopinBot-v1" />
        </n-form-item>
      </n-form>
    </n-modal>

    <!-- 抓取结果预览 -->
    <n-modal v-model:show="showResultModal" preset="card" title="抓取结果" style="width: 700px">
      <p>共抓取 <strong>{{ scrapedResult?.resumes?.length || 0 }}</strong> 条简历</p>
      <n-data-table
        :columns="resultColumns"
        :data="scrapedResult?.resumes || []"
        :pagination="false"
        size="small"
      />
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue';
import { NButton, NTag, useMessage } from 'naive-ui';
import {
  triggerScrape, listScrapedResumes,
  type ScrapedResume,
} from '@/api/scraped-resume';

const message = useMessage();
const items = ref<ScrapedResume[]>([]);
const loading = ref(false);
const showScrapeModal = ref(false);
const showResultModal = ref(false);
const scrapedResult = ref<ScrapedResume | null>(null);

const sourceOptions = [
  { label: 'Mock RPA (本地模拟)', value: 'MOCK_RPA' },
];

const STATUS_COLORS: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  PENDING: 'default',
  SCRAPED: 'info',
  IMPORTED: 'success',
  FAILED: 'error',
  DUPLICATE: 'warning',
};

const STATUS_LABELS: Record<string, string> = {
  PENDING: '待抓取',
  SCRAPED: '已抓取',
  IMPORTED: '已导入',
  FAILED: '失败',
  DUPLICATE: '重复',
};

const columns = [
  { title: 'ID', key: 'id', width: 100, ellipsis: { tooltip: true } },
  { title: '数据源', key: 'source', width: 120 },
  { title: 'Bot 名', key: 'scraperJobName', width: 140 },
  {
    title: '状态', key: 'status', width: 90,
    render: (row: ScrapedResume) => h(NTag, { type: STATUS_COLORS[row.status], size: 'small' }, () => STATUS_LABELS[row.status] || row.status),
  },
  { title: '抓取时间', key: 'scrapedAt', width: 170,
    render: (row: ScrapedResume) => row.scrapedAt ? new Date(row.scrapedAt).toLocaleString('zh-CN') : '-' },
];

const resultColumns = [
  { title: '姓名', key: 'name' },
  { title: '手机', key: 'phone' },
  { title: '邮箱', key: 'email' },
  { title: '来源', key: 'source' },
];

const scrapeForm = ref({
  source: 'MOCK_RPA',
  jobTitle: '',
  city: '',
  scraperJobName: 'MockBot-v1',
});

async function reload() {
  loading.value = true;
  try {
    items.value = await listScrapedResumes({ pageSize: 50 });
  } catch (err: any) {
    message.error(`加载失败: ${err?.message || err}`);
  } finally {
    loading.value = false;
  }
}

async function handleScrape() {
  try {
    const r = await triggerScrape(scrapeForm.value);
    scrapedResult.value = r;
    showScrapeModal.value = false;
    showResultModal.value = true;
    await reload();
    message.success(`抓取完成: ${r.resumes?.length || 0} 条`);
  } catch (err: any) {
    message.error(`抓取失败: ${err?.message || err}`);
  }
}

onMounted(reload);
</script>

<style scoped>
.scraped-resume-list { width: 100%; }
.mt-4 { margin-top: 16px; }
</style>
