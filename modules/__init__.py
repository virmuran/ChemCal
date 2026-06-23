# ChemCal/modules/__init__.py
"""ChemCal 模块包 — 路径设置 + 核心数据管理器初始化"""

import os
import sys
from pathlib import Path

# 添加当前目录到 Python 路径，确保可以导入其他模块
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


def setup_module_paths():
    """将 ChemCal 关键目录添加到 sys.path"""
    added_paths = []

    # 项目根目录
    root_dir = Path(__file__).parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
        added_paths.append(str(root_dir))

    # converter 目录
    converter_dir = root_dir / "modules" / "converter"
    if converter_dir.exists() and str(converter_dir) not in sys.path:
        sys.path.insert(0, str(converter_dir))
        added_paths.append(str(converter_dir))

    # process_design 目录
    process_design_dir = root_dir / "modules" / "process_design"
    if process_design_dir.exists() and str(process_design_dir) not in sys.path:
        sys.path.insert(0, str(process_design_dir))
        added_paths.append(str(process_design_dir))

    return added_paths


def init_database(data_file=None):
    """初始化数据管理器"""
    try:
        from data_manager import DataManager

        data_manager = DataManager.get_instance(data_file)

        # 初始化工艺设计数据
        if "process_design" not in data_manager.data:
            data_manager.data["process_design"] = {
                "projects": [],
                "materials": [],
                "equipment": [],
                "streams": []
            }

            # 添加示例物料
            example_materials = [
                {
                    "material_id": "WATER",
                    "name": "水",
                    "cas_number": "7732-18-5",
                    "molecular_formula": "H2O",
                    "molecular_weight": 18.02,
                    "phase": "liquid",
                    "density": 997.0,
                    "boiling_point": 100.0,
                    "melting_point": 0.0,
                    "hazard_class": "无",
                    "notes": "常见溶剂"
                },
                {
                    "material_id": "ETHANOL",
                    "name": "乙醇",
                    "cas_number": "64-17-5",
                    "molecular_formula": "C2H6O",
                    "molecular_weight": 46.07,
                    "phase": "liquid",
                    "density": 789.0,
                    "boiling_point": 78.37,
                    "melting_point": -114.1,
                    "flash_point": 13.0,
                    "hazard_class": "易燃",
                    "notes": "常用有机溶剂"
                }
            ]

            data_manager.data["process_design"]["materials"] = example_materials
            data_manager._save_data()

        return data_manager

    except ImportError as e:
        print(f"无法导入 DataManager: {e}")
        raise
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        raise


def get_data_manager(data_file=None):
    """获取数据管理器实例"""
    try:
        from data_manager import DataManager
        return DataManager.get_instance(data_file)
    except ImportError as e:
        print(f"无法导入 DataManager: {e}")
        raise


# 自动设置模块路径
_added_paths = setup_module_paths()
if _added_paths:
    print(f"已添加模块路径: {_added_paths}")

# 导出常用函数
__all__ = [
    "init_database",
    "get_data_manager",
    "setup_module_paths",
]
