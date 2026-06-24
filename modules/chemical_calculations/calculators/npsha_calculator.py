from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QGridLayout, QMessageBox,
    QScrollArea, QSizePolicy, QFileDialog,
)
from PySide6.QtGui import QFont, QDoubleValidator
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt
import os
import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K, G, ATM_PRESSURE_MPA, WATER_DENSITY, WATER_CP, load_steam_iapws, get_steam_props
from svg_utils import svg_text


class NPSHaCalculator(CalculatorBase):
    """离心泵NPSHa计算（左右布局优化版）"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self.setup_ui()
        self._update_svg_diagram()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception:
            self.data_manager = None

    def setup_ui(self):
        """设置左右布局的NPSHa计算UI"""
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
        
        # 说明文本
        description = QLabel(
            "计算离心泵的可用汽蚀余量(NPSHa)，评估泵的汽蚀性能。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 输入参数组 - 使用GridLayout实现整齐的布局
        input_group = QGroupBox("输入参数")
        
        # 使用GridLayout确保整齐排列
        input_layout = QGridLayout(input_group)
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)
        
        # 标签样式 - 右对齐
        label_style = """
            QLabel {
                font-weight: bold;
                padding-right: 10px;
            }
        """
        
        # 输入框和下拉菜单的固定宽度        
        row = 0
        
        # 液面压力（敞口容器为大气压，密闭容器为操作压力）
        surface_pressure_label = QLabel("液面压力 (kPaA):")
        surface_pressure_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        surface_pressure_label.setStyleSheet(label_style)
        input_layout.addWidget(surface_pressure_label, row, 0)
        
        self.surface_pressure_input = QLineEdit()
        self.surface_pressure_input.setPlaceholderText("敞口容器: 101.3 (标准大气压)")
        self.surface_pressure_input.setValidator(QDoubleValidator(0.1, 22000.0, 6))
        self.surface_pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.surface_pressure_input, row, 1)
        
        self.surface_pressure_combo = QComboBox()
        self.surface_pressure_combo.setStyleSheet(COMBOBOX_STYLE)
        self.surface_pressure_combo.addItems([
            "请选择液面压力",
            "101.3 kPaA - 敞口容器(标准大气压)",
            "98.1 kPaA - 海拔300米",
            "95.0 kPaA - 海拔500米",
            "89.9 kPaA - 海拔1000米",
            "200 kPaA - 低压容器",
            "500 kPaA - 中压容器"
        ])
        self.surface_pressure_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.surface_pressure_combo.currentTextChanged.connect(self.on_surface_pressure_changed)
        input_layout.addWidget(self.surface_pressure_combo, row, 2)
        
        row += 1
        
        # 液体饱和蒸汽压
        vapor_pressure_label = QLabel("液体饱和蒸汽压 (kPa):")
        vapor_pressure_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vapor_pressure_label.setStyleSheet(label_style)
        input_layout.addWidget(vapor_pressure_label, row, 0)
        
        self.vapor_pressure_input = QLineEdit()
        self.vapor_pressure_input.setPlaceholderText("例如: 2.34 (水在20°C)")
        self.vapor_pressure_input.setValidator(QDoubleValidator(0.001, 22064.0, 6))
        self.vapor_pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.vapor_pressure_input, row, 1)
        
        self.vapor_pressure_combo = QComboBox()
        self.vapor_pressure_combo.setStyleSheet(COMBOBOX_STYLE)
        self.vapor_pressure_combo.addItems([
            "请选择蒸汽压",
            "0.61 kPa - 水在0°C",
            "1.23 kPa - 水在10°C",
            "2.34 kPa - 水在20°C",
            "4.24 kPa - 水在30°C",
            "7.38 kPa - 水在40°C",
            "12.34 kPa - 水在50°C",
            "19.92 kPa - 水在60°C",
            "31.19 kPa - 水在70°C",
            "47.39 kPa - 水在80°C",
            "70.14 kPa - 水在90°C",
            "101.33 kPa - 水在100°C"
        ])
        self.vapor_pressure_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.vapor_pressure_combo.currentTextChanged.connect(self.on_vapor_pressure_changed)
        input_layout.addWidget(self.vapor_pressure_combo, row, 2)
        
        row += 1
        
        # 吸入液面高度
        static_head_label = QLabel("吸入液面高度 (m):")
        static_head_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        static_head_label.setStyleSheet(label_style)
        input_layout.addWidget(static_head_label, row, 0)
        
        self.static_head_input = QLineEdit()
        self.static_head_input.setPlaceholderText("正值为灌注，负值为抽吸")
        self.static_head_input.setValidator(QDoubleValidator(-20.0, 50.0, 6))
        self.static_head_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.static_head_input, row, 1)
        
        self.static_head_combo = QComboBox()
        self.static_head_combo.setStyleSheet(COMBOBOX_STYLE)
        self.static_head_combo.addItems([
            "请选择吸入方式",
            "正压头 - 灌注吸入",
            "负压头 - 抽吸吸入",
            "零压头 - 水平吸入"
        ])
        self.static_head_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.static_head_combo.currentTextChanged.connect(self.on_static_head_changed)
        input_layout.addWidget(self.static_head_combo, row, 2)
        
        row += 1
        
        # 吸入管路损失
        friction_loss_label = QLabel("吸入管路损失 (m):")
        friction_loss_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        friction_loss_label.setStyleSheet(label_style)
        input_layout.addWidget(friction_loss_label, row, 0)
        
        self.friction_loss_input = QLineEdit()
        self.friction_loss_input.setPlaceholderText("例如: 1.5")
        self.friction_loss_input.setValidator(QDoubleValidator(0.0, 20.0, 6))
        self.friction_loss_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.friction_loss_input, row, 1)
        
        self.friction_loss_combo = QComboBox()
        self.friction_loss_combo.setStyleSheet(COMBOBOX_STYLE)
        self.friction_loss_combo.addItems([
            "请选择管路类型",
            "0.5-1.0 m - 短直管路",
            "1.0-2.0 m - 中等管路",
            "2.0-3.0 m - 长管路",
            "3.0-5.0 m - 复杂管路"
        ])
        self.friction_loss_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.friction_loss_combo.currentTextChanged.connect(self.on_friction_loss_changed)
        input_layout.addWidget(self.friction_loss_combo, row, 2)
        
        row += 1
        
        # 液体密度
        density_label = QLabel("液体密度 (kg/m³):")
        density_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        density_label.setStyleSheet(label_style)
        input_layout.addWidget(density_label, row, 0)
        
        self.density_input = QLineEdit()
        self.density_input.setPlaceholderText("例如: 1000 (水)")
        self.density_input.setValidator(QDoubleValidator(500.0, 2000.0, 6))
        self.density_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.density_input, row, 1)
        
        self.density_combo = QComboBox()
        self.density_combo.setStyleSheet(COMBOBOX_STYLE)
        self.density_combo.addItems([
            "请选择流体",
            "1000 kg/m³ - 水(20°C)",
            "998 kg/m³ - 水(25°C)",
            "983 kg/m³ - 水(60°C)",
            "789 kg/m³ - 乙醇",
            "719 kg/m³ - 汽油", 
            "1261 kg/m³ - 甘油",
            "1025 kg/m³ - 海水",
            "680 kg/m³ - 汽油(轻质)",
            "850 kg/m³ - 柴油"
        ])
        self.density_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.density_combo.currentTextChanged.connect(self.on_density_changed)
        input_layout.addWidget(self.density_combo, row, 2)
        
        row += 1
        
        # NPSHr (可选)
        npshr_label = QLabel("泵必需汽蚀余量NPSHr (m):")
        npshr_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        npshr_label.setStyleSheet(label_style)
        input_layout.addWidget(npshr_label, row, 0)
        
        self.npshr_input = QLineEdit()
        self.npshr_input.setPlaceholderText("可选，来自泵性能曲线")
        self.npshr_input.setValidator(QDoubleValidator(0.1, 20.0, 6))
        self.npshr_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.npshr_input, row, 1)
        
        self.npshr_combo = QComboBox()
        self.npshr_combo.setStyleSheet(COMBOBOX_STYLE)
        self.npshr_combo.addItems([
            "请选择NPSHr",
            "1.0-2.0 m - 低NPSHr泵",
            "2.0-4.0 m - 标准泵",
            "4.0-6.0 m - 高NPSHr泵",
            "6.0-8.0 m - 特殊泵",
            "未知NPSHr"
        ])
        self.npshr_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.npshr_combo.currentTextChanged.connect(self.on_npshr_changed)
        input_layout.addWidget(self.npshr_combo, row, 2)
        
        row += 1
        
        # 安全裕量（泵型选择）
        safety_label = QLabel("安全裕量 (m):")
        safety_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        safety_label.setStyleSheet(label_style)
        input_layout.addWidget(safety_label, row, 0)
        
        self.safety_margin_input = QLineEdit()
        self.safety_margin_input.setPlaceholderText("选择泵型自动填充")
        self.safety_margin_input.setValidator(QDoubleValidator(0.0, 5.0, 6))
        self.safety_margin_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.safety_margin_input, row, 1)
        
        self.safety_margin_combo = QComboBox()
        self.safety_margin_combo.setStyleSheet(COMBOBOX_STYLE)
        self.safety_margin_combo.addItems([
            "请选择泵型获取推荐安全裕量",
            "0.6-1.0 m - 一般离心泵",
            "2.1 m - 锅炉给水泵/给水循环泵/卧式冷凝器热冷凝液泵",
            "2.1 m - 减压塔釜液泵",
            "0.3 m - 立式和卧式表面冷凝器热冷凝液泵",
            "0.6 m - 常温常压冷却水泵",
            "0.6 m - 吸入压力<70kPa(表)的泵",
            "0.6 m - 多级泵和双吸叶轮泵",
            "0.6 m - 自动启动泵",
            "2.1 m - 吸收塔釜液泵/CO2汽提塔等(15.5~205°C)",
            "0.6 m - 将容器架高提高NPSHa的泵",
            "0.3-1.2 m - 输送平衡液体/蒸汽分压下液体的泵",
            "0.6 m - 输送非平衡液体的泵"
        ])
        self.safety_margin_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.safety_margin_combo.currentTextChanged.connect(self.on_safety_margin_changed)
        input_layout.addWidget(self.safety_margin_combo, row, 2)
        
        left_layout.addWidget(input_group)
        
        # 计算按钮
        calculate_btn = QPushButton("计算")
        calculate_btn.setFont(QFont("Arial", 12, QFont.Bold))
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
        calculate_btn.clicked.connect(self.calculate_npsha)
        left_layout.addWidget(calculate_btn)

        # 底部按钮行
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

        left_layout.addStretch()

        # 右侧：结果显示区域 (占1/3宽度)
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        self.svg_widget = QSvgWidget()
        self.svg_widget.setMinimumHeight(220)
        self.svg_widget.setMaximumHeight(280)
        self.svg_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        right_layout.addWidget(self.svg_widget)
        self.svg_widget.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
        
        # 结果显示
        self.result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(self.result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #666;
                border-radius: 6px;
                padding: 8px;
                /* bg via theme */min-height: 500px;
            }
        """)
        result_layout.addWidget(self.result_text)
        
        right_layout.addWidget(self.result_group)
        
        # 将左右两部分添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)  # 左侧占2/3
        main_layout.addWidget(right_widget, 1)  # 右侧占1/3
    
    def on_surface_pressure_changed(self, text):
        """处理液面压力选择变化"""
        if "请选择" in text:
            self.surface_pressure_input.setReadOnly(False)
            self.surface_pressure_input.setPlaceholderText("敞口容器: 101.3 (标准大气压)")
            self.surface_pressure_input.clear()
            return
        self.surface_pressure_input.setReadOnly(True)
        try:
            import re
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                self.surface_pressure_input.setText(f"{float(match.group(1)):.1f}")
        except:
            pass
    
    def on_vapor_pressure_changed(self, text):
        """处理蒸汽压选择变化"""
        if "请选择" in text:
            self.vapor_pressure_input.setReadOnly(False)
            self.vapor_pressure_input.setPlaceholderText("例如: 2.34 (水在20°C)")
            self.vapor_pressure_input.clear()
            return
        self.vapor_pressure_input.setReadOnly(True)
        try:
            import re
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                self.vapor_pressure_input.setText(f"{float(match.group(1)):.2f}")
        except:
            pass
    
    def on_static_head_changed(self, text):
        """处理静压头选择变化"""
        if "请选择" in text:
            self.static_head_input.setPlaceholderText("正值为灌注，负值为抽吸")
            self.static_head_input.clear()
            return
        if "正压头" in text:
            self.static_head_input.setPlaceholderText("正值为灌注")
        elif "负压头" in text:
            self.static_head_input.setPlaceholderText("负值为抽吸")
        else:
            self.static_head_input.setPlaceholderText("零压头")
    
    def on_friction_loss_changed(self, text):
        """处理管路损失选择变化"""
        if "请选择" in text:
            self.friction_loss_input.setReadOnly(False)
            self.friction_loss_input.setPlaceholderText("例如: 1.5")
            self.friction_loss_input.clear()
            return
        self.friction_loss_input.setReadOnly(True)
        try:
            import re
            match = re.search(r'(\d+\.?\d*)-(\d+\.?\d*)', text)
            if match:
                min_val = float(match.group(1))
                max_val = float(match.group(2))
                self.friction_loss_input.setText(f"{(min_val + max_val) / 2:.1f}")
        except:
            pass
    
    def on_density_changed(self, text):
        """处理密度选择变化"""
        if "请选择" in text:
            self.density_input.setReadOnly(False)
            self.density_input.setPlaceholderText("例如: 1000 (水)")
            self.density_input.clear()
            return
        self.density_input.setReadOnly(True)
        try:
            import re
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                self.density_input.setText(f"{float(match.group(1)):.0f}")
        except:
            pass
    
    def on_npshr_changed(self, text):
        """处理NPSHr选择变化"""
        if "请选择" in text:
            self.npshr_input.clear()
            self.npshr_input.setPlaceholderText("可选，来自泵性能曲线")
            return
        if "未知" in text:
            self.npshr_input.clear()
            self.npshr_input.setPlaceholderText("不输入NPSHr")
        else:
            try:
                import re
                match = re.search(r'(\d+\.?\d*)-(\d+\.?\d*)', text)
                if match:
                    min_val = float(match.group(1))
                    max_val = float(match.group(2))
                    self.npshr_input.setText(f"{(min_val + max_val) / 2:.1f}")
            except:
                pass
    
    def on_safety_margin_changed(self, text):
        """处理安全裕量选择变化"""
        if "请选择" in text:
            self.safety_margin_input.clear()
            self.safety_margin_input.setPlaceholderText("选择泵型自动填充")
            return
        self.safety_margin_input.setReadOnly(True)
        try:
            import re
            match_range = re.search(r'(\d+\.?\d*)-(\d+\.?\d*)', text)
            if match_range:
                min_v = float(match_range.group(1))
                max_v = float(match_range.group(2))
                self.safety_margin_input.setText(f"{(min_v + max_v) / 2:.1f}")
            else:
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    self.safety_margin_input.setText(f"{float(match.group(1)):.1f}")
        except:
            pass
    
    def calculate_npsha(self):
        """计算NPSHa"""
        try:
            # 获取输入值
            surface_pressure = float(self.surface_pressure_input.text() or 0)
            vapor_pressure = float(self.vapor_pressure_input.text() or 0)
            static_head = float(self.static_head_input.text() or 0)
            friction_loss = float(self.friction_loss_input.text() or 0)
            density = float(self.density_input.text() or 0)
            npshr = self.npshr_input.text()
            npshr_value = float(npshr) if npshr else None
            safety_margin_text = self.safety_margin_input.text()
            safety_margin = float(safety_margin_text) if safety_margin_text else None
            
            # 验证输入
            if surface_pressure <= 0 or vapor_pressure < 0 or friction_loss < 0 or density <= 0:
                QMessageBox.warning(self, "输入错误", "请填写有效的参数（液面压力和密度必须大于0）")
                return
            
            # ── NPSHa 公式 ──
            # NPSHa = (P_surface - P_vapor) / (ρ·g) + H_static - H_friction
            g = G
            
            surface_head = (surface_pressure * 1000) / (density * g)
            vapor_head = (vapor_pressure * 1000) / (density * g)
            
            npsha = surface_head - vapor_head + static_head - friction_loss
            
            # ── 结果展示 ──
            result = f"""═══════════════════════════════════════
                         输入参数
═══════════════════════════════════════

• 液面压力: {surface_pressure} kPaA
• 液体饱和蒸汽压: {vapor_pressure} kPa
• 流体密度: {density} kg/m³
• 泵安装高度: {static_head} m
• 泵入口管路损失: {friction_loss} m
• 安全裕量: {f"{safety_margin} m" if safety_margin else "未指定"}
{f"• 泵必需汽蚀余量 NPSHr: {npshr_value} m" if npshr_value else "• 泵必需汽蚀余量 NPSHr: 未指定"}

═══════════════════════════════════════
                        计算结果
═══════════════════════════════════════

中间计算:
• 液面压力头: {surface_head:.3f} m
• 蒸汽压头:   {vapor_head:.3f} m

最终结果:
• 可用汽蚀余量 NPSHa = {npsha:.3f} m"""
            
            if npshr_value:
                raw_margin = npsha - npshr_value
                result += f"""
• 泵必需汽蚀余量 NPSHr: {npshr_value} m
• NPSHa - NPSHr = {raw_margin:.3f} m"""

                if safety_margin:
                    effective_margin = raw_margin - safety_margin
                    result += f"""
• 指定安全裕量: {safety_margin} m
• 扣除裕量后余量: {effective_margin:.3f} m

═══════════════════════════════════════
                      安全评估
═══════════════════════════════════════
"""
                    if effective_margin >= 0.5:
                        result += " 优秀 - 汽蚀余量非常充足，满足设计要求"
                    elif effective_margin >= 0:
                        result += " 合格 - 汽蚀余量满足基本要求"
                    elif effective_margin >= -0.3:
                        result += " 偏紧 - 余量偏小，建议增大安装高度或减小管路损失"
                    else:
                        result += " 不足 - 汽蚀余量不足，可能发生汽蚀！需改进设计"
                    
                    result += f"""
• NPSHa / (NPSHr + 裕量) = {npsha/(npshr_value + safety_margin):.2f}"""
                else:
                    result += f"""

═══════════════════════════════════════
                      安全评估
═══════════════════════════════════════
"""
                    if raw_margin >= 1.0:
                        result += " 优秀 - 汽蚀余量非常充足，泵运行安全"
                    elif raw_margin >= 0.5:
                        result += " 良好 - 汽蚀余量充足，泵运行安全"
                    elif raw_margin >= 0.3:
                        result += " 注意 - 汽蚀余量基本满足，建议监控"
                    elif raw_margin >= 0:
                        result += " 警告 - 汽蚀余量刚好满足，风险较高"
                    else:
                        result += " 危险 - 汽蚀余量不足，可能发生汽蚀"
                    
                    result += f"\n• NPSHa / NPSHr = {npsha/npshr_value:.2f}"
            else:
                result += """
注意: 未输入NPSHr值，无法进行安全性评估。
请参考泵的性能曲线获取NPSHr值。"""

                if safety_margin:
                    result += f"""
参考信息（基于安全裕量 {safety_margin} m）:
• NPSHa 可用于克服 NPSHr + 安全裕量"""

                result += """
一般要求:
• NPSHa ≥ NPSHr + 安全裕量
• 敞口容器推荐裕量 0.6~1.0 m
• 锅炉给水泵/釜液泵推荐裕量 2.1 m"""

            result += f"""

═══════════════════════════════════════
                        计算公式
═══════════════════════════════════════

NPSHa = (P_s - P_v) / (ρ·g) + H_inst - H_f

其中:
P_s    = {surface_pressure} kPaA (液面绝对压力)
P_v    = {vapor_pressure} kPa (饱和蒸汽压)
ρ      = {density} kg/m³ (液体密度)
g      = G m/s² (重力加速度)
H_inst = {static_head} m (泵安装高度)
H_f    = {friction_loss} m (吸入管路损失)

详细计算:
({surface_pressure}×1000/({density}×G)) - ({vapor_pressure}×1000/({density}×G)) + {static_head} - {friction_loss}
= {surface_head:.3f} - {vapor_head:.3f} + {static_head} - {friction_loss}
= {npsha:.3f} m

═══════════════════════════════════════
                        应用说明
═══════════════════════════════════════

• NPSHa ≥ NPSHr + 安全裕量 才能避免汽蚀
• 汽蚀会导致泵性能下降、振动和损坏
• 计算结果仅供参考，实际应用请考虑安全系数
• 高温液体饱和蒸汽压较高，对NPSHa影响显著
• 密闭容器液面压力可能远大于大气压"""
            
            self.result_text.setText(result)

            self._last_npsha = round(npsha, 2)
            self._last_surface_pressure = surface_pressure
            self._last_density = density
            self._update_svg_diagram()
            
        except ValueError as e:
            QMessageBox.critical(self, "计算错误", f"参数输入格式错误: {str(e)}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "密度不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    # ───────────────── 泵吸入安装 SVG 示意图 ─────────────────
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        return svg_text(x, y, text, size, color, bold, center)

    def _generate_pump_suction_svg(self, **kw):
        """生成泵吸入安装示意图：容器 → 管路 → 泵"""
        w, h = 380, 280
        p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']

        # ── 容器（左侧） ──
        tank_x, tank_y, tank_w, tank_h = 40, 35, 85, 115
        p.append(f'<rect x="{tank_x}" y="{tank_y}" width="{tank_w}" height="{tank_h}" '
                 f'fill="#e8edf2" stroke="#4a6fa5" stroke-width="2" rx="3"/>')
        # 容器内液位（下部蓝色填充）
        liquid_h = 88
        liquid_y = tank_y + tank_h - liquid_h
        p.append(f'<rect x="{tank_x+2}" y="{liquid_y}" width="{tank_w-4}" height="{liquid_h-2}" '
                 f'fill="#a8d8ea" rx="1"/>')
        # 液面虚线
        p.append(f'<line x1="{tank_x}" y1="{liquid_y}" x2="{tank_x+tank_w}" y2="{liquid_y}" '
                 f'stroke="#3498db" stroke-width="1.5" stroke-dasharray="5,3"/>')
        # 容器标签
        p.append(self._text(tank_x + tank_w/2, tank_y - 12, "供液容器", size=9, color="#4a6fa5", bold=True))
        # 液面压力标签
        ps_val = kw.get("surface_pressure", "")
        ps_text = f"P_s={ps_val}" if ps_val else "P_s"
        p.append(self._text(tank_x + tank_w/2, liquid_y - 10, ps_text, size=9, color="#3498db", bold=True))

        # ── 管路 ──
        pipe_top = tank_y + tank_h  # 容器底出口
        pipe_color = "#7f8c8d"
        pipe_w = 5
        # 竖管: 容器底 → 向下
        mid_x = tank_x + tank_w/2
        elbow_y = pipe_top + 45
        p.append(f'<line x1="{mid_x}" y1="{pipe_top}" x2="{mid_x}" y2="{elbow_y}" '
                 f'stroke="{pipe_color}" stroke-width="{pipe_w}"/>')
        # 横管: 容器底 → 泵侧
        pump_x = 280
        p.append(f'<line x1="{mid_x}" y1="{elbow_y}" x2="{pump_x}" y2="{elbow_y}" '
                 f'stroke="{pipe_color}" stroke-width="{pipe_w}"/>')
        # 竖管: 弯头 → 泵入口
        pump_inlet_y = 210
        p.append(f'<line x1="{pump_x}" y1="{elbow_y}" x2="{pump_x}" y2="{pump_inlet_y}" '
                 f'stroke="{pipe_color}" stroke-width="{pipe_w}"/>')

        # 管路损失标注
        hf_val = kw.get("friction_loss", "")
        hf_text = f"h_f={hf_val}m" if hf_val else "h_f"
        p.append(self._text(mid_x + (pump_x - mid_x)/2, elbow_y - 8, hf_text, size=9, color="#e74c3c", bold=True))

        # ── 泵 ──
        pump_r = 20
        pump_cy = pump_inlet_y + pump_r + 5
        p.append(f'<circle cx="{pump_x}" cy="{pump_cy}" r="{pump_r}" '
                 f'fill="#ef5350" stroke="#c0392b" stroke-width="2"/>')
        p.append(self._text(pump_x, pump_cy, "泵", size=10, color="white", bold=True))
        # 排出管
        discharge_y = pump_cy + pump_r
        p.append(f'<line x1="{pump_x}" y1="{discharge_y}" x2="{pump_x}" y2="{h-15}" '
                 f'stroke="{pipe_color}" stroke-width="{pipe_w}" marker-end="url(#arrow_out)"/>')

        # ── 安装高度标注（液面到泵中心线） ──
        hst_x = tank_x + tank_w + 16
        hst_y1 = liquid_y
        hst_y2 = pump_cy
        p.append(f'<line x1="{hst_x}" y1="{hst_y1}" x2="{hst_x}" y2="{hst_y2}" '
                 f'stroke="#e67e22" stroke-width="1" stroke-dasharray="5,3"/>')
        p.append(f'<line x1="{hst_x-5}" y1="{hst_y1}" x2="{hst_x+5}" y2="{hst_y1}" '
                 f'stroke="#e67e22" stroke-width="1.5"/>')
        p.append(f'<line x1="{hst_x-5}" y1="{hst_y2}" x2="{hst_x+5}" y2="{hst_y2}" '
                 f'stroke="#e67e22" stroke-width="1.5"/>')
        # 泵安装高度箭头
        p.append(f'<polygon points="{hst_x+2},{hst_y1+6} {hst_x-2},{hst_y1+6} {hst_x},{hst_y1}" '
                 f'fill="#e67e22"/>')
        p.append(f'<polygon points="{hst_x+2},{hst_y2-6} {hst_x-2},{hst_y2-6} {hst_x},{hst_y2}" '
                 f'fill="#e67e22"/>')

        hst_val = kw.get("static_head", "")
        hst_text = f"H_inst={hst_val}m" if hst_val else "H_inst"
        hst_mid = (hst_y1 + hst_y2) / 2
        p.append(self._text(hst_x + 18, hst_mid, hst_text, size=10, color="#e67e22", bold=True, center=False))

        # ── 图例和标题 ──
        p.append(self._text(w/2, 12, "NPSHa 泵吸入安装示意图", size=10, color="#4a6fa5", bold=True))

        # 底部结果
        npsha_val = kw.get("npsha", "")
        if npsha_val:
            p.append(self._text(10, h-10, f"NPSHa = {npsha_val} m", size=10, color="#27ae60", bold=True, center=False))

        # 图例
        p.append(self._text(w - 80, h - 10, "h_f: 管路损失", size=8, color="#e74c3c", center=False))

        p.append('<defs>'
                 '<marker id="arrow_out" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto">'
                 '<path d="M0,0 L8,4 L0,8 Z" fill="#7f8c8d"/>'
                 '</marker>'
                 '</defs></svg>')
        return "".join(p)

    def _update_svg_diagram(self):
        try:
            kw = {}
            # 读取当前输入值用于SVG标注
            try:
                val = self.surface_pressure_input.text().strip()
                if val:
                    kw["surface_pressure"] = val
            except:
                pass
            try:
                val = self.static_head_input.text().strip()
                if val:
                    kw["static_head"] = val
            except:
                pass
            try:
                val = self.friction_loss_input.text().strip()
                if val:
                    kw["friction_loss"] = val
            except:
                pass
            if hasattr(self, "_last_npsha"):
                kw["npsha"] = str(self._last_npsha)
            s = self._generate_pump_suction_svg(**kw)
            self.svg_widget.load(s.encode("utf-8"))
        except:
            pass

    def clear_inputs(self):
        """清空所有输入"""
        self.surface_pressure_combo.setCurrentIndex(0)
        self.vapor_pressure_combo.setCurrentIndex(0)
        self.static_head_combo.setCurrentIndex(0)
        self.friction_loss_combo.setCurrentIndex(0)
        self.density_combo.setCurrentIndex(0)
        self.npshr_combo.setCurrentIndex(0)
        self.safety_margin_combo.setCurrentIndex(0)
        self.surface_pressure_input.clear()
        self.vapor_pressure_input.clear()
        self.static_head_input.clear()
        self.friction_loss_input.clear()
        self.density_input.clear()
        self.npshr_input.clear()
        self.safety_margin_input.clear()
        self.result_text.clear()

    def _get_history_data(self):
        """提供历史记录数据"""
        surface_pressure = float(self.surface_pressure_input.text() or 0)
        vapor_pressure = float(self.vapor_pressure_input.text() or 0)
        static_head = float(self.static_head_input.text() or 0)
        friction_loss = float(self.friction_loss_input.text() or 0)
        density = float(self.density_input.text() or 0)
        npshr_text = self.npshr_input.text()
        npshr_value = float(npshr_text) if npshr_text else None
        safety_margin_text = self.safety_margin_input.text()
        safety_margin = float(safety_margin_text) if safety_margin_text else None

        inputs = {
            "液面压力_kPaA": surface_pressure,
            "饱和蒸汽压_kPa": vapor_pressure,
            "泵安装高度_m": static_head,
            "管路损失_m": friction_loss,
            "液体密度_kg_m3": density
        }
        if npshr_value is not None:
            inputs["NPSHr_m"] = npshr_value
        if safety_margin is not None:
            inputs["安全裕量_m"] = safety_margin

        outputs = {}
        try:
            g = G
            surface_head = (surface_pressure * 1000) / (density * g)
            vapor_head = (vapor_pressure * 1000) / (density * g)
            npsha = surface_head - vapor_head + static_head - friction_loss
            outputs = {
                "液面压力头_m": round(surface_head, 3),
                "蒸汽压头_m": round(vapor_head, 3),
                "NPSHa_m": round(npsha, 3)
            }
            if npshr_value is not None:
                raw_margin = npsha - npshr_value
                outputs["NPSHa减NPSHr_m"] = round(raw_margin, 3)
                outputs["NPSHa_NPSHr"] = round(npsha / npshr_value, 2) if npshr_value > 0 else 0
                if safety_margin is not None:
                    outputs["扣除裕量后余量_m"] = round(raw_margin - safety_margin, 3)
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        """获取项目信息"""
        return {"calculator": "NPSHaCalculator", "name": "NPSHa汽蚀余量计算"}

    def generate_report(self):
        """生成报告"""
        return self.result_text.toPlainText()

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "NPSHaCalculator")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "NPSHaCalculator")