# TDesign《桌面端组件(通用)》套用性评估

> 评估日期：2026-10-18
> 评估对象：MasterGo 分享《桌面端组件(通用)》→ 确认为 **腾讯 TDesign 官方开源设计系统**的设计侧资产
> 关联：tdesign-vue-next（Vue 3 组件实现）Stable 1.20.10
> 结论一句话：**可以套用，但不建议换组件库。设计令牌与规范口径直接借用，运行时保持 naive-ui 不动。**

---

## 0. 身份鉴定

分享链接 `mastergo.com/goto/WXUfiN6G?page_id=0:194670&file=172698996235937`
真实文件地址 `mastergo.com/file/172698996235937?page_id=0:194670`

打开后 Cover 页大字标识：**Open Source Design System / TDesign**，左上角 Starter / Web / Version 1.2.x。
左侧图层树组件清单与 tdesign-vue-next 官网组件总览逐项对齐：

| 分类 | 组件 |
| --- | --- |
| Welcome | Changelog / Styles / Template |
| Base 基础 | Button、Divider、Icon、Layout、Link |
| Navigation 导航 | Anchor、Breadcrumb、Dropdown、Menu、**Pagination**、Steps、Tabs |
| Entry 输入 | Cascader、Checkbox、ColorPicker、DatePicker、Form、Input、InputNumber、Radio、Search、Select |
| Data 数据展示 | Table、Tag、Badge、Avatar、Descriptions、Statistic… |
| Feedback 反馈 | Alert、Dialog、Drawer、Notification、Message、Popconfirm、Progress、Result、Skeleton、Spin |
| Advanced 高级 | Anchor、Calendar、Cascader、Transfer、Upload、TreeSelect、Cascader… |

结论：这是 TDesign 设计体系的 MasterGo 设计资产，**不是社区组件库、不是私有设计稿**，可以放心引用。

---

## 1. 本项目现状（量化基线）

| 维度 | 实测值 | 采集方式 |
| --- | --- | --- |
| UI 库 | naive-ui `^2.44.1` | `web/app/package.json` |
| 引用文件数 | **168 个** | `grep -rl "naive-ui" src` |
| `<n-*>` 标签总数 | **3706 个** | `grep -roh "<n-[a-z-]*" src --include=*.vue \| wc -l` |
| tdesign 引用 | **0** | `grep -rl tdesign src \| wc -l` |
| 自定义皮肤 CSS | glass.css **1514 行** + glass-modal.css **156 行** = 1670 行 | `wc -l` |
| CSS 内 `--n-*` 覆盖 | 12 处（仅冰山一角，scoped style 内还有大量 `:deep()`） | `grep -o "\-\-n-[a-z-]*"` |
| naive 官方主题机制 | **完全未使用** | `grep -rn "ConfigProvider\|darkTheme\|themeOverrides"` → 0 命中 |

组件分布 Top 15：

```
n-button 563   n-form-item 424   n-icon 383      n-select 307   n-input 297
n-space  194   n-tag 132         n-modal 107     n-empty 93      n-data-table 84
n-grid-item 79 n-switch 74       n-form 72       n-input-number 71 n-radio 66
```

品牌色：`--brand: #6366F1`（OKLCH 推导 50~900 十级色阶，单一输入 `--brand`）

---

## 2. 三层套用性结论

### 第 1 层 · 设计令牌 → ✅ 直接套用

TDesign 令牌体系：5 类（色彩 / 尺寸 / 圆角 / 阴影 / 字体），色彩类走 10 级色阶
（`--td-brand-color-1..10`，主色 `--td-brand-color-7: #0052d9`），
支持全局覆盖 + 组件级覆盖，主题生成器可导出 CSS 变量集。

**与本项目高度同构**：我们已有 `--brand: #6366F1` 单一输入 → OKLCH 推导 `--brand-50..900`，
外加 `--brand-button` / `--brand-hover` / `--brand-pressed` / `--on-brand` 语义层。

可借鉴的 3 点：
1. **10 级色阶命名法**（1 最浅 → 10 最深）↔ 我们的 50~900，两者一一对位，无需重命名。
2. **「组件级覆盖」范式**——TDesign 允许只覆盖单组件的令牌，不必全局改。我们现在的玻璃拟态皮肤
   只能靠 `:deep()` 逐组件硬改，这个范式值得移植。
3. **主题生成器导出 CSS**——对应我们已落地的 `brand-tokens.mjs`（单一输入 → 生成令牌）。

**不套用的部分**：TDesign 的品牌色是 `#0052D9`（TDesign 蓝），与我们的靛紫 `#6366F1` 冲突。
若整套换成 TDesign 蓝，等于全站视觉重做。**只借方法，不借色值。**

### 第 2 层 · 组件规范口径 → ⚠️ 改造后套用

TDesign 关键规范与我们的对照：

| 规范点 | TDesign | 本项目现状 | 判定 |
| --- | --- | --- | --- |
| Button 变体 | `variant`：base 填充 / outline 描边 / dashed 虚框 / text 文字 | 我们是「4 类 6 态」：主 / 次 / 幽灵 / 危险 | **概念同源，命名不同** |
| Button 主题 | `theme`：default / primary / danger / light | primary / default / ghost / danger | 需映射 |
| Button 尺寸 | `size`：extra-small / small / medium / large | 我们只有 `small`（`OP_ACTION_BUTTON_SIZE`） | ⚠️ 我们缺 xs / medium / large 三档 |
| Pagination 总数 | `totalContent`（默认显示） | `totalPrefix()` 统一渲染 | 一致 |
| Pagination 档位 | `pageSizeOptions` 默认 `[5,10,20,50]` | 我们 `[10,20,50,100]` | 一致（我们更贴合 B 端） |
| Pagination 跳页 | `showJumper`，默认 `false` | 我们 `showQuickJumper` 必开 | 一致 |
| Pagination 默认页大小 | 默认 `10` | `TABLE_PAGE_SIZE = 20` | 我们的更适合 B 端 |
| Table 斑马纹 | `bordered` + 斑马线 | 我们 `striped` + 去边线 + 标题行常驻底色 | **我们的已更贴近实战** |
| Table 固定列 | `fixed: 'left' \| 'right'` | naive `fixed` | 一致 |
| Table 虚拟滚动 | `scroll={{ type: 'virtual' }}`，`threshold` 默认 100 | naive 有 `virtual-scroll-props` | 一致 |
| Table 吸顶 | `headerAffixedTop` / `footerAffixedBottom` / `paginationAffixedBottom` | naive 无对应 | ⚠️ **值得补** |
| Dialog 底部按钮 | `confirmBtn` / `cancelBtn`，类型 `string \| ButtonProps \| TNode` | naive `positiveText` / `negativeText` | 一致 |
| Dialog 异步加载 | `confirmLoading` + 按钮带 loading 标识 | 我们 `loading` 强制态已有 | 一致 |
| Dialog 宽度 | 可传任意宽度 | 我们有 4 档档位规范（`MODAL_WIDTHS`） | 我们的更成体系 |
| Dialog 样式穿透 | 用 `:global()`，`:deep()` **对 Teleport 无效** | 同病 | ⚠️ 已知坑，需写进文档 |

**必须修正的 3 个认知**（TDesign 文档明确指出，我们踩过同一个坑）：
- Dialog 用 Teleport 重构后，`:deep()` **无法穿透** → 必须 `:global()`。本项目记忆里
  `glass-modal.css` 是独立非 scoped 文件，正是绕过此坑的正确做法。
- 多层 Dialog 嵌套时，**除最内层外，外层必须设 `lazy: true`**，否则报
  `NotFoundError: insertBefore ... is not a child of this node`。
- `attach` 挂载的目标节点必须**在挂载 Teleport 之前已存在于 DOM**。

**净收益**：TDesign 在 Button 尺寸三档、Table 吸顶、Dialog 嵌套规范上比我们成熟，可直接抄口径。

### 第 3 层 · 组件代码实现 → ❌ 不建议套用

引入 `tdesign-vue-next` 的成本（本项目实测基线）：

| 成本项 | 量级 |
| --- | --- |
| 需替换的标签 | **3706 个** `<n-*>` → `<t-*>`，其中 `n-button` 563 个 |
| 属性名映射 | `positive-text`→`theme="primary"`、`striped`→`bordered`、`show-quick-jumper`→`show-jumper`… 全线不兼容 |
| 主题适配 | 现有 1670 行玻璃拟态皮肤基于 `--n-*` 变量，需全部重写为 `--td-*` |
| i18n 适配 | 每个组件的 locale 包名不同（`tdesign` vs `naive`），现有 zh-CN 域文件结构需重做 |
| 现有基建失效 | `useTableColumns`（唯一真源）、`useTablePagination`（唯一真源）全部作废重写 |
| 双库共存风险 | naive 与 tdesign 都注入全局样式，主题变量命名不冲突但视觉必然割裂，168 个文件无法一次切完 |
| 收益 | 无——设计侧我们已经通过模板中心做到了等价能力 |

**代价 / 收益比是负的**，且会推倒刚建成的「单一真源」基建（`useTableColumns` / `useTablePagination`），
违反项目铁律「改条件/参数透传必补穿透测试」「验证须穿透真实链路」的成本模型。

---

## 3. 落地建议（三档，按投入产出排序）

### 建议 A · 零成本立即可做（推荐先做）

把 TDesign 的**规范口径**写进现有模板中心，**不引入任何依赖**：

1. **补 Button 尺寸三档** —— 在 `button-skin.css` 增加 `.stpl-btn--xs / --md / --lg`（对齐 naive `size="small|medium|large"`），
   在按钮模板的「使用规则」页签演示，并把「行内操作用 xs/小号、标准按钮用小号、主 CTA 用中号」写进规则。
   > 依据：TDesign 有 4 档，我们只有 1 档，563 个 `n-button` 缺尺寸语义。
2. **补 Table 吸顶** —— 列表模板 `.table-wrap` 增加 `max-height` + 表头吸顶示范，
   说明「长列表必须吸顶，否则滚动丢失上下文」。
3. **补 Dialog 嵌套规范** —— 写进 `NAIVE_UI_PITFALLS.md` 的「Teleport 穿透」章节：
   `:deep()` 无效 → `:global()`；多层嵌套外层设 `lazy`。

### 建议 B · 令牌层方法论借鉴（中期）

把 TDesign 的「组件级令牌覆盖」范式引入 `tokens.css`：
允许某个模块声明自己的令牌覆盖块（如模板中心的 `.stpl-root`），**而不污染全局**。
我们现在的 `.stpl-root` 已经是这个模式的雏形（上一轮踩坑后补的），可以把它正式升格为项目惯例。

同时建议在 `tokens.css` 头部注释里补一行溯源信息：色阶命名法参考 TDesign Design Token 体系。

### 建议 C · 换组件库（❌ 明确不建议）

不建议引入 `tdesign-vue-next`。若未来公司层面强制要求统一到 TDesign，
那是一个独立的架构级决策，需要单独立项、重新评估，不应混在 UI 规范统一里做。

---

## 4. 与既有决策的关系

本评估**不推翻**已落地的任何结论：
- 「乙系列表」为全站唯一标准 —— 不变。
- 按钮「4 类 6 态」 —— 保留（与 TDesign `variant` × `theme` 概念同源，只是命名不同）。
- 分页以 `useTablePagination` 为唯一真源 —— 不变（TDesign 的 `pageSizeOptions` 默认值与我们不同，不宜照抄）。

**唯一新增建议**：补 Button 尺寸三档（建议 A 第 1 条），其余按兵不动。

---

## 5. 参考来源

- MasterGo《桌面端组件(通用)》：`mastergo.com/file/172698996235937?page_id=0:194670`
- TDesign Vue Next 官网（1.20.10）：`tdesign.tencent.com/vue-next/components/{table,pagination,dialog,button}`
- Design Token：`tdesign.tencent.com/design/design-token`
- 本项目现状采集：`web/app/package.json`、`web/app/src/**`（2026-10-18 实测）
