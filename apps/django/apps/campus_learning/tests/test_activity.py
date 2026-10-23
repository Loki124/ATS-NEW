"""活动域回归测试（活动 / 活动评分 / **奖励分值解析**）。

重点是 `parse_reward_points` —— 逆向清单 §5 A6「附加分 = 活动奖励分值 + 历月
加减分之和」需要把**文本**奖励（「+3 分」）解析成整数。它被设计成**可复用的纯
函数**（无 DB、无副作用），考核域的综合排名「附加分」维度复用同一口径。

四种必测输入：正数 / 负数 / 无数字 / 空串。
"""
import pytest

from apps.campus_learning.models import Activity, ActivityScore, parse_reward_points

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-learning'


# ---------------------------------------------------------------------------
# 奖励分值解析（纯函数）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    'text, expected',
    [
        ('+3 分', 3),        # 正数：规范写法（带符号）
        ('+10分', 10),
        ('3 分', 3),         # 正数：省略符号
        ('-2 分', -2),       # 负数：扣分
        ('-5分', -5),
        ('无奖励', 0),        # 无数字
        ('一等奖', 0),
        ('', 0),            # 空串
        (None, 0),          # None
    ],
)
def test_parse_reward_points(text, expected):
    """四种输入（正数 / 负数 / 无数字 / 空串）+ 若干变体。"""
    assert parse_reward_points(text) == expected


def test_parse_reward_points_normalizes_full_width():
    """全角写法归一化后同样能解析（「＋3 分」「３ 分」「－2 分」）。"""
    assert parse_reward_points('＋3 分') == 3
    assert parse_reward_points('３ 分') == 3
    assert parse_reward_points('－2 分') == -2


def test_parse_reward_points_prefers_signed_number():
    """带符号的整数优先 —— 「排名第 1 名，+5 分」取 +5 而不是 1。"""
    assert parse_reward_points('排名第 1 名，+5 分') == 5


def test_parse_reward_points_is_pure():
    """纯函数：同样的输入永远同样的输出，不改入参、不碰数据库。"""
    text = '+7 分'
    assert parse_reward_points(text) == 7
    assert parse_reward_points(text) == 7
    assert text == '+7 分'


# ---------------------------------------------------------------------------
# 活动 / 活动评分
# ---------------------------------------------------------------------------
@pytest.fixture
def activity(db):
    return Activity.objects.create(
        name='校招辩论赛', type='竞技', date='2026-10-20',
        status=Activity.Status.FINISHED, reward='+3 分',
    )


def test_activity_exposes_parsed_reward_points(auth_client, activity):
    """活动详情把奖励文本解析成整数分值输出（前端不必再自己 parse）。"""
    resp = auth_client.get(f'{BASE}/activities/')
    assert resp.status_code == 200, resp.content
    row = next(r for r in resp.json()['data'] if r['id'] == activity.id)
    assert row['reward'] == '+3 分'
    assert row['rewardPoints'] == 3


def test_activity_score_reward_points_exposed(auth_client, activity, make_person):
    """活动评分同样输出 rewardPoints（附加分维度的原料）。"""
    person = make_person('甲同学')
    resp = auth_client.post(
        f'{BASE}/activity-scores/',
        {'activity': activity.id, 'person': person.id, 'score': '88.00', 'reward': '-2 分', 'rank': 3},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()['data']
    assert data['rewardPoints'] == -2
    # DecimalField 在 DRF 默认序列化为字符串（COERCE_DECIMAL_TO_STRING）
    assert data['score'] == '88.00'
    assert data['rank'] == 3
    assert ActivityScore.objects.get().reward == '-2 分'


def test_activity_score_scoped_to_visible_persons(mentor_client, activity, make_person):
    """活动评分按可见范围收窄。"""
    other = make_person('别人的徒弟')
    ActivityScore.objects.create(activity=activity, person=other, score=50)

    resp = mentor_client.get(f'{BASE}/activity-scores/')
    assert resp.status_code == 200, resp.content
    assert resp.json()['data'] == []
