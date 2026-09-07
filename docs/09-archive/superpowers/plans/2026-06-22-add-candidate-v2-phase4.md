# AddCandidateModal V2 - Phase 4: 前端原语组件 实施 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 10 个 Vue 3 原语组件，封装状态 tag / 横幅 / 重复信息卡 / 占用操作 / 职位 chip 等可复用 UI 元素。

**Architecture:**
- 10 个原语组件独立文件，按职责单一原则
- 组件接受 props + emits，**不直接调 store**（保持纯展示组件，方便 Phase 5 场景组件组合）
- 复用项目现有 Naive UI 组件 + UnoCSS 工具类
- 金色品牌色（`#FBCE5B → #E5B82A` 渐变）通过 `var(--primary)` `var(--primary-dark)` 引用

**Tech Stack:**
- Frontend: Vue 3 + TypeScript + Composition API + Naive UI + UnoCSS
- 测试: vitest + @vue/test-utils + happy-dom

**Spec:** [docs/superpowers/specs/2026-06-22-add-candidate-v2-design.md](../specs/2026-06-22-add-candidate-v2-design.md) §3.1
**依赖 Phase 3:** Pinia store + API 客户端已就绪

---

## 文件结构

### 新增 10 个原语组件
- `web/app/src/components/common/StatusTag.vue` — 状态 tag（4 状态）
- `web/app/src/components/common/CheckBanner.vue` — 查重结果横幅
- `web/app/src/components/common/DuplicateInfoCard.vue` — 重复信息卡
- `web/app/src/components/common/OccupiedActions.vue` — 5 处理按钮
- `web/app/src/components/common/ApplyPositionSelector.vue` — 申请分配选职位
- `web/app/src/components/common/ScorePanel.vue` — 评分面板（4 维度）
- `web/app/src/components/common/ResumeCard.vue` — 批量模式单条卡片
- `web/app/src/components/common/PositionChips.vue` — 职位 chip 多选
- `web/app/src/components/common/DirectionPicker.vue` — 3 方向按钮
- `web/app/src/components/common/UploadZone.vue` — 拖拽上传区

### 新增 10 个测试文件
- `web/app/src/components/common/__tests__/StatusTag.test.ts`
- `web/app/src/components/common/__tests__/CheckBanner.test.ts`
- `...` （每个组件一个）

---

## 全局约束

- **金色品牌色**：CSS 变量 `var(--primary)` / `var(--primary-dark)`（已配置在 `index.css` + `uno.config.ts`）
- **Naive UI 优先**：基础 UI 元素（按钮、输入框、tag、card）用 Naive UI
- **TypeScript strict**：所有 props 用 `defineProps<{...}>()` + 类型
- **emits 命名**：kebab-case（`update:model-value` 等）
- **v-model**：用 `defineModel()` 或 `update:xxx` 模式

---

## Task 1: StatusTag + CheckBanner (基础 tag + 横幅)

**Files:**
- Create: `web/app/src/components/common/StatusTag.vue`
- Create: `web/app/src/components/common/CheckBanner.vue`
- Create: `web/app/src/components/common/__tests__/StatusTag.test.ts`
- Create: `web/app/src/components/common/__tests__/CheckBanner.test.ts`

### Step 1.1: 写失败测试

`web/app/src/components/common/__tests__/StatusTag.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusTag from '../StatusTag.vue'

describe('StatusTag', () => {
  it.each([
    ['clean', '无重复', 'g'],
    ['unocc', '未占用', 'y'],
    ['occupied', '已占用', 'r'],
    ['processing', '处理中', 'b'],
  ])('renders %s status with label %s and color %s', (status, label, color) => {
    const wrapper = mount(StatusTag, { props: { status } })
    expect(wrapper.text()).toContain(label)
    expect(wrapper.find('.tag').classes()).toContain(`tag-${color}`)
  })

  it('renders null status as fallback', () => {
    const wrapper = mount(StatusTag, { props: { status: 'unknown' as any } })
    expect(wrapper.text()).toContain('未知')
  })
})
```

`web/app/src/components/common/__tests__/CheckBanner.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CheckBanner from '../CheckBanner.vue'

describe('CheckBanner', () => {
  it.each([
    ['clean', '系统中未发现重复简历'],
    ['unocc', '系统中已有同名简历'],
    ['occupied', '该候选人已被占用'],
    ['processing', '简历正在处理中'],
  ])('renders %s banner with appropriate text', (status, text) => {
    const wrapper = mount(CheckBanner, { props: { status } })
    expect(wrapper.text()).toContain(text)
    expect(wrapper.find('.cb').classes()).toContain(status)
  })
})
```

### Step 1.2: 跑测试确认失败

```bash
cd /Users/loki/ats-add-candidate-v2/ATS-New/web/app && npx vitest run src/components/common/__tests__/StatusTag.test.ts src/components/common/__tests__/CheckBanner.test.ts
```
Expected: 失败（无 module）

### Step 1.3: 写实现

`web/app/src/components/common/StatusTag.vue`:
```vue
<script setup lang="ts">
type Status = 'processing' | 'clean' | 'unocc' | 'occupied'
const props = defineProps<{ status: Status }>()

const config: Record<Status, { label: string; color: string }> = {
  clean: { label: '无重复', color: 'g' },
  unocc: { label: '未占用', color: 'y' },
  occupied: { label: '已占用', color: 'r' },
  processing: { label: '处理中', color: 'b' },
}

const cfg = config[props.status] || { label: '未知', color: 'g' }
</script>

<template>
  <span :class="['tag', `tag-${cfg.color}`]">
    <span :class="['td', `td-${cfg.color}`]"></span>
    {{ cfg.label }}
  </span>
</template>

<style scoped>
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
.td {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}
.tag-g { background: var(--sl); color: #065F46; }
.tag-y { background: var(--wl); color: #92400E; }
.tag-r { background: var(--dl); color: #991B1B; }
.tag-b { background: var(--bl); color: #1E40AF; }
.td-g { background: var(--s); }
.td-y { background: var(--w); }
.td-r { background: var(--d); }
.td-b { background: var(--b); animation: pulse2 1s infinite; }
@keyframes pulse2 { 0%,100% { opacity: 1 } 50% { opacity: 0.3 } }
</style>
```

`web/app/src/components/common/CheckBanner.vue`:
```vue
<script setup lang="ts">
type Status = 'processing' | 'clean' | 'unocc' | 'occupied'
defineProps<{ status: Status }>()

const config = {
  clean: { icon: '✅', text: '系统中未发现重复简历，该候选人可正常入库。' },
  unocc: { icon: 'ℹ️', text: '系统中已有同名简历，但未被任何流程占用。提交时系统会合并新旧简历信息。' },
  occupied: { icon: '⚠️', text: '该候选人在系统中已被占用。当前被其他流程锁定，请选择处理方式。' },
  processing: { icon: '⏳', text: '简历正在处理中，请稍候...' },
}
</script>

<template>
  <div :class="['cb', $props.status]">
    <span class="cb-icon">{{ config[$props.status]?.icon }}</span>
    <div>{{ config[$props.status]?.text }}</div>
  </div>
</template>

<style scoped>
.cb {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 11px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  line-height: 1.5;
}
.cb-icon { font-size: 16px; flex-shrink: 0; margin-top: 1px; }
.cb.clean { background: var(--sl); color: #065F46; border: 1px solid #A7F3D0; }
.cb.unocc { background: var(--wl); color: #92400E; border: 1px solid #FDE68A; }
.cb.occupied { background: var(--dl); color: #991B1B; border: 1px solid #FECACA; }
.cb.processing { background: var(--bl); color: #1E40AF; border: 1px solid #BFDBFE; }
</style>
```

### Step 1.4: 跑测试

```bash
npx vitest run src/components/common/__tests__/StatusTag.test.ts src/components/common/__tests__/CheckBanner.test.ts
```
Expected: 8 tests pass (4 + 4)

### Step 1.5: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/components/common/StatusTag.vue \
        ATS-New/web/app/src/components/common/CheckBanner.vue \
        ATS-New/web/app/src/components/common/__tests__/StatusTag.test.ts \
        ATS-New/web/app/src/components/common/__tests__/CheckBanner.test.ts
git commit -m "feat(add-candidate-frontend): 原语组件 - StatusTag + CheckBanner"
```

---

## Task 2: DuplicateInfoCard + OccupiedActions

**Files:**
- Create: `web/app/src/components/common/DuplicateInfoCard.vue`
- Create: `web/app/src/components/common/OccupiedActions.vue`
- Create: 2 test files

### Step 2.1: 写测试

`DuplicateInfoCard.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DuplicateInfoCard from '../DuplicateInfoCard.vue'

const info = {
  existing_resume_id: 'RES-2024-08521',
  created_at: '2024-08-15',
  history: '高级前端工程师（2024-08）· 已归档',
  cur_status: '未占用 · 可安全合并',
  active_application_id: undefined as string | undefined,
}

describe('DuplicateInfoCard', () => {
  it('renders all info rows when status=unocc', () => {
    const wrapper = mount(DuplicateInfoCard, { props: { info, status: 'unocc' } })
    expect(wrapper.text()).toContain('RES-2024-08521')
    expect(wrapper.text()).toContain('2024-08-15')
    expect(wrapper.text()).toContain('高级前端工程师')
    expect(wrapper.text()).toContain('未占用')
  })

  it('renders status with red color when occupied', () => {
    const wrapper = mount(DuplicateInfoCard, {
      props: { info: { ...info, cur_status: '已占用 · 面试中' }, status: 'occupied' },
    })
    const valueEl = wrapper.find('.dup-value')
    expect(valueEl.attributes('style')).toContain('color:')
  })
})
```

`OccupiedActions.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import OccupiedActions from '../OccupiedActions.vue'

describe('OccupiedActions', () => {
  it('renders 5 action buttons', () => {
    const wrapper = mount(OccupiedActions, { props: { draftId: 'd1' } })
    const btns = wrapper.findAll('.occ-btn')
    expect(btns).toHaveLength(5)
  })

  it('emits action event with draftId and action name when clicked', async () => {
    const wrapper = mount(OccupiedActions, { props: { draftId: 'd1' } })
    const pendingBtn = wrapper.findAll('.occ-btn').find((b) => b.text().includes('待分配'))!
    await pendingBtn.trigger('click')
    expect(wrapper.emitted('action')?.[0]).toEqual(['d1', 'pending'])
  })

  it('emits merge event', async () => {
    const wrapper = mount(OccupiedActions, { props: { draftId: 'd2' } })
    const mergeBtn = wrapper.findAll('.occ-btn').find((b) => b.text().includes('合并'))!
    await mergeBtn.trigger('click')
    expect(wrapper.emitted('action')?.[0]).toEqual(['d2', 'merge'])
  })
})
```

### Step 2.2: 跑测试确认失败

### Step 2.3: 写实现

`DuplicateInfoCard.vue`:
```vue
<script setup lang="ts">
import type { DuplicateInfo } from '@/api/addCandidate'

defineProps<{ info: Partial<DuplicateInfo>; status: 'unocc' | 'occupied' }>()
</script>

<template>
  <div class="dup-card">
    <div class="dup-row">
      <span class="dup-label">已有简历ID</span>
      <span class="dup-value">{{ info.existing_resume_id }}</span>
    </div>
    <div class="dup-row">
      <span class="dup-label">创建时间</span>
      <span class="dup-value">{{ info.created_at }}</span>
    </div>
    <div class="dup-row">
      <span class="dup-label">历史应聘</span>
      <span class="dup-value">{{ info.history }}</span>
    </div>
    <div class="dup-row">
      <span class="dup-label">当前状态</span>
      <span class="dup-value" :style="{ color: status === 'occupied' ? '#991B1B' : '#92400E' }">
        {{ info.cur_status }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.dup-card {
  border: 1px solid #FDE68A;
  border-radius: 8px;
  padding: 10px 14px;
  background: #FFFDF5;
  font-size: 11px;
}
.dup-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
.dup-label { color: var(--g5); }
.dup-value { font-weight: 500; }
</style>
```

`OccupiedActions.vue`:
```vue
<script setup lang="ts">
defineProps<{ draftId: string }>()
const emit = defineEmits<{
  (e: 'action', draftId: string, action: 'pending' | 'merge' | 'apply' | 'cancel' | 'score'): void
}>()
</script>

<template>
  <div class="occ-actions">
    <button class="occ-btn primary" @click="emit('action', draftId, 'pending')">上传至待分配</button>
    <button class="occ-btn" @click="emit('action', draftId, 'merge')">合并至已有简历</button>
    <button class="occ-btn" @click="emit('action', draftId, 'apply')">申请分配</button>
    <button class="occ-btn warn" @click="emit('action', draftId, 'cancel')">取消上传</button>
    <button class="occ-btn" @click="emit('action', draftId, 'score')">模拟评分</button>
  </div>
</template>

<style scoped>
.occ-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.occ-btn {
  padding: 5px 12px;
  border: 1px solid var(--g3);
  border-radius: 8px;
  font-size: 10px;
  cursor: pointer;
  background: #fff;
  color: var(--g7);
  transition: 0.15s;
}
.occ-btn:hover { border-color: var(--p); background: var(--pl); }
.occ-btn.primary { background: var(--p); color: #fff; border-color: var(--p); }
.occ-btn.primary:hover { background: var(--ph); }
.occ-btn.warn { color: #991B1B; border-color: var(--d); }
.occ-btn.warn:hover { background: var(--dl); }
</style>
```

### Step 2.4: 跑测试

Expected: 5 tests pass

### Step 2.5: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/components/common/DuplicateInfoCard.vue \
        ATS-New/web/app/src/components/common/OccupiedActions.vue \
        ATS-New/web/app/src/components/common/__tests__/DuplicateInfoCard.test.ts \
        ATS-New/web/app/src/components/common/__tests__/OccupiedActions.test.ts
git commit -m "feat(add-candidate-frontend): 原语组件 - DuplicateInfoCard + OccupiedActions"
```

---

## Task 3: ApplyPositionSelector + ScorePanel

**Files:**
- Create: `web/app/src/components/common/ApplyPositionSelector.vue`
- Create: `web/app/src/components/common/ScorePanel.vue`
- Create: 2 test files

### Step 3.1: 写测试

`ApplyPositionSelector.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ApplyPositionSelector from '../ApplyPositionSelector.vue'

const positions = ['高级前端工程师', '资深前端工程师', '前端架构师', '产品经理']

describe('ApplyPositionSelector', () => {
  it('renders all position options', () => {
    const wrapper = mount(ApplyPositionSelector, { props: { positions, modelValue: '' } })
    const items = wrapper.findAll('.apply-pos-item')
    expect(items).toHaveLength(positions.length)
  })

  it('emits update:modelValue with selected position', async () => {
    const wrapper = mount(ApplyPositionSelector, { props: { positions, modelValue: '' } })
    await wrapper.findAll('.apply-pos-item')[0].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['高级前端工程师'])
  })

  it('highlights currently selected position', () => {
    const wrapper = mount(ApplyPositionSelector, { props: { positions, modelValue: '前端架构师' } })
    const items = wrapper.findAll('.apply-pos-item')
    expect(items[2].classes()).toContain('sel')
  })
})
```

`ScorePanel.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScorePanel from '../ScorePanel.vue'

const score = {
  score: 78,
  passed: true,
  dimensions: [
    { name: '技术匹配', score: 82 },
    { name: '经验匹配', score: 75 },
    { name: '学历匹配', score: 90 },
    { name: '综合素质', score: 65 },
  ],
}

describe('ScorePanel', () => {
  it('renders overall score', () => {
    const wrapper = mount(ScorePanel, { props: { score } })
    expect(wrapper.text()).toContain('78')
  })

  it('renders pass tag when passed=true', () => {
    const wrapper = mount(ScorePanel, { props: { score } })
    expect(wrapper.text()).toContain('通过')
  })

  it('renders fail tag when passed=false', () => {
    const wrapper = mount(ScorePanel, { props: { score: { ...score, passed: false } } })
    expect(wrapper.text()).toContain('未通过')
  })

  it('renders 4 dimension bars', () => {
    const wrapper = mount(ScorePanel, { props: { score } })
    const dims = wrapper.findAll('.sc-dim')
    expect(dims).toHaveLength(4)
  })
})
```

### Step 3.2: 跑测试

Expected: 7 tests pass

### Step 3.3: 写实现

`ApplyPositionSelector.vue`:
```vue
<script setup lang="ts">
const props = defineProps<{ positions: string[]; modelValue: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', val: string): void }>()

function select(pos: string) {
  emit('update:modelValue', pos)
}
</script>

<template>
  <div class="apply-pos">
    <div class="apply-pos-title">选择目标职位</div>
    <div class="apply-pos-list">
      <div
        v-for="p in positions"
        :key="p"
        :class="['apply-pos-item', { sel: modelValue === p }]"
        @click="select(p)"
      >
        {{ p }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.apply-pos {
  margin-top: 8px;
  padding: 10px 12px;
  background: var(--bl);
  border: 1px solid #BFDBFE;
  border-radius: 8px;
}
.apply-pos-title { font-size: 11px; font-weight: 600; color: #1E40AF; margin-bottom: 6px; }
.apply-pos-list { display: flex; flex-wrap: wrap; gap: 6px; }
.apply-pos-item {
  padding: 4px 10px;
  border: 1px solid var(--g3);
  border-radius: 8px;
  cursor: pointer;
  font-size: 10px;
  background: #fff;
  transition: 0.15s;
}
.apply-pos-item:hover { border-color: var(--p); }
.apply-pos-item.sel { border-color: var(--p); background: var(--pl); color: var(--p); font-weight: 500; }
</style>
```

`ScorePanel.vue`:
```vue
<script setup lang="ts">
interface ScoreResult {
  score: number
  passed: boolean
  dimensions: Array<{ name: string; score: number }>
}
const props = defineProps<{ score: ScoreResult }>()

function dimColor(s: number) {
  if (s >= 80) return 'var(--s)'
  if (s >= 60) return 'var(--w)'
  return 'var(--d)'
}
</script>

<template>
  <div class="score-panel">
    <div class="score-panel-title">🎯 模拟评分结果</div>
    <div class="score-overall-row">
      <div :class="['score-big', score.passed ? 'pass' : 'fail']">{{ score.score }}</div>
      <div>
        <div style="font-size:11px;color:var(--g6);">综合匹配分</div>
        <span :class="['score-pass-tag', score.passed ? 'pass' : 'fail']">
          {{ score.passed ? '通过' : '未通过' }}
        </span>
      </div>
    </div>
    <div style="font-size:10px;color:var(--g5);margin-bottom:8px;">及格线：60分 · 仅供参考</div>
    <div v-for="dim in score.dimensions" :key="dim.name" class="sc-dim">
      <span class="sc-dim-name">{{ dim.name }}</span>
      <div class="sc-dim-bar">
        <div class="sc-dim-fill" :style="{ width: `${dim.score}%`, background: dimColor(dim.score) }"></div>
      </div>
      <span class="sc-dim-score">{{ dim.score }}</span>
    </div>
  </div>
</template>

<style scoped>
.score-panel {
  border: 1px solid var(--g3);
  border-radius: 8px;
  padding: 12px;
  background: var(--g1);
  margin-top: 8px;
}
.score-panel-title { font-size: 11px; font-weight: 600; color: var(--g7); margin-bottom: 8px; }
.score-overall-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.score-big { font-size: 28px; font-weight: 700; line-height: 1; }
.score-big.pass { color: var(--s); }
.score-big.fail { color: var(--d); }
.score-pass-tag { padding: 2px 8px; border-radius: 20px; font-size: 10px; font-weight: 600; display: inline-block; margin-top: 2px; }
.score-pass-tag.pass { background: var(--sl); color: #065F46; }
.score-pass-tag.fail { background: var(--dl); color: #991B1B; }
.sc-dim { display: flex; align-items: center; gap: 8px; margin-top: 6px; font-size: 11px; }
.sc-dim-name { width: 70px; color: var(--g6); flex-shrink: 0; }
.sc-dim-bar { flex: 1; height: 6px; background: var(--g2); border-radius: 3px; overflow: hidden; }
.sc-dim-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.sc-dim-score { width: 28px; text-align: right; font-weight: 600; flex-shrink: 0; }
</style>
```

### Step 3.4: 跑测试

Expected: 7 tests pass

### Step 3.5: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/components/common/ApplyPositionSelector.vue \
        ATSNew/web/app/src/components/common/ScorePanel.vue \
        ATS-New/web/app/src/components/common/__tests__/ApplyPositionSelector.test.ts \
        ATS-New/web/app/src/components/common/__tests__/ScorePanel.test.ts
git commit -m "feat(add-candidate-frontend): 原语组件 - ApplyPositionSelector + ScorePanel"
```

---

## Task 4: ResumeCard + PositionChips

**Files:**
- Create: `web/app/src/components/common/ResumeCard.vue`
- Create: `web/app/src/components/common/PositionChips.vue`
- Create: 2 test files

### Step 4.1: 写测试

`ResumeCard.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ResumeCard from '../ResumeCard.vue'
import type { ResumeDraft } from '@/stores/addCandidate'

const baseResume: ResumeDraft = {
  id: 'd1',
  file_name: 'zhangsan.pdf',
  job_id: 'j1',
  status: 'clean',
  progress: 100,
  procPhase: null,
  edited: {},
  parsed: { name: '张三', phone: '138****8888', email: 'z@x.com', gender: '男', age: 28 } as any,
  duplicate: { status: 'clean' } as any,
}

describe('ResumeCard', () => {
  it('renders name, file, gender, age, phone from parsed', () => {
    const wrapper = mount(ResumeCard, { props: { resume: baseResume, active: false, selected: false } })
    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('zhangsan.pdf')
    expect(wrapper.text()).toContain('138****8888')
  })

  it('shows status tag for status=clean', () => {
    const wrapper = mount(ResumeCard, { props: { resume: baseResume, active: false, selected: false } })
    expect(wrapper.text()).toContain('无重复')
  })

  it('emits toggle when header clicked', async () => {
    const wrapper = mount(ResumeCard, { props: { resume: baseResume, active: false, selected: false } })
    await wrapper.find('.c-header').trigger('click')
    expect(wrapper.emitted('toggle')).toBeTruthy()
  })

  it('applies expanded class when active=true', () => {
    const wrapper = mount(ResumeCard, { props: { resume: baseResume, active: true, selected: false } })
    expect(wrapper.find('.card-item').classes()).toContain('expanded')
  })

  it('shows progress bar when status=processing', () => {
    const wrapper = mount(ResumeCard, {
      props: { resume: { ...baseResume, status: 'processing', progress: 50, procPhase: 'parsing' }, active: false, selected: false },
    })
    expect(wrapper.find('.pbar').exists()).toBe(true)
  })
})
```

`PositionChips.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PositionChips from '../PositionChips.vue'

const positions = ['高级前端工程师', '资深前端工程师', '前端架构师', '产品经理']

describe('PositionChips', () => {
  it('renders all positions as chips', () => {
    const wrapper = mount(PositionChips, { props: { positions, modelValue: [] } })
    expect(wrapper.findAll('.pos-item')).toHaveLength(positions.length)
  })

  it('emits update:modelValue with single selection', async () => {
    const wrapper = mount(PositionChips, { props: { positions, modelValue: [] } })
    await wrapper.findAll('.pos-item')[0].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([['高级前端工程师']])
  })

  it('highlights selected positions', () => {
    const wrapper = mount(PositionChips, { props: { positions, modelValue: ['前端架构师'] } })
    const items = wrapper.findAll('.pos-item')
    expect(items[2].classes()).toContain('sel')
  })
})
```

### Step 4.2: 跑测试

Expected: 8 tests pass

### Step 4.3: 写实现

`ResumeCard.vue`:
```vue
<script setup lang="ts">
import type { ResumeDraft } from '@/stores/addCandidate'
import StatusTag from './StatusTag.vue'
import CheckBanner from './CheckBanner.vue'

const props = defineProps<{
  resume: ResumeDraft
  active: boolean
  selected: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle'): void
  (e: 'select'): void
  (e: 'replace'): void
}>()

function getStatusClass(s: string) {
  if (s === 'clean') return 'clean'
  if (s === 'unocc') return 'unocc'
  if (s === 'occupied') return 'occ'
  return ''
}

function progressColor(p: string | null) {
  if (p === 'uploading') return 'bl'
  if (p === 'parsing') return 'ye'
  if (p === 'checking') return 'pu'
  return 'bl'
}
</script>

<template>
  <div :class="['card-item', getStatusClass(resume.status), { expanded: active, selected }]">
    <div class="c-header" @click="emit('toggle')">
      <div v-if="resume.status !== 'processing'" :class="['c-chk', { checked: selected }]" @click.stop="emit('select')"></div>
      <div v-else style="width:16px;flex-shrink:0;"></div>
      <div class="c-avatar">{{ resume.parsed?.name?.charAt(0) || resume.file_name.charAt(0) }}</div>
      <div class="c-info">
        <div class="c-name">
          {{ resume.parsed?.name || resume.file_name }}
          <span class="c-file">{{ resume.file_name }}</span>
          <StatusTag :status="resume.status" />
        </div>
        <div class="c-basic">
          <span v-if="resume.parsed?.gender">{{ resume.parsed.gender }}</span>
          <span v-if="resume.parsed?.age">{{ resume.parsed.age }}岁</span>
          <span v-if="resume.parsed?.phone">{{ resume.parsed.phone }}</span>
          <span v-if="resume.parsed?.edu">{{ resume.parsed.edu }}</span>
          <span v-if="resume.parsed?.position">{{ resume.parsed.position }}</span>
        </div>
        <div v-if="resume.status === 'processing'" class="pbar">
          <div :class="['pfill', progressColor(resume.procPhase)]" :style="{ width: `${resume.progress}%` }"></div>
        </div>
      </div>
      <button v-if="resume.status !== 'processing'" class="replace-file-btn" @click.stop="emit('replace')">更换</button>
      <div class="c-expand">▾</div>
    </div>

    <div v-if="active" class="c-body">
      <CheckBanner v-if="resume.duplicate" :status="resume.duplicate.status" />
      <!-- Phase 5 场景组件会在这里插入更多内容 -->
      <slot name="body" />
    </div>
  </div>
</template>

<style scoped>
.card-item {
  border: 1px solid var(--g3);
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
  transition: 0.15s;
}
.card-item:hover { border-color: var(--p); }
.card-item.selected { border-color: var(--p); box-shadow: 0 0 0 1px rgba(79, 70, 229, 0.15); }
.card-item.occ { border-left: 3px solid var(--d); }
.card-item.unocc { border-left: 3px solid var(--w); }
.card-item.clean { border-left: 3px solid var(--s); }

.c-header { display: flex; align-items: center; gap: 10px; padding: 12px 14px; cursor: pointer; }
.c-chk {
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
.c-chk.checked { background: var(--p); border-color: var(--p); }
.c-chk.checked::after { content: '✓'; color: #fff; font-size: 10px; }

.c-avatar {
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
.c-info { flex: 1; min-width: 0; }
.c-name { font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.c-file { font-size: 10px; color: var(--g5); font-weight: 400; }
.c-basic { font-size: 11px; color: var(--g6); display: flex; gap: 10px; flex-wrap: wrap; margin-top: 2px; }
.c-expand { font-size: 16px; color: var(--g5); transition: 0.2s; flex-shrink: 0; }
.card-item.expanded .c-expand { transform: rotate(180deg); }

.pbar { height: 3px; background: var(--g3); border-radius: 2px; overflow: hidden; margin-top: 4px; }
.pfill { height: 100%; border-radius: 2px; transition: width 0.3s; }
.pfill.bl { background: var(--b); }
.pfill.ye { background: #F59E0B; }
.pfill.pu { background: #8B5CF6; }

.replace-file-btn {
  padding: 4px 8px;
  font-size: 11px;
  border: 1px solid var(--g3);
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.c-body { padding: 0 14px 14px; border-top: 1px solid var(--g3); }
</style>
```

`PositionChips.vue`:
```vue
<script setup lang="ts">
const props = defineProps<{ positions: string[]; modelValue: string[] }>()
const emit = defineEmits<{ (e: 'update:modelValue', val: string[]): void }>()

function toggle(pos: string) {
  if (modelValue.includes(pos)) {
    emit('update:modelValue', modelValue.filter((p) => p !== pos))
  } else {
    emit('update:modelValue', [...modelValue, pos])
  }
}
</script>

<template>
  <div class="pos-list">
    <div
      v-for="p in positions"
      :key="p"
      :class="['pos-item', { sel: modelValue.includes(p) }]"
      @click="toggle(p)"
    >
      {{ p }}
    </div>
  </div>
</template>

<style scoped>
.pos-list { display: flex; flex-wrap: wrap; gap: 6px; }
.pos-item {
  padding: 6px 12px;
  border: 1px solid var(--g3);
  border-radius: 8px;
  cursor: pointer;
  font-size: 11px;
  background: #fff;
  transition: 0.15s;
}
.pos-item:hover { border-color: var(--p); }
.pos-item.sel { border-color: var(--p); background: var(--pl); color: var(--p); font-weight: 500; }
</style>
```

### Step 4.4: 跑测试

Expected: 8 tests pass

### Step 4.5: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/components/common/ResumeCard.vue \
        ATS-New/web/app/src/components/common/PositionChips.vue \
        ATS-New/web/app/src/components/common/__tests__/ResumeCard.test.ts \
        ATS-New/web/app/src/components/common/__tests__/PositionChips.test.ts
git commit -m "feat(add-candidate-frontend): 原语组件 - ResumeCard + PositionChips"
```

---

## Task 5: DirectionPicker + UploadZone

**Files:**
- Create: `web/app/src/components/common/DirectionPicker.vue`
- Create: `web/app/src/components/common/UploadZone.vue`
- Create: 2 test files

### Step 5.1: 写测试

`DirectionPicker.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DirectionPicker from '../DirectionPicker.vue'

describe('DirectionPicker', () => {
  it('renders 3 options', () => {
    const wrapper = mount(DirectionPicker, { props: { modelValue: '', hasOccupied: false } })
    expect(wrapper.findAll('.dopt')).toHaveLength(3)
  })

  it('emits update:modelValue when option clicked', async () => {
    const wrapper = mount(DirectionPicker, { props: { modelValue: '', hasOccupied: false } })
    await wrapper.findAll('.dopt')[0].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['pending'])
  })

  it('disables talent and position options when hasOccupied=true', () => {
    const wrapper = mount(DirectionPicker, { props: { modelValue: '', hasOccupied: true } })
    const opts = wrapper.findAll('.dopt')
    expect(opts[1].classes()).toContain('off')  // talent
    expect(opts[2].classes()).toContain('off')  // position
    expect(opts[0].classes()).not.toContain('off')  // pending
  })

  it('highlights currently selected option', () => {
    const wrapper = mount(DirectionPicker, { props: { modelValue: 'position', hasOccupied: false } })
    const opts = wrapper.findAll('.dopt')
    expect(opts[2].classes()).toContain('sel')
  })
})
```

`UploadZone.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UploadZone from '../UploadZone.vue'

describe('UploadZone', () => {
  it('renders upload hint and quick actions', () => {
    const wrapper = mount(UploadZone)
    expect(wrapper.text()).toContain('点击上传或拖拽')
    expect(wrapper.text()).toContain('PDF / Word / TXT')
  })

  it('emits upload event when zone clicked', async () => {
    const wrapper = mount(UploadZone)
    await wrapper.find('.upload-zone').trigger('click')
    expect(wrapper.emitted('upload')).toBeTruthy()
  })

  it('adds dragover class on dragover', async () => {
    const wrapper = mount(UploadZone)
    await wrapper.find('.upload-zone').trigger('dragover')
    expect(wrapper.find('.upload-zone').classes()).toContain('dragover')
  })

  it('emits upload event on drop with files', async () => {
    const wrapper = mount(UploadZone)
    const file = new File(['x'], 'test.pdf', { type: 'application/pdf' })
    await wrapper.find('.upload-zone').trigger('drop', { dataTransfer: { files: [file] } })
    expect(wrapper.emitted('upload')?.[0]?.[0]).toEqual([file])
  })
})
```

### Step 5.2: 跑测试

Expected: 8 tests pass

### Step 5.3: 写实现

`DirectionPicker.vue`:
```vue
<script setup lang="ts">
import type { Direction } from '@/api/addCandidate'

const props = defineProps<{ modelValue: '' | Direction; hasOccupied: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', val: Direction): void }>()

const options: Array<{ value: Direction; icon: string; label: string; hint: string }> = [
  { value: 'pending', icon: '📥', label: '待分配', hint: '无需评分，直接进入' },
  { value: 'talent', icon: '📁', label: '人才库', hint: '无需评分，直接进入' },
  { value: 'position', icon: '🎯', label: '职位', hint: '需人岗匹配评分' },
]

function select(opt: Direction) {
  if (props.hasOccupied && opt !== 'pending') return
  emit('update:modelValue', opt)
}
</script>

<template>
  <div class="dir-opts">
    <div
      v-for="opt in options"
      :key="opt.value"
      :class="['dopt', { sel: modelValue === opt.value, off: hasOccupied && opt.value !== 'pending' }]"
      @click="select(opt.value)"
    >
      <div class="dicon">{{ opt.icon }}</div>
      <div class="dinfo">
        <div class="dlabel">{{ opt.label }}</div>
        <div class="dhint">{{ opt.hint }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dir-opts { display: flex; flex-direction: column; gap: 6px; }
.dopt {
  padding: 10px 14px;
  border: 2px solid var(--g3);
  border-radius: 12px;
  cursor: pointer;
  transition: 0.15s;
  background: #fff;
  display: flex;
  align-items: center;
  gap: 10px;
}
.dopt:hover:not(.off) { border-color: var(--p); }
.dopt.sel { border-color: var(--p); background: var(--pl); }
.dopt.off { opacity: 0.4; cursor: not-allowed; background: var(--g1); }
.dicon { font-size: 20px; flex-shrink: 0; }
.dinfo { flex: 1; }
.dlabel { font-weight: 600; font-size: 12px; }
.dhint { font-size: 10px; color: var(--g5); }
</style>
```

`UploadZone.vue`:
```vue
<script setup lang="ts">
const emit = defineEmits<{ (e: 'upload', files: File[]): void }>()

function handleClick() {
  emit('upload', [])  // parent handles file picker
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  ;(e.currentTarget as HTMLElement).classList.add('dragover')
}

function handleDragLeave(e: DragEvent) {
  ;(e.currentTarget as HTMLElement).classList.remove('dragover')
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  ;(e.currentTarget as HTMLElement).classList.remove('dragover')
  const files = Array.from(e.dataTransfer?.files || [])
  emit('upload', files)
}
</script>

<template>
  <div
    class="upload-zone"
    @click="handleClick"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
  >
    <div class="up-icon">📁</div>
    <div class="up-text">点击上传或拖拽简历文件到此处</div>
    <div class="up-hint">支持 PDF / Word / TXT，单文件不超过 10MB，支持批量上传</div>
    <div class="up-quick">
      <span @click.stop="emit('upload', [])">📄 选择文件</span>
      <span @click.stop="emit('upload', [])">📂 从人才库导入</span>
    </div>
  </div>
</template>

<style scoped>
.upload-zone {
  border: 2px dashed var(--g4);
  border-radius: 12px;
  padding: 32px 20px;
  text-align: center;
  cursor: pointer;
  transition: 0.15s;
  background: var(--g1);
}
.upload-zone:hover, .upload-zone.dragover { border-color: var(--p); background: var(--pl); }
.upload-zone.dragover { box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15); }
.up-icon { font-size: 36px; margin-bottom: 8px; transition: 0.2s; }
.upload-zone.dragover .up-icon { transform: scale(1.1); }
.up-text { font-size: 13px; font-weight: 500; color: var(--g7); }
.up-hint { font-size: 11px; color: var(--g5); margin-top: 4px; }
.up-quick { display: flex; gap: 8px; justify-content: center; margin-top: 12px; }
.up-quick span {
  font-size: 11px;
  padding: 4px 10px;
  background: #fff;
  border: 1px solid var(--g3);
  border-radius: 20px;
  color: var(--g6);
  cursor: pointer;
}
.up-quick span:hover { border-color: var(--p); color: var(--p); }
</style>
```

### Step 5.4: 跑测试

Expected: 8 tests pass

### Step 5.5: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/components/common/DirectionPicker.vue \
        ATS-New/web/app/src/components/common/UploadZone.vue \
        ATS-New/web/app/src/components/common/__tests__/DirectionPicker.test.ts \
        ATS-New/web/app/src/components/common/__tests__/UploadZone.test.ts
git commit -m "feat(add-candidate-frontend): 原语组件 - DirectionPicker + UploadZone"
```

---

## Task 6: 端到端验证

### Step 6.1: 跑全部原语组件测试

```bash
cd /Users/loki/ats-add-candidate-v2/ATS-New/web/app && npx vitest run src/components/common/ 2>&1 | tail -15
```
Expected: 36+ tests pass（5+5+7+8+8+8 = 41 across 10 components）

### Step 6.2: 跑全部前端测试看回归

```bash
npx vitest run 2>&1 | tail -10
```
Expected: 100+ tests pass, no regressions

### Step 6.3: Tag + Push

```bash
cd /Users/loki/ats-add-candidate-v2
git tag -d phase4-complete 2>/dev/null
git tag -a phase4-complete -m "Phase 4 完成: 10 原语组件 (StatusTag/CheckBanner/DuplicateInfoCard/OccupiedActions/ApplyPositionSelector/ScorePanel/ResumeCard/PositionChips/DirectionPicker/UploadZone)"
git push gitee feat/add-candidate-v2 --follow-tags
```

---

## 总时间预算

| Task | 工作量 |
|---|---|
| 1-5: 10 个原语组件 | ~3 天 |
| 6: 验证 | 0.5 天 |
| **合计** | **~3.5 天** |

---

## 执行选项

Two execution options:
1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task
2. **Inline Execution**

**Which approach?**