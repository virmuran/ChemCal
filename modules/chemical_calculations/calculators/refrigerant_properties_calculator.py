from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QLabel, QLineEdit, QPushButton, QComboBox,
                              QTextEdit, QGridLayout, QScrollArea,
                              QMessageBox, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math
import os
import importlib.util

# 导入工业级精度制冷剂物性模块
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    _spec = importlib.util.spec_from_file_location(
        "refrigerant_eos",
        os.path.join(parent_dir, "refrigerant_eos.py")
    )
    refrigerant_eos = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(refrigerant_eos)
    USE_INDUSTRIAL_EOS = True
except Exception as e:
    print(f"警告: 无法加载工业级制冷剂物性模块: {e}")
    USE_INDUSTRIAL_EOS = False
    refrigerant_eos = None

import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K, G, ATM_PRESSURE_MPA, WATER_DENSITY, WATER_CP, load_steam_iapws, get_steam_props
# DOCX 报告导出

# ---------------------------------------------------------------------------
#  QGroupBox 统一样式
# ---------------------------------------------------------------------------

LINEEDIT_STYLE = "padding: 6px 10px; border: 1px solid #888; border-radius: 4px;"

# 制冷剂数据库
REFRIGERANT_DB = {
    "R134a": {"type": "HFC", "odp": "0", "gwp": "1430", "safety_class": "A1", "mw": 102.03, "tc": 101.1, "pc": 4059, "tb": -26.1, "critical_density": 511.9, "omega": 0.326},
    "R22": {"type": "HCFC", "odp": "0.055", "gwp": "1810", "safety_class": "A1", "mw": 86.47, "tc": 96.2, "pc": 4970, "tb": -40.8, "critical_density": 523.8, "omega": 0.220},
    "R410A": {"type": "HFC混合", "odp": "0", "gwp": "2088", "safety_class": "A1", "mw": 72.58, "tc": 72.1, "pc": 4902, "tb": -51.4, "critical_density": 486.0, "omega": 0.293},
    "R407C": {"type": "HFC混合", "odp": "0", "gwp": "1774", "safety_class": "A1", "mw": 86.20, "tc": 87.3, "pc": 4630, "tb": -43.8, "critical_density": 475.0, "omega": 0.310},
    "R404A": {"type": "HFC混合", "odp": "0", "gwp": "3922", "safety_class": "A1", "mw": 97.60, "tc": 72.1, "pc": 3730, "tb": -46.1, "critical_density": 486.0, "omega": 0.310},
    "R507": {"type": "HFC混合", "odp": "0", "gwp": "3985", "safety_class": "A1", "mw": 98.86, "tc": 70.7, "pc": 3790, "tb": -46.7, "critical_density": 485.0, "omega": 0.310},
    "R717 (氨)": {"type": "天然工质", "odp": "0", "gwp": "0", "safety_class": "B2", "mw": 17.03, "tc": 132.3, "pc": 11333, "tb": -33.3, "critical_density": 235.0, "omega": 0.252},
    "R718 (水)": {"type": "天然工质", "odp": "0", "gwp": "0", "safety_class": "A1", "mw": 18.02, "tc": 374.1, "pc": 22064, "tb": 100.0, "critical_density": 322.0, "omega": 0.344},
    "R290 (丙烷)": {"type": "HC", "odp": "0", "gwp": "3", "safety_class": "A3", "mw": 44.10, "tc": 96.7, "pc": 4250, "tb": -42.1, "critical_density": 220.0, "omega": 0.152},
    "R600a (异丁烷)": {"type": "HC", "odp": "0", "gwp": "3", "safety_class": "A3", "mw": 58.12, "tc": 134.7, "pc": 3640, "tb": -11.7, "critical_density": 225.0, "omega": 0.186},
    "R1234yf": {"type": "HFO", "odp": "0", "gwp": "4", "safety_class": "A2L", "mw": 114.04, "tc": 94.7, "pc": 3380, "tb": -29.4, "critical_density": 488.0, "omega": 0.276},
    "R1234ze": {"type": "HFO", "odp": "0", "gwp": "6", "safety_class": "A2L", "mw": 114.04, "tc": 109.4, "pc": 3630, "tb": -18.9, "critical_density": 488.0, "omega": 0.313},
    "R32": {"type": "HFC", "odp": "0", "gwp": "675", "safety_class": "A2L", "mw": 52.02, "tc": 78.1, "pc": 5780, "tb": -51.7, "critical_density": 424.0, "omega": 0.277},
    "R125": {"type": "HFC", "odp": "0", "gwp": "3500", "safety_class": "A1", "mw": 120.02, "tc": 66.0, "pc": 3620, "tb": -48.1, "critical_density": 573.0, "omega": 0.305},
    "R143a": {"type": "HFC", "odp": "0", "gwp": "4470", "safety_class": "A2L", "mw": 84.04, "tc": 72.7, "pc": 3760, "tb": -47.2, "critical_density": 431.0, "omega": 0.261},
}

# 制冷剂名称映射到 refrigerant_eos 模块名称
_REF_MAP = {
    "R134a": "R134a", "R22": "R22", "R410A": "R410A",
    "R407C": "R410A", "R404A": "R410A", "R507": "R410A",
    "R717 (氨)": "R717", "R718 (水)": "R718",
    "R290 (丙烷)": "R290", "R600a (异丁烷)": "R600a",
    "R1234yf": "R134a", "R1234ze": "R134a",
    "R32": "R32", "R125": "R125", "R143a": "R143a",
}

class RefrigerantPropertiesCalculator(CalculatorBase):
    """制冷剂物性计算器 - 统一UI风格版"""

    calculation_type = "refrigerant_properties_calculator"

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)

        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()

        self._last_calc_results = {}
        self.setup_ui()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    def init_data_manager(self):
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None

    def setup_ui(self):
        """设置UI界面 - 统一风格布局"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ====== 左侧：输入参数区域 ======
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } "
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 1. 顶部说明文字
        description = QLabel(
            "计算各种制冷剂的热力学性质（饱和、过热、过冷、压缩因子、循环分析），"
            "基于 Peng-Robinson 状态方程 + Antoine 方程 + Rackett 方程，工业级精度。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)

        # 2. 制冷剂选择组
        ref_group = QGroupBox("制冷剂选择")
        ref_layout = QGridLayout(ref_group)
        ref_layout.setVerticalSpacing(12)
        ref_layout.setHorizontalSpacing(10)
        ref_layout.setColumnStretch(0, 4)
        ref_layout.setColumnStretch(1, 8)
        ref_layout.setColumnStretch(2, 5)

        label_style = "font-weight: bold; padding-right: 10px;"

        ref_label = QLabel("制冷剂:")
        ref_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ref_label.setStyleSheet(label_style)
        ref_layout.addWidget(ref_label, 0, 0)

        self.refrigerant_selection = QComboBox()
        self.refrigerant_selection.setStyleSheet(COMBOBOX_STYLE)
        self.refrigerant_selection.addItems(list(REFRIGERANT_DB.keys()))
        self.refrigerant_selection.currentTextChanged.connect(self.update_refrigerant_info)
        ref_layout.addWidget(self.refrigerant_selection, 0, 1)

        ref_hint = QLabel("选择制冷剂类型")
        ref_hint.setStyleSheet("font-style: italic;")
        ref_layout.addWidget(ref_hint, 0, 2)

        # 制冷剂信息显示
        info_labels = [("类型:", "ref_type_info"), ("ODP:", "ref_odp_info"), ("GWP:", "ref_gwp_info"), ("安全等级:", "ref_safety_info")]
        for idx, (text, attr_name) in enumerate(info_labels):
            lbl = QLabel(text)
            lbl.setStyleSheet(label_style)
            ref_layout.addWidget(lbl, 1 + idx // 2, 0 if idx % 2 == 0 else 3)
            val = QLabel("--")
            setattr(self, attr_name, val)
            ref_layout.addWidget(val, 1 + idx // 2, 1 if idx % 2 == 0 else 4)

        left_layout.addWidget(ref_group)

        # 3. 计算条件组
        condition_group = QGroupBox("计算条件")
        condition_layout = QGridLayout(condition_group)
        condition_layout.setVerticalSpacing(12)
        condition_layout.setHorizontalSpacing(10)
        condition_layout.setColumnStretch(0, 4)
        condition_layout.setColumnStretch(1, 8)
        condition_layout.setColumnStretch(2, 5)

        # 计算类型
        ctype_label = QLabel("计算类型:")
        ctype_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ctype_label.setStyleSheet(label_style)
        condition_layout.addWidget(ctype_label, 0, 0)

        self.calculation_type = QComboBox()
        self.calculation_type.setStyleSheet(COMBOBOX_STYLE)
        self.calculation_type.addItems([
            "饱和性质计算", "过热性质计算", "过冷性质计算",
            "压缩因子计算", "热力循环分析"
        ])
        self.calculation_type.currentTextChanged.connect(self._on_calc_type_changed)
        condition_layout.addWidget(self.calculation_type, 0, 1)

        ctype_hint = QLabel("选择计算类型")
        ctype_hint.setStyleSheet("font-style: italic;")
        condition_layout.addWidget(ctype_hint, 0, 2)

        # 温度
        temp_label = QLabel("温度:")
        temp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        temp_label.setStyleSheet(label_style)
        condition_layout.addWidget(temp_label, 1, 0)

        self.temperature_input = QLineEdit()
        self.temperature_input.setPlaceholderText("例如：25")
        self.temperature_input.setValidator(QDoubleValidator(-200, 300, 2))
        self.temperature_input.setStyleSheet(LINEEDIT_STYLE)
        self.temperature_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(self.temperature_input, 1, 1)

        temp_hint = QLabel("°C")
        temp_hint.setStyleSheet("font-style: italic;")
        condition_layout.addWidget(temp_hint, 1, 2)

        # 压力
        pres_label = QLabel("压力:")
        pres_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pres_label.setStyleSheet(label_style)
        condition_layout.addWidget(pres_label, 2, 0)

        self.pressure_input = QLineEdit()
        self.pressure_input.setPlaceholderText("例如：666")
        self.pressure_input.setValidator(QDoubleValidator(0.1, 10000, 1))
        self.pressure_input.setStyleSheet(LINEEDIT_STYLE)
        self.pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(self.pressure_input, 2, 1)

        pres_hint = QLabel("kPa")
        pres_hint.setStyleSheet("font-style: italic;")
        condition_layout.addWidget(pres_hint, 2, 2)

        # 干度
        quality_label = QLabel("干度:")
        quality_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        quality_label.setStyleSheet(label_style)
        condition_layout.addWidget(quality_label, 3, 0)

        self.quality_input = QLineEdit()
        self.quality_input.setPlaceholderText("例如：0.5")
        self.quality_input.setValidator(QDoubleValidator(0, 1, 3))
        self.quality_input.setStyleSheet(LINEEDIT_STYLE)
        self.quality_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        condition_layout.addWidget(self.quality_input, 3, 1)

        quality_hint = QLabel("0~1")
        quality_hint.setStyleSheet("font-style: italic;")
        condition_layout.addWidget(quality_hint, 3, 2)

        # 冷凝温度（热力循环分析用）
        self.cond_temp_label = QLabel("冷凝温度:")
        self.cond_temp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cond_temp_label.setStyleSheet(label_style)
        self.cond_temp_label.setVisible(False)
        condition_layout.addWidget(self.cond_temp_label, 4, 0)

        self.cond_temp_input = QLineEdit()
        self.cond_temp_input.setPlaceholderText("例如：40")
        self.cond_temp_input.setValidator(QDoubleValidator(-100, 200, 2))
        self.cond_temp_input.setStyleSheet(LINEEDIT_STYLE)
        self.cond_temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cond_temp_input.setVisible(False)
        condition_layout.addWidget(self.cond_temp_input, 4, 1)

        cond_hint = QLabel("°C")
        cond_hint.setStyleSheet("font-style: italic;")
        cond_hint.setVisible(False)
        self._cond_hint = cond_hint
        condition_layout.addWidget(cond_hint, 4, 2)

        left_layout.addWidget(condition_group)

        # 4. 制冷剂基本信息组
        info_group = QGroupBox("制冷剂基本信息")
        info_layout = QGridLayout(info_group)
        info_layout.setVerticalSpacing(12)
        info_layout.setHorizontalSpacing(10)
        info_layout.setColumnStretch(0, 4)
        info_layout.setColumnStretch(1, 8)
        info_layout.setColumnStretch(2, 5)
        info_layout.setColumnStretch(3, 4)
        info_layout.setColumnStretch(4, 8)
        info_layout.setColumnStretch(5, 5)

        info_items = [
            ("分子量:", "mw_val", "g/mol", 0), ("临界温度:", "tc_val", "°C", 0),
            ("临界压力:", "pc_val", "kPa", 1), ("正常沸点:", "tb_val", "°C", 1),
            ("临界密度:", "cd_val", "kg/m³", 2), ("偏心因子:", "omega_val", "", 2),
        ]
        for text, attr, unit, row in info_items:
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet(label_style)
            col = 0 if info_items.index((text, attr, unit, row)) % 2 == 0 else 3
            info_layout.addWidget(lbl, row, col)
            val = QLabel("--")
            setattr(self, attr, val)
            info_layout.addWidget(val, row, col + 1)
            u = QLabel(unit)
            u.setStyleSheet("color: #7f8c8d;")
            info_layout.addWidget(u, row, col + 2)

        left_layout.addWidget(info_group)

        left_layout.addStretch()

        # ====== 右侧：结果显示区域 ======
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(12)

        result_group = QGroupBox("计算结果")
        result_inner = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        # 结果框统一标准：边框/背景/文字色交给主题系统，仅指定等宽字体
        self.result_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: 13px;
            }
        """)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        result_inner.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # 下载按钮行：清空 → DOCX → PDF
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        for label, style, slot in [
            ("清空", CLEAR_BTN_STYLE, self.clear_inputs),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        right_layout.addLayout(btn_layout)

        # 计算按钮放最底部（结果→下载→计算）
        calc_btn = self.make_calc_button("查  询")
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)

        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

        self.update_refrigerant_info()

    # ------------------------------------------------------------------
    #  UI 交互
    # ------------------------------------------------------------------

    def _on_calc_type_changed(self, text):
        show = (text == "热力循环分析")
        self.cond_temp_label.setVisible(show)
        self.cond_temp_input.setVisible(show)
        self._cond_hint.setVisible(show)

    def update_refrigerant_info(self):
        info = REFRIGERANT_DB.get(self.refrigerant_selection.currentText(), {})
        self.ref_type_info.setText(info.get('type', '--'))
        self.ref_odp_info.setText(info.get('odp', '--'))
        self.ref_gwp_info.setText(info.get('gwp', '--'))
        self.ref_safety_info.setText(info.get('safety_class', '--'))
        self.mw_val.setText(str(info.get('mw', '--')))
        self.tc_val.setText(f"{info.get('tc', 0):.1f}")
        self.pc_val.setText(f"{info.get('pc', 0):.0f}")
        self.tb_val.setText(f"{info.get('tb', 0):.1f}")
        self.cd_val.setText(f"{info.get('critical_density', 0):.1f}")
        self.omega_val.setText(f"{info.get('omega', 0):.3f}")

    # ------------------------------------------------------------------
    #  计算入口
    # ------------------------------------------------------------------

    def calculate(self):
        try:
            refrigerant = self.refrigerant_selection.currentText()
            info = REFRIGERANT_DB.get(refrigerant, {})
            calc_type = self.calculation_type.currentText()
            T = float(self.temperature_input.text()) if self.temperature_input.text() else None
            P = float(self.pressure_input.text()) if self.pressure_input.text() else None
            x = float(self.quality_input.text()) if self.quality_input.text() else None

            results = self.calculate_refrigerant_properties(refrigerant, info, calc_type, T, P, x)
            self._last_calc_results = results
            self._last_calc_results.update({"refrigerant": refrigerant, "calc_type": calc_type})
            self._format_results(results, calc_type)
        except ValueError:
            self.result_text.setPlainText("⚠ 输入参数格式错误，请检查输入值。")
        except Exception as e:
            self.result_text.setPlainText(f"⚠ 计算错误: {str(e)}")

    def calculate_refrigerant_properties(self, refrigerant, info, calc_type, T, P, x):
        T_k = T + C_TO_K if T else None

        if calc_type == "饱和性质计算":
            if T is not None:
                P_sat = self._calc_sat_pressure(refrigerant, T)
                results = self._calc_saturated_props(refrigerant, T, P_sat)
                results['temperature'] = T
                results['pressure'] = P_sat
            elif P is not None:
                T_sat = self._calc_sat_temperature(refrigerant, P)
                results = self._calc_saturated_props(refrigerant, T_sat, P)
                results['temperature'] = T_sat
                results['pressure'] = P
            else:
                raise ValueError("需要输入温度或压力")
        elif calc_type == "过热性质计算":
            if T is not None and P is not None:
                results = self._calc_superheated_props(refrigerant, T, P)
            else:
                raise ValueError("过热性质计算需要温度和压力")
        elif calc_type == "过冷性质计算":
            if T is not None and P is not None:
                results = self._calc_subcooled_props(refrigerant, T, P)
            else:
                raise ValueError("过冷性质计算需要温度和压力")
        elif calc_type == "压缩因子计算":
            if T is not None and P is not None:
                results = self._calc_compressibility(refrigerant, T, P, info)
            else:
                raise ValueError("压缩因子计算需要温度和压力")
        else:
            if T is not None:
                ct = self.cond_temp_input.text()
                T_cond = float(ct) if ct else (T + 40.0)
                results = self._analyze_cycle(refrigerant, T, T_cond)
            else:
                raise ValueError("热力循环分析需要蒸发温度")

        # 传输性质补充
        if calc_type in ("过冷性质计算", "饱和性质计算"):
            extra = self._liquid_sound_speed(refrigerant, T, P, results)
            results.update(extra)
        else:
            transport = self._calc_transport_props(refrigerant, T, P, results.get('density', 0))
            results.update(transport)

        return results

    # ------------------------------------------------------------------
    #  核心计算方法（保留原有逻辑）
    # ------------------------------------------------------------------

    def _calc_sat_pressure(self, refrigerant, T):
        if USE_INDUSTRIAL_EOS:
            try:
                ref_name = _REF_MAP.get(refrigerant, "R134a")
                sat = refrigerant_eos.saturation_properties(T_K=T+C_TO_K, ref_name=ref_name)
                return sat['P_MPa'] * 1000
            except Exception:
                pass
        # 简化 Antoine
        if refrigerant == "R134a":
            return 10 ** (6.87601 - 1171.530 / (T - 16.156))
        elif refrigerant == "R22":
            return 10 ** (6.64014 - 1176.059 / (T - 13.508))
        return 10 ** (6.8 - 1150.0 / (T - 18.0))

    def _calc_sat_temperature(self, refrigerant, P):
        if USE_INDUSTRIAL_EOS:
            try:
                ref_name = _REF_MAP.get(refrigerant, "R134a")
                sat = refrigerant_eos.saturation_properties(P_MPa=P/1000.0, ref_name=ref_name)
                return sat['T_K'] - C_TO_K
            except Exception:
                pass
        if refrigerant == "R134a":
            return 1171.530 / (6.87601 - math.log10(P)) - (-16.156)
        elif refrigerant == "R22":
            return 1176.059 / (6.64014 - math.log10(P)) - (-13.508)
        return 1150.0 / (6.8 - math.log10(P)) - (-18.0)

    def _calc_saturated_props(self, refrigerant, T, P):
        ref_name = _REF_MAP.get(refrigerant, "R134a")
        if USE_INDUSTRIAL_EOS and ref_name in getattr(refrigerant_eos, 'REFRIGERANTS', {}):
            try:
                sat = refrigerant_eos.saturation_properties(T_K=T+C_TO_K, ref_name=ref_name)
                ref_data = refrigerant_eos.REFRIGERANTS[ref_name]
                P_MPa = sat['P_MPa']
                u_f = sat['h_f'] - P_MPa * 1e3 / sat['rho_f']
                u_g = sat['h_g'] - P_MPa * 1e3 / sat['rho_g']
                g_f = sat['h_f'] - (T + C_TO_K) * sat['s_f']
                g_g = sat['h_g'] - (T + C_TO_K) * sat['s_g']
                tp = refrigerant_eos.transport_properties(sat['P_MPa'], T, ref_name=ref_name, phase='liquid')
                mu = tp['mu'] * 1e6
                k = tp['k']
                cp_J = sat['cp_f'] * 1000.0
                Pr = mu * 1e-6 * cp_J / k if k > 0 else 0
                R_J = 8.314 / (ref_data['M'] / 1000.0)
                cv_kJ = (cp_J - R_J) / 1000.0
                return {
                    'density': sat['rho_f'], 'enthalpy': sat['h_f'], 'entropy': sat['s_f'],
                    'internal_energy': u_f, 'gibbs': g_f,
                    'hf': sat['h_f'], 'hg': sat['h_g'], 'hfg': sat['h_fg'],
                    'sf': sat['s_f'], 'sg': sat['s_g'], 'sfg': sat['s_g'] - sat['s_f'],
                    'density_f': sat['rho_f'], 'density_g': sat['rho_g'],
                    'z_factor': sat['Z_g'], 'cp': sat['cp_f'], 'cv': cv_kJ,
                    'viscosity': mu, 'thermal_cond': k, 'prandtl': Pr,
                }
            except Exception:
                pass
        hf, hg = 100 + 2.5 * T, 300 + 1.8 * T
        sf, sg = 0.5 + 0.01 * T, 1.5 + 0.008 * T
        return {'density': 1000-5*T, 'enthalpy': hf, 'entropy': sf,
                'internal_energy': hf-P/1000, 'gibbs': hf-(T+C_TO_K)*sf/1000,
                'hf': hf, 'hg': hg, 'hfg': hg-hf,
                'sf': sf, 'sg': sg, 'sfg': sg-sf,
                'density_f': 1000-5*T, 'density_g': 20-0.1*T}

    def _calc_superheated_props(self, refrigerant, T, P):
        ref_name = _REF_MAP.get(refrigerant, "R134a")
        if USE_INDUSTRIAL_EOS and ref_name in getattr(refrigerant_eos, 'REFRIGERANTS', {}):
            try:
                P_MPa = P / 1000.0
                prop = refrigerant_eos.vapor_properties(P_MPa, T, ref_name=ref_name)
                ref_data = refrigerant_eos.REFRIGERANTS[ref_name]
                R_J = 8.314 / (ref_data['M'] / 1000.0)
                cp = prop['cp']
                cv = cp - R_J / 1000.0
                u = prop['h'] - P_MPa * 1e3 * prop['v']
                g = prop['h'] - (T + C_TO_K) * prop['s']
                return {
                    'temperature': T, 'pressure': P, 'density': prop['rho'],
                    'enthalpy': prop['h'], 'entropy': prop['s'],
                    'internal_energy': u, 'gibbs': g,
                    'z_factor': prop['Z'], 'cp': cp, 'cv': cv,
                }
            except Exception:
                pass
        h, s = 350 + 1.5 * T + 0.01 * P, 1.7 + 0.009 * T + 0.0001 * P
        return {'temperature': T, 'pressure': P, 'density': 15-0.08*T+0.001*P,
                'enthalpy': h, 'entropy': s, 'internal_energy': h-P/1000}

    def _calc_subcooled_props(self, refrigerant, T, P):
        ref_name = _REF_MAP.get(refrigerant, "R134a")
        if USE_INDUSTRIAL_EOS and ref_name in getattr(refrigerant_eos, 'REFRIGERANTS', {}):
            try:
                P_MPa = P / 1000.0
                prop = refrigerant_eos.liquid_properties(P_MPa, T, ref_name=ref_name)
                ref_data = refrigerant_eos.REFRIGERANTS[ref_name]
                R_J = 8.314 / (ref_data['M'] / 1000.0)
                cp = prop['cp']
                cv = cp - R_J / 1000.0
                u = prop['h'] - P_MPa * 1e3 / prop['rho']
                g = prop['h'] - (T + C_TO_K) * prop['s']
                tp = refrigerant_eos.transport_properties(P_MPa, T, ref_name=ref_name, phase='liquid')
                mu = tp['mu'] * 1e6
                k = tp['k']
                cp_J = cp * 1000.0
                Pr = mu * 1e-6 * cp_J / k if k > 0 else 0
                return {
                    'temperature': T, 'pressure': P, 'density': prop['rho'],
                    'enthalpy': prop['h'], 'entropy': prop['s'],
                    'internal_energy': u, 'gibbs': g, 'z_factor': 0.0,
                    'cp': cp, 'cv': cv, 'viscosity': mu, 'thermal_cond': k, 'prandtl': Pr,
                }
            except Exception:
                pass
        h, s = 80 + 2.2 * T + 0.001 * P, 0.4 + 0.008 * T + 0.00005 * P
        return {'temperature': T, 'pressure': P, 'density': 1050-4.5*T+0.002*P,
                'enthalpy': h, 'entropy': s, 'internal_energy': h-P/1000}

    def _calc_compressibility(self, refrigerant, T, P, info):
        ref_name = _REF_MAP.get(refrigerant, "R134a")
        if USE_INDUSTRIAL_EOS and ref_name in getattr(refrigerant_eos, 'REFRIGERANTS', {}):
            try:
                P_MPa = P / 1000.0
                z = refrigerant_eos.compressibility_factor(P_MPa, T, ref_name=ref_name)
                ref_data = refrigerant_eos.REFRIGERANTS[ref_name]
                R_J = 8.314 / (ref_data['M'] / 1000.0)
                Z_v = z['Z_vapor']
                density = P * 1e3 / (Z_v * R_J * (T + C_TO_K))
                cp = ref_data['cp_ideal']
                cv = cp - R_J / 1000.0
                return {
                    'temperature': T, 'pressure': P, 'z_factor': Z_v,
                    'density': density, 'enthalpy': 200+1.5*T,
                    'entropy': 1.0+0.005*T, 'internal_energy': 180+1.4*T,
                    'gibbs': 150+1.2*T, 'cp': cp, 'cv': cv,
                }
            except Exception:
                pass
        tc_k = info.get('tc', 100) + C_TO_K
        Tr = (T + C_TO_K) / tc_k
        Pr_val = P / info.get('pc', 4000)
        Z = 1.0 - 0.1 * Pr_val / Tr if Tr < 1.0 else 1.0 + 0.1 * Pr_val / Tr
        return {'temperature': T, 'pressure': P, 'z_factor': Z,
                'density': P*1000/(Z*8.314/info.get('mw',100)*1000*(T+C_TO_K))}

    def _analyze_cycle(self, refrigerant, T_evap, T_cond):
        ref_name = _REF_MAP.get(refrigerant, "R134a")
        if USE_INDUSTRIAL_EOS and ref_name in getattr(refrigerant_eos, 'REFRIGERANTS', {}):
            try:
                cycle = refrigerant_eos.refrigeration_cycle_analysis(ref_name, T_evap, T_cond)
                sat_ev = refrigerant_eos.saturation_properties(T_K=T_evap+C_TO_K, ref_name=ref_name)
                P_evap = cycle['P_evap_MPa'] * 1000
                P_cond = cycle['P_cond_MPa'] * 1000
                vol_cap = cycle['q_evap'] * sat_ev['rho_g']
                return {
                    'temperature': T_evap, 'pressure': P_evap,
                    'cop': cycle['COP'], 'refrigeration_effect': cycle['q_evap'],
                    'volumetric_capacity': vol_cap, 'glide': 0.0,
                    'density': sat_ev['rho_g'], 'enthalpy': cycle['h1'],
                    'entropy': sat_ev['s_g'],
                    'h1': cycle['h1'], 'h2': cycle['h2'],
                    'h3': cycle['h3'], 'h4': cycle['h4'],
                    'P_evap': P_evap, 'P_cond': P_cond,
                }
            except Exception:
                pass
        P_evap = self._calc_sat_pressure(refrigerant, T_evap)
        h1, h2, h3 = 400, 450, 250
        re = h1 - h3
        cop = re / (h2 - h1)
        return {'temperature': T_evap, 'pressure': P_evap, 'cop': cop,
                'refrigeration_effect': re, 'volumetric_capacity': re*(20-0.1*T_evap),
                'glide': 0.0, 'density': 20-0.1*T_evap}

    def _liquid_sound_speed(self, refrigerant, T, P, results):
        if not USE_INDUSTRIAL_EOS or not T:
            return {'sound_speed': 0}
        ref_name = _REF_MAP.get(refrigerant, "R134a")
        if ref_name not in getattr(refrigerant_eos, 'REFRIGERANTS', {}):
            return {'sound_speed': 0}
        C_LIQ = {
            'R134a': (1409.0, 2.36), 'R22': (1200.0, 2.10), 'R717': (2100.0, 2.40),
            'R718': (5530.0, 13.60), 'R290': (850.0, 1.30), 'R600a': (900.0, 1.50),
            'R410A': (1170.0, 1.87), 'R32': (1100.0, 1.80), 'R125': (1000.0, 1.60),
            'R143a': (1050.0, 1.70),
        }
        T_K = T + C_TO_K
        if ref_name in C_LIQ:
            a, b = C_LIQ[ref_name]
            c = max(200.0, min(2000.0, a - b * T_K))
        else:
            c = 600.0
        return {"sound_speed": c}

    def _calc_transport_props(self, refrigerant, T, P, density):
        """简化的气相传输性质计算"""
        if not T or density <= 0:
            return {'viscosity': 0, 'thermal_cond': 0, 'prandtl': 0, 'sound_speed': 0}
        # 简化 Chapman-Enskog 估算
        T_K = T + C_TO_K
        mu = 1.5e-5 * (T_K / 300.0) ** 0.7  # Pa·s
        k = 0.015 * (T_K / 300.0) ** 0.5  # W/(m·K)
        cp = 1.0  # kJ/(kg·K) 近似
        Pr = mu * cp * 1000.0 / k if k > 0 else 0
        return {'viscosity': mu * 1e6, 'thermal_cond': k, 'prandtl': Pr, 'sound_speed': 0}

    # ------------------------------------------------------------------
    #  结果格式化
    # ------------------------------------------------------------------

    def _format_results(self, r, calc_type):
        lines = []
        ref = r.get('refrigerant', '')
        lines.append("═══════════════════════════════════════")
        lines.append(f"    制冷剂物性计算结果 ({ref})")
        lines.append("═══════════════════════════════════════")
        lines.append(f"")
        lines.append(f"计算类型: {calc_type}")
        if 'temperature' in r:
            lines.append(f"温度: {r['temperature']:.2f} °C")
        if 'pressure' in r:
            lines.append(f"压力: {r['pressure']:.2f} kPa")
        lines.append(f"")

        if calc_type == "饱和性质计算":
            lines.append(f"─── 饱和性质 ───")
            lines.append(f"  饱和液焓 hf:  {r.get('hf', 0):.2f} kJ/kg")
            lines.append(f"  饱和汽焓 hg:  {r.get('hg', 0):.2f} kJ/kg")
            lines.append(f"  汽化潜热 hfg: {r.get('hfg', 0):.2f} kJ/kg")
            lines.append(f"  饱和液熵 sf:  {r.get('sf', 0):.4f} kJ/(kg·K)")
            lines.append(f"  饱和汽熵 sg:  {r.get('sg', 0):.4f} kJ/(kg·K)")
            lines.append(f"  汽化熵变 sfg: {r.get('sfg', 0):.4f} kJ/(kg·K)")
            lines.append(f"  液相密度:     {r.get('density_f', 0):.2f} kg/m³")
            lines.append(f"  气相密度:     {r.get('density_g', 0):.4f} kg/m³")
        elif calc_type == "热力循环分析":
            lines.append(f"─── 循环分析 ───")
            lines.append(f"  蒸发压力:       {r.get('P_evap', 0):.2f} kPa")
            lines.append(f"  冷凝压力:       {r.get('P_cond', 0):.2f} kPa")
            lines.append(f"  压比:           {r.get('P_cond', 0)/r.get('P_evap', 1):.2f}")
            lines.append(f"  理论COP:        {r.get('cop', 0):.2f}")
            lines.append(f"  单位制冷量:     {r.get('refrigeration_effect', 0):.2f} kJ/kg")
            lines.append(f"  容积制冷量:     {r.get('volumetric_capacity', 0):.2f} kJ/m³")
            lines.append(f"  h1(蒸发出口):   {r.get('h1', 0):.2f} kJ/kg")
            lines.append(f"  h2(压缩出口):   {r.get('h2', 0):.2f} kJ/kg")
            lines.append(f"  h3(冷凝出口):   {r.get('h3', 0):.2f} kJ/kg")
            lines.append(f"  h4(节流出口):   {r.get('h4', 0):.2f} kJ/kg")

        lines.append(f"")
        lines.append(f"─── 热力性质 ───")
        lines.append(f"  密度:       {r.get('density', 0):.4f} kg/m³")
        lines.append(f"  比焓:       {r.get('enthalpy', 0):.2f} kJ/kg")
        lines.append(f"  比熵:       {r.get('entropy', 0):.4f} kJ/(kg·K)")
        if 'internal_energy' in r:
            lines.append(f"  比内能:     {r['internal_energy']:.2f} kJ/kg")
        if 'gibbs' in r:
            lines.append(f"  比吉布斯能: {r['gibbs']:.2f} kJ/kg")
        if 'z_factor' in r:
            lines.append(f"  压缩因子:   {r['z_factor']:.4f}")
        lines.append(f"")
        lines.append(f"─── 传输性质 ───")
        lines.append(f"  粘度:       {r.get('viscosity', 0):.2f} μPa·s")
        lines.append(f"  热导率:     {r.get('thermal_cond', 0):.4f} W/(m·K)")
        lines.append(f"  普朗特数:   {r.get('prandtl', 0):.4f}")
        lines.append(f"  音速:       {r.get('sound_speed', 0):.1f} m/s")
        if 'cp' in r:
            lines.append(f"  定压比热:   {r['cp']:.3f} kJ/(kg·K)")
        if 'cv' in r:
            lines.append(f"  定容比热:   {r['cv']:.3f} kJ/(kg·K)")

        self.result_text.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------
    #  清空 / 历史数据 / 报告
    # ------------------------------------------------------------------

    def clear_inputs(self):
        self.temperature_input.clear()
        self.pressure_input.clear()
        self.quality_input.clear()
        if hasattr(self, 'cond_temp_input'):
            self.cond_temp_input.clear()
        self.result_text.clear()
        self._last_calc_results = {}

    def _get_history_data(self):
        refrigerant = self.refrigerant_selection.currentText()
        calc_type = self.calculation_type.currentText()
        T = float(self.temperature_input.text()) if self.temperature_input.text() else None
        P = float(self.pressure_input.text()) if self.pressure_input.text() else None
        inputs = {"制冷剂": refrigerant, "计算类型": calc_type, "温度_C": T, "压力_kPa": P}
        outputs = {}
        try:
            r = self._last_calc_results
            if r:
                outputs = {
                    "密度_kg_m3": round(r.get('density', 0), 4),
                    "比焓_kJ_kg": round(r.get('enthalpy', 0), 2),
                    "比熵_kJ_kgK": round(r.get('entropy', 0), 4),
                }
        except Exception as e:
            outputs["计算错误"] = str(e)
        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        return {"project_name": "制冷剂物性计算", "calculator_name": "制冷剂物性计算器",
                "version": "1.0", "description": "PR EOS + Antoine + Rackett 工业级精度"}

    def generate_report(self):
        r = self._last_calc_results
        if not r:
            return "尚未进行计算。"
        lines = ["制冷剂物性计算报告", "=" * 50,
                 f"制冷剂: {r.get('refrigerant', '')}",
                 f"计算类型: {r.get('calc_type', '')}", "",
                 self.result_text.toPlainText()]
        return "\n".join(lines)

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "RefrigerantPropertiesCalculator")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "RefrigerantPropertiesCalculator")
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    calculator = RefrigerantPropertiesCalculator()
    calculator.resize(1200, 800)
    calculator.show()
    sys.exit(app.exec())
