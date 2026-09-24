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
        <span v-if="counts('processing') > 0" class="st-pill processing"><span class="st-dot"></span>{{ counts('processing') }} 份处理中</span>
        <span v-if="counts('clean') > 0" class="st-pill clean"><span class="st-dot"></span>{{ counts('clean') }} 份无重复</span>
        <span v-if="counts('unocc') > 0" class="st-pill unocc"><span class="st-dot"></span>{{ counts('unocc') }} 份未占用</span>
        <span v-if="counts('occupied') > 0" class="st-pill occupied"><span class="st-dot"></span>{{ counts('occupied') }} 份需处理</span>
      </div>

      <div v-if="store.selectedIds.length > 0" class="bulk-bar">
        已选 <span class="bulk-count">{{ store.selectedIds.length }}</span> 份简历
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
      <div class="rp-title"><NIcon :size="15" style="vertical-align:-2px;margin-right:4px;color:var(--c-warning-deep)" aria-hidden="true"><AlertTriangle /></NIcon>需处理项</div>
      <div class="nbar error"><strong>有 {{ occupiedCount() }} 份简历已被占用，需要先处理。</strong><br>请展开对应简历卡片，选择处理方式后再进入下一步。</div>
    </div>
    <div class="rp-section">
      <div class="rp-title">步骤说明</div>
      <div class="nbar info">上传简历后系统将自动解析并查重。<br>• <strong>无重复</strong>：可直接进入下一步<br>• <strong>未占用</strong>：系统有记录但可合并<br>• <strong>需处理</strong>：已被占用，需选择处理方式</div>
    </div>
  </div>
</template>

<style scoped>
.left-panel {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4) 20px;
  border-right: 1px solid var(--g3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.right-panel {
  width: 340px;
  flex-shrink: 0;
  overflow-y: auto;
  padding: var(--space-4) 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
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
.cb {
  padding: var(--space-2) var(--space-3);
  border-radius: 8px;
  font-size: 11px;
  margin: var(--space-2) 0;
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  line-height: 1.5;
}
.cb .cb-icon { font-size: var(--fs-16); flex-shrink: 0; margin-top: 1px; }
.cb.clean { background: var(--sl); color: var(--c-success-deep); border: 1px solid var(--c-success-bg); }
.cb.unocc { background: var(--wl); color: var(--c-warning-deep); border: 1px solid var(--c-warning-bg); }
.cb.occupied { background: var(--c-error-bg); color: var(--c-error-deep); border: 1px solid var(--c-error-bg); }
.cb.processing { background: var(--c-info-soft); color: var(--c-info-deep); border: 1px solid var(--c-info-bg); }
.dup-card {
  border: 1px solid var(--c-warning-bg);
  border-radius: 8px;
  padding: 10px 14px;
  background: var(--g1);
  margin: var(--space-2) 0;
  font-size: 11px;
}
.dup-card .dup-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
.dup-card .dup-label { color: var(--g5); }
.dup-card .dup-value { font-weight: 500; }
.dup-card .dup-note {
  font-size: var(--fs-10);
  color: var(--c-warning-deep);
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--c-warning-bg);
}
.fst {
  font-size: var(--fs-10);
  font-weight: 600;
  color: var(--g6);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 10px;
  margin-bottom: 6px;
}
.frow { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: var(--space-2); }
.fg { display: flex; flex-direction: column; gap: 3px; }
.fg label { font-size: var(--fs-10); font-weight: 500; color: var(--g6); }
.fg input,
.fg select,
.fg textarea {
  padding: 6px var(--space-2);
  border: 1px solid var(--g4);
  border-radius: 5px;
  font-size: 11px;
  outline: none;
  font-family: inherit;
}
.fg input:focus,
.fg select:focus,
.fg textarea:focus { border-color: var(--brand); box-shadow: 0 0 0 2px var(--overlay-scrim-mid); }
.fg textarea { resize: vertical; min-height: 50px; }
.seg-item {
  border: 1px solid var(--g3);
  border-radius: 8px;
  padding: 10px var(--space-3);
  background: var(--g1);
  margin-top: 6px;
}
.seg-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--g6);
  margin-bottom: 6px;
}
.seg-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--brand-a12);
  color: var(--brand);
  font-size: var(--fs-10);
  font-weight: 700;
}
.seg-readonly { font-size: 11px; color: var(--g7); line-height: 1.6; }
.seg-line { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.seg-readonly .seg-line span { color: var(--g6); }
.recheck-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 6px 10px;
  background: var(--g1);
  border: 1px solid var(--c-info-bg);
  border-radius: 8px;
  font-size: var(--fs-10);
  color: var(--c-info-deep);
  margin: var(--space-2) 0;
}
.recheck-bar .spin2 {
  width: 12px;
  height: 12px;
  border: 2px solid var(--c-info-bg);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }
.occ-actions { display: flex; gap: 6px; margin-top: var(--space-2); flex-wrap: wrap; }
/* v2 bugfix P0-C: 业务按钮白底 → 玻璃 */
.occ-btn {
  padding: 5px var(--space-3);
  border: 1px solid var(--g3);
  border-radius: 8px;
  font-size: var(--fs-10);
  cursor: pointer;
  transition: 0.15s;
  background: var(--glass-bg-card);
  color: var(--g7);
}
.occ-btn:hover { border-color: var(--brand); background: var(--brand-a12); }
.occ-btn.primary { background: var(--brand); color: var(--n-100); border-color: var(--brand); }
.occ-btn.primary:hover { background: var(--ph); }
/* v2 bugfix P0-C: .occ-btn.warn 白底 → 玻璃 */
.occ-btn.warn { background: var(--glass-bg-card); color: var(--c-error-deep); border-color: var(--c-error-deep); }
.occ-btn.warn:hover { background: var(--c-error-bg); }
.apply-pos {
  margin-top: var(--space-2);
  padding: 10px var(--space-3);
  background: var(--c-info-soft);
  border: 1px solid var(--c-info-bg);
  border-radius: 8px;
}
.apply-pos-title { font-size: 11px; font-weight: 600; color: var(--c-info-deep); margin-bottom: 6px; }
.apply-pos-list { display: flex; flex-wrap: wrap; gap: 6px; }
/* v2 bugfix P0-C: 职位 chip 白底 → 玻璃 */
.apply-pos-item {
  padding: var(--space-1) 10px;
  border: 1px solid var(--g3);
  border-radius: 8px;
  cursor: pointer;
  font-size: var(--fs-10);
  background: var(--glass-bg-card);
  transition: 0.15s;
}
.apply-pos-item:hover { border-color: var(--brand); }
.apply-pos-item.sel {
  border-color: var(--brand);
  background: var(--brand-a12);
  color: var(--brand);
  font-weight: 500;
}
.apply-pos-done {
  padding: 6px 10px;
  background: var(--sl);
  border: 1px solid var(--c-success-bg);
  border-radius: 8px;
  font-size: 11px;
  color: var(--c-success-deep);
  margin-top: var(--space-2);
}
.score-panel {
  border: 1px solid var(--g3);
  border-radius: 8px;
  padding: var(--space-3);
  background: var(--g1);
  margin-top: var(--space-2);
}
.score-panel-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--g7);
  margin-bottom: var(--space-2);
  display: flex;
  align-items: center;
  gap: 6px;
}
.score-overall-row { display: flex; align-items: center; gap: var(--space-3); margin-bottom: 10px; }
.score-big { font-size: 28px; font-weight: 700; line-height: 1; }
.score-big.pass { color: var(--c-success); }
.score-big.fail { color: var(--c-error-deep); }
.score-pass-tag {
  padding: 2px var(--space-2);
  border-radius: 20px;
  font-size: var(--fs-10);
  font-weight: 600;
  display: inline-block;
  margin-top: 2px;
}
.score-pass-tag.pass { background: var(--sl); color: var(--c-success-deep); }
.score-pass-tag.fail { background: var(--c-error-bg); color: var(--c-error-deep); }
.sc-dim { display: flex; align-items: center; gap: var(--space-2); margin-top: 6px; font-size: 11px; }
.sc-dim-name { width: 70px; color: var(--g6); flex-shrink: 0; }
.sc-dim-bar {
  flex: 1;
  height: 6px;
  background: var(--g2);
  border-radius: 3px;
  overflow: hidden;
}
.sc-dim-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.sc-dim-score { width: 28px; text-align: right; font-weight: 600; flex-shrink: 0; }
.tag {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 2px 7px;
  border-radius: 20px;
  font-size: var(--fs-10);
  font-weight: 500;
  white-space: nowrap;
}
.td { width: 5px; height: 5px; border-radius: 50%; }
.pbar {
  height: 3px;
  background: var(--g3);
  border-radius: 2px;
  overflow: hidden;
  margin-top: var(--space-1);
}
.pbar .pfill { height: 100%; border-radius: 2px; transition: width 0.3s ease; }
.pfill.bl { background: var(--c-info); }
.pfill.ye { background: var(--c-warning); }
.pfill.pu { background: var(--brand-grad-a); } /* P5 整改：第 3 品牌紫 var(--brand) -> 令牌 */
.pfill.gr { background: var(--c-success); }
/* v2 bugfix P0-C: 业务按钮白底 → 玻璃（同一文件中其他业务卡片一起清理） */
.replace-file-btn {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--g3);
  border-radius: 6px;
  background: var(--glass-bg-card);
  color: var(--g7);
  font-size: 11px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  transition: 0.15s;
}
.replace-file-btn:hover { border-color: var(--brand); color: var(--brand); background: var(--brand-a12); }
.replace-file-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.replace-banner {
  padding: 10px 14px;
  background: linear-gradient(90deg, var(--c-info-bg) 0%, var(--c-info-soft) 100%); /* T5 P2 已落地：info 渐变端点走 §4 语义令牌（--c-info-bg / --c-info-soft），暗色自动跟 §14 覆盖 */
  border: 1px solid var(--c-info-bg);
  border-radius: 8px;
  font-size: var(--fs-12);
  color: var(--c-info-deep);
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: var(--space-2);
}
.replace-banner .rb-icon { font-size: var(--fs-16); flex-shrink: 0; }
.replace-banner .rb-text { flex: 1; }
.replace-banner .rb-text strong { display: block; margin-bottom: 2px; }
.replace-banner .rb-meta { font-size: 11px; color: var(--c-info-deep); opacity: 0.85; }
.nbar {
  padding: var(--space-2) var(--space-3);
  border-radius: 8px;
  font-size: var(--fs-10);
  margin-top: var(--space-2);
}
.nbar.info { background: var(--c-info-soft); border: 1px solid var(--c-info-bg); color: var(--c-info-deep); }
.nbar.warn { background: var(--wl); border: 1px solid var(--c-warning-bg); color: var(--c-warning-deep); }
.nbar.error { background: var(--c-error-bg); border: 1px solid var(--c-error-bg); color: var(--c-error-deep); }
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
.rp-section { margin-bottom: var(--space-1); }
.rp-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--g7);
  margin-bottom: var(--space-2);
  display: flex;
  align-items: center;
  gap: 6px;
}
.rp-title::after { content: ''; flex: 1; height: 1px; background: var(--g3); }

@media (max-width: 768px) {
  .left-panel,
  .right-panel { width: 100%; border-right: none; border-top: 1px solid var(--g3); padding: var(--space-3) 14px; }
  .frow { grid-template-columns: 1fr; }
}
</style>