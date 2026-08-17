from django.apps import AppConfig


class DictionaryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dictionary'
    verbose_name = '数据字典'

    def ready(self):
        from django.db.models.signals import post_migrate
        from apps.dictionary.registry import run_dictionary_seeds

        post_migrate.connect(lambda **kwargs: run_dictionary_seeds(), sender=self)
