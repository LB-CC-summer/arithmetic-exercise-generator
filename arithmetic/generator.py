"""题目生成器。

生成算法（约束感知的直接构造，而不是「先随机生成再整题丢弃」）：

1. 随机决定本题的运算符个数 ``k``（1 ~ 3）以及运算符的种类；
2. 递归地随机拆分运算符个数，先构造左子树、再构造右子树；
3. 合并时按运算的数学性质做**局部修正**：

   * 减法：若左值小于右值就交换左右操作数，于是 e1 >= e2 恒成立，不可能出现负数；
   * 除法：先交换到小数在前，再要求 0 < 左值 < 右值，于是商一定是真分数；
     只有两个操作数相等或其中一个为 0 这种退化情形才在本节点内重采样，
     不会把整道题作废重来。

4. 用 :meth:`Expr.canonical_key` 得到的规范键判断题目是否重复，重复则丢弃重生成。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from fractions import Fraction

from arithmetic.errors import CapacityError
from arithmetic.expression import (
    OP_ADD,
    OP_DIV,
    OP_MUL,
    OP_SUB,
    Expr,
)
from arithmetic.fraction_text import format_fraction

#: 每道题目允许出现的运算符个数上限。
MAX_OPERATORS_PER_EXERCISE = 3

#: 单个节点内部允许的重采样次数。失败一次会重新抽取运算符，
#: 因此实际失败概率远低于该数值本身。
_NODE_RETRIES = 32

#: 连续多少次没有抽到新题目，就认为该范围的题目已被抽干。
_CONSECUTIVE_MISS_LIMIT = 20000

#: 取到自然数 0 的概率。0 是题目定义里的自然数，但 ``2 × 0``、``0 + 0``
#: 这类退化题目对练习没有意义，而且会挤占不重复题目的空间，
#: 因此把它的出现概率压到 15%，而不是与其它数值等概率。
_ZERO_PROBABILITY = 0.15


@dataclass(frozen=True)
class Exercise:
    """一道题目及其标准答案。"""

    index: int
    expr: Expr

    @property
    def question_line(self) -> str:
        """题目文件中的一行，例如 ``1. 3/4 + 1/2 = ``。"""
        return f"{self.index}. {self.expr.to_text()} = "

    @property
    def answer_line(self) -> str:
        """答案文件中的一行，例如 ``1. 5/4``。"""
        return f"{self.index}. {format_fraction(self.expr.value)}"


class ExerciseGenerator:
    """按 ``-r`` 给定的数值范围生成不重复的四则运算题目。"""

    def __init__(
        self,
        range_limit: int,
        max_operators: int = MAX_OPERATORS_PER_EXERCISE,
        seed: int | None = None,
    ) -> None:
        if range_limit < 1:
            raise ValueError("range_limit 必须是不小于 1 的自然数")

        self.range_limit = range_limit
        self.max_operators = max_operators
        self._rng = random.Random(seed)
        self._seen: set[tuple] = set()

        # 分母必须小于 r，且分子小于分母，因此 r < 3 时不存在真分数。
        self._fractions_available = range_limit >= 3
        # r = 1 时取值池里只有 0，无法回避「两边都是 0」的算式。
        self._has_nonzero_value = range_limit >= 2
        # 除法要求 0 < 被除数 < 除数，r < 3 时找不到这样的两个数，
        # 此时直接从可选运算符中剔除除号，以免生成违反「商为真分数」的题目。
        self._operators: list[str] = [OP_ADD, OP_SUB, OP_MUL]
        if range_limit >= 3:
            self._operators.append(OP_DIV)

    # ------------------------------------------------------------------ 对外接口

    def generate(self, count: int) -> list[Exercise]:
        """生成 ``count`` 道互不重复的题目。"""
        if count < 1:
            raise ValueError("题目个数必须是正整数")

        exercises: list[Exercise] = []
        consecutive_miss = 0

        while len(exercises) < count:
            expr = self._build(self._rng.randint(1, self.max_operators))
            key = expr.canonical_key()
            if key in self._seen:
                consecutive_miss += 1
                if consecutive_miss >= _CONSECUTIVE_MISS_LIMIT:
                    raise CapacityError(
                        f"在 -r {self.range_limit} 的范围内无法生成 {count} 道互不重复的题目，"
                        f"目前已生成 {len(exercises)} 道。请增大 -r，或减少 -n。"
                    )
                continue

            consecutive_miss = 0
            self._seen.add(key)
            exercises.append(Exercise(index=len(exercises) + 1, expr=expr))

        return exercises

    @property
    def distinct_count(self) -> int:
        """本次生成过程中已经出现过的互不相同的题目个数。"""
        return len(self._seen)

    # ------------------------------------------------------------------ 内部实现

    def _build(self, remaining: int) -> Expr:
        """构造一个恰好含 ``remaining`` 个运算符的表达式。"""
        if remaining == 0:
            return Expr.number(self._random_value())

        for _ in range(_NODE_RETRIES):
            expr = self._try_build(remaining)
            if expr is not None:
                return expr

        raise CapacityError(
            f"在 -r {self.range_limit} 的范围内无法构造满足约束的表达式，"
            "请增大 -r（真分数的分母必须小于 r）。"
        )

    def _try_build(self, remaining: int) -> Expr | None:
        """尝试构造一棵子树；只有除法遇到退化操作数时才返回 ``None``。"""
        op = self._rng.choice(self._operators)
        left_ops = self._rng.randint(0, remaining - 1)
        left = self._build(left_ops)
        right = self._build(remaining - 1 - left_ops)

        # 0 + 0、0 - 0、0 × 0 这类算式没有练习价值，只要还有别的数值可选就重采样。
        if self._has_nonzero_value and left.value == 0 and right.value == 0:
            return None

        if op == OP_SUB:
            # 保证 e1 >= e2：计算过程永远不会出现负数。
            if left.value < right.value:
                left, right = right, left
            return Expr.combine(op, left, right)

        if op == OP_DIV:
            if left.value > right.value:
                left, right = right, left
            # 既要 0 < 商 < 1，又要排除「商为 0」和「商为 1」两种退化情形。
            if left.value > 0 and left.value < right.value:
                return Expr.combine(op, left, right)
            return None

        return Expr.combine(op, left, right)

    def _random_value(self) -> Fraction:
        """随机取一个自然数或一个真分数。"""
        if self.range_limit == 1:
            return Fraction(0)
        if self._rng.random() < _ZERO_PROBABILITY:
            return Fraction(0)
        if self._fractions_available and self._rng.random() < 0.5:
            return self._random_proper_fraction()
        return Fraction(self._rng.randrange(1, self.range_limit))

    def _random_proper_fraction(self) -> Fraction:
        """随机取一个真分数：分子小于分母，且分母小于 ``-r``。"""
        denominator = self._rng.randrange(2, self.range_limit)
        numerator = self._rng.randrange(1, denominator)
        return Fraction(numerator, denominator)
