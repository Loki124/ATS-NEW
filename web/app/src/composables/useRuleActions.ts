/**
 * 规则操作组合式：复制 / 启用停用 / 删除。
 * 删除走 useDialog 二次确认（禁用原生 confirm）；所有动作结束后回调 reload 刷新列表。
 */
import { useMessage, useDialog } from 'naive-ui'
import { copyRule, toggleRule, deleteRule, type ControlRule } from '../api/campusControl'
import { extractApiError } from '../api/dynamic-field'

export function useRuleActions(reload: () => void | Promise<void>) {
  const message = useMessage()
  const dialog = useDialog()

  async function copy(rule: ControlRule) {
    try {
      await copyRule(rule.id)
      message.success('已复制为未启用副本')
      await reload()
    } catch (e) {
      message.error(extractApiError(e, '复制失败'))
    }
  }

  async function toggle(rule: ControlRule, isActive: boolean) {
    try {
      await toggleRule(rule.id, isActive)
      message.success(isActive ? '已启用规则' : '已停用规则')
      await reload()
    } catch (e) {
      message.error(extractApiError(e, '操作失败'))
    }
  }

  async function remove(rule: ControlRule) {
    const label = [rule.code, rule.dimensionName || rule.dimension, rule.indicatorName || rule.indicator]
      .filter(Boolean)
      .join(' · ')
    dialog.warning({
      title: '确认删除规则',
      content: `确定删除规则「${label}」吗？该操作不可撤销。`,
      positiveText: '删除',
      negativeText: '取消',
      onPositiveClick: async () => {
        try {
          await deleteRule(rule.id)
          message.success('已删除规则')
          await reload()
        } catch (e) {
          message.error(extractApiError(e, '删除失败'))
        }
      },
    })
  }

  return { copy, toggle, remove }
}
