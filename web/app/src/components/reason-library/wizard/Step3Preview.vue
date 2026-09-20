<template>
  <div class="step3">
    <div class="step-intro">
      <n-icon :component="InformationCircleOutline" color="var(--brand)" :size="16" />
      <span>
        <b>{{ t('reasonLibrary.wizard.step3.title') }}</b>
        — {{ t('reasonLibrary.wizard.intro.step3') }}
      </span>
    </div>

    <div class="preview-wrap glass-card">
      <div class="preview-modal">
        <div class="pv-head">
          <h3>{{ previewTitle }}</h3>
          <div class="pv-count-row">
            <span class="req">{{ t('reasonLibrary.wizard.preview.requiredHint') }}</span>
            <span class="lbl">{{ t('reasonLibrary.wizard.preview.chooseReason') }}</span>
            <span class="lim">{{ t('reasonLibrary.wizard.preview.maxHint') }}</span>
          </div>
        </div>

        <div class="pv-body">
          <div class="pv-tbl-head">
            <span>{{ t('reasonLibrary.wizard.preview.colFactor') }}</span>
            <span>{{ t('reasonLibrary.wizard.preview.colCategory') }}</span>
            <span>{{ t('reasonLibrary.wizard.preview.colReasons') }}</span>
          </div>

          <div v-if="!previewTree.length" class="pv-empty">{{ t('reasonLibrary.wizard.preview.empty') }}</div>
          <template v-else>
            <div
              v-for="(g, gi) in previewTree"
              :key="g.id"
              class="pv-row"
              :class="{ merged: !g.isLeaf }"
              :style="!g.isLeaf ? { 'grid-template-rows': `repeat(${countSubRows(g)}, auto)` } : {}"
            >
              <div
                class="pv-cell l1"
                :class="['c-' + colorCycle[gi % colorCycle.length], { span2: g.isLeaf }]"
                :style="!g.isLeaf ? { 'grid-row': `1 / span ${countSubRows(g)}` } : {}"
              >
                {{ g.name }}
              </div>

              <template v-if="g.isLeaf">
                <div class="pv-chips">
                  <span v-for="tag in g.tags" :key="tag.id" class="pv-chip">
                    {{ tag.name }}
                    <n-icon v-if="tag.tip" :component="InformationCircleOutline" :size="9" class="tip-i" />
                  </span>
                  <template v-if="g.allowCustom">
                    <input
                      v-if="editingOther[g.id]"
                      v-focus
                      class="pv-other-input"
                      :value="otherInputs[g.id] || ''"
                      :placeholder="t('reasonLibrary.wizard.preview.otherPlaceholder')"
                      @input="(e: any) => onOtherInput(g.id, (e.target as HTMLInputElement).value)"
                      @keydown.enter="commitOther(g.id)"
                      @blur="commitOther(g.id)"
                    />
                    <span
                      v-else-if="otherInputs[g.id]"
                      class="pv-chip other-filled"
                      @click="editOtherAgain(g.id)"
                    >{{ otherInputs[g.id] }}</span>
                    <span v-else class="pv-chip other" @click="onOtherClick(g.id)">{{ t('reasonLibrary.wizard.preview.other') }}</span>
                  </template>
                </div>
              </template>

              <template v-else>
                <template v-for="sub in g.children" :key="sub.id">
                  <template v-if="sub.isLeaf">
                    <div :class="['pv-cell', 'c-' + colorCycle[gi % colorCycle.length]]">{{ sub.name }}</div>
                    <div class="pv-chips">
                      <span v-for="tag in sub.tags" :key="tag.id" class="pv-chip">
                        {{ tag.name }}
                        <n-icon v-if="tag.tip" :component="InformationCircleOutline" :size="9" class="tip-i" />
                      </span>
                      <template v-if="sub.allowCustom">
                        <input
                          v-if="editingOther[sub.id]"
                          v-focus
                          class="pv-other-input"
                          :value="otherInputs[sub.id] || ''"
                          :placeholder="t('reasonLibrary.wizard.preview.otherPlaceholder')"
                          @input="(e: any) => onOtherInput(sub.id, (e.target as HTMLInputElement).value)"
                          @keydown.enter="commitOther(sub.id)"
                          @blur="commitOther(sub.id)"
                        />
                        <span
                          v-else-if="otherInputs[sub.id]"
                          class="pv-chip other-filled"
                          @click="editOtherAgain(sub.id)"
                        >{{ otherInputs[sub.id] }}</span>
                        <span v-else class="pv-chip other" @click="onOtherClick(sub.id)">{{ t('reasonLibrary.wizard.preview.other') }}</span>
                      </template>
                    </div>
                  </template>
                  <template v-else>
                    <div :class="['pv-cell', 'c-' + colorCycle[gi % colorCycle.length]]">{{ sub.name }}</div>
                    <div>
                      <div v-for="l3 in sub.children.filter((x: any) => x.tags?.length)" :key="l3.id" class="pv-l3-group">
                        <div class="pv-l3-title">{{ l3.name }}</div>
                        <div class="pv-chips">
                          <span v-for="tag in l3.tags" :key="tag.id" class="pv-chip">
                            {{ tag.name }}
                            <n-icon v-if="tag.tip" :component="InformationCircleOutline" :size="9" class="tip-i" />
                          </span>
                          <template v-if="l3.allowCustom">
                            <input
                              v-if="editingOther[l3.id]"
                              v-focus
                              class="pv-other-input"
                              :value="otherInputs[l3.id] || ''"
                              :placeholder="t('reasonLibrary.wizard.preview.otherPlaceholder')"
                              @input="(e: any) => onOtherInput(l3.id, (e.target as HTMLInputElement).value)"
                              @keydown.enter="commitOther(l3.id)"
                              @blur="commitOther(l3.id)"
                            />
                            <span
                              v-else-if="otherInputs[l3.id]"
                              class="pv-chip other-filled"
                              @click="editOtherAgain(l3.id)"
                            >{{ otherInputs[l3.id] }}</span>
                            <span v-else class="pv-chip other" @click="onOtherClick(l3.id)">{{ t('reasonLibrary.wizard.preview.other') }}</span>
                          </template>
                        </div>
                      </div>
                    </div>
                  </template>
                </template>
              </template>
            </div>
          </template>
        </div>

        <div class="pv-foot">
          <button class="pv-btn">{{ t('reasonLibrary.common.cancel') }}</button>
          <button class="pv-btn primary">{{ t('reasonLibrary.common.confirm') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Step3Preview (T-18)
 * - 模拟业务方弹窗预览 (与原型 §第六步完全对齐)
 * - 三列 grid (88px 108px 1fr) + 5 色循环 (blue/green/purple/orange/gray)
 * - 每张 L1 大类一行; 末级直接展示 tags chip; 非末级递归展开为 L2 + L3
 * - "其他" chip 在 allowCustom=true 的末级显示
 *
 * 数据来源: wizard.categories + wizard.scenes
 * 仅读 (UI 模拟, 不修改 wizard)
 */
import { computed, reactive, ref } from 'vue'
import { NIcon } from 'naive-ui'
import { InformationCircleOutline } from '@vicons/ionicons5'
import type { ReasonTag, RuleCategory, WizardPayload } from '../../../types/reason-library'
import { t } from '../../../locales/zh-CN'

const props = defineProps<{
  wizard: WizardPayload
  allTags: ReasonTag[]
}>()

// 5 色循环 (与原型 .c-blue/green/purple/orange/gray 对齐)
const colorCycle = ['blue', 'green', 'purple', 'orange', 'gray']

const previewTitle = computed(() => {
  const scene = props.wizard.scenes[0]
  if (!scene) return t('reasonLibrary.wizard.preview.sceneMissing')
  return t('reasonLibrary.wizard.preview.sceneHeader', { scene }).replace('{scene}', scene)
})

interface PreviewNode {
  id: string
  name: string
  isLeaf: boolean
  tags: ReasonTag[]
  allowCustom: boolean
  children: PreviewNode[]
}

/** 构造预览树: 过滤掉无 tag 的空末级 */
const previewTree = computed<PreviewNode[]>(() => {
  const cats = props.wizard.categories
  const childMap = new Map<string, RuleCategory[]>()
  cats.forEach((c) => {
    const pid = c.parentId || ''
    if (!childMap.has(pid)) childMap.set(pid, [])
    childMap.get(pid)!.push(c)
  })
  const tagById = new Map(props.allTags.map((t) => [t.id, t]))

  function walk(c: RuleCategory): PreviewNode | null {
    const children = (childMap.get(c.id) || []).sort((a, b) => a.order - b.order)
    if (children.length === 0) {
      const tags = (c.tags || [])
        .map((t) => tagById.get(t.id))
        .filter((t): t is ReasonTag => !!t)
      if (tags.length === 0) return null
      return { id: c.id, name: c.name, isLeaf: true, tags, allowCustom: c.allowCustom, children: [] }
    }
    const subNodes = children.map(walk).filter((n): n is PreviewNode => !!n)
    if (subNodes.length === 0) return null
    return {
      id: c.id,
      name: c.name,
      isLeaf: false,
      tags: [],
      allowCustom: c.allowCustom,
      children: subNodes,
    }
  }

  return (childMap.get('') || [])
    .sort((a, b) => a.order - b.order)
    .map(walk)
    .filter((n): n is PreviewNode => !!n)
})

/** 计算某 L1 下有多少"行" (用于 grid-row 跨行) */
function countSubRows(node: PreviewNode): number {
  if (node.isLeaf) return 1
  return node.children.length
}

// ============= Item5: 末级「其他」自定义输入 =============
// 任意层级(L1/L2/L3)的末级分类, 若 allowCustom=true, 点击「其他」展开输入框由用户输入
const editingOther = reactive<Record<string, boolean>>({})
const otherInputs = reactive<Record<string, string>>({})

function onOtherClick(id: string) {
  editingOther[id] = true
}
function onOtherInput(id: string, val: string) {
  otherInputs[id] = val
}
function commitOther(id: string) {
  const v = (otherInputs[id] ?? '').trim()
  if (!v) otherInputs[id] = ''
  editingOther[id] = false
}
function editOtherAgain(id: string) {
  editingOther[id] = true
}

// 进入编辑态时自动聚焦输入框
const vFocus = {
  mounted: (el: HTMLElement) => el.focus(),
}
</script>

<style scoped>
.step3 { display: flex; flex-direction: column; gap: var(--space-3); }

.step-intro {
  display: flex;
  gap: var(--space-2);
  align-items: flex-start;
  padding: var(--space-2) var(--space-3);
  background: var(--brand-soft);
  border-radius: var(--radius-md);
  font-size: var(--fs-12);
  color: var(--ink-soft);
  line-height: 1.6;
}
.step-intro b { color: var(--brand); font-weight: 600; }

/* === 预览容器 === */
.preview-wrap {
  background: linear-gradient(180deg, var(--g1), transparent);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  display: flex;
  justify-content: center;
}

.preview-modal {
  background: #fff;
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 720px;
  box-shadow: 0 12px 40px rgba(15, 20, 40, .12);
  overflow: hidden;
  border: 1px solid var(--border-hairline);
}

.pv-head { padding: var(--space-3) var(--space-4) 0; }
.pv-head h3 { margin: 0 0 var(--space-1); font-size: var(--fs-15); font-weight: 600; color: var(--ink); }
.pv-count-row { display: flex; align-items: baseline; margin-top: var(--space-2); }
.pv-count-row .req { color: var(--c-error); margin-right: 4px; font-size: var(--fs-13); }
.pv-count-row .lbl { font-size: var(--fs-13); font-weight: 600; }
.pv-count-row .lim {
  margin-left: auto;
  font-size: var(--fs-12);
  color: #f5a623;
}
.pv-count-row .lim b { color: var(--c-error); }

.pv-body { padding: var(--space-2) var(--space-4) var(--space-1); max-height: 380px; overflow-y: auto; }

.pv-tbl-head {
  display: grid;
  grid-template-columns: 88px 108px 1fr;
  gap: 10px;
  background: var(--g1);
  border-radius: var(--radius-sm);
  padding: 7px 11px;
  font-size: var(--fs-11);
  font-weight: 600;
  color: var(--ink-soft);
  margin-bottom: var(--space-2);
  position: sticky;
  top: 0;
  z-index: 2;
}

.pv-row {
  display: grid;
  grid-template-columns: 88px 108px 1fr;
  gap: 10px;
  margin-bottom: 10px;
}
.pv-row.merged { margin-bottom: 10px; }

.pv-cell {
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 9px 8px;
  font-size: var(--fs-12);
  font-weight: 600;
  text-align: center;
  line-height: 1.5;
  word-break: break-all;
  align-self: stretch;
}
.pv-cell.l1 { min-height: 46px; }
.pv-cell.l1.span2 { grid-column: 1 / 3; }

/* === 5 色循环 (与原型对齐) === */
.c-blue { background: var(--brand-soft); color: var(--brand); }
.c-green { background: var(--c-success-soft); color: var(--c-success-deep); }
.c-purple { background: rgba(139, 92, 246, .12); color: #6d28d9; }
.c-orange { background: var(--brand-warm-soft); color: var(--brand-warm-deep); }
.c-gray { background: var(--g1); color: var(--ink-soft); }

.pv-chips { display: flex; flex-wrap: wrap; gap: 6px; align-content: flex-start; }
.pv-chip {
  border: 1px solid var(--border-hairline);
  border-radius: 7px;
  background: #fff;
  color: var(--ink-soft);
  font-size: var(--fs-11);
  padding: 4px 11px;
  line-height: 1.4;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.pv-chip .tip-i { font-size: 9px; margin-left: 2px; opacity: .55; }
.pv-chip.other { cursor: pointer; border-style: dashed; color: var(--brand); border-color: var(--brand); }
.pv-chip.other:hover { background: rgba(54, 110, 235, .08); }
.pv-chip.other-filled { background: rgba(54, 110, 235, .1); border-color: var(--brand); color: var(--brand); }
.pv-other-input {
  border: 1px solid var(--brand);
  border-radius: 7px;
  font-size: var(--fs-11);
  padding: 4px 10px;
  line-height: 1.4;
  width: 120px;
  outline: none;
  color: var(--ink);
  background: #fff;
}
.pv-other-input:focus { box-shadow: 0 0 0 2px rgba(54, 110, 235, .18); }

.pv-l3-title {
  font-size: var(--fs-11);
  font-weight: 600;
  color: var(--ink-soft);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 5px;
}
.pv-l3-title::before {
  content: '';
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  opacity: .5;
}
.pv-l3-group + .pv-l3-group {
  margin-top: 8px;
  padding-top: 7px;
  border-top: 1px dashed var(--border-hairline);
}

.pv-empty {
  padding: 40px;
  text-align: center;
  color: var(--ink-faint);
  font-size: var(--fs-13);
}

.pv-foot {
  padding: var(--space-2) var(--space-4) var(--space-3);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid var(--border-hairline);
  margin-top: var(--space-2);
}
.pv-btn {
  border-radius: var(--radius-sm);
  font-size: var(--fs-12);
  font-weight: 500;
  padding: 0 20px;
  line-height: 32px;
  cursor: pointer;
  border: 1px solid var(--border-hairline);
  background: #fff;
  color: var(--ink-soft);
}
.pv-btn.primary {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}
</style>
