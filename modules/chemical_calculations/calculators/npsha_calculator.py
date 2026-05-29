from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QGridLayout, QMessageBox,
    QScrollArea, QSizePolicy, QFileDialog,
)
from PySide6.QtGui import QFont, QDoubleValidator
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt
import os
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
class NPSHaCalculator(QWidget):
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
        self._wheel_blocker = ComboBoxWheelBlocker(self)
        for combo in self.findChildren(QComboBox):
            combo.installEventFilter(self._wheel_blocker)

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
        
        # 大气压力
        atm_pressure_label = QLabel("大气压力 (kPa):")
        atm_pressure_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        atm_pressure_label.setStyleSheet(label_style)
        input_layout.addWidget(atm_pressure_label, row, 0)
        
        self.atm_pressure_input = QLineEdit()
        self.atm_pressure_input.setPlaceholderText("例如: 101.3 (标准大气压)")
        self.atm_pressure_input.setValidator(QDoubleValidator(80.0, 110.0, 6))
        self.atm_pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.atm_pressure_input, row, 1)
        
        self.atm_pressure_combo = QComboBox()
        self.atm_pressure_combo.setStyleSheet(COMBOBOX_STYLE)
        self.atm_pressure_combo.addItems([
            "101.3 kPa - 标准大气压",
            "98.1 kPa - 海拔300米",
            "95.0 kPa - 海拔500米", 
            "89.9 kPa - 海拔1000米",
            "自定义大气压力"
        ])
        self.atm_pressure_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.atm_pressure_combo.currentTextChanged.connect(self.on_atm_pressure_changed)
        input_layout.addWidget(self.atm_pressure_combo, row, 2)
        
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
            "101.33 kPa - 水在100°C",
            "自定义蒸汽压"
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
            "0.5-1.0 m - 短直管路",
            "1.0-2.0 m - 中等管路",
            "2.0-3.0 m - 长管路",
            "3.0-5.0 m - 复杂管路",
            "自定义管路损失"
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
            "1000 kg/m³ - 水(20°C)",
            "998 kg/m³ - 水(25°C)",
            "983 kg/m³ - 水(60°C)",
            "789 kg/m³ - 乙醇",
            "719 kg/m³ - 汽油", 
            "1261 kg/m³ - 甘油",
            "1025 kg/m³ - 海水",
            "680 kg/m³ - 汽油(轻质)",
            "850 kg/m³ - 柴油",
            "自定义密度"
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
            "1.0-2.0 m - 低NPSHr泵",
            "2.0-4.0 m - 标准泵",
            "4.0-6.0 m - 高NPSHr泵",
            "6.0-8.0 m - 特殊泵",
            "未知NPSHr"
        ])
        self.npshr_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.npshr_combo.currentTextChanged.connect(self.on_npshr_changed)
        input_layout.addWidget(self.npshr_combo, row, 2)
        
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
        self.download_txt_btn = QPushButton("下载计算书(TXT)")
        self.download_txt_btn.clicked.connect(self.download_txt_report)
        self.download_txt_btn.setMinimumHeight(50)
        self.download_txt_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_txt_btn.setStyleSheet("""
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
        bottom_layout.addWidget(self.download_txt_btn)
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
    
    def on_atm_pressure_changed(self, text):
        """处理大气压力选择变化"""
        if "自定义" in text:
            self.atm_pressure_input.setReadOnly(False)
            self.atm_pressure_input.setPlaceholderText("输入自定义大气压力")
            self.atm_pressure_input.clear()
        else:
            self.atm_pressure_input.setReadOnly(True)
            try:
                # 从文本中提取数字
                import re
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    pressure_value = float(match.group(1))
                    self.atm_pressure_input.setText(f"{pressure_value:.1f}")
            except:
                pass
    
    def on_vapor_pressure_changed(self, text):
        """处理蒸汽压选择变化"""
        if "自定义" in text:
            self.vapor_pressure_input.setReadOnly(False)
            self.vapor_pressure_input.setPlaceholderText("输入自定义蒸汽压")
            self.vapor_pressure_input.clear()
        else:
            self.vapor_pressure_input.setReadOnly(True)
            try:
                # 从文本中提取数字
                import re
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    vapor_value = float(match.group(1))
                    self.vapor_pressure_input.setText(f"{vapor_value:.2f}")
            except:
                pass
    
    def on_static_head_changed(self, text):
        """处理静压头选择变化"""
        if "正压头" in text:
            self.static_head_input.setPlaceholderText("正值为灌注")
        elif "负压头" in text:
            self.static_head_input.setPlaceholderText("负值为抽吸")
        else:
            self.static_head_input.setPlaceholderText("零压头")
    
    def on_friction_loss_changed(self, text):
        """处理管路损失选择变化"""
        if "自定义" in text:
            self.friction_loss_input.setReadOnly(False)
            self.friction_loss_input.setPlaceholderText("输入自定义管路损失")
            self.friction_loss_input.clear()
        else:
            self.friction_loss_input.setReadOnly(True)
            try:
                # 从文本中提取数字范围
                import re
                match = re.search(r'(\d+\.?\d*)-(\d+\.?\d*)', text)
                if match:
                    min_val = float(match.group(1))
                    max_val = float(match.group(2))
                    avg_val = (min_val + max_val) / 2
                    self.friction_loss_input.setText(f"{avg_val:.1f}")
            except:
                pass
    
    def on_density_changed(self, text):
        """处理密度选择变化"""
        if "自定义" in text:
            self.density_input.setReadOnly(False)
            self.density_input.setPlaceholderText("输入自定义密度")
            self.density_input.clear()
        else:
            self.density_input.setReadOnly(True)
            try:
                # 从文本中提取数字
                import re
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    density_value = float(match.group(1))
                    self.density_input.setText(f"{density_value:.0f}")
            except:
                pass
    
    def on_npshr_changed(self, text):
        """处理NPSHr选择变化"""
        if "未知" in text:
            self.npshr_input.clear()
            self.npshr_input.setPlaceholderText("不输入NPSHr")
        else:
            try:
                # 从文本中提取数字范围
                import re
                match = re.search(r'(\d+\.?\d*)-(\d+\.?\d*)', text)
                if match:
                    min_val = float(match.group(1))
                    max_val = float(match.group(2))
                    avg_val = (min_val + max_val) / 2
                    self.npshr_input.setText(f"{avg_val:.1f}")
            except:
                pass
    
    def calculate_npsha(self):
        """计算NPSHa"""
        try:
            # 获取输入值
            atm_pressure = float(self.atm_pressure_input.text() or 0)
            vapor_pressure = float(self.vapor_pressure_input.text() or 0)
            static_head = float(self.static_head_input.text() or 0)
            friction_loss = float(self.friction_loss_input.text() or 0)
            density = float(self.density_input.text() or 0)
            npshr = self.npshr_input.text()
            npshr_value = float(npshr) if npshr else None
            
            # 验证输入
            if atm_pressure <= 0 or vapor_pressure < 0 or friction_loss < 0 or density <= 0:
                QMessageBox.warning(self, "输入错误", "请填写有效的参数（大气压和密度必须大于0）")
                return
            
            # 计算NPSHa
            # NPSHa = (大气压头 + 静压头) - 蒸汽压头 - 损失压头
            # 压头 = 压力 / (密度 * 重力加速度)
            g = 9.81  # m/s²
            
            atm_head = (atm_pressure * 1000) / (density * g)  # 转换为Pa后计算压头
            vapor_head = (vapor_pressure * 1000) / (density * g)
            
            npsha = atm_head + static_head - vapor_head - friction_loss
            
            # 显示结果 - 使用格式化的输出
            result = f"""═══════════════════════════════════════════════════
                         输入参数
═══════════════════════════════════════════════════

• 大气压力: {atm_pressure} kPa
• 液体饱和蒸汽压: {vapor_pressure} kPa
• 吸入液面高度: {static_head} m
• 吸入管路损失: {friction_loss} m
• 液体密度: {density} kg/m³
{f"• 泵必需汽蚀余量 NPSHr: {npshr_value} m" if npshr_value else "• 泵必需汽蚀余量 NPSHr: 未指定"}

═══════════════════════════════════════════════════
                        计算结果
═══════════════════════════════════════════════════

中间计算:
• 大气压头: {atm_head:.3f} m
• 蒸汽压头: {vapor_head:.3f} m

最终结果:
• 可用汽蚀余量 NPSHa = {npsha:.3f} m

汽蚀余量分析:"""
            
            if npshr_value:
                safety_margin = npsha - npshr_value
                result += f"""
• 泵必需汽蚀余量 NPSHr: {npshr_value} m
• 安全余量: {safety_margin:.3f} m

安全评估:"""
                
                if safety_margin >= 1.0:
                    result += "\n 优秀 - 汽蚀余量非常充足，泵运行安全"
                elif safety_margin >= 0.5:
                    result += "\n 良好 - 汽蚀余量充足，泵运行安全"
                elif safety_margin >= 0.3:
                    result += "\n️ 注意 - 汽蚀余量基本满足，建议监控"
                elif safety_margin >= 0:
                    result += "\n️ 警告 - 汽蚀余量刚好满足，风险较高"
                else:
                    result += "\n 危险 - 汽蚀余量不足，可能发生汽蚀"
                    
                result += f"\n• NPSHa/NPSHr 比值: {npsha/npshr_value:.2f}"
            else:
                result += """
注意: 未输入NPSHr值，无法进行安全性评估。
请参考泵的性能曲线获取NPSHr值。

一般要求:
• NPSHa ≥ NPSHr + 0.5 m (最小安全余量)
• NPSHa ≥ NPSHr + 1.0 m (推荐安全余量)
• 对于易汽化液体，建议更大的安全余量"""

            result += f"""

═══════════════════════════════════════════════════
                        计算公式
═══════════════════════════════════════════════════

NPSHa = (P_atm / (ρ·g)) + H_static - (P_vapor / (ρ·g)) - H_friction

其中:
P_atm = {atm_pressure} kPa (大气压力)
P_vapor = {vapor_pressure} kPa (饱和蒸汽压)
ρ = {density} kg/m³ (液体密度)
g = 9.81 m/s² (重力加速度)
H_static = {static_head} m (静压头)
H_friction = {friction_loss} m (摩擦损失)

详细计算:
({atm_pressure}×1000 / ({density}×9.81)) + {static_head} - ({vapor_pressure}×1000 / ({density}×9.81)) - {friction_loss}
= {atm_head:.3f} + {static_head} - {vapor_head:.3f} - {friction_loss}
= {npsha:.3f} m

═══════════════════════════════════════════════════
                        应用说明
═══════════════════════════════════════════════════

• NPSHa必须大于NPSHr才能避免汽蚀
• 汽蚀会导致泵性能下降、振动和损坏
• 计算结果仅供参考，实际应用请考虑安全系数
• 对于高温液体，饱和蒸汽压对NPSHa影响显著"""
            
            self.result_text.setText(result)

            self._last_npsha = round(npsha, 2)
            self._last_atm_pressure = atm_pressure
            self._last_density = density
            self._update_svg_diagram()
            
        except ValueError as e:
            QMessageBox.critical(self, "计算错误", f"参数输入格式错误: {str(e)}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "密度不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    # ───────────────── 管道 SVG 示意图 ─────────────────
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        e = 'font-weight="bold"' if bold else ""
        a = 'text-anchor="middle"' if center else ""
        return f'<text x="{x}" y="{y}" {a} font-size="{size}" fill="{color}" {e}>{text}</text>'

    def _generate_pipe_svg(self, **kw):
        w, h = 360, 260
        p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']
        cx, cy, pw, ph = w/2, h/2-10, 260, 60
        py = cy - 30
        d = kw.get("diameter", "?")
        f_val = kw.get("flow", "")
        v = kw.get("velocity", "")
        p.append(f'<rect x="{cx-pw/2}" y="{py}" width="{pw}" height="{ph}" fill="#e8edf2" stroke="#4a6fa5" stroke-width="2" rx="6"/>')
        p.append(f'<rect x="{cx-pw/2+15}" y="{py+10}" width="{pw-30}" height="{ph-20}" fill="#dce4ec" stroke="#7f8c8d" stroke-width="1" rx="3"/>')
        p.append(f'<line x1="{cx-90}" y1="{cy}" x2="{cx+90}" y2="{cy}" stroke="#3498db" stroke-width="2.5" marker-end="url(#arrow)"/>')
        v_text = f"{v} m/s" if v else "? m/s"
        p.append(self._text(cx, cy-10, v_text, size=10, color="#3498db", bold=True))
        d_text = f"DN {d} mm" if d and d != "?" else "DN ?"
        p.append(self._text(cx, py+ph+35, d_text, size=10, color="#555"))
        info_y = h - 14
        if f_val:
            p.append(self._text(40, info_y, f"流量: {f_val}", size=10, color="#444", center=False))
        p.append(self._text(cx, 12, "管路示意", size=10, color="#4a6fa5", bold=True))
        p.append('<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#3498db"/></marker></defs></svg>')
        return "".join(p)

    def _update_svg_diagram(self):
        try:
            kw = {}
            if hasattr(self, "diameter_combo"):
                t = self.diameter_combo.currentText()
                kw["diameter"] = t.split("mm")[0].strip() if "mm" in t else t
            for attr in ["flow_input", "velocity_input", "flow_rate_input"]:
                if hasattr(self, attr):
                    try:
                        val = getattr(self, attr).text().strip()
                        if val: kw[attr.replace("_input", "").replace("_rate", "")] = val
                    except: pass
            s = self._generate_pipe_svg(**kw)
            self.svg_widget.load(s.encode("utf-8"))
        except: pass

    def clear_inputs(self):
        """清空所有输入"""
        self.atm_pressure_combo.setCurrentIndex(0)
        self.vapor_pressure_combo.setCurrentIndex(0)
        self.static_head_combo.setCurrentIndex(0)
        self.friction_loss_combo.setCurrentIndex(0)
        self.density_combo.setCurrentIndex(0)
        self.npshr_combo.setCurrentIndex(0)
        self.atm_pressure_input.clear()
        self.vapor_pressure_input.clear()
        self.static_head_input.clear()
        self.friction_loss_input.clear()
        self.density_input.clear()
        self.npshr_input.clear()
        self.result_text.clear()

    def _get_history_data(self):
        """提供历史记录数据"""
        atm_pressure = float(self.atm_pressure_input.text() or 0)
        vapor_pressure = float(self.vapor_pressure_input.text() or 0)
        static_head = float(self.static_head_input.text() or 0)
        friction_loss = float(self.friction_loss_input.text() or 0)
        density = float(self.density_input.text() or 0)
        npshr_text = self.npshr_input.text()
        npshr_value = float(npshr_text) if npshr_text else None

        inputs = {
            "大气压力_kPa": atm_pressure,
            "饱和蒸汽压_kPa": vapor_pressure,
            "静压头_m": static_head,
            "摩擦损失_m": friction_loss,
            "液体密度_kg_m3": density
        }
        if npshr_value is not None:
            inputs["NPSHr_m"] = npshr_value

        outputs = {}
        try:
            g = 9.81
            atm_head = (atm_pressure * 1000) / (density * g)
            vapor_head = (vapor_pressure * 1000) / (density * g)
            npsha = atm_head + static_head - vapor_head - friction_loss
            outputs = {
                "大气压头_m": round(atm_head, 3),
                "蒸汽压头_m": round(vapor_head, 3),
                "NPSHa_m": round(npsha, 3)
            }
            if npshr_value is not None:
                safety_margin = npsha - npshr_value
                outputs["安全余量_m"] = round(safety_margin, 3)
                outputs["NPSHa_NPSHr"] = round(npsha / npshr_value, 2) if npshr_value > 0 else 0
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        """获取项目信息"""
        return {"calculator": "NPSHaCalculator", "name": "NPSHa汽蚀余量计算"}

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
            self, "保存TXT报告", "NPSHa计算报告.txt", "文本文件 (*.txt)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "成功", f"报告已保存：\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败：{e}")

    def download_pdf_report(self):
        """生成PDF报告"""
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先计算，再下载PDF。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存PDF报告", "NPSHa计算报告.pdf", "PDF文件 (*.pdf)"
        )
        if not path:
            return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            font_paths = [
                r"C:\Windows\Fonts\simhei.ttf",
                r"C:\Windows\Fonts\msyh.ttc",
                r"C:\Windows\Fonts\simsun.ttc",
            ]
            font_name = "SimHei"
            for fp in font_paths:
                if os.path.exists(fp):
                    pdfmetrics.registerFont(TTFont(font_name, fp))
                    break
            c = canvas.Canvas(path, pagesize=A4)
            width, height = A4
            c.setFont(font_name, 11)
            y = height - 50
            for line in content.split("\n"):
                if y < 50:
                    c.showPage()
                    c.setFont(font_name, 11)
                    y = height - 50
                c.drawString(40, y, line)
                y -= 18
            c.save()
            QMessageBox.information(self, "成功", f"PDF已保存：\n{path}")
        except ImportError:
            txt_path = path.replace(".pdf", ".txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(content)
            QMessageBox.information(
                self, "提示",
                f"未安装reportlab，已保存为TXT格式：\n{txt_path}\n\n可通过 pip install reportlab 安装PDF支持。"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"PDF生成失败：{e}")