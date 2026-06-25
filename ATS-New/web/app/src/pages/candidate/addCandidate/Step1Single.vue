<script setup lang="ts">
import { computed } from 'vue'
import { useAddCandidateStore } from '@/stores/addCandidate'
import StatusTag from '@/components/common/StatusTag.vue'
import CheckBanner from '@/components/common/CheckBanner.vue'
import DuplicateInfoCard from '@/components/common/DuplicateInfoCard.vue'
import OccupiedActions from '@/components/common/OccupiedActions.vue'
import ApplyPositionSelector from '@/components/common/ApplyPositionSelector.vue'
import ScorePanel from '@/components/common/ScorePanel.vue'

const store = useAddCandidateStore()
const emit = defineEmits<{ (e: 'replace', draftId: string): void }>()
const resume = computed(() => store.resumes[0])
const isOccupied = computed(() => resume.value?.status === 'occupied')
const isUnocc = computed(() => resume.value?.status === 'unocc')
const positions = ['高级前端工程师', '资深前端工程师', '前端架构师', 'Web前端Leader', '全栈工程师']

function onField(field: string, e: Event) {
  if (!resume.value) return
  const v = (e.target as HTMLInputElement).value
  store.updateField(resume.value.id, field as any, v)
  store.triggerRecheck(resume.value.id)
}

function onAction(_draftId: string, action: any) {
  if (!resume.value) return
  if (action === 'apply') {
    store.setOccupyAction(resume.value.id, 'apply')
  } else {
    store.setOccupyAction(resume.value.id, action)
  }
}

function onSelectPos(pos: string) {
  if (!resume.value) return
  store.selectApplyPos(resume.value.id, pos)
}
</script>

<template>
  <div class="left-panel" v-if="resume">
    <div class="detail-header">
      <div class="detail-avatar">{{ resume.parsed?.name?.charAt(0) || resume.file_name.charAt(0) }}</div>
      <div style="flex:1;min-width:0">
        <div class="detail-name">
          {{ resume.parsed?.name || resume.file_name }}
          <StatusTag :status="resume.status" />
        </div>
        <div class="detail-file">{{ resume.file_name }}</div>
      </div>
      <div class="detail-header-actions">
        <button class="replace-file-btn" data-testid="replace-file" @click="emit('replace', resume.id)">更换简历</button>
      </div>
    </div>

    <!-- Basic info section -->
    <div class="detail-section">
      <div class="detail-section-title">基本信息</div>
      <div class="frow">
        <div class="fg"><label>姓名 *</label>
          <input :value="resume.parsed?.name || ''" @change="onField('name', $event)" data-testid="field-name" />
        </div>
        <div class="fg"><label>性别</label>
          <select :value="resume.parsed?.gender || ''" @change="onField('gender', $event)">
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
        </div>
      </div>
      <div class="frow">
        <div class="fg"><label>年龄</label>
          <input :value="resume.parsed?.age || ''" @change="onField('age', $event)" />
        </div>
        <div class="fg"><label>手机号 *</label>
          <input :value="resume.parsed?.phone || ''" @change="onField('phone', $event)" data-testid="field-phone" />
        </div>
      </div>
      <div class="frow">
        <div class="fg"><label>邮箱 *</label>
          <input :value="resume.parsed?.email || ''" @change="onField('email', $event)" data-testid="field-email" />
        </div>
        <div class="fg"><label>来源文件</label>
          <input :value="resume.file_name" disabled style="background: var(--g1);" />
        </div>
      </div>
    </div>

    <!-- Education -->
    <div v-if="resume.parsed?.educations?.length" class="detail-section">
      <div class="detail-section-title">教育背景 <span class="seg-count">{{ resume.parsed.educations.length }} 段</span></div>
      <div v-for="(edu, i) in resume.parsed.educations" :key="i" class="seg-item">
        <div class="seg-header"><span class="seg-num">{{ i + 1 }}</span> {{ edu.period }} · {{ edu.school }}</div>
        <div class="seg-readonly"><div class="seg-line"><span>{{ edu.school }}</span><span>{{ edu.major }}</span><span>{{ edu.degree }}</span></div></div>
      </div>
    </div>

    <!-- Experience -->
    <div v-if="resume.parsed?.experiences?.length" class="detail-section">
      <div class="detail-section-title">工作经历 <span class="seg-count">{{ resume.parsed.experiences.length }} 段</span></div>
      <div v-for="(exp, i) in resume.parsed.experiences" :key="i" class="seg-item">
        <div class="seg-header"><span class="seg-num">{{ i + 1 }}</span> {{ exp.period }} · {{ exp.company }} · {{ exp.position }}</div>
        <div style="font-size:10px;color:var(--g5);margin-top:4px;">{{ exp.summary }}</div>
      </div>
    </div>
  </div>

  <div class="right-panel" v-if="resume">
    <div class="rp-section"><div class="rp-title">查重结果</div>
      <CheckBanner :status="resume.duplicate?.status || 'clean'" />
    </div>

    <div v-if="(isOccupied || isUnocc) && resume.duplicate" class="rp-section">
      <div class="rp-title">重复信息</div>
      <DuplicateInfoCard :info="resume.duplicate" :status="resume.status" />
    </div>

    <div v-if="resume.occupyAction === 'apply'" class="rp-section">
      <ApplyPositionSelector :positions="positions" :modelValue="resume.appliedPosition || ''" @update:modelValue="onSelectPos" />
    </div>

    <div v-if="isOccupied" class="rp-section">
      <div class="rp-title">处理选项</div>
      <OccupiedActions :draftId="resume.id" @action="onAction" />
    </div>

    <div v-if="resume.scoreSnapshot" class="rp-section">
      <ScorePanel :score="resume.scoreSnapshot" />
    </div>

    <div class="rp-section"><div class="rp-title">步骤说明</div>
      <div class="nbar info">上传简历后系统将自动解析并查重。<br>• <strong>无重复</strong>：可直接进入下一步<br>• <strong>未占用</strong>：系统有记录但可合并<br>• <strong>已占用</strong>：需选择处理方式</div>
    </div>
  </div>
</template>

<style scoped>
.left-panel { flex: 1; overflow-y: auto; padding: 16px 20px; border-right: 1px solid var(--g3); display: flex; flex-direction: column; gap: 12px; }
.right-panel { width: 340px; flex-shrink: 0; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 14px; }
.detail-header { display: flex; align-items: center; gap: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--g3); }
.detail-avatar { width: 48px; height: 48px; border-radius: 50%; background: var(--pl); display: flex; align-items: center; justify-content: center; font-size: 20px; color: var(--p); font-weight: 600; flex-shrink: 0; }
.detail-name { font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.detail-file { font-size: 12px; color: var(--g5); margin-top: 2px; }
.detail-section { display: flex; flex-direction: column; gap: 4px; }
.detail-section-title { font-size: 12px; font-weight: 600; color: var(--g7); text-transform: uppercase; letter-spacing: 0.5px; padding-bottom: 6px; border-bottom: 1px solid var(--g2); display: flex; align-items: center; justify-content: space-between; }
.seg-count { font-size: 10px; color: var(--g5); font-weight: 400; text-transform: none; letter-spacing: 0; }
.frow { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.fg { display: flex; flex-direction: column; gap: 3px; }
.fg label { font-size: 10px; font-weight: 500; color: var(--g6); }
.fg input, .fg select { padding: 6px 8px; border: 1px solid var(--g4); border-radius: 5px; font-size: 11px; outline: none; font-family: inherit; }
.fg input:focus, .fg select:focus { border-color: var(--p); box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.08); }
.seg-item { border: 1px solid var(--g3); border-radius: 8px; padding: 10px 12px; background: var(--g1); margin-top: 6px; }
.seg-header { display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600; color: var(--g6); margin-bottom: 6px; }
.seg-num { display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: var(--pl); color: var(--p); font-size: 10px; font-weight: 700; }
.seg-readonly { font-size: 11px; color: var(--g7); line-height: 1.6; }
.seg-line { display: flex; gap: 8px; flex-wrap: wrap; }
.rp-section { margin-bottom: 4px; }
.rp-title { font-size: 11px; font-weight: 600; color: var(--g7); margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
.rp-title::after { content: ''; flex: 1; height: 1px; background: var(--g3); }
.replace-file-btn { padding: 6px 10px; border: 1px solid var(--g3); border-radius: 6px; background: #fff; color: var(--g7); font-size: 12px; cursor: pointer; }
.nbar { padding: 8px 12px; border-radius: 8px; font-size: 10px; margin-top: 8px; }
.nbar.info { background: var(--bl); border: 1px solid #BFDBFE; color: #1E40AF; }
</style>
