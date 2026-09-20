# SETUP — 详细安装步骤

> **最后更新**: 2026-08-03 — Django 6.0 + DRF 3.15 + Python 3.14 + Vue 3 + Vite 5
> 本文假定 macOS + homebrew。其他系统类推。

## 🚀 快速启动 (5 步)

```bash
# 0. 一次性环境
brew install python@3.14 node mysql@8 redis
brew services start mysql
brew services start redis

# 1. 数据库 (MySQL 方式, 推荐贴近生产)
mysql -u root -e "CREATE DATABASE IF NOT EXISTS ats_db CHARACTER SET utf8mb4;"
mysql -u root -e "CREATE USER 'ats_user'@'localhost' IDENTIFIED BY 'ats_password';"
mysql -u root -e "GRANT ALL ON ats_db.* TO 'ats_user'@'localhost';"

# 1b. 数据库 (SQLite 方式, 5 分钟跑通)
#   跳过 mysql 步骤, 在 .env 设 DATABASE_URL=sqlite:///db.sqlite3

# 2. 后端
cd apps/django
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-django pytest-cov   # 测试
cp .env.example .env
# 编辑 .env:
#   DATABASE_URL=mysql://ats_user:ats_password@localhost:3306/ats_db
#   DJANGO_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
#   DJANGO_DEBUG=True
#   REDIS_URL=redis://localhost:6379/0
#   CORS_ALLOWED_ORIGINS=http://localhost:5212

python manage.py migrate
python manage.py collectstatic --noinput       # whitenoise 静态资源
python manage.py loaddata seeds/07_demo_user.json  # admin / admin123 (可选)

# 3. 启动 (任选一)
#    a) gunicorn (贴近生产)
python -m gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2
#    b) runserver (开发热重载)
python manage.py runserver 0.0.0.0:8000

# 4. 前端 (另一个 terminal)
cd ../../web/app
npm install
npm run dev                 # → http://localhost:5212

# 5. 浏览器
open http://localhost:5212/
# 登录: admin / admin123 (如果跑过 loaddata)
```

**验证清单**:
- [ ] `http://localhost:8000/health/` 返 `{"status":"ok"}`
- [ ] `http://localhost:8000/api/docs/` 看到 Swagger UI
- [ ] `http://localhost:5212/` 看到登录页
- [ ] `http://localhost:8000/ops-dashboard-7f3b9c2e/login/` (默认 token, 生产必须改)

---

## 📁 关键路径

| 用途 | 路径 |
|---|---|
| 后端项目根 | `apps/django/` |
| Django 设置 | `apps/django/config/settings/{base,dev,prod,test}.py` |
| 业务 app | `apps/django/apps/{candidate,demand,offer,...}/` |
| 迁移 | `apps/django/apps/*/migrations/` |
| 种子数据 | `apps/django/seeds/*.json` |
| pytest fixtures | `apps/django/tests/conftest.py` |
| 前端项目根 | `web/app/` |
| API 客户端 | `web/app/src/api/*.ts` |
| 路由 + RBAC | `web/app/src/router/index.ts` |
| 全局配置 | `web/app/src/config/index.ts` |
| 文档 | `docs/` |
| 跑通指南 | `RUNBOOK.md` |

---

## 🛠 配置 .env 详解

```bash
# === Django ===
DJANGO_SETTINGS_MODULE=config.settings          # dev 模式, prod 改 config.settings.prod
DJANGO_SECRET_KEY=<50+ 字符随机串>              # 生产必填, dev 有 default
DJANGO_DEBUG=True                                # 生产必 False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1        # 生产列明确域名

# === Database ===
# 选项 1: MySQL (生产)
DATABASE_URL=mysql://ats_user:ats_password@localhost:3306/ats_db
# 选项 2: PostgreSQL
DATABASE_URL=postgres://ats_user:ats_password@localhost:5432/ats_db
# 选项 3: SQLite (dev / test)
DATABASE_URL=sqlite:///db.sqlite3

# === Redis (Celery broker + cache + Channels) ===
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# === JWT ===
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# === CORS (跨域, dev 必须含前端 5212) ===
CORS_ALLOWED_ORIGINS=http://localhost:5212,http://127.0.0.1:5212

# === Admin URL (2026-08-03 改成 env) ===
ADMIN_URL_TOKEN=<random 24+ 字符>               # 生产必填, dev 默认 'ops-dashboard-7f3b9c2e'

# === 限流 ===
RATELIMIT_ENABLE=True

# === 集成 (可选) ===
WECOM_CORPID=...  WECOM_CORPSECRET=...  WECOM_AGENTID=...
SMS_PROVIDER=mock  SMS_API_KEY=...
MOKA_API_URL=...  MOKA_API_KEY=...
AFFINDA_API_KEY=test_affinda_key_dev             # 简历解析, dev 默认

# === 监控 (可选) ===
SENTRY_DSN=
PROMETHEUS_ENABLED=False

# === 日志 ===
LOG_LEVEL=INFO                                    # DEBUG / INFO / WARNING / ERROR

# === Fernet 加密 (IntegrationConfig 凭据加密) ===
INTEGRATION_FERNET_KEY=<32-byte base64, 用 python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 生成>
```

---

## 🐳 Docker Compose 方式 (贴近生产)

```bash
cd ops
cp .env.example .env
# 编辑 .env (MYSQL_ROOT_PASSWORD / MYSQL_PASSWORD / JWT_SECRET / INTEGRATION_FERNET_KEY 等)

docker compose up -d
# 验证:
curl http://localhost:9908/health/
# 浏览器:
open http://localhost:9908/
```

**注意**:
- nginx 暴露 host `:9908` 端口 (容器内 80)
- backend 容器内 5125, 仅 docker 网络可达
- mysql 容器内 3306, 仅 docker 网络可达

---

## 🧪 跑测试

```bash
# 后端 (39 个 pytest)
cd apps/django
source .venv/bin/activate
pytest tests/ -v

# 前端 (132 个 vitest)
cd web/app
npm test
```

**测试通过标准**:
- 后端: 39 passed, 0 failed
- 前端: 132 passed, 0 failed
- 详见 `RUNBOOK.md` §3

---

## 📋 附录:其他系统

### Ubuntu / Debian

```bash
sudo apt install python3.14 python3.14-venv mysql-server redis-server nodejs npm
sudo systemctl start mysql
sudo systemctl start redis-server
```

### Windows (WSL2 推荐)

```bash
# 在 WSL2 Ubuntu 里跑, 跟 macOS 一样
```

### CentOS / RHEL

```bash
sudo dnf install python3.14 mysql-server redis nodejs
sudo systemctl start mysqld
sudo systemctl start redis
```

---

## ⚠️ 常见安装问题

### Q: pip install 报 `cryptography 49.0.0` vs `msal<49` 冲突

A: 跟 hermes 解释器共享 site-packages 引起, ATS 不直接用 msal。两个解决方案:
1. 给 ATS 完全独立 venv (推荐): `python3.14 -m venv /opt/ats-venv`
2. 等 hermes 升 msal 1.37+

详见 `apps/django/requirements.txt` 顶部 long comment。

### Q: macOS 上 `brew install python@3.14` 找不到

A: 改用 `brew install python@3.12` 或 pyenv。Python 3.11+ 都能跑,只是 .venv 是 3.14。

### Q: MySQL `utf8mb4` 中文乱码

A: 确保 `DATABASES['default']['OPTIONS']['charset'] = 'utf8mb4'` (base.py 已设), 且 `LANGUAGE_CODE = 'zh-hans'` + `TIME_ZONE = 'Asia/Shanghai'`。

### Q: Redis 起不来

A: 生产必须, dev 没起会 fallback LocMemCache。`brew services start redis` 或 `redis-server --daemonize yes`。

### Q: 前端 `npm install` 慢

A: 切到国内镜像: `npm config set registry https://registry.npmmirror.com`

---

## §3. 三关门禁（必跑，2026-09-20 收口）

每次业务代码改动后必跑以下三关，全过方可提交：

### 3.1 第一关：后端健康
```bash
cd apps/django
.venv/bin/python manage.py check   # 0 issues
```
⚠️ **仅 `check` 不够**——它不跑 migration、不连数据库。须 + migrate + 真接口实测。

### 3.2 第二关：前端静态
```bash
cd web/app
npm run lint:ci                      # ESLint exit 0
npm run build:nocheck                # vite build exit 0
```
- **`npm run lint:ci`**：CI 模式（不输出 fix 建议，只报错）。
- **`npm run build:nocheck`**：vue-tsc 类型检查因 OOM 经常 SIGKILL（exit 137），**项目禁用 vue-tsc**，用 vite build 兜底类型。
- **项目无 stylelint**——所有 UI 改动视觉验证靠 Playwright，不靠 lint。

### 3.3 第三关：真实 dev MySQL 接口实测
```bash
# 后端
.venv/bin/python manage.py runserver 0.0.0.0:8000 &

# 前端（独立端口，避开 launchd :5212 HMR 陈旧）
nohup /Users/loki/.workbuddy/binaries/node/versions/22.22.2-3/bin/npm run dev -- --port 5277 &
# 注：用托管 node，PATH 前置 .workbuddy/binaries/node/versions/22.22.2-3/bin

# 真实接口实测（curl 不走代理，避免 vite proxy 假绿）
curl --noproxy '*' http://localhost:8000/health/
curl --noproxy '*' -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'

# 前端 Browser 实测（沙箱可用 Playwright + 缓存 Chromium）
```

### 3.4 门禁失败处理 SOP

| 现象 | 可能根因 | 动作 |
|------|----------|------|
| `check` 0 issues 但接口 500 | 缺 migration | `manage.py migrate` 后再测 |
| `build:nocheck` exit 137 | vue-tsc OOM | 已禁用；改用 `vite build` |
| 接口 401/403 反复 | StatReloader 重启 1-2 秒内误报 | 等 3 秒后重试 |
| 接口 401 但 curl 200 | 同源 cookie 触发 CSRF/Session | 见 `docs/06-runbook/PROJECT_BOUNDARY.md` §3.3 + DRF 配置 |
| UI 改动前端看不到 | launchd :5212 HMR 陈旧 / vite 跑在 worktree | 改用 :5277 独立端口；检查 vite 进程 cwd |

### 3.5 沙箱环境特殊

- **Playwright + 缓存 Chromium 可用**（CommonJS 写法）：
  ```js
  import pkg from 'playwright';
  const { chromium } = pkg;
  const browser = await chromium.launch({ headless: true });
  ```
- **不要再以"沙箱无浏览器"为由跳过真实浏览器验证**——这是已知翻车点。
- **并行会话会替本会话 commit**（MEMORY 实证 2026-09-20）：交付前必 `git log`+`git status` 核实真实状态，勿假设"没 commit 就还没提交"。
