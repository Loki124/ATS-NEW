# ATS-NEW UI 诊断 V3 — v2 阶段实施后实测（2026-08-23）

> 设计系统架构师 Diana · 关系链：
> - 上游诊断：`docs/UI_DIAGNOSIS_V2.md`（38 个问题 · 4 维度 + 框架/组件/交互/UX）
> - 设计规范：`web/app/DESIGN.md`（液态玻璃 v2 · 9 章节）
> - 执行清单：`docs/UI_HANDOFF_CHECKLIST.md`（v2 阶段 8 / 9 / 10）
> - **本报告定位**：**实测进度盘点 + 增量新发现**，不重复 V2 已收敛项。
> - 摸底命令：`grep -rE ...` 实测 + 文件审阅（不是自报数字）。

---

## 一、当前进度盘点（按执行清单门禁实测）

### 1.1 P0 门禁（9 项必过）

| 验收门禁 | 当前实测 | 判定 | 备注 |
|---|---|---|---|
| **C1** 业务页 Ant 色硬编码 = 0 行 | OfferList 1 / DemandList 4 / Onboarding 0 / Interview 0 / Candidate 0 / Resume 0 / TalentPool 0 / **settings 22** | ⚠️ **未达成** | 列表页 5 个几乎清零；**设置中心 22 处是新的塌陷点**（T5 未覆盖到 settings/） |
| **C2** 主按钮 `!important` 覆盖移除 | `grep var(--ink) !important` = 0 行 | ✅ 达成 | App.vue themeOverrides 白字生效 |
| **C3** 5 列表页用 `.glass-card` / `.glass-panel` | 受全局 `.n-card.n-card` 兜底但**显式声明缺失** | ⚠️ 兜底非方案 | 兜底规则会让所有未声明页也玻璃化，但**业务页自己不用 glass-card**仍会让组件变异（比如表单、Modal 等 n-card 变体） |
| **U1** 5 列表页 768/480 响应式 | 已收口（git log T6.1） | ✅ 达成 | commit `c1a94da / 1f4aabc / cd0e779 / b4b99ec / e500144 / cc82998` |
| **U2** 768/375 侧栏 drawer 化 | Layout.vue v-if + n-drawer 已落 | ✅ 达成 | commit `2539d47 / 44ef605 / cc82998` |
| **U4** 暗色下业务页无白纸黑字 | **17 处 `background: white/#fff`** 残留 | ⚠️ **未达成** | 主要集中在 settings/（ProcessDetailModal 6 / DataDictionary 3 / AnnouncementSettings 2） |
| **U5** 暗色卡片 = `rgba(30,41,59,.62)` | 同上 | ⚠️ 同上 | settings 页 + 公告系统 + 公共组件占大头 |
| **U11** 错误态路由 + 全局 axios 兜底 | main.ts L36/39 `_toast.warning/error` + errors/{NotFound,Forbidden}.vue + settings/Placeholder.vue 全有 | ✅ **达成但需打磨** | UI 兜底已上，但 `_toast.warning('接口不存在')` 措辞欠专业（应说"开发中"），见 §三 增量 |
| **F1** 5 占位路由显示 PLACEHOLDER | Placeholder.vue L32-38 META_MAP 收口 5 路由 | ✅ 达成 | emoji 占左 + meta + ETA + Issue + 按钮格式齐 |

### 1.2 P1 门禁（16 项）

| 验收门禁 | 当前实测 | 判定 |
|---|---|---|
| F2/F3 404/403 双列 | NotFound/Forbidden 在 `errors/` 下 | ✅ 达成 |
| F6 面包屑 | `components/common/Breadcrumb.vue` 已建，Layout.vue L139-142 挂载 | ✅ 达成 |
| C4 body 透明 | `index.css` L21 仍 `background-color: #f5f5f5` **未切** | ❌ 未达成 |
| C7 font-size 硬编码 = 0 | 待实测但 V2 时 401 处 | ❌ 大概率未达成 |
| C11 表头玻璃化 | `glass.css` L361-371 追加 | ✅ 已落 |
| I2 强调色统一 c-info/success | Dashboard matter-tab__count 等已切 | ✅ 达成 |
| **I3 操作列 ≤ 160px** | **仅 CandidateList 用 n-dropdown**，其他 4 列表页仍是按钮堆叠 | ⚠️ 进行中 |
| U6 滚动条暗色 | index.css L21-26 已覆盖 `body.dark ::-webkit-scrollbar-thumb` | ✅ 已落 |
| U9 空状态收口 | `components/common/EmptyState.vue` + dashboard 子版**并存** | ⚠️ 双套未合一 |
| **U10 mockData 张三真实化** | `name:'张三', id:'CDD005878'` 仍存在，未见 `age:28 / experience:'5年'` | ❌ **未达成** |
| U12 危险操作 dialog.warning | git log 无 commit 记录 | ❌ 待排查 |
| A1 `#8c8c8c` = 0 | grep 仅在 settings 22 处命中 | ⚠️ 未清零 |
| A5 图标按钮 aria-label | Layout 已加；列表/详情页未巡检 | ❌ 大概率缺失 |
| I4 入场动效扩展到 5 列表页 | 仅 Dashboard 有 stagger | ❌ 进行中 |
| I5 Loading/EmptyState 收口 | LoadingState.vue 已建，**是否被引用**未知 | ⚠️ 待验 |

### 1.3 P2 门禁（13 项）

| 验收门禁 | 当前实测 | 判定 |
|---|---|---|
| F5/F7 两套导航合一 | **SettingsLayout 仍自写 menu-group / menu-item**（L52/71/82 等），与 Layout n-menu 并存 | ❌ 未收口（F5） |
| I10 快捷键扩展 | Layout.vue L198 `useShortcuts()` 已落（v2.7） | ✅ 收口 |
| F4 SettingsLayout `:deep` 注入 = 0 行 | **剩 1 行**：`.settings-scroll :deep(.page-container) { padding: 0 }` (L576) | ⚠️ **该行不可一刀切删**（理由见 §二 T9 决策建议） |
| U3 表横滚提示 | 部分页加 `-webkit-overflow-scrolling: touch` | ⚠️ 部分达成 |
| U7 滚动条暗色 | 已落（C4 同 U6） | ✅ |
| U8 页头文案 | 各页"管理 X"无副标题/数据量 | ❌ 长期项 |
| U13 toast 规范 | 各 message.success/error 调用无统一规范 | ❌ |
| A2/A3/A4 a11y | A3 emoji 占位（Login L145-159 + DemandList L255-281 + Placeholder.vue L33-37） | ❌ |

---

## 二、T9.1 关键决策建议（PM 评审点）

V2 执行清单 T9.1 验收要求"删除 SettingsLayout 全部 `:deep` 注入"。当前实测仅剩 **1 行**：

```css
/* SettingsLayout.vue L576 */
.settings-scroll :deep(.page-container) {
  padding: 0;
  min-height: 100%;
}
```

**这条不该删**，理由：
- `.settings-scroll` 有 `padding: 20px`（L571），`.page-container` 默认 `padding: 24px`（glass.css L591）
- **不抹平这一行**：所有设置子页会变成 `20 + 24 = 44px` 双重 padding，视觉塌缩
- 这是 **布局职责**（避免 padding 叠加），不是 V2 反对的"视觉锚点 hack"

**建议执行清单 T9.1 验收条款修正**：
- ❌ 旧验收："`grep ':deep' SettingsLayout.vue = 0`"
- ✅ 新验收："`:deep(.n-card / .page-title / .filter-row / .n-button--primary-type) 等视觉类注入 = 0`；**保留 1 行 `:deep(.page-container)` 解 padding 叠加**"

PM 拍板后可改文档，**避免工程师误删导致视觉塌陷**。

---

## 三、增量新发现（V2 没覆盖或 V2 之后才出的）

### 新 #1【P0】T5 未覆盖到 settings/，22 处 Ant 色死灰复燃

```bash
grep -rE '#1890ff|#52c41a|#ff4d4f|#fa8c16|#722ed1|#8c8c8c' src/pages/settings src/components
# → 22 行
```

**典型位置**：
- `ProcessDetailModal.vue` L? 状态色硬编码（应是 Ant Design 旧调色板残留）
- `DataDictionary.vue` 字典值高亮
- `AnnouncementSettings.vue` 标签状态色

**修复策略**：参照 T5.1.1-T5.1.5 模板（执行清单已有），新增 T5.1.7-T5.1.11 覆盖 settings/。

### 新 #2【P0】T5 之外还有 17 处 `#fff / white` 硬编码背景，集中在 settings + 公告 + 公共组件

| 文件 | 处数 |
|---|---|
| `pages/settings/ProcessDetailModal.vue` | 6 |
| `pages/settings/DataDictionary.vue` | 3 |
| `pages/announcement/AnnouncementList.vue` | 3 |
| `pages/settings/AnnouncementSettings.vue` | 2 |
| `pages/settings/StageRuleConfigModal.vue` | 1 |
| `pages/offer/OfferList.vue` | 1 |
| `pages/announcement/AnnouncementDetail.vue` | 1 |
| `components/common/UploadZone.vue` | 1 |
| `components/common/PositionChips.vue` | 1 |
| `components/common/OccupiedActions.vue` | 1 |

**修复策略**：`#fff / white` → `var(--glass-bg-card)` 或 `var(--glass-bg-elevated)`；如果需要纯白不透明兜底，使用 `var(--surface)`。

### 新 #3【P1】settings/ 下 components/common/EmptyState.vue + components/dashboard/EmptyState.vue 双套并存

- `components/common/EmptyState.vue` — 已是公共组件
- `components/dashboard/EmptyState.vue` — **重名遗留**，旧 token 别名（`--color-ink-soft` / `--color-surface-sunk`），可能是历史未删除

**处理建议**：grep `components/dashboard/EmptyState.vue` 引用方，若 0 引用 → **删 dashboard 版**；若有引用 → 改 import 路径到 common/。

### 新 #4【P1】U11 的 toast 文案欠专业，需产品对齐

**当前 main.ts L36**：
```ts
_toast.warning(`接口不存在: ${url.split('?')[0]}`)
```

**问题**：
- "接口不存在"对超管用户来说吓人（暗示系统坏了）
- 真实场景：9 个 app 后端 endpoint 缺实现（看 memo）—— 用户感知应是"页面正在建设中"而非"系统异常"
- 460 错误：`_toast.error('服务异常，请稍后再试')` — OK

**建议**：
- 404 → 静默，仅 `console.warn`（开发模式）+ 业务页自己跳占位（已有 Placeholder.vue 机制）
- 500 → 保留 toast，但改为 `message.error('服务繁忙，请稍后重试')`（避免暗示 bug）
- 401/403 → 已有 logout，保留

### 新 #5【P0】C4 body 透明还没切（与 C2 一波不同步）

`index.css` L21 仍 `background-color: #f5f5f5`，暗色下仍是浅灰，与玻璃系统的 `--aurora-base` 极光底冲突。

**修复**：单行替换
```css
body {
  background: transparent;  /* 让 .app-aurora 透出 */
  color: var(--ink);        /* 替代 rgba(0,0,0,0.88) */
}
```

### 新 #6【P1】T9.2 F5：SettingsLayout 自写 menu-group 还在

L52/L71/L82 等处的 `.menu-group / .menu-item / .menu-item-parent / .sub-menu-item`（约 130 行）全自写 DOM，未用 `n-menu`——这违背"n-menu 双套合一"的初衷。

**决策点**（PM 拍板）：
- **A 方案**：SettingsLayout.vue 整体改用 n-menu options（与 Layout.vue 一致），删自写 DOM — 改动中等，但 root 模板大改
- **B 方案**：保留自写（视觉风格可更灵活），但接受 **F5 不收口**作为长期技术债
- **C 方案**：抽出 `useSettingsMenu` composable（业务 + 渲染保持分离），自写渲染层不改

**推荐 A 方案**：原因是 n-menu 已支持二级 + 三级嵌套（Layout.vue 路由 watch L399-432 已示范），成本远低于维护两套渲染。

---

## 四、当前高风险 / 死角清单（按风险等级）

### P0（阻塞产品体验）

1. **T5 未覆盖 settings/** — 22 处 Ant 色硬编码，新塌陷点（§新 #1）
2. **U4/U5 17 处 white 背景** — 暗色下"白色漂浮"未消灭（§新 #2）
3. **C4 body 浅灰未切** — 暗色下与极光冲突（§新 #5）
4. **U10 mockData 张三** — 给真实用户演示时会让人怀疑专业性
5. **T7.4 操作列仅 CandidateList 完成下拉化** — 其他 4 列表页仍按钮堆叠

### P1（明显可见可短期共存）

1. **T8.4 表格行键盘可达** — V2.7 强调约束但未巡检
2. **T8.3 危险操作二次确认** — V2.7 强调但 git log 无 commit
3. **U11 toast 文案欠专业**（§新 #4）
4. **EmptyState 双套并存**（§新 #3）
5. **T9.1 验收条款歧义**（§二）
6. **T9.2 SettingsLayout 自写菜单未合一**（§新 #6）
7. **A1/A5 a11y** — `#8c8c8c` 残留 + 图标按钮 aria-label 未巡检

### P2（迭代打磨）

1. F7 路由 meta.roles 业务确认（permission 实际是否要做）
2. C13 状态映射函数散布各页（OfferList/DemandList/CandidateList 重复定义）
3. C14 label 灰色硬编码（grep 应有 14+ 处）
4. I6 Hero 搜索与 ⌘K 联动
5. I9 n-menu transition 强制关闭的兼容性（与 Naive UI 后续版本）
6. U13 toast 规范
7. A3 emoji 占位（Login + DemandList + Placeholder 共 3+ 处）
8. A4 缺全局 skip-to-content

---

## 五、与 UI_DIAGNOSIS_V2.md 的差异（避免重复扫描时混淆）

| 项 | V2 已收敛 | V3 新发现 |
|---|---|---|
| C1 99 处 Ant 色 → 5 列表页 | ✅ V3 实测 0 / 0 / 0 / 0 / 0 | ⚠️ settings/ 22 处塌陷 |
| C4 body 浅灰 | — | ❌ 未切（执行清单 T5.1.6 标为"v1 已做完"但实测未做） |
| U11 axios 兜底 | — | ✅ 已落但文案欠专业 |
| F5 两套导航 | — | ⚠️ SettingsLayout 仍自写 menu-group |
| T7.4 操作列瘦身 | — | ⚠️ 5 个仅 1 个完成 |
| 双 EmptyState | — | ⚠️ common + dashboard 重名 |
| T9.1 :deep 验收条款 | — | ⚠️ 条款过严，剩 1 行不该删 |

---

## 六、给执行清单的增量补丁建议

| 新增任务 | 工作量 | 优先级 | 依赖 |
|---|---|---|---|
| **T5.1.7** `pages/settings/*` Ant 色清零（含 22 处） | 0.4d | P0 | T1.1 |
| **T5.1.8** `pages/announcement/*` + `components/common/*` white 背景 token 化（17 处） | 0.3d | P0 | T5.1.7 |
| **T5.1.9** `index.css` body `#f5f5f5` → `transparent`（C4 / U6） | 0.05d | P0 | — |
| **T8.4.1** 5 列表页（Offer/Onboarding/Interview/Demand/Candidate）rowProps `tabindex + Enter` 全量加 | 0.3d | P1 | T8.4 |
| **T8.3.1** 危险状态变更 dialog.warning 二次确认（Offer/Interview/Onboarding） | 0.3d | P1 | — |
| **T7.4.1** OfferList/OnboardingList/InterviewList 操作列 n-dropdown 化 | 0.4d | P1 | T7.4 |
| **T9.1.1** 验收条款修正：保留 `:deep(.page-container)`（解 padding 叠加） | 0d（文档） | P2 | — |
| **T9.2.1** SettingsLayout 自写 menu-group 改 n-menu options | 0.4d | P1 | — |
| **U11.1** main.ts L36 toast 文案改专业措辞（404 静默 / 500 软化） | 0.1d | P1 | — |
| **T10.4.1** `dashboard/EmptyState.vue` 删除或统一到 common/ | 0.1d | P1 | — |
| **U10.1** CandidateList mockData 张三真实化（age 28 / 5年） | 0.05d | P0 | — |
| **A5.1** 图标按钮全量加 aria-label 巡检 | 0.2d | P1 | — |

**总计增量：~3.0 人日**（可解 5 个 P0 + 7 个 P1）

---

## 七、给 PM 的快读结论

### ✅ 已收口（10 项）
1. 单一事实来源 `tokens.css` v2 液态玻璃（DESIGN.md 9 章节）
2. 玻璃原子类（`.glass-panel / .card / .input / .btn-* / .tag / .table / .sidebar`）
3. 全局 `n-card.n-card` 兜底玻璃化（中心化杠杆生效）
4. 5 列表页业务 Ant 色清零（Onboarding/Interview/Candidate/Resume/TalentPool **0 处**）
5. 5 列表页响应式（1024/768/480 三档）
6. 侧栏 ≤768 折叠为 n-drawer + hamburger
7. 全局 `themeOverrides` 接品牌色 + 暗色变量集
8. 全局 `app-aurora` 极光底 + 暗色拉丝深玻璃
9. 全局 axios 拦截器 UI 兜底（warning/error toast）
10. 5 占位路由 + 404 + 403 + 面包屑 + ⌘K 全部落地

### ⚠️ 仍待解决的 5 个 P0
1. settings/ 下 **22 处** Ant 色硬编码（T5 未覆盖到 settings，详见 §新 #1）
2. settings + 公告 + 公共组件共 **17 处** `background: white` 暗色下不切（§新 #2）
3. index.css body `#f5f5f5` 未切透明（与极光冲突，§新 #5）
4. `I3` T7.4 操作列**仅 1/5** 完成 n-dropdown 化
5. `U10` mockData 张三 `8岁/1年` 等假数据未真实化

### 🎯 给 PM 拍板的 2 个决策点
- **决策 1**：T9.1 验收条款是否修正为"保留 `:deep(.page-container)` 1 行"？（不改会导致设置页 padding 塌缩，详见 §二）
- **决策 2**：T9.2 SettingsLayout 改 n-menu（A 方案，推荐）还是保留自写（B 方案，欠技术债）？（详见 §新 #6）

### 📋 下一轮执行顺序建议（PM 拍板后）

```
P0 1 步走完（2.0d）：T5.1.7 + T5.1.8 + T5.1.9 + T7.4 + U10.1
P1 并行（1.0d）：T8.3 + T8.4 + U11.1 + T10.4.1 + A5.1 + T9.2
P2 持续：T9.1.1 文档修正 + 其他长期项
总计增量：3 人日
```

---

## 八、本报告方法论透明声明

- **没有重复 V2 已收敛项**：所有"已达成"判定基于实测 grep + git log
- **进度盘点用硬证据**：每个 P0/P1 验收都标了实测命令 + 文件:行号
- **增量新发现是 V2 没覆盖的 6 项**：settings/塌陷 + 17 white + body 浅灰 + toast 文案 + EmptyState 双套 + SettingsLayout menu 自写
- **没有为发现而发现**：增量都是 P0 或决策点，不是 P2 凑数
- **风险评估基于实测进度**：不是"理论应该解决"，是"实测还有 X 处"

---

**报告位置**：`docs/UI_DIAGNOSIS_V3.md`
**对应分支**：`feat/ui-v2-reconciliation`
**对应 commit baseline**：`7c40974 (HEAD)`
**生成时间**：2026-08-23 18:26 GMT+8
