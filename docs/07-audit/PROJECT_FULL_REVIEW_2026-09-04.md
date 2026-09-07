# ATS-NEW 项目全盘复评报告（2026-09-04 · 距上次 9 天）

> **检查方式**：全量实测 grep/find/git 计数，与 `docs/PROJECT_FULL_REVIEW_2026-08-26.md` 做**逐项对比**。
> **基线**：`main @ 3595654`，工作区**干净**（上次未提交的 campus_control indicator 改动已 commit `ccd79e8`）。
> **窗口**：2026-08-26 → 2026-09-04，**158 次 commit**，作者**仅 loki**（单人）。

---

## 0. 总评：上次 6 项 B/A-，这次基本盘没升，但「债务处理」动真格了

| 维度 | 上次 (08-26) | 本次 (09-04) | 变化 |
|---|---|---|---|
| 产品完成度 | A- | **A-** | 持平，数据看板导出真落地，interview 评价弹窗接入 |
| 后端架构 | B+ | **B+** | 持平，campus_control 加了 services.py（261 行），但 views.py 反涨到 1115 行 |
| 后端质量 | B | **B+** | ⚠️ 微升：测试从 772 → **986**（+27.7%），但 except Exception 从 122 → **154**（恶化 26%） |
| 前端工程 | B+ | **A-** | ⬆️ 显著提升：硬编码 hex 从 466 → **81**（-83%），v-html 收敛到 SafeHtml 单点，composables 1→4 |
| 设计体系 | B+ | **A-** | ⬆️ UI 审计 PR 主线兑现，tokens/glass 体量翻倍，审计闸门落地 |
| 文档健康度 | C+ | **B-** | ⬆️ 数据看板导出端点不再 404；规模数字仍多套，但新增 commit 比对基线 |

**一句话**：9 天里主战场在 UI/UX 合规改造和 campus_control 收口，**前端跃迁最大**、**后端在测试覆盖率上前进但 fail-open 还在恶化**、**stub 端点治理未动**。

---

## 1. 数字对照（实测，不沿用上次）

| # | 指标 | 08-26 | 09-04 | Δ | 备注 |
|---|---|---|---|---|---|
| 1 | Django apps（目录） | 35 | **38** | +3 | `rule_engine` 模块新增（13 类；含 adapters/bridge/integrations 子目录） |
| 2 | Model 派生类（含中间基类） | ~97（口径偏宽） | **77** | 更严格口径 | 实际更稳的派生数 |
| 3 | ViewSet + APIView 视图类 | 66+21=87 | **65+19=84** | -3 | 部分 view 合并/下沉到 service |
| 4 | config/urls.py 主路由 | 59（48 include） | **62**（urls.py 191 行） | +3 | 包含 `ed0b23e` 数据看板通用导出 |
| 5 | pytest test_*.py 文件数 | 82 | **108** | +26 | 测试金字塔持续扩张 |
| 6 | pytest def test_ 函数数 | 772 | **986** | +214（+27.7%） | 测试资产是真硬通货 |
| 7 | vitest .test.ts 文件数 | 30 | **31** | +1 | |
| 8 | vitest it/test( 用例 | 124 | **140** | +16 | |
| 9 | migrations 目录 | 32 | **33** | +1 | |
| 10 | 前端 .vue 总数 | 66 | **99** | +33 | 含弹窗/子组件展开 |
| 11 | 前端 API 客户端数 | 30 | **30** | 0 | 见后端债#1（仍复制粘贴） |
| 12 | 前端 `any` 出现 | ~498 | **558** | +60（恶化） | strict 名义开，实际逃逸增加 |
| 13 | 前端硬编码 hex 出现 | 466（33 文件） | **81（21 文件）** | **-83%** | ⬆️ UI 收敛主战场成果 |
| 14 | 巨型组件 ≥1000 行 | 7 | **8** | +1 | 新增 ExternalSettings.vue（1387） |
| 15 | composables 数量 | 1（useShortcuts） | **4**（+ useDraft / useRuleActions / useUndo） | +3 | 抽取工作起步 |
| 16 | tokens.css 行数 | 244 | **321** | +77 | 暗色/语义令牌补全 |
| 17 | glass.css 行数 | 953 | **1165** | +212 | 玻璃原子类继续沉淀 |
| 18 | docs/ 文档数 | 106 | **124** | +18 | 增量大，质量需挑 |
| 19 | `except Exception` | 122 | **154** | +32（恶化 26%） | fail-open 蔓延 |
| 20 | urls_stubs.py path 数 | 74 | **74** | **0** | ⚠️ 上次 P0#2 完全未动 |
| 21 | 空壳 app 状态 | 5 个 | search/external_sync/data 不存在 models.py；duplicate_check/scraped_resume 0 model | 同上 | ⚠️ 上次 P2#11 未动 |
| 22 | 工作区未提交改动 | 有 | **0** | ✅ | 上次 P0#1 完成 |

---

## 2. 上次 P0 / P1 / P2 行动清单落地情况

### P0（两周内）

| # | 上次动作 | 状态 | 证据 |
|---|---|---|---|
| 1 | 收口未提交的 campus_control indicator 改动 | ✅ | `git status` 干净，commit `ccd79e8` 已入 |
| 2 | urls_stubs.py 74 条逐一定性 | ❌ 未动 | 文件仍 31KB、74 path，无 T02 推进 |
| 3 | 规模数字改脚本生成 | ❌ 未动 | Makefile / scripts/ 无 stats 脚本，本次仍靠实测 |

### P1（一个月内）

| # | 上次动作 | 状态 | 证据 |
|---|---|---|---|
| 4 | 前端统一 request 封装 | ❌ 未动 | utils/ 仍只有 debounce/request-dedup/sanitizeHtml/role；无单点 axios 实例；30 个 API 文件仍各自 axios.create |
| 5 | campus_control/views.py 拆 service + views ≤500 行准入 | ⚠️ 部分 | 已建 services.py（**261 行**）+ calc.py（370）+ io_xlsx.py + io_indicator.py；但 views.py 从 972 → **1115**（超 200 行） |
| 6 | django-fsm → viewflow.fsm 立项 | ❌ 未动 | 仍 `django-fsm==3.0.1`，requirements.txt 注释「Phase 2 技术债」字样未变 |
| 7 | 巨型组件 Top3 拆分（ProcessDetailModal/CampusControl/CandidateList） | ⚠️ 微退步 | ProcessDetailModal 2290 → **2582**（+292）；CampusControl 1658 → **1841**；外部新增 ExternalSettings 1387；只有 StageRuleConfigModal 1524（仍在超 1k） |

### P2（季度内）

| # | 上次动作 | 状态 |
|---|---|---|
| 8 | `except Exception` 122 处分类治理 | ❌ 恶化（→154，+32） |
| 9 | 硬编码 hex 清零 + 间距/字号 token 二期 | ⚠️ 颜色部分超额完成（-83%），间距字号仍 401/126/165 量级未动 |
| 10 | 移动端 PRD 评审 → 内部企微 H5 先行 | ❌ 未动（仅 docs/mobile/MOBILE_STRATEGY_PRD.md v0.1 待评审） |
| 11 | 空壳 app 清理 + 路由别名收敛（T03/T05 打包） | ❌ 未动 |
| 12 | locales 死代码清理 + composables 抽取 | ⚠️ composables +3；locales/zh-CN.ts 仍存（157 字节） |

**落地率**：P0 完成 **1/3**（仅 #1），P1 完成 **0/4**（3 项部分、1 项未动），P2 完成 **0/6**（2 项部分、4 项未动）。
**结论**：9 天精力 95% 集中在 UI/UX 合规与 campus_control 收口两条线，原本最有希望的 P0 行动清单推进微弱。

---

## 3. 新增重要变化（按影响排序）

### 3.1 数据看板通用导出端点真落地 ✅（上次唯一「残留 404 待办」消除）
- `ed0b23e feat(analytics): 数据看板通用导出 /api/v1/data/export/<resource>/`
- 实现 `apps/analytics/views_export.py`（新建），支持 Candidate/Demand/Position/Offer/Interview/Onboarding，csv/json 格式
- 修复前端 `api/data.ts:51 exportResource` 调 `/api/v1/data/export/{resource}/` 的死链
- 这是上次 P0 唯一「文档承诺但实测 404」的项目，本次明确兑现

### 3.2 R-107 SafeHtml 收敛 v-html ✅（XSS 治理闭环）
- `3595654 feat(ui): 引入 SafeHtml 包装组件收敛 v-html 到唯一 SFC（R-107 P0）`
- 实测：`grep v-html` 命中只剩 `SafeHtml.vue` 自身（2 处）+ AnnouncementDetail.vue 一处语义注释，业务文件 0 处 v-html
- 配套：`utils/sanitizeHtml.ts` 8 个 XSS 向量测试覆盖；vue/no-v-html lint 闸门自动 catch 任何新增
- **意义**：从「默认允许 + eslint-disable」翻转为「默认禁止 + 单点白名单」，XSS 风险面被锁死

### 3.3 UI 审计 PR 闭环（P0-B + P1 合规改造，`5f1f47e`）
- 涉及 hero 标题栏、弹窗布局、section-nav、进入条件 radio 用法、PlaySkipForwardOutline 图标替换
- 验证：5f1f47e 之后 `a011c15 fix(lint/test)`、`0040f20 fix(web): 收尾 5 文件 vue-tsc 错误` 表明审计 PR 引入了 4 处 TS 报错 + sanitizeHtml 误删文本，已修
- **观察**：UI 审计 PR 引入的二次错误表明「大规模 UI 改造 → 类型回归」仍需模板属性顺序等纪律

### 3.4 阶段规则弹窗视觉重构（`eb89580`/`a361ba6`/`76a0306`）
- StageRuleConfigModal 是上次 7 个巨型组件之一，本次视觉整改匹配 Liquid Glass v2 + 适配原型交互
- **但**：行数仍是 1524（上次的 1019），视觉整改未做拆分

### 3.5 interview 评价弹窗接入（`de6afde` + `af10812` + `712b49c`）
- API client + modal 接入 + 退役旧表单；按 stitch design v2 重做卡片式表单
- InterviewEvaluation 加 meta_json 字段，前后端迁出 scores[__meta]
- 是上次「接入层缺口」待办的真实兑现

### 3.6 campus_control 持续推进
- `ab53669` Person.save() 自动补号（不再硬编码 code）
- `3785600/4a08539/c253f1b` 人员数据表格瘦身：8 筛 + 1 搜、状态精简 4 项、移除编辑/删除按钮、搜索框加宽
- `77428af` 人员数据表格移除操作栏
- **但**：views.py 涨到 1115 行（+143 行）——模块复杂度未收敛，service 抽取被 view 反超

### 3.7 rule_engine 模块新增（13 个 Model 类，全仓最大）
- 子目录：`adapters.py / bridge.py / integrations/ / services.py / views.py / migrations/`
- 含 management commands
- 是新模块不是合并带来的——但具体业务范围未在 requirements.md 体现

### 3.8 R-204 微文案收尾
- `38f72d1` 人称「您」→「你」+ 「确定」→ 动词宾语（提交审批/分配简历）
- 「软规范」工作流：UI 审计 PR 把微文案一致性也纳入了

---

## 4. 趋势判断

**A. 前端正进入「Liquid Glass v2 + UI 审计闸门」双轨闭环**
- v-html → SafeHtml 单点；硬编码 hex -83%；tokens.css/glass.css 体量翻倍；R-204 微文案入规
- 下一阶段大概率是「间距/字号 token 二期」（UI_DESIGN_SPEC.md §3、§4 是空白）+ Naive `themeOverrides` 与 var() 不兼容的工程化妥协方案

**B. 后端「测试资产 vs fail-open」剪刀差在扩大**
- pytest 9 天 +214 个（-27.7% 增量），但 `except Exception` 同期 +32（恶化 26%）
- 这是个值得警惕的信号——**测试在补，但 fail-open 在同时蔓延**，等于「你测了 X 路径，但生产 X 路径里 fail-open 的捕获行为可能根本不触发被测代码」

**C. campus_control 出现「Service 已建、Views 仍膨胀」的反模式**
- services.py + calc.py + io_xlsx.py + io_indicator.py 已成完整 service 层（产品上有进展）
- 但 views.py 同步增 143 行，说明 view 层在用 service 的同时**重复堆砌**
- 不立准入线（如 views ≤ 500 行、>300 行强制走 PR 复议），未来 3 个月会涨破 1500

**E. worktree 路径合并已完成（`f09f613 merge: workbuddy/main-5f436540 → main`）**
- `5121985 fix(launch): V2 worktree 已合并到 main, paths 切回主项目`
- worktree 上的 DANGEROUS_MEMORY 条目（vite dev 跑 worktree 不是 main）已不再相关——但要确认脚本是否同步切回主项目

---

## 5. 仍待解决的高优先级债务

1. **stub 端点 74 条仍挂根路由**（无变化）：是上次 P0 唯一一条未动的硬债
2. **django-fsm 停维**（无变化）：业务核心 7 FSMField / 43 transition 押注在上游不再维护的库上
3. **巨型组件 8 个**（略增）：ProcessDetailModal 2582 行居首，新增 ExternalSettings
4. **前端 axios 30 文件复制粘贴**（无变化）：改了 token 流程要改 30 处
5. **空壳 app 5 个**（无变化）：search/external_sync/data 无 models.py；duplicate_check/scraped_resume 0 model
6. **路由别名/重复挂载**（未复核）：上次提到的 urls.py:37-47 双前缀别名堆积 + urls_stubs 注释的重复挂载，本次仍为复核盲点
8. **`except Exception` 154 处**（恶化）：与测试覆盖增长背离
9. **rules_engine 模块无文档**（新增盲点）：13 个 Model 类的业务范围未在 requirements/PROJECT_PLAN 体现

---

## 6. 行动建议（已重新排序）

### P0（立即，2 周内）
| # | 动作 | 对应 |
|---|---|---|
| 1 | urls_stubs.py 74 条逐一定性（落地 / 显式 501 / 删除三选一），至少前端 UI 标注「演示数据」 | 上次 P0#2 失约 |
| 2 | 后端 views.py 准入线（建议 ≤500 行，>300 行 PR 复议），重点治理 campus_control/views.py 1115 行 | 上次 P1#5 部分 |
| 3 | `except Exception` 154 处分类治理（fail-open 清零或显式豁免理由） | 持续恶化项 |
| 4 | rule_engine 模块补 requirements / PROJECT_PLAN 文档说明业务范围 | 新增盲点 |

### P1（一个月内）
| # | 动作 | 对应 |
|---|---|---|
| 5 | 前端统一 request 封装（单实例 axios + 拦截器 + 刷新队列下沉），30 个 API 文件渐进迁移 | 上次 P1#4 失约 |
| 6 | 巨型组件 Top3 拆分（ProcessDetailModal 2582 / CampusControl 1841 / StageRuleConfigModal 1524） | 上次 P1#7 失约 |
| 7 | 间距/字号 token 二期（tokens.css 当前 321 行，颜色系完整、间距系待补） | 上次 P2#9 剩余 |
| 8 | django-fsm → viewflow.fsm 立项（先影子验证 43 transition） | 上次 P1#6 失约 |

### P2（季度内）
| # | 动作 |
|---|---|
| 9 | 空壳 app 清理（search/external_sync/data/duplicate_check/scraped_resume）+ 路由别名收敛打包 |
| 10 | locales/zh-CN.ts 删除（composables 已从 1 增到 4，组合式 API 稳定后再清） |
| 11 | 移动端 PRD 评审 → 内部企微 H5 立项 |
| 12 | 路由别名（urls.py:37-47）一次性收敛 |
| 13 | worktree → main 合并后的脚本同步确认（paths/launchd 是否仍指向 worktree） |

---

## 7. 一句话复评

> **后端测试资产还在扩，但 fail-open 同期恶化——9 天里前端 UI 收敛兑现 83% 硬编码 hex 下降与 v-html 单点化是真正的"治理式"胜利；后端的 P0 行动清单失约最多（urls_stubs / 文档数字脚本化 / view 准入线），需要在下一轮把 "治理模式"从 UI 扩散到后端。**

---

*报告生成：2026-09-04 · 158 commits（单人 loki）· 数据全部实测*
*对比基线：docs/PROJECT_FULL_REVIEW_2026-08-26.md*

---

## 8. 后续治理更新（2026-09-05）

> 本节记录 09-04 复评后紧接的治理动作，更正 §1 #21 / §5 #5 的「空壳 app」误判。

### 8.1 「空壳 app 5 个」状态更正

| app | 09-04 复评定性 | 实测真相 | 处置 |
|---|---|---|---|
| `data` | 无 models.py | 目录已删（端点迁 `analytics/urls_data.py`） | ✅ 已闭环 |
| `scraped_resume` | 0 model | 已有 1 Model（T02.5 落地） | ✅ 已闭环 |
| `search` | 无 models.py | 315 行真搜索（跨 6 实体聚合） | 非空壳（无 model 视图型 app） |
| `external_sync` | 无 models.py | G40 Mock 占位（前端显式 Mock 页） | 非空壳（无 model 视图型 app） |
| `duplicate_check` | 0 model | stub（返空假数据，G45 已迁） | ✅ 已删（假绿清零） |

**结论**：5 个「空壳 app」实际 **0 个是真空壳**——2 个已闭环、2 个是「无 model 视图型 app」非空壳、1 个是残留假绿 stub 已删。`search`/`external_sync` 无 model 是**设计如此**（纯查询视图 / Mock 占位），不该被「空壳 app 清理」误伤。

### 8.2 路由别名收敛（§5 #6 / §6 #12）

删 3 个 FE 已废弃的旧前缀别名（`config/urls.py`），保留 1 个 FE 主调用别名：

| 别名 | 判定 | 依据 |
|---|---|---|
| `recruitment-processes/` | ✅ 删 | FE 仅注释残留（`recruitment-process.ts:7`） |
| `recruitment-process-stage-links/` | ✅ 删 | FE 仅注释残留（同上 `:9`） |
| `entry-condition-rules/` | ✅ 删 | FE 仅注释残留（同上 `:10`） |
| `referral/`（单数） | ❌ 保留 | FE **主调用路径**（`referral.ts` 10+ 处用单数） |