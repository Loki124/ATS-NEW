"""Reason Library 初始数据 (T02 / 0002_seed_initial_data.py + management cmd).

数据来源: ``/Users/loki/Downloads/reason_library_prototype.html`` L596-722。
幂等: 全部用 get_or_create, 重复执行不会重复灌入。

灌入内容:
- 53 条系统标签 (劳动者 / 劳动工具 / 劳动资料 / 劳动对象 / 需求与流程,
  5 大类仅作注释, 不作为标签字段, Q7)
- 1 条预置默认规则 (r-resume, 名「预置默认规则」, is_system=True), 含完整 categories 树
  + assignments + scene assignments。该规则为系统兜底 (覆盖全部场景×类型, 不可调整
  覆盖/名称/状态); 历史上的兄弟规则 r-cancel/r-talent 已于迁移 0012 删除。
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from django.db import transaction
from nanoid import generate as nanoid_generate

from .models import (
    MAX_CATEGORY_LEVEL,
    SCENE_OPTIONS,
    ReasonTag,
    RuleCategory,
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
# 1 条预置默认规则 (原型 L657-722; r-cancel/r-talent 已于 0012 删除)
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
def seed_initial_data(verbose: bool = False, apps=None) -> Dict[str, int]:
    """灌入 53 系统标签 + 3 预置规则 (含完整树 + assignment + scene assignment)。

    Returns: {'tags': N, 'rules': M, 'categories': K, 'assignments': L, 'scenes': P}
    """
    _validate_seed()

    # 数据迁移安全: 从 migration (0002) 调用时传入 apps, 用历史模型操作,
    # 避免引用尚未添加的字段. 关键陷阱 (2026-10-08 实测):
    #   - RuleSceneAssignment.recruit_type 由 0009 添加
    #   - SceneRule.code / version 由 0014 添加, 且 SceneRule.save() 重写会在事务内
    #     自动写 code 列. 0002 早于 0014 运行, 若用实时 SceneRule 模型 → INSERT 触发
    #     save() 重写写 scene_rule.code → OperationalError: no such column.
    #     故 0002 下 SceneRule 也必须走历史模型 (无 code 列、无 save() 重写),
    #     由 0014 的 backfill_code_version RunPython 统一补号.
    # apps 为 None 时 (management cmd / conftest) 保持实时模型, save() 自动补号, 行为不变.
    # 历史 RSA.rule 外键要求历史 SceneRule 实例, 故 scene assignment 用历史实例创建.
    if apps is not None:
        # 0002 数据迁移: 整组 reason_library 模型统一切到历史模型, 避开尚未添加的字段
        # (SceneRule.code/version @0014, RuleSceneAssignment.recruit_type @0009) 及其 save() 重写.
        # 关键: 必须整组一致 —— 否则历史 SceneRule 实例喂不进实时模型的 FK
        #       (ValueError: Cannot query "SceneRule ...": Must be "SceneRule" instance).
        SceneRule = apps.get_model('reason_library', 'SceneRule')
        ReasonTag = apps.get_model('reason_library', 'ReasonTag')
        RuleCategory = apps.get_model('reason_library', 'RuleCategory')
        CategoryAssignment = apps.get_model('reason_library', 'CategoryAssignment')
        RuleSceneAssignment = apps.get_model('reason_library', 'RuleSceneAssignment')
    else:
        # management cmd / conftest: 保持实时模型, save() 自动补号, 行为不变.
        from apps.reason_library.models import (
            CategoryAssignment,
            ReasonTag,
            RuleCategory,
            RuleSceneAssignment,
            SceneRule,
        )

    # 1) Tags
    # 历史模型 (apps 非 None) 无 save() 重写, 不会自动生成 reason_tag.code;
    # 而 code 在 0001 即建且 unique, 必须显式给唯一值, 否则批量插入撞唯一约束.
    # 实时模型 (apps=None) 由 save() 自动补号, 此处不传 code.
    _hist_code = (lambda: f'R{nanoid_generate(size=11)}') if apps is not None else None
    # 历史模型 (apps 非 None) 无 save() 重写 → 不会自动生成 nanoid 主键 id;
    # 而 id 是 CharField PK 且 unique, 必须显式给唯一值, 否则批量插入撞主键唯一约束.
    # (RuleSceneAssignment 在其 create 处已显式传 id; 其余四个 nanoid-PK 模型在此统一注入.)
    _hist_id = (lambda: nanoid_generate(size=21)) if apps is not None else None
    tag_objs: Dict[str, ReasonTag] = {}
    for name, en, tip, _grp in SYSTEM_TAGS:
        tag_defaults = {
            'en_name': en,
            'tip': tip,
            'type': TagType.CUSTOM.value,  # 2026-09-21: 存量标签统一为自定义
            'enabled': True,
        }
        if _hist_code is not None:
            tag_defaults['code'] = _hist_code()
        if _hist_id is not None:
            tag_defaults['id'] = _hist_id()
        tag, created = ReasonTag.objects.get_or_create(
            name=name,
            defaults=tag_defaults,
        )
        tag_objs[name] = tag

    # 2026-09-21: 系统预置标签 (流程自动写入原因)
    for name, en, tip in PRESET_TAGS:
        preset_defaults = {
            'en_name': en,
            'tip': tip,
            'type': TagType.SYSTEM.value,
            'enabled': True,
        }
        if _hist_code is not None:
            preset_defaults['code'] = _hist_code()
        if _hist_id is not None:
            preset_defaults['id'] = _hist_id()
        _, created = ReasonTag.objects.get_or_create(
            name=name,
            defaults=preset_defaults,
        )
        if verbose and created:
            print(f'  + tag: {name}')

    # 2) Rules + categories + assignments + scenes
    rule_count = 0
    cat_count = 0
    asn_count = 0
    scene_count = 0
    for rule_def in PRESET_RULES:
        # apps 非 None → 历史 SceneRule (无 code/version 列、无 save() 重写);
        # 否则实时模型自动补号. 二者均经上方整组历史/实时切换, 此处直接复用.
        rule_model = SceneRule
        rule_defaults = {
            'is_system': rule_def['is_system'],
            'enabled': rule_def['enabled'],
            'description': f'预置规则 [{rule_def["key"]}]',
        }
        # 历史模型下显式给 nanoid 主键 (save() 不自动生成); code 由 0014 backfill 统一补号, 此处不传.
        if _hist_id is not None:
            rule_defaults['id'] = _hist_id()
        rule, rule_created = rule_model.objects.get_or_create(
            name=rule_def['name'],
            defaults=rule_defaults,
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
            cat_defaults = {
                'parent': parent_obj,
                'order': order,
                'allow_custom': allow_custom,
                'level': level,
            }
            # 历史模型下显式给 nanoid 主键 (save() 不自动生成)
            if _hist_id is not None:
                cat_defaults['id'] = _hist_id()
            cat, created = RuleCategory.objects.get_or_create(
                rule=rule, name=cname,
                defaults=cat_defaults,
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
                asn_defaults = {'order': idx}
                # 历史模型下显式给 nanoid 主键 (save() 不自动生成)
                if _hist_id is not None:
                    asn_defaults['id'] = _hist_id()
                _, created = CategoryAssignment.objects.get_or_create(
                    category=cat_obj, tag=tag_obj,
                    defaults=asn_defaults,
                )
                asn_count += 1
                if verbose and created:
                    print(f'      + assignment: {cname} → {tn}' if (cname := cat_obj.name) else '')

        # 2c) Scene assignments - 先清后建 (幂等)
        # RuleSceneAssignment 与 rule 同为历史/实时模型 (上方统一切换), 直接复用 rule 实例.
        _assign_rule = rule
        RuleSceneAssignment.objects.filter(rule=_assign_rule).delete()
        for s in rule_def['scenes']:
            RuleSceneAssignment.objects.create(
                id=nanoid_generate(size=21), rule=_assign_rule, scene=s)
            scene_count += 1

    return {
        'tags': len(SYSTEM_TAGS) + len(PRESET_TAGS),
        'rules': rule_count,
        'categories': cat_count,
        'assignments': asn_count,
        'scenes': scene_count,
    }
