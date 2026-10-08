"""阶段类型守卫: 起止阶段 (START_END) 仅系统预置 (初评/正式录用) 可用, 不可用于新建阶段。

项目级标准 (兵哥 2026-09-20 定调): 系统级默认数据走系统内置 (代码枚举 / 迁移预置),
不进数据字典。START_END 类型仅由迁移 0012 预置的初评/正式录用持有,
用户新建阶段时下拉不得出现该类型, 后端序列化器亦拒绝 is_builtin=False 的 START_END。
"""
import pytest

from apps.process.models import RecruitmentStage
from apps.process.serializers import RecruitmentStageSerializer


@pytest.mark.django_db
def test_create_stage_rejects_start_end_type():
    """新建阶段传入 START_END (未置 is_builtin) 必须被拒。"""
    s = RecruitmentStageSerializer(data={'name': '仅测试起止', 'stage_type': 'START_END'})
    assert s.is_valid() is False
    assert 'stage_type' in s.errors


@pytest.mark.django_db
def test_create_stage_allows_normal_type():
    """新建阶段传入普通类型 (SCREEN) 应放行。"""
    s = RecruitmentStageSerializer(data={'name': '仅测试筛选', 'stage_type': 'SCREEN'})
    assert s.is_valid() is True


@pytest.mark.django_db
def test_update_builtin_start_end_allowed():
    """编辑系统预置的初评 (is_builtin=True, START_END) 不应被守卫拦截。"""
    stage = RecruitmentStage.objects.filter(
        code='P001', deleted_at__isnull=True,
    ).first()
    assert stage is not None
    s = RecruitmentStageSerializer(
        instance=stage,
        data={'name': stage.name, 'stage_type': 'START_END', 'is_builtin': True},
        partial=True,
    )
    assert s.is_valid() is True
