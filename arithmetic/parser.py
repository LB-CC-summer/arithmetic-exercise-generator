"""把 ``Exercises.txt`` 中的一行题目文本解析回表达式树。

批改功能不能相信题目文件里的答案，必须把题目本身重新解析、重新计算，
因此需要一个独立的递归下降解析器。文法与题目给出的定义完全一致：

.. code-block:: text

    expression := term (('+' | '-') term)*
    term       := factor (('×' | '÷') factor)*
    factor     := number | '(' expression ')'

优先级由文法层级决定：先乘除、后加减，括号可以改变结合顺序。
"""

from __future__ import annotations

import re

from arithmetic.errors import FileFormatError
from arithmetic.expression import (
    OP_ADD,
    OP_DIV,
    OP_MUL,
    OP_SUB,
    Expr,
)
from arithmetic.fraction_text import parse_fraction

#: 一个数字：自然数、真分数（a/b）或带分数（2’3/8）。
_NUMBER_PATTERN = r"\d+(?:[\u2019'\u2032]\d+/\d+|/\d+)?"

_TOKEN_RE = re.compile(
    rf"""
      (?P<space>\s+)
    | (?P<number>{_NUMBER_PATTERN})
    | (?P<op>[+\-\u00d7\u00f7*/\u2212\u2013\u2014])
    | (?P<lparen>[(\uff08])
    | (?P<rparen>[)\uff09])
    """,
    re.VERBOSE,
)

#: 手工输入时容易被写错的符号，统一归一化。
_OPERATOR_ALIASES = {
    "*": OP_MUL,
    "/": OP_DIV,
    "\u2212": OP_SUB,  # 数学减号
    "\u2013": OP_SUB,  # 短破折号
    "\u2014": OP_SUB,  # 长破折号
}


class _TokenStream:
    """把一条题目的文本切成记号序列，并提供「读一个 / 看一个」的操作。"""

    def __init__(self, text: str) -> None:
        self.text = text
        self.tokens: list[tuple[str, str]] = []
        position = 0
        while position < len(text):
            match = _TOKEN_RE.match(text, position)
            if match is None:
                raise FileFormatError(
                    f"题目中出现无法识别的字符：{text[position]!r}（来自 {text!r}）"
                )
            position = match.end()
            kind = match.lastgroup
            if kind != "space":
                self.tokens.append((kind, match.group()))
        self.cursor = 0

    def peek(self) -> tuple[str, str] | None:
        if self.cursor >= len(self.tokens):
            return None
        return self.tokens[self.cursor]

    def next(self) -> tuple[str, str]:
        token = self.peek()
        if token is None:
            raise FileFormatError(f"题目表达式不完整：{self.text!r}")
        self.cursor += 1
        return token


def parse_expression(text: str) -> Expr:
    """解析一条不含等号的表达式文本，返回表达式树。"""
    stream = _TokenStream(text)
    expr = _parse_expression(stream)
    if stream.peek() is not None:
        leftover = stream.next()[1]
        raise FileFormatError(f"表达式 {text!r} 中有多余的字符：{leftover!r}")
    return expr


def _parse_expression(stream: _TokenStream) -> Expr:
    """expression := term (('+' | '-') term)*"""
    node = _parse_term(stream)
    while True:
        token = stream.peek()
        if token is None or token[0] != "op" or _normalize_op(token[1]) not in (OP_ADD, OP_SUB):
            return node
        op = _normalize_op(stream.next()[1])
        node = Expr.combine(op, node, _parse_term(stream))


def _parse_term(stream: _TokenStream) -> Expr:
    """term := factor (('×' | '÷') factor)*"""
    node = _parse_factor(stream)
    while True:
        token = stream.peek()
        if token is None or token[0] != "op" or _normalize_op(token[1]) not in (OP_MUL, OP_DIV):
            return node
        op = _normalize_op(stream.next()[1])
        node = Expr.combine(op, node, _parse_factor(stream))


def _parse_factor(stream: _TokenStream) -> Expr:
    """factor := number | '(' expression ')'"""
    token = stream.peek()
    if token is None:
        raise FileFormatError(f"题目表达式不完整：{stream.text!r}")

    kind, text = token
    if kind == "lparen":
        stream.next()
        node = _parse_expression(stream)
        closing = stream.peek()
        if closing is None or closing[0] != "rparen":
            raise FileFormatError(f"表达式 {stream.text!r} 中的括号不匹配。")
        stream.next()
        return node

    if kind == "number":
        stream.next()
        try:
            return Expr.number(parse_fraction(text))
        except ValueError as exc:
            raise FileFormatError(str(exc)) from exc

    raise FileFormatError(
        f"表达式 {stream.text!r} 的第 {stream.cursor + 1} 个记号不是数字或括号。"
    )


def _normalize_op(text: str) -> str:
    return _OPERATOR_ALIASES.get(text, text)
