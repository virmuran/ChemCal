from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox,
    QScrollArea, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtSvgWidgets import QSvgWidget
import re

from utils.docx_utils import ReportExporter
from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        MODE_BUTTON_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from svg_utils import svg_text


class 管道壁厚(CalculatorBase):
    """管道壁厚计算器（左右布局优化版）"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        
        # 使用传入的数据管理器或创建新的
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
            
        # 先初始化 material_database
        self.material_database = {}
        self.setup_material_database()  # 先调用这个
        self.setup_ui()  # 然后调用 setup_ui
        # 默认选 20# 碳钢，许用应力自动填入
        self.material_combo.setCurrentIndex(10)  # "20# (20°C) - GB/T699"
        self._update_svg_diagram()

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
            
    def setup_ui(self):
        """设置左右布局的管道壁厚计算UI"""
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
            "依据 ASME B31.3 工艺管道规范计算管道壁厚。输入设计压力、温度、材质后，自动匹配标准管表(Sch)推荐壁厚。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 2. 输入参数组 - 使用GridLayout实现整齐的布局
        input_group = CalculatorBase.make_group_box("输入参数")
        
        # 使用GridLayout确保整齐排列
        input_layout = QGridLayout(input_group)
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)
        
        # 标签样式 - 右对齐，粗体，右侧留间距（统一标准）
        label_style = INPUT_LABEL_STYLE
        
        # 输入框和下拉菜单使用 SizePolicy 自适应宽度，不设置固定宽度
        
        # 第一列：参数名称（右对齐）
        # 第二列：输入框（固定宽度）
        # 第三列：下拉菜单/按钮（固定宽度）
        
        row = 0
        
        # 设计压力
        pressure_label = QLabel("设计压力 P(MPa(g)):")
        pressure_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pressure_label.setStyleSheet(label_style)
        input_layout.addWidget(pressure_label, row, 0)
        
        self.pressure_input = QLineEdit()
        self.pressure_input.setPlaceholderText("例如: 1.0")
        self.pressure_input.setValidator(QDoubleValidator(0.01, 100.0, 3))
        self.pressure_input.setText("1.0")
        self.pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        input_layout.addWidget(self.pressure_input, row, 1)
        
        # 压力提示
        self.pressure_hint = QLabel("1 MPa = 10 bar")
        self.pressure_hint.setStyleSheet("font-style: italic;")
        self.pressure_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.pressure_hint, row, 2)
        
        row += 1
        
        # 设计温度
        temp_label = QLabel("设计温度 T(°C):")
        temp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        temp_label.setStyleSheet(label_style)
        input_layout.addWidget(temp_label, row, 0)
        
        self.temp_input = QLineEdit()
        self.temp_input.setPlaceholderText("例如: 150")
        self.temp_input.setValidator(QDoubleValidator(-200.0, 800.0, 1))
        self.temp_input.setText("180")
        self.temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        input_layout.addWidget(self.temp_input, row, 1)
        
        # 温度提示
        self.temp_hint = QLabel("直接输入温度值")
        self.temp_hint.setStyleSheet("font-style: italic;")
        self.temp_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.temp_hint, row, 2)
        
        row += 1
        
        # 管道外径
        diameter_label = QLabel("管道外径 D(mm):")
        diameter_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        diameter_label.setStyleSheet(label_style)
        input_layout.addWidget(diameter_label, row, 0)
        
        self.diameter_input = QLineEdit()
        self.diameter_input.setPlaceholderText("选择管径自动填入")
        self.diameter_input.setValidator(QDoubleValidator(1.0, 2000.0, 2))
        self.diameter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        input_layout.addWidget(self.diameter_input, row, 1)
        
        self.diameter_combo = QComboBox()
        self.diameter_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_diameter_options()
        self.diameter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.diameter_combo.currentTextChanged.connect(self.on_diameter_changed)
        input_layout.addWidget(self.diameter_combo, row, 2)
        
        row += 1
        
        # 焊接接头系数
        weld_label = QLabel("焊接接头系数 Ej:")
        weld_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        weld_label.setStyleSheet(label_style)
        input_layout.addWidget(weld_label, row, 0)
        
        self.weld_input = QLineEdit()
        self.weld_input.setPlaceholderText("例如: 1.0")
        self.weld_input.setValidator(QDoubleValidator(0.1, 1.0, 3))
        self.weld_input.setText("1.0")
        self.weld_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        input_layout.addWidget(self.weld_input, row, 1)
        
        self.weld_combo = QComboBox()
        self.weld_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_weld_factor_options()
        self.weld_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.weld_combo.currentTextChanged.connect(self.on_weld_factor_changed)
        input_layout.addWidget(self.weld_combo, row, 2)
        
        row += 1
        
        # 许用应力
        stress_label = QLabel("许用应力 S(MPa):")
        stress_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        stress_label.setStyleSheet(label_style)
        input_layout.addWidget(stress_label, row, 0)
        
        self.stress_input = QLineEdit()
        self.stress_input.setPlaceholderText("自动填充")
        self.stress_input.setReadOnly(True)
        self.stress_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.stress_input, row, 1)
        
        self.material_combo = QComboBox()
        self.material_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_material_options()
        self.material_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.material_combo.currentTextChanged.connect(self.on_material_changed)
        input_layout.addWidget(self.material_combo, row, 2)
        
        row += 1
        
        # 系数Y
        y_label = QLabel("系数 Y:")
        y_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        y_label.setStyleSheet(label_style)
        input_layout.addWidget(y_label, row, 0)
        
        self.y_input = QLineEdit()
        self.y_input.setPlaceholderText("自动计算")
        self.y_input.setReadOnly(True)
        self.y_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.y_input, row, 1)
        
        self.y_combo = QComboBox()
        self.y_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_y_factor_options()
        self.y_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.y_combo.currentTextChanged.connect(self.on_y_factor_changed)
        input_layout.addWidget(self.y_combo, row, 2)
        
        row += 1
        
        # 减薄量C1
        thinning_label = QLabel("减薄量 C₁(mm):")
        thinning_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        thinning_label.setStyleSheet(label_style)
        input_layout.addWidget(thinning_label, row, 0)
        
        self.thinning_input = QLineEdit()
        self.thinning_input.setPlaceholderText("例如: 0.50")
        self.thinning_input.setValidator(QDoubleValidator(0.0, 10.0, 2))
        self.thinning_input.setText("0.50")
        self.thinning_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        input_layout.addWidget(self.thinning_input, row, 1)
        
        self.thinning_combo = QComboBox()
        self.thinning_combo.setStyleSheet(COMBOBOX_STYLE)
        self.thinning_combo.addItems([
            "0.00 mm - 无减薄",
            "0.25 mm - 轻微减薄",
            "0.50 mm - 标准减薄",
            "0.75 mm - 中等减薄",
            "1.00 mm - 较大减薄"
        ])
        self.thinning_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.thinning_combo.currentTextChanged.connect(self.on_thinning_changed)
        input_layout.addWidget(self.thinning_combo, row, 2)
        
        row += 1
        
        # 腐蚀裕量C2
        corrosion_label = QLabel("腐蚀裕量 C₂(mm):")
        corrosion_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        corrosion_label.setStyleSheet(label_style)
        input_layout.addWidget(corrosion_label, row, 0)
        
        self.corrosion_input = QLineEdit()
        self.corrosion_input.setPlaceholderText("例如: 0.05")
        self.corrosion_input.setValidator(QDoubleValidator(0.0, 10.0, 2))
        self.corrosion_input.setText("1.50")
        self.corrosion_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        input_layout.addWidget(self.corrosion_input, row, 1)
        
        self.corrosion_combo = QComboBox()
        self.corrosion_combo.setStyleSheet(COMBOBOX_STYLE)
        self.corrosion_combo.addItems([
            "0.00 mm - 无腐蚀",
            "0.05 mm - 轻微腐蚀",
            "0.10 mm - 一般腐蚀",
            "0.50 mm - 中等腐蚀",
            "1.00 mm - 较强腐蚀",
            "1.50 mm - 严重腐蚀",
            "2.00 mm - 非常严重腐蚀"
        ])
        self.corrosion_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.corrosion_combo.currentTextChanged.connect(self.on_corrosion_changed)
        input_layout.addWidget(self.corrosion_combo, row, 2)
        
        left_layout.addWidget(input_group)
        
        # 4. 在底部添加拉伸因子
        left_layout.addStretch()
        
        # 右侧：结果显示区域 (占1/3宽度)
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        # 管道壁厚截面示意图 (SVG)
        self.svg_widget = QSvgWidget()
        self.svg_widget.setMinimumSize(280, 220)
        self.svg_widget.setMaximumHeight(280)
        self.svg_widget.setStyleSheet("background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 4px;")
        self.svg_widget.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
        right_layout.addWidget(self.svg_widget)
        
        # 计算结果
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
        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(CLEAR_BTN_STYLE)
        clear_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        clear_btn.clicked.connect(self.clear_inputs)
        docx_btn = QPushButton("DOCX")
        docx_btn.setStyleSheet(DOCX_BTN_STYLE)
        docx_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        docx_btn.clicked.connect(self.download_docx_report)
        pdf_btn = QPushButton("PDF")
        pdf_btn.setStyleSheet(PDF_BTN_STYLE)
        pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pdf_btn.clicked.connect(self.download_pdf_report)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(docx_btn)
        btn_layout.addWidget(pdf_btn)
        right_layout.addLayout(btn_layout)
        
        # 计算按钮（最底部）
        calc_btn = CalculatorBase.make_calc_button()
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)
        
        # 将左右两部分添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)  # 左侧占2/3
        main_layout.addWidget(right_widget, 1)  # 右侧占1/3
        
        # 初始材料选择
        self.on_material_changed(self.material_combo.currentText())
        self.on_y_factor_changed(self.y_combo.currentText())
    
    def setup_material_database(self):
        """设置材料数据库"""
        # 材料许用应力数据库 (MPa)
        self.material_database = {
            # 碳钢
            "Q235-A (20°C)": {"stress": 113, "type": "碳钢", "temp": 20},
            "Q235-A (100°C)": {"stress": 113, "type": "碳钢", "temp": 100},
            "Q235-A (200°C)": {"stress": 113, "type": "碳钢", "temp": 200},
            "20# (20°C)": {"stress": 130, "type": "碳钢", "temp": 20},
            "20# (100°C)": {"stress": 130, "type": "碳钢", "temp": 100},
            "20# (200°C)": {"stress": 130, "type": "碳钢", "temp": 200},
            "20# (300°C)": {"stress": 130, "type": "碳钢", "temp": 300},
            "20# (350°C)": {"stress": 122, "type": "碳钢", "temp": 350},
            "20# (400°C)": {"stress": 111, "type": "碳钢", "temp": 400},
            "20# (425°C)": {"stress": 104, "type": "碳钢", "temp": 425},
            "20# (450°C)": {"stress": 97, "type": "碳钢", "temp": 450},
            
            # 不锈钢 - 按照截图中的格式
            "304(0Cr18Ni9) (20°C)": {"stress": 137, "type": "奥氏体不锈钢", "temp": 20},
            "304(0Cr18Ni9) (100°C)": {"stress": 137, "type": "奥氏体不锈钢", "temp": 100},
            "304(0Cr18Ni9) (200°C)": {"stress": 137, "type": "奥氏体不锈钢", "temp": 200},
            "304(0Cr18Ni9) (300°C)": {"stress": 137, "type": "奥氏体不锈钢", "temp": 300},
            "304(0Cr18Ni9) (350°C)": {"stress": 132, "type": "奥氏体不锈钢", "temp": 350},
            "304(0Cr18Ni9) (400°C)": {"stress": 132, "type": "奥氏体不锈钢", "temp": 400},
            "304(0Cr18Ni9) (425°C)": {"stress": 121, "type": "奥氏体不锈钢", "temp": 425},
            "304(0Cr18Ni9) (450°C)": {"stress": 121, "type": "奥氏体不锈钢", "temp": 450},
            "304(0Cr18Ni9) (500°C)": {"stress": 121, "type": "奥氏体不锈钢", "temp": 500},
            
            "316(0Cr17Ni12Mo2) (20°C)": {"stress": 130, "type": "奥氏体不锈钢", "temp": 20},
            "316(0Cr17Ni12Mo2) (100°C)": {"stress": 130, "type": "奥氏体不锈钢", "temp": 100},
            "316(0Cr17Ni12Mo2) (200°C)": {"stress": 130, "type": "奥氏体不锈钢", "temp": 200},
            "316(0Cr17Ni12Mo2) (300°C)": {"stress": 130, "type": "奥氏体不锈钢", "temp": 300},
            "316(0Cr17Ni12Mo2) (400°C)": {"stress": 125, "type": "奥氏体不锈钢", "temp": 400},
            "316(0Cr17Ni12Mo2) (500°C)": {"stress": 116, "type": "奥氏体不锈钢", "temp": 500},
            "316(0Cr17Ni12Mo2) (600°C)": {"stress": 101, "type": "奥氏体不锈钢", "temp": 600},
            
            # 合金钢
            "16Mn (20°C)": {"stress": 170, "type": "合金钢", "temp": 20},
            "16Mn (100°C)": {"stress": 170, "type": "合金钢", "temp": 100},
            "16Mn (200°C)": {"stress": 170, "type": "合金钢", "temp": 200},
            "16Mn (300°C)": {"stress": 170, "type": "合金钢", "temp": 300},
            "16Mn (350°C)": {"stress": 170, "type": "合金钢", "temp": 350},
            "16Mn (400°C)": {"stress": 163, "type": "合金钢", "temp": 400},
            "16Mn (450°C)": {"stress": 150, "type": "合金钢", "temp": 450},
            
            "15CrMo (20°C)": {"stress": 150, "type": "合金钢", "temp": 20},
            "15CrMo (100°C)": {"stress": 150, "type": "合金钢", "temp": 100},
            "15CrMo (200°C)": {"stress": 150, "type": "合金钢", "temp": 200},
            "15CrMo (300°C)": {"stress": 150, "type": "合金钢", "temp": 300},
            "15CrMo (400°C)": {"stress": 150, "type": "合金钢", "temp": 400},
            "15CrMo (450°C)": {"stress": 147, "type": "合金钢", "temp": 450},
            "15CrMo (500°C)": {"stress": 140, "type": "合金钢", "temp": 500},
            "15CrMo (550°C)": {"stress": 128, "type": "合金钢", "temp": 550},
        }
    
    def setup_diameter_options(self):
        """设置管道外径选项"""
        # ASME B36.10 / GB/T 17395 标准外径
        diameter_options = [
            "- 请选择管道外径 -",
            "10.3 mm - DN6 [1/8\"]",
            "13.7 mm - DN8 [1/4\"]",
            "17.1 mm - DN10 [3/8\"]",
            "21.3 mm - DN15 [1/2\"]",
            "26.7 mm - DN20 [3/4\"]",
            "33.4 mm - DN25 [1\"]",
            "42.2 mm - DN32 [1.25\"]",
            "48.3 mm - DN40 [1.5\"]",
            "60.3 mm - DN50 [2\"]",
            "73.0 mm - DN65 [2.5\"]",
            "88.9 mm - DN80 [3\"]",
            "114.3 mm - DN100 [4\"]",
            "141.3 mm - DN125 [5\"]",
            "168.3 mm - DN150 [6\"]",
            "219.1 mm - DN200 [8\"]",
            "273.0 mm - DN250 [10\"]",
            "323.9 mm - DN300 [12\"]",
            "355.6 mm - DN350 [14\"]",
            "406.4 mm - DN400 [16\"]",
            "457.2 mm - DN450 [18\"]",
            "508.0 mm - DN500 [20\"]",
            "610.0 mm - DN600 [24\"]",
        ]
        self.diameter_combo.addItems(diameter_options)
        # 默认显示"请选择"提示
        self.diameter_combo.setCurrentIndex(0)
        
    def setup_weld_factor_options(self):
        """设置焊接接头系数选项"""
        weld_options = [
            "- 请选择焊接接头系数 -",
            "1.0 - 电熔焊 100%无损检测 双面对接焊",
            "0.9 - 电熔焊 100%无损检测 单面对接焊",
            "0.85 - 电熔焊 局部无损检测 双面对接焊",
            "0.8 - 电熔焊 局部无损检测 单面对接焊",
            "0.8 - 螺旋缝自动焊",
            "0.7 - 电熔焊 不作无损检测 双面对接焊",
            "0.6 - 电熔焊 不作无损检测 单面对接焊",
            "0.85 - 电阻焊 100%涡流检测",
            "0.65 - 电阻焊 不作无损检测",
            "0.6 - 加热炉焊 不作无损检测"
        ]
        self.weld_combo.addItems(weld_options)
        # 设置默认值
        self.weld_combo.setCurrentIndex(1)  # Ej=1.0
    
    def setup_y_factor_options(self):
        """设置系数Y选项"""
        y_options = [
            "- 请选择系数Y -",
            "0.4 - 铁素体钢 (温度≤482°C)",
            "0.5 - 铁素体钢 (温度>482°C)",
            "0.4 - 奥氏体钢 (温度≤482°C)",
            "0.7 - 奥氏体钢 (温度>482°C)",
            "0.4 - 其他金属材料"
        ]
        self.y_combo.addItems(y_options)
        # 设置默认值
        self.y_combo.setCurrentIndex(1)  # Y=0.4
        
    def on_diameter_changed(self, text):
        """处理直径选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            return
            
        # 从文本中提取数值并填入输入框
        try:
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                diameter_value = float(match.group(1))
                self.diameter_input.setText(f"{diameter_value}")
        except:
            pass
    
    def setup_material_options(self):
        """设置材料选项"""
        materials = [
            "- 请选择材料 -",  # 添加空值选项
            "304(0Cr18Ni9) (20°C) - GB/T1277 奥氏体不锈钢",
            "304(0Cr18Ni9) (100°C) - GB/T1277 奥氏体不锈钢",
            "304(0Cr18Ni9) (200°C) - GB/T1277 奥氏体不锈钢",
            "304(0Cr18Ni9) (300°C) - GB/T1277 奥氏体不锈钢",
            "304(0Cr18Ni9) (350°C) - GB/T1277 奥氏体不锈钢",
            "304(0Cr18Ni9) (400°C) - GB/T1277 奥氏体不锈钢",
            "316(0Cr17Ni12Mo2) (20°C) - GB/T1220 奥氏体不锈钢",
            "316(0Cr17Ni12Mo2) (300°C) - GB/T1220 奥氏体不锈钢",
            "316(0Cr17Ni12Mo2) (500°C) - GB/T1220 奥氏体不锈钢",
            "20# (20°C) - GB/T699 优质碳素结构钢",
            "20# (200°C) - GB/T699 优质碳素结构钢",
            "20# (400°C) - GB/T699 优质碳素结构钢",
            "Q235-A (20°C) - GB/T700 一般结构用钢",
            "16Mn (20°C) - GB/T1591 低合金高强度钢",
            "16Mn (300°C) - GB/T1591 低合金高强度钢",
            "15CrMo (20°C) - GB/T3077 耐热钢",
            "15CrMo (500°C) - GB/T3077 耐热钢"
        ]
        self.material_combo.addItems(materials)
        # 设置默认值为304不锈钢
        self.material_combo.setCurrentIndex(1)
    
    def on_material_changed(self, text):
        """处理材料选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.stress_input.clear()
            return
            
        material_key = text.split(" - ")[0]
        if material_key in self.material_database:
            stress = self.material_database[material_key]["stress"]
            self.stress_input.setText(f"{stress}")
            
            # 根据材料类型自动设置系数Y
            material_type = self.material_database[material_key]["type"]
            design_temp = float(self.temp_input.text() or "20")
            
            if "奥氏体" in material_type:
                if design_temp <= 482:
                    y_value = 0.4
                    y_text = "0.4 - 奥氏体钢 (温度≤482°C)"
                else:
                    y_value = 0.7
                    y_text = "0.7 - 奥氏体钢 (温度>482°C)"
            else:  # 铁素体钢和其他
                if design_temp <= 482:
                    y_value = 0.4
                    y_text = "0.4 - 铁素体钢 (温度≤482°C)"
                else:
                    y_value = 0.5
                    y_text = "0.5 - 铁素体钢 (温度>482°C)"
            
            self.y_input.setText(f"{y_value}")
            # 查找并设置对应的Y系数选项
            for i in range(self.y_combo.count()):
                if y_text in self.y_combo.itemText(i):
                    self.y_combo.setCurrentIndex(i)
                    break
    
    def on_weld_factor_changed(self, text):
        """处理焊接接头系数变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.weld_input.clear()
            return
            
        try:
            # 提取数值部分
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                weld_factor = float(match.group(1))
                self.weld_input.setText(f"{weld_factor}")
        except:
            pass
    
    def on_y_factor_changed(self, text):
        """处理系数Y变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.y_input.clear()
            return
            
        try:
            # 提取数值部分
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                y_factor = float(match.group(1))
                self.y_input.setText(f"{y_factor}")
        except:
            pass
    
    def on_thinning_changed(self, text):
        """处理减薄量变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.thinning_input.clear()
            return
            
        try:
            # 提取数值部分
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                thinning_value = float(match.group(1))
                self.thinning_input.setText(f"{thinning_value}")
        except:
            pass
    
    def on_corrosion_changed(self, text):
        """处理腐蚀裕量变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.corrosion_input.clear()
            return
            
        try:
            # 提取数值部分
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                corrosion_value = float(match.group(1))
                self.corrosion_input.setText(f"{corrosion_value}")
        except:
            pass
    
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        return svg_text(x, y, text, size, color, bold, center)

    def _generate_pipe_svg(self, **kw):
        """管道壁厚截面：双同心圆 + 管壁标注 + Sch 推荐"""
        w, h = 360, 260
        p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
            f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>'
        ]
        cx, cy = w/2, h/2 - 5
        od = kw.get("outer_diameter", "?")
        tn = kw.get("thickness", "?")
        sch = kw.get("sch_name", "")
        dp = kw.get("design_pressure", "")

        r_outer = 70
        # 壁厚比例：thickness/OD 映射到视觉厚度
        try:
            ratio = float(tn) / float(od) if od != "?" and tn != "?" else 0.06
        except:
            ratio = 0.06
        r_inner = r_outer * (1 - ratio * 3)  # 放大3倍便于观察
        r_inner = max(r_inner, 30)

        # 外圆（管壁外缘）
        p.append(f'<circle cx="{cx}" cy="{cy}" r="{r_outer}" fill="#e8edf2" stroke="#4a6fa5" stroke-width="3"/>')
        # 内圆（通径）
        p.append(f'<circle cx="{cx}" cy="{cy}" r="{r_inner}" fill="#dce4ec" stroke="#7f8c8d" stroke-width="1.5"/>')
        # 壁厚标注（右侧）
        arrow_rx = cx + r_outer + 10
        p.append(f'<line x1="{arrow_rx}" y1="{cy+r_inner}" x2="{arrow_rx}" y2="{cy+r_outer}" stroke="#e74c3c" stroke-width="2"/>')
        tn_label = f"t={tn}mm" if tn != "?" else "t=? mm"
        p.append(self._text(arrow_rx+10, cy+(r_inner+r_outer)/2, tn_label, size=10, color="#e74c3c", bold=True, center=False))

        # 外径标注
        dia_y = cy + r_outer + 30
        od_label = f"φ{od}mm" if od != "?" else "φ? mm"
        p.append(f'<line x1="{cx-r_outer}" y1="{dia_y}" x2="{cx+r_outer}" y2="{dia_y}" stroke="#7f8c8d" stroke-width="1" marker-start="url(#dimL)" marker-end="url(#dimR)"/>')
        p.append(self._text(cx, dia_y+16, od_label, size=10, color="#555"))

        # 顶部 Sch 标签
        title = f"管道壁厚 — {sch}" if sch else "管道壁厚"
        p.append(self._text(cx, 12, title, size=10, color="#4a6fa5", bold=True))

        # 底部信息
        info_y = h - 14
        if dp:
            p.append(self._text(10, info_y, f"设计压力: {dp} MPa", size=10, color="#444", center=False))
        if od != "?" and tn != "?":
            try:
                ratio_pct = round(float(tn) / float(od) * 100, 1)
                p.append(self._text(w-60, info_y, f"t/D={ratio_pct}%", size=10, color="#444", center=False))
            except: pass

        p.append('<defs>'
                 '<marker id="dimL" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M8,0 L0,4 L8,8 Z" fill="#7f8c8d"/></marker>'
                 '<marker id="dimR" markerWidth="8" markerHeight="8" refX="0" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#7f8c8d"/></marker>'
                 '</defs></svg>')
        return "".join(p)

    def _update_svg_diagram(self):
        try:
            kw = {}
            if hasattr(self, '_last_outer_diameter') and self._last_outer_diameter:
                kw['outer_diameter'] = self._last_outer_diameter
            else:
                try: kw['outer_diameter'] = float(self.diameter_input.text())
                except: pass
            if hasattr(self, '_last_thickness') and self._last_thickness:
                kw['thickness'] = round(self._last_thickness, 1)
            if hasattr(self, '_last_design_pressure') and self._last_design_pressure:
                kw['design_pressure'] = round(self._last_design_pressure, 2)
            if hasattr(self, '_last_sch_name') and self._last_sch_name:
                kw['sch_name'] = self._last_sch_name
            s = self._generate_pipe_svg(**kw)
            self.svg_widget.load(s.encode("utf-8"))
        except: pass
    def calculate(self):
        """计算管道壁厚"""
        try:
            # 获取输入值
            standard = "ASME B31.3 - 工艺管道"
            design_pressure = float(self.pressure_input.text())  # MPa
            design_temp = float(self.temp_input.text())  # °C
            outer_diameter = float(self.diameter_input.text())  # mm
            allowable_stress = float(self.stress_input.text())  # MPa
            weld_factor = float(self.weld_input.text())
            y_factor = float(self.y_input.text())
            thinning_allowance = float(self.thinning_input.text())  # mm (减薄量C1)
            corrosion_allowance = float(self.corrosion_input.text())  # mm (腐蚀裕量C2)
            
            # 验证输入
            if not all([design_pressure, outer_diameter, allowable_stress, weld_factor, y_factor]):
                QMessageBox.warning(self, "输入错误", "请填写所有必需参数")
                return
            
            if design_pressure <= 0 or outer_diameter <= 0 or allowable_stress <= 0:
                QMessageBox.warning(self, "输入错误", "压力、直径和许用应力必须大于0")
                return
            
            # 根据ASME B31.3公式计算理论壁厚
            # t = P * D / (2 * S * E + 2 * P * Y) + C
            # 其中C是总附加量 = C1 + C2
            
            total_additional = thinning_allowance + corrosion_allowance
            
            # 计算理论壁厚 (mm) - 使用标准公式
            theoretical_thickness = (design_pressure * outer_diameter) / \
                                  (2 * allowable_stress * weld_factor + 2 * design_pressure * y_factor)
            
            # 计算设计壁厚 (包含总附加量)
            design_thickness = theoretical_thickness + total_additional
            
            # 计算最小要求壁厚
            minimum_required_thickness = theoretical_thickness + corrosion_allowance
            
            # 选择标准管壁厚 — 通过管表匹配 Sch
            lookup = self._lookup_pipe_schedule(outer_diameter, design_thickness)
            if lookup:
                sch_name, standard_thickness, sch_margin, matched_dn, matched_od = lookup
            else:
                # 外径不在管表中，用通用圆整
                standard_thicknesses = [2.0,2.3,2.6,2.9,3.2,3.6,4.0,4.5,5.0,5.6,6.3,7.1,8.0,8.8,10.0,11.0,12.5,14.2,16.0,17.5,20.0]
                standard_thickness = min((t for t in standard_thicknesses if t >= design_thickness), default=standard_thicknesses[-1])
                sch_name = "—"
                sch_margin = round(standard_thickness - design_thickness, 2)
                matched_dn = "?"
                matched_od = outer_diameter
            
            # 计算实际应力
            actual_stress = design_pressure * (outer_diameter - 2 * standard_thickness) / \
                          (2 * standard_thickness * weld_factor)
            
            # 安全系数
            safety_factor = allowable_stress / actual_stress if actual_stress > 0 else 0
            
            # 计算重量增加百分比
            if standard_thickness > 0 and theoretical_thickness > 0:
                weight_increase = ((standard_thickness / theoretical_thickness) - 1) * 100
            else:
                weight_increase = 0
            
            # 显示结果
            result = self.format_results(
                standard, design_pressure, design_temp, outer_diameter, 
                allowable_stress, weld_factor, y_factor, 
                thinning_allowance, corrosion_allowance, total_additional,
                theoretical_thickness, minimum_required_thickness, design_thickness,
                standard_thickness, actual_stress, safety_factor, weight_increase,
                sch_name, sch_margin, matched_dn, matched_od
            )
            
            self.result_text.setText(result)

            self._last_outer_diameter = outer_diameter
            self._last_thickness = standard_thickness
            self._last_design_pressure = design_pressure
            self._last_sch_name = sch_name
            self._update_svg_diagram()
            
        except ValueError as e:
            QMessageBox.critical(self, "计算错误", f"参数输入格式错误: {str(e)}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "参数不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")
    
    # ── 标准管道壁厚表 (ASME B36.10/B36.19) ──
    # { (DN, 外径mm): [ (Sch, 壁厚mm), ... ] } 按壁厚从小到大排列
    PIPE_SCHEDULES = {
        (6, 10.3):    [("Sch40",1.73),("Sch80",2.41),("Sch160",3.15)],
        (8, 13.7):    [("Sch40",2.24),("Sch80",3.02),("Sch160",3.68)],
        (10, 17.1):   [("Sch40",2.31),("Sch80",3.20),("Sch160",4.01)],
        (15, 21.3):   [("Sch5S",1.65),("Sch10S",2.11),("Sch40",2.77),("Sch80",3.73),("Sch160",4.78)],
        (20, 26.7):   [("Sch5S",1.65),("Sch10S",2.11),("Sch40",2.87),("Sch80",3.91),("Sch160",5.56)],
        (25, 33.4):   [("Sch5S",1.65),("Sch40",3.38),("Sch80",4.55),("Sch160",6.35)],
        (32, 42.2):   [("Sch5S",1.65),("Sch40",3.56),("Sch80",4.85),("Sch160",6.35)],
        (40, 48.3):   [("Sch5S",1.65),("Sch40",3.68),("Sch80",5.08),("Sch160",7.14)],
        (50, 60.3):   [("Sch5S",1.65),("Sch10S",2.77),("Sch40",3.91),("Sch80",5.54),("Sch160",8.74)],
        (65, 73.0):   [("Sch5S",2.11),("Sch40",5.16),("Sch80",7.01),("Sch160",9.53)],
        (80, 88.9):   [("Sch5S",2.11),("Sch10S",3.05),("Sch40",5.49),("Sch80",7.62),("Sch160",11.13)],
        (100,114.3):  [("Sch5S",2.11),("Sch10S",3.05),("Sch40",6.02),("Sch80",8.56),("Sch160",13.49)],
        (125,141.3):  [("Sch5S",2.77),("Sch10S",3.40),("Sch40",6.55),("Sch80",9.53),("Sch160",15.88)],
        (150,168.3):  [("Sch5S",2.77),("Sch10S",3.40),("Sch40",7.11),("Sch80",10.97),("Sch160",18.26)],
        (200,219.1):  [("Sch5S",2.77),("Sch10S",3.76),("Sch40",8.18),("Sch80",12.70),("Sch160",23.01)],
        (250,273.0):  [("Sch5S",3.40),("Sch10S",4.19),("Sch40",9.27),("Sch80",15.09),("Sch160",28.58)],
        (300,323.9):  [("Sch5S",3.96),("Sch10S",4.57),("Sch40",10.31),("Sch80",17.48),("Sch160",33.32)],
        (350,355.6):  [("Sch10",6.35),("Sch40",11.13),("Sch80",19.05),("Sch160",35.71)],
        (400,406.4):  [("Sch10",6.35),("Sch40",12.70),("Sch80",21.44),("Sch160",40.49)],
        (450,457.2):  [("Sch10",6.35),("Sch40",14.27),("Sch80",23.83),("Sch160",45.24)],
        (500,508.0):  [("Sch10",6.35),("Sch40",15.09),("Sch80",26.19),("Sch160",50.01)],
        (600,610.0):  [("Sch10",6.35),("Sch40",17.48),("Sch80",30.96),("Sch160",59.54)],
    }

    def _lookup_pipe_schedule(self, outer_diameter_mm, required_thickness):
        """根据外径匹配最近DN，查找满足壁厚要求的标准Sch
        返回: (Sch名称, 标准壁厚mm, 裕度mm) 或 None"""
        best_dn = None
        best_dist = 9999
        for (dn, od), schedules in self.PIPE_SCHEDULES.items():
            dist = abs(od - outer_diameter_mm)
            if dist < best_dist:
                best_dist = dist
                best_dn = (dn, od, schedules)
        if best_dn is None or best_dist > 10:
            return None
        dn, od, schedules = best_dn
        for sch_name, wall_thk in schedules:
            if wall_thk >= required_thickness:
                margin = wall_thk - required_thickness
                return (sch_name, wall_thk, round(margin, 2), dn, od)
        # 超过最大壁厚
        last_sch, last_thk = schedules[-1]
        return (last_sch, last_thk, round(last_thk - required_thickness, 2), dn, od)

    def clear_inputs(self):
        """清空所有输入"""
        self.material_combo.setCurrentIndex(0)
        self.diameter_combo.setCurrentIndex(0)
        self.weld_combo.setCurrentIndex(0)
        self.y_combo.setCurrentIndex(0)
        self.thinning_combo.setCurrentIndex(0)
        self.corrosion_combo.setCurrentIndex(0)
        self.pressure_input.clear()
        self.temp_input.clear()
        self.diameter_input.clear()
        self.weld_input.clear()
        self.stress_input.clear()
        self.y_input.clear()
        self.thinning_input.clear()
        self.corrosion_input.clear()
        self.result_text.clear()

    def _get_history_data(self):
        """提供历史记录数据"""
        standard = "ASME B31.3 - 工艺管道"
        design_pressure = float(self.pressure_input.text() or 0)
        design_temp = float(self.temp_input.text() or 0)
        outer_diameter = float(self.diameter_input.text() or 0)
        weld_factor = float(self.weld_input.text() or 0)
        allowable_stress = float(self.stress_input.text() or 0)
        y_factor = float(self.y_input.text() or 0)
        thinning_allowance = float(self.thinning_input.text() or 0)
        corrosion_allowance = float(self.corrosion_input.text() or 0)

        inputs = {
            "计算标准": standard,
            "设计压力_MPa": design_pressure,
            "设计温度_C": design_temp,
            "管道外径_mm": outer_diameter,
            "焊接接头系数": weld_factor,
            "许用应力_MPa": allowable_stress,
            "系数Y": y_factor,
            "减薄量_mm": thinning_allowance,
            "腐蚀裕量_mm": corrosion_allowance
        }

        outputs = {}
        try:
            total_additional = thinning_allowance + corrosion_allowance
            theoretical_thickness = (design_pressure * outer_diameter) / \
                                   (2 * allowable_stress * weld_factor + 2 * design_pressure * y_factor)
            design_thickness = theoretical_thickness + total_additional
            minimum_required_thickness = theoretical_thickness + corrosion_allowance
            standard_thickness = self.select_standard_thickness(design_thickness)
            actual_stress = design_pressure * (outer_diameter - 2 * standard_thickness) / \
                          (2 * standard_thickness * weld_factor)
            safety_factor = allowable_stress / actual_stress if actual_stress > 0 else 0
            weight_increase = ((standard_thickness / theoretical_thickness) - 1) * 100 if theoretical_thickness > 0 else 0

            outputs = {
                "理论壁厚_mm": round(theoretical_thickness, 2),
                "最小要求壁厚_mm": round(minimum_required_thickness, 2),
                "设计壁厚_mm": round(design_thickness, 2),
                "选用标准壁厚_mm": standard_thickness,
                "实际应力_MPa": round(actual_stress, 1),
                "安全系数": round(safety_factor, 2),
                "强度状态": "安全" if safety_factor >= 1.0 else "需重新设计"
            }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def format_results(self, standard, design_pressure, design_temp, outer_diameter,
                      allowable_stress, weld_factor, y_factor,
                      thinning_allowance, corrosion_allowance, total_additional,
                      theoretical_thickness, minimum_required_thickness, design_thickness,
                      standard_thickness, actual_stress, safety_factor, weight_increase,
                      sch_name="?", sch_margin=0.0, matched_dn="?", matched_od=0.0):
        """格式化计算结果 — 包含管道等级推荐"""
        pipe_spec = f"DN{matched_dn} (φ{matched_od}×{standard_thickness}mm)  {sch_name}"
        return f"""═══════════
 输入参数
══════════

    计算标准: {standard}
    设计压力 P: {design_pressure} MPa(g)
    设计温度 T: {design_temp} °C
    管道外径 D: {outer_diameter} mm
    焊接接头系数 Ej: {weld_factor}
    许用应力 S: {allowable_stress} MPa
    系数 Y: {y_factor}
    减薄量 C₁: {thinning_allowance:.2f} mm
    腐蚀裕量 C₂: {corrosion_allowance:.2f} mm
    总附加量 C: {total_additional:.2f} mm

══════════
壁厚计算
══════════

    • 理论计算壁厚 t₀: {theoretical_thickness:.2f} mm
    • 最小要求壁厚 t_min: {minimum_required_thickness:.2f} mm
    • 设计计算壁厚 t_d: {design_thickness:.2f} mm
    • 管表匹配Sch: {sch_name}
    • 推荐取用壁厚 t_n: {standard_thickness} mm
    • 推荐管道规格: {pipe_spec}
    • 壁厚裕度: {sch_margin:.2f} mm

══════════
强度校核
══════════

    • 实际计算应力: {actual_stress:.1f} MPa
    • 安全系数: {safety_factor:.2f}
    • 强度状态: {'安全 (安全系数≥1.0)' if safety_factor >= 1.0 else '需重新设计 (安全系数<1.0)'}

══════════
经济性分析
══════════

    • 重量增加: {weight_increase:.1f} %
    • 壁厚余量: {standard_thickness - design_thickness:.2f} mm

══════════
计算说明
══════════

    • 采用标准壁厚计算公式: t = P×D / (2×S×E + 2×P×Y) + C
    • 管表壁厚基于 ASME B36.10/B36.19 标准 Sch 系列
    • Y系数根据材料类型和设计温度确定
    • 腐蚀裕量C₂建议取值: 碳钢 1.5~3mm, 不锈钢 0~1mm
    • 建议安全系数不小于1.0，重要管道建议1.5以上
    • 计算结果仅供参考，实际应用需经专业工程师审核"""
    
    def get_project_info(self):
        return {
            "project_name": "管道壁厚计算",
            "calculator_name": "管道壁厚计算器",
            "version": "1.0",
            "description": "依据 ASME B31.3 工艺管道规范计算管道壁厚并匹配标准管表(Sch)"
        }

    def generate_report(self):
        """生成计算书"""
        content = self.result_text.toPlainText().strip()
        if not content:
            return "尚未进行计算。"
        lines = ["工程计算书 - 管道壁厚计算", "=" * 50, "", content]
        return "\n".join(lines)

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "管道壁厚")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "管道壁厚")

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = 管道壁厚()
    widget.resize(1200, 800)
    widget.show()
    
    sys.exit(app.exec())