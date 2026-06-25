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

      <div v-if="isAllDone()" @click="emit('upload', [])" class="upload-zone" style="padding:10px 14px;border-style:dashed;margin-bottom:10px;cursor:pointer;display:flex;align-items:center;gap:8px;font-size:11px;text-align:left;">
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
.left-panel { flex: 1; overflow-y: auto; padding: 16px 20px; border-right: 1px solid var(--g3); display: flex; flex-direction: column; gap: 12px; }
.right-panel { width: 340px; flex-shrink: 0; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 14px; }
.status-summary { display: flex; gap: 8px; flex-wrap: wrap; }
.st-pill { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 500; display: flex; align-items: center; gap: 5px; }
.st-pill .st-dot { width: 6px; height: 6px; border-radius: 50%; }
.st-pill.processing { background: var(--bl); color: #1E40AF; }
.st-pill.processing .st-dot { background: var(--b); animation: pulse2 1s infinite; }
.st-pill.clean { background: var(--sl); color: #065F46; }
.st-pill.clean .st-dot { background: var(--s); }
.st-pill.unocc { background: var(--wl); color: #92400E; }
.st-pill.unocc .st-dot { background: var(--w); }
.st-pill.occupied { background: var(--dl); color: #991B1B; }
.st-pill.occupied .st-dot { background: var(--d); }
.bulk-bar { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: var(--pl); border-radius: 8px; font-size: 11px; color: #3730A3; }
.bulk-count { font-weight: 600; }
.card-list { display: flex; flex-direction: column; gap: 8px; }
.nbar { padding: 8px 12px; border-radius: 8px; font-size: 10px; margin-top: 8px; }
.nbar.info { background: var(--bl); border: 1px solid #BFDBFE; color: #1E40AF; }
.nbar.error { background: var(--dl); border: 1px solid #FECACA; color: #991B1B; }
.btn { padding: 7px 14px; border-radius: 8px; font-size: 11px; font-weight: 500; cursor: pointer; border: none; }
.bs { background: #fff; color: var(--g7); border: 1px solid var(--g4); }
.rp-section { margin-bottom: 4px; }
.rp-title { font-size: 11px; font-weight: 600; color: var(--g7); margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
.rp-title::after { content: ''; flex: 1; height: 1px; background: var(--g3); }
@keyframes pulse2 { 0%,100% { opacity: 1 } 50% { opacity: 0.3 } }
</style>