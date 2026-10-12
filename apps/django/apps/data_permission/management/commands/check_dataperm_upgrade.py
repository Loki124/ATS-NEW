"""上线前体检：数据权限动态条件 + 权限模板。

定位：**这不是迁移脚本**，本功能不需要任何数据搬迁（本仓两条迁移均为
「新建空表」与「加一列 default=[]」，见 0003 / 0030）。本命令回答的是一个更
基础的问题 ——「上线所依赖的『存量为零』假设，在目标环境是否真的成立」。

若某环境已在用测试功能、或存在脏数据，下面第 2 组检查会报【异常】，
此时应当先人工查清再上线，而不是直接 migrate 后上线。

用法:
    python manage.py check_dataperm_upgrade              # 体检（有异常时 exit 1）
    python manage.py check_dataperm_upgrade --strict     # 「注意」也视为失败
    python manage.py check_dataperm_upgrade --sample 500 # 调整抽样编译数量

退出码: 0=通过（可能有注意项） / 1=有异常（或 --strict 下有注意项）
"""
from django.core.management.base import BaseCommand
from django.db import connection

OK = '[OK]'
WARN = '[注意]'
FAIL = '[异常]'


class Command(BaseCommand):
    help = '数据权限动态条件 + 权限模板 上线前体检（不修改任何数据）'

    def add_arguments(self, parser):
        parser.add_argument('--sample', type=int, default=200,
                            help='存量规则抽样编译的数量上限（默认 200，0=全量）')
        parser.add_argument('--strict', action='store_true',
                            help='把「注意」项也视为失败')

    # ------------------------------------------------------------------ 输出
    def _line(self, tag, text):
        self.stdout.write('{} {}'.format(tag, text))

    # ------------------------------------------------- 1. 迁移是否已应用
    def _check_migrations(self, out):
        from django.db.migrations.executor import MigrationExecutor

        try:
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            plan = executor.migration_plan(targets)
        except Exception as e:  # noqa: BLE001 — 升级自检命令，读不到迁移状态只警告不失败
            out.append((WARN, '无法读取迁移状态：{}'.format(e)))
            return

        if plan:
            names = ['{}.{}'.format(m.app_label, m.name) for m, _ in plan]
            out.append((FAIL, '有 {} 个迁移未应用：{}（请先执行 manage.py migrate）'
                        .format(len(plan), '、'.join(names[:6]))))
        else:
            out.append((OK, '数据库迁移已全部应用'))

    # ------------------------------------------- 2. 存量残留（核心假设）
    def _check_residue(self, out):
        from apps.data_permission.models import DataPermissionRule

        rules = list(DataPermissionRule.objects.filter(
            level='ROW', scope_payload__isnull=False,
        ).only('scope_payload'))

        with_ref = 0
        with_dynamic = 0
        with_orphan_flag = 0
        for r in rules:
            payload = r.scope_payload or {}
            if not isinstance(payload, dict):
                continue
            for g in payload.get('groups') or []:
                if not isinstance(g, dict):
                    continue
                if isinstance(g.get('templateRef'), dict):
                    with_ref += 1
                    if g['templateRef'].get('orphaned'):
                        with_orphan_flag += 1
            for g in payload.get('groups') or []:
                for c in (g or {}).get('conditions') or []:
                    if isinstance(c, dict) and (c.get('valueSource') or 'static') == 'dynamic':
                        with_dynamic += 1

        total = len(rules)
        out.append((OK, '存量行级规则 {} 条（体检基准）'.format(total)))

        # 首次上线应为 0；非 0 说明该环境已在用新功能，上线不再是「纯新增」
        for label, n in (
            ('含 templateRef（模板引用）', with_ref),
            ('含 valueSource=dynamic（动态取值）', with_dynamic),
            ('含 orphaned（失效标记）', with_orphan_flag),
        ):
            if n == 0:
                out.append((OK, '存量 scope_payload {}: 0 条'.format(label)))
            else:
                out.append((FAIL, '存量 scope_payload {}: {} 条 —— 非预期！'
                            .format(label, n)))

    # ------------------------------------- 3. 模板表与内置模板是否就绪
    def _check_templates(self, out):
        from django.db import ProgrammingError

        try:
            from apps.data_permission.models import DataPermTemplate
            count = DataPermTemplate.objects.count()
        except ProgrammingError:
            out.append((WARN, '模板表尚未创建：请先执行 manage.py migrate'))
            return
        except Exception as e:  # noqa: BLE001 — 升级自检命令，模板表不可读只警告不失败
            out.append((WARN, '读取模板表失败：{}'.format(e)))
            return

        if count == 0:
            out.append((WARN, '模板表为空：请执行 manage.py seed_data_perm_templates '
                               '（不影响上线，用户仍可手工配置动态取值）'))
        else:
            codes = list(DataPermTemplate.objects.values_list('code', flat=True))
            builtin = [c for c in codes if c.startswith('DPT0')]
            out.append((OK, '模板 {} 个：{}'.format(count, '、'.join(codes[:8]))))
            if not builtin:
                out.append((WARN, '未发现内置模板（DPT000x），建议执行 seed 预置'))

        # 孤儿引用：scope_payload 引用的模板不存在 -> 那些组会按 missing 提示
        try:
            from apps.data_permission.models import DataPermissionRule
            refs = set()
            for r in DataPermissionRule.objects.filter(
                level='ROW', scope_payload__isnull=False,
            ).only('scope_payload'):
                for g in ((r.scope_payload or {}).get('groups') or []):
                    ref = (g or {}).get('templateRef') or {}
                    if isinstance(ref, dict) and ref.get('templateCode'):
                        refs.add(ref['templateCode'])
            if refs:
                from apps.data_permission.models import DataPermTemplate as T
                missing = sorted(refs - set(
                    T.all_objects.values_list('code', flat=True)))
                if missing:
                    out.append((FAIL, '存在指向不存在模板的引用：{}'
                                .format('、'.join(missing))))
                else:
                    out.append((OK, '模板引用全部可解析（{} 个）'.format(len(refs))))
        except Exception as e:  # noqa: BLE001 — 升级自检命令，孤儿引用检查失败只警告不中断
            out.append((WARN, '孤儿引用检查跳过：{}'.format(e)))

    # ----------------------------- 4. 存量规则在新编译器下能否正常编译
    def _check_compile(self, sample, out):
        from apps.data_permission.expr_compiler import compile_scope_q
        from apps.data_permission.field_map import MODULE_ORDER
        from apps.data_permission.models import DataPermissionRule

        qs = DataPermissionRule.objects.filter(
            level='ROW', scope_type='CUSTOM', scope_payload__isnull=False,
        ).only('entity', 'scope_payload')
        if sample:
            qs = qs[:sample]
        rules = list(qs)
        if not rules:
            out.append((OK, '无 CUSTOM 行级规则，跳过编译体检'))
            return

        ok = bad = 0
        errors = []
        for r in rules:
            entity = r.entity if r.entity in MODULE_ORDER else None
            if entity is None:
                continue
            try:
                # user=None：存量静态条件不依赖用户上下文；动态条件会 fail-closed
                # 但不抛异常 —— 这里只关心「新代码能否无异常编译存量数据」
                compile_scope_q(r.scope_payload, entity, user=None)
                ok += 1
            except Exception as e:  # noqa: BLE001 — 升级自检命令，存量规则编译失败只计数不中断
                bad += 1
                if len(errors) < 5:
                    errors.append('rule {}: {}'.format(r.pk, e))

        if bad == 0:
            out.append((OK, '存量规则编译抽样 {} 条全部通过'.format(ok)))
        else:
            out.append((FAIL, '存量规则编译 {} 条失败 / 共 {} 条'
                        .format(bad, ok + bad)))
            for line in errors:
                out.append((FAIL, '  ' + line))

    # ------------------------------------------------------------------ 主流程
    def handle(self, *args, **options):
        sample = options.get('sample') or 0
        strict = options.get('strict')

        self.stdout.write(self.style.SUCCESS(
            '=== 数据权限动态条件 + 权限模板 上线前体检 ==='))

        out = []
        self._check_migrations(out)
        self._check_residue(out)
        self._check_templates(out)
        self._check_compile(sample, out)

        n_fail = sum(1 for t, _ in out if t == FAIL)
        n_warn = sum(1 for t, _ in out if t == WARN)
        n_ok = sum(1 for t, _ in out if t == OK)

        for tag, text in out:
            self._line(tag, text)

        self.stdout.write('')
        summary = '{} {} / {} {} / {} {}'.format(OK, n_ok, WARN, n_warn, FAIL, n_fail)
        if n_fail:
            self.stdout.write(self.style.ERROR('体检未通过：{}'.format(summary)))
            raise SystemExit(1)
        if n_warn and strict:
            self.stdout.write(self.style.ERROR('存在注意项（--strict 视为失败）：{}'.format(summary)))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS('体检通过：{}'.format(summary)))