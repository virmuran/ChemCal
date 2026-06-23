"""
蒸汽空消计算器 — 计算发酵罐/种子罐/管道空消所需蒸汽量

计算原理：
  蒸汽消耗 = (罐体加热热负荷 + 灭菌期间散热损失) / (蒸汽汽化潜热 * 热效率)

物理模型：
  1. 由罐体体积和高径比反推几何尺寸（直径、高度、表面积）
  2. 按 ASME BPVC VIII-1 公式估算壁厚
  3. 由表面积 * 壁厚 * 材质密度计算罐体重量
  4. Q_heat = m * Cp * ΔT 计算加热热负荷
  5. Q_loss = h_loss * A * ΔT * time 计算散热损失
  6. 通过 IAPWS-IF97 获取蒸汽汽化潜热
  7. 蒸汽量 = (Q_heat + Q_loss) * 安全系数 / 汽化潜热

局限性：
  - 罐体重量的 ±15~20% 来自壁厚估算（实际受设计压力、制造商标准影响）
  - 保温散热系数为经验值
  - 作为初步设计估算远优于盲猜，误差在可接受范围
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QFrame,
    QScrollArea, QButtonGroup, QGridLayout,
    QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math
import os
import sys
import importlib.util
from datetime import datetime
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
# DOCX 报告导出

# 动态加载 IAPWS-IF97 蒸汽物性模块
try:
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _parent_dir = os.path.dirname(_current_dir)
    _spec = importlib.util.spec_from_file_location(
        "steam_iapws",
        os.path.join(_parent_dir, "steam_iapws.py")
    )
    _steam_iapws = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_steam_iapws)
    _iapws_available = True
except Exception as _e:
    _iapws_available = False
    print(f"警告: 无法加载 IAPWS-IF97 模块: {_e}")

# ── 输入参数 key 常量（显式定义，避免清洗/硬编码不一致的Bug）──
K_VOLUME = "volume"               # 罐体体积 m³
K_HD_RATIO = "hd_ratio"           # 高径比 H/D
K_MATERIAL = "material"           # 罐体材质
K_T_STERILIZE = "t_sterilize"     # 灭菌温度 °C
K_T_INITIAL = "t_initial"         # 初始温度 °C
K_P_STEAM = "p_steam"             # 蒸汽压力 MPa(g)
K_INSULATION = "insulation"       # 保温类型
K_TIME = "sterilize_time"         # 灭菌时间 min
K_SAFETY = "safety_factor"        # 安全系数
K_EFFICIENCY = "efficiency"       # 热效率

# 管道消毒专用 key
K_PIPE_DN = "pipe_dn"             # 管道公称直径
K_PIPE_LENGTH = "pipe_length"     # 管道长度 m
K_PIPE_MATERIAL = "pipe_material" # 管道材质

# ── 材质数据库 ──
# ρ: 密度 kg/m³, Cp: 比热容 J/(kg·K), S: 许用应力 MPa (150°C)
MATERIAL_DB = {
    "304不锈钢": {"rho": 7930, "cp": 500, "S": 115, "display": "304不锈钢"},
    "316L不锈钢": {"rho": 8000, "cp": 500, "S": 115, "display": "316L不锈钢"},
    "碳钢Q235": {"rho": 7850, "cp": 460, "S": 113, "display": "碳钢 Q235"},
    "搪玻璃": {"rho": 7850, "cp": 460, "S": 100, "display": "搪玻璃（碳钢基体）"},
    "钛材TA2": {"rho": 4510, "cp": 540, "S": 100, "display": "钛材 TA2"},
}

# ── 保温类型 ──
INSULATION_DB = {
    "无保温": 15.0,
    "岩棉50mm": 3.0,
    "岩棉80mm": 2.0,
    "岩棉100mm": 1.5,
}

# ── 管道尺寸表（Schedule 40, 碳钢/不锈钢标准）──
# DN: (外径 mm, 壁厚 mm)
PIPE_DIMENSIONS = {
    "DN15": (21.3, 2.8),
    "DN20": (26.9, 2.9),
    "DN25": (33.7, 3.2),
    "DN32": (42.4, 3.6),
    "DN40": (48.3, 3.7),
    "DN50": (60.3, 3.9),
    "DN65": (76.1, 5.2),
    "DN80": (88.9, 5.5),
    "DN100": (114.3, 6.0),
    "DN125": (139.7, 6.6),
    "DN150": (168.3, 7.1),
    "DN200": (219.1, 8.2),
    "DN250": (273.0, 9.3),
    "DN300": (323.9, 10.3),
}

# ── 样式 ──


class SteamSterilizationCalculator(CalculatorBase):
    """蒸汽空消计算器"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)

        if data_manager is not None:
            self.data_manager = data_manager
        else:
            try:
                from data_manager import DataManager
                self.data_manager = DataManager.get_instance()
            except Exception:
                self.data_manager = None

        self.input_widgets = {}
        self._last_results = {}

        self.setup_ui()
        self.setup_calculation_mode(0)  # 默认罐体空消

        # 滚轮拦截
        self.setup_wheel_blocker()

    # ═══════════════════════════════════════════════════════════════
    # UI 构建
    # ═══════════════════════════════════════════════════════════════

    def setup_ui(self):
        """主布局：左右分栏"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ── 左侧：输入区域 ──
        scroll_left = QScrollArea()
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 说明文字
        desc = QLabel(
            "蒸汽空消计算器 — 计算发酵罐、种子罐及管道空消所需蒸汽量。\n"
            "基于罐体体积反推几何尺寸和壁厚，估算罐体重量，结合蒸汽汽化潜热计算蒸汽消耗。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc)

        # 计算模式按钮组
        mode_group = QGroupBox("计算模式")
        mode_layout = QHBoxLayout(mode_group)

        self.mode_button_group = QButtonGroup(self)
        self.mode_buttons = {}

        modes = [
            ("罐体空消", "发酵罐/种子罐空消蒸汽计算"),
            ("管道消毒", "管道消毒蒸汽计算"),
        ]

        for i, (name, tip) in enumerate(modes):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: black;
                    border: 1px solid #888;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                }
                QPushButton:checked {
                    background-color: #4b5cc4;
                    color: white;
                }
                QPushButton:hover:!checked {
                    background-color: #c0ebd7;
                    color: black;
                }
            """)
            self.mode_button_group.addButton(btn, i)
            mode_layout.addWidget(btn)
            self.mode_buttons[name] = btn

        self.mode_buttons["罐体空消"].setChecked(True)
        mode_layout.addStretch()
        left_layout.addWidget(mode_group)

        # 输入参数网格
        input_group = QGroupBox("输入参数")
        self.input_layout = QGridLayout(input_group)
        self.input_layout.setSpacing(12)
        self.input_layout.setContentsMargins(10, 15, 10, 15)
        # 列比例: label(4) : input(8) : hint/combo(5)
        self.input_layout.setColumnStretch(0, 4)
        self.input_layout.setColumnStretch(1, 8)
        self.input_layout.setColumnStretch(2, 5)
        left_layout.addWidget(input_group)

        # 计算按钮
        calc_btn = QPushButton("计 算")
        calc_btn.setMinimumHeight(50)
        calc_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                padding: 0px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #219955;
            }
        """)
        calc_btn.clicked.connect(self.calculate)
        left_layout.addWidget(calc_btn)

        scroll_left.setWidget(left_widget)

        # ── 右侧：结果区域 ──
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)

        result_group = QGroupBox("计算结果")
        result_inner = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("font-size: 13px;")
        result_inner.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # 底部按钮
        btn_layout = QHBoxLayout()

        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(
            "QPushButton { background-color: #95a5a6; color: white; "
            "padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #7f8c8d; }"
        )
        clear_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(clear_btn)

        docx_btn = QPushButton("下载 DOCX")
        docx_btn.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; "
            "padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #2980b9; }"
        )
        docx_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        docx_btn.clicked.connect(self.download_docx_report)
        btn_layout.addWidget(docx_btn)

        pdf_btn = QPushButton("下载 PDF")
        pdf_btn.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; "
            "padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #c0392b; }"
        )
        pdf_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        pdf_btn.clicked.connect(self.download_pdf_report)
        btn_layout.addWidget(pdf_btn)

        right_layout.addLayout(btn_layout)

        # 组装左右
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

        # 模式切换连接
        self.mode_button_group.buttonClicked.connect(self.on_mode_button_clicked)

    # ═══════════════════════════════════════════════════════════════
    # 模式切换
    # ═══════════════════════════════════════════════════════════════

    def on_mode_button_clicked(self, button):
        """模式按钮点击"""
        self.setup_calculation_mode(self.mode_button_group.id(button))

    def get_current_mode(self):
        checked = self.mode_button_group.checkedButton()
        return checked.text() if checked else "罐体空消"

    def setup_calculation_mode(self, mode_index):
        """切换到指定的计算模式"""
        # 清除输入网格
        for key in list(self.input_widgets.keys()):
            w = self.input_widgets.pop(key)
            w.setParent(None)

        # 清结果
        self.result_text.clear()
        self._last_results = {}

        if mode_index == 0:
            self._setup_tank_mode()
        else:
            self._setup_pipe_mode()

    # ═══════════════════════════════════════════════════════════════
    # 模式1 — 罐体空消
    # ═══════════════════════════════════════════════════════════════

    def _setup_tank_mode(self):
        """罐体空消输入界面"""
        label_style = "font-weight: bold; padding-right: 10px; text-align: right;"

        inputs = [
            (0, "罐体体积 (m³):", K_VOLUME, "例如：10", QDoubleValidator(0.1, 10000, 2)),
            (1, "高径比 H/D:", K_HD_RATIO, "默认 2.0", QDoubleValidator(0.5, 5.0, 1)),
            (2, "罐体材质:", K_MATERIAL, None, None),
            (3, "灭菌温度 (°C):", K_T_STERILIZE, "默认 121", QDoubleValidator(100, 150, 1)),
            (4, "初始温度 (°C):", K_T_INITIAL, "默认 25", QDoubleValidator(-10, 50, 1)),
            (5, "蒸汽压力 MPa(g):", K_P_STEAM, "默认 0.3", QDoubleValidator(0.05, 2.5, 2)),
            (6, "保温类型:", K_INSULATION, None, None),
            (7, "灭菌时间 (min):", K_TIME, "默认 30", QDoubleValidator(5, 240, 1)),
            (8, "安全系数:", K_SAFETY, "默认 1.2", QDoubleValidator(1.0, 2.0, 2)),
            (9, "热效率:", K_EFFICIENCY, "默认 0.95", QDoubleValidator(0.5, 1.0, 2)),
        ]

        for row, label_text, key, placeholder, validator in inputs:
            lbl = QLabel(label_text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet(label_style)
            self.input_layout.addWidget(lbl, row, 0)

            if key == K_MATERIAL:
                combo = QComboBox()
                combo.setStyleSheet(COMBOBOX_STYLE)
                for mat in MATERIAL_DB:
                    combo.addItem(mat)
                combo.setCurrentIndex(0)
                self.input_layout.addWidget(combo, row, 1)
                self.input_widgets[key] = combo
            elif key == K_INSULATION:
                combo = QComboBox()
                combo.setStyleSheet(COMBOBOX_STYLE)
                for ins in INSULATION_DB:
                    combo.addItem(ins)
                combo.setCurrentIndex(1)  # 默认岩棉50mm
                self.input_layout.addWidget(combo, row, 1)
                self.input_widgets[key] = combo
            else:
                line = QLineEdit()
                line.setAlignment(Qt.AlignmentFlag.AlignLeft)
                if placeholder:
                    line.setPlaceholderText(placeholder)
                    # 设置默认值
                    defaults = {
                        K_VOLUME: "", K_HD_RATIO: "2.0", K_T_STERILIZE: "121",
                        K_T_INITIAL: "25", K_P_STEAM: "0.3", K_TIME: "30",
                        K_SAFETY: "1.2", K_EFFICIENCY: "0.95",
                    }
                    if key in defaults and defaults[key]:
                        line.setText(defaults[key])
                if validator:
                    line.setValidator(validator)
                self.input_layout.addWidget(line, row, 1)
                self.input_widgets[key] = line

    # ═══════════════════════════════════════════════════════════════
    # 模式2 — 管道消毒
    # ═══════════════════════════════════════════════════════════════

    def _setup_pipe_mode(self):
        """管道消毒输入界面"""
        label_style = "font-weight: bold; padding-right: 10px; text-align: right;"

        inputs = [
            (0, "管道公称直径:", K_PIPE_DN, None, None),
            (1, "管道长度 (m):", K_PIPE_LENGTH, "例如：50", QDoubleValidator(0.5, 5000, 1)),
            (2, "管道材质:", K_PIPE_MATERIAL, None, None),
            (3, "灭菌温度 (°C):", K_T_STERILIZE, "默认 121", QDoubleValidator(100, 150, 1)),
            (4, "初始温度 (°C):", K_T_INITIAL, "默认 25", QDoubleValidator(-10, 50, 1)),
            (5, "蒸汽压力 MPa(g):", K_P_STEAM, "默认 0.3", QDoubleValidator(0.05, 2.5, 2)),
            (6, "保温类型:", K_INSULATION, None, None),
            (7, "灭菌时间 (min):", K_TIME, "默认 30", QDoubleValidator(5, 240, 1)),
            (8, "安全系数:", K_SAFETY, "默认 1.2", QDoubleValidator(1.0, 2.0, 2)),
            (9, "热效率:", K_EFFICIENCY, "默认 0.95", QDoubleValidator(0.5, 1.0, 2)),
        ]

        for row, label_text, key, placeholder, validator in inputs:
            lbl = QLabel(label_text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet(label_style)
            self.input_layout.addWidget(lbl, row, 0)

            if key == K_PIPE_DN:
                combo = QComboBox()
                combo.setStyleSheet(COMBOBOX_STYLE)
                for dn in PIPE_DIMENSIONS:
                    od, wt = PIPE_DIMENSIONS[dn]
                    combo.addItem(f"{dn} (外径{od}×{wt}mm)")
                combo.setCurrentIndex(5)  # 默认 DN50
                self.input_layout.addWidget(combo, row, 1)
                self.input_widgets[key] = combo
            elif key == K_PIPE_MATERIAL:
                combo = QComboBox()
                combo.setStyleSheet(COMBOBOX_STYLE)
                pipe_mats = ["304不锈钢", "316L不锈钢", "碳钢Q235"]
                for mat in pipe_mats:
                    combo.addItem(mat)
                combo.setCurrentIndex(0)
                self.input_layout.addWidget(combo, row, 1)
                self.input_widgets[key] = combo
            elif key == K_INSULATION:
                combo = QComboBox()
                combo.setStyleSheet(COMBOBOX_STYLE)
                for ins in INSULATION_DB:
                    combo.addItem(ins)
                combo.setCurrentIndex(1)
                self.input_layout.addWidget(combo, row, 1)
                self.input_widgets[key] = combo
            else:
                line = QLineEdit()
                line.setAlignment(Qt.AlignmentFlag.AlignLeft)
                if placeholder:
                    line.setPlaceholderText(placeholder)
                    defaults = {
                        K_PIPE_LENGTH: "50", K_T_STERILIZE: "121",
                        K_T_INITIAL: "25", K_P_STEAM: "0.3", K_TIME: "30",
                        K_SAFETY: "1.2", K_EFFICIENCY: "0.95",
                    }
                    if key in defaults and defaults[key]:
                        line.setText(defaults[key])
                if validator:
                    line.setValidator(validator)
                self.input_layout.addWidget(line, row, 1)
                self.input_widgets[key] = line

    # ═══════════════════════════════════════════════════════════════
    # 输入读取
    # ═══════════════════════════════════════════════════════════════

    def _get(self, key, default=0.0):
        """从 input_widgets 中读取数值"""
        if key not in self.input_widgets:
            return default
        w = self.input_widgets[key]
        if isinstance(w, QLineEdit):
            t = w.text().strip()
            if t:
                try:
                    return float(t)
                except ValueError:
                    return default
            return default
        elif isinstance(w, QComboBox):
            return w.currentText()
        return default

    # ═══════════════════════════════════════════════════════════════
    # 蒸汽物性（通过 IAPWS-IF97）
    # ═══════════════════════════════════════════════════════════════

    def _get_steam_props(self, p_gauge_mpa):
        """由表压 MPa(g) 获取蒸汽物性"""
        if not _iapws_available:
            return {"sat_temp": 143.6, "h_fg": 2133.0, "method": "内置近似值"}

        try:
            p_abs = p_gauge_mpa + 0.101325  # 表压转绝对压力 MPa
            from iapws import IAPWS97
            steam = IAPWS97(P=p_abs, x=1.0)  # 干饱和蒸汽
            return {
                "sat_temp": steam.T - 273.15,
                "h_fg": steam.h - IAPWS97(P=p_abs, x=0).h,  # h_g - h_f
                "method": "IAPWS-IF97"
            }
        except Exception:
            # 回退到 IAPWS97 saturated temperature
            try:
                from iapws import IAPWS97
                steam = IAPWS97(P=p_gauge_mpa + 0.101325, x=1.0)
                sat_water = IAPWS97(P=p_gauge_mpa + 0.101325, x=0)
                return {
                    "sat_temp": steam.T - 273.15,
                    "h_fg": steam.h - sat_water.h,
                    "method": "IAPWS-IF97"
                }
            except Exception:
                return {"sat_temp": 143.6, "h_fg": 2133.0, "method": "内置近似值"}

    # ═══════════════════════════════════════════════════════════════
    # 罐体几何计算
    # ═══════════════════════════════════════════════════════════════

    def _calc_tank_geometry(self, volume, hd_ratio):
        """由体积和高径比反推罐体几何尺寸

        V = π*(D/2)²*(k*D) = πkD³/4  →  D = (4V/(πk))^(1/3)

        Returns:
            dict: D(m), H(m), A_body(m²), A_heads(m²), A_total(m²)
        """
        D = (4 * volume / (math.pi * hd_ratio)) ** (1 / 3)
        H = hd_ratio * D

        # 筒体侧面积
        A_body = math.pi * D * H

        # 封头面积（标准椭圆封头，近似 1.08×投影面积 每个）
        A_head_per = 1.08 * math.pi * D**2 / 4
        A_heads = 2 * A_head_per

        A_total = A_body + A_heads

        return {
            "D": D,
            "H": H,
            "A_body": A_body,
            "A_heads": A_heads,
            "A_total": A_total,
        }

    def _calc_wall_thickness(self, D, p_design, material_data):
        """ASME BPVC VIII-1 圆柱壳壁厚计算

        t = P*R/(S*E - 0.6*P) + CA

        D: 内径 m
        p_design: 设计压力 MPa
        material_data: MATERIAL_DB 中条目

        Returns: 壁厚 mm（向上取整到标准板厚）
        """
        R = D * 500  # 内半径 mm (D/2 * 1000)
        S = material_data["S"]  # 许用应力 MPa
        E = 0.85  # 焊接接头系数（局部探伤）
        CA = 1.0  # 腐蚀裕量 mm

        t_calc = p_design * R / (S * E - 0.6 * p_design) + CA

        # 向上取整到标准板厚
        thresholds = [3, 4, 5, 6, 8, 10, 12, 14, 16, 20]
        for t_std in thresholds:
            if t_calc <= t_std:
                return t_std
        return max(thresholds[-1], math.ceil(t_calc))

    # ═══════════════════════════════════════════════════════════════
    # 计算逻辑
    # ═══════════════════════════════════════════════════════════════

    def calculate(self):
        """主计算入口"""
        mode = self.get_current_mode()
        try:
            if mode == "罐体空消":
                self._calc_tank()
            else:
                self._calc_pipe()
        except ValueError as e:
            QMessageBox.warning(self, "输入错误", str(e))
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"发生意外错误:\n{str(e)}")

    def _calc_tank(self):
        """罐体空消计算"""
        # 读取输入
        volume = self._get(K_VOLUME)
        if volume <= 0:
            raise ValueError("请输入有效的罐体体积")

        hd_ratio = self._get(K_HD_RATIO, 2.0)
        material_name = self._get(K_MATERIAL, "304不锈钢")
        t_sterilize = self._get(K_T_STERILIZE, 121)
        t_initial = self._get(K_T_INITIAL, 25)
        p_steam = self._get(K_P_STEAM, 0.3)
        insulation = self._get(K_INSULATION, "岩棉50mm")
        time_min = self._get(K_TIME, 30)
        safety = self._get(K_SAFETY, 1.2)
        efficiency = self._get(K_EFFICIENCY, 0.95)

        mat = MATERIAL_DB[material_name]

        # 1. 几何计算
        geo = self._calc_tank_geometry(volume, hd_ratio)

        # 2. 壁厚计算（设计压力 = 蒸汽压力 + 0.2MPa 裕量）
        p_design = p_steam + 0.2
        wall_thickness = self._calc_wall_thickness(geo["D"], p_design, mat)

        # 3. 罐体重量
        tank_weight = geo["A_total"] * (wall_thickness / 1000) * mat["rho"]  # kg

        # 4. 加热热负荷
        delta_t = t_sterilize - t_initial
        q_heat = tank_weight * mat["cp"] * delta_t / 1000  # kJ

        # 5. 散热损失
        t_ambient = 25  # 假设环境温度
        h_loss = INSULATION_DB[insulation]  # W/(m²·K)
        q_loss = h_loss * geo["A_total"] * (t_sterilize - t_ambient) * time_min * 60 / 1000  # kJ

        # 6. 蒸汽物性
        steam = self._get_steam_props(p_steam)
        h_fg = steam["h_fg"]  # kJ/kg

        # 7. 蒸汽用量
        q_total = (q_heat + q_loss) * safety
        steam_mass_theoretical = q_total / h_fg
        steam_mass_actual = steam_mass_theoretical / efficiency

        # 8. 存储结果用于历史
        self._last_results = {
            "模式": "罐体空消",
            "volume": volume,
            "hd_ratio": hd_ratio,
            "material": material_name,
            "p_steam": p_steam,
            "t_sterilize": t_sterilize,
            "t_initial": t_initial,
            "D": geo["D"],
            "H": geo["H"],
            "A_total": geo["A_total"],
            "wall_thickness": wall_thickness,
            "tank_weight": tank_weight,
            "delta_t": delta_t,
            "q_heat": q_heat,
            "q_loss": q_loss,
            "steam_sat_temp": steam["sat_temp"],
            "h_fg": h_fg,
            "steam_method": steam["method"],
            "q_total": q_total,
            "steam_mass_theoretical": steam_mass_theoretical,
            "safety": safety,
            "efficiency": efficiency,
            "steam_mass_actual": steam_mass_actual,
            "insulation": insulation,
            "time_min": time_min,
        }

        # 9. 显示结果
        self._display_tank_result()

    def _calc_pipe(self):
        """管道消毒计算"""
        # 读取输入
        pipe_dn_text = self._get(K_PIPE_DN, "DN50 (外径60.3×3.9mm)")
        pipe_length = self._get(K_PIPE_LENGTH, 50)
        if pipe_length <= 0:
            raise ValueError("请输入有效的管道长度")

        material_name = self._get(K_PIPE_MATERIAL, "304不锈钢")
        t_sterilize = self._get(K_T_STERILIZE, 121)
        t_initial = self._get(K_T_INITIAL, 25)
        p_steam = self._get(K_P_STEAM, 0.3)
        insulation = self._get(K_INSULATION, "岩棉50mm")
        time_min = self._get(K_TIME, 30)
        safety = self._get(K_SAFETY, 1.2)
        efficiency = self._get(K_EFFICIENCY, 0.95)

        # 解析管道尺寸
        dn_code = pipe_dn_text.split()[0]  # e.g., "DN50"
        if dn_code not in PIPE_DIMENSIONS:
            raise ValueError(f"不支持的管道规格: {dn_code}")

        od, wt = PIPE_DIMENSIONS[dn_code]

        mat = MATERIAL_DB[material_name]

        # 1. 管道外表面积
        A_per_meter = math.pi * (od / 1000)  # m²/m
        A_total = A_per_meter * pipe_length  # m²

        # 2. 管道重量（按环形截面）
        id_ = od - 2 * wt
        A_cross = math.pi * (od**2 - id_**2) / 4 / 1e6  # m²
        pipe_weight = A_cross * pipe_length * mat["rho"]  # kg

        # 3. 加热热负荷
        delta_t = t_sterilize - t_initial
        q_heat = pipe_weight * mat["cp"] * delta_t / 1000  # kJ

        # 4. 散热损失
        t_ambient = 25
        h_loss = INSULATION_DB[insulation]
        q_loss = h_loss * A_total * (t_sterilize - t_ambient) * time_min * 60 / 1000  # kJ

        # 5. 蒸汽物性
        steam = self._get_steam_props(p_steam)
        h_fg = steam["h_fg"]

        # 6. 蒸汽用量
        q_total = (q_heat + q_loss) * safety
        steam_mass_theoretical = q_total / h_fg
        steam_mass_actual = steam_mass_theoretical / efficiency

        # 7. 存储
        self._last_results = {
            "模式": "管道消毒",
            "p_steam": p_steam,
            "pipe_dn": dn_code,
            "pipe_od": od,
            "pipe_wt": wt,
            "pipe_length": pipe_length,
            "material": material_name,
            "A_total": A_total,
            "pipe_weight": pipe_weight,
            "delta_t": delta_t,
            "q_heat": q_heat,
            "q_loss": q_loss,
            "steam_sat_temp": steam["sat_temp"],
            "h_fg": h_fg,
            "steam_method": steam["method"],
            "q_total": q_total,
            "steam_mass_theoretical": steam_mass_theoretical,
            "safety": safety,
            "efficiency": efficiency,
            "steam_mass_actual": steam_mass_actual,
            "insulation": insulation,
            "time_min": time_min,
        }

        # 8. 显示
        self._display_pipe_result()

    # ═══════════════════════════════════════════════════════════════
    # 结果显示
    # ═══════════════════════════════════════════════════════════════

    def _display_tank_result(self):
        r = self._last_results
        text = f"""══════════════════════════
   罐体空消蒸汽计算
══════════════════════════

【罐体几何参数】
  罐体体积: {r['volume']:.1f} m³
  高径比 H/D: {r['hd_ratio']:.1f}
  计算内径: {r['D']:.3f} m ({r['D']*1000:.0f} mm)
  计算高度: {r['H']:.3f} m ({r['H']*1000:.0f} mm)
  估算壁厚: {r['wall_thickness']:.0f} mm ({r['material']})
  外表面积: {r['A_total']:.1f} m²
  罐体重量: {r['tank_weight']:.0f} kg ({r['tank_weight']/1000:.2f} t)

【热负荷计算】
  材质: {r['material']} (比热容 {MATERIAL_DB[r['material']]['cp']} J/(kg·K))
  温差: {r['delta_t']:.1f} °C ({r['t_sterilize']} → {r['t_initial']})
  罐体加热热负荷: {r['q_heat']/1000:.1f} MJ ({r['q_heat']:.0f} kJ)
  散热系数: {INSULATION_DB.get(r['insulation'], '?')} W/(m²·K) ({r['insulation']})
  灭菌时间: {r['time_min']:.0f} min
  散热量: {r['q_loss']/1000:.2f} MJ ({r['q_loss']:.0f} kJ)

【蒸汽物性】
  蒸汽压力: {r['p_steam']:.2f} MPa(g)
  饱和温度: {r['steam_sat_temp']:.1f} °C
  汽化潜热: {r['h_fg']:.1f} kJ/kg
  物性来源: {r['steam_method']}

【蒸汽消耗】
  总热负荷: {r['q_total']/1000:.2f} MJ
  理论蒸汽量: {r['steam_mass_theoretical']:.2f} kg
  安全系数: {r['safety']:.2f}
  热效率: {r['efficiency']:.2f}
  ★ 实际蒸汽用量: {r['steam_mass_actual']:.2f} kg
  ★ 折合标况: {r['steam_mass_actual']/r['volume']:.1f} kg/m³(罐容)
"""  
        self.result_text.setText(text)

    def _display_pipe_result(self):
        r = self._last_results
        text = f"""══════════════════════════
   管道消毒蒸汽计算
══════════════════════════

【管道参数】
  管道规格: {r['pipe_dn']} (外径{r['pipe_od']}×{r['pipe_wt']}mm)
  管道长度: {r['pipe_length']:.0f} m
  管道材质: {r['material']}
  外表面积: {r['A_total']:.1f} m²
  管道重量: {r['pipe_weight']:.1f} kg

【热负荷计算】
  温差: {r['delta_t']:.1f} °C
  管道加热热负荷: {r['q_heat']/1000:.2f} MJ ({r['q_heat']:.0f} kJ)
  散热系数: {INSULATION_DB.get(r['insulation'], '?')} W/(m²·K) ({r['insulation']})
  灭菌时间: {r['time_min']:.0f} min
  散热量: {r['q_loss']/1000:.3f} MJ ({r['q_loss']:.1f} kJ)

【蒸汽物性】
  蒸汽压力: {r['p_steam']:.2f} MPa(g)
  饱和温度: {r['steam_sat_temp']:.1f} °C
  汽化潜热: {r['h_fg']:.1f} kJ/kg
  物性来源: {r['steam_method']}

【蒸汽消耗】
  总热负荷: {r['q_total']/1000:.3f} MJ
  理论蒸汽量: {r['steam_mass_theoretical']:.2f} kg
  安全系数: {r['safety']:.2f}
  热效率: {r['efficiency']:.2f}
  ★ 实际蒸汽用量: {r['steam_mass_actual']:.2f} kg
  ★ 折合标况: {r['steam_mass_actual']/r['pipe_length']:.2f} kg/m(管长)
"""
        self.result_text.setText(text)

    # ═══════════════════════════════════════════════════════════════
    # 清空
    # ═══════════════════════════════════════════════════════════════

    def clear_all(self):
        """重置所有输入"""
        mode = self.get_current_mode()
        self.setup_calculation_mode(0 if mode == "罐体空消" else 1)

    # ═══════════════════════════════════════════════════════════════
    # 历史记录
    # ═══════════════════════════════════════════════════════════════

    def _get_history_data(self):
        """提供历史记录数据"""
        if not self._last_results:
            return {"inputs": {}, "outputs": {}}

        r = self._last_results
        if r.get("模式") == "罐体空消":
            inputs = {
                "罐体体积_m3": r.get("volume", 0),
                "高径比": r.get("hd_ratio", 0),
                "材质": r.get("material", ""),
                "灭菌温度_C": self._last_results.get("t_sterilize", 0),
                "初始温度_C": self._last_results.get("t_initial", 0),
                "蒸汽压力_MPa": self._last_results.get("p_steam", 0),
                "保温类型": r.get("insulation", ""),
                "灭菌时间_min": r.get("time_min", 0),
                "安全系数": r.get("safety", 0),
                "热效率": r.get("efficiency", 0),
            }
        else:
            inputs = {
                "管道规格": r.get("pipe_dn", ""),
                "管道长度_m": r.get("pipe_length", 0),
                "材质": r.get("material", ""),
                "灭菌温度_C": self._last_results.get("t_sterilize", 0),
                "初始温度_C": self._last_results.get("t_initial", 0),
                "蒸汽压力_MPa": self._last_results.get("p_steam", 0),
                "保温类型": r.get("insulation", ""),
                "灭菌时间_min": r.get("time_min", 0),
                "安全系数": r.get("safety", 0),
                "热效率": r.get("efficiency", 0),
            }

        outputs = {"实际蒸汽用量_kg": round(r.get("steam_mass_actual", 0), 2)}

        return {"inputs": inputs, "outputs": outputs}

    # ═══════════════════════════════════════════════════════════════
    # 报告导出
    # ═══════════════════════════════════════════════════════════════

    def download_docx_report(self):
        """生成DOCX计算书"""
        ReportExporter.export_docx(self, "蒸汽空消计算")

    def download_pdf_report(self):
        """生成PDF计算书"""
        ReportExporter.export_pdf(self, "蒸汽空消计算")


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = SteamSterilizationCalculator()
    widget.resize(1200, 800)
    widget.show()
    sys.exit(app.exec())
