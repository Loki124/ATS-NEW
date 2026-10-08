import { useDialog, useMessage } from 'naive-ui'

interface UseCloseGuardOptions {
  /** 保存中？为 true 时拦截所有关闭（防重复提交/半保存态关闭） */
  isSaving?: () => boolean
  /** 是否有未保存修改？默认 () => true（最安全：表单弹窗一律二次确认）。可传真实脏检查 */
  isDirty?: () => boolean
  /** 真正执行关闭的动作（emit('update:show', false) / visible.value=false / 现有 close()） */
  onClose: () => void
  /** 确认弹窗文案（可选，给中文默认） */
  title?: string
  content?: string
}

/**
 * 统一弹窗关闭守卫：
 * - 保存中 → 拦截并轻提示
 * - 有未保存修改 → 弹确认（放弃 / 继续编辑），确认后才 onClose
 * - 否则 → 直接 onClose
 * 配合模板 :mask-closable="false" + :on-mask-click="requestClose" + @update:show="(v)=>!v&&requestClose()" 使用，
 * 使遮罩/ESC/X 三条关闭路径全部经过本守卫，消除「点遮罩静默丢草稿」的不一致。
 */
export function useCloseGuard(options: UseCloseGuardOptions) {
  const dialog = useDialog()
  const message = useMessage()
  const isSaving = options.isSaving ?? (() => false)
  const isDirty = options.isDirty ?? (() => true)

  /**
   * 返回 false 的语义：
   * - 作为 @negative-click / @on-mask-click 钩子时，告诉 Naive UI「不要自动关闭」，由本守卫在确认后才 onClose；
   * - 作为 @update:show / 普通 click 监听器时，返回值被忽略，无副作用。
   */
  function requestClose(): boolean {
    if (isSaving()) {
      message.warning('正在保存，请稍候…')
      return false
    }
    if (isDirty()) {
      dialog.warning({
        title: options.title ?? '放弃未保存的修改？',
        content: options.content ?? '当前内容尚未保存，关闭后将丢失。确定要放弃吗？',
        positiveText: '放弃',
        negativeText: '继续编辑',
        onPositiveClick: () => options.onClose(),
      })
      return false
    }
    options.onClose()
    return false
  }

  return { requestClose }
}
