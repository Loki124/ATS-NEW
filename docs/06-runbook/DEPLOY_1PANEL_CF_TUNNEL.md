# 部署链路口诀：1Panel + CF Tunnel + Webhook
> 最后更新：2026-09-23（依据 git 最后提交）

> 适用：ATS-NEW 生产环境（`ats.lokisong.cloud:9908`）的部署链路。
> 状态：2026-09-10 至 09-16 多日部署卡点收口。

---

## 1. 完整链路口诀

```
开发者 push 到 Gitee
    ↓ (Gitee webhook POST)
ats-deploy-infra webhook receiver (stdlib :9876, X-Gitee-Token 校验)
    ↓
ats-deploy-infra webhook-deploy.sh
    ├─ flock 抢锁（失败时递归杀接管）
    ├─ git pull + checkout target SHA
    ├─ docker compose build
    ├─ backend container migrate + run_dictionary_seeds（兜底）
    ├─ frontend container build（builder node:22 glibc）
    ├─ nginx reload / 重启 backend
    └─ curl http://localhost:8000/health/ （真端点，不是 /api/health/）
    ↓
Cloudflare Tunnel (ats-deploy-infra/ats.lokisong.cloud)
    ↓
Internet (https://ats.lokisong.cloud:9908)
```

---

## 2. 部署卡点 5 层根因（2026-09-10 至 09-16 实证）

### 2.1 第一层：1Panel 创建编排 403（ats-backend，commit `9e09ed9`）

**根因**：compose `ats-backend` service 含 `image: xxx` 字段 → 1Panel 拒绝编排（要求从构建上下文 build，不接受预拉镜像）。

**修法**：删除 `image:` 字段，1Panel 自动 build。

### 2.2 第二层：pull_policy 修复（commit `1949170`）

**根因**：compose `pull_policy: always` 与本地 build 冲突 → 1Panel 反复拉取不存在的镜像 → 编排失败。

**修法**：移除 `pull_policy: always`，让 build 走本地。

### 2.3 第三层：前端容器构建 vue-tsc OOM（commit `2b2c22a`）

**根因**：前端 Dockerfile 默认 `npm run build` 含 vue-tsc 类型检查 → 容器内 OOM（exit 2）。

**修法**：Dockerfile 改用 `npm run build:nocheck`（vue-tsc 跳过）—— 与本地 dev 门禁一致。

### 2.4 第四层：oxc-parser 原生绑定缺失（commit `a29121f`）

**根因**：vite 默认 builder 镜像（如 node:18-alpine）基于 musl libc → oxc-parser 原生绑定缺失（exit 1）。

**修法**：builder 镜像换 `node:22-bookworm-slim`（glibc）。

### 2.5 第五层：node:18 EBADENGINE（commit `b735269`）

**根因**：`node:18-alpine` 已 EOL，npm/yarn/vite 报 EBADENGINE。

**修法**：统一升 `node:22`。

---

## 3. Python 容器循环报错（commit `548b9f8`）

**根因**：compose 漏传 `MYSQL_DATABASE` → Python 容器走 `DATABASE_URL` 回退 → 解析 'Port' → 成 'L' → 报 `Port could not be cast to integer value as 'L'`。

**修法**：compose 必填变量必须显式声明（详见 `docs/06-runbook/PROJECT_BOUNDARY.md` §3.2）。

---

## 4. compose 漏传 MYSQL_DATABASE（commit `afddefe`）

**根因**：第三层根因修完后仍报同样错误 → 服务器**未自动拉取最新镜像**（1Panel 应用缓存旧 image）。

**修法**：
- 1Panel 设置自动拉取最新镜像
- 或手动到 1Panel 控制台 → 应用 → 重启（拉新）
- 实证：22:29 截图硬证据（用户贴图，服务器仍是旧 image）

---

## 5. Gitee webhook TLS 握手失败

**根因**：Gitee 服务器在 Cloudflare 边缘 → CF Tunnel → 1Panel backend。某次 TLS 握手失败（Gitee 与 Cloudflare 之间）。

**修法**：
- 短期：手动重试 webhook（curl + 同样 payload）。
- 长期：webhook receiver 加重试队列（待 ats-deploy-infra 实施）。

---

## 6. 自动部署闭环验证 + flock 跳过陷阱

### 6.1 flock -n 9 抢锁失败递归接管

```bash
# 错误写法：抢锁失败直接退出 → 「假绿」（脚本退出但没真部署）
flock -n 9 || { echo "lock held"; exit 1; }

# 正确写法：递归杀旧进程后接管（commit `c777e8d` / `70d1138`）
if ! flock -n 9; then
    # 查谁拿着锁 → kill 旧部署 → 抢锁
    OLD_PID=$(lsof -t /var/lock/ats-deploy 2>/dev/null)
    [ -n "$OLD_PID" ] && kill -9 "$OLD_PID"
    sleep 1
    flock -n 9 || { echo "still locked after kill"; exit 1; }
fi
```

### 6.2 僵死锁根因

**根因**：上一次的 `deploy.sh` 因某种原因没正常释放 flock（信号未捕获、exit 不走 cleanup）。下一次的 `flock -n 9` 直接失败。

**修法**：部署脚本 trap EXIT 释放锁 + flock -n 抢锁失败时杀接管。

---

## 7. Webhook 接收器（stdlib 零依赖，迁 ats-deploy-infra）

`bin/webhook-receiver.py`：

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac, hashlib, json, os

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        token = self.headers.get('X-Gitee-Token', '')
        if not hmac.compare_digest(token, os.environ['WEBHOOK_SECRET']):
            self.send_response(401); self.end_headers(); return
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        # 转发到 webhook-deploy.sh（spawn subprocess）
        ...

HTTPServer(('0.0.0.0', 9876), Handler).serve_forever()
```

- 监听 `:9876`
- `X-Gitee-Token` 明文校验（与 Gitee webhook 配置一致）
- 鉴权失败 → 401（不进入 deploy 流程）
- 鉴权成功 → spawn `webhook-deploy.sh`

### 7.1 迁移记录
- 2026-09-19 `dd27a2f` (ATS-NEW) + `48910c3` (ats-deploy-infra)：webhook 接收器迁 ats-deploy-infra（最佳方案落地）

---

## 8. 完整部署 SOP（运维执行手册）

### 8.1 初次部署
```bash
# 在部署机（ats-deploy-infra 仓库）
docker compose up -d --build

# 验证
docker compose ps                                  # 全部 running
curl --noproxy '*' http://localhost:8000/health/  # 200
curl https://ats.lokisong.cloud:9908/             # 200（CF Tunnel）
```

### 8.2 日常部署（Gitee push 触发）
```bash
# 开发者侧
git push gitee main

# 部署机侧：自动执行（无需手动）
# webhook → receiver → deploy.sh → migrate → restart → health check
```

### 8.3 失败排查清单
| 现象 | 第一动作 |
|------|----------|
| webhook 401 | `X-Gitee-Token` 是否与 Gitee 配置一致 |
| webhook 200 但 deploy 未跑 | `journalctl -u webhook-receiver -n 100` 看 spawn |
| deploy 启动后卡 flock | `lsof /var/lock/ats-deploy` 看谁拿着锁 |
| container 起不来 | `docker compose logs backend --tail 100` |
| HTTP 200 但页面 500 | 实时检查 `manage.py runserver` console 看 traceback |
| CF Tunnel 报 1033 | `cloudflared tunnel info ats-deploy` 看 tunnel 状态 |

---

## 9. 关联文档

- 项目边界（业务仓 vs 部署仓分工） → `docs/06-runbook/PROJECT_BOUNDARY.md`
- 字典种子兜底（commit `d19dfe7` / `02a79c2`） → `docs/05-campus-control/STAGE_TYPE_SYSTEM.md` §9
- 部署侧 PR diff（字典种子兜底 + 健康端点修复） → `docs/06-runbook/deploy-webhook-fix-pr.md`
- 迁移漂移假绿（dev 库掩盖） → `docs/06-runbook/MIGRATION_DRIFT.md`