"""教育经历「院校标签就高原则」的选取口径（聂荣 2026-10-23 需求文档）。

需求原文（人员管理模块 · 个人档案 · 基本信息）：
  「教育经历（**院校标签就高原则**对应的教育经历，包含字段 院校名称、专业、学历）」

## 判定顺序

1. **院校标签高者优先**：``985`` > ``211`` > ``双一流`` > ``其他``
   —— 优先级 = `campus_control.constants.SCHOOLS` 的**声明顺序**，不另造一套优先级表
   （另造必然与下拉枚举漂移）。
2. **标签相同 → 学历高者优先**：博士 > 硕士 > 本科 > 大专 > 中专/中技 > 高中及以下 > 其他
   —— 优先级同样取 `constants.EDUCATIONS` 的声明顺序。
3. **仍相同 → 取最早录入的一条**（``created_at`` 升序）→ 结果**稳定可复现**，
   不随查询顺序抖动。

## 边界

- 无任何教育经历 → 返回 ``None``（调用方回退到 `Person` 自身的单条院校字段，
  保证老数据不空）。
- 标签/学历为空（未采集）→ 视为**最低**优先级（排在所有有效值之后），但仍可被选中
  （只有一条记录时它就是答案）。
"""
from .constants import EDUCATIONS, SCHOOLS

#: 院校标签优先级（**值越大越优先**）；未采集（空串）排在所有有效标签之后
#:
#: ⚠️ `SCHOOLS` 的声明顺序是「**最优在前**」（985 → 211 → 双一流 → 其他），
#:    而本模块用 `max()` 取最高 → 计分必须**反向**（越靠前分越高），
#:    否则会把「其他」当成最优。未知/未采集标签记 0 分（最低）。
SCHOOL_TAG_PRIORITY = {
    tag: len(SCHOOLS) - idx for idx, tag in enumerate(SCHOOLS)
}
#: 学历优先级（值越大越优先）——`EDUCATIONS` 同样是「最优在前」
EDUCATION_PRIORITY = {
    edu: len(EDUCATIONS) - idx for idx, edu in enumerate(EDUCATIONS)
}

_LOWEST = 0


def school_tag_rank(tag) -> int:
    """院校标签优先级；未采集/未知标签 → 最低（0）。"""
    return SCHOOL_TAG_PRIORITY.get((tag or '').strip(), _LOWEST)


def education_rank(education) -> int:
    """学历优先级；未采集/未知学历 → 最低（0）。"""
    return EDUCATION_PRIORITY.get((education or '').strip(), _LOWEST)


def pick_top_education(records):
    """从多条教育经历里挑「院校标签就高」的那一条。

    :param records: 教育经历序列（元素需有 ``school_tag`` / ``education`` /
        ``created_at``；ORM 模型与 dict 都支持）
    :return: 选中的那一条；无记录时返回 ``None``
    """
    items = [r for r in (records or []) if r]
    if not items:
        return None

    def _field(record, name):
        """ORM 模型与 dict 统一取值。"""
        if isinstance(record, dict):
            return record.get(name)
        return getattr(record, name, None)

    def _key(record):
        created = _field(record, 'created_at')
        return (
            school_tag_rank(_field(record, 'school_tag')),
            education_rank(_field(record, 'education')),
            # 最早录入 → 用时间戳取负（越小越靠前）；无时间戳排最后
            -_time_key(created),
        )

    return max(items, key=_key)


def _time_key(value):
    """把 created_at 归一成可比较的数值。

    ⚠️ `created_at` 可能是 ``datetime``（ORM 默认）或 ``date``（测试里手写对象）——
    ``date`` 没有 ``.timestamp()`` → 直接调用会 AttributeError。
    这里统一转成「距 1970 的秒数」，``date`` 按当天零点算。
    """
    if value is None:
        return float('inf')
    if hasattr(value, 'timestamp'):
        return value.timestamp()
    if hasattr(value, 'toordinal'):
        # date → 用序数日（每天一个整数），足够做先后比较
        return float(value.toordinal()) * 86400.0
    return float('inf')
