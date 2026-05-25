# ChemCal/base_module.py
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

class BaseModule(QWidget):
    """所有模块的基础类"""
    
    # 定义信号
    data_changed = Signal()  # 数据变化信号
    module_loaded = Signal(str)  # 模块加载完成信号
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.module_name = self.__class__.__name__
    
    def set_data_manager(self, data_manager):
        """设置数据管理器"""
        self.data_manager = data_manager
    
    def get_module_name(self):
        """获取模块名称"""
        return self.module_name
    
    def save_data(self):
        """保存数据 - 子类可重写"""
        pass
    
    def load_data(self):
        """加载数据 - 子类可重写"""
        pass
    
    def refresh(self):
        """刷新模块 - 子类可重写"""
        pass
    
    def on_theme_changed(self, theme_name):
        """主题变化处理 - 子类可重写"""
        pass