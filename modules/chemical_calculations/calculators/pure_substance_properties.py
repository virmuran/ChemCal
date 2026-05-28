from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, 
                              QLabel, QLineEdit, QComboBox, QPushButton, 
                              QTextEdit, QTableWidget, QTableWidgetItem,
                              QHeaderView, QMessageBox, QTabWidget,
                              QCheckBox, QRadioButton, QButtonGroup, QScrollArea,
                              QFileDialog, QSizePolicy, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math
from fpdf import FPDF
from modules.combo_box_utils import ComboBoxWheelBlocker

# QGroupBox统一样式
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

class PureSubstanceProperties(QWidget):
    """纯物质物性数据查询"""

    # 计算类型类属性
    calculation_type = "pure_substance_properties"

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self.substance_data = self.load_substance_data()
        self.setup_ui()

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
        """设置UI - 统一布局规范"""
        # 主布局为水平布局
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧输入区 - 使用滚动区域
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } "
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        # 不设置 setMaximumWidth，让左侧动态扩展
        
        left_widget = QWidget()
        left_widget.setStyleSheet("background: transparent;")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # 顶部说明文字
        desc_label = QLabel("查询纯物质的基本物性和热力学性质，支持温度和压力条件设置，提供物性数据计算和温度影响分析。")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc_label)
        
        # 查询条件组
        query_group = QGroupBox("查询条件")
        query_layout = QGridLayout(query_group)
        query_layout.setSpacing(12)  # 行间距12px
        query_layout.setHorizontalSpacing(10)  # 列间距10px
        
        # 第0列 stretch=4, 第1列 stretch=8, 第2列 stretch=5
        query_layout.setColumnStretch(0, 4)
        query_layout.setColumnStretch(1, 8)
        query_layout.setColumnStretch(2, 5)
        
        # 物质选择 - 第0行
        category_label = QLabel("物质类别:")
        category_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        category_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        query_layout.addWidget(category_label, 0, 0)
        
        self.category_combo = QComboBox()
        self.category_combo.setStyleSheet(COMBOBOX_STYLE)
        self.category_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.category_combo.addItems([
            "无机物", "有机物", "金属", "气体", "液体", "固体"
        ])
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        query_layout.addWidget(self.category_combo, 0, 1)
        
        category_hint = QLabel("选择物质类别")
        category_hint.setStyleSheet("font-style: italic;")
        query_layout.addWidget(category_hint, 0, 2)
        
        # 具体物质选择 - 第1行
        substance_label = QLabel("具体物质:")
        substance_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        substance_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        query_layout.addWidget(substance_label, 1, 0)
        
        self.substance_combo = QComboBox()
        self.substance_combo.setStyleSheet(COMBOBOX_STYLE)
        self.substance_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.substance_combo.currentTextChanged.connect(self.on_substance_changed)
        query_layout.addWidget(self.substance_combo, 1, 1)
        
        substance_hint = QLabel("选择具体物质")
        substance_hint.setStyleSheet("font-style: italic;")
        query_layout.addWidget(substance_hint, 1, 2)
        
        # CAS号显示 - 第2行
        cas_label = QLabel("CAS号:")
        cas_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        cas_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        query_layout.addWidget(cas_label, 2, 0)
        
        self.cas_label = QLabel("")
        self.cas_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_layout.addWidget(self.cas_label, 2, 1)
        
        cas_hint = QLabel("物质标识符")
        cas_hint.setStyleSheet("font-style: italic;")
        query_layout.addWidget(cas_hint, 2, 2)
        
        # 温度输入 - 第3行（普通输入框）
        temp_label = QLabel("温度 (°C):")
        temp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        temp_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        query_layout.addWidget(temp_label, 3, 0)

        self.temperature_input = QLineEdit()
        self.temperature_input.setText("25")
        self.temperature_input.setPlaceholderText("输入温度值")
        self.temperature_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_layout.addWidget(self.temperature_input, 3, 1)

        temp_hint = QLabel("查询温度条件")
        temp_hint.setStyleSheet("font-style: italic;")
        query_layout.addWidget(temp_hint, 3, 2)
        
        # 压力输入 - 第4行（普通输入框）
        pressure_label = QLabel("压力 (kPa):")
        pressure_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pressure_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        query_layout.addWidget(pressure_label, 4, 0)

        self.pressure_input = QLineEdit()
        self.pressure_input.setText("101.3")
        self.pressure_input.setPlaceholderText("输入压力值")
        self.pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_layout.addWidget(self.pressure_input, 4, 1)

        pressure_hint = QLabel("查询压力条件")
        pressure_hint.setStyleSheet("font-style: italic;")
        query_layout.addWidget(pressure_hint, 4, 2)
        
        # 状态显示 - 第5行
        state_label = QLabel("当前状态:")
        state_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        state_label.setStyleSheet("font-weight: bold; padding-right: 10px;")
        query_layout.addWidget(state_label, 5, 0)
        
        self.state_label = QLabel("液态")
        self.state_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_layout.addWidget(self.state_label, 5, 1)
        
        state_hint = QLabel("根据温度自动判断")
        state_hint.setStyleSheet("font-style: italic;")
        query_layout.addWidget(state_hint, 5, 2)
        
        left_layout.addWidget(query_group)
        
        # 计算按钮（绿色 #27ae60，字号12pt，最小高度50px）
        self.query_btn = QPushButton("查询")
        self.query_btn.clicked.connect(self.calculate)
        self.query_btn.setFont(QFont("Arial", 12))
        self.query_btn.setMinimumHeight(50)
        self.query_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.query_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                min-height: 50px; padding: 0px;
                font-weight: bold;
            }
            QPushButton:hover:!checked {
                background-color: #ae2774;
            } """)
        left_layout.addWidget(self.query_btn)
        
        # 温度影响计算按钮
        self.temp_calc_btn = QPushButton("温度影响计算")
        self.temp_calc_btn.clicked.connect(self.temperature_calculation)
        self.temp_calc_btn.setMinimumHeight(40)
        self.temp_calc_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.temp_calc_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #8e44ad; "
            "color: white; "
            "font-weight: bold; "
            "border: none; "
            "border-radius: 8px; "
            "padding: 8px; "
            "}"
            "QPushButton:hover:!checked { background-color: #7d3c98; }"
        )
        left_layout.addWidget(self.temp_calc_btn)
        
        # 基本物性 & 热力学性质 - 左右分布
        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(15)

        # 基本物性组（左）
        basic_prop_group = QGroupBox("基本物性")
        basic_prop_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        basic_prop_layout = QVBoxLayout(basic_prop_group)
        basic_prop_layout.setContentsMargins(6, 6, 6, 6)

        self.basic_prop_table = QTableWidget()
        self.basic_prop_table.setColumnCount(3)
        self.basic_prop_table.setHorizontalHeaderLabels(["物性", "数值", "单位"])
        self.basic_prop_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.basic_prop_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        basic_prop_layout.addWidget(self.basic_prop_table)

        tables_layout.addWidget(basic_prop_group)

        # 热力学性质组（右）
        thermo_prop_group = QGroupBox("热力学性质")
        thermo_prop_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        thermo_prop_layout = QVBoxLayout(thermo_prop_group)
        thermo_prop_layout.setContentsMargins(6, 6, 6, 6)

        self.thermo_prop_table = QTableWidget()
        self.thermo_prop_table.setColumnCount(3)
        self.thermo_prop_table.setHorizontalHeaderLabels(["物性", "数值", "单位"])
        self.thermo_prop_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.thermo_prop_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        thermo_prop_layout.addWidget(self.thermo_prop_table)

        tables_layout.addWidget(thermo_prop_group)

        left_layout.addLayout(tables_layout, 1)
        
        # 设置左侧滚动区域
        left_scroll.setWidget(left_widget)
        main_layout.addWidget(left_scroll, 2)
        
        # 右侧结果区
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        right_widget.setMinimumWidth(300)
        
        # 查询结果组（与左侧查询条件统一风格）
        result_group = QGroupBox("查询结果")
        result_layout = QVBoxLayout(result_group)
        
        # 结果文本区（按照规范：背景#f8f9fa，边框1px solid #ecf0f1，圆角6px，padding 8px，minHeight 500px，Expanding/Expanding）
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet(
            "QTextEdit { "
            "/* bg via theme */"
            "border: 1px solid #ecf0f1; "
            "border-radius: 6px; "
            "padding: 8px; "
            "font-size: 13px; "
            "}"
        )
        result_layout.addWidget(self.result_text)
        
        right_layout.addWidget(result_group)
        
        # 底部按钮行
        button_layout = QHBoxLayout()
        
        # 清空按钮
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_inputs)
        self.clear_btn.setMinimumHeight(50)
        self.clear_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.clear_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #95a5a6; "
            "color: white; "
            "font-weight: bold; "
            "border: none; "
            "border-radius: 6px; "
            "padding: 8px; "
            "}"
            "QPushButton:hover:!checked { background-color: #7f8c8d; }"
        )
        button_layout.addWidget(self.clear_btn)
        
        button_layout.addStretch()
        
        # 下载TXT按钮（绿色 #27ae60，最小高度50px）
        self.download_txt_btn = QPushButton("下载计算书(TXT)")
        self.download_txt_btn.clicked.connect(self.download_txt_report)
        self.download_txt_btn.setMinimumHeight(50)
        self.download_txt_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_txt_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #27ae60; "
            "color: white; "
            "font-weight: bold; "
            "border: none; "
            "border-radius: 6px; "
            "padding: 8px; "
            "}"
            "QPushButton:hover:!checked { background-color: #219653; }"
        )
        button_layout.addWidget(self.download_txt_btn)
        
        # 下载PDF按钮（红色 #e74c3c，最小高度50px）
        self.download_pdf_btn = QPushButton("下载计算书(PDF)")
        self.download_pdf_btn.clicked.connect(self.generate_pdf_report)
        self.download_pdf_btn.setMinimumHeight(50)
        self.download_pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_pdf_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #e74c3c; "
            "color: white; "
            "font-weight: bold; "
            "border: none; "
            "border-radius: 6px; "
            "padding: 8px; "
            "}"
            "QPushButton:hover:!checked { background-color: #c0392b; }"
        )
        button_layout.addWidget(self.download_pdf_btn)
        
        right_layout.addLayout(button_layout)
        
        main_layout.addWidget(right_widget, 1)
        
        # 初始化下拉框
        self.on_category_changed(self.category_combo.currentText())
    
    def calculate(self):
        """执行计算 - 查询物性数据"""
        try:
            # 获取查询条件
            substance = self.substance_combo.currentText()
            temperature = float(self.temperature_input.text())
            pressure = float(self.pressure_input.text())
            
            # 查询数据
            if substance in self.substance_data:
                data = self.substance_data[substance]
                self.update_state_label(substance, temperature)
                self.display_basic_properties(data["basic"])
                self.display_thermal_properties(data["thermal"], temperature, pressure)
                self.update_result_text(substance, data, temperature, pressure)
            else:
                QMessageBox.information(self, "查询结果", f"未找到物质 '{substance}' 的物性数据")
                
        except Exception as e:
            QMessageBox.warning(self, "查询错误", f"查询过程中发生错误: {str(e)}")
    
    def update_result_text(self, substance, data, temperature, pressure):
        """更新结果文本区"""
        basic = data.get("basic", {})
        thermal = data.get("thermal", {})
        
        result = f"=== {substance} 物性数据查询结果 ===\n\n"
        result += f"查询条件: 温度 = {temperature}°C, 压力 = {pressure} kPa\n\n"
        
        result += "【基本物性】\n"
        result += f"  分子式: {basic.get('分子式', 'N/A')}\n"
        result += f"  分子量: {basic.get('分子量', 0):.3f} g/mol\n"
        result += f"  CAS号: {basic.get('CAS号', 'N/A')}\n"
        result += f"  沸点: {basic.get('沸点', 0)} °C\n"
        result += f"  熔点: {basic.get('熔点', 0)} °C\n"
        result += f"  临界温度: {basic.get('临界温度', 'N/A')} K\n"
        result += f"  临界压力: {basic.get('临界压力', 'N/A')} kPa\n"
        result += f"  临界密度: {basic.get('临界密度', 'N/A')} g/cm³\n"
        if basic.get('偏心因子') is not None:
            result += f"  偏心因子: {basic.get('偏心因子', 0):.3f}\n"
        
        result += "\n【热力学性质】\n"
        result += f"  密度: {thermal.get('密度', 0)} kg/m³\n"
        result += f"  粘度: {thermal.get('粘度', 0)} mPa·s\n"
        result += f"  热导率: {thermal.get('热导率', 0)} W/m·K\n"
        result += f"  比热容: {thermal.get('比热容', 0)} kJ/(kg·K)\n"
        result += f"  蒸发热: {thermal.get('蒸发热', 0)} kJ/kg\n"
        result += f"  表面张力: {thermal.get('表面张力', 0)} mN/m\n"
        result += f"  基准温度: {thermal.get('基准温度', 25.0)} °C\n"
        
        result += f"\n【当前状态】\n"
        result += f"  {self.state_label.text()}\n"
        
        self.result_text.setPlainText(result)
    
    def _get_history_data(self):
        """提供历史记录数据"""
        substance = self.substance_combo.currentText()
        temperature = float(self.temperature_input.text())
        pressure = float(self.pressure_input.text())

        inputs = {
            "物质名称": substance,
            "温度_C": temperature,
            "压力": pressure
        }

        outputs = {}
        if substance in self.substance_data:
            data = self.substance_data[substance]
            basic = data.get("basic", {})
            thermal = data.get("thermal", {})
            boiling_point = basic.get("沸点", 0)
            state = "气态" if temperature > boiling_point else ("固态" if temperature < basic.get("熔点", 0) else "液态")

            outputs = {
                "分子式": basic.get("分子式", ""),
                "分子量": basic.get("分子量", 0),
                "沸点_C": basic.get("沸点", 0),
                "熔点_C": basic.get("熔点", 0),
                "临界温度_K": basic.get("临界温度", 0),
                "临界压力_kPa": basic.get("临界压力", 0),
                "物态": state,
                "密度_kg_L": thermal.get("密度", 0),
                "比热容_kJ_kgK": thermal.get("比热容", 0)
            }

        return {"inputs": inputs, "outputs": outputs}
    
    def get_project_info(self):
        """获取项目信息"""
        return {
            "name": self.calculation_type,
            "description": "纯物质物性数据查询与计算",
            "parameters": {
                "物质": self.substance_combo.currentText(),
                "温度": float(self.temperature_input.text()),
                "压力": float(self.pressure_input.text())
            }
        }
    
    def generate_report(self):
        """生成报告数据"""
        substance = self.substance_combo.currentText()
        temperature = float(self.temperature_input.text())
        pressure = float(self.pressure_input.text())
        
        report = {
            "title": f"{self.calculation_type}报告",
            "substance": substance,
            "temperature": temperature,
            "pressure": pressure,
            "history_data": self._get_history_data()
        }
        
        if substance in self.substance_data:
            report["basic_data"] = self.substance_data[substance]["basic"]
            report["thermal_data"] = self.substance_data[substance]["thermal"]
        
        return report
    
    def download_txt_report(self):
        """下载TXT格式报告"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存TXT报告", "", "Text Files (*.txt)"
        )
        
        if file_path:
            try:
                report = self.generate_report()
                result_text = self.result_text.toPlainText()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"{report['title']}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"物质: {report['substance']}\n")
                    f.write(f"温度: {report['temperature']} °C\n")
                    f.write(f"压力: {report['pressure']} kPa\n\n")
                    f.write(result_text)
                
                QMessageBox.information(self, "下载成功", f"TXT报告已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "下载失败", f"保存TXT报告时发生错误:\n{str(e)}")
    
    def generate_pdf_report(self):
        """生成PDF格式报告"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存PDF报告", "", "PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                report = self.generate_report()
                pdf = FPDF()
                pdf.add_page()
                
                # 使用微软雅黑字体
                pdf.add_font('MicrosoftYaHei', '', 'C:/Windows/Fonts/msyh.ttc', uni=True)
                pdf.set_font('MicrosoftYaHei', '', 12)
                
                # 标题
                pdf.cell(200, 10, text=report['title'], ln=True, align='C')
                pdf.ln(10)
                
                # 基本信息
                pdf.cell(200, 10, text=f"物质: {report['substance']}", ln=True)
                pdf.cell(200, 10, text=f"温度: {report['temperature']} °C", ln=True)
                pdf.cell(200, 10, text=f"压力: {report['pressure']} kPa", ln=True)
                pdf.ln(5)
                
                # 查询结果
                pdf.cell(200, 10, text="查询结果:", ln=True)
                result_text = self.result_text.toPlainText()
                pdf.multi_cell(0, 10, text=result_text)
                
                pdf.output(file_path)
                QMessageBox.information(self, "生成成功", f"PDF报告已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "生成失败", f"生成PDF报告时发生错误:\n{str(e)}")
    
    def on_category_changed(self, category):
        """类别改变事件"""
        substances = {
            "无机物": ["水", "氨", "二氧化碳", "硫酸", "氯化钠", "盐酸", "氢氧化钠"],
            "有机物": ["甲醇", "乙醇", "丙酮", "苯", "甲苯", "乙酸", "正己烷", "环己烷", "甲烷", "乙烷", "丙烷", "乙烯", "丙烯"],
            "金属": ["铁", "铜", "铝", "锌", "铅", "银", "金"],
            "气体": ["空气", "氧气", "氮气", "氢气", "甲烷", "乙烷", "丙烷", "乙烯", "丙烯", "二氧化碳"],
            "液体": ["水", "乙醇", "甲醇", "丙酮", "苯", "甲苯", "乙酸", "正己烷", "环己烷", "硫酸"],
            "固体": ["冰", "食盐", "石英", "石墨", "金刚石"]
        }
        
        self.substance_combo.clear()
        if category in substances:
            self.substance_combo.addItems(substances[category])
        
        # 默认选择第一个物质
        if self.substance_combo.count() > 0:
            self.substance_combo.setCurrentIndex(0)
            self.update_cas_number()
    
    def on_substance_changed(self, substance):
        """物质改变事件"""
        self.update_cas_number()
    
    def update_cas_number(self):
        """更新CAS号"""
        substance = self.substance_combo.currentText()
        cas_numbers = {
            "水": "7732-18-5",
            "氨": "7664-41-7",
            "硫酸": "7664-93-9",
            "盐酸": "7647-01-0",
            "氢氧化钠": "1310-73-2",
            "氯化钠": "7647-14-5",
            "二氧化碳": "124-38-9",
            "甲烷": "74-82-8",
            "乙烷": "74-84-0",
            "丙烷": "74-98-6",
            "乙烯": "74-85-1",
            "丙烯": "115-07-1",
            "苯": "71-43-2",
            "甲苯": "108-88-3",
            "甲醇": "67-56-1",
            "乙醇": "64-17-5",
            "铁": "7439-89-6",
            "铜": "7440-50-8",
            "铝": "7429-90-5",
            "空气": "132259-10-0",
            "氧气": "7782-44-7",
            "氮气": "7727-37-9",
            "氢气": "1333-74-0"
        }
        
        self.cas_label.setText(cas_numbers.get(substance, "未知"))
    
    def load_substance_data(self):
        """加载物质物性数据库（扩展版 22 种常见化工物质）
        
        数据来源:
        - 临界性质: NIST Chemistry WebBook / DIPPR Project 801
        - Antoine 系数: NIST (单位: log10(P/mmHg) = A - B/(T/°C + C))
        - DIPPR 密度: ρ = A / B^(1-(1-T/C)^D), T 单位 K, ρ 单位 kg/m³
        - Andrade 粘度: μ = A × 10^(B/(T+C)), μ 单位 mPa·s, T 单位 °C
        - 液相比热容: Cp = A + B·T + C·T² + D·T³, kJ/(kg·K), T 单位 K
        """
        substance_data = {
            # ── 无机物 ──
            "水": {
                "basic": {
                    "分子式": "H₂O", "分子量": 18.015, "CAS号": "7732-18-5",
                    "沸点": 100.0, "熔点": 0.0, "临界温度": 647.14,
                    "临界压力": 22064, "临界密度": 0.322,
                    "偏心因子": 0.344
                },
                "thermal": {
                    "密度": 997.0, "粘度": 0.890, "热导率": 0.606,
                    "比热容": 4.181, "蒸发热": 2257, "表面张力": 72.0,
                    "基准温度": 25.0
                },
                "formula_params": {
                    "antoine_A": 8.07131, "antoine_B": 1730.63, "antoine_C": 233.426,
                    "antoine_Tmin": 1, "antoine_Tmax": 100,
                    "dippr_A": 0.14395, "dippr_B": 0.01111, "dippr_C": 649.727, "dippr_D": 0.05107,
                    "andrade_A": 0.46612, "andrade_B": 1659.4, "andrade_C": -139.49,
                    "cp_A": -203.6060, "cp_B": 1523.29, "cp_C": -3196.13, "cp_D": 2474.55,
                    "cp_Tmin": 273.15, "cp_Tmax": 623.15,
                    "kt_A": -0.432, "kt_B": -5.725e-3, "kt_C": -8.078e-6
                }
            },
            "氨": {
                "basic": {
                    "分子式": "NH₃", "分子量": 17.031, "CAS号": "7664-41-7",
                    "沸点": -33.34, "熔点": -77.73, "临界温度": 405.40,
                    "临界压力": 11334, "临界密度": 0.225,
                    "偏心因子": 0.253
                },
                "thermal": {
                    "密度": 602.0, "粘度": 0.134, "热导率": 0.504,
                    "比热容": 4.70, "蒸发热": 1371, "表面张力": 23.4,
                    "基准温度": -33.3
                },
                "formula_params": {
                    "antoine_A": 7.55466, "antoine_B": 1002.71, "antoine_C": 247.885,
                    "antoine_Tmin": -74, "antoine_Tmax": 60,
                    "dippr_A": 0.2372, "dippr_B": 0.2656, "dippr_C": 406.0, "dippr_D": 0.2939,
                    "andrade_A": -0.4506, "andrade_B": 330.1, "andrade_C": -60.16,
                    "cp_A": 1.7449, "cp_B": 0.00730, "cp_C": -6.491e-5, "cp_D": 2.391e-7,
                    "cp_Tmin": 195, "cp_Tmax": 400
                }
            },
            "二氧化碳": {
                "basic": {
                    "分子式": "CO₂", "分子量": 44.010, "CAS号": "124-38-9",
                    "沸点": -78.46, "熔点": -56.56, "临界温度": 304.13,
                    "临界压力": 7377, "临界密度": 0.468,
                    "偏心因子": 0.225
                },
                "thermal": {
                    "密度": 776.0, "粘度": 0.070, "热导率": 0.086,
                    "比热容": 2.45, "蒸发热": 342, "表面张力": 4.7,
                    "基准温度": -20.0
                },
                "formula_params": {
                    "antoine_A": 6.81228, "antoine_B": 1301.679, "antoine_C": -3.494,
                    "antoine_Tmin": -100, "antoine_Tmax": -20
                }
            },
            "硫酸": {
                "basic": {
                    "分子式": "H₂SO₄", "分子量": 98.079, "CAS号": "7664-93-9",
                    "沸点": 337.0, "熔点": 10.4, "临界温度": 924.0,
                    "临界压力": 6400, "临界密度": 0.514,
                    "偏心因子": 0.468
                },
                "thermal": {
                    "密度": 1835.0, "粘度": 24.5, "热导率": 0.340,
                    "比热容": 1.42, "蒸发热": 511, "表面张力": 55.0,
                    "基准温度": 25.0
                },
                "formula_params": {
                    "antoine_A": 7.97870, "antoine_B": 1687.54, "antoine_C": 230.45,
                    "antoine_Tmin": 150, "antoine_Tmax": 330
                }
            },
            "氯化钠": {
                "basic": {
                    "分子式": "NaCl", "分子量": 58.44, "CAS号": "7647-14-5",
                    "沸点": 1465, "熔点": 801, "临界温度": None,
                    "临界压力": None, "临界密度": None,
                    "偏心因子": None
                },
                "thermal": {
                    "密度": 2165.0, "粘度": None, "热导率": 6.5,
                    "比热容": 0.864, "蒸发热": None, "表面张力": None,
                    "基准温度": 25.0
                },
                "formula_params": {}
            },
            # ── 有机物 ──
            "甲醇": {
                "basic": {
                    "分子式": "CH₃OH", "分子量": 32.042, "CAS号": "67-56-1",
                    "沸点": 64.7, "熔点": -97.6, "临界温度": 512.6,
                    "临界压力": 8094, "临界密度": 0.272,
                    "偏心因子": 0.565
                },
                "thermal": {
                    "密度": 787.0, "粘度": 0.544, "热导率": 0.202,
                    "比热容": 2.53, "蒸发热": 1100, "表面张力": 22.6,
                    "基准温度": 25.0
                },
                "formula_params": {
                    "antoine_A": 8.08097, "antoine_B": 1582.27, "antoine_C": 239.726,
                    "antoine_Tmin": -16, "antoine_Tmax": 91,
                    "dippr_A": 0.25657, "dippr_B": 0.26684, "dippr_C": 512.6, "dippr_D": 0.27564,
                    "andrade_A": -0.7299, "andrade_B": 700.6, "andrade_C": -67.82,
                    "cp_A": 1.0392, "cp_B": 0.00214, "cp_C": 2.103e-5, "cp_D": -5.505e-8,
                    "cp_Tmin": 175, "cp_Tmax": 493
                }
            },
            "乙醇": {
                "basic": {
                    "分子式": "C₂H₅OH", "分子量": 46.069, "CAS号": "64-17-5",
                    "沸点": 78.4, "熔点": -114.1, "临界温度": 513.9,
                    "临界压力": 6148, "临界密度": 0.276,
                    "偏心因子": 0.644
                },
                "thermal": {
                    "密度": 785.0, "粘度": 1.074, "热导率": 0.167,
                    "比热容": 2.44, "蒸发热": 841, "表面张力": 22.3,
                    "基准温度": 25.0
                },
                "formula_params": {
                    "antoine_A": 8.11220, "antoine_B": 1592.86, "antoine_C": 226.184,
                    "antoine_Tmin": -20, "antoine_Tmax": 93,
                    "dippr_A": 0.21626, "dippr_B": 0.26725, "dippr_C": 513.9, "dippr_D": 0.26880,
                    "andrade_A": -0.6554, "andrade_B": 1079.7, "andrade_C": -66.41,
                    "cp_A": 1.0792, "cp_B": 0.00340, "cp_C": 3.174e-6, "cp_D": -1.344e-8,
                    "cp_Tmin": 159, "cp_Tmax": 500
                }
            },
            "丙酮": {
                "basic": {
                    "分子式": "CH₃COCH₃", "分子量": 58.080, "CAS号": "67-64-1",
                    "沸点": 56.1, "熔点": -94.7, "临界温度": 508.1,
                    "临界压力": 4701, "临界密度": 0.278,
                    "偏心因子": 0.307
                },
                "thermal": {
                    "密度": 784.0, "粘度": 0.295, "热导率": 0.161,
                    "比热容": 2.17, "蒸发热": 518, "表面张力": 23.7,
                    "基准温度": 25.0
                },
                "formula_params": {
                    "antoine_A": 7.02447, "antoine_B": 1161.0, "antoine_C": 224.0,
                    "antoine_Tmin": -32, "antoine_Tmax": 77,
                    "dippr_A": 0.25443, "dippr_B": 0.24691, "dippr_C": 508.1, "dippr_D": 0.28574,
                    "andrade_A": -0.8397, "andrade_B": 553.0, "andrade_C": -62.85
                }
            },
            "苯": {
                "basic": {
                    "分子式": "C₆H₆", "分子量": 78.114, "CAS号": "71-43-2",
                    "沸点": 80.1, "熔点": 5.5, "临界温度": 562.2,
                    "临界压力": 4898, "临界密度": 0.304,
                    "偏心因子": 0.210
                },
                "thermal": {
                    "密度": 876.0, "粘度": 0.604, "热导率": 0.144,
                    "比热容": 1.73, "蒸发热": 394, "表面张力": 28.9,
                    "基准温度": 25.0
                },
                "formula_params": {
                    "antoine_A": 6.90565, "antoine_B": 1211.03, "antoine_C": 220.790,
                    "antoine_Tmin": -16, "antoine_Tmax": 104,
                    "dippr_A": 0.30792, "dippr_B": 0.26918, "dippr_C": 562.16, "dippr_D": 0.28276,
                    "andrade_A": -0.6285, "andrade_B": 718.4, "andrade_C": -67.90,
                    "cp_A": 0.7300, "cp_B": 0.00300, "cp_C": 2.959e-6, "cp_D": -1.621e-8,
                    "cp_Tmin": 280, "cp_Tmax": 540
                }
            },
            "甲苯": {
                "basic": {
                    "分子式": "C₇H₈", "分子量": 92.141, "CAS号": "108-88-3",
                    "沸点": 110.6, "熔点": -95.0, "临界温度": 591.8,
                    "临界压力": 4109, "临界密度": 0.292,
                    "偏心因子": 0.264
                },
                "thermal": {
                    "密度": 862.0, "粘度": 0.560, "热导率": 0.131,
                    "比热容": 1.70, "蒸发热": 363, "表面张力": 28.5,
                    "基准温度": 25.0
                },
                "formula_params": {
                    "antoine_A": 6.95464, "antoine_B": 1344.8, "antoine_C": 219.48,
                    "antoine_Tmin": 6, "antoine_Tmax": 137,
                    "dippr_A": 0.29376, "dippr_B": 0.27038, "dippr_C": 591.8, "dippr_D": 0.28555
                }
            },
            "乙酸": {
                "basic": {
                    "分子式": "CH₃COOH", "分子量": 60.052, "CAS号": "64-19-7",
                    "沸点": 118.0, "熔点": 16.6, "临界温度": 594.8,
                    "临界压力": 5786, "临界密度": 0.351,
                    "偏心因子": 0.445
                },
                "thermal": {
                    "密度": 1044.0, "粘度": 1.04, "热导率": 0.159,
                    "比热容": 2.05, "蒸发热": 394, "表面张力": 27.6,
                    "基准温度": 25.0
                },
                "formula_params": {
                    "antoine_A": 7.18807, "antoine_B": 1416.7, "antoine_C": 211.0,
                    "antoine_Tmin": 15, "antoine_Tmax": 157
                }
            },
            "正己烷": {
                "basic": {
                    "分子式": "C₆H₁₄", "分子量": 86.178, "CAS号": "110-54-3",
                    "沸点": 68.7, "熔点": -95.3, "临界温度": 507.5,
                    "临界压力": 3012, "临界密度": 0.233,
                    "偏心因子": 0.301
                },
                "thermal": {
                    "密度": 655.0, "粘度": 0.300, "热导率": 0.124,
                    "比热容": 2.24, "蒸发热": 365, "表面张力": 18.4,
                    "基准温度": 25.0
                },
                "formula_params": {
                    "antoine_A": 6.87776, "antoine_B": 1171.53, "antoine_C": 224.366,
                    "antoine_Tmin": -25, "antoine_Tmax": 91
                }
            },
            "环己烷": {
                "basic": {
                    "分子式": "C₆H₁₂", "分子量": 84.162, "CAS号": "110-82-7",
                    "沸点": 80.7, "熔点": 6.5, "临界温度": 553.5,
                    "临界压力": 4073, "临界密度": 0.273,
                    "偏心因子": 0.213
                },
                "thermal": {
                    "密度": 774.0, "粘度": 0.898, "热导率": 0.124,
                    "比热容": 1.86, "蒸发热": 399, "表面张力": 24.9,
                    "基准温度": 25.0
                },
                "formula_params": {
                    "antoine_A": 6.84941, "antoine_B": 1206.001, "antoine_C": 223.148,
                    "antoine_Tmin": 6, "antoine_Tmax": 105
                }
            },
            # ── 气体（常温） ──
            "甲烷": {
                "basic": {
                    "分子式": "CH₄", "分子量": 16.043, "CAS号": "74-82-8",
                    "沸点": -161.5, "熔点": -182.5, "临界温度": 190.6,
                    "临界压力": 4600, "临界密度": 0.163,
                    "偏心因子": 0.008
                },
                "thermal": {
                    "密度": 0.657, "粘度": 0.0109, "热导率": 0.0343,
                    "比热容": 2.20, "蒸发热": 511, "表面张力": 3.7,
                    "基准温度": -161.5
                },
                "formula_params": {
                    "antoine_A": 6.61184, "antoine_B": 389.93, "antoine_C": 266.00,
                    "antoine_Tmin": -180, "antoine_Tmax": -140
                }
            },
            "乙烷": {
                "basic": {
                    "分子式": "C₂H₆", "分子量": 30.070, "CAS号": "74-84-0",
                    "沸点": -88.6, "熔点": -182.8, "临界温度": 305.3,
                    "临界压力": 4880, "临界密度": 0.207,
                    "偏心因子": 0.099
                },
                "thermal": {
                    "密度": 1.263, "粘度": None, "热导率": None,
                    "比热容": 1.76, "蒸发热": 489, "表面张力": None,
                    "基准温度": -88.6
                },
                "formula_params": {
                    "antoine_A": 6.80266, "antoine_B": 666.83, "antoine_C": 256.47,
                    "antoine_Tmin": -130, "antoine_Tmax": -70
                }
            },
            "丙烷": {
                "basic": {
                    "分子式": "C₃H₈", "分子量": 44.096, "CAS号": "74-98-6",
                    "沸点": -42.1, "熔点": -187.7, "临界温度": 369.8,
                    "临界压力": 4248, "临界密度": 0.220,
                    "偏心因子": 0.152
                },
                "thermal": {
                    "密度": 493.0, "粘度": 0.105, "热导率": 0.0824,
                    "比热容": 2.44, "蒸发热": 426, "表面张力": 7.0,
                    "基准温度": -42.1
                },
                "formula_params": {
                    "antoine_A": 6.80398, "antoine_B": 804.00, "antoine_C": 247.04,
                    "antoine_Tmin": -100, "antoine_Tmax": -20
                }
            },
            "乙烯": {
                "basic": {
                    "分子式": "C₂H₄", "分子量": 28.054, "CAS号": "74-85-1",
                    "沸点": -103.7, "熔点": -169.2, "临界温度": 282.3,
                    "临界压力": 5042, "临界密度": 0.215,
                    "偏心因子": 0.087
                },
                "thermal": {
                    "密度": 1.261, "粘度": None, "热导率": None,
                    "比热容": 1.54, "蒸发热": 484, "表面张力": None,
                    "基准温度": -103.7
                },
                "formula_params": {
                    "antoine_A": 6.74756, "antoine_B": 585.00, "antoine_C": 255.00,
                    "antoine_Tmin": -130, "antoine_Tmax": -75
                }
            },
            "丙烯": {
                "basic": {
                    "分子式": "C₃H₆", "分子量": 42.081, "CAS号": "115-07-1",
                    "沸点": -47.6, "熔点": -185.2, "临界温度": 364.9,
                    "临界压力": 4600, "临界密度": 0.232,
                    "偏心因子": 0.142
                },
                "thermal": {
                    "密度": 514.0, "粘度": None, "热导率": None,
                    "比热容": 2.15, "蒸发热": 438, "表面张力": None,
                    "基准温度": -47.6
                },
                "formula_params": {
                    "antoine_A": 6.81960, "antoine_B": 785.00, "antoine_C": 247.00,
                    "antoine_Tmin": -90, "antoine_Tmax": -20
                }
            },
            # ── 气体（大气） ──
            "空气": {
                "basic": {
                    "分子式": "N₂/O₂混合", "分子量": 28.966, "CAS号": "132259-10-0",
                    "沸点": -194.3, "熔点": None, "临界温度": 132.5,
                    "临界压力": 3786, "临界密度": 0.313,
                    "偏心因子": 0.035
                },
                "thermal": {
                    "密度": 1.169, "粘度": 0.0182, "热导率": 0.0259,
                    "比热容": 1.005, "蒸发热": 199, "表面张力": None,
                    "基准温度": 25.0
                },
                "formula_params": {}
            },
            "氧气": {
                "basic": {
                    "分子式": "O₂", "分子量": 31.999, "CAS号": "7782-44-7",
                    "沸点": -183.0, "熔点": -218.8, "临界温度": 154.6,
                    "临界压力": 5043, "临界密度": 0.436,
                    "偏心因子": 0.022
                },
                "thermal": {
                    "密度": 1.308, "粘度": 0.0203, "热导率": 0.0260,
                    "比热容": 0.917, "蒸发热": 213, "表面张力": None,
                    "基准温度": -183.0
                },
                "formula_params": {
                    "antoine_A": 6.98773, "antoine_B": 588.72, "antoine_C": 267.31,
                    "antoine_Tmin": -200, "antoine_Tmax": -150
                }
            },
            "氮气": {
                "basic": {
                    "分子式": "N₂", "分子量": 28.014, "CAS号": "7727-37-9",
                    "沸点": -195.8, "熔点": -210.0, "临界温度": 126.2,
                    "临界压力": 3394, "临界密度": 0.313,
                    "偏心因子": 0.037
                },
                "thermal": {
                    "密度": 1.145, "粘度": 0.0176, "热导率": 0.0258,
                    "比热容": 1.040, "蒸发热": 199, "表面张力": None,
                    "基准温度": -195.8
                },
                "formula_params": {
                    "antoine_A": 6.49457, "antoine_B": 255.821, "antoine_C": 266.551,
                    "antoine_Tmin": -210, "antoine_Tmax": -180
                }
            },
            "氢气": {
                "basic": {
                    "分子式": "H₂", "分子量": 2.016, "CAS号": "1333-74-0",
                    "沸点": -252.9, "熔点": -259.2, "临界温度": 33.2,
                    "临界压力": 1315, "临界密度": 0.031,
                    "偏心因子": -0.216
                },
                "thermal": {
                    "密度": 0.082, "粘度": 0.0088, "热导率": 0.181,
                    "比热容": 14.32, "蒸发热": 446, "表面张力": None,
                    "基准温度": -252.9
                },
                "formula_params": {}
            }
        }
        
        return substance_data
    
    def query_properties(self):
        """查询物性数据（保留旧接口）"""
        self.calculate()
    
    def update_state_label(self, substance, temperature):
        """更新状态标签"""
        if substance in self.substance_data:
            data = self.substance_data[substance]
            boiling_point = data["basic"]["沸点"]
            melting_point = data["basic"]["熔点"]
            
            if temperature > boiling_point:
                state = "气态"
            elif temperature < melting_point:
                state = "固态"
            else:
                state = "液态"
            
            self.state_label.setText(state)
    
    def display_basic_properties(self, basic_data):
        """显示基本物性"""
        basic_props = [
            ["分子式", basic_data["分子式"], "-"],
            ["分子量", f"{basic_data['分子量']:.3f}", "g/mol"],
            ["CAS号", basic_data["CAS号"], "-"],
            ["沸点", f"{basic_data['沸点']}", "°C"],
            ["熔点", f"{basic_data['熔点']}", "°C"],
            ["临界温度", f"{basic_data['临界温度']}" if basic_data.get("临界温度") else "N/A", "K"],
            ["临界压力", f"{basic_data['临界压力']}" if basic_data.get("临界压力") else "N/A", "kPa"],
            ["临界密度", f"{basic_data['临界密度']}" if basic_data.get("临界密度") else "N/A", "g/cm³"],
        ]
        if basic_data.get("偏心因子") is not None:
            basic_props.append(["偏心因子", f"{basic_data['偏心因子']:.3f}", "-"])
        
        self.update_table(self.basic_prop_table, basic_props)
    
    def display_thermal_properties(self, thermal_data, temperature, pressure):
        """显示热力学性质（使用 DIPPR / Andrade 方程修正）"""
        substance_name = self.substance_combo.currentText()
        data = self.substance_data.get(substance_name, {})
        fp = data.get("formula_params", {})
        
        base_temp = thermal_data.get("基准温度", 25.0)
        
        # 密度：DIPPR 方程（如有系数）
        if "dippr_A" in fp:
            density = self._dippr_density(fp, temperature)
        else:
            density = self._simple_density_correction(thermal_data["密度"], temperature, base_temp)
        
        # 粘度：Andrade 方程（如有系数）
        if "andrade_A" in fp:
            viscosity = self._andrade_viscosity(fp, temperature)
        else:
            viscosity = self._simple_viscosity_correction(thermal_data["粘度"], temperature, base_temp)
        
        # 热导率：简化线性修正
        thermal_cond = self._simple_thermal_cond_correction(
            thermal_data["热导率"], temperature, base_temp, fp
        )
        
        # 比热容：DIPPR 多项式（如有系数）
        if "cp_A" in fp:
            heat_capacity = self._dippr_heat_capacity(fp, temperature)
        else:
            heat_capacity = self._simple_cp_correction(thermal_data["比热容"], temperature, base_temp)
        
        thermal_props = [
            ["密度", f"{density:.3f}", "kg/m³" if density > 1 else "g/cm³"],
            ["粘度", f"{viscosity:.4f}", "mPa·s"] if viscosity is not None else ["粘度", "N/A", "-"],
            ["热导率", f"{thermal_cond:.4f}", "W/m·K"] if thermal_cond is not None else ["热导率", "N/A", "-"],
            ["比热容", f"{heat_capacity:.3f}", "kJ/(kg·K)"],
            ["蒸发热(常沸点)", f"{thermal_data['蒸发热']}", "kJ/kg"] if thermal_data.get("蒸发热") else ["蒸发热", "N/A", "-"],
            ["表面张力", f"{thermal_data['表面张力']}", "mN/m"] if thermal_data.get("表面张力") else ["表面张力", "N/A", "-"],
        ]
        
        # 蒸气压计算（如有 Antoine 系数且温度在范围内）
        if "antoine_A" in fp:
            try:
                p_sat = self._antoine_vapor_pressure(fp, temperature)
                thermal_props.append(["蒸气压", f"{p_sat:.2f}", "kPa"])
            except Exception:
                pass
        
        self.update_table(self.thermo_prop_table, thermal_props)
    
    def _dippr_density(self, fp, T_C):
        """DIPPR 液体密度方程: ρ = A / B^(1-(1-T/C)^D)
        T 单位 K, ρ 单位 kg/m³"""
        try:
            A, B, C, D = fp["dippr_A"], fp["dippr_B"], fp["dippr_C"], fp["dippr_D"]
            T_K = T_C + 273.15
            T_r = T_K / C
            if T_r >= 1.0:
                return 0.0
            rho = A / (B ** (1.0 - (1.0 - T_r) ** D))
            return max(0.0, rho)
        except Exception:
            return 0.0
    
    def _andrade_viscosity(self, fp, T_C):
        """Andrade 液体粘度方程: μ = A × 10^(B/(T+C))
        μ 单位 mPa·s, T 单位 °C"""
        try:
            A, B, C = fp["andrade_A"], fp["andrade_B"], fp["andrade_C"]
            mu = A * (10.0 ** (B / (T_C + C)))
            return max(0.0, mu)
        except Exception:
            return None
    
    def _antoine_vapor_pressure(self, fp, T_C):
        """Antoine 蒸气压方程: log10(P/mmHg) = A - B/(T+C)
        返回 kPa"""
        try:
            A, B, C = fp["antoine_A"], fp["antoine_B"], fp["antoine_C"]
            Tmin = fp.get("antoine_Tmin", -999)
            Tmax = fp.get("antoine_Tmax", 999)
            if T_C < Tmin or T_C > Tmax:
                raise ValueError("超出Antoine方程适用温度范围")
            log_p = A - B / (T_C + C)
            p_mmhg = 10.0 ** log_p
            return p_mmhg * 0.133322  # mmHg → kPa
        except Exception:
            return None
    
    def _dippr_heat_capacity(self, fp, T_C):
        """DIPPR 液相比热容多项式: Cp = A + B·T + C·T² + D·T³
        kJ/(kg·K), T 单位 K"""
        try:
            A, B, C, D = fp["cp_A"], fp["cp_B"], fp["cp_C"], fp["cp_D"]
            T_K = T_C + 273.15
            Tmin = fp.get("cp_Tmin", 0)
            Tmax = fp.get("cp_Tmax", 9999)
            if T_K < Tmin or T_K > Tmax:
                raise ValueError("超出比热容多项式适用范围")
            cp = A + B * T_K + C * T_K**2 + D * T_K**3
            return max(0.0, cp)
        except Exception:
            return 0.0
    
    def _simple_density_correction(self, base_value, T, base_T):
        """简化密度修正（线性）"""
        if base_value is None:
            return 0.0
        vol_exp = 7e-4  # 液体体积膨胀系数近似值
        return base_value / (1.0 + vol_exp * (T - base_T))
    
    def _simple_viscosity_correction(self, base_value, T, base_T):
        """简化粘度修正"""
        if base_value is None:
            return None
        dT = T - base_T
        return base_value * math.exp(-0.02 * dT)
    
    def _simple_thermal_cond_correction(self, base_value, T, base_T, fp):
        """简化热导率修正"""
        if base_value is None:
            return None
        if "kt_A" in fp:
            try:
                dT = T - base_T
                kt = base_value + fp["kt_A"] * dT + fp["kt_B"] * dT**2 + fp["kt_C"] * dT**3
                return max(0.0, kt)
            except Exception:
                pass
        dT = T - base_T
        return base_value * (1.0 + 1e-3 * dT)
    
    def _simple_cp_correction(self, base_value, T, base_T):
        """简化比热容修正"""
        if base_value is None:
            return 0.0
        dT = T - base_T
        return base_value * (1.0 + 2e-3 * dT)
    
    def calculate_temperature_effect(self, base_value, temperature, property_type):
        """兼容旧接口的温度修正（保留用于温度扫描）"""
        substance_name = self.substance_combo.currentText()
        data = self.substance_data.get(substance_name, {})
        fp = data.get("formula_params", {})
        thermal = data.get("thermal", {})
        base_T = thermal.get("基准温度", 25.0)
        
        if property_type == "density":
            if "dippr_A" in fp:
                return self._dippr_density(fp, temperature)
            return self._simple_density_correction(thermal.get("密度", base_value), temperature, base_T)
        elif property_type == "viscosity":
            if "andrade_A" in fp:
                return self._andrade_viscosity(fp, temperature) or base_value
            return self._simple_viscosity_correction(thermal.get("粘度", base_value), temperature, base_T)
        elif property_type == "thermal_cond":
            return self._simple_thermal_cond_correction(thermal.get("热导率", base_value), temperature, base_T, fp)
        elif property_type == "heat_capacity":
            if "cp_A" in fp:
                return self._dippr_heat_capacity(fp, temperature)
            return self._simple_cp_correction(thermal.get("比热容", base_value), temperature, base_T)
        else:
            return base_value
    
    def update_table(self, table, data):
        """更新表格数据"""
        table.setRowCount(len(data))
        for i, row_data in enumerate(data):
            for j, data_item in enumerate(row_data):
                item = QTableWidgetItem(data_item)
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(i, j, item)
    
    def temperature_calculation(self):
        """温度影响计算"""
        try:
            substance = self.substance_combo.currentText()
            if substance not in self.substance_data:
                QMessageBox.warning(self, "计算错误", "请先选择有效的物质")
                return
            
            # 创建温度范围数据
            temperatures = [0, 25, 50, 75, 100]
            data = self.substance_data[substance]["thermal"]
            
            result_text = f"=== {substance} 温度影响分析 ===\n\n"
            result_text += f"{'温度(°C)':<12}{'密度(kg/m³)':<18}{'粘度(mPa·s)':<18}{'热导率(W/m·K)':<20}{'比热容(kJ/kg·K)':<20}\n"
            result_text += "-" * 90 + "\n"
            
            for temp in temperatures:
                density = self.calculate_temperature_effect(data["密度"], temp, "density")
                viscosity = self.calculate_temperature_effect(data["粘度"], temp, "viscosity")
                thermal_cond = self.calculate_temperature_effect(data["热导率"], temp, "thermal_cond")
                heat_capacity = self.calculate_temperature_effect(data["比热容"], temp, "heat_capacity")
                
                result_text += f"{temp:<12}{density:<18.3f}{viscosity if viscosity else 'N/A':<18}{thermal_cond if thermal_cond else 'N/A':<20}{heat_capacity:<20.3f}\n"
            
            self.result_text.setPlainText(result_text)
            
        except Exception as e:
            QMessageBox.warning(self, "计算错误", f"温度影响计算失败: {str(e)}")
    
    def clear_inputs(self):
        """清空输入"""
        self.category_combo.setCurrentIndex(0)
        self.temperature_input.setText("25")
        self.pressure_input.setText("101.3")
        self.basic_prop_table.setRowCount(0)
        self.thermo_prop_table.setRowCount(0)
        self.result_text.clear()

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = PureSubstanceProperties()
    widget.resize(1300, 700)
    widget.show()
    
    sys.exit(app.exec())
