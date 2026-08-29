"""
pH 计算器 — 酸碱中和 / 缓冲溶液 / 稀释 / pH 调节

四种计算模式：
  1. 酸碱中和：已知酸液浓度和体积，计算所需碱液（或反之）
  2. 缓冲溶液：Henderson-Hasselbalch 方程计算缓冲液 pH
  3. 稀释计算：加水稀释后 pH 变化
  4. pH 调节：从当前 pH 调到目标 pH 所需酸/碱量

"""
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QScrollArea,
    QButtonGroup, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QCheckBox

from calculator_base import CalculatorBase
from app_styles import (INPUT_LABEL_STYLE, CLEAR_BTN_STYLE,
                        DOCX_BTN_STYLE, PDF_BTN_STYLE)
from utils.docx_utils import ReportExporter

# ── 常见弱酸/弱碱 pKa/pKb 参照 ──
# (名称, 类型 acid/base, pK 值, 温度)
PK_TABLE = {
    "醋酸/醋酸钠":     ("酸", 4.76, 25),
    "磷酸二氢盐/磷酸一氢盐": ("酸", 7.21, 25),
    "碳酸/碳酸氢盐":   ("酸", 6.35, 25),
    "碳酸氢盐/碳酸盐": ("酸", 10.33, 25),
    "柠檬酸/柠檬酸钠": ("酸", 3.13, 25),
    "氨水/氯化铵":     ("碱", 4.75, 25),
    "Tris-HCl":        ("碱", 8.07, 25),
}

# ── pH 调节常用酸碱预设 ──
# 元组: (类型 acid/base, 形态, 密度g/mL或MW, 含量%, 分子量, n_val)
#  液体: C(mol/L) = 含量% × 密度 × 10 / 分子量
#  固体: 每克有效 mol = 含量% × n_val / (分子量 × 100)
ADJUST_REAGENTS = {
    # ── 液体酸 ──
    "盐酸 31% (工业)":       ("酸", "液体", 1.16,  31,  36.46,  1),
    "盐酸 36% (浓)":         ("酸", "液体", 1.18,  36,  36.46,  1),
    "硫酸 93% (工业)":       ("酸", "液体", 1.83,  93,  98.08,  2),
    "硫酸 98% (浓)":         ("酸", "液体", 1.84,  98,  98.08,  2),
    "磷酸 75% (工业)":       ("酸", "液体", 1.58,  75,  98.00,  3),
    "磷酸 85% (食品级)":     ("酸", "液体", 1.69,  85,  98.00,  3),
    "冰醋酸 99.5%":          ("酸", "液体", 1.05,  99.5, 60.05,  1),

    # ── 液体碱 ──
    "液碱 NaOH 30%":         ("碱", "液体", 1.33,  30,  40.00,  1),
    "液碱 NaOH 32%":         ("碱", "液体", 1.35,  32,  40.00,  1),
    "液碱 NaOH 50%":         ("碱", "液体", 1.53,  50,  40.00,  1),
    "氨水 20%":              ("碱", "液体", 0.92,  20,  35.05,  1),
    "氨水 25%":              ("碱", "液体", 0.91,  25,  35.05,  1),

    # ── 固体酸碱 ──
    "NaOH 片碱 (99%)":       ("碱", "固体", 40.00,  99, None,   1),
    "Ca(OH)₂ 石灰 (95%)":   ("碱", "固体", 74.00,  95, None,   2),
    "Na₂CO₃ 纯碱 (99%)":     ("碱", "固体", 106.0,  99, None,   2),
    "柠檬酸 (无水, 99%)":    ("酸", "固体", 192.1,  99, None,   3),

    # ── 自定义 ──
    "自定义液体":             ("",  "液体", 1.00,  10, 1.0,    1),
    "自定义固体":             ("",  "固体", 1.00, 100, None,   1),
}

# ── 酸碱分子量（快速查） ──
_REAGENT_MW = {
    "HCl": 36.46, "H2SO4": 98.08, "NaOH": 40.00,
    "H3PO4": 98.00, "CH3COOH": 60.05, "NH3": 35.05,
    "Ca(OH)2": 74.00, "Na2CO3": 106.0, "C6H8O7": 192.1,
}


class PHCalculator(CalculatorBase):
    """pH 计算器 v1.0"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent, data_manager)
        self._last_results = {}
        self._mode_widgets = {}       # mode → {name: widget}
        self._all_inputs = {}         # 全部输入控件统一引用
        self.setup_ui()
        self.setup_wheel_blocker()

    # ═════════════════════════════════════════
    #  UI
    # ═════════════════════════════════════════

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ── 左 ──
        scroll = QScrollArea()
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } "
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left = QWidget()
        left.setStyleSheet("")
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(15)

        desc = QLabel("pH 计算 — 酸碱中和 / 缓冲溶液 / 稀释 / 调节")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc)

        # ── 模式按钮 ──
        mode_group = QGroupBox("计算模式")
        mode_ly = QHBoxLayout(mode_group)
        self.mode_btn_group = QButtonGroup(self)
        self.mode_btns = {}
        modes = [
            ("酸碱中和", "已知酸浓度, 求所需碱量（或反之）"),
            ("缓冲溶液 pH", "Henderson-Hasselbalch 缓冲液 pH"),
            ("稀释后 pH", "加水稀释后的 pH 变化"),
            ("pH 调节", "调至目标 pH 所需酸/碱量"),
        ]
        for i, (name, tip) in enumerate(modes):
            btn = CalculatorBase.make_mode_button(name, tip)
            self.mode_btns[name] = btn
            self.mode_btn_group.addButton(btn, i)
            mode_ly.addWidget(btn)
        self.mode_btn_group.buttonClicked.connect(self._on_mode)
        self.mode_btns["酸碱中和"].setChecked(True)
        left_layout.addWidget(mode_group)

        # ── 四个面板（切换模式时显隐） ──
        self._create_neutralize_panel(left_layout)
        self._create_buffer_panel(left_layout)
        self._create_dilute_panel(left_layout)
        self._create_adjust_panel(left_layout)
        self._on_mode(self.mode_btns["酸碱中和"])   # 初始显示面板

        left_layout.addStretch()
        scroll.setWidget(left)
        main_layout.addWidget(scroll, 2)

        # ── 右栏: 结果（顶）→ 下载按钮（中）→ 计算按钮（底） ──
        right = QWidget()
        right.setMinimumWidth(300)
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(15)

        result_group = QGroupBox("计算结果")
        rl = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)   # 给个最小高度够看清结果即可
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        self.result_text.setStyleSheet(
            "QTextEdit { "
            "font-family: Consolas, 'Microsoft YaHei', monospace; "
            "font-size: 13px; "
            "}"
        )
        rl.addWidget(self.result_text)
        right_layout.addWidget(result_group)      # 不加 stretch，让它自然高度

        # 下载按钮行（居中，位于结果下方）
        btn_layout = QHBoxLayout()
        for name, style, cb in [
            ("清空", CLEAR_BTN_STYLE, self.clear),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            b = QPushButton(name)
            b.setStyleSheet(style)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.clicked.connect(cb)
            btn_layout.addWidget(b)
        right_layout.addLayout(btn_layout)

        # 计算按钮：固定在最下方（最大视觉权重）
        calc_btn = CalculatorBase.make_calc_button()
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)

        main_layout.addWidget(right, 1)

    # ── 工厂方法 ──

    def _group(self, title: str) -> QGroupBox:
        gb = CalculatorBase.make_group_box(title)
        gl = QGridLayout(gb)
        gl.setHorizontalSpacing(10)
        gl.setVerticalSpacing(12)
        gl.setColumnStretch(0, 4)
        gl.setColumnStretch(1, 8)
        gl.setColumnStretch(2, 5)
        return gb, gl

    def _lbl(self, text: str) -> QLabel:
        lb = QLabel(text)
        lb.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lb.setStyleSheet(INPUT_LABEL_STYLE)
        return lb

    def _hint(self, text: str) -> QLabel:
        h = QLabel(text)
        h.setStyleSheet("font-style: italic; color: #666;")
        h.setWordWrap(True)
        return h

    def _inp(self, default="", decimals=2) -> QLineEdit:
        ie = QLineEdit(default)
        v = QDoubleValidator()
        v.setDecimals(decimals)
        ie.setValidator(v)
        return ie

    def _combo(self) -> QComboBox:
        cb = CalculatorBase.make_combo_box()
        return cb

    def _add_row(self, grid: QGridLayout, r: int, label: str, name: str,
                  widget: QWidget, hint_text: str = "") -> int:
        lbl = self._lbl(label)
        lbl.setObjectName(f"lbl_{name}")
        grid.addWidget(lbl, r, 0)
        widget.setObjectName(f"w_{name}")
        grid.addWidget(widget, r, 1)
        hint_w = None
        if hint_text:
            hint_w = self._hint(hint_text)
            hint_w.setObjectName(f"hint_{name}")
            grid.addWidget(hint_w, r, 2)
        self._all_inputs[name] = widget
        # 同时保存 label / hint 引用，便于后续显隐
        if not hasattr(self, "_row_widgets"):
            self._row_widgets = {}
        self._row_widgets[name] = {"label": lbl, "input": widget, "hint": hint_w}
        return r + 1

    # ── 四种模式面板 ──

    def _create_neutralize_panel(self, layout):
        gb, g = self._group("酸碱中和")
        r = 0
        r = self._add_row(g, r, "已知侧", "side", self._combo(),
                          "选择\"酸\"表示已知酸浓度, 求所需碱量")
        cb = self._all_inputs["side"]
        cb.addItems(["酸（已知酸,求碱）", "碱（已知碱,求酸）"])
        r = self._add_row(g, r, "已知液浓度", "n_C", self._inp("1.0"),
                          "mol/L")
        r = self._add_row(g, r, "已知液体积", "n_V", self._inp("1.0"),
                          "L")
        r = self._add_row(g, r, "H⁺ / OH⁻ 个数", "n_val", self._inp("1", 0),
                          "HCl=1, H₂SO₄=2, NaOH=1, Ca(OH)₂=2")
        r = self._add_row(g, r, "待求液浓度", "n_other_C", self._inp("1.0"),
                          "mol/L")
        r = self._add_row(g, r, "待求液 H⁺/OH⁻ 个数", "n_other_val", self._inp("1", 0),
                          "所求侧的氢离子或氢氧根个数")
        self._mode_widgets["酸碱中和"] = gb
        gb.setVisible(True)
        layout.addWidget(gb)

    def _create_buffer_panel(self, layout):
        gb, g = self._group("缓冲溶液")
        r = 0
        r = self._add_row(g, r, "缓冲体系", "buf_system", self._combo(),
                          "选择常见缓冲对, 也可手动输 pKa")
        cb = self._all_inputs["buf_system"]
        cb.addItems(["手动输入 pKa"] + list(PK_TABLE.keys()))
        cb.currentTextChanged.connect(self._on_buffer_system)
        r = self._add_row(g, r, "pKa / pKb", "buf_pk", self._inp("4.76"),
                          "弱酸 pKa 或弱碱 pKb")
        r = self._add_row(g, r, "缓冲类型", "buf_type", self._combo(),
                          "酸型=弱酸及其盐 / 碱型=弱碱及其盐")
        cb2 = self._all_inputs["buf_type"]
        cb2.addItems(["酸型（HA/A⁻）", "碱型（B/BH⁺）"])
        r = self._add_row(g, r, "共轭碱浓度 [A⁻]", "buf_salt", self._inp("0.1"),
                          "盐/共轭碱的浓度 mol/L")
        r = self._add_row(g, r, "弱酸浓度 [HA]", "buf_acid", self._inp("0.1"),
                          "弱酸或弱碱的浓度 mol/L")
        self._mode_widgets["缓冲溶液 pH"] = gb
        gb.setVisible(False)
        layout.addWidget(gb)

    def _create_dilute_panel(self, layout):
        gb, g = self._group("稀释参数")
        r = 0
        r = self._add_row(g, r, "初始 pH", "dil_pH1", self._inp("3.0"),
                          "稀释前的 pH 值")
        r = self._add_row(g, r, "溶液类型", "dil_type", self._combo(),
                          "强酸/强碱直接算; 弱电解需 pKa")
        cb = self._all_inputs["dil_type"]
        cb.addItems(["强酸", "强碱", "弱酸（需 pKa）", "弱碱（需 pKb）"])
        cb.currentTextChanged.connect(self._on_dil_type)
        r = self._add_row(g, r, "pKa / pKb", "dil_pk", self._inp("4.76"),
                          "弱酸/弱碱解离常数, 强电解无需")
        r = self._add_row(g, r, "初始体积", "dil_V1", self._inp("1.0"),
                          "L")
        r = self._add_row(g, r, "稀释后体积", "dil_V2", self._inp("10.0"),
                          "L（必须 > 初始体积）")
        self._mode_widgets["稀释后 pH"] = gb
        gb.setVisible(False)
        layout.addWidget(gb)

    def _create_adjust_panel(self, layout):
        gb, g = self._group("pH 调节参数")
        r = 0
        r = self._add_row(g, r, "当前 pH", "adj_pH0", self._inp("7.0"),
                          "当前溶液的 pH")
        r = self._add_row(g, r, "目标 pH", "adj_pH1", self._inp("5.0"),
                          "希望调到多少")
        r = self._add_row(g, r, "溶液体积", "adj_V", self._inp("2500"),
                          "L（或 m³ 换算为 1000L=1m³ 后输入）")

        # ── 缓冲体系开关（放在 column 1 与其他输入框对齐） ──
        self._adj_buf_cb = QCheckBox("含缓冲体系（发酵液 / 有机酸溶液）")
        self._adj_buf_cb.setToolTip("勾选后按总可滴定酸浓度计算，适用于含弱酸的体系")
        self._adj_buf_cb.toggled.connect(self._on_buf_toggle)
        g.addWidget(self._adj_buf_cb, r, 1)
        # 右侧留空，用空 widget 撑住 4:8:5 列宽比例
        spacer = QLabel("")
        spacer.setObjectName("spacer_buf")
        g.addWidget(spacer, r, 2)
        r += 1
        r += 1

        self._adj_total_acid_edit = self._inp("0.063")
        self._adj_total_acid_label = self._lbl("总可滴定酸浓度")
        self._adj_total_acid_unit = QLabel("mol/L（发酵液实测值）")
        self._adj_total_acid_unit.setStyleSheet("font-style: italic; color: #666;")
        g.addWidget(self._adj_total_acid_label, r, 0)
        g.addWidget(self._adj_total_acid_edit, r, 1)
        g.addWidget(self._adj_total_acid_unit, r, 2)
        self._all_inputs["adj_total_acid"] = self._adj_total_acid_edit
        r += 1

        self._on_buf_toggle(False)

        # ── 调节剂 ──
        r = self._add_row(g, r, "调节剂", "adj_reagent", self._combo(),
                          "选择常用酸碱（自动填参数）")
        cb = self._all_inputs["adj_reagent"]
        cb.addItems(list(ADJUST_REAGENTS.keys()))
        cb.setCurrentText("液碱 NaOH 30%")
        cb.currentTextChanged.connect(self._on_adjust_reagent)

        # ── 液体模式: 重量%（mol/L 提示合并到 hint 里） ──
        r = self._add_row(g, r, "重量浓度",
                          "adj_wt", self._inp("30"), "%")
        # 不再单独创建 mol_hint 标签，让 _on_adjust_reagent 直接改 hint 文案

        # ── 固体模式 ──
        r = self._add_row(g, r, "分子量 M",
                          "adj_mw", self._inp("40.0"), "g/mol")
        r = self._add_row(g, r, "有效含量",
                          "adj_purity", self._inp("99"), "%")

        # n 值
        r = self._add_row(g, r, "H⁺ / OH⁻ 当量数",
                          "adj_n", self._inp("1", 0),
                          "每分子释放 H⁺ 或 OH⁻ 个数")

        self._adj_liquid_fields = ["adj_wt"]
        self._adj_solid_fields = ["adj_mw", "adj_purity"]
        self._mode_widgets["pH 调节"] = gb
        gb.setVisible(False)
        layout.addWidget(gb)
        self._on_adjust_reagent("液碱 NaOH 30%")   # 初始状态

    # ═════════════════════════════════════════
    #  事件
    # ═════════════════════════════════════════

    def _on_mode(self, btn):
        for name, w in self._mode_widgets.items():
            w.setVisible(name == btn.text())
        # 稀释模式切类型时更新 pK 行可见性
        if btn.text() == "稀释后 pH":
            self._on_dil_type(self._all_inputs.get("dil_type", None))

    def _on_buffer_system(self, name):
        if name == "手动输入 pKa":
            return
        info = PK_TABLE.get(name)
        if info:
            _, pk, _ = info
            self._all_inputs["buf_pk"].setText(str(pk))

    def _on_dil_type(self, arg=None):
        if isinstance(arg, str):
            t = arg
        elif hasattr(arg, 'currentText'):
            t = arg.currentText()
        else:
            t = self._all_inputs.get("dil_type", None)
        if t is None:
            t = "强酸"
        elif hasattr(t, 'currentText'):
            t = t.currentText()
        weak = "弱" in t
        for suf in ("dil_pk",):
            w = self._all_inputs.get(suf)
            if w:
                w.setVisible(weak)
                # 找 label 也同步
                lbl = self.findChild(QLabel, f"lbl_{suf}")
                if lbl:
                    lbl.setVisible(weak)

    def _on_adjust_reagent(self, name):
        """试剂预设切换 → 自动填充参数 + 显隐液体/固体字段"""
        info = ADJUST_REAGENTS.get(name)
        if not info:
            return
        _, form, val1, val2, mw, n_val = info
        if form == "液体":
            self._all_inputs["adj_wt"].setText(str(val2))
            mol_l = val2 / 100 * val1 * 1000 / mw
            # 把 mol/L 派生值合并到 hint 文字里："%（≈ X.X mol/L）"
            hint = self._row_widgets.get("adj_wt", {}).get("hint")
            if hint is not None:
                hint.setText(f"% (≈ {mol_l:.1f} mol/L)")
        else:
            self._all_inputs["adj_mw"].setText(str(val1))
            self._all_inputs["adj_purity"].setText(str(val2))
        self._all_inputs["adj_n"].setText(str(n_val))
        self._toggle_adjust_fields(form)
        self._adjust_form = form

    def _toggle_adjust_fields(self, form):
        """显示/隐藏液体专属字段 vs 固体专属字段（同时控制 label / hint / 输入框）"""
        is_liquid = (form == "液体")
        rows = getattr(self, "_row_widgets", {})
        for fld in self._adj_liquid_fields:
            visible = is_liquid
            for w in rows.get(fld, {}).values():
                if w is not None:
                    w.setVisible(visible)
        for fld in self._adj_solid_fields:
            visible = not is_liquid
            for w in rows.get(fld, {}).values():
                if w is not None:
                    w.setVisible(visible)

    def _on_buf_toggle(self, checked):
        """勾选/取消缓冲体系 → 显隐总可滴定酸输入行"""
        self._adj_total_acid_label.setVisible(checked)
        self._adj_total_acid_edit.setVisible(checked)
        self._adj_total_acid_unit.setVisible(checked)

    # ═════════════════════════════════════════
    #  读取
    # ═════════════════════════════════════════

    def _get(self, key: str, default=0.0) -> float:
        w = self._all_inputs.get(key)
        if w is None:
            return default
        if isinstance(w, QComboBox):
            return 0.0
        try:
            return float(w.text() or default)
        except ValueError:
            return default

    def _combo_text(self, key: str) -> str:
        w = self._all_inputs.get(key)
        if w is None:
            return ""
        return w.currentText() if isinstance(w, QComboBox) else ""

    # ═════════════════════════════════════════
    #  计算入口
    # ═════════════════════════════════════════

    def calculate(self):
        btn = self.mode_btn_group.checkedButton()
        mode = btn.text() if btn else "酸碱中和"
        try:
            if mode == "酸碱中和":
                r = self._calc_neutralize()
            elif mode == "缓冲溶液 pH":
                r = self._calc_buffer()
            elif mode == "稀释后 pH":
                r = self._calc_dilute()
            else:
                r = self._calc_adjust()
            self._last_results = r
            self._display(mode, r)
        except Exception as e:
            self.result_text.setPlainText(f"⚠ 计算错误: {e}")

    # ═════════════════════════════════════════
    #  模式 1：酸碱中和
    # ═════════════════════════════════════════

    def _calc_neutralize(self) -> dict:
        C1  = self._get("n_C")
        V1  = self._get("n_V")
        n1  = self._get("n_val")
        C2  = self._get("n_other_C")
        n2  = self._get("n_other_val")
        # 摩尔守恒: C1 × V1 × n1 = C2 × V2 × n2
        if C2 <= 0 or n2 <= 0:
            raise ValueError("待求液浓度和 H⁺/OH⁻ 个数必须 > 0")
        V2 = C1 * V1 * n1 / (C2 * n2)
        return {
            "C1": C1, "V1": V1, "n1": n1,
            "C2": C2, "n2": n2,
            "V2": V2,
        }

    # ═════════════════════════════════════════
    #  模式 2：缓冲溶液
    # ═════════════════════════════════════════

    def _calc_buffer(self) -> dict:
        pk = self._get("buf_pk")
        buf_type = self._combo_text("buf_type")
        salt = self._get("buf_salt")
        acid = self._get("buf_acid")
        if acid <= 0:
            raise ValueError("弱酸/弱碱浓度必须 > 0")
        ratio = salt / acid
        if buf_type.startswith("酸型"):
            pH = pk + math.log10(ratio) if ratio > 0 else pk
            pOH = 14 - pH
        else:
            pOH = pk + math.log10(ratio) if ratio > 0 else pk
            pH = 14 - pOH
        return {"pk": pk, "ratio": ratio, "pH": pH, "pOH": pOH, "type": buf_type}

    # ═════════════════════════════════════════
    #  模式 3：稀释
    # ═════════════════════════════════════════

    def _calc_dilute(self) -> dict:
        pH1 = self._get("dil_pH1")
        stype = self._combo_text("dil_type")
        V1 = self._get("dil_V1")
        V2 = self._get("dil_V2")
        pk = self._get("dil_pk")

        if V1 <= 0 or V2 <= 0:
            raise ValueError("体积必须 > 0")
        if V2 <= V1:
            raise ValueError("稀释后体积必须 > 初始体积")
        factor = V2 / V1

        if "强" in stype:
            if "酸" in stype:
                pH2 = pH1 + math.log10(factor)
            else:
                pH2 = 14 - ((14 - pH1) + math.log10(factor))
        else:
            # 弱电解：简化公式 [H⁺]2 = Ka × (C1 × V1 / V2)
            # 近似: pH2 ≈ 0.5×(pKa + pCa2) 其中 Ca2 = C1/factor
            if pk <= 0:
                raise ValueError("弱电解需要 pKa/pKb, 请填入")
            if "酸" in stype:
                C1 = 10 ** (-pH1)
                Ca = C1 / factor
                tmp = (-pk + math.sqrt(pk**2 + 4 * pk * Ca)) / 2
                pH2 = -math.log10(max(tmp, 1e-14)) if tmp > 0 else pH1 + math.log10(factor)
            else:
                pOH1 = 14 - pH1
                Cb = 10 ** (-pOH1) / factor
                tmp = (-pk + math.sqrt(pk**2 + 4 * pk * Cb)) / 2
                pH2 = 14 + math.log10(max(tmp, 1e-14)) if tmp > 0 else pH1 - math.log10(factor)

        return {"pH1": pH1, "pH2": pH2, "V1": V1, "V2": V2, "factor": factor, "type": stype}

    # ═════════════════════════════════════════
    #  模式 4：pH 调节
    # ═════════════════════════════════════════

    def _calc_adjust(self) -> dict:
        pH0 = self._get("adj_pH0")
        pH1 = self._get("adj_pH1")
        V = self._get("adj_V")
        n_val = self._get("adj_n")

        if V <= 0:
            raise ValueError("溶液体积必须 > 0")
        if n_val <= 0:
            raise ValueError("H⁺/OH⁻ 当量数必须 > 0")

        form = getattr(self, "_adjust_form", "液体")
        reagent = self._combo_text("adj_reagent")

        # ── 决定用哪种酸浓度 ──
        buf_enabled = self._adj_buf_cb.isChecked()
        if buf_enabled:
            total_acid = self._get("adj_total_acid")
            if total_acid <= 0:
                raise ValueError("总可滴定酸浓度必须 > 0")
            delta_H_mol = total_acid * V   # 按总酸浓度算
        else:
            h0 = 10 ** (-pH0)
            h1 = 10 ** (-pH1)
            delta_H_mol = abs(h1 - h0) * V  # 按游离 H⁺ 算

        if form == "液体":
            wt = self._get("adj_wt")                  # 重量%
            reagent = self._combo_text("adj_reagent")
            info = ADJUST_REAGENTS.get(reagent, ("", "液体", 1.0, 10, 1.0, 1))
            rho, mw = info[2], info[4]                 # 密度 g/mL, 分子量
            C = wt / 100 * rho * 1000 / mw             # → mol/L
            if C <= 0 or n_val <= 0:
                raise ValueError("浓度和 n 值必须 > 0")
            mol_effective = C * n_val
            delta_L = delta_H_mol / mol_effective
            result = {
                "pH0": pH0, "pH1": pH1, "V": V,
                "form": "液体", "reagent": reagent,
                "conc_molL": C, "wt_pct": wt, "n_val": n_val,
                "delta_H_mol": delta_H_mol,
                "amount": delta_L * 1000,  # mL
                "unit": "mL",
            }
        else:
            MW = self._get("adj_mw")
            purity = self._get("adj_purity", 100) / 100
            if MW <= 0:
                raise ValueError("分子量必须 > 0")
            mol_effective = purity * n_val / MW     # 有效 mol/g（每克固体折合多少 OH⁻/H⁺）
            delta_g = delta_H_mol / mol_effective
            result = {
                "pH0": pH0, "pH1": pH1, "V": V,
                "form": "固体", "reagent": reagent,
                "MW": MW, "purity": purity * 100, "n_val": n_val,
                "delta_H_mol": delta_H_mol,
                "amount": delta_g,  # g
                "unit": "g",
            }

        result["direction"] = "加入酸（降低 pH）" if pH1 < pH0 else "加入碱（提高 pH）"
        result["buffered"] = buf_enabled
        return result

    # ═════════════════════════════════════════
    #  显示
    # ═════════════════════════════════════════

    def _display(self, mode, data):
        lines = []
        if mode == "酸碱中和":
            lines.append("═" * 40)
            lines.append("  酸碱中和计算结果")
            lines.append("═" * 40)
            lines.append(f"  已知侧: C={data['C1']:.3f} mol/L, V={data['V1']:.3f} L, n={data['n1']:.0f}")
            lines.append(f"  待求侧: C={data['C2']:.3f} mol/L, n={data['n2']:.0f}")
            lines.append(f"  → 需要体积 = {data['V2']:.3f} L = {data['V2']*1000:.1f} mL")

        elif mode == "缓冲溶液 pH":
            lines.append("═" * 40)
            lines.append("  缓冲溶液 pH")
            lines.append("═" * 40)
            lines.append(f"  体系: {data['type']}")
            lines.append(f"  pK   = {data['pk']:.2f}")
            lines.append(f"  [A⁻]/[HA] = {data['ratio']:.3f}")
            lines.append(f"  log([A⁻]/[HA]) = {math.log10(max(data['ratio'],1e-14)):.3f}")
            lines.append(f"  → pH = {data['pH']:.2f}     pOH = {data['pOH']:.2f}")

        elif mode == "稀释后 pH":
            lines.append("═" * 40)
            lines.append("  稀释后 pH")
            lines.append("═" * 40)
            lines.append(f"  类型: {data['type']}")
            lines.append(f"  初始 pH = {data['pH1']:.2f}")
            lines.append(f"  稀释倍数 = {data['factor']:.1f}×")
            lines.append(f"  → 稀释后 pH = {data['pH2']:.2f}")

        else:  # pH 调节
            lines.append("═" * 50)
            lines.append("  pH 调节计算结果")
            lines.append("═" * 50)
            lines.append(f"  {data['direction']}")
            lines.append(f"  调节剂: {data['reagent']}（{data['form']}）")
            if data.get("buffered"):
                lines.append("  模型: 含缓冲体系（按总可滴定酸计算）")
            else:
                lines.append("  模型: 纯水 / 无缓冲（按游离 H⁺ 计算）")
            lines.append(f"  当前 pH = {data['pH0']:.2f} → 目标 pH = {data['pH1']:.2f}")
            lines.append(f"  需要改变的 H⁺ 当量 = {data['delta_H_mol']:.4f} mol")
            if data["form"] == "液体":
                lines.append(f"  试剂浓度: {data.get('wt_pct', '?')}%  ≈ {data['conc_molL']:.2f} mol/L,  n = {data['n_val']:.0f}")
            else:
                lines.append(f"  分子量 = {data['MW']:.1f},  含量 = {data['purity']:.0f}%,  n = {data['n_val']:.0f}")
            lines.append(f"  → 需要 {data['amount']:.2f} {data['unit']}")

        self.result_text.setPlainText("\n".join(lines))

    # ═════════════════════════════════════════
    #  清空 & 历史
    # ═════════════════════════════════════════

    def clear(self):
        for _, w in self._all_inputs.items():
            if isinstance(w, QLineEdit):
                w.clear()
        self.result_text.clear()
        self._last_results = {}

    def _get_history_data(self) -> dict:
        r = self._last_results
        if not r:
            return {}
        btn = self.mode_btn_group.checkedButton()
        mode = btn.text() if btn else ""
        return {
            "inputs": {"模式": mode, **{k: str(v) for k, v in r.items()}},
            "outputs": r,
            "notes": "",
        }

    # ═════════════════════════════════════════
    #  报告
    # ═════════════════════════════════════════

    def get_project_info(self):
        return {
            "project_name": "pH 计算",
            "calculator_name": "pH 计算器",
            "version": "1.0",
            "description": "酸碱中和/缓冲溶液(Henderson-Hasselbalch)/稀释/pH调节"
        }

    def generate_report(self):
        content = self.result_text.toPlainText().strip()
        if not content:
            return "尚未进行计算。"
        btn = self.mode_btn_group.checkedButton()
        mode = btn.text() if btn else ""
        lines = [f"pH 计算报告（{mode}）", "=" * 50, "", content]
        return "\n".join(lines)

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "PHCalculator")

    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "PHCalculator")
