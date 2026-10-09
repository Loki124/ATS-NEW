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

## 5. 测试约束（关键）

- **当前 CI 测试库是 sqlite**，而 sqlite 的 `MATCH`/FULLTEXT 与 MySQL 语义不同，
  无法在现有 CI 验证 FULLTEXT 行为。
- 因此方案 A 必须：在 CI 增加一条 **MySQL 集成测试**（或本地用 MySQL fixture）
  专门验证 `keyword_match()` 的召回/排序，否则代码无法被 CI 证明正确。
- 这是"索引级迁移"不能盲目开工的核心原因之一——**没有 MySQL 验证环境前，
  不应把 `keyword_q` 切到 FULLTEXT**。

## 6. 决策待办

- [ ] DBA / infra 确认走 A 还是 B（或暂不迁移，维持 `LIKE`）；
- [ ] 若 A：确认是否提供 MySQL 测试环境 / CI 集成测试；
- [ ] 若 B：确认 ES 集群资源与同步方案（双写 vs CDC）。
