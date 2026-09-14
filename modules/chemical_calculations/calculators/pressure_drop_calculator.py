from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox,
    QScrollArea, QDialog, QSpinBox, QButtonGroup, QGridLayout,
    QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
from PySide6.QtSvgWidgets import QSvgWidget
import math
import re
from datetime import datetime
import sys


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K, G
from svg_utils import svg_text
from utils.docx_utils import ReportExporter  # DOCX 报告导出


class FittingsDialog(QDialog):
    """管件和阀门选择对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择管件和阀门")
        self.setModal(True)
        self.resize(400, 500)
        self.fittings_data = {}
        self.setup_ui()
    
    def setup_ui(self):
        """设置对话框UI"""
        layout = QVBoxLayout(self)
        
        # 说明文本
        description = QLabel("选择管件和阀门类型及数量：")
        layout.addWidget(description)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("")
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 管件和阀门数据
        fittings_list = [
            ("45°弯头", 0.35),
            ("90°弯头", 0.75),
            ("90°方形弯头", 1.3),
            ("180°弯头", 1.5),
            ("三通", 1.0),
            ("截止阀(全开)", 6.0),
            ("角阀(全开)", 2.0),
            ("闸阀(全开)", 0.2),
            ("闸阀(3/4开)", 0.9),
            ("闸阀(1/2开)", 4.5),
            ("闸阀(1/4开)", 24.0),
            ("盘式流量计", 8.0),
            ("蝶阀(全开)", 0.3),
            ("转子流量计", 5.0),
            ("旋启止回阀", 2.0),
            ("升降止回阀", 10.0),
            ("文丘里流量计", 0.2)
        ]
        
        for name, resistance in fittings_list:
            widget = QWidget()
            h_layout = QHBoxLayout(widget)
            
            label = QLabel(f"{name} (ξ={resistance})")
            h_layout.addWidget(label)
            
            spin_box = QSpinBox()
            spin_box.setRange(0, 100)
            spin_box.valueChanged.connect(lambda value, n=name, r=resistance: self.on_fitting_changed(n, r, value))
            h_layout.addWidget(spin_box)
            
            scroll_layout.addWidget(widget)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        
        confirm_btn = QPushButton("确认")
        confirm_btn.clicked.connect(self.accept)
        button_layout.addWidget(confirm_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def on_fitting_changed(self, name, resistance, count):
        """处理管件数量变化"""
        self.fittings_data[name] = (resistance, count)
    
    def clear_all(self):
        """清空所有选择"""
        # 重置所有spinbox
        for widget in self.findChildren(QSpinBox):
            widget.setValue(0)
        self.fittings_data.clear()
    
    def get_total_resistance(self):
        """获取总局部阻力系数"""
        total = 0.0
        for resistance, count in self.fittings_data.values():
            total += resistance * count
        return total

class 压降计算(CalculatorBase):
    """管道压降计算（左右布局优化版）"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        
        # 使用传入的数据管理器或创建新的
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        
        self.local_resistance_coeff = 0.0
        self.setup_ui()
        self.setup_mode_dependencies()
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
        """设置左右布局的管道压降计算UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧：输入参数区域 - 使用动态宽度
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # 1. 首先添加说明文本
        description = QLabel(
            "计算流体在管道中流动时的压力损失，支持不可压缩流体和可压缩流体计算。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 2. 然后添加计算模式选择
        mode_group = QGroupBox("计算模式")
        mode_layout = QHBoxLayout(mode_group)
        
        self.mode_button_group = QButtonGroup(self)
        self.mode_buttons = {}
        
        modes = [
            ("不可压缩流体", "适用于液体和低速气体"),
            ("可压缩流体（绝热）", "适用于高速气体，绝热过程"),
            ("可压缩流体（等温）", "适用于高速气体，等温过程")
        ]
        
        for i, (mode_name, tooltip) in enumerate(modes):
            btn = self.make_mode_button(mode_name, tooltip)
            self.mode_button_group.addButton(btn, i)
            mode_layout.addWidget(btn)
            self.mode_buttons[mode_name] = btn
        
        # 默认选择第一个
        self.mode_buttons["不可压缩流体"].setChecked(True)
        self.mode_button_group.buttonClicked.connect(self.on_mode_button_clicked)
        
        left_layout.addWidget(mode_group)
        
        # 3. 输入参数组 - 使用GridLayout实现整齐的布局
        input_group = QGroupBox("输入参数")
        
        # 使用GridLayout确保整齐排列
        input_layout = QGridLayout(input_group)
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        
        # 设置列宽比例
        input_layout.setColumnStretch(0, 4)  # 标签列（规范要求4）
        input_layout.setColumnStretch(1, 8)  # 输入框列（规范要求8）
        input_layout.setColumnStretch(2, 5)  # 提示列（规范要求5）
        
        # 标签样式统一走 INPUT_LABEL_STYLE
        row = 0
        
        # 管道粗糙度
        roughness_label = QLabel("管道粗糙度:")
        roughness_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        roughness_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(roughness_label, row, 0)
        
        self.roughness_input = QLineEdit("0.2")
        self.roughness_input.setPlaceholderText("输入粗糙度值")
        self.roughness_input.setValidator(QDoubleValidator(0.001, 10.0, 6))
        self.roughness_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        input_layout.addWidget(self.roughness_input, row, 1)
        
        self.roughness_combo = QComboBox()
        self.roughness_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_roughness_options()
        self.roughness_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        self.roughness_combo.currentTextChanged.connect(self.on_roughness_changed)
        input_layout.addWidget(self.roughness_combo, row, 2)
        
        row += 1
        
        # 管道内径
        diameter_label = QLabel("管道内径 (mm):")
        diameter_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        diameter_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(diameter_label, row, 0)
        
        self.diameter_input = QLineEdit("100")
        self.diameter_input.setPlaceholderText("输入内径值")
        self.diameter_input.setValidator(QDoubleValidator(1.0, 2000.0, 6))
        self.diameter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        input_layout.addWidget(self.diameter_input, row, 1)
        
        self.diameter_combo = QComboBox()
        self.diameter_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_diameter_options()
        self.diameter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        self.diameter_combo.currentTextChanged.connect(self.on_diameter_changed)
        input_layout.addWidget(self.diameter_combo, row, 2)
        
        row += 1
        
        # 管道长度
        length_label = QLabel("管道长度 (m):")
        length_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        length_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(length_label, row, 0)
        
        self.length_input = QLineEdit("300")
        self.length_input.setPlaceholderText("例如: 300")
        self.length_input.setValidator(QDoubleValidator(0.1, 10000.0, 6))
        self.length_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        input_layout.addWidget(self.length_input, row, 1)
        
        # 长度输入不需要下拉菜单，替换为提示标签
        self.length_hint = QLabel("直接输入长度值")
        self.length_hint.setStyleSheet("font-style: italic;")
        self.length_hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        input_layout.addWidget(self.length_hint, row, 2)
        
        row += 1
        
        # 流体流量
        flow_label = QLabel("流体流量 (m³/h):")
        flow_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        flow_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(flow_label, row, 0)
        
        self.flow_input = QLineEdit("5172")
        self.flow_input.setPlaceholderText("例如: 5172")
        self.flow_input.setValidator(QDoubleValidator(0.1, 1000000.0, 6))
        self.flow_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        input_layout.addWidget(self.flow_input, row, 1)
        
        # 流量输入不需要下拉菜单，替换为提示标签
        self.flow_hint = QLabel("直接输入流量值")
        self.flow_hint.setStyleSheet("font-style: italic;")
        self.flow_hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        input_layout.addWidget(self.flow_hint, row, 2)
        
        row += 1
        
        # 流体物质
        fluid_label = QLabel("流体物质:")
        fluid_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fluid_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(fluid_label, row, 0)
        
        self.fluid_input = QLineEdit()
        self.fluid_input.setPlaceholderText("自动填充")
        self.fluid_input.setReadOnly(True)
        self.fluid_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        input_layout.addWidget(self.fluid_input, row, 1)
        
        self.fluid_combo = QComboBox()
        self.fluid_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_fluid_options()
        self.fluid_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        self.fluid_combo.currentTextChanged.connect(self.on_fluid_changed)
        input_layout.addWidget(self.fluid_combo, row, 2)
        
        row += 1
        
        # 密度
        density_label = QLabel("密度 (kg/m³):")
        density_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        density_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(density_label, row, 0)
        
        self.density_input = QLineEdit()
        self.density_input.setPlaceholderText("自动填充")
        self.density_input.setReadOnly(True)
        self.density_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        input_layout.addWidget(self.density_input, row, 1)
        
        # 密度不需要下拉，替换为提示标签
        self.density_hint = QLabel("根据流体自动计算")
        self.density_hint.setStyleSheet("font-style: italic;")
        self.density_hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        input_layout.addWidget(self.density_hint, row, 2)
        
        row += 1
        
        # 动力粘度
        viscosity_label = QLabel("动力粘度 (mPa·s):")
        viscosity_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        viscosity_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(viscosity_label, row, 0)
        
        self.viscosity_input = QLineEdit()
        self.viscosity_input.setPlaceholderText("自动填充")
        self.viscosity_input.setReadOnly(True)
        self.viscosity_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        input_layout.addWidget(self.viscosity_input, row, 1)
        
        # 粘度不需要下拉，替换为提示标签
        self.viscosity_hint = QLabel("根据流体自动计算")
        self.viscosity_hint.setStyleSheet("font-style: italic;")
        self.viscosity_hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        input_layout.addWidget(self.viscosity_hint, row, 2)
        
        row += 1
        
        # 标高变化 - 仅不可压缩流体
        self.elevation_label = QLabel("标高变化 (m):")
        self.elevation_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.elevation_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(self.elevation_label, row, 0)
        
        self.elevation_input = QLineEdit("0")
        self.elevation_input.setPlaceholderText("例如: 0")
        self.elevation_input.setValidator(QDoubleValidator(-1000.0, 1000.0, 6))
        self.elevation_input.setText("0")
        self.elevation_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        input_layout.addWidget(self.elevation_input, row, 1)
        
        # 标高变化不需要下拉，替换为提示标签
        self.elevation_hint = QLabel("正值为上升，负值为下降")
        self.elevation_hint.setStyleSheet("font-style: italic;")
        self.elevation_hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        input_layout.addWidget(self.elevation_hint, row, 2)
        
        row += 1
        
        # 绝热系数 - 仅绝热流动
        self.adiabatic_label = QLabel("绝热系数:")
        self.adiabatic_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.adiabatic_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(self.adiabatic_label, row, 0)
        
        self.adiabatic_input = QLineEdit()
        self.adiabatic_input.setPlaceholderText("自动填充")
        self.adiabatic_input.setReadOnly(True)
        self.adiabatic_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        input_layout.addWidget(self.adiabatic_input, row, 1)
        
        self.adiabatic_combo = QComboBox()
        self.adiabatic_combo.setStyleSheet(COMBOBOX_STYLE)
        self.adiabatic_combo.addItems([
            "- 请选择绝热系数 -",
            "1.67 - 单原子气体",
            "1.40 - 双原子气体", 
            "1.30 - 三原子气体",
            "自定义绝热系数"
        ])
        self.adiabatic_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        self.adiabatic_combo.currentTextChanged.connect(self.on_adiabatic_changed)
        input_layout.addWidget(self.adiabatic_combo, row, 2)
        
        row += 1
        
        # 起始压力 - 可压缩流体
        self.pressure_label = QLabel("起始压力 (kPa):")
        self.pressure_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.pressure_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(self.pressure_label, row, 0)
        
        self.pressure_input = QLineEdit("101.3")
        self.pressure_input.setPlaceholderText("例如: 101.3")
        self.pressure_input.setValidator(QDoubleValidator(0.1, 10000.0, 6))
        self.pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平扩展
        input_layout.addWidget(self.pressure_input, row, 1)
        
        # 压力不需要下拉，替换为提示标签
        self.pressure_hint = QLabel("标准大气压: 101.3 kPa")
        self.pressure_hint.setStyleSheet("font-style: italic;")
        self.pressure_hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        input_layout.addWidget(self.pressure_hint, row, 2)
        
        left_layout.addWidget(input_group)
        
        # 4. 管件和阀门按钮
        self.fittings_btn = QPushButton("选择管件和阀门")
        self.fittings_btn.setFont(QFont("Arial", 10))
        self.fittings_btn.clicked.connect(self.select_fittings)
        self.fittings_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.fittings_btn.setStyleSheet(CLEAR_BTN_STYLE)
        left_layout.addWidget(self.fittings_btn)
        
        # 5. 在底部添加拉伸因子
        left_layout.addStretch()
        
        # 右侧：结果显示区域 - 使用动态宽度
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)  # 设置最小宽度而不是固定宽度
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        self.svg_widget = QSvgWidget()
        self.svg_widget.setMinimumHeight(220)
        self.svg_widget.setMaximumHeight(280)
        self.svg_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.svg_widget.setStyleSheet("background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 4px;")
        right_layout.addWidget(self.svg_widget)
        self.svg_widget.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
        
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
        calc_btn = self.make_calc_button("计 算")
        calc_btn.clicked.connect(self.calculate_pressure_drop)
        right_layout.addWidget(calc_btn)
        
        # 将左右两部分添加到主布局，设置拉伸因子
        main_layout.addWidget(left_widget, 2)  # 左侧占2/3权重
        main_layout.addWidget(right_widget, 1)  # 右侧占1/3权重
    
    def on_mode_button_clicked(self, button):
        """处理计算模式按钮点击"""
        mode_text = button.text()
        self.on_mode_changed(mode_text)

    def get_current_mode(self):
        """获取当前选择的计算模式"""
        checked_button = self.mode_button_group.checkedButton()
        if checked_button:
            return checked_button.text()
        return "不可压缩流体"  # 默认值

    def setup_mode_dependencies(self):
        """设置计算模式的依赖关系"""
        # 初始状态 - 不可压缩流体
        self.on_mode_changed("不可压缩流体")    
    
    def on_mode_changed(self, mode):
        """处理计算模式变化"""
        # 隐藏所有特定参数
        self.elevation_label.setVisible(False)
        self.elevation_input.setVisible(False)
        self.elevation_hint.setVisible(False)  # 更新为标签
        
        self.adiabatic_label.setVisible(False)
        self.adiabatic_input.setVisible(False)
        self.adiabatic_combo.setVisible(False)
        
        self.pressure_label.setVisible(False)
        self.pressure_input.setVisible(False)
        self.pressure_hint.setVisible(False)  # 更新为标签
        
        # 根据模式显示相应参数
        if mode == "不可压缩流体":
            self.elevation_label.setVisible(True)
            self.elevation_input.setVisible(True)
            self.elevation_hint.setVisible(True)  # 更新为标签
        elif mode == "可压缩流体（绝热）":
            self.adiabatic_label.setVisible(True)
            self.adiabatic_input.setVisible(True)
            self.adiabatic_combo.setVisible(True)
            self.pressure_label.setVisible(True)
            self.pressure_input.setVisible(True)
            self.pressure_hint.setVisible(True)  # 更新为标签
        elif mode == "可压缩流体（等温）":
            self.pressure_label.setVisible(True)
            self.pressure_input.setVisible(True)
            self.pressure_hint.setVisible(True)  # 更新为标签
    
    def setup_roughness_options(self):
        """设置管道粗糙度选项"""
        from reference_data import ROUGHNESS_DISPLAY
        self.roughness_combo.addItems(ROUGHNESS_DISPLAY)
        self.roughness_combo.setCurrentIndex(0)
    def on_roughness_changed(self, text):
        """处理粗糙度选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.roughness_input.clear()
            return
            
        # 从文本中提取数值并填入输入框
        try:
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                roughness_value = float(match.group(1))
                self.roughness_input.setText(f"{roughness_value}")
        except:
            pass
    
    def setup_diameter_options(self):
        """设置管道内径选项（Sch 40 标准管）"""
        from reference_data import PIPE_ID_DISPLAY, PIPE_SCH40
        self.diameter_combo.addItems(PIPE_ID_DISPLAY)
        self.diameter_combo.setCurrentIndex(0)
    def on_diameter_changed(self, text):
        """处理直径选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.diameter_input.clear()
            return
            
        # 从文本中提取数值并填入输入框
        try:
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                diameter_value = float(match.group(1))
                self.diameter_input.setText(f"{diameter_value}")
        except:
            pass
    
    def setup_fluid_options(self):
        """设置流体选项（含温度级密度和动力粘度数据 - 74项）"""
        fluid_options = [
            "- 请选择流体 -",
            "水 (10°C) - 密度: 1000.0, 粘度: 1.307",
            "水 (20°C) - 密度: 998.0, 粘度: 1.004",
            "水 (30°C) - 密度: 996.0, 粘度: 0.802",
            "水 (40°C) - 密度: 992.0, 粘度: 0.662",
            "水 (50°C) - 密度: 988.0, 粘度: 0.555",
            "水 (60°C) - 密度: 983.0, 粘度: 0.475",
            "水 (70°C) - 密度: 978.0, 粘度: 0.414",
            "水 (80°C) - 密度: 972.0, 粘度: 0.365",
            "水 (90°C) - 密度: 965.0, 粘度: 0.327",
            "水 (100°C) - 密度: 958.0, 粘度: 0.295",
            "水蒸气 (20°C) - 密度: 0.748, 粘度: 0.012425",
            "空气 (0°C) - 密度: 1.293, 粘度: 0.0133",
            "空气 (10°C) - 密度: 1.2473, 粘度: 0.0142",
            "空气 (20°C) - 密度: 1.2047, 粘度: 0.0151",
            "空气 (30°C) - 密度: 1.165, 粘度: 0.016",
            "空气 (40°C) - 密度: 1.1278, 粘度: 0.0169",
            "空气 (50°C) - 密度: 1.0929, 粘度: 0.0179",
            "空气 (60°C) - 密度: 1.0601, 粘度: 0.0189",
            "空气 (70°C) - 密度: 1.0292, 粘度: 0.0199",
            "空气 (80°C) - 密度: 1.000062, 粘度: 0.0209",
            "空气 (90°C) - 密度: 0.9725, 粘度: 0.0219",
            "空气 (100°C) - 密度: 0.94646, 粘度: 0.023",
            "氨气 (20°C) - 密度: 0.708, 粘度: 0.013978",
            "二氧化碳 (20°C) - 密度: 1.83, 粘度: 0.008024",
            "一氧化碳 (20°C) - 密度: 1.164, 粘度: 0.015106",
            "氦 (20°C) - 密度: 0.166, 粘度: 0.118557",
            "氢 (20°C) - 密度: 0.084, 粘度: 0.1047",
            "甲烷 (20°C) - 密度: 0.667, 粘度: 0.016465",
            "氮 (20°C) - 密度: 1.165, 粘度: 0.015032",
            "氧 (20°C) - 密度: 1.33, 粘度: 0.015194",
            "二氧化硫 (20°C) - 密度: 2.659, 粘度: 0.004706",
            "乙醛 (20°C) - 密度: 788.0, 粘度: 0.295",
            "醋酸 (20°C) - 密度: 1048.0, 粘度: 1.232",
            "丙酮 (20°C) - 密度: 790.0, 粘度: 0.41",
            "烯丙醇 (20°C) - 密度: 852.0, 粘度: 1.603",
            "氨水 (20°C) - 密度: 829.0, 粘度: 0.265",
            "苯胺 (20°C) - 密度: 1021.0, 粘度: 4.37",
            "啤酒 (20°C) - 密度: 996.0, 粘度: 1.8",
            "苯 (20°C) - 密度: 879.0, 粘度: 0.741",
            "溴 (20°C) - 密度: 3120.0, 粘度: 0.34",
            "卤水(5%溶液) (20°C) - 密度: 1037.0, 粘度: 1.097",
            "氯化钙(5%溶液) (20°C) - 密度: 1037.0, 粘度: 1.161",
            "四氯化碳 (20°C) - 密度: 1595.0, 粘度: 0.612",
            "蓖麻油 (20°C) - 密度: 960.0, 粘度: 1017.0",
            "中国木油 (20°C) - 密度: 993.0, 粘度: 308.0",
            "棉籽油 (20°C) - 密度: 926.0, 粘度: 76.0",
            "乙醇 (20°C) - 密度: 789.0, 粘度: 1.51",
            "酒精 (20°C) - 密度: 789.0, 粘度: 1.51",
            "蚁酸 (20°C) - 密度: 1220.0, 粘度: 1.5",
            "汽油 (20°C) - 密度: 719.0, 粘度: 0.406",
            "甘油 (20°C) - 密度: 1261.0, 粘度: 1183.0",
            "庚烷 (20°C) - 密度: 682.0, 粘度: 0.6",
            "己烷 (20°C) - 密度: 658.0, 粘度: 0.51",
            "煤油 (20°C) - 密度: 804.0, 粘度: 2.4",
            "亚麻籽油 (20°C) - 密度: 920.0, 粘度: 47.0",
            "机油-光 (20°C) - 密度: 900.0, 粘度: 47.0",
            "汞 (20°C) - 密度: 13570.0, 粘度: 0.119",
            "乙酸甲酯 (20°C) - 密度: 959.0, 粘度: 0.44",
            "甲醇 (20°C) - 密度: 792.0, 粘度: 0.745",
            "牛奶 (20°C) - 密度: 1035.0, 粘度: 1.13",
            "壬 (20°C) - 密度: 717.0, 粘度: 1.0",
            "橄榄油 (20°C) - 密度: 910.0, 粘度: 91.5",
            "苯酚 (20°C) - 密度: 1078.0, 粘度: 11.3",
            "丙醇 (20°C) - 密度: 804.0, 粘度: 2.8",
            "菜籽油 (20°C) - 密度: 920.0, 粘度: 178.0",
            "SAE10油 (20°C) - 密度: 869.0, 粘度: 90.0",
            "SAE30油 (20°C) - 密度: 888.0, 粘度: 245.0",
            "海水 (10°C) - 密度: 1028.0, 粘度: 1.346",
            "海水 (20°C) - 密度: 1025.0, 粘度: 1.044",
            "氯化钠(25%溶液) (20°C) - 密度: 1190.0, 粘度: 2.4",
            "豆油 (20°C) - 密度: 926.0, 粘度: 75.0",
            "甲苯 (20°C) - 密度: 867.0, 粘度: 0.68",
            "三氯乙烯 (20°C) - 密度: 1463.0, 粘度: 0.96",
        ]
        self.fluid_combo.addItems(fluid_options)
        self.fluid_combo.setCurrentIndex(0)

        self.fluid_data = {}
        for option in fluid_options[1:]:
            parts = option.split(" - ")
            props = parts[1]
            density_str = props.split("密度: ")[1].split(", 粘度")[0]
            viscosity_str = props.split("粘度: ")[1]
            self.fluid_data[option] = (float(density_str), float(viscosity_str))
    
    def on_fluid_changed(self, text):
        """处理流体选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.fluid_input.clear()
            self.density_input.clear()
            self.viscosity_input.clear()
            return
            
        self.fluid_input.setText(text.split(" - ")[0])
        
        if text in self.fluid_data:
            density, viscosity = self.fluid_data[text]
            self.density_input.setText(f"{density:.3f}")
            self.viscosity_input.setText(f"{viscosity:.6f}")
    
    def on_adiabatic_changed(self, text):
        """处理绝热系数选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.adiabatic_input.clear()
            self.adiabatic_input.setReadOnly(True)
            self.adiabatic_input.setPlaceholderText("请选择绝热系数")
            return
            
        if "自定义" in text:
            self.adiabatic_input.setReadOnly(False)
            self.adiabatic_input.setPlaceholderText("输入自定义值")
            self.adiabatic_input.clear()
        else:
            self.adiabatic_input.setReadOnly(True)
            try:
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    adiabatic_value = float(match.group(1))
                    self.adiabatic_input.setText(f"{adiabatic_value:.2f}")
            except:
                pass
    
    def get_roughness_value(self):
        """获取粗糙度值"""
        text = self.roughness_combo.currentText()

        # 检查是否为空值选项
        if text.startswith("-") or not text.strip():
            # 如果没有选择，尝试从输入框获取
            try:
                return float(self.roughness_input.text() or 0) / 1000
            except:
                return 0.05 / 1000  # 默认值
        
        # 尝试从文本中提取数字
        try:
            # 匹配第一个数字或数字范围
            match = re.search(r'(\d+\.?\d*)(?:~(\d+\.?\d*))?', text)
            if match:
                if match.group(2):  # 有范围
                    # 取中间值
                    min_val = float(match.group(1))
                    max_val = float(match.group(2))
                    roughness_mm = (min_val + max_val) / 2
                else:  # 单个值
                    roughness_mm = float(match.group(1))
                
                return roughness_mm / 1000  # 转换为米
        except:
            pass
        
        # 如果无法解析，尝试直接转换整个文本
        try:
            # 移除单位并转换
            text_clean = text.replace("mm", "").strip()
            return float(text_clean) / 1000
        except:
            # 默认值
            return 0.05 / 1000
    
    def get_diameter_value(self):
        """获取管道内径值"""
        text = self.diameter_combo.currentText()

        # 检查是否为空值选项
        if text.startswith("-") or not text.strip():
            # 如果没有选择，尝试从输入框获取
            try:
                return float(self.diameter_input.text() or 0) / 1000
            except:
                return 0.1  # 默认值
        
        # 尝试从文本中提取数字
        try:
            # 匹配第一个数字
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                diameter_mm = float(match.group(1))
                return diameter_mm / 1000  # 转换为米
        except:
            pass
        
        # 如果无法解析，尝试直接转换整个文本
        try:
            # 移除单位并转换
            text_clean = text.replace("mm", "").strip()
            return float(text_clean) / 1000
        except:
            # 默认值
            return 0.1
    
    def get_adiabatic_value(self):
        """获取绝热系数值

        修复：原实现先解析下拉文本，选到"自定义绝热系数"时正则取不到数字、
        float("自定义绝热系数") 又抛异常，一律回落 1.4 —— 用户填的自定义 γ 被完全忽略。
        现改为输入框优先（下拉选预设时输入框已同步填入数值）。
        """
        # 输入框优先（γ ≥ 1）
        try:
            v = float(self.adiabatic_input.text())
            if v > 1.0:
                return v
        except (ValueError, TypeError):
            pass

        text = self.adiabatic_combo.currentText()
        if text.startswith("-") or not text.strip():
            return 1.4  # 默认值

        try:
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                return float(match.group(1))
        except Exception:
            pass

        try:
            return float(text)
        except Exception:
            return 1.4
    
    def select_fittings(self):
        """选择管件和阀门"""
        dialog = FittingsDialog(self)
        if dialog.exec():
            self.local_resistance_coeff = dialog.get_total_resistance()
    
    # ───────────────── 管道 SVG 示意图 ─────────────────
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        return svg_text(x, y, text, size, color, bold, center)

    def _generate_pipe_svg(self, **kw):
        w, h = 360, 260
        p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']
        cx, cy, pw, ph = w/2, h/2-10, 260, 60
        py = cy - 30
        d = kw.get("diameter", "?")
        v = kw.get("velocity", "")
        p_drop = kw.get("pressure_drop", "")
        ff = kw.get("friction_factor", "")
        p.append(f'<rect x="{cx-pw/2}" y="{py}" width="{pw}" height="{ph}" fill="#e8edf2" stroke="#4a6fa5" stroke-width="2" rx="6"/>')
        p.append(f'<rect x="{cx-pw/2+15}" y="{py+10}" width="{pw-30}" height="{ph-20}" fill="#dce4ec" stroke="#7f8c8d" stroke-width="1" rx="3"/>')
        p.append(f'<line x1="{cx-90}" y1="{cy}" x2="{cx+90}" y2="{cy}" stroke="#3498db" stroke-width="2.5" marker-end="url(#arrow)"/>')
        v_text = f"v={v} m/s" if v else "v=? m/s"
        p.append(self._text(cx, cy-10, v_text, size=10, color="#3498db", bold=True))
        d_text = f"DN{d}mm" if d and d != "?" else "DN?"
        p.append(self._text(cx, py+ph+35, d_text, size=10, color="#555"))
        info_y = h - 14
        if p_drop:
            p.append(self._text(40, info_y, f"压降: {p_drop} kPa", size=10, color="#444", center=False))
        if ff:
            p.append(self._text(w-40, info_y, f"f: {ff}", size=10, color="#444", center=False))
        p.append(self._text(cx, 12, "管路压降示意", size=10, color="#4a6fa5", bold=True))
        p.append('<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#3498db"/></marker></defs></svg>')
        return "".join(p)

    def _update_svg_diagram(self):
        try:
            kw = {}
            # 优先用计算后的存储值
            if hasattr(self, '_last_diameter') and self._last_diameter:
                kw['diameter'] = self._last_diameter
            else:
                try: kw['diameter'] = self.diameter_combo.currentText().split("mm")[0].strip()
                except: pass
            if hasattr(self, '_last_velocity') and self._last_velocity is not None:
                kw['velocity'] = round(self._last_velocity, 2)
            if hasattr(self, '_last_pressure_drop') and self._last_pressure_drop is not None:
                kw['pressure_drop'] = round(self._last_pressure_drop, 2)
            if hasattr(self, '_last_friction_factor') and self._last_friction_factor is not None:
                kw['friction_factor'] = round(self._last_friction_factor, 4)
            s = self._generate_pipe_svg(**kw)
            self.svg_widget.load(s.encode("utf-8"))
        except: pass

    def calculate_pressure_drop(self):
        """计算管道压降"""
        try:
            # 获取输入值 - 修复这里：使用按钮组而不是mode_combo
            mode = self.get_current_mode()  # 使用新的方法获取模式
            diameter = self.get_diameter_value()
            length = float(self.length_input.text() or 0)
            flow_rate = float(self.flow_input.text() or 0)
            density = float(self.density_input.text() or 0)
            # 界面输入为 mPa·s；_friction_and_reynolds 内部自行换算为 Pa·s，
            # 此处绝不能再除一次 1000（曾致雷诺数放大 1000 倍、摩擦系数落进
            # 完全粗糙区，沿程与可压缩压降系统性偏低）。显示用 Pa·s 另行换算。
            viscosity_mpas = float(self.viscosity_input.text() or 0)
            viscosity = viscosity_mpas / 1000  # Pa·s，仅用于结果展示
            roughness = self.get_roughness_value()
            
            # 可压缩模式只适用于气体（流体表里气体密度均 < 3 kg/m³）
            if mode != "不可压缩流体" and density > 100:
                QMessageBox.warning(
                    self, "输入错误",
                    "可压缩流体模式仅适用于气体介质。\n"
                    "当前所选流体密度过高（液体），请改选 水蒸气 / 空气 / 氨气 等气体，"
                    "或切换为「不可压缩流体」模式。")
                return

            # 验证输入
            if not all([diameter, length, flow_rate, density, viscosity]):
                QMessageBox.warning(self, "输入错误", "请填写所有必需参数")
                return
            
            # 流速 / 雷诺数 / 流态 / 摩擦系数（与历史记录共用同一套公式）
            velocity, reynolds, flow_regime, friction_factor = \
                self._friction_and_reynolds(diameter, flow_rate, density, viscosity_mpas, roughness)
            
            # 根据不同模式计算压降
            if mode == "不可压缩流体":
                elevation = float(self.elevation_input.text() or 0)
                
                # 计算沿程阻力损失
                pressure_drop_friction = friction_factor * (length / diameter) * (density * velocity ** 2) / 2
                
                # 计算局部阻力损失
                pressure_drop_local = self.local_resistance_coeff * (density * velocity ** 2) / 2
                
                # 计算静压头变化
                pressure_drop_elevation = density * G * elevation
                
                # 总压降
                total_pressure_drop = pressure_drop_friction + pressure_drop_local + pressure_drop_elevation
                
                result = self.format_incompressible_result(
                    mode, diameter, length, elevation, flow_rate, density, 
                    viscosity, roughness, velocity, reynolds, flow_regime, 
                    friction_factor, pressure_drop_friction, pressure_drop_local,
                    pressure_drop_elevation, total_pressure_drop
                )
                
            elif mode == "可压缩流体（绝热）":
                adiabatic_index = self.get_adiabatic_value()
                start_pressure = float(self.pressure_input.text() or 0) * 1000  # 转换为Pa

                # 入口密度 / 声速 / 马赫数 / Fanno 压降（抽为公共方法，历史记录复用）
                mach_number, total_pressure_drop, rho_in, blocked = self._adiabatic_dp(
                    adiabatic_index, start_pressure, diameter, length,
                    flow_rate, density, friction_factor)
                
                result = self.format_adiabatic_result(
                    mode, diameter, length, flow_rate, density, viscosity, 
                    roughness, adiabatic_index, start_pressure/1000, velocity, 
                    reynolds, flow_regime, friction_factor, mach_number, 
                    total_pressure_drop, rho_in=rho_in, blocked=blocked
                )
                
            elif mode == "可压缩流体（等温）":
                start_pressure = float(self.pressure_input.text() or 0) * 1000  # 转换为Pa

                # 等温可压缩流动（忽略加速项），R 由标准状态密度反推；
                # 若用起始压力反推，高压工况下会把 R 一并放大，压降严重失真。
                total_pressure_drop, rho_in, blocked = self._isothermal_dp(
                    start_pressure, diameter, length, flow_rate, density, friction_factor)

                result = self.format_isothermal_result(
                    mode, diameter, length, flow_rate, density, viscosity,
                    roughness, start_pressure/1000, velocity, reynolds,
                    flow_regime, friction_factor, total_pressure_drop,
                    rho_in=rho_in, blocked=blocked
                )
            
            self.result_text.setText(result)

            self._last_diameter = int(diameter * 1000)
            self._last_velocity = velocity
            self._last_pressure_drop = total_pressure_drop / 1000  # Pa -> kPa
            self._last_friction_factor = friction_factor
            self._update_svg_diagram()
            
        except ValueError as e:
            QMessageBox.critical(self, "计算错误", f"参数输入格式错误: {str(e)}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "参数不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def clear_inputs(self):
        """清空所有输入（恢复出厂默认值，保证清空后可直接重算）"""
        # 先复位下拉（会触发联动清空输入框），再回填默认文本
        self.roughness_combo.setCurrentIndex(0)
        self.diameter_combo.setCurrentIndex(0)
        self.fluid_combo.setCurrentIndex(0)
        self.adiabatic_combo.setCurrentIndex(0)
        self.roughness_input.setText("0.2")
        self.diameter_input.setText("100")
        self.length_input.setText("300")
        self.flow_input.setText("5172")
        self.density_input.clear()
        self.viscosity_input.clear()
        self.elevation_input.setText("0")
        self.pressure_input.setText("101.3")
        self.adiabatic_input.clear()
        self.result_text.clear()
        self.local_resistance_coeff = 0.0
        self._update_svg_diagram()

    def _get_history_data(self):
        """提供历史记录所需的输入输出数据"""
        mode = self.get_current_mode()
        diameter = self.get_diameter_value()
        length = float(self.length_input.text() or 0)
        flow_rate = float(self.flow_input.text() or 0)
        density = float(self.density_input.text() or 0)
        viscosity = float(self.viscosity_input.text() or 0)
        roughness = self.get_roughness_value()

        inputs = {
            "计算模式": mode,
            "管道内径": f"{diameter*1000:.1f} mm",
            "管道内径原始值(m)": diameter,
            "管道长度": f"{length} m",
            "流体流量": f"{flow_rate} m\u00b3/h",
            "流体密度": f"{density:.3f} kg/m\u00b3",
            "动力粘度": f"{viscosity:.4f} mPa\u00b7s",
            "管道粗糙度": f"{roughness*1000:.3f} mm",
            "流体类型": self.fluid_combo.currentText(),
        }

        outputs = {}
        raw_results = {}

        if mode == "不可压缩流体":
            elevation = float(self.elevation_input.text() or 0)
            inputs["标高变化"] = f"{elevation} m"
            velocity, reynolds, _, friction_factor = self._friction_and_reynolds(
                diameter, flow_rate, density, viscosity, roughness)
            pd_friction = friction_factor * (length / diameter) * (density * velocity ** 2) / 2
            pd_local = self.local_resistance_coeff * (density * velocity ** 2) / 2
            pd_elevation = density * G * elevation
            total = pd_friction + pd_local + pd_elevation
            inputs["局部阻力系数"] = self.local_resistance_coeff
            raw_results = {
                "流速(m/s)": velocity, "雷诺数": reynolds,
                "摩擦系数": friction_factor,
                "沿程损失(kPa)": pd_friction/1000,
                "局部损失(kPa)": pd_local/1000,
                "静压头变化(kPa)": pd_elevation/1000,
                "总压降(kPa)": total/1000,
                "总压降(Pa)": total,
            }
        elif mode == "可压缩流体（绝热）":
            adiabatic = self.get_adiabatic_value()
            pressure = float(self.pressure_input.text() or 0)
            inputs["绝热系数"] = adiabatic
            inputs["起点压力"] = f"{pressure} kPa"
            # 与主计算共用同一套公式（原实现另用 287·293 与经验压比，结果对不上）
            velocity, reynolds, _, friction_factor = self._friction_and_reynolds(
                diameter, flow_rate, density, viscosity, roughness)
            mach, total, _, _ = self._adiabatic_dp(
                adiabatic, pressure * 1000, diameter, length,
                flow_rate, density, friction_factor)
            raw_results = {
                "流速(m/s)": velocity, "雷诺数": reynolds,
                "摩擦系数": friction_factor, "马赫数": mach,
                "总压降(kPa)": total/1000,
            }
        else:  # 可压缩流体（等温）
            pressure = float(self.pressure_input.text() or 0)
            inputs["起点压力"] = f"{pressure} kPa"
            velocity, reynolds, _, friction_factor = self._friction_and_reynolds(
                diameter, flow_rate, density, viscosity, roughness)
            # 原实现此处沿用不可压缩 Darcy 式，与主计算的等温可压缩式不一致
            total, _, _ = self._isothermal_dp(
                pressure * 1000, diameter, length, flow_rate, density, friction_factor)
            raw_results = {
                "流速(m/s)": velocity, "雷诺数": reynolds,
                "摩擦系数": friction_factor,
                "总压降(kPa)": total/1000,
            }

        for k, v in raw_results.items():
            if isinstance(v, float):
                outputs[k] = round(v, 6)
            else:
                outputs[k] = v

        return {"inputs": inputs, "outputs": outputs}

    def format_incompressible_result(self, mode, diameter, length, elevation, flow_rate, 
                                   density, viscosity, roughness, velocity, reynolds, 
                                   flow_regime, friction_factor, pressure_drop_friction, 
                                   pressure_drop_local, pressure_drop_elevation, total_pressure_drop):
        """格式化不可压缩流体计算结果"""
        return f"""═══════════
 输入参数
══════════

    计算模式: {mode}
    管道内径: {diameter*1000:.1f} mm
    管道长度: {length} m
    标高变化: {elevation} m
    流体流量: {flow_rate} m³/h
    流体密度: {density:.3f} kg/m³
    流体粘度: {viscosity*1000:.6f} mPa·s
    管道粗糙度: {roughness*1000:.3f} mm
    局部阻力系数: {self.local_resistance_coeff:.3f}

══════════
计算结果
══════════

    流动特性:
    • 流速: {velocity:.2f} m/s
    • 雷诺数: {reynolds:.0f}
    • 流态: {flow_regime}
    • 摩擦系数: {friction_factor:.6f}

    压力损失分析:
    • 沿程阻力损失: {pressure_drop_friction/1000:.3f} kPa
    • 局部阻力损失: {pressure_drop_local/1000:.3f} kPa
    • 静压头变化: {pressure_drop_elevation/1000:.3f} kPa
    • 总压力损失: {total_pressure_drop/1000:.3f} kPa

    单位换算:
    • 总压力损失: {total_pressure_drop:.1f} Pa
    • 总压力损失: {total_pressure_drop/100000:.6f} bar

══════════
计算说明
══════════

    • 使用Darcy-Weisbach公式计算沿程阻力
    • 局部阻力基于选择的管件和阀门计算
    • 考虑了标高变化对静压的影响
    • 结果仅供参考，实际应用请考虑安全系数"""
    
    def format_adiabatic_result(self, mode, diameter, length, flow_rate, density, 
                              viscosity, roughness, adiabatic_index, start_pressure, 
                              velocity, reynolds, flow_regime, friction_factor, 
                              mach_number, total_pressure_drop, rho_in=None,
                              blocked=False):
        """格式化绝热流动计算结果"""
        rho_line = (f"    入口密度(@起始压力): {rho_in:.4f} kg/m³\n"
                    f"    标准状态密度(20°C,101.3kPa): {density:.4f} kg/m³\n"
                    if rho_in else f"    流体密度: {density:.3f} kg/m³\n")
        blocked_line = ("\n    ⚠ 阻塞流：该管长已超过临界长度 L*，出口锁在声速截面，\n"
                        "      按此流量实际无法通过，需加大管径或降低流量！\n"
                        if blocked else "")
        return f"""
══════════
 输入参数
══════════

    计算模式: {mode}
    管道内径: {diameter*1000:.1f} mm
    管道长度: {length} m
    流体流量: {flow_rate} m³/h（入口状态）
{rho_line}    流体粘度: {viscosity*1000:.6f} mPa·s
    管道粗糙度: {roughness*1000:.3f} mm
    绝热系数: {adiabatic_index:.2f}
    起始压力: {start_pressure:.1f} kPa（绝压）

══════════
计算结果
══════════

    流动特性:
    • 流速: {velocity:.2f} m/s
    • 雷诺数: {reynolds:.0f}
    • 流态: {flow_regime}
    • 摩擦系数: {friction_factor:.6f}
    • 马赫数: {mach_number:.4f}{blocked_line}
    压力损失分析:
    • 总压力损失: {total_pressure_drop/1000:.3f} kPa
    • 压降百分比: {total_pressure_drop/(start_pressure*1000)*100:.2f} %

    单位换算:
    • 总压力损失: {total_pressure_drop:.1f} Pa
    • 总压力损失: {total_pressure_drop/100000:.6f} bar

══════════
计算说明
══════════

    • 使用绝热流动(Fanno流动)关系式计算
    • 入口密度按理想气体由起始压力换算（流体表密度为标准状态值）
    • 结果仅供参考，实际应用请考虑安全系数"""
    
    def format_isothermal_result(self, mode, diameter, length, flow_rate, density, 
                               viscosity, roughness, start_pressure, velocity, 
                               reynolds, flow_regime, friction_factor, total_pressure_drop,
                               rho_in=None, blocked=False):
        """格式化等温流动计算结果"""
        rho_line = (f"    入口密度(@起始压力): {rho_in:.4f} kg/m³\n"
                    f"    标准状态密度(20°C,101.3kPa): {density:.4f} kg/m³\n"
                    if rho_in else f"    流体密度: {density:.3f} kg/m³\n")
        blocked_line = ("\n    ⚠ 阻塞流：P1²−(f·L/D)·G²RT ≤ 0，该管长无法通过此流量，\n"
                        "      需加大管径或降低流量！\n"
                        if blocked else "")
        return f"""
══════════
 输入参数
══════════

    计算模式: {mode}
    管道内径: {diameter*1000:.1f} mm
    管道长度: {length} m
    流体流量: {flow_rate} m³/h（入口状态）
{rho_line}    流体粘度: {viscosity*1000:.6f} mPa·s
    管道粗糙度: {roughness*1000:.3f} mm
    起始压力: {start_pressure:.1f} kPa（绝压）

══════════
计算结果
══════════

    流动特性:
    • 流速: {velocity:.2f} m/s
    • 雷诺数: {reynolds:.0f}
    • 流态: {flow_regime}
    • 摩擦系数: {friction_factor:.6f}{blocked_line}
    压力损失分析:
    • 总压力损失: {total_pressure_drop/1000:.3f} kPa
    • 压降百分比: {total_pressure_drop/(start_pressure*1000)*100:.2f} %

    单位换算:
    • 总压力损失: {total_pressure_drop:.1f} Pa
    • 总压力损失: {total_pressure_drop/100000:.6f} bar

══════════
计算说明
══════════

    • 使用等温流动公式 P1²−P2²=(f·L/D)·G²RT 计算（忽略加速项）
    • 假设气体温度恒定 20°C，入口密度按理想气体换算
    • 结果仅供参考，实际应用请考虑安全系数"""
    
    def solve_colebrook(self, relative_roughness, reynolds):
        """使用迭代法求解Colebrook-White方程"""
        # 初始猜测值
        f = 0.02
        for i in range(100):
            f_new = 1 / (-2 * math.log10(relative_roughness/3.7 + 2.51/(reynolds * math.sqrt(f)))) ** 2
            if abs(f_new - f) < 1e-8:
                return f_new
            f = f_new
        return f

    # ── 气体入口状态（理想气体） ────────────────────────────────
    # 流体表里的气体密度均为 101.325 kPa / 20 °C 的标准状态值，
    # 直接拿去算高压管道的声速/质量流量会整体失真，故统一在此换算入口密度。
    GAS_T_REF_K = 293.15

    def _gas_R(self, density):
        """由所选流体的标准状态密度反推气体常数 R = P/(ρT)，J/(kg·K)"""
        return 101325.0 / (max(density, 1e-9) * self.GAS_T_REF_K)

    def _gas_inlet_density(self, density, p_pa):
        """按理想气体计算入口压力下的气体密度，kg/m³"""
        return p_pa / (self._gas_R(density) * self.GAS_T_REF_K)

    # ── 水力计算公共方法（主计算与历史记录共用，避免两套公式各行其是） ──

    def _friction_and_reynolds(self, diameter, flow_rate, density, viscosity, roughness):
        """返回 (流速 m/s, 雷诺数, 流态, 摩擦系数)

        参数口径（务必遵守，历史上这里踩过坑）：
            diameter  : m
            flow_rate : m³/h（标况/入口状态）
            density   : kg/m³
            viscosity : **mPa·s**（界面输入口径，本方法内部除 1000 转 Pa·s）
            roughness : m（绝对粗糙度，界面 mm 已由 get_roughness_value 折算）
        """
        area = math.pi * (diameter / 2) ** 2
        velocity = (flow_rate / 3600.0) / area          # m³/h -> m³/s
        viscosity_pa = viscosity / 1000.0               # mPa·s -> Pa·s
        reynolds = (density * velocity * diameter) / viscosity_pa
        if reynolds < 2000:
            friction_factor = 64 / reynolds
            flow_regime = "层流"
        elif reynolds < 4000:
            # 过渡区：Swamee-Jain 显式近似
            friction_factor = 0.25 / (math.log10(
                roughness / (3.7 * diameter) + 5.74 / reynolds ** 0.9)) ** 2
            flow_regime = "过渡流"
        else:
            friction_factor = self.solve_colebrook(roughness / diameter, reynolds)
            flow_regime = "湍流"
        return velocity, reynolds, flow_regime, friction_factor

    @staticmethod
    def _fanno_param(mach, gamma):
        """Fanno 参数 4fL*/D"""
        if mach <= 0 or mach >= 1:
            return float('inf')
        term1 = (1 - mach ** 2) / (gamma * mach ** 2)
        term2 = (gamma + 1) / (2 * gamma) * math.log(
            mach ** 2 * (gamma + 1) / (2 + (gamma - 1) * mach ** 2))
        return term1 + term2

    @classmethod
    def _fanno_mach_from_param(cls, param, gamma, mach_guess=0.5):
        """由 Fanno 参数反求 Mach 数（Newton-Raphson）"""
        M = mach_guess
        for _ in range(50):
            fp = cls._fanno_param(M, gamma)
            dm = 1e-6
            fp_plus = cls._fanno_param(M + dm, gamma)
            dfp = (fp_plus - fp) / dm
            if abs(dfp) < 1e-12:
                break
            M_new = M - (fp - param) / dfp
            M_new = min(max(M_new, 0.001), 0.999)
            if abs(M_new - M) < 1e-8:
                M = M_new
                break
            M = M_new
        return M

    @staticmethod
    def _fanno_p_ratio(mach, gamma):
        """Fanno 流 P/P* 关系"""
        return (1 / mach) * math.sqrt(
            (2 + (gamma - 1) * mach ** 2) / (gamma + 1))

    def _adiabatic_dp(self, gamma, p1, diameter, length, flow_rate, density,
                      friction_factor):
        """绝热（Fanno）流动压降

        返回 (入口马赫数, 压降 Pa, 入口密度 kg/m³, 是否阻塞)
        """
        rho_in = self._gas_inlet_density(density, p1)
        area = math.pi * (diameter / 2) ** 2
        velocity = (flow_rate / 3600.0) / area
        mach = velocity / math.sqrt(gamma * p1 / rho_in)

        # 声速截面压力比 P*/P1（阻塞时出口锁在 M=1 截面）
        p_star_ratio = mach * math.sqrt(
            (gamma + 1.0) / (2.0 + (gamma - 1.0) * mach ** 2))

        if mach >= 1.0:
            # 入口已声速/超音速，亚音速 Fanno 模型不适用
            return mach, p1 * (1.0 - p_star_ratio), rho_in, True

        fanno_out = self._fanno_param(mach, gamma) - 4 * friction_factor * length / diameter
        if fanno_out <= 0:
            # 管长超过临界长度 L* → 阻塞
            return mach, p1 * (1.0 - p_star_ratio), rho_in, True

        m_out = self._fanno_mach_from_param(fanno_out, gamma, max(mach * 0.9, 0.1))
        p_exit = p1 / self._fanno_p_ratio(mach, gamma) * self._fanno_p_ratio(m_out, gamma)
        return mach, p1 - p_exit, rho_in, False

    def _isothermal_dp(self, p1, diameter, length, flow_rate, density, friction_factor):
        """等温可压缩流动压降：P1² − P2² = (f·L/D)·G²·R·T

        返回 (压降 Pa, 入口密度 kg/m³, 是否阻塞)
        """
        rho_in = self._gas_inlet_density(density, p1)
        area = math.pi * (diameter / 2) ** 2
        mass_flux = rho_in * (flow_rate / 3600.0) / area       # kg/(m²·s)
        term = ((friction_factor * length / diameter) * mass_flux ** 2
                * self._gas_R(density) * self.GAS_T_REF_K)
        p2_sq = p1 ** 2 - term
        if p2_sq <= 0:
            return p1, rho_in, True
        return p1 - math.sqrt(p2_sq), rho_in, False

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
        try:
            # 获取当前结果文本
            result_text = self.result_text.toPlainText()
            
            # 更宽松的检查条件：只要结果文本不为空且包含计算结果的关键字
            if not result_text or ("计算结果" not in result_text and "压力损失" not in result_text):
                QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
                return ""
                
            # 获取工程信息
            project_info = self.get_project_info()
            
            # 添加报告头信息
            report = f"""工程计算书 - 管道压降计算
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
计算工具: ChemCal 工程计算模块
========================================

"""
            report += result_text
            
            # 添加工程信息部分
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

    计算书编号: PD-{datetime.now().strftime('%Y%m%d')}-001
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
            return ""

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "压降计算")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "压降计算")

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = 压降计算()
    calculator.resize(1200, 800)
    calculator.show()
    
    sys.exit(app.exec())