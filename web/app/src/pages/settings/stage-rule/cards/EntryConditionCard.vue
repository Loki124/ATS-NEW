<template>
  <section class="config-card">
    <div class="card-title">
      <n-icon :component="FilterOutline" />
      进入条件
      <span class="title-desc">· 配置候选人进入本阶段需满足的条件</span>
    </div>

    <div class="block-header block-header--split">
      <div class="block-header__main">
        <n-icon :component="ListOutline" />
        <span class="block-desc">· 满足全部规则方可进入本阶段</span>
      </div>
      <ModuleSwitch :model-value="moduleOn" @update:model-value="emit('update:moduleOn', $event)" />
    </div>

    <div class="rule-content" :class="{ 'rule-content--hidden': !moduleOn }">
      <div class="actions-row">
        <button class="btn-outline-primary" type="button" @click="emit('add')">
          <n-icon :component="AddOutline" /> 添加规则
        </button>
        <button class="btn-text-primary" type="button" @click="emit('configure')">
          <n-icon :component="CreateOutline" /> 规则配置
        </button>
      </div>

      <RuleTable :columns="columns" :rows="rules">
        <template #actions="{ row }">
          <div class="action-btns">
            <a @click="emit('edit', row)">编辑</a>
            <a @click="emit('toggle', row)">{{ row.status === 'ENABLED' ? '停用' : '启用' }}</a>
            <a class="danger" @click="emit('remove', row)">删除</a>
          </div>
        </template>
      </RuleTable>
    </div>
  </section>
</template>

<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { FilterOutline, ListOutline, AddOutline, CreateOutline } from '@vicons/ionicons5'
import ModuleSwitch from '../components/ModuleSwitch.vue'
import RuleTable from '../components/RuleTable.vue'
import type { EntryConditionRule } from '../types'

defineProps<{
  rules: EntryConditionRule[]
  moduleOn: boolean
}>()

const emit = defineEmits<{
  (e: 'update:moduleOn', v: boolean): void
  (e: 'add'): void
  (e: 'configure'): void
  (e: 'edit', rule: EntryConditionRule): void
  (e: 'toggle', rule: EntryConditionRule): void
  (e: 'remove', rule: EntryConditionRule): void
}>()

const columns = [
  { key: 'rule_name', title: '规则名', width: '22%' },
  { key: 'expression', title: '执行条件', width: '28%' },
  { key: 'reject_message', title: '未满足提示', width: '30%' },
]
</script>

<style scoped>
.actions-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-top: 8px;
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
.btn-text-primary {
  background: transparent;
  border: none;
  color: var(--brand);
  font-size: var(--fs-12);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
  padding: 0 var(--space-1);
}
.btn-text-primary:hover {
  color: var(--brand-hover);
}
.action-btns {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.action-btns a {
  color: var(--brand);
  text-decoration: none;
  cursor: pointer;
  font-size: var(--fs-12);
  transition: color var(--duration-fast) var(--ease-out);
}
.action-btns a:hover {
  color: var(--brand-hover);
  text-decoration: underline;
}
.action-btns a.danger {
  color: var(--c-error);
}
.action-btns a.danger:hover {
  color: var(--c-error-deep);
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
