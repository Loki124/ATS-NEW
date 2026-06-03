# ATS-New Webhook 自动部署

`git push` → server 自动 `git pull + prisma + build + restart`，**再也不用 SSH 跑脚本**。

## 架构

```
┌─ 你 ─────────────┐    ┌─ Cloudflare Tunnel ─────┐    ┌─ loki-server ───────────┐
│  git push        │ →  │ webhook.ats.lokisong    │ →  │ :9876  webhook.js        │
│                  │    │   .cloud                │    │   ↓                     │
│                  │    │                         │    │ webhook-deploy.sh       │
│                  │    │                         │    │   ↓                     │
│                  │    │                         │    │ git pull + npm + prisma │
│                  │    │                         │    │   ↓                     │
│                  │    │                         │    │ :9908  Express (重启)    │
└──────────────────┘    └─────────────────────────┘    └──────────────────────────┘
```

## 一次性安装（在 server 上）

### 1. 生成 secret

```bash
SECRET=$(openssl rand -hex 32)
echo "你的 secret: $SECRET"
# 记下来，GitHub 和 gitee 都要用同一个
```

### 2. 安装 webhook 接收器（systemd）

```bash
# 把代码 clone 下来（如果还没）
cd /opt/ats
[ -d ATS-New ] || git clone https://gitee.com/loki126/ATS-NEW.git ATS-New
cd ATS-New
git pull origin main

# 装 systemd unit（先改 secret）
sudo tee /etc/systemd/system/ats-webhook.service > /dev/null <<EOF
[Unit]
Description=ATS-New Webhook Receiver
After=network.target

[Service]
Type=simple
User=loki
Group=loki
WorkingDirectory=/opt/ats/ATS-New
Environment="WEBHOOK_SECRET=替换成第1步生成的secret"
Environment="WEBHOOK_PORT=9876"
Environment="WEBHOOK_BRANCH=main"
ExecStart=/usr/bin/node /opt/ats/ATS-New/scripts/webhook.js
Restart=always
RestartSec=5
StandardOutput=append:/home/loki/ats-webhook.log
StandardError=append:/home/loki/ats-webhook.log

[Install]
WantedBy=multi-user.target
EOF

# 启用 + 启动
sudo systemctl daemon-reload
sudo systemctl enable ats-webhook
sudo systemctl start ats-webhook
sudo systemctl status ats-webhook

# 验证健康检查
curl -s http://localhost:9876/health
# → {"status":"ok","service":"ats-webhook",...}
```

### 3. CF Tunnel 加一条 public hostname

在 Cloudflare Zero Trust dashboard → 你的 Tunnel → **Public Hostname** → **Add a public hostname**：

| 字段 | 值 |
|---|---|
| Subdomain | `webhook` |
| Domain | `lokisong.cloud` |
| Service | `http://localhost:9876` |

保存。CF 会给你新域名 `https://webhook.lokisong.cloud`。

### 4. 配 GitHub Webhook

在 `https://github.com/Loki124/ATS-NEW/settings/hooks` → **Add webhook**：

| 字段 | 值 |
|---|---|
| Payload URL | `https://webhook.lokisong.cloud/webhook` |
| Content type | `application/json` |
| Secret | 第 1 步的 secret |
| SSL verification | Enable |
| Events | **Just the push event** |

点 **Add webhook**。GitHub 会发一个 ping 验证：
- `Response: 200` ✓
- 看 server：`tail -20 /home/loki/ats-webhook.log`

### 5. 配 gitee Webhook（如果你也用 gitee）

在 `https://gitee.com/loki126/ATS-NEW/manage/webhooks` → **添加 Webhook**：

| 字段 | 值 |
|---|---|
| URL | `https://webhook.lokisong.cloud/webhook` |
| 事件 | **Push** |
| 密钥 | 第 1 步的 secret（gitee 叫"密钥"） |

## 测试

```bash
# 手动测试 webhook（带正确签名）
SECRET='你的 secret'
BODY='{"ref":"refs/heads/main","commits":[]}'
SIG="sha256=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')"
curl -X POST http://localhost:9876/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-Hub-Signature-256: $SIG" \
  -d "$BODY"
# → {"ok":true,"message":"deploy triggered","deployLog":"/tmp/ats-deploy.log","pid":12345}

# 看部署进度
tail -f /tmp/ats-deploy.log

# 健康检查
curl -s http://localhost:9876/health
```

## 日常使用

```bash
# 本地开发完
git add .
git commit -m "feat: xxx"
git push origin main

# → 10-30 秒后，server 自动：
#   - git pull
#   - npm install (后端)
#   - prisma generate + db push
#   - npm install + build (前端)
#   - 重启 Express on :9908

# 看部署日志
tail -f /tmp/ats-deploy.log
```

## 故障排查

```bash
# webhook 服务状态
sudo systemctl status ats-webhook
journalctl -u ats-webhook -n 50

# 部署日志
tail -50 /tmp/ats-deploy.log

# Express 日志
tail -50 /home/loki/ats-backend.log

# 手动跑一次部署（跳过 webhook）
bash /opt/ats/ATS-New/scripts/webhook-deploy.sh

# 重启 webhook
sudo systemctl restart ats-webhook
```

## 安全注意

- **secret 必须保密**：泄露了别人能随便触发你的部署
- **9876 端口**：Cloudflare Tunnel 暴露了公网，但有 secret 守门，安全性 OK
- **systemd 加固**：`webhook.service` 已设 `NoNewPrivileges` / `PrivateTmp` / `ProtectSystem`
- **部署脚本是 root 跑的吗？**：不是，以 `loki` 用户跑（`User=loki`）。如果部署中需要 `sudo`，得给 `loki` 加 NOPASSWD

## 文件清单

| 文件 | 作用 |
|---|---|
| `scripts/webhook.js` | Node.js webhook 接收器（GitHub + gitee 签名验证） |
| `scripts/webhook-deploy.sh` | 实际跑 git pull + prisma + build + restart |
| `scripts/webhook.service` | systemd unit 模板 |
| `scripts/webhook-setup.md` | 本文档 |
