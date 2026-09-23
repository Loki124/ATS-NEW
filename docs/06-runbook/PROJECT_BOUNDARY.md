# 项目边界与角色分工（业务仓 vs 部署仓）

> 适用：ATS-NEW（Django + Vue）与 ats-deploy-infra（部署基础设施）的协作分工。
> 状态：2026-09-18 运维代码剥离已落地，业务仓已无部署代码。

---

## 1. 仓库边界

| 仓库 | 职责 | 含 |
|------|------|----|
| **ATS-NEW**（业务仓，Gitee `loki126/ATS-NEW`） | 业务代码 + 数据 + 文档 | Django 6.0.6 + DRF 后端；Vue 3 + Naive UI 前端；MySQL/SQLite 数据；`docs/` 项目文档；`.workbuddy/` 内部记忆 |
| **ats-deploy-infra**（部署仓） | 部署基础设施 | `docker-compose.yml` / `nginx.conf` / `systemd/*.service` / `webhook-deploy.sh` / `bin/webhook-receiver.py` (stdlib) |

**红线**：业务仓不写部署代码、部署仓不写业务代码。混入会污染 review + 误改风险。

---

## 2. 业务仓变更检查清单

改动前先确认这条变更属于业务仓：

| 类别 | 例 | 归属 |
|------|----|------|
| Django model / view / serializer | `apps/campus_control/views.py` | ✅ 业务仓 |
| Vue 组件 / 页面 / API | `web/app/src/pages/**` | ✅ 业务仓 |
| 路由配置 / API endpoint | `apps/*/urls.py` | ✅ 业务仓 |
| 数据迁移 | `apps/*/migrations/*.py` | ✅ 业务仓 |
| 数据库 schema / 索引 | 同上 | ✅ 业务仓 |
| Dockerfile / compose / nginx / systemd | 部署相关 | ❌ → ats-deploy-infra |
| webhook 接收器 / 部署脚本 / 启动顺序 | 部署相关 | ❌ → ats-deploy-infra |

---

## 3. ats-deploy-infra 部署链路（精简）

完整链路口诀：**Web push → webhook receiver (stdlib :9876) → webhook-deploy.sh → migrate → restart → health check**。

### 3.1 Webhook 接收器
- stdlib 零依赖（迁后），监听 :9876。
- `X-Gitee-Token` 明文校验（与 Gitee webhook 配置一致）。
- 鉴权失败 → 401（不进入 deploy 流程）。

### 3.2 webhook-deploy.sh
- 关键顺序：`migrate` → `run_dictionary_seeds`（兜底）→ `collectstatic` → `restart gunicorn`。
- 🔒 **compose `${VAR:?}` 13 个必填变量硬闸**：缺任一变量 deploy 立即 fail（防"凑齐变量漏一项"的假绿）。
- 🔒 **stale flock 假绿**：`flock -n 9` 抢锁 → 失败时**递归杀接管**（不是简单退出）。

### 3.3 健康检查
- 真实健康端点 `http://localhost:$APP_PORT/health/`（**不是** `/api/health/`，旧 URL 返 404 是假绿实证）。
- 见 `docs/06-runbook/DEPLOY_1PANEL_CF_TUNNEL.md` 完整链路。

---

## 4. 业务仓不含部署代码的实证

| 时间 | Commit | 动作 |
|------|--------|------|
| 2026-09-18 | `9c03236` (ATS-NEW) | 运维代码剥离出 ATS-NEW |
| 2026-09-18 | `3a61350` (ats-deploy-infra) | 同步落到部署仓 |
| 2026-09-19 | `dd27a2f` (ATS-NEW) | webhook 接收器迁 ats-deploy-infra（最佳方案） |
| 2026-09-19 | `48910c3` (ats-deploy-infra) | 接收器落地 + 端到端验证 |

剥离后业务仓 `grep -r 'flock\|systemctl\|docker-compose\|nginx' web/ apps/ docs/ 2>/dev/null | grep -v node_modules` 应**零命中**（如有命中即混入部署代码，须还原）。

---

## 5. 跨仓协作规范

- **PR 模板**：跨仓改动（业务仓 schema 变 → 部署仓需配合）走 `docs/06-runbook/deploy-webhook-fix-pr.md` 模式：业务仓提交"PR 模板 + diff 副本"，部署仓 PR 由用户在自有环境应用（`git apply`）。
- **双保险兜底**（commit `d19dfe7`）：业务仓字典种子走幂等迁移 + 部署仓 webhook 部署后强制重跑 `run_dictionary_seeds()`，互为冗余——任一边失灵另一边兜底。

---

## 6. 关联文档

- 完整部署链路口诀 → `docs/06-runbook/DEPLOY_1PANEL_CF_TUNNEL.md`
- 字典种子兜底双保险 → `docs/06-runbook/ENGINEERING_RULES.md` §8「系统级默认数据」
- 部署侧 PR diff 模板 → `docs/06-runbook/deploy-webhook-fix-pr.md` + `docs/06-runbook/webhook-deploy.diff`