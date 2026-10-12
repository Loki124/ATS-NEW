#!/usr/bin/env node
/**
 * brand-tokens.mjs — 品牌色令牌生成器（AGENTS.md §4 R-209..R-214）
 * ---------------------------------------------------------------
 * 唯一事实来源：AGENTS.md。品牌色 MUST NOT 手写，MUST 由本脚本生成。
 *
 * 设计要点：
 *   R-209  OKLCH 定义品牌色，仅色相 --brand-h 与彩度 --brand-c 为输入；
 *         生成 50..900 感知均匀色阶（L/C 两端收敛，免浅阶发灰 / 深阶发脏）。
 *   R-210 主按钮自动选阶至对比度 ≥ 4.5:1，禁止锁死 -500 + 白字。
 *   R-211 品牌色与语义色（success/warning/error/info）色相 < 30° 视为冲突，
 *         报告并提示用明度分离 + 图标消解（不旋转语义色相）。
 *   R-212 暗色模式重排 L / 降低 C，禁止 (1-L) 反转或复用浅色阶（防光晕）。
 *   R-213 运行时换肤成本 = 改 1 个变量（--brand / --brand-h / --brand-c）。
 *   R-214 令牌 MUST 由本脚本生成并纳入 CI；--ci 退出码作为验收依据。
 *
 * 用法：
 *   node brand-tokens.mjs --brand "#6366F1" [--out src/styles/brand-tokens.css]
 *                          [--prefix brand] [--report] [--json] [--ci]
 *
 *   --brand <hex>   单一输入色（#rgb / #rrggbb，可带 #）。默认 #6366F1。
 *   --out   <file>   CSS 输出路径（相对脚本目录）。默认 src/styles/brand-tokens.css。
 *   --prefix <p>    令牌前缀。默认 brand。
 *   --report        打印人类可读报告（对比度 / 选阶 / 冲突）。
 *   --json          打印 JSON 报告到 stdout（不影响 --out 写入）。
 *   --ci            门禁模式：跑 c<0.05 拦截 + 对比度门禁 + 提交文件新鲜度 diff，
 *                  任一失败 exit 1。不写文件（除非同时给了 --out 且非 --ci）。
 */

import { oklch, formatHex, parse, rgb } from 'culori';
import { writeFileSync, readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ---------- CLI 解析 ----------
function parseArgs(argv) {
  const args = { brand: '#6366F1', out: 'src/styles/brand-tokens.css', outTs: 'src/styles/brand-tokens.gen.ts', prefix: 'brand', report: false, json: false, ci: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--brand') args.brand = argv[++i];
    else if (a === '--out') args.out = argv[++i];
    else if (a === '--out-ts') args.outTs = argv[++i];
    else if (a === '--prefix') args.prefix = argv[++i];
    else if (a === '--report') args.report = true;
    else if (a === '--json') args.json = true;
    else if (a === '--ci') args.ci = true;
    else { console.error(`未知参数: ${a}`); process.exit(2); }
  }
  return args;
}

// ---------- 颜色工具 ----------
function hexToRgbChannels(hex) {
  const c = rgb(hex);
  if (!c) throw new Error(`无法解析颜色: ${hex}`);
  return [c.r * 255, c.g * 255, c.b * 255];
}
function relLum([r, g, b]) {
  const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}
function contrast(h1, h2) {
  const L1 = relLum(hexToRgbChannels(h1));
  const L2 = relLum(hexToRgbChannels(h2));
  const a = Math.max(L1, L2), b = Math.min(L1, L2);
  return (a + 0.05) / (b + 0.05);
}
function ringHueDelta(h1, h2) {
  let d = Math.abs(((h1 % 360) + 360) % 360 - (((h2 % 360) + 360) % 360));
  return d > 180 ? 360 - d : d;
}

// R-209 色阶生成（感知均匀 L/C 两端收敛）
const STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900];
const L_LIGHT = [0.97, 0.93, 0.87, 0.78, 0.68, 0.60, 0.51, 0.42, 0.33, 0.25];
const C_LIGHT = [0.55, 0.70, 0.85, 0.95, 1.00, 1.00, 0.95, 0.85, 0.70, 0.60];
// R-212 暗色重排：更高 L 保证暗底可见，更低 C 防光晕（非 1-L 反转）
const L_DARK = [0.86, 0.80, 0.73, 0.65, 0.58, 0.51, 0.44, 0.38, 0.32, 0.27];
const C_DARK = [0.26, 0.36, 0.46, 0.52, 0.52, 0.48, 0.43, 0.38, 0.33, 0.28];

function buildScale(c, h, L, C) {
  return STEPS.map((step, i) => ({
    step,
    l: L[i],
    hex: formatHex(oklch({ mode: 'oklch', l: L[i], c: c * C[i], h })),
  }));
}
function scaleToObj(scale) {
  const o = {};
  for (const { step, hex } of scale) o[step] = hex;
  return o;
}

// 语义色相（人类共识，色相由共识决定，不随品牌漂移）
const SEMANTIC = [
  { name: 'success', hue: 142 },
  { name: 'warning', hue: 40 },
  { name: 'error', hue: 25 },
  { name: 'info', hue: 220 },
];

function generate({ brand, prefix = 'brand' }) {
  const P = prefix;
  // 解析输入 → OKLCH
  const base = oklch(brand);
  if (!base) throw new Error(`无法将 "${brand}" 转换为 OKLCH`);
  const h = base.h ?? 0;          // 无彩色归零，避免 NaN
  const c = base.c ?? 0;
  const l = base.l ?? 0;

  const lightScale = buildScale(c, h, L_LIGHT, C_LIGHT);
  const darkScale = buildScale(c, h, L_DARK, C_DARK);
  const scaleLight = scaleToObj(lightScale);
  const scaleDark = scaleToObj(darkScale);

  // R-210 主按钮自动选阶：挑与品牌 L 最接近、且白字对比度 ≥ 4.5 的最亮阶
  const WHITE = '#ffffff';
  const candidates = lightScale
    .map((s) => ({ ...s, ratio: contrast(s.hex, WHITE) }))
    .filter((s) => s.ratio >= 4.5)
    .sort((a, b) => Math.abs(a.l - l) - Math.abs(b.l - l)); // 越接近品牌 L 越优先（升序）
  let buttonStep, buttonBg, buttonFg, buttonRatio;
  if (candidates.length > 0) {
    const sel = candidates[0];
    buttonStep = sel.step; buttonBg = sel.hex; buttonFg = WHITE; buttonRatio = sel.ratio;
  } else {
    // 极端浅色品牌：改用深色前景
    const darkCands = lightScale
      .map((s) => ({ ...s, ratio: contrast(s.hex, '#111827') }))
      .filter((s) => s.ratio >= 4.5)
      .sort((a, b) => b.l - a.l);
    const sel = darkCands[0];
    buttonStep = sel?.step ?? 500; buttonBg = sel?.hex ?? scaleLight[500];
    buttonFg = '#111827'; buttonRatio = sel?.ratio ?? contrast(buttonBg, buttonFg);
  }

  // 暗色主按钮：亮阶 + 深色前景（R-212，禁止沿用浅色白字方案）。
  // 选 L 最接近 0.64 的达标亮阶（既在暗底上发光又保证深色文字可读）。
  const DARK_TARGET_L = 0.64;
  const darkCands = darkScale
    .map((s) => ({ ...s, ratio: contrast(s.hex, '#111827') }))
    .filter((s) => s.ratio >= 4.5)
    .sort((a, b) => Math.abs(a.l - DARK_TARGET_L) - Math.abs(b.l - DARK_TARGET_L));
  const darkButton = darkCands[0] ?? darkScale.find((s) => s.step === 400) ?? darkScale[darkScale.length - 1];
  const darkButtonRatio = darkButton ? contrast(darkButton.hex, '#111827') : 0;

  // 品牌文字（落在浅 brand-soft 底上可读）—— 用最深阶
  const textColor = scaleLight[900];

  // R-210 品牌色「作前景色」（强调文字 / 图标 / 链接）的跨模式自动选阶。
  // 为什么需要独立于 --brand-text：--brand-text 锁 900 深阶，浅底很稳，但暗色模式下
  // 900 阶被 R-212 重排成近黑（实测对暗底仅 1.2:1，文字几乎不可见），不能跨模式复用。
  // 也不能简单锁 -600：暗色下 600 阶同样被重排为"深"（实测 2.3:1），比现状更差。
  // 故按 R-210 同一原则各模式动态选「刚好达标」的最浅阶 ——
  //   浅色：白底上从浅往深取第一个 ≥4.5 的阶（保留品牌紫识别度的最浅可用阶）
  //   暗色：暗底上从深往浅取第一个 ≥4.5 的阶
  // 暗色参考底用 --surface(#1E293B，页面主底) 而不是 --surface-elevated(#0F172A，最深面)：
  //   品牌前景色九成场景落在页面/卡片主底上，而主底比最深面亮。原按 #0F172A 选出的
  //   300 阶实测对 #1E293B 仅 4.45:1（差 0.05 不达标），改用主底后自动上抬到 200 阶
  //   （对 #1E293B 6.01:1、对 #0F172A 6.90:1，两种底都稳）。
  const DARK_FG_REF = '#1E293B';
  const fgLightCands = lightScale
    .map((s) => ({ ...s, ratio: contrast(s.hex, '#ffffff') }))
    .filter((s) => s.ratio >= 4.5)
    .sort((a, b) => b.l - a.l);                       // l 降序 = 由浅到深
  const fgLight = fgLightCands[0];
  const fgDarkCands = darkScale
    .map((s) => ({ ...s, ratio: contrast(s.hex, DARK_FG_REF) }))
    .filter((s) => s.ratio >= 4.5)
    .sort((a, b) => a.l - b.l);                       // l 升序 = 由深到浅
  const fgDark = fgDarkCands[0];

  // R-211 语义冲突检测
  const conflicts = SEMANTIC
    .map((s) => ({ name: s.name, delta: ringHueDelta(h, s.hue) }))
    .filter((s) => s.delta < 30);

  // 装饰性渐变端点（谐波旋转，非语义色，R-211 豁免）
  const gradA = formatHex(oklch({ mode: 'oklch', l: 0.62, c: Math.min(c * 1.05, 0.24), h: (h + 14) % 360 }));
  const gradB = formatHex(oklch({ mode: 'oklch', l: 0.68, c: Math.min(c * 1.0, 0.22), h: (h + 66) % 360 }));

  const rgbChannels = hexToRgbChannels(brand).map((v) => Math.round(v)).join(', ');

  return {
    brand, oklch: { h: +h.toFixed(2), c: +c.toFixed(4), l: +l.toFixed(4) },
    scale: { light: scaleLight, dark: scaleDark },
    button: {
      light: { step: buttonStep, bg: buttonBg, fg: buttonFg, ratio: +buttonRatio.toFixed(2) },
      dark: { step: darkButton?.step, bg: darkButton?.hex, fg: '#111827', ratio: +darkButtonRatio.toFixed(2) },
    },
    text: { light: { step: 900, color: textColor, ratio: +contrast(textColor, '#ffffff').toFixed(2) } },
    fg: {
      light: fgLight
        ? { step: fgLight.step, color: fgLight.hex, ratio: +fgLight.ratio.toFixed(2) }
        : { step: 800, color: scaleLight[800], ratio: +contrast(scaleLight[800], '#ffffff').toFixed(2) },
      dark: fgDark
        ? { step: fgDark.step, color: fgDark.hex, ratio: +fgDark.ratio.toFixed(2) }
        : { step: 300, color: scaleDark[300], ratio: +contrast(scaleDark[300], DARK_FG_REF).toFixed(2) },
    },
    conflicts,
    grad: { a: gradA, b: gradB },
    rgbChannels,
    tokens: { P, c, h },
  };
}

// ---------- CSS 渲染 ----------
function renderCss(g) {
  const { P, h, c } = g.tokens;
  const sl = g.scale.light;
  const sd = g.scale.dark;
  const hex = g.brand;
  const btn = g.button.light;
  const dbtn = g.button.dark;
  const gradA = g.grad.a, gradB = g.grad.b;

  const lightScaleLines = STEPS.map((s) => `  --${P}-${s}: ${sl[s]};`).join('\n');
  const darkScaleLines = STEPS.map((s) => `  --${P}-${s}: ${sd[s]};`).join('\n');

  return `/* =============================================================
 * AUTO-GENERATED by brand-tokens.mjs — DO NOT EDIT BY HAND.
 * 单一输入：--brand (hex)。其余品牌令牌由 OKLCH 推导。
 * 重新生成：npm run tokens   (或 node brand-tokens.mjs --brand "<hex>")
 * 规范：AGENTS.md §4 R-209..R-214
 * ============================================================= */

:root {
  /* === OKLCH 输入源（运行时换肤改这 3 个即可，R-213） === */
  --${P}: ${hex};
  --${P}-h: ${h};            /* 色相 */
  --${P}-c: ${c};            /* 彩度 */
  --${P}-l: ${g.oklch.l};    /* 输入色明度 */
  --${P}-rgb: ${g.rgbChannels};  /* 同 --${P} 的 RGB 三元，供 rgba() 拼装 */

  /* === 50..900 感知均匀色阶（R-209） === */
${lightScaleLines}

  /* === 主按钮自动选阶（R-210，禁止锁 -500） === */
  --${P}-button: var(--${P}-${btn.step});
  --on-${P}: ${btn.fg};                       /* --${P}-button 上的前景色 */
  --${P}-text: var(--${P}-900);               /* 浅底上的品牌文字色 */
  --${P}-fg:   var(--${P}-${g.fg.light.step});    /* 品牌色作前景(强调文字/图标/链接)，跨模式自选阶 */

  /* === 向后兼容别名（glass.css / .vue 现有引用，禁止改名破坏） === */
  --${P}-hover:    color-mix(in oklch, var(--${P}-${btn.step}) 75%, #fff);
  --${P}-pressed:  color-mix(in oklch, var(--${P}-${btn.step}) 80%, #000);
  --${P}-dark:     color-mix(in oklch, var(--${P}-${btn.step}) 66%, #000);
  --${P}-soft:     color-mix(in oklch, var(--${P}-${btn.step}) 12%, transparent);
  --${P}-tint:     color-mix(in oklch, var(--${P}-${btn.step})  6%, transparent);
  --option-hover:  color-mix(in oklch, var(--${P}-${btn.step}) 14%, transparent);
  --${P}-a32:      color-mix(in oklch, var(--${P}-${btn.step}) 32%, transparent);
  --${P}-a22:      color-mix(in oklch, var(--${P}-${btn.step}) 22%, transparent);
  --${P}-a12:      color-mix(in oklch, var(--${P}-${btn.step}) 12%, transparent);

  /* === 装饰性渐变端点（谐波旋转，非语义色 R-211 豁免） === */
  --${P}-grad-a: ${gradA};
  --${P}-grad-b: ${gradB};

  /* === 主按钮渐变端点（R-210 选阶，随模式重排） ===
     原先主按钮渐变写死 var(--${P}) → var(--${P}-grad-a)，而 grad-a 是装饰端点
     （#8c63fa）且**无暗色重排**，导致：
       浅色 渐变最亮端配浅字 ≈ 4.08:1
       暗色 深字 #1E293B 压在亮紫渐变上 ≈ 3.27:1
     两模式都不达 AA，且与品牌色无关 —— 换任何品牌色都一样不达标。
     故按模式重排：浅色用深阶配 on-brand 亮字，暗色用亮阶配 on-brand 深字。 */
  --${P}-grad-from: var(--${P}-600);
  --${P}-grad-to:   var(--${P}-700);
}

/* R-212 暗色模式：重排 L / 降低 C，禁止 (1-L) 反转 / 复用浅色阶 */
body.dark {
  /* 暗色色阶 */
${darkScaleLines}

  /* 暗色主按钮：亮阶 + 深色前景（防光晕） */
  --${P}-button: var(--${P}-${dbtn.step});
  --on-${P}: #111827;

  /* R-212 暗色重排：品牌前景色必须换到亮阶，否则深阶在暗底上不可读 */
  --${P}-fg: var(--${P}-${g.fg.dark.step});

  /* 主按钮渐变：暗色改亮阶（配 --on-brand 深字），浅色用深阶（配亮字） */
  --${P}-grad-from: var(--${P}-300);
  --${P}-grad-to:   var(--${P}-200);

  /* 暗色别名（基于亮阶重新配比，避免浅色半透底在暗玻璃上消失） */
  --${P}-hover:    color-mix(in oklch, var(--${P}-${dbtn.step}) 78%, #fff);
  --${P}-pressed:  color-mix(in oklch, var(--${P}-${dbtn.step}) 80%, #000);
  --${P}-dark:     color-mix(in oklch, var(--${P}-${dbtn.step}) 55%, #000);
  --${P}-soft:     color-mix(in oklch, var(--${P}-${dbtn.step}) 24%, transparent);
  --${P}-tint:     color-mix(in oklch, var(--${P}-${dbtn.step}) 12%, transparent);
  --option-hover:  color-mix(in oklch, var(--${P}-${dbtn.step}) 18%, transparent);
  --${P}-a32:      color-mix(in oklch, var(--${P}-${dbtn.step}) 45%, transparent);
  --${P}-a22:      color-mix(in oklch, var(--${P}-${dbtn.step}) 32%, transparent);
  --${P}-a12:      color-mix(in oklch, var(--${P}-${dbtn.step}) 18%, transparent);
}
`;
}

// ---------- TS 常量渲染（供 JS 消费，保证与 CSS 同源） ----------
// 为什么需要：Naive UI 的 parseColor 不解析 CSS 变量，themeOverrides 只接受 hex 字面量
// （见 src/App.vue 中「已知限制」注释）。若在 store 里另写一套推导，会与 CSS 的
// --brand-fg / --brand-button 各算一套、必然漂移。故由本生成器单点产出。
function renderTs(g) {
  const { P } = g.tokens;
  return `/* 由 brand-tokens.mjs 生成，请勿手改 —— 运行 \`npm run tokens\` 重新生成。 */
/**
 * 品牌令牌（TS 侧）。
 * 与 ${P}-tokens.css 同源产出，供 Naive UI themeOverrides 使用：
 * Naive 的 parseColor 不解析 CSS 变量，只接受 hex 字面量。
 *
 * - ${P}-fg     : 品牌色作前景（强调文字/图标/链接），已按 R-210 逐模式选「刚好达标 4.5:1」的阶
 * - ${P}-button : 主按钮底色 + 其上的前景色（-on-）
 */
export const BRAND_TOKENS = {
  brand: '${g.brand}',
  fg: {
    light: { step: ${g.fg.light.step}, color: '${g.fg.light.color}', ratio: ${g.fg.light.ratio} },
    dark:  { step: ${g.fg.dark.step},  color: '${g.fg.dark.color}',  ratio: ${g.fg.dark.ratio} },
  },
  button: {
    light: { step: ${g.button.light.step}, bg: '${g.button.light.bg}', on: '${g.button.light.fg}', ratio: ${g.button.light.ratio} },
    dark:  { step: ${g.button.dark.step},  bg: '${g.button.dark.bg}',  on: '#111827', ratio: ${g.button.dark.ratio} },
  },
  buttonText: {
    light: '${g.button.light.fg}',
    dark:  '#111827',
  },
} as const;
`;
}

// ---------- 报告 ----------
function renderReport(g) {
  const { h, c, l } = g.oklch;
  const btn = g.button.light, dbtn = g.button.dark;
  let out = '';
  out += `品牌色: ${g.brand}  →  OKLCH(${h}, ${c}, ${l})\n`;
  out += `色阶(浅): ` + STEPS.map((s) => `${s}=${g.scale.light[s]}`).join('  ') + '\n';
  out += `主按钮(浅): --brand-${btn.step} ${btn.bg} + ${btn.fg}  对比度 ${btn.ratio}:1\n`;
  if (dbtn.step) out += `主按钮(暗): --brand-${dbtn.step} ${dbtn.bg} + #111827  对比度 ${dbtn.ratio}:1\n`;
  out += `品牌前景色(浅): --brand-${g.fg.light.step} ${g.fg.light.color}  对白底 ${g.fg.light.ratio}:1\n`;
  out += `品牌前景色(暗): --brand-${g.fg.dark.step} ${g.fg.dark.color}  对暗底 ${g.fg.dark.ratio}:1\n`;
  out += `冲突检测(R-211): `;
  if (g.conflicts.length === 0) out += '无 (<30° 色相冲突)\n';
  else out += g.conflicts.map((x) => `${x.name}(Δ${x.delta}°)`).join(', ') + ' — 需明度分离 + 图标\n';
  out += `装饰渐变: grad-a=${g.grad.a}  grad-b=${g.grad.b}\n`;
  return out;
}

// ---------- 主流程 ----------
function main() {
  const args = parseArgs(process.argv);
  let g;
  try {
    g = generate({ brand: args.brand, prefix: args.prefix });
  } catch (e) {
    console.error(`[brand-tokens] 生成失败: ${e.message}`);
    process.exit(2);
  }

  const errors = [];
  const warnings = [];

  // R-209 输入约束：彩度过低无法承担品牌识别度
  if (g.oklch.c < 0.05) {
    errors.push(`品牌色彩度 c=${g.oklch.c} < 0.05，无法承担品牌识别度（R-209）。`);
  }
  // R-210 对比度门禁
  if (g.button.light.ratio < 4.5) {
    errors.push(`主按钮浅色对比度 ${g.button.light.ratio}:1 < 4.5:1（R-210）。`);
  }
  if (g.button.dark.step && g.button.dark.ratio < 4.5) {
    errors.push(`主按钮暗色对比度 ${g.button.dark.ratio}:1 < 4.5:1（R-210）。`);
  }
  // R-211 语义冲突（默认仅警告，不阻断；--strict 时升级为错误）
  if (g.conflicts.length > 0) {
    const msg = `品牌色与语义色色相冲突 ${g.conflicts.map((x) => x.name).join('/')}（R-211），需用明度分离 + 图标消解。`;
    if (process.env.BRAND_STRICT === '1') errors.push(msg); else warnings.push(msg);
  }

  if (args.report) process.stdout.write(renderReport(g));
  if (args.json) process.stdout.write(JSON.stringify(g, null, 2) + '\n');

  const outPath = resolve(__dirname, args.out);

  if (args.ci) {
    // 门禁模式：先跑质量门禁，再校验提交文件新鲜度
    if (errors.length > 0) {
      console.error('[brand-tokens] CI 门禁失败:');
      for (const e of errors) console.error('  ✗ ' + e);
      process.exit(1);
    }
    for (const w of warnings) console.warn('  ⚠ ' + w);
    // 新鲜度：重新生成并与已提交文件比对（CSS 与 TS 常量两份都要校验）
    const outTsPath = resolve(__dirname, args.outTs);
    const expected = renderCss(g);
    const expectedTs = renderTs(g);
    if (!existsSync(outPath)) {
      console.error(`[brand-tokens] 缺失生成文件: ${args.out}（请运行 npm run tokens 并提交）`);
      process.exit(1);
    }
    const actual = readFileSync(outPath, 'utf8');
    if (actual.trim() !== expected.trim()) {
      console.error('[brand-tokens] 已提交的 brand-tokens.css 与当前 --brand 不一致（已过期）。');
      console.error('  请运行 `npm run tokens` 重新生成并提交。');
      process.exit(1);
    }
    if (!existsSync(outTsPath)) {
      console.error(`[brand-tokens] 缺失生成文件: ${args.outTs}（请运行 npm run tokens 并提交）`);
      process.exit(1);
    }
    if (readFileSync(outTsPath, 'utf8').trim() !== expectedTs.trim()) {
      console.error('[brand-tokens] 已提交的 brand-tokens.gen.ts 与当前 --brand 不一致（已过期）。');
      console.error('  请运行 `npm run tokens` 重新生成并提交。');
      process.exit(1);
    }
    console.log(`[brand-tokens] ✅ CI 门禁通过（brand=${g.brand}, button=${g.button.light.step}, ratio=${g.button.light.ratio}:1）`);
    process.exit(0);
  }

  // 非 CI：写文件（除非显式只想要报告）
  if (!args.report && !args.json) {
    writeFileSync(outPath, renderCss(g), 'utf8');
    writeFileSync(resolve(__dirname, args.outTs), renderTs(g), 'utf8');
    console.log(`[brand-tokens] 已写入 ${args.out}`);
    console.log(`[brand-tokens] 已写入 ${args.outTs}`);
  }
}

main();
