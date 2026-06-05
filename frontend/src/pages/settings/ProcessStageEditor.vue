<template>
  <div class="process-stage-editor">
    <div class="page-header">
      <n-space align="center">
        <n-button text @click="$router.back()">
          <template #icon><n-icon :component="ArrowBackOutline" /></template>
          返回
        </n-button>
        <h2>{{ processName }} - 阶段配置</h2>
      </n-space>
      <n-button type="primary" @click="showAddModal = true" :disabled="!processId">
        <template #icon><n-icon :component="AddOutline" /></template>
        添加阶段
      </n-button>
    </div>

    <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
      从<strong>全局阶段模板库</strong>中选择阶段加入此流程。同一阶段在每个流程中只能添加一次。可拖拽调整顺序。
    </n-alert>

    <n-spin :show="loading">
      <div v-if="links.length === 0" class="empty-state">
        <n-empty description="该流程还没有阶段，点右上角「添加阶段」开始" />
      </div>
      <div v-else>
        <draggable-list v-model="orderedLinks" @update:model-value="onReorder">
          <template #item="{ element }">
            <n-card class="stage-card" size="small">
              <div class="stage-row">
                <div class="stage-info">
                  <n-tag v-if="element.isStart" type="success" size="small">起始</n-tag>
                  <n-tag v-if="element.isEnd" type="warning" size="small">结束</n-tag>
                  <n-tag :type="getTypeColor(element.stage.stageType)" size="small">
                    {{ element.stage.stageType }}
                  </n-tag>
                  <span class="stage-code">{{ element.stage.code }}</span>
                  <span class="stage-name">{{ element.customName || element.stage.name }}</span>
                  <span v-if="element.stage.isSystem" class="sys-tag">[系统]</span>
                  <span class="stage-limit" v-if="element.stageLimit">⏱ {{ element.stageLimit }}h</span>
                </div>
                <div class="stage-actions">
                  <n-button text size="small" type="primary" @click="goRules(element)">规则</n-button>
                  <n-button text size="small" type="primary" @click="goConditions(element)">条件</n-button>
                  <n-button text size="small" @click="editLinkStageLimit(element)">时长</n-button>
                  <n-popconfirm
                    v-if="!element.isStart && !element.isEnd"
                    @positive-click="removeLink(element)"
                  >
                    <template #trigger>
                      <n-button text size="small" type="error">移除</n-button>
                    </template>
                    从此流程中移除「{{ element.stage.name }}」？
                  </n-popconfirm>
                  <n-tag v-else type="default" size="small">起止不可移除</n-tag>
                </div>
              </div>
              <div v-if="element.stage.features?.length" class="stage-features">
                <span v-for="f in element.stage.features" :key="f" class="feature-chip">{{ f }}</span>
              </div>
            </n-card>
          </template>
        </draggable-list>
      </div>
    </n-spin>

    <!-- 添加阶段弹窗 - 从全局库选 -->
    <n-modal v-model:show="showAddModal" preset="card" title="从全局阶段库选择" style="width: 720px">
      <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
        只显示<strong>启用中</strong>且<strong>未被当前流程引用</strong>的阶段。
      </n-alert>
      <n-spin :show="loadingAddModal">
        <n-data-table
          :columns="addModalColumns"
          :data="availableStages"
          :row-key="(r) => r.id"
          :pagination="{ pageSize: 8 }"
        />
      </n-spin>
    </n-modal>

    <!-- 设置阶段时长弹窗 -->
    <n-modal v-model:show="showLimitModal" preset="card" title="设置阶段时长限制" style="width: 400px">
      <n-form :model="limitForm" label-placement="top">
        <n-form-item label="时长（小时）">
          <n-input-number v-model:value="limitForm.stageLimit" :min="0" placeholder="留空表示不限制" style="width: 100%" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showLimitModal = false">取消</n-button>
          <n-button type="primary" @click="saveStageLimit">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useMessage, NButton, NTag, NPopconfirm, NIcon, NSpace, NInputNumber, NForm, NFormItem, NModal, NDataTable, NAlert, NEmpty, NSpin, NCard } from 'naive-ui'
import { AddOutline, ArrowBackOutline } from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
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

const message = useMessage()
const route = useRoute()
const router = useRouter()

const processId = computed(() => route.query.processId as string)
const processName = ref('招聘流程')
const links = ref<any[]>([])
const orderedLinks = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const loadingAddModal = ref(false)
const availableStages = ref<any[]>([])
const showLimitModal = ref(false)
const limitForm = ref({ linkId: '', stageLimit: 0 })

// 类型颜色映射
function getTypeColor(type: string) {
  return ({ FILTER: 'info', INTERVIEW: 'success', OFFER: 'warning', ONBOARDING: 'error', INVITATION: 'default' } as any)[type] || 'default'
}

const addModalColumns = [
  { title: '编号', key: 'code', width: 80 },
  { title: '名称', key: 'name', width: 120 },
  {
    title: '类型',
    key: 'stageType',
    width: 90,
    render: (r: any) => h(NTag, { type: getTypeColor(r.stageType), size: 'small' }, { default: () => r.stageType }),
  },
  {
    title: '使用',
    key: 'use',
    width: 100,
    render: (r: any) => h('span', { class: 'dim' }, `${r._count?.links || 0} 个流程`),
  },
  { title: '功能项', key: 'features', render: (r: any) => Array.isArray(r.features) ? r.features.join(', ') : '-' },
  {
    title: '操作',
    key: 'action',
    width: 90,
    render: (r: any) => h(NButton, { size: 'small', type: 'primary', onClick: () => addToProcess(r) }, { default: () => '添加' }),
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
    orderedLinks.value = [...links.value].sort((a: any, b: any) => a.orderIndex - b.orderIndex)
  } catch (e: any) {
    message.error(e?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function openAddModal() {
  showAddModal.value = true
  loadingAddModal.value = true
  try {
    const all = await listStages({ status: 'ACTIVE' })
    // 排除已被引用的 + 起止（不可重复添加）
    const usedIds = new Set(links.value.map((l) => l.stageId))
    availableStages.value = all.filter((s) => !usedIds.has(s.id) && !s.isSystem ? true : !usedIds.has(s.id))
    // 系统预置起止阶段不能重复添加 - 已经在 create 时自动 link 了
    availableStages.value = availableStages.value.filter((s) => !s.isSystem || !usedIds.has(s.id))
  } catch (e: any) {
    message.error(e?.response?.data?.message || '加载候选阶段失败')
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
    message.success('已添加')
    showAddModal.value = false
    loadProcess()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '添加失败')
  }
}

async function removeLink(link: any) {
  try {
    await deleteProcessLink(link.id)
    message.success('已移除')
    loadProcess()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '移除失败')
  }
}

async function onReorder(newList: any[]) {
  orderedLinks.value = newList
  const ids = newList.map((l: any) => l.id)
  try {
    await reorderProcessLinks(processId.value, ids)
    message.success('顺序已保存')
  } catch (e: any) {
    message.error(e?.response?.data?.message || '顺序保存失败')
    loadProcess() // 重新加载以恢复
  }
}

function editLinkStageLimit(link: any) {
  limitForm.value = { linkId: link.id, stageLimit: link.stageLimit || 0 }
  showLimitModal.value = true
}

async function saveStageLimit() {
  try {
    await updateProcessLink(limitForm.value.linkId, {
      stageLimit: limitForm.value.stageLimit || null,
    })
    message.success('已保存')
    showLimitModal.value = false
    loadProcess()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '保存失败')
  }
}

function goRules(link: any) {
  // 留给下轮：阶段规则编辑器
  message.info(`阶段规则编辑器（${link.stage.name}）— 留待下轮实现`)
}

function goConditions(link: any) {
  // 留给下轮：进入条件可视化编辑器
  message.info(`进入条件编辑器（${link.stage.name}）— 留待下轮实现`)
}

onMounted(() => loadProcess())
</script>

<style scoped>
.process-stage-editor {
  padding: 20px 24px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.empty-state {
  padding: 60px 0;
  text-align: center;
}
.stage-card {
  margin-bottom: 8px;
  cursor: move;
  transition: all 0.2s;
}
.stage-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.stage-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stage-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.stage-code {
  font-family: monospace;
  color: #666;
  font-size: 13px;
}
.stage-name {
  font-weight: 500;
  font-size: 15px;
}
.sys-tag {
  font-size: 11px;
  color: #fa8c16;
  background: #fff7e6;
  padding: 1px 6px;
  border-radius: 3px;
}
.stage-limit {
  font-size: 12px;
  color: #888;
}
.stage-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}
.stage-features {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #eee;
}
.feature-chip {
  font-size: 11px;
  color: #666;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
}
</style>
