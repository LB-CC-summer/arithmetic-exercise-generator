"""批改：把题目重新算一遍，再与答案文件逐题比对。

批改时不会读取答案文件里的任何中间信息，而是把 Exercises.txt 的每一行
重新解析、重新计算，再与 Answers.txt 对应行的数值比较。
这样即使答案文件被改错，也能被准确地统计出来。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from arithmetic.errors import FileFormatError
from arithmetic.files import (
    read_lines,
    require_same_length,
    split_index_prefix,
    write_lines,
)
from arithmetic.fraction_text import parse_fraction
from arithmetic.parser import parse_expression

# 批改统计结果的文件名（相对于程序运行的当前目录）。
GRADE_FILE_NAME = "Grade.txt"


@dataclass(frozen=True)
class GradeResult:
    """一次批改的统计结果。"""

    correct: list[int]
    wrong: list[int]

    @property
    def total(self) -> int:
        return len(self.correct) + len(self.wrong)

    def to_lines(self) -> list[str]:
        """按题目要求的格式生成两行统计结果。"""
        return [
            f"Correct: {len(self.correct)} ({_format_indices(self.correct)})",
            f"Wrong: {len(self.wrong)} ({_format_indices(self.wrong)})",
        ]


def _format_indices(indices: list[int]) -> str:
    return ", ".join(str(index) for index in indices)


def grade(exercise_lines: list[str], answer_lines: list[str]) -> GradeResult:
    """批改已经按行读入的题目与答案。"""
    require_same_length(exercise_lines, answer_lines)

    correct: list[int] = []
    wrong: list[int] = []

    for position, (exercise_line, answer_line) in enumerate(
        zip(exercise_lines, answer_lines), start=1
    ):
        index = _resolve_index(exercise_line, position)
        expected = _evaluate_question(exercise_line, position)
        actual = _parse_answer(answer_line, position)
        (correct if expected == actual else wrong).append(index)

    return GradeResult(correct=correct, wrong=wrong)


def run_grading(exercise_path: Path, answer_path: Path, output_path: Path) -> GradeResult:
    """完整批改流程：读文件 -> 重新计算 -> 写 Grade.txt。"""
    exercise_lines = read_lines(exercise_path, "题目文件")
    answer_lines = read_lines(answer_path, "答案文件")

    result = grade(exercise_lines, answer_lines)
    write_lines(output_path, result.to_lines())
    return result


def _resolve_index(line: str, position: int) -> int:
    """取题号；文件里没有写编号时退化为按顺序编号。"""
    index, _ = split_index_prefix(line)
    return index if index is not None else position


def _evaluate_question(line: str, position: int) -> Fraction:
    """计算第 ``position`` 行题目的正确答案。"""
    _, content = split_index_prefix(line)
    if "=" in content:
        content = content.split("=", 1)[0].strip()

    try:
        return parse_expression(content).value
    except FileFormatError as exc:
        raise FileFormatError(f"题目文件第 {position} 行无法解析：{exc}") from exc


def _parse_answer(line: str, position: int) -> Fraction:
    """解析答案文件中的一行。"""
    _, content = split_index_prefix(line)
    if "=" in content:
        content = content.split("=", 1)[-1].strip()

    try:
        return parse_fraction(content)
    except ValueError as exc:
        raise FileFormatError(f"答案文件第 {position} 行无法解析：{exc}") from exc
