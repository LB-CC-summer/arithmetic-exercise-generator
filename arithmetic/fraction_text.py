"""真分数的文本格式化与解析。

题目规定的分数写法有两种：

* 真分数 ``3/5``，即分子小于分母；
* 带分数 ``2’3/8``，即整数部分与真分数之间用 ``’``（U+2019，右单引号）分隔。

内部一律使用 :class:`fractions.Fraction` 精确表示，绝不使用浮点数，
这样 ``1/6 + 1/8`` 才能稳定地得到 ``7/24`` 而不是 ``0.2916666...``。
"""

from __future__ import annotations

import re
from fractions import Fraction

#: 带分数允许的分隔符：右单引号（题目要求）、ASCII 撇号、prime 符号。
#: 后两者只是为了容忍手工抄写时写成普通撇号的情况。
MIXED_SEPARATORS = ("\u2019", "'", "\u2032")

#: 匹配「整数」「真分数」「带分数」，允许前导正负号。
_NUMBER_RE = re.compile(
    r"^(?P<sign>[+-]?)"
    r"(?:(?P<whole>\d+)(?P<sep>[\u2019'\u2032]))?"
    r"(?:(?P<num>\d+)/(?P<den>\d+)|(?P<int>\d+))$"
)


def format_fraction(value: Fraction) -> str:
    """把 :class:`Fraction` 渲染成题目要求的文本。

    规则：

    * 分母为 1 时直接输出整数，例如 ``Fraction(4)`` -> ``"4"``；
    * 分子小于分母时输出真分数，例如 ``Fraction(3, 5)`` -> ``"3/5"``；
    * 假分数输出带分数，例如 ``Fraction(19, 8)`` -> ``"2’3/8"``。
    """
    if value.denominator == 1:
        return str(value.numerator)

    sign = "-" if value < 0 else ""
    numerator = abs(value.numerator)
    denominator = value.denominator
    whole, remainder = divmod(numerator, denominator)

    if remainder == 0:  # 约分后其实是整数
        return f"{sign}{whole}"
    if whole == 0:  # 真分数
        return f"{sign}{remainder}/{denominator}"
    return f"{sign}{whole}\u2019{remainder}/{denominator}"


def parse_fraction(text: str) -> Fraction:
    """解析 ``"3/5"``、``"2’3/8"``、``"7"`` 形式的文本。

    解析失败时抛出 :class:`ValueError`，由调用方转换成
    :class:`~arithmetic.errors.FileFormatError` 并给出友好提示。
    """
    compact = text.strip().replace(" ", "")
    if not compact:
        raise ValueError("分数文本为空")

    match = _NUMBER_RE.match(compact)
    if match is None:
        raise ValueError(f"无法识别的数值：{text!r}")

    denominator_text = match.group("den")
    if denominator_text is not None and int(denominator_text) == 0:
        raise ValueError(f"分母不能为 0：{text!r}")

    magnitude = _parse_magnitude(match)
    return -magnitude if match.group("sign") == "-" else magnitude


def _parse_magnitude(match: re.Match[str]) -> Fraction:
    """把正则匹配结果换算成不带符号的 :class:`Fraction`。"""
    whole = int(match.group("whole")) if match.group("whole") else 0
    numerator_text = match.group("num")

    if numerator_text is not None:
        fraction = Fraction(int(numerator_text), int(match.group("den")))
    else:
        fraction = Fraction(int(match.group("int")))

    if match.group("sep") is not None:
        return whole + fraction
    return fraction
