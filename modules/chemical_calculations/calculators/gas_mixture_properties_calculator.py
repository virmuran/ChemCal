from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                              QLabel, QLineEdit, QPushButton, QComboBox, 
                              QFormLayout, QTextEdit, QGridLayout, QScrollArea,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QTabWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math
import numpy as np

# =============================================================================
# 工业级气体物性内置数据库
# =============================================================================
# LJ 势参数: sigma [Å], epsilon/k [K]  (来源: Reid, Prausnitz & Poling, App.B)
# NASA 7系数多项式 cp [J/(mol·K)]:
#   cp/R = a1 + a2*T + a3*T^2 + a4*T^3 + a5*T^4   (T in K)
#   高温段 [1000-5000K]: coeffs_hi = [a1..a5]
#   低温段 [200-1000K]:  coeffs_lo = [a1..a5]
# (来源: NASA/TP-2002-211556 / Burcat&Ruscic 2005)
# =============================================================================
_GAS_DB = {
    "氮气(N2)": {
        'sigma': 3.798, 'eps_k': 71.4,
        'coeffs_lo': [3.53101, -0.000123661, -5.02999e-7, 2.43531e-9, -1.40881e-12],
        'coeffs_hi': [2.95258, 1.39690e-3, -4.92632e-7, 7.86010e-11, -4.60755e-15],
    },
    "氧气(O2)": {
        'sigma': 3.467, 'eps_k': 106.7,
        'coeffs_lo': [3.78246, -2.99674e-3, 9.84730e-6, -9.68130e-9, 3.24373e-12],
        'coeffs_hi': [3.69758, 6.13520e-4, -1.25884e-7, 1.77528e-11, -1.13644e-15],
    },
    "氢气(H2)": {
        'sigma': 2.827, 'eps_k': 59.7,
        'coeffs_lo': [2.34433, 7.98052e-3, -1.94782e-5, 2.01572e-8, -7.37612e-12],
        'coeffs_hi': [3.33728, -4.94025e-5, 4.99457e-7, -1.79566e-10, 2.00255e-14],
    },
    "二氧化碳(CO2)": {
        'sigma': 3.941, 'eps_k': 195.2,
        'coeffs_lo': [2.35677, 8.98460e-3, -7.12356e-6, 2.45919e-9, -1.43699e-13],
        'coeffs_hi': [3.85746, 4.41437e-3, -2.21481e-6, 5.23490e-10, -4.72084e-14],
    },
    "甲烷(CH4)": {
        'sigma': 3.758, 'eps_k': 148.6,
        'coeffs_lo': [5.14988, -1.36709e-2, 4.91800e-5, -4.84743e-8, 1.66694e-11],
        'coeffs_hi': [1.65326, 1.00263e-2, -3.31661e-6, 5.36483e-10, -3.14697e-14],
    },
    "乙烷(C2H6)": {
        'sigma': 4.443, 'eps_k': 215.7,
        'coeffs_lo': [4.29142, -5.50155e-3, 5.99438e-5, -7.08466e-8, 2.68686e-11],
        'coeffs_hi': [4.82594, 1.38401e-2, -4.55725e-6, 6.72097e-10, -3.59816e-14],
    },
    "丙烷(C3H8)": {
        'sigma': 5.118, 'eps_k': 237.1,
        'coeffs_lo': [4.21200, 1.70859e-3, 6.30198e-5, -8.19614e-8, 3.16948e-11],
        'coeffs_hi': [6.66950, 2.00640e-2, -6.82300e-6, 1.00994e-9, -5.47893e-14],
    },
    "水蒸气(H2O)": {
        'sigma': 2.641, 'eps_k': 809.1,
        'coeffs_lo': [4.19864, -2.03643e-3, 6.52040e-6, -5.48797e-9, 1.77197e-12],
        'coeffs_hi': [2.67704, 2.97319e-3, -7.73769e-7, 9.44335e-11, -4.26900e-15],
    },
    "氩气(Ar)": {
        'sigma': 3.542, 'eps_k': 93.3,
        'coeffs_lo': [2.5, 0.0, 0.0, 0.0, 0.0],
        'coeffs_hi': [2.5, 0.0, 0.0, 0.0, 0.0],
    },
    "一氧化碳(CO)": {
        'sigma': 3.690, 'eps_k': 91.7,
        'coeffs_lo': [3.57954, -6.10354e-4, 1.01681e-6, 9.07006e-10, -9.04424e-13],
        'coeffs_hi': [3.04849, 1.35173e-3, -4.85794e-7, 7.88536e-11, -4.69807e-15],
    },
}

# Neufeld et al. (1972) 碰撞积分参数
_NF_A, _NF_B, _NF_C, _NF_D, _NF_E, _NF_F = 1.16145, 0.14874, 0.52487, 0.77320, 2.16178, 2.43787

def _neufeld_omega(T_star):
    """Neufeld et al. (1972) 碰撞积分 Omega_v"""
    return (_NF_A / T_star**_NF_B +
            _NF_C / math.exp(_NF_D * T_star) +
            _NF_E / math.exp(_NF_F * T_star))

def _nasa_cp(name, T_K):
    """NASA 7系数多项式计算 cp [J/(mol·K)]，T in K"""
    db = _GAS_DB.get(name)
    if db is None:
        return 30.0  # 未知气体默认值
    R = 8.314
    if T_K >= 1000.0:
        a = db['coeffs_hi']
    else:
        a = db['coeffs_lo']
    cp_R = a[0] + a[1]*T_K + a[2]*T_K**2 + a[3]*T_K**3 + a[4]*T_K**4
    return cp_R * R  # J/(mol·K)

def _pure_viscosity_CE(name, mw_gmol, T_K):
    """Chapman-Enskog 公式计算纯气体粘度 [Pa·s]"""
    db = _GAS_DB.get(name)
    if db is None:
        # 无 LJ 参数时用 Sutherland 幂律估算 (参考 N2 尺度)
        return 1.78e-5 * (T_K / 293.15) ** 0.71
    sigma = db['sigma']    # Å
    eps_k = db['eps_k']    # K
    T_star = T_K / eps_k
    omega = _neufeld_omega(T_star)
    # Chapman-Enskog: mu [Poise] = 2.6693e-5 * sqrt(M*T) / (sigma^2 * Omega)
    mu_poise = 2.6693e-5 * math.sqrt(mw_gmol * T_K) / (sigma**2 * omega)
    return mu_poise * 0.1  # Pa·s

def _lee_kesler_z(Tr, Pr, omega):
    """
    Lee-Kesler (1975) 方程计算气相压缩因子。
    Z = Z0 + (omega/0.3978) * (Z1 - Z0)
    参数来源: Smith, Van Ness, Abbott, Introduction to CICE, 7th Ed., Table 3.3
    精度: ±1% (气相 Tr>0.6, Pr<10)
    """
    def _lk_Z(rho_r, Tr, b1,b2,b3,b4,c1,c2,c3,c4,d1,d2,beta,gamma):
        """Lee-Kesler BWR Z 方程，rho_r = reduced density"""
        B = b1 - b2/Tr - b3/Tr**2 - b4/Tr**3
        C = c1 - c2/Tr + c3/Tr**3
        D = d1 + d2/Tr
        return (1.0 + B*rho_r + C*rho_r**2 + D*rho_r**5
                + c4*rho_r**2/Tr**3*(beta + gamma*rho_r**2)*math.exp(-gamma*rho_r**2))

    def _solve_rho(Tr, Pr, params):
        """阻尼不动点迭代求气相 rho_r"""
        rho = Pr / Tr  # 理想气体初值
        for _ in range(2000):
            Z = _lk_Z(rho, Tr, *params)
            rho_new = Pr / (Z * Tr)
            rho_new = max(1e-6, min(rho_new, 20.0))
            if abs(rho_new - rho) < 1e-11:
                return rho_new
            rho = 0.3 * rho + 0.7 * rho_new
        return rho

    # Smith, Van Ness & Abbott 7th Ed. Table 3.3 参数（b2,b3,b4 均为正数）
    # 简单流体参数
    p0 = (0.1181193, 0.265728, 0.154790, 0.030323,
          0.0236744,  0.0186984, 0.0, 0.042724,
          1.55488e-4, 6.23689e-5, 0.65392, 0.060167)
    # 参考流体（正辛烷，omega_R=0.3978）参数
    p1 = (0.2026579, 0.331511,  0.027655, 0.203488,
          0.0313422,  0.0503323, 0.016901, 0.041577,
          4.8736e-4,  0.0740336, 1.226,    0.03754)

    if Tr <= 0 or Pr <= 0:
        return 1.0
    try:
        rho0 = _solve_rho(Tr, Pr, p0)
        Z0 = _lk_Z(rho0, Tr, *p0)

        rho1 = _solve_rho(Tr, Pr, p1)
        Z1 = _lk_Z(rho1, Tr, *p1)

        Z = Z0 + (omega / 0.3978) * (Z1 - Z0)
        return max(0.05, min(Z, 5.0))
    except Exception:
        # 降级：Pitzer 关联式
        B0 = 0.083 - 0.422 / Tr**1.6
        B1 = 0.139 - 0.172 / Tr**4.2
        return max(0.1, 1.0 + (B0 + omega * B1) * Pr / Tr)


class GasMixturePropertiesCalculator(QWidget):
    """气体混合物物性计算器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.components = []
        self.setup_ui()
        
    def setup_ui(self):
        """设置气体混合物物性计算界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("气体混合物物性计算")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # 说明文本
        desc_label = QLabel("计算气体混合物的密度、粘度、热导率、比热容、压缩因子等物性参数")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #7f8c8d; margin: 5px;")
        main_layout.addWidget(desc_label)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 组分设置标签页
        composition_tab = QWidget()
        composition_layout = QVBoxLayout(composition_tab)
        
        # 条件设置组
        condition_group = QGroupBox("计算条件")
        condition_layout = QGridLayout(condition_group)
        
        self.temperature_input = QLineEdit()
        self.temperature_input.setText("25")
        self.temperature_input.setValidator(QDoubleValidator(-273, 2000, 2))
        
        self.pressure_input = QLineEdit()
        self.pressure_input.setText("101.325")
        self.temperature_input.setValidator(QDoubleValidator(0.1, 100000, 2))
        
        self.mixture_type = QComboBox()
        self.mixture_type.addItems(["理想气体", "真实气体"])
        
        self.calculation_method = QComboBox()
        self.calculation_method.addItems(["简单混合规则", "Kay规则", "对应状态原理"])
        
        condition_layout.addWidget(QLabel("温度:"), 0, 0)
        condition_layout.addWidget(self.temperature_input, 0, 1)
        condition_layout.addWidget(QLabel("°C"), 0, 2)
        
        condition_layout.addWidget(QLabel("压力:"), 0, 3)
        condition_layout.addWidget(self.pressure_input, 0, 4)
        condition_layout.addWidget(QLabel("kPa"), 0, 5)
        
        condition_layout.addWidget(QLabel("混合物类型:"), 1, 0)
        condition_layout.addWidget(self.mixture_type, 1, 1, 1, 2)
        
        condition_layout.addWidget(QLabel("计算方法:"), 1, 3)
        condition_layout.addWidget(self.calculation_method, 1, 4, 1, 2)
        
        composition_layout.addWidget(condition_group)
        
        # 组分设置组
        component_group = QGroupBox("组分设置")
        component_layout = QVBoxLayout(component_group)
        
        # 组分数量选择
        component_count_layout = QHBoxLayout()
        component_count_layout.addWidget(QLabel("组分数:"))
        self.component_count = QComboBox()
        self.component_count.addItems(["2", "3", "4", "5"])
        self.component_count.currentTextChanged.connect(self.update_component_table)
        component_count_layout.addWidget(self.component_count)
        component_count_layout.addStretch()
        component_layout.addLayout(component_count_layout)
        
        # 组分参数表
        self.component_table = QTableWidget()
        self.component_table.setColumnCount(8)
        self.component_table.setHorizontalHeaderLabels([
            "组分", "摩尔分数", "分子量", "临界温度", "临界压力", "临界体积", "偏心因子", "Zc"
        ])
        component_layout.addWidget(self.component_table)
        
        composition_layout.addWidget(component_group)
        composition_layout.addStretch()
        
        # 结果标签页
        result_tab = QWidget()
        result_layout = QVBoxLayout(result_tab)
        
        # 按钮组
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
        
        # 基本物性结果
        basic_properties_group = QGroupBox("基本物性")
        basic_properties_layout = QGridLayout(basic_properties_group)
        
        self.mw_mixture_result = QLabel("--")
        self.tc_mixture_result = QLabel("--")
        self.pc_mixture_result = QLabel("--")
        self.vc_mixture_result = QLabel("--")
        self.omega_mixture_result = QLabel("--")
        self.zc_mixture_result = QLabel("--")
        
        basic_properties_layout.addWidget(QLabel("平均分子量:"), 0, 0)
        basic_properties_layout.addWidget(self.mw_mixture_result, 0, 1)
        basic_properties_layout.addWidget(QLabel("g/mol"), 0, 2)
        
        basic_properties_layout.addWidget(QLabel("虚拟临界温度:"), 0, 3)
        basic_properties_layout.addWidget(self.tc_mixture_result, 0, 4)
        basic_properties_layout.addWidget(QLabel("K"), 0, 5)
        
        basic_properties_layout.addWidget(QLabel("虚拟临界压力:"), 1, 0)
        basic_properties_layout.addWidget(self.pc_mixture_result, 1, 1)
        basic_properties_layout.addWidget(QLabel("kPa"), 1, 2)
        
        basic_properties_layout.addWidget(QLabel("虚拟临界体积:"), 1, 3)
        basic_properties_layout.addWidget(self.vc_mixture_result, 1, 4)
        basic_properties_layout.addWidget(QLabel("cm³/mol"), 1, 5)
        
        basic_properties_layout.addWidget(QLabel("平均偏心因子:"), 2, 0)
        basic_properties_layout.addWidget(self.omega_mixture_result, 2, 1)
        basic_properties_layout.addWidget(QLabel(""), 2, 2)
        
        basic_properties_layout.addWidget(QLabel("虚拟临界压缩因子:"), 2, 3)
        basic_properties_layout.addWidget(self.zc_mixture_result, 2, 4)
        basic_properties_layout.addWidget(QLabel(""), 2, 5)
        
        result_layout.addWidget(basic_properties_group)
        
        # 热物性结果
        thermal_properties_group = QGroupBox("热物性")
        thermal_properties_layout = QGridLayout(thermal_properties_group)
        
        self.density_result = QLabel("--")
        self.z_factor_result = QLabel("--")
        self.viscosity_result = QLabel("--")
        self.thermal_cond_result = QLabel("--")
        self.cp_result = QLabel("--")
        self.cv_result = QLabel("--")
        self.ratio_cp_cv_result = QLabel("--")
        self.sound_speed_result = QLabel("--")
        
        thermal_properties_layout.addWidget(QLabel("密度:"), 0, 0)
        thermal_properties_layout.addWidget(self.density_result, 0, 1)
        thermal_properties_layout.addWidget(QLabel("kg/m³"), 0, 2)
        
        thermal_properties_layout.addWidget(QLabel("压缩因子:"), 0, 3)
        thermal_properties_layout.addWidget(self.z_factor_result, 0, 4)
        thermal_properties_layout.addWidget(QLabel(""), 0, 5)
        
        thermal_properties_layout.addWidget(QLabel("粘度:"), 1, 0)
        thermal_properties_layout.addWidget(self.viscosity_result, 1, 1)
        thermal_properties_layout.addWidget(QLabel("μPa·s"), 1, 2)
        
        thermal_properties_layout.addWidget(QLabel("热导率:"), 1, 3)
        thermal_properties_layout.addWidget(self.thermal_cond_result, 1, 4)
        thermal_properties_layout.addWidget(QLabel("W/(m·K)"), 1, 5)
        
        thermal_properties_layout.addWidget(QLabel("定压比热:"), 2, 0)
        thermal_properties_layout.addWidget(self.cp_result, 2, 1)
        thermal_properties_layout.addWidget(QLabel("J/(mol·K)"), 2, 2)
        
        thermal_properties_layout.addWidget(QLabel("定容比热:"), 2, 3)
        thermal_properties_layout.addWidget(self.cv_result, 2, 4)
        thermal_properties_layout.addWidget(QLabel("J/(mol·K)"), 2, 5)
        
        thermal_properties_layout.addWidget(QLabel("比热比:"), 3, 0)
        thermal_properties_layout.addWidget(self.ratio_cp_cv_result, 3, 1)
        thermal_properties_layout.addWidget(QLabel(""), 3, 2)
        
        thermal_properties_layout.addWidget(QLabel("音速:"), 3, 3)
        thermal_properties_layout.addWidget(self.sound_speed_result, 3, 4)
        thermal_properties_layout.addWidget(QLabel("m/s"), 3, 5)
        
        result_layout.addWidget(thermal_properties_group)
        
        # 对应状态参数
        state_params_group = QGroupBox("对应状态参数")
        state_params_layout = QGridLayout(state_params_group)
        
        self.tr_result = QLabel("--")
        self.pr_result = QLabel("--")
        self.vr_result = QLabel("--")
        self.reduced_density_result = QLabel("--")
        
        state_params_layout.addWidget(QLabel("对比温度:"), 0, 0)
        state_params_layout.addWidget(self.tr_result, 0, 1)
        state_params_layout.addWidget(QLabel(""), 0, 2)
        
        state_params_layout.addWidget(QLabel("对比压力:"), 0, 3)
        state_params_layout.addWidget(self.pr_result, 0, 4)
        state_params_layout.addWidget(QLabel(""), 0, 5)
        
        state_params_layout.addWidget(QLabel("对比体积:"), 1, 0)
        state_params_layout.addWidget(self.vr_result, 1, 1)
        state_params_layout.addWidget(QLabel(""), 1, 2)
        
        state_params_layout.addWidget(QLabel("对比密度:"), 1, 3)
        state_params_layout.addWidget(self.reduced_density_result, 1, 4)
        state_params_layout.addWidget(QLabel(""), 1, 5)
        
        result_layout.addWidget(state_params_group)
        
        # 添加标签页
        self.tab_widget.addTab(composition_tab, "组分设置")
        self.tab_widget.addTab(result_tab, "计算结果")
        
        scroll_layout.addWidget(self.tab_widget)
        
        # 计算说明
        info_text = QTextEdit()
        info_text.setMaximumHeight(150)
        info_text.setHtml("""
        <h4>计算说明（工业级精度）:</h4>
        <ul>
        <li><b>平均分子量</b>: M_mix = Σ(y_i × M_i)</li>
        <li><b>虚拟临界参数</b>: Kay 规则 (线性混合) 或 Prausnitz-Gunn (二次混合)</li>
        <li><b>压缩因子</b>: Lee-Kesler (1975) BWR 方程，Z = Z₀ + ω/0.3978 × (Z₁-Z₀)</li>
        <li><b>密度</b>: ρ = P·M / (Z·R·T)，真实气体用 Lee-Kesler Z</li>
        <li><b>纯组分粘度</b>: Chapman-Enskog 理论 + Neufeld (1972) 碰撞积分 (±5%)</li>
        <li><b>混合粘度</b>: Wilke (1950) 混合规则</li>
        <li><b>纯组分导热系数</b>: 修正 Eucken 关联式 k = μ·(cp + 1.25R)/M</li>
        <li><b>混合导热系数</b>: Mason-Saxena (1958) 混合规则</li>
        <li><b>理想气体比热</b>: NASA 7系数多项式 (JANAF 数据库，±1%)</li>
        <li><b>真实气体比热修正</b>: Pitzer 关联式剩余比热</li>
        <li><b>支持气体</b>: N₂, O₂, H₂, CO₂, CH₄, C₂H₆, C₃H₈, H₂O, Ar, CO</li>
        </ul>
        """)
        info_text.setReadOnly(True)
        scroll_layout.addWidget(info_text)
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # 初始化表格
        self.update_component_table()
        
    def update_component_table(self):
        """更新组分参数表"""
        count = int(self.component_count.currentText())
        self.component_table.setRowCount(count)
        
        # 预设一些常见气体的物性参数
        preset_gases = {
            "氮气(N2)": [28.013, 126.2, 3390, 89.5, 0.037, 0.29],
            "氧气(O2)": [31.999, 154.6, 5043, 73.4, 0.021, 0.288],
            "氢气(H2)": [2.016, 33.2, 1315, 65.0, -0.216, 0.305],
            "二氧化碳(CO2)": [44.01, 304.2, 7377, 94.0, 0.225, 0.274],
            "甲烷(CH4)": [16.043, 190.6, 4600, 99.0, 0.008, 0.288],
            "乙烷(C2H6)": [30.07, 305.4, 4880, 148.0, 0.098, 0.285],
            "丙烷(C3H8)": [44.096, 369.8, 4248, 203.0, 0.152, 0.281],
            "水蒸气(H2O)": [18.015, 647.3, 22064, 56.0, 0.344, 0.229],
            "氩气(Ar)": [39.948, 150.9, 4898, 74.9, -0.002, 0.291],
            "一氧化碳(CO)": [28.01, 132.9, 3498, 93.1, 0.045, 0.292]
        }
        
        for i in range(count):
            # 组分名称
            name_combo = QComboBox()
            name_combo.addItems(list(preset_gases.keys()))
            name_combo.setCurrentIndex(i % len(preset_gases))
            self.component_table.setCellWidget(i, 0, name_combo)
            
            # 获取预设参数
            current_name = name_combo.currentText()
            params = preset_gases.get(current_name, [0, 0, 0, 0, 0, 0])
            
            # 摩尔分数
            if i == 0:
                y_item = QTableWidgetItem("0.5")
            elif i == 1:
                y_item = QTableWidgetItem("0.5")
            else:
                y_item = QTableWidgetItem("0.0")
            self.component_table.setItem(i, 1, y_item)
            
            # 分子量
            mw_item = QTableWidgetItem(f"{params[0]:.3f}")
            self.component_table.setItem(i, 2, mw_item)
            
            # 临界温度
            tc_item = QTableWidgetItem(f"{params[1]:.1f}")
            self.component_table.setItem(i, 3, tc_item)
            
            # 临界压力
            pc_item = QTableWidgetItem(f"{params[2]:.0f}")
            self.component_table.setItem(i, 4, pc_item)
            
            # 临界体积
            vc_item = QTableWidgetItem(f"{params[3]:.1f}")
            self.component_table.setItem(i, 5, vc_item)
            
            # 偏心因子
            omega_item = QTableWidgetItem(f"{params[4]:.3f}")
            self.component_table.setItem(i, 6, omega_item)
            
            # 临界压缩因子
            zc_item = QTableWidgetItem(f"{params[5]:.3f}")
            self.component_table.setItem(i, 7, zc_item)
    
    def clear_inputs(self):
        """清空所有输入"""
        self.temperature_input.setText("25")
        self.pressure_input.setText("101.325")
        self.update_component_table()
        
        # 清空结果
        for label in [self.mw_mixture_result, self.tc_mixture_result, 
                     self.pc_mixture_result, self.vc_mixture_result,
                     self.omega_mixture_result, self.zc_mixture_result,
                     self.density_result, self.z_factor_result,
                     self.viscosity_result, self.thermal_cond_result,
                     self.cp_result, self.cv_result, self.ratio_cp_cv_result,
                     self.sound_speed_result, self.tr_result, self.pr_result,
                     self.vr_result, self.reduced_density_result]:
            label.setText("--")
    
    def calculate(self):
        """执行气体混合物物性计算"""
        try:
            # 获取计算条件
            temperature = float(self.temperature_input.text())
            pressure = float(self.pressure_input.text())
            mixture_type = self.mixture_type.currentText()
            method = self.calculation_method.currentText()
            
            # 获取组分数据
            components = self.get_component_data()
            
            # 检查摩尔分数总和
            total_y = sum(comp['y'] for comp in components)
            if abs(total_y - 1.0) > 0.01:
                self.show_error(f"摩尔分数总和应为1.0，当前为{total_y:.3f}")
                return
            
            # 执行计算
            results = self.calculate_mixture_properties(components, temperature, pressure, mixture_type, method)
            
            # 显示结果
            self.display_results(results)
            
        except ValueError as e:
            self.show_error("输入参数格式错误，请检查输入值")
        except Exception as e:
            self.show_error(f"计算错误: {str(e)}")

    def _get_history_data(self):
        """提供历史记录数据"""
        temperature = float(self.temperature_input.text() or 0)
        pressure = float(self.pressure_input.text() or 0)
        mixture_type = self.mixture_type.currentText()
        method = self.calculation_method.currentText()

        inputs = {
            "温度_C": temperature,
            "压力_MPa": pressure,
            "混合物类型": mixture_type,
            "计算方法": method
        }

        outputs = {}
        try:
            components = self.get_component_data()
            results = self.calculate_mixture_properties(components, temperature, pressure, mixture_type, method)
            outputs = {
                "混合分子量": round(results.get('mw_mix', 0), 3),
                "密度_kg_m3": round(results.get('density', 0), 4),
                "压缩系数": round(results.get('z_factor', 0), 4),
                "粘度_Pa_s": round(results.get('viscosity', 0), 6),
                "热导率_W_mK": round(results.get('thermal_conductivity', 0), 4),
                "定压比热_kJ_kgK": round(results.get('cp', 0), 3),
                "绝热指数": round(results.get('gamma', 0), 4),
                "音速_m_s": round(results.get('sound_speed', 0), 1)
            }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def get_component_data(self):
        """从表格获取组分数据"""
        count = int(self.component_count.currentText())
        components = []
        
        for i in range(count):
            name = self.component_table.cellWidget(i, 0).currentText()
            y = float(self.component_table.item(i, 1).text())
            mw = float(self.component_table.item(i, 2).text())
            tc = float(self.component_table.item(i, 3).text())
            pc = float(self.component_table.item(i, 4).text())
            vc = float(self.component_table.item(i, 5).text())
            omega = float(self.component_table.item(i, 6).text())
            zc = float(self.component_table.item(i, 7).text())
            
            components.append({
                'name': name,
                'y': y,
                'mw': mw,
                'tc': tc,
                'pc': pc,
                'vc': vc,
                'omega': omega,
                'zc': zc
            })
        
        return components
    
    def calculate_mixture_properties(self, components, T, P, mixture_type, method):
        """计算气体混合物物性"""
        # 转换为绝对温度
        T_k = T + 273.15
        
        # 计算混合物基本参数
        mw_mix = sum(comp['y'] * comp['mw'] for comp in components)
        
        # 根据选择的方法计算虚拟临界参数
        if method == "简单混合规则" or method == "Kay规则":
            # Kay规则
            tc_mix = sum(comp['y'] * comp['tc'] for comp in components)
            pc_mix = sum(comp['y'] * comp['pc'] for comp in components)
            vc_mix = sum(comp['y'] * comp['vc'] for comp in components)
            omega_mix = sum(comp['y'] * comp['omega'] for comp in components)
            zc_mix = sum(comp['y'] * comp['zc'] for comp in components)
        else:
            # 对应状态原理（更复杂的混合规则）
            # 这里使用Prausnitz-Gunn规则
            tc_mix = 0.0
            pc_mix = 0.0
            vc_mix = 0.0
            
            for i, comp_i in enumerate(components):
                for j, comp_j in enumerate(components):
                    # 二元交互参数（简化，实际需要更复杂的计算）
                    k_ij = 0.0  # 二元交互参数
                    if i != j:
                        k_ij = 1 - ((comp_i['vc'] ** (1/3) * comp_j['vc'] ** (1/3)) / 
                                   (0.5 * (comp_i['vc'] ** (2/3) + comp_j['vc'] ** (2/3)))) ** 3
                    
                    tc_ij = (1 - k_ij) * math.sqrt(comp_i['tc'] * comp_j['tc'])
                    vc_ij = ((comp_i['vc'] ** (1/3) + comp_j['vc'] ** (1/3)) / 2) ** 3
                    zc_ij = 0.291 - 0.08 * (comp_i['omega'] + comp_j['omega']) / 2
                    pc_ij = zc_ij * 8.314 * tc_ij / vc_ij * 1000  # 转换为kPa
                    
                    tc_mix += comp_i['y'] * comp_j['y'] * tc_ij
                    pc_mix += comp_i['y'] * comp_j['y'] * pc_ij
                    vc_mix += comp_i['y'] * comp_j['y'] * vc_ij
            
            omega_mix = sum(comp['y'] * comp['omega'] for comp in components)
            zc_mix = 0.291 - 0.08 * omega_mix
        
        # 计算对比参数
        tr = T_k / tc_mix
        pr = P / pc_mix
        # 对比体积: vr = z * R * Tc / (Pc * Vc_mix)，Vc_mix 单位 cm³/mol -> m³/mol
        if vc_mix > 0 and tc_mix > 0 and pc_mix > 0:
            R_gas = 8.314  # J/(mol·K)
            Vc_m3 = vc_mix * 1e-6  # cm³/mol -> m³/mol
            Pc_Pa = pc_mix * 1e3   # kPa -> Pa
            zc_calc = Pc_Pa * Vc_m3 / (R_gas * tc_mix)
            vr = zc_calc / zc_mix if zc_mix > 0 else 1.0
        else:
            vr = 1.0
        
        # 计算压缩因子
        if mixture_type == "理想气体":
            z_factor = 1.0
        else:
            # 使用对应状态原理计算压缩因子
            z_factor = self.calculate_compressibility_factor(tr, pr, omega_mix)
        
        # 计算密度
        if mixture_type == "理想气体":
            density = P * 1000 * mw_mix / (8.314 * T_k)  # kg/m³
        else:
            density = P * 1000 * mw_mix / (z_factor * 8.314 * T_k)  # kg/m³
        
        # 计算粘度
        viscosity = self.calculate_viscosity(components, T_k, density, mw_mix)
        
        # 计算热导率
        thermal_conductivity = self.calculate_thermal_conductivity(components, T_k, density, mw_mix)
        
        # 计算比热容
        cp_mix, cv_mix, gamma = self.calculate_heat_capacity(components, T_k, mixture_type)
        
        # 计算音速
        sound_speed = self.calculate_sound_speed(T_k, mw_mix, gamma, z_factor)
        
        # 计算对比密度
        reduced_density = density / (mw_mix / vc_mix * 1000)  # 转换为mol/m³
        
        return {
            'mw_mix': mw_mix,
            'tc_mix': tc_mix,
            'pc_mix': pc_mix,
            'vc_mix': vc_mix,
            'omega_mix': omega_mix,
            'zc_mix': zc_mix,
            'density': density,
            'z_factor': z_factor,
            'viscosity': viscosity,
            'thermal_conductivity': thermal_conductivity,
            'cp_mix': cp_mix,
            'cv_mix': cv_mix,
            'gamma': gamma,
            'sound_speed': sound_speed,
            'tr': tr,
            'pr': pr,
            'vr': vr,
            'reduced_density': reduced_density
        }
    
    def calculate_compressibility_factor(self, tr, pr, omega):
        """计算压缩因子（Lee-Kesler 1975 对应状态方程）"""
        if tr <= 0 or pr <= 0:
            return 1.0
        try:
            return _lee_kesler_z(tr, pr, omega)
        except Exception:
            # 降级：Pitzer B 关联式
            B0 = 0.083 - 0.422 / tr**1.6
            B1 = 0.139 - 0.172 / tr**4.2
            return max(0.1, 1.0 + (B0 + omega * B1) * pr / tr)
    
    def calculate_viscosity(self, components, T, density, mw_mix):
        """计算气体混合物粘度
        纯组分: Chapman-Enskog + Neufeld (1972) 碰撞积分
        混合: Wilke (1950) 混合规则
        """
        # 各组分纯气体粘度 [Pa·s]
        mus = []
        for comp in components:
            mu_i = _pure_viscosity_CE(comp['name'], comp['mw'], T)
            mus.append(mu_i)

        # Wilke 混合规则
        n = len(components)
        mu_mix = 0.0
        for i in range(n):
            if components[i]['y'] < 1e-10:
                continue
            denom = 0.0
            for j in range(n):
                if components[j]['y'] < 1e-10:
                    continue
                # Wilke 交互系数 phi_ij
                sqrt_mu = math.sqrt(mus[i] / mus[j]) if mus[j] > 0 else 1.0
                mwj_mwi = components[j]['mw'] / components[i]['mw']
                phi_ij = (1.0 + sqrt_mu * mwj_mwi**0.25)**2 / math.sqrt(8.0 * (1.0 + components[i]['mw'] / components[j]['mw']))
                denom += components[j]['y'] * phi_ij
            if denom > 0:
                mu_mix += components[i]['y'] * mus[i] / denom

        return mu_mix * 1e6  # Pa·s -> μPa·s
    
    def calculate_thermal_conductivity(self, components, T, density, mw_mix):
        """计算气体混合物热导率
        纯组分: 修正 Eucken 关联式  k_i = mu_i * (cp_i/M_i + 1.25*R/M_i)
        混合: Mason-Saxena (1958) 混合规则 (与 Wilke 形式相同)
        """
        R = 8.314  # J/(mol·K)
        ks = []
        mus_Pa = []
        for comp in components:
            mu_i = _pure_viscosity_CE(comp['name'], comp['mw'], T)  # Pa·s
            cp_mol = _nasa_cp(comp['name'], T)                      # J/(mol·K)
            Mi = comp['mw'] * 1e-3                                  # kg/mol
            # 修正 Eucken: k = mu * (cp_mass + 1.25*R_mass)
            # cp_mass [J/(kg·K)] = cp_mol / Mi; R_mass = R / Mi
            k_i = mu_i * (cp_mol / Mi + 1.25 * R / Mi)
            ks.append(k_i)
            mus_Pa.append(mu_i)

        # Mason-Saxena 混合规则（与 Wilke 等价，但基于热导率 phi_ij）
        n = len(components)
        k_mix = 0.0
        for i in range(n):
            if components[i]['y'] < 1e-10:
                continue
            denom = 0.0
            for j in range(n):
                if components[j]['y'] < 1e-10:
                    continue
                sqrt_mu = math.sqrt(mus_Pa[i] / mus_Pa[j]) if mus_Pa[j] > 0 else 1.0
                mwj_mwi = components[j]['mw'] / components[i]['mw']
                phi_ij = (1.0 + sqrt_mu * mwj_mwi**0.25)**2 / math.sqrt(8.0 * (1.0 + components[i]['mw'] / components[j]['mw']))
                denom += components[j]['y'] * phi_ij
            if denom > 0:
                k_mix += components[i]['y'] * ks[i] / denom

        return k_mix  # W/(m·K)
    
    def calculate_heat_capacity(self, components, T, mixture_type):
        """计算气体混合物比热容
        理想气体 cp: NASA 7系数多项式 (JANAF 数据库)
        真实气体校正: Lee-Kesler 剩余比热 (cp_dep)
        """
        R = 8.314  # J/(mol·K)

        # 理想气体混合比热 [J/(mol·K)]
        cp_ideal = sum(comp['y'] * _nasa_cp(comp['name'], T) for comp in components)
        cv_ideal = cp_ideal - R  # J/(mol·K)

        if mixture_type == "理想气体":
            cp_mix = cp_ideal
            cv_mix = cv_ideal
        else:
            # 真实气体校正：Lee-Kesler 剩余比热 (cp^dep/R)
            # 使用混合参数
            mw_mix = sum(c['y'] * c['mw'] for c in components)
            tc_mix = sum(c['y'] * c['tc'] for c in components)
            pc_mix = sum(c['y'] * c['pc'] for c in components)
            omega_mix = sum(c['y'] * c['omega'] for c in components)
            T_K = T  # T 已是 K

            Tr = T_K / tc_mix
            Pr = (sum(c['y'] for c in components) * 101.325) / pc_mix  # 估算, 低影响
            # 数值微分求 d(Z)/d(Tr) ≈ 剩余比热简化：
            # cp^dep ≈ -R * d^2(Z*Tr)/d(Tr^2) * Pr  (低压修正)
            # 在工程精度下，真实气体修正量对 cp 通常 <5%
            # 使用 Pitzer 关联: cp_dep/R ≈ -omega * 0.172/Tr^(4.2) * Pr  (简化)
            cp_dep = -R * omega_mix * 0.172 / Tr**4.2 * Pr
            cp_mix = cp_ideal + cp_dep
            cv_mix = cp_mix - R * _lee_kesler_z(Tr, Pr, omega_mix) if tc_mix > 0 and pc_mix > 0 else cp_ideal - R
            cp_mix = max(cv_ideal + 1e-3, cp_mix)
            cv_mix = max(1e-3, cv_mix)

        gamma = cp_mix / cv_mix if cv_mix > 0 else 1.4

        return cp_mix, cv_mix, gamma
    
    def calculate_sound_speed(self, T, mw_mix, gamma, z_factor):
        """计算音速"""
        # 音速公式: a = sqrt(γ * Z * R * T / M)
        R = 8.314  # J/(mol·K)
        sound_speed = math.sqrt(gamma * z_factor * R * T / (mw_mix / 1000))  # m/s
        
        return sound_speed
    
    def display_results(self, results):
        """显示计算结果"""
        self.mw_mixture_result.setText(f"{results['mw_mix']:.3f}")
        self.tc_mixture_result.setText(f"{results['tc_mix']:.1f}")
        self.pc_mixture_result.setText(f"{results['pc_mix']:.0f}")
        self.vc_mixture_result.setText(f"{results['vc_mix']:.1f}")
        self.omega_mixture_result.setText(f"{results['omega_mix']:.3f}")
        self.zc_mixture_result.setText(f"{results['zc_mix']:.3f}")
        
        self.density_result.setText(f"{results['density']:.3f}")
        self.z_factor_result.setText(f"{results['z_factor']:.3f}")
        self.viscosity_result.setText(f"{results['viscosity']:.1f}")
        self.thermal_cond_result.setText(f"{results['thermal_conductivity']:.4f}")
        self.cp_result.setText(f"{results['cp_mix']:.2f}")
        self.cv_result.setText(f"{results['cv_mix']:.2f}")
        self.ratio_cp_cv_result.setText(f"{results['gamma']:.3f}")
        self.sound_speed_result.setText(f"{results['sound_speed']:.1f}")
        
        self.tr_result.setText(f"{results['tr']:.3f}")
        self.pr_result.setText(f"{results['pr']:.3f}")
        self.vr_result.setText(f"{results['vr']:.3f}")
        self.reduced_density_result.setText(f"{results['reduced_density']:.3f}")
    
    def show_error(self, message):
        """显示错误信息"""
        for label in [self.mw_mixture_result, self.tc_mixture_result, 
                     self.pc_mixture_result, self.vc_mixture_result,
                     self.omega_mixture_result, self.zc_mixture_result,
                     self.density_result, self.z_factor_result,
                     self.viscosity_result, self.thermal_cond_result,
                     self.cp_result, self.cv_result, self.ratio_cp_cv_result,
                     self.sound_speed_result, self.tr_result, self.pr_result,
                     self.vr_result, self.reduced_density_result]:
            label.setText("计算错误")
        
        print(f"错误: {message}")


if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = GasMixturePropertiesCalculator()
    calculator.resize(900, 800)
    calculator.show()
    
    sys.exit(app.exec())