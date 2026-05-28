from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QGridLayout,
    QFileDialog, QDialog, QDialogButtonBox, QTabWidget, QSpinBox,
    QButtonGroup, QFrame, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math
import re
from datetime import datetime
from modules.combo_box_utils import ComboBoxWheelBlocker


COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #888;
        border-radius: 4px;
        padding: 6px 10px;
        /* background via theme */
        /* color via theme */
    }
    QComboBox QAbstractItemView {
        /* background-color via theme */
        /* color via theme */
        border: 1px solid #888;
        selection-background-color: #3498db;
        selection-color: black;
    }
    QComboBox QAbstractItemView::item {
        padding: 3px 8px;
    }
"""
class 篮式过滤器(QWidget):
    """篮式过滤器设计与压降计算器"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        
        # 使用传入的数据管理器或创建新的
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        
        self.setup_ui()
        self.setup_default_values()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self._wheel_blocker = ComboBoxWheelBlocker(self)
        for combo in self.findChildren(QComboBox):
            combo.installEventFilter(self._wheel_blocker)
    
    def init_data_manager(self):
        """初始化数据管理器 - 使用单例模式"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
            print("使用共享的数据管理器实例")
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None
    
    def setup_ui(self):
        """设置篮式过滤器设计计算UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧：输入参数区域
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        scroll_left.setWidgetResizable(True)

        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # 说明文本
        description = QLabel(
            "篮式过滤器设计计算器 - 根据流体参数、工况条件和过滤要求，进行过滤器设计和压降计算。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 流体介质参数组
        fluid_group = self.create_group_box("流体介质参数")
        fluid_layout = QGridLayout(fluid_group)
        self.setup_fluid_parameters(fluid_layout)
        left_layout.addWidget(fluid_group)
        
        # 系统工况参数组
        system_group = self.create_group_box("系统工况参数")
        system_layout = QGridLayout(system_group)
        self.setup_system_parameters(system_layout)
        left_layout.addWidget(system_group)
        
        # 过滤核心参数组
        filter_group = self.create_group_box("过滤核心参数")
        filter_layout = QGridLayout(filter_group)
        self.setup_filter_parameters(filter_layout)
        left_layout.addWidget(filter_group)
        
        # 结构与材料参数组
        structure_group = self.create_group_box("结构与材料参数")
        structure_layout = QGridLayout(structure_group)
        self.setup_structure_parameters(structure_layout)
        left_layout.addWidget(structure_group)
        
        # 经济参数组
        economic_group = self.create_group_box("经济参数")
        economic_layout = QGridLayout(economic_group)
        self.setup_economic_parameters(economic_layout)
        left_layout.addWidget(economic_group)
        
        # 按钮区域
        self.setup_buttons(left_layout)
        
        left_layout.addStretch()
        
        # 右侧：结果显示区域
        right_widget = QWidget()
        right_widget.setMinimumWidth(400)
        right_widget.setMaximumWidth(500)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        
        # 创建结果Tab
        self.result_tabs = self.create_result_tabs()
        right_layout.addWidget(self.result_tabs)
        
        # 复制按钮
        copy_btn = QPushButton(" 复制结果")
        copy_btn.clicked.connect(self.copy_results_to_clipboard)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover:!checked {
                background-color: #8e44ad;
            }
        """)
        right_layout.addWidget(copy_btn)
        
        # 将左右两部分添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)
    
    def create_group_box(self, title):
        """创建统一的GroupBox"""
        group = QGroupBox(title)
        return group
    
    def add_labeled_input(self, layout, row, col, label_text, widget, placeholder=None, validator=None, read_only=False):
        """添加带标签的输入控件"""
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                padding-right: 10px;
                min-width: 100px;
            }
        """)
        layout.addWidget(label, row, col)
        
        # 根据widget类型设置属性
        if isinstance(widget, QLineEdit):
            if placeholder:
                widget.setPlaceholderText(placeholder)
            if validator:
                widget.setValidator(validator)
            if read_only:
                widget.setReadOnly(True)
        
        widget.setFixedWidth(180)  # 统一宽度
        layout.addWidget(widget, row, col + 1)
        return widget
    
    def setup_fluid_parameters(self, layout):
        """设置流体参数输入"""
        layout.setVerticalSpacing(12)
        layout.setHorizontalSpacing(20)
        
        # 第0行：介质名称和介质密度
        self.fluid_name_input = self.add_labeled_input(layout, 0, 0, "介质名称:", QLineEdit(), "例如：循环水")
        self.density_input = self.add_labeled_input(layout, 0, 2, "密度 (kg/m³):", QLineEdit(), "例如：992.0", QDoubleValidator(1, 3000, 3))
        
        # 第1行：动力粘度和介质腐蚀性
        self.viscosity_input = self.add_labeled_input(layout, 1, 0, "动力粘度 (Pa·s):", QLineEdit(), "例如：0.001002", QDoubleValidator(1e-6, 10, 6))
        
        # 介质腐蚀性下拉框
        self.corrosion_combo = QComboBox()
        self.corrosion_combo.setStyleSheet(COMBOBOX_STYLE)
        self.corrosion_combo.addItems(["无腐蚀", "弱腐蚀", "中等腐蚀", "强腐蚀", "特殊腐蚀性"])
        self.add_labeled_input(layout, 1, 2, "介质腐蚀性:", self.corrosion_combo)
    
    def setup_system_parameters(self, layout):
        """设置系统工况参数输入"""
        layout.setVerticalSpacing(12)
        layout.setHorizontalSpacing(20)
        
        # 第0行：设计流量和设计压力
        self.flow_input = self.add_labeled_input(layout, 0, 0, "设计流量 (m³/h):", QLineEdit(), "例如：150.0", QDoubleValidator(0.1, 100000, 1))
        self.pressure_input = self.add_labeled_input(layout, 0, 2, "设计压力 (MPa):", QLineEdit(), "例如：1.6", QDoubleValidator(0.01, 10, 2))
        
        # 第1行：设计温度和允许压降
        self.temp_input = self.add_labeled_input(layout, 1, 0, "设计温度 (°C):", QLineEdit(), "例如：80.0", QDoubleValidator(-50, 500, 1))
        self.max_pressure_drop_input = self.add_labeled_input(layout, 1, 2, "允许压降 (kPa):", QLineEdit(), "例如：50.0", QDoubleValidator(0.1, 1000, 1))
    
    def setup_filter_parameters(self, layout):
        """设置过滤核心参数输入"""
        layout.setVerticalSpacing(12)
        layout.setHorizontalSpacing(20)
        
        # 第0行：过滤精度和滤网材质
        self.mesh_input = self.add_labeled_input(layout, 0, 0, "过滤精度 (μm):", QLineEdit(), "例如：3000.0", QDoubleValidator(1, 10000, 1))
        
        # 滤网材质下拉框
        self.material_combo = QComboBox()
        self.material_combo.setStyleSheet(COMBOBOX_STYLE)
        self.add_labeled_input(layout, 0, 2, "滤网材质:", self.material_combo)
        
        # 第1行：滤网开孔率和推荐过滤速度
        self.porosity_input = self.add_labeled_input(layout, 1, 0, "滤网开孔率 (%):", QLineEdit(), "例如：35.0", QDoubleValidator(10, 80, 1))
        self.velocity_input = self.add_labeled_input(layout, 1, 2, "过滤速度 (m/s):", QLineEdit(), "例如：0.1", QDoubleValidator(0.01, 5, 3))
    
    def setup_structure_parameters(self, layout):
        """设置结构与材料参数输入"""
        layout.setVerticalSpacing(12)
        layout.setHorizontalSpacing(20)
        
        # 第0行：滤网丝径和支撑网厚度
        self.wire_diameter_input = QLineEdit()
        self.add_labeled_input(layout, 0, 0, "滤网丝径 (m):", self.wire_diameter_input, "自动计算", read_only=True)
        
        self.support_thickness_input = self.add_labeled_input(layout, 0, 2, "支撑网厚度 (m):", QLineEdit(), "例如：0.002", QDoubleValidator(0.001, 0.05, 4))
        
        # 第1行：材料许用应力和法兰口径
        self.stress_input = self.add_labeled_input(layout, 1, 0, "材料许用应力 (MPa):", QLineEdit(), "例如：137.0", QDoubleValidator(50, 500, 1))
        
        # 法兰口径下拉框
        self.flange_size_combo = QComboBox()
        self.flange_size_combo.setStyleSheet(COMBOBOX_STYLE)
        self.add_labeled_input(layout, 1, 2, "法兰口径:", self.flange_size_combo)
    
    def setup_economic_parameters(self, layout):
        """设置经济参数输入"""
        layout.setVerticalSpacing(12)
        layout.setHorizontalSpacing(20)
        
        # 第0行：制作单价和税率
        self.unit_price_input = self.add_labeled_input(layout, 0, 0, "制作单价 (元/kg):", QLineEdit(), "例如：20.0", QDoubleValidator(1, 1000, 2))
        self.tax_rate_input = self.add_labeled_input(layout, 0, 2, "税率:", QLineEdit(), "例如：0.13", QDoubleValidator(0, 1, 3))
        
        # 第1行：企业所得税和利润
        self.corporate_tax_input = self.add_labeled_input(layout, 1, 0, "企业所得税:", QLineEdit(), "例如：0.05", QDoubleValidator(0, 1, 3))
        self.profit_input = self.add_labeled_input(layout, 1, 2, "利润:", QLineEdit(), "例如：0.2", QDoubleValidator(0, 1, 3))
    
    def setup_buttons(self, layout):
        """设置按钮区域"""
        # 计算按钮
        calculate_btn = QPushButton("计算")
        calculate_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calculate_btn.clicked.connect(self.perform_design_calculation)
        calculate_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                min-height: 50px; padding: 0px;
                font-weight: bold;
            }
            QPushButton:hover:!checked {
                background-color: #ae2774;
            } """)
        calculate_btn.setMinimumHeight(50)
        layout.addWidget(calculate_btn)
        
        # 下载按钮
        download_layout = QHBoxLayout()
        download_txt_btn = QPushButton("下载计算书(TXT)")
        download_txt_btn.clicked.connect(self.download_txt_report)
        download_txt_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover:!checked {
                background-color: #219653;
            }
        """)

        download_pdf_btn = QPushButton("下载计算书(PDF)")
        download_pdf_btn.clicked.connect(self.generate_pdf_report)
        download_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover:!checked {
                background-color: #c0392b;
            }
        """)

        download_layout.addWidget(download_txt_btn)
        download_layout.addWidget(download_pdf_btn)
        layout.addLayout(download_layout)
    
    def create_result_tabs(self):
        """创建结果TabWidget"""
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #666;
                border-radius: 8px;
                /* background via theme */
            }
            QTabBar::tab {
                /* bg via theme */
                padding: 8px 16px;
                margin-right: 2px;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                /* bg via theme */
                /* color via theme */
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                /* bg via theme */
            }
        """)
        
        # 详细结果Tab
        detailed_result_widget = QWidget()
        detailed_layout = QVBoxLayout(detailed_result_widget)
        detailed_layout.setContentsMargins(5, 5, 5, 5)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #666;
                border-radius: 6px;
                padding: 8px;
                /* bg via theme */}
        """)
        self.result_text.setMaximumHeight(700)
        detailed_layout.addWidget(self.result_text)
        
        # 选型结果Tab
        selection_widget = QWidget()
        selection_layout = QVBoxLayout(selection_widget)
        selection_layout.setContentsMargins(5, 5, 5, 5)
        self.selection_text = QTextEdit()
        self.selection_text.setReadOnly(True)
        self.selection_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #666;
                border-radius: 6px;
                padding: 8px;
                /* bg via theme */}
        """)
        self.selection_text.setMaximumHeight(700)
        selection_layout.addWidget(self.selection_text)
        
        tabs.addTab(detailed_result_widget, "详细结果")
        tabs.addTab(selection_widget, "选型结果")
        
        return tabs
    
    def setup_default_values(self):
        """设置默认值"""
        # 输入框默认值
        defaults = [
            (self.fluid_name_input, "循环水"),
            (self.density_input, "992.0"),
            (self.viscosity_input, "0.001002"),
            (self.flow_input, "150.0"),
            (self.pressure_input, "1.6"),
            (self.temp_input, "80.0"),
            (self.max_pressure_drop_input, "50.0"),
            (self.mesh_input, "3000.0"),
            (self.porosity_input, "35.0"),
            (self.velocity_input, "0.1"),
            (self.support_thickness_input, "0.002"),
            (self.stress_input, "137.0"),
            (self.unit_price_input, "20.0"),
            (self.tax_rate_input, "0.13"),
            (self.corporate_tax_input, "0.05"),
            (self.profit_input, "0.2")
        ]
        
        for widget, value in defaults:
            widget.setText(value)
        
        # 下拉框选项
        materials = [
            "304不锈钢", "316不锈钢", "316L不锈钢", "碳钢",
            "双相钢2205", "哈氏合金C276", "钛合金", "聚丙烯(PP)", "聚四氟乙烯(PTFE)"
        ]
        self.material_combo.addItems(materials)
        self.material_combo.setCurrentText("304不锈钢")
        
        # 法兰口径选项 - 与压降计算模块保持一致
        flange_options = [
            "DN10 [10mm]", "DN15 [15mm]", "DN20 [20mm]", "DN25 [25mm]",
            "DN32 [32mm]", "DN40 [40mm]", "DN50 [50mm]", "DN65 [65mm]", 
            "DN80 [80mm]", "DN100 [100mm]", "DN125 [125mm]", "DN150 [150mm]",
            "DN200 [200mm]", "DN250 [250mm]", "DN300 [300mm]", "DN350 [350mm]",
            "DN400 [400mm]", "DN450 [450mm]", "DN500 [500mm]"
        ]
        self.flange_size_combo.addItems(flange_options)
        self.flange_size_combo.setCurrentText("DN100 [100mm]")
    
    # ==================== 核心计算方法 ====================
    
    def calculate_wire_diameter(self, mesh_size):
        """计算滤网丝径"""
        return 0.4 * mesh_size / 1000000
    
    def calculate_effective_area(self, flow_rate, velocity):
        """计算有效过滤面积"""
        return flow_rate / (3600 * velocity)
    
    def calculate_screen_diameter(self, effective_area):
        """计算滤网内径"""
        return math.sqrt(effective_area / (math.pi * 1.2)) * 1000
    
    def calculate_screen_height(self, screen_diameter):
        """计算滤网高度"""
        return 1.2 * screen_diameter
    
    def calculate_pressure_drop(self, viscosity, velocity, support_thickness, porosity, wire_diameter):
        """计算压降"""
        if porosity == 0 or wire_diameter == 0:
            return 0
        
        numerator = 32 * viscosity * velocity * support_thickness
        denominator = (porosity / 100) * (wire_diameter ** 2)
        pressure_drop_pa = numerator / denominator
        return pressure_drop_pa / 1000  # 转换为kPa
    
    def calculate_stress_factor(self, pressure, screen_diameter, support_thickness, stress):
        """计算应力系数"""
        pressure_kpa = pressure * 1000
        diameter_m = screen_diameter / 1000
        stress_kpa = stress * 1000
        
        denominator = 2 * support_thickness * stress_kpa
        if denominator == 0:
            return float('inf')
        return (pressure_kpa * diameter_m) / denominator
    
    def calculate_pipe_diameter(self, flow_rate, pipe_velocity=2.0):
        """计算进出口管径"""
        return math.sqrt(4 * flow_rate / (3600 * math.pi * pipe_velocity)) * 1000
    
    def round_value(self, value, value_type):
        """统一圆整函数"""
        if value_type == 'area':  # 面积：圆整到0.001 m²
            return math.ceil(value * 1000) / 1000
        elif value_type == 'dimension':  # 尺寸：圆整到10 mm
            return math.ceil(value / 10) * 10
        elif value_type == 'pressure':  # 压力：圆整到0.001 kPa
            return math.ceil(value * 1000) / 1000
        elif value_type == 'weight':  # 重量：圆整到1 kg
            return math.ceil(value)
        else:
            return value
    
    def get_filter_diameter_value(self, screen_diameter_rounded):
        """获取过滤器内径的取值"""
        calc_value = screen_diameter_rounded + 60
        
        # 根据计算值选取最接近的标准直径
        standard_diameters = [
            (10, 10), (15, 15), (20, 20), (25, 25),
            (32, 32), (40, 40), (50, 50), (65, 65),
            (80, 80), (100, 100), (125, 125), (150, 150),
            (200, 200), (250, 250), (300, 300), (350, 350),
            (400, 400), (450, 450), (500, 500)
        ]
        
        for condition_value, standard_diameter in standard_diameters:
            if calc_value <= condition_value:
                return standard_diameter
        
        return standard_diameters[-1][1]  # 大于最大值时返回最大直径
    
    def get_flange_from_pipe_diameter(self, pipe_diameter):
        """根据管径选择法兰口径"""
        standard_flanges = [
            ("DN10 [10mm]", 10), ("DN15 [15mm]", 15), ("DN20 [20mm]", 20), ("DN25 [25mm]", 25),
            ("DN32 [32mm]", 32), ("DN40 [40mm]", 40), ("DN50 [50mm]", 50), ("DN65 [65mm]", 65),
            ("DN80 [80mm]", 80), ("DN100 [100mm]", 100), ("DN125 [125mm]", 125), ("DN150 [150mm]", 150),
            ("DN200 [200mm]", 200), ("DN250 [250mm]", 250), ("DN300 [300mm]", 300), ("DN350 [350mm]", 350),
            ("DN400 [400mm]", 400), ("DN450 [450mm]", 450), ("DN500 [500mm]", 500)
        ]
        
        for flange_dn, approx_diameter in standard_flanges:
            if approx_diameter >= pipe_diameter:
                return flange_dn
        
        return standard_flanges[-1][0]
    
    def get_flange_weight(self, diameter_mm):
        """根据直径获取法兰重量"""
        flange_weights = [
            (10, 0.4), (15, 0.5), (20, 0.6), (25, 0.6),
            (32, 1.1), (40, 1.1), (50, 1.4), (65, 2.1),
            (80, 2.5), (100, 3.6), (125, 5.3), (150, 7.5),
            (200, 14.8), (250, 21.5), (300, 39.6), (350, 39.0),
            (400, 48.9), (450, 62.0), (500, 75.5)
        ]
        
        for size, weight in flange_weights:
            if diameter_mm <= size:
                return weight
        
        return flange_weights[-1][1]
    
    def calculate_weight(self, filter_diameter, filter_height, pipe_diameter):
        """计算过滤器重量"""
        steel_density = 8000  # kg/m³
        
        # 1. 底（上+下）重量
        bottom_radius = filter_diameter / 1000 / 2
        bottom_area = math.pi * bottom_radius ** 2
        single_bottom_volume = bottom_area * 0.005  # 厚度5mm
        single_bottom_weight = single_bottom_volume * steel_density
        bottom_weight = single_bottom_weight * 2
        bottom_weight_rounded = self.round_value(bottom_weight, 'weight')
        
        # 2. 筒体重量
        shell_diameter_m = filter_diameter / 1000
        shell_height_m = filter_height / 1000
        shell_area = math.pi * shell_diameter_m * shell_height_m
        shell_volume = shell_area * 0.005  # 厚度5mm
        shell_weight = shell_volume * steel_density
        shell_weight_rounded = self.round_value(shell_weight, 'weight')
        
        # 3. 封头法兰重量
        head_flange_weight = self.get_flange_weight(filter_diameter)
        
        # 4. 过滤篮筐重量
        part1 = math.pi * filter_diameter/1000 * filter_height/1000 * 0.003 * 8 * 1000
        part2 = (filter_diameter/1000/2)**2 * math.pi * 0.003 * 8
        basket_weight = part1 + part2
        basket_weight_rounded = self.round_value(basket_weight, 'weight')
        
        # 5. 进出料法兰重量
        inlet_outlet_flange_weight = self.get_flange_weight(pipe_diameter)
        
        # 总重量
        total_weight = (bottom_weight_rounded + shell_weight_rounded + 
                       head_flange_weight + basket_weight_rounded + 
                       inlet_outlet_flange_weight)
        
        return {
            "bottom": bottom_weight_rounded,
            "shell": shell_weight_rounded,
            "head_flange": head_flange_weight,
            "basket": basket_weight_rounded,
            "inlet_outlet_flange": inlet_outlet_flange_weight,
            "total": total_weight
        }
    
    def calculate_price(self, total_weight, unit_price, tax_rate, corporate_tax, profit):
        """计算产品价格"""
        return total_weight * unit_price * (1 + tax_rate + corporate_tax + profit)
    
    # ==================== 主要计算逻辑 ====================
    
    def perform_design_calculation(self):
        """执行设计计算"""
        try:
            # 1. 获取输入值
            inputs = self.get_input_values()
            if not inputs:
                return
            
            # 2. 计算基础参数
            wire_diameter = self.calculate_wire_diameter(inputs['mesh_size'])
            self.wire_diameter_input.setText(f"{wire_diameter:.6f}")
            
            # 3. 计算主要尺寸
            effective_area = self.calculate_effective_area(inputs['flow_rate'], inputs['velocity'])
            screen_diameter = self.calculate_screen_diameter(effective_area)
            screen_height = self.calculate_screen_height(screen_diameter)
            pressure_drop = self.calculate_pressure_drop(inputs['viscosity'], inputs['velocity'], 
                                                         inputs['support_thickness'], inputs['porosity'], wire_diameter)
            stress_factor = self.calculate_stress_factor(inputs['design_pressure'], screen_diameter, 
                                                         inputs['support_thickness'], inputs['stress'])
            pipe_diameter = self.calculate_pipe_diameter(inputs['flow_rate'])
            
            # 4. 圆整处理
            effective_area_rounded = self.round_value(effective_area, 'area')
            screen_diameter_rounded = self.round_value(screen_diameter, 'dimension')
            screen_height_rounded = self.round_value(screen_height, 'dimension')
            pressure_drop_rounded = self.round_value(pressure_drop, 'pressure')
            
            # 5. 选择法兰口径
            flange_dn = self.get_flange_from_pipe_diameter(pipe_diameter)
            index = self.flange_size_combo.findText(flange_dn)
            if index >= 0:
                self.flange_size_combo.setCurrentIndex(index)
            
            # 6. 计算过滤器尺寸
            filter_diameter_calc = screen_diameter_rounded + 60
            filter_diameter_rounded = self.get_filter_diameter_value(screen_diameter_rounded)
            filter_height = screen_height_rounded + 60
            
            # 7. 计算重量和价格
            weight_result = self.calculate_weight(filter_diameter_rounded, filter_height, pipe_diameter)
            price = self.calculate_price(weight_result["total"], inputs['unit_price'], 
                                        inputs['tax_rate'], inputs['corporate_tax'], inputs['profit'])
            
            # 8. 检查结果
            pressure_drop_ok = pressure_drop <= inputs['max_pressure_drop']
            stress_factor_ok = stress_factor <= 1.0
            
            # 9. 生成结果显示
            self.display_results(inputs, effective_area, screen_diameter, screen_height, pressure_drop,
                               effective_area_rounded, screen_diameter_rounded, screen_height_rounded, pressure_drop_rounded,
                               stress_factor, pipe_diameter, filter_diameter_calc, filter_diameter_rounded,
                               filter_height, weight_result, price, pressure_drop_ok, stress_factor_ok, flange_dn)
            
        except ValueError as e:
            QMessageBox.critical(self, "计算错误", f"参数输入格式错误: {str(e)}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "参数不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def _get_history_data(self):
        """提供历史记录数据"""
        inputs = self.get_input_values()

        inputs_hist = {
            "流体名称": inputs.get('fluid_name', ''),
            "密度_kg_m3": inputs.get('density', 0),
            "动力粘度_Pa_s": inputs.get('viscosity', 0),
            "设计流量_m3_h": inputs.get('flow_rate', 0),
            "设计压力_MPa": inputs.get('design_pressure', 0),
            "设计温度_C": inputs.get('design_temp', 0),
            "允许压降_kPa": inputs.get('max_pressure_drop', 0),
            "过滤精度_um": inputs.get('mesh_size', 0),
            "材料": inputs.get('material', ''),
            "开孔率_%": inputs.get('porosity', 0),
            "过滤速度_m_s": inputs.get('velocity', 0),
            "支撑网厚度_m": inputs.get('support_thickness', 0),
            "许用应力_MPa": inputs.get('stress', 0)
        }

        outputs = {}
        try:
            wire_diameter = self.calculate_wire_diameter(inputs['mesh_size'])
            effective_area = self.calculate_effective_area(inputs['flow_rate'], inputs['velocity'])
            screen_diameter = self.calculate_screen_diameter(effective_area)
            screen_height = self.calculate_screen_height(screen_diameter)
            pressure_drop = self.calculate_pressure_drop(inputs['viscosity'], inputs['velocity'],
                                                        inputs['support_thickness'], inputs['porosity'], wire_diameter)
            stress_factor = self.calculate_stress_factor(inputs['design_pressure'], screen_diameter,
                                                         inputs['support_thickness'], inputs['stress'])
            pipe_diameter = self.calculate_pipe_diameter(inputs['flow_rate'])
            effective_area_rounded = self.round_value(effective_area, 'area')
            screen_diameter_rounded = self.round_value(screen_diameter, 'dimension')
            filter_diameter_rounded = self.get_filter_diameter_value(screen_diameter_rounded)

            outputs = {
                "丝径_mm": round(wire_diameter * 1000, 4),
                "有效面积_m2": round(effective_area, 4),
                "筛网直径_mm": round(screen_diameter * 1000, 1),
                "筛网高度_mm": round(screen_height * 1000, 1),
                "压降_kPa": round(pressure_drop, 2),
                "应力因子": round(stress_factor, 3),
                "管道直径_mm": round(pipe_diameter * 1000, 1),
                "过滤器直径_mm": filter_diameter_rounded
            }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs_hist, "outputs": outputs}

    def get_input_values(self):
        """获取并验证输入值"""
        try:
            inputs = {
                'fluid_name': self.fluid_name_input.text().strip(),
                'density': float(self.density_input.text() or 0),
                'viscosity': float(self.viscosity_input.text() or 0),
                'corrosion': self.corrosion_combo.currentText(),
                'flow_rate': float(self.flow_input.text() or 0),
                'design_pressure': float(self.pressure_input.text() or 0),
                'design_temp': float(self.temp_input.text() or 0),
                'max_pressure_drop': float(self.max_pressure_drop_input.text() or 0),
                'mesh_size': float(self.mesh_input.text() or 0),
                'material': self.material_combo.currentText(),
                'porosity': float(self.porosity_input.text() or 0),
                'velocity': float(self.velocity_input.text() or 0),
                'support_thickness': float(self.support_thickness_input.text() or 0),
                'stress': float(self.stress_input.text() or 0),
                'unit_price': float(self.unit_price_input.text() or 0),
                'tax_rate': float(self.tax_rate_input.text() or 0),
                'corporate_tax': float(self.corporate_tax_input.text() or 0),
                'profit': float(self.profit_input.text() or 0)
            }
            
            # 验证必填字段
            required = [
                ('fluid_name', '介质名称'),
                ('density', '介质密度'),
                ('viscosity', '动力粘度'),
                ('flow_rate', '设计流量'),
                ('design_pressure', '设计压力'),
                ('mesh_size', '过滤精度'),
                ('porosity', '滤网开孔率'),
                ('velocity', '过滤速度'),
                ('support_thickness', '支撑网厚度'),
                ('stress', '材料许用应力')
            ]
            
            missing = [name for field, name in required if inputs[field] == 0 or (isinstance(inputs[field], str) and not inputs[field])]
            
            if missing:
                QMessageBox.warning(self, "输入错误", "请填写以下必需参数：\n" + ', '.join(missing))
                return None
            
            return inputs
            
        except ValueError:
            QMessageBox.warning(self, "输入错误", "参数格式不正确，请检查数字输入")
            return None
    
    def display_results(self, inputs, effective_area, screen_diameter, screen_height, pressure_drop,
                       effective_area_rounded, screen_diameter_rounded, screen_height_rounded, pressure_drop_rounded,
                       stress_factor, pipe_diameter, filter_diameter_calc, filter_diameter_rounded,
                       filter_height, weight_result, price, pressure_drop_ok, stress_factor_ok, flange_dn):
        """显示计算结果"""
        # 详细结果
        detailed_result = self.format_detailed_result(
            inputs, effective_area, screen_diameter, screen_height, pressure_drop,
            effective_area_rounded, screen_diameter_rounded, screen_height_rounded, pressure_drop_rounded,
            stress_factor, pipe_diameter, filter_diameter_calc, filter_diameter_rounded,
            filter_height, weight_result, price, pressure_drop_ok, stress_factor_ok, flange_dn
        )
        self.result_text.setText(detailed_result)
        
        # 选型结果
        selection_result = self.format_selection_result(
            inputs, effective_area_rounded, screen_diameter_rounded, screen_height_rounded,
            pipe_diameter, flange_dn, pressure_drop_rounded, weight_result["total"], 
            price, pressure_drop_ok, stress_factor_ok
        )
        self.selection_text.setText(selection_result)
        
        # 默认显示详细结果
        self.result_tabs.setCurrentIndex(0)
    
    # ==================== 结果格式化 ====================
    
    def format_detailed_result(self, inputs, effective_area, screen_diameter, screen_height, pressure_drop,
                              effective_area_rounded, screen_diameter_rounded, screen_height_rounded, pressure_drop_rounded,
                              stress_factor, pipe_diameter, filter_diameter_calc, filter_diameter_rounded,
                              filter_height, weight_result, price, pressure_drop_ok, stress_factor_ok, flange_dn):
        """格式化详细结果"""
        pressure_drop_status = "合格" if pressure_drop_ok else "不合格"
        stress_factor_status = "合格" if stress_factor_ok else "不合格"
        
        return f"""
══════════
 设计参数
══════════

    流体介质参数:
    • 介质名称: {inputs['fluid_name']}
    • 介质密度: {inputs['density']:.1f} kg/m³
    • 动力粘度: {inputs['viscosity']:.6f} Pa·s
    • 介质腐蚀性: {inputs['corrosion']}

    系统工况参数:
    • 设计流量: {inputs['flow_rate']:.1f} m³/h
    • 设计压力: {inputs['design_pressure']:.1f} MPa
    • 设计温度: {inputs['design_temp']:.1f} °C
    • 允许压降: {inputs['max_pressure_drop']:.1f} kPa

    过滤核心参数:
    • 过滤精度: {inputs['mesh_size']:.1f} μm
    • 滤网材质: {inputs['material']}
    • 滤网开孔率: {inputs['porosity']:.1f} %
    • 过滤速度: {inputs['velocity']:.3f} m/s

    结构与材料参数:
    • 滤网丝径: {float(self.wire_diameter_input.text()):.6f} m
    • 支撑网厚度: {inputs['support_thickness']:.4f} m
    • 材料许用应力: {inputs['stress']:.1f} MPa
    • 法兰口径: {flange_dn}

    经济参数:
    • 制作单价: {inputs['unit_price']:.2f} 元/kg
    • 税率: {inputs['tax_rate']:.3f}
    • 企业所得税: {inputs['corporate_tax']:.3f}
    • 利润: {inputs['profit']:.3f}

══════════
计算结果
══════════

    【计算值 vs 取值】
    1. 有效过滤面积:
    • 计算值: {effective_area:.4f} m²
    • 取值: {effective_area_rounded:.4f} m²

    2. 滤网内径:
    • 计算值: {screen_diameter:.1f} mm
    • 取值: {screen_diameter_rounded:.1f} mm

    3. 滤网高度:
    • 计算值: {screen_height:.1f} mm
    • 取值: {screen_height_rounded:.1f} mm

    4. 计算压降:
    • 计算值: {pressure_drop:.3f} kPa
    • 取值: {pressure_drop_rounded:.3f} kPa {pressure_drop_status}
    • 允许压降: {inputs['max_pressure_drop']:.1f} kPa

    5. 应力系数: {stress_factor:.4f} {stress_factor_status}

    6. 进出口管径:
    • 计算值: {pipe_diameter:.1f} mm
    • 建议法兰口径: {flange_dn}

    过滤器结构尺寸:
    • 过滤器内径计算值: {filter_diameter_calc:.1f} mm
    • 过滤器内径取值: {filter_diameter_rounded:.1f} mm
    • 过滤器高度: {filter_height:.1f} mm

    重量分析:
    • 底（上+下）重量: {weight_result.get('bottom', 0):.1f} kg
    • 筒体重量: {weight_result.get('shell', 0):.1f} kg
    • 封头法兰重量: {weight_result.get('head_flange', 0):.1f} kg
    • 过滤篮筐重量: {weight_result.get('basket', 0):.1f} kg
    • 进出料法兰重量: {weight_result.get('inlet_outlet_flange', 0):.1f} kg
    • 总重量: {weight_result.get('total', 0):.1f} kg

    价格计算:
    • 产品底价: {price:.0f} 元/台

══════════
计算说明
══════════

    计算公式:
    1. 有效过滤面积: A = Q/(3600*v)
    2. 滤网内径: D = √(A/(π*1.2)) * 1000
    3. 滤网高度: H = 1.2 * D
    4. 计算压降: ΔP = (32*μ*v*L)/(ε*d0²) / 1000
    5. 应力系数: δ = (P*D)/(2*δ*[σ]t)
    6. 进出口管径: dₚ = √(4Q/(3600*π*vₚ)) * 1000

    取值规则:
    • 面积: 向上取整到0.001 m²
    • 尺寸: 向上取整到10 mm
    • 压力: 向上取整到0.001 kPa
    • 重量: 向上取整到1 kg

    注意:
    • 压降应小于允许压降，应力系数应小于1.0
    • 实际设计应考虑安全系数和制造工艺
    • 计算结果仅供参考，最终设计需经专业工程师审核"""
    
    def format_selection_result(self, inputs, effective_area, screen_diameter, screen_height,
                               pipe_diameter, flange_dn, pressure_drop, total_weight, 
                               price, pressure_drop_ok, stress_factor_ok):
        """格式化选型结果"""
        # 生成过滤器型号
        pressure_value = int(inputs['design_pressure'] * 10)
        model_code = f"SBL-{pressure_value}P {flange_dn.split('[')[0].strip()}"
        
        measures = '设计合格，可直接选用' if (pressure_drop_ok and stress_factor_ok) else '需要调整设计参数'
        
        return f"""
══════════
选型结果
══════════

    过滤器型号: {model_code}
    有效过滤面积: {effective_area:.3f} m²
    滤网规格: {inputs['material']}
    过滤精度: {inputs['mesh_size']:.0f} μm (开孔率: {inputs['porosity']:.1f}%)
    滤网尺寸: {screen_diameter:.0f} × {screen_height:.0f} mm
    进出口管径: {pipe_diameter:.0f} mm (匹配{flange_dn})
    计算压降: {pressure_drop:.2f} kPa / 允许压降: {inputs['max_pressure_drop']:.0f} kPa
    设计压力/温度: {inputs['design_pressure']:.1f} MPa / {inputs['design_temp']:.0f} °C
    整机质量: {total_weight:.1f} kg
    估算价格: {price:.0f} 元/台

    设计状态: {'设计合格' if (pressure_drop_ok and stress_factor_ok) else '需要调整'}
    建议措施: {measures}

══════════
备注说明
══════════

    型号说明: {model_code}
    • SBL: 立式篮式过滤器
    • {pressure_value}P: 公称压力PN{pressure_value}
    • {flange_dn.split('[')[0].strip()}: 公称通径

    选型建议:
    • 根据介质腐蚀性选择合适的材质
    • 高粘度流体应适当增大过滤面积
    • 压降超标时应考虑增加过滤器数量或规格

    制造要求:
    • 焊接应符合相关标准规范
    • 滤网应均匀平整，无破损
    • 压力试验应满足设计要求"""
    
    # ==================== 工具方法 ====================
    
    def copy_results_to_clipboard(self):
        """复制结果到剪贴板"""
        try:
            import pyperclip
            current_tab = self.result_tabs.currentIndex()
            
            if current_tab == 0:  # 详细结果
                text = self.result_text.toPlainText()
            else:  # 选型结果
                text = self.selection_text.toPlainText()
            
            if text and text.strip():
                pyperclip.copy(text)
                QMessageBox.information(self, "复制成功", "结果已复制到剪贴板")
            else:
                QMessageBox.warning(self, "复制失败", "没有可复制的内容")
        except ImportError:
            QMessageBox.warning(self, "复制失败", "请安装pyperclip库: pip install pyperclip")
        except Exception as e:
            QMessageBox.warning(self, "复制失败", f"复制时发生错误: {str(e)}")
    
    def get_project_info(self):
        """获取工程信息 - 使用共享的项目信息"""
        try:
            class ProjectInfoDialog(QDialog):
                def __init__(self, parent=None, default_info=None, report_number=""):
                    super().__init__(parent)
                    self.default_info = default_info or {}
                    self.report_number = report_number
                    self.setWindowTitle("工程信息")
                    self.setFixedSize(400, 350)
                    self.setup_ui()
                    
                def setup_ui(self):
                    layout = QVBoxLayout(self)
                    
                    # 标题
                    title_label = QLabel("请输入工程信息")
                    title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
                    layout.addWidget(title_label)
                    
                    # 公司名称
                    company_layout = QHBoxLayout()
                    company_label = QLabel("公司名称:")
                    company_label.setFixedWidth(80)
                    self.company_input = QLineEdit()
                    self.company_input.setPlaceholderText("例如：XX建筑工程有限公司")
                    self.company_input.setText(self.default_info.get('company_name', ''))
                    company_layout.addWidget(company_label)
                    company_layout.addWidget(self.company_input)
                    layout.addLayout(company_layout)
                    
                    # 工程编号
                    number_layout = QHBoxLayout()
                    number_label = QLabel("工程编号:")
                    number_label.setFixedWidth(80)
                    self.project_number_input = QLineEdit()
                    self.project_number_input.setPlaceholderText("例如：2024-FILTER-001")
                    self.project_number_input.setText(self.default_info.get('project_number', ''))
                    number_layout.addWidget(number_label)
                    number_layout.addWidget(self.project_number_input)
                    layout.addLayout(number_layout)
                    
                    # 工程名称
                    project_layout = QHBoxLayout()
                    project_label = QLabel("工程名称:")
                    project_label.setFixedWidth(80)
                    self.project_input = QLineEdit()
                    self.project_input.setPlaceholderText("例如：化工厂过滤器系统")
                    self.project_input.setText(self.default_info.get('project_name', ''))
                    project_layout.addWidget(project_label)
                    project_layout.addWidget(self.project_input)
                    layout.addLayout(project_layout)
                    
                    # 子项名称
                    subproject_layout = QHBoxLayout()
                    subproject_label = QLabel("子项名称:")
                    subproject_label.setFixedWidth(80)
                    self.subproject_input = QLineEdit()
                    self.subproject_input.setPlaceholderText("例如：主生产区过滤器")
                    self.subproject_input.setText(self.default_info.get('subproject_name', ''))
                    subproject_layout.addWidget(subproject_label)
                    subproject_layout.addWidget(self.subproject_input)
                    layout.addLayout(subproject_layout)
                    
                    # 计算书编号
                    report_number_layout = QHBoxLayout()
                    report_number_label = QLabel("计算书编号:")
                    report_number_label.setFixedWidth(80)
                    self.report_number_input = QLineEdit()
                    self.report_number_input.setText(self.report_number)
                    report_number_layout.addWidget(report_number_label)
                    report_number_layout.addWidget(self.report_number_input)
                    layout.addLayout(report_number_layout)
                    
                    # 按钮
                    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                    button_box.accepted.connect(self.accept)
                    button_box.rejected.connect(self.reject)
                    layout.addWidget(button_box)
                    
                def get_info(self):
                    return {
                        'company_name': self.company_input.text().strip(),
                        'project_number': self.project_number_input.text().strip(),
                        'project_name': self.project_input.text().strip(),
                        'subproject_name': self.subproject_input.text().strip(),
                        'report_number': self.report_number_input.text().strip()
                    }
            
            # 从数据管理器获取共享的项目信息
            saved_info = {}
            if self.data_manager:
                saved_info = self.data_manager.get_project_info()
            
            # 获取下一个报告编号
            report_number = ""
            if self.data_manager:
                report_number = self.data_manager.get_next_report_number("FILTER")
            
            dialog = ProjectInfoDialog(self, saved_info, report_number)
            if dialog.exec() == QDialog.Accepted:
                info = dialog.get_info()
                # 验证必填字段
                if not info['project_name']:
                    QMessageBox.warning(self, "输入错误", "工程名称不能为空")
                    return self.get_project_info()  # 重新弹出对话框
                
                # 保存项目信息到数据管理器
                if self.data_manager:
                    info_to_save = {
                        'company_name': info['company_name'],
                        'project_number': info['project_number'],
                        'project_name': info['project_name'],
                        'subproject_name': info['subproject_name']
                    }
                    self.data_manager.update_project_info(info_to_save)
                    print("项目信息已保存")
                
                return info
            else:
                return None  # 用户取消了
                    
        except Exception as e:
            print(f"获取工程信息失败: {e}")
            return None
    
    def generate_report(self):
        """生成计算书"""
        try:
            # 获取当前结果文本
            result_text = self.result_text.toPlainText()
            selection_text = self.selection_text.toPlainText()
            
            # 检查是否已经计算
            if not result_text or not selection_text or ("计算结果" not in result_text and "设计参数" not in result_text):
                QMessageBox.warning(self, "生成失败", "请先进行设计计算再生成计算书")
                return None
                
            # 获取工程信息
            project_info = self.get_project_info()
            if not project_info:
                return None  # 用户取消了输入
            
            # 添加报告头信息
            report = f"""工程计算书 - 篮式过滤器设计计算
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
计算工具: ChemCal 工程计算模块
========================================

"""
            report += result_text
            report += "\n\n"
            report += selection_text
            
            # 添加工程信息部分
            report += f"""
══════════
 工程信息
══════════

    公司名称: {project_info['company_name']}
    工程编号: {project_info['project_number']}
    工程名称: {project_info['project_name']}
    子项名称: {project_info['subproject_name']}
    计算日期: {datetime.now().strftime('%Y-%m-%d')}

══════════
计算书标识
══════════

    计算书编号: {project_info['report_number']}
    版本: 1.0
    状态: 正式计算书

══════════
备注说明
══════════

    1. 本计算书基于流体力学原理及相关标准规范
    2. 计算结果仅供参考，实际应用需考虑安全系数
    3. 重要工程参数应经专业工程师审核确认
    4. 计算条件变更时应重新进行计算

---
生成于 ChemCal 工程计算模块
"""
            return report
            
        except Exception as e:
            print(f"生成计算书失败: {e}")
            return None
    
    def download_txt_report(self):
        """下载TXT格式计算书"""
        try:
            # 直接调用 generate_report，它内部会进行检查
            report_content = self.generate_report()
            if report_content is None:  # 如果返回None，说明检查失败或用户取消
                return
                
            # 选择保存路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"篮式过滤器设计计算书_{timestamp}.txt"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存计算书", default_name, "Text Files (*.txt)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                QMessageBox.information(self, "下载成功", f"计算书已保存到:\n{file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "下载失败", f"保存计算书时发生错误: {str(e)}")
    
    def generate_pdf_report(self):
        """生成PDF格式计算书"""
        try:
            # 直接调用 generate_report，它内部会进行检查
            report_content = self.generate_report()
            if report_content is None:  # 如果返回None，说明检查失败或用户取消
                return False
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"篮式过滤器设计计算书_{timestamp}.pdf"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存PDF计算书", default_name, "PDF Files (*.pdf)"
            )
            
            if not file_path:
                return False
                
            # 尝试导入reportlab
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.pdfgen import canvas
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.units import inch
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                import os
                
                # 注册中文字体
                try:
                    font_paths = [
                        "C:/Windows/Fonts/simhei.ttf",
                        "C:/Windows/Fonts/simsun.ttc",
                        "C:/Windows/Fonts/msyh.ttc",
                        "/Library/Fonts/Arial Unicode.ttf",
                        "/System/Library/Fonts/Arial.ttf",
                        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
                        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                    ]
                    
                    chinese_font_registered = False
                    for font_path in font_paths:
                        if os.path.exists(font_path):
                            try:
                                if "simhei" in font_path.lower():
                                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                                    chinese_font_registered = True
                                    break
                                elif "simsun" in font_path.lower():
                                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                                    chinese_font_registered = True
                                    break
                                elif "msyh" in font_path.lower() or "microsoftyahei" in font_path.lower():
                                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                                    chinese_font_registered = True
                                    break
                                elif "arial unicode" in font_path.lower():
                                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                                    chinese_font_registered = True
                                    break
                            except:
                                continue
                    
                    if not chinese_font_registered:
                        pdfmetrics.registerFont(TTFont('ChineseFont', 'Helvetica'))
                except:
                    pass
                
                # 创建PDF文档
                doc = SimpleDocTemplate(file_path, pagesize=A4)
                styles = getSampleStyleSheet()
                
                # 创建支持中文的样式
                chinese_style_normal = ParagraphStyle(
                    'ChineseNormal',
                    parent=styles['Normal'],
                    fontName='ChineseFont',
                    fontSize=10,
                    leading=14,
                )
                
                chinese_style_heading = ParagraphStyle(
                    'ChineseHeading',
                    parent=styles['Heading1'],
                    fontName='ChineseFont',
                    fontSize=16,
                    leading=20,
                    spaceAfter=12,
                )
                
                story = []
                
                # 添加标题
                title = Paragraph("工程计算书 - 篮式过滤器设计计算", chinese_style_heading)
                story.append(title)
                story.append(Spacer(1, 0.2*inch))
                
                # 处理报告内容，替换特殊字符和表情
                processed_content = self.process_content_for_pdf(report_content)
                
                # 添加内容
                for line in processed_content.split('\n'):
                    if line.strip():
                        line = line.replace(' ', '&nbsp;')
                        line = line.replace('═', '=').replace('─', '-')
                        para = Paragraph(line, chinese_style_normal)
                        story.append(para)
                        story.append(Spacer(1, 0.05*inch))
                
                # 生成PDF
                doc.build(story)
                QMessageBox.information(self, "生成成功", f"PDF计算书已保存到:\n{file_path}")
                return True
                
            except ImportError:
                QMessageBox.warning(
                    self, 
                    "功能不可用", 
                    "PDF生成功能需要安装reportlab库\n\n请运行: pip install reportlab"
                )
                return False
                
        except Exception as e:
            QMessageBox.critical(self, "生成失败", f"生成PDF时发生错误: {str(e)}")
            return False
    
    def process_content_for_pdf(self, content):
        """处理内容，使其适合PDF显示"""
        # 清理bullet符号
        content = content.replace("•", "")
        
        # 替换单位符号
        content = content.replace("m³", "m3")
        content = content.replace("g/100g", "g/100g")
        content = content.replace("kg/m³", "kg/m3")
        content = content.replace("Nm³/h", "Nm3/h")
        content = content.replace("Pa·s", "Pa.s")
        content = content.replace("m²", "m2")
        content = content.replace("0²", "02")
        content = content.replace("dₚ", "dp")
        content = content.replace("vₚ", "vp")
        
        return content


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    calculator = 篮式过滤器()
    calculator.resize(1200, 800)
    calculator.show()
    sys.exit(app.exec())