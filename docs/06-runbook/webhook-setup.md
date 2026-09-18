# ATS-NEW Webhook 自动部署（Docker 版）

> ⚠️ **2026-09-18 更新**：部署编排（webhook 接收器 / docker-compose / Dockerfile / systemd unit / 轮询部署）
> 已整体迁移到独立仓库 **[ats-deploy-infra](https://gitee.com/loki126/ats-deploy-infra.git)**。
> 本文档描述的 `ops/scripts/*` 路径已不存在；生产栈的实际部署逻辑、令牌校验（X-Gitee-Token 明文口令，非 HMAC）、
> 构建文件注入机制，均以 ats-deploy-infra 仓库为准，详见其 README。本文件保留作历史参考。

`git push` → Gitee 触发 → 部署机自动 `git pull + docker compose build + up -d`，**再也不用 SSH 手动重建镜像**。

> 旧版（venv + systemd + npm build）已废弃。本文档对应 **1Panel + docker compose** 生产栈（现由 ats-deploy-infra 统一管理）。

## 架构

```
┌─ 你 ───────────┐   ┌─ Cloudflare Tunnel ─────────┐   ┌─ 部署机 ─────────────────────┐
│ git push main  │ → │ webhook.ats.example.com      │ → │ :9000  webhook_receiver.py  │
│               │   │   (public hostname → :9000)  │   │   ↓ (校验 X-Gitee-Token)     │
│               │   │                              │   │ ops/scripts/webhook-deploy.sh│
│               │   │                              │   │   ↓                         │
│               │   │                              │   │ git pull + docker compose   │
│               │   │                              │   │   build + up -d             │
└───────────────┘   └──────────────────────────────┘   └─────────────────────────────┘
```

要点：接收器只监听 `127.0.0.1:9000`，经 CF Tunnel 的 public hostname 暴露到公网；Gitee 用密钥（明文 header `X-Gitee-Token`）守门，无密钥无法触发部署。

## 一次性安装（在部署机上）

### 1. 生成密钥

```bash
SECRET=$(openssl rand -hex 32)
echo "你的 secret: $SECRET"
# 记下来, Gitee webhook 与 systemd unit 用同一个
```

### 2. 落代码 + 安装接收器（systemd）

```bash
# 部署机仓库根 (含 ops/ apps/ web/), 默认 /opt/data/ATS-new
cd /opt/data/ATS-new
git pull origin main

# 装 systemd unit, 把 __WEBHOOK_SECRET__ 换成第 1 步生成的 secret
sudo cp ops/scripts/ats-webhook.service /etc/systemd/system/
sudo sed -i "s/__WEBHOOK_SECRET__/$SECRET/" /etc/systemd/system/ats-webhook.service

sudo systemctl daemon-reload
sudo systemctl enable --now ats-webhook
sudo systemctl status ats-webhook

# 健康检查
curl -s http://127.0.0.1:9000/health
# → {"status":"ok","service":"ats-webhook",...}
```

接收器以 root 运行（部署脚本要调 `docker compose` + `git reset`）。它只监听本机 9000，公网不可直连。

### 3. CF Tunnel 加一条 public hostname

Cloudflare Zero Trust → 你的 Tunnel → **Public Hostname → Add**：

| 字段 | 值 |
|---|---|
| Subdomain | `webhook` |
| Domain | 你的域名（与 CF Tunnel 一致，如 `ats.example.com`）|
| Service | `http://localhost:9000` |

保存后得到 `https://webhook.ats.example.com`（把 `ats.example.com` 换成你的实际域名）。

### 4. 配 Gitee Webhook

`https://gitee.com/loki126/ATS-NEW/manage/webhooks` → **添加 Webhook**：

| 字段 | 值 |
|---|---|
| URL | `https://webhook.ats.example.com/webhook` |
| 事件 | **Push** |
| 密钥 | 第 1 步的 secret（Gitee 叫「密钥」）|

添加后 Gitee 会发一个 **Test Hook**：看部署机 `tail -20 /var/log/ats-webhook.log` 应出现 `收到 Test Hook, 回 200 不部署`。

## 测试

```bash
# 手动用正确密钥模拟一次 push 到 main (会真正触发部署)
SECRET='你的 secret'
curl -X POST https://webhook.ats.example.com/webhook \
  -H "Content-Type: application/json" \
  -H "X-Gitee-Token: $SECRET" \
  -H "X-Gitee-Event: Push Hook" \
  -d '{"ref":"refs/heads/main"}'
# → {"ok":true,"message":"deploy triggered","deployScript":"/opt/data/ATS-new/ops/scripts/webhook-deploy.sh",...}

# 看部署进度 (部署脚本自带并发锁 + 健康检查)
tail -f /var/log/ats-deploy.log

# 接收器健康
curl -s http://127.0.0.1:9000/health
```

## 日常使用

```bash
# 本地改完
git add .
git commit -m "feat: xxx"
git push origin main

# → ~1-2 分钟后部署机自动:
#   - git fetch + reset 到 origin/main 最新代码
#   - docker compose build --no-cache (把新代码打进镜像, 解决"代码改了但容器没变")
#   - docker compose up -d --force-recreate
#   - 后端 /health/ 健康检查
```

## 常见问题

**Q: 推完代码容器还是旧的？**
A: 那就是没走 webhook、或手动重启了容器但没重建镜像。webhook 部署脚本已 `docker compose build --no-cache` + `--force-recreate`，保证新代码进镜像。手动排障：`docker exec ats-celery-worker sed -n '204,213p' /app/config/settings/base.py` 看容器内代码是否最新。

**Q: 部署日志在哪？**
A: `/var/log/ats-deploy.log`（部署脚本输出）+ `/var/log/ats-webhook.log`（接收器输出）。

**Q: 想手动触发一次部署（跳过 webhook）？**
A: `sudo bash /opt/data/ATS-new/ops/scripts/webhook-deploy.sh`

**Q: 接收器挂了？**
A: `sudo systemctl restart ats-webhook`；`systemctl status ats-webhook` / `journalctl -u ats-webhook -n 50`。

**Q: Gitee 测试 webhook 报 `SSLHandshakeException: handshake_failure`（返回 -2）？**
A: 这是 **Gitee 的 Java webhook 客户端与 Cloudflare 边缘的 TLS 协商失败**，还没到我们的接收器，也不是密钥错（密钥错会返回 403）。先本地验证链路本身是否通：
   ```bash
   curl -v https://webhook.你的域名/webhook
   ```
   若本地能正常握手（TLS 1.3 + 证书有效，且 GET /webhook 命中接收器自定义 404 `{"error":"not found"}`），说明 DNS / CF Tunnel / 接收器都正常，问题只在 Gitee 客户端。
   根因：Gitee 的 Java 栈不支持 Cloudflare 默认的 **TLS 1.3 / ChaCha20-POLY1305** 协商。
   修复：Cloudflare 后台 → **SSL/TLS → Edge Certificates → TLS 1.3 关掉（OFF）**，强制 TLS 1.2 + AES-GCM（Java 客户端支持）。改完回 Gitee webhook 管理页「重发请求」，应返回 200（`null: HTTP/1.1 200 OK` 是 Gitee 的响应行前缀）。注意 Gitee webhook 出口地理浮动（CF-RAY 可能在 HKG/AMS 等不同边缘），该设置对所有边缘生效。
   坑：本地测 curl 时 `-H` 头要写在同一行或用 `\` 续行，否则 zsh 会报 `command not found: -H`，导致只发了裸 GET（返回 404 属预期，不代表链路坏）。

**Q: 部署一直打印「已有部署在跑 (lock 被占), 本次跳过」，线上代码就是不变？**
A: 上一次部署进程挂死（或子进程继承了 flock 的 fd 9 没释放），把 `/var/run/ats-deploy.lock` 的锁占死了。后续所有触发都被跳过 → 「推了 Gitee 但线上不变」。
   - 处置：`sudo lsof /var/run/ats-deploy.lock` 找持有进程 → `sudo fuser -k /var/run/ats-deploy.lock` 杀掉 → 再 `sudo bash /opt/data/ATS-new/ops/scripts/webhook-deploy.sh`。
   - 脚本已加**僵死锁自愈**：锁龄 > `LOCK_STALE_SECONDS`（默认 1800s）自动强制接管，不再需要手动清锁。

**Q: 部署报 `error while interpolating ...: required variable XXX is missing a value`？**
A: `docker-compose.yml` 里有 `${XXX:?必填}` 插值变量，但生产 `ops/.env` 没配。compose 插值**遇到第一个缺失就停**，所以要一次性补齐。
   - 脚本已加**前置检查**（第 0 步）：build 前自动抽取 compose 里所有必填变量，缺了直接列清单，不再 build 到一半才炸。
   - 补齐方法：对照 `ops/.env.example`，把缺的变量写进 `/opt/data/ATS-new/ops/.env`。

## 轮询式自动部署（不依赖 Gitee webhook，推荐作为兜底）

Gitee webhook 受限于「Gitee 的 Java 客户端 ↔ Cloudflare 边缘 TLS 协商」，偶发投递失败。为保证「每次 push 必部署」，增加一条**服务端主动 pull** 的兜底链路——部署机定时 `git fetch` 对比 `origin/main`，有新增提交就自动部署，与 webhook 完全解耦。

**安装（部署机执行）：**
```bash
sudo cp /opt/data/ATS-new/ops/scripts/ats-poll-deploy.service \
        /opt/data/ATS-new/ops/scripts/ats-poll-deploy.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ats-poll-deploy.timer
```

**日常使用：** `git push` 后 5 分钟内自动 `git fetch` 发现新提交并部署，无需任何手动触发。

**查看 / 调试：**
```bash
systemctl list-timers ats-poll-deploy.timer      # 下次触发时间
sudo systemctl start ats-poll-deploy.service     # 立即手动跑一次
tail -f /var/log/ats-poll-deploy.log             # 触发记录(只记"检测到新提交")
tail -f /var/log/ats-deploy.log                  # 部署详情
```

**要点：**
- `poll-deploy.sh` 无新提交时静默退出（不刷日志）；有新提交才调 `webhook-deploy.sh`。
- 与 `ats-webhook.service` 并存互不干扰——两者最终都调 `webhook-deploy.sh`，由同一把 `flock` 锁防重叠。
- 若部署失败（build 报错），修好代码 push 新提交即可由下轮自动重试。

## 安全注意

- **secret 必须保密**：泄露后任何人可触发你的部署（虽然只是 pull + rebuild，不会泄露数据，但会浪费算力）。
- **9000 端口本机监听**：公网经 CF Tunnel 反代，且有密钥校验；不要把 9000 直接暴露到 0.0.0.0 公网。
- **root 运行**：接收器需调 docker；`ats-webhook.service` 已 `NoNewPrivileges` / `PrivateTmp` / `ReadWritePaths` 最小化加固。

## 文件清单

| 文件 | 作用 |
|---|---|
| `ops/scripts/webhook_receiver.py` | Webhook 接收器（Python 标准库，零依赖，校验 `X-Gitee-Token`，触发部署） |
| `ops/scripts/webhook-deploy.sh` | 实际部署：`git pull` + `docker compose build --no-cache` + `up -d --force-recreate` + 健康检查 |
| `ops/scripts/ats-webhook.service` | systemd unit（运行接收器，监听 9000） |
| `ops/scripts/poll-deploy.sh` | 轮询部署脚本：`git fetch` + 对比 `origin/main`，有新提交才调 `webhook-deploy.sh` |
| `ops/scripts/ats-poll-deploy.service` | systemd oneshot（跑一次 `poll-deploy.sh`） |
| `ops/scripts/ats-poll-deploy.timer` | systemd timer（每 5 分钟触发一次 service） |
| `docs/06-runbook/webhook-setup.md` | 本文档 |
