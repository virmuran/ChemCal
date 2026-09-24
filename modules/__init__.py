# ChemCal/modules/__init__.py
"""ChemCal 模块包 — 路径设置"""

import os
import sys
from pathlib import Path

# 添加当前目录到 Python 路径，确保可以导入其他模块
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


def setup_module_paths():
    """将 ChemCal 关键目录添加到 sys.path。

    注意：**不要**再把 `modules/converter` 之类的子包目录注入 sys.path。
    那样会让同一份代码同时以 `calculators.x` 和 `modules.converter.calculators.x`
    两条路径被导入，产生两个互不相认的类对象（`issubclass` 判 False、
    单例失效）。子包一律用包限定导入。
    """
    added_paths = []

    # 项目根目录
    root_dir = Path(__file__).parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
        added_paths.append(str(root_dir))

    return added_paths


# 自动设置模块路径（静默：曾经每次导入都 print 一行，污染日志与测试输出）
setup_module_paths()

# 导出常用函数
__all__ = [
    "setup_module_paths",
]
