"""论坛域回归测试（板块 / 发帖 / 板块过滤 / 关键词搜索）。

覆盖契约 §3.3 的三项要求：
1. **发帖** —— 发帖人固定为当前登录用户（不信任前端传的 author）；
2. **板块过滤** —— `?board=` 只返回该板块的帖子；
3. **关键词搜索** —— `?kw=` 按标题模糊匹配。

另含一条隔离口径回归：论坛是社区空间，**全部角色可见**（逆向清单 §4.2），
故帖子列表**不按校招生可见范围收窄**。
"""
import pytest

from apps.campus_learning.models import ForumBoard, ForumPost

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-learning'


@pytest.fixture
def board(db):
    return ForumBoard.objects.create(name='学习交流', description='课程讨论', sort=1)


@pytest.fixture
def board2(db):
    return ForumBoard.objects.create(name='生活八卦', description='轻松一刻', sort=2)


# ---------------------------------------------------------------------------
# 发帖
# ---------------------------------------------------------------------------
def test_create_post_sets_author_to_current_user(auth_client, board, super_user):
    """发帖人 = 当前登录用户（前端传 author 也不认）。"""
    resp = auth_client.post(
        f'{BASE}/forum-posts/',
        {'board': board.id, 'title': '这门课怎么复习', 'content': '求资料',
         'author': str(super_user.id)},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()['data']
    assert data['title'] == '这门课怎么复习'
    # author 是 core.User 外键 → 主键为整型（校招生档案外键才是 nanoid 字符串）
    assert str(data['author']) == str(super_user.id)
    assert data['authorName'] == super_user.full_name
    assert data['boardName'] == '学习交流'
    assert data['replyCount'] == 0
    assert data['pinned'] is False


def test_post_list_returns_created_post(auth_client, board):
    """发帖后列表能查到。"""
    auth_client.post(
        f'{BASE}/forum-posts/',
        {'board': board.id, 'title': '标题一', 'content': '正文'},
        format='json',
    )
    resp = auth_client.get(f'{BASE}/forum-posts/')
    assert resp.status_code == 200, resp.content
    titles = [r['title'] for r in resp.json()['data']]
    assert '标题一' in titles


# ---------------------------------------------------------------------------
# 板块过滤 + 关键词搜索
# ---------------------------------------------------------------------------
def test_filter_posts_by_board(auth_client, board, board2):
    """?board= 只返回该板块的帖子。"""
    auth_client.post(
        f'{BASE}/forum-posts/',
        {'board': board.id, 'title': '学习区的帖子', 'content': '正文'},
        format='json',
    )
    auth_client.post(
        f'{BASE}/forum-posts/',
        {'board': board2.id, 'title': '生活区的帖子', 'content': '正文'},
        format='json',
    )

    resp = auth_client.get(f'{BASE}/forum-posts/?board={board.id}')
    assert resp.status_code == 200, resp.content
    titles = [r['title'] for r in resp.json()['data']]
    assert titles == ['学习区的帖子']


def test_keyword_search_filters_by_title(auth_client, board):
    """?kw= 按标题模糊匹配。"""
    auth_client.post(
        f'{BASE}/forum-posts/',
        {'board': board.id, 'title': '校招课程资料汇总', 'content': '正文'},
        format='json',
    )
    auth_client.post(
        f'{BASE}/forum-posts/',
        {'board': board.id, 'title': '今天食堂吃什么', 'content': '正文'},
        format='json',
    )

    resp = auth_client.get(f'{BASE}/forum-posts/?kw=校招')
    assert resp.status_code == 200, resp.content
    titles = [r['title'] for r in resp.json()['data']]
    assert titles == ['校招课程资料汇总']


def test_keyword_search_no_result_returns_empty_list(auth_client, board):
    """搜索无结果 → 空列表（不是 404，也不是报错）。"""
    auth_client.post(
        f'{BASE}/forum-posts/',
        {'board': board.id, 'title': '今天食堂吃什么', 'content': '正文'},
        format='json',
    )
    resp = auth_client.get(f'{BASE}/forum-posts/?kw=不存在的关键词')
    assert resp.status_code == 200, resp.content
    assert resp.json()['data'] == []


# ---------------------------------------------------------------------------
# 隔离口径
# ---------------------------------------------------------------------------
def test_forum_posts_are_not_scoped_by_person(mentor_client, board, make_person):
    """论坛**全部角色可见** —— 导师也能看到其他班学生的帖子（逆向清单 §4.2）。"""
    other = make_person('别人班的同学')
    ForumPost.objects.create(
        board=board, title='外班的帖子', content='正文', person=other,
    )

    resp = mentor_client.get(f'{BASE}/forum-posts/')
    assert resp.status_code == 200, resp.content
    titles = [r['title'] for r in resp.json()['data']]
    assert titles == ['外班的帖子']


def test_soft_delete_hides_post_from_list(auth_client, board):
    """软删后列表不再出现；restore 后回来。"""
    resp = auth_client.post(
        f'{BASE}/forum-posts/',
        {'board': board.id, 'title': '待删除的帖子', 'content': '正文'},
        format='json',
    )
    post_id = resp.json()['data']['id']

    resp = auth_client.delete(f'{BASE}/forum-posts/{post_id}/')
    assert resp.status_code == 200, resp.content

    resp = auth_client.get(f'{BASE}/forum-posts/')
    assert not any(r['id'] == post_id for r in resp.json()['data'])

    resp = auth_client.post(f'{BASE}/forum-posts/{post_id}/restore/', {}, format='json')
    assert resp.status_code == 200, resp.content

    resp = auth_client.get(f'{BASE}/forum-posts/')
    assert any(r['id'] == post_id for r in resp.json()['data'])
