<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { useAddCandidateStore } from '@/stores/addCandidate'
import StatusTag from '@/components/common/StatusTag.vue'
import CheckBanner from '@/components/common/CheckBanner.vue'
import DuplicateInfoCard from '@/components/common/DuplicateInfoCard.vue'
import OccupiedActions from '@/components/common/OccupiedActions.vue'
import ApplyPositionSelector from '@/components/common/ApplyPositionSelector.vue'
import ScorePanel from '@/components/common/ScorePanel.vue'
const { t } = useI18n()

const store = useAddCandidateStore()
const emit = defineEmits<{ (e: 'replace', draftId: string): void }>()
const resume = computed(() => store.resumes[0])
const isOccupied = computed(() => resume.value?.status === 'occupied')
const isUnocc = computed(() => resume.value?.status === 'unocc')
const positions = ['高级前端工程师', '资深前端工程师', '前端架构师', 'Web前端Leader', '全栈工程师']

function onField(field: string, e: Event) {
  if (!resume.value) return
  const v = (e.target as HTMLInputElement).value
  store.updateField(resume.value.id, field as any, v)
  store.triggerRecheck(resume.value.id)
}

function onAction(_draftId: string, action: any) {
  if (!resume.value) return
  if (action === 'apply') {
    store.setOccupyAction(resume.value.id, 'apply')
  } else {
    store.setOccupyAction(resume.value.id, action)
  }
}

function onSelectPos(pos: string) {
  if (!resume.value) return
  store.selectApplyPos(resume.value.id, pos)
}
</script>

<template>
  <div v-if="resume" class="left-panel">
    <div v-if="resume.parseError" class="parse-error">
      <span class="pe-icon">⚠</span><span>{{ resume.parseError }}</span>
    </div>
    <div class="detail-header">
      <div class="detail-avatar">{{ resume.parsed?.name?.charAt(0) || resume.file_name.charAt(0) }}</div>
      <div style="flex:1;min-width:0">
        <div class="detail-name">
          {{ resume.parsed?.name || resume.file_name }}
          <StatusTag :status="resume.status" />
        </div>
        <div class="detail-file">{{ resume.file_name }}</div>
      </div>
      <div class="detail-header-actions">
        <button class="replace-file-btn" data-testid="replace-file" @click="emit('replace', resume.id)">{{ t('pages.candidate.addCandidate.Step1Single.s1') }}</button>
      </div>
    </div>

    <!-- Basic info section -->
    <div class="detail-section">
      <div class="detail-section-title">{{ t('pages.candidate.addCandidate.Step1Single.s2') }}</div>
      <div class="frow">
        <div class="fg">
<label>{{ t('pages.candidate.addCandidate.Step1Single.s3') }}</label>
          <input :value="resume.parsed?.name || ''" data-testid="field-name" @change="onField('name', $event)" />
        </div>
        <div class="fg">
<label>{{ t('pages.candidate.addCandidate.Step1Single.s4') }}</label>
          <select :value="resume.parsed?.gender || ''" @change="onField('gender', $event)">
            <option value="男">{{ t('pages.candidate.addCandidate.Step1Single.s5') }}</option>
            <option value="女">{{ t('pages.candidate.addCandidate.Step1Single.s6') }}</option>
          </select>
        </div>
      </div>
      <div class="frow">
        <div class="fg">
<label>{{ t('pages.candidate.addCandidate.Step1Single.s7') }}</label>
          <input :value="resume.parsed?.age || ''" @change="onField('age', $event)" />
        </div>
        <div class="fg">
<label>{{ t('pages.candidate.addCandidate.Step1Single.s8') }}</label>
          <input :value="resume.parsed?.phone || ''" data-testid="field-phone" @change="onField('phone', $event)" />
        </div>
      </div>
      <div class="frow">
        <div class="fg">
<label>{{ t('pages.candidate.addCandidate.Step1Single.s9') }}</label>
          <input :value="resume.parsed?.email || ''" data-testid="field-email" @change="onField('email', $event)" />
        </div>
        <div class="fg">
<label>{{ t('pages.candidate.addCandidate.Step1Single.s10') }}</label>
          <input :value="resume.file_name" disabled style="background: var(--g1);" />
        </div>
      </div>
    </div>

    <!-- Education -->
    <div v-if="resume.parsed?.educations?.length" class="detail-section">
      <div class="detail-section-title">{{ t('pages.candidate.addCandidate.Step1Single.s11') }} <span class="seg-count">{{ resume.parsed.educations.length }} 段</span></div>
      <div v-for="(edu, i) in resume.parsed.educations" :key="i" class="seg-item">
        <div class="seg-header"><span class="seg-num">{{ i + 1 }}</span> {{ edu.period }} · {{ edu.school }}</div>
        <div class="seg-readonly"><div class="seg-line"><span>{{ edu.school }}</span><span>{{ edu.major }}</span><span>{{ edu.degree }}</span></div></div>
      </div>
    </div>

    <!-- Experience -->
    <div v-if="resume.parsed?.experiences?.length" class="detail-section">
      <div class="detail-section-title">{{ t('pages.candidate.addCandidate.Step1Single.s12') }} <span class="seg-count">{{ resume.parsed.experiences.length }} 段</span></div>
      <div v-for="(exp, i) in resume.parsed.experiences" :key="i" class="seg-item">
        <div class="seg-header"><span class="seg-num">{{ i + 1 }}</span> {{ exp.period }} · {{ exp.company }} · {{ exp.position }}</div>
        <div style="font-size: var(--fs-10);color:var(--g5);margin-top: var(--space-1);">{{ exp.summary }}</div>
      </div>
    </div>
  </div>

  <div v-if="resume" class="right-panel">
    <div class="rp-section">
<div class="rp-title">{{ t('pages.candidate.addCandidate.Step1Single.s13') }}</div>
      <CheckBanner :status="resume.duplicate?.status || 'clean'" />
    </div>

    <div v-if="(isOccupied || isUnocc) && resume.duplicate" class="rp-section">
      <div class="rp-title">{{ t('pages.candidate.addCandidate.Step1Single.s14') }}</div>
      <DuplicateInfoCard :info="resume.duplicate" :status="resume.status" />
    </div>

    <div v-if="resume.occupyAction === 'apply'" class="rp-section">
      <ApplyPositionSelector :positions="positions" :model-value="resume.appliedPosition || ''" @update:model-value="onSelectPos" />
    </div>

    <div v-if="isOccupied" class="rp-section">
      <div class="rp-title">{{ t('pages.candidate.addCandidate.Step1Single.s15') }}</div>
      <OccupiedActions :draft-id="resume.id" @action="onAction" />
    </div>

    <div v-if="resume.scoreSnapshot" class="rp-section">
      <ScorePanel :score="resume.scoreSnapshot" />
    </div>

    <div class="rp-section">
<div class="rp-title">{{ t('pages.candidate.addCandidate.Step1Single.s16') }}</div>
      <div class="nbar info">{{ t('pages.candidate.addCandidate.Step1Single.s17') }}<br>• <strong>{{ t('pages.candidate.addCandidate.Step1Single.s18') }}</strong>{{ t('pages.candidate.addCandidate.Step1Single.s19') }}<br>• <strong>{{ t('pages.candidate.addCandidate.Step1Single.s20') }}</strong>{{ t('pages.candidate.addCandidate.Step1Single.s21') }}<br>• <strong>{{ t('pages.candidate.addCandidate.Step1Single.s22') }}</strong>{{ t('pages.candidate.addCandidate.Step1Single.s23') }}</div>
    </div>
  </div>
</template>

<style scoped>
@import './step1-shared.css';

.detail-view { display: flex; flex-direction: column; gap: var(--space-4); }
.detail-section { display: flex; flex-direction: column; gap: var(--space-1); }
.detail-section-title {
  font-size: var(--fs-12);
  font-weight: 600;
  color: var(--g7);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--g2);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.seg-count {
  font-size: var(--fs-10);
  color: var(--g5);
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
}
.detail-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--g3);
}
.detail-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--brand-a12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-20);
  color: var(--brand);
  font-weight: 600;
  flex-shrink: 0;
}
.detail-name {
  font-size: var(--fs-18);
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.detail-file { font-size: var(--fs-12); color: var(--g5); margin-top: 2px; }
.detail-header-actions {
  margin-left: auto;
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.parse-error {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--c-error-bg);
  border: 1px solid var(--c-error-deep);
  border-radius: 8px;
  color: var(--c-error-deep);
  font-size: var(--fs-12);
  line-height: 1.5;
}
.parse-error .pe-icon { flex-shrink: 0; }
</style>
