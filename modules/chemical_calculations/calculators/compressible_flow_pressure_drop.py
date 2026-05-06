from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QLabel, QLineEdit, QComboBox, QPushButton,
                              QTextEdit, QTableWidget, QTableWidgetItem,
                              QHeaderView, QMessageBox, QTabWidget, QDoubleSpinBox,
                              QCheckBox, QRadioButton, QButtonGroup)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math


class CompressibleFlowPressureDrop(QWidget):
    """可压缩流体压降计算器"""

    calculation_type = "compressible_flow_pressure_drop"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        title_label = QLabel("可压缩流体压降计算")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        main_layout.addWidget(title_label)

        self.tab_widget = QTabWidget()
        self.calculation_tab = self.create_calculation_tab()
        self.tab_widget.addTab(self.calculation_tab, "压降计算")
        self.theory_tab = self.create_theory_tab()
        self.tab_widget.addTab(self.theory_tab, "理论说明")
        main_layout.addWidget(self.tab_widget)

    def create_calculation_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 流体性质
        fluid_group = QGroupBox("流体性质")
        fluid_layout = QVBoxLayout(fluid_group)

        ft_layout = QHBoxLayout()
        ft_layout.addWidget(QLabel("流体类型:"))
        self.fluid_combo = QComboBox()
        self.fluid_combo.addItems([
            "空气", "氮气", "氧气", "氢气", "二氧化碳", "天然气",
            "蒸汽", "甲烷", "乙烷", "丙烷", "自定义气体"
        ])
        self.fluid_combo.currentTextChanged.connect(self.on_fluid_changed)
        ft_layout.addWidget(self.fluid_combo)

        ft_layout.addWidget(QLabel("分子量 (g/mol):"))
        self.molecular_weight_input = QDoubleSpinBox()
        self.molecular_weight_input.setRange(1, 200)
        self.molecular_weight_input.setValue(28.97)
        self.molecular_weight_input.setSuffix(" g/mol")
        ft_layout.addWidget(self.molecular_weight_input)

        ft_layout.addWidget(QLabel("比热比 (γ):"))
        self.gamma_input = QDoubleSpinBox()
        self.gamma_input.setRange(1.0, 2.0)
        self.gamma_input.setValue(1.4)
        self.gamma_input.setSingleStep(0.01)
        ft_layout.addWidget(self.gamma_input)
        fluid_layout.addLayout(ft_layout)

        gp_layout = QHBoxLayout()
        gp_layout.addWidget(QLabel("比气体常数 R (J/(kg·K)):"))
        self.gas_constant_input = QDoubleSpinBox()
        self.gas_constant_input.setRange(50, 5000)
        self.gas_constant_input.setValue(287)
        self.gas_constant_input.setSuffix(" J/(kg·K)")
        gp_layout.addWidget(self.gas_constant_input)

        gp_layout.addWidget(QLabel("动力粘度 (μPa·s):"))
        self.viscosity_input = QDoubleSpinBox()
        self.viscosity_input.setRange(1, 100)
        self.viscosity_input.setValue(18.27)
        self.viscosity_input.setSuffix(" μPa·s")
        gp_layout.addWidget(self.viscosity_input)
        fluid_layout.addLayout(gp_layout)
        layout.addWidget(fluid_group)

        # 管道参数
        pipe_group = QGroupBox("管道参数")
        pipe_layout = QVBoxLayout(pipe_group)

        ps_layout = QHBoxLayout()
        ps_layout.addWidget(QLabel("管道内径 (mm):"))
        self.diameter_input = QDoubleSpinBox()
        self.diameter_input.setRange(1, 2000)
        self.diameter_input.setValue(100)
        self.diameter_input.setSuffix(" mm")
        ps_layout.addWidget(self.diameter_input)

        ps_layout.addWidget(QLabel("管道长度 (m):"))
        self.length_input = QDoubleSpinBox()
        self.length_input.setRange(1, 10000)
        self.length_input.setValue(100)
        self.length_input.setSuffix(" m")
        ps_layout.addWidget(self.length_input)

        ps_layout.addWidget(QLabel("绝对粗糙度 (mm):"))
        self.roughness_input = QDoubleSpinBox()
        self.roughness_input.setRange(0.001, 5)
        self.roughness_input.setValue(0.046)
        self.roughness_input.setSuffix(" mm")
        ps_layout.addWidget(self.roughness_input)
        pipe_layout.addLayout(ps_layout)

        pc_layout = QHBoxLayout()
        pc_layout.addWidget(QLabel("管道形状:"))
        self.pipe_shape_combo = QComboBox()
        self.pipe_shape_combo.addItems(["圆形", "矩形"])
        pc_layout.addWidget(self.pipe_shape_combo)

        pc_layout.addWidget(QLabel("当量长度系数:"))
        self.equivalent_length_factor = QDoubleSpinBox()
        self.equivalent_length_factor.setRange(1.0, 3.0)
        self.equivalent_length_factor.setValue(1.5)
        self.equivalent_length_factor.setSingleStep(0.1)
        pc_layout.addWidget(self.equivalent_length_factor)
        pc_layout.addStretch()
        pipe_layout.addLayout(pc_layout)
        layout.addWidget(pipe_group)

        # 操作条件
        condition_group = QGroupBox("操作条件")
        condition_layout = QVBoxLayout(condition_group)

        pt_layout = QHBoxLayout()
        pt_layout.addWidget(QLabel("入口压力 (kPa):"))
        self.inlet_pressure_input = QDoubleSpinBox()
        self.inlet_pressure_input.setRange(1, 10000)
        self.inlet_pressure_input.setValue(500)
        self.inlet_pressure_input.setSuffix(" kPa")
        pt_layout.addWidget(self.inlet_pressure_input)

        pt_layout.addWidget(QLabel("出口压力 (kPa):"))
        self.outlet_pressure_input = QDoubleSpinBox()
        self.outlet_pressure_input.setRange(1, 10000)
        self.outlet_pressure_input.setValue(400)
        self.outlet_pressure_input.setSuffix(" kPa")
        pt_layout.addWidget(self.outlet_pressure_input)

        pt_layout.addWidget(QLabel("温度 (°C):"))
        self.temperature_input = QDoubleSpinBox()
        self.temperature_input.setRange(-200, 1000)
        self.temperature_input.setValue(20)
        self.temperature_input.setSuffix(" °C")
        pt_layout.addWidget(self.temperature_input)
        condition_layout.addLayout(pt_layout)

        fl_layout = QHBoxLayout()
        fl_layout.addWidget(QLabel("质量流量 (kg/h):"))
        self.mass_flow_input = QDoubleSpinBox()
        self.mass_flow_input.setRange(0.1, 100000)
        self.mass_flow_input.setValue(1000)
        self.mass_flow_input.setSuffix(" kg/h")
        fl_layout.addWidget(self.mass_flow_input)
        fl_layout.addStretch()
        condition_layout.addLayout(fl_layout)
        layout.addWidget(condition_group)

        # 计算方法
        method_group = QGroupBox("计算方法")
        method_layout = QHBoxLayout(method_group)

        self.method_group = QButtonGroup(self)
        self.darcy_radio = QRadioButton("Darcy-Weisbach (等温积分)")
        self.darcy_radio.setChecked(True)
        self.method_group.addButton(self.darcy_radio)
        method_layout.addWidget(self.darcy_radio)

        self.darcy_simple_radio = QRadioButton("Darcy-Weisbach (平均密度)")
        self.method_group.addButton(self.darcy_simple_radio)
        method_layout.addWidget(self.darcy_simple_radio)

        self.weymouth_radio = QRadioButton("Weymouth公式")
        self.method_group.addButton(self.weymouth_radio)
        method_layout.addWidget(self.weymouth_radio)

        self.panhandle_radio = QRadioButton("Panhandle公式")
        self.method_group.addButton(self.panhandle_radio)
        method_layout.addWidget(self.panhandle_radio)
        method_layout.addStretch()
        layout.addWidget(method_group)

        # 按钮
        btn_layout = QHBoxLayout()
        self.calculate_btn = QPushButton("计算压降")
        self.calculate_btn.clicked.connect(self.calculate_pressure_drop)
        self.calculate_btn.setStyleSheet("QPushButton { background-color: #9b59b6; color: white; font-weight: bold; }")
        btn_layout.addWidget(self.calculate_btn)

        self.auto_calc_btn = QPushButton("反算流量")
        self.auto_calc_btn.clicked.connect(self.auto_calculate_flow)
        self.auto_calc_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; }")
        btn_layout.addWidget(self.auto_calc_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_inputs)
        self.clear_btn.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; }")
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)

        # 结果
        result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(300)
        result_layout.addWidget(self.result_text)
        layout.addWidget(result_group)

        detail_group = QGroupBox("详细参数")
        detail_layout = QVBoxLayout(detail_group)
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(3)
        self.detail_table.setHorizontalHeaderLabels(["参数", "数值", "单位"])
        detail_layout.addWidget(self.detail_table)
        layout.addWidget(detail_group)

        return tab

    def on_fluid_changed(self, fluid_name):
        fluid_properties = {
            "空气":   {"mw": 28.97, "gamma": 1.40, "R": 287.1, "viscosity": 18.27},
            "氮气":   {"mw": 28.01, "gamma": 1.40, "R": 296.8, "viscosity": 17.90},
            "氧气":   {"mw": 32.00, "gamma": 1.40, "R": 259.8, "viscosity": 20.80},
            "氢气":   {"mw": 2.016, "gamma": 1.41, "R": 4124.0, "viscosity": 8.90},
            "二氧化碳": {"mw": 44.01, "gamma": 1.30, "R": 188.9, "viscosity": 14.80},
            "天然气": {"mw": 18.00, "gamma": 1.30, "R": 461.5, "viscosity": 11.20},
            "蒸汽":   {"mw": 18.02, "gamma": 1.33, "R": 461.5, "viscosity": 12.30},
            "甲烷":   {"mw": 16.04, "gamma": 1.32, "R": 518.3, "viscosity": 11.20},
            "乙烷":   {"mw": 30.07, "gamma": 1.20, "R": 276.5, "viscosity": 9.50},
            "丙烷":   {"mw": 44.10, "gamma": 1.13, "R": 188.5, "viscosity": 8.10}
        }
        if fluid_name in fluid_properties:
            p = fluid_properties[fluid_name]
            self.molecular_weight_input.setValue(p["mw"])
            self.gamma_input.setValue(p["gamma"])
            self.gas_constant_input.setValue(p["R"])
            self.viscosity_input.setValue(p["viscosity"])

    def create_theory_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        theory_text = QTextEdit()
        theory_text.setReadOnly(True)
        theory_text.setHtml(self.get_theory_html())
        layout.addWidget(theory_text)
        return tab

    def get_theory_html(self):
        return """
        <h2>可压缩流体压降计算理论</h2>

        <h3>可压缩流体特点</h3>
        <p>可压缩流体（气体、蒸汽等）在流动过程中密度会随压力和温度变化，需要考虑密度变化、压力变化对物性的影响、音速限制（阻塞流）等。</p>

        <h3>常用计算方法</h3>

        <h4>1. Darcy-Weisbach 等温积分法（推荐）</h4>
        <p>假设等温流动，对动量方程积分得：</p>
        <p><b>P₁² - P₂² = (f·L/D)·(ṁ/A)²·(R·T/M)</b></p>
        <p>适用于长距离管道（ΔP/P₁ > 10% 时比平均密度法准确得多），基于理想气体假设。</p>

        <h4>2. Darcy-Weisbach 平均密度法</h4>
        <p>ΔP = f × (L/D) × (ρ_avg × v²/2)</p>
        <p>使用进出口平均密度，适用于 ΔP/P₁ < 10% 的低压降情况。</p>

        <h4>3. Weymouth 公式</h4>
        <p>Q = C × (P₁² - P₂²)<sup>0.5</sup> × D<sup>2.667</sup> / L<sup>0.5</sup></p>
        <p>天然气管道经验公式，完全湍流区，C=0.0330（SI）。</p>

        <h4>4. Panhandle A 公式</h4>
        <p>Q = C × E × (P₁² - P₂²)<sup>0.5394</sup> × D<sup>2.6182</sup> / L<sup>0.4604</sup></p>
        <p>天然气管道，考虑效率因子 E，C=0.0280（SI），n=0.0793。</p>

        <h3>关键参数</h3>
        <ul>
        <li><b>雷诺数 Re</b>: 层流 &lt;2000, 过渡 2000-4000, 湍流 &gt;4000</li>
        <li><b>马赫数 Ma</b>: Ma&lt;0.3 不可压缩, 0.3-0.8 可压缩, &gt;0.8 高速</li>
        <li><b>临界压比</b>: P₂/P₁ ≥ (2/(γ+1))<sup>γ/(γ-1)</sup>，否则发生阻塞流</li>
        </ul>

        <h3>参考标准</h3>
        <ul>
        <li>ASME MFC-3M / ISO 5167 流量测量</li>
        <li>AGA Report No. 3 / API MPMS Chapter 14</li>
        <li>Crane TP 410 Flow of Fluids</li>
        </ul>
        """

    # ------------------------------------------------------------------
    #  核心计算
    # ------------------------------------------------------------------

    def get_selected_method(self):
        if self.darcy_radio.isChecked():
            return "darcy_integral"
        elif self.darcy_simple_radio.isChecked():
            return "darcy_avg"
        elif self.weymouth_radio.isChecked():
            return "weymouth"
        elif self.panhandle_radio.isChecked():
            return "panhandle"
        return "darcy_integral"

    @staticmethod
    def calculate_density_ideal(pressure_Pa, temperature_K, R_specific):
        """理想气体密度"""
        return pressure_Pa / (R_specific * temperature_K)

    @staticmethod
    def calculate_reynolds(diameter, velocity, density, viscosity):
        return density * velocity * diameter / viscosity

    @staticmethod
    def calculate_friction_factor(reynolds, roughness, diameter):
        """Colebrook-White 迭代求解摩擦系数"""
        if reynolds <= 0:
            return 0.02
        if reynolds < 2000:
            return 64.0 / reynolds
        rel_roughness = roughness / diameter
        # Swamee-Jain 初始猜测（更稳定）
        f = 0.25 / (math.log10(rel_roughness / 3.7 + 5.74 / reynolds ** 0.9)) ** 2
        for _ in range(50):
            rhs = rel_roughness / 3.7 + 2.51 / (reynolds * math.sqrt(f))
            f_new = 1.0 / (-2.0 * math.log10(rhs)) ** 2
            if abs(f_new - f) < 1e-8:
                return f_new
            f = f_new
        return f

    def calculate_pressure_drop(self):
        try:
            method = self.get_selected_method()
            d = self.diameter_input.value() / 1000.0
            L = self.length_input.value()
            eps = self.roughness_input.value() / 1000.0
            P1_kPa = self.inlet_pressure_input.value()
            P2_kPa = self.outlet_pressure_input.value()
            T_C = self.temperature_input.value()
            m_kg_h = self.mass_flow_input.value()
            gamma = self.gamma_input.value()
            R = self.gas_constant_input.value()
            mu = self.viscosity_input.value() * 1e-6
            equiv_factor = self.equivalent_length_factor.value()

            P1_Pa = P1_kPa * 1000.0
            P2_Pa = P2_kPa * 1000.0
            T_K = T_C + 273.15
            m = m_kg_h / 3600.0
            A = math.pi * d ** 2 / 4.0

            # 入口密度和流速
            rho1 = self.calculate_density_ideal(P1_Pa, T_K, R)
            v1 = m / (rho1 * A) if rho1 > 0 else 0
            Re1 = self.calculate_reynolds(d, v1, rho1, mu)
            f = self.calculate_friction_factor(Re1, eps, d)
            L_eq = L * equiv_factor

            # 马赫数
            a_sound = math.sqrt(gamma * R * T_K)
            Ma = v1 / a_sound if a_sound > 0 else 0

            # 临界压比
            P_crit_ratio = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
            P2_min = P1_Pa * P_crit_ratio

            if method == "darcy_integral":
                # 等温积分法: P1² - P2² = (f·L_eq/D)·(m/A)²·R·T
                # 可以正算 P2 或反算 m
                dp_squared = (f * L_eq / d) * (m / A) ** 2 * R * T_K
                P2_calc_Pa = math.sqrt(max(0, P1_Pa ** 2 - dp_squared))
                delta_P_kPa = (P1_Pa - P2_calc_Pa) / 1000.0

                # 校验阻塞
                is_choked = P2_calc_Pa < P2_min if P2_min > 0 else False

                # 平均参数
                P_avg_Pa = (P1_Pa + P2_calc_Pa) / 2.0
                rho_avg = self.calculate_density_ideal(P_avg_Pa, T_K, R)
                v_avg = m / (rho_avg * A) if rho_avg > 0 else 0

                results = {
                    "计算方法": "Darcy-Weisbach (等温积分)",
                    "摩擦系数 f": f,
                    "当量长度 Leq": L_eq,
                    "入口密度": rho1,
                    "出口密度": self.calculate_density_ideal(P2_calc_Pa, T_K, R),
                    "平均密度": rho_avg,
                    "入口流速": v1,
                    "平均流速": v_avg,
                    "雷诺数": Re1,
                    "马赫数": Ma,
                    "阻塞流": is_choked,
                    "出口压力_kPa": P2_calc_Pa / 1000.0,
                }
                pressure_drop_kPa = delta_P_kPa

            elif method == "darcy_avg":
                # 平均密度法
                rho2 = self.calculate_density_ideal(P2_Pa, T_K, R)
                rho_avg = (rho1 + rho2) / 2.0
                v_avg = m / (rho_avg * A) if rho_avg > 0 else 0
                delta_P_Pa = f * (L_eq / d) * (rho_avg * v_avg ** 2) / 2.0
                pressure_drop_kPa = delta_P_Pa / 1000.0

                results = {
                    "计算方法": "Darcy-Weisbach (平均密度)",
                    "摩擦系数 f": f,
                    "当量长度 Leq": L_eq,
                    "平均密度": rho_avg,
                    "平均流速": v_avg,
                    "雷诺数": Re1,
                    "马赫数": Ma,
                }

            elif method == "weymouth":
                # Weymouth 公式 (SI 单位)
                # Q = 0.0330 * ((P1² - P2²)/L)^(1/2) * D^(8/3)
                # 其中 P: kPa(abs), L: km, D: mm, Q: m³/s（标准工况 15°C, 101.325 kPa）
                L_km = L / 1000.0
                D_mm = d * 1000.0
                dp_sq = P1_kPa ** 2 - P2_kPa ** 2
                if dp_sq > 0 and L_km > 0:
                    Q_std_m3s = 0.0330 * math.sqrt(dp_sq / L_km) * D_mm ** (8.0 / 3.0)
                    Q_std_m3h = Q_std_m3s * 3600.0
                else:
                    Q_std_m3h = 0.0
                pressure_drop_kPa = P1_kPa - P2_kPa

                # 等效质量流量
                rho_std = self.calculate_density_ideal(101325.0, 288.15, R)
                m_calc = Q_std_m3s * rho_std * 3600.0

                results = {
                    "计算方法": "Weymouth公式",
                    "标准流量": Q_std_m3h,
                    "等效质量流量": m_calc,
                }

            elif method == "panhandle":
                # Panhandle A 公式 (SI)
                # Q = 0.0280 * E * ((P1²-P2²)/L)^0.5394 * D^2.6182
                # P: kPa(abs), L: km, D: mm, Q: m³/s（标准工况）
                L_km = L / 1000.0
                D_mm = d * 1000.0
                dp_sq = P1_kPa ** 2 - P2_kPa ** 2
                E = 0.92
                n_exp = 0.0793  # Panhandle A 效率指数
                if dp_sq > 0 and L_km > 0:
                    Q_std_m3s = 0.0280 * E * (dp_sq / L_km) ** 0.5394 * D_mm ** 2.6182
                    Q_std_m3h = Q_std_m3s * 3600.0
                else:
                    Q_std_m3h = 0.0
                pressure_drop_kPa = P1_kPa - P2_kPa

                rho_std = self.calculate_density_ideal(101325.0, 288.15, R)
                m_calc = Q_std_m3s * rho_std * 3600.0

                results = {
                    "计算方法": "Panhandle A公式",
                    "标准流量": Q_std_m3h,
                    "效率因子 E": E,
                    "等效质量流量": m_calc,
                }
            else:
                pressure_drop_kPa = 0
                results = {}

            self.display_results(pressure_drop_kPa, results, Ma, Re1, method)
            self.update_detail_table(results, Ma, Re1, f, method)

        except Exception as e:
            QMessageBox.warning(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def auto_calculate_flow(self):
        """基于等温积分公式反算最大质量流量"""
        try:
            d = self.diameter_input.value() / 1000.0
            L = self.length_input.value()
            eps = self.roughness_input.value() / 1000.0
            P1_kPa = self.inlet_pressure_input.value()
            P2_kPa = self.outlet_pressure_input.value()
            T_C = self.temperature_input.value()
            gamma = self.gamma_input.value()
            R = self.gas_constant_input.value()
            mu = self.viscosity_input.value() * 1e-6
            equiv_factor = self.equivalent_length_factor.value()

            P1_Pa = P1_kPa * 1000.0
            P2_Pa = P2_kPa * 1000.0
            T_K = T_C + 273.15
            A = math.pi * d ** 2 / 4.0
            L_eq = L * equiv_factor

            # 临界压比
            P_crit_ratio = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
            P2_min_Pa = P1_Pa * P_crit_ratio

            # 先用初始估算计算 f，然后迭代
            m_est = 1.0  # kg/s 初始估算
            for _ in range(30):
                rho1 = self.calculate_density_ideal(P1_Pa, T_K, R)
                v1 = m_est / (rho1 * A)
                Re = self.calculate_reynolds(d, v1, rho1, mu)
                f = self.calculate_friction_factor(Re, eps, d)

                # 等温积分反算: m = A * sqrt((P1² - P2²) * D / (f * L_eq * R * T))
                dp_sq = P1_Pa ** 2 - P2_Pa ** 2
                if dp_sq <= 0:
                    QMessageBox.information(self, "提示", "入口压力不大于出口压力，无法计算流量。")
                    return
                m_new = A * math.sqrt(dp_sq * d / (f * L_eq * R * T_K))

                if abs(m_new - m_est) / max(m_new, 1e-10) < 1e-6:
                    break
                m_est = m_new

            # 检查阻塞
            rho_out = self.calculate_density_ideal(P2_Pa, T_K, R)
            v_out = m_est / (rho_out * A)
            a_sound = math.sqrt(gamma * R * T_K)
            Ma_out = v_out / a_sound

            if P2_Pa < P2_min_Pa:
                # 阻塞流：重新计算临界出口压力对应的流量
                P2_choked = P2_min_Pa
                dp_sq_choked = P1_Pa ** 2 - P2_choked ** 2
                m_est = A * math.sqrt(dp_sq_choked * d / (f * L_eq * R * T_K))
                QMessageBox.warning(self, "阻塞流警告",
                    f"给定压差过大，出口发生阻塞流！\n"
                    f"临界出口压力: {P2_choked/1000:.1f} kPa\n"
                    f"最大质量流量: {m_est*3600:.1f} kg/h\n"
                    f"出口马赫数 ≈ 1.0")
            elif Ma_out > 0.8:
                QMessageBox.warning(self, "高速流动警告",
                    f"出口马赫数 {Ma_out:.3f}，接近声速！\n"
                    f"质量流量: {m_est*3600:.1f} kg/h")

            self.mass_flow_input.setValue(m_est * 3600.0)
            QMessageBox.information(self, "流量反算结果",
                f"基于等温积分公式反算：\n"
                f"质量流量: {m_est*3600:.1f} kg/h\n"
                f"出口马赫数: {Ma_out:.3f}")

        except Exception as e:
            QMessageBox.warning(self, "计算错误", f"流量反算失败: {str(e)}")

    # ------------------------------------------------------------------
    #  显示
    # ------------------------------------------------------------------

    def display_results(self, pressure_drop, results, mach_number, reynolds, method):
        flow_regime = "层流" if reynolds < 2000 else ("过渡流" if reynolds < 4000 else "湍流")
        compressibility = "不可压缩" if mach_number < 0.3 else ("可压缩" if mach_number < 0.8 else "高速可压缩")

        method_name = results.get("计算方法", "未知")
        html = f"""
        <h3>可压缩流体压降计算结果</h3>
        <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr style="background-color: #f8f9fa;">
            <td style="padding: 8px; font-weight: bold;">项目</td>
            <td style="padding: 8px;">计算结果</td>
            <td style="padding: 8px;">说明</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">计算方法</td>
            <td style="padding: 8px;">{method_name}</td>
            <td style="padding: 8px;">选用的计算公式</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">压降</td>
            <td style="padding: 8px; color: #9b59b6; font-weight: bold;">{pressure_drop:.2f} kPa</td>
            <td style="padding: 8px;">{'积分法精确值' if '积分' in method_name else '压力差值'}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">雷诺数</td>
            <td style="padding: 8px;">{reynolds:.0f}</td>
            <td style="padding: 8px;">{flow_regime}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">马赫数</td>
            <td style="padding: 8px; {'color: red;' if mach_number > 0.8 else 'color: green;'}">
                {mach_number:.4f}
            </td>
            <td style="padding: 8px;">{compressibility}</td>
        </tr>
        """

        # 方法特定结果
        if "出口密度" in results:
            html += f"""
        <tr><td style="padding: 8px; font-weight: bold;">出口压力</td>
            <td style="padding: 8px;">{results['出口压力_kPa']:.2f} kPa</td>
            <td style="padding: 8px;">等温积分法计算值</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">出口密度</td>
            <td style="padding: 8px;">{results['出口密度']:.3f} kg/m³</td>
            <td style="padding: 8px;"></td></tr>"""
        if "阻塞流" in results and results["阻塞流"]:
            html += """
        <tr style="background-color: #ffcccc;"><td colspan="3" style="padding: 8px; color: red; font-weight: bold;">
            ⚠️ 警告：发生阻塞流！出口马赫数 ≥ 1，实际出口压力高于计算值。</td></tr>"""
        if "标准流量" in results:
            html += f"""
        <tr><td style="padding: 8px; font-weight: bold;">标准体积流量</td>
            <td style="padding: 8px;">{results['标准流量']:.1f} m³/h</td>
            <td style="padding: 8px;">标准工况 15°C, 101.325 kPa</td></tr>"""

        html += "</table>"

        if mach_number > 0.8:
            html += """
            <h4 style="color: red;">⚠️ 警告：接近/超过音速流动</h4>
            <p>马赫数大于0.8，等温流动假设可能不成立，建议使用绝热流动模型。</p>"""
        if reynolds > 100000:
            html += """
            <h4 style="color: orange;">提示：完全湍流</h4>
            <p>雷诺数较高，摩擦系数主要取决于管道粗糙度。</p>"""

        self.result_text.setHtml(html)

    def update_detail_table(self, results, mach_number, reynolds, friction_factor, method):
        detail_data = [
            ["马赫数", f"{mach_number:.4f}", "-"],
            ["雷诺数", f"{reynolds:.0f}", "-"],
            ["摩擦系数 f", f"{friction_factor:.6f}", "-"],
            ["流动状态", "层流" if reynolds < 2000 else ("过渡流" if reynolds < 4000 else "湍流"), "-"],
            ["可压缩性", "不可压缩" if mach_number < 0.3 else ("可压缩" if mach_number < 0.8 else "高速可压缩"), "-"],
        ]
        unit_map = {
            "当量长度 Leq": "m",
            "入口密度": "kg/m³",
            "出口密度": "kg/m³",
            "平均密度": "kg/m³",
            "入口流速": "m/s",
            "平均流速": "m/s",
            "标准流量": "m³/h (标况)",
            "等效质量流量": "kg/h",
            "效率因子 E": "-",
            "出口压力_kPa": "kPa",
        }
        for key, value in results.items():
            if key == "计算方法":
                continue
            if isinstance(value, bool):
                detail_data.append([key, "是" if value else "否", "-"])
            elif isinstance(value, (int, float)):
                unit = unit_map.get(key, "-")
                detail_data.append([key, f"{value:.4f}", unit])

        self.detail_table.setRowCount(len(detail_data))
        for i, row_data in enumerate(detail_data):
            for j, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                item.setTextAlignment(Qt.AlignCenter)
                self.detail_table.setItem(i, j, item)
        header = self.detail_table.horizontalHeader()
        for col in range(3):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

    def clear_inputs(self):
        self.fluid_combo.setCurrentIndex(0)
        self.molecular_weight_input.setValue(28.97)
        self.gamma_input.setValue(1.4)
        self.gas_constant_input.setValue(287)
        self.viscosity_input.setValue(18.27)
        self.diameter_input.setValue(100)
        self.length_input.setValue(100)
        self.roughness_input.setValue(0.046)
        self.pipe_shape_combo.setCurrentIndex(0)
        self.equivalent_length_factor.setValue(1.5)
        self.inlet_pressure_input.setValue(500)
        self.outlet_pressure_input.setValue(400)
        self.temperature_input.setValue(20)
        self.mass_flow_input.setValue(1000)
        self.darcy_radio.setChecked(True)
        self.result_text.clear()
        self.detail_table.setRowCount(0)

    def _get_history_data(self):
        method = self.get_selected_method()
        inputs = {
            "计算方法": method,
            "管道直径_mm": self.diameter_input.value(),
            "管道长度_m": self.length_input.value(),
            "粗糙度_mm": self.roughness_input.value(),
            "入口压力_kPa": self.inlet_pressure_input.value(),
            "出口压力_kPa": self.outlet_pressure_input.value(),
            "温度_C": self.temperature_input.value(),
            "质量流量_kg_h": self.mass_flow_input.value(),
            "分子量": self.molecular_weight_input.value(),
            "绝热指数": self.gamma_input.value(),
        }
        outputs = {}
        try:
            d = self.diameter_input.value() / 1000.0
            T_K = self.temperature_input.value() + 273.15
            R = self.gas_constant_input.value()
            mu = self.viscosity_input.value() * 1e-6
            P1 = self.inlet_pressure_input.value() * 1000.0
            rho1 = P1 / (R * T_K)
            m = self.mass_flow_input.value() / 3600.0
            A = math.pi * d ** 2 / 4.0
            v1 = m / (rho1 * A)
            Re = self.calculate_reynolds(d, v1, rho1, mu)
            f = self.calculate_friction_factor(Re, self.roughness_input.value() / 1000.0, d)
            gamma = self.gamma_input.value()
            a = math.sqrt(gamma * R * T_K)
            outputs = {
                "入口密度_kg_m3": round(rho1, 4),
                "入口流速_m_s": round(v1, 2),
                "雷诺数": round(Re, 0),
                "摩擦系数": round(f, 6),
                "马赫数": round(v1 / a, 4),
                "压降_kPa": round(self.inlet_pressure_input.value() - self.outlet_pressure_input.value(), 2),
            }
        except Exception as e:
            outputs["计算错误"] = str(e)
        return {"inputs": inputs, "outputs": outputs}


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = CompressibleFlowPressureDrop()
    widget.resize(900, 750)
    widget.show()
    sys.exit(app.exec())
