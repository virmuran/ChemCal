import math, os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QButtonGroup,
    QRadioButton,
    QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator


COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 6px 10px;
        background: white;
        color: black;
    }
    QComboBox QAbstractItemView {
        background-color: white;
        color: black;
        border: 1px solid #bdc3c7;
        selection-background-color: #3498db;
        selection-color: black;
    }
    QComboBox QAbstractItemView::item {
        padding: 3px 8px;
    }
"""
class CompressibleFlowPressureDrop(QWidget):
    """可压缩流体压降计算器（统一 UI 规范版）"""
    calculation_type = "compressible_flow_pressure_drop"

    FLUID_DB = {
        "air":      {"mw": 28.97, "gamma": 1.40, "R": 287.1,  "mu": 18.27},
        "nitrogen": {"mw": 28.01, "gamma": 1.40, "R": 296.8,  "mu": 17.90},
        "oxygen":   {"mw": 32.00, "gamma": 1.40, "R": 259.8,  "mu": 20.80},
        "hydrogen": {"mw": 2.016, "gamma": 1.41, "R": 4124.0, "mu": 8.90},
        "co2":      {"mw": 44.01, "gamma": 1.30, "R": 188.9,  "mu": 14.80},
        "ng":       {"mw": 19.00, "gamma": 1.30, "R": 440.0,  "mu": 11.20},
        "steam":   {"mw": 18.02, "gamma": 1.33, "R": 461.5,  "mu": 12.30},
        "methane":  {"mw": 16.04, "gamma": 1.32, "R": 518.3,  "mu": 11.20},
        "ethane":   {"mw": 30.07, "gamma": 1.20, "R": 276.5,  "mu": 9.50},
        "propane": {"mw": 44.10, "gamma": 1.13, "R": 188.5,  "mu": 8.10},
    }

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager if data_manager is not None else None
        self._last_result = {}
        self._last_params = {}
        self.setup_ui()

    def setup_ui(self):
        group_style = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bdc3c7;
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
        main = QHBoxLayout(self)
        main.setSpacing(15)
        main.setContentsMargins(10, 10, 10, 10)

        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left = QWidget()
        left.setStyleSheet("QWidget { background: transparent; }")
        ll = QVBoxLayout(left)
        ll.setSpacing(15)

        desc = QLabel(
            "计算可压缩流体（气体/蒸汽）管道压降。\n"
            "支持等温积分法（推荐）、平均密度法、Weymouth 公式、Panhandle A 公式。\n"
            "可反算最大流量及阻塞流检测。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        ll.addWidget(desc)

        def L(t):
            l = QLabel(t)
            l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            l.setMinimumWidth(120)
            l.setMaximumWidth(200)
            l.setStyleSheet("font-weight: bold; padding-right: 10px;")
            return l

        def H(t):
            l = QLabel(t)
            l.setMinimumWidth(100)
            l.setMaximumWidth(250)
            l.setStyleSheet("color: #95a5a6; font-size: 11px;")
            return l

        # ---- 流体性质 ----
        fg = QGroupBox("流体性质"); fg.setStyleSheet(group_style)
        fgrid = QGridLayout(fg); fgrid.setHorizontalSpacing(10); fgrid.setVerticalSpacing(10)
        fgrid.setColumnStretch(0, 2)  # 标签列可伸缩

        fgrid.setColumnStretch(1, 3)  # 输入框列可伸缩

        fgrid.setColumnStretch(2, 2)  # 提示列可伸缩


        self.fluid_combo = QComboBox()
        self.fluid_combo.setStyleSheet(COMBOBOX_STYLE)
        self.fluid_combo.addItems(["air","nitrogen","oxygen","hydrogen","co2","ng","steam","methane","ethane","propane","custom"])
        self.fluid_combo.setMinimumWidth(150)
        self.fluid_combo.setMaximumWidth(400)
        self.fluid_combo.currentTextChanged.connect(self._on_fluid)
        fgrid.addWidget(L("流体类型:"), 0, 0)
        fgrid.addWidget(self.fluid_combo, 0, 1)
        fgrid.addWidget(H("选择后自动填充物性"), 0, 2)

        self.mw_in = QLineEdit("28.97"); self.mw_in.setMinimumWidth(150)
        self.mw_in = QLineEdit("28.97"); self.mw_in.setMaximumWidth(400)
        self.mw_in.setValidator(QDoubleValidator(1, 200, 2))
        fgrid.addWidget(L("分子量 (g/mol):"), 1, 0)
        fgrid.addWidget(self.mw_in, 1, 1)
        fgrid.addWidget(H("air=28.97"), 1, 2)

        self.gamma_in = QLineEdit("1.40"); self.gamma_in.setMinimumWidth(150)
        self.gamma_in = QLineEdit("1.40"); self.gamma_in.setMaximumWidth(400)
        self.gamma_in.setValidator(QDoubleValidator(1.0, 2.0, 3))
        fgrid.addWidget(L("绝热指数 g:"), 2, 0)
        fgrid.addWidget(self.gamma_in, 2, 1)
        fgrid.addWidget(H("双原子=1.4"), 2, 2)

        self.R_in = QLineEdit("287.1"); self.R_in.setMinimumWidth(150)
        self.R_in = QLineEdit("287.1"); self.R_in.setMaximumWidth(400)
        self.R_in.setValidator(QDoubleValidator(50, 5000, 1))
        fgrid.addWidget(L("气体常数 R (J/(kg*K)):"), 3, 0)
        fgrid.addWidget(self.R_in, 3, 1)
        fgrid.addWidget(H("air=287.1"), 3, 2)

        self.mu_in = QLineEdit("18.27"); self.mu_in.setMinimumWidth(150)
        self.mu_in = QLineEdit("18.27"); self.mu_in.setMaximumWidth(400)
        self.mu_in.setValidator(QDoubleValidator(1, 100, 2))
        fgrid.addWidget(L("动力粘度 (uPa*s):"), 4, 0)
        fgrid.addWidget(self.mu_in, 4, 1)
        fgrid.addWidget(H("air=18.27"), 4, 2)
        ll.addWidget(fg)

        # ---- 管道参数 ----
        pg = QGroupBox("管道参数"); pg.setStyleSheet(group_style)
        pgrid = QGridLayout(pg); pgrid.setHorizontalSpacing(10); pgrid.setVerticalSpacing(10)

        self.dia_in = QLineEdit("100"); self.dia_in.setMinimumWidth(150)
        self.dia_in = QLineEdit("100"); self.dia_in.setMaximumWidth(400)
        self.dia_in.setValidator(QDoubleValidator(1, 2000, 1))
        pgrid.addWidget(L("管道内径 (mm):"), 0, 0)
        pgrid.addWidget(self.dia_in, 0, 1)
        pgrid.addWidget(H(""), 0, 2)

        self.len_in = QLineEdit("100"); self.len_in.setMinimumWidth(150)
        self.len_in = QLineEdit("100"); self.len_in.setMaximumWidth(400)
        self.len_in.setValidator(QDoubleValidator(1, 100000, 1))
        pgrid.addWidget(L("管道长度 (m):"), 1, 0)
        pgrid.addWidget(self.len_in, 1, 1)
        pgrid.addWidget(H(""), 1, 2)

        self.eps_in = QLineEdit("0.046"); self.eps_in.setMinimumWidth(150)
        self.eps_in = QLineEdit("0.046"); self.eps_in.setMaximumWidth(400)
        self.eps_in.setValidator(QDoubleValidator(0.001, 5, 3))
        pgrid.addWidget(L("绝对粗糙度 (mm):"), 2, 0)
        pgrid.addWidget(self.eps_in, 2, 1)
        pgrid.addWidget(H("新钢管=0.046"), 2, 2)

        self.eqf_in = QLineEdit("1.5"); self.eqf_in.setMinimumWidth(150)
        self.eqf_in = QLineEdit("1.5"); self.eqf_in.setMaximumWidth(400)
        self.eqf_in.setValidator(QDoubleValidator(1.0, 3.0, 1))
        pgrid.addWidget(L("当量长度系数:"), 3, 0)
        pgrid.addWidget(self.eqf_in, 3, 1)
        pgrid.addWidget(H("含管件时>1"), 3, 2)
        ll.addWidget(pg)

        # ---- 操作条件 ----
        cg = QGroupBox("操作条件"); cg.setStyleSheet(group_style)
        cgrid = QGridLayout(cg); cgrid.setHorizontalSpacing(10); cgrid.setVerticalSpacing(10)

        self.P1_in = QLineEdit("500"); self.P1_in.setMinimumWidth(150)
        self.P1_in = QLineEdit("500"); self.P1_in.setMaximumWidth(400)
        self.P1_in.setValidator(QDoubleValidator(1, 100000, 1))
        cgrid.addWidget(L("入口压力 (kPa):"), 0, 0)
        cgrid.addWidget(self.P1_in, 0, 1)
        cgrid.addWidget(H("绝对压力"), 0, 2)

        self.P2_in = QLineEdit("400"); self.P2_in.setMinimumWidth(150)
        self.P2_in = QLineEdit("400"); self.P2_in.setMaximumWidth(400)
        self.P2_in.setValidator(QDoubleValidator(1, 100000, 1))
        cgrid.addWidget(L("出口压力 (kPa):"), 1, 0)
        cgrid.addWidget(self.P2_in, 1, 1)
        cgrid.addWidget(H("绝对压力"), 1, 2)

        self.temp_in = QLineEdit("20"); self.temp_in.setMinimumWidth(150)
        self.temp_in = QLineEdit("20"); self.temp_in.setMaximumWidth(400)
        self.temp_in.setValidator(QDoubleValidator(-200, 1000, 1))
        cgrid.addWidget(L("温度 (C):"), 2, 0)
        cgrid.addWidget(self.temp_in, 2, 1)
        cgrid.addWidget(H("用于密度计算"), 2, 2)

        self.flow_in = QLineEdit("1000"); self.flow_in.setMinimumWidth(150)
        self.flow_in = QLineEdit("1000"); self.flow_in.setMaximumWidth(400)
        self.flow_in.setValidator(QDoubleValidator(0.1, 1e8, 1))
        cgrid.addWidget(L("质量流量 (kg/h):"), 3, 0)
        cgrid.addWidget(self.flow_in, 3, 1)
        cgrid.addWidget(H("已知流量时填写"), 3, 2)
        ll.addWidget(cg)

        # ---- 计算方法 ----
        mg = QGroupBox("计算方法"); mg.setStyleSheet(group_style)
        mgrid = QGridLayout(mg)
        self.mbg = QButtonGroup(self)
        self.rb_darcy = QRadioButton("Darcy-Weisbach 等温积分（推荐）")
        self.rb_darcy.setChecked(True)
        self.mbg.addButton(self.rb_darcy)
        mgrid.addWidget(self.rb_darcy, 0, 0)
        rb2 = QRadioButton("Darcy-Weisbach 平均密度")
        self.mbg.addButton(rb2); mgrid.addWidget(rb2, 0, 1)
        rb3 = QRadioButton("Weymouth 公式（天然气）")
        self.mbg.addButton(rb3); mgrid.addWidget(rb3, 1, 0)
        rb4 = QRadioButton("Panhandle A 公式（天然气）")
        self.mbg.addButton(rb4); mgrid.addWidget(rb4, 1, 1)
        ll.addWidget(mg)

        # ---- 计算按钮 ----
        bb = QHBoxLayout()
        b_calc = QPushButton("计算压降")
        b_calc.setStyleSheet("QPushButton{background-color:#3498db;color:white;font-weight:bold;font-size:14px;border-radius:8px;min-height:50px;}QPushButton:hover{background-color:#2980b9;}")
        b_calc.clicked.connect(self.calculate_pressure_drop)
        b_flow = QPushButton("反算流量")
        b_flow.setStyleSheet("QPushButton{background-color:#27ae60;color:white;font-weight:bold;font-size:14px;border-radius:8px;min-height:50px;}QPushButton:hover{background-color:#219a52;}")
        b_flow.clicked.connect(self.auto_calculate_flow)
        bb.addWidget(b_calc); bb.addWidget(b_flow)
        ll.addLayout(bb)

        # ---- 详细参数表 ----
        dg = QGroupBox("详细参数"); dg.setStyleSheet(group_style)
        dv = QVBoxLayout(dg)
        self.dtable = QTableWidget()
        self.dtable.setColumnCount(3)
        self.dtable.setHorizontalHeaderLabels(["参数", "数值", "单位"])
        self.dtable.setMaximumHeight(180)
        self.dtable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        dv.addWidget(self.dtable)
        ll.addWidget(dg)

        # ---- 底部按钮行 ----
        br = QHBoxLayout()
        b_clr = QPushButton("清空")
        b_clr.setStyleSheet("QPushButton{background-color:#95a5a6;color:white;font-weight:bold;border-radius:6px;padding:8px 20px;}QPushButton:hover{background-color:#7f8c8d;}")
        b_clr.clicked.connect(self.clear_inputs)
        b_txt = QPushButton("下载TXT报告")
        b_txt.setStyleSheet("QPushButton{background-color:#27ae60;color:white;font-weight:bold;border-radius:6px;padding:8px 20px;}QPushButton:hover{background-color:#219a52;}")
        b_txt.clicked.connect(self.download_txt_report)
        b_pdf = QPushButton("下载PDF报告")
        b_pdf.setStyleSheet("QPushButton{background-color:#e74c3c;color:white;font-weight:bold;border-radius:6px;padding:8px 20px;}QPushButton:hover{background-color:#c0392b;}")
        b_pdf.clicked.connect(self.generate_pdf_report)
        br.addWidget(b_clr); br.addStretch(); br.addWidget(b_txt); br.addWidget(b_pdf)
        ll.addLayout(br)

        # ---- 右侧结果区 ----
        right = QWidget(); right.setMinimumWidth(400)
        rl = QVBoxLayout(right); rl.setSpacing(10)
        rg = QGroupBox("计算结果"); rg.setStyleSheet(group_style)
        rv = QVBoxLayout(rg)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setStyleSheet("QTextEdit{background-color:#f8f9fa;border:1px solid #dee2e6;border-radius:6px;font-family:Consolas,monospace;font-size:13px;padding:10px;}")
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        rv.addWidget(self.result_text)
        rl.addWidget(rg)

        scroll_left.setWidget(left)
        main.addWidget(scroll_left, 2)
        main.addWidget(right, 1)

    # ---- 事件 ----
    def _on_fluid(self, name):
        d = self.FLUID_DB.get(name)
        if d:
            self.mw_in.setText(str(d["mw"]))
            self.gamma_in.setText(str(d["gamma"]))
            self.R_in.setText(str(d["R"]))
            self.mu_in.setText(str(d["mu"]))

    def _method(self):
        btns = self.mbg.buttons()
        if btns[0].isChecked(): return "darcy_integral"
        if btns[1].isChecked(): return "darcy_avg"
        if btns[2].isChecked(): return "weymouth"
        if btns[3].isChecked(): return "panhandle"
        return "darcy_integral"

    # ---- 物理工具 ----
    @staticmethod
    def _rho(P_Pa, T_K, R):
        return P_Pa / (R * T_K) if R * T_K > 0 else 0

    @staticmethod
    def _Re(d, v, rho, mu):
        return rho * v * d / mu if mu > 0 else 0

    @staticmethod
    def _friction(Re, eps, d):
        if Re <= 0: return 0.02
        if Re < 2000: return 64.0 / Re
        rr = eps / d
        f = 0.25 / (math.log10(rr / 3.7 + 5.74 / (Re ** 0.9))) ** 2
        for _ in range(50):
            rhs = rr / 3.7 + 2.51 / (Re * math.sqrt(f))
            f_new = 1.0 / (2.0 * math.log10(rhs)) ** 2
            if abs(f_new - f) < 1e-8: return f_new
            f = f_new
        return f

    @staticmethod
    def _sound(gamma, R, T_K):
        return math.sqrt(gamma * R * T_K)

    # ---- 主计算 ----
    def calculate_pressure_drop(self):
        try:
            mw    = float(self.mw_in.text())
            gamma = float(self.gamma_in.text())
            R     = float(self.R_in.text())
            mu    = float(self.mu_in.text()) * 1e-6
            d     = float(self.dia_in.text()) / 1000.0
            L     = float(self.len_in.text())
            eps   = float(self.eps_in.text()) / 1000.0
            eqf   = float(self.eqf_in.text())
            P1    = float(self.P1_in.text()) * 1000.0
            P2    = float(self.P2_in.text()) * 1000.0
            T_C   = float(self.temp_in.text())
            m_kg  = float(self.flow_in.text()) / 3600.0
            T_K   = T_C + 273.15
            A     = math.pi * d ** 2 / 4.0
            L_eq  = L * eqf

            rho1 = self._rho(P1, T_K, R)
            v1   = m_kg / (rho1 * A) if rho1 > 0 else 0
            Re1  = self._Re(d, v1, rho1, mu)
            f    = self._friction(Re1, eps, d)
            a    = self._sound(gamma, R, T_K)
            Ma   = v1 / a if a > 0 else 0

            P_crit = P1 * (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
            method = self._method()
            results = {}
            dp_kPa = 0.0

            if method == "darcy_integral":
                dp_sq = (f * L_eq / d) * (m_kg / A) ** 2 * R * T_K
                P2_calc = math.sqrt(max(0, P1 ** 2 - dp_sq))
                dp_kPa = (P1 - P2_calc) / 1000.0
                choked = P2_calc < P_crit
                results = {
                    "计算方法": "Darcy-Weisbach（等温积分）",
                    "摩擦系数 f": f,
                    "当量长度 Leq (m)": L_eq,
                    "入口密度 (kg/m3)": rho1,
                    "出口压力 (kPa)": P2_calc / 1000.0,
                    "阻塞流": "是" if choked else "否",
                }
            elif method == "darcy_avg":
                rho2 = self._rho(P2, T_K, R)
                rho_avg = (rho1 + rho2) / 2.0
                v_avg = m_kg / (rho_avg * A) if rho_avg > 0 else 0
                dp_Pa = f * (L_eq / d) * (rho_avg * v_avg ** 2) / 2.0
                dp_kPa = dp_Pa / 1000.0
                results = {
                    "计算方法": "Darcy-Weisbach（平均密度）",
                    "摩擦系数 f": f,
                    "平均密度 (kg/m3)": rho_avg,
                }
            elif method == "weymouth":
                L_km = L / 1000.0
                D_mm = d * 1000.0
                dp_sq = (P1/1000.0) ** 2 - (P2/1000.0) ** 2
                Q = 0.0330 * math.sqrt(max(0, dp_sq / L_km)) * D_mm ** (8.0/3.0) if L_km > 0 else 0
                dp_kPa = (P1 - P2) / 1000.0
                rho_std = self._rho(101325, 288.15, R)
                results = {
                    "计算方法": "Weymouth 公式",
                    "标准体积流量 (m3/h)": Q * 3600,
                    "等效质量流量 (kg/h)": Q * rho_std * 3600,
                }
            elif method == "panhandle":
                L_km = L / 1000.0
                D_mm = d * 1000.0
                dp_sq = (P1/1000.0) ** 2 - (P2/1000.0) ** 2
                E = 0.92
                Q = 0.0280 * E * (dp_sq / L_km) ** 0.5394 * D_mm ** 2.6182 if L_km > 0 else 0
                dp_kPa = (P1 - P2) / 1000.0
                rho_std = self._rho(101325, 288.15, R)
                results = {
                    "计算方法": "Panhandle A 公式",
                    "标准体积流量 (m3/h)": Q * 3600,
                    "效率因子 E": E,
                    "等效质量流量 (kg/h)": Q * rho_std * 3600,
                }

            self._last_result = {"dp_kPa": dp_kPa, "Re": Re1, "f": f, "Ma": Ma,
                              "is_choked": P2 < P_crit, "P_crit": P_crit / 1000.0}
            self._last_params = {"method": method, "mw": mw, "gamma": gamma, "R": R}
            self._display(dp_kPa, results, Re1, Ma, f)
            self._update_table(results, Re1, Ma, f)
            if self.data_manager:
                try:
                    self.data_manager.add_record("compressible_flow", self._get_history())
                except Exception:
                    pass
        except ValueError as e:
            self._err("输入错误：" + str(e))
        except Exception as e:
            self._err("计算错误：" + str(e))

    def auto_calculate_flow(self):
        try:
            gamma = float(self.gamma_in.text())
            R     = float(self.R_in.text())
            mu    = float(self.mu_in.text()) * 1e-6
            d     = float(self.dia_in.text()) / 1000.0
            L     = float(self.len_in.text())
            eps   = float(self.eps_in.text()) / 1000.0
            eqf   = float(self.eqf_in.text())
            P1    = float(self.P1_in.text()) * 1000.0
            P2    = float(self.P2_in.text()) * 1000.0
            T_C   = float(self.temp_in.text())
            T_K   = T_C + 273.15
            A     = math.pi * d ** 2 / 4.0
            L_eq  = L * eqf
            P_crit = P1 * (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
            m_est = 1.0
            for _ in range(30):
                rho1 = self._rho(P1, T_K, R)
                v1 = m_est / (rho1 * A)
                Re = self._Re(d, v1, rho1, mu)
                f = self._friction(Re, eps, d)
                dp_sq = P1 ** 2 - P2 ** 2
                if dp_sq <= 0:
                    QMessageBox.information(self, "提示", "入口压力不大于出口压力，无法计算。")
                    return
                m_new = A * math.sqrt(dp_sq * d / (f * L_eq * R * T_K))
                if abs(m_new - m_est) / max(m_new, 1e-10) < 1e-6:
                    m_est = m_new
                    break
                m_est = m_new
            rho_out = self._rho(P2, T_K, R)
            v_out = m_est / (rho_out * A)
            a = self._sound(gamma, R, T_K)
            Ma_out = v_out / a
            if P2 < P_crit:
                QMessageBox.warning(self, "阻塞流警告",
                    f"出口发生阻塞流！\n临界压力: {P_crit/1000:.1f} kPa\n"
                    f"最大流量: {m_est*3600:.1f} kg/h")
            elif Ma_out > 0.8:
                QMessageBox.warning(self, "高速警告",
                    f"出口马赫数 {Ma_out:.3f}，接近音速！\n"
                    f"流量: {m_est*3600:.1f} kg/h")
            self.flow_in.setText(str(round(m_est * 3600, 2)))
            QMessageBox.information(self, "完成",
                f"反算流量: {m_est*3600:.1f} kg/h\n出口马赫数: {Ma_out:.3f}")
        except Exception as e:
            QMessageBox.warning(self, "错误", "反算失败：" + str(e))

    # ---- 显示 ----
    def _display(self, dp_kPa, results, Re, Ma, f):
        flow_str = "层流" if Re < 2000 else ("过渡流" if Re < 4000 else "湍流")
        comp_str = "不可压缩" if Ma < 0.3 else ("可压缩" if Ma < 0.8 else "高速")
        lines = [
            "=" * 55,
            "       可压缩流体压降计算结果",
            "=" * 55, "",
            f"  计算方法   : {results.get(chr(35746)+chr(31639)+chr(26041)+chr(27861), chr(45))}",
            f"  压降        : {dp_kPa:.2f} kPa",
            f"  雷诺数      : {Re:.0f} ({flow_str})",
            f"  马赫数      : {Ma:.4f} ({comp_str})",
            f"  摩擦系数 f  : {f:.6f}",
        ]
        for k, v in results.items():
            if k == "计算方法": continue
            lines.append(f"  {k}  : {v:.4f}" if isinstance(v, float) else f"  {k}  : {v}")
        if Ma > 0.8:
            lines += ["", "  警告：马赫数>0.8，等温假设可能不成立！"]
        lines += ["", "=" * 55]
        self.result_text.setPlainText("\n".join(lines))

    def _update_table(self, results, Re, Ma, f):
        data = [
            ["马赫数", f"{Ma:.4f}", "-"],
            ["雷诺数", f"{Re:.0f}", "-"],
            ["摩擦系数 f", f"{f:.6f}", "-"],
            ["流动状态", "层流" if Re < 2000 else ("过渡流" if Re < 4000 else "湍流"), "-"],
        ]
        unit_map = {
            "当量长度 Leq (m)": "m", "入口密度 (kg/m3)": "kg/m3",
            "出口压力 (kPa)": "kPa", "平均密度 (kg/m3)": "kg/m3",
            "标准体积流量 (m3/h)": "m3/h", "等效质量流量 (kg/h)": "kg/h", "效率因子 E": "-",
        }
        for k, v in results.items():
            if k == "计算方法": continue
            unit = unit_map.get(k, "-")
            if isinstance(v, float):
                data.append([k, f"{v:.4f}", unit])
            else:
                data.append([k, str(v), unit])
        self.dtable.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, val in enumerate(row):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.dtable.setItem(i, j, item)

    def _err(self, msg):
        self.result_text.setPlainText("错误：" + msg)

    # ---- 清空 ----
    def clear_inputs(self):
        self.fluid_combo.setCurrentIndex(0)
        self.mw_in.setText("28.97"); self.gamma_in.setText("1.40")
        self.R_in.setText("287.1"); self.mu_in.setText("18.27")
        self.dia_in.setText("100"); self.len_in.setText("100")
        self.eps_in.setText("0.046"); self.eqf_in.setText("1.5")
        self.P1_in.setText("500"); self.P2_in.setText("400")
        self.temp_in.setText("20"); self.flow_in.setText("1000")
        self.rb_darcy.setChecked(True)
        self.result_text.clear(); self.dtable.setRowCount(0)
        self._last_result = {}; self._last_params = {}

    # ---- 历史数据 ----
    def _get_history(self):
        r = self._last_result
        p = self._last_params
        return {
            "inputs": {
                "method": p.get("method", ""),
                "diameter_mm": float(self.dia_in.text()),
                "length_m": float(self.len_in.text()),
                "P1_kPa": float(self.P1_in.text()),
                "P2_kPa": float(self.P2_in.text()),
                "temp_C": float(self.temp_in.text()),
                "flow_kg_h": float(self.flow_in.text()),
            },
            "outputs": {
                "dp_kPa": round(r.get("dp_kPa", 0), 2),
                "Re": round(r.get("Re", 0), 0),
                "Ma": round(r.get("Ma", 0), 4),
            }
        }

    def get_project_info(self):
        return {"calculator": "CompressibleFlowPressureDrop", "name": "可压缩流体压降"}

    def generate_report(self):
        return self.result_text.toPlainText()

    # ---- 下载报告 ----
    def download_txt_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先计算，再下载报告。"); return
        path, _ = QFileDialog.getSaveFileName(self, "保存TXT报告", "压降计算报告.txt", "文本文件 (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "成功", f"报告已保存：\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败：{e}")

    def generate_pdf_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先计算，再下载PDF。"); return
        path, _ = QFileDialog.getSaveFileName(self, "保存PDF报告", "压降计算报告.pdf", "PDF文件 (*.pdf)")
        if not path: return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.enums import TA_LEFT
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            font_paths = ["C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simsun.ttc"]
            fname = "Helvetica"
            for fp in font_paths:
                if os.path.exists(fp):
                    try:
                        pdfmetrics.registerFont(TTFont("CF", fp)); fname = "CF"; break
                    except Exception:
                        continue
            doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
            styles = getSampleStyleSheet()
            st = ParagraphStyle("B", fontName=fname, fontSize=10, leading=16, alignment=TA_LEFT)
            story = []
            for line in content.split("\n"):
                safe = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                story.append(Paragraph(safe if safe.strip() else "&nbsp;", st))
                story.append(Spacer(1, 1))
            doc.build(story)
            QMessageBox.information(self, "成功", f"PDF已保存：\n{path}")
        except ImportError:
            QMessageBox.critical(self, "错误", "缺少reportlab，请运行：pip install reportlab")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"PDF生成失败：{e}")


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = CompressibleFlowPressureDrop()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
