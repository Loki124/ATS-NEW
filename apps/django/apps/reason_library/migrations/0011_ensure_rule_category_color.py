"""0011_ensure_rule_category_color: 兜底补 rule_category.color 列。

背景（与 0006 / 0010_ensure 同源的 schema 漂移）:
- color 字段由本迁移之前的某次改动下沉进 0001 CreateModel
  （因 0002 seed_initial_data 用「真实模型」RuleCategory.objects.get_or_create
   建分类，若 color 不在 0001 CreateModel 则全新库 migrate 在 0002 即失败：
   INSERT 引用不存在的 color 列）。
- 后果：在「下沉之后」才建/迁移的库（如生产 / 较早的 dev 库）
  只跑了更早的迁移链，rule_category 物理上可能没有 color 列。
- SceneRule 列表/详情 / 向导保存会读写 rule_category.color，缺失列 →
  MySQL 抛 'Unknown column' → DRF 返回 HTTP 500。

本迁移排在链尾（依赖 0010），运行时自检：
- 列已存在（全新库 0001 已建 / dev 已建）→ 全程 no-op，绝对安全；
- 列缺失（漂移的生产库）→ 加 VARCHAR(16) NOT NULL DEFAULT ''，
  使其与模型（CharField(max_length=16, blank=True, default='')）一致。

幂等 + 与既有列定义完全一致，可在任意环境重复 migrate。
"""
from django.db import migrations


def _ensure_color_column(apps, schema_editor):
    # 与 0006 / 0010_ensure 同策略：MySQL 专有语法自检补列；非 MySQL
    # （SQLite 测试库）直接 no-op，避免 information_schema 不存在导致
    # migrate 全量失败。
    if schema_editor.connection.vendor != 'mysql':
        return

    cur = schema_editor.connection.cursor()
    try:
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = 'rule_category' AND column_name = 'color'"
        )
        if cur.fetchone():
            return  # 已存在 → 跳过

        # 与 Django 对 CharField(max_length=16, default='') 在 MySQL 上的
        # DDL 保持一致：VARCHAR(16) NOT NULL DEFAULT ''。
        cur.execute(
            "ALTER TABLE rule_category "
            "ADD COLUMN color VARCHAR(16) NOT NULL DEFAULT ''"
        )
    finally:
        cur.close()


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0010_ensure_scene_rule_max_selectable_tags'),
    ]

    operations = [
        migrations.RunPython(
            _ensure_color_column, migrations.RunPython.noop
        ),
    ]
