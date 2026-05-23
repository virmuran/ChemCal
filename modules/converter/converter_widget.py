# modules/converter/converter_widget.py
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QListWidget, 
                               QListWidgetItem, QStackedWidget, QLabel, QFrame)
from PySide6.QtCore import Qt, QSize
import os
import sys
import traceback

# 添加当前目录到路径，确保可以找到 calculators 模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 尝试导入计算器类，如果失败则设置为 None
ScientificCalculator = None
LoanCalculator = None
TaxCalculator = None
LengthConverter = None
WeightConverter = None
AreaConverter = None
VolumeConverter = None
TemperatureConverter = None
SpeedConverter = None
BaseConverter = None
EnergyConverter = None
PressureConverter = None
PowerConverter = None
ForceConverter = None

# 单独导入每个计算器，这样如果一个失败不会影响其他
calculators_to_import = [
    ("calculators.scientific_calculator", "ScientificCalculator"),
    ("calculators.loan_calculator", "LoanCalculator"),
    ("calculators.tax_calculator", "TaxCalculator"),
    ("calculators.length_converter", "LengthConverter"),
    ("calculators.weight_converter", "WeightConverter"),
    ("calculators.area_converter", "AreaConverter"),
    ("calculators.volume_converter", "VolumeConverter"),
    ("calculators.temperature_converter", "TemperatureConverter"),
    ("calculators.speed_converter", "SpeedConverter"),
    ("calculators.base_converter", "BaseConverter"),
    ("calculators.energy_converter", "EnergyConverter"),
    ("calculators.pressure_converter", "PressureConverter"),
    ("calculators.power_converter", "PowerConverter"),
    ("calculators.force_converter", "ForceConverter")
]

for module_path, class_name in calculators_to_import:
    try:
        module = __import__(module_path, fromlist=[class_name])
        globals()[class_name] = getattr(module, class_name)
    except Exception as e:
        print(f"{class_name} 导入失败: {e}")
        globals()[class_name] = None

class ConverterWidget(QWidget):
    """多功能工具集合模块"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setup_ui()
    
    def setup_ui(self):
        """设置多功能工具UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建左侧导航列表
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(130)
        self.nav_list.setObjectName("converterNavList")  # 样式由主题 QSS 提供
        
        # 创建右侧内容区域
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("converterContentStack")  # 样式由主题 QSS 提供
        
        # 添加导航项和对应的页面
        self.pages = []
        
        # 只添加成功导入的页面，并捕获实例化错误
        page_configs = [
            (ScientificCalculator, "科学计算器"),
            (LoanCalculator, "房贷计算"),
            (TaxCalculator, "个税计算"),
            (LengthConverter, "长度换算"),
            (WeightConverter, "重量换算"),
            (AreaConverter, "面积换算"),
            (VolumeConverter, "体积换算"),
            (TemperatureConverter, "温度换算"),
            (SpeedConverter, "速度换算"),
            (BaseConverter, "进制转换"),
            (EnergyConverter, "热能换算"),
            (PressureConverter, "压强换算"),
            (PowerConverter, "功率换算"),
            (ForceConverter, "力换算")
        ]
        
        for calculator_class, title in page_configs:
            if calculator_class:
                try:
                    widget = calculator_class()
                    self.add_page(title, widget)
                except Exception as e:
                    print(f"{title} 页面创建失败: {e}")
                    traceback.print_exc()
                    # 创建错误页面
                    error_widget = self.create_error_widget(title, str(e))
                    self.add_page(f"{title} (错误)", error_widget)
        
        # 如果没有成功导入任何页面，显示错误信息
        if len(self.pages) == 0:
            error_widget = self.create_error_widget("所有计算器", "无法加载任何计算器模块")
            self.content_stack.addWidget(error_widget)
            self.nav_list.addItem("错误")
        
        # 连接选择事件
        self.nav_list.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        
        # 默认选择第一项
        if self.nav_list.count() > 0:
            self.nav_list.setCurrentRow(0)
        
        # 添加到主布局
        main_layout.addWidget(self.nav_list)
        main_layout.addWidget(self.content_stack, 1)  # 1 表示占据剩余空间
    
    def create_error_widget(self, title, error_msg):
        """创建错误显示组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        error_label = QLabel(f"{title} 加载失败\n错误: {error_msg}")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("color: red; font-size: 14px; padding: 20px;")
        layout.addWidget(error_label)
        
        return widget
        
    def add_page(self, title, widget):
        """添加页面到导航和堆栈"""
        # 添加到导航列表
        self.nav_list.addItem(title)
        
        # 添加到堆栈窗口
        self.content_stack.addWidget(widget)
        
        # 保存页面引用
        self.pages.append(widget)