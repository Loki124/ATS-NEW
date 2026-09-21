"""Reason Library 初始数据 (T02 / 0002_seed_initial_data.py + management cmd).

数据来源: ``/Users/loki/Downloads/reason_library_prototype.html`` L596-722。
幂等: 全部用 get_or_create, 重复执行不会重复灌入。

灌入内容:
- 53 条系统标签 (劳动者 / 劳动工具 / 劳动资料 / 劳动对象 / 需求与流程,
  5 大类仅作注释, 不作为标签字段, Q7)
- 3 条预置规则 (r-resume / r-cancel / r-talent), 含完整 categories 树
  + assignments + scene assignments
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from django.db import transaction

from .models import (
    MAX_CATEGORY_LEVEL,
    CategoryAssignment,
    ReasonTag,
    RuleCategory,
    RuleSceneAssignment,
    SCENE_OPTIONS,
    SceneRule,
    TagType,
)


# ---------------------------------------------------------------------------
# 53 条系统标签 (原型 L596-654)
# 字段: (name, en_name, tip, group)
# group 仅作注释分组 (Q7: 不作为标签字段)
# ---------------------------------------------------------------------------
SYSTEM_TAGS: List[Tuple[str, str, str, str]] = [
    # —— 劳动者 ——
    ('学历不匹配', 'Education mismatch', '', '劳动者'),
    ('毕业院校不匹配', 'School mismatch', '', '劳动者'),
    ('专业不匹配', 'Major mismatch', '', '劳动者'),
    ('年龄不匹配', 'Age mismatch', '', '劳动者'),
    ('性别不匹配', 'Gender mismatch', '', '劳动者'),
    ('婚育状态不匹配', 'Marital status mismatch', '', '劳动者'),
    ('户籍类型不匹配', 'Hukou type mismatch', '', '劳动者'),
    ('籍贯不匹配', 'Native place mismatch', '', '劳动者'),
    ('工作地不匹配', 'Work location mismatch', '', '劳动者'),
    ('身高体重不匹配', 'Physical mismatch', '', '劳动者'),
    ('形象不匹配', 'Appearance mismatch', '', '劳动者'),
    ('性格不匹配', 'Personality mismatch', '', '劳动者'),
    ('晋升经历不匹配', 'Promotion mismatch', '', '劳动者'),
    ('违规违纪不匹配', 'Disciplinary issue', '', '劳动者'),
    ('离职原因不匹配', 'Resignation reason', '', '劳动者'),
    ('职业规划不匹配', 'Career plan mismatch', '', '劳动者'),
    ('资质证书不匹配', 'Certificate mismatch', '', '劳动者'),
    # —— 劳动工具 ——
    ('技能经验年限不匹配', 'Skill years mismatch', '', '劳动工具'),
    ('业务系统经验不匹配', 'System experience mismatch', '', '劳动工具'),
    ('跳槽频繁', 'Frequent job hopping', '', '劳动工具'),
    ('薪酬期望不匹配', 'Salary expectation mismatch', '', '劳动工具'),
    ('不接受经营者分润模式', 'Reject profit sharing', '', '劳动工具'),
    ('能上能下能动不匹配', 'Flexibility mismatch', '', '劳动工具'),
    ('尊重事实-回答问题隐瞒', 'Concealment', '', '劳动工具'),
    ('尊重事实-不尊重规则', 'Disrespect rules', '', '劳动工具'),
    ('自我批判-害怕批评', 'Afraid of criticism', '', '劳动工具'),
    ('自我批判-习惯抱怨', 'Habitual complaining', '', '劳动工具'),
    ('积极主动-求职意愿不强', 'Weak intention', '', '劳动工具'),
    ('积极主动-不喜欢沟通', 'Poor communication', '', '劳动工具'),
    ('积极主动-害怕被拒绝', 'Fear of rejection', '', '劳动工具'),
    ('积极主动-持续学习不匹配', 'Weak learning', '', '劳动工具'),
    ('认真负责-喜欢推诿', 'Shirking responsibility', '', '劳动工具'),
    ('认真负责-敷衍应付', 'Perfunctory', '', '劳动工具'),
    ('艰苦奋斗-不接受吃苦耐劳作息/考勤', 'Reject hard schedule', '', '劳动工具'),
    ('艰苦奋斗-吃苦意愿不足', 'Insufficient endurance', '', '劳动工具'),
    # —— 劳动资料 ——
    ('非对标公司', 'Non-benchmark company', '', '劳动资料'),
    ('非对标行业', 'Non-benchmark industry', '', '劳动资料'),
    ('黑名单企业', 'Blacklisted company', '', '劳动资料'),
    # —— 劳动对象 ——
    ('职位类型不匹配', 'Job type mismatch', '', '劳动对象'),
    ('职级不匹配', 'Level mismatch', '', '劳动对象'),
    ('对标岗位年限不足', 'Insufficient years', '', '劳动对象'),
    ('团队管理经验不匹配', 'Team management mismatch', '', '劳动对象'),
    ('业务体量不匹配', 'Business scale mismatch', '', '劳动对象'),
    ('国家/区域经验不匹配', 'Region experience mismatch', '', '劳动对象'),
    ('退伍年限不匹配（专项岗位特有）', 'Veteran years mismatch', '仅针对专项招聘岗位显示', '劳动对象'),
    ('负责品类/业务线不匹配', 'Category mismatch', '', '劳动对象'),
    # —— 需求与流程 ——
    ('需求已暂停', 'Requisition paused', '该需求已暂停招聘', '需求与流程'),
    ('需求已停招', 'Requisition closed', '', '需求与流程'),
    ('需求已完成', 'Requisition fulfilled', '', '需求与流程'),
    ('岗位画像调整', 'JD adjusted', '', '需求与流程'),
    ('招聘流程不匹配', 'Process mismatch', '', '需求与流程'),
    ('简历信息不全', 'Incomplete resume', '', '需求与流程'),
    ('简历时间矛盾/存疑', 'Timeline suspicious', '', '需求与流程'),
]


# 2026-09-21 新增: 系统预置标签 (流程节点自动写入的原因, 仅供代码/流程引用)
PRESET_TAGS: List[Tuple[str, str, str]] = [
    ('已录用', 'Hired', ''),
    ('已离职', 'Resigned', ''),
    ('上传直接归档', 'Upload auto archived', ''),
    ('为候选人推荐了新职位', 'Recommended new job', ''),
    ('职位关闭自动归档', 'Job closed auto archived', ''),
    ('筛选不通过自动淘汰', 'Screen auto rejected', ''),
    ('加入黑名单', 'Blacklisted', ''),
    ('长时间未处理自动归档', 'Stale auto archived', ''),
    ('面试不通过自动淘汰', 'Interview auto rejected', ''),
    ('管控重复申请', 'Duplicate application blocked', ''),
]


# ---------------------------------------------------------------------------
# 3 条预置规则 (原型 L657-722)
# 每条规则结构:
#   {key, name, is_system, enabled, scenes, categories, assignments}
# categories: [(key, name, parent_key, order, allow_custom)]
# assignments: {category_key: [tag_name, ...]}
# ---------------------------------------------------------------------------
PRESET_RULES: List[Dict] = [
    {
        'key': 'r-resume',
        'name': '预置默认规则',
        'is_system': True,
        'enabled': True,
        'scenes': ['筛选不通过', '淘汰'],
        'categories': [
            ('c1', '劳动者', None, 1, False),
            ('c1-1', '打工者 / 经营者 / 企业家', 'c1', 1, True),
            ('c2', '劳动工具', None, 2, False),
            ('c2-1', '有形工具-技术', 'c2', 1, False),
            ('c2-1-1', '实体工具', 'c2-1', 1, True),
            ('c2-1-2', '业务系统', 'c2-1', 2, True),
            ('c2-2', '无形工具-主观能动性', 'c2', 2, True),
            ('c3', '劳动资料', None, 3, False),
            ('c3-1', '线上零售 / 线下服务 / 全域分销', 'c3', 1, True),
            ('c4', '劳动对象', None, 4, False),
            ('c4-1', '产品 服务 产品/服务', 'c4', 1, True),
            ('c5', '需求与流程', None, 5, True),
        ],
        'assignments': {
            'c1-1': ['学历不匹配', '毕业院校不匹配', '专业不匹配', '年龄不匹配', '性别不匹配',
                     '婚育状态不匹配', '户籍类型不匹配', '籍贯不匹配', '工作地不匹配',
                     '身高体重不匹配', '形象不匹配', '性格不匹配', '晋升经历不匹配',
                     '违规违纪不匹配', '离职原因不匹配', '职业规划不匹配', '资质证书不匹配'],
            'c2-1-1': ['技能经验年限不匹配'],
            'c2-1-2': ['业务系统经验不匹配'],
            'c2-2': ['跳槽频繁', '薪酬期望不匹配', '不接受经营者分润模式',
                     '能上能下能动不匹配', '尊重事实-回答问题隐瞒', '尊重事实-不尊重规则',
                     '自我批判-害怕批评', '自我批判-习惯抱怨', '积极主动-求职意愿不强',
                     '积极主动-不喜欢沟通', '积极主动-害怕被拒绝', '积极主动-持续学习不匹配',
                     '认真负责-喜欢推诿', '认真负责-敷衍应付', '艰苦奋斗-不接受吃苦耐劳作息/考勤',
                     '艰苦奋斗-吃苦意愿不足'],
            'c3-1': ['非对标公司', '非对标行业', '黑名单企业'],
            'c4-1': ['职位类型不匹配', '职级不匹配', '对标岗位年限不足',
                     '团队管理经验不匹配', '业务体量不匹配', '国家/区域经验不匹配',
                     '退伍年限不匹配（专项岗位特有）', '负责品类/业务线不匹配'],
            'c5': ['需求已暂停', '需求已停招', '需求已完成', '岗位画像调整',
                   '招聘流程不匹配', '简历信息不全', '简历时间矛盾/存疑'],
        },
    },
    {
        'key': 'r-cancel',
        'name': '预置默认规则 · 取消面试',
        'is_system': False,
        'enabled': True,
        'scenes': ['取消面试'],
        'categories': [
            ('cc1', '候选人原因', None, 1, True),
            ('cc2', '岗位原因', None, 2, True),
            ('cc3', '流程原因', None, 3, False),
            ('cc3-1', '面试安排问题', 'cc3', 1, True),
        ],
        'assignments': {
            'cc1': ['积极主动-求职意愿不强', '积极主动-不喜欢沟通', '积极主动-害怕被拒绝'],
            'cc2': ['需求已暂停', '需求已停招'],
            'cc3-1': ['招聘流程不匹配', '简历信息不全'],
        },
    },
    {
        'key': 'r-talent',
        'name': '预置默认规则 · 放入人才库',
        'is_system': False,
        'enabled': False,
        'scenes': ['放入人才库'],
        'categories': [
            ('t1', '暂不匹配', None, 1, True),
            ('t2', '储备候选人', None, 2, True),
        ],
        'assignments': {
            't1': ['学历不匹配', '专业不匹配', '年龄不匹配'],
            't2': ['积极主动-持续学习不匹配'],
        },
    },
]


# ---------------------------------------------------------------------------
# 校验: level 1..4 与 SCENE_OPTIONS
# ---------------------------------------------------------------------------
def _validate_seed():
    seen_names = set()
    for name, en, tip, _grp in SYSTEM_TAGS:
        if name in seen_names:
            raise ValueError(f'SYSTEM_TAGS 重复: {name}')
        seen_names.add(name)
        if len(name) > 32:
            raise ValueError(f'tag name 超长 (32): {name}')
        if len(en) > 64:
            raise ValueError(f'tag en_name 超长 (64): {en}')
        if len(tip) > 128:
            raise ValueError(f'tag tip 超长 (128): {tip}')

    tag_name_set = seen_names
    for rule in PRESET_RULES:
        for s in rule['scenes']:
            if s not in SCENE_OPTIONS:
                raise ValueError(f'rule {rule["key"]} 场景非法: {s}')
        cat_keys = set()
        for ck, cname, parent_key, order, allow_custom in rule['categories']:
            if ck in cat_keys:
                raise ValueError(f'rule {rule["key"]} 分类 key 重复: {ck}')
            cat_keys.add(ck)
            if len(cname) > 32:
                raise ValueError(f'分类名超长 (32): {cname}')
            # level 由 parent 推导: root=1, child=parent.level+1
            # 但原型没显式标 level, 校验时推导一次确认 <= MAX_CATEGORY_LEVEL
            parent_level = 0
            if parent_key:
                # 找父分类的 level
                for pk, _pn, pp_key, _po, _pa in rule['categories']:
                    if pk == parent_key:
                        # 父的 level: 递归向上推
                        def _parent_level(target_pk, depth=0):
                            for k2, _, pp2, _, _ in rule['categories']:
                                if k2 == target_pk:
                                    if pp2 is None:
                                        return 1
                                    return _parent_level(pp2, depth + 1) + 1
                            return 0
                        parent_level = _parent_level(parent_key)
                        break
            level = parent_level + 1 if parent_key else 1
            if level > MAX_CATEGORY_LEVEL:
                raise ValueError(f'分类层级 > {MAX_CATEGORY_LEVEL}: {rule["key"]}/{ck}')
        for ck, tag_names in rule['assignments'].items():
            if ck not in cat_keys:
                raise ValueError(f'rule {rule["key"]} assignment 引用未知分类: {ck}')
            for tn in tag_names:
                if tn not in tag_name_set:
                    raise ValueError(f'rule {rule["key"]} assignment 引用未知标签: {tn}')


# ---------------------------------------------------------------------------
# 入口: seed_initial_data() - 供 0002 migration + management cmd 调用
# 幂等: 全部 get_or_create, 已存在则跳过
# ---------------------------------------------------------------------------
@transaction.atomic
def seed_initial_data(verbose: bool = False) -> Dict[str, int]:
    """灌入 53 系统标签 + 3 预置规则 (含完整树 + assignment + scene assignment)。

    Returns: {'tags': N, 'rules': M, 'categories': K, 'assignments': L, 'scenes': P}
    """
    _validate_seed()

    # 1) Tags
    tag_objs: Dict[str, ReasonTag] = {}
    for name, en, tip, _grp in SYSTEM_TAGS:
        tag, created = ReasonTag.objects.get_or_create(
            name=name,
            defaults={
                'en_name': en,
                'tip': tip,
                'type': TagType.CUSTOM.value,  # 2026-09-21: 存量标签统一为自定义
                'enabled': True,
            },
        )
        tag_objs[name] = tag

    # 2026-09-21: 系统预置标签 (流程自动写入原因)
    for name, en, tip in PRESET_TAGS:
        ReasonTag.objects.get_or_create(
            name=name,
            defaults={
                'en_name': en,
                'tip': tip,
                'type': TagType.SYSTEM.value,
                'enabled': True,
            },
        )
        if verbose and created:
            print(f'  + tag: {name}')

    # 2) Rules + categories + assignments + scenes
    rule_count = 0
    cat_count = 0
    asn_count = 0
    scene_count = 0
    for rule_def in PRESET_RULES:
        rule, rule_created = SceneRule.objects.get_or_create(
            name=rule_def['name'],
            defaults={
                'is_system': rule_def['is_system'],
                'enabled': rule_def['enabled'],
                'description': f'预置规则 [{rule_def["key"]}]',
            },
        )
        # 已存在时同步 is_system / enabled (避免 seed 重跑时状态漂移)
        if not rule_created:
            dirty = False
            if rule.is_system != rule_def['is_system']:
                rule.is_system = rule_def['is_system']
                dirty = True
            if rule.description != f'预置规则 [{rule_def["key"]}]':
                rule.description = f'预置规则 [{rule_def["key"]}]'
                dirty = True
            if dirty:
                rule.save(update_fields=['is_system', 'description', 'updated_at'])
        rule_count += 1
        if verbose and rule_created:
            print(f'  + rule: {rule.name}')

        # 2a) Categories - 按原型顺序处理, 先父后子
        # 但 rule_def['categories'] 顺序可能父在前子在后, 这里按出现顺序遍历即可
        # (因为 parent 引用的是字符串 key, 等所有父建好后建子)
        cat_key_to_obj: Dict[str, RuleCategory] = {}
        # 计算 level: 父为 None → 1, 否则父.level + 1
        for ck, cname, parent_key, order, allow_custom in rule_def['categories']:
            level = 1
            parent_obj = None
            if parent_key:
                parent_obj = cat_key_to_obj.get(parent_key)
                if parent_obj is None:
                    raise RuntimeError(
                        f'rule {rule_def["key"]} 分类 {ck} 引用了未先建的父 {parent_key}'
                    )
                level = parent_obj.level + 1
            cat, created = RuleCategory.objects.get_or_create(
                rule=rule, name=cname,
                defaults={
                    'parent': parent_obj,
                    'order': order,
                    'allow_custom': allow_custom,
                    'level': level,
                },
            )
            cat_key_to_obj[ck] = cat
            cat_count += 1
            if verbose and created:
                print(f'    + category: {cname} (level {level})')

        # 2b) Assignments
        for ck, tag_names in rule_def['assignments'].items():
            cat_obj = cat_key_to_obj[ck]
            for idx, tn in enumerate(tag_names):
                tag_obj = tag_objs[tn]
                _, created = CategoryAssignment.objects.get_or_create(
                    category=cat_obj, tag=tag_obj,
                    defaults={'order': idx},
                )
                asn_count += 1
                if verbose and created:
                    print(f'      + assignment: {cname} → {tn}' if (cname := cat_obj.name) else '')

        # 2c) Scene assignments - 先清后建 (幂等)
        RuleSceneAssignment.objects.filter(rule=rule).delete()
        for s in rule_def['scenes']:
            RuleSceneAssignment.objects.create(rule=rule, scene=s)
            scene_count += 1

    return {
        'tags': len(SYSTEM_TAGS) + len(PRESET_TAGS),
        'rules': rule_count,
        'categories': cat_count,
        'assignments': asn_count,
        'scenes': scene_count,
    }
