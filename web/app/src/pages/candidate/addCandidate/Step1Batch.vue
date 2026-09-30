<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { NIcon } from 'naive-ui'
import { WarningOutline as AlertTriangle } from '@vicons/ionicons5'
import { useAddCandidateStore } from '@/stores/addCandidate'
import ResumeCard from '@/components/common/ResumeCard.vue'
import UploadZone from '@/components/common/UploadZone.vue'
const { t } = useI18n()

const store = useAddCandidateStore()
const emit = defineEmits<{ (e: 'upload', files: File[]): void }>()

function counts(s: string) { return store.resumes.filter((r) => r.status === s).length }
const isAllDone = () => store.resumes.every((r) => r.status !== 'processing')
const occupiedCount = () => store.resumes.filter((r) => r.status === 'occupied').length
</script>

<template>
  <div class="left-panel">
    <UploadZone v-if="store.resumes.length === 0" @upload="emit('upload', $event)" />

    <template v-else>
      <div class="status-summary">
        <span v-if="counts('processing') > 0" class="st-pill processing"><span class="st-dot"></span>{{ counts('processing') }}{{ t('pages.candidate.addCandidate.Step1Batch.s6') }}</span>
        <span v-if="counts('clean') > 0" class="st-pill clean"><span class="st-dot"></span>{{ counts('clean') }}{{ t('pages.candidate.addCandidate.Step1Batch.s7') }}</span>
        <span v-if="counts('unocc') > 0" class="st-pill unocc"><span class="st-dot"></span>{{ counts('unocc') }}{{ t('pages.candidate.addCandidate.Step1Batch.s8') }}</span>
        <span v-if="counts('occupied') > 0" class="st-pill occupied"><span class="st-dot"></span>{{ counts('occupied') }}{{ t('pages.candidate.addCandidate.Step1Batch.s9') }}</span>
      </div>

      <div v-if="store.selectedIds.length > 0" class="bulk-bar">
        {{ t('pages.candidate.addCandidate.Step1Batch.s16') }} <span class="bulk-count">{{ store.selectedIds.length }}</span> {{ t('pages.candidate.addCandidate.Step1Batch.s17') }}
        <button class="btn bs" style="font-size: var(--fs-10);padding: 3px var(--space-2);">{{ t('pages.candidate.addCandidate.Step1Batch.s1') }}</button>
        <button class="btn bs" style="font-size: var(--fs-10);padding: 3px var(--space-2);" @click="store.selectedIds = []">{{ t('pages.candidate.addCandidate.Step1Batch.s2') }}</button>
      </div>

      <div v-if="isAllDone()" class="upload-zone" style="padding:10px 14px;border-style:dashed;margin-bottom:10px;cursor:pointer;display:flex;align-items:center;gap: var(--space-2);font-size:11px;text-align:left;" @click="emit('upload', [])">
        <span style="font-size: var(--fs-18);">📎</span>
        <span style="flex:1;color:var(--g6);">{{ t('pages.candidate.addCandidate.Step1Batch.s3') }}<span style="color:var(--brand);font-weight:500;">{{ t('pages.candidate.addCandidate.Step1Batch.s4') }}</span>{{ t('pages.candidate.addCandidate.Step1Batch.s5') }}</span>
        <span style="font-size: var(--fs-10);color:var(--g5);">PDF / Word / TXT</span>
      </div>

      <div class="card-list">
        <ResumeCard
          v-for="r in store.resumes"
          :key="r.id"
          :resume="r"
          :active="store.activeId === r.id"
          :selected="store.selectedIds.includes(r.id)"
          @toggle="store.activeId = store.activeId === r.id ? null : r.id"
          @select="store.selectedIds.includes(r.id) ? store.selectedIds = store.selectedIds.filter(i => i !== r.id) : store.selectedIds.push(r.id)"
        />
      </div>
    </template>
  </div>

  <div class="right-panel">
    <div v-if="occupiedCount() > 0" class="rp-section">
      <div class="rp-title"><NIcon :size="15" style="vertical-align:-2px;margin-right:4px;color:var(--c-warning-deep)" aria-hidden="true"><AlertTriangle /></NIcon>{{ t('pages.candidate.addCandidate.Step1Batch.s10') }}</div>
      <div class="nbar error"><strong>{{ t('pages.candidate.addCandidate.Step1Batch.s18', { n: occupiedCount() }) }}</strong><br>{{ t('pages.candidate.addCandidate.Step1Batch.s19') }}</div>
    </div>
    <div class="rp-section">
      <div class="rp-title">{{ t('pages.candidate.addCandidate.Step1Batch.s11') }}</div>
      <div class="nbar info">{{ t('pages.candidate.addCandidate.Step1Batch.s20') }}<br>• <strong>{{ t('pages.candidate.addCandidate.Step1Batch.s12') }}</strong>{{ t('pages.candidate.addCandidate.Step1Batch.s21') }}<br>• <strong>{{ t('pages.candidate.addCandidate.Step1Batch.s13') }}</strong>{{ t('pages.candidate.addCandidate.Step1Batch.s22') }}<br>• <strong>{{ t('pages.candidate.addCandidate.Step1Batch.s14') }}</strong>{{ t('pages.candidate.addCandidate.Step1Batch.s15') }}</div>
    </div>
  </div>
</template>

<style scoped>
@import './step1-shared.css';

.status-summary { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.st-pill {
  padding: var(--space-1) 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}
.st-pill .st-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.st-pill.processing { background: var(--c-info-soft); color: var(--c-info-deep); }
.st-pill.processing .st-dot { background: var(--c-info); animation: pulse2 1s infinite; }
.st-pill.clean { background: var(--sl); color: var(--c-success-deep); }
.st-pill.clean .st-dot { background: var(--c-success); }
.st-pill.unocc { background: var(--wl); color: var(--c-warning-deep); }
.st-pill.unocc .st-dot { background: var(--w); }
.st-pill.occupied { background: var(--c-error-bg); color: var(--c-error-deep); }
.st-pill.occupied .st-dot { background: var(--c-error-deep); }
@keyframes pulse2 { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
.legend { display: flex; gap: var(--space-3); font-size: var(--fs-10); color: var(--g5); flex-wrap: wrap; }
.legend span { display: flex; align-items: center; gap: var(--space-1); }
.legend .ld { width: 6px; height: 6px; border-radius: 50%; }
.legend .ld.lg { background: var(--c-success); }
.legend .ld.ly { background: var(--w); }
.legend .ld.lr { background: var(--c-error-deep); }
.legend .ld.lb { background: var(--c-info); }
.bulk-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: var(--space-2) var(--space-3);
  background: var(--brand-a12);
  border-radius: 8px;
  font-size: 11px;
  color: var(--c-info-deep);
}
.bulk-count { font-weight: 600; }
.upload-zone {
  border: 2px dashed var(--g4);
  border-radius: 12px;
  padding: var(--space-8) 20px;
  text-align: center;
  cursor: pointer;
  transition: 0.15s;
  background: var(--g1);
}
.upload-zone:hover { border-color: var(--brand); background: var(--brand-a12); }
.upload-zone.dragover {
  border-color: var(--brand);
  background: var(--brand-a12);
  box-shadow: 0 0 0 3px var(--overlay-scrim-mid);
}
.upload-zone .up-icon { font-size: var(--fs-36); margin-bottom: var(--space-2); transition: 0.2s; }
.upload-zone.dragover .up-icon { transform: scale(1.1); }
.upload-zone .up-text { font-size: var(--fs-13); font-weight: 500; color: var(--g7); }
.upload-zone .up-hint { font-size: 11px; color: var(--g5); margin-top: var(--space-1); }
.upload-zone .up-quick { display: flex; gap: var(--space-2); justify-content: center; margin-top: var(--space-3); }
/* v2 bugfix P0-C: 业务页白底透出极光 */
.upload-zone .up-quick span {
  font-size: 11px;
  padding: var(--space-1) 10px;
  background: var(--glass-bg-card);
  border: 1px solid var(--g3);
  border-radius: 20px;
  color: var(--g6);
  cursor: pointer;
}
.upload-zone .up-quick span:hover { border-color: var(--brand); color: var(--brand); }
.card-list { display: flex; flex-direction: column; gap: var(--space-2); }
/* v2 bugfix P0-C: 业务卡片白底 → 玻璃 */
.card-item {
  border: 1px solid var(--g3);
  border-radius: 8px;
  background: var(--glass-bg-card);
  overflow: hidden;
  transition: 0.15s;
}
.card-item:hover { border-color: var(--brand); }
.card-item.selected { border-color: var(--brand); box-shadow: 0 0 0 1px var(--overlay-scrim-mid); }
.card-item.occ { border-left: 3px solid var(--c-error-deep); }
.card-item.dir-set { border-left: 3px solid var(--c-success); }
.card-item.unocc { border-left: 3px solid var(--w); }
.card-item.clean { border-left: 3px solid var(--c-success); }
.card-item .c-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: var(--space-3) 14px;
  cursor: pointer;
}
.card-item .c-header .c-chk {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  border: 2px solid var(--g4);
  border-radius: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-item .c-header .c-chk.checked { background: var(--brand); border-color: var(--brand); }
.card-item .c-header .c-chk.checked::after { content: '✓'; color: var(--g1); font-size: var(--fs-10); }
.card-item .c-header .c-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--g2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-14);
  color: var(--g5);
  flex-shrink: 0;
  font-weight: 600;
}
.card-item .c-header .c-info { flex: 1; min-width: 0; }
.card-item .c-header .c-name {
  font-weight: 600;
  font-size: var(--fs-13);
  display: flex;
  align-items: center;
  gap: 6px;
}
.card-item .c-header .c-file { font-size: var(--fs-10); color: var(--g5); font-weight: 400; }
.card-item .c-header .c-basic {
  font-size: 11px;
  color: var(--g6);
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 2px;
}
.card-item .c-header .c-expand {
  font-size: var(--fs-16);
  color: var(--g5);
  transition: 0.2s;
  flex-shrink: 0;
}
.card-item.expanded .c-header .c-expand { transform: rotate(180deg); }
.card-item .c-body { display: none; padding: 0 14px 14px; border-top: 1px solid var(--g3); }
.card-item.expanded .c-body { display: block; }
.btn {
  padding: 7px 14px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  transition: 0.15s;
}
/* v2 bugfix P0-C: .bs 业务按钮白底 → 玻璃 */
.bs { background: var(--glass-bg-card); color: var(--g7); border: 1px solid var(--g4); }
.bs:hover { background: var(--g2); }
</style>
