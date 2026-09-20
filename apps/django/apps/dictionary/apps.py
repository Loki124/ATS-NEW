from django.apps import AppConfig


def _seed_dictionary_on_post_migrate(**kwargs):
    """post_migrate 回调：遍历注册表统一注入业务字典种子。

    必须用具名函数（而非 lambda）。Django 信号 connect 默认 weak=True，
    lambda 作为匿名临时对象在 ready() 返回后会被 GC，导致回调静默失效、
    字典种子（如 recruitment_stage_type 的 START_END 项）不再自动落库。
    具名函数由模块强引用，配合 weak=False 双保险。
    """
    from apps.dictionary.registry import run_dictionary_seeds
    run_dictionary_seeds()


class DictionaryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dictionary'
    verbose_name = '数据字典'

    def ready(self):
        from django.db.models.signals import post_migrate
        from apps.dictionary.registry import register_dictionary_seed

        # 业务枚举字典种子（学历/职位类别/招聘渠道/离职原因/合同类型）
        from apps.dictionary.seeds import (
            seed_education_type,
            seed_job_category_type,
            seed_recruit_channel_type,
            seed_offboard_reason_type,
            seed_contract_type_type,
        )

        register_dictionary_seed(seed_education_type)
        register_dictionary_seed(seed_job_category_type)
        register_dictionary_seed(seed_recruit_channel_type)
        register_dictionary_seed(seed_offboard_reason_type)
        register_dictionary_seed(seed_contract_type_type)

        post_migrate.connect(_seed_dictionary_on_post_migrate, sender=self, weak=False)
