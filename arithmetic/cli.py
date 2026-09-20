"""命令行参数解析与流程编排。

两种工作模式互斥：

* 生成模式 ``-n <个数> -r <范围>``：生成题目与答案两个文件；
* 批改模式 ``-e <题目文件> -a <答案文件>``：重新计算并统计正确率。

所有可预期异常都在 :func:`run` 中统一捕获，输出带 ``error:`` 前缀的提示
和一段简易帮助，并返回退出码 2。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from arithmetic.errors import ExerciseError, UsageError
from arithmetic.files import write_lines
from arithmetic.generator import ExerciseGenerator
from arithmetic.grader import GRADE_FILE_NAME, run_grading

#: 生成模式下两个输出文件的名字（存放在程序运行的当前目录）。
EXERCISE_FILE_NAME = "Exercises.txt"
ANSWER_FILE_NAME = "Answers.txt"

#: 未显式给出 -n 时默认生成的题目个数。
DEFAULT_EXERCISE_COUNT = 10

#: 批改模式下，题号明细打印到控制台的最大题目数。
_CONSOLE_DETAIL_LIMIT = 50

USAGE_HINT = """使用方法：
  Myapp.exe -n <题目个数> -r <数值范围>      生成题目与答案
  Myapp.exe -e <题目文件> -a <答案文件>      批改答案并统计

参数说明：
  -n  生成题目的个数，默认 10
  -r  题目中数值（自然数、真分数及其分母）的范围，必须给定
  -e  待批改的题目文件
  -a  待批改的答案文件

提示：使用 -h 可以查看完整帮助。"""


class _ArgumentParser(argparse.ArgumentParser):
    """把 argparse 的默认报错行为改成抛出 :class:`UsageError`。"""

    def error(self, message: str) -> None:  # noqa: D102 - 覆盖父类行为
        raise UsageError(message)


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = _ArgumentParser(
        prog="Myapp.exe",
        description="小学四则运算题目自动生成与批改程序",
        epilog=USAGE_HINT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=None,
        metavar="N",
        help="生成题目的个数（默认 10）",
    )
    parser.add_argument(
        "-r",
        "--range",
        dest="range_limit",
        type=int,
        default=None,
        metavar="R",
        help="题目中数值（自然数、真分数及其分母）的范围，必须给定",
    )
    parser.add_argument(
        "-e",
        "--exercise",
        type=Path,
        default=None,
        metavar="FILE",
        help="待批改的题目文件",
    )
    parser.add_argument(
        "-a",
        "--answer",
        type=Path,
        default=None,
        metavar="FILE",
        help="待批改的答案文件",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    """程序主流程，返回进程退出码。"""
    try:
        args = build_parser().parse_args(argv)
        if args.exercise is not None or args.answer is not None:
            return _run_grading(args)
        return _run_generation(args)
    except SystemExit as exc:  # -h / --help
        return int(exc.code or 0)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(USAGE_HINT, file=sys.stderr)
        return 2
    except ExerciseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _run_generation(args: argparse.Namespace) -> int:
    """生成模式：写 Exercises.txt 与 Answers.txt。"""
    if args.range_limit is None:
        raise UsageError(
            "缺少 -r 参数。 -r 用于限定题目中数值（自然数、真分数及其分母）的范围，必须给定。"
        )
    if args.range_limit < 1:
        raise UsageError("-r 必须是不小于 1 的自然数。")
    if args.number is not None and args.number < 1:
        raise UsageError("-n 必须是正整数。")

    count = args.number if args.number is not None else DEFAULT_EXERCISE_COUNT
    exercises = ExerciseGenerator(args.range_limit).generate(count)

    exercise_path = Path.cwd() / EXERCISE_FILE_NAME
    answer_path = Path.cwd() / ANSWER_FILE_NAME
    write_lines(exercise_path, [exercise.question_line for exercise in exercises])
    write_lines(answer_path, [exercise.answer_line for exercise in exercises])

    print(f"已生成 {len(exercises)} 道题目：{exercise_path}")
    print(f"对应的答案：{answer_path}")
    return 0


def _run_grading(args: argparse.Namespace) -> int:
    """批改模式：写 Grade.txt。"""
    if args.exercise is None or args.answer is None:
        raise UsageError("-e 与 -a 必须同时给定，例如：Myapp.exe -e Exercises.txt -a Answers.txt")
    if args.range_limit is not None or args.number is not None:
        raise UsageError("-n / -r 只能用于生成模式，不能与 -e / -a 同时使用。")

    output_path = Path.cwd() / GRADE_FILE_NAME
    result = run_grading(args.exercise, args.answer, output_path)

    print(f"共批改 {result.total} 道题，统计结果已写入：{output_path}")
    print(f"Correct: {len(result.correct)}    Wrong: {len(result.wrong)}")
    # 题目很多时题号列表会刷满屏幕，只有规模不大时才把它打印出来，
    # 完整结果始终写在 Grade.txt 中。
    if result.total <= _CONSOLE_DETAIL_LIMIT:
        for line in result.to_lines():
            print(line)
    return 0
