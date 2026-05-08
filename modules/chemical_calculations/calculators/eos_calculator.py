import math, os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QGridLayout, QFileDialog, QMessageBox,
    QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator


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
    p = b / a
    q = c / a
    r = d / a
    A = q - p * p / 3.0
    B = r - p * q / 3.0 + 2.0 * p * p * p / 27.0
    disc = -(4 * A * A * A + 27 * B * B)
    if disc > 1e-10:
        m = 2.0 * math.sqrt(-A / 3.0)
        theta = math.acos(max(-1.0, min(1.0, -B / (m * m * m / 2.0)))) / 3.0
        roots = []
        for k in range(3):
            t = m * math.cos(theta + 2 * math.pi * k / 3.0)
            roots.append(t - p / 3.0)
        return sorted(roots, reverse=True)
    elif abs(disc) < 1e-10:
        t1 = 3.0 * B / A if abs(A) > 1e-30 else 0.0
        x1 = t1 - p / 3.0
        x2 = -t1 / 2.0 - p / 3.0
        if abs(x1 - x2) > 1e-10:
            return sorted([x1, x2, x2], reverse=True)
        return [x1]
    else:
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
#  EOS 计算器主类（统一 UI 规范版）
# ---------------------------------------------------------------------------

class EOSCalculator(QWidget):
    """状态方程计算器 — 支持 vdW / RK / SRK / PR 立方型 EOS"""
    calculation_type = "eos_calculator"

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager if data_manager is not None else None
        self._last_result = {}
        self._last_params = {}
        self.setup_ui()

    def setup_ui(self):
        group_style = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bdc3c7;
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
        main = QHBoxLayout(self)
        main.setSpacing(15)
        main.setContentsMargins(10, 10, 10, 10)

        # =========== 左侧输入区 ===========
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left = QWidget()
        left.setStyleSheet("QWidget { background: transparent; }")
        ll = QVBoxLayout(left)
        ll.setSpacing(15)

        desc = QLabel(
            "使用立方型状态方程计算流体热力学性质。\n"
            "支持 van der Waals、Redlich-Kwong、Soave-Redlich-Kwong、Peng-Robinson 方程。\n"
            "可计算压缩因子、逸度系数、剩余焓/熵/Gibbs自由能等。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        ll.addWidget(desc)

        def L(t):
            l = QLabel(t)
            l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            l.setMinimumWidth(120)
            l.setMaximumWidth(200)
            l.setStyleSheet("font-weight: bold; padding-right: 10px;")
            return l

        def H(t):
            l = QLabel(t)
            l.setMinimumWidth(100)
            l.setMaximumWidth(250)
            l.setStyleSheet("color: #95a5a6; font-size: 11px;")
            return l

        # ---- 物质参数 ----
        sg = QGroupBox("物质参数"); sg.setStyleSheet(group_style)
        sgrid = QGridLayout(sg)
        sgrid.setHorizontalSpacing(10)
        sgrid.setVerticalSpacing(10)
        sgrid.setColumnStretch(0, 2)  # 标签列可伸缩

        sgrid.setColumnStretch(1, 3)  # 输入框列可伸缩

        sgrid.setColumnStretch(2, 2)  # 提示列可伸缩


        self.substance_combo = QComboBox()
        self.substance_combo.addItems(["自定义"] + list(SUBSTANCE_DATABASE.keys()))
        self.substance_combo.setMinimumWidth(150)
        self.substance_combo.setMaximumWidth(400)
        self.substance_combo.currentTextChanged.connect(self._on_substance)
        sgrid.addWidget(L("物质选择:"), 0, 0)
        sgrid.addWidget(self.substance_combo, 0, 1)
        sgrid.addWidget(H("选择后自动填充物性参数"), 0, 2)

        self.tc_input = QLineEdit()
        self.tc_input.setPlaceholderText("临界温度")
        self.tc_input.setMinimumWidth(150)
        self.tc_input.setMaximumWidth(400)
        self.tc_input.setValidator(QDoubleValidator(1, 2000, 2))
        sgrid.addWidget(L("临界温度 Tc (K):"), 1, 0)
        sgrid.addWidget(self.tc_input, 1, 1)
        sgrid.addWidget(H("甲烷=190.56"), 1, 2)

        self.pc_input = QLineEdit()
        self.pc_input.setPlaceholderText("临界压力")
        self.pc_input.setMinimumWidth(150)
        self.pc_input.setMaximumWidth(400)
        self.pc_input.setValidator(QDoubleValidator(100, 100000, 1))
        sgrid.addWidget(L("临界压力 Pc (kPa):"), 2, 0)
        sgrid.addWidget(self.pc_input, 2, 1)
        sgrid.addWidget(H("甲烷=4599"), 2, 2)

        self.omega_input = QLineEdit()
        self.omega_input.setPlaceholderText("偏心因子")
        self.omega_input.setMinimumWidth(150)
        self.omega_input.setMaximumWidth(400)
        self.omega_input.setValidator(QDoubleValidator(-1, 2, 4))
        sgrid.addWidget(L("偏心因子 w:"), 3, 0)
        sgrid.addWidget(self.omega_input, 3, 1)
        sgrid.addWidget(H("甲烷=0.0115"), 3, 2)

        self.mw_input = QLineEdit()
        self.mw_input.setPlaceholderText("分子量")
        self.mw_input.setMinimumWidth(150)
        self.mw_input.setMaximumWidth(400)
        self.mw_input.setValidator(QDoubleValidator(1, 500, 3))
        sgrid.addWidget(L("分子量 M (g/mol):"), 4, 0)
        sgrid.addWidget(self.mw_input, 4, 1)
        sgrid.addWidget(H("甲烷=16.04"), 4, 2)

        self.zc_input = QLineEdit("0.27")
        self.zc_input.setPlaceholderText("临界压缩因子")
        self.zc_input.setMinimumWidth(150)
        self.zc_input.setMaximumWidth(400)
        self.zc_input.setValidator(QDoubleValidator(0.1, 0.5, 3))
        sgrid.addWidget(L("临界压缩因子 Zc:"), 5, 0)
        sgrid.addWidget(self.zc_input, 5, 1)
        sgrid.addWidget(H("一般取0.27"), 5, 2)

        ll.addWidget(sg)

        # ---- 状态方程选择 ----
        eg = QGroupBox("状态方程选择"); eg.setStyleSheet(group_style)
        egrid = QGridLayout(eg)
        egrid.setHorizontalSpacing(10)
        egrid.setVerticalSpacing(10)

        self.eos_type = QComboBox()
        self.eos_type.addItems([
            "理想气体方程",
            "范德瓦尔斯方程",
            "Redlich-Kwong方程",
            "Soave-Redlich-Kwong方程",
            "Peng-Robinson方程"
        ])
        self.eos_type.setMinimumWidth(150)
        self.eos_type.setMaximumWidth(400)
        egrid.addWidget(L("状态方程:"), 0, 0)
        egrid.addWidget(self.eos_type, 0, 1)
        egrid.addWidget(H("推荐SRK或PR"), 0, 2)

        self.calc_type_combo = QComboBox()
        self.calc_type_combo.addItems([
            "P-V-T关系计算",
            "压缩因子计算",
            "逸度系数计算",
            "剩余性质计算"
        ])
        self.calc_type_combo.setMinimumWidth(150)
        self.calc_type_combo.setMaximumWidth(400)
        egrid.addWidget(L("计算类型:"), 1, 0)
        egrid.addWidget(self.calc_type_combo, 1, 1)
        egrid.addWidget(H("默认综合计算全部性质"), 1, 2)

        ll.addWidget(eg)

        # ---- 计算条件 ----
        cg = QGroupBox("计算条件"); cg.setStyleSheet(group_style)
        cgrid = QGridLayout(cg)
        cgrid.setHorizontalSpacing(10)
        cgrid.setVerticalSpacing(10)

        self.temperature_input = QLineEdit()
        self.temperature_input.setPlaceholderText("温度")
        self.temperature_input.setMinimumWidth(150)
        self.temperature_input.setMaximumWidth(400)
        self.temperature_input.setValidator(QDoubleValidator(1, 2000, 2))
        cgrid.addWidget(L("温度 T (K):"), 0, 0)
        cgrid.addWidget(self.temperature_input, 0, 1)
        cgrid.addWidget(H("例如298.15"), 0, 2)

        self.pressure_input = QLineEdit()
        self.pressure_input.setPlaceholderText("压力")
        self.pressure_input.setMinimumWidth(150)
        self.pressure_input.setMaximumWidth(400)
        self.pressure_input.setValidator(QDoubleValidator(0.1, 100000, 2))
        cgrid.addWidget(L("压力 P (kPa):"), 1, 0)
        cgrid.addWidget(self.pressure_input, 1, 1)
        cgrid.addWidget(H("例如101.325"), 1, 2)

        self.volume_input = QLineEdit()
        self.volume_input.setPlaceholderText("可选，留空自动计算")
        self.volume_input.setMinimumWidth(150)
        self.volume_input.setMaximumWidth(400)
        self.volume_input.setValidator(QDoubleValidator(1e-6, 1000, 6))
        cgrid.addWidget(L("摩尔体积 V (m³/mol):"), 2, 0)
        cgrid.addWidget(self.volume_input, 2, 1)
        cgrid.addWidget(H("留空则由EOS求解"), 2, 2)

        ll.addWidget(cg)

        # ---- 方程说明（折叠在左侧底部） ----
        info_group = QGroupBox("状态方程说明"); info_group.setStyleSheet(group_style)
        info_layout = QVBoxLayout(info_group)
        info_text = QLabel(
            "理想气体: PV=RT，适用于低压高温\n"
            "范德瓦尔斯: P=RT/(V-b)-a/V²，最早立方EOS\n"
            "RK: P=RT/(V-b)-a/(√T·V(V+b))，改进温度依赖\n"
            "SRK: P=RT/(V-b)-aα(T)/(V(V+b))，引入偏心因子\n"
            "PR: P=RT/(V-b)-aα(T)/(V²+2bV-b²)，临界区更准确"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        info_layout.addWidget(info_text)
        ll.addWidget(info_group)

        # ---- 计算按钮 ----
        bb = QHBoxLayout()
        b_calc = QPushButton("  计  算  ")
        b_calc.setStyleSheet(
            "QPushButton{background-color:#3498db;color:white;font-weight:bold;"
            "font-size:14px;border-radius:8px;min-height:50px;}"
            "QPushButton:hover{background-color:#2980b9;}"
        )
        b_calc.clicked.connect(self.calculate)
        bb.addWidget(b_calc)
        ll.addLayout(bb)

        # ---- 底部按钮行 ----
        br = QHBoxLayout()
        b_clr = QPushButton("清空")
        b_clr.setStyleSheet(
            "QPushButton{background-color:#95a5a6;color:white;font-weight:bold;"
            "border-radius:6px;padding:8px 20px;}"
            "QPushButton:hover{background-color:#7f8c8d;}"
        )
        b_clr.clicked.connect(self.clear_inputs)
        b_txt = QPushButton("下载TXT报告")
        b_txt.setStyleSheet(
            "QPushButton{background-color:#27ae60;color:white;font-weight:bold;"
            "border-radius:6px;padding:8px 20px;}"
            "QPushButton:hover{background-color:#219a52;}"
        )
        b_txt.clicked.connect(self.download_txt_report)
        b_pdf = QPushButton("下载PDF报告")
        b_pdf.setStyleSheet(
            "QPushButton{background-color:#e74c3c;color:white;font-weight:bold;"
            "border-radius:6px;padding:8px 20px;}"
            "QPushButton:hover{background-color:#c0392b;}"
        )
        b_pdf.clicked.connect(self.generate_pdf_report)
        br.addWidget(b_clr)
        br.addStretch()
        br.addWidget(b_txt)
        br.addWidget(b_pdf)
        ll.addLayout(br)

        # =========== 右侧结果区 ===========
        right = QWidget()
        right.setMinimumWidth(400)
        rl = QVBoxLayout(right)
        rl.setSpacing(10)
        rg = QGroupBox("计算结果")
        rg.setStyleSheet(group_style)
        rv = QVBoxLayout(rg)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setStyleSheet(
            "QTextEdit{background-color:#f8f9fa;border:1px solid #dee2e6;"
            "border-radius:6px;font-family:Consolas,monospace;font-size:13px;padding:10px;}"
        )
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        rv.addWidget(self.result_text)
        rl.addWidget(rg)

        scroll_left.setWidget(left)
        main.addWidget(scroll_left, 2)
        main.addWidget(right, 1)

        # 默认选中甲烷
        self.substance_combo.setCurrentText("甲烷")

    # ------------------------------------------------------------------
    #  物质参数联动
    # ------------------------------------------------------------------

    def _on_substance(self, name):
        if name == "自定义":
            for w in (self.tc_input, self.pc_input, self.omega_input,
                      self.mw_input, self.zc_input):
                w.clear()
        else:
            p = SUBSTANCE_DATABASE.get(name, {})
            self.tc_input.setText(str(p.get("tc", "")))
            self.pc_input.setText(str(p.get("pc", "")))
            self.omega_input.setText(str(p.get("omega", "")))
            self.mw_input.setText(str(p.get("mw", "")))
            self.zc_input.setText(str(p.get("zc", "0.27")))

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

        Pc_Pa = pc * 1000  # kPa -> Pa

        if eos_type == "范德瓦尔斯方程":
            a = 27 * (R * tc) ** 2 / (64 * Pc_Pa)
            b = R * tc / (8 * Pc_Pa)
            return {'a': a, 'b': b, 'alpha': 1.0}

        elif eos_type == "Redlich-Kwong方程":
            a0 = 0.42748 * (R * tc) ** 2 / Pc_Pa
            b = 0.08664 * R * tc / Pc_Pa
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
        """将立方 EOS 转为 Z 的多项式，返回气相根（最大的正实根）。"""
        R = 8.314
        if not params:
            return 1.0

        a = params['a']
        b = params['b']
        A = a * (Pr * 1000) / (R * Tr) ** 2
        B = b * (Pr * 1000) / (R * Tr)

        if eos_type == "范德瓦尔斯方程":
            coeffs = (1.0, -(1 + B), A, -A * B)
        elif eos_type == "Redlich-Kwong方程":
            coeffs = (1.0, -1.0, A - B - B * B, -A * B)
        elif eos_type == "Soave-Redlich-Kwong方程":
            coeffs = (1.0, -1.0, A - B - B * B, -A * B)
        elif eos_type == "Peng-Robinson方程":
            coeffs = (1.0, -(1 - B), A - 2 * B - 3 * B * B, -(A * B - B * B - B ** 3))
        else:
            return 1.0

        roots = _solve_cubic(*coeffs)
        if not roots:
            return 1.0
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
        返回 (H^R, S^R, G^R) J/mol, J/(mol·K), J/mol
        """
        R = 8.314
        if not params:
            return 0.0, 0.0, 0.0

        a = params['a']
        b = params['b']
        A = a * (Pr * 1000) / (R * Tr) ** 2
        B = b * (Pr * 1000) / (R * Tr)

        if eos_type == "范德瓦尔斯方程":
            H_R = R * T * (Z - 1.0) - a * (Pr * 1000) / (Z * R * T)
            S_R = R * (math.log(Z) + B / Z)

        elif eos_type in ("Redlich-Kwong方程", "Soave-Redlich-Kwong方程"):
            if eos_type == "Soave-Redlich-Kwong方程":
                m_srk = 0.480 + 1.574 * omega - 0.176 * omega ** 2
                sqrt_Tr = math.sqrt(Tr) if Tr > 0 else 1.0
                da_over_a = -m_srk / (T * sqrt_Tr) if T > 0 else 0.0
            else:
                da_over_a = -0.5 / T if T > 0 else 0.0

            H_R = R * T * (Z - 1.0 - (A / B) * math.log(1.0 + B / Z) * (1.0 + T * da_over_a))
            S_R = R * (math.log(Z - B) - (A / B) * math.log(1.0 + B / Z) + math.log(Z))

        elif eos_type == "Peng-Robinson方程":
            kappa = 0.37464 + 1.54226 * omega - 0.26992 * omega ** 2
            sqrt_Tr = math.sqrt(Tr) if Tr > 0 else 1.0
            dalpha_over_alpha = kappa / (T * sqrt_Tr) if T > 0 else 0.0
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
            V = Z * R * T / (P * 1000)
        else:
            Z = P * 1000 * V / (R * T)

        density = mw / (V * 1000) if V and V > 0 else 0.0

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
    #  清空
    # ------------------------------------------------------------------

    def clear_inputs(self):
        self.substance_combo.setCurrentText("甲烷")
        self.eos_type.setCurrentIndex(0)
        self.calc_type_combo.setCurrentIndex(0)
        self.temperature_input.clear()
        self.pressure_input.clear()
        self.volume_input.clear()
        self.result_text.clear()
        self._last_result = {}
        self._last_params = {}

    # ------------------------------------------------------------------
    #  计算
    # ------------------------------------------------------------------

    def calculate(self):
        try:
            tc = float(self.tc_input.text())
            pc = float(self.pc_input.text())
            omega = float(self.omega_input.text())
            mw = float(self.mw_input.text())
            zc = float(self.zc_input.text()) if self.zc_input.text() else 0.27

            T = float(self.temperature_input.text())
            P = float(self.pressure_input.text())
            V_text = self.volume_input.text().strip()
            V = float(V_text) if V_text else None

            eos_type = self.eos_type.currentText()
            calc_type = self.calc_type_combo.currentText()

            Tr = T / tc
            Pr = P / pc

            if T <= 0:
                raise ValueError("温度必须大于0")
            if P <= 0:
                raise ValueError("压力必须大于0")

            results = self.calculate_eos_properties(eos_type, T, P, V, tc, pc, omega, mw, zc, Tr, Pr)

            self._last_result = results
            self._last_params = {
                "eos_type": eos_type,
                "calc_type": calc_type,
                "substance": self.substance_combo.currentText(),
                "T": T, "P": P, "V": V,
                "tc": tc, "pc": pc, "omega": omega, "mw": mw, "zc": zc,
                "Tr": Tr, "Pr": Pr
            }

            self._display(results, eos_type, calc_type, T, P)

            # 保存历史
            if self.data_manager:
                try:
                    self.data_manager.add_record("eos_calculator", self._get_history_data())
                except Exception:
                    pass

        except ValueError as e:
            self.result_text.setPlainText(f"输入错误：{e}")
        except Exception as e:
            self.result_text.setPlainText(f"计算错误：{e}")

    def _display(self, r, eos_type, calc_type, T, P):
        """将计算结果格式化输出到右侧 QTextEdit"""
        lines = [
            "=" * 50,
            "        状态方程计算结果",
            "=" * 50, "",
            f"  状态方程   : {eos_type}",
            f"  计算类型   : {calc_type}",
            f"  物质       : {self._last_params.get('substance', '自定义')}",
            "",
            "-" * 50,
            "  基本热力学性质",
            "-" * 50,
            f"  对比温度 Tr     : {r['reduced_temp']:.4f}",
            f"  对比压力 Pr     : {r['reduced_pressure']:.4f}",
            f"  对比体积 Vr     : {r['reduced_volume']:.4f}",
            f"  偏心因子 w      : {r['acentric_factor']:.4f}",
            "",
            f"  压缩因子 Z      : {r['z_factor']:.6f}",
            f"  摩尔体积 V      : {r['molar_volume']:.6e} m³/mol",
            f"  密度 rho        : {r['density']:.4f} kg/m³",
            "",
            f"  逸度系数 phi    : {r['fugacity_coeff']:.6f}",
            f"  逸度 f          : {r['fugacity']:.4f} kPa",
            "",
            "-" * 50,
            "  剩余性质（真实 - 理想）",
            "-" * 50,
            f"  剩余焓 H^R      : {r['residual_enthalpy']:.2f} J/mol",
            f"  剩余熵 S^R      : {r['residual_entropy']:.4f} J/(mol·K)",
            f"  剩余Gibbs G^R   : {r['residual_gibbs']:.2f} J/mol",
            "",
            "-" * 50,
            "  状态方程参数",
            "-" * 50,
            f"  a 参数          : {r['a_parameter']:.6e}",
            f"  b 参数          : {r['b_parameter']:.6e}",
            f"  alpha(T)        : {r['alpha_parameter']:.6f}",
        ]

        # 工程建议
        lines += ["", "-" * 50, "  工程建议", "-" * 50]
        Tr = r['reduced_temp']
        Pr = r['reduced_pressure']
        Z = r['z_factor']

        if Pr < 0.1 and Tr > 2.0:
            lines.append("  理想气体假设成立，偏差 < 1%")
        elif abs(Z - 1.0) < 0.02:
            lines.append("  偏离理想气体较小（Z ≈ 1），可用理想气体近似")
        elif abs(Z - 1.0) < 0.1:
            lines.append("  中等偏离理想气体，建议使用立方 EOS 计算")
        else:
            lines.append("  显著偏离理想气体，必须使用真实气体 EOS")

        if Tr > 1.0 and Pr > 1.0:
            lines.append("  超临界状态，PR 方程通常比 SRK 更准确")
        elif Tr < 1.0 and Pr > 0.5:
            lines.append("  近临界区，注意 EOS 精度可能下降")

        if Z < 0.3:
            lines.append("  压缩因子较低，流体可能接近液相")

        lines += ["", "=" * 50]
        self.result_text.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------
    #  历史数据
    # ------------------------------------------------------------------

    def _get_history_data(self):
        p = self._last_params
        r = self._last_result
        return {
            "inputs": {
                "状态方程": p.get("eos_type", ""),
                "物质": p.get("substance", ""),
                "临界温度_K": p.get("tc", 0),
                "临界压力_kPa": p.get("pc", 0),
                "偏心因子": p.get("omega", 0),
                "分子量": p.get("mw", 0),
                "温度_K": p.get("T", 0),
                "压力_kPa": p.get("P", 0),
            },
            "outputs": {
                "对比温度": round(r.get("reduced_temp", 0), 4),
                "对比压力": round(r.get("reduced_pressure", 0), 4),
                "压缩因子Z": round(r.get("z_factor", 0), 6),
                "逸度系数": round(r.get("fugacity_coeff", 0), 6),
                "剩余焓_J_mol": round(r.get("residual_enthalpy", 0), 2),
                "剩余熵_J_mol_K": round(r.get("residual_entropy", 0), 4),
                "密度_kg_m3": round(r.get("density", 0), 4),
            }
        }

    # ------------------------------------------------------------------
    #  报告
    # ------------------------------------------------------------------

    def get_project_info(self):
        return {"calculator": "EOSCalculator", "name": "状态方程计算"}

    def generate_report(self):
        return self.result_text.toPlainText()

    def download_txt_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先计算，再下载报告。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存TXT报告", "状态方程计算报告.txt", "文本文件 (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "成功", f"报告已保存：\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败：{e}")

    def generate_pdf_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先计算，再下载PDF。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存PDF报告", "状态方程计算报告.pdf", "PDF文件 (*.pdf)")
        if not path:
            return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.enums import TA_LEFT
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            font_paths = ["C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simsun.ttc"]
            fname = "Helvetica"
            for fp in font_paths:
                if os.path.exists(fp):
                    try:
                        pdfmetrics.registerFont(TTFont("CF", fp))
                        fname = "CF"
                        break
                    except Exception:
                        continue
            doc = SimpleDocTemplate(path, pagesize=A4,
                                    leftMargin=20*mm, rightMargin=20*mm,
                                    topMargin=20*mm, bottomMargin=20*mm)
            styles = getSampleStyleSheet()
            st = ParagraphStyle("B", fontName=fname, fontSize=10, leading=16, alignment=TA_LEFT)
            story = []
            for line in content.split("\n"):
                safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(safe if safe.strip() else "&nbsp;", st))
                story.append(Spacer(1, 1))
            doc.build(story)
            QMessageBox.information(self, "成功", f"PDF已保存：\n{path}")
        except ImportError:
            QMessageBox.critical(self, "错误", "缺少reportlab，请运行：pip install reportlab")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"PDF生成失败：{e}")


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    calculator = EOSCalculator()
    calculator.resize(1200, 800)
    calculator.show()
    sys.exit(app.exec())
