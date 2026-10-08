"""P1-3 统一信封 helper 单测（纯函数，不触库，可在 SQLite 下运行）。"""
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from apps.common.response import error_response, success_response
from apps.common.views import EnvelopeWriteMixin


def test_success_response_basic_shape():
    resp = success_response({'id': 1}, message='ok')
    assert resp.status_code == 200
    body = resp.data
    assert body == {
        'success': True,
        'data': {'id': 1},
        'message': 'ok',
        'code': 0,
    }


def test_success_response_defaults():
    resp = success_response()
    body = resp.data
    assert body['success'] is True
    assert body['data'] is None
    assert body['message'] == ''
    assert body['code'] == 0


def test_success_response_created_status():
    resp = success_response({'id': 1}, status_code=status.HTTP_201_CREATED)
    assert resp.status_code == 201


def test_success_response_pagination_added():
    resp = success_response([1, 2], pagination={'total': 2, 'page': 1})
    body = resp.data
    assert body['success'] is True
    assert body['data'] == [1, 2]
    assert body['pagination'] == {'total': 2, 'page': 1}


def test_error_response_shape():
    resp = error_response(message='bad', code=1, status_code=400, errors={'f': ['x']})
    assert resp.status_code == 400
    body = resp.data
    assert body == {
        'success': False,
        'data': None,
        'message': 'bad',
        'code': 1,
        'errors': {'f': ['x']},
    }


def test_error_response_default_status():
    resp = error_response(message='fail')
    assert resp.status_code == 400


# ---- EnvelopeWriteMixin 集成（用 APIRequestFactory，不触库） ----
class _DummySerializer:
    def __init__(self, instance=None, data=None, partial=False, many=False):
        self.instance = instance
        self._data = data or {'id': 99}
        self.data = self._data

    def is_valid(self, raise_exception=False):
        return True


class _DummyViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
    serializer_class = _DummySerializer
    permission_classes = [AllowAny]

    def get_serializer(self, *args, **kwargs):
        return _DummySerializer(*args, **kwargs)

    def get_object(self):
        return object()

    def perform_create(self, serializer):
        pass

    def perform_update(self, serializer):
        pass


def test_envelope_write_mixin_create_envelopes():
    factory = APIRequestFactory()
    view = _DummyViewSet.as_view({'post': 'create'})
    req = factory.post('/x/', {'a': 1}, format='json')
    resp = view(req)
    assert resp.status_code == 201
    assert resp.data['success'] is True
    # create 把 serializer.data 透传进 data（此处 dummy 回显入参）
    assert resp.data['data'] == {'a': 1}


def test_envelope_write_mixin_retrieve_envelopes():
    factory = APIRequestFactory()
    view = _DummyViewSet.as_view({'get': 'retrieve'})
    req = factory.get('/x/1/')
    resp = view(req, pk=1)
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert resp.data['data'] == {'id': 99}
