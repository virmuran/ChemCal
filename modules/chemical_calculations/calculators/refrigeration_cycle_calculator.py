"""
制冷循环计算器 — 计算蒸汽压缩制冷循环的性能参数（制冷量、压缩功、COP 等）

支持理想循环（无过冷过热）与实际循环（含过冷过热）。
优先使用 refrigerant_eos 模块（PR EOS 工业级精度），缺失时回退简化计算。
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox,
    QScrollArea, QButtonGroup, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
import math
import os
from datetime import datetime

# 导入工业级精度制冷剂物性模块
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "refrigerant_eos",
        os.path.join(parent_dir, "refrigerant_eos.py")
    )
    _refrigerant_eos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_refrigerant_eos)

    USE_INDUSTRIAL_CYCLE = True
    print("成功加载工业级制冷循环计算模块 (refrigerant_eos)")
except Exception as e:
    print(f"警告: 无法加载工业级制冷循环模块: {e}")
    print("将使用简化计算方法")
    USE_INDUSTRIAL_CYCLE = False
    _refrigerant_eos = None

from app_styles import (COMBOBOX_STYLE, SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K
from utils.docx_utils import ReportExporter


class RefrigerationCycleCalculator(CalculatorBase):
    """制冷循环计算器"""
    calculation_type = "refrigeration_cycle_calculator"

    def __init__(self, parent=None, data_manager=None):
        """初始化制冷循环计算器

        Args:
            parent: 父窗口
            data_manager: 数据管理器，用于保存历史记录
        """
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_result = ""
        self._last_params = {}
        self.setup_ui()
        self.setup_refrigerant_data()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None

    def setup_ui(self):
        """设置制冷循环计算UI"""
        # 创建主布局
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ========== 左侧输入区 ==========
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(SCROLL_AREA_STYLE)
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 顶部说明文字
        description = QLabel(
            "计算蒸汽压缩制冷循环的性能参数，包括制冷量、压缩功、COP等。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)

        # ========== 循环类型选择组 ==========
        cycle_group = CalculatorBase.make_group_box("循环类型")
        cycle_layout = QHBoxLayout(cycle_group)
        cycle_layout.setSpacing(10)

        self.cycle_button_group = QButtonGroup(self)

        cycles = [
            ("理想循环", "无过冷过热"),
            ("实际循环", "包含过冷过热")
        ]

        for i, (cycle_name, tooltip) in enumerate(cycles):
            btn = CalculatorBase.make_mode_button(cycle_name, tooltip)
            self.cycle_button_group.addButton(btn, i)
            cycle_layout.addWidget(btn)

        self.cycle_button_group.button(0).setChecked(True)
        self.cycle_button_group.buttonClicked.connect(self.on_cycle_type_changed)

        left_layout.addWidget(cycle_group)

        # ========== 输入参数组 ==========
        input_group = CalculatorBase.make_group_box("输入参数")

        input_layout = QGridLayout(input_group)
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)

        row = 0

        def lbl(text):
            w = QLabel(text)
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            w.setStyleSheet(INPUT_LABEL_STYLE)
            input_layout.addWidget(w, row, 0)
            return w

        def hint(text):
            w = QLabel(text)
            w.setStyleSheet("font-style: italic;")
            input_layout.addWidget(w, row, 2)
            return w

        # 制冷剂选择
        lbl("制冷剂:")
        self.refrigerant_combo = QComboBox()
        self.refrigerant_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_refrigerant_options()
        self.refrigerant_combo.currentTextChanged.connect(self.on_refrigerant_changed)
        input_layout.addWidget(self.refrigerant_combo, row, 1)
        hint("选择循环工质")

        row += 1

        # 蒸发温度
        lbl("蒸发温度 (°C):")
        self.evap_temp_input = QLineEdit()
        self.evap_temp_input.setPlaceholderText("例如: -10")
        self.evap_temp_input.setValidator(QDoubleValidator(-100.0, 100.0, 2))
        self.evap_temp_input.setText("-10")
        input_layout.addWidget(self.evap_temp_input, row, 1)
        hint("制冷剂蒸发温度")

        row += 1

        # 冷凝温度
        lbl("冷凝温度 (°C):")
        self.cond_temp_input = QLineEdit()
        self.cond_temp_input.setPlaceholderText("例如: 40")
        self.cond_temp_input.setValidator(QDoubleValidator(-50.0, 100.0, 2))
        self.cond_temp_input.setText("40")
        input_layout.addWidget(self.cond_temp_input, row, 1)
        hint("制冷剂冷凝温度")

        row += 1

        # 过冷度
        self.subcool_label = lbl("过冷度 (K):")
        self.subcool_input = QLineEdit()
        self.subcool_input.setPlaceholderText("例如: 5")
        self.subcool_input.setValidator(QDoubleValidator(0.0, 50.0, 2))
        self.subcool_input.setText("5")
        input_layout.addWidget(self.subcool_input, row, 1)
        self.subcool_hint = hint("仅实际循环")

        row += 1

        # 过热度
        self.superheat_label = lbl("过热度 (K):")
        self.superheat_input = QLineEdit()
        self.superheat_input.setPlaceholderText("例如: 5")
        self.superheat_input.setValidator(QDoubleValidator(0.0, 50.0, 2))
        self.superheat_input.setText("5")
        input_layout.addWidget(self.superheat_input, row, 1)
        self.superheat_hint = hint("仅实际循环")

        row += 1

        # 质量流量
        lbl("质量流量 (kg/s):")
        self.mass_flow_input = QLineEdit()
        self.mass_flow_input.setPlaceholderText("例如: 0.1")
        self.mass_flow_input.setValidator(QDoubleValidator(0.001, 100.0, 6))
        self.mass_flow_input.setText("0.1")
        input_layout.addWidget(self.mass_flow_input, row, 1)
        hint("循环制冷剂流量")

        row += 1

        # 压缩机效率
        lbl("压缩机效率 (%):")
        self.comp_eff_input = QLineEdit()
        self.comp_eff_input.setPlaceholderText("例如: 80")
        self.comp_eff_input.setValidator(QDoubleValidator(10.0, 100.0, 2))
        self.comp_eff_input.setText("80")
        input_layout.addWidget(self.comp_eff_input, row, 1)
        hint("等熵效率")

        left_layout.addWidget(input_group)

        left_layout.addStretch()

        # ========== 右侧结果区 ==========
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        # 结果显示组
        result_group = CalculatorBase.make_group_box("计算结果")
        result_layout = QVBoxLayout(result_group)

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
        result_layout.addWidget(self.result_text)

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

        # ========== 将左右两部分添加到主布局 ==========
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

        # 初始状态设置
        self.on_cycle_type_changed()

    def setup_refrigerant_data(self):
        """设置制冷剂物性数据"""
        self.refrigerant_data = {
            "R134a": {
                "critical_temp": 101.1,  # °C
                "critical_pressure": 4059,  # kPa
                "molecular_weight": 102.03,  # g/mol
                "ODP": 0,  # 臭氧破坏潜能
                "GWP": 1430  # 全球变暖潜能
            },
            "R22": {
                "critical_temp": 96.2,
                "critical_pressure": 4970,
                "molecular_weight": 86.47,
                "ODP": 0.055,
                "GWP": 1810
            },
            "R410A": {
                "critical_temp": 72.1,
                "critical_pressure": 4900,
                "molecular_weight": 72.58,
                "ODP": 0,
                "GWP": 2088
            },
            "R32": {
                "critical_temp": 78.4,
                "critical_pressure": 5780,
                "molecular_weight": 52.02,
                "ODP": 0,
                "GWP": 675
            },
            "R717 (氨)": {
                "critical_temp": 132.3,
                "critical_pressure": 11280,
                "molecular_weight": 17.03,
                "ODP": 0,
                "GWP": 0
            },
            "R744 (CO₂)": {
                "critical_temp": 31.1,
                "critical_pressure": 7380,
                "molecular_weight": 44.01,
                "ODP": 0,
                "GWP": 1
            }
        }

    def setup_refrigerant_options(self):
        """设置制冷剂选项"""
        refrigerants = [
            "R134a - HFC制冷剂，环保型",
            "R22 - HCFC制冷剂，逐步淘汰",
            "R410A - HFC混合制冷剂，空调常用",
            "R32 - HFC制冷剂，低GWP",
            "R717 (氨) - 天然制冷剂，高效",
            "R744 (CO₂) - 天然制冷剂，环保"
        ]
        self.refrigerant_combo.addItems(refrigerants)

    def on_refrigerant_changed(self, text):
        """处理制冷剂选择变化"""
        pass

    def on_cycle_type_changed(self):
        """处理循环类型变化"""
        is_actual = self.cycle_button_group.checkedButton().text() == "实际循环"

        # 对于理想循环，隐藏过冷过热输入
        self.subcool_label.setVisible(is_actual)
        self.subcool_input.setVisible(is_actual)
        self.subcool_hint.setVisible(is_actual)
        self.superheat_label.setVisible(is_actual)
        self.superheat_input.setVisible(is_actual)
        self.superheat_hint.setVisible(is_actual)

    def calculate_saturation_pressure(self, refrigerant, temperature):
        """计算饱和压力（简化计算）

        Args:
            refrigerant: 制冷剂名称
            temperature: 温度（°C）

        Returns:
            饱和压力（kPa）
        """
        # 使用Antoine方程简化计算
        if refrigerant == "R134a":
            A, B, C = 6.9094, 1169.0, 224.0
        elif refrigerant == "R22":
            A, B, C = 6.9399, 1117.0, 231.0
        elif refrigerant == "R410A":
            A, B, C = 6.9454, 1125.0, 232.0
        elif refrigerant == "R32":
            A, B, C = 6.8935, 1083.0, 236.0
        elif refrigerant == "R717 (氨)":
            A, B, C = 7.3605, 926.0, 240.0
        elif refrigerant == "R744 (CO₂)":
            A, B, C = 6.8123, 1301.0, 273.0
        else:
            A, B, C = 6.9094, 1169.0, 224.0  # 默认R134a

        T = temperature + C_TO_K  # 转换为K
        P_sat = math.exp(A - B/(T - C)) * 100  # kPa
        return P_sat

    def calculate_enthalpy(self, refrigerant, temperature, pressure, is_vapor=True):
        """计算焓值（简化计算）

        Args:
            refrigerant: 制冷剂名称
            temperature: 温度（°C）
            pressure: 压力（kPa）
            is_vapor: 是否为气相

        Returns:
            焓值（kJ/kg）
        """
        # 简化计算，实际应用中应使用详细的物性表或方程
        if refrigerant == "R134a":
            if is_vapor:
                # 蒸汽焓值
                return 250 + 1.8 * temperature  # kJ/kg
            else:
                # 液体焓值
                return 100 + 1.5 * temperature  # kJ/kg
        else:
            # 其他制冷剂的简化计算
            if is_vapor:
                return 250 + 1.8 * temperature
            else:
                return 100 + 1.5 * temperature

    def calculate_entropy(self, refrigerant, temperature, pressure, is_vapor=True):
        """计算熵值（简化计算）

        Args:
            refrigerant: 制冷剂名称
            temperature: 温度（°C）
            pressure: 压力（kPa）
            is_vapor: 是否为气相

        Returns:
            熵值（kJ/kg·K）
        """
        if refrigerant == "R134a":
            if is_vapor:
                return 0.9 + 0.01 * temperature  # kJ/kg·K
            else:
                return 0.4 + 0.005 * temperature  # kJ/kg·K
        else:
            if is_vapor:
                return 0.9 + 0.01 * temperature
            else:
                return 0.4 + 0.005 * temperature

    def calculate(self):
        """计算制冷循环 - 统一接口方法

        此方法为统一UI规范要求的接口，调用实际的计算逻辑
        """
        try:
            # 获取输入值
            cycle_type = self.cycle_button_group.checkedButton().text()
            refrigerant_text = self.refrigerant_combo.currentText()
            refrigerant = refrigerant_text.split(" - ")[0]

            evap_temp = float(self.evap_temp_input.text())
            cond_temp = float(self.cond_temp_input.text())
            mass_flow = float(self.mass_flow_input.text())
            comp_efficiency = float(self.comp_eff_input.text()) / 100

            # 验证输入
            if evap_temp >= cond_temp:
                QMessageBox.warning(self, "输入错误", "蒸发温度必须低于冷凝温度")
                return

            if cycle_type == "实际循环":
                subcool = float(self.subcool_input.text())
                superheat = float(self.superheat_input.text())
            else:
                subcool = 0
                superheat = 0

            # 制冷剂名称映射
            ref_map = {
                "R134a": "R134a",
                "R22": "R22",
                "R410A": "R410A",
                "R32": "R32",
                "R717 (氨)": "R717",
            }
            if refrigerant == "R744 (CO₂)":
                QMessageBox.warning(
                    self, "暂不支持",
                    "CO₂ (R744) 的临界温度仅 31.1°C，常规冷凝温度（如 40°C）下已进入\n"
                    "跨临界循环区域，需要专门的跨临界循环模型（气体冷却器）计算。\n"
                    "本计算器暂不支持 CO₂，请选用其他制冷剂。")
                return
            ref_name = ref_map.get(refrigerant, "R134a")

            # 尝试使用工业级精度计算
            if USE_INDUSTRIAL_CYCLE and ref_name in getattr(_refrigerant_eos, 'REFRIGERANTS', {}):
                result = self._calculate_cycle_industrial(
                    ref_name, evap_temp, cond_temp, subcool, superheat,
                    mass_flow, comp_efficiency, cycle_type
                )
            else:
                result = self._calculate_cycle_simplified(
                    refrigerant, evap_temp, cond_temp, subcool, superheat,
                    mass_flow, comp_efficiency, cycle_type
                )

            # 输出结果到QTextEdit
            self.result_text.setPlainText(result)
            self._last_result = result
            self._last_params = {
                "cycle_type": cycle_type,
                "refrigerant": refrigerant,
                "evap_temp": evap_temp,
                "cond_temp": cond_temp,
                "subcool": subcool,
                "superheat": superheat,
                "mass_flow": mass_flow,
                "comp_efficiency": comp_efficiency,
            }

        except ValueError as e:
            QMessageBox.critical(self, "计算错误", f"参数输入格式错误: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def _calculate_cycle_industrial(self, ref_name, evap_temp, cond_temp,
                                     subcool, superheat, mass_flow, comp_efficiency, cycle_type):
        """工业级精度制冷循环计算 (PR EOS)

        Args:
            ref_name: 制冷剂名称
            evap_temp: 蒸发温度（°C）
            cond_temp: 冷凝温度（°C）
            subcool: 过冷度（K）
            superheat: 过热度（K）
            mass_flow: 质量流量（kg/s）
            comp_efficiency: 压缩机效率（0-1）
            cycle_type: 循环类型

        Returns:
            格式化后的计算结果字符串
        """
        eos = _refrigerant_eos
        ref_data = eos.REFRIGERANTS[ref_name]

        # --- 状态1: 压缩机进口 (蒸发器出口) ---
        sat_ev = eos.saturation_properties(T_K=evap_temp + C_TO_K, ref_name=ref_name)
        P_evap_MPa = sat_ev['P_MPa']

        # 过热蒸汽性质
        T1_C = evap_temp + superheat
        prop1 = eos.vapor_properties(P_evap_MPa, T1_C, ref_name=ref_name)
        h1 = prop1['h']
        s1 = prop1['s']
        T1 = T1_C

        # --- 状态2: 压缩机出口 (等熵压缩: s2s = s1, 二分迭代) ---
        sat_cd = eos.saturation_properties(T_K=cond_temp + C_TO_K, ref_name=ref_name)
        P_cond_MPa = sat_cd['P_MPa']

        T2s_lo = max(evap_temp, cond_temp)
        T2s_hi = T2s_lo + 250.0
        for _ in range(80):
            T2s_mid = 0.5 * (T2s_lo + T2s_hi)
            s_mid = eos.vapor_properties(P_cond_MPa, T2s_mid, ref_name=ref_name)['s']
            if s_mid > s1:
                T2s_hi = T2s_mid
            else:
                T2s_lo = T2s_mid
        T2s_C = 0.5 * (T2s_lo + T2s_hi)
        v2s = eos.vapor_properties(P_cond_MPa, T2s_C, ref_name=ref_name)
        h2s = v2s['h']
        h2 = h1 + (h2s - h1) / comp_efficiency

        # 实际排气温度: 由 h2 在过热区反查 (焓随温度单调)
        T2_lo, T2_hi = T2s_C, T2s_C + 200.0
        for _ in range(80):
            T2_mid = 0.5 * (T2_lo + T2_hi)
            h_mid = eos.vapor_properties(P_cond_MPa, T2_mid, ref_name=ref_name)['h']
            if h_mid > h2:
                T2_hi = T2_mid
            else:
                T2_lo = T2_mid
        T2_C = 0.5 * (T2_lo + T2_hi)

        # --- 状态3: 冷凝器出口 (过冷液体) ---
        T3_C = cond_temp - subcool
        prop3 = eos.liquid_properties(P_cond_MPa, T3_C, ref_name=ref_name)
        h3 = prop3['h']
        T3 = T3_C

        # --- 状态4: 膨胀阀出口 (等焓节流) ---
        h4 = h3
        # 计算节流后干度
        x4 = (h4 - sat_ev['h_f']) / sat_ev['h_fg'] if sat_ev['h_fg'] > 0 else 0.2
        x4 = max(0.0, min(1.0, x4))
        T4 = evap_temp

        # --- 循环性能计算 ---
        refrigeration_effect = h1 - h4
        compressor_work = h2 - h1
        heat_rejection = h2 - h3

        COP = refrigeration_effect / compressor_work if compressor_work > 0.01 else 0
        compressor_power = mass_flow * compressor_work
        refrigeration_capacity = mass_flow * refrigeration_effect

        # 效率分析
        carnot_COP = (evap_temp + C_TO_K) / (cond_temp - evap_temp)
        efficiency = COP / carnot_COP * 100

        # 容积制冷量
        rho_evap = sat_ev['rho_g']
        volumetric_capacity = refrigeration_effect * rho_evap

        # 压力比
        pressure_ratio = P_cond_MPa / P_evap_MPa if P_evap_MPa > 0 else 0

        # 输运性质
        tp = eos.transport_properties(P_evap_MPa, evap_temp, ref_name=ref_name, phase='vapor')
        mu_evap = tp['mu'] * 1e6  # Pa·s -> μPa·s
        k_evap = tp['k']          # W/(m·K)

        P_evap_kPa = P_evap_MPa * 1000
        P_cond_kPa = P_cond_MPa * 1000

        method_note = "PR EOS + Antoine + Rackett" if USE_INDUSTRIAL_CYCLE else "简化计算"

        return f"""═══════════════════════════════════════════════════
                         输入参数
═══════════════════════════════════════════════════

循环类型: {cycle_type}
制冷剂: {ref_name}
蒸发温度: {evap_temp} °C
冷凝温度: {cond_temp} °C
过冷度: {subcool} K
过热度: {superheat} K
质量流量: {mass_flow} kg/s
压缩机效率: {comp_efficiency*100:.1f} %
计算方法: {method_note}

═══════════════════════════════════════════════════
                        状态点参数
═══════════════════════════════════════════════════

• 点1 (压缩机进口 - 蒸发器出口):
  温度: {T1:.1f} °C, 压力: {P_evap_kPa:.1f} kPa
  焓值: {h1:.2f} kJ/kg, 熵值: {s1:.4f} kJ/(kg·K)

• 点2 (压缩机出口 - 冷凝器入口):
  温度: {T2_C:.1f} °C, 压力: {P_cond_kPa:.1f} kPa
  焓值: {h2:.2f} kJ/kg

• 点3 (冷凝器出口 - 膨胀阀入口):
  温度: {T3:.1f} °C, 压力: {P_cond_kPa:.1f} kPa
  焓值: {h3:.2f} kJ/kg

• 点4 (膨胀阀出口 - 蒸发器入口):
  温度: {T4:.1f} °C, 压力: {P_evap_kPa:.1f} kPa
  焓值: {h4:.2f} kJ/kg, 干度: {x4:.3f}

═══════════════════════════════════════════════════
                        性能参数
═══════════════════════════════════════════════════

单位质量参数:
• 制冷效应: {refrigeration_effect:.2f} kJ/kg
• 压缩功: {compressor_work:.2f} kJ/kg
• 排热量: {heat_rejection:.2f} kJ/kg
• 压力比: {pressure_ratio:.2f}

系统性能:
• 制冷量: {refrigeration_capacity:.2f} kW
• 压缩机功率: {compressor_power:.2f} kW
• 性能系数(COP): {COP:.3f}
• 单位容积制冷量: {volumetric_capacity:.1f} kJ/m³

效率分析:
• 卡诺循环COP: {carnot_COP:.3f}
• 循环效率: {efficiency:.1f} %

蒸发器侧输运性质:
• 粘度: {mu_evap:.2f} μPa·s
• 导热系数: {k_evap:.4f} W/(m·K)

═══════════════════════════════════════════════════
                        计算说明
═══════════════════════════════════════════════════

• 压缩过程: 等熵迭代 (s2s = s1, EOS 焓熵) + 等熵效率修正
• 膨胀过程: 等焓节流
• 饱和性质精度: ±2%, P-V-T 精度: ±3%
• 结果适用于工程初步设计和方案比选"""

    def _calculate_cycle_simplified(self, refrigerant, evap_temp, cond_temp,
                                     subcool, superheat, mass_flow, comp_efficiency, cycle_type):
        """简化计算（保底方案）

        Args:
            refrigerant: 制冷剂名称
            evap_temp: 蒸发温度（°C）
            cond_temp: 冷凝温度（°C）
            subcool: 过冷度（K）
            superheat: 过热度（K）
            mass_flow: 质量流量（kg/s）
            comp_efficiency: 压缩机效率（0-1）
            cycle_type: 循环类型

        Returns:
            格式化后的计算结果字符串
        """
        # 计算各状态点参数
        P_evap = self.calculate_saturation_pressure(refrigerant, evap_temp)
        T1 = evap_temp + superheat
        h1 = self.calculate_enthalpy(refrigerant, T1, P_evap, is_vapor=True)
        s1 = self.calculate_entropy(refrigerant, T1, P_evap, is_vapor=True)

        P_cond = self.calculate_saturation_pressure(refrigerant, cond_temp)
        h2s = h1 + (P_cond - P_evap) * 0.1
        h2 = h1 + (h2s - h1) / comp_efficiency
        T2 = cond_temp + 20

        T3 = cond_temp - subcool
        h3 = self.calculate_enthalpy(refrigerant, T3, P_cond, is_vapor=False)

        h4 = h3
        T4 = evap_temp

        refrigeration_effect = h1 - h4
        compressor_work = h2 - h1
        heat_rejection = h2 - h3

        COP = refrigeration_effect / compressor_work
        compressor_power = mass_flow * compressor_work
        refrigeration_capacity = mass_flow * refrigeration_effect

        carnot_COP = (evap_temp + C_TO_K) / (cond_temp - evap_temp)
        efficiency = COP / carnot_COP * 100

        return self._format_results(
            cycle_type, refrigerant, evap_temp, cond_temp, subcool, superheat,
            mass_flow, comp_efficiency, P_evap, P_cond, h1, h2, h3, h4,
            refrigeration_effect, compressor_work, heat_rejection, COP,
            compressor_power, refrigeration_capacity, carnot_COP, efficiency
        )

    def _format_results(self, cycle_type, refrigerant, evap_temp, cond_temp, subcool,
                      superheat, mass_flow, comp_efficiency, P_evap, P_cond, h1, h2,
                      h3, h4, refrigeration_effect, compressor_work, heat_rejection,
                      COP, compressor_power, refrigeration_capacity, carnot_COP, efficiency):
        """格式化计算结果

        Args:
            各种计算参数

        Returns:
            格式化后的字符串
        """
        return f"""═══════════════════════════════════════════════════
⚠⚠⚠  物性库 refrigerant_eos 加载失败  ⚠⚠⚠
以下结果由粗略估算公式产生（误差可达 ±30% 以上），
不可用于工程设计，请检查程序安装后重新计算。
═══════════════════════════════════════════════════
                         输入参数
═══════════════════════════════════════════════════

循环类型: {cycle_type}
制冷剂: {refrigerant}
蒸发温度: {evap_temp} °C
冷凝温度: {cond_temp} °C
过冷度: {subcool} K
过热度: {superheat} K
质量流量: {mass_flow} kg/s
压缩机效率: {comp_efficiency*100:.1f} %

═══════════════════════════════════════════════════
                        状态点参数
═══════════════════════════════════════════════════

• 点1 (压缩机进口):
  温度: {evap_temp + superheat:.1f} °C, 压力: {P_evap:.1f} kPa
  焓值: {h1:.2f} kJ/kg

• 点2 (压缩机出口):
  温度: {cond_temp + 20:.1f} °C, 压力: {P_cond:.1f} kPa
  焓值: {h2:.2f} kJ/kg

• 点3 (冷凝器出口):
  温度: {cond_temp - subcool:.1f} °C, 压力: {P_cond:.1f} kPa
  焓值: {h3:.2f} kJ/kg

• 点4 (膨胀阀出口):
  温度: {evap_temp:.1f} °C, 压力: {P_evap:.1f} kPa
  焓值: {h4:.2f} kJ/kg

═══════════════════════════════════════════════════
                        性能参数
═══════════════════════════════════════════════════

单位质量参数:
• 制冷效应: {refrigeration_effect:.2f} kJ/kg
• 压缩功: {compressor_work:.2f} kJ/kg
• 排热量: {heat_rejection:.2f} kJ/kg

系统性能:
• 制冷量: {refrigeration_capacity:.2f} kW
• 压缩机功率: {compressor_power:.2f} kW
• 性能系数(COP): {COP:.3f}

效率分析:
• 卡诺循环COP: {carnot_COP:.3f}
• 循环效率: {efficiency:.1f} %

═══════════════════════════════════════════════════
                        计算说明
═══════════════════════════════════════════════════

• 基于蒸汽压缩制冷循环理论计算
• 使用简化物性计算方法
• 假设压缩过程为等熵过程
• 膨胀过程为等焓过程
• 冷凝器和蒸发器压力为饱和压力
• 结果仅供参考，实际系统性能可能有所不同"""

    def clear_inputs(self):
        """清空所有输入"""
        self.cycle_button_group.button(0).setChecked(True)
        self.refrigerant_combo.setCurrentIndex(0)
        self.evap_temp_input.setText("-10")
        self.cond_temp_input.setText("40")
        self.subcool_input.setText("5")
        self.superheat_input.setText("5")
        self.mass_flow_input.setText("0.1")
        self.comp_eff_input.setText("80")
        self.on_cycle_type_changed()
        self.result_text.clear()
        self._last_result = ""
        self._last_params = {}

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

    def generate_report(self):
        """生成计算书文本（str）"""
        try:
            result_text = self.result_text.toPlainText()
            if not result_text or ("COP" not in result_text):
                return None

            project_info = self.get_project_info()
            report = f"""══════════════════════════════════════════
          制冷循环计算计算书
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

  1. 优先采用 PR 状态方程工业级物性，缺失时回退简化关联式
  2. 压缩过程按等熵效率修正，膨胀过程按等焓节流处理
  3. 计算结果适用于工程初步设计，实际选型需经专业工程师审核确认

---
生成于 ChemCal 工程计算模块
"""
            return report

        except Exception as e:
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "制冷循环计算")

    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "制冷循环计算")

    def _get_history_data(self):
        """获取历史记录数据 - 统一接口方法

        Returns:
            包含输入和输出数据的字典
        """
        cycle_type = self.cycle_button_group.checkedButton().text()
        refrigerant_text = self.refrigerant_combo.currentText()
        refrigerant = refrigerant_text.split(" - ")[0]
        evap_temp = float(self.evap_temp_input.text() or 0)
        cond_temp = float(self.cond_temp_input.text() or 0)
        mass_flow = float(self.mass_flow_input.text() or 0)
        comp_efficiency = float(self.comp_eff_input.text() or 0) / 100

        inputs = {
            "循环类型": cycle_type,
            "制冷剂": refrigerant,
            "蒸发温度_C": evap_temp,
            "冷凝温度_C": cond_temp,
            "质量流量_kg_s": mass_flow,
            "压缩机效率_%": comp_efficiency * 100
        }

        outputs = {}
        try:
            if cycle_type == "实际循环":
                subcool = float(self.subcool_input.text() or 0)
                superheat = float(self.superheat_input.text() or 0)
                inputs["过冷度_C"] = subcool
                inputs["过热度_C"] = superheat
            else:
                subcool = 0
                superheat = 0

            ref_map = {
                "R134a": "R134a", "R22": "R22", "R410A": "R410A",
                "R32": "R32", "R717 (氨)": "R717",
            }
            if refrigerant == "R744 (CO₂)":
                return {"inputs": inputs, "outputs": {"说明": "CO₂ 跨临界循环暂不支持"}}
            ref_name = ref_map.get(refrigerant, "R134a")

            if USE_INDUSTRIAL_CYCLE and ref_name in getattr(_refrigerant_eos, 'REFRIGERANTS', {}):
                sat_ev = _refrigerant_eos.saturation_properties(T_K=evap_temp+C_TO_K, ref_name=ref_name)
                sat_cd = _refrigerant_eos.saturation_properties(T_K=cond_temp+C_TO_K, ref_name=ref_name)

                T1_C = evap_temp + superheat
                prop1 = _refrigerant_eos.vapor_properties(sat_ev['P_MPa'], T1_C, ref_name=ref_name)
                h1 = prop1['h']
                s1 = prop1['s']

                # 等熵迭代: s2s = s1
                P_cd = sat_cd['P_MPa']
                T2s_lo = max(evap_temp, cond_temp)
                T2s_hi = T2s_lo + 250.0
                for _ in range(80):
                    T2s_mid = 0.5 * (T2s_lo + T2s_hi)
                    s_mid = _refrigerant_eos.vapor_properties(P_cd, T2s_mid, ref_name=ref_name)['s']
                    if s_mid > s1:
                        T2s_hi = T2s_mid
                    else:
                        T2s_lo = T2s_mid
                h2s = _refrigerant_eos.vapor_properties(P_cd, 0.5*(T2s_lo+T2s_hi), ref_name=ref_name)['h']
                h2 = h1 + (h2s - h1) / comp_efficiency

                T3_C = cond_temp - subcool
                prop3 = _refrigerant_eos.liquid_properties(sat_cd['P_MPa'], T3_C, ref_name=ref_name)
                h3 = prop3['h']
                h4 = h3

                refrigeration_effect = h1 - h4
                compressor_work = h2 - h1
                COP = refrigeration_effect / compressor_work
                compressor_power = mass_flow * compressor_work
                refrigeration_capacity = mass_flow * refrigeration_effect
                carnot_COP = (evap_temp + C_TO_K) / (cond_temp - evap_temp)
            else:
                P_evap = self.calculate_saturation_pressure(refrigerant, evap_temp)
                P_cond = self.calculate_saturation_pressure(refrigerant, cond_temp)
                T1 = evap_temp + superheat
                h1 = self.calculate_enthalpy(refrigerant, T1, P_evap, is_vapor=True)
                h2s = h1 + (P_cond - P_evap) * 0.1
                h2 = h1 + (h2s - h1) / comp_efficiency
                h3 = self.calculate_enthalpy(refrigerant, cond_temp - subcool, P_cond, is_vapor=False)
                h4 = h3
                refrigeration_effect = h1 - h4
                compressor_work = h2 - h1
                COP = refrigeration_effect / compressor_work
                compressor_power = mass_flow * compressor_work
                refrigeration_capacity = mass_flow * refrigeration_effect
                carnot_COP = (evap_temp + C_TO_K) / (cond_temp - evap_temp)

            outputs = {
                "制冷量_kW": round(refrigeration_capacity, 2),
                "压缩机功率_kW": round(compressor_power, 2),
                "COP": round(COP, 3),
                "卡诺COP": round(carnot_COP, 3),
                "单位制冷量_kJ_kg": round(refrigeration_effect, 2),
                "单位压缩功_kJ_kg": round(compressor_work, 2)
            }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = RefrigerationCycleCalculator()
    widget.resize(1300, 700)
    widget.show()

    sys.exit(app.exec())
