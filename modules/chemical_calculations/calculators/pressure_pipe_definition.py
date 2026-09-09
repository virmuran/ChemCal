# [file name]: calculators/pressure_pipe_definition.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                              QLabel, QLineEdit, QComboBox, QPushButton, 
                              QTextEdit, QTableWidget, QTableWidgetItem,
                              QHeaderView, QMessageBox, QTabWidget, QSizePolicy,
                              QScrollArea, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math
from datetime import datetime


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from utils.docx_utils import ReportExporter
class 压力管道定义(CalculatorBase):
    """压力管道定义计算器"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self.setup_ui()

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
        """设置UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 添加计算标签页
        self.calculation_tab = self.create_calculation_tab()
        self.tab_widget.addTab(self.calculation_tab, "管道定义计算")
        
        # 添加标准说明标签页
        self.standard_tab = self.create_standard_tab()
        self.tab_widget.addTab(self.standard_tab, "标准说明")
        
        main_layout.addWidget(self.tab_widget)
    
    def create_calculation_tab(self):
        """创建计算标签页"""
        tab = QWidget()
        main_layout = QHBoxLayout(tab)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧：输入参数区域（QScrollArea）
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # 输入参数组 - 标准三列 GridLayout
        input_group = CalculatorBase.make_group_box("输入参数")
        input_layout = QGridLayout(input_group)
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)
        
        row = 0
        
        # 设计压力
        pressure_label = QLabel("设计压力 (MPa):")
        pressure_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pressure_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(pressure_label, row, 0)
        
        self.pressure_input = QLineEdit()
        self.pressure_input.setPlaceholderText("请输入设计压力")
        self.pressure_input.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.pressure_input, row, 1)
        
        pressure_hint = QLabel("表压")
        pressure_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(pressure_hint, row, 2)
        
        row += 1
        
        # 工作压力
        wp_label = QLabel("工作压力 (MPa):")
        wp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        wp_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(wp_label, row, 0)
        
        self.working_pressure_input = QLineEdit()
        self.working_pressure_input.setPlaceholderText("请输入工作压力")
        self.working_pressure_input.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.working_pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.working_pressure_input, row, 1)
        
        wp_hint = QLabel("表压")
        wp_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(wp_hint, row, 2)
        
        row += 1
        
        # 设计温度
        dt_label = QLabel("设计温度 (°C):")
        dt_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        dt_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(dt_label, row, 0)
        
        self.temp_input = QLineEdit()
        self.temp_input.setPlaceholderText("请输入设计温度")
        self.temp_input.setValidator(QDoubleValidator(-200.0, 1000.0, 1))
        self.temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.temp_input, row, 1)
        
        dt_hint = QLabel("用于管道类别判定")
        dt_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(dt_hint, row, 2)
        
        row += 1
        
        # 工作温度
        wt_label = QLabel("工作温度 (°C):")
        wt_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        wt_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(wt_label, row, 0)
        
        self.working_temp_input = QLineEdit()
        self.working_temp_input.setPlaceholderText("请输入工作温度")
        self.working_temp_input.setValidator(QDoubleValidator(-200.0, 1000.0, 1))
        self.working_temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.working_temp_input, row, 1)
        
        wt_hint = QLabel("用于压力管道判定")
        wt_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(wt_hint, row, 2)
        
        row += 1
        
        # 介质类型
        media_label = QLabel("介质类型:")
        media_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        media_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(media_label, row, 0)
        
        self.media_combo = QComboBox()
        self.media_combo.setStyleSheet(COMBOBOX_STYLE)
        self.media_combo.addItems(["气体", "液化气体", "蒸汽", "可燃液体", "有毒介质", "一般液体"])
        self.media_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.media_combo, row, 1)
        
        media_hint = QLabel("选择介质分类")
        media_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(media_hint, row, 2)
        
        row += 1
        
        # 公称直径
        dia_label = QLabel("公称直径 (mm):")
        dia_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        dia_label.setStyleSheet(INPUT_LABEL_STYLE)
        input_layout.addWidget(dia_label, row, 0)
        
        self.diameter_input = QLineEdit()
        self.diameter_input.setPlaceholderText("请输入公称直径")
        self.diameter_input.setValidator(QDoubleValidator(0.0, 5000.0, 1))
        self.diameter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.diameter_input, row, 1)
        
        dia_hint = QLabel(">25mm 为判定条件之一")
        dia_hint.setStyleSheet("font-style: italic;")
        input_layout.addWidget(dia_hint, row, 2)
        
        left_layout.addWidget(input_group)
        
        # 压力管道分类参考
        classification_group = CalculatorBase.make_group_box("压力管道分类参考")
        classification_layout = QVBoxLayout(classification_group)
        
        self.classification_table = QTableWidget()
        self.classification_table.setColumnCount(4)
        self.classification_table.setHorizontalHeaderLabels(["类别", "代号", "适用范围", "主要特征"])
        self.setup_classification_table()
        classification_layout.addWidget(self.classification_table)
        
        left_layout.addWidget(classification_group)
        left_layout.addStretch()
        
        # 右侧：标准右栏
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
        self.calculate_btn = self.make_calc_button("计 算")
        self.calculate_btn.clicked.connect(self.calculate_pipe_definition)
        right_layout.addWidget(self.calculate_btn)
        
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)
        
        return tab
    
    def setup_classification_table(self):
        """设置分类表数据"""
        classifications = [
            ["GA类", "GA1", "长输管道", "输送有毒、可燃、易爆气体，设计压力>1.6MPa"],
            ["GA类", "GA2", "长输管道", "GA1以外的长输管道"],
            ["GB类", "GB1", "公用管道", "城镇燃气管道"],
            ["GB类", "GB2", "公用管道", "城镇热力管道"],
            ["GC类", "GC1", "工业管道", "输送极度危害、高度危害介质，或设计压力≥4.0MPa"],
            ["GC类", "GC2", "工业管道", "除GC3外的其他工业管道"],
            ["GC类", "GC3", "工业管道", "输送无毒、非可燃介质，设计压力≤1.0MPa"]
        ]
        
        self.classification_table.setRowCount(len(classifications))
        for i, row_data in enumerate(classifications):
            for j, data in enumerate(row_data):
                item = QTableWidgetItem(data)
                item.setTextAlignment(Qt.AlignCenter)
                self.classification_table.setItem(i, j, item)
        
        # 调整表格列宽
        header = self.classification_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
    
    def create_standard_tab(self):
        """创建标准说明标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 标准说明文本
        standard_text = QTextEdit()
        standard_text.setReadOnly(True)
        standard_text.setHtml(self.get_standard_html())
        layout.addWidget(standard_text)
        
        return tab
    
    def get_standard_html(self):
        """获取标准说明HTML内容"""
        return """
        <h2>压力管道定义与分类标准</h2>
        
        <h3>压力管道定义</h3>
        <p>根据《压力管道安全技术监察规程》，压力管道是指利用一定的压力，用于输送气体或者液体的管状设备，其范围规定为最高工作压力大于或者等于0.1MPa（表压）的气体、液化气体、蒸汽介质或者可燃、易爆、有毒、有腐蚀性、最高工作温度高于或者等于标准沸点的液体介质，且公称直径大于25mm的管道。</p>
        
        <h3>压力管道分类</h3>
        
        <h4>GA类 - 长输管道</h4>
        <ul>
            <li><b>GA1级：</b>
                <ul>
                    <li>输送有毒、可燃、易爆气体介质，设计压力大于1.6MPa的管道</li>
                    <li>输送有毒、可燃、易爆液体介质，输送距离≥200km且公称直径≥300mm的管道</li>
                    <li>输送浆体介质，输送距离≥50km且公称直径≥150mm的管道</li>
                </ul>
            </li>
            <li><b>GA2级：</b>GA1级以外的长输管道</li>
        </ul>
        
        <h4>GB类 - 公用管道</h4>
        <ul>
            <li><b>GB1级：</b>城镇燃气管道</li>
            <li><b>GB2级：</b>城镇热力管道</li>
        </ul>
        
        <h4>GC类 - 工业管道</h4>
        <ul>
            <li><b>GC1级：</b>
                <ul>
                    <li>输送毒性程度为极度危害介质、高度危害气体介质和工作温度高于标准沸点的高度危害液体介质的管道</li>
                    <li>输送火灾危险性为甲、乙类可燃气体或者甲类液体（包括液化烃）的管道，并且设计压力≥4.0MPa的管道</li>
                    <li>输送流体介质并且设计压力≥10.0MPa，或者设计压力≥4.0MPa且设计温度≥400℃的管道</li>
                </ul>
            </li>
            <li><b>GC2级：</b>除GC3级以外的其他工业管道</li>
            <li><b>GC3级：</b>输送无毒、非可燃流体介质，设计压力≤1.0MPa且设计温度>-20℃但不大于185℃的管道</li>
        </ul>
        
        <h3>主要参考标准</h3>
        <ul>
            <li>TSG D0001-2009《压力管道安全技术监察规程—工业管道》</li>
            <li>GB/T 20801-2020《压力管道规范 工业管道》</li>
            <li>GB 50160-2018《石油化工企业设计防火标准》</li>
            <li>GB 50028-2006《城镇燃气设计规范》</li>
        </ul>
        
        <h3>注意事项</h3>
        <p>本计算工具仅供参考，实际工程应用请以相关标准和规范为准。压力管道的定义和分类可能因具体项目要求和地方规定而有所不同。</p>
        """
    
    def calculate_pipe_definition(self):
        """计算压力管道定义"""
        try:
            # 获取输入值
            design_pressure = float(self.pressure_input.text() or 0)
            working_pressure = float(self.working_pressure_input.text() or 0)
            design_temp = float(self.temp_input.text() or 0)
            working_temp = float(self.working_temp_input.text() or 0)
            diameter = float(self.diameter_input.text() or 0)
            media_type = self.media_combo.currentText()
            
            # 验证输入
            if design_pressure <= 0 or diameter <= 0:
                QMessageBox.warning(self, "输入错误", "请填写设计压力和公称直径！")
                return
            
            # 判断是否为压力管道
            is_pressure_pipe = self.is_pressure_pipe(design_pressure, diameter, media_type, working_temp)
            
            # 确定管道类别
            pipe_class = self.determine_pipe_class(design_pressure, design_temp, media_type, diameter)
            
            # 显示结果
            self.display_results(is_pressure_pipe, pipe_class, design_pressure, diameter, media_type)
            
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的数值！")
    
    def is_pressure_pipe(self, pressure, diameter, media_type, temp):
        """判断是否为压力管道"""
        # 基本条件：压力≥0.1MPa且直径>25mm
        if pressure < 0.1 or diameter <= 25:
            return False
        
        # 介质条件
        gaseous_media = ["气体", "液化气体", "蒸汽"]
        hazardous_liquid = ["可燃液体", "有毒介质"]
        
        if media_type in gaseous_media:
            return True
        elif media_type in hazardous_liquid:
            return True
        elif media_type == "一般液体" and temp >= 100:  # 假设标准沸点为100°C
            return True
        
        return False
    
    def determine_pipe_class(self, pressure, temp, media_type, diameter):
        """确定管道类别（简化算法）"""
        hazardous_media = ["有毒介质", "可燃液体"]
        
        # GC1级条件
        if (media_type == "有毒介质" and pressure >= 0.1) or \
           (media_type == "可燃液体" and pressure >= 4.0) or \
           (pressure >= 10.0) or \
           (pressure >= 4.0 and temp >= 400):
            return "GC1"
        
        # GC3级条件
        if media_type == "一般液体" and pressure <= 1.0 and -20 < temp <= 185:
            return "GC3"
        
        # 默认GC2级
        return "GC2"
    
    def display_results(self, is_pressure_pipe, pipe_class, pressure, diameter, media_type):
        """显示计算结果"""
        result_text = f"""
        <h3>计算结果</h3>
        
        <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr style="background-color: #f8f9fa;">
            <td style="padding: 8px; font-weight: bold;">项目</td>
            <td style="padding: 8px;">结果</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">是否为压力管道</td>
            <td style="padding: 8px; {'color: green;' if is_pressure_pipe else 'color: red;'}">
                {'是压力管道' if is_pressure_pipe else '不是压力管道'}
            </td>
        </tr>
        """
        
        if is_pressure_pipe:
            result_text += f"""
        <tr>
            <td style="padding: 8px; font-weight: bold;">管道类别</td>
            <td style="padding: 8px; color: #e74c3c; font-weight: bold;">{pipe_class}级</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">设计压力</td>
            <td style="padding: 8px;">{pressure} MPa</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">公称直径</td>
            <td style="padding: 8px;">{diameter} mm</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">介质类型</td>
            <td style="padding: 8px;">{media_type}</td>
        </tr>
        """
        
        result_text += "</table>"
        
        if is_pressure_pipe:
            result_text += f"""
            <h4> {pipe_class}级管道说明</h4>
            <p>{self.get_class_description(pipe_class)}</p>
            
            <h4>注意事项</h4>
            <ul>
                <li>请按照相关规范进行设计、制造和检验</li>
                <li>需要相应的资质和许可</li>
                <li>定期进行安全检查和维护</li>
            </ul>
            """
        
        self.result_text.setHtml(result_text)
    
    def get_class_description(self, pipe_class):
        """获取类别说明"""
        descriptions = {
            "GC1": "属于GC1级工业管道，输送介质具有高度危险性，需要严格的设计、制造和检验要求。",
            "GC2": "属于GC2级工业管道，为一般工业管道，需按照相关规范进行设计和检验。",
            "GC3": "属于GC3级工业管道，危险性较低，但仍需按照规范进行设计和施工。"
        }
        return descriptions.get(pipe_class, "未知类别")
    
    def clear_inputs(self):
        """清空输入"""
        self.pressure_input.clear()
        self.working_pressure_input.clear()
        self.temp_input.clear()
        self.working_temp_input.clear()
        self.diameter_input.clear()
        self.media_combo.setCurrentIndex(0)
        self.result_text.clear()

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
            
            # 检查条件
            if not result_text or ("计算结果" not in result_text and "压力管道" not in result_text):
                QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
                return ""
            
            # 获取工程信息
            project_info = self.get_project_info()
            
            # 添加报告头信息
            report = f"""工程计算书 - 压力管道定义
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

    计算书编号: {project_info.get('report_number', '')}
    版本: 1.0
    状态: 正式计算书

══════════
备注说明
══════════

    1. 本计算书基于《压力管道安全技术监察规程》及相关标准规范
    2. 计算结果仅供参考，实际应用请以相关标准和规范为准
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
        ReportExporter.export_docx(self, "压力管道定义")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "压力管道定义")

    def _get_history_data(self):
        """提供历史记录数据"""
        design_pressure = float(self.pressure_input.text() or 0)
        working_pressure = float(self.working_pressure_input.text() or 0)
        design_temp = float(self.temp_input.text() or 0)
        working_temp = float(self.working_temp_input.text() or 0)
        diameter = float(self.diameter_input.text() or 0)
        media_type = self.media_combo.currentText()

        inputs = {
            "设计压力_MPa": design_pressure,
            "工作压力_MPa": working_pressure,
            "设计温度_C": design_temp,
            "工作温度_C": working_temp,
            "公称直径_mm": diameter,
            "介质类型": media_type
        }

        outputs = {}
        result_text = self.result_text.toPlainText()
        if "管道类别" in result_text or "GC" in result_text:
            import re
            class_match = re.search(r'(GC[123])', result_text)
            if class_match:
                outputs["判定管道类别"] = class_match.group(1)

        return {"inputs": inputs, "outputs": outputs}

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = 压力管道定义()
    widget.resize(800, 600)
    widget.show()
    
    sys.exit(app.exec())