"""导入院校库（apps/library/data/院校库.xlsx）。

用法::

    python manage.py import_schools                 # 读内置 data/院校库.xlsx
    python manage.py import_schools --file a.xlsx   # 指定文件
    python manage.py import_schools --clear         # 导入前清空 School 表
    python manage.py import_schools --if-empty      # 表非空则跳过（容器启动用）

幂等：以「院校名」为键 update_or_create，重复执行只更新不重复插入。

数据清洗要点（源自真实文件，别删）:
1. 脏值 ``#N/A``（Excel 公式未命中）、``——``（占位符）一律转空串。
2. ``institution_code`` 有 56 行为空、且有 1 组重复（潍坊医学院 / 山东第二医科大学
   是同一所学校更名前后的两条记录，共用一个代码）。code 字段 UNIQUE，故空值或
   冲突值统一生成 ``AUTO<md5(name)前12位>`` 的合成码，保证唯一且不丢记录。
3. 「办学地区」形如 ``青海-海东`` 或 ``广西``，按首个 '-' 拆 province / city。
4. 「校准标签」源数据用反斜杠分隔，统一规范化为 '|' 分隔入库。
"""
import hashlib
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.library.models import School

# 内置副本优先：生产部署机没有 ~/Desktop
DEFAULT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'data',
    '院校库.xlsx',
)
FALLBACK_FILE = os.path.expanduser('~/Desktop/院校库.xlsx')

# 表头兼容：英文键（当前文件）与中文键（人工另存时可能被改写）
ALIASES = {
    'school_name': ('school_name', '院校名称', '学校名称', '名称'),
    'education_level': ('education_level', '学历层次', '教育层次', '办学层次'),
    'code': ('institution_code', '院校代码', '学校代码', '代码'),
    'type': ('institution_type', '院校类型', '学校类型', '类型'),
    'nature': ('institution_nature', '办学性质', '院校性质', '性质'),
    'affiliated_to': ('affiliated_to', '主管部门', '隶属'),
    'area': ('办学地区', '地区', '所在地'),
    'address': ('详细地址', '地址'),
    'tags': ('校准标签', '标签', '院校标签'),
}

DIRTY = {'#N/A', '#N/A!', '——', '—', '-', '/', 'N/A', 'None', 'nan'}


def clean(v):
    """去空白 + 脏值转空串。"""
    if v is None:
        return ''
    s = str(v).strip()
    return '' if s in DIRTY else s


def split_area(area: str):
    """'青海-海东' -> ('青海', '海东')；'广西' -> ('广西', '')。"""
    if not area:
        return '', ''
    for sep in ('-', '－', '—', '–', '、'):
        if sep in area:
            p, _, c = area.partition(sep)
            return p.strip(), c.strip()
    return area, ''


def synth_code(name: str) -> str:
    """为无码 / 撞码院校生成稳定的合成码（同一校名永远得到同一个码）。"""
    return 'AUTO' + hashlib.md5(name.encode('utf-8')).hexdigest()[:12]


def norm_tags(raw: str) -> str:
    """'双高院校C档\\优质专科高职' -> '双高院校C档|优质专科高职'。"""
    parts = []
    for t in raw.replace('/', '|').replace('\\', '|').split('|'):
        t = t.strip()
        if t and t not in parts:
            parts.append(t)
    return '|'.join(parts)


class Command(BaseCommand):
    help = '导入院校库 xlsx（院校名唯一，幂等）'

    def add_arguments(self, parser):
        parser.add_argument('--file', default=None, help='xlsx 路径，默认读内置 data/院校库.xlsx')
        parser.add_argument('--clear', action='store_true', help='导入前清空 School 表')
        parser.add_argument('--if-empty', action='store_true', help='表非空则跳过导入')

    def handle(self, *args, **opts):
        path = opts['file'] or (DEFAULT_FILE if os.path.exists(DEFAULT_FILE) else FALLBACK_FILE)
        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f'文件不存在: {path}'))
            return

        if opts['if_empty'] and School.objects.exists():
            self.stdout.write(self.style.WARNING(f'跳过导入（School 已有 {School.objects.count()} 条）'))
            return

        if opts['clear']:
            School.all_objects.all().delete()
            self.stdout.write('已清空 School 表')

        import openpyxl

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            self.stdout.write(self.style.ERROR('空表'))
            return

        header = [clean(h) for h in rows[0]]
        idx = {}
        for key, names in ALIASES.items():
            for i, h in enumerate(header):
                if h in names:
                    idx[key] = i
                    break
        missing = [k for k in ('school_name',) if k not in idx]
        if missing:
            self.stdout.write(self.style.ERROR(f'缺列: {missing}，实际表头: {header}'))
            return

        def cell(row, key):
            i = idx.get(key)
            return clean(row[i]) if i is not None and i < len(row) else ''

        created = updated = skipped = 0
        seen_codes: set[str] = set()

        def resolve_code(name: str, raw_code: str) -> str:
            """返回可用的唯一 code：空码/本轮撞码/库中已被他人占用 -> 合成码。"""
            nonlocal seen_codes
            code = raw_code
            if not code or code in seen_codes:
                code = synth_code(name)
            while School.all_objects.filter(code=code).exclude(name=name).exists() or code in seen_codes:
                code = synth_code(name + code)
            seen_codes.add(code)
            return code

        with transaction.atomic():
            for row in rows[1:]:
                name = cell(row, 'school_name')
                if not name:
                    skipped += 1
                    continue
                province, city = split_area(cell(row, 'area'))
                defaults = {
                    'code': resolve_code(name, cell(row, 'code')),
                    'education_level': cell(row, 'education_level'),
                    'school_type': cell(row, 'type'),
                    'school_category': cell(row, 'nature'),
                    'affiliated_to': cell(row, 'affiliated_to'),
                    'province': province,
                    'city': city,
                    'location': cell(row, 'address'),
                    'tags': norm_tags(cell(row, 'tags')),
                    'status': 'ACTIVE',
                }
                obj, is_new = School.all_objects.update_or_create(name=name, defaults=defaults)
                # update_or_create 不会走自定义 save()，补 id
                if not obj.id:
                    obj.save()
                created += int(is_new)
                updated += int(not is_new)

        self.stdout.write(self.style.SUCCESS(
            f'导入完成: 新增 {created} / 更新 {updated} / 跳过 {skipped}'
        ))
        self.stdout.write(self.style.SUCCESS(f'School 总数: {School.objects.count()}'))
