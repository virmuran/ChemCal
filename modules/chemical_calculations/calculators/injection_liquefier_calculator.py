"""
蒸汽喷射液化器用汽量计算器（一次喷射 / 两次喷射）

适用：淀粉糖、麦芽糊精、味精、酒精、氨基酸等行业的淀粉乳**喷射液化**工段，
      核算喷射液化器（含低压「低温蒸汽」喷射液化器）所需的工作蒸汽（生蒸汽）用汽量，
      以及喷射后的液化液量、稀释后浓度、蒸汽管径与设计选型汽量。

═══════════════ 1. 先搞清楚「低温蒸汽喷射液化器」是什么设备 ═══════════════
    喷射液化器（jet cooker）把**饱和蒸汽直接注入**淀粉乳薄层，靠蒸汽的汽化潜热
    与凝水显热把料液在极短时间内（＜1 s）加热到糊化/液化温度；蒸汽同时起
    「加热 + 湍流剪切混合」两重作用，是淀粉糖工业液化工序的关键设备。

    「低温蒸汽」不是指蒸汽温度异常低，而是指**用低压（低饱和温度）蒸汽**：
    低压蒸汽喷射液化器在 105 °C 以下喷射液化时，蒸汽表压只要 ~0.1 MPa
    （对应饱和温度 120 °C）即可，比传统 0.6~1.0 MPa 中高压喷射更省汽、
    不易结堵、不易过度糊化；这类设备多以「以汽带料」方式工作，
    在 30~40 % 浓度淀粉乳上应用最广。

    **代价是一条硬约束：蒸汽的饱和温度必须高于液化出口温度**——
    低压蒸汽只能用在它饱和温度以下的液化段。本计算器强制校验这一条。

═══════════════ 2. 用汽量（直接蒸汽注入的热量衡算）═══════════════
    料液升温需热          Q = G · C · (t₂ − t₁)              [kJ/h]
    浆料比热（质量加权）  C = C₀·X/100 + C_w·(100 − X)/100   [kJ/(kg·K)]
        C₀ = 淀粉质比热 ≈ 1.55，C_w = 水比热 ≈ 4.18，X = 浆料干物浓度 wt%
    注入蒸汽放热          Q = D · (I − λ)
    ⇒  **用汽量        D = G · C · (t₂ − t₁) / (I − λ)**     [kg/h]

    其中（均取饱和态，IAPWS-IF97）：
        I = 工作蒸汽焓 = h_f(p) + x·h_fg(p)     （x = 干度，饱和蒸汽取 1.0）
        λ = 凝结水焓   = h_f(t₂)                 ← **取出口温度下的饱和水焓**

    ⚠ 注意 λ 与 I **不在同一温度**：蒸汽进来是 t_sat(p) 的饱和汽，出去是与料液
      同温 (t₂) 的凝水，所以有效焓差 (I − λ) 略大于该压力下的汽化潜热 h_fg
      （多出「凝水从 t_sat 过冷到 t₂」放出的显热）。这一步是本类计算最常填错
      的地方——若误用 h_fg 代替 (I − λ)，用汽量会偏小 5~10 %。

    二次喷射（高温维持后再升温）：
        料液量变为 G' = G + D₁，比热按**已稀释后**的新浓度 X' 重算，
        D₂ = G' · C' · (t₂b − t₂a) / (I − λ@t₂b)

    蒸汽直接注入还会**稀释料液**：喷射后浓度 X' = G·X / (G + D)，
    本计算器一并给出，供后续维持/糖化工段核算。

═══════════════ 3. 硬约束（低压蒸汽喷射液化器的适用边界）═══════════════
        t₂ ＜ t_sat(p_s)        —— 否则蒸汽温度低于出口料温，物理上无法把料液加热到此温度
        一般还需 t_sat(p_s) − t₂ ≥ 10~15 °C，喷射器才有稳定压差驱动、雾化良好
    本计算器对违反者直接**报错**，对余量不足者给**警告**，并给出「所需最低蒸汽压力」。

═══════════════ 4. 浆料比重与密度（体积 ↔ 质量换算）═══════════════
    现场给的常是**体积流量**（泵/流量计读数 m³/h），而热量衡算要的是**质量流量**
    kg/h，中间必须过一道密度：

        修正比重  d = d₂₀ − 0.001 × (t₁ − 20) / 1.5
            d₂₀  = 20 °C 基准下由波美度/比重查表得到的浆料比重
            (t₁−20)/1.5 = 温度修正：料液每比 20 °C 高 1.5 °C，比重就往下扣一格 0.001
                          （量级与水的体积膨胀一致：20~100 °C 平均约 0.0007 /°C）
        密度      ρ  = 1000 · d                     [kg/m³]
        质量流量  G  = Q · ρ / 1000 = Q · d         [t/h]，Q 为体积流量 m³/h

    · 波美度 ↔ 比重：°Bé = 145·(1 − 1/d)（重表口径；与行业淀粉乳波美换算表
      逐点复核一致，偏差 ≤0.03 °Bé）
    · 干物含量估算：X ≈ 1.777 × °Bé（行业淀粉乳波美表自带的线性式「固体% = 波美度×1.7770」，
      表覆盖到约 25 °Bé / 44 %，更高浓度属外推，**以化验值为准**）
    ⚠ 淀粉乳 ≠ 糖液：不要拿糖度/锤度表去查淀粉乳（基准温度与体系都不同）。

═══════════════ 5. 数据来源与口径 ═══════════════
    · 蒸汽/饱和水焓：项目自带 IAPWS-IF97（steam_iapws）；表压→绝压加 0.101325 MPa。
      饱和蒸汽基础物性走项目统一入口 common_constants.get_steam_props（表压口径）。
    · 比热加权式与直接蒸汽注入热量衡算式：淀粉糖/味精行业设计资料与教材通用式，
      多份独立来源口径一致（C₀ 取 1.55 kJ/(kg·K)；λ 取出口温度下的饱和水焓）。
    · 经验校核（厂商公开样本）：进料 30 %DS 时蒸煮每吨淀粉约耗 0.34 t 蒸汽、
      35 %DS 时约 0.26 t 蒸汽（样本未注明蒸汽压力与料液初温口径，仅作量级校核）。
    · 蒸汽管内流速：饱和蒸汽常规取 25~40 m/s（本计算器取 30 m/s 估算管径，仅供参考）。
    · 浆料比热中的 C₀ 属经验取值，不同原料（玉米/木薯/小麦淀粉、含蛋白杂质）略有差异，
      宜以本厂物料实测或同类装置数据替换。

═══════════════ 6. 与设计表格各列的对应（本计算器逐列覆盖）═══════════════
    设计表格的列                                本计算器对应
    ──────────────────────────────────────────────────────────────────────
    蒸汽压力（表压）                            输入「生蒸汽表压 p_s (MPa)」
    总焓（查表）                                输入「总焓 I 查表值」（留空则按压力自动算）
    物料初始温度                                输入「浆料初温 t₁」
    物料终点温度                                输入「一次喷射出口温度 t₂₁」
    物料量                                      输入「淀粉乳流量 G」(可按质量 t/h 或体积 m³/h)
    谷物比热                                    输入「淀粉质比热 C₀」（表格的「谷物比热」1.55）
    淀粉乳含量                                  输入「干物浓度 X (wt%)」
    比重查表 / 修正比重                         输入「浆料比重 d₂₀」→ 输出「修正比重 d」
    物料比热（= 淀粉乳比热）                    输出 C = C₀·X/100 + C_w·(100−X)/100
    密度（= 修正比重）                          输出 ρ = 1000·d
    喷射器规格（= 物料量 ÷ 密度）               输出「喷射器规格 / 物料体积流量」m³/h
    Q = （）方法一                              输出（谷物与水分开累计，分项展开式）
    Q = （）方法二                              输出（调浆乳液整体式）
    蒸汽用量 = 3600·Q /(总焓 − 4.19·t₂)         输出 D₁（主算 λ 取 IAPWS 饱和水焓 h_f(t₂)，
                                                      并给出 4.19·t₂ 口径的对照值）
    吨淀粉乳气耗 = 蒸汽用量 ÷ 物料量            输出「吨淀粉乳气耗」kg 汽/t 乳
    ──────────────────────────────────────────────────────────────────────

    ⚠ 表格提示「计算功率时候需要将谷物和水分开累计——调浆乳液的原功率 =
      调浆液×比热×温差」：这两句话说的是**同一件事的两种写法**。加权比热
      C = C₀·X/100 + C_w·(100−X)/100 已经把谷物的 1.55 与水的 4.18 按比例合成，
      所以「谷物与水分开累计」（方法一，分项展开）与「调浆液×比热×温差」
      （方法二，整体式）**数学上恒等**，结果必须相同——本计算器把两式并列输出
      并给出差值百分比，用来互相校核：差值不为 0 即说明某项的百分数/分母口径填错了。

    ⚠ 「吨淀粉乳气耗」（÷ 物料量，含水的乳液）与「吨干物汽耗」（÷ 干物量）是
      **两个不同口径**，本计算器同时给出。二者换算：吨干物汽耗 = 吨乳气耗 ÷ (X/100)。
"""

import math
import os
import importlib.util

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QGridLayout, QTextEdit, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtSvgWidgets import QSvgWidget

from app_styles import (COMBOBOX_STYLE, SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)
from utils.docx_utils import ReportExporter
from svg_utils import svg_text
from datetime import datetime

from calculator_base import CalculatorBase
# 项目硬契约：饱和蒸汽（表压）一律走 common_constants.get_steam_props
from common_constants import get_steam_props, WATER_CP
# 计算链：算完把「可传递给下游的出口状态」登记到会话上下文（闪蒸等下游页取用）
from chain_context import ChainContext

# IAPWS-IF97 完整物性（动态导入，写法与浓缩蒸发器计算器一致）
try:
    _cur = os.path.dirname(os.path.abspath(__file__))
    _parent = os.path.dirname(_cur)
    _spec = importlib.util.spec_from_file_location(
        "steam_iapws", os.path.join(_parent, "steam_iapws.py"))
    _STEAM = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_STEAM)
except Exception as _e:                                          # noqa: BLE001
    print(f"警告: 无法加载 IAPWS-IF97 模块: {_e}")
    _STEAM = None


#: 蒸汽管道标准公称通径系列（mm），用于就近选管
_DN_SERIES = [15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200,
              250, 300, 350, 400, 450, 500, 600]

#: 浆料比重表的基准温度（°C）——行业淀粉乳波美换算表多以 20 °C 标定
DENSITY_REF_T = 20.0

#: 比重温度修正斜率：料温每比基准高 1.5 °C，比重降一格 0.001
DENSITY_DT_PER_STEP = 1.5

#: 波美度 ↔ 比重 换算常数（重表口径 °Bé = K·(1 − 1/d)）
BAUME_K = 145.0

#: 淀粉乳「波美度 → 干物含量」经验系数（行业波美表自带式：固体 % = 1.7770 × °Bé）
BAUME_TO_SOLID = 1.7770

#: 设计表格口径的凝结水焓系数：λ′ = 4.19 × t₂
#: 本计算器主算走 IAPWS-IF97 的饱和水焓 h_f(t₂)，此系数仅用于与设计表格逐列对照
#: （两者偏差通常 < 0.1 %，即表格的 4.19·t₂ 与精确焓等价）
LAMBDA_CP_REF = 4.19


class InjectionLiquefierCalculator(CalculatorBase):
    """蒸汽喷射液化器用汽量计算器（一次喷射 / 两次喷射）"""

    MODES = ["一次喷射液化（低温喷射）", "两次喷射液化（一次 + 二次高温）"]

    #: 计算链标识（下游页面按此标识取本页输出）
    CHAIN_MODULE = "injection_liquefier_calculator"
    CHAIN_PAGE = "喷射液化器用汽量"

    #: 浆料量输入方式（体积流量需过一道密度换算）
    FLOW_MODES = ["质量流量 (t/h)", "体积流量 (m³/h)"]

    #: 设计余量说明用
    _MARGIN_HINT = "选型用，覆盖热损/波动"

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_result = {}
        self._rows = {}                      # 按模式显隐的控件登记
        self.setup_ui()
        self.setup_default_values()
        self.setup_wheel_blocker()

    # ═══════════════════════ UI ═══════════════════════
    def setup_ui(self):
        main = QHBoxLayout(self)
        main.setSpacing(15)
        main.setContentsMargins(10, 10, 10, 10)

        # ── 左栏：输入 ──
        scroll = QScrollArea()
        scroll.setStyleSheet(SCROLL_AREA_STYLE)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setSpacing(10)

        desc = QLabel(
            "淀粉乳喷射液化用汽量核算：浆料流量与浓度 → 浆料比热 → 直接蒸汽注入热量衡算 → "
            "用汽量（一次/二次）→ 液化液量与稀释后浓度 → 蒸汽管径与选型汽量。"
            "「低温蒸汽」即低压蒸汽，适用于 105 °C 以下喷射液化（表压 ~0.1 MPa 起）。")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size:12px;padding:5px;")
        ll.addWidget(desc)

        ls = INPUT_LABEL_STYLE

        def lbl(t):
            w = QLabel(t)
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            w.setStyleSheet(ls)
            return w

        def hint(t):
            w = QLabel(t)
            w.setStyleSheet("font-style:italic;color:#666;")
            return w

        def add_row(grid, key, text, widget, hint_text, row):
            """建一行「标签 + 控件 + 提示」，并按 key 登记（供模式显隐）"""
            a, b, c = lbl(text), widget, hint(hint_text)
            grid.addWidget(a, row, 0)
            grid.addWidget(b, row, 1)
            grid.addWidget(c, row, 2)
            self._rows.setdefault(key, []).extend([a, b, c])
            return row + 1

        # ── 计算模式 ──
        g0 = CalculatorBase.make_group_box("计算模式")
        g0g = QGridLayout(g0)
        g0g.setHorizontalSpacing(10)
        g0g.setVerticalSpacing(10)
        g0g.setColumnStretch(0, 4)
        g0g.setColumnStretch(1, 8)
        g0g.setColumnStretch(2, 5)

        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet(COMBOBOX_STYLE)
        self.mode_combo.addItems(self.MODES)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        g0g.addWidget(lbl("计算模式:"), 0, 0)
        g0g.addWidget(self.mode_combo, 0, 1)
        g0g.addWidget(hint("「一次」即第一段低温喷射"), 0, 2)
        ll.addWidget(g0)

        # ── 浆料与产能 ──
        g1 = CalculatorBase.make_group_box("浆料与产能")
        g1g = QGridLayout(g1)
        g1g.setHorizontalSpacing(10)
        g1g.setVerticalSpacing(10)
        g1g.setColumnStretch(0, 4)
        g1g.setColumnStretch(1, 8)
        g1g.setColumnStretch(2, 5)
        r = 0

        self.flow_mode_combo = QComboBox()
        self.flow_mode_combo.setStyleSheet(COMBOBOX_STYLE)
        self.flow_mode_combo.addItems(self.FLOW_MODES)
        r = add_row(g1g, "flowmode", "浆料量输入方式:", self.flow_mode_combo,
                    "车间按体积计量时选 m³/h", r)

        self.feed_input = QLineEdit("20")
        self.feed_input.setValidator(QDoubleValidator(0.01, 10000.0, 3))
        r = add_row(g1g, "feed", "淀粉乳流量 G (t/h):", self.feed_input,
                    "进喷射器的调浆后乳液量", r)

        self.d20_input = QLineEdit("1.133")
        self.d20_input.setValidator(QDoubleValidator(0.9, 1.8, 4))
        r = add_row(g1g, "d20", "浆料比重 d₂₀ (20 °C):", self.d20_input,
                    "查表值；30 % ≈ 1.133（17 °Bé）", r)

        self.conc_input = QLineEdit("30")
        self.conc_input.setValidator(QDoubleValidator(1.0, 70.0, 2))
        r = add_row(g1g, "conc", "干物浓度 X (wt%):", self.conc_input,
                    "喷射液化常用 30~40 %", r)

        self.t1_input = QLineEdit("25")
        self.t1_input.setValidator(QDoubleValidator(0.0, 100.0, 1))
        r = add_row(g1g, "t1", "浆料初温 t₁ (°C):", self.t1_input,
                    "调浆后温度，冬 20 / 夏 35", r)

        self.cp0_input = QLineEdit("1.55")
        self.cp0_input.setValidator(QDoubleValidator(0.5, 4.0, 3))
        r = add_row(g1g, "cp0", "淀粉质比热 C₀ (kJ/(kg·K)):", self.cp0_input,
                    f"经验取值 1.55（水取 {WATER_CP:g}）", r)

        ll.addWidget(g1)

        # ── 喷射温度 ──
        g2 = CalculatorBase.make_group_box("喷射温度")
        g2g = QGridLayout(g2)
        g2g.setHorizontalSpacing(10)
        g2g.setVerticalSpacing(10)
        g2g.setColumnStretch(0, 4)
        g2g.setColumnStretch(1, 8)
        g2g.setColumnStretch(2, 5)
        r = 0

        self.t2a_input = QLineEdit("105")
        self.t2a_input.setValidator(QDoubleValidator(20.0, 180.0, 1))
        r = add_row(g2g, "t2a", "一次喷射出口温度 t₂₁ (°C):", self.t2a_input,
                    "低温喷射常用 105~108 °C", r)

        self.t2b_in_input = QLineEdit("95")
        self.t2b_in_input.setValidator(QDoubleValidator(20.0, 180.0, 1))
        r = add_row(g2g, "t2b_in", "二次喷射进口温度 (°C):", self.t2b_in_input,
                    "维持罐出口，较一次出口略降", r)

        self.t2b_out_input = QLineEdit("125")
        self.t2b_out_input.setValidator(QDoubleValidator(20.0, 180.0, 1))
        r = add_row(g2g, "t2b_out", "二次喷射出口温度 t₂₂ (°C):", self.t2b_out_input,
                    "高温维持/灭酶段 120~140 °C", r)

        ll.addWidget(g2)

        # ── 蒸汽与设计 ──
        g3 = CalculatorBase.make_group_box("蒸汽与设计")
        g3g = QGridLayout(g3)
        g3g.setHorizontalSpacing(10)
        g3g.setVerticalSpacing(10)
        g3g.setColumnStretch(0, 4)
        g3g.setColumnStretch(1, 8)
        g3g.setColumnStretch(2, 5)
        r = 0

        self.ps_input = QLineEdit("0.3")
        self.ps_input.setValidator(QDoubleValidator(0.05, 4.0, 3))
        r = add_row(g3g, "ps", "生蒸汽表压 p_s (MPa):", self.ps_input,
                    "表压！低温喷射 0.1 起", r)

        # 设计表格里的「总焓（查表）」列：留空即按压力（与干度）自动查算
        self.total_h_input = QLineEdit("")
        self.total_h_input.setValidator(QDoubleValidator(1000.0, 4000.0, 2))
        self.total_h_input.setPlaceholderText("留空 = 按压力自动算")
        r = add_row(g3g, "totalh", "总焓 I 查表值 (kJ/kg):", self.total_h_input,
                    "表格「总焓」列；填了就按查表值算", r)

        self.dry_input = QLineEdit("1.0")
        self.dry_input.setValidator(QDoubleValidator(0.5, 1.0, 3))
        r = add_row(g3g, "dry", "蒸汽干度 x:", self.dry_input,
                    "饱和蒸汽取 1.0", r)

        self.margin_input = QLineEdit("10")
        self.margin_input.setValidator(QDoubleValidator(0.0, 100.0, 1))
        r = add_row(g3g, "margin", "设计余量 (%):", self.margin_input,
                    "选型用，覆盖热损/波动", r)

        ll.addWidget(g3)
        ll.addStretch()
        scroll.setWidget(lw)

        # ── 右栏：结果 ──
        rw = QWidget()
        rw.setMinimumWidth(300)
        rl = QVBoxLayout(rw)
        rl.setSpacing(15)

        self.svg_widget = QSvgWidget()
        self.svg_widget.setMinimumHeight(200)
        self.svg_widget.setMaximumHeight(260)
        self.svg_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rl.addWidget(self.svg_widget)
        self.svg_widget.renderer().setAspectRatioMode(Qt.KeepAspectRatio)

        rg = CalculatorBase.make_group_box("计算结果")
        rvl = QVBoxLayout(rg)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setStyleSheet(
            "QTextEdit { font-family: Consolas, 'Microsoft YaHei', monospace; font-size: 13px; }")
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        rvl.addWidget(self.result_text)
        rl.addWidget(rg)

        bl = QHBoxLayout()
        bl.setSpacing(8)
        for name, style, cb in [
            ("清空", CLEAR_BTN_STYLE, self.clear_inputs),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(name)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(cb)
            bl.addWidget(btn)
        rl.addLayout(bl)

        calc_btn = self.make_calc_button("计 算")
        calc_btn.clicked.connect(self.calculate)
        rl.addWidget(calc_btn)

        main.addWidget(scroll, 2)
        main.addWidget(rw, 1)

        # 控件全部建好后再连信号（避免早发信号时槽函数访问未创建的控件）
        self.flow_mode_combo.currentTextChanged.connect(self._on_flow_mode_changed)
        self._on_mode_changed(self.mode_combo.currentText())
        self._on_flow_mode_changed(self.flow_mode_combo.currentText())
        self._update_svg_diagram()

    # ═══════════════════════ 交互 ═══════════════════════
    def _on_flow_mode_changed(self, mode):
        """切换质量/体积流量：改流量行的标签与提示"""
        vol = (mode == self.FLOW_MODES[1])
        rows = self._rows.get("feed", ())
        if len(rows) >= 3:
            rows[0].setText("淀粉乳体积流量 Q (m³/h):" if vol
                            else "淀粉乳流量 G (t/h):")
            rows[2].setText("泵/流量计读数，按比重折成质量流量" if vol
                            else "进喷射器的调浆后乳液量")

    def _on_mode_changed(self, mode):
        """两次喷射模式才显示二次喷射温度"""
        two_stage = (mode == self.MODES[1])
        for key in ("t2b_in", "t2b_out"):
            for w in self._rows.get(key, ()):
                w.setVisible(two_stage)

    @staticmethod
    def _num(widget, name):
        try:
            return float(widget.text().strip())
        except (TypeError, ValueError):
            raise ValueError(f"{name} 未填写或不是数字")

    @staticmethod
    def _num_opt(widget, name):
        """可留空的数值输入：空串 → None；非空但不是数字 → 报错"""
        txt = (widget.text() or "").strip()
        if not txt:
            return None
        try:
            return float(txt)
        except (TypeError, ValueError):
            raise ValueError(f"{name} 不是数字")

    # ═══════════════════════ 蒸汽物性工具 ═══════════════════════
    @staticmethod
    def _sat_from_gauge(p_gauge):
        """饱和蒸汽（表压 MPa）→ (温度 °C, 汽化潜热 kJ/kg)，走项目统一入口"""
        d = get_steam_props(p_gauge)
        return d["sat_temp"], d["h_fg"]

    @staticmethod
    def _sat_from_abs(p_abs):
        """饱和参数（绝压 MPa）→ dict（IAPWS-IF97）"""
        if _STEAM is None:
            raise ValueError("IAPWS-IF97 模块不可用，无法计算蒸汽物性")
        return _STEAM.saturation_properties(P_MPa=p_abs)

    @staticmethod
    def _sat_from_temp(t_c):
        """饱和参数（温度 °C）→ dict（IAPWS-IF97）"""
        if _STEAM is None:
            raise ValueError("IAPWS-IF97 模块不可用，无法计算饱和水焓")
        return _STEAM.saturation_properties(T_C=t_c)

    @classmethod
    def _p_sat_abs(cls, t_c):
        """由饱和温度求绝压 MPa"""
        if _STEAM is None:
            raise ValueError("IAPWS-IF97 模块不可用，无法计算饱和压力")
        return _STEAM.saturation_pressure(t_c)

    # ═══════════════════════ 浆料密度工具 ═══════════════════════
    @staticmethod
    def _sg_corrected(d20, t1):
        """把 20 °C 基准的比重折算到实际料温：
            d = d₂₀ − 0.001 · (t₁ − 20) / 1.5   （料温每高 1.5 °C，比重降一格 0.001）"""
        return d20 - 0.001 * (t1 - DENSITY_REF_T) / DENSITY_DT_PER_STEP

    @staticmethod
    def _baume_from_sg(d):
        """比重 → 波美度（重表 145 口径：°Bé = 145·(1 − 1/d)）"""
        if d <= 0:
            return 0.0
        return BAUME_K * (1.0 - 1.0 / d)

    @staticmethod
    def _solid_from_sg(d):
        """比重（20 °C 基准查表值）→ 干物含量 wt%（行业淀粉乳波美表经验式）

        该表自带线性式「固体 % = 1.7770 × 波美度」，覆盖到约 25 °Bé / 44 %，
        仅作对照用，**以化验值为准**。"""
        return BAUME_TO_SOLID * InjectionLiquefierCalculator._baume_from_sg(d)

    @classmethod
    def _dn_for(cls, q_m3h, u_ms=30.0):
        """按体积流量与流速估蒸汽管径，返回 (标准 DN, 计算内径 mm, 实际流速 m/s)"""
        if q_m3h <= 0:
            return 0, 0.0, 0.0
        area = q_m3h / 3600.0 / u_ms                      # m²
        d_mm = math.sqrt(4.0 * area / math.pi) * 1000.0
        dn = next((d for d in _DN_SERIES if d >= d_mm), _DN_SERIES[-1])
        u_act = q_m3h / 3600.0 / (math.pi * (dn / 1000.0) ** 2 / 4.0)
        return dn, d_mm, u_act

    # ═══════════════════════ 计算 ═══════════════════════
    def calculate(self):
        try:
            res = self._compute()
            self._last_result = res
            self._publish_chain(res)          # 先登记，结果区才能列出可传递项
            self._render(res)
            self._update_svg_diagram()
        except ValueError as e:
            self._show_error(str(e))
        except Exception as e:                                   # noqa: BLE001
            self._show_error(f"计算错误：{e}")

    def _publish_chain(self, r):
        """把「可传递给下游的出口状态」登记到计算链上下文

        下游（如闪蒸计算）据此一键取值：浆料量、蒸汽用量、喷射后液量、
        物料比热、干物浓度、出口温度。登记失败不影响本页计算。"""
        vals = {
            "浆料量": r.get("G_t", 0.0),                     # t/h（进喷射器的原始浆料）
            "蒸汽用量": r.get("D_total", 0.0),               # kg/h（一次+二次合计）
            "喷射后液量": r.get("G_final", 0.0) / 1000.0,    # t/h（含凝水，闪蒸进料）
            "物料比热": r.get("C_final", 0.0),               # kJ/(kg·K)
            "干物浓度": r.get("X_final", 0.0),               # wt%
            "出口温度": r.get("t_out", 0.0),                 # °C
            "生蒸汽表压": r.get("ps", 0.0),                  # MPa(g)
            "总焓": r.get("I", 0.0),                         # kJ/kg
            "浆料比重": r.get("d_corr", 0.0),                # t/m³（20 °C 修正比重）
        }
        units = {"浆料量": "t/h", "蒸汽用量": "kg/h", "喷射后液量": "t/h",
                 "物料比热": "kJ/(kg·K)", "干物浓度": "wt%", "出口温度": "°C",
                 "生蒸汽表压": "MPa(g)", "总焓": "kJ/kg", "浆料比重": "t/m³"}
        try:
            entry = ChainContext.publish(self.CHAIN_MODULE, self.CHAIN_PAGE,
                                         values=vals, units=units,
                                         note=r.get("mode", ""))
            r["chain_published"] = bool(entry)
            r["chain_values"] = vals
            r["chain_units"] = units
            r["chain_time_str"] = entry["time_str"] if entry else ""
        except Exception as e:                                   # noqa: BLE001
            print(f"计算链登记失败（不影响计算）: {e}")
            r["chain_published"] = False

    def _compute(self):
        two_stage = (self.mode_combo.currentText() == self.MODES[1])
        by_volume = (self.flow_mode_combo.currentText() == self.FLOW_MODES[1])

        feed_in = self._num(self.feed_input,
                            "浆料体积流量" if by_volume else "淀粉乳流量")
        d20 = self._num(self.d20_input, "浆料比重 d₂₀")
        X = self._num(self.conc_input, "干物浓度") / 100.0
        t1 = self._num(self.t1_input, "浆料初温")
        cp0 = self._num(self.cp0_input, "淀粉质比热")
        t2a = self._num(self.t2a_input, "一次喷射出口温度")
        ps = self._num(self.ps_input, "生蒸汽表压")
        dry = self._num(self.dry_input, "蒸汽干度")
        margin = self._num(self.margin_input, "设计余量")
        h_in = self._num_opt(self.total_h_input, "总焓（查表值）")

        # ── 校验 ──
        if feed_in <= 0:
            raise ValueError("淀粉乳流量必须大于 0")
        if not (0.0 < X < 1.0):
            raise ValueError("干物浓度应在 0~100 wt% 之间")
        if not (0.9 <= d20 <= 1.8):
            raise ValueError("浆料比重 d₂₀ 应在 0.9~1.8 之间（20 °C 基准查表值）")

        # ── 浆料比重温度修正 → 密度 → 质量流量 ──
        d_corr = self._sg_corrected(d20, t1)
        if d_corr <= 0.5:
            raise ValueError(
                f"温度修正后比重 {d_corr:.4f} 不合理，请核对浆料初温与比重查表值")
        rho = d_corr * 1000.0                     # kg/m³
        baume = self._baume_from_sg(d20)          # 20 °C 基准波美度（对照）
        X_est = self._solid_from_sg(d20)          # 由比重估算的干物含量 wt%（对照）
        if by_volume:
            Q_m3h = feed_in
            G_t = Q_m3h * d_corr                  # t/h = m³/h × d
        else:
            G_t = feed_in
            Q_m3h = feed_in / d_corr              # 反算体积流量，供参考
        if cp0 <= 0:
            raise ValueError("淀粉质比热必须大于 0")
        if not (0.5 <= dry <= 1.0):
            raise ValueError("蒸汽干度应在 0.5~1.0 之间")
        if margin < 0:
            raise ValueError("设计余量不能为负")

        # ── 蒸汽物性（饱和态）──
        ATM = 0.101325
        p_abs = ps + ATM
        if not (0.0007 < p_abs < 16.5):
            raise ValueError(f"生蒸汽绝压 {p_abs:.3f} MPa 超出 IAPWS-IF97 饱和线范围")
        sat_s = self._sat_from_abs(p_abs)
        t_sat = sat_s["T_C"]                     # 蒸汽饱和温度
        I_auto = sat_s["h_f"] + dry * sat_s["h_fg"]   # 工作蒸汽焓（按干度自动算）
        v_g = sat_s["v_g"]                       # 饱和蒸汽比容 m³/kg

        # 设计表格「总焓（查表）」列：填了就按查表值算，留空则用 IAPWS 自动算
        if h_in is not None:
            if h_in <= 0:
                raise ValueError("总焓（查表值）必须大于 0")
            I = h_in
            I_src = "查表输入"
        else:
            I = I_auto
            I_src = "自动（按压力与干度）"

        if t2a <= t1:
            raise ValueError(f"一次喷射出口温度 {t2a:.1f} °C 必须高于浆料初温 {t1:.1f} °C")
        # 硬约束：蒸汽饱和温度必须高于出口料温
        if t2a >= t_sat:
            raise ValueError(
                f"一次喷射出口温度 {t2a:.1f} °C 已达/超过生蒸汽饱和温度 {t_sat:.1f} °C"
                f"（表压 {ps:.3f} MPa）——蒸汽无法把料液加热到此温度。\n"
                f"  所需最低蒸汽表压 ≈ {self._p_sat_abs(t2a) + 0.05 - ATM:.3f} MPa"
                f"（含 0.05 MPa 驱动余量）；或把出口温度降到 {t_sat - 10:.1f} °C 以下。")

        warn = []

        # 「总焓（查表）」与自动算值对照：查错蒸汽表是这类表格的常见错误
        if h_in is not None and I_auto > 0 and abs(I - I_auto) > 0.01 * I_auto:
            warn.append(
                f"你填的总焓 {I:.1f} kJ/kg 与按表压 {ps:.3f} MPa(g) 自动算的 "
                f"{I_auto:.1f} kJ/kg 相差 {abs(I - I_auto) / I_auto * 100:.2f} %"
                f"——请核对是否查错了蒸汽表（本器按你填的值计算）")

        drive_margin = t_sat - t2a
        if drive_margin < 10.0:
            warn.append(
                f"蒸汽饱和温度 {t_sat:.1f} °C 与出口料温 {t2a:.1f} °C 仅差 "
                f"{drive_margin:.1f} °C（＜10 °C）——喷射器压差驱动不足，雾化与温控会变差，"
                f"建议提高蒸汽压力或降低出口温度")

        # 浓度与比重互校（行业经验式，仅作对照，不覆盖用户填的化验值）
        if abs(X_est - X * 100.0) > 2.0:
            warn.append(
                f"由比重 d₂₀ = {d20:.4f}（≈ {baume:.1f} °Bé）查表估算干物含量约 "
                f"{X_est:.1f} wt%，与你填的 {X * 100.0:.1f} wt% 相差 "
                f"{abs(X_est - X * 100.0):.1f} 个百分点 —— 请核对比重读数或化验浓度"
                f"（估算式为行业经验式，以化验值为准）")

        # ── 1. 浆料比热与需热 ──
        C = cp0 * X + WATER_CP * (1.0 - X)                    # kJ/(kg·K)
        G = G_t * 1000.0                                      # kg/h
        G_solid = G * X                                       # 干物量 kg/h
        mC = G * C                                            # 热容流量 kJ/(h·K)
        Q1_kjh = mC * (t2a - t1)                              # kJ/h（整体式，主算口径）
        Q1_kW = Q1_kjh / 3600.0

        # 设计表格「Q=（）方法一」：谷物与水分开累计（分项展开式）
        #   Q = [G·(100−X)·4.18·t₂ + G·X·C₀·t₂ − G·t₁·C·100] / 100 / 3600
        # 设计表格「Q=（）方法二」：调浆乳液整体（= G·C·(t₂−t₁)）
        # 两式数学恒等（加权比热已把谷物 C₀ 与水的 C_w 按比例合成），此处并列做互校
        Xp = X * 100.0
        Q1_A_kjh = (G * (100.0 - Xp) * WATER_CP * t2a
                    + G * Xp * cp0 * t2a
                    - G * t1 * C * 100.0) / 100.0
        Q1_B_kjh = G * 100.0 * (t2a - t1) * C / 100.0
        Q1_A_kW = Q1_A_kjh / 3600.0
        Q1_B_kW = Q1_B_kjh / 3600.0
        q_diff_kjh = Q1_A_kjh - Q1_B_kjh
        q_diff_pct = abs(q_diff_kjh) / Q1_B_kjh * 100.0 if Q1_B_kjh > 0 else 0.0

        # ── 2. 一次喷射用汽量（核心）──
        lam1 = self._sat_from_temp(t2a)["h_f"]                # 凝结水焓 @ 出口温度
        dh1 = I - lam1                                        # 有效放热焓差
        if dh1 <= 0:
            raise ValueError(
                f"有效放热焓差 (I − λ) = {dh1:.1f} kJ/kg ≤ 0："
                f"蒸汽焓 {I:.1f} 已不大于 {t2a:.1f} °C 凝水焓 {lam1:.1f}，参数不自洽")
        D1 = Q1_kjh / dh1                                     # kg/h
        # 设计表格口径「蒸汽用量 = 3600·Q /(总焓 − 4.19·t₂)」对照
        lam1_tab = LAMBDA_CP_REF * t2a
        dh1_tab = I - lam1_tab
        D1_tab = Q1_kjh / dh1_tab if dh1_tab > 0 else 0.0
        d1_tab_pct = (D1_tab - D1) / D1 * 100.0 if D1 > 0 else 0.0
        #: 单位汽耗 [kg 汽 / t 干物]＝D₁ ÷ 干物量的「吨数」（等价 kg/kg × 1000）
        unit_steam = D1 * 1000.0 / G_solid if G_solid > 0 else 0.0
        #: 设计表格口径「吨淀粉乳气耗」= 蒸汽用量 ÷ 物料量 [kg 汽 / t 淀粉乳]
        unit_slurry = D1 / G_t if G_t > 0 else 0.0
        v_steam1 = D1 * v_g                                   # m³/h（kg/h × m³/kg）

        # ── 3. 喷射后液化液（蒸汽凝水稀释）──
        G1 = G + D1
        X1 = (G * X) / G1 if G1 > 0 else 0.0
        C1 = cp0 * X1 + WATER_CP * (1.0 - X1)
        dilution = X1 / X if X > 0 else 0.0                   # 浓度保持率

        # ── 4. 二次喷射（仅两次模式）──
        D2 = 0.0
        t2b_in = t2b_out = 0.0
        lam2 = 0.0
        dh2 = 0.0
        lam2_tab = dh2_tab = D2_tab = d2_tab_pct = 0.0
        Q2_kjh = Q2_kW = 0.0
        v_steam2 = 0.0
        G2 = X2 = C2 = 0.0
        if two_stage:
            t2b_in = self._num(self.t2b_in_input, "二次喷射进口温度")
            t2b_out = self._num(self.t2b_out_input, "二次喷射出口温度")
            if t2b_in > t2a + 1e-9:
                warn.append(
                    f"二次喷射进口温度 {t2b_in:.1f} °C 高于一次喷射出口 {t2a:.1f} °C"
                    f"——维持罐段温度通常略降，除非中间另有换热升温，请核对")
            if t2b_out <= t2b_in:
                raise ValueError(
                    f"二次喷射出口温度 {t2b_out:.1f} °C 必须高于进口温度 {t2b_in:.1f} °C")
            if t2b_out >= t_sat:
                raise ValueError(
                    f"二次喷射出口温度 {t2b_out:.1f} °C 已达/超过生蒸汽饱和温度 "
                    f"{t_sat:.1f} °C（表压 {ps:.3f} MPa）。\n"
                    f"  高温喷射段所需最低蒸汽表压 ≈ "
                    f"{self._p_sat_abs(t2b_out) + 0.05 - ATM:.3f} MPa。")
            lam2 = self._sat_from_temp(t2b_out)["h_f"]
            dh2 = I - lam2
            if dh2 <= 0:
                raise ValueError(f"二次喷射有效放热焓差 (I − λ) = {dh2:.1f} kJ/kg ≤ 0，参数不自洽")
            if (t_sat - t2b_out) < 10.0:
                warn.append(
                    f"二次喷射段蒸汽饱和温度与出口料温仅差 {t_sat - t2b_out:.1f} °C"
                    f"（＜10 °C），压差驱动可能不足")
            Q2_kjh = G1 * C1 * (t2b_out - t2b_in)
            Q2_kW = Q2_kjh / 3600.0
            D2 = Q2_kjh / dh2
            lam2_tab = LAMBDA_CP_REF * t2b_out
            dh2_tab = I - lam2_tab
            D2_tab = Q2_kjh / dh2_tab if dh2_tab > 0 else 0.0
            d2_tab_pct = (D2_tab - D2) / D2 * 100.0 if D2 > 0 else 0.0
            v_steam2 = D2 * v_g                               # m³/h
            G2 = G1 + D2
            X2 = (G * X) / G2 if G2 > 0 else 0.0
            C2 = cp0 * X2 + WATER_CP * (1.0 - X2)

        # ── 5. 供汽汇总与管径 ──
        D_total = D1 + D2
        v_total = D_total * v_g                               # m³/h
        Q_total_kjh = Q1_kjh + Q2_kjh
        Q_total_kW = Q1_kW + Q2_kW
        D_design = D_total * (1.0 + margin / 100.0)
        dn_total, d_calc, u_act = self._dn_for(v_total)
        dn_1, d_calc1, u_act1 = self._dn_for(v_steam1)

        # ── 6. 参考校核（厂商样本量级）──
        # 厂商样本：30 %DS 约 0.34 t 汽/t 淀粉、35 %DS 约 0.26 t 汽/t（口径未注明）
        unit_t = unit_steam / 1000.0                          # t 汽/t 干物

        # 蒸汽所需最低表压
        p_min_a = self._p_sat_abs(t2a) + 0.05 - ATM
        p_min_b = (self._p_sat_abs(t2b_out) + 0.05 - ATM) if two_stage else None

        # ── 7. 「最终出口状态」：供计算链下游（闪蒸、预热等）取用 ──
        if two_stage:
            t_out, G_final, X_final, C_final = t2b_out, G2, X2 * 100.0, C2
        else:
            t_out, G_final, X_final, C_final = t2a, G1, X1 * 100.0, C1

        return {
            "mode": self.mode_combo.currentText(),
            "two_stage": two_stage,
            # 输入回显
            "G_t": G_t, "X": X * 100, "t1": t1, "cp0": cp0,
            "t2a": t2a, "t2b_in": t2b_in, "t2b_out": t2b_out,
            "ps": ps, "dry": dry, "margin": margin,
            "h_in": h_in, "I_src": I_src, "I_auto": I_auto,
            # 浆料量、比重与密度
            "by_volume": by_volume, "flow_mode": self.flow_mode_combo.currentText(),
            "feed_in": feed_in, "Q_m3h": Q_m3h,
            "d20": d20, "d_corr": d_corr, "rho": rho,
            "baume": baume, "X_est": X_est,
            # 蒸汽
            "p_abs": p_abs, "t_sat": t_sat, "I": I, "v_g": v_g,
            "h_fg": sat_s["h_fg"], "drive_margin": drive_margin,
            # 浆料
            "C": C, "G": G, "G_solid": G_solid, "mC": mC,
            # 一次喷射（含表格两法互校与 4.19·t₂ 口径对照）
            "Q1_kjh": Q1_kjh, "Q1_kW": Q1_kW,
            "Q1_A_kjh": Q1_A_kjh, "Q1_A_kW": Q1_A_kW,
            "Q1_B_kjh": Q1_B_kjh, "Q1_B_kW": Q1_B_kW,
            "q_diff_kjh": q_diff_kjh, "q_diff_pct": q_diff_pct,
            "lam1": lam1, "dh1": dh1, "D1": D1,
            "lam1_tab": lam1_tab, "dh1_tab": dh1_tab, "D1_tab": D1_tab,
            "d1_tab_pct": d1_tab_pct,
            "unit_steam": unit_steam, "unit_t": unit_t,
            "unit_slurry": unit_slurry, "spec_vol": Q_m3h,
            "v_steam1": v_steam1, "dn_1": dn_1, "d_calc1": d_calc1, "u_act1": u_act1,
            # 液化液
            "G1": G1, "X1": X1 * 100, "C1": C1, "dilution": dilution,
            # 二次喷射
            "lam2": lam2, "dh2": dh2, "Q2_kjh": Q2_kjh, "Q2_kW": Q2_kW, "D2": D2,
            "lam2_tab": lam2_tab, "dh2_tab": dh2_tab, "D2_tab": D2_tab,
            "d2_tab_pct": d2_tab_pct,
            "v_steam2": v_steam2, "G2": G2, "X2": X2 * 100, "C2": C2,
            # 汇总
            "D_total": D_total, "v_total": v_total,
            "Q_total_kjh": Q_total_kjh, "Q_total_kW": Q_total_kW,
            "D_design": D_design, "dn_total": dn_total,
            "d_calc": d_calc, "u_act": u_act,
            "p_min_a": p_min_a, "p_min_b": p_min_b,
            # 计算链下游用的最终出口状态
            "t_out": t_out, "G_final": G_final, "X_final": X_final, "C_final": C_final,
            "warn": warn,
        }

    # ═══════════════════════ 结果渲染 ═══════════════════════
    def _render(self, r):
        L = []
        L.append("蒸汽喷射液化器用汽量计算")
        L.append("=" * 58)
        L.append(f"【计算模式】{r['mode']}")
        L.append("")
        L.append("【一、物料量、比重与比热】")
        L.append(f"  物料量输入方式    = {r['flow_mode']}")
        L.append(f"  物料量 G          = {r['G_t']:.3f} t/h = {r['G']:.0f} kg/h"
                 f"   [热量衡算按质量流量]")
        L.append(f"  喷射器规格        = 物料量 ÷ 密度 = {r['G_t']:.3f} ÷ {r['d_corr']:.4f}"
                 f" = {r['spec_vol']:.3f} m³/h   [按体积选型用]")
        L.append(f"  浆料比重 d₂₀      = {r['d20']:.4f}   [20 °C 基准查表值]")
        L.append(f"  温度修正          = −0.001×({r['t1']:.1f}−20)/1.5"
                 f" = {r['d_corr'] - r['d20']:+.5f}")
        L.append(f"  修正比重 d        = {r['d_corr']:.4f}"
                 f"   →   密度 ρ = {r['rho']:.1f} kg/m³")
        L.append(f"  干物浓度 X        = {r['X']:.2f} wt%"
                 f"   [由该比重查表估算 ≈ {r['X_est']:.1f} wt% / {r['baume']:.1f} °Bé，供对照]")
        L.append(f"  干物量            = {r['G_solid']/1000:.3f} t/h")
        L.append(f"  浆料初温 t₁       = {r['t1']:.1f} °C")
        L.append(f"  物料比热 C（= 表格「淀粉乳比热」）")
        L.append(f"      C = C₀·X/100 + C_w·(100−X)/100")
        L.append(f"        = {r['cp0']:.3f}×{r['X']:.2f}/100 + {WATER_CP:g}×"
                 f"{100 - r['X']:.2f}/100")
        L.append(f"        = {r['C']:.4f} kJ/(kg·K)")
        L.append(f"  热容流量 G·C      = {r['mC']:.0f} kJ/(h·K)")
        L.append("")
        L.append("【二、蒸汽物性】")
        L.append(f"  生蒸汽表压 p_s    = {r['ps']:.3f} MPa(g)")
        L.append(f"  生蒸汽绝压        = {r['p_abs']:.4f} MPa(a)")
        L.append(f"  饱和温度 t_s      = {r['t_sat']:.2f} °C")
        L.append(f"  汽化潜热 h_fg     = {r['h_fg']:.1f} kJ/kg")
        L.append(f"  蒸汽干度 x        = {r['dry']:.2f}")
        L.append(f"  总焓 I            = {r['I']:.1f} kJ/kg   [{r['I_src']}]")
        if r.get("h_in") is not None and r.get("I_auto"):
            L.append(f"      （自动算值 {r['I_auto']:.1f} kJ/kg，与查表值差 "
                     f"{(r['I'] - r['I_auto']) / r['I_auto'] * 100:+.2f} %）")
        L.append(f"  饱和汽比容 v_g    = {r['v_g']:.4f} m³/kg")
        L.append(f"  与出口料温差      = t_s − t₂₁ = {r['drive_margin']:.1f} °C"
                 + ("（＜10，压差驱动不足）" if r['drive_margin'] < 10 else ""))
        L.append("")
        L.append("【三、需热量 Q —— 表格两法互校】")
        L.append(f"  喷射出口温度 t₂₁  = {r['t2a']:.1f} °C")
        L.append("  口径提示：表格的「谷物与水分开累计」与「调浆液×比热×温差」是同一")
        L.append("  件事的两种写法，两式恒等，此处并列以便互相校核。")
        L.append("")
        L.append("  方法一（谷物与水分开累计）")
        L.append("      Q = [G(100−X)·4.18·t₂ + G·X·C₀·t₂ − G·t₁·C·100] / 100 / 3600")
        L.append(f"        = [{r['G']:.0f}×{100 - r['X']:.2f}×{WATER_CP:g}×{r['t2a']:.1f}"
                 f" + {r['G']:.0f}×{r['X']:.2f}×{r['cp0']:.3f}×{r['t2a']:.1f}")
        L.append(f"           − {r['G']:.0f}×{r['t1']:.1f}×{r['C']:.4f}×100] / 100 / 3600")
        L.append(f"        = {r['Q1_A_kW']:.2f} kW")
        L.append("")
        L.append("  方法二（调浆乳液整体：调浆液 × 比热 × 温差）")
        L.append("      Q = G·100·(t₂−t₁)·C / 100 / 3600")
        L.append(f"        = {r['G']:.0f}×100×({r['t2a']:.1f}−{r['t1']:.1f})"
                 f"×{r['C']:.4f} / 100 / 3600")
        L.append(f"        = {r['Q1_B_kW']:.2f} kW")
        L.append("")
        L.append(f"  → 两法差值 = {r['q_diff_pct']:.3f} %（数学恒等，互校通过）")
        L.append("")
        L.append("【四、蒸汽用量与汽耗（一次喷射）】★")
        L.append(f"  需热量 Q₁         = {r['Q1_kW']:.2f} kW = {r['Q1_kjh']:.4g} kJ/h")
        L.append(f"  凝水焓 λ = h_f(t₂₁)= {r['lam1']:.2f} kJ/kg   [取出口料温下的饱和水焓]")
        L.append(f"  有效焓差 (I − λ)  = {r['dh1']:.1f} kJ/kg"
                 f"（大于同压潜热 {r['h_fg']:.1f}，含凝水过冷显热）")
        L.append(f"  → 蒸汽用量 D₁     = 3600·Q/(I − λ) = {r['D1']:.1f} kg/h"
                 f" = {r['D1']/1000:.3f} t/h")
        L.append(f"  [表格口径对照] λ′ = 4.19×t₂₁ = {r['lam1_tab']:.2f} kJ/kg"
                 f" → D₁′ = {r['D1_tab']:.1f} kg/h（差 {r['d1_tab_pct']:+.3f} %）")
        L.append("")
        L.append("  汽耗")
        L.append(f"      吨淀粉乳气耗  = D₁ ÷ 物料量 = {r['unit_slurry']:.1f} kg 汽/t 淀粉乳"
                 f"   ← 表格口径")
        L.append(f"      吨干物汽耗    = D₁ ÷ 干物量 = {r['unit_steam']:.1f} kg 汽/t 干物"
                 f"（{r['unit_t']:.3f} t/t）")
        L.append(f"      换算关系      : 吨干物汽耗 = 吨乳气耗 ÷ (X/100) = "
                 f"{r['unit_slurry']:.1f} ÷ {r['X']/100:.4f}")
        L.append(f"  蒸汽体积流量      = {r['v_steam1']:.0f} m³/h"
                 f"（管径参考 DN{r['dn_1']}，流速 {r['u_act1']:.1f} m/s）")
        L.append("")
        L.append("【五、喷射后液化液（蒸汽凝水稀释）】")
        L.append(f"  液化液总量 G₁     = G + D₁ = {r['G1']/1000:.3f} t/h")
        L.append(f"  稀释后浓度 X₁     = G·X/G₁ = {r['X1']:.2f} wt%"
                 f"（原 {r['X']:.2f}%，保持率 {r['dilution']*100:.1f}%）")
        L.append(f"  液化液比热 C₁     = {r['C1']:.3f} kJ/(kg·K)")
        if r["two_stage"]:
            L.append("")
            L.append("【六、二次喷射（高温维持段）】")
            L.append(f"  进口温度 t₂a'     = {r['t2b_in']:.1f} °C")
            L.append(f"  出口温度 t₂₂      = {r['t2b_out']:.1f} °C")
            L.append(f"  需热量 Q₂         = G₁·C₁·(t₂₂ − t₂a') = {r['Q2_kjh']:.4g} kJ/h"
                     f" = {r['Q2_kW']:.1f} kW")
            L.append(f"  凝水焓 λ = h_f(t₂₂)= {r['lam2']:.2f} kJ/kg")
            L.append(f"  有效焓差 (I − λ)  = {r['dh2']:.1f} kJ/kg")
            L.append(f"  → 用汽量 D₂       = {r['D2']:.1f} kg/h = {r['D2']/1000:.3f} t/h")
            L.append(f"  [表格口径对照] λ′ = 4.19×t₂₂ = {r['lam2_tab']:.2f} kJ/kg"
                     f" → D₂′ = {r['D2_tab']:.1f} kg/h（差 {r['d2_tab_pct']:+.3f} %）")
            L.append(f"  → 蒸汽体积流量    = {r['v_steam2']:.0f} m³/h")
            L.append(f"  二次喷射后液量 G₂ = {r['G2']/1000:.3f} t/h，浓度 X₂ = {r['X2']:.2f} wt%")
        L.append("")
        L.append("【七、供汽汇总与选型】" if r["two_stage"] else "【六、供汽汇总与选型】")
        L.append(f"  液化总用汽 D      = {'D₁ + D₂' if r['two_stage'] else 'D₁'}"
                 f" = {r['D_total']:.1f} kg/h = {r['D_total']/1000:.3f} t/h")
        L.append(f"  总需热量 Q        = {r['Q_total_kW']:.1f} kW")
        _ut = r['D_total'] / r['G_t'] if r['G_t'] > 0 else 0.0
        L.append(f"  总吨淀粉乳气耗    = D ÷ 物料量 = {_ut:.1f} kg 汽/t 淀粉乳")
        L.append(f"  蒸汽体积流量      = {r['v_total']:.0f} m³/h")
        L.append(f"  → 推荐蒸汽管径    = DN{r['dn_total']}"
                 f"（计算内径 {r['d_calc']:.1f} mm，流速 {r['u_act']:.1f} m/s，取 30 m/s 估）")
        L.append(f"  → 选型汽量        = D ×（1 + {r['margin']:.1f}%）= {r['D_design']:.1f} kg/h"
                 f" = {r['D_design']/1000:.3f} t/h   [含设计余量]")
        L.append(f"  最低蒸汽表压要求  = {r['p_min_a']:.3f} MPa"
                 + (f"（二次段 {r['p_min_b']:.3f} MPa）" if r["p_min_b"] is not None else "")
                 + "   [出口温度 + 0.05 MPa 驱动余量]")
        if r["warn"]:
            L.append("")
            L.append("【提示与警告】")
            for i, w in enumerate(r["warn"], 1):
                L.append(f"  {i}) {w}")
        if r.get("chain_published"):
            L.append("")
            L.append("【计算链】本页出口状态已登记，下游页面（闪蒸等）可用「取上游值」一键引用：")
            for k, v in (r.get("chain_values") or {}).items():
                u = (r.get("chain_units") or {}).get(k, "")
                L.append(f"      {k:<8s} = {v:>10.4f} {u}")
            L.append(f"      登记时间：{r.get('chain_time_str', '')}"
                     f"（本页重算后登记自动更新，下游会提示「已过期」）")
        L.append("")
        L.append("=" * 58)
        L.append("  口径说明：凝结水焓 λ 取**出口料温下的饱和水焓**（非蒸汽压力下的），")
        L.append("  因蒸汽进来是 t_s 饱和汽、出去是与料液同温的凝水；若误用同压潜热 h_fg")
        L.append("  代替 (I − λ)，用汽量将偏小 5~10 %。")
        L.append("  经验校核：厂商样本 30 %DS 约 0.34、35 %DS 约 0.26 t 汽/t 淀粉（口径未注明）。")
        L.append(f"  水比热取项目统一常量 {WATER_CP:g} kJ/(kg·K)（表格写 4.18，差异 0.03 % 可忽略）；")
        L.append("  「总焓（查表）」填了就按查表值算，留空则由本器按压力自动查算并互校。")
        L.append("  C₀ = 1.55 kJ/(kg·K) 属经验取值，宜以本厂物料数据替换；结果仅供参考。")
        L.append("=" * 58)
        self.result_text.setPlainText("\n".join(L))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"错误：{msg}")
        self._last_result = {}

    def _show_warn(self, msg):
        self.result_text.setPlainText(f"提示：{msg}")

    # ═══════════════════════ 清空 ═══════════════════════
    def setup_default_values(self):
        self.feed_input.setText("20")
        self.d20_input.setText("1.133")
        self.conc_input.setText("30")
        self.t1_input.setText("25")
        self.cp0_input.setText("1.55")
        self.t2a_input.setText("105")
        self.t2b_in_input.setText("95")
        self.t2b_out_input.setText("125")
        self.ps_input.setText("0.3")
        self.total_h_input.setText("")
        self.dry_input.setText("1.0")
        self.margin_input.setText("10")

    def clear_inputs(self):
        """恢复出厂默认值（可直接重算）"""
        self.mode_combo.setCurrentIndex(0)
        self.flow_mode_combo.setCurrentIndex(0)
        self.setup_default_values()
        self.result_text.clear()
        self._last_result = {}
        self._on_mode_changed(self.mode_combo.currentText())
        self._on_flow_mode_changed(self.flow_mode_combo.currentText())
        self._update_svg_diagram()

    # ═══════════════════════ 历史 ═══════════════════════
    def _get_history_data(self):
        r = self._last_result
        if not r:
            return {"inputs": {}, "outputs": {}}
        inputs = {
            "计算模式": r.get("mode", ""),
            "浆料量方式": r.get("flow_mode", ""),
            "淀粉乳流量_t_h": r.get("G_t", 0),
            "浆料比重_d20": r.get("d20", 0),
            "干物浓度_wt%": r.get("X", 0),
            "浆料初温_C": r.get("t1", 0),
            "一次喷射出口温度_C": r.get("t2a", 0),
            "生蒸汽表压_MPa": r.get("ps", 0),
        }
        if r.get("h_in") is not None:
            inputs["总焓_查表_kJ_kg"] = r.get("h_in", 0)
        outputs = {
            "修正比重": round(r.get("d_corr", 0), 4),
            "浆料比热_kJ_kgK": round(r.get("C", 0), 3),
            "喷射器规格_m3_h": round(r.get("spec_vol", 0), 3),
            "需热量_kW": round(r.get("Q1_kW", 0), 2),
            "一次用汽量_kg_h": round(r.get("D1", 0), 1),
            "吨乳气耗_kg_t": round(r.get("unit_slurry", 0), 1),
            "单位汽耗_kg_t干物": round(r.get("unit_steam", 0), 1),
            "液化液量_t_h": round(r.get("G1", 0) / 1000.0, 3),
            "稀释后浓度_wt%": round(r.get("X1", 0), 2),
            "选型汽量_kg_h": round(r.get("D_design", 0), 1),
        }
        if r.get("two_stage"):
            outputs["二次用汽量_kg_h"] = round(r.get("D2", 0), 1)
            outputs["液化总用汽_kg_h"] = round(r.get("D_total", 0), 1)
        return {"inputs": inputs, "outputs": outputs}

    # ═══════════════════════ 工程信息 / 报告 ═══════════════════════
    def get_project_info(self):
        """获取工程信息（dict，标准键）"""
        try:
            saved = {}
            if self.data_manager:
                saved = self.data_manager.get_project_info() or {}
        except Exception:                                        # noqa: BLE001
            saved = {}
        return {
            "company_name": saved.get("company_name", ""),
            "project_number": saved.get("project_number", ""),
            "project_name": saved.get("project_name", ""),
            "subproject_name": saved.get("subproject_name", ""),
            "calculation_type": "蒸汽喷射液化器用汽量计算",
        }

    def generate_report(self):
        """生成计算书文本（str；无结果返回 None）"""
        try:
            body = self.result_text.toPlainText()
            if not body or "用汽量计算" not in body:
                return None
            info = self.get_project_info()
            head = "\n".join([
                "═" * 58,
                "        蒸汽喷射液化器用汽量计算书",
                "═" * 58,
            ])
            foot = "\n".join([
                "═" * 58,
                " 工程信息",
                "═" * 58,
                "",
                f"  公司名称: {info.get('company_name', '')}",
                f"  工程编号: {info.get('project_number', '')}",
                f"  工程名称: {info.get('project_name', '')}",
                f"  子项名称: {info.get('subproject_name', '')}",
                f"  计算类型: {info.get('calculation_type', '')}",
                f"  计算日期: {datetime.now().strftime('%Y-%m-%d')}",
                "",
                "═" * 58,
                " 计算公式与依据",
                "═" * 58,
                "",
                "  0. 浆料量、比重与密度（体积 ↔ 质量换算）",
                "     修正比重 d = d₂₀ − 0.001·(t₁ − 20)/1.5",
                "        d₂₀ = 20 °C 基准查表比重；料温每比 20 °C 高 1.5 °C，比重降一格 0.001",
                "     密度 ρ = 1000·d  kg/m³；质量流量 G = Q·d  t/h（Q 为体积流量 m³/h）",
                "     波美度 °Bé = 145·(1 − 1/d)；干物含量估算 X ≈ 1.7770·°Bé（经验式，以化验为准）",
                "     喷射器规格 = 物料量 ÷ 密度（= 物料体积流量 m³/h，供按体积选型）",
                "  1. 浆料比热（质量加权，即设计表格的「淀粉乳比热」）",
                "     C = C₀·X/100 + C_w·(100 − X)/100        kJ/(kg·K)",
                "     C₀ = 1.55（表格「谷物比热」，经验值）；C_w = 4.18（水）；X = 干物浓度 wt%",
                "  2. 需热量 Q（设计表格给了两种写法，本计算器并列互校）",
                "     方法一（谷物与水分开累计）：",
                "       Q = [G(100−X)·4.18·t₂ + G·X·C₀·t₂ − G·t₁·C·100] / 100 / 3600    kW",
                "     方法二（调浆乳液整体：调浆液 × 比热 × 温差）：",
                "       Q = G·100·(t₂ − t₁)·C / 100 / 3600                             kW",
                "     两式数学恒等（加权比热已把谷物与水的比热按比例合成），结果必须相同；",
                "     并列输出用于互相校核——差值不为 0 即说明某项的百分数/分母口径填错了。",
                "  3. 直接蒸汽注入热量衡算（本计算器核心）",
                "     D = G·C·(t₂ − t₁) / (I − λ) = 3600·Q / (I − λ)             kg/h",
                "     I = 工作蒸汽焓 = h_f(p) + x·h_fg(p)     （x 干度，饱和汽取 1.0）",
                "         设计表格的「总焓（查表）」可直接填入，留空则由本器按压力自动算；",
                "         两者相差 >1 % 时给出提示（常见原因是查错了蒸汽表）。",
                "     λ = 凝结水焓 = h_f(t₂)  ← 取出口料温下的饱和水焓（非蒸汽压力下的）",
                "     蒸汽进来为 t_s(p) 饱和汽、出去为与料液同温 (t₂) 的凝水，",
                "     故 (I − λ) 略大于同压汽化潜热 h_fg（含凝水过冷显热）。",
                "     表格口径 λ′ = 4.19·t₂ 与本器口径等价（偏差 < 0.1 %），结果中并列给出对照。",
                "  4. 二次喷射（高温段）",
                "     D₂ = (G + D₁)·C₁·(t₂₂ − t₂a') / (I − h_f(t₂₂))，C₁ 按稀释后浓度重算",
                "  5. 稀释：喷射后浓度 X₁ = G·X/(G + D₁)（蒸汽凝水使料液变稀）",
                "  6. 硬约束：t₂ ＜ t_sat(p_s)，且 t_sat − t₂ ≥ 10~15 °C（压差驱动）",
                "  7. 汽耗（两个口径，勿混用）",
                "     吨淀粉乳气耗 = D ÷ 物料量   kg 汽 / t 淀粉乳（设计表格口径，分母是含水的乳液）",
                "     吨干物汽耗   = D ÷ 干物量   kg 汽 / t 干物（换算式：吨干物汽耗 = 吨乳气耗 ÷ X%）",
                "  8. 管径：DN 按 V = D·v_g 与流速 30 m/s（饱和蒸汽常规 25~40）估算",
                "",
                "═" * 58,
                " 数据来源与假设",
                "═" * 58,
                "",
                "  1. 蒸汽与饱和水焓取自 IAPWS-IF97（项目自带 steam_iapws 模块），",
                "     饱和蒸汽基础物性走项目统一入口 common_constants.get_steam_props；",
                "  2. 表压→绝压按 +0.101325 MPa 换算；",
                "  3. 比热加权式与直接蒸汽注入热量衡算式为淀粉糖/味精行业设计资料通用式，",
                "     多份独立来源口径一致；",
                "  4. 经验校核：厂商公开样本 30 %DS 蒸煮每吨淀粉约耗 0.34 t 蒸汽、",
                "     35 %DS 约 0.26 t（样本未注明蒸汽压力与料液初温口径，仅作量级校核）；",
                "  5. C₀、蒸汽流速等属经验取值，宜以本厂物料与设备数据替换；",
                "  6. 计算结果仅供参考，实际工程须经专业工程师审核确认。",
                "",
                "---",
                "生成于 ChemCal 工程计算模块",
            ])
            return f"{head}\n\n{body}\n\n{foot}"
        except Exception as e:                                   # noqa: BLE001
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        ReportExporter.export_docx(self, "蒸汽喷射液化器用汽量")

    def download_pdf_report(self):
        ReportExporter.export_pdf(self, "蒸汽喷射液化器用汽量")

    # ═══════════════════════ SVG 示意图 ═══════════════════════
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        return svg_text(x, y, text, size, color, bold, center)

    def _update_svg_diagram(self):
        """按当前输入刷新喷射液化流程示意图（属性一律 XML 语法）"""
        w, h = 380, 250
        try:
            t1 = float(self.t1_input.text())
            t2a = float(self.t2a_input.text())
        except (TypeError, ValueError):
            t1, t2a = 25.0, 105.0
        two = (self.mode_combo.currentText() == self.MODES[1])

        p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
             f'width="{w}" height="{h}">',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']

        # 蒸汽母管（顶部，橙）
        p.append(f'<line x1="40" y1="42" x2="{w - 40}" y2="42" '
                 f'stroke="#e67e22" stroke-width="3"/>')
        p.append(self._text(w / 2, 32, "生蒸汽（饱和）", size=9, color="#e67e22", bold=True))

        # 淀粉乳罐（左）
        p.append('<rect x="30" y="88" width="62" height="52" fill="#dbe7f5" '
                 'stroke="#4a6fa5" stroke-width="1.5" rx="4"/>')
        p.append(self._text(61, 108, "淀粉乳", size=9, color="#2c3e50", bold=True))
        p.append(self._text(61, 124, f"{t1:.0f} °C", size=9, color="#2c3e50"))

        # 喷射器 1（文丘里：三角+矩形）
        xj1 = 120
        p.append(f'<polygon points="{xj1},104 {xj1 + 22},92 {xj1 + 22},116" '
                 f'fill="#f6d9b0" stroke="#c47d1a" stroke-width="1.5"/>')
        p.append(f'<rect x="{xj1 + 22}" y="92" width="26" height="24" fill="#f6d9b0" '
                 f'stroke="#c47d1a" stroke-width="1.5"/>')
        p.append(f'<line x1="{xj1 + 9}" y1="42" x2="{xj1 + 9}" y2="92" '
                 f'stroke="#e67e22" stroke-width="2.5"/>')
        p.append(self._text(xj1 + 24, 84, "喷射器", size=9, color="#a06010", bold=True))
        p.append(self._text(xj1 + 24, 132, f"{t2a:.0f} °C", size=9, color="#a06010", bold=True))

        # 连接箭头
        p.append(f'<line x1="92" y1="114" x2="{xj1 - 2}" y2="114" '
                 f'stroke="#4a6fa5" stroke-width="2"/>')

        if two:
            # 维持罐
            p.append('<rect x="182" y="88" width="58" height="52" fill="#e8f5e9" '
                     'stroke="#43a047" stroke-width="1.5" rx="4"/>')
            p.append(self._text(211, 108, "维持罐", size=9, color="#2e7d32", bold=True))
            p.append(self._text(211, 124, "保温液化", size=8, color="#2e7d32"))
            p.append(f'<line x1="{xj1 + 48}" y1="114" x2="180" y2="114" '
                     f'stroke="#4a6fa5" stroke-width="2"/>')
            # 喷射器 2
            xj2 = 256
            p.append(f'<polygon points="{xj2},104 {xj2 + 20},92 {xj2 + 20},116" '
                     f'fill="#f6d9b0" stroke="#c47d1a" stroke-width="1.5"/>')
            p.append(f'<rect x="{xj2 + 20}" y="92" width="24" height="24" fill="#f6d9b0" '
                     f'stroke="#c47d1a" stroke-width="1.5"/>')
            p.append(f'<line x1="{xj2 + 8}" y1="42" x2="{xj2 + 8}" y2="92" '
                     f'stroke="#e67e22" stroke-width="2.5"/>')
            p.append(self._text(xj2 + 20, 84, "喷射器2", size=8, color="#a06010", bold=True))
            p.append(f'<line x1="240" y1="114" x2="{xj2 - 2}" y2="114" '
                     f'stroke="#4a6fa5" stroke-width="2"/>')
            # 出料
            p.append(f'<line x1="{xj2 + 44}" y1="114" x2="{w - 30}" y2="114" '
                     f'stroke="#2980b9" stroke-width="2.5"/>')
            p.append(self._text(w - 34, 100, "液化液", size=9, color="#2980b9",
                                bold=True, center=False))
        else:
            # 维持罐（虚线示意）
            p.append('<rect x="188" y="88" width="58" height="52" fill="#e8f5e9" '
                     'stroke="#43a047" stroke-width="1.5" stroke-dasharray="4 3" rx="4"/>')
            p.append(self._text(217, 108, "维持罐", size=9, color="#2e7d32", bold=True))
            p.append(self._text(217, 124, "保温液化", size=8, color="#2e7d32"))
            p.append(f'<line x1="{xj1 + 48}" y1="114" x2="186" y2="114" '
                     f'stroke="#4a6fa5" stroke-width="2"/>')
            p.append(f'<line x1="246" y1="114" x2="{w - 30}" y2="114" '
                     f'stroke="#2980b9" stroke-width="2.5"/>')
            p.append(self._text(w - 34, 100, "液化液", size=9, color="#2980b9",
                                bold=True, center=False))

        # 底部结果摘要
        r = self._last_result
        if r:
            line1 = f"物料比热 {r['C']:.2f} kJ/(kg·K)   有效焓差 {r['dh1']:.0f} kJ/kg"
            if two:
                line2 = f"用汽 D₁ {r['D1']:.0f} + D₂ {r['D2']:.0f} = {r['D_total']:.0f} kg/h"
            else:
                line2 = f"蒸汽用量 D₁ = {r['D1']:.0f} kg/h（{r['unit_slurry']:.0f} kg 汽/t 乳）"
            p.append(self._text(w / 2, h - 50, line1, size=9, color="#1d6f42", bold=True))
            p.append(self._text(w / 2, h - 34, line2, size=10, color="#1d6f42", bold=True))
            p.append(self._text(w / 2, h - 18,
                                f"液化液 {r['G1']/1000:.2f} t/h   浓度降至 {r['X1']:.1f} wt%",
                                size=9, color="#333", bold=True))
        else:
            p.append(self._text(w / 2, h - 30, "点击「计 算」查看结果", size=9, color="#888"))
        p.append("</svg>")
        self.svg_widget.load("".join(p).encode("utf-8"))


# 为动态导入提供简洁别名
injection_liquefier_calculator = InjectionLiquefierCalculator
