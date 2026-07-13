"""V2 权限系统启动校验. 在 AppConfig.ready() 调用, 缺资源/缺模板/缺配置立即 ImproperlyConfigured."""
from django.core.exceptions import ImproperlyConfigured

REQUIRED_TEMPLATES = ['TMPL_ADMIN', 'TMPL_DIRECTOR', 'TMPL_SPECIALIST', 'TMPL_INTERVIEWER']
REQUIRED_TENANT_CONFIG_KEY = 'GLOBAL_DEFAULT_DATA_SCOPE'
MIN_RESOURCE_COUNT = 50


def bootstrap_permission_v2():
    """服务启动时由 AppConfig.ready() 调用. 缺一即 ImproperlyConfigured."""
    from .models_permission_v2 import PermissionResource, PermissionTemplate, TenantConfig
    # 1. 4 个系统模板必须存在
    missing = [t for t in REQUIRED_TEMPLATES if not PermissionTemplate.objects.filter(
        template_code=t, is_system=1, status=1).exists()]
    if missing:
        raise ImproperlyConfigured(f'V2 templates missing: {missing}')
    # 2. 资源总数 >= MIN_RESOURCE_COUNT
    cnt = PermissionResource.objects.filter(status=1).count()
    if cnt < MIN_RESOURCE_COUNT:
        raise ImproperlyConfigured(f'V2 resources only {cnt}, need >= {MIN_RESOURCE_COUNT}')
    # 3. 全局默认 scope 配置存在
    if not TenantConfig.objects.filter(
        config_key=REQUIRED_TENANT_CONFIG_KEY, system_code='recruit').exists():
        raise ImproperlyConfigured(f'tenant_config {REQUIRED_TENANT_CONFIG_KEY} missing')