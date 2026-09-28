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

    #: 工程信息标准键 —— 同时是「是否需要从旧格式迁移」的判据（旧格式用 design_unit）
    PROJECT_INFO_KEYS = ("company_name", "project_number",
                         "project_name", "subproject_name")

    #: 已移除模块遗留的数据键（历史残渣，读取时丢弃、保存时不再写回）
    #: 对应模块：倒计时 / 笔记 / 工艺设计 / 流程设计 / 报告计数器 / 设备名称映射，
    #: 已在 v1.12.0 ~ v1.12.1 全部移除
    LEGACY_KEYS = ("countdowns", "custom_countdown_buttons", "folders",
                   "report_counter", "process_design", "equipment_name_mapping")
    
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
        """加载或创建数据文件

        解析失败时**绝不就地覆盖**原文件：先另存为 .corrupt-<时间戳>.json 再从默认
        数据重建 —— 原代码的 `except (..., Exception)` 会吞掉一切异常后直接重建，
        等于静默销毁用户仅有的那份数据（坏文件至少还能手工抢救）。
        """
        # 如果文件存在，尝试加载
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print("数据文件加载成功")

                before = json.dumps(data, sort_keys=True, ensure_ascii=False)
                # 迁移旧版本的工程信息数据 + 丢弃已移除模块的遗留键
                data = self._migrate_project_info_data(data)
                data = self._prune_legacy_keys(data)
                if json.dumps(data, sort_keys=True, ensure_ascii=False) != before:
                    # 迁移/清理结果立刻固化，盘上不再留旧格式与残渣
                    self._save_data(data)

                return data
            except Exception as e:
                print(f"加载数据文件失败: {e}")
                self._quarantine_broken_file()

        # 如果文件不存在或加载失败，创建默认数据
        print("创建默认数据文件")
        default_data = self.get_default_data()
        self._save_data(default_data)
        return default_data

    def _quarantine_broken_file(self):
        """把无法解析的数据文件改名保留下来（不就地覆盖、不删除）"""
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            broken = f"{os.path.splitext(self.data_file)[0]}.corrupt-{ts}.json"
            os.replace(self.data_file, broken)
            print(f"原数据文件已保留为: {broken}")
        except Exception as e:
            print(f"保留原数据文件失败: {e}")

    def _prune_legacy_keys(self, data):
        """丢弃已移除模块遗留的数据键（LEGACY_KEYS）"""
        dropped = [k for k in self.LEGACY_KEYS if k in data]
        for key in dropped:
            data.pop(key, None)
        if dropped:
            print(f"已丢弃遗留数据键: {', '.join(dropped)}")
        return data
    
    def _migrate_project_info_data(self, data):
        """迁移旧版工程信息格式（design_unit → company_name 等）

        ⚠ 本函数位于**每次启动的加载路径**上，判据必须是「缺少新格式标志键」。
        曾用 `if "project_info" in data` 作判据 —— 新格式同样有这个键，于是每次
        启动都把新格式数据当旧格式重迁一遍：
            company_name    ← 旧键 design_unit（新格式没有）          → 清空
            project_number  ← project_name 里的阿拉伯数字（中文名抠不到）→ 清空
            subproject_name ← 硬编码空串                              → 清空
        用户录入四项、重启后只剩 project_name（v1.13.0 实测复现，3/4 字段丢失）。
        """
        info = data.get("project_info")
        if not isinstance(info, dict):
            return data
        # 新格式标志：company_name 是四标准键之一，旧格式用的是 design_unit
        if "company_name" in info:
            return data

        new_info = dict.fromkeys(self.PROJECT_INFO_KEYS, "")
        # 公司名称：从旧的设计单位迁移
        new_info["company_name"] = info.get("design_unit", "") or ""
        # 工程名称：原名保留；若形如编号（含阿拉伯数字）额外当工程编号用
        old_name = info.get("project_name", "") or ""
        new_info["project_name"] = old_name
        if any(ch.isdigit() for ch in old_name):
            new_info["project_number"] = old_name
        # 旧格式若已带这两键则原样继承（有则优先，别丢数据）
        new_info["project_number"] = (info.get("project_number")
                                      or new_info["project_number"])
        new_info["subproject_name"] = info.get("subproject_name", "") or ""

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
        return self.data.get("project_info",
                             dict.fromkeys(self.PROJECT_INFO_KEYS, ""))
    
    def update_project_info(self, project_info):
        """更新工程信息（新格式）

        基于当前值合并：只传部分键时其余字段保持原值不被清空；
        显式传空串则视为清空该字段。
        """
        # 现值打底 + 传入键覆盖（缺省键保留现值，而非默认空串）
        merged_info = {**dict.fromkeys(self.PROJECT_INFO_KEYS, ""),
                       **self.get_project_info(),
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
            "project_info": dict.fromkeys(self.PROJECT_INFO_KEYS, ""),
            "settings": {},  # 保持兼容：读取方一律用 .get()，缺键也不报错
        }
