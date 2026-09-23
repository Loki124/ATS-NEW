"""0010_ensure_scene_rule_max_selectable_tags: 兜底补 scene_rule.max_selectable_tags 列。

背景（与 0006_ensure 同源的 schema 漂移）:
- max_selectable_tags 曾由 0008_add_max_selectable_tags 真正加列。
- 后为修复「全新库 0002 seed 用真实模型含该列 → SELECT 失败」，
  将字段下沉进 0001 CreateModel，并把 0008 改成空 noop 占位
  （仅维持 dev 库迁移链完整）。
- 后果：在「下沉之后」才建/迁移的库（如生产）只跑了空 noop →
  scene_rule 物理上没有 max_selectable_tags 列。
- 而生产迁移链又卡在 0007（reason_tag.code 缺失，已由 0006_ensure 兜底），
  0008/0009 从未执行，于是该列在老库上彻底缺席。
- SceneRuleListSerializer 的 list 查询 SELECT 了 scene_rule.max_selectable_tags，
  生产库缺列 → MySQL 抛 'Unknown column' → DRF 返回 HTTP 500
  （即 /api/v1/reason-library/rules/ 500 的真实根因，区别于 cloudflare 的
  ERR_CONNECTION_RESET 噪音）。

本迁移排在链尾（依赖 0009），运行时自检：
- 列已存在（全新库 0001 已建 / dev 已建）→ 全程 no-op，绝对安全；
- 列缺失（漂移的生产库）→ 加 SMALLINT UNSIGNED NOT NULL DEFAULT 5，
  使其与模型（PositiveSmallIntegerField(default=5)）一致。

幂等 + 与既有列定义完全一致，可在任意环境重复 migrate。
"""
from django.db import migrations


def _ensure_max_selectable_tags_column(apps, schema_editor):
    # 与 0006_ensure 同策略：MySQL 专有语法自检补列；非 MySQL（SQLite 测试库）
    # 直接 no-op，避免 information_schema 不存在导致 migrate 全量失败。
    if schema_editor.connection.vendor != 'mysql':
        return

    cur = schema_editor.connection.cursor()
    try:
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = 'scene_rule' AND column_name = 'max_selectable_tags'"
        )
        if cur.fetchone():
            return  # 已存在 → 跳过

        # 生产 MySQL 9.6 支持 ADD COLUMN ... DEFAULT 的 instant DDL：
        # 一次性补齐列 + 默认值，存量行自动填 5（与模型 default 一致）。
        # 与 Django 对 PositiveSmallIntegerField 在 MySQL 上的 DDL 保持一致。
        cur.execute(
            "ALTER TABLE scene_rule "
            "ADD COLUMN max_selectable_tags SMALLINT UNSIGNED NOT NULL DEFAULT 5"
        )
    finally:
        cur.close()


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0009_remove_rulesceneassignment_uniq_scene_and_more'),
    ]

    operations = [
        migrations.RunPython(
            _ensure_max_selectable_tags_column, migrations.RunPython.noop
        ),
    ]
