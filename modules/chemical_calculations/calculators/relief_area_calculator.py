import os
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox,
    QScrollArea, QSizePolicy,

)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator, QFont
from modules.combo_box_utils import ComboBoxWheelBlocker


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
class ReliefAreaCalculator(QWidget):
    """泄压面积计算器（统一 UI 规范版）

    计算安全阀、爆破片等泄压装置的所需泄放面积。
    基于 ASME VIII / API 520 / API 521 标准，
    支持气体/蒸汽临界流与亚临界流、液体泄放、两相流简化计算。
    """

    # ── 标准安全阀喉径规格表 (DN, 喉径mm, 面积mm²) ──
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
    ]

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
        self._wheel_blocker = ComboBoxWheelBlocker(self)
        for combo in self.findChildren(QComboBox):
            combo.installEventFilter(self._wheel_blocker)

    def init_data_manager(self):
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception:
            self.data_manager = None

    # ─────────────────────── UI ───────────────────────────
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ──────────────── 左侧输入区 ────────────────
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        scroll_left.setWidgetResizable(True)

        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 说明文字
        desc = QLabel(
            "计算安全阀、爆破片等泄压装置的所需泄放面积。"
            "依据 ASME VIII / API 520 / API 521 标准，"
            "支持气体/蒸汽临界流与亚临界流、液体泄放、两相流计算。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc)

        label_style = "font-weight: bold; padding-right: 10px;"

        def make_lbl(text):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet(label_style)
            return lbl

        def make_hint(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-style: italic;")
            return lbl

        # ── 泄放场景组 ──
        scenario_group = QGroupBox("泄放场景")
        scenario_group.setStyleSheet(GROUP_STYLE)
        sg = QGridLayout(scenario_group)
        sg.setHorizontalSpacing(10)
        sg.setVerticalSpacing(12)
        sg.setColumnStretch(0, 4)
        sg.setColumnStretch(1, 8)
        sg.setColumnStretch(2, 5)


        # 行0：泄放场景
        self.scenario_combo = QComboBox()
        self.scenario_combo.setStyleSheet(COMBOBOX_STYLE)
        self.scenario_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.scenario_combo.addItems([
            "火灾工况", "操作故障", "热膨胀",
            "化学反应失控", "外部火灾", "换热管破裂"])
        sg.addWidget(make_lbl("泄放场景:"), 0, 0)
        sg.addWidget(self.scenario_combo, 0, 1)
        sg.addWidget(make_hint("选择泄放工况"), 0, 2)

        # 行1：介质类型
        self.fluid_combo = QComboBox()
        self.fluid_combo.setStyleSheet(COMBOBOX_STYLE)
        self.fluid_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.fluid_combo.addItems(["气体/蒸汽", "液体", "两相流"])
        self.fluid_combo.currentTextChanged.connect(self._on_fluid_changed)
        sg.addWidget(make_lbl("介质类型:"), 1, 0)
        sg.addWidget(self.fluid_combo, 1, 1)
        sg.addWidget(make_hint("气体/液体/两相流"), 1, 2)

        # 行2：设计标准
        self.standard_combo = QComboBox()
        self.standard_combo.setStyleSheet(COMBOBOX_STYLE)
        self.standard_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.standard_combo.addItems(["ASME VIII", "API 520", "API 521", "ISO 4126"])
        sg.addWidget(make_lbl("设计标准:"), 2, 0)
        sg.addWidget(self.standard_combo, 2, 1)
        sg.addWidget(make_hint("选择计算标准"), 2, 2)

        left_layout.addWidget(scenario_group)

        # ── 设备参数组 ──
        vessel_group = QGroupBox("设备参数")
        vessel_group.setStyleSheet(GROUP_STYLE)
        vg = QGridLayout(vessel_group)
        vg.setHorizontalSpacing(10)
        vg.setVerticalSpacing(12)
        vg.setColumnStretch(0, 4)
        vg.setColumnStretch(1, 8)
        vg.setColumnStretch(2, 5)

        # 行0：容器容积
        self.volume_input = QLineEdit("10")
        self.volume_input.setValidator(QDoubleValidator(0.01, 100000, 2))
        self.volume_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vg.addWidget(make_lbl("容器容积:"), 0, 0)
        vg.addWidget(self.volume_input, 0, 1)
        self.volume_unit_combo = QComboBox()
        self.volume_unit_combo.setStyleSheet(COMBOBOX_STYLE)
        self.volume_unit_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.volume_unit_combo.addItems(["m\u00b3", "L"])
        vg.addWidget(self.volume_unit_combo, 0, 2)

        # 行1：设计压力
        self.design_p_input = QLineEdit("1.1")
        self.design_p_input.setValidator(QDoubleValidator(0.001, 100, 3))
        self.design_p_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vg.addWidget(make_lbl("设计压力:"), 1, 0)
        vg.addWidget(self.design_p_input, 1, 1)
        self.design_p_unit_combo = QComboBox()
        self.design_p_unit_combo.setStyleSheet(COMBOBOX_STYLE)
        self.design_p_unit_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.design_p_unit_combo.addItems(["kPa", "MPa", "bar"])
        vg.addWidget(self.design_p_unit_combo, 1, 2)

        # 行2：操作压力
        self.oper_p_input = QLineEdit("0.8")
        self.oper_p_input.setValidator(QDoubleValidator(0.001, 100, 3))
        self.oper_p_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vg.addWidget(make_lbl("操作压力:"), 2, 0)
        vg.addWidget(self.oper_p_input, 2, 1)
        self.oper_p_unit_combo = QComboBox()
        self.oper_p_unit_combo.setStyleSheet(COMBOBOX_STYLE)
        self.oper_p_unit_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.oper_p_unit_combo.addItems(["kPa", "MPa", "bar"])
        vg.addWidget(self.oper_p_unit_combo, 2, 2)

        # 行3：最大允许工作压力
        self.mawp_input = QLineEdit("1.0")
        self.mawp_input.setValidator(QDoubleValidator(0.001, 100, 3))
        self.mawp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vg.addWidget(make_lbl("最大允许压力:"), 3, 0)
        vg.addWidget(self.mawp_input, 3, 1)
        self.mawp_unit_combo = QComboBox()
        self.mawp_unit_combo.setStyleSheet(COMBOBOX_STYLE)
        self.mawp_unit_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mawp_unit_combo.addItems(["kPa", "MPa", "bar"])
        vg.addWidget(self.mawp_unit_combo, 3, 2)

        left_layout.addWidget(vessel_group)

        # ── 介质参数组 ──
        fluid_group = QGroupBox("介质参数")
        fluid_group.setStyleSheet(GROUP_STYLE)
        fg = QGridLayout(fluid_group)
        fg.setHorizontalSpacing(10)
        fg.setVerticalSpacing(12)
        fg.setColumnStretch(0, 4)
        fg.setColumnStretch(1, 8)
        fg.setColumnStretch(2, 5)

        # 行0：介质名称
        self.fluid_name_input = QLineEdit()
        self.fluid_name_input.setPlaceholderText("例如：蒸汽")
        fg.addWidget(make_lbl("介质名称:"), 0, 0)
        fg.addWidget(self.fluid_name_input, 0, 1)
        fg.addWidget(make_hint("填写介质名称"), 0, 2)

        # 行1：分子量
        self.mw_input = QLineEdit("18")
        self.mw_input.setValidator(QDoubleValidator(1, 500, 2))
        self.mw_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        fg.addWidget(make_lbl("分子量 (g/mol):"), 1, 0)
        fg.addWidget(self.mw_input, 1, 1)
        fg.addWidget(make_hint("蒸汽=18, 空气=29"), 1, 2)

        # 行2：温度
        self.temp_input = QLineEdit("200")
        self.temp_input.setValidator(QDoubleValidator(-273, 2000, 1))
        self.temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        fg.addWidget(make_lbl("温度 (\u00b0C):"), 2, 0)
        fg.addWidget(self.temp_input, 2, 1)
        fg.addWidget(make_hint("操作温度"), 2, 2)

        # 行3：压缩因子
        self.z_input = QLineEdit("1.0")
        self.z_input.setValidator(QDoubleValidator(0.1, 2.0, 3))
        self.z_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        fg.addWidget(make_lbl("压缩因子 Z:"), 3, 0)
        fg.addWidget(self.z_input, 3, 1)
        fg.addWidget(make_hint("理想气体=1.0"), 3, 2)

        # 行4：比热比
        self.gamma_input = QLineEdit("1.3")
        self.gamma_input.setValidator(QDoubleValidator(1.0, 2.0, 3))
        self.gamma_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        fg.addWidget(make_lbl("绝热指数 \u03b3:"), 4, 0)
        fg.addWidget(self.gamma_input, 4, 1)
        fg.addWidget(make_hint("双原子=1.4"), 4, 2)

        # 行5：密度
        self.density_input = QLineEdit("1.2")
        self.density_input.setValidator(QDoubleValidator(0.01, 20000, 3))
        self.density_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        fg.addWidget(make_lbl("密度 (kg/m\u00b3):"), 5, 0)
        fg.addWidget(self.density_input, 5, 1)
        fg.addWidget(make_hint("液体~1000, 气体~1.2"), 5, 2)

        left_layout.addWidget(fluid_group)

        # ── 泄放参数组 ──
        relief_group = QGroupBox("泄放参数")
        relief_group.setStyleSheet(GROUP_STYLE)
        rg = QGridLayout(relief_group)
        rg.setHorizontalSpacing(10)
        rg.setVerticalSpacing(12)
        rg.setColumnStretch(0, 4)
        rg.setColumnStretch(1, 8)
        rg.setColumnStretch(2, 5)

        # 行0：泄放速率
        self.relief_rate_input = QLineEdit("1000")
        self.relief_rate_input.setValidator(QDoubleValidator(0.001, 1e8, 1))
        self.relief_rate_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rg.addWidget(make_lbl("泄放速率:"), 0, 0)
        rg.addWidget(self.relief_rate_input, 0, 1)
        self.rate_unit_combo = QComboBox()
        self.rate_unit_combo.setStyleSheet(COMBOBOX_STYLE)
        self.rate_unit_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.rate_unit_combo.addItems(["kg/h", "kg/s", "m\u00b3/h"])
        rg.addWidget(self.rate_unit_combo, 0, 2)

        # 行1：背压
        self.back_p_input = QLineEdit("101.325")
        self.back_p_input.setValidator(QDoubleValidator(0, 100000, 3))
        self.back_p_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rg.addWidget(make_lbl("背压:"), 1, 0)
        rg.addWidget(self.back_p_input, 1, 1)
        rg.addWidget(make_hint("大气压=101.325"), 1, 2)

        # 行2：超压百分比
        self.over_p_input = QLineEdit("10")
        self.over_p_input.setValidator(QDoubleValidator(1, 100, 1))
        self.over_p_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rg.addWidget(make_lbl("超压百分比:"), 2, 0)
        rg.addWidget(self.over_p_input, 2, 1)
        rg.addWidget(make_hint("通常10%, 火灾21%"), 2, 2)

        # 行3：排放系数
        self.kd_input = QLineEdit("0.65")
        self.kd_input.setValidator(QDoubleValidator(0.1, 1.0, 3))
        self.kd_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rg.addWidget(make_lbl("排放系数 Kd:"), 3, 0)
        rg.addWidget(self.kd_input, 3, 1)
        rg.addWidget(make_hint("弹簧式0.65, 先导0.9"), 3, 2)

        left_layout.addWidget(relief_group)

        # ── 计算按钮 ──
        calc_btn = QPushButton("计算")
        calc_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calc_btn.setMinimumHeight(50)
        calc_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                min-height: 50px; padding: 0px;
            }
            QPushButton:hover { background-color: #219955; }
        """)
        calc_btn.clicked.connect(self.calculate)
        left_layout.addWidget(calc_btn)

        # ── 标准安全阀规格表 ──
        valve_group = QGroupBox("标准安全阀喉径规格")
        valve_group.setStyleSheet(GROUP_STYLE)
        valve_vbox = QVBoxLayout(valve_group)

        self.valve_table = QTableWidget()
        self.valve_table.setColumnCount(4)
        self.valve_table.setHorizontalHeaderLabels(
            ["公称尺寸", "喉径 (mm)", "泄放面积 (mm\u00b2)", "适用压力 (kPa)"])
        self.valve_table.setMaximumHeight(200)
        self._populate_valve_table()
        vh = self.valve_table.horizontalHeader()
        vh.setSectionResizeMode(QHeaderView.Stretch)
        valve_vbox.addWidget(self.valve_table)
        left_layout.addWidget(valve_group)

        # ── 底部按钮行 ──
        btn_row = QHBoxLayout()

        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6; color: white;
                font-weight: bold; border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        clear_btn.clicked.connect(self.clear_inputs)

        dl_txt_btn = QPushButton("下载计算书(TXT)")
        dl_txt_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        dl_txt_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white;
                font-weight: bold; border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #219653; }
        """)
        dl_txt_btn.clicked.connect(self.download_txt_report)

        dl_pdf_btn = QPushButton("下载计算书(PDF)")
        dl_pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        dl_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; color: white;
                font-weight: bold; border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        dl_pdf_btn.clicked.connect(self.generate_pdf_report)

        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(dl_txt_btn)
        btn_row.addWidget(dl_pdf_btn)
        left_layout.addLayout(btn_row)

        # ──────────────── 右侧结果区 ────────────────
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        result_group = QGroupBox("计算结果")
        result_group.setStyleSheet(GROUP_STYLE)
        result_vbox = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet("""
            QTextEdit {
                /* bg via theme */border: 1px solid #ecf0f1;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        result_vbox.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # 拼合
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

    # ──────────────────── 辅助 ───────────────────────────
    def _populate_valve_table(self):
        """填充标准安全阀规格表"""
        self.valve_table.setRowCount(len(self.STANDARD_VALVES))
        for i, (dn, d, a) in enumerate(self.STANDARD_VALVES):
            items = [dn, str(d), str(a), "\u22641600"]
            for j, val in enumerate(items):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.valve_table.setItem(i, j, item)

    def _on_fluid_changed(self, fluid_type):
        """介质类型切换时更新默认值"""
        if fluid_type == "液体":
            self.density_input.setText("1000")
            self.gamma_input.setText("1.0")
            self.mw_input.setText("18")
        elif fluid_type == "气体/蒸汽":
            self.density_input.setText("1.2")
            self.gamma_input.setText("1.3")
            self.mw_input.setText("18")
        else:  # 两相流
            self.density_input.setText("50")
            self.gamma_input.setText("1.3")
            self.mw_input.setText("18")

    @staticmethod
    def _pressure_to_kpa(value, unit):
        """统一转为 kPa"""
        if unit == "MPa":
            return value * 1000
        elif unit == "bar":
            return value * 100
        return value  # kPa

    # ──────────────────── 计算 ───────────────────────────
    def calculate(self):
        try:
            # 场景与标准
            scenario = self.scenario_combo.currentText()
            fluid_type = self.fluid_combo.currentText()
            standard = self.standard_combo.currentText()

            # 设备参数
            vessel_vol = float(self.volume_input.text())
            vessel_vol_unit = self.volume_unit_combo.currentText()
            vessel_vol_m3 = vessel_vol / 1000 if vessel_vol_unit == "L" else vessel_vol

            design_p = float(self.design_p_input.text())
            design_p_kpa = self._pressure_to_kpa(
                design_p, self.design_p_unit_combo.currentText())

            oper_p = float(self.oper_p_input.text())
            oper_p_kpa = self._pressure_to_kpa(
                oper_p, self.oper_p_unit_combo.currentText())

            mawp = float(self.mawp_input.text())
            mawp_kpa = self._pressure_to_kpa(
                mawp, self.mawp_unit_combo.currentText())

            # 介质参数
            fluid_name = self.fluid_name_input.text() or "未命名"
            mw = float(self.mw_input.text())
            temp_c = float(self.temp_input.text())
            z = float(self.z_input.text())
            gamma = float(self.gamma_input.text())
            density = float(self.density_input.text())

            # 泄放参数
            relief_rate = float(self.relief_rate_input.text())
            rate_unit = self.rate_unit_combo.currentText()
            if rate_unit == "kg/h":
                relief_rate_kgs = relief_rate / 3600.0
            elif rate_unit == "m\u00b3/h":
                relief_rate_kgs = relief_rate * density / 3600.0
            else:
                relief_rate_kgs = relief_rate

            back_p_kpa = float(self.back_p_input.text())
            over_p_pct = float(self.over_p_input.text())
            kd = float(self.kd_input.text())

            # 泄放压力 (MAWP × (1 + 超压%))
            relief_p_kpa = mawp_kpa * (1 + over_p_pct / 100.0)

            # 火灾工况泄放量估算（API 521: Q = 43.2·F·A^0.82）
            fire_rate_kgs = None
            if "火灾" in scenario:
                env_f = 1.0  # 裸露容器环境因子
                # 估算润湿面积（简化：按容器体积粗估）
                if vessel_vol_m3 > 0:
                    assumed_wetted_a = 2.0 * (vessel_vol_m3 ** (2.0 / 3.0)) * 3.1416
                    heat_input = 43.2 * env_f * (assumed_wetted_a ** 0.82)
                    latent_heat = 300.0  # 假设潜热 kJ/kg
                    fire_rate_kgs = heat_input / latent_heat

            # 根据介质类型计算泄放面积
            if fluid_type == "气体/蒸汽":
                area_mm2 = self._calc_gas_area(
                    relief_rate_kgs, relief_p_kpa, back_p_kpa,
                    temp_c, mw, z, gamma, kd)
            elif fluid_type == "液体":
                area_mm2 = self._calc_liquid_area(
                    relief_rate_kgs, relief_p_kpa, back_p_kpa,
                    density, kd)
            else:
                area_mm2 = self._calc_two_phase_area(
                    relief_rate_kgs, relief_p_kpa, back_p_kpa,
                    temp_c, mw, density, kd)

            diameter_mm = math.sqrt(area_mm2 / math.pi) * 2
            recommended = self._recommend_size(area_mm2)

            # 临界流动判断（仅气体）
            critical_ratio = 0
            actual_ratio = 0
            is_choked = False
            if fluid_type == "气体/蒸汽":
                critical_ratio = (2 / (gamma + 1)) ** (gamma / (gamma - 1))
                actual_ratio = back_p_kpa / relief_p_kpa if relief_p_kpa > 0 else 1
                is_choked = actual_ratio <= critical_ratio

            self._last_result = {
                "area_mm2": area_mm2,
                "diameter_mm": diameter_mm,
                "recommended": recommended,
                "relief_p_kpa": relief_p_kpa,
                "relief_rate_kgh": relief_rate_kgs * 3600,
                "flow_type": self._flow_type_label(fluid_type, is_choked),
                "is_choked": is_choked,
                "critical_ratio": critical_ratio,
                "actual_ratio": actual_ratio,
                "fire_rate_kgs": fire_rate_kgs,
            }
            self._last_params = {
                "scenario": scenario,
                "fluid_type": fluid_type,
                "standard": standard,
                "fluid_name": fluid_name,
                "vessel_vol_m3": vessel_vol_m3,
                "design_p_kpa": design_p_kpa,
                "oper_p_kpa": oper_p_kpa,
                "mawp_kpa": mawp_kpa,
                "mw": mw,
                "temp_c": temp_c,
                "z": z,
                "gamma": gamma,
                "density": density,
                "relief_rate": relief_rate,
                "rate_unit": rate_unit,
                "back_p_kpa": back_p_kpa,
                "over_p_pct": over_p_pct,
                "kd": kd,
            }

            self._display()

            

        except ValueError as e:
            self._show_error(f"输入错误：{e}")
        except Exception as e:
            self._show_error(f"计算错误：{e}")

    # ── 气体/蒸汽泄放面积 (ASME VIII / API 520, SI) ──
    @staticmethod
    def _calc_gas_area(W, P1_kpa, P2_kpa, T_c, M, Z, k, Kd):
        """返回所需泄放面积 (mm²)"""
        T_k = T_c + 273.15
        C = 0.03948 * math.sqrt(k * (2 / (k + 1)) ** ((k + 1) / (k - 1)))
        sqrt_M_TZ = math.sqrt(M / (T_k * Z))

        critical_ratio = (2 / (k + 1)) ** (k / (k - 1))
        ratio = P2_kpa / P1_kpa if P1_kpa > 0 else 1.0

        if ratio <= critical_ratio:
            # 临界流（阻塞流）
            A_m2 = W / (C * Kd * P1_kpa * 1000 * sqrt_M_TZ)
        else:
            # 亚临界流
            r = ratio
            F = math.sqrt(
                (k / (k - 1)) * (r ** (2 / k) - r ** ((k + 1) / k)))
            A_m2 = W / (C * Kd * P1_kpa * 1000 * F * sqrt_M_TZ)

        return A_m2 * 1e6  # m² → mm²

    # ── 液体泄放面积 (ASME VIII / API 520, SI) ──
    @staticmethod
    def _calc_liquid_area(W, P1_kpa, P2_kpa, rho, Kd):
        """返回所需泄放面积 (mm²)"""
        delta_p = (P1_kpa - P2_kpa) * 1000  # kPa → Pa
        if delta_p <= 0:
            return float("inf")
        A_m2 = W / (Kd * math.sqrt(2 * rho * delta_p))
        return A_m2 * 1e6

    # ── 两相流泄放面积（均相平衡模型简化） ──
    @staticmethod
    def _calc_two_phase_area(W, P1_kpa, P2_kpa, T_c, M, rho, Kd):
        """两相流简化计算，使用气体公式近似"""
        T_k = T_c + 273.15
        k = 1.3
        Z = 1.0
        C = 0.03948 * math.sqrt(k * (2 / (k + 1)) ** ((k + 1) / (k - 1)))
        sqrt_M_TZ = math.sqrt(M / (T_k * Z))

        critical_ratio = (2 / (k + 1)) ** (k / (k - 1))
        ratio = P2_kpa / P1_kpa if P1_kpa > 0 else 1.0

        if ratio <= critical_ratio:
            A_m2 = W / (C * Kd * P1_kpa * 1000 * sqrt_M_TZ)
        else:
            r = ratio
            F = math.sqrt(
                (k / (k - 1)) * (r ** (2 / k) - r ** ((k + 1) / k)))
            A_m2 = W / (C * Kd * P1_kpa * 1000 * F * sqrt_M_TZ)

        return A_m2 * 1e6

    # ── 推荐标准阀门规格 ──
    def _recommend_size(self, area_mm2):
        """根据计算面积推荐满足 10% 安全余量的最小标准规格"""
        for dn, d, a in self.STANDARD_VALVES:
            if a >= area_mm2 * 1.1:
                return dn
        return "DN150 或定制"

    @staticmethod
    def _flow_type_label(fluid_type, is_choked):
        if fluid_type == "气体/蒸汽":
            return "临界流（阻塞流）" if is_choked else "亚临界流"
        elif fluid_type == "液体":
            return "不可压缩流动"
        return "两相流（HEM简化）"

    # ──────────────────── 显示 ───────────────────────────
    def _display(self):
        r = self._last_result
        p = self._last_params
        lines = [
            "=" * 55,
            "          泄压面积计算结果",
            "=" * 55,
            "",
            "【工况条件】",
            f"  泄放场景       : {p['scenario']}",
            f"  介质类型       : {p['fluid_type']}",
            f"  设计标准       : {p['standard']}",
            f"  介质名称       : {p['fluid_name']}",
            "",
            "【设备参数】",
            f"  容器容积       : {p['vessel_vol_m3']:.2f} m\u00b3",
            f"  设计压力       : {p['design_p_kpa']:.1f} kPa",
            f"  操作压力       : {p['oper_p_kpa']:.1f} kPa",
            f"  MAWP           : {p['mawp_kpa']:.1f} kPa",
            "",
            "【介质参数】",
            f"  分子量         : {p['mw']} g/mol",
            f"  温度           : {p['temp_c']} \u00b0C",
            f"  压缩因子 Z     : {p['z']}",
            f"  绝热指数 \u03b3     : {p['gamma']}",
            f"  密度           : {p['density']} kg/m\u00b3",
            "",
            "【泄放参数】",
            f"  泄放速率       : {p['relief_rate']} {p['rate_unit']}",
            f"  背压           : {p['back_p_kpa']} kPa",
            f"  超压百分比     : {p['over_p_pct']} %",
            f"  排放系数 Kd    : {p['kd']}",
            "",
            "【计算结果】",
            f"  \u2605 所需泄放面积   : {r['area_mm2']:.2f} mm\u00b2",
            f"  \u2605 等效喉径       : {r['diameter_mm']:.2f} mm",
            f"    推荐规格       : {r['recommended']}",
            f"    泄放压力       : {r['relief_p_kpa']:.1f} kPa",
            f"    泄放量         : {r['relief_rate_kgh']:.2f} kg/h",
            f"    流动状态       : {r['flow_type']}",
        ]

        # 气体临界流信息
        if p['fluid_type'] == "气体/蒸汽":
            lines.append(f"    临界压比       : {r['critical_ratio']:.4f}")
            lines.append(f"    实际背压比     : {r['actual_ratio']:.4f}")
            if r['is_choked']:
                lines.append("    \u26a0 当前为临界流（阻塞流），背压不影响泄放量")
            else:
                lines.append("    \u26a0 当前为亚临界流，背压降低泄放能力")

        # 火灾工况信息
        if r['fire_rate_kgs'] is not None:
            lines += [
                "",
                "【火灾工况估算】",
                "  按 API 521 火灾热输入公式估算：",
                f"    Q = 43.2 \u00d7 F \u00d7 A^0.82",
                f"    估算火灾泄放量   : {r['fire_rate_kgs']:.2f} kg/s",
                f"    折合             : {r['fire_rate_kgs']*3600:.1f} kg/h",
            ]

        lines += [
            "",
            "【选型建议】",
            f"  1. 所需泄放面积 {r['area_mm2']:.2f} mm\u00b2",
            f"     推荐选用 {r['recommended']} 安全阀或等效泄压装置",
            "  2. 排放系数 Kd 应按阀门制造商提供值选取",
            "  3. 实际泄压装置的认证排量应大于计算泄放量",
            "  4. 背压修正：背压 > 10% 泄放压力时需选平衡式",
            "  5. 火灾工况下超压百分比可取 21%",
            "",
            "【标准依据】",
            "  ASME BPVC Section VIII Div.1 UG-131/132",
            "  API RP 520 Part I - Sizing & Selection",
            "  API RP 521 - Pressure-Relieving Systems",
            "  ISO 4126 - Safety Devices for Pressure Protection",
            "",
            "  * 本结果为理论计算值，实际选型需由",
            "    专业工程师结合工况确认设计方案。",
            "=" * 55,
        ]
        self.result_text.setPlainText("\n".join(lines))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"\u26a0\ufe0f  错误：{msg}")

    # ──────────────────── 清空 ───────────────────────────
    def clear_inputs(self):
        self.scenario_combo.setCurrentIndex(0)
        self.fluid_combo.setCurrentIndex(0)
        self.standard_combo.setCurrentIndex(0)
        self.volume_input.setText("10")
        self.volume_unit_combo.setCurrentIndex(0)
        self.design_p_input.setText("1.1")
        self.design_p_unit_combo.setCurrentIndex(0)
        self.oper_p_input.setText("0.8")
        self.oper_p_unit_combo.setCurrentIndex(0)
        self.mawp_input.setText("1.0")
        self.mawp_unit_combo.setCurrentIndex(0)
        self.fluid_name_input.clear()
        self.mw_input.setText("18")
        self.temp_input.setText("200")
        self.z_input.setText("1.0")
        self.gamma_input.setText("1.3")
        self.density_input.setText("1.2")
        self.relief_rate_input.setText("1000")
        self.rate_unit_combo.setCurrentIndex(0)
        self.back_p_input.setText("101.325")
        self.over_p_input.setText("10")
        self.kd_input.setText("0.65")
        self.result_text.clear()
        self._last_result = {}
        self._last_params = {}

    # ──────────────────── 历史数据 ──────────────────────
    def _get_history_data(self):
        r = self._last_result
        p = self._last_params
        return {
            "inputs": {
                "场景类型": p.get("scenario", ""),
                "介质类型": p.get("fluid_type", ""),
                "设计标准": p.get("standard", ""),
                "容器容积_m3": p.get("vessel_vol_m3", 0),
                "MAWP_kPa": p.get("mawp_kpa", 0),
                "分子量": p.get("mw", 0),
                "温度_C": p.get("temp_c", 0),
                "绝热指数": p.get("gamma", 0),
                "泄放速率": p.get("relief_rate", 0),
                "速率单位": p.get("rate_unit", ""),
                "超压_%": p.get("over_p_pct", 0),
                "排放系数": p.get("kd", 0),
            },
            "outputs": {
                "泄放面积_mm2": round(r.get("area_mm2", 0), 2),
                "等效喉径_mm": round(r.get("diameter_mm", 0), 2),
                "推荐规格": r.get("recommended", ""),
                "泄放压力_kPa": round(r.get("relief_p_kpa", 0), 1),
            }
        }

    def get_project_info(self):
        return {
            "calculator": "ReliefAreaCalculator",
            "name": "泄压面积计算",
        }

    # ──────────────────── 报告 ───────────────────────────
    def generate_report(self):
        return self.result_text.toPlainText()

    def download_txt_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先计算，再下载报告。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存TXT报告", "泄压面积计算报告.txt", "文本文件 (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "成功", f"报告已保存到：\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败：{e}")

    def generate_pdf_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先计算，再下载PDF。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存PDF报告", "泄压面积计算报告.pdf", "PDF文件 (*.pdf)")
        if not path:
            return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.enums import TA_LEFT
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            font_paths = [
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simsun.ttc",
            ]
            font_name = "Helvetica"
            for fp in font_paths:
                if os.path.exists(fp):
                    try:
                        pdfmetrics.registerFont(TTFont("CF", fp))
                        font_name = "CF"
                        break
                    except Exception:
                        continue

            doc = SimpleDocTemplate(
                path, pagesize=A4,
                leftMargin=20 * mm, rightMargin=20 * mm,
                topMargin=20 * mm, bottomMargin=20 * mm)
            styles = getSampleStyleSheet()
            st = ParagraphStyle(
                "Body", fontName=font_name, fontSize=10,
                leading=16, alignment=TA_LEFT)
            story = []
            for line in content.split("\n"):
                safe = line.replace("&", "&amp;").replace(
                    "<", "&lt;").replace(">", "&gt;")
                story.append(
                    Paragraph(safe if safe.strip() else "&nbsp;", st))
                story.append(Spacer(1, 1))
            doc.build(story)
            QMessageBox.information(self, "成功", f"PDF已保存到：\n{path}")
        except ImportError:
            QMessageBox.critical(
                self, "错误", "缺少 reportlab 库，请运行：pip install reportlab")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"PDF生成失败：{e}")


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = ReliefAreaCalculator()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
