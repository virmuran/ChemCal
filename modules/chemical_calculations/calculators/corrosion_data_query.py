from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
                              QLabel, QLineEdit, QComboBox, QPushButton,
                              QTextEdit, QTableWidget, QTableWidgetItem,
                              QHeaderView, QMessageBox, QTabWidget,
                              QScrollArea, QFileDialog, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
from fpdf import FPDF
import os
import datetime
import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
# DOCX 报告导出

# 统一GroupBox样式

class CorrosionDataQuery(CalculatorBase):
    """腐蚀数据查询计算器"""

    # 计算类型标识
    calculation_type = "腐蚀数据查询"

    def __init__(self, parent=None, data_manager=None):
        """构造函数

        Args:
            parent: 父窗口
            data_manager: 数据管理器（可选）
        """
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self.corrosion_data = self.load_corrosion_data()
        self.setup_ui()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from modules.data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception:
            self.data_manager = None

    def setup_ui(self):
        """构建统一风格的UI布局"""
        # 外层主布局：水平布局，间距15，边距10
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ========= 左侧输入区（QScrollArea包裹） =========
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } "
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        # 左侧内部容器
        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部说明文字
        desc_label = QLabel("查询工程材料和腐蚀介质的组合腐蚀数据，提供腐蚀速率、耐蚀评级和使用建议。支持多种材料和介质的腐蚀性能查询。")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc_label)

        # 查询条件组 — QGridLayout 三列 stretch(4,8,5)
        query_group = QGroupBox("查询条件")
        query_grid = QGridLayout(query_group)
        query_grid.setSpacing(12)
        query_grid.setHorizontalSpacing(10)
        query_grid.setColumnStretch(0, 4)
        query_grid.setColumnStretch(1, 8)
        query_grid.setColumnStretch(2, 5)

        label_style = "font-weight: bold; padding-right: 10px;"
        hint_style = "font-style: italic;"

        def make_lbl(text, row, col):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet(label_style)
            query_grid.addWidget(lbl, row, col)
            return lbl

        # 行0：材料类别
        make_lbl("材料类别:", 0, 0)
        self.material_category_combo = QComboBox()
        self.material_category_combo.setStyleSheet(COMBOBOX_STYLE)
        self.material_category_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.material_category_combo.addItems([
            "碳钢", "不锈钢", "合金钢", "铜及铜合金", "铝及铝合金",
            "钛及钛合金", "镍基合金", "塑料", "橡胶", "陶瓷"
        ])
        self.material_category_combo.currentTextChanged.connect(self.on_material_category_changed)
        query_grid.addWidget(self.material_category_combo, 0, 1)
        hint_0 = QLabel("选择材料大类")
        hint_0.setStyleSheet(hint_style)
        query_grid.addWidget(hint_0, 0, 2)

        # 行1：具体材料
        make_lbl("具体材料:", 1, 0)
        self.material_combo = QComboBox()
        self.material_combo.setStyleSheet(COMBOBOX_STYLE)
        self.material_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_grid.addWidget(self.material_combo, 1, 1)
        hint_1 = QLabel("选择具体材料")
        hint_1.setStyleSheet(hint_style)
        query_grid.addWidget(hint_1, 1, 2)

        # 行2：介质类别
        make_lbl("介质类别:", 2, 0)
        self.medium_category_combo = QComboBox()
        self.medium_category_combo.setStyleSheet(COMBOBOX_STYLE)
        self.medium_category_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.medium_category_combo.addItems([
            "酸类", "碱类", "盐类", "有机溶剂", "气体", "水及水溶液"
        ])
        self.medium_category_combo.currentTextChanged.connect(self.on_medium_category_changed)
        query_grid.addWidget(self.medium_category_combo, 2, 1)
        hint_2 = QLabel("选择介质大类")
        hint_2.setStyleSheet(hint_style)
        query_grid.addWidget(hint_2, 2, 2)

        # 行3：具体介质
        make_lbl("具体介质:", 3, 0)
        self.medium_combo = QComboBox()
        self.medium_combo.setStyleSheet(COMBOBOX_STYLE)
        self.medium_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_grid.addWidget(self.medium_combo, 3, 1)
        hint_3 = QLabel("选择具体介质")
        hint_3.setStyleSheet(hint_style)
        query_grid.addWidget(hint_3, 3, 2)

        # 行4：温度
        make_lbl("温度 (°C):", 4, 0)
        self.temperature_input = QLineEdit("25")
        self.temperature_input.setValidator(QDoubleValidator(-50, 500, 1))
        self.temperature_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_grid.addWidget(self.temperature_input, 4, 1)
        hint_4 = QLabel("操作温度条件")
        hint_4.setStyleSheet(hint_style)
        query_grid.addWidget(hint_4, 4, 2)

        # 行5：浓度
        make_lbl("浓度 (%):", 5, 0)
        self.concentration_input = QLineEdit("10")
        self.concentration_input.setValidator(QDoubleValidator(0, 100, 1))
        self.concentration_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_grid.addWidget(self.concentration_input, 5, 1)
        hint_5 = QLabel("介质浓度")
        hint_5.setStyleSheet(hint_style)
        query_grid.addWidget(hint_5, 5, 2)

        # 行6：pH值
        make_lbl("pH值:", 6, 0)
        self.ph_input = QLineEdit("7")
        self.ph_input.setValidator(QDoubleValidator(0, 14, 1))
        self.ph_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_grid.addWidget(self.ph_input, 6, 1)
        hint_6 = QLabel("介质酸碱度 (0-14)")
        hint_6.setStyleSheet(hint_style)
        query_grid.addWidget(hint_6, 6, 2)

        left_layout.addWidget(query_group)

        # 查询按钮（绿色 #27ae60）
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
            QPushButton:hover {
                background-color: #219955;
            } """)
        left_layout.addWidget(self.query_btn)

        # 搜索功能
        search_group = QGroupBox("快速搜索")
        search_layout = QHBoxLayout(search_group)

        search_label = QLabel("搜索关键词:")
        search_label.setStyleSheet("font-weight: bold;")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入材料或介质名称进行搜索...")
        self.search_input.returnPressed.connect(self.on_search)
        search_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self.on_search)
        self.search_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #27ae60; "
            "color: white; "
            "font-weight: bold; "
            "padding: 8px 16px; "
            "border: none; "
            "border-radius: 8px; "
            "}"
            "QPushButton:hover:!checked { background-color: #219955; }"
        )
        search_layout.addWidget(self.search_btn)
        left_layout.addWidget(search_group)

        # 标签页组件（材料库、腐蚀类型）
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(
            "QTabWidget::pane { "
            "border: 1px solid #888; "
            "border-radius: 6px; "
            "top: -1px; "
            "}"
            "QTabBar::tab { "
            "background: #ecf0f1; "
            "border: 1px solid #888; "
            "border-bottom: none; "
            "border-top-left-radius: 6px; "
            "border-top-right-radius: 6px; "
            "padding: 8px 16px; "
            "margin-right: 2px; "
            "font-weight: bold; "
            "}"
            "QTabBar::tab:selected { "
            "background: #ffffff; "
            "color: #2980b9; "
            "}"
            "QTabBar::tab:hover:!selected { "
            "background: #d5dbdb; "
            "}"
        )

        # 添加材料库标签页
        self.material_tab = self.create_material_tab()
        self.tab_widget.addTab(self.material_tab, "材料库")

        # 添加腐蚀类型标签页
        self.corrosion_types_tab = self.create_corrosion_types_tab()
        self.tab_widget.addTab(self.corrosion_types_tab, "腐蚀类型")

        left_layout.addWidget(self.tab_widget)

        # 弹性空间填充底部
        left_layout.addStretch()

        left_scroll.setWidget(left_widget)

        # ========= 右侧结果区 =========
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0, 0, 0, 0)

        result_group = QGroupBox("查询结果")
        result_vbox = QVBoxLayout(result_group)

        # 右侧 QTextEdit：只读、浅灰背景、圆角、最小高度500px
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
        self.result_text.setPlaceholderText("查询结果将在此处显示...")
        result_vbox.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # 底部按钮行（右侧）：清空（灰）→ Stretch → 下载TXT（蓝）→ 下载PDF（红）
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
        bottom_layout.addWidget(self.download_docx_btn)
        bottom_layout.addWidget(self.download_pdf_btn)
        right_layout.addLayout(bottom_layout)

        # ========= 按比例添加到主布局 =========
        main_layout.addWidget(left_scroll, 2)   # 左侧占2份
        main_layout.addWidget(right_widget, 1)  # 右侧占1份

        # 初始化下拉框选项
        self.on_material_category_changed(self.material_category_combo.currentText())
        self.on_medium_category_changed(self.medium_category_combo.currentText())

    def calculate(self):
        """执行计算 - 查询腐蚀数据"""
        try:
            # 获取查询条件
            material = self.material_combo.currentText()
            medium = self.medium_combo.currentText()
            try:
                temperature = float(self.temperature_input.text())
            except ValueError:
                temperature = 25.0
            try:
                concentration = float(self.concentration_input.text())
            except ValueError:
                concentration = 10.0
            try:
                ph = float(self.ph_input.text())
            except ValueError:
                ph = 7.0

            # 构建查询键
            query_key = f"{material}-{medium}"

            # 精确匹配查询
            if query_key in self.corrosion_data:
                data = self.corrosion_data[query_key]
                self.display_results(data, material, medium, temperature, concentration)
            else:
                # 无精确匹配时尝试模糊查询
                self.fuzzy_query(material, medium, temperature, concentration)

        except Exception as e:
            QMessageBox.warning(self, "查询错误", f"查询过程中发生错误: {str(e)}")

    def on_material_category_changed(self, category):
        """材料类别改变时更新具体材料下拉框"""
        materials = {
            "碳钢": ["Q235", "Q345", "20#钢", "45#钢", "A36", "A53"],
            "不锈钢": ["304", "304L", "316", "316L", "321", "310S", "2205", "2507"],
            "合金钢": ["15CrMo", "12Cr1MoV", "P91", "P92", "4130", "4140"],
            "铜及铜合金": ["纯铜", "黄铜", "青铜", "白铜", "铜镍合金"],
            "铝及铝合金": ["1060", "3003", "5052", "6061", "7075"],
            "钛及钛合金": ["纯钛", "Ti-6Al-4V", "Ti-0.2Pd"],
            "镍基合金": ["Inconel 600", "Inconel 625", "Hastelloy C276", "Monel 400"],
            "塑料": ["PVC", "PP", "PE", "PTFE", "PVDF"],
            "橡胶": ["NBR", "EPDM", "FKM", "CR", "SBR"],
            "陶瓷": ["氧化铝", "碳化硅", "氧化锆", "氮化硅"]
        }

        self.material_combo.clear()
        if category in materials:
            self.material_combo.addItems(materials[category])

    def on_medium_category_changed(self, category):
        """介质类别改变时更新具体介质下拉框"""
        mediums = {
            "酸类": ["盐酸", "硫酸", "硝酸", "磷酸", "醋酸", "氢氟酸", "柠檬酸"],
            "碱类": ["氢氧化钠", "氢氧化钾", "氨水", "碳酸钠", "石灰水"],
            "盐类": ["氯化钠", "氯化钾", "硫酸钠", "碳酸氢钠", "氯化钙", "硫酸铜"],
            "有机溶剂": ["甲醇", "乙醇", "丙酮", "苯", "甲苯", "二甲苯", "氯仿"],
            "气体": ["氧气", "氯气", "硫化氢", "二氧化碳", "氨气", "二氧化硫"],
            "水及水溶液": ["纯水", "自来水", "海水", "河水", "冷却水", "锅炉水"]
        }

        self.medium_combo.clear()
        if category in mediums:
            self.medium_combo.addItems(mediums[category])

    def create_material_tab(self):
        """创建材料库标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # 材料库说明
        info_group = QGroupBox("常用工程材料耐腐蚀性能参考")
        info_layout = QVBoxLayout(info_group)

        # 材料参数表
        material_table = QTableWidget()
        material_table.setColumnCount(6)
        material_table.setHorizontalHeaderLabels(["材料", "主要成分", "适用温度(°C)", "主要耐腐蚀介质", "不耐腐蚀介质", "应用领域"])

        material_data = [
            ["304不锈钢", "Cr18Ni9", "-270~800", "硝酸、有机酸、碱", "盐酸、氯化物", "化工、食品、医药"],
            ["316不锈钢", "Cr17Ni12Mo2", "-270~800", "硫酸、磷酸、有机酸", "盐酸、氢氟酸", "化工、海洋、医药"],
            ["碳钢Q235", "Fe-C", "-20~400", "碱、大气、水", "酸、氧化性介质", "建筑、结构、管道"],
            ["哈氏合金C276", "Ni-Mo-Cr", "-196~1000", "盐酸、硫酸、氯化物", "强氧化性酸", "化工、环保、海洋"],
            ["钛TA2", "Ti", "-270~300", "氯化物、海水、硝酸", "氢氟酸、干氯气", "化工、海洋、航空"],
            ["聚四氟乙烯", "C2F4", "-200~260", "几乎所有化学品", "熔融碱金属", "化工、电子、医疗"],
            ["聚丙烯", "C3H6", "0~100", "酸、碱、盐溶液", "氧化性酸、溶剂", "化工、水处理"],
            ["丁腈橡胶", "NBR", "-30~120", "油类、脂肪烃", "酮、酯、臭氧", "密封、油管"]
        ]

        material_table.setRowCount(len(material_data))
        for i, row_data in enumerate(material_data):
            for j, data in enumerate(row_data):
                item = QTableWidgetItem(data)
                item.setTextAlignment(Qt.AlignCenter)
                material_table.setItem(i, j, item)

        # 表格列宽 Stretch 铺满
        header = material_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        material_table.verticalHeader().setVisible(False)

        info_layout.addWidget(material_table)
        layout.addWidget(info_group)

        return tab

    def create_corrosion_types_tab(self):
        """创建腐蚀类型标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        corrosion_group = QGroupBox("常见腐蚀类型知识")
        group_layout = QVBoxLayout(corrosion_group)

        corrosion_text = QTextEdit()
        corrosion_text.setReadOnly(True)
        corrosion_text.setPlainText(self.get_corrosion_types_text())
        corrosion_text.setStyleSheet(
            "QTextEdit { "
            "background-color: #ffffff; "
            "border: 1px solid #888; "
            "border-radius: 4px; "
            "padding: 8px; "
            "}"
        )
        group_layout.addWidget(corrosion_text)
        layout.addWidget(corrosion_group)

        return tab

    def get_corrosion_types_text(self):
        """获取腐蚀类型的文本内容"""
        text = "常见腐蚀类型\n\n"
        text += "1. 均匀腐蚀\n"
        text += "   特征：整个金属表面均匀减薄\n"
        text += "   原因：化学或电化学反应在整个表面均匀发生\n"
        text += "   防护：选用耐腐蚀材料、涂层、缓蚀剂\n\n"

        text += "2. 点蚀\n"
        text += "   特征：局部区域形成小孔或凹坑\n"
        text += "   原因：局部破坏钝化膜，形成腐蚀电池\n"
        text += "   易发材料：不锈钢、铝、钛在含氯离子环境中\n\n"

        text += "3. 缝隙腐蚀\n"
        text += "   特征：在缝隙或遮蔽区域发生\n"
        text += "   原因：缝隙内外氧浓度差异形成浓差电池\n"
        text += "   防护：避免缝隙设计、使用密封剂\n\n"

        text += "4. 电偶腐蚀\n"
        text += "   特征：两种不同金属接触处的腐蚀\n"
        text += "   原因：电位差驱动电子流动\n"
        text += "   防护：避免异种金属接触、使用绝缘材料\n\n"

        text += "5. 应力腐蚀开裂\n"
        text += "   特征：在拉应力和特定介质共同作用下开裂\n"
        text += "   原因：应力加速局部腐蚀\n"
        text += "   典型组合：奥氏体不锈钢-氯离子、碳钢-硝酸盐\n\n"

        text += "6. 晶间腐蚀\n"
        text += "   特征：沿晶界选择性腐蚀\n"
        text += "   原因：晶界区与晶内成分差异\n"
        text += "   典型材料：不锈钢敏化态、铝合金\n\n"

        text += "7. 腐蚀疲劳\n"
        text += "   特征：交变应力与腐蚀介质共同作用\n"
        text += "   原因：腐蚀降低材料疲劳强度\n"
        text += "   防护：降低应力集中、表面处理\n\n"

        text += "8. 冲刷腐蚀\n"
        text += "   特征：流体冲刷加速腐蚀\n"
        text += "   原因：机械磨损与化学腐蚀协同作用\n"
        text += "   防护：降低流速、选用耐磨材料\n\n"

        text += "腐蚀速率等级\n\n"
        text += "   < 0.025 mm/年：优秀（完全耐蚀）\n"
        text += "   0.025 - 0.05 mm/年：良好（耐蚀）\n"
        text += "   0.05 - 0.125 mm/年：可用（尚耐蚀）\n"
        text += "   0.125 - 0.25 mm/年：差（不耐蚀）\n"
        text += "   > 0.25 mm/年：很差（严重腐蚀）\n\n"

        text += "参考标准\n"
        text += "   GB/T 10123-2001 金属和合金的腐蚀基本术语\n"
        text += "   GB/T 18590-2001 金属和合金的腐蚀点蚀评定方法\n"
        text += "   ASTM G31 实验室浸渍腐蚀试验\n"
        text += "   NACE MR0175 油田设备用金属材料抗硫化物应力开裂\n"

        return text

    def load_corrosion_data(self):
        """加载腐蚀数据库（内置模拟数据）"""
        corrosion_data = {
            # 碳钢数据
            "Q235-盐酸": {"rate": 12.5, "rating": "很差", "notes": "严重腐蚀，不推荐使用"},
            "Q235-硫酸": {"rate": 1.2, "rating": "差", "notes": "浓度<70%时可用，但腐蚀严重"},
            "Q235-氢氧化钠": {"rate": 0.02, "rating": "优秀", "notes": "常温下耐蚀性良好"},
            "Q235-海水": {"rate": 0.15, "rating": "差", "notes": "需要防护涂层"},

            # 不锈钢数据
            "304-盐酸": {"rate": 2.5, "rating": "很差", "notes": "不推荐使用，腐蚀严重"},
            "304-硫酸": {"rate": 0.08, "rating": "可用", "notes": "低浓度、常温下可用"},
            "304-硝酸": {"rate": 0.01, "rating": "优秀", "notes": "优良的耐硝酸性能"},
            "304-海水": {"rate": 0.05, "rating": "可用", "notes": "可能发生点蚀"},

            "316-盐酸": {"rate": 1.8, "rating": "很差", "notes": "不推荐使用"},
            "316-硫酸": {"rate": 0.05, "rating": "良好", "notes": "耐蚀性优于304"},
            "316-海水": {"rate": 0.02, "rating": "良好", "notes": "较好的耐海水性能"},

            # 钛数据
            "纯钛-盐酸": {"rate": 0.001, "rating": "优秀", "notes": "优良的耐盐酸性能"},
            "纯钛-海水": {"rate": 0.0001, "rating": "优秀", "notes": "极佳的耐海水性能"},
            "纯钛-硝酸": {"rate": 0.001, "rating": "优秀", "notes": "优良的耐硝酸性能"},

            # 哈氏合金数据
            "哈氏合金C276-盐酸": {"rate": 0.05, "rating": "可用", "notes": "在高温高浓度下仍可用"},
            "哈氏合金C276-硫酸": {"rate": 0.02, "rating": "良好", "notes": "优良的耐硫酸性能"},

            # 塑料数据
            "PVC-盐酸": {"rate": 0.001, "rating": "优秀", "notes": "优良的耐盐酸性能"},
            "PVC-硫酸": {"rate": 0.001, "rating": "优秀", "notes": "优良的耐硫酸性能"},
            "PTFE-盐酸": {"rate": 0.0001, "rating": "优秀", "notes": "几乎不腐蚀"}
        }

        return corrosion_data

    def query_corrosion_data(self):
        """执行腐蚀数据查询（保留旧接口）"""
        self.calculate()

    def fuzzy_query(self, material, medium, temperature, concentration):
        """模糊查询：查找相关腐蚀数据"""
        related_data = []
        for key, value in self.corrosion_data.items():
            if material in key and medium in key:
                related_data.append((key, value))

        if related_data:
            # 构建模糊查询结果文本
            result = f"=== 相关腐蚀数据 ===\n\n"
            result += f"未找到精确匹配「{material}-{medium}」，以下是相关数据：\n\n"
            result += f"{'材料-介质':<25}{'腐蚀速率(mm/年)':<20}{'评级':<12}{'说明':<30}\n"
            result += "-" * 90 + "\n"

            for key, data in related_data:
                result += f"{key:<25}{data['rate']:<20}{data['rating']:<12}{data['notes']:<30}\n"

            self.result_text.setPlainText(result)

        else:
            self.result_text.setPlainText(f"未找到包含「{material}」和「{medium}」的相关腐蚀数据。")

    def get_rate_color(self, rate):
        """根据腐蚀速率返回对应的颜色标记"""
        if rate < 0.025:
            return "green"
        elif rate < 0.05:
            return "blue"
        elif rate < 0.125:
            return "orange"
        else:
            return "red"

    def display_results(self, data, material, medium, temperature, concentration):
        """显示精确匹配的查询结果"""
        rate_color = self.get_rate_color(data["rate"])

        result = f"=== 腐蚀数据查询结果 ===\n\n"
        result += f"材料-介质: {material} - {medium}\n"
        result += f"腐蚀速率: {data['rate']} mm/年\n"
        result += f"耐蚀评级: {data['rating']}\n"
        result += f"温度条件: {temperature} °C\n"
        result += f"浓度条件: {concentration} %\n\n"

        result += f"说明与建议\n"
        result += f"{data['notes']}\n\n"

        # 根据腐蚀速率添加使用建议
        if data["rate"] < 0.05:
            result += "建议：该材料在此介质中耐蚀性良好，可以选用。\n"
        elif data["rate"] < 0.125:
            result += "建议：该材料在此介质中耐蚀性一般，需要定期检查和维护。\n"
        else:
            result += "建议：该材料在此介质中耐蚀性差，不推荐使用，请选用其他材料。\n"

        # 计算不同壁厚下的使用寿命估算
        thickness_options = [3, 5, 8, 10]  # mm
        result += f"\n使用寿命估算（假设腐蚀均匀）：\n"
        for thickness in thickness_options:
            if data["rate"] > 0:
                life = thickness / data["rate"]
                result += f"  {thickness}mm厚度: 约{life:.1f}年\n"

        self.result_text.setPlainText(result)

    def on_search(self):
        """快速搜索功能"""
        keyword = self.search_input.text().strip().lower()
        if not keyword:
            return

        results = []
        for key, value in self.corrosion_data.items():
            if keyword in key.lower():
                results.append((key, value))

        if results:
            result_text = f"=== 搜索结果：「{keyword}」 ===\n\n"
            result_text += f"{'材料-介质':<25}{'速率(mm/年)':<18}{'评级':<12}{'备注':<30}\n"
            result_text += "-" * 90 + "\n"
            for key, data in results:
                result_text += f"{key:<25}{data['rate']:<18}{data['rating']:<12}{data['notes']:<30}\n"
            self.result_text.setPlainText(result_text)
        else:
            self.result_text.setPlainText(f"未找到包含「{keyword}」的相关数据。")

    def clear_inputs(self):
        """清空所有输入和结果"""
        self.material_category_combo.setCurrentIndex(0)
        self.medium_category_combo.setCurrentIndex(0)
        self.temperature_input.setText("25")
        self.concentration_input.setText("10")
        self.ph_input.setText("7")
        self.result_text.clear()
        self.search_input.clear()

    def _get_history_data(self):
        """获取当前查询的历史记录数据（供外部调用）

        Returns:
            dict: 包含inputs和outputs的字典
        """
        material = self.material_combo.currentText()
        medium = self.medium_combo.currentText()
        try:
            temperature = float(self.temperature_input.text())
        except ValueError:
            temperature = 25.0
        try:
            concentration = float(self.concentration_input.text())
        except ValueError:
            concentration = 10.0
        try:
            ph = float(self.ph_input.text())
        except ValueError:
            ph = 7.0

        inputs = {
            "材料类别": self.material_category_combo.currentText(),
            "具体材料": material,
            "介质类别": self.medium_category_combo.currentText(),
            "具体介质": medium,
            "温度_C": temperature,
            "浓度_%": concentration,
            "pH值": ph
        }

        outputs = {}
        # 从查询结果提取输出数据
        result_text = self.result_text.toPlainText()
        if result_text and "腐蚀速率:" in result_text:
            for line in result_text.split("\n"):
                if "腐蚀速率:" in line:
                    outputs["腐蚀速率"] = line.split(":")[1].strip()
                elif "耐蚀评级:" in line:
                    outputs["耐蚀评级"] = line.split(":")[1].strip()

        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        """获取项目信息（报告生成用）

        Returns:
            dict: 项目基本信息字典
        """
        return {
            "project_name": "腐蚀数据查询",
            "calculation_type": self.calculation_type,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operator": "用户",
        }

    def generate_report(self):
        """生成完整的查询报告内容

        Returns:
            str: 格式化的完整报告文本
        """
        history = self._get_history_data()
        project = self.get_project_info()

        report_lines = [
            "=" * 60,
            "              腐蚀数据查询报告",
            "=" * 60,
            "",
            f"生成时间：{project['timestamp']}",
            f"计算类型：{project['calculation_type']}",
            "",
            "-" * 40,
            "【查询条件】",
            "-" * 40,
        ]
        for k, v in history["inputs"].items():
            report_lines.append(f"  {k}: {v}")

        report_lines.extend([
            "",
            "-" * 40,
            "【查询结果】",
            "-" * 40,
        ])
        for k, v in history["outputs"].items():
            report_lines.append(f"  {k}: {v}")

        # 补充详情文本
        detail_content = self.result_text.toPlainText().strip()
        if detail_content:
            report_lines.extend([
                "",
                "-" * 40,
                "【详细信息】",
                "-" * 40,
                detail_content
            ])

        report_lines.extend([
            "",
            "=" * 60,
            "                     报告结束",
            "=" * 60,
        ])

        return "\n".join(report_lines)

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "CorrosionDataQuery")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "CorrosionDataQuery")
if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = CorrosionDataQuery()
    widget.resize(1300, 700)
    widget.show()

    sys.exit(app.exec())
