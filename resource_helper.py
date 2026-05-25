# ChemCal/resource_helper.py
import sys
import os


def resource_path(relative_path: str) -> str:
    """
    获取资源文件的绝对路径。
    PyInstaller 打包后资源存储在临时目录 sys._MEIPASS，
    开发环境下直接以脚本所在目录为基准。
    """
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, relative_path)


def get_icon_path(icon_name: str) -> str | None:
    """获取图标文件路径，找不到返回 None"""
    local = os.path.join("icons", icon_name)
    if os.path.exists(local):
        return local
    packed = resource_path(f"icons/{icon_name}")
    return packed if os.path.exists(packed) else None
