<script setup lang="ts">
import { ref, computed } from 'vue'
import { NModal, NButton } from 'naive-ui'
import { useAddCandidateStore } from '@/stores/addCandidate'
import Stepper from './addCandidate/Stepper.vue'
import Step1Single from './addCandidate/Step1Single.vue'
import Step1Batch from './addCandidate/Step1Batch.vue'
import Step2Assign from './addCandidate/Step2Assign.vue'
import ScoringOverlay from './addCandidate/ScoringOverlay.vue'
import AsyncResult from './addCandidate/AsyncResult.vue'
import UploadZone from '@/components/common/UploadZone.vue'
import { replaceFile as apiReplaceFile } from '@/api/addCandidate'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ (e: 'update:show', v: boolean): void; (e: 'created'): void }>()

const store = useAddCandidateStore()
const fileInput = ref<HTMLInputElement | null>(null)

const showModal = computed({
  get: () => props.show,
  set: (v) => emit('update:show', v),
})

function closeModal() {
  if (store.isDirty) {
    if (!confirm('有未保存的修改，确认关闭？')) return
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

async function handleReplace(draftId: string) {
  const fi = document.createElement('input')
  fi.type = 'file'
  fi.accept = '.pdf,.doc,.docx,.txt'
  fi.onchange = async () => {
    if (!fi.files || fi.files.length === 0) return
    const file = fi.files[0]
    store.replaceResumeFile(draftId, file.name)
    await apiReplaceFile(draftId, file)
    await store.pollParseStatus(draftId)
  }
  fi.click()
}

async function handleSubmit() {
  await store.submit()
  emit('created')
}

function nextStep() {
  store.step = 2
}
</script>

<template>
  <n-modal v-model:show="showModal" preset="card" style="width: 960px;" :bordered="false" :mask-closable="false" data-testid="add-candidate-modal">
    <template #header>
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-size:18px;font-weight:700;">创建候选人</span>
        <span style="font-size:11px;color:var(--g5);">V2</span>
      </div>
    </template>

    <div style="display:flex;flex-direction:column;height:80vh;max-height:700px;">
      <Stepper />

      <div v-if="store.step === 1" style="flex:1;display:flex;overflow:hidden;">
        <div v-if="store.resumes.length === 0" style="flex:1;display:flex;align-items:center;justify-content:center;padding:20px;">
          <UploadZone @upload="handleFiles" />
        </div>
        <Step1Single v-else-if="store.resumes.length === 1" @replace="handleReplace" />
        <Step1Batch v-else @upload="handleFiles" />
      </div>

      <div v-else-if="store.step === 2" style="flex:1;display:flex;overflow:hidden;">
        <Step2Assign @back="store.step = 1" @submit="handleSubmit" />
      </div>

      <div v-else-if="store.step === 3" style="flex:1;display:flex;overflow:hidden;">
        <ScoringOverlay v-if="store.submitMode === 'wait' || !store.asyncResult" @close="closeModal" />
        <AsyncResult v-else @close="closeModal" />
      </div>
    </div>

    <template #footer v-if="store.step === 1 && store.resumes.length > 0">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <n-button @click="closeModal">取消</n-button>
        <n-button type="primary" :disabled="!store.canGoStep2" data-testid="next-step-btn" @click="nextStep">
          下一步：选择去向 & 提交
        </n-button>
      </div>
    </template>
  </n-modal>
</template>