"""
蒸汽管道压降/温降计算器

计算长输蒸汽管道在输送过程中的压降和温降，考虑：
  - 敷设方式：架空/地沟/直埋
  - 保温层：有/无，保温材料厚度和导热系数
  - 输出：末端压力、温度、冷凝水量、压降、温降

依据：
  - 达西-魏斯巴赫公式：ΔP = f × (L/D) × ρv²/2
  - 传热方程：Q_loss = π D L K (T_s - T_a)
  - 冷凝水：m_cond = Q_loss / h_fg
"""

import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QScrollArea,
    QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator

from calculator_base import CalculatorBase
from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, SCROLL_AREA_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)
from common_constants import ATM_PRESSURE_MPA, get_steam_props

# ── 敷设方式 ──
INSTALL_TYPES = {
    "架空": {"alpha": 1.0, "desc": "空气中散热"},
    "地沟": {"alpha": 0.5, "desc": "地沟内半封闭"},
    "直埋": {"alpha": 0.3, "desc": "土壤中直埋"},
}

# ── 保温材料导热系数 W/(m·K) ──
INSULATION_MATERIALS = {
    "岩棉": 0.045,
    "玻璃棉": 0.042,
    "硅酸铝": 0.055,
    "聚氨酯": 0.025,
    "无保温": 100,  # 近似裸管
}

# ── 钢管绝对粗糙度 mm ──
PIPE_ROUGHNESS = {
    "碳钢无缝管": 0.05,
    "不锈钢管": 0.03,
    "镀锌钢管": 0.15,
}


class SteamPipePressureDropCalculator(CalculatorBase):
    """蒸汽管道压降/温降计算器"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent, data_manager)
        self.inputs = {}
        self.setup_ui()
        self.setup_wheel_blocker()

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

        self._create_steam_group(left_layout)
        self._create_pipe_group(left_layout)
        self._create_env_group(left_layout)

        calc_btn = QPushButton("计  算")
        calc_btn.setStyleSheet(CALC_BUTTON_STYLE)
        calc_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calc_btn.setMinimumHeight(50)
        calc_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        calc_btn.clicked.connect(self.calculate)
        left_layout.addWidget(calc_btn)
        left_layout.addStretch()
        scroll_left.setWidget(left_widget)

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
            ("TXT", DOCX_BTN_STYLE, self._on_download_txt),
            ("PDF", PDF_BTN_STYLE, self._on_download_pdf),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        right_layout.addLayout(btn_layout)

        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

    def _add_grid(self, parent):
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)
        parent.setLayout(grid)
        return grid

    def _add_row(self, grid, row, label, default, unit, vld=None):
        grid.addWidget(QLabel(label), row, 0)
        le = QLineEdit(default)
        if vld:
            le.setValidator(vld)
        grid.addWidget(le, row, 1)
        grid.addWidget(QLabel(unit), row, 2)
        return le

    def _create_steam_group(self, parent):
        group = QGroupBox("蒸汽参数")
        group.setStyleSheet(GROUP_STYLE)
        grid = self._add_grid(group)

        self.inputs["pressure"] = self._add_row(
            grid, 0, "进口蒸汽表压 P₁", "0.6",
            "MPa(g)", QDoubleValidator(0.01, 10, 3))

        self.inputs["flow"] = self._add_row(
            grid, 1, "蒸汽质量流量", "5000",
            "kg/h", QDoubleValidator(10, 1e6, 1))

        grid.addWidget(QLabel("蒸汽状态"), 2, 0)
        self.inputs["steam_state"] = QComboBox()
        self.inputs["steam_state"].addItems(["饱和蒸汽", "微过热蒸汽(过热度10°C)"])
        self.inputs["steam_state"].setStyleSheet(COMBOBOX_STYLE)
        grid.addWidget(self.inputs["steam_state"], 2, 1, 1, 2)

    def _create_pipe_group(self, parent):
        group = QGroupBox("管道参数")
        group.setStyleSheet(GROUP_STYLE)
        grid = self._add_grid(group)

        self.inputs["pipe_id"] = self._add_row(
            grid, 0, "管道内径 d", "150",
            "mm", QDoubleValidator(10, 2000, 1))

        self.inputs["pipe_len"] = self._add_row(
            grid, 1, "管道长度 L", "500",
            "m", QDoubleValidator(1, 10000, 1))

        grid.addWidget(QLabel("管材"), 2, 0)
        self.inputs["pipe_material"] = QComboBox()
        self.inputs["pipe_material"].addItems(list(PIPE_ROUGHNESS.keys()))
        self.inputs["pipe_material"].setStyleSheet(COMBOBOX_STYLE)
        grid.addWidget(self.inputs["pipe_material"], 2, 1, 1, 2)

        grid.addWidget(QLabel("敷设方式"), 3, 0)
        self.inputs["install_type"] = QComboBox()
        self.inputs["install_type"].addItems(list(INSTALL_TYPES.keys()))
        self.inputs["install_type"].setStyleSheet(COMBOBOX_STYLE)
        grid.addWidget(self.inputs["install_type"], 3, 1, 1, 2)

        grid.addWidget(QLabel("保温材料"), 4, 0)
        self.inputs["insulation_mat"] = QComboBox()
        self.inputs["insulation_mat"].addItems(list(INSULATION_MATERIALS.keys()))
        self.inputs["insulation_mat"].setStyleSheet(COMBOBOX_STYLE)
        grid.addWidget(self.inputs["insulation_mat"], 4, 1, 1, 2)

        self.inputs["insulation_thk"] = self._add_row(
            grid, 5, "保温层厚度", "50",
            "mm", QDoubleValidator(0, 300, 1))

    def _create_env_group(self, parent):
        group = QGroupBox("环境条件")
        group.setStyleSheet(GROUP_STYLE)
        grid = self._add_grid(group)

        self.inputs["ambient_temp"] = self._add_row(
            grid, 0, "环境温度 T_a", "20",
            "°C", QDoubleValidator(-30, 60, 1))

        self.inputs["wind_speed"] = self._add_row(
            grid, 1, "平均风速", "3",
            "m/s", QDoubleValidator(0, 30, 1))

    # ── 计算 ────────────────────────────────────────────────

    def calculate(self):
        try:
            P1_gauge = float(self.inputs["pressure"].text())
            m_dot = float(self.inputs["flow"].text()) / 3600.0  # kg/s
            d_mm = float(self.inputs["pipe_id"].text())
            d = d_mm / 1000.0
            L = float(self.inputs["pipe_len"].text())
            install = self.inputs["install_type"].currentText()
            ins_mat = self.inputs["insulation_mat"].currentText()
            ins_thk = float(self.inputs["insulation_thk"].text()) / 1000.0
            T_a = float(self.inputs["ambient_temp"].text())
            v_wind = float(self.inputs["wind_speed"].text())
            eps = PIPE_ROUGHNESS[self.inputs["pipe_material"].currentText()] / 1000.0

            # 蒸汽物性（入口状态）
            props = get_steam_props(P1_gauge)
            T1 = props["sat_temp"]
            h_fg = props["h_fg"] * 1000  # kJ/kg → J/kg

            # 蒸汽密度（近似饱和）
            P_abs = P1_gauge + ATM_PRESSURE_MPA  # MPa
            # 理想气体近似，但饱和蒸汽密度偏低
            # 使用近似：在0.1~1.0MPa范围 ρ ≈ 1.0~6.0 kg/m³
            rho_v = P_abs * 10 * 0.8  # kg/m³ 近似

            # 蒸汽流速
            A = math.pi * d**2 / 4
            v = m_dot / (rho_v * A) if rho_v > 0 and A > 0 else 10

            # 雷诺数
            # 饱和蒸汽动力粘度 ≈ 1.5e-5 Pa·s
            mu_v = 1.5e-5
            Re = rho_v * v * d / mu_v if mu_v > 0 else 1e5

            # 摩擦系数 (Colebrook 近似)
            if Re < 2300:
                f = 64 / Re
            else:
                f = 0.25 / (math.log10(eps / d / 3.7 + 5.74 / Re**0.9))**2

            # 压降 (达西-魏斯巴赫)
            dP = f * (L / d) * rho_v * v**2 / 2 / 1e6  # Pa → MPa

            # ── 温降计算 ──
            # 总传热系数估算
            alpha = INSTALL_TYPES[install]["alpha"]
            lambda_ins = INSULATION_MATERIALS[ins_mat]

            if ins_thk > 0 and lambda_ins < 50:
                # 有保温
                K = lambda_ins / ins_thk  # W/(m²·K)
                K = K * (1 + 0.1 * v_wind) * alpha
            else:
                # 裸管 — 表面传热
                h_conv = 5 + 3.5 * v_wind  # 自然对流 + 强制对流
                K = h_conv * alpha

            # 散热面积
            D_outer = d + 2 * ins_thk + 0.008  # 外径 + 保温 + 管壁
            A_surf = math.pi * D_outer * L

            # 散热量
            T_avg = T1 - 5  # 平均蒸汽温度，近似取进口温度-5°C
            dT = T_avg - T_a
            if dT <= 0:
                dT = 10
            Q_loss = K * A_surf * dT  # W

            # 冷凝水量
            m_cond = Q_loss / h_fg * 3600  # kg/h

            # 温降估算
            delta_T = Q_loss / (m_dot * 2010)  # 2010 J/(kg·K) 水蒸气比热

            # 末端参数
            P2 = max(0.001, P1_gauge - dP)
            T2 = T1 - delta_T

            # ── 输出 ──
            lines = []
            lines.append("═══ 蒸汽管道压降/温降计算 ═══")
            lines.append(f"")
            lines.append(f"【输入参数】")
            lines.append(f"  进口压力: {P1_gauge:.2f} MPa(g) = {P_abs:.3f} MPa(a)")
            lines.append(f"  进口温度: {T1:.1f} °C")
            lines.append(f"  蒸汽流量: {m_dot * 3600:.0f} kg/h")
            lines.append(f"  管径/长度: DN{d_mm:.0f} / {L:.0f} m")
            lines.append(f"  敷设方式: {install}")
            lines.append(f"  保温: {ins_mat} {ins_thk * 1000:.0f}mm")
            lines.append(f"  环境温度: {T_a:.0f} °C")
            lines.append(f"")
            lines.append(f"【流动参数】")
            lines.append(f"  蒸汽密度: {rho_v:.3f} kg/m³")
            lines.append(f"  管内流速: {v:.1f} m/s")
            lines.append(f"  雷诺数 Re: {Re:.0f}")
            lines.append(f"  摩擦系数 f: {f:.4f}")
            lines.append(f"")
            lines.append(f"【压降】")
            lines.append(f"  压降 ΔP: {dP * 1000:.1f} kPa ({dP:.4f} MPa)")
            lines.append(f"  单位压降: {dP * 1000 / L:.2f} kPa/m")
            lines.append(f"  压降率: {dP / P1_gauge * 100:.1f}%")
            lines.append(f"")
            lines.append(f"【温降与散热】")
            lines.append(f"  散热损失: {Q_loss / 1000:.1f} kW")
            lines.append(f"  温降 ΔT: {delta_T:.1f} °C")
            lines.append(f"  冷凝水量: {m_cond:.1f} kg/h")
            lines.append(f"")
            lines.append(f"【末端状态】")
            lines.append(f"  末端压力 P₂: {P2:.3f} MPa(g)")
            lines.append(f"  末端温度 T₂: {T2:.0f} °C")

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
                         f"蒸汽管道压降_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"))

    def _on_download_pdf(self):
        import os
        from datetime import datetime
        self.download_pdf_report(
            self.generate_report(),
            os.path.join(os.path.expanduser("~"), "Desktop",
                         f"蒸汽管道压降_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"))
