"""M07 action_map 单测：ACTION_REGISTRY / PRESET_PACKAGES 注册表与校验。"""
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from apps.data_permission import action_map


class ActionMapTestCase(TestCase):
    def test_known_actions_registered(self):
        for key in ('view', 'edit', 'create', 'transition', 'feedback', 'claim',
                    'merge', 'batch_update', 'import', 'delete', 'export'):
            self.assertIn(key, action_map.ACTION_REGISTRY)

    def test_destructive_flag_set(self):
        self.assertTrue(action_map.ACTION_REGISTRY['delete']['destructive'])
        self.assertTrue(action_map.ACTION_REGISTRY['merge']['destructive'])
        self.assertFalse(action_map.ACTION_REGISTRY['edit']['destructive'])

    def test_is_known_action(self):
        self.assertTrue(action_map.is_known_action('edit'))
        self.assertFalse(action_map.is_known_action('frobnicate'))

    def test_validate_action_ok_and_raise(self):
        # 合法 -> 原样返回
        self.assertEqual(action_map.validate_action('edit'), 'edit')
        # 非法 -> 抛
        with self.assertRaises(ImproperlyConfigured):
            action_map.validate_action('not_real')

    def test_resolve_preset_returns_action_set(self):
        self.assertEqual(
            action_map.resolve_preset('read_only'), {'view'}
        )
        self.assertIn('edit', action_map.resolve_preset('owner_full'))
        self.assertIn('transition', action_map.resolve_preset('owner_full'))

    def test_resolve_preset_unknown_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            action_map.resolve_preset('no_such_preset')

    def test_all_preset_actions_registered(self):
        # 预设包若引用了未注册动作 -> resolve_preset 必抛，这里逐个验证均合法
        for name in action_map.PRESET_PACKAGES:
            resolved = action_map.resolve_preset(name)  # 不抛即通过
            self.assertIsInstance(resolved, set)

    def test_preset_contains(self):
        self.assertTrue(action_map.preset_contains('owner_full', 'edit'))
        self.assertFalse(action_map.preset_contains('read_only', 'delete'))
        self.assertFalse(action_map.preset_contains('no_such', 'edit'))
