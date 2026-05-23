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
class SafetyValveCalculator(QWidget):
    """安全阀计算器（统一 UI 规范版）"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_result = {}
        self._last_params = {}
        self.setup_ui()

    def init_data_manager(self):
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception:
            self.data_manager = None

    # ─────────────────────────── UI ─────────────────────────────
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
            "计算安全阀喉径面积和推荐喉径，基于 ASME BPVC Section VIII / API RP 520 标准。"
            "支持气体/蒸汽临界流与亚临界流、液体泄放、火灾工况计算。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc)

        # ── 工况条件组 ──
        cond_group = QGroupBox("工况条件")
        cond_group.setStyleSheet(GROUP_STYLE)
        grid = QGridLayout(cond_group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)


        label_style = "font-weight: bold; padding-right: 10px;"

        def make_lbl(text):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet(label_style)
            return lbl

        # 行0：介质类型
        self.medium_combo = QComboBox()
        self.medium_combo.setStyleSheet(COMBOBOX_STYLE)
        self.medium_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.medium_combo.addItems(["蒸汽", "空气", "气体", "液体", "两相流"])
        self.medium_combo.currentTextChanged.connect(self._on_medium_changed)
        grid.addWidget(make_lbl("介质类型:"), 0, 0)
        grid.addWidget(self.medium_combo, 0, 1)
        hint_m = QLabel("选择后自动填充分子量和绝热指数")
        hint_m.setStyleSheet("font-style: italic;")
        grid.addWidget(hint_m, 0, 2)

        # 行1：分子量
        self.mw_input = QLineEdit("18")
        self.mw_input.setValidator(QDoubleValidator(1, 200, 2))
        self.mw_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(make_lbl("分子量 (g/mol):"), 1, 0)
        grid.addWidget(self.mw_input, 1, 1)
        hint_mw = QLabel("蒸汽=18, 空气=29")
        hint_mw.setStyleSheet("font-style: italic;")
        grid.addWidget(hint_mw, 1, 2)

        # 行2：绝热指数
        self.gamma_input = QLineEdit("1.3")
        self.gamma_input.setValidator(QDoubleValidator(1.0, 2.0, 3))
        self.gamma_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(make_lbl("绝热指数 (γ):"), 2, 0)
        grid.addWidget(self.gamma_input, 2, 1)
        hint_g = QLabel("双原子=1.4")
        hint_g.setStyleSheet("font-style: italic;")
        grid.addWidget(hint_g, 2, 2)

        # 行3：设定压力
        self.set_pressure_input = QLineEdit("1.0")
        self.set_pressure_input.setValidator(QDoubleValidator(0.01, 100, 3))
        self.set_pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(make_lbl("设定压力:"), 3, 0)
        grid.addWidget(self.set_pressure_input, 3, 1)
        hint_p = QLabel("MPa (表压)")
        grid.addWidget(hint_p, 3, 2)

        # 行4：背压
        self.back_pressure_input = QLineEdit("0.1")
        self.back_pressure_input.setValidator(QDoubleValidator(0, 100, 3))
        self.back_pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(make_lbl("背压:"), 4, 0)
        grid.addWidget(self.back_pressure_input, 4, 1)
        hint_bp = QLabel("MPa")
        grid.addWidget(hint_bp, 4, 2)

        # 行5：超压百分比
        self.overpressure_input = QLineEdit("10")
        self.overpressure_input.setValidator(QDoubleValidator(10, 100, 1))
        self.overpressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(make_lbl("超压百分比:"), 5, 0)
        grid.addWidget(self.overpressure_input, 5, 1)
        hint_op = QLabel("通常 10% 或 21%")
        hint_op.setStyleSheet("font-style: italic;")
        grid.addWidget(hint_op, 5, 2)

        # 行6：操作温度
        self.temp_input = QLineEdit("100")
        self.temp_input.setValidator(QDoubleValidator(-273, 1000, 1))
        self.temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(make_lbl("操作温度 (°C):"), 6, 0)
        grid.addWidget(self.temp_input, 6, 1)
        hint_t = QLabel("")
        grid.addWidget(hint_t, 6, 2)

        # 行7：泄放温度
        self.relief_temp_input = QLineEdit("150")
        self.relief_temp_input.setValidator(QDoubleValidator(-273, 1000, 1))
        self.relief_temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(make_lbl("泄放温度 (°C):"), 7, 0)
        grid.addWidget(self.relief_temp_input, 7, 1)
        hint_rt = QLabel("")
        grid.addWidget(hint_rt, 7, 2)

        # 行8：压缩因子
        self.z_input = QLineEdit("1.0")
        self.z_input.setValidator(QDoubleValidator(0.1, 2.0, 3))
        self.z_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(make_lbl("压缩因子 Z:"), 8, 0)
        grid.addWidget(self.z_input, 8, 1)
        hint_z = QLabel("理想气体=1.0")
        hint_z.setStyleSheet("font-style: italic;")
        grid.addWidget(hint_z, 8, 2)

        left_layout.addWidget(cond_group)

        # ── 泄放条件组 ──
        relief_group = QGroupBox("泄放条件")
        relief_group.setStyleSheet(GROUP_STYLE)
        rgrid = QGridLayout(relief_group)
        rgrid.setHorizontalSpacing(10)
        rgrid.setVerticalSpacing(12)
        rgrid.setColumnStretch(0, 4)
        rgrid.setColumnStretch(1, 8)
        rgrid.setColumnStretch(2, 5)

        # 行0：泄放量
        self.relief_rate_input = QLineEdit("1000")
        self.relief_rate_input.setValidator(QDoubleValidator(0, 1e8, 1))
        self.relief_rate_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rgrid.addWidget(make_lbl("泄放量 (kg/h):"), 0, 0)
        rgrid.addWidget(self.relief_rate_input, 0, 1)
        hint_rr = QLabel("已知泄放量")
        hint_rr.setStyleSheet("font-style: italic;")
        rgrid.addWidget(hint_rr, 0, 2)

        # 行1：润湿面积 + 工况类型
        self.wetted_area_input = QLineEdit("50")
        self.wetted_area_input.setValidator(QDoubleValidator(0, 10000, 1))
        self.wetted_area_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rgrid.addWidget(make_lbl("润湿面积 (m²):"), 1, 0)
        rgrid.addWidget(self.wetted_area_input, 1, 1)

        self.fire_combo = QComboBox()
        self.fire_combo.setStyleSheet(COMBOBOX_STYLE)
        self.fire_combo.addItems(["普通工况", "火灾工况"])
        self.fire_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rgrid.addWidget(self.fire_combo, 1, 2)

        # 行2：环境因子
        self.env_factor_input = QLineEdit("1.0")
        self.env_factor_input.setValidator(QDoubleValidator(0.1, 2.0, 2))
        self.env_factor_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rgrid.addWidget(make_lbl("环境因子 F:"), 2, 0)
        rgrid.addWidget(self.env_factor_input, 2, 1)
        hint_ef = QLabel("标准=1.0")
        hint_ef.setStyleSheet("font-style: italic;")
        rgrid.addWidget(hint_ef, 2, 2)

        left_layout.addWidget(relief_group)

        # ── 安全阀参数组 ──
        valve_group = QGroupBox("安全阀参数")
        valve_group.setStyleSheet(GROUP_STYLE)
        vgrid = QGridLayout(valve_group)
        vgrid.setHorizontalSpacing(10)
        vgrid.setVerticalSpacing(12)
        vgrid.setColumnStretch(0, 4)
        vgrid.setColumnStretch(1, 8)
        vgrid.setColumnStretch(2, 5)

        self.valve_type_combo = QComboBox()
        self.valve_type_combo.setStyleSheet(COMBOBOX_STYLE)
        self.valve_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.valve_type_combo.addItems(["弹簧式", "先导式", "重锤式"])
        vgrid.addWidget(make_lbl("安全阀类型:"), 0, 0)
        vgrid.addWidget(self.valve_type_combo, 0, 1)
        hint_vt = QLabel("")
        vgrid.addWidget(hint_vt, 0, 2)

        self.material_combo = QComboBox()
        self.material_combo.setStyleSheet(COMBOBOX_STYLE)
        self.material_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.material_combo.addItems(["碳钢", "不锈钢", "合金钢", "特殊合金"])
        vgrid.addWidget(make_lbl("材料:"), 1, 0)
        vgrid.addWidget(self.material_combo, 1, 1)
        hint_mt = QLabel("")
        vgrid.addWidget(hint_mt, 1, 2)

        self.discharge_combo = QComboBox()
        self.discharge_combo.setStyleSheet(COMBOBOX_STYLE)
        self.discharge_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.discharge_combo.addItems(["开式", "闭式", "半开式"])
        vgrid.addWidget(make_lbl("排放方式:"), 2, 0)
        vgrid.addWidget(self.discharge_combo, 2, 1)
        hint_dc = QLabel("")
        vgrid.addWidget(hint_dc, 2, 2)

        left_layout.addWidget(valve_group)

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

        # ── 详细参数表 ──
        detail_group = QGroupBox("详细参数")
        detail_group.setStyleSheet(GROUP_STYLE)
        detail_vbox = QVBoxLayout(detail_group)

        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(3)
        self.detail_table.setHorizontalHeaderLabels(["参数", "数值", "单位"])
        self.detail_table.setMaximumHeight(180)
        dh = self.detail_table.horizontalHeader()
        dh.setSectionResizeMode(QHeaderView.Stretch)
        detail_vbox.addWidget(self.detail_table)
        left_layout.addWidget(detail_group)

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

    # ──────────────────── 事件 ──────────────────────────────────
    def _on_medium_changed(self, medium):
        mapping = {
            "蒸汽": (18, 1.3),
            "空气": (29, 1.4),
            "气体": (16, 1.3),
            "液体": (18, 1.0),
            "两相流": (18, 1.3),
        }
        mw, gamma = mapping.get(medium, (18, 1.3))
        self.mw_input.setText(str(mw))
        self.gamma_input.setText(str(gamma))

    # ──────────────────── 计算 ──────────────────────────────────
    def calculate(self):
        try:
            medium = self.medium_combo.currentText()
            mw = float(self.mw_input.text() or 18)
            gamma = float(self.gamma_input.text() or 1.3)
            set_p = float(self.set_pressure_input.text() or 1.0)
            back_p = float(self.back_pressure_input.text() or 0.1)
            over_p = float(self.overpressure_input.text() or 10)
            relief_t = float(self.relief_temp_input.text() or 150)
            z = float(self.z_input.text() or 1.0)
            relief_rate = float(self.relief_rate_input.text() or 1000)
            is_fire = self.fire_combo.currentText() == "火灾工况"
            wetted_a = float(self.wetted_area_input.text() or 50)
            env_f = float(self.env_factor_input.text() or 1.0)

            set_pa = set_p * 1e6
            back_pa = back_p * 1e6
            over_frac = over_p / 100.0
            relief_pressure = set_pa * (1 + over_frac)
            relief_k = relief_t + 273.15
            relief_rate_kgs = relief_rate / 3600.0

            if is_fire:
                heat_input = 43.2 * env_f * (wetted_a ** 0.82)
                latent_heat = 300.0
                relief_rate_kgs = (heat_input / latent_heat)

            if medium in ("蒸汽", "空气", "气体", "两相流"):
                area = self._gas_area(
                    relief_rate_kgs, relief_pressure, back_pa,
                    relief_k, mw, gamma, z)
            else:
                area = self._liquid_area(
                    relief_rate_kgs, relief_pressure, back_pa)

            diameter = math.sqrt(4 * area / math.pi) * 1000  # mm

            std_diameters = [6, 8, 10, 15, 20, 25, 32, 40, 50,
                             65, 80, 100, 125, 150, 200]
            selected_d = min(std_diameters, key=lambda x: abs(x - diameter))

            # 阻塞流判断
            critical_ratio = (2 / (gamma + 1)) ** (gamma / (gamma - 1))
            actual_ratio = back_pa / relief_pressure if relief_pressure > 0 else 1
            is_choked = actual_ratio <= critical_ratio

            result = {
                "area_mm2": area * 1e6,
                "diameter_mm": diameter,
                "selected_d_mm": selected_d,
                "relief_rate_kgh": relief_rate_kgs * 3600,
                "relief_pressure_MPa": relief_pressure / 1e6,
                "is_choked": is_choked,
                "critical_ratio": critical_ratio,
                "actual_ratio": actual_ratio,
            }
            self._last_result = result
            self._last_params = {
                "medium": medium, "mw": mw, "gamma": gamma,
                "set_pressure": set_p, "back_pressure": back_p,
                "overpressure": over_p, "relief_temp": relief_t,
                "compressibility": z,
            }

            self._update_detail_table(result)
            self._display(result, medium)

            

        except ValueError as e:
            self._show_error(f"输入错误：{e}")
        except Exception as e:
            self._show_error(f"计算错误：{e}")

    # ── 气体泄放面积 (ASME VIII / API 520, SI) ──
    @staticmethod
    def _gas_area(W, P1, P2, T, M, gamma, Z):
        C = 0.03948 * math.sqrt(
            gamma * (2 / (gamma + 1)) ** ((gamma + 1) / (gamma - 1)))
        Kd = 0.65
        critical_ratio = (2 / (gamma + 1)) ** (gamma / (gamma - 1))
        ratio = P2 / P1 if P1 > 0 else 1.0

        if ratio <= critical_ratio:
            # 临界流（阻塞流）
            area = W / (C * Kd * P1 * math.sqrt(M / (T * Z)))
        else:
            # 亚临界流
            r = ratio
            F = math.sqrt(
                (gamma / (gamma - 1)) *
                (r ** (2 / gamma) - r ** ((gamma + 1) / gamma)))
            area = W / (C * Kd * P1 * F * math.sqrt(M / (T * Z)))
        return area

    # ── 液体泄放面积 (ASME VIII / API 520, SI) ──
    @staticmethod
    def _liquid_area(W, P1, P2, density=1000.0):
        Kd = 0.65
        delta_p = (P1 - P2)
        if delta_p <= 0:
            return float("inf")
        return W / (Kd * math.sqrt(2 * density * delta_p))

    # ──────────────────── 显示 ──────────────────────────────────
    def _display(self, r, medium):
        r_val = self._last_result
        params = self._last_params
        lines = [
            "=" * 50,
            "       安全阀计算结果",
            "=" * 50,
            "",
            "【输入参数】",
            f"  介质类型       : {medium}",
            f"  分子量         : {params.get('mw', '')} g/mol",
            f"  绝热指数 γ     : {params.get('gamma', '')}",
            f"  设定压力       : {params.get('set_pressure', '')} MPa",
            f"  背压           : {params.get('back_pressure', '')} MPa",
            f"  超压百分比     : {params.get('overpressure', '')} %",
            f"  泄放温度       : {params.get('relief_temp', '')} °C",
            f"  压缩因子 Z     : {params.get('compressibility', '')}",
            "",
            "【计算结果】",
            f"  ★ 所需喉径面积  : {r_val['area_mm2']:.2f} mm²",
            f"    计算喉径       : {r_val['diameter_mm']:.1f} mm",
            f"  ★ 推荐标准喉径   : {r_val['selected_d_mm']} mm",
            f"    泄放量         : {r_val['relief_rate_kgh']:.1f} kg/h",
            f"    泄放压力       : {r_val['relief_pressure_MPa']:.3f} MPa",
        ]

        if medium in ("蒸汽", "空气", "气体", "两相流"):
            lines.append(
                f"    流动状态       : "
                f"{'临界流（阻塞流）' if r_val['is_choked'] else '亚临界流'}"
            )
            lines.append(
                f"    临界压比       : {r_val['critical_ratio']:.4f}"
            )
            lines.append(
                f"    实际背压比     : {r_val['actual_ratio']:.4f}"
            )

        lines += [
            "",
            "【标准依据】",
            "  ASME BPVC Section VIII Div.1 - 压力容器",
            "  API RP 520 Part I - 炼油厂泄压装置",
            "  API Std 526 - 法兰钢制安全阀",
            "  GB/T 12241 - 安全阀一般要求",
            "",
            "【选型建议】",
            f"  1. 选择喉径不小于 {r_val['selected_d_mm']} mm 的安全阀",
            "  2. 确保安全阀额定排量 > 计算泄放量",
            "  3. 根据介质腐蚀性选择阀体材料",
        ]

        if medium in ("蒸汽", "空气", "气体", "两相流"):
            if r_val["actual_ratio"] > 0.5:
                lines.append("  4. 背压较高，建议选用平衡式安全阀")
            else:
                lines.append("  4. 背压较低，普通弹簧式即可")

        lines += [
            "  5. 符合 GB/T 12241 / API RP 520 规范要求",
            "",
            "  * 本结果为理论计算值，实际选型需由",
            "    专业工程师结合工况确认设计方案。",
            "=" * 50,
        ]
        self.result_text.setPlainText("\n".join(lines))

    def _update_detail_table(self, r):
        data = [
            ["所需喉径面积", f"{r['area_mm2']:.2f}", "mm²"],
            ["计算喉径", f"{r['diameter_mm']:.1f}", "mm"],
            ["推荐标准喉径", f"{r['selected_d_mm']}", "mm"],
            ["泄放量", f"{r['relief_rate_kgh']:.1f}", "kg/h"],
            ["泄放压力", f"{r['relief_pressure_MPa']:.3f}", "MPa"],
            ["背压", f"{self._last_params.get('back_pressure', 0):.2f}", "MPa"],
            ["背压比", f"{r['actual_ratio']*100:.1f}", "%"],
            ["超压比例", f"{self._last_params.get('overpressure', 10):.0f}", "%"],
        ]
        self.detail_table.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, val in enumerate(row):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.detail_table.setItem(i, j, item)

    def _show_error(self, msg):
        self.result_text.setPlainText(f"⚠️  错误：{msg}")

    # ──────────────────── 清空 ───────────────────────────────────
    def clear_inputs(self):
        self.medium_combo.setCurrentIndex(0)
        self.mw_input.setText("18")
        self.gamma_input.setText("1.3")
        self.set_pressure_input.setText("1.0")
        self.back_pressure_input.setText("0.1")
        self.overpressure_input.setText("10")
        self.temp_input.setText("100")
        self.relief_temp_input.setText("150")
        self.z_input.setText("1.0")
        self.relief_rate_input.setText("1000")
        self.fire_combo.setCurrentIndex(0)
        self.wetted_area_input.setText("50")
        self.env_factor_input.setText("1.0")
        self.valve_type_combo.setCurrentIndex(0)
        self.material_combo.setCurrentIndex(0)
        self.discharge_combo.setCurrentIndex(0)
        self.result_text.clear()
        self.detail_table.setRowCount(0)
        self._last_result = {}
        self._last_params = {}

    # ──────────────────── 历史数据 ──────────────────────────────
    def _get_history_data(self):
        r = self._last_result
        return {
            "inputs": {
                "介质类型": self._last_params.get("medium", ""),
                "设定压力_MPa": self._last_params.get("set_pressure", 0),
                "背压_MPa": self._last_params.get("back_pressure", 0),
                "超压_%": self._last_params.get("overpressure", 0),
            },
            "outputs": {
                "喉径面积_mm2": round(r.get("area_mm2", 0), 2),
                "推荐喉径_mm": r.get("selected_d_mm", 0),
                "泄放压力_MPa": round(r.get("relief_pressure_MPa", 0), 3),
            }
        }

    def get_project_info(self):
        return {
            "calculator": "SafetyValveCalculator",
            "name": "安全阀计算",
        }

    # ──────────────────── 报告 ───────────────────────────────────
    def generate_report(self):
        return self.result_text.toPlainText()

    def download_txt_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先计算，再下载报告。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存TXT报告", "安全阀计算报告.txt", "文本文件 (*.txt)")
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
            self, "保存PDF报告", "安全阀计算报告.pdf", "PDF文件 (*.pdf)")
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
    w = SafetyValveCalculator()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
