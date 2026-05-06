from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QLabel, QLineEdit, QPushButton, QComboBox,
                              QFormLayout, QTextEdit, QGridLayout, QScrollArea,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QTabWidget, QCheckBox, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math

# ---------------------------------------------------------------------------
#  物质数据库（Antoine + UNIQUAC r/q + 分子量）
#  Antoine 系数来源：NIST Chemistry WebBook / Perry's
#  UNIQUAC r, q: Dortmund Data Bank / DECHEMA
# ---------------------------------------------------------------------------

SUBSTANCE_DB = {
    "甲醇":   {"antoine": [7.89750, 1474.08, 229.13], "mw": 32.04, "r": 1.4311, "q": 1.4320},
    "乙醇":   {"antoine": [8.20417, 1642.89, 230.30], "mw": 46.07, "r": 2.1055, "q": 1.9720},
    "水":     {"antoine": [8.07131, 1730.63, 233.43], "mw": 18.02, "r": 0.9200, "q": 1.4000},
    "苯":     {"antoine": [6.90565, 1211.03, 220.79], "mw": 78.11, "r": 3.1878, "q": 2.4000},
    "甲苯":   {"antoine": [6.95464, 1344.80, 219.48], "mw": 92.14, "r": 3.9228, "q": 2.9680},
    "丙酮":   {"antoine": [7.02447, 1161.00, 224.00], "mw": 58.08, "r": 2.5735, "q": 2.3360},
    "乙酸":   {"antoine": [7.18807, 1416.70, 211.00], "mw": 60.05, "r": 2.2024, "q": 2.0720},
    "正己烷": {"antoine": [6.87776, 1171.53, 224.37], "mw": 86.18, "r": 4.4998, "q": 3.8560},
    "正庚烷": {"antoine": [6.89386, 1264.90, 216.64], "mw": 100.20, "r": 5.1742, "q": 4.3960},
    "环己烷": {"antoine": [6.84130, 1201.53, 222.65], "mw": 84.16, "r": 4.0464, "q": 3.2400},
    "异丙醇": {"antoine": [8.11778, 1580.92, 219.61], "mw": 60.10, "r": 2.7799, "q": 2.5080},
    "乙酸乙酯": {"antoine": [7.10179, 1244.95, 217.88], "mw": 88.11, "r": 3.4786, "q": 3.1160},
    "氯仿":   {"antoine": [6.95465, 1170.97, 226.23], "mw": 119.38, "r": 2.8700, "q": 2.4100},
    "二氯甲烷": {"antoine": [7.08030, 1138.91, 231.45], "mw": 84.93, "r": 2.8980, "q": 2.3220},
    "1-丙醇": {"antoine": [8.37895, 1788.02, 227.44], "mw": 60.10, "r": 2.7799, "q": 2.5080},
    "2-丁醇": {"antoine": [7.36366, 1305.20, 173.40], "mw": 74.12, "r": 3.3520, "q": 2.8880},
}

# 预设二元交互参数数据库
# 格式: (组分i, 组分j): {model: {params}}
# Wilson: Δλ12 (J/mol), Δλ21 (J/mol)
# NRTL: Δg12 (J/mol), Δg21 (J/mol), α12
# UNIQUAC: Δu12 (J/mol), Δu21 (J/mol)
BINARY_PARAMS_DB = {
    ("甲醇", "水"): {
        "Wilson":  {"lambda12": 122.6, "lambda21": 658.3},
        "NRTL":    {"g12": -253.88, "g21": 2223.2, "alpha": 0.2988},
        "UNIQUAC": {"u12": -255.6, "u21": 1287.0},
    },
    ("乙醇", "水"): {
        "Wilson":  {"lambda12": 181.0, "lambda21": 511.5},
        "NRTL":    {"g12": -118.3, "g21": 1636.6, "alpha": 0.2974},
        "UNIQUAC": {"u12": 66.57, "u21": 1704.5},
    },
    ("丙酮", "水"): {
        "Wilson":  {"lambda12": 221.3, "lambda21": 1319.2},
        "NRTL":    {"g12": 335.4, "g21": 1337.4, "alpha": 0.3083},
        "UNIQUAC": {"u12": 695.0, "u21": 924.9},
    },
    ("苯", "甲苯"): {
        "Wilson":  {"lambda12": 240.1, "lambda21": 197.1},
        "NRTL":    {"g12": 292.0, "g21": -269.2, "alpha": 0.3},
        "UNIQUAC": {"u12": 144.6, "u21": -55.7},
    },
    ("乙醇", "苯"): {
        "Wilson":  {"lambda12": 1415.7, "lambda21": 231.8},
        "NRTL":    {"g12": 1510.7, "g21": 262.6, "alpha": 0.3008},
        "UNIQUAC": {"u12": 1246.6, "u21": 166.5},
    },
    ("甲醇", "丙酮"): {
        "Wilson":  {"lambda12": 561.8, "lambda21": 458.7},
        "NRTL":    {"g12": 212.1, "g21": 366.7, "alpha": 0.3084},
        "UNIQUAC": {"u12": 67.87, "u21": -321.3},
    },
    ("乙酸", "水"): {
        "Wilson":  {"lambda12": 664.1, "lambda21": 653.8},
        "NRTL":    {"g12": 629.6, "g21": 1802.2, "alpha": 0.2977},
        "UNIQUAC": {"u12": 806.6, "u21": 1139.7},
    },
}


def _get_binary_params(comp_i, comp_j, model):
    """查找预设二元参数，正反均可匹配"""
    key1 = (comp_i, comp_j)
    key2 = (comp_j, comp_i)
    db_entry = BINARY_PARAMS_DB.get(key1) or BINARY_PARAMS_DB.get(key2)
    if db_entry and model in db_entry:
        p = db_entry[model]
        if key1 in BINARY_PARAMS_DB:
            return p
        else:
            # 反向：交换12↔21
            swapped = {}
            for k, v in p.items():
                if k == "lambda12": swapped["lambda12"] = p.get("lambda21", 0)
                elif k == "lambda21": swapped["lambda21"] = p.get("lambda12", 0)
                elif k == "g12": swapped["g12"] = p.get("g21", 0)
                elif k == "g21": swapped["g21"] = p.get("g12", 0)
                elif k == "u12": swapped["u12"] = p.get("u21", 0)
                elif k == "u21": swapped["u21"] = p.get("u12", 0)
                else: swapped[k] = v
            return swapped
    return None


# ---------------------------------------------------------------------------
#  纯 Python Rachford-Rice 求解器
# ---------------------------------------------------------------------------

def solve_rachford_rice(z, K, tol=1e-10, max_iter=200):
    """求解 Rachford-Rice 方程 Σ zi(Ki-1)/(1+V(Ki-1)) = 0，返回气相分率 V ∈ [0,1]"""
    n = len(z)
    # 确定搜索区间
    # V=0 时函数值 f(0)=Σ zi(Ki-1)=ΣziKi-1
    # V=1 时函数值 f(1)=Σ zi(Ki-1)/Ki
    f0 = sum(z[i] * (K[i] - 1) for i in range(n))
    f1 = sum(z[i] * (K[i] - 1) / K[i] for i in range(n))

    if abs(f0) < tol:
        return 0.0
    if abs(f1) < tol:
        return 1.0
    if f0 * f1 > 0:
        # 无根在 [0,1]，返回边界
        return 0.0 if abs(f0) < abs(f1) else 1.0

    # Newton 迭代
    V = 0.5
    for _ in range(max_iter):
        f = 0.0
        df = 0.0
        for i in range(n):
            denom = 1.0 + V * (K[i] - 1)
            if abs(denom) < 1e-30:
                denom = 1e-30
            term = z[i] * (K[i] - 1) / denom
            f += term
            df -= z[i] * (K[i] - 1) ** 2 / (denom * denom)
        if abs(df) < 1e-30:
            break
        dV = -f / df
        V_new = V + dV
        # 限制步长
        V_new = max(0.0, min(1.0, V_new))
        if abs(V_new - V) < tol:
            return V_new
        V = V_new
    return V


# ---------------------------------------------------------------------------
#  活度系数计算函数（纯 Python）
# ---------------------------------------------------------------------------

def wilson_ln_gamma(x, T, lambda_mat, n):
    """
    Wilson 方程，返回 ln γ 列表。
    lambda_mat: n×n 列表，Lambda[i][j] = exp(-(λij - λjj)/(R*T))
    """
    R = 8.314  # J/(mol·K)
    ln_gamma = [0.0] * n
    for i in range(n):
        sum_xj_Lij = sum(x[j] * lambda_mat[i][j] for j in range(n) if x[j] > 0)
        if sum_xj_Lij <= 0:
            ln_gamma[i] = 0.0
            continue
        sum_xk_Lki_over_sum = 0.0
        for k in range(n):
            if x[k] <= 0:
                continue
            sum_xj_Lkj = sum(x[j] * lambda_mat[k][j] for j in range(n) if x[j] > 0)
            if sum_xj_Lkj > 0:
                sum_xk_Lki_over_sum += x[k] * lambda_mat[k][i] / sum_xj_Lkj
        ln_gamma[i] = 1.0 - math.log(sum_xj_Lij) - sum_xk_Lki_over_sum
    return ln_gamma


def nrtl_ln_gamma(x, T, tau_mat, G_mat, alpha_mat, n):
    """
    NRTL 方程，返回 ln γ 列表。
    tau_mat[i][j] = Δgij/(R*T)
    G_mat[i][j] = exp(-αij * τij)
    """
    ln_gamma = [0.0] * n
    for i in range(n):
        sum_xj_Gji_tauji = 0.0
        sum_xj_Gji = 0.0
        sum_xj_Gij_over_denom = 0.0
        for j in range(n):
            if x[j] <= 0:
                continue
            denom_j = sum(x[k] * G_mat[k][j] for k in range(n) if x[k] > 0)
            if denom_j <= 0:
                continue
            sum_xk_Gkj_taukj = sum(x[k] * G_mat[k][j] * tau_mat[k][j]
                                    for k in range(n) if x[k] > 0)
            sum_xj_Gji += x[j] * G_mat[j][i]
            sum_xj_Gji_tauji += x[j] * G_mat[j][i] * tau_mat[j][i]
            sum_xj_Gij_over_denom += x[j] * G_mat[i][j] / denom_j * (tau_mat[i][j] - sum_xk_Gkj_taukj / denom_j)
        ln_gamma[i] = sum_xj_Gij_over_denom + sum_xj_Gji_tauji / sum_xj_Gji if sum_xj_Gji > 0 else 0.0
    return ln_gamma


def uniquac_ln_gamma(x, T, r_list, q_list, tau_mat, n):
    """
    UNIQUAC 方程，返回 ln γ 列表。
    ln γi = ln γi^C + ln γi^R
    组合项使用 r, q
    剩余项使用 τij = exp(-uij/(R*T))
    """
    R = 8.314
    # ---- 组合项 ----
    r_avg = sum(x[i] * r_list[i] for i in range(n))
    q_avg = sum(x[i] * q_list[i] for i in range(n))
    if r_avg <= 0 or q_avg <= 0:
        return [0.0] * n

    ln_gamma_C = [0.0] * n
    for i in range(n):
        if x[i] <= 0:
            continue
        phi_i = r_list[i] / r_avg
        theta_i = q_list[i] / q_avg
        l_i = 10.0 / 2.0 * (r_list[i] - q_list[i]) - (r_list[i] - 1.0)
        ln_gamma_C[i] = (math.log(phi_i / x[i]) + 5.0 / 2.0 * q_list[i] * math.log(theta_i / phi_i)
                         + l_i - phi_i / x[i] * sum(x[j] * l_j for j, l_j in enumerate(
                              [10.0 / 2.0 * (r_list[k] - q_list[k]) - (r_list[k] - 1.0) for k in range(n)])))

    # ---- 剩余项 ----
    ln_gamma_R = [0.0] * n
    for i in range(n):
        if x[i] <= 0:
            continue
        sum_xj_theta_j_tao_ji = 0.0
        for j in range(n):
            if x[j] <= 0:
                continue
            theta_j = q_list[j] / q_avg
            sum_xk_theta_k_tao_kj = sum(x[k] * q_list[k] / q_avg * tau_mat[k][j]
                                         for k in range(n) if x[k] > 0)
            if sum_xk_theta_k_tao_kj <= 0:
                continue
            sum_xj_theta_j_tao_ji += theta_j * tau_mat[j][i] / sum_xk_theta_k_tao_kj
        theta_i = q_list[i] / q_avg
        sum_xk_theta_k_tao_ki = sum(x[k] * q_list[k] / q_avg * tau_mat[k][i]
                                     for k in range(n) if x[k] > 0)
        ln_gamma_R[i] = (q_list[i] / 2.0 * (1.0 - math.log(sum_xk_theta_k_tao_ki)
                          - sum_xj_theta_j_tao_ji)) if sum_xk_theta_k_tao_ki > 0 else 0.0

    return [ln_gamma_C[i] + ln_gamma_R[i] for i in range(n)]


# ---------------------------------------------------------------------------
#  主界面
# ---------------------------------------------------------------------------

class VLEActivityCoefficientCalculator(QWidget):
    """气液平衡（活度系数法）计算器"""

    calculation_type = "vle_activity_coefficient_calculator"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.components = []
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        title_label = QLabel("气液平衡计算（活度系数法）")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        main_layout.addWidget(title_label)

        desc_label = QLabel("使用活度系数法计算多组分系统的气液平衡，支持 Wilson、NRTL、UNIQUAC 方程（纯 Python，无需 numpy/scipy）")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #7f8c8d; margin: 5px;")
        main_layout.addWidget(desc_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        self.tab_widget = QTabWidget()

        # ---- 系统设置标签页 ----
        system_tab = QWidget()
        system_layout = QVBoxLayout(system_tab)

        # 组分设置
        component_group = QGroupBox("组分设置")
        component_layout = QVBoxLayout(component_group)

        cc_layout = QHBoxLayout()
        cc_layout.addWidget(QLabel("组分数:"))
        self.component_count = QComboBox()
        self.component_count.addItems(["2", "3", "4"])
        self.component_count.currentTextChanged.connect(self.update_component_table)
        cc_layout.addWidget(self.component_count)
        cc_layout.addStretch()
        component_layout.addLayout(cc_layout)

        self.component_table = QTableWidget()
        self.component_table.setColumnCount(7)
        self.component_table.setHorizontalHeaderLabels([
            "组分", "Antoine A", "Antoine B", "Antoine C", "摩尔质量", "UNIQUAC r", "UNIQUAC q"
        ])
        component_layout.addWidget(self.component_table)
        system_layout.addWidget(component_group)

        # 计算条件
        condition_group = QGroupBox("计算条件")
        condition_layout = QGridLayout(condition_group)

        self.temperature_input = QLineEdit()
        self.temperature_input.setPlaceholderText("例如：78.3（°C）")
        self.temperature_input.setValidator(QDoubleValidator(-100, 500, 2))

        self.pressure_input = QLineEdit()
        self.pressure_input.setText("101.325")
        self.pressure_input.setValidator(QDoubleValidator(0.1, 10000, 2))

        self.model_selection = QComboBox()
        self.model_selection.addItems(["Wilson方程", "NRTL方程", "UNIQUAC方程"])

        self.calc_type = QComboBox()
        self.calc_type.addItems(["泡点计算", "露点计算", "等温闪蒸"])

        condition_layout.addWidget(QLabel("温度:"), 0, 0)
        condition_layout.addWidget(self.temperature_input, 0, 1)
        condition_layout.addWidget(QLabel("°C"), 0, 2)
        condition_layout.addWidget(QLabel("压力:"), 0, 3)
        condition_layout.addWidget(self.pressure_input, 0, 4)
        condition_layout.addWidget(QLabel("kPa"), 0, 5)
        condition_layout.addWidget(QLabel("热力学模型:"), 1, 0)
        condition_layout.addWidget(self.model_selection, 1, 1, 1, 2)
        condition_layout.addWidget(QLabel("计算类型:"), 1, 3)
        condition_layout.addWidget(self.calc_type, 1, 4, 1, 2)

        system_layout.addWidget(condition_group)

        # 二元交互参数
        binary_group = QGroupBox("二元交互参数")
        binary_layout = QVBoxLayout(binary_group)
        self.binary_table = QTableWidget()
        binary_layout.addWidget(self.binary_table)
        # 快速加载按钮
        btn_layout = QHBoxLayout()
        self.load_preset_btn = QPushButton("加载预设参数")
        self.load_preset_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; padding: 6px; border-radius: 4px; }"
                                          "QPushButton:hover { background-color: #219a52; }")
        self.load_preset_btn.clicked.connect(self.load_preset_binary_params)
        btn_layout.addWidget(self.load_preset_btn)
        btn_layout.addStretch()
        binary_layout.addLayout(btn_layout)
        system_layout.addWidget(binary_group)
        system_layout.addStretch()

        # ---- 液相组成标签页 ----
        comp_tab = QWidget()
        comp_tab_layout = QVBoxLayout(comp_tab)
        comp_tab_layout.addWidget(QLabel("液相摩尔分数（总和应为 1.0）:"))
        self.comp_input_table = QTableWidget()
        self.comp_input_table.setColumnCount(3)
        self.comp_input_table.setHorizontalHeaderLabels(["组分", "液相摩尔分数 xi", ""])
        comp_tab_layout.addWidget(self.comp_input_table)
        system_layout_tab2 = comp_tab
        # 这里改为在 comp_tab 中
        comp_tab_layout.addStretch()

        # ---- 结果标签页 ----
        result_tab = QWidget()
        result_layout = QVBoxLayout(result_tab)

        btn_row = QHBoxLayout()
        self.calc_btn = QPushButton("计算")
        self.calc_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; padding: 8px; border-radius: 4px; }"
                                  "QPushButton:hover { background-color: #2980b9; }")
        self.calc_btn.clicked.connect(self.calculate)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; padding: 8px; border-radius: 4px; }"
                                   "QPushButton:hover { background-color: #7f8c8d; }")
        self.clear_btn.clicked.connect(self.clear_inputs)
        btn_row.addWidget(self.calc_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        result_layout.addLayout(btn_row)

        result_display_group = QGroupBox("计算结果")
        result_display_layout = QVBoxLayout(result_display_group)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels([
            "组分", "液相摩尔分数", "气相摩尔分数", "活度系数 γ", "K 值"
        ])
        result_display_layout.addWidget(self.result_table)

        summary_layout = QFormLayout()
        self.bubble_point_result = QLabel("--")
        self.dew_point_result = QLabel("--")
        self.flash_temp_result = QLabel("--")
        self.vapor_fraction_result = QLabel("--")
        self.iter_count_result = QLabel("--")

        summary_layout.addRow("泡点温度 (°C):", self.bubble_point_result)
        summary_layout.addRow("露点温度 (°C):", self.dew_point_result)
        summary_layout.addRow("闪蒸温度 (°C):", self.flash_temp_result)
        summary_layout.addRow("气相分率 V:", self.vapor_fraction_result)
        summary_layout.addRow("迭代次数:", self.iter_count_result)

        result_display_layout.addLayout(summary_layout)
        result_layout.addWidget(result_display_group)

        # 标签页
        self.tab_widget.addTab(system_tab, "系统设置")
        self.tab_widget.addTab(comp_tab, "液相组成")
        self.tab_widget.addTab(result_tab, "计算结果")

        scroll_layout.addWidget(self.tab_widget)

        info_text = QTextEdit()
        info_text.setMaximumHeight(150)
        info_text.setHtml("""
        <h4>计算说明:</h4>
        <ul>
        <li><b>Antoine方程</b>: log₁₀(P_sat) = A - B/(T+C)，P 单位 kPa，T 单位 °C</li>
        <li><b>Wilson方程</b>: 适用于极性/非极性混合物，不含部分互溶系统</li>
        <li><b>NRTL方程</b>: 适用于非理想体系，包括部分互溶系统；需输入 α₁₂ (非随机性参数)</li>
        <li><b>UNIQUAC方程</b>: 基于分子结构（r,q）和相互作用能的通用模型</li>
        <li><b>泡点计算</b>: 给定液相组成和压力，迭代求泡点温度和气相组成</li>
        <li><b>露点计算</b>: 给定气相组成和压力，迭代求露点温度和液相组成</li>
        <li><b>等温闪蒸</b>: 给定总组成、温度和压力，Rachford-Rice 方程求气相分率</li>
        <li>预设 7 组常见二元交互参数（甲醇-水、乙醇-水等），点击「加载预设参数」自动填充</li>
        </ul>
        """)
        info_text.setReadOnly(True)
        scroll_layout.addWidget(info_text)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        self.update_component_table()

    # ------------------------------------------------------------------
    #  组分表管理
    # ------------------------------------------------------------------

    def update_component_table(self):
        count = int(self.component_count.currentText())
        self.component_table.setRowCount(count)

        for i in range(count):
            name_combo = QComboBox()
            name_combo.addItems(["自定义"] + list(SUBSTANCE_DB.keys()))
            name_combo.setCurrentIndex((i % len(SUBSTANCE_DB)) + 1)
            name_combo.currentTextChanged.connect(lambda text, row=i: self._on_component_changed(row))
            self.component_table.setCellWidget(i, 0, name_combo)

            current = name_combo.currentText()
            params = SUBSTANCE_DB.get(current, {})
            ant = params.get("antoine", [0, 0, 0])

            self.component_table.setItem(i, 1, QTableWidgetItem(f"{ant[0]:.5f}"))
            self.component_table.setItem(i, 2, QTableWidgetItem(f"{ant[1]:.2f}"))
            self.component_table.setItem(i, 3, QTableWidgetItem(f"{ant[2]:.2f}"))
            self.component_table.setItem(i, 4, QTableWidgetItem(f"{params.get('mw', 0):.2f}"))
            self.component_table.setItem(i, 5, QTableWidgetItem(f"{params.get('r', 0):.4f}"))
            self.component_table.setItem(i, 6, QTableWidgetItem(f"{params.get('q', 0):.4f}"))

        self.update_binary_table()
        self.update_comp_input_table()

    def _on_component_changed(self, row):
        combo = self.component_table.cellWidget(row, 0)
        if not combo:
            return
        name = combo.currentText()
        params = SUBSTANCE_DB.get(name, {})
        ant = params.get("antoine", [0, 0, 0])
        self.component_table.item(row, 1).setText(f"{ant[0]:.5f}")
        self.component_table.item(row, 2).setText(f"{ant[1]:.2f}")
        self.component_table.item(row, 3).setText(f"{ant[2]:.2f}")
        self.component_table.item(row, 4).setText(f"{params.get('mw', 0):.2f}")
        self.component_table.item(row, 5).setText(f"{params.get('r', 0):.4f}")
        self.component_table.item(row, 6).setText(f"{params.get('q', 0):.4f}")
        self.update_binary_table()

    def update_comp_input_table(self):
        count = int(self.component_count.currentText())
        self.comp_input_table.setRowCount(count)
        for i in range(count):
            combo = self.component_table.cellWidget(i, 0)
            name = combo.currentText() if combo else f"组分{i+1}"
            name_label = QTableWidgetItem(name)
            name_label.setFlags(name_label.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.comp_input_table.setItem(i, 0, name_label)
            if i == 0:
                xi = QTableWidgetItem("0.5")
            elif i == 1:
                xi = QTableWidgetItem("0.5")
            else:
                xi = QTableWidgetItem("0.0")
            self.comp_input_table.setItem(i, 1, xi)
            pct = QTableWidgetItem("50.0%")
            pct.setFlags(pct.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.comp_input_table.setItem(i, 2, pct)

    def update_binary_table(self):
        count = int(self.component_count.currentText())
        n_pairs = count * (count - 1) // 2
        self.binary_table.setRowCount(n_pairs)
        model = self.model_selection.currentText()

        if model == "Wilson方程":
            headers = ["组分对", "Δλ₁₂ (J/mol)", "Δλ₂₁ (J/mol)", ""]
        elif model == "NRTL方程":
            headers = ["组分对", "Δg₁₂ (J/mol)", "Δg₂₁ (J/mol)", "α₁₂"]
        else:  # UNIQUAC
            headers = ["组分对", "Δu₁₂ (J/mol)", "Δu₂₁ (J/mol)", ""]
        self.binary_table.setColumnCount(len(headers))
        self.binary_table.setHorizontalHeaderLabels(headers)

        row = 0
        for i in range(count):
            for j in range(i + 1, count):
                ci = self.component_table.cellWidget(i, 0)
                cj = self.component_table.cellWidget(j, 0)
                ni = ci.currentText() if ci else f"组分{i+1}"
                nj = cj.currentText() if cj else f"组分{j+1}"
                self.binary_table.setItem(row, 0, QTableWidgetItem(f"{ni} — {nj}"))

                # 尝试加载预设
                preset = _get_binary_params(ni, nj, model)
                if preset:
                    self.binary_table.setItem(row, 1, QTableWidgetItem(f"{preset.get('lambda12', preset.get('g12', preset.get('u12', 0))):.1f}"))
                    self.binary_table.setItem(row, 2, QTableWidgetItem(f"{preset.get('lambda21', preset.get('g21', preset.get('u21', 0))):.1f}"))
                    if model == "NRTL方程":
                        self.binary_table.setItem(row, 3, QTableWidgetItem(f"{preset.get('alpha', 0.3):.4f}"))
                else:
                    self.binary_table.setItem(row, 1, QTableWidgetItem("0.0"))
                    self.binary_table.setItem(row, 2, QTableWidgetItem("0.0"))
                    if model == "NRTL方程":
                        self.binary_table.setItem(row, 3, QTableWidgetItem("0.3"))
                row += 1

    def load_preset_binary_params(self):
        """重新加载预设参数（切换模型后用）"""
        self.update_binary_table()
        QMessageBox.information(self, "已更新", "二元交互参数已根据当前模型和组分自动加载预设值（如有）。")

    # ------------------------------------------------------------------
    #  获取输入数据
    # ------------------------------------------------------------------

    def get_component_data(self):
        count = int(self.component_count.currentText())
        components = []
        for i in range(count):
            combo = self.component_table.cellWidget(i, 0)
            name = combo.currentText() if combo else f"组分{i+1}"
            a = float(self.component_table.item(i, 1).text())
            b = float(self.component_table.item(i, 2).text())
            c = float(self.component_table.item(i, 3).text())
            mw = float(self.component_table.item(i, 4).text())
            r = float(self.component_table.item(i, 5).text())
            q = float(self.component_table.item(i, 6).text())
            components.append({
                'name': name, 'antoine_a': a, 'antoine_b': b, 'antoine_c': c,
                'mw': mw, 'r': r, 'q': q
            })
        return components

    def get_compositions(self):
        count = int(self.component_count.currentText())
        x = []
        for i in range(count):
            val = float(self.comp_input_table.item(i, 1).text())
            x.append(val)
        # 归一化
        total = sum(x)
        if total > 0 and abs(total - 1.0) > 1e-6:
            x = [v / total for v in x]
        return x

    def get_binary_params(self, components):
        """获取二元交互参数，返回 (i,j) -> dict"""
        count = len(components)
        model = self.model_selection.currentText()
        params = {}
        row = 0
        for i in range(count):
            for j in range(i + 1, count):
                val1 = float(self.binary_table.item(row, 1).text())
                val2 = float(self.binary_table.item(row, 2).text())
                entry = {}
                if model == "Wilson方程":
                    entry = {"lambda12": val1, "lambda21": val2}
                elif model == "NRTL方程":
                    alpha = float(self.binary_table.item(row, 3).text())
                    entry = {"g12": val1, "g21": val2, "alpha": alpha}
                else:
                    entry = {"u12": val1, "u21": val2}
                params[(i, j)] = entry
                row += 1
        return params

    def _build_matrices(self, components, binary_params, T_K, model, n):
        """根据模型构建交互矩阵"""
        R = 8.314
        if model == "Wilson方程":
            Lambda = [[1.0] * n for _ in range(n)]
            for (i, j), p in binary_params.items():
                if i < n and j < n:
                    Lambda[i][j] = math.exp(-p["lambda12"] / (R * T_K))
                    Lambda[j][i] = math.exp(-p["lambda21"] / (R * T_K))
            return {"Lambda": Lambda}

        elif model == "NRTL方程":
            tau = [[0.0] * n for _ in range(n)]
            G = [[1.0] * n for _ in range(n)]
            alpha_m = [[0.3] * n for _ in range(n)]
            for (i, j), p in binary_params.items():
                if i < n and j < n:
                    a_ij = p.get("alpha", 0.3)
                    tau[i][j] = p["g12"] / (R * T_K)
                    tau[j][i] = p["g21"] / (R * T_K)
                    G[i][j] = math.exp(-a_ij * tau[i][j])
                    G[j][i] = math.exp(-a_ij * tau[j][i])
                    alpha_m[i][j] = a_ij
                    alpha_m[j][i] = a_ij
            return {"tau": tau, "G": G, "alpha": alpha_m}

        else:  # UNIQUAC
            tau = [[1.0] * n for _ in range(n)]
            for (i, j), p in binary_params.items():
                if i < n and j < n:
                    tau[i][j] = math.exp(-p["u12"] / (R * T_K))
                    tau[j][i] = math.exp(-p["u21"] / (R * T_K))
            return {"tau": tau}

    # ------------------------------------------------------------------
    #  计算
    # ------------------------------------------------------------------

    def calculate_activity_coefficients(self, x, T_K, matrices, model, n):
        """返回 γ 列表"""
        if model == "Wilson方程":
            ln_g = wilson_ln_gamma(x, T_K, matrices["Lambda"], n)
        elif model == "NRTL方程":
            ln_g = nrtl_ln_gamma(x, T_K, matrices["tau"], matrices["G"], matrices["alpha"], n)
        else:
            r_list = [self._current_components[i]['r'] for i in range(n)]
            q_list = [self._current_components[i]['q'] for i in range(n)]
            ln_g = uniquac_ln_gamma(x, T_K, r_list, q_list, matrices["tau"], n)
        return [math.exp(gi) for gi in ln_g]

    @staticmethod
    def _psat(comp, T_C):
        """Antoine 饱和蒸气压 (kPa)"""
        logP = comp['antoine_a'] - comp['antoine_b'] / (T_C + comp['antoine_c'])
        return 10.0 ** logP

    def calculate(self):
        try:
            T_C = float(self.temperature_input.text()) if self.temperature_input.text() else 25.0
            P = float(self.pressure_input.text())
            model = self.model_selection.currentText()
            calc_type = self.calc_type.currentText()

            self._current_components = components = self.get_component_data()
            n = len(components)
            x = self.get_compositions()
            binary_params = self.get_binary_params(components)

            T_K = T_C + 273.15

            if calc_type == "泡点计算":
                T_bub, y, gamma, Psat, iters = self._bubble_point_T(x, P, components, binary_params, model, n, T_C)
                self.bubble_point_result.setText(f"{T_bub:.2f}")
                self.dew_point_result.setText("--")
                self.flash_temp_result.setText("--")
                self.vapor_fraction_result.setText("0.0000（泡点）")
                self.iter_count_result.setText(str(iters))

                K = [gamma[i] * Psat[i] / P for i in range(n)]
                self._show_results(components, x, y, gamma, K)

            elif calc_type == "露点计算":
                y = x.copy()  # 输入为气相组成
                T_dew, x_calc, gamma, Psat, iters = self._dew_point_T(y, P, components, binary_params, model, n, T_C)
                self.dew_point_result.setText(f"{T_dew:.2f}")
                self.bubble_point_result.setText("--")
                self.flash_temp_result.setText("--")
                self.vapor_fraction_result.setText("1.0000（露点）")
                self.iter_count_result.setText(str(iters))

                K = [gamma[i] * Psat[i] / P for i in range(n)]
                self._show_results(components, x_calc, y, gamma, K)

            else:  # 等温闪蒸
                z = x.copy()
                matrices = self._build_matrices(components, binary_params, T_K, model, n)
                gamma = self.calculate_activity_coefficients(z, T_K, matrices, model, n)
                Psat = [self._psat(components[i], T_C) for i in range(n)]
                K = [gamma[i] * Psat[i] / P for i in range(n)]
                V = solve_rachford_rice(z, K)
                x_flash = [z[i] / (1 + V * (K[i] - 1)) for i in range(n)]
                y_flash = [K[i] * x_flash[i] for i in range(n)]

                self.bubble_point_result.setText("--")
                self.dew_point_result.setText("--")
                self.flash_temp_result.setText(f"{T_C:.2f}")
                self.vapor_fraction_result.setText(f"{V:.4f}")
                self.iter_count_result.setText("—（Rachford-Rice）")
                self._show_results(components, x_flash, y_flash, gamma, K)

        except ValueError:
            self.show_error("输入参数格式错误，请检查输入值")
        except Exception as e:
            self.show_error(f"计算错误: {str(e)}")

    def _bubble_point_T(self, x, P, components, bp, model, n, T_init_C, tol=1e-4, max_iter=200):
        """Newton-Raphson 泡点温度迭代"""
        T_C = T_init_C
        for iteration in range(max_iter):
            T_K = T_C + 273.15
            matrices = self._build_matrices(components, bp, T_K, model, n)
            gamma = self.calculate_activity_coefficients(x, T_K, matrices, model, n)
            Psat = [self._psat(components[i], T_C) for i in range(n)]
            K = [gamma[i] * Psat[i] / P for i in range(n)]
            f = sum(K[i] * x[i] for i in range(n)) - 1.0
            if abs(f) < tol:
                y = [K[i] * x[i] for i in range(n)]
                return T_C, y, gamma, Psat, iteration + 1
            # df/dT
            dT = 0.01
            T_C2 = T_C + dT
            T_K2 = T_C2 + 273.15
            matrices2 = self._build_matrices(components, bp, T_K2, model, n)
            gamma2 = self.calculate_activity_coefficients(x, T_K2, matrices2, model, n)
            Psat2 = [self._psat(components[i], T_C2) for i in range(n)]
            K2 = [gamma2[i] * Psat2[i] / P for i in range(n)]
            f2 = sum(K2[i] * x[i] for i in range(n)) - 1.0
            df = (f2 - f) / dT
            if abs(df) < 1e-12:
                T_C += 0.5
            else:
                T_C -= f / df
            # 限制范围
            T_C = max(-50, min(500, T_C))
        y = [K[i] * x[i] for i in range(n)]
        return T_C, y, gamma, Psat, max_iter

    def _dew_point_T(self, y, P, components, bp, model, n, T_init_C, tol=1e-4, max_iter=200):
        """Newton-Raphson 露点温度迭代"""
        T_C = T_init_C
        for iteration in range(max_iter):
            T_K = T_C + 273.15
            # 需点需要先估算液相组成来算活度系数
            x_est = [0.0] * n
            Psat = [self._psat(components[i], T_C) for i in range(n)]
            # 初始估算 x_i = y_i * P / Psat_i
            denom = sum(y[i] * P / Psat[i] if Psat[i] > 0 else 0 for i in range(n))
            x_est = [y[i] * P / Psat[i] / denom if Psat[i] > 0 and denom > 0 else 1.0/n for i in range(n)]
            matrices = self._build_matrices(components, bp, T_K, model, n)
            gamma = self.calculate_activity_coefficients(x_est, T_K, matrices, model, n)
            K = [gamma[i] * Psat[i] / P for i in range(n)]
            f = sum(y[i] / K[i] for i in range(n)) - 1.0
            if abs(f) < tol:
                x_calc = [y[i] / K[i] for i in range(n)]
                return T_C, x_calc, gamma, Psat, iteration + 1
            dT = 0.01
            T_C2 = T_C + dT
            T_K2 = T_C2 + 273.15
            Psat2 = [self._psat(components[i], T_C2) for i in range(n)]
            denom2 = sum(y[i] * P / Psat2[i] if Psat2[i] > 0 else 0 for i in range(n))
            x_est2 = [y[i] * P / Psat2[i] / denom2 if Psat2[i] > 0 and denom2 > 0 else 1.0/n for i in range(n)]
            matrices2 = self._build_matrices(components, bp, T_K2, model, n)
            gamma2 = self.calculate_activity_coefficients(x_est2, T_K2, matrices2, model, n)
            K2 = [gamma2[i] * Psat2[i] / P for i in range(n)]
            f2 = sum(y[i] / K2[i] for i in range(n)) - 1.0
            df = (f2 - f) / dT
            if abs(df) < 1e-12:
                T_C -= 0.5
            else:
                T_C -= f / df
            T_C = max(-50, min(500, T_C))
        x_calc = [y[i] / K[i] for i in range(n)]
        return T_C, x_calc, gamma, Psat, max_iter

    # ------------------------------------------------------------------
    #  结果显示
    # ------------------------------------------------------------------

    def _show_results(self, components, x, y, gamma, K):
        n = len(components)
        self.result_table.setRowCount(n)
        for i in range(n):
            self.result_table.setItem(i, 0, QTableWidgetItem(components[i]['name']))
            self.result_table.setItem(i, 1, QTableWidgetItem(f"{x[i]:.6f}"))
            self.result_table.setItem(i, 2, QTableWidgetItem(f"{y[i]:.6f}"))
            self.result_table.setItem(i, 3, QTableWidgetItem(f"{gamma[i]:.6f}"))
            self.result_table.setItem(i, 4, QTableWidgetItem(f"{K[i]:.6f}"))

    # ------------------------------------------------------------------
    #  清空 / 错误
    # ------------------------------------------------------------------

    def clear_inputs(self):
        self.temperature_input.clear()
        self.pressure_input.setText("101.325")
        self.update_component_table()
        self.result_table.setRowCount(0)
        self.bubble_point_result.setText("--")
        self.dew_point_result.setText("--")
        self.flash_temp_result.setText("--")
        self.vapor_fraction_result.setText("--")
        self.iter_count_result.setText("--")

    def show_error(self, message):
        self.result_table.setRowCount(0)
        self.bubble_point_result.setText("计算错误")
        self.dew_point_result.setText("计算错误")
        self.flash_temp_result.setText("计算错误")
        self.vapor_fraction_result.setText("计算错误")
        self.iter_count_result.setText("--")
        QMessageBox.critical(self, "计算错误", message)

    def _get_history_data(self):
        temperature = float(self.temperature_input.text()) if self.temperature_input.text() else 25.0
        pressure = float(self.pressure_input.text()) if self.pressure_input.text() else 0
        model = self.model_selection.currentText()
        calc_type = self.calc_type.currentText()
        inputs = {
            "温度_C": temperature,
            "压力_kPa": pressure,
            "热力学模型": model,
            "计算类型": calc_type
        }
        outputs = {}
        try:
            components = self.get_component_data()
            inputs["组分数量"] = len(components)
            for i, comp in enumerate(components):
                inputs[f"组分{i+1}"] = comp.get("name", "")
            bub_text = self.bubble_point_result.text()
            dew_text = self.dew_point_result.text()
            vf_text = self.vapor_fraction_result.text()
            if bub_text and bub_text not in ["--", "计算错误"]:
                outputs["泡点温度_C"] = float(bub_text)
            if dew_text and dew_text not in ["--", "计算错误"]:
                outputs["露点温度_C"] = float(dew_text)
            if vf_text and vf_text not in ["--", "计算错误"]:
                outputs["气相分率"] = vf_text
        except Exception as e:
            outputs["计算错误"] = str(e)
        return {"inputs": inputs, "outputs": outputs}


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    calculator = VLEActivityCoefficientCalculator()
    calculator.resize(950, 750)
    calculator.show()
    sys.exit(app.exec())
