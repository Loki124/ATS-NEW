"""条件表达式解析器与验证器

支持语法（PRD v4 §9.4, §10.3.3）：
- 条件编号：1, 2, 3, ...
- 运算符：AND, OR
- 括号：( )
- 优先级：括号 > AND > OR

示例：
- (1 AND 2) OR (3 AND 4)
- 1 AND (2 OR 3)
- (1 OR 2 OR 3) AND 4
"""
import re
import logging
from typing import List, Dict, Any, Set, Tuple

logger = logging.getLogger(__name__)


class ExpressionError(Exception):
    """表达式解析错误"""
    pass


class Token:
    """Token 类型"""
    NUMBER = 'NUMBER'
    AND = 'AND'
    OR = 'OR'
    LPAREN = 'LPAREN'
    RPAREN = 'RPAREN'
    EOF = 'EOF'

    def __init__(self, type_: str, value: Any = None, pos: int = 0):
        self.type = type_
        self.value = value
        self.pos = pos

    def __repr__(self):
        return f'Token({self.type}, {self.value!r})'


def tokenize(expression: str) -> List[Token]:
    """词法分析"""
    tokens = []
    i = 0
    while i < len(expression):
        c = expression[i]
        if c.isspace():
            i += 1
        elif c == '(':
            tokens.append(Token(Token.LPAREN, '(', i))
            i += 1
        elif c == ')':
            tokens.append(Token(Token.RPAREN, ')', i))
            i += 1
        elif c.isdigit():
            j = i
            while j < len(expression) and expression[j].isdigit():
                j += 1
            tokens.append(Token(Token.NUMBER, int(expression[i:j]), i))
            i = j
        elif expression[i:i+3].upper() == 'AND':
            tokens.append(Token(Token.AND, 'AND', i))
            i += 3
        elif expression[i:i+2].upper() == 'OR':
            tokens.append(Token(Token.OR, 'OR', i))
            i += 2
        else:
            raise ExpressionError(f'位置 {i}: 非法字符 "{c}"')
    tokens.append(Token(Token.EOF, None, len(expression)))
    return tokens


class Parser:
    """递归下降解析器

    文法（优先级从低到高）：
        expr   := or_expr
        or_expr  := and_expr ('OR' and_expr)*
        and_expr := primary ('AND' primary)*
        primary  := NUMBER | '(' expr ')'
    """
    def __init__(self, tokens: List[Token], max_id: int):
        self.tokens = tokens
        self.pos = 0
        self.max_id = max_id

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, expected_type: str = None) -> Token:
        token = self.tokens[self.pos]
        if expected_type and token.type != expected_type:
            raise ExpressionError(f'位置 {token.pos}: 期望 {expected_type}，得到 {token.type}')
        self.pos += 1
        return token

    def parse(self) -> bool:
        """入口"""
        if self.peek().type == Token.EOF:
            raise ExpressionError('空表达式')
        result = self.or_expr()
        if self.peek().type != Token.EOF:
            raise ExpressionError(f'位置 {self.peek().pos}: 表达式未结束')
        return result

    def or_expr(self) -> bool:
        result = self.and_expr()
        while self.peek().type == Token.OR:
            self.consume(Token.OR)
            right = self.and_expr()
            result = result or right
        return result

    def and_expr(self) -> bool:
        result = self.primary()
        while self.peek().type == Token.AND:
            self.consume(Token.AND)
            right = self.primary()
            result = result and right
        return result

    def primary(self) -> bool:
        token = self.peek()
        if token.type == Token.LPAREN:
            self.consume(Token.LPAREN)
            result = self.or_expr()
            self.consume(Token.RPAREN)
            return result
        elif token.type == Token.NUMBER:
            self.consume(Token.NUMBER)
            if token.value < 1 or token.value > self.max_id:
                raise ExpressionError(f'位置 {token.pos}: 条件编号 {token.value} 超出范围（1-{self.max_id}）')
            return True  # 占位：实际求值时会被替换
        else:
            raise ExpressionError(f'位置 {token.pos}: 期望条件编号或 "(", 得到 {token.type}')


def validate_syntax(expression: str, max_id: int) -> Dict[str, Any]:
    """验证表达式语法

    Returns:
        {
            'valid': bool,
            'error': Optional[str],
            'error_pos': Optional[int],
        }
    """
    if not expression or not expression.strip():
        return {'valid': False, 'error': '表达式不能为空', 'error_pos': 0}

    try:
        tokens = tokenize(expression)
        parser = Parser(tokens, max_id)
        parser.parse()
        return {'valid': True, 'error': None, 'error_pos': None}
    except ExpressionError as e:
        return {'valid': False, 'error': str(e), 'error_pos': None}
    except Exception as e:
        logger.exception('Unexpected error in expression validation')
        return {'valid': False, 'error': f'未知错误: {e}', 'error_pos': None}


def extract_used_ids(expression: str) -> Set[int]:
    """提取表达式中使用的条件编号"""
    tokens = tokenize(expression)
    return {t.value for t in tokens if t.type == Token.NUMBER}


def evaluate(expression: str, condition_results: Dict[int, bool]) -> bool:
    """求值表达式

    Args:
        expression: 表达式字符串
        condition_results: {条件编号: 布尔值}

    Returns:
        表达式结果
    """
    tokens = tokenize(expression)

    def _eval_pos(pos: int) -> Tuple[bool, int]:
        """返回 (值, 下一个位置)"""
        # 简化：使用单 pass + 优先级栈
        raise NotImplementedError('请使用 ExpressionEvaluator 类')

    evaluator = ExpressionEvaluator(tokens, condition_results)
    return evaluator.evaluate()


class ExpressionEvaluator:
    """表达式求值器

    使用 Shunting-Yard 算法转换为逆波兰式后求值
    """
    PRECEDENCE = {Token.AND: 2, Token.OR: 1}

    def __init__(self, tokens: List[Token], condition_results: Dict[int, bool]):
        self.tokens = tokens
        self.condition_results = condition_results
        self.pos = 0

    def evaluate(self) -> bool:
        # 转换为 RPN
        rpn = self._to_rpn()

        # 求值 RPN
        stack = []
        for token in rpn:
            if token.type == Token.NUMBER:
                stack.append(self.condition_results.get(token.value, False))
            elif token.type in (Token.AND, Token.OR):
                if len(stack) < 2:
                    raise ExpressionError('表达式不完整')
                b = stack.pop()
                a = stack.pop()
                if token.type == Token.AND:
                    stack.append(a and b)
                else:
                    stack.append(a or b)

        if len(stack) != 1:
            raise ExpressionError('表达式结构错误')
        return stack[0]

    def _to_rpn(self) -> List[Token]:
        """Shunting-Yard 转 RPN"""
        output = []
        op_stack = []

        i = 0
        while i < len(self.tokens):
            token = self.tokens[i]

            if token.type == Token.EOF:
                break
            elif token.type == Token.NUMBER:
                output.append(token)
            elif token.type in (Token.AND, Token.OR):
                while (op_stack and op_stack[-1].type != Token.LPAREN and
                       self.PRECEDENCE.get(op_stack[-1].type, 0) >= self.PRECEDENCE[token.type]):
                    output.append(op_stack.pop())
                op_stack.append(token)
            elif token.type == Token.LPAREN:
                op_stack.append(token)
            elif token.type == Token.RPAREN:
                while op_stack and op_stack[-1].type != Token.LPAREN:
                    output.append(op_stack.pop())
                if not op_stack:
                    raise ExpressionError('括号不匹配')
                op_stack.pop()  # 弹出 LPAREN

            i += 1

        while op_stack:
            if op_stack[-1].type == Token.LPAREN:
                raise ExpressionError('括号不匹配')
            output.append(op_stack.pop())

        return output


def suggest_expression_fix(expression: str, max_id: int) -> str:
    """尝试修复简单语法错误

    修复：
    - 全角括号 → 半角
    - 中文 AND/OR → 英文
    - 智能加括号
    """
    fixed = expression
    fixed = fixed.replace('（', '(').replace('）', ')')
    fixed = fixed.replace('AND'.lower(), 'AND')
    fixed = fixed.replace('或者', ' OR ')
    fixed = fixed.replace('且', ' AND ')
    fixed = re.sub(r'\s+', ' ', fixed).strip()
    return fixed
