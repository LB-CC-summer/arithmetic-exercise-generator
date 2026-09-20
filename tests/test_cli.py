"""命令行行为的测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from arithmetic.cli import run


def test_generate_writes_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert run(["-n", "10", "-r", "10"]) == 0

    exercises = (tmp_path / "Exercises.txt").read_text(encoding="utf-8").splitlines()
    answers = (tmp_path / "Answers.txt").read_text(encoding="utf-8").splitlines()
    assert len(exercises) == len(answers) == 10
    assert "已生成 10 道题目" in capsys.readouterr().out


def test_range_is_mandatory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert run(["-n", "10"]) == 2
    assert "缺少 -r 参数" in capsys.readouterr().err
    assert not (tmp_path / "Exercises.txt").exists()


def test_no_arguments_returns_usage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert run([]) == 2
    assert "使用方法" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [["-r", "0"], ["-r", "1", "-n", "0"], ["-r", "x"]])
def test_invalid_arguments_return_two(argv: list[str], capsys) -> None:
    assert run(argv) == 2
    assert "error:" in capsys.readouterr().err


def test_grading_mode_writes_grade_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Exercises.txt").write_text("1. 1 + 1 = \n2. 2 + 2 = \n", encoding="utf-8")
    (tmp_path / "Answers.txt").write_text("1. 2\n2. 5\n", encoding="utf-8")

    assert run(["-e", "Exercises.txt", "-a", "Answers.txt"]) == 0
    assert (tmp_path / "Grade.txt").read_text(encoding="utf-8") == "Correct: 1 (1)\nWrong: 1 (2)\n"


def test_grading_requires_both_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert run(["-e", "Exercises.txt"]) == 2
    assert "必须同时给定" in capsys.readouterr().err


def test_modes_cannot_be_mixed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Exercises.txt").write_text("1. 1 + 1 = \n", encoding="utf-8")
    assert run(["-e", "Exercises.txt", "-a", "Answers.txt", "-r", "10"]) == 2
    assert "不能与" in capsys.readouterr().err


def test_help_is_available(capsys) -> None:
    assert run(["-h"]) == 0
    assert "小学四则运算题目自动生成与批改程序" in capsys.readouterr().out
