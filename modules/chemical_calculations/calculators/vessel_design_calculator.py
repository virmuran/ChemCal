"""
容器/贮罐设计计算器

依据 GB 150.1~150.4 压力容器标准，计算立式圆筒形容器的：
  - 筒体/封头壁厚（内压）
  - 全容积与有效容积
  - 材料重量估算
  - 水压试验压力校核

支持四种封头型式：椭圆封头、半球形封头、碟形封头、平盖
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
from common_constants import G, ATM_PRESSURE_MPA

# ── 材料许用应力 (MPa) ──
# (名称, 密度 kg/m³, [σ]@20°C, [σ]@100°C, [σ]@150°C, [σ]@200°C)
ALLOWABLE_STRESS = {
    "Q235B":    (7850, 113, 113, 108, 105),
    "Q345R":    (7850, 189, 189, 183, 177),
    "S30408 (304)":  (7930, 137, 137, 137, 130),
    "S31603 (316L)": (8000, 117, 117, 115, 108),
    "16MnDR":   (7850, 174, 174, 169, 163),
    "自定义":    (7850, None, None, None, None),
}

# ── 封头类型 ──
HEAD_TYPES = {
    "标准椭圆封头 (EHA)": {
        "depth_ratio": 0.25,       # h_i/D_i = 0.25
        "volume_coeff": 0.1309,    # V = coeff * D_i³
        "area_coeff": 1.13,        # A = coeff * D_i² (近似)
        "k_factor": 1.0,           # 形状系数 K
    },
    "半球形封头": {
        "depth_ratio": 0.50,
        "volume_coeff": 0.2618,    # π/12
        "area_coeff": 1.571,       # π/2
        "k_factor": 1.0,
    },
    "碟形封头 (THA)": {
        "depth_ratio": 0.194,
        "volume_coeff": 0.0994,
        "area_coeff": 0.93,
        "k_factor": 1.54,          # M 系数近似
    },
    "平盖": {
        "depth_ratio": 0.0,
        "volume_coeff": 0.0,
        "area_coeff": 0.785,       # π/4
        "k_factor": 0.0,           # 焊接结构相关
    },
}

# ── 焊缝系数 ──
WELD_COEFF = {
    "双面焊对接 100%无损检测": 1.00,
    "双面焊对接 局部无损检测": 0.85,
    "单面焊对接 带垫板": 0.90,
    "单面焊对接 不带垫板": 0.70,
}


class VesselDesignCalculator(CalculatorBase):
    """容器/贮罐设计计算器 v1.0"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent, data_manager)
        self._last_thickness = None
        self._last_weight = None
        self._last_volume = None
        self.setup_ui()
        self.setup_wheel_blocker()
        self._fill_stress()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ── 左侧：输入 ──
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(SCROLL_AREA_STYLE)
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(12)

        # 设计参数组
        self._create_design_group(left_layout)
        # 几何参数组
        self._create_geometry_group(left_layout)
        # 材料参数组
        self._create_material_group(left_layout)

        left_layout.addStretch()
        scroll_left.setWidget(left_widget)

        # ── 右侧：结果 ──
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
        # 结果框统一标准：边框/背景/文字色交给主题系统，仅指定等宽字体
        self.result_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: 13px;
            }
        """)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        rl.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        for label, style, slot in [
            ("清空", CLEAR_BTN_STYLE, self.clear),
            ("DOCX", DOCX_BTN_STYLE, self._on_download_txt),
            ("PDF", PDF_BTN_STYLE, self._on_download_pdf),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        right_layout.addLayout(btn_layout)

        # 计算按钮放最底部（结果→下载→计算）
        calc_btn = self.make_calc_button("计  算")
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)

        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

    def _make_grid(self, parent):
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)
        parent.setLayout(grid)
        return grid

    def _add_row(self, grid, row, label_text, default, unit, vld=None):
        grid.addWidget(QLabel(label_text), row, 0)
        le = QLineEdit(default)
        if vld:
            le.setValidator(vld)
        grid.addWidget(le, row, 1)
        grid.addWidget(QLabel(unit), row, 2)
        return le

    def _create_design_group(self, parent):
        group = QGroupBox("设计参数")
        group.setStyleSheet(GROUP_STYLE)
        grid = self._make_grid(group)
        self.inputs = {}

        self.inputs["design_pressure"] = self._add_row(
            grid, 0, "设计压力 p", "0.6",
            "MPa", QDoubleValidator(0.001, 100, 4))

        self.inputs["design_temp"] = self._add_row(
            grid, 1, "设计温度 T", "120",
            "°C", QDoubleValidator(-50, 600, 1))

        grid.addWidget(QLabel("封头型式"), 2, 0)
        self.inputs["head_type"] = QComboBox()
        self.inputs["head_type"].addItems(list(HEAD_TYPES.keys()))
        self.inputs["head_type"].setStyleSheet(COMBOBOX_STYLE)
        grid.addWidget(self.inputs["head_type"], 2, 1)

        grid.addWidget(QLabel("腐蚀裕量 C₂"), 3, 0)
        self.inputs["corrosion"] = QLineEdit("1.5")
        self.inputs["corrosion"].setValidator(QDoubleValidator(0, 10, 1))
        grid.addWidget(self.inputs["corrosion"], 3, 1)
        grid.addWidget(QLabel("mm"), 3, 2)

        grid.addWidget(QLabel("钢板负偏差 C₁"), 4, 0)
        self.inputs["plate_deviation"] = QLineEdit("0.3")
        self.inputs["plate_deviation"].setValidator(QDoubleValidator(0, 5, 1))
        grid.addWidget(self.inputs["plate_deviation"], 4, 1)
        grid.addWidget(QLabel("mm"), 4, 2)

        grid.addWidget(QLabel("焊缝系数 φ"), 5, 0)
        self.inputs["weld_coeff"] = QComboBox()
        self.inputs["weld_coeff"].addItems(list(WELD_COEFF.keys()))
        self.inputs["weld_coeff"].setStyleSheet(COMBOBOX_STYLE)
        self.inputs["weld_coeff"].setCurrentIndex(1)  # 默认 0.85
        grid.addWidget(self.inputs["weld_coeff"], 5, 1)

        parent.addWidget(group)

    def _create_geometry_group(self, parent):
        group = QGroupBox("几何参数")
        group.setStyleSheet(GROUP_STYLE)
        grid = self._make_grid(group)

        self.inputs["inner_diameter"] = self._add_row(
            grid, 0, "筒体内径 D_i", "2400",
            "mm", QDoubleValidator(100, 30000, 1))

        self.inputs["height_d_ratio"] = self._add_row(
            grid, 1, "长径比 H/D_i", "2.0",
            "—", QDoubleValidator(0.5, 10, 2))

        self.inputs["fill_ratio"] = self._add_row(
            grid, 2, "装料系数", "0.75",
            "—", QDoubleValidator(0.1, 0.95, 2))

        self.inputs["insulation_thk"] = self._add_row(
            grid, 3, "保温层厚（重量用）", "0",
            "mm", QDoubleValidator(0, 500, 1))

        parent.addWidget(group)

    def _create_material_group(self, parent):
        group = QGroupBox("材料参数")
        group.setStyleSheet(GROUP_STYLE)
        grid = self._make_grid(group)

        grid.addWidget(QLabel("壳体材料"), 0, 0)
        self.inputs["material"] = QComboBox()
        self.inputs["material"].addItems(list(ALLOWABLE_STRESS.keys()))
        self.inputs["material"].setStyleSheet(COMBOBOX_STYLE)
        self.inputs["material"].currentTextChanged.connect(self._fill_stress)
        grid.addWidget(self.inputs["material"], 0, 1)

        self.inputs["allow_stress"] = self._add_row(
            grid, 1, "许用应力 [σ]ᵗ", "137",
            "MPa", QDoubleValidator(10, 500, 1))

        self.inputs["density"] = self._add_row(
            grid, 2, "材料密度 ρ", "7930",
            "kg/m³", QDoubleValidator(1000, 20000, 1))

        parent.addWidget(group)

    def _fill_stress(self, name=None):
        """根据材料和设计温度自动填入许用应力"""
        try:
            if name is None:
                name = self.inputs["material"].currentText()
        except (RuntimeError, KeyError):
            return
        data = ALLOWABLE_STRESS.get(name)
        if data is None or data[1] is None:
            return
        try:
            T = float(self.inputs["design_temp"].text())
        except ValueError:
            T = 120
        temps = [20, 100, 150, 200]
        stresses = data[1:]
        if T <= temps[0]:
            s = stresses[0]
        elif T >= temps[-1]:
            s = stresses[-1]
        else:
            for i in range(len(temps) - 1):
                if temps[i] <= T <= temps[i + 1]:
                    f = (T - temps[i]) / (temps[i + 1] - temps[i])
                    s = stresses[i] + f * (stresses[i + 1] - stresses[i])
                    break
            else:
                s = stresses[0]
        self.inputs["allow_stress"].setText(f"{s:.0f}")
        self.inputs["density"].setText(str(data[0]))

    # ── 计算 ────────────────────────────────────────────────

    def calculate(self):
        try:
            Di = float(self.inputs["inner_diameter"].text()) / 1000.0  # mm → m
            Pc = float(self.inputs["design_pressure"].text())           # MPa
            C2 = float(self.inputs["corrosion"].text()) / 1000.0        # mm → m
            C1 = float(self.inputs["plate_deviation"].text()) / 1000.0
            phi = WELD_COEFF[self.inputs["weld_coeff"].currentText()]
            sigma = float(self.inputs["allow_stress"].text())           # MPa
            H_D = float(self.inputs["height_d_ratio"].text())
            fill = float(self.inputs["fill_ratio"].text())
            rho = float(self.inputs["density"].text())
            head_key = self.inputs["head_type"].currentText()
            head = HEAD_TYPES[head_key]

            H = Di * H_D  # 筒体高度 m

            # ── 壁厚计算 (GB 150) ──
            # 圆筒: δ = Pc * Di / (2[σ]φ - Pc)
            delta_calc = Pc * Di / (2 * sigma * phi - Pc)
            delta_nom = delta_calc + C2 + C1
            # 向上圆整到0.5mm
            delta_nom = math.ceil(delta_nom * 2000) / 2000.0
            delta_nom = max(delta_nom, 0.003)  # 最小3mm

            # 封头壁厚（椭圆封头）
            if head_key == "半球形封头":
                delta_head = Pc * Di / (4 * sigma * phi - Pc)
            elif head_key == "碟形封头 (THA)":
                delta_head = Pc * Di * head["k_factor"] / (2 * sigma * phi - 0.5 * Pc)
            elif head_key == "平盖":
                delta_head = Di * math.sqrt(0.3 * Pc / sigma)
            else:  # 椭圆封头
                delta_head = Pc * Di / (2 * sigma * phi - 0.5 * Pc)
            delta_head_nom = math.ceil((delta_head + C2 + C1) * 2000) / 2000.0
            delta_head_nom = max(delta_head_nom, 0.003)

            # ── 容积 ──
            V_cylinder = math.pi * Di**2 / 4 * H
            V_head_each = head["volume_coeff"] * Di**3
            V_total = V_cylinder + V_head_each * 2
            V_effective = V_total * fill

            # ── 重量估算 ──
            Dm = Di + delta_nom  # 平均直径
            A_cyl = math.pi * Dm * H
            W_cyl = rho * A_cyl * delta_nom / 1000  # kg → 吨展示用

            A_head_each = head["area_coeff"] * Di**2
            W_heads = rho * A_head_each * 2 * delta_head_nom / 1000

            W_total_kg = (W_cyl + W_heads) * 1000

            # ── 水压试验压力 ──
            Pt = 1.25 * Pc * sigma / sigma  # 简化为 1.25Pc
            Pt = max(Pt, Pc + 0.1)

            # ── 输出 ──
            self._last_thickness = delta_nom * 1000
            self._last_weight = W_total_kg
            self._last_volume = V_total

            lines = []
            lines.append("═══ 容器设计计算结果 ═══")
            lines.append(f"标准依据: GB 150-2011 压力容器")
            lines.append(f"")
            lines.append(f"【设计条件】")
            lines.append(f"  设计压力: {Pc:.3f} MPa")
            lines.append(f"  设计温度: {float(self.inputs['design_temp'].text()):.0f} °C")
            lines.append(f"  材料: {self.inputs['material'].currentText()}")
            lines.append(f"  许用应力 [σ]ᵗ: {sigma:.0f} MPa")
            lines.append(f"  焊缝系数 φ: {phi:.2f}")
            lines.append(f"  腐蚀裕量: {C2 * 1000:.1f} mm")
            lines.append(f"")
            lines.append(f"【壁厚计算】")
            lines.append(f"  筒体计算壁厚: {delta_calc * 1000:.2f} mm")
            lines.append(f"  筒体名义壁厚: {delta_nom * 1000:.1f} mm (含 C₁+C₂)")
            lines.append(f"  封头计算壁厚: {delta_head * 1000:.2f} mm")
            lines.append(f"  封头名义壁厚: {delta_head_nom * 1000:.1f} mm")
            lines.append(f"  水压试验压力: {Pt:.2f} MPa")
            lines.append(f"")
            lines.append(f"【几何尺寸】")
            lines.append(f"  筒体内径 D_i: {Di * 1000:.0f} mm")
            lines.append(f"  筒体高度 H: {H * 1000:.0f} mm")
            lines.append(f"  封头型式: {head_key}")
            lines.append(f"  封头深度: {Di * head['depth_ratio'] * 1000:.0f} mm")
            lines.append(f"")
            lines.append(f"【容积】")
            lines.append(f"  全容积: {V_total:.2f} m³")
            lines.append(f"  有效容积: {V_effective:.2f} m³ (装料系数 {fill:.0%})")
            lines.append(f"")
            lines.append(f"【重量估算】")
            lines.append(f"  壳体总重: {W_total_kg:.0f} kg")
            lines.append(f"  筒体: {W_cyl * 1000:.0f} kg")
            lines.append(f"  封头×2: {W_heads * 1000:.0f} kg")

            self.result_text.setText("\n".join(lines))

        except Exception as e:
            QMessageBox.critical(self, "计算错误", str(e))

    def clear(self):
        for w in self.inputs.values():
            if isinstance(w, QLineEdit):
                w.clear()
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(0)
        self.result_text.clear()
        self._fill_stress()

    def _get_history_data(self):
        return {"inputs": {}, "outputs": {}}

    def generate_report(self):
        return self.result_text.toPlainText()

    def _on_download_txt(self):
        import os
        from datetime import datetime
        self.download_docx_report(
            self.generate_report(),
            os.path.join(os.path.expanduser("~"), "Desktop",
                         f"容器设计_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"))

    def _on_download_pdf(self):
        import os
        from datetime import datetime
        self.download_pdf_report(
            self.generate_report(),
            os.path.join(os.path.expanduser("~"), "Desktop",
                         f"容器设计_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"))


# 别名
vessel_design_calculator = VesselDesignCalculator
