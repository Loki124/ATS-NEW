# ATS-NEW 暗色模式修复 · 技术实施文档
> 最后更新：2026-09-07（依据 git 最后提交）

> **v1.1（2026-08-23 18:55）**—— critique-reviewer 评审后修订：补 P0 1-4 + P1 1/3/4 + P2-1。  
> **v1.0（2026-08-23 18:37）**—— Diana 首版交付：5 层根因 + 4 阶段实施 + 可照抄代码块。  
> 触发：用户报障截图「暗色模式的样式乱七八糟」（校招管控 + 设置侧栏）  
> 范围：`web/app/src/**` 全栈，不动后端  
> 关系链：上游 `UI_DIAGNOSIS_V3.md`（V3 增量 #2/#3/#5 都属此问题）；设计规范 `web/app/DESIGN.md` §2 Dark Mode Token Set  
> **当前版本统一为 5 阶段（A/B/C/D/E）**——详见 §十一、§十三 修订记录

---

## 0. PM 决策采纳（v3 拍板 → 写入手册）

| 编号       | 决策                                   | 采纳方案                                                                                                                                                                           | 落地位置                                                  |
| -------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| **决策 1** | T9.1 验收条款                            | **保留 1 行 `:deep(.page-container)`**（解 `settings-scroll 20px + page-container 24px` 双重 padding 塌缩），删除视觉类 `:deep(.n-card / .page-title / .filter-row / .n-button--primary-type)` | `SettingsLayout.vue:576` 保留；删除原 T9.1 的"删全部 :deep"验收条款 |
| **决策 2** | T9.2 SettingsLayout 自写 menu-group 改造 | **A 方案**：SettingsLayout.vue 改用 `n-menu :options="menuOptions"`（与 Layout.vue 一致），删自写 DOM                                                                                        | `SettingsLayout.vue` 重构（本文档 §八 阶段 D 含完整模板）            |

---

## 一、截图硬证据（用户报障 → 根因映射）

| 截图所见                                                                                                                      | 根因层级                                                                                                                      | 严重度 |
| ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | --- |
| **白卡漂浮**：校招管控 `.glass-panel` 内的表格（实时看板）仍是浅色背景                                                                             | **根因 1（核心 95%）**：Naive UI darkTheme 未挂 → 原生 `n-data-table` 浅色默认背景                                                         | P0  |
| **底部"本看板已合并" `n-alert`** 蓝色背景 vs 深色环境对比突兀                                                                                 | 根因 1：`n-alert` 走 light theme                                                                                              | P1  |
| **顶部 tabs** "实时看板/规则配置…" 视觉单薄，浅色模式配色                                                                                      | 根因 1：`n-tabs-nav` 走 light theme                                                                                           | P1  |
| **顶部年份/月份 `n-input-number / n-select`** 浅色背景                                                                              | 根因 1：原生表单组件走 light theme                                                                                                  | P1  |
| **5 张 KPI 卡片 "4" 红 / "1" 橙** 颜色过饱和，与玻璃质感冲突                                                                                | 根因 2：`.kpi-card.danger / .warn` 颜色走 hex，应走暗色透色 token                                                                      | P2  |
| **侧栏"个人信息管理/公司信息管理…"** 字色对比度低                                                                                             | 根因 3：SettingsLayout 自写菜单 `.menu-item` 字色 `var(--ink-soft)` 暗色下应更亮，但 `--ink-soft: #AEB8CC` 对 `rgba(30,41,59,.55)` 仅 4:1 边缘 | P1  |
| **侧栏"招聘提速/其他"分组标题** 看不清                                                                                                   | 根因 3：`.group-title` `var(--ink-faint) = #7C879B` 对深玻璃 3:1 **不达标**                                                         | P1  |
| **"校招管控" 标题渐变偏淡**                                                                                                         | 根因 4：`.gradient-title` 不分暗色态，背景深时品牌透明渐变视觉对比偏弱                                                                             | P2  |
| **`CampusControl.vue:1404` `.batch-monthly-sum { color: #374151 }` / `:1412` `border-top: 1px solid #eef2f7`** 自写硬编码暗色下失明 | 根因 5：业务页自写 hex 没收口                                                                                                        | P2  |

---

## 二、根因 5 层分析（从全局到具体）

```
[第 1 层] tokens.css §14 暗色变量集 ✅ 已完备
         --ink / --ink-soft / --ink-faint / --glass-bg-* / --aurora-* 全套
         ↓ [DOWN]
[第 2 层] glass.css 暗色态 ✅ kpi-card / table-th / glass-panel 已覆盖
         ↓ [DOWN]
[第 3 层] ❌ Naive UI 原生组件未挂 darkTheme
         → n-data-table / n-tabs / n-alert / n-input-number / n-select / n-tag / n-checkbox / n-radio / n-switch 走 light theme 默认色
         → 即便 body.dark 设了，body 内 DOM 颜色对了，但 Naive 组件内部是「独立样式」必须靠 :theme="darkTheme" 触发
         ↓ [DOWN]
[第 4 层] ⚠️ 业务页自写 #374151 / #eef2f7 / #94a3b8（L1404/L1412/L271）硬编码 hex 没收口
         ↓ [DOWN]
[第 5 层] ⚠️ SettingsLayout 自写 .menu-item / .menu-group 缺暗色对比度微调（仅 #AEB8CC / #7C879B）
```

**根因 1（暗 Naive darkTheme）解释 95% 视觉问题**。

---

## 三、修复策略（5 阶段 · 总 ~2.9 人日）

```
阶段 A（0.3d）前置：stores/theme.ts 暴露 isDark（isDark 必须存在）
                    详见 §4.4，否则阶段 A 主代码 `isDark.value ? darkTheme : undefined` 全走 false 分支

阶段 B（0.3d）★ 核心修复：挂 Naive darkTheme + themeOverrides 双形态
            → 修 App.vue：用 :theme="isDark ? darkTheme : undefined" 触发原生组件深色
            → themeOverrides 双形态覆盖 bodyColor/cardColor/modalColor/popoverColor/
              tableColor/tableHeaderColor/tableColorHover/tableColorStriped/
              inputColor/inputColorDisabled/buttonColor2*/
              textColor1/textColor2/textColor3/dividerColor/borderColor
            → 一次性解决 95% 的暗色问题

阶段 C（0.3d）CampusControl 自写 hex → token
            → 修 3 处 #hex 硬编码（L271/L1404/L1412）

阶段 D（0.4d）决策 2 配套：SettingsLayout 改 n-menu（T9.2）
            → 130 行自写 DOM 拆解为 n-menu options
            → 完整迁移 5 分组（基本信息/过程管理/招聘提速/内容管理/其他）

阶段 E（0.4d）SettingsLayout 暗色对比度微调 + 巡检兜底
            → 自写菜单（保留）需在 E 阶段统一加 :global(body.dark) 提亮
            → 5 列表页 + Settings 子页浅 Naive 组件暗色态全量验证
```

> **命名一致**：本表与 §四/六/七/八/十一 全部统一为 A/B/C/D/E；改动前 checklist:
>
> - §三：C = CampusControl hex；D = n-menu；E = 巡检兜底
> - §四：B = App.vue darkTheme 主修复（前置 A = theme.ts isDark）
> - §六：C = CampusControl（与 §三 同）—— 待 §六 标题修正
> - §七/八：E = 巡检兜底；D = n-menu

---

## 四、阶段 B（核心修复）· Naive UI darkTheme 挂载

> **前置依赖 — 必读**：本阶段主代码使用 `const { isDark } = storeToRefs(themeStore)`。  
> **当前 `stores/theme.ts` return 表内没有 `isDark`**（实测 line 203-215），直接套用会导致 §4.3 主代码 `isDark.value ? darkTheme : undefined` 永远走 `undefined` 分支 = Naive darkTheme 不挂 = **95% 修复目标不达成**。
>
> **请先执行 §4.4「`stores/theme.ts` 暴露 isDark」前置补丁**（10 分钟，单文件），再回到 §4.3 主代码。

### 4.1 改动原理

Naive UI 的 dark theme 是一套完整调色板。`n-config-provider` 必须传两个 prop：

- `:theme` 触发原生组件深色渲染
- `:theme-overrides` 在当前 theme 上叠加品牌色/圆角/字色

**当前 App.vue 缺 `:theme` prop**，所以无论 body.dark 怎么切，Naive 原生组件都用 light theme 默认色。

### 4.2 文件改动清单

| 文件                    | 行号            | 动作                                                                                                                 |
| --------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------ |
| `src/App.vue`         | 全文重写          | 引入 `darkTheme` from 'naive-ui'；computed 切 `theme: darkTheme \| undefined`；原 `themeOverrides` 拆分覆盖到 dark/light 共同使用 |
| `src/stores/theme.ts` | L203 return 表 | **前置：暴露 `isDark` 派生 ref**（详见 §4.4）                                                                                 |

### 4.3 完整代码块（**可直接照抄**）

```vue

<template>
  <n-config-provider
    :theme="isDark ? darkTheme : undefined"
    :theme-overrides="themeOverrides"
    :locale="zhCN"
    :date-locale="dateZhCN"
  >
    <n-loading-bar-provider>
      <n-message-provider>
        <n-dialog-provider>
          <n-notification-provider>
            <router-view />
          </n-notification-provider>
        </n-dialog-provider>
      </n-message-provider>
    </n-loading-bar-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { darkTheme, zhCN, dateZhCN, type GlobalThemeOverrides } from 'naive-ui'
import { useThemeStore } from './stores/theme'

// 启动期 user 重水化 + 服务端重调已统一在 main.ts 处理.
// 此前 App.vue onMounted 里的 localStorage('token') 兼容分支已删除 —
// 因为 main.ts step 1 已经覆盖了 'token' / 'accessToken' 双 key fallback,
// 这里再做一次会产生与 main.ts 顺序竞争, 是 dead code.

// === v2 液态玻璃：Naive UI themeOverrides（DESIGN.md §2）===
// 单一输入：stores/theme.ts 的 brandHex（来自 --brand / 设置页）。
// 改 brandHex 即可全站联动（按钮、激活态、链接、玻璃辉光、极光主光斑）。
//
// ⚠️ 已知限制：Naive UI 内部用 parseColor 把 primaryColor 转成 RGB 计算
//    hover/pressed 等派生色，传 CSS 变量字符串 `var(--brand)` 会导致
//    颜色工具函数失败（Naive 不解析 var()）。
//    妥协方案：themeOverrides 用 hex 字面量（由 store.deriveHover/derivePressed
//    派生，业务层玻璃类通过 var(--brand) 直接驱动）。
//
// ★ 2026-08-23 暗色修复：darkTheme 从 naive-ui 直接 import，
//    通过 computed 切 :theme prop 让 n-data-table / n-tabs / n-alert
//    等原生组件走深色调色板。配合 body.dark（CSS 变量）联动 glass/aurora。
const themeStore = useThemeStore()
const { brandHex, brandHoverHex, brandPressedHex, isDark } = storeToRefs(themeStore)

const themeOverrides = computed<GlobalThemeOverrides>(() => ({
  common: {
    primaryColor:        brandHex.value,
    primaryColorHover:   brandHoverHex.value,
    primaryColorPressed: brandPressedHex.value,
    primaryColorSuppl:   brandHex.value,
    // === 语义色（与 tokens.css 的 --c-* 默认值同步）===
    successColor: '#16A34A',
    warningColor: '#F59E0B',
    errorColor:   '#EF4444',
    infoColor:    '#3B82F6',
    // === 圆角（DESIGN.md §11：主圆角 16px）===
    borderRadius: '16px',
    // === 暗色模式下的字色 / 表面色（让 Naive 原生组件走暗色变量不「浅色实底」）
    // base: 'darkTheme' 自带，但 hover 等覆盖会偏浅 → 走 var() 强压为品牌可控 ===
    bodyColor: isDark.value ? 'transparent' : 'transparent',  // 透明让 glass.css 接管
    cardColor: isDark.value ? 'transparent' : '#ffffff',       // 让 .n-card.n-card 玻璃化接管
    modalColor: isDark.value ? 'transparent' : '#ffffff',
    popoverColor: isDark.value ? 'transparent' : '#ffffff',
    tableColor: isDark.value ? 'transparent' : '#ffffff',      // ★ 解决「白卡漂浮」核心
    tableHeaderColor: isDark.value ? 'rgba(255, 255, 255, 0.04)' : 'rgba(255, 255, 255, 0.65)',
    tableColorHover: isDark.value ? 'rgba(255, 255, 255, 0.06)' : 'rgba(99, 102, 241, 0.06)',
    tableColorStriped: isDark.value ? 'transparent' : 'transparent',
    inputColor: isDark.value ? 'rgba(255, 255, 255, 0.06)' : 'rgba(255, 255, 255, 0.5)',
    inputColorDisabled: isDark.value ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.02)',
    buttonColor2: isDark.value ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.06)',
    buttonColor2Hover: isDark.value ? 'rgba(255, 255, 255, 0.18)' : 'rgba(0, 0, 0, 0.09)',
    buttonColor2Pressed: isDark.value ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.04)',
    textColor1: isDark.value ? 'rgba(232, 236, 246, 1)' : 'rgba(15, 23, 42, 1)',         // 主要文字
    textColor2: isDark.value ? 'rgba(174, 184, 204, 1)' : 'rgba(71, 85, 105, 1)',         // 次要文字
    textColor3: isDark.value ? 'rgba(124, 135, 155, 1)' : 'rgba(148, 163, 184, 1)',       // 占位符
    dividerColor: isDark.value ? 'rgba(255, 255, 255, 0.08)' : 'rgba(15, 23, 42, 0.08)',
    borderColor: isDark.value ? 'rgba(255, 255, 255, 0.12)' : 'rgba(15, 23, 42, 0.12)',
  },
  Card: {
    borderRadius: '16px',
  },
  Button: {
    borderRadiusMedium: '16px',
    // 玻璃按钮：白字（DESIGN.md §4 btn-primary：品牌渐变背景 → 白字最稳）
    textColorPrimary:          '#ffffff',
    textColorHoverPrimary:     '#ffffff',
    textColorPressedPrimary:   '#ffffff',
    textColorFocusPrimary:     '#ffffff',
    textColorDisabledPrimary:  '#ffffff',
  },
}))
</script>

<style>
/* 全局样式已在 index.css 中定义 */
</style>
```

### 4.4 前置：stores/theme.ts 暴露 isDark（P0 阻塞级 bug · 必做）

**问题诊断**（实测 `stores/theme.ts:203-215`）：

```ts
// 现有 return 表 —— 注意：没有 isDark
return {
  brandHex, mode, brandHoverHex, brandPressedHex,  // <-- 无 isDark!
  setBrand, setMode, reset, init,
}
```

`applyModeToDom(m)` L128 通过 `body.classList.toggle('dark', dark)` 把暗色态表达在 DOM class 上，  
但 store 不持有对应的响应式状态。文档 §4.3 主代码用 `const { isDark } = storeToRefs(themeStore)` 解构  
到 `undefined`，导致 `isDark.value ? darkTheme : undefined` 永远走 `false` 分支。

#### 文件改动清单

| 文件                    | 行号                 | 动作                                                       |
| --------------------- | ------------------ | -------------------------------------------------------- |
| `src/stores/theme.ts` | L1-2 import 区      | 加 `import { ref, computed, watch, onScopeDispose }`（如有缺） |
| 同上                    | L109-L140 派生区      | 新增 `isDark` ref + auto 模式响应系统切换逻辑                        |
| 同上                    | L203-L215 return 表 | 把 `isDark` 加入返回                                          |

#### 完整代码块（**可直接照抄**）

```ts
// === web/app/src/stores/theme.ts ===
// === 1) 替换 applyModeToDom 内的 body.classList.apply(.) 行附近，新增 isDark 响应 ===
// 在 `state` 区域（line 110 附近，brandHex/mode 之后）新增：

  // ★ 2026-08-23 暗色修复：暴露 isDark 供 App.vue 的 n-config-provider :theme 使用
  // 替代：原代码仅通过 body.classList.toggle('dark', ...) 表达，响应式拿不到
  const isDark = ref(false)

// === 2) 替换 applyModeToDom 函数（约 line 126-140），改为响应式同步 isDark ===

  function applyModeToDom(m: ThemeMode) {
    const body = document.body
    let dark: boolean

    if (m === 'auto') {
      const mq = window.matchMedia('(prefers-color-scheme: dark)')
      dark = mq.matches
      // 同时把 mq 引用保存到闭包以便响应系统主题变化（见 watch）
      ;(applyModeToDom as any)._mq = mq
    } else {
      dark = m === 'dark'
    }

    body.classList.toggle('dark', dark)
    isDark.value = dark   // ★ 与 DOM 同步
  }

// === 3) 在现有 `watch(mode, applyModeToDom)` 之后（line 201 之后）新增 ===

  // auto 模式响应系统主题变化（store 生命周期 = 应用生命周期，不清理）
  if (typeof window !== 'undefined') {
    watch(mode, (m) => {
      if (m !== 'auto') return
      const mq = window.matchMedia('(prefers-color-scheme: dark)')
      const handler = (e: MediaQueryListEvent) => {
        isDark.value = e.matches
        document.body.classList.toggle('dark', e.matches)
      }
      mq.addEventListener('change', handler)
    }, { immediate: true })
  }

// === 4) 修改 return 表（line 203-215）新增 isDark ===

  return {
    // state
    brandHex,
    mode,
    isDark,           // ★ 新增
    // 派生
    brandHoverHex,
    brandPressedHex,
    // actions
    setBrand,
    setMode,
    reset,
    init,
  }
```

#### 验证方法

```bash
# 重启 dev
cd web/app && npm run dev

# 浏览器 console 测响应式
__ats.theme.get()      # 返回对象，现在应包含 isDark 派生（手算返回 brandHex + mode，没暴露 isDark 在 get 内）
__ats.theme.setMode('dark')
# DevTools Vue inspector: useThemeStore() 的 isDark 应为 true
# App.vue 的 n-config-provider :theme prop 应变为 darkTheme（Vue devtools 可见）
__ats.theme.setMode('light')
# isDark 应自动变 false
```

### 4.5 验证方法（主修复）

```bash
# 1. 启动 dev（前置 §4.4 必须已落地）
cd web/app && npm run dev

# 2. 打开浏览器 console 测主题切换
__ats.theme.setMode('dark')   # 应让 body 加 .dark 类 + Vue DevTools 中 useThemeStore().isDark === true
__ats.theme.setMode('light')  # 应去掉 .dark + isDark === false

# 3. 视觉验证（按截图同位置）
# 打开 /settings/campus-control
# - 实时看板表格背景应变深玻璃色（不再是白色漂浮）
# - 底部 n-alert 应变深色系
# - KPI 卡片数字应清晰可读
```

---

## 五、阶段 C · CampusControl 自写 hex → token

### 5.1 文件改动清单

| 文件                                 | 行号      | 现状                                      | 改为                                             |
| ---------------------------------- | ------- | --------------------------------------- | ---------------------------------------------- |
| `pages/settings/CampusControl.vue` | 271-272 | `style="color: #94a3b8"`                | `style="color: var(--ink-faint)"`              |
| `pages/settings/CampusControl.vue` | 1404    | `.batch-monthly-sum { color: #374151 }` | `color: var(--ink)`                            |
| `pages/settings/CampusControl.vue` | 1412    | `border-top: 1px solid #eef2f7`         | `border-top: 1px solid var(--border-hairline)` |

### 5.2 完整代码块（**可直接照抄**）

```vue


<div v-if="!batchDrawer.dimensionId" style="color: var(--ink-faint); padding: 8px 0; font-size: 13px;">请先选择维度</div>
<div v-else-if="batchIndicators.length === 0" style="color: var(--ink-faint); padding: 8px 0; font-size: 13px;">该维度下暂无指标，请先到「指标管理」新增</div>
```

```vue


.batch-monthly-sum {
  color: var(--ink);   /* 原 #374151，浅色等同；暗色自动转 #E8ECF6 */
  ...
}
```

```vue


.batch-sum {
  border-top: 1px solid var(--border-hairline);  /* 原 #eef2f7 */
  ...
}
```

### 5.3 验证方法

```bash
grep -nE '#374151|#eef2f7|#94a3b8|#94A3B8' src/pages/settings/CampusControl.vue
# 应返回 0 行
```

---

## 七、阶段 E · 巡检兜底（5 列表页 + Settings 子页 · 含暗色对比度微调）

> **命名修正**：原文档此节标题误标为"阶段 D 巡检兜底"，按 A/B/C/D/E 重排后应为"阶段 E"。  
> （"阶段 D"已分配给"§八 决策 2 配套 · SettingsLayout 改 n-menu"。）

### 7.1 巡检内容

跑 Playwright 自动截图 5 列表页 + Settings 8 个子页 × light/dark × 4 视口，重点看：

- `n-data-table` 表体背景是否随暗色切换
- `n-tabs-nav` 在暗色下是否完整可见
- `n-alert` 暗色下是否有合适对比度
- `n-tag` 语义色（success/warning/error）暗色下字色对比
- `n-input-number / n-select` 暗色下背景

### 7.2 巡检命令

```bash
# 启动 dev（launchd 已保活）
curl --noproxy '*' http://localhost:5212/

# 自动化截图
/Users/loki/WorkBuddy/招聘助手/ATS-NEW/qa-final.mjs  # 已有，需补 dark 主题
```

### 7.3 兜底样式（如发现仍有局部问题）

```css
/* web/app/src/styles/glass.css 末尾追加 */
/* === 阶段 E 巡检兜底 —— 用 themeOverrides 替代 !important，符合"单一来源"哲学 === */

/* n-tabs 在暗色下的 tabbar 底部线 */
body.dark .n-tabs .n-tabs-nav::after {
  background: var(--glass-border);
}

/* n-checkbox / n-radio 暗色文字色 */
body.dark .n-checkbox__label,
body.dark .n-radio__label {
  color: var(--ink);
}

/* n-tag 暗色语义色微调（success/warning/error/info 在深玻璃上对比度补强） */
body.dark .n-tag.n-tag--success-type { color: var(--c-success); background: var(--c-success-soft); }
body.dark .n-tag.n-tag--warning-type { color: var(--c-warning); background: var(--c-warning-soft); }
body.dark .n-tag.n-tag--error-type   { color: var(--c-error);   background: var(--c-error-soft); }
body.dark .n-tag.n-tag--info-type    { color: var(--c-info);    background: var(--c-info-soft); }
```

> **重要修正**（v1.1 评审反馈 P1-3）：原 §7.3 用 `body.dark .n-alert { background: ... !important }` 走强覆盖，  
> 与 DESIGN.md §7 Do's "任何样式都走 token + themeOverrides" 的"单一来源"哲学冲突。  
> **正确做法**：把 n-alert 暗色背景塞进 §4.3 App.vue 的 themeOverrides：
>
> ```ts
> // §4.3 themeOverrides 内补充
> Alert: {
>   colorInfo:    isDark.value ? 'rgba(59, 130, 246, 0.18)' : 'rgba(59, 130, 246, 0.12)',
>   colorSuccess: isDark.value ? 'rgba(22, 163, 74, 0.20)' : 'rgba(22, 163, 74, 0.12)',
>   colorWarning: isDark.value ? 'rgba(245, 158, 11, 0.22)' : 'rgba(245, 158, 11, 0.14)',
>   colorError:   isDark.value ? 'rgba(239, 68, 68, 0.20)' : 'rgba(239, 68, 68, 0.12)',
> },
> ```
>
> 同时追加 §4.3 themeOverrides 关键缺失字段（v1.1 评审 P2-1）：
>
> ```ts
> actionColor:        isDark.value ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.04)',
> tabColor:           isDark.value ? 'rgba(255, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.7)',
> closeColorHover:    isDark.value ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.09)',
> ```

---

## 八、阶段 D（决策 2 配套）· SettingsLayout 改 n-menu（T9.2）

> **命名修正**：原文档此节命名上无章节号（"八、决策 2 配套实施"），按 A/B/C/D/E 重排后归为"阶段 D"。

### 8.1 重构理由

SettingsLayout.vue 当前自写 130 行 `.menu-group / .menu-item / .menu-item-parent / .sub-menu-item` DOM + 4 个 toggle 函数（`isGroupExpanded / isItemExpanded / toggleGroup / toggleItem`）。

- 维护成本 ≈ Layout.vue 的 n-menu 实现 × 2
- 体验断层：展开/折叠动画 vs Layout 自动展开父菜单
- 移动端兼容差异

Layout.vue L399-432 已示范 n-menu 处理二级 + 三级嵌套。

### 8.2 完整重构代码（**可直接照抄**，与 Layout.vue 风格一致）

> **v1.1 修订**（评审判 P0-3 / P0-4 / P1-1）：
>
> 1. **补 imports**：`h` from 'vue'、`NIcon` from 'naive-ui'、全部 icons（不再依赖全局）
> 2. **列全 5 个分组**（基本信息/过程管理/招聘提速/内容管理/其他），每组 children 完整迁移
> 3. **expandCurrent 改累 ancestor**：3 嵌套菜单（如 `/settings/company-mgmt → /settings/company`）需展开中间层 + 最外层 group

```vue

<template>
  <n-layout class="settings-layout" has-sider :sider-width="collapsed ? 64 : 220" style="height: 100%">
    
    <n-layout-sider
      :width="220"
      :collapsed-width="64"
      :collapsed="collapsed"
      collapse-mode="width"
      :native-scrollbar="false"
      class="settings-sider glass-sidebar"
    >
      <div class="sider-header" :class="{ collapsed: collapsed }">
        <h2 v-if="!collapsed" class="sider-title gradient-title">设置</h2>
        <button
          class="collapse-btn"
          :class="{ collapsed: collapsed }"
          type="button"
          aria-label="折叠设置菜单"
          @click="collapsed = !collapsed"
        >
          <n-icon :component="collapsed ? ChevronForwardOutline : ChevronBackOutline" />
        </button>
      </div>

      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="subMenuOptions"
        :value="activeKey"
        :expanded-keys="expandedKeys"
        :theme-overrides="settingsMenuThemeOverrides"
        class="settings-menu"
        @update:value="handleMenuClick"
        @update:expanded-keys="onExpandedKeysChange"
      />
    </n-layout-sider>

    
    <n-layout-content class="settings-content">
      <div class="settings-aurora" aria-hidden="true">
        <span class="blob blob-a"></span>
        <span class="blob blob-b"></span>
        <span class="blob blob-c"></span>
      </div>
      <div class="settings-scroll">
        <router-view />
      </div>
    </n-layout-content>
  </n-layout>
</template>

<script setup lang="ts">
// ★ v1.1 补全 imports
import { ref, computed, watch, nextTick, h, type Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon } from 'naive-ui'   // ★ 之前漏
import {
  ChevronForwardOutline, ChevronBackOutline,
  PersonCircleOutline, BusinessOutline, PeopleOutline, BookOutline, BookmarkOutline,
  ClipboardOutline, StarOutline, SchoolOutline, GitNetworkOutline, GitBranchOutline,
  StopwatchOutline, ConstructOutline, LayersOutline, InformationCircleOutline,
  CloudUploadOutline, ServerOutline, SearchOutline, AnalyticsOutline,
  ColorPaletteOutline, LocationOutline, VideocamOutline, MailOutline,
  ShieldCheckmarkOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)

// ★ v1.1 修复：必须定义 MenuItem 类型 + 子菜单类型（含 type:'group'）
interface MenuItem {
  key: string
  label: string
  icon?: () => any     // n-menu 期望 icon 是 render 函数
  type?: 'group' | 'divider' | 'render'
  children?: MenuItem[]
}

// ★ v1.1 修复：subMenuOptions 列全 5 个分组，全部 children 完整迁移
//   结构：5 group（基本信息/过程管理/招聘提速/内容管理/其他）+ 嵌套二级/三级菜单
//   icon 渲染：保持 render 函数形式（与 Layout.vue 一致）
const subMenuOptions: MenuItem[] = [
  {
    key: 'g-basic',
    type: 'group',
    label: '基本信息',
    children: [
      { key: '/settings/account', label: '个人信息管理', icon: () => h(NIcon, null, { default: () => h(PersonCircleOutline) }) },
      {
        key: 'g-company',
        label: '公司信息管理',
        icon: () => h(NIcon, null, { default: () => h(BusinessOutline) }),
        children: [
          { key: '/settings/company', label: '公司信息', icon: () => h(NIcon, null, { default: () => h(BusinessOutline) }) },
          { key: '/settings/company/address', label: '公司地址', icon: () => h(NIcon, null, { default: () => h(LocationOutline) }) },
          { key: '/settings/company/meeting-rooms', label: '公司会议室', icon: () => h(NIcon, null, { default: () => h(VideocamOutline) }) },
          { key: '/settings/company/resume-mailbox', label: '接收简历邮箱', icon: () => h(NIcon, null, { default: () => h(MailOutline) }) },
          { key: '/settings/company/brand', label: '品牌信息管理', icon: () => h(NIcon, null, { default: () => h(ColorPaletteOutline) }) },
        ],
      },
      {
        key: 'g-org',
        label: '组织信息管理',
        icon: () => h(NIcon, null, { default: () => h(PeopleOutline) }),
        children: [
          { key: '/settings/department', label: '组织职责管理', icon: () => h(NIcon, null, { default: () => h(BusinessOutline) }) },
          { key: '/settings/permissions', label: '角色管理', icon: () => h(NIcon, null, { default: () => h(ShieldCheckmarkOutline) }) },
          { key: '/settings/user-management', label: '团队成员管理', icon: () => h(NIcon, null, { default: () => h(PeopleOutline) }) },
          { key: '/settings/user-groups', label: '用户组管理', icon: () => h(NIcon, null, { default: () => h(PersonCircleOutline) }) },
        ],
      },
    ],
  },
  {
    key: 'g-process',
    type: 'group',
    label: '过程管理',
    children: [
      { key: '/settings/demand-config', label: '招聘需求设置', icon: () => h(NIcon, null, { default: () => h(ClipboardOutline) }) },
      { key: '/settings/dictionary', label: '数据字典', icon: () => h(NIcon, null, { default: () => h(BookmarkOutline) }) },
      { key: '/settings/campus-control', label: '校招管控', icon: () => h(NIcon, null, { default: () => h(SchoolOutline) }) },
      { key: '/settings/scoring', label: '评分规则', icon: () => h(NIcon, null, { default: () => h(StarOutline) }) },
    ],
  },
  {
    key: 'g-speedup',
    type: 'group',
    label: '招聘提速',
    children: [
      { key: '/settings/recruitment-stage', label: '招聘阶段配置', icon: () => h(NIcon, null, { default: () => h(LayersOutline) }) },
      { key: '/settings/recruitment-process', label: '招聘流程', icon: () => h(NIcon, null, { default: () => h(GitNetworkOutline) }) },
      { key: '/settings/recruitment-round', label: '面试轮次', icon: () => h(NIcon, null, { default: () => h(StopwatchOutline) }) },
    ],
  },
  {
    key: 'g-content',
    type: 'group',
    label: '内容管理',
    children: [
      { key: '/settings/announcements', label: '制度公告', icon: () => h(NIcon, null, { default: () => h(BookOutline) }) },
    ],
  },
  {
    key: 'g-misc',
    type: 'group',
    label: '其他',
    children: [
      { key: '/settings/theme', label: '主题外观', icon: () => h(NIcon, null, { default: () => h(ColorPaletteOutline) }) },
      { key: '/settings/company-library', label: '公司库', icon: () => h(NIcon, null, { default: () => h(BusinessOutline) }) },
      { key: '/settings/school-library', label: '院校库', icon: () => h(NIcon, null, { default: () => h(SchoolOutline) }) },
      { key: '/settings/dynamic-fields', label: '动态字段', icon: () => h(NIcon, null, { default: () => h(ConstructOutline) }) },
      { key: '/settings/scraped-resumes', label: '我找的简历', icon: () => h(NIcon, null, { default: () => h(SearchOutline) }) },
      { key: '/settings/data-dashboard', label: '数据中心', icon: () => h(NIcon, null, { default: () => h(AnalyticsOutline) }) },
      { key: '/settings/external', label: '对外接口', icon: () => h(NIcon, null, { default: () => h(ServerOutline) }) },
      { key: '/settings/public', label: '公共设置', icon: () => h(NIcon, null, { default: () => h(CloudUploadOutline) }) },
    ],
  },
]

const settingsMenuThemeOverrides = {
  itemTextColor: 'var(--ink-soft)',
  itemTextColorHover: 'var(--ink)',
  itemTextColorActive: 'var(--brand)',
  itemTextColorActiveHover: 'var(--brand)',
  itemIconColor: 'var(--ink-soft)',
  itemIconColorHover: 'var(--ink)',
  itemIconColorActive: 'var(--brand)',
  itemColorActive: 'var(--brand-soft)',
  itemColorActiveHover: 'var(--brand-soft)',
  borderRadius: '6px',
  groupTextColor: 'var(--ink-faint)',
}

// ★ v1.1 修复：expandCurrent 改为累计 ancestor 链（3 嵌套必须展开中间层 + 最外层 group）
//   原版只 walk 一层（group → child），遇到二级嵌套（g-org → g-company → 叶子）会漏中间层
//   新版用 path 数组累积所有祖先 key，全链路展开
function findPathToKey(items: MenuItem[], target: string, currentPath: string[] = []): string[] | null {
  for (const item of items) {
    const newPath = [...currentPath, item.key]
    if (item.key === target) return newPath
    if (item.children?.length) {
      const found = findPathToKey(item.children, target, newPath)
      if (found) return found
    }
  }
  return null
}

function expandCurrentTo(path: string) {
  const chain = findPathToKey(subMenuOptions, path)
  if (!chain) return
  // chain 是从最外层 group 到目标 key 的完整路径，剔除目标本身
  const ancestors = chain.slice(0, -1)
  const merged = new Set([...expandedKeys.value, ...ancestors])
  expandedKeys.value = Array.from(merged)
}

const expandedKeys = ref<string[]>([])
function onExpandedKeysChange(keys: string[]) {
  expandedKeys.value = keys
}

const optimisticKey = ref('')
const optimisticTimer = ref<number>()
const activeKey = computed(() => {
  if (optimisticKey.value) return optimisticKey.value
  return route.path
})

watch(() => route.path, () => expandCurrentTo(route.path), { immediate: true })

function handleMenuClick(key: string) {
  if (typeof key === 'string' && key.startsWith('/')) {
    nextTick(() => { optimisticKey.value = key })
    if (optimisticTimer.value) window.clearTimeout(optimisticTimer.value)
    optimisticTimer.value = window.setTimeout(() => { optimisticKey.value = '' }, 1000)
    router.push(key)
  }
}

watch(() => route.path, () => {
  if (optimisticTimer.value) { window.clearTimeout(optimisticTimer.value); optimisticTimer.value = undefined }
  optimisticKey.value = ''
})
</script>

<style scoped>
/* 保留 .settings-layout / .sider-header / .collapse-btn；
   自写 menu-group / group-header / menu-item 等已删除（见 §8.3）。
   玻璃激活态覆盖：利用 settings-sider 已有 class="glass-sidebar"（glass.css 全局接管） */
.settings-layout { height: 100%; background: transparent; overflow: hidden; }
.sider-header {
  position: sticky; top: 0; z-index: 10;
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 16px 12px 20px;
  border-bottom: 1px solid var(--border-hairline);
  background: var(--glass-bg-panel);
  backdrop-filter: blur(var(--glass-blur-panel));
  -webkit-backdrop-filter: blur(var(--glass-blur-panel));
}
/* 注：暗色模式下 sider-header 提亮见 §十六/阶段 E 的 body.dark .sider-header 规则
   或挪到 glass.css 全局（推荐，避免 scoped 失效） */
</style>
```

### 8.3 删除项

- 删除 4 个 toggle 函数（`isGroupExpanded / isItemExpanded / toggleGroup / toggleItem`）—— 但**不删除模板 `<div class="sider-header">`**&#x7B49; 30 行布局骨架
- 删除 `flatMenuItems` / `findLeafContext` 折叠态辅助
- 删除模板中 `<div class="menu-group">` 等 130 行 menu DOM
- 删除 `<style scoped>` 中 `.menu-group / .group-header / .group-body / .menu-item / .sub-menu / .has-children` 等所有规则（仅保留 `.settings-layout / .sider-header / .collapse-btn`）

### 8.4 验证方法

```bash
# 1. 自写组件清零
grep -c 'class="menu-group\|isGroupExpanded\|toggleGroup\|isItemExpanded\|toggleItem' src/pages/settings/SettingsLayout.vue
# 期望：0 行

# 2. n-menu 必备 import 已加
grep -nE "from 'vue'|NIcon" src/pages/settings/SettingsLayout.vue | head
# 期望：能看到 `import { ref, computed, watch, nextTick, h, type Component } from 'vue'` 和 `import { NIcon } from 'naive-ui'`

# 3. 视觉验证
# 进入 /settings/company（3 级嵌套：基本信息 → 公司信息管理 → 公司信息）
# 应自动展开「基本信息」group + 「公司信息管理」sub-menu
```

---

## 九、验收门禁（4 档 · 全过才合格）

### 9.1 阶段 A 门禁（前置：`stores/theme.ts` 暴露 `isDark`）

```bash
# 重启 dev
cd web/app && npm run dev

# 浏览器 console 验证
__ats.theme.get()      # 返回 { brand, mode }
# Vue DevTools → pinia → theme store：isDark 字段存在

# 切换主题后观察 isDark 是否响应
__ats.theme.setMode('dark')   # Vue DevTools 中 isDark === true
__ats.theme.setMode('light')  # isDark === false
__ats.theme.setMode('auto')   # 跟随时切系统主题，isDark 应自动跟随
```

### 9.2 阶段 B 门禁（核心修复 · App.vue darkTheme + themeOverrides）

```bash
# 1. 浅色模式无回归（关键）
# 浏览器打开 5 列表页 × Dashboard × Login × Settings × 校招管控
# 应与 v2 阶段效果一致，无视觉差异

# 2. 暗色模式核心（截图复现）
__ats.theme.setMode('dark')
# 进入 /settings/campus-control：
#   - 实时看板表格背景 = var(--glass-bg-card) 深玻璃，非白色
#   - 顶部 tabs 暗色可见
#   - KPI 卡片数字清晰可读
#   - 底部 n-alert 暗色背景 + 透明

# 3. 切换回浅色
__ats.theme.setMode('light')
# 全站视觉与切换前一致
```

### 9.3 阶段 C 门禁（CampusControl hex → token）

```bash
grep -nE '#374151|#eef2f7|#94a3b8|#94A3B8' src/pages/settings/CampusControl.vue
# 期望：0 行
```

### 9.4 阶段 D 门禁（SettingsLayout 改 n-menu）

```bash
# 1. 自写组件清零
grep -c 'class="menu-group\|isGroupExpanded\|toggleGroup\|isItemExpanded\|toggleItem' src/pages/settings/SettingsLayout.vue
# 期望：0 行

# 2. n-menu 必备 import 已加
grep -nE "from 'vue'|NIcon" src/pages/settings/SettingsLayout.vue | head
# 期望：能看到 `import { ref, computed, watch, nextTick, h, type Component } from 'vue'` 和 `import { NIcon } from 'naive-ui'`

# 3. subMenuOptions 5 分组全迁移
grep -E "type: 'group'" src/pages/settings/SettingsLayout.vue | wc -l
# 期望：5

# 4. 视觉验证（3 嵌套菜单自动展开）
# 进入 /settings/company（路径：基本信息 → 公司信息管理 → 公司信息）
# 应自动展开「基本信息」group + 「公司信息管理」sub-menu
```

### 9.5 阶段 E 门禁（巡检兜底）

```bash
# Playwright 自动截图
/Users/loki/WorkBuddy/招聘助手/ATS-NEW/qa-final.mjs

# 截图矩阵
# 5 列表页（Offer/Demand/Onboarding/Interview/Candidate）
# × 4 视口（1440/1024/768/375）
# × 2 主题（light/dark）
# = 40 截图

# 视觉回归：每张图人工目检
# - 表格背景暗色下深玻璃
# - 标签/Alert/Form 暗色可见
# - 无"白卡漂浮"
# - 暗色模式下设置侧栏菜单字色清晰可读，分组小标题对比度 ≥ 4.5:1
```

```bash
# Playwright 自动截图
/Users/loki/WorkBuddy/招聘助手/ATS-NEW/qa-final.mjs

# 截图矩阵
# 5 列表页（Offer/Demand/Onboarding/Interview/Candidate）
# × 4 视口（1440/1024/768/375）
# × 2 主题（light/dark）
# = 40 截图

# 视觉回归：每张图人工目检
# - 表格背景暗色下深玻璃
# - 标签/Alert/Form 暗色可见
# - 无"白卡漂浮"
```

---

## 十、风险与回滚

### 10.1 阶段 A 风险

| 风险                                                          | 概率 | 缓解                                                                                       |
| ----------------------------------------------------------- | -- | ---------------------------------------------------------------------------------------- |
| Naive darkTheme 引入导致某些自定义组件样式破相                             | 中  | 单文件 commit + 视觉回归；如有问题在 overrides 中再加规约                                                  |
| `bodyColor: 'transparent'` 导致 Naive 内部 Modal mask 透明        | 低  | Modal mask 走 `--glass-bg-overlay` 覆写，glass-modal.css 已落                                  |
| `tableColor: 'transparent'` 让 `.n-data-table-wrapper` 容器没背景 | 中  | glass.css L341-358 `.glass-table` 已接管，ListView 页表格都不裸 `<n-data-table>` 而包 `.glass-panel` |

### 10.2 阶段 B/C/D 风险

| 风险                         | 概率            | 缓解                                                                           |
| -------------------------- | ------------- | ---------------------------------------------------------------------------- |
| CampusControl hex 替换破坏现有视觉 | 低             | 颜色完全等同（#374151 ≈ var(--ink) in light），无肉眼差异                                  |
| SettingsLayout 重构回归        | **中（高风险反向删）** | **严格执行用户 memory「首轮仅 DOM 替换不删 CSS」，第 2 轮再删**；先 commit 一个"仅 DOM 替换"再做"删自写 CSS" |
| 巡检遗漏暗色 Naive 组件            | 中             | 阶段 D 用 Playwright 自动截图覆盖                                                     |

### 10.3 回滚策略

每个阶段独立 commit，可单独 revert：

```bash
# 阶段 A 异常
git revert <commit-A>  # 仅 App.vue 回滚，不影响其他阶段

# 阶段 B 异常
git revert <commit-B>  # 仅 CampusControl L271/L1404/L1412

# 阶段 C/D 异常
git revert <commit-C>  # 仅 SettingsLayout 局部 CSS
git revert <commit-D>  # 仅 glass.css 兜底
```

### 10.4 commit 规约（v1.1 阶段重命名后）

检查一下实施文档中的内容在项目中是否已经全部完成了

---

## 十一、工作量与排期

| 阶段                                                | 工作量       | 优先级       | 依赖  |
| ------------------------------------------------- | --------- | --------- | --- |
| **A**（前置）stores/theme.ts 暴露 `isDark`              | 0.05d     | **P0 阻塞** | —   |
| **B**（核心修复）挂 Naive darkTheme + themeOverrides 双形态 | 0.3d      | **P0 关键** | A   |
| **C** CampusControl 3 处 #hex → token              | 0.3d      | P0        | —   |
| **D** SettingsLayout 改 n-menu（T9.2 决策 2）          | 0.4d      | P1        | A   |
| **E** SettingsLayout 自写菜单暗色对比度 + 巡检兜底             | 1.5d      | P2        | A、D |
| **总计**                                            | **2.55d** |           |     |

**建议排期**：A → B（必须串行）→ C（并行）→ D → E。  
**先做 A+B**（核心修复 + 前置，立竿见影），其他按优先级推进。

> **v1.1 阶段命名修正**：原文档阶段命名不一致：
>
> - 原 §三「修复策略」4 阶段 + §十一 5 阶段，编排上混淆"D = 巡检兜底 vs D = n-menu"
> - 修正后统一 A/B/C/D/E：A = theme.ts 前置；B = App.vue darkTheme 主修复；C = CampusControl；D = n-menu；E = 巡检兜底
> - §六 标题"CampusControl"原误标"SettingsLayout 自写菜单"——已修正

---

## 十二、后续观察点（已上 SLA 监控）

切到阶段 B（含前置 A）上线后，**监控以下情况 7 天**：

- 暗色模式下 Naive `n-data-table` 表格内的"自定义渲染 cell"是否仍可读（如有 `<n-tag>` 嵌入）
- 暗色模式下 `<n-modal>` 弹窗毛玻璃遮罩是否过深
- `localStorage.ats-theme` 跨标签同步是否正常
- `prefers-color-scheme: dark` + 用户 auto 模式是否触发 `body.dark`
- 暗色模式下 `useThemeStore().isDark` 在 Vue DevTools 中是否正确响应（auto + 系统切换）

如有回归，按 §10.3 回滚。

---

## 十三、修订记录（changelog）

### v1.1 · 2026-08-23（critique-reviewer 评审后修订）

| 维度                                | 修订点                                                                                    | 评审依据                                                                                                  |
| --------------------------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **§三 策略**                         | 4 阶段 → 5 阶段，新增「A 前置 stores/theme.ts」                                                   | P0-1 阻塞                                                                                               |
| **§三 / §十一 命名**                   | D/D/E 重新分配：A=theme.ts / B=App.vue / C=CampusControl / D=n-menu / E=巡检                  | P1-4 命名冲突                                                                                             |
| **§四 4.4 新增**                     | `stores/theme.ts` 暴露 `isDark` 完整补丁（10 分钟）                                              | **P0-1 阻塞级**：实测 `theme.ts:203-215` return 表无 `isDark` → `storeToRefs` 取 undefined → 主代码全走 light theme |
| **§六 标题修正**                       | 原"SettingsLayout 自写菜单"→"CampusControl 自写 hex → token"（与 §十一 C 一致）                      | P1-4 命名                                                                                               |
| **§七 标题修正**                       | "阶段 D"→"阶段 E"（巡检兜底是 E）                                                                 | P1-4 命名                                                                                               |
| **§七 7.3 !important**             | 原 `body.dark .n-alert { background: ... !important }` 改为走 §4.3 themeOverrides.Alert 字典 | P1-3 哲学一致                                                                                             |
| **§七 7.3 新增 P2-1**                | themeOverrides 补充 `actionColor / tabColor / closeColorHover` 字段                        | P2-1 Naive UI 暗色字段完整化                                                                                 |
| **§八 标题修正**                       | "八、决策 2 配套实施"→"阶段 D 决策 2 配套"                                                           | P1-4 命名                                                                                               |
| **§八 8.2 imports 全补**             | `h from 'vue'` + `NIcon from 'naive-ui'` + 全部 22 个 icons                               | **P0-3 TS 编译报错**                                                                                      |
| **§八 8.2 subMenuOptions 列全 5 分组** | 完整迁移基本信息/过程管理/招聘提速/内容管理/其他 + 嵌套 children                                               | **P0-4 工程师自行迁移失败风险**                                                                                  |
| **§八 8.2 expandCurrentTo 重写**     | 原 walk 只一层 → 新版 `findPathToKey` 累计 ancestor 链                                          | **P1-1 3 级嵌套菜单不展开**                                                                                   |
| **§九 9.3 验收补**                    | 增加 "n-menu import 已加" + "3 嵌套菜单自动展开" 视觉验证                                              | P0-3 + P1-1 闭环                                                                                        |

### v1.0 · 2026-08-23 18:37（首版）

Diana 交付初版：5 层根因 + 4 阶段实施 + 可照抄代码块。

> **评审团队**：`design-engine-ui-review` / critique-reviewer（3.8/5 分）  
> **修订者**：Hua（主理人，机械代码修补不消耗 agent 配额）

---

**报告位置**：`docs/UI_DARK_MODE_TECHNICAL_PLAN.md`  
**关系链**：V3 诊断（增量 #2/#3/#5）→ 本实施文档 → 阶段 A/B/C/D/E  
**当前版本**：v1.1（评审后修订）  
**生成时间**：2026-08-23 18:37 GMT+8（v1.0）/ 18:55 GMT+8（v1.1）
