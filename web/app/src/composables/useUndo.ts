import { h } from 'vue'
import { useMessage, NButton } from 'naive-ui'

/**
 * useUndo —— R-106 破坏性操作可撤销（中等级：直接执行 + Toast 撤销 5-8s）
 * 用法：const { undoable } = useUndo()
 *      undoable('已删除「Q3 报表」', () => restore(id))
 * 注意：onUndo 必须提供真实可恢复的回调（重新插入本地列表 / 调恢复接口）。
 *      禁止传入 no-op —— 那等于假撤销（验证剧场）。
 */
export function useUndo() {
  const message = useMessage()

  function undoable(text: string, onUndo: () => void | Promise<void>, duration = 8000) {
    // Naive UI MessageOptions 无 action 字段，使用官方支持的 render 自定义内容
    let inst: ReturnType<typeof message.success> | undefined
    const doUndo = () => {
      Promise.resolve(onUndo())
        .then(() => inst?.destroy())
        .catch(() => message.error('撤销失败，请手动恢复'))
    }
    inst = message.success('', {
      duration,
      keepAliveOnHover: true,
      render: () =>
        h(
          'div',
          { style: 'display:flex;align-items:center;gap:8px;' },
          [
            h('span', { style: 'flex:1;' }, text),
            h(
              NButton,
              { size: 'small', text: true, type: 'primary', onClick: doUndo },
              { default: () => '撤销' },
            ),
          ],
        ),
    })
  }

  return { undoable }
}
