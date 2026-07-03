"""Stage start/end business rule tests (BR-001 强化)

覆盖:
- 一个 stage 不能同时 is_start=true 且 is_end=true
- is_start=true 全局只能有 1 个
- is_end=true 全局只能有 1 个
- 修改其他 stage 时,如果把 is_start 设为 true,之前那个会保留 → 校验拒绝
- 修改自身:取消 is_start 是允许的
- 新创建的 stage 默认 is_start=false is_end=false
"""
from django.test import TestCase
from apps.process.models import RecruitmentStage, StageStatus, StageType


class StageStartEndTestCase(TestCase):
    def setUp(self):
        # 初评 (起始)
        self.initial = RecruitmentStage.objects.create(
            code='P001', name='初评', stage_type=StageType.SCREEN,
            status=StageStatus.ENABLED, is_builtin=True,
            is_start=True, is_end=False,
        )
        # 正式录用 (结束)
        self.offer = RecruitmentStage.objects.create(
            code='P008', name='正式录用', stage_type=StageType.OFFER,
            status=StageStatus.ENABLED, is_builtin=True,
            is_start=False, is_end=True,
        )
        # 一个普通阶段
        self.normal = RecruitmentStage.objects.create(
            code='P002', name='简历评估', stage_type=StageType.SCREEN,
            status=StageStatus.ENABLED,
            is_start=False, is_end=False,
        )

    def test_both_flags_cannot_be_set(self):
        """同一阶段不能同时 is_start=true 且 is_end=true"""
        from apps.process.serializers import RecruitmentStageSerializer
        # 修改 normal 让它两个都 true
        s = RecruitmentStageSerializer(
            instance=self.normal,
            data={'is_start': True, 'is_end': True},
            partial=True,
        )
        self.assertFalse(s.is_valid())
        # 验证错误包含 is_start 或 non_field_errors
        err = s.errors
        self.assertTrue('is_start' in err or 'non_field_errors' in err,
                        f'Expected is_start/non_field_errors error, got: {err}')

    def test_only_one_start_stage_allowed(self):
        """is_start=true 全局只能有 1 个,试图给 normal 设置 is_start=true 应该失败"""
        from apps.process.serializers import RecruitmentStageSerializer
        s = RecruitmentStageSerializer(
            instance=self.normal,
            data={'is_start': True},
            partial=True,
        )
        self.assertFalse(s.is_valid())
        self.assertIn('is_start', s.errors)

    def test_only_one_end_stage_allowed(self):
        """is_end=true 全局只能有 1 个,试图给 normal 设置 is_end=true 应该失败"""
        from apps.process.serializers import RecruitmentStageSerializer
        s = RecruitmentStageSerializer(
            instance=self.normal,
            data={'is_end': True},
            partial=True,
        )
        self.assertFalse(s.is_valid())
        self.assertIn('is_end', s.errors)

    def test_self_unset_allowed(self):
        """取消自身的 is_start 是允许的"""
        from apps.process.serializers import RecruitmentStageSerializer
        s = RecruitmentStageSerializer(
            instance=self.initial,
            data={'is_start': False},
            partial=True,
        )
        self.assertTrue(s.is_valid(), f'Expected valid, got: {s.errors}')

    def test_create_new_stage_default_not_start_or_end(self):
        """新创建的 stage 默认 is_start=false is_end=false"""
        s = RecruitmentStage.objects.create(
            code='P003', name='电话沟通', stage_type=StageType.INVITATION,
            status=StageStatus.ENABLED,
        )
        self.assertFalse(s.is_start)
        self.assertFalse(s.is_end)
