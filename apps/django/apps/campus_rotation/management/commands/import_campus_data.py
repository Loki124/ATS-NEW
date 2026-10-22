"""校招轮岗数据迁移脚本（按冻结方案 §7，OQ-2 / OQ-3）。

设计原则
--------
- 不预置任何真实部门 / 人员 / 导师 / 平台实例（OQ-2）。本脚本是「后续真实数据接入
  通道」，默认无待迁移数据，运行即打印空报告、退出码 0。
- 幂等：`RotationResource`/`ClassRoom` 按业务唯一键 `resource_no` / `code` 走 `update_or_create`；
  `RotationArrangement` 按 `person_id + stage` 定位（先查后更或新建）。重复执行安全。
- 部门匹配：读入原型部门名 → 按 `Department.name` 精确匹配 ATS 部门；匹配不到**不新建
  假部门**，写入报告 `unmatched_depts[]` 由运营在 UI 手工建（OQ-2）。
- 导师 / 班主任 / 直属上级：按 `employee_id` / `username` 映射到 ATS `User`；映射不到
  记 `unmatched_users[]`，**不创建账号**（OQ-3）。

用法
----
    # 仅打印匹配报告，不落库
    python manage.py import_campus_data --dry-run

    # 带数据源落库（无真实数据前请勿使用；需显式指定 --source）
    python manage.py import_campus_data --source /path/to/data.json

    # 同时输出 JSON 报告到文件
    python manage.py import_campus_data --dry-run --json-report /tmp/report.json

数据源 JSON 结构见模块底部 `SAMPLE_DATA` 注释。字段采用原型语义名，脚本负责映射。
"""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.common.models import FullAuditModel  # noqa: F401  (确认抽象基类可达)


# ---------------------------------------------------------------------------
# 引用解析：部门 / 用户
# ---------------------------------------------------------------------------
class ReferenceResolver:
    """把原型里的部门名 / 人员标识解析成 ATS 对象，并收集匹配失败项。"""

    def __init__(self):
        self.unmatched_depts = []
        self.unmatched_users = []
        # 去重集合，避免报告里同一名字重复出现
        self._seen_dept = set()
        self._seen_user = set()

    def resolve_department(self, value):
        """按 name 精确匹配 Department；失败记 unmatched_depts，返回部门对象或 None。

        value 可以是：
          - 字符串：当作部门名精确匹配；
          - dict：优先 name，缺省回退 code。
        空值（None / ''）按「无需映射」返回 None，不入报告。
        """
        from apps.core.models import Department

        if value is None or value == '':
            return None

        name = code = None
        if isinstance(value, dict):
            name = (value.get('name') or '').strip() or None
            code = (value.get('code') or '').strip() or None
        else:
            name = str(value).strip() or None

        if not name and not code:
            return None

        dept = None
        if name:
            dept = Department.objects.filter(name=name).first()
        if dept is None and code:
            dept = Department.objects.filter(code=code).first()

        if dept is None:
            key = name or code
            if key not in self._seen_dept:
                self._seen_dept.add(key)
                self.unmatched_depts.append(key)
        return dept

    def resolve_user(self, value):
        """按 employee_id / username 映射到 User；失败记 unmatched_users，返回或 None。

        value 可以是：
          - dict：优先 employee_id，缺省回退 username；
          - 字符串：当作 username。
        空值按「无需映射」返回 None，不入报告。
        """
        from apps.core.models import User

        if value is None or value == '':
            return None

        employee_id = username = None
        if isinstance(value, dict):
            employee_id = (value.get('employee_id') or '').strip() or None
            username = (value.get('username') or '').strip() or None
        else:
            username = str(value).strip() or None

        if not employee_id and not username:
            return None

        user = None
        if employee_id:
            user = User.objects.filter(employee_id=employee_id).first()
        if user is None and username:
            user = User.objects.filter(username=username).first()

        if user is None:
            key = employee_id or username
            if key not in self._seen_user:
                self._seen_user.add(key)
                self.unmatched_users.append(key)
        return user


# ---------------------------------------------------------------------------
# 命令主体
# ---------------------------------------------------------------------------
class Command(BaseCommand):
    help = '校招轮岗数据迁移（§7，OQ-2/OQ-3）：幂等框架，支持 --dry-run 打印匹配报告不落库。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            dest='source',
            default=None,
            help='数据源 JSON 文件路径。不传则无待迁移数据（默认空运行）。',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='只打印匹配报告不落库（默认行为安全提示：未指定 --source 本就无写入）。',
        )
        parser.add_argument(
            '--json-report',
            dest='json_report',
            default=None,
            help='将报告以 JSON 形式写入指定路径（便于 CI / 运营复核）。',
        )

    # ---- 数据加载 ----
    def load_source(self, path):
        if not path:
            return {'resources': [], 'class_rooms': [], 'rotation_arrangements': []}
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f'读取数据源失败: {exc}')
        if not isinstance(data, dict):
            raise CommandError('数据源顶层必须是 JSON 对象（含 resources/class_rooms/rotation_arrangements）。')
        data.setdefault('resources', [])
        data.setdefault('class_rooms', [])
        data.setdefault('rotation_arrangements', [])
        return data

    # ---- 单模型 upsert ----
    def upsert_resource(self, resolver, item, stats, dry_run):
        from apps.campus_rotation.io_rotation_resource import (
            RESOURCE_TYPE_BY_LABEL,
            RESOURCE_TYPE_LABEL,
        )
        from apps.campus_rotation.models import RotationResource

        resource_no = (item.get('resource_no') or '').strip()
        if not resource_no:
            raise CommandError(f'RotationResource 缺少业务唯一键 resource_no: {item!r}')

        # 资源类型（直播间 / 客服部门 / 其他）—— 决定编号前缀与「平台」是否必填
        raw_type = (item.get('resource_type') or '').strip()
        resource_type = RESOURCE_TYPE_BY_LABEL.get(raw_type, raw_type)
        if resource_type not in RESOURCE_TYPE_LABEL:
            raise CommandError(
                f'RotationResource.resource_type 非法（须为 直播间 / 客服部门 / 其他）: {item!r}'
            )

        defaults = {
            'name': item.get('name', ''),
            'resource_type': resource_type,
            'department': resolver.resolve_department(item.get('department')),
            'bu': resolver.resolve_department(item.get('bu')),
            'mentor': resolver.resolve_user(item.get('mentor')),
            'platform': (item.get('platform') or '').strip() if resource_type == 'LIVE_ROOM' else '',
            'location': item.get('location', ''),
            'capacity': item.get('capacity'),
            'social_count': item.get('social_count', 0),
            'is_active': item.get('is_active', True),
            'remark': item.get('remark', ''),
        }
        if dry_run:
            # 预览：看是否已存在
            exists = RotationResource.objects.filter(resource_no=resource_no).exists()
            stats['resources']['would_update' if exists else 'would_create'] += 1
            stats['preview'].append({
                'model': 'RotationResource', 'key': resource_no,
                'action': 'update' if exists else 'create',
            })
            return
        obj, created = RotationResource.objects.update_or_create(
            resource_no=resource_no, defaults=defaults,
        )
        if created:
            stats['resources']['created'] += 1
        else:
            stats['resources']['updated'] += 1

    def upsert_class_room(self, resolver, item, stats, dry_run):
        from apps.campus_rotation.models import ClassRoom

        code = (item.get('code') or '').strip()
        if not code:
            raise CommandError(f'ClassRoom 缺少业务唯一键 code: {item!r}')

        defaults = {
            'name': item.get('name', ''),
            'head_teacher': resolver.resolve_user(item.get('head_teacher')),
            'hrbp': resolver.resolve_user(item.get('hrbp')),
            'batch': item.get('batch', ''),
            'remark': item.get('remark', ''),
        }
        if dry_run:
            exists = ClassRoom.objects.filter(code=code).exists()
            stats['class_rooms']['would_update' if exists else 'would_create'] += 1
            stats['preview'].append({
                'model': 'ClassRoom', 'key': code,
                'action': 'update' if exists else 'create',
            })
            return
        obj, created = ClassRoom.objects.update_or_create(code=code, defaults=defaults)
        if created:
            stats['class_rooms']['created'] += 1
        else:
            stats['class_rooms']['updated'] += 1

    def upsert_rotation_arrangement(self, resolver, item, stats, dry_run):
        from apps.campus_rotation.models import RotationArrangement

        person_id = item.get('person_id')
        stage = item.get('stage', 'PENDING')
        if person_id is None:
            raise CommandError(f'RotationArrangement 缺少 person_id: {item!r}')

        # 业务唯一键：person_id + stage（模型层无 DB 唯一约束，先查首条再决定更/建）
        lookup = {'person_id': person_id, 'stage': stage}
        defaults = {
            'intent_bu': (item.get('intent_bu') or '').strip(),
            'suggest_dept': resolver.resolve_department(item.get('suggest_dept')),
            'suggest_mentor': resolver.resolve_user(item.get('suggest_mentor')),
            'head_teacher': resolver.resolve_user(item.get('head_teacher')),
            'current_dept': resolver.resolve_department(item.get('current_dept')),
            'mentor': resolver.resolve_user(item.get('mentor')),
            'direct_manager': resolver.resolve_user(item.get('direct_manager')),
            'class_room': self._resolve_class_room(resolver, item.get('class_room')),
            'resource': self._resolve_resource(resolver, item.get('resource')),
            'employee_status': item.get('employee_status', ''),
            'rotation_start': item.get('rotation_start'),
            'rotation_end': item.get('rotation_end'),
            'rank': item.get('rank'),
            'final_dept': item.get('final_dept', ''),
            'result': item.get('result', ''),
            'note': item.get('note', ''),
        }
        if dry_run:
            exists = RotationArrangement.objects.filter(**lookup).exists()
            stats['rotation_arrangements']['would_update' if exists else 'would_create'] += 1
            stats['preview'].append({
                'model': 'RotationArrangement', 'key': f'{person_id}:{stage}',
                'action': 'update' if exists else 'create',
            })
            return

        existing = RotationArrangement.objects.filter(**lookup).first()
        if existing is None:
            existing = RotationArrangement(**lookup)
            stats['rotation_arrangements']['created'] += 1
        else:
            stats['rotation_arrangements']['updated'] += 1
        for field, val in defaults.items():
            setattr(existing, field, val)
        existing.save()

    def _resolve_class_room(self, resolver, value):
        from apps.campus_rotation.models import ClassRoom

        if value is None or value == '':
            return None
        code = value if isinstance(value, str) else (value.get('code') or '').strip()
        if not code:
            return None
        return ClassRoom.objects.filter(code=code).first()

    def _resolve_resource(self, resolver, value):
        """按「资源编号」解析轮岗资源（直播间 / 客服部门 / 其他合一后的具体位置）。"""
        from apps.campus_rotation.models import RotationResource

        if value is None or value == '':
            return None
        no = value if isinstance(value, str) else (value.get('resource_no') or '').strip()
        if not no:
            return None
        return RotationResource.objects.filter(resource_no=no).first()

    # ---- 报告 ----
    def build_report(self, data, resolver, stats, dry_run):
        total_in = (
            len(data['resources']) + len(data['class_rooms'])
            + len(data['rotation_arrangements'])
        )
        return {
            'mode': 'dry-run (no DB write)' if dry_run else 'apply',
            'source': 'inline-empty' if not getattr(self, 'source_path', None) else self.source_path,
            'input_rows': total_in,
            'resources': stats['resources'],
            'class_rooms': stats['class_rooms'],
            'rotation_arrangements': stats['rotation_arrangements'],
            'unmatched_depts': resolver.unmatched_depts,
            'unmatched_users': resolver.unmatched_users,
            'preview': stats['preview'] if dry_run else [],
        }

    def print_report(self, report):
        self.stdout.write(self.style.MIGRATE_HEADING('=== 校招轮岗数据迁移报告 ==='))
        self.stdout.write(f"模式: {report['mode']}")
        self.stdout.write(f"数据源: {report['source']}")
        self.stdout.write(f"待处理行数: {report['input_rows']}")
        self.stdout.write(
            'RotationResource: '
            f"created={report['resources'].get('created', 0)} "
            f"updated={report['resources'].get('updated', 0)} "
            f"would_create={report['resources'].get('would_create', 0)} "
            f"would_update={report['resources'].get('would_update', 0)}"
        )
        self.stdout.write(
            'ClassRoom:       '
            f"created={report['class_rooms'].get('created', 0)} "
            f"updated={report['class_rooms'].get('updated', 0)} "
            f"would_create={report['class_rooms'].get('would_create', 0)} "
            f"would_update={report['class_rooms'].get('would_update', 0)}"
        )
        self.stdout.write(
            'RotationArrange: '
            f"created={report['rotation_arrangements'].get('created', 0)} "
            f"updated={report['rotation_arrangements'].get('updated', 0)} "
            f"would_create={report['rotation_arrangements'].get('would_create', 0)} "
            f"would_update={report['rotation_arrangements'].get('would_update', 0)}"
        )

        if report['unmatched_depts']:
            self.stdout.write(self.style.WARNING(
                f"unmatched_depts ({len(report['unmatched_depts'])}): "
                f"{', '.join(report['unmatched_depts'])}"
            ))
        else:
            self.stdout.write('unmatched_depts: [] (全部匹配或无需映射)')

        if report['unmatched_users']:
            self.stdout.write(self.style.WARNING(
                f"unmatched_users ({len(report['unmatched_users'])}): "
                f"{', '.join(report['unmatched_users'])}"
            ))
        else:
            self.stdout.write('unmatched_users: [] (全部匹配或无需映射)')

        if report['mode'].startswith('dry-run'):
            self.stdout.write(self.style.SUCCESS('DRY-RUN 完成：未对任何数据表写入。'))

    # ---- 入口 ----
    def handle(self, *args, **options):
        self.source_path = options.get('source')
        dry_run = options.get('dry_run')
        json_report = options.get('json_report')

        data = self.load_source(self.source_path)
        resolver = ReferenceResolver()

        stats = {
            'resources': {},
            'class_rooms': {},
            'rotation_arrangements': {},
            'preview': [],
        }
        for bucket in ('resources', 'class_rooms', 'rotation_arrangements'):
            stats[bucket] = {'created': 0, 'updated': 0, 'would_create': 0, 'would_update': 0}

        # 默认（无 --source）即为 dry 安全态：即便 dry_run 为假，也无数据可写。
        effective_dry = dry_run or not self.source_path

        # 按业务唯一键顺序处理；事务包裹（apply 时）保证原子性
        from django.db import transaction

        try:
            if effective_dry:
                for item in data['resources']:
                    self.upsert_resource(resolver, item, stats, dry_run=True)
                for item in data['class_rooms']:
                    self.upsert_class_room(resolver, item, stats, dry_run=True)
                for item in data['rotation_arrangements']:
                    self.upsert_rotation_arrangement(resolver, item, stats, dry_run=True)
            else:
                with transaction.atomic():
                    for item in data['resources']:
                        self.upsert_resource(resolver, item, stats, dry_run=False)
                    for item in data['class_rooms']:
                        self.upsert_class_room(resolver, item, stats, dry_run=False)
                    for item in data['rotation_arrangements']:
                        self.upsert_rotation_arrangement(resolver, item, stats, dry_run=False)
        except CommandError:
            raise
        except Exception as exc:  # noqa: BLE001 导入命令兜底: 内部异常统一转友好报错 + 非零退出
            raise CommandError(f'迁移处理异常: {exc}')

        report = self.build_report(data, resolver, stats, dry_run=effective_dry)
        self.print_report(report)

        if json_report:
            try:
                with open(json_report, 'w', encoding='utf-8') as fh:
                    json.dump(report, fh, ensure_ascii=False, indent=2)
                self.stdout.write(self.style.SUCCESS(f'JSON 报告已写入: {json_report}'))
            except OSError as exc:
                raise CommandError(f'写入 JSON 报告失败: {exc}')

        return


# ---------------------------------------------------------------------------
# 数据源 JSON 结构示例（仅文档用途，本脚本不读取本常量）
# ---------------------------------------------------------------------------
SAMPLE_DATA = '''
{
  "resources": [
    {
      "resource_no": "LR0001",
      "name": "深圳直播间A",
      "resource_type": "直播间",          // 或 客服部门 / 其他
      "department": "腾讯云研发部",        // 按 Department.name 精确匹配
      "bu": "云与智慧产业事业群",          // 按 Department.name 精确匹配
      "mentor": {"employee_id": "12345"},  // 或 {"username": "zhangsan"}
      "platform": "TENCENT_MEETING",      // 仅直播间填
      "location": "SHENZHEN",
      "capacity": 50,
      "is_active": true
    }
  ],
  "class_rooms": [
    {
      "code": "CL001",
      "name": "2026校招一班",
      "head_teacher": {"username": "lisi"},
      "hrbp": {"username": "wangwu"},
      "batch": "2026"
    }
  ],
  "rotation_arrangements": [
    {
      "person_id": 100001,
      "stage": "PENDING",
      "intent_bu": "云与智慧产业事业群",
      "suggest_dept": "腾讯云研发部",
      "suggest_mentor": {"employee_id": "12345"},
      "head_teacher": {"username": "lisi"},
      "current_dept": "腾讯云研发部",
      "mentor": {"employee_id": "12345"},
      "direct_manager": {"username": "zhaoliu"},
      "class_room": "CL001",
      "resource": "LR0001",             // 按资源编号匹配（具体位置）
      "employee_status": "PROBATION"
    }
  ]
}
'''
