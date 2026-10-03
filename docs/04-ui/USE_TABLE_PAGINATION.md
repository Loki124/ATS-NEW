# useTablePagination — 列表分页统一组件
> 最后更新：2026-09-20（依据 git 最后提交）

> 适用：ATS-NEW 前端所有 `<n-data-table>` 远程分页场景。
> 状态：2026-09-16 立项，2026-09-18 收口为统一 composable。

---

## 1. 为什么需要统一

- 多个列表页（候选 / 标量 / 需求 / 部门 / 字段 / 流程 / 院校 / 等等）分页器外观/行为不一致。
- 远程分页数据源有的是 `total`、有的是 `count`、有的是 `itemCount`，与 naive-ui `pagination` 字段名冲突。
- 多次复盘发现：reactive pagination 对象含 `pageSize` 字段时，naive-ui 内部受控失效（点 `50/页` 永远卡在初始值）。

---

## 2. 用法

```ts
import { useTablePagination } from '@/composables/useTablePagination'

const { pagination, queryParams, reset } = useTablePagination()

const { data, pending, refresh } = await useApiList('/api/v1/xxx/', {
  ...queryParams,  // 自动透传 page / page_size
})

// 在 <n-data-table> 上：
<n-data-table :pagination="pagination" :data="data" />
```

---

## 3. 默认参数

| 参数 | 值 |
|------|----|
| `TABLE_PAGE_SIZE` | 20 |
| `pageSizeOptions` | `[10, 20, 50, 100]` |

---

## 4. 强制外观

```
共 N 条 | [页码] | 20 / 页 [下拉] | 跳至 [输入框]
```

具体实现：`<n-pagination show-size-picker show-quick-jumper />` + `item-count` 绑定总条数 + `prefix` slot 渲染「共 N 条」。

---

## 5. 反模式（避免踩）

### 5.1 受控失效坑（commit `53c9624` 实证）

```ts
// ❌ 错：reactive 里含 pageSize 字段
const pagination = reactive({ page: 1, pageSize: 20, showSizePicker: true, ... })
```

Naive UI 内部：
```ts
const controlledPageSizeRef = computed(() => pagination.pageSize)
const mergedPageSizeRef = useMergedState(controlledPageSizeRef, uncontrolledPageSizeRef)
```

当 `:pagination` 传 reactive 对象且含 `pageSize` 时，`controlledPageSizeRef` 始终等于外部 reactive 的 pageSize；内置分页器的 `onUpdate:pageSize` 仅写入 `uncontrolledPageSizeRef`，**不写回外部 reactive** → pageSize 永远卡在初始值。

```ts
// ✅ 对：用 defaultPageSize（只设初始值）
const pagination = reactive({
  page: 1,
  // 没有 pageSize！
  showSizePicker: true,
  'onUpdate:page': (p) => { page = p; refresh() },
  'onUpdate:page-size': (s) => { pageSize.value = s; page = 1; refresh() },
})
```

### 5.2 字段名错用

| 错 | 对 |
|----|----|
| `pagination.total` | `pagination.itemCount` |
| 后端字段 `total` | 后端字段 `count` |
| naive-ui `pageSizeOptions` | naive-ui `pageSizes` |
| `?pageSize=20`（参数） | `?page_size=20`（DRF 透传） |

---

## 6. 关联文档

- 设置页滚动契约 → `docs/04-ui/SETTINGS_PAGE_STRUCTURE.md`（分页器嵌在 `.page-body` 内）
- 标准简历设置（三层结构 + 拖拽） → `docs/04-ui/STANDARD_RESUME_SETTINGS.md`