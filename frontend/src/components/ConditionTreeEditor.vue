<!--
  条件树形编辑器 - 3 级嵌套 AND/OR (PRD #5.4)
  - 最多 3 级嵌套
  - 根条件可添加同级
  - 子条件可指定 AND/OR 关系
  - 内置字段枚举 (候选人字段 / 阶段状态)
  - 字段操作符下拉
-->
<template>
  <div class="condition-tree-editor">
    <div v-for="(item, idx) in items" :key="item.id || idx" class="tree-item">
      <!-- 条件节点 -->
      <div class="node-row">
        <n-select
          v-model:value="item.relationToParent"
          :options="relationOptions"
          size="small"
          style="width: 100px"
          v-if="item.parentId"
        />
        <n-tag v-else type="primary" size="small">根</n-tag>

        <n-select
          v-model:value="item.field"
          :options="fieldOptions"
          size="small"
          placeholder="字段"
          style="width: 180px"
          filterable
          @update:value="(v) => onFieldChange(item, v)"
        />

        <n-select
          v-model:value="item.operator"
          :options="getOperatorOptions(item.field)"
          size="small"
          placeholder="运算符"
          style="width: 160px"
        />

        <n-input
          v-if="needsSingleValue(item.operator)"
          v-model:value="item.value"
          size="small"
          placeholder="值"
          style="width: 140px"
        />
        <n-input
          v-else-if="needsArrayValue(item.operator)"
          v-model:value="item.value"
          size="small"
          placeholder="值(逗号分隔)"
          style="width: 200px"
        />
        <n-input-number
          v-else-if="needsNumberValue(item.operator)"
          v-model:value="item.value"
          size="small"
          placeholder="值"
          style="width: 120px"
        />

        <n-button text size="small" type="error" @click="removeItem(item)" :disabled="!canRemove">
          删除
        </n-button>
      </div>

      <!-- 阶段状态字段时需要选关联的 stageId -->
      <div v-if="item.field === 'STAGE_STATUS'" class="ref-stage-row">
        <n-text depth="3" size="small">关联阶段：</n-text>
        <n-select
          v-model:value="item.refStageId"
          :options="allStages"
          size="small"
          placeholder="选择要检查状态的阶段"
          style="width: 240px"
        />
        <n-input
          v-model:value="item.value"
          size="small"
          placeholder="状态值, 如 PASS / FAIL / PENDING"
          style="width: 220px"
        />
      </div>

      <!-- 子条件 -->
      <div v-if="item.children && item.children.length > 0" class="children">
        <ConditionTreeEditor
          :items="item.children"
          :all-stages="allStages"
          :depth="(depth || 0) + 1"
        />
      </div>

      <!-- 添加子条件按钮 (限 3 级) -->
      <div v-if="(depth || 0) < 2" class="add-child-row">
        <n-button text size="small" type="primary" @click="addChild(item)">
          + 添加子条件
        </n-button>
      </div>
    </div>

    <div class="add-root-row">
      <n-button size="small" type="primary" dashed @click="addRoot">
        + 添加根条件
      </n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { NButton, NTag, NInput, NInputNumber, NSelect, NText } from 'naive-ui'
import { useMessage } from 'naive-ui'

const props = defineProps<{
  modelValue: any[]
  allStages: { label: string; value: string }[]
  allLinkIds: string[]
  depth?: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: any[]): void
}>()

const message = useMessage()
const items = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

// 兄弟项 / 父子项互斥规则
const canRemove = computed(() => items.value.length > 1 || (props.depth || 0) > 0)

const relationOptions = [
  { label: 'AND', value: 'AND' },
  { label: 'OR', value: 'OR' },
]

const fieldOptions = [
  { label: '候选人 - 年龄', value: 'AGE' },
  { label: '候选人 - 性别', value: 'GENDER' },
  { label: '候选人 - 婚育情况', value: 'MARRIAGE' },
  { label: '候选人 - 最高学历', value: 'HIGHEST_EDU' },
  { label: '候选人 - 第一学历', value: 'FIRST_EDU' },
  { label: '候选人 - 职级', value: 'LEVEL' },
  { label: '候选人 - 职务', value: 'JOB' },
  { label: '候选人 - 任职公司', value: 'COMPANY' },
  { label: '候选人 - 简历来源', value: 'RESUME_SOURCE' },
  { label: '候选人 - 简历渠道', value: 'RESUME_CHANNEL' },
  { label: '阶段状态', value: 'STAGE_STATUS' },
]

// 各字段的可用运算符
const FIELD_OPERATORS: Record<string, any[]> = {
  AGE: [
    { label: '>', value: 'GT' },
    { label: '>=', value: 'GTE' },
    { label: '=', value: 'EQ' },
    { label: '<', value: 'LT' },
    { label: '<=', value: 'LTE' },
    { label: '为空', value: 'EMPTY' },
    { label: '不为空', value: 'NOT_EMPTY' },
  ],
  GENDER: [
    { label: '=', value: 'EQ' },
    { label: '包含', value: 'IN' },
    { label: '为空', value: 'EMPTY' },
  ],
  MARRIAGE: [
    { label: '=', value: 'EQ' },
    { label: '包含', value: 'IN' },
    { label: '为空', value: 'EMPTY' },
  ],
  HIGHEST_EDU: [
    { label: '包含', value: 'CONTAINS' },
    { label: '不包含', value: 'NOT_CONTAINS' },
    { label: '为空', value: 'EMPTY' },
  ],
  FIRST_EDU: [
    { label: '包含', value: 'CONTAINS' },
    { label: '不包含', value: 'NOT_CONTAINS' },
    { label: '为空', value: 'EMPTY' },
  ],
  LEVEL: [
    { label: '包含', value: 'CONTAINS' },
    { label: '不包含', value: 'NOT_CONTAINS' },
    { label: '为空', value: 'EMPTY' },
  ],
  JOB: [
    { label: '包含', value: 'CONTAINS' },
    { label: '不包含', value: 'NOT_CONTAINS' },
    { label: '为空', value: 'EMPTY' },
  ],
  COMPANY: [
    { label: '包含', value: 'CONTAINS' },
    { label: '不包含', value: 'NOT_CONTAINS' },
    { label: '为空', value: 'EMPTY' },
  ],
  RESUME_SOURCE: [
    { label: '包含', value: 'CONTAINS' },
    { label: '不包含', value: 'NOT_CONTAINS' },
  ],
  RESUME_CHANNEL: [
    { label: '包含', value: 'CONTAINS' },
    { label: '不包含', value: 'NOT_CONTAINS' },
  ],
  STAGE_STATUS: [
    { label: '=', value: 'EQ' },
    { label: '包含', value: 'IN' },
    { label: '为空', value: 'EMPTY' },
  ],
}

function getOperatorOptions(field: string) {
  return FIELD_OPERATORS[field] || []
}

function needsSingleValue(op?: string) {
  return op && ['GT', 'GTE', 'LT', 'LTE', 'EQ', 'CONTAINS', 'NOT_CONTAINS'].includes(op)
}
function needsArrayValue(op?: string) {
  return op && ['IN', 'NOT_IN', 'BETWEEN'].includes(op)
}
function needsNumberValue(op?: string) {
  return op && ['GT', 'GTE', 'LT', 'LTE', 'EQ'].includes(op)
}

function newItem(parentId: string | null = null, relationToParent: string | null = null): any {
  return {
    id: `tmp_${Math.random().toString(36).slice(2, 10)}`,
    parentId,
    relationToParent,
    field: 'AGE',
    operator: 'GTE',
    value: '',
    refStageId: null,
    refDictId: null,
    orderIndex: items.value.length,
    children: [],
  }
}

function addRoot() {
  const it = newItem(null, null)
  items.value = [...items.value, it]
}

function addChild(parent: any) {
  if (!parent.children) parent.children = []
  parent.children.push(newItem(parent.id, 'AND'))
  // 触发响应式更新
  items.value = [...items.value]
}

function removeItem(item: any) {
  // 收集要删除的 id（含子节点）
  const ids = new Set<string>()
  const collect = (it: any) => {
    if (it.id) ids.add(it.id)
    if (it.children) it.children.forEach(collect)
  }
  collect(item)
  items.value = items.value.filter((it: any) => !ids.has(it.id))
}

function onFieldChange(item: any, _v: string) {
  // 字段变化时清空 value（避免字段/值类型不匹配）
  item.value = ''
}
</script>

<script lang="ts">
// 递归组件需要 name 选项
export default {
  name: 'ConditionTreeEditor',
}
</script>

<style scoped>
.condition-tree-editor {
  width: 100%;
}
.tree-item {
  padding: 8px 0;
  border-left: 2px solid #e0e0e0;
  padding-left: 12px;
  margin-left: 4px;
}
.node-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}
.ref-stage-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  margin-left: 108px;
  padding: 4px 0;
}
.children {
  margin-left: 24px;
  margin-top: 4px;
}
.add-child-row {
  margin-left: 108px;
  margin-top: 2px;
  margin-bottom: 4px;
}
.add-root-row {
  margin-top: 8px;
}
</style>
