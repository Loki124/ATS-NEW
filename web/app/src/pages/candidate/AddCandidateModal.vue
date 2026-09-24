<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, watch } from 'vue'
import { NModal, NButton, useDialog } from 'naive-ui'
import { useAddCandidateStore } from '@/stores/addCandidate'
import Stepper from './addCandidate/Stepper.vue'
import Step1Single from './addCandidate/Step1Single.vue'
import Step1Batch from './addCandidate/Step1Batch.vue'
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
        <span style="font-size: var(--fs-18);font-weight:700;">{ t('pages.candidate.AddCandidateModal.s1') }</span>
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
        <div v-if="store.resumes.length === 0" style="flex:1;display:flex;align-items:center;justify-content:center;padding:20px;">
          <UploadZone @upload="handleFiles" />
        </div>
        <Step1Single v-else-if="store.resumes.length === 1" @replace="handleReplace" />
        <Step1Batch v-else @upload="handleFiles" />
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
        <n-button @click="closeModal">取消</n-button>
        <n-button type="primary" :disabled="!store.canGoStep2" data-testid="next-step-btn" @click="nextStep">
          下一步：选择去向 & 提交
        </n-button>
      </div>
    </template>
  </n-modal>
</template>