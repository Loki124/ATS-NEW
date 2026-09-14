"""导入院校库（apps/library/data/院校库.xlsx）。

用法::

    python manage.py import_schools                 # 读内置 data/院校库.xlsx
    python manage.py import_schools --file a.xlsx   # 指定文件
    python manage.py import_schools --clear         # 导入前清空 School 表
    python manage.py import_schools --if-empty      # 表非空则跳过（容器启动用）

幂等：以「院校名」为键 update_or_create，重复执行只更新不重复插入。

--------------------------------------------------------------------------
曾用名规范（2026-09-15 定，改动前先读，别拍脑袋拆括号）
--------------------------------------------------------------------------
源文件 2745 条里带括号的有 14 条，但**只有 3 条是真·更名关系**：

1. 显式标注：``嘉兴大学(原名嘉兴学院)``、``山东航空学院(原滨州学院)``
   → 主名取括号前，括号内（去掉「原名/原」）即曾用名。
2. 撞码推断：两条不同校名共用同一 institution_code → 同一所学校更名前后。
   实例：``山东第二医科大学(潍坊医学院)`` 与独立的 ``潍坊医学院`` 同为
   4137010438，合并为一条；主名里的旧名括号会被剥离，最终主名
   ``山东第二医科大学``、曾用名 ``潍坊医学院``。
3. **括号是校区/地名的一律不拆**：``大连理工大学(盘锦校区)``、
   ``中国矿业大学(北京)``、``中国地质大学(武汉)``、``哈尔滨工业大学(威海)``…
   这些是独立法人、院校代码不同，括号是校名的一部分。误拆会把两所不同的
   大学合成一所，属于数据事故。

--------------------------------------------------------------------------
其它清洗要点（源自真实文件）
--------------------------------------------------------------------------
1. 脏值 ``#N/A``（Excel 公式未命中）、``——``（占位符）一律转空串。
2. ``institution_code`` 有 56 行为空（含撞码合并后留下的孤儿），code 字段
   UNIQUE，故空值/冲突值统一生成 ``AUTO<md5(name)前12位>`` 的合成码，不丢记录。
3. 「办学地区」形如 ``青海-海东`` 或 ``广西``，按首个 '-' 拆 province / city。
4. 「校准标签」源数据用反斜杠分隔，统一规范化为 '|' 分隔入库。
"""
import hashlib
import os
import re
from collections import OrderedDict, defaultdict

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

# 曾用名显式标注：XX(原名YY) / XX(原YY)。非此格式的括号一律视为校名的一部分。
FORMER_NAME_RE = re.compile(r'^(?P<main>.+?)[（(]\s*原(?:名)?\s*(?P<old>[^）)]+?)\s*[）)]$')
# 撞码合并时用于剥离主名里的旧名括号：XX(YY) 且 YY 确为另一条记录的校名
PAREN_RE = re.compile(r'^(?P<main>.+?)[（(](?P<paren>[^）)]*)[）)]$')


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


def parse_name(raw: str):
    """按「曾用名规范」拆分校名，返回 (主名, 曾用名列表)。

    仅识别显式标注的 ``原名/原``；校区、地名括号保持原样。
    """
    m = FORMER_NAME_RE.match(raw)
    if m:
        old = m.group('old').strip()
        return m.group('main').strip(), [old] if old else []
    return raw, []


def join_former(names) -> str:
    """去重去空后按 '|' 连接，保持传入顺序。"""
    return '|'.join(OrderedDict.fromkeys(n.strip() for n in names if n and n.strip()))


class Command(BaseCommand):
    help = '导入院校库 xlsx（院校名唯一，幂等；含曾用名规范与撞码合并）'

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
        if 'school_name' not in idx:
            self.stdout.write(self.style.ERROR(f'缺列 school_name，实际表头: {header}'))
            return

        def cell(row, key):
            i = idx.get(key)
            return clean(row[i]) if i is not None and i < len(row) else ''

        # ===== 第一遍：解析成内存记录 =====
        records = []
        renamed_away = set()  # 因拆曾用名而作废的旧校名（需从库中删除）
        for row in rows[1:]:
            raw_name = cell(row, 'school_name')
            if not raw_name:
                continue
            name, formers = parse_name(raw_name)
            if name != raw_name:
                renamed_away.add(raw_name)
            province, city = split_area(cell(row, 'area'))
            records.append({
                'name': name,
                'code': cell(row, 'code'),
                'education_level': cell(row, 'education_level'),
                'school_type': cell(row, 'type'),
                'school_category': cell(row, 'nature'),
                'affiliated_to': cell(row, 'affiliated_to'),
                'province': province,
                'city': city,
                'location': cell(row, 'address'),
                'tags': norm_tags(cell(row, 'tags')),
                'former_names': list(formers),
            })

        # ===== 第二遍：按院校代码合并更名前后的两条记录 =====
        groups = defaultdict(list)
        no_code = []
        for r in records:
            (groups[r['code']] if r['code'] else no_code).append(r)

        merged = list(no_code)
        absorbed = set()  # 被并入主记录的旧校名（对应的独立行需删除）
        for code, group in groups.items():
            if len(group) == 1:
                merged.append(group[0])
                continue
            # 主记录：名字未被同组其它记录标为曾用名的那条
            former_union = set()
            for r in group:
                former_union.update(r['former_names'])
            primaries = [r for r in group if r['name'] not in former_union]
            if not primaries:
                # 无显式标注：取信息更全的一条（地址长 + 标签多 + 名长），保证结果稳定
                primaries = [max(group, key=lambda r: (len(r['location']), len(r['tags']), r['name']))]
            primary = primaries[0]
            for r in group:
                if r is primary:
                    continue
                absorbed.add(r['name'])
                primary['former_names'].append(r['name'])
                primary['former_names'].extend(r['former_names'])
                # 主记录缺的字段用被合并记录补齐（后者可能是信息更全的那条）
                for f in ('location', 'province', 'city', 'school_type', 'school_category',
                          'affiliated_to', 'education_level', 'tags'):
                    if not primary[f] and r[f]:
                        primary[f] = r[f]
            merged.append(primary)
            self.stdout.write(
                f'  合并同码 {code}: ' + '、'.join(r['name'] for r in group)
                + f' → 主记录「{primary["name"]}」'
            )

        # 撞码合并后：若主名括号内容正好是被合并掉的旧校名（如
        # 「山东第二医科大学(潍坊医学院)」+「潍坊医学院」同码），剥离括号，
        # 让主名回归「山东第二医科大学」，旧名进曾用名。
        for r in merged:
            m = PAREN_RE.match(r['name'])
            if m and m.group('paren').strip() in absorbed:
                old = m.group('paren').strip()
                renamed_away.add(r['name'])
                r['name'] = m.group('main').strip()
                r['former_names'].append(old)
                self.stdout.write(f'  剥离旧名括号: 「{m.group("main").strip()}({old})」→「{m.group("main").strip()}」')

        created = updated = 0
        seen_codes = set()

        def resolve_code(name: str, raw_code: str) -> str:
            """返回可用的唯一 code：空码/本轮撞码/库中已被他人占用 → 合成码。"""
            nonlocal seen_codes
            code = raw_code
            if not code or code in seen_codes:
                code = synth_code(name)
            while School.all_objects.filter(code=code).exclude(name=name).exists() or code in seen_codes:
                code = synth_code(name + code)
            seen_codes.add(code)
            return code

        with transaction.atomic():
            # 先删旧记录再 upsert：否则被作废的旧行仍占着真实院校代码，
            # 会让主记录在 resolve_code 里误判为撞码而退化成 AUTO 合成码。
            stale = (absorbed | renamed_away) - {r['name'] for r in merged}
            if stale:
                deleted, _ = School.all_objects.filter(name__in=stale).delete()
                self.stdout.write(f'  已删除被合并 / 作废的旧记录 {deleted} 条: {sorted(stale)}')

            for r in merged:
                r['former_names'] = join_former(
                    [n for n in r['former_names'] if n != r['name']]
                )
                defaults = {k: r[k] for k in (
                    'education_level', 'school_type', 'school_category', 'affiliated_to',
                    'province', 'city', 'location', 'tags', 'former_names',
                )}
                defaults['code'] = resolve_code(r['name'], r['code'])
                defaults['status'] = 'ACTIVE'
                _, is_new = School.all_objects.update_or_create(name=r['name'], defaults=defaults)
                created += int(is_new)
                updated += int(not is_new)

        self.stdout.write(self.style.SUCCESS(
            f'导入完成: 新增 {created} / 更新 {updated} / 合并 {len(absorbed)}'
        ))
        self.stdout.write(self.style.SUCCESS(f'School 总数: {School.objects.count()}'))
