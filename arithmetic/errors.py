"""项目自定义异常。

所有可以预期的错误都派生自 :class:`ExerciseError`，由命令行层统一捕获，
输出带 ``error:`` 前缀的可读提示，而不是打印 Python 的调用堆栈。
这样即使输入文件有问题，用户看到的也是一句能看懂的中文说明。
"""

from __future__ import annotations


class ExerciseError(Exception):
    """本项目所有可预期异常的基类。"""


class UsageError(ExerciseError):
    """命令行参数缺失、冲突或取值不合法。"""


class CapacityError(ExerciseError):
    """在当前 ``-r`` 范围下无法生成足够多的不重复题目。"""


class FileFormatError(ExerciseError):
    """题目文件或答案文件的内容不符合规范。"""


class FileAccessError(ExerciseError):
    """文件不存在、不是普通文件，或者没有读写权限。"""
