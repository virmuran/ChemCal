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


# 自动设置模块路径（静默：曾经每次导入都 print 一行，污染日志与测试输出）
setup_module_paths()

# 导出常用函数
__all__ = [
    "init_database",
    "get_data_manager",
    "setup_module_paths",
]
