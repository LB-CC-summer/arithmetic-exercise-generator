"""表达式树：求值、渲染与去重用的规范形式。

设计要点：

1. **表达式在构造时就完成求值**。每个节点缓存自己的值，父节点直接用子节点的值
   做一次四则运算即可，避免每渲染一次就递归重算一遍（这是本项目最重要的优化之一）。
2. **渲染必须与结构一一对应**。``to_text()`` 只在「按标准优先级重新解析能够还原
   同一棵树」时才省略括号，因此题目文本不会出现结构歧义，题目里每个子表达式
   都与树上的节点严格对应（子表达式的约束因此也一定成立）。
3. **去重使用「规范化键」**。题目要求判定「能否通过有限次交换 + 和 × 的左右
   操作数变成同一道题」，因此对 ``+``/``×`` 节点把两个子节点的规范键排序，
   对 ``-``/``÷`` 节点保持顺序，得到一棵与二叉树结构一一对应的字符串/元组键。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterator

from arithmetic.fraction_text import format_fraction

OP_ADD = "+"
OP_SUB = "-"
OP_MUL = "\u00d7"
OP_DIV = "\u00f7"

#: 满足交换律的运算符，只有这些运算符的去重才允许交换左右操作数。
COMMUTATIVE_OPS = frozenset({OP_ADD, OP_MUL})

ALL_OPS = (OP_ADD, OP_SUB, OP_MUL, OP_DIV)

_PRECEDENCE = {OP_ADD: 1, OP_SUB: 1, OP_MUL: 2, OP_DIV: 2}


def apply_operator(op: str, left: Fraction, right: Fraction) -> Fraction:
    """按运算符计算两个分数的结果（使用精确分数，不做浮点近似）。"""
    if op == OP_ADD:
        return left + right
    if op == OP_SUB:
        return left - right
    if op == OP_MUL:
        return left * right
    if op == OP_DIV:
        if right == 0:
            raise ZeroDivisionError("除数不能为 0")
        return left / right
    raise ValueError(f"未知运算符：{op!r}")


@dataclass(frozen=True)
class Expr:
    """不可变的表达式树节点。

    ``op`` 为 ``None`` 时表示叶子节点（一个自然数或真分数），否则表示二元运算。
    ``value`` 是整棵子树的值，在构造时算好并缓存。
    """

    value: Fraction
    op: str | None = None
    left: "Expr | None" = None
    right: "Expr | None" = None

    @property
    def is_leaf(self) -> bool:
        return self.op is None

    @staticmethod
    def number(value: Fraction) -> "Expr":
        """构造叶子节点。"""
        return Expr(value=value)

    @staticmethod
    def combine(op: str, left: "Expr", right: "Expr") -> "Expr":
        """构造二元运算节点，并立即求出该节点的值。"""
        return Expr(
            value=apply_operator(op, left.value, right.value),
            op=op,
            left=left,
            right=right,
        )

    # ------------------------------------------------------------------ 结构查询

    def operator_count(self) -> int:
        """返回整棵表达式包含的运算符个数。"""
        if self.is_leaf:
            return 0
        return 1 + self.left.operator_count() + self.right.operator_count()  # type: ignore[union-attr]

    def iter_nodes(self) -> Iterator["Expr"]:
        """先序遍历所有节点，便于校验约束。"""
        yield self
        if not self.is_leaf:
            yield from self.left.iter_nodes()  # type: ignore[union-attr]
            yield from self.right.iter_nodes()  # type: ignore[union-attr]

    def leaves(self) -> list[Fraction]:
        """返回所有叶子节点的值，顺序为从左到右。"""
        if self.is_leaf:
            return [self.value]
        return self.left.leaves() + self.right.leaves()  # type: ignore[union-attr]

    # ------------------------------------------------------------------ 文本渲染

    def to_text(self) -> str:
        """渲染成题目文本，例如 ``3/4 + (1/2 × 2/3)``。"""
        return self._render(parent_op=None, is_right=False)

    def _render(self, parent_op: str | None, is_right: bool) -> str:
        if self.is_leaf:
            return format_fraction(self.value)

        body = (
            f"{self.left._render(self.op, False)} {self.op} "  # type: ignore[union-attr]
            f"{self.right._render(self.op, True)}"  # type: ignore[union-attr]
        )
        if parent_op is not None and _needs_parentheses(parent_op, is_right, self.op):
            return f"({body})"
        return body

    # ------------------------------------------------------------------ 去重键

    def canonical_key(self) -> tuple:
        """返回用于判重的规范键。

        对 ``+`` 与 ``×`` 节点，把两个子树的规范键按字符串序排列，
        等价于「允许任意次交换左右操作数」；对 ``-`` 与 ``÷`` 节点保持左右顺序，
        因为它们既不满足交换律也不满足结合律。
        """
        if self.is_leaf:
            return ("num", str(self.value.numerator), str(self.value.denominator))

        left_key = self.left.canonical_key()  # type: ignore[union-attr]
        right_key = self.right.canonical_key()  # type: ignore[union-attr]
        if self.op in COMMUTATIVE_OPS and repr(right_key) < repr(left_key):
            left_key, right_key = right_key, left_key
        return (self.op, left_key, right_key)

    def __str__(self) -> str:  # pragma: no cover - 调试用
        return self.to_text()


def _needs_parentheses(parent_op: str, is_right: bool, child_op: str) -> bool:
    """判断子表达式渲染时是否需要补括号。

    只有三种情况需要补括号：

    * 子表达式优先级低于父节点，例如 ``(1 + 2) × 3``；
    * 子表达式位于右侧且与父节点同级，例如 ``5 - (2 + 3)``、``5 × (6 ÷ 7 × 8)``。
      左结合解析会把同级右侧的子表达式并进父节点，省略括号就会改变结构；
    * 其余情况（优先级更高，或者位于左侧）按标准优先级解析都能还原，故省略括号。
    """
    parent_precedence = _PRECEDENCE[parent_op]
    child_precedence = _PRECEDENCE[child_op]

    if child_precedence < parent_precedence:
        return True
    if child_precedence > parent_precedence:
        return False
    return is_right
