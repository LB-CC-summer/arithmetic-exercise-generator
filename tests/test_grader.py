"""批改功能的测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from arithmetic.errors import FileAccessError, FileFormatError
from arithmetic.grader import grade, run_grading


def test_all_correct() -> None:
    exercises = ["1. 1/6 + 1/8 = ", "2. 3 × (1 + 2) = "]
    answers = ["1. 7/24", "2. 9"]
    result = grade(exercises, answers)
    assert result.correct == [1, 2]
    assert result.wrong == []


def test_mixed_correct_and_wrong() -> None:
    """统计结果必须严格等于题目要求的格式。"""
    exercises = [f"{index}. 1 + 1 = " for index in range(1, 11)]
    answers = [f"{index}. 2" if index % 2 == 1 else f"{index}. 3" for index in range(1, 11)]
    result = grade(exercises, answers)
    assert result.to_lines() == [
        "Correct: 5 (1, 3, 5, 7, 9)",
        "Wrong: 5 (2, 4, 6, 8, 10)",
    ]


@pytest.mark.parametrize(
    ("exercise", "answer"),
    [
        ("1. 1/6 + 1/8 = ", "1. 7/24"),      # 标准写法
        ("1. 3/2 + 1/2 = ", "1. 2"),         # 假分数约分后等于整数
        ("1. 1’1/2 + 1/2 = ", "1. 2"),       # 带分数参与运算
        ("1. 1/6 + 1/8 = ", "1. 7/23"),      # 算错了
    ],
)
def test_fraction_comparison(exercise: str, answer: str) -> None:
    result = grade([exercise], [answer])
    expected_correct = not answer.endswith("7/23")
    assert (result.correct == [1]) is expected_correct


def test_decimal_answer_is_rejected_as_format_error() -> None:
    """答案只允许自然数与真分数，小数属于格式错误，程序会明确报错。"""
    with pytest.raises(FileFormatError, match="答案文件第 1 行"):
        grade(["1. 1/6 + 1/8 = "], ["1. 0.29"])


def test_accepts_files_without_index_prefix() -> None:
    """兼容手工删除编号的题目文件。"""
    result = grade(["1/6 + 1/8 = ", "1 + 1 = "], ["7/24", "2"])
    assert result.correct == [1, 2]


def test_answer_written_after_equals_sign_is_accepted() -> None:
    result = grade(["1. 1/6 + 1/8 = "], ["1. 1/6 + 1/8 = 7/24"])
    assert result.correct == [1]


def test_mismatched_length_raises() -> None:
    with pytest.raises(FileFormatError, match="数量不一致"):
        grade(["1. 1 + 1 = "], ["1. 2", "2. 3"])


def test_invalid_exercise_line_raises() -> None:
    with pytest.raises(FileFormatError, match="无法解析"):
        grade(["1. 1 + + 2 = "], ["1. 3"])


def test_run_grading_writes_grade_file(tmp_path: Path) -> None:
    exercise_file = tmp_path / "Exercises.txt"
    answer_file = tmp_path / "Answers.txt"
    grade_file = tmp_path / "Grade.txt"
    exercise_file.write_text("1. 1 + 1 = \n2. 2 × 3 = \n", encoding="utf-8")
    answer_file.write_text("1. 2\n2. 7\n", encoding="utf-8")

    result = run_grading(exercise_file, answer_file, grade_file)

    assert result.correct == [1]
    assert result.wrong == [2]
    assert grade_file.read_text(encoding="utf-8") == "Correct: 1 (1)\nWrong: 1 (2)\n"


def test_missing_file_raises_readable_error(tmp_path: Path) -> None:
    with pytest.raises(FileAccessError, match="不存在"):
        run_grading(tmp_path / "nope.txt", tmp_path / "nope2.txt", tmp_path / "Grade.txt")
