from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                              QLabel, QLineEdit, QComboBox, QPushButton, 
                              QTextEdit, QTableWidget, QTableWidgetItem,
                              QHeaderView, QMessageBox, QTabWidget, QDoubleSpinBox,
                              QCheckBox, QRadioButton, QButtonGroup, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math

class PureSubstanceProperties(QWidget):
    """纯物质物性数据查询"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.substance_data = self.load_substance_data()
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("纯物质物性数据查询")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 添加查询标签页
        self.query_tab = self.create_query_tab()
        self.tab_widget.addTab(self.query_tab, "物性查询")
        
        # 添加物质库标签页
        self.substance_lib_tab = self.create_substance_lib_tab()
        self.tab_widget.addTab(self.substance_lib_tab, "物质库")
        
        # 添加计算公式标签页
        self.formula_tab = self.create_formula_tab()
        self.tab_widget.addTab(self.formula_tab, "计算公式")
        
        main_layout.addWidget(self.tab_widget)
    
    def create_query_tab(self):
        """创建查询标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 查询条件组
        query_group = QGroupBox("查询条件")
        query_layout = QVBoxLayout(query_group)
        
        # 物质选择
        substance_layout = QHBoxLayout()
        substance_layout.addWidget(QLabel("物质类别:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "无机物", "有机物", "金属", "气体", "液体", "固体"
        ])
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        substance_layout.addWidget(self.category_combo)
        
        substance_layout.addWidget(QLabel("具体物质:"))
        self.substance_combo = QComboBox()
        substance_layout.addWidget(self.substance_combo)
        
        substance_layout.addWidget(QLabel("CAS号:"))
        self.cas_label = QLabel("")
        substance_layout.addWidget(self.cas_label)
        
        query_layout.addLayout(substance_layout)
        
        # 温度压力条件
        condition_layout = QHBoxLayout()
        condition_layout.addWidget(QLabel("温度 (°C):"))
        self.temperature_input = QDoubleSpinBox()
        self.temperature_input.setRange(-273, 5000)
        self.temperature_input.setValue(25)
        self.temperature_input.setSuffix(" °C")
        condition_layout.addWidget(self.temperature_input)
        
        condition_layout.addWidget(QLabel("压力 (kPa):"))
        self.pressure_input = QDoubleSpinBox()
        self.pressure_input.setRange(0.1, 100000)
        self.pressure_input.setValue(101.3)
        self.pressure_input.setSuffix(" kPa")
        condition_layout.addWidget(self.pressure_input)
        
        condition_layout.addWidget(QLabel("状态:"))
        self.state_label = QLabel("液态")
        condition_layout.addWidget(self.state_label)
        
        query_layout.addLayout(condition_layout)
        
        layout.addWidget(query_group)
        
        # 按钮组
        button_layout = QHBoxLayout()
        self.query_btn = QPushButton("查询物性数据")
        self.query_btn.clicked.connect(self.query_properties)
        self.query_btn.setStyleSheet("QPushButton { background-color: #8e44ad; color: white; font-weight: bold; }")
        button_layout.addWidget(self.query_btn)
        
        self.temp_calc_btn = QPushButton("温度影响计算")
        self.temp_calc_btn.clicked.connect(self.temperature_calculation)
        self.temp_calc_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; }")
        button_layout.addWidget(self.temp_calc_btn)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_inputs)
        self.clear_btn.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; }")
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # 基本物性组
        basic_prop_group = QGroupBox("基本物性")
        basic_prop_layout = QVBoxLayout(basic_prop_group)
        
        self.basic_prop_table = QTableWidget()
        self.basic_prop_table.setColumnCount(3)
        self.basic_prop_table.setHorizontalHeaderLabels(["物性", "数值", "单位"])
        basic_prop_layout.addWidget(self.basic_prop_table)
        
        layout.addWidget(basic_prop_group)
        
        # 热力学性质组
        thermo_prop_group = QGroupBox("热力学性质")
        thermo_prop_layout = QVBoxLayout(thermo_prop_group)
        
        self.thermo_prop_table = QTableWidget()
        self.thermo_prop_table.setColumnCount(3)
        self.thermo_prop_table.setHorizontalHeaderLabels(["物性", "数值", "单位"])
        thermo_prop_layout.addWidget(self.thermo_prop_table)
        
        layout.addWidget(thermo_prop_group)
        
        # 初始化下拉框
        self.on_category_changed(self.category_combo.currentText())
        
        return tab
    
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
    
    def create_substance_lib_tab(self):
        """创建物质库标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 物质库说明
        info_label = QLabel("常见纯物质物性数据参考")
        info_label.setFont(QFont("Arial", 12, QFont.Bold))
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # 物质参数表
        substance_table = QTableWidget()
        substance_table.setColumnCount(7)
        substance_table.setHorizontalHeaderLabels(["物质", "分子式", "分子量", "沸点(°C)", "熔点(°C)", "密度(g/cm³)", "CAS号"])
        
        substance_data = [
            ["水", "H₂O", "18.015", "100.0", "0.0", "0.997", "7732-18-5"],
            ["氨", "NH₃", "17.031", "-33.3", "-77.7", "0.602", "7664-41-7"],
            ["二氧化碳", "CO₂", "44.010", "-78.5", "-56.6", "0.776", "124-38-9"],
            ["硫酸", "H₂SO₄", "98.079", "337.0", "10.4", "1.835", "7664-93-9"],
            ["氯化钠", "NaCl", "58.44", "1465", "801", "2.165", "7647-14-5"],
            ["甲醇", "CH₃OH", "32.042", "64.7", "-97.6", "0.787", "67-56-1"],
            ["乙醇", "C₂H₅OH", "46.069", "78.4", "-114.1", "0.785", "64-17-5"],
            ["丙酮", "CH₃COCH₃", "58.080", "56.1", "-94.7", "0.784", "67-64-1"],
            ["苯", "C₆H₆", "78.114", "80.1", "5.5", "0.876", "71-43-2"],
            ["甲苯", "C₇H₈", "92.141", "110.6", "-95.0", "0.862", "108-88-3"],
            ["乙酸", "CH₃COOH", "60.052", "118.0", "16.6", "1.044", "64-19-7"],
            ["正己烷", "C₆H₁₄", "86.178", "68.7", "-95.3", "0.655", "110-54-3"],
            ["环己烷", "C₆H₁₂", "84.162", "80.7", "6.5", "0.774", "110-82-7"],
            ["甲烷", "CH₄", "16.043", "-161.5", "-182.5", "0.424", "74-82-8"],
            ["乙烷", "C₂H₆", "30.070", "-88.6", "-182.8", "0.546", "74-84-0"],
            ["丙烷", "C₃H₈", "44.096", "-42.1", "-187.7", "0.493", "74-98-6"],
            ["乙烯", "C₂H₄", "28.054", "-103.7", "-169.2", "0.610", "74-85-1"],
            ["丙烯", "C₃H₆", "42.081", "-47.6", "-185.2", "0.519", "115-07-1"],
            ["空气", "混合", "28.966", "-194.3", "-", "0.001", "132259-10-0"],
            ["氧气", "O₂", "31.999", "-183.0", "-218.8", "0.001", "7782-44-7"],
            ["氮气", "N₂", "28.014", "-195.8", "-210.0", "0.001", "7727-37-9"],
            ["氢气", "H₂", "2.016", "-252.9", "-259.2", "0.000", "1333-74-0"],
            ["铁", "Fe", "55.845", "2862", "1538", "7.874", "7439-89-6"],
            ["铜", "Cu", "63.546", "2562", "1085", "8.960", "7440-50-8"],
            ["铝", "Al", "26.982", "2467", "660", "2.700", "7429-90-5"],
        ]
        
        substance_table.setRowCount(len(substance_data))
        for i, row_data in enumerate(substance_data):
            for j, data in enumerate(row_data):
                item = QTableWidgetItem(data)
                item.setTextAlignment(Qt.AlignCenter)
                substance_table.setItem(i, j, item)
        
        # 调整列宽
        header = substance_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        layout.addWidget(substance_table)
        
        return tab
    
    def create_formula_tab(self):
        """创建计算公式标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 计算公式说明
        formula_text = QTextEdit()
        formula_text.setReadOnly(True)
        formula_text.setHtml(self.get_formula_html())
        layout.addWidget(formula_text)
        
        return tab
    
    def get_formula_html(self):
        """获取计算公式HTML内容"""
        return """
        <h2>物性计算公式</h2>
        
        <h3>1. 密度计算</h3>
        <p><b>理想气体密度：</b>ρ = P × M / (R × T)</p>
        <p>其中：P-压力(Pa)，M-分子量(kg/mol)，R-气体常数(8.314 J/mol·K)，T-温度(K)</p>
        
        <h3>2. 蒸气压计算</h3>
        <p><b>Antoine方程：</b>log₁₀(P) = A - B / (T + C)</p>
        <p>其中：P-蒸气压(mmHg)，T-温度(°C)，A、B、C为物质常数</p>
        
        <h3>3. 粘度计算</h3>
        <p><b>液体粘度：</b>μ = A × exp(B / T)</p>
        <p><b>气体粘度：</b>μ = μ₀ × (T/T₀)<sup>n</sup></p>
        <p>其中：A、B、μ₀、T₀、n为物质常数</p>
        
        <h3>4. 热导率计算</h3>
        <p><b>液体热导率：</b>k = A + B × T + C × T²</p>
        <p><b>气体热导率：</b>k = k₀ × (T/T₀)<sup>m</sup></p>
        
        <h3>5. 热容计算</h3>
        <p><b>定压热容：</b>C<sub>p</sub> = A + B × T + C × T² + D × T³</p>
        <p><b>定容热容：</b>C<sub>v</sub> = C<sub>p</sub> - R</p>
        
        <h3>6. 临界性质关系</h3>
        <p><b>对比温度：</b>T<sub>r</sub> = T / T<sub>c</sub></p>
        <p><b>对比压力：</b>P<sub>r</sub> = P / P<sub>c</sub></p>
        <p><b>对比体积：</b>V<sub>r</sub> = V / V<sub>c</sub></p>
        
        <h3>7. 状态方程</h3>
        <p><b>理想气体：</b>PV = nRT</p>
        <p><b>van der Waals：</b>(P + a/V²)(V - b) = RT</p>
        <p><b>Redlich-Kwong：</b>P = RT/(V - b) - a/(√T × V(V + b))</p>
        
        <h3>8. 热力学关系</h3>
        <p><b>焓变：</b>ΔH = ∫C<sub>p</sub>dT</p>
        <p><b>熵变：</b>ΔS = ∫(C<sub>p</sub>/T)dT</p>
        <p><b>Gibbs自由能：</b>ΔG = ΔH - TΔS</p>
        
        <h3>常用常数</h3>
        <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr style="background-color: #3498db; color: white;">
            <th style="padding: 8px;">常数</th>
            <th style="padding: 8px;">符号</th>
            <th style="padding: 8px;">数值</th>
            <th style="padding: 8px;">单位</th>
        </tr>
        <tr>
            <td style="padding: 8px;">通用气体常数</td>
            <td style="padding: 8px;">R</td>
            <td style="padding: 8px;">8.314</td>
            <td style="padding: 8px;">J/mol·K</td>
        </tr>
        <tr>
            <td style="padding: 8px;">Avogadro常数</td>
            <td style="padding: 8px;">N<sub>A</sub></td>
            <td style="padding: 8px;">6.022×10²³</td>
            <td style="padding: 8px;">mol⁻¹</td>
        </tr>
        <tr>
            <td style="padding: 8px;">Boltzmann常数</td>
            <td style="padding: 8px;">k</td>
            <td style="padding: 8px;">1.381×10⁻²³</td>
            <td style="padding: 8px;">J/K</td>
        </tr>
        <tr>
            <td style="padding: 8px;">标准大气压</td>
            <td style="padding: 8px;">P<sub>atm</sub></td>
            <td style="padding: 8px;">101.325</td>
            <td style="padding: 8px;">kPa</td>
        </tr>
        </table>
        
        <h3>参考数据源</h3>
        <ul>
            <li>CRC Handbook of Chemistry and Physics</li>
            <li>Perry's Chemical Engineers' Handbook</li>
            <li>NIST Chemistry WebBook</li>
            <li>DIPPR Project 801 Database</li>
        </ul>
        """
    
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
        """查询物性数据"""
        try:
            # 获取查询条件
            substance = self.substance_combo.currentText()
            temperature = self.temperature_input.value()
            pressure = self.pressure_input.value()
            
            # 查询数据
            if substance in self.substance_data:
                data = self.substance_data[substance]
                self.update_state_label(substance, temperature)
                self.display_basic_properties(data["basic"])
                self.display_thermal_properties(data["thermal"], temperature, pressure)
            else:
                QMessageBox.information(self, "查询结果", f"未找到物质 '{substance}' 的物性数据")
                
        except Exception as e:
            QMessageBox.warning(self, "查询错误", f"查询过程中发生错误: {str(e)}")

    def _get_history_data(self):
        """提供历史记录数据"""
        substance = self.substance_combo.currentText()
        temperature = self.temperature_input.value()
        pressure = self.pressure_input.value()

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
        
        # 调整列宽
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
    
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
            
            result_text = f"<h3>{substance} 温度影响分析</h3>"
            result_text += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
            result_text += "<tr style='background-color: #f8f9fa;'>"
            result_text += "<th style='padding: 8px;'>温度(°C)</th>"
            result_text += "<th style='padding: 8px;'>密度(g/cm³)</th>"
            result_text += "<th style='padding: 8px;'>粘度(mPa·s)</th>"
            result_text += "<th style='padding: 8px;'>热导率(W/m·K)</th>"
            result_text += "<th style='padding: 8px;'>比热容(kJ/kg·K)</th>"
            result_text += "</tr>"
            
            for temp in temperatures:
                density = self.calculate_temperature_effect(data["密度"], temp, "density")
                viscosity = self.calculate_temperature_effect(data["粘度"], temp, "viscosity")
                thermal_cond = self.calculate_temperature_effect(data["热导率"], temp, "thermal_cond")
                heat_capacity = self.calculate_temperature_effect(data["比热容"], temp, "heat_capacity")
                
                result_text += f"""
                <tr>
                    <td style='padding: 8px;'>{temp}</td>
                    <td style='padding: 8px;'>{density:.3f}</td>
                    <td style='padding: 8px;'>{viscosity:.3f}</td>
                    <td style='padding: 8px;'>{thermal_cond:.3f}</td>
                    <td style='padding: 8px;'>{heat_capacity:.3f}</td>
                </tr>
                """
            
            result_text += "</table>"
            
            QMessageBox.information(self, "温度影响分析", result_text.replace("<table", "<table width='100%'").replace("<h3>", "").replace("</h3>", ""))
            
        except Exception as e:
            QMessageBox.warning(self, "计算错误", f"温度影响计算失败: {str(e)}")
    
    def clear_inputs(self):
        """清空输入"""
        self.category_combo.setCurrentIndex(0)
        self.temperature_input.setValue(25)
        self.pressure_input.setValue(101.3)
        self.basic_prop_table.setRowCount(0)
        self.thermo_prop_table.setRowCount(0)

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = PureSubstanceProperties()
    widget.resize(900, 700)
    widget.show()
    
    sys.exit(app.exec())