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
import sys
from pathlib import Path

# DOCX 报告导出
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.docx_utils import ReportExporter

COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #888;
        border-radius: 4px;
        padding: 6px 10px;
    }
    QComboBox QAbstractItemView {
        border: 1px solid #888;
        selection-background-color: #3498db;
        selection-color: black;
    }
    QComboBox QAbstractItemView::item {
        padding: 3px 8px;
    }
"""

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

# ── 标准安全阀喉径规格 ──
STANDARD_VALVES = [
    ("DN15", 11, 95),
    ("DN20", 16, 201),
    ("DN25", 19, 284),
    ("DN32", 23, 415),
    ("DN40", 26, 531),
    ("DN50", 33, 855),
    ("DN65", 47, 1735),
    ("DN80", 52, 2124),
    ("DN100", 68, 3631),
    ("DN125", 83, 5410),
    ("DN150", 102, 8171),
    ("DN200", 145, 16513),
]

class SafetyValveCalculator(QWidget):
    """安全阀泄放面积计算 — 模式驱动版"""

    # ── 6种计算类型及其默认参数 ──
    MODE_CONFIG = {
        "饱和水蒸汽":    {"gamma": 1.33, "mw": 18, "z": 1.0, "auto_temp": True,  "fire": False},
        "过热水蒸汽":    {"gamma": 1.30, "mw": 18, "z": 1.0, "auto_temp": False, "fire": False},
        "气体":          {"gamma": 1.30, "mw": 16, "z": 1.0, "auto_temp": False, "fire": False},
        "空气":          {"gamma": 1.40, "mw": 29, "z": 1.0, "auto_temp": False, "fire": False},
        "火灾工况(已知润湿面积)": {"gamma": 1.33, "mw": 18, "z": 1.0, "auto_temp": True,  "fire": True, "known_area": True},
        "火灾工况(未知润湿面积)": {"gamma": 1.33, "mw": 18, "z": 1.0, "auto_temp": True,  "fire": True, "known_area": False},
    }

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_result = {}
        self._last_params = {}
        self._widget_groups = {}  # mode→[widgets] mapping
        self.setup_ui()
        self._on_mode_changed(self.mode_combo.currentText())
        self._update_svg_diagram()

        self._wheel_blocker = ComboBoxWheelBlocker(self)
        for combo in self.findChildren(QComboBox):
            combo.installEventFilter(self._wheel_blocker)

    def init_data_manager(self):
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception:
            self.data_manager = None

    # ═══════════════════════════ UI ═══════════════════════════
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
        ll.setSpacing(12)

        # 说明
        desc = QLabel("计算安全阀喉径面积，依据 ASME VIII / API 520。6种计算类型，支持已知/未知泄放量。")
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
            w.setStyleSheet("font-style:italic;")
            return w

        # ── 计算条件组 ──
        g1 = QGroupBox("计算条件")
        g1g = QGridLayout(g1)
        g1g.setHorizontalSpacing(10); g1g.setVerticalSpacing(10)
        g1g.setColumnStretch(0, 4); g1g.setColumnStretch(1, 8); g1g.setColumnStretch(2, 5)
        r = 0

        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet(COMBOBOX_STYLE)
        self.mode_combo.addItems(list(self.MODE_CONFIG.keys()))
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        g1g.addWidget(lbl("计算类型:"), r, 0)
        g1g.addWidget(self.mode_combo, r, 1)
        g1g.addWidget(hint("选择工况类型"), r, 2); r += 1

        # 泄放量来源
        self.relief_source_combo = QComboBox()
        self.relief_source_combo.setStyleSheet(COMBOBOX_STYLE)
        self.relief_source_combo.addItems(["已知泄放量", "未知泄放量"])
        self.relief_source_combo.currentTextChanged.connect(self._on_source_changed)
        self._relief_source_label = lbl("泄放量来源:")
        self._relief_source_hint = hint("已知/未知切换")
        g1g.addWidget(self._relief_source_label, r, 0)
        g1g.addWidget(self.relief_source_combo, r, 1)
        g1g.addWidget(self._relief_source_hint, r, 2); r += 1

        # 整定压力
        self.ps_input = QLineEdit("1.0")
        self.ps_input.setValidator(QDoubleValidator(0.01, 100, 3))
        g1g.addWidget(lbl("整定压力 Ps (G):"), r, 0)
        g1g.addWidget(self.ps_input, r, 1)
        g1g.addWidget(hint("MPa (表压)"), r, 2); r += 1

        # 最高允许工作压力
        self.mawp_input = QLineEdit("1.1")
        self.mawp_input.setValidator(QDoubleValidator(0.01, 100, 3))
        g1g.addWidget(lbl("最高允许工作压力 (G):"), r, 0)
        g1g.addWidget(self.mawp_input, r, 1)
        g1g.addWidget(hint("MPa (表压), 超压基准"), r, 2); r += 1

        # 流量系数 Kd
        self.kd_type_combo = QComboBox()
        self.kd_type_combo.setStyleSheet(COMBOBOX_STYLE)
        self.kd_type_combo.addItems([
            "请选择阀型",
            "全启式 (0.65)",
            "带调节圈微启式 (0.45)",
            "不带调节圈微启式 (0.30)",
        ])
        self.kd_type_combo.currentTextChanged.connect(self._on_kd_type_changed)
        self.kd_input = QLineEdit("0.65")
        self.kd_input.setValidator(QDoubleValidator(0.1, 1.0, 3))
        g1g.addWidget(lbl("流量系数 Kd:"), r, 0)
        g1g.addWidget(self.kd_input, r, 1)
        g1g.addWidget(self.kd_type_combo, r, 2); r += 1

        ll.addWidget(g1)

        # ── 泄放量参数组 ──
        self._group_relief = QGroupBox("泄放量参数")
        grg = QGridLayout(self._group_relief)
        grg.setHorizontalSpacing(10); grg.setVerticalSpacing(10)
        grg.setColumnStretch(0, 4); grg.setColumnStretch(1, 8); grg.setColumnStretch(2, 5)
        rr = 0

        # 已知泄放量
        self._lbl_flow = lbl("泄放量 W:")
        self.relief_flow_input = QLineEdit("1000")
        self.relief_flow_input.setValidator(QDoubleValidator(0.001, 1e8, 1))
        self._hint_flow = hint("kg/h")
        grg.addWidget(self._lbl_flow, rr, 0)
        grg.addWidget(self.relief_flow_input, rr, 1)
        grg.addWidget(self._hint_flow, rr, 2); rr += 1

        # 未知泄放量 - 管道参数
        self._lbl_pipe_d = lbl("管道内径:")
        self.pipe_d_input = QLineEdit("50")
        self.pipe_d_input.setValidator(QDoubleValidator(1, 2000, 1))
        self._hint_pipe_d = hint("mm")
        grg.addWidget(self._lbl_pipe_d, rr, 0)
        grg.addWidget(self.pipe_d_input, rr, 1)
        grg.addWidget(self._hint_pipe_d, rr, 2); rr += 1

        self._lbl_pipe_v = lbl("气体流速:")
        self.pipe_v_input = QLineEdit("30")
        self.pipe_v_input.setValidator(QDoubleValidator(1, 300, 1))
        self._hint_pipe_v = hint("m/s")
        grg.addWidget(self._lbl_pipe_v, rr, 0)
        grg.addWidget(self.pipe_v_input, rr, 1)
        grg.addWidget(self._hint_pipe_v, rr, 2); rr += 1

        # 火灾参数
        self._lbl_wet = lbl("润湿面积:")
        self.wetted_area_input = QLineEdit("50")
        self.wetted_area_input.setValidator(QDoubleValidator(0.1, 10000, 1))
        self._hint_wet = hint("m²")
        grg.addWidget(self._lbl_wet, rr, 0)
        grg.addWidget(self.wetted_area_input, rr, 1)
        grg.addWidget(self._hint_wet, rr, 2); rr += 1

        self._lbl_env = lbl("环境因子 F:")
        self.env_factor_input = QLineEdit("1.0")
        self.env_factor_input.setValidator(QDoubleValidator(0.1, 2.0, 2))
        self._hint_env = hint("裸露=1.0, 保温=0.3")
        grg.addWidget(self._lbl_env, rr, 0)
        grg.addWidget(self.env_factor_input, rr, 1)
        grg.addWidget(self._hint_env, rr, 2); rr += 1

        self._lbl_latent = lbl("汽化潜热:")
        self.latent_heat_input = QLineEdit("2260")
        self.latent_heat_input.setValidator(QDoubleValidator(100, 10000, 1))
        self._hint_latent = hint("kJ/kg, 水≈2260")
        grg.addWidget(self._lbl_latent, rr, 0)
        grg.addWidget(self.latent_heat_input, rr, 1)
        grg.addWidget(self._hint_latent, rr, 2); rr += 1

        # 火灾未知 - 容器参数
        self._lbl_vessel_d = lbl("容器直径:")
        self.vessel_d_input = QLineEdit("2.0")
        self.vessel_d_input.setValidator(QDoubleValidator(0.1, 50, 2))
        self._hint_vessel_d = hint("m")
        grg.addWidget(self._lbl_vessel_d, rr, 0)
        grg.addWidget(self.vessel_d_input, rr, 1)
        grg.addWidget(self._hint_vessel_d, rr, 2); rr += 1

        self._lbl_vessel_l = lbl("容器长度/高度:")
        self.vessel_l_input = QLineEdit("5.0")
        self.vessel_l_input.setValidator(QDoubleValidator(0.1, 100, 2))
        self._hint_vessel_l = hint("m")
        grg.addWidget(self._lbl_vessel_l, rr, 0)
        grg.addWidget(self.vessel_l_input, rr, 1)
        grg.addWidget(self._hint_vessel_l, rr, 2); rr += 1

        self._lbl_vessel_type = lbl("容器类型:")
        self.vessel_type_combo = QComboBox()
        self.vessel_type_combo.setStyleSheet(COMBOBOX_STYLE)
        self.vessel_type_combo.addItems(["卧式", "立式", "球罐"])
        self._hint_vessel_type = hint("")
        grg.addWidget(self._lbl_vessel_type, rr, 0)
        grg.addWidget(self.vessel_type_combo, rr, 1)
        grg.addWidget(self._hint_vessel_type, rr, 2); rr += 1

        ll.addWidget(self._group_relief)

        # ── 介质参数组 ──
        self._group_fluid = QGroupBox("介质参数")
        gfg = QGridLayout(self._group_fluid)
        gfg.setHorizontalSpacing(10); gfg.setVerticalSpacing(10)
        gfg.setColumnStretch(0, 4); gfg.setColumnStretch(1, 8); gfg.setColumnStretch(2, 5)
        fr = 0

        self._lbl_mw = lbl("分子量 M:")
        self.mw_input = QLineEdit("18")
        self.mw_input.setValidator(QDoubleValidator(1, 500, 2))
        self._hint_mw = hint("g/mol")
        gfg.addWidget(self._lbl_mw, fr, 0)
        gfg.addWidget(self.mw_input, fr, 1)
        gfg.addWidget(self._hint_mw, fr, 2); fr += 1

        self._lbl_gamma = lbl("绝热指数 γ:")
        self.gamma_input = QLineEdit("1.3")
        self.gamma_input.setValidator(QDoubleValidator(1.0, 2.0, 3))
        self._hint_gamma = hint("空气=1.4")
        gfg.addWidget(self._lbl_gamma, fr, 0)
        gfg.addWidget(self.gamma_input, fr, 1)
        gfg.addWidget(self._hint_gamma, fr, 2); fr += 1

        self._lbl_z = lbl("压缩因子 Z:")
        self.z_input = QLineEdit("1.0")
        self.z_input.setValidator(QDoubleValidator(0.1, 2.0, 3))
        self._hint_z = hint("理想气体=1.0")
        gfg.addWidget(self._lbl_z, fr, 0)
        gfg.addWidget(self.z_input, fr, 1)
        gfg.addWidget(self._hint_z, fr, 2); fr += 1

        self._lbl_temp = lbl("操作温度 T:")
        self.temp_input = QLineEdit("150")
        self.temp_input.setValidator(QDoubleValidator(-273, 2000, 1))
        self._hint_temp = hint("°C")
        gfg.addWidget(self._lbl_temp, fr, 0)
        gfg.addWidget(self.temp_input, fr, 1)
        gfg.addWidget(self._hint_temp, fr, 2); fr += 1

        # 超压百分比
        self._lbl_over = lbl("超压百分比:")
        self.overpressure_input = QLineEdit("10")
        self.overpressure_input.setValidator(QDoubleValidator(5, 100, 1))
        self._hint_over = hint("通常10%, 火灾21%")
        gfg.addWidget(self._lbl_over, fr, 0)
        gfg.addWidget(self.overpressure_input, fr, 1)
        gfg.addWidget(self._hint_over, fr, 2); fr += 1

        # 背压（可选）
        self._lbl_back = lbl("背压 (表):")
        self.back_pressure_input = QLineEdit("0")
        self.back_pressure_input.setValidator(QDoubleValidator(0, 50, 3))
        self._hint_back = hint("MPa, 0=排大气")
        gfg.addWidget(self._lbl_back, fr, 0)
        gfg.addWidget(self.back_pressure_input, fr, 1)
        gfg.addWidget(self._hint_back, fr, 2); fr += 1

        ll.addWidget(self._group_fluid)

        # ── 计算按钮 ──
        calc_btn = QPushButton("计算")
        calc_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calc_btn.setMinimumHeight(50)
        calc_btn.setStyleSheet("QPushButton{background-color:#27ae60;color:white;border:none;border-radius:8px;font-weight:bold;}QPushButton:hover{background-color:#219955;}")
        calc_btn.clicked.connect(self.calculate)
        ll.addWidget(calc_btn)

        # ── 底部按钮 ──
        bl = QHBoxLayout()
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_inputs)
        self.clear_btn.setMinimumHeight(50)
        self.clear_btn.setStyleSheet("QPushButton{background-color:#95a5a6;color:white;border:none;border-radius:6px;padding:8px;font-weight:bold;}QPushButton:hover{background-color:#7f8c8d;}")

        self.dl_txt_btn = QPushButton("下载计算书(DOCX)")
        self.dl_txt_btn.clicked.connect(self.download_docx_report)
        self.dl_txt_btn.setMinimumHeight(50)
        self.dl_txt_btn.setStyleSheet("QPushButton{background-color:#3498db;color:white;border:none;border-radius:6px;padding:8px;font-weight:bold;}QPushButton:hover{background-color:#2980b9;}")

        self.dl_pdf_btn = QPushButton("下载计算书(PDF)")
        self.dl_pdf_btn.clicked.connect(self.download_pdf_report)
        self.dl_pdf_btn.setMinimumHeight(50)
        self.dl_pdf_btn.setStyleSheet("QPushButton{background-color:#e74c3c;color:white;border:none;border-radius:6px;padding:8px;font-weight:bold;}QPushButton:hover{background-color:#c0392b;}")

        bl.addWidget(self.clear_btn)
        bl.addStretch()
        bl.addWidget(self.dl_txt_btn)
        bl.addWidget(self.dl_pdf_btn)
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

    # ═══════════════════════════ 模式切换 ═══════════════════════════
    def _on_mode_changed(self, mode):
        cfg = self.MODE_CONFIG.get(mode, {})
        is_fire = cfg.get("fire", False)
        known_area = cfg.get("known_area", True)
        # 更新默认参数
        self.mw_input.setText(str(cfg.get("mw", 18)))
        self.gamma_input.setText(str(cfg.get("gamma", 1.3)))
        self.z_input.setText(str(cfg.get("z", 1.0)))
        if is_fire:
            self.overpressure_input.setText("21")
        else:
            self.overpressure_input.setText("10")

        # 介质参数可见性
        fluid_widgets = [self._lbl_mw, self.mw_input, self._hint_mw,
                        self._lbl_gamma, self.gamma_input, self._hint_gamma,
                        self._lbl_z, self.z_input, self._hint_z,
                        self._lbl_temp, self.temp_input, self._hint_temp]
        if mode in ("饱和水蒸汽",):
            for w in fluid_widgets: w.setVisible(False)
        elif mode in ("过热水蒸汽",):
            for w in fluid_widgets[:-3]: w.setVisible(False)  # hide M, γ, Z, show T
            for w in fluid_widgets[-3:]: w.setVisible(True)
        elif mode == "空气":
            for w in fluid_widgets[:9]: w.setVisible(False)  # hide M, γ, Z
            for w in fluid_widgets[9:]: w.setVisible(True)   # show T
        elif mode.startswith("火灾"):
            if known_area:
                for w in fluid_widgets[:-3]: w.setVisible(False)
                for w in fluid_widgets[-3:]: w.setVisible(False)
            else:
                for w in fluid_widgets: w.setVisible(False)
        else:
            for w in fluid_widgets: w.setVisible(True)

        # 泄放量来源
        if is_fire:
            self._relief_source_label.setVisible(False)
            self.relief_source_combo.setVisible(False)
            self._relief_source_hint.setVisible(False)
        else:
            self._relief_source_label.setVisible(True)
            self.relief_source_combo.setVisible(True)
            self._relief_source_hint.setVisible(True)

        self._on_source_changed(self.relief_source_combo.currentText())
        self._update_relief_param_visibility(mode)

    def _on_source_changed(self, source):
        mode = self.mode_combo.currentText()
        self._update_relief_param_visibility(mode)

    def _update_relief_param_visibility(self, mode):
        cfg = self.MODE_CONFIG.get(mode, {})
        is_fire = cfg.get("fire", False)
        known_area = cfg.get("known_area", True)
        source = self.relief_source_combo.currentText()
        is_known = (source == "已知泄放量") or is_fire

        # 已知泄放量行
        for w in [self._lbl_flow, self.relief_flow_input, self._hint_flow]:
            w.setVisible(is_known and not is_fire)

        # 未知泄放量 - 管道参数（非火灾模式）
        for w in [self._lbl_pipe_d, self.pipe_d_input, self._hint_pipe_d,
                  self._lbl_pipe_v, self.pipe_v_input, self._hint_pipe_v]:
            w.setVisible(not is_known and not is_fire)

        # 火灾 - 润湿面积
        for w in [self._lbl_wet, self.wetted_area_input, self._hint_wet]:
            w.setVisible(is_fire and known_area)

        # 环境因子（火灾通用）
        for w in [self._lbl_env, self.env_factor_input, self._hint_env]:
            w.setVisible(is_fire)

        # 汽化潜热（火灾通用）
        for w in [self._lbl_latent, self.latent_heat_input, self._hint_latent]:
            w.setVisible(is_fire)

        # 火灾未知润湿 - 容器参数
        for w in [self._lbl_vessel_d, self.vessel_d_input, self._hint_vessel_d,
                  self._lbl_vessel_l, self.vessel_l_input, self._hint_vessel_l,
                  self._lbl_vessel_type, self.vessel_type_combo, self._hint_vessel_type]:
            w.setVisible(is_fire and not known_area)

    def _on_kd_type_changed(self, text):
        mapping = {"全启式": "0.65", "带调节圈微启式": "0.45", "不带调节圈微启式": "0.30"}
        for key, val in mapping.items():
            if key in text:
                self.kd_input.setText(val)
                return
        # "请选择"不改变

    # ═══════════════════════════ 计算 ═══════════════════════════
    def calculate(self):
        try:
            mode = self.mode_combo.currentText()
            cfg = self.MODE_CONFIG.get(mode, {})
            is_fire = cfg.get("fire", False)
            known_area = cfg.get("known_area", True)
            source = self.relief_source_combo.currentText()
            is_known = (source == "已知泄放量")

            ps_g = float(self.ps_input.text())       # MPa (表)
            mawp_g = float(self.mawp_input.text())   # MPa (表)
            kd = float(self.kd_input.text())
            over_pct = float(self.overpressure_input.text())
            back_p = float(self.back_pressure_input.text() or 0)

            # ── 泄放压力 (MAWP × (1+超压%) + 大气压) ──
            relief_p_mpaa = mawp_g * (1 + over_pct / 100) + 0.1013

            # ── 泄放量计算 ──
            if is_fire:
                env_f = float(self.env_factor_input.text())
                latent_heat = float(self.latent_heat_input.text()) * 1000  # kJ→J

                if known_area:
                    wetted_a = float(self.wetted_area_input.text())
                else:
                    d = float(self.vessel_d_input.text())
                    l = float(self.vessel_l_input.text())
                    vessel_type = self.vessel_type_combo.currentText()
                    if vessel_type == "球罐":
                        wetted_a = math.pi * d**2
                    elif vessel_type == "立式":
                        wetted_a = math.pi * d * (l * 0.8)  # 润湿高度≈0.8H
                    else:  # 卧式
                        wetted_a = math.pi * d * l * 0.5 + math.pi * d**2 / 4

                heat_input = 43200 * env_f * (wetted_a ** 0.82)  # W (J/s)
                relief_rate_kgs = heat_input / latent_heat  # kg/s
                relief_rate_kgh = relief_rate_kgs * 3600

                self._last_wetted_area = wetted_a
                self._last_heat_input = heat_input / 1000  # kW
            elif is_known:
                relief_rate_kgh = float(self.relief_flow_input.text())
                relief_rate_kgs = relief_rate_kgh / 3600
                self._last_wetted_area = None
                self._last_heat_input = None
            else:
                # 未知泄放量：从管道参数估算
                pipe_d_mm = float(self.pipe_d_input.text())
                pipe_v = float(self.pipe_v_input.text())
                pipe_area = math.pi * (pipe_d_mm / 1000)**2 / 4  # m²

                # 估算蒸汽/气体密度
                mw = float(self.mw_input.text())
                t_c = float(self.temp_input.text() or 150)
                rho = relief_p_mpaa * 1e6 * mw / (8314 * (t_c + 273.15))  # kg/m³

                relief_rate_kgs = rho * pipe_area * pipe_v
                relief_rate_kgh = relief_rate_kgs * 3600
                self._last_wetted_area = None
                self._last_heat_input = None

            # ── 介质参数 ──
            mw = float(self.mw_input.text())
            gamma = float(self.gamma_input.text())
            z = float(self.z_input.text())
            t_c = float(self.temp_input.text() or 150)
            t_k = t_c + 273.15

            # ── 临界流判断 ──
            back_pa = back_p * 1e6 + 101300  # 转换为 PaA
            relief_p_pa = relief_p_mpaa * 1e6
            critical_ratio = (2 / (gamma + 1)) ** (gamma / (gamma - 1))
            actual_ratio = back_pa / relief_p_pa if relief_p_pa > 0 else 1
            is_choked = actual_ratio <= critical_ratio

            # ── 泄放面积计算 (ASME VIII / API 520) ──
            C = 0.03948 * math.sqrt(gamma * (2 / (gamma + 1)) ** ((gamma + 1) / (gamma - 1)))
            sqrt_term = math.sqrt(mw / (t_k * z))

            if is_choked:
                area_m2 = relief_rate_kgs / (C * kd * relief_p_pa * sqrt_term)
            else:
                r = actual_ratio
                F = math.sqrt((gamma / (gamma - 1)) * (r ** (2 / gamma) - r ** ((gamma + 1) / gamma)))
                area_m2 = relief_rate_kgs / (C * kd * relief_p_pa * F * sqrt_term)

            area_mm2 = area_m2 * 1e6
            diameter_mm = math.sqrt(4 * area_mm2 / math.pi)

            # ── 推荐标准喉径 ──
            recommended = self._recommend_size(area_mm2)

            # ── 存储结果 ──
            self._last_result = {
                "area_mm2": area_mm2,
                "diameter_mm": diameter_mm,
                "recommended": recommended,
                "relief_p_mpaa": relief_p_mpaa,
                "relief_rate_kgh": relief_rate_kgh,
                "is_choked": is_choked,
                "critical_ratio": critical_ratio,
                "actual_ratio": actual_ratio,
                "gamma": gamma,
                "mw": mw,
                "kd": kd,
                "C": C,
            }
            self._last_params = {
                "mode": mode,
                "ps_g": ps_g,
                "mawp_g": mawp_g,
                "kd": kd,
                "over_pct": over_pct,
                "back_p": back_p,
                "mw": mw,
                "gamma": gamma,
                "z": z,
                "t_c": t_c,
            }

            self._display()
            self._update_svg_diagram()

        except ValueError as e:
            self._show_error(f"输入错误：{e}")
        except Exception as e:
            self._show_error(f"计算错误：{e}")

    def _recommend_size(self, area_mm2):
        for dn, d, a in STANDARD_VALVES:
            if a >= area_mm2 * 1.1:
                return f"{dn} (喉径{d}mm, 面积{a}mm²)"
        return f"DN200 或定制 (面积{area_mm2:.1f}mm²)"

    # ═══════════════════════════ 显示 ═══════════════════════════
    def _display(self):
        r = self._last_result
        p = self._last_params
        lines = [
            "=" * 39,
            "        安全阀泄放面积计算结果",
            "=" * 39,
            "",
            "【计算条件】",
            f"  计算类型        : {p['mode']}",
            f"  整定压力 Ps(G)  : {p['ps_g']} MPa",
            f"  最高允许工作压力 : {p['mawp_g']} MPa (G)",
            f"  流量系数 Kd     : {p['kd']}",
            f"  超压百分比      : {p['over_pct']}%",
            f"  背压            : {p['back_p']} MPa (G)",
            "",
            "【介质参数】",
            f"  分子量 M        : {p['mw']} g/mol",
            f"  绝热指数 γ      : {p['gamma']}",
            f"  压缩因子 Z      : {p['z']}",
            f"  操作温度 T      : {p['t_c']} °C",
            "",
            "【计算结果】",
            f"  ★ 所需泄放面积   : {r['area_mm2']:.2f} mm²",
            f"  ★ 等效喉径       : {r['diameter_mm']:.1f} mm",
            f"  ★ 推荐标准规格   : {r['recommended']}",
            f"    泄放压力       : {r['relief_p_mpaa']:.3f} MPaA",
            f"    泄放量         : {r['relief_rate_kgh']:.1f} kg/h",
            f"    临界压比       : {r['critical_ratio']:.4f}",
            f"    实际背压比     : {r['actual_ratio']:.4f}",
            f"    流动状态       : {'临界流（阻塞流）' if r['is_choked'] else '亚临界流'}",
        ]

        if self._last_heat_input:
            lines += [
                f"    润湿面积       : {self._last_wetted_area:.1f} m²",
                f"    火灾热输入     : {self._last_heat_input:.1f} kW",
            ]

        lines += [
            "",
            "【计算公式】",
            "  ASME VIII / API 520 气体泄放面积公式：",
            "  A = W / (C × Kd × P1 × √(M/(T×Z)))",
            "  C = 0.03948 × √(γ×(2/(γ+1))^((γ+1)/(γ-1)))",
            f"  计算 C = {r['C']:.4f}",
            "",
            "【选型建议】",
            f"  1. 选择喉径不低于 {r['diameter_mm']:.1f} mm 的安全阀",
            f"  2. 推荐 {r['recommended']}",
            "  3. 安全阀额定排量应大于计算泄放量",
            "  4. 背压>10%泄放压力时选用平衡式安全阀",
        ]

        if r['actual_ratio'] > 0.5:
            lines.append("  5. 当前背压较高，建议选用先导式或平衡波纹管式")
        else:
            lines.append("  5. 当前背压较低，普通弹簧式即可")

        lines += [
            "",
            "【标准依据】",
            "  ASME BPVC Section VIII Div.1",
            "  API RP 520 Part I",
            "  API RP 521",
            "  GB/T 12241",
            "",
            "  * 理论计算值，最终选型由专业工程师确认。",
            "=" * 39,
        ]
        self.result_text.setPlainText("\n".join(lines))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"错误：{msg}")

    # ═══════════════════════════ 清空 ═══════════════════════════
    def clear_inputs(self):
        self.mode_combo.setCurrentIndex(0)
        self.relief_source_combo.setCurrentIndex(0)
        self.ps_input.setText("1.0")
        self.mawp_input.setText("1.1")
        self.kd_type_combo.setCurrentIndex(0)
        self.kd_input.setText("0.65")
        self.relief_flow_input.setText("1000")
        self.pipe_d_input.setText("50")
        self.pipe_v_input.setText("30")
        self.wetted_area_input.setText("50")
        self.env_factor_input.setText("1.0")
        self.latent_heat_input.setText("2260")
        self.vessel_d_input.setText("2.0")
        self.vessel_l_input.setText("5.0")
        self.vessel_type_combo.setCurrentIndex(0)
        self.mw_input.setText("18")
        self.gamma_input.setText("1.3")
        self.z_input.setText("1.0")
        self.temp_input.setText("150")
        self.overpressure_input.setText("10")
        self.back_pressure_input.setText("0")
        self.result_text.clear()
        self._last_result = {}
        self._last_params = {}
        self._last_wetted_area = None
        self._last_heat_input = None
        self._on_mode_changed(self.mode_combo.currentText())

    # ═══════════════════════════ 历史 ═══════════════════════════
    def _get_history_data(self):
        r = self._last_result
        p = self._last_params
        return {
            "inputs": {
                "计算类型": p.get("mode", ""),
                "整定压力_MPa": p.get("ps_g", 0),
                "MAWP_MPa": p.get("mawp_g", 0),
                "流量系数_Kd": p.get("kd", 0),
                "超压_%": p.get("over_pct", 0),
            },
            "outputs": {
                "喉径面积_mm2": round(r.get("area_mm2", 0), 2),
                "等效喉径_mm": round(r.get("diameter_mm", 0), 2),
                "推荐规格": r.get("recommended", ""),
                "泄放压力_MPaA": round(r.get("relief_p_mpaa", 0), 3),
            }
        }

    def get_project_info(self):
        return {"calculator": "SafetyValveCalculator", "name": "安全阀计算"}

    def generate_report(self):
        return self.result_text.toPlainText()

    # ═══════════════════════════ SVG ═══════════════════════════
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        e = 'font-weight="bold"' if bold else ""
        a = 'text-anchor="middle"' if center else ""
        return f'<text x="{x}" y="{y}" {a} font-size="{size}" fill="{color}" {e}>{text}</text>'

    def _generate_safety_valve_svg(self, **kw):
        w, h = 380, 280
        p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']

        # ── 压力容器 ──
        vx, vy, vw, vh = 40, 40, 70, 130
        p.append(f'<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" fill="#e8edf2" stroke="#c0392b" stroke-width="2" rx="4"/>')
        p.append(self._text(vx+vw/2, vy+vh/2, "压力容器", size=9, color="#c0392b", bold=True))

        # ── 安全阀 ──
        sv_x, sv_y, sv_w, sv_h = 210, 55, 110, 70
        # 阀体
        p.append(f'<rect x="{sv_x}" y="{sv_y}" width="{sv_w}" height="{sv_h}" fill="#fef3f2" stroke="#e74c3c" stroke-width="2" rx="3"/>')
        # 弹簧示意
        for i in range(4):
            sy = sv_y + 10 + i*12
            p.append(f'<line x1="{sv_x+20}" y1="{sy}" x2="{sv_x+sv_w-20}" y2="{sy}" stroke="#e74c3c" stroke-width="1" stroke-dasharray="3,2"/>')
        p.append(self._text(sv_x+sv_w/2, sv_y-10, "安全阀", size=10, color="#e74c3c", bold=True))

        # ── 进口管 ──
        pipe_y = vy + vh/2 + 20
        p.append(f'<line x1="{vx+vw}" y1="{pipe_y}" x2="{sv_x}" y2="{pipe_y}" stroke="#7f8c8d" stroke-width="5"/>')
        p.append(self._text((vx+vw+sv_x)/2, pipe_y-10, "进口", size=8, color="#555"))

        # ── 排放管 ──
        p.append(f'<line x1="{sv_x+sv_w}" y1="{sv_y+sv_h/2}" x2="{sv_x+sv_w+60}" y2="{sv_y+sv_h/2}" stroke="#7f8c8d" stroke-width="5" marker-end="url(#arr)"/>')
        p.append(self._text(sv_x+sv_w+30, sv_y+sv_h/2-10, "排放", size=8, color="#555"))

        # ── 压力标注 ──
        ps_val = kw.get("ps", "")
        mawp_val = kw.get("mawp", "")
        if ps_val:
            p.append(self._text(vx+vw+30, vy+15, f"Ps={ps_val}", size=9, color="#c0392b", bold=True, center=False))
        if mawp_val:
            p.append(self._text(vx+vw+30, vy+30, f"MAWP={mawp_val}", size=9, color="#e67e22", bold=True, center=False))

        p.append(self._text(w/2, 12, "安全阀泄放示意", size=10, color="#4a6fa5", bold=True))

        # 结果
        area_val = kw.get("area", "")
        if area_val:
            p.append(self._text(10, h-10, f"A={area_val} mm²", size=10, color="#27ae60", bold=True, center=False))

        p.append('<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#7f8c8d"/></marker></defs></svg>')
        return "".join(p)

    def _update_svg_diagram(self):
        try:
            kw = {}
            try:
                val = self.ps_input.text().strip()
                if val: kw["ps"] = val
            except: pass
            try:
                val = self.mawp_input.text().strip()
                if val: kw["mawp"] = val
            except: pass
            if self._last_result:
                kw["area"] = f"{self._last_result.get('area_mm2', 0):.1f}"
            s = self._generate_safety_valve_svg(**kw)
            self.svg_widget.load(s.encode("utf-8"))
        except: pass

    # ═══════════════════════════ 报告 ═══════════════════════════
    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "SafetyValveCalculator")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "SafetyValveCalculator")
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = SafetyValveCalculator()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
