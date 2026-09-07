<!--
  进入条件 Card 1（HTML 原型 2 列表格 + 行内条件组展开式预览）
  原型列：执行条件（条件组展开）/ 未满足提示
  原型无"操作"列——编辑通过 Card 1 标题 row 的"规则配置"按钮进二级弹窗。
-->
<template>
  <section class="config-card">
    <div class="card-title">
      <span class="title-left">
        <n-icon :component="LogInOutline" />
        进入条件
        <span class="title-desc">· 候选人在进入当前阶段时，将会受到配置的条件进行校验</span>
      </span>
      <span class="title-actions">
        <button class="btn-outline-primary" type="button" @click="emit('add')">
          <n-icon :component="AddOutline" /> 添加规则
        </button>
        <button class="btn-outline-primary" type="button" @click="emit('configure')">
          <n-icon :component="CreateOutline" /> 规则配置
        </button>
        <ModuleSwitch :model-value="moduleOn" @update:model-value="emit('update:moduleOn', $event)" />
      </span>
    </div>

    <div class="rule-content" :class="{ 'rule-content--hidden': !moduleOn }">
      <div class="rule-table-wrap">
        <table class="rule-table">
          <thead>
            <tr>
              <th>执行条件</th>
              <th style="width: 200px;">未满足提示</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="rules.length === 0">
              <td colspan="2" class="rule-table__empty">暂无规则</td>
            </tr>
            <tr v-for="rule in rules" v-else :key="rule.id || rule.rule_name">
              <td>
                <div class="rule-condition">
                  <template v-if="rule.groups && rule.groups.length">
                    <div v-for="(g, gi) in rule.groups" :key="gi" class="rule-condition__group">
                      <template v-if="rule.groups.length > 1">
                        <div class="rule-condition__group-label">条件组 {{ gi + 1 }}</div>
                      </template>
                      <div v-for="(c, ci) in g.conditions" :key="ci" class="rule-condition__line">
                        条件{{ gi + 1 }}.{{ ci + 1 }}：{{ formatCondition(c) }}
                      </div>
                      <div v-if="g.innerExpression" class="rule-condition__line">
                        组内表达式：{{ g.innerExpression }}
                      </div>
                    </div>
                    <div class="rule-condition__line rule-condition__line--total">
                      表达式：{{ rule.expression || '—' }}
                    </div>
                  </template>
                  <template v-else>
                    <div v-for="(it, idx) in rule.items" :key="idx" class="rule-condition__line">
                      条件{{ idx + 1 }}：{{ formatCondition(it) }}
                    </div>
                    <div class="rule-condition__line rule-condition__line--total">
                      表达式：{{ rule.expression || '—' }}
                    </div>
                  </template>
                </div>
              </td>
              <td>{{ rule.reject_message || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { LogInOutline, AddOutline, CreateOutline } from '@vicons/ionicons5'
import ModuleSwitch from '../components/ModuleSwitch.vue'
import type { EntryConditionRule, ConditionItem } from '../types'
import { AR_OPERATOR_LABELS, AR_SOURCE_LABELS } from '../constants'

defineProps<{
  rules: EntryConditionRule[]
  moduleOn: boolean
}>()

const emit = defineEmits<{
  (e: 'update:moduleOn', v: boolean): void
  (e: 'add'): void
  (e: 'configure'): void
}>()

function formatCondition(it: ConditionItem): string {
  const sourceLabel = AR_SOURCE_LABELS[it.condition_type] || it.condition_type
  const opLabel = AR_OPERATOR_LABELS[it.operator] || it.operator
  if (it.operator === 'IS_EMPTY' || it.operator === 'IS_NOT_EMPTY') {
    return `${sourceLabel} ${it.field} ${opLabel}`
  }
  const valueText = Array.isArray(it.value) ? it.value.join('、') : String(it.value ?? '')
  return `${sourceLabel} ${it.field} ${opLabel} ${valueText}`
}
</script>

<style scoped>
/* ===== card-title 双层布局（HTML 原型 .title-left + .title-actions） ===== */
.card-title {
  flex-wrap: wrap;
  gap: var(--space-2);
}
.title-left {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  min-width: 0;
}
.title-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  margin-left: auto;
}
.title-actions .btn-outline-primary {
  margin: 0;
}

.btn-outline-primary {
  background: transparent;
  border: 1px dashed var(--brand);
  color: var(--brand);
  padding: 0 14px;
  height: 30px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-12);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  font-weight: 500;
}
.btn-outline-primary:hover {
  background: var(--brand-a12);
  border-style: solid;
}

/* ===== Rule Table (HTML 原型 .rule-table) ===== */
.rule-table-wrap {
  overflow-x: auto;
  border-radius: var(--radius-sm);
  scrollbar-width: thin;
}
.rule-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: var(--fs-12);
  background: var(--surface);
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--g2);
}
.rule-table th {
  background: var(--g1);
  padding: 8px 12px;
  text-align: left;
  font-weight: 500;
  color: var(--ink-soft);
  border-bottom: 1px solid var(--g2);
  white-space: nowrap;
  font-size: var(--fs-12);
}
.rule-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-hairline);
  vertical-align: middle;
  line-height: 1.4;
}
.rule-table tr:last-child td { border-bottom: none; }
.rule-table__empty {
  text-align: center;
  color: var(--ink-faint);
  padding: 14px !important;
  font-style: italic;
}

/* 行内条件组展开式预览 */
.rule-condition__line {
  line-height: 1.6;
}
.rule-condition__group + .rule-condition__group {
  margin-top: 6px;
}
.rule-condition__group-label {
  color: var(--ink-soft);
  font-weight: 500;
  margin-bottom: 2px;
}
.rule-condition__line--total {
  color: var(--ink-soft);
  font-weight: 500;
  margin-top: 2px;
}

/* 模块关闭时规则表显隐（max-height 过渡，不丢数据） */
.rule-content {
  transition: opacity var(--duration-base) var(--ease-out),
    max-height var(--duration-base) var(--ease-out);
  overflow: hidden;
  max-height: 2000px;
  opacity: 1;
}
.rule-content--hidden {
  max-height: 0;
  opacity: 0;
  pointer-events: none;
  margin: 0 !important;
}
</style>