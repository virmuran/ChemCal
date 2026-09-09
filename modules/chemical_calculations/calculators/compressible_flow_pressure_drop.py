import math
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QButtonGroup,
    QRadioButton,
    QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K
from utils.docx_utils import ReportExporter  # DOCX 报告导出


class CompressibleFlowPressureDrop(CalculatorBase):
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
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_result = {}
        self._last_params = {}
        self.setup_ui()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    def init_data_manager(self):
        """初始化数据管理器（无外部传入时使用）"""
        self.data_manager = None

    def setup_ui(self):
        main = QHBoxLayout(self)
        main.setSpacing(15)
        main.setContentsMargins(10, 10, 10, 10)

        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left = QWidget()
        left.setStyleSheet("")
        ll = QVBoxLayout(left)
        ll.setSpacing(15)

        desc = QLabel(
            "计算可压缩流体（气体/蒸汽）管道压降。\n"
            "支持等温积分法（推荐）、平均密度法、Weymouth 公式、Panhandle A 公式。\n"
            "可反算最大流量及阻塞流检测。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        ll.addWidget(desc)

        def L(t):
            l = QLabel(t)
            l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            l.setStyleSheet(INPUT_LABEL_STYLE)
            return l

        def H(t):
            l = QLabel(t)
            l.setStyleSheet("font-style: italic;")
            return l

        # ---- 流体性质 ----
        fg = CalculatorBase.make_group_box("流体性质")
        fgrid = QGridLayout(fg); fgrid.setHorizontalSpacing(10); fgrid.setVerticalSpacing(12)
        fgrid.setColumnStretch(0, 4)
        fgrid.setColumnStretch(1, 8)
        fgrid.setColumnStretch(2, 5)

        self.fluid_combo = QComboBox()
        self.fluid_combo.setStyleSheet(COMBOBOX_STYLE)
        self.fluid_combo.addItems(["air","nitrogen","oxygen","hydrogen","co2","ng","steam","methane","ethane","propane","custom"])
        self.fluid_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.fluid_combo.currentTextChanged.connect(self._on_fluid)
        fgrid.addWidget(L("流体类型:"), 0, 0)
        fgrid.addWidget(self.fluid_combo, 0, 1)
        fgrid.addWidget(H("选择后自动填充物性"), 0, 2)

        self.mw_in = QLineEdit("28.97")
        self.mw_in.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mw_in.setValidator(QDoubleValidator(1, 200, 2))
        fgrid.addWidget(L("分子量 (g/mol):"), 1, 0)
        fgrid.addWidget(self.mw_in, 1, 1)
        fgrid.addWidget(H("air=28.97"), 1, 2)

        self.gamma_in = QLineEdit("1.40")
        self.gamma_in.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.gamma_in.setValidator(QDoubleValidator(1.0, 2.0, 3))
        fgrid.addWidget(L("绝热指数 g:"), 2, 0)
        fgrid.addWidget(self.gamma_in, 2, 1)
        fgrid.addWidget(H("双原子=1.4"), 2, 2)

        self.R_in = QLineEdit("287.1")
        self.R_in.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.R_in.setValidator(QDoubleValidator(50, 5000, 1))
        fgrid.addWidget(L("气体常数 R (J/(kg*K)):"), 3, 0)
        fgrid.addWidget(self.R_in, 3, 1)
        fgrid.addWidget(H("air=287.1"), 3, 2)

        self.mu_in = QLineEdit("18.27")
        self.mu_in.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mu_in.setValidator(QDoubleValidator(1, 100, 2))
        fgrid.addWidget(L("动力粘度 (uPa*s):"), 4, 0)
        fgrid.addWidget(self.mu_in, 4, 1)
        fgrid.addWidget(H("air=18.27"), 4, 2)
        ll.addWidget(fg)

        # ---- 管道参数 ----
        pg = CalculatorBase.make_group_box("管道参数")
        pgrid = QGridLayout(pg); pgrid.setHorizontalSpacing(10); pgrid.setVerticalSpacing(12)
        pgrid.setColumnStretch(0, 4)
        pgrid.setColumnStretch(1, 8)
        pgrid.setColumnStretch(2, 5)

        self.dia_in = QLineEdit("100")
        self.dia_in.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.dia_in.setValidator(QDoubleValidator(1, 2000, 1))
        pgrid.addWidget(L("管道内径 (mm):"), 0, 0)
        pgrid.addWidget(self.dia_in, 0, 1)
        pgrid.addWidget(H(""), 0, 2)

        self.len_in = QLineEdit("100")
        self.len_in.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.len_in.setValidator(QDoubleValidator(1, 100000, 1))
        pgrid.addWidget(L("管道长度 (m):"), 1, 0)
        pgrid.addWidget(self.len_in, 1, 1)
        pgrid.addWidget(H(""), 1, 2)

        self.eps_in = QLineEdit("0.046")
        self.eps_in.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.eps_in.setValidator(QDoubleValidator(0.001, 5, 3))
        pgrid.addWidget(L("绝对粗糙度 (mm):"), 2, 0)
        pgrid.addWidget(self.eps_in, 2, 1)
        pgrid.addWidget(H("新钢管=0.046"), 2, 2)

        self.eqf_in = QLineEdit("1.5")
        self.eqf_in.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.eqf_in.setValidator(QDoubleValidator(1.0, 3.0, 1))
        pgrid.addWidget(L("当量长度系数:"), 3, 0)
        pgrid.addWidget(self.eqf_in, 3, 1)
        pgrid.addWidget(H("含管件时>1"), 3, 2)
        ll.addWidget(pg)

        # ---- 操作条件 ----
        cg = CalculatorBase.make_group_box("操作条件")
        cgrid = QGridLayout(cg); cgrid.setHorizontalSpacing(10); cgrid.setVerticalSpacing(12)
        cgrid.setColumnStretch(0, 4)
        cgrid.setColumnStretch(1, 8)
        cgrid.setColumnStretch(2, 5)

        self.P1_in = QLineEdit("500")
        self.P1_in.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.P1_in.setValidator(QDoubleValidator(1, 100000, 1))
        cgrid.addWidget(L("入口压力 (kPa):"), 0, 0)
        cgrid.addWidget(self.P1_in, 0, 1)
        cgrid.addWidget(H("绝对压力"), 0, 2)

        self.P2_in = QLineEdit("400")
        self.P2_in.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.P2_in.setValidator(QDoubleValidator(1, 100000, 1))
        cgrid.addWidget(L("出口压力 (kPa):"), 1, 0)
        cgrid.addWidget(self.P2_in, 1, 1)
        cgrid.addWidget(H("绝对压力"), 1, 2)

        self.temp_in = QLineEdit("20")
        self.temp_in.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.temp_in.setValidator(QDoubleValidator(-200, 1000, 1))
        cgrid.addWidget(L("温度 (C):"), 2, 0)
        cgrid.addWidget(self.temp_in, 2, 1)
        cgrid.addWidget(H("用于密度计算"), 2, 2)

        self.flow_in = QLineEdit("1000")
        self.flow_in.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.flow_in.setValidator(QDoubleValidator(0.1, 1e8, 1))
        cgrid.addWidget(L("质量流量 (kg/h):"), 3, 0)
        cgrid.addWidget(self.flow_in, 3, 1)
        cgrid.addWidget(H("已知流量时填写"), 3, 2)
        ll.addWidget(cg)

        # ---- 计算方法 ----
        mg = CalculatorBase.make_group_box("计算方法")
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
        ll.addStretch()

        # ---- 右侧结果区 ----
        right = QWidget(); right.setMinimumWidth(300)
        rl = QVBoxLayout(right); rl.setSpacing(15)
        rg = CalculatorBase.make_group_box("计算结果")
        rv = QVBoxLayout(rg)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        # 结果框统一标准：边框/背景/文字色交给主题系统，仅指定等宽字体
        self.result_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: 13px;
            } """)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        rv.addWidget(self.result_text)
        rl.addWidget(rg)

        # ---- 详细参数表（移入右栏）----
        dg = CalculatorBase.make_group_box("详细参数")
        dv = QVBoxLayout(dg)
        self.dtable = QTableWidget()
        self.dtable.setColumnCount(3)
        self.dtable.setHorizontalHeaderLabels(["参数", "数值", "单位"])
        self.dtable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dtable.verticalHeader().setVisible(False)
        self.dtable.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dtable.setFocusPolicy(Qt.NoFocus)
        # 不写死高度：表格 Expanding 吃掉右栏富余空间，能显示几行就显示几行，窗口不被撑大
        self.dtable.setMinimumHeight(120)
        self.dtable.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        dv.addWidget(self.dtable)
        rl.addWidget(dg, 1)

        # ---- 底部按钮行：清空 | DOCX | PDF ----
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(CLEAR_BTN_STYLE)
        clear_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        clear_btn.clicked.connect(self.clear_inputs)
        docx_btn = QPushButton("DOCX")
        docx_btn.setStyleSheet(DOCX_BTN_STYLE)
        docx_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        docx_btn.clicked.connect(self.download_docx_report)
        pdf_btn = QPushButton("PDF")
        pdf_btn.setStyleSheet(PDF_BTN_STYLE)
        pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pdf_btn.clicked.connect(self.download_pdf_report)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(docx_btn)
        btn_layout.addWidget(pdf_btn)
        rl.addLayout(btn_layout)

        # ---- 计算按钮行（最底部）：反算流量 | 计算 ----
        calc_layout = QHBoxLayout()
        calc_layout.setSpacing(8)
        b_flow = QPushButton("反算流量")
        b_flow.setMinimumHeight(50)
        b_flow.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        b_flow.setStyleSheet(CALC_BUTTON_STYLE)
        b_flow.clicked.connect(self.auto_calculate_flow)
        b_calc = self.make_calc_button("计 算")
        b_calc.clicked.connect(self.calculate_pressure_drop)
        calc_layout.addWidget(b_flow)
        calc_layout.addWidget(b_calc)
        rl.addLayout(calc_layout)

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
            T_K   = T_C + C_TO_K
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
            T_K   = T_C + C_TO_K
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
            f"  计算方法   : {results.get('计算方法', '-')}",
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
    def _get_history_data(self):
        """提供历史记录所需的输入输出数据"""
        r = self._last_result
        p = self._last_params
        try:
            inputs = {
                "计算方法": p.get("method", ""),
                "管道内径_mm": float(self.dia_in.text() or 0),
                "管道长度_m": float(self.len_in.text() or 0),
                "入口压力_kPa": float(self.P1_in.text() or 0),
                "出口压力_kPa": float(self.P2_in.text() or 0),
                "温度_C": float(self.temp_in.text() or 0),
                "质量流量_kg_h": float(self.flow_in.text() or 0),
            }
        except (ValueError, TypeError):
            return {"inputs": {}, "outputs": {}}
        outputs = {
            "压降_kPa": round(r.get("dp_kPa", 0), 2),
            "雷诺数": round(r.get("Re", 0), 0),
            "马赫数": round(r.get("Ma", 0), 4),
        }
        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        """获取工程信息 - 返回 dict"""
        try:
            saved_info = {}
            if self.data_manager:
                saved_info = self.data_manager.get_project_info()
            return {
                'company_name': saved_info.get('company_name', ''),
                'project_number': saved_info.get('project_number', ''),
                'project_name': saved_info.get('project_name', ''),
                'subproject_name': saved_info.get('subproject_name', ''),
                'report_number': ''
            }
        except Exception as e:
            print(f"获取工程信息失败: {e}")
            return {}

    def generate_report(self):
        """生成计算书 - 返回纯文本"""
        try:
            # 获取当前结果文本
            result_text = self.result_text.toPlainText()
            
            # 检查条件
            if not result_text or "计算结果" not in result_text:
                QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
                return ""
            
            # 获取工程信息
            project_info = self.get_project_info()
            
            # 添加报告头信息
            report = f"""工程计算书 - 可压缩流体压降计算
计算工具: ChemCal 工程计算模块
========================================

"""
            report += result_text
            
            # 添加工程信息部分
            report += f"""══════════
 工程信息
══════════

    公司名称: {project_info.get('company_name', '')}
    工程编号: {project_info.get('project_number', '')}
    工程名称: {project_info.get('project_name', '')}
    子项名称: {project_info.get('subproject_name', '')}
    计算日期: {datetime.now().strftime('%Y-%m-%d')}

══════════
计算书标识
══════════

    计算书编号: {project_info.get('report_number', '')}
    版本: 1.0
    状态: 正式计算书

══════════
备注说明
══════════

    1. 本计算书基于气体动力学及流体力学原理
    2. 计算结果仅供参考，实际应用需考虑安全系数
    3. 马赫数>0.8 时等温假设可能不成立，请选用绝热模型复核
    4. 计算条件变更时应重新进行计算

---
生成于 ChemCal 工程计算模块
"""
            return report
            
        except Exception as e:
            print(f"生成计算书失败: {e}")
            return ""

    # ---- 下载报告 ----
    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "可压缩流体压降")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "可压缩流体压降")
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = CompressibleFlowPressureDrop()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
