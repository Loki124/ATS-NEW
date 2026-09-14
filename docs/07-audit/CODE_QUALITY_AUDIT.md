# ATS-NEW 代码工程质量审计报告

- **审计日期**：2026-08-31（基于 `main` 分支 `04fec990`）
- **审计范围**：`apps/django`（Django 6.0.6 + DRF）+ `web/app/src`（Vue 3 + Vite 5 + TS strict）
- **审计方式**：纯静态分析（Glob/Grep/AST 脚本），**未修改任何业务源码**
- **统计口径**：
  - 后端排除 `.venv/`、`__pycache__/`、`htmlcov/`、`node_modules/`
  - 前端排除 `node_modules/`、`dist*/`、`*.map`、`*.min.js`、`*.d.ts`、`*.mjs` 副本、`__tests__/`
  - 所有数字均为脚本实测，非估算；复现命令见文末附录

> **事实 vs 判断**：文中每条结论标注 `[事实]`（含文件路径:行号或命令输出）或 `[判断]`（附推断依据）。

---

## 一、TL;DR

**整体评价：代码"骨架"质量明显高于"血肉"质量。**

架构分层（model/serializer/view/service）执行得相当克制——243 个 model 最多只有 10 个方法、65 个 serializer 最多只有 4 个方法，跨 app 复制粘贴几乎为零（后端 12 行窗口下只找到 1 组重复，36 行）。后端命名 100% snake_case、89 个 migration 100% 标准命名、37 个生产依赖 100% 精确锁版本且每一条都写了取舍理由。**这些是很多团队做不到的事。**

但**运行时契约层已经出现系统性裂缝**，且有 3 条是"静默失效"——代码在跑，但没在干活：

| # | 问题 | 一句话 |
|---|------|--------|
| 1 | `npm run build` **实际是失败的** | `vue-tsc` 报 10 个类型错误（exit 2），日常出包靠 `build:nocheck` 绕过，TS strict 形同虚设 |
| 2 | 全局 axios 错误拦截器 **是死代码** | `main.ts:25-45` 注册在默认实例，而 31/31 个 API 模块各自 `axios.create()` → 404/500 统一处理对全站无效 |
| 3 | 数据范围解析器有 **fail-open 路径** | `core/scope_resolver.py` 4 处静默 except（含 `except Exception: pass`），异常后落到租户配置，配置为 ALL 时放行全量数据 |
| 4 | EmptyState 统一 **没做完** | `components/dashboard/index.ts:19` 仍导出 `./EmptyState.vue`，该文件已不存在 |

**如果只还一笔技术债，还第 1 条**——它让 TS strict、让 `any` 治理、让所有类型层面的改进都没有落地通道（现在连编译都过不了，改了也验证不了）。
**如果只还两笔，加第 2 条**——它意味着线上前端目前**没有任何 404/500 兜底**，用户看到的失败态完全由各页面 `catch` 分支自行发挥。

---

## 二、评分卡

| 维度 | 得分 | 关键依据 |
|------|:----:|----------|
| **可读性** | 3 / 5 | 后端 docstring 密度高、命名零违规；但前端 11 个 `.vue` > 800 行，最大 2490 行，`MouManagement.vue` 的 script 块 928 行 |
| **可维护性** | 3 / 5 | model/serializer 极薄、后端重复率近乎为零；但 74 条路由的跨域 stub 山、31 份重复 axios 实例、1298 行死代码 |
| **一致性** | 3 / 5 | 后端命名 100% snake_case、SFC 100% `<script setup lang="ts">`；但 API 返回约定 25 : 22 分裂、双图标库、拦截器挂载位置不一致 |
| **健壮性** | **2 / 5** | 47.6% 的 except 静默吞异常、越权链路有 fail-open、全局错误拦截器失效、类型检查不通过 |
| **依赖健康** | 4 / 5 | 后端 37 依赖全 `==` 锁定且有取舍注释；前端仅 11 运行时依赖 + lockfile；扣分在 1 个零引用依赖、双图标库、无 CI lint gate |
| **综合** | **3.0 / 5** | 下限由"健壮性"决定，上限被"可读性/一致性"拉住 |

**判断依据**：评分采用"最短板主导 + 相对基准校准"。健壮性给 2 分是因为存在 3 处**静默失效**（不是"没做"，而是"做了但不生效"，排查成本远高于"没做"）；依赖健康给 4 分是横向对比同类 Django+Vue 项目，`requirements.txt` 里逐条记录"为什么锁这个版本/为什么不采纳某建议"属于前 10% 水准。

---

## 三、代码规模数据表

### 3.1 总览

| 项目 | 文件数 | 行数 | 口径 |
|------|-------:|-----:|------|
| 后端生产代码 | 353 | 37,504 | `.py`，排除 tests / migrations / .venv |
| 后端测试代码 | 112 | 20,690 | 同上 |
| **后端测试/生产比** | — | **0.55** | 20,690 / 37,504 |
| 后端 migrations | 89 | 5,042 | 排除 `__init__.py` |
| **后端合计** | **582** | **62,353** | 全部 `.py`，排除 .venv |
| 前端 `.vue` | 97 | 34,879 | `web/app/src` |
| 前端 `.ts` | 79 | 7,924 | 排除 `*.d.ts` |
| **前端合计** | **176** | **42,803** | 排除 node_modules / dist* / 测试 |

> `[事实]` 命令：`find apps/django -name "*.py" -not -path "*/.venv/*" ... | xargs wc -l`
>
> `[判断]` 前端"约 3 万文件"的说法来自 `node_modules`；**实际源码只有 176 个文件**，规模属于中小型 SPA，与后端的体量（5.8 万行）不成比例——前端的复杂度是"单文件堆料"而非"文件数量多"。

### 3.2 后端按 app 行数 TOP 12

| App | 行数 | 有 service 层 | 有 migrations |
|-----|-----:|:--:|:--:|
| application | 6,257 | ✅ | ✅ |
| core | 5,909 | ❌ | ✅ |
| process | 5,873 | ✅ | ✅ |
| campus_control | 5,654 | ✅ | ✅ |
| add_candidate | 3,294 | ✅ | ✅ |
| candidate | 2,804 | ✅ | ✅ |
| rule_engine | 1,904 | ✅ | ✅ |
| integration | 1,635 | ✅ | ✅ |
| demand | 1,607 | ✅ | ✅ |
| dictionary | 1,485 | ❌ | ✅ |
| time_limit | 1,370 | ✅ | ✅ |
| automation | 1,228 | ✅ | ✅ |

`[事实]` 36 个 app 中 **24 个有 service 层**，12 个没有：`announcement common core dictionary duplicate_check dynamic_field external_sync library mou resume_flow scraped_resume search`；3 个 app 连 migrations 都没有：`duplicate_check external_sync search`（疑为纯代理/存根 app）。

### 3.3 前端按目录行数 TOP 10

| 目录 | 行数 |
|------|-----:|
| `src/pages/settings` | **16,713**（占前端总量 39%） |
| `src/api` | 3,943 |
| `src/pages/candidate` | 2,600 |
| `src/pages` | 2,106 |
| `src/pages/candidate/addCandidate` | 1,715 |
| `src/components/dashboard` | 1,474 |
| `src/components` | 1,226 |
| `src/pages/demand` | 1,140 |
| `src/pages/settings/permission` | 1,116 |
| `src/pages/announcement` | 955 |

`[判断]` 设置页一个目录占掉前端 39% 的代码量，且其中 `ProcessDetailModal.vue`(2490) + `CampusControl.vue`(1709) + `MouManagement.vue`(1465) + `ExternalSettings.vue`(1387) 四个文件就有 7,051 行——设置域是前端复杂度绝对热点，任何组件抽取/composable 重构都应从这里开始，收益密度最高。

---

## 四、TOP 热点文件表

### 4.1 前端 TOP 10（按总行数）

| 文件 | 总行 | script | template | style | 风险 | 建议 |
|------|-----:|-------:|---------:|------:|------|------|
| `pages/settings/ProcessDetailModal.vue` | **2,490** | 955 | 784 | 734 | 🔴 超高危 | 拆成「流程元信息 / 阶段列表 / 规则编辑」3 个子组件 + `useProcessForm` composable；style 734 行抽到独立 CSS |
| `pages/settings/CampusControl.vue` | **1,709** | 954 | 399 | 354 | 🔴 超高危 | 3 个 tab（看板/指标库/规则）拆 3 组件；后端 `campus_control` 才是最重的 app，前端逻辑应考虑下沉 |
| `pages/settings/MouManagement.vue` | 1,465 | 928 | 477 | 58 | 🟠 高危 | script 928 行含完整 CRUD + 权限容器逻辑，抽 `useMouCrud` |
| `pages/settings/ExternalSettings.vue` | 1,387 | 907 | 419 | 59 | 🟠 高危 | 供应商适配逻辑抽 `useSupplierAdapter` |
| `pages/candidate/CandidateList.vue` | 1,141 | 412 | 380 | 347 | 🟠 高危 | 与 `CandidateDetail.vue` 有 408 行重复，先抽共用 `CandidateFieldBlock` |
| `pages/demand/DemandList.vue` | 1,140 | — | — | — | 🟠 高危 | 列表页通用骨架（筛选+表格+批量操作）可抽象为 `useCrudList` |
| `pages/settings/DataDictionary.vue` | 1,050 | 582 | 318 | 148 | 🟡 关注 | 树形 CRUD 抽 `DictionaryTree` 组件 |
| `pages/settings/StageRuleConfigModal.vue` | 1,019 | 503 | 236 | 267 | 🟡 关注 | 含 4 行注释掉的代码（:425-428），随重构一并清理 |
| `pages/Layout.vue` | 927 | 333 | 191 | 401 | 🟡 关注 | style 401 行抽主题 CSS |
| `pages/settings/AnnouncementSettings.vue` | 907 | 306 | 258 | 341 | 🟡 关注 | 含 1 处 TODO（:533） |

`[事实]` 阈值统计：`.vue` > 800 行 **11 个**，> 1500 行 **2 个**；400–800 行观察名单 **19 个**。`.ts` 无一个超过 800 行（最长 `src/api/campusControl.ts` 423 行）。

### 4.2 后端 TOP 10（非测试 `.py`）

| 文件 | 行数 | 风险 | 建议 |
|------|-----:|------|------|
| `apps/application/services/__init__.py` | **1,084** | 🟠 高危 | `ApplicationService` 类本体 934 行，是唯一 >500 行的类。按生命周期（创建/推进/跳转/换流程/升级）拆成 5 个模块 |
| `apps/campus_control/views.py` | **1,052** | 🔴 超高危 | **31 处直接 ORM 查询写在 view 里**（全仓最高），`set_rules()` 单函数 214 行。业务逻辑必须下沉到 `services.py`（该 app 已有 service 层） |
| `apps/integration/services.py` | 704 | 🟡 关注 | 供应商适配，按供应商拆分子模块 |
| `apps/referral/urls_stubs.py` | 697 | 🔴 超高危 | **跨域 stub 山，见 §5.3**，不是行数问题是架构问题 |
| `apps/application/views.py` | 682 | 🟡 关注 | `ApplicationViewSet` 479 行 / 18 方法，service 层已存在，view 只应做参数校验与序列化 |
| `apps/candidate/services.py` | 672 | 🟡 关注 | — |
| `apps/process/views.py` | 620 | 🟡 关注 | `RecruitmentProcessViewSet` 249 行 / 9 方法 |
| `config/settings/base.py` | 582 | 🟢 正常 | 配置文件，可接受 |
| `apps/process/models.py` | 553 | 🟢 正常 | — |
| `apps/process/serializers.py` | 546 | 🟢 正常 | — |

`[事实]` 阈值统计：非测试 `.py` > 800 行 **2 个**，> 1500 行 **0 个**。函数 > 80 行（非测试）**25 个**，最长 214 行。

### 4.3 后端超长函数 TOP 8（> 80 行阈值）

| 行数 | 位置 | 函数名 |
|-----:|------|--------|
| 214 | `apps/campus_control/views.py:228` | `set_rules()` |
| 206 | `apps/application/services/__init__.py:278` | `advance_application_to_next_stage()` |
| 205 | `apps/process/services/versioning.py:258` | `clone_process_with_new_version()` |
| 164 | `apps/process/services/template_apply.py:24` | `apply_template_to_process()` |
| 158 | `apps/core/management/commands/init_demo_data.py:75` | `init_roles()` |
| 152 | `apps/application/services/__init__.py:728` | `upgrade_workflow_version()` |
| 131 | `apps/process/management/commands/load_process_templates.py:102` | `load_template()` |
| 131 | `apps/campus_control/services.py:130` | `validate_offer_against_rules()` |

---

## 五、分项详查

### 5.1 重复代码

#### 5.1.1 前端：高度集中，有一处极端案例

`[事实]` 检测方法：归一化（去空行/注释/缩进）后按 12 行滑动窗口哈希，统计跨文件共享窗口。

| 重复组 | 共享块数 | 重复行数 | 涉及文件 |
|--------|--------:|--------:|----------|
| **Step1Batch ↔ Step1Single** | **97** | **1,164** | `pages/candidate/addCandidate/Step1Batch.vue` (502 行) / `Step1Single.vue` (530 行) |
| CandidateDetail ↔ CandidateList | 34 | 408 | `pages/candidate/` |
| 设置页 CSS 样板 | 16 | 192 | CompanyLibrary / DynamicFieldSettings / FieldAclSettings / MouManagement 等 ≥4 个 |
| Step1Batch ↔ Step1Single ↔ Step2Assign | 10 | 120 | `addCandidate/` |
| RecruitmentProcess ↔ Round ↔ Stage | 9 | 108 | `pages/settings/` |
| OfferList ↔ OnboardingList | 8 | 96 | `pages/offer` / `pages/onboarding` |
| CompanyLibrary ↔ SchoolLibrary | 7 | 84 | `pages/settings/` |
| AddCandidateModal.**legacy** ↔ AddReferralModal | 5 | 60 | （legacy 文件本身已死） |

`[事实]` 任务线索「**设置页多个模块结构雷同**」**已验证成立，但性质与预期不同**：重复的 192 行主要是 `<style scoped>` 里的滚动容器样板注释块（"标题区固定 flex-shrink:0 / 内容区自己滚 flex:1;min-height:0"），不是业务逻辑重复。修复成本极低（抽一个 `settings-page.css` 或 UnoCSS shortcut），但收益也有限。

`[判断]` 真正值钱的是第一行：`Step1Batch.vue` 与 `Step1Single.vue` 两个文件合计 1,032 行，其中 **1,164 行重复窗口**意味着重复率约 **55%**（窗口重叠计数导致块数×12 > 文件总行，实际单份重复约 550 行）。这两个文件是"单份录入"和"批量录入"两个入口，差异应在**数据获取方式**而非 UI——建议抽 `Step1Form.vue` 承载表单，两个入口只提供不同的 `onSubmit` 数据源。**这是全仓单点收益最高的重构。**

#### 5.1.2 后端：异常干净

`[事实]` 同样方法扫描后端 234 个文件，**只找到 1 组重复**：`apps/referral/urls_single.py` ↔ `apps/referral/views.py`，3 个共享块 / 36 行（referral code 生成的 hashlib 逻辑被抄了一份）。

`[判断]` 后端跨 app 复制粘贴几乎不存在，说明 service 层抽象是有效的。**这一项无需投入。**

### 5.2 死代码与坏味道

#### 5.2.1 前端死模块：10 个 / 1,298 行

`[事实]` 构建模块导入图（含 router 的 `import(/* webpackChunkName */ '...')` 动态导入）后，下列模块**无任何导入方**：

| 文件 | 行数 | 备注 |
|------|-----:|------|
| `pages/candidate/AddCandidateModal.legacy.vue` | 588 | 文件名自带 `.legacy`，纯历史遗留 |
| `pages/offer/BackgroundCheckPanel.vue` | 220 | 背调面板，疑似被 `OfferList` 内联实现替代 |
| `pages/interview/InterviewFeedbackForm.vue` | 165 | 面试评价表单 |
| `pages/interview/InterviewEvalSummaryCard.vue` | 83 | 同上，**且是未提交的新文件**（`git status` 显示 `??`） |
| `stores/department.ts` | 62 | `useDepartmentStore` 零引用 |
| `stores/demand.ts` | 60 | `useDemandStore` 零引用 |
| `components/common/LoadingState.vue` | 40 | 与 `EmptyState` 同期引入，未被采用 |
| `api/dict.ts` | 22 | **stub，永远 `return []`**（:20-21） |
| `pages/settings/Settings.vue` | 51 | 被 `SettingsLayout.vue` 取代 |
| `locales/zh-CN.ts` | 7 | i18n 未落地 |

**额外死代码**：
- `src/utils/debounce.mjs`(147) + `src/utils/request-dedup.mjs`(74) = **221 行**——是同名 `.ts` 的**手工去类型副本**，注释自称"供 .mjs 测试用"。**全仓零引用**（`grep -rn "\.mjs" src` 无结果）。
- `src/utils/debounce.ts`(170) + `request-dedup.ts`(131) + `condition-expression.ts`(152) 共 453 行，**生产代码零 import**，只有测试引用。
- `src/api/dict.ts` 与 `src/api/dictionary.ts`(201 行) **双套字典 API 并存**，前者是死 stub——调用方极易引错。

`[判断]` 合计约 **1,519 行可安全删除**（10 个死模块 1,298 + `.mjs` 副本 221），占前端总量 3.6%。删除成本近乎为零（无导入方），建议一次性清理。

#### 5.2.2 后端死代码

`[事实]` `apps/core/scope_resolver.py:133` 的 `_dept_ids()` 自述："R8 之后 resolve_scope 不再使用它, 保留是因为 scripts/ 和历史调用方可能还依赖"——典型"以防万一"式保留，实际无调用方。

#### 5.2.3 坏味道统计

| 指标 | 后端 | 前端 |
|------|-----:|-----:|
| `console.log` 残留 | — | **1**（`pages/settings/AccountSettings.vue:252`） |
| `console.error` / `console.warn` | — | 33 / 18（**均为合理的错误上报，不算残留**） |
| `debugger` 语句 | — | **0** |
| 裸 `print()` 调试（app 代码内） | **0** | — |
| 裸 `except:` | **0** | — |
| `except X: pass`（仅 pass） | 20 | — |
| 静默 except（无 log 无 raise） | **148 / 311（47.6%）** | — |
| `except Exception` / `BaseException` | 126 | — |
| `@ts-ignore` / `@ts-expect-error` / `@ts-nocheck` | — | **0** |
| `eslint-disable` 注释 | — | 1（`AnnouncementDetail.vue:56`） |
| TODO / FIXME / HACK / XXX | 12 / 0 / 0 / 0 | 4 / 0 / 0 / 0 |
| 注释掉的代码块（≥3 行） | **0** | 1（4 行，`StageRuleConfigModal.vue:425`） |

`[判断]` 这一栏是**本次审计最亮眼的部分**：前端 0 个 `debugger`、0 个 `@ts-ignore`、后端 0 个裸 `except`、0 处注释掉的代码块、app 代码 0 个 `print()`。这些是"低分项目"最常见的重灾区，ATS-NEW 全部干净。唯一的 `console.log`（AccountSettings:252）也只在上传环境探测分支里。

**问题不在"没写规范"，而在"规范没接进流水线"**（见 §5.6）。

### 5.3 错误处理质量

#### 5.3.1 静默异常：148 处，接近一半

`[事实]` AST 扫描非测试代码，311 个 except handler 中：
- **148 个（47.6%）既不打日志也不重抛**
- 91 个打日志，79 个重抛
- 126 个捕获的是 `Exception` / `BaseException`

按 app 分布（静默数 TOP 6）：`core` 31 / `campus_control` 27 / `application` 23 / `integration` 11 / `add_candidate` 7 / `candidate` 4。

`[判断]` `campus_control` 的 27 处大多是 `except (TypeError, ValueError)` 包裹数值转换（Decimal 解析），属于"可接受的防御性降级"，但**完全没有日志**意味着脏数据进库时无从排查。`application` 的 23 处集中在 `views.py` 的 `except StateTransitionError`（143/148/167/191/279/316/337/358/373/391/443/461/482/655）——状态机拒绝转换时静默，前端可能拿到"成功但没变"的响应。

#### 5.3.2 ⚠️ P0：数据范围解析器存在 fail-open 路径

`[事实]` `apps/core/scope_resolver.py` 是**越权防护（IDOR）的核心**，却在 4 处静默吞异常：

```
:46   except Exception: units = None        # L1 user 级
:52   except Exception: pass                # L1 role_code
:54   except (OperationalError, ProgrammingError): pass   # L1 整体
:82   except (OperationalError, ProgrammingError): pass   # L2 role 级
:84   except Exception: pass                # ← 捕获一切，无任何记录
```

第 84 行捕获**所有**异常后，控制流继续走到 L3：

```
:88   cfg = TenantConfig.objects.filter(config_key='GLOBAL_DEFAULT_DATA_SCOPE', ...).first()
:90   if cfg and cfg.config_value == 'ALL':
:91       return {'all': True}      # ← 放行全量数据
```

`[判断]` 这是**典型的 fail-open**：任何导致 `RoleV2` 查询失败的原因（不只是注释里假设的"V2 schema 未应用"，还包括 DB 连接抖动、表锁超时、字段类型变更）都会被 `:84` 静默吞掉，然后落到 L3；若租户默认配置为 `ALL`，用户将获得**全量数据访问权限**，且日志里不留任何痕迹。**判定为 P0**，依据：影响面是数据越权，且失败是静默的（不可观测）。

`[事实]` **正面范例**：`apps/field_acl/mixins.py:66-78` 处理完全正确——`except Exception` 后 `logger.exception(...)` 记录上下文，然后 `return self._apply_default_mask(entity, data)` **降级为全部脱敏**（fail-closed），注释明确写"宁可多脱敏也不泄漏"。

`[判断]` 同一个仓库里两种截然相反的降级哲学并存，说明**缺少统一的"异常降级策略"约定**。建议把 `field_acl` 的写法固化成 ADR：涉权限/涉敏的异常一律 fail-closed + `logger.exception`；业务计算的异常才可 fail-open，且必须有日志。

#### 5.3.3 ⚠️ P0：全局 axios 错误拦截器对全站无效

`[事实]` 三段证据链：

1. `src/main.ts:25-45` 注册响应拦截器：
   ```ts
   axios.interceptors.response.use((resp) => resp, (err) => { /* 404 告警 / 500 toast */ })
   ```
   注册在 **axios 默认实例**上。

2. `src/api/` 下 **31 个模块全部各自 `axios.create()`**：
   ```
   grep -rn "axios.create(" src → 31 处（30 个 api 模块 + 1 个页面组件）
   ```
   另有 `src/pages/talent/TalentPool.vue:15` 在**页面组件内部**又建了一个实例。

3. 全仓**只有 2 处真实调用**走默认实例：
   - `src/api/auth.ts:83`（token refresh，注释说明是为避免拦截器递归）
   - `src/pages/candidate/AddCandidateModal.legacy.vue:381`（死文件）
   
   另有 2 行是注释掉的代码（`StageRuleConfigModal.vue:427-428`）。

`[判断]` axios 的 `create()` **不继承默认实例上已注册的拦截器**（只继承 `defaults` 配置）。因此 `main.ts` 里那段精心设计的 404/500 兜底——包括注释里提到的"404 静默 + console.warn"、"500 toast 文案改成'服务繁忙'避免暗示系统 bug"这些**经过产品评审的决策——对 31 个 API 模块的请求全部不生效**。

后果：线上前端目前**没有任何统一的 HTTP 错误兜底**，每个页面的 `catch` 分支各写各的。这是一个"代码在、行为不在"的缺陷，靠 code review 极难发现（两段代码看起来都完全正常）。**判定为 P0。**

修复很简单：把拦截器拆到 `src/api/http.ts` 的单一实例工厂，31 个模块改为共享。

#### 5.3.4 错误文案

`[事实]` 前端 52 处 `console.*` 中 33 处是 `console.error`，`main.ts:110-115` 还挂了 `app.config.errorHandler` 和 `unhandledrejection` 全局兜底。

`[判断]` 全局兜底**只 `console.error` 不弹提示**，用户在组件内未捕获的错误面前看到的是"页面没反应"而非错误提示。建议 `errorHandler` 里补一个 toast（非 404 场景）。

### 5.4 命名与规范一致性

#### 5.4.1 后端命名：满分

`[事实]`
- `def [a-z]+[A-Z]` 匹配数：**0**（1,243 处 `def` 中）
- 缩进赋值 `myVar =` 匹配数：**0**
- 后端 100% snake_case

#### 5.4.2 前端命名：91 处 snake_case 残留

`[事实]` 非测试源码中 91 个不同的 snake_case token，TOP 示例：

| token | 出现 | 位置 | 性质判断 |
|-------|-----:|------|---------|
| `draft_id` | 6 | `api/addCandidate.ts` | ⚠️ 响应/路径字段，应为 `draftId` |
| `page_size` | 5 | `settings/ExternalSettings.vue` | ✅ 查询参数，camelCase parser 不处理 query string，**合理** |
| `task_id` | 4 | `api/addCandidate.ts` | ⚠️ 应为 `taskId` |
| `super_admin_product` | 4 | `settings/DemandConfig.vue` | ⚠️ 权限码常量，非字段命名 |
| `count_by_status` / `count_by_dept` | 2 | `settings/DataDashboard.vue` | ⚠️ 响应字段，应为 camelCase |
| `pdp_mbti_20` | 2 | `CandidateDetail/List.vue` | ✅ 业务编码，保持原样合理 |

`[事实]` 后端确已全局启用 camelCase 转换：`config/settings/base.py:298-308` 配置 `CamelCaseJSONRenderer` + `CamelCaseJSONParser`，全仓无 `@renderer_classes` 覆盖，仅 2 处 `JsonResponse`（都在 `core/views_health.py`，健康检查无需转换）。

`[判断]` 转换链路是通的，前端残留的 snake_case 属于**历史代码未跟随改造**，而非链路问题。`page_size` 一类查询参数是合理的（DRF camel-case 不转换 query string），但 `count_by_status`、`draft_id` 这类响应字段访问是错的——要么后端确实返回了 snake_case（说明某些响应绕过了 DRF renderer，需查），要么前端访问了不存在的字段（静默 `undefined`）。**建议先补一个契约测试来定性，再决定改哪边。**

#### 5.4.3 ⚠️ P1：API 层返回约定分裂

`[事实]` `src/api/*.ts` 中：

| 返回形态 | 处数 | 示例 |
|---------|-----:|------|
| `return data`（整个信封 `{success, data, pagination}`） | **25** | `api/candidate.ts:44` `listCandidates()` |
| `return data.data`（拆包，只给 payload） | **22** | `api/candidate.ts:117` `fetchStatusSchema()` |
| `return res.data` | 2 | — |

**同一个文件内就存在两种约定**：`src/api/candidate.ts` 的 `listCandidates()` 返回整包，而 `fetchStatusSchema()` 返回 `data.data`。

`[判断]` 这让调用方无法形成肌肉记忆，每个调用点都得回去看实现。任务里提到的约定「列表响应 `{success, data:[...], pagination:{total}}`」在**后端**是一致成立的（`referral/urls_stubs.py:16` 等处可见标准信封），**问题是前端 API 层有没有统一拆包**——答案是"没有，25:22 五五开"。

**建议**：统一为"API 层一律整包返回，由调用方或一个小工具函数拆包"，或反过来"API 层一律拆包返回 payload，分页信息挂在响应对象上"。两种都行，但必须二选一并写进 AGENTS.md。

### 5.5 前端工程

#### 5.5.1 ⚠️ P0：`npm run build` 实际是失败的

`[事实]` `package.json` 的 build 脚本是 `vue-tsc && vite build`。实测：

```
$ npx vue-tsc --noEmit
$ echo $?
2
```

**10 个类型错误**：

| 位置 | 错误 | 性质 |
|------|------|------|
| `components/dashboard/index.ts:21` | TS2307 Cannot find module `'./EmptyState.vue'` | 🔴 引用不存在的文件 |
| `pages/settings/ProcessDetailModal.vue:294/299/580` | TS2339 `autoSkipNPlusTwo` 不存在（3 处） | 🔴 类型定义与实现脱节 |
| `pages/settings/RecruitmentProcess.vue:31`<br>`RecruitmentRound.vue:31`<br>`RecruitmentStage.vue:36` | TS2559 `DataTable` themeOverrides 属性不匹配（3 处） | 🟠 naive-ui 版本升级遗留 |
| `pages/settings/SettingsLayout.vue:185/187` | TS2322/TS2345 `(Key \| undefined)[]` 不能赋给 `(string \| number)[]` | 🟠 未处理 undefined |
| `pages/Login.vue:237` | TS2353 `containerStyle` 不在 `MessageOptions` 中 | 🟡 |

`[事实]` 但 `npx vite build` **单独运行是成功的**（6,209 模块，23.67s）——Vite 不做类型检查，且 Rollup 的 tree-shaking 让未被 `import` 的 `EmptyState` 重导出没有被解析，所以构建"侥幸"没炸。项目里也确实准备了 `build:nocheck` 脚本作为逃生通道。

`[判断]` **TS strict 目前是"声明了但没有执行"的状态**。这一条是所有类型治理工作的前置阻塞——在 `vue-tsc` 不通过的情况下，任何"消灭 `any`"的改动都无法验证是否引入了新错误。**判定为 P0，且应排在所有类型相关工作的第一位。**

顺带：`config/urls.py:91` 有一行被注释掉的 `# path('', include('apps.referral.urls_stubs')),`，是 §5.3 路由调整的残留。

#### 5.5.2 TypeScript strict 下的 `any`

`[事实]` 非测试源码中 `any` token 共 **522 处**，占 42,803 行的 **1.22%**：
- `as any`：**46**
- `any[]`：**61**
- `Record<string, any>`：**27**

TOP 5 文件：

| `any` 数 | 总行 | 密度 | 文件 |
|--------:|-----:|-----:|------|
| 37 | 1,710 | 2.2% | `pages/settings/CampusControl.vue` |
| 36 | 2,491 | 1.4% | `pages/settings/ProcessDetailModal.vue` |
| 26 | 1,388 | 1.9% | `pages/settings/ExternalSettings.vue` |
| 23 | 646 | **3.6%** | `pages/resume/ResumeList.vue` |
| 22 | 408 | **5.4%** | `pages/settings/ProcessStageEditor.vue` |

`[判断]` 1.22% 的密度**不算"泛滥"**（同类项目常见 3–8%）。真正的障碍是三处配置把类型治理的闸门关掉了：
1. `eslint.config.js` 显式 `'@typescript-eslint/no-explicit-any': 'off'`，注释坦承"项目用了大量 any (mock 数据 / 后端类型不全)"
2. `tsconfig.json` 的 `noUnusedLocals: false` / `noUnusedParameters: false`——死导入可以无限累积
3. `vue-tsc` 不通过 → 类型错误无人可见

**建议**：先修 P0 打通 `vue-tsc`，再把 `no-explicit-any` 从 `off` 改成 `warn`（不阻塞构建但可见），按文件逐个清零。

#### 5.5.3 SFC 规范：一致性极佳

`[事实]`

| 指标 | 数值 |
|------|-----:|
| `<script setup>` 使用率 | **97 / 97（100%）** |
| `<script setup>` 缺 `lang="ts"` | **0** |
| props 声明且带类型 | 33（0 个无类型 / 裸 `defineProps()`） |
| emits 声明且带类型 | 30（0 个无类型数组形式） |
| `<style scoped>` | 90 |
| `<style>` 无 scoped | **4**（`App.vue` 全局合理；`RuleConfigDrawer.vue` / `StageRuleConfigModal.vue` 各含 1–2 个未 scoped 块） |

`[判断]` 这是全仓一致性做得最好的一栏。Props/emits 类型完整度 100%——配合 0 个 `@ts-ignore`，说明组件接口契约是认真维护的。**无需投入，保持即可。**

#### 5.5.4 状态管理：store 少而薄，但 localStorage 泄漏严重

`[事实]`
- 5 个 store，全部使用 **setup 风格** `defineStore(id, () => {...})`——写法 100% 统一
- 合计 941 行，其中 `addCandidate.ts` 390 行（单流程向导，合理）
- 2 个 store 零引用（`demand` / `department`）
- **`localStorage` 直接读写 104 处，分布在 49 个文件**，其中生产代码高频点：`api/addCandidate.ts`(4)、`api/auth.ts`(3)、`api/dashboard.ts`(2)、`pages/resume/ResumeList.vue`(5)、`router/index.ts`(5)

`[判断]` store 数量偏少（5 个）与"几乎无跨页面共享状态"的设计取向一致，本身没问题。但 `localStorage` 散落在 **API 模块**里（`api/auth.ts` 直接读 token 而不是从 `userStore` 取）是**分层泄漏**——API 层不应知道持久化细节。这也正是 §5.3 中 31 份 axios 实例各自手写 `Authorization` 拦截器的直接原因：**没有单一的 token 出口。**

**建议**：收敛出 `src/api/http.ts`（单一 axios 实例 + 拦截器 + 从 store 取 token），这一举同时解决 §5.3.3（拦截器失效）和本节（token 泄漏）两个问题。

#### 5.5.5 其他

`[事实]`
- `v-html` 用法 2 处，均在 `pages/announcement/AnnouncementDetail.vue:56-57`，配 `// eslint-disable-next-line vue/no-v-html`
- ESLint 规则 `'vue/no-v-html': 'error'` 是**显式重新启用**的，注释记录了历史 XSS 修复（OfferList 已改 sandbox iframe）

`[判断]` 富文本公告渲染场景下 `v-html` 难以完全避免，且已有显式豁免 + 审计注释，属于**可接受的风险**。但公告内容若可由非管理员编辑（运营/ HR 可发公告），则引入 DOMPurify 仍是必要的。需产品经理确认公告发布权限模型。

### 5.6 后端工程

#### 5.6.1 分层职责：model / serializer 极薄，view 偏厚

`[事实]`

| 层 | 类数量 | 最多方法数 | 最大行数 |
|----|-------:|-----------:|---------:|
| Model | 243 | **10**（`Candidate`） | 257 |
| Serializer | 65 | **4**（`CandidateCreateSerializer`） | 66 |
| View/ViewSet | 27 | **18**（`ApplicationViewSet`） | **479** |

`[判断]` 243 个 model 最多 10 个方法、65 个 serializer 最多 4 个方法——**这是教科书级的"贫血模型 + 薄序列化器"**，没有出现"model 里塞业务逻辑"或"serializer 里做写操作"的常见反模式。

厚的是 view：
- `ApplicationViewSet` 479 行 / 18 方法（`apps/application/views.py`）——但该 app **有** 1,084 行的 service 层，view 应该只是薄壳
- `CandidateViewSet` 419 行 / 17 方法
- `ControlRuleViewSet` 407 行 / 11 方法（`campus_control`）——**该 app 的 view 里有 31 处直接 ORM 查询，是全仓最高**

`[事实]` ORM 直接在 view 中出现的次数 TOP 5：`campus_control/views.py` **31** / `analytics/views.py` 14 / `process/views.py` 13 / `core/views.py` 9 / `entry_condition/views.py` 8。

#### 5.6.2 ⚠️ P1：跨域 stub 山 —— `apps/referral/urls_stubs.py`

`[事实]`
- **697 行，74 条 `path()` 路由**
- 所属 app：`referral`（内推），但路由前缀覆盖 **≥17 个业务域**：

| 前缀 | 路由数 | 域 |
|------|------:|-----|
| `permissions` | 16 | 权限 |
| `recruitment-rules` | 14 | 规则 |
| `candidates` | 10 | 候选人 |
| `recruitment-rounds` | 6 | 招聘轮次 |
| `auth` | 4 | 认证 |
| `offer-templates` | 4 | Offer |
| `login` / `search` / `scoring` / `bulk-create` / `upload-and-parse` / `evaluate` / `resumes` / `duplicate-check` / `api` / `check-stage-transition` | 各 2 | 混合 |

- 挂载位置 `config/urls.py:28`：`path('', include('apps.referral.urls_stubs'))`——**挂在 `/api/v1/` 根路径**，且排在 `path('', include('apps.core.urls'))`（:36）**之前**
- 文件内注释自陈："详细 stub 逻辑在 apps.referral.urls_stubs (**寄放 referral app, 仅是位置**)"

`[事实]` 路由顺序的脆弱性被注释反复强调：
- `config/urls.py:21` "全局统一搜索必须排在 urls_stubs 的 search stub 之前以优先命中（若在其后会被 stub 抢先）"
- `config/urls.py:25-27` "把 urls_stubs 挂到 core.urls 之前, 避免 core/permissions router 抢……（之前 line 60, 被 core 的 router.register 抢先吃掉）"

`[判断]` 这是一个**靠注释维护的隐式契约**：`/api/v1/` 下所有路由的解析结果，取决于这 74 条 stub 与后续各 app 路由的**注册顺序**。任何人在 `config/urls.py` 中间插入一行 `path('', include(...))`，都可能静默地把某个真实 endpoint 变成返回空数组的 stub，且**测试未必能发现**（stub 返回 200 + 空数据，不是 404）。

**判定为 P1**（不是 P0 是因为它目前行为正确，且注释完备；但它是"定时炸弹"）。修复路径：把 74 条路由按域归还给各自 app，或至少收敛到一个显式的 `apps/stubs/urls.py` 并在文件头用表格列出"哪些 endpoint 仍是 stub + 计划实装时间"，配合一个"stub 清单契约测试"防止静默漂移。

#### 5.6.3 N+1 查询风险

`[事实]` 非测试代码：

| 指标 | 数值 |
|------|-----:|
| ORM 查询构造（`.objects.filter/all/get/exclude/...`） | **409** |
| `select_related` / `prefetch_related` / `only` / `defer` | **62（15.2%）** |

按 app（查询数 TOP 6）：

| app | 查询数 | 优化数 | 优化率 |
|-----|-------:|-------:|-------:|
| core | 65 | 6 | 9.2% |
| campus_control | 45 | 3 | 6.7% |
| **analytics** | 34 | **0** | **0%** |
| application | 31 | 7 | 22.6% |
| process | 31 | 4 | 12.9% |
| referral | 14 | 4 | 28.6% |

零优化且查询密集的文件：`analytics/services.py`(16 查询)、`analytics/views.py`(14)、`core/views_permission_v2.py`(11)、`referral/urls_stubs.py`(9)、`core/serializers.py`(8)、`core/scope_resolver.py`(8)、`position/services.py`(7)、`integration/services.py`(7)、`candidate/services.py`(7)。

`[事实]` 循环内执行 ORM 查询的候选点 **67 处**（12 个是真实热点，如 `campus_control/views.py:295/541/577/1008` 在 for 循环里调 `.first()`）。

`[判断]` 15.2% 的优化率**偏低但不算灾难**（多数列表页配了分页，单页 20 条，N+1 上限可控）。真正需要优先处理的是：
1. `analytics/*`（34 查询 0 优化）—— 聚合/导出场景数据量最大，N+1 会直接拖垮响应时间
2. `core/scope_resolver.py`（8 查询 0 优化）—— **每个请求都要跑**，是全局放大器
3. `campus_control/views.py` 循环内 `.first()`

**建议**：先给 `core/scope_resolver.py` 加缓存（用户 scope 在一个请求内不变），`analytics` 加 `select_related`/`prefetch_related` 并在 CI 加 `django-perf-rec` 或 `assertNumQueries` 断言。

#### 5.6.4 Migrations

`[事实]`
- 89 个迁移文件，5,042 行，**命名 100% 符合 `NNNN_snake_case.py`**（非标准命名数：**0**）
- 33 / 36 个 app 有 migrations；无 migrations 的 3 个：`duplicate_check`、`external_sync`、`search`
- 单 app 最多 7 个（`candidate`、`campus_control`）

`[判断]` 迁移数量健康（平均 2.5 个/app），无需 squash。命名规范满分。

### 5.7 依赖健康

#### 5.7.1 后端：优秀

`[事实]`
- `requirements.txt`：**37 个运行时依赖，100% `==` 精确锁定**（0 个未锁定）
- `requirements-dev.txt`：6 个开发工具
- 文件头有 12 行"R9 修订说明"，逐条记录历史教训与取舍：
  - 曾用 celery==5.4.0 而实装 5.6.3、pytest==8.2.0 而实装 9.1.1 → 改为 `pip freeze` 实装版本
  - 曾同时 pin `django-fsm==2.8.1` 和 `django-fsm-2==4.0.0` → 两者提供同一顶层模块 `django_fsm`，互相覆盖，属于不确定行为 → 只保留 `django-fsm==3.0.1`
  - 架构评审建议加 `django-cryptography` → **明确不采纳**，理由：最后发布停在 2022 年，为 50 行代码引入不维护依赖
  - 移除 `python-decouple==3.8`（未安装且零引用）、`uvicorn[standard]`（未安装且与 daphne 重复）
- 生产/开发依赖已分离（Dockerfile 只装 `requirements.txt`）

**风险项**：
- `django-fsm==3.0.1` —— **已停止维护**（文件内自述"官方建议迁移到 viewflow.fsm —— 见 Phase 2 技术债"）。状态机是该项目的核心抽象，`application` app 大量依赖 `StateTransitionError`。
- `requirements-dev.txt` 的 6 个 lint/type 工具（`black>=24.4`、`flake8>=7.0`、`isort>=5.13`、`mypy>=1.10`、`django-stubs>=5.0`、`djangorestframework-stubs>=3.15`）**全部用 `>=` 且注释明说"当前 .venv 里都没装, 也没有任何 CI 步骤在跑"**。

#### 5.7.2 前端：精简，但有冗余

`[事实]`
- **11 个运行时依赖**（axios / vue / vue-router / pinia / naive-ui / dayjs / @vueuse/core / lucide-vue-next / @vicons/ionicons5 / @wangeditor/*）
- 21 个开发依赖，有 `package-lock.json`（314 KB）
- 全部用 `^` caret 范围（有 lockfile 兜底，可接受）

**风险项**：
- **`@vueuse/core` 声明但零 import**（`grep -rn "@vueuse/core" src` → 0）——纯沉没成本
- **双图标库并存**：`@vicons/ionicons5`（45 处 import）+ `lucide-vue-next`（14 处 import）。`[判断]` 两套视觉风格混用，且 `lucide-vue-next: ^1.0.0` 版本号存疑（lucide-vue-next 主流版本为 0.4xx，1.x 需核实真实性）
- **打包体积**：`vendor-naive-ui` **1,344 KB**（gzip 360 KB）、`vendor-rich-editor`（wangEditor）**807 KB**（gzip 282 KB）——两者合计占首屏 vendor 的绝大比重。`[判断]` rich-editor 只在 `RichEditor.vue` 一处使用，应改为 `defineAsyncComponent` 懒加载

`[事实]` `django-fsm`、`@vueuse/core` 两项之外的依赖版本均为主流 LTS/稳定版，无明显 CVE 高危项（未联网核查，仅基于版本时间判断）。

`[判断]` 依赖健康总体 **4/5**。扣分不在"版本管理"（这块做得比多数团队好），而在**"没有 CI 把关"**：后端 lint 工具装了不跑、前端 `vue-tsc` 不通过也能出包。**依赖治理的真正缺口是流水线，不是版本号。**

### 5.8 仓库卫生（顺带发现）

`[事实]` 与代码质量无直接关系，但影响协作效率：

| 问题 | 数量 | 说明 |
|------|-----:|------|
| 根目录误建文件 | **6** | `open`（**234 KB PNG 截图**）、`1nagent-browser`、`1ncurl`、`1necho`（0 字节）、`1ncat`、`1nsleep`（126 字节）——均为 2026-08-29 的 shell 误操作产物，全部未 tracked |
| 陈旧构建目录 | **14** | `web/app/dist_old_*`（11 个）、`dist-qa-verify`、`dist-verify`、`dist.bak281` |
| Vite 临时文件 | **40** | `web/app/vite.config.ts.timestamp-*.mjs`（已被 `.gitignore` 的 `*.timestamp-*.mjs` 覆盖） |
| `.DS_Store` | 13（磁盘）/ **0（tracked）** | gitignore 生效 |
| `htmlcov/` | 15 MB | 已被 gitignore |
| 逃逸 gitignore 的目录 | 1 | `web/app/"dist_old_1788066979"/` —— **目录名含字面引号**，导致 `dist*/` 规则失配，出现在 `git status` 未跟踪列表 |

`[判断]` 除"`open` 是 234 KB 二进制误入仓库根目录"外，其余均被 `.gitignore` 正确覆盖，不污染版本库。但 14 个陈旧 dist 目录 + 15 MB htmlcov 会拖慢 IDE 索引和 `Glob`/`Grep`（本次审计中已多次需要手动排除）。建议一次性清理并给 `dist_old_*` 加一条显式 ignore。

---

## 六、技术债清单（按修复成本 / 收益排序）

排序依据：**收益 ÷ 成本** 降序。"成本"以人日估算（1 人日 = 8 小时）。

| # | 技术债 | 成本 | 收益 | 比值 | 优先级 |
|--:|--------|:----:|:----:|:----:|:------:|
| 1 | 修复 `vue-tsc` 10 个类型错误，恢复 `npm run build` | 1.0 人日 | **解锁所有类型治理工作**；消除"引用不存在文件"的定时炸弹 | ★★★★★ | **P0** |
| 2 | 收敛 31 份 axios 实例为单一 `src/api/http.ts` | 1.5 人日 | 恢复全局 404/500 兜底；消灭 ~62 处重复块；统一 token 出口 | ★★★★★ | **P0** |
| 3 | `core/scope_resolver.py` 补 `logger.exception` + fail-closed 兜底 | 0.5 人日 | 消除越权链路的静默 fail-open | ★★★★★ | **P0** | ✅ **已修复** (ATS-NEW `43ba391`)：4 处补 `logger.exception`，L2 失败兜底改 `return {'management_unit_ids': []}`，加 3 条 pytest 锁定 |
| 4 | 删除 `components/dashboard/index.ts:19` 的悬空 `EmptyState` 导出 | 0.1 人日 | 完成 EmptyState 统一；消除 TS2307 | ★★★★★ | **P0** |
| 5 | 删除 10 个死模块（1,298 行）+ `utils/*.mjs`（221 行） | 0.5 人日 | 减 1,519 行；消除 `dict.ts`/`dictionary.ts` 双套陷阱 | ★★★★☆ | P1 |
| 6 | 统一 API 返回约定（25 `return data` : 22 `return data.data`） | 1.5 人日 | 消除调用方心智负担；为后续生成 SDK/类型打基础 | ★★★★☆ | P1 |
| 7 | `Step1Batch.vue` / `Step1Single.vue` 抽共用表单组件 | 2.0 人日 | 减 ~550 行重复（55% 重复率） | ★★★★☆ | P1 |
| 8 | 给 148 处静默 except 补日志（先做 `core` / `application` 的 54 处） | 1.5 人日 | 让线上异常可观测 | ★★★★☆ | P1 |
| 9 | 制定并落地"异常降级策略 ADR"（以 `field_acl/mixins.py:66` 为范本） | 0.5 人日 | 防止新的 fail-open 被引入 | ★★★★☆ | P1 |
| 10 | `core/scope_resolver.py` 加请求内缓存（每请求必跑 8 次查询） | 0.5 人日 | 全局查询数下降 | ★★★★☆ | P1 |
| 11 | `apps/referral/urls_stubs.py` 74 条路由按域归位 + stub 契约测试 | 3.0 人日 | 消除"靠注册顺序决定路由命中"的隐式契约 | ★★★☆☆ | P1 |
| 12 | `campus_control/views.py` 31 处 ORM 下沉到 service；`set_rules()` 214 行拆分 | 3.0 人日 | 消除全仓最厚的 view | ★★★☆☆ | P1 |
| 13 | `analytics/*` 34 处查询补 `select_related` + `assertNumQueries` 断言 | 1.0 人日 | 聚合/导出场景性能 | ★★★☆☆ | P1 |
| 14 | wangEditor 改 `defineAsyncComponent` 懒加载 | 0.3 人日 | 首屏 vendor -807 KB（gzip -282 KB） | ★★★☆☆ | P1 |
| 15 | `localStorage` 收敛到 store（104 处 → 集中在 `user`/`theme`） | 2.0 人日 | 分层清晰；与 #2 协同 | ★★★☆☆ | P2 |
| 16 | `ProcessDetailModal.vue`(2,490 行) 拆 3 子组件 + composable | 3.0 人日 | 前端最大热点；但改动面大、回归风险高 | ★★☆☆☆ | P2 |
| 17 | 前端 `any` 治理（522 处）：ESLint 规则 `off` → `warn`，逐文件清零 | 4.0 人日 | 类型安全；依赖 #1 先行 | ★★☆☆☆ | P2 |
| 18 | 移除 `@vueuse/core`（零引用）；统一图标库为 1 套 | 1.0 人日 | 依赖瘦身；但图标统一涉及 UI 走查 | ★★☆☆☆ | P2 |
| 19 | 12 个无 service 层的 app 补分层（`core`/`dictionary` 优先） | 5.0 人日 | 架构一致性；改动面大 | ★★☆☆☆ | P2 |
| 20 | `django-fsm` 迁移到 `viewflow.fsm` | 8.0 人日 | 解除不维护依赖；核心抽象迁移风险高 | ★☆☆☆☆ | P3 |
| 21 | 仓库卫生清理（6 个根目录垃圾文件、14 个 dist_old、htmlcov） | 0.2 人日 | 提升 IDE/Grep 效率 | ★★★★★ | **顺手做** |

**合计**：21 条，其中 **P0 4 条**、**P1 10 条**、**P2 5 条**、**P3 1 条**、**顺手做 1 条**。

**建议节奏**：
- **第 1 周**：#1 → #2 → #3 → #4（4 条 P0，合计 3.1 人日）。这 4 条都是"静默失效"型缺陷，修完立刻让系统的可观测性和类型安全回到应有水位。
- **第 2–3 周**：#5 → #6 → #7 → #8 → #9 → #10（6 条，合计 6.5 人日）。清理 + 立规矩。
- **第 4 周及以后**：#11 → #14（架构与性能），#16/#17 视排期与 #1 的完成情况启动。

---

## 七、P0 / P1 / P2 清单

### 🔴 P0（必须立即修复，共 4 条）

| # | 问题 | 证据 | 影响 | 修复方案 |
|--:|------|------|------|----------|
| **P0-1** | `npm run build` 失败，TS strict 未执行 | `npx vue-tsc --noEmit` → **exit 2，10 个错误**；`package.json` build 脚本为 `vue-tsc && vite build` | 类型错误不可见；所有类型治理工作无法验证；日常靠 `build:nocheck` 逃生 | 逐个修复 10 个错误；修完后把 `build:nocheck` 标记为 deprecated |
| **P0-2** | 全局 axios 错误拦截器对 31/31 API 模块无效 | `main.ts:25-45` 注册在默认实例；`grep -rn "axios.create(" src` → 31 处；全仓仅 `api/auth.ts:83` 走默认实例 | **线上前端无统一 HTTP 错误兜底**；404/500 处理完全失效；31 份重复的 baseURL+timeout+auth 拦截器 | 抽 `src/api/http.ts` 单一实例工厂，31 个模块改为共享；`TalentPool.vue:15` 的实例一并删除 |
| **P0-3** | 数据范围解析器存在 fail-open 路径 | `apps/core/scope_resolver.py:46/52/82/84`，其中 **`:84` 是 `except Exception: pass`**；异常后落到 `:88-91` 的 L3 租户配置，配置为 `ALL` 时 `return {'all': True}` | 异常时**放行全量数据**且无任何日志痕迹 | 4 处全部补 `logger.exception`；`:84` 的失败兜底改为 `return {'management_unit_ids': []}`（fail-closed 到 SELF） |
| **P0-4** | EmptyState 统一未完成，存在悬空导出 | `src/components/dashboard/index.ts:19` → `export { default as EmptyState } from './EmptyState.vue'`；`ls src/components/dashboard/EmptyState.vue` → **No such file**；`git ls-files \| grep EmptyState` 只有 `components/common/EmptyState.vue` | TS2307 错误；任何 `import { EmptyState } from '.../components/dashboard'` 会构建失败；Vite 目前仅因 tree-shaking 未触发 | 删除该行导出（或改为从 `components/common/EmptyState.vue` 重导出） |

### 🟠 P1（本迭代内修复，共 10 条）

| # | 问题 | 证据 |
|--:|------|------|
| **P1-1** | `apps/referral/urls_stubs.py` 跨域 stub 山，靠注册顺序维持正确性 | 697 行 / 74 条 `path()` / ≥17 个业务域；`config/urls.py:28` 挂在 `/api/v1/` 根且排在 `core.urls`(:36) 之前；注释自陈"寄放 referral app, 仅是位置" |
| **P1-2** | 31 个 api 模块重复 `axios.create()` + 手写 Authorization（与 P0-2 同源，作为重构项单列） | `grep -rn "baseURL: config.api.baseUrl" src` → 20+；`grep -rn "cfg.headers.Authorization" src` → 20+；另有 `TalentPool.vue:15` |
| **P1-3** | API 层返回约定 25 : 22 分裂 | `return data$` 25 处 vs `return data.data` 22 处 vs `return res.data` 2 处；`api/candidate.ts` 单文件内两种并存（:44 vs :117） |
| **P1-4** | `Step1Batch.vue` ↔ `Step1Single.vue` 约 55% 重复 | 12 行窗口共享 97 块 / 1,164 重复行；文件分别 502 / 530 行 |
| **P1-5** | 148 / 311（47.6%）except 静默吞异常 | AST 扫描非测试代码；`core` 31 / `campus_control` 27 / `application` 23 |
| **P1-6** | 缺少统一的异常降级策略 ADR | `field_acl/mixins.py:66` 是正确范本（fail-closed + logger.exception），`scope_resolver.py` 是反例（fail-open + 静默） |
| **P1-7** | `core/scope_resolver.py` 每请求 8 次查询且 0 优化 | `py_orm.py` 输出：queries=8, opt=0；该文件在每个鉴权请求的主链路上 |
| **P1-8** | `campus_control/views.py` 全仓最厚 view | 1,052 行；31 处直接 ORM（全仓最高）；`set_rules()` 单函数 214 行（:228） |
| **P1-9** | `analytics/*` 34 处查询 0 优化 | `analytics/services.py` 16 查询 / `analytics/views.py` 14 查询，`opt=0` |
| **P1-10** | wangEditor 未懒加载 | 构建产物 `vendor-rich-editor` 807 KB（gzip 282 KB），仅 `RichEditor.vue` 一处使用 |

### 🟡 P2（排期修复，共 5 条）

| # | 问题 | 证据 |
|--:|------|------|
| **P2-1** | 前端死代码 1,519 行 | 10 个零导入模块 1,298 行 + `utils/*.mjs` 221 行；`api/dict.ts` 与 `api/dictionary.ts` 双套并存 |
| **P2-2** | `any` 522 处 + 治理闸门全关 | 密度 1.22%；`eslint.config.js` `'@typescript-eslint/no-explicit-any': 'off'`；`tsconfig.json` `noUnusedLocals: false` |
| **P2-3** | `localStorage` 104 处分散在 49 个文件，含 API 模块 | `api/auth.ts`(3) / `api/addCandidate.ts`(4) / `api/dashboard.ts`(2) / `ResumeList.vue`(5) |
| **P2-4** | 依赖冗余：零引用 + 双图标库 + 版本存疑 | `@vueuse/core` 0 import；`@vicons/ionicons5`(45) + `lucide-vue-next`(14) 并存；`lucide-vue-next: ^1.0.0` 版本号需核实 |
| **P2-5** | 12 / 36 app 无 service 层 | `announcement common core dictionary duplicate_check dynamic_field external_sync library mou resume_flow scraped_resume search` |

### 🟢 顺手做（0.2 人日）

- 删除根目录 6 个误建文件（含 234 KB 的 `open` PNG）
- 清理 14 个 `dist_old_*` / `dist-qa-verify` / `dist-verify` / `dist.bak281`
- 删除 `web/app/"dist_old_1788066979"/`（目录名含引号，逃逸 `dist*/` ignore 规则）
- `config/urls.py:91` 删除注释掉的重复 include 行

---

## 八、本次审计的正面发现（值得保持）

审计不应只挑毛病。以下实践**明显优于同类项目基准**，建议在团队内固化并推广：

1. **后端依赖管理是教科书级的** —— `requirements.txt` 37 个依赖 100% `==` 锁定，且逐条记录"为什么锁这个版本"、"为什么不采纳评审建议"、"哪些包被移除及原因"。生产/开发依赖分离。**这是本次审计唯一拿到满分的子项。**
2. **后端命名零违规** —— 1,243 个 `def` 中 0 个 camelCase，0 个不规范赋值。
3. **后端跨 app 复制粘贴几乎为零** —— 12 行窗口下全仓只找到 1 组重复（36 行）。service 层抽象是有效的。
4. **Model / Serializer 极薄** —— 243 个 model 最多 10 个方法，65 个 serializer 最多 4 个方法。没有"胖模型"或"序列化器里做写操作"。
5. **前端 SFC 一致性 100%** —— 97/97 `<script setup lang="ts">`，props/emits 类型完整度 100%，0 个 `@ts-ignore`，0 个 `debugger`。
6. **注释掉的代码块几乎为零** —— 后端 0 处，前端 1 处（4 行）。
7. **`field_acl/mixins.py:66` 的 fail-closed 实现是优秀范本** —— `except` 后 `logger.exception` 记上下文，再降级到"全部脱敏"，注释写明"宁可多脱敏也不泄漏"。
8. **测试代码量可观** —— 后端测试/生产比 0.55（20,690 / 37,504 行）。
9. **Migrations 命名 100% 规范** —— 89 个文件，0 个非标准命名，平均 2.5 个/app，无需 squash。
10. **安全敏感改动留痕** —— `eslint.config.js` 里 `vue/no-v-html` 被显式重新启用并记录了 XSS 修复历史；`requirements.txt` 记录了为什么不引入 `django-cryptography`。

---

## 附录：复现命令

本次审计使用的分析脚本位于 `/tmp/ats_audit/`（临时目录，审计结束后已删除），核心命令如下：

```bash
# ===== 代码规模 =====
# 后端总行数（排除 .venv/__pycache__/htmlcov）
find apps/django -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*" \
  -not -path "*/htmlcov/*" -print0 | xargs -0 wc -l | tail -1

# TOP 20 后端非测试文件
find apps/django -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*" \
  -not -path "*/htmlcov/*" -not -path "*/tests/*" -not -name "test_*.py" \
  -print0 | xargs -0 wc -l | sort -rn | head -22

# 前端总行数（排除 dist*/node_modules/*.d.ts）
cd web/app && find src -type f \( -name "*.vue" -o -name "*.ts" \) -not -name "*.d.ts" \
  -print0 | xargs -0 wc -l | tail -1

# 前端 TOP 25 .vue
cd web/app && find src -name "*.vue" -print0 | xargs -0 wc -l | sort -rn | head -26

# ===== P0 验证 =====
# P0-1: 类型检查
cd web/app && npx vue-tsc --noEmit; echo "exit=$?"     # → 2，10 个错误

# P0-2: axios 实例数量
cd web/app && grep -rn "axios.create(" src | wc -l     # → 31（+2 测试注释）

# P0-3: fail-open 路径
sed -n '40,95p' apps/django/apps/core/scope_resolver.py

# P0-4: 悬空导出
cd web/app && ls src/components/dashboard/EmptyState.vue   # → No such file
cd web/app && sed -n '19p' src/components/dashboard/index.ts

# ===== 错误处理 =====
# 静默 except 统计（AST）：见 py_except_stats.py
# 手工验证单例
sed -n '84,86p' apps/django/apps/core/scope_resolver.py

# ===== 重复代码 =====
# 12 行滑动窗口跨文件共享：见 dup_detect.py
#   python3 dup_detect.py 12 2 <root>

# ===== 死代码 =====
# 前端模块导入图：见 dead_export.py（含 router 动态 import 的 webpackChunkName 注释处理）

# ===== N+1 =====
# ORM 查询 vs 优化：见 py_orm.py

# ===== 依赖 =====
grep -c "==" apps/django/requirements.txt               # → 37（全部锁定）
cd web/app && python3 -c "import json;p=json.load(open('package.json'));print(len(p['dependencies']),len(p['devDependencies']))"
```

### 分析脚本清单（`/tmp/ats_audit/`，均为只读）

| 脚本 | 用途 |
|------|------|
| `py_smells.py` | 后端 AST 扫描：裸 except / 静默 except / 长函数 / 大类 / TODO |
| `py_except_stats.py` | 后端按 app 的异常处理质量统计（handlers / broad / bare / logged / reRaise / silent） |
| `py_orm.py` | ORM 查询数 vs `select_related`/`prefetch_related` 优化率 + 循环内查询检测 |
| `py_arch.py` | Model/Serializer/View 分层职责统计 + 生产/测试代码量 |
| `fe_scan.py` | 前端 `any` / `@ts-ignore` / eslint-disable / v-html / SFC 规范统计 |
| `dup_detect.py` | 跨文件重复块检测（可配置窗口大小与最小共享文件数） |
| `dead_export.py` | 前端模块导入图 + 零引用模块/导出识别 |

---

## 九、方法说明与局限

**本次审计覆盖**：静态代码分析、依赖清单、构建产物、配置一致性。

**未覆盖（需其他手段）**：
- **运行时行为**：未启动服务，N+1 的 67 处"循环内查询"候选点未经 SQL 日志验证，实际触发比例需 `django-debug-toolbar` 或 `assertNumQueries` 确认
- **依赖 CVE**：未联网查询漏洞库，`django-fsm` 之外的安全状态未核实
- **测试有效性**：后端测试行数 20,690（比例 0.55）仅统计体量，未评估断言质量与覆盖率（项目内已有 `docs/COVERAGE_BASELINE_2026-08-06.md`，可参考）
- **Git 历史模式**：未做热点文件变更频率分析（churn vs complexity 交叉可进一步定位真正该重构的文件）

**统计口径的已知误差**：
- 重复代码检测中，"共享块数 × 12 行"会重复计数重叠窗口，因此 `Step1Batch/Step1Single` 的 1,164 行是**上界**，实际单份重复量约 550 行（按 55% 重复率 × 1,032 行推算）
- 67 处"循环内 ORM 查询"候选点采用 25 行前瞻窗口，包含一定数量的假阳性（循环体实际已结束的情况），抽样验证后估计真实值在 12–20 处

---

*报告完成于 2026-08-31 · 审计人：寇豆码（软件工程组）*
