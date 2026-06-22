"""验证 add_candidate app 正确注册到 Django"""
from django.apps import apps


def test_add_candidate_app_is_registered():
    """app 必须在 INSTALLED_APPS 中"""
    config = apps.get_app_config('add_candidate')
    assert config.name == 'apps.add_candidate'
    assert config.verbose_name == '候选人创建（V2）'


def test_affinda_settings_exist():
    """Affinda 配置必须存在"""
    from django.conf import settings
    assert hasattr(settings, 'AFFINDA_API_KEY')
    assert hasattr(settings, 'AFFINDA_BASE_URL')
    assert hasattr(settings, 'AFFINDA_WORKSPACE')
    assert hasattr(settings, 'AFFINDA_DOCUMENT_TYPE')
