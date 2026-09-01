"""T3 软删补全变异守卫 (mutation guard)。

证明 21 个 C 类业务模型的 deleted_at 补全不是"假绿":
- 结构级: 每个模型具备 deleted_at 字段, 默认 objects 管理器过滤软删,
  all_objects 取全部(含已删)。若有人移除 SoftDeleteManager 过滤, 结构级断言即失败。
- 行为级: 以 library.School 为样本, 真实创建 -> soft_delete -> 默认管理器不可见
  -> all_objects 可见 -> restore -> 默认管理器重新可见。任何一层被改坏, 行为级断言失败。
"""
from django.test import TestCase
from django.apps import apps

# C 类 21 个业务实体 (按约定补全 deleted_at, 跳过 A 类内置 / B 类配置表)
C_MODELS = [
    'add_candidate.ParseJob',
    'analytics.ExportTask',
    'analytics.ReportSnapshot',
    'candidate.CandidateTag',
    'gdpr.GDPRRequest',
    'integration.BackgroundCheckOrder',
    'integration.BackgroundCheckOrderEvent',
    'integration.IntegrationConfig',
    'integration.IntegrationSyncLog',
    'library.Company',
    'library.School',
    'mou.MouAgreement',
    'mou.MouContainer',
    'mou.MouRule',
    'mou.MutualExclusionGroup',
    'notification.NotificationTemplate',
    'process.CandidateRecommendation',
    'process.CandidateScreen',
    'resume_flow.ApprovalFlow',
    'resume_flow.ApprovalFlowHistory',
    'scraped_resume.ScrapedResume',
]


class SoftDeleteGuardTest(TestCase):
    def test_c_models_have_deleted_at_and_filtering_manager(self):
        for label in C_MODELS:
            app, name = label.split('.')
            model = apps.get_model(app, name)
            with self.subTest(model=label):
                # 1) 字段存在
                field_names = [f.name for f in model._meta.get_fields()]
                self.assertIn('deleted_at', field_names,
                              f"{label}: 缺少 deleted_at 字段")

                # 2) 默认管理器过滤软删 (WHERE 含 "deleted_at IS NULL", 而非仅 SELECT 列)
                default_sql = str(model._default_manager.get_queryset().query)
                self.assertRegex(default_sql, r'deleted_at.{0,12}IS NULL',
                                f"{label}: 默认管理器未做 deleted_at IS NULL 过滤 (疑似假绿)")

                # 3) all_objects 不过滤 (WHERE 不含 deleted_at IS NULL, 可访问已删)
                all_sql = str(model.all_objects.get_queryset().query)
                self.assertNotRegex(all_sql, r'deleted_at.{0,12}IS NULL',
                                    f"{label}: all_objects 不应过滤 deleted_at")

                # 4) 软删方法可用
                self.assertTrue(hasattr(model, 'soft_delete'),
                                f"{label}: 缺少 soft_delete() 方法")
                self.assertTrue(hasattr(model, 'restore'),
                                f"{label}: 缺少 restore() 方法")

    def test_school_soft_delete_excluded_from_default_manager(self):
        from apps.library.models import School

        s = School.objects.create(
            id='GUARD_SCH_001', name='守卫测试院校', code='GUARD_CODE_001')
        # 未删: 默认管理器可见
        self.assertIn(s, School.objects.all())

        # 软删
        s.soft_delete()

        # 已删: 默认管理器不可见 (假绿检测核心)
        self.assertNotIn(s, School.objects.all())
        # 已删: all_objects 仍可见
        self.assertIn(s, School.all_objects.all())

        # 恢复: 默认管理器重新可见
        restored = School.all_objects.get(pk='GUARD_SCH_001')
        restored.restore()
        self.assertIn(restored, School.objects.all())
