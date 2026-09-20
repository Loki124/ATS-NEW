"""Reason Library app — 原因标签池 + 场景规则 (PRD v4 §XX).

设计要点 (T01, 2026-XX-XX):
- reason_tag: 全局标签池, 软删 + deleted_at 唯一约束 (Q-A4: 含软删)
- scene_rule: 场景规则, is_system=True 时仅超管可改 (Q1/Q2)
- rule_category: 多层分类树, level CHECK 1<=level<=4
- category_assignment: 分类 ↔ 标签 多对多, UNIQUE(category_id, tag_id)
- rule_scene_assignment: 场景 → 规则, UNIQUE(scene) (Q6: 一场景一规则)
"""
default_app_config = 'apps.reason_library.apps.ReasonLibraryConfig'
