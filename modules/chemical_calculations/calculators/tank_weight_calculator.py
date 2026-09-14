from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox,
    QScrollArea, QButtonGroup, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
import math

from utils.docx_utils import ReportExporter
from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        MODE_BUTTON_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase


class 罐体重量(CalculatorBase):
    """罐体重量计算器（与压降计算UI完全一致）"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        
        # 使用传入的数据管理器或创建新的
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        
        self.setup_ui()

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
        """设置与压降计算完全一致的UI布局"""
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
            "计算各种类型罐体的重量，包括空罐重量、液体重量和总重量。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 2. 罐体类型选择
        type_group = CalculatorBase.make_group_box("罐体类型")
        type_layout = QHBoxLayout(type_group)
        
        self.type_button_group = QButtonGroup(self)
        
        tank_types = [
            ("锥体罐", "圆锥底垂直储罐"),
            ("平底罐", "平底垂直储罐"),
            ("椭圆底罐", "椭圆封头储罐"),
            ("卧式罐", "卧式圆柱储罐"),
            ("球罐", "球形储罐")
        ]
        
        for i, (type_name, tooltip) in enumerate(tank_types):
            btn = CalculatorBase.make_mode_button(type_name, tooltip)
            self.type_button_group.addButton(btn, i)
            type_layout.addWidget(btn)
        
        # 默认选择第一个
        self.type_button_group.button(0).setChecked(True)
        self.type_button_group.buttonClicked.connect(self.on_tank_type_changed)
        
        left_layout.addWidget(type_group)
        
        # 3. 输入参数组 - 使用GridLayout实现整齐的布局
        input_group = CalculatorBase.make_group_box("尺寸参数")
        
        # 使用GridLayout确保整齐排列
        self.input_layout = QGridLayout(input_group)
        self.input_layout.setVerticalSpacing(12)
        self.input_layout.setHorizontalSpacing(10)
        self.input_layout.setColumnStretch(0, 4)
        self.input_layout.setColumnStretch(1, 8)
        self.input_layout.setColumnStretch(2, 5)
        
        # 标签样式 - 右对齐（统一标准）
        label_style = INPUT_LABEL_STYLE
        
        # 输入框和下拉菜单的固定宽度
        
        # 第一列：参数名称（右对齐）
        # 第二列：输入框（固定宽度）
        # 第三列：下拉菜单或提示标签（固定宽度）
        
        row = 0
        
        # 筒体外径 - 所有罐体类型都需要
        diameter_label = QLabel("筒体外径 D (mm):")
        diameter_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        diameter_label.setStyleSheet(label_style)
        self.input_layout.addWidget(diameter_label, row, 0)
        
        self.diameter_input = QLineEdit("3000")
        self.diameter_input.setPlaceholderText("例如: 3000")
        self.diameter_input.setValidator(QDoubleValidator(0.1, 50000.0, 2))
        self.diameter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.input_layout.addWidget(self.diameter_input, row, 1)
        
        self.diameter_hint = QLabel("直接输入直径值")
        self.diameter_hint.setStyleSheet("font-style: italic;")
        self.input_layout.addWidget(self.diameter_hint, row, 2)
        
        row += 1
        
        # 筒体高度 - 锥体罐、平底罐、椭圆底罐需要
        self.height_label = QLabel("筒体高度 H (mm):")
        self.height_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.height_label.setStyleSheet(label_style)
        self.input_layout.addWidget(self.height_label, row, 0)
        
        self.height_input = QLineEdit("5000")
        self.height_input.setPlaceholderText("例如: 5000")
        self.height_input.setValidator(QDoubleValidator(0.1, 50000.0, 2))
        self.height_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.input_layout.addWidget(self.height_input, row, 1)
        
        self.height_hint = QLabel("直接输入高度值")
        self.height_hint.setStyleSheet("font-style: italic;")
        self.input_layout.addWidget(self.height_hint, row, 2)
        
        row += 1
        
        # 筒体壁厚 - 锥体罐、平底罐、椭圆底罐、卧式罐需要
        self.shell_thickness_label = QLabel("筒体壁厚 (mm):")
        self.shell_thickness_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.shell_thickness_label.setStyleSheet(label_style)
        self.input_layout.addWidget(self.shell_thickness_label, row, 0)
        
        self.shell_thickness_input = QLineEdit("6.0")
        self.shell_thickness_input.setPlaceholderText("例如: 6.0")
        self.shell_thickness_input.setValidator(QDoubleValidator(1.0, 100.0, 1))
        self.shell_thickness_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.input_layout.addWidget(self.shell_thickness_input, row, 1)
        
        self.shell_thickness_hint = QLabel("直接输入壁厚值")
        self.shell_thickness_hint.setStyleSheet("font-style: italic;")
        self.input_layout.addWidget(self.shell_thickness_hint, row, 2)
        
        row += 1
        
        # 锥体高度 - 仅锥体罐需要
        self.cone_height_label = QLabel("锥体高度 h (mm):")
        self.cone_height_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cone_height_label.setStyleSheet(label_style)
        self.input_layout.addWidget(self.cone_height_label, row, 0)
        
        self.cone_height_input = QLineEdit("1200")
        self.cone_height_input.setPlaceholderText("例如: 1200")
        self.cone_height_input.setValidator(QDoubleValidator(0.1, 10000.0, 2))
        self.cone_height_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.input_layout.addWidget(self.cone_height_input, row, 1)
        
        self.cone_height_hint = QLabel("直接输入锥体高度")
        self.cone_height_hint.setStyleSheet("font-style: italic;")
        self.input_layout.addWidget(self.cone_height_hint, row, 2)
        
        row += 1
        
        # 锥口直径 - 仅锥体罐需要
        self.nozzle_diameter_label = QLabel("锥口直径 d (mm):")
        self.nozzle_diameter_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.nozzle_diameter_label.setStyleSheet(label_style)
        self.input_layout.addWidget(self.nozzle_diameter_label, row, 0)
        
        self.nozzle_diameter_input = QLineEdit("100")
        self.nozzle_diameter_input.setPlaceholderText("例如: 100")
        self.nozzle_diameter_input.setValidator(QDoubleValidator(0.01, 50000.0, 3))
        self.nozzle_diameter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.input_layout.addWidget(self.nozzle_diameter_input, row, 1)
        
        self.nozzle_diameter_hint = QLabel("直接输入锥口直径")
        self.nozzle_diameter_hint.setStyleSheet("font-style: italic;")
        self.input_layout.addWidget(self.nozzle_diameter_hint, row, 2)
        
        row += 1
        
        # 筒体长度 - 仅卧式罐需要
        self.length_label = QLabel("筒体长度 L (mm):")
        self.length_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.length_label.setStyleSheet(label_style)
        self.input_layout.addWidget(self.length_label, row, 0)
        
        self.length_input = QLineEdit("5000")
        self.length_input.setPlaceholderText("例如: 5000")
        self.length_input.setValidator(QDoubleValidator(0.1, 50000.0, 2))
        self.length_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.input_layout.addWidget(self.length_input, row, 1)
        
        self.length_hint = QLabel("直接输入长度值")
        self.length_hint.setStyleSheet("font-style: italic;")
        self.input_layout.addWidget(self.length_hint, row, 2)
        
        row += 1
        
        # 液位高度 - 卧式罐、球罐需要
        self.liquid_level_label = QLabel("液位高度 h (mm):")
        self.liquid_level_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.liquid_level_label.setStyleSheet(label_style)
        self.input_layout.addWidget(self.liquid_level_label, row, 0)
        
        self.liquid_level_input = QLineEdit("1000")
        self.liquid_level_input.setPlaceholderText("例如: 1000")
        self.liquid_level_input.setValidator(QDoubleValidator(0.0, 50000.0, 2))
        self.liquid_level_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.input_layout.addWidget(self.liquid_level_input, row, 1)
        
        self.liquid_level_hint = QLabel("直接输入液位高度")
        self.liquid_level_hint.setStyleSheet("font-style: italic;")
        self.input_layout.addWidget(self.liquid_level_hint, row, 2)
        
        row += 1
        
        # 球体壁厚 - 仅球罐需要
        self.sphere_thickness_label = QLabel("球体壁厚 (mm):")
        self.sphere_thickness_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.sphere_thickness_label.setStyleSheet(label_style)
        self.input_layout.addWidget(self.sphere_thickness_label, row, 0)
        
        self.sphere_thickness_input = QLineEdit("6.0")
        self.sphere_thickness_input.setPlaceholderText("例如: 6.0")
        self.sphere_thickness_input.setValidator(QDoubleValidator(1.0, 100.0, 1))
        self.sphere_thickness_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.input_layout.addWidget(self.sphere_thickness_input, row, 1)
        
        self.sphere_thickness_hint = QLabel("直接输入壁厚值")
        self.sphere_thickness_hint.setStyleSheet("font-style: italic;")
        self.input_layout.addWidget(self.sphere_thickness_hint, row, 2)
        
        left_layout.addWidget(input_group)
        
        # 4. 材料参数组
        material_group = CalculatorBase.make_group_box("材料参数")
        
        material_layout = QGridLayout(material_group)
        material_layout.setVerticalSpacing(12)
        material_layout.setHorizontalSpacing(10)
        material_layout.setColumnStretch(0, 4)
        material_layout.setColumnStretch(1, 8)
        material_layout.setColumnStretch(2, 5)
        
        label_style = INPUT_LABEL_STYLE
        
        row = 0

        # 罐体密度
        density_label = QLabel("罐体密度 (kg/m³):")
        density_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        density_label.setStyleSheet(label_style)
        material_layout.addWidget(density_label, row, 0)
        
        self.density_input = QLineEdit("7930")
        self.density_input.setPlaceholderText("例如: 7930")
        self.density_input.setValidator(QDoubleValidator(100, 20000, 2))
        self.density_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        material_layout.addWidget(self.density_input, row, 1)
        
        self.material_combo = QComboBox()
        self.material_combo.setStyleSheet(COMBOBOX_STYLE)
        self.material_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.material_combo.addItems([
            "- 请选择材料 -",
            "304不锈钢 - 密度: 7930 kg/m³",
            "316不锈钢 - 密度: 7980 kg/m³", 
            "碳钢 - 密度: 7850 kg/m³",
            "玻璃钢（FRP） - 密度: 2000 kg/m³",
            "聚氯乙烯（PVC） - 密度: 1400 kg/m³",
            "聚乙烯(PE) - 密度: 970 kg/m³",
            "铝 - 密度: 2850 kg/m³",
            "钛合金 - 密度: 4510 kg/m³",
            "自定义材料"
        ])
        self.material_combo.currentTextChanged.connect(self.on_material_changed)
        material_layout.addWidget(self.material_combo, row, 2)
        
        row += 1
        
        # 液体密度
        liquid_density_label = QLabel("液体密度 (kg/m³):")
        liquid_density_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        liquid_density_label.setStyleSheet(label_style)
        material_layout.addWidget(liquid_density_label, row, 0)
        
        self.liquid_density_input = QLineEdit("1000")
        self.liquid_density_input.setPlaceholderText("例如: 1000")
        self.liquid_density_input.setValidator(QDoubleValidator(0, 2000, 0))
        self.liquid_density_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        material_layout.addWidget(self.liquid_density_input, row, 1)
        
        self.liquid_density_hint = QLabel("水: 1000 kg/m³")
        self.liquid_density_hint.setStyleSheet("font-style: italic;")
        material_layout.addWidget(self.liquid_density_hint, row, 2)
        
        left_layout.addWidget(material_group)
        
        # 在底部添加拉伸因子
        left_layout.addStretch()
        
        # 右侧：结果显示区域 (占1/3宽度)
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        
        # 结果显示
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
        calc_btn.clicked.connect(self.calculate_weight)
        right_layout.addWidget(calc_btn)
        
        # 将左右两部分添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)  # 左侧占2/3
        main_layout.addWidget(right_widget, 1)  # 右侧占1/3
        
        # 设置初始状态 - 锥体罐
        self.on_tank_type_changed(self.type_button_group.checkedButton())
    
    def get_current_tank_type(self):
        """获取当前选择的罐体类型"""
        checked_button = self.type_button_group.checkedButton()
        if checked_button:
            return checked_button.text()
        return "锥体罐"  # 默认值
    
    def on_tank_type_changed(self, button):
        """处理罐体类型变化 - 动态显示/隐藏参数行"""
        tank_type = button.text() if button else "锥体罐"
        
        # 隐藏所有特定参数行
        self.height_label.setVisible(False)
        self.height_input.setVisible(False)
        self.height_hint.setVisible(False)
        
        self.shell_thickness_label.setVisible(False)
        self.shell_thickness_input.setVisible(False)
        self.shell_thickness_hint.setVisible(False)
        
        self.cone_height_label.setVisible(False)
        self.cone_height_input.setVisible(False)
        self.cone_height_hint.setVisible(False)
        
        self.nozzle_diameter_label.setVisible(False)
        self.nozzle_diameter_input.setVisible(False)
        self.nozzle_diameter_hint.setVisible(False)
        
        self.length_label.setVisible(False)
        self.length_input.setVisible(False)
        self.length_hint.setVisible(False)
        
        self.liquid_level_label.setVisible(False)
        self.liquid_level_input.setVisible(False)
        self.liquid_level_hint.setVisible(False)
        
        self.sphere_thickness_label.setVisible(False)
        self.sphere_thickness_input.setVisible(False)
        self.sphere_thickness_hint.setVisible(False)
        
        # 根据罐体类型显示相应参数行
        if tank_type == "锥体罐":
            self.height_label.setVisible(True)
            self.height_input.setVisible(True)
            self.height_hint.setVisible(True)
            
            self.shell_thickness_label.setVisible(True)
            self.shell_thickness_input.setVisible(True)
            self.shell_thickness_hint.setVisible(True)
            
            self.cone_height_label.setVisible(True)
            self.cone_height_input.setVisible(True)
            self.cone_height_hint.setVisible(True)
            
            self.nozzle_diameter_label.setVisible(True)
            self.nozzle_diameter_input.setVisible(True)
            self.nozzle_diameter_hint.setVisible(True)
            
        elif tank_type == "平底罐":
            self.height_label.setVisible(True)
            self.height_input.setVisible(True)
            self.height_hint.setVisible(True)
            
            self.shell_thickness_label.setVisible(True)
            self.shell_thickness_input.setVisible(True)
            self.shell_thickness_hint.setVisible(True)
            
        elif tank_type == "椭圆底罐":
            self.height_label.setVisible(True)
            self.height_input.setVisible(True)
            self.height_hint.setVisible(True)
            
            self.shell_thickness_label.setVisible(True)
            self.shell_thickness_input.setVisible(True)
            self.shell_thickness_hint.setVisible(True)
            
        elif tank_type == "卧式罐":
            self.shell_thickness_label.setVisible(True)
            self.shell_thickness_input.setVisible(True)
            self.shell_thickness_hint.setVisible(True)
            
            self.length_label.setVisible(True)
            self.length_input.setVisible(True)
            self.length_hint.setVisible(True)
            
            self.liquid_level_label.setVisible(True)
            self.liquid_level_input.setVisible(True)
            self.liquid_level_hint.setVisible(True)
            
        elif tank_type == "球罐":
            self.liquid_level_label.setVisible(True)
            self.liquid_level_input.setVisible(True)
            self.liquid_level_hint.setVisible(True)
            
            self.sphere_thickness_label.setVisible(True)
            self.sphere_thickness_input.setVisible(True)
            self.sphere_thickness_hint.setVisible(True)
    
    def on_material_changed(self, text):
        """处理材料选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            return
            
        if "自定义" in text:
            # 自定义材料，不清空输入框，用户可以手动输入
            # 可以在这里可选地清除密度输入框或保持原值
            # self.density_input.clear()
            pass
        else:
            try:
                # 从文本中提取密度值
                import re
                match = re.search(r'密度:\s*(\d+)', text)
                if match:
                    density_value = float(match.group(1))
                    self.density_input.setText(f"{density_value}")
            except:
                pass
    
    def calculate_weight(self):
        """计算罐体重量"""
        try:
            tank_type = self.get_current_tank_type()
            diameter = float(self.diameter_input.text() or 0) / 1000
            material_density = float(self.density_input.text() or 0)
            liquid_density = float(self.liquid_density_input.text() or 0)
            
            # 验证输入
            if not all([diameter, material_density, liquid_density]):
                QMessageBox.warning(self, "输入错误", "请填写所有必需参数")
                return
            
            if tank_type == "锥体罐":
                height = float(self.height_input.text() or 0) / 1000
                shell_thickness = float(self.shell_thickness_input.text() or 0) / 1000
                cone_height = float(self.cone_height_input.text() or 0) / 1000
                nozzle_diameter = float(self.nozzle_diameter_input.text() or 0) / 1000
                
                # 计算锥体罐重量
                tank_weight = self.calculate_cone_tank_weight(
                    diameter, height, shell_thickness, cone_height, nozzle_diameter, material_density
                )
                
                # 计算液体重量
                liquid_weight = self.calculate_cone_liquid_weight(
                    diameter, height, cone_height, nozzle_diameter, liquid_density
                )
                
            elif tank_type == "平底罐":
                height = float(self.height_input.text() or 0) / 1000
                shell_thickness = float(self.shell_thickness_input.text() or 0) / 1000
                
                # 计算平底罐重量
                tank_weight = self.calculate_flat_tank_weight(
                    diameter, height, shell_thickness, material_density
                )
                
                # 计算液体重量
                liquid_weight = self.calculate_flat_liquid_weight(
                    diameter, height, liquid_density
                )
                
            elif tank_type == "椭圆底罐":
                height = float(self.height_input.text() or 0) / 1000
                shell_thickness = float(self.shell_thickness_input.text() or 0) / 1000
                
                # 计算椭圆底罐重量
                tank_weight = self.calculate_elliptic_tank_weight(
                    diameter, height, shell_thickness, material_density
                )
                
                # 计算液体重量
                liquid_weight = self.calculate_elliptic_liquid_weight(
                    diameter, height, liquid_density
                )
                
            elif tank_type == "卧式罐":
                length = float(self.length_input.text() or 0) / 1000
                shell_thickness = float(self.shell_thickness_input.text() or 0) / 1000
                liquid_level = float(self.liquid_level_input.text() or 0) / 1000
                
                # 计算卧式罐重量
                tank_weight = self.calculate_horizontal_tank_weight(
                    diameter, length, shell_thickness, material_density
                )
                
                # 计算液体重量
                liquid_weight = self.calculate_horizontal_liquid_weight(
                    diameter, length, liquid_level, liquid_density
                )
                
            elif tank_type == "球罐":
                liquid_level = float(self.liquid_level_input.text() or 0) / 1000
                sphere_thickness = float(self.sphere_thickness_input.text() or 0) / 1000
                
                # 计算球罐重量
                tank_weight = self.calculate_sphere_tank_weight(
                    diameter, sphere_thickness, material_density
                )
                
                # 计算液体重量
                liquid_weight = self.calculate_sphere_liquid_weight(
                    diameter, liquid_level, liquid_density
                )
            else:
                raise ValueError("未知罐体类型")
            
            # 显示结果
            self.display_results(tank_type, tank_weight, liquid_weight, material_density, liquid_density)
            
        except ValueError as e:
            QMessageBox.warning(self, "输入错误", f"请输入有效的数值: {str(e)}")
        except Exception as e:
            QMessageBox.warning(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def _get_history_data(self):
        """提供历史记录数据"""
        tank_type = self.get_current_tank_type()
        diameter = float(self.diameter_input.text() or 0)
        material_density = float(self.density_input.text() or 0)
        liquid_density = float(self.liquid_density_input.text() or 0)

        inputs = {
            "罐体类型": tank_type,
            "直径_mm": diameter,
            "材料密度_kg_m3": material_density,
            "液体密度_kg_m3": liquid_density
        }

        outputs = {}
        try:
            D = diameter / 1000
            if tank_type == "锥体罐":
                H = float(self.height_input.text() or 0) / 1000
                t = float(self.shell_thickness_input.text() or 0) / 1000
                h_cone = float(self.cone_height_input.text() or 0) / 1000
                d = float(self.nozzle_diameter_input.text() or 0) / 1000
                inputs["高度_mm"] = H * 1000
                inputs["壁厚_mm"] = t * 1000
                inputs["锥高_mm"] = h_cone * 1000
                tank_weight = self.calculate_cone_tank_weight(D, H, t, h_cone, d, material_density)
                liquid_weight = self.calculate_cone_liquid_weight(D, H, h_cone, d, liquid_density)
            elif tank_type == "平底罐":
                H = float(self.height_input.text() or 0) / 1000
                t = float(self.shell_thickness_input.text() or 0) / 1000
                inputs["高度_mm"] = H * 1000
                inputs["壁厚_mm"] = t * 1000
                tank_weight = self.calculate_flat_tank_weight(D, H, t, material_density)
                liquid_weight = self.calculate_flat_liquid_weight(D, H, liquid_density)
            elif tank_type == "椭圆底罐":
                H = float(self.height_input.text() or 0) / 1000
                t = float(self.shell_thickness_input.text() or 0) / 1000
                inputs["高度_mm"] = H * 1000
                inputs["壁厚_mm"] = t * 1000
                tank_weight = self.calculate_elliptic_tank_weight(D, H, t, material_density)
                liquid_weight = self.calculate_elliptic_liquid_weight(D, H, liquid_density)
            elif tank_type == "卧式罐":
                L = float(self.length_input.text() or 0) / 1000
                t = float(self.shell_thickness_input.text() or 0) / 1000
                h = float(self.liquid_level_input.text() or 0) / 1000
                inputs["长度_mm"] = L * 1000
                inputs["壁厚_mm"] = t * 1000
                inputs["液位_mm"] = h * 1000
                tank_weight = self.calculate_horizontal_tank_weight(D, L, t, material_density)
                liquid_weight = self.calculate_horizontal_liquid_weight(D, L, h, liquid_density)
            elif tank_type == "球罐":
                t = float(self.sphere_thickness_input.text() or 0) / 1000
                h = float(self.liquid_level_input.text() or 0) / 1000
                inputs["壁厚_mm"] = t * 1000
                inputs["液位_mm"] = h * 1000
                tank_weight = self.calculate_sphere_tank_weight(D, t, material_density)
                liquid_weight = self.calculate_sphere_liquid_weight(D, h, liquid_density)
            else:
                tank_weight = 0
                liquid_weight = 0

            outputs = {
                "罐体重量_kg": round(tank_weight, 1),
                "液体重量_kg": round(liquid_weight, 1),
                "总重量_kg": round(tank_weight + liquid_weight, 1)
            }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def calculate_cone_tank_weight(self, D, H, t, h_cone, d, density):
        """计算锥体罐重量"""
        # 筒体体积 (圆柱侧面积 × 厚度)
        cylinder_area = math.pi * D * H
        cylinder_volume = cylinder_area * t
        
        # 锥体体积 (圆锥台侧面积 × 厚度)
        R_large = D / 2
        r_small = d / 2
        
        cone_slant_height = math.sqrt(h_cone**2 + (R_large - r_small)**2)
        cone_area = math.pi * (R_large + r_small) * cone_slant_height
        cone_volume = cone_area * t
        
        # 顶盖平板（锥底罐底部为锥体，平板为顶部封盖）
        bottom_area = math.pi * (R_large**2)
        bottom_volume = bottom_area * t
        
        # 总重量
        total_volume = cylinder_volume + cone_volume + bottom_volume
        total_weight = total_volume * density
        
        return total_weight
    
    def calculate_cone_liquid_weight(self, D, H, h_cone, d, liquid_density):
        """计算锥体罐液体重量（满罐：筒体 + 锥台）"""
        # 筒体部分液体体积
        cylinder_volume = math.pi * (D/2)**2 * H

        # 锥体部分为圆台（大端 R、小端 r=d/2）: V = (π·h/3)·(R² + R·r + r²)
        R = D / 2
        r = d / 2
        cone_volume = (math.pi * h_cone / 3.0) * (R**2 + R*r + r**2)

        total_volume = cylinder_volume + cone_volume
        liquid_weight = total_volume * liquid_density

        return liquid_weight
    
    def calculate_flat_tank_weight(self, D, H, t, density):
        """计算平底罐重量"""
        # 筒体侧面积
        cylinder_area = math.pi * D * H
        
        # 罐底面积 (平底)
        bottom_area = math.pi * (D/2)**2
        
        # 罐顶面积 (平的)
        top_area = bottom_area
        
        # 总表面积
        total_area = cylinder_area + bottom_area + top_area
        
        # 总重量
        total_volume = total_area * t
        total_weight = total_volume * density
        
        return total_weight
    
    def calculate_flat_liquid_weight(self, D, H, liquid_density):
        """计算平底罐液体重量"""
        total_volume = math.pi * (D/2)**2 * H
        liquid_weight = total_volume * liquid_density
        return liquid_weight
    
    def calculate_elliptic_tank_weight(self, D, H, t, density):
        """计算椭圆底罐重量"""
        # 筒体侧面积
        cylinder_area = math.pi * D * H
        
        # 椭圆封头面积
        head_area = 1.084 * math.pi * (D/2)**2
        total_head_area = 2 * head_area
        
        # 总表面积
        total_area = cylinder_area + total_head_area
        
        # 总重量
        total_volume = total_area * t
        total_weight = total_volume * density
        
        return total_weight
    
    def calculate_elliptic_liquid_weight(self, D, H, liquid_density):
        """计算椭圆底罐液体重量"""
        # 圆柱部分
        cylinder_volume = math.pi * (D/2)**2 * H
        
        # 椭圆封头体积
        head_volume = 0.1309 * D**3
        total_head_volume = 2 * head_volume
        
        total_volume = cylinder_volume + total_head_volume
        liquid_weight = total_volume * liquid_density
        return liquid_weight
    
    def calculate_horizontal_tank_weight(self, D, L, t, density):
        """计算卧式罐重量"""
        # 筒体侧面积
        cylinder_area = math.pi * D * L
        
        # 两个椭圆封头面积
        head_area = 1.084 * math.pi * (D/2)**2
        total_head_area = 2 * head_area
        
        # 总表面积
        total_area = cylinder_area + total_head_area
        
        # 总重量
        total_volume = total_area * t
        total_weight = total_volume * density
        
        return total_weight
    
    def calculate_horizontal_liquid_weight(self, D, L, h, liquid_density):
        """计算卧式罐液体重量"""
        if h == 0:
            total_volume = 0
        elif h >= D:
            total_volume = math.pi * (D/2)**2 * L
        else:
            # 部分充液计算
            R = D/2
            theta = 2 * math.acos((R - h) / R)
            segment_area = R**2 * (theta - math.sin(theta)) / 2
            total_volume = segment_area * L
        
        liquid_weight = total_volume * liquid_density
        return liquid_weight
    
    def calculate_sphere_tank_weight(self, D, t, density):
        """计算球罐重量"""
        # 球体表面积
        sphere_area = 4 * math.pi * (D/2)**2
        
        # 总重量
        total_volume = sphere_area * t
        total_weight = total_volume * density
        
        return total_weight
    
    def calculate_sphere_liquid_weight(self, D, h, liquid_density):
        """计算球罐液体重量"""
        if h == 0:
            total_volume = 0
        elif h >= D:
            total_volume = (4/3) * math.pi * (D/2)**3
        else:
            # 球冠体积
            R = D/2
            volume = (1/3) * math.pi * h**2 * (3*R - h)
            total_volume = volume
        
        liquid_weight = total_volume * liquid_density
        return liquid_weight
    
    def display_results(self, tank_type, tank_weight, liquid_weight, material_density, liquid_density):
        """显示计算结果"""
        total_weight = tank_weight + liquid_weight
        
        result_text = f"""═══════════
 输入参数
══════════

    罐体类型: {tank_type}
    罐体密度: {material_density:,} kg/m³
    液体密度: {liquid_density:,} kg/m³

══════════
计算结果
══════════

    重量分析:
    • 罐体空重: {tank_weight:,.1f} kg
    • 液体重量: {liquid_weight:,.1f} kg
    • 总重量: {total_weight:,.1f} kg

    单位换算:
    • 罐体空重: {tank_weight/1000:,.3f} 吨
    • 液体重量: {liquid_weight/1000:,.3f} 吨
    • 总重量: {total_weight/1000:,.3f} 吨

══════════
设计建议
══════════

    • 总重量: {total_weight/1000:,.2f} 吨
    • 建议吊装设备能力不小于总重量的1.2倍
    • 基础设计应同时考虑罐体空重和操作重量
    • 运输时需考虑最大总重量

══════════
备注说明
══════════

    • 计算结果为理论值，实际重量可能因制造工艺、附件等因素有所不同
    • 罐体重量计算基于简化几何模型
    • 液体重量计算基于满液状态或指定液位高度
    • 结果仅供参考，实际应用请考虑安全系数
"""
        
        self.result_text.setText(result_text)
    
    def clear_inputs(self):
        """清空输入"""
        # 重置所有输入为默认值
        self.type_button_group.button(0).setChecked(True)
        self.on_tank_type_changed(self.type_button_group.button(0))
        
        # 尺寸参数（输入框单位为 mm，恢复出厂默认值）
        self.diameter_input.setText("3000")
        self.height_input.setText("5000")
        self.shell_thickness_input.setText("6.0")
        self.cone_height_input.setText("1200")
        self.nozzle_diameter_input.setText("100")
        self.length_input.setText("5000")
        self.liquid_level_input.setText("1000")
        self.sphere_thickness_input.setText("6.0")
        
        # 材料参数
        self.material_combo.setCurrentIndex(1)  # 304不锈钢
        self.liquid_density_input.setText("1000")
        
        # 清空结果
        self.result_text.clear()
    
    def get_project_info(self):
        return {
            "project_name": "罐体重量计算",
            "calculator_name": "罐体重量计算器",
            "version": "1.0",
            "description": "锥体罐/平底罐/椭圆底罐/卧式罐/球罐的重量计算"
        }

    def generate_report(self):
        content = self.result_text.toPlainText().strip()
        if not content:
            return "尚未进行计算。"
        lines = ["罐体重量计算报告", "=" * 50, "", content]
        return "\n".join(lines)

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "罐体重量")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "罐体重量")

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = 罐体重量()
    calculator.resize(1200, 800)
    calculator.setWindowTitle("罐体重量计算器")
    calculator.show()
    
    sys.exit(app.exec())

