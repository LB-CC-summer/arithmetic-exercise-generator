"""优化前的朴素实现，仅用于性能对比，不参与正式流程。

它和 :mod:`arithmetic.generator` 完成同一件事，但用的是最直观的写法：

1. **整题拒绝采样**：先完全随机地生成一棵表达式树，再检查是否满足
   「计算过程不出现负数」「除法的商是真分数」；只要有一个节点不满足，
   整道题作废、从头再来。运算符越多、嵌套的除法越多，一次成功的概率越低。
2. **两两比较判重**：每生成一道新题，就与已经生成的所有题目逐一做
   「能否通过交换 + 和 × 的左右操作数变成同一道题」的递归比较，
   复杂度是 O(k^2)，其中 k 是已经生成的题目数量。

运行 ``python baseline_naive.py`` 可以看到它与正式实现的耗时对比。
"""

from __future__ import annotations

import random
import time
from fractions import Fraction

from arithmetic.expression import (
    COMMUTATIVE_OPS,
    OP_ADD,
    OP_DIV,
    OP_MUL,
    OP_SUB,
    Expr,
)

MAX_OPERATORS_PER_EXERCISE = 3


def equivalent(left: Expr, right: Expr) -> bool:
    """判断两棵表达式树能否通过交换 + 和 × 的左右操作数变成同一棵树。"""
    if left.is_leaf or right.is_leaf:
        return left.is_leaf and right.is_leaf and left.value == right.value
    if left.op != right.op:
        return False
    if left.op in COMMUTATIVE_OPS:
        same_order = equivalent(left.left, right.left) and equivalent(left.right, right.right)
        swapped = equivalent(left.left, right.right) and equivalent(left.right, right.left)
        return same_order or swapped
    return equivalent(left.left, right.left) and equivalent(left.right, right.right)


class NaiveGenerator:
    """朴素实现：整题拒绝采样 + 两两比较判重。"""

    def __init__(self, range_limit: int, seed: int | None = None) -> None:
        self.range_limit = range_limit
        self._rng = random.Random(seed)
        self._fractions_available = range_limit >= 3
        self._operators = [OP_ADD, OP_SUB, OP_MUL]
        if range_limit >= 3:
            self._operators.append(OP_DIV)

    def generate(self, count: int) -> list[Expr]:
        problems: list[Expr] = []
        while len(problems) < count:
            expr = self._random_valid_expression()
            if expr is None:
                continue
            # 两两比较判重：题目越多，这一步越慢。
            if any(equivalent(expr, other) for other in problems):
                continue
            problems.append(expr)
        return problems

    # ------------------------------------------------------------------ 内部实现

    def _random_valid_expression(self) -> Expr | None:
        try:
            expr = self._build(self._rng.randint(1, MAX_OPERATORS_PER_EXERCISE))
        except ZeroDivisionError:
            return None
        return expr if self._is_valid(expr) else None

    def _build(self, remaining: int) -> Expr:
        if remaining == 0:
            return Expr.number(self._random_value())
        op = self._rng.choice(self._operators)
        left_ops = self._rng.randint(0, remaining - 1)
        left = self._build(left_ops)
        right = self._build(remaining - 1 - left_ops)
        return Expr.combine(op, left, right)

    @staticmethod
    def _is_valid(expr: Expr) -> bool:
        for node in expr.iter_nodes():
            if node.value < 0:
                return False
            if node.op == OP_DIV and not Fraction(0) < node.value < Fraction(1):
                return False
        return True

    def _random_value(self) -> Fraction:
        if self._fractions_available and self._rng.random() < 0.5:
            denominator = self._rng.randrange(2, self.range_limit)
            return Fraction(self._rng.randrange(1, denominator), denominator)
        return Fraction(self._rng.randrange(self.range_limit))


def benchmark(count: int, range_limit: int = 10, seed: int = 20250920) -> tuple[float, int]:
    """返回 (耗时秒数, 生成的题目数)。"""
    started = time.perf_counter()
    problems = NaiveGenerator(range_limit, seed=seed).generate(count)
    return time.perf_counter() - started, len(problems)


if __name__ == "__main__":  # pragma: no cover - 手工运行的性能对比脚本
    for size in (200, 500, 1000, 2000):
        elapsed, produced = benchmark(size)
        print(f"朴素实现 -n {size}: {elapsed:8.2f} 秒（生成 {produced} 道题）")
