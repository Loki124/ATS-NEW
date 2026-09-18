from django.apps import AppConfig


class ChannelConfig(AppConfig):
    name = 'apps.channel'
    verbose_name = '渠道管理'

    def ready(self):
        from apps.dictionary.registry import register_dictionary_seed
        from apps.channel.seeds import (
            seed_application_channel_type,
            seed_resume_source_type,
        )

        register_dictionary_seed(seed_application_channel_type)
        register_dictionary_seed(seed_resume_source_type)
