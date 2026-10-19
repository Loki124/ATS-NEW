/**
 * useTableColumns —— 数据列表列对齐规则与操作列规格的单一真源
 *
 * 设计意图（2026-10-15 兵哥指令「为数据列表的内容设定对齐规则，尽量统一使用居中对齐」）：
 * 此前各表格列对齐全靠各页自觉，设置中心全域仅 6 处声明 `align`，其余默认左对齐，
 * 同一套设计系统下观感参差。本 composable 与 useTablePagination.ts 对称，提供唯一来源。
 *
 * ## 一、四档对齐规则（按【列的内容类型】分档，不是无脑全居中）
 *
 * | 档 | 内容类型              | 对齐   | 典型列                        |
 * |----|-----------------------|--------|-------------------------------|
 * | A  | 短值 / 枚举 / 标识     | center | 编码、名称、数量、状态、来源   |
 * | B  | 控件 / 操作           | center | 开关、按钮组                  |
 * | C  | 数值（可比大小）      | center | 天数、金额、人数              |
 * | D  | 长文本 / 富内容       | left   | 描述、备注、规则表达式、JSON  |
 *
 * ⚠️ **D 档必须保留左对齐**：长 SQL / 多行描述居中后极难扫读，
 * 强制居中会把「整齐」换成「读不懂」。整齐 ≠ 一律居中。
 *
 * ## 二、为什么用工厂函数而不是全局 CSS
 *
 * n-data-table 的 `align` 最终渲染为**行内 `style="text-align:..."`**（实测验证），
 * 行内样式优先级高于任何 CSS 规则 ⇒ 全局样式表无法覆盖。
 * （td 虽同时带 `n-data-table-td--center-align` class 可作钩子，
 *   但表头 th 只有行内 style，无 class 可用，无法对称实现。）
 * 因此唯一可行路径是在【列定义层】统一声明，本工厂即为该层入口。
 *
 * ## 三、操作列规格（同一问题的另一半）
 *
 * 实测 Naive UI common 主题刻度：
 *   tiny  = 12px / height 22px   ← 旧写法
 *   small = 14px / height 28px
 *   medium= 14px / height 34px   ← 工具栏按钮
 *   表格正文 = 14px
 * tiny 的 12px 比同页正文与工具栏按钮都小 2px，视觉上「矮一截」，
 * 正是「文字和 icon 太小、不像一个层级」的成因。
 * ⇒ 操作列统一走 `OP_ACTION_BUTTON_SIZE`（small），与正文同字号。
 *
 * 📖 依据规范：docs/04-ui/UI_STANDARD.md §5.9.1
 *   （同组按钮全有 icon 或全无；删除 type="error"；操作列 NSpace wrap:false）
 *   docs/04-ui/frontend-DESIGN.md §Data Table
 *   （操作列用 quaternary + type=primary/error 文字按钮，不堆实心）
 */
import type { DataTableColumn, DataTableRowKey } from 'naive-ui';
import { h } from 'vue';
import type { TableBaseColumn, TableColumnTitle } from 'naive-ui/es/data-table/src/interface';

/** 列内容类型 → 对齐档位（见文件头四档规则表） */
export type ColumnAlignTier = 'short' | 'control' | 'numeric' | 'text';

/** 各档对应的 text-align（与 n-data-table `align` 取值一致） */
export const ALIGN_BY_TIER: Record<ColumnAlignTier, 'left' | 'center'> = {
  short: 'center', //  A 短值 / 枚举 / 标识
  control: 'center', // B 控件 / 操作
  numeric: 'center', // C 数值
  text: 'left', //    D 长文本（强制左对齐，见文件头警告）
};

/**
 * 列定义入参类型。
 *
 * ⚠️ 类型陷阱（tsc TS2353「'title' does not exist in type」）：
 * Naive 的 `TableColumn` / `DataTableColumn` 都是**联合类型**
 * （TableColumnGroup | TableBaseColumn | TableSelectionColumn | TableExpandColumn），
 * 对联合类型做 Omit / Partial 会按分配律展开成各成员的公共字段集，
 * `title` 虽存在于部分成员也会被判为「不存在」。
 *
 * 正解：以 `TableBaseColumn`（业务叶子列，title/key/width/render/fixed 全在此）
 * 为基础 + 局部放宽 align。分组的 type/children 列请直接写裸对象，不必套工厂。
 */
export type ColumnInput<T = any> = Omit<TableBaseColumn<T>, 'align'> & {
  align?: 'left' | 'center';
};

/**
 * 操作列按钮统一规格。
 * small = 14px / height 28px，与表格正文同字号同层级。
 * ⚠️ 保留 icon 是刻意的：§1.8.1 明令「同组按钮必须全有 icon 或全无」，
 *    只放大按钮去掉 icon 会换成另一种违规。
 */
export const OP_ACTION_BUTTON_SIZE = 'small' as const;

/**
 * 🔴 表头对齐的真正解法（实测得出，勿改回 CSS-only 方案）
 *
 * naive 源码 `TableParts/Header.mjs:243`：
 *     textAlign: column.titleAlign || column.align
 * ⇒ align:'center' 确实被写进 `<th style="text-align:center">` 的行内样式。
 *
 * 但实测 DOM 结构是：
 *     <th style="text-align:center">
 *       <div class="n-data-table-th__title-wrapper">
 *         <div class="n-data-table-th__title">标题</div>   ← 块级子元素
 *       </div>
 *     </th>
 *
 * ⚠️ **text-align 只对【行内内容】生效**，而 title 是块级子元素、
 *    内部另起一行按左对齐排 ⇒ th 行内是 center，**视觉上标题仍偏左**。
 *    这就是「表头没跟着正文一起居中」的根因。
 *
 * ❌ CSS-only 方案全部无效（已逐一验证）：
 *    · `text-align: inherit` —— jsdom 与部分浏览器对 inline→block 继承链解析不可靠，
 *      且 CSS 无法读取 th 的行内值来判断该不该居中；
 *    · `.n-data-table-th--center-align` —— **该 class 只存在于 td，th 没有**；
 *    · `:has()` —— 能用但需维护一份「哪些 th 居中」的状态，与列工厂重复且易漂移。
 *
 * ✅ 正解：把 title 渲染为**带 text-align 的块级元素**，
 *    由列工厂直接产出 VNode。对齐与内容绑定在一起，不依赖任何继承或外部状态。
 */
function buildTitle(title: TableColumnTitle | undefined, align: 'left' | 'center'): TableColumnTitle | undefined {
  // 非字符串标题（函数式/自定义 VNode）交还调用方自行处理，不强行包裹
  if (typeof title !== 'string') return title;
  return () =>
    h(
      'span',
      { style: { display: 'block', textAlign: align } },
      { default: () => title },
    );
}

/**
 * 列工厂：声明列内容类型，自动套用对应档位的对齐。
 *
 * 对齐同时作用于【表头与正文】—— 见 buildTitle() 的实测说明。
 *
 * 用法（替代裸对象数组）：
 * ```ts
 * const columns = [
 *   column({ title: '身份编码', key: 'roleCode', width: 160 }, 'short'),
 *   column({ title: '状态', key: 'status', width: 90, render: ... }, 'control'),
 *   column({ title: '描述', key: 'desc' }, 'text'),
 * ]
 * ```
 *
 * @param col  列定义（其余字段原样透传）
 * @param tier 列内容类型档位；缺省为 'short'（A 档居中）—— 数据列表以短值为主
 */
export function column<T = any>(col: ColumnInput<T>, tier: ColumnAlignTier = 'short'): DataTableColumn<T> {
  // 已显式声明 align 的列以调用方为准（尊重个别页的例外），否则按档位套用
  const align = col.align ?? ALIGN_BY_TIER[tier];
  return {
    ...col,
    align,
    // 表头同步对齐（naive 会把 titleAlign||align 写进 th 行内样式，但那是块级 title 的父级，
    // 视觉不生效，故额外用 titleAlign 声明一次，与 buildTitle 的 VNode 形成双保险）
    titleAlign: col.titleAlign ?? align,
    title: buildTitle(col.title, align),
  } as DataTableColumn<T>;
}

/**
 * 批量版：把「档位数组」与「列定义数组」按序配对，一次性生成整表列定义。
 *
 * 用于需要在同一处声明全部列、且希望对齐规则一目了然的场景。
 *
 * @param cols 列定义数组（顺序需与 tiers 顺序一致）
 * @param tiers 各列档位；长度不一致时按最短为准，缺失列回退 'short'
 */
export function columns<T = any>(
  cols: ColumnInput<T>[],
  tiers: ColumnAlignTier[],
): DataTableColumn<T>[] {
  return cols.map((col, i) => column<T>(col, tiers[i] ?? 'short'));
}

export type { DataTableColumn, DataTableRowKey };
