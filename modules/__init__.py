# ChemCal/modules/__init__.py
__version__ = "v1.0.20260131"
__author__ = "ChemCal Team"

import os
import sys
from pathlib import Path

# 添加当前目录到 Python 路径，确保可以导入其他模块
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

def init_database(data_file=None):
    try:
        from ..data_manager import DataManager
        
        # 获取数据管理器实例
        data_manager = DataManager.get_instance(data_file)
        
        # 检查是否有默认的工艺设计数据
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
    try:
        from ..data_manager import DataManager
        return DataManager.get_instance(data_file)
    except ImportError as e:
        print(f"无法导入 DataManager: {e}")
        raise

def setup_module_paths():
    added_paths = []
    
    # 添加当前目录的父目录（ChemCal 根目录）
    root_dir = Path(__file__).parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
        added_paths.append(str(root_dir))
    
    # 添加 converter 目录
    converter_dir = root_dir / "modules" / "converter"
    if converter_dir.exists() and str(converter_dir) not in sys.path:
        sys.path.insert(0, str(converter_dir))
        added_paths.append(str(converter_dir))
    
    # 添加 process_design 目录
    process_design_dir = root_dir / "modules" / "process_design"
    if process_design_dir.exists() and str(process_design_dir) not in sys.path:
        sys.path.insert(0, str(process_design_dir))
        added_paths.append(str(process_design_dir))
    
    return added_paths

def check_module_dependencies():
    dependencies = {
        "PySide6": False,
        "pandas": False,
        "json": True,  # Python 标准库
        "datetime": True,  # Python 标准库
        "pathlib": True,  # Python 标准库
        "dataclasses": True  # Python 3.7+ 标准库
    }
    
    try:
        import PySide6
        dependencies["PySide6"] = True
        dependencies["PySide6_version"] = PySide6.__version__
    except ImportError:
        dependencies["PySide6"] = False
        dependencies["PySide6_error"] = "未安装"
    
    try:
        import pandas
        dependencies["pandas"] = True
        dependencies["pandas_version"] = pandas.__version__
    except ImportError:
        dependencies["pandas"] = False
        dependencies["pandas_error"] = "未安装"
    
    return dependencies

# 自动设置模块路径
_added_paths = setup_module_paths()
if _added_paths:
    print(f"已添加模块路径: {_added_paths}")

# 导出常用函数和类
__all__ = [
    '__version__',
    '__author__',
    'init_database',
    'get_data_manager',
    'init_process_design_modules',
    'setup_module_paths',
    'check_module_dependencies'
]

# 如果直接运行此文件，执行测试
if __name__ == "__main__":
    print(f"ChemCal 模块包 v{__version__}")
    print(f"作者: {__author__}")
    
    print("\n检查模块依赖...")
    deps = check_module_dependencies()
    for dep, status in deps.items():
        if isinstance(status, bool):
            status_str = "OK" if status else "FAIL"
            print(f"  {status_str} {dep}")
    
    print("\n测试数据库初始化...")
    try:
        # 使用测试数据文件
        test_data_file = "test_ChemCal_data.json"
        if os.path.exists(test_data_file):
            os.remove(test_data_file)
        
        dm = init_database(test_data_file)
        print(f"数据管理器初始化成功，实例ID: {id(dm)}")
        
        # 检查工艺设计数据
        if "process_design" in dm.data:
            materials_count = len(dm.data["process_design"].get("materials", []))
            print(f"工艺设计数据存在，包含 {materials_count} 个物料")
        
        # 清理测试文件
        if os.path.exists(test_data_file):
            os.remove(test_data_file)
            print(f"已清理测试文件: {test_data_file}")
            
    except Exception as e:
        print(f"数据库初始化测试失败: {e}")
    
    print("\nChemCal 模块初始化完成")