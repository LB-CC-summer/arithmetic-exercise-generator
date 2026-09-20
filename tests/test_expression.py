"""表达式树的求值、渲染与去重键测试。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from arithmetic.expression import (
    OP_ADD,
    OP_DIV,
    OP_MUL,
    OP_SUB,
    Expr,
)
from arithmetic.parser import parse_expression


def number(value: int | Fraction) -> Expr:
    return Expr.number(Fraction(value))


def test_fraction_addition_matches_specification_example() -> None:
    """题目给出的例子：1/6 + 1/8 = 7/24。"""
    expr = Expr.combine(OP_ADD, Expr.number(Fraction(1, 6)), Expr.number(Fraction(1, 8)))
    assert expr.value == Fraction(7, 24)


def test_node_caches_value_from_children() -> None:
    expr = Expr.combine(OP_SUB, number(5), number(2))
    assert expr.value == 3
    assert expr.operator_count() == 1


@pytest.mark.parametrize(
    ("expr", "text"),
    [
        # 同级右侧的 - 必须加括号
        (Expr.combine(OP_ADD, number(1), Expr.combine(OP_SUB, number(2), number(3))), "1 + (2 - 3)"),
        # 被减数是复合表达式时必须加括号
        (Expr.combine(OP_SUB, number(5), Expr.combine(OP_ADD, number(2), number(3))), "5 - (2 + 3)"),
        # 被除数是复合表达式时必须加括号
        (Expr.combine(OP_DIV, number(5), Expr.combine(OP_MUL, number(2), number(3))), "5 ÷ (2 × 3)"),
        # 左结合的减法不需要括号
        (Expr.combine(OP_SUB, Expr.combine(OP_SUB, number(9), number(4)), number(2)), "9 - 4 - 2"),
        # 加减运算作为乘法的因子时，优先级更低，必须补括号
        (Expr.combine(OP_MUL, number(3), Expr.combine(OP_ADD, number(1), number(2))), "3 × (1 + 2)"),
        # 乘除优先级高于加减，作为加法的因子时不需要括号
        (Expr.combine(OP_ADD, number(3), Expr.combine(OP_MUL, number(1), number(2))), "3 + 1 × 2"),
        # 同级右侧的子表达式必须补括号，否则会被并进父节点而改变结构
        (
            Expr.combine(
                OP_MUL, number(5), Expr.combine(OP_MUL, Expr.combine(OP_DIV, number(6), number(7)), number(8))
            ),
            "5 × (6 ÷ 7 × 8)",
        ),
    ],
)
def test_to_text_parentheses(expr: Expr, text: str) -> None:
    assert expr.to_text() == text


@pytest.mark.parametrize(
    "text",
    ["1 + 2 + 3", "3 × (1 + 2)", "5 - (2 + 3)", "9 - 4 - 2", "(1/2 × 4) ÷ 2/3"],
)
def test_render_then_parse_rebuilds_the_same_tree(text: str) -> None:
    """渲染与解析互为逆运算：文本解析回来的树必须与原树完全相同。"""
    expr = parse_expression(text)
    assert parse_expression(expr.to_text()) == expr


def test_commutative_swaps_are_duplicates() -> None:
    """23 + 45 与 45 + 23 重复；6 × 8 与 8 × 6 重复。"""
    assert (
        Expr.combine(OP_ADD, number(23), number(45)).canonical_key()
        == Expr.combine(OP_ADD, number(45), number(23)).canonical_key()
    )
    assert (
        Expr.combine(OP_MUL, number(6), number(8)).canonical_key()
        == Expr.combine(OP_MUL, number(8), number(6)).canonical_key()
    )


def test_nested_commutative_swaps_are_duplicates() -> None:
    """题目明确说明：3+(2+1) 与 1+2+3 是重复的题目。"""
    left = parse_expression("3 + (2 + 1)")
    right = parse_expression("1 + 2 + 3")
    assert left.canonical_key() == right.canonical_key()


def test_different_association_is_not_duplicate() -> None:
    """题目明确说明：1+2+3 与 3+2+1 不是重复的题目。"""
    assert parse_expression("1 + 2 + 3").canonical_key() != parse_expression("3 + 2 + 1").canonical_key()


def test_subtraction_and_division_order_matters() -> None:
    assert (
        Expr.combine(OP_SUB, number(3), number(1)).canonical_key()
        != Expr.combine(OP_SUB, number(1), number(3)).canonical_key()
    )
    assert (
        Expr.combine(OP_DIV, number(1), number(2)).canonical_key()
        != Expr.combine(OP_DIV, number(2), number(1)).canonical_key()
    )
