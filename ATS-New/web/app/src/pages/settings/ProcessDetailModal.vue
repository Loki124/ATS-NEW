<!--
  Plan T7: 流程详情 Modal (read-only, single-column)
  - 显示流程基础信息
  - 纵向单列渲染所有阶段卡片 (不再用 masonry)
  - 首个/末尾阶段显示 "系统内置" 徽标
  - 底部 "前往编辑" 按钮 -> 触发 goEdit 事件 (路由回 RecruitmentProcess 走编辑流)
-->
<template>
  <n-modal
    :show="show"
    preset="card"
    :title="`流程详情 - ${data?.name || ''}`"
    style="width: 720px; max-width: 95vw"
    :mask-closable="true"
    @update:show="(v) => emit('update:show', v)"
  >
    <n-spin :show="loading">
      <!-- ====== 基础信息 ====== -->
      <div v-if="data" class="detail-meta">
        <div class="detail-meta__row">
          <span class="detail-meta__label">流程编号:</span>
          <span>{{ data.code }}</span>
        </div>
        <div class="detail-meta__row">
          <span class="detail-meta__label">流程名称:</span>
          <span>{{ data.name }}</span>
          <n-tag v-if="data.status === 'ACTIVE'" type="success" size="small" style="margin-left: 8px">启用</n-tag>
          <n-tag v-else type="default" size="small" style="margin-left: 8px">停用</n-tag>
        </div>
        <div v-if="data.description" class="detail-meta__row">
          <span class="detail-meta__label">流程说明:</span>
          <span>{{ data.description }}</span>
        </div>
        <div v-if="data.applicableDepartments && data.applicableDepartments.length" class="detail-meta__row">
          <span class="detail-meta__label">适用部门:</span>
          <n-space size="small" :wrap="false">
            <n-tag
              v-for="d in data.applicableDepartments"
              :key="d"
              size="small"
              type="info"
            >
              {{ d }}
            </n-tag>
          </n-space>
        </div>
        <div class="detail-meta__row">
          <span class="detail-meta__label">适用范围模式:</span>
          <span>{{ data.applicableMode === 'ALL' ? '全部满足' : '任意满足' }}</span>
        </div>
        <div class="detail-meta__row">
          <span class="detail-meta__label">校验简历评分:</span>
          <span>{{ data.validateResumeScore ? '是' : '否' }}</span>
        </div>
        <div v-if="data.failPrompt" class="detail-meta__row">
          <span class="detail-meta__label">流转异常提示:</span>
          <span>{{ data.failPrompt }}</span>
        </div>
      </div>

      <n-divider title-placement="left">阶段列表 ({{ links.length }})</n-divider>

      <!-- ====== 单列纵向 stage list ====== -->
      <div v-if="!loading && links.length === 0" class="detail-empty">
        暂无阶段
      </div>
      <div v-else class="stage-list">
        <div
          v-for="(link, idx) in links"
          :key="link.id"
          class="stage-card"
        >
          <!-- 阶段序号 + 名称 + 系统徽标 -->
          <div class="stage-card__header">
            <span class="stage-card__order">{{ idx + 1 }}</span>
            <span class="stage-card__name">{{ link.stage?.name || link.customName || '未命名' }}</span>
            <n-tag
              v-if="link.stage?.isSystem"
              class="stage-card__system-badge"
              type="info"
              size="small"
            >
              系统内置
            </n-tag>
            <n-tag v-if="link.isStart" type="success" size="small">起始</n-tag>
            <n-tag v-if="link.isEnd" type="warning" size="small">结束</n-tag>
          </div>

          <!-- 阶段类型 + features -->
          <div class="stage-card__meta">
            <n-tag size="small" type="default">{{ stageTypeLabel(link.stage?.stageType) }}</n-tag>
            <n-tag
              v-for="f in link.stage?.features || []"
              :key="f"
              size="small"
              type="default"
            >
              {{ f }}
            </n-tag>
          </div>

          <!-- 阶段规则 -->
          <div v-if="link.rule" class="stage-card__rule">
            <span class="stage-card__rule-label">自动流转:</span>
            <span>{{ ruleLabel(link.rule) }}</span>
          </div>

          <!-- 进入条件 - 注意: condition 是 EntryCondition 对象,不是字符串 -->
          <div v-if="link.condition" class="stage-card__entry">
            <span class="stage-card__entry-label">进入条件:</span>
            <span>已配置</span>
          </div>
        </div>
      </div>
    </n-spin>

    <template #footer>
      <n-space justify="end">
        <n-button @click="emit('update:show', false)">关闭</n-button>
        <n-button
          type="primary"
          data-testid="btn-go-edit"
          @click="onGoEdit"
        >
          前往编辑
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NSpace, NTag, NSpin, NDivider, NModal, NButton, useMessage } from 'naive-ui'
import {
  getProcess,
  listProcessLinks,
  type RecruitmentProcess,
  type ProcessStageLink,
} from '../../api/recruitment-process'

const props = defineProps<{
  show: boolean
  processId: string
}>()

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
  (e: 'goEdit', processId: string): void
}>()

const message = useMessage()
const loading = ref(false)
const data = ref<RecruitmentProcess | null>(null)
const links = ref<ProcessStageLink[]>([])

async function load() {
  if (!props.processId) return
  loading.value = true
  try {
    const [proc, lks] = await Promise.all([getProcess(props.processId), listProcessLinks(props.processId)])
    data.value = proc as RecruitmentProcess
    // 按 orderIndex 排序
    links.value = (lks || []).slice().sort((a: any, b: any) => (a.orderIndex || 0) - (b.orderIndex || 0))
  } catch (e: any) {
    message.error(e?.response?.data?.message || '加载流程详情失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.show, props.processId],
  ([s]) => {
    if (s && props.processId) load()
  },
  { immediate: true },
)

function onGoEdit() {
  if (!props.processId) return
  emit('goEdit', props.processId)
}

function stageTypeLabel(t?: string): string {
  switch (t) {
    case 'FILTER': return '筛选'
    case 'INVITATION': return '邀约'
    case 'INTERVIEW': return '面试'
    case 'OFFER': return 'Offer'
    case 'ONBOARDING': return '入职'
    default: return t || '-'
  }
}

function ruleLabel(r: any): string {
  if (!r) return '-'
  const parts: string[] = []
  if (r.autoAdvanceType && r.autoAdvanceType !== 'NONE') {
    parts.push(`自动流转(${r.autoAdvanceType})`)
  }
  if (r.timeLimit) {
    parts.push(`限时 ${r.timeLimit} 天`)
  }
  return parts.length > 0 ? parts.join(' / ') : '已配置'
}
</script>

<style scoped>
.detail-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 4px;
}
.detail-meta__row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  line-height: 1.6;
}
.detail-meta__label {
  color: #666;
  min-width: 100px;
  font-weight: 500;
}
.detail-empty {
  text-align: center;
  color: #999;
  padding: 24px 0;
}

/* 单列纵向列表 (Plan T7: 不再使用 masonry) */
.stage-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stage-card {
  border: 1px solid #e0e0e6;
  border-radius: 6px;
  padding: 12px 16px;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.stage-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.stage-card__order {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #18a058;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}
.stage-card__name {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}
.stage-card__system-badge {
  margin-left: 4px;
}
.stage-card__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.stage-card__rule,
.stage-card__entry {
  font-size: 13px;
  color: #555;
}
.stage-card__rule-label,
.stage-card__entry-label {
  color: #888;
  margin-right: 4px;
}
</style>
