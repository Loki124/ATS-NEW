"""Add Candidate V2 - SSE 流 (Redis pub/sub 改造)

为什么用 Redis pub/sub：
- 内存 defaultdict 在多进程部署（gunicorn workers × Celery workers）下不工作 —
  Celery worker 写到自己进程的 dict，gunicorn worker 读不到。
- Redis pub/sub 跨进程、跨机器共享，Celery → Web 事件可靠送达。
"""
import json
import time

import redis
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework.views import APIView

from apps.core.permissions import IsHROrAbove
from apps.core.role_v2_query import is_super_admin

_redis = None


def _get_redis():
    """懒加载 Redis client（连 CELERY_BROKER_URL）"""
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.CELERY_BROKER_URL)
    return _redis


def broadcast_event(task_id: str, payload: dict):
    """Celery task 调这个推 SSE 事件（写入 Redis pub/sub）"""
    r = _get_redis()
    channel = f'add_candidate:scoring:{task_id}'
    r.publish(channel, json.dumps(payload, ensure_ascii=False))


def _consume_events(task_id: str):
    """SSE consumer generator（订阅 Redis pub/sub）"""
    r = _get_redis()
    pubsub = r.pubsub()
    channel = f'add_candidate:scoring:{task_id}'
    pubsub.subscribe(channel)

    last_heartbeat = time.time()
    try:
        for message in pubsub.listen():
            if message['type'] != 'message':
                continue
            try:
                evt = json.loads(message['data'])
            except (TypeError, ValueError):
                continue
            event = evt.get('event', 'message')
            data = json.dumps(evt.get('data', {}), ensure_ascii=False)
            yield f'event: {event}\ndata: {data}\n\n'
            if event == 'task-complete':
                break

            # Heartbeat
            now = time.time()
            if now - last_heartbeat > 15:
                yield ': heartbeat\n\n'
                last_heartbeat = now
    finally:
        try:
            pubsub.unsubscribe(channel)
        except Exception:  # noqa: BLE001 — SSE 收尾: Redis pubsub 关闭失败不应让 SSE 推送连接泄漏
            pass
        try:
            pubsub.close()
        except Exception:  # noqa: BLE001 — 同上, pubsub.close 失败兜底 (best-effort 收尾)
            pass


class ScoringStreamView(APIView):
    """GET /scoring/stream/{task_id}/

    SSE 评分进度流。前端 EventSource 连这个端点。
    """
    permission_classes = [IsHROrAbove]

    def get(self, request, task_id):
        # 2026-07-02: IDOR fix — 校验 task_id 归属当前 actor (或超管)
        #   之前缺校验 → HR-A 可订阅 HR-B 的 scoring 流, 偷看候选人评分细节
        #   owner 写入由 ScoringStartView / BulkCreateView 在 redis hash 中完成
        owner_key = f'add_candidate:scoring:owner:{task_id}'
        owner_id = _get_redis().get(owner_key)
        if owner_id is None:
            from rest_framework.response import Response
            from rest_framework import status as http_status
            return Response(
                {'detail': 'Task not found or expired', 'code': 'TASK_NOT_FOUND'},
                status=http_status.HTTP_404_NOT_FOUND,
            )
        owner_id = owner_id.decode() if isinstance(owner_id, bytes) else str(owner_id)
        if owner_id != str(request.user.id) and not is_super_admin(request.user):
            from rest_framework.response import Response
            from rest_framework import status as http_status
            return Response(
                {'detail': 'Permission denied', 'code': 'FORBIDDEN'},
                status=http_status.HTTP_403_FORBIDDEN,
            )

        response = StreamingHttpResponse(
            _consume_events(task_id),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # nginx 不缓冲
        return response
