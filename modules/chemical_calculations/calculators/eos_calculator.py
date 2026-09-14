import math, os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QGridLayout, QFileDialog, QMessageBox,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K, G, ATM_PRESSURE_MPA, WATER_DENSITY, WATER_CP, load_steam_iapws, get_steam_props
# DOCX 报告导出
from utils.docx_utils import ReportExporter

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
        # 标准三根公式: cos(3θ) = 3B/(2A)·√(-3/A)，等价于 -B/(m³/4)
        theta = math.acos(max(-1.0, min(1.0, -B / (m * m * m / 4.0)))) / 3.0
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
            return sorted([x1, x2], reverse=True)
        return [x1]
    else:
        # 单实根情况（disc<0），标准 Cardano 公式:
        # u = cbrt(-B/2 + √(B²/4 + A³/27)), v = cbrt(-B/2 - √(B²/4 + A³/27))
        # 根 = u + v - p/3
        half_B = B / 2.0
        sq = half_B * half_B + A * A * A / 27.0
        if sq < 0:
            sq = 0.0
        s = math.sqrt(sq)

        def _cbrt(x):
            return math.copysign(abs(x) ** (1.0 / 3.0), x)

        C = _cbrt(-half_B + s)
        D = _cbrt(-half_B - s)
        t = C + D
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
#  UI 样式常量
# ---------------------------------------------------------------------------


class EOSCalculator(CalculatorBase):
    """状态方程计算器 — 支持 vdW / RK / SRK / PR 立方型 EOS"""
    calculation_type = "eos_calculator"

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager if data_manager is not None else None
        self._last_result = {}
        self._last_params = {}
        self.setup_ui()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    def setup_ui(self):
        main = QHBoxLayout(self)
        main.setSpacing(15)
        main.setContentsMargins(10, 10, 10, 10)

        # ========== 左侧输入区 ==========
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }"
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left = QWidget()
        left.setStyleSheet("")
        ll = QVBoxLayout(left)
        ll.setSpacing(15)

        desc = QLabel(
            "使用立方型状态方程计算流体热力学性质。\n"
            "支持 van der Waals、Redlich-Kwong、Soave-Redlich-Kwong、Peng-Robinson 方程。\n"
            "可计算压缩因子、逸度系数、剩余焓/熵/Gibbs 自由能等。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px;")
        ll.addWidget(desc)

        # 标签工厂（不再设固定宽度）
        def L(t):
            l = QLabel(t)
            l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            l.setStyleSheet("font-weight: bold; padding-right: 10px;")
            l.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return l

        # 提示标签工厂
        def H(t):
            l = QLabel(t)
            l.setStyleSheet("font-size: 11px;")
            l.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return l

        # ---- 物质参数 ----
        sg = QGroupBox("物质参数")
        sgrid = QGridLayout(sg)
        sgrid.setHorizontalSpacing(10)
        sgrid.setVerticalSpacing(10)
        sgrid.setColumnStretch(0, 4)
        sgrid.setColumnStretch(1, 8)
        sgrid.setColumnStretch(2, 5)

        self.substance_combo = QComboBox()
        self.substance_combo.setStyleSheet(COMBOBOX_STYLE)
        self.substance_combo.addItems(["自定义"] + list(SUBSTANCE_DATABASE.keys()))
        self.substance_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.substance_combo.currentTextChanged.connect(self._on_substance)
        sgrid.addWidget(L("物质选择:"), 0, 0)
        sgrid.addWidget(self.substance_combo, 0, 1)
        sgrid.addWidget(H("选择后自动填充物性参数"), 0, 2)

        self.tc_input = QLineEdit()
        self.tc_input.setPlaceholderText("临界温度")
        self.tc_input.setValidator(QDoubleValidator(1, 2000, 2))
        self.tc_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sgrid.addWidget(L("临界温度 Tc (K):"), 1, 0)
        sgrid.addWidget(self.tc_input, 1, 1)
        sgrid.addWidget(H("甲烷=190.56"), 1, 2)

        self.pc_input = QLineEdit()
        self.pc_input.setPlaceholderText("临界压力")
        self.pc_input.setValidator(QDoubleValidator(100, 100000, 1))
        self.pc_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sgrid.addWidget(L("临界压力 Pc (kPa):"), 2, 0)
        sgrid.addWidget(self.pc_input, 2, 1)
        sgrid.addWidget(H("甲烷=4599"), 2, 2)

        self.omega_input = QLineEdit()
        self.omega_input.setPlaceholderText("偏心因子")
        self.omega_input.setValidator(QDoubleValidator(-1, 2, 4))
        self.omega_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sgrid.addWidget(L("偏心因子 ω:"), 3, 0)
        sgrid.addWidget(self.omega_input, 3, 1)
        sgrid.addWidget(H("甲烷=0.0115"), 3, 2)

        self.mw_input = QLineEdit()
        self.mw_input.setPlaceholderText("分子量")
        self.mw_input.setValidator(QDoubleValidator(1, 500, 3))
        self.mw_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sgrid.addWidget(L("分子量 M (g/mol):"), 4, 0)
        sgrid.addWidget(self.mw_input, 4, 1)
        sgrid.addWidget(H("甲烷=16.04"), 4, 2)

        self.zc_input = QLineEdit("0.27")
        self.zc_input.setPlaceholderText("临界压缩因子")
        self.zc_input.setValidator(QDoubleValidator(0.1, 0.5, 3))
        self.zc_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sgrid.addWidget(L("临界压缩因子 Zc:"), 5, 0)
        sgrid.addWidget(self.zc_input, 5, 1)
        sgrid.addWidget(H("一般取0.27"), 5, 2)

        ll.addWidget(sg)

        # ---- 状态方程选择 ----
        eg = QGroupBox("状态方程选择")
        egrid = QGridLayout(eg)
        egrid.setHorizontalSpacing(10)
        egrid.setVerticalSpacing(10)
        egrid.setColumnStretch(0, 4)
        egrid.setColumnStretch(1, 8)
        egrid.setColumnStretch(2, 5)

        self.eos_type = QComboBox()
        self.eos_type.setStyleSheet(COMBOBOX_STYLE)
        self.eos_type.addItems([
            "理想气体方程",
            "范德瓦尔斯方程",
            "Redlich-Kwong方程",
            "Soave-Redlich-Kwong方程",
            "Peng-Robinson方程"
        ])
        self.eos_type.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        egrid.addWidget(L("状态方程:"), 0, 0)
        egrid.addWidget(self.eos_type, 0, 1)
        egrid.addWidget(H("推荐SRK或PR"), 0, 2)

        self.calc_type_combo = QComboBox()
        self.calc_type_combo.setStyleSheet(COMBOBOX_STYLE)
        self.calc_type_combo.addItems([
            "P-V-T关系计算",
            "压缩因子计算",
            "逸度系数计算",
            "剩余性质计算"
        ])
        self.calc_type_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        egrid.addWidget(L("计算类型:"), 1, 0)
        egrid.addWidget(self.calc_type_combo, 1, 1)
        egrid.addWidget(H("默认综合计算全部性质"), 1, 2)

        ll.addWidget(eg)

        # ---- 计算条件 ----
        cg = QGroupBox("计算条件")
        cgrid = QGridLayout(cg)
        cgrid.setHorizontalSpacing(10)
        cgrid.setVerticalSpacing(10)
        cgrid.setColumnStretch(0, 4)
        cgrid.setColumnStretch(1, 8)
        cgrid.setColumnStretch(2, 5)

        self.temperature_input = QLineEdit("300")
        self.temperature_input.setPlaceholderText("温度")
        self.temperature_input.setValidator(QDoubleValidator(1, 2000, 2))
        self.temperature_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        cgrid.addWidget(L("温度 T (K):"), 0, 0)
        cgrid.addWidget(self.temperature_input, 0, 1)
        cgrid.addWidget(H("例如298.15"), 0, 2)

        self.pressure_input = QLineEdit("101.325")
        self.pressure_input.setPlaceholderText("压力")
        self.pressure_input.setValidator(QDoubleValidator(0.1, 100000, 2))
        self.pressure_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        cgrid.addWidget(L("压力 P (kPa):"), 1, 0)
        cgrid.addWidget(self.pressure_input, 1, 1)
        cgrid.addWidget(H("例如101.325"), 1, 2)

        self.volume_input = QLineEdit()
        self.volume_input.setPlaceholderText("可选，留空自动计算")
        self.volume_input.setValidator(QDoubleValidator(1e-6, 1000, 6))
        self.volume_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        cgrid.addWidget(L("摩尔体积 V (m³/mol):"), 2, 0)
        cgrid.addWidget(self.volume_input, 2, 1)
        cgrid.addWidget(H("留空则由EOS求解"), 2, 2)

        ll.addWidget(cg)

        # ---- 方程说明 ----
        info_group = QGroupBox("状态方程说明")
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

        # ---- 底部拉伸 ----
        ll.addStretch()

        # ========== 右侧结果区 ==========
        right = QWidget()
        right.setMinimumWidth(300)
        rl = QVBoxLayout(right)
        rl.setSpacing(10)

        rg = QGroupBox("计算结果")
        rv = QVBoxLayout(rg)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        self.result_text.setStyleSheet(
            "QTextEdit { "
            "font-family: Consolas, 'Microsoft YaHei', monospace; "
            "font-size: 13px; "
            "}"
        )
        rv.addWidget(self.result_text)
        rl.addWidget(rg)

        # 下载按钮行：清空 → DOCX → PDF
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        for label, style, slot in [
            ("清空", CLEAR_BTN_STYLE, self.clear_inputs),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        rl.addLayout(btn_layout)

        # 计算按钮（最底部）
        calc_btn = self.make_calc_button("查 询")
        calc_btn.clicked.connect(self.calculate)
        rl.addWidget(calc_btn)

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
    def _solve_Z(eos_type, params, T, P):
        """将立方 EOS 转为 Z 的多项式，返回气相根（最大的正实根）。"""
        R = 8.314
        if not params:
            return 1.0

        a = params['a']
        b = params['b']
        A = a * (P * 1000) / (R * T) ** 2
        B = b * (P * 1000) / (R * T)

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
    def _fugacity_coeff(eos_type, params, Z, T, P):
        """解析逸度系数 ln φ"""
        R = 8.314
        if not params or Z <= 0:
            return 1.0

        a = params['a']
        b = params['b']
        A = a * (P * 1000) / (R * T) ** 2
        B = b * (P * 1000) / (R * T)

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
    #  剩余性质（解析精确式，经 U_R 积分途径推导并数值验证）
    # ------------------------------------------------------------------

    @staticmethod
    def _residual_properties(eos_type, params, Z, T, P, tc, omega):
        """
        返回 (H^R, S^R, G^R) J/mol, J/(mol·K), J/mol

        推导: U^R = ∫[T(∂P/∂T)_V − P]dV = −(a−T·a')·I(V)，
              H^R = U^R + RT(Z−1)。
        吸引项因子统一为 (1−β̄)，β̄ ≡ (T/a)(da/dT)：
          vdW: β̄=0；RK: β̄=−0.5（→教科书 H^R/RT = Z−1−(3A/2B)ln(1+B/Z)）
          SRK/PR: β̄ = −κ√Tr/(1+κ(1−√Tr))
        S^R 用恒等式 S^R = (H^R − RT·lnφ)/T（与逸度系数严格自洽），
        G^R = RT·lnφ。
        """
        R = 8.314
        if not params:
            return 0.0, 0.0, 0.0

        a = params['a']
        b = params['b']
        A = a * (P * 1000) / (R * T) ** 2
        B = b * (P * 1000) / (R * T)
        Tr = T / tc if tc > 0 else 1.0
        sqrt_Tr = math.sqrt(Tr) if Tr > 0 else 1.0

        phi = EOSCalculator._fugacity_coeff(eos_type, params, Z, T, P)
        G_R = R * T * math.log(phi) if phi > 0 else 0.0

        if eos_type == "范德瓦尔斯方程":
            H_R = R * T * (Z - 1.0) - a * (P * 1000) / (Z * R * T)

        elif eos_type == "Redlich-Kwong方程":
            # β̄ = −0.5 恒定 → 因子 1.5
            H_R = R * T * (Z - 1.0 - 1.5 * (A / B) * math.log(1.0 + B / Z))

        elif eos_type == "Soave-Redlich-Kwong方程":
            m = 0.480 + 1.574 * omega - 0.176 * omega ** 2
            beta = -m * sqrt_Tr / (1.0 + m * (1.0 - sqrt_Tr))
            H_R = R * T * (Z - 1.0 - (A / B) * (1.0 - beta) * math.log(1.0 + B / Z))

        elif eos_type == "Peng-Robinson方程":
            kappa = 0.37464 + 1.54226 * omega - 0.26992 * omega ** 2
            beta = -kappa * sqrt_Tr / (1.0 + kappa * (1.0 - sqrt_Tr))
            sqrt2 = math.sqrt(2.0)
            H_R = R * T * (Z - 1.0
                           - (A / (2.0 * sqrt2 * B)) * (1.0 - beta)
                           * math.log((Z + (1 + sqrt2) * B) / (Z + (1 - sqrt2) * B)))
        else:
            H_R = 0.0

        S_R = (H_R - G_R) / T
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
                Z = self._solve_Z(eos_type, params, T, P)
            V = Z * R * T / (P * 1000)
        else:
            Z = P * 1000 * V / (R * T)

        density = mw / (V * 1000) if V and V > 0 else 0.0

        phi = self._fugacity_coeff(eos_type, params, Z, T, P)
        fugacity = phi * P

        H_R, S_R, G_R = self._residual_properties(eos_type, params, Z, T, P, tc, omega)

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
        self.tc_input.clear()
        self.pc_input.clear()
        self.omega_input.clear()
        self.mw_input.clear()
        self.zc_input.setText("0.27")
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
            f"  偏心因子 ω      : {r['acentric_factor']:.4f}",
            "",
            f"  压缩因子 Z      : {r['z_factor']:.6f}",
            f"  摩尔体积 V      : {r['molar_volume']:.6e} m³/mol",
            f"  密度 ρ        : {r['density']:.4f} kg/m³",
            "",
            f"  逸度系数 φ    : {r['fugacity_coeff']:.6f}",
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
        if not self.result_text.toPlainText().strip() or not self._last_result:
            QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
            return None
        return self.result_text.toPlainText()

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "EOSCalculator")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "EOSCalculator")
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    calculator = EOSCalculator()
    calculator.resize(1200, 800)
    calculator.show()
    sys.exit(app.exec())
