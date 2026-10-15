# 脚手架对比分析：RuoYi-Vue-Pro(yudao) vs ATS-NEW

> 日期：2026-10-11
> 目的：评估 `项目开发/新项目研究` 下的 yudao 脚手架，提炼可借鉴/直接复用内容，并给出对 ATS-NEW 的可行性与注意事项。

## 0. 对比对象与前提

| 项 | 目标项目（被研究） | 我们（ATS-NEW） |
|---|---|---|
| 后端 | 芋道 RuoYi-Vue-Pro：Java 17 + Spring Boot 3.5 + MyBatis-Plus，Maven 多模块 | Django 6.0.6 + DRF 3.17.1 + Celery/Channels，单仓库多 app |
| 前端 | yudao-ui-admin-vben：Vue3.5 + Vite8 + TS + Ant Design Vue（多 app 变体），pnpm workspace | Vue3 + Vite5 + Pinia + Naive UI 2.44 + UnoCSS，npm 简单 monorepo |
| 真实状态 | **被大幅裁剪的 fork**：磁盘仅 8 个业务模块，部署文档声称 13 个（erp/wms/mes… 目录与 pom 均不存在）；前端 `pms` 因缺组件 `pnpm build:antd` 会失败 | 业务完整，部署已迁到独立仓库 `ats-deploy-infra` |

⚠️ **前提注意**：目标项目不是完整官方版，对比一律以**磁盘实际代码**为准，部署文档的模块清单/compose 的 `yudao-ui-admin`（旧 Vue2 版，不存在）不可照搬。

---

## 1. 技术架构对比

| 维度 | yudao（目标） | ATS-NEW（我们） | 差距判断 |
|---|---|---|---|
| 语言/运行时 | Java 17（运行 21-jre） | Python 3.14 + Django | 生态不同，仅可借鉴思想 |
| 后端框架 | Spring Boot + MyBatis-Plus | Django + DRF | 各有 ORM；我们缺"统一响应/分页/异常"体系（已在补 envelope） |
| 数据库/ORM | MySQL + MyBatis + dynamic-datasource(多数据源) | MySQL 8（生产/开发/测试统一，已禁用 SQLite）+ Django ORM | 对等 |
| 实时/异步 | WebSocket starter + Redis-MQ/RabbitMQ | Channels 4.3 + Celery 5.6 + Redis | 我们已覆盖 |
| 认证/权限 | Spring Security + 数据权限注解 | SimpleJWT + V2 权限(L1-L4 Scope) + data_permission app | 我们已有雏形，可借鉴"注解化数据权限" |
| 前端 UI | Ant Design Vue（另有 Element/Naive/TDesign 变体） | **Naive UI（已固定，不引入其它库）** | 我们已锁定单库，**适配器多库模式当前收益低** |
| 状态机/工作流 | Flowable BPM | django-fsm-2（状态机） | 路线不同：我们是轻量 FSM，非 BPMN |
| 监控 | SkyWalking / Spring Boot Admin / OTel | sentry-sdk + django-prometheus | 我们已覆盖 |
| 测试 | JUnit5 + Mockito + H2 | pytest + vitest + Playwright + a11y | 对等，我们 MySQL 对标其 H2（SQLite 已禁用） |
| 部署 | Dockerfile + compose(mysql+redis+server+admin) + 初始化SQL | 独立仓库 ats-deploy-infra（Docker/compose/nginx/webhook/systemd） | 我们更干净（业务/运维分离） |

---

## 2. 目录 / 模块结构对比

**后端**
- yudao：`yudao-framework`（15 个 starter 集合）+ `yudao-server`（空壳容器，靠依赖拼装）+ `yudao-module-*`（system/infra/bpm/report/mp/pay/hrm/ai）。**"框架与业务彻底分离，业务按 module 插拔"**。
- ATS-NEW：`apps/django/apps/*` 功能 app 平铺（interview/invitation/library/metrics/mou/notification/offer/onboarding/position/process/reason_library/referral/add_candidate/candidate/data_permission/duplicate_rule/entry_condition）。框架能力散落在各 app 与 `apps/common`。
- 借鉴点：把通用能力（信封/异常/日志/审计/数据权限）抽成独立 `apps/common/*` 或 `framework` 包，明确"框架 vs 业务"边界（我们已在做 envelope 治理，方向一致）。

**前端**
- yudao：`pnpm workspace`，`apps/*`（多端变体）+ `packages/@core`、`packages/effects`、`packages/ui-kit` 分层（业务不直连 UI 库，经 `adapter` 桥接）。
- ATS-NEW：`web/app` 单 SPA + `web/` 下其它（node_modules 巨）。无 workspace，无 adapter 层。
- 借鉴点：`packages/@core`/`effects`（请求层、权限、hooks）拆分思路可学；但**多 UI 库 adapter 因我们已锁定 Naive UI 而暂不必要**。

---

## 3. 依赖管理对比（重点可借鉴）

| 项 | yudao | ATS-NEW | 借鉴建议 |
|---|---|---|---|
| 后端版本治理 | Maven **BOM**（`yudao-dependencies`）+ `${revision}` 一处改全局生效 | `requirements.txt` **已用 `==` 精确锁** + `requirements-dev.txt` 分离（R9 整改，很好） | Python 无 BOM，但可用 **uv / pip-tools** 生成锁定；我们 `==` 已达标，无需 BOM |
| 前端版本治理 | **pnpm `catalog:` 单一版本表**（全仓版本集中一处） | npm，版本号散落各 `package.json` | 引入 **pnpm workspace + catalog**，或至少用 `package.json` 的 `overrides` 统一；ROI 中 |
| 构建编排 | **Turborepo**（turbo `--filter` 按 app 构建） | Makefile + Vite 单构 | 前端若膨胀再考虑 Turborepo |
| 包管理 | pnpm（preinstall 强制 only-allow） | npm | 可考虑切 pnpm（更快、支持 catalog） |

**结论**：后端依赖治理我们已基本到位（精确锁 + dev 分离）；最大可学的是**前端 catalog 单一版本表**。

---

## 4. 代码组织方式对比

- yudao：**DO/VO/DTO 严格区分**；统一响应 `CommonResult<T>{code,msg,data}` + `PageResult<T>{list,total}`；统一异常 `ServiceException`+`ErrorCode`；分层 `controller/service/impl/dal(dataobject+mapper)`。
- ATS-NEW：Django app 内 `views.py/services.py/models.py/serializers.py`；DRF serializer 充当 DTO；**缺统一的响应信封/分页包装/错误码体系**——但审计整改里已落地 `BaseModelViewSet` + 统一信封（正在做，与 `CommonResult` 对标）。
- 借鉴点：
  1. **统一响应/分页/异常**：我们已在做，对照 yudao 补齐 `code/msg/data` 与分页 `{list,total}`、业务错误码枚举即可，可行性**高**。
  2. **DTO/VO 分层**：Django 用 serializer 已足够，不必硬搬 Java 三件套，但可约定"入参 serializer / 出参 serializer"分离。
  3. **代码生成器**（见 §8.1-2）：最高价值借鉴。

---

## 5. 构建工具对比

- 后端：yudao `mvn -pl yudao-server -am install` + `spring-boot:repackage` 打可执行 jar；ATS 用 `gunicorn`(WSGI)+`daphne`(ASGI)。对等。
- 前端：yudao `vite8` + `turbo filter`；ATS `vite5` + `Makefile`。可借鉴：**Vite 升级到 8**、Turborepo 任务编排（前端增长后）。
- 我们 Makefile 已覆盖 install/run/test/lint，质量入口清晰，**无需大改**。

---

## 6. 测试策略对比

| 项 | yudao | ATS-NEW | 对标情况 |
|---|---|---|---|
| 后端单测 | JUnit5 + Mockito-inline + H2 内存库 | pytest + MySQL（`--create-db` 真实迁移） | 我们对标 H2 用 MySQL，且 CI 跑 MySQL8 更严（已禁用 SQLite） |
| 造数 | podam 随机造数 | 可用 **factory_boy** | 建议引入工厂，降测试样板 |
| 前端 | Vitest + happy-dom + Playwright + **lefthook**(git 钩子) | Vitest + happy-dom + Playwright + @axe-core | 我们缺 **git 钩子(lint-staged/husky/lefthook)**，建议补 |
| 隔离机制 | test-classes 下 `sql/{create,clean}.sql` | 我们有 `quarantine` marker 隔离不稳定用例 | 我们机制已先进 |

**借鉴**：① 引入 `factory_boy` 造数；② 加 `lefthook`/`husky` + `lint-staged` 提交前校验；③ 其余我们对标已到位甚至更好。

---

## 7. 部署方案对比

- yudao：Dockerfile(temurin:21-jre) + compose(mysql+redis+server+admin) + **初始化 SQL 挂 `docker-entrypoint-initdb.d` 自动建库** + Nginx 反代。
- ATS-NEW：业务仓库零运维文件，全在 `ats-deploy-infra`（Docker/compose/nginx/webhook/systemd）。**我们更优**（业务/运维彻底分离）。
- 借鉴点：① 数据库**初始化/seed 脚本自动化挂盘**（我们 migration 已够，但 seed 数据可更自动化）；② 多环境 env 注入；③ 监控面板（我们已有 sentry+prometheus，可对标本 Dashboards）。

---

## 8. 可复用组件 / 模式（核心：可借鉴清单 + 可行性 + 注意事项）

### 8.1 后端（只能借鉴"模式"，不能搬 Java 代码）

| # | 组件/模式 | 来源 | 对 ATS 价值 | 可行性 | 注意事项 |
|---|---|---|---|---|---|
| 1 | **统一响应/分页/异常** `CommonResult/PageResult/ServiceException` | yudao-common | 高（我们已在做 envelope） | **高** | 直接对照补齐 `code/msg/data` + 分页 `{list,total}` + 业务错误码枚举；复用现有 `BaseModelViewSet` |
| 2 | **代码生成器**（元数据驱动，前后端+SQL+单测一键生成，106 个 `.vm`） | `yudao-module-infra/.../codegen` | **极高**（候选/职位/面试/Offer 大量 CRUD） | 中（需投入，ROI 高） | 用 `manage.py gencrud` 或 cookiecutter 自建 Django 版；避免直接抄 `.vm`，改为 Python 模板 |
| 3 | **数据权限注解** `@DataPermission` + 规则工厂 + AOP 注入 WHERE | starter-biz-data-permission | 高（招聘官只看自己团队候选人） | **高** | 我们 `data_permission` app 已有雏形；借鉴"注解+规则工厂"模式，用 Django 中间件/查询集过滤实现 |
| 4 | **字典管理** `DictData` + 前端 `dict-tag` | module-system + components/dict-tag | 高（状态/类型/学历等枚举集中） | **高** | 独立小模块，前后端配套；我们有大量硬编码枚举可迁此 |
| 5 | **Excel 导入导出** `ExcelUtils`(FastExcel)+模板 | starter-excel | 高（候选人批量导入刚需） | **高** | 我们已有 `openpyxl`，封装等价 `ExcelUtils`（下拉框/列宽/精度保护）即可 |
| 6 | **操作/访问日志** `@ApiAccessLog` + bizlog AOP 落库 | starter-web + bizlog-sdk | 中-高（"谁改了哪条记录"审计） | 中 | 注意异步落库避免阻塞主链路；我们审计需求明确 |
| 7 | **文件上传** `FileService` + 前端 uploader | module-infra + components/upload | 中（简历附件） | 中 | 先确认我们是否已有等价实现再补 |
| 8 | **WebSocket 实时通知** | starter-websocket | 中（新投递/面试提醒） | **高（已有 Channels）** | 我们已具备，对标增强即可 |
| 9 | **定时任务** quartz | starter-job | 中 | **高（已有 Celery beat）** | 已有，无需引入 |
| 10 | **消息队列** redis-mq/rabbitmq | starter-mq | 中（简历解析/邮件解耦） | **高（已有 Celery/RQ）** | 已有，无需引入 |
| 11 | **安全套件** XSS/接口签名防重放/Lock4j | starter-web/starter-protection | 中 | 中 | 我们已有 SSRF 治理 + ratelimit；可加"接口签名防重放" |
| 12 | **监控** SkyWalking/SBA | starter-monitor | 中 | **高（已有 sentry+prometheus）** | 已有，本 Dashboards 即可 |
| 13 | **敏感词/IP 风控** | starter-biz-ip/sensitive-word | 中（登录风控、简历敏感词） | 中 | 可引入 `sensitive-word` 思路（Python 有 `sensitive` 类库） |
| 14 | **多租户 SaaS** 租户上下文自动注入 | starter-biz-tenant | 低-中（未来多企业版） | 低（架构级） | 当前单租户，属重大架构决策，暂不急 |
| 15 | **工作流 BPM** Flowable + bpmn-js | module-bpm | 中-高（招聘流程可视化） | **低（路线冲突）** | 我们已用 `django-fsm-2` 状态机；引入 BPM 是"替代还是并存"需决策，重量级，慎入 |

### 8.2 前端（Vue 同语言，**可直接参考实现**）

| # | 组件/模式 | 来源 | 对 ATS 价值 | 可行性 | 注意事项 |
|---|---|---|---|---|---|
| 1 | **权限指令** `v-access:role/code`（无权限直接移除 DOM） | `packages/effects/access` | 高（按钮级"仅 HR 可发 Offer"） | **高** | 小改动，对标我们前端权限体系 |
| 2 | **声明式/Schema 表单** `VbenForm` + `form-create` | `@core/ui-kit/form-ui` + components/form-create | 高（候选人/职位表单降码） | 中-高 | 借鉴 schema 驱动表单；我们表单偏手写，可逐步迁移 |
| 3 | **统一请求层** `request-client`(含 upload/download/SSE/错误码) | `packages/effects/request` | 中-高 | 中 | 我们 axios 封装可增强（SSE 流式、统一错误码映射） |
| 4 | **组件适配器** `adapter/component`（桥接 UI 库与业务） | `apps/web-antd/src/adapter` | 低（**我们已锁定 Naive UI，不换库**） | 低 | 当前收益有限；仅当未来做多品牌/多 UI 才值得 |
| 5 | **字典标签/选择器** `dict-tag` + `use-dict-select` | components/dict-tag | 高（配合后端字典 #4） | **高** | 前后端配套 |
| 6 | **上传组件** `upload/` + `use-upload` | components/upload | 中（简历上传） | 中 | 配合后端文件上传 |
| 7 | **操作日志查看组件** `operate-log` | components/operate-log | 中（配合后端 #6） | 中 | 消费 `@ApiAccessLog` 数据展示 |
| 8 | **高性能表格** `vxe-table` adapter + 操作列 | adapter/vxe-table | 中（候选人池大列表） | 中 | 我们已有虚拟滚动(#39)，对标而非替换 |
| 9 | **Cron 表达式组件** `cron-tab` | components/cron-tab | 中（定时任务配置 UI） | 中 | 仅当做定时任务管理页时需要 |
| 10 | **富文本** tinymce（我们已用 wangeditor） | components/tinymce | 低 | — | 我们已有等价物 |
| 11 | **国际化** vue-i18n 多语言 | locales | 低（我们已有且做了域拆分 #39） | — | 我们已领先 |

---

## 9. 优先级与 ROI 排序（适配 ATS 的建议）

**立刻可借鉴（高 ROI / 低风险）**
- 统一响应/分页/异常（已在做，对照 yudao 补齐 → 完成度最高）
- 数据权限"注解+规则工厂"模式（我们 `data_permission` 已有雏形）
- 字典管理（小模块，前后端配套，消除硬编码枚举）
- Excel 导入导出工具封装（候选人批量导入刚需）
- 前端权限指令 `v-access`（小改动）

**中期（需投入但价值大）**
- 轻量代码生成器 `manage.py gencrud`（CRUD 全栈降码，ROI 最高的一项）
- 声明式/Schema 表单（表单降码）
- 统一请求层增强（SSE/错误码）
- 操作/访问日志 AOP（审计需求）

**慎入（重 / 需架构决策 / 我们已有等效物）**
- BPM 工作流（vs 现有 django-fsm-2 状态机，路线冲突）
- 多租户 SaaS（架构级）
- 多 UI 库适配器（已锁定 Naive UI，当前无收益）
- 消息队列/定时任务/WebSocket/监控（我们 Celery/Channels/sentry 已覆盖，对标即可，勿重复引入）

**工程治理（低成本高收益）**
- 前端引入 pnpm workspace + `catalog` 单一版本表（或 npm `overrides`）
- 引入 `factory_boy` 测试造数 + `lefthook`/`husky` 提交前校验
- Vite 升级到 8（与 yudao 对齐，性能更好）

---

## 10. 总注意事项

1. **语言栈差异**：目标是 Java 生态（MyBatis/注解 AOP/Spring），**后端不能搬代码，只能搬"模式与思想"**；前端 Vue 部分（同语言）可直接参考组件实现。
2. **裁剪 fork 风险**：目标项目不完整，以磁盘代码为准；其部署文档的模块清单/compose 的 `yudao-ui-admin` 均已失效，不要照搬。
3. **我们已有大量等效物**：WebSocket(Channels)、MQ/定时(Celery)、监控(sentry/prometheus)、状态机(django-fsm-2)、i18n(域拆分 #39)、虚拟滚动(#39)、统一信封(envelope 治理)。这些**对标增强即可，不必从零借鉴或重复引入**。
4. **已有硬约束**：UI 库已固定 Naive UI（不引入其它库），所以 yudao 的"多 UI 库 adapter"模式当前无收益；部署已独立仓库，业务仓库保持零运维文件。
5. **避免过度工程**：BOM/catalog 在 Python 侧用 `uv`/`pip-tools` 即可达到"单一版本事实源"，不必硬套 Maven 概念。
