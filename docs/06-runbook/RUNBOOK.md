# ATS-NEW 项目跑通指南 (RUNBOOK)

> **最后更新**: 2026-08-04 @ HEAD `010e4d4`（T01.1 落地后）
> **给 PM / 新同学**: 5 分钟从 0 跑通整个项目, 看到登录页 + 业务列表
> **紧急回滚**: 见 §6（覆盖 R1 migration / BUG 系列 / R11 CI 失败场景）

---

## 0. 一次性环境准备

需要本地装:

- **Python 3.14+**（项目 `.venv` 是 3.14.6）
- **Node.js 20+** + npm（项目用 `package-lock.json`，**不要再用 pnpm**）
- **MySQL 8**（生产一致）或 **SQLite**（dev/test 兜底）
- **Redis 7**（限流 + Celery + Channels）

```bash
# macOS
brew install python@3.14 node mysql@8 redis
```

---

## 1. 跑后端（5 分钟）

```bash
cd apps/django

# 1. 激活 venv（项目已就绪）
source .venv/bin/activate

# 2. 装依赖（首次）
pip install -r requirements.txt

# 3. 配 .env
cp .env.example .env
# 编辑 .env:
#   DATABASE_URL=sqlite:///db.sqlite3   (开发用 sqlite, 生产用 mysql)
#   DJANGO_SECRET_KEY=<50+ 字符随机串>  (生产必须)
#   DJANGO_DEBUG=True
#   REDIS_URL=redis://localhost:6379/0 (本地有 redis 起就 OK, 未起会 LocMemCache fallback)
#   CORS_ALLOWED_ORIGINS=http://localhost:5212

# 4. 迁移 + 种子
python manage.py migrate
python manage.py loaddata seeds/07_demo_user.json   # 可选, 创建 admin/admin123

# 5. 起服务
python -m gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2
# 或开发模式: python manage.py runserver 0.0.0.0:8000
```

打开 http://localhost:8000/ 应该看到 Vue SPA 首页（需要前端也起）。

**API 验证**（路径修正确，之前 `/api/v1/health/` 404 的 bug 已报 ✅）：

- ✅ http://localhost:8000/health/ → `{"status":"ok"}`（**正确路径**，`config/urls.py:125`）
- ✅ http://localhost:8000/api/docs/ → Swagger UI（看 60+ 端点）
- ✅ http://localhost:8000/${ADMIN_URL_TOKEN}/ → Django admin（env 化 token）

---

## 2. 跑前端（3 分钟）

```bash
cd web/app
npm install
npm run dev              # → http://localhost:5212
```

打开 http://localhost:5212 看到登录页：

- 默认测试账号（跑过 `loaddata` 才有）：`admin / admin123`
- 或自己注册：`POST /api/v1/auth/register/`（⚠️ 2026-08-04 现状：返 501，企业内 ATS 不开放自助注册，账号由 admin 后台创建）

---

## 3. 跑测试（1 分钟）

```bash
# 后端全量 (2026-10-08: 隔离区已代码内化, 用 -m "not quarantine" 排除, 详见 08-测试体系.md §2.4)
cd apps/django
source .venv/bin/activate
pytest --tb=line -q --no-header -p no:cacheprovider -m "not quarantine" --cov=apps --cov-fail-under=70

# 前端 (带覆盖率门禁)
cd web/app
npm test -- --coverage
```

**预期**：全量通过且覆盖率不低于门禁（后端 70 / 前端见 vitest thresholds）。隔离区为空（9 条 deselect 已于 2026-10-01 实测全部 PASS 并随 `apps/*/tests/` 全量收集进入正式回归）。

---

## 4. 故障排查（FAQ）

### Q: `/api/v1/health/` 返 404

A: ✅ **已修复**（2026-08-04 文档同步）。真实路径 `/health/`（`config/urls.py:125`）。`Makefile:47` 的 `curl /api/v1/health/` 也需修。

### Q: `pytest` 跑出 FK constraint / no such column 错

A: V2 schema 缺失。T01.1 (`010e4d4`) 已把 `roles` (11 列) + `user_roles` (10 列) 真实建表，**无需再补**。如果跑出新错，看 `tests/conftest.py` 的 `_ensure_v2_schema_on_sqlite()` 内部字典。

### Q: 某个 API 返 403 forbidden

A: 大概率 V2 权限检查失败。

- 检查后端日志：`no such column: user_roles.role_code` → V2 schema 缺失（**T01.1 已修**）
- 检查 fixture 是否设了 role（V2 fixture 用 raw SQL `_create_role_v2` / `_raw_attach_v2_role`）
- 检查 `role_permission` 表是否有该 `resource_code` 行

### Q: 某个 API 返 200 但 data 是空数组

A: `ScopeQuerysetMixin` 过滤掉了。

- L1: `user_role.management_unit_ids` 非空 → 用
- L2: `role.default_data_scope_type='ALL'` → 全放
- L3: `tenant_config.GLOBAL_DEFAULT_DATA_SCOPE='ALL'` → 全放
- L4: 兜底 SELF → `qs.filter(created_by=user)`

**R8 已修复**（`af5e4a2`）：DEPT scope 之前会折空返 SELF，现在正确爬子树。

### Q: 前端 vitest 报 `localStorage.getItem is not a function`

A: happy-dom 测试环境没 localStorage，在 test setup 加 stub（看 `src/router/__tests__/router.test.ts` 的 `_localStorageStub`）。

### Q: 调 API 拿到 `{success: true, data: {id: "stub-xxx-xxxx"}}`

A: 命中 stub 路由。`apps/referral/urls_stubs.py` 仍有 37 个兜底端点。

- **R5 已修**（`e624105`）：`auth/register` 和 `auth/change-password` 现返 501
- 但 `candidates/batch/recommend` 等仍返回 STATIC 假数据，生产前必须补
- 详见 `docs/PHASE2_DESIGN_2026-08-03.md` §2.9 决策矩阵

### Q: 前端 5212 端口被占

A: 改 `web/app/src/config/index.ts` 的 `frontend.port` 或 `vite.config.ts` 的 `server.port`。

### Q: 后端 8000 端口被占

A: 改启动命令 `--bind` 参数或 `web/app/src/config/index.ts` 的 `backend.port`。

### Q: Dockerfile HEALTHCHECK 启动期报错

A: ✅ **已修复**（`7aa6608`）。修复前语法错误，未设置 `--start-period`，容器启动期即判 unhealthy。

### Q: Channels 4.3 + daphne 4.2 连不上

A: 检查 `CHANNEL_LAYERS` 配置在 `config/settings/base.py`，Redis 不可达 → LocMemChannelLayer 兜底但仅单进程。

### Q: Celery 5.6 task 提交成功但不执行

A: beat 未启。`ats-celery-beat.service` 必须**同时**与 `ats-celery.service` 起，否则 cron 任务不会触发。

### Q: django-fsm 3.0 transition 抛 `TransitionNotAllowed`

A: ✅ **BUG-5 已修**（`f970bf8`）：候选人 FSM 5 个 transition 补齐，由 `FSMModelMixin` 统一 source 校验。如仍报，看 `apps/candidate/models.py` `@transition` 装饰器的 `source` 列表。

---

## 5. 关键文件位置

| 关注点 | 文件 |
|---|---|
| Django 路由总入口 | `apps/django/config/urls.py` |
| 健康检查路径 | `apps/django/config/urls.py:125`（`/health/`）|
| V2 权限检查 | `apps/django/apps/core/permission_check.py` |
| V2 scope resolver | `apps/django/apps/core/scope_resolver.py` |
| 字段脱敏 | `apps/django/apps/field_acl/services.py`（R2 接入 f4b65ab） |
| Stub 路由 | `apps/django/apps/referral/urls_stubs.py`（37 端点） |
| 状态机（7 FSMField） | `apps/django/apps/*/models.py` (`@transition`) |
| T01.1 V2 schema 建表 | `apps/django/apps/core/migrations/0004_v2_apply_schema.py` |
| 前端路由 + RBAC | `web/app/src/router/index.ts` |
| 前端 API 客户端 | `web/app/src/api/*.ts`（27 个） |
| 测试 fixtures | `apps/django/tests/fixtures_common.py`（V1/V2 双路径） |
| CI 配置 | `.github/workflows/ci.yml` |
| 架构审计 | `docs/09-archive/ARCHITECTURE_REVIEW_2026-08-03.md` |
| Phase 2 设计 | `docs/PHASE2_DESIGN_2026-08-03.md` |

---

## 6. 紧急回滚（按场景）

### 6.1 R1 migration 崩溃（`apps/django/apps/candidate/migrations/0004` 缺 `import models`）

✅ **已修复**（`443550d`）：补 `from django.db import models`。回滚路径：

```bash
# 验证：python manage.py migrate --plan 应无错
# 如回滚需重做: git revert 443550d 后人工补 import，再 migrate
```

### 6.2 BUG 系列回滚

| Bug | 现象 | 修复 commit | 回滚命令 |
|---|---|---|---|
| BUG-1 | 身份证查重永久失效 | `f8708c9` | `git revert f8708c9` |
| BUG-2 | 7 处 view 缺 request context | `eae19c3` | `git revert eae19c3` |
| BUG-3/4 | operator 字段 + id_card_no None | `1e1ed1e` | `git revert 1e1ed1e` |
| BUG-5 | FSM 5 transition 缺失 | `f970bf8` | `git revert f970bf8` |
| BUG-6 | 信号审计需显式 | `8213f78` | `git revert 8213f78` |
| BUG-7 | 迁移 0005 变量遮蔽 | `c60b65f` | `git revert c60b65f`（会回退 hash 修复） |

### 6.3 R11 CI 门禁松绑（如需临时松绑）

`9475c6a` 把 lint / trivy / type-check 全部从 `|| true` 改回真阻断。如 CI 阻断影响发版但已知无关：

```bash
# 临时方案 (不推荐):
git revert 9475c6a
# 然后立即 cherry-pick 回来，CI 红是质量信号，应修而非绕
```

### 6.4 生产根本起不来

```bash
# 1. 看 systemd 状态
systemctl status ats-django.service ats-celery.service ats-celery-beat.service

# 2. 看日志
journalctl -u ats-django.service -n 200 --no-pager

# 3. 常见原因
#    - DJANGO_SETTINGS_MODULE 设错: 必须 config.settings.prod
#    - REDIS_URL 不可达: prod.py:86-97 启动时 TCP 探测
#    - INTEGRATION_FERNET_KEY 未设: 返 RuntimeError
#    - SECRET_KEY < 50 字符: prod.py:27 强校验

# 4. 紧急回滚到上一稳定点
git checkout <last-green-sha>  # 重建 venv, 重 migrate
```

---

## 7. 跟生产一致的部署路径

- **生产 systemd**: `ats-django.service` (gunicorn 4w) + `ats-celery.service` + `ats-celery-beat.service`
- **HTTPS**: Cloudflare Tunnel (`ats.lokisong.cloud` → `127.0.0.1:8000`)
- **生产数据库**: MySQL 8 (强依赖, dev/test SQLite 兜底)
- **生产缓存**: Redis 7 (Celery broker + Channels layer + 限流, 强依赖)
- **Docker Compose**: 部署编排（docker-compose / Dockerfile / nginx.conf / webhook 接收器 / systemd unit）已迁移到独立仓库 **[ats-deploy-infra](https://gitee.com/loki126/ats-deploy-infra.git)**，本仓库不再跟踪 `ops/`。生产栈的 R4 修复（mysql+redis+backend，0720247）现位于该仓库 `compose/docker-compose.yml`。

---

## 8. 跑通后的下一步

1. **看业务**: `http://localhost:5212/dashboard` → 工作台
2. **走流程**: 创建需求 → 发布职位 → 推荐候选人 → 筛选 → 面试 → Offer → 待入职
3. **看 stub**: 批量导入 / 智能分配 / RPA 抓取 / 数据导出 — **R5 修后部分返 501**，详情 `docs/PHASE2_DESIGN_2026-08-03.md` §2.9
4. **看权限**: 切不同 role 账号（admin / HR / HRBP）看菜单和按钮差异
5. **看 Phase 2**: `docs/PHASE2_DESIGN_2026-08-03.md` — T01.1 ✅ 已落地，余下 T01.2+ 进行中

---

*文档版本: V2.0 (2026-08-04 许清楚 overhaul, 修复路径/测试数 + 加紧急回滚段)*
