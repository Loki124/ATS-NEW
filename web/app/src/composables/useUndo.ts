import { useMessage } from 'naive-ui'

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
    message.success(text, {
      duration,
      keepAliveOnHover: true,
      action: {
        text: '撤销',
        onClick: () => {
          Promise.resolve(onUndo()).catch(() => {
            message.error('撤销失败，请手动恢复')
          })
        },
      },
    })
  }

  return { undoable }
}
