# 搜索基建方案 Spike（#38 索引级迁移）

> 状态：**仅出方案，代码改造待 DBA / infra 拍板**。代码侧 `keyword_q()` 收口已完成（见
> `apps/common/search.py`），本文件只讨论"索引级优化"这一基建决策项。
> 当前线上搜索仍是 `field__icontains`（即 `LIKE '%kw%'`，B-Tree 索引失效、大表线性扫、
> 无中文分词、无相关性排序）。

---

## 1. 现状与痛点

| 项 | 内容 |
|---|---|
| 入口 | `apps/common/search.py:keyword_q()`（统一收口，业务无感） |
| 实现 | `Q(field__icontains=kw)` 的 OR 组合 |
| 问题 | ① 模糊前缀 `%kw%` 无法命中 B-Tree 索引，大表退化为全表扫描；② 无中文分词，
  `icontains` 按字符子串匹配，无法做"词"级召回；③ 无相关性排序；④ 无法跨多字段加权 |
| 规模 | 候选人 / 简历 / 需求表均为主要被搜对象，随数据增长延迟线性恶化 |

---

## 2. 两条候选路径

### 方案 A：MySQL 原生 FULLTEXT + ngram 解析器

- **机制**：InnoDB FULLTEXT 配合 `ngram_token_size`（默认 2）对 CJK 做二元/多元切分，
  使中文可被 FULLTEXT 索引；`MATCH(... ) AGAINST(... IN BOOLEAN MODE)` 替代 `LIKE`。
- **改动面**：仅改 `keyword_q()` 内部——把 `__icontains` 换成 `MATCH...AGAINST`
  （或新增 `keyword_match()` 并让 `keyword_q` 路由），业务调用方不变。
- **收益**：零新增基础设施；与现有 MySQL 同库同事务，无数据同步/一致性问题；
  改造成本最低（≈1 处 + 迁移脚本建 FULLTEXT 索引 + 回滚 DDL）。
- **代价 / 风险**：
  - ngram 粒度与 `ngram_token_size` 需调参（太小召回噪、太大漏召回）；
  - 相关性排序能力弱于 ES；
  - 仍占用主库算力，超高 QPS 下不与主库读写隔离；
  - `IN BOOLEAN MODE` 语法与 `LIKE` 语义不完全等价，需回归既有搜索用例。

### 方案 B：独立 Elasticsearch

- **机制**：ES + IK 中文分词，建候选/简历/需求索引；写链路经 CDC（或应用双写）同步，
  读链路走 ES 查询。
- **收益**：专业 CJK 分词 + 相关性打分（BM25）+ 聚合/高亮；读写与主库隔离，可水平扩展；
  支撑未来"语义/向量"检索演进。
- **代价 / 风险**：
  - **新增一整套基础设施**：ES 集群、索引生命周期、写入同步管道（双写或 CDC）、
    监控告警——ops 成本显著；
  - **数据一致性**：双写有事务边界问题，CDC 有同步延迟，需定义"近实时"SLA；
  - **迁移复杂度**：历史数据重建索引、回滚困难（ES 与 DB 双源）；
  - **团队成本**：需具备 ES 运维能力。

---

## 3. 推荐

- **默认推荐方案 A（MySQL ngram FULLTEXT）** 作为第一阶段：
  - 改动收敛在 `keyword_q()` 一处，风险/成本最低；
  - 多数 ATS 规模（千万行级以内）下 FULLTEXT 已能解决"线性扫"瓶颈；
  - 用**特性开关**（`settings.SEARCH_BACKEND = 'like' | 'fulltext'`）灰度，
    可一键回退到 `LIKE`，不阻塞线上。
- **仅当**出现以下信号再评估方案 B：搜索 QPS 持续高位拖累主库、需要语义/向量检索、
  或多租户隔离要求读写彻底分离。
- 无论选哪条，都**先在本 Spike 结论上由 DBA / infra 拍板**再开工。

---

## 4. 若选 A 的实施拆解（待拍板后展开）

1. 在预发 MySQL 调整 `ngram_token_size` 并 `ALTER TABLE ... ADD FULLTEXT(...)`；
2. `keyword_q()` 新增 `backend` 参数，按开关路由 `LIKE` / `MATCH...AGAINST`；
3. 迁移脚本 + 回滚 DDL；
4. 回归 `apps/candidate`、`apps/demand` 等搜索用例，校验召回与排序。

## 5. 测试约束（已核实）

- **CI 的 `test-backend` 任务已起 `mysql:8.0` service，并通过 `DB_ENGINE=mysql`
  让全量测试跑在 MySQL 上**（`config/settings/test.py:29` 支持该开关，
  2026-10-08 #26 对齐生产 MySQL 8）。因此 FULLTEXT / ngram 行为**可在现有 CI 直接验证**，
  无需新增验证环境。
- 本地快速通道默认仍是 SQLite（`DB_ENGINE` 缺省 = `sqlite`），要本地验证 FULLTEXT 只需：
  `DB_ENGINE=mysql DB_NAME=ats_test DB_USER=root DB_HOST=127.0.0.1 DB_PORT=3306 pytest ...`
  （或设 `DATABASE_URL=mysql://...`），指向与 CI 同款的 MySQL 8。
- 结论：**方案 A 无验证阻塞**。把 `keyword_q` 切到 `MATCH...AGAINST` 时，
  只需补一条针对 `keyword_match()` 召回/排序的用例，它会自然落在现有 MySQL CI job 上跑通。

## 6. 决策结论（2026-10-09）

- **方案 A 已批准并落地**：用户确认走 MySQL ngram FULLTEXT（无需 ES）。
- 实现：
  - `apps/common/search.py`：`keyword_q` 新增 `backend` / `model` 参数；`fulltext` 路径用
    `MATCH(\`table\`.\`col\`) AGAINST (%s) > 0`（ngram），关联字段 / 非安全标识符回退 `icontains`；
  - `config/settings/base.py`：新增 `SEARCH_BACKEND`（默认 `auto` → MySQL 走 FULLTEXT、其余回退 LIKE）；
  - `apps/candidate/migrations/0013_*`、`apps/application/migrations/0007_*`：MySQL-only 的 FULLTEXT 索引
    （`WITH PARSER ngram`），SQLite/Postgres 自动跳过（RunPython 按 vendor 守卫）；
  - `apps/common/tests/test_search.py`：MySQL 门控用例，验证中文 ngram 召回与关联字段回退。
- 验证：本地 MySQL 9.6 与 CI `mysql:8.0` 同款语义，用例全部通过。

## 7. 后续可选

- [ ] 若未来搜索 QPS / 语义检索需求上升，再评估方案 B（ES）；
- [ ] 灰度 / 回滚：设 `SEARCH_BACKEND=like` 即可一键回到 `LIKE`，无需改动代码或索引。
