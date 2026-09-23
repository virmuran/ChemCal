"""
浓缩蒸发器计算器（单效 / 多效 / MVR / TVR）

适用：糖液、淀粉糖、发酵液、废水等溶液的浓缩蒸发工段方案计算 ——
      物料衡算 → 蒸发水量 → 热量衡算与生蒸汽耗量 → 效数与温差分配 → 各效传热面积
      → 蒸发强度校核与加热室形式建议 → MVR/TVR 节能方案能耗对比。

═══════════════ 1. 物料衡算（与溶解固形物守恒等价）═══════════════
        W = F · (1 − x0/x1)          W 蒸发水量  F 进料量  x0 进料质量分数  x1 出料质量分数
        P = F − W                    出料（浓缩液）量
        第 i 效出料浓度  x_i = F·x0 / (F − Σ_{j≤i} W_j)

═══════════════ 2. 热量衡算（并流进料，逐效解析求解）═══════════════
        W_i·λ'_i = D_i·λ_i·η_h − F_i·Cp·(t_i − t_{i−1})
            D_i 第 i 效加热蒸汽量（D_1 = 生蒸汽，i≥2 时 D_i = W_{i−1}）
            λ_i  加热蒸汽汽化潜热（在 T_{i−1} 下）；λ'_i 本效产生蒸汽的汽化潜热（在 t_i 下）
            F_i  进入第 i 效的料液量；t_0 = 进料温度
        ⇒ 对 D_1 呈线性（每个 W_i = a_i·D_1 + b_i），由 ΣW_i = W 闭式解出 D_1
        蒸汽经济性   = W / D_1  （kg 蒸发水 / kg 生蒸汽）
        单位汽耗     = D_1 / W  （t 生蒸汽 / t 蒸发水）

═══════════════ 3. 传热面积与温差分配 ═══════════════
        有效总温差   ΣΔT = T_s − t_n − (n−1)·Δ'''(效间管路/除沫/静压损失)
        分配         ΔT_i ∝ 1/K_i          K_i = K_1 · r^(i−1)（r = 逐效衰减比）
        各效面积     A_i = Q_i / (K_i · ΔT_i)     Q_i = D_i·λ_i
        设计面积     = max(A_i)（等面积法取最大者；亦给出总面积与平均值）
        蒸发强度     = W_i / A_i   kg/(m²·h)，与所选加热室形式的经验区间校核

═══════════════ 4. MVR（机械蒸汽再压缩）═══════════════
        t_v = t_b − BPE  →  p_1 = p_sat(t_v)        蒸发室二次蒸汽压力
        p_2 = p_1 · π                               压缩比 π
        h_{2s} = h(p_2, s = s_1)  —— 等熵压缩终点（IAPWS-IF97 反算）
        w_is = h_{2s} − h_1；  w_act = w_is / η_is
        P = (W/3600)·w_act                           压缩机轴功率 kW
        单位电耗 = P / (W/1000)                      kWh / t 蒸发水
        可用供热 = W·(h_{2,act} − h_f(p_2))          压缩后蒸汽冷凝放热
        需    热 = W·λ'_b + F·Cp·(t_b − T_f)         蒸发 + 进料显热
        ⇒ 差额为负时需补充生蒸汽；为正时说明余热可预热进料
        有效温差 = T_sat(p_2) − t_b（工程上宜 ≥ 5~8 °C，低于此值给出警告）

═══════════════ 5. TVR（热力蒸汽再压缩 / 蒸汽喷射热泵）═══════════════
        喷射器以生蒸汽 D 引射 u·D 的二次蒸汽，混合后作为首效加热蒸汽，总量 D(1+u)。
        等效：生蒸汽耗量降为 D/(1+u) ⇒ **蒸汽经济性提高 (1+u) 倍**（u = 引射系数，
        kg 引射蒸汽/kg 生蒸汽，单级喷射器工程常用 0.5~1.2；压比过高时引射效率迅速下降）。

═══════════════ 6. 数据来源 ═══════════════
    · 蒸汽物性：IAPWS-IF97（本程序自带模块），汽化潜热统一走 common_constants.get_steam_props
    · 蒸发强度经验区间：公开技术资料/设备样本 —— 降膜清洁 20~35、降膜易结垢 12~20、
      升膜 15~30 kg/(m²·h)；强制循环/外循环样本未给统一值，按易结垢工况 12~20 保守取值，
      宜以中试或厂商样本确认
    · 传热系数 K 经验区间：降膜 1500~3500、升膜 1500~2500、强制循环/外循环 1000~1800
      W/(m²·K)；本计算器默认值取区间中位，用户可按物料特性替换
    · 沸点升高 BPE **不做关联式推算**（不同体系差异大、随浓度剧变），由用户按物料手册/试验
      填入；高盐废水每效常见 1~4 °C。本计算器按各效取同一值计算并明确标注该简化。
    · 热损失系数 η_h 取 0.95~0.98（每效约 2~5% 热损）
"""

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

# IAPWS-IF97 完整物性（动态导入，写法与长输蒸汽管道计算器一致）
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


class EvaporatorCalculator(CalculatorBase):
    """浓缩蒸发器计算器（单效/多效/MVR/TVR）"""

    MODES = ["单效蒸发", "多效蒸发（并流）", "MVR 机械蒸汽再压缩", "TVR 热力蒸汽再压缩"]
    EFFECTS = ["2 效", "3 效", "4 效", "5 效", "6 效"]

    #: 加热室形式 → (默认 K W/(m²·K), 蒸发强度经验区间 kg/(m²·h), 说明)
    HEATER_TYPES = {
        "降膜式（清洁物料）":   (2500.0, (20.0, 35.0), "热敏、低中粘度，停留时间 5~30 s"),
        "降膜式（易结垢物料）": (1500.0, (12.0, 20.0), "易结垢时取低值，需 CIP"),
        "升膜式":               (2000.0, (15.0, 30.0), "低粘度不易结垢，浓缩比不宜 >3"),
        "强制循环/外循环":      (1200.0, (12.0, 20.0), "易结晶、易结垢、高粘度"),
    }

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_result = {}
        self.setup_ui()
        self.setup_default_values()
        self.setup_wheel_blocker()

    # ═══════════════════════ UI ═══════════════════════
    def setup_ui(self):
        main = QHBoxLayout(self)
        main.setSpacing(15)
        main.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setStyleSheet(SCROLL_AREA_STYLE)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setSpacing(10)

        desc = QLabel(
            "浓缩蒸发工段计算：物料衡算 → 各效蒸发量与浓度 → 热量衡算与生蒸汽耗量 → "
            "效数温差分配 → 各效传热面积与蒸发强度 → 加热室形式建议；"
            "并给出 单效 / 多效 / MVR / TVR 四种方案的能耗对比。")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size:12px;padding:5px;")
        ll.addWidget(desc)

        ls = INPUT_LABEL_STYLE
        self._rows = {}

        def lbl(t):
            w = QLabel(t)
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            w.setStyleSheet(ls)
            return w

        def hint(t):
            w = QLabel(t)
            w.setStyleSheet("font-style:italic;color:#666;")
            return w

        def add_row(grid, key, label, widget, hint_text, row):
            la, hi = lbl(label), hint(hint_text)
            grid.addWidget(la, row, 0)
            grid.addWidget(widget, row, 1)
            grid.addWidget(hi, row, 2)
            self._rows[key] = (la, widget, hi)

        def new_grid(box):
            g = QGridLayout(box)
            g.setHorizontalSpacing(10)
            g.setVerticalSpacing(10)
            g.setColumnStretch(0, 4)
            g.setColumnStretch(1, 8)
            g.setColumnStretch(2, 5)
            return g

        # ── 计算模式 ──
        g0 = CalculatorBase.make_group_box("计算模式")
        g0g = new_grid(g0)
        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet(COMBOBOX_STYLE)
        self.mode_combo.addItems(self.MODES)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        add_row(g0g, "mode", "计算模式:", self.mode_combo, "MVR/TVR 见右侧能耗对比", 0)
        ll.addWidget(g0)

        # ── 物料与产品 ──
        g1 = CalculatorBase.make_group_box("物料与产品")
        g1g = new_grid(g1)
        r = 0
        self.feed_input = QLineEdit("10000")
        self.feed_input.setValidator(QDoubleValidator(1.0, 1e7, 1))
        add_row(g1g, "feed", "进料量 F (kg/h):", self.feed_input, "料液处理量", r); r += 1
        self.x0_input = QLineEdit("12")
        self.x0_input.setValidator(QDoubleValidator(0.1, 80.0, 2))
        add_row(g1g, "x0", "进料浓度 x0 (wt%):", self.x0_input, "溶质质量分数", r); r += 1
        self.x1_input = QLineEdit("60")
        self.x1_input.setValidator(QDoubleValidator(0.5, 95.0, 2))
        add_row(g1g, "x1", "出料浓度 x1 (wt%):", self.x1_input, "浓缩液质量分数", r); r += 1
        self.tf_input = QLineEdit("25")
        self.tf_input.setValidator(QDoubleValidator(0.0, 200.0, 1))
        add_row(g1g, "tf", "进料温度 T_f (°C):", self.tf_input, "影响显热项与自蒸发", r); r += 1
        self.cp_input = QLineEdit("3.80")
        self.cp_input.setValidator(QDoubleValidator(0.5, 10.0, 2))
        add_row(g1g, "cp", "料液比热容 Cp (kJ/(kg·K)):", self.cp_input,
                "糖液 3.5~4.0；水 4.18", r); r += 1
        ll.addWidget(g1)

        # ── 加热与蒸发条件 ──
        g2 = CalculatorBase.make_group_box("加热与蒸发条件")
        g2g = new_grid(g2)
        r = 0
        self.ps_input = QLineEdit("0.4")
        self.ps_input.setValidator(QDoubleValidator(0.01, 4.0, 3))
        add_row(g2g, "ps", "生蒸汽表压 p_s (MPa):", self.ps_input, "表压，非绝压", r); r += 1
        self.eta_h_input = QLineEdit("0.97")
        self.eta_h_input.setValidator(QDoubleValidator(0.5, 1.0, 3))
        add_row(g2g, "eta_h", "热损失系数 η_h:", self.eta_h_input, "每效约 2~5% 热损", r); r += 1
        self.tb_input = QLineEdit("70")
        self.tb_input.setValidator(QDoubleValidator(20.0, 180.0, 1))
        add_row(g2g, "tb", "蒸发温度 t_b (°C):", self.tb_input,
                "单效/MVR 为溶液沸点；多效为**末效**沸点", r); r += 1
        self.bpe_input = QLineEdit("1.5")
        self.bpe_input.setValidator(QDoubleValidator(0.0, 20.0, 2))
        add_row(g2g, "bpe", "沸点升高 BPE (°C):", self.bpe_input,
                "须按物料查手册/试验，高盐 1~4", r); r += 1
        self.dtloss_input = QLineEdit("1.0")
        self.dtloss_input.setValidator(QDoubleValidator(0.0, 10.0, 2))
        add_row(g2g, "dtloss", "效间温差损失 Δ''' (°C/效):", self.dtloss_input,
                "管路/除沫/静压，仅多效用", r); r += 1
        self.cw_dt_input = QLineEdit("8")
        self.cw_dt_input.setValidator(QDoubleValidator(1.0, 40.0, 1))
        add_row(g2g, "cwdt", "冷凝器冷却水温升 (°C):", self.cw_dt_input,
                "估算末效冷凝水用量", r); r += 1
        ll.addWidget(g2)

        # ── 传热与选型 ──
        g3 = CalculatorBase.make_group_box("传热与加热室选型")
        g3g = new_grid(g3)
        r = 0
        self.heater_combo = QComboBox()
        self.heater_combo.setStyleSheet(COMBOBOX_STYLE)
        self.heater_combo.addItems(list(self.HEATER_TYPES.keys()))
        self.heater_combo.currentTextChanged.connect(self._on_heater_changed)
        add_row(g3g, "heater", "加热室形式:", self.heater_combo,
                "决定 K 与蒸发强度参考区间", r); r += 1

        self.effects_combo = QComboBox()
        self.effects_combo.setStyleSheet(COMBOBOX_STYLE)
        self.effects_combo.addItems(self.EFFECTS)
        self.effects_combo.setCurrentIndex(1)     # 3 效
        add_row(g3g, "effects", "效数 n:", self.effects_combo, "工程常用 3~5 效", r); r += 1

        self.k1_input = QLineEdit("2500")
        self.k1_input.setValidator(QDoubleValidator(100.0, 8000.0, 1))
        add_row(g3g, "k1", "一效传热系数 K₁ (W/(m²·K)):", self.k1_input,
                "降膜 1500~3500", r); r += 1

        self.k_decay_input = QLineEdit("0.8")
        self.k_decay_input.setValidator(QDoubleValidator(0.3, 1.0, 3))
        add_row(g3g, "kdecay", "逐效 K 衰减比 r:", self.k_decay_input,
                "K_i = K₁·r^(i−1)", r); r += 1

        self.k_single_input = QLineEdit("2000")
        self.k_single_input.setValidator(QDoubleValidator(100.0, 8000.0, 1))
        add_row(g3g, "ksingle", "传热系数 K (W/(m²·K)):", self.k_single_input,
                "单效 / MVR 用", r); r += 1

        self.safety_input = QLineEdit("1.15")
        self.safety_input.setValidator(QDoubleValidator(1.0, 3.0, 2))
        add_row(g3g, "safety", "面积裕量系数:", self.safety_input, "通常 1.1~1.2", r); r += 1
        ll.addWidget(g3)

        # ── MVR 参数 ──
        g4 = CalculatorBase.make_group_box("MVR 压缩参数")
        g4g = new_grid(g4)
        r = 0
        self.pi_input = QLineEdit("1.8")
        self.pi_input.setValidator(QDoubleValidator(1.05, 5.0, 3))
        add_row(g4g, "pi", "压缩比 π = p₂/p₁:", self.pi_input, "单级离心常用 1.5~2.0", r); r += 1
        self.eta_is_input = QLineEdit("0.75")
        self.eta_is_input.setValidator(QDoubleValidator(0.3, 1.0, 3))
        add_row(g4g, "etais", "等熵效率 η_is:", self.eta_is_input, "离心式 0.70~0.82", r); r += 1
        self.eta_m_input = QLineEdit("0.95")
        self.eta_m_input.setValidator(QDoubleValidator(0.3, 1.0, 3))
        add_row(g4g, "etam", "电机与传动效率 η_m:", self.eta_m_input, "0.92~0.97", r); r += 1
        self._g4 = g4
        ll.addWidget(g4)

        # ── TVR 参数 ──
        g5 = CalculatorBase.make_group_box("TVR 引射参数")
        g5g = new_grid(g5)
        r = 0
        self.ejector_input = QLineEdit("0.8")
        self.ejector_input.setValidator(QDoubleValidator(0.0, 3.0, 2))
        add_row(g5g, "u", "引射系数 u:", self.ejector_input,
                "kg 引射蒸汽/kg 生蒸汽，常用 0.5~1.2", r)
        self._g5 = g5
        ll.addWidget(g5)

        ll.addStretch()
        scroll.setWidget(lw)

        # ── 右栏 ──
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

        self._on_mode_changed(self.mode_combo.currentText())
        self._update_svg_diagram()

    # ═══════════════════════ 交互 ═══════════════════════
    def _on_heater_changed(self, text):
        """加热室形式 → 自动填传热系数默认值"""
        info = self.HEATER_TYPES.get(text)
        if not info:
            return
        k = info[0]
        self.k1_input.setText(f"{k:g}")
        self.k_single_input.setText(f"{k:g}")

    def _on_mode_changed(self, mode):
        """按模式显隐输入行"""
        multi = mode in ("多效蒸发（并流）", "TVR 热力蒸汽再压缩")
        mvr = mode == "MVR 机械蒸汽再压缩"
        tvr = mode == "TVR 热力蒸汽再压缩"

        vis = {
            "effects": multi,
            "k1": multi,
            "kdecay": multi,
            "ksingle": not multi,
            "dtloss": multi,
            "pi": mvr,
            "etais": mvr,
            "etam": mvr,
            "u": tvr,
        }
        for key, show in vis.items():
            for w in self._rows.get(key, ()):
                w.setVisible(show)
        # 整组显隐：MVR / TVR 参数组在无关模式下只留空标题框，属冗余 UI，一并隐藏
        self._g4.setVisible(mvr)
        self._g5.setVisible(tvr)

    def _num(self, widget, name):
        try:
            return float(widget.text().strip())
        except (TypeError, ValueError):
            raise ValueError(f"{name} 未填写或不是数字")

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
            raise ValueError("IAPWS-IF97 模块不可用，无法计算真空侧饱和参数")
        return _STEAM.saturation_properties(P_MPa=p_abs)

    @staticmethod
    def _p_sat_abs(t_c):
        """由饱和温度求绝压 MPa"""
        if _STEAM is None:
            raise ValueError("IAPWS-IF97 模块不可用，无法计算饱和压力")
        return _STEAM.saturation_pressure(t_c)

    # ═══════════════════════ 计算 ═══════════════════════
    def calculate(self):
        try:
            res = self._compute()
            self._last_result = res
            self._render(res)
            self._update_svg_diagram()
        except ValueError as e:
            self._show_error(str(e))
        except Exception as e:                                   # noqa: BLE001
            self._show_error(f"计算错误：{e}")

    def _read_common(self):
        F = self._num(self.feed_input, "进料量")
        x0 = self._num(self.x0_input, "进料浓度") / 100.0
        x1 = self._num(self.x1_input, "出料浓度") / 100.0
        Tf = self._num(self.tf_input, "进料温度")
        Cp = self._num(self.cp_input, "料液比热容")
        ps = self._num(self.ps_input, "生蒸汽表压")
        eta_h = self._num(self.eta_h_input, "热损失系数")
        bpe = self._num(self.bpe_input, "沸点升高")
        safety = self._num(self.safety_input, "面积裕量系数")
        cw_dt = self._num(self.cw_dt_input, "冷凝器冷却水温升")

        if F <= 0:
            raise ValueError("进料量必须大于 0")
        if not (0 < x0 < 1) or not (0 < x1 < 1):
            raise ValueError("浓度应在 0~100 wt% 之间")
        if x1 <= x0:
            raise ValueError(f"出料浓度 {x1*100:.2f}% 必须大于进料浓度 {x0*100:.2f}%，否则无需浓缩")
        if not (0.5 <= eta_h <= 1.0):
            raise ValueError("热损失系数应在 0.5~1.0 之间")
        if safety < 1.0:
            raise ValueError("面积裕量系数不应小于 1.0")
        if cw_dt <= 0:
            raise ValueError("冷却水温升必须大于 0")

        T_s, lam_s = self._sat_from_gauge(ps)
        if T_s is None:
            raise ValueError("无法获取生蒸汽饱和温度，请检查压力输入")

        W = F * (1.0 - x0 / x1)
        P = F - W
        if W <= 0:
            raise ValueError("蒸发水量为 0，请检查浓度设置")

        return {
            "F": F, "x0": x0, "x1": x1, "Tf": Tf, "Cp": Cp,
            "ps": ps, "eta_h": eta_h, "bpe": bpe, "safety": safety,
            "cw_dt": cw_dt, "T_s": T_s, "lam_s": lam_s, "W": W, "P": P,
        }

    def _compute(self):
        mode = self.mode_combo.currentText()
        c = self._read_common()
        warn = []

        if mode == "单效蒸发":
            core = self._compute_single(c, warn)
        elif mode == "多效蒸发（并流）":
            core = self._compute_multi(c, warn)
        elif mode == "MVR 机械蒸汽再压缩":
            core = self._compute_mvr(c, warn)
        else:
            core = self._compute_multi(c, warn)
            core = self._apply_tvr(core, c, warn)

        core.update({
            "mode": mode,
            # ── 输入回显（供渲染与历史使用）──
            "F_calc": c["F"], "x0_calc": c["x0"], "x1_calc": c["x1"],
            "W_calc": c["W"], "P_calc": c["P"],
            "ps_calc": c["ps"], "T_s_calc": c["T_s"], "lam_s_calc": c["lam_s"],
            "cw_dt_calc": c["cw_dt"], "Tf_calc": c["Tf"], "Cp_calc": c["Cp"],
            # ── 选型信息 ──
            "intensity_lo": self.HEATER_TYPES[self.heater_combo.currentText()][1][0],
            "intensity_hi": self.HEATER_TYPES[self.heater_combo.currentText()][1][1],
            "heater": self.heater_combo.currentText(),
            "heater_note": self.HEATER_TYPES[self.heater_combo.currentText()][2],
            "warn": warn,
        })
        core["compare"] = self._compare_modes(c)
        core["heater_advice"] = self._heater_advice(c, core)
        return core

    # ── 单效 ──
    def _compute_single(self, c, warn):
        tb = self._num(self.tb_input, "蒸发温度")
        K = self._num(self.k_single_input, "传热系数")
        bpe = c["bpe"]
        t_v = tb - bpe                                  # 二次蒸汽温度
        if tb <= c["Tf"] + 1.0:
            warn.append(f"蒸发温度 {tb:.1f} °C 不高于进料温度 {c['Tf']:.1f} °C，料液无自蒸发，"
                        "且需额外显热")
        if tb >= c["T_s"] - 3.0:
            warn.append(f"蒸发温度 {tb:.1f} °C 与生蒸汽饱和温度 {c['T_s']:.1f} °C 过于接近，"
                        "有效传热温差不足，请降低蒸发温度（提高真空度）或提高蒸汽压力")

        p_v = self._p_sat_abs(t_v)
        sat_v = self._sat_from_abs(p_v)
        lam_b = sat_v["h_fg"]
        Ct = c["Cp"]

        Q_evap = c["W"] * lam_b                                     # kJ/h
        Q_sens = c["F"] * Ct * max(0.0, tb - c["Tf"])               # kJ/h
        Q_total = Q_evap + Q_sens
        D = Q_total / (c["lam_s"] * c["eta_h"])                     # kg/h 生蒸汽
        dt = c["T_s"] - tb
        if dt <= 0:
            raise ValueError(f"有效温差 {dt:.2f} °C ≤ 0，无法传热（生蒸汽 {c['T_s']:.1f} °C）")
        A = (Q_total / 3600.0) * 1000.0 / (K * dt) * c["safety"]     # m²
        # 末效冷凝器
        Q_cond = c["W"] * lam_b / 3600.0                            # kW
        cw = Q_cond / (WATER_CP * c["cw_dt"]) * 3600.0 / 1000.0     # m³/h

        return {
            "n": 1, "D": D, "economy": c["W"] / D if D else 0.0,
            "steam_per_water": D / c["W"] if c["W"] else 0.0,
            "Q_total_kW": Q_total / 3600.0, "Q_evap_kW": Q_evap / 3600.0,
            "Q_sens_kW": Q_sens / 3600.0,
            "A_total": A, "A_design": A, "A_avg": A,
            "K_avg": K, "dt_eff_total": dt, "dt_min": dt,
            "effects": [{"i": 1, "t": tb, "t_v": t_v, "p_abs": p_v,
                         "x": c["x1"] * 100, "W": c["W"], "D": D,
                         "K": K, "dT": dt, "Q_kW": Q_total / 3600.0,
                         "A": A, "intensity": c["W"] / A if A else 0.0}],
            "lam_b": lam_b, "cw_m3h": cw, "Q_cond_kW": Q_cond,
            "bpe": bpe, "tb": tb, "t_v_last": t_v,
        }

    # ── 多效（并流） ──
    def _compute_multi(self, c, warn):
        n = int(self.effects_combo.currentText().split()[0])
        K1 = self._num(self.k1_input, "一效传热系数")
        r = self._num(self.k_decay_input, "逐效 K 衰减比")
        dt_loss = self._num(self.dtloss_input, "效间温差损失")
        t_n = self._num(self.tb_input, "末效蒸发温度")
        bpe = c["bpe"]
        Cp = c["Cp"]
        W_total = c["W"]
        F = c["F"]
        T_s = c["T_s"]

        sum_dt = T_s - t_n - (n - 1) * dt_loss
        if sum_dt <= n * 1.0:
            raise ValueError(
                f"有效总温差不足（{sum_dt:.2f} °C，含 {n-1} 段效间损失 {dt_loss:.2f} °C/段）："
                f"生蒸汽饱和温度 {T_s:.1f} °C，末效沸点 {t_n:.1f} °C。"
                f"请减少效数、提高生蒸汽压力或降低末效温度")
        if t_n <= c["Tf"]:
            warn.append(f"末效沸点 {t_n:.1f} °C 不高于进料温度 {c['Tf']:.1f} °C，"
                        "前段料液无自蒸发，且可能需预冷进料")

        K = [K1 * r ** i for i in range(n)]
        inv_sum = sum(1.0 / k for k in K)
        dT = [sum_dt * (1.0 / K[i]) / inv_sum for i in range(n)]

        # 各效溶液沸点与二次蒸汽温度
        t = []
        t_prev = T_s
        for i in range(n):
            t_i = t_prev - dT[i]
            t.append(t_i)
            t_prev = t_i - bpe - (dt_loss if i < n - 1 else 0.0)
        # 温度序列自检（末效应落到 t_n 附近，偏差即输入不自洽）
        if abs(t[-1] - t_n) > 1.0:
            warn.append(f"温差分配后末效沸点 {t[-1]:.2f} °C 与输入末效沸点 {t_n:.2f} °C "
                        f"偏差 {t[-1]-t_n:+.2f} °C（沸点升高与效间损失所致，属正常）")

        # 逐效汽化潜热
        lam = [self._sat_from_gauge(c["ps"])[1]]              # i=1 用生蒸汽
        for i in range(1, n):
            lam.append(self._sat_from_abs(self._p_sat_abs(t[i - 1] - bpe))["h_fg"])
        lam_b = [self._sat_from_abs(self._p_sat_abs(t[i]))["h_fg"] for i in range(n)]

        # 逐效热量衡算（对 D1 线性：W_i = a_i·D1 + b_i）
        Acoef = [0.0] * n
        Bcoef = [0.0] * n
        dT_sol = [t[i] - (c["Tf"] if i == 0 else t[i - 1]) for i in range(n)]
        for i in range(n):
            if i == 0:
                Acoef[0] = lam[0] * c["eta_h"] / lam_b[0]
                Bcoef[0] = -F * Cp * dT_sol[0] / lam_b[0]
            else:
                A_prev = sum(Acoef[:i])
                B_prev = sum(Bcoef[:i])
                Acoef[i] = (Acoef[i - 1] * lam[i] * c["eta_h"]
                            + A_prev * Cp * dT_sol[i]) / lam_b[i]
                Bcoef[i] = (Bcoef[i - 1] * lam[i] * c["eta_h"]
                            - (F - B_prev) * Cp * dT_sol[i]) / lam_b[i]
        sum_a, sum_b = sum(Acoef), sum(Bcoef)
        if abs(sum_a) < 1e-12:
            raise ValueError("热量衡算方程组退化，请检查输入")
        D1 = (W_total - sum_b) / sum_a
        if D1 <= 0:
            raise ValueError(
                f"解得生蒸汽量为 {D1:.1f} kg/h（负值/零）：料液自蒸发已超过蒸发需求，"
                f"请检查进料温度 {c['Tf']:.1f} °C 与末效沸点 {t_n:.1f} °C 是否合理")
        Ws = [Acoef[i] * D1 + Bcoef[i] for i in range(n)]

        # 各效浓度 / 面积 / 强度
        effects = []
        cum = 0.0
        for i in range(n):
            cum += Ws[i]
            x_i = F * c["x0"] / (F - cum) if (F - cum) > 0 else float("nan")
            D_i = D1 if i == 0 else Ws[i - 1]
            Q = D_i * lam[i] / 3600.0                       # kW
            A_i = Q * 1000.0 / (K[i] * dT[i]) * c["safety"]
            effects.append({
                "i": i + 1, "t": t[i], "t_v": t[i] - bpe,
                "p_abs": self._p_sat_abs(t[i] - bpe),
                "x": x_i * 100, "W": Ws[i], "D": D_i,
                "K": K[i], "dT": dT[i], "Q_kW": Q,
                "A": A_i, "intensity": Ws[i] / A_i if A_i else 0.0,
            })
        A_design = max(e["A"] for e in effects)
        A_total = sum(e["A"] for e in effects)

        # 末效冷凝器
        lam_last = lam_b[-1]
        Q_cond = Ws[-1] * lam_last / 3600.0
        cw = Q_cond / (WATER_CP * c["cw_dt"]) * 3600.0 / 1000.0

        # 热量拆解：传热侧热负荷 − 蒸发潜热 = 料液显热+自蒸发净项
        q_steam_net = sum(effects[i]["D"] * lam[i] * c["eta_h"]
                          for i in range(n)) / 3600.0
        q_evap = sum(Ws[i] * lam_b[i] for i in range(n)) / 3600.0
        q_sens = q_steam_net - q_evap

        lo, hi = self.HEATER_TYPES[self.heater_combo.currentText()][1]
        bad = [(e["i"], round(e["intensity"], 1)) for e in effects
               if not (lo * 0.7 <= e["intensity"] <= hi * 1.4)]
        if bad:
            warn.append(f"部分效蒸发强度超出所选形式的经验区间 {lo:g}~{hi:g} kg/(m²·h)："
                        f"{bad}，建议调整效数/K 取值或改选加热室形式")

        return {
            "n": n, "D": D1, "economy": W_total / D1 if D1 else 0.0,
            "steam_per_water": D1 / W_total if W_total else 0.0,
            "Q_total_kW": sum(e["Q_kW"] for e in effects),
            "Q_evap_kW": q_evap, "Q_sens_kW": q_sens,
            "A_total": A_total, "A_design": A_design,
            "A_avg": A_total / n, "K_avg": sum(K) / n,
            "dt_eff_total": sum_dt, "dt_min": min(dT),
            "effects": effects, "dT": dT, "K": K,
            "lam_b": lam_b[-1], "cw_m3h": cw, "Q_cond_kW": Q_cond,
            "bpe": bpe, "tb": t_n, "t_v_last": t[-1] - bpe,
        }

    # ── MVR ──
    def _compute_mvr(self, c, warn):
        if _STEAM is None:
            raise ValueError("IAPWS-IF97 模块不可用，MVR 压缩计算无法进行")
        tb = self._num(self.tb_input, "蒸发温度")
        K = self._num(self.k_single_input, "传热系数")
        pi = self._num(self.pi_input, "压缩比")
        eta_is = self._num(self.eta_is_input, "等熵效率")
        eta_m = self._num(self.eta_m_input, "电机与传动效率")
        bpe = c["bpe"]

        if pi <= 1.0:
            raise ValueError("压缩比必须大于 1")
        if tb <= c["Tf"]:
            warn.append(f"蒸发温度 {tb:.1f} °C 不高于进料温度 {c['Tf']:.1f} °C，"
                        "需另行预热/预冷进料")

        t_v = tb - bpe
        p1 = self._p_sat_abs(t_v)
        p2 = p1 * pi
        sat1 = self._sat_from_abs(p1)
        sat2 = self._sat_from_abs(p2)
        h1, s1 = sat1["h_g"], sat1["s_g"]
        T2_sat = sat2["T_C"]
        dt_heat = T2_sat - tb
        if dt_heat < 5.0:
            warn.append(f"压缩后饱和温度 {T2_sat:.1f} °C 与溶液沸点 {tb:.1f} °C 的有效温差仅 "
                        f"{dt_heat:.2f} °C（宜 ≥5~8 °C）：需提高压缩比或降低蒸发温度")
        if dt_heat <= 0:
            raise ValueError(
                f"压缩后饱和温度 {T2_sat:.2f} °C 低于溶液沸点 {tb:.2f} °C，无法传热；"
                f"压缩比 {pi:.2f} 偏小，至少需 {self._p_sat_abs(tb)/p1:.2f}")

        st2s = _STEAM.properties_from_ps(p2, s1)
        h2s = st2s["h"]
        w_is = h2s - h1
        if w_is <= 0:
            raise ValueError("等熵压缩焓升为负，请检查压缩比与蒸发温度")
        w_act = w_is / eta_is
        h2_act = h1 + w_act
        st2_act = _STEAM.properties_from_ph(p2, h2_act)
        T2_act = st2_act["T_C"]
        superheat = max(0.0, T2_act - T2_sat)

        P_shaft = c["W"] * w_act / 3600.0                  # kW 轴功率
        P_motor = P_shaft / eta_m                          # kW 电机输入
        unit_kwh = P_motor / (c["W"] / 1000.0)             # kWh/t 蒸发水

        # 能量平衡：压缩蒸汽可供热 vs 蒸发+显热需求
        q_avail = c["W"] * (h2_act - sat2["h_f"]) / 3600.0              # kW
        lam_b = sat1["h_fg"]
        q_need = (c["W"] * lam_b + c["F"] * c["Cp"] * max(0.0, tb - c["Tf"])) / 3600.0
        delta_kw = q_avail - q_need
        D_supply = 0.0
        if delta_kw < 0:
            D_supply = (-delta_kw) * 3600.0 / (c["lam_s"] * c["eta_h"])
            warn.append(f"压缩蒸汽供热不足 {(-delta_kw):.1f} kW，需补充生蒸汽约 "
                        f"{D_supply:.0f} kg/h（用于进料预热或提高压缩比）")
        A_heat = q_need * 1000.0 / (K * dt_heat) * c["safety"] if dt_heat > 0 else float("nan")

        return {
            "n": 1, "D": D_supply,
            "economy": (c["W"] / D_supply) if D_supply > 0 else float("inf"),
            "steam_per_water": (D_supply / c["W"]) if c["W"] else 0.0,
            "Q_total_kW": q_need, "Q_evap_kW": c["W"] * lam_b / 3600.0,
            "Q_sens_kW": c["F"] * c["Cp"] * max(0.0, tb - c["Tf"]) / 3600.0,
            "A_total": A_heat, "A_design": A_heat, "A_avg": A_heat,
            "K_avg": K, "dt_eff_total": dt_heat, "dt_min": dt_heat,
            "effects": [{"i": 1, "t": tb, "t_v": t_v, "p_abs": p1,
                         "x": c["x1"] * 100, "W": c["W"], "D": c["W"],
                         "K": K, "dT": dt_heat, "Q_kW": q_need,
                         "A": A_heat, "intensity": c["W"] / A_heat if A_heat else 0.0}],
            "lam_b": lam_b, "cw_m3h": 0.0, "Q_cond_kW": max(0.0, -delta_kw),
            "bpe": bpe, "tb": tb, "t_v_last": t_v,
            "mvr": {
                "pi": pi, "p1": p1, "p2": p2, "T2_sat": T2_sat,
                "T2_act": T2_act, "superheat": superheat,
                "w_is": w_is, "w_act": w_act, "h1": h1, "h2s": h2s,
                "P_shaft": P_shaft, "P_motor": P_motor,
                "unit_kwh": unit_kwh, "q_avail": q_avail, "q_need": q_need,
                "delta_kw": delta_kw, "D_supply": D_supply,
                "eta_is": eta_is, "eta_m": eta_m,
            },
        }

    # ── TVR（在多效结果上叠加） ──
    def _apply_tvr(self, core, c, warn):
        u = self._num(self.ejector_input, "引射系数")
        if u < 0:
            raise ValueError("引射系数不能为负")
        D_new = core["D"] / (1.0 + u)
        D_eject = core["D"] - D_new                     # 被引射的二次蒸汽量
        econ_raw = core["economy"]
        core["tvr"] = {
            "u": u, "D_raw": core["D"], "D_new": D_new,
            "D_eject": D_eject, "economy_raw": econ_raw,
            "economy_new": econ_raw * (1.0 + u),
        }
        core["D"] = D_new
        core["economy"] = econ_raw * (1.0 + u)
        core["steam_per_water"] = D_new / c["W"] if c["W"] else 0.0
        warn.append(f"TVR 引射系数 u = {u:.2f}：生蒸汽由 {core['tvr']['D_raw']:.0f} "
                    f"降至 {D_new:.0f} kg/h，蒸汽经济性 {econ_raw:.2f} → "
                    f"{core['economy']:.2f}（提高 {u*100:.0f}%）；"
                    f"引射蒸汽 {D_eject:.0f} kg/h 取自二次蒸汽。⚠ 单级喷射器压缩比通常 ≤1.5，"
                    f"引射系数随压比升高迅速下降，实际 u 须由喷射器厂家按工况给出")
        if u > 1.2:
            warn.append(f"引射系数 {u:.2f} 高于单级喷射器常用上限 1.2，请核实喷射器选型")
        return core

    # ── 四方案能耗对比 ──
    def _compare_modes(self, c):
        """同一蒸发负荷下对比 单效 / 多效 / MVR / TVR 的能耗（自洽口径）"""
        rows = []
        tb = self._num(self.tb_input, "蒸发温度")
        bpe = c["bpe"]
        lam_b = self._sat_from_abs(self._p_sat_abs(tb - bpe))["h_fg"]
        # 单效
        try:
            s1 = self._compute_single(c, [])
            rows.append(("单效蒸发", "1 效", s1["steam_per_water"], 0.0, s1["A_total"]))
        except ValueError:
            pass
        # 多效
        try:
            mn = self._compute_multi(c, [])
            rows.append((f"多效蒸发（{mn['n']} 效）", f"{mn['n']} 效",
                         mn["steam_per_water"], 0.0, mn["A_total"]))
        except ValueError:
            pass
        # MVR
        try:
            mv = self._compute_mvr(c, [])
            rows.append(("MVR 机械蒸汽再压缩", "1 效",
                         mv["steam_per_water"], mv["mvr"]["unit_kwh"], mv["A_total"]))
        except ValueError:
            pass
        # TVR（在可算的多效基础上）
        try:
            mt = self._apply_tvr(self._compute_multi(c, []), c, [])
            rows.append((f"TVR 热力蒸汽再压缩（{mt['n']} 效 + 喷射器）", f"{mt['n']} 效",
                         mt["steam_per_water"], 0.0, mt["A_total"]))
        except ValueError:
            pass
        return {"rows": rows, "lam_b": lam_b}

    # ── 加热室形式建议 ──
    def _heater_advice(self, c, core):
        """按浓度、蒸发强度与所选形式给建议（不做无出处的自动判定，只做一致性提示）"""
        tips = []
        x1 = c["x1"] * 100
        tips.append(f"出料浓度 {x1:.1f} wt%：浓度越高粘度越大、沸点升高越大，"
                    "末效宜留足够有效温差")
        if x1 >= 45 and "降膜" in core["heater"]:
            tips.append("出料浓度 ≥45 wt%：粘度上升明显，降膜分配器与布膜难度增大，"
                        "宜考虑降膜+强制循环组合或末段强制循环")
        if x1 >= 60:
            tips.append("出料浓度 ≥60 wt%：接近或超过部分糖类常温溶解度，"
                        "需确认是否有结晶析出风险并核算结垢周期")
        tips.append(f"当前形式（{core['heater']}）经验蒸发强度区间 "
                    f"{core['intensity_lo']:g}~{core['intensity_hi']:g} kg/(m²·h)："
                    f"{core['heater_note']}")
        return tips

    # ═══════════════════════ 结果渲染 ═══════════════════════
    def _render(self, r):
        L = []
        L.append("浓缩蒸发器计算")
        L.append("=" * 60)
        L.append(f"【计算模式】{r['mode']}    加热室形式：{r['heater']}")
        L.append("")
        L.append("【一、物料衡算】")
        L.append(f"  进料量 F          = {r['F_calc']:.0f} kg/h")
        L.append(f"  浓度 x0 → x1      = {r['x0_calc']*100:.2f} → {r['x1_calc']*100:.2f} wt%")
        L.append(f"  蒸发水量 W        = F(1 − x0/x1) = {r['W_calc']:.1f} kg/h")
        L.append(f"  浓缩液量 P        = F − W = {r['P_calc']:.1f} kg/h")
        L.append(f"  浓缩倍数          = {r['x1_calc']/r['x0_calc']:.2f}")
        L.append("")
        L.append("【二、蒸汽与热量衡算】")
        L.append(f"  生蒸汽表压       = {r['ps_calc']:.3f} MPa(g)"
                 f"  →  饱和温度 {r['T_s_calc']:.1f} °C，"
                 f"汽化潜热 {r['lam_s_calc']:.1f} kJ/kg")
        L.append(f"  蒸发温度 t_b      = {r['tb']:.1f} °C，沸点升高 BPE = {r['bpe']:.2f} °C"
                 f"  →  二次蒸汽温度 {r['t_v_last']:.2f} °C")
        L.append(f"  总热负荷 Q        = {r['Q_total_kW']:.1f} kW"
                 f"（蒸发 {r['Q_evap_kW']:.1f} + 进料显热 {r['Q_sens_kW']:.1f}）")
        if r.get("mvr"):
            L.append("")
        L.append(f"  生蒸汽耗量 D      = {r['D']:.1f} kg/h")
        L.append(f"  蒸汽经济性 W/D    = {r['economy']:.3f} kg 蒸发水/kg 生蒸汽")
        L.append(f"  单位汽耗          = {r['steam_per_water']:.3f} t 蒸汽/t 蒸发水")
        if r.get("mvr"):
            m = r["mvr"]
            L.append("")
            L.append("【三、MVR 压缩计算】")
            L.append(f"  蒸发室压力 p₁     = {m['p1']*1000:.2f} kPa(a)")
            L.append(f"  压缩后压力 p₂     = {m['p2']*1000:.2f} kPa(a)"
                     f"（压缩比 π = {m['pi']:.2f}）")
            L.append(f"  压缩后饱和温度    = {m['T2_sat']:.2f} °C；实际排气 "
                     f"{m['T2_act']:.2f} °C（过热 {m['superheat']:.2f} °C）")
            L.append(f"  有效传热温差      = {m['T2_sat']:.2f} − {r['tb']:.2f} = "
                     f"{r['dt_eff_total']:.2f} °C")
            L.append(f"  等熵焓升 w_is     = {m['w_is']:.2f} kJ/kg"
                     f"（h₁ {m['h1']:.1f} → h₂s {m['h2s']:.1f} kJ/kg）")
            L.append(f"  实际比功 w_act    = w_is/η_is = {m['w_act']:.2f} kJ/kg"
                     f"（η_is = {m['eta_is']:.2f}）")
            L.append(f"  压缩机轴功率      = {m['P_shaft']:.1f} kW")
            L.append(f"  电机输入功率      = {m['P_motor']:.1f} kW"
                     f"（η_m = {m['eta_m']:.2f}）")
            L.append(f"  单位电耗          = {m['unit_kwh']:.1f} kWh/t 蒸发水")
            L.append(f"  供热/需热         = {m['q_avail']:.1f} / {m['q_need']:.1f} kW"
                     f"  →  差额 {m['delta_kw']:+.1f} kW")
            if m["D_supply"] > 0:
                L.append(f"  需补充生蒸汽      = {m['D_supply']:.1f} kg/h")
            else:
                L.append("  无需补充生蒸汽（稳定运行下仅启动/补热用汽）")
        else:
            L.append("")
            L.append("【三、各效参数】")
            for e in r["effects"]:
                L.append(f"  第 {e['i']} 效： 沸点 {e['t']:.2f} °C | 蒸汽 "
                         f"{e['t_v']:.2f} °C | {e['p_abs']*1000:.1f} kPa(a)")
                L.append(f"          浓度 {e['x']:.2f} wt% | 蒸发量 {e['W']:.1f} kg/h | "
                         f"加热蒸汽 {e['D']:.1f} kg/h")
                L.append(f"          K = {e['K']:.0f} W/(m²·K) | ΔT = {e['dT']:.2f} °C | "
                         f"Q = {e['Q_kW']:.1f} kW")
                L.append(f"          面积 A = {e['A']:.2f} m² | 蒸发强度 "
                         f"{e['intensity']:.1f} kg/(m²·h)")
        L.append("")
        L.append("【四、面积与校核】")
        L.append(f"  有效总温差        = {r['dt_eff_total']:.2f} °C"
                 f"（最小分温差 {r['dt_min']:.2f} °C）")
        L.append(f"  平均传热系数      = {r['K_avg']:.0f} W/(m²·K)")
        L.append(f"  设计面积（取最大） = {r['A_design']:.2f} m²")
        L.append(f"  各效面积之和      = {r['A_total']:.2f} m²"
                 f"（平均 {r['A_avg']:.2f} m²/效）")
        L.append(f"  蒸发强度区间参考  = {r['intensity_lo']:g}~{r['intensity_hi']:g} "
                 f"kg/(m²·h)（{r['heater']}）")
        if r["cw_m3h"] > 0:
            L.append(f"  末效冷凝器        = {r['Q_cond_kW']:.1f} kW"
                     f"  →  循环冷却水 ≈ {r['cw_m3h']:.1f} m³/h"
                     f"（温升 {r['cw_dt_calc']:.0f} °C）")
        if r.get("tvr"):
            t = r["tvr"]
            L.append("")
            L.append("【五、TVR 节能效果】")
            L.append(f"  引射系数 u        = {t['u']:.2f}")
            L.append(f"  生蒸汽耗量        = {t['D_raw']:.1f} → {t['D_new']:.1f} kg/h")
            L.append(f"  引射二次蒸汽      = {t['D_eject']:.1f} kg/h")
            L.append(f"  蒸汽经济性        = {t['economy_raw']:.3f} → {t['economy_new']:.3f}"
                     f"（×(1+u)）")
        if r["compare"]["rows"]:
            L.append("")
            L.append("【方案能耗对比（同一蒸发负荷）】")
            L.append(f"  {'方案':<28}{'蒸汽 t/t':>10}{'电耗 kWh/t':>12}{'面积 m²':>10}")
            for name, eff, spw, kwh, area in r["compare"]["rows"]:
                L.append(f"  {name:<28}{spw:>10.3f}{kwh:>12.1f}{area:>10.1f}")
            L.append("  注：蒸汽耗量按同一生蒸汽压力与蒸发温度计算；MVR 的蒸汽仅为补热，"
                     "主能耗为电")
        L.append("")
        L.append("【加热室形式与工艺提示】")
        for i, tip in enumerate(r["heater_advice"], 1):
            L.append(f"  {i}) {tip}")
        if r["warn"]:
            L.append("")
            L.append("【提示与警告】")
            for i, w in enumerate(r["warn"], 1):
                L.append(f"  {i}) {w}")
        L.append("")
        L.append("=" * 60)
        L.append("  沸点升高 BPE 由输入给定（各效取同一值）——不同体系差异大且随浓度剧变，")
        L.append("  本计算器不做关联式推算，请按物料手册或试验数据填入后再定案。")
        L.append("  蒸发强度与传热系数为公开资料/设备样本经验区间，宜以中试或厂商样本确认。")
        L.append("=" * 60)
        self.result_text.setPlainText("\n".join(L))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"错误：{msg}")
        self._last_result = {}

    def _show_warn(self, msg):
        self.result_text.setPlainText(f"提示：{msg}")

    # ═══════════════════════ 清空 ═══════════════════════
    def setup_default_values(self):
        self.feed_input.setText("10000")
        self.x0_input.setText("12")
        self.x1_input.setText("60")
        self.tf_input.setText("25")
        self.cp_input.setText("3.80")
        self.ps_input.setText("0.4")
        self.eta_h_input.setText("0.97")
        self.tb_input.setText("70")
        self.bpe_input.setText("1.5")
        self.dtloss_input.setText("1.0")
        self.cw_dt_input.setText("8")
        self.effects_combo.setCurrentIndex(1)
        self.k1_input.setText("2500")
        self.k_decay_input.setText("0.8")
        self.k_single_input.setText("2000")
        self.safety_input.setText("1.15")
        self.pi_input.setText("1.8")
        self.eta_is_input.setText("0.75")
        self.eta_m_input.setText("0.95")
        self.ejector_input.setText("0.8")

    def clear_inputs(self):
        """恢复出厂默认值（可直接重算）"""
        self.mode_combo.setCurrentIndex(0)
        self.heater_combo.setCurrentIndex(0)
        self.setup_default_values()
        self.result_text.clear()
        self._last_result = {}
        self._on_mode_changed(self.mode_combo.currentText())
        self._update_svg_diagram()

    # ═══════════════════════ 历史 ═══════════════════════
    def _get_history_data(self):
        r = self._last_result
        if not r:
            return {"inputs": {}, "outputs": {}}
        inputs = {
            "计算模式": r.get("mode", ""),
            "加热室形式": r.get("heater", ""),
            "进料量_kg_h": r.get("F_calc", 0),
            "进料浓度_wt%": round(r.get("x0_calc", 0) * 100, 2),
            "出料浓度_wt%": round(r.get("x1_calc", 0) * 100, 2),
            "生蒸汽表压_MPa": r.get("ps_calc", 0),
            "效数": r.get("n", 1),
        }
        outputs = {
            "蒸发水量_kg_h": round(r.get("W_calc", 0), 1),
            "生蒸汽耗量_kg_h": round(r.get("D", 0), 1),
            "蒸汽经济性": round(r.get("economy", 0), 3) if r.get("economy") != float("inf") else 0,
            "单位汽耗_t_t": round(r.get("steam_per_water", 0), 3),
            "设计面积_m2": round(r.get("A_design", 0), 1),
            "各效面积之和_m2": round(r.get("A_total", 0), 1),
        }
        if r.get("mvr"):
            outputs["压缩机轴功率_kW"] = round(r["mvr"]["P_shaft"], 1)
            outputs["单位电耗_kWh_t"] = round(r["mvr"]["unit_kwh"], 1)
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
            "calculation_type": "浓缩蒸发器（单效/多效/MVR/TVR）",
        }

    def generate_report(self):
        """生成计算书文本（str；无结果返回 None）"""
        try:
            body = self.result_text.toPlainText()
            if not body or "浓缩蒸发器计算" not in body:
                return None
            info = self.get_project_info()
            head = "\n".join([
                "═" * 60,
                "        浓缩蒸发器计算书（单效 / 多效 / MVR / TVR）",
                "═" * 60,
            ])
            foot = "\n".join([
                "═" * 60,
                " 工程信息",
                "═" * 60,
                "",
                f"  公司名称: {info.get('company_name', '')}",
                f"  工程编号: {info.get('project_number', '')}",
                f"  工程名称: {info.get('project_name', '')}",
                f"  子项名称: {info.get('subproject_name', '')}",
                f"  计算类型: {info.get('calculation_type', '')}",
                f"  计算日期: {datetime.now().strftime('%Y-%m-%d')}",
                "",
                "═" * 60,
                " 计算公式",
                "═" * 60,
                "",
                "  1. 物料衡算    W = F·(1 − x0/x1)；  P = F − W",
                "                 第 i 效浓度 x_i = F·x0/(F − ΣW_j)",
                "  2. 逐效热量衡算 W_i·λ'_i = D_i·λ_i·η_h − F_i·Cp·(t_i − t_{i−1})",
                "                 并流：D_1 = 生蒸汽，D_i = W_{i−1}，t_0 = 进料温度",
                "                 对 D_1 线性 ⇒ 由 ΣW_i = W 闭式解出 D_1",
                "  3. 蒸汽经济性   = W/D_1；单位汽耗 = D_1/W",
                "  4. 温差分配     ΣΔT = T_s − t_n − (n−1)·Δ'''；ΔT_i ∝ 1/K_i，",
                "                 K_i = K_1·r^(i−1)",
                "  5. 传热面积     A_i = Q_i/(K_i·ΔT_i)；设计面积取 max(A_i)",
                "  6. MVR 压缩     p_1 = p_sat(t_b − BPE)，p_2 = p_1·π",
                "                 h_2s = h(p_2, s = s_1)（IAPWS-IF97 反算）",
                "                 w_act = (h_2s − h_1)/η_is；P = W·w_act/3600",
                "                 供热 = W·(h_2act − h_f(p_2))；需热 = W·λ'_b + F·Cp·(t_b − T_f)",
                "  7. TVR          生蒸汽 D → D/(1+u)；经济性 ×(1+u)",
                "",
                "═" * 60,
                " 数据来源与假设",
                "═" * 60,
                "",
                "  1. 蒸汽物性采用 IAPWS-IF97（本程序自带实现）；汽化潜热经",
                "     common_constants.get_steam_props 统一入口取得；",
                "  2. 沸点升高 BPE 由输入给定、各效取同一值——不同体系差异大且随浓度剧变，",
                "     不做关联式推算，须按物料手册或试验数据填入；",
                "  3. 蒸发强度经验区间（kg/(m²·h)）：降膜清洁 20~35、降膜易结垢 12~20、",
                "     升膜 15~30；强制循环/外循环样本未给统一值，按易结垢工况 12~20 保守取值；",
                "  4. 传热系数区间 W/(m²·K)：降膜 1500~3500、升膜 1500~2500、",
                "     强制循环/外循环 1000~1800，默认取区间中位；",
                "  5. 热损失系数 η_h 取 0.95~0.98（每效 2~5% 热损）；",
                "  6. 多效按并流进料、各效等面积法设计；未计冷凝水闪蒸、不凝气排放、",
                "     料液沸点升高沿程变化与结晶析出；",
                "  7. 计算结果仅供参考，实际工程须经专业工程师审核确认，",
                "     并以中试或厂商样本数据校核 K 与蒸发强度。",
                "",
                "---",
                "生成于 ChemCal 工程计算模块",
            ])
            return f"{head}\n\n{body}\n\n{foot}"
        except Exception as e:                                   # noqa: BLE001
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        ReportExporter.export_docx(self, "浓缩蒸发器计算")

    def download_pdf_report(self):
        ReportExporter.export_pdf(self, "浓缩蒸发器计算")

    # ═══════════════════════ SVG 示意图 ═══════════════════════
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        return svg_text(x, y, text, size, color, bold, center)

    def _update_svg_diagram(self):
        """按当前模式刷新蒸发流程示意图"""
        w, h = 380, 250
        mode = self.mode_combo.currentText()
        p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
             f'width="{w}" height="{h}">',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']

        mvr = mode.startswith("MVR")
        multi = mode.startswith("多效") or mode.startswith("TVR")
        n = 1
        if multi:
            try:
                n = int(self.effects_combo.currentText().split()[0])
            except (TypeError, ValueError):
                n = 3

        # 生蒸汽管
        p.append(f'<line x1="30" y1="52" x2="96" y2="52" stroke="#e74c3c" stroke-width="4"/>')
        p.append(self._text(30, 40, "生蒸汽", size=9, color="#e74c3c", bold=True,
                            center=False))

        # 效体：多效分列，单效/MVR 一个大方框
        n_show = n if multi else 1
        total_w = 230.0
        gap = 8.0
        bw = (total_w - (n_show - 1) * gap) / n_show
        x0, y0, bh = 96.0, 76.0, 74.0
        r = self._last_result
        for i in range(n_show):
            x = x0 + i * (bw + gap)
            p.append(f'<rect x="{x:.1f}" y="{y0}" width="{bw:.1f}" height="{bh}" '
                     f'fill="#e8edf2" stroke="#4a6fa5" stroke-width="2" rx="4"/>')
            p.append(self._text(x + bw / 2, y0 + 20, f"{i+1} 效" if multi else "蒸发室",
                                size=9, color="#4a6fa5", bold=True))
            if r and r.get("effects") and i < len(r["effects"]):
                e = r["effects"][i]
                p.append(self._text(x + bw / 2, y0 + 38, f"{e['t']:.0f}°C",
                                    size=8, color="#333"))
                p.append(self._text(x + bw / 2, y0 + 52, f"A={e['A']:.1f}m²",
                                    size=8, color="#333"))
            # 效间二次蒸汽箭头
            if i < n_show - 1:
                ax = x + bw + 1
                p.append(f'<line x1="{ax:.1f}" y1="{y0+bh/2:.1f}" x2="{ax+gap-2:.1f}" '
                         f'y2="{y0+bh/2:.1f}" stroke="#e67e22" stroke-width="3"/>')
        x_end = x0 + n_show * bw + (n_show - 1) * gap

        # MVR 压缩机（首效上方回压）
        if mvr:
            p.append(f'<rect x="{x0+bw/2-34:.1f}" y="18" width="68" height="30" rx="5" '
                     f'fill="#d5f5e3" stroke="#1d6f42" stroke-width="1.5"/>')
            p.append(self._text(x0 + bw / 2, 33, "压缩机", size=9, color="#1d6f42", bold=True))
            p.append(f'<line x1="{x0+bw/2:.1f}" y1="{y0}" x2="{x0+bw/2:.1f}" y2="48" '
                     f'stroke="#e67e22" stroke-width="3"/>')
            p.append(f'<line x1="{x0+bw/2-30:.1f}" y1="48" x2="{x0+bw/2:.1f}" y2="48" '
                     f'stroke="#e67e22" stroke-width="3"/>')

        # 进料 / 出料
        p.append(f'<line x1="30" y1="{y0+56:.1f}" x2="{x0:.1f}" y2="{y0+56:.1f}" '
                 f'stroke="#2980b9" stroke-width="4"/>')
        p.append(self._text(30, y0 + 70, "进料", size=9, color="#2980b9", bold=True,
                            center=False))
        p.append(f'<line x1="{x_end:.1f}" y1="{y0+bh+8:.1f}" x2="{x_end+10:.1f}" '
                 f'y2="{y0+bh+8:.1f}" stroke="#16a085" stroke-width="4"/>')
        p.append(self._text(x_end - 6, y0 + bh + 24, "浓缩液", size=9, color="#16a085",
                            bold=True, center=False))

        # 冷凝器 / 真空
        p.append(f'<line x1="{x_end-8:.1f}" y1="{y0+bh:.1f}" x2="{x_end-8:.1f}" '
                 f'y2="{y0+bh+34:.1f}" stroke="#7f8c8d" stroke-width="3"/>')
        p.append(f'<rect x="{x_end-46:.1f}" y="{y0+bh+34:.1f}" width="76" height="26" rx="4" '
                 f'fill="#fdebd0" stroke="#b9770e" stroke-width="1.5"/>')
        p.append(self._text(x_end - 8, y0 + bh + 47,
                            "不凝气/真空" if mvr else "冷凝器", size=8,
                            color="#b9770e", bold=True))

        # 底部摘要
        if r:
            p.append(self._text(w / 2, h - 44,
                                f"W = {r['W_calc']:.0f} kg/h   "
                                f"汽耗 {r['steam_per_water']:.3f} t/t   经济性 {r['economy']:.2f}"
                                if r.get("economy") != float("inf") else
                                f"W = {r['W_calc']:.0f} kg/h",
                                size=9, color="#1d6f42", bold=True))
            extra = f"设计面积 {r['A_design']:.1f} m²"
            if r.get("mvr"):
                extra += f"   电耗 {r['mvr']['unit_kwh']:.1f} kWh/t"
            p.append(self._text(w / 2, h - 28, extra, size=9, color="#1d6f42", bold=True))
        else:
            p.append(self._text(w / 2, h - 30, "点击「计 算」查看结果", size=9, color="#888"))
        p.append("</svg>")
        self.svg_widget.load("".join(p).encode("utf-8"))


# 为动态导入提供简洁别名
evaporator_calculator = EvaporatorCalculator
