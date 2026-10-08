<template>
  <div class="page-container process-stage-editor">
<div class="page-body">
    <div class="page-header">
      <div>
        <n-space align="center">
          <n-button text @click="$router.back()">
            <template #icon><n-icon :component="ArrowBackOutline" /></template>
            {{ t('pages.settings.ProcessStageEditor.s1') }}
          </n-button>
          <h2 class="page-title">{{ processName }} - {{ t('pages.settings.ProcessStageEditor.s38') }}</h2>
        </n-space>
        <p class="page-subtitle">{{ t('pages.settings.ProcessStageEditor.s2') }}</p>
      </div>
      <n-button type="primary" :disabled="!processId" @click="openAddModal">
        <template #icon><n-icon :component="AddOutline" /></template>
        {{ t('pages.settings.ProcessStageEditor.s3') }}
      </n-button>
    </div>

    <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
      {{ t('pages.settings.ProcessStageEditor.s52') }}<strong>{{ t('pages.settings.ProcessStageEditor.s4') }}</strong>{{ t('pages.settings.ProcessStageEditor.s39') }}
    </n-alert>

    <n-spin :show="loading">
      <div v-if="links.length === 0" class="empty-state">
        <n-empty :description="t('pages.settings.ProcessStageEditor.s5')" />
      </div>
      <div v-else>
        <draggable-list v-model="orderedLinks" @update:model-value="onReorder">
          <template #item="{ element }">
            <n-card class="stage-card" size="small">
              <div class="stage-row">
                <div class="stage-info">
                  <n-tag v-if="element.stage?.isStart" type="success" size="small">{{ t('pages.settings.ProcessStageEditor.s6') }}</n-tag>
                  <n-tag v-if="element.stage?.isEnd" type="warning" size="small">{{ t('pages.settings.ProcessStageEditor.s7') }}</n-tag>
                  <n-tag :type="getTypeColor(element.stage.stageType)" size="small">
                    {{ element.stage.stageType }}
                  </n-tag>
                  <span class="stage-code">{{ element.stage.code }}</span>
                  <span class="stage-name">{{ element.customName || element.stage.name }}</span>
                  <span v-if="element.stage.isBuiltin ?? element.stage.isSystem" class="sys-tag">{{ t('pages.settings.ProcessStageEditor.s8') }}</span>
                  <span v-if="element.stageLimit" class="stage-limit">⏱ {{ element.stageLimit }}h</span>
                </div>
                <div class="stage-actions">
                  <n-button text size="small" type="primary" @click="goRules(element)">{{ t('pages.settings.ProcessStageEditor.s9') }}</n-button>
                  <n-button text size="small" type="primary" @click="goConditions(element)">{{ t('pages.settings.ProcessStageEditor.s10') }}</n-button>
                  <n-button text size="small" @click="editLinkCustomName(element)">{{ t('pages.settings.ProcessStageEditor.s11') }}</n-button>
                  <n-button text size="small" @click="editLinkStageLimit(element)">{{ t('pages.settings.ProcessStageEditor.s40') }}</n-button>
                  <n-popconfirm
                    v-if="!element.stage?.isStart && !element.stage?.isEnd"
                    @positive-click="removeLink(element)"
                  >
                    <template #trigger>
                      <n-button size="small" type="error">{{ t('pages.settings.ProcessStageEditor.s12') }}</n-button>
                    </template>
                    {{ t('pages.settings.ProcessStageEditor.s41', { name: element.stage.name }) }}
                  </n-popconfirm>
                  <n-tag v-else type="default" size="small">{{ t('pages.settings.ProcessStageEditor.s13') }}</n-tag>
                </div>
              </div>
              <div v-if="(element.stage.features ?? element.stage.defaultFeatures)?.length" class="stage-features">
                <span v-for="f in (element.stage.features ?? element.stage.defaultFeatures)" :key="f" class="feature-chip">{{ featureLabel(f) }}</span>
              </div>
            </n-card>
          </template>
        </draggable-list>
      </div>
    </n-spin>

    <!-- 添加阶段弹窗 - 从全局库选 -->
    <n-modal
      v-model:show="showAddModal"
      preset="card"
      :title="t('pages.settings.ProcessStageEditor.s14')"
      style="width: 720px; max-width: 90vw"
      :transform-origin="undefined"
    >
      <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
        {{ t('pages.settings.ProcessStageEditor.s53') }}<strong>{{ t('pages.settings.ProcessStageEditor.s15') }}</strong>{{ t('pages.settings.ProcessStageEditor.s54') }}<strong>{{ t('pages.settings.ProcessStageEditor.s16') }}</strong>{{ t('pages.settings.ProcessStageEditor.s51') }}
      </n-alert>
      <n-spin :show="loadingAddModal">
        <n-data-table
          :columns="addModalColumns"
          :data="availableStages"
          :row-key="(r) => r.id"
          :pagination="localPagination(8)"
        />
      </n-spin>
    </n-modal>

    <!-- 设置阶段时长弹窗 -->
    <n-modal
      v-model:show="showLimitModal"
      preset="card"
      :mask-closable="false"
      :title="t('pages.settings.ProcessStageEditor.s17')"
      style="width: 400px; max-width: 90vw"
      :transform-origin="undefined"
    >
      <n-form :model="limitForm" label-placement="top">
        <n-form-item :label="t('pages.settings.ProcessStageEditor.s18')">
          <n-input-number v-model:value="limitForm.stageLimit" :min="0" :placeholder="t('pages.settings.ProcessStageEditor.s19')" style="width: 100%" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showLimitModal = false">{{ t('pages.settings.ProcessStageEditor.s20') }}</n-button>
          <n-button type="primary" class="gradient-btn" @click="saveStageLimit">{{ t('pages.settings.ProcessStageEditor.s21') }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 修改流程内阶段名称弹窗（customName，覆盖全局 stage 名，满足「可修改名称」） -->
    <n-modal
      v-model:show="showRenameModal"
      preset="card"
      :mask-closable="false"
      :title="t('pages.settings.ProcessStageEditor.s22')"
      style="width: 400px; max-width: 90vw"
      :transform-origin="undefined"
    >
      <n-form :model="renameForm" label-placement="top">
        <n-form-item :label="t('pages.settings.ProcessStageEditor.s23')">
          <n-input
            v-model:value="renameForm.customName"
            :placeholder="t('pages.settings.ProcessStageEditor.s24')"
            :maxlength="20"
            show-count
            clearable
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showRenameModal = false">{{ t('pages.settings.ProcessStageEditor.s25') }}</n-button>
          <n-button type="primary" class="gradient-btn" @click="saveCustomName">{{ t('pages.settings.ProcessStageEditor.s26') }}</n-button>
        </n-space>
      </template>
    </n-modal>
    </div><!-- /.page-body -->
</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useMessage, NButton, NTag, NPopconfirm, NIcon, NSpace, NInput, NInputNumber, NForm, NFormItem, NModal, NDataTable, NAlert, NEmpty, NSpin, NCard } from 'naive-ui'
import { AddOutline, ArrowBackOutline } from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { localPagination } from '@/composables/useTablePagination'
import {
  getProcess,
  listProcessLinks,
  listStages,
  addProcessLink,
  updateProcessLink,
  deleteProcessLink,
  reorderProcessLinks,
} from '../../api/recruitment-process'
import DraggableList from '../../components/DraggableList.vue'
import type { TagType } from '../../api/offer'

// 类型颜色映射 (key 对齐后端 StageType 系统内置枚举)
const STAGE_TYPE_COLOR: Record<string, string> = {
  START_END: 'primary',
  SCREEN: 'info',
  INVITATION: 'default',
  INTERVIEW: 'success',
  ASSESSMENT: 'info',
  OFFER: 'warning',
  OTHER: 'default',
}

const message = useMessage()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const processId = computed(() => route.query.processId as string)
const processName = ref(t('pages.settings.ProcessStageEditor.s42'))
const links = ref<any[]>([])
const orderedLinks = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const loadingAddModal = ref(false)
const availableStages = ref<any[]>([])
const showLimitModal = ref(false)
const limitForm = ref<{ linkId: string; stageLimit: number | null }>({ linkId: '', stageLimit: 0 })
const showRenameModal = ref(false)
const renameForm = ref<{ linkId: string; customName: string }>({ linkId: '', customName: '' })

// 类型颜色映射
function getTypeColor(type: string): TagType {
  return (STAGE_TYPE_COLOR as Record<string, TagType>)[type] || 'default'
}

// 功能项 code → 中文名称（对齐后端 recruitment_stages 实际取值 + RecruitmentStage.vue FEATURE_LABELS）。
// 兵哥 2026-10-02 要求「流程管理」中阶段包含功能全部中文展示（原模板直接渲染 code 导致出现 AUTO_MATCH 等英文）。
const FEATURE_LABEL: Record<string, string> = {
  RESUME_REVIEW: '简历评估',
  AUTO_MATCH: '自动匹配',
  BULK_IMPORT: '批量导入',
  CANDIDATE_INFO: '候选人信息',
  CANDIDATE_RESPONSE: '候选人回复',
  CODE_EDITOR: '代码编辑器',
  EVALUATION_FORM: '评估表单',
  INTERVIEW: '面试',
  INTERVIEWER: '面试官',
  TMPL_INTERVIEWER: '模板面试官',
  INTERVIEW_SCHEDULE: '面试安排',
  JOINT_INTERVIEW: '联合面试',
  MULTI_ROUND: '多轮面试',
  OFFER: 'Offer',
  OFFER_APPROVAL: 'Offer 审批',
  OFFER_GENERATION: 'Offer 生成',
  PHONE_CALL: '电话沟通',
  SCORING: '评分',
  VIDEO_RECORD: '视频录制',
  INVITE_FILTER: '邀约筛选',
  INVITE_UPDATE_INFO: '邀约信息更新',
  TRANSFER_STAGE: '阶段流转',
  ARCHIVE: '归档',
  NOTES: '备注',
  SCORE_RANK: '评分排名',
  DUPLICATE_CHECK: '查重',
  AI_SCORE: 'AI 评分',
  VOICE_RECORD: '语音记录',
  SALARY_NEGOTIATION: '薪资协商',
  BACKGROUND_CHECK: '背景调查',
  // 旧前端臆造 code（兼容老数据）
  ARRANGE_INTERVIEW: '安排面试',
  INVITE_INTERVIEW: '邀请面试',
  SEND_OFFER: '发送 Offer',
  START_BACKGROUND_CHECK: '发起背调',
  START_ONBOARDING: '发起入职',
}
function featureLabel(f: string): string {
  return FEATURE_LABEL[f] || f
}

const addModalColumns = [
  { title: t('pages.settings.ProcessStageEditor.s27'), key: 'code', width: 80 },
  { title: t('pages.settings.ProcessStageEditor.s28'), key: 'name', width: 120 },
  {
    title: t('pages.settings.ProcessStageEditor.s29'),
    key: 'stageType',
    width: 90,
    render: (r: any) => h(NTag, { type: getTypeColor(r.stageType), size: 'small' }, { default: () => r.stageType }),
  },
  {
    title: t('pages.settings.ProcessStageEditor.s30'),
    key: 'use',
    width: 100,
    render: (r: any) => h('span', { class: 'dim' }, t('pages.settings.ProcessStageEditor.s43', { n: r.referenceCount ?? r._count?.links ?? 0 })),
  },
  { title: t('pages.settings.ProcessStageEditor.s31'), key: 'features', render: (r: any) => {
    const feats = r.features ?? r.defaultFeatures
    return Array.isArray(feats) && feats.length > 0 ? feats.map((x: string) => featureLabel(x)).join('、') : '-'
  }},
  {
    title: t('pages.settings.ProcessStageEditor.s32'),
    key: 'action',
    width: 90,
    render: (r: any) => h(NButton, { size: 'small', type: 'primary', onClick: () => addToProcess(r) }, { default: () => t('pages.settings.ProcessStageEditor.s44') }),
  },
]

async function loadProcess() {
  if (!processId.value) return
  loading.value = true
  try {
    const p = await getProcess(processId.value)
    processName.value = p.name
    // 后端用 links 字段
    links.value = p.links || []
    // 2026-07-03: FE 类型 'order' (apps/api/recruitment-process.ts:87) — 之前 a.orderIndex 是 undefined, 排序静默坏.
    orderedLinks.value = [...links.value].sort((a: any, b: any) => (a.order ?? 0) - (b.order ?? 0))
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.ProcessStageEditor.s45'))
  } finally {
    loading.value = false
  }
}

async function openAddModal() {
  showAddModal.value = true
  loadingAddModal.value = true
  try {
    const all = await listStages({ status: 'ENABLED' })
    // 排除已被引用的 + 系统预置起止阶段 (不可重复添加)
    const usedIds = new Set(links.value.map((l) => l.stageId))
    availableStages.value = all.filter(
      (s) => !usedIds.has(s.id) && !s.isStart && !s.isEnd
    )
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.ProcessStageEditor.s46'))
  } finally {
    loadingAddModal.value = false
  }
}

async function addToProcess(row: any) {
  try {
    await addProcessLink({
      processId: processId.value,
      stageId: row.id,
    })
    message.success(t('pages.settings.ProcessStageEditor.s33'))
    showAddModal.value = false
    loadProcess()
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.ProcessStageEditor.s47'))
  }
}

async function removeLink(link: any) {
  try {
    await deleteProcessLink(link.id)
    message.success(t('pages.settings.ProcessStageEditor.s34'))
    loadProcess()
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.ProcessStageEditor.s48'))
  }
}

async function onReorder(newList: any[]) {
  orderedLinks.value = newList
  const ids = newList.map((l: any) => l.id)
  try {
    await reorderProcessLinks(processId.value, ids)
    message.success(t('pages.settings.ProcessStageEditor.s35'))
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.ProcessStageEditor.s49'))
    loadProcess() // 重新加载以恢复
  }
}

function editLinkStageLimit(link: any) {
  limitForm.value = { linkId: link.id, stageLimit: link.stageLimit || 0 }
  showLimitModal.value = true
}

function editLinkCustomName(link: any) {
  // custom_name 为空串时 display_name 属性自动回退 stage.name（模型 custom_name 非 null）
  renameForm.value = { linkId: link.id, customName: link.customName || '' }
  showRenameModal.value = true
}

async function saveCustomName() {
  try {
    await updateProcessLink(renameForm.value.linkId, {
      customName: renameForm.value.customName.trim(),
    })
    message.success(t('pages.settings.ProcessStageEditor.s36'))
    showRenameModal.value = false
    loadProcess()
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.ProcessStageEditor.s50'))
  }
}

async function saveStageLimit() {
  try {
    const stageLimit = limitForm.value.stageLimit
    await updateProcessLink(limitForm.value.linkId, {
      stageLimit: stageLimit && stageLimit > 0 ? stageLimit : undefined,
    })
    message.success(t('pages.settings.ProcessStageEditor.s37'))
    showLimitModal.value = false
    loadProcess()
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.ProcessStageEditor.s50'))
  }
}

function goRules(link: any) {
  router.push(`/settings/process-rules?processId=${processId.value}&linkId=${link.id}&tab=rule`)
}

function goConditions(link: any) {
  router.push(`/settings/process-rules?processId=${processId.value}&linkId=${link.id}&tab=condition`)
}

onMounted(() => loadProcess())
</script>

<style scoped>
/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header {
  flex-shrink: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}


/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
.page-header {
  flex-shrink: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}


.process-stage-editor {
  padding: 20px var(--space-6);
}
/* 删除 scoped .page-header margin-bottom 覆盖（规范：复用全局 glass.css 通栏分隔线规则） */
.page-header h2 {
  margin: 0;
  font-size: var(--fs-18);
  font-weight: 600;
}
.empty-state {
  padding: 60px 0;
  text-align: center;
}
.stage-card {
  margin-bottom: var(--space-2);
  cursor: move;
  transition: all var(--duration-base) var(--ease-out);
}
.stage-card:hover {
  box-shadow: var(--shadow-sm);
}
.stage-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stage-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.stage-code {
  font-family: monospace;
  color: var(--n-500);
  font-size: var(--fs-13);
}
.stage-name {
  font-weight: 500;
  font-size: var(--fs-15);
}
.sys-tag {
  font-size: 11px;
  color: var(--c-warning);
  background: var(--c-warning-soft); /* v2.8 T2.8.3: 浅黄 → var(--c-warning-soft) */
  padding: 1px 6px;
  border-radius: 3px;
}
.stage-limit {
  font-size: var(--fs-12);
  color: var(--n-450);
}
.stage-actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}
.stage-features {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-top: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px dashed var(--glass-border);
}
.feature-chip {
  font-size: 11px;
  color: var(--n-500);
  background: var(--g1);
  padding: 2px 6px;
  border-radius: 3px;
}
</style>
