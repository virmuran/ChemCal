from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QFrame,
    QScrollArea, QDialog, QSpinBox, QButtonGroup, QGridLayout, QFileDialog,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math
import sys
import os

# 导入工业级精度制冷剂物性模块
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "refrigerant_eos", 
        os.path.join(parent_dir, "refrigerant_eos.py")
    )
    _refrigerant_eos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_refrigerant_eos)
    
    USE_INDUSTRIAL_CYCLE = True
    print("成功加载工业级制冷循环计算模块 (refrigerant_eos)")
except Exception as e:
    print(f"警告: 无法加载工业级制冷循环模块: {e}")
    print("将使用简化计算方法")
    USE_INDUSTRIAL_CYCLE = False
    _refrigerant_eos = None

from modules.combo_box_utils import ComboBoxWheelBlocker
import sys
from pathlib import Path

# DOCX 报告导出
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.docx_utils import ReportExporter

# 统一的QGroupBox样式
GROUP_STYLE = """
    QGroupBox {
        font-weight: bold;
        border: 1px solid #888;
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 8px 0 8px;
    }
"""
COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #888;
        border-radius: 4px;
        padding: 6px 10px;
        /* background via theme */
        color: black;
    }
    QComboBox QAbstractItemView {
        /* background-color via theme */
        color: black;
        border: 1px solid #888;
        selection-background-color: #3498db;
        selection-color: black;
    }
    QComboBox QAbstractItemView::item {
        padding: 3px 8px;
    }
"""

class RefrigerationCycleCalculator(QWidget):
    """制冷循环计算器"""
    calculation_type = "refrigeration_cycle_calculator"

    def __init__(self, parent=None, data_manager=None):
        """初始化制冷循环计算器
        
        Args:
            parent: 父窗口
            data_manager: 数据管理器，用于保存历史记录
        """
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_result = ""
        self._last_params = {}
        self.setup_ui()
        self.setup_refrigerant_data()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self._wheel_blocker = ComboBoxWheelBlocker(self)
        for combo in self.findChildren(QComboBox):
            combo.installEventFilter(self._wheel_blocker)

    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None
    
    def setup_ui(self):
        """设置制冷循环计算UI"""
        # 创建主布局
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ========== 左侧输入区 ==========
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } "
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部说明文字
        description = QLabel(
            "计算蒸汽压缩制冷循环的性能参数，包括制冷量、压缩功、COP等。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)

        # ========== 循环类型选择组 ==========
        cycle_group = QGroupBox("循环类型")
        cycle_layout = QHBoxLayout(cycle_group)
        cycle_layout.setSpacing(10)

        self.cycle_button_group = QButtonGroup(self)

        cycles = [
            ("理想循环", "无过冷过热"),
            ("实际循环", "包含过冷过热")
        ]

        for i, (cycle_name, tooltip) in enumerate(cycles):
            btn = QPushButton(cycle_name)
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
                    color: black;
                    text-align: center;
                }
                QPushButton:checked {
                    background-color: #4b5cc4;
                    color: white;
                }
                QPushButton:hover:!checked {
                    background-color: #c0ebd7;
                    color: black;
                }
            """)
            self.cycle_button_group.addButton(btn, i)
            cycle_layout.addWidget(btn)

        cycle_layout.addStretch()
        self.cycle_button_group.button(0).setChecked(True)
        self.cycle_button_group.buttonClicked.connect(self.on_cycle_type_changed)

        left_layout.addWidget(cycle_group)

        # ========== 输入参数组 ==========
        input_group = QGroupBox("输入参数")

        input_layout = QGridLayout(input_group)
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)

        row = 0

        # 制冷剂选择
        label_ref = QLabel("制冷剂:")
        label_ref.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label_ref.setStyleSheet("font-weight: bold; padding-right: 10px;")
        label_ref.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(label_ref, row, 0)

        self.refrigerant_combo = QComboBox()
        self.refrigerant_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_refrigerant_options()
        self.refrigerant_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.refrigerant_combo.currentTextChanged.connect(self.on_refrigerant_changed)
        input_layout.addWidget(self.refrigerant_combo, row, 1)

        hint_ref = QLabel("选择循环工质")
        hint_ref.setStyleSheet("font-style: italic;")
        hint_ref.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(hint_ref, row, 2)

        row += 1

        # 蒸发温度
        label_evap = QLabel("蒸发温度 (°C):")
        label_evap.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label_evap.setStyleSheet("font-weight: bold; padding-right: 10px;")
        label_evap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(label_evap, row, 0)

        self.evap_temp_input = QLineEdit()
        self.evap_temp_input.setPlaceholderText("例如: -10")
        self.evap_temp_input.setValidator(QDoubleValidator(-100.0, 100.0, 2))
        self.evap_temp_input.setText("-10")
        self.evap_temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.evap_temp_input, row, 1)

        hint_evap = QLabel("制冷剂蒸发温度")
        hint_evap.setStyleSheet("font-style: italic;")
        hint_evap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(hint_evap, row, 2)

        row += 1

        # 冷凝温度
        label_cond = QLabel("冷凝温度 (°C):")
        label_cond.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label_cond.setStyleSheet("font-weight: bold; padding-right: 10px;")
        label_cond.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(label_cond, row, 0)

        self.cond_temp_input = QLineEdit()
        self.cond_temp_input.setPlaceholderText("例如: 40")
        self.cond_temp_input.setValidator(QDoubleValidator(-50.0, 100.0, 2))
        self.cond_temp_input.setText("40")
        self.cond_temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.cond_temp_input, row, 1)

        hint_cond = QLabel("制冷剂冷凝温度")
        hint_cond.setStyleSheet("font-style: italic;")
        hint_cond.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(hint_cond, row, 2)

        row += 1

        # 过冷度
        self.subcool_label = QLabel("过冷度 (K):")
        self.subcool_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.subcool_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        self.subcool_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.subcool_label, row, 0)

        self.subcool_input = QLineEdit()
        self.subcool_input.setPlaceholderText("例如: 5")
        self.subcool_input.setValidator(QDoubleValidator(0.0, 50.0, 2))
        self.subcool_input.setText("5")
        self.subcool_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.subcool_input, row, 1)

        self.subcool_hint = QLabel("仅实际循环")
        self.subcool_hint.setStyleSheet("font-style: italic;")
        self.subcool_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.subcool_hint, row, 2)

        row += 1

        # 过热度
        self.superheat_label = QLabel("过热度 (K):")
        self.superheat_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.superheat_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        self.superheat_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.superheat_label, row, 0)

        self.superheat_input = QLineEdit()
        self.superheat_input.setPlaceholderText("例如: 5")
        self.superheat_input.setValidator(QDoubleValidator(0.0, 50.0, 2))
        self.superheat_input.setText("5")
        self.superheat_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.superheat_input, row, 1)

        self.superheat_hint = QLabel("仅实际循环")
        self.superheat_hint.setStyleSheet("font-style: italic;")
        self.superheat_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.superheat_hint, row, 2)

        row += 1

        # 质量流量
        label_flow = QLabel("质量流量 (kg/s):")
        label_flow.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label_flow.setStyleSheet("font-weight: bold; padding-right: 10px;")
        label_flow.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(label_flow, row, 0)

        self.mass_flow_input = QLineEdit()
        self.mass_flow_input.setPlaceholderText("例如: 0.1")
        self.mass_flow_input.setValidator(QDoubleValidator(0.001, 100.0, 6))
        self.mass_flow_input.setText("0.1")
        self.mass_flow_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.mass_flow_input, row, 1)

        hint_flow = QLabel("循环制冷剂流量")
        hint_flow.setStyleSheet("font-style: italic;")
        hint_flow.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(hint_flow, row, 2)

        row += 1

        # 压缩机效率
        label_eff = QLabel("压缩机效率 (%):")
        label_eff.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label_eff.setStyleSheet("font-weight: bold; padding-right: 10px;")
        label_eff.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(label_eff, row, 0)

        self.comp_eff_input = QLineEdit()
        self.comp_eff_input.setPlaceholderText("例如: 80")
        self.comp_eff_input.setValidator(QDoubleValidator(10.0, 100.0, 2))
        self.comp_eff_input.setText("80")
        self.comp_eff_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.comp_eff_input, row, 1)

        hint_eff = QLabel("等熵效率")
        hint_eff.setStyleSheet("font-style: italic;")
        hint_eff.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(hint_eff, row, 2)

        left_layout.addWidget(input_group)

        # ========== 计算按钮 ==========
        calculate_btn = QPushButton("计算")
        calculate_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        calculate_btn.setMinimumHeight(50)
        calculate_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        calculate_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                min-height: 50px; padding: 0px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219955;
            } """)
        calculate_btn.clicked.connect(self.calculate)
        left_layout.addWidget(calculate_btn)

        # ========== 底部按钮行 ==========
        bottom_layout = QHBoxLayout()
        
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
        
        bottom_layout.addWidget(self.clear_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.download_docx_btn)
        bottom_layout.addWidget(self.download_pdf_btn)
        left_layout.addLayout(bottom_layout)
        left_layout.addStretch()  # 将内容顶到顶部，剩余空间在底部

        # ========== 右侧结果区 ==========
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        # 结果显示组
        result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet(
            "QTextEdit { /* bg via theme */border: 1px solid #ecf0f1; "
            "border-radius: 6px; font-family: Consolas, monospace; font-size: 13px; padding: 8px; }"
        )
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        result_layout.addWidget(self.result_text)

        right_layout.addWidget(result_group)

        # ========== 将左右两部分添加到主布局 ==========
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

        # 初始状态设置
        self.on_cycle_type_changed()

    def setup_refrigerant_data(self):
        """设置制冷剂物性数据"""
        self.refrigerant_data = {
            "R134a": {
                "critical_temp": 101.1,  # °C
                "critical_pressure": 4059,  # kPa
                "molecular_weight": 102.03,  # g/mol
                "ODP": 0,  # 臭氧破坏潜能
                "GWP": 1430  # 全球变暖潜能
            },
            "R22": {
                "critical_temp": 96.2,
                "critical_pressure": 4970,
                "molecular_weight": 86.47,
                "ODP": 0.055,
                "GWP": 1810
            },
            "R410A": {
                "critical_temp": 72.1,
                "critical_pressure": 4900,
                "molecular_weight": 72.58,
                "ODP": 0,
                "GWP": 2088
            },
            "R32": {
                "critical_temp": 78.4,
                "critical_pressure": 5780,
                "molecular_weight": 52.02,
                "ODP": 0,
                "GWP": 675
            },
            "R717 (氨)": {
                "critical_temp": 132.3,
                "critical_pressure": 11280,
                "molecular_weight": 17.03,
                "ODP": 0,
                "GWP": 0
            },
            "R744 (CO₂)": {
                "critical_temp": 31.1,
                "critical_pressure": 7380,
                "molecular_weight": 44.01,
                "ODP": 0,
                "GWP": 1
            }
        }
    
    def setup_refrigerant_options(self):
        """设置制冷剂选项"""
        refrigerants = [
            "R134a - HFC制冷剂，环保型",
            "R22 - HCFC制冷剂，逐步淘汰",
            "R410A - HFC混合制冷剂，空调常用",
            "R32 - HFC制冷剂，低GWP",
            "R717 (氨) - 天然制冷剂，高效",
            "R744 (CO₂) - 天然制冷剂，环保"
        ]
        self.refrigerant_combo.addItems(refrigerants)
    
    def on_refrigerant_changed(self, text):
        """处理制冷剂选择变化"""
        pass
    
    def on_cycle_type_changed(self):
        """处理循环类型变化"""
        is_actual = self.cycle_button_group.checkedButton().text() == "实际循环"
        
        # 对于理想循环，隐藏过冷过热输入
        self.subcool_label.setVisible(is_actual)
        self.subcool_input.setVisible(is_actual)
        self.subcool_hint.setVisible(is_actual)
        self.superheat_label.setVisible(is_actual)
        self.superheat_input.setVisible(is_actual)
        self.superheat_hint.setVisible(is_actual)
    
    def calculate_saturation_pressure(self, refrigerant, temperature):
        """计算饱和压力（简化计算）
        
        Args:
            refrigerant: 制冷剂名称
            temperature: 温度（°C）
            
        Returns:
            饱和压力（kPa）
        """
        # 使用Antoine方程简化计算
        if refrigerant == "R134a":
            A, B, C = 6.9094, 1169.0, 224.0
        elif refrigerant == "R22":
            A, B, C = 6.9399, 1117.0, 231.0
        elif refrigerant == "R410A":
            A, B, C = 6.9454, 1125.0, 232.0
        elif refrigerant == "R32":
            A, B, C = 6.8935, 1083.0, 236.0
        elif refrigerant == "R717 (氨)":
            A, B, C = 7.3605, 926.0, 240.0
        elif refrigerant == "R744 (CO₂)":
            A, B, C = 6.8123, 1301.0, 273.0
        else:
            A, B, C = 6.9094, 1169.0, 224.0  # 默认R134a
        
        T = temperature + 273.15  # 转换为K
        P_sat = math.exp(A - B/(T - C)) * 100  # kPa
        return P_sat
    
    def calculate_enthalpy(self, refrigerant, temperature, pressure, is_vapor=True):
        """计算焓值（简化计算）
        
        Args:
            refrigerant: 制冷剂名称
            temperature: 温度（°C）
            pressure: 压力（kPa）
            is_vapor: 是否为气相
            
        Returns:
            焓值（kJ/kg）
        """
        # 简化计算，实际应用中应使用详细的物性表或方程
        if refrigerant == "R134a":
            if is_vapor:
                # 蒸汽焓值
                return 250 + 1.8 * temperature  # kJ/kg
            else:
                # 液体焓值
                return 100 + 1.5 * temperature  # kJ/kg
        else:
            # 其他制冷剂的简化计算
            if is_vapor:
                return 250 + 1.8 * temperature
            else:
                return 100 + 1.5 * temperature
    
    def calculate_entropy(self, refrigerant, temperature, pressure, is_vapor=True):
        """计算熵值（简化计算）
        
        Args:
            refrigerant: 制冷剂名称
            temperature: 温度（°C）
            pressure: 压力（kPa）
            is_vapor: 是否为气相
            
        Returns:
            熵值（kJ/kg·K）
        """
        if refrigerant == "R134a":
            if is_vapor:
                return 0.9 + 0.01 * temperature  # kJ/kg·K
            else:
                return 0.4 + 0.005 * temperature  # kJ/kg·K
        else:
            if is_vapor:
                return 0.9 + 0.01 * temperature
            else:
                return 0.4 + 0.005 * temperature
    
    def calculate(self):
        """计算制冷循环 - 统一接口方法
        
        此方法为统一UI规范要求的接口，调用实际的计算逻辑
        """
        try:
            # 获取输入值
            cycle_type = self.cycle_button_group.checkedButton().text()
            refrigerant_text = self.refrigerant_combo.currentText()
            refrigerant = refrigerant_text.split(" - ")[0]
            
            evap_temp = float(self.evap_temp_input.text())
            cond_temp = float(self.cond_temp_input.text())
            mass_flow = float(self.mass_flow_input.text())
            comp_efficiency = float(self.comp_eff_input.text()) / 100
            
            # 验证输入
            if evap_temp >= cond_temp:
                QMessageBox.warning(self, "输入错误", "蒸发温度必须低于冷凝温度")
                return
            
            if cycle_type == "实际循环":
                subcool = float(self.subcool_input.text())
                superheat = float(self.superheat_input.text())
            else:
                subcool = 0
                superheat = 0
            
            # 制冷剂名称映射
            ref_map = {
                "R134a": "R134a",
                "R22": "R22",
                "R410A": "R410A",
                "R32": "R32",
                "R717 (氨)": "R717",
                "R744 (CO₂)": "R410A",  # CO2 无 Antoine 系数，近似使用 R410A
            }
            ref_name = ref_map.get(refrigerant, "R134a")
            
            # 尝试使用工业级精度计算
            if USE_INDUSTRIAL_CYCLE and ref_name in getattr(_refrigerant_eos, 'REFRIGERANTS', {}):
                result = self._calculate_cycle_industrial(
                    ref_name, evap_temp, cond_temp, subcool, superheat,
                    mass_flow, comp_efficiency, cycle_type
                )
            else:
                result = self._calculate_cycle_simplified(
                    refrigerant, evap_temp, cond_temp, subcool, superheat,
                    mass_flow, comp_efficiency, cycle_type
                )
            
            # 输出结果到QTextEdit
            self.result_text.setPlainText(result)
            self._last_result = result
            self._last_params = {
                "cycle_type": cycle_type,
                "refrigerant": refrigerant,
                "evap_temp": evap_temp,
                "cond_temp": cond_temp,
                "subcool": subcool,
                "superheat": superheat,
                "mass_flow": mass_flow,
                "comp_efficiency": comp_efficiency,
            }

            # 保存历史
            
        except ValueError as e:
            QMessageBox.critical(self, "计算错误", f"参数输入格式错误: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def _calculate_cycle_industrial(self, ref_name, evap_temp, cond_temp, 
                                     subcool, superheat, mass_flow, comp_efficiency, cycle_type):
        """工业级精度制冷循环计算 (PR EOS)
        
        Args:
            ref_name: 制冷剂名称
            evap_temp: 蒸发温度（°C）
            cond_temp: 冷凝温度（°C）
            subcool: 过冷度（K）
            superheat: 过热度（K）
            mass_flow: 质量流量（kg/s）
            comp_efficiency: 压缩机效率（0-1）
            cycle_type: 循环类型
            
        Returns:
            格式化后的计算结果字符串
        """
        eos = _refrigerant_eos
        ref_data = eos.REFRIGERANTS[ref_name]
        
        # --- 状态1: 压缩机进口 (蒸发器出口) ---
        T1_K = evap_temp + 273.15 + superheat
        sat_ev = eos.saturation_properties(T_K=evap_temp + 273.15, ref_name=ref_name)
        P_evap_MPa = sat_ev['P_MPa']
        
        # 过热蒸汽性质
        T1_C = evap_temp + superheat
        prop1 = eos.vapor_properties(P_evap_MPa, T1_C, ref_name=ref_name)
        h1 = prop1['h']
        s1 = prop1['s']
        T1 = T1_C
        
        # --- 状态2: 压缩机出口 (等熵压缩) ---
        sat_cd = eos.saturation_properties(T_K=cond_temp + 273.15, ref_name=ref_name)
        P_cond_MPa = sat_cd['P_MPa']
        
        # 等熵压缩温度近似（理想气体）
        cp_g = ref_data['cp_ideal']
        R_spec = 8.314 / (ref_data['M'] / 1000.0)  # J/(kg·K)
        gamma = (cp_g * 1000.0 + R_spec) / R_spec
        
        T2_ideal_K = T1_K * (P_cond_MPa / P_evap_MPa) ** ((gamma - 1.0) / gamma)
        h2s = h1 + cp_g * (T2_ideal_K - T1_K)
        h2 = h1 + (h2s - h1) / comp_efficiency
        T2_C = T2_ideal_K - 273.15 + (1.0 / comp_efficiency - 1.0) * 20  # 近似排气温度

        # --- 状态3: 冷凝器出口 (过冷液体) ---
        T3_C = cond_temp - subcool
        prop3 = eos.liquid_properties(P_cond_MPa, T3_C, ref_name=ref_name)
        h3 = prop3['h']
        T3 = T3_C

        # --- 状态4: 膨胀阀出口 (等焓节流) ---
        h4 = h3
        # 计算节流后干度
        x4 = (h4 - sat_ev['h_f']) / sat_ev['h_fg'] if sat_ev['h_fg'] > 0 else 0.2
        x4 = max(0.0, min(1.0, x4))
        T4 = evap_temp

        # --- 循环性能计算 ---
        refrigeration_effect = h1 - h4
        compressor_work = h2 - h1
        heat_rejection = h2 - h3

        COP = refrigeration_effect / compressor_work if compressor_work > 0.01 else 0
        compressor_power = mass_flow * compressor_work
        refrigeration_capacity = mass_flow * refrigeration_effect

        # 效率分析
        carnot_COP = (evap_temp + 273.15) / (cond_temp - evap_temp)
        efficiency = COP / carnot_COP * 100

        # 容积制冷量
        rho_evap = sat_ev['rho_g']
        volumetric_capacity = refrigeration_effect * rho_evap

        # 压力比
        pressure_ratio = P_cond_MPa / P_evap_MPa if P_evap_MPa > 0 else 0

        # 输运性质
        tp = eos.transport_properties(P_evap_MPa, evap_temp, ref_name=ref_name, phase='vapor')
        mu_evap = tp['mu'] * 1e6  # Pa·s -> μPa·s
        k_evap = tp['k']          # W/(m·K)

        P_evap_kPa = P_evap_MPa * 1000
        P_cond_kPa = P_cond_MPa * 1000

        method_note = "PR EOS + Antoine + Rackett" if USE_INDUSTRIAL_CYCLE else "简化计算"

        return f"""═══════════════════════════════════════════════════
                         输入参数
═══════════════════════════════════════════════════

循环类型: {cycle_type}
制冷剂: {ref_name}
蒸发温度: {evap_temp} °C
冷凝温度: {cond_temp} °C
过冷度: {subcool} K
过热度: {superheat} K
质量流量: {mass_flow} kg/s
压缩机效率: {comp_efficiency*100:.1f} %
计算方法: {method_note}

═══════════════════════════════════════════════════
                        状态点参数
═══════════════════════════════════════════════════

• 点1 (压缩机进口 - 蒸发器出口):
  温度: {T1:.1f} °C, 压力: {P_evap_kPa:.1f} kPa
  焓值: {h1:.2f} kJ/kg, 熵值: {s1:.4f} kJ/(kg·K)

• 点2 (压缩机出口 - 冷凝器入口):
  温度: {T2_C:.1f} °C, 压力: {P_cond_kPa:.1f} kPa
  焓值: {h2:.2f} kJ/kg

• 点3 (冷凝器出口 - 膨胀阀入口):
  温度: {T3:.1f} °C, 压力: {P_cond_kPa:.1f} kPa
  焓值: {h3:.2f} kJ/kg

• 点4 (膨胀阀出口 - 蒸发器入口):
  温度: {T4:.1f} °C, 压力: {P_evap_kPa:.1f} kPa
  焓值: {h4:.2f} kJ/kg, 干度: {x4:.3f}

═══════════════════════════════════════════════════
                        性能参数
═══════════════════════════════════════════════════

单位质量参数:
• 制冷效应: {refrigeration_effect:.2f} kJ/kg
• 压缩功: {compressor_work:.2f} kJ/kg
• 排热量: {heat_rejection:.2f} kJ/kg
• 压力比: {pressure_ratio:.2f}

系统性能:
• 制冷量: {refrigeration_capacity:.2f} kW
• 压缩机功率: {compressor_power:.2f} kW
• 性能系数(COP): {COP:.3f}
• 单位容积制冷量: {volumetric_capacity:.1f} kJ/m³

效率分析:
• 卡诺循环COP: {carnot_COP:.3f}
• 循环效率: {efficiency:.1f} %

蒸发器侧输运性质:
• 粘度: {mu_evap:.2f} μPa·s
• 导热系数: {k_evap:.4f} W/(m·K)

═══════════════════════════════════════════════════
                        计算说明
═══════════════════════════════════════════════════

• 基于 Peng-Robinson 状态方程 + Antoine 方程 + Rackett 方程
• 压缩过程: 理想气体等熵近似 + 效率修正
• 膨胀过程: 等焓节流
• 饱和性质精度: ±2%, P-V-T 精度: ±3%
• 结果适用于工程初步设计和方案比选"""

    def _calculate_cycle_simplified(self, refrigerant, evap_temp, cond_temp,
                                     subcool, superheat, mass_flow, comp_efficiency, cycle_type):
        """简化计算（保底方案）
        
        Args:
            refrigerant: 制冷剂名称
            evap_temp: 蒸发温度（°C）
            cond_temp: 冷凝温度（°C）
            subcool: 过冷度（K）
            superheat: 过热度（K）
            mass_flow: 质量流量（kg/s）
            comp_efficiency: 压缩机效率（0-1）
            cycle_type: 循环类型
            
        Returns:
            格式化后的计算结果字符串
        """
        # 计算各状态点参数
        P_evap = self.calculate_saturation_pressure(refrigerant, evap_temp)
        T1 = evap_temp + superheat
        h1 = self.calculate_enthalpy(refrigerant, T1, P_evap, is_vapor=True)
        s1 = self.calculate_entropy(refrigerant, T1, P_evap, is_vapor=True)

        P_cond = self.calculate_saturation_pressure(refrigerant, cond_temp)
        h2s = h1 + (P_cond - P_evap) * 0.1
        h2 = h1 + (h2s - h1) / comp_efficiency
        T2 = cond_temp + 20

        T3 = cond_temp - subcool
        h3 = self.calculate_enthalpy(refrigerant, T3, P_cond, is_vapor=False)

        h4 = h3
        T4 = evap_temp

        refrigeration_effect = h1 - h4
        compressor_work = h2 - h1
        heat_rejection = h2 - h3

        COP = refrigeration_effect / compressor_work
        compressor_power = mass_flow * compressor_work
        refrigeration_capacity = mass_flow * refrigeration_effect

        carnot_COP = (evap_temp + 273.15) / (cond_temp - evap_temp)
        efficiency = COP / carnot_COP * 100

        return self._format_results(
            cycle_type, refrigerant, evap_temp, cond_temp, subcool, superheat,
            mass_flow, comp_efficiency, P_evap, P_cond, h1, h2, h3, h4,
            refrigeration_effect, compressor_work, heat_rejection, COP,
            compressor_power, refrigeration_capacity, carnot_COP, efficiency
        )

    def _format_results(self, cycle_type, refrigerant, evap_temp, cond_temp, subcool, 
                      superheat, mass_flow, comp_efficiency, P_evap, P_cond, h1, h2, 
                      h3, h4, refrigeration_effect, compressor_work, heat_rejection, 
                      COP, compressor_power, refrigeration_capacity, carnot_COP, efficiency):
        """格式化计算结果
        
        Args:
            各种计算参数
            
        Returns:
            格式化后的字符串
        """
        return f"""═══════════════════════════════════════════════════
                         输入参数
═══════════════════════════════════════════════════

循环类型: {cycle_type}
制冷剂: {refrigerant}
蒸发温度: {evap_temp} °C
冷凝温度: {cond_temp} °C
过冷度: {subcool} K
过热度: {superheat} K
质量流量: {mass_flow} kg/s
压缩机效率: {comp_efficiency*100:.1f} %

═══════════════════════════════════════════════════
                        状态点参数
═══════════════════════════════════════════════════

• 点1 (压缩机进口):
  温度: {evap_temp + superheat:.1f} °C, 压力: {P_evap:.1f} kPa
  焓值: {h1:.2f} kJ/kg

• 点2 (压缩机出口):
  温度: {cond_temp + 20:.1f} °C, 压力: {P_cond:.1f} kPa  
  焓值: {h2:.2f} kJ/kg

• 点3 (冷凝器出口):
  温度: {cond_temp - subcool:.1f} °C, 压力: {P_cond:.1f} kPa
  焓值: {h3:.2f} kJ/kg

• 点4 (膨胀阀出口):
  温度: {evap_temp:.1f} °C, 压力: {P_evap:.1f} kPa
  焓值: {h4:.2f} kJ/kg

═══════════════════════════════════════════════════
                        性能参数
═══════════════════════════════════════════════════

单位质量参数:
• 制冷效应: {refrigeration_effect:.2f} kJ/kg
• 压缩功: {compressor_work:.2f} kJ/kg  
• 排热量: {heat_rejection:.2f} kJ/kg

系统性能:
• 制冷量: {refrigeration_capacity:.2f} kW
• 压缩机功率: {compressor_power:.2f} kW
• 性能系数(COP): {COP:.3f}

效率分析:
• 卡诺循环COP: {carnot_COP:.3f}
• 循环效率: {efficiency:.1f} %

═══════════════════════════════════════════════════
                        计算说明
═══════════════════════════════════════════════════

• 基于蒸汽压缩制冷循环理论计算
• 使用简化物性计算方法
• 假设压缩过程为等熵过程
• 膨胀过程为等焓过程
• 冷凝器和蒸发器压力为饱和压力
• 结果仅供参考，实际系统性能可能有所不同"""

    def clear_inputs(self):
        """清空所有输入"""
        self.cycle_button_group.button(0).setChecked(True)
        self.refrigerant_combo.setCurrentIndex(0)
        self.evap_temp_input.setText("-10")
        self.cond_temp_input.setText("40")
        self.subcool_input.setText("5")
        self.superheat_input.setText("5")
        self.mass_flow_input.setText("0.1")
        self.comp_eff_input.setText("80")
        self.result_text.clear()
        self._last_result = ""
        self._last_params = {}

    def get_project_info(self):
        """获取项目信息 - 统一接口方法
        
        Returns:
            项目信息字典
        """
        return {"calculator": "RefrigerationCycleCalculator", "name": "制冷循环计算"}

    def generate_report(self):
        """生成报告 - 统一接口方法
        
        Returns:
            报告文本
        """
        return self.result_text.toPlainText()

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "RefrigerationCycleCalculator")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "RefrigerationCycleCalculator")
    def _get_history_data(self):
        """获取历史记录数据 - 统一接口方法
        
        Returns:
            包含输入和输出数据的字典
        """
        cycle_type = self.cycle_button_group.checkedButton().text()
        refrigerant_text = self.refrigerant_combo.currentText()
        refrigerant = refrigerant_text.split(" - ")[0]
        evap_temp = float(self.evap_temp_input.text() or 0)
        cond_temp = float(self.cond_temp_input.text() or 0)
        mass_flow = float(self.mass_flow_input.text() or 0)
        comp_efficiency = float(self.comp_eff_input.text() or 0) / 100

        inputs = {
            "循环类型": cycle_type,
            "制冷剂": refrigerant,
            "蒸发温度_C": evap_temp,
            "冷凝温度_C": cond_temp,
            "质量流量_kg_s": mass_flow,
            "压缩机效率_%": comp_efficiency * 100
        }

        outputs = {}
        try:
            if cycle_type == "实际循环":
                subcool = float(self.subcool_input.text() or 0)
                superheat = float(self.superheat_input.text() or 0)
                inputs["过冷度_C"] = subcool
                inputs["过热度_C"] = superheat
            else:
                subcool = 0
                superheat = 0

            ref_map = {
                "R134a": "R134a", "R22": "R22", "R410A": "R410A",
                "R32": "R32", "R717 (氨)": "R717", "R744 (CO₂)": "R410A",
            }
            ref_name = ref_map.get(refrigerant, "R134a")

            if USE_INDUSTRIAL_CYCLE and ref_name in getattr(_refrigerant_eos, 'REFRIGERANTS', {}):
                sat_ev = _refrigerant_eos.saturation_properties(T_K=evap_temp+273.15, ref_name=ref_name)
                sat_cd = _refrigerant_eos.saturation_properties(T_K=cond_temp+273.15, ref_name=ref_name)
                P_evap = sat_ev['P_MPa'] * 1000
                P_cond = sat_cd['P_MPa'] * 1000

                T1_C = evap_temp + superheat
                prop1 = _refrigerant_eos.vapor_properties(sat_ev['P_MPa'], T1_C, ref_name=ref_name)
                h1 = prop1['h']

                ref_data = _refrigerant_eos.REFRIGERANTS[ref_name]
                cp_g = ref_data['cp_ideal']
                R_spec = 8.314 / (ref_data['M'] / 1000.0)
                gamma = (cp_g * 1000.0 + R_spec) / R_spec
                T1_K = T1_C + 273.15
                T2_ideal_K = T1_K * (sat_cd['P_MPa'] / sat_ev['P_MPa']) ** ((gamma - 1.0) / gamma)
                h2s = h1 + cp_g * (T2_ideal_K - T1_K)
                h2 = h1 + (h2s - h1) / comp_efficiency

                T3_C = cond_temp - subcool
                prop3 = _refrigerant_eos.liquid_properties(sat_cd['P_MPa'], T3_C, ref_name=ref_name)
                h3 = prop3['h']
                h4 = h3

                refrigeration_effect = h1 - h4
                compressor_work = h2 - h1
                COP = refrigeration_effect / compressor_work
                compressor_power = mass_flow * compressor_work
                refrigeration_capacity = mass_flow * refrigeration_effect
                carnot_COP = (evap_temp + 273.15) / (cond_temp - evap_temp)
            else:
                P_evap = self.calculate_saturation_pressure(refrigerant, evap_temp)
                P_cond = self.calculate_saturation_pressure(refrigerant, cond_temp)
                T1 = evap_temp + superheat
                h1 = self.calculate_enthalpy(refrigerant, T1, P_evap, is_vapor=True)
                h2s = h1 + (P_cond - P_evap) * 0.1
                h2 = h1 + (h2s - h1) / comp_efficiency
                h3 = self.calculate_enthalpy(refrigerant, cond_temp - subcool, P_cond, is_vapor=False)
                h4 = h3
                refrigeration_effect = h1 - h4
                compressor_work = h2 - h1
                COP = refrigeration_effect / compressor_work
                compressor_power = mass_flow * compressor_work
                refrigeration_capacity = mass_flow * refrigeration_effect
                carnot_COP = (evap_temp + 273.15) / (cond_temp - evap_temp)

            outputs = {
                "制冷量_kW": round(refrigeration_capacity, 2),
                "压缩机功率_kW": round(compressor_power, 2),
                "COP": round(COP, 3),
                "卡诺COP": round(carnot_COP, 3),
                "单位制冷量_kJ_kg": round(refrigeration_effect, 2),
                "单位压缩功_kJ_kg": round(compressor_work, 2)
            }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = RefrigerationCycleCalculator()
    widget.resize(1300, 700)
    widget.show()
    
    sys.exit(app.exec())
