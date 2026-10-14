<script lang="ts">
/**
 * 多选框「全部」标签渲染（2026-10-14 兵哥定稿）。
 *
 * 背景：值域配置的多选对象框顶部有「全部 / 取消全部」项。选中「全部」后，
 * 底层 value 是「哨兵 + 全量 id」，若走 n-select 默认渲染，标签区会铺开
 * 十几个 chip（既挤占空间又看不出"这是全选"）。
 *
 * ⚠️ Naive UI 2.44 的 n-select **只有 renderTag prop、没有 #tag 插槽**
 * （内部 Selection 只调用 props.renderTag，见 _internal/selection/src/Selection.mjs），
 * 所以这里必须用函数式组件 + :render-tag 传入，用插槽是无效的。
 *
 * 渲染规则：
 *   - 全选态：只给哨兵项渲染一个「全部」chip，其余项渲染空 → 标签区只有「全部」
 *   - 非全选态：按默认样式逐个渲染具体对象，可单独删除
 *
 * 数据层不做特殊处理：哨兵值不落库，存的始终是真实对象 id 全集，
 * 「应用时映射出所有选项」天然成立（规则计算拿到的就是全部 id）。
 */
import { defineComponent, h } from 'vue'
import { NTag } from 'naive-ui'

export default defineComponent({
  name: 'AllChipTag',
  props: {
    /** 当前被渲染的选项（来自 renderTag 的入参） */
    option: { type: Object, required: true },
    /** 该多选框当前是否处于全选态 */
    all: { type: Boolean, default: false },
    /** 「全部」哨兵值 */
    sentinel: { type: String, default: '' },
    /** 全选态下展示的文案 */
    allLabel: { type: String, default: '' },
  },
  emits: ['close'],
  setup(props, { emit }) {
    const tag = (label: string) =>
      h(
        NTag,
        {
          size: 'small',
          bordered: false,
          closable: true,
          onClose: () => emit('close'),
        },
        { default: () => label },
      )
    return () => {
      // 全选态：只有哨兵项出「全部」，真实项一律不渲染
      if (props.all) return props.option.value === props.sentinel ? tag(props.allLabel) : null
      return tag(props.option.label)
    }
  },
})
</script>
