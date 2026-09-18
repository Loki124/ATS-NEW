#!/usr/bin/env python3
"""
ATS-NEW Webhook 接收器 (FastAPI 版, 由 ats-deploy-infra 的 ats-webhook.service 拉起)

监听 127.0.0.1:9876, 校验 Gitee 推送的 X-Gitee-Token, 触发 Docker 自动部署脚本。

Gitee Webhook 约定:
- 请求头 `X-Gitee-Token` = 在 Gitee 后台设置的「密钥」(明文, 非 HMAC 签名)
- 请求头 `X-Gitee-Event` = 事件类型, Push 事件为 "Push Hook", 测试为 "Test Hook"
- 请求体 JSON 含 `ref` 字段, 形如 "refs/heads/main"

设计:
- 仅处理目标分支 (默认 main) 的 Push Hook
- 部署脚本自身带 flock 并发锁, 这里直接 spawn 后台拉起即可, HTTP 立即 200 返回
- 与旧 ops/scripts/webhook_receiver.py 行为一致, 仅替换为 FastAPI 框架
- 接收器只需 Docker CLI (经 /run/docker.sock 与守护进程通信), 不直写 /var/lib/docker

环境变量:
  WEBHOOK_SECRET   必填, Gitee webhook 密钥 (校验不通过返回 403)
  WEBHOOK_PORT     监听端口, 默认 9876 (与 ats-webhook.service 对齐)
  WEBHOOK_HOST     监听地址, 默认 127.0.0.1
  WEBHOOK_BRANCH   触发部署的分支, 默认 main
  DEPLOY_SCRIPT    部署脚本绝对路径, 默认 /opt/ats-deploy-infra/bin/webhook-deploy.sh
  PENDING_DIR      触发记录目录, 默认 /var/lib/ats-deploy/pending
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request, Response

SECRET = os.environ.get("WEBHOOK_SECRET", "")
PORT = int(os.environ.get("WEBHOOK_PORT", "9876"))
HOST = os.environ.get("WEBHOOK_HOST", "127.0.0.1")
BRANCH = os.environ.get("WEBHOOK_BRANCH", "main")
DEPLOY_SCRIPT = os.environ.get(
    "DEPLOY_SCRIPT", "/opt/ats-deploy-infra/bin/webhook-deploy.sh"
)
PENDING_DIR = Path(os.environ.get("PENDING_DIR", "/var/lib/ats-deploy/pending"))

app = FastAPI(title="ATS-NEW Webhook Receiver")


def _trigger_deploy() -> None:
    """后台触发部署脚本 (脚本自身有 flock 防重入)。"""

    def _run() -> None:
        try:
            env = dict(os.environ)
            env["WEBHOOK_BRANCH"] = BRANCH
            subprocess.Popen(
                ["bash", DEPLOY_SCRIPT],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[webhook] 触发部署失败: {exc}")

    threading.Thread(target=_run, daemon=True).start()


def _write_pending(body: dict) -> None:
    """落盘触发记录 (仅审计用途, 非部署流程必需)。"""
    try:
        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        head = body.get("head_commit") or {}
        commit = body.get("after") or head.get("id") or "unknown"
        record = {
            "branch": BRANCH,
            "ref": body.get("ref"),
            "commit": commit,
            "author": (head.get("author") or {}).get("name"),
            "triggered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        stamp = f"{commit}.{int(time.time() * 1000)}"
        (PENDING_DIR / f"{stamp}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[webhook] 写 pending 记录失败 (非致命): {exc}")


def _is_push_to_target_branch(body: dict) -> bool:
    return body.get("ref") == f"refs/heads/{BRANCH}"


@app.get("/health")
@app.get("/healthcheck")
@app.get("/")
async def health():
    return {
        "status": "ok",
        "service": "ats-webhook",
        "branch": BRANCH,
        "deploy_script": DEPLOY_SCRIPT,
        "secret_configured": bool(SECRET),
    }


@app.post("/webhook")
async def webhook(request: Request):
    token = request.headers.get("X-Gitee-Token", "")
    event = request.headers.get("X-Gitee-Event", "")

    if not SECRET:
        return Response(
            content=json.dumps({"ok": False, "error": "server WEBHOOK_SECRET 未配置"}),
            status_code=500,
            media_type="application/json",
        )
    if token != SECRET:
        print(f"[webhook] 密钥校验失败 (event={event})")
        return Response(
            content=json.dumps({"ok": False, "error": "invalid token"}),
            status_code=403,
            media_type="application/json",
        )

    raw = await request.body()
    try:
        body = json.loads(raw.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        body = {}

    if event == "Test Hook":
        print("[webhook] 收到 Test Hook, 回 200 不部署")
        return {"ok": True, "message": "test ok"}

    if event != "Push Hook":
        return {"ok": True, "message": f"ignored event {event}"}

    if not _is_push_to_target_branch(body):
        ref = body.get("ref", "unknown")
        print(f"[webhook] 非目标分支 (ref={ref}, 期望 refs/heads/{BRANCH}), 忽略")
        return {"ok": True, "message": f"ignored ref {ref}"}

    print(f"[webhook] 目标分支 push, 触发部署: {DEPLOY_SCRIPT}")
    _write_pending(body)
    _trigger_deploy()
    return {
        "ok": True,
        "message": "deploy triggered",
        "deployScript": DEPLOY_SCRIPT,
        "log": "/var/log/ats-deploy.log",
    }


if __name__ == "__main__":
    if not SECRET:
        print("[webhook] ⚠ 警告: WEBHOOK_SECRET 未设置, 所有请求将返回 500。请通过环境变量注入密钥。")
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
