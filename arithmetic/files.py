"""题目文件、答案文件与统计结果的读写。

对外只提供少量函数，所有异常都转换成 :mod:`arithmetic.errors` 中定义的可读异常，
避免把 FileNotFoundError、UnicodeDecodeError 之类的底层异常直接抛给用户。
"""

from __future__ import annotations

import re
from pathlib import Path

from arithmetic.errors import FileAccessError, FileFormatError

#: 题号写法之一：数字 + 分隔符，例如「12. 」「12、」「12)」。
_INDEX_WITH_SEPARATOR_RE = re.compile(r"^\s*(\d+)\s*[.\u3001)\uff09]\s*")

#: 题号写法之二：数字 + 空白，但空白之后必须还是数字，
#: 否则 "1 + 1 = " 这样的题目会被误去掉开头的操作数，
#: 而 "1/6 + 1/8 = " 这样的真分数也会被误当成题号「1」。
_INDEX_WITH_SPACE_RE = re.compile(r"^\s*(\d+)\s+(?=\d)")

#: 文本文件编码。真分数使用右单引号（U+2019），必须用 UTF-8 才能正确保存。
FILE_ENCODING = "utf-8"


def read_lines(path: Path, describe: str) -> list[str]:
    """读取文本文件并去掉空行，保留原始顺序。"""
    if not path.exists():
        raise FileAccessError(f"{describe}不存在：{path}")
    if not path.is_file():
        raise FileAccessError(f"{describe}不是普通文件：{path}")

    try:
        text = path.read_text(encoding=FILE_ENCODING)
    except UnicodeDecodeError as exc:
        raise FileAccessError(
            f"{describe}无法按 UTF-8 解码：{path}。请确认文件是纯文本且编码正确。"
        ) from exc
    except OSError as exc:
        raise FileAccessError(f"{describe}读取失败：{path}（{exc.strerror}）") from exc

    return [line.strip() for line in text.splitlines() if line.strip()]


def split_index_prefix(line: str) -> tuple[int | None, str]:
    """把可选的题号前缀与真正的内容分开。

    题目要求「输入的题目都是按照顺序编号的」，但为了让手工编辑过的文件也能批改，
    这里对没有编号的行同样兼容。
    """
    match = _INDEX_WITH_SEPARATOR_RE.match(line) or _INDEX_WITH_SPACE_RE.match(line)
    if match is None:
        return None, line.strip()
    return int(match.group(1)), line[match.end() :].strip()


def write_lines(path: Path, lines: list[str]) -> None:
    """把若干行写入文件，使用 UTF-8 编码与 ``\\n`` 换行。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding=FILE_ENCODING, newline="\n") as handle:
            for line in lines:
                handle.write(line + "\n")
    except OSError as exc:
        raise FileAccessError(f"文件写入失败：{path}（{exc.strerror}）") from exc


def require_same_length(exercises: list[str], answers: list[str]) -> None:
    """题目数与答案数必须一致，否则批改结果没有意义。"""
    if len(exercises) != len(answers):
        raise FileFormatError(
            f"题目文件有 {len(exercises)} 道题，答案文件有 {len(answers)} 个答案，"
            "两者数量不一致，无法批改。"
        )
