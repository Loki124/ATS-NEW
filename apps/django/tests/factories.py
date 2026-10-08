"""factory_boy 起步工厂 (#40, 2026-10-09).

审计指出数据构造全靠手写 ORM + raw SQL helper, 引入 factory_boy 收敛。本文件是
**起步集**: 先提供最高频的 User / Candidate / Department 工厂; 其余模型 (Application /
Process / Offer ...) 的工厂按需在各自 app 的 tests/ 下补齐, 逐步替换手写 fixture。

用法 (测试内):
    from tests.factories import CandidateFactory
    cand = CandidateFactory()                       # 默认 recruit_type=social
    cand = CandidateFactory(recruit_type='campus')  # 校园招聘分区
    user = UserFactory()                            # 密码固定 'testpass123'

注意: Candidate 的 phone_hash/email_hash/id_card_hash 由模型 save() 自动计算,
      工厂无需 (也不应) 手动设置。
"""
import factory
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    class Meta:
        model = 'core.User'
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@example.com')
    # 默认密码统一, 便于测试登录; 真随机密码请用 UserFactory(password='...')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = 'core.Department'
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'部门_{n}')


class CandidateFactory(DjangoModelFactory):
    class Meta:
        model = 'candidate.Candidate'

    name = factory.Sequence(lambda n: f'候选人_{n}')
    phone = factory.Sequence(lambda n: f'1380000{n:04d}')
    # recruit_type 有默认值 (social); 校园分区用例显式传 recruit_type='campus'
    # phone_hash/email_hash/id_card_hash 由模型 save() 自动计算, 此处不设置。
