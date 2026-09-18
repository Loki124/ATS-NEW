/**
 * useTablePagination —— 设置页 / 列表页统一分页配置工厂
 *
 * 设计意图（2026-09-16 兵哥指令「表格分页统一组件」）：
 * 此前各页散落 inline `{ pageSize: 30 }` / `{ pageSize: 15 }` / 远程 computed
 * 写法不一、每页自定页面大小，违反 UI 一致性。本 composable 提供唯一来源：
 *   - TABLE_PAGE_SIZE        统一默认每页条数（20）
 *   - TABLE_PAGE_SIZE_OPTIONS 统一 pageSize 可选项 [10, 20, 50, 100]
 *   - localPagination()      客户端分页（一次性取全量，n-data-table 自行切片）
 *   - remotePagination()     服务端分页（page / itemCount 由调用方响应式维护）
 *
 * 统一外观（与 docs/04-ui/SETTINGS_PAGE_STRUCTURE.md §4.x 截图规范一致）：
 *   共 N 条  |  < 1 2 >  |  [20 / 页 ▾]  |  跳至 [__]
 *   - showSizePicker: true  + pageSizes（切换每页条数）
 *   - showQuickJumper: true（跳至第 N 页）
 *   - prefix 渲染「共 N 条」
 *
 * ⚠️ n-data-table 远程分页用 itemCount（非 total）表达总条数 —— remotePagination 已对齐。
 * ⚠️ 禁止在业务页再手写 `{ pageSize: N }` 或远程 computed（见 docs/04-ui/SETTINGS_PAGE_STRUCTURE.md）。
 */
import { computed, ref, type Ref } from 'vue';

/** 统一默认每页条数 */
export const TABLE_PAGE_SIZE = 20;

/** 统一 pageSize 可选项 */
export const TABLE_PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

/** 分页前缀：渲染「共 N 条」（n-pagination / n-data-table 均透传 itemCount） */
function totalPrefix(info: { itemCount?: number }): string {
  return `共 ${info.itemCount ?? 0} 条`;
}

/**
 * 本地（客户端）分页配置。
 * 适用于一次性拉取全量、由 n-data-table 在前端切片展示的场景。
 * @param pageSize 每页条数，默认 TABLE_PAGE_SIZE
 */
export function localPagination(pageSize: number = TABLE_PAGE_SIZE) {
  return {
    page: 1,
    pageSize,
    showSizePicker: true,
    pageSizes: TABLE_PAGE_SIZE_OPTIONS,
    showQuickJumper: true,
    prefix: totalPrefix,
  };
}

/**
 * 远程（服务端）分页配置（响应式 computed）。
 * @param opts.page      当前页 Ref<number>（双向绑定，组件 @update:page 写回）
 * @param opts.itemCount 总条数 Ref<number>（n-data-table 远程分页字段，非 total）
 * @param opts.pageSize  每页条数，number 或 Ref<number>，默认 TABLE_PAGE_SIZE
 * @param opts.showSizePicker 是否显示 pageSize 切换，默认 false
 * @param opts.onPageChange    页码变化回调（可选，用于触发重新拉取）
 * @param opts.onPageSizeChange pageSize 变化回调（可选；传入时自动开启 showSizePicker 并 page 归 1）
 */
export function remotePagination(opts: {
  page: Ref<number>;
  itemCount: Ref<number>;
  pageSize?: number | Ref<number>;
  showSizePicker?: boolean;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
}) {
  const pageSizeRef =
    typeof opts.pageSize === 'object' ? (opts.pageSize as Ref<number>) : ref(opts.pageSize ?? TABLE_PAGE_SIZE);
  const enableSizePicker =
    opts.showSizePicker ?? (opts.onPageSizeChange !== undefined);

  return computed(() => ({
    page: opts.page.value,
    pageSize: pageSizeRef.value,
    itemCount: opts.itemCount.value,
    showSizePicker: enableSizePicker,
    pageSizes: TABLE_PAGE_SIZE_OPTIONS,
    showQuickJumper: true,
    prefix: totalPrefix,
    ...(enableSizePicker && opts.onPageSizeChange
      ? {
          onUpdatePageSize: (size: number) => {
            pageSizeRef.value = size;
            opts.page.value = 1;
            opts.onPageSizeChange?.(size);
          },
        }
      : {}),
  }));
}
