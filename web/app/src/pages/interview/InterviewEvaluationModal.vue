<script lang="ts">
export type RecValue = 'PASS' | 'MANAGER' | 'DISCUSS' | 'FAIL'
export interface DimItem { key: string; name: string; desc?: string; score: number }
export interface EvalGroup { key: string; title: string; hint?: string; items: DimItem[] }
export interface Candidate { name: string; position: string; department: string; round: string; date: string; interviewer: string }
export interface Evaluation { candidate: Candidate; overallScore: number; groups: EvalGroup[]; recommendation: RecValue; comment: string }
</script>

<script setup lang="ts">
/**
 * 面试评价弹窗（设计稿 · Liquid Glass v2）
 * -------------------------------------------------------------
 * 三态：
 *   - mode="view"  只读查看（候选人画像 + 维度评分 + 评语 + 推荐结论）
 *   - mode="edit"  填写评价（1-5 分段评分 + 推荐结论 + 评语，可提交）
 * 数据约定对齐后端 InterviewEvaluation：
 *   scores(JSON) / overall_score / recommendation / comment
 * 当前为设计态：内置 demo 数据，submit 仅 emit 不落库；
 * 接入时把 demo 换成 props.evaluation 并接 api/interview 的 evaluation 接口即可。
 */
import { ref, computed, watch } from 'vue'
import { NModal, NButton, NTag, NSpace, NInput, NDivider, useMessage } from 'naive-ui'

const props = withDefaults(defineProps<{
  show?: boolean
  mode?: 'view' | 'edit'
  evaluation?: Evaluation
}>(), {
  show: false,
  mode: 'view',
  evaluation: undefined,
})

const emit = defineEmits<{
  'update:show': [boolean]
  submit: [payload: { scores: Record<string, number>; overallScore: number; recommendation: RecValue; comment: string }]
}>()

const message = useMessage()

/* ---------- demo 数据（对齐截图「杨前」评价） ---------- */
const DEMO: Evaluation = {
  candidate: {
    name: '杨前', position: '前端开发工程师', department: '微信事业群',
    round: '一面', date: '2026-08-28 14:00', interviewer: '张工',
  },
  overallScore: 3.0,
  groups: [
    {
      key: 'siwei', title: '四唯契合性', hint: '岗位胜任力底层结构',
      items: [
        { key: 'laodongzhe', name: '劳动者', desc: '专业能力与成长潜力', score: 4 },
        { key: 'laodonggongju', name: '劳动工具', desc: '技术栈熟练度', score: 4 },
        { key: 'laodongziliao', name: '劳动资料', desc: '知识资产沉淀', score: 5 },
        { key: 'laodongduixiang', name: '劳动对象', desc: '业务理解深度', score: 3 },
      ],
    },
    {
      key: 'wuli', title: '五力价值观', hint: '腾讯价值观行为锚定',
      items: [
        { key: 'zunzhongshishi', name: '尊重事实', desc: '基于数据理性决策', score: 5 },
        { key: 'ziwopipan', name: '自我批判', desc: '复盘与持续改进', score: 4 },
        { key: 'zhiji', name: '积极主动', desc: 'owner 意识', score: 4 },
        { key: 'renzefuke', name: '认真负责', desc: '结果交付靠谱度', score: 5 },
        { key: 'jiankufendou', name: '艰苦奋斗', desc: '攻坚韧性', score: 3 },
      ],
    },
  ],
  recommendation: 'PASS',
  comment: '候选人技术基础扎实，React/Vue 双栈均有生产经验；沟通表达清晰，自我复盘意识强。业务理解（劳动对象）偏弱，建议二面重点考察。',
}

const REC_OPTIONS: { value: RecValue; label: string; type: 'success' | 'info' | 'warning' | 'error' }[] = [
  { value: 'PASS', label: '通过', type: 'success' },
  { value: 'MANAGER', label: '经理', type: 'info' },
  { value: 'DISCUSS', label: '面议', type: 'warning' },
  { value: 'FAIL', label: '不通过', type: 'error' },
]

/* ---------- 状态 ---------- */
const source = computed(() => props.evaluation ?? DEMO)
const editing = ref(props.mode === 'edit')
const draft = ref<EvalGroup[]>([])
const draftComment = ref('')
const draftRec = ref<RecValue>('PASS')

function loadDraft() {
  draft.value = JSON.parse(JSON.stringify(source.value.groups))
  draftComment.value = source.value.comment
  draftRec.value = source.value.recommendation
}
watch(() => [props.show, props.mode], () => {
  if (props.show) {
    editing.value = props.mode === 'edit'
    if (editing.value) loadDraft()
  }
}, { immediate: true })

/* ---------- 计算 ---------- */
const avgScore = computed(() => {
  const all = draft.value.flatMap(g => g.items.map(i => i.score))
  if (!all.length) return source.value.overallScore
  return Math.round((all.reduce((a, b) => a + b, 0) / all.length) * 10) / 10
})
const gaugeOffset = computed(() => {
  const C = 2 * Math.PI * 52
  const v = (editing.value ? avgScore.value : source.value.overallScore) / 5
  return C * (1 - v)
})
function scoreColor(s: number) {
  if (s >= 4) return 'var(--c-success)'
  if (s >= 3) return 'var(--c-warning)'
  return 'var(--c-error)'
}
function recMeta(v: RecValue) {
  return REC_OPTIONS.find(r => r.value === v)!
}
const canSubmit = computed(() => draft.value.some(g => g.items.some(i => i.score > 0)))

/* ---------- 交互 ---------- */
function setScore(gIdx: number, iIdx: number, val: number) {
  const cur = draft.value[gIdx].items[iIdx].score
  draft.value[gIdx].items[iIdx].score = cur === val ? 0 : val
}
function pickRec(v: RecValue) { draftRec.value = v }

function handleSubmit() {
  if (!canSubmit.value) { message.warning('请至少完成一项维度评分'); return }
  const scores: Record<string, number> = {}
  draft.value.forEach(g => g.items.forEach(i => { scores[i.key] = i.score }))
  emit('submit', {
    scores,
    overallScore: avgScore.value,
    recommendation: draftRec.value,
    comment: draftComment.value,
  })
  message.success('评价已提交（设计态·未落库）')
  editing.value = false
}
function close() { emit('update:show', false) }
function startEdit() { loadDraft(); editing.value = true }
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    :bordered="false"
    style="width: 880px; max-width: 94vw;"
    :title="editing ? '填写面试评价' : '面试评价'"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <!-- ================= 查看态 ================= -->
    <div v-if="!editing" class="ats-eval">
      <div class="ats-eval__layout">
        <!-- 左：候选人画像 + 综合评分 -->
        <aside class="ats-rail glass-card">
          <div class="ats-avatar">{{ source.candidate.name.slice(0, 1) }}</div>
          <div class="ats-name">{{ source.candidate.name }}</div>
          <div class="ats-sub">{{ source.candidate.position }}</div>
          <n-divider style="margin: 14px 0;" />
          <div class="ats-gauge">
            <svg viewBox="0 0 120 120" class="ats-gauge__svg">
              <circle cx="60" cy="60" r="52" class="ats-gauge__track" />
              <circle
                cx="60" cy="60" r="52"
                class="ats-gauge__fill"
                :stroke="scoreColor(source.overallScore)"
                :stroke-dashoffset="gaugeOffset"
              />
            </svg>
            <div class="ats-gauge__center">
              <div class="ats-gauge__num" :style="{ color: scoreColor(source.overallScore) }">
                {{ source.overallScore.toFixed(1) }}
              </div>
              <div class="ats-gauge__cap">综合评分</div>
            </div>
          </div>
          <div class="ats-rec">
            <span class="ats-rec__label">最终推荐</span>
            <n-tag :type="recMeta(source.recommendation).type" :bordered="false" round size="large">
              {{ recMeta(source.recommendation).label }}
            </n-tag>
          </div>
          <ul class="ats-meta">
            <li><span>轮次</span><b>{{ source.candidate.round }}</b></li>
            <li><span>部门</span><b>{{ source.candidate.department }}</b></li>
            <li><span>时间</span><b>{{ source.candidate.date }}</b></li>
            <li><span>面试官</span><b>{{ source.candidate.interviewer }}</b></li>
          </ul>
        </aside>

        <!-- 右：维度评分 + 评语 -->
        <section class="ats-detail">
          <div v-for="group in source.groups" :key="group.key" class="ats-group">
            <div class="ats-group__head">
              <span class="ats-group__bar" />
              <div>
                <div class="ats-group__title">{{ group.title }}</div>
                <div v-if="group.hint" class="ats-group__hint">{{ group.hint }}</div>
              </div>
            </div>
            <div
              v-for="item in group.items"
              :key="item.key"
              class="ats-dim"
            >
              <div class="ats-dim__info">
                <span class="ats-dim__name">{{ item.name }}</span>
                <span v-if="item.desc" class="ats-dim__desc">{{ item.desc }}</span>
              </div>
              <div class="ats-dim__rating">
                <span
                  v-for="n in 5"
                  :key="n"
                  class="ats-dot"
                  :class="{ 'is-on': n <= item.score }"
                  :style="n <= item.score ? { background: scoreColor(item.score) } : {}"
                />
                <span class="ats-dim__score" :style="{ color: scoreColor(item.score) }">
                  {{ item.score }}<i>/5</i>
                </span>
              </div>
            </div>
          </div>

          <div class="ats-comment">
            <div class="ats-comment__label">评语</div>
            <p class="ats-comment__text">{{ source.comment }}</p>
          </div>
        </section>
      </div>
    </div>

    <!-- ================= 编辑态 ================= -->
    <div v-else class="ats-eval">
      <div class="ats-eval__layout">
        <aside class="ats-rail glass-card">
          <div class="ats-avatar">{{ source.candidate.name.slice(0, 1) }}</div>
          <div class="ats-name">{{ source.candidate.name }}</div>
          <div class="ats-sub">{{ source.candidate.position }} · {{ source.candidate.round }}</div>
          <n-divider style="margin: 14px 0;" />
          <div class="ats-gauge">
            <svg viewBox="0 0 120 120" class="ats-gauge__svg">
              <circle cx="60" cy="60" r="52" class="ats-gauge__track" />
              <circle
                cx="60" cy="60" r="52"
                class="ats-gauge__fill"
                :stroke="scoreColor(avgScore)"
                :stroke-dashoffset="gaugeOffset"
              />
            </svg>
            <div class="ats-gauge__center">
              <div class="ats-gauge__num" :style="{ color: scoreColor(avgScore) }">
                {{ avgScore.toFixed(1) }}
              </div>
              <div class="ats-gauge__cap">实时均分</div>
            </div>
          </div>
          <div class="ats-rec">
            <span class="ats-rec__label">最终推荐</span>
            <div class="ats-rec__chips">
              <button
                v-for="opt in REC_OPTIONS"
                :key="opt.value"
                type="button"
                class="ats-chip"
                :class="['is-' + opt.type, { 'is-active': draftRec === opt.value }]"
                @click="pickRec(opt.value)"
              >
{{ opt.label }}
</button>
            </div>
          </div>
        </aside>

        <section class="ats-detail">
          <div v-for="(group, gi) in draft" :key="group.key" class="ats-group">
            <div class="ats-group__head">
              <span class="ats-group__bar" />
              <div>
                <div class="ats-group__title">{{ group.title }}</div>
                <div v-if="group.hint" class="ats-group__hint">{{ group.hint }}</div>
              </div>
            </div>
            <div
              v-for="(item, ii) in group.items"
              :key="item.key"
              class="ats-dim ats-dim--edit"
            >
              <div class="ats-dim__info">
                <span class="ats-dim__name">{{ item.name }}</span>
                <span v-if="item.desc" class="ats-dim__desc">{{ item.desc }}</span>
              </div>
              <div class="ats-seg">
                <button
                  v-for="n in 5"
                  :key="n"
                  type="button"
                  class="ats-seg__btn"
                  :class="{ 'is-on': n <= item.score }"
                  :style="n <= item.score ? { background: scoreColor(item.score), borderColor: scoreColor(item.score) } : {}"
                  @click="setScore(gi, ii, n)"
                >
{{ n }}
</button>
              </div>
            </div>
          </div>

          <div class="ats-comment ats-comment--edit">
            <div class="ats-comment__label">评语</div>
            <n-input
              v-model:value="draftComment"
              type="textarea"
              :rows="4"
              placeholder="技术能力、沟通、综合素质、风险点…"
            />
          </div>
        </section>
      </div>
    </div>

    <template #footer>
      <n-space justify="end">
        <template v-if="!editing">
          <n-button @click="close">关闭</n-button>
          <n-button type="primary" @click="startEdit">编辑评价</n-button>
        </template>
        <template v-else>
          <n-button @click="close">取消</n-button>
          <n-button type="primary" :disabled="!canSubmit" @click="handleSubmit">提交评价</n-button>
        </template>
      </n-space>
    </template>
  </n-modal>
</template>

<style scoped>
/* ===== 布局 ===== */
.ats-eval__layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: var(--space-4);
  align-items: start;
}
@media (max-width: 720px) {
  .ats-eval__layout { grid-template-columns: 1fr; }
}

/* ===== 左栏 rail ===== */
.ats-rail {
  position: sticky;
  top: 0;
  padding: var(--space-4);
  text-align: center;
}
.ats-avatar {
  width: 64px; height: 64px; margin: 0 auto var(--space-3);
  border-radius: var(--radius-pill);
  display: grid; place-items: center;
  font-size: 26px; font-weight: 700; color: #fff;
  background: linear-gradient(135deg, var(--brand), var(--brand-grad-a));
  box-shadow: 0 6px 18px var(--brand-a22);
}
.ats-name { font-size: var(--text-h4); font-weight: 700; color: var(--ink); }
.ats-sub { font-size: var(--text-meta); color: var(--ink-faint); margin-top: 2px; }

.ats-gauge { position: relative; width: 140px; height: 140px; margin: var(--space-2) auto; }
.ats-gauge__svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.ats-gauge__track { fill: none; stroke: var(--g1); stroke-width: 10; }
.ats-gauge__fill {
  fill: none; stroke-width: 10; stroke-linecap: round;
  stroke-dasharray: 326.7;
  transition: stroke-dashoffset var(--duration-slow) var(--ease-out), stroke var(--duration-base);
}
.ats-gauge__center {
  position: absolute; inset: 0; display: grid; place-content: center; text-align: center;
}
.ats-gauge__num { font-size: 32px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.ats-gauge__cap { font-size: var(--text-meta); color: var(--ink-faint); margin-top: 2px; }

.ats-rec { margin-top: var(--space-3); display: grid; gap: var(--space-2); justify-items: center; }
.ats-rec__label { font-size: var(--text-meta); color: var(--ink-faint); }
.ats-rec__chips { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.ats-chip {
  border: 1px solid var(--border-hairline);
  background: var(--glass-bg-input);
  color: var(--ink-soft);
  border-radius: var(--radius-pill);
  padding: 5px 14px; font-size: var(--text-small); cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}
.ats-chip.is-active.is-success { background: var(--c-success-soft); color: var(--c-success); border-color: var(--c-success); }
.ats-chip.is-active.is-info { background: var(--c-info-soft); color: var(--c-info); border-color: var(--c-info); }
.ats-chip.is-active.is-warning { background: var(--c-warning-soft); color: var(--c-warning); border-color: var(--c-warning); }
.ats-chip.is-active.is-error { background: var(--c-error-soft); color: var(--c-error); border-color: var(--c-error); }
.ats-chip:hover { border-color: var(--brand); color: var(--brand); }

.ats-meta { list-style: none; margin: var(--space-4) 0 0; padding: 0; text-align: left; display: grid; gap: var(--space-2); }
.ats-meta li { display: flex; justify-content: space-between; font-size: var(--text-small); }
.ats-meta span { color: var(--ink-faint); }
.ats-meta b { color: var(--ink); font-weight: 600; }

/* ===== 右栏 detail ===== */
.ats-group { margin-bottom: var(--space-4); }
.ats-group__head { display: flex; align-items: center; gap: 10px; margin-bottom: var(--space-3); }
.ats-group__bar { width: 4px; height: 18px; border-radius: var(--radius-pill); background: linear-gradient(var(--brand), var(--brand-grad-a)); }
.ats-group__title { font-size: var(--text-body); font-weight: 700; color: var(--ink); }
.ats-group__hint { font-size: var(--text-meta); color: var(--ink-faint); margin-top: 1px; }

.ats-dim {
  display: flex; align-items: center; justify-content: space-between; gap: var(--space-3);
  padding: 10px 0; border-bottom: 1px dashed var(--border-hairline);
}
.ats-dim:last-child { border-bottom: none; }
.ats-dim__info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ats-dim__name { font-size: var(--text-small); font-weight: 600; color: var(--ink); }
.ats-dim__desc { font-size: var(--text-meta); color: var(--ink-faint); }

.ats-dim__rating { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.ats-dot { width: 10px; height: 10px; border-radius: var(--radius-pill); background: var(--g2); transition: background var(--duration-fast); }
.ats-dim__score { font-size: var(--text-small); font-weight: 700; font-variant-numeric: tabular-nums; margin-left: var(--space-1); min-width: 34px; text-align: right; }
.ats-dim__score i { font-style: normal; font-size: var(--text-meta); color: var(--ink-faint); font-weight: 400; }

/* 编辑态分段评分 */
.ats-seg { display: flex; gap: 6px; }
.ats-seg__btn {
  width: 34px; height: 34px; border-radius: var(--radius-md);
  border: 1px solid var(--border-hairline);
  background: var(--glass-bg-input);
  color: var(--ink-soft); font-size: var(--text-small); font-weight: 600; cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}
.ats-seg__btn:hover { border-color: var(--brand); transform: translateY(-1px); }
.ats-seg__btn.is-on { color: #fff; box-shadow: 0 4px 12px var(--brand-a22); }

/* 评语 */
.ats-comment { margin-top: var(--space-4); }
.ats-comment__label { font-size: var(--text-meta); color: var(--ink-faint); margin-bottom: 6px; font-weight: 600; }
.ats-comment__text {
  margin: 0; padding: var(--space-3); border-radius: var(--radius-md);
  background: var(--glass-bg-input); border: 1px solid var(--border-hairline);
  font-size: var(--text-small); line-height: 1.7; color: var(--ink-soft);
}
</style>
