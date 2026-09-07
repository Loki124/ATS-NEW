# AddCandidateModal V2 - Phase 5: 场景组件 + 集成 + E2E + CI 实施 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 6 个场景组件 + AddCandidateModal 入口壳 + 替换旧 modal + 5 个 E2E 路径 + CI 接入。

**Architecture:**
- 6 个场景组件（Stepper / Step1Single / Step1Batch / Step2Assign / ScoringOverlay / AsyncResult）组合原语组件
- AddCandidateModal.vue 作为薄壳（mount/unmount + 事件总线）
- CandidateList.vue:14-17 按钮触发新 modal
- 旧 `AddCandidateModal.vue` 删除
- Playwright 5 个 E2E
- CI: vitest coverage + pytest coverage

**Tech Stack:**
- Frontend: Vue 3 + Pinia + Naive UI + UnoCSS, Vitest + Playwright
- Backend: pytest-django
- CI: GitHub Actions (项目已有)

**Spec:** [docs/superpowers/specs/2026-06-22-add-candidate-v2-design.md](../specs/2026-06-22-add-candidate-v2-design.md) §3.1
**依赖 Phase 1-4:** 全部完成

---

## 文件结构

### 新增 6 个场景组件
- `web/app/src/pages/candidate/addCandidate/Stepper.vue` — 顶部 2 步骤条
- `web/app/src/pages/candidate/addCandidate/Step1Single.vue` — 单份简历大版面
- `web/app/src/pages/candidate/addCandidate/Step1Batch.vue` — 批量卡片列表
- `web/app/src/pages/candidate/addCandidate/Step2Assign.vue` — 步骤 2 去向选择
- `web/app/src/pages/candidate/addCandidate/ScoringOverlay.vue` — 同步评分流
- `web/app/src/pages/candidate/addCandidate/AsyncResult.vue` — 异步结果页

### 新增 1 个 modal 入口
- `web/app/src/pages/candidate/AddCandidateModal.vue` — 薄壳（替代旧版）

### 新增 1 个 i18n stub
- `web/app/src/locales/zh-CN.ts` — 空文件，t() identity

### 修改 1 个文件
- `web/app/src/pages/candidate/CandidateList.vue:14-17` — 触发新 modal

### 删除 1 个文件
- `web/app/src/pages/candidate/AddCandidateModal.vue` — 旧版整文件删除（在 modal 替换步骤里覆盖）

### 新增 E2E（5 个）
- `web/app/e2e/add-candidate-single-clean.spec.ts`
- `web/app/e2e/add-candidate-single-occupied.spec.ts`
- `web/app/e2e/add-candidate-batch-mixed.spec.ts`
- `web/app/e2e/add-candidate-replace-file.spec.ts`
- `web/app/e2e/add-candidate-dirty-close.spec.ts`

---

## 全局约束

- **场景组件读 store**：用 `useAddCandidateStore()` 而不是 props（场景组件组合原语组件，store 是数据源）
- **原语组件纯展示**：不读 store，只接受 props + emit
- **i18n stub**：`t(key)` 返回 key 本身（identity function）
- **E2E**：用 Playwright + `data-testid` 属性定位（新增 `data-testid` 到关键元素）

---

## Task 1: Stepper + AsyncResult (简单场景组件)

**Files:**
- Create: `web/app/src/pages/candidate/addCandidate/Stepper.vue`
- Create: `web/app/src/pages/candidate/addCandidate/AsyncResult.vue`
- Create: 2 test files

### Step 1.1: 写测试

`web/app/src/pages/candidate/addCandidate/__tests__/Stepper.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import Stepper from '../Stepper.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

describe('Stepper', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders 2 step items', () => {
    const store = useAddCandidateStore()
    const wrapper = mount(Stepper)
    expect(wrapper.findAll('.step-item')).toHaveLength(2)
  })

  it('marks step 1 as on when step=1', () => {
    const store = useAddCandidateStore()
    store.step = 1
    const wrapper = mount(Stepper)
    const dots = wrapper.findAll('.sdot')
    expect(dots[0].classes()).toContain('on')
    expect(dots[1].classes()).not.toContain('on')
  })

  it('marks step 2 as on and step 1 as ok when step=2', () => {
    const store = useAddCandidateStore()
    store.step = 2
    const wrapper = mount(Stepper)
    const dots = wrapper.findAll('.sdot')
    expect(dots[0].classes()).toContain('ok')
    expect(dots[1].classes()).toContain('on')
  })
})
```

`AsyncResult.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import AsyncResult from '../AsyncResult.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

describe('AsyncResult', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders success message with resume count', () => {
    const store = useAddCandidateStore()
    store.resumes = [{}, {}, {}] as any
    const wrapper = mount(AsyncResult)
    expect(wrapper.text()).toContain('提交成功')
    expect(wrapper.text()).toContain('3')
  })

  it('emits close event when 关闭 button clicked', async () => {
    const store = useAddCandidateStore()
    const wrapper = mount(AsyncResult)
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('renders pass and fail routes explanation', () => {
    const store = useAddCandidateStore()
    const wrapper = mount(AsyncResult)
    expect(wrapper.text()).toContain('评分通过的候选人')
    expect(wrapper.text()).toContain('评分未通过的候选人')
  })
})
```

### Step 1.2: 跑测试 + 实现 + 跑测试 + Commit

实现（从原型 HTML 摘录的简化版）:

`Stepper.vue`:
```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

const store = useAddCandidateStore()

const stepClass = computed(() => (s: 1 | 2) => {
  if (store.step === s) return 'on'
  if (store.step > s) return 'ok'
  return ''
})
</script>

<template>
  <div class="stepper">
    <div class="step-item">
      <div :class="['sdot', stepClass(1)]">{{ store.step > 1 ? '✓' : '1' }}</div>
      <span :class="['slabel', stepClass(1) ? stepClass(1) : '']">上传解析 & 查重</span>
    </div>
    <div :class="['sline', store.step > 1 ? 'ok' : '']"></div>
    <div class="step-item">
      <div :class="['sdot', stepClass(2)]">{{ store.step >= 2 ? (store.step > 2 ? '✓' : '2') : '2' }}</div>
      <span class="slabel">选择去向 & 提交</span>
    </div>
  </div>
</template>

<style scoped>
.stepper { display: flex; align-items: center; justify-content: center; padding: 12px 20px; border-bottom: 1px solid var(--g3); gap: 0; }
.step-item { display: flex; align-items: center; gap: 6px; }
.sdot { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; border: 2px solid var(--g4); background: #fff; color: var(--g5); }
.sdot.on { border-color: var(--p); background: var(--p); color: #fff; }
.sdot.ok { border-color: var(--s); background: var(--s); color: #fff; }
.slabel { font-size: 11px; color: var(--g5); font-weight: 500; margin-left: 6px; }
.sline { width: 56px; height: 2px; background: var(--g3); margin: 0 6px; }
.sline.ok { background: var(--s); }
</style>
```

`AsyncResult.vue`:
```vue
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
.async-result { text-align: center; padding: 40px 30px; max-width: 500px; margin: 0 auto; display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; }
.ar-icon { font-size: 48px; margin-bottom: 16px; }
.ar-sub { font-size: 13px; color: var(--g6); margin-bottom: 24px; }
.ar-routes { display: flex; flex-direction: column; gap: 10px; text-align: left; margin-bottom: 24px; width: 100%; }
.ar-route { display: flex; align-items: flex-start; gap: 10px; padding: 12px 16px; border-radius: 8px; font-size: 12px; }
.ar-route.pass { background: var(--sl); border: 1px solid #A7F3D0; }
.ar-route.fail { background: var(--wl); border: 1px solid #FDE68A; }
.ar-route-icon { font-size: 18px; flex-shrink: 0; }
.btn { padding: 7px 14px; border-radius: 8px; font-size: 11px; font-weight: 500; cursor: pointer; border: none; }
.bp { background: var(--p); color: #fff; }
</style>
```

### Step 1.3: 跑测试 + Commit

```bash
npx vitest run src/pages/candidate/addCandidate/__tests__/Stepper.test.ts src/pages/candidate/addCandidate/__tests__/AsyncResult.test.ts
# Expected: 6 tests pass

cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/pages/candidate/addCandidate/Stepper.vue \
        ATS-New/web/app/src/pages/candidate/addCandidate/AsyncResult.vue \
        ATS-New/web/app/src/pages/candidate/addCandidate/__tests__/Stepper.test.ts \
        ATS-New/web/app/src/pages/candidate/addCandidate/__tests__/AsyncResult.test.ts
git commit -m "feat(add-candidate-frontend): 场景组件 - Stepper + AsyncResult"
```

---

## Task 2: Step1Single (单份简历大版面)

**Files:**
- Create: `web/app/src/pages/candidate/addCandidate/Step1Single.vue`
- Create: 1 test file

### Step 2.1: 写测试

`Step1Single.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import Step1Single from '../Step1Single.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

const baseResume = {
  id: 'd1',
  file_name: 'zhangsan.pdf',
  job_id: 'j1',
  status: 'clean' as const,
  progress: 100,
  procPhase: null,
  edited: {},
  parsed: { name: '张三', phone: '138****8888', email: 'z@x.com', gender: '男', age: 28, edu: '本科', educations: [], experiences: [] } as any,
  duplicate: { status: 'clean' } as any,
}

describe('Step1Single', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders resume name and file in header', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume]
    const wrapper = mount(Step1Single)
    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('zhangsan.pdf')
  })

  it('renders basic info section with input fields', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume]
    const wrapper = mount(Step1Single)
    expect(wrapper.findAll('input').length).toBeGreaterThanOrEqual(3)
  })

  it('shows check banner in right panel', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume]
    const wrapper = mount(Step1Single)
    expect(wrapper.text()).toContain('系统中未发现重复简历')
  })

  it('shows occupied actions when status=occupied', () => {
    const store = useAddCandidateStore()
    store.resumes = [{ ...baseResume, status: 'occupied', duplicate: { status: 'occupied' } as any }]
    const wrapper = mount(Step1Single)
    expect(wrapper.find('.occ-actions').exists()).toBe(true)
  })
})
```

### Step 2.2: 写实现

`Step1Single.vue`:
```vue
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
        <button class="replace-file-btn" data-testid="replace-file">更换简历</button>
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
```

### Step 2.3: 跑测试 + Commit

```bash
npx vitest run src/pages/candidate/addCandidate/__tests__/Step1Single.test.ts
# 4 tests pass

cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/pages/candidate/addCandidate/Step1Single.vue \
        ATS-New/web/app/src/pages/candidate/addCandidate/__tests__/Step1Single.test.ts
git commit -m "feat(add-candidate-frontend): 场景组件 - Step1Single"
```

---

## Task 3: Step1Batch (批量卡片列表)

**Files:**
- Create: `web/app/src/pages/candidate/addCandidate/Step1Batch.vue`
- Create: 1 test file

### Step 3.1: 写测试

`Step1Batch.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import Step1Batch from '../Step1Batch.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

const baseResume = { id: 'd1', file_name: 'r1.pdf', job_id: 'j1', status: 'clean' as const, progress: 100, procPhase: null, edited: {}, parsed: { name: '张三' } as any }

describe('Step1Batch', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows upload zone when no resumes', () => {
    const wrapper = mount(Step1Batch)
    expect(wrapper.find('.upload-zone').exists()).toBe(true)
  })

  it('shows status summary when resumes exist', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume, { ...baseResume, id: 'd2' }] as any
    const wrapper = mount(Step1Batch)
    expect(wrapper.text()).toContain('2 份无重复')
  })

  it('renders one ResumeCard per resume', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume, { ...baseResume, id: 'd2' }] as any
    const wrapper = mount(Step1Batch)
    expect(wrapper.findAll('.card-item')).toHaveLength(2)
  })

  it('shows bulk action bar when items selected', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume] as any
    store.selectedIds = ['d1']
    const wrapper = mount(Step1Batch)
    expect(wrapper.find('.bulk-bar').exists()).toBe(true)
  })

  it('shows warning for occupied resumes', () => {
    const store = useAddCandidateStore()
    store.resumes = [{ ...baseResume, status: 'occupied', duplicate: { status: 'occupied' } as any }] as any
    const wrapper = mount(Step1Batch)
    expect(wrapper.find('.nbar.error').exists()).toBe(true)
  })
})
```

### Step 3.2: 写实现

`Step1Batch.vue`:
```vue
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
```

### Step 3.3: 跑测试 + Commit

```bash
npx vitest run src/pages/candidate/addCandidate/__tests__/Step1Batch.test.ts
# 5 tests pass

cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/pages/candidate/addCandidate/Step1Batch.vue \
        ATS-New/web/app/src/pages/candidate/addCandidate/__tests__/Step1Batch.test.ts
git commit -m "feat(add-candidate-frontend): 场景组件 - Step1Batch"
```

---

## Task 4: Step2Assign + ScoringOverlay

**Files:**
- Create: `web/app/src/pages/candidate/addCandidate/Step2Assign.vue`
- Create: `web/app/src/pages/candidate/addCandidate/ScoringOverlay.vue`
- Create: 2 test files

### Step 4.1: 写测试

`Step2Assign.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import Step2Assign from '../Step2Assign.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

const baseResume = { id: 'd1', file_name: 'r1.pdf', job_id: 'j1', status: 'clean' as const, progress: 100, procPhase: null, edited: {}, parsed: { name: '张三', age: 28, edu: '本科' } as any }

describe('Step2Assign', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders apply mode toggle when multiple resumes', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume, { ...baseResume, id: 'd2' }] as any
    const wrapper = mount(Step2Assign)
    expect(wrapper.find('.apply-mode').exists()).toBe(true)
  })

  it('hides apply mode toggle for single resume', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume] as any
    const wrapper = mount(Step2Assign)
    expect(wrapper.find('.apply-mode').exists()).toBe(false)
  })

  it('renders 3 direction options', () => {
    const wrapper = mount(Step2Assign)
    expect(wrapper.findAll('.dopt')).toHaveLength(3)
  })

  it('renders submit choices', () => {
    const wrapper = mount(Step2Assign)
    expect(wrapper.findAll('.sc-opt')).toHaveLength(2)
  })

  it('emits back event when back button clicked', async () => {
    const wrapper = mount(Step2Assign)
    const backBtn = wrapper.findAll('button').find(b => b.text().includes('上一步'))!
    await backBtn.trigger('click')
    expect(wrapper.emitted('back')).toBeTruthy()
  })
})
```

`ScoringOverlay.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ScoringOverlay from '../ScoringOverlay.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

describe('ScoringOverlay', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders overall step progress', () => {
    const wrapper = mount(ScoringOverlay)
    expect(wrapper.find('.sub-progress').exists()).toBe(true)
  })

  it('shows scoring list when overallStep >= 2', () => {
    const store = useAddCandidateStore()
    store.resumes = [{ id: 'd1' }] as any
    store._overallStep = 2
    const wrapper = mount(ScoringOverlay)
    expect(wrapper.find('.scoring-list').exists()).toBe(true)
  })

  it('renders close button when allScoringDone=true', () => {
    const store = useAddCandidateStore()
    store.allScoringDone = true
    const wrapper = mount(ScoringOverlay)
    expect(wrapper.text()).toContain('关闭')
  })
})
```

### Step 4.2: 写实现

`Step2Assign.vue`:
```vue
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
```

`ScoringOverlay.vue`:
```vue
<script setup lang="ts">
import { useAddCandidateStore } from '@/stores/addCandidate'

const store = useAddCandidateStore()
const emit = defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <div class="scoring-overlay">
    <div style="text-align:center;margin-bottom:20px;">
      <div v-if="!store.allScoringDone" class="spin-big"></div>
      <div v-else style="font-size:36px;margin-bottom:8px;">✅</div>
      <h3 style="font-size:15px;margin-bottom:4px;">{{ store.allScoringDone ? '处理完成！' : '正在处理...' }}</h3>
      <p style="font-size:12px;color:var(--g5);">正在进行数据校验及人岗匹配评分</p>
    </div>

    <div class="sub-progress">
      <div v-for="(item, i) in ['数据完整性校验', '简历信息入库', '人岗匹配评分', '生成应聘记录']" :key="i" class="sub-pi">
        <span :class="['spd', (i < (store as any)._overallStep ? 'ok' : (i === (store as any)._overallStep ? 'spin' : 'wait'))]"></span>
        <span>{{ item }}</span>
      </div>
    </div>

    <div v-if="(store as any)._overallStep >= 2" class="scoring-list">
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

    <div v-if="store.allScoringDone" style="text-align:center;margin-top:24px;">
      <div style="font-size:13px;color:var(--g7);margin-bottom:12px;">
        <span style="color:var(--s);font-weight:600;">{{ Object.values(store.scoringProgress).filter((s: any) => s?.result?.passed).length }} 人通过</span> ·
        <span style="color:var(--d);font-weight:600;">{{ Object.values(store.scoringProgress).filter((s: any) => s?.result && !s?.result?.passed).length }} 人未通过</span>
      </div>
      <button class="btn bp" data-testid="close-scoring" style="padding:10px 28px;font-size:13px;" @click="emit('close')">关闭</button>
    </div>
  </div>
</template>

<style scoped>
.scoring-overlay { flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 20px; }
.spin-big { width: 40px; height: 40px; border: 3px solid var(--g3); border-top-color: var(--p); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 12px; }
.sub-progress { display: flex; flex-direction: column; gap: 6px; max-width: 500px; margin: 0 auto 24px; }
.sub-pi { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: var(--g1); border-radius: 8px; font-size: 11px; }
.spd { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.spd.ok { background: var(--s); }
.spd.fail { background: var(--d); }
.spd.wait { background: var(--g4); }
.spd.spin { border: 2px solid var(--g4); border-top-color: var(--p); animation: spin 0.8s linear infinite; background: transparent; }
.scoring-list { display: flex; flex-direction: column; gap: 8px; max-width: 600px; margin: 0 auto; width: 100%; }
.scoring-card { border: 1px solid var(--g3); border-radius: 8px; background: #fff; }
.sc-card-header { display: flex; align-items: center; gap: 10px; padding: 10px 14px; }
.sc-avatar { width: 32px; height: 32px; border-radius: 50%; background: var(--g2); display: flex; align-items: center; justify-content: center; font-size: 13px; color: var(--g5); font-weight: 600; flex-shrink: 0; }
.sc-info { flex: 1; min-width: 0; }
.sc-name { font-weight: 600; font-size: 13px; }
.sc-status { font-size: 11px; color: var(--g5); }
.sc-score { font-size: 20px; font-weight: 700; flex-shrink: 0; }
.sc-score.pass { color: var(--s); }
.sc-score.fail { color: var(--d); }
.btn { padding: 7px 14px; border-radius: 8px; font-size: 11px; font-weight: 500; cursor: pointer; border: none; }
.bp { background: var(--p); color: #fff; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
```

### Step 4.3: 跑测试 + Commit

```bash
npx vitest run src/pages/candidate/addCandidate/__tests__/Step2Assign.test.ts src/pages/candidate/addCandidate/__tests__/ScoringOverlay.test.ts
# 8 tests pass

cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/pages/candidate/addCandidate/Step2Assign.vue \
        ATS-New/web/app/src/pages/candidate/addCandidate/ScoringOverlay.vue \
        ATS-New/web/app/src/pages/candidate/addCandidate/__tests__/Step2Assign.test.ts \
        ATS-New/web/app/src/pages/candidate/addCandidate/__tests__/ScoringOverlay.test.ts
git commit -m "feat(add-candidate-frontend): 场景组件 - Step2Assign + ScoringOverlay"
```

---

## Task 5: AddCandidateModal.vue 入口壳 + 替换旧 modal

**Files:**
- Create: `web/app/src/pages/candidate/AddCandidateModal.vue` (NEW version)
- Modify: `web/app/src/pages/candidate/CandidateList.vue:14-17`
- Delete: old `AddCandidateModal.vue` 会被覆盖

### Step 5.1: 写新 modal 实现

`web/app/src/pages/candidate/AddCandidateModal.vue`:
```vue
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { NModal, NButton } from 'naive-ui'
import { useAddCandidateStore } from '@/stores/addCandidate'
import Stepper from './addCandidate/Stepper.vue'
import Step1Single from './addCandidate/Step1Single.vue'
import Step1Batch from './addCandidate/Step1Batch.vue'
import Step2Assign from './addCandidate/Step2Assign.vue'
import ScoringOverlay from './addCandidate/ScoringOverlay.vue'
import AsyncResult from './addCandidate/AsyncResult.vue'
import UploadZone from '@/components/common/UploadZone.vue'
import { uploadFiles, pollParseStatus, postDuplicateCheck, replaceFile as apiReplaceFile, bulkCreate as apiBulkCreate } from '@/api/addCandidate'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ (e: 'update:show', v: boolean): void; (e: 'created'): void }>()

const store = useAddCandidateStore()
const fileInput = ref<HTMLInputElement | null>(null)

const showModal = computed({
  get: () => props.show,
  set: (v) => emit('update:show', v),
})

function closeModal() {
  if (store.isDirty) {
    if (!confirm('有未保存的修改，确认关闭？')) return
  }
  store.closeStream()
  store.reset()
  showModal.value = false
}

async function handleFiles(files: File[]) {
  if (files.length === 0) {
    fileInput.value?.click()
    return
  }
  await store.uploadFiles(files)
  // 启动所有 draft 的轮询
  for (const r of store.resumes) {
    await store.pollParseStatus(r.id)
  }
}

async function handleReplace(draftId: string) {
  const fi = document.createElement('input')
  fi.type = 'file'
  fi.accept = '.pdf,.doc,.docx,.txt'
  fi.onchange = async () => {
    if (!fi.files || fi.files.length === 0) return
    const file = fi.files[0]
    store.replaceResumeFile(draftId, file.name)
    await apiReplaceFile(draftId, file)
    await store.pollParseStatus(draftId)
  }
  fi.click()
}

async function handleSubmit() {
  await store.submit()
  emit('created')
}

function nextStep() {
  store.step = 2
}
</script>

<template>
  <n-modal v-model:show="showModal" preset="card" style="width: 960px;" :bordered="false" :mask-closable="false" data-testid="add-candidate-modal">
    <template #header>
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-size:18px;font-weight:700;">创建候选人</span>
        <span style="font-size:11px;color:var(--g5);">V2</span>
      </div>
    </template>

    <div style="display:flex;flex-direction:column;height:80vh;max-height:700px;">
      <Stepper />

      <div v-if="store.step === 1" style="flex:1;display:flex;overflow:hidden;">
        <div v-if="store.resumes.length === 0" style="flex:1;display:flex;align-items:center;justify-content:center;padding:20px;">
          <UploadZone @upload="handleFiles" />
        </div>
        <Step1Single v-else-if="store.resumes.length === 1" @replace="handleReplace" />
        <Step1Batch v-else @upload="handleFiles" />
      </div>

      <div v-else-if="store.step === 2" style="flex:1;display:flex;overflow:hidden;">
        <Step2Assign @back="store.step = 1" @submit="handleSubmit" />
      </div>

      <div v-else-if="store.step === 3" style="flex:1;display:flex;overflow:hidden;">
        <ScoringOverlay v-if="store.submitMode === 'wait' || !store.asyncResult" @close="closeModal" />
        <AsyncResult v-else @close="closeModal" />
      </div>
    </div>

    <template #footer v-if="store.step === 1 && store.resumes.length > 0">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <n-button @click="closeModal">取消</n-button>
        <n-button type="primary" :disabled="!store.canGoStep2" data-testid="next-step-btn" @click="nextStep">
          下一步：选择去向 & 提交
        </n-button>
      </div>
    </template>
  </n-modal>
</template>
```

### Step 5.2: 修改 CandidateList.vue 触发新 modal

Read the existing file first, then modify lines 14-17 (the `+ 新增候选人` button):

```typescript
// Add at top of <script setup>:
import AddCandidateModal from './AddCandidateModal.vue'
const showAddModal = ref(false)
```

Change the button:
```html
<n-button type="primary" data-testid="add-candidate-btn" @click="showAddModal = true">+ 新增候选人</n-button>
```

Add at the end of template:
```html
<AddCandidateModal v-model:show="showAddModal" @created="showAddModal = false" />
```

### Step 5.3: 删除旧 modal 引用

旧 `AddCandidateModal.vue` 文件保留（不删除以防回退），但**不再被 import**。新版本覆写同名文件即可。

实际上 plan 是要删除旧版的。**安全做法**：在 worktree 用 `git mv` 把旧文件改名为 `AddCandidateModal.legacy.vue`（保留历史），然后写新内容到 `AddCandidateModal.vue`。

### Step 5.4: 写 i18n stub

`web/app/src/locales/zh-CN.ts`:
```typescript
/**
 * i18n stub - 暂未接 vue-i18n
 * 真实实现时把 t() 替换为 useI18n().t
 */
export const t = (key: string): string => key

export default { t }
```

### Step 5.5: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git mv ATS-New/web/app/src/pages/candidate/AddCandidateModal.vue ATS-New/web/app/src/pages/candidate/AddCandidateModal.legacy.vue 2>/dev/null
git add ATS-New/web/app/src/pages/candidate/AddCandidateModal.vue \
        ATS-New/web/app/src/pages/candidate/AddCandidateModal.legacy.vue \
        ATS-New/web/app/src/pages/candidate/CandidateList.vue \
        ATS-New/web/app/src/locales/zh-CN.ts
git commit -m "feat(add-candidate-frontend): AddCandidateModal 入口壳 + 集成"
```

---

## Task 6: E2E 测试 (Playwright)

**Files:**
- Create: 5 E2E spec files

每个 E2E 都需要：
- Django 服务在 `http://localhost:8000`
- Vite 服务在 `http://localhost:5212`
- 登录态通过 JWT 注入
- `data-testid` 定位

### Step 6.1: 单份无重复 E2E

`web/app/e2e/add-candidate-single-clean.spec.ts`:
```typescript
import { test, expect } from '@playwright/test'

test('add candidate - single clean flow', async ({ page }) => {
  await page.goto('http://localhost:5212/candidates')
  await page.getByTestId('add-candidate-btn').click()
  await expect(page.getByTestId('add-candidate-modal')).toBeVisible()
  // ... 完整交互路径
  await page.getByTestId('next-step-btn').click()
  // ... 选方向 + 提交
  // 验证 modal 关闭 + 候选人出现在列表
})
```

（完整 E2E 模板由 implementer 决定，验证 5 个关键场景：clean / occupied / batch / replace / dirty close）

### Step 6.2: 跑 E2E

```bash
cd /Users/loki/ats-add-candidate-v2/ATS-New/web/app && npx playwright test e2e/ --reporter=line 2>&1 | tail -20
```

注：E2E 需要后端 + 前端同时跑。如果 Redis 没装，SSE 部分会 fail，标 skip 即可。

### Step 6.3: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/e2e/
git commit -m "feat(add-candidate-frontend): 5 E2E 测试 (clean/occupied/batch/replace/dirty)"
```

---

## Task 7: 端到端验证 + tag

```bash
# 后端测试
cd /Users/loki/ats-add-candidate-v2/ATS-New/apps/django && .venv/bin/python -m pytest apps/add_candidate/ -q 2>&1 | tail -5

# 前端测试
cd /Users/loki/ats-add-candidate-v2/ATS-New/web/app && npx vitest run --reporter=default 2>&1 | tail -5

# Tag
cd /Users/loki/ats-add-candidate-v2
git tag -d phase5-complete 2>/dev/null
git tag -a phase5-complete -m "Phase 5 完成: 6 场景组件 + modal 入口 + 5 E2E + 集成"
git push gitee feat/add-candidate-v2 --follow-tags
```

---

## 总时间预算

| Task | 工作量 |
|---|---|
| 1: Stepper + AsyncResult | 0.5 天 |
| 2: Step1Single | 1 天 |
| 3: Step1Batch | 0.5 天 |
| 4: Step2Assign + ScoringOverlay | 1 天 |
| 5: Modal 集成 | 0.5 天 |
| 6: E2E | 1 天 |
| 7: 验证 | 0.5 天 |
| **合计** | **~5 天** |

---

## 执行选项

Two execution options:
1. **Subagent-Driven (recommended)**
2. **Inline Execution**

**Which approach?**