"""表达式验证服务

封装 apps.process.expressions 的能力，对外暴露稳定的 service 层 API：
- validate_expression(): 校验语法 + 引用编号是否在合法范围内
- evaluate_expression(): 条件求值（给具体 context）
- suggest_fix(): 自动修复简单语法错误
- preview(): 给前端实时反馈（valid/error/suggestion）
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from ..expressions import (
    ExpressionError,
    ExpressionEvaluator,
    extract_used_ids,
    suggest_expression_fix,
    tokenize,
    validate_syntax,
)

logger = logging.getLogger(__name__)


@dataclass
class ExpressionValidationResult:
    """表达式校验结果 - 统一返回结构"""
    valid: bool
    expression: str
    error: Optional[str] = None
    error_pos: Optional[int] = None
    suggestion: Optional[str] = None
    used_ids: Optional[List[int]] = None
    max_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # 去掉 None 让返回更干净
        return {k: v for k, v in d.items() if v is not None}


def validate_expression(expression: str, max_id: int) -> ExpressionValidationResult:
    """对外的表达式校验入口

    Args:
        expression: 条件表达式字符串
        max_id: 最大条件编号（条件项总数）

    Returns:
        ExpressionValidationResult
    """
    result = validate_syntax(expression, max_id)
    used = sorted(extract_used_ids(expression)) if result['valid'] else None

    suggestion = None
    if not result['valid']:
        # 尝试修复建议
        fixed = suggest_expression_fix(expression, max_id)
        if fixed != expression:
            # 修复后再校验一次
            recheck = validate_syntax(fixed, max_id)
            if recheck['valid']:
                suggestion = fixed

    return ExpressionValidationResult(
        valid=result['valid'],
        expression=expression,
        error=result.get('error'),
        error_pos=result.get('error_pos'),
        suggestion=suggestion,
        used_ids=used,
        max_id=max_id,
    )


def evaluate_expression(expression: str, condition_results: Dict[int, bool]) -> bool:
    """求值条件表达式

    Args:
        expression: 条件表达式
        condition_results: {条件序号: 布尔值}

    Returns:
        表达式最终布尔值

    Raises:
        ExpressionError: 表达式非法
    """
    tokens = tokenize(expression)
    evaluator = ExpressionEvaluator(tokens, condition_results)
    return evaluator.evaluate()


def extract_ids(expression: str) -> List[int]:
    """提取表达式中引用的所有条件编号（按出现顺序）"""
    return [t.value for t in tokenize(expression) if t.type == 'NUMBER']
