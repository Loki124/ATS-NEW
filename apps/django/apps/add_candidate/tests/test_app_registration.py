"""验证 add_candidate app 正确注册到 Django"""
from django.apps import apps


def test_add_candidate_app_is_registered():
    """app 必须在 INSTALLED_APPS 中"""
    config = apps.get_app_config('add_candidate')
    assert config.name == 'apps.add_candidate'
    assert config.verbose_name == '候选人创建（V2）'


def test_resume_parser_settings_exist():
    """本地简历解析后端配置必须存在（替代原 Affinda）"""
    from django.conf import settings
    assert hasattr(settings, 'RESUME_PARSER_BACKEND')
    assert settings.RESUME_PARSER_BACKEND in ('career_core', 'smartresume')
    assert hasattr(settings, 'CAREER_CORE_BIN')
    assert hasattr(settings, 'SMARTRESUME_CLI')
    assert hasattr(settings, 'SMARTRESUME_PYTHON')
    assert hasattr(settings, 'RESUME_PARSER_TIMEOUT')
    assert isinstance(settings.RESUME_PARSER_TIMEOUT, int)
