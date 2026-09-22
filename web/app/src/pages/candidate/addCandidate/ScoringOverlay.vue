<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { CheckmarkCircleOutline as CheckCircle2 } from '@vicons/ionicons5'
import { useAddCandidateStore } from '@/stores/addCandidate'

const store = useAddCandidateStore()
const emit = defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <div class="scoring-overlay">
    <div style="text-align:center;margin-bottom:20px;">
      <div v-if="!store.allScoringDone" class="spin-big"></div>
      <div v-else style="font-size: var(--fs-36);margin-bottom: var(--space-2);color:var(--c-success-deep);"><NIcon :size="36" aria-hidden="true"><CheckCircle2 /></NIcon></div>
      <h3 style="font-size: var(--fs-15);margin-bottom: var(--space-1);">{{ store.allScoringDone ? '处理完成！' : '正在处理...' }}</h3>
      <p style="font-size: var(--fs-12);color:var(--g5);">正在进行数据校验及人岗匹配评分</p>
    </div>

    <div class="sub-progress">
      <div v-for="(item, i) in ['数据完整性校验', '简历信息入库', '人岗匹配评分', '生成应聘记录']" :key="i" class="sub-pi">
        <span :class="['spd', (i < store._overallStep ? 'ok' : (i === store._overallStep ? 'spin' : 'wait'))]"></span>
        <span>{{ item }}</span>
      </div>
    </div>

    <div v-if="store._overallStep >= 2" class="scoring-list">
      <div v-for="r in store.resumes" :key="r.id" class="scoring-card">
        <div class="sc-card-header">
          <div class="sc-avatar">{{ r.parsed?.name?.charAt(0) || r.id.charAt(0) }}</div>
          <div class="sc-info">
            <div class="sc-name">{{ r.parsed?.name || r.file_name }}</div>
            <div class="sc-status">{{ (store.scoringProgress as any)[r.id]?.status === 'done' ? ((store.scoringProgress as any)[r.id]?.result?.passed ? '评分通过' : '评分未通过') : '评分中...' }}</div>
          </div>
          <div v-if="(store.scoringProgress as any)[r.id]?.result" :class="['sc-score', (store.scoringProgress as any)[r.id]?.result?.passed ? 'pass' : 'fail']">
            {{ (store.scoringProgress as any)[r.id]?.result?.score }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="store.allScoringDone" style="text-align:center;margin-top: var(--space-6);">
      <div style="font-size: var(--fs-13);color:var(--g7);margin-bottom: var(--space-3);">
        <span style="color:var(--c-success);font-weight:600;">{{ Object.values(store.scoringProgress).filter((s: any) => s?.result?.passed).length }} 人通过</span> ·
        <span style="color:var(--c-error-deep);font-weight:600;">{{ Object.values(store.scoringProgress).filter((s: any) => s?.result && !s?.result?.passed).length }} 人未通过</span>
      </div>
      <button class="btn bp" data-testid="close-scoring" style="padding:10px 28px;font-size: var(--fs-13);" @click="emit('close')">关闭</button>
    </div>
  </div>
</template>

<style scoped>
.scoring-overlay {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 20px;
}
.sub-overlay { text-align: center; padding: 30px 20px; }
.sub-overlay h3 { font-size: var(--fs-15); margin-bottom: var(--space-1); }
.sub-overlay p { font-size: var(--fs-12); color: var(--g5); }
.spin-big {
  width: 40px;
  height: 40px;
  border: 3px solid var(--g3);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto var(--space-4);
}
.sub-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 400px;
  margin: 20px auto 0;
}
.sub-pi {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: var(--space-2) var(--space-3);
  background: var(--g1);
  border-radius: 8px;
  font-size: 11px;
}
.sub-pi .spd {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.sub-pi .spd.ok { background: var(--c-success); }
.sub-pi .spd.fail { background: var(--c-error-deep); }
.sub-pi .spd.wait { background: var(--g4); }
.sub-pi .spd.spin {
  border: 2px solid var(--g4);
  border-top-color: var(--brand);
  animation: spin 0.8s linear infinite;
  background: transparent;
}
.scoring-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
}
/* v2 bugfix P0-C: 评分卡白底 → 玻璃 */
.scoring-card {
  border: 1px solid var(--g3);
  border-radius: 8px;
  background: var(--glass-bg-card);
  overflow: hidden;
  transition: 0.15s;
}
.scoring-card:hover { border-color: var(--brand); }
.scoring-card.passed { border-left: 3px solid var(--c-success); }
.scoring-card.failed { border-left: 3px solid var(--c-error-deep); }
.scoring-card.scoring { border-left: 3px solid var(--c-info); }
.scoring-card.waiting { border-left: 3px solid var(--g4); }
.sc-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
}
.sc-avatar {
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
.sc-info { flex: 1; min-width: 0; }
.sc-name { font-weight: 600; font-size: var(--fs-13); }
.sc-status { font-size: 11px; color: var(--g5); }
.sc-score { font-size: var(--fs-20); font-weight: 700; flex-shrink: 0; }
.sc-score.pass { color: var(--c-success); }
.sc-score.fail { color: var(--c-error-deep); }
.sc-detail {
  padding: 0 14px var(--space-3);
  border-top: 1px solid var(--g3);
  display: none;
}
.scoring-card.expanded .sc-detail { display: block; }
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
.bp { background: var(--brand); color: #fff; }
.bp:hover { background: var(--ph); }
.bp:disabled { background: var(--g4); cursor: not-allowed; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .scoring-overlay { padding: 14px var(--space-3); }
  .sub-progress { max-width: 100%; }
  .scoring-list { max-width: 100%; }
}
</style>