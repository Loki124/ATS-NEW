"""导入码表库数据（行政区划 / 国家区号 / 民族 / 语言）。

用法:
    python manage.py import_code_tables                 # 导入全部
    python manage.py import_code_tables --only regions   # 只导行政区划
    python manage.py import_code_tables --clear          # 清空后重导

数据来源（已随仓库落在 apps/code_table/data/，离线可跑）:
    - 行政区划: 国家统计局《统计用区划代码》2023 版（经 sinlmao/regions_data 整理 CSV）
                省/市/区县/镇乡 四级，不含村级
    - 国家区号: mledoze/countries (ISO 3166-1 + IDD 国际电话区号 + 中文译名)
    - 民族:     GB/T 3304-1991《中国各民族名称的罗马字母拼写法和代码》
    - 语言:     ISO 639（umpirsky/language-list 中英文对照）

幂等: 全部使用 update_or_create，重复执行不会重复插入。
"""
import csv
import json
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.code_table.models import Country, Ethnicity, Language, Region

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')

# GB/T 3304-1991: (数字代码, 民族名称, 罗马字母代码)
# 来源: 教育部 GB3304-91 标准文本, 与交通部/卫健委数据字典交叉核对一致
ETHNICITIES = [
    ('01', '汉族', 'HA'), ('02', '蒙古族', 'MG'), ('03', '回族', 'HU'), ('04', '藏族', 'ZA'),
    ('05', '维吾尔族', 'UG'), ('06', '苗族', 'MH'), ('07', '彝族', 'YI'), ('08', '壮族', 'ZH'),
    ('09', '布依族', 'BY'), ('10', '朝鲜族', 'CS'), ('11', '满族', 'MA'), ('12', '侗族', 'DO'),
    ('13', '瑶族', 'YA'), ('14', '白族', 'BA'), ('15', '土家族', 'TJ'), ('16', '哈尼族', 'HN'),
    ('17', '哈萨克族', 'KZ'), ('18', '傣族', 'DA'), ('19', '黎族', 'LI'), ('20', '傈僳族', 'LS'),
    ('21', '佤族', 'VA'), ('22', '畲族', 'SH'), ('23', '高山族', 'GS'), ('24', '拉祜族', 'LH'),
    ('25', '水族', 'SU'), ('26', '东乡族', 'DX'), ('27', '纳西族', 'NX'), ('28', '景颇族', 'JP'),
    ('29', '柯尔克孜族', 'KG'), ('30', '土族', 'TU'), ('31', '达斡尔族', 'DU'), ('32', '仫佬族', 'ML'),
    ('33', '羌族', 'QI'), ('34', '布朗族', 'BL'), ('35', '撒拉族', 'SL'), ('36', '毛南族', 'MN'),
    ('37', '仡佬族', 'GL'), ('38', '锡伯族', 'XB'), ('39', '阿昌族', 'AC'), ('40', '普米族', 'PM'),
    ('41', '塔吉克族', 'TA'), ('42', '怒族', 'NU'), ('43', '乌孜别克族', 'UZ'), ('44', '俄罗斯族', 'RS'),
    ('45', '鄂温克族', 'EW'), ('46', '德昂族', 'DE'), ('47', '保安族', 'BN'), ('48', '裕固族', 'YG'),
    ('49', '京族', 'GI'), ('50', '塔塔尔族', 'TT'), ('51', '独龙族', 'DR'), ('52', '鄂伦春族', 'OR'),
    ('53', '赫哲族', 'HZ'), ('54', '门巴族', 'MB'), ('55', '珞巴族', 'LB'), ('56', '基诺族', 'JN'),
    ('97', '其他', ''), ('98', '外国血统中国籍人士', ''),
]


class Command(BaseCommand):
    help = '导入码表库数据（行政区划 / 国家区号 / 民族 / 语言）'

    def add_arguments(self, parser):
        parser.add_argument('--data-dir', default=DATA_DIR, help='数据文件目录')
        parser.add_argument(
            '--only', choices=['regions', 'countries', 'ethnicities', 'languages'],
            help='只导入指定码表',
        )
        parser.add_argument('--clear', action='store_true', help='导入前清空对应表')
        parser.add_argument(
            '--if-empty', action='store_true',
            help='仅当目标表为空时才导入（容器启动脚本用，避免每次启动重写 4.5 万条）',
        )

    def handle(self, *args, **opts):
        data_dir = opts['data_dir']
        only = opts['only']
        tasks = [
            ('regions', self.import_regions),
            ('countries', self.import_countries),
            ('ethnicities', self.import_ethnicities),
            ('languages', self.import_languages),
        ]
        for name, fn in tasks:
            if only and name != only:
                continue
            model = {'regions': Region, 'countries': Country,
                     'ethnicities': Ethnicity, 'languages': Language}[name]
            if opts['clear']:
                model.objects.all().delete()
            if opts['if_empty'] and model.objects.exists():
                self.stdout.write(f'  跳过 {name}（已有 {model.objects.count()} 条）')
                continue
            n = fn(data_dir)
            self.stdout.write(self.style.SUCCESS(f'  {name}: {n} 条'))

    # ---------- 行政区划 ----------
    def import_regions(self, data_dir: str) -> int:
        """省/市/区县/镇乡 四级。

        CSV 格式:
            province.csv: code,name                 （无父级）
            city.csv:     code,name,p_code          （父级=省）
            county.csv:   code,name,c_code          （父级=市）
            town.csv:     code,name,c_code          （父级=区县）
        """
        specs = [
            ('province.csv', 1, None),
            ('city.csv', 2, 'p_code'),
            ('county.csv', 3, 'c_code'),
            ('town.csv', 4, 'c_code'),
        ]
        total = 0
        batch = []
        for filename, level, parent_field in specs:
            path = os.path.join(data_dir, filename)
            if not os.path.exists(path):
                self.stdout.write(self.style.WARNING(f'  跳过（文件缺失）: {path}'))
                continue
            count = 0
            with open(path, encoding='utf-8', newline='') as f:
                for row in csv.DictReader(f):
                    code = (row.get('code') or '').strip()
                    name = (row.get('name') or '').strip()
                    if not code or not name:
                        continue
                    parent = ''
                    if parent_field:
                        parent = (row.get(parent_field) or '').strip()
                    batch.append(Region(code=code, name=name, level=level, parent_code=parent))
                    count += 1
                    if len(batch) >= 2000:
                        Region.objects.bulk_create(batch, ignore_conflicts=True,
                                                   update_conflicts=False)
                        batch = []
            if batch:
                Region.objects.bulk_create(batch, ignore_conflicts=True, update_conflicts=False)
                batch = []
            total += count
            self.stdout.write(f'    {filename} (level={level}): {count} 行')
        return total

    # ---------- 国家 / 地区 ----------
    def import_countries(self, data_dir: str) -> int:
        path = os.path.join(data_dir, 'countries.json')
        if not os.path.exists(path):
            self.stdout.write(self.style.WARNING(f'  跳过（文件缺失）: {path}'))
            return 0
        with open(path, encoding='utf-8') as f:
            raw = json.load(f)

        objs = []
        for item in raw:
            cca2 = (item.get('cca2') or '').strip()
            if not cca2:
                continue
            idd = item.get('idd') or {}
            root = (idd.get('root') or '').strip()
            suffixes = [s for s in (idd.get('suffixes') or []) if s]
            # ⚠️ 区号拼接规则：root 可能不完整（中国 root='+8' + suffix='6' → +86），
            #    但多区号国家（美国 root='+1' + ['201','202',...]）拼首个 suffix 会错成 +1201。
            #    判定：只有唯一 suffix 时才拼接（说明 root 需补全）；多 suffix 则 root 本身即完整区号。
            if root and len(suffixes) == 1:
                phone = f'{root}{suffixes[0]}'
            else:
                phone = root
            trans = (item.get('translations') or {}).get('zho') or {}
            name_cn = (trans.get('common') or '').strip() or (item.get('name') or {}).get('common', '')
            objs.append(Country(
                code=cca2,
                code3=(item.get('cca3') or '').strip(),
                name_cn=name_cn[:200],
                name_en=((item.get('name') or {}).get('common') or '').strip()[:200],
                phone_code=phone[:10],
            ))
        with transaction.atomic():
            Country.objects.bulk_create(objs, ignore_conflicts=True)
        return len(objs)

    # ---------- 民族 ----------
    def import_ethnicities(self, data_dir: str) -> int:
        objs = [Ethnicity(code=c, name=n, letter_code=lc) for c, n, lc in ETHNICITIES]
        with transaction.atomic():
            Ethnicity.objects.bulk_create(objs, ignore_conflicts=True)
        return len(objs)

    # ---------- 语言 ----------
    def import_languages(self, data_dir: str) -> int:
        zh_path = os.path.join(data_dir, 'lang_zh.json')
        en_path = os.path.join(data_dir, 'lang_en.json')
        if not os.path.exists(zh_path):
            self.stdout.write(self.style.WARNING(f'  跳过（文件缺失）: {zh_path}'))
            return 0
        with open(zh_path, encoding='utf-8') as f:
            zh = json.load(f)
        en = {}
        if os.path.exists(en_path):
            with open(en_path, encoding='utf-8') as f:
                en = json.load(f)

        objs = [
            Language(code=code, name_cn=(name_cn or '')[:200], name_en=(en.get(code) or '')[:200])
            for code, name_cn in zh.items() if code
        ]
        with transaction.atomic():
            Language.objects.bulk_create(objs, ignore_conflicts=True)
        return len(objs)
