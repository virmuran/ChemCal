from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QGridLayout, QMessageBox,
    QButtonGroup, QScrollArea, QSizePolicy,
)
from PySide6.QtGui import QDoubleValidator
from PySide6.QtCore import Qt
import math
import re
import importlib.util
import os
from datetime import datetime


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K
from utils.docx_utils import ReportExporter
# DOCX 报告导出

# ─────────────────── IAPWS-IF97 动态加载 ───────────────────
_IAPWS_MODULE = None
_IAPWS_AVAILABLE = False

def _load_iapws():
    """动态加载 steam_iapws 模块"""
    global _IAPWS_MODULE, _IAPWS_AVAILABLE
    if _IAPWS_MODULE is not None or _IAPWS_AVAILABLE:
        return _IAPWS_AVAILABLE
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location(
            "steam_iapws",
            os.path.join(base_dir, "steam_iapws.py")
        )
        if spec is None:
            _IAPWS_AVAILABLE = False
            return False
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _IAPWS_MODULE = module
        _IAPWS_AVAILABLE = True
        return True
    except Exception:
        _IAPWS_AVAILABLE = False
        return False

_load_iapws()


class 蒸汽管径流量(CalculatorBase):
    """蒸汽管径和流量查询（左右布局优化版 - 统一UI风格）"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        
        # 使用传入的数据管理器或创建新的
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
            
        self.setup_ui()
        self.setup_widget_references()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()
    
    def init_data_manager(self):
        """初始化数据管理器 - 使用单例模式"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
            print("使用共享的数据管理器实例")
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None
    
    def setup_widget_references(self):
        """设置控件引用 - 修复findChild问题"""
        # 通过对象名称来查找控件
        self.flow_label = None
        self.diameter_label = None
        
        # 查找标签
        for widget in self.findChildren(QLabel):
            text = widget.text()
            if "蒸汽流量" in text:
                self.flow_label = widget
            elif "管道内径" in text:
                self.diameter_label = widget
    
    def setup_ui(self):
        """设置左右布局的蒸汽管径和流量查询UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧：输入参数区域 (占2/3宽度)
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        scroll_left.setWidgetResizable(True)

        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")  # 限制最大宽度
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # 1. 首先添加说明文本
        description = QLabel(
            "根据蒸汽压力、温度和流量计算推荐管径，或根据管径计算最大蒸汽流量。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 2. 计算模式选择 - 使用按钮组
        mode_group = CalculatorBase.make_group_box("计算模式")
        mode_layout = QHBoxLayout(mode_group)

        self.mode_button_group = QButtonGroup(self)
        self.mode_buttons = {}

        modes = [
            ("根据流量计算管径", "输入蒸汽流量，计算推荐管径"),
            ("根据管径计算流量", "输入管径，计算最大蒸汽流量")
        ]

        for i, (mode_name, tooltip) in enumerate(modes):
            btn = CalculatorBase.make_mode_button(mode_name, tooltip)
            self.mode_button_group.addButton(btn, i)
            mode_layout.addWidget(btn)
            self.mode_buttons[mode_name] = btn

        # 默认选择第一个
        self.mode_buttons["根据流量计算管径"].setChecked(True)
        self.mode_button_group.buttonClicked.connect(self.on_mode_changed)

        left_layout.addWidget(mode_group)
        
        # 3. 输入参数组 - 使用GridLayout实现整齐的布局
        input_group = CalculatorBase.make_group_box("输入参数")

        # 使用GridLayout确保整齐排列
        input_layout = QGridLayout(input_group)
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)

        row = 0
        
        # 蒸汽压力
        pressure_label = QLabel("蒸汽压力 (MPa):")
        pressure_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pressure_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(pressure_label, row, 0)
        
        self.pressure_input = QLineEdit()
        self.pressure_input.setPlaceholderText("例如: 1.0")
        self.pressure_input.setValidator(QDoubleValidator(0.01, 20.0, 6))
        self.pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.pressure_input, row, 1)
        
        self.pressure_combo = QComboBox()
        self.pressure_combo.setStyleSheet(COMBOBOX_STYLE)
        self.pressure_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setup_pressure_options()
        self.pressure_combo.currentTextChanged.connect(self.on_pressure_changed)
        input_layout.addWidget(self.pressure_combo, row, 2)
        
        row += 1
        
        # 蒸汽温度
        temperature_label = QLabel("蒸汽温度 (°C):")
        temperature_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        temperature_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(temperature_label, row, 0)
        
        self.temperature_input = QLineEdit()
        self.temperature_input.setPlaceholderText("例如: 200")
        self.temperature_input.setValidator(QDoubleValidator(100.0, 600.0, 6))
        self.temperature_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.temperature_input, row, 1)
        
        self.temperature_combo = QComboBox()
        self.temperature_combo.setStyleSheet(COMBOBOX_STYLE)
        self.temperature_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setup_temperature_options()
        self.temperature_combo.currentTextChanged.connect(self.on_temperature_changed)
        input_layout.addWidget(self.temperature_combo, row, 2)
        
        row += 1
        
        # 流量输入（管径计算模式）
        self.flow_label_widget = QLabel("蒸汽流量 (kg/h):")  # 使用不同的变量名
        self.flow_label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.flow_label_widget.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(self.flow_label_widget, row, 0)
        
        self.flow_input = QLineEdit()
        self.flow_input.setPlaceholderText("例如: 1000")
        self.flow_input.setValidator(QDoubleValidator(1.0, 100000.0, 6))
        self.flow_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.flow_input, row, 1)
        
        self.flow_combo = QComboBox()
        self.flow_combo.setStyleSheet(COMBOBOX_STYLE)
        self.flow_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setup_flow_options()
        self.flow_combo.currentTextChanged.connect(self.on_flow_changed)
        input_layout.addWidget(self.flow_combo, row, 2)
        
        row += 1
        
        # 管径输入（流量计算模式） - 隐藏初始状态
        self.diameter_label_widget = QLabel("管道内径 (mm):")  # 使用不同的变量名
        self.diameter_label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.diameter_label_widget.setStyleSheet(INPUT_LABEL_STYLE)
        self.diameter_label_widget.setVisible(False)
        input_layout.addWidget(self.diameter_label_widget, row, 0)
        
        self.diameter_input = QLineEdit()
        self.diameter_input.setPlaceholderText("例如: 50")
        self.diameter_input.setValidator(QDoubleValidator(10.0, 1000.0, 6))
        self.diameter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.diameter_input.setVisible(False)
        input_layout.addWidget(self.diameter_input, row, 1)
        
        self.diameter_combo = QComboBox()
        self.diameter_combo.setStyleSheet(COMBOBOX_STYLE)
        self.diameter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setup_diameter_options()
        self.diameter_combo.currentTextChanged.connect(self.on_diameter_changed)
        self.diameter_combo.setVisible(False)
        input_layout.addWidget(self.diameter_combo, row, 2)
        
        left_layout.addWidget(input_group)
        left_layout.addStretch()

        # 右侧：结果显示区域 (占1/3宽度)
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        
        # 结果显示
        self.result_group = CalculatorBase.make_group_box("计算结果")
        result_layout = QVBoxLayout(self.result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        # 结果框统一标准：边框/背景/文字色交给主题系统，仅指定等宽字体
        self.result_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: 13px;
            } """)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        result_layout.addWidget(self.result_text)

        right_layout.addWidget(self.result_group)

        # 底部按钮行：清空 | DOCX | PDF
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setStyleSheet(CLEAR_BTN_STYLE)
        self.clear_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.clear_btn.clicked.connect(self.clear_inputs)
        docx_btn = QPushButton("DOCX")
        docx_btn.setStyleSheet(DOCX_BTN_STYLE)
        docx_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        docx_btn.clicked.connect(self.download_docx_report)
        pdf_btn = QPushButton("PDF")
        pdf_btn.setStyleSheet(PDF_BTN_STYLE)
        pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pdf_btn.clicked.connect(self.download_pdf_report)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(docx_btn)
        btn_layout.addWidget(pdf_btn)
        right_layout.addLayout(btn_layout)

        # 计算按钮（最底部）
        self.calculate_btn = self.make_calc_button("计 算")
        self.calculate_btn.clicked.connect(self.calculate_steam_pipe)
        right_layout.addWidget(self.calculate_btn)

        # 将左右两部分添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)  # 左侧占2/3
        main_layout.addWidget(right_widget, 1)  # 右侧占1/3
        
        # 设置初始显示状态
        self.on_mode_changed("根据流量计算管径")
    
    def get_current_mode(self):
        """获取当前选择的计算模式"""
        checked_button = self.mode_button_group.checkedButton()
        if checked_button:
            return checked_button.text()
        return "根据流量计算管径"  # 默认值
    
    def on_mode_changed(self, mode):
        """处理计算模式变化"""
        if isinstance(mode, QPushButton):
            mode = mode.text()
            
        if "根据管径计算流量" in mode:
            # 隐藏流量相关控件
            self.flow_label_widget.setVisible(False)
            self.flow_input.setVisible(False)
            self.flow_combo.setVisible(False)
            # 显示管径相关控件
            self.diameter_label_widget.setVisible(True)
            self.diameter_input.setVisible(True)
            self.diameter_combo.setVisible(True)
        else:
            # 显示流量相关控件
            self.flow_label_widget.setVisible(True)
            self.flow_input.setVisible(True)
            self.flow_combo.setVisible(True)
            # 隐藏管径相关控件
            self.diameter_label_widget.setVisible(False)
            self.diameter_input.setVisible(False)
            self.diameter_combo.setVisible(False)
    
    def setup_pressure_options(self):
        """设置蒸汽压力选项"""
        pressure_options = [
            "- 请选择蒸汽压力 -",
            "0.1 MPa - 低压蒸汽",
            "0.3 MPa - 低压蒸汽",
            "0.6 MPa - 中压蒸汽",
            "1.0 MPa - 中压蒸汽",
            "1.6 MPa - 高压蒸汽",
            "2.5 MPa - 高压蒸汽",
            "4.0 MPa - 超高压蒸汽",
            "自定义压力"
        ]
        self.pressure_combo.addItems(pressure_options)
        self.pressure_combo.setCurrentIndex(0)
    
    def setup_temperature_options(self):
        """设置蒸汽温度选项"""
        temperature_options = [
            "- 请选择蒸汽温度 -",
            "100°C - 饱和蒸汽",
            "120°C - 饱和蒸汽",
            "150°C - 饱和蒸汽",
            "180°C - 饱和蒸汽",
            "200°C - 过热蒸汽",
            "250°C - 过热蒸汽",
            "300°C - 过热蒸汽",
            "400°C - 高温蒸汽",
            "自定义温度"
        ]
        self.temperature_combo.addItems(temperature_options)
        self.temperature_combo.setCurrentIndex(0)
    
    def setup_flow_options(self):
        """设置蒸汽流量选项"""
        flow_options = [
            "- 请选择流量范围 -",
            "小流量: 10-100 kg/h",
            "中等流量: 100-1000 kg/h",
            "大流量: 1000-10000 kg/h",
            "超大流量: 10000-100000 kg/h",
            "自定义流量"
        ]
        self.flow_combo.addItems(flow_options)
        self.flow_combo.setCurrentIndex(0)
    
    def setup_diameter_options(self):
        """设置管道内径选项"""
        diameter_options = [
            "- 请选择管道内径 -",
            "DN15 - 15 mm",
            "DN20 - 20 mm",
            "DN25 - 25 mm",
            "DN32 - 32 mm",
            "DN40 - 40 mm",
            "DN50 - 50 mm",
            "DN65 - 65 mm",
            "DN80 - 80 mm",
            "DN100 - 100 mm",
            "DN125 - 125 mm",
            "DN150 - 150 mm",
            "DN200 - 200 mm",
            "DN250 - 250 mm",
            "DN300 - 300 mm",
            "自定义管径"
        ]
        self.diameter_combo.addItems(diameter_options)
        self.diameter_combo.setCurrentIndex(0)
    
    def on_pressure_changed(self, text):
        """处理压力选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.pressure_input.clear()
            self.pressure_input.setPlaceholderText("输入压力值")
            self.pressure_input.setReadOnly(False)
            return
            
        if "自定义" in text:
            self.pressure_input.setReadOnly(False)
            self.pressure_input.setPlaceholderText("输入自定义压力")
            self.pressure_input.clear()
        else:
            self.pressure_input.setReadOnly(True)
            try:
                # 从文本中提取数字
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    pressure_value = float(match.group(1))
                    self.pressure_input.setText(f"{pressure_value:.1f}")
            except:
                pass
    
    def on_temperature_changed(self, text):
        """处理温度选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.temperature_input.clear()
            self.temperature_input.setPlaceholderText("输入温度值")
            self.temperature_input.setReadOnly(False)
            return
            
        if "自定义" in text:
            self.temperature_input.setReadOnly(False)
            self.temperature_input.setPlaceholderText("输入自定义温度")
            self.temperature_input.clear()
        else:
            self.temperature_input.setReadOnly(True)
            try:
                # 从文本中提取数字
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    temperature_value = float(match.group(1))
                    self.temperature_input.setText(f"{temperature_value:.0f}")
            except:
                pass
    
    def on_flow_changed(self, text):
        """处理流量选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.flow_input.clear()
            self.flow_input.setPlaceholderText("输入流量值")
            self.flow_input.setReadOnly(False)
            return
            
        if "自定义" in text:
            self.flow_input.setReadOnly(False)
            self.flow_input.setPlaceholderText("输入自定义流量")
            self.flow_input.clear()
        else:
            self.flow_input.setReadOnly(True)
            try:
                # 从文本中提取数字范围
                match = re.search(r'(\d+\.?\d*)-(\d+\.?\d*)', text)
                if match:
                    min_val = float(match.group(1))
                    max_val = float(match.group(2))
                    avg_val = (min_val + max_val) / 2
                    self.flow_input.setText(f"{avg_val:.0f}")
            except:
                pass
    
    def on_diameter_changed(self, text):
        """处理管径选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.diameter_input.clear()
            self.diameter_input.setPlaceholderText("输入管径值")
            self.diameter_input.setReadOnly(False)
            return
            
        if "自定义" in text:
            self.diameter_input.setReadOnly(False)
            self.diameter_input.setPlaceholderText("输入自定义管径")
            self.diameter_input.clear()
        else:
            self.diameter_input.setReadOnly(True)
            try:
                # 从文本中提取数字
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    diameter_value = float(match.group(1))
                    self.diameter_input.setText(f"{diameter_value:.0f}")
            except:
                pass
    
    def clear_inputs(self):
        """清空所有输入参数"""
        for widget in self.findChildren(QLineEdit):
            widget.clear()
        for widget in self.findChildren(QComboBox):
            widget.setCurrentIndex(0)

    def calculate_steam_pipe(self):
        """计算蒸汽管径或流量"""
        try:
            # 获取输入值
            mode = self.get_current_mode()
            pressure = float(self.pressure_input.text() or 0)
            temperature = float(self.temperature_input.text() or 0)
            
            # 验证输入
            if not pressure or not temperature:
                QMessageBox.warning(self, "输入错误", "请填写蒸汽压力和温度")
                return
            
            # 计算蒸汽密度
            steam_density = self.calculate_steam_density(pressure, temperature)
            specific_volume = 1 / steam_density if steam_density > 0 else 0
            
            if "根据流量计算管径" in mode:
                flow_rate = float(self.flow_input.text() or 0)
                if not flow_rate:
                    QMessageBox.warning(self, "输入错误", "请填写蒸汽流量")
                    return
                
                # 推荐蒸汽流速
                recommended_velocity = 25.0
                
                # 质量流量转换为体积流量
                volume_flow = (flow_rate / 3600) * specific_volume
                
                # 计算所需管径
                required_area = volume_flow / recommended_velocity
                required_diameter = math.sqrt(4 * required_area / math.pi) * 1000  # mm
                
                # 推荐标准管径
                standard_diameters = [15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 250, 300]
                recommended_diameter = min(standard_diameters, key=lambda x: abs(x - required_diameter))
                
                # 计算实际流速
                actual_area = math.pi * (recommended_diameter / 1000 / 2) ** 2
                actual_velocity = volume_flow / actual_area
                
                # 显示结果 - 使用格式化的输出
                result = self.format_diameter_result(
                    mode, pressure, temperature, steam_density, specific_volume,
                    flow_rate, volume_flow, required_diameter, recommended_diameter,
                    actual_velocity, required_area
                )
                
            else:  # 根据管径计算流量
                diameter = float(self.diameter_input.text() or 0)
                if not diameter:
                    QMessageBox.warning(self, "输入错误", "请填写管道内径")
                    return
                
                # 推荐蒸汽流速
                recommended_velocity = 25.0
                
                # 计算最大流量
                area = math.pi * (diameter / 1000 / 2) ** 2
                volume_flow = area * recommended_velocity
                max_flow_rate = volume_flow / specific_volume * 3600  # kg/h
                
                # 显示结果 - 使用格式化的输出
                result = self.format_flow_result(
                    mode, pressure, temperature, steam_density, specific_volume,
                    diameter, area, volume_flow, max_flow_rate, recommended_velocity
                )
            
            self.result_text.setText(result)
            
        except ValueError as e:
            QMessageBox.critical(self, "计算错误", f"参数输入格式错误: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def _get_history_data(self):
        """提供历史记录数据"""
        mode = self.get_current_mode()
        pressure = float(self.pressure_input.text() or 0)
        temperature = float(self.temperature_input.text() or 0)
        steam_density = self.calculate_steam_density(pressure, temperature)
        specific_volume = 1 / steam_density if steam_density > 0 else 0

        inputs = {
            "计算模式": mode,
            "压力_MPa": pressure,
            "温度_C": temperature,
            "蒸汽密度_kg_m3": round(steam_density, 4),
            "比容_m3_kg": round(specific_volume, 4)
        }

        outputs = {}
        try:
            if "根据流量计算管径" in mode:
                flow_rate = float(self.flow_input.text() or 0)
                inputs["质量流量_kg_h"] = flow_rate
                volume_flow = (flow_rate / 3600) * specific_volume
                inputs["体积流量_m3_s"] = round(volume_flow, 4)
                required_area = volume_flow / 25.0
                required_diameter = math.sqrt(4 * required_area / math.pi) * 1000
                standard_diameters = [15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 250, 300]
                recommended_diameter = min(standard_diameters, key=lambda x: abs(x - required_diameter))
                actual_area = math.pi * (recommended_diameter / 1000 / 2) ** 2
                actual_velocity = volume_flow / actual_area
                outputs = {
                    "所需管径_mm": round(required_diameter, 1),
                    "推荐标准管径": f"DN{recommended_diameter}",
                    "实际流速_m_s": round(actual_velocity, 2)
                }
            else:
                diameter = float(self.diameter_input.text() or 0)
                inputs["管道内径_mm"] = diameter
                area = math.pi * (diameter / 1000 / 2) ** 2
                volume_flow = area * 25.0
                max_flow_rate = volume_flow / specific_volume * 3600
                outputs = {
                    "截面积_m2": round(area, 5),
                    "体积流量_m3_s": round(volume_flow, 4),
                    "最大质量流量_kg_h": round(max_flow_rate, 1)
                }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def format_diameter_result(self, mode, pressure, temperature, steam_density, specific_volume,
                               flow_rate, volume_flow, required_diameter, recommended_diameter,
                               actual_velocity, required_area):
        """格式化管径计算结果"""
        return f"""═══════════
 输入参数
══════════

    计算模式: {mode}
    蒸汽压力: {pressure} MPa
    蒸汽温度: {temperature} °C
    蒸汽密度: {steam_density:.4f} kg/m³
    蒸汽比容: {specific_volume:.4f} m³/kg
    蒸汽流量: {flow_rate} kg/h

══════════
计算结果
══════════

    流量分析:
    • 质量流量: {flow_rate} kg/h
    • 体积流量: {volume_flow*3600:.2f} m³/h
    • 体积流量: {volume_flow:.6f} m³/s

    管径分析:
    • 计算所需管径: {required_diameter:.1f} mm
    • 推荐标准管径: DN{recommended_diameter} ({recommended_diameter} mm)

    流速分析:
    • 推荐蒸汽流速: 25.0 m/s
    • 实际蒸汽流速: {actual_velocity:.1f} m/s
    • 流速状态: {"正常" if 20 <= actual_velocity <= 40 else "注意"}

    技术参数:
    • 所需流通面积: {required_area:.6f} m²
    • 标准管流通面积: {math.pi * (recommended_diameter / 1000 / 2) ** 2:.6f} m²

══════════
计算说明
══════════

    • 推荐蒸汽流速范围: 20-40 m/s
    • 低压蒸汽可取较低流速，高压蒸汽可取较高流速
    • 实际应用请考虑压力损失和管道材质
    • 对于长距离输送，建议选择较低流速以减小压降
    • 计算结果仅供参考，实际应用请考虑安全系数"""
    
    def format_flow_result(self, mode, pressure, temperature, steam_density, specific_volume,
                          diameter, area, volume_flow, max_flow_rate, recommended_velocity):
        """格式化流量计算结果"""
        return f"""═══════════
 输入参数
══════════

    计算模式: {mode}
    蒸汽压力: {pressure} MPa
    蒸汽温度: {temperature} °C
    蒸汽密度: {steam_density:.4f} kg/m³
    蒸汽比容: {specific_volume:.4f} m³/kg
    管道内径: {diameter} mm

══════════
计算结果
══════════

    管道参数:
    • 管道内径: {diameter} mm
    • 流通面积: {area:.6f} m²

    流量分析:
    • 推荐蒸汽流速: {recommended_velocity} m/s
    • 最大蒸汽流量: {max_flow_rate:.0f} kg/h
    • 体积流量: {volume_flow*3600:.2f} m³/h

    不同流速对应流量:
    • 20 m/s (低流速): {volume_flow / recommended_velocity * 20 / specific_volume * 3600:.0f} kg/h
    • 25 m/s (标准流速): {max_flow_rate:.0f} kg/h
    • 30 m/s (较高流速): {volume_flow / recommended_velocity * 30 / specific_volume * 3600:.0f} kg/h
    • 40 m/s (高流速): {volume_flow / recommended_velocity * 40 / specific_volume * 3600:.0f} kg/h

══════════
计算说明
══════════

    • 推荐蒸汽流速范围: 20-40 m/s
    • 实际流量应考虑压力损失和安全系数
    • 对于重要应用，建议进行详细的水力计算
    • 计算结果仅供参考，实际应用请考虑具体工况"""
    
    def calculate_steam_density(self, pressure_mpa, temperature_c):
        """计算蒸汽密度（优先 IAPWS-IF97，失败则简化公式）"""
        temperature_k = temperature_c + C_TO_K

        # 优先使用 IAPWS-IF97
        if _IAPWS_MODULE is not None:
            try:
                # 判断是饱和还是过热：查饱和温度
                T_sat = _IAPWS_MODULE.tsat_p(pressure_mpa)  # 饱和温度 °C
                if temperature_c <= T_sat:
                    # 饱和蒸汽 → Region 4 饱和气体密度
                    props = _IAPWS_MODULE.region4_saturation(pressure_mpa)
                    vg = props['vg']  # 比容 m³/kg
                    return 1.0 / vg if vg > 0 else 0.1
                else:
                    # 过热蒸汽 → Region 2
                    props = _IAPWS_MODULE.region2(pressure_mpa, temperature_c)
                    v = props['v']  # 比容 m³/kg
                    return 1.0 / v if v > 0 else 0.1
            except Exception:
                pass

        # Fallback: 简化经验公式（误差较大，仅供参考）
        pressure_bar = pressure_mpa * 10
        if temperature_c < 200:
            density = 0.6 * pressure_bar / (temperature_c + 100)
        else:
            density = 0.5 * pressure_bar / (temperature_c + 150)
        return max(density, 0.1)
    
    def get_project_info(self):
        """获取工程信息 - 返回 dict"""
        try:
            saved_info = {}
            if self.data_manager:
                saved_info = self.data_manager.get_project_info()
            return {
                'company_name': saved_info.get('company_name', ''),
                'project_number': saved_info.get('project_number', ''),
                'project_name': saved_info.get('project_name', ''),
                'subproject_name': saved_info.get('subproject_name', ''),
                'report_number': ''
            }
        except Exception as e:
            print(f"获取工程信息失败: {e}")
            return {}

    def generate_report(self):
        """生成计算书"""
        try:
            # 获取当前结果文本
            result_text = self.result_text.toPlainText()
            
            # 检查结果是否为空
            if not result_text or ("计算结果" not in result_text and "计算模式" not in result_text):
                QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
                return None
                
            # 获取工程信息
            project_info = self.get_project_info()
            if not project_info:
                return None  # 用户取消了输入
            
            # 添加报告头信息
            report = f"""工程计算书 - 蒸汽管道计算
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
计算工具: ChemCal 工程计算模块
========================================

"""
            report += result_text
            
            # 添加工程信息部分
            report += f"""══════════
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

    计算书编号: STEAM-{datetime.now().strftime('%Y%m%d')}-001
    版本: 1.0
    状态: 正式计算书

══════════
备注说明
══════════

    1. 本计算书基于蒸汽工程原理及相关标准规范
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

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "蒸汽管径流量")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "蒸汽管径流量")

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = 蒸汽管径流量()
    calculator.resize(1200, 800)
    calculator.show()
    
    sys.exit(app.exec())