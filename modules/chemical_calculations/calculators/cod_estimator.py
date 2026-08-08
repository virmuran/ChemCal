"""
发酵废水 COD 估算器
省略文档内容...
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QScrollArea,
    QButtonGroup, QGridLayout, QSizePolicy, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math

from calculator_base import CalculatorBase
from common_constants import C_TO_K, G, ATM_PRESSURE_MPA, WATER_DENSITY, WATER_CP, load_steam_iapws, get_steam_props
from app_styles import (COMBOBOX_STYLE, MODE_BUTTON_STYLE,
                        CALC_BUTTON_STYLE, SCROLL_AREA_STYLE,
                        INPUT_LABEL_STYLE, CLEAR_BTN_STYLE,
                        DOCX_BTN_STYLE, PDF_BTN_STYLE)

# ── COD 当量数据库 ──
COD_DB = {
    # 碳源
    "葡萄糖": (1.067, "碳源"),
    "蔗糖": (1.122, "碳源"),
    "淀粉(可溶)": (1.185, "碳源"),
    "甘油": (1.217, "碳源"),
    "糖蜜": (0.90, "碳源"),  # 经验值，约50%糖分
    # 有机氮源
    "玉米浆": (0.85, "氮源"),
    "酵母浸粉": (0.95, "氮源"),
    "豆粕水解液": (0.80, "氮源"),
    "蛋白胨": (0.90, "氮源"),
    "(NH₄)₂SO₄": (0.00, "无机氮"),  # 无机，不贡献COD
    "尿素": (0.00, "无机氮"),        # 无机
    # 有机酸/中间代谢物
    "乙酸": (1.067, "有机酸"),
    "乳酸": (1.067, "有机酸"),
    "柠檬酸": (0.75, "有机酸"),
    "琥珀酸": (0.95, "有机酸"),
    "乙醇": (2.087, "醇类"),
    # 氨基酸产品
    "L-缬氨酸": (1.638, "产品"),
    "L-赖氨酸": (1.532, "产品"),
    "L-苏氨酸": (1.075, "产品"),
    "L-谷氨酸": (0.979, "产品"),
    "L-亮氨酸": (1.830, "产品"),
    "L-异亮氨酸": (1.830, "产品"),
    "L-蛋氨酸": (1.073, "产品"),
    # 菌体
    "菌体干重(DCW)": (1.42, "菌体"),
    "菌体(湿重×20%)": (0.284, "菌体"),
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


class CODEstimator(CalculatorBase):
    """发酵废水 COD 估算器"""

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
        left = QWidget()
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
        mode_layout.addStretch()
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

        scroll.setWidget(left)

        # ── 右 ──
        right = QWidget()
        right.setMinimumWidth(300)
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)

        result_group = QGroupBox("计算结果")
        result_inner = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("font-size: 13px;")
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

        # 计算按钮
        self.calc_btn = CalculatorBase.make_calc_button()
        self.calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(self.calc_btn)

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
        ls = "font-weight: bold; padding-right: 10px;"
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
                hint.setStyleSheet("color: #666; font-size: 11px;")
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

        # ── 物料投加表 ──
        mat_label = QLabel("▼ 原料投加量 (g/L)：可在下方表格中增加/减少行")
        mat_label.setStyleSheet("font-weight: bold; color: #2c3e50; padding-top: 10px;")
        self.input_layout.addWidget(mat_label, row, 0, 1, 3)
        row += 1

        # 物料表：名称 | 投加量(g/L) | 操作
        self.mat_table = QTableWidget(0, 3)
        self.mat_table.setHorizontalHeaderLabels(["物料名称", "投加量 (g/L)", "操作"])
        self.mat_table.horizontalHeader().setStretchLastSection(False)
        self.mat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.mat_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.mat_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.mat_table.setMaximumHeight(200)
        self.mat_table.verticalHeader().setVisible(False)

        # 添加默认行
        default_mats = [("葡萄糖", "100"), ("玉米浆", "15"), ("酵母浸粉", "5")]
        for name, val in default_mats:
            self._add_mat_row(name, val)

        self.input_layout.addWidget(self.mat_table, row, 0, 1, 3)
        row += 1

        # 添加/删除物料按钮
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ 添加物料")
        add_btn.clicked.connect(self._add_mat_row_dialog)
        add_btn.setStyleSheet("QPushButton { color: #27ae60; font-weight: bold; padding: 4px 12px; }")
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        self.input_layout.addLayout(btn_row, row, 0, 1, 3)
        row += 1

        # ── 废水参数 ──
        lbl = QLabel("废水参数")
        lbl.setStyleSheet("font-weight: bold; color: #2c3e50; padding-top: 10px;")
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
                hint.setStyleSheet("color: #666; font-size: 11px;")
                self.input_layout.addWidget(hint, row, 2)
            else:
                le = QLineEdit()
                if placeholder:
                    le.setPlaceholderText(placeholder)
                self.input_layout.addWidget(le, row, 1)
                self.input_widgets[key] = le
            row += 1

    def _add_mat_row(self, name="", value=""):
        row_idx = self.mat_table.rowCount()
        self.mat_table.insertRow(row_idx)

        # 物料名下拉
        combo = QComboBox()
        combo.setStyleSheet(COMBOBOX_STYLE)
        # 排除产品和菌体类
        mat_names = [k for k, v in COD_DB.items() if v[1] in ("碳源", "氮源", "有机酸", "醇类")]
        combo.addItems([""] + mat_names)
        if name:
            idx = combo.findText(name)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        combo.setEditable(True)
        self.mat_table.setCellWidget(row_idx, 0, combo)

        # 投加量
        val_item = QTableWidgetItem(value)
        self.mat_table.setItem(row_idx, 1, val_item)

        # 删除按钮
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet("QPushButton { color: #e74c3c; font-weight: bold; }")
        del_btn.clicked.connect(lambda: self.mat_table.removeRow(row_idx))
        self.mat_table.setCellWidget(row_idx, 2, del_btn)

    def _add_mat_row_dialog(self):
        self._add_mat_row()

    def _read_mat_table(self):
        """从物料表读取数据，返回 [(name, conc_g_L), ...]"""
        rows = []
        for r in range(self.mat_table.rowCount()):
            combo = self.mat_table.cellWidget(r, 0)
            val_item = self.mat_table.item(r, 1)
            if not combo or not val_item:
                continue
            name = combo.currentText().strip()
            val_text = val_item.text().strip()
            if name and val_text:
                try:
                    val = float(val_text)
                    if val > 0:
                        rows.append((name, val))
                except ValueError:
                    pass
        return rows

    # ═══════════════════════════════════════
    # 模式2: 类比缩放法
    # ═══════════════════════════════════════

    def _setup_analogy(self):
        ls = "font-weight: bold; padding-right: 10px;"
        row = 0
        pairs = [
            # (label, key, placeholder, default)
            ("─ 参考项目（已知数据）─", None, None, None),
            ("参考项目 COD (mg/L):", "ref_cod", "例如：1800", ""),
            ("参考项目 投糖量 (g/L):", "ref_sugar", "例如：120", ""),
            ("参考项目 产品产量 (g/L):", "ref_yield", "例如：60", ""),
            ("参考项目 残糖 (g/L):", "ref_residual", "例如：5", ""),
            ("", None, None, None),
            ("─ 新项目（待估算）─", None, None, None),
            ("新项目 投糖量 (g/L):", "new_sugar", "例如：130", ""),
            ("新项目 产品产量 (g/L):", "new_yield", "例如：65", ""),
            ("新项目 残糖 (g/L):", "new_residual", "例如：4", ""),
        ]
        for label, key, placeholder, default in pairs:
            if not key:
                lbl = QLabel(label)
                lbl.setStyleSheet("font-weight: bold; color: #2c3e50; padding: 5px 0;")
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
        mat_rows = self._read_mat_table()

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

        # ── 废水COD总量 ──
        # 发酵液COD = 输入 - 产品 + 残糖 + 菌体(根据废水来源决定是否包含)
        waste_source = self._get("waste_source", "发酵废液（离心后上清液）")

        if "含菌体" in waste_source:
            liquid_cod = input_cod_total - product_cod + residual_cod + biomass_cod
        elif "上清液" in waste_source or "提取" in waste_source:
            liquid_cod = input_cod_total - product_cod + residual_cod + biomass_cod * 0.15  # 少量菌体残留
        else:
            liquid_cod = input_cod_total - product_cod + residual_cod + biomass_cod

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
        cod_load = liquid_cod * vol / 1000  # kg O₂/批 (从g/L×m³ → 需除以1000)
        # 注意: liquid_cod 是 g O₂/L, vol 是 m³ = 1000L
        # cod_load = liquid_cod (g/L) * vol (m³) * 1000 (L/m³) / 1000 (g/kg) = liquid_cod * vol
        cod_load = liquid_cod * vol  # kg/批

        if total_waste_vol > 0:
            cod_conc = cod_load / total_waste_vol  # mg/L (= g/m³, kg/m³ × 1000 = mg/L)
            # cod_load in kg, total_waste_vol in m³
            # cod_conc = cod_load * 1000 (g/kg) / total_waste_vol (m³) = mg/L
            cod_conc = cod_load * 1000 / total_waste_vol  # mg/L
        else:
            cod_conc = 0

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

        # 缩放因子：COD ∝ (投糖 - 产量修正 + 残糖差)
        # 简单缩放：按投糖量比例 × 产率修正
        sugar_ratio = new_sugar / ref_sugar if ref_sugar > 0 else 1
        yield_effect = (ref_sugar - ref_yield * 0.2) / (new_sugar - new_yield * 0.2) if (new_sugar - new_yield * 0.2) > 0 else 1

        # 综合缩放
        scale = (new_sugar - new_yield * 0.18 + new_residual * 1.067) / \
                (ref_sugar - ref_yield * 0.18 + ref_residual * 1.067) \
                if (ref_sugar - ref_yield * 0.18 + ref_residual * 1.067) > 0 else 1

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

        lines.append(f"  {'物料名称':<16} {'投加量':>8} {'COD当量':>8} {'贡献COD':>8} {'类别':<8}")
        lines.append(f"  {'─'*54}")
        for name, c in r["contrib_cod"].items():
            lines.append(f"  {name:<16} {c['conc']:>8.1f} {c['eq']:>8.3f} {c['cod']:>8.1f} {c['cat']:<8}")
        if r["residual_sugar"] > 0:
            lines.append(f"  {'残糖(葡萄糖)':<16} {r['residual_sugar']:>8.1f} {1.067:>8.3f} {residual_cod:>8.1f} {'残糖':<8}")
        if r["biomass"] > 0:
            lines.append(f"  {'菌体':<16} {r['biomass']:>8.1f} {1.42:>8.3f} {biomass_cod:>8.1f} {'菌体':<8}")

        lines.append("")
        lines.append("【COD 平衡】")
        lines.append(f"  投入总COD: {total_input:>8.1f} g O₂/L")
        lines.append(f"  - 产品带走: {product_cod:>8.1f} g O₂/L (产量×{r['product_cod_eq']:.3f})")
        lines.append(f"  + 残糖残留: {residual_cod:>8.1f} g O₂/L")
        lines.append(f"  + 菌体贡献: {biomass_cod:>8.1f} g O₂/L")
        lines.append(f"  ─────────────────────────")
        lines.append(f"  发酵液COD: {r['liquid_cod']:>8.1f} g O₂/L")
        lines.append(f"  废水来源: {r['waste_source']}")
        lines.append("")
        lines.append("【废水排放估算】")
        lines.append(f"  废水产生量: {r['waste_vol']:.1f} m³/批")
        lines.append(f"  COD负荷: {r['cod_load']:.1f} kg O₂/批")
        lines.append(f"  ★ COD浓度: {r['cod_conc']:.0f} mg/L")

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
        return {"inputs": {}, "outputs": {"COD_浓度_mg_L": round(self._last_results.get("cod_conc", self._last_results.get("cod_est", 0)), 0)}}


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = CODEstimator()
    widget.resize(1200, 800)
    widget.show()
    sys.exit(app.exec())
