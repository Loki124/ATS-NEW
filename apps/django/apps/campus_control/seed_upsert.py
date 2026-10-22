"""校招生模拟数据写入助手 —— 幂等 + 可改名升级。

⚠️ 写入策略铁律：**只增改，绝不删**（不做 wipe / 不调用 --force 重灌）。
理由：开发/演示库里除种子数据外，还可能有业务侧手工新建的维度/规则/人员
（实测 dev 库有 UI 手建的「身份证籍贯」维度 + 15 条规则），重灌会连带清掉。

匹配规则（按优先级）：
1. 命中 `name`（新姓名）→ 原地更新该行；
2. 命中 `legacy_name`（改名前的老姓名）→ **原地改名**并更新字段（不新建、不留旧名残影）；
3. 都没命中 → 新建一行（`code` 由 `Person.save()` 自动补 C+8 流水号）。

⇒ 模拟数据从「员工N」升级为真实姓名后，重跑 seed 命令即可把存量行改名补齐，
不会产生重复行，也不需要清库。
"""
from datetime import date

from apps.campus_control.models import Person

# 允许写入的字段白名单（其余字段一律不碰，避免误改业务字段）
_WRITABLE = (
    'bu', 'school', 'school_name', 'sex', 'major', 'month', 'status',
    'position', 'level', 'counted', 'employee_id', 'education', 'phone',
    'expected_entry_date', 'actual_entry_date',
)


def _as_date(v):
    """字符串/date → date；空值 → None。"""
    if not v:
        return None
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v))


def upsert_person_rows(rows: list[dict]) -> tuple[int, int]:
    """按「姓名 / 历史姓名」幂等写入人员行。

    :param rows: 每行至少含 name；可含 legacy_name 与 _WRITABLE 中的字段
                 （日期字段接受 'YYYY-MM-DD' 字符串或 date）
    :return: (新建数, 更新数)
    """
    created = updated = 0
    for row in rows:
        name = (row.get('name') or '').strip()
        if not name:
            continue
        legacy = (row.get('legacy_name') or '').strip() or None

        qs = Person.objects.filter(name=name)
        if legacy and legacy != name:
            qs = qs | Person.objects.filter(name=legacy)
        obj = qs.order_by('code').first()

        values = {k: row[k] for k in _WRITABLE if k in row}
        if 'expected_entry_date' in values:
            values['expected_entry_date'] = _as_date(values['expected_entry_date'])
        if 'actual_entry_date' in values:
            values['actual_entry_date'] = _as_date(values['actual_entry_date'])

        if obj is None:
            Person.objects.create(name=name, **values)
            created += 1
            continue

        # 原地更新：改到新姓名 + 覆盖白名单字段（未提供的字段保持原值）
        obj.name = name
        for k, v in values.items():
            setattr(obj, k, v)
        obj.save()
        updated += 1
    return created, updated
