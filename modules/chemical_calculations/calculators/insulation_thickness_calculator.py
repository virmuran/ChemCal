import os
import math
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QGridLayout,
    QButtonGroup, QMessageBox, QFileDialog,
    QScrollArea,

)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator


class InsulationThicknessCalculator(QWidget):
    """保温厚度计算器（统一 UI 规范版）"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.data_manager = None
        self._last_result = {}   # 缓存最近一次计算结果
        self._last_params = {}    # 缓存最近一次输入参数
        self.setup_material_properties()
        self.setup_ui()

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
        group_style = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bdc3c7;
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

        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ──────────────── 左侧输入区 ────────────────
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        scroll_left.setWidgetResizable(True)

        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("QWidget { background: transparent; }")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 说明文字
        desc = QLabel(
            "计算保温层厚度，支持四种计算方法："
            "绝热层经济厚度、表面温度法、防结露、热损失法。"
            "请根据实际工况选择计算方法并填写参数。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        left_layout.addWidget(desc)

        # ── 计算类型选择（按钮组）──
        type_group = QGroupBox("计算类型")
        type_group.setStyleSheet(group_style)
        type_layout = QHBoxLayout(type_group)

        self.calc_type_group = QButtonGroup(self)
        calc_types = [
            ("绝热层经济厚度", "基于经济性考虑计算最佳保温厚度"),
            ("表面温度法",     "根据外表面温度要求计算保温厚度"),
            ("防结露",         "防止表面结露的最小保温厚度"),
            ("热损失法",       "根据允许热损失量计算保温厚度"),
        ]
        for i, (text, tip) in enumerate(calc_types):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.setMinimumWidth(110)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ecf0f1;
                    border: 1px solid #bdc3c7;
                    border-radius: 6px;
                    padding: 7px 4px;
                    font-size: 12px;
                }
                QPushButton:checked {
                    background-color: #3498db;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #d5dbdb;
                }
            """)
            self.calc_type_group.addButton(btn, i)
            type_layout.addWidget(btn)
        self.calc_type_group.buttons()[0].setChecked(True)
        self.calc_type_group.idClicked.connect(self._on_calc_type_changed)

        left_layout.addWidget(type_group)

        # ── 输入参数组（四列网格，适配多计算方法）──
        input_group = QGroupBox("输入参数")
        input_group.setStyleSheet(group_style)
        grid = QGridLayout(input_group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        label_style = "font-weight: bold; padding-right: 10px;"

        def make_lbl(text, row, col):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setFixedWidth(160)
            lbl.setStyleSheet(label_style)
            grid.addWidget(lbl, row, col)
            return lbl

        def make_edit(placeholder, validator_range, row, col):
            ed = QLineEdit()
            ed.setPlaceholderText(placeholder)
            ed.setFixedWidth(180)
            if validator_range:
                lo, hi, dec = validator_range
                ed.setValidator(QDoubleValidator(lo, hi, dec))
            grid.addWidget(ed, row, col)
            return ed

        def make_combo(items, row, col):
            cb = QComboBox()
            cb.addItems(items)
            cb.setFixedWidth(180)
            grid.addWidget(cb, row, col)
            return cb

        # 行0：设备型式 + 保温类型
        make_lbl("设备型式:", 0, 0)
        self.equipment_type_combo = make_combo(
            ["管道或圆筒形设备", "平面形设备"], 0, 1)
        self.equipment_type_combo.currentTextChanged.connect(
            self._on_equipment_type_changed)

        make_lbl("保温类型:", 0, 2)
        self.insulation_type_combo = make_combo(
            ["保温", "保冷"], 0, 3)
        self.insulation_type_combo.currentTextChanged.connect(
            self._on_insulation_type_changed)

        # 行1：设备尺寸 + 保温材料
        make_lbl("设备尺寸(mm):", 1, 0)
        self.size_input = make_edit("108", (1.0, 5000.0, 2), 1, 1)
        self.size_input.setText("108")

        make_lbl("保温材料:", 1, 2)
        self.material_combo = make_combo(
            list(self.material_properties.keys()) + ["自定义材料"], 1, 3)
        self.material_combo.currentTextChanged.connect(self._on_material_changed)

        # 行2：导热系数 + 材料密度
        make_lbl("导热系数(W/m·K):", 2, 0)
        self.conductivity_input = make_edit("0.0512", (0.001, 1.0, 6), 2, 1)
        self.conductivity_input.setText("0.0512")

        make_lbl("密度(kg/m³):", 2, 2)
        self.density_input = make_edit("170", (10.0, 500.0, 2), 2, 3)
        self.density_input.setText("170")

        # 行3：环境温度 + 风速
        make_lbl("环境温度(°C):", 3, 0)
        self.ambient_temp_input = make_edit("20", (-50.0, 60.0, 2), 3, 1)
        self.ambient_temp_input.setText("20")

        make_lbl("风速(m/s):", 3, 2)
        self.wind_speed_input = make_edit("3", (0.0, 20.0, 2), 3, 3)
        self.wind_speed_input.setText("3")

        # 行4：露点温度 + 设备温度
        make_lbl("露点温度(°C):", 4, 0)
        self.dew_point_input = make_edit("22", (-50.0, 60.0, 2), 4, 1)
        self.dew_point_input.setText("22")
        self.dew_point_label = grid.itemAtPosition(4, 0).widget()

        make_lbl("设备温度(°C):", 4, 2)
        self.equipment_temp_input = make_edit("200", (-200.0, 1000.0, 2), 4, 3)
        self.equipment_temp_input.setText("200")

        # ── 动态参数区（不同计算方法的特定参数）──
        self.dynamic_container = QWidget()
        self.dynamic_layout = QGridLayout(self.dynamic_container)
        self.dynamic_layout.setHorizontalSpacing(10)
        self.dynamic_layout.setVerticalSpacing(10)
        grid.addWidget(self.dynamic_container, 5, 0, 1, 4)

        left_layout.addWidget(input_group)

        # ── 计算按钮 ──
        calc_btn = QPushButton("▶  计算保温厚度")
        calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 8px;
                min-height: 50px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        calc_btn.clicked.connect(self.calculate)
        left_layout.addWidget(calc_btn)

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

        dl_txt_btn = QPushButton("⬇ 下载TXT报告")
        dl_txt_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white;
                font-weight: bold; border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #219a52; }
        """)
        dl_txt_btn.clicked.connect(self.download_txt_report)

        dl_pdf_btn = QPushButton("⬇ 下载PDF报告")
        dl_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; color: white;
                font-weight: bold; border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        dl_pdf_btn.clicked.connect(self.generate_pdf_report)

        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(dl_txt_btn)
        btn_row.addWidget(dl_pdf_btn)
        left_layout.addLayout(btn_row)
        left_layout.addStretch()

        # ──────────────── 右侧结果区 ────────────────
        right_widget = QWidget()
        right_widget.setMinimumWidth(400)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)

        result_group = QGroupBox("计算结果")
        result_group.setStyleSheet(group_style)
        result_vbox = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 13px;
                padding: 10px;
            }
        """)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        result_vbox.addWidget(self.result_text)
        right_layout.addWidget(result_group)

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
            w.setFixedWidth(160)
            w.setStyleSheet("font-weight: bold; padding-right: 10px;")
            return w

        def ed(placeholder, val_range):
            w = QLineEdit()
            w.setPlaceholderText(placeholder)
            w.setFixedWidth(180)
            if val_range:
                lo, hi, dec = val_range
                w.setValidator(QDoubleValidator(lo, hi, dec))
            return w

        if calc_type == "绝热层经济厚度":
            self.dynamic_layout.addWidget(lbl("能量价格(元/GJ):"), row, 0)
            self.energy_price_input = ed("3.6", (0.1, 100.0, 2))
            self.energy_price_input.setText("3.6")
            self.dynamic_layout.addWidget(self.energy_price_input, row, 1)

            self.dynamic_layout.addWidget(lbl("绝热造价(元/m³):"), row, 2)
            self.insulation_cost_input = ed("640", (100.0, 5000.0, 2))
            self.insulation_cost_input.setText("640")
            self.dynamic_layout.addWidget(self.insulation_cost_input, row, 3)
            row += 1

            self.dynamic_layout.addWidget(lbl("年运行时间(小时):"), row, 0)
            self.operation_time_input = ed("8000", (1.0, 8760.0, 2))
            self.operation_time_input.setText("8000")
            self.dynamic_layout.addWidget(self.operation_time_input, row, 1)

            self.dynamic_layout.addWidget(lbl("年利率(%):"), row, 2)
            self.interest_rate_input = ed("10", (0.1, 50.0, 2))
            self.interest_rate_input.setText("10")
            self.dynamic_layout.addWidget(self.interest_rate_input, row, 3)
            row += 1

            self.dynamic_layout.addWidget(lbl("计息年限(年):"), row, 0)
            self.years_input = ed("5", (1.0, 30.0, 2))
            self.years_input.setText("5")
            self.dynamic_layout.addWidget(self.years_input, row, 1)

        elif calc_type == "表面温度法":
            self.dynamic_layout.addWidget(lbl("外表面温度(°C):"), row, 0)
            self.surface_temp_input = ed("26", (-50.0, 200.0, 2))
            self.surface_temp_input.setText("26")
            self.dynamic_layout.addWidget(self.surface_temp_input, row, 1)

        elif calc_type == "热损失法":
            self.dynamic_layout.addWidget(lbl("允许热损失(W/m²):"), row, 0)
            self.heat_loss_limit_input = ed("160", (10.0, 1000.0, 2))
            self.heat_loss_limit_input.setText("160")
            self.dynamic_layout.addWidget(self.heat_loss_limit_input, row, 1)

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
        if hasattr(self, "dew_point_label"):
            self.dew_point_label.setEnabled(is_cold)

    # ──────────────────── 计算核心 ──────────────────────────────
    @staticmethod
    def _surface_htc(wind_speed, delta_t=None):
        """表面传热系数 (W/m²·K)，GB/T 8175 近似"""
        h_out = 11.63 + 7.12 * (wind_speed ** 0.6)
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

            if self.data_manager:
                try:
                    self.data_manager.add_record(
                        "insulation_thickness", self._get_history_data())
                except Exception:
                    pass

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

    def _surface_temp_method(self, equip_type, d1, lam, h,
                             ambient, equip_t, t_surf):
        """表面温度法求厚度（Newton-Raphson）"""
        t_guess = 0.010
        for _ in range(80):
            if equip_type == "管道或圆筒形设备":
                d2 = d1 + 2 * t_guess
                r_ins = math.log(d2 / d1) / (2 * math.pi * lam)
                heat = (equip_t - ambient) / (r_ins + 1 / (h * math.pi * d2))
                t_calc = ambient + heat * (1 / (h * math.pi * d2))
            else:
                r_ins = t_guess / lam
                heat = (equip_t - ambient) / (r_ins + 1 / h)
                t_calc = ambient + heat / h

            f = t_calc - t_surf
            if abs(f) < 0.05:
                break
            t_guess += -f * 0.001 if f > 0 else 0.001
            t_guess = max(t_guess, 0.001)

        return t_guess * 1000.0

    def _anti_condensation(self, equip_type, d1, lam,
                           ambient, equip_t, dew_point):
        """防结露最小厚度"""
        return self._surface_temp_method(
            equip_type, d1, lam,
            self._surface_htc(0.5, 10),
            ambient, equip_t, dew_point + 2.0)

    def _heat_loss_method(self, equip_type, d1, lam, h,
                          delta_t, q_limit):
        """允许热损失法求厚度"""
        t_guess = 0.010
        for _ in range(80):
            if equip_type == "管道或圆筒形设备":
                d2 = d1 + 2 * t_guess
                r_ins = math.log(d2 / d1) / (2 * math.pi * lam)
                r_surf = 1 / (h * math.pi * d2)
                q = delta_t / (r_ins + r_surf)        # W/m
                q_area = q / (math.pi * d2)           # W/m²
            else:
                r_ins = t_guess / lam
                q_area = delta_t / (r_ins + 1 / h)   # W/m²

            f = q_area - q_limit
            if abs(f) < 0.1:
                break
            t_guess += -f * 0.0001 if f > 0 else 0.0001
            t_guess = max(t_guess, 0.001)

        return t_guess * 1000.0

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
            "  GB/T 4272-2008   设备绝热技术通则",
            "  GB/T 8175-2008   设备及管道绝热设计导则",
            "  ASHRAE Fundamentals Handbook",
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
        return {
            "calculator": "InsulationThicknessCalculator",
            "name": "保温厚度计算",
        }

    # ──────────────────── 报告生成 ──────────────────────────────
    def generate_report(self):
        return self.result_text.toPlainText()

    def download_txt_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先执行计算，再下载报告。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存TXT报告", "保温厚度计算报告.txt", "文本文件 (*.txt)")
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
            QMessageBox.warning(self, "提示", "请先执行计算，再下载PDF。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存PDF报告", "保温厚度计算报告.pdf", "PDF文件 (*.pdf)")
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
                safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(safe if safe.strip() else "&nbsp;", st))
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
    w = InsulationThicknessCalculator()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
