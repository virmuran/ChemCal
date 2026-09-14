"""
夹套/盘管换热面积核算计算器

两种换热型式：
  1. 夹套换热 — 整体夹套/半管夹套，蒸汽/水加热/冷却
  2. 盘管换热 — 螺旋盘管，沉浸式换热

设计流程：
  - 输入釜体尺寸和操作条件
  - 选择换热介质（蒸汽/水/导热油）
  - 计算釜内侧给热系数（搅拌/自然对流）
  - 计算换热介质侧给热系数
  - 综合传热系数 → 所需面积 → 与可用面积对比 → 裕量

理论依据：
  - 搅拌釜内侧：Nu = C·Re^a·Pr^b·(μ/μ_w)^c
  - 夹套水侧：Dittus-Boelter Nu = 0.023·Re^0.8·Pr^n
  - 盘管：Nu = 0.023·Re^0.8·Pr^0.4·(1+3.5·d_i/D_coil)
  - 蒸汽冷凝：h ≈ 5000~15000 W/(m²·K)
  - 总传热系数：1/K = 1/h_i + δ/λ + 1/h_o + R_f
"""

import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QScrollArea,
    QButtonGroup, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtSvgWidgets import QSvgWidget

from calculator_base import CalculatorBase
from utils.docx_utils import ReportExporter
from app_styles import (COMBOBOX_STYLE, GROUP_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, CLEAR_BTN_STYLE,
                        DOCX_BTN_STYLE, PDF_BTN_STYLE)
from svg_utils import svg_text, svg_rect, svg_line, svg_start, svg_end
from common_constants import G, WATER_DENSITY, WATER_CP, get_steam_props

# ── 换热介质类型 ──
MEDIA_TYPES = {
    "饱和蒸汽(加热)": {"mode": "steam", "h_range": (5000, 15000)},
    "热水(加热/冷却)": {"mode": "water", "h_range": (500, 5000)},
    "冷水(冷却)": {"mode": "water", "h_range": (500, 3000)},
    "导热油(加热)": {"mode": "oil", "h_range": (200, 2000)},
    "自定义介质": {"mode": "custom", "h_range": (100, 15000)},
}

# ── 釜内介质数据 ──
VESSEL_MEDIA = {
    "水": {"cp": WATER_CP, "rho": WATER_DENSITY, "k": 0.599, "mu": 1.005e-3},
    "95%乙醇": {"cp": 2.51, "rho": 789, "k": 0.171, "mu": 1.20e-3},
    "乙二醇": {"cp": 2.35, "rho": 1113, "k": 0.258, "mu": 20.0e-3},
    "导热油": {"cp": 2.90, "rho": 870, "k": 0.12, "mu": 5.0e-3},
    "盐水(20%)": {"cp": 3.71, "rho": 1150, "k": 0.54, "mu": 1.8e-3},
    "苯": {"cp": 1.36, "rho": 879, "k": 0.15, "mu": 0.65e-3},
    "甲醇": {"cp": 2.53, "rho": 792, "k": 0.202, "mu": 0.59e-3},
    "自定义": {"cp": None, "rho": None, "k": None, "mu": None},
}

# ── 釜体材质导热系数 (W/(m·K)) ──
WALL_MATERIALS = {
    "碳钢": 45.0,
    "304不锈钢": 16.3,
    "316L不锈钢": 16.3,
    "搪玻璃": 1.05,
    "自定义": None,
}

# ── 污垢热阻典型值 (m²·K/W) ──
FOULING_RESISTANCE = {
    "洁净介质": (0.0001, 0.0001),
    "工艺水": (0.0002, 0.0002),
    "有机溶剂": (0.0001, 0.0002),
    "含悬浮物液体": (0.0004, 0.0004),
    "易结垢介质": (0.0008, 0.0008),
    "自定义": (None, None),
}


class JacketCoilCalculator(CalculatorBase):
    """夹套/盘管换热面积核算计算器"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent, data_manager)
        self._last_area_avail = None
        self._last_area_req = None
        self._last_margin = None
        self._last_K = None
        self._last_Q = None
        self._last_lmtd = None
        self.setup_ui()
        self.setup_wheel_blocker()
        self._update_input_visibility()

    # ── UI 构建 ────────────────────────────────────────────

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ── 左侧：输入参数 (占 2/3) ──
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(SCROLL_AREA_STYLE)
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 模式选择按钮
        self._create_mode_buttons(left_layout)

        # 釜体参数组
        self._create_vessel_group(left_layout)

        # 换热介质参数组
        self._create_media_group(left_layout)

        # 高级参数组（可折叠感）
        self._create_advanced_group(left_layout)

        left_layout.addStretch()
        scroll_left.setWidget(left_widget)

        # ── 右侧：结果 + SVG (占 1/3) ──
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        # SVG 示意图（特色功能，保留在右栏最上方）
        svg_group = QGroupBox("示意图")
        svg_group.setStyleSheet(GROUP_STYLE)
        svg_inner = QVBoxLayout(svg_group)
        self.svg_widget = QSvgWidget()
        self.svg_widget.setMinimumSize(280, 240)
        self.svg_widget.setStyleSheet("background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 4px;")
        svg_inner.addWidget(self.svg_widget)
        right_layout.addWidget(svg_group)

        # 结果显示
        result_group = QGroupBox("计算结果")
        result_group.setStyleSheet(GROUP_STYLE)
        result_layout = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        self.result_text.setStyleSheet(
            "QTextEdit { "
            "font-family: Consolas, 'Microsoft YaHei', monospace; "
            "font-size: 13px; "
            "}"
        )
        result_layout.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # 下载按钮行：清空 → DOCX → PDF
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        for label, style, slot in [
            ("清空", CLEAR_BTN_STYLE, self.clear),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        right_layout.addLayout(btn_layout)

        # 计算按钮（最底部）
        calc_btn = self.make_calc_button("计 算")
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)

        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

    def _create_mode_buttons(self, parent_layout):
        """创建换热型式选择按钮"""
        mode_group = QGroupBox("换热型式")
        mode_group.setStyleSheet(GROUP_STYLE)
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setSpacing(6)

        self.mode_group = QButtonGroup(self)
        modes = ["夹套换热", "盘管换热"]
        for i, mode in enumerate(modes):
            btn = QPushButton(mode)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setStyleSheet(MODE_BUTTON_STYLE)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.mode_group.addButton(btn, i)
            mode_layout.addWidget(btn)

        self.mode_group.buttonClicked.connect(self._update_input_visibility)
        parent_layout.addWidget(mode_group)

    def _create_vessel_group(self, parent_layout):
        """创建釜体参数输入组"""
        group = QGroupBox("釜体参数")
        group.setStyleSheet(GROUP_STYLE)
        grid = QGridLayout(group)
        grid.setSpacing(12)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)

        self.inputs = {}
        row = 0

        # 操作体积
        grid.addWidget(QLabel("操作体积 V"), row, 0)
        self.inputs["volume"] = QLineEdit("5.0")
        self.inputs["volume"].setValidator(QDoubleValidator(0.001, 100000, 3))
        grid.addWidget(self.inputs["volume"], row, 1)
        grid.addWidget(QLabel("m³"), row, 2)
        row += 1

        # 釜体直径
        grid.addWidget(QLabel("釜体内径 D"), row, 0)
        self.inputs["diameter"] = QLineEdit("1.6")
        self.inputs["diameter"].setValidator(QDoubleValidator(0.1, 100, 3))
        grid.addWidget(self.inputs["diameter"], row, 1)
        grid.addWidget(QLabel("m"), row, 2)
        row += 1

        # 长径比 → 自动算筒体高度
        grid.addWidget(QLabel("高径比 H/D"), row, 0)
        self.inputs["aspect_ratio"] = QLineEdit("2.0")
        self.inputs["aspect_ratio"].setValidator(QDoubleValidator(0.5, 10, 2))
        grid.addWidget(self.inputs["aspect_ratio"], row, 1)
        grid.addWidget(QLabel("筒体高=H/D×D"), row, 2)
        row += 1

        # 夹套相关（默认显示）
        self.jacket_height_ratio_label = QLabel("夹套高度占比")
        grid.addWidget(self.jacket_height_ratio_label, row, 0)
        self.inputs["jacket_height_ratio"] = QLineEdit("0.75")
        self.inputs["jacket_height_ratio"].setValidator(QDoubleValidator(0.1, 1.0, 2))
        grid.addWidget(self.inputs["jacket_height_ratio"], row, 1)
        self.jacket_height_ratio_unit = QLabel("占筒体高")
        grid.addWidget(self.jacket_height_ratio_unit, row, 2)
        row += 1

        # 盘管相关（默认隐藏）
        self.coil_od_label = QLabel("盘管外径 do")
        grid.addWidget(self.coil_od_label, row, 0)
        self.inputs["coil_od"] = QLineEdit("0.057")
        self.inputs["coil_od"].setValidator(QDoubleValidator(0.01, 0.5, 3))
        grid.addWidget(self.inputs["coil_od"], row, 1)
        self.coil_od_unit = QLabel("m")
        grid.addWidget(self.coil_od_unit, row, 2)
        row += 1

        self.coil_dc_label = QLabel("盘管圈径 Dc")
        grid.addWidget(self.coil_dc_label, row, 0)
        self.inputs["coil_dc"] = QLineEdit("1.2")
        self.inputs["coil_dc"].setValidator(QDoubleValidator(0.1, 50, 3))
        grid.addWidget(self.inputs["coil_dc"], row, 1)
        self.coil_dc_unit = QLabel("m")
        grid.addWidget(self.coil_dc_unit, row, 2)
        row += 1

        self.coil_pitch_label = QLabel("盘管螺距 p")
        grid.addWidget(self.coil_pitch_label, row, 0)
        self.inputs["coil_pitch"] = QLineEdit("0.08")
        self.inputs["coil_pitch"].setValidator(QDoubleValidator(0.01, 1.0, 3))
        grid.addWidget(self.inputs["coil_pitch"], row, 1)
        self.coil_pitch_unit = QLabel("m")
        grid.addWidget(self.coil_pitch_unit, row, 2)
        row += 1

        # 釜内介质
        grid.addWidget(QLabel("釜内介质"), row, 0)
        self.inputs["vessel_medium"] = QComboBox()
        self.inputs["vessel_medium"].addItems(list(VESSEL_MEDIA.keys()))
        self.inputs["vessel_medium"].setStyleSheet(COMBOBOX_STYLE)
        self.inputs["vessel_medium"].currentTextChanged.connect(self._on_medium_changed)
        grid.addWidget(self.inputs["vessel_medium"], row, 1)
        grid.addWidget(QLabel("自动填入物性"), row, 2)
        row += 1

        # 釜内温度
        grid.addWidget(QLabel("釜内温度 t_v"), row, 0)
        self.inputs["vessel_temp"] = QLineEdit("60")
        self.inputs["vessel_temp"].setValidator(QDoubleValidator(-50, 500, 1))
        grid.addWidget(self.inputs["vessel_temp"], row, 1)
        grid.addWidget(QLabel("°C"), row, 2)
        row += 1

        # 搅拌器
        grid.addWidget(QLabel("搅拌桨直径 d_i"), row, 0)
        self.inputs["impeller_d"] = QLineEdit("0.53")
        self.inputs["impeller_d"].setValidator(QDoubleValidator(0.05, 50, 3))
        grid.addWidget(self.inputs["impeller_d"], row, 1)
        grid.addWidget(QLabel("m（无搅拌填0）"), row, 2)
        row += 1

        grid.addWidget(QLabel("搅拌转速 n"), row, 0)
        self.inputs["impeller_n"] = QLineEdit("120")
        self.inputs["impeller_n"].setValidator(QDoubleValidator(0, 3000, 1))
        grid.addWidget(self.inputs["impeller_n"], row, 1)
        grid.addWidget(QLabel("r/min"), row, 2)

        parent_layout.addWidget(group)

        # 初始填充物性
        self._on_medium_changed("水")

    def _create_media_group(self, parent_layout):
        """创建换热介质参数组"""
        group = QGroupBox("换热介质")
        group.setStyleSheet(GROUP_STYLE)
        grid = QGridLayout(group)
        grid.setSpacing(12)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)

        row = 0

        # 介质类型下拉
        grid.addWidget(QLabel("介质类型"), row, 0)
        self.inputs["media_type"] = QComboBox()
        self.inputs["media_type"].addItems(list(MEDIA_TYPES.keys()))
        self.inputs["media_type"].setStyleSheet(COMBOBOX_STYLE)
        self.inputs["media_type"].currentTextChanged.connect(self._on_media_type_changed)
        grid.addWidget(self.inputs["media_type"], row, 1)
        grid.addWidget(QLabel(""), row, 2)
        row += 1

        # 蒸汽相关（默认显示）
        grid.addWidget(QLabel("蒸汽表压"), row, 0)
        self.inputs["steam_pressure"] = QLineEdit("0.3")
        self.inputs["steam_pressure"].setValidator(QDoubleValidator(0, 10, 3))
        self.steam_p_label = QLabel("蒸汽表压")
        grid.addWidget(self.inputs["steam_pressure"], row, 1)
        self.steam_p_unit = QLabel("MPa(g)")
        grid.addWidget(self.steam_p_unit, row, 2)
        row += 1

        # 介质进口温度
        grid.addWidget(QLabel("介质进口 t_h1"), row, 0)
        self.inputs["media_in_temp"] = QLineEdit("143")
        self.inputs["media_in_temp"].setValidator(QDoubleValidator(-50, 600, 1))
        self.media_in_label = QLabel("介质进口 t_h1")
        grid.addWidget(self.inputs["media_in_temp"], row, 1)
        self.media_in_unit = QLabel("°C（蒸汽=饱和温度）")
        grid.addWidget(self.media_in_unit, row, 2)
        row += 1

        # 介质出口温度
        grid.addWidget(QLabel("介质出口 t_h2"), row, 0)
        self.inputs["media_out_temp"] = QLineEdit("143")
        self.inputs["media_out_temp"].setValidator(QDoubleValidator(-50, 600, 1))
        self.media_out_label = QLabel("介质出口 t_h2")
        grid.addWidget(self.inputs["media_out_temp"], row, 1)
        self.media_out_unit = QLabel("°C（蒸汽=冷凝温度）")
        grid.addWidget(self.media_out_unit, row, 2)
        row += 1

        # 介质流量（水/油模式）
        grid.addWidget(QLabel("介质流量"), row, 0)
        self.inputs["media_flow"] = QLineEdit("5000")
        self.inputs["media_flow"].setValidator(QDoubleValidator(0, 1e7, 1))
        self.media_flow_label = QLabel("介质流量")
        grid.addWidget(self.inputs["media_flow"], row, 1)
        self.media_flow_unit = QLabel("kg/h")
        grid.addWidget(self.media_flow_unit, row, 2)
        row += 1

        parent_layout.addWidget(group)

    def _create_advanced_group(self, parent_layout):
        """创建高级参数组"""
        group = QGroupBox("高级参数")
        group.setStyleSheet(GROUP_STYLE)
        grid = QGridLayout(group)
        grid.setSpacing(12)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)

        row = 0

        # 釜体壁厚
        grid.addWidget(QLabel("釜体壁厚 δ"), row, 0)
        self.inputs["wall_thickness"] = QLineEdit("0.012")
        self.inputs["wall_thickness"].setValidator(QDoubleValidator(0.001, 0.2, 4))
        grid.addWidget(self.inputs["wall_thickness"], row, 1)
        grid.addWidget(QLabel("m"), row, 2)
        row += 1

        # 釜体材质
        grid.addWidget(QLabel("釜体材质"), row, 0)
        self.inputs["wall_material"] = QComboBox()
        self.inputs["wall_material"].addItems(list(WALL_MATERIALS.keys()))
        self.inputs["wall_material"].setStyleSheet(COMBOBOX_STYLE)
        self.inputs["wall_material"].currentTextChanged.connect(self._on_wall_mtrl_changed)
        grid.addWidget(self.inputs["wall_material"], row, 1)
        grid.addWidget(QLabel(""), row, 2)
        row += 1

        # 自定义导热系数
        grid.addWidget(QLabel("导热系数 λ"), row, 0)
        self.inputs["wall_lambda"] = QLineEdit("16.3")
        self.inputs["wall_lambda"].setValidator(QDoubleValidator(0.01, 500, 2))
        grid.addWidget(self.inputs["wall_lambda"], row, 1)
        grid.addWidget(QLabel("W/(m·K)"), row, 2)
        row += 1

        # 污垢热阻
        grid.addWidget(QLabel("污垢热阻类型"), row, 0)
        self.inputs["fouling_type"] = QComboBox()
        self.inputs["fouling_type"].addItems(list(FOULING_RESISTANCE.keys()))
        self.inputs["fouling_type"].setStyleSheet(COMBOBOX_STYLE)
        self.inputs["fouling_type"].currentTextChanged.connect(self._on_fouling_changed)
        grid.addWidget(self.inputs["fouling_type"], row, 1)
        grid.addWidget(QLabel(""), row, 2)
        row += 1

        grid.addWidget(QLabel("釜内侧 R_fi"), row, 0)
        self.inputs["fouling_inner"] = QLineEdit("0.0002")
        self.inputs["fouling_inner"].setValidator(QDoubleValidator(0, 0.01, 6))
        grid.addWidget(self.inputs["fouling_inner"], row, 1)
        grid.addWidget(QLabel("m²·K/W"), row, 2)
        row += 1

        grid.addWidget(QLabel("介质侧 R_fo"), row, 0)
        self.inputs["fouling_outer"] = QLineEdit("0.0002")
        self.inputs["fouling_outer"].setValidator(QDoubleValidator(0, 0.01, 6))
        grid.addWidget(self.inputs["fouling_outer"], row, 1)
        grid.addWidget(QLabel("m²·K/W"), row, 2)
        row += 1

        # 安全系数
        grid.addWidget(QLabel("安全系数"), row, 0)
        self.inputs["safety_factor"] = QLineEdit("1.15")
        self.inputs["safety_factor"].setValidator(QDoubleValidator(1.0, 3.0, 2))
        grid.addWidget(self.inputs["safety_factor"], row, 1)
        grid.addWidget(QLabel("面积=理论值×系数"), row, 2)
        row += 1

        parent_layout.addWidget(group)

    # ── 动态UI控制 ─────────────────────────────────────────

    def _update_input_visibility(self, *_):
        """根据换热型式显示/隐藏对应参数（输入框+标签+单位提示一并处理）"""
        is_jacket = self._get_mode() == "jacket"

        # 夹套参数：夹套模式显示，盘管模式隐藏
        jacket_keys = ["jacket_height_ratio"]
        coil_keys = ["coil_od", "coil_dc", "coil_pitch"]

        for key in jacket_keys:
            w = self.inputs.get(key)
            if w:
                w.setVisible(is_jacket)
        self.jacket_height_ratio_label.setVisible(is_jacket)
        self.jacket_height_ratio_unit.setVisible(is_jacket)

        for key in coil_keys:
            w = self.inputs.get(key)
            if w:
                w.setVisible(not is_jacket)
        for lbl in (self.coil_od_label, self.coil_od_unit,
                    self.coil_dc_label, self.coil_dc_unit,
                    self.coil_pitch_label, self.coil_pitch_unit):
            lbl.setVisible(not is_jacket)


    def _on_medium_changed(self, name):
        """釜内介质变更时填物性"""
        data = VESSEL_MEDIA.get(name, {})
        if name != "自定义":
            self.inputs["vessel_temp"].setText("60")
        self._fill_props(data)

    def _on_media_type_changed(self, name):
        """换热介质类型变更时调整界面"""
        info = MEDIA_TYPES.get(name, {})
        is_steam = (info.get("mode") == "steam")
        is_custom = (info.get("mode") == "custom")

        # 蒸汽模式下隐藏流量和出口温度编辑
        self.inputs["media_flow"].setEnabled(not is_steam)
        self.inputs["media_out_temp"].setReadOnly(is_steam)
        if is_steam:
            self.inputs["media_out_temp"].setText(self.inputs["media_in_temp"].text())

    def _on_wall_mtrl_changed(self, name):
        """釜体材质变更"""
        lbd = WALL_MATERIALS.get(name)
        if lbd is not None:
            self.inputs["wall_lambda"].setText(str(lbd))

    def _on_fouling_changed(self, name):
        """污垢热阻类型变更"""
        vals = FOULING_RESISTANCE.get(name, (None, None))
        if vals[0] is not None:
            self.inputs["fouling_inner"].setText(str(vals[0]))
            self.inputs["fouling_outer"].setText(str(vals[1]))

    def _fill_props(self, data):
        """向物性输入框填充默认值（为扩展预留）"""
        pass  # 当前物性从字典直接读取

    def _get_mode(self):
        """获取当前换热型式"""
        return "jacket" if self.mode_group.checkedId() == 0 else "coil"

    # ── 计算引擎 ────────────────────────────────────────────

    def calculate(self):
        """执行计算"""
        try:
            mode = self._get_mode()
            D = float(self.inputs["diameter"].text())  # m
            H_D = float(self.inputs["aspect_ratio"].text())
            H = D * H_D  # 筒体高度
            t_v = float(self.inputs["vessel_temp"].text())  # °C

            # ── 釜内介质物性（取操作温度） ──
            name = self.inputs["vessel_medium"].currentText()
            mdata = VESSEL_MEDIA[name]
            rho = mdata["rho"] if mdata["rho"] is not None else float(self._safe("vessel_density", "1000"))
            cp = mdata["cp"] if mdata["cp"] is not None else 4.181
            k_v = mdata["k"] if mdata["k"] is not None else 0.6
            mu = mdata["mu"] if mdata["mu"] is not None else 0.001

            # ── 可用换热面积 ──
            if mode == "jacket":
                ratio = float(self.inputs["jacket_height_ratio"].text())
                H_j = H * ratio
                A_avail = math.pi * D * H_j  # 圆筒部分 + 忽略封头
                A_avail += math.pi * D * D / 4  # 下封头近似
            else:
                do = float(self.inputs["coil_od"].text())
                Dc = float(self.inputs["coil_dc"].text())
                pitch = float(self.inputs["coil_pitch"].text())
                H_eff = H * 0.7  # 盘管有效高度
                n_coils = H_eff / pitch
                L_coil = n_coils * math.pi * Dc
                A_avail = math.pi * do * L_coil

            # ── 换热介质侧 ──
            media_name = self.inputs["media_type"].currentText()
            media_info = MEDIA_TYPES[media_name]
            is_steam = (media_info["mode"] == "steam")

            if is_steam:
                p_steam = float(self.inputs["steam_pressure"].text())
                props = get_steam_props(p_steam)
                T_steam = props["sat_temp"]
                h_fg = props["h_fg"]
                T_h1 = T_steam
                T_h2 = T_steam
                # 蒸汽流量（实际需从热负荷反推，这里用输入值）
                m_s = float(self.inputs["media_flow"].text()) if self.inputs["media_flow"].text() else 0
                if m_s <= 0 and t_v < T_steam:
                    # 估算蒸汽量（先粗算热负荷）
                    Q_heat_est = A_avail * 500 * (T_steam - t_v) / 1000  # kW
                    m_s = Q_heat_est * 3600 / h_fg  # kg/h
                Q_kW = m_s * h_fg / 3600
            else:
                T_h1 = float(self.inputs["media_in_temp"].text())
                T_h2 = float(self.inputs["media_out_temp"].text())
                m = float(self.inputs["media_flow"].text())
                if media_info["mode"] == "oil":
                    cp_m = 2.9
                else:
                    cp_m = WATER_CP
                Q_kW = m * cp_m * abs(T_h1 - T_h2) / 3600

            # ── 对数平均温差 ──
            dT1 = T_h1 - t_v
            dT2 = T_h2 - t_v
            if dT1 <= 0 or dT2 <= 0:
                QMessageBox.warning(self, "温度错误",
                                    f"换热介质温度必须高于釜内温度\n介质={T_h1}~{T_h2}°C, 釜内={t_v}°C")
                return
            if abs(dT1 - dT2) < 0.01:
                LMTD = (dT1 + dT2) / 2
            else:
                LMTD = (dT1 - dT2) / math.log(dT1 / dT2)

            # ── 釜内侧给热系数 h_i ──
            d_impeller = float(self.inputs["impeller_d"].text())
            n_rpm = float(self.inputs["impeller_n"].text())
            if d_impeller > 0 and n_rpm > 0:
                n_rps = n_rpm / 60.0
                Re = rho * n_rps * d_impeller**2 / mu
                Pr = cp * 1000 * mu / k_v
                if mode == "jacket":
                    Nu = 0.36 * Re**0.67 * Pr**0.33
                else:
                    Nu = 0.87 * Re**0.62 * Pr**0.33
                h_i = Nu * k_v / D
            else:
                # 自然对流
                Pr = cp * 1000 * mu / k_v
                beta = 1.0 / (t_v + 273.15)
                dT_nat = abs(T_h1 - t_v)
                Gr = rho**2 * G * beta * dT_nat * D**3 / mu**2
                Ra = Gr * Pr
                Nu = 0.13 * Ra**0.333
                h_i = Nu * k_v / D

            # ── 换热介质侧给热系数 h_o ──
            if is_steam:
                h_o = 8000  # W/(m²·K) 蒸汽冷凝典型值
                self._re_warning = None
            elif mode == "jacket":
                # 夹套内给热系数（特征尺寸取夹套间隙）
                gap = 0.05  # 夹套间隙 m
                flow_area = math.pi * D * gap
                m_media = float(self.inputs["media_flow"].text())
                rho_m = WATER_DENSITY
                mu_m = 0.001
                if m_media > 0 and flow_area > 0:
                    v = m_media / (3600 * rho_m * flow_area)
                    De = 2 * gap  # 水力直径
                    Re_o = rho_m * v * De / mu_m
                    Pr_o = WATER_CP * 1000 * mu_m / (0.6 if media_info["mode"] == "water" else 0.15)
                    Nu_o = 0.023 * Re_o**0.8 * Pr_o**0.4
                    h_o = Nu_o * (0.6 if media_info["mode"] == "water" else 0.15) / De
                    if Re_o < 4000:
                        self._re_warning = (f"⚠ 夹套侧 Re≈{Re_o:.0f}，处于层流/过渡区，"
                                            "Dittus-Boelter 关联式适用性差，介质侧 h_o 仅供粗估")
                    else:
                        self._re_warning = None
                else:
                    h_o = 1500
                    self._re_warning = None
            else:
                # 盘管内给热系数
                do = float(self.inputs["coil_od"].text())
                di = do - 0.004  # 默认壁厚2mm
                Dc = float(self.inputs["coil_dc"].text())
                m_media = float(self.inputs["media_flow"].text())
                if m_media > 0:
                    rho_m = WATER_DENSITY
                    mu_m = 0.001
                    Ai_coil = math.pi * di**2 / 4
                    v = m_media / (3600 * rho_m * Ai_coil)
                    Re_o = rho_m * v * di / mu_m
                    Pr_o = WATER_CP * 1000 * mu_m / 0.6
                    Nu_straight = 0.023 * Re_o**0.8 * Pr_o**0.4
                    Nu_o = Nu_straight * (1 + 3.5 * di / Dc)
                    h_o = Nu_o * 0.6 / di
                    if Re_o < 4000:
                        self._re_warning = (f"⚠ 盘管内 Re≈{Re_o:.0f}，处于层流/过渡区，"
                                            "Dittus-Boelter 关联式适用性差，介质侧 h_o 仅供粗估")
                    else:
                        self._re_warning = None
                else:
                    h_o = 2000
                    self._re_warning = None

            # ── 总传热系数 ──
            delta = float(self.inputs["wall_thickness"].text())
            lbd_w = float(self.inputs["wall_lambda"].text())
            R_fi = float(self.inputs["fouling_inner"].text())
            R_fo = float(self.inputs["fouling_outer"].text())

            K = 1.0 / (1.0 / h_i + delta / lbd_w + 1.0 / h_o + R_fi + R_fo)

            # ── 所需面积 ──
            safety = float(self.inputs["safety_factor"].text())
            A_req = (Q_kW * 1000) / (K * LMTD) * safety

            # ── 裕量 ──
            if A_avail > 0:
                margin = (A_avail - A_req) / A_req * 100
            else:
                margin = -100

            # ── 存储结果 ──
            self._last_area_avail = A_avail
            self._last_area_req = A_req
            self._last_margin = margin
            self._last_K = K
            self._last_Q = Q_kW
            self._last_lmtd = LMTD

            # ── 输出结果 ──
            lines = []
            mode_name = "夹套换热" if mode == "jacket" else "盘管换热"
            lines.append(f"══════ {mode_name} 核算结果 ══════")
            lines.append(f"")
            lines.append(f"【换热面积】")
            lines.append(f"  可用换热面积 A₀:  {A_avail:.3f} m²")
            lines.append(f"  所需换热面积 A:   {A_req:.3f} m²")
            lines.append(f"  面积裕量:        {margin:+.1f} %")
            status = "✅ 满足要求" if margin >= 0 else "❌ 面积不足！"
            lines.append(f"  结论: {status}")
            lines.append(f"")
            lines.append(f"【传热参数】")
            lines.append(f"  总传热系数 K:     {K:.1f} W/(m²·K)")
            lines.append(f"  釜内侧 h_i:       {h_i:.1f} W/(m²·K)")
            lines.append(f"  介质侧 h_o:       {h_o:.1f} W/(m²·K)")
            lines.append(f"  热负荷 Q:         {Q_kW:.1f} kW")
            lines.append(f"  对数平均温差:     {LMTD:.1f} °C")
            if getattr(self, "_re_warning", None):
                lines.append(f"  {self._re_warning}")
            lines.append(f"")
            lines.append(f"【换热介质】")
            if is_steam:
                lines.append(f"  饱和蒸汽 {p_steam:.1f} MPa(g) = {T_steam:.1f}°C")
                lines.append(f"  汽化潜热: {h_fg:.0f} kJ/kg")
                lines.append(f"  蒸汽用量: {m_s:.0f} kg/h")
            else:
                lines.append(f"  介质: {media_name}")
                lines.append(f"  进口 {T_h1:.1f}°C → 出口 {T_h2:.1f}°C")
                lines.append(f"  流量: {m:.0f} kg/h")
            if mode == "jacket":
                lines.append(f"  夹套高度: {H * float(self.inputs['jacket_height_ratio'].text()):.2f} m")
            else:
                lines.append(f"  盘管长度: {L_coil:.1f} m ({n_coils:.0f} 圈)")

            self.result_text.setText("\n".join(lines))
            self._update_svg_diagram()

        except ValueError as e:
            QMessageBox.critical(self, "输入错误", f"参数格式不正确: {e}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "参数不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算异常: {e}")

    def _safe(self, key, default):
        """安全获取输入值"""
        w = self.inputs.get(key)
        if w is None:
            return default
        text = w.text() if hasattr(w, 'text') else str(w)
        try:
            return text
        except Exception:
            return default

    # ── SVG 示意图 ──────────────────────────────────────────

    def _update_svg_diagram(self):
        """更新 SVG 示意图"""
        try:
            mode = self._get_mode()
            D = float(self.inputs["diameter"].text())
            H_D = float(self.inputs["aspect_ratio"].text())
            H = D * H_D
            t_v = float(self.inputs["vessel_temp"].text())

            if mode == "jacket":
                ratio = float(self.inputs["jacket_height_ratio"].text())
                svg = self._build_jacket_svg(D, H, ratio, t_v)
            else:
                do = float(self.inputs["coil_od"].text())
                Dc = float(self.inputs["coil_dc"].text())
                svg = self._build_coil_svg(D, H, Dc, do, t_v)

            self.svg_widget.load(svg.encode("utf-8"))
        except Exception:
            self.svg_widget.load(self._build_fallback_svg().encode("utf-8"))

    def _build_jacket_svg(self, D, H, ratio, t_v):
        """绘制夹套釜 SVG"""
        parts = [svg_start(680, 380)]

        # 缩放
        ws, hs = 340, 340
        max_dim = max(D, H * 1.3)
        scale = 280 / max_dim

        # 釜体中心
        cx, top_y = ws, hs - int(H * scale / 2)
        w_px = int(D * scale)
        h_px = int(H * scale)

        # 釜体（筒体 + 椭圆底）
        parts.append(svg_rect(cx - w_px // 2, top_y, w_px, h_px, fill="#e8f0fe", stroke="#4a6fa5", stroke_width=2, rx=0))
        # 椭圆封头底
        parts.append(
            '<ellipse cx="{0}" cy="{1}" rx="{2}" ry="{3}" fill="#dce8f5" stroke="#4a6fa5" stroke-width="2"/>'.format(
                cx, top_y + h_px, w_px // 2, int(w_px // 4)))

        # 夹套（外轮廓虚线）
        j_top = top_y + int(h_px * (1 - ratio))
        j_h = h_px - int(h_px * (1 - ratio))
        pad = 12
        parts.append(svg_rect(cx - w_px // 2 - pad, j_top, w_px + 2 * pad, j_h,
                               fill="none", stroke="#e74c3c", stroke_width=2.5, rx=2))
        # 虚线效果用白色覆盖重绘
        parts.append(svg_rect(cx - w_px // 2 - pad, j_top, w_px + 2 * pad, j_h,
                               fill="none", stroke="#e74c3c", stroke_width=2.5, rx=2))

        # 标注
        parts.append(svg_text(cx, top_y - 18, f"釜内径 D={D:.2f}m", size=10, color="#4a6fa5", bold=True))
        parts.append(svg_text(cx - w_px // 2 - pad - 50, j_top + j_h // 2, f"夹套", size=9, color="#e74c3c", bold=True))
        parts.append(svg_text(cx + w_px // 2 + pad + 45, j_top + j_h // 2, f"H_j={H * ratio:.2f}m", size=9, color="#e74c3c"))
        parts.append(svg_text(cx, top_y + h_px + w_px // 4 + 16, f"釜内温度 t_v={t_v:.0f}°C", size=10, color="#333", bold=True))

        # 蒸汽入口 → 冷凝水出口
        parts.append(svg_text(cx + w_px // 2 + pad + 45, j_top + 15, f"蒸汽进", size=8, color="#c0392b"))
        parts.append(svg_line(cx + w_px // 2, j_top + 10, cx + w_px // 2 + pad + 40, j_top + 10, stroke="#c0392b", stroke_width=2))
        parts.append(svg_text(cx + w_px // 2 + pad + 45, j_top + j_h - 5, f"冷凝水出", size=8, color="#2980b9"))
        parts.append(svg_line(cx + w_px // 2, j_top + j_h - 10, cx + w_px // 2 + pad + 40, j_top + j_h - 10, stroke="#2980b9", stroke_width=2))

        parts.append(svg_end())
        return "".join(parts)

    def _build_coil_svg(self, D, H, Dc, do, t_v):
        """绘制盘管釜 SVG"""
        parts = [svg_start(680, 380)]

        ws, hs = 340, 340
        max_dim = max(D, H * 1.3)
        scale = 280 / max_dim

        cx, top_y = ws, hs - int(H * scale / 2)
        w_px = int(D * scale)
        h_px = int(H * scale)

        # 釜体
        parts.append(svg_rect(cx - w_px // 2, top_y, w_px, h_px, fill="#e8f0fe", stroke="#4a6fa5", stroke_width=2, rx=0))
        parts.append(
            '<ellipse cx="{0}" cy="{1}" rx="{2}" ry="{3}" fill="#dce8f5" stroke="#4a6fa5" stroke-width="2"/>'.format(
                cx, top_y + h_px, w_px // 2, int(w_px // 4)))

        # 盘管（螺旋线简化为水平波纹）
        dc_px = int(Dc * scale)
        coil_top = top_y + int(h_px * 0.15)
        coil_bot = top_y + int(h_px * 0.85)
        n_turns = 8
        turn_h = (coil_bot - coil_top) / n_turns

        for i in range(n_turns):
            cy_i = coil_top + int((i + 0.5) * turn_h)
            r_coil = dc_px // 2
            parts.append(
                '<ellipse cx="{0}" cy="{1}" rx="{2}" ry="{3}" fill="none" stroke="#e67e22" stroke-width="2.5"/>'.format(
                    cx, cy_i, r_coil, int(turn_h * 0.4)))

        # 盘管进出口
        parts.append(svg_text(cx - dc_px // 2 - 55, coil_top - 5, "介质进", size=8, color="#e67e22", bold=True))
        parts.append(svg_line(cx - dc_px // 2, coil_top, cx - dc_px // 2 - 50, coil_top, stroke="#e67e22", stroke_width=2))
        parts.append(svg_text(cx - dc_px // 2 - 55, coil_bot + 5, "介质出", size=8, color="#2980b9", bold=True))
        parts.append(svg_line(cx - dc_px // 2, coil_bot, cx - dc_px // 2 - 50, coil_bot, stroke="#2980b9", stroke_width=2))

        parts.append(svg_text(cx, top_y - 18, f"釜内径 D={D:.2f}m", size=10, color="#4a6fa5", bold=True))
        parts.append(svg_text(cx, top_y + h_px + w_px // 4 + 16, f"釜内温度 ={t_v:.0f}°C", size=10, color="#333", bold=True))
        parts.append(svg_text(cx, coil_top - 22, f"盘管 Dc={Dc:.2f}m  do={do * 1000:.0f}mm", size=9, color="#e67e22"))

        parts.append(svg_end())
        return "".join(parts)

    def _build_fallback_svg(self):
        """默认 SVG"""
        parts = [svg_start(680, 380)]
        parts.append(svg_text(340, 190, "请输入参数后点击计算", size=14, color="#999"))
        parts.append(svg_end())
        return "".join(parts)

    # ── 清空 ────────────────────────────────────────────────

    def clear(self):
        """清空所有输入"""
        defaults = {
            "volume": "5.0", "diameter": "1.6", "aspect_ratio": "2.0",
            "jacket_height_ratio": "0.75",
            "coil_od": "0.057", "coil_dc": "1.2", "coil_pitch": "0.08",
            "vessel_temp": "60", "impeller_d": "0.53", "impeller_n": "120",
            "steam_pressure": "0.3", "media_in_temp": "143", "media_out_temp": "143",
            "media_flow": "5000",
            "wall_thickness": "0.012", "wall_lambda": "16.3",
            "fouling_inner": "0.0002", "fouling_outer": "0.0002",
            "safety_factor": "1.15",
        }
        for key, val in defaults.items():
            w = self.inputs.get(key)
            if w and hasattr(w, 'setText'):
                w.setText(val)
        self.result_text.clear()
        self._update_svg_diagram()

    # ── 报告导出 ─────────────────────────────────────────────

    def get_project_info(self):
        return {
            "project_name": "夹套/盘管换热面积核算",
            "calculator_name": "夹套/盘管换热面积计算器",
            "version": "1.0",
            "description": "夹套/盘管两种换热型式：给热系数计算 → 总传热系数 → 面积核算与裕量"
        }

    def generate_report(self):
        """生成报告文本"""
        lines = []
        lines.append("夹套/盘管换热面积核算报告")
        lines.append("=" * 50)
        lines.append(self.result_text.toPlainText())
        return "\n".join(lines)

    def download_docx_report(self):
        """生成 DOCX 计算书"""
        ReportExporter.export_docx(self, "夹套盘管换热面积")

    def download_pdf_report(self):
        """生成 PDF 计算书"""
        ReportExporter.export_pdf(self, "夹套盘管换热面积")

    def _get_history_data(self):
        """历史记录数据"""
        mode_name = "夹套换热" if self._get_mode() == "jacket" else "盘管换热"
        inputs = {
            "换热型式": mode_name,
            "釜体直径_m": self._safe_num("diameter"),
            "高径比": self._safe_num("aspect_ratio"),
            "釜内温度_C": self._safe_num("vessel_temp"),
        }
        outputs = {}
        if self._last_K is not None:
            outputs = {
                "可用面积_m2": round(self._last_area_avail, 3),
                "所需面积_m2": round(self._last_area_req, 3),
                "面积裕量_%": round(self._last_margin, 1),
                "总传热系数_W_m2K": round(self._last_K, 1),
                "热负荷_kW": round(self._last_Q, 1),
                "LMTD_C": round(self._last_lmtd, 1),
            }
        return {"inputs": inputs, "outputs": outputs}

    def _safe_num(self, key):
        """安全获取数值"""
        w = self.inputs.get(key)
        if w and hasattr(w, 'text'):
            try:
                return float(w.text())
            except Exception:
                return None
        return None


# 为动态导入提供简洁别名
jacket_coil_calculator = JacketCoilCalculator
