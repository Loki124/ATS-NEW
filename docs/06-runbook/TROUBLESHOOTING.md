# TROUBLESHOOTING — 常见问题排查

> **最后更新**: 2026-08-03 — Django 6.0 + DRF 3.15 + Vue 3 + Vite 5
> 按问题分类, 每个问题给"症状 → 原因 → 解法"三段式。

---

## 1. 安装/启动

### T-1.1: `pip install -r requirements.txt` 报版本冲突

**症状**: `ResolutionImpossible: for help visit ...` 或 `ERROR: pip's resolver ...`
**原因**: Python 解释器与 .venv 版本不一致, 或系统包(hermes / 全局 pip)污染。
**解法**:
```bash
# 1) 用完全独立的 venv
python3.14 -m venv /opt/ats-venv
source /opt/ats-venv/bin/activate
pip install --upgrade pip
pip install -r apps/django/requirements.txt

# 2) 仍冲突, 看哪个包在抢
pip install -r requirements.txt --dry-run 2>&1 | head -50
```

### T-1.2: `python manage.py migrate` 报 `Unknown database 'ats_db'`

**症状**: `django.db.utils.OperationalError: (1049, "Unknown database 'ats_db'")`
**原因**: MySQL 没建库 / DATABASE_URL 写错。
**解法**:
```bash
# 1) 登录 mysql 建库
mysql -u root -e "CREATE DATABASE IF NOT EXISTS ats_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
# 2) 验证 .env 里 DATABASE_URL
grep DATABASE_URL apps/django/.env
#    应该是: mysql://ats_user:ats_password@localhost:3306/ats_db
```

### T-1.3: `python manage.py runserver` 报 `No module named 'config'`

**症状**: `ModuleNotFoundError: No module named 'config'`
**原因**: cwd 不在 `apps/django/`, 或者 venv 没激活。
**解法**:
```bash
cd apps/django
source .venv/bin/activate
python manage.py runserver
```

### T-1.4: 前端 `npm install` 报 `EACCES` 权限错

**症状**: `EACCES: permission denied, mkdir '/usr/local/lib/node_modules/...'`
**原因**: 全局装包需要 sudo, 跟项目不匹配。
**解法**:
```bash
# 改 npm 全局 prefix 到用户目录
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.zshrc  # 或 ~/.bashrc
source ~/.zshrc
npm install  # 重新跑
```

### T-1.5: gunicorn 启动后 worker 立刻退出

**症状**: `Worker failed to boot.`, 日志里 `ModuleNotFoundError: No module named 'config'`
**原因**: gunicorn 找不到 `config` 包, 需在 `apps/django/` 目录里跑。
**解法**:
```bash
cd apps/django
.venv/bin/python -m gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2
# 不要在项目根或 web/app/ 里跑
```

---

## 2. 认证/JWT

### T-2.1: 登录返 401 `invalid_credentials`

**症状**: POST `/api/v1/auth/login/` 返 `{"success": false, "code": "invalid_credentials"}`
**原因**: 用户名/密码错, 或账号 `is_active=False`, 或 `deleted_at` 不为空。
**解法**:
```bash
# 查 DB 看用户状态
mysql -u ats_user -p ats_db -e "SELECT id, username, is_active, deleted_at FROM users WHERE username='admin';"
# 重置密码
cd apps/django
.venv/bin/python manage.py shell -c "
from apps.core.models import User
u = User.objects.get(username='admin')
u.set_password('admin123')
u.is_active = True
u.deleted_at = None
u.save()
print('reset ok')
"
```

### T-2.2: API 返 401 但 token 看起来对

**症状**: 带着 `Authorization: Bearer xxx` 但返 `{"detail": "Authentication credentials were not provided."}`
**原因**: `Authorization` 头格式错, 或 token 过期, 或用户被 disable。
**解法**:
```bash
# 1) 验证 header
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/candidates/ -v | head -20
# 2) token decode
.venv/bin/python -c "from rest_framework_simplejwt.tokens import AccessToken; t=AccessToken('<token>'); print(t.payload)"
# 3) 续 token
curl -X POST -H "Content-Type: application/json" -d '{"refresh": "<refresh>"}' \
  http://localhost:8000/api/v1/auth/refresh/
```

### T-2.3: 改密返 success 但实际没改

**症状**: POST `/api/v1/auth/change-password/` 返 `{success: true, message: '密码已更新 (stub)'}`
**原因**: **这是 stub 路由!** 2026-07-01 加的兜底, 没有真实现。
**解法**:
- response header 检查 `X-Stub: true`
- 后端 WARNING log: `STUB endpoint called: view=auth_change_password`
- 真要修, 在 `apps/core/views_auth.py` 加 `change_password_view`, 在 `apps/core/urls_auth.py` 替换 stub 路由

---

## 3. 业务 API

### T-3.1: 列表 API 返 200 但 data 是空数组

**症状**: GET `/api/v1/candidates/` 返 `{"success": true, "data": [], "pagination": {...}}`, 即使库里 100 条
**原因**: `ScopeQuerysetMixin` 过滤掉。L1/L2/L3 都没配 ALL scope, L4 兜底 SELF 只看自己创建的。
**解法**:
```python
# 1) 看 scope 解析
cd apps/django
.venv/bin/python manage.py shell -c "
from apps.core.models import User
from apps.core.scope_resolver import resolve_scope
u = User.objects.get(username='admin')
print(resolve_scope(u))
"
# 返 {'management_unit_ids': []} → L4 兜底

# 2) 给 user 配 ALL scope
.venv/bin/python manage.py shell -c "
from apps.core.models_permission_v2 import UserRoleV2
UserRoleV2.objects.update_or_create(
    user_id=1, system_code='recruit', role_code='SUPER_ADMIN',
    defaults={'management_unit_ids': [1]}  # 或者用 L2: 设 role.default_data_scope_type='ALL'
)
"
```

### T-3.2: API 返 403 forbidden

**症状**: GET `/api/v1/demands/` 返 403
**原因**: V2 权限检查失败。三种可能:
1. 没 V2 role (UserRoleV2 表空)
2. V2 role 有但 role_permission 表没 resource_code 授权
3. 测试 DB 上 V2 schema 缺列 (`user_roles.role_code` 不存在)
**解法**:
```bash
# 1) 看后端日志, 找具体原因
tail -100 /tmp/ats-logs/backend.log | grep -E "Forbidden|OperationalError|role_code"

# 2) 查 V2 角色 + 权限
mysql -u ats_user -p ats_db -e "
SELECT u.username, ur.role_code, ur.system_code
FROM user_roles ur JOIN users u ON u.id = ur.user_id
WHERE u.username='admin';

SELECT * FROM role_permission WHERE role_code='SUPER_ADMIN' LIMIT 10;
"

# 3) 缺授权, INSERT
mysql -u ats_user -p ats_db -e "
INSERT INTO role_permission (role_code, resource_code, system_code, created_at)
VALUES ('SUPER_ADMIN', 'recruit:demand:list', 'recruit', NOW());
"
```

### T-3.3: POST 创建返 400 字段错

**症状**: `{"name": ["This field is required."]}` 但前端明明传了
**原因**: snake_case ↔ camelCase 转换。`djangorestframework-camel-case` 自动转, 但**单词字段**(id/username/access/refresh)不转。
**解法**:
- 看 serializer `fields` 列表, 确认字段名
- 看 DRF browsable API 的 raw payload 验证
- 前端 axios 拦截器不要手动加 `Content-Type: application/json`, 让 axios 自动判断

### T-3.4: API 返 `{success: true, data: {id: "stub-xxx-..."}}`

**症状**: POST 看似成功, 但数据库里没数据
**原因**: **stub 路由**返 fake 数据, 没真写入。
**解法**:
- response header 必有 `X-Stub: true`
- 后端 WARNING log: `STUB endpoint called: view=...`
- 当前 stub 列表 (2026-08-03):
  - `auth/register`, `auth/change-password`
  - `candidates/batch/{recommend,archive,assign,export,screen}`
  - `recruitment-process/stage-rules`, `auto-archive-rules`
  - `recruitment-rounds`, `bulk-create`, `upload-and-parse`
  - `scoring/start`, `scoring/{evaluate,start}`
  - `offer-templates`, `permissions-v2/{roles,functions,...}` (5 个)
  - 等等, 20+ 个
- **临时绕过**: 业务侧自己用 `apps/<domain>/views.py` 真 API 调
- **永久 fix**: 把 stub 实现补到对应 app, 在 `apps/referral/urls_stubs.py` 删 stub 路由

---

## 4. 前端 / 浏览器

### T-4.1: 登录页 401 但后端返 200

**症状**: 浏览器 network 看 login 返 200, 但前端跳回登录页
**原因**: JWT 没存, 或 token 拦截器没带 header。
**解法**:
```typescript
// web/app/src/api/auth.ts 应该有:
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
```

### T-4.2: 前端页面白屏 / Naive UI 报 "Cannot access 'ma' before initialization"

**症状**: 浏览器 console 报 TDZ 错, 页面空
**原因**: `vendor-naive-ui` chunk 被错误拆分, naive-ui 2.x 生态必须在同一 chunk。
**解法**:
- 看 `web/app/vite.config.ts` 的 `manualChunks` 块, 确认 `vendor-naive-ui` 包含 naive-ui 全部间接依赖
- CI 有断言: `vendor-misc` 超过 100KB 会 fail
- 临时绕过: `npm run build:nocheck` (跳过 type check) 然后 `collectstatic` 部署

### T-4.3: 路由守卫说 "requiresAuth" 但 token 还在

**症状**: 刷新页面后跳回 /login
**原因**: `vue-router 4` 不会自动继承父路由的 meta 到子路由, `to.meta.requiresAuth` 永远 undefined
**解法** (已修, 2026-06-29): 用 `to.matched.some(r => r.meta?.requiresAuth)` 检查整条匹配链
```typescript
// web/app/src/router/index.ts:182
const requiresAuth = to.matched.some((r: any) => r.meta?.requiresAuth)
```

### T-4.4: Vite dev 跨域 CORS 错

**症状**: `Access to XMLHttpRequest at 'http://localhost:8000/...' from origin 'http://localhost:5212' has been blocked by CORS`
**原因**: vite proxy 没配, 或者后端 CORS_ALLOWED_ORIGINS 没含 5212
**解法**:
```typescript
// web/app/vite.config.ts proxy
proxy: {
  '/api': { target: 'http://localhost:8000', changeOrigin: true }
}
// 后端 .env
CORS_ALLOWED_ORIGINS=http://localhost:5212,http://127.0.0.1:5212
```

---

## 5. 测试

### T-5.1: pytest 报 `no such column: user_roles.role_code`

**症状**: V2 业务代码 (permission_check / role_v2_query) 查 `user_roles.role_code` 列不存在
**原因**: sqlite 测试 DB 是 V1 schema, conftest 应补 V2 列
**解法**:
- 验证 conftest.py 的 `_ensure_v2_schema_on_sqlite` 跑过 (stdout 应有 `[conftest] seeded N role_permission rows`)
- 如果 schema 改了, 同步更新 conftest 里的 `v2_roles_cols` / `v2_ur_cols` 字典

### T-5.2: pytest 报 `NOT NULL constraint failed: roles.id` / `roles.role_name` / `user_roles.role_id`

**症状**: V2 fixtures (RoleV2 / UserRoleV2) 走 model save() 但表是 V1 schema
**原因**: V1 表 PK 是 VARCHAR(32), V2 model 期望 BigAuto, NOT NULL 字段不一致
**解法**:
- conftest 必须用 raw SQL fixture (`_create_role_v2` / `_raw_attach_v2_role`)
- 不要在测试里直接 `RoleV2.objects.create()`, 用 `_create_role_v2('HR', 'HR')`

### T-5.3: vitest 报 `localStorage.getItem is not a function`

**症状**: router guard 测试 fail
**原因**: happy-dom 测试环境没 localStorage
**解法** (已修, 2026-08-03): 在 test setup 加 stub
```typescript
;(globalThis as any).localStorage = {
  _data: {} as Record<string, string>,
  getItem(k: string) { return this._data[k] ?? null },
  setItem(k: string, v: string) { this._data[k] = v },
  removeItem(k: string) { delete this._data[k] },
  clear() { this._data = {} },
  key(i: number) { return Object.keys(this._data)[i] ?? null },
  get length() { return Object.keys(this._data).length },
}
```

### T-5.4: vitest 报 "expected to be called with arguments"

**症状**: `expect.objectContaining` 不 match
**原因**: spy 实际有 N 个 args, 测试只 expect 1 个
**解法**:
```typescript
// 错
expect(mock).toHaveBeenCalledWith(expect.objectContaining({ q: '张' }))
// 对
expect(mock).toHaveBeenCalledWith(
  expect.objectContaining({ q: '张' }),
  expect.anything(),  // signal 等其他 args
)
```

---

## 6. 部署/生产

### T-6.1: 生产 `ImproperlyConfigured: DJANGO_SECRET_KEY 仍是默认值`

**症状**: 启动报 `ImproperlyConfigured`, 立刻退出
**原因**: `_validate_production_config()` 强校验, 不允许默认值
**解法**:
```bash
# 生成新 key
python -c "import secrets; print(secrets.token_urlsafe(64))"
# 设到生产 .env
DJANGO_SECRET_KEY=<上面输出的串>
```

### T-6.2: 生产 `CACHES` 报 Redis 不可用

**症状**: `生产环境 Redis 不可用 (...). 不允许 LocMemCache 静默 fallback`
**原因**: prod settings 启动期 socket 探活, Redis 不通直接 fail
**解法**:
- 启动 Redis: `systemctl start redis` / `brew services start redis`
- 验证: `redis-cli ping` 应返 `PONG`
- 临时绕过: 改 dev settings (但生产禁止)

### T-6.3: gunicorn worker timeout

**症状**: `[CRITICAL] WORKER TIMEOUT (pid:1234)`
**原因**: 单个请求超过 30s, 默认 gunicorn timeout
**解法**:
```bash
# 临时: 调 timeout
gunicorn --timeout 120 ...
# 永久: 看哪个 API 慢, 优化或加 celery 异步化
```

### T-6.4: Cloudflare Tunnel 配置丢失

**症状**: 域名访问 502 / 504
**原因**: CF Tunnel 路由是 dashboard API-managed, `/etc/cloudflared/config.yml` 是过期 snapshot
**解法**:
- 登录 Cloudflare Zero Trust Dashboard
- 找到 ats.lokisong.cloud 的 tunnel 配置
- 确认指向 `127.0.0.1:8000`
- 不要改 `/etc/cloudflared/config.yml`, 那是历史文件

---

## 7. 调试技巧

### 看后端日志
```bash
# 实时
tail -f /tmp/ats-logs/backend.log
# 找最近 ERROR
grep -E "ERROR|CRITICAL" /tmp/ats-logs/backend.log | tail -20
```

### 看前端日志
```bash
tail -f /tmp/ats-logs/frontend.log
# 浏览器 console 也看
```

### 进 Django shell
```bash
cd apps/django
.venv/bin/python manage.py shell
# 试错
>>> from apps.candidate.models import Candidate
>>> Candidate.objects.filter(deleted_at__isnull=True).count()
```

### 进 Django admin (生产)
```bash
# 默认 token (生产必须改)
open http://localhost:8000/ops-dashboard-7f3b9c2e/login/
# 自定义 token (推荐)
ADMIN_URL_TOKEN=<你的随机串> python -m gunicorn ...
```

### 跑单独一个测试
```bash
# 后端
cd apps/django
.venv/bin/pytest tests/test_demand.py::TestDemandAPI::test_list_demands -v

# 前端
cd web/app
npx vitest run src/router/__tests__/router.test.ts
```

---

## 8. 仍然有疑问?

1. 看 `RUNBOOK.md` 5 分钟跑通指南
2. 看 `docs/02-architecture/technical.md` 整体架构
3. 看 `docs/CHANGELOG.md` 最近改了什么
4. 看 `docs/COMPLIANCE_AUDIT_2026-08-03.md` 已知问题 + 修复优先级
5. 看后端 logs + 浏览器 console
