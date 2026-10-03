# ATS-NEW 前端 · 可访问性 & 工程门禁诊断
> 最后更新：2026-09-07（依据 git 最后提交）

> 诊断人：齐活林（交付总监，team-lead）
> 诊断日期：2026-09-03
> 范围：`web/app/src`（97 个 `.vue`，36,210 行；6 个 CSS，1,803 行）
> 权威规范：仓库根 `AGENTS.md` v2.0.0
> 工具：`grep -rE` 全量统计（非抽样），逐条附 `文件:行号`

## 0. 证据等级声明（先说清楚哪些是真验证、哪些不是）

本文严格遵守 `AGENTS.md §0.2` 的可验证性分级，**不做验证剧场**：

| 标记 | 本文占比 | 说明 |
|---|---|---|
| `[S]` 静态可判定 | 全部数字结论 | 由 `grep`/`Read` 得到，附命令与命中数，可复现 |
| `[R]` 需运行时渲染 | **未验证** | 对比度实测、44px 命中区、320px 溢出、暗色别名解析值 —— 本次环境 `npm ci` 被沙箱拒绝（`CODEBUDDY_BROKER_DENY`），无法启动 dev server / Playwright，故**一律不打勾** |
| `[H]` 需人眼判断 | **未验证** | 眯眼测试、视觉层次 —— 需兵哥本人确认 |

> ⚠️ 暗色别名陷阱（`--sl`/`--wl`/`--ph` 在 `body.dark` 下不生效）不在本文范围，见 `architecture-diagnosis.md` §B。其结论来自 **CSS 规范 + 代码事实**的静态推理，证据链完整，但按 `[R]` 规则标注为**待运行时复核**。该陷阱在本项目 2026-08-25 已有同类实证记录，可信度高。

---

## 1. 总体结论（3 句话）

1. **设计 token 治理水平远超平均**：97 个组件里硬编码 hex 仅 2 处、`font-size: Npx` 仅 4 处、无大固定宽容器 —— 这是长期专项治理（T5-design-token-convergence）的真实成果，不是运气。
2. **治理成果没有防回归机制**：颜色门禁插件 `.stylelintrc.json` + `stylelint-plugin-strict-color.cjs` 写得完整正确，但 **package.json 无 script、CI 无步骤**，等于建了门禁没通电；且插件本身存在**扫描盲区**（render function 内联样式字符串扫不到），现存 6 处硬编码正好全在盲区里。
3. **可访问性是最大短板**：`aria-*` 全仓 42 处（0.43 个/组件）、17 处 `div/span @click` 键盘不可达、全局 `focus-visible` 仅 2 条规则 —— 但**无位图内容所以 `alt` 缺失不构成缺陷**（已核实，不误报）。

---

## 2. 可访问性（a11y）实测数据 `[S]`

### 2.1 基线统计

| 指标 | 实测值 | 判定 | 证据 |
|---|---|---|---|
| `<img>` / `<n-image>` | **0 / 0** | ✅ 不适用 | `grep -rc '<img'`、`<n-image` 全仓 0 |
| `alt=` | 0 处 | ✅ **不是缺陷** | 无位图内容，无需替代文本（避免误报） |
| `<svg>` / lucide 图标 | 8 / 19 | ✅ | 图标总量小 |
| `aria-hidden` | 23 处 | ✅ 覆盖充分 | ≥ NIcon 总数 19，装饰图标已标注 |
| `aria-label` | 16 处 | ⚠️ 偏少 | 271 个 `<n-button>` 中大量图标按钮无标签 |
| `role=` | 15 处 | ⚠️ 偏少 | 97 个组件仅 15 处显式 role |
| **`tabindex > 0`** | **0 处** | ✅ **合规** | `AGENTS.md R-109` 明令禁止，实测零违规 |
| `<button>` + `<n-button>` | 39 + 271 | ✅ 语义化良好 | 主体按钮走语义标签 |

### 2.2 P1 缺陷：17 处点击元素键盘不可达

`AGENTS.md R-109` 要求「所有交互元素必须可通过 Tab 访问」。实测 `<div|span @click>` 且**同行无 `role=` / `tabindex`** 的命中：

| 文件:行号 | 元素 | 用户影响 |
|---|---|---|
| `components/dashboard/JobCard.vue:2` | `.job-card` | 工作台职位卡片，键盘用户无法打开职位 |
| `components/dashboard/ScreeningListItem.vue:2` | `.screening-item` | 筛选列表项不可达 |
| `components/common/UploadZone.vue:39` | 选择文件 | **核心上传入口，键盘用户无法上传简历** |
| `components/common/UploadZone.vue:40` | 从人才库导入 | 同上 |
| `components/common/ResumeCard.vue:35` | `.c-header` | 简历卡展开/收起不可达 |
| `components/common/ResumeCard.vue:36` | `.c-chk` 复选框 | **勾选框不可达，无法批量选择简历** |
| `pages/candidate/addCandidate/Step1Batch.vue:34` | 上传区 | 批量录入入口不可达 |
| `pages/candidate/addCandidate/Step2Assign.vue:31,32` | 统一/逐条设置切换 | **模式切换只能用鼠标** |
| `pages/candidate/addCandidate/Step2Assign.vue:60,64` | 提交方式选项 | **单选语义用 div 实现，且不可达** |
| `pages/candidate/CandidateList.vue:108` | 候选人姓名 | 查看详情的入口之一不可达 |
| `pages/settings/ProcessDetailModal.vue:331,344,363` | 折叠头 | 流程规则折叠面板不可达 |
| `pages/demand/DemandList.vue:40` | `.card-left` | **需求卡片主点击区不可达** |

**共 17 处**（`grep -rnE '<(div|span)[^>]*@click' | grep -v tabindex | grep -v role=` 命中数）。

> 另注：`Step2Assign.vue:60,64` 用 `div` 模拟**单选组**（统一/逐条、等待/异步），既无 `role="radiogroup"` 也无 `aria-checked`，屏幕阅读器完全无法感知当前选中项。

### 2.3 P1 缺陷：全局焦点样式仅 2 条规则

`AGENTS.md R-101` 要求每个交互组件实现 `focus-visible`。实测：

| 文件 | `focus-visible` 命中 |
|---|---|
| `styles/glass.css` | **2** |
| `styles/tokens.css` | 0 |
| `styles/brand-tokens.css` | 0 |
| `styles/glass-modal.css` | 0 |
| `index.css` / `App.css` | 0 |

**全站仅 2 条 `focus-visible` 规则**，意味着 Naive UI 默认焦点环 + 2 条自定义规则撑起 310 个按钮的焦点反馈。键盘用户基本无法判断焦点落在哪里。

---

## 3. 工程门禁：建好但没通电 `[S]`

### 3.1 门禁资产齐备（这部分做得好）

- `web/app/.stylelintrc.json`：配置完整，含 `customSyntax: postcss-html`（能解析 `.vue`）、规则 `strict-color/strict-color-value: true`、正确忽略 `brand-tokens.css`（该文件由 CLI 生成，允许字面量）
- `web/app/stylelint-plugin-strict-color.cjs`：自研插件，纯正则零依赖，允许值白名单设计合理（`var()` / gradient / `color-mix()` / `transparent` / 纯黑白）
- `.github/workflows/ci.yml:155-178`：`brand-tokens` job 独立存在，跑 `node brand-tokens.mjs --ci`，符合 `AGENTS.md R-214`
- CI 注释 `ci.yml:6` 与 `ci.yml:147` 显示历史问题 `npm run lint || true` **已被修复**为 `npm run lint:ci`（`--max-warnings=0`）—— 说明团队有门禁意识

### 3.2 P1 缺陷：stylelint 从未被调用

| 检查项 | 结果 | 证据 |
|---|---|---|
| `package.json` 有 stylelint script？ | ❌ 无 | `scripts` 仅含 `lint`(eslint) / `lint:ci`(eslint)，无 stylelint |
| CI `test-frontend` job 跑 stylelint？ | ❌ 无 | `ci.yml:120-153`，步骤为 `npm ci` → `npm run build` → `npm test` → `npm run lint:ci` |
| `brand-tokens` job 跑 stylelint？ | ❌ 无 | `ci.yml:155-178`，仅生成 + `--ci` 校验 |

**结论**：颜色硬编码门禁**从未在 CI 中执行过一次**。当前「97 组件仅 2 处硬编码 hex」是人工治理的存量成果，**没有任何机制阻止明天新增 200 处硬编码**。

### 3.3 P1 缺陷：门禁存在扫描盲区

插件 `COLOR_PROPS` / `SHORTHAND_PROPS` 匹配的是 **CSS 声明**。实测现存 6 处硬编码**全部位于盲区**：

| 文件:行号 | 内容 | 盲区类型 |
|---|---|---|
| `pages/settings/DepartmentManagement.vue:456` | `h('span', { style: 'color: #bfbfbf' }, '—')` | render function 内联字符串 |
| `pages/settings/DepartmentManagement.vue:468` | 同上 | 同上 |
| `pages/candidate/addCandidate/Step1Batch.vue:34` | `style="...font-size:11px..."` | 模板内联 `style` 属性 |
| `pages/candidate/AddCandidateModal.vue:123` | `style="font-size:11px;color:var(--g5);"` | 同上 |
| `pages/settings/CampusControl.vue:1064` | `h('span', { style: 'font-size:12px; color:var(--n-text-color-3,#999);' }, m)` | render function + **幽灵 token 兜底值** |
| `pages/settings/MouManagement.vue:743` | `h('span', { style: 'font-size:12px' }, ...)` | render function |

**这 6 处 = 全仓硬编码 hex 的 100% + 硬编码 font-size 的 100%**，无一例外落在插件扫不到的地方。即便门禁通电，也抓不到它们。

> 附带发现：`CampusControl.vue:1064` 的 `var(--n-text-color-3,#999)` 带兜底值 `#999`，这种「token + 硬编码兜底」写法是 token 体系的隐蔽漏洞 —— token 一旦失效就静默降级到硬编码色。

### 3.4 环境限制说明（诚实标注）

本次尝试 `npm ci` 实测 stylelint，被沙箱策略拒绝：

```
npm error code CODEBUDDY_BROKER_DENY
npm error Brokered host mkdir requires an available runtime file rule
```

故 **3.2/3.3 的结论基于静态配置核查（配置内容 + CI 步骤 + package.json），未做 stylelint 实跑验证**。结论本身不依赖实跑（"CI 里没有这一步"是文件事实），但「存量违规总数」这个数字**本次无法给出**，需在能装依赖的环境补测。

---

## 4. 状态覆盖与性能 `[S]`

### 4.1 加载 / 空态 / 分页 —— 修正后的真实水位

> ⚠️ 开篇摸底时因 `grep` 未加 `-E`（`\|` 在 BRE 下不生效），曾得出「分页 0 处、空态 24%」的错误数字。以下为**修正后**的实测值。

| 能力 | 实测值 | 判定 |
|---|---|---|
| `:loading=` 绑定 | **101 处** | ✅ 覆盖良好 |
| loading 状态变量声明 | 62 个 | ✅ |
| `<n-spin>` | 16 处 | ✅ |
| 分页（`:pagination=` + `<n-pagination>`） | 56 + 2 处，**31/97 文件** | ✅ 覆盖良好 |
| `<n-empty>` | 36 处 | ⚠️ 见 4.2 |
| 骨架屏 `skeleton` | 24 处 | ⚠️ 覆盖不完整 |
| `EmptyState.vue` 组件 | 定义存在，**仅 1 处引用** | ❌ 资产闲置 |

### 4.2 P2 缺陷：空态组件建了不用

`components/common/EmptyState.vue`（1058 字节）是专门封装的空态组件，但全仓**只在 `pages/Dashboard.vue:66` 用了 1 次**；其余 36 处空态各自直接用 `<n-empty>`。

后果：空态的插图、文案、操作按钮**没有统一标准**，每个页面自行发挥。这是典型的「组件资产沉淀了但没被采纳」。

### 4.3 P2：9 个 data-table 无分页

`AGENTS.md R-108` 要求条目 > 200 时虚拟化或分页。39 个文件含 `n-data-table`，其中 **9 个没有任何分页配置**：

`App.vue`、`pages/candidate/AddCandidateModal.legacy.vue`、`pages/offer/BackgroundCheckPanel.vue`、`pages/settings/StageRuleConfigModal.vue`、`pages/settings/permission/TemplatesTab.vue`、`RolesTab.vue`、`UserRolesTab.vue`、`pages/notification/NotificationList.vue`、`pages/demand/DemandList.vue`

> 前几个可能是 `n-data-table` 的误匹配或弹窗内小表，风险最高的是 **`NotificationList.vue`**（消息通知量随时间单调增长，无分页必然撑爆）。

### 4.4 性能敏感项

| 指标 | 实测值 | 风险 |
|---|---|---|
| `backdrop-filter` | CSS 48 + Vue 36 = **84 处** | 毛玻璃是 GPU 密集型，84 处叠加在低端机/远程桌面上会明显掉帧；`Login.vue:7` / `Layout.vue:7` / `ProcessDetailModal.vue:6` 最集中 |
| `!important` | CSS 98 + Vue 157 = **255 处** | 样式优先级军备竞赛，后续任何样式调整都越来越难 |
| 内联 `:style=` | 46 处 / 25 文件 | 绕过主题切换，暗色模式下可能不跟随 |
| `@media` 响应式 | 42 处 / **22 个文件（23%）** | 桌面端产品可接受，但 Dashboard / 候选人列表应至少有窄屏降级 |

`!important` 最集中的文件：`pages/Layout.vue:44`、`pages/settings/DataDictionary.vue:36`、`ProcessDetailModal.vue:19`、`SettingsLayout.vue:12`。

---

## 5. 本次诊断的「不能打勾」清单

按 `AGENTS.md §0.2`，以下为 `[R]`/`[H]` 项，**本次未验证，禁止视为已通过**：

- [ ] `R-102` 触控目标 ≥ 44×44px（需渲染后测量伪元素命中区）
- [ ] `R-103` 320px 视口无横向溢出
- [ ] `R-109` 对比度 ≥ 4.5:1（需取计算色 + 实测；`--ink-faint: #64748B` 注释自称 4.8:1，需复算）
- [ ] `R-201` 320/768/1200 三档验收
- [ ] `R-202` 一屏一主角（眯眼测试，需人眼）
- [ ] 第 3 节暗色别名陷阱的实际渲染表现
- [ ] `npm run build` 通过性、`npm test` 通过性（依赖未安装，未跑）

---

## 6. 建议的整改优先级（本部分视角）

| 优先级 | 整改项 | 成本 | 收益 |
|---|---|---|---|
| **P0** | 给 `package.json` 加 `stylelint` script + CI 步骤（3 行改动） | 极低 | 让已有治理成果具备防回归能力 |
| **P1** | 修 17 处 `div/span @click`（加 `role="button"` + `tabindex="0"` + 键盘事件） | 中 | 键盘用户可用，合规风险清零 |
| **P1** | 补全局 `:focus-visible` 基础规则（1 条 CSS 覆盖全部可聚焦元素） | 极低 | 键盘可用性质变 |
| **P1** | 插件补 render function / 内联 style 扫描，或清理那 6 处盲区硬编码 | 中 | 门禁真正闭环 |
| **P2** | `EmptyState.vue` 推广替换 36 处 `<n-empty>` | 中 | 空态体验统一 |
| **P2** | `NotificationList.vue` 补分页 | 低 | 避免数据增长撑爆 |
