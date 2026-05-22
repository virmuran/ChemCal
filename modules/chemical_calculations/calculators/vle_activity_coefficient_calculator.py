from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QLabel, QLineEdit, QPushButton, QComboBox,
                              QFormLayout, QTextEdit, QGridLayout, QScrollArea,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QTabWidget, QMessageBox, QSizePolicy)
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
    f0 = sum(z[i] * (K[i] - 1) for i in range(n))
    f1 = sum(z[i] * (K[i] - 1) / K[i] for i in range(n))

    if abs(f0) < tol:
        return 0.0
    if abs(f1) < tol:
        return 1.0
    if f0 * f1 > 0:
        return 0.0 if abs(f0) < abs(f1) else 1.0

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
        V_new = max(0.0, min(1.0, V_new))
        if abs(V_new - V) < tol:
            return V_new
        V = V_new
    return V


# ---------------------------------------------------------------------------
#  活度系数计算函数（纯 Python）
# ---------------------------------------------------------------------------

def wilson_ln_gamma(x, T, lambda_mat, n):
    """Wilson 方程，返回 ln γ 列表。"""
    R = 8.314
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
    """NRTL 方程，返回 ln γ 列表。"""
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
    """UNIQUAC 方程，返回 ln γ 列表。"""
    R = 8.314
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
#  QGroupBox 统一样式
# ---------------------------------------------------------------------------
GROUP_STYLE = """
    QGroupBox {
        font-weight: bold;
        border: 1px solid #888;
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 8px 0 8px;
    }
"""
COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #888;
        border-radius: 4px;
        padding: 6px 10px;
        /* background via theme */
        /* color via theme */
    }
    QComboBox QAbstractItemView {
        /* background-color via theme */
        /* color via theme */
        border: 1px solid #888;
        selection-background-color: #3498db;
        selection-color: black;
    }
    QComboBox QAbstractItemView::item {
        padding: 3px 8px;
    }
"""


class VLEActivityCoefficientCalculator(QWidget):
    """气液平衡（活度系数法）计算器 - 统一UI风格版"""

    calculation_type = "vle_activity_coefficient_calculator"

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)

        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()

        self.components = []
        self._current_components = []
        self._last_calc_results = {}
        self.setup_ui()

    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None

    def setup_ui(self):
        """设置UI界面 - 统一风格布局"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ====== 左侧：输入参数区域（带滚动） ======
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } "
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 1. 顶部说明文字
        description = QLabel(
            "使用活度系数法计算多组分系统的气液平衡，支持 Wilson、NRTL、UNIQUAC 方程（纯 Python，无需 numpy/scipy）。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: inherit; font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)

        # 2. 计算条件组
        condition_group = QGroupBox("计算条件")
        condition_group.setStyleSheet(GROUP_STYLE)
        condition_layout = QGridLayout(condition_group)
        condition_layout.setVerticalSpacing(12)
        condition_layout.setHorizontalSpacing(10)
        condition_layout.setColumnStretch(0, 4)
        condition_layout.setColumnStretch(1, 8)
        condition_layout.setColumnStretch(2, 5)

        label_style = "QLabel { font-weight: bold; padding-right: 10px; }"

        # 温度
        temp_label = QLabel("温度:")
        temp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        temp_label.setStyleSheet(label_style)
        condition_layout.addWidget(temp_label, 0, 0)

        self.temperature_input = QLineEdit()
        self.temperature_input.setPlaceholderText("例如：78.3")
        self.temperature_input.setValidator(QDoubleValidator(-100, 500, 2))
        self.temperature_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(self.temperature_input, 0, 1)

        temp_hint = QLabel("°C")
        temp_hint.setStyleSheet("color: #7f8c8d;")
        temp_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(temp_hint, 0, 2)

        # 压力
        pres_label = QLabel("压力:")
        pres_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pres_label.setStyleSheet(label_style)
        condition_layout.addWidget(pres_label, 1, 0)

        self.pressure_input = QLineEdit()
        self.pressure_input.setText("101.325")
        self.pressure_input.setPlaceholderText("例如：101.325")
        self.pressure_input.setValidator(QDoubleValidator(0.1, 10000, 2))
        self.pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(self.pressure_input, 1, 1)

        pres_hint = QLabel("kPa")
        pres_hint.setStyleSheet("color: #7f8c8d;")
        pres_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(pres_hint, 1, 2)

        # 热力学模型
        model_label = QLabel("热力学模型:")
        model_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        model_label.setStyleSheet(label_style)
        condition_layout.addWidget(model_label, 2, 0)

        self.model_selection = QComboBox()
        self.model_selection.setStyleSheet(COMBOBOX_STYLE)
        self.model_selection.addItems(["Wilson方程", "NRTL方程", "UNIQUAC方程"])
        self.model_selection.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.model_selection.currentTextChanged.connect(self._on_model_changed)
        condition_layout.addWidget(self.model_selection, 2, 1)

        model_hint = QLabel("选择活度系数模型")
        model_hint.setStyleSheet("color: inherit; font-style: italic;")
        model_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(model_hint, 2, 2)

        # 计算类型
        ctype_label = QLabel("计算类型:")
        ctype_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ctype_label.setStyleSheet(label_style)
        condition_layout.addWidget(ctype_label, 3, 0)

        self.calc_type = QComboBox()
        self.calc_type.setStyleSheet(COMBOBOX_STYLE)
        self.calc_type.addItems(["泡点计算", "露点计算", "等温闪蒸"])
        self.calc_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(self.calc_type, 3, 1)

        ctype_hint = QLabel("泡点/露点/闪蒸")
        ctype_hint.setStyleSheet("color: inherit; font-style: italic;")
        ctype_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(ctype_hint, 3, 2)

        # 组分数
        comp_label = QLabel("组分数:")
        comp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        comp_label.setStyleSheet(label_style)
        condition_layout.addWidget(comp_label, 4, 0)

        self.component_count = QComboBox()
        self.component_count.setStyleSheet(COMBOBOX_STYLE)
        self.component_count.addItems(["2", "3", "4"])
        self.component_count.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.component_count.currentTextChanged.connect(self.update_component_table)
        condition_layout.addWidget(self.component_count, 4, 1)

        comp_hint = QLabel("2~4组分体系")
        comp_hint.setStyleSheet("color: inherit; font-style: italic;")
        comp_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(comp_hint, 4, 2)

        left_layout.addWidget(condition_group)

        # 3. 标签页区域：组分设置 / 液相组成
        self.tab_widget = QTabWidget()

        # ---- Tab 1: 组分设置 ----
        system_tab = QWidget()
        system_tab_layout = QVBoxLayout(system_tab)

        # 组分参数表
        comp_group = QGroupBox("组分参数（Antoine + UNIQUAC）")
        comp_group.setStyleSheet(GROUP_STYLE)
        comp_table_layout = QVBoxLayout(comp_group)
        self.component_table = QTableWidget()
        self.component_table.setColumnCount(7)
        self.component_table.setHorizontalHeaderLabels([
            "组分", "Antoine A", "Antoine B", "Antoine C", "摩尔质量", "UNIQUAC r", "UNIQUAC q"
        ])
        self.component_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        comp_table_layout.addWidget(self.component_table)
        system_tab_layout.addWidget(comp_group)

        # 二元交互参数表
        binary_group = QGroupBox("二元交互参数")
        binary_group.setStyleSheet(GROUP_STYLE)
        binary_layout = QVBoxLayout(binary_group)
        self.binary_table = QTableWidget()
        self.binary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        binary_layout.addWidget(self.binary_table)

        btn_row = QHBoxLayout()
        self.load_preset_btn = QPushButton("加载预设参数")
        self.load_preset_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; border: none; border-radius: 4px; padding: 6px; font-weight: bold; }"
            "QPushButton:hover { background-color: #219653; }"
        )
        self.load_preset_btn.clicked.connect(self.load_preset_binary_params)
        btn_row.addWidget(self.load_preset_btn)
        btn_row.addStretch()
        binary_layout.addLayout(btn_row)
        system_tab_layout.addWidget(binary_group)

        self.tab_widget.addTab(system_tab, "组分设置")

        # ---- Tab 2: 液相组成 ----
        comp_tab = QWidget()
        comp_tab_layout = QVBoxLayout(comp_tab)
        comp_input_group = QGroupBox("液相摩尔分数（总和应为 1.0）")
        comp_input_group.setStyleSheet(GROUP_STYLE)
        comp_input_inner = QVBoxLayout(comp_input_group)
        self.comp_input_table = QTableWidget()
        self.comp_input_table.setColumnCount(3)
        self.comp_input_table.setHorizontalHeaderLabels(["组分", "液相摩尔分数 xi", "占比"])
        self.comp_input_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        comp_input_inner.addWidget(self.comp_input_table)
        comp_tab_layout.addWidget(comp_input_group)
        comp_tab_layout.addStretch()

        self.tab_widget.addTab(comp_tab, "液相组成")
        left_layout.addWidget(self.tab_widget)

        # 4. 计算按钮
        calculate_btn = QPushButton("查询")
        calculate_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calculate_btn.clicked.connect(self.calculate)
        calculate_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                min-height: 50px; padding: 0px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219955;
            }
        """)
        calculate_btn.setMinimumHeight(50)
        calculate_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        left_layout.addWidget(calculate_btn)

        # 5. 下载按钮行
        download_layout = QHBoxLayout()
        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet("""
            QPushButton { background-color: #95a5a6; color: white; border: none; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        clear_btn.clicked.connect(self.clear_inputs)
        download_layout.addWidget(clear_btn)

        download_layout.addStretch()

        download_txt_btn = QPushButton("下载计算书(TXT)")
        download_txt_btn.clicked.connect(self.download_txt_report)
        download_txt_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; border: none; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #219653; }
        """)

        download_pdf_btn = QPushButton("下载计算书(PDF)")
        download_pdf_btn.clicked.connect(self.generate_pdf_report)
        download_pdf_btn.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; border: none; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #c0392b; }
        """)

        download_layout.addWidget(download_txt_btn)
        download_layout.addWidget(download_pdf_btn)
        left_layout.addLayout(download_layout)

        # 底部拉伸
        left_layout.addStretch()

        # ====== 右侧：结果显示区域 ======
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        result_group = QGroupBox("计算结果")
        result_group.setStyleSheet(GROUP_STYLE)
        result_inner = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ecf0f1;
                border-radius: 6px;
                padding: 8px;
                /* bg via theme */min-height: 500px;
            }
        """)
        result_inner.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # 将左右添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

        # 初始化组分表
        self.update_component_table()

    # ------------------------------------------------------------------
    #  模型变更时更新二元参数表
    # ------------------------------------------------------------------
    def _on_model_changed(self):
        """模型切换后更新二元参数表"""
        self.update_binary_table()

    # ------------------------------------------------------------------
    #  组分表管理
    # ------------------------------------------------------------------

    def update_component_table(self):
        count = int(self.component_count.currentText())
        self.component_table.setRowCount(count)

        for i in range(count):
            name_combo = QComboBox()
            name_combo.setStyleSheet(COMBOBOX_STYLE)
            name_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        """重新加载预设参数"""
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
        """执行计算并显示结果"""
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

            # 保存计算结果用于报告
            self._last_calc_results = {
                "T_C": T_C, "P": P, "model": model, "calc_type": calc_type,
                "components": components, "n": n
            }

            if calc_type == "泡点计算":
                T_bub, y, gamma, Psat, iters = self._bubble_point_T(x, P, components, binary_params, model, n, T_C)
                K = [gamma[i] * Psat[i] / P for i in range(n)]
                self._last_calc_results.update({
                    "type": "bubble", "T_bub": T_bub, "y": y, "x": x,
                    "gamma": gamma, "Psat": Psat, "K": K, "iters": iters
                })
                self._format_bubble_result(components, x, y, gamma, K, T_bub, iters, model, P)

            elif calc_type == "露点计算":
                y_input = x.copy()  # 输入为气相组成
                T_dew, x_calc, gamma, Psat, iters = self._dew_point_T(y_input, P, components, binary_params, model, n, T_C)
                K = [gamma[i] * Psat[i] / P for i in range(n)]
                self._last_calc_results.update({
                    "type": "dew", "T_dew": T_dew, "y": y_input, "x": x_calc,
                    "gamma": gamma, "Psat": Psat, "K": K, "iters": iters
                })
                self._format_dew_result(components, x_calc, y_input, gamma, K, T_dew, iters, model, P)

            else:  # 等温闪蒸
                z = x.copy()
                matrices = self._build_matrices(components, binary_params, T_K, model, n)
                gamma = self.calculate_activity_coefficients(z, T_K, matrices, model, n)
                Psat = [self._psat(components[i], T_C) for i in range(n)]
                K = [gamma[i] * Psat[i] / P for i in range(n)]
                V = solve_rachford_rice(z, K)
                x_flash = [z[i] / (1 + V * (K[i] - 1)) for i in range(n)]
                y_flash = [K[i] * x_flash[i] for i in range(n)]
                self._last_calc_results.update({
                    "type": "flash", "T_C": T_C, "z": z, "x": x_flash, "y": y_flash,
                    "gamma": gamma, "Psat": Psat, "K": K, "V": V
                })
                self._format_flash_result(components, z, x_flash, y_flash, gamma, K, V, T_C, model, P)

        except ValueError:
            self.result_text.setPlainText("⚠ 输入参数格式错误，请检查输入值。")
        except Exception as e:
            self.result_text.setPlainText(f"⚠ 计算错误: {str(e)}")

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
            T_C = max(-50, min(500, T_C))
        y = [K[i] * x[i] for i in range(n)]
        return T_C, y, gamma, Psat, max_iter

    def _dew_point_T(self, y, P, components, bp, model, n, T_init_C, tol=1e-4, max_iter=200):
        """Newton-Raphson 露点温度迭代"""
        T_C = T_init_C
        for iteration in range(max_iter):
            T_K = T_C + 273.15
            x_est = [0.0] * n
            Psat = [self._psat(components[i], T_C) for i in range(n)]
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
    #  结果格式化（输出到右侧 QTextEdit）
    # ------------------------------------------------------------------

    def _format_bubble_result(self, components, x, y, gamma, K, T_bub, iters, model, P):
        n = len(components)
        lines = []
        lines.append("═══════════════════════════════════════")
        lines.append("        泡点计算结果")
        lines.append("═══════════════════════════════════════")
        lines.append(f"")
        lines.append(f"热力学模型: {model}")
        lines.append(f"系统压力:   {P:.2f} kPa")
        lines.append(f"泡点温度:   {T_bub:.4f} °C")
        lines.append(f"迭代次数:   {iters}")
        lines.append(f"")
        lines.append("─── 各组分结果 ───")
        lines.append(f"{'组分':<10} {'液相 xi':<12} {'气相 yi':<12} {'γi':<12} {'Ki':<12} {'Psat(kPa)':<12}")
        lines.append("─" * 68)
        for i in range(n):
            psat = self._psat(components[i], T_bub)
            lines.append(
                f"{components[i]['name']:<10} {x[i]:<12.6f} {y[i]:<12.6f} "
                f"{gamma[i]:<12.6f} {K[i]:<12.6f} {psat:<12.4f}"
            )
        lines.append("─" * 68)
        lines.append(f"{'合计':<10} {sum(x):<12.6f} {sum(y):<12.6f}")
        lines.append(f"")
        lines.append(f"说明: Antoine方程 log₁₀(Psat) = A - B/(T+C)")
        self.result_text.setPlainText("\n".join(lines))

    def _format_dew_result(self, components, x, y, gamma, K, T_dew, iters, model, P):
        n = len(components)
        lines = []
        lines.append("═══════════════════════════════════════")
        lines.append("        露点计算结果")
        lines.append("═══════════════════════════════════════")
        lines.append(f"")
        lines.append(f"热力学模型: {model}")
        lines.append(f"系统压力:   {P:.2f} kPa")
        lines.append(f"露点温度:   {T_dew:.4f} °C")
        lines.append(f"迭代次数:   {iters}")
        lines.append(f"")
        lines.append("─── 各组分结果 ───")
        lines.append(f"{'组分':<10} {'液相 xi':<12} {'气相 yi':<12} {'γi':<12} {'Ki':<12} {'Psat(kPa)':<12}")
        lines.append("─" * 68)
        for i in range(n):
            psat = self._psat(components[i], T_dew)
            lines.append(
                f"{components[i]['name']:<10} {x[i]:<12.6f} {y[i]:<12.6f} "
                f"{gamma[i]:<12.6f} {K[i]:<12.6f} {psat:<12.4f}"
            )
        lines.append("─" * 68)
        lines.append(f"{'合计':<10} {sum(x):<12.6f} {sum(y):<12.6f}")
        lines.append(f"")
        lines.append(f"说明: Antoine方程 log₁₀(Psat) = A - B/(T+C)")
        self.result_text.setPlainText("\n".join(lines))

    def _format_flash_result(self, components, z, x, y, gamma, K, V, T_C, model, P):
        n = len(components)
        lines = []
        lines.append("═══════════════════════════════════════")
        lines.append("        等温闪蒸计算结果")
        lines.append("═══════════════════════════════════════")
        lines.append(f"")
        lines.append(f"热力学模型: {model}")
        lines.append(f"系统压力:   {P:.2f} kPa")
        lines.append(f"闪蒸温度:   {T_C:.4f} °C")
        lines.append(f"气相分率 V: {V:.6f}")
        lines.append(f"")
        lines.append("─── 各组分结果 ───")
        lines.append(f"{'组分':<10} {'进料 zi':<12} {'液相 xi':<12} {'气相 yi':<12} {'γi':<12} {'Ki':<12}")
        lines.append("─" * 68)
        for i in range(n):
            lines.append(
                f"{components[i]['name']:<10} {z[i]:<12.6f} {x[i]:<12.6f} "
                f"{y[i]:<12.6f} {gamma[i]:<12.6f} {K[i]:<12.6f}"
            )
        lines.append("─" * 68)
        lines.append(f"{'合计':<10} {sum(z):<12.6f} {sum(x):<12.6f} {sum(y):<12.6f}")
        lines.append(f"")
        lines.append(f"说明: Rachford-Rice 方程求解气相分率")
        self.result_text.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------
    #  清空 / 错误
    # ------------------------------------------------------------------

    def clear_inputs(self):
        self.temperature_input.clear()
        self.pressure_input.setText("101.325")
        self.update_component_table()
        self.result_text.clear()
        self._last_calc_results = {}

    # ------------------------------------------------------------------
    #  历史数据 / 项目信息 / 报告
    # ------------------------------------------------------------------

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
            r = self._last_calc_results
            if r.get("type") == "bubble":
                outputs["泡点温度_C"] = r.get("T_bub", 0)
            elif r.get("type") == "dew":
                outputs["露点温度_C"] = r.get("T_dew", 0)
            elif r.get("type") == "flash":
                outputs["气相分率"] = r.get("V", 0)
        except Exception as e:
            outputs["计算错误"] = str(e)
        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        return {
            "project_name": "气液平衡计算（活度系数法）",
            "calculator_name": "VLE活度系数计算器",
            "version": "1.0",
            "description": "使用活度系数法（Wilson/NRTL/UNIQUAC）计算多组分系统气液平衡"
        }

    def generate_report(self):
        """生成文本报告内容"""
        r = self._last_calc_results
        if not r:
            return "尚未进行计算。"
        lines = []
        lines.append("气液平衡计算报告（活度系数法）")
        lines.append("=" * 50)
        lines.append(f"计算类型: {r.get('calc_type', '')}")
        lines.append(f"热力学模型: {r.get('model', '')}")
        lines.append(f"系统压力: {r.get('P', 0):.2f} kPa")
        lines.append(f"")
        lines.append(self.result_text.toPlainText())
        return "\n".join(lines)

    def download_txt_report(self):
        """下载TXT计算书"""
        try:
            from PySide6.QtWidgets import QFileDialog
            content = self.generate_report()
            if not content or content == "尚未进行计算。":
                QMessageBox.warning(self, "提示", "请先进行计算后再下载。")
                return
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存计算书", "VLE活度系数计算书.txt", "Text Files (*.txt)"
            )
            if file_path:
                from datetime import datetime
                header = f"CalcE - 气液平衡计算（活度系数法）\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}\n\n"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(header + content)
                QMessageBox.information(self, "成功", f"计算书已保存至:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def generate_pdf_report(self):
        """下载PDF计算书"""
        try:
            from PySide6.QtWidgets import QFileDialog
            content = self.generate_report()
            if not content or content == "尚未进行计算。":
                QMessageBox.warning(self, "提示", "请先进行计算后再下载。")
                return
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存PDF计算书", "VLE活度系数计算书.pdf", "PDF Files (*.pdf)"
            )
            if file_path:
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                # 尝试使用中文字体
                try:
                    font_path = "C:/Windows/Fonts/msyh.ttc"
                    pdf.add_font("msyh", "", font_path, uni=True)
                    pdf.set_font("msyh", size=10)
                except Exception:
                    pdf.set_font("Helvetica", size=10)

                for line in content.split("\n"):
                    pdf.cell(0, 6, line, ln=True)
                pdf.output(file_path)
                QMessageBox.information(self, "成功", f"PDF计算书已保存至:\n{file_path}")
        except ImportError:
            QMessageBox.critical(self, "错误", "需要安装 fpdf 库: pip install fpdf")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"PDF生成失败: {str(e)}")


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    calculator = VLEActivityCoefficientCalculator()
    calculator.resize(1200, 800)
    calculator.show()
    sys.exit(app.exec())
