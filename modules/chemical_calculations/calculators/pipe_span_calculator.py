from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QGridLayout, QMessageBox, QDialog,
    QFileDialog, QDialogButtonBox, QScrollArea, QSizePolicy
)
from PySide6.QtGui import QFont, QDoubleValidator
from PySide6.QtCore import Qt
import math
import re
from datetime import datetime
import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
# DOCX 报告导出


class ProjectInfoDialog(QDialog):
    """工程信息对话框 - 与压降计算模块保持一致"""
    
    def __init__(self, parent=None, default_info=None, report_number=""):
        super().__init__(parent)
        self.default_info = default_info or {}
        self.report_number = report_number
        self.setWindowTitle("工程信息")
        self.setFixedSize(400, 350)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("请输入工程信息")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
        layout.addWidget(title_label)
        
        # 公司名称
        company_layout = QHBoxLayout()
        company_label = QLabel("公司名称:")
        company_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("例如：XX建筑工程有限公司")
        self.company_input.setText(self.default_info.get('company_name', ''))
        company_layout.addWidget(company_label)
        company_layout.addWidget(self.company_input)
        layout.addLayout(company_layout)
        
        # 工程编号
        number_layout = QHBoxLayout()
        number_label = QLabel("工程编号:")
        number_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.project_number_input = QLineEdit()
        self.project_number_input.setPlaceholderText("例如：2024-PD-001")
        self.project_number_input.setText(self.default_info.get('project_number', ''))
        number_layout.addWidget(number_label)
        number_layout.addWidget(self.project_number_input)
        layout.addLayout(number_layout)
        
        # 工程名称
        project_layout = QHBoxLayout()
        project_label = QLabel("工程名称:")
        project_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.project_input = QLineEdit()
        self.project_input.setPlaceholderText("例如：化工厂管道系统")
        self.project_input.setText(self.default_info.get('project_name', ''))
        project_layout.addWidget(project_label)
        project_layout.addWidget(self.project_input)
        layout.addLayout(project_layout)
        
        # 子项名称
        subproject_layout = QHBoxLayout()
        subproject_label = QLabel("子项名称:")
        subproject_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.subproject_input = QLineEdit()
        self.subproject_input.setPlaceholderText("例如：主生产区管道")
        self.subproject_input.setText(self.default_info.get('subproject_name', ''))
        subproject_layout.addWidget(subproject_label)
        subproject_layout.addWidget(self.subproject_input)
        layout.addLayout(subproject_layout)
        
        # 计算书编号
        report_number_layout = QHBoxLayout()
        report_number_label = QLabel("计算书编号:")
        report_number_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.report_number_input = QLineEdit()
        self.report_number_input.setText(self.report_number)
        report_number_layout.addWidget(report_number_label)
        report_number_layout.addWidget(self.report_number_input)
        layout.addLayout(report_number_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def get_info(self):
        return {
            'company_name': self.company_input.text().strip(),
            'project_number': self.project_number_input.text().strip(),
            'project_name': self.project_input.text().strip(),
            'subproject_name': self.subproject_input.text().strip(),
            'report_number': self.report_number_input.text().strip()
        }

class 管道跨距(CalculatorBase):
    """管道跨距计算（按照压降计算模块UI风格重新设计）"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        
        # 使用传入的数据管理器或创建新的
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        
        self.setup_ui()
        self.setup_default_values()

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
        """设置左右布局的管道跨距计算UI - 与压降计算模块保持一致"""
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
        
        # 1. 首先添加说明文本
        description = QLabel(
            "计算管道在不同支撑条件下的最大允许跨距。考虑管道重量、流体重量和保温层重量。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 2. 输入参数组 - 使用GridLayout实现整齐的布局
        input_group = QGroupBox("输入参数")
        
        # 使用GridLayout确保整齐排列
        input_layout = QGridLayout(input_group)
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)
        
        # 标签样式 - 右对齐
        label_style = "font-weight: bold; padding-right: 10px;"
        
        
        row = 0
        
        # 管道外径
        od_label = QLabel("管道外径 (mm):")
        od_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        od_label.setStyleSheet(label_style)
        input_layout.addWidget(od_label, row, 0)
        
        self.od_input = QLineEdit()
        self.od_input.setPlaceholderText("输入外径值")
        self.od_input.setValidator(QDoubleValidator(1.0, 2000.0, 6))
        self.od_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.od_input, row, 1)
        
        self.od_combo = QComboBox()
        self.od_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_od_options()
        self.od_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.od_combo.currentTextChanged.connect(self.on_od_changed)
        input_layout.addWidget(self.od_combo, row, 2)
        
        row += 1
        
        # 管道壁厚
        thickness_label = QLabel("管道壁厚 (mm):")
        thickness_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        thickness_label.setStyleSheet(label_style)
        input_layout.addWidget(thickness_label, row, 0)
        
        self.thickness_input = QLineEdit()
        self.thickness_input.setPlaceholderText("输入壁厚值")
        self.thickness_input.setValidator(QDoubleValidator(0.1, 100.0, 6))
        self.thickness_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.thickness_input, row, 1)
        
        self.thickness_combo = QComboBox()
        self.thickness_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_thickness_options()
        self.thickness_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.thickness_combo.currentTextChanged.connect(self.on_thickness_changed)
        input_layout.addWidget(self.thickness_combo, row, 2)
        
        row += 1
        
        # 管道材料
        material_label = QLabel("管道材料:")
        material_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        material_label.setStyleSheet(label_style)
        input_layout.addWidget(material_label, row, 0)
        
        self.material_combo = QComboBox()
        self.material_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_material_options()
        self.material_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.material_combo.currentTextChanged.connect(self.on_material_changed)
        input_layout.addWidget(self.material_combo, row, 1)
        
        # 材料属性提示标签
        self.material_hint = QLabel("根据材料自动计算")
        self.material_hint.setStyleSheet("font-style: italic;")
        self.material_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.material_hint, row, 2)
        
        row += 1
        
        # 流体密度
        fluid_label = QLabel("流体密度 (kg/m³):")
        fluid_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fluid_label.setStyleSheet(label_style)
        input_layout.addWidget(fluid_label, row, 0)
        
        self.fluid_density_input = QLineEdit()
        self.fluid_density_input.setPlaceholderText("输入流体密度")
        self.fluid_density_input.setValidator(QDoubleValidator(0.0, 20000.0, 6))
        self.fluid_density_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.fluid_density_input, row, 1)
        
        self.fluid_combo = QComboBox()
        self.fluid_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_fluid_options()
        self.fluid_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.fluid_combo.currentTextChanged.connect(self.on_fluid_changed)
        input_layout.addWidget(self.fluid_combo, row, 2)
        
        row += 1
        
        # 保温层厚度
        insulation_label = QLabel("保温层厚度 (mm):")
        insulation_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        insulation_label.setStyleSheet(label_style)
        input_layout.addWidget(insulation_label, row, 0)
        
        self.insulation_input = QLineEdit()
        self.insulation_input.setPlaceholderText("输入保温层厚度")
        self.insulation_input.setValidator(QDoubleValidator(0.0, 500.0, 6))
        self.insulation_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.insulation_input, row, 1)
        
        self.insulation_combo = QComboBox()
        self.insulation_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_insulation_options()
        self.insulation_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.insulation_combo.currentTextChanged.connect(self.on_insulation_changed)
        input_layout.addWidget(self.insulation_combo, row, 2)
        
        row += 1
        
        # 保温层密度
        insulation_density_label = QLabel("保温层密度 (kg/m³):")
        insulation_density_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        insulation_density_label.setStyleSheet(label_style)
        input_layout.addWidget(insulation_density_label, row, 0)
        
        self.insulation_density_input = QLineEdit()
        self.insulation_density_input.setPlaceholderText("输入保温层密度")
        self.insulation_density_input.setValidator(QDoubleValidator(0.0, 2000.0, 6))
        self.insulation_density_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.insulation_density_input, row, 1)
        
        self.insulation_density_combo = QComboBox()
        self.insulation_density_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_insulation_density_options()
        self.insulation_density_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.insulation_density_combo.currentTextChanged.connect(self.on_insulation_density_changed)
        input_layout.addWidget(self.insulation_density_combo, row, 2)
        
        row += 1
        
        # 允许应力
        stress_label = QLabel("允许应力 (MPa):")
        stress_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        stress_label.setStyleSheet(label_style)
        input_layout.addWidget(stress_label, row, 0)
        
        self.stress_input = QLineEdit()
        self.stress_input.setPlaceholderText("输入允许应力值")
        self.stress_input.setValidator(QDoubleValidator(1.0, 1000.0, 6))
        self.stress_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.stress_input, row, 1)
        
        self.stress_combo = QComboBox()
        self.stress_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_stress_options()
        self.stress_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stress_combo.currentTextChanged.connect(self.on_stress_changed)
        input_layout.addWidget(self.stress_combo, row, 2)
        
        left_layout.addWidget(input_group)
        
        # 3. 计算按钮
        calculate_btn = QPushButton("计算")
        calculate_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calculate_btn.clicked.connect(self.calculate_span)
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
        calculate_btn.setMinimumHeight(50)
        calculate_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        left_layout.addWidget(calculate_btn)
        
        # 4. 底部按钮行
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
        
        # 5. 在底部添加拉伸因子
        left_layout.addStretch()
        
        # 右侧：结果显示区域 (占1/3宽度)
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        
        # 结果显示
        self.result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(self.result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
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
        
        # 设置默认值
        self.setup_default_values()
    
    def setup_od_options(self):
        """设置管道外径选项"""
        od_options = [
            "- 请选择管道外径 -",
            "21.3 mm - DN15 [1/2\"]",
            "26.9 mm - DN20 [3/4\"]",
            "33.7 mm - DN25 [1\"]",
            "42.4 mm - DN32 [1¼\"]", 
            "48.3 mm - DN40 [1½\"]",
            "60.3 mm - DN50 [2\"]",
            "76.1 mm - DN65 [2½\"]",
            "88.9 mm - DN80 [3\"]",
            "114.3 mm - DN100 [4\"]",
            "139.7 mm - DN125 [5\"]",
            "168.3 mm - DN150 [6\"]",
            "219.1 mm - DN200 [8\"]",
            "273.0 mm - DN250 [10\"]",
            "323.9 mm - DN300 [12\"]",
            "自定义外径"
        ]
        self.od_combo.addItems(od_options)
        self.od_combo.setCurrentIndex(0)
    
    def setup_thickness_options(self):
        """设置管道壁厚选项"""
        thickness_options = [
            "- 请选择管道壁厚 -",
            "SCH 10 - 薄壁",
            "SCH 20 - 标准壁厚", 
            "SCH 40 - 厚壁",
            "SCH 80 - 加厚壁",
            "SCH 160 - 特厚壁",
            "自定义壁厚"
        ]
        self.thickness_combo.addItems(thickness_options)
        self.thickness_combo.setCurrentIndex(0)
    
    def setup_material_options(self):
        """设置管道材料选项"""
        material_options = [
            "- 请选择管道材料 -",
            "碳钢 - 密度: 7850 kg/m³, 弹性模量: 200 GPa",
            "不锈钢304 - 密度: 7930 kg/m³, 弹性模量: 193 GPa",
            "不锈钢316 - 密度: 8000 kg/m³, 弹性模量: 193 GPa",
            "铜 - 密度: 8960 kg/m³, 弹性模量: 110 GPa",
            "铝 - 密度: 2700 kg/m³, 弹性模量: 69 GPa",
            "PVC - 密度: 1380 kg/m³, 弹性模量: 3 GPa",
            "自定义材料"
        ]
        self.material_combo.addItems(material_options)
        self.material_combo.setCurrentIndex(0)
        
        # 设置材料数据字典
        self.material_data = {}
        for option in material_options[1:]:  # 跳过空选项
            if "自定义" not in option:
                parts = option.split(" - ")
                name = parts[0]
                props = parts[1]
                
                density_str = props.split("密度: ")[1].split(", 弹性模量")[0].replace(" kg/m³", "")
                modulus_str = props.split("弹性模量: ")[1].replace(" GPa", "")
                
                self.material_data[option] = (float(density_str), float(modulus_str))
    
    def setup_fluid_options(self):
        """设置流体密度选项"""
        fluid_options = [
            "- 请选择流体密度 -",
            "0 - 空管",
            "1000 - 水",
            "789 - 乙醇", 
            "719 - 汽油",
            "850 - 柴油",
            "1261 - 甘油",
            "13600 - 汞",
            "自定义密度"
        ]
        self.fluid_combo.addItems(fluid_options)
        self.fluid_combo.setCurrentIndex(0)
    
    def setup_insulation_options(self):
        """设置保温层厚度选项"""
        insulation_options = [
            "- 请选择保温层厚度 -",
            "0 - 无保温",
            "25 - 薄保温",
            "50 - 标准保温", 
            "75 - 厚保温",
            "100 - 超厚保温",
            "自定义厚度"
        ]
        self.insulation_combo.addItems(insulation_options)
        self.insulation_combo.setCurrentIndex(0)
    
    def setup_insulation_density_options(self):
        """设置保温层密度选项"""
        insulation_density_options = [
            "- 请选择保温层密度 -",
            "50 - 玻璃棉",
            "100 - 岩棉",
            "200 - 硅酸铝", 
            "300 - 泡沫玻璃",
            "自定义密度"
        ]
        self.insulation_density_combo.addItems(insulation_density_options)
        self.insulation_density_combo.setCurrentIndex(0)
    
    def setup_stress_options(self):
        """设置允许应力选项"""
        stress_options = [
            "- 请选择允许应力 -",
            "137.9 MPa - 碳钢(A53)",
            "172.4 MPa - 高强度钢",
            "117.2 MPa - 不锈钢304",
            "34.5 MPa - PVC",
            "82.7 MPa - 铝",
            "自定义应力"
        ]
        self.stress_combo.addItems(stress_options)
        self.stress_combo.setCurrentIndex(0)
    
    def setup_default_values(self):
        """设置默认值"""
        # 不预先填入数值，只设置下拉框默认选项
        self.od_combo.setCurrentIndex(8)  # DN100
        self.thickness_combo.setCurrentIndex(3)  # SCH 40
        self.material_combo.setCurrentIndex(1)  # 碳钢
        self.fluid_combo.setCurrentIndex(2)  # 水
        self.insulation_combo.setCurrentIndex(3)  # 标准保温
        self.insulation_density_combo.setCurrentIndex(2)  # 硅酸铝
        self.stress_combo.setCurrentIndex(1)  # 碳钢
    
    def on_od_changed(self, text):
        """处理外径选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.od_input.clear()
            return
            
        if "自定义" in text:
            self.od_input.setReadOnly(False)
            self.od_input.setPlaceholderText("输入自定义外径")
            self.od_input.clear()
        else:
            self.od_input.setReadOnly(False)
            try:
                # 从选项文本中提取数值
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    od_value = float(match.group(1))
                    self.od_input.setText(f"{od_value}")
            except:
                pass
    
    def on_thickness_changed(self, text):
        """处理壁厚选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.thickness_input.clear()
            return
            
        if "自定义" in text:
            self.thickness_input.setReadOnly(False)
            self.thickness_input.setPlaceholderText("输入自定义壁厚")
            self.thickness_input.clear()
        else:
            self.thickness_input.setReadOnly(False)
            # 根据选项设置默认值
            if "SCH 10" in text:
                self.thickness_input.setText("3.05")
            elif "SCH 20" in text:
                self.thickness_input.setText("3.40")
            elif "SCH 40" in text:
                self.thickness_input.setText("6.02")
            elif "SCH 80" in text:
                self.thickness_input.setText("8.56")
            elif "SCH 160" in text:
                self.thickness_input.setText("13.49")
    
    def on_material_changed(self, text):
        """处理材料选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            return
            
        if "自定义" in text:
            self.material_hint.setText("需要手动输入属性")
        else:
            # 更新提示标签
            if " - " in text:
                self.material_hint.setText(text.split(" - ")[1])
    
    def on_fluid_changed(self, text):
        """处理流体密度选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.fluid_density_input.clear()
            return
            
        if "自定义" in text:
            self.fluid_density_input.setReadOnly(False)
            self.fluid_density_input.setPlaceholderText("输入自定义密度")
            self.fluid_density_input.clear()
        else:
            self.fluid_density_input.setReadOnly(False)
            # 从选项文本中提取数值
            try:
                match = re.search(r'(\d+)', text)
                if match:
                    density_value = float(match.group(1))
                    self.fluid_density_input.setText(f"{density_value}")
            except:
                pass
    
    def on_insulation_changed(self, text):
        """处理保温层厚度选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.insulation_input.clear()
            return
            
        if "自定义" in text:
            self.insulation_input.setReadOnly(False)
            self.insulation_input.setPlaceholderText("输入自定义厚度")
            self.insulation_input.clear()
        else:
            self.insulation_input.setReadOnly(False)
            # 从选项文本中提取数值
            try:
                match = re.search(r'(\d+)', text)
                if match:
                    thickness_value = float(match.group(1))
                    self.insulation_input.setText(f"{thickness_value}")
            except:
                pass
    
    def on_insulation_density_changed(self, text):
        """处理保温层密度选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.insulation_density_input.clear()
            return
            
        if "自定义" in text:
            self.insulation_density_input.setReadOnly(False)
            self.insulation_density_input.setPlaceholderText("输入自定义密度")
            self.insulation_density_input.clear()
        else:
            self.insulation_density_input.setReadOnly(False)
            # 从选项文本中提取数值
            try:
                match = re.search(r'(\d+)', text)
                if match:
                    density_value = float(match.group(1))
                    self.insulation_density_input.setText(f"{density_value}")
            except:
                pass
    
    def on_stress_changed(self, text):
        """处理允许应力选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.stress_input.clear()
            return
            
        if "自定义" in text:
            self.stress_input.setReadOnly(False)
            self.stress_input.setPlaceholderText("输入自定义应力")
            self.stress_input.clear()
        else:
            self.stress_input.setReadOnly(False)
            # 从选项文本中提取数值
            try:
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    stress_value = float(match.group(1))
                    self.stress_input.setText(f"{stress_value}")
            except:
                pass
    
    def get_material_properties(self):
        """获取材料属性"""
        text = self.material_combo.currentText()
        
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            # 默认碳钢属性
            return 7850, 200e9
        
        if "碳钢" in text:
            return 7850, 200e9
        elif "不锈钢304" in text:
            return 7930, 193e9
        elif "不锈钢316" in text:
            return 8000, 193e9
        elif "铜" in text:
            return 8960, 110e9
        elif "铝" in text:
            return 2700, 69e9
        elif "PVC" in text:
            return 1380, 3e9
        else:
            return 7850, 200e9  # 默认碳钢
    
    def get_od_value(self):
        """获取外径值"""
        text = self.od_combo.currentText()

        # 检查是否为空值选项
        if text.startswith("-") or not text.strip():
            # 如果没有选择，尝试从输入框获取
            try:
                return float(self.od_input.text() or 0) / 1000
            except:
                return 0.1143  # 默认DN100
        
        # 尝试从文本中提取数字
        try:
            # 匹配第一个数字
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                od_mm = float(match.group(1))
                return od_mm / 1000  # 转换为米
        except:
            pass
        
        # 如果无法解析，尝试直接转换
        try:
            return float(text) / 1000
        except:
            # 默认值
            return 0.1143
    
    def get_thickness_value(self):
        """获取壁厚值"""
        text = self.thickness_combo.currentText()

        # 检查是否为空值选项
        if text.startswith("-") or not text.strip():
            # 如果没有选择，尝试从输入框获取
            try:
                return float(self.thickness_input.text() or 0) / 1000
            except:
                return 0.00602  # 默认SCH40
        
        # 尝试从文本中提取数字
        try:
            return float(self.thickness_input.text() or 0) / 1000
        except:
            # 默认值
            return 0.00602
    
    def calculate_span(self):
        """计算管道跨距"""
        try:
            # 获取输入值
            od = self.get_od_value()
            thickness = self.get_thickness_value()
            material_density, elastic_modulus = self.get_material_properties()
            fluid_density = float(self.fluid_density_input.text() or 0)
            insulation_thickness = float(self.insulation_input.text() or 0) / 1000
            insulation_density = float(self.insulation_density_input.text() or 0)
            allowable_stress = float(self.stress_input.text() or 0) * 1e6  # 转换为Pa
            
            # 验证输入
            if not all([od, thickness, allowable_stress]):
                QMessageBox.warning(self, "输入错误", "请填写管道外径、壁厚和允许应力")
                return
            
            # 计算管道内径
            id_val = od - 2 * thickness
            
            # 计算截面惯性矩
            I = math.pi * (od**4 - id_val**4) / 64
            
            # 计算截面模量
            Z = math.pi * (od**4 - id_val**4) / (32 * od)
            
            # 计算单位长度重量
            # 管道重量
            pipe_area = math.pi * (od**2 - id_val**2) / 4
            pipe_weight = pipe_area * material_density * 9.81  # N/m
            
            # 流体重量
            if fluid_density > 0:
                fluid_area = math.pi * id_val**2 / 4
                fluid_weight = fluid_area * fluid_density * 9.81  # N/m
            else:
                fluid_weight = 0
            
            # 保温层重量
            if insulation_thickness > 0 and insulation_density > 0:
                insulation_od = od + 2 * insulation_thickness
                insulation_area = math.pi * (insulation_od**2 - od**2) / 4
                insulation_weight = insulation_area * insulation_density * 9.81  # N/m
            else:
                insulation_weight = 0
            
            # 总重量
            total_weight = pipe_weight + fluid_weight + insulation_weight
            
            # 计算最大跨距
            span_stress = math.sqrt(8 * allowable_stress * Z / total_weight)

            # 基于挠度的跨距（简支梁，挠度限 L/360）
            # δ = 5·w·L⁴/(384·E·I) = L/360
            # → L³ = 384·E·I / (360·5·w) = 384·E·I / (1800·w)
            w = total_weight  # N/m
            span_deflection = ((384 * elastic_modulus * I) / (1800 * w)) ** (1/3)
            
            # 取较小值作为推荐跨距
            recommended_span = min(span_stress, span_deflection)

            # 推荐跨距下的实际挠度（用于利用率计算）
            max_deflection = recommended_span / 360  # 允许挠度 L/360
            
            # 显示结果
            result = f"""═══════════
 输入参数
══════════

    管道参数:
    • 外径: {od*1000:.1f} mm
    • 内径: {id_val*1000:.1f} mm  
    • 壁厚: {thickness*1000:.1f} mm

    材料参数:
    • 管道材料密度: {material_density} kg/m³
    • 弹性模量: {elastic_modulus/1e9:.0f} GPa
    • 允许应力: {allowable_stress/1e6:.1f} MPa

    载荷参数:
    • 流体密度: {fluid_density} kg/m³
    • 保温层厚度: {insulation_thickness*1000:.0f} mm
    • 保温层密度: {insulation_density} kg/m³

══════════
计算结果
══════════

    重量计算:
    • 管道重量: {pipe_weight:.2f} N/m
    • 流体重量: {fluid_weight:.2f} N/m
    • 保温层重量: {insulation_weight:.2f} N/m
    • 总重量: {total_weight:.2f} N/m

    跨距计算结果:
    • 基于应力限制: {span_stress:.2f} m
    • 基于挠度限制: {span_deflection:.2f} m
    • 推荐最大跨距: {recommended_span:.2f} m

    安全评估:
    • 应力利用率: {total_weight * recommended_span**2 / (8 * Z) / allowable_stress * 100:.1f}%
    • 挠度利用率: {total_weight * recommended_span**4 / (384 * elastic_modulus * I) / max_deflection * 100:.1f}%

══════════
计算公式
══════════

    应力限制跨距: L = √(8·σ·Z / w)
    挠度限制跨距: L = ⁴√(384·E·I / (5·w·δ_max))

    其中:
    σ = {allowable_stress/1e6:.1f} MPa (允许应力)
    E = {elastic_modulus/1e9:.0f} GPa (弹性模量)
    Z = {Z*1e6:.3f} cm³ (截面模量)
    I = {I*1e8:.3f} cm⁴ (惯性矩)
    w = {total_weight:.2f} N/m (总载荷)
    δ_max = L/360 (最大允许挠度)

══════════
应用说明
══════════

    • 实际跨距应小于计算值，建议取 0.8-0.9 的安全系数
    • 对于振动较大的管道，应进一步减小跨距
    • 重要管道应进行详细的应力分析
    • 计算结果仅供参考，实际设计需符合相关规范"""
            
            self.result_text.setText(result)
            
        except ValueError as e:
            QMessageBox.critical(self, "计算错误", f"参数输入格式错误: {str(e)}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "参数不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def clear_inputs(self):
        """清空所有输入"""
        self.od_combo.setCurrentIndex(0)
        self.thickness_combo.setCurrentIndex(0)
        self.material_combo.setCurrentIndex(0)
        self.fluid_combo.setCurrentIndex(0)
        self.insulation_combo.setCurrentIndex(0)
        self.insulation_density_combo.setCurrentIndex(0)
        self.stress_combo.setCurrentIndex(0)
        self.od_input.clear()
        self.thickness_input.clear()
        self.fluid_density_input.clear()
        self.insulation_input.clear()
        self.insulation_density_input.clear()
        self.stress_input.clear()
        self.result_text.clear()

    def _get_history_data(self):
        """提供历史记录数据"""
        od = self.get_od_value()
        thickness = self.get_thickness_value()
        material_density, elastic_modulus = self.get_material_properties()
        fluid_density = float(self.fluid_density_input.text() or 0)
        insulation_thickness = float(self.insulation_input.text() or 0) / 1000
        insulation_density = float(self.insulation_density_input.text() or 0)
        allowable_stress = float(self.stress_input.text() or 0) * 1e6

        inputs = {
            "管道外径_mm": round(od * 1000, 1),
            "壁厚_mm": round(thickness * 1000, 1),
            "材料密度_kg_m3": material_density,
            "流体密度_kg_m3": fluid_density,
            "保温层厚度_mm": insulation_thickness * 1000,
            "保温层密度_kg_m3": insulation_density,
            "允许应力_MPa": float(self.stress_input.text() or 0)
        }

        outputs = {}
        try:
            id_val = od - 2 * thickness
            I = math.pi * (od**4 - id_val**4) / 64
            Z = math.pi * (od**4 - id_val**4) / (32 * od)
            pipe_area = math.pi * (od**2 - id_val**2) / 4
            pipe_weight = pipe_area * material_density * 9.81
            fluid_area = math.pi * id_val**2 / 4
            fluid_weight = fluid_area * fluid_density * 9.81 if fluid_density > 0 else 0
            insulation_od = od + 2 * insulation_thickness
            insulation_area = math.pi * (insulation_od**2 - od**2) / 4
            insulation_weight = insulation_area * insulation_density * 9.81 if insulation_thickness > 0 and insulation_density > 0 else 0
            total_weight = pipe_weight + fluid_weight + insulation_weight
            # 基于应力的跨距（应力限制）
            span_stress = math.sqrt(8 * allowable_stress * Z / total_weight)

            # 基于挠度的跨距（简支梁，挠度限 L/360）
            w = total_weight  # N/m
            span_deflection = ((384 * elastic_modulus * I) / (1800 * w)) ** (1/3)
            recommended_span = min(span_stress, span_deflection)

            outputs = {
                "管道内径_mm": round(id_val * 1000, 1),
                "总重量_N_m": round(total_weight, 2),
                "基于应力跨距_m": round(span_stress, 2),
                "基于挠度跨距_m": round(span_deflection, 2),
                "推荐最大跨距_m": round(recommended_span, 2)
            }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        """获取工程信息 - 与压降计算模块保持一致"""
        try:
            # 从数据管理器获取共享的项目信息
            saved_info = {}
            if self.data_manager:
                saved_info = self.data_manager.get_project_info()
            
            # 获取下一个报告编号
            report_number = ""
            if self.data_manager:
                report_number = self.data_manager.get_next_report_number("SPAN")
            
            dialog = ProjectInfoDialog(self, saved_info, report_number)
            if dialog.exec() == QDialog.Accepted:
                info = dialog.get_info()
                # 验证必填字段
                if not info['project_name']:
                    QMessageBox.warning(self, "输入错误", "工程名称不能为空")
                    return self.get_project_info()  # 重新弹出对话框
                
                # 保存项目信息到数据管理器
                if self.data_manager:
                    # 保存所有项目信息（使用新版字段名）
                    info_to_save = {
                        'company_name': info['company_name'],
                        'project_number': info['project_number'],
                        'project_name': info['project_name'],
                        'subproject_name': info['subproject_name']
                    }
                    self.data_manager.update_project_info(info_to_save)
                    print("项目信息已保存")
                
                return info
            else:
                return None  # 用户取消了
                    
        except Exception as e:
            print(f"获取工程信息失败: {e}")
            return None
    
    def generate_report(self):
        """生成计算书"""
        try:
            # 获取当前结果文本
            result_text = self.result_text.toPlainText()
            
            # 检查条件
            if not result_text or ("计算结果" not in result_text and "跨距计算结果" not in result_text):
                QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
                return None
                
            # 获取工程信息
            project_info = self.get_project_info()
            if not project_info:
                return None  # 用户取消了输入
            
            # 添加报告头信息
            report = f"""工程计算书 - 管道跨距计算
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

    计算书编号: {project_info['report_number']}
    版本: 1.0
    状态: 正式计算书

══════════
备注说明
══════════

    1. 本计算书基于结构力学原理及相关标准规范
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
        ReportExporter.export_docx(self, "管道跨距")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "管道跨距")
    def process_content_for_pdf(self, content):
        """处理内容，使其适合PDF显示"""
        # 清理bullet符号
        content = content.replace("•", "")
        
        # 替换单位符号
        content = content.replace("m³", "m3")
        content = content.replace("kg/m³", "kg/m3")
        
        return content

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = 管道跨距()
    calculator.resize(1200, 800)
    calculator.show()
    
    sys.exit(app.exec())