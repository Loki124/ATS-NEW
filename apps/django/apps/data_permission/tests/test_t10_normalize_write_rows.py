"""T10 WRITE 增量守卫：归一化 legacy WRITE 行 ``actions=[]`` -> NULL（幂等 + 不破坏真实配置）。

钉死的两条契约（与 migrations/0009_normalize_write_rows.py 对齐）：
  1. 只归一退化态 ``actions=[]`` 的 WRITE 行 -> NULL；非空 list（真实动作配置）与
     NULL（规范态）一律不动；
  2. 幂等：重复执行后仍 0 条 legacy WRITE 行；
  3. 干净库（无 legacy 插入）下不应存在 ``actions=[]`` 的 WRITE 行 —— 增量守卫保证
     新的 upsert 路径不再产出 []（见 role_scope_api.upsert_modules 始终存 list 或删行）。

注：迁移模块名以数字开头，无法用 `from ... import` 直接导入，故用 importlib 取函数。
"""
import importlib

from django.apps import apps
from django.db import connection
from django.test import TestCase

from apps.data_permission.models import DataPermissionRule, RowScopeAccess, RowScopeType

_MIG = importlib.import_module('apps.data_permission.migrations.0009_normalize_write_rows')
normalize_legacy_write_actions = _MIG.normalize_legacy_write_actions


class _FakeSchemaEditor:
    """迁移 RunPython 的 schema_editor 参数在纯数据迁移里用不到，给个占位。"""

    def __init__(self):
        self.connection = connection


def _run_migration():
    """以当前 app 注册表（0008->0009 间 DataPermissionRule 无 schema 变更）执行数据函数。"""
    normalize_legacy_write_actions(apps=apps, schema_editor=_FakeSchemaEditor())


class NormalizeWriteRowsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role = 'TEST_ROLE'

    def _make(self, actions):
        return DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value=self.role, level='ROW',
            row_access=RowScopeAccess.WRITE, entity='candidate',
            scope_type=RowScopeType.OWNER, actions=actions, status=1,
        )

    def test_normalizes_only_legacy_empty_list_keeps_real_config(self):
        legacy = self._make([])        # 退化态，应被归一为 NULL
        proper = self._make(['edit'])  # 真实动作配置，必须保留
        canonical = self._make(None)   # 规范态，必须保留

        _run_migration()

        legacy.refresh_from_db()
        proper.refresh_from_db()
        canonical.refresh_from_db()
        # 退化态 -> NULL（全部放行）
        self.assertIsNone(legacy.actions)
        # 真实配置毫发无损
        self.assertEqual(proper.actions, ['edit'])
        # 规范态不动
        self.assertIsNone(canonical.actions)

    def test_idempotent_no_legacy_after_second_run(self):
        self._make([])  # 一条 legacy
        _run_migration()
        # 第一次后不应再有 legacy
        self.assertEqual(
            DataPermissionRule.objects.filter(row_access='WRITE', actions=[]).count(), 0
        )
        # 再跑一次仍是 0（空转，不报错、不重复改动）
        _run_migration()
        self.assertEqual(
            DataPermissionRule.objects.filter(row_access='WRITE', actions=[]).count(), 0
        )

    def test_zero_legacy_write_rows_in_clean_db(self):
        # 增量守卫invariant：干净库（未手动插入 legacy）下不应存在 [] WRITE 行。
        # 若未来 upsert 路径回退到产出 []，本断言即翻红，第一时间拦截回归。
        self.assertEqual(
            DataPermissionRule.objects.filter(row_access='WRITE', actions=[]).count(), 0
        )
