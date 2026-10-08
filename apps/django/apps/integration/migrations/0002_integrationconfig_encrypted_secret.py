"""Fix 6: IntegrationConfig 新增 encrypted_secret 字段 (Fernet 加密存储敏感凭据).

老 config JSON 中敏感字段 (corp_secret / access_key_secret / password) 仍保留.
运维在管理界面更新 secret 后, 由 encrypt_migration 一次性把老 config 中的敏感字段加密
迁移到 encrypted_secret 字段. 之后从 config 取明文路径走 _get_decrypted_config.
"""
import json

from django.db import migrations, models


def encrypt_existing_secrets(apps, schema_editor):
    """把 IntegrationConfig.config 中已存在的敏感字段加密迁移到 encrypted_secret."""
    IntegrationConfig = apps.get_model('integration', 'IntegrationConfig')
    SENSITIVE = {
        'EMAIL': ['password', 'smtp_password'],
        'WECOM': ['corp_secret'],
        'MOKA': ['api_key', 'api_secret'],
        'SMS': ['access_key_secret'],
        'BACKGROUND_CHECK': ['api_key'],
    }
    # 跳过加密因为 INTEGRATION_FERNET_KEY 可能未配置 (migration 在全新环境跑)
    # 仅当 key 已配置才加密. 未配置时把明文保留在 config, 业务代码依旧能用 (兼容老部署).
    from django.conf import settings
    fernet_key = getattr(settings, 'INTEGRATION_FERNET_KEY', None)
    if not fernet_key:
        return
    from cryptography.fernet import Fernet
    fernet = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
    for cfg in IntegrationConfig.objects.all():
        keys = SENSITIVE.get(cfg.type, [])
        original = cfg.config or {}
        secret_dict = {}
        for k in keys:
            if k in original and original[k]:
                secret_dict[k] = original[k]
        if secret_dict:
            encrypted = fernet.encrypt(json.dumps(secret_dict).encode('utf-8')).decode('ascii')
            cfg.encrypted_secret = encrypted
            cfg.save(update_fields=['encrypted_secret', 'updated_at'])


def decrypt_existing_secrets(apps, schema_editor):
    """回滚: 不还原 (deleted_at 已软删足够)."""


class Migration(migrations.Migration):

    dependencies = [
        ('integration', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='integrationconfig',
            name='encrypted_secret',
            field=models.TextField(blank=True, help_text='JSON: {"corp_secret":"...", "access_key_secret":"..."} 加密后', verbose_name='加密凭据 (Fernet)'),
        ),
        migrations.RunPython(encrypt_existing_secrets, decrypt_existing_secrets),
    ]