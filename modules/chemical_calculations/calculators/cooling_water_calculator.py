import os
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QGridLayout, QFileDialog, QMessageBox,
    QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator, QFont
from PySide6.QtSvgWidgets import QSvgWidget
from modules.combo_box_utils import ComboBoxWheelBlocker


COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #888; border-radius: 4px;
        padding: 6px 10px;
    }
    QComboBox QAbstractItemView {
        border: 1px solid #888;
        selection-background-color: #3498db; selection-color: black;
    }
    QComboBox QAbstractItemView::item { padding: 3px 8px; }
"""


class CoolingWaterCalculator(QWidget):
    """循环冷却水用水量计算 — 模式驱动版

    5种热负荷来源模式 + 直接输入模式，统一计算循环水量、推荐管径。
    """

    # ── 发酵类型 → 产热率范围 (kJ/L·h) ──
    FERM_TYPES = {
        "请选择发酵类型":     (0, 0),
        "氨基酸发酵(缬氨酸/谷氨酸等)": (12, 25),
        "细菌发酵(E.coli等好氧)":      (20, 60),
        "酵母发酵":                     (5, 15),
        "霉菌发酵(青霉素等)":           (2, 8),
        "乳酸菌发酵(微好氧)":           (2, 5),
        "厌氧发酵":                     (0.5, 2),
    }

    # ── 气体比热容参考 (kJ/(kg·°C)) ──
    GAS_CP = {
        "请选择气体":       1.0,
        "空气":             1.005,
        "氮气(N2)":         1.04,
        "二氧化碳(CO2)":    0.85,
        "甲烷(CH4)":        2.22,
        "氨气(NH3)":        2.06,
        "蒸汽/水蒸气":      1.86,
    }

    # ── 冷却水参数预设 ──
    CW_PRESETS = {
        "循环冷却水(进32°C,出37°C,ΔT=5)":  (32, 37),
        "循环冷却水(进32°C,出40°C,ΔT=8)":  (32, 40),
        "冷冻水(进7°C,出12°C,ΔT=5)":       (7, 12),
        "深冷水(进-5°C,出0°C,ΔT=5)":       (-5, 0),
    }

    # ── 推荐流速 ──
    PIPE_VELOCITY = {
        "DN25以下": 1.0,
        "DN25~DN50": 1.5,
        "DN50~DN100": 2.0,
        "DN100~DN200": 2.5,
        "DN200以上": 3.0,
    }

    STANDARD_PIPES = [25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 250, 300, 350, 400, 450, 500]

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self._last_result = {}
        self.setup_ui()
        self._on_mode_changed(self.mode_combo.currentText())

        self._wheel_blocker = ComboBoxWheelBlocker(self)
        for combo in self.findChildren(QComboBox):
            combo.installEventFilter(self._wheel_blocker)

    # ═══════════════════════ UI ═══════════════════════
    def setup_ui(self):
        main = QHBoxLayout(self)
        main.setSpacing(15)
        main.setContentsMargins(10, 10, 10, 10)

        # ── 左侧 ──
        scroll = QScrollArea()
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}QScrollBar:vertical{background:transparent;width:8px;}QScrollBar::handle:vertical{background:#c0c0c0;border-radius:4px;min-height:30px;}QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setSpacing(10)

        desc = QLabel("计算各种设备的循环冷却水用水量，支持发酵罐/结晶罐/反应釜/脱色罐/换热器/冷凝器/蒸馏釜/气体冷却/直接热负荷 9 种模式，自动推荐管径。")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size:12px;padding:5px;")
        ll.addWidget(desc)

        ls = "font-weight:bold;padding-right:8px;"
        def lbl(t):
            w = QLabel(t)
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            w.setStyleSheet(ls)
            return w
        def hint(t):
            w = QLabel(t)
            w.setStyleSheet("font-style:italic;color:#666;")
            return w

        # ── 计算模式组 ──
        g1 = QGroupBox("计算模式")
        g1g = QGridLayout(g1)
        g1g.setHorizontalSpacing(10); g1g.setVerticalSpacing(10)
        g1g.setColumnStretch(0, 4); g1g.setColumnStretch(1, 8); g1g.setColumnStretch(2, 5)

        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet(COMBOBOX_STYLE)
        self.mode_combo.addItems([
            "请选择计算模式",
            "发酵罐",
            "结晶罐",
            "化学反应釜",
            "脱色罐",
            "换热器",
            "冷凝器",
            "蒸馏釜/蒸发器",
            "气体冷却器",
            "直接输入热负荷"
        ])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        g1g.addWidget(lbl("计算模式:"), 0, 0)
        g1g.addWidget(self.mode_combo, 0, 1)
        g1g.addWidget(hint("选择设备类型"), 0, 2)

        ll.addWidget(g1)

        # ── 热负荷参数组 ──
        self._group_load = QGroupBox("热负荷参数")
        glg = QGridLayout(self._group_load)
        glg.setHorizontalSpacing(10); glg.setVerticalSpacing(10)
        glg.setColumnStretch(0, 4); glg.setColumnStretch(1, 8); glg.setColumnStretch(2, 5)
        lr = 0

        # ---- 发酵罐参数 ----
        self._lbl_ferm_type = lbl("发酵类型:")
        self.ferm_type_combo = QComboBox()
        self.ferm_type_combo.setStyleSheet(COMBOBOX_STYLE)
        self.ferm_type_combo.addItems(list(self.FERM_TYPES.keys()))
        self.ferm_type_combo.currentTextChanged.connect(self._on_ferm_type_changed)
        self._hint_ferm_type = hint("选择后自动填充产热率")
        glg.addWidget(self._lbl_ferm_type, lr, 0)
        glg.addWidget(self.ferm_type_combo, lr, 1)
        glg.addWidget(self._hint_ferm_type, lr, 2); lr += 1

        self._lbl_heat_rate = lbl("产热率:")
        self.heat_rate_input = QLineEdit("15")
        self.heat_rate_input.setValidator(QDoubleValidator(0.1, 100, 1))
        self._hint_heat_rate = hint("kJ/(L·h)")
        glg.addWidget(self._lbl_heat_rate, lr, 0)
        glg.addWidget(self.heat_rate_input, lr, 1)
        glg.addWidget(self._hint_heat_rate, lr, 2); lr += 1

        self._lbl_vol = lbl("工作容积:")
        self.work_vol_input = QLineEdit("100")
        self.work_vol_input.setValidator(QDoubleValidator(0.1, 10000, 2))
        self._hint_vol = hint("m³")
        glg.addWidget(self._lbl_vol, lr, 0)
        glg.addWidget(self.work_vol_input, lr, 1)
        glg.addWidget(self._hint_vol, lr, 2); lr += 1

        self._lbl_stir = lbl("搅拌功率:")
        self.stir_power_input = QLineEdit("55")
        self.stir_power_input.setValidator(QDoubleValidator(0, 10000, 1))
        self._hint_stir = hint("kW, 可选")
        glg.addWidget(self._lbl_stir, lr, 0)
        glg.addWidget(self.stir_power_input, lr, 1)
        glg.addWidget(self._hint_stir, lr, 2); lr += 1

        # ---- 反应釜参数 ----
        self._lbl_rxn_heat = lbl("反应热:")
        self.rxn_heat_input = QLineEdit("200")
        self.rxn_heat_input.setValidator(QDoubleValidator(-10000, 100000, 1))
        self._hint_rxn_heat = hint("kW, +放热/-吸热")
        glg.addWidget(self._lbl_rxn_heat, lr, 0)
        glg.addWidget(self.rxn_heat_input, lr, 1)
        glg.addWidget(self._hint_rxn_heat, lr, 2); lr += 1

        # ---- 换热器/冷凝器 ----
        self._lbl_heat_load = lbl("热负荷:")
        self.heat_load_input = QLineEdit("500")
        self.heat_load_input.setValidator(QDoubleValidator(0.1, 100000, 1))
        self._hint_heat_load = hint("kW")
        glg.addWidget(self._lbl_heat_load, lr, 0)
        glg.addWidget(self.heat_load_input, lr, 1)
        glg.addWidget(self._hint_heat_load, lr, 2); lr += 1

        # ---- 冷凝器 ----
        self._lbl_cond_rate = lbl("冷凝量:")
        self.cond_rate_input = QLineEdit("2000")
        self.cond_rate_input.setValidator(QDoubleValidator(0.1, 1e6, 1))
        self._hint_cond_rate = hint("kg/h")
        glg.addWidget(self._lbl_cond_rate, lr, 0)
        glg.addWidget(self.cond_rate_input, lr, 1)
        glg.addWidget(self._hint_cond_rate, lr, 2); lr += 1

        self._lbl_latent = lbl("汽化潜热:")
        self.latent_heat_input = QLineEdit("2260")
        self.latent_heat_input.setValidator(QDoubleValidator(100, 10000, 1))
        self._hint_latent_c = hint("kJ/kg, 水=2260")
        glg.addWidget(self._lbl_latent, lr, 0)
        glg.addWidget(self.latent_heat_input, lr, 1)
        glg.addWidget(self._hint_latent_c, lr, 2); lr += 1

        # ---- 气体冷却器 ----
        self._lbl_gas_rate = lbl("气体流量:")
        self.gas_rate_input = QLineEdit("5000")
        self.gas_rate_input.setValidator(QDoubleValidator(0.1, 1e6, 1))
        self._hint_gas_rate = hint("kg/h")
        glg.addWidget(self._lbl_gas_rate, lr, 0)
        glg.addWidget(self.gas_rate_input, lr, 1)
        glg.addWidget(self._hint_gas_rate, lr, 2); lr += 1

        self._lbl_gas_cp = lbl("气体比热容:")
        self.gas_cp_combo = QComboBox()
        self.gas_cp_combo.setStyleSheet(COMBOBOX_STYLE)
        self.gas_cp_combo.addItems(list(self.GAS_CP.keys()))
        self.gas_cp_combo.currentTextChanged.connect(self._on_gas_cp_changed)
        self._hint_gas_cp = hint("kJ/(kg·°C)")
        glg.addWidget(self._lbl_gas_cp, lr, 0)
        glg.addWidget(self.gas_cp_combo, lr, 1)
        glg.addWidget(self._hint_gas_cp, lr, 2); lr += 1

        self._lbl_gas_tin = lbl("气体进口温度:")
        self.gas_tin_input = QLineEdit("120")
        self.gas_tin_input.setValidator(QDoubleValidator(-50, 2000, 1))
        self._hint_gas_tin = hint("°C")
        glg.addWidget(self._lbl_gas_tin, lr, 0)
        glg.addWidget(self.gas_tin_input, lr, 1)
        glg.addWidget(self._hint_gas_tin, lr, 2); lr += 1

        self._lbl_gas_tout = lbl("气体出口温度:")
        self.gas_tout_input = QLineEdit("40")
        self.gas_tout_input.setValidator(QDoubleValidator(-50, 2000, 1))
        self._hint_gas_tout = hint("°C")
        glg.addWidget(self._lbl_gas_tout, lr, 0)
        glg.addWidget(self.gas_tout_input, lr, 1)
        glg.addWidget(self._hint_gas_tout, lr, 2); lr += 1

        ll.addWidget(self._group_load)

        # ── 冷却水参数组 ──
        self._group_cw = QGroupBox("冷却水参数")
        gcg = QGridLayout(self._group_cw)
        gcg.setHorizontalSpacing(10); gcg.setVerticalSpacing(10)
        gcg.setColumnStretch(0, 4); gcg.setColumnStretch(1, 8); gcg.setColumnStretch(2, 5)

        cr = 0
        self.cw_preset_combo = QComboBox()
        self.cw_preset_combo.setStyleSheet(COMBOBOX_STYLE)
        self.cw_preset_combo.addItems(
            ["请选择冷却水类型"] + list(self.CW_PRESETS.keys()) + ["自定义水温"]
        )
        self.cw_preset_combo.currentTextChanged.connect(self._on_cw_preset_changed)
        gcg.addWidget(lbl("冷却水类型:"), cr, 0)
        gcg.addWidget(self.cw_preset_combo, cr, 1)
        gcg.addWidget(hint("预设进出水温度"), cr, 2); cr += 1

        self.cw_tin_input = QLineEdit("32")
        self.cw_tin_input.setValidator(QDoubleValidator(-10, 100, 1))
        gcg.addWidget(lbl("进水温度:"), cr, 0)
        gcg.addWidget(self.cw_tin_input, cr, 1)
        gcg.addWidget(hint("°C"), cr, 2); cr += 1

        self.cw_tout_input = QLineEdit("37")
        self.cw_tout_input.setValidator(QDoubleValidator(-10, 100, 1))
        gcg.addWidget(lbl("回水温度:"), cr, 0)
        gcg.addWidget(self.cw_tout_input, cr, 1)
        gcg.addWidget(hint("°C"), cr, 2); cr += 1

        self.safety_factor_input = QLineEdit("1.2")
        self.safety_factor_input.setValidator(QDoubleValidator(1.0, 3.0, 2))
        gcg.addWidget(lbl("安全系数:"), cr, 0)
        gcg.addWidget(self.safety_factor_input, cr, 1)
        gcg.addWidget(hint("通常 1.1~1.3"), cr, 2); cr += 1

        ll.addWidget(self._group_cw)

        # ── 计算按钮 ──
        calc_btn = QPushButton("计算")
        calc_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calc_btn.setMinimumHeight(50)
        calc_btn.setStyleSheet("QPushButton{background-color:#27ae60;color:white;border:none;border-radius:8px;font-weight:bold;}QPushButton:hover{background-color:#219955;}")
        calc_btn.clicked.connect(self.calculate)
        ll.addWidget(calc_btn)

        # ── 底部按钮 ──
        bl = QHBoxLayout()
        for name, color, hover, cb in [
            ("清空", "#95a5a6", "#7f8c8d", self.clear_inputs),
            ("下载计算书(TXT)", "#3498db", "#2980b9", self.download_txt_report),
            ("下载计算书(PDF)", "#e74c3c", "#c0392b", self.download_pdf_report),
        ]:
            btn = QPushButton(name)
            btn.clicked.connect(cb)
            btn.setMinimumHeight(50)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet(f"QPushButton{{background-color:{color};color:white;border:none;border-radius:6px;padding:8px;font-weight:bold;}}QPushButton:hover{{background-color:{hover};}}")
            bl.addWidget(btn)
        ll.addLayout(bl)
        ll.addStretch()

        scroll.setWidget(lw)

        # ── 右侧 ──
        rw = QWidget()
        rw.setMinimumWidth(300)
        rl = QVBoxLayout(rw)
        rl.setSpacing(15)

        self.svg_widget = QSvgWidget()
        self.svg_widget.setMinimumHeight(220)
        self.svg_widget.setMaximumHeight(280)
        self.svg_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rl.addWidget(self.svg_widget)
        self.svg_widget.renderer().setAspectRatioMode(Qt.KeepAspectRatio)

        rg = QGroupBox("计算结果")
        rvl = QVBoxLayout(rg)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setStyleSheet("QTextEdit{border:1px solid #888;border-radius:6px;padding:8px;min-height:500px;}")
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        rvl.addWidget(self.result_text)
        rl.addWidget(rg)

        main.addWidget(scroll, 2)
        main.addWidget(rw, 1)

    # ═══════════════════════ 模式切换 ═══════════════════════
    def _on_mode_changed(self, mode):
        """根据模式显隐热负荷参数行，并适配标签文字"""
        rows = {
            "ferm_type":  (self._lbl_ferm_type, self.ferm_type_combo, self._hint_ferm_type),
            "heat_rate":  (self._lbl_heat_rate, self.heat_rate_input, self._hint_heat_rate),
            "work_vol":   (self._lbl_vol, self.work_vol_input, self._hint_vol),
            "stir_power": (self._lbl_stir, self.stir_power_input, self._hint_stir),
            "rxn_heat":   (self._lbl_rxn_heat, self.rxn_heat_input, self._hint_rxn_heat),
            "heat_load":  (self._lbl_heat_load, self.heat_load_input, self._hint_heat_load),
            "cond_rate":  (self._lbl_cond_rate, self.cond_rate_input, self._hint_cond_rate),
            "latent":     (self._lbl_latent, self.latent_heat_input, self._hint_latent_c),
            "gas_rate":   (self._lbl_gas_rate, self.gas_rate_input, self._hint_gas_rate),
            "gas_cp":     (self._lbl_gas_cp, self.gas_cp_combo, self._hint_gas_cp),
            "gas_tin":    (self._lbl_gas_tin, self.gas_tin_input, self._hint_gas_tin),
            "gas_tout":   (self._lbl_gas_tout, self.gas_tout_input, self._hint_gas_tout),
        }
        for trio in rows.values():
            for w in trio:
                w.setVisible(False)

        visible = []
        if mode == "发酵罐":
            visible = ["ferm_type", "heat_rate", "work_vol", "stir_power"]
        elif mode == "结晶罐":
            visible = ["rxn_heat", "work_vol", "stir_power"]
        elif mode == "化学反应釜":
            visible = ["rxn_heat", "work_vol", "stir_power"]
        elif mode == "脱色罐":
            visible = ["heat_load", "work_vol", "stir_power"]
        elif mode == "换热器":
            visible = ["heat_load"]
        elif mode == "冷凝器":
            visible = ["cond_rate", "latent"]
        elif mode == "蒸馏釜/蒸发器":
            visible = ["cond_rate", "latent"]
        elif mode == "气体冷却器":
            visible = ["gas_rate", "gas_cp", "gas_tin", "gas_tout"]
        elif mode == "直接输入热负荷":
            visible = ["heat_load"]

        for key in visible:
            for w in rows[key]:
                w.setVisible(True)

        # ── 标签适配 ──
        label_map = {
            "发酵罐":       ("反应热:", "kW, +放热/-吸热"),
            "结晶罐":       ("结晶热负荷:", "kW, 含结晶放热+显热降温"),
            "化学反应釜":   ("反应热:", "kW, +放热/-吸热"),
            "脱色罐":       ("散热+搅拌热:", "kW, 保温散热+搅拌功率"),
            "换热器":       ("热负荷:", "kW"),
            "冷凝器":       ("冷凝量:", "kg/h"),
            "蒸馏釜/蒸发器": ("蒸发量:", "kg/h"),
            "气体冷却器":   ("气体流量:", "kg/h"),
            "直接输入热负荷":("热负荷:", "kW"),
        }
        if mode in label_map:
            l_text, h_text = label_map[mode]
            if hasattr(self, "_lbl_heat_load"):
                # 找当前可见的第一个负荷标签并适配
                if "rxn_heat" in visible:
                    self._lbl_rxn_heat.setText(l_text)
                    self._hint_rxn_heat.setText(h_text)
                elif "heat_load" in visible:
                    self._lbl_heat_load.setText(l_text)
                    self._hint_heat_load.setText(h_text)
                elif "cond_rate" in visible:
                    self._lbl_cond_rate.setText(l_text)
                    self._hint_cond_rate.setText(h_text)
                elif "gas_rate" in visible:
                    self._lbl_gas_rate.setText(l_text)
                    self._hint_gas_rate.setText(h_text)

        if hasattr(self, "_group_load"):
            group_titles = {
                "发酵罐": "发酵罐参数", "结晶罐": "结晶罐参数",
                "化学反应釜": "反应釜参数", "脱色罐": "脱色罐参数",
                "换热器": "热负荷参数", "冷凝器": "冷凝器参数",
                "蒸馏釜/蒸发器": "蒸馏釜/蒸发器参数",
                "气体冷却器": "气体冷却器参数", "直接输入热负荷": "热负荷参数",
            }
            self._group_load.setTitle(group_titles.get(mode, "热负荷参数"))

        self._on_ferm_type_changed(self.ferm_type_combo.currentText())

    def _on_ferm_type_changed(self, text):
        if text in self.FERM_TYPES:
            lo, hi = self.FERM_TYPES[text]
            if lo > 0:
                self.heat_rate_input.setText(f"{(lo + hi) / 2:.0f}")
                self.heat_rate_input.setToolTip(f"推荐范围: {lo}~{hi} kJ/(L·h)")

    def _on_gas_cp_changed(self, text):
        if text in self.GAS_CP and text != "请选择气体":
            pass  # 只做参考显示，不自动填入（比热容是下拉选择不是输入框）

    def _on_cw_preset_changed(self, text):
        if text in self.CW_PRESETS:
            tin, tout = self.CW_PRESETS[text]
            self.cw_tin_input.setText(str(tin))
            self.cw_tout_input.setText(str(tout))
        elif text == "自定义水温":
            self.cw_tin_input.clear()
            self.cw_tout_input.clear()

    # ═══════════════════════ 计算 ═══════════════════════
    def calculate(self):
        try:
            mode = self.mode_combo.currentText()
            if "请选择" in mode:
                self._show_error("请先选择计算模式")
                return

            cw_tin = float(self.cw_tin_input.text() or 32)
            cw_tout = float(self.cw_tout_input.text() or 37)
            safety = float(self.safety_factor_input.text() or 1.2)
            delta_t_cw = cw_tout - cw_tin
            if delta_t_cw <= 0:
                self._show_error("回水温度必须大于进水温度")
                return

            cp_water = 4.18  # kJ/(kg·°C)

            # ── 各模式热负荷计算 ──
            mode_labels = {}
            q_sources = []  # (描述, kW)

            if mode == "发酵罐":
                heat_rate = float(self.heat_rate_input.text() or 15)   # kJ/(L·h)
                work_vol = float(self.work_vol_input.text() or 100)    # m³
                stir_power = float(self.stir_power_input.text() or 0)  # kW
                ferm_type = self.ferm_type_combo.currentText()

                # 发酵代谢热：kJ/(L·h) × L → kJ/h → kW
                q_metab = heat_rate * work_vol * 1000 / 3600  # kW
                q_stir = stir_power * 0.7  # 70%搅拌功率转化为热
                q_total = q_metab + q_stir

                q_sources.append((f"发酵代谢热({ferm_type}): {heat_rate} kJ/(L·h) × {work_vol} m³", q_metab))
                if stir_power > 0:
                    q_sources.append((f"搅拌热: {stir_power} kW × 70%", q_stir))

                lo, hi = self.FERM_TYPES.get(ferm_type, (0, 0))
                if lo > 0:
                    mode_labels["_range"] = f"产热率参考范围: {lo}~{hi} kJ/(L·h)"

            elif mode == "化学反应釜":
                rxn_heat = float(self.rxn_heat_input.text() or 200)
                work_vol = float(self.work_vol_input.text() or 10)
                stir_power = float(self.stir_power_input.text() or 0)
                q_rxn = abs(rxn_heat)
                q_stir = stir_power * 0.7
                q_total = q_rxn + q_stir

                q_sources.append((f"反应热: {rxn_heat} kW (绝对值)", q_rxn))
                if stir_power > 0:
                    q_sources.append((f"搅拌热: {stir_power} kW × 70%", q_stir))

            elif mode == "结晶罐":
                rxn_heat = float(self.rxn_heat_input.text() or 200)
                work_vol = float(self.work_vol_input.text() or 10)
                stir_power = float(self.stir_power_input.text() or 0)
                q_rxn = abs(rxn_heat)
                q_stir = stir_power * 0.7
                q_total = q_rxn + q_stir

                q_sources.append((f"结晶热负荷(含放热+降温显热): {rxn_heat} kW", q_rxn))
                if stir_power > 0:
                    q_sources.append((f"搅拌热: {stir_power} kW × 70%", q_stir))
                mode_labels["_note"] = "提示: 结晶热≈60~100 kJ/kg结晶, 显热降温≈m×Cp×ΔT"

            elif mode == "脱色罐":
                heat_load = float(self.heat_load_input.text() or 15)
                work_vol = float(self.work_vol_input.text() or 10)
                stir_power = float(self.stir_power_input.text() or 0)
                q_stir = stir_power * 0.7
                q_total = heat_load + q_stir

                q_sources.append((f"保温散热: {heat_load} kW", heat_load))
                if stir_power > 0:
                    q_sources.append((f"搅拌热: {stir_power} kW × 70%", q_stir))
                mode_labels["_note"] = "提示: 保温散热≈罐体表面积×K×ΔT(内−外)"

            elif mode == "换热器":
                q_total = float(self.heat_load_input.text() or 500)
                q_sources.append(("换热器热负荷", q_total))

            elif mode == "冷凝器":
                cond_rate = float(self.cond_rate_input.text() or 2000)
                latent = float(self.latent_heat_input.text() or 2260)
                q_total = cond_rate * latent / 3600
                q_sources.append((f"冷凝热: {cond_rate} kg/h × {latent} kJ/kg", q_total))

            elif mode == "蒸馏釜/蒸发器":
                cond_rate = float(self.cond_rate_input.text() or 2000)
                latent = float(self.latent_heat_input.text() or 2260)
                q_total = cond_rate * latent / 3600
                q_sources.append((f"蒸发潜热: {cond_rate} kg/h × {latent} kJ/kg", q_total))

            elif mode == "气体冷却器":
                gas_rate = float(self.gas_rate_input.text() or 5000)
                gas_cp_text = self.gas_cp_combo.currentText()
                gas_cp = self.GAS_CP.get(gas_cp_text, 1.0)
                gas_tin = float(self.gas_tin_input.text() or 120)
                gas_tout = float(self.gas_tout_input.text() or 40)
                q_total = gas_rate * gas_cp * (gas_tin - gas_tout) / 3600
                if q_total < 0:
                    self._show_error("气体出口温度必须小于进口温度")
                    return
                q_sources.append((f"气体冷却: {gas_rate} kg/h × {gas_cp} × ({gas_tin}-{gas_tout})°C", q_total))

            elif mode == "直接输入热负荷":
                q_total = float(self.heat_load_input.text() or 500)
                q_sources.append(("直接热负荷", q_total))

            # ── 循环水量计算 ──
            q_with_safety = q_total * safety
            m_cw_kgs = q_with_safety / (cp_water * delta_t_cw)    # kg/s
            v_cw_m3h = m_cw_kgs * 3.6                            # m³/h
            v_cw_Lh = v_cw_m3h * 1000                            # L/h

            # ── 推荐管径 ──
            rec_dn = self._recommend_pipe(v_cw_m3h)

            self._last_result = {
                "q_total": q_total, "q_with_safety": q_with_safety,
                "m_cw_kgs": m_cw_kgs, "v_cw_m3h": v_cw_m3h,
                "v_cw_Lh": v_cw_Lh, "rec_dn": rec_dn,
                "delta_t_cw": delta_t_cw, "safety": safety,
                "cw_tin": cw_tin, "cw_tout": cw_tout,
                "mode": mode, "q_sources": q_sources,
                "mode_labels": mode_labels,
            }

            self._display()
            self._update_svg_diagram()

        except ValueError as e:
            self._show_error(f"输入错误：{e}")
        except Exception as e:
            self._show_error(f"计算错误：{e}")

    def _recommend_pipe(self, v_m3h):
        """根据流量推荐管径"""
        for dn in self.STANDARD_PIPES:
            area = math.pi * (dn / 1000) ** 2 / 4
            v_actual = (v_m3h / 3600) / area  # m/s
            # 流速在合理范围
            if dn < 50 and v_actual <= 2.5:
                return f"DN{dn} (流速 {v_actual:.1f} m/s)"
            if 50 <= dn < 100 and v_actual <= 2.0:
                return f"DN{dn} (流速 {v_actual:.1f} m/s)"
            if dn >= 100 and v_actual <= 3.0:
                return f"DN{dn} (流速 {v_actual:.1f} m/s)"
        return f"DN500 (流速 {(v_m3h/3600)/(math.pi*0.25)} m/s)"

    # ═══════════════════════ 显示 ═══════════════════════
    def _display(self):
        r = self._last_result
        lines = [
            "=" * 55,
            "        循环冷却水用水量计算",
            "=" * 55,
            "",
            f"【计算模式】{r['mode']}",
            "",
            "【热负荷来源】",
        ]
        for desc, val in r["q_sources"]:
            lines.append(f"  {desc} = {val:.1f} kW")
        lines.append(f"  合计: {r['q_total']:.1f} kW")

        if "_range" in r.get("mode_labels", {}):
            lines.append(f"  {r['mode_labels']['_range']}")
        if "_note" in r.get("mode_labels", {}):
            lines.append(f"  {r['mode_labels']['_note']}")

        lines += [
            f"  安全系数: ×{r['safety']}",
            f"  设计热负荷: {r['q_with_safety']:.1f} kW",
            "",
            "【冷却水参数】",
            f"  进水温度: {r['cw_tin']} °C",
            f"  回水温度: {r['cw_tout']} °C",
            f"  温差 ΔT: {r['delta_t_cw']} °C",
            "",
            "【计算结果】",
            f"  ★ 循环水量: {r['v_cw_m3h']:.2f} m³/h",
            f"                = {r['v_cw_Lh']:.0f} L/h",
            f"                = {r['m_cw_kgs']:.2f} kg/s",
            f"  ★ 推荐管径: {r['rec_dn']}",
            "",
            "【计算公式】",
            "  Q = Σ(q_source) × 安全系数",
            f"  = {r['q_total']:.1f} × {r['safety']}",
            f"  = {r['q_with_safety']:.1f} kW",
            "",
            "  m_cw = Q / (cp × ΔT)",
            f"       = {r['q_with_safety']:.1f} / (4.18 × {r['delta_t_cw']})",
            f"       = {r['m_cw_kgs']:.2f} kg/s",
            "",
            "  V_cw = m_cw × 3.6",
            f"       = {r['v_cw_m3h']:.2f} m³/h",
            "",
            "【选型建议】",
            f"  1. 循环水总管径 ≥ {r['rec_dn'].split()[0]}",
            "  2. 选用冷却塔时，按循环水量 × 1.1 选型",
            "  3. 冷冻水系统需校核制冷机组冷量",
            "  4. 多台设备并联时，需累加循环水量",
            "",
            "  * 计算结果仅供参考，实际工程由专业工程师确认。",
            "=" * 55,
        ]
        self.result_text.setPlainText("\n".join(lines))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"错误：{msg}")

    # ═══════════════════════ 清空 ═══════════════════════
    def clear_inputs(self):
        self.mode_combo.setCurrentIndex(0)
        self.ferm_type_combo.setCurrentIndex(0)
        self.heat_rate_input.setText("15")
        self.work_vol_input.setText("100")
        self.stir_power_input.setText("55")
        self.rxn_heat_input.setText("200")
        self.heat_load_input.setText("500")
        self.cond_rate_input.setText("2000")
        self.latent_heat_input.setText("2260")
        self.gas_rate_input.setText("5000")
        self.gas_cp_combo.setCurrentIndex(0)
        self.gas_tin_input.setText("120")
        self.gas_tout_input.setText("40")
        self.cw_preset_combo.setCurrentIndex(0)
        self.cw_tin_input.setText("32")
        self.cw_tout_input.setText("37")
        self.safety_factor_input.setText("1.2")
        self.result_text.clear()
        self._last_result = {}
        self._on_mode_changed(self.mode_combo.currentText())

    # ═══════════════════════ 历史 ═══════════════════════
    def _get_history_data(self):
        r = self._last_result
        return {
            "inputs": {
                "计算模式": r.get("mode", ""),
                "设计热负荷_kW": round(r.get("q_with_safety", 0), 1),
                "进水温度_°C": r.get("cw_tin", 0),
                "回水温度_°C": r.get("cw_tout", 0),
            },
            "outputs": {
                "循环水量_m3h": round(r.get("v_cw_m3h", 0), 2),
                "推荐管径": r.get("rec_dn", ""),
            }
        }

    def get_project_info(self):
        return {"calculator": "CoolingWaterCalculator", "name": "循环水计算"}

    def generate_report(self):
        return self.result_text.toPlainText()

    # ═══════════════════════ SVG ═══════════════════════
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        e = 'font-weight="bold"' if bold else ""
        a = 'text-anchor="middle"' if center else ""
        return f'<text x="{x}" y="{y}" {a} font-size="{size}" fill="{color}" {e}>{text}</text>'

    def _generate_cw_svg(self, **kw):
        w, h = 380, 280
        p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']

        # 设备（左侧矩形）
        eq_x, eq_y, eq_w, eq_h = 40, 60, 80, 100
        p.append(f'<rect x="{eq_x}" y="{eq_y}" width="{eq_w}" height="{eq_h}" '
                 f'fill="#e8edf2" stroke="#4a6fa5" stroke-width="2" rx="4"/>')
        p.append(self._text(eq_x + eq_w/2, eq_y + eq_h/2, "设备", size=10, color="#4a6fa5", bold=True))
        p.append(self._text(eq_x + eq_w/2, eq_y - 10, "热负荷 Q", size=9, color="#e74c3c", bold=True))

        # 冷却水进管（下方）
        cw_in_y = eq_y + eq_h + 30
        p.append(f'<line x1="{eq_x + eq_w/2}" y1="{eq_y + eq_h}" x2="{eq_x + eq_w/2}" y2="{cw_in_y}" '
                 f'stroke="#3498db" stroke-width="6"/>')
        p.append(f'<line x1="{eq_x + eq_w/2 - 60}" y1="{cw_in_y}" x2="{eq_x + eq_w/2}" y2="{cw_in_y}" '
                 f'stroke="#3498db" stroke-width="6" marker-end="url(#arrow_in)"/>')
        p.append(self._text(eq_x + eq_w/2 - 30, cw_in_y + 18, "进水", size=9, color="#3498db", bold=True))
        tin_val = kw.get("tin", "")
        if tin_val:
            p.append(self._text(eq_x + eq_w/2 - 30, cw_in_y + 32, f"{tin_val}°C", size=8, color="#3498db"))

        # 冷却水出管（上方）
        p.append(f'<line x1="{eq_x + eq_w/2}" y1="{eq_y}" x2="{eq_x + eq_w/2}" y2="{eq_y - 25}" '
                 f'stroke="#e74c3c" stroke-width="6"/>')
        p.append(f'<line x1="{eq_x + eq_w/2}" y1="{eq_y - 25}" x2="{eq_x + eq_w/2 + 60}" y2="{eq_y - 25}" '
                 f'stroke="#e74c3c" stroke-width="6" marker-end="url(#arrow_out)"/>')
        p.append(self._text(eq_x + eq_w/2 + 30, eq_y - 35, "回水", size=9, color="#e74c3c", bold=True))
        tout_val = kw.get("tout", "")
        if tout_val:
            p.append(self._text(eq_x + eq_w/2 + 30, eq_y - 22, f"{tout_val}°C", size=8, color="#e74c3c"))

        # 右侧流量标注
        flow_val = kw.get("flow", "")
        temp_val = kw.get("delta_t", "")
        if flow_val:
            p.append(self._text(260, eq_y + 20, f"循环水量:", size=10, color="#555", bold=True, center=False))
            p.append(self._text(260, eq_y + 35, f"{flow_val} m³/h", size=12, color="#27ae60", bold=True, center=False))
        if temp_val:
            p.append(self._text(260, eq_y + 55, f"ΔT={temp_val}°C", size=10, color="#e67e22", bold=True, center=False))

        p.append(self._text(w/2, 12, "循环冷却水示意", size=10, color="#4a6fa5", bold=True))

        p.append('<defs>'
                 '<marker id="arrow_in" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto">'
                 '<path d="M0,0 L8,4 L0,8 Z" fill="#3498db"/></marker>'
                 '<marker id="arrow_out" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto">'
                 '<path d="M0,0 L8,4 L0,8 Z" fill="#e74c3c"/></marker>'
                 '</defs></svg>')
        return "".join(p)

    def _update_svg_diagram(self):
        try:
            kw = {}
            if self._last_result:
                kw["flow"] = f"{self._last_result.get('v_cw_m3h', 0):.2f}"
                kw["tin"] = str(self._last_result.get("cw_tin", ""))
                kw["tout"] = str(self._last_result.get("cw_tout", ""))
                kw["delta_t"] = str(self._last_result.get("delta_t_cw", 0))
            s = self._generate_cw_svg(**kw)
            self.svg_widget.load(s.encode("utf-8"))
        except:
            pass

    # ═══════════════════════ 报告 ═══════════════════════
    def download_txt_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先计算，再下载报告。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存TXT报告", "循环水计算报告.txt", "文本文件 (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "成功", f"报告已保存：\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败：{e}")

    def download_pdf_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先计算，再下载PDF。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存PDF报告", "循环水计算报告.pdf", "PDF文件 (*.pdf)")
        if not path:
            return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph
            from reportlab.lib.enums import TA_LEFT
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            font_paths = ["C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simsun.ttc"]
            font_name = "Helvetica"
            for fp in font_paths:
                if os.path.exists(fp):
                    try:
                        pdfmetrics.registerFont(TTFont("CF", fp))
                        font_name = "CF"
                        break
                    except: continue
            doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
            st = ParagraphStyle("Body", fontName=font_name, fontSize=10, leading=16, alignment=TA_LEFT)
            story = []
            for line in content.split("\n"):
                safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(safe if safe.strip() else "&nbsp;", st))
            doc.build(story)
            QMessageBox.information(self, "成功", f"PDF已保存：\n{path}")
        except ImportError:
            QMessageBox.critical(self, "错误", "缺少 reportlab 库，请运行：pip install reportlab")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"PDF生成失败：{e}")


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = CoolingWaterCalculator()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
