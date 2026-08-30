<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { AlertTriangle } from 'lucide-vue-next'
import { useAddCandidateStore } from '@/stores/addCandidate'
import DirectionPicker from '@/components/common/DirectionPicker.vue'
import PositionChips from '@/components/common/PositionChips.vue'

const store = useAddCandidateStore()
const emit = defineEmits<{ (e: 'back'): void; (e: 'submit'): void }>()

const positions = ['高级前端工程师', '资深前端工程师', '前端架构师', 'Web前端Leader', '全栈工程师', '高级后端工程师', '产品经理', 'UI设计师']
const hasOccupied = () => store.resumes.some((r) => r.status === 'occupied')
const isMulti = () => store.resumes.length > 1
</script>

<template>
  <div class="left-panel">
    <div class="status-summary" style="margin-bottom:10px;">
      <span v-for="r in store.resumes" :key="r.id" :class="['st-pill', r.status]"><span class="st-dot"></span>{{ r.parsed?.name || r.file_name }}</span>
    </div>

    <div class="nbar info" style="margin-top: var(--space-2);">
      {{ store.applyMode === 'per' ? '逐条设置模式：为每份简历单独选择去向。' : '统一设置模式：右侧面板设置的去向将应用到所有简历。' }}
    </div>
  </div>

  <div class="right-panel">
    <div v-if="isMulti()" class="rp-section">
      <div class="rp-title">设置模式</div>
      <div class="apply-mode">
        <span :class="[store.applyMode === 'all' ? 'active' : '']" @click="store.applyMode = 'all'">统一设置</span>
        <span :class="[store.applyMode === 'per' ? 'active' : '']" @click="store.applyMode = 'per'">逐条设置</span>
      </div>
    </div>

    <div v-if="store.applyMode === 'all'" class="rp-section">
      <div class="rp-title">选择入库方向</div>
      <DirectionPicker :model-value="store.dirAll" :has-occupied="hasOccupied()" @update:model-value="(v) => store.setDirAll(v)" />
    </div>

    <div v-if="store.applyMode === 'all' && store.dirAll === 'position'" class="rp-section">
      <div class="rp-title">选择目标职位</div>
      <div class="pos-selector"><PositionChips :positions="positions" :model-value="store.posAll ? [store.posAll] : []" @update:model-value="(v) => store.setPosAll(v[0] || '')" /></div>
    </div>

    <div v-if="hasOccupied()" class="nbar warn"><NIcon :size="15" style="vertical-align:-2px;margin-right:4px" aria-hidden="true"><AlertTriangle /></NIcon>有 {{ store.resumes.filter(r => r.status === 'occupied').length }} 份简历已被占用，仅可选择"待分配"。</div>

    <div class="rp-section">
      <div class="rp-title">应聘信息</div>
      <div class="frow3">
        <div class="fg"><label>渠道</label><select v-model="store.appInfo.channel"><option>招聘网站</option><option>内推</option><option>猎头</option></select></div>
        <div class="fg"><label>来源</label><input v-model="store.appInfo.source" /></div>
        <div class="fg"><label>提供人</label><input v-model="store.appInfo.provider" placeholder="如：张三" /></div>
      </div>
    </div>

    <div class="submit-choices">
      <div class="sc-title">提交方式</div>
      <div class="sc-opts">
        <div :class="['sc-opt', { sel: store.submitMode === 'wait' }]" @click="store.submitMode = 'wait'">
          <div class="sclabel">提交并等待结果</div>
          <div class="schint">在当前页面查看每份简历评分进度及结果</div>
        </div>
        <div :class="['sc-opt', { sel: store.submitMode === 'async' }]" @click="store.submitMode = 'async'">
          <div class="sclabel">提交后通知我</div>
          <div class="schint">提交后关闭，后台评分完成后通知</div>
        </div>
      </div>
    </div>
  </div>

  <div class="mf" style="position:absolute;bottom:0;left:0;right:0;">
    <div><button class="btn bs" @click="emit('back')">← 上一步</button></div>
    <div class="btng">
      <button :disabled="!store.canSubmit" class="btn bp" data-testid="submit-btn" @click="emit('submit')">提交</button>
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
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}
.st-pill .st-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.st-pill.clean { background: var(--sl); color: var(--c-success-deep); }
.st-pill.clean .st-dot { background: var(--s); }
.st-pill.unocc { background: var(--wl); color: var(--c-warning-deep); }
.st-pill.unocc .st-dot { background: var(--w); }
.st-pill.occupied { background: var(--dl); color: var(--c-error-deep); }
.st-pill.occupied .st-dot { background: var(--d); }
.card-list { display: flex; flex-direction: column; gap: var(--space-2); }
.step2-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: 1px solid var(--g3);
  border-radius: 8px;
  background: var(--glass-bg-card); /* v2.8 T2.8.1: var(--g1) → var(--glass-bg-card) */
}
.step2-card .s2-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--g2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-13);
  color: var(--g5);
  font-weight: 600;
  flex-shrink: 0;
}
.step2-card .s2-info { flex: 1; min-width: 0; }
.step2-card .s2-name {
  font-weight: 600;
  font-size: var(--fs-13);
  display: flex;
  align-items: center;
  gap: 6px;
}
.step2-card .s2-meta {
  font-size: 11px;
  color: var(--g6);
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-top: 2px;
}
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
.apply-mode { display: flex; gap: var(--space-1); margin-bottom: var(--space-2); }
.apply-mode span {
  padding: var(--space-1) 10px;
  border: 1px solid var(--g3);
  border-radius: 20px;
  font-size: var(--fs-10);
  cursor: pointer;
  transition: 0.15s;
}
.apply-mode span:hover { border-color: var(--p); }
.apply-mode span.active { background: var(--p); color: var(--n-100); border-color: var(--p); }
.dir-opts { display: flex; flex-direction: column; gap: 6px; }
.dopt {
  padding: 10px 14px;
  border: 2px solid var(--g3);
  border-radius: 12px;
  cursor: pointer;
  transition: 0.15s;
  background: var(--glass-bg-card); /* v2.8 T2.8.1: var(--g1) → var(--glass-bg-card) */
  display: flex;
  align-items: center;
  gap: 10px;
}
.dopt:hover:not(.off) { border-color: var(--p); }
.dopt.sel { border-color: var(--p); background: var(--pl); }
.dopt.off { opacity: 0.4; cursor: not-allowed; background: var(--g1); }
.dopt .dicon { font-size: var(--fs-20); flex-shrink: 0; }
.dopt .dinfo { flex: 1; }
.dopt .dlabel { font-weight: 600; font-size: var(--fs-12); }
.dopt .dhint { font-size: var(--fs-10); color: var(--g5); }
.pos-selector {
  margin-top: var(--space-2);
  padding: 10px var(--space-3);
  background: var(--glass-bg-card); /* v2.8 T2.8.1: var(--g1) → var(--glass-bg-card) */
  border: 1px solid var(--g3);
  border-radius: 12px;
}
.pos-selector .ps-title { font-size: 11px; font-weight: 600; color: var(--g7); margin-bottom: 6px; }
.pos-list { display: flex; flex-wrap: wrap; gap: 6px; }
.pos-item {
  padding: 6px var(--space-3);
  border: 1px solid var(--g3);
  border-radius: 8px;
  cursor: pointer;
  font-size: 11px;
  transition: 0.15s;
  background: var(--glass-bg-card); /* v2.8 T2.8.1: var(--g1) → var(--glass-bg-card) */
}
.pos-item:hover { border-color: var(--p); }
.pos-item.sel {
  border-color: var(--p);
  background: var(--pl);
  color: var(--p);
  font-weight: 500;
}
.per-dir-list { display: flex; flex-direction: column; gap: 5px; max-height: 200px; overflow-y: auto; }
.per-dir-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) 10px;
  border: 1px solid var(--g3);
  border-radius: 8px;
  background: var(--glass-bg-card); /* v2.8 T2.8.1: var(--g1) → var(--glass-bg-card) */
  font-size: 11px;
}
.per-dir-item .pdi-name { font-weight: 500; min-width: 50px; font-size: 11px; }
.per-dir-item .pdi-status { flex: 1; display: flex; align-items: center; gap: var(--space-1); font-size: var(--fs-10); }
.per-dir-item select {
  padding: var(--space-1) 6px;
  border: 1px solid var(--g3);
  border-radius: 4px;
  font-size: var(--fs-10);
  max-width: 80px;
}
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
.nbar {
  padding: var(--space-2) var(--space-3);
  border-radius: 8px;
  font-size: var(--fs-10);
  margin-top: var(--space-2);
}
.nbar.info { background: var(--bl); border: 1px solid var(--c-info-bg); color: var(--c-info-deep); }
.nbar.warn { background: var(--wl); border: 1px solid var(--c-warning-bg); color: var(--c-warning-deep); }
.nbar.error { background: var(--dl); border: 1px solid var(--c-error-bg); color: var(--c-error-deep); }
.frow3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
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
.fg textarea:focus { border-color: var(--p); box-shadow: 0 0 0 2px var(--overlay-scrim-mid); }
.submit-choices {
  margin-top: var(--space-1);
  padding: var(--space-3) 14px;
  background: var(--g1);
  border-radius: 12px;
  border: 1px solid var(--g3);
}
.sc-title { font-weight: 600; font-size: 11px; margin-bottom: 6px; color: var(--g7); }
.sc-opts { display: flex; flex-direction: column; gap: 6px; }
.sc-opt {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--g3);
  border-radius: 8px;
  cursor: pointer;
  transition: 0.15s;
  background: var(--glass-bg-card); /* v2.8 T2.8.1: var(--g1) → var(--glass-bg-card) */
  font-size: 11px;
}
.sc-opt:hover { border-color: var(--p); }
.sc-opt.sel { border-color: var(--p); background: var(--pl); }
.sclabel { font-weight: 600; font-size: 11px; }
.schint { font-size: 9px; color: var(--g5); margin-top: 1px; }
.mf {
  padding: 14px 20px;
  border-top: 1px solid var(--g3);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--glass-bg-card); /* v2.8 T2.8.1: var(--g1) → var(--glass-bg-card) */
  flex-shrink: 0;
}
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
.bp { background: var(--p); color: var(--n-100); }
.bp:hover { background: var(--ph); }
.bp:disabled { background: var(--g4); cursor: not-allowed; }
.bs { background: var(--surface); color: var(--g7); border: 1px solid var(--g4); } /* v2.8 T2.8.1: var(--n-100) → var(--surface) */
.bs:hover { background: var(--g2); }
.bg { background: transparent; color: var(--g6); }
.bg:hover { background: var(--g2); }
.btng { display: flex; gap: 6px; align-items: center; }

@media (max-width: 768px) {
  .left-panel,
  .right-panel { width: 100%; border-right: none; border-top: 1px solid var(--g3); padding: var(--space-3) 14px; }
  .frow3 { grid-template-columns: 1fr; }
  .mf { padding: var(--space-3) 14px; }
}
</style>