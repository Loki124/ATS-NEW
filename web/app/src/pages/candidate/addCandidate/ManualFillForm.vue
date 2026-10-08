<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed } from 'vue'
import { useAddCandidateStore } from '@/stores/addCandidate'
import { NButton, useMessage } from 'naive-ui'

const { t } = useI18n()
const store = useAddCandidateStore()
const message = useMessage()

const form = ref({
  name: '',
  phone: '',
  email: '',
  gender: '',
  age: null as number | null,
  file_name: '',
})
const submitting = ref(false)

// name/phone/email 必填（与 Step1 校验 passesValidation 对齐）
const canSubmit = computed(
  () => !!form.value.name.trim() && !!form.value.phone.trim() && !!form.value.email.trim(),
)

async function onAdd() {
  if (!canSubmit.value) {
    message.warning(t('pages.candidate.addCandidate.ManualFillForm.s7'))
    return
  }
  submitting.value = true
  try {
    await store.addManualResume({
      name: form.value.name.trim(),
      phone: form.value.phone.trim(),
      email: form.value.email.trim(),
      gender: form.value.gender || undefined,
      age: form.value.age,
      file_name: form.value.file_name.trim() || undefined,
    })
    message.success(t('pages.candidate.addCandidate.ManualFillForm.s8'))
    // 重置以便连续录入多位候选人
    form.value = { name: '', phone: '', email: '', gender: '', age: null, file_name: '' }
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    message.error(detail || t('pages.candidate.addCandidate.ManualFillForm.s9'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="manual-form">
    <div class="mf-head">
      <div class="mf-title">{{ t('pages.candidate.addCandidate.ManualFillForm.s1') }}</div>
      <button class="mf-switch" type="button" @click="store.entryMode = 'upload'">
        {{ t('pages.candidate.addCandidate.ManualFillForm.s2') }}
      </button>
    </div>

    <div class="mf-grid">
      <div class="fg">
        <label>{{ t('pages.candidate.addCandidate.ManualFillForm.s3') }}<span class="req">*</span></label>
        <input v-model="form.name" data-testid="manual-name" :placeholder="t('pages.candidate.addCandidate.ManualFillForm.s3')" />
      </div>
      <div class="fg">
        <label>{{ t('pages.candidate.addCandidate.ManualFillForm.s4') }}</label>
        <select v-model="form.gender">
          <option value="">{{ t('pages.candidate.addCandidate.ManualFillForm.s10') }}</option>
          <option value="男">{{ t('pages.candidate.addCandidate.Step1Single.s5') }}</option>
          <option value="女">{{ t('pages.candidate.addCandidate.Step1Single.s6') }}</option>
        </select>
      </div>
      <div class="fg">
        <label>{{ t('pages.candidate.addCandidate.ManualFillForm.s5') }}<span class="req">*</span></label>
        <input v-model="form.phone" data-testid="manual-phone" :placeholder="t('pages.candidate.addCandidate.ManualFillForm.s5')" />
      </div>
      <div class="fg">
        <label>{{ t('pages.candidate.addCandidate.ManualFillForm.s6') }}<span class="req">*</span></label>
        <input v-model="form.email" data-testid="manual-email" :placeholder="t('pages.candidate.addCandidate.ManualFillForm.s6')" />
      </div>
      <div class="fg">
        <label>{{ t('pages.candidate.addCandidate.ManualFillForm.s11') }}</label>
        <input v-model.number="form.age" type="number" min="0" max="120" :placeholder="t('pages.candidate.addCandidate.ManualFillForm.s11')" />
      </div>
    </div>

    <div class="mf-actions">
      <n-button
        type="primary"
        :disabled="!canSubmit || submitting"
        :loading="submitting"
        data-testid="manual-add-btn"
        @click="onAdd"
      >
        {{ t('pages.candidate.addCandidate.ManualFillForm.s12') }}
      </n-button>
      <span v-if="store.resumes.length > 0" class="mf-count">
        {{ t('pages.candidate.addCandidate.ManualFillForm.s13', { n: store.resumes.length }) }}
      </span>
    </div>
  </div>
</template>

<style scoped>
@import './step1-shared.css';

.manual-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--glass-bg-card);
  border: 1px solid var(--g3);
  border-radius: 8px;
}
.mf-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mf-title {
  font-size: var(--fs-14);
  font-weight: 600;
  color: var(--g7);
}
.mf-switch {
  background: none;
  border: none;
  color: var(--brand);
  font-size: var(--fs-12);
  cursor: pointer;
  padding: var(--space-1);
}
.mf-switch:hover {
  text-decoration: underline;
}
.mf-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-3);
}
.mf-grid .fg {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.mf-grid .req {
  color: var(--c-error-deep);
  margin-left: 2px;
}
.mf-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.mf-count {
  font-size: var(--fs-12);
  color: var(--g6);
}
</style>
