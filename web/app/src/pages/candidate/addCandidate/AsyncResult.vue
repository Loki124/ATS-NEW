<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { CheckCircle2, Inbox, Clock } from 'lucide-vue-next'
import { useAddCandidateStore } from '@/stores/addCandidate'

const store = useAddCandidateStore()
const emit = defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <div class="async-result">
    <div class="ar-icon"><NIcon :size="40" aria-hidden="true"><CheckCircle2 /></NIcon></div>
    <h3>提交成功</h3>
    <p class="ar-sub">{{ store.resumes.length }} 份简历已提交后台处理</p>
    <div class="ar-routes">
      <div class="ar-route pass">
        <span class="ar-route-icon"><NIcon :size="18" aria-hidden="true"><CheckCircle2 /></NIcon></span>
        <div><strong>评分通过的候选人</strong><br>将直接进入目标职位，您将在职位详情中看到候选人信息。</div>
      </div>
      <div class="ar-route fail">
        <span class="ar-route-icon"><NIcon :size="18" aria-hidden="true"><Inbox /></NIcon></span>
        <div><strong>评分未通过的候选人</strong><br>将在"待分配"中展示，您可以手动处理或重新分配。</div>
      </div>
    </div>
    <div class="nbar info" style="width:100%;text-align:center;"><NIcon :size="14" style="vertical-align:-2px" aria-hidden="true"><Clock /></NIcon> 评分完成后将通过消息通知您，请留意系统消息。</div>
    <button class="btn bp" data-testid="close-async" style="margin-top: var(--space-6);padding:10px 28px;font-size: var(--fs-13);" @click="emit('close')">关闭</button>
  </div>
</template>

<style scoped>
.async-result {
  text-align: center;
  padding: 40px 30px;
  max-width: 500px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
}
.ar-icon { font-size: 48px; margin-bottom: var(--space-4); }
.async-result h3 { font-size: var(--fs-18); font-weight: 700; margin-bottom: var(--space-2); }
.ar-sub { font-size: var(--fs-13); color: var(--g6); margin-bottom: var(--space-6); }
.ar-routes {
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
  margin-bottom: var(--space-6);
  width: 100%;
}
.ar-route {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: var(--space-3) var(--space-4);
  border-radius: 8px;
  font-size: var(--fs-12);
}
.ar-route.pass { background: var(--sl); border: 1px solid var(--c-success-bg); }
.ar-route.fail { background: var(--wl); border: 1px solid var(--c-warning-bg); }
.ar-route-icon { font-size: var(--fs-18); flex-shrink: 0; }
.nbar {
  padding: var(--space-2) var(--space-3);
  border-radius: 8px;
  font-size: var(--fs-10);
  margin-top: var(--space-2);
}
.nbar.info { background: var(--c-info-soft); border: 1px solid var(--c-info-bg); color: var(--c-info-deep); }
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
.bp { background: var(--brand); color: var(--n-100); }
.bp:hover { background: var(--ph); }
.bp:disabled { background: var(--g4); cursor: not-allowed; }

@media (max-width: 768px) {
  .async-result { padding: var(--space-6) var(--space-4); }
  .ar-route { font-size: 11px; padding: 10px var(--space-3); }
}
</style>
