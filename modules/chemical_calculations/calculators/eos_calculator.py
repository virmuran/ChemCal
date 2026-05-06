from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QLabel, QLineEdit, QPushButton, QComboBox,
                              QFormLayout, QTextEdit, QGridLayout, QScrollArea,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QTabWidget, QCheckBox, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math


# ---------------------------------------------------------------------------
#  纯 Python 三次方程求解器（无需 numpy）
# ---------------------------------------------------------------------------

def solve_cubic_real_roots(a, b, c, d):
    """求解 ax³+bx²+cx+d=0，返回所有实根（从大到小）。"""
    if abs(a) < 1e-30:
        if abs(b) < 1e-30:
            return []
        disc = c * c - 4 * b * d
        if disc < 0:
            return []
        sq = math.sqrt(disc)
        return sorted([(-c - sq) / (2 * b), (-c + sq) / (2 * b)], reverse=True)
    # Vieta 代换 x = t - p/3
    p = b / a
    q = c / a
    r = d / a
    A = q - p * p / 3.0
    B = r - p * q / 3.0 + 2.0 * p * p * p / 27.0
    disc = -(4 * A * A * A + 27 * B * B)
    if disc > 1e-10:
        # 三个不等实根
        m = 2.0 * math.sqrt(-A / 3.0)
        theta = math.acos(max(-1.0, min(1.0, -B / (m * m * m / 2.0)))) / 3.0
        roots = []
        for k in range(3):
            t = m * math.cos(theta + 2 * math.pi * k / 3.0)
            roots.append(t - p / 3.0)
        return sorted(roots, reverse=True)
    elif abs(disc) < 1e-10:
        # 重根
        t1 = 3.0 * B / A if abs(A) > 1e-30 else 0.0
        x1 = t1 - p / 3.0
        x2 = -t1 / 2.0 - p / 3.0
        if abs(x1 - x2) > 1e-10:
            return sorted([x1, x2, x2], reverse=True)
        return [x1]
    else:
        # 一个实根 + 两个共轭复根
        half_B = B / 2.0
        sq = half_B * half_B + A * A * A / 27.0
        if sq < 0:
            sq = 0.0
        C = (abs(half_B + math.sqrt(sq))) ** (1.0 / 3.0)
        D = (abs(half_B - math.sqrt(sq))) ** (1.0 / 3.0)
        t = -(C + D) if B > 0 else -(C - D)
        return [t - p / 3.0]


def _solve_cubic(a, b, c, d):
    """求解 ax³+bx²+cx+d=0，返回所有正实根（从大到小）。"""
    try:
        roots = solve_cubic_real_roots(a, b, c, d)
        return [r for r in roots if r > 1e-12]
    except Exception:
        return []


# ---------------------------------------------------------------------------
#  物质参数数据库（22 种常见化工物质）
# ---------------------------------------------------------------------------

SUBSTANCE_DATABASE = {
    "甲烷":    {"tc": 190.56, "pc": 4599,  "omega": 0.0115, "mw": 16.04, "zc": 0.286},
    "乙烷":    {"tc": 305.32, "pc": 4872,  "omega": 0.0995, "mw": 30.07, "zc": 0.285},
    "丙烷":    {"tc": 369.83, "pc": 4248,  "omega": 0.1523, "mw": 44.10, "zc": 0.281},
    "正丁烷":  {"tc": 425.12, "pc": 3796,  "omega": 0.2002, "mw": 58.12, "zc": 0.274},
    "异丁烷":  {"tc": 408.14, "pc": 3648,  "omega": 0.1848, "mw": 58.12, "zc": 0.282},
    "正戊烷":  {"tc": 469.70, "pc": 3370,  "omega": 0.2515, "mw": 72.15, "zc": 0.270},
    "正己烷":  {"tc": 507.50, "pc": 3025,  "omega": 0.3013, "mw": 86.18, "zc": 0.266},
    "正庚烷":  {"tc": 540.20, "pc": 2740,  "omega": 0.3495, "mw": 100.20, "zc": 0.261},
    "正辛烷":  {"tc": 568.70, "pc": 2490,  "omega": 0.3996, "mw": 114.23, "zc": 0.259},
    "乙烯":    {"tc": 282.35, "pc": 5042,  "omega": 0.0866, "mw": 28.05, "zc": 0.281},
    "丙烯":    {"tc": 364.90, "pc": 4600,  "omega": 0.1424, "mw": 42.08, "zc": 0.275},
    "二氧化碳": {"tc": 304.21, "pc": 7383,  "omega": 0.2236, "mw": 44.01, "zc": 0.274},
    "氮气":    {"tc": 126.19, "pc": 3394,  "omega": 0.0377, "mw": 28.01, "zc": 0.290},
    "氢气":    {"tc": 33.19,  "pc": 1313,  "omega": -0.2160, "mw": 2.016, "zc": 0.305},
    "氧气":    {"tc": 154.58, "pc": 5043,  "omega": 0.0218, "mw": 32.00, "zc": 0.288},
    "水":      {"tc": 647.10, "pc": 22064, "omega": 0.3438, "mw": 18.02, "zc": 0.229},
    "氩气":    {"tc": 150.87, "pc": 4898,  "omega": -0.0022, "mw": 39.95, "zc": 0.291},
    "氦气":    {"tc": 5.195,  "pc": 227.5, "omega": -0.390, "mw": 4.003, "zc": 0.302},
    "氨":      {"tc": 405.40, "pc": 11353, "omega": 0.2563, "mw": 17.03, "zc": 0.244},
    "硫化氢":  {"tc": 373.50, "pc": 8963,  "omega": 0.0943, "mw": 34.08, "zc": 0.284},
    "二氧化硫": {"tc": 430.75, "pc": 7884,  "omega": 0.2451, "mw": 64.07, "zc": 0.269},
    "苯":      {"tc": 562.05, "pc": 4895,  "omega": 0.2098, "mw": 78.11, "zc": 0.268},
}


# ---------------------------------------------------------------------------
#  EOS 计算器主类
# ---------------------------------------------------------------------------

class EOSCalculator(QWidget):
    """状态方程计算器"""

    calculation_type = "eos_calculator"  # 模块加载所需属性

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置状态方程计算界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # 标题
        title_label = QLabel("状态方程计算")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        main_layout.addWidget(title_label)

        desc_label = QLabel("使用各种状态方程计算流体的热力学性质，包括 van der Waals、RK、SRK、PR 等立方型状态方程")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #7f8c8d; margin: 5px;")
        main_layout.addWidget(desc_label)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        self.tab_widget = QTabWidget()

        # ---- 物质参数标签页 ----
        substance_tab = QWidget()
        substance_layout = QVBoxLayout(substance_tab)

        substance_group = QGroupBox("物质参数")
        substance_layout_grid = QGridLayout(substance_group)

        self.substance_selection = QComboBox()
        self.substance_selection.addItems(["自定义"] + list(SUBSTANCE_DATABASE.keys()))
        self.substance_selection.currentTextChanged.connect(self.update_substance_parameters)

        self.tc_input = QLineEdit()
        self.tc_input.setPlaceholderText("例如：190.56")
        self.tc_input.setValidator(QDoubleValidator(1, 2000, 2))

        self.pc_input = QLineEdit()
        self.pc_input.setPlaceholderText("例如：4599")
        self.pc_input.setValidator(QDoubleValidator(100, 100000, 1))

        self.omega_input = QLineEdit()
        self.omega_input.setPlaceholderText("例如：0.0115")
        self.omega_input.setValidator(QDoubleValidator(-1, 2, 4))

        self.mw_input = QLineEdit()
        self.mw_input.setPlaceholderText("例如：16.04")
        self.mw_input.setValidator(QDoubleValidator(1, 500, 3))

        self.zc_input = QLineEdit()
        self.zc_input.setPlaceholderText("例如：0.286")
        self.zc_input.setValidator(QDoubleValidator(0.1, 0.5, 3))

        substance_layout_grid.addWidget(QLabel("物质:"), 0, 0)
        substance_layout_grid.addWidget(self.substance_selection, 0, 1, 1, 5)

        substance_layout_grid.addWidget(QLabel("临界温度:"), 1, 0)
        substance_layout_grid.addWidget(self.tc_input, 1, 1)
        substance_layout_grid.addWidget(QLabel("K"), 1, 2)
        substance_layout_grid.addWidget(QLabel("临界压力:"), 1, 3)
        substance_layout_grid.addWidget(self.pc_input, 1, 4)
        substance_layout_grid.addWidget(QLabel("kPa"), 1, 5)

        substance_layout_grid.addWidget(QLabel("偏心因子 ω:"), 2, 0)
        substance_layout_grid.addWidget(self.omega_input, 2, 1)
        substance_layout_grid.addWidget(QLabel(""), 2, 2)
        substance_layout_grid.addWidget(QLabel("分子量:"), 2, 3)
        substance_layout_grid.addWidget(self.mw_input, 2, 4)
        substance_layout_grid.addWidget(QLabel("g/mol"), 2, 5)

        substance_layout_grid.addWidget(QLabel("临界压缩因子:"), 3, 0)
        substance_layout_grid.addWidget(self.zc_input, 3, 1)
        substance_layout_grid.addWidget(QLabel(""), 3, 2)

        substance_layout.addWidget(substance_group)

        # 状态方程选择
        eos_group = QGroupBox("状态方程选择")
        eos_layout = QGridLayout(eos_group)

        self.eos_type = QComboBox()
        self.eos_type.addItems([
            "理想气体方程",
            "范德瓦尔斯方程",
            "Redlich-Kwong方程",
            "Soave-Redlich-Kwong方程",
            "Peng-Robinson方程"
        ])

        self.calc_type_combo = QComboBox()
        self.calc_type_combo.addItems([
            "P-V-T关系计算",
            "压缩因子计算",
            "逸度系数计算",
            "剩余性质计算"
        ])

        eos_layout.addWidget(QLabel("状态方程:"), 0, 0)
        eos_layout.addWidget(self.eos_type, 0, 1, 1, 2)
        eos_layout.addWidget(QLabel("计算类型:"), 0, 3)
        eos_layout.addWidget(self.calc_type_combo, 0, 4, 1, 2)

        substance_layout.addWidget(eos_group)

        # 计算条件
        condition_group = QGroupBox("计算条件")
        condition_layout = QGridLayout(condition_group)

        self.temperature_input = QLineEdit()
        self.temperature_input.setPlaceholderText("例如：298.15")
        self.temperature_input.setValidator(QDoubleValidator(1, 2000, 2))

        self.pressure_input = QLineEdit()
        self.pressure_input.setPlaceholderText("例如：101.325")
        self.pressure_input.setValidator(QDoubleValidator(0.1, 100000, 2))

        self.volume_input = QLineEdit()
        self.volume_input.setPlaceholderText("例如：0.024（可选，留空自动计算）")
        self.volume_input.setValidator(QDoubleValidator(1e-6, 1000, 6))

        condition_layout.addWidget(QLabel("温度:"), 0, 0)
        condition_layout.addWidget(self.temperature_input, 0, 1)
        condition_layout.addWidget(QLabel("K"), 0, 2)
        condition_layout.addWidget(QLabel("压力:"), 0, 3)
        condition_layout.addWidget(self.pressure_input, 0, 4)
        condition_layout.addWidget(QLabel("kPa"), 0, 5)
        condition_layout.addWidget(QLabel("摩尔体积:"), 1, 0)
        condition_layout.addWidget(self.volume_input, 1, 1)
        condition_layout.addWidget(QLabel("m³/mol"), 1, 2)

        substance_layout.addWidget(condition_group)
        substance_layout.addStretch()

        # ---- 结果标签页 ----
        result_tab = QWidget()
        result_layout = QVBoxLayout(result_tab)

        button_layout = QHBoxLayout()
        self.calc_btn = QPushButton("计算")
        self.calc_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; padding: 8px; border-radius: 4px; }"
                                  "QPushButton:hover { background-color: #2980b9; }")
        self.calc_btn.clicked.connect(self.calculate)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; padding: 8px; border-radius: 4px; }"
                                   "QPushButton:hover { background-color: #7f8c8d; }")
        self.clear_btn.clicked.connect(self.clear_inputs)
        button_layout.addWidget(self.calc_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        result_layout.addLayout(button_layout)

        # 基本热力学性质
        basic_group = QGroupBox("基本热力学性质")
        basic_layout = QGridLayout(basic_group)
        self.z_factor_result = QLabel("--")
        self.density_result = QLabel("--")
        self.molar_volume_result = QLabel("--")
        self.fugacity_coeff_result = QLabel("--")
        self.fugacity_result = QLabel("--")

        basic_layout.addWidget(QLabel("压缩因子 Z:"), 0, 0)
        basic_layout.addWidget(self.z_factor_result, 0, 1)
        basic_layout.addWidget(QLabel(""), 0, 2)
        basic_layout.addWidget(QLabel("密度:"), 0, 3)
        basic_layout.addWidget(self.density_result, 0, 4)
        basic_layout.addWidget(QLabel("kg/m³"), 0, 5)
        basic_layout.addWidget(QLabel("摩尔体积:"), 1, 0)
        basic_layout.addWidget(self.molar_volume_result, 1, 1)
        basic_layout.addWidget(QLabel("m³/mol"), 1, 2)
        basic_layout.addWidget(QLabel("逸度系数 φ:"), 1, 3)
        basic_layout.addWidget(self.fugacity_coeff_result, 1, 4)
        basic_layout.addWidget(QLabel(""), 1, 5)
        basic_layout.addWidget(QLabel("逸度 f:"), 2, 0)
        basic_layout.addWidget(self.fugacity_result, 2, 1)
        basic_layout.addWidget(QLabel("kPa"), 2, 2)
        result_layout.addWidget(basic_group)

        # 剩余性质
        residual_group = QGroupBox("剩余性质（真实 - 理想）")
        residual_layout = QGridLayout(residual_group)
        self.residual_enthalpy_result = QLabel("--")
        self.residual_entropy_result = QLabel("--")
        self.residual_gibbs_result = QLabel("--")

        residual_layout.addWidget(QLabel("剩余焓 H^R:"), 0, 0)
        residual_layout.addWidget(self.residual_enthalpy_result, 0, 1)
        residual_layout.addWidget(QLabel("J/mol"), 0, 2)
        residual_layout.addWidget(QLabel("剩余熵 S^R:"), 0, 3)
        residual_layout.addWidget(self.residual_entropy_result, 0, 4)
        residual_layout.addWidget(QLabel("J/(mol·K)"), 0, 5)
        residual_layout.addWidget(QLabel("剩余Gibbs G^R:"), 1, 0)
        residual_layout.addWidget(self.residual_gibbs_result, 1, 1)
        residual_layout.addWidget(QLabel("J/mol"), 1, 2)
        result_layout.addWidget(residual_group)

        # 对比状态参数
        reduced_group = QGroupBox("对比状态参数")
        reduced_layout = QGridLayout(reduced_group)
        self.reduced_temp_result = QLabel("--")
        self.reduced_pressure_result = QLabel("--")
        self.reduced_volume_result = QLabel("--")
        self.acentric_factor_result = QLabel("--")

        reduced_layout.addWidget(QLabel("对比温度 Tr:"), 0, 0)
        reduced_layout.addWidget(self.reduced_temp_result, 0, 1)
        reduced_layout.addWidget(QLabel(""), 0, 2)
        reduced_layout.addWidget(QLabel("对比压力 Pr:"), 0, 3)
        reduced_layout.addWidget(self.reduced_pressure_result, 0, 4)
        reduced_layout.addWidget(QLabel(""), 0, 5)
        reduced_layout.addWidget(QLabel("对比体积 Vr:"), 1, 0)
        reduced_layout.addWidget(self.reduced_volume_result, 1, 1)
        reduced_layout.addWidget(QLabel(""), 1, 2)
        reduced_layout.addWidget(QLabel("偏心因子 ω:"), 1, 3)
        reduced_layout.addWidget(self.acentric_factor_result, 1, 4)
        reduced_layout.addWidget(QLabel(""), 1, 5)
        result_layout.addWidget(reduced_group)

        # 状态方程参数
        eos_params_group = QGroupBox("状态方程参数")
        eos_params_layout = QGridLayout(eos_params_group)
        self.a_parameter_result = QLabel("--")
        self.b_parameter_result = QLabel("--")
        self.alpha_parameter_result = QLabel("--")

        eos_params_layout.addWidget(QLabel("a 参数:"), 0, 0)
        eos_params_layout.addWidget(self.a_parameter_result, 0, 1)
        eos_params_layout.addWidget(QLabel(""), 0, 2)
        eos_params_layout.addWidget(QLabel("b 参数:"), 0, 3)
        eos_params_layout.addWidget(self.b_parameter_result, 0, 4)
        eos_params_layout.addWidget(QLabel(""), 0, 5)
        eos_params_layout.addWidget(QLabel("α(T) 参数:"), 1, 0)
        eos_params_layout.addWidget(self.alpha_parameter_result, 1, 1)
        eos_params_layout.addWidget(QLabel(""), 1, 2)
        result_layout.addWidget(eos_params_group)

        # 标签页
        self.tab_widget.addTab(substance_tab, "物质参数")
        self.tab_widget.addTab(result_tab, "计算结果")

        scroll_layout.addWidget(self.tab_widget)

        # 说明文本
        info_text = QTextEdit()
        info_text.setMaximumHeight(200)
        info_text.setHtml("""
        <h4>状态方程说明:</h4>
        <ul>
        <li><b>理想气体方程</b>: PV = RT，适用于低压高温条件</li>
        <li><b>范德瓦尔斯方程</b>: P = RT/(V-b) - a/V²，考虑分子体积和分子间作用力</li>
        <li><b>Redlich-Kwong方程</b>: P = RT/(V-b) - a/(√T·V(V+b))，改进温度依赖关系</li>
        <li><b>Soave-Redlich-Kwong方程</b>: P = RT/(V-b) - aα(T)/(V(V+b))，引入偏心因子改进精度</li>
        <li><b>Peng-Robinson方程</b>: P = RT/(V-b) - aα(T)/(V²+2bV-b²)，在临界区有更好表现</li>
        </ul>
        <p><b>剩余性质</b> H^R = H - H^ig，S^R = S - S^ig，基于各方程的解析公式精确计算</p>
        <p><b>逸度系数</b> φ = f/P，用于相平衡计算，各方程均有解析解</p>
        """)
        info_text.setReadOnly(True)
        scroll_layout.addWidget(info_text)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        self.update_substance_parameters()

    # ------------------------------------------------------------------
    #  物质参数
    # ------------------------------------------------------------------

    def update_substance_parameters(self):
        substance = self.substance_selection.currentText()
        if substance == "自定义":
            for w in (self.tc_input, self.pc_input, self.omega_input, self.mw_input, self.zc_input):
                w.clear()
        else:
            params = SUBSTANCE_DATABASE.get(substance, {})
            self.tc_input.setText(f"{params.get('tc', 0)}")
            self.pc_input.setText(f"{params.get('pc', 0)}")
            self.omega_input.setText(f"{params.get('omega', 0)}")
            self.mw_input.setText(f"{params.get('mw', 0)}")
            self.zc_input.setText(f"{params.get('zc', 0.27)}")

    # ------------------------------------------------------------------
    #  状态方程参数计算
    # ------------------------------------------------------------------

    @staticmethod
    def _eos_params(eos_type, tc, pc, omega, T, Tr):
        """
        返回 dict: {a, b, alpha} 或 {}（理想气体）
        a, b 单位与 R=8.314 J/(mol·K), P 单位 kPa, V 单位 m³/mol 一致。
        """
        R = 8.314
        if eos_type == "理想气体方程":
            return {}

        Pc_Pa = pc * 1000  # kPa -> Pa 以匹配 R 单位

        if eos_type == "范德瓦尔斯方程":
            a = 27 * (R * tc) ** 2 / (64 * Pc_Pa)
            b = R * tc / (8 * Pc_Pa)
            return {'a': a, 'b': b, 'alpha': 1.0}

        elif eos_type == "Redlich-Kwong方程":
            a0 = 0.42748 * (R * tc) ** 2 / Pc_Pa
            b = 0.08664 * R * tc / Pc_Pa
            # RK 的 a 含 √T 项，将 alpha = 1/√(T·Tc) 合入
            alpha = (tc / T) ** 0.5
            a = a0 * alpha
            return {'a': a, 'b': b, 'alpha': alpha}

        elif eos_type == "Soave-Redlich-Kwong方程":
            a0 = 0.42748 * (R * tc) ** 2 / Pc_Pa
            b = 0.08664 * R * tc / Pc_Pa
            m = 0.480 + 1.574 * omega - 0.176 * omega ** 2
            alpha = (1 + m * (1 - Tr ** 0.5)) ** 2
            a = a0 * alpha
            return {'a': a, 'b': b, 'alpha': alpha}

        elif eos_type == "Peng-Robinson方程":
            a0 = 0.45724 * (R * tc) ** 2 / Pc_Pa
            b = 0.07780 * R * tc / Pc_Pa
            kappa = 0.37464 + 1.54226 * omega - 0.26992 * omega ** 2
            alpha = (1 + kappa * (1 - Tr ** 0.5)) ** 2
            a = a0 * alpha
            return {'a': a, 'b': b, 'alpha': alpha}

        return {}

    # ------------------------------------------------------------------
    #  求解压缩因子 Z
    # ------------------------------------------------------------------

    @staticmethod
    def _solve_Z(eos_type, params, Tr, Pr):
        """
        将立方 EOS 转为 Z 的多项式，用纯 Python 求解。
        返回气相根（最大的正实根）。
        """
        R = 8.314

        if not params:
            return 1.0

        a = params['a']
        b = params['b']

        # 无量纲参数（注意单位一致性：P kPa → Pa）
        A = a * (Pr * 1000) / (R * Tr) ** 2
        B = b * (Pr * 1000) / (R * Tr)

        if eos_type == "范德瓦尔斯方程":
            # Z³ - (1+B)Z² + AZ - AB = 0
            coeffs = (1.0, -(1 + B), A, -A * B)
        elif eos_type == "Redlich-Kwong方程":
            # Z³ - Z² + (A-B-B²)Z - AB = 0
            coeffs = (1.0, -1.0, A - B - B * B, -A * B)
        elif eos_type == "Soave-Redlich-Kwong方程":
            # Z³ - Z² + (A-B-B²)Z - AB = 0 (同 RK 形式)
            coeffs = (1.0, -1.0, A - B - B * B, -A * B)
        elif eos_type == "Peng-Robinson方程":
            # Z³ - (1-B)Z² + (A-2B-3B²)Z - (AB-B²-B³) = 0
            coeffs = (1.0, -(1 - B), A - 2 * B - 3 * B * B, -(A * B - B * B - B ** 3))
        else:
            return 1.0

        roots = _solve_cubic(*coeffs)
        if not roots:
            return 1.0
        # 返回最大正实根（气相）
        return max(roots)

    # ------------------------------------------------------------------
    #  逸度系数
    # ------------------------------------------------------------------

    @staticmethod
    def _fugacity_coeff(eos_type, params, Z, Tr, Pr):
        """解析逸度系数 ln φ"""
        R = 8.314

        if not params or Z <= 0:
            return 1.0

        a = params['a']
        b = params['b']
        A = a * (Pr * 1000) / (R * Tr) ** 2
        B = b * (Pr * 1000) / (R * Tr)

        if eos_type == "范德瓦尔斯方程":
            ln_phi = Z - 1.0 - math.log(Z - B) - A / Z
            return math.exp(ln_phi)

        elif eos_type in ("Redlich-Kwong方程", "Soave-Redlich-Kwong方程"):
            ln_phi = Z - 1.0 - math.log(Z - B) - (A / B) * math.log(1.0 + B / Z)
            return math.exp(ln_phi)

        elif eos_type == "Peng-Robinson方程":
            sqrt2 = math.sqrt(2.0)
            ln_phi = (Z - 1.0 - math.log(Z - B)
                      - (A / (2.0 * sqrt2 * B)) * math.log((Z + (1 + sqrt2) * B) / (Z + (1 - sqrt2) * B)))
            return math.exp(ln_phi)

        return 1.0

    # ------------------------------------------------------------------
    #  剩余性质（解析公式）
    # ------------------------------------------------------------------

    @staticmethod
    def _residual_properties(eos_type, params, Z, Tr, Pr, T, tc, omega):
        """
        返回 (H^R, S^R) J/mol, J/(mol·K)
        基于 Smith, Van Ness, Abbott — Introduction to Chemical Engineering Thermodynamics
        """
        R = 8.314

        if not params:
            return 0.0, 0.0

        a = params['a']
        b = params['b']
        A = a * (Pr * 1000) / (R * Tr) ** 2
        B = b * (Pr * 1000) / (R * Tr)

        if eos_type == "范德瓦尔斯方程":
            H_R = R * T * (Z - 1.0) - a * Z  # d(ln α)/d(1/T) = -a, 其中 α ∝ T^0
            S_R = R * (math.log(Z - B) - B / (Z - B))
            # 修正 vdW: H^R = R*T*(Z-1) - a/V = R*T*(Z-1) - a*P/(Z*R*T)
            # 但按标准推导: H^R/RT = Z-1 + T*(dα/dT)_V / RT, 对vdW α=a/V^2, T无关
            # H^R = RT*(Z-1) - a/V = RT*(Z-1) - a*P/(Z*R*T)
            H_R = R * T * (Z - 1.0) - a * (Pr * 1000) / (Z * R * T)
            S_R = R * (math.log(Z) + B / Z)  # ln φ + (Z-1) - ln(Z-B) 对vdW简化

        elif eos_type in ("Redlich-Kwong方程", "Soave-Redlich-Kwong方程"):
            # H^R/RT = Z - 1 - 3a/(2bRT)·ln(1+B/Z)·(1 + da/dT/a)
            # 对 SRK: da/dT = a0 * 2·α·(1+m)/√Tc · (-1/(2√T)) = -a·m/(T·√(Tr)·(1+...))
            if eos_type == "Soave-Redlich-Kwong方程":
                m_srk = 0.480 + 1.574 * omega - 0.176 * omega ** 2
                sqrt_Tr = math.sqrt(Tr) if Tr > 0 else 1.0
                da_over_a = -m_srk / (T * sqrt_Tr) if T > 0 else 0.0
            else:
                # RK: a ∝ 1/√T, so da/dT = -a/(2T), da/a = -1/(2T)
                da_over_a = -0.5 / T if T > 0 else 0.0

            H_R = R * T * (Z - 1.0 - (A / B) * math.log(1.0 + B / Z) * (1.0 + T * da_over_a))
            S_R = R * (math.log(Z - B) - (A / B) * math.log(1.0 + B / Z) + math.log(Z))

        elif eos_type == "Peng-Robinson方程":
            kappa = 0.37464 + 1.54226 * omega - 0.26992 * omega ** 2
            sqrt_Tr = math.sqrt(Tr) if Tr > 0 else 1.0
            # PR: a = a0·α, α = (1+κ(1-√Tr))²
            # dα/dT = 2·α·κ/(2·T·√Tr) = α·κ/(T·√Tr)  (注意符号)
            dalpha_over_alpha = kappa / (T * sqrt_Tr) if T > 0 else 0.0
            # da/dT = a0·dα/dT = a·dα/α
            da_over_a = dalpha_over_alpha

            sqrt2 = math.sqrt(2.0)
            H_R = R * T * (Z - 1.0
                           - (A / (2.0 * sqrt2 * B)) * (1.0 + T * da_over_a)
                           * math.log((Z + (1 + sqrt2) * B) / (Z + (1 - sqrt2) * B)))
            S_R = R * (math.log(Z - B)
                       - (A / (2.0 * sqrt2 * B)) * math.log((Z + (1 + sqrt2) * B) / (Z + (1 - sqrt2) * B))
                       + math.log(Z))
        else:
            H_R = 0.0
            S_R = 0.0

        G_R = H_R - T * S_R
        return H_R, S_R, G_R

    # ------------------------------------------------------------------
    #  公共计算入口
    # ------------------------------------------------------------------

    def calculate_eos_properties(self, eos_type, T, P, V, tc, pc, omega, mw, zc, Tr, Pr):
        R = 8.314

        params = self._eos_params(eos_type, tc, pc, omega, T, Tr)

        # 求解 Z 和 V
        if V is None:
            if eos_type == "理想气体方程":
                Z = 1.0
            else:
                Z = self._solve_Z(eos_type, params, Tr, Pr)
            V = Z * R * T / (P * 1000)  # m³/mol
        else:
            Z = P * 1000 * V / (R * T)

        density = mw / (V * 1000) if V and V > 0 else 0.0  # kg/m³

        phi = self._fugacity_coeff(eos_type, params, Z, Tr, Pr)
        fugacity = phi * P

        H_R, S_R, G_R = self._residual_properties(eos_type, params, Z, Tr, Pr, T, tc, omega)

        Vc = R * tc / (pc * 1000) if pc > 0 else 1.0
        Vr = V / Vc if V else 0.0

        return {
            'z_factor': Z,
            'density': density,
            'molar_volume': V,
            'fugacity_coeff': phi,
            'fugacity': fugacity,
            'residual_enthalpy': H_R,
            'residual_entropy': S_R,
            'residual_gibbs': G_R,
            'reduced_temp': Tr,
            'reduced_pressure': Pr,
            'reduced_volume': Vr,
            'acentric_factor': omega,
            'a_parameter': params.get('a', 0),
            'b_parameter': params.get('b', 0),
            'alpha_parameter': params.get('alpha', 0)
        }

    # ------------------------------------------------------------------
    #  UI 交互
    # ------------------------------------------------------------------

    def clear_inputs(self):
        for w in (self.tc_input, self.pc_input, self.omega_input,
                  self.mw_input, self.zc_input, self.temperature_input,
                  self.pressure_input, self.volume_input):
            w.clear()
        for lbl in (self.z_factor_result, self.density_result,
                    self.molar_volume_result, self.fugacity_coeff_result,
                    self.fugacity_result, self.residual_enthalpy_result,
                    self.residual_entropy_result, self.residual_gibbs_result,
                    self.reduced_temp_result, self.reduced_pressure_result,
                    self.reduced_volume_result, self.acentric_factor_result,
                    self.a_parameter_result, self.b_parameter_result,
                    self.alpha_parameter_result):
            lbl.setText("--")

    def calculate(self):
        try:
            tc = float(self.tc_input.text())
            pc = float(self.pc_input.text())
            omega = float(self.omega_input.text())
            mw = float(self.mw_input.text())
            zc = float(self.zc_input.text()) if self.zc_input.text() else 0.27

            T = float(self.temperature_input.text())
            P = float(self.pressure_input.text())
            V_input = self.volume_input.text()
            V = float(V_input) if V_input else None

            eos_type = self.eos_type.currentText()

            Tr = T / tc
            Pr = P / pc

            results = self.calculate_eos_properties(eos_type, T, P, V, tc, pc, omega, mw, zc, Tr, Pr)
            self.display_results(results)

        except ValueError:
            self.show_error("输入参数格式错误，请检查输入值")
        except Exception as e:
            self.show_error(f"计算错误: {str(e)}")

    def display_results(self, results):
        self.z_factor_result.setText(f"{results['z_factor']:.4f}")
        self.density_result.setText(f"{results['density']:.3f}")
        self.molar_volume_result.setText(f"{results['molar_volume']:.6f}")
        self.fugacity_coeff_result.setText(f"{results['fugacity_coeff']:.6f}")
        self.fugacity_result.setText(f"{results['fugacity']:.3f}")

        self.residual_enthalpy_result.setText(f"{results['residual_enthalpy']:.2f}")
        self.residual_entropy_result.setText(f"{results['residual_entropy']:.4f}")
        self.residual_gibbs_result.setText(f"{results['residual_gibbs']:.2f}")

        self.reduced_temp_result.setText(f"{results['reduced_temp']:.4f}")
        self.reduced_pressure_result.setText(f"{results['reduced_pressure']:.4f}")
        self.reduced_volume_result.setText(f"{results['reduced_volume']:.4f}")
        self.acentric_factor_result.setText(f"{results['acentric_factor']:.4f}")

        self.a_parameter_result.setText(f"{results['a_parameter']:.4f}")
        self.b_parameter_result.setText(f"{results['b_parameter']:.6f}")
        self.alpha_parameter_result.setText(f"{results['alpha_parameter']:.4f}")

    def show_error(self, message):
        QMessageBox.critical(self, "计算错误", message)
        for lbl in (self.z_factor_result, self.density_result,
                    self.molar_volume_result, self.fugacity_coeff_result,
                    self.fugacity_result, self.residual_enthalpy_result,
                    self.residual_entropy_result, self.residual_gibbs_result,
                    self.reduced_temp_result, self.reduced_pressure_result,
                    self.reduced_volume_result, self.acentric_factor_result,
                    self.a_parameter_result, self.b_parameter_result,
                    self.alpha_parameter_result):
            lbl.setText("计算错误")

    def _get_history_data(self):
        try:
            tc = float(self.tc_input.text() or 0)
            pc = float(self.pc_input.text() or 0)
            omega = float(self.omega_input.text() or 0)
            mw = float(self.mw_input.text() or 0)
            zc = float(self.zc_input.text() or 0.27) if self.zc_input.text() else 0.27
            T = float(self.temperature_input.text() or 0)
            P = float(self.pressure_input.text() or 0)
            V_input = self.volume_input.text()
            V = float(V_input) if V_input else None
            eos_type = self.eos_type.currentText()

            inputs = {
                "状态方程": eos_type,
                "临界温度_K": tc,
                "临界压力_kPa": pc,
                "偏心因子": omega,
                "分子量": mw,
                "温度_K": T,
                "压力_kPa": P,
                "体积_m3_mol": V
            }
            Tr = T / tc if tc > 0 else 0
            Pr = P / pc if pc > 0 else 0
            results = self.calculate_eos_properties(eos_type, T, P, V, tc, pc, omega, mw, zc, Tr, Pr)
            outputs = {
                "对比温度": round(Tr, 4),
                "对比压力": round(Pr, 4),
                "压缩因子Z": round(results.get('z_factor', 0), 4),
                "逸度系数": round(results.get('fugacity_coeff', 0), 6),
                "剩余焓_J_mol": round(results.get('residual_enthalpy', 0), 2),
                "密度_kg_m3": round(results.get('density', 0), 4)
            }
        except Exception as e:
            inputs = {}
            outputs = {"计算错误": str(e)}
        return {"inputs": inputs, "outputs": outputs}


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    calculator = EOSCalculator()
    calculator.resize(900, 800)
    calculator.show()
    sys.exit(app.exec())
