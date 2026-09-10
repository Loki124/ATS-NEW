#!/usr/bin/env python3
"""
ATS-NEW Webhook 接收器 (Docker 版, 零依赖, 仅标准库)

监听 HTTP 端口, 校验 Gitee 推送的密钥, 触发 Docker 自动部署脚本。

Gitee Webhook 约定:
- 请求头 `X-Gitee-Token` = 在 Gitee 后台设置的「密钥」(明文, 非 HMAC 签名)
- 请求头 `X-Gitee-Event` = 事件类型, Push 事件为 "Push Hook", 测试为 "Test Hook"
- 请求体 JSON 含 `ref` 字段, 形如 "refs/heads/main"

设计:
- 仅处理目标分支 (默认 main) 的 Push Hook
- 部署脚本自身带 flock 并发锁, 这里直接 Popen 后台拉起即可, HTTP 立即 200 返回
- 不依赖任何第三方包, 可直接 `python3 webhook_receiver.py` 运行

环境变量:
  WEBHOOK_SECRET   必填, Gitee webhook 密钥 (校验不通过返回 403)
  WEBHOOK_PORT     监听端口, 默认 9000
  WEBHOOK_BRANCH   触发部署的分支, 默认 main
  DEPLOY_SCRIPT    部署脚本绝对路径, 默认 本文件同目录/webhook-deploy.sh
"""

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

SECRET = os.environ.get("WEBHOOK_SECRET", "")
PORT = int(os.environ.get("WEBHOOK_PORT", "9000"))
BRANCH = os.environ.get("WEBHOOK_BRANCH", "main")
DEPLOY_SCRIPT = os.environ.get(
    "DEPLOY_SCRIPT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "webhook-deploy.sh"),
)
WEBHOOK_BRANCH = BRANCH  # 部署脚本也读 WEBHOOK_BRANCH

_lock = threading.Lock()  # 防止同一进程内短时间重复 spawn


def trigger_deploy():
    """后台触发部署脚本 (脚本自身有 flock 防重入)。"""
    def _run():
        try:
            with _lock:
                pass
            env = dict(os.environ)
            env["WEBHOOK_BRANCH"] = WEBHOOK_BRANCH
            subprocess.Popen(
                ["bash", DEPLOY_SCRIPT],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[webhook] 触发部署失败: {exc}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def is_push_to_target_branch(body: dict) -> bool:
    ref = body.get("ref", "")
    return ref == f"refs/heads/{BRANCH}"


class Handler(BaseHTTPRequestHandler):
    # 静默默认访问日志, 改用我们自己的结构化日志
    def log_message(self, fmt, *args):
        print(f"[webhook] {fmt % args}")

    def _send_json(self, code, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path.rstrip("/") in ("", "/health", "/healthcheck"):
            self._send_json(200, {
                "status": "ok",
                "service": "ats-webhook",
                "branch": BRANCH,
                "deploy_script": DEPLOY_SCRIPT,
                "secret_configured": bool(SECRET),
            })
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path.rstrip("/") not in ("/webhook",):
            self._send_json(404, {"error": "not found"})
            return

        token = self.headers.get("X-Gitee-Token", "")
        event = self.headers.get("X-Gitee-Event", "")

        if not SECRET:
            self._send_json(500, {"ok": False, "error": "server WEBHOOK_SECRET 未配置"})
            return
        if token != SECRET:
            print(f"[webhook] 密钥校验失败 (event={event})")
            self._send_json(403, {"ok": False, "error": "invalid token"})
            return

        # 读取 body
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            body = {}

        # Gitee 测试事件: 直接回 200 让 Gitee 标记连接成功, 不触发部署
        if event == "Test Hook":
            print("[webhook] 收到 Test Hook, 回 200 不部署")
            self._send_json(200, {"ok": True, "message": "test ok"})
            return

        if event != "Push Hook":
            self._send_json(200, {"ok": True, "message": f"ignored event {event}"})
            return

        if not is_push_to_target_branch(body):
            ref = body.get("ref", "unknown")
            print(f"[webhook] 非目标分支 (ref={ref}, 期望 refs/heads/{BRANCH}), 忽略")
            self._send_json(200, {"ok": True, "message": f"ignored ref {ref}"})
            return

        print(f"[webhook] 目标分支 push, 触发部署: {DEPLOY_SCRIPT}")
        trigger_deploy()
        self._send_json(200, {
            "ok": True,
            "message": "deploy triggered",
            "deployScript": DEPLOY_SCRIPT,
            "log": "/var/log/ats-deploy.log",
        })


def main():
    if not SECRET:
        print("[webhook] ⚠ 警告: WEBHOOK_SECRET 未设置, 所有请求将返回 500。请通过环境变量注入密钥。")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[webhook] 监听 0.0.0.0:{PORT}  branch={BRANCH}  script={DEPLOY_SCRIPT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[webhook] 收到中断, 退出")
        server.shutdown()


if __name__ == "__main__":
    main()
