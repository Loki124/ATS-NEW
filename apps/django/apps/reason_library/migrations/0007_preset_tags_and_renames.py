"""0007: 预置数据调整 (2026-09-21, 全部幂等, 重跑安全)。

1. 存量原因标签 type system → custom (排除下方 10 个预置标签名)。
2. 新增 10 个系统预置标签 (流程节点自动写入原因)。
3. 系统预置规则名称统一改为「预置默认规则」系列。
4. 清理挂在非末级分类上的标签绑定 (UI 不可见的历史脏数据, 也是
   TagPicker『已在当前规则中使用』误报的来源)。

用原生 SQL: historical model 不执行自定义 save(), id/code 需显式生成。
"""
from django.db import migrations
from django.utils import timezone

PRESET_TAGS = [
    ('已录用', 'Hired', ''),
    ('已离职', 'Resigned', ''),
    ('上传直接归档', 'Upload auto archived', ''),
    ('为候选人推荐了新职位', 'Recommended new job', ''),
    ('职位关闭自动归档', 'Job closed auto archived', ''),
    ('筛选不通过自动淘汰', 'Screen auto rejected', ''),
    ('加入黑名单', 'Blacklisted', ''),
    ('长时间未处理自动归档', 'Stale auto archived', ''),
    ('面试不通过自动淘汰', 'Interview auto rejected', ''),
    ('管控重复申请', 'Duplicate application blocked', ''),
]

_PRESET_NAMES = [n for n, _, _ in PRESET_TAGS]


def _gen_code(nanoid_generate):
    return 'R' + nanoid_generate('0123456789abcdefghijklmnopqrstuvwxyz', size=11)


def adjust(apps, schema_editor):
    cur = schema_editor.connection.cursor()
    try:
        from nanoid import generate as nanoid_generate
    except ImportError:  # pragma: no cover
        import random
        import string

        def nanoid_generate(alphabet=None, size=11):
            pool = alphabet or string.ascii_letters + string.digits
            return ''.join(random.choices(pool, k=size))

    # 1) 存量 system → custom (排除预置标签; 用 Django 标准 %s 占位符，由 backend 自动转 ?(SQLite)/%(MySQL))
    placeholders = ','.join('%s' for _ in _PRESET_NAMES)
    cur.execute(
        f"UPDATE reason_tag SET type = 'custom' WHERE type = 'system' AND name NOT IN ({placeholders})",
        _PRESET_NAMES,
    )

    # 2) 新增 10 个系统预置标签 (按 name 幂等)
    now = timezone.now()
    for name, en, tip in PRESET_TAGS:
        cur.execute("SELECT 1 FROM reason_tag WHERE name = %s LIMIT 1", [name])
        if cur.fetchone():
            continue
        cur.execute(
            "INSERT INTO reason_tag (id, name, en_name, tip, type, enabled, code, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, 'system', 1, %s, %s, %s)",
            [nanoid_generate(size=21), name, en, tip, _gen_code(nanoid_generate), now, now],
        )

    # 3) 系统规则改名 (name 唯一: 目标名被其他行占用则换下一个)
    #    2026-09-24: 仅「预置默认规则」一条 (兄弟规则 r-cancel/r-talent 已由 0012 删除),
    #    故 names 只保留单一默认名。
    cur.execute("SELECT id FROM scene_rule WHERE is_system = 1 ORDER BY created_at")
    rule_ids = [row[0] for row in cur.fetchall()]
    names = ['预置默认规则']
    for rid in rule_ids:
        target = None
        for n in list(names):
            cur.execute("SELECT 1 FROM scene_rule WHERE name = %s AND id != %s LIMIT 1", [n, rid])
            if not cur.fetchone():
                target = n
                break
        if target is None:
            continue
        cur.execute("UPDATE scene_rule SET name = %s WHERE id = %s", [target, rid])
        names.remove(target)

    # 4) 清理非末级分类上的绑定 (有子分类的分类即非末级)
    cur.execute(
        "DELETE FROM category_assignment WHERE category_id IN "
        "(SELECT id FROM rule_category WHERE parent_id IS NOT NULL AND parent_id != '')"
    )
    cur.close()


def reverse_adjust(apps, schema_editor):
    cur = schema_editor.connection.cursor()
    for name, _, _ in PRESET_TAGS:
        cur.execute("DELETE FROM reason_tag WHERE name = %s AND type = 'system'", [name])
    cur.close()


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0006_ensure_reason_tag_code'),
    ]

    operations = [
        migrations.RunPython(adjust, reverse_adjust),
    ]
