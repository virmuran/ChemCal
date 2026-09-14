"""
保温厚度计算器 — 支持四种计算方法：
绝热层经济厚度、表面温度法、防结露、热损失法（GB/T 8175 近似）
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QGridLayout,
    QButtonGroup, QMessageBox,
    QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from datetime import datetime
import math

from app_styles import (COMBOBOX_STYLE, SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from utils.docx_utils import ReportExporter


class InsulationThicknessCalculator(CalculatorBase):
    """保温厚度计算器（统一 UI 规范版）"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_result = {}   # 缓存最近一次计算结果
        self._last_params = {}    # 缓存最近一次输入参数
        self.setup_material_properties()
        self.setup_ui()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception:
            self.data_manager = None

    # ─────────────────────────── 材料数据 ─────────────────────────────
    def setup_material_properties(self):
        self.material_properties = {
            "硅酸钙(170kg/m³)": {"conductivity": 0.0512, "density": 170},
            "岩棉":                {"conductivity": 0.040,  "density": 120},
            "玻璃棉":              {"conductivity": 0.042,  "density": 64},
            "硅酸铝纤维":          {"conductivity": 0.120,  "density": 200},
            "聚氨酯泡沫":          {"conductivity": 0.025,  "density": 40},
            "聚苯乙烯泡沫":        {"conductivity": 0.038,  "density": 30},
            "橡塑海绵":            {"conductivity": 0.038,  "density": 80},
            "气凝胶":              {"conductivity": 0.018,  "density": 180},
            "复合硅酸盐":          {"conductivity": 0.048,  "density": 180},
            "微孔硅酸钙":          {"conductivity": 0.055,  "density": 220},
            "珍珠岩":              {"conductivity": 0.065,  "density": 80},
        }

    # ─────────────────────────── UI ─────────────────────────────
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ──────────────── 左侧输入区 ────────────────
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(SCROLL_AREA_STYLE)
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 说明文字
        desc = QLabel(
            "计算保温层厚度，支持四种计算方法："
            "绝热层经济厚度、表面温度法、防结露、热损失法。"
            "请根据实际工况选择计算方法并填写参数。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc)

        # ── 计算类型选择（按钮组）──
        type_group = CalculatorBase.make_group_box("计算类型")
        type_layout = QHBoxLayout(type_group)

        self.calc_type_group = QButtonGroup(self)
        calc_types = [
            ("绝热层经济厚度", "基于经济性考虑计算最佳保温厚度"),
            ("表面温度法",     "根据外表面温度要求计算保温厚度"),
            ("防结露",         "防止表面结露的最小保温厚度"),
            ("热损失法",       "根据允许热损失量计算保温厚度"),
        ]
        for i, (text, tip) in enumerate(calc_types):
            btn = CalculatorBase.make_mode_button(text, tip)
            self.calc_type_group.addButton(btn, i)
            type_layout.addWidget(btn)
        self.calc_type_group.buttons()[0].setChecked(True)
        self.calc_type_group.idClicked.connect(self._on_calc_type_changed)

        left_layout.addWidget(type_group)

        # ── 输入参数组（三列网格：标签(4) : 输入(8) : 提示(5)）──
        input_group = CalculatorBase.make_group_box("输入参数")
        grid = QGridLayout(input_group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)

        row = 0

        def make_lbl(text):
            nonlocal row
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet(INPUT_LABEL_STYLE)
            grid.addWidget(lbl, row, 0)
            return lbl

        def make_edit(placeholder, validator_range, default=None):
            ed = QLineEdit()
            ed.setPlaceholderText(placeholder)
            if validator_range:
                lo, hi, dec = validator_range
                ed.setValidator(QDoubleValidator(lo, hi, dec))
            if default is not None:
                ed.setText(default)
            return ed

        def make_hint(text):
            h = QLabel(text)
            h.setStyleSheet("font-style: italic;")
            grid.addWidget(h, row, 2)
            return h

        # 行0：设备型式 + 保温类型
        make_lbl("设备型式:")
        self.equipment_type_combo = QComboBox()
        self.equipment_type_combo.setStyleSheet(COMBOBOX_STYLE)
        self.equipment_type_combo.addItems(["管道或圆筒形设备", "平面形设备"])
        self.equipment_type_combo.currentTextChanged.connect(
            self._on_equipment_type_changed)
        grid.addWidget(self.equipment_type_combo, row, 1)
        make_hint("管道直径或平面宽度")

        row += 1

        make_lbl("保温类型:")
        self.insulation_type_combo = QComboBox()
        self.insulation_type_combo.setStyleSheet(COMBOBOX_STYLE)
        self.insulation_type_combo.addItems(["保温", "保冷"])
        self.insulation_type_combo.currentTextChanged.connect(
            self._on_insulation_type_changed)
        grid.addWidget(self.insulation_type_combo, row, 1)
        self.insulation_hint = make_hint("保冷时需填写露点温度")

        row += 1

        # 行2：设备尺寸 + 保温材料
        make_lbl("设备尺寸(mm):")
        self.size_input = make_edit("108", (1.0, 5000.0, 2), "108")
        grid.addWidget(self.size_input, row, 1)
        make_hint("管道公称直径或设备宽度")

        row += 1

        make_lbl("保温材料:")
        self.material_combo = QComboBox()
        self.material_combo.setStyleSheet(COMBOBOX_STYLE)
        self.material_combo.addItems(
            list(self.material_properties.keys()) + ["自定义材料"])
        self.material_combo.currentTextChanged.connect(self._on_material_changed)
        grid.addWidget(self.material_combo, row, 1)
        make_hint("选择材料自动填充物性")

        row += 1

        # 行4：导热系数 + 材料密度
        make_lbl("导热系数(W/m·K):")
        self.conductivity_input = make_edit("0.0512", (0.001, 1.0, 6), "0.0512")
        grid.addWidget(self.conductivity_input, row, 1)
        make_hint("随温度略有变化")

        row += 1

        make_lbl("密度(kg/m³):")
        self.density_input = make_edit("170", (10.0, 500.0, 2), "170")
        grid.addWidget(self.density_input, row, 1)
        make_hint("用于估算荷载")

        row += 1

        # 行6：环境温度 + 风速
        make_lbl("环境温度(°C):")
        self.ambient_temp_input = make_edit("20", (-50.0, 60.0, 2), "20")
        grid.addWidget(self.ambient_temp_input, row, 1)
        make_hint("室内可取20~25")

        row += 1

        make_lbl("风速(m/s):")
        self.wind_speed_input = make_edit("3", (0.0, 20.0, 2), "3")
        grid.addWidget(self.wind_speed_input, row, 1)
        make_hint("室外一般取2~5")

        row += 1

        # 行8：露点温度 + 设备温度
        make_lbl("露点温度(°C):")
        self.dew_point_input = make_edit("22", (-50.0, 60.0, 2), "22")
        grid.addWidget(self.dew_point_input, row, 1)
        self.dew_point_hint = make_hint("仅保冷工况使用")

        row += 1

        make_lbl("设备温度(°C):")
        self.equipment_temp_input = make_edit("200", (-200.0, 1000.0, 2), "200")
        grid.addWidget(self.equipment_temp_input, row, 1)
        make_hint("介质工作温度")

        row += 1

        # ── 动态参数区（不同计算方法的特定参数）──
        self.dynamic_container = QWidget()
        self.dynamic_layout = QGridLayout(self.dynamic_container)
        self.dynamic_layout.setHorizontalSpacing(10)
        self.dynamic_layout.setVerticalSpacing(10)
        self.dynamic_layout.setColumnStretch(0, 4)
        self.dynamic_layout.setColumnStretch(1, 8)
        self.dynamic_layout.setColumnStretch(2, 5)
        grid.addWidget(self.dynamic_container, row, 0, 1, 3)

        left_layout.addWidget(input_group)

        left_layout.addStretch()

        # ──────────────── 右侧结果区 ────────────────
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        result_group = CalculatorBase.make_group_box("计算结果")
        result_vbox = QVBoxLayout(result_group)

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
        result_vbox.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # ── 底部按钮行：清空 | DOCX | PDF ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        for name, style, cb in [
            ("清空", CLEAR_BTN_STYLE, self.clear_inputs),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(name)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(cb)
            btn_layout.addWidget(btn)
        right_layout.addLayout(btn_layout)

        # ── 计算按钮（最底部） ──
        calc_btn = self.make_calc_button("计 算")
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)

        # 拼合
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

        # 初始化动态参数 + UI 可见性
        self._build_dynamic_params()
        self._update_ui_visibility()

    # ──────────────────── 动态参数 ──────────────────────────────
    def _build_dynamic_params(self):
        """根据当前计算方法重建动态参数区"""
        # 清空
        while self.dynamic_layout.count():
            child = self.dynamic_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        calc_type = self._get_calc_type()
        row = 0

        def lbl(text):
            w = QLabel(text)
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            w.setStyleSheet(INPUT_LABEL_STYLE)
            self.dynamic_layout.addWidget(w, row, 0)
            return w

        def ed(placeholder, val_range, default=None):
            w = QLineEdit()
            w.setPlaceholderText(placeholder)
            if val_range:
                lo, hi, dec = val_range
                w.setValidator(QDoubleValidator(lo, hi, dec))
            if default is not None:
                w.setText(default)
            return w

        def hint(text):
            w = QLabel(text)
            w.setStyleSheet("font-style: italic;")
            self.dynamic_layout.addWidget(w, row, 2)
            return w

        if calc_type == "绝热层经济厚度":
            lbl("能量价格(元/GJ):")
            self.energy_price_input = ed("3.6", (0.1, 100.0, 2), "3.6")
            self.dynamic_layout.addWidget(self.energy_price_input, row, 1)
            hint("蒸汽/电折算价格")
            row += 1

            lbl("绝热造价(元/m³):")
            self.insulation_cost_input = ed("640", (100.0, 5000.0, 2), "640")
            self.dynamic_layout.addWidget(self.insulation_cost_input, row, 1)
            hint("含材料+施工")
            row += 1

            lbl("年运行时间(小时):")
            self.operation_time_input = ed("8000", (1.0, 8760.0, 2), "8000")
            self.dynamic_layout.addWidget(self.operation_time_input, row, 1)
            hint("连续运行取8000+")
            row += 1

            lbl("年利率(%):")
            self.interest_rate_input = ed("10", (0.1, 50.0, 2), "10")
            self.dynamic_layout.addWidget(self.interest_rate_input, row, 1)
            hint("投资回收折现率")
            row += 1

            lbl("计息年限(年):")
            self.years_input = ed("5", (1.0, 30.0, 2), "5")
            self.dynamic_layout.addWidget(self.years_input, row, 1)
            hint("投资回收年限")

        elif calc_type == "表面温度法":
            lbl("外表面温度(°C):")
            self.surface_temp_input = ed("26", (-50.0, 200.0, 2), "26")
            self.dynamic_layout.addWidget(self.surface_temp_input, row, 1)
            hint("防烫伤常取≤50")

        elif calc_type == "热损失法":
            lbl("允许热损失(W/m²):")
            self.heat_loss_limit_input = ed("160", (10.0, 1000.0, 2), "160")
            self.dynamic_layout.addWidget(self.heat_loss_limit_input, row, 1)
            hint("按GB/T 4272选取")

        # 防结露法：无额外参数

    def _get_calc_type(self):
        btn = self.calc_type_group.checkedButton()
        return btn.text() if btn else "绝热层经济厚度"

    def _on_calc_type_changed(self, _id):
        self._build_dynamic_params()
        self._update_ui_visibility()

    def _on_equipment_type_changed(self, _text):
        pass

    def _on_insulation_type_changed(self, text):
        self._update_ui_visibility()

    def _on_material_changed(self, text):
        if text in self.material_properties:
            p = self.material_properties[text]
            self.conductivity_input.setText(str(p["conductivity"]))
            self.density_input.setText(str(p["density"]))

    def _update_ui_visibility(self):
        is_cold = self.insulation_type_combo.currentText() == "保冷"
        self.dew_point_input.setEnabled(is_cold)
        if hasattr(self, "dew_point_hint"):
            self.dew_point_hint.setEnabled(is_cold)

    # ──────────────────── 计算核心 ──────────────────────────────
    @staticmethod
    def _surface_htc(wind_speed, delta_t=None):
        """表面传热系数 (W/m²·K)。
        GB/T 8175-2008 §5.3.2：经济厚度/热损失计算 α 取常数 11.63（风速=0 时本式退化为此值）；
        校核表面温度 α = 1.163·(6+3√ω)，化工设计手册室外式 α = 11.63 + 7.12·√ω。
        """
        h_out = 11.63 + 7.12 * (wind_speed ** 0.5) if wind_speed > 0 else 11.63
        h_in = 9.1 + 0.052 * (delta_t or 20)
        return max(h_out, h_in)

    def calculate(self):
        try:
            ct = self._get_calc_type()
            equip_type = self.equipment_type_combo.currentText()
            ins_type = self.insulation_type_combo.currentText()
            size = float(self.size_input.text() or 108) / 1000.0
            conductivity = float(self.conductivity_input.text() or 0.0512)
            ambient = float(self.ambient_temp_input.text() or 20)
            wind = float(self.wind_speed_input.text() or 3)
            equip_t = float(self.equipment_temp_input.text() or 200)

            args = {
                "calc_type": ct,
                "equipment_type": equip_type,
                "insulation_type": ins_type,
                "size": size,
                "conductivity": conductivity,
                "ambient_temp": ambient,
                "wind_speed": wind,
                "equipment_temp": equip_t,
            }

            h = self._surface_htc(wind, abs(equip_t - ambient))
            delta_t = abs(equip_t - ambient)

            if ct == "绝热层经济厚度":
                ep = float(self.energy_price_input.text() or 3.6)
                ic = float(self.insulation_cost_input.text() or 640)
                ot = float(self.operation_time_input.text() or 8000)
                ir = float(self.interest_rate_input.text() or 10) / 100.0
                yr = float(self.years_input.text() or 5)
                thk = self._economic_thickness(
                    equip_type, size, conductivity, h,
                    delta_t, ep, ic, ot, ir, yr)
                method_name = "绝热层经济厚度法"

            elif ct == "表面温度法":
                t_surf = float(self.surface_temp_input.text() or 26)
                thk = self._surface_temp_method(
                    equip_type, size, conductivity, h,
                    ambient, equip_t, t_surf)
                method_name = "表面温度法"

            elif ct == "防结露":
                dew = float(self.dew_point_input.text() or 22)
                thk = self._anti_condensation(
                    equip_type, size, conductivity, ambient, equip_t, dew)
                method_name = "防结露法"

            elif ct == "热损失法":
                q_limit = float(self.heat_loss_limit_input.text() or 160)
                thk = self._heat_loss_method(
                    equip_type, size, conductivity, h,
                    delta_t, q_limit)
                method_name = "最大允许热损失法"
            else:
                raise ValueError(f"未知计算类型：{ct}")

            self._last_result = {
                "thickness_mm": thk,
                "method": method_name,
                "calc_type": ct,
            }
            self._last_params = args
            self._display_result(thk, ct, method_name, args)

        except ValueError as e:
            self._show_error(f"输入错误：{e}")
        except Exception as e:
            self._show_error(f"计算错误：{e}")

    # ── 各种厚度计算方法 ──

    def _economic_thickness(self, equip_type, d1, lam, h,
                           delta_t, energy_price, ins_cost,
                           op_time, interest, years):
        """绝热层经济厚度（迭代法）"""
        energy_price_j = energy_price / 1e9
        op_time_s = op_time * 3600.0
        crf = (interest * (1 + interest) ** years) / \
              ((1 + interest) ** years - 1) if interest > 0 else 1.0

        best, min_cost = 0.010, float("inf")

        for t_int in range(1, 301):
            t = t_int / 1000.0
            if equip_type == "管道或圆筒形设备":
                d2 = d1 + 2 * t
                r_ins = math.log(d2 / d1) / (2 * math.pi * lam)
                r_surf = 1 / (h * math.pi * d2)
                q = delta_t / (r_ins + r_surf)    # W/m
                vol = math.pi * (d2 ** 2 - d1 ** 2) / 4
            else:
                r_ins = t / lam
                r_surf = 1 / h
                q = delta_t / (r_ins + r_surf)    # W/m²
                vol = t

            ann_heat = q * op_time_s * energy_price_j
            ann_inv = vol * ins_cost * crf
            total = ann_heat + ann_inv
            if total < min_cost:
                min_cost = total
                best = t

        return best * 1000.0

    @staticmethod
    def _bisect_thickness(g, lo=0.0005, hi=1.0, tol=0.02):
        """在 [lo, hi] (m) 上对单调函数 g(t) 二分求根。
        g 应关于 t 单调且两端异号；无异号时返回偏差较小的端点。"""
        glo, ghi = g(lo), g(hi)
        if glo * ghi > 0:
            return (lo if abs(glo) < abs(ghi) else hi) * 1000.0
        best = (lo + hi) / 2
        for _ in range(80):
            mid = (lo + hi) / 2
            gm = g(mid)
            best = mid
            if abs(gm) < tol:
                break
            if glo * gm <= 0:
                hi = mid
                ghi = gm
            else:
                lo = mid
                glo = gm
        return best * 1000.0

    def _surface_temp_method(self, equip_type, d1, lam, h,
                             ambient, equip_t, t_surf):
        """表面温度法求厚度：解 t_calc(δ) = t_surf（二分法）"""
        def g(t):
            if equip_type == "管道或圆筒形设备":
                d2 = d1 + 2 * t
                r_ins = math.log(d2 / d1) / (2 * math.pi * lam)
                heat = (equip_t - ambient) / (r_ins + 1 / (h * math.pi * d2))
                t_calc = ambient + heat * (1 / (h * math.pi * d2))
            else:
                r_ins = t / lam
                heat = (equip_t - ambient) / (r_ins + 1 / h)
                t_calc = ambient + heat / h
            return t_calc - t_surf

        return self._bisect_thickness(g, tol=0.02)

    def _anti_condensation(self, equip_type, d1, lam,
                           ambient, equip_t, dew_point):
        """防结露最小厚度"""
        return self._surface_temp_method(
            equip_type, d1, lam,
            self._surface_htc(0.5, 10),
            ambient, equip_t, dew_point + 2.0)

    def _heat_loss_method(self, equip_type, d1, lam, h,
                          delta_t, q_limit):
        """允许热损失法求厚度：解 q_area(δ) = q_limit（二分法）"""
        def g(t):
            if equip_type == "管道或圆筒形设备":
                d2 = d1 + 2 * t
                r_ins = math.log(d2 / d1) / (2 * math.pi * lam)
                r_surf = 1 / (h * math.pi * d2)
                q = delta_t / (r_ins + r_surf)        # W/m
                q_area = q / (math.pi * d2)           # W/m²
            else:
                r_ins = t / lam
                q_area = delta_t / (r_ins + 1 / h)   # W/m²
            return q_area - q_limit

        return self._bisect_thickness(g, tol=0.05)

    # ──────────────────── 结果显示 ──────────────────────────────
    def _display_result(self, thk_mm, calc_type, method_name, params):
        lines = [
            "=" * 50,
            "         保温厚度计算结果",
            "=" * 50,
            "",
            "【计算信息】",
            f"  计算方法   : {method_name}",
            f"  设备型式   : {params['equipment_type']}",
            f"  保温类型   : {params['insulation_type']}",
            "",
            "【输入参数】",
            f"  设备尺寸   : {float(self.size_input.text() or 108):.1f} mm",
            f"  导热系数   : {float(self.conductivity_input.text() or 0.0512):.6f} W/(m·K)",
            f"  材料密度   : {float(self.density_input.text() or 170):.0f} kg/m³",
            f"  环境温度   : {float(self.ambient_temp_input.text() or 20):.1f} °C",
            f"  设备温度   : {float(self.equipment_temp_input.text() or 200):.1f} °C",
            f"  风速       : {float(self.wind_speed_input.text() or 3):.1f} m/s",
            "",
        ]

        # 动态参数
        if calc_type == "绝热层经济厚度":
            lines += [
                "【经济参数】",
                f"  能量价格   : {float(self.energy_price_input.text() or 3.6):.2f} 元/GJ",
                f"  绝热造价   : {float(self.insulation_cost_input.text() or 640):.0f} 元/m³",
                f"  年运行时间 : {float(self.operation_time_input.text() or 8000):.0f} h",
                f"  年利率     : {float(self.interest_rate_input.text() or 10):.1f} %",
                f"  计息年限   : {float(self.years_input.text() or 5):.0f} 年",
                "",
            ]
        elif calc_type == "表面温度法":
            lines += [
                "【目标参数】",
                f"  外表面温度 : {float(self.surface_temp_input.text() or 26):.1f} °C",
                "",
            ]
        elif calc_type == "防结露":
            lines += [
                "【目标参数】",
                f"  露点温度   : {float(self.dew_point_input.text() or 22):.1f} °C",
                f"  目标表面温 : {float(self.dew_point_input.text() or 22):.1f} + 2.0 = {float(self.dew_point_input.text() or 22) + 2:.1f} °C",
                "",
            ]
        elif calc_type == "热损失法":
            lines += [
                "【目标参数】",
                f"  允许热损失 : {float(self.heat_loss_limit_input.text() or 160):.0f} W/m²",
                "",
            ]

        lines += [
            "【计算结果】",
            f"  ★ 推荐保温厚度：{thk_mm:.1f} mm",
            f"                       ({thk_mm / 1000:.3f} m)",
            "",
            "【标准依据】",
            "  GB/T 8175        设备及管道绝热设计导则（公式按 2008 版核对；2025 新版已发布代替）",
            "  GB/T 4272-2024   设备及管道绝热技术通则",
            "",
            "【工程建议】",
        ]

        # 工程建议
        if thk_mm < 20:
            lines.append("  保温厚度偏薄（<20mm），")
        elif thk_mm > 100:
            lines.append("  保温厚度较大（>100mm），建议核算经济厚度。")
        else:
            lines.append("  保温厚度处于合理范围（20~100mm）。")

        ins_type = params["insulation_type"]
        if ins_type == "保冷":
            lines.append("  保冷工况：注意防潮层及接缝密封，防止结露腐蚀。")
        else:
            lines.append("  保温工况：建议在外表面加设保护层（铝皮/镀锌板）。")

        lines += [
            "",
            "  ⚠️  本结果为理论计算值，",
            "      实际工程请结合施工条件、规范安全系数，",
            "      并由专业工程师确认设计方案。",
            "=" * 50,
        ]
        self.result_text.setPlainText("\n".join(lines))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"⚠️  错误：{msg}")

    # ──────────────────── 清空 ───────────────────────────────────
    def clear_inputs(self):
        self.size_input.setText("108")
        self.material_combo.setCurrentIndex(0)
        self.conductivity_input.setText("0.0512")
        self.density_input.setText("170")
        self.ambient_temp_input.setText("20")
        self.wind_speed_input.setText("3")
        self.dew_point_input.setText("22")
        self.equipment_temp_input.setText("200")
        self.calc_type_group.buttons()[0].setChecked(True)
        self._build_dynamic_params()
        self.result_text.clear()
        self._last_result = {}
        self._last_params = {}

    # ──────────────────── 历史数据 ──────────────────────────────
    def _get_history_data(self):
        r = self._last_result
        p = self._last_params
        return {
            "inputs": {
                "计算方法": p.get("calc_type", ""),
                "设备型式": p.get("equipment_type", ""),
                "保温类型": p.get("insulation_type", ""),
                "设备尺寸_mm": p.get("size", 0) * 1000,
                "导热系数_W_mK": p.get("conductivity", 0),
            },
            "outputs": {
                "推荐保温厚度_mm": round(r.get("thickness_mm", 0), 1),
                "计算方法": r.get("method", ""),
            }
        }

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

    # ──────────────────── 报告生成 ──────────────────────────────
    def generate_report(self):
        """生成计算书文本（str）"""
        try:
            result_text = self.result_text.toPlainText()
            if not result_text or ("保温厚度" not in result_text or "错误" in result_text[:10]):
                return None

            project_info = self.get_project_info()
            report = f"""══════════════════════════════════════════
          保温厚度计算计算书
══════════════════════════════════════════

{result_text}

══════════════════════════════════════════
 工程信息
══════════════════════════════════════════

  公司名称: {project_info.get('company_name', '')}
  工程编号: {project_info.get('project_number', '')}
  工程名称: {project_info.get('project_name', '')}
  子项名称: {project_info.get('subproject_name', '')}
  计算日期: {datetime.now().strftime('%Y-%m-%d')}

══════════════════════════════════════════
备注说明
══════════════════════════════════════════

  1. 计算依据 GB/T 4272-2008、GB/T 8175-2008 及 ASHRAE 手册
  2. 表面传热系数按风速与温差近似取值，实际受气象条件影响
  3. 计算结果为理论值，实际工程需结合施工条件由专业工程师确认

---
生成于 ChemCal 工程计算模块
"""
            return report

        except Exception as e:
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "保温厚度计算")

    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "保温厚度计算")

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = InsulationThicknessCalculator()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
