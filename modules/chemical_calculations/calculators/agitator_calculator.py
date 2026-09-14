"""
发酵搅拌功率 & kLa 传氧系数计算器

两种模式：
  1. 搅拌功率 — 不通气搅拌功率 → 通气功率衰减 → 搅拌电机选型
  2. kLa 传氧系数 — 通气量 → 体积传氧系数 → OTR → 需氧量校核

理论依据：
  - 不通气功率：P₀ = Np × ρ × n³ × d⁵
  - 通气功率：Pg = C × (P₀² × n × d³ / Q⁰·⁵⁶)⁰·⁴⁵
  - kLa：kLa = A × (Pg/V)ᵃ × (vs)ᵇ（van't Riet 关联式）
"""

import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QMessageBox, QScrollArea,
    QButtonGroup, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator

from calculator_base import CalculatorBase
from utils.docx_utils import ReportExporter
from app_styles import (INPUT_LABEL_STYLE, CLEAR_BTN_STYLE,
                        DOCX_BTN_STYLE, PDF_BTN_STYLE)


# ── 搅拌桨类型 ──
# (名称, 功率准数Np, 推荐说明)
IMPELLER_TYPES = {
    "Rushton 涡轮（六直叶）": (5.5, "高剪切，发酵罐标准配置"),
    "Rushton 涡轮（六弯叶）": (4.8, "剪切力略低于直叶"),
    "Rushton 涡轮（六箭叶）": (4.0, "介于涡轮和桨式之间"),
    "Pitched 桨（45°×4叶）":  (1.5, "轴向流，中等剪切"),
    "Pitched 桨（45°×6叶）":  (2.0, "轴向流，多叶版"),
    "Prop 推进式（3叶）":     (0.35, "轴向流，低剪切"),
    "锚式/框式":               (0.5, "高粘度，层流区"),
}

# ── 罐体长径比标准 ──
# (名称, 高径比 H/D, 说明)
ASPECT_RATIOS = {
    "标准发酵罐（H/D=2~3）":         2.5,
    "高径比发酵罐（H/D=3~4）":       3.5,
    "低矮罐（H/D=1~2）":             1.5,
    "自定义高径比":                   0,
}


class AgitatorCalculator(CalculatorBase):
    """发酵搅拌功率 & kLa 传氧系数计算器"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent, data_manager)
        self._last_results = {}
        self.setup_ui()
        self.setup_wheel_blocker()

    # ═══════════════════════════════════════════
    # UI 构建
    # ═══════════════════════════════════════════

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ── 左 ──
        scroll = QScrollArea()
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } "
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left = QWidget()
        left.setStyleSheet("")
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(15)

        desc = QLabel(
            "搅拌功率 & kLa 传氧系数计算 — 支持不通气/通气搅拌功率计算，\n"
            "以及基于 van't Riet 关联式的体积传氧系数估算。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc)

        # ── 模式选择 ──
        mode_group = QGroupBox("计算模式")
        mode_ly = QHBoxLayout(mode_group)
        self.mode_btn_group = QButtonGroup(self)
        self.mode_btns = {}
        for i, (name, tip) in enumerate([
            ("搅拌功率计算", "计算不通气/通气搅拌功率 + 电机选型"),
            ("kLa 传氧系数", "通气量 → kLa → OTR → 需氧校核"),
        ]):
            btn = CalculatorBase.make_mode_button(name, tip)
            self.mode_btns[name] = btn
            self.mode_btn_group.addButton(btn, i)
            mode_ly.addWidget(btn)
        self.mode_btn_group.buttonClicked.connect(self._on_mode_changed)
        left_layout.addWidget(mode_group)

        # ── 罐体参数 ──
        self._group_tank = CalculatorBase.make_group_box("罐体参数")
        tg = QGridLayout(self._group_tank)
        tg.setHorizontalSpacing(10)
        tg.setVerticalSpacing(12)
        tg.setColumnStretch(0, 4)
        tg.setColumnStretch(1, 8)
        tg.setColumnStretch(2, 5)
        r = 0

        def lbl(t):
            lb = QLabel(t)
            lb.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lb.setStyleSheet(INPUT_LABEL_STYLE)
            return lb

        def hint(t):
            h = QLabel(t)
            h.setStyleSheet("font-style: italic; color: #666;")
            h.setWordWrap(True)
            return h

        def inp(default="", validator=None):
            ie = QLineEdit(default)
            if validator:
                ie.setValidator(validator)
            return ie

        tg.addWidget(lbl("有效体积 (m³):"), r, 0)
        self.volume_input = inp("50", QDoubleValidator(0.1, 10000, 1))
        tg.addWidget(self.volume_input, r, 1)
        tg.addWidget(hint("发酵罐装料量"), r, 2)
        r += 1

        tg.addWidget(lbl("罐直径 (m):"), r, 0)
        self.diameter_input = inp("3.0", QDoubleValidator(0.1, 20, 2))
        tg.addWidget(self.diameter_input, r, 1)
        tg.addWidget(hint("内径"), r, 2)
        r += 1

        tg.addWidget(lbl("高径比 H/D:"), r, 0)
        self.aspect_combo = CalculatorBase.make_combo_box()
        self.aspect_combo.addItems(list(ASPECT_RATIOS.keys()))
        self.aspect_combo.setCurrentText("标准发酵罐（H/D=2~3）")
        self.aspect_combo.currentTextChanged.connect(self._on_aspect_changed)
        tg.addWidget(self.aspect_combo, r, 1)

        self.aspect_hint = hint("选择后自动计算液位高度")
        tg.addWidget(self.aspect_hint, r, 2)
        r += 1

        tg.addWidget(lbl("液位高度 (m):"), r, 0)
        self.liquid_height_input = inp("6.0", QDoubleValidator(0.1, 30, 2))
        tg.addWidget(self.liquid_height_input, r, 1)
        tg.addWidget(hint("装料液面距罐底"), r, 2)
        r += 1

        self._aspect_custom_row = r
        self.custom_aspect_label = lbl("自定义 H/D:")
        self.custom_aspect_label.setVisible(False)
        tg.addWidget(self.custom_aspect_label, r, 0)
        self.custom_aspect_input = inp("2.5", QDoubleValidator(1, 6, 1))
        self.custom_aspect_input.setVisible(False)
        self.custom_aspect_input.textChanged.connect(self._apply_custom_aspect)
        tg.addWidget(self.custom_aspect_input, r, 1)
        self.custom_aspect_hint = hint("输入自定义高径比")
        self.custom_aspect_hint.setVisible(False)
        tg.addWidget(self.custom_aspect_hint, r, 2)
        r += 1
        self._row_count_tank = r

        left_layout.addWidget(self._group_tank)

        # ── 搅拌参数 ──
        self._group_agitate = CalculatorBase.make_group_box("搅拌参数")
        ag = QGridLayout(self._group_agitate)
        ag.setHorizontalSpacing(10)
        ag.setVerticalSpacing(12)
        ag.setColumnStretch(0, 4)
        ag.setColumnStretch(1, 8)
        ag.setColumnStretch(2, 5)
        r = 0

        ag.addWidget(lbl("搅拌桨类型:"), r, 0)
        self.impeller_combo = CalculatorBase.make_combo_box()
        self.impeller_combo.addItems(list(IMPELLER_TYPES.keys()))
        ag.addWidget(self.impeller_combo, r, 1)
        self.impeller_hint = hint("Rushton 涡轮，标准配置")
        self.impeller_combo.currentTextChanged.connect(self._on_impeller_changed)
        ag.addWidget(self.impeller_hint, r, 2)
        r += 1

        ag.addWidget(lbl("搅拌桨直径 (m):"), r, 0)
        self.d_impeller_input = inp("1.0", QDoubleValidator(0.1, 10, 2))
        ag.addWidget(self.d_impeller_input, r, 1)
        self.d_impeller_hint = hint("推荐 D/T ≈ 0.3~0.5")
        ag.addWidget(self.d_impeller_hint, r, 2)
        r += 1

        ag.addWidget(lbl("搅拌转速 (rpm):"), r, 0)
        self.speed_input = inp("150", QDoubleValidator(1, 2000, 0))
        ag.addWidget(self.speed_input, r, 1)
        ag.addWidget(hint("常用 100~300 rpm"), r, 2)
        r += 1

        ag.addWidget(lbl("桨叶数:"), r, 0)
        self.num_impellers_input = inp("2", QDoubleValidator(1, 6, 0))
        ag.addWidget(self.num_impellers_input, r, 1)
        ag.addWidget(hint("发酵罐通常 2~3 层桨"), r, 2)
        r += 1

        ag.addWidget(lbl("液体密度 (kg/m³):"), r, 0)
        self.density_input = inp("1050", QDoubleValidator(500, 2000, 0))
        ag.addWidget(self.density_input, r, 1)
        ag.addWidget(hint("发酵液 ≈1000~1100 kg/m³"), r, 2)
        r += 1

        ag.addWidget(lbl("液体粘度 (mPa·s):"), r, 0)
        self.viscosity_input = inp("50", QDoubleValidator(0.1, 100000, 1))
        ag.addWidget(self.viscosity_input, r, 1)
        ag.addWidget(hint("发酵液 ≈10~200 mPa·s"), r, 2)
        r += 1

        self._row_count_ag = r
        left_layout.addWidget(self._group_agitate)

        # ── 通气参数（kLa 模式可见） ──
        self._group_aeration = CalculatorBase.make_group_box("通气参数")
        ar = QGridLayout(self._group_aeration)
        ar.setHorizontalSpacing(10)
        ar.setVerticalSpacing(12)
        ar.setColumnStretch(0, 4)
        ar.setColumnStretch(1, 8)
        ar.setColumnStretch(2, 5)
        r = 0

        ar.addWidget(lbl("通气量 (vvm):"), r, 0)
        self.vvm_input = inp("1.0", QDoubleValidator(0.1, 10, 2))
        ar.addWidget(self.vvm_input, r, 1)
        ar.addWidget(hint("体积通气比，常用 0.5~2.0 vvm"), r, 2)
        r += 1

        ar.addWidget(lbl("OUR (mmol/(L·h)):"), r, 0)
        self.our_input = inp("100", QDoubleValidator(1, 500, 0))
        ar.addWidget(self.our_input, r, 1)
        self.our_hint = hint("菌种耗氧速率，仅 kLa 模式使用")
        ar.addWidget(self.our_hint, r, 2)
        r += 1

        self._group_aeration.setVisible(False)
        left_layout.addWidget(self._group_aeration)

        left_layout.addStretch()
        scroll.setWidget(left)
        main_layout.addWidget(scroll, 2)

        # ── 右 ──
        right = QWidget()
        right.setMinimumWidth(300)
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(15)

        # ── 结果 ──
        result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(result_group)
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
        result_layout.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # ── 下载按钮行：清空 → DOCX → PDF ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        for name, style, cb in [
            ("清空", CLEAR_BTN_STYLE, self.clear_all),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            b = QPushButton(name)
            b.setStyleSheet(style)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.clicked.connect(cb)
            btn_layout.addWidget(b)
        right_layout.addLayout(btn_layout)

        # ── 计算按钮（最底部） ──
        calc_btn = CalculatorBase.make_calc_button("计 算")
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)

        main_layout.addWidget(right, 1)

        # ── 初始状态 ──
        self.mode_btns["搅拌功率计算"].setChecked(True)

    # ═══════════════════════════════════════════
    # 事件
    # ═══════════════════════════════════════════

    def _on_mode_changed(self, btn):
        is_kla = btn.text() == "kLa 传氧系数"
        self._group_aeration.setVisible(is_kla)

    def _on_aspect_changed(self, text):
        ratio = ASPECT_RATIOS.get(text, 0)
        if ratio > 0 and hasattr(self, 'diameter_input'):
            try:
                d = float(self.diameter_input.text() or 0)
                if d > 0:
                    h = d * ratio
                    self.liquid_height_input.setText(f"{h:.2f}")
                    self.aspect_hint.setText(f"已自动计算: {h:.2f} m")
            except ValueError:
                pass
        if text == "自定义高径比":
            # 整行联动显示，并立即用自定义值换算液位高度
            self.custom_aspect_label.setVisible(True)
            self.custom_aspect_input.setVisible(True)
            self.custom_aspect_hint.setVisible(True)
            self._apply_custom_aspect()
        else:
            self.custom_aspect_label.setVisible(False)
            self.custom_aspect_input.setVisible(False)
            self.custom_aspect_hint.setVisible(False)

    def _apply_custom_aspect(self):
        """自定义高径比 → 自动换算液位高度（使输入真正生效）"""
        try:
            d = float(self.diameter_input.text() or 0)
            ratio = float(self.custom_aspect_input.text() or 0)
            if d > 0 and ratio > 0:
                h = d * ratio
                self.liquid_height_input.setText(f"{h:.2f}")
                self.aspect_hint.setText(f"已按自定义 H/D={ratio:g} 计算: {h:.2f} m")
        except ValueError:
            pass

    def _on_impeller_changed(self, text):
        info = IMPELLER_TYPES.get(text, ("", ""))
        self.impeller_hint.setText(info[1] if len(info) > 1 else "")

    def clear_all(self):
        """清空输入并恢复出厂默认值"""
        defaults = {
            self.volume_input: "50",
            self.diameter_input: "3.0",
            self.liquid_height_input: "6.0",
            self.custom_aspect_input: "2.5",
            self.d_impeller_input: "1.0",
            self.speed_input: "150",
            self.num_impellers_input: "2",
            self.density_input: "1050",
            self.viscosity_input: "50",
            self.vvm_input: "1.0",
            self.our_input: "100",
        }
        for w, val in defaults.items():
            w.setText(val)
        self.result_text.clear()
        self._last_results = {}

    # ═══════════════════════════════════════════
    # 核心计算
    # ═══════════════════════════════════════════

    def calculate(self):
        try:
            mode_btn = self.mode_btn_group.checkedButton()
            mode = mode_btn.text() if mode_btn else "搅拌功率计算"

            # ── 读取公共参数 ──
            V = float(self.volume_input.text() or 0)
            D = float(self.diameter_input.text() or 0)
            H = float(self.liquid_height_input.text() or 0)
            d_imp = float(self.d_impeller_input.text() or 0)
            N = float(self.speed_input.text() or 0)
            n_imp = float(self.num_impellers_input.text() or 1)
            rho = float(self.density_input.text() or 1000)
            mu = float(self.viscosity_input.text() or 1)

            if mode == "搅拌功率计算":
                result = self._calc_power(V, D, H, d_imp, N, n_imp, rho, mu)
            else:
                vvm = float(self.vvm_input.text() or 0)
                our = float(self.our_input.text() or 0)
                result = self._calc_kla(V, D, H, d_imp, N, n_imp, rho, mu, vvm, our)

            self._last_results = result
            self._display_result(mode, result)

        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"请检查输入参数:\n{str(e)}")

    def _calc_power(self, V, D, H, d, N, n_imp, rho, mu):
        """搅拌功率计算"""
        # 桨型参数
        imp_name = self.impeller_combo.currentText()
        np_val = IMPELLER_TYPES.get(imp_name, (0, ""))[0]

        # 雷诺数 → 功率准数修正
        n_rps = N / 60  # rpm → rps
        Re = rho * n_rps * d**2 / (mu / 1000)  # mPa·s → Pa·s

        # 不通气功率
        P0 = np_val * rho * n_rps**3 * d**5 * n_imp
        P0_kw = P0 / 1000

        # 电机选型建议
        motor_power = P0_kw * 1.3  # 安全系数 1.3
        motor_choices = ["7.5", "11", "15", "18.5", "22", "30", "37", "45", "55",
                         "75", "90", "110", "132", "160", "200", "250", "315", "400"]
        rec_motor = "≥" + min((m for m in motor_choices if float(m) >= motor_power),
                              key=lambda x: float(x), default="400")

        # 通气功率估算（Michel & Miller 关联式，SI 单位）
        # Pg = 0.706 × (P0² × n × d³ / Q^0.56)^0.45   [W]
        # 其中 P0[W]、n[r/s]、d[m]、Q[m³/s]（vvm×V 为 m³/min，需除 60）
        vvm = float(self.vvm_input.text() or 1.0)
        Q = vvm * V / 60  # m³/s
        if Q > 0 and P0 > 0:
            Pg = 0.706 * (P0**2 * n_rps * d**3 / Q**0.56) ** 0.45
            Pg = min(Pg, P0)  # 物理上限：通气后功率不高于不通气功率
        else:
            Pg = P0  # 未通气或不通气工况
        Pg_kw = Pg / 1000

        return {
            "Re": Re,
            "Np": np_val,
            "P0_kW": P0_kw,
            "Pg_kW": Pg_kw,
            "motor_rec": rec_motor,
            "motor_power": motor_power,
            "n_rps": n_rps,
            "tip_speed": math.pi * d * n_rps,
            "PmV": P0_kw / V,
        }

    def _calc_kla(self, V, D, H, d, N, n_imp, rho, mu, vvm, our):
        """kLa 传氧系数计算"""
        # 先算搅拌功率
        power_data = self._calc_power(V, D, H, d, N, n_imp, rho, mu)

        Pg_kw = power_data["Pg_kW"]
        Pg_W = Pg_kw * 1000
        vol_m3 = V

        # 表观气速 (m/h)
        A_cross = math.pi * D**2 / 4
        Q_air = vvm * V  # m³/min
        vs = (Q_air / 60) / A_cross  # m/s

        # van't Riet 关联式：kLa = A × (Pg/V)^a × (vs)^b
        # 非牛顿/牛顿发酵液：A=0.026, a=0.4, b=0.5
        # 单位: kLa [1/s], Pg/V [W/m³], vs [m/s]（注意必须用 m/s，不能用 m/h）
        kLa_s = 0.026 * (Pg_W / vol_m3)**0.4 * vs**0.5  # 1/s
        kLa = kLa_s * 3600  # 1/h

        # OTRmax (最大传氧速率)
        # OTR = kLa × (C* - C)
        # 假设 30°C 水中饱和溶氧 C* ≈ 7.5 mg/L ≈ 0.234 mmol/L
        C_star_mmol = 0.234  # mmol/L
        CL_mmol = 0.05 * C_star_mmol  # 临界溶氧 ~5%
        OTR_max = kLa_s * (C_star_mmol - CL_mmol) * 3600  # mmol/(L·h)

        # OUR 校核
        safety = OTR_max / our if our > 0 else float('inf')

        # 需求通气量（OTR ∝ vs^0.5，即 ∝ vvm^0.5 → vvm_req = vvm×(OUR/OTRmax)²）
        q_air_required = vvm * (our / OTR_max) ** 2 if OTR_max > 0 else float('inf')

        return {
            "Pg_kW": Pg_kw,
            "vs_m_s": vs,
            "kLa_per_h": kLa,
            "kLa_per_s": kLa_s,
            "OTR_max": OTR_max,
            "OUR": our,
            "safety_ratio": safety,
            "q_vvm_req": q_air_required,
        }

    # ═══════════════════════════════════════════
    # 结果显示
    # ═══════════════════════════════════════════

    def _get_history_data(self):
        """提供历史记录数据"""
        inputs = {
            "计算模式": (self.mode_btn_group.checkedButton().text()
                        if self.mode_btn_group.checkedButton() else "搅拌功率计算"),
            "桨型": self.impeller_combo.currentText(),
            "罐体体积_m3": float(self.volume_input.text() or 0),
            "罐径_m": float(self.diameter_input.text() or 0),
            "液位高度_m": float(self.liquid_height_input.text() or 0),
            "桨径_m": float(self.d_impeller_input.text() or 0),
            "转速_rpm": float(self.speed_input.text() or 0),
            "桨层数": float(self.num_impellers_input.text() or 1),
            "密度_kg_m3": float(self.density_input.text() or 1000),
            "粘度_mPa_s": float(self.viscosity_input.text() or 1),
        }
        outputs = {}
        r = getattr(self, "_last_results", None) or {}
        for key, out_key in [("P0_kW", "不通气功率_kW"), ("Pg_kW", "通气功率_kW"),
                             ("motor_rec", "推荐电机_kW"), ("Re", "雷诺数"),
                             ("tip_speed", "桨端线速度_m_s")]:
            if key in r:
                v = r[key]
                outputs[out_key] = round(v, 3) if isinstance(v, float) else v
        if "kLa_per_h" in r:
            outputs["kLa_h_1"] = round(r["kLa_per_h"], 3)
        if "OTR_max" in r:
            outputs["OTR_max_mmol_L_h"] = round(r["OTR_max"], 2)
        return {"inputs": inputs, "outputs": outputs}

    def _display_result(self, mode, data):
        lines = []
        imp_name = self.impeller_combo.currentText()

        if "Re" in data:
            lines.append("═" * 50)
            lines.append("  搅拌功率计算结果")
            lines.append("═" * 50)
            lines.append(f"  桨型: {imp_name}")
            lines.append(f"  Np = {data['Np']:.1f}")
            lines.append(f"  雷诺数 Re = {data['Re']:.0f}")
            lines.append(f"  叶尖速度 = {data['tip_speed']:.2f} m/s")
            lines.append("")
            lines.append(f"  不通气功率 P₀ = {data['P0_kW']:.2f} kW")
            lines.append(f"  通气功率 Pg  = {data['Pg_kW']:.2f} kW")
            lines.append(f"  单位体积功率 = {data['PmV']:.2f} kW/m³")
            lines.append("")
            lines.append(f"  推荐电机功率: {data['motor_rec']} kW")
            lines.append(f"  (安全系数 1.3, 按不通气选型)")

        if "kLa_per_h" in data:
            lines.append("")
            lines.append("═" * 50)
            lines.append("  kLa 传氧系数计算结果")
            lines.append("═" * 50)
            lines.append(f"  通气功率 Pg = {data['Pg_kW']:.2f} kW")
            lines.append(f"  表观气速 vs = {data['vs_m_s']:.3f} m/s")
            lines.append("")
            lines.append(f"  kLa = {data['kLa_per_h']:.1f} /h")
            lines.append(f"      = {data['kLa_per_s']:.4f} /s")
            lines.append("")
            lines.append(f"  OTRmax = {data['OTR_max']:.1f} mmol/(L·h)")
            lines.append(f"  OUR    = {data['OUR']:.0f} mmol/(L·h)")
            lines.append(f"  安全系数 = {data['safety_ratio']:.2f}")
            if data['safety_ratio'] >= 1.5:
                lines.append("  ✅ 供氧充足 (安全系数 ≥ 1.5)")
            elif data['safety_ratio'] >= 1.0:
                lines.append("  ⚠️ 供氧临界 (1.0~1.5，建议提高通气量)")
            else:
                lines.append("  ❌ 供氧不足，请增大通气量或提高搅拌转速")
            lines.append("")
            if data['q_vvm_req'] > 0:
                lines.append(f"  需求通气量: {data['q_vvm_req']:.2f} vvm")
            lines.append("")
            lines.append("  van't Riet 关联式: kLa = 0.026×(Pg/V)^0.4×vs^0.5")
            lines.append("  基准: 30°C, C*=7.5 mg/L, CL=5%C*")

        self.result_text.setPlainText("\n".join(lines))

    # ── 报告导出 ──

    def get_project_info(self):
        return {
            "project_name": "搅拌功率 & kLa 传氧系数计算",
            "calculator_name": "搅拌功率 & kLa 传氧系数计算器",
            "version": "1.0",
            "description": "不通气/通气搅拌功率计算 + 电机选型 + van't Riet 关联式 kLa 传氧系数与需氧校核"
        }

    def generate_report(self):
        """生成计算书文本（供 ReportExporter 使用）"""
        if not self._last_results:
            return "尚未进行计算。"
        lines = ["搅拌功率 & kLa 传氧系数计算书", "=" * 50]
        lines.append(self.result_text.toPlainText())
        return "\n".join(lines)

    def download_docx_report(self):
        """生成 DOCX 计算书"""
        ReportExporter.export_docx(self, "搅拌功率&kLa计算")

    def download_pdf_report(self):
        """生成 PDF 计算书"""
        ReportExporter.export_pdf(self, "搅拌功率&kLa计算")
