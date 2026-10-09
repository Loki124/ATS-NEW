from django.db import migrations

# 2026-10-09 (#38 方案 A): 为 application.code 的 FULLTEXT 路径建索引。
# 仅 MySQL 生效。


def add_fulltext(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    tbl = apps.get_model('application', 'Application')._meta.db_table
    with schema_editor.connection.cursor() as cur:
        try:
            cur.execute(f'CREATE FULLTEXT INDEX ft_application_code ON {tbl} (code) WITH PARSER ngram')
        except Exception:
            pass  # 索引已存在则忽略


def remove_fulltext(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    tbl = apps.get_model('application', 'Application')._meta.db_table
    with schema_editor.connection.cursor() as cur:
        try:
            cur.execute(f'DROP INDEX ft_application_code ON {tbl}')
        except Exception:
            pass


class Migration(migrations.Migration):
    dependencies = [('application', '0006_application_idx_application_state_grab_and_more')]
    operations = [migrations.RunPython(add_fulltext, remove_fulltext)]
