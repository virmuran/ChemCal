from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox,
    QScrollArea, QDialog, QSpinBox, QButtonGroup, QGridLayout,
    QFileDialog, QDialogButtonBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QDoubleValidator
import math
import re
import os
import importlib.util
from datetime import datetime
import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K, G, ATM_PRESSURE_MPA, WATER_DENSITY, WATER_CP, load_steam_iapws, get_steam_props
# DOCX 报告导出

# IAPWS-IF97 工业标准蒸汽物性（动态导入，避免 relative import 失败）
try:
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _parent_dir = os.path.dirname(_current_dir)
    _spec = importlib.util.spec_from_file_location( "steam_iapws",
        os.path.join(_parent_dir, "steam_iapws.py")
    )
    _steam_iapws = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_steam_iapws)

    iapws_T_sat = _steam_iapws.saturation_temperature
    iapws_P_sat = _steam_iapws.saturation_pressure
    iapws_sat_props = _steam_iapws.saturation_properties
    iapws_steam_props = _steam_iapws.steam_properties
    iapws_wet_steam = _steam_iapws.wet_steam_properties
    iapws_from_ph = _steam_iapws.properties_from_ph
    iapws_from_ps = _steam_iapws.properties_from_ps
    iapws_viscosity = _steam_iapws.viscosity
    iapws_thermal_cond = _steam_iapws.thermal_conductivity
except Exception as e:
    print(f"警告: 无法加载 IAPWS-IF97 模块: {e}")
    iapws_T_sat = iapws_P_sat = iapws_sat_props = None
    iapws_steam_props = iapws_wet_steam = None
    iapws_from_ph = iapws_from_ps = None
    iapws_viscosity = iapws_thermal_cond = None

# QGroupBox 统一样式

# 滚动条统一样式
SCROLLBAR_STYLE = """
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #c0c0c0;
        border-radius: 4px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover {
        background: #a0a0a0;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }
    QScrollBar:horizontal {
        background: transparent;
        height: 8px;
        margin: 0;
    }
    QScrollBar::handle:horizontal {
        background: #c0c0c0;
        border-radius: 4px;
        min-width: 30px;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
    }
"""

class SteamPropertyCalculator(CalculatorBase):
    """水蒸气性质查询计算器 - 统一UI规范版本"""
    
    # 计算类型类属性
    calculation_type = "水蒸气性质查询"
    
    # 信号：用于传递计算结果
    calculation_completed = Signal(dict)
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        
        # 使用传入的数据管理器或创建新的
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        
        # 初始化状态变量
        self.current_mode = "saturation"  # 默认饱和状态
        self.parameter1_type = "pressure"  # 参数1类型
        self.parameter2_type = "temperature"  # 参数2类型
        
        # 初始化单位
        self.pressure_unit = "MPa"
        self.temperature_unit = "°C"
        self.density_unit = "kg/m³"
        self.enthalpy_unit = "kJ/kg"
        self.entropy_unit = "kJ/(kg·K)"
        
        self.setup_ui()
        self.setup_mode_dependencies()
        self.initialize_values()
        self.setup_connections()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()
    
    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
            print("使用共享的数据管理器实例")
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None
    
    def setup_ui(self):
        """设置UI界面 - 按照统一UI规范"""
        # 主布局：QHBoxLayout，间距15，边距10
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # ==================== 左侧：输入参数区域 ====================
        scroll_left = QScrollArea()
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } " + SCROLLBAR_STYLE)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout = left_layout  # 供子函数直接添加控件
        
        # 1. 顶部说明文字
        description = QLabel(
            "查询水蒸气在不同状态下的热力学性质，包括密度、比焓、比熵等。支持饱和状态和其他状态查询。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 2. 查询模式选择
        mode_group = QGroupBox("查询模式")
        mode_layout = QHBoxLayout(mode_group)
        
        self.mode_button_group = QButtonGroup(self)
        self.mode_buttons = {}
        
        modes = [
            ("饱和状态", "查询饱和状态下的水蒸气性质"),
            ("其他状态", "查询已知两个参数的水蒸气性质")
        ]
        
        for i, (mode_name, tooltip) in enumerate(modes):
            btn = QPushButton(mode_name)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setMinimumWidth(120)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    border: 1px solid #666;
                    border-radius: 4px;
                    padding: 8px;
                    text-align: center;
                    color: black;
                }
                QPushButton:checked {
                    background-color: #4b5cc4;
                    color: white;
                }
                QPushButton:hover:!checked {
                    background-color: #c0ebd7;
                } """)
            self.mode_button_group.addButton(btn, i)
            mode_layout.addWidget(btn)
            self.mode_buttons[mode_name] = btn
        
        # 默认选择第一个
        self.mode_buttons["饱和状态"].setChecked(True)
        self.mode_button_group.buttonClicked.connect(self.on_mode_button_clicked)
        
        mode_layout.addStretch()
        left_layout.addWidget(mode_group)
        
        # 3. 饱和状态：已知参数 + 输入参数
        self.create_saturation_page()

        # 4. 其他状态：已知参数组合 + 输入参数
        self.create_other_page()

        # 默认显示饱和状态，隐藏其他状态
        self.other_known_group.hide()
        self.other_input_group.hide()

        # 清空按钮
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_inputs)
        self.clear_btn.setMinimumHeight(50)
        self.clear_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            } """)
        left_layout.addWidget(self.clear_btn)
        left_layout.addStretch()
        
        # ==================== 右侧：结果显示区域 ====================
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)  # 设置最小宽度
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)
        
        # 结果显示
        self.result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(self.result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #666;
                border-radius: 6px;
                padding: 8px;
                /* bg via theme */min-height: 500px;
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
                font-size: 12px;
                line-height: 1.4;
            } """)
        result_layout.addWidget(self.result_text)
        
        right_layout.addWidget(self.result_group)
        
        # 下载TXT按钮
        self.download_docx_btn = QPushButton("下载计算书(DOCX)")
        self.download_docx_btn.clicked.connect(self.download_docx_report)
        self.download_docx_btn.setMinimumHeight(50)
        self.download_docx_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_docx_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            } """)
        right_layout.addWidget(self.download_docx_btn)
        
        # 下载PDF按钮
        self.download_pdf_btn = QPushButton("下载计算书(PDF)")
        self.download_pdf_btn.clicked.connect(self.download_pdf_report)
        self.download_pdf_btn.setMinimumHeight(50)
        self.download_pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            } """)
        right_layout.addWidget(self.download_pdf_btn)
        
        # 计算按钮
        self.calculate_btn = self.make_calc_button("查询")
        self.calculate_btn.clicked.connect(self.calculate)
        right_layout.addWidget(self.calculate_btn)
        
        # ==================== 添加左右布局 ====================
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)  # 左侧占2/3权重
        main_layout.addWidget(right_widget, 1)  # 右侧占1/3权重
    
    def create_saturation_page(self):
        """创建饱和状态的已知参数 + 输入参数两个框，直接加入 left_layout"""
        # --- 框1：已知参数选择 ---
        self.sat_known_group = QGroupBox("已知参数")
        known_btn_layout = QHBoxLayout(self.sat_known_group)
        known_btn_layout.setSpacing(8)

        self.sat_known_button_group = QButtonGroup(self)
        self.sat_known_buttons = {}

        known_options = ["压力 P", "温度 T"]

        for i, option in enumerate(known_options):
            btn = QPushButton(option)
            btn.setCheckable(True)
            btn.setMinimumWidth(120)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    border: 1px solid #666;
                    border-radius: 4px;
                    padding: 8px;
                    text-align: center;
                    color: black;
                }
                QPushButton:checked {
                    background-color: #4b5cc4;
                    color: white;
                }
                QPushButton:hover:!checked {
                    background-color: #c0ebd7;
                    color: black;
                } """)
            self.sat_known_button_group.addButton(btn, i)
            known_btn_layout.addWidget(btn)
            self.sat_known_buttons[option] = btn

        self.sat_known_buttons["压力 P"].setChecked(True)
        self.sat_known_button_group.buttonClicked.connect(self.on_sat_known_button_clicked)

        known_btn_layout.addStretch()
        self.left_layout.addWidget(self.sat_known_group)

        # --- 框2：输入参数 ---
        self.sat_input_group = QGroupBox("输入参数")
        input_layout = QGridLayout(self.sat_input_group)
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)

        row = 0

        # 参数1输入
        self.sat_param1_label = QLabel("压力 (MPa):")
        self.sat_param1_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.sat_param1_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        self.sat_param1_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.sat_param1_label, row, 0)

        self.sat_param1_input = QLineEdit()
        self.sat_param1_input.setPlaceholderText("例如: 0.6")
        self.sat_param1_input.setValidator(QDoubleValidator(0.001, 30.0, 6))
        self.sat_param1_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.sat_param1_input, row, 1)

        self.sat_param1_combo = QComboBox()
        self.sat_param1_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_pressure_options(self.sat_param1_combo)
        self.sat_param1_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sat_param1_combo.currentTextChanged.connect(
            lambda text: self.on_param_combo_changed(text, self.sat_param1_input)
        )
        input_layout.addWidget(self.sat_param1_combo, row, 2)

        row += 1

        # 干度输入
        dryness_label = QLabel("干度 (0-1):")
        dryness_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        dryness_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        dryness_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(dryness_label, row, 0)

        self.dryness_input = QLineEdit()
        self.dryness_input.setPlaceholderText("例如: 0.9")
        self.dryness_input.setValidator(QDoubleValidator(0.0, 1.0, 3))
        self.dryness_input.setText("1.0")  # 默认干饱和蒸汽
        self.dryness_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.dryness_input, row, 1)

        # 干度说明
        self.dryness_hint = QLabel("干度=0:饱和水，干度=1:干饱和蒸汽")
        self.dryness_hint.setStyleSheet("font-style: italic;")
        self.dryness_hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.dryness_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.dryness_hint, row, 2)

        self.left_layout.addWidget(self.sat_input_group)

    def create_other_page(self):
        """创建其他状态的已知参数组合 + 输入参数两个框，直接加入 left_layout"""
        # --- 框1：已知参数组合选择 ---
        self.other_known_group = QGroupBox("已知参数组合")
        known_btn_layout = QHBoxLayout(self.other_known_group)
        known_btn_layout.setSpacing(8)

        self.other_known_button_group = QButtonGroup(self)
        self.other_known_buttons = {}

        known_options = [ "压力 P 和温度 T", "压力 P 和比焓 H",
            "压力 P 和比熵 S"
        ]

        for i, option in enumerate(known_options):
            btn = QPushButton(option)
            btn.setCheckable(True)
            btn.setMinimumWidth(120)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    border: 1px solid #666;
                    border-radius: 4px;
                    padding: 8px;
                    text-align: center;
                    color: black;
                }
                QPushButton:checked {
                    background-color: #4b5cc4;
                    color: white;
                }
                QPushButton:hover:!checked {
                    background-color: #c0ebd7;
                    color: black;
                } """)
            self.other_known_button_group.addButton(btn, i)
            known_btn_layout.addWidget(btn)
            self.other_known_buttons[option] = btn

        self.other_known_buttons["压力 P 和温度 T"].setChecked(True)
        self.other_known_button_group.buttonClicked.connect(self.on_other_known_button_clicked)

        known_btn_layout.addStretch()
        self.left_layout.addWidget(self.other_known_group)

        # --- 框2：输入参数 ---
        self.other_input_group = QGroupBox("输入参数")
        input_layout = QGridLayout(self.other_input_group)
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)

        row = 0

        # 参数1输入
        self.other_param1_label = QLabel("压力 (MPa):")
        self.other_param1_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.other_param1_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        self.other_param1_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.other_param1_label, row, 0)

        self.other_param1_input = QLineEdit()
        self.other_param1_input.setPlaceholderText("例如: 0.6")
        self.other_param1_input.setValidator(QDoubleValidator(0.001, 30.0, 6))
        self.other_param1_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.other_param1_input, row, 1)

        self.other_param1_combo = QComboBox()
        self.other_param1_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_pressure_options(self.other_param1_combo)
        self.other_param1_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.other_param1_combo.currentTextChanged.connect(
            lambda text: self.on_param_combo_changed(text, self.other_param1_input)
        )
        input_layout.addWidget(self.other_param1_combo, row, 2)

        row += 1

        # 参数2输入
        self.other_param2_label = QLabel("温度 (°C):")
        self.other_param2_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.other_param2_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        self.other_param2_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.other_param2_label, row, 0)

        self.other_param2_input = QLineEdit()
        self.other_param2_input.setPlaceholderText("例如: 165")
        self.other_param2_input.setValidator(QDoubleValidator(0.01, 800.0, 6))
        self.other_param2_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.other_param2_input, row, 1)

        self.other_param2_combo = QComboBox()
        self.other_param2_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_temperature_options(self.other_param2_combo)
        self.other_param2_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.other_param2_combo.currentTextChanged.connect(
            lambda text: self.on_param_combo_changed(text, self.other_param2_input)
        )
        input_layout.addWidget(self.other_param2_combo, row, 2)

        self.left_layout.addWidget(self.other_input_group)
    
    def setup_mode_dependencies(self):
        """设置计算模式的依赖关系"""
        self.on_mode_changed("饱和状态")
    
    def setup_connections(self):
        """设置信号连接"""
        pass
    
    def initialize_values(self):
        """初始化值"""
        # 饱和状态默认值
        self.sat_param1_input.setText("0.6")
        self.dryness_input.setText("0.9")
        
        # 其他状态默认值
        self.other_param1_input.setText("0.6")
        self.other_param2_input.setText("165")
    
    def setup_pressure_options(self, combo_box):
        """设置压力选项"""
        options = [ "- 请选择压力 -", "0.1013 MPa - 常压", "0.1 MPa - 低压蒸汽", "0.3 MPa - 低压蒸汽", "0.6 MPa - 中压蒸汽", "1.0 MPa - 中压蒸汽", "1.6 MPa - 高压蒸汽", "2.5 MPa - 高压蒸汽", "4.0 MPa - 超高压蒸汽", "10.0 MPa - 超高压蒸汽",
            "自定义压力"
        ]
        combo_box.addItems(options)
        combo_box.setCurrentIndex(0)
    
    def setup_temperature_options(self, combo_box):
        """设置温度选项"""
        options = [ "- 请选择温度 -", "100 °C - 饱和蒸汽", "120 °C - 饱和蒸汽", "150 °C - 饱和蒸汽", "165 °C - 饱和蒸汽", "180 °C - 饱和蒸汽", "200 °C - 过热蒸汽", "250 °C - 过热蒸汽", "300 °C - 过热蒸汽", "400 °C - 高温蒸汽", "500 °C - 高温蒸汽", "600 °C - 超高温蒸汽",
            "自定义温度"
        ]
        combo_box.addItems(options)
        combo_box.setCurrentIndex(0)
    
    def on_mode_button_clicked(self, button):
        """处理计算模式按钮点击"""
        mode_text = button.text()
        self.on_mode_changed(mode_text)
    
    def on_sat_known_button_clicked(self, button):
        """处理饱和状态已知参数按钮点击"""
        param_type = button.text()
        self.update_sat_known_ui(param_type)
    
    def on_other_known_button_clicked(self, button):
        """处理其他状态已知参数组合按钮点击"""
        param_combo = button.text()
        self.update_other_known_ui(param_combo)
    
    def get_current_mode(self):
        """获取当前选择的计算模式"""
        checked_button = self.mode_button_group.checkedButton()
        if checked_button:
            return checked_button.text()
        return "饱和状态"
    
    def on_mode_changed(self, mode):
        """处理计算模式变化：用 show/hide 切换对应 GroupBox"""
        self.current_mode = mode

        if mode == "饱和状态":
            self.sat_known_group.show()
            self.sat_input_group.show()
            self.other_known_group.hide()
            self.other_input_group.hide()
        else:
            self.sat_known_group.hide()
            self.sat_input_group.hide()
            self.other_known_group.show()
            self.other_input_group.show()
    
    def update_sat_known_ui(self, param_type):
        """更新饱和状态已知参数UI"""
        if "压力" in param_type:
            self.sat_param1_label.setText("压力 (MPa):")
            self.sat_param1_combo.clear()
            self.setup_pressure_options(self.sat_param1_combo)
            self.sat_param1_input.setValidator(QDoubleValidator(0.001, 30.0, 6))
            self.sat_param1_input.setPlaceholderText("例如: 0.6")
            self.sat_param1_input.setText("0.6")
        else:
            self.sat_param1_label.setText("温度 (°C):")
            self.sat_param1_combo.clear()
            self.setup_temperature_options(self.sat_param1_combo)
            self.sat_param1_input.setValidator(QDoubleValidator(0.01, 800.0, 6))
            self.sat_param1_input.setPlaceholderText("例如: 165")
            self.sat_param1_input.setText("165")
    
    def update_other_known_ui(self, param_combo):
        """更新其他状态已知参数组合UI"""
        if "压力 P 和温度 T" in param_combo:
            self.other_param1_label.setText("压力 (MPa):")
            self.other_param2_label.setText("温度 (°C):")
            
            self.other_param1_combo.clear()
            self.setup_pressure_options(self.other_param1_combo)
            self.other_param1_input.setValidator(QDoubleValidator(0.001, 30.0, 6))
            self.other_param1_input.setPlaceholderText("例如: 0.6")
            
            self.other_param2_combo.clear()
            self.setup_temperature_options(self.other_param2_combo)
            self.other_param2_input.setValidator(QDoubleValidator(0.01, 800.0, 6))
            self.other_param2_input.setPlaceholderText("例如: 165")
            
        elif "压力 P 和比焓 H" in param_combo:
            self.other_param1_label.setText("压力 (MPa):")
            self.other_param2_label.setText("比焓 (kJ/kg):")
            
            self.other_param1_combo.clear()
            self.setup_pressure_options(self.other_param1_combo)
            self.other_param1_input.setValidator(QDoubleValidator(0.001, 30.0, 6))
            self.other_param1_input.setPlaceholderText("例如: 0.6")
            
            self.other_param2_combo.clear()
            enthalpy_options = [ "- 请选择比焓 -", "500 kJ/kg - 过冷水", "1000 kJ/kg - 湿蒸汽", "2000 kJ/kg - 湿蒸汽", "2675 kJ/kg - 饱和蒸汽", "2800 kJ/kg - 过热蒸汽", "3000 kJ/kg - 过热蒸汽", "3500 kJ/kg - 高温蒸汽",
                "自定义比焓"
            ]
            self.other_param2_combo.addItems(enthalpy_options)
            self.other_param2_input.setValidator(QDoubleValidator(0.1, 5000.0, 6))
            self.other_param2_input.setPlaceholderText("例如: 2800")
            
        elif "压力 P 和比熵 S" in param_combo:
            self.other_param1_label.setText("压力 (MPa):")
            self.other_param2_label.setText("比熵 (kJ/(kg·K)):")
            
            self.other_param1_combo.clear()
            self.setup_pressure_options(self.other_param1_combo)
            self.other_param1_input.setValidator(QDoubleValidator(0.001, 30.0, 6))
            self.other_param1_input.setPlaceholderText("例如: 0.6")
            
            self.other_param2_combo.clear()
            entropy_options = [ "- 请选择比熵 -", "1.0 kJ/(kg·K) - 过冷水", "3.0 kJ/(kg·K) - 湿蒸汽", "5.0 kJ/(kg·K) - 湿蒸汽", "6.5 kJ/(kg·K) - 饱和蒸汽", "7.0 kJ/(kg·K) - 过热蒸汽", "8.0 kJ/(kg·K) - 过热蒸汽",
                "自定义比熵"
            ]
            self.other_param2_combo.addItems(entropy_options)
            self.other_param2_input.setValidator(QDoubleValidator(0.1, 10.0, 6))
            self.other_param2_input.setPlaceholderText("例如: 7.0")
    
    def on_param_combo_changed(self, text, input_widget):
        """处理参数下拉菜单变化"""
        if text.startswith("-") or not text.strip():
            input_widget.clear()
            input_widget.setReadOnly(False)
            return
        
        if "自定义" in text:
            input_widget.setReadOnly(False)
            input_widget.setPlaceholderText("输入自定义值")
            input_widget.clear()
        else:
            input_widget.setReadOnly(True)
            try:
                match = re.search(r"(\d+\.?\d*)", text)
                if match:
                    value = float(match.group(1))
                    if "MPa" in text:
                        input_widget.setText(f"{value:.4f}")
                    elif "°C" in text:
                        input_widget.setText(f"{value:.0f}")
                    elif "kJ/kg" in text:
                        input_widget.setText(f"{value:.1f}")
                    elif "kJ/(kg·K)" in text:
                        input_widget.setText(f"{value:.3f}")
                    else:
                        input_widget.setText(f"{value}")
            except:
                pass
    
    # ==================== 计算函数 ====================
    
    def calculate(self):
        """计算水蒸气性质 - 统一方法名"""
        try:
            if self.current_mode == "饱和状态":
                self.calculate_saturation_properties()
            else:
                self.calculate_other_properties()
                
        except ValueError as e:
            QMessageBox.critical(self, "输入错误", f"参数输入格式错误: {str(e)}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "计算过程中出现除零错误")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")
    
    def clear_inputs(self):
        """清空输入和结果"""
        self.sat_param1_input.clear()
        self.dryness_input.setText("1.0")
        self.other_param1_input.clear()
        self.other_param2_input.clear()
        self.result_text.clear()
    
    def _get_history_data(self):
        """提供历史记录数据"""
        mode = self.current_mode
        inputs = {"计算模式": mode}
        outputs = {}
        try:
            if mode == "饱和状态":
                checked_button = self.sat_known_button_group.checkedButton()
                param_type = checked_button.text() if checked_button else "压力 P"
                param_value = float(self.sat_param1_input.text() or 0)
                dryness = float(self.dryness_input.text() or 0)
                inputs["已知参数"] = param_type
                inputs["参数值"] = param_value
                inputs["干度"] = dryness

                try:
                    if "压力" in param_type:
                        pressure_mpa = param_value
                        saturation_temp = iapws_T_sat(pressure_mpa)
                    else:
                        temperature_c = param_value
                        pressure_mpa = iapws_P_sat(temperature_c)
                        saturation_temp = temperature_c

                    sat = iapws_sat_props(P_MPa=pressure_mpa)
                    if dryness < 1:
                        ws = iapws_wet_steam(P_MPa=pressure_mpa, dryness=dryness)
                        density = ws["rho"]
                        enthalpy = ws["h"]
                        entropy = ws["s"]
                    else:
                        density = sat["rho_g"]
                        enthalpy = sat["h_g"]
                        entropy = sat["s_g"]

                except Exception:
                    density = 0; enthalpy = 0; entropy = 0; saturation_temp = 0; pressure_mpa = 0

                outputs = { "压力_MPa": round(pressure_mpa, 4), "温度_C": round(saturation_temp, 2), "密度_kg_m3": round(density, 5), "比容_m3_kg": round(1/density, 5) if density > 0 else 0, "焓_kJ_kg": round(enthalpy, 2), "熵_kJ_kgK": round(entropy, 4)
                }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}
    
    def get_project_info(self):
        """获取项目信息 - 用于报告生成"""
        return { "project_name": "水蒸气性质查询", "calculation_type": self.calculation_type, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operator": "User"
        }
    
    def generate_report(self):
        """生成计算结果报告"""
        result_text = self.result_text.toPlainText()
        
        if not result_text or "计算结果" not in result_text:
            QMessageBox.warning(self, "生成失败", "请先进行计算再生成报告")
            return None
        
        project_info = self.get_project_info()
        
        report = f"""
========================================
           水蒸气性质查询计算书
========================================

项目信息:
    项目名称: {project_info["project_name"]}
    计算类型: {project_info["calculation_type"]}
    计算时间: {project_info["timestamp"]}
    操作人: {project_info["operator"]}

========================================
          计算结果
========================================

{result_text}

========================================
          计算说明
========================================

1. 本计算基于 IAPWS-IF97 工业标准
2. 计算结果仅供参考，实际应用请参考相关标准
3. 对于精确计算，建议使用专业物性软件
4. 在临界点附近物性变化剧烈，需要特别注意

========================================
          结束
========================================
"""
        return report
    
    def calculate_saturation_properties(self):
        """计算饱和状态水蒸气性质"""
        checked_button = self.sat_known_button_group.checkedButton()
        if checked_button:
            param_type = checked_button.text()
        else:
            param_type = "压力 P"
        
        param_value = float(self.sat_param1_input.text() or 0)
        dryness = float(self.dryness_input.text() or 0)
        
        if not param_value:
            QMessageBox.warning(self, "输入错误", "请输入参数值")
            return
        
        if dryness < 0 or dryness > 1:
            QMessageBox.warning(self, "输入错误", "干度必须在0~1之间")
            return
        
        if "压力" in param_type:
            pressure_mpa = param_value
            saturation_temp = self.calculate_saturation_temperature(pressure_mpa)
        else:
            temperature_c = param_value
            pressure_mpa = self.calculate_saturation_pressure(temperature_c)
            saturation_temp = temperature_c
        
        density = self.calculate_steam_density(pressure_mpa, saturation_temp, dryness)
        enthalpy = self.calculate_enthalpy(pressure_mpa, saturation_temp, dryness)
        entropy = self.calculate_entropy(pressure_mpa, saturation_temp, dryness)
        specific_volume = 1 / density if density > 0 else 0
        
        if dryness == 0:
            state = "饱和水"
            state_icon = ""
        elif dryness == 1:
            state = "干饱和蒸汽"
            state_icon = ""
        else:
            state = f"湿蒸汽 (干度={dryness:.3f})"
            state_icon = ""
        
        result = self.format_saturation_result(
            param_type, param_value, dryness, pressure_mpa, saturation_temp,
            state, state_icon, density, specific_volume, enthalpy, entropy
        )
        
        # 使用 setPlainText 输出结果
        self.result_text.setPlainText(result)
        
        if hasattr(self, "calculation_completed"):
            self.calculation_completed.emit({ "mode": "saturation", "pressure": pressure_mpa, "temperature": saturation_temp, "dryness": dryness, "state": state, "density": density, "enthalpy": enthalpy, "entropy": entropy
            })
    
    def calculate_other_properties(self):
        """计算其他状态水蒸气性质"""
        checked_button = self.other_known_button_group.checkedButton()
        if checked_button:
            param_combo = checked_button.text()
        else:
            param_combo = "压力 P 和温度 T"
        
        param1_value = float(self.other_param1_input.text() or 0)
        param2_value = float(self.other_param2_input.text() or 0)
        
        if not param1_value or not param2_value:
            QMessageBox.warning(self, "输入错误", "请输入所有参数值")
            return
        
        if "压力 P 和温度 T" in param_combo:
            pressure_mpa = param1_value
            temperature_c = param2_value
            
            try:
                sat = iapws_sat_props(P_MPa=pressure_mpa)
                saturation_temp = sat["T_C"]
            except Exception:
                saturation_temp = self.calculate_saturation_temperature(pressure_mpa)
            
            if temperature_c < saturation_temp - 0.1:
                state = "过冷水"
                state_icon = ""
                dryness = 0
            elif abs(temperature_c - saturation_temp) < 0.1:
                state = "饱和状态"
                state_icon = ""
                dryness = 1
            else:
                state = "过热蒸汽"
                state_icon = ""
                dryness = 1
        
        elif "压力 P 和比焓 H" in param_combo:
            pressure_mpa = param1_value
            enthalpy_kjkg = param2_value
            
            try:
                result_ph = iapws_from_ph(pressure_mpa, enthalpy_kjkg)
                temperature_c = result_ph["T_C"]
                dryness = result_ph["dryness"]
                state_en = result_ph["phase"]

                state_map = { "subcooled_liquid": "过冷水", "wet_steam": "湿蒸汽", "superheated_steam": "过热蒸汽",
                }
                state = state_map.get(state_en, state_en)
                state_icon = ""
                saturation_temp = self.calculate_saturation_temperature(pressure_mpa)
            except Exception as e:
                QMessageBox.critical(self, "计算错误", f"IAPWS P-H 求解失败: {str(e)}")
                return
        
        else:  # 压力 P 和比熵 S
            pressure_mpa = param1_value
            entropy_kjkgk = param2_value
            
            try:
                result_ps = iapws_from_ps(pressure_mpa, entropy_kjkgk)
                temperature_c = result_ps["T_C"]
                dryness = result_ps["dryness"]
                state_en = result_ps["phase"]

                state_map = { "subcooled_liquid": "过冷水", "wet_steam": "湿蒸汽", "superheated_steam": "过热蒸汽",
                }
                state = state_map.get(state_en, state_en)
                state_icon = ""
                saturation_temp = self.calculate_saturation_temperature(pressure_mpa)
            except Exception as e:
                QMessageBox.critical(self, "计算错误", f"IAPWS P-S 求解失败: {str(e)}")
                return
        
        density = self.calculate_steam_density(pressure_mpa, temperature_c, dryness)
        enthalpy = self.calculate_enthalpy(pressure_mpa, temperature_c, dryness)
        entropy = self.calculate_entropy(pressure_mpa, temperature_c, dryness)
        specific_volume = 1 / density if density > 0 else 0
        superheat = temperature_c - saturation_temp if temperature_c > saturation_temp else 0
        
        result = self.format_other_result(
            param_combo, pressure_mpa, param2_value, temperature_c, saturation_temp,
            state, state_icon, dryness, density, specific_volume, enthalpy, entropy, superheat
        )
        
        self.result_text.setPlainText(result)
        
        if hasattr(self, "calculation_completed"):
            self.calculation_completed.emit({ "mode": "other", "param_combo": param_combo, "pressure": pressure_mpa, "param2": param2_value, "temperature": temperature_c, "dryness": dryness, "state": state, "density": density, "enthalpy": enthalpy, "entropy": entropy
            })
    
    def calculate_saturation_temperature(self, pressure_mpa):
        """计算饱和温度 [°C]"""
        try:
            return iapws_T_sat(pressure_mpa)
        except Exception:
            return 373.95
    
    def calculate_saturation_pressure(self, temperature_c):
        """计算饱和压力 [MPa]"""
        try:
            return iapws_P_sat(temperature_c)
        except Exception:
            return 22.064
    
    def calculate_steam_density(self, pressure_mpa, temperature_c, dryness=1):
        """计算蒸汽/水密度 [kg/m³]"""
        try:
            if dryness < 1:
                ws = iapws_wet_steam(P_MPa=pressure_mpa, dryness=dryness)
                return ws["rho"]
            else:
                T_sat = iapws_T_sat(pressure_mpa)
                if abs(temperature_c - T_sat) < 0.1:
                    sat = iapws_sat_props(P_MPa=pressure_mpa)
                    return sat["rho_g"]
                else:
                    props = iapws_steam_props(pressure_mpa, temperature_c)
                    return props["rho"]
        except Exception:
            return 0.5
    
    def calculate_enthalpy(self, pressure_mpa, temperature_c, dryness=1):
        """计算比焓 [kJ/kg]"""
        try:
            if dryness < 1:
                ws = iapws_wet_steam(P_MPa=pressure_mpa, dryness=dryness)
                return ws["h"]
            else:
                T_sat = iapws_T_sat(pressure_mpa)
                if abs(temperature_c - T_sat) < 0.1:
                    sat = iapws_sat_props(P_MPa=pressure_mpa)
                    return sat["h_g"]
                else:
                    props = iapws_steam_props(pressure_mpa, temperature_c)
                    return props["h"]
        except Exception:
            return 2700.0
    
    def calculate_entropy(self, pressure_mpa, temperature_c, dryness=1):
        """计算比熵 [kJ/(kg·K)]"""
        try:
            if dryness < 1:
                ws = iapws_wet_steam(P_MPa=pressure_mpa, dryness=dryness)
                return ws["s"]
            else:
                T_sat = iapws_T_sat(pressure_mpa)
                if abs(temperature_c - T_sat) < 0.1:
                    sat = iapws_sat_props(P_MPa=pressure_mpa)
                    return sat["s_g"]
                else:
                    props = iapws_steam_props(pressure_mpa, temperature_c)
                    return props["s"]
        except Exception:
            return 7.0
    
    def format_saturation_result(self, param_type, param_value, dryness, pressure, temperature,
                                state, state_icon, density, specific_volume, enthalpy, entropy):
        """格式化饱和状态结果"""
        unit = param_type.split()[-1]
        dryness_desc = ""
        if 0 < dryness < 1:
            dryness_desc = "\n\n* 干度 {:.3f} 表示蒸汽中含有 {:.1f}% 的饱和蒸汽".format(dryness, dryness*100)
        elif dryness == 0:
            dryness_desc = "\n\n* 饱和水状态，可用于加热或传热计算"
        elif dryness == 1:
            dryness_desc = "\n\n* 干饱和蒸汽，可用于动力或工艺过程"
        
        latent_heat = self.calculate_enthalpy(pressure, temperature, 1) - self.calculate_enthalpy(pressure, temperature, 0)
        
        return f"""═══════════════════════════════════════════════════
                         输入参数
═══════════════════════════════════════════════════

* 查询模式: 饱和状态
* 已知参数: {param_type}
* 参数值: {param_value:.4f} {unit}
* 干度: {dryness:.3f}

═══════════════════════════════════════════════════
                        计算结果
═══════════════════════════════════════════════════

* 压力: {pressure:.4f} MPa
* 温度: {temperature:.2f} C
* 状态: {state_icon} {state}

物性参数:
* 密度: {density:.4f} kg/m3
* 比容: {specific_volume:.6f} m3/kg
* 比焓: {enthalpy:.2f} kJ/kg
* 比熵: {entropy:.4f} kJ/(kg.K)

饱和参数对比:
* 饱和压力: {pressure:.4f} MPa
* 饱和温度: {temperature:.2f} C
* 汽化潜热: {latent_heat:.1f} kJ/kg

═══════════════════════════════════════════════════
                        状态说明
═══════════════════════════════════════════════════

{state_icon} {state}{dryness_desc}

═══════════════════════════════════════════════════
                        应用建议
═══════════════════════════════════════════════════

* 以上数据为工程近似值
* 实际应用请参考IAPWS-IF97标准
* 对于精确计算，建议使用专业物性软件
* 在临界点附近物性变化剧烈，需要特别注意"""
    
    def format_other_result(self, param_combo, pressure, param2_value, temperature, saturation_temp,
                           state, state_icon, dryness, density, specific_volume, enthalpy, entropy, superheat):
        """格式化其他状态结果"""
        param2_name = param_combo.split("和")[1].strip()
        state_desc = ""
        if superheat > 0:
            if 10 < superheat <= 50:
                state_desc = "\n\n* 过热度 {:.1f}C，属于中等过热蒸汽".format(superheat)
            elif superheat > 50:
                state_desc = "\n\n* 过热度 {:.1f}C，属于高度过热蒸汽".format(superheat)
            if abs(temperature - saturation_temp) < 5:
                state_desc += "\n* 接近饱和状态，需要注意汽水分离"
        elif temperature < saturation_temp - 0.1:
            state_desc = "\n\n* 处于过冷水状态，需要加热才能产生蒸汽"
        
        temp_diff = superheat if superheat > 0 else saturation_temp - temperature
        diff_label = "过热度" if superheat > 0 else "过冷度"
        
        dryness_line = ""
        if 0 < dryness < 1:
            dryness_line = "\n* 干度: {:.3f}".format(dryness)
        superheat_line = ""
        if superheat > 0:
            superheat_line = "\n* 过热度: {:.2f} C".format(superheat)
        
        return """============================================================
                         输入参数
============================================================

* 查询模式: 其他状态
* 已知参数: {}
* 压力 P: {:.4f} MPa
* {}: {:.4f}

============================================================
                        计算结果
============================================================

* 压力: {:.4f} MPa
* 温度: {:.2f} C
* 状态: {} {}{}{}

物性参数:
* 密度: {:.4f} kg/m3
* 比容: {:.6f} m3/kg
* 比焓: {:.2f} kJ/kg
* 比熵: {:.4f} kJ/(kg.K)

参考数据:
* 饱和温度: {:.2f} C
* 当前温度: {:.2f} C
* {}: {:.2f} C

============================================================
                        状态说明
============================================================

{} {}{}

============================================================
                        应用建议
============================================================

* 以上数据为工程近似值
* 实际应用请参考IAPWS-IF97标准
* 对于精确计算，建议使用专业物性软件
* 在临界点附近物性变化剧烈，需要特别注意""".format(
            param_combo, pressure, param2_name, param2_value,
            pressure, temperature, state_icon, state, dryness_line, superheat_line,
            density, specific_volume, enthalpy, entropy,
            saturation_temp, temperature,
            diff_label, temp_diff,
            state_icon, state, state_desc
        )

# ==================== 报告生成函数 ====================

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "SteamPropertyCalculator")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "SteamPropertyCalculator")
    def _pdf_add_line(self, pdf, line):
        """PDF添加单行文本"""
        try:
            if line.startswith("==="):
                pdf.ln(3)
                return
            
            if line.strip().startswith("*") or line.strip().startswith("物性") or line.strip().startswith("饱和") or line.strip().startswith("应用") or line.strip().startswith("状态"):
                pdf.set_font("Helvetica", "B", 10)
            else:
                pdf.set_font("Helvetica", "", 10)
            
            line_text = line.replace("*", " ").strip()
            pdf.multi_cell(0, 5, line_text)
        except Exception:
            pass

# ==================== 测试代码 ====================
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = SteamPropertyCalculator()
    calculator.resize(1200, 800)
    calculator.show()
    
    sys.exit(app.exec())
