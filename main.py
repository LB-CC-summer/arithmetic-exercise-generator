"""程序入口。

在命令行中这样运行：

.. code-block:: text

    python main.py -n 10 -r 10
    python main.py -e Exercises.txt -a Answers.txt
"""

from __future__ import annotations

from arithmetic.cli import run

if __name__ == "__main__":
    raise SystemExit(run())
