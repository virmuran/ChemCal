from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QLabel, QLineEdit, QPushButton, QComboBox,
                              QTextEdit, QGridLayout, QScrollArea,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QMessageBox, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math
from modules.combo_box_utils import ComboBoxWheelBlocker

# =============================================================================
# 工业级气体物性内置数据库
# =============================================================================
_GAS_DB = {
    "氮气(N2)": {
        'sigma': 3.798, 'eps_k': 71.4,
        'coeffs_lo': [3.53101, -0.000123661, -5.02999e-7, 2.43531e-9, -1.40881e-12],
        'coeffs_hi': [2.95258, 1.39690e-3, -4.92632e-7, 7.86010e-11, -4.60755e-15],
    },
    "氧气(O2)": {
        'sigma': 3.467, 'eps_k': 106.7,
        'coeffs_lo': [3.78246, -2.99674e-3, 9.84730e-6, -9.68130e-9, 3.24373e-12],
        'coeffs_hi': [3.69758, 6.13520e-4, -1.25884e-7, 1.77528e-11, -1.13644e-15],
    },
    "氢气(H2)": {
        'sigma': 2.827, 'eps_k': 59.7,
        'coeffs_lo': [2.34433, 7.98052e-3, -1.94782e-5, 2.01572e-8, -7.37612e-12],
        'coeffs_hi': [3.33728, -4.94025e-5, 4.99457e-7, -1.79566e-10, 2.00255e-14],
    },
    "二氧化碳(CO2)": {
        'sigma': 3.941, 'eps_k': 195.2,
        'coeffs_lo': [2.35677, 8.98460e-3, -7.12356e-6, 2.45919e-9, -1.43699e-13],
        'coeffs_hi': [3.85746, 4.41437e-3, -2.21481e-6, 5.23490e-10, -4.72084e-14],
    },
    "甲烷(CH4)": {
        'sigma': 3.758, 'eps_k': 148.6,
        'coeffs_lo': [5.14988, -1.36709e-2, 4.91800e-5, -4.84743e-8, 1.66694e-11],
        'coeffs_hi': [1.65326, 1.00263e-2, -3.31661e-6, 5.36483e-10, -3.14697e-14],
    },
    "乙烷(C2H6)": {
        'sigma': 4.443, 'eps_k': 215.7,
        'coeffs_lo': [4.29142, -5.50155e-3, 5.99438e-5, -7.08466e-8, 2.68686e-11],
        'coeffs_hi': [4.82594, 1.38401e-2, -4.55725e-6, 6.72097e-10, -3.59816e-14],
    },
    "丙烷(C3H8)": {
        'sigma': 5.118, 'eps_k': 237.1,
        'coeffs_lo': [4.21200, 1.70859e-3, 6.30198e-5, -8.19614e-8, 3.16948e-11],
        'coeffs_hi': [6.66950, 2.00640e-2, -6.82300e-6, 1.00994e-9, -5.47893e-14],
    },
    "水蒸气(H2O)": {
        'sigma': 2.641, 'eps_k': 809.1,
        'coeffs_lo': [4.19864, -2.03643e-3, 6.52040e-6, -5.48797e-9, 1.77197e-12],
        'coeffs_hi': [2.67704, 2.97319e-3, -7.73769e-7, 9.44335e-11, -4.26900e-15],
    },
    "氩气(Ar)": {
        'sigma': 3.542, 'eps_k': 93.3,
        'coeffs_lo': [2.5, 0.0, 0.0, 0.0, 0.0],
        'coeffs_hi': [2.5, 0.0, 0.0, 0.0, 0.0],
    },
    "一氧化碳(CO)": {
        'sigma': 3.690, 'eps_k': 91.7,
        'coeffs_lo': [3.57954, -6.10354e-4, 1.01681e-6, 9.07006e-10, -9.04424e-13],
        'coeffs_hi': [3.04849, 1.35173e-3, -4.85794e-7, 7.88536e-11, -4.69807e-15],
    },
}

# 预设气体物性参数（用于组分表默认填充）
_PRESET_GASES = {
    "氮气(N2)": [28.013, 126.2, 3390, 89.5, 0.037, 0.29],
    "氧气(O2)": [31.999, 154.6, 5043, 73.4, 0.021, 0.288],
    "氢气(H2)": [2.016, 33.2, 1315, 65.0, -0.216, 0.305],
    "二氧化碳(CO2)": [44.01, 304.2, 7377, 94.0, 0.225, 0.274],
    "甲烷(CH4)": [16.043, 190.6, 4600, 99.0, 0.008, 0.288],
    "乙烷(C2H6)": [30.07, 305.4, 4880, 148.0, 0.098, 0.285],
    "丙烷(C3H8)": [44.096, 369.8, 4248, 203.0, 0.152, 0.281],
    "水蒸气(H2O)": [18.015, 647.3, 22064, 56.0, 0.344, 0.229],
    "氩气(Ar)": [39.948, 150.9, 4898, 74.9, -0.002, 0.291],
    "一氧化碳(CO)": [28.01, 132.9, 3498, 93.1, 0.045, 0.292],
}

# Neufeld et al. (1972) 碰撞积分参数
_NF_A, _NF_B, _NF_C, _NF_D, _NF_E, _NF_F = 1.16145, 0.14874, 0.52487, 0.77320, 2.16178, 2.43787

def _neufeld_omega(T_star):
    """Neufeld et al. (1972) 碰撞积分 Omega_v"""
    return (_NF_A / T_star**_NF_B +
            _NF_C / math.exp(_NF_D * T_star) +
            _NF_E / math.exp(_NF_F * T_star))

def _nasa_cp(name, T_K):
    """NASA 7系数多项式计算 cp [J/(mol·K)]"""
    db = _GAS_DB.get(name)
    if db is None:
        return 30.0
    R = 8.314
    a = db['coeffs_hi'] if T_K >= 1000.0 else db['coeffs_lo']
    cp_R = a[0] + a[1]*T_K + a[2]*T_K**2 + a[3]*T_K**3 + a[4]*T_K**4
    return cp_R * R

def _pure_viscosity_CE(name, mw_gmol, T_K):
    """Chapman-Enskog 公式计算纯气体粘度 [Pa·s]"""
    db = _GAS_DB.get(name)
    if db is None:
        return 1.78e-5 * (T_K / 293.15) ** 0.71
    sigma = db['sigma']
    eps_k = db['eps_k']
    T_star = T_K / eps_k
    omega = _neufeld_omega(T_star)
    mu_poise = 2.6693e-5 * math.sqrt(mw_gmol * T_K) / (sigma**2 * omega)
    return mu_poise * 0.1

def _lee_kesler_z(Tr, Pr, omega):
    """Lee-Kesler (1975) 方程计算气相压缩因子"""
    def _lk_Z(rho_r, Tr, b1,b2,b3,b4,c1,c2,c3,c4,d1,d2,beta,gamma):
        B = b1 - b2/Tr - b3/Tr**2 - b4/Tr**3
        C = c1 - c2/Tr + c3/Tr**3
        D = d1 + d2/Tr
        return (1.0 + B*rho_r + C*rho_r**2 + D*rho_r**5
                + c4*rho_r**2/Tr**3*(beta + gamma*rho_r**2)*math.exp(-gamma*rho_r**2))

    def _solve_rho(Tr, Pr, params):
        rho = Pr / Tr
        for _ in range(2000):
            Z = _lk_Z(rho, Tr, *params)
            rho_new = Pr / (Z * Tr)
            rho_new = max(1e-6, min(rho_new, 20.0))
            if abs(rho_new - rho) < 1e-11:
                return rho_new
            rho = 0.3 * rho + 0.7 * rho_new
        return rho

    p0 = (0.1181193, 0.265728, 0.154790, 0.030323,
          0.0236744,  0.0186984, 0.0, 0.042724,
          1.55488e-4, 6.23689e-5, 0.65392, 0.060167)
    p1 = (0.2026579, 0.331511,  0.027655, 0.203488,
          0.0313422,  0.0503323, 0.016901, 0.041577,
          4.8736e-4,  0.0740336, 1.226,    0.03754)

    if Tr <= 0 or Pr <= 0:
        return 1.0
    try:
        rho0 = _solve_rho(Tr, Pr, p0)
        Z0 = _lk_Z(rho0, Tr, *p0)
        rho1 = _solve_rho(Tr, Pr, p1)
        Z1 = _lk_Z(rho1, Tr, *p1)
        Z = Z0 + (omega / 0.3978) * (Z1 - Z0)
        return max(0.05, min(Z, 5.0))
    except Exception:
        B0 = 0.083 - 0.422 / Tr**1.6
        B1 = 0.139 - 0.172 / Tr**4.2
        return max(0.1, 1.0 + (B0 + omega * B1) * Pr / Tr)


# ---------------------------------------------------------------------------
#  QGroupBox 统一样式
# ---------------------------------------------------------------------------
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


class GasMixturePropertiesCalculator(QWidget):
    """气体混合物物性计算器 - 统一UI风格版"""

    calculation_type = "gas_mixture_properties_calculator"

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)

        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()

        self.components = []
        self._last_calc_results = {}
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
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None

    def setup_ui(self):
        """设置UI界面 - 统一风格布局"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ====== 左侧：输入参数区域 ======
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } "
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 1. 顶部说明文字
        description = QLabel(
            "计算气体混合物的密度、粘度、热导率、比热容、压缩因子等物性参数。"
            "支持 Lee-Kesler 压缩因子、Chapman-Enskog 粘度、Wilke 混合规则、NASA 比热多项式。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)

        # 2. 计算条件组
        condition_group = QGroupBox("计算条件")
        condition_layout = QGridLayout(condition_group)
        condition_layout.setVerticalSpacing(12)
        condition_layout.setHorizontalSpacing(10)

        label_style = "QLabel { font-weight: bold; padding-right: 10px; }"

        # 温度
        temp_label = QLabel("温度:")
        temp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        temp_label.setStyleSheet(label_style)
        condition_layout.addWidget(temp_label, 0, 0)

        self.temperature_input = QLineEdit()
        self.temperature_input.setText("25")
        self.temperature_input.setPlaceholderText("例如：25")
        self.temperature_input.setValidator(QDoubleValidator(-273, 2000, 2))
        self.temperature_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(self.temperature_input, 0, 1)

        temp_hint = QLabel("°C")
        temp_hint.setStyleSheet("color: #7f8c8d;")
        condition_layout.addWidget(temp_hint, 0, 2)

        # 压力
        pres_label = QLabel("压力:")
        pres_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pres_label.setStyleSheet(label_style)
        condition_layout.addWidget(pres_label, 1, 0)

        self.pressure_input = QLineEdit()
        self.pressure_input.setText("101.325")
        self.pressure_input.setPlaceholderText("例如：101.325")
        self.pressure_input.setValidator(QDoubleValidator(0.1, 100000, 2))
        self.pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(self.pressure_input, 1, 1)

        pres_hint = QLabel("kPa")
        pres_hint.setStyleSheet("color: #7f8c8d;")
        condition_layout.addWidget(pres_hint, 1, 2)

        # 混合物类型
        mix_label = QLabel("混合物类型:")
        mix_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        mix_label.setStyleSheet(label_style)
        condition_layout.addWidget(mix_label, 2, 0)

        self.mixture_type = QComboBox()
        self.mixture_type.setStyleSheet(COMBOBOX_STYLE)
        self.mixture_type.addItems(["理想气体", "真实气体"])
        self.mixture_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(self.mixture_type, 2, 1)

        mix_hint = QLabel("真实气体用Lee-Kesler")
        mix_hint.setStyleSheet("font-style: italic;")
        condition_layout.addWidget(mix_hint, 2, 2)

        # 计算方法
        method_label = QLabel("计算方法:")
        method_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        method_label.setStyleSheet(label_style)
        condition_layout.addWidget(method_label, 3, 0)

        self.calculation_method = QComboBox()
        self.calculation_method.setStyleSheet(COMBOBOX_STYLE)
        self.calculation_method.addItems(["简单混合规则", "Kay规则", "对应状态原理"])
        self.calculation_method.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(self.calculation_method, 3, 1)

        method_hint = QLabel("Kay规则/对应状态")
        method_hint.setStyleSheet("font-style: italic;")
        condition_layout.addWidget(method_hint, 3, 2)

        # 组分数
        comp_label = QLabel("组分数:")
        comp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        comp_label.setStyleSheet(label_style)
        condition_layout.addWidget(comp_label, 4, 0)

        self.component_count = QComboBox()
        self.component_count.setStyleSheet(COMBOBOX_STYLE)
        self.component_count.addItems(["2", "3", "4", "5"])
        self.component_count.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.component_count.currentTextChanged.connect(self.update_component_table)
        condition_layout.addWidget(self.component_count, 4, 1)

        comp_hint = QLabel("2~5组分混合")
        comp_hint.setStyleSheet("font-style: italic;")
        condition_layout.addWidget(comp_hint, 4, 2)

        condition_layout.setColumnStretch(0, 4)
        condition_layout.setColumnStretch(1, 8)
        condition_layout.setColumnStretch(2, 5)
        left_layout.addWidget(condition_group)

        # 3. 组分参数表
        component_group = QGroupBox("组分参数")
        component_table_layout = QVBoxLayout(component_group)
        self.component_table = QTableWidget()
        self.component_table.setColumnCount(8)
        self.component_table.setHorizontalHeaderLabels([
            "组分", "摩尔分数", "分子量", "临界温度(K)", "临界压力(kPa)", "临界体积(cm³/mol)", "偏心因子", "Zc"
        ])
        self.component_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        component_table_layout.addWidget(self.component_table)
        left_layout.addWidget(component_group)

        # 4. 计算按钮
        calculate_btn = QPushButton("查询")
        calculate_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calculate_btn.clicked.connect(self.calculate)
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
        left_layout.addWidget(calculate_btn)

        # 5. 底部按钮行
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
        self.download_txt_btn = QPushButton("下载计算书(TXT)")
        self.download_txt_btn.clicked.connect(self.download_txt_report)
        self.download_txt_btn.setMinimumHeight(50)
        self.download_txt_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_txt_btn.setStyleSheet("""
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
        bottom_layout.addWidget(self.download_txt_btn)
        bottom_layout.addWidget(self.download_pdf_btn)
        left_layout.addLayout(bottom_layout)

        # 底部拉伸
        left_layout.addStretch()

        # ====== 右侧：结果显示区域 ======
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        result_group = QGroupBox("计算结果")
        result_inner = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #666;
                border-radius: 6px;
                padding: 8px;
                /* bg via theme */min-height: 500px;
            }
        """)
        result_inner.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # 将左右添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

        # 初始化表格
        self.update_component_table()

    # ------------------------------------------------------------------
    #  组分表管理
    # ------------------------------------------------------------------

    def update_component_table(self):
        """更新组分参数表"""
        count = int(self.component_count.currentText())
        self.component_table.setRowCount(count)

        for i in range(count):
            name_combo = QComboBox()
            name_combo.setStyleSheet(COMBOBOX_STYLE)
            name_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            name_combo.addItems(list(_PRESET_GASES.keys()))
            name_combo.setCurrentIndex(i % len(_PRESET_GASES))
            self.component_table.setCellWidget(i, 0, name_combo)

            current_name = name_combo.currentText()
            params = _PRESET_GASES.get(current_name, [0, 0, 0, 0, 0, 0])

            if i == 0:
                y_item = QTableWidgetItem("0.5")
            elif i == 1:
                y_item = QTableWidgetItem("0.5")
            else:
                y_item = QTableWidgetItem("0.0")
            self.component_table.setItem(i, 1, y_item)
            self.component_table.setItem(i, 2, QTableWidgetItem(f"{params[0]:.3f}"))
            self.component_table.setItem(i, 3, QTableWidgetItem(f"{params[1]:.1f}"))
            self.component_table.setItem(i, 4, QTableWidgetItem(f"{params[2]:.0f}"))
            self.component_table.setItem(i, 5, QTableWidgetItem(f"{params[3]:.1f}"))
            self.component_table.setItem(i, 6, QTableWidgetItem(f"{params[4]:.3f}"))
            self.component_table.setItem(i, 7, QTableWidgetItem(f"{params[5]:.3f}"))

    def get_component_data(self):
        """从表格获取组分数据"""
        count = int(self.component_count.currentText())
        components = []
        for i in range(count):
            name = self.component_table.cellWidget(i, 0).currentText()
            y = float(self.component_table.item(i, 1).text())
            mw = float(self.component_table.item(i, 2).text())
            tc = float(self.component_table.item(i, 3).text())
            pc = float(self.component_table.item(i, 4).text())
            vc = float(self.component_table.item(i, 5).text())
            omega = float(self.component_table.item(i, 6).text())
            zc = float(self.component_table.item(i, 7).text())
            components.append({
                'name': name, 'y': y, 'mw': mw, 'tc': tc, 'pc': pc,
                'vc': vc, 'omega': omega, 'zc': zc
            })
        return components

    # ------------------------------------------------------------------
    #  计算核心
    # ------------------------------------------------------------------

    def calculate(self):
        """执行气体混合物物性计算"""
        try:
            temperature = float(self.temperature_input.text())
            pressure = float(self.pressure_input.text())
            mixture_type = self.mixture_type.currentText()
            method = self.calculation_method.currentText()

            components = self.get_component_data()
            total_y = sum(comp['y'] for comp in components)
            if abs(total_y - 1.0) > 0.01:
                self.result_text.setPlainText(f"⚠ 摩尔分数总和应为1.0，当前为{total_y:.3f}")
                return

            results = self.calculate_mixture_properties(components, temperature, pressure, mixture_type, method)
            self._last_calc_results = results
            self._last_calc_results.update({
                "temperature": temperature, "pressure": pressure,
                "mixture_type": mixture_type, "method": method,
                "components": components
            })
            self._format_results(results, components)

        except ValueError:
            self.result_text.setPlainText("⚠ 输入参数格式错误，请检查输入值。")
        except Exception as e:
            self.result_text.setPlainText(f"⚠ 计算错误: {str(e)}")

    def calculate_mixture_properties(self, components, T, P, mixture_type, method):
        """计算气体混合物物性"""
        T_k = T + 273.15
        mw_mix = sum(comp['y'] * comp['mw'] for comp in components)

        if method in ("简单混合规则", "Kay规则"):
            tc_mix = sum(comp['y'] * comp['tc'] for comp in components)
            pc_mix = sum(comp['y'] * comp['pc'] for comp in components)
            vc_mix = sum(comp['y'] * comp['vc'] for comp in components)
            omega_mix = sum(comp['y'] * comp['omega'] for comp in components)
            zc_mix = sum(comp['y'] * comp['zc'] for comp in components)
        else:
            tc_mix = 0.0
            pc_mix = 0.0
            vc_mix = 0.0
            for i, comp_i in enumerate(components):
                for j, comp_j in enumerate(components):
                    k_ij = 0.0
                    if i != j:
                        k_ij = 1 - ((comp_i['vc'] ** (1/3) * comp_j['vc'] ** (1/3)) /
                                   (0.5 * (comp_i['vc'] ** (2/3) + comp_j['vc'] ** (2/3)))) ** 3
                    tc_ij = (1 - k_ij) * math.sqrt(comp_i['tc'] * comp_j['tc'])
                    vc_ij = ((comp_i['vc'] ** (1/3) + comp_j['vc'] ** (1/3)) / 2) ** 3
                    zc_ij = 0.291 - 0.08 * (comp_i['omega'] + comp_j['omega']) / 2
                    pc_ij = zc_ij * 8.314 * tc_ij / vc_ij * 1000
                    tc_mix += comp_i['y'] * comp_j['y'] * tc_ij
                    pc_mix += comp_i['y'] * comp_j['y'] * pc_ij
                    vc_mix += comp_i['y'] * comp_j['y'] * vc_ij
            omega_mix = sum(comp['y'] * comp['omega'] for comp in components)
            zc_mix = 0.291 - 0.08 * omega_mix

        tr = T_k / tc_mix if tc_mix > 0 else 1.0
        pr = P / pc_mix if pc_mix > 0 else 1.0

        if vc_mix > 0 and tc_mix > 0 and pc_mix > 0:
            R_gas = 8.314
            Vc_m3 = vc_mix * 1e-6
            Pc_Pa = pc_mix * 1e3
            zc_calc = Pc_Pa * Vc_m3 / (R_gas * tc_mix)
            vr = zc_calc / zc_mix if zc_mix > 0 else 1.0
        else:
            vr = 1.0

        z_factor = 1.0 if mixture_type == "理想气体" else _lee_kesler_z(tr, pr, omega_mix)

        if mixture_type == "理想气体":
            density = P * 1000 * mw_mix / (8.314 * T_k)
        else:
            density = P * 1000 * mw_mix / (z_factor * 8.314 * T_k)

        viscosity = self._calc_viscosity(components, T_k)
        thermal_conductivity = self._calc_thermal_conductivity(components, T_k)
        cp_mix, cv_mix, gamma = self._calc_heat_capacity(components, T_k, mixture_type, tc_mix, pc_mix, omega_mix)
        sound_speed = math.sqrt(gamma * z_factor * 8.314 * T_k / (mw_mix / 1000)) if mw_mix > 0 else 0
        reduced_density = density / (mw_mix / vc_mix * 1000) if vc_mix > 0 else 0

        return {
            'mw_mix': mw_mix, 'tc_mix': tc_mix, 'pc_mix': pc_mix,
            'vc_mix': vc_mix, 'omega_mix': omega_mix, 'zc_mix': zc_mix,
            'density': density, 'z_factor': z_factor, 'viscosity': viscosity,
            'thermal_conductivity': thermal_conductivity,
            'cp_mix': cp_mix, 'cv_mix': cv_mix, 'gamma': gamma,
            'sound_speed': sound_speed, 'tr': tr, 'pr': pr,
            'vr': vr, 'reduced_density': reduced_density
        }

    def _calc_viscosity(self, components, T):
        """Chapman-Enskog + Wilke 混合粘度 [μPa·s]"""
        mus = [_pure_viscosity_CE(c['name'], c['mw'], T) for c in components]
        n = len(components)
        mu_mix = 0.0
        for i in range(n):
            if components[i]['y'] < 1e-10:
                continue
            denom = 0.0
            for j in range(n):
                if components[j]['y'] < 1e-10:
                    continue
                sqrt_mu = math.sqrt(mus[i] / mus[j]) if mus[j] > 0 else 1.0
                mwj_mwi = components[j]['mw'] / components[i]['mw']
                phi_ij = (1.0 + sqrt_mu * mwj_mwi**0.25)**2 / math.sqrt(8.0 * (1.0 + components[i]['mw'] / components[j]['mw']))
                denom += components[j]['y'] * phi_ij
            if denom > 0:
                mu_mix += components[i]['y'] * mus[i] / denom
        return mu_mix * 1e6

    def _calc_thermal_conductivity(self, components, T):
        """修正 Eucken + Mason-Saxena 混合热导率 [W/(m·K)]"""
        R = 8.314
        ks = []
        mus_Pa = []
        for comp in components:
            mu_i = _pure_viscosity_CE(comp['name'], comp['mw'], T)
            cp_mol = _nasa_cp(comp['name'], T)
            Mi = comp['mw'] * 1e-3
            k_i = mu_i * (cp_mol / Mi + 1.25 * R / Mi)
            ks.append(k_i)
            mus_Pa.append(mu_i)

        n = len(components)
        k_mix = 0.0
        for i in range(n):
            if components[i]['y'] < 1e-10:
                continue
            denom = 0.0
            for j in range(n):
                if components[j]['y'] < 1e-10:
                    continue
                sqrt_mu = math.sqrt(mus_Pa[i] / mus_Pa[j]) if mus_Pa[j] > 0 else 1.0
                mwj_mwi = components[j]['mw'] / components[i]['mw']
                phi_ij = (1.0 + sqrt_mu * mwj_mwi**0.25)**2 / math.sqrt(8.0 * (1.0 + components[i]['mw'] / components[j]['mw']))
                denom += components[j]['y'] * phi_ij
            if denom > 0:
                k_mix += components[i]['y'] * ks[i] / denom
        return k_mix

    def _calc_heat_capacity(self, components, T, mixture_type, tc_mix, pc_mix, omega_mix):
        """NASA 比热 + 真实气体修正 [J/(mol·K)]"""
        R = 8.314
        cp_ideal = sum(c['y'] * _nasa_cp(c['name'], T) for c in components)
        cv_ideal = cp_ideal - R

        if mixture_type == "理想气体":
            return cp_ideal, cv_ideal, cp_ideal / cv_ideal

        Tr = T / tc_mix if tc_mix > 0 else 1.0
        Pr = 101.325 / pc_mix if pc_mix > 0 else 0.01
        cp_dep = -R * omega_mix * 0.172 / Tr**4.2 * Pr
        cp_mix = max(cv_ideal + 1e-3, cp_ideal + cp_dep)
        z = _lee_kesler_z(Tr, Pr, omega_mix) if tc_mix > 0 and pc_mix > 0 else 1.0
        cv_mix = max(1e-3, cp_mix - R * z)
        gamma = cp_mix / cv_mix if cv_mix > 0 else 1.4
        return cp_mix, cv_mix, gamma

    # ------------------------------------------------------------------
    #  结果格式化
    # ------------------------------------------------------------------

    def _format_results(self, r, components):
        lines = []
        lines.append("═══════════════════════════════════════")
        lines.append("      气体混合物物性计算结果")
        lines.append("═══════════════════════════════════════")
        lines.append(f"")
        lines.append(f"计算条件: {r.get('mixture_type', '')} / {r.get('method', '')}")
        lines.append(f"温度: {r.get('temperature', 0):.1f} °C  ({r.get('temperature', 0)+273.15:.1f} K)")
        lines.append(f"压力: {r.get('pressure', 0):.2f} kPa")
        lines.append(f"")
        lines.append(f"─── 虚拟临界参数 ───")
        lines.append(f"  平均分子量:       {r['mw_mix']:.3f} g/mol")
        lines.append(f"  虚拟临界温度:     {r['tc_mix']:.1f} K")
        lines.append(f"  虚拟临界压力:     {r['pc_mix']:.0f} kPa")
        lines.append(f"  虚拟临界体积:     {r['vc_mix']:.1f} cm³/mol")
        lines.append(f"  平均偏心因子:     {r['omega_mix']:.4f}")
        lines.append(f"  虚拟临界压缩因子: {r['zc_mix']:.4f}")
        lines.append(f"")
        lines.append(f"─── 热物性 ───")
        lines.append(f"  密度:       {r['density']:.4f} kg/m³")
        lines.append(f"  压缩因子:   {r['z_factor']:.4f}")
        lines.append(f"  粘度:       {r['viscosity']:.2f} μPa·s")
        lines.append(f"  热导率:     {r['thermal_conductivity']:.4f} W/(m·K)")
        lines.append(f"  定压比热:   {r['cp_mix']:.3f} J/(mol·K)")
        lines.append(f"  定容比热:   {r['cv_mix']:.3f} J/(mol·K)")
        lines.append(f"  比热比:     {r['gamma']:.4f}")
        lines.append(f"  音速:       {r['sound_speed']:.1f} m/s")
        lines.append(f"")
        lines.append(f"─── 对应状态参数 ───")
        lines.append(f"  对比温度 Tr: {r['tr']:.4f}")
        lines.append(f"  对比压力 Pr: {r['pr']:.4f}")
        lines.append(f"  对比体积 Vr: {r['vr']:.4f}")
        lines.append(f"  对比密度:   {r['reduced_density']:.4f}")
        lines.append(f"")
        lines.append(f"─── 各组分信息 ───")
        for c in components:
            lines.append(f"  {c['name']}: y={c['y']:.4f}, M={c['mw']:.2f}, Tc={c['tc']:.1f}K, Pc={c['pc']:.0f}kPa")
        self.result_text.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------
    #  清空
    # ------------------------------------------------------------------

    def clear_inputs(self):
        self.temperature_input.setText("25")
        self.pressure_input.setText("101.325")
        self.update_component_table()
        self.result_text.clear()
        self._last_calc_results = {}

    # ------------------------------------------------------------------
    #  历史数据 / 项目信息 / 报告
    # ------------------------------------------------------------------

    def _get_history_data(self):
        temperature = float(self.temperature_input.text() or 0)
        pressure = float(self.pressure_input.text() or 0)
        mixture_type = self.mixture_type.currentText()
        method = self.calculation_method.currentText()
        inputs = {
            "温度_C": temperature, "压力_kPa": pressure,
            "混合物类型": mixture_type, "计算方法": method
        }
        outputs = {}
        try:
            r = self._last_calc_results
            if r:
                outputs = {
                    "混合分子量": round(r.get('mw_mix', 0), 3),
                    "密度_kg_m3": round(r.get('density', 0), 4),
                    "压缩系数": round(r.get('z_factor', 0), 4),
                    "粘度_uPa_s": round(r.get('viscosity', 0), 2),
                    "热导率_W_mK": round(r.get('thermal_conductivity', 0), 4),
                    "定压比热_J_molK": round(r.get('cp_mix', 0), 3),
                    "绝热指数": round(r.get('gamma', 0), 4),
                    "音速_m_s": round(r.get('sound_speed', 0), 1),
                }
        except Exception as e:
            outputs["计算错误"] = str(e)
        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        return {
            "project_name": "气体混合物物性计算",
            "calculator_name": "气体混合物物性计算器",
            "version": "1.0",
            "description": "Chapman-Enskog粘度+Lee-Kesler压缩因子+NASA比热"
        }

    def generate_report(self):
        r = self._last_calc_results
        if not r:
            return "尚未进行计算。"
        lines = []
        lines.append("气体混合物物性计算报告")
        lines.append("=" * 50)
        lines.append(f"混合物类型: {r.get('mixture_type', '')}")
        lines.append(f"计算方法: {r.get('method', '')}")
        lines.append(f"温度: {r.get('temperature', 0):.1f} °C")
        lines.append(f"压力: {r.get('pressure', 0):.2f} kPa")
        lines.append("")
        lines.append(self.result_text.toPlainText())
        return "\n".join(lines)

    def download_txt_report(self):
        try:
            from PySide6.QtWidgets import QFileDialog
            content = self.generate_report()
            if not content or content == "尚未进行计算。":
                QMessageBox.warning(self, "提示", "请先进行计算后再下载。")
                return
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存计算书", "气体混合物物性计算书.txt", "Text Files (*.txt)"
            )
            if file_path:
                from datetime import datetime
                header = f"ChemCal - 气体混合物物性计算\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}\n\n"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(header + content)
                QMessageBox.information(self, "成功", f"计算书已保存至:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def download_pdf_report(self):
        try:
            from PySide6.QtWidgets import QFileDialog
            content = self.generate_report()
            if not content or content == "尚未进行计算。":
                QMessageBox.warning(self, "提示", "请先进行计算后再下载。")
                return
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存PDF计算书", "气体混合物物性计算书.pdf", "PDF Files (*.pdf)"
            )
            if file_path:
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                try:
                    font_path = "C:/Windows/Fonts/msyh.ttc"
                    pdf.add_font("msyh", "", font_path, uni=True)
                    pdf.set_font("msyh", size=10)
                except Exception:
                    pdf.set_font("Helvetica", size=10)
                for line in content.split("\n"):
                    pdf.cell(0, 6, line, ln=True)
                pdf.output(file_path)
                QMessageBox.information(self, "成功", f"PDF计算书已保存至:\n{file_path}")
        except ImportError:
            QMessageBox.critical(self, "错误", "需要安装 fpdf 库: pip install fpdf")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"PDF生成失败: {str(e)}")


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    calculator = GasMixturePropertiesCalculator()
    calculator.resize(1200, 800)
    calculator.show()
    sys.exit(app.exec())
