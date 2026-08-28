# ATS-NEW 项目全盘体检报告（2026-08-26）

> **检查方式**：静态盘点 + 实际 grep/find/git 计数（不照抄文档旧数字），覆盖顶层文档、后端 35 app、前端 66 页面、设计体系与 docs/ 106 份文档。
> **基线**：`main @ ccd79e8`，工作区有未提交改动（campus_control indicator 导入导出进行中）。

---

## 0. 总体结论与评分卡

**一句话总结**：这是一个**功能完成度高、工程化成熟、正在从「快速堆功能」向「收敛治理」转折点上的中型全栈项目**——核心招聘闭环已跑通且测试资产雄厚（772 pytest + 124 vitest），但 stub 假数据、文档漂移、巨型文件三类债务开始拖累可信度。

| 维度 | 评级 | 一句话依据 |
|---|---|---|
| 产品完成度 | **A-** | P0/P1/P3 全部 done，核心 7 状态机闭环可用；扣分项：P2 外部集成被授权阻塞、stub 假数据仍在线 |
| 后端架构 | **B+** | 分层清晰、权限 fail-closed、审计合规扎实；扣分项：74 条 stub 挂根路由、django-fsm 停维 |
| 后端质量 | **B** | 772 个测试是硬资产；122 处 `except Exception`、5 个 >800 行文件待治 |
| 前端工程 | **B+** | Vite 分包精细、RBAC 双层守卫、测试金字塔完整；扣分项：axios 无统一封装、7 个千行组件 |
| 设计体系 | **B+** | tokens.css 单源 + glass 原子类已成体系、旧别名清零；残留 466 处硬编码 hex |
| 文档健康度 | **C+** | 数量充足（106 份）但**数字互相打架**，README/technical/requirements 三份三个口径 |

---

## 1. 产品维度

### 1.1 定位与进度

- **北极星指标**明确：Time-to-Qualified-Hire（单位时间有效到岗数）；三大目标：周期降 30%、降低用人经理返工、人才库复用率 ≥25%。
- **六阶段全生命周期规划**（需求→职位→筛选→面试→录用→入职）已成文（`docs/产品全生命周期规划.md`），模块命名与真实系统对齐，可直接当研发地图用。

| 阶段 | 状态 | 备注 |
|---|---|---|
| P0 核心 14 项 | ✅ 14/14 | 7 FSMField 业务状态机闭环 |
| P1 重要模块 | ✅ 12/12 | 脱敏/倒序推荐/背调/智能分配等 |
| P2 外部集成 | 🟡 受阻 | 企微/腾讯会议/Moka/背调/RPA——卡企业 API 授权，非研发问题 |
| P3 数据治理 | ✅ 5/5 | 字典/院校公司库/动态字段/OCR 查重 |
| Phase 2 T01-T07 | 🟡 仅 T01.1 | 权限单轨化、stub 落地、空壳清理均未动 |

### 1.2 活跃前线

- **校招管控 campus_control 是当前绝对主线**：git 最近 15 次提交几乎全是它；模块已迭代到规则 v2.5+（维度→指标→规则→Person，占比+人数双口径、三态校验 BLOCK/WARN/PASS）。
- **工作区存在未提交改动**：`campus_control/views.py`、`campusControl.ts`、`CampusControl.vue` 修改 + 新增 `io_indicator.py` 及其测试（指标导入导出功能开发中）。建议尽快收口 commit，避免基线漂移。
- **移动端双端战略 PRD 待评审**（内部企微 H5 + 外部微信小程序分立），两个前置决策未定：微信主体归属、Person 与外部投递人映射。

### 1.3 产品层风险

1. **假数据在线**：`urls_stubs.py` 74 条 mock 端点仍挂生产路由树根部，「批量推荐/智能分配/RPA 抓取/数据导出」等入口可能返回静态假数据——对演示无害，对真实使用是信任风险。
2. **P2 集成依赖外部授权**：企微/会议/Moka 等若长期拿不到授权，相关页面会停留在半成品状态，需在 UI 上明示「未接入」而不是留死按钮。
3. **角色体系庞大但引导薄弱**：6 角色 × 58 路由 × 字段级 ACL，权限组合爆炸；缺面向新用户的角色视图说明（RUNBOOK 只有开发者视角）。

---

## 2. 技术维度 · 后端（apps/django）

### 2.1 架构与规模（实测）

| 指标 | 数值 | 证据 |
|---|---|---|
| Django 版本 | 6.0.6 + DRF 3.17.1 | requirements.txt（R9 后与 pip freeze 对齐） |
| 业务 app | **35 个**（INSTALLED_APPS 41） | `apps/django/apps/` |
| Model | 约 **97 个类** | grep `class.*(models.Model)` |
| 视图类 | ViewSet 66 + APIView 21 = **87** | 全仓统计 |
| 路由 | config/urls.py 59 条主注册（48 include） | `config/urls.py` |
| 测试 | **82 个 test 文件 / 772 个 def test_** | 实际 grep（排除 .venv） |
| Migrations | 32 目录，最新 2026-08-24 | find 统计 |
| settings | base/dev/prod/test 四文件分层 | `config/settings/` |

### 2.2 亮点（值得保持）

- **权限 fail-closed**：`core/permissions.py:54` 异常时返回 False（deny-by-default），这是全项目最正确的一处默认姿态。
- **合规底座扎实**：字段级 ACL（FieldAclService）+ PII Fernet 加密 + id_card_hash 不可逆查重 + 5 路审计 + GDPR 匿名化，PIPL/GDPR 意识明显领先同类内部系统。
- **ConditionalCsrfMiddleware 自研**解决 JWT + Vite 场景 CSRF，admin 入口 env-token 混淆。
- **依赖治理有先例**：R9 把 `==` 锁版本与 pip freeze 对齐并写入审计注释，防假绿。
- 公共基类复用好：UUIDModel + FullAuditModel + SoftDeleteModel（7 个 app 接入）。

### 2.3 技术债清单（按危害排序）

| # | 债务 | 量级 | 危害 |
|---|---|---|---|
| 1 | **stub 端点未清** | `referral/urls_stubs.py` 31KB、**74 条 path**，以 `path('', include(...))` 活跃挂根 | 假数据污染真实使用；README 宣称的「37 个」已过期失真 |
| 2 | **`except Exception` 泛滥** | **122 处** | 部分 fail-open 返回默认值，静默吞错 |
| 3 | **django-fsm 3.0.1 停维** | 7 个 FSMField / 43 transition 全押注 | 上游不再维护，viewflow.fsm 迁移只有文档没有代码 |
| 4 | **超大文件** | application/services/__init__.py 1084 行、campus_control/views.py 972 行（全仓最大 views 且仍在增长）、campus_control/tests/test_calc.py 1011 行 | 改动热区集中，review 与回归成本高 |
| 5 | **路由别名堆积** | processes/recruitment-processes、entry-condition 两套前缀并存（urls.py:37-47）+ urls_stubs 内还有一条被注释的重复挂载 | 对外契约混乱，T05 迟早要还 |
| 6 | **空壳 app** | search、external_sync、duplicate_check（0 model 或纯占位） | INSTALLED_APPS 虚胖 |
| 7 | **软删未全覆盖** | SoftDeleteModel 覆盖 7 app，campus_control 明确硬删 | 删除语义不一致，审计口径分裂 |

---

## 3. 技术维度 · 前端（web/app）

### 3.1 规模与工程化（实测）

| 指标 | 数值 | 备注 |
|---|---|---|
| 页面组件 | **66 个 .vue**（settings 33 个占一半） | 中大型 SPA |
| 路由 | 58 条，RBAC 双层（meta.roles + routeGuard，SUPER_ADMIN 直通） | 有 requiresAuth 继承 bug 的修复痕迹 |
| API 客户端 | 30 个 .ts | 见下方债务 #1 |
| 公共组件 / composables | 41 个 / 仅 1 个 useShortcuts.ts | 组合式抽取不足 |
| Pinia store | 5 个（user/theme/demand/department/addCandidate） | 健康 |
| 测试 | vitest 30 文件 124 用例 + Playwright 15 spec 20 用例 | 金字塔完整 |
| TS | `"strict": true`，但 `any` 约 **498 处** | strict 名义达标、实际松 |
| 关键依赖 | vue ^3.4 / vite ^5 / naive-ui ^2.44 / unocss ^66.7 / wangeditor ^5.1 | 与文档一致 |

### 3.2 亮点

- **Vite 配置有三处精心处理**：wangEditor(~860KB) 单独切 `vendor-rich-editor` chunk 防拖首屏；naive-ui 锁同 chunk + optimizeDeps 防 TDZ 白屏；prod `base:'/static/'` 对齐 Django whitenoise。
- 路由级 code splitting 带 webpackChunkName 分组；Dashboard 子组件 defineAsyncComponent + Skeleton。
- Plan O 性能专项（gzip -60% + ETag 304 + N+1 检测服务）说明性能有基线意识。

### 3.3 技术债清单

| # | 债务 | 量级 | 危害 |
|---|---|---|---|
| 1 | **axios 无统一封装** | 29/30 个 API 文件各自 `axios.create` + 复制 token 拦截器；刷新队列单点困在 auth.ts | 改鉴权要动 30 个文件；401 行为不一致风险 |
| 2 | **巨型组件** | ProcessDetailModal 2290 行、CampusControl 2099、MouManagement 1470、CandidateList 1141、DemandList 1140、DataDictionary 1028、StageRuleConfigModal 1019 | 可测性差，vitest 覆盖集中在外围 |
| 3 | `any` 498 处 | strict 开着但逃逸普遍 | 类型护栏名存实虚 |
| 4 | 死代码 | `src/locales/zh-CN.ts` 全项目零引用 | i18n 假象 |
| 5 | composables 仅 1 个 | 表格分页/筛选/CRUD 逻辑在各页面重复 | 33 个 settings 页面是重灾区 |

---

## 4. 设计维度

### 4.1 体系现状

- **单源 token 已建成**：`tokens.css`（244 行）以 `--brand:#6366F1` 为唯一手填输入，hover/pressed/dark/soft/tint 全部 color-mix 派生；`glass.css`（953 行）提供 `.glass-panel/-card/-input/-sidebar/-table/-tag` 原子类 + `.btn-*`；配套 `glass-modal.css`。
- **权威规范就位**：`docs/ui/UI_DESIGN_SPEC.md` v2.1（WCAG 2.1 AA 目标、中性灰阶梯 `--g1…--g7` 补齐了 onboarding 曾引用未定义的缺陷）、`SETTINGS_PAGE_STRUCTURE.md` 统一设置页骨架。
- **暗色模式**：`body.dark` 变量集切换方案落地，曾踩中的「`:root` 别名继承携带计算值」陷阱已通过整段迁移修复——实测 `var(--color-` 旧别名引用与定义均为 **0 处**，清得很干净。

### 4.2 收敛进度 vs 残留

UI_RECONCILIATION 总纲诊断的 38 问题（P0×9）中，8 阶段路线图大部分标记落地（5 大列表页替换、三档响应式、侧栏折叠、错误/占位页双列布局等）。**残留债务**：

1. **466 处硬编码 hex 散布在 33 个 .vue**（含 `#fff` 类语义白，实际需要治理的核心约百处量级）——「禁止硬编码」约束对新代码生效，存量未清完。
2. 尺寸类硬编码历史量大（诊断口径：font-size 401 / padding 126 / border-radius 165 处），tokens 只覆盖颜色系，间距/字号 token 化尚未启动。
3. Naive UI `themeOverrides` 必须写 hex 字面量（不解析 var()）——意味着换品牌色时要手动同步两处，与「只改 --brand 一处」的目标存在结构性张力，值得在规范里显式登记为已知例外。
4. 移动端仅「基础响应式」，与移动端战略 PRD 的要求（19/66 页补到 100%）之间缺口巨大。

---

## 5. 交叉观察（跨维度的系统性问题）

1. **文档-实现漂移是当前最大的可信度问题**。同一时刻三份权威文档给出三套数字：README「30 apps / 384 tests」（08-04）、requirements「148 路由」（08-17）、实测「35 apps / 772 tests / 87 视图类」。项目刚刚在设计系统上完成了「单一事实来源」，但文档体系本身还没有——建议所有规模数字改为脚本生成（如 `make stats` 输出 markdown 片段），杜绝手抄过期。
2. **测试资产在为架构债兜底而非驱动收敛**。772 个 pytest 是真资产，但最大的测试文件（1011 行）恰好属于最新的 campus_control——新模块在重复「大 views + 大测试文件」的老路，说明缺少「views ≤ N 行必须拆 service」这类准入规则（calc.py/io_xlsx.py 已证明 service 拆分可行）。
3. **「修好了」的叙事与现状有出入**。README 说 stub「37 个（24 落地 + 3 保留 501 + 10 删）」，实测 74 条仍在且活跃挂载——Phase 2 T02 实际未执行，文档却写成既定事实。这与历史上 R11（CI 门禁 `|| true`）暴露的是同一种心态，值得警惕复发。
4. **单点风险集中在三处**：django-fsm 停维（业务核心押注）、前端 token 刷新单点、campus_control/views.py 持续膨胀。
5. **工作区卫生**：main 分支上有未提交的 indicator 导入导出改动 + 两份未跟踪的 campus_control 分析文档 + docs/mobile/，建议本轮收口后统一 commit/push。

---

## 6. 行动建议

### P0（两周内，低成本高回报）
| # | 动作 | 对应问题 |
|---|---|---|
| 1 | 收口当前未提交的 campus_control io_indicator 改动（验证 + commit + push） | §5.5 |
| 2 | urls_stubs 74 条逐一定性（落地 / 显式 501 / 删除），至少先让「返回静态假数据」的端点在前端 UI 标注「演示数据」 | 后端债#1、产品风险#1 |
| 3 | 规模数字改脚本生成，刷新 README/technical/requirements 三份口径 | §5.1 |

### P1（一个月内）
| # | 动作 | 对应问题 |
|---|---|---|
| 4 | 前端建统一 request 封装（单实例 axios + 拦截器 + 刷新队列下沉），30 个 API 文件渐进迁移 | 前端债#1 |
| 5 | campus_control/views.py 按 calc/io_xlsx 先例拆 service 层，并立「views ≤ 500 行」准入线 | 后端债#4 |
| 6 | django-fsm → viewflow.fsm 迁移立项（先影子验证 43 个 transition） | 后端债#3 |
| 7 | 巨型组件 Top3 拆分（ProcessDetailModal / CampusControl / CandidateList） | 前端债#2 |

### P2（季度内）
| # | 动作 |
|---|---|
| 8 | `except Exception` 122 处分类治理：fail-open 清零或显式注释豁免理由 |
| 9 | 存量硬编码 hex 清零 + 间距/字号 token 化二期 |
| 10 | 移动端 PRD 评审 → 内部企微 H5 先行立项 |
| 11 | 空壳 app 清理（search/external_sync/duplicate_check）+ 路由别名收敛（T03/T05 打包做） |
| 12 | locales 死代码清理；composables 抽取（表格 CRUD 通用逻辑） |

---

*报告生成：2026-08-26 · 数据来源：实际文件 grep/find/git 计数（非文档转抄）*
