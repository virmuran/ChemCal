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
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QScrollArea,
    QButtonGroup, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator

from calculator_base import CalculatorBase
from app_styles import (COMBOBOX_STYLE, GROUP_STYLE, MODE_BUTTON_STYLE,
                        CALC_BUTTON_STYLE, SCROLL_AREA_STYLE,
                        INPUT_LABEL_STYLE, CLEAR_BTN_STYLE,
                        DOCX_BTN_STYLE, PDF_BTN_STYLE)
from common_constants import G, WATER_DENSITY


# ── 搅拌桨类型 ──
# (名称, 功率准数Np, 推荐说明)
IMPELLER_TYPES = {
    "Rushton 涡轮（六直叶）": (5.5, "高剪切，发酵罐标准配置"),
    "Rushton 涡轮（六弯叶）": (4.8, "剪切力略低于直叶"),
    "Rushton 涡轮（六箭叶）": (4.0, "介于涡轮和桨式之间"),
    " pitched 桨（45°×4叶）":  (1.5, "轴向流，中等剪切"),
    " pitched 桨（45°×6叶）":  (2.0, "轴向流，多叶版"),
    " prop 推进式（3叶）":     (0.35, "轴向流，低剪切"),
    "锚式/框式":               (0.5, "高粘度，层流区"),
}

# ── 罐体长径比标准（仅作提示） ──
ASPECT_HINT = {
    (0, 2):   "低矮罐",
    (2, 3):   "标准发酵罐",
    (3, 4):   "高径比发酵罐",
    (4, 99):  "超细长罐（少见）",
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
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left = QWidget()
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

        # ── 液位高度：根据 V、D 自动派生（圆柱形：H = 4V/πD²） ──
        tg.addWidget(lbl("液位高度 (m):"), r, 0)
        self.liquid_height_label = QLabel("—")
        self.liquid_height_label.setStyleSheet(
            "padding: 6px 10px; background: #f5f7fa; border: 1px solid #ddd; "
            "border-radius: 3px; color: #333; font-size: 13px;"
        )
        tg.addWidget(self.liquid_height_label, r, 1)
        tg.addWidget(hint("由 V 和 D 自动算出"), r, 2)
        r += 1

        # ── 高径比：同样派生 ──
        tg.addWidget(lbl("高径比 H/D:"), r, 0)
        self.aspect_ratio_label = QLabel("—")
        self.aspect_ratio_label.setStyleSheet(
            "padding: 6px 10px; background: #f5f7fa; border: 1px solid #ddd; "
            "border-radius: 3px; color: #333; font-size: 13px;"
        )
        tg.addWidget(self.aspect_ratio_label, r, 1)
        self.aspect_hint = hint("标准发酵罐 H/D ≈ 2~3")
        tg.addWidget(self.aspect_hint, r, 2)
        r += 1

        self._row_count_tank = r

        # V / D 任一变化 → 重算 H、H/D、桨径、层数
        self.volume_input.textChanged.connect(self._update_tank_geometry)
        self.diameter_input.textChanged.connect(self._update_tank_geometry)

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
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(15)

        # ── 计算按钮 ──
        calc_btn = CalculatorBase.make_calc_button()
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)

        # ── 结果 ──
        result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("font-size: 12px;")
        result_layout.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # ── 底部按钮 ──
        btn_layout = QHBoxLayout()
        for name, style, cb in [
            ("清空", CLEAR_BTN_STYLE, self.clear_all),
            ("下载 DOCX", DOCX_BTN_STYLE, lambda: self.download_docx_report("搅拌功率&kLa计算")),
            ("下载 PDF", PDF_BTN_STYLE, lambda: self.download_pdf_report("搅拌功率&kLa计算")),
        ]:
            b = QPushButton(name)
            b.setStyleSheet(style)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.clicked.connect(cb)
            btn_layout.addWidget(b)
        right_layout.addLayout(btn_layout)

        right_layout.addStretch()
        main_layout.addWidget(right, 1)

        # ── 初始状态 ──
        self.mode_btns["搅拌功率计算"].setChecked(True)
        # 所有控件已就绪，执行一次初始派生
        self._update_tank_geometry()

    # ═══════════════════════════════════════════
    # 事件
    # ═══════════════════════════════════════════

    def _on_mode_changed(self, btn):
        is_kla = btn.text() == "kLa 传氧系数"
        self._group_aeration.setVisible(is_kla)

    def _update_tank_geometry(self):
        """V 或 D 改变时，自动派生 H、H/D，并更新搅拌桨直径和桨叶层数建议"""
        try:
            v = float(self.volume_input.text() or 0)
            d = float(self.diameter_input.text() or 0)
            if v > 0 and d > 0:
                h = 4.0 * v / (math.pi * d * d)
                ratio = h / d
                self.liquid_height_label.setText(f"{h:.2f} m")
                self.aspect_ratio_label.setText(f"{ratio:.2f}")

                # 罐型提示
                for (lo, hi), label in ASPECT_HINT.items():
                    if lo <= ratio < hi:
                        self.aspect_hint.setText(f"{label}（H/D ≈ {ratio:.3f}）")
                        break

                # ── 搅拌桨直径：d_impeller = D × 0.33（Rushton 标准比） ──
                d_rec = d * 0.333
                self.d_impeller_input.setText(f"{d_rec:.2f}")
                self.d_impeller_hint.setText(
                    f"自动填充 d≈D/3={d_rec:.2f}m（手动可改）"
                )

                # ── 桨叶层数：根据 H/D 自动建议 ──
                if ratio < 1.5:
                    layers = 1
                elif ratio < 2.5:
                    layers = 2
                elif ratio < 3.5:
                    layers = 3
                else:
                    layers = 4
                self.num_impellers_input.setText(str(layers))
            else:
                self.liquid_height_label.setText("—")
                self.aspect_ratio_label.setText("—")
                self.aspect_hint.setText("标准发酵罐 H/D ≈ 2~3")
                self.d_impeller_hint.setText("推荐 D/d ≈ 3")
        except ValueError:
            self.liquid_height_label.setText("—")
            self.aspect_ratio_label.setText("—")

    def _on_impeller_changed(self, text):
        """搅拌桨类型切换 → 更新提示文案"""
        info = IMPELLER_TYPES.get(text, ("", ""))
        self.impeller_hint.setText(info[1] if len(info) > 1 else "")

    def _validate_geometry(self, V, D, H, d_imp, N) -> list:
        """校验输入数据是否在合理范围内，返回警告列表（空 = 无问题）"""
        warnings = []
        h_d = H / D if D > 0 else 0

        # 1. 高径比
        if h_d < 0.2:
            warnings.append(
                f"高径比 H/D = {h_d:.3f}，罐体过于扁平（H = {H:.2f}m, D = {D:.2f}m）。\n"
                f"  请检查：直径是否偏大、或装料体积是否偏小"
            )
        elif h_d > 6:
            warnings.append(
                f"高径比 H/D = {h_d:.2f}，罐体过于细长，搅拌效果可能不理想"
            )

        # 2. 液位高度绝对值
        if H < 0.5:
            warnings.append(
                f"液位高度 H = {H:.3f}m < 0.5m，几乎为薄层，无法正常搅拌"
            )

        # 3. 搅拌桨直径 vs 罐径
        if d_imp > 0 and D > 0:
            d_ratio = d_imp / D
            if d_ratio > 0.6:
                warnings.append(
                    f"搅拌桨直径 d = {d_imp:.2f}m 大于罐径的 60%（d/D = {d_ratio:.2f}），\n"
                    f"  桨叶可能与罐壁干涉"
                )
            elif d_ratio < 0.2:
                warnings.append(
                    f"搅拌桨直径 d = {d_imp:.2f}m 小于罐径的 20%（d/D = {d_ratio:.2f}），\n"
                    f"  桨叶过小，罐壁附近混合效果差"
                )

        # 4. 转速
        if N > 0 and d_imp > 0:
            tip = math.pi * d_imp * N / 60
            if tip > 8:
                warnings.append(
                    f"叶尖速度 = {tip:.1f} m/s > 8 m/s（严重剪切、气蚀风险）"
                )
            elif tip > 6:
                warnings.append(
                    f"叶尖速度 = {tip:.1f} m/s（偏高，注意剪切敏感菌种）"
                )
            elif tip < 0.5:
                warnings.append(
                    f"叶尖速度 = {tip:.1f} m/s < 0.5 m/s（搅拌弱，混合可能不足）"
                )

        return warnings
        info = IMPELLER_TYPES.get(text, ("", ""))
        self.impeller_hint.setText(info[1] if len(info) > 1 else "")

    def clear_all(self):
        """清空所有输入"""
        for w in self.findChildren(QLineEdit):
            w.clear()
        self.result_text.clear()

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
            # 液位高度 H 由 V 和 D 自动派生（圆柱形：H = 4V/πD²）
            H = 4.0 * V / (math.pi * D * D) if V > 0 and D > 0 else 0
            d_imp = float(self.d_impeller_input.text() or 0)
            N = float(self.speed_input.text() or 0)
            n_imp = float(self.num_impellers_input.text() or 1)
            rho = float(self.density_input.text() or 1000)
            mu = float(self.viscosity_input.text() or 1)

            # ── 输入合理性校验 ──
            warnings = self._validate_geometry(V, D, H, d_imp, N)
            if warnings:
                wmsg = "⚠ 输入可能不合理：\n\n" + "\n".join(f"  • {w}" for w in warnings)
                wmsg += "\n\n  是否仍要继续计算？"
                reply = QMessageBox.warning(
                    self, "输入校验", wmsg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

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

        # ── 电机选型（分步考虑效率 & 余量） ──
        # 搅拌轴功率 P₀ → 密封损失 → 减速机 → 电机输出 → 电机输入 → 设计余量
        eta_seal = 0.95     # 机械密封/填料函效率
        eta_gearbox = 0.92  # 减速机（摆线/平行轴）传动效率
        eta_motor = 0.92    # 电机效率（IE3 等级）
        k_safety = 1.2      # 设计余量（启动力矩、负荷波动）
        motor_power = P0_kw / (eta_seal * eta_gearbox * eta_motor) * k_safety
        # motor_power ≈ P0_kw × 1.49（比之前 1.3 更保守）

        motor_choices = ["7.5", "11", "15", "18.5", "22", "30", "37", "45", "55",
                         "75", "90", "110", "132", "160", "200", "250", "315", "400"]
        rec_motor = "≥" + min((m for m in motor_choices if float(m) >= motor_power),
                              key=lambda x: float(x), default="400")

        # 通气功率估算（假设 vvm=1.0）
        vvm = float(self.vvm_input.text() or 1.0)
        Q = vvm * V  # m³/min
        Pg_factor = (P0**2 * n_rps * d**3 / (Q / 60)**0.56) ** 0.45
        Pg = min(P0 * Pg_factor, P0 * 0.7) if P0 > 0 else 0
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
        vs_mh = vs * 3600  # m/h

        # van't Riet 关联式：kLa = A × (Pg/V)^a × (vs)^b
        # 非牛顿/牛顿发酵液：A=0.026, a=0.4, b=0.5
        kLa = 0.026 * (Pg_W / vol_m3)**0.4 * (vs_mh)**0.5  # 1/h
        kLa_s = kLa / 3600  # 1/s

        # OTRmax (最大传氧速率)
        # OTR = kLa × (C* - C)
        # 假设 30°C 水中饱和溶氧 C* ≈ 7.5 mg/L ≈ 0.234 mmol/L
        C_star_mmol = 0.234  # mmol/L
        CL_mmol = 0.05 * C_star_mmol  # 临界溶氧 ~5%
        OTR_max = kLa_s * (C_star_mmol - CL_mmol) * 3600  # mmol/(L·h)

        # OUR 校核
        safety = OTR_max / our if our > 0 else float('inf')

        # 需求通气量
        q_air_required = our / OTR_max * vvm if OTR_max > 0 else float('inf')

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
            lines.append(f"  不通气功率 P₀（轴功率）= {data['P0_kW']:.2f} kW")
            lines.append(f"  通气功率 Pg = {data['Pg_kW']:.2f} kW")
            lines.append(f"  单位体积功率 = {data['PmV']:.2f} kW/m³")
            lines.append("")
            lines.append("  电机选型分解：")
            lines.append(f"    P₀ = {data['P0_kW']:.2f} kW")
            lines.append(f"    ÷ η_密封(0.95) ÷ η_减速机(0.92) ÷ η_电机(0.92) × K_余量(1.2)")
            lines.append(f"    = {data['P0_kW']:.2f} / 0.80 × 1.2 = {data['motor_power']:.2f} kW")
            lines.append(f"  → 推荐电机: {data['motor_rec']} kW")

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

    def generate_report(self):
        """生成计算书文本（供 ReportExporter 使用）"""
        lines = []
        if not self._last_results:
            return ""
        lines.append("搅拌功率 & kLa 传氧系数计算书")
        self._display_result(
            self.mode_btn_group.checkedButton().text() if self.mode_btn_group.checkedButton() else "",
            self._last_results
        )
        lines.append(self.result_text.toPlainText())
        return "\n".join(lines)
