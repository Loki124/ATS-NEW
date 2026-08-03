# ATS 项目跑通指南 (RUNBOOK)

> **给产品经理 / 新同学**: 5 分钟从 0 跑通整个项目,看到登录页 + 业务列表。
> 写于 2026-08-03,基于 Django 6.0 + DRF 3.15 + Vue 3 实际状态。

---

## 0. 一次性环境准备

需要本地装:
- **Python 3.14+** (项目用 3.14, .venv 已就绪)
- **Node.js 20+** + pnpm (或 npm)
- **可选**: MySQL 8 (生产一致, 否则用 SQLite 兜底)

```bash
# macOS
brew install python@3.14 node mysql@8 redis
```

---

## 1. 跑后端 (5 分钟)

```bash
cd apps/django

# 1. 激活 venv (项目根已经创建好了)
source .venv/bin/activate

# 2. 装依赖 (首次)
pip install -r requirements.txt
pip install pytest pytest-django pytest-cov  # 测试用

# 3. 配 .env
cp .env.example .env
# 编辑 .env:
#   DATABASE_URL=sqlite:///db.sqlite3   (开发用 sqlite, 生产用 mysql)
#   DJANGO_SECRET_KEY=<随便一个长串>    (生产必须 50+ 字符)
#   DJANGO_DEBUG=True
#   REDIS_URL=redis://localhost:6379/0 (本地有 redis 起就 OK, 没起会 fallback LocMemCache)
#   CORS_ALLOWED_ORIGINS=http://localhost:5212

# 4. 迁移 + 种子
python manage.py migrate
python manage.py loaddata seeds/07_demo_user.json   # 可选, 创建 admin/admin123

# 5. 起服务
python -m gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2
# 或者开发模式: python manage.py runserver 0.0.0.0:8000
```

打开 http://localhost:8000/ 应该看到 Vue SPA 首页 (需要前端也起)。

API 测试:
- http://localhost:8000/api/v1/health/ → `{"status":"ok"}`
- http://localhost:8000/api/docs/ → Swagger UI (看 60+ 端点)
- http://localhost:8000/admin/ (或 `/${ADMIN_URL_TOKEN}/`) → Django admin

---

## 2. 跑前端 (3 分钟)

```bash
cd web/app
npm install              # 或 pnpm install
npm run dev              # → http://localhost:5212
```

打开 http://localhost:5212 看到登录页:
- 默认测试账号 (跑过 `loaddata` 才有): `admin / admin123`
- 或者自己注册: `/api/v1/auth/register/` (目前是 stub,生产前会真补)

---

## 3. 跑测试 (1 分钟)

```bash
# 后端 39 tests
cd apps/django
source .venv/bin/activate
pytest tests/ -v

# 前端 132 tests
cd web/app
npm test
```

预期全过。如果有 fail,看下面"故障排查"。

---

## 4. 故障排查 (FAQ)

### Q: pytest 跑出 FK constraint / no such column 错

A: conftest.py 的 `_ensure_v2_schema_on_sqlite` 必须在 sqlite 上给 `user_roles` / `roles` 表补 V2 列。
如果改了 model,需要把新列加进 `_ensure_v2_schema_on_sqlite()` 里的 `v2_roles_cols` / `v2_ur_cols` 字典。

### Q: 某个 API 返 403 forbidden

A: 大概率 V2 权限检查失败。
- 检查后端日志: `no such column: user_roles.role_code` → V2 schema 缺失
- 检查 fixture 是否设了 role (V2 fixture 用 raw SQL `_create_role_v2` / `_raw_attach_v2_role`)
- 检查 `role_permission` 表是否有该 `resource_code` 行 (V2 `has_perm` 查这个表)

### Q: 某个 API 返 200 但 data 是空数组

A: 大概率 `ScopeQuerysetMixin` 过滤掉了。
- L1: `user_role.management_unit_ids` 非空 → 用
- L2: `role.default_data_scope_type='ALL'` → 全放
- L3: `tenant_config.GLOBAL_DEFAULT_DATA_SCOPE='ALL'` → 全放
- L4: 兜底 SELF → `qs.filter(created_by=user)`, 创的人不是自己就空

测试 fixtures 用 L2 (`_create_role_v2` 设 `default_data_scope_type='ALL'`)。

### Q: 前端 vitest 报 `localStorage.getItem is not a function`

A: happy-dom 测试环境没 localStorage,需要在 test setup 加 stub (看 `src/router/__tests__/router.test.ts` 里的 `_localStorageStub`)。

### Q: 调某个 API 拿到 `{success:true, data:{id: "stub-xxx-xxxx", ...}}`

A: 命中了 stub 路由!`apps/referral/urls_stubs.py` 有 20+ 兜底端点。
- response header 有 `X-Stub: true`
- 后端 WARNING log: `STUB endpoint called: view=...`
- 这些端点 FE 调用了但 BE 没真实现,生产前必须补

### Q: 前端 5212 端口被占

A: 改 `web/app/src/config/index.ts` 的 `frontend.port`, 或 `vite.config.ts` 的 `server.port`。

### Q: 后端 8000 端口被占

A: 改 `web/app/src/config/index.ts` 的 `backend.port` (要跟 `apps/django/config/settings/base.py` 启动时 `--bind` 一致)。

---

## 5. 关键文件位置速查

| 关注点 | 文件 |
|---|---|
| Django 路由总入口 | `apps/django/config/urls.py` |
| V2 权限检查 | `apps/django/apps/core/permission_check.py` |
| 字段脱敏 | `apps/django/apps/field_acl/services.py` |
| Stub 路由 | `apps/django/apps/referral/urls_stubs.py` |
| 状态机 (9 个) | `apps/django/apps/*/models.py` (`@fsm_field` 装饰器) |
| 前端路由 + RBAC | `web/app/src/router/index.ts` |
| 前端 API 客户端 | `web/app/src/api/*.ts` (27 个) |
| 测试 fixtures | `apps/django/tests/conftest.py` |
| CI 配置 | `.github/workflows/ci.yml` |
| 当前 changelog | `docs/CHANGELOG.md` |
| 架构图 | `docs/ARCHITECTURE.md` |

---

## 6. 跟生产一致的部署路径

- **生产 systemd**: `ats-django.service` (gunicorn 4w) + `ats-celery.service` + `ats-celery-beat.service`
- **HTTPS**: Cloudflare Tunnel (`ats.lokisong.cloud` → `127.0.0.1:8000`)
- **生产数据库**: MySQL 8 (生产 .env 必设 `DATABASE_URL=mysql://...`, dev/test 用 sqlite)
- **生产缓存**: Redis 7 (生产强依赖, dev 没起会 LocMemCache fallback)

---

## 7. 跑通后的下一步

1. **看业务**: `http://localhost:5212/dashboard` → 看工作台
2. **走流程**: 创建需求 → 发布职位 → 推荐候选人 → 筛选 → 面试 → Offer → 待入职
3. **看 stub**: 试试批量导入 / 智能分配 / RPA 抓取 / 数据导出 — 这些都是 stub, 假数据
4. **看权限**: 切不同 role 账号 (admin / HR / HRBP) 看菜单和按钮差异
5. **看代码**: `docs/CHANGELOG.md` 看最近 1 个月做了啥, `docs/ARCHITECTURE.md` 看全局架构
