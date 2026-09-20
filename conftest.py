"""pytest 的根目录配置文件。

它的存在让 pytest 把项目根目录加入 ``sys.path``，于是 ``import arithmetic`` 在
VSCode、命令行或 CI 中都能正常工作，无需额外设置 PYTHONPATH。
"""
