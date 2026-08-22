<script setup lang="ts">
import { useAddCandidateStore } from '@/stores/addCandidate'
import ResumeCard from '@/components/common/ResumeCard.vue'
import UploadZone from '@/components/common/UploadZone.vue'

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
        <button class="btn bs" style="font-size:10px;padding:3px 8px;">批量设为待分配</button>
        <button class="btn bs" style="font-size:10px;padding:3px 8px;" @click="store.selectedIds = []">取消选择</button>
      </div>

      <div v-if="isAllDone()" class="upload-zone" style="padding:10px 14px;border-style:dashed;margin-bottom:10px;cursor:pointer;display:flex;align-items:center;gap:8px;font-size:11px;text-align:left;" @click="emit('upload', [])">
        <span style="font-size:18px;">📎</span>
        <span style="flex:1;color:var(--g6);">拖拽或<span style="color:var(--p);font-weight:500;">点击</span>追加更多简历</span>
        <span style="font-size:10px;color:var(--g5);">PDF / Word / TXT</span>
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
      <div class="rp-title">⚠️ 需处理项</div>
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
  padding: 16px 20px;
  border-right: 1px solid var(--g3);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.right-panel {
  width: 340px;
  flex-shrink: 0;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.status-summary { display: flex; gap: 8px; flex-wrap: wrap; }
.st-pill {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}
.st-pill .st-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.st-pill.processing { background: var(--bl); color: #1E40AF; }
.st-pill.processing .st-dot { background: var(--b); animation: pulse2 1s infinite; }
.st-pill.clean { background: var(--sl); color: #065F46; }
.st-pill.clean .st-dot { background: var(--s); }
.st-pill.unocc { background: var(--wl); color: #92400E; }
.st-pill.unocc .st-dot { background: var(--w); }
.st-pill.occupied { background: var(--dl); color: #991B1B; }
.st-pill.occupied .st-dot { background: var(--d); }
@keyframes pulse2 { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
.legend { display: flex; gap: 12px; font-size: 10px; color: var(--g5); flex-wrap: wrap; }
.legend span { display: flex; align-items: center; gap: 4px; }
.legend .ld { width: 6px; height: 6px; border-radius: 50%; }
.legend .ld.lg { background: var(--s); }
.legend .ld.ly { background: var(--w); }
.legend .ld.lr { background: var(--d); }
.legend .ld.lb { background: var(--b); }
.bulk-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--pl);
  border-radius: 8px;
  font-size: 11px;
  color: #3730A3;
}
.bulk-count { font-weight: 600; }
.upload-zone {
  border: 2px dashed var(--g4);
  border-radius: 12px;
  padding: 32px 20px;
  text-align: center;
  cursor: pointer;
  transition: 0.15s;
  background: var(--g1);
}
.upload-zone:hover { border-color: var(--p); background: var(--pl); }
.upload-zone.dragover {
  border-color: var(--p);
  background: var(--pl);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
}
.upload-zone .up-icon { font-size: 36px; margin-bottom: 8px; transition: 0.2s; }
.upload-zone.dragover .up-icon { transform: scale(1.1); }
.upload-zone .up-text { font-size: 13px; font-weight: 500; color: var(--g7); }
.upload-zone .up-hint { font-size: 11px; color: var(--g5); margin-top: 4px; }
.upload-zone .up-quick { display: flex; gap: 8px; justify-content: center; margin-top: 12px; }
/* v2 bugfix P0-C: 业务页白底透出极光 */
.upload-zone .up-quick span {
  font-size: 11px;
  padding: 4px 10px;
  background: var(--glass-bg-card);
  border: 1px solid var(--g3);
  border-radius: 20px;
  color: var(--g6);
  cursor: pointer;
}
.upload-zone .up-quick span:hover { border-color: var(--p); color: var(--p); }
.card-list { display: flex; flex-direction: column; gap: 8px; }
/* v2 bugfix P0-C: 业务卡片白底 → 玻璃 */
.card-item {
  border: 1px solid var(--g3);
  border-radius: 8px;
  background: var(--glass-bg-card);
  overflow: hidden;
  transition: 0.15s;
}
.card-item:hover { border-color: var(--p); }
.card-item.selected { border-color: var(--p); box-shadow: 0 0 0 1px rgba(79, 70, 229, 0.15); }
.card-item.occ { border-left: 3px solid var(--d); }
.card-item.dir-set { border-left: 3px solid var(--s); }
.card-item.unocc { border-left: 3px solid var(--w); }
.card-item.clean { border-left: 3px solid var(--s); }
.card-item .c-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
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
.card-item .c-header .c-chk.checked { background: var(--p); border-color: var(--p); }
.card-item .c-header .c-chk.checked::after { content: '✓'; color: #fff; font-size: 10px; }
.card-item .c-header .c-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--g2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: var(--g5);
  flex-shrink: 0;
  font-weight: 600;
}
.card-item .c-header .c-info { flex: 1; min-width: 0; }
.card-item .c-header .c-name {
  font-weight: 600;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.card-item .c-header .c-file { font-size: 10px; color: var(--g5); font-weight: 400; }
.card-item .c-header .c-basic {
  font-size: 11px;
  color: var(--g6);
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 2px;
}
.card-item .c-header .c-expand {
  font-size: 16px;
  color: var(--g5);
  transition: 0.2s;
  flex-shrink: 0;
}
.card-item.expanded .c-header .c-expand { transform: rotate(180deg); }
.card-item .c-body { display: none; padding: 0 14px 14px; border-top: 1px solid var(--g3); }
.card-item.expanded .c-body { display: block; }
.cb {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 11px;
  margin: 8px 0;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  line-height: 1.5;
}
.cb .cb-icon { font-size: 16px; flex-shrink: 0; margin-top: 1px; }
.cb.clean { background: var(--sl); color: #065F46; border: 1px solid #A7F3D0; }
.cb.unocc { background: var(--wl); color: #92400E; border: 1px solid #FDE68A; }
.cb.occupied { background: var(--dl); color: #991B1B; border: 1px solid #FECACA; }
.cb.processing { background: var(--bl); color: #1E40AF; border: 1px solid #BFDBFE; }
.dup-card {
  border: 1px solid #FDE68A;
  border-radius: 8px;
  padding: 10px 14px;
  background: #FFFDF5;
  margin: 8px 0;
  font-size: 11px;
}
.dup-card .dup-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
.dup-card .dup-label { color: var(--g5); }
.dup-card .dup-value { font-weight: 500; }
.dup-card .dup-note {
  font-size: 10px;
  color: #92400E;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed #FDE68A;
}
.fst {
  font-size: 10px;
  font-weight: 600;
  color: var(--g6);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 10px;
  margin-bottom: 6px;
}
.frow { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; }
.fg { display: flex; flex-direction: column; gap: 3px; }
.fg label { font-size: 10px; font-weight: 500; color: var(--g6); }
.fg input,
.fg select,
.fg textarea {
  padding: 6px 8px;
  border: 1px solid var(--g4);
  border-radius: 5px;
  font-size: 11px;
  outline: none;
  font-family: inherit;
}
.fg input:focus,
.fg select:focus,
.fg textarea:focus { border-color: var(--p); box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.08); }
.fg textarea { resize: vertical; min-height: 50px; }
.seg-item {
  border: 1px solid var(--g3);
  border-radius: 8px;
  padding: 10px 12px;
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
  background: var(--pl);
  color: var(--p);
  font-size: 10px;
  font-weight: 700;
}
.seg-readonly { font-size: 11px; color: var(--g7); line-height: 1.6; }
.seg-line { display: flex; gap: 8px; flex-wrap: wrap; }
.seg-readonly .seg-line span { color: var(--g6); }
.recheck-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: 8px;
  font-size: 10px;
  color: #1E40AF;
  margin: 8px 0;
}
.recheck-bar .spin2 {
  width: 12px;
  height: 12px;
  border: 2px solid #BFDBFE;
  border-top-color: var(--p);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }
.occ-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
/* v2 bugfix P0-C: 业务按钮白底 → 玻璃 */
.occ-btn {
  padding: 5px 12px;
  border: 1px solid var(--g3);
  border-radius: 8px;
  font-size: 10px;
  cursor: pointer;
  transition: 0.15s;
  background: var(--glass-bg-card);
  color: var(--g7);
}
.occ-btn:hover { border-color: var(--p); background: var(--pl); }
.occ-btn.primary { background: var(--p); color: #fff; border-color: var(--p); }
.occ-btn.primary:hover { background: var(--ph); }
/* v2 bugfix P0-C: .occ-btn.warn 白底 → 玻璃 */
.occ-btn.warn { background: var(--glass-bg-card); color: #991B1B; border-color: var(--d); }
.occ-btn.warn:hover { background: var(--dl); }
.apply-pos {
  margin-top: 8px;
  padding: 10px 12px;
  background: var(--bl);
  border: 1px solid #BFDBFE;
  border-radius: 8px;
}
.apply-pos-title { font-size: 11px; font-weight: 600; color: #1E40AF; margin-bottom: 6px; }
.apply-pos-list { display: flex; flex-wrap: wrap; gap: 6px; }
/* v2 bugfix P0-C: 职位 chip 白底 → 玻璃 */
.apply-pos-item {
  padding: 4px 10px;
  border: 1px solid var(--g3);
  border-radius: 8px;
  cursor: pointer;
  font-size: 10px;
  background: var(--glass-bg-card);
  transition: 0.15s;
}
.apply-pos-item:hover { border-color: var(--p); }
.apply-pos-item.sel {
  border-color: var(--p);
  background: var(--pl);
  color: var(--p);
  font-weight: 500;
}
.apply-pos-done {
  padding: 6px 10px;
  background: var(--sl);
  border: 1px solid #A7F3D0;
  border-radius: 8px;
  font-size: 11px;
  color: #065F46;
  margin-top: 8px;
}
.score-panel {
  border: 1px solid var(--g3);
  border-radius: 8px;
  padding: 12px;
  background: var(--g1);
  margin-top: 8px;
}
.score-panel-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--g7);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.score-overall-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.score-big { font-size: 28px; font-weight: 700; line-height: 1; }
.score-big.pass { color: var(--s); }
.score-big.fail { color: var(--d); }
.score-pass-tag {
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 600;
  display: inline-block;
  margin-top: 2px;
}
.score-pass-tag.pass { background: var(--sl); color: #065F46; }
.score-pass-tag.fail { background: var(--dl); color: #991B1B; }
.sc-dim { display: flex; align-items: center; gap: 8px; margin-top: 6px; font-size: 11px; }
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
  gap: 4px;
  padding: 2px 7px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}
.td { width: 5px; height: 5px; border-radius: 50%; }
.pbar {
  height: 3px;
  background: var(--g3);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 4px;
}
.pbar .pfill { height: 100%; border-radius: 2px; transition: width 0.3s ease; }
.pfill.bl { background: var(--b); }
.pfill.ye { background: #F59E0B; }
.pfill.pu { background: #8B5CF6; }
.pfill.gr { background: var(--s); }
/* v2 bugfix P0-C: 业务按钮白底 → 玻璃（同一文件中其他业务卡片一起清理） */
.replace-file-btn {
  padding: 4px 8px;
  border: 1px solid var(--g3);
  border-radius: 6px;
  background: var(--glass-bg-card);
  color: var(--g7);
  font-size: 11px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: 0.15s;
}
.replace-file-btn:hover { border-color: var(--p); color: var(--p); background: var(--pl); }
.replace-file-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.replace-banner {
  padding: 10px 14px;
  background: linear-gradient(90deg, var(--bl) 0%, #DBEAFE 100%);
  border: 1px solid #BFDBFE;
  border-radius: 8px;
  font-size: 12px;
  color: #1E40AF;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.replace-banner .rb-icon { font-size: 16px; flex-shrink: 0; }
.replace-banner .rb-text { flex: 1; }
.replace-banner .rb-text strong { display: block; margin-bottom: 2px; }
.replace-banner .rb-meta { font-size: 11px; color: #1E40AF; opacity: 0.85; }
.nbar {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 10px;
  margin-top: 8px;
}
.nbar.info { background: var(--bl); border: 1px solid #BFDBFE; color: #1E40AF; }
.nbar.warn { background: var(--wl); border: 1px solid #FDE68A; color: #92400E; }
.nbar.error { background: var(--dl); border: 1px solid #FECACA; color: #991B1B; }
.btn {
  padding: 7px 14px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: 0.15s;
}
/* v2 bugfix P0-C: .bs 业务按钮白底 → 玻璃 */
.bs { background: var(--glass-bg-card); color: var(--g7); border: 1px solid var(--g4); }
.bs:hover { background: var(--g2); }
.rp-section { margin-bottom: 4px; }
.rp-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--g7);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.rp-title::after { content: ''; flex: 1; height: 1px; background: var(--g3); }

@media (max-width: 768px) {
  .left-panel,
  .right-panel { width: 100%; border-right: none; border-top: 1px solid var(--g3); padding: 12px 14px; }
  .frow { grid-template-columns: 1fr; }
}
</style>