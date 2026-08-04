"""
储罐壁厚计算器 — GB 50341 + NB/T 47003 双标准

  - GB 50341-2014：一英尺法逐圈计算，适用于大、中型常压储罐
  - NB/T 47003.1-2009：压力容器圆筒公式，适用于小型承压罐 / 微正压罐

支持固定顶 / 浮顶 / 内浮顶三种罐型，自动计算底板、顶板厚度和材料重量。
"""

import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QScrollArea,
    QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator

from calculator_base import CalculatorBase
from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, SCROLL_AREA_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)
from common_constants import G

# ═══════════════════════════════════════════════════════════════
#  常量数据
# ═══════════════════════════════════════════════════════════════

# ── 计算标准 ──
STANDARDS = {
    "GB 50341-2014  (常压储罐·一英尺法)": "gb50341",
    "NB/T 47003.1-2009  (压力容器·圆筒公式)": "nb47003",
}

# ── 材料数据库 ──
# (密度 kg/m³, S_d 设计许用应力 MPa, S_t 水压试验许用应力 MPa)
MATERIAL_DB = {
    "Q235B":    (7850, 157, 171),
    "Q245R":    (7850, 148, 163),
    "Q345R":    (7850, 208, 227),
    "Q370R":    (7850, 218, 238),
    "S30408 (304)":  (7930, 137, 137),
    "S31603 (316L)": (8000, 115, 115),
    "自定义":    (7850, None, None),
}

# ── 焊缝系数 ──
WELD_EFF = {
    "双面焊 100% RT":           1.00,
    "双面焊 局部 RT":           0.85,
    "单面焊 带垫板 局部 RT":    0.80,
    "单面焊 不带垫板":          0.70,
}

# ── 最小壁厚 — GB 50341 (D < 6m 参考 NB/T 47003) ──
# (罐径上限 m, 最小厚度 mm, 标准名)
GB50341_MIN_THICKNESS = [
    (6,   4),    # D < 6m → 参照压力容器规范，取 4mm
    (15,  5),
    (36,  6),
    (60,  7),
    (75,  8),
    (90,  9),
    (float("inf"), 10),
]

# ── 最小壁厚 — NB/T 47003.1-2009 ──
# 碳钢 ≥ 3mm，不锈钢 ≥ 2mm（不得小于 3mm 用于碳钢制压力容器壳体）
# (材料类型关键字, 最小 mm)
NB47003_CARBON_STEEL = 3
NB47003_STAINLESS = 2

# ── 标准钢板规格 (mm) ──
STD_PLATE_THICKNESSES = [
    4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 22,
    24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 45,
]

# ── 罐型 ──
TANK_TYPES = ["固定顶（拱顶/锥顶）", "外浮顶", "内浮顶"]


# ═══════════════════════════════════════════════════════════════
#  计算器主体
# ═══════════════════════════════════════════════════════════════

class AtmosphericTankThicknessCalculator(CalculatorBase):
    """储罐壁厚计算器 v1.1 — 双标准"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent, data_manager)
        self._last_results = None
        self._input_widgets = {}            # name → widget
        self._conditional_widgets = []       # NB/T 47003 专属控件 (name, lbl, unit)
        self.setup_ui()
        self.setup_wheel_blocker()
        # 初始：GB 50341 默认 → 隐藏 NB 专属字段
        self._on_standard_changed("GB 50341-2014  (常压储罐·一英尺法)")

    # ═════════════════════════════════════════════════════════
    #  UI 搭建
    # ═════════════════════════════════════════════════════════

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(SCROLL_AREA_STYLE)
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(12)

        self._create_basic_group(left_layout)
        self._create_geometry_group(left_layout)
        self._create_pressure_group(left_layout)   # NB/T 47003 专属（动态显隐）
        self._create_material_group(left_layout)

        calc_btn = QPushButton("计  算")
        calc_btn.setStyleSheet(CALC_BUTTON_STYLE)
        calc_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calc_btn.setMinimumHeight(50)
        calc_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        calc_btn.clicked.connect(self.calculate)
        left_layout.addWidget(calc_btn)
        left_layout.addStretch()

        scroll_left.setWidget(left_widget)

        # ── 右侧 ──
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(12)

        result_group = QGroupBox("计算结果")
        result_group.setStyleSheet(GROUP_STYLE)
        rl = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setStyleSheet("font-size: 13px; font-family: Consolas, 'Microsoft YaHei';")
        rl.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        for label, style, slot in [
            ("清空", CLEAR_BTN_STYLE, self.clear),
            ("下载 DOCX", DOCX_BTN_STYLE, self._on_download_docx),
            ("下载 PDF", PDF_BTN_STYLE, self._on_download_pdf),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        right_layout.addLayout(btn_layout)

        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

    def _add_input_row(self, grid: QGridLayout, row: int, label: str, name: str,
                        unit: str = "", default: str = "", tooltip: str = "",
                        readonly: bool = False, widget_type: str = "lineedit",
                        hidden: bool = False):
        """添加一行 标签 + 输入/下拉 + 单位。hidden=True 则初始隐藏整行"""
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
        if tooltip:
            lbl.setToolTip(tooltip)
        lbl.setObjectName(f"lbl_{name}")

        if widget_type == "combo":
            w = QComboBox()
            w.setStyleSheet(COMBOBOX_STYLE)
        else:
            w = QLineEdit(default)
            w.setPlaceholderText(tooltip or f"请输入{label}")
            if readonly:
                w.setReadOnly(True)
                w.setStyleSheet("background-color: #f0f0f0;")
            v = QDoubleValidator()
            v.setDecimals(0 if name.endswith("_int") else 3)
            w.setValidator(v)

        w.setObjectName(f"w_{name}")

        unit_lbl = QLabel(unit)
        unit_lbl.setStyleSheet("color: #666;")
        unit_lbl.setObjectName(f"unit_{name}")

        grid.addWidget(lbl, row, 0)
        grid.addWidget(w, row, 1)
        grid.addWidget(unit_lbl, row, 2)

        self._input_widgets[name] = w
        if hidden:
            lbl.hide(); w.hide(); unit_lbl.hide()

        return w

    def _create_basic_group(self, layout: QVBoxLayout):
        grp = QGroupBox("设计参数")
        grp.setStyleSheet(GROUP_STYLE)
        g = QGridLayout(grp)
        g.setSpacing(12)
        g.setColumnStretch(0, 4)
        g.setColumnStretch(1, 8)
        g.setColumnStretch(2, 5)

        # 0 — 计算标准
        self._add_input_row(g, 0, "计算标准", "standard", widget_type="combo")
        cb = self._input_widgets["standard"]
        cb.addItems(list(STANDARDS.keys()))
        cb.currentTextChanged.connect(self._on_standard_changed)

        # 1 — 储罐类型
        self._add_input_row(g, 1, "储罐类型", "tank_type", widget_type="combo")
        self._input_widgets["tank_type"].addItems(TANK_TYPES)

        # 2 — 储液密度
        self._add_input_row(g, 2, "储液密度", "liquid_density",
                            unit="kg/m³", default="1000",
                            tooltip="储存介质的密度，水=1000")

        # 3 — 腐蚀裕量
        self._add_input_row(g, 3, "腐蚀裕量", "corrosion_allowance",
                            unit="mm", default="1.5",
                            tooltip="设计使用年限内的腐蚀裕量，一般碳钢取1.5~3mm")

        layout.addWidget(grp)

    def _create_geometry_group(self, layout: QVBoxLayout):
        grp = QGroupBox("几何参数")
        grp.setStyleSheet(GROUP_STYLE)
        g = QGridLayout(grp)
        g.setSpacing(12)
        g.setColumnStretch(0, 4)
        g.setColumnStretch(1, 8)
        g.setColumnStretch(2, 5)

        self._add_input_row(g, 0, "储罐内径", "tank_diameter",
                            unit="m", default="",
                            tooltip="储罐内径 D（m）")
        self._add_input_row(g, 1, "罐壁总高", "tank_height",
                            unit="m", default="",
                            tooltip="罐壁总高度（底板到顶圈顶部）")
        self._add_input_row(g, 2, "设计液位", "liquid_level",
                            unit="m", default="",
                            tooltip="最高设计液位，一般取罐壁总高的 90%~95%")
        self._add_input_row(g, 3, "圈数（层数）", "num_courses",
                            unit="圈", default="6",
                            tooltip="罐壁由几圈钢板组成。NB/T 47003 模式可设为 1")

        layout.addWidget(grp)

    def _create_pressure_group(self, layout: QVBoxLayout):
        """NB/T 47003 专属参数组 — 默认隐藏"""
        self.pressure_group = QGroupBox("压力参数  (NB/T 47003)")
        self.pressure_group.setStyleSheet(GROUP_STYLE)
        g = QGridLayout(self.pressure_group)
        g.setSpacing(12)
        g.setColumnStretch(0, 4)
        g.setColumnStretch(1, 8)
        g.setColumnStretch(2, 5)

        self._add_input_row(g, 0, "设计压力 Pc", "design_pressure_pc",
                            unit="MPa", default="0",
                            tooltip="设计压力（表压 MPa）。常压罐 = 0，微正压罐填入正压值",
                            hidden=True)
        self._add_input_row(g, 1, "设计温度 Td", "design_temp_td",
                            unit="°C", default="50",
                            tooltip="设计温度，用于选择材料许用应力。常温取 50°C",
                            hidden=True)

        # 记录这两个控件以便统一显隐
        self._conditional_widgets = [
            ("design_pressure_pc", "设计压力 Pc", "MPa"),
            ("design_temp_td", "设计温度 Td", "°C"),
        ]

        self.pressure_group.hide()
        layout.addWidget(self.pressure_group)

    def _create_material_group(self, layout: QVBoxLayout):
        grp = QGroupBox("材料参数")
        grp.setStyleSheet(GROUP_STYLE)
        g = QGridLayout(grp)
        g.setSpacing(12)
        g.setColumnStretch(0, 4)
        g.setColumnStretch(1, 8)
        g.setColumnStretch(2, 5)

        self._add_input_row(g, 0, "罐壁材质", "material_grade", widget_type="combo")
        cb = self._input_widgets["material_grade"]
        cb.addItems(list(MATERIAL_DB.keys()))
        cb.currentTextChanged.connect(self._on_material_changed)

        self._add_input_row(g, 1, "许用应力 [σ]", "allowable_stress_d",
                            unit="MPa", default="", readonly=True,
                            tooltip="设计温度下的许用应力，选择材质后自动填入")

        self._add_input_row(g, 2, "水压试验 S_t", "allowable_stress_t",
                            unit="MPa", default="", readonly=True,
                            tooltip="水压试验许用应力，选择材质后自动填入")

        self._add_input_row(g, 3, "钢板密度", "steel_density",
                            unit="kg/m³", default="", readonly=True,
                            tooltip="选择材质后自动填入")

        self._add_input_row(g, 4, "焊缝系数", "weld_efficiency", widget_type="combo")
        self._input_widgets["weld_efficiency"].addItems(list(WELD_EFF.keys()))
        self._input_widgets["weld_efficiency"].setCurrentText("双面焊 局部 RT")

        layout.addWidget(grp)

    # ═════════════════════════════════════════════════════════
    #  标准切换
    # ═════════════════════════════════════════════════════════

    def _on_standard_changed(self, text: str):
        """切换标准 → 显隐压力参数组"""
        mode = STANDARDS.get(text, "gb50341")
        visible = (mode == "nb47003")

        # 显隐整组
        self.pressure_group.setVisible(visible)

        # 显隐组内控件（layout 移除 widget 后不会自动隐藏，用 show/hide）
        for name, _, _ in self._conditional_widgets:
            for suffix in ("lbl_", "w_", "unit_"):
                obj = self.findChild(QLabel if suffix.startswith("lbl") else QLineEdit if suffix.startswith("w") else QLabel, f"{suffix}{name}")
                if obj:
                    obj.setVisible(visible)

        self._current_mode = mode

    def _on_material_changed(self, name: str):
        data = MATERIAL_DB.get(name)
        if data is None:
            return
        density, sd, st = data
        if sd is not None:
            self._input_widgets["allowable_stress_d"].setText(str(sd))
            self._input_widgets["allowable_stress_t"].setText(str(st))
            self._input_widgets["steel_density"].setText(str(density))
        else:
            for k in ("allowable_stress_d", "allowable_stress_t", "steel_density"):
                w = self._input_widgets[k]
                w.setReadOnly(False)
                w.setStyleSheet("")
                w.setText("")

    # ═════════════════════════════════════════════════════════
    #  工具方法
    # ═════════════════════════════════════════════════════════

    @staticmethod
    def _get_val(widgets: dict, key: str, default=0.0) -> float:
        w = widgets.get(key)
        if w is None:
            return default
        if isinstance(w, QComboBox):
            return 0.0
        text = w.text().strip()
        if not text:
            return default
        try:
            return float(text)
        except ValueError:
            return default

    @staticmethod
    def _get_combo(widgets: dict, key: str) -> str:
        w = widgets.get(key)
        if w is None:
            return ""
        return w.currentText() if isinstance(w, QComboBox) else ""

    @staticmethod
    def _round_up_plate(thickness_mm: float) -> float:
        for t in STD_PLATE_THICKNESSES:
            if t >= thickness_mm - 0.001:
                return t
        return STD_PLATE_THICKNESSES[-1]

    def _min_thickness_gb50341(self, D: float) -> float:
        for limit, t_min in GB50341_MIN_THICKNESS:
            if D <= limit:
                return t_min
        return 10

    def _is_stainless(self, mat: str) -> bool:
        return "304" in mat or "316" in mat or "SS" in mat.upper()

    # ═════════════════════════════════════════════════════════
    #  计算
    # ═════════════════════════════════════════════════════════

    def calculate(self):
        w = self._input_widgets

        # ── 公共输入 ──
        D = self._get_val(w, "tank_diameter")
        H_total = self._get_val(w, "tank_height")
        H_liquid = self._get_val(w, "liquid_level")
        n_courses = int(self._get_val(w, "num_courses", 6))
        rho_l = self._get_val(w, "liquid_density", 1000)
        CA = self._get_val(w, "corrosion_allowance", 1.5)
        S_d = self._get_val(w, "allowable_stress_d")
        S_t = self._get_val(w, "allowable_stress_t")
        rho_s = self._get_val(w, "steel_density", 7850)
        tank_type = self._get_combo(w, "tank_type")
        E_w = WELD_EFF.get(self._get_combo(w, "weld_efficiency"), 0.85)
        mat_grade = self._get_combo(w, "material_grade")
        mode = getattr(self, "_current_mode", "gb50341")

        # NB/T 47003 专属
        Pc = self._get_val(w, "design_pressure_pc", 0)       # 设计压力 MPa
        Td = self._get_val(w, "design_temp_td", 50)

        # ── 输入校验 ──
        errors = []
        if D <= 0:       errors.append("储罐内径必须 > 0")
        if H_total <= 0: errors.append("罐壁总高必须 > 0")
        if H_liquid <= 0: H_liquid = H_total * 0.9
        if H_liquid > H_total: errors.append("设计液位不可大于罐壁总高")
        if n_courses <= 0: errors.append("圈数必须 ≥ 1")
        if S_d <= 0 or S_t <= 0: errors.append("请选择罐壁材质以获取许用应力")
        if rho_l <= 0:   errors.append("储液密度必须 > 0")
        if rho_l > 10000: rho_l = 1000
        if errors:
            self.result_text.setPlainText("⚠ 输入错误：\n" + "\n".join(f"  • {e}" for e in errors))
            return

        G_sg = rho_l / 1000.0
        course_height = H_total / n_courses
        lines = []

        # ── 表头 ──
        std_label = "GB 50341-2014 一英尺法" if mode == "gb50341" else "NB/T 47003.1-2009 圆筒公式"
        lines.append("═" * 60)
        lines.append(f"  储罐壁厚计算书 — {tank_type}")
        lines.append(f"  计算标准：{std_label}")
        lines.append("═" * 60)
        lines.append(f"  内径 D = {D:.2f} m  |  罐高 H = {H_total:.2f} m  |  液位 = {H_liquid:.2f} m")
        lines.append(f"  圈数×圈高 = {n_courses} × {course_height:.3f} m")
        lines.append(f"  储液密度 = {rho_l:.0f} kg/m³ (SG={G_sg:.3f})")
        lines.append(f"  腐蚀裕量 = {CA:.1f} mm  |  材质 = {mat_grade}")
        lines.append(f"  [σ] = {S_d:.0f} MPa  |  S_t = {S_t:.0f} MPa  |  焊缝系数 E = {E_w:.2f}")
        if mode == "nb47003":
            lines.append(f"  设计压力 Pc = {Pc:.4f} MPa  |  设计温度 Td = {Td:.0f} °C")
            # 液压试验压力
            p_test = max(1.25 * Pc, Pc + 0.1)
            lines.append(f"  液压试验压力 p_T ≥ {p_test:.4f} MPa")
        lines.append("─" * 60)

        lines.append(f"  {'圈号':>4s} │{'液柱(m)':>9s} │{'p_calc(MPa)':>12s} │{'计算(mm)':>9s} │{'须用(mm)':>9s} │{'名义(mm)':>9s} │  校核")
        lines.append("  " + "─" * 56)

        course_results = []
        total_weight = 0.0

        for i in range(n_courses):
            bottom_elev = i * course_height
            design_point = bottom_elev + 0.3
            liquid_head = max(H_liquid - design_point, 0)

            if mode == "gb50341":
                # ── GB 50341 一英尺法 ──
                t_calc = 4.9 * D * liquid_head * G_sg / (S_d * E_w)

                # 水压试验
                if rho_l <= 1000:
                    t_hydro_check = 4.9 * D * liquid_head * 1.0 / (S_t * E_w)
                else:
                    hydro_head = max(H_liquid * G_sg - design_point, 0)
                    t_hydro_check = 4.9 * D * hydro_head * 1.0 / (S_t * E_w)

                t_required = max(t_calc, t_hydro_check)
                t_min_noca = self._min_thickness_gb50341(D)

                p_calc_label = " — "   # 不显示 p_calc

            else:
                # ── NB/T 47003 圆筒公式 ──
                # 计算压力 = 设计压力 + 液柱静压 (MPa)
                p_hydro = rho_l * G * liquid_head / 1_000_000   # MPa
                p_calc = Pc + p_hydro

                # 厚度公式：δ = p_calc × D / (2 × [σ]t × φ - p_calc)  (mm)
                if p_calc <= 0:
                    t_calc = 0
                else:
                    t_calc = (p_calc * D * 1000) / (2 * S_d * E_w - p_calc)

                # 水压试验校核
                if rho_l <= 1000:
                    p_hydro_test = 1000 * G * liquid_head / 1_000_000
                else:
                    hydro_head = max(H_liquid * G_sg - design_point, 0)
                    p_hydro_test = 1000 * G * hydro_head / 1_000_000

                p_test_calc = max(1.25 * Pc, Pc + 0.1) + p_hydro_test

                if p_test_calc <= 0:
                    t_hydro_check = 0
                else:
                    # 水压试验时许用应力 = S_t 或 0.9 × ReL
                    t_hydro_check = (p_test_calc * D * 1000) / (2 * S_t * E_w - p_test_calc)

                t_required = max(t_calc, t_hydro_check)

                # NB/T 47003 最小壁厚
                if self._is_stainless(mat_grade):
                    t_min_noca = NB47003_STAINLESS
                else:
                    t_min_noca = NB47003_CARBON_STEEL

                p_calc_label = f"{p_calc:.4f}"

            t_design_v = t_required + CA
            t_nominal = self._round_up_plate(t_design_v)
            t_min = t_min_noca + CA

            status = "✓" if t_nominal >= t_min else f"✗ < {t_min:.1f}"

            weight_kg = math.pi * D * course_height * (t_nominal / 1000) * rho_s
            total_weight += weight_kg

            course_results.append({
                "圈号": i + 1, "底部标高": bottom_elev, "液柱高度": liquid_head,
                "p_calc": p_calc if mode == "nb47003" else None,
                "计算壁厚": t_calc, "水压试验": t_hydro_check,
                "需用壁厚": t_required, "设计厚度": t_design_v,
                "名义厚度": t_nominal, "校核": status, "重量": weight_kg,
                "min_thickness": t_min_noca,
            })

            lines.append(
                f"  {i+1:4d} │{liquid_head:9.3f} │{p_calc_label:>12s} │"
                f"{t_calc:9.3f} │{t_required:9.3f} │{t_nominal:9.1f} │  {status}"
            )

        # ── 底板 ──
        bottom_course_t = course_results[0]["名义厚度"] if course_results else 6
        annular_plate_t = self._round_up_plate(max(6 + CA, bottom_course_t * 0.5))
        bottom_plate_t = self._round_up_plate(max(6 + CA, 6.0))

        # ── 顶板 ──
        if "固定" in tank_type:
            roof_t = self._round_up_plate(max(5 + CA, 5.0))
        else:
            roof_t = 4.5

        # ── 重量 ──
        bottom_area = math.pi * (D / 2) ** 2
        roof_area = bottom_area
        bottom_weight = bottom_area * (bottom_plate_t / 1000) * rho_s
        roof_weight = roof_area * (roof_t / 1000) * rho_s
        shell_weight = total_weight
        total_w = shell_weight + bottom_weight + roof_weight

        lines.append("─" * 60)
        lines.append(f"  底板：边缘板 {annular_plate_t:.1f}mm / 中幅板 {bottom_plate_t:.1f}mm  →  {bottom_weight/1000:.3f}t")
        lines.append(f"  顶板：{roof_t:.1f}mm  →  {roof_weight/1000:.3f}t")
        lines.append(f"  罐壁总重：{shell_weight/1000:.3f} t")
        lines.append(f"  罐体总重：{total_w/1000:.3f} t")
        lines.append("═" * 60)
        lines.append(f"  最小壁厚（不含 CA）：{t_min_noca:.0f}mm"
                     f"（标准：{'GB 50341' if mode=='gb50341' else 'NB/T 47003'}）")
        lines.append("═" * 60)

        self.result_text.setPlainText("\n".join(lines))

        self._last_results = {
            "mode": mode, "tank_type": tank_type,
            "D": D, "H_total": H_total, "H_liquid": H_liquid,
            "n_courses": n_courses, "course_height": course_height,
            "rho_l": rho_l, "CA": CA, "S_d": S_d, "S_t": S_t,
            "E_w": E_w, "rho_s": rho_s, "mat_grade": mat_grade,
            "Pc": Pc, "Td": Td,
            "courses": course_results,
            "bottom_plate_t": bottom_plate_t,
            "annular_plate_t": annular_plate_t,
            "roof_t": roof_t,
            "shell_weight": shell_weight,
            "bottom_weight": bottom_weight,
            "roof_weight": roof_weight,
            "total_weight": total_w,
            "min_thickness": t_min_noca,
        }

    # ═════════════════════════════════════════════════════════
    #  导出 & 清空 & 历史
    # ═════════════════════════════════════════════════════════

    def _build_report_lines(self) -> list:
        r = self._last_results
        if r is None:
            return ["无计算结果"]

        std_name = "GB 50341-2014 (一英尺法)" if r["mode"] == "gb50341" else "NB/T 47003.1-2009 (圆筒公式)"
        lines = []
        lines.append(("储罐壁厚计算书", "h1"))
        lines.append((f"罐型：{r['tank_type']}  |  {std_name}", "subtitle"))
        lines.append((""))
        lines.append(("一、设计条件", "h2"))
        lines.append((f"内径 D = {r['D']:.2f} m  |  罐高 H = {r['H_total']:.2f} m  |  液位 = {r['H_liquid']:.2f} m", "p"))
        lines.append((f"储液密度 = {r['rho_l']:.0f} kg/m³  |  腐蚀裕量 = {r['CA']:.1f} mm", "p"))
        if r["mode"] == "nb47003":
            lines.append((f"设计压力 Pc = {r['Pc']:.4f} MPa  |  设计温度 = {r['Td']:.0f} °C", "p"))
        lines.append((""))
        lines.append(("二、材料与焊缝", "h2"))
        lines.append((f"材质 = {r['mat_grade']}  |  [σ] = {r['S_d']:.0f} MPa  |  S_t = {r['S_t']:.0f} MPa  |  E = {r['E_w']:.2f}", "p"))
        lines.append((""))
        lines.append(("三、逐圈壁厚", "h2"))
        for c in r["courses"]:
            p_info = f" | p={c['p_calc']:.4f}MPa" if c.get("p_calc") is not None else ""
            lines.append((
                f"第{c['圈号']:2d}圈 H={c['液柱高度']:6.3f}m{p_info} | "
                f"计算{c['计算壁厚']:5.2f}mm | 名义{c['名义厚度']:5.1f}mm | {c['校核']}",
                "p"
            ))
        lines.append((""))
        lines.append(("四、底板与顶板", "h2"))
        lines.append((f"边缘板 {r['annular_plate_t']:.1f}mm  /  中幅板 {r['bottom_plate_t']:.1f}mm", "p"))
        lines.append((f"顶板 {r['roof_t']:.1f}mm", "p"))
        lines.append((""))
        lines.append(("五、重量", "h2"))
        lines.append((f"罐壁 {r['shell_weight']/1000:.3f}t  /  底板 {r['bottom_weight']/1000:.3f}t  /  顶板 {r['roof_weight']/1000:.3f}t", "p"))
        lines.append((f"总计 {r['total_weight']/1000:.3f}t", "p"))
        return lines

    def _on_download_docx(self):
        if self._last_results is None:
            self.result_text.setPlainText("⚠ 请先完成计算再导出。")
            return
        self.download_docx_report("储罐壁厚")

    def _on_download_pdf(self):
        if self._last_results is None:
            self.result_text.setPlainText("⚠ 请先完成计算再导出。")
            return
        self.download_pdf_report("储罐壁厚")

    def clear(self):
        for _, w in self._input_widgets.items():
            if isinstance(w, QLineEdit):
                if not w.isReadOnly():
                    w.clear()
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(0)
        self._input_widgets["tank_type"].setCurrentIndex(0)
        self._input_widgets["standard"].setCurrentIndex(0)
        self._input_widgets["material_grade"].setCurrentIndex(0)
        self._input_widgets["weld_efficiency"].setCurrentText("双面焊 局部 RT")
        self.result_text.clear()
        self._last_results = None

    def _get_history_data(self) -> dict:
        r = self._last_results
        if r is None:
            return {}
        return {
            "inputs": {
                "标准": "GB50341" if r["mode"] == "gb50341" else "NB47003",
                "罐型": r["tank_type"],
                "内径(m)": str(r["D"]),
                "罐高(m)": str(r["H_total"]),
                "液位(m)": str(r["H_liquid"]),
                "设计压力(MPa)": str(r.get("Pc", 0)),
                "材质": r.get("mat_grade", ""),
                "[σ](MPa)": str(r["S_d"]),
                "焊缝系数": str(r["E_w"]),
            },
            "outputs": {
                "底圈名义厚度(mm)": str(r["courses"][0]["名义厚度"]) if r["courses"] else "N/A",
                "罐体总重(t)": f"{r['total_weight']/1000:.3f}",
            },
            "notes": "",
        }
