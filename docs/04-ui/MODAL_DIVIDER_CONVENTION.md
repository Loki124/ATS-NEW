# 弹窗分隔线规范（Modal Divider Convention）

> 适用范围：所有 `preset="card"` 的 `<n-modal>`（含 `<n-drawer>` 同理）。
> 关联代码：`web/app/src/styles/glass.css` 的「弹窗统一」段 + 本规范。

## 结论（一句话）

**每个弹窗的顶部、底部各处，只能有「一条」分隔线。** 顶部 = header 底边线；底部 = footer 顶边线。

## 根因（为什么会出现「两条线」）

本项目的 `glass.css` 为所有 `.n-modal` 统一提供：

- `.n-modal .n-card-header { border-bottom: 1px solid var(--border-hairline); }`  ← 顶部第 1 条
- `.n-modal .n-card__footer { border-top: 1px solid var(--border-hairline); }`   ← 底部第 1 条

而 Naive UI 的 `:segmented="{ content: 'soft', footer: 'soft' }"` 会在卡片根元素上加
`n-card--content-soft-segmented` / `n-card--footer-soft-segmented` 修饰类，其 cssr 规则
（naive `card/src/styles/index.cssr.mjs`）会**再**给 `.n-card-content:not(:first-child)` 和
`.n-card__footer:not(:first-child)` 各加一条 `border-top`。

结果：

- **顶部**：header 的 `border-bottom` + content 的 `border-top`（content 是 header 之后的非首个子元素，二者为**相邻两个元素**）→ **双线**。这是真实出现的「弹窗顶部分割线两条线」问题，必须修。
- **底部**：footer 的 `border-top` 来自「全局 `.n-modal .n-card__footer`」与「footer-segmented cssr」**两条规则，但指向同一元素的同一 `border-top` 属性** → 最终只渲染为**一条线**，天生不会叠成双线。故底部**不需要**中和；若误对 footer 也设 `border-top:none`，反而会把这唯一的分隔线整条删掉（实测 `footerBorderTop=0px` 即为此误修，已回退）。

## 修复手段（已落地，勿回退）

在 `glass.css` 中**只**中和 Naive 加在 `content` 上的那一条 `border-top`（顶部双线的来源）：

```css
.n-card.n-modal.n-card--content-segmented        > .n-card-content,
.n-card.n-modal.n-card--content-soft-segmented   > .n-card-content {
  border-top: none;
}
```

- 顶部：中和后只剩 header 的 `border-bottom` 一条线。
- 底部：**保留** `glass.css` 的 `.n-card__footer { border-top }` 作为 footer 唯一分隔线（不动 footer）。
选择器特异性 `(0,4,0)` 高于 Naive `(0,2,0)`，不依赖样式注入顺序。

## 防回归守则（新增/修改弹窗时必读）

1. **不要**再为「分隔线」新增 `border`。`glass.css` 已对 `.n-modal` 全局兜底。
2. 弹窗可以继续用 `:segmented="{ content:'soft', footer:'soft' }`（其 soft 仅调整 padding/margin，
   不再贡献额外边框线）——但**不要**为了「加一条线」而引入 segmented，也**不要**手写 border 去叠。
3. 若某弹窗需要「无顶/无底分隔线」的特殊版式，在该弹窗作用域内**显式覆盖**（特指名 selector），
   而不是改全局规则。
4. 验收红线：**真机截图**里每个弹窗顶部/底部只能看到一条线；若看到两条，先查：
   - 是否给弹窗加了 `:segmented` 且上面这条中和规则被更高特异性覆盖；
   - 是否在组件 scoped 样式里手动加了 `border-top/bottom` 与全局线重叠。

## 真机验收方法

用 `ats-new-ui-runtime-verify` 技能取浏览器实测：

```js
const r = await page.evaluate(() => {
  const m = [...document.querySelectorAll('.n-modal')].pop()
  const cs = el => el ? getComputedStyle(el) : null
  const header = m.querySelector('.n-card-header')
  const content = m.querySelector('.n-card-content')
  const footer  = m.querySelector('.n-card__footer')
  return {
    headerBorderBottom: cs(header)?.borderBottomWidth + ' ' + cs(header)?.borderBottomColor,
    contentBorderTop:   cs(content)?.borderTopWidth + ' ' + cs(content)?.borderTopColor,
    footerBorderTop:    cs(footer)?.borderTopWidth + ' ' + cs(footer)?.borderTopColor,
  }
})
// 期望: headerBorderBottom=1px、contentBorderTop=0px、footerBorderTop=1px
```

判读：

| 字段 | 期望 | 异常含义 |
|---|---|---|
| `headerBorderBottom` | `1px` | 顶部分隔线存在 |
| `contentBorderTop` | `0px` | 中和生效，无第二条顶线 |
| `footerBorderTop` | `1px` | 底部分隔线存在且唯一 |
