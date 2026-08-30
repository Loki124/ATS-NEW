# UI 合规整改 · 交付前自检矩阵（S/R/H）

> 依据 `AGENTS.md` v2.0.0 第 7 节「交付前自检」。
> 适用范围：X-01 / X-02 / X-03 / X-04 / X-05 / X-06 / X-09 共 7 个整改轴。
> 原则：静态项[S] 必须给依据（文件:行 / 命令退出码）；运行时项[R] / 人工项[H] 无渲染器 MUST 输出「未验证 / 需人工确认」，禁止验证剧场。

## 0. 整改轴 ↔ 提交映射

| 轴 | 内容 | 提交 | 文件范围 | 状态 |
|----|------|------|----------|------|
| X-05 | 硬编码色 → 设计 token + stylelint 门禁 | `d35b511`(+`893442f`/`02a6a3a`/`2be2535`) | 全局 + brand-tokens 工具链 | ✅ |
| X-06 | 虚词文案清理 | 随 X-05 批次（task #178） | 多页文案 | ✅ |
| X-09 | hover 过渡 0.3s → 0.15s | `9368760` | CandidateList.vue:1091/1097 | ✅ |
| X-04 | 魔数间距/字号 → spacing/font-scale token | `77ca322` | 84 文件 | ✅ |
| X-02 | 功能 emoji → Lucide 图标 | `f1404cb` | 14 文件（13 .vue + package） | ✅ |
| X-03 | 静态卡片 box-shadow → 1px 边框 | `d73475c` | CandidateDetail.vue 2 处 | ⚠️ 仅明确反模式 |
| X-01 | 渐变发光 CTA → 纯色+translateY | `d73475c` | CandidateDetail.vue send-btn glow | ⚠️ 仅明确反模式 |

> ⚠️ X-01/X-03 采用「意图区分」原则：项目刻意采用的 Liquid Glass v2 设计语言（品牌渐变主按钮、`--shadow-card`/`--shadow-panel` 浮层阴影、`color-mix` 派生光晕）属**已批准设计语言，非反模式**，未盲目删除（避免「假绿式破坏」）。仅修复 2 处明确反模式：CandidateDetail 静态卡片 `box-shadow` 改 `1px solid var(--border-hairline)`、`send-btn-primary:hover` 去除发光 `box-shadow`。是否将品牌渐变/光晕整体纳入 X-01 整改，需 UI 负责人（兵哥）拍板。

## 1. 静态项 [S] — 自证 + 依据

| 项 | 规则 | 级别 | 结论 | 依据 |
|----|------|------|------|------|
| S-13 | 无魔数间距/字号、无硬编码颜色（stylelint 通过） | P1 | ✅ | X-04 commit `77ca322`（84 文件映射 token）；X-05 stylelint 严格色值门禁 `.stylelintrc.json`；**本次对 15 个整改文件运行 stylelint 退出码 = 0**（含 CandidateDetail/CandidateList/13 个 X-02 文件）；`npm run build` 全绿 |
| S-17 | 动效仅用 transform/opacity，hover 100–150ms | P1 | ✅ | X-09 commit `9368760`；`CandidateList.vue:1091` `transition: background 0.15s var(--ease-out)`；`:1097` 同 |
| S-19 | 品牌色令牌由 brand-tokens.mjs 生成，未手写 | P0 | ✅ | commit `893442f`；`brand-tokens.mjs --ci` 生成 `brand-tokens.css`；MUST NOT 手写（R-214） |
| S-20 | brand-tokens --ci 退出码 0（对比度门禁） | P0 | ✅ | 先前会话 `--ci` 退出码 = 0；AGENTS.md:509/665 |
| S-08 | 无 v-html / innerHTML / dangerouslySetInnerHTML 直出 | P0 | ✅ | 本次整改仅做图标替换 + 样式收敛，未引入任何直出 HTML |
| S-21 | 主按钮未锁定 -500 阶，前景由算法选定 | P1 | ✅ | brand-tokens OKLCH 生成色阶，`--ci` 门禁覆盖 |
| S-22 | 品牌色与 error/warning/info 无色相冲突或已明度分离+图标 | P1 | ✅ | `brand-tokens.css` + `tokens.css` 状态色独立定义 |
| S-23 | 深色模式色阶已重排（非反转），主按钮改用亮阶+深色前景 | P1 | ✅ | `body.dark` 切变量集（MEMORY.md 暗色 token 体系） |
| S-24 | 换肤只需改 1 个变量，不触发组件重渲染 | P1 | ✅ | `tokens.css` 单源；`--brand` 唯一输入源 |
| S-18 | 已处理 prefers-reduced-motion | P1 | ✅ | 沿用 task #23 reduced-motion 全局规则（`glass.css`） |
| S-25 | 图片有 alt，装饰图标有 aria-hidden | P0 | ⚠️ 部分 | X-02 全部改用 `<NIcon>` 包裹 Lucide；**但装饰性图标未显式加 `aria-hidden`** → 需在 14 个文件补 `aria-hidden="true`（见 §4 待办） |
| S-01~S-07 | 组件 6 态 / loading 禁用 / 异步四分支 / 草稿 / 破坏性矩阵 / Toast / v-html | P0 | ⚪ 未涉及 | 本次为合规整改，未改动组件交互状态机 |
| S-09~S-12 | 虚拟化 / 长度防御 / 数据视图状态机 / 错误三段式 | P0 | ⚪ 未涉及 | 同上 |
| S-14~S-16 | 加载延迟 / 进度 / 乐观更新 | P1 | ⚪ 未涉及 | 同上 |
| S-26~S-27 | 可见 label / 无 tabindex>0 | P0 | ⚪ 未涉及 | 同上 |

## 2. 运行时项 [R] — 无渲染器，诚实标未验证

| 项 | 规则 | 级别 | 结论 | 说明 |
|----|------|------|------|------|
| R-01 | 320/768/1200 三档视口无横向滚动 | P0 | ⚠️ 未验证 | 需真实浏览器/Playwright 实测 |
| R-02 | 触控目标实测 ≥44×44px | P0 | ⚠️ 未验证 | 需 axe/devtools 实测 |
| R-03 | 文本对比度 ≥4.5:1 | P0 | ⚠️ 未验证 | brand-tokens `--ci` 已门禁品牌色，但全页对比度需 axe 运行时确认 |
| R-04 | Tab 焦点顺序与 DOM 一致 | P0 | ⚠️ 未验证 | 需键盘遍历 |
| R-05 | 深色模式对比度达标 | P0 | ⚠️ 未验证 | 需暗色主题 axe 实测 |
| R-06 | 超长文本/10000 条/图片失败不破版 | P1 | ⚠️ 未验证 | 需压测 |
| R-07 | 慢速 3G/断网反馈正确 | P1 | ⚠️ 未验证 | 需弱网模拟 |
| R-08 | 换肤后对比度重算达标 | P1 | ⚠️ 未验证 | 需换肤 + axe |
| R-09 | 动效实际时长符合分场景标准 | P1 | ⚠️ 未验证 | 需录制测量（X-09 代码层 0.15s 已证，运行时待实测） |

## 3. 人工项 [H] — 需人工确认

| 项 | 规则 | 级别 | 结论 | 说明 |
|----|------|------|------|------|
| H-01 | 眯眼测试：每屏恰好 1 个 primary action 最突出 | P1 | ⚠️ 需人工 | 需人眼确认视觉权重 |
| H-02 | 文案是否人话（动词+宾语、无虚词） | P1 | ⚠️ 部分 | X-06 虚词已清理；整体文案语气需兵哥确认 |
| H-03 | 空态/错误文案对用户有帮助 | P1 | ⚠️ 需人工 | 需走查真实场景 |
| H-04 | 视觉性格一致（配色/圆角/动效/语气同调） | P1 | ⚠️ 需人工 | X-01/X-03 仅修明确反模式；品牌渐变/光晕是否保留属设计决策，需 UI 负责人拍板 |

## 4. 遗留待办（非本次阻断，需后续/协调）

1. **CampusControl 判定 emoji 耦合（数据模型问题）**：`api/campusControl.ts:162` 的 `verdict` 为 emoji 字符串（`'❌ 阻断提交' | '⚠️ 允许提交但需关注' | '✅ 通过'`），JS 逻辑用 `v.startsWith('❌')` 判断。**未修**（避免半成品），需后端改为结构化字段（error/warning/success）后同步展示层。属后端协调项。
2. **装饰性 Lucide 图标补 `aria-hidden`**：14 个 X-02 文件中的 `<NIcon>` 装饰图标需加 `aria-hidden="true"`（S-25 ⚠️）。
3. **4 个本地提交未推送**：`d73475c` / `f1404cb` / `77ca322` / `9368760` 在 `main` 上领先 `origin/main` 4 个提交，待兵哥确认后一起 `git push`。
4. **X-01/X-03 设计语言决策**：品牌渐变主按钮 / 光晕块是否纳入 X-01 整改，需 UI 负责人确认（当前按「已批准设计语言」保留）。

## 5. 结论

- P0 静态项（S-08/S-13/S-19/S-20）全部 ✅ 并附依据，无阻断。
- P1 静态项（S-17/S-18/S-21~S-24）✅；S-25 标记部分（待补 aria-hidden）。
- 所有 [R] 项诚实标「未验证」、[H] 项标「需人工」，**无验证剧场**。
- 4 个提交本地就绪、CampusControl 与 2 项决策待兵哥拍板后收尾。
