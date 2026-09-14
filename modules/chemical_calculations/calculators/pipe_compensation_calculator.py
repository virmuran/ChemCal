from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox,
    QScrollArea, QButtonGroup, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
import math
import re
from datetime import datetime


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from utils.docx_utils import ReportExporter


class 管道补偿(CalculatorBase):
    """管道补偿计算器（与压降计算器UI一致）"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        
        # 使用传入的数据管理器或创建新的
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        
        # 先设置管道标准数据，再设置UI
        self.setup_pipe_standards()
        self.setup_material_data()
        self.setup_ui()
        self.setup_mode_dependencies()

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
    
    def setup_material_data(self):
        """设置综合的管道材质数据"""
        self.pipe_materials = {
            # 通用材料分类
            "- 请选择管道材质 -": {"alpha": 0, "elastic": 0, "stress": 0, "description": ""},
            
            # 碳钢类
            "碳素钢 (C≤0.3%)": {"alpha": 11.7, "elastic": 200, "stress": 120, "description": "普通碳素钢，含碳量≤0.3%"},
            "碳素钢 (C＞0.3%)、碳锰钢": {"alpha": 11.5, "elastic": 205, "stress": 125, "description": "中碳钢，含碳量>0.3%"},
            "碳钢 (普通)": {"alpha": 11.7, "elastic": 200, "stress": 120, "description": "通用碳钢材料"},
            
            # 合金钢类
            "碳钼钢、低铬钼钢 (Cr3Mo)": {"alpha": 11.5, "elastic": 205, "stress": 140, "description": "低合金铬钼钢"},
            "中铬钼钢 (Cr5Mo~Cr9Mo)": {"alpha": 11.3, "elastic": 210, "stress": 160, "description": "中合金铬钼钢"},
            "高铬钢 (Cr13、Cr17)": {"alpha": 10.5, "elastic": 215, "stress": 180, "description": "高铬不锈钢"},
            
            # 不锈钢类
            "奥氏体不锈钢 (Cr18Ni9~Cr19Ni14)": {"alpha": 16.5, "elastic": 193, "stress": 137, "description": "300系列奥氏体不锈钢"},
            "Cr25 Ni20": {"alpha": 16.2, "elastic": 195, "stress": 145, "description": "高镍铬不锈钢"},
            "304(0Cr18Ni9) [GB/T12771]": {"alpha": 16.5, "elastic": 193, "stress": 137, "description": "304不锈钢，通用型"},
            "304L(00Cr19Ni10) [GB/T12771]": {"alpha": 16.8, "elastic": 193, "stress": 125, "description": "304L低碳不锈钢"},
            "316L(00Cr17Ni14Mo2) [GB/T12771]": {"alpha": 16.0, "elastic": 193, "stress": 137, "description": "316L含钼不锈钢"},
            "不锈钢304": {"alpha": 16.5, "elastic": 193, "stress": 137, "description": "304不锈钢"},
            "不锈钢316": {"alpha": 16.0, "elastic": 193, "stress": 137, "description": "316不锈钢"},
            
            # 铸铁类
            "灰铸铁": {"alpha": 10.5, "elastic": 100, "stress": 80, "description": "普通灰铸铁"},
            "球墨铸铁": {"alpha": 11.0, "elastic": 170, "stress": 140, "description": "球墨铸铁，强度较高"},
            
            # 有色金属类
            "铝及铝合金": {"alpha": 23.1, "elastic": 69, "stress": 55, "description": "铝及其合金"},
            "紫铜": {"alpha": 16.5, "elastic": 110, "stress": 69, "description": "纯铜材料"},
            "铜": {"alpha": 16.5, "elastic": 110, "stress": 69, "description": "铜材料"},
            "铝": {"alpha": 23.1, "elastic": 69, "stress": 55, "description": "铝材料"},
            
            # 特殊合金
            "蒙乃尔合金 (Ni67-Cu30)": {"alpha": 13.5, "elastic": 179, "stress": 160, "description": "蒙乃尔合金，耐腐蚀"},
            "铜镍合金 (Cu70-Ni30)": {"alpha": 15.0, "elastic": 150, "stress": 130, "description": "铜镍合金，耐海水腐蚀"},
            
            # 塑料类
            "PVC": {"alpha": 70.0, "elastic": 3, "stress": 15, "description": "聚氯乙烯塑料"},
            
            # 标准牌号
            "20# [GB/T13793]": {"alpha": 11.7, "elastic": 200, "stress": 120, "description": "20号钢，GB/T13793标准"},
            "20# [GB/T8163]": {"alpha": 11.7, "elastic": 200, "stress": 120, "description": "20号钢，GB/T8163标准"},
            "20# [GB3087]": {"alpha": 11.7, "elastic": 200, "stress": 120, "description": "20号钢，GB3087标准"},
            
            # 自定义
            "自定义材质": {"alpha": 0, "elastic": 0, "stress": 0, "description": "用户自定义材料参数"}
        }
    
    def setup_pipe_standards(self):
        """设置管道标准规格数据（外径）"""
        # 标准管道外径规格 (单位：mm)
        self.pipe_standards = [
            ("- 请选择管道外径 -", 0),  # 空值选项
            ("DN6 (1/8\") - 10.3mm", 10.3),
            ("DN8 (1/4\") - 13.7mm", 13.7),
            ("DN10 (3/8\") - 17.2mm", 17.2),
            ("DN15 (1/2\") - 21.3mm", 21.3),
            ("DN20 (3/4\") - 26.9mm", 26.9),
            ("DN25 (1\") - 33.7mm", 33.7),
            ("DN32 (1.25\") - 42.4mm", 42.4),
            ("DN40 (1.5\") - 48.3mm", 48.3),
            ("DN50 (2\") - 60.3mm", 60.3),
            ("DN65 (2.5\") - 73.0mm", 73.0),
            ("DN80 (3\") - 88.9mm", 88.9),
            ("DN100 (4\") - 114.3mm", 114.3),
            ("DN125 (5\") - 139.7mm", 139.7),
            ("DN150 (6\") - 168.3mm", 168.3),
            ("DN200 (8\") - 219.1mm", 219.1),
            ("DN250 (10\") - 273.0mm", 273.0),
            ("DN300 (12\") - 323.9mm", 323.9),
            ("DN350 (14\") - 355.6mm", 355.6),
            ("DN400 (16\") - 406.4mm", 406.4),
            ("DN450 (18\") - 457.2mm", 457.2),
            ("DN500 (20\") - 508.0mm", 508.0),
            ("DN600 (24\") - 609.6mm", 609.6),
            ("DN700 (28\") - 711.2mm", 711.2),
            ("DN800 (32\") - 812.8mm", 812.8),
            ("DN900 (36\") - 914.4mm", 914.4),
            ("DN1000 (40\") - 1016.0mm", 1016.0),
            ("DN1200 (48\") - 1219.2mm", 1219.2),
            ("DN1400 (56\") - 1422.0mm", 1422.0),
        ]
    
    def setup_ui(self):
        """设置左右布局的管道补偿计算UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧：输入参数区域 (占2/3宽度)
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        scroll_left.setWidgetResizable(True)

        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # 1. 说明文本
        description = QLabel(
            "计算管道热膨胀量和需要的补偿量，评估管道热应力，支持L形和Z形补偿计算。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 2. 计算模式选择
        mode_group = CalculatorBase.make_group_box("计算模式")
        mode_layout = QHBoxLayout(mode_group)
        
        self.mode_button_group = QButtonGroup(self)
        self.mode_buttons = {}
        
        modes = [
            ("热膨胀基本计算", "计算管道热膨胀量和应力"),
            ("L形直角弯补偿", "L形管道补偿计算"),
            ("Z形折角弯补偿", "Z形管道补偿计算")
        ]
        
        for i, (mode_name, tooltip) in enumerate(modes):
            btn = CalculatorBase.make_mode_button(mode_name, tooltip)
            self.mode_button_group.addButton(btn, i)
            mode_layout.addWidget(btn)
            self.mode_buttons[mode_name] = btn
        
        # 默认选择第一个
        self.mode_buttons["热膨胀基本计算"].setChecked(True)
        self.mode_button_group.buttonClicked.connect(self.on_mode_button_clicked)
        
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
        
        # 管道材质选择
        material_label = QLabel("管道材质:")
        material_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        material_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(material_label, row, 0)
        
        self.material_combo = QComboBox()
        self.material_combo.setStyleSheet(COMBOBOX_STYLE)
        self.material_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # 添加材质选项，分组显示
        # 首先添加空选项
        self.material_combo.addItem("- 请选择管道材质 -")
        
        # 碳钢类
        self.material_combo.addItem("碳素钢 (C≤0.3%)")
        self.material_combo.addItem("碳素钢 (C＞0.3%)、碳锰钢")
        self.material_combo.addItem("碳钢 (普通)")
        self.material_combo.addItem("20# [GB/T13793]")
        self.material_combo.addItem("20# [GB/T8163]")
        self.material_combo.addItem("20# [GB3087]")
        
        # 合金钢类
        self.material_combo.addItem("碳钼钢、低铬钼钢 (Cr3Mo)")
        self.material_combo.addItem("中铬钼钢 (Cr5Mo~Cr9Mo)")
        self.material_combo.addItem("高铬钢 (Cr13、Cr17)")
        
        # 不锈钢类
        self.material_combo.addItem("奥氏体不锈钢 (Cr18Ni9~Cr19Ni14)")
        self.material_combo.addItem("Cr25 Ni20")
        self.material_combo.addItem("304(0Cr18Ni9) [GB/T12771]")
        self.material_combo.addItem("304L(00Cr19Ni10) [GB/T12771]")
        self.material_combo.addItem("316L(00Cr17Ni14Mo2) [GB/T12771]")
        self.material_combo.addItem("不锈钢304")
        self.material_combo.addItem("不锈钢316")
        
        # 铸铁类
        self.material_combo.addItem("灰铸铁")
        self.material_combo.addItem("球墨铸铁")
        
        # 有色金属类
        self.material_combo.addItem("铝及铝合金")
        self.material_combo.addItem("铝")
        self.material_combo.addItem("紫铜")
        self.material_combo.addItem("铜")
        
        # 特殊合金类
        self.material_combo.addItem("蒙乃尔合金 (Ni67-Cu30)")
        self.material_combo.addItem("铜镍合金 (Cu70-Ni30)")
        
        # 塑料类
        self.material_combo.addItem("PVC")
        
        # 自定义
        self.material_combo.addItem("自定义材质")
        
        self.material_combo.currentTextChanged.connect(self.on_material_changed)
        input_layout.addWidget(self.material_combo, row, 1)
        
        # 材质描述（第2列）
        self.material_desc_label = QLabel("")
        self.material_desc_label.setStyleSheet("font-style: italic;")
        self.material_desc_label.setWordWrap(True)
        input_layout.addWidget(self.material_desc_label, row, 2)
        
        row += 1
        
        # 管道外径
        od_label = QLabel("管道外径 (mm):")
        od_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        od_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(od_label, row, 0)
        
        self.od_input = QLineEdit("108")
        self.od_input.setPlaceholderText("例如: 108")
        self.od_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.od_input.setValidator(QDoubleValidator(1.0, 2000.0, 6))
        input_layout.addWidget(self.od_input, row, 1)
        
        self.od_combo = QComboBox()
        self.od_combo.setStyleSheet(COMBOBOX_STYLE)
        self.od_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # 添加管道外径选项
        for name, od in self.pipe_standards:
            if od == 0:  # 空值选项
                self.od_combo.addItem(name)
            else:
                self.od_combo.addItem(name)
        
        self.od_combo.currentTextChanged.connect(self.on_od_combo_changed)
        input_layout.addWidget(self.od_combo, row, 2)
        
        row += 1
        
        # 管道长度 - 基本计算模式
        self.length_label = QLabel("管道长度 (m):")
        self.length_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.length_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(self.length_label, row, 0)
        
        self.length_input = QLineEdit("50.0")
        self.length_input.setPlaceholderText("例如: 50.0")
        self.length_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.length_input.setValidator(QDoubleValidator(0.1, 1000.0, 6))
        input_layout.addWidget(self.length_input, row, 1)
        
        self.length_hint = QLabel("基本计算时使用")
        self.length_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(self.length_hint, row, 2)
        
        row += 1
        
        # L形补偿参数 - 长臂L1
        self.l1_label = QLabel("长臂 L1 (m):")
        self.l1_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.l1_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(self.l1_label, row, 0)
        
        self.l1_input = QLineEdit("20.0")
        self.l1_input.setPlaceholderText("例如: 20.0")
        self.l1_input.setValidator(QDoubleValidator(0.1, 1000.0, 6))
        self.l1_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.l1_input, row, 1)
        
        self.l1_hint = QLabel("L形和Z形补偿时使用")
        self.l1_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(self.l1_hint, row, 2)
        
        row += 1
        
        # L形补偿参数 - 短臂L2
        self.l2_label = QLabel("短臂 L2 (m):")
        self.l2_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.l2_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(self.l2_label, row, 0)
        
        self.l2_input = QLineEdit("9.0")
        self.l2_input.setPlaceholderText("例如: 9.0")
        self.l2_input.setValidator(QDoubleValidator(0.1, 1000.0, 6))
        self.l2_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.l2_input, row, 1)
        
        self.l2_hint = QLabel("L形和Z形补偿时使用")
        self.l2_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(self.l2_hint, row, 2)
        
        row += 1
        
        # Z形补偿参数 - 臂长L3
        self.l3_label = QLabel("臂长 L3 (m):")
        self.l3_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.l3_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(self.l3_label, row, 0)
        
        self.l3_input = QLineEdit("15.0")
        self.l3_input.setPlaceholderText("例如: 15.0")
        self.l3_input.setValidator(QDoubleValidator(0.1, 1000.0, 6))
        self.l3_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.l3_input, row, 1)
        
        self.l3_hint = QLabel("仅Z形补偿时使用")
        self.l3_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(self.l3_hint, row, 2)
        
        row += 1
        
        # 温度参数
        temp_install_label = QLabel("安装温度 (°C):")
        temp_install_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        temp_install_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(temp_install_label, row, 0)
        
        self.temp_install_input = QLineEdit("20")
        self.temp_install_input.setPlaceholderText("例如: 20")
        self.temp_install_input.setValidator(QDoubleValidator(-100.0, 100.0, 6))
        self.temp_install_input.setText("20")
        self.temp_install_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.temp_install_input, row, 1)
        
        self.temp_install_hint = QLabel("管道安装时的温度")
        self.temp_install_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(self.temp_install_hint, row, 2)
        
        row += 1
        
        temp_operate_label = QLabel("操作温度 (°C):")
        temp_operate_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        temp_operate_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(temp_operate_label, row, 0)
        
        self.temp_operate_input = QLineEdit("200")
        self.temp_operate_input.setPlaceholderText("例如: 200")
        self.temp_operate_input.setValidator(QDoubleValidator(-100.0, 500.0, 6))
        self.temp_operate_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.temp_operate_input, row, 1)
        
        self.temp_operate_hint = QLabel("管道运行时的温度")
        self.temp_operate_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(self.temp_operate_hint, row, 2)
        
        row += 1
        
        # 线膨胀系数
        alpha_label = QLabel("线膨胀系数 (×10⁻⁶/°C):")
        alpha_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        alpha_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(alpha_label, row, 0)
        
        self.alpha_value_input = QLineEdit()
        self.alpha_value_input.setPlaceholderText("自动填充")
        self.alpha_value_input.setReadOnly(True)
        self.alpha_value_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.alpha_value_input, row, 1)
        
        self.alpha_hint = QLabel("根据材质自动计算")
        self.alpha_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(self.alpha_hint, row, 2)
        
        row += 1
        
        # 弹性模量
        elastic_label = QLabel("弹性模量 (GPa):")
        elastic_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        elastic_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(elastic_label, row, 0)
        
        self.elastic_value_input = QLineEdit()
        self.elastic_value_input.setPlaceholderText("自动填充")
        self.elastic_value_input.setReadOnly(True)
        self.elastic_value_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.elastic_value_input, row, 1)
        
        self.elastic_hint = QLabel("根据材质自动计算")
        self.elastic_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(self.elastic_hint, row, 2)
        
        row += 1
        
        # 许用应力
        stress_label = QLabel("许用应力 (MPa):")
        stress_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        stress_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(stress_label, row, 0)
        
        self.stress_value_input = QLineEdit()
        self.stress_value_input.setPlaceholderText("自动填充")
        self.stress_value_input.setReadOnly(True)
        self.stress_value_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.stress_value_input, row, 1)
        
        self.stress_hint = QLabel("根据材质自动计算")
        self.stress_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(self.stress_hint, row, 2)
        
        left_layout.addWidget(input_group)
        
        # 4. 在底部添加拉伸因子
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
        calc_btn.clicked.connect(self.calculate_compensation)
        right_layout.addWidget(calc_btn)
        
        # 将左右两部分添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)  # 左侧占2/3
        main_layout.addWidget(right_widget, 1)  # 右侧占1/3
    
    def on_od_combo_changed(self, text):
        """处理管道外径下拉菜单选择变化"""
        # 检查是否为空值选项或分隔线
        if text.startswith("-") or not text.strip() or text.startswith("---"):
            return
            
        # 从文本中提取外径数值
        try:
            # 使用正则表达式匹配数字
            match = re.search(r'(\d+\.?\d*)mm', text)
            if match:
                od_value = float(match.group(1))
                self.od_input.setText(f"{od_value}")
        except:
            pass
    
    def on_material_changed(self, text):
        """处理材料选择变化"""
        # 检查是否为空值选项或分隔线
        if text.startswith("-") or not text.strip() or text.startswith("---"):
            self.material_desc_label.setText("")
            self.alpha_value_input.clear()
            self.elastic_value_input.clear()
            self.stress_value_input.clear()
            return
        
        # 检查材质是否在数据字典中
        if text in self.pipe_materials:
            material_data = self.pipe_materials[text]
            
            # 更新描述
            if text == "自定义材质":
                self.material_desc_label.setText("请手动输入材料参数")
                self.alpha_value_input.setReadOnly(False)
                self.elastic_value_input.setReadOnly(False)
                self.stress_value_input.setReadOnly(False)
                self.alpha_value_input.clear()
                self.elastic_value_input.clear()
                self.stress_value_input.clear()
            else:
                desc = material_data["description"]
                self.material_desc_label.setText(f"材质描述: {desc}")
                
                # 设置输入框为只读并填充数值
                self.alpha_value_input.setReadOnly(True)
                self.elastic_value_input.setReadOnly(True)
                self.stress_value_input.setReadOnly(True)
                
                # 填充数值
                self.alpha_value_input.setText(f"{material_data['alpha']:.2f}")
                self.elastic_value_input.setText(f"{material_data['elastic']:.0f}")
                self.stress_value_input.setText(f"{material_data['stress']:.0f}")
        else:
            self.material_desc_label.setText("")
    
    def on_mode_button_clicked(self, button):
        """处理计算模式按钮点击"""
        mode_text = button.text()
        self.on_mode_changed(mode_text)
    
    def get_current_mode(self):
        """获取当前选择的计算模式"""
        checked_button = self.mode_button_group.checkedButton()
        if checked_button:
            return checked_button.text()
        return "热膨胀基本计算"  # 默认值
    
    def setup_mode_dependencies(self):
        """设置计算模式的依赖关系"""
        # 初始状态 - 热膨胀基本计算
        self.on_mode_changed("热膨胀基本计算")
    
    def on_mode_changed(self, mode):
        """处理计算模式变化"""
        # 重置所有参数可见性
        self.length_input.setVisible(True)
        self.length_label.setVisible(True)
        self.length_hint.setVisible(True)
        
        self.l1_input.setVisible(False)
        self.l1_label.setVisible(False)
        self.l1_hint.setVisible(False)
        
        self.l2_input.setVisible(False)
        self.l2_label.setVisible(False)
        self.l2_hint.setVisible(False)
        
        self.l3_input.setVisible(False)
        self.l3_label.setVisible(False)
        self.l3_hint.setVisible(False)
        
        # 根据模式显示相应参数
        if mode == "热膨胀基本计算":
            self.length_label.setText("管道长度 (m):")
            self.length_hint.setText("基本计算时使用")
        elif mode == "L形直角弯补偿":
            self.length_input.setVisible(False)
            self.length_label.setVisible(False)
            self.length_hint.setVisible(False)
            
            self.l1_input.setVisible(True)
            self.l1_label.setVisible(True)
            self.l1_hint.setVisible(True)
            
            self.l2_input.setVisible(True)
            self.l2_label.setVisible(True)
            self.l2_hint.setVisible(True)
        elif mode == "Z形折角弯补偿":
            self.length_input.setVisible(False)
            self.length_label.setVisible(False)
            self.length_hint.setVisible(False)
            
            self.l1_input.setVisible(True)
            self.l1_label.setVisible(True)
            self.l1_hint.setVisible(True)
            
            self.l2_input.setVisible(True)
            self.l2_label.setVisible(True)
            self.l2_hint.setVisible(True)
            
            self.l3_input.setVisible(True)
            self.l3_label.setVisible(True)
            self.l3_hint.setVisible(True)
    
    def get_material_properties(self):
        """获取材料属性"""
        try:
            # 从输入框获取数值
            alpha_str = self.alpha_value_input.text()
            elastic_str = self.elastic_value_input.text()
            stress_str = self.stress_value_input.text()
            
            # 转换为标准单位
            alpha = float(alpha_str or 11.7) * 1e-6  # 从×10⁻⁶/°C转换为/°C
            elastic = float(elastic_str or 200) * 1e9  # 从GPa转换为Pa
            stress = float(stress_str or 120) * 1e6  # 从MPa转换为Pa
            
            return alpha, elastic, stress
        except ValueError:
            # 如果输入无效，使用碳钢默认值
            return 11.7e-6, 200e9, 120e6
    
    def get_pipe_dimensions(self):
        """获取管道外径和壁厚"""
        # 获取外径
        try:
            od = float(self.od_input.text() or 0) / 1000  # 转换为米
        except ValueError:
            od = 0.108  # 默认108mm
        
        # 根据外径估算壁厚（简化的经验公式）
        # 这里假设壁厚为外径的5%，最小为1mm
        thickness_mm = max(od * 1000 * 0.05, 1.0)  # 最小1mm
        
        # 如果是标准规格，使用更精确的壁厚
        text = self.od_combo.currentText()
        if not text.startswith("-") and text.strip() and not text.startswith("---"):
            # 尝试从下拉菜单中获取更精确的壁厚
            # 这里可以根据实际标准添加更精确的壁厚数据
            pass
        
        thickness = thickness_mm / 1000  # 转换为米
        
        return od, thickness
    
    def calculate_compensation(self):
        """计算管道补偿"""
        try:
            # 获取当前计算模式
            mode = self.get_current_mode()
            
            # 获取管道外径和估算的壁厚
            od, thickness = self.get_pipe_dimensions()
            
            # 获取温度参数
            temp_install = float(self.temp_install_input.text() or 0)
            temp_operate = float(self.temp_operate_input.text() or 0)
            
            # 计算温度变化
            temp_change = abs(temp_operate - temp_install)
            
            # 获取材料属性
            alpha, elastic, allowable_stress = self.get_material_properties()
            
            # 获取当前选择的材质名称
            material_name = self.material_combo.currentText()
            if material_name.startswith("---") or material_name == "- 请选择管道材质 -":
                material_name = "未指定材质"
            
            # 验证基本输入
            if not all([od, thickness, temp_change]):
                QMessageBox.warning(self, "输入错误", "请填写基本参数（管道规格、温度）")
                return
            
            # 根据模式计算
            if mode == "热膨胀基本计算":
                length = float(self.length_input.text() or 0)
                if not length:
                    QMessageBox.warning(self, "输入错误", "请填写管道长度")
                    return
                
                result = self.calculate_basic_expansion(od, thickness, length, temp_change, alpha, elastic, allowable_stress, material_name)
                
            elif mode == "L形直角弯补偿":
                l1 = float(self.l1_input.text() or 0)
                l2 = float(self.l2_input.text() or 0)
                if not l1 or not l2:
                    QMessageBox.warning(self, "输入错误", "请填写L1和L2臂长")
                    return
                
                result = self.calculate_l_shaped_compensation(od, thickness, l1, l2, temp_change, alpha, elastic, allowable_stress, material_name)
                
            elif mode == "Z形折角弯补偿":
                l1 = float(self.l1_input.text() or 0)
                l2 = float(self.l2_input.text() or 0)
                l3 = float(self.l3_input.text() or 0)
                if not l1 or not l2 or not l3:
                    QMessageBox.warning(self, "输入错误", "请填写L1、L2和L3臂长")
                    return
                
                result = self.calculate_z_shaped_compensation(od, thickness, l1, l2, l3, temp_change, alpha, elastic, allowable_stress, material_name)
            
            else:
                result = "错误: 未知的计算模式"
            
            self.result_text.setText(result)
            
        except ValueError as e:
            QMessageBox.critical(self, "计算错误", f"参数输入格式错误: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def clear_inputs(self):
        """清空所有输入"""
        self.material_combo.setCurrentIndex(0)
        self.od_combo.setCurrentIndex(0)
        self.od_input.clear()
        self.length_input.clear()
        self.l1_input.clear()
        self.l2_input.clear()
        self.l3_input.clear()
        self.temp_install_input.clear()
        self.temp_operate_input.clear()
        self.alpha_value_input.clear()
        self.elastic_value_input.clear()
        self.stress_value_input.clear()
        self.result_text.clear()

    def _get_history_data(self):
        """提供历史记录数据"""
        mode = self.get_current_mode()
        material_name = self.material_combo.currentText()
        if material_name.startswith("---") or material_name == "- 请选择管道材质 -":
            material_name = "未指定"
        od, thickness = self.get_pipe_dimensions()
        temp_install = float(self.temp_install_input.text() or 0)
        temp_operate = float(self.temp_operate_input.text() or 0)
        temp_change = abs(temp_operate - temp_install)
        alpha, elastic, allowable_stress = self.get_material_properties()

        inputs = {
            "计算模式": mode,
            "管道材质": material_name,
            "管道外径_mm": round(od * 1000, 1),
            "管道壁厚_mm": round(thickness * 1000, 1),
            "安装温度_C": temp_install,
            "操作温度_C": temp_operate,
            "温度变化_C": round(temp_change, 1),
            "线膨胀系数_1e-6": round(alpha * 1e6, 2),
            "弹性模量_GPa": round(elastic / 1e9, 0),
            "许用应力_MPa": round(allowable_stress / 1e6, 0)
        }

        outputs = {}
        try:
            if mode == "热膨胀基本计算":
                length = float(self.length_input.text() or 0)
                inputs["管道长度_m"] = length
                expansion = alpha * temp_change * length
                id_val = od - 2 * thickness
                area = math.pi * (od**2 - id_val**2) / 4
                stress = elastic * alpha * temp_change
                force = stress * area
                if expansion < 0.05:
                    compensation = "自然补偿"
                elif expansion < 0.15:
                    compensation = "Π型补偿器"
                elif expansion < 0.3:
                    compensation = "波纹管补偿器"
                else:
                    compensation = "套筒/球形补偿器"
                outputs = {
                    "热膨胀量_mm": round(expansion * 1000, 1),
                    "热应力_MPa": round(stress / 1e6, 1),
                    "热推力_kN": round(force / 1000, 1),
                    "推荐补偿方式": compensation
                }
            elif mode == "L形直角弯补偿":
                l1 = float(self.l1_input.text() or 0)
                l2 = float(self.l2_input.text() or 0)
                inputs["L1臂长_m"] = l1
                inputs["L2臂长_m"] = l2
                expansion = alpha * temp_change * max(l1, l2)
                outputs = {
                    "L1臂长_m": l1,
                    "L2臂长_m": l2,
                    "最大热膨胀_mm": round(expansion * 1000, 1)
                }
            elif mode == "Z形折角弯补偿":
                l1 = float(self.l1_input.text() or 0)
                l2 = float(self.l2_input.text() or 0)
                l3 = float(self.l3_input.text() or 0)
                inputs["L1_m"] = l1
                inputs["L2_m"] = l2
                inputs["L3_m"] = l3
                expansion = alpha * temp_change * max(l1, l3)
                outputs = {
                    "L1_m": l1,
                    "L2_m": l2,
                    "L3_m": l3,
                    "端臂热膨胀_mm": round(expansion * 1000, 1)
                }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def calculate_basic_expansion(self, od, thickness, length, temp_change, alpha, elastic, allowable_stress, material_name):
        """计算基本热膨胀"""
        # 计算热膨胀量
        expansion = alpha * temp_change * length  # 米
        
        # 计算截面面积
        id_val = od - 2 * thickness
        area = math.pi * (od**2 - id_val**2) / 4
        
        # 计算热应力 (如果完全约束)
        stress = elastic * alpha * temp_change  # Pa
        
        # 计算热推力
        force = stress * area  # N
        
        # 推荐补偿方式
        if expansion < 0.05:  # 50mm
            compensation = "自然补偿 (利用管道走向)"
        elif expansion < 0.15:  # 150mm
            compensation = "Π型补偿器"
        elif expansion < 0.3:  # 300mm
            compensation = "波纹管补偿器"
        else:
            compensation = "套筒补偿器或球形补偿器"
        
        # 应力评估
        stress_mpa = stress / 1e6
        if stress_mpa < allowable_stress / 1e6 * 0.8:
            stress_evaluation = "热应力在安全范围内"
        elif stress_mpa < allowable_stress / 1e6:
            stress_evaluation = "热应力较高，需要详细应力分析"
        else:
            stress_evaluation = "热应力过高，必须采取补偿措施"
        
        result = f"""═══════════
输入参数
══════════

    计算模式: 热膨胀基本计算
    管道材质: {material_name}
    管道外径: {od*1000:.1f} mm
    管道壁厚: {thickness*1000:.1f} mm (估算值)
    管道长度: {length} m
    安装温度: {self.temp_install_input.text()} °C
    操作温度: {self.temp_operate_input.text()} °C
    温度变化: {temp_change:.1f} °C
    线膨胀系数: {alpha*1e6:.2f} ×10⁻⁶/°C
    弹性模量: {elastic/1e9:.0f} GPa
    许用应力: {allowable_stress/1e6:.0f} MPa

══════════
计算结果
══════════

    热膨胀分析:
    • 热膨胀量: {expansion*1000:.1f} mm
    • 热膨胀量: {expansion:.6f} m

    应力分析:
    • 完全约束时的热应力: {stress_mpa:.1f} MPa
    • 许用应力: {allowable_stress/1e6:.0f} MPa
    • 热应力与许用应力比: {stress_mpa/(allowable_stress/1e6)*100:.1f}%
    • 完全约束时的热推力: {force/1000:.1f} kN

    补偿建议:
    • 推荐补偿方式: {compensation}

    安全评估:
    • {stress_evaluation}

══════════
计算说明
══════════

    • 热膨胀量: ΔL = α × L × ΔT
    • 热应力: σ = E × α × ΔT
    • 热推力: F = σ × A

    其中:
    α = 线膨胀系数, L = 管道长度
    ΔT = 温度变化, E = 弹性模量
    A = 管道截面积

    • 壁厚为估算值，实际工程请使用准确的管道壁厚
    • 结果仅供参考，实际工程需考虑安全系数"""
        
        return result
    
    def calculate_l_shaped_compensation(self, od, thickness, l1, l2, temp_change, alpha, elastic, allowable_stress, material_name):
        """计算L形直角弯补偿"""
        # 计算总膨胀量 (使用较长臂)
        total_length = l1 + l2
        expansion = alpha * temp_change * total_length
        
        # 计算L形补偿的应力集中系数
        # 简化计算：使用经验公式
        if l2 > 0:
            ratio = l1 / l2
            if ratio > 1:
                stress_concentration = 1.5 + 0.5 * (ratio - 1)
            else:
                stress_concentration = 1.5
        else:
            stress_concentration = 2.0
        
        # 计算截面参数
        id_val = od - 2 * thickness
        area = math.pi * (od**2 - id_val**2) / 4
        section_modulus = math.pi * (od**4 - id_val**4) / (32 * od)
        
        # 计算弯矩和应力
        # 简化计算：假设膨胀力作用在长臂末端
        expansion_force = elastic * alpha * temp_change * area  # 简化的膨胀力
        moment = expansion_force * l2  # 简化计算
        
        bending_stress = moment * od / (2 * section_modulus)
        total_stress = bending_stress * stress_concentration
        
        # 评估补偿能力
        if l2 >= 10 * od:
            compensation_ability = "良好"
        elif l2 >= 5 * od:
            compensation_ability = "一般"
        else:
            compensation_ability = "不足"
        
        # 安全评估
        stress_mpa = total_stress / 1e6
        allowable_mpa = allowable_stress / 1e6
        
        if stress_mpa < allowable_mpa * 0.7:
            safety = "安全"
            safety_icon = "✓"
        elif stress_mpa < allowable_mpa:
            safety = "临界"
            safety_icon = "⚠"
        else:
            safety = "不安全"
            safety_icon = "✗"
        
        result = f"""═══════════
输入参数
══════════

    计算模式: L形直角弯补偿
    管道材质: {material_name}
    管道外径: {od*1000:.1f} mm
    管道壁厚: {thickness*1000:.1f} mm (估算值)
    长臂 L1: {l1} m
    短臂 L2: {l2} m
    安装温度: {self.temp_install_input.text()} °C
    操作温度: {self.temp_operate_input.text()} °C
    温度变化: {temp_change:.1f} °C
    线膨胀系数: {alpha*1e6:.2f} ×10⁻⁶/°C
    弹性模量: {elastic/1e9:.0f} GPa
    许用应力: {allowable_mpa:.0f} MPa

══════════
计算结果
══════════

    几何参数:
    • 总管道长度: {total_length:.2f} m
    • 长短臂比: {l1/l2:.2f} : 1
    • 应力集中系数: {stress_concentration:.2f}

    热膨胀分析:
    • 总热膨胀量: {expansion*1000:.1f} mm
    • 总热膨胀量: {expansion:.6f} m

    应力分析:
    • 弯曲应力: {bending_stress/1e6:.1f} MPa
    • 考虑应力集中后的应力: {stress_mpa:.1f} MPa
    • 许用应力: {allowable_mpa:.0f} MPa
    • 应力比: {stress_mpa/allowable_mpa*100:.1f}%
    • 膨胀力: {expansion_force/1000:.1f} kN
    • 弯矩: {moment:.0f} N·m

    补偿能力评估:
    • L形补偿能力: {compensation_ability}
    • 建议最小短臂长度: {10*od:.2f} m (10倍管径)

    安全评估:
    • {safety_icon} {safety}

══════════
计算说明
══════════

    • L形补偿利用管道直角转弯吸收热膨胀
    • 短臂长度对补偿能力影响较大
    • 应力集中系数考虑了弯头处的应力放大效应
    • 建议短臂长度不小于10倍管径以获得良好补偿效果
    • 壁厚为估算值，实际工程请使用准确的管道壁厚
    • 结果仅供参考，实际工程需详细应力分析"""
        
        return result
    
    def calculate_z_shaped_compensation(self, od, thickness, l1, l2, l3, temp_change, alpha, elastic, allowable_stress, material_name):
        """计算Z形折角弯补偿"""
        # 计算总膨胀量
        total_length = l1 + l2 + l3
        expansion = alpha * temp_change * total_length
        
        # 计算Z形补偿的应力
        # 简化计算：假设对称Z形，中间臂为主要补偿臂
        if l2 > 0:
            # 简化的Z形补偿公式
            section_modulus = math.pi * (od**4 - (od-2*thickness)**4) / (32 * od)
            
            # 计算膨胀力
            expansion_force = elastic * alpha * temp_change * math.pi * (od**2 - (od-2*thickness)**2) / 4
            
            # 简化的弯矩计算
            moment = expansion_force * l2 / 2
            
            bending_stress = moment * od / (2 * section_modulus)
            # Z形补偿通常有较低的应力集中
            total_stress = bending_stress * 1.2
        else:
            total_stress = 0
        
        # 评估补偿能力
        if l2 >= 15 * od:
            compensation_ability = "优秀"
        elif l2 >= 10 * od:
            compensation_ability = "良好"
        elif l2 >= 5 * od:
            compensation_ability = "一般"
        else:
            compensation_ability = "不足"
        
        # 安全评估
        stress_mpa = total_stress / 1e6
        allowable_mpa = allowable_stress / 1e6
        
        if stress_mpa < allowable_mpa * 0.6:
            safety = "非常安全"
            safety_icon = "✓✓"
        elif stress_mpa < allowable_mpa * 0.8:
            safety = "安全"
            safety_icon = "✓"
        elif stress_mpa < allowable_mpa:
            safety = "临界"
            safety_icon = "⚠"
        else:
            safety = "不安全"
            safety_icon = "[NO]"
        
        result = f"""═══════════
输入参数
══════════

    计算模式: Z形折角弯补偿
    管道材质: {material_name}
    管道外径: {od*1000:.1f} mm
    管道壁厚: {thickness*1000:.1f} mm (估算值)
    臂长 L1: {l1} m
    臂长 L2: {l2} m
    臂长 L3: {l3} m
    安装温度: {self.temp_install_input.text()} °C
    操作温度: {self.temp_operate_input.text()} °C
    温度变化: {temp_change:.1f} °C
    线膨胀系数: {alpha*1e6:.2f} ×10⁻⁶/°C
    弹性模量: {elastic/1e9:.0f} GPa
    许用应力: {allowable_mpa:.0f} MPa

══════════
计算结果
══════════

    几何参数:
    • 总管道长度: {total_length:.2f} m
    • Z形总跨度: {l1 + l3:.2f} m
    • 中间臂长度: {l2:.2f} m

    热膨胀分析:
    • 总热膨胀量: {expansion*1000:.1f} mm
    • 总热膨胀量: {expansion:.6f} m

    应力分析:
    • 弯曲应力: {bending_stress/1e6 if 'bending_stress' in locals() else 0:.1f} MPa
    • 考虑应力集中后的应力: {stress_mpa:.1f} MPa
    • 许用应力: {allowable_mpa:.0f} MPa
    • 应力比: {stress_mpa/allowable_mpa*100 if allowable_mpa > 0 else 0:.1f}%
    • 膨胀力: {expansion_force/1000 if 'expansion_force' in locals() else 0:.1f} kN

    补偿能力评估:
    • Z形补偿能力: {compensation_ability}
    • 建议中间臂长度: {10*od:.2f} m (10倍管径)
    • Z形补偿特点: 适用于较大热膨胀量的场合

    安全评估:
    • {safety_icon} {safety}

══════════
计算说明
══════════

    • Z形补偿通过三个臂的变形吸收热膨胀
    • 中间臂长度对补偿效果影响最大
    • Z形补偿通常比L形补偿能吸收更大的热膨胀量
    • 建议中间臂长度不小于10倍管径
    • 壁厚为估算值，实际工程请使用准确的管道壁厚
    • 结果仅供参考，实际工程需详细应力分析"""
        
        return result
    
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
            
            # 检查是否有计算结果
            if not result_text or ("计算结果" not in result_text and "热膨胀量" not in result_text):
                QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
                return ""
            
            # 获取工程信息
            project_info = self.get_project_info()
            
            # 获取当前模式
            mode = self.get_current_mode()
            
            # 添加报告头信息
            report = f"""工程计算书 - 管道补偿计算
计算类型: {mode}
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
    计算书编号: {project_info.get('report_number', '')}
    计算日期: {datetime.now().strftime('%Y-%m-%d')}

══════════
备注说明
══════════

    1. 本计算书基于热力学原理及相关标准规范
    2. 计算结果仅供参考，实际应用需考虑安全系数
    3. 重要工程参数应经专业工程师审核确认
    4. 计算条件变更时应重新进行计算
    5. 对于重要管道系统，建议进行详细的有限元分析
    6. 管道壁厚为估算值，实际工程请使用准确的管道壁厚数据

---
生成于 ChemCal 工程计算模块
"""
            return report
            
        except Exception as e:
            print(f"生成计算书失败: {e}")
            return ""
    
    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "管道补偿")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "管道补偿")

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = 管道补偿()
    calculator.resize(1200, 800)
    calculator.setWindowTitle("管道补偿计算器")
    calculator.show()
    
    sys.exit(app.exec())