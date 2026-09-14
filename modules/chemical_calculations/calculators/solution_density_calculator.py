"""
溶液密度计算器
支持物料：水、柠檬酸溶液、葡萄糖溶液、蔗糖溶液、NaOH溶液、HCl溶液、H2SO4溶液、NaCl溶液
计算方法：IAPWS-IF97（纯水）+ 经验公式（溶液）+ 温度修正
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QComboBox, QFrame, QGridLayout, QTextEdit, QScrollArea,
    QToolButton, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
from datetime import datetime
import math
import importlib.util
import os
import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K, G, ATM_PRESSURE_MPA, WATER_DENSITY, WATER_CP, load_steam_iapws, get_steam_props
# DOCX 报告导出
from utils.docx_utils import ReportExporter

# ─────────────────── IAPWS-IF97 动态加载 ───────────────────
_IAPWS_MODULE = None
_IAPWS_AVAILABLE = False

def _load_iapws():
    """动态加载 steam_iapws 模块（与换热器计算器同款方案）

    ⚠ 2026-09-13 修复：steam_iapws.py 位于 calculators 的上一级目录
    （modules/chemical_calculations/steam_iapws.py），原代码只在
    calculators 同级目录找 → 永远加载失败 → 静默回退 UNESCO。
    """
    global _IAPWS_MODULE, _IAPWS_AVAILABLE
    if _IAPWS_MODULE is not None or _IAPWS_AVAILABLE:
        return _IAPWS_AVAILABLE
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "steam_iapws.py"),
            os.path.join(os.path.dirname(base_dir), "steam_iapws.py"),
        ]
        path = next((p for p in candidates if os.path.isfile(p)), None)
        if path is None:
            _IAPWS_AVAILABLE = False
            return False
        spec = importlib.util.spec_from_file_location("steam_iapws", path)
        if spec is None:
            _IAPWS_AVAILABLE = False
            return False
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _IAPWS_MODULE = module
        _IAPWS_AVAILABLE = True
        return True
    except Exception:
        _IAPWS_MODULE = None
        _IAPWS_AVAILABLE = False
        return False

_load_iapws()

# ─────────────────────────── 密度计算核心函数 ───────────────────────────

def rho_water(T: float) -> float:
    """
    纯水密度（优先 IAPWS-IF97 Region 1，失败则 UNESCO 1983 公式）
    T: 温度 °C，有效范围 0~100°C（IAPWS 可到 350°C）
    返回: kg/m³
    参考: IAPWS-IF97 / UNESCO 1983
    精度: IAPWS ±0.01 kg/m³ | UNESCO ±0.1 kg/m³
    """
    T = max(0.0, min(100.0, T))
    # 优先 IAPWS-IF97：用 steam_properties(0.101325 MPa, T)（Region1 过冷液/饱和液）
    # ⚠ 2026-09-13 修复：原调用 _IAPWS_MODULE.region1(P, T)，
    # 模块中并无公开 region1（私有 _region1 签名是 (T_K, P_MPa)），
    # 参数顺序、单位、函数名三重错误 → 每次抛异常静默回退 UNESCO。
    if _IAPWS_MODULE is not None:
        try:
            props = _IAPWS_MODULE.steam_properties(ATM_PRESSURE_MPA, T)
            if props.get('phase') == 'subcooled_liquid':
                return 1.0 / props['v']
            # 已达/超过饱和温度（T≈100°C）：取饱和液密度 rho_f，
            # 否则 steam_properties 会返回饱和蒸汽密度 0.59 kg/m³
            sat = _IAPWS_MODULE.saturation_properties(T_C=T)
            return sat['rho_f']
        except Exception:
            pass
    # Fallback: UNESCO 1983 公式（±0.1 kg/m³）
    num = (999.83952 + 16.945176 * T - 7.9870401e-3 * T**2
           - 46.170461e-6 * T**3 + 105.56302e-9 * T**4)
    den = 1.0 + 16.87985e-3 * T
    return num / den

def rho_citric_acid(w: float, T: float = 20.0) -> float:
    """
    柠檬酸（C6H8O7）水溶液密度
    w: 质量分数 0~0.70
    T: 温度 °C
    返回: kg/m³
    公式来源: 文献实验数据拟合（Apelblat & Manzurola 1999 等）
    误差: ±2 kg/m³ (w<0.6), ±5 kg/m³ (w>0.6)
    """
    c = w * 100.0  # 转为质量百分比
    # 20°C 基准密度（二阶多项式拟合实验数据）
    rho_20 = 999.8 + 4.607 * c - 0.01054 * c**2
    # 温度修正（利用纯水密度差近似）
    correction = rho_water(T) - rho_water(20.0)
    return rho_20 + correction

def rho_glucose(w: float, T: float = 20.0) -> float:
    """
    葡萄糖（C6H12O6）水溶液密度
    w: 质量分数 0~0.60
    T: 温度 °C
    返回: kg/m³
    公式来源: Perry's 手册 20°C 数据最小二乘拟合（2026-09-13 重拟合）
    拟合误差: ≤0.1 kg/m³（锚点 10/20/30/40%）
    """
    c = w * 100.0
    rho_20 = 1002.45 + 3.519 * c + 0.0205 * c**2
    correction = rho_water(T) - rho_water(20.0)
    return rho_20 + correction

def rho_sucrose(w: float, T: float = 20.0) -> float:
    """
    蔗糖（C12H22O11）水溶液密度
    w: 质量分数 0~0.67（20°C 饱和溶解度 203.9 g/100g ≈ 67.1%）
    T: 温度 °C
    返回: kg/m³
    公式来源: ICUMSA 表最小二乘拟合（2026-09-13 重拟合，三次）
    拟合误差: ≤0.2 kg/m³（锚点 10~60%）
    """
    c = w * 100.0
    rho_20 = (997.867 + 3.99471 * c + 0.00713492 * c**2
              + 1.09259e-4 * c**3)
    correction = rho_water(T) - rho_water(20.0)
    return rho_20 + correction

def rho_naoh(w: float, T: float = 20.0) -> float:
    """
    NaOH 水溶液密度
    w: 质量分数 0~0.50
    T: 温度 °C
    返回: kg/m³
    公式来源: Perry's 手册 20°C 数据最小二乘拟合（2026-09-13 重拟合，三次）
    ⚠ 旧系数 999.8+7.988c−0.03649c² 在 20% 时算出 1145（实际 1219，偏低 74）
    拟合误差: ≤0.7 kg/m³（锚点 4~50%）
    """
    c = w * 100.0
    rho_20 = (1000.92 + 10.5598 * c + 0.0330541 * c**2
              - 7.18267e-4 * c**3)
    correction = rho_water(T) - rho_water(20.0)
    return rho_20 + correction

def rho_hcl(w: float, T: float = 20.0) -> float:
    """
    盐酸（HCl）水溶液密度
    w: 质量分数 0~0.38
    T: 温度 °C
    返回: kg/m³
    公式来源: Perry's 手册 20°C 数据最小二乘拟合（2026-09-13 重拟合）
    拟合误差: ≤0.3 kg/m³（锚点 10~38%）
    """
    c = w * 100.0
    rho_20 = 996.882 + 5.02862 * c + 1.35988e-3 * c**2
    correction = rho_water(T) - rho_water(20.0)
    return rho_20 + correction

def rho_h2so4(w: float, T: float = 20.0) -> float:
    """
    硫酸（H2SO4）水溶液密度
    w: 质量分数 0~0.98
    T: 温度 °C
    返回: kg/m³
    公式来源: Perry's 手册 20°C 数据最小二乘拟合（2026-09-13 重拟合，五次）
    ⚠ 旧三阶系数在 80% 时偏低 159、90% 偏低 192
    拟合误差: ≤1.7 kg/m³（锚点 10~98%）
    """
    c = w * 100.0
    rho_20 = (1013.25 + 3.53371 * c + 0.229567 * c**2
              - 6.20113e-3 * c**3 + 8.59409e-5 * c**4
              - 4.22407e-7 * c**5)
    correction = rho_water(T) - rho_water(20.0)
    return rho_20 + correction

def rho_nacl(w: float, T: float = 20.0) -> float:
    """
    NaCl 水溶液密度
    w: 质量分数 0~0.264（20°C 饱和）
    T: 温度 °C
    返回: kg/m³
    公式来源: Perry's 手册 20°C 数据最小二乘拟合（2026-09-13 重拟合）
    ⚠ 旧系数 999.8+6.781c−0.05874c² 在 24% 时偏低 52
    拟合误差: ≤2.3 kg/m³（锚点 0~26%）
    """
    c = w * 100.0
    rho_20 = 998.132 + 7.40439 * c + 3.87041e-3 * c**2
    correction = rho_water(T) - rho_water(20.0)
    return rho_20 + correction

# ─────────────────────────── 物料配置表 ───────────────────────────

SUBSTANCE_CONFIG = {
    "纯水": {
        "func": lambda w, T: rho_water(T),
        "w_range": (0.0, 0.0),
        "T_range": (0, 100),
        "w_label": "（纯水，无需输入质量分数）",
        "w_max": 0.0,
        "formula": "IAPWS-IF97 Region1（0~350°C）| UNESCO 1983 备用",
        "ref": "IAPWS-IF97 / UNESCO 1983",
        "accuracy": "IAPWS ±0.01 kg/m³ | UNESCO ±0.1 kg/m³",
    },
    "柠檬酸溶液": {
        "func": rho_citric_acid,
        "w_range": (0.0, 0.70),
        "T_range": (0, 80),
        "w_label": "柠檬酸质量分数（0~0.70）",
        "w_max": 0.70,
        "formula": "ρ(20°C) = 999.8 + 4.607c − 0.01054c²  + 温度修正",
        "ref": "Apelblat & Manzurola (1999)；文献数据拟合",
        "accuracy": "±2 kg/m³ (w<0.6)",
    },
    "葡萄糖溶液": {
        "func": rho_glucose,
        "w_range": (0.0, 0.60),
        "T_range": (0, 80),
        "w_label": "葡萄糖质量分数（0~0.60）",
        "w_max": 0.60,
        "formula": "ρ(20°C) = 1002.45 + 3.519c + 0.0205c²  + 温度修正",
        "ref": "Perry's 手册 20°C 数据拟合（2026-09-13 重拟合）",
        "accuracy": "±1 kg/m³（锚点 10~40%）",
    },
    "蔗糖溶液": {
        "func": rho_sucrose,
        "w_range": (0.0, 0.67),
        "T_range": (0, 80),
        "w_label": "蔗糖质量分数（0~0.67，20°C 饱和）",
        "w_max": 0.67,
        "formula": "ρ(20°C) = 997.867 + 3.99471c + 0.00713492c² + 1.0926×10⁻⁴c³  + 温度修正",
        "ref": "ICUMSA 表 20°C 数据拟合（2026-09-13 重拟合）",
        "accuracy": "±1 kg/m³（锚点 10~60%）",
    },
    "NaOH 溶液": {
        "func": rho_naoh,
        "w_range": (0.0, 0.50),
        "T_range": (0, 80),
        "w_label": "NaOH 质量分数（0~0.50）",
        "w_max": 0.50,
        "formula": "ρ(20°C) = 1000.92 + 10.5598c + 0.0330541c² − 7.183×10⁻⁴c³  + 温度修正",
        "ref": "Perry's 手册 20°C 数据拟合（2026-09-13 重拟合）",
        "accuracy": "±1 kg/m³（锚点 4~50%）",
    },
    "盐酸 (HCl)": {
        "func": rho_hcl,
        "w_range": (0.0, 0.38),
        "T_range": (0, 60),
        "w_label": "HCl 质量分数（0~0.38）",
        "w_max": 0.38,
        "formula": "ρ(20°C) = 996.882 + 5.02862c + 1.360×10⁻³c²  + 温度修正",
        "ref": "Perry's 手册 20°C 数据拟合（2026-09-13 重拟合）",
        "accuracy": "±1 kg/m³（锚点 10~38%）",
    },
    "硫酸 (H₂SO₄)": {
        "func": rho_h2so4,
        "w_range": (0.0, 0.98),
        "T_range": (0, 80),
        "w_label": "H₂SO₄ 质量分数（0~0.98）",
        "w_max": 0.98,
        "formula": "ρ(20°C) = 1013.25 + 3.53371c + 0.229567c² − 6.201×10⁻³c³ + 8.594×10⁻⁵c⁴ − 4.224×10⁻⁷c⁵  + 温度修正",
        "ref": "Perry's 手册 20°C 数据拟合（2026-09-13 重拟合，五次）",
        "accuracy": "±2 kg/m³（锚点 10~98%）",
    },
    "NaCl 溶液": {
        "func": rho_nacl,
        "w_range": (0.0, 0.264),
        "T_range": (0, 80),
        "w_label": "NaCl 质量分数（0~0.264，20°C 饱和）",
        "w_max": 0.264,
        "formula": "ρ(20°C) = 998.132 + 7.40439c + 3.870×10⁻³c²  + 温度修正",
        "ref": "Perry's 手册 20°C 数据拟合（2026-09-13 重拟合）",
        "accuracy": "±2 kg/m³（锚点 0~26%）",
    },
}

# ─────────────────────────── UI 主类 ───────────────────────────



class SolutionDensityCalculator(CalculatorBase):
    """溶液密度计算器"""

    calculation_type = "solution_density"

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
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

    # ── UI 搭建 ──────────────────────────────────────────────

    def setup_ui(self):
        """设置UI - 统一布局规范"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 左侧输入区 - 使用滚动区域
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } "
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        left_widget = QWidget()
        left_widget.setStyleSheet("background: transparent;")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 顶部说明文字
        desc_label = QLabel("计算常见溶液（水、柠檬酸、葡萄糖、蔗糖、NaOH、HCl、H₂SO₄、NaCl）在不同温度和浓度下的密度，支持单点计算和温度扫描。")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc_label)

        # 单页布局：输入参数 + 温度扫描 + 公式参考（折叠）
        self._build_input_group(left_layout)
        self._build_scan_group(left_layout)
        self._build_ref_group(left_layout)

        left_layout.addStretch()

        # 设置左侧滚动区域
        left_scroll.setWidget(left_widget)
        main_layout.addWidget(left_scroll, 2)

        # 右侧结果区
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        right_widget.setMinimumWidth(300)

        # 查询结果组
        result_group = QGroupBox("查询结果")
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
            ("清空", CLEAR_BTN_STYLE, self.clear_inputs),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        right_layout.addLayout(btn_layout)

        # 计算按钮（最底部）
        calc_btn = self.make_calc_button("查 询")
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)

        main_layout.addWidget(right_widget, 1)

    # ── 输入参数组（单点计算） ────────────────────────────────

    def _build_input_group(self, parent_layout):
        """输入参数组：物料 + 质量分数 + 温度（单点计算与温度扫描共用）"""
        group = QGroupBox("输入参数")
        grid = QGridLayout(group)
        grid.setSpacing(12)
        grid.setHorizontalSpacing(10)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)

        label_style = "font-weight: bold; padding-right: 10px;"

        # 物料种类 - 第0行
        substance_label = QLabel("物料种类:")
        substance_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        substance_label.setStyleSheet(label_style)
        grid.addWidget(substance_label, 0, 0)

        self.substance_combo = QComboBox()
        self.substance_combo.setStyleSheet(COMBOBOX_STYLE)
        self.substance_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.substance_combo.addItems(list(SUBSTANCE_CONFIG.keys()))
        self.substance_combo.currentTextChanged.connect(self._on_substance_changed)
        grid.addWidget(self.substance_combo, 0, 1)

        sub_hint = QLabel("支持 8 种常见物料")
        sub_hint.setStyleSheet("font-style: italic;")
        grid.addWidget(sub_hint, 0, 2)

        # 质量分数 - 第1行
        w_label = QLabel("质量分数 w:")
        w_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        w_label.setStyleSheet(label_style)
        grid.addWidget(w_label, 1, 0)

        self.w_input = QLineEdit("0.20")
        self.w_input.setValidator(QDoubleValidator(0.0, 1.0, 6))
        self.w_input.setPlaceholderText("例如: 0.20 表示 20%")
        self.w_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.w_input, 1, 1)

        self.w_hint = QLabel("范围：0~0.70")
        self.w_hint.setStyleSheet("font-style: italic;")
        grid.addWidget(self.w_hint, 1, 2)

        # 温度 - 第2行
        T_label = QLabel("温度 T (°C):")
        T_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        T_label.setStyleSheet(label_style)
        grid.addWidget(T_label, 2, 0)

        self.T_input = QLineEdit("25")
        self.T_input.setValidator(QDoubleValidator(-10.0, 200.0, 2))
        self.T_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.T_input, 2, 1)

        T_hint = QLabel("有效范围见公式参考")
        T_hint.setStyleSheet("font-style: italic;")
        grid.addWidget(T_hint, 2, 2)

        # 当前物料公式说明
        self.formula_label = QLabel("")
        self.formula_label.setStyleSheet(
            "color: inherit; font-size: 12px; padding: 5px;"
        )
        self.formula_label.setWordWrap(True)
        grid.addWidget(self.formula_label, 3, 0, 1, 3)

        parent_layout.addWidget(group)

        # 初始化显示
        self._on_substance_changed(self.substance_combo.currentText())

    # ── 温度扫描参数组 ────────────────────────────────────────

    def _build_scan_group(self, parent_layout):
        """温度扫描参数组：物料与质量分数复用上方输入参数组"""
        group = QGroupBox("温度扫描")
        grid = QGridLayout(group)
        grid.setSpacing(12)
        grid.setHorizontalSpacing(10)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)

        label_style = "font-weight: bold; padding-right: 10px;"
        hint_style = "color: inherit; font-style: italic;"

        # 第0行：起始温度
        lbl3 = QLabel("起始温度 (°C):")
        lbl3.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl3.setStyleSheet(label_style)
        grid.addWidget(lbl3, 0, 0)

        self.scan_T_start = QLineEdit("0")
        self.scan_T_start.setValidator(QDoubleValidator(-10.0, 200.0, 1))
        self.scan_T_start.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.scan_T_start, 0, 1)

        start_hint = QLabel("扫描起始温度")
        start_hint.setStyleSheet(hint_style)
        grid.addWidget(start_hint, 0, 2)

        # 第1行：终止温度
        lbl4 = QLabel("终止温度 (°C):")
        lbl4.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl4.setStyleSheet(label_style)
        grid.addWidget(lbl4, 1, 0)

        self.scan_T_end = QLineEdit("100")
        self.scan_T_end.setValidator(QDoubleValidator(-10.0, 200.0, 1))
        self.scan_T_end.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.scan_T_end, 1, 1)

        end_hint = QLabel("大于起始")
        end_hint.setStyleSheet(hint_style)
        grid.addWidget(end_hint, 1, 2)

        # 第2行：步长
        lbl5 = QLabel("步长 (°C):")
        lbl5.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl5.setStyleSheet(label_style)
        grid.addWidget(lbl5, 2, 0)

        self.scan_step = QLineEdit("10")
        self.scan_step.setValidator(QDoubleValidator(0.1, 50.0, 1))
        self.scan_step.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.scan_step, 2, 1)

        step_hint = QLabel("温度间隔")
        step_hint.setStyleSheet(hint_style)
        grid.addWidget(step_hint, 2, 2)

        # 扫描按钮（紫色 #8e44ad，辅助按钮）
        scan_btn = QPushButton("开始扫描")
        scan_btn.setMinimumHeight(40)
        scan_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        scan_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #8e44ad; color: white; "
            "font-weight: bold; border: none; "
            "border-radius: 8px; padding: 8px; "
            "}"
            "QPushButton:hover:!checked { background-color: #7d3c98; }"
        )
        scan_btn.clicked.connect(self._run_scan)
        grid.addWidget(scan_btn, 3, 0, 1, 3)

        parent_layout.addWidget(group)

    # ── 公式参考（可折叠） ────────────────────────────────────

    def _build_ref_group(self, parent_layout):
        """公式参考：默认收起，点击标题展开全部物料的公式说明"""
        self.ref_toggle = QToolButton()
        self.ref_toggle.setText("公式参考")
        self.ref_toggle.setCheckable(True)
        self.ref_toggle.setChecked(False)
        self.ref_toggle.setArrowType(Qt.RightArrow)
        self.ref_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.ref_toggle.setStyleSheet(
            "QToolButton { border: none; font-weight: bold; "
            "font-size: 13px; color: inherit; padding: 4px; }"
        )
        self.ref_toggle.clicked.connect(self._toggle_ref)
        parent_layout.addWidget(self.ref_toggle)

        self.ref_widget = QWidget()
        ref_layout = QVBoxLayout(self.ref_widget)
        ref_layout.setContentsMargins(10, 2, 10, 2)

        ref_text = QTextEdit()
        ref_text.setReadOnly(True)
        ref_text.setMinimumHeight(240)
        ref_text.setStyleSheet(
            "QTextEdit { "
            "font-family: Consolas, 'Microsoft YaHei', monospace; "
            "font-size: 12px; "
            "border: none; background: transparent; "
            "}"
        )
        content = ""
        for name, cfg in SUBSTANCE_CONFIG.items():
            content += f"【{name}】\n"
            content += f"  浓度范围: w = {cfg['w_range'][0]:.0%} ~ {cfg['w_range'][1]:.0%}\n"
            content += f"  温度范围: {cfg['T_range'][0]} ~ {cfg['T_range'][1]} °C\n"
            content += f"  计算公式: {cfg['formula']}\n"
            content += f"  数据来源: {cfg['ref']}\n"
            content += f"  精度: {cfg['accuracy']}\n\n"
        ref_text.setPlainText(content.strip())
        ref_layout.addWidget(ref_text)

        self.ref_widget.setVisible(False)
        parent_layout.addWidget(self.ref_widget)

    def _toggle_ref(self):
        """展开/收起公式参考"""
        expanded = self.ref_toggle.isChecked()
        self.ref_toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.ref_widget.setVisible(expanded)

    # ── 事件处理 ──────────────────────────────────────────────

    def _on_substance_changed(self, name: str):
        cfg = SUBSTANCE_CONFIG.get(name, {})
        w_max = cfg.get("w_max", 1.0)
        self.w_hint.setText(f"范围：0 ~ {w_max:.0%}")
        is_water = (name == "纯水")
        self.w_input.setEnabled(not is_water)
        if is_water:
            self.w_input.setText("0")

        formula_text = (
            f"📐 公式: {cfg.get('formula', '')}\n"
            f"📚 来源: {cfg.get('ref', '')}  |  精度: {cfg.get('accuracy', '')}"
        )
        self.formula_label.setText(formula_text)

    def _calculate_single(self):
        name = self.substance_combo.currentText()
        cfg = SUBSTANCE_CONFIG.get(name)
        if not cfg:
            return

        try:
            w = float(self.w_input.text()) if self.w_input.isEnabled() else 0.0
            T = float(self.T_input.text())
        except ValueError:
            self.result_text.setPlainText("⚠ 输入无效，请检查数值格式")
            return

        w_max = cfg["w_max"]
        if w < 0 or (w_max > 0 and w > w_max):
            self.result_text.setPlainText(f"⚠ 质量分数超出范围 (0 ~ {w_max:.0%})")
            return

        try:
            rho = cfg["func"](w, T)
        except Exception as e:
            self.result_text.setPlainText(f"计算错误: {e}")
            return

        # 写入右侧结果区
        result = f"=== {name} 密度计算结果 ===\n\n"
        result += f"物料：{name}\n"
        result += f"质量分数 w = {w:.2%}\n"
        result += f"温度 T = {T:.1f} °C\n\n"
        result += f"{'─' * 30}\n\n"
        result += f"  密度 ρ = {rho:.2f} kg/m³\n"
        result += f"  密度 ρ = {rho/1000:.4f} g/cm³\n\n"
        result += f"{'─' * 30}\n"
        result += f"公式：{cfg.get('formula', '')}\n"
        result += f"来源：{cfg.get('ref', '')}\n"
        result += f"精度：{cfg.get('accuracy', '')}\n"
        self.result_text.setPlainText(result)

        # 保存到历史记录

    def _run_scan(self):
        name = self.substance_combo.currentText()
        cfg = SUBSTANCE_CONFIG.get(name)
        if not cfg:
            return

        try:
            w = float(self.w_input.text()) if self.w_input.isEnabled() else 0.0
            T_start = float(self.scan_T_start.text())
            T_end = float(self.scan_T_end.text())
            step = float(self.scan_step.text())
        except ValueError:
            self.result_text.setPlainText("⚠ 输入参数无效，请检查数值格式")
            return

        if step <= 0 or T_start >= T_end:
            self.result_text.setPlainText("⚠ 步长必须大于0，且起始温度小于终止温度")
            return

        temperatures = []
        t = T_start
        while t <= T_end + 1e-9:
            temperatures.append(round(t, 2))
            t += step

        result = f"=== {name} 温度扫描结果 (w = {w:.2%}) ===\n\n"
        result += f"{'温度(°C)':<12}{'密度(kg/m³)':<18}{'密度(g/cm³)'}\n"
        result += "-" * 50 + "\n"

        for T in temperatures:
            try:
                rho = cfg["func"](w, T)
                result += f"{T:<12.1f}{rho:<18.2f}{rho/1000:.4f}\n"
            except Exception:
                result += f"{T:<12.1f}{'计算错误':<18}\n"

        self.result_text.setPlainText(result)

    # ── 历史记录接口 ──────────────────────────────────────────

    def _get_history_data(self):
        name = self.substance_combo.currentText()
        try:
            w = float(self.w_input.text()) if self.w_input.isEnabled() else 0.0
            T = float(self.T_input.text())
        except Exception:
            return {}
        return {
            "inputs":  {"物料": name, "质量分数 w": w, "温度 T(°C)": T},
            "outputs": {"结果": self.result_text.toPlainText()},
            "notes":   "",
        }

    # ── 规范要求的方法 ──────────────────────────────────────────

    def calculate(self):
        """统一计算入口"""
        self._calculate_single()

    def _clear_inputs(self):
        """清空输入"""
        self.substance_combo.setCurrentIndex(0)
        self.w_input.setText("0.20")
        self.T_input.setText("25")
        self.result_text.clear()

    def clear_inputs(self):
        """清空输入（外部接口）"""
        self._clear_inputs()

    def get_project_info(self):
        """获取工程信息 - 返回 dict"""
        try:
            saved_info = {}
            if getattr(self, 'data_manager', None):
                saved_info = self.data_manager.get_project_info()
            return {
                'company_name': saved_info.get('company_name', ''),
                'project_number': saved_info.get('project_number', ''),
                'project_name': saved_info.get('project_name', ''),
                'subproject_name': saved_info.get('subproject_name', ''),
            }
        except Exception:
            return {'company_name': '', 'project_number': '',
                    'project_name': '', 'subproject_name': ''}

    def generate_report(self):
        """生成计算书文本（必须返回 str，导出链路依赖）"""
        try:
            result_text = self.result_text.toPlainText()
            if not result_text.strip():
                return None

            project_info = self.get_project_info()
            report = f"""══════════════════════════════════════════
          溶液密度计算书
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

  1. 溶液密度按所选物料的经验关联式计算，随温度、浓度变化
  2. 关联式适用范围以结果中标注的温度/浓度区间为准
  3. 计算结果仅供参考，实际工程需经专业工程师审核确认

---
生成于 ChemCal 工程计算模块
"""
            return report

        except Exception as e:
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "溶液密度计算")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "溶液密度计算")
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    win = SolutionDensityCalculator()
    win.setWindowTitle("溶液密度计算器 - 测试")
    win.resize(680, 580)
    win.show()
    sys.exit(app.exec())
