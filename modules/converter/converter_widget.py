# modules/converter/converter_widget.py
"""换算器标签页 —— 左侧导航 + 右侧各换算页。

导航顺序 = 下面的 CALCULATOR_MODULES 顺序（单一清单：模块、类名、标题一起写），
避免"导入清单"和"页面清单"两处各写一遍、改一处忘一处。
"""
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
                               QStackedWidget, QLabel)
from PySide6.QtCore import Qt
import importlib
import os
import sys
import traceback

# 添加当前目录到路径（仅供无法用包限定名导入时的兜底）
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

#: 换算器清单：(模块路径, 类名, 导航标题) —— 顺序即导航顺序
#: 分三段：基础量 → 力学/热工 → 化工常用物性与传递量
CALCULATOR_MODULES = [
    # ── 基础量 ──
    ("calculators.length_converter", "LengthConverter", "长度换算"),
    ("calculators.weight_converter", "WeightConverter", "重量换算"),
    ("calculators.area_converter", "AreaConverter", "面积换算"),
    ("calculators.volume_converter", "VolumeConverter", "体积换算"),
    ("calculators.flow_converter", "FlowConverter", "流量换算"),
    ("calculators.temperature_converter", "TemperatureConverter", "温度换算"),
    ("calculators.speed_converter", "SpeedConverter", "速度换算"),
    ("calculators.base_converter", "BaseConverter", "进制转换"),
    # ── 力学 / 热工 ──
    ("calculators.energy_converter", "EnergyConverter", "热能换算"),
    ("calculators.pressure_converter", "PressureConverter", "压强换算"),
    ("calculators.power_converter", "PowerConverter", "功率换算"),
    ("calculators.force_converter", "ForceConverter", "力换算"),
    # ── 化工物性与传递量（2026-09-15 扩充）──
    ("calculators.density_converter", "DensityConverter", "密度换算"),
    ("calculators.dynamic_viscosity_converter", "DynamicViscosityConverter", "动力粘度换算"),
    ("calculators.kinematic_viscosity_converter", "KinematicViscosityConverter", "运动粘度换算"),
    ("calculators.surface_tension_converter", "SurfaceTensionConverter", "表面张力换算"),
    ("calculators.thermal_conductivity_converter", "ThermalConductivityConverter", "导热系数换算"),
    ("calculators.heat_transfer_coefficient_converter",
     "HeatTransferCoefficientConverter", "传热系数换算"),
    ("calculators.specific_heat_converter", "SpecificHeatConverter", "比热容换算"),
    ("calculators.calorific_value_converter", "CalorificValueConverter", "热值换算"),
    ("calculators.concentration_converter", "ConcentrationConverter", "浓度换算"),
]

# 逐个导入换算器：一个失败不影响其他。
# 优先用**包限定名**（modules.converter.calculators.xxx）导入 —— 否则同一份文件会以
# `calculators.xxx` 与 `modules.converter.calculators.xxx` 两个模块名各加载一份，
# 产生两个互不相认的类对象（isinstance/issubclass 跨路径判定为 False，测试实测抓到过）。
_PACKAGE = __package__ or "modules.converter"

for _module_path, _class_name, _title in CALCULATOR_MODULES:
    _module, _last_error = None, None
    for _full_name in (f"{_PACKAGE}.{_module_path}", _module_path):
        try:
            _module = importlib.import_module(_full_name)
            break
        except Exception as e:                     # noqa: BLE001
            _last_error = e
    if _module is None:
        print(f"{_class_name} 导入失败: {_last_error}")
        globals()[_class_name] = None
        continue
    _cls = getattr(_module, _class_name, None)
    if _cls is None:
        print(f"{_class_name} 在模块 {_module.__name__} 中不存在")
    globals()[_class_name] = _cls


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

        for _module_path, class_name, title in CALCULATOR_MODULES:
            calculator_class = globals().get(class_name)
            if not calculator_class:
                continue                       # 导入就失败：打印已在上方，直接跳过
            try:
                widget = calculator_class()
                self.add_page(title, widget)
            except Exception as e:
                print(f"{title} 页面创建失败: {e}")
                traceback.print_exc()
                self.add_page(f"{title} (错误)", self.create_error_widget(title, str(e)))

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
        """创建错误显示组件（颜色由主题提供，不写死）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        error_label = QLabel(f"{title} 加载失败\n错误: {error_msg}")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setWordWrap(True)
        error_label.setObjectName("errorLabel")
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
