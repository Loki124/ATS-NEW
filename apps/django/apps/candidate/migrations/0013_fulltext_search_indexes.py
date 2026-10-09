from django.db import migrations

# 2026-10-09 (#38 方案 A): 为 keyword_q 的 FULLTEXT 路径建索引。
# 仅 MySQL 生效（SQLite/Postgres 不支持 FULLTEXT，且 CI 测试库已是 MySQL 8）。
_COLS = [
    ('ft_candidate_name', 'name'),
    ('ft_candidate_phone', 'phone'),
    ('ft_candidate_email', 'email'),
    ('ft_candidate_current_company', 'current_company'),
]


def add_fulltext(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    tbl = apps.get_model('candidate', 'Candidate')._meta.db_table
    with schema_editor.connection.cursor() as cur:
        for idx, col in _COLS:
            try:
                # ngram 解析器：MySQL 默认 FULLTEXT 按空白切词，无法索引中文；
                # 候选人姓名多为中文，必须用 ngram 才能召回。
                cur.execute(f'CREATE FULLTEXT INDEX {idx} ON {tbl} ({col}) WITH PARSER ngram')
            except Exception:
                pass  # 索引已存在则忽略


def remove_fulltext(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    tbl = apps.get_model('candidate', 'Candidate')._meta.db_table
    with schema_editor.connection.cursor() as cur:
        for idx, _ in _COLS:
            try:
                cur.execute(f'DROP INDEX {idx} ON {tbl}')
            except Exception:
                pass


class Migration(migrations.Migration):
    dependencies = [('candidate', '0012_candidate_archived_at_candidate_is_archived_and_more')]
    operations = [migrations.RunPython(add_fulltext, remove_fulltext)]
