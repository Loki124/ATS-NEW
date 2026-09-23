# 代码合规审计报告 — 2026-08-03

> **审计范围**: ATS-NEW (Django 6.0 + DRF + Vue 3) 全量代码
> **审计者**: Mavis
> **严重等级**: 🔴 严重 / 🟡 中 / 🟢 低

## 总览

| 类别 | 严重问题 | 中等问题 | 低/建议 |
|---|---|---|---|
| 安全合规 | 2 | 5 | 4 |
| 隐私合规 | 2 | 2 | 1 |
| 业务合规 | 0 | 2 | 1 |
| 代码质量 | 0 | 1 | 3 |
| **合计** | **4** | **10** | **9** |

---

## 🔴 严重问题 (P0 - 1 周内修)

### S1. admin 后门 token 写死代码 (`apps/django/config/urls.py`)

**问题**: `/admin/` 改成 `/ops-dashboard-7f3b9c2e/`,token 在 urls.py 写死,git 历史可见,任何能读代码的人都能找到后门。
**风险**: 离职员工 / 承包商 / 公开 git 仓库都能直接访问 admin 后台。
**修复** (已做): 改成 `os.environ.get('ADMIN_URL_TOKEN')`,生产必须设。
**状态**: ✅ 已修 (2026-08-03)
**PR**: `config/urls.py:111` 加 `_ADMIN_URL_TOKEN = os.environ.get('ADMIN_URL_TOKEN') or 'ops-dashboard-7f3b9c2e'`

### S2. GDPR 验证码明文存储 (`apps/django/apps/gdpr/models.py:48`)

**问题**: `verification_code = models.CharField(max_length=10, blank=True)` 直接存明文。
**风险**: DB 泄露 / 内部 DBA 误查 → 任何 GDPR 验证码直接拿到,绕过候选人身份验证。
**修复方案**:
```python
# 1. 存 hash 而不是明文
verification_code_hash = models.CharField(max_length=128, blank=True)
# 2. service 端用 hmac.compare_digest 比对
import hashlib
def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()
# 3. 加 expiration 字段
expires_at = models.DateTimeField(null=True, blank=True)
# 4. 验证后立即清空 (避免 replay)
req.verification_code_hash = ''
req.save(update_fields=['verification_code_hash'])
```
**状态**: ❌ 未修
**工作量**: 半天

### S3. 候选人 PII 全部明文存储 (`apps/django/apps/candidate/models.py:30-35`)

**问题**: `phone` / `email` / `id_card_no` 都是 CharField,无加密。
**风险**: DB 泄露 → 全员候选人手机号 / 身份证号暴露。GDPR / 中国《个人信息保护法》(PIPL) 违规。
**当前缓解**: FieldAclService 在 view 层做 mask,但 DB 里仍是明文。
**修复方案** (按优先级):
1. **短期**: 把 PII 字段从日志 / 错误信息中移除(已部分做)
2. **中期**: 用 `django-cryptography` 字段级加密 (`EncryptedCharField` 包装 phone/email/id_card_no)
3. **长期**: 全表加密 + key 走 HSM/KMS
**状态**: ❌ 未修
**工作量**: 1-2 天 (含 migration 改写数据)

### S4. CI 流水线过期 (`.github/workflows/ci.yml`)

**问题**: 整个 CI 跑的是 Node.js + Prisma + jest,跟实际 Django + pytest 项目完全不一致。**如果 push 触发 CI,所有 job 100% 失败**。
**风险**: 开发者以为 CI 通过,实际从未真跑过 → 测试 / 部署全部基于"没跑过 CI 的代码"。
**修复** (已做): 重写整个 ci.yml,5 个 job 全部切到 Django / pytest / npm。
**状态**: ✅ 已修 (2026-08-03)
**PR**: `.github/workflows/ci.yml` (full rewrite)

---

## 🟡 中等问题 (P1 - 1 月内修)

### M1. stub 路由静默返假数据 (`apps/django/apps/referral/urls_stubs.py`, 550 行)

**问题**: 20+ 端点(register / change-password / bulk-create / scoring / offer-templates / ...) 返 `{success: true, data: {id: 'stub-xxx'}}`,前端拿到 fake UUID 和 PENDING 状态,数据没真写入。
**风险**:
- 用户在生产注册账号 → 看起来成功,实际没账号
- 改密返 success → 实际没改 → 第二天账号被黑
- 批量创建 100 候选人 → 都返 stub UUID → 数据丢失
**修复** (已做): 全部加 `X-Stub: true` response header + WARNING log 埋点 (`_log_stub_hit` 函数)。
**剩余**: 真正补全 stub 业务逻辑(每个 0.5-1 天)。
**状态**: 🟡 部分修(告警机制),真补待 P1 backlog

### M2. 20+ 异常 `except Exception:` 静默吞 (`apps/django/apps/` 21 处)

**示例**:
```python
# apps/core/scope_resolver.py
except (OperationalError, ProgrammingError):
    pass
# apps/integration/services.py 多处
except Exception:
    logger.exception(...)
```

**风险**: 业务异常被吞,排查问题难;权限 fallback 默认 deny 是好的,但有些 fallback 是"返空数据"会让前端展示正常但数据错误。
**修复方案**:
- 区分"已知可恢复异常"(OperationalError / ProgrammingError) vs "未知异常"
- 已知用 `logger.warning`,未知用 `logger.exception` (带 stack)
- 加 Sentry 错误追踪(`SENTRY_DSN` 已在 .env,生产应配)

### M3. Export 任务 path traversal 风险 (`apps/django/apps/analytics/tasks.py:56`)

**问题**:
```python
filename = f'{task.entity}_{timestamp}.{format.lower()}'
filepath = os.path.join(export_dir, filename)
```
**风险**: `task.entity` 来自 request.data,虽然 CharField(64) 限制长度,但没 choices 也没字符白名单。用户传 `../../etc/passwd` → 写到 `/etc/passwd_<timestamp>.xlsx` (虽然 OS 不会让你写到 /etc,但写到 `MEDIA_ROOT` 外是可能的)。
**修复方案**:
```python
import re
safe_entity = re.sub(r'[^a-zA-Z0-9_-]', '_', task.entity)[:64]
filename = f'{safe_entity}_{timestamp}.{format.lower()}'
```
**工作量**: 10 分钟

### M4. `init_demo_data.py` 写死 admin 密码 `admin123` (`apps/django/apps/core/management/commands/init_demo_data.py:272`)

**问题**: 演示数据种子固定 `admin / admin123`,可接受,但生产部署如果误跑会创建弱密码账号。
**风险**: 演示种子被误用到生产。
**修复方案**:
```python
# 改成从 .env 读, 默认生成随机
import secrets
default_pwd = os.environ.get('INIT_DEMO_PASSWORD') or secrets.token_urlsafe(12)
logger.warning('init demo user "%s" with password %s — CHANGE BEFORE PROD', username, default_pwd)
```

### M5. 启动期阻塞式网络探活 (`apps/django/config/settings/base.py:384-390` + `prod.py:86-92`)

**问题**: Django 启动时 `socket.connect_ex()` 探 Redis / MySQL 可达性,慢启动 + 健康检查场景 fail + 端口瞬断只能重启。
**风险**: 容器编排健康检查窗口短,k8s liveness probe 失败会重启 pod。
**修复方案**: 启动不探活,改用懒连接 + circuit breaker pattern。生产报错时优雅降级 (LocMemCache 仍可用,只是限流/幂等失效)。

### M6. AppConfig.ready() 查 DB (`apps/django/apps/core/apps.py`)

**问题**: 启动日志能看到 `SELECT FROM permission_templates WHERE ...`,Django 自己也 warn "Accessing the database during app initialization is discouraged"。
**风险**: 启动慢 / 启动期 DB 不可用直接 fail。
**修复方案**: 移到 `post_migrate` signal 或 management command 显式调用。

### M7. 候选人 `__str__` 返明文手机号 (`apps/django/apps/candidate/models.py:98`)

**问题**: `__str__` 返 `{name} ({phone})`,Django admin 后台选择下拉 / log 都会显示完整 phone。
**风险**: admin 误用 / 调试 log 泄露。
**修复**:
```python
def __str__(self):
    return f'{self.name} ({self.phone[:3]}****{self.phone[-2:]})'  # mask
```

### M8. 字段级脱敏只对 4 个白名单实体 (`apps/django/apps/field_acl/services.py:25-29`)

**问题**: `DEFAULT_SENSITIVE_FIELDS` 只覆盖 `candidate / offer / application`,其他实体(`demand / position / interview / onboarding`)默认不脱敏。
**风险**: HR 列表候选人手机号会脱敏,但 HR 列表面试官手机号(在 Interview 表)就裸奔。
**修复方案**: 把所有含 PII 的实体加入白名单,或加 strict mode (默认 mask,除非显式 READ)。

### M9. JWT 默认 lifetime 60 分钟太长 (`apps/django/config/settings/base.py:319`)

**问题**: 60 分钟 access + 7 天 refresh,被盗后窗口大。
**修复方案**: access 改 15 分钟,refresh 改 1 天。配合 `ROTATE_REFRESH_TOKENS=True` (已设)。

### M10. 没有 rate limit 测试 (`apps/django/apps/core/views_auth.py:14-25`)

**问题**: LoginRateThrottle (5/min) / RegisterRateThrottle (3/hour) / ChangePasswordRateThrottle (5/min) 都是装饰器,没单测验证真生效。
**风险**: 装饰器被误删没发现 → 撞库无限制。

---

## 🟢 低/建议 (P2 - 长期改进)

### L1. 无前端 CSP / SRI (`web/app/index.html`)

**建议**: 加 Content-Security-Policy meta + 静态资源 SRI hash。生产 nginx 层加更稳。

### L2. `request-dedup` 测试用了真后端 (`web/app/src/utils/__tests__/request-dedup.test.mjs`)

**建议**: 加 mock。

### L3. `console.warn` / `console.error` 多处使用 (`web/app/src/main.ts`)

**建议**: 生产 build 阶段自动 strip console (用 terser / esbuild `drop_console: true`)。

### L4. `django-fsm 2.8.1` 已废弃

迁移到 `viewflow.fsm` (官方 fork)。工作量: 1-2 周(9 个状态机重写 transition decorator)。

### L5. pytest fixture `_ensure_v2_schema_on_sqlite` 用 raw SQL (`apps/django/tests/conftest.py`)

**建议**: 改成 Django `RunSQL` migration 形式,让 test DB schema 可重放。

### L6. MIGRATION.md / PROJECT_PLAN.md 等文档严重过期

**已修**: 2026-08-03 复盘时已重写 ARCHITECTURE.md。**还需**: MIGRATION.md / PROJECT_PLAN.md / SETUP.md / TROUBLESHOOTING.md / technical.md / CHANGELOG.md 增量更新(本任务范围内)。

### L7. `secrets.token_urlsafe` 没用于 session / CSRF

**建议**: 加 SESSION_COOKIE_NAME 自定义 + CSRF 用 secrets 生成 token (Django 默认是 random,但 `SECRET_KEY` 变化会让所有 session 失效,符合预期)。

### L8. 没看到 load test / 性能基线

**建议**: 加 `locust` 压测,记录 P95 / P99 latency,作为后续优化 baseline。

### L9. `init.sh` / `create_tables_sql.py` 存在但功能跟 migrate 重复

**建议**: 删 create_tables_sql.py(误导新人),init.sh 保留并加注释 "Django migration 已替代"。

---

## 已完成的合规改进 (本轮)

| 改动 | 文件 | 状态 |
|---|---|---|
| admin token env 化 | `config/urls.py` | ✅ |
| stub 路由加 X-Stub + log 告警 | `apps/referral/urls_stubs.py` | ✅ |
| CI 切到 Django | `.github/workflows/ci.yml` | ✅ |
| 文档过期项更新 (ARCHITECTURE.md / config.json / Makefile) | `docs/` | ✅ |
| 7 个后端 + 3 个前端测试 fail 修 | `tests/` + `web/app/__tests__/` | ✅ |

## 待办 (P0/P1 backfill,需排期)

| ID | 严重度 | 工作量 | 负责人 |
|---|---|---|---|
| S2 | 🔴 | 0.5d | (未指派) |
| S3 | 🔴 | 1-2d | (未指派) |
| M1 stub 补全 | 🟡 | 5-10d | (未指派) |
| M2 异常处理 | 🟡 | 2d | (未指派) |
| M3 path traversal | 🟡 | 10min | (未指派) |
| M4 演示密码 | 🟡 | 10min | (未指派) |
| M5 启动探活 | 🟡 | 0.5d | (未指派) |
| M6 ready() 查 DB | 🟡 | 0.5d | (未指派) |
| M7 __str__ 脱敏 | 🟡 | 5min | (未指派) |
| M8 脱敏白名单 | 🟡 | 0.5d | (未指派) |
| M9 JWT lifetime | 🟡 | 5min | (未指派) |
| M10 rate limit 测试 | 🟡 | 0.5d | (未指派) |
