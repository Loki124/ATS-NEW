from django.apps import AppConfig


class ProcessConfig(AppConfig):
    name = 'apps.process'
    verbose_name = '招聘流程管理'

    def ready(self):
        from . import signals  # noqa
        from apps.dictionary.registry import register_dictionary_seed
        from apps.process.seeds import seed_recruitment_stage_type

        register_dictionary_seed(seed_recruitment_stage_type)
