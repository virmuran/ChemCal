# ChemCal/data_manager.py
import json
import os
from datetime import date, datetime
from PySide6.QtCore import QObject, Signal

class JSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理datetime和date对象"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

class DataManager(QObject):
    """数据管理类，负责JSON文件的读写 - 单例模式"""
    
    # 单例实例
    _instance = None
    _initialized = False
    
    # 定义信号
    data_changed = Signal(str)  # 数据变更信号，参数为变更的数据类型
    
    def __new__(cls, data_file=None):
        """单例模式的 __new__ 方法"""
        if cls._instance is None:
            cls._instance = super(DataManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, data_file=None):
        """初始化方法 - 只执行一次"""
        # 防止重复初始化
        if DataManager._initialized:
            return
            
        super().__init__()
        
        # 如果没有指定数据文件，使用默认路径
        if data_file is None:
            data_file = self._get_default_data_file_path()
        
        self.data_file = data_file
        print(f"数据文件路径: {self.data_file}")
        self.data = self._load_or_create_data()
        
        DataManager._initialized = True
    
    @classmethod
    def get_instance(cls, data_file=None):
        """获取单例实例的类方法"""
        if cls._instance is None:
            cls._instance = DataManager(data_file)
        return cls._instance
    
    def _get_default_data_file_path(self):
        """获取默认数据文件路径"""
        data_dir = os.path.join(os.path.expanduser("~"), ".ChemCal", "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "ChemCal_data.json")
    
    def _load_or_create_data(self):
        """加载或创建数据文件"""
        # 如果文件存在，尝试加载
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print("数据文件加载成功")
                    
                    # 迁移旧版本的工程信息数据
                    data = self._migrate_project_info_data(data)
                    
                    return data
            except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
                print(f"加载数据文件失败: {e}")
        
        # 如果文件不存在或加载失败，创建默认数据
        print("创建默认数据文件")
        default_data = self.get_default_data()
        self._save_data(default_data)
        return default_data
    
    def _migrate_project_info_data(self, data):
        """迁移旧版本的工程信息数据"""
        if "project_info" in data:
            old_info = data["project_info"]
            new_info = {}
            
            # 迁移公司名称（从旧的设计单位）
            if "design_unit" in old_info:
                new_info["company_name"] = old_info["design_unit"]
            else:
                new_info["company_name"] = ""
                
            # 迁移工程编号（从旧的项目名称或空）
            if "project_name" in old_info:
                # 如果旧的项目名称看起来像是一个编号，可以作为工程编号
                if any(char.isdigit() for char in old_info["project_name"]):
                    new_info["project_number"] = old_info["project_name"]
                else:
                    new_info["project_number"] = ""
                new_info["project_name"] = old_info["project_name"]
            else:
                new_info["project_number"] = ""
                new_info["project_name"] = ""
                
            # 子项名称默认为空
            new_info["subproject_name"] = ""
            
            data["project_info"] = new_info
            
            print("已迁移工程信息数据到新格式")
            
        return data
    
    def _save_data(self, data=None):
        """保存数据到文件"""
        if data is None:
            data = self.data
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            
            # 使用自定义编码器处理datetime对象
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4, cls=JSONEncoder)
            print("数据保存成功")
            return True
        except Exception as e:
            print(f"保存数据失败: {e}")
            return False

    # ==================== 工程信息存储方法（新格式）====================
    def get_project_info(self):
        """获取工程信息（新格式）"""
        return self.data.get("project_info", {
            "company_name": "",
            "project_number": "",
            "project_name": "",
            "subproject_name": ""
        })
    
    def update_project_info(self, project_info):
        """更新工程信息（新格式）

        基于当前值合并：只传部分键时其余字段保持原值不被清空；
        显式传空串则视为清空该字段。
        """
        # 确保包含所有必需的字段
        default_info = {
            "company_name": "",
            "project_number": "",
            "project_name": "",
            "subproject_name": ""
        }

        # 现值打底 + 传入键覆盖（缺省键保留现值，而非默认空串）
        merged_info = {**default_info, **self.get_project_info(),
                       **project_info}

        self.data["project_info"] = merged_info
        if self._save_data():
            self.data_changed.emit("project_info")
            print(f"工程信息已保存: {merged_info}")
        return True
    
    # ==================== 设置相关方法 ====================
    def get_settings(self):
        """获取设置"""
        return self.data.get("settings", {})
    
    def update_settings(self, settings):
        """更新设置"""
        self.data["settings"] = settings
        if self._save_data():
            self.data_changed.emit("settings")
            print("设置已更新")
        return True
    
    def get_default_data(self):
        """返回默认数据结构

        ChemCal 是纯工程计算工具集，数据文件只存两类内容：
        `project_info`（计算书抬头，由 `get_project_info()` 读取）与
        `settings`（界面设置，如主题）。
        """
        return {
            "project_info": {
                "company_name": "",
                "project_number": "",
                "project_name": "",
                "subproject_name": ""
            },
            "settings": {},  # 保持兼容：读取方一律用 .get()，缺键也不报错
        }
