"""
离心泵功率计算器
遵循统一UI规范改造
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QGridLayout, QMessageBox,
    QScrollArea, QFileDialog, QSizePolicy,
)
from PySide6.QtGui import QFont, QDoubleValidator
from PySide6.QtCore import Qt
import os
import re

# 统一滚动条样式
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

# QGroupBox统一样式
GROUP_STYLE = """
    QGroupBox {
        font-weight: bold;
        border: 1px solid #bdc3c7;
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
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 6px 10px;
        background: white;
        color: black;
    }
    QComboBox QAbstractItemView {
        background-color: white;
        color: black;
        border: 1px solid #bdc3c7;
        selection-background-color: #3498db;
        selection-color: black;
    }
    QComboBox QAbstractItemView::item {
        padding: 3px 8px;
    }
"""


class CentrifugalPumpCalculator(QWidget):
    """离心泵功率计算器"""
    
    calculation_type = "pump_power_calculator"
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_result = ""
        self._last_params = {}
        self.setup_ui()

    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None
    
    def setup_ui(self):
        """设置UI布局"""
        # 主布局 - 水平布局
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧：输入参数区域
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }} {SCROLLBAR_STYLE}")
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        left_widget = QWidget()
        left_widget.setStyleSheet("QWidget { background: transparent; }")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部说明文字
        description = QLabel(
            "计算离心泵的轴功率、电机功率和效率，考虑流量、扬程、介质密度和泵效率。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #7f8c8d; font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 输入参数组
        input_group = QGroupBox("输入参数")
        input_group.setStyleSheet(GROUP_STYLE)
        
        # GridLayout三列布局
        input_layout = QGridLayout(input_group)
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)

        row = 0

        # 流量输入
        flow_label = QLabel("流量 (m³/h):")
        flow_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        flow_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        flow_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(flow_label, row, 0)

        self.flow_input = QLineEdit()
        self.flow_input.setPlaceholderText("例如: 100")
        self.flow_input.setValidator(QDoubleValidator(0.1, 10000.0, 6))
        self.flow_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.flow_input, row, 1)

        self.flow_combo = QComboBox()
        self.flow_combo.setStyleSheet(COMBOBOX_STYLE)
        self.flow_combo.addItems([
            "小流量: 0.1-10 m³/h",
            "中等流量: 10-100 m³/h",
            "大流量: 100-1000 m³/h",
            "超大流量: 1000-10000 m³/h",
            "自定义流量"
        ])
        self.flow_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.flow_combo.currentTextChanged.connect(self.on_flow_changed)
        input_layout.addWidget(self.flow_combo, row, 2)

        row += 1

        # 扬程输入
        head_label = QLabel("扬程 (m):")
        head_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        head_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        head_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(head_label, row, 0)

        self.head_input = QLineEdit()
        self.head_input.setPlaceholderText("例如: 50")
        self.head_input.setValidator(QDoubleValidator(0.1, 1000.0, 6))
        self.head_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.head_input, row, 1)

        self.head_combo = QComboBox()
        self.head_combo.setStyleSheet(COMBOBOX_STYLE)
        self.head_combo.addItems([
            "低扬程: 1-20 m",
            "中等扬程: 20-80 m",
            "高扬程: 80-200 m",
            "超高扬程: 200-1000 m",
            "自定义扬程"
        ])
        self.head_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.head_combo.currentTextChanged.connect(self.on_head_changed)
        input_layout.addWidget(self.head_combo, row, 2)

        row += 1

        # 介质密度
        density_label = QLabel("介质密度 (kg/m³):")
        density_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        density_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        density_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(density_label, row, 0)

        self.density_input = QLineEdit()
        self.density_input.setPlaceholderText("例如: 1000 (水)")
        self.density_input.setValidator(QDoubleValidator(1.0, 2000.0, 6))
        self.density_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.density_input, row, 1)

        self.density_combo = QComboBox()
        self.density_combo.setStyleSheet(COMBOBOX_STYLE)
        self.density_combo.addItems([
            "1000 - 水 (20°C)",
            "998 - 水 (25°C)",
            "983 - 水 (60°C)",
            "789 - 乙醇",
            "719 - 汽油",
            "850 - 柴油",
            "1261 - 甘油",
            "1025 - 海水",
            "自定义密度"
        ])
        self.density_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.density_combo.currentTextChanged.connect(self.on_density_changed)
        input_layout.addWidget(self.density_combo, row, 2)

        row += 1

        # 泵效率
        efficiency_label = QLabel("泵效率 (%):")
        efficiency_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        efficiency_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        efficiency_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(efficiency_label, row, 0)

        self.efficiency_input = QLineEdit()
        self.efficiency_input.setPlaceholderText("例如: 75")
        self.efficiency_input.setValidator(QDoubleValidator(10.0, 95.0, 6))
        self.efficiency_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.efficiency_input, row, 1)

        self.efficiency_combo = QComboBox()
        self.efficiency_combo.setStyleSheet(COMBOBOX_STYLE)
        self.efficiency_combo.addItems([
            "50-60% - 小型泵",
            "60-70% - 标准泵",
            "70-80% - 高效泵",
            "80-90% - 超高效泵",
            "自定义效率"
        ])
        self.efficiency_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.efficiency_combo.currentTextChanged.connect(self.on_efficiency_changed)
        input_layout.addWidget(self.efficiency_combo, row, 2)

        row += 1

        # 电机效率
        motor_efficiency_label = QLabel("电机效率 (%):")
        motor_efficiency_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        motor_efficiency_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        motor_efficiency_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(motor_efficiency_label, row, 0)

        self.motor_efficiency_input = QLineEdit()
        self.motor_efficiency_input.setPlaceholderText("例如: 92")
        self.motor_efficiency_input.setValidator(QDoubleValidator(50.0, 98.0, 6))
        self.motor_efficiency_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.motor_efficiency_input, row, 1)

        self.motor_efficiency_combo = QComboBox()
        self.motor_efficiency_combo.setStyleSheet(COMBOBOX_STYLE)
        self.motor_efficiency_combo.addItems([
            "85-88% - 小型电机",
            "88-92% - 标准电机",
            "92-95% - 高效电机",
            "95-97% - 超高效电机",
            "自定义效率"
        ])
        self.motor_efficiency_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.motor_efficiency_combo.currentTextChanged.connect(self.on_motor_efficiency_changed)
        input_layout.addWidget(self.motor_efficiency_combo, row, 2)

        row += 1

        # 安全系数
        safety_label = QLabel("安全系数:")
        safety_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        safety_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        safety_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(safety_label, row, 0)

        self.safety_combo = QComboBox()
        self.safety_combo.setStyleSheet(COMBOBOX_STYLE)
        self.safety_combo.addItems([
            "1.0 (无安全系数)",
            "1.05 (轻微)",
            "1.1 (标准)",
            "1.15 (保守)",
            "1.2 (高安全)",
            "1.25 (超高安全)"
        ])
        self.safety_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.safety_combo, row, 1)

        self.safety_hint = QLabel("默认选用标准安全系数")
        self.safety_hint.setStyleSheet("color: #7f8c8d; font-style: italic; padding-left: 10px;")
        self.safety_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.safety_hint, row, 2)
        
        left_layout.addWidget(input_group)
        
        # 计算按钮
        calculate_btn = QPushButton("  计  算  ")
        calculate_btn.clicked.connect(self.calculate)
        calculate_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        calculate_btn.setMinimumHeight(50)
        calculate_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        calculate_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-weight: bold; "
            "border: none; border-radius: 8px; min-height: 50px; padding: 0px; }"
            "QPushButton:hover { background-color: #219955; }"
        )
        left_layout.addWidget(calculate_btn)
        
        # 底部按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        b_clr = QPushButton("清空")
        b_clr.setMinimumHeight(50)
        b_clr.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        b_clr.setStyleSheet(
            "QPushButton { background-color: #95a5a6; color: white; font-weight: bold; "
            "border: none; border-radius: 6px; padding: 8px; }"
            "QPushButton:hover { background-color: #7f8c8d; }"
        )
        b_clr.clicked.connect(self.clear_inputs)

        b_txt = QPushButton("下载计算书(TXT)")
        b_txt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        b_txt.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-weight: bold; "
            "border: none; border-radius: 6px; padding: 8px; }"
            "QPushButton:hover { background-color: #219653; }"
        )
        b_txt.clicked.connect(self.download_txt_report)

        b_pdf = QPushButton("下载计算书(PDF)")
        b_pdf.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        b_pdf.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; font-weight: bold; "
            "border: none; border-radius: 6px; padding: 8px; }"
            "QPushButton:hover { background-color: #c0392b; }"
        )
        b_pdf.clicked.connect(self.generate_pdf_report)
        
        btn_row.addWidget(b_clr)
        btn_row.addStretch()
        btn_row.addWidget(b_txt)
        btn_row.addWidget(b_pdf)
        
        left_layout.addLayout(btn_row)
        left_layout.addStretch()
        
        # 右侧：结果显示区域
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        
        # 结果显示组
        result_group = QGroupBox("计算结果")
        result_group.setStyleSheet(GROUP_STYLE)
        result_layout = QVBoxLayout(result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet(
            "QTextEdit { background-color: #f8f9fa; border: 1px solid #ecf0f1; "
            "border-radius: 6px; font-family: Consolas, monospace; font-size: 13px; padding: 8px; }"
        )
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        result_layout.addWidget(self.result_text)
        
        right_layout.addWidget(result_group)
        
        # 添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)
    
    def on_flow_changed(self, text):
        """处理流量选择变化"""
        if "自定义" in text:
            self.flow_input.setReadOnly(False)
            self.flow_input.setPlaceholderText("输入自定义流量")
            self.flow_input.clear()
        else:
            self.flow_input.setReadOnly(True)
            match = re.search(r'(\d+\.?\d*)-(\d+\.?\d*)', text)
            if match:
                min_val = float(match.group(1))
                max_val = float(match.group(2))
                avg_val = (min_val + max_val) / 2
                self.flow_input.setText(f"{avg_val:.1f}")
    
    def on_head_changed(self, text):
        """处理扬程选择变化"""
        if "自定义" in text:
            self.head_input.setReadOnly(False)
            self.head_input.setPlaceholderText("输入自定义扬程")
            self.head_input.clear()
        else:
            self.head_input.setReadOnly(True)
            match = re.search(r'(\d+\.?\d*)-(\d+\.?\d*)', text)
            if match:
                min_val = float(match.group(1))
                max_val = float(match.group(2))
                avg_val = (min_val + max_val) / 2
                self.head_input.setText(f"{avg_val:.1f}")
    
    def on_density_changed(self, text):
        """处理密度选择变化"""
        if "自定义" in text:
            self.density_input.setReadOnly(False)
            self.density_input.setPlaceholderText("输入自定义密度")
            self.density_input.clear()
        else:
            self.density_input.setReadOnly(True)
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                density_value = float(match.group(1))
                self.density_input.setText(f"{density_value:.0f}")
    
    def on_efficiency_changed(self, text):
        """处理泵效率选择变化"""
        if "自定义" in text:
            self.efficiency_input.setReadOnly(False)
            self.efficiency_input.setPlaceholderText("输入自定义效率")
            self.efficiency_input.clear()
        else:
            self.efficiency_input.setReadOnly(True)
            match = re.search(r'(\d+\.?\d*)-(\d+\.?\d*)', text)
            if match:
                min_val = float(match.group(1))
                max_val = float(match.group(2))
                avg_val = (min_val + max_val) / 2
                self.efficiency_input.setText(f"{avg_val:.1f}")
    
    def on_motor_efficiency_changed(self, text):
        """处理电机效率选择变化"""
        if "自定义" in text:
            self.motor_efficiency_input.setReadOnly(False)
            self.motor_efficiency_input.setPlaceholderText("输入自定义效率")
            self.motor_efficiency_input.clear()
        else:
            self.motor_efficiency_input.setReadOnly(True)
            match = re.search(r'(\d+\.?\d*)-(\d+\.?\d*)', text)
            if match:
                min_val = float(match.group(1))
                max_val = float(match.group(2))
                avg_val = (min_val + max_val) / 2
                self.motor_efficiency_input.setText(f"{avg_val:.1f}")
    
    def get_safety_factor(self):
        """获取安全系数"""
        text = self.safety_combo.currentText()
        if "1.0" in text:
            return 1.0
        elif "1.05" in text:
            return 1.05
        elif "1.1" in text:
            return 1.1
        elif "1.15" in text:
            return 1.15
        elif "1.2" in text:
            return 1.2
        elif "1.25" in text:
            return 1.25
        else:
            return 1.1
    
    def calculate(self):
        """计算离心泵功率"""
        try:
            # 获取输入值
            flow_rate = float(self.flow_input.text() or 0)
            head = float(self.head_input.text() or 0)
            density = float(self.density_input.text() or 0)
            efficiency = float(self.efficiency_input.text() or 0)
            motor_efficiency = float(self.motor_efficiency_input.text() or 0)
            safety_factor = self.get_safety_factor()
            
            # 验证输入
            if not all([flow_rate, head, density, efficiency, motor_efficiency]):
                QMessageBox.warning(self, "输入错误", "请填写所有参数")
                return
            
            # 计算有效功率
            effective_power = (flow_rate / 3600) * density * 9.81 * head / 1000
            
            # 计算轴功率
            shaft_power = effective_power / (efficiency / 100)
            
            # 计算电机功率
            motor_power = shaft_power / (motor_efficiency / 100) * safety_factor
            
            # 计算总效率
            total_efficiency = (efficiency / 100) * (motor_efficiency / 100) * 100
            
            # 推荐电机规格
            standard_motors = [0.75, 1.1, 1.5, 2.2, 3.0, 4.0, 5.5, 7.5, 11, 15, 18.5, 22, 
                              30, 37, 45, 55, 75, 90, 110, 132, 160, 200, 250, 315, 355, 400]
            candidates = [m for m in standard_motors if m >= motor_power]
            recommended_motor = min(candidates) if candidates else standard_motors[-1]
            
            # 格式化结果
            result = f"""═══════════════════════════════════════════════════
                        输入参数
═══════════════════════════════════════════════════

运行参数:
• 流量: {flow_rate} m³/h
• 扬程: {head} m
• 介质密度: {density} kg/m³
• 泵效率: {efficiency} %
• 电机效率: {motor_efficiency} %
• 安全系数: {safety_factor}

═══════════════════════════════════════════════════
                       计算结果
═══════════════════════════════════════════════════

功率计算:
• 有效功率: {effective_power:.2f} kW
• 轴功率: {shaft_power:.2f} kW
• 电机功率: {motor_power:.2f} kW

效率分析:
• 总效率: {total_efficiency:.1f} %

设备选型:
• 推荐电机功率: {recommended_motor} kW

安全评估:
• 功率余量: {(recommended_motor - motor_power) / motor_power * 100:.1f}%

═══════════════════════════════════════════════════
                       计算公式
═══════════════════════════════════════════════════

P_有效 = (Q × ρ × g × H) / 3600000
P_轴 = P_有效 / η_泵
P_电机 = P_轴 / η_电机 × K_安全

其中:
Q = {flow_rate} m³/h (流量)
ρ = {density} kg/m³ (密度)
g = 9.81 m/s² (重力加速度)
H = {head} m (扬程)
η_泵 = {efficiency/100:.3f} (泵效率)
η_电机 = {motor_efficiency/100:.3f} (电机效率)
K_安全 = {safety_factor} (安全系数)

详细计算:
P_有效 = ({flow_rate} × {density} × 9.81 × {head}) / 3600000 = {effective_power:.2f} kW
P_轴 = {effective_power:.2f} / {efficiency/100:.3f} = {shaft_power:.2f} kW
P_电机 = {shaft_power:.2f} / {motor_efficiency/100:.3f} × {safety_factor} = {motor_power:.2f} kW

═══════════════════════════════════════════════════
                       应用说明
═══════════════════════════════════════════════════

• 实际选型应选择比计算功率大的标准电机
• 考虑启动电流和过载能力
• 对于重载启动，建议选择更大的安全系数
• 计算结果仅供参考，实际应用请考虑具体工况"""
            
            self.result_text.setPlainText(result)
            self._last_result = result
            self._last_params = {
                "flow": flow_rate,
                "head": head,
                "density": density,
                "efficiency": efficiency,
                "motor_efficiency": motor_efficiency,
                "safety_factor": safety_factor,
            }
            
            # 保存历史记录
            if self.data_manager:
                try:
                    self.data_manager.add_record(self.calculation_type, self._get_history_data())
                except Exception:
                    pass
            
        except ValueError as e:
            QMessageBox.critical(self, "计算错误", f"参数输入格式错误: {str(e)}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "效率不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")
    
    def clear_inputs(self):
        """清空所有输入"""
        self.flow_input.clear()
        self.head_input.clear()
        self.density_input.clear()
        self.efficiency_input.clear()
        self.motor_efficiency_input.clear()
        self.flow_combo.setCurrentIndex(0)
        self.head_combo.setCurrentIndex(0)
        self.density_combo.setCurrentIndex(0)
        self.efficiency_combo.setCurrentIndex(0)
        self.motor_efficiency_combo.setCurrentIndex(0)
        self.safety_combo.setCurrentIndex(2)
        self.result_text.clear()
        self._last_result = ""
        self._last_params = {}
    
    def _get_history_data(self):
        """获取当前输入输出数据，用于保存历史记录"""
        try:
            inputs = {
                "流量 (m³/h)": self.flow_input.text() or "",
                "扬程 (m)": self.head_input.text() or "",
                "介质密度 (kg/m³)": self.density_input.text() or "",
                "泵效率 (%)": self.efficiency_input.text() or "",
                "电机效率 (%)": self.motor_efficiency_input.text() or "",
                "安全系数": self.safety_combo.currentText(),
            }
            outputs = {}
            text = self.result_text.toPlainText()
            for key, pattern in [
                ("有效功率 (kW)", r"有效功率:\s*([\d.]+)\s*kW"),
                ("轴功率 (kW)", r"轴功率:\s*([\d.]+)\s*kW"),
                ("电机功率 (kW)", r"电机功率:\s*([\d.]+)\s*kW"),
                ("总效率 (%)", r"总效率:\s*([\d.]+)\s*%"),
                ("推荐电机 (kW)", r"推荐电机功率:\s*([\d.]+)\s*kW"),
            ]:
                m = re.search(pattern, text)
                if m:
                    outputs[key] = m.group(1)
            return {"inputs": inputs, "outputs": outputs}
        except Exception:
            return {"inputs": {}, "outputs": {}}
    
    def get_project_info(self):
        """获取项目信息"""
        return {"calculator": "CentrifugalPumpCalculator", "name": "离心泵功率计算"}
    
    def generate_report(self):
        """生成报告"""
        return self.result_text.toPlainText()
    
    def download_txt_report(self):
        """下载TXT报告"""
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先计算，再下载报告。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存TXT报告", "离心泵功率计算报告.txt", "文本文件 (*.txt)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "成功", f"报告已保存：\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败：{e}")
    
    def generate_pdf_report(self):
        """生成PDF报告"""
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先计算，再下载PDF。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存PDF报告", "离心泵功率计算报告.pdf", "PDF文件 (*.pdf)"
        )
        if not path:
            return
        try:
            from fpdf import FPDF
            
            pdf = FPDF()
            pdf.add_page()
            pdf.add_font('msyh', '', 'C:/Windows/Fonts/msyh.ttc', uni=True)
            pdf.set_font('msyh', '', 10)
            
            for line in content.split('\n'):
                if line.strip():
                    pdf.cell(0, 8, line.encode('latin1', 'replace').decode('latin1'))
                    pdf.ln()
                else:
                    pdf.ln(4)
            
            pdf.output(path)
            QMessageBox.information(self, "成功", f"PDF已保存：\n{path}")
        except ImportError:
            QMessageBox.critical(self, "错误", "缺少fpdf，请运行：pip install fpdf")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"PDF生成失败：{e}")
