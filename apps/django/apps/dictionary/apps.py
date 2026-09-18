from django.apps import AppConfig


class DictionaryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dictionary'
    verbose_name = '数据字典'

    def ready(self):
        from django.db.models.signals import post_migrate
        from apps.dictionary.registry import run_dictionary_seeds, register_dictionary_seed

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

        post_migrate.connect(lambda **kwargs: run_dictionary_seeds(), sender=self)
