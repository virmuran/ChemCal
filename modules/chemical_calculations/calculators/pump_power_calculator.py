"""
离心泵功率计算器
遵循统一UI规范改造
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QGridLayout, QMessageBox,
    QScrollArea, QSizePolicy,
)
from PySide6.QtGui import QDoubleValidator
from PySide6.QtCore import Qt
import re
from datetime import datetime


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import G
from utils.docx_utils import ReportExporter
# DOCX 报告导出

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

class CentrifugalPumpCalculator(CalculatorBase):
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
        self._pump_type = None
        self.setup_ui()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None
    
    # ── 泵型效率数据库 ──
    # 每型独立分档：(流量上限 m³/h, 效率)，依 GB/T 5656 及泵行业经验值
    PUMP_EFFICIENCY = {
        "IS 单级单吸":  [(50, 0.55), (150, 0.70), (300, 0.78), (float("inf"), 0.84)],
        "S/SH 单级双吸": [(200, 0.65), (800, 0.75), (2000, 0.82), (float("inf"), 0.87)],
        "D/DG 多级":   [(50, 0.50), (150, 0.63), (300, 0.72), (float("inf"), 0.78)],
        "IH 化工流程": [(50, 0.50), (150, 0.62), (300, 0.70), (float("inf"), 0.76)],
        "AY 油泵":     [(50, 0.48), (150, 0.60), (300, 0.68), (float("inf"), 0.75)],
    }

    def _mk_label(self, text):
        """统一右对齐加粗标签"""
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return lbl

    def _on_pump_type_changed(self, text):
        """泵型变化→自动估算泵效率（效率下拉未选择时）"""
        for key in self.PUMP_EFFICIENCY:
            if text.startswith(key):
                self._pump_type = key
                self._refresh_auto_efficiency()
                return
        self._pump_type = None

    def _refresh_auto_efficiency(self):
        """泵型已选且效率下拉未选择时，按当前流量刷新估算效率"""
        if not getattr(self, "_pump_type", None):
            return
        if self.efficiency_combo.currentIndex() != 0:
            return  # 用户已从下拉选择/自定义效率，不打扰
        try:
            q = float(self.flow_input.text() or 0)
        except ValueError:
            return
        if q <= 0:
            return
        est = self._estimate_pump_efficiency(self._pump_type, q)
        if est:
            self.efficiency_input.setText(f"{est * 100:.0f}")

    def _on_drive_changed(self, text):
        """传动方式变化→更新传动效率"""
        import re
        m = re.search(r"η=([\d.]+)", text)
        if m:
            self.drive_eff_label.setText(f"ηd={m.group(1)}")
    
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
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 顶部说明文字
        description = QLabel(
            "依据 GB/T 5656 离心泵技术条件，计算轴功率、电机功率和配套功率。"
            "含泵型效率数据库，支持直联/皮带/齿轮传动选型。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # ===== 泵型选择 =====
        pump_group = CalculatorBase.make_group_box("泵型与传动")
        pump_layout = QGridLayout(pump_group)
        pump_layout.setVerticalSpacing(8)
        pump_layout.setHorizontalSpacing(10)
        pump_layout.setColumnStretch(0, 4)
        pump_layout.setColumnStretch(1, 8)
        pump_layout.setColumnStretch(2, 5)

        prow = 0
        # 泵类型
        pump_layout.addWidget(self._mk_label("泵类型:"), prow, 0)
        self.pump_type_combo = QComboBox()
        self.pump_type_combo.setStyleSheet(COMBOBOX_STYLE)
        self.pump_type_combo.addItems([
            "- 请选择泵类型 -",
            "IS 单级单吸离心泵 (清水/化工)",
            "S/SH 单级双吸离心泵 (大流量)",
            "D/DG 多级离心泵 (高扬程)",
            "IH 化工流程泵 (耐腐蚀)",
            "AY 离心油泵 (石油化工)",
        ])
        self.pump_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.pump_type_combo.currentTextChanged.connect(self._on_pump_type_changed)
        pump_layout.addWidget(self.pump_type_combo, prow, 1)
        pump_layout.addWidget(QLabel(""), prow, 2)
        prow += 1

        # 传动方式
        pump_layout.addWidget(self._mk_label("传动方式:"), prow, 0)
        self.drive_combo = QComboBox()
        self.drive_combo.setStyleSheet(COMBOBOX_STYLE)
        self.drive_combo.addItems([
            "- 请选择传动方式 -",
            "直联传动 (η=1.00)",
            "皮带传动 (η=0.95)",
            "齿轮传动 (η=0.98)",
            "液力偶合器 (η=0.97)",
        ])
        self.drive_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.drive_combo.currentTextChanged.connect(self._on_drive_changed)
        pump_layout.addWidget(self.drive_combo, prow, 1)
        self.drive_eff_label = QLabel("ηd=1.00")
        self.drive_eff_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        pump_layout.addWidget(self.drive_eff_label, prow, 2)
        prow += 1

        # 转速
        pump_layout.addWidget(self._mk_label("转速 N (r/min):"), prow, 0)
        self.speed_input = QLineEdit("2900")
        self.speed_input.setPlaceholderText("如: 2900")
        self.speed_input.setValidator(QDoubleValidator(500.0, 30000.0, 0))
        self.speed_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pump_layout.addWidget(self.speed_input, prow, 1)
        self.speed_hint = QLabel("2P=2900, 4P=1450")
        self.speed_hint.setStyleSheet("color: #7f8c8d; font-style: italic;")
        pump_layout.addWidget(self.speed_hint, prow, 2)

        left_layout.addWidget(pump_group)

        # ===== 输入参数组 =====
        input_group = CalculatorBase.make_group_box("输入参数")
        
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
        flow_label.setStyleSheet(INPUT_LABEL_STYLE)
        flow_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(flow_label, row, 0)

        self.flow_input = QLineEdit("100")
        self.flow_input.setPlaceholderText("例如: 100")
        self.flow_input.setValidator(QDoubleValidator(0.1, 10000.0, 6))
        self.flow_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.flow_input, row, 1)

        self.flow_combo = QComboBox()
        self.flow_combo.setStyleSheet(COMBOBOX_STYLE)
        self.flow_combo.addItems([
            "- 请选择流量范围 -",
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
        head_label.setStyleSheet(INPUT_LABEL_STYLE)
        head_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(head_label, row, 0)

        self.head_input = QLineEdit("50")
        self.head_input.setPlaceholderText("例如: 50")
        self.head_input.setValidator(QDoubleValidator(0.1, 1000.0, 6))
        self.head_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.head_input, row, 1)

        self.head_combo = QComboBox()
        self.head_combo.setStyleSheet(COMBOBOX_STYLE)
        self.head_combo.addItems([
            "- 请选择扬程范围 -",
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
        density_label.setStyleSheet(INPUT_LABEL_STYLE)
        density_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(density_label, row, 0)

        self.density_input = QLineEdit("1000")
        self.density_input.setPlaceholderText("例如: 1000 (水)")
        self.density_input.setValidator(QDoubleValidator(1.0, 2000.0, 6))
        self.density_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.density_input, row, 1)

        self.density_combo = QComboBox()
        self.density_combo.setStyleSheet(COMBOBOX_STYLE)
        self.density_combo.addItems([
            "- 请选择介质密度 -",
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
        efficiency_label.setStyleSheet(INPUT_LABEL_STYLE)
        efficiency_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(efficiency_label, row, 0)

        self.efficiency_input = QLineEdit("75")
        self.efficiency_input.setPlaceholderText("例如: 75")
        self.efficiency_input.setValidator(QDoubleValidator(10.0, 95.0, 6))
        self.efficiency_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.efficiency_input, row, 1)

        self.efficiency_combo = QComboBox()
        self.efficiency_combo.setStyleSheet(COMBOBOX_STYLE)
        self.efficiency_combo.addItems([
            "- 请选择泵效率范围 -",
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
        motor_efficiency_label.setStyleSheet(INPUT_LABEL_STYLE)
        motor_efficiency_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(motor_efficiency_label, row, 0)

        self.motor_efficiency_input = QLineEdit()
        self.motor_efficiency_input.setPlaceholderText("留空自动按电机容量估算")
        self.motor_efficiency_input.setValidator(QDoubleValidator(50.0, 98.0, 6))
        self.motor_efficiency_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.motor_efficiency_input, row, 1)

        self.motor_efficiency_combo = QComboBox()
        self.motor_efficiency_combo.setStyleSheet(COMBOBOX_STYLE)
        self.motor_efficiency_combo.addItems([
            "- 请选择电机效率范围 -",
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
        safety_label = QLabel("安全系数 K:")
        safety_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        safety_label.setStyleSheet(INPUT_LABEL_STYLE)
        safety_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(safety_label, row, 0)

        self.safety_input = QLineEdit("1.1")
        self.safety_input.setPlaceholderText("例如: 1.1")
        self.safety_input.setValidator(QDoubleValidator(1.0, 3.0, 2))
        self.safety_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.safety_input, row, 1)

        self.safety_combo = QComboBox()
        self.safety_combo.setStyleSheet(COMBOBOX_STYLE)
        self.safety_combo.addItems([
            "- 请选择安全系数 -",
            "1.0 (无余量)",
            "1.05 (轻微余量)",
            "1.1 (标准选型)",
            "1.15 (保守设计)",
            "1.2 (高安全)",
            "1.25 (超高安全)",
        ])
        self.safety_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.safety_combo.currentTextChanged.connect(self.on_safety_combo_changed)
        input_layout.addWidget(self.safety_combo, row, 2)
        
        left_layout.addWidget(input_group)
        left_layout.addStretch()
        
        # 右侧：结果显示区域
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        # 结果显示组
        result_group = CalculatorBase.make_group_box("计算结果")
        result_layout = QVBoxLayout(result_group)

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

        right_layout.addWidget(result_group)

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
        self.calculate_btn.clicked.connect(self.calculate)
        right_layout.addWidget(self.calculate_btn)

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
        self._refresh_auto_efficiency()
    
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
        """获取安全系数：优先读输入框"""
        try:
            val = float(self.safety_input.text())
            if 1.0 <= val <= 3.0:
                return val
        except:
            pass
        return 1.1

    def on_safety_combo_changed(self, text):
        """安全系数下拉选择"""
        import re
        m = re.search(r'([\d.]+)', text)
        if m and not text.startswith("-"):
            self.safety_input.setText(m.group(1))
    def _estimate_pump_efficiency(self, pump_type, flow_rate):
        """根据泵型和流量估算泵效率（每型独立分档）"""
        for upper, eff in self.PUMP_EFFICIENCY.get(pump_type, []):
            if flow_rate <= upper:
                return eff
        return None

    def _get_drive_efficiency(self):
        """从传动方式下拉框提取效率值"""
        import re
        t = self.drive_combo.currentText()
        m = re.search(r"η=([\d.]+)", t)
        return float(m.group(1)) if m else 1.0

    MOTOR_EFF_TABLE = {  # 电机效率估算 (GB 18613 3级能效)
        0.75: 0.75, 1.1: 0.78, 1.5: 0.80, 2.2: 0.82, 3.0: 0.84,
        4.0: 0.85, 5.5: 0.87, 7.5: 0.88, 11: 0.89, 15: 0.90,
        18.5: 0.91, 22: 0.91, 30: 0.92, 37: 0.92, 45: 0.93,
        55: 0.93, 75: 0.94, 90: 0.94, 110: 0.94, 132: 0.95,
        160: 0.95, 200: 0.95, 250: 0.95, 315: 0.95,
    }

    STANDARD_MOTORS = [0.75, 1.1, 1.5, 2.2, 3.0, 4.0, 5.5, 7.5, 11, 15, 18.5, 22,
                       30, 37, 45, 55, 75, 90, 110, 132, 160, 200, 250, 315, 355, 400]

    def calculate(self):
        """离心泵功率选型计算"""
        try:
            flow_rate = float(self.flow_input.text() or 0)
            head = float(self.head_input.text() or 0)
            density = float(self.density_input.text() or 0)
            speed = float(self.speed_input.text() or 2900)

            # 泵效率：优先自动估算，否则用输入值
            pump_eff_auto = self._estimate_pump_efficiency(self._pump_type, flow_rate)
            if pump_eff_auto and not self.efficiency_input.text().strip():
                efficiency = pump_eff_auto * 100  # 转为百分比
                self.efficiency_input.setText(f"{efficiency:.0f}")
            else:
                efficiency = float(self.efficiency_input.text() or 0)

            safety_factor = self.get_safety_factor()
            drive_eff = self._get_drive_efficiency()

            if not all([flow_rate, head, density, efficiency]):
                QMessageBox.warning(self, "输入错误", "请填写流量、扬程、密度和泵效率")
                return

            # === 计算 ===
            # 1. 有效功率 Pe = ρgQH / 3600000 (kW)
            pe = (flow_rate / 3600) * density * G * head / 1000

            # 2. 轴功率 P = Pe / η_pump
            p_shaft = pe / (efficiency / 100)

            # 3. 电机功率 P_m = P_shaft / η_drive * K_safety（先不计电机效率）
            p_motor_raw = p_shaft / drive_eff * safety_factor

            # 4. 匹配电机功率
            matched = min((m for m in self.STANDARD_MOTORS if m >= p_motor_raw),
                         default=self.STANDARD_MOTORS[-1])

            # 5. 电机效率：用户填写优先，否则按匹配电机容量查表估算 (GB 18613)
            motor_eff_text = self.motor_efficiency_input.text().strip()
            motor_eff_input = None
            if motor_eff_text:
                try:
                    motor_eff_input = float(motor_eff_text)
                except ValueError:
                    motor_eff_input = None
            m_eff = None  # default
            for kw, eff in sorted(self.MOTOR_EFF_TABLE.items()):
                if kw >= matched:
                    m_eff = eff
                    break
            if m_eff is None:
                m_eff = 0.90
            if motor_eff_input is not None:
                m_eff = motor_eff_input / 100

            # 6. 实际输入功率 = 轴功率 / η_drive / η_motor × K
            p_input = p_shaft / drive_eff / m_eff * safety_factor

            # 极数判定
            match_poles = 2 if speed >= 2500 else (4 if speed >= 1200 else 6)
            # === 输出 ===
            pump_type_name = self.pump_type_combo.currentText().split(" (")[0] if self._pump_type else "—"
            result = f"""═══════════════════════════════════════════════════
                        输入参数
═══════════════════════════════════════════════════

工况参数:
• 泵类型: {pump_type_name}
• 流量 Q: {flow_rate} m³/h
• 扬程 H: {head} m
• 转速 N: {speed:.0f} r/min
• 介质密度 ρ: {density} kg/m³

效率参数:
• 泵效率 η_pump: {efficiency:.1f} %{'  (自动估算)' if pump_eff_auto and efficiency == pump_eff_auto*100 else ''}
• 传动效率 η_drive: {drive_eff:.2f}
• 电机效率 η_motor: {m_eff*100:.1f} %  {'(用户输入)' if motor_eff_input is not None else f'(按{matched} kW级电机估算)'}
• 安全系数 K: {safety_factor}

═══════════════════════════════════════════════════
                       计算结果
═══════════════════════════════════════════════════

功率计算:
• 有效功率 Pe: {pe:.2f} kW
• 轴功率 P: {p_shaft:.2f} kW
• 电机输入功率 P_in: {p_input:.2f} kW

设备选型:
• 配套电机功率: {matched} kW
• 功率裕度: {((matched - p_input) / p_input * 100):.1f}%

═══════════════════════════════════════════════════
                       计算公式
═══════════════════════════════════════════════════

Pe = ρ·g·Q·H / 3600000
   = {density}×G×{flow_rate}×{head} / 3600000
   = {pe:.2f} kW

P_轴 = Pe / η_pump = {pe:.2f} / {efficiency/100:.3f} = {p_shaft:.2f} kW

P_电机 = P_轴 / (η_drive × η_motor) × K
       = {p_shaft:.2f} / ({drive_eff:.2f} × {m_eff:.2f}) × {safety_factor}
       = {p_input:.2f} kW

选型电机: ≥ {p_input:.2f} kW → {matched} kW

═══════════════════════════════════════════════════
                       应用建议
═══════════════════════════════════════════════════

• 泵类型: {pump_type_name}
• 传动方式: {self.drive_combo.currentText().split(' (')[0]}
• 推荐电机: Y{match_poles}-{matched} kW  (防护等级IP54以上)
• 实际选型应结合管路特性曲线和泵性能曲线复核
• 对于重载启动工况，建议加大一档电机"""

            self.result_text.setPlainText(result)
            self._last_result = result
            self._last_params = {
                "flow": flow_rate, "head": head, "density": density,
                "shaft_power": round(p_shaft, 2), "motor_power": round(p_input, 2),
                "matched_power": matched, "efficiency": efficiency,
                "pump_type": pump_type_name,
            }

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
        self.speed_input.clear()
        self.pump_type_combo.setCurrentIndex(0)
        self.drive_combo.setCurrentIndex(0)
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
                ("有效功率 (kW)", r"有效功率 Pe:\s*([\d.]+)"),
                ("轴功率 (kW)", r"轴功率 P:\s*([\d.]+)"),
                ("电机输入功率 (kW)", r"电机输入功率 P_in:\s*([\d.]+)"),
                ("配套电机功率 (kW)", r"配套电机功率:\s*([\d.]+)"),
            ]:
                m = re.search(pattern, text)
                if m:
                    outputs[key] = m.group(1)
            return {"inputs": inputs, "outputs": outputs}
        except Exception:
            return {"inputs": {}, "outputs": {}}
    
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
        """生成计算书 - 返回纯文本"""
        result_text = self.result_text.toPlainText()
        if not result_text or "计算结果" not in result_text:
            QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
            return ""
        project_info = self.get_project_info()
        report = f"""工程计算书 - 离心泵功率计算
计算工具: ChemCal 工程计算模块
========================================

"""
        report += result_text
        report += f"""══════════
 工程信息
══════════

    公司名称: {project_info.get('company_name', '')}
    工程编号: {project_info.get('project_number', '')}
    工程名称: {project_info.get('project_name', '')}
    子项名称: {project_info.get('subproject_name', '')}
    计算日期: {datetime.now().strftime('%Y-%m-%d')}

══════════
计算书标识
══════════

    计算书编号: {project_info.get('report_number', '')}
    版本: 1.0
    状态: 正式计算书

══════════
备注说明
══════════

    1. 本计算书基于 GB/T 5656 及相关标准规范
    2. 计算结果仅供参考，实际应用需考虑安全系数
    3. 重要工程参数应经专业工程师审核确认
    4. 计算条件变更时应重新进行计算

---
生成于 ChemCal 工程计算模块
"""
        return report

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "离心泵功率")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "离心泵功率")