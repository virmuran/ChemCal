"""
板框压滤机过滤面积计算器

适用：厢式 / 板框式压滤机的过滤面积核算、滤室容积与每批处理量、恒压过滤时间（Ruth 方程）、
      洗涤与循环周期、产能核算，以及由目标产能反算所需过滤面积与机型推荐。

═══════════════ 1. 几何恒等式（本计算器由过滤面积直接算滤室总容积）═══════════════
    过滤面积   A = n · 2 · a          （一个滤室两面过滤；a = 单面有效过滤面积，n = 滤室数）
    滤室总容积 V = n · a · δ          （δ = 滤饼厚度，即滤室深度）
    ⇒  V = A · δ / 2

    与厂商公开样本逐条复核（厢式 XAZ 系列 630/800/1000/1250 十余个型号，偏差 ≤4%）：
      800×800   A=50 m²  δ=30 mm → A·δ/2 = 750 L   厂商标称滤室总容量 750 L   （吻合）
      1000×1000 A=60 m²  δ=30 mm → 900 L           厂商标称 0.90 m³          （吻合）
      1000×1000 A=100 m² δ=30 mm → 1500 L          厂商标称 1475 L           （+1.7%）
      1250×1250 A=100 m² δ=30 mm → 1500 L          厂商标称 1468 L           （+2.2%）

═══════════════ 2. 过滤动力学（Ruth 恒压过滤方程）═══════════════
    量纲：μ[Pa·s]  α[m/kg]  c[kg 干渣/m³ 滤液]  V[m³]  A[m²]  Δp[Pa]

        t = μ·α·c·(V² + 2·V·V_e) / (2·A²·Δp)

    以单位面积产液量 q = V/A、q_e = V_e/A 表示：
        t = μ·α·c·(q² + 2·q·q_e) / (2·Δp)

    洗涤（板框经典工程假定：洗涤速率 = 终了过滤速率的 1/4）
        (dV/dt)_end = A²·Δp / (μ·α·c·(V + V_e))
        t_w = 4·V_w / (dV/dt)_end

    循环周期  T = t_f + t_w + t_aux       产能 = 每批干渣量 × 1440 / T

    ⚠ 由上式可推得一条有用的性质：每批滤液量 V ∝ A，故 t_f ∝ V²/A² 与 A 无关、
      t_w 亦然 ⇒ **循环周期与过滤面积无关，产能与面积成正比**（前提：滤饼厚度不变）。
      这正是「反算选型」可以直接按面积线性放大的依据。

═══════════════ 3. 数据来源与假设（计算书中逐条标注）═══════════════
    · 机型规格：厂商公开样本（厢式 XAZ 系列），仅作选型起点，设计须以订货样本为准；
      厂商样本中 630 系列的「滤饼厚度 25 mm」与其「滤室总容量」互不吻合（按容积反推约 28 mm），
      故本计算器不含 630 预设，避免把厂商口径矛盾带进计算。
    · 滤饼比阻 α、滤室充满系数 φ、滤饼含水率 w：**属试验/经验取值**（默认值仅数量级参考），
      工程设计宜取同物料小试数据；本计算器在报告中标为「经验取值」而非标准值。
    · 过滤压力：厂商样本常用 0.5~1.6 MPa（厢式），超出机型额定压力时给出警告。
"""

import math
import os
import importlib.util

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QGridLayout, QTextEdit, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtSvgWidgets import QSvgWidget

from app_styles import (COMBOBOX_STYLE, CALC_BUTTON_STYLE, SCROLL_AREA_STYLE,
                        INPUT_LABEL_STYLE, CLEAR_BTN_STYLE, DOCX_BTN_STYLE,
                        PDF_BTN_STYLE)
from utils.docx_utils import ReportExporter
from svg_utils import svg_text
from datetime import datetime

from calculator_base import CalculatorBase


class FilterPressAreaCalculator(CalculatorBase):
    """板框压滤机过滤面积计算器"""

    #: 常用厢式压滤机机型预设：(滤板外框尺寸 mm, 过滤面积 m², 滤饼厚度 mm)
    #: 取自厂商公开样本；滤室总容量可由 V = A·δ/2 复核（见模块 docstring）
    PRESS_PRESETS = {
        "自定义（手动填过滤面积）":              None,
        "XAZ30/800-U   800×800  30 m²  30 mm":  (800, 30.0, 30.0),
        "XAZ50/800-U   800×800  50 m²  30 mm":  (800, 50.0, 30.0),
        "XAZ60/1000-U  1000×1000 60 m²  30 mm": (1000, 60.0, 30.0),
        "XAZ100/1000-U 1000×1000 100 m² 30 mm": (1000, 100.0, 30.0),
        "XAZ100/1250-U 1250×1250 100 m² 30 mm": (1250, 100.0, 30.0),
        "XAZ140/1250-U 1250×1250 140 m² 30 mm": (1250, 140.0, 30.0),
    }

    #: 计算模式
    MODES = ["面积核算（现有设备）", "产能反算选型（目标产量→面积）"]

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_result = {}
        self.setup_ui()
        self.setup_default_values()
        self.setup_wheel_blocker()

    # ═══════════════════════ UI ═══════════════════════
    def setup_ui(self):
        main = QHBoxLayout(self)
        main.setSpacing(15)
        main.setContentsMargins(10, 10, 10, 10)

        # ── 左栏：输入 ──
        scroll = QScrollArea()
        scroll.setStyleSheet(SCROLL_AREA_STYLE)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setSpacing(10)

        desc = QLabel(
            "板框（厢式）压滤机过滤面积核算：机型与滤饼厚度 → 滤室容积 → 每批处理量 → "
            "恒压过滤时间（Ruth 方程）→ 洗涤与循环周期 → 产能；亦可由目标产量反算所需面积。")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size:12px;padding:5px;")
        ll.addWidget(desc)

        ls = INPUT_LABEL_STYLE

        def lbl(t):
            w = QLabel(t)
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            w.setStyleSheet(ls)
            return w

        def hint(t):
            w = QLabel(t)
            w.setStyleSheet("font-style:italic;color:#666;")
            return w

        # ── 计算模式 ──
        g0 = CalculatorBase.make_group_box("计算模式")
        g0g = QGridLayout(g0)
        g0g.setHorizontalSpacing(10)
        g0g.setVerticalSpacing(10)
        g0g.setColumnStretch(0, 4)
        g0g.setColumnStretch(1, 8)
        g0g.setColumnStretch(2, 5)

        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet(COMBOBOX_STYLE)
        self.mode_combo.addItems(self.MODES)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        g0g.addWidget(lbl("计算模式:"), 0, 0)
        g0g.addWidget(self.mode_combo, 0, 1)
        g0g.addWidget(hint("反算模式需填目标产量"), 0, 2)
        ll.addWidget(g0)

        # ── 机型参数 ──
        g1 = CalculatorBase.make_group_box("机型与滤室参数")
        g1g = QGridLayout(g1)
        g1g.setHorizontalSpacing(10)
        g1g.setVerticalSpacing(10)
        g1g.setColumnStretch(0, 4)
        g1g.setColumnStretch(1, 8)
        g1g.setColumnStretch(2, 5)
        r = 0

        self.preset_combo = QComboBox()
        self.preset_combo.setStyleSheet(COMBOBOX_STYLE)
        self.preset_combo.addItems(list(self.PRESS_PRESETS.keys()))
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        self._lbl_preset = lbl("机型预设:")
        self._hint_preset = hint("选自厂商样本")
        g1g.addWidget(self._lbl_preset, r, 0)
        g1g.addWidget(self.preset_combo, r, 1)
        g1g.addWidget(self._hint_preset, r, 2)
        r += 1

        self.area_input = QLineEdit("50")
        self.area_input.setValidator(QDoubleValidator(0.1, 5000.0, 2))
        self._lbl_area = lbl("过滤面积 A (m²):")
        self._hint_area = hint("总过滤面积（可手改）")
        g1g.addWidget(self._lbl_area, r, 0)
        g1g.addWidget(self.area_input, r, 1)
        g1g.addWidget(self._hint_area, r, 2)
        r += 1

        self.cake_thk_input = QLineEdit("30")
        self.cake_thk_input.setValidator(QDoubleValidator(5.0, 60.0, 1))
        self._lbl_thk = lbl("滤饼厚度 δ (mm):")
        self._hint_thk = hint("即滤室深度")
        g1g.addWidget(self._lbl_thk, r, 0)
        g1g.addWidget(self.cake_thk_input, r, 1)
        g1g.addWidget(self._hint_thk, r, 2)
        r += 1

        self.fill_factor_input = QLineEdit("0.95")
        self.fill_factor_input.setValidator(QDoubleValidator(0.5, 1.0, 2))
        self._lbl_fill = lbl("滤室充满系数 φ:")
        self._hint_fill = hint("经验取值 0.85~1.0")
        g1g.addWidget(self._lbl_fill, r, 0)
        g1g.addWidget(self.fill_factor_input, r, 1)
        g1g.addWidget(self._hint_fill, r, 2)
        r += 1

        self.target_input = QLineEdit("10")
        self.target_input.setValidator(QDoubleValidator(0.1, 100000.0, 2))
        self._lbl_target = lbl("目标干渣产量 (t/d):")
        self._hint_target = hint("仅反算模式使用")
        g1g.addWidget(self._lbl_target, r, 0)
        g1g.addWidget(self.target_input, r, 1)
        g1g.addWidget(self._hint_target, r, 2)
        r += 1

        ll.addWidget(g1)

        # ── 物料参数 ──
        g2 = CalculatorBase.make_group_box("物料参数")
        g2g = QGridLayout(g2)
        g2g.setHorizontalSpacing(10)
        g2g.setVerticalSpacing(10)
        g2g.setColumnStretch(0, 4)
        g2g.setColumnStretch(1, 8)
        g2g.setColumnStretch(2, 5)
        r = 0

        self.solid_input = QLineEdit("10")
        self.solid_input.setValidator(QDoubleValidator(0.1, 60.0, 2))
        self._lbl_solid = lbl("料浆固含量 x_s (wt%):")
        self._hint_solid = hint("干固体质量分数")
        g2g.addWidget(self._lbl_solid, r, 0)
        g2g.addWidget(self.solid_input, r, 1)
        g2g.addWidget(self._hint_solid, r, 2)
        r += 1

        self.cake_water_input = QLineEdit("60")
        self.cake_water_input.setValidator(QDoubleValidator(1.0, 90.0, 2))
        self._lbl_cakewater = lbl("滤饼含水率 w (wt%):")
        self._hint_cakewater = hint("湿滤饼中液体质量分数")
        g2g.addWidget(self._lbl_cakewater, r, 0)
        g2g.addWidget(self.cake_water_input, r, 1)
        g2g.addWidget(self._hint_cakewater, r, 2)
        r += 1

        self.cake_rho_input = QLineEdit("1300")
        self.cake_rho_input.setValidator(QDoubleValidator(500.0, 3000.0, 1))
        self._lbl_cakerho = lbl("湿滤饼密度 ρ_c (kg/m³):")
        self._hint_cakerho = hint("经验取值 1200~1600")
        g2g.addWidget(self._lbl_cakerho, r, 0)
        g2g.addWidget(self.cake_rho_input, r, 1)
        g2g.addWidget(self._hint_cakerho, r, 2)
        r += 1

        self.filtrate_rho_input = QLineEdit("1000")
        self.filtrate_rho_input.setValidator(QDoubleValidator(500.0, 2500.0, 1))
        self._lbl_frho = lbl("滤液密度 ρ_f (kg/m³):")
        self._hint_frho = hint("水溶液取 1000")
        g2g.addWidget(self._lbl_frho, r, 0)
        g2g.addWidget(self.filtrate_rho_input, r, 1)
        g2g.addWidget(self._hint_frho, r, 2)
        r += 1

        ll.addWidget(g2)

        # ── 过滤动力学 ──
        g3 = CalculatorBase.make_group_box("过滤动力学（Ruth 恒压过滤）")
        g3g = QGridLayout(g3)
        g3g.setHorizontalSpacing(10)
        g3g.setVerticalSpacing(10)
        g3g.setColumnStretch(0, 4)
        g3g.setColumnStretch(1, 8)
        g3g.setColumnStretch(2, 5)
        r = 0

        self.dp_input = QLineEdit("0.6")
        self.dp_input.setValidator(QDoubleValidator(0.05, 3.0, 2))
        self._lbl_dp = lbl("过滤压力 Δp (MPa):")
        self._hint_dp = hint("厢式常用 0.5~1.0")
        g3g.addWidget(self._lbl_dp, r, 0)
        g3g.addWidget(self.dp_input, r, 1)
        g3g.addWidget(self._hint_dp, r, 2)
        r += 1

        self.mu_input = QLineEdit("1.0")
        self.mu_input.setValidator(QDoubleValidator(0.1, 5000.0, 3))
        self._lbl_mu = lbl("滤液粘度 μ (mPa·s):")
        self._hint_mu = hint("20 °C 水 = 1.0")
        g3g.addWidget(self._lbl_mu, r, 0)
        g3g.addWidget(self.mu_input, r, 1)
        g3g.addWidget(self._hint_mu, r, 2)
        r += 1

        self.alpha_input = QLineEdit("1.0e12")
        self._lbl_alpha = lbl("滤饼比阻 α (m/kg):")
        self._hint_alpha = hint("经验取值 1e11~1e13")
        g3g.addWidget(self._lbl_alpha, r, 0)
        g3g.addWidget(self.alpha_input, r, 1)
        g3g.addWidget(self._hint_alpha, r, 2)
        r += 1

        self.ve_input = QLineEdit("0")
        self.ve_input.setValidator(QDoubleValidator(0.0, 1e7, 3))
        self._lbl_ve = lbl("当量滤液体积 V_e (L):")
        self._hint_ve = hint("滤布阻力项，无数据可取 0")
        g3g.addWidget(self._lbl_ve, r, 0)
        g3g.addWidget(self.ve_input, r, 1)
        g3g.addWidget(self._hint_ve, r, 2)
        r += 1

        self.aux_input = QLineEdit("45")
        self.aux_input.setValidator(QDoubleValidator(0.0, 600.0, 1))
        self._lbl_aux = lbl("辅助时间 t_aux (min):")
        self._hint_aux = hint("卸饼/装机/进料准备")
        g3g.addWidget(self._lbl_aux, r, 0)
        g3g.addWidget(self.aux_input, r, 1)
        g3g.addWidget(self._hint_aux, r, 2)
        r += 1

        self.wash_ratio_input = QLineEdit("0.10")
        self.wash_ratio_input.setValidator(QDoubleValidator(0.0, 5.0, 3))
        self._lbl_wash = lbl("洗涤液量 / 滤液量:")
        self._hint_wash = hint("填 0 表示不洗涤")
        g3g.addWidget(self._lbl_wash, r, 0)
        g3g.addWidget(self.wash_ratio_input, r, 1)
        g3g.addWidget(self._hint_wash, r, 2)
        r += 1

        ll.addWidget(g3)
        ll.addStretch()
        scroll.setWidget(lw)

        # ── 右栏：结果 ──
        rw = QWidget()
        rw.setMinimumWidth(300)
        rl = QVBoxLayout(rw)
        rl.setSpacing(15)

        self.svg_widget = QSvgWidget()
        self.svg_widget.setMinimumHeight(200)
        self.svg_widget.setMaximumHeight(260)
        self.svg_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rl.addWidget(self.svg_widget)
        self.svg_widget.renderer().setAspectRatioMode(Qt.KeepAspectRatio)

        rg = CalculatorBase.make_group_box("计算结果")
        rvl = QVBoxLayout(rg)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setStyleSheet(
            "QTextEdit { font-family: Consolas, 'Microsoft YaHei', monospace; font-size: 13px; }")
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        rvl.addWidget(self.result_text)
        rl.addWidget(rg)

        bl = QHBoxLayout()
        bl.setSpacing(8)
        for name, style, cb in [
            ("清空", CLEAR_BTN_STYLE, self.clear_inputs),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(name)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(cb)
            bl.addWidget(btn)
        rl.addLayout(bl)

        calc_btn = self.make_calc_button("计 算")
        calc_btn.clicked.connect(self.calculate)
        rl.addWidget(calc_btn)

        main.addWidget(scroll, 2)
        main.addWidget(rw, 1)

        self._on_mode_changed(self.mode_combo.currentText())
        self._update_svg_diagram()

    # ═══════════════════════ 交互 ═══════════════════════
    def _on_preset_changed(self, text):
        """机型预设 → 自动填过滤面积 / 滤饼厚度"""
        preset = self.PRESS_PRESETS.get(text)
        if preset:
            _size, area, thk = preset
            self.area_input.setText(f"{area:g}")
            self.cake_thk_input.setText(f"{thk:g}")

    def _on_mode_changed(self, mode):
        reverse = mode == self.MODES[1]
        for w in (self._lbl_target, self.target_input, self._hint_target):
            w.setVisible(reverse)

    def _num(self, widget, name):
        try:
            return float(widget.text().strip())
        except (TypeError, ValueError):
            raise ValueError(f"{name} 未填写或不是数字")

    # ═══════════════════════ 计算 ═══════════════════════
    def calculate(self):
        try:
            res = self._compute()
            self._last_result = res
            self._render(res)
            self._update_svg_diagram()
        except ValueError as e:
            self._show_error(str(e))
        except Exception as e:                                  # noqa: BLE001
            self._show_error(f"计算错误：{e}")

    def _compute(self):
        mode_reverse = self.mode_combo.currentText() == self.MODES[1]

        A = self._num(self.area_input, "过滤面积")
        delta_mm = self._num(self.cake_thk_input, "滤饼厚度")
        phi = self._num(self.fill_factor_input, "滤室充满系数")
        x_s = self._num(self.solid_input, "料浆固含量") / 100.0
        w_cake = self._num(self.cake_water_input, "滤饼含水率") / 100.0
        rho_cake = self._num(self.cake_rho_input, "湿滤饼密度")
        rho_f = self._num(self.filtrate_rho_input, "滤液密度")
        dp_mpa = self._num(self.dp_input, "过滤压力")
        mu_cp = self._num(self.mu_input, "滤液粘度")
        alpha = self._parse_sci(self.alpha_input.text(), "滤饼比阻")
        V_e = self._num(self.ve_input, "当量滤液体积") / 1000.0
        t_aux = self._num(self.aux_input, "辅助时间")
        wash_ratio = self._num(self.wash_ratio_input, "洗涤液量比")

        # ── 校验 ──
        if A <= 0:
            raise ValueError("过滤面积必须大于 0")
        if delta_mm <= 0:
            raise ValueError("滤饼厚度必须大于 0")
        if not (0.0 < phi <= 1.0):
            raise ValueError("滤室充满系数应在 0~1 之间")
        if not (0.0 < x_s < 1.0):
            raise ValueError("料浆固含量应在 0~100 wt% 之间")
        if not (0.0 < w_cake < 1.0):
            raise ValueError("滤饼含水率应在 0~100 wt% 之间")
        # 滤饼必须比料浆更浓：湿滤饼固体分数 (1-w) 必须大于料浆固含量 x_s
        if (1.0 - w_cake) <= x_s:
            raise ValueError(
                f"滤饼含水率与料浆固含量不匹配：滤饼固体分数 {100*(1-w_cake):.1f}% "
                f"必须大于料浆固含量 {100*x_s:.1f}%（否则物料守恒不成立，无滤液产出）")
        if dp_mpa <= 0:
            raise ValueError("过滤压力必须大于 0")
        if alpha <= 0:
            raise ValueError("滤饼比阻必须大于 0")
        if mu_cp <= 0:
            raise ValueError("滤液粘度必须大于 0")

        warn = []

        # ── 1. 几何：滤室容积（V = A·δ/2）──
        delta_m = delta_mm / 1000.0
        V_chamber = A * delta_m / 2.0

        # ── 2. 每批滤饼与物料衡算 ──
        V_cake = V_chamber * phi
        m_cake = V_cake * rho_cake
        m_solid = m_cake * (1.0 - w_cake)          # 干渣
        m_liquid_cake = m_cake * w_cake            # 滤饼带液
        m_slurry = m_solid / x_s                   # 每批料浆
        m_filtrate = m_slurry - m_cake             # 滤液
        V_filtrate = m_filtrate / rho_f
        c_ratio = m_solid / V_filtrate if V_filtrate > 0 else 0.0   # kg 干渣/m³ 滤液

        # ── 3. Ruth 恒压过滤时间 ──
        mu = mu_cp * 1e-3
        dp = dp_mpa * 1e6
        t_f_s = mu * alpha * c_ratio * (V_filtrate ** 2 + 2.0 * V_filtrate * V_e) / \
            (2.0 * A ** 2 * dp)
        t_f = t_f_s / 60.0
        q_avg = V_filtrate / A                     # 单位面积产液量 m³/m²
        # 终了过滤速率与洗涤时间
        dVdt_end = A ** 2 * dp / (mu * alpha * c_ratio * (V_filtrate + V_e))
        V_wash = V_filtrate * wash_ratio
        t_wash = (4.0 * V_wash / dVdt_end) / 60.0 if (wash_ratio > 0 and dVdt_end > 0) else 0.0
        u_filter = V_filtrate / t_f_s if t_f_s > 0 else 0.0        # m³/s
        u_wash = (V_wash / (t_wash * 60.0)) if t_wash > 0 else 0.0

        # ── 4. 循环周期与产能 ──
        T_cycle = t_f + t_wash + t_aux
        batches_per_day = 1440.0 / T_cycle if T_cycle > 0 else 0.0
        solid_per_day = m_solid * batches_per_day / 1000.0          # t/d
        slurry_per_hour = m_slurry * (60.0 / T_cycle) if T_cycle > 0 else 0.0   # kg/h
        cap_per_area = solid_per_day / A if A > 0 else 0.0          # t/(m²·d)

        if dp_mpa > 1.6:
            warn.append(f"过滤压力 {dp_mpa:.2f} MPa 超出厢式压滤机样本常用上限 1.6 MPa，"
                        "须核对机型额定压力")
        if dp_mpa < 0.4:
            warn.append(f"过滤压力 {dp_mpa:.2f} MPa 偏低，常规厢式机型工作在 0.5~1.0 MPa")
        if phi > 1.0:
            warn.append("滤室充满系数不应大于 1.0")
        if t_aux <= 0:
            warn.append("辅助时间为 0 时循环周期仅含过滤+洗涤，实际产能会明显高估")

        # ── 5. 反算选型 ──
        A_req = None
        recommend = ""
        if mode_reverse:
            target = self._num(self.target_input, "目标干渣产量")
            if cap_per_area <= 0:
                raise ValueError("单位面积产能为 0，无法反算")
            A_req = target / cap_per_area
            recommend, rec_area, rec_thk = self._recommend(A_req)
            if rec_area:
                batches_needed = max(1, math.ceil(A_req / rec_area))
                warn.append(
                    f"若用 {recommend}（单台 {rec_area:g} m²），需 {batches_needed} 台并联；"
                    f"或选更大机型。反算依据：循环周期与面积无关，产能 ∝ 面积（滤饼厚度不变时）")

        return {
            "mode": self.mode_combo.currentText(),
            "A": A, "delta_mm": delta_mm, "phi": phi,
            "x_s": x_s * 100, "w_cake": w_cake * 100,
            "rho_cake": rho_cake, "rho_f": rho_f,
            "dp_mpa": dp_mpa, "mu_cp": mu_cp, "alpha": alpha,
            "V_e": V_e, "t_aux": t_aux, "wash_ratio": wash_ratio,
            "V_chamber": V_chamber, "V_cake": V_cake, "m_cake": m_cake,
            "m_solid": m_solid, "m_liquid_cake": m_liquid_cake,
            "m_slurry": m_slurry, "m_filtrate": m_filtrate,
            "V_filtrate": V_filtrate, "c_ratio": c_ratio,
            "t_f": t_f, "t_wash": t_wash, "T_cycle": T_cycle,
            "q_avg": q_avg, "u_filter": u_filter, "u_wash": u_wash,
            "V_wash": V_wash, "dVdt_end": dVdt_end,
            "batches_per_day": batches_per_day,
            "solid_per_day": solid_per_day,
            "slurry_per_hour": slurry_per_hour,
            "cap_per_area": cap_per_area,
            "A_req": A_req, "recommend": recommend,
            "warn": warn,
        }

    @staticmethod
    def _parse_sci(text, name):
        """解析可能写成 1e12 形式的科学计数输入"""
        t = (text or "").strip().replace("×", "x").replace("^", "e").lower()
        try:
            return float(t)
        except (TypeError, ValueError):
            raise ValueError(f"{name} 未填写或不是数字（可写 1e12 形式）")

    @staticmethod
    def _recommend(A_req):
        """按所需面积推荐预设机型，返回 (机型名, 推荐面积, 滤饼厚度)

        取「过滤面积 ≥ 需求」中最小的那个型号（够用且最省）。
        """
        best = None                      # (机型名, 滤饼厚度, 面积)
        for name, preset in FilterPressAreaCalculator.PRESS_PRESETS.items():
            if not preset:
                continue
            _size, area, thk = preset
            key = _split_preset_name(name)[0]
            if area >= A_req and (best is None or area < best[2]):
                best = (key, thk, area)
        if best:
            return best[0], best[2], best[1]
        # 超出预设最大机型的处理能力
        max_name, max_area = "", 0.0
        for name, preset in FilterPressAreaCalculator.PRESS_PRESETS.items():
            if preset and preset[1] > max_area:
                max_name, max_area = _split_preset_name(name)[0], preset[1]
        return f"超出样本最大机型（{max_name}）", max_area, 0.0

    # ═══════════════════════ 结果渲染 ═══════════════════════
    def _render(self, r):
        L = []
        L.append("板框压滤机过滤面积核算")
        L.append("=" * 58)
        L.append(f"【计算模式】{r['mode']}")
        L.append("")
        L.append("【一、滤室几何】")
        L.append(f"  过滤面积 A        = {r['A']:.2f} m²")
        L.append(f"  滤饼厚度 δ        = {r['delta_mm']:.1f} mm")
        L.append(f"  滤室总容积 V      = A·δ/2 = {r['V_chamber']:.4f} m³"
                 f"（{r['V_chamber']*1000:.1f} L）")
        L.append(f"  充满系数 φ        = {r['phi']:.2f}  →  实收滤饼容积 "
                 f"{r['V_cake']:.4f} m³")
        L.append("")
        L.append("【二、每批物料衡算】")
        L.append(f"  湿滤饼质量        = {r['m_cake']:.1f} kg"
                 f"（ρ_c = {r['rho_cake']:.0f} kg/m³）")
        L.append(f"  其中干渣          = {r['m_solid']:.1f} kg"
                 f"（含水率 {r['w_cake']:.1f} wt%）")
        L.append(f"  其中滤饼带液      = {r['m_liquid_cake']:.1f} kg")
        L.append(f"  每批料浆处理量    = {r['m_slurry']:.1f} kg"
                 f"（固含量 {r['x_s']:.2f} wt%）")
        L.append(f"  每批滤液量        = {r['m_filtrate']:.1f} kg  /  {r['V_filtrate']:.4f} m³")
        L.append(f"  干渣/滤液比 c     = {r['c_ratio']:.2f} kg/m³")
        L.append("")
        L.append("【三、过滤动力学（Ruth 恒压过滤）】")
        L.append(f"  过滤压力 Δp       = {r['dp_mpa']:.3f} MPa")
        L.append(f"  滤液粘度 μ        = {r['mu_cp']:.3f} mPa·s")
        L.append(f"  滤饼比阻 α        = {r['alpha']:.3e} m/kg   [经验/试验取值]")
        L.append(f"  当量滤液体积 V_e  = {r['V_e']*1000:.3f} L")
        L.append(f"  单位面积产液量 q  = {r['q_avg']:.4f} m³/m²")
        L.append(f"  → 过滤时间 t_f    = {r['t_f']:.2f} min   "
                 f"（t = μ·α·c·(V²+2V·V_e)/(2A²Δp)）")
        L.append(f"  → 平均过滤速率    = {r['u_filter']*1000:.2f} L/s"
                 f"（{r['u_filter']*3600:.2f} m³/h）")
        if r['t_wash'] > 0:
            L.append(f"  终了过滤速率      = {r['dVdt_end']*1000:.2f} L/s")
            L.append(f"  洗涤液量          = {r['V_wash']:.4f} m³")
            L.append(f"  → 洗涤时间 t_w    = {r['t_wash']:.2f} min"
                     "（按洗涤速率 = 终了过滤速率 1/4 的工程假定）")
        else:
            L.append("  洗涤时间 t_w      = 0（未设洗涤）")
        L.append("")
        L.append("【四、循环周期与产能】")
        L.append(f"  单循环时间 T      = t_f {r['t_f']:.2f} + t_w {r['t_wash']:.2f}"
                 f" + t_aux {r['t_aux']:.1f} = {r['T_cycle']:.2f} min")
        L.append(f"  日循环次数        = {r['batches_per_day']:.2f} 次/d")
        L.append(f"  → 干渣产量        = {r['solid_per_day']:.2f} t/d")
        L.append(f"  → 料浆处理量      = {r['slurry_per_hour']:.0f} kg/h")
        L.append(f"  → 单位面积产能    = {r['cap_per_area']*1000:.2f} kg/(m²·d)")
        L.append(f"  滤布总面积        ≈ {r['A']:.2f} m²（每面一块，等于过滤面积）")
        if r['A_req'] is not None:
            L.append("")
            L.append("【五、反算选型（目标产量 → 面积）】")
            L.append(f"  目标干渣产量      = {self._num(self.target_input, '目标干渣产量'):.2f} t/d")
            L.append(f"  → 所需过滤面积    = 目标 ÷ 单位面积产能 = {r['A_req']:.2f} m²")
            L.append(f"  → 推荐机型        = {r['recommend']}")
            L.append("  依据：滤饼厚度不变时循环周期与面积无关，产能与面积成正比")
        if r['warn']:
            L.append("")
            L.append("【提示与警告】")
            for i, w in enumerate(r['warn'], 1):
                L.append(f"  {i}) {w}")
        L.append("")
        L.append("=" * 58)
        L.append("  经验取值说明：滤饼比阻 α、充满系数 φ、滤饼含水率与密度均为试验/经验值，")
        L.append("  宜用同物料小试数据；机型规格取自厂商公开样本，设计须以订货样本为准。")
        L.append("=" * 58)
        self.result_text.setPlainText("\n".join(L))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"错误：{msg}")
        self._last_result = {}

    def _show_warn(self, msg):
        self.result_text.setPlainText(f"提示：{msg}")

    # ═══════════════════════ 清空 ═══════════════════════
    def setup_default_values(self):
        self.preset_combo.setCurrentIndex(1)      # XAZ30/800-U
        self.area_input.setText("50")
        self.cake_thk_input.setText("30")
        self.fill_factor_input.setText("0.95")
        self.target_input.setText("10")
        self.solid_input.setText("10")
        self.cake_water_input.setText("60")
        self.cake_rho_input.setText("1300")
        self.filtrate_rho_input.setText("1000")
        self.dp_input.setText("0.6")
        self.mu_input.setText("1.0")
        self.alpha_input.setText("1.0e12")
        self.ve_input.setText("0")
        self.aux_input.setText("45")
        self.wash_ratio_input.setText("0.10")

    def clear_inputs(self):
        """恢复出厂默认值（可直接重算）"""
        self.mode_combo.setCurrentIndex(0)
        self.preset_combo.setCurrentIndex(0)
        self.setup_default_values()
        self.result_text.clear()
        self._last_result = {}
        self._on_mode_changed(self.mode_combo.currentText())
        self._update_svg_diagram()

    # ═══════════════════════ 历史 ═══════════════════════
    def _get_history_data(self):
        r = self._last_result
        if not r:
            return {"inputs": {}, "outputs": {}}
        inputs = {
            "计算模式": r.get("mode", ""),
            "过滤面积_m2": r.get("A", 0),
            "滤饼厚度_mm": r.get("delta_mm", 0),
            "料浆固含量_wt%": r.get("x_s", 0),
            "滤饼含水率_wt%": r.get("w_cake", 0),
            "过滤压力_MPa": r.get("dp_mpa", 0),
        }
        outputs = {
            "滤室总容积_m3": round(r.get("V_chamber", 0), 4),
            "每批干渣_kg": round(r.get("m_solid", 0), 1),
            "过滤时间_min": round(r.get("t_f", 0), 2),
            "循环周期_min": round(r.get("T_cycle", 0), 2),
            "干渣产量_t_d": round(r.get("solid_per_day", 0), 2),
        }
        if r.get("A_req") is not None:
            outputs["所需过滤面积_m2"] = round(r.get("A_req", 0), 2)
            outputs["推荐机型"] = r.get("recommend", "")
        return {"inputs": inputs, "outputs": outputs}

    # ═══════════════════════ 工程信息 / 报告 ═══════════════════════
    def get_project_info(self):
        """获取工程信息（dict，标准键）"""
        try:
            saved = {}
            if self.data_manager:
                saved = self.data_manager.get_project_info() or {}
        except Exception:                                        # noqa: BLE001
            saved = {}
        return {
            "company_name": saved.get("company_name", ""),
            "project_number": saved.get("project_number", ""),
            "project_name": saved.get("project_name", ""),
            "subproject_name": saved.get("subproject_name", ""),
            "calculation_type": "板框压滤机过滤面积核算",
        }

    def generate_report(self):
        """生成计算书文本（str；无结果返回 None）"""
        try:
            body = self.result_text.toPlainText()
            if not body or "过滤面积核算" not in body:
                return None
            info = self.get_project_info()
            head = "\n".join([
                "═" * 58,
                "        板框压滤机过滤面积计算书",
                "═" * 58,
            ])
            foot = "\n".join([
                "═" * 58,
                " 工程信息",
                "═" * 58,
                "",
                f"  公司名称: {info.get('company_name', '')}",
                f"  工程编号: {info.get('project_number', '')}",
                f"  工程名称: {info.get('project_name', '')}",
                f"  子项名称: {info.get('subproject_name', '')}",
                f"  计算类型: {info.get('calculation_type', '')}",
                f"  计算日期: {datetime.now().strftime('%Y-%m-%d')}",
                "",
                "═" * 58,
                " 计算公式与依据",
                "═" * 58,
                "",
                "  1. 滤室总容积  V = A·δ/2",
                "     （A = n·2·a 一个滤室两面过滤；V = n·a·δ）",
                "     与厂商样本复核：800×800/50 m²/30 mm → 750 L（样本 750 L）；",
                "     1000×1000/60 m²/30 mm → 900 L（样本 0.90 m³），偏差 ≤4%",
                "  2. 恒压过滤    t = μ·α·c·(V² + 2·V·V_e)/(2·A²·Δp)   （Ruth 方程）",
                "  3. 洗涤时间    t_w = 4·V_w/(dV/dt)_end；",
                "                 (dV/dt)_end = A²Δp/(μ·α·c·(V + V_e))",
                "  4. 循环周期    T = t_f + t_w + t_aux；产能 = 每批干渣 × 1440/T",
                "  5. 反算选型    滤饼厚度不变时循环周期与面积无关 ⇒ 产能 ∝ 面积",
                "",
                "═" * 58,
                " 数据来源与假设",
                "═" * 58,
                "",
                "  1. 机型规格取自厂商公开样本（厢式 XAZ 系列），仅作选型起点，",
                "     设计须以订货样本的滤室容积与额定压力为准；",
                "  2. 滤饼比阻 α、充满系数 φ、滤饼含水率与密度均属试验/经验取值，",
                "     宜以同物料小试数据替换后再定案；",
                "  3. 洗涤按「洗涤速率 = 终了过滤速率 1/4」的板框经典工程假定，",
                "     与洗涤液粘度、洗涤压力差异相关，实际宜按试验修正；",
                "  4. 计算结果仅供参考，实际工程须经专业工程师审核确认。",
                "",
                "---",
                "生成于 ChemCal 工程计算模块",
            ])
            return f"{head}\n\n{body}\n\n{foot}"
        except Exception as e:                                   # noqa: BLE001
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        ReportExporter.export_docx(self, "板框压滤机过滤面积")

    def download_pdf_report(self):
        ReportExporter.export_pdf(self, "板框压滤机过滤面积")

    # ═══════════════════════ SVG 示意图 ═══════════════════════
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        return svg_text(x, y, text, size, color, bold, center)

    def _update_svg_diagram(self):
        """按当前输入刷新板框示意图（规则：属性一律 XML 语法）"""
        w, h = 380, 250
        A = 0.0
        delta = 0.0
        try:
            A = float(self.area_input.text())
            delta = float(self.cake_thk_input.text())
        except (TypeError, ValueError):
            pass

        p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
             f'width="{w}" height="{h}">',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']

        # 交替的 板(灰) / 滤室(浅蓝，宽度随滤饼厚度示意)
        n_cells = 5
        x0, y0 = 60, 70
        cell_h = 96
        gap = 4.0
        gap_px = max(3.0, min(22.0, delta * 0.55))
        cell_w = 10.0
        total = n_cells * cell_w + (n_cells - 1) * gap_px
        while total > 240 and cell_w > 4:
            cell_w -= 0.5
            total = n_cells * cell_w + (n_cells - 1) * gap_px
        x = x0
        for i in range(n_cells):
            p.append(f'<rect x="{x:.1f}" y="{y0}" width="{gap_px:.1f}" height="{cell_h}" '
                     f'fill="#dbe7f5" stroke="#4a6fa5" stroke-width="1"/>')
            x += gap_px
            if i < n_cells - 1:
                p.append(f'<rect x="{x:.1f}" y="{y0}" width="{cell_w:.1f}" height="{cell_h}" '
                         f'fill="#d5d8dc" stroke="#7f8c8d" stroke-width="1"/>')
                x += cell_w
        x_end = x
        p.append(self._text((x0 + x_end) / 2, y0 - 14, "板框组（蓝=滤室 灰=滤板）",
                            size=9, color="#4a6fa5", bold=True))

        # 进料总管（顶部）
        p.append(f'<line x1="{x0}" y1="{y0 - 4}" x2="{x_end:.1f}" y2="{y0 - 4}" '
                 f'stroke="#e67e22" stroke-width="3"/>')
        p.append(self._text(x0 - 4, y0 - 4, "进料", size=9, color="#e67e22",
                            bold=True, center=False))
        # 滤液出口（底部）
        p.append(f'<line x1="{x0}" y1="{y0 + cell_h + 4}" x2="{x_end:.1f}" '
                 f'y2="{y0 + cell_h + 4}" stroke="#2980b9" stroke-width="3"/>')
        p.append(self._text(x0 - 4, y0 + cell_h + 16, "滤液", size=9, color="#2980b9",
                            bold=True, center=False))

        # 尺寸标注：δ
        mid_x = (x0 + x_end) / 2
        p.append(f'<line x1="{x0}" y1="{y0 + cell_h + 30}" x2="{x_end:.1f}" '
                 f'y2="{y0 + cell_h + 30}" stroke="#888" stroke-width="1"/>')
        p.append(self._text(mid_x, y0 + cell_h + 44, f"A = {A:.2f} m²   δ = {delta:.1f} mm",
                            size=9, color="#333", bold=True))

        # 底部结果摘要
        r = self._last_result
        if r:
            p.append(self._text(w / 2, h - 32,
                                f"每批干渣 {r['m_solid']:.1f} kg   "
                                f"过滤 {r['t_f']:.1f} min   周期 {r['T_cycle']:.1f} min",
                                size=9, color="#1d6f42", bold=True))
            p.append(self._text(w / 2, h - 16,
                                f"产能 {r['solid_per_day']:.2f} t/d（干渣）",
                                size=10, color="#1d6f42", bold=True))
        else:
            p.append(self._text(w / 2, h - 24, "点击「计 算」查看结果",
                                size=9, color="#888"))
        p.append("</svg>")
        self.svg_widget.load("".join(p).encode("utf-8"))


def _split_preset_name(name):
    """从预设显示名中取机型代号（首段，如 XAZ50/800-U）"""
    return [seg for seg in name.split() if seg]


# 为动态导入提供简洁别名
filter_press_area_calculator = FilterPressAreaCalculator
