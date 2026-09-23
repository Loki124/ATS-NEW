"""0006_ensure_reason_tag_code: 兜底补 reason_tag.code 列。

背景（schema 漂移）:
- 早期 0006 曾真正为 reason_tag 加 code 列 + 预置数据（当时登记名
  '0006_reason_code_and_preset_data'）。
- 后为修复「全新库 0002 seed 用真实模型含 code → SELECT code 失败」，
  将 code 下沉进 0001 CreateModel，并把 0006 改名成 0006_add_reason_tag_code
  且改为空 noop 占位（仅维持 dev 库迁移链完整）。
- 后果：在「改名之后」才建/迁移的库（如生产）只跑了空 noop →
  reason_tag 物理上没有 code 列 → 0007 的 INSERT 引用 code 直接
  'Unknown column' 失败，且 0007 排在后面，单纯新增靠后的迁移救不了。

本迁移放在 0006 之后、0007 之前，运行时自检：
- code 列已存在（全新库 0001 已建 / dev 已建）→ 全程 no-op，绝对安全；
- code 列缺失（漂移的生产库）→ 加可空列 → 回填唯一 code → 补唯一索引
  → 置 NOT NULL，使其与模型（unique=True, editable=False）一致。

幂等 + 与既有列定义完全一致，可在任意环境重复 migrate。
"""
from django.db import migrations


def _ensure_code_column(apps, schema_editor):
    from nanoid import generate as nanoid_generate

    cur = schema_editor.connection.cursor()
    try:
        # 1) 列是否已存在（全新库 / dev 已建 → 跳过加列）
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = 'reason_tag' AND column_name = 'code'"
        )
        if not cur.fetchone():
            # MySQL 不支持 ADD COLUMN IF NOT EXISTS，先加可空列以便回填
            cur.execute("ALTER TABLE reason_tag ADD COLUMN code VARCHAR(24) NULL")

        # 2) 回填缺失 code（模型 save() 生成 'R' + base36(11)，保持同型）
        cur.execute("SELECT id FROM reason_tag WHERE code IS NULL OR code = ''")
        missing = [r[0] for r in cur.fetchall()]
        for rid in missing:
            while True:
                c = 'R' + nanoid_generate('0123456789abcdefghijklmnopqrstuvwxyz', size=11)
                cur.execute("SELECT 1 FROM reason_tag WHERE code = %s LIMIT 1", [c])
                if not cur.fetchone():
                    break
            cur.execute("UPDATE reason_tag SET code = %s WHERE id = %s", [c, rid])

        # 3) 唯一索引（全新库 0001 已建 → 跳过，避免重名/重复建）
        cur.execute(
            "SELECT 1 FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() "
            "AND table_name = 'reason_tag' AND column_name = 'code' AND non_unique = 0 "
            "LIMIT 1"
        )
        if not cur.fetchone():
            cur.execute("ALTER TABLE reason_tag ADD UNIQUE INDEX uq_reason_tag_code (code)")

        # 4) 置 NOT NULL（回填后无空值；已是非空则 ALTER 为 no-op）
        cur.execute("SELECT COUNT(*) FROM reason_tag WHERE code IS NULL OR code = ''")
        if cur.fetchone()[0] == 0:
            cur.execute("ALTER TABLE reason_tag MODIFY code VARCHAR(24) NOT NULL")
    finally:
        cur.close()


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0006_add_reason_tag_code'),
    ]

    operations = [
        migrations.RunPython(_ensure_code_column, migrations.RunPython.noop),
    ]
