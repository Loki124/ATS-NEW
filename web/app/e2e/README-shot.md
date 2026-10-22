# UI 改动的「自证」工具链：截图

> 本文件是 **给 AI/执行者** 看的操作说明。目的：UI 改动**必须有真图背书**，不能只靠静态推理。

## 为什么需要它

2026-10-22 连续三轮 UI 改动（系统切换器 → 人员管理列重排 → 入职日期单元格）**代码看着都对、渲染全错**，
原因无一例外是「**只有静态推理、没有真图**」：

| 现象 | 真实原因 | 静态分析为什么看不出来 |
|------|---------|--------------------|
| 两行日期被排成两列 | `grid-template-columns: auto auto` 是行优先填充 | 读 CSS 语义完全正确 |
| 图标越出高亮块 | 单元格自绘内容的 `padding` 没生效 | 规则在源码里，看得到 |
| 日期在「/」处折行、图标掉到上一行 | 同上（样式压根没命中） | 同上 |
| 弹窗里显示 `:content-style="{...}"` 源码文本 | HTML 注释插在组件标签的**属性列表中间** → Vue 编译器打断属性解析 | 模板能编译、能过 lint |

**根因（最关键的一条）**：`scoped` 样式对 **列 `render` 里 `h()` 动态造的 VNode 完全不命中** ——
Vue 的 `data-v-xxx` 是**编译期给模板里的元素**静态注入的，`h()` 造的元素没有这个属性。
→ 这类单元格样式必须放在**非 scoped** 的 `<style>` 块里。

## 用法

```bash
cd web/app

# 1) 截某个页面（自动签发 dev 会话 → 注入 → 截图）
npm run shot -- /campus/person --out=/tmp/shots

# 2) 截「点了某按钮之后」的状态（弹窗 / 下拉 / 浮出层）
npm run shot -- /campus/person --click="button:has-text('高级筛选')" --name=adv

# 3) 截「悬停后浮出」的状态（注意：**先 click 再 hover**，脚本已按此顺序执行）
npm run shot -- /settings/account --click=".collapse-btn" --hover=".settings-menu .n-submenu" --name=flyout

# 4) 整页截图
npm run shot -- /campus/person --full
```

### 选项

| 选项 | 说明 |
|------|------|
| `--click=<选择器>` | 截图前点击（可重复；**先于 hover 执行**） |
| `--hover=<选择器>` | 截图前悬停（可重复） |
| `--wait=<毫秒>` | 截图前额外等待（默认 1200ms） |
| `--full` | 整页截图（默认只截视口） |
| `--out=<目录>` | 输出目录（默认 `e2e/__shots__`） |
| `--name=<前缀>` | 文件名前缀 |
| `--width` / `--height` | 视口尺寸（默认 1440×900） |
| `SHOT_BASE` | 前端地址（默认 `http://127.0.0.1:5212`） |

## 两个前置条件（踩过的坑）

### 1. 浏览器从哪来 —— 用**系统 Chrome**，不要用 playwright 自带的 chromium

本机 `~/Library/Caches/ms-playwright/` **是空的**（playwright 自带 chromium 未下载），
`chromium.launch()` 会直接报 `Executable doesn't exist` → 这就是过去反复「起不了浏览器」的真因。

```js
// ✅ 驱动系统已装的 Google Chrome，无需下载任何东西
chromium.launch({ channel: 'chrome', args: ['--no-sandbox', '--disable-dev-shm-usage'] })
```

> 若希望改用 playwright 自带 chromium：`npx playwright install chromium`（需联网下载 ~150MB）。

### 2. 登录态从哪来 —— 调后端签发 token，**不要猜密码、不要改用户数据**

`admin/admin123` 已在 2026-10-08 移除（弱口令不再写死），`e2e/auth.setup.ts` 因此**已过期**。
本脚本改为直接调后端 `_issue_login_token(admin)` 签发一对 access/refresh（与登录接口同一套逻辑），
注入 `localStorage` 后访问 —— **只生成 token，不写任何用户数据**：

```js
await context.addInitScript((s) => {
  localStorage.setItem('accessToken', s.access)
  localStorage.setItem('refreshToken', s.refresh)
  localStorage.setItem('user', JSON.stringify(s.user))
}, session)
```

## 量尺寸（比目测准）

需要「某列多宽才不被裁 / 容器到底多宽」时，直接在浏览器里量，别猜：

```js
const info = await page.evaluate(() => {
  const wrap = document.querySelector('.table-wrap')
  const ths = Array.from(document.querySelectorAll('.n-data-table-thead th')).map((th) => ({
    text: th.innerText.trim(), w: Math.round(th.getBoundingClientRect().width),
  }))
  return { client: wrap?.clientWidth, ths }
})
```

实测样例（1440 视口 / 侧栏 64）：表格容器可用 **1344px** —— 列宽合计超过它，末尾列就会被
`fixed:'right'` 的操作列盖住。

### ⚠️ 判「规则有没有命中」要用**非继承属性**（2026-10-22 实测踩坑）

`getComputedStyle` 读出来的值，**有可能来自父级继承而不是你写的规则** —— 这会给出假阳性。

实测反例：`.saturation-cell` 声明 `font-variant-numeric: tabular-nums`，
computed 里是 `tabular-nums`，看着「生效了」；实测却是继承自父级
`.n-data-table-table`（`parentTableFV = "tabular-nums"`）——
该元素**根本没有 `data-v-*` 属性**，scoped 规则压根没命中。

**安全判据**：

```js
// ① 先看规则命中了吗（选择器需要 data-v，但 h() 渲染的元素没有）
el.getAttributeNames().filter(n => n.startsWith('data-v-'))   // h() 渲染 → 空数组 → 未命中

// ② 用非继承属性验证（font-weight / color / display / gap …）
getComputedStyle(el).fontWeight

// ③ 再量几何
el.getBoundingClientRect()
```

**顺序铁律**：**先判「命中」→ 再判「几何」→ 最后才调数值**。
反过来（先调数值）就会出现「连续三轮改 CSS 都没生效」。

## ⚠️ 两个视口不是同一份东西（2026-10-22 实测踩到）

| 视口 | 服务 | 看到的是 | 改代码后要做什么 |
|------|------|---------|----------------|
| **dev** | `http://127.0.0.1:5212` | 源码实时（HMR） | 刷新即可 |
| **:8000** | Django | **`web/app/dist` 的构建产物** | `npm run build` **+** `manage.py collectstatic --noinput` |

- Django 的 SPA fallback 直接读 `web/app/dist/index.html`；
- 而 `/assets/*` 静态资源由 whitenoise 从 `STATIC_ROOT`（`apps/django/staticfiles/`）serve
  → **只 build 不 collectstatic，:8000 仍是旧资源**。
- 一键同步（改完前端后跑这条，:8000 即为最新）：
  ```bash
  npm run build:dist      # = vite build + manage.py collectstatic --noinput
  ```
- 实测踩坑：用户反馈「这里的样式还是错的」，而 dev 视口是对的 —— 查出来 **dist 是前一天 22:51 的旧构建**
  （`.user-menu-row` 还是旧 flex 版 `space-between` → 语言开关被挤出面板被裁），
  源码里早已改成 grid 三列版。**重建 + collectstatic 后 :8000 真图确认修复。**
- 截图脚本用 `SHOT_BASE=http://127.0.0.1:8000` 可直接验证「用户真正看到的那份」。

## 配套的「文档级」检查（静态也能抓的部分）

- **scoped → h() 动态元素**：这类样式放非 scoped 块；用 `getComputedStyle` 验证是否真的命中。
- **组件标签属性中间插注释**：会打断 Vue 模板的属性解析 → 注释一律放在标签**外**。
- 写完用 `npm run shot -- <路由>` 截一张，**肉眼看**再收工。
