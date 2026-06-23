# ChemCal/data_manager.py
import json
import os
import traceback
import uuid
from datetime import date, datetime
from typing import List, Optional, Dict, Any
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
                    
                    # 确保 process_design 数据结构存在且包含 msds_documents
                    data = self._ensure_process_design_data(data)
                    
                    # 确保设备数据结构存在
                    data = self._ensure_equipment_data(data)
                    
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
    
    def _ensure_process_design_data(self, data):
        """确保 process_design 数据结构完整"""
        if "process_design" not in data:
            data["process_design"] = {
                "projects": [],
                "materials": [],
                "equipment": [],
                "msds_documents": [],
                "streams": []
            }
        else:
            # 确保 msds_documents 字段存在
            if "msds_documents" not in data["process_design"]:
                data["process_design"]["msds_documents"] = []
            
            # 确保所有必要的字段都存在
            required_fields = ["projects", "materials", "equipment", "msds_documents", "streams"]
            for field in required_fields:
                if field not in data["process_design"]:
                    data["process_design"][field] = []
        
        return data
    
    def _ensure_equipment_data(self, data):
        """确保设备数据结构存在"""
        # 检查是否有独立的 equipment 数据，如果有则合并到 process_design 中
        if "equipment" in data and "process_design" in data:
            # 合并独立的 equipment 数据到 process_design.equipment
            for eq in data.get("equipment", []):
                # 检查是否已存在于 process_design.equipment 中
                eq_id = eq.get('equipment_id')
                found = False
                for existing_eq in data["process_design"].get("equipment", []):
                    if existing_eq.get('equipment_id') == eq_id:
                        found = True
                        break
                if not found:
                    data["process_design"].setdefault("equipment", []).append(eq)
            
            # 移除独立的 equipment 字段
            if "equipment" in data:
                del data["equipment"]
                print("已合并独立的设备数据到 process_design.equipment")
        
        # 确保 process_design.equipment 存在
        if "process_design" not in data:
            data["process_design"] = {}
        
        if "equipment" not in data["process_design"]:
            data["process_design"]["equipment"] = []
        
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
        """更新工程信息（新格式）"""
        # 确保包含所有必需的字段
        default_info = {
            "company_name": "",
            "project_number": "",
            "project_name": "",
            "subproject_name": ""
        }
        
        # 合并默认值和提供的值
        merged_info = {**default_info, **project_info}
        
        self.data["project_info"] = merged_info
        if self._save_data():
            self.data_changed.emit("project_info")
            print(f"工程信息已保存: {merged_info}")
        return True
    
    # ==================== 报告计数器相关方法 ====================
    def get_report_counter(self):
        """获取通用的报告计数器"""
        return self.data.get("report_counter", {})
    
    def update_report_counter(self, counter):
        """更新通用的报告计数器"""
        self.data["report_counter"] = counter
        if self._save_data():
            self.data_changed.emit("report_counter")
            print(f"报告计数器已更新: {counter}")
        return True
    
    def get_next_report_number(self, prefix="PD"):
        """获取下一个报告编号"""
        today = datetime.now().strftime("%Y%m%d")
        counter = self.get_report_counter()
        
        # 如果今天是新的一天，重置计数器
        if counter.get("date") != today:
            counter = {"date": today, "count": 1}
        else:
            # 否则递增计数器
            counter["count"] = counter.get("count", 0) + 1
        
        # 保存计数器
        self.update_report_counter(counter)
        
        # 生成报告编号
        report_number = f"{prefix}-{today}-{counter['count']:03d}"
        print(f"生成报告编号: {report_number}")
        return report_number
    
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
    
    # ==================== 设备相关方法 ====================
    def get_equipment_data(self) -> List[Dict]:
        """获取所有设备数据"""
        return self.data.get("process_design", {}).get("equipment", [])
    
    def add_equipment(self, equipment_data: Dict) -> bool:
        """添加设备"""
        try:
            # 安全转换浮点数值
            def safe_float(value, default=0.0):
                try:
                    if isinstance(value, (int, float)):
                        return float(value)
                    elif isinstance(value, str):
                        cleaned = value.strip()
                        # 处理特殊值
                        if cleaned.upper() in ['NT', 'N/A', 'NA', 'NULL', '-', '--', '']:
                            return default
                        return float(cleaned)
                    else:
                        return default
                except (ValueError, TypeError):
                    return default
            
            # 确保浮点数字段正确
            equipment_data['design_pressure'] = safe_float(equipment_data.get('design_pressure', 0))
            equipment_data['design_temperature'] = safe_float(equipment_data.get('design_temperature', 0))
            
            # 确保有设备ID
            if 'equipment_id' not in equipment_data or not equipment_data['equipment_id']:
                equipment_data['equipment_id'] = f"EQ_{uuid.uuid4().hex[:8].upper()}"
            
            # 确保有创建时间
            if 'created_at' not in equipment_data:
                equipment_data['created_at'] = datetime.now().isoformat()
            
            # 更新更新时间
            equipment_data['updated_at'] = datetime.now().isoformat()
            
            # 获取设备列表
            equipment_list = self.data.setdefault("process_design", {}).setdefault("equipment", [])
            
            # 检查是否已存在
            eq_id = equipment_data['equipment_id']
            existing_idx = -1
            for i, eq in enumerate(equipment_list):
                if eq.get("equipment_id") == eq_id:
                    existing_idx = i
                    break
            
            if existing_idx >= 0:
                # 更新现有设备
                equipment_list[existing_idx] = equipment_data
                print(f"更新设备: {eq_id}")
            else:
                # 添加新设备
                equipment_list.append(equipment_data)
                print(f"添加设备: {eq_id}")
            
            return self._save_data()
        except Exception as e:
            print(f"添加设备失败: {e}")
            traceback.print_exc()
            return False
    
    def update_equipment(self, equipment_id: str, update_data: Dict) -> bool:
        """更新设备"""
        try:
            equipment_list = self.get_equipment_data()
            for i, eq in enumerate(equipment_list):
                if eq.get("equipment_id") == equipment_id:
                    # 合并数据
                    equipment_list[i].update(update_data)
                    # 更新更新时间
                    equipment_list[i]["updated_at"] = datetime.now().isoformat()
                    
                    print(f"更新设备: {equipment_id}")
                    return self._save_data()
            
            print(f"设备未找到: {equipment_id}")
            return False
        except Exception as e:
            print(f"更新设备失败: {e}")
            return False
    
    def delete_equipment(self, equipment_id: str) -> bool:
        """删除设备"""
        try:
            equipment_list = self.get_equipment_data()
            for i, eq in enumerate(equipment_list):
                if eq.get("equipment_id") == equipment_id:
                    del equipment_list[i]
                    print(f"删除设备: {equipment_id}")
                    return self._save_data()
            
            print(f"设备未找到: {equipment_id}")
            return False
        except Exception as e:
            print(f"删除设备失败: {e}")
            return False
    
    def get_equipment_by_id(self, equipment_id: str) -> Optional[Dict]:
        """根据ID获取设备"""
        for eq in self.get_equipment_data():
            if eq.get("equipment_id") == equipment_id:
                return eq
        return None
    
    def get_equipment_by_unique_code(self, unique_code: str) -> Optional[Dict]:
        """根据唯一编码获取设备"""
        for eq in self.get_equipment_data():
            if eq.get("unique_code") == unique_code:
                return eq
        return None
    
    # ==================== 物料名称映射相关方法 ====================
    def get_equipment_name_mapping(self):
        """获取设备名称对照表"""
        return self.data.get("equipment_name_mapping", {})

    def add_equipment_name_mapping(self, chinese_name, english_name):
        """添加设备名称对照"""
        mapping = self.data.setdefault("equipment_name_mapping", {})
        mapping[chinese_name] = english_name
        if self._save_data():
            self.data_changed.emit("equipment_name_mapping")
        return True

    def remove_equipment_name_mapping(self, chinese_name):
        """移除设备名称对照"""
        if "equipment_name_mapping" in self.data:
            if chinese_name in self.data["equipment_name_mapping"]:
                del self.data["equipment_name_mapping"][chinese_name]
                if self._save_data():
                    self.data_changed.emit("equipment_name_mapping")
                return True
        return False

    def get_english_name(self, chinese_name):
        """根据中文名称获取英文名称"""
        mapping = self.data.get("equipment_name_mapping", {})
        return mapping.get(chinese_name, "")

    # ==================== 物料相关方法 ====================
    def get_materials(self) -> List[Dict]:
        """获取所有物料数据"""
        return self.data.get("process_design", {}).get("materials", [])
    
    def add_material(self, material_data: Dict) -> bool:
        """添加物料"""
        try:
            materials_list = self.data.setdefault("process_design", {}).setdefault("materials", [])
            materials_list.append(material_data)
            return self._save_data()
        except Exception as e:
            print(f"添加物料失败: {e}")
            return False
    
    # ==================== MSDS相关方法 ====================
    def get_msds_documents(self) -> List[Dict]:
        """获取所有MSDS文档"""
        return self.data.get("process_design", {}).get("msds_documents", [])
    
    def add_msds_document(self, msds_data: Dict) -> bool:
        """添加MSDS文档"""
        try:
            msds_list = self.data.setdefault("process_design", {}).setdefault("msds_documents", [])
            msds_list.append(msds_data)
            return self._save_data()
        except Exception as e:
            print(f"添加MSDS文档失败: {e}")
            return False
    
    # ==================== 项目相关方法 ====================
    def get_projects(self) -> List[Dict]:
        """获取所有项目数据"""
        return self.data.get("process_design", {}).get("projects", [])
    
    def add_project(self, project_data: Dict) -> bool:
        """添加项目"""
        try:
            projects_list = self.data.setdefault("process_design", {}).setdefault("projects", [])
            projects_list.append(project_data)
            return self._save_data()
        except Exception as e:
            print(f"添加项目失败: {e}")
            return False
    
    # ==================== 通用CRUD操作方法 ====================
    def _add_item(self, data_key, item_data, id_field="id"):
        """通用添加项目方法"""
        items = self.data.setdefault(data_key, [])
        if id_field not in item_data:
            item_data[id_field] = self._get_next_id(data_key)
        items.append(item_data)
        if self._save_data():
            self.data_changed.emit(data_key)
            print(f"成功添加项目到 {data_key}: {item_data}")
        else:
            print(f"保存数据失败")
        return item_data
    
    def _update_item(self, data_key, item_id, updates, id_field="id"):
        """通用更新项目方法"""
        for item in self.data.get(data_key, []):
            if item.get(id_field) == item_id:
                for key, value in updates.items():
                    item[key] = value
                if self._save_data():
                    self.data_changed.emit(data_key)
                return True
        return False
    
    def _delete_item(self, data_key, item_id, id_field="id"):
        """通用删除项目方法"""
        self.data[data_key] = [
            item for item in self.data.get(data_key, []) 
            if item.get(id_field) != item_id
        ]
        if self._save_data():
            self.data_changed.emit(data_key)
    
    def _get_items(self, data_key):
        """通用获取项目列表方法"""
        return self.data.get(data_key, [])
    
    def _get_next_id(self, data_key):
        """获取下一个可用的ID"""
        items = self.data.get(data_key, [])
        if not items:
            return 1
        return max(item.get("id", 0) for item in items) + 1
    
    # ==================== 文件夹相关方法 ====================
    def get_folders(self):
        """获取所有文件夹"""
        folders_data = self.data.get("folders", [])
        
        # 处理不同类型的数据结构
        if not folders_data:
            return []
        
        if isinstance(folders_data[0], dict):
            return [folder["name"] for folder in folders_data]
        elif isinstance(folders_data[0], str):
            return folders_data
        else:
            print(f"警告：未知的文件夹数据结构: {folders_data}")
            return []
    
    def add_folder(self, name):
        """添加新文件夹"""
        # 检查是否已存在同名文件夹
        existing_folders = self.get_folders()
        if name in existing_folders:
            print(f"文件夹 '{name}' 已存在！")
            return False
        
        folder = {
            "name": name,
            "created_at": datetime.now().isoformat()
        }
        result = self._add_item("folders", folder, id_field="name")
        
        if result:
            self.data_changed.emit("folders")
            return True
        return False
    
    def delete_folder(self, folder_name):
        """删除文件夹"""
        self.data["folders"] = [
            folder for folder in self.data.get("folders", []) 
            if folder.get("name") != folder_name
        ]
        
        if self._save_data():
            self.data_changed.emit("folders")
        return True
    
    def rename_folder(self, old_name, new_name):
        """重命名文件夹"""
        # 检查新名称是否已存在
        if new_name in [folder.get("name") for folder in self.data.get("folders", [])]:
            return False
        
        # 更新文件夹名称
        for folder in self.data.get("folders", []):
            if folder.get("name") == old_name:
                folder["name"] = new_name
                break
        
        if self._save_data():
            self.data_changed.emit("folders")
        return True

    # ==================== 倒计时相关方法 ====================
    def get_countdowns(self):
        return self._get_items("countdowns")
    
    def add_countdown(self, name, target_date, target_time="23:59"):
        countdown = {
            "name": name,
            "target_date": target_date,
            "target_time": target_time,
            "created_at": datetime.now().isoformat()
        }
        return self._add_item("countdowns", countdown)
    
    def update_countdown(self, countdown_id, **kwargs):
        return self._update_item("countdowns", countdown_id, kwargs)
    
    def delete_countdown(self, countdown_id):
        self._delete_item("countdowns", countdown_id)
    
    # ==================== 自定义倒计时按钮 ====================
    def get_custom_countdown_buttons(self):
        return self._get_items("custom_countdown_buttons")
    
    def add_custom_countdown_button(self, name, minutes):
        button = {
            "name": name,
            "minutes": minutes,
            "created_at": datetime.now().isoformat()
        }
        return self._add_item("custom_countdown_buttons", button)
    
    def update_custom_countdown_button(self, button_id, **kwargs):
        return self._update_item("custom_countdown_buttons", button_id, kwargs)
    
    def delete_custom_countdown_button(self, button_id):
        self._delete_item("custom_countdown_buttons", button_id)
    
    def get_default_data(self):
        """返回默认数据结构（新格式）"""
        default_data = {
            "countdowns": [],
            "custom_countdown_buttons": [],
            "folders": ["工作", "生活", "学习"],
            "project_info": {
                "company_name": "",
                "project_number": "",
                "project_name": "",
                "subproject_name": ""
            },
            "report_counter": {},
            "settings": {},  # 添加空的settings以保持兼容性
            "process_design": {  # 添加 process_design 数据结构
                "projects": [],
                "materials": [],
                "equipment": [],
                "msds_documents": [],  # 添加 MSDS 文档
                "streams": []
            },
            "equipment_name_mapping": {
                "泵": "Pump",
                "压缩机": "Compressor",
                "换热器": "Heat Exchanger",
                "反应器": "Reactor",
                "储罐": "Storage Tank",
                "分离器": "Separator",
                "阀门": "Valve",
                "管道": "Pipe",
                "塔": "Tower",
                "容器": "Vessel"
            }
        }
        
        # 添加一些示例物料
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
            },
            {
                "material_id": "METHANE",
                "name": "甲烷",
                "cas_number": "74-82-8",
                "molecular_formula": "CH4",
                "molecular_weight": 16.04,
                "phase": "gas",
                "density": 0.717,
                "boiling_point": -161.5,
                "melting_point": -182.5,
                "flash_point": -188.0,
                "hazard_class": "易燃",
                "notes": "天然气主要成分"
            }
        ]
        
        default_data["process_design"]["materials"] = example_materials
        
        # 添加一些示例 MSDS 文档
        example_msds = [
            {
                "msds_id": "MSDS-2024-001",
                "material_name": "盐酸",
                "cas_number": "7647-01-0",
                "supplier": "XX化学品公司",
                "version": "2.1",
                "effective_date": "2024-01-01T00:00:00",
                "expiry_date": "2025-01-01T00:00:00",
                "hazard_class": "腐蚀性,有毒",
                "status": "有效",
                "description": "36%盐酸，工业级",
                "created_at": "2024-01-01T10:00:00",
                "updated_at": "2024-01-01T10:00:00",
                "last_updated": "2024-01-01T10:00:00"
            },
            {
                "msds_id": "MSDS-2024-002",
                "material_name": "甲醇",
                "cas_number": "67-56-1",
                "supplier": "YY溶剂公司",
                "version": "1.5",
                "effective_date": "2023-12-01T00:00:00",
                "expiry_date": "2024-12-01T00:00:00",
                "hazard_class": "易燃,有毒",
                "status": "有效",
                "description": "99.9%甲醇，色谱级",
                "created_at": "2023-12-01T14:30:00",
                "updated_at": "2023-12-01T14:30:00",
                "last_updated": "2023-12-01T14:30:00"
            }
        ]
        
        default_data["process_design"]["msds_documents"] = example_msds
        
        return default_data

    def save_flow_diagram(self, diagram_data: dict) -> bool:
        """保存工艺流程图数据"""
        try:
            # 确保 process_design 数据结构存在
            if "process_design" not in self.data:
                self.data["process_design"] = {}
            
            # 保存流程图数据
            self.data["process_design"]["flow_diagram"] = diagram_data
            
            # 保存更新时间
            self.data["process_design"]["flow_diagram_updated"] = datetime.now().isoformat()
            
            return self._save_data()
        except Exception as e:
            print(f"保存工艺流程图数据失败: {e}")
            return False

    def load_flow_diagram(self) -> dict:
        """加载工艺流程图数据"""
        try:
            # 获取流程图数据
            diagram_data = self.data.get("process_design", {}).get("flow_diagram", {})
            
            # 如果没有数据，返回空结构
            if not diagram_data:
                return {}
            
            return diagram_data
        except Exception as e:
            print(f"加载工艺流程图数据失败: {e}")
            return {}

    # ==================== 历史记录相关方法 ====================
    def add_record(self, calculator_id, history_data):
        """添加计算历史记录，委托给 HistoryDB

        Args:
            calculator_id: 计算器标识
            history_data: 历史数据，支持两种格式：
                - {"inputs": {...}, "outputs": {...}}  — 直接含 inputs/outputs
                - {"calculator_name": ..., "inputs": ..., "outputs": ...}  — 含名称
        """
        try:
            from modules.history_db import HistoryDB
            db = HistoryDB()
            if isinstance(history_data, dict):
                calculator_name = history_data.get("calculator_name", calculator_id)
                calculator_category = history_data.get("calculator_category", "工程计算")
                inputs = history_data.get("inputs", {})
                outputs = history_data.get("outputs", {})
                notes = history_data.get("notes", "")
            else:
                calculator_name = calculator_id
                calculator_category = "工程计算"
                inputs = history_data
                outputs = {}
                notes = ""
            db.save(calculator_id, calculator_name, calculator_category, inputs, outputs, notes)
        except Exception as e:
            print(f"保存历史记录失败: {e}")

