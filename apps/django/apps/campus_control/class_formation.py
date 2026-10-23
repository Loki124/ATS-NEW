"""校招生成班服务（聂荣 2026-10-23《校招生管理系统 - 需求文档》口径）。

## 需求原文

> 人员管理模块 · 字段及规则：班级（按照当前批次每30-35人成立一个班级，默认30人成班，
> 若剩余人数低于10人则均分至所有班级，超过10人则独立成班，若均分后单个班级人数超过35人，
> 则不均分，独立成班）
>
> 轮岗安排模块 · 字段及规则：班级（同上）、班主任（基于班级自动带出可修改）、
> 班长（基于班级自动带出可修改）

## 为什么是「服务」而不是视图里的几行

成班会**写三张表**（建班级 → 挂人 → 带出班主任/班长），且必须满足：

- **幂等**：同批次重复点「一键成班」不能把已分好班的人再分一次；
- **人数守恒**：成班方案的总人数必须等于实际处理的人数（`rules.plan_class_sizes` 保证）；
- **失败不留半成品**：建到一半报错要能整体回滚（否则留下几个空班）。

故收敛到本模块，视图只负责鉴权 + 调服务 + 拼响应。

## 口径真源

成班人数方案在 `apps.campus_rotation.rules.plan_class_sizes`（与批次/导师规则同文件），
本模块只负责「取人 → 建班 → 挂人 → 回填」这四步编排。
"""
from django.db import transaction

from apps.campus_control.models import Person
from apps.campus_rotation.models import ClassRoom
from apps.campus_rotation.rules import plan_class_sizes


def _class_name(batch: str, index: int) -> str:
    """班级名：``<批次>-<序号>``（如 ``260701-01``）。

    ⚠️ `ClassRoom.name` 有唯一约束 → 同批次重建成班时名字会撞；
      本服务靠「跳过已分班人员 + 只补建缺口班」保证不会重名。
    """
    return f'{batch}-{index:02d}'


@transaction.atomic
def form_classes_for_batch(batch: str, *, dry_run: bool = False):
    """按批次一键成班（聂荣口径）。

    :param batch: 批次号（如 ``260701``）
    :param dry_run: True 时只算方案不落库（前端「预览成班方案」用）
    :return: 计划 dict ``{'batch', 'total', 'sizes', 'classes', 'skipped', 'created'}``
    """
    batch = (batch or '').strip()
    if not batch:
        raise ValueError('批次号不能为空')

    # ① 取该批次**尚未分配班级**的人员（已分班的跳过 → 幂等）
    pending = list(
        Person.objects.filter(batch=batch, deleted_at__isnull=True)
        .exclude(class_room_id__isnull=False)
        .order_by('code')
    )
    total = len(pending)
    sizes = plan_class_sizes(total)

    plan = {
        'batch': batch,
        'total': total,
        'sizes': sizes,
        'classes': [],
        'skipped': 0,
        'created': 0,
    }
    if dry_run or total == 0:
        plan['classes'] = [
            {'name': _class_name(batch, i + 1), 'size': size}
            for i, size in enumerate(sizes)
        ]
        return plan

    # ② 建班并挂人
    offset = 0
    existing_names = set(
        ClassRoom.objects.filter(batch=batch).values_list('name', flat=True)
    )
    for i, size in enumerate(sizes):
        members = pending[offset:offset + size]
        offset += size
        name = _class_name(batch, i + 1)
        if name in existing_names:
            # 同名班已存在（重跑）→ 复用它，把这批人挂上去
            classroom = ClassRoom.objects.filter(batch=batch, name=name).first()
        else:
            classroom = ClassRoom(batch=batch, name=name)
            classroom.save()
            existing_names.add(name)
        Person.objects.filter(
            id__in=[p.id for p in members],
        ).update(class_room=classroom, batch=batch)
        plan['classes'].append({'name': name, 'size': len(members)})
        plan['created'] += 1
    return plan
