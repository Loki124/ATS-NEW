> ⚠️ 已归档于 2026-10-18（UI 文档收敛，见 `UI_DOC_AUDIT_2026-10-18.md`）。
> 本文件为历史诊断 / 走查 / 整改快照，**不再作为规范依据**。
> 当前权威规范见 `UI_DESIGN_SPEC.md`，唯一索引见 `README.md`。

# ATS-NEW 统一 UI 设计系统（液态玻璃 / Liquid Glass）
> 最后更新：2026-09-14（依据 git 最后提交）

> ⚠️ **本文档已废弃（2026-09-10）**：其内容已并入 [`UI_RECONCILIATION.md`](./UI_RECONCILIATION.md)（前端 UI 改造总纲）与 [`UI_DESIGN_SPEC.md`](./UI_DESIGN_SPEC.md)（统一设计规范 v2.2）。仅保留作历史参考，不再维护。

> 状态：**待确认（v1.0-draft）** · 设计系统架构师 Diana · 2026-08-21
> 适用范围：`web/app`（Vue3 + Naive UI + UnoCSS）全部页面与组件。
> 设计参考：Apple Liquid Glass（2025）、Linear（深度与克制）、Stripe（色彩纪律）、Vercel（间距节奏）。
> 治理原则：**单一事实来源 = 本文件 + `src/styles/tokens.css`**。任何组件禁止再硬编码品牌色/模糊值/圆角，统一走 CSS 变量与 Naive UI `themeOverrides`。

---

## 1. Visual Theme & Atmosphere（视觉主题与氛围）

**品牌设计哲学**
ATS-NEW 是腾讯招聘/人才管理后台（B 端、高频、数据密集）。新系统以「液态玻璃」为统一语言：半透明表面 + 柔光晕背景 + 精确高光描边，让信息层浮于有呼吸感的极光背景之上，既专业克制又不呆板。

**视觉基调**：通透、轻盈、有层次；克制的高级感，而非炫技。

**5 个核心视觉特征**
1. **Glass Surfaces** — 半透明白底 + `backdrop-filter` 毛玻璃，配顶部 1px 高光。
2. **Aurora Background** — 冷调极光光斑（靛/紫/青）作全局底色，玻璃才有「可透」的内容。
3. **Soft Elevation** — 多层柔阴影 + 内高光，无硬黑边。
4. **Single Brand Accent** — 全站唯一品牌强调色（靛紫 `#6366F1`），语义色仅用于状态。
5. **Gradient Type** — 页面主标题用品牌渐变文字，正文保持纯墨色保证可读。

**光影与质感倾向**：浅色优先（liquid glass on light aurora）；玻璃用 `blur(16–24px)` + `rgba(255,255,255,.55–.72)`；高光用 `inset 0 1px 0 rgba(255,255,255,.6)`。

> **暗色模式已纳入交付**（见 §2 Dark Mode Token Set）。浅色为默认主题，暗色通过 `body.dark` / `[data-theme="dark"]` 一键切换，**组件 CSS 不变，仅切变量**。品牌色支持运行时自定义换肤（见 §2 可自定义机制）。

---

## 2. Color Palette & Roles（调色板与角色）

所有色值以 HEX + CSS 变量双格式给出。**改品牌色只改 `--brand` 一处**（要切腾讯蓝 `#0052D9` 亦可，见 §9）。

### Primary / Brand（默认推荐 `#6366F1`，支持运行时自定义换肤）
| 角色 | HEX | CSS 变量 | 使用场景 / 派生方式 |
|---|---|---|---|
| Brand | `#6366F1` | `--brand` | 主按钮、激活态、链接、强调。**唯一必填输入** |
| Brand Button | 自动选阶 | `--brand-button` | **实底**（按钮/chip/选中态）。禁止锁 `-500` 阶，见 §4 |
| Brand Hover | 派生 | `--brand-hover` | hover。`color-mix(in oklch, var(--brand-600) 75%, #fff)`（暗色 `var(--brand-300) 78%`） |
| Brand Pressed | 派生 | `--brand-pressed` | active/pressed。`color-mix(in oklch, var(--brand-600) 80%, #000)`（暗色 `var(--brand-300) 80%`） |
| Brand Dark | 派生 | `--brand-dark` | 渐变深端。`color-mix(in oklch, var(--brand-600) 66%, #000)`（暗色 55%） |
| Gradient A | `#A855F7` | `--brand-grad-a` | 标题/按钮渐变中段（默认类比紫，可覆盖） |
| Gradient B | `#EC4899` | `--brand-grad-b` | 标题渐变末段（默认类比粉，仅装饰，可覆盖） |
| Warm | `#FBCE5B` | `--brand-warm` | 暖色实底（通过/优秀档位）。暗色提亮为 `#FCD34D` |
| Warm Soft | `rgba(251,206,91,.15)` | `--brand-warm-soft` | 暖色半透底 |

> ⚠️ 派生色一律用 `oklch` 而非 `srgb`/`hsl`：HSL 的 L 通道非感知均匀，同 L 值下黄与蓝视觉亮度差近一倍，会导致换品牌色后色阶节奏失衡。
> 本表所有 `-600`/`-300` 引用均由 `brand-tokens.mjs` 按品牌色自动生成，**禁止手工编辑**；改品牌色只需改 `--brand` 一个输入。

#### 品牌文字色（作前景用，与实底色严格分离）

| 角色 | CSS 变量 | 浅色（`#6366F1`） | 暗色 | 用途 |
|---|---|---|---|---|
| Brand Fg | `--brand-fg` | `--brand-600` `#5050D1` | `--brand-200` `#B9C7FF` | 强调文字 / 图标 / 链接（压普通表面） |
| Brand Fg Hover | `--brand-fg-hover` | `--brand-pressed` | `--brand-100` `#D0DFFF` | 品牌文字 hover 阶，**保证 hover 后对比度不下降** |
| Brand Fg On Soft | `--brand-fg-on-soft` | `--brand-fg` | `--brand-100` | 品牌字压**品牌半透底**（`--brand-soft` / 玻璃面板合成后） |
| Brand Alt Ink | `--brand-alt-ink` | `#5B32C8` | `#C4A6FF` | 派生型 / 次级强调。`--brand-grad-a` 的**文字化替身** |
| Warm Ink | `--brand-warm-ink` | `#7C2D12` | `#7C2D12`（同值） | 文字压在 `--brand-warm` **实底**上 |
| Warm Deep | `--brand-warm-deep` | `#B45309` | `#FCD34D` | 文字压在 `--brand-warm-soft` **半透底**上 |
| On Brand | `--on-brand` | `#FFFFFF` | `#111827` | 压在 `--brand-button` 实底上的前景 |

**可自定义机制（白标 / 换肤）**
- 品牌色是**唯一外部输入**：改一处即全站换肤（按钮渐变、激活态、链接、玻璃辉光、极光主光斑联动）。
- `--brand-50…--brand-900` 九阶、`--brand-button`、`--brand-fg`、`--brand-hover/pressed/dark` 全部由 `brand-tokens.mjs` 经 **OKLCH 自动生成**，无需手维护。
- 渐变端 `--brand-grad-a/--brand-grad-b` 提供默认类比色；白标场景可整体覆盖为品牌近似色。
- Naive UI `themeOverrides`（`App.vue`）由**同一品牌值**在 JS 计算 primaryColor/hover/pressed，保证原生组件与玻璃类一致。
- 腾讯 CI 备选：`BRAND_COLOR="#0052D9"`（仅改一处，组件 CSS 不动）。

```bash
# 🚫 不要在 :root 手写派生色 —— 会覆盖 brand-tokens.css 的生成产物，
#    且绕开 --ci 门禁，导致换肤后对比度静默不达标。
# ✅ 只改品牌色这一个输入：
BRAND_COLOR="#0052D9" npm run tokens
```

### Neutral / Ink（墨色，替代原 `#1f2937` 深灰侧栏）
| 角色 | HEX | CSS 变量 | 使用场景 |
|---|---|---|---|
| Ink | `#0F172A` | `--ink` | 标题、重要正文 |
| Ink Soft | `#475569` | `--ink-soft` | 次要正文、标签 |
| Ink Faint | `#5B6B84` | `--ink-faint` | 占位符、辅助说明。原 `#94A3B8` 仅 2.6:1；再由 `#64748B` 下调（压 `--g1` 仅 4.34:1）→ 白底 5.41 / `--g1` 4.94:1 |
| Surface | `#FFFFFF` | `--surface` | 不透明兜底表面 |
| Border Hairline | `rgba(15,23,42,.08)` | `--border-hairline` | 实体分隔线 |

### Glass Surfaces（玻璃表面 —— 系统核心）
| 角色 | 值 | CSS 变量 |
|---|---|---|
| 面板底 | `rgba(255,255,255,.55)` | `--glass-bg-panel` |
| 卡片底 | `rgba(255,255,255,.62)` | `--glass-bg-card` |
| 浮起底 | `rgba(255,255,255,.72)` | `--glass-bg-elevated` |
| 输入底 | `rgba(255,255,255,.45)` | `--glass-bg-input` |
| 玻璃描边 | `rgba(255,255,255,.70)` | `--glass-border` |
| 强描边 | `rgba(255,255,255,.90)` | `--glass-border-strong` |

### Semantic Colors（语义色，仅状态，不做品牌）

每族三个色阶：**主色**（装饰/图标/图形）→ **`-deep`**（**文字专用**，两模式各自重排）→ **`-soft`**（浅底）。

| 角色 | 主色 | Deep（文字） | 浅色 Deep | 暗色 Deep | 浅底 |
|---|---|---|---|---|---|
| Success | `#16A34A` | `--c-success-deep` | `#065F46` | `#6EE7B7` | `rgba(22,163,74,.12)` |
| Warning | `#F59E0B` | `--c-warning-deep` | `#92400E` | `#FCD34D` | `rgba(245,158,11,.14)` |
| Error | `#C62828` | `--c-error-deep` | `#991B1B` | `#FCA5A5` | `rgba(239,68,68,.12)` |
| Info | `#3B82F6` | `--c-info-deep` | `#1E40AF` | `#93C5FD` | `rgba(59,130,246,.12)` |

**实底之上的前景色**（`--c-*-deep` 作背景时配对使用，如圆点、实底 chip）：

| CSS 变量 | 浅色 | 暗色 | 实底 → 前景对比度 |
|---|---|---|---|
| `--on-c-success-deep` | `#FFFFFF` | `#0F172A` | 7.68:1 / 11.71:1 |
| `--on-c-warning-deep` | `#FFFFFF` | `#0F172A` | 7.09:1 / 12.38:1 |
| `--on-c-error-deep` | `#FFFFFF` | `#0F172A` | 8.31:1 / 9.41:1 |
| `--on-c-info-deep` | `#FFFFFF` | `#0F172A` | 8.72:1 / 9.90:1 |

> 暗色下 `-deep` 是**亮色**，`#FFFFFF` 前景只有 1.80–1.90:1 —— 故暗色一律 `#0F172A` 深字。

> 🚫 **`--c-*` 主色不得当文字色，也不得当实底色。**
> 主色压自家 `-soft` 底仅约 2.9:1（例 `#16A34A` on `#E3F4E9` = 2.89:1）；主色配白字仅 2.15–4.47:1。
> 文字一律用 `-deep`，实底一律用 `-deep` + `--on-c-*-deep`。

### Shadow Colors
| 角色 | rgba |
|---|---|
| Shadow Soft | `rgba(15,23,42,.08)` |
| Shadow Strong | `rgba(15,23,42,.12)` |
| Glow Brand | `rgba(99,102,241,.32)` |

### Aurora Background（全局底色，替换原纯灰 `#f9fafb` / 纯金 `#FBCE5B`）
基色 `linear-gradient(180deg,#EEF1FB 0%,#E7ECFB 100%)`，叠加 3 个模糊光斑：
- 靛 `radial-gradient(circle, rgba(99,102,241,.30), transparent 65%)`
- 紫 `radial-gradient(circle, rgba(168,85,247,.20), transparent 65%)`
- 青 `radial-gradient(circle, rgba(34,211,238,.16), transparent 65%)`

### Dark Mode Token Set（暗色模式 · 已纳入交付）
通过 `body.dark`（或 `[data-theme="dark"]`）切换。**组件 CSS 不变，仅切变量**——玻璃在暗色极光上呈「拉丝深玻璃」，表现最佳。

| 角色 | 浅色 | 暗色 | CSS 变量 |
|---|---|---|---|
| 墨色 Ink | `#0F172A` | `#E8ECF6` | `--ink` |
| 次墨 | `#475569` | `#AEB8CC` | `--ink-soft` |
| 辅墨 | `#5B6B84` | `#93A0B5` | `--ink-faint`（浅色原 `#64748B` 压 `--g1` 仅 4.34:1；暗色原 `#7C879B` 对 `--surface` 仅 4.04:1） |
| 玻璃面板 | `rgba(255,255,255,.55)` | `rgba(30,41,59,.55)` | `--glass-bg-panel` |
| 玻璃卡片 | `rgba(255,255,255,.62)` | `rgba(30,41,59,.62)` | `--glass-bg-card` |
| 玻璃浮起 | `rgba(255,255,255,.72)` | `rgba(30,41,59,.72)` | `--glass-bg-elevated` |
| 玻璃输入 | `rgba(255,255,255,.45)` | `rgba(30,41,59,.45)` | `--glass-bg-input` |
| 玻璃描边 | `rgba(255,255,255,.70)` | `rgba(255,255,255,.14)` | `--glass-border` |
| 强描边 | `rgba(255,255,255,.90)` | `rgba(255,255,255,.22)` | `--glass-border-strong` |
| 极光基色 | `#EEF1FB→#E7ECFB` | `#0B1020→#111936` | `--aurora-base` |
| 极光光斑 | 靛.30/紫.20/青.16 | 靛.40/紫.30/青.22 | `--aurora-1/2/3` |
| 语义浅底 | `.12` | `.22` | `--c-*-soft` |
| 阴影色调 | 深蓝灰低透 | 纯黑低透 | `--shadow-*`（暗色加深） |

> 暗色模式开关建议持久化（localStorage / 用户设置），并提供「跟随系统」（`prefers-color-scheme`）。品牌自定义与暗色可叠加生效。

---

## 2.5 前景色选阶与文字色禁忌（强制）

品牌色与语义色的**主色是为实底/装饰设计的，直接当文字用会静默不达标**。以下为踩过的坑与唯一正确姿势。

### 选阶规则

- **前景色策略必须先于阶位决定**。否则亮品牌（黄 / 浅绿）被压成褐色、暗品牌被提亮成反常识配色。
- 明度 `baseL > 0.75` 判为亮色品牌 → 固定**深色字**，取最接近 `baseL` 的阶（限制 200–500，避免过浅失去分量）。
- 常规品牌 → 固定**对比色**（浅色模式白字），取「对比度刚好达标」的**最浅**阶。
- 优选区间（浅色 400–800 / 暗色 400–700）无解才扩展到全色阶。
- 由 `brand-tokens.mjs` 自动完成，`--ci` 门禁失败即退出码非 0。

### 🚫 五条硬性禁忌

| # | 禁忌 | 为什么 | 改用 |
|---|---|---|---|
| 1 | 禁止 `--brand` / `--brand-500` 直接当实底 | `#3B82F6` 配白字仅 3.68:1 | `--brand-button` + `--on-brand` |
| 2 | 禁止 `--brand-hover` 当文字色 | 两模式都向白偏，浅色实测 **3.58:1**，hover 后反而比常态更难读 | `--brand-fg-hover` |
| 3 | 禁止 `--c-*` 主色当文字色 | 压自家 `-soft` 底仅约 **2.9:1**；配白字 2.15–4.47:1 | `--c-*-deep` |
| 4 | 禁止 `--brand-grad-a` 当文字色 | `#8C63FA` 仅 **3.98:1**（暗底 3.68:1） | `--brand-alt-ink` |
| 5 | 禁止文字压 `--brand-warm` 实底时用 `--brand-warm-deep` | 暗色下两者**同为 `#FCD34D`** → 对比度 **1.00:1**，文字完全不可见 | `--brand-warm-ink` |

### 颜色语义与色相冲突

品牌色与语义色色相接近时（如品牌橙 vs error 红）语义系统失效。**消解策略是拉开明度（OKLCH ΔL ≥ 0.20），禁止旋转语义色色相** —— 旋转会破坏功能语义（"错误红"变成紫红后用户不再认为它是错误）。拉开明度后必须强制搭配图标。

### 暗色前景色必须反向推导

暗色模式下 `-deep` 阶是**亮色**，前景不能再用白色（仅 1.75:1）。本轮修正涉及：

- `--brand-fg` 暗色阶位由 `300` 改为 **`200`**（选阶参考底由极光深蓝 `#0F172A` 改为 `--surface` `#1E293B`，更贴近真实底色）→ `#B9C7FF`，对暗底 **8.83:1**。
- `--ink-faint` 暗色由 `#7C879B` 改为 **`#93A0B5`**（原值对 `--surface` 仅 4.04:1）。
- `--ink-faint` 浅色由 `#64748B` 改为 **`#5B6B84`**（原值压 `--g1` 仅 4.34:1）；`--g5` 与遗留别名 `--n-350…500` 同值同步。
- ⚠️ `--ink-faint` 与 `--g5` 的值只对**不透明浅色底**成立；Naive 组件走 `themeOverrides` 传值，**不随本令牌变化**（实测 Naive `textColor3` 仍为 `#94A3B8`），见 `T5-design-token-convergence.md` §5.6。

> ⚠️ 这两项是**全局视觉变更**：暗色下所有品牌强调文字与辅助文字都会变亮。改色后必须做全站视觉回归，不得只看单个页面。

---

## 2.6 令牌单一事实源

| 令牌类别 | 权威文件 | 可否手工改 |
|---|---|---|
| 品牌色阶 + 前景选阶 | `web/app/src/styles/brand-tokens.css`（由 `brand-tokens.mjs` 生成） | 🚫 否 |
| 品牌色 TS 常量 | `web/app/src/styles/brand-tokens.gen.ts` | 🚫 否 |
| 语义色 / 中性色 / 间距 / 字号 | `web/app/src/styles/tokens.css` | ✅ 是 |
| 玻璃 / 层级 | `web/app/src/styles/glass.css` | ✅ 是 |

改品牌色只需改**一个输入**：`npm run tokens` 脚本中的 `BRAND_COLOR` 环境变量（或直接 `node brand-tokens.mjs --brand "#XXXXXX"`），其余色阶与前景色自动重算。`--ci` 门禁会对实底前景对比度做校验，不达标即非 0 退出。

```bash
# 换品牌色：改这一处即可
BRAND_COLOR="#0052D9" npm run tokens
```

| 命令 | 用途 |
|---|---|
| `npm run tokens` | 生成 + `--ci` 门禁（**提交前必跑**） |
| `npm run tokens -- --report` | 打印色阶与对比度报告，人工核对 |
| `npm run tokens -- --json` | 输出机器可读格式，供其他工具消费 |

---

## 3. Typography Rules（排版规则）

**Font Family**
- 正文/中文：`"PingFang SC","Microsoft YaHei",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif`
- 等宽：`"SF Mono",Menlo,Monaco,Consolas,monospace`

**Type Scale**（全部走 `src/styles/tokens.css` 变量，禁止页面内硬编码 px）

| Token | 用途 | Size | Weight | Line-height | Letter-spacing |
|---|---|---|---|---|---|
| `--text-display` | Hero 标题 | 2.5rem/40 | 700 | 1.2 | -0.02em |
| `--text-h1` | 页面标题 | 2rem/32 | 700 | 1.25 | -0.01em |
| `--text-h2` | 区块标题 | 1.5rem/24 | 600 | 1.3 | 0 |
| `--text-h3` | 卡片标题 | 1.25rem/20 | 600 | 1.35 | 0 |
| `--text-h4` | 子标题 | 1.125rem/18 | 600 | 1.4 | 0 |
| `--text-body` | 正文 | 0.9375rem/15 | 400 | 1.6 | 0 |
| `--text-small` | 次要 | 0.8125rem/13 | 400 | 1.5 | 0 |
| `--text-meta` | 辅助/标签 | 0.75rem/12 | 500 | 1.4 | 0.02em |

**设计哲学**：字重只用 400/500/600/700 四档；标题靠字重+字号建立层级，不靠颜色；数字用 `font-variant-numeric: tabular-nums` 对齐。

**渐变标题（仅页面/Hero 主标题）**
```css
.gradient-title{
  background:linear-gradient(135deg,var(--brand) 0%,var(--brand-grad-a) 55%,var(--brand-grad-b) 100%);
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;
}
```

---

## 4. Component Stylings（组件样式）

### Buttons（4 变体，全部玻璃化）
```css
/* Primary：玻璃浮起 + 品牌渐变 + 辉光 */
.btn-primary{
  background:linear-gradient(135deg,var(--brand),var(--brand-grad-a));
  color:#fff;border:1px solid rgba(255,255,255,.35);
  border-radius:var(--radius-md);
  padding:10px 18px;font-weight:600;
  box-shadow:0 4px 14px var(--glow-brand), inset 0 1px 0 rgba(255,255,255,.4);
  backdrop-filter:blur(8px);transition:all var(--duration-base) var(--ease-out);
}
.btn-primary:hover{box-shadow:0 6px 20px rgba(99,102,241,.45);transform:translateY(-1px);}
.btn-primary:active{transform:translateY(0);}

/* Secondary：玻璃表面 + 描边 */
.btn-secondary{
  background:var(--glass-bg-card);border:1px solid var(--glass-border);
  color:var(--ink);border-radius:var(--radius-md);padding:10px 18px;
  backdrop-filter:blur(10px);
}
/* hover 文字用 --brand-fg-hover，不用 --brand-hover（后者仅 3.58:1） */
.btn-secondary:hover{border-color:var(--brand-fg);color:var(--brand-fg-hover);}

/* Ghost：透明，仅 hover 浅底 */
.btn-ghost{background:transparent;color:var(--ink-soft);border:1px solid transparent;border-radius:var(--radius-md);}
.btn-ghost:hover{background:rgba(15,23,42,.04);color:var(--ink);}

/* Danger：玻璃错误 —— soft 底必须配 deep 字 */
.btn-danger{
  background:var(--c-error-soft);border:1px solid rgba(239,68,68,.3);
  color:var(--c-error-deep);border-radius:var(--radius-md);padding:10px 18px;
}
```
> Naive UI 按钮：通过 `App.vue` 的 `GlobalThemeOverrides` 把 `primaryColor` 改为 `--brand-button`，文字色取 `--on-brand`（浅色 `#fff` / 暗色 `#111827`），圆角 `var(--radius-md)`；不再使用金色 `#FBCE5B`。

### Cards / Panels（玻璃面板，替换 `card-base` 扁平白卡）
```css
.glass-panel{
  position:relative;background:var(--glass-bg-panel);
  backdrop-filter:blur(var(--glass-blur-panel));-webkit-backdrop-filter:blur(var(--glass-blur-panel));
  border:1px solid var(--glass-border);border-radius:var(--radius-lg);
  box-shadow:var(--shadow-panel);
}
.glass-panel::before{ /* 顶部高光 */
  content:'';position:absolute;inset:0;border-radius:inherit;pointer-events:none;
  background:linear-gradient(180deg,rgba(255,255,255,.55),rgba(255,255,255,0) 40%);
}
.glass-card{ background:var(--glass-bg-card); border-radius:var(--radius-md);
  border:1px solid var(--glass-border); backdrop-filter:blur(var(--glass-blur-card));
  box-shadow:var(--shadow-card); padding:var(--space-4); position:relative; }
```
> 退路：不支持 `backdrop-filter` 的浏览器，`background` 已是不透明白底，可读性与外观不崩。

### Inputs
```css
.glass-input{
  background:var(--glass-bg-input);border:1px solid var(--glass-border);
  border-radius:var(--radius-sm);padding:9px 12px;color:var(--ink);
  backdrop-filter:blur(var(--glass-blur-input));transition:all var(--duration-fast) var(--ease-out);
}
.glass-input:focus{border-color:var(--brand-fg);box-shadow:0 0 0 3px rgba(99,102,241,.18);outline:none;}
::placeholder{color:var(--ink-faint);}
```

### Navigation（玻璃侧栏 + 玻璃顶栏，替换 `#1f2937` 深灰侧栏）
- 侧栏：`.glass-panel` 竖向，背景 `var(--glass-bg-panel)`，**不再用深色实底**；激活项 = `background:rgba(99,102,241,.14)` + 左侧 3px `--brand` accent bar（替换金色 `#FBCE5B` 激活态）。
- 顶栏：固定在内容区顶部，`.glass-panel` 横条 + `position:sticky;top:0;z-index:10`。
- 菜单文字：常态 `var(--ink-soft)`，激活 `var(--brand)`。

### Badges / Tags
```css
.glass-tag{display:inline-flex;align-items:center;padding:2px 10px;border-radius:var(--radius-pill);
  background:var(--glass-bg-card);border:1px solid var(--glass-border);color:var(--ink-soft);
  font-size:var(--text-meta);font-weight:500;}
/* 品牌半透底 → 必须用 --brand-fg-on-soft，不是 --brand-fg，也不是 --brand */
.glass-tag--brand{background:rgba(99,102,241,.12);color:var(--brand-fg-on-soft);border-color:rgba(99,102,241,.25);}
/* 语义 tag：--c-*-soft 底 + --c-*-deep 字（主色仅 2.9:1，禁止使用） */
.glass-tag--error{background:var(--c-error-soft);color:var(--c-error-deep);}
/* 实底 chip：--c-*-deep 底 + --on-c-*-deep 字 */
.chip--error.is-active{background:var(--c-error-deep);color:var(--on-c-error-deep);}
```

### Modals / Dialogs / Drawers
- 遮罩：`background:rgba(15,23,42,.28);backdrop-filter:blur(6px)`（模态毛玻璃）。
- 内容：`.glass-card` 浮起态（`--glass-bg-elevated` + `--shadow-elevated`）。
- 抽屉右侧滑入 + 同玻璃材质；圆角 `var(--radius-lg)`。

### Data Table（玻璃表格，替换 Naive 默认白条纹）
- 容器：`.glass-panel`；表头 `background:rgba(255,255,255,.5)`；行分隔 `1px solid var(--border-hairline)`；hover 行 `background:rgba(99,102,241,.06)`；**禁止斑马纹实底**。
- 操作列按钮用 `quaternary` + `type=primary/error`（文字按钮），不堆实心按钮。

---

## 5. Layout Principles（布局原则）

**Spacing System**：4pt 基数（沿用 `tokens.css`）：`--space-1:4 --space-2:8 --space-3:12 --space-4:16 --space-6:24 --space-8:32 --space-12:48 --space-16:64`。组件内边距统一走变量，禁止 CampusControl 式硬编码 `12px/14px/18px`。

**Grid System**：内容最大宽 `1440px`；主区 `2fr / 1fr`（左主右辅），`≤1100px` 折叠为单列（沿用 Dashboard 现有断点）。

**Container**：`padding: var(--space-6)`（24px）；区块间距 `var(--space-6)`。

**留白哲学**：玻璃表面之间留 `16–24px` 呼吸缝；极光背景透过缝隙可见，营造层次。不堆满。

---

## 6. Depth & Elevation（深度与层级）

**Shadow System**
```css
--shadow-xs:   0 1px 2px rgba(15,23,42,.06);
--shadow-sm:   0 2px 8px rgba(15,23,42,.06);
--shadow-card: 0 8px 32px rgba(15,23,42,.08), inset 0 1px 0 rgba(255,255,255,.6);
--shadow-panel:0 12px 40px rgba(15,23,42,.10), inset 0 1px 0 rgba(255,255,255,.6);
--shadow-elevated:0 16px 48px rgba(15,23,42,.12), inset 0 1px 0 rgba(255,255,255,.7);
--shadow-2xl:  0 28px 72px rgba(15,23,42,.16);
```

**Surface Layers**（背景→表面→浮起→覆盖）
`aurora base` → `--glass-bg-panel` → `--glass-bg-card` → `--glass-bg-elevated` → `modal overlay`。

**Z-index Scale**：`sidebar 10` · `header 20` · `dropdown 1000` · `drawer 1100` · `modal 1200` · `toast 1300`。

**Backdrop Effects**：`--glass-blur-panel:24px; --glass-blur-card:16px; --glass-blur-input:10px; --glass-blur-overlay:6px`。**必须带 `-webkit-backdrop-filter` 前缀**（Safari/微信内置浏览器）。

**暗色模式**：已纳入交付，变量集见 §2 Dark Mode Token Set。切换 `body.dark` 即生效，组件 CSS 不变；阴影在暗色下转纯黑低透。

---

## 7. Do's and Don'ts（设计规范与禁忌）

**Do ✅**
1. 品牌色只用一个 `--brand`（靛紫），语义色只表状态。
2. 所有表面用 `.glass-panel/.glass-card`，背景靠极光透出。
3. 间距/圆角/模糊全部走 `tokens.css` 变量与 `themeOverrides`。
4. 渐变文字仅用于页面/Hero 主标题，正文保持纯墨。
5. `backdrop-filter` 必带 `-webkit-` 前缀，并保留不透明兜底底。
6. 玻璃面板加 `::before` 顶部高光，强化「液态」质感。
7. 数字用 `tabular-nums` 对齐；标题层级靠字重字号。

**Don't ❌**
1. 不得再用金色 `#FBCE5B`、橙色 `#FF7A45` 作为品牌色（仅保留为历史告警，迁移后删除）。
2. 不得深色实底侧栏 `#1f2937` + 金激活态并存于玻璃系统。
3. 不得扁平白卡（`card-base` / `bg-white rounded-xl shadow-sm`）与玻璃混排。
4. 不得硬编码 hex / blur / radius（如 `blur(20px)`、`#6366f1`、`border-radius:18px` 散落组件）。
5. 不得玻璃面板叠不透明白卡（CampusControl 现状：玻璃面板内 Naive 表格仍是实白条纹）。
6. 不得 KPI 行 `repeat(4,1fr)` 无响应式折叠（移动端挤压）。
7. 不得用 `transition:all .2s` 无缓动变量；统一 `var(--ease-out)`。

---

## 8. Responsive Behavior（响应式行为）

**Breakpoints**
| 名 | min-width | 说明 |
|---|---|---|
| sm | 640px | 手机横屏 |
| md | 768px | 平板 |
| lg | 1024px | 小桌面 |
| xl | 1280px | 桌面 |
| 2xl | 1536px | 宽屏 |

**Touch Targets**：最小 `44×44px`（按钮/菜单项）。

**折叠策略**
- KPI 行：4 列 → `lg` 2 列 → `sm` 1 列。
- Dashboard 主区：左主右辅 `2fr/1fr` → `≤1100px` 单列。
- 侧栏：`<lg` 可收起为图标栏（沿用现有 collapse）。
- Hero：`<768px` 标题与搜索纵向堆叠。

**Font Scaling**：`--text-body` 在 `<sm` 升至 `1rem/16` 提升移动可读；Display 在 `<md` 降至 `2rem`。

---

## 9. Agent Prompt Guide（AI 代理提示指南）

**Quick Reference**：品牌 `--brand:#6366F1`（唯一输入，hover/pressed/dark 经 `color-mix` 自动派生）；玻璃 `--glass-bg-card/.62 + blur(16px) + border rgba(255,255,255,.7) + 顶部高光`；极光底 `linear-gradient(180deg,#EEF1FB,#E7ECFB)`；圆角 `--radius-md:16px`；间距 4pt。**换肤只动 `--brand` 一处**（切腾讯蓝 `#0052D9` 同理）；**暗色加 `body.dark`**。

**Component Prompts（可直接复制）**
1. 「生成一个 `.glass-card` 统计卡，含标签+大数字+趋势 pill，使用 `--brand` 主色与 `--text-h2` 数字，hover 浮起。」
2. 「把 Naive `n-data-table` 包进 `.glass-panel`，表头半透明白、行 hairline 分隔、hover 行品牌浅底，去掉斑马纹。」
3. 「写一个玻璃主按钮 `.btn-primary`：品牌渐变 + 辉光 + `backdrop-filter:blur(8px)`，hover 上移 1px。」
4. 「把左侧深色侧栏改成 `.glass-panel` 竖向玻璃，激活项用 `rgba(99,102,241,.14)` + 3px 品牌 accent bar。」
5. 「生成全局极光背景层 `.app-aurora`（3 个模糊光斑），固定在 `body` 之后、`app` 之前，z-index 0。」
6. 「写一个玻璃输入框 `.glass-input`，focus 时 3px 品牌辉光环。」

**Iteration Guide（8 条）**
1. 先定 `--brand` 与极光，再调玻璃透明度——背景不对，玻璃全废。
2. 每加一个玻璃层，确认其下方有极光/内容可透，否则退化为白卡。
3. 玻璃 + 文字对比度：浅底玻璃上墨色 `#0F172A` 始终 ≥ WCAG AA。
4. 渐进迁移：先统一 token 与 themeOverrides（全局生效），再逐页替换 `card-base` → `.glass-card`。
5. 不改 Naive 组件源码，只在 `GlobalThemeOverrides` 与包裹层 class 调整，避免升级冲突。
6. 每改一处硬色值，回到 `tokens.css` 抽成变量，保持单一事实来源。
7. 移动端务必检查 `backdrop-filter` 性能与折叠；低端机可降 blur 至 10px。
8. 灰度验证：先 CampusControl（已实现玻璃）对齐本规范，再外推到其他页，减少返工。
