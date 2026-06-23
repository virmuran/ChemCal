"""
ChemCal 系统诊断工具 — 依赖检查 + 自检功能

从 modules/__init__.py 拆分而来，减轻包初始化文件的职责。
"""

import os
import sys


def check_module_dependencies():
    """检查项目所需 Python 包的安装状态"""
    dependencies = {
        "PySide6": False,
        "json": True,        # Python 标准库
        "datetime": True,    # Python 标准库
        "pathlib": True,     # Python 标准库
        "dataclasses": True, # Python 3.7+ 标准库
    }

    try:
        import PySide6
        dependencies["PySide6"] = True
        dependencies["PySide6_version"] = PySide6.__version__
    except ImportError:
        dependencies["PySide6"] = False
        dependencies["PySide6_error"] = "未安装"

    return dependencies


def run_self_test():
    """运行模块自检（开发调试用）"""
    print("=" * 40)
    print("  ChemCal 系统诊断")
    print("=" * 40)

    print("\n模块依赖检查...")
    deps = check_module_dependencies()
    for dep, status in deps.items():
        if isinstance(status, bool):
            status_str = "✅ OK" if status else "❌ FAIL"
            print(f"  {status_str}  {dep}")

    print("\n数据管理器测试...")
    try:
        from data_manager import DataManager
        dm = DataManager.get_instance()
        print(f"  ✅ DataManager 实例: {id(dm)}")
    except Exception as e:
        print(f"  ❌ DataManager: {e}")

    print("\n" + "=" * 40)
    print("  诊断完成")
    print("=" * 40)


if __name__ == "__main__":
    run_self_test()
