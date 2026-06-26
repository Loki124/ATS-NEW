<script setup lang="ts">
import { useAddCandidateStore } from '@/stores/addCandidate'

const store = useAddCandidateStore()
const emit = defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <div class="async-result">
    <div class="ar-icon">✅</div>
    <h3>提交成功</h3>
    <p class="ar-sub">{{ store.resumes.length }} 份简历已提交后台处理</p>
    <div class="ar-routes">
      <div class="ar-route pass">
        <span class="ar-route-icon">✅</span>
        <div><strong>评分通过的候选人</strong><br>将直接进入目标职位，您将在职位详情中看到候选人信息。</div>
      </div>
      <div class="ar-route fail">
        <span class="ar-route-icon">📥</span>
        <div><strong>评分未通过的候选人</strong><br>将在"待分配"中展示，您可以手动处理或重新分配。</div>
      </div>
    </div>
    <div class="nbar info" style="width:100%;text-align:center;">⏰ 评分完成后将通过消息通知您，请留意系统消息。</div>
    <button class="btn bp" data-testid="close-async" style="margin-top:24px;padding:10px 28px;font-size:13px;" @click="emit('close')">关闭</button>
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
.ar-icon { font-size: 48px; margin-bottom: 16px; }
.async-result h3 { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
.ar-sub { font-size: 13px; color: var(--g6); margin-bottom: 24px; }
.ar-routes {
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
  margin-bottom: 24px;
  width: 100%;
}
.ar-route {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 12px;
}
.ar-route.pass { background: var(--sl); border: 1px solid #A7F3D0; }
.ar-route.fail { background: var(--wl); border: 1px solid #FDE68A; }
.ar-route-icon { font-size: 18px; flex-shrink: 0; }
.nbar {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 10px;
  margin-top: 8px;
}
.nbar.info { background: var(--bl); border: 1px solid #BFDBFE; color: #1E40AF; }
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
.bp { background: var(--p); color: #fff; }
.bp:hover { background: var(--ph); }
.bp:disabled { background: var(--g4); cursor: not-allowed; }

@media (max-width: 768px) {
  .async-result { padding: 24px 16px; }
  .ar-route { font-size: 11px; padding: 10px 12px; }
}
</style>
