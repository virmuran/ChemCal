"""
管道间距计算器 - 依据化工部标准HG/T20592~20623-2009
参照GB50316和SH3012标准
管廊上管道净距：50mm，法兰外缘与相邻管道净距：25mm
"""

from PySide6.QtWidgets import (
    QSizePolicy, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QGroupBox, QFormLayout, QPushButton, 
    QGridLayout, QMessageBox, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from datetime import datetime


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from utils.docx_utils import ReportExporter

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
        """设置UI界面 - 统一标准左右分栏布局"""
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
        
        # 输入参数区（管道参数/布置参数/特殊要求 3 组）
        input_widget = self.create_input_section()
        left_layout.addWidget(input_widget)
        
        # 标准间距要求组
        table_group = CalculatorBase.make_group_box("标准间距要求")
        table_layout = QVBoxLayout(table_group)
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
        left_layout.addWidget(table_group)
        
        # 计算原理说明组
        principle_group = CalculatorBase.make_group_box("计算原理")
        principle_layout = QVBoxLayout(principle_group)
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
        left_layout.addWidget(principle_group)
        
        # 在底部添加拉伸因子
        left_layout.addStretch()
        
        # 右侧：结果显示区域 (占1/3宽度)
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        
        # 结果显示组
        result_group = CalculatorBase.make_group_box("计算结果")
        result_layout = QVBoxLayout(result_group)
        
        # 主要结果
        self.result_main_label = QLabel("点击计算按钮开始计算")
        self.result_main_label.setAlignment(Qt.AlignCenter)
        self.result_main_label.setStyleSheet("""
            /* color via theme */
            /* bg via theme */
            padding: 15px;
            border-radius: 8px;
            font-size: 16px;
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
        calc_btn.clicked.connect(self.calculate_spacing)
        right_layout.addWidget(calc_btn)
        
        # 将左右两部分添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)  # 左侧占2/3
        main_layout.addWidget(right_widget, 1)  # 右侧占1/3
        
    def create_input_section(self):
        """创建输入参数区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # 创建管道参数组（双列）
        pipes_group = CalculatorBase.make_group_box("管道参数")
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
        layout_group = CalculatorBase.make_group_box("布置参数")
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
        special_group = CalculatorBase.make_group_box("特殊要求")
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
    
    def clear_inputs(self):
        """清空并恢复默认参数"""
        self.reset_inputs()

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
            # 检查是否有计算结果
            if not self.results.get('spacing_final', 0):
                QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
                return None

            project_info = self.get_project_info()
            r = self.results
            notes = r.get('notes') or []
            notes_block = ""
            if notes:
                notes_block = ("══════════\n数据提示\n══════════\n\n"
                               + "\n".join(f"    • {n}" for n in notes) + "\n\n")

            report = f"""工程计算书 - 管道间距计算
计算工具: ChemCal 工程计算模块
========================================

══════════
 工程信息
══════════

    公司名称: {project_info.get('company_name', '')}
    工程编号: {project_info.get('project_number', '')}
    工程名称: {project_info.get('project_name', '')}
    子项名称: {project_info.get('subproject_name', '')}
    计算日期: {datetime.now().strftime('%Y-%m-%d')}

══════════
输入参数
══════════

    管道1: DN={self.dn_input1.currentText()}, 法兰等级={self.flange_combo1.currentText()}
    管道2: DN={self.dn_input2.currentText()}, 法兰等级={self.flange_combo2.currentText()}
    保温厚度: {self.insulation_input1.text()}mm / {self.insulation_input2.text()}mm
    布置方式: {self.layout_combo.currentText()}
    支承类型: {self.rack_type_combo.currentText()}
    热位移: {self.thermal_input.text()}mm

══════════
计算结果
══════════

    法兰外径: {r['flange_od1']:.1f}mm / {r['flange_od2']:.1f}mm
    管道外径: {r['pipe_od1']:.1f}mm / {r['pipe_od2']:.1f}mm
    基础间距（管廊净距）: {r['spacing_basic']:.1f}mm
    法兰间距（法兰外缘）: {r['spacing_flange']:.1f}mm
    最终最小中心距: {r['spacing_final']:.1f}mm

{notes_block}══════════
备注说明
══════════

    1. 法兰外径依据 HG/T 20592-2009 钢制管法兰 PN 系列（整体钢制管法兰表）
    2. 本计算书参照 GB 50316 和 SH 3012，管廊净距 50mm、法兰外缘净距 25mm
    3. 计算结果仅供参考，实际应用需考虑安全系数
    4. 重要工程参数应经专业工程师审核确认
    5. 计算条件变更时应重新进行计算

---
生成于 ChemCal 工程计算模块
"""
            return report
        except Exception as e:
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "管道间距")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "管道间距")
    def load_flange_data(self):
        """加载法兰外径数据（HG/T 20592-2009 钢制管法兰 PN 系列，单位 mm）

        表内填的是【法兰外径 D】，不是螺栓孔中心圆直径 K！
        （K 比 D 小 30~70mm，误用 K 会使法兰间距偏小 → 相邻法兰实际干涉）
        数据来源：HG/T 20592-2009 表 8.2.4 系列（整体钢制管法兰）。
        注：PN63 / PN100 该标准仅给到 DN400，更大口径未收录。
        """
        flange_data = {
            10:  {'PN10': 90,  'PN16': 90,  'PN25': 90,  'PN40': 90,  'PN63': 100, 'PN100': 100},
            15:  {'PN10': 95,  'PN16': 95,  'PN25': 95,  'PN40': 95,  'PN63': 105, 'PN100': 105},
            20:  {'PN10': 105, 'PN16': 105, 'PN25': 105, 'PN40': 105, 'PN63': 130, 'PN100': 130},
            25:  {'PN10': 115, 'PN16': 115, 'PN25': 115, 'PN40': 115, 'PN63': 140, 'PN100': 140},
            32:  {'PN10': 140, 'PN16': 140, 'PN25': 140, 'PN40': 140, 'PN63': 155, 'PN100': 155},
            40:  {'PN10': 150, 'PN16': 150, 'PN25': 150, 'PN40': 150, 'PN63': 170, 'PN100': 170},
            50:  {'PN10': 165, 'PN16': 165, 'PN25': 165, 'PN40': 165, 'PN63': 180, 'PN100': 195},
            65:  {'PN10': 185, 'PN16': 185, 'PN25': 185, 'PN40': 185, 'PN63': 205, 'PN100': 220},
            80:  {'PN10': 200, 'PN16': 200, 'PN25': 200, 'PN40': 200, 'PN63': 215, 'PN100': 230},
            100: {'PN10': 220, 'PN16': 220, 'PN25': 235, 'PN40': 235, 'PN63': 250, 'PN100': 265},
            125: {'PN10': 250, 'PN16': 250, 'PN25': 270, 'PN40': 270, 'PN63': 295, 'PN100': 315},
            150: {'PN10': 285, 'PN16': 285, 'PN25': 300, 'PN40': 300, 'PN63': 345, 'PN100': 355},
            200: {'PN10': 340, 'PN16': 340, 'PN25': 360, 'PN40': 375, 'PN63': 415, 'PN100': 430},
            250: {'PN10': 395, 'PN16': 405, 'PN25': 425, 'PN40': 450, 'PN63': 470, 'PN100': 505},
            300: {'PN10': 445, 'PN16': 460, 'PN25': 485, 'PN40': 515, 'PN63': 530, 'PN100': 585},
            350: {'PN10': 505, 'PN16': 520, 'PN25': 555, 'PN40': 580, 'PN63': 600, 'PN100': 655},
            400: {'PN10': 565, 'PN16': 580, 'PN25': 620, 'PN40': 660, 'PN63': 670, 'PN100': 715},
            450: {'PN10': 615, 'PN16': 640, 'PN25': 670, 'PN40': 685},
            500: {'PN10': 670, 'PN16': 715, 'PN25': 730, 'PN40': 755},
        }
        return flange_data

    # 管子外径（GB/T 17395 通用系列 / ASME B36.10M，mm）
    PIPE_OD_TABLE = {
        10: 17.2, 15: 21.3, 20: 26.9, 25: 33.7, 32: 42.4, 40: 48.3, 50: 60.3,
        65: 76.1, 80: 88.9, 100: 114.3, 125: 139.7, 150: 168.3, 200: 219.1,
        250: 273.0, 300: 323.9, 350: 355.6, 400: 406.4, 450: 457.0, 500: 508.0,
    }

    
    def load_initial_data(self):
        """初始化加载数据（先清空，避免单位制来回切换时条目重复累加）"""
        # 初始化公称直径列表（公制）
        dn_list = ["15", "20", "25", "32", "40", "50", "65", "80", "100", 
                  "125", "150", "200", "250", "300", "350", "400", "450", "500"]
        
        self.dn_input1.clear()
        self.dn_input2.clear()
        self.dn_input1.addItems(dn_list)
        self.dn_input2.addItems(dn_list)
        self.dn_input1.setCurrentIndex(8)  # 默认DN100
        self.dn_input2.setCurrentIndex(8)  # 默认DN100
        
        # 初始化法兰等级
        flange_grades = ["PN10", "PN16", "PN25", "PN40", "PN63", "PN100"]
        self.flange_combo1.clear()
        self.flange_combo2.clear()
        self.flange_combo1.addItems(flange_grades)
        self.flange_combo2.addItems(flange_grades)
        self.flange_combo1.setCurrentIndex(0)  # 默认PN10
        self.flange_combo2.setCurrentIndex(0)  # 默认PN10
        
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
    
    def _dn_to_int(self, dn):
        """把下拉/手输规格归一化为 DN 数字（按当前单位制判定，避免 "1"/"20" 歧义）"""
        s = str(dn).strip()
        if self.unit_combo.currentIndex() == 1:      # 英制 NPS
            return self.nps_to_dn(s)
        try:
            return int(float(s))
        except ValueError:
            return self.nps_to_dn(s)

    def lookup_flange_od(self, dn, flange_grade):
        """查法兰外径，返回 (外径mm, 备注)。未收录时按已知最大值保守取值并提示。"""
        table = self.flange_data.get(dn)
        if table:
            if flange_grade in table:
                return table[flange_grade], ""
            known = [v for k, v in table.items() if k in ("PN10", "PN16", "PN25", "PN40")]
            if known:
                v = max(known)
                return v, (f"DN{dn} 的 {flange_grade} 法兰外径 HG/T 20592-2009 未收录，"
                           f"暂按同口径最大已知外径 {v}mm 保守取值，请查标准手册复核")
        est = round(dn * 2.2, 1)
        return est, f"DN{dn} 非常用口径，法兰外径按 2.2×DN = {est}mm 保守估算，请查标准手册复核"

    def get_flange_od(self, dn, flange_grade):
        """获取法兰外径（mm）"""
        od, _ = self.lookup_flange_od(self._dn_to_int(dn), flange_grade)
        return od

    def get_pipe_od(self, dn):
        """获取管道外径（mm，GB/T 17395 通用系列 / ASME B36.10M）"""
        n = self._dn_to_int(dn)
        if n in self.PIPE_OD_TABLE:
            return self.PIPE_OD_TABLE[n]
        return round(n * 1.15, 1)  # 非常用口径：按 1.15×DN 保守估算
    
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
            
            # 获取法兰外径（未收录的(DN,PN)组合会返回保守估算值并给出提示）
            flange_od1, note1 = self.lookup_flange_od(self._dn_to_int(dn1), flange_grade1)
            flange_od2, note2 = self.lookup_flange_od(self._dn_to_int(dn2), flange_grade2)
            notes = [n for n in (note1, note2) if n]

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
                'pipe_od2': pipe_od2,
                'notes': notes
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

        # 数据来源提示（法兰外径未收录 / 非标口径保守估算）
        notes = self.results.get('notes') or []
        if notes:
            detail_text += "<br><br><b>数据提示:</b><br>• " + "<br>• ".join(notes)

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
        """导出计算结果 - 已由报告导出功能替代"""
        self.download_docx_report()

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