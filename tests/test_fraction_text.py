"""分数文本格式的测试。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from arithmetic.fraction_text import format_fraction, parse_fraction


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Fraction(3, 5), "3/5"),          # 真分数：五分之三
        (Fraction(19, 8), "2\u20193/8"),  # 带分数：二又八分之三
        (Fraction(4), "4"),               # 整数
        (Fraction(0), "0"),               # 自然数 0
        (Fraction(7, 24), "7/24"),        # 题目给出的例子
        (Fraction(-19, 8), "-2\u20193/8"),  # 负数只在批改时可能遇到
    ],
)
def test_format_fraction(value: Fraction, expected: str) -> None:
    assert format_fraction(value) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3/5", Fraction(3, 5)),
        ("2\u20193/8", Fraction(19, 8)),   # 题目要求的右单引号
        ("2'3/8", Fraction(19, 8)),        # 容忍 ASCII 撇号
        ("7", Fraction(7)),
        (" 12 ", Fraction(12)),
        ("-3/5", Fraction(-3, 5)),
        ("7/5", Fraction(7, 5)),           # 批改时容忍学生写成假分数
    ],
)
def test_parse_fraction(text: str, expected: Fraction) -> None:
    assert parse_fraction(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "3/0", "1\u2019"])
def test_parse_fraction_rejects_invalid_text(text: str) -> None:
    with pytest.raises(ValueError):
        parse_fraction(text)


def test_format_then_parse_round_trip() -> None:
    for value in [Fraction(0), Fraction(1, 2), Fraction(19, 8), Fraction(9)]:
        assert parse_fraction(format_fraction(value)) == value
