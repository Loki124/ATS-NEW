"""回归测试: "库没跟上代码" 的自诊断 (db_schema_out_of_sync)

2026-10-15 实测教训: 新 app 注册进 INSTALLED_APPS + 迁移文件在仓, 但本地库没跑
migrate, ORM 抛 ProgrammingError(1146 Table ... doesn't exist) → 统一异常处理器
原来一律包成 500 "服务器内部错误", 前端只弹"服务繁忙", 排查方向被带偏
(先怀疑代码 bug / 权限 / 迁移文件缺失, 实际只需跑 migrate)。

本测试锁定三件事:
  1. 表/列不存在能被识别, 且给出可执行提示
  2. **不误报** —— SQL 语法错 / 唯一键冲突 / FK 失败等真 bug 必须仍走 internal_error
  3. 生产 (DEBUG=False) 不泄漏具体表名, 但仍标记为环境问题
"""
from django.db import DatabaseError, IntegrityError, OperationalError, ProgrammingError
from django.test import SimpleTestCase, override_settings

from apps.common.exceptions import _db_schema_out_of_sync_hint


class DbSchemaOutOfSyncHintTests(SimpleTestCase):
    """纯函数测试: 不碰数据库, 因此不建表也能跑。"""

    @override_settings(DEBUG=True)
    def test_missing_table_detected(self):
        exc = ProgrammingError(
            "(1146, \"Table 'ats_dev.position_title_jobtitle' doesn't exist\")"
        )
        hint = _db_schema_out_of_sync_hint(exc)
        self.assertIsNotNone(hint, '漏跑 migrate 的表不存在必须被识别')
        self.assertIn('position_title_jobtitle', hint, '开发期应指出具体哪张表')
        self.assertIn('migrate', hint, '提示必须包含可执行命令')

    @override_settings(DEBUG=True)
    def test_missing_column_detected(self):
        exc = OperationalError(
            "(1054, \"Unknown column 'user_roles.user_id' in 'field list'\")"
        )
        hint = _db_schema_out_of_sync_hint(exc)
        self.assertIsNotNone(hint)
        self.assertIn('user_roles.user_id', hint)

    @override_settings(DEBUG=True)
    def test_sqlite_wording_detected(self):
        """SQLite 措辞不同(no such table/column), 也要认。"""
        table_exc = DatabaseError('no such table: position_title_jobtitle')
        self.assertIsNotNone(_db_schema_out_of_sync_hint(table_exc))
        column_exc = DatabaseError("no such column: user_id")
        self.assertIsNotNone(_db_schema_out_of_sync_hint(column_exc))

    # ── 关键: 不误报 ──
    # 这些是**真 bug**, 若被当成"迁移没跑", 排查方向会被带偏到错误的地方。
    def test_real_bugs_not_misreported(self):
        real_bugs = [
            ProgrammingError("(1064, \"You have an error in your SQL syntax\")"),
            ProgrammingError("(1062, \"Duplicate entry 'x' for key 'uk'\")"),
            IntegrityError("(1452, \"Cannot add or update a child row\")"),
            OperationalError("(2006, \"MySQL server has gone away\")"),
            OperationalError("(1213, \"Deadlock found\")"),
            OperationalError("(1045, \"Access denied for user\")"),
        ]
        for exc in real_bugs:
            with self.subTest(exc=str(exc)):
                self.assertIsNone(
                    _db_schema_out_of_sync_hint(exc),
                    f'真 bug 被误判为迁移问题, 会把排查带偏: {exc}',
                )

    def test_non_db_exception_ignored(self):
        self.assertIsNone(_db_schema_out_of_sync_hint(ValueError("Table x doesn't exist")))

    # ── 生产不泄漏 schema ──
    @override_settings(DEBUG=False)
    def test_prod_does_not_leak_table_name(self):
        exc = ProgrammingError(
            "(1146, \"Table 'ats_pro.core_secrettable' doesn't exist\")"
        )
        hint = _db_schema_out_of_sync_hint(exc)
        self.assertIsNotNone(hint, '生产也要标记为环境问题')
        self.assertNotIn('core_secrettable', hint, '生产不得泄漏具体表名')
        self.assertNotIn('ats_pro', hint, '生产不得泄漏数据库名')
