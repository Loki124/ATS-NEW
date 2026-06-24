"""Add Candidate V2 - SSE 流"""
import json
import threading
import time
from collections import defaultdict

from django.http import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

# 内存 pub/sub：task_id → list of (event, data) tuples
_TASK_EVENTS: dict = defaultdict(list)
_TASK_LOCKS: dict = defaultdict(threading.Lock)


def broadcast_event(task_id: str, payload: dict):
    """Celery task 调这个推 SSE 事件"""
    with _TASK_LOCKS[task_id]:
        _TASK_EVENTS[task_id].append(payload)


def _consume_events(task_id: str):
    """SSE consumer generator"""
    last_heartbeat = time.time()
    while True:
        with _TASK_LOCKS[task_id]:
            events = list(_TASK_EVENTS[task_id])
            _TASK_EVENTS[task_id].clear()

        for evt in events:
            event = evt.get('event', 'message')
            data = json.dumps(evt.get('data', {}), ensure_ascii=False)
            yield f'event: {event}\ndata: {data}\n\n'
            if event == 'task-complete':
                return

        # Heartbeat
        if time.time() - last_heartbeat > 15:
            yield ': heartbeat\n\n'
            last_heartbeat = time.time()

        time.sleep(0.5)


class ScoringStreamView(APIView):
    """GET /scoring/stream/{task_id}/

    SSE 评分进度流。前端 EventSource 连这个端点。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        response = StreamingHttpResponse(
            _consume_events(task_id),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # nginx 不缓冲
        return response
