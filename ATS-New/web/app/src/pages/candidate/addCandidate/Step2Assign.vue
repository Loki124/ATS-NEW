<script setup lang="ts">
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

    <div class="nbar info" style="margin-top:8px;">
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
      <DirectionPicker :modelValue="store.dirAll" :hasOccupied="hasOccupied()" @update:modelValue="(v) => store.setDirAll(v)" />
    </div>

    <div v-if="store.applyMode === 'all' && store.dirAll === 'position'" class="rp-section">
      <div class="rp-title">选择目标职位</div>
      <div class="pos-selector"><PositionChips :positions="positions" :modelValue="store.posAll ? [store.posAll] : []" @update:modelValue="(v) => store.setPosAll(v[0] || '')" /></div>
    </div>

    <div v-if="hasOccupied()" class="nbar warn">⚠️ 有 {{ store.resumes.filter(r => r.status === 'occupied').length }} 份简历已被占用，仅可选择"待分配"。</div>

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
.left-panel { flex: 1; overflow-y: auto; padding: 16px 20px; border-right: 1px solid var(--g3); display: flex; flex-direction: column; gap: 12px; }
.right-panel { width: 340px; flex-shrink: 0; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 14px; }
.status-summary { display: flex; gap: 8px; flex-wrap: wrap; }
.st-pill { padding: 4px 10px; border-radius: 20px; font-size: 11px; display: flex; align-items: center; gap: 5px; }
.st-pill .st-dot { width: 6px; height: 6px; border-radius: 50%; }
.st-pill.clean { background: var(--sl); color: #065F46; }
.st-pill.unocc { background: var(--wl); color: #92400E; }
.st-pill.occupied { background: var(--dl); color: #991B1B; }
.apply-mode { display: flex; gap: 4px; }
.apply-mode span { padding: 4px 10px; border: 1px solid var(--g3); border-radius: 20px; font-size: 10px; cursor: pointer; }
.apply-mode span.active { background: var(--p); color: #fff; border-color: var(--p); }
.rp-section { margin-bottom: 4px; }
.rp-title { font-size: 11px; font-weight: 600; color: var(--g7); margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
.rp-title::after { content: ''; flex: 1; height: 1px; background: var(--g3); }
.nbar { padding: 8px 12px; border-radius: 8px; font-size: 10px; margin-top: 8px; }
.nbar.info { background: var(--bl); border: 1px solid #BFDBFE; color: #1E40AF; }
.nbar.warn { background: var(--wl); border: 1px solid #FDE68A; color: #92400E; }
.frow3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
.fg { display: flex; flex-direction: column; gap: 3px; }
.fg label { font-size: 10px; font-weight: 500; color: var(--g6); }
.fg input, .fg select { padding: 6px 8px; border: 1px solid var(--g4); border-radius: 5px; font-size: 11px; }
.submit-choices { margin-top: 4px; padding: 12px 14px; background: var(--g1); border-radius: 12px; border: 1px solid var(--g3); }
.sc-title { font-weight: 600; font-size: 11px; margin-bottom: 6px; color: var(--g7); }
.sc-opts { display: flex; flex-direction: column; gap: 6px; }
.sc-opt { padding: 8px 12px; border: 1px solid var(--g3); border-radius: 8px; cursor: pointer; background: #fff; font-size: 11px; }
.sc-opt.sel { border-color: var(--p); background: var(--pl); }
.sclabel { font-weight: 600; font-size: 11px; }
.schint { font-size: 9px; color: var(--g5); margin-top: 1px; }
.mf { padding: 14px 20px; border-top: 1px solid var(--g3); display: flex; align-items: center; justify-content: space-between; background: #fff; }
.btn { padding: 7px 14px; border-radius: 8px; font-size: 11px; font-weight: 500; cursor: pointer; border: none; }
.bp { background: var(--p); color: #fff; }
.bp:disabled { background: var(--g4); cursor: not-allowed; }
.bs { background: #fff; color: var(--g7); border: 1px solid var(--g4); }
.btng { display: flex; gap: 6px; }
</style>