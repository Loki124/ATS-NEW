<template>
  <div class="rule-table-wrap">
    <table class="rule-table">
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            :style="col.width ? { width: col.width } : undefined"
          >
            {{ col.title }}
          </th>
          <th v-if="$slots.actions" class="rule-table__act-col">{ t('pages.settings.stage-rule.components.RuleTable.s1') }</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, idx) in rows" :key="rowKey(row, idx)">
          <td v-for="col in columns" :key="col.key" :title="String(row[col.key] ?? '')">
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]" :index="idx">
              {{ row[col.key] ?? '' }}
            </slot>
          </td>
          <td v-if="$slots.actions" class="rule-table__actions">
            <slot name="actions" :row="row" :index="idx" />
          </td>
        </tr>
        <tr v-if="rows.length === 0">
          <td class="rule-table__empty" :colspan="columns.length + ($slots.actions ? 1 : 0)">
            暂无规则
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts" generic="T extends Record<string, any>">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

interface Column {
  key: string
  title: string
  width?: string
}

const props = defineProps<{
  columns: Column[]
  rows: T[]
  rowKeyProp?: string
}>()

function rowKey(row: T, idx: number): string {
  const id = (row as Record<string, any>).id
  return id != null ? String(id) : `row-${idx}`
}
</script>

<style scoped>
.rule-table-wrap {
  overflow-x: auto;
  margin-top: 6px;
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
  font-weight: 500;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  border-bottom: 1px solid var(--g2);
  text-align: left;
  padding: var(--space-2) var(--space-3);
  white-space: nowrap;
}
.rule-table td {
  font-size: var(--fs-12);
  color: var(--ink);
  border-bottom: 1px solid var(--g2);
  padding: var(--space-2) var(--space-3);
  vertical-align: middle;
}
.rule-table tr:last-child td {
  border-bottom: none;
}
.rule-table__act-col {
  width: 140px;
}
.rule-table__actions {
  white-space: nowrap;
}
.rule-table__empty {
  text-align: center;
  color: var(--ink-faint);
  padding: 14px !important;
  font-style: italic;
}
</style>
