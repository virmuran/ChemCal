"""
发酵废水 COD 估算器
省略文档内容...
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QScrollArea,
    QButtonGroup, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
import datetime

from calculator_base import CalculatorBase
from app_styles import (SCROLL_AREA_STYLE,
                        INPUT_LABEL_STYLE, CLEAR_BTN_STYLE,
                        DOCX_BTN_STYLE, PDF_BTN_STYLE)


def thod_from_formula(n_c, n_h, n_n=0, n_o=0, n_s=0, mw=None):
    """理论需氧量 ThOD，g O₂/g 物质。

    氧化终态约定（与重铬酸钾法 COD 的口径一致，不计硝化）：
        C → CO₂,  H → H₂O,  N → NH₃（不继续氧化为硝酸盐）,  S → SO₄²⁻

    电子守恒推导（O₂ 每 mol 接受 4 个电子）：
        n(O₂) = (4·C + H + 6·S − 3·N − 2·O) / 4
        ThOD  = n(O₂) · 32 / M

    说明：N 按 NH₃ 计（−3 价）会扣除 3 个电子/mol；若按硝化计至硝酸盐，
    需再加 2 mol O₂/mol N，数值会明显偏大。本模块统一采用「不计硝化」。
    """
    n_o2 = (4 * n_c + n_h + 6 * n_s - 3 * n_n - 2 * n_o) / 4.0
    if mw is None:
        raise ValueError("需提供分子量 mw")
    return n_o2 * 32.0 / mw


# ── COD 当量数据库 ──
# 标「理论值」者由 thod_from_formula 按上述约定算出，可用 tests 直接复核；
# 标「经验值」者为工业发酵统计值，无唯一理论解，仅供估算。
#
# ⚠ 数据勘误（2026-09-14）：原 "L-蛋氨酸" 填 1.073，与 L-苏氨酸(1.075) 几乎相同，
#   系误抄；含硫氨基酸的 S 须氧化到 SO₄²⁻，理论值应为 1.609（偏小 33%）。
COD_DB = {
    # 碳源
    "葡萄糖": (1.066, "碳源"),        # 理论值 C6H12O6
    "蔗糖": (1.122, "碳源"),          # 理论值 C12H22O11
    "淀粉(可溶)": (1.184, "碳源"),    # 理论值，按 (C6H10O5)n 单体
    "甘油": (1.216, "碳源"),          # 理论值 C3H8O3
    "糖蜜": (0.90, "碳源"),           # 经验值（甘蔗/甜菜糖蜜实测统计）
    # 有机氮源
    "玉米浆": (0.85, "氮源"),         # 经验值
    "酵母浸粉": (0.95, "氮源"),       # 经验值
    "豆粕水解液": (0.80, "氮源"),     # 经验值
    "蛋白胨": (0.90, "氮源"),         # 经验值
    "(NH₄)₂SO₄": (0.00, "无机氮"),    # 无机，不计硝化时无 COD
    "尿素": (0.00, "无机氮"),         # 无机；重铬酸钾法不氧化尿素，实测 COD 近 0
    # 有机酸/中间代谢物
    "乙酸": (1.066, "有机酸"),        # 理论值 C2H4O2
    "乳酸": (1.066, "有机酸"),        # 理论值 C3H6O3
    "柠檬酸": (0.750, "有机酸"),      # 理论值，按无水柠檬酸 C6H8O7
    "琥珀酸": (0.948, "有机酸"),      # 理论值 C4H6O4
    "乙醇": (2.084, "醇类"),          # 理论值 C2H6O
    # 氨基酸产品
    "L-缬氨酸": (1.639, "产品"),      # 理论值 C5H11NO2
    "L-赖氨酸": (1.532, "产品"),      # 理论值 C6H14N2O2
    "L-苏氨酸": (1.075, "产品"),      # 理论值 C4H9NO3
    "L-谷氨酸": (0.979, "产品"),      # 理论值 C5H9NO4
    "L-亮氨酸": (1.830, "产品"),      # 理论值 C6H13NO2
    "L-异亮氨酸": (1.830, "产品"),    # 理论值 C6H13NO2（与亮氨酸同分异构）
    "L-蛋氨酸": (1.609, "产品"),      # 理论值 C5H11NO2S（S→SO₄²⁻；原误填 1.073）
    # 菌体
    "菌体干重(DCW)": (1.42, "菌体"),  # 经验值，近似按 C5H7O2N 计（理论 1.415）
    "菌体(湿重×20%)": (0.284, "菌体"),  # = 1.42 × 20% 干重比
}


# ── 产品类型预设 ──
# (产品名, 默认COD当量, 典型副产物说明)
PRODUCT_PRESETS = {
    "L-缬氨酸": "L-缬氨酸",
    "L-赖氨酸盐酸盐": "L-赖氨酸",
    "L-苏氨酸": "L-苏氨酸",
    "L-谷氨酸钠(MSG)": "L-谷氨酸",
    "自定义": None,
}

# ── 废水来源 → (产品是否仍留在废水中, 菌体在废水中的残留比例) ──
WASTE_SOURCE_RETENTION = {
    "发酵废液（离心后上清液）": (True, 0.15),   # 菌体已离心分离，产品尚未提取
    "全发酵液（含菌体）": (True, 1.0),          # 整罐排放，产品与菌体全在
    "提取废液（离子交换/膜分离）": (False, 0.15),  # 产品已被回收，不计入废水 COD
    "综合废水（工艺+清洗）": (True, 1.0),
}

# ── 物料衡算法原料清单（静态网格行，与其他计算器风格一致）──
# (名称, 默认值)；默认值对应典型氨基酸发酵配方
MAT_LIST = [
    ("葡萄糖", "100"), ("蔗糖", ""), ("淀粉(可溶)", ""), ("甘油", ""), ("糖蜜", ""),
    ("玉米浆", "15"), ("酵母浸粉", "5"), ("豆粕水解液", ""), ("蛋白胨", ""),
    ("乙酸", ""), ("乳酸", ""), ("柠檬酸", ""), ("琥珀酸", ""), ("乙醇", ""),
]


class CODEstimator(CalculatorBase):
    """发酵废水 COD 估算器"""

    calculation_type = "废水COD估算"

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent, data_manager)
        self.input_widgets = {}
        self._last_results = {}

        self.setup_ui()
        self.setup_calculation_mode(0)
        self.setup_wheel_blocker()

    # ═══════════════════════════════════════
    # UI 构建
    # ═══════════════════════════════════════

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ── 左 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_AREA_STYLE)
        left = QWidget()
        left.setStyleSheet("")
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(15)

        desc = QLabel(
            "COD估算器 — 基于物料衡算或已知项目类比，估算发酵废水 COD 浓度。\n"
            "物料衡算模式下输入各原料投加量和发酵参数，系统按 COD 当量逐项求和。\n"
            "类比缩放模式以已知项目为基准按比例缩放。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc)

        # 模式选择
        mode_group = QGroupBox("计算模式")
        mode_layout = QHBoxLayout(mode_group)
        self.mode_btn_group = QButtonGroup(self)
        self.mode_btns = {}
        modes = [("物料衡算法", "按各物料投加量逐项计算COD"),
                 ("类比缩放法", "以参考项目实测COD为基准按比例缩放")]
        for i, (name, tip) in enumerate(modes):
            btn = CalculatorBase.make_mode_button(name, tip)
            self.mode_btn_group.addButton(btn, i)
            mode_layout.addWidget(btn)
            self.mode_btns[name] = btn
        self.mode_btns["物料衡算法"].setChecked(True)
        left_layout.addWidget(mode_group)

        self.mode_btn_group.buttonClicked.connect(self._on_mode_clicked)

        # 输入参数容器
        self.input_group = QGroupBox("输入参数")
        self.input_layout = QGridLayout(self.input_group)
        self.input_layout.setSpacing(12)
        self.input_layout.setContentsMargins(10, 15, 10, 15)
        self.input_layout.setColumnStretch(0, 4)
        self.input_layout.setColumnStretch(1, 8)
        self.input_layout.setColumnStretch(2, 5)
        left_layout.addWidget(self.input_group)

        # 收尾弹性空间：组框保持自然高度，多余空间留在底部（否则组框被撑开、内容下沉）
        left_layout.addStretch()

        scroll.setWidget(left)

        # ── 右 ──
        right = QWidget()
        right.setMinimumWidth(300)
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(15)

        result_group = CalculatorBase.make_group_box("计算结果")
        result_inner = QVBoxLayout(result_group)
        # 结果框统一标准：边框/背景/文字色交给主题系统，仅指定等宽字体
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: 13px;
            } """)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        result_inner.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        btn_layout = QHBoxLayout()
        for name, style, callback in [("清空", CLEAR_BTN_STYLE, self.clear_all),
                                       ("下载 DOCX", DOCX_BTN_STYLE, lambda: self.download_docx_report("废水COD估算")),
                                       ("下载 PDF", PDF_BTN_STYLE, lambda: self.download_pdf_report("废水COD估算"))]:
            b = QPushButton(name)
            b.setStyleSheet(style)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.clicked.connect(callback)
            btn_layout.addWidget(b)
        right_layout.addLayout(btn_layout)

        # 计算按钮（绿色，置底）
        calc_btn = CalculatorBase.make_calc_button()
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)

        main_layout.addWidget(scroll, 2)
        main_layout.addWidget(right, 1)

    # ═══════════════════════════════════════
    # 模式切换
    # ═══════════════════════════════════════

    def _on_mode_clicked(self, button):
        idx = self.mode_btn_group.id(button)
        self.setup_calculation_mode(idx)

    def _get_mode(self):
        checked = self.mode_btn_group.checkedButton()
        return checked.text() if checked else "物料衡算法"

    def setup_calculation_mode(self, mode_index):
        for w in self.input_widgets.values():
            w.setParent(None)
        self.input_widgets.clear()
        self._last_results = {}
        self.result_text.clear()

        # 清除标题容器
        while self.input_layout.count():
            item = self.input_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if mode_index == 0:
            self._setup_mass_balance()
        else:
            self._setup_analogy()

    # ═══════════════════════════════════════
    # 模式1: 物料衡算法
    # ═══════════════════════════════════════

    def _setup_mass_balance(self):
        ls = INPUT_LABEL_STYLE
        row = 0

        # ── 基础参数 ──
        basics = [
            ("发酵体积 (m³):", "batch_vol", "例如：50", "50"),
            ("产品类型:", "product_type", None, None),
            ("产品产量 (g/L):", "product_yield", "例如：60", "60"),
            ("残糖 (g/L):", "residual_sugar", "例如：5", "5"),
            ("菌体浓度 (g DCW/L):", "biomass", "例如：8", "8"),
        ]
        for label, key, placeholder, default in basics:
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet(ls)
            self.input_layout.addWidget(lbl, row, 0)

            if key == "product_type":
                combo = CalculatorBase.make_combo_box()
                for p in PRODUCT_PRESETS:
                    combo.addItem(p)
                self.input_layout.addWidget(combo, row, 1)
                self.input_widgets[key] = combo
                # 说明
                hint = QLabel("COD当量由产品决定")
                hint.setStyleSheet("font-style: italic;")
                self.input_layout.addWidget(hint, row, 2)
            else:
                le = QLineEdit()
                if placeholder:
                    le.setPlaceholderText(placeholder)
                if default:
                    le.setText(default)
                le.setValidator(QDoubleValidator(0, 100000, 2))
                self.input_layout.addWidget(le, row, 1)
                self.input_widgets[key] = le
            row += 1

        # ── 原料投加量（静态网格，留空或0表示未添加）──
        mat_label = QLabel("▼ 原料投加量 (g/L)，留空或 0 表示未添加")
        mat_label.setStyleSheet("font-weight: bold; padding-top: 10px;")
        self.input_layout.addWidget(mat_label, row, 0, 1, 3)
        row += 1

        for name, default in MAT_LIST:
            lbl = QLabel(f"{name}:")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet(ls)
            self.input_layout.addWidget(lbl, row, 0)

            le = QLineEdit()
            if default:
                le.setText(default)
            else:
                le.setPlaceholderText("0")
                le.setText("0")  # 0 = 未添加
            le.setValidator(QDoubleValidator(0, 100000, 2))
            self.input_layout.addWidget(le, row, 1)
            self.input_widgets["mat_" + name] = le

            eq, cat = COD_DB[name]
            hint = QLabel(f"COD当量 {eq}（{cat}）")
            hint.setStyleSheet("font-style: italic;")
            self.input_layout.addWidget(hint, row, 2)
            row += 1

        # ── 废水参数 ──
        lbl = QLabel("废水参数")
        lbl.setStyleSheet("font-weight: bold; padding-top: 10px;")
        self.input_layout.addWidget(lbl, row, 0, 1, 3)
        row += 1

        waste_params = [
            ("废水来源:", "waste_source", None),
            ("废水产生量 (m³/批):", "waste_volume", "如不填，按装液量的80%估算"),
            ("稀释/洗涤水 (m³/批):", "wash_water", "可选，如清洗水排入污水处理系统"),
        ]
        for label, key, placeholder in waste_params:
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet(ls)
            self.input_layout.addWidget(lbl, row, 0)

            if key == "waste_source":
                combo = CalculatorBase.make_combo_box()
                combo.addItems(["发酵废液（离心后上清液）",
                                "全发酵液（含菌体）",
                                "提取废液（离子交换/膜分离）",
                                "综合废水（工艺+清洗）"])
                self.input_layout.addWidget(combo, row, 1)
                self.input_widgets[key] = combo
                hint = QLabel("不同来源COD差异大")
                hint.setStyleSheet("font-style: italic;")
                self.input_layout.addWidget(hint, row, 2)
            else:
                le = QLineEdit()
                if placeholder:
                    le.setPlaceholderText(placeholder)
                self.input_layout.addWidget(le, row, 1)
                self.input_widgets[key] = le
            row += 1

    def _read_materials(self):
        """读取原料投加量（input_widgets 中 mat_* 键），返回 [(name, conc_g_L), ...]"""
        rows = []
        for name, _ in MAT_LIST:
            key = "mat_" + name
            if key not in self.input_widgets:
                continue
            val = self._get(key, 0)
            if val > 0:
                rows.append((name, val))
        return rows

    # ═══════════════════════════════════════
    # 模式2: 类比缩放法
    # ═══════════════════════════════════════

    def _setup_analogy(self):
        ls = INPUT_LABEL_STYLE
        row = 0
        pairs = [
            # (label, key, placeholder, default)
            ("─ 参考项目（已知数据）─", None, None, None),
            ("参考项目 COD (mg/L):", "ref_cod", "例如：1800", "1800"),
            ("参考项目 投糖量 (g/L):", "ref_sugar", "例如：120", "120"),
            ("参考项目 产品产量 (g/L):", "ref_yield", "例如：60", "60"),
            ("参考项目 残糖 (g/L):", "ref_residual", "例如：5", "5"),
            ("", None, None, None),
            ("─ 新项目（待估算）─", None, None, None),
            ("新项目 投糖量 (g/L):", "new_sugar", "例如：130", "130"),
            ("新项目 产品产量 (g/L):", "new_yield", "例如：65", "65"),
            ("新项目 残糖 (g/L):", "new_residual", "例如：4", "4"),
        ]
        for label, key, placeholder, default in pairs:
            if not key:
                lbl = QLabel(label)
                lbl.setStyleSheet("font-weight: bold; padding: 5px 0;")
                self.input_layout.addWidget(lbl, row, 0, 1, 3)
                row += 1
                continue
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet(ls)
            self.input_layout.addWidget(lbl, row, 0)

            le = QLineEdit()
            if placeholder:
                le.setPlaceholderText(placeholder)
            if default:
                le.setText(default)
            le.setValidator(QDoubleValidator(0, 100000, 1))
            self.input_layout.addWidget(le, row, 1)
            self.input_widgets[key] = le
            row += 1

    # ═══════════════════════════════════════
    # 输入读取
    # ═══════════════════════════════════════

    def _get(self, key, default=0.0):
        if key not in self.input_widgets:
            return default
        w = self.input_widgets[key]
        if isinstance(w, QLineEdit):
            t = w.text().strip()
            return float(t) if t else default
        elif isinstance(w, QComboBox):
            return w.currentText()
        return default

    # ═══════════════════════════════════════
    # 计算
    # ═══════════════════════════════════════

    def calculate(self):
        mode = self._get_mode()
        try:
            if "物料" in mode:
                self._calc_mass_balance()
            else:
                self._calc_analogy()
        except ValueError as e:
            QMessageBox.warning(self, "输入错误", str(e))
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"发生意外错误:\n{str(e)}")

    def _calc_mass_balance(self):
        vol = self._get("batch_vol", 50)
        if vol <= 0:
            raise ValueError("请输入有效的发酵体积")

        product_type = self._get("product_type", "L-缬氨酸")
        product_yield = self._get("product_yield", 60)
        residual_sugar = self._get("residual_sugar", 5)
        biomass = self._get("biomass", 8)
        waste_vol = self._get("waste_volume", 0)
        wash_water = self._get("wash_water", 0)

        # 查找产品COD当量
        prod_key = PRODUCT_PRESETS.get(product_type, None)
        if prod_key and prod_key in COD_DB:
            product_cod_eq = COD_DB[prod_key][0]
        else:
            product_cod_eq = 1.0  # 自定义默认值

        # 读取物料表
        mat_rows = self._read_materials()

        # ── COD 贡献 ──
        contrib_cod = {}
        input_cod_total = 0.0  # g O₂/L

        for name, conc in mat_rows:
            eq, cat = COD_DB.get(name, (0, "未知"))
            cod_val = conc * eq
            contrib_cod[name] = {"conc": conc, "eq": eq, "cod": cod_val, "cat": cat}
            input_cod_total += cod_val

        # ── 产品带走COD ──
        product_cod = product_yield * product_cod_eq

        # ── 残糖贡献COD ──
        residual_cod = residual_sugar * COD_DB["葡萄糖"][0]

        # ── 菌体贡献COD ──
        biomass_cod = biomass * COD_DB["菌体干重(DCW)"][0]

        # ── 废水中各来源的保留规则 ──
        # (产品是否仍在废水中, 菌体在废水中的残留比例)
        # 全发酵液/综合废水：产品未提取、菌体全在；上清液：产品在、菌体离心去除；
        # 提取废液：产品已由离交/膜分离回收，故其 COD 不算进废水。
        waste_source = self._get("waste_source", "发酵废液（离心后上清液）")
        product_in_waste, biomass_retention = WASTE_SOURCE_RETENTION.get(
            waste_source, (True, 1.0))

        # ── 废水（液相）COD ──
        # COD 守恒：投入COD = 产品COD + 菌体COD + 未消耗碳源COD + 呼吸氧化为CO₂的COD。
        # 因 CO₂ 的需氧量为 0，最后一项即"真正被氧化掉"的部分。故液相残存 COD 只能由
        # 仍留在液相的那几项构成 —— 这正是下面三行相加的含义。
        #
        # ⚠ 原实现写作「投入总COD − 产品 + 残糖 + 菌体」，而残糖与菌体的 COD 本来就
        #   包含在投入总COD里（菌体由消耗掉的糖转化而来，属再分配而非新增），
        #   属重复计入：默认参数下把结果高估了约 25%；
        #   且原实现对四种废水来源一律扣减产品COD，与"全发酵液"的语义矛盾。
        liquid_cod = (residual_cod
                      + biomass_cod * biomass_retention
                      + (product_cod if product_in_waste else 0.0))

        # 被呼吸氧化掉的 COD（用于校验物料口径是否自洽）
        mineralized_cod = input_cod_total - (product_cod + biomass_cod + residual_cod)

        # 限制最小值为0（不能为负）
        liquid_cod = max(liquid_cod, 0)

        # ── 废水体积 ──
        if waste_vol > 0:
            total_waste_vol = waste_vol
        else:
            # 默认按装液量80%估算（发酵液体积=罐容×80%装液量→废水≈发酵液）
            total_waste_vol = vol * 0.8

        total_waste_vol += wash_water  # 洗涤水排入

        # ── COD 浓度 ──
        # liquid_cod: g O₂/L；× vol(m³) → kg O₂/批（g/L × 1000 L/m³ = 1000 g/m³ = 1 kg/m³）
        cod_load = liquid_cod * vol                        # kg O₂/批
        # kg/批 ÷ m³/批 × 1000 → g/m³ = mg/L
        cod_conc = cod_load * 1000 / total_waste_vol if total_waste_vol > 0 else 0.0

        # ── 存储 ──
        self._last_results = {
            "mode": "物料衡算法",
            "vol": vol,
            "product_type": product_type,
            "product_yield": product_yield,
            "product_cod_eq": product_cod_eq,
            "product_cod": product_cod,
            "residual_sugar": residual_sugar,
            "residual_cod": residual_cod,
            "biomass": biomass,
            "biomass_cod": biomass_cod,
            "contrib_cod": contrib_cod,
            "input_cod_total": input_cod_total,
            "liquid_cod": liquid_cod,
            "mineralized_cod": mineralized_cod,
            "product_in_waste": product_in_waste,
            "biomass_retention": biomass_retention,
            "waste_source": waste_source,
            "waste_vol": total_waste_vol,
            "wash_water": wash_water,
            "cod_load": cod_load,
            "cod_conc": cod_conc,
            "mat_rows": mat_rows,
        }

        self._display_mass_balance()

    def _calc_analogy(self):
        ref_cod = self._get("ref_cod", 1800)
        ref_sugar = self._get("ref_sugar", 120)
        ref_yield = self._get("ref_yield", 60)
        ref_residual = self._get("ref_residual", 5)
        new_sugar = self._get("new_sugar", 130)
        new_yield = self._get("new_yield", 65)
        new_residual = self._get("new_residual", 4)

        if ref_cod <= 0 or ref_sugar <= 0:
            raise ValueError("请输入有效的参考项目数据")

        # 缩放因子：COD ∝ (投糖 − 0.18×产量 + 1.066×残糖)
        # 0.18 为产量对糖耗的近似折减系数（产品 COD 当量已单独赋值，此处只做糖基折算）；
        # 残糖按葡萄糖 COD 当量折算。
        sugar_eq = COD_DB["葡萄糖"][0]
        ref_base = ref_sugar - ref_yield * 0.18 + ref_residual * sugar_eq
        new_base = new_sugar - new_yield * 0.18 + new_residual * sugar_eq
        if ref_base <= 0:
            raise ValueError(
                "参考项目数据不自洽：投糖量 − 0.18×产品产量 + COD当量×残糖 ≤ 0，请检查输入")
        scale = new_base / ref_base
        if scale <= 0:
            raise ValueError("新项目数据不自洽：折算糖基 ≤ 0，请检查投糖量/产量/残糖")

        cod_est = ref_cod * scale

        self._last_results = {
            "mode": "类比缩放法",
            "ref_cod": ref_cod,
            "ref_sugar": ref_sugar,
            "ref_yield": ref_yield,
            "ref_residual": ref_residual,
            "new_sugar": new_sugar,
            "new_yield": new_yield,
            "new_residual": new_residual,
            "scale": scale,
            "cod_est": cod_est,
        }

        self._display_analogy()

    # ═══════════════════════════════════════
    # 结果显示
    # ═══════════════════════════════════════

    def _display_mass_balance(self):
        r = self._last_results
        lines = ["══════════════════════════════",
                 "   发酵废水 COD 估算（物料衡算法）",
                 "══════════════════════════════",
                 "",
                 "【发酵参数】",
                 f"  发酵体积: {r['vol']:.1f} m³",
                 f"  产品类型: {r['product_type']}",
                 f"  产品产量: {r['product_yield']:.1f} g/L",
                 f"  产品COD当量: {r['product_cod_eq']:.3f} g O₂/g",
                 f"  残糖: {r['residual_sugar']:.1f} g/L",
                 f"  菌体浓度: {r['biomass']:.1f} g DCW/L",
                 "",
                 "【各组分 COD 贡献】"]

        total_input = r["input_cod_total"]
        product_cod = r["product_cod"]
        residual_cod = r["residual_cod"]
        biomass_cod = r["biomass_cod"]

        sugar_eq = COD_DB["葡萄糖"][0]
        dcw_eq = COD_DB["菌体干重(DCW)"][0]
        lines.append(f"  {'物料名称':<16} {'投加量':>8} {'COD当量':>8} {'贡献COD':>8} {'类别':<8}")
        lines.append(f"  {'─'*54}")
        for name, c in r["contrib_cod"].items():
            lines.append(f"  {name:<16} {c['conc']:>8.1f} {c['eq']:>8.3f} {c['cod']:>8.1f} {c['cat']:<8}")
        if r["residual_sugar"] > 0:
            lines.append(f"  {'残糖(葡萄糖)':<16} {r['residual_sugar']:>8.1f} {sugar_eq:>8.3f} {residual_cod:>8.1f} {'残糖':<8}")
        if r["biomass"] > 0:
            lines.append(f"  {'菌体':<16} {r['biomass']:>8.1f} {dcw_eq:>8.3f} {biomass_cod:>8.1f} {'菌体':<8}")

        # ── COD 平衡（投入口径 → 液相残留口径）──
        in_waste = "是" if r["product_in_waste"] else "否（已提取回收）"
        ret_pct = r["biomass_retention"] * 100
        lines.append("")
        lines.append("【COD 平衡】")
        lines.append(f"  投入总COD:      {total_input:>8.1f} g O₂/L  （各原料之和）")
        lines.append(f"   ├ 产品COD:     {product_cod:>8.1f} g O₂/L  （{r['product_yield']:.1f} × {r['product_cod_eq']:.3f}）")
        lines.append(f"   ├ 菌体COD:     {biomass_cod:>8.1f} g O₂/L  （{r['biomass']:.1f} × {dcw_eq:.3f}）")
        lines.append(f"   └ 残糖COD:     {residual_cod:>8.1f} g O₂/L  （{r['residual_sugar']:.1f} × {sugar_eq:.3f}）")
        lines.append(f"  ─────────────────────────")
        lines.append(f"  呼吸氧化为CO₂:  {max(r['mineralized_cod'], 0.0):>8.1f} g O₂/L  （投入 − 上述三项）")
        lines.append(f"  废水（液相）COD:{r['liquid_cod']:>8.1f} g O₂/L")
        lines.append(f"  废水来源: {r['waste_source']}")
        lines.append(f"  产品是否留在废水中: {in_waste}；菌体残留率: {ret_pct:.0f}%")
        if r["mineralized_cod"] < 0:
            lines.append("")
            lines.append("  ⚠ 物料口径不自洽：产品+菌体+残糖的 COD 已超过投入总 COD，")
            lines.append("     说明产品产量/残糖/当量与投料量组合在 COD 守恒上不可行。")
            lines.append("     请核对投糖量与产品产量（产率不可能超过 COD 收率 100%）。")
        if r["product_in_waste"] and r["liquid_cod"] > 0 \
                and r["product_cod"] / r["liquid_cod"] > 0.3:
            lines.append("")
            lines.append("  提示：产品 COD 占废水 COD 的 30% 以上。若该产品经离子交换/膜分离")
            lines.append("        回收，废水应改选「提取废液（离子交换/膜分离）」，否则会把产品")
            lines.append("        当作污染物算进废水，显著高估 COD。")
        lines.append("")
        lines.append("【废水排放估算】")
        lines.append(f"  废水产生量: {r['waste_vol']:.1f} m³/批")
        lines.append(f"  COD负荷: {r['cod_load']:.1f} kg O₂/批")
        lines.append(f"  ★ COD浓度: {r['cod_conc']:.0f} mg/L")
        lines.append("")
        lines.append("【数据来源与口径】")
        lines.append("  • 有机物料 COD 当量 = 理论需氧量 ThOD：C→CO₂、H→H₂O、N→NH₃（不计硝化）、S→SO₄²⁻")
        lines.append("  • 糖蜜/玉米浆/酵母浸粉/蛋白胨/豆粕水解液/菌体为工业经验值，无唯一理论解")
        lines.append("  • 结果为估算值，设计前请以实测 COD 校核")

        self.result_text.setText("\n".join(lines))

    def _display_analogy(self):
        r = self._last_results
        text = f"""══════════════════════════════
   发酵废水 COD 估算（类比缩放法）
══════════════════════════════

【参考项目（已知）】
  实测 COD: {r['ref_cod']:.0f} mg/L
  投糖量: {r['ref_sugar']:.1f} g/L
  产品产量: {r['ref_yield']:.1f} g/L
  残糖: {r['ref_residual']:.1f} g/L

【新项目（待估算）】
  投糖量: {r['new_sugar']:.1f} g/L
  产品产量: {r['new_yield']:.1f} g/L
  残糖: {r['new_residual']:.1f} g/L

【估算结果】
  缩放系数: {r['scale']:.3f}
  ★ 估算 COD: {r['cod_est']:.0f} mg/L

【说明】
  缩放基于 COD ∝ (投糖 - 0.18×产量 + 1.067×残糖) 的简化模型
  物料成分差异较大时建议使用物料衡算法
  最终以实测为准
"""
        self.result_text.setText(text)

    # ═══════════════════════════════════════
    # 辅助
    # ═══════════════════════════════════════

    def clear_all(self):
        idx = 0
        checked = self.mode_btn_group.checkedButton()
        if checked:
            idx = self.mode_btn_group.id(checked)
        self.setup_calculation_mode(idx)

    def _get_history_data(self):
        """提供历史记录数据"""
        mode = self._get_mode()
        inputs = {"计算模式": mode}
        outputs = {}
        if "物料" in mode:
            for key, label in [("batch_vol", "发酵体积_m3"), ("product_type", "产品类型"),
                               ("product_yield", "产品产量_g_L"), ("residual_sugar", "残糖_g_L"),
                               ("biomass", "菌体浓度_g_L"), ("waste_volume", "废水量_m3"),
                               ("waste_source", "废水来源"), ("wash_water", "洗涤水_m3")]:
                if key in self.input_widgets:
                    inputs[label] = self._get(key, "" if key == "product_type" else 0)
            # 非零原料投加量逐项记录
            for name, _ in MAT_LIST:
                key = "mat_" + name
                if key in self.input_widgets:
                    v = self._get(key, 0)
                    if v > 0:
                        inputs[f"原料_{name}_g_L"] = v
            outputs["COD_浓度_mg_L"] = round(self._last_results.get("cod_conc", 0), 0)
            outputs["COD_负荷_kg_批"] = round(self._last_results.get("cod_load", 0), 1)
        else:
            for key, label in [("ref_cod", "参考COD_mg_L"), ("new_sugar", "新项目投糖_g_L"),
                               ("new_yield", "新项目产量_g_L")]:
                if key in self.input_widgets:
                    inputs[label] = self._get(key, 0)
            outputs["COD_浓度_mg_L"] = round(self._last_results.get("cod_est", 0), 0)
        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        """获取项目信息（报告生成用，返回标准工程信息 dict）"""
        saved = {}
        try:
            if self.data_manager:
                saved = self.data_manager.get_project_info() or {}
        except Exception:
            saved = {}
        return {
            "company_name": saved.get("company_name", ""),
            "project_number": saved.get("project_number", ""),
            "project_name": saved.get("project_name", "废水COD估算"),
            "subproject_name": saved.get("subproject_name", ""),
            "calculation_type": self.calculation_type,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def generate_report(self):
        """生成报告内容（返回 str；未计算时返回 None，不生成空文件）"""
        if not self._last_results:
            return None
        r = self._last_results
        lines = [
            "=" * 60,
            "              废水COD估算报告",
            "=" * 60,
            "",
            f"生成时间：{self.get_project_info()['timestamp']}",
            f"计算模式：{r['mode']}",
            "",
        ]
        if r["mode"] == "物料衡算法":
            lines.extend([
                "-" * 40,
                "【发酵参数】",
                "-" * 40,
                f"  发酵体积: {r['vol']:.1f} m³",
                f"  产品类型: {r['product_type']}（COD当量 {r['product_cod_eq']:.3f} g O₂/g）",
                f"  产品产量: {r['product_yield']:.1f} g/L",
                f"  残糖: {r['residual_sugar']:.1f} g/L",
                f"  菌体浓度: {r['biomass']:.1f} g DCW/L",
                "",
                "-" * 40,
                "【COD 平衡】",
                "-" * 40,
                f"  投入总COD: {r['input_cod_total']:.1f} g O₂/L（各原料之和）",
                f"   ├ 产品COD: {r['product_cod']:.1f} g O₂/L",
                f"   ├ 菌体COD: {r['biomass_cod']:.1f} g O₂/L",
                f"   └ 残糖COD: {r['residual_cod']:.1f} g O₂/L",
                f"  呼吸氧化为CO₂: {max(r['mineralized_cod'], 0.0):.1f} g O₂/L（投入 − 上述三项）",
                f"  废水（液相）COD: {r['liquid_cod']:.1f} g O₂/L",
                f"  废水来源: {r['waste_source']}",
                f"  产品留在废水中: {'是' if r['product_in_waste'] else '否（已提取回收）'}"
                f"；菌体残留率: {r['biomass_retention']*100:.0f}%",
                "",
                "-" * 40,
                "【废水排放估算】",
                "-" * 40,
                f"  废水产生量: {r['waste_vol']:.1f} m³/批",
                f"  COD负荷: {r['cod_load']:.1f} kg O₂/批",
                f"  COD浓度: {r['cod_conc']:.0f} mg/L",
            ])
            if r["mineralized_cod"] < 0:
                lines.extend([
                    "",
                    "  ⚠ 物料口径不自洽：产品+菌体+残糖 COD 超过投入总 COD，",
                    "     该产量/残糖/当量组合在 COD 守恒上不可行，请核对投糖量与产品产量。",
                ])
        else:
            lines.extend([
                "-" * 40,
                "【参考项目】",
                "-" * 40,
                f"  实测 COD: {r['ref_cod']:.0f} mg/L",
                f"  投糖量: {r['ref_sugar']:.1f} g/L  产品产量: {r['ref_yield']:.1f} g/L  残糖: {r['ref_residual']:.1f} g/L",
                "",
                "-" * 40,
                "【新项目估算】",
                "-" * 40,
                f"  投糖量: {r['new_sugar']:.1f} g/L  产品产量: {r['new_yield']:.1f} g/L  残糖: {r['new_residual']:.1f} g/L",
                f"  缩放系数: {r['scale']:.3f}",
                f"  估算 COD: {r['cod_est']:.0f} mg/L",
            ])
        pi = self.get_project_info()
        lines.extend([
            "",
            "-" * 40,
            "【数据来源与口径】",
            "-" * 40,
            "  有机物料 COD 当量 = 理论需氧量 ThOD：C→CO₂、H→H₂O、N→NH₃（不计硝化）、S→SO₄²⁻",
            "  理论值可复核：n(O₂) = (4C + H + 6S − 3N − 2O)/4，ThOD = n(O₂)·32/M",
            "  糖蜜/玉米浆/酵母浸粉/蛋白胨/豆粕水解液/菌体 为工业经验值，无唯一理论解",
            "  COD 平衡按守恒式核算：投入COD = 产品 + 菌体 + 残糖 + 呼吸氧化为CO₂",
            "  本结果为估算值，工程设计前请以实测 COD 校核。",
            "",
            "=" * 60,
            "                      工程信息",
            "=" * 60,
            f"    公司名称: {pi.get('company_name', '')}",
            f"    工程编号: {pi.get('project_number', '')}",
            f"    工程名称: {pi.get('project_name', '')}",
            f"    子项名称: {pi.get('subproject_name', '')}",
            f"    计算日期: {datetime.datetime.now().strftime('%Y-%m-%d')}",
            "",
            "=" * 60,
            "                     报告结束",
            "=" * 60,
        ])
        return "\n".join(lines)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = CODEstimator()
    widget.resize(1200, 800)
    widget.show()
    sys.exit(app.exec())
