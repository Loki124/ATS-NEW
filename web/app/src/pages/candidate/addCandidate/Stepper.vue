<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { NIcon } from 'naive-ui'
import { CheckmarkOutline as Check } from '@vicons/ionicons5'
import { useAddCandidateStore } from '@/stores/addCandidate'

const store = useAddCandidateStore()
const { t } = useI18n()

const stepClass = computed(() => (s: 1 | 2) => {
  if (store.step === s) return 'on'
  if (store.step > s) return 'ok'
  return ''
})
</script>

<template>
  <div class="stepper">
    <div class="step-item">
      <div :class="['sdot', stepClass(1)]"><NIcon v-if="store.step > 1" :size="16" aria-hidden="true"><Check /></NIcon><template v-else>1</template></div>
      <span :class="['slabel', stepClass(1) ? stepClass(1) : '']">{{ t('pages.candidate.addCandidate.Stepper.s1') }}</span>
    </div>
    <div :class="['sline', store.step > 1 ? 'ok' : '']"></div>
    <div class="step-item">
      <div :class="['sdot', stepClass(2)]"><NIcon v-if="store.step > 2" :size="16" aria-hidden="true"><Check /></NIcon><template v-else>2</template></div>
      <span class="slabel">{{ t('pages.candidate.addCandidate.Stepper.s2') }}</span>
    </div>
  </div>
</template>

<style scoped>
.stepper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-3) 20px;
  border-bottom: 1px solid var(--g3);
  flex-shrink: 0;
  gap: 0;
}
.step-item { display: flex; align-items: center; gap: 2px; }
.sdot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  transition: 0.2s;
  border: 2px solid var(--g4);
  background: var(--glass-bg-card); /* v2.8 T2.8.1: #fff → var(--glass-bg-card) */
  color: var(--g5);
}
/* 圆点内是 11px 数字 / 16px 对勾图标，压在实底上。
   实底+前景必须成对取令牌，不能随手"品牌色/语义色 + 白字"：
     旧值 --brand 4.47:1 / --c-success 3.30:1 / --c-warning 2.15:1（均不达 4.5:1）。
   现走 --brand-button + --on-brand、--c-*-deep + --on-c-*-deep（两模式各自重排）。 */
.sdot.on { border-color: var(--brand-button); background: var(--brand-button); color: var(--on-brand); }
.sdot.ok { border-color: var(--c-success-deep); background: var(--c-success-deep); color: var(--on-c-success-deep); }
.sdot.warn { border-color: var(--c-warning-deep); background: var(--c-warning-deep); color: var(--on-c-warning-deep); }
.slabel {
  font-size: 11px;
  color: var(--g5);
  font-weight: 500;
  margin-left: 6px;
}
.sdot.on + .slabel { color: var(--brand-fg); }
.sdot.ok + .slabel { color: var(--c-success-deep); }
.sdot.warn + .slabel { color: var(--c-warning-deep); }
.sline {
  width: 56px;
  height: 2px;
  background: var(--g3);
  margin: 0 6px;
  transition: 0.2s;
}
.sline.ok { background: var(--c-success); }
.sline.on { background: linear-gradient(to right, var(--c-success), var(--brand)); }

@media (max-width: 768px) {
  .stepper { padding: 10px var(--space-3); }
  .sline { width: 32px; }
  .slabel { font-size: var(--fs-10); margin-left: var(--space-1); }
}
</style>
