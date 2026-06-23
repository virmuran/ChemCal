"""
管道间距计算器 - 依据化工部标准HG/T20592~20623-2009
参照GB50316和SH3012标准
管廊上管道净距：50mm，法兰外缘与相邻管道净距：25mm
"""

from PySide6.QtWidgets import (
    QSizePolicy, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QGroupBox, QFormLayout, QPushButton, 
    QGridLayout, QFrame, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QDoubleValidator, QIntValidator
import math
import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
# DOCX 报告导出

class 管道间距(CalculatorBase):
    """专业的管道间距计算器 - 依据化工部标准"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setup_ui()
        
        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

        # 初始化法兰数据
        self.flange_data = self.load_flange_data()
        
        # 初始化结果
        self.results = {
            'spacing_basic': 0,      # 基础间距
            'spacing_flange': 0,     # 考虑法兰间距
            'spacing_final': 0,      # 最终间距
            'flange_od1': 0,         # 管道1法兰外径
            'flange_od2': 0,         # 管道2法兰外径
            'pipe_od1': 0,           # 管道1外径
            'pipe_od2': 0            # 管道2外径
        }
        
    def setup_ui(self):
        """设置UI界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建两列布局
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # 左侧：输入参数
        input_widget = self.create_input_section()
        content_layout.addWidget(input_widget, 1)
        
        # 右侧：结果和示意图
        output_widget = self.create_output_section()
        content_layout.addWidget(output_widget, 1)
        
        main_layout.addLayout(content_layout)
        
        # 计算按钮
        self.calculate_btn = QPushButton("计算")
        self.calculate_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.calculate_btn.clicked.connect(self.calculate_spacing)
        self.calculate_btn.setMinimumHeight(50)
        self.calculate_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.calculate_btn.setStyleSheet("""
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
        main_layout.addWidget(self.calculate_btn)
        
        # 底部按钮
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
        main_layout.addLayout(bottom_layout)
        
    def create_input_section(self):
        """创建输入参数区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # 创建管道参数组（双列）
        pipes_group = QGroupBox("管道参数")
        pipes_layout = QGridLayout()
        pipes_layout.setVerticalSpacing(10)
        pipes_layout.setHorizontalSpacing(15)
        
        # 表头
        pipes_layout.addWidget(QLabel("<b>参数</b>"), 0, 0)
        pipes_layout.addWidget(QLabel("<b>管道 1</b>"), 0, 1)
        pipes_layout.addWidget(QLabel("<b>管道 2</b>"), 0, 2)
        
        # 单位制选择
        pipes_layout.addWidget(QLabel("单位制:"), 1, 0)
        self.unit_combo = QComboBox()
        self.unit_combo.setStyleSheet(COMBOBOX_STYLE)
        self.unit_combo.addItems(["公制 (DN/mm)", "英制 (NPS/inch)"])
        self.unit_combo.currentIndexChanged.connect(self.on_unit_changed)
        pipes_layout.addWidget(self.unit_combo, 1, 1, 1, 2)
        
        # 公称直径
        pipes_layout.addWidget(QLabel("公称直径:"), 2, 0)
        self.dn_input1 = QComboBox()
        self.dn_input1.setStyleSheet(COMBOBOX_STYLE)
        self.dn_input1.setEditable(True)
        self.dn_input2 = QComboBox()
        self.dn_input2.setStyleSheet(COMBOBOX_STYLE)
        self.dn_input2.setEditable(True)
        pipes_layout.addWidget(self.dn_input1, 2, 1)
        pipes_layout.addWidget(self.dn_input2, 2, 2)
        
        # 法兰等级
        pipes_layout.addWidget(QLabel("法兰等级:"), 3, 0)
        self.flange_combo1 = QComboBox()
        self.flange_combo1.setStyleSheet(COMBOBOX_STYLE)
        self.flange_combo2 = QComboBox()
        self.flange_combo2.setStyleSheet(COMBOBOX_STYLE)
        pipes_layout.addWidget(self.flange_combo1, 3, 1)
        pipes_layout.addWidget(self.flange_combo2, 3, 2)
        
        # 保温厚度
        pipes_layout.addWidget(QLabel("保温厚度 (mm):"), 4, 0)
        self.insulation_input1 = QLineEdit("0")
        self.insulation_input2 = QLineEdit("0")
        pipes_layout.addWidget(self.insulation_input1, 4, 1)
        pipes_layout.addWidget(self.insulation_input2, 4, 2)
        
        # 是否保温
        pipes_layout.addWidget(QLabel("是否保温:"), 5, 0)
        self.insulation_check1 = QCheckBox("是")
        self.insulation_check2 = QCheckBox("是")
        pipes_layout.addWidget(self.insulation_check1, 5, 1)
        pipes_layout.addWidget(self.insulation_check2, 5, 2)
        
        pipes_group.setLayout(pipes_layout)
        layout.addWidget(pipes_group)
        
        # 布置参数组
        layout_group = QGroupBox("布置参数")
        layout_group
        layout_form = QFormLayout()
        layout_form.setVerticalSpacing(10)
        layout_form.setHorizontalSpacing(15)
        
        # 布置方式
        self.layout_combo = QComboBox()
        self.layout_combo.setStyleSheet(COMBOBOX_STYLE)
        self.layout_combo.addItems(["水平平行", "上下平行", "垂直交叉", "L形布置"])
        layout_form.addRow("布置方式:", self.layout_combo)
        
        # 管廊类型
        self.rack_type_combo = QComboBox()
        self.rack_type_combo.setStyleSheet(COMBOBOX_STYLE)
        self.rack_type_combo.addItems(["管廊", "管墩", "地面", "架空"])
        layout_form.addRow("支承类型:", self.rack_type_combo)
        
        # 是否考虑热位移
        self.thermal_check = QCheckBox("考虑热位移")
        self.thermal_check.setChecked(True)
        layout_form.addRow("热位移:", self.thermal_check)
        
        # 热位移量 (mm)
        self.thermal_input = QLineEdit("10")
        self.thermal_input.setValidator(QDoubleValidator(0, 100, 1))
        layout_form.addRow("热位移量 (mm):", self.thermal_input)
        
        layout_group.setLayout(layout_form)
        layout.addWidget(layout_group)
        
        # 特殊要求组
        special_group = QGroupBox("特殊要求")
        special_group
        special_form = QFormLayout()
        
        # 法兰面对面布置
        self.flange_face_check = QCheckBox("法兰面对面布置")
        special_form.addRow("特殊布置:", self.flange_face_check)
        
        # 是否含阀门
        self.valve_check1 = QCheckBox("管道1含阀门")
        self.valve_check2 = QCheckBox("管道2含阀门")
        special_form.addRow("阀门:", self.valve_check1)
        special_form.addRow("", self.valve_check2)
        
        # 是否含仪表
        self.instrument_check = QCheckBox("含仪表/管件")
        special_form.addRow("仪表管件:", self.instrument_check)
        
        special_group.setLayout(special_form)
        layout.addWidget(special_group)
        
        # 初始加载数据
        self.load_initial_data()
        
        return widget
    
    def create_output_section(self):
        """创建输出结果区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 计算结果组
        result_group = QGroupBox("计算结果")
        result_group
        result_layout = QVBoxLayout()
        
        # 主要结果
        self.result_main_label = QLabel("点击计算按钮开始计算")
        self.result_main_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.result_main_label.setAlignment(Qt.AlignCenter)
        self.result_main_label.setStyleSheet("""
            /* color via theme */
            /* bg via theme */
            padding: 15px;
            border-radius: 8px;
            border: 2px solid #27ae60;
        """)
        result_layout.addWidget(self.result_main_label)
        
        # 详细结果
        self.result_detail_label = QLabel("")
        self.result_detail_label.setStyleSheet("""
            /* color via theme */
            font-size: 13px;
            padding: 10px;
            /* bg via theme */
            border-radius: 5px;
        """)
        self.result_detail_label.setWordWrap(True)
        result_layout.addWidget(self.result_detail_label)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        # 标准间距表组
        table_group = QGroupBox("标准间距要求")
        table_group
        table_layout = QVBoxLayout()
        
        table_text = QLabel(
            "根据SH3012-2011标准要求：\n\n"
            "• 管廊上布置的管道（不论有无保温）：\n"
            "   管道间净距 ≥ 50mm\n\n"
            "• 法兰外缘与相邻管道：\n"
            "   最小净距 ≥ 25mm\n\n"
            "• 管道与结构/设备：\n"
            "   最小净距 ≥ 100mm\n\n"
            "• 含阀门的管道：\n"
            "   需增加操作空间 ≥ 300mm"
        )
        table_text.setStyleSheet("color: #7f8c8d; font-size: 12px; padding: 10px;")
        table_text.setWordWrap(True)
        table_layout.addWidget(table_text)
        
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        # 计算原理说明
        principle_group = QGroupBox("计算原理")
        principle_group
        principle_layout = QVBoxLayout()
        
        principle_text = QLabel(
            "计算步骤：\n"
            "1. 根据DN/NPS和法兰等级查取法兰外径\n"
            "2. 计算基础间距 = 管道外径/2 + 相邻管道外径/2 + 50mm\n"
            "3. 计算法兰间距 = 法兰外径/2 + 相邻法兰外径/2 + 25mm\n"
            "4. 最终间距取两者较大值\n"
            "5. 考虑保温层、热位移、阀门等附加要求"
        )
        principle_text.setStyleSheet("color: #34495e; font-size: 12px; padding: 10px;")
        principle_text.setWordWrap(True)
        principle_layout.addWidget(principle_text)
        
        principle_group.setLayout(principle_layout)
        layout.addWidget(principle_group)
        
        return widget
    
    def clear_inputs(self):
        """清空所有输入参数"""
        for widget in self.findChildren((QLineEdit, QComboBox)):
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "管道间距")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "管道间距")
    def load_flange_data(self):
        """加载法兰标准数据（简化版，实际应使用完整数据库）"""
        # HG/T20592-2009 PN系列法兰外径数据（单位：mm）
        # 格式: {DN: {法兰等级: 外径}}
        flange_data = {
            # PN10/16 系列
            15: {'PN10': 65, 'PN16': 65, 'PN25': 65, 'PN40': 65, 'PN63': 65, 'PN100': 65},
            20: {'PN10': 75, 'PN16': 75, 'PN25': 75, 'PN40': 75, 'PN63': 75, 'PN100': 75},
            25: {'PN10': 85, 'PN16': 85, 'PN25': 85, 'PN40': 85, 'PN63': 85, 'PN100': 85},
            32: {'PN10': 100, 'PN16': 100, 'PN25': 100, 'PN40': 100, 'PN63': 100, 'PN100': 100},
            40: {'PN10': 110, 'PN16': 110, 'PN25': 110, 'PN40': 110, 'PN63': 110, 'PN100': 110},
            50: {'PN10': 125, 'PN16': 125, 'PN25': 125, 'PN40': 125, 'PN63': 125, 'PN100': 140},
            65: {'PN10': 145, 'PN16': 145, 'PN25': 145, 'PN40': 145, 'PN63': 145, 'PN100': 160},
            80: {'PN10': 160, 'PN16': 160, 'PN25': 160, 'PN40': 160, 'PN63': 160, 'PN100': 190},
            100: {'PN10': 180, 'PN16': 180, 'PN25': 190, 'PN40': 190, 'PN63': 190, 'PN100': 230},
            125: {'PN10': 210, 'PN16': 210, 'PN25': 220, 'PN40': 220, 'PN63': 220, 'PN100': 270},
            150: {'PN10': 240, 'PN16': 240, 'PN25': 250, 'PN40': 250, 'PN63': 250, 'PN100': 300},
            200: {'PN10': 295, 'PN16': 295, 'PN25': 310, 'PN40': 320, 'PN63': 320, 'PN100': 360},
            250: {'PN10': 350, 'PN16': 350, 'PN25': 370, 'PN40': 385, 'PN63': 385, 'PN100': 425},
            300: {'PN10': 400, 'PN16': 400, 'PN25': 430, 'PN40': 450, 'PN63': 450, 'PN100': 485},
            350: {'PN10': 460, 'PN16': 460, 'PN25': 490, 'PN40': 510, 'PN63': 510, 'PN100': 555},
            400: {'PN10': 515, 'PN16': 515, 'PN25': 550, 'PN40': 585, 'PN63': 585, 'PN100': 620},
            450: {'PN10': 565, 'PN16': 565, 'PN25': 600, 'PN40': 610, 'PN63': 610, 'PN100': 660},
            500: {'PN10': 615, 'PN16': 615, 'PN25': 660, 'PN40': 670, 'PN63': 670, 'PN100': 730},
        }
        return flange_data
    
    def load_initial_data(self):
        """初始化加载数据"""
        # 初始化公称直径列表（公制）
        dn_list = ["15", "20", "25", "32", "40", "50", "65", "80", "100", 
                  "125", "150", "200", "250", "300", "350", "400", "450", "500"]
        
        self.dn_input1.addItems(dn_list)
        self.dn_input2.addItems(dn_list)
        self.dn_input1.setCurrentIndex(8)  # 默认DN100
        self.dn_input2.setCurrentIndex(8)  # 默认DN100
        
        # 初始化法兰等级
        flange_grades = ["PN10", "PN16", "PN25", "PN40", "PN63", "PN100"]
        self.flange_combo1.addItems(flange_grades)
        self.flange_combo2.addItems(flange_grades)
        self.flange_combo1.setCurrentIndex(0)  # 默认PN10
        self.flange_combo2.setCurrentIndex(0)  # 默认PN20
        
        # 设置输入验证
        for input_widget in [self.insulation_input1, self.insulation_input2, 
                           self.thermal_input]:
            input_widget.setValidator(QDoubleValidator(0, 1000, 1))
        
    def on_unit_changed(self):
        """单位制改变时的处理"""
        if self.unit_combo.currentText() == "英制 (NPS/inch)":
            # 英制NPS尺寸
            nps_list = ["1/2", "3/4", "1", "1 1/4", "1 1/2", "2", "2 1/2", 
                       "3", "4", "6", "8", "10", "12", "14", "16", "18", "20"]
            self.dn_input1.clear()
            self.dn_input2.clear()
            self.dn_input1.addItems(nps_list)
            self.dn_input2.addItems(nps_list)
            self.dn_input1.setCurrentIndex(3)  # 默认1 1/4"
            self.dn_input2.setCurrentIndex(3)  # 默认1 1/4"
        else:
            # 公制DN尺寸
            self.load_initial_data()
    
    def nps_to_dn(self, nps_str):
        """NPS英制尺寸转换为DN公称直径"""
        nps_to_dn_map = {
            "1/2": 15, "3/4": 20, "1": 25, "1 1/4": 32, "1 1/2": 40,
            "2": 50, "2 1/2": 65, "3": 80, "4": 100, "6": 150,
            "8": 200, "10": 250, "12": 300, "14": 350, "16": 400,
            "18": 450, "20": 500
        }
        return nps_to_dn_map.get(nps_str, 50)
    
    def get_flange_od(self, dn, flange_grade):
        """获取法兰外径"""
        try:
            if isinstance(dn, str):
                # 如果是英制，先转换为DN
                if '"' in dn or "/" in dn or " " in dn:
                    dn = self.nps_to_dn(dn)
                else:
                    dn = int(dn)
            
            # 从数据中查找
            if dn in self.flange_data:
                if flange_grade in self.flange_data[dn]:
                    return self.flange_data[dn][flange_grade]
            
            # 如果没找到，使用估算公式
            return dn * 1.5 + 50  # 简化估算
        except:
            return 100  # 默认值
    
    def get_pipe_od(self, dn):
        """获取管道外径（根据DN估算）"""
        try:
            if isinstance(dn, str):
                # 如果是英制，先转换为DN
                if '"' in dn or "/" in dn or " " in dn:
                    dn = self.nps_to_dn(dn)
                else:
                    dn = int(dn)
            
            # 管道外径估算（根据常用壁厚系列）
            if dn <= 80:
                return dn + 2 * 3.5  # 小口径管道
            elif dn <= 200:
                return dn + 2 * 4.5  # 中口径管道
            else:
                return dn + 2 * 6.0  # 大口径管道
        except:
            return dn * 1.1  # 简化估算
    
    def calculate_spacing(self):
        """计算管道间距 - 依据标准"""
        try:
            # 获取输入参数
            dn1 = self.dn_input1.currentText()
            dn2 = self.dn_input2.currentText()
            
            flange_grade1 = self.flange_combo1.currentText()
            flange_grade2 = self.flange_combo2.currentText()
            
            # 获取保温厚度（如果未保温则为0）
            insulation1 = float(self.insulation_input1.text()) if self.insulation_check1.isChecked() else 0
            insulation2 = float(self.insulation_input2.text()) if self.insulation_check2.isChecked() else 0
            
            # 获取法兰外径
            flange_od1 = self.get_flange_od(dn1, flange_grade1)
            flange_od2 = self.get_flange_od(dn2, flange_grade2)
            
            # 获取管道外径
            pipe_od1 = self.get_pipe_od(dn1)
            pipe_od2 = self.get_pipe_od(dn2)
            
            # 考虑保温层后的管道外径
            pipe_od_with_ins1 = pipe_od1 + 2 * insulation1
            pipe_od_with_ins2 = pipe_od2 + 2 * insulation2
            
            # 根据SH3012标准计算：
            # 1. 基础间距（管道间净距50mm）
            spacing_basic = (pipe_od_with_ins1 + pipe_od_with_ins2) / 2 + 50
            
            # 2. 法兰间距（法兰外缘净距25mm）
            spacing_flange = (flange_od1 + flange_od2) / 2 + 25
            
            # 3. 取两者中的较大值
            spacing_final = max(spacing_basic, spacing_flange)
            
            # 4. 考虑热位移（如果勾选）
            if self.thermal_check.isChecked():
                thermal_displacement = float(self.thermal_input.text())
                spacing_final += thermal_displacement
            
            # 5. 考虑阀门附加空间
            if self.valve_check1.isChecked() or self.valve_check2.isChecked():
                spacing_final += 300  # 阀门操作空间
            
            # 6. 考虑仪表管件
            if self.instrument_check.isChecked():
                spacing_final += 150  # 仪表管件空间
            
            # 7. 考虑法兰面对面布置
            if self.flange_face_check.isChecked():
                spacing_final += 100  # 增加法兰操作空间
            
            # 8. 根据管廊类型调整
            rack_type = self.rack_type_combo.currentText()
            if rack_type == "管墩":
                spacing_final += 50  # 管墩需要更多空间
            elif rack_type == "地面":
                spacing_final += 100  # 地面布置需要维护空间
            
            # 保存结果
            self.results.update({
                'spacing_basic': spacing_basic,
                'spacing_flange': spacing_flange,
                'spacing_final': spacing_final,
                'flange_od1': flange_od1,
                'flange_od2': flange_od2,
                'pipe_od1': pipe_od1,
                'pipe_od2': pipe_od2
            })
            
            # 更新显示
            self.update_results_display()
            
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误:\n{str(e)}")
    
    def update_results_display(self):
        """更新结果显示"""
        # 主要结果
        result_text = f"<span style='color:#27ae60; font-size:16px;'>最小中心距: {self.results['spacing_final']:.1f} mm</span>"
        self.result_main_label.setText(result_text)
        
        # 详细结果
        detail_text = (
            f"<b>计算详情:</b><br>"
            f"• 管道1: DN={self.dn_input1.currentText()}, "
            f"法兰外径={self.results['flange_od1']:.1f}mm, "
            f"管道外径={self.results['pipe_od1']:.1f}mm<br>"
            f"• 管道2: DN={self.dn_input2.currentText()}, "
            f"法兰外径={self.results['flange_od2']:.1f}mm, "
            f"管道外径={self.results['pipe_od2']:.1f}mm<br><br>"
            f"<b>间距计算:</b><br>"
            f"• 基础间距（管廊净距）: {self.results['spacing_basic']:.1f}mm<br>"
            f"• 法兰间距（法兰外缘）: {self.results['spacing_flange']:.1f}mm<br>"
            f"• 附加调整: "
        )
        
        # 添加附加项说明
        adjustments = []
        if self.thermal_check.isChecked():
            adjustments.append(f"热位移 {self.thermal_input.text()}mm")
        if self.valve_check1.isChecked() or self.valve_check2.isChecked():
            adjustments.append("阀门操作空间 300mm")
        if self.instrument_check.isChecked():
            adjustments.append("仪表管件空间 150mm")
        if self.flange_face_check.isChecked():
            adjustments.append("法兰面对面布置 100mm")
        
        if adjustments:
            detail_text += " + ".join(adjustments)
        else:
            detail_text += "无"
        
        self.result_detail_label.setText(detail_text)

    def _get_history_data(self):
        """提供历史记录数据"""
        dn1 = self.dn_input1.currentText()
        dn2 = self.dn_input2.currentText()
        flange_grade1 = self.flange_combo1.currentText()
        flange_grade2 = self.flange_combo2.currentText()
        insulation1 = float(self.insulation_input1.text()) if self.insulation_check1.isChecked() else 0
        insulation2 = float(self.insulation_input2.text()) if self.insulation_check2.isChecked() else 0

        inputs = {
            "管道1_DN": dn1,
            "管道2_DN": dn2,
            "法兰等级1": flange_grade1,
            "法兰等级2": flange_grade2,
            "保温厚度1_mm": insulation1,
            "保温厚度2_mm": insulation2,
            "管廊类型": self.rack_type_combo.currentText(),
            "热位移_mm": float(self.thermal_input.text()) if self.thermal_check.isChecked() else 0
        }

        outputs = {}
        if self.results.get('spacing_final', 0) > 0:
            outputs = {
                "管道1外径_mm": self.results.get('pipe_od1', 0),
                "管道2外径_mm": self.results.get('pipe_od2', 0),
                "法兰1外径_mm": self.results.get('flange_od1', 0),
                "法兰2外径_mm": self.results.get('flange_od2', 0),
                "基础间距_mm": self.results.get('spacing_basic', 0),
                "法兰间距_mm": self.results.get('spacing_flange', 0),
                "最小中心距_mm": self.results.get('spacing_final', 0)
            }
        else:
            outputs["状态"] = "未计算"

        return {"inputs": inputs, "outputs": outputs}

    def reset_inputs(self):
        """重置所有输入到默认值"""
        # 重置单位制
        self.unit_combo.setCurrentIndex(0)
        
        # 重置管道参数
        self.dn_input1.setCurrentIndex(8)  # DN100
        self.dn_input2.setCurrentIndex(8)  # DN100
        self.flange_combo1.setCurrentIndex(0)  # PN10
        self.flange_combo2.setCurrentIndex(0)  # PN10
        self.insulation_input1.setText("0")
        self.insulation_input2.setText("0")
        self.insulation_check1.setChecked(False)
        self.insulation_check2.setChecked(False)
        
        # 重置布置参数
        self.layout_combo.setCurrentIndex(0)
        self.rack_type_combo.setCurrentIndex(0)
        self.thermal_check.setChecked(True)
        self.thermal_input.setText("10")
        
        # 重置特殊要求
        self.flange_face_check.setChecked(False)
        self.valve_check1.setChecked(False)
        self.valve_check2.setChecked(False)
        self.instrument_check.setChecked(False)
        
        # 重置结果显示
        self.result_main_label.setText("点击计算按钮开始计算")
        self.result_detail_label.setText("")
        
        # 重置结果数据
        self.results = {
            'spacing_basic': 0,
            'spacing_flange': 0,
            'spacing_final': 0,
            'flange_od1': 0,
            'flange_od2': 0,
            'pipe_od1': 0,
            'pipe_od2': 0
        }
    
    def export_results(self):
        """导出计算结果"""
        if self.results['spacing_final'] == 0:
            QMessageBox.warning(self, "提示", "请先进行计算后再导出结果")
            return
        
        try:
            # 这里可以添加导出到文件的功能
            # 目前先显示在消息框中
            report = (
                f"=== 管道间距计算报告 ===\n\n"
                f"计算时间: {self.get_current_time()}\n"
                f"参考标准: HG/T20592~20623-2009, GB50316, SH3012\n\n"
                f"--- 输入参数 ---\n"
                f"管道1: DN={self.dn_input1.currentText()}, "
                f"法兰等级={self.flange_combo1.currentText()}\n"
                f"管道2: DN={self.dn_input2.currentText()}, "
                f"法兰等级={self.flange_combo2.currentText()}\n"
                f"保温厚度: {self.insulation_input1.text()}mm / {self.insulation_input2.text()}mm\n"
                f"布置方式: {self.layout_combo.currentText()}\n"
                f"支承类型: {self.rack_type_combo.currentText()}\n\n"
                f"--- 计算结果 ---\n"
                f"法兰外径: {self.results['flange_od1']:.1f}mm / {self.results['flange_od2']:.1f}mm\n"
                f"管道外径: {self.results['pipe_od1']:.1f}mm / {self.results['pipe_od2']:.1f}mm\n"
                f"基础间距（管廊）: {self.results['spacing_basic']:.1f}mm\n"
                f"法兰间距（外缘）: {self.results['spacing_flange']:.1f}mm\n"
                f"最终最小中心距: {self.results['spacing_final']:.1f}mm\n\n"
                f"--- 设计建议 ---\n"
                f"推荐采用中心距: {math.ceil(self.results['spacing_final']/10)*10}mm\n"
                f"（向上取整到10mm的倍数）"
            )
            
            QMessageBox.information(self, "计算结果报告", report)
            
        except Exception as e:
            QMessageBox.warning(self, "导出错误", f"导出过程中发生错误:\n{str(e)}")
    
    def get_current_time(self):
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = 管道间距()
    calculator.setWindowTitle("管道间距计算器 - 专业版")
    calculator.resize(900, 700)
    calculator.show()
    
    sys.exit(app.exec())