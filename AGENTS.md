name: ui-interaction-constraints
description: 生成或修改任何 UI 界面代码时必须遵守的交互、视觉、品牌色与容错约束。适用于前端组件、页面、样式文件。
globs:
  - "/*.tsx"
  - "/*.jsx"
  - "/*.vue"
  - "/*.html"
  - "/*.css"
  - "/*.scss"
  - "/*.svelte"
  - "/tokens*.css"
alwaysApply: false
priority: 100
version: 2.0.0
tools:

## brand-tokens: node brand-tokens.mjs --brand  [--out ] [--report] [--json] [--ci]

# UI 交互约束规范（Agent-Readable）

本文件为机器约束文件，不是设计教程。关键词遵循 RFC 2119（全大写才具约束力）。

执行前提：任何 UI 代码生成任务开始前先读取本文件；交付前完成第 7 节自检并输出自检结果表。
本文件是唯一权威源，品牌色令牌 MUST 由第 4 节的 CLI 生成，MUST NOT 手工编写。

## 0. 分级体系

### 0.1 优先级

| 级别 | 名称 | 含义 |
|---|---|---|
| P0 | 阻断级 | 违反则不得交付，必须先修复 |
| P1 | 系统级 | 违反则需在交付说明中显式标注原因 |
| P2 | 禁止级 | 反模式黑名单，检测到即视为缺陷 |

### 0.2 可验证性（决定自检时该输出什么）

编写代码的 agent 没有渲染器。要求它对"320px 无横向滚动""对比度达标""眯眼测试"打勾，只会产出全勾的仪式表，零信息量。

| 标记 | 含义 | 自检时该怎么做 |
|---|---|---|
| [S] static | lint / AST / CLI 可静态判定 | MUST 判定并给出依据（文件:行、lint 输出或命令退出码） |
| [R] runtime | 需浏览器渲染后测量 | MUST NOT 打勾。MUST 输出 未验证，需运行时工具 |
| [H] human | 需人眼 / 主观判断 | MUST NOT 打勾。MUST 输出 需人工确认 |

禁止验证剧场：对 [R] / [H] 项输出 ✅ 视为违规。

## 1. 设计令牌（Token）

R-001 [P1][S] 编写任何样式前 MUST 先具备完整令牌，MUST NOT 在组件内硬编码原始数值。

品牌色令牌 MUST NOT 手工编写 —— MUST 由 R-214 的 CLI 生成。以下仅为结构示意：

:root {
  /* 间距：8px 基线 */
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px;
  --space-5: 20px; --space-6: 24px; --space-8: 32px; --space-10: 40px;
  --space-12: 48px; --space-16: 64px;

  /* 字号刻度 */
  --text-xs: 12px; --text-sm: 14px; --text-base: 16px; --text-lg: 18px;
  --text-xl: 20px; --text-2xl: 24px; --text-3xl: 32px; --text-4xl: 48px;

  /* 品牌色 —— 由 brand-tokens.mjs 生成，禁止手写 */
  --brand-h: 39.23; --brand-c: 0.1926;
  --brand-50: #ffddc0; /* … 至 --brand-900 */
  --brand-button: var(--brand-600);   /* 自动选阶，禁止锁 -500 */
  --on-brand: #ffffff;
  --brand-text: #b62d00;

  /* 语义色：独立于品牌色，禁止由其推导（R-211） */
  --color-success: #22c55e; --color-warning: #f59e0b;
  --color-error: #ef4444;   --color-info: #3b82f6;

  /* 中性色 */
  --color-text-primary: #111827;   --color-text-secondary: #6b7280;
  --color-text-tertiary: #9ca3af;  --color-text-disabled: #d1d5db;
  --color-bg: #ffffff; --color-bg-subtle: #f9fafb; --color-border: #e5e7eb;

  /* 动效 */
  --dur-fast: 120ms;   /* hover / 点击反馈 */
  --dur-base: 220ms;   /* 出现 / 消失 */
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
}

/* 深色模式中性色：MUST 单独定义，MUST NOT 反转浅色值。品牌色见 R-212 */
:root[data-theme='dark'] {
  --color-text-primary: #f9fafb;   --color-text-secondary: #9ca3af;
  --color-text-tertiary: #6b7280;  --color-text-disabled: #4b5563;
  --color-bg: #111827; --color-bg-subtle: #1f2937; --color-border: #374151;
  --color-success: #4ade80; --color-warning: #fbbf24;
  --color-error: #f87171;   --color-info: #60a5fa;
}

## 2. P0 阻断级约束

### R-101 [P0][S] 交互组件必须实现完整状态

每个可交互组件 MUST 实现：default / hover / active / focus-visible / loading / disabled。
异步提交类组件 MUST 在 loading 期间设置 disabled，防止重复提交。

// ❌ 违规：无 loading、无 disabled，可重复提交
<button onClick={submit}>提交</button>

// ✅ 正确
<button
  onClick={submit}
  disabled={isSubmitting || !isValid}
  aria-busy={isSubmitting}
  className={cn('btn', isSubmitting && 'btn--loading')}
>
  {isSubmitting ? <><Spinner /> 保存中…</> : '创建项目'}
</button>

.btn:focus-visible { outline: 2px solid var(--brand-button); outline-offset: 2px; }
.btn:disabled { opacity: .5; cursor: not-allowed; }

### R-102 [P0][R] 触控目标 ≥ 44×44px

图标按钮视觉尺寸不足时 MUST 用 padding 或伪元素扩大命中区。

.icon-btn { width: 32px; height: 32px; position: relative; }
.icon-btn::after { content: ''; position: absolute; inset: -6px; }  /* 扩至 44px */

命中区必须渲染后测量（含伪元素），故为 [R]。

### R-103 [P0][R] 320px 视口无横向溢出

MUST NOT 使用固定像素宽度容器。

/* ❌ 违规 */ .card { width: 380px; }
/* ✅ 正确 */ .card { width: 100%; max-width: 380px; }
.container { max-width: 1280px; margin-inline: auto; padding-inline: var(--space-4); }

### R-104 [P0][S] 异步操作必须提供四类反馈

任何异步操作 MUST 覆盖：加载 / 空态 / 成功 / 失败。MUST NOT 出现静默失败。

### R-105 [P0][S] 用户输入不得丢失

核心逻辑：草稿安全是"不打断用户"的前提。草稿在 → 离开即安全 → 无需确认框。

预计填写时间 > 1 分钟的表单 MUST 自动保存草稿：

- 保存介质 MAY 为 localStorage；MUST 设置 TTL ≤ 24h，提交成功后 MUST 立即清除
- 返回时 MUST 提示 已恢复上次填写的内容，并提供 清空 出口
- MUST NOT 弹二次确认框 —— 草稿已存在时弹窗即违反 R-106
useEffect(() => {
  if (hasSensitiveField(values)) return;
  const id = setTimeout(() => saveDraft(draftKey, values, { ttl: 86_400_000 }), 800);
  return () => clearTimeout(id);
}, [values]);

if (restoredDraft) toast('已恢复上次填写的内容', {
  action: { label: '清空', onClick: clearDraft },
});

敏感字段 MUST NOT 进入任何持久化介质（localStorage / sessionStorage / IndexedDB / 服务端草稿接口）：

password  newPassword  currentPassword  confirmPassword
cardNumber  cvv  cvc  expiry  idCard  passport  ssn
otp  smsCode  captcha  token  apiKey  secret  securityAnswer

检测 MUST 采用字段名匹配 + 输入类型匹配双保险；任一命中即整体禁用该表单草稿功能（不逐字段过滤，避免部分落盘）。

const SENSITIVE_KEY = /password|passwd|cvv|cvc|card|idcard|passport|ssn|otp|smscode|captcha|token|apikey|secret/i;
const hasSensitiveField = (v: object) => Object.keys(v).some(k => SENSITIVE_KEY.test(k));
// 模板层 MUST 同步校验：存在 input[type=password] 的表单整体禁用草稿

注：Chrome / Firefox / Safari 均已不再显示 beforeunload 自定义文案，MUST NOT 依赖它传递信息。

### R-106 [P0][S] 破坏性操作必须可撤销

按破坏性分级处理，MUST NOT 对所有删除一律使用确认弹窗。

| 级别 | 处理方式 |
|---|---|
| 可逆（点赞/收藏/开关/归档） | 直接执行 + 乐观更新，禁止确认弹窗 |
| 中等（删除单条/移动） | 直接执行 + Toast 撤销（停留 5–8s） |
| 高（批量删除/清空） | 确认框，文案说明具体后果与影响范围 |
| 不可逆（支付/发布） | 确认框 + 影响预览 + 二次验证 |

toast('已删除「Q3 财务报表」', {
  action: { label: '撤销', onClick: () => restore(id) },
  duration: 8000,
});

### R-107 [P0][S] 用户输入必须转义

MUST NOT 将未净化输入通过 dangerouslySetInnerHTML / innerHTML / v-html 输出。

// ❌ 违规
<div dangerouslySetInnerHTML={{ __html: userInput }} />
// ✅ 正确：默认文本渲染即转义
<div>{userInput}</div>

### R-108 [P0][S] 长列表必须虚拟化或分页

渲染条目 > 200 时 MUST 使用虚拟滚动或分页。

### R-109 [P0][R] 无障碍基线

对比度（WCAG 2.1 AA）：

- 常规文本 MUST ≥ 4.5:1
- 大文本 MAY 放宽至 3:1，但 MUST 严格满足以下任一条件：
  - 字号 ≥ 24px（18pt），或
  - 字号 ≥ 18.66px（14pt）且 font-weight ≥ 700（bold）

⚠️ 高频误判：19px 常规字重不属于大文本，MUST 仍按 4.5:1 校验。
字号 ≥18.66px 只是必要条件，加粗才是豁免前提。

焦点与语义：

- 所有交互元素 MUST 可通过 Tab 访问；焦点顺序 MUST 跟随 DOM 顺序；DOM 顺序 MUST 与单一阅读顺序一致
- 响应式下 MUST NOT 通过 order / grid-template-areas 重排可聚焦元素的相对顺序（DOM 顺序固定而视觉顺序随断点变化，二者会冲突；视觉重排 MAY 用于非交互元素）
- MUST NOT 使用 tabindex > 0
- 错误信息 MUST NOT 仅依赖颜色表达（颜色 + 图标 + 文字，至少两种）
- 交互元素 MUST 使用语义化标签（<button> / <a> / <h1>–<h6>）
- 图片 MUST 提供 alt；纯装饰图标 MUST 设 aria-hidden="true"

### R-110 [P0][S] 动态文本不得撑破布局

.text  { overflow-wrap: anywhere; word-break: break-word; }
.ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.clamp-3 {
  display: -webkit-box; -webkit-line-clamp: 3;
  -webkit-box-orient: vertical; overflow: hidden;
}

截断内容 MUST 提供查看完整信息的途径（title 属性 或 展开按钮）。

### R-111 [P0][S] 数据视图必须实现完整状态机

每个数据视图 MUST 覆盖以下状态，MUST NOT 只实现"有数据"的 happy path：

首次使用引导 骨架屏加载 有数据 空态 搜索无结果 筛选无结果 部分失败 全部失败 离线 无权限 已达上限

部分失败为最高频遗漏项：成功项 MUST 正常展示，失败项 MUST 就地提供重试入口。

{items.map(item => item.error
  ? <ErrorRow key={item.id} error={item.error} onRetry={() => retry(item.id)} />
  : <DataRow key={item.id} data={item} />
)}

## 3. P1 系统级约束

### R-201 [P1][R] 断点：三档 + 流式网格

< 768px    手机：单列
768–1024px 平板：2 列
> 1024px   桌面：3–4 列 + max-width 限宽

/* MUST 优先使用免媒体查询的流式网格 */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-6);
}

验收宽度：320px / 768px / 1200px 三档 MUST 全部验证。

### R-202 [P1][H] 一屏一主角

每个视图 MUST 恰好有 1 个 primary action（实心按钮），其余 MUST 降级为 ghost / text button。
危险操作 MUST 与主操作保持 ≥ 32px 距离并视觉隔离。

眯眼测试（需人眼）：界面缩至 25% 时 MUST 只有一个元素最突出。

### R-203 [P1][S] 错误三段式

MUST 包含：① 人话描述发生了什么 → ② 用户数据是否安全 → ③ 至少一个可点击的恢复动作。
技术错误码 MUST 折叠在"详情"中并支持一键复制。MUST NOT 以"抱歉"开头。

❌ Error: ECONNRESET 500        ❌ 操作失败
✅ 没连上服务器，你填的内容已存在本地。 [重试] [复制错误信息]

### R-204 [P1][S/H] 微文案规则

- 按钮 MUST 使用「动词 + 宾语」描述动作结果，中文 2–6 字。MUST NOT 使用"提交/确定/是/否/OK"
- 确认框 MUST 说明具体后果，而非询问是否确认
- 人称 MUST 统一使用"你"，MUST NOT 使用"您"（政务 / 严肃金融场景除外）
- 时间 MUST 使用相对格式（3 分钟前）+ hover 显示绝对时间
- 加载文案 MUST 具体化（正在上传 3 个文件（2/3）），MUST NOT 使用"加载中…"
- 动态数字 MUST 应用 font-variant-numeric: tabular-nums 防抖动

| 反例 | 正例 |
|---|---|
| 提交 | 创建项目 |
| 确定 | 删除这 3 个文件 |
| 确认删除？ | 删除「Q3 财务报表」？删除后 30 天内可从回收站恢复。 |

### R-205 [P1][S] 感知性能

| 耗时 | 处理 |
|---|---|
| < 100ms | MUST 有即时视觉反馈（按下态 / 高亮） |
| 100–300ms | MUST NOT 显示任何加载态（避免闪烁） |
| 300ms–1s | MUST 显示骨架屏（优先于 spinner） |
| 1–10s | MUST 显示具体进度（已上传 3/10） |
| > 10s | MUST 可后台运行 + 可取消 + 完成后通知 |

const showSkeleton = useDelayedFlag(isLoading, 300); // 300ms 内返回不显示

乐观更新 MUST 仅用于可逆操作（点赞 / 收藏 / 开关 / 排序），MUST NOT 用于支付 / 删除 / 表单提交。

### R-206 [P1][S] 动效规范

- MUST 只动画 transform 与 opacity。MUST NOT 动画 width / height / top / left / margin
- 时长 MUST 分场景：hover / 点击反馈 100–150ms；元素出现 / 消失 200–300ms
- MUST 尊重 prefers-reduced-motion
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
}

### R-207 [P1][R] 真实数据边界

MUST 验证：超长文本（20+ 字姓名）/ 超短（1 字）/ 纯 emoji / 0 条 / 1 条 / 10000 条 / 空头像 / 图片加载失败 / 慢速 3G / 断网 / 无权限 / 登录态过期。
图片 MUST 有占位兜底，MUST NOT 加载失败后塌成 0 高度。

### R-208 [P1][S] 视觉层级

MUST 通过字号 / 字重 / 颜色 / 间距建立层级。
标题行高 MUST 为 1.2–1.3，正文行高 MUST 为 1.5–1.7。全站字体 MUST NOT 超过 2 种。

## 4. 品牌色系统（Brand Color）

品牌色是唯一必须由外部输入的令牌，其余颜色由它推导或与之解耦。
缺失本节会导致：所有产品长得一样 / 换品牌色要改几百处 / 品牌色与语义色打架 / 对比度静默不达标。

### R-209 [P1][S] 品牌色注入与色阶生成

品牌色 MUST NOT 硬编码为预设色板。MUST 以 OKLCH 定义，仅需色相 --brand-h 与彩度 --brand-c。

为什么 MUST 用 OKLCH 而非 HSL：HSL 的 L 通道不是感知均匀的——hsl(60 100% 50%)（黄）与 hsl(240 100% 50%)（蓝）L 值相同，视觉亮度差一倍。用 HSL 生成色阶，不同色相的产品会得到节奏完全不一致的 9 阶。

import { oklch, formatHex } from 'culori';

const STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900];
const L_LIGHT = [0.97, 0.93, 0.87, 0.78, 0.68, 0.60, 0.51, 0.42, 0.33, 0.25];
const C_LIGHT = [0.55, 0.70, 0.85, 0.95, 1.00, 1.00, 0.95, 0.85, 0.70, 0.60]; // 两端降彩度，免浅阶发灰 / 深阶发脏

export function buildScale(c, h, L, C) {
  return L.map((l, i) => formatHex(oklch({ mode: 'oklch', l, c: c * C[i], h })));
}

输入约束：彩度 c < 0.05（接近灰）时 MUST 提示"该色无法承担品牌识别度"，CI MUST 拦截（R-214）。
无彩色（白 / 灰 / 黑）在 OKLCH 中色相无定义，MUST 将 h 归零而非产生 NaN。

### R-210 [P0][S] 对比度自动达标

这是最高频的静默缺陷：品牌色直接用作按钮背景时对比度常不达标，而视觉上"看起来没事"。

MUST NOT 将前景色写死为白或黑。MUST NOT 固定用 -500 阶。

选阶策略 —— 前景色策略 MUST 先于阶位决定（否则亮色品牌被压成褐色、暗色品牌被提亮成反常识配色）：

- 判定品牌明度 baseL。baseL > 0.75 视为亮色品牌（黄 / 浅绿 / 荧光系）
- 亮色品牌 → 固定深色字，取最接近 baseL 的阶（限制在 200–500，避免过浅失去按钮分量）
- 常规品牌 → 固定对比色（浅色模式白字），取「对比度刚好达标」的最浅阶
- 优选区间（浅色 400–800 / 深色 400–700）无解才扩展到全色阶
const ratio = (a, b) => wcagContrast(a, b);

export function pickButtonPair(scale, mode, baseL, L, AA = 4.5) {
  const bgL = mode === 'light' ? 1.0 : 0.21;
  const PREF = mode === 'light' ? [3,4,5,6,7] : [3,4,5,6];
  const [fgMain, fgAlt] = mode === 'light' ? ['#ffffff', '#111827'] : ['#111827', '#ffffff'];

  const byBg    = idx => [...idx].sort((a,b) => Math.abs(L[a]-bgL)   - Math.abs(L[b]-bgL));
  const byBrand = idx => [...idx].sort((a,b) => Math.abs(L[a]-baseL) - Math.abs(L[b]-baseL));
  const all = L.map((_, i) => i);

  const tryFg = (order, fg) => {
    for (const i of order) if (ratio(scale[i], fg) >= AA)
      return { step: STEPS[i], bg: scale[i], fg, ratio: +ratio(scale[i], fg).toFixed(2) };
    return null;
  };

  if (baseL > 0.75) {                       // 亮色品牌：保留明度 + 深色字
    const bright = [2,3,4,5];
    return tryFg(byBrand(bright), fgAlt) ?? tryFg(byBrand(all), fgAlt) ?? tryFg(byBrand(all), fgMain);
  }
  return tryFg(byBg(PREF), fgMain)          // 常规品牌：深色按钮 + 白字
      ?? tryFg(byBg(all), fgMain)
      ?? tryFg(byBrand(all), fgAlt);
}

实测基准：

| 颜色 | 对比度 | 结论 |
|---|---|---|
| #3b82f6（blue-500） | 3.68 : 1 | ❌ 禁止用作主按钮背景 |
| #2563eb（blue-600） | 5.17 : 1 | ✅ 主按钮默认应取此阶 |
| #1d4ed8（blue-700） | 6.94 : 1 | ✅ 适合 hover / active |

| 品牌色 | 自动选阶结果 | 说明 |
|---|---|---|
| #3b82f6 蓝 | brand-600 + 白字 5.93:1 | 自动跳过不达标的 500 |
| #FFE800 亮黄 | brand-200 + 黑字 12.07:1 | 亮黄走 Snapchat 路线，不被压成褐色 |
| #FF6B35 橙 | brand-600 + 白字 6.24:1 | 与 error 仅差 13.9° → 触发 R-211 |
| #22c55e 绿 | brand-600 + 白字 5.11:1 | 与 success 冲突 → 触发 R-211 |

### R-211 [P1][S] 语义色与品牌色冲突

品牌色与语义色色相接近时语义系统失效——这正是"红色又当错误又当品牌色"的根源。

消解策略 MUST 使用【明度分离】，MUST NOT 旋转语义色色相。

⚠️ 旋转色相会破坏功能色语义——"错误红"被转成紫红/橙红后，用户不再认为它是错误。
正确做法是保留色相，拉开 OKLCH 明度（ΔL ≥ 0.20），并强制搭配图标。

// 色相最小夹角（0–180）。跨 0° 时必须取环形距离
export function hueDelta(h1, h2) {
  const d = Math.abs(h1 - h2) % 360;
  return d > 180 ? 360 - d : d;
}
// hueDelta(350, 10) === 20  ← 常见错误写法会算成 160，导致跨 0° 冲突漏判

export function resolveSemantic(brand, sem, minDelta = 30) {
  if (hueDelta(brand.h, sem.h) >= minDelta) return { ...sem, conflict: false, requiresIcon: false };
  const l = brand.l > 0.5 ? Math.max(0.35, sem.l - 0.20) : Math.min(0.75, sem.l + 0.20);
  return { ...sem, l, conflict: true, requiresIcon: true };
}

铁律：语义色 MUST NOT 由品牌色推导生成。语义色是功能色，色相由人类共识决定（红=错误、绿=成功），MUST NOT 随品牌漂移。冲突时该语义色 MUST 搭配图标。

### R-212 [P1][S] 深色模式品牌色

MUST NOT 直接反转色阶（1 - L）或复用浅色阶——深色背景下高饱和品牌色会产生光晕刺眼（halation）。

深色色阶按「相对深底的对比度」重排：50 = 最低对比（贴近深底）→ 900 = 最高对比（亮）。

const L_DARK = [0.28, 0.32, 0.38, 0.46, 0.56, 0.66, 0.74, 0.80, 0.86, 0.91];
const C_DARK = [0.60, 0.70, 0.85, 0.95, 1.00, 0.95, 0.85, 0.75, 0.65, 0.55]; // 提亮 L、降低 C

深色模式主按钮 MUST 改用 -400/-500 阶配深色前景（#111827），MUST NOT 沿用浅色模式的白字方案。

### R-213 [P1][S] 运行时换肤与多品牌白标

品牌色 MUST 支持运行时替换，替换成本 MUST 为改 1 个变量。

[data-brand='a'] { --brand-h: 217; --brand-c: 0.15; }
[data-brand='b'] { --brand-h: 25;  --brand-c: 0.17; }

- 换肤 MUST NOT 触发组件重渲染（用 CSS 变量，不用 JS 内联样式）
- 换肤后 MUST 重新校验对比度，不达标自动回退阶位
- 白标场景 MUST 将 --brand-h/c 存于主题层，MUST NOT 散落在组件内

### R-214 [P0][S] 令牌生成与 CI 门禁

品牌色令牌 MUST NOT 手工编写。MUST 通过 brand-tokens.mjs 生成并纳入 CI 门禁。

这是让 R-210 / R-211 / R-212 真正生效的唯一手段：手写令牌无法保证对比度，只有生成 + 拦截才闭环。

#### CLI 契约

node brand-tokens.mjs --brand "<hex>" [--out tokens.css] [--prefix brand] [--report] [--json] [--ci]

| 参数 | 含义 |
|---|---|
| --brand <hex> | 品牌色，唯一必需输入 |
| --out <path> | 输出 CSS 路径，默认 tokens.css |
| --prefix <name> | CSS 变量前缀，默认 brand |
| --report | 只输出诊断报告，不写文件 |
| --json | 机器可读报告 → stdout（诊断信息走 stderr） |
| --ci | 门禁模式：不达标 exit 1 |

退出码：0 通过；1 门禁失败（即便失败，JSON 报告仍完整输出到 stdout 便于归档）。

CI 失败条件（任一命中）：

- 品牌色彩度 < 0.05（无法承担识别度，含白 / 灰 / 黑等无彩色）
- 浅色模式主按钮无阶位满足 AA 4.5:1
- 深色模式主按钮无阶位满足 AA 4.5:1
- 浅色模式品牌文本色无阶位满足 AA
- 深色模式品牌文本色无阶位满足 AA

JSON 报告字段（--json）：

{
  brand, oklch: { h, c, l },
  scale: { 50..900 },
  button: { light: { step, bg, fg, ratio }, dark: { … } },
  text:   { light: { step, color, ratio },  dark: { … } },
  semantic: [ { key, hex, conflict, delta, requiresIcon } ],
  warnings: string[],
  ci: { pass: boolean, failures: string[] }
}

#### CI 集成

# .github/workflows/brand-tokens.yml
- name: 生成并校验品牌色令牌
  run: node brand-tokens.mjs --brand "${{ vars.BRAND_COLOR }}" --ci --out src/styles/tokens.css

- name: 归档对比度报告
  if: always()
  run: node brand-tokens.mjs --brand "${{ vars.BRAND_COLOR }}" --json > brand-report.json

// package.json
{
  "scripts": {
    "tokens": "node brand-tokens.mjs --brand \"$BRAND_COLOR\" --ci",
    "tokens:report": "node brand-tokens.mjs --brand \"$BRAND_COLOR\" --report"
  }
}

Agent 行为：生成或改动品牌色后 MUST 执行 --ci，MUST 依据退出码在自检表 S-20 / S-21 给出依据，MUST NOT 凭肉眼断言对比度达标。

## 5. P2 禁止清单（反模式黑名单）

以下模式 MUST NOT 出现。检测到即视为缺陷。

| 编号 | 禁止 | 改为 |
|---|---|---|
| X-01 | 紫蓝渐变 + 发光阴影的 CTA | 纯色填充 + translateY(-1px) hover |
| X-02 | emoji 用作功能图标（🚀 ✨ 💡） | Lucide / Heroicons / Tabler 图标库 |
| X-03 | 静态卡片使用 box-shadow | 1px 边框；阴影仅用于浮层（弹窗 / 下拉 / Toast） |
| X-04 | 魔数间距 / 字号（17px 13.5px） | 使用间距令牌（8 的倍数）与字号刻度 |
| X-05 | 硬编码颜色值散落组件内 | 使用色彩令牌 |
| X-06 | 虚词文案（赋能 / 一站式 / 无缝 / 重新定义 / Welcome to） | 描述具体动作与结果 |
| X-07 | 卡片嵌套卡片 | 扁平化，用间距与分隔线分组 |
| X-08 | 欺骗性设计模式（Deceptive Patterns，即 Dark Patterns：不是深色主题 Dark Mode）——默认勾选 / 隐藏取消入口 / 虚假紧迫感 / 确认纠缠 / 价格障眼法 / 羞辱式挽留文案 | 显式同意、退出路径可见、诚实定价 |
| X-09 | hover 动效时长 > 200ms | 100–150ms |
| X-10 | 红色同时用于"错误"与"强调"；绿色同时用于"成功"与"删除" | 语义色一一对应，禁止复用 |
| X-11 | 仅用 placeholder 充当标签 | MUST 使用可见 <label> |
| X-12 | 固定像素容器宽度导致小屏溢出 | width: 100% + max-width |
| X-13 | 手写品牌色令牌 / 硬编码预设色板 | brand-tokens.mjs 生成（R-214） |
| X-14 | 主按钮锁定 -500 阶配白字 | 自动选阶至对比度 ≥ 4.5:1（R-210） |
| X-15 | 语义色由品牌色推导，或靠旋转色相消解冲突 | 明度分离 + 图标（R-211） |
| X-16 | 深色模式直接反转色阶 | 重排 L / 降低 C（R-212） |

### X-01 品牌渐变例外（Liquid Glass v2 设计语言）

X-01 的「紫蓝渐变 + 发光阴影的 CTA」针对的是廉价 glow-button 反模式（渐变填充与发光阴影叠加）。本项目有意采用 **Liquid Glass v2** 设计语言，其品牌渐变主按钮属于**已批准的设计表达**，豁免 X-01，但须满足以下全部约束，否则仍视为缺陷：

1. **渐变来源合法**：`background` 渐变 MUST 由 `brand-tokens.mjs`（R-214）生成并引用 `--brand` / `--brand-grad-a` 等令牌，MUST NOT 手写色值或自挑色板。
2. **对比度门禁**：前景色 MUST 通过 `brand-tokens.mjs --ci` 退出码 0 验证（≥4.5:1），MUST NOT 凭肉眼判定。
3. **hover 形态**：MUST 使用 `translateY(-1px)` 反馈，**禁止**对 CTA 施加发光 `box-shadow`（glow）。
4. **阴影范围**：`box-shadow` 仅允许用于玻璃浮层（`.glass-panel` / 弹窗 / 下拉 / Toast 的 `--shadow-card` / `--shadow-panel`）；静态卡片与 CTA 自身 MUST NOT 带发光阴影（同时受 X-03 约束）。

> 判定口诀：品牌渐变**填充**合法（须令牌化 + 对比度达标）；**发光阴影**非法（X-01/X-03 双禁）。二者不能叠加。

## 6. 自动化验证

MUST NOT 依赖手写 grep 做验证。 正则子串匹配会系统性漏报，制造虚假的安全感：
grep -vE '(...|40|...)px' 会让 margin: 140px 因包含 40px 而逃逸；
gap: 16px 13px 命中 16px 后整行放行；中文按钮 提交 永远匹配不到 submit；
grep -P 在 macOS/BSD 上不存在。

正确做法：交给基于 AST / 渲染 的专用工具。

### 6.1 安装

npm i -D stylelint stylelint-declaration-strict-value \
         eslint-plugin-jsx-a11y @axe-core/playwright culori

### 6.2 stylelint — 令牌强制（X-04 / X-05 / X-13）

// .stylelintrc.json
{
  "plugins": ["stylelint-declaration-strict-value"],
  "rules": {
    "scale-unlimited/declaration-strict-value": [
      [
        { "property": "/^(margin|padding|gap|row-gap|column-gap|inset|top|right|bottom|left)/",
          "value": "/^var\\(--space-|^0$|^auto$|^inherit$|^calc\\(/" },
        { "property": "/^(color|background|background-color|border|border-color|fill|stroke)/",
          "value": "/^var\\(--|^transparent$|^currentColor$|^none$|^inherit$/" },
        { "property": "/^font-size/", "value": "/^var\\(--text-/" }
      ],
      { "severity": "error", "ignoreFiles": ["**/tokens.css"] }
    ]
  }
}

### 6.3 eslint — XSS / 无障碍（R-107 / R-109）

// eslint.config.js
import jsxA11y from 'eslint-plugin-jsx-a11y';

export default [
  jsxA11y.flatConfigs.recommended,
  {
    rules: {
      'jsx-a11y/alt-text': 'error',
      'jsx-a11y/anchor-is-valid': 'error',
      'no-restricted-properties': ['error',
        { property: 'dangerouslySetInnerHTML', message: 'R-107: 禁止直出未净化 HTML' },
        { object: 'document', property: 'write', message: 'R-107: 禁止 document.write' },
      ],
      'no-restricted-syntax': ['error',
        { selector: "AssignmentExpression[left.property.name='innerHTML']", message: 'R-107' },
      ],
    },
  },
];

### 6.4 axe-core — 运行时（R-109 对比度 / R-102 命中区 / R-103 溢出）

// a11y.spec.ts — 三档视口各跑一遍
import AxeBuilder from '@axe-core/playwright';

for (const vp of [{ width: 320, height: 640 }, { width: 768, height: 1024 }, { width: 1200, height: 900 }]) {
  await page.setViewportSize(vp);
  const { violations } = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();
  expect(violations).toEqual([]);
}

// 命中区（含伪元素扩展，必须渲染后测量）
const small = await page.$$eval('button, a, [role="button"]', els =>
  els.filter(el => { const r = el.getBoundingClientRect(); return r.width < 44 || r.height < 44; })
     .map(el => el.outerHTML.slice(0, 80))
);
expect(small).toEqual([]);

### 6.5 品牌色门禁（R-214）

node brand-tokens.mjs --brand "$BRAND_COLOR" --ci   # exit 1 = 阻断

### 6.6 emoji 图标检测（X-02，跨平台脚本）

grep -P 不可移植，MUST 用 Node 脚本：

// scripts/check-emoji.mjs
import { readdirSync, readFileSync } from 'node:fs';
const RE = /\p{Extended_Pictographic}/u;

const walk = d => readdirSync(d, { withFileTypes: true }).flatMap(e =>
  e.isDirectory() ? walk(`${d}/${e.name}`) : [`${d}/${e.name}`]);

const hits = walk('src').flatMap(f =>
  readFileSync(f, 'utf8').split('\n')
    .map((l, i) => RE.test(l) ? `${f}:${i + 1}` : null).filter(Boolean));

if (hits.length) { console.error('X-02 违规：', hits); process.exit(1); }

## 7. 交付前自检（Self-Check）

完成 UI 代码后 MUST 逐条自检并在交付说明中输出自检结果表。任何 P0 项未通过 MUST NOT 交付。

### 7.1 输出格式

| 项 | 规则 | 级别 | 结论 | 依据 |
|----|------|------|------|------|
| S-01 | 组件 6 态 | P0 | ✅ | src/Btn.tsx:12–18 |
| S-02 | loading 禁用 | P0 | ❌ | src/Btn.tsx:9 缺 disabled → 已修复 |
| S-20 | 主按钮选阶 | P0 | ✅ | brand-tokens --ci exit=0, brand-600 6.24:1 |
| R-03 | 对比度 ≥4.5:1 | P0 | ⚠️ 未验证 | 需 axe 运行时确认 |
| H-01 | 眯眼测试 | P1 | ⚠️ 需人工 | 需人眼确认 |

### 7.2 静态项 [S] — agent MUST 自证并给依据

- [S-01 P0] 交互组件含 default/hover/active/focus-visible/loading/disabled？
- [S-02 P0] 异步提交期间 disabled + aria-busy？
- [S-03 P0] 异步操作覆盖 加载/空/成功/失败 四个分支？
- [S-04 P0] 表单自动保存草稿，且敏感字段已整体豁免？
- [S-05 P0] 草稿 TTL ≤24h 且提交成功后清除？
- [S-06 P0] 破坏性操作按 R-106 四级矩阵处理（非一律确认框）？
- [S-07 P0] 撤销型 Toast duration ≥5s？
- [S-08 P0] 无 dangerouslySetInnerHTML / innerHTML / v-html 直出？
- [S-09 P0] 长列表（>200 条）已虚拟化或分页？
- [S-10 P0] 动态文本有长度防御 CSS，截断处可查看完整内容？
- [S-11 P0] 数据视图状态机分支齐全（含部分失败的重试入口）？
- [S-12 P0] 错误提示为三段式且含可点击恢复动作？
- [S-13 P1] 无魔数间距/字号、无硬编码颜色（stylelint 通过）？
- [S-14 P1] 加载态延迟 300ms 显示？
- [S-15 P1] >1s 操作显示具体进度？
- [S-16 P1] 乐观更新仅用于可逆操作？
- [S-17 P1] 动效仅用 transform/opacity，hover 100–150ms？
- [S-18 P1] 已处理 prefers-reduced-motion？
- [S-19 P0] 品牌色令牌由 brand-tokens.mjs 生成，未手工编写？（X-13）
- [S-20 P0] brand-tokens --ci 退出码为 0？（对比度门禁）
- [S-21 P1] 主按钮未锁定 -500 阶，前景色由算法选定？（X-14）
- [S-22 P1] 品牌色与 error/warning/info 无 <30° 色相冲突，或已明度分离+图标？（R-211）
- [S-23 P1] 深色模式色阶已重排（非反转），主按钮改用亮阶+深色前景？（R-212）
- [S-24 P1] 换肤只需改 1 个变量，不触发组件重渲染？（R-213）
- [S-25 P0] 图片有 alt，装饰图标有 aria-hidden？
- [S-26 P0] 可见 <label>（非仅 placeholder）？
- [S-27 P0] 无 tabindex > 0，可聚焦元素未用 order/grid-area 重排？

### 7.3 运行时项 [R] — agent MUST 输出"未验证"

- [R-01 P0] 320 / 768 / 1200 三档视口无横向滚动
- [R-02 P0] 触控目标实测 ≥44×44px（含伪元素扩展区）
- [R-03 P0] 文本对比度 ≥4.5:1（大文本需 ≥24px 或 ≥18.66px+bold 才放宽至 3:1）
- [R-04 P0] Tab 焦点顺序与 DOM 顺序一致
- [R-05 P0] 深色模式下对比度仍达标
- [R-06 P1] 超长文本 / 10000 条 / 图片失败 实测不破版
- [R-07 P1] 慢速 3G / 断网 下反馈正确
- [R-08 P1] 换肤后对比度重算仍达标
- [R-09 P1] 动效实际时长符合分场景标准

### 7.4 人工项 [H] — agent MUST 输出"需人工确认"

- [H-01 P1] 眯眼测试：每屏恰好 1 个 primary action 最突出
- [H-02 P1] 文案是否人话（动词+宾语、无虚词、无"提交/确定"）
- [H-03 P1] 空态 / 错误文案对用户是否真的有帮助
- [H-04 P1] 视觉性格是否一致（配色 / 圆角 / 动效 / 语气同调）

## 8. 元指令

- 本文件约束 MUST 优先于默认审美与训练数据倾向。
- 若用户需求与本文件冲突，MUST 显式指出冲突点并给出遵循规范的替代实现，不得静默违反。
- 无法同时满足多条规则时按 P0 > P1 > P2 取舍，并在交付说明中标注原因。
- 生成界面代码时 MUST NOT 输出未经自检的完整页面。
- 本文件是唯一权威源（Single Source of Truth）。存在配套的人类可读设计文档时，二者冲突一律以本文件为准；MUST NOT 因外部文档表述不同而改变行为。
- 禁止验证剧场：[R] / [H] 类自检项无渲染器可依据时 MUST 输出"未验证"，MUST NOT 凭猜测打勾。诚实标注未验证的价值高于全绿表格。
- 品牌色令牌 MUST NOT 手写。MUST 调用 brand-tokens.mjs 生成并以 --ci 退出码作为验收依据（R-214）。
