"""导入阳光高考专业库 CSV 到 Major 表。

用法:
    python manage.py import_majors
    python manage.py import_majors --file /path/to/院校专业库（阳光高考）-工作表1.csv
    python manage.py import_majors --clear           # 清空后重导

CSV 列（首行为表头，次行为中文说明行，需跳过）:
    specId, 专业代码, 专业名称, 学历层次, 学历层次代码, 门类, 门类代码,
    专业类, 专业类代码, 数据年份, 专业介绍, 详情URL

幂等: 以 spec_id 为唯一键，重复执行会更新而非重复插入。
"""
import csv
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.library.models import Major

DEFAULT_FILE = os.path.expanduser(
    '~/Downloads/院校专业库（阳光高考）-工作表1.csv'
)

# CSV 表头 → 模型字段
FIELD_MAP = {
    'specId': 'spec_id',
    '专业代码': 'code',
    '专业名称': 'name',
    '学历层次': 'education_level',
    '学历层次代码': 'education_level_code',
    '门类': 'discipline',
    '门类代码': 'discipline_code',
    '专业类': 'category',
    '专业类代码': 'category_code',
    '数据年份': 'data_year',
    '专业介绍': 'intro',
    '详情URL': 'detail_url',
}

MAX_LEN = {
    'spec_id': 64, 'code': 50, 'name': 200, 'education_level': 50,
    'education_level_code': 20, 'discipline': 100, 'discipline_code': 20,
    'category': 100, 'category_code': 20, 'data_year': 10, 'detail_url': 500,
}


class Command(BaseCommand):
    help = '导入阳光高考专业库 CSV'

    def add_arguments(self, parser):
        parser.add_argument('--file', default=DEFAULT_FILE, help='CSV 文件路径')
        parser.add_argument('--clear', action='store_true', help='导入前清空 Major 表')

    def handle(self, *args, **opts):
        path = opts['file']
        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f'文件不存在: {path}'))
            return

        if opts['clear']:
            n, _ = Major.all_objects.all().delete()
            self.stdout.write(f'已清空 Major 表（{n} 条）')

        created = updated = skipped = 0
        with open(path, encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                spec_id = (row.get('specId') or '').strip()
                # 跳过次行的中文说明行（specId = '数据源网站的唯一ID'）与空行。
                # ⚠️ 不能用 isdigit(): specId 既有纯数字也有字母数字混合（如 gt1f9b0av6cwkk37）。
                #    判定合法: 仅 ASCII 字母/数字; 说明行含中文 → isascii() 为 False。
                if not spec_id or not (spec_id.isascii() and spec_id.isalnum()):
                    skipped += 1
                    continue

                defaults = {}
                for csv_col, field in FIELD_MAP.items():
                    if field == 'spec_id':
                        continue
                    value = (row.get(csv_col) or '').strip()
                    limit = MAX_LEN.get(field)
                    if limit and value:
                        value = value[:limit]
                    defaults[field] = value

                obj, was_created = Major.all_objects.update_or_create(
                    spec_id=spec_id, defaults=defaults,
                )
                created += was_created
                updated += not was_created

        self.stdout.write(self.style.SUCCESS(
            f'导入完成: 新增 {created} / 更新 {updated} / 跳过 {skipped}'
        ))
        self.stdout.write(f'当前 Major 总数: {Major.objects.count()}')
