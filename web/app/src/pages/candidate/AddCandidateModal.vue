<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, watch } from 'vue'
import { NModal, NButton, useDialog } from 'naive-ui'
import { useAddCandidateStore } from '@/stores/addCandidate'
import Stepper from './addCandidate/Stepper.vue'
import Step1Single from './addCandidate/Step1Single.vue'
import Step1Batch from './addCandidate/Step1Batch.vue'
import ManualFillForm from './addCandidate/ManualFillForm.vue'
import Step2Assign from './addCandidate/Step2Assign.vue'
import ScoringOverlay from './addCandidate/ScoringOverlay.vue'
import AsyncResult from './addCandidate/AsyncResult.vue'
import UploadZone from '@/components/common/UploadZone.vue'
import { replaceFile as apiReplaceFile } from '@/api/addCandidate'
const { t } = useI18n()

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ (e: 'update:show', v: boolean): void; (e: 'created'): void }>()

const store = useAddCandidateStore()
const fileInput = ref<HTMLInputElement | null>(null)
const dialog = useDialog()

// 2026-09-27: 父组件（CandidateList.handleAddSuccess）在提交成功后直接置
// v-model:show=false 关闭弹窗——v-model 下父组件改 prop 不会触发本组件的
// showModal setter，于是 store.reset() 从不执行：step 残留为 3、评分浮层状态残留，
// 再次打开弹窗直接渲染 step===3 的 ScoringOverlay，显示卡死的"正在处理..."。
// 修法：以「弹窗是否打开」为准，打开即复位，关闭即停流；与关闭路径解耦。
watch(
  () => props.show,
  (v) => {
    if (v) {
      store.closeStream()
      store.reset()
    } else {
      store.closeStream()
    }
  },
)

// P1 整改：移除原生 confirm()，统一用 useDialog().warning()
function tryClose() {
  if (store.isDirty) {
    dialog.warning({
      title: '有未保存的修改',
      content: '确认关闭？未保存的修改将丢失。',
      positiveText: '确认关闭',
      negativeText: '取消',
      onPositiveClick: () => {
        store.closeStream()
        store.reset()
        emit('update:show', false)
      },
    })
    return
  }
  store.closeStream()
  store.reset()
  emit('update:show', false)
}

const showModal = computed({
  get: () => props.show,
  set: (v) => {
    if (!v) {
      // 用户尝试关闭 (X / mask / esc) -> 走 dirty 检查
      if (store.isDirty) {
        tryClose()
        return
      }
      store.closeStream()
      store.reset()
    }
    emit('update:show', v)
  },
})

function closeModal() {
  if (store.isDirty) {
    tryClose()
    return
  }
  store.closeStream()
  store.reset()
  showModal.value = false
}

async function handleFiles(files: File[]) {
  if (files.length === 0) {
    fileInput.value?.click()
    return
  }
  await store.uploadFiles(files)
  // 启动所有 draft 的轮询
  for (const r of store.resumes) {
    await store.pollParseStatus(r.id)
  }
}

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const files = target.files ? Array.from(target.files) : []
  target.value = ''  // reset so same file can be selected again
  if (files.length > 0) {
    handleFiles(files)
  }
}

async function handleReplace(draftId: string) {
  const fi = document.createElement('input')
  fi.type = 'file'
  fi.accept = '.pdf,.doc,.docx,.txt'
  fi.onchange = async () => {
    if (!fi.files || fi.files.length === 0) return
    const file = fi.files[0]
    store.replaceResumeFile(draftId, file.name)
    const resp = await apiReplaceFile(draftId, file)
    // 把后端返回的新 job_id 传入 pollParseStatus, 让它轮询新的 job
    if (resp && resp.job_id) {
      await store.pollParseStatus(draftId, resp.job_id)
    } else {
      await store.pollParseStatus(draftId)
    }
  }
  fi.click()
}

const submitting = ref(false)
async function handleSubmit() {
  submitting.value = true
  try {
    await store.submit()
    emit('created')
  } finally {
    submitting.value = false
  }
}

function nextStep() {
  store.step = 2
}
</script>

<template>
  <n-modal v-model:show="showModal" preset="card" style="width: 960px; max-width: 90vw;" :bordered="false" :mask-closable="false" data-testid="add-candidate-modal">
    <template #header>
      <div style="display:flex;align-items:center;gap: var(--space-2);">
        <span style="font-size: var(--fs-18);font-weight:700;">{{ t('pages.candidate.AddCandidateModal.s1') }}</span>
        <span style="font-size:11px;color:var(--g5);">V2</span>
      </div>
    </template>

    <div style="display:flex;flex-direction:column;height:min(80vh,700px);">
<!-- P5 整改：height:80vh -> min(80vh,700px)，避免极长弹窗撑爆屏 -->
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.doc,.docx,.txt"
        multiple
        style="display:none"
        data-testid="hidden-file-input"
        @change="onFileChange"
      />
      <Stepper />

      <div v-if="store.step === 1" style="flex:1;display:flex;overflow:hidden;">
        <!-- 手动填写模式：表单 + 已添加列表（无文件建草稿） -->
        <div v-if="store.entryMode === 'manual'" style="flex:1;display:flex;flex-direction:column;overflow:auto;padding:16px 20px;gap:var(--space-3);">
          <ManualFillForm />
          <!-- 2026-10-08 布局修复: Step1Single/Step1Batch 是「左详情 .left-panel(flex:1) + 右查重 .right-panel(340px)」
               双根横向片段，设计给上传模式的 row 容器（本文件下方 v-else 分支同构）。
               29201d8a 将其直接投入 column 容器后：左栏 flex-basis:0 + overflow:auto 触发自动最小尺寸归零
               → 塌缩成半截头像；右栏 340px 纵向堆叠到左下 → 查重/重复信息/处理选项挤成窄条。
               包一层 row 容器恢复横向双栏（min-height:0 让双栏在剩余高度内各自滚动）。 -->
          <div v-if="store.resumes.length === 1" style="flex:1;display:flex;min-height:0;">
            <Step1Single @replace="handleReplace" />
          </div>
          <div v-else-if="store.resumes.length > 1" style="flex:1;display:flex;min-height:0;">
            <Step1Batch @upload="handleFiles" />
          </div>
        </div>
        <!-- 上传简历模式（默认） -->
        <template v-else>
          <div v-if="store.resumes.length === 0" style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;gap:var(--space-4);">
            <div class="entry-tabs">
              <button :class="['entry-tab', store.entryMode === 'upload' ? 'active' : '']" type="button" @click="store.entryMode = 'upload'">{{ t('pages.candidate.AddCandidateModal.s4') }}</button>
              <button :class="['entry-tab', store.entryMode === 'manual' ? 'active' : '']" type="button" @click="store.entryMode = 'manual'">{{ t('pages.candidate.AddCandidateModal.s5') }}</button>
            </div>
            <UploadZone @upload="handleFiles" />
          </div>
          <Step1Single v-else-if="store.resumes.length === 1" @replace="handleReplace" />
          <Step1Batch v-else @upload="handleFiles" />
        </template>
      </div>

      <div v-else-if="store.step === 2" style="flex:1;display:flex;overflow:hidden;">
        <Step2Assign :submitting="submitting" @back="store.step = 1" @submit="handleSubmit" />
      </div>

      <div v-else-if="store.step === 3" style="flex:1;display:flex;overflow:hidden;">
        <ScoringOverlay v-if="store.submitMode === 'wait' || !store.asyncResult" @close="closeModal" />
        <AsyncResult v-else @close="closeModal" />
      </div>
    </div>

    <template v-if="store.step === 1 && store.resumes.length > 0" #footer>
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <n-button @click="closeModal">{{ t('pages.candidate.AddCandidateModal.s2') }}</n-button>
        <n-button type="primary" :disabled="!store.canGoStep2" data-testid="next-step-btn" @click="nextStep">
          {{ t('pages.candidate.AddCandidateModal.s3') }}
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<style scoped>
.entry-tabs {
  display: inline-flex;
  padding: 3px;
  background: var(--g1);
  border: 1px solid var(--g3);
  border-radius: 999px;
}
.entry-tab {
  padding: 6px 18px;
  border: none;
  background: none;
  border-radius: 999px;
  font-size: var(--fs-12);
  font-weight: 500;
  color: var(--g6);
  cursor: pointer;
  transition: 0.15s;
}
.entry-tab.active {
  background: var(--brand);
  color: #fff;
}
.entry-tab:not(.active):hover {
  color: var(--brand);
}
</style>