# F1–F4 / G1–G8 — Phase 5（性能与可维护性）+ Phase 6（文档与台账）（2026-10-21）

> 对应整改计划卡 `docs/PLAN_项目整改_2026-10-21.md`：
> **Phase 5**：F1 Celery 幂等化 / F2 任务重试配置 / F3 外部 HTTP 移出请求路径 / F4 批量导入 N+1
> **Phase 6**：G1–G8 文档与台账口径
> **未做**：F5（prefetch_related）、F6（拆大组件）、F7（清理 any）—— 理由见 §7。

---

## 1. 落地一览

| 卡 | 做了什么 | 验证 |
|---|---|---|
| F1 | 每日看板快照**幂等**（新增唯一幂等键 + `update_or_create`）；提醒任务改「**先标记后发**」（新增抢占位 `sending_at`） | 快照跑两次只 1 条；抢占/超时重抢/失败释放 4 条用例 |
| F2 | 10 个 Celery 任务补 `max_retries` + `autoretry_for`（**只加 max_retries 不会重试**） | 10 参数化静态守卫用例 |
| F3 | 通知外部通道调用**移出请求路径**（`on_commit` 入队 + 双重兜底） | 4 条用例：请求路径不碰外部通道 |
| F4 | 字典批量导入 N+1：2N 次查询 → O(1) 预取 | 3 条 vs 9 条 SELECT 次数**对比** |
| G1–G8 | README 当前阶段/目录/安全说明；TODO.md 两处口径矛盾；07-audit 索引；清理 sqlite 残留 | 链接全量脚本校验 |

**后端整跑：3224 passed / 12 skipped / 0 failed**（87.3s）。

---

## 2. F1｜Celery 幂等化

### 2.1 每日看板快照

**缺陷**：`generate_daily_report_snapshot` 每次都 `create` → 任务重跑（Celery 重试 / 手动补跑）
或并发跑，**同一天会出现多条看板快照**。

**改法**：`ReportSnapshot` 增 `snapshot_key`（唯一、可空）—— MySQL 唯一索引**允许多个 NULL**，
故不影响其他快照；任务改 `update_or_create(snapshot_key='DASHBOARD:YYYY-MM-DD')`。
迁移：`apps/analytics/migrations/0007_reportsnapshot_snapshot_key.py`。

> 为什么不用「`(report_type, name)` 唯一约束」：`name` 是自由文本且可由 API 写入，
> 加唯一约束会把「重名」从允许变成 400 —— 那是**产品行为变更**，不该由性能卡顺带引入。
> 独立幂等键只约束「每日看板」这一类，不碰其他快照。

### 2.2 提醒任务：先标记后发

**缺陷**：原实现是「**发 → 记 `sent_at`**」。若外部通道**已经收到**、但落 `sent_at` 前进程崩溃
（容器被杀 / OOM / 部署重启），下一轮会**重发** → 候选人收到两封一样的提醒。

**改法**：`NotificationLog` 增 `sending_at`（抢占位），发送前先用**条件 UPDATE** 抢占本行：

| 情形 | 处理 |
|---|---|
| 抢到（`sending_at` 由 NULL 置 now） | 才真正发送 |
| 抢不到（别人正在发 / 上一轮刚发过） | 跳过，不重复发 |
| 抢占超 5 分钟（上一轮崩溃） | 允许重新抢占 → **既不重复也不漏发** |

迁移：`apps/notification/migrations/0004_notificationlog_sending_at.py`。

---

## 3. F2｜Celery 任务重试配置

**关键认知**：**只加 `max_retries` 不会自动重试** —— Celery 需要 `autoretry_for=(瞬时异常)`
（或任务体内显式 `raise self.retry()`），且异常要真正**逃出任务体**才会被重跑。
「配了 `max_retries=3` 却没有 `autoretry_for`」是**看起来配了、实际不重试**的典型退化。

故给 10 个任务统一加：

```python
@shared_task(
    name='...',
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(OperationalError,),
)
```

选 `django.db.OperationalError`（DB 抖动 / 死锁 / 连接断开）：它是 `DatabaseError` 子类但
**不含** `IntegrityError` / `ProgrammingError`（非瞬时，重试无意义只会放大副作用）。

涉及：`analytics`×2、`gdpr`×1、`invitation`×2、`notification`×1、`talent_pool`×2、
`metrics`×1、`add_candidate`×1。

**静态守卫**：新增参数化用例逐个断言 `max_retries` / `default_retry_delay` / `autoretry_for`
（含 `OperationalError`）都在 —— 防止后续改动把重试配置悄悄回退。

---

## 4. F3｜通知外部通道调用移出请求路径

### 4.1 前提核实（不轻信计划卡）

计划卡列了 9 处 `timeout=10` 的同步外部调用。逐个查调用方后确认**真正在请求路径上的只有一类**：

| 调用点 | 是否在请求路径 |
|---|---|
| `NotificationService.send_notification` → 邮件/短信/企微 | ✅ **在**（Offer 审批、面试安排、公告推送、自动化规则执行） |
| `apps/integration/views.py:73,79,81` | 集成**自检端点**（故意同步，「测试短信」/「测试消息」） |
| `suppliers/hmac_adapter.py` / `ssrf.py` | 供应商同步批处理（后台任务） |
| `integration/services.py` 的阿里云/企微/moka | 由 Celery 任务调用 |

### 4.2 改法

1. 落库后 `transaction.on_commit(...)` **入队**由 Celery 任务投递，请求立即返回。
   **必须用 `on_commit`**：不等事务提交就入队，worker 会抢在提交前读不到这一行。
2. **兜底 1**：broker 不可用（开发机没起 worker）→ 同步投递，**不丢通知**。
   异常集刻意收窄（kombu / redis / socket），**不新增宽捕获**（盲 except 基线仍是 147）。
3. **兜底 2**：每小时 `send_pending_reminders` 捡走仍未送达的日志。
4. 投递逻辑抽成 `NotificationDispatcher.deliver_log()`（抢占 → 发送 → 落状态），
   即时任务与每小时任务**共用** → 两条路径不会重复发送。

### 4.3 两个需要说清的点

- **worker 依赖不是新假设**：部署脚本本就起
  `celery -A celery_app worker -Q celery,time_limit,automation,notification,analytics,application,gdpr,invitation,talent_pool` + beat，
  且每小时提醒重试 / 每日看板快照 / GDPR 保留期清理**本来就是** Celery 定时任务 —— worker 不起时它们同样不跑。
- **返回值语义变更**：`send_notification` 的 `sent` 从「已发送」变为「**已受理(已入队待投递)**」，
  另加 `queued: True`。唯一依赖该字段的生产调用方是公告推送
  （`apps/announcement/views.py:235` 决定是否记录 log_id）→ 语义等价。

### 4.4 踩坑记录（值得留档）

本仓**测试环境里 Celery 的 eager 模式不生效**：实测 `current_app.conf.task_always_eager = False`
（`current_app` 是 Celery 默认 app，未继承 Django 的 `CELERY_*` 设置；`config/settings/test.py` 里
`CELERY_TASK_ALWAYS_EAGER = True` 只作用于 `celery_app` 那个 app 实例）。
→ 测试里 `.delay()` 会**真投到 broker**，任务不执行（表现为 state=PENDING）。
故 F3 的用例**直接调用任务函数**而非 `.delay()`（任务体与投递方式无关）。

---

## 5. F4｜字典批量导入 N+1

**缺陷**：`DictionaryTypeViewSet.submit` 处理「已存在项」时，每条 2 次查询：
① `DictionaryItem.objects.get(id=p['item_id'], ...)`；
② `_has_children_final()` 内的 `filter(parent=item, ...)` → N 条 = **2N 次**（导入 500 条 = 1000 次往返）。

**改法**：批量预取 —— 一次取全部已存在项 + 一次取子级映射（`{parent_id: [child_id]}`），循环内零查询。
`_has_children_final` 增可选 `live_children` 参数，不传时退回单查（其他调用方不受影响）。
业务语义保持不变：找不到的 `item_id` 仍由外层 `except DictionaryItem.DoesNotExist` → 400。

**验证方式**：用「**3 条 vs 9 条的 SELECT 次数对比**」而不是写死魔法数字 ——
数字会随无关改动漂移，对比法不会。另锁三条语义：值确实被更新、缺失项仍 400、有子级不可停用。

---

## 6. G1–G8｜文档与台账

| 卡 | 实际改动 |
|---|---|
| G1 | README「当前阶段」改为如实反映：台账 S0–S9 共 125 项 / 完成 96 项（76.8%）+ **2026-10-21 系统性整改 Phase 0–4 全部完成**（每阶段一句话）+ 明确待办（C4 / E8 / E9 / Phase 5 / Phase 6）+ 指向诊断报告与计划卡 |
| G2 | 目录树移除 `ops/`，注明「部署/运维文件已迁出本仓库（ats-deploy-infra）」，仓库根 `ops/` 仅为历史残留空壳、**不具备任何部署能力** |
| G3 | 新增「安全说明」：`PII 加密范围`（目前**仅身份证号**是字段级加密；手机号/邮箱仍是明文 → C4）、`PII_HASH_SALT` 必填（生产缺配置直接拒绝启动；历史 salt `ats-pii` 公开可反查手机号）、`ENCRYPTION_KEY` 必填（不得复用 `INTEGRATION_FERNET_KEY`）、密钥轮换（`ENCRYPTION_KEYS` + `reencrypt_pii`）、`ops/.env` 的角色（本地残留、非部署配置、禁止提交真实密钥） |
| G4 | TODO.md 的 S6 口径注释**仍然矛盾**（已逐项核对：S6 明细表 7 项全 ✅、汇总表 S6 行「0/0/0/7/0」）→ 改为与汇总表一致 |
| G5 | 计数口径的分项加总 30 ≠ 声称的 29（汇总表 S5 行是「未开始 1 / 受阻 1 / 挂起 1」= 3 项，注释写「S5×4（2 未开始…）」）→ 改为 S5×3 |
| G6 | 已在 Phase 1 收尾时完成（`pytest.ini` 改为只指向 CI 的「Report test count」单一事实源，不硬编码数字） |
| G7 | 新建 `docs/07-audit/INDEX.md`，登记全部 26 份文档；README 与索引的**全部相对链接已脚本校验存在** |
| G8 | 两个 sqlite 残留（`db.sqlite3` 0 字节 / `dev_db.sqlite3` 4.5MB，均**未被 git 跟踪、无任何代码引用**）已移入回收站（**可恢复**） |

---

## 7. 未做项与理由

| 卡 | 理由 |
|---|---|
| **F5** 补 `prefetch_related` | 收益依赖**真实数据量**（本地库数据量小，EXPLAIN 无意义）→ 应在生产量级副本上逐页用 EXPLAIN 验证后再改，避免「加了 prefetch 反而更慢」 |
| **F6** 拆大组件（10 个 >1000 行的 .vue） | 拆 2000 行组件的回归面极大，须按业务价值分批、每批独立验证，不能一次全拆 |
| **F7** 清理 `any`（约 200 处） | 宜伴随 F6 的拆分顺带做（拆出的子模块本身就不该用 `any`） |

---

## 8. 改动文件清单

**新增**

| 文件 | 作用 |
|---|---|
| `apps/django/tests/test_f1_f2_celery_idempotency.py` | 幂等 + 重试配置（17 条） |
| `apps/django/tests/test_f3_notification_async.py` | 请求路径不碰外部通道（4 条） |
| `apps/django/tests/test_f4_dictionary_nplus1.py` | N+1 查询数对比 + 语义（4 条） |
| `apps/django/apps/analytics/migrations/0007_reportsnapshot_snapshot_key.py` | 快照幂等键 |
| `apps/django/apps/notification/migrations/0004_notificationlog_sending_at.py` | 通知抢占位 |
| `docs/07-audit/INDEX.md` | 审计文档索引（G7） |

**修改**

| 文件 | 改动 |
|---|---|
| `apps/django/apps/analytics/models.py` | `ReportSnapshot.snapshot_key` |
| `apps/django/apps/analytics/tasks.py` | 快照幂等 + 2 个任务的重试配置 |
| `apps/django/apps/notification/models.py` | `NotificationLog.sending_at` |
| `apps/django/apps/notification/services.py` | `deliver_log()`（抢占投递）+ `send_notification` 改入队 + 同步兜底 |
| `apps/django/apps/notification/tasks.py` | 新增 `send_notification_log_task`；重试任务改用共用投递逻辑 |
| `apps/django/apps/dictionary/views.py` | 批量预取消除 N+1 |
| `apps/django/apps/{gdpr,invitation,talent_pool,metrics,add_candidate}/tasks.py` | 重试配置 |
| `README.md` | 当前阶段 / 目录结构 / 安全说明（G1–G3） |
| `TODO.md` | S6 口径注释 + 计数算术（G4 / G5） |
