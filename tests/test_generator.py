"""生成器的约束测试：这是「功能评分」最核心的部分。"""

from __future__ import annotations

import time
from fractions import Fraction

import pytest

from arithmetic.errors import CapacityError
from arithmetic.expression import OP_DIV, OP_SUB
from arithmetic.generator import ExerciseGenerator


def generate(count: int, range_limit: int = 10, seed: int = 20250920):
    return ExerciseGenerator(range_limit, seed=seed).generate(count)


def test_no_negative_result_anywhere() -> None:
    """需求 4：计算过程不能出现负数，即每个 e1 - e2 都满足 e1 >= e2。"""
    for exercise in generate(300):
        for node in exercise.expr.iter_nodes():
            assert node.value >= 0, f"出现负数：{exercise.question_line}"
            if node.op == OP_SUB:
                assert node.left.value >= node.right.value, f"减法不满足 e1 >= e2：{exercise.question_line}"
            if node.op is not None:
                assert node.left.value >= 0 and node.right.value >= 0


def test_division_result_is_always_proper_fraction() -> None:
    """需求 5：e1 ÷ e2 的结果必须是真分数（0 < 商 < 1）。"""
    seen_division = 0
    for exercise in generate(500):
        for node in exercise.expr.iter_nodes():
            if node.op == OP_DIV:
                seen_division += 1
                assert Fraction(0) < node.value < Fraction(1), f"商不是真分数：{exercise.question_line}"
                assert node.left.value < node.right.value
    assert seen_division > 0, "500 道题中应该出现除法"


def test_operator_count_never_exceeds_three() -> None:
    """需求 6：每道题目的运算符不超过 3 个。"""
    for exercise in generate(500):
        count = exercise.expr.operator_count()
        assert 1 <= count <= 3, f"运算符个数越界：{exercise.question_line}"


def test_all_values_are_within_range() -> None:
    """需求 3：题目中的自然数、真分数及其分母都小于 -r 的值。"""
    for exercise in generate(300, range_limit=10):
        for value in exercise.expr.leaves():
            if value.denominator == 1:
                assert 0 <= value < 10, f"自然数越界：{exercise.question_line}"
            else:
                assert 0 < value < 1, f"叶子节点不是真分数：{exercise.question_line}"
                assert value.denominator < 10, f"分数分母越界：{exercise.question_line}"


def test_exercises_are_unique_under_commutative_swap() -> None:
    """需求 7：一次运行生成的题目不能重复。"""
    exercises = generate(1000)
    keys = [exercise.expr.canonical_key() for exercise in exercises]
    assert len(set(keys)) == len(keys) == 1000


def test_supports_ten_thousand_exercises() -> None:
    """需求 9：程序应能支持一万道题目的生成。"""
    started = time.perf_counter()
    exercises = generate(10000, range_limit=10)
    elapsed = time.perf_counter() - started

    assert len(exercises) == 10000
    assert len({exercise.expr.canonical_key() for exercise in exercises}) == 10000
    assert elapsed < 60, f"生成一万道题目耗时过长：{elapsed:.2f} 秒"


def test_text_lines_are_well_formed() -> None:
    exercises = generate(20)
    for exercise in exercises:
        assert exercise.question_line.startswith(f"{exercise.index}. ")
        assert exercise.question_line.endswith(" = ")
        assert "  " not in exercise.question_line  # 运算符与等号前后只有一个空格
        assert exercise.answer_line.startswith(f"{exercise.index}. ")


def test_small_range_still_produces_valid_exercises() -> None:
    """-r 2 时不存在满足约束的除法，程序应自动只使用加减乘。"""
    exercises = generate(30, range_limit=2)
    assert len(exercises) == 30
    for exercise in exercises:
        for node in exercise.expr.iter_nodes():
            assert node.op != OP_DIV


def test_raises_capacity_error_instead_of_hanging() -> None:
    """-r 1 时可选数值只有 0，题目很快被抽干，程序必须报错而不是死循环。"""
    with pytest.raises(CapacityError, match="无法生成"):
        generate(10000, range_limit=1)
