from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QPushButton,
    QComboBox, QGridLayout, QTextEdit, QMessageBox, QDialog,
    QDialogButtonBox, QScrollArea, QSpinBox, QButtonGroup, QCheckBox,
    QFrame, QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QDoubleValidator
from PySide6.QtSvgWidgets import QSvgWidget
import math
import re
import os
import importlib.util
from datetime import datetime
from enum import Enum
import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from svg_utils import svg_text, svg_rect, svg_line, svg_circle, svg_ellipse, svg_arrow_marker, svg_start, svg_end

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

# ==================== 枚举定义 ====================


class FlowArrangement(Enum):
    """流动方式枚举"""
    COUNTERCURRENT = "逆流"
    COCURRENT = "并流"

class HeatTransferMode(Enum):
    """传热模式枚举"""
    DIRECT = "直接计算法"
    FLUID_PARAMS = "流体参数法"
    STEAM_HEATING = "蒸汽加热法"
    INTELLIGENT = "智能选型"
    SINGLE_SIDE = "未知侧设计"

# ==================== 主界面类 ====================

class 换热器面积(CalculatorBase):
    """换热器面积计算器 - 统一UI风格版"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        
        # 初始化数据管理器
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        
        # 初始化数据
        self.specific_heat_data = self.setup_specific_heat_data()
        self.steam_properties = {}
        self.exchanger_types_data = self.setup_exchanger_types_data()
        self.flow_arrangements = list(FlowArrangement)
        self.steam_properties = {}  # 蒸汽物性数据缓存
        
        self.setup_ui()
        self.setup_mode_dependencies()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception:
            self.data_manager = None
    
    def setup_specific_heat_data(self):
        """设置流体比热容数据 - 增加常用介质"""
        return {
            "水": 4.187,
            "95%乙醇": 2.51,
            "乙二醇": 2.35,
            "导热油": 2.9,
            "汽油": 2.22,
            "空气": 1.005,
            "氨气": 2.26,
            "苯": 1.36,
            "甲醇": 2.53,
            "盐水(20%)": 3.71
        }
    
    def setup_exchanger_types_data(self):
        """设置换热器类型数据 - 基于图片信息优化"""
        return {
            "管壳式换热器": {"k_range": (300, 1200), "desc": "结构简单，适应性强，耐高压"},
            "板式换热器": {"k_range": (2000, 7000), "desc": "传热效率高，结构紧凑"},
            "螺旋板式换热器": {"k_range": (500, 2200), "desc": "不易结垢，处理含固体颗粒"},
            "套管式换热器": {"k_range": (300, 800), "desc": "结构简单，耐高压"},
            "容积式加热器": {"k_range": (500, 1500), "desc": "蒸汽加热水专用，K=1160-3950"}
        }
    
    def calculate_steam_properties_from_gauge(self, pressure_gauge_MPa):
        """
        根据表压计算蒸汽物性参数
        输入：表压 (MPa)
        返回：dict 包含 saturation_temp (°C), latent_heat (kJ/kg)
        
        优先使用 IAPWS-IF97 标准，不可用时回退到查表插值
        """
        P_abs = pressure_gauge_MPa + 0.101325  # 表压 → 绝对压力
        
        if _iapws_available and 0.001 <= P_abs <= 22.064:
            try:
                sat = _steam_iapws.saturation_properties(P_MPa=P_abs)
                return {
                    "saturation_temp": round(sat['T_C'], 1),
                    "latent_heat": round(sat['h_fg'], 1),
                    "method": "IAPWS-IF97"
                }
            except Exception:
                pass
        
        # 回退：查表插值法
        return self._steam_properties_fallback(pressure_gauge_MPa)
    
    @staticmethod
    def _steam_properties_fallback(pressure_gauge_MPa):
        """回退查表法"""
        steam_data_gauge = [
            (0.0, 100.0, 2256.4),
            (0.1, 120.2, 2201.6),
            (0.2, 133.5, 2163.2),
            (0.3, 143.6, 2133.0),
            (0.4, 151.8, 2107.4),
            (0.5, 158.8, 2084.3),
            (0.6, 165.0, 2063.0),
            (0.7, 170.4, 2043.1),
            (0.8, 175.4, 2024.3),
            (0.9, 179.9, 2006.5),
            (1.0, 184.1, 1989.8)
        ]
        
        if pressure_gauge_MPa <= steam_data_gauge[0][0]:
            return {
                "saturation_temp": steam_data_gauge[0][1],
                "latent_heat": steam_data_gauge[0][2],
                "method": "查表法(回退)"
            }
        elif pressure_gauge_MPa >= steam_data_gauge[-1][0]:
            return {
                "saturation_temp": steam_data_gauge[-1][1],
                "latent_heat": steam_data_gauge[-1][2],
                "method": "查表法(回退)"
            }
        
        for i in range(len(steam_data_gauge)-1):
            P1, T1, r1 = steam_data_gauge[i]
            P2, T2, r2 = steam_data_gauge[i+1]
            
            if P1 <= pressure_gauge_MPa <= P2:
                factor = (pressure_gauge_MPa - P1) / (P2 - P1)
                T_sat = T1 + factor * (T2 - T1)
                latent_heat = r1 + factor * (r2 - r1)
                
                return {
                    "saturation_temp": round(T_sat, 1),
                    "latent_heat": round(latent_heat, 1),
                    "method": "查表法(回退)"
                }
        
        return {
            "saturation_temp": 100.0,
            "latent_heat": 2256.4,
            "method": "查表法(回退)"
        }
    
    def setup_ui(self):
        """设置用户界面 - 与压降计算模块统一风格"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧：输入参数区域 (占2/3宽度)
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        scroll_left.setWidgetResizable(True)

        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")  # 限制最大宽度
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # 1. 首先添加说明文本
        description = QLabel(
            "基于《传热技术、设备与工业应用》原理，计算换热器传热面积，支持多种计算模式。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 2. 然后添加计算模式选择
        mode_group = QGroupBox("计算模式")
        mode_layout = QHBoxLayout(mode_group)
        
        self.mode_button_group = QButtonGroup(self)
        self.mode_buttons = {}
        
        modes = [
            ("直接计算", "已知热负荷、传热系数和温差"),
            ("流体参数", "根据流体进出口参数计算"),
            ("蒸汽加热", "使用蒸汽加热冷流体"),
            ("智能选型", "自动推荐换热器类型"),
            ("未知侧设计", "一侧参数完整，另一侧仅知入口温度")
        ]
        
        for i, (mode_name, tooltip) in enumerate(modes):
            btn = QPushButton(mode_name)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    border: 1px solid #666;
                    border-radius: 4px;
                    padding: 8px;
                    text-align: center;
                    color: black;
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
            self.mode_buttons[mode_name] = btn
        
        # 默认选择第一个
        self.mode_buttons["直接计算"].setChecked(True)
        mode_layout.addStretch()
        left_layout.addWidget(mode_group)
        
        # 3. 输入参数组 - 使用GridLayout实现整齐的布局
        input_group = QGroupBox("输入参数")
        
        # 使用GridLayout确保整齐排列
        self.input_layout = QGridLayout(input_group)
        self.input_layout.setVerticalSpacing(12)
        self.input_layout.setHorizontalSpacing(10)
        self.input_layout.setColumnStretch(0, 4)
        self.input_layout.setColumnStretch(1, 8)
        self.input_layout.setColumnStretch(2, 5)
        
        # 标签样式 - 右对齐
        label_style = """
            QLabel {
                font-weight: bold;
                padding-right: 10px;
            }
        """
        
        # 输入框和下拉菜单的固定宽度
        input_width = 400
        combo_width = 250
        
        # 输入控件字典
        self.input_widgets = {}
        self.advanced_widgets = {}
        
        # 蒸汽加热专用控件
        self.steam_flow_label = None
        self.steam_temp_label = None
        
        left_layout.addWidget(input_group)
        
        # 4. 高级参数组
        advanced_group = QGroupBox("高级参数")
        
        advanced_layout = QGridLayout(advanced_group)
        advanced_layout.setVerticalSpacing(12)
        advanced_layout.setHorizontalSpacing(10)
        
        # 安全系数
        safety_label = QLabel("安全系数:")
        safety_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        safety_label.setStyleSheet(label_style)
        advanced_layout.addWidget(safety_label, 0, 0)
        
        self.safety_factor_input = QLineEdit()
        self.safety_factor_input.setPlaceholderText("建议：1.10-1.30")
        self.safety_factor_input.setValidator(QDoubleValidator(1.0, 2.0, 2))
        self.safety_factor_input.setText("1.15")
        self.safety_factor_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        advanced_layout.addWidget(self.safety_factor_input, 0, 1)
        
        # 污垢系数
        fouling_label = QLabel("污垢系数 (m²·K/W):")
        fouling_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fouling_label.setStyleSheet(label_style)
        advanced_layout.addWidget(fouling_label, 0, 2)
        
        self.fouling_factor_input = QLineEdit()
        self.fouling_factor_input.setPlaceholderText("例如：0.0002")
        self.fouling_factor_input.setValidator(QDoubleValidator(0.00001, 0.01, 5))
        self.fouling_factor_input.setText("0.0002")
        self.fouling_factor_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        advanced_layout.addWidget(self.fouling_factor_input, 0, 3)
        
        left_layout.addWidget(advanced_group)
        
        # 5. 计算按钮
        calculate_btn = QPushButton("计算")
        calculate_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calculate_btn.clicked.connect(self.calculate)
        calculate_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                min-height: 50px; padding: 0px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219955;
            } """)
        calculate_btn.setMinimumHeight(50)
        calculate_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        left_layout.addWidget(calculate_btn)
        
        # 6. 底部按钮布局
        bottom_layout = QHBoxLayout()
        
        # 清空按钮
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_inputs)
        self.clear_btn.setMinimumHeight(50)
        self.clear_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            } """)
        
        # 下载TXT按钮
        self.download_docx_btn = QPushButton("下载计算书(DOCX)")
        self.download_docx_btn.clicked.connect(self.download_docx_report)
        self.download_docx_btn.setMinimumHeight(50)
        self.download_docx_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_docx_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            } """)
        
        # 下载PDF按钮
        self.download_pdf_btn = QPushButton("下载计算书(PDF)")
        self.download_pdf_btn.clicked.connect(self.download_pdf_report)
        self.download_pdf_btn.setMinimumHeight(50)
        self.download_pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            } """)
        
        bottom_layout.addWidget(self.clear_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.download_docx_btn)
        bottom_layout.addWidget(self.download_pdf_btn)
        left_layout.addLayout(bottom_layout)
        
        # 7. 在底部添加拉伸因子，这样放大窗口时空白会出现在这里
        left_layout.addStretch()
        
        # 右侧：结果显示区域 (占1/3宽度)
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        
        # 换热器示意图 (SVG 动态绘制)
        self.svg_widget = QSvgWidget()
        self.svg_widget.setMinimumHeight(220)
        self.svg_widget.setMaximumHeight(280)
        self.svg_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.svg_widget.setStyleSheet("""
            QSvgWidget {
                border: 1px solid #666;
                border-radius: 6px;
                background-color: white;
            }
        """)
        right_layout.addWidget(self.svg_widget)
        
        # 结果显示
        self.result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(self.result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #666;
                border-radius: 6px;
                padding: 8px;
                /* bg via theme */min-height: 300px;
            }
        """)
        result_layout.addWidget(self.result_text)
        
        right_layout.addWidget(self.result_group)
        
        # 将左右两部分添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)  # 左侧占2/3
        main_layout.addWidget(right_widget, 1)  # 右侧占1/3
    
    def setup_mode_dependencies(self):
        """设置计算模式的依赖关系"""
        # 连接模式切换信号
        self.mode_button_group.buttonClicked.connect(self.on_mode_button_clicked)
        # 初始状态 - 直接计算模式
        self.on_mode_changed("直接计算")

    # ───────────────── SVG 示意图 ─────────────────
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        """SVG 文本（委托 svg_utils）"""
        return svg_text(x, y, text, size, color, bold, center)

    def _draw_flow_port(self, parts, x, y_base, y_dir, label, temp_text, color, arrow_id):
        """流体进出口：箭头 + 标签 + 温度"""
        arrow_len = abs(y_dir)
        sign = 1 if y_dir > 0 else -1
        arrow = f'<line x1="{x}" y1="{y_base}" x2="{x}" y2="{y_base+y_dir}" stroke="{color}" stroke-width="2.5" marker-end="url(#{arrow_id})"/>'
        parts.append(arrow)
        if y_dir < 0:  # 向上
            parts.append(self._text(x, y_base+y_dir-6, label, size=10, color=color, bold=True))
            parts.append(self._text(x, y_base+y_dir+8, temp_text, size=10, color="#555"))
        else:  # 向下
            parts.append(self._text(x, y_base+y_dir+16, label, size=10, color=color, bold=True))
            parts.append(self._text(x, y_base+y_dir+30, temp_text, size=10, color="#555"))

    # ===== 五种换热器外形绘制 =====

    def _draw_body_tube(self, parts, x, y, w, h):
        """管壳式：水平圆筒 + 封头 + 管束 + 折流板"""
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#e8edf2" stroke="#4a6fa5" stroke-width="2" rx="6"/>')
        parts.append(f'<ellipse cx="{x}" cy="{y+h/2}" rx="10" ry="{h/2}" fill="#dce4ec" stroke="#4a6fa5" stroke-width="2"/>')
        parts.append(f'<ellipse cx="{x+w}" cy="{y+h/2}" rx="10" ry="{h/2}" fill="#dce4ec" stroke="#4a6fa5" stroke-width="2"/>')
        for ty in [y+18, y+34, y+50, y+66, y+82]:
            parts.append(f'<line x1="{x-6}" y1="{ty}" x2="{x+w+6}" y2="{ty}" stroke="#7f8c8d" stroke-width="1.5" stroke-dasharray="4,3"/>')
        for bx in [x+50, x+110, x+170]:
            parts.append(f'<line x1="{bx}" y1="{y+4}" x2="{bx}" y2="{y+h-4}" stroke="#4a6fa5" stroke-width="1.5"/>')

    def _draw_body_plate(self, parts, x, y, w, h):
        """板式：矩形框 + 竖线表示板片 + 交替箭头"""
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#e8edf2" stroke="#4a6fa5" stroke-width="2" rx="4"/>')
        for px in range(6):
            px_val = x + 30 + px * 35
            parts.append(f'<line x1="{px_val}" y1="{y+4}" x2="{px_val}" y2="{y+h-4}" stroke="#4a6fa5" stroke-width="1" opacity="0.5"/>')
        # 板间流道标注
        for ci, label in [(x+47, "热"), (x+82, "冷"), (x+117, "热"), (x+152, "冷"), (x+187, "热")]:
            parts.append(self._text(ci, y+h/2+3, label, size=8, color="#fff"))

    def _draw_body_spiral(self, parts, cx, cy, r):
        """螺旋板式：从中心螺旋向外"""
        for i in range(8):
            a = i * 0.8
            rr = 10 + i * 12
            ex = cx + int(rr * 0.5)
            if rr < r - 5:
                parts.append(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="#4a6fa5" stroke-width="1.5" opacity="0.6"/>')
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{4}" fill="#4a6fa5"/>')

    def _draw_body_doublepipe(self, parts, x, y, w, h):
        """套管式：内外两层圆管"""
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#e8edf2" stroke="#4a6fa5" stroke-width="2" rx="14" ry="14"/>')
        inner_h = h * 0.4
        inner_y = y + (h - inner_h) / 2
        parts.append(f'<rect x="{x+5}" y="{inner_y}" width="{w-10}" height="{inner_h}" fill="#dce4ec" stroke="#4a6fa5" stroke-width="1.5" rx="8"/>')

    def _draw_body_tank(self, parts, x, y, w, h):
        """容积式：圆筒罐 + 内部盘管"""
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#e8edf2" stroke="#4a6fa5" stroke-width="2" rx="8"/>')
        # 盘管（螺旋）
        for ci in range(4):
            cy_val = y + h * 0.3 + ci * h * 0.18
            parts.append(f'<ellipse cx="{x+w/2}" cy="{cy_val}" rx="{w*0.35}" ry="{h*0.07}" fill="none" stroke="#e74c3c" stroke-width="1.5"/>')

    def _generate_heat_exchanger_svg(self, mode="直接计算", exchanger_type="", **kwargs):
        """根据换热器类型和计算模式生成 SVG 示意图"""
        w, h = 360, 260
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
                 f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']

        body_x, body_y, body_w, body_h = 60, 72, 240, 100
        hot_in = kwargs.get('hot_in', '?')
        hot_out = kwargs.get('hot_out', '?')
        cold_in = kwargs.get('cold_in', '?')
        cold_out = kwargs.get('cold_out', '?')

        # ── 按类型画外形 ──
        if exchanger_type == "板式换热器":
            self._draw_body_plate(parts, body_x, body_y, body_w, body_h)
            hx_label = "板式换热器"
            # 板式流道：热侧上下，冷侧另一侧上下
            self._draw_flow_port(parts, body_x+40, body_y, -30, "热侧入口", f"{hot_in}°C", "#e74c3c", "arrowRed")
            self._draw_flow_port(parts, body_x+40, body_y+body_h, 30, "热侧出口", f"{hot_out}°C", "#e74c3c", "arrowRed_down")
            self._draw_flow_port(parts, body_x+body_w-40, body_y, -30, "冷侧出口", f"{cold_out}°C", "#3498db", "arrowBlue_up")
            self._draw_flow_port(parts, body_x+body_w-40, body_y+body_h, 30, "冷侧入口", f"{cold_in}°C", "#3498db", "arrowBlue")

        elif exchanger_type == "螺旋板式换热器":
            cx, cy, r = body_x+body_w/2, body_y+body_h/2, body_h/2-5
            self._draw_body_spiral(parts, int(cx), int(cy), int(r))
            hx_label = "螺旋板式换热器"
            # 螺旋：两个进出口
            self._draw_flow_port(parts, body_x+50, body_y, -30, "热侧入口", f"{hot_in}°C", "#e74c3c", "arrowRed")
            self._draw_flow_port(parts, body_x+50, body_y+body_h, 30, "热侧出口", f"{hot_out}°C", "#e74c3c", "arrowRed_down")
            self._draw_flow_port(parts, body_x+body_w-50, body_y, -30, "冷侧出口", f"{cold_out}°C", "#3498db", "arrowBlue_up")
            self._draw_flow_port(parts, body_x+body_w-50, body_y+body_h, 30, "冷侧入口", f"{cold_in}°C", "#3498db", "arrowBlue")

        elif exchanger_type == "套管式换热器":
            self._draw_body_doublepipe(parts, body_x, body_y, body_w, body_h)
            hx_label = "套管式换热器"
            # 内管/环隙
            self._draw_flow_port(parts, body_x+50, body_y, -30, "内管入口", f"{hot_in}°C", "#e74c3c", "arrowRed")
            self._draw_flow_port(parts, body_x+50, body_y+body_h, 30, "内管出口", f"{hot_out}°C", "#e74c3c", "arrowRed_down")
            self._draw_flow_port(parts, body_x+body_w-50, body_y, -30, "环隙出口", f"{cold_out}°C", "#3498db", "arrowBlue_up")
            self._draw_flow_port(parts, body_x+body_w-50, body_y+body_h, 30, "环隙入口", f"{cold_in}°C", "#3498db", "arrowBlue")

        elif exchanger_type == "容积式加热器":
            self._draw_body_tank(parts, body_x, body_y, body_w, body_h)
            hx_label = "容积式加热器"
            # 盘管入口/出口 + 罐体进出口
            self._draw_flow_port(parts, body_x+50, body_y, -30, "蒸汽入口", f"{hot_in}°C", "#e74c3c", "arrowRed")
            self._draw_flow_port(parts, body_x+50, body_y+body_h, 30, "凝液出口", f"{hot_out}°C", "#e74c3c", "arrowRed_down")
            self._draw_flow_port(parts, body_x+body_w-50, body_y, -30, "出水口", f"{cold_out}°C", "#3498db", "arrowBlue_up")
            self._draw_flow_port(parts, body_x+body_w-50, body_y+body_h, 30, "进水口", f"{cold_in}°C", "#3498db", "arrowBlue")

        else:  # 管壳式（默认）
            self._draw_body_tube(parts, body_x, body_y, body_w, body_h)
            hx_label = "管壳式换热器"
            self._draw_flow_port(parts, body_x+35, body_y, -30, "壳程入口", f"{hot_in}°C", "#e74c3c", "arrowRed")
            self._draw_flow_port(parts, body_x+35, body_y+body_h, 30, "壳程出口", f"{hot_out}°C", "#e74c3c", "arrowRed_down")
            self._draw_flow_port(parts, body_x+body_w-35, body_y, -30, "管程出口", f"{cold_out}°C", "#3498db", "arrowBlue_up")
            self._draw_flow_port(parts, body_x+body_w-35, body_y+body_h, 30, "管程入口", f"{cold_in}°C", "#3498db", "arrowBlue")

        # ── 底部信息栏 ──
        heat_load = kwargs.get('heat_load')
        area = kwargs.get('area')
        info_y = h - 14
        if heat_load is not None:
            parts.append(self._text(body_x, info_y, f"热负荷: {heat_load} kW", size=10, color="#444", center=False))
        if area is not None:
            parts.append(self._text(body_x+body_w-30, info_y, f"面积: {area} m²", size=10, color="#444", center=False))

        # ── 顶部标签：类型 + 模式 ──
        mode_names = {"直接计算": "直接换热量计算", "流体参数": "流体参数法",
                      "蒸汽加热": "蒸汽加热", "未知侧设计": "未知侧设计",
                      "智能选型": "智能选型"}
        title = hx_label
        if mode in mode_names and mode != "智能选型":
            title += f" — {mode_names[mode]}"
        parts.append(self._text(body_x+body_w/2, 12, title, size=10, color="#4a6fa5", bold=True))

        # ── 箭头定义 ──
        parts.append('''<defs>
            <marker id="arrowRed" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#e74c3c"/></marker>
            <marker id="arrowRed_down" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#e74c3c"/></marker>
            <marker id="arrowBlue" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#3498db"/></marker>
            <marker id="arrowBlue_up" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#3498db"/></marker>
        </defs>''')

        parts.append('</svg>')
        return ''.join(parts)

    def _update_svg_diagram(self):
        """根据当前计算模式 + 换热器类型 + 输入参数更新 SVG 示意图"""
        try:
            mode = self.get_current_mode()
            kwargs = {'mode': mode}

            # 换热器类型
            ex_type = self.get_widget_value("exchanger_type", "")
            if ex_type and not ex_type.startswith("-"):
                kwargs['exchanger_type'] = ex_type

            # 通用参数
            heat_load = self.get_widget_value("heat_load")
            K = self.get_widget_value("k_value", 500)

            if mode == "直接计算":
                kwargs['hot_in'] = self.get_widget_value("hot_in_temp")
                kwargs['hot_out'] = self.get_widget_value("hot_out_temp")
                kwargs['cold_in'] = self.get_widget_value("cold_in_temp")
                kwargs['cold_out'] = self.get_widget_value("cold_out_temp")
            elif mode == "流体参数":
                kwargs['hot_in'] = self.get_widget_value("hot_in_temp")
                kwargs['hot_out'] = self.get_widget_value("hot_out_temp")
                kwargs['cold_in'] = self.get_widget_value("cold_in_temp")
                kwargs['cold_out'] = self.get_widget_value("cold_out_temp")
                W_hot = self.get_widget_value("hot_flow")
                W_cold = self.get_widget_value("cold_flow")
                if W_hot: kwargs['shell_media'] = f"{W_hot} kg/h"
                if W_cold: kwargs['tube_media'] = f"{W_cold} kg/h"
            elif mode == "蒸汽加热":
                kwargs['hot_in'] = self.get_widget_value("steam_temp")
                kwargs['hot_out'] = self.get_widget_value("steam_out_temp")
                kwargs['cold_in'] = self.get_widget_value("material_in_temp")
                kwargs['cold_out'] = self.get_widget_value("material_out_temp")
                heat_load = self.get_widget_value("steam_heat_load")
            elif mode == "未知侧设计":
                kwargs['hot_in'] = self.get_widget_value("known_in_temp")
                kwargs['hot_out'] = self.get_widget_value("known_out_temp")
                kwargs['cold_in'] = self.get_widget_value("unknown_in_temp")
                kwargs['cold_out'] = self.get_widget_value("unknown_out_temp")
            elif mode == "智能选型":
                kwargs['hot_in'] = self.get_widget_value("selection_hot_in")
                kwargs['hot_out'] = self.get_widget_value("selection_hot_out")
                kwargs['cold_in'] = self.get_widget_value("selection_cold_in")
                kwargs['cold_out'] = self.get_widget_value("selection_cold_out")

            kwargs['heat_load'] = heat_load

            # 估算面积
            try:
                T_hot_in = kwargs.get('hot_in')
                T_hot_out = kwargs.get('hot_out')
                T_cold_in = kwargs.get('cold_in')
                T_cold_out = kwargs.get('cold_out')
                if all(v is not None for v in [T_hot_in, T_hot_out, T_cold_in, T_cold_out, heat_load, K]):
                    delta_hot = abs(float(T_hot_in) - float(T_hot_out))
                    delta_cold = abs(float(T_cold_out) - float(T_cold_in))
                    if delta_hot > 0 and delta_cold > 0 and delta_hot != delta_cold:
                        import math
                        lmtd = (delta_hot - delta_cold) / math.log(delta_hot / delta_cold)
                        area = (float(heat_load) * 1000) / (float(K) * lmtd)
                        kwargs['area'] = round(area, 1)
            except Exception:
                pass

            svg = self._generate_heat_exchanger_svg(**kwargs)
            self.svg_widget.load(svg.encode('utf-8'))
        except Exception:
            pass

    def on_mode_button_clicked(self, button):
        """处理计算模式按钮点击"""
        mode_text = button.text()
        self.on_mode_changed(mode_text)
    
    def get_current_mode(self):
        """获取当前选择的计算模式"""
        checked_button = self.mode_button_group.checkedButton()
        if checked_button:
            return checked_button.text()
        return "直接计算"
    
    def on_mode_changed(self, mode):
        """处理计算模式变化"""
        # 清除现有输入控件
        self.clear_widgets(self.input_layout)
        self.input_widgets.clear()
        
        # 标签样式
        label_style = """
            QLabel {
                font-weight: bold;
                padding-right: 10px;
            }
        """
        
        input_width = 400
        combo_width = 250
        
        row = 0
        
        if mode == "直接计算":
            self.setup_direct_calculation_mode(row, label_style, input_width, combo_width)
        elif mode == "流体参数":
            self.setup_fluid_parameters_mode(row, label_style, input_width, combo_width)
        elif mode == "蒸汽加热":
            self.setup_steam_heating_mode(row, label_style, input_width, combo_width)
        elif mode == "智能选型":
            self.setup_intelligent_selection_mode(row, label_style, input_width, combo_width)
        elif mode == "未知侧设计":
            self.setup_single_side_mode(row, label_style, input_width, combo_width)
    
    def setup_direct_calculation_mode(self, row, label_style, input_width, combo_width):
        """设置直接计算法界面"""
        # 热负荷 Q (kW)
        self.add_input_field(row, "热负荷 Q (kW):", "heat_load", "例如：1000", 
                            QDoubleValidator(0.1, 1000000, 1), input_width, label_style)
        row += 1

        # 温度参数
        temperatures = [
            ("热流体进口T1 (°C):", "hot_in_temp", "例如：90"),
            ("热流体出口T2 (°C):", "hot_out_temp", "例如：60"),
            ("冷流体进口t1 (°C):", "cold_in_temp", "例如：20"),
            ("冷流体出口t2 (°C):", "cold_out_temp", "例如：50")
        ]
        
        for label_text, key, placeholder in temperatures:
            self.add_input_field(row, label_text, key, placeholder,
                                QDoubleValidator(-273, 1000, 1), input_width, label_style)
            row += 1

        # 总传热系数
        self.add_k_value_section(row, input_width, combo_width, label_style)
        row += 1
        
        # 流动方式
        label = QLabel("流动方式:")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(label_style)
        self.input_layout.addWidget(label, row, 0)
        
        self.input_widgets["flow_arrangement"] = QComboBox()
        self.input_widgets["flow_arrangement"].setStyleSheet(COMBOBOX_STYLE)
        for arrangement in self.flow_arrangements:
            self.input_widgets["flow_arrangement"].addItem(arrangement.value)
        self.input_widgets["flow_arrangement"].setCurrentText("逆流")
        self.input_widgets["flow_arrangement"].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_layout.addWidget(self.input_widgets["flow_arrangement"], row, 1)
    
    def setup_fluid_parameters_mode(self, row, label_style, input_width, combo_width):
        """设置流体参数法界面"""
        # 热流体参数
        hot_params = [
            ("热流体流量W1 (kg/h):", "hot_flow", "例如：5000"),
            ("热流体进口T1 (°C):", "hot_in_temp", "例如：90"),
            ("热流体出口T2 (°C):", "hot_out_temp", "例如：60")
        ]
        
        for label_text, key, placeholder in hot_params:
            self.add_input_field(row, label_text, key, placeholder,
                                QDoubleValidator(1, 1000000, 1) if "flow" in key else QDoubleValidator(-273, 1000, 1),
                                input_width, label_style)
            row += 1
        
        # 热流体比热容
        self.add_cp_section(row, "热流体比热容 Cp1 (kJ/kg·K):", "hot_cp", "hot_cp_combo", 
                           input_width, combo_width, label_style)
        row += 1

        # 冷流体参数
        cold_params = [
            ("冷流体流量W2 (kg/h):", "cold_flow", "例如：10000"),
            ("冷流体进口t1 (°C):", "cold_in_temp", "例如：20"),
            ("冷流体出口t2 (°C):", "cold_out_temp", "例如：50")
        ]
        
        for label_text, key, placeholder in cold_params:
            self.add_input_field(row, label_text, key, placeholder,
                                QDoubleValidator(1, 1000000, 1) if "flow" in key else QDoubleValidator(-273, 1000, 1),
                                input_width, label_style)
            row += 1
        
        # 冷流体比热容
        self.add_cp_section(row, "冷流体比热容 Cp2 (kJ/kg·K):", "cold_cp", "cold_cp_combo", 
                           input_width, combo_width, label_style)
        row += 1
        
        # 总传热系数
        self.add_k_value_section(row, input_width, combo_width, label_style)
        row += 1
        
        # 流动方式
        label = QLabel("流动方式:")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(label_style)
        self.input_layout.addWidget(label, row, 0)
        
        self.input_widgets["flow_arrangement"] = QComboBox()
        self.input_widgets["flow_arrangement"].setStyleSheet(COMBOBOX_STYLE)
        for arrangement in self.flow_arrangements:
            self.input_widgets["flow_arrangement"].addItem(arrangement.value)
        self.input_widgets["flow_arrangement"].setCurrentText("逆流")
        self.input_widgets["flow_arrangement"].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_layout.addWidget(self.input_widgets["flow_arrangement"], row, 1)
    
    def setup_steam_heating_mode(self, row, label_style, input_width, combo_width):
        """设置蒸汽加热法界面"""
        # 计算类型选择
        label = QLabel("计算类型:")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(label_style)
        self.input_layout.addWidget(label, row, 0)
        
        self.input_widgets["calculation_type"] = QComboBox()
        self.input_widgets["calculation_type"].setStyleSheet(COMBOBOX_STYLE)
        self.input_widgets["calculation_type"].addItem("设计计算（计算蒸汽消耗）")
        self.input_widgets["calculation_type"].addItem("校核计算（给定蒸汽流量）")
        self.input_widgets["calculation_type"].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_widgets["calculation_type"].currentTextChanged.connect(self.on_steam_calc_type_changed)
        self.input_layout.addWidget(self.input_widgets["calculation_type"], row, 1)
        
        row += 1
        
        # 蒸汽压力
        label = QLabel("蒸汽压力 (MPa):")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(label_style)
        self.input_layout.addWidget(label, row, 0)
        
        self.input_widgets["steam_pressure"] = QLineEdit()
        self.input_widgets["steam_pressure"].setPlaceholderText("例如：0.3")
        self.input_widgets["steam_pressure"].setValidator(QDoubleValidator(0.01, 5.0, 3))
        self.input_widgets["steam_pressure"].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_widgets["steam_pressure"].textChanged.connect(self.update_steam_properties_display)
        self.input_layout.addWidget(self.input_widgets["steam_pressure"], row, 1)
        
        # 蒸汽温度显示
        self.steam_temp_label = QLabel("饱和温度: -- °C")
        self.steam_temp_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.input_layout.addWidget(self.steam_temp_label, row, 2)
        
        row += 1
        
        # 蒸汽流量（仅校核计算时显示）
        label = QLabel("蒸汽流量 (kg/h):")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(label_style)
        self.input_layout.addWidget(label, row, 0)
        
        self.input_widgets["steam_flow"] = QLineEdit()
        self.input_widgets["steam_flow"].setPlaceholderText("仅校核计算需要")
        self.input_widgets["steam_flow"].setValidator(QDoubleValidator(1, 1000000, 1))
        self.input_widgets["steam_flow"].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_widgets["steam_flow"].setEnabled(False)
        self.input_layout.addWidget(self.input_widgets["steam_flow"], row, 1)
        
        self.steam_flow_label = QLabel("（设计计算自动计算）")
        self.steam_flow_label.setStyleSheet("font-style: italic;")
        self.input_layout.addWidget(self.steam_flow_label, row, 2)
        
        row += 1

        # 冷流体参数
        cold_params = [
            ("冷流体流量 (kg/h):", "cold_flow", "例如：270000"),
            ("冷流体进口t1 (°C):", "cold_in_temp", "例如：37"),
            ("冷流体出口t2 (°C):", "cold_out_temp", "例如：70")
        ]
        
        for label_text, key, placeholder in cold_params:
            self.add_input_field(row, label_text, key, placeholder,
                                QDoubleValidator(1, 1000000, 1) if "flow" in key else QDoubleValidator(-273, 1000, 1),
                                input_width, label_style)
            row += 1
        
        # 冷流体比热容
        self.add_cp_section(row, "冷流体比热容 Cp2 (kJ/kg·K):", "cold_cp", "cold_cp_combo", 
                           input_width, combo_width, label_style)
        row += 1
        
        # 总传热系数
        self.add_k_value_section(row, input_width, combo_width, label_style)
        
    def on_steam_calc_type_changed(self, text):
        """蒸汽计算类型变化处理"""
        if "校核计算" in text:
            self.input_widgets["steam_flow"].setEnabled(True)
            self.input_widgets["steam_flow"].setPlaceholderText("请输入蒸汽流量")
            if self.steam_flow_label:
                self.steam_flow_label.setText("请输入蒸汽流量")
        else:
            self.input_widgets["steam_flow"].setEnabled(False)
            self.input_widgets["steam_flow"].clear()
            self.input_widgets["steam_flow"].setPlaceholderText("仅校核计算需要")
            if self.steam_flow_label:
                self.steam_flow_label.setText("（设计计算自动计算）")
    
    def update_steam_properties_display(self):
        """更新蒸汽物性显示"""
        try:
            pressure_text = self.input_widgets["steam_pressure"].text().strip()
            if pressure_text:
                pressure_gauge = float(pressure_text)
                
                # 直接使用表压计算
                props = self.calculate_steam_properties_from_gauge(pressure_gauge)
                
                # 更新显示
                if self.steam_temp_label:
                    self.steam_temp_label.setText(
                        f"饱和温度: {props['saturation_temp']} °C\n"
                        f"汽化潜热: {props['latent_heat']} kJ/kg"
                    )
                
                # 保存供后续使用
                self.steam_properties = props
        except ValueError:
            if self.steam_temp_label:
                self.steam_temp_label.setText("饱和温度: -- °C\n汽化潜热: -- kJ/kg")
    
    def setup_intelligent_selection_mode(self, row, label_style, input_width, combo_width):
        """设置智能选型模式界面"""
        # 操作条件
        conditions = [
            ("操作压力 (MPa):", "operating_pressure", "例如：0.5"),
            ("操作温度 (°C):", "operating_temperature", "例如：100"),
            ("流量 (kg/h):", "flow_rate", "例如：5000")
        ]
        
        for label_text, key, placeholder in conditions:
            self.add_input_field(row, label_text, key, placeholder,
                                QDoubleValidator(0.01, 35.0, 2) if "pressure" in key else 
                                QDoubleValidator(1, 1000000, 1) if "flow" in key else 
                                QDoubleValidator(-273, 1000, 1),
                                input_width, label_style)
            row += 1
        
        # 流体类型
        label = QLabel("流体类型:")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(label_style)
        self.input_layout.addWidget(label, row, 0)
        
        fluid_types = ["水/液体", "气体", "蒸汽", "粘稠流体", "腐蚀性流体"]
        self.input_widgets["fluid_type"] = QComboBox()
        self.input_widgets["fluid_type"].setStyleSheet(COMBOBOX_STYLE)
        for fluid in fluid_types:
            self.input_widgets["fluid_type"].addItem(fluid)
        self.input_widgets["fluid_type"].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_layout.addWidget(self.input_widgets["fluid_type"], row, 1)
        
        row += 1
        
        # 特殊条件
        self.input_widgets["fouling_tendency"] = QCheckBox("易结垢")
        self.input_widgets["fouling_tendency"].setStyleSheet("color: #2c3e50; padding: 5px;")
        self.input_layout.addWidget(self.input_widgets["fouling_tendency"], row, 1)
        
        self.input_widgets["high_pressure"] = QCheckBox("高压操作")
        self.input_widgets["high_pressure"].setStyleSheet("color: #2c3e50; padding: 5px;")
        self.input_layout.addWidget(self.input_widgets["high_pressure"], row, 2)
        
        row += 1
        
        self.input_widgets["corrosive"] = QCheckBox("腐蚀性")
        self.input_widgets["corrosive"].setStyleSheet("color: #2c3e50; padding: 5px;")
        self.input_layout.addWidget(self.input_widgets["corrosive"], row, 1)
        
        self.input_widgets["phase_change"] = QCheckBox("相变过程")
        self.input_widgets["phase_change"].setStyleSheet("color: #2c3e50; padding: 5px;")
        self.input_layout.addWidget(self.input_widgets["phase_change"], row, 2)
    
    def setup_single_side_mode(self, row, label_style, input_width, combo_width):
        """设置未知侧设计模式界面"""
        # ── 已知侧（完整参数）──
        known_label = QLabel("▼ 已知侧（完整参数）：")
        known_label.setStyleSheet("font-weight: bold; color: #2c3e50; padding: 5px 0;")
        self.input_layout.addWidget(known_label, row, 0, 1, 3)
        row += 1

        known_params = [
            ("流量 (kg/h):", "known_flow", "例如：5000", QDoubleValidator(1, 1000000, 1)),
            ("进口温度 (°C):", "known_in_temp", "例如：90", QDoubleValidator(-100, 1000, 1)),
            ("出口温度 (°C):", "known_out_temp", "例如：60", QDoubleValidator(-100, 1000, 1)),
        ]
        for label_text, key, placeholder, validator in known_params:
            self.add_input_field(row, label_text, key, placeholder, validator, input_width, label_style)
            row += 1

        self.add_cp_section(row, "比热容 Cp (kJ/kg·K):", "known_cp", "known_cp_combo",
                           input_width, combo_width, label_style)
        row += 1

        # ── 未知侧（仅知入口）──
        self.add_separator(row)
        row += 1

        unknown_label = QLabel("▼ 未知侧（仅知入口）：")
        unknown_label.setStyleSheet("font-weight: bold; color: #e67e22; padding: 5px 0;")
        self.input_layout.addWidget(unknown_label, row, 0, 1, 3)
        row += 1

        self.add_input_field(row, "进口温度 (°C):", "unknown_in_temp", "例如：20",
                            QDoubleValidator(-100, 1000, 1), input_width, label_style)
        row += 1

        self.add_cp_section(row, "比热容 Cp (kJ/kg·K):", "unknown_cp", "unknown_cp_combo",
                           input_width, combo_width, label_style)
        row += 1

        # ── 推算方式选择 ──
        self.add_separator(row)
        row += 1

        sub_label = QLabel("▼ 推算方式（二选一）：")
        sub_label.setStyleSheet("font-weight: bold; color: #3498db; padding: 5px 0;")
        self.input_layout.addWidget(sub_label, row, 0, 1, 3)
        row += 1

        # 子模式选择
        label = QLabel("选择推算方式:")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(label_style)
        self.input_layout.addWidget(label, row, 0)

        self.input_widgets["unknown_infer"] = QComboBox()
        self.input_widgets["unknown_infer"].setStyleSheet(COMBOBOX_STYLE)
        self.input_widgets["unknown_infer"].addItems([
            "给定出口温度 → 计算流量",
            "给定流量 → 计算出口温度"
        ])
        self.input_widgets["unknown_infer"].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_widgets["unknown_infer"].currentTextChanged.connect(self._on_single_side_infer_changed)
        self.input_layout.addWidget(self.input_widgets["unknown_infer"], row, 1)
        row += 1

        # 动态输入（根据子模式切换）
        self.add_input_field(row, "出口温度 (°C):", "unknown_out_temp", "例如：40",
                            QDoubleValidator(-100, 1000, 1), input_width, label_style)
        self._single_side_temp_row = row
        row += 1

        self.add_input_field(row, "流量 (kg/h):", "unknown_flow", "例如：10000",
                            QDoubleValidator(1, 1000000, 1), input_width, label_style)
        self._single_side_flow_row = row
        row += 1

        # 初始状态：默认"给定出口温度"，隐藏流量输入
        self.input_widgets["unknown_flow"].setEnabled(False)
        self.input_widgets["unknown_flow"].setPlaceholderText("自动计算")

        # ── 系统参数 ──
        self.add_separator(row)
        row += 1

        self.add_k_value_section(row, input_width, combo_width, label_style)
        row += 1

        # 流动方式
        label = QLabel("流动方式:")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(label_style)
        self.input_layout.addWidget(label, row, 0)

        self.input_widgets["flow_arrangement"] = QComboBox()
        self.input_widgets["flow_arrangement"].setStyleSheet(COMBOBOX_STYLE)
        for arrangement in self.flow_arrangements:
            self.input_widgets["flow_arrangement"].addItem(arrangement.value)
        self.input_widgets["flow_arrangement"].setCurrentText("逆流")
        self.input_widgets["flow_arrangement"].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_layout.addWidget(self.input_widgets["flow_arrangement"], row, 1)

    def _on_single_side_infer_changed(self, text):
        """未知侧推算方式切换——交换出口温度/流量的输入状态"""
        if "流量" in text and "给定" in text:
            # "给定流量 → 计算出口温度"
            if "unknown_flow" in self.input_widgets:
                self.input_widgets["unknown_flow"].setEnabled(True)
                self.input_widgets["unknown_flow"].setPlaceholderText("输入已知流量")
            if "unknown_out_temp" in self.input_widgets:
                self.input_widgets["unknown_out_temp"].clear()  # 切换时清除旧值
                self.input_widgets["unknown_out_temp"].setEnabled(False)
                self.input_widgets["unknown_out_temp"].setPlaceholderText("自动计算")
        else:
            # "给定出口温度 → 计算流量"
            if "unknown_out_temp" in self.input_widgets:
                self.input_widgets["unknown_out_temp"].setEnabled(True)
                self.input_widgets["unknown_out_temp"].setPlaceholderText("输入目标出口温度")
            if "unknown_flow" in self.input_widgets:
                self.input_widgets["unknown_flow"].clear()  # 切换时清除旧值
                self.input_widgets["unknown_flow"].setEnabled(False)
                self.input_widgets["unknown_flow"].setPlaceholderText("自动计算")
    
    def add_input_field(self, row, label_text, key, placeholder, validator, width, style):
        """添加输入字段辅助函数"""
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(style)
        self.input_layout.addWidget(label, row, 0)
        
        self.input_widgets[key] = QLineEdit()
        self.input_widgets[key].setPlaceholderText(placeholder)
        self.input_widgets[key].setValidator(validator)
        self.input_widgets[key].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_layout.addWidget(self.input_widgets[key], row, 1)
        
        # 添加提示标签
        hint_label = QLabel("直接输入值")
        hint_label.setStyleSheet("font-style: italic;")
        self.input_layout.addWidget(hint_label, row, 2)
    
    def add_cp_section(self, row, label_text, cp_key, combo_key, input_width, combo_width, label_style):
        """添加比热容选择部分"""
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(label_style)
        self.input_layout.addWidget(label, row, 0)
        
        self.input_widgets[cp_key] = QLineEdit()
        self.input_widgets[cp_key].setPlaceholderText("输入或选择")
        self.input_widgets[cp_key].setValidator(QDoubleValidator(0.1, 20.0, 3))
        self.input_widgets[cp_key].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_layout.addWidget(self.input_widgets[cp_key], row, 1)
        
        self.input_widgets[combo_key] = QComboBox()
        self.input_widgets[combo_key].setStyleSheet(COMBOBOX_STYLE)
        self.input_widgets[combo_key].addItem("- 选择流体类型 -")
        for fluid in self.specific_heat_data.keys():
            self.input_widgets[combo_key].addItem(fluid)
        self.input_widgets[combo_key].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_widgets[combo_key].currentTextChanged.connect(
            lambda text, cp_key=cp_key: self.on_cp_selected(text, self.input_widgets[cp_key])
        )
        self.input_layout.addWidget(self.input_widgets[combo_key], row, 2)
    
    def add_k_value_section(self, row, input_width, combo_width, label_style):
        """添加K值选择部分"""
        label = QLabel("总传热系数K (W/m²·K):")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(label_style)
        self.input_layout.addWidget(label, row, 0)
        
        self.input_widgets["k_value"] = QLineEdit()
        self.input_widgets["k_value"].setPlaceholderText("选择类型后推荐")
        self.input_widgets["k_value"].setValidator(QDoubleValidator(10, 10000, 1))
        self.input_widgets["k_value"].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_layout.addWidget(self.input_widgets["k_value"], row, 1)
        
        self.input_widgets["exchanger_type"] = QComboBox()
        self.input_widgets["exchanger_type"].setStyleSheet(COMBOBOX_STYLE)
        self.input_widgets["exchanger_type"].addItem("- 选择换热器类型 -")
        for exchanger_type in self.exchanger_types_data.keys():
            self.input_widgets["exchanger_type"].addItem(exchanger_type)
        self.input_widgets["exchanger_type"].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_widgets["exchanger_type"].currentTextChanged.connect(self.on_exchanger_type_changed)
        self.input_layout.addWidget(self.input_widgets["exchanger_type"], row, 2)
    
    def add_separator(self, row):
        """添加分隔线"""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #bdc3c7;")
        self.input_layout.addWidget(line, row, 0, 1, 3)
    
    def clear_widgets(self, layout):
        """清除布局中的所有控件"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
    
    def on_cp_selected(self, text, lineedit):
        """处理比热容选择"""
        if text.startswith("-") or not text.strip():
            return
        
        if text in self.specific_heat_data:
            cp_value = self.specific_heat_data[text]
            lineedit.setText(f"{cp_value:.3f}")
    
    def on_exchanger_type_changed(self, text):
        """处理换热器类型选择变化"""
        if text.startswith("-") or not text.strip():
            return
        
        if text in self.exchanger_types_data:
            k_range = self.exchanger_types_data[text]["k_range"]
            recommended = (k_range[0] + k_range[1]) / 2
            
            # 更新K值输入框
            if "k_value" in self.input_widgets:
                self.input_widgets["k_value"].setText(f"{recommended:.0f}")

            # 刷新 SVG 示意图
            self._update_svg_diagram()

    def get_widget_value(self, key, default=None):
        """获取控件值"""
        if key in self.input_widgets:
            widget = self.input_widgets[key]
            if isinstance(widget, QLineEdit):
                text = widget.text().strip()
                if text:
                    try:
                        return float(text)
                    except:
                        return text
            elif isinstance(widget, QComboBox):
                return widget.currentText()
            elif isinstance(widget, QCheckBox):
                return widget.isChecked()
        return default
    
    def get_advanced_value(self, key, default=None):
        """获取高级参数值"""
        if key == "safety_factor":
            text = self.safety_factor_input.text().strip()
            if text:
                try:
                    return float(text)
                except:
                    return default
            return default
        elif key == "fouling_factor":
            text = self.fouling_factor_input.text().strip()
            if text:
                try:
                    return float(text)
                except:
                    return default
            return default
        return default
    
    def validate_inputs(self, inputs, required_fields):
        """验证输入参数是否完整"""
        missing_fields = []
        for field in required_fields:
            value = inputs.get(field)
            if value is None or value == "":
                missing_fields.append(field)
        
        if missing_fields:
            return False, f"请填写以下必需参数：{', '.join(missing_fields)}"
        return True, ""
    
    def clear_inputs(self):
        """清空所有输入"""
        self.clear_widgets(self.input_layout)
        self.input_widgets.clear()
        self.safety_factor_input.setText("1.15")
        self.fouling_factor_input.setText("0.0002")
        self.result_text.clear()
        self.mode_buttons["直接计算"].setChecked(True)
        self.on_mode_changed("直接计算")
    
    def calculate(self):
        """执行计算"""
        try:
            mode = self.get_current_mode()
            
            if mode == "直接计算":
                self.calculate_mode_0()
            elif mode == "流体参数":
                self.calculate_mode_1()
            elif mode == "蒸汽加热":
                self.calculate_mode_2()
            elif mode == "未知侧设计":
                self.calculate_mode_3()
            elif mode == "智能选型":
                self.perform_intelligent_selection()
            else:
                QMessageBox.warning(self, "计算错误", "请选择计算模式")
            
            # 更新 SVG 示意图
            self._update_svg_diagram()

        except ValueError as e:
            QMessageBox.critical(self, "输入错误", f"参数输入格式错误: {str(e)}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "参数不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def _get_history_data(self):
        """提供历史记录数据"""
        mode = self.get_current_mode()
        K = self.get_widget_value("k_value")

        inputs = {"计算模式": mode, "传热系数_W_m2K": K}
        outputs = {}

        try:
            if mode == "直接计算":
                Q_heat = self.get_widget_value("heat_load")
                T1 = self.get_widget_value("hot_in_temp")
                T2 = self.get_widget_value("hot_out_temp")
                t1 = self.get_widget_value("cold_in_temp")
                t2 = self.get_widget_value("cold_out_temp")
                inputs.update({
                    "热负荷_kW": Q_heat,
                    "热流体进口温度_C": T1,
                    "热流体出口温度_C": T2,
                    "冷流体进口温度_C": t1,
                    "冷流体出口温度_C": t2,
                })
                delta_T1 = T1 - T2 if T1 is not None and T2 is not None else 0
                delta_T2 = t2 - t1 if t2 is not None and t1 is not None else 0
                lmtd = (delta_T1 - delta_T2) / math.log(delta_T1 / delta_T2) if delta_T1 != delta_T2 else (delta_T1 + delta_T2) / 2
                if Q_heat and K and lmtd:
                    area = (Q_heat * 1000) / (K * lmtd)
                    outputs = {
                        "对数平均温差_C": round(lmtd, 2),
                        "所需换热面积_m2": round(area, 2)
                    }
            elif mode == "未知侧设计":
                W_known = self.get_widget_value("known_flow")
                Tk_in = self.get_widget_value("known_in_temp")
                Tk_out = self.get_widget_value("known_out_temp")
                Cp_k = self.get_widget_value("known_cp")
                Tu_in = self.get_widget_value("unknown_in_temp")
                Tu_out = self.get_widget_value("unknown_out_temp")
                Wu = self.get_widget_value("unknown_flow")
                Cp_u = self.get_widget_value("unknown_cp")
                flow_arrangement = self.get_widget_value("flow_arrangement", "逆流")
                safety_factor = self.get_advanced_value("safety_factor", 1.15)
                infer_mode = self.get_widget_value("unknown_infer", "给定出口温度 → 计算流量")
                guess_temp = infer_mode.startswith("给定出口温度")

                direction = "加热" if (Tk_in or 0) > (Tu_in or 0) else "冷却"
                is_heating = direction == "加热"
                inputs.update({
                    "换热方向": direction,
                    "已知侧流量_kg_h": W_known,
                    "已知侧进口_C": Tk_in,
                    "已知侧出口_C": Tk_out,
                    "已知侧比热_kJ_kgK": Cp_k,
                    "未知侧进口_C": Tu_in,
                    "未知侧出口_C": Tu_out,
                    "未知侧流量_kg_h": Wu,
                    "未知侧比热_kJ_kgK": Cp_u,
                })
                if not all([W_known, Cp_k, Tk_in, Tk_out, Tu_in]):
                    return {"inputs": inputs, "outputs": outputs}

                Q_W = W_known / 3600 * Cp_k * 1000 * abs(Tk_in - Tk_out)
                Q_kW = Q_W / 1000
                outputs["热负荷_kW"] = round(Q_kW, 2)

                # 推算未知侧
                Cp_u_J = (Cp_u or 4.187) * 1000
                T_calc = Tu_in + 20  # 默认估算
                if guess_temp and Tu_out is not None:
                    dT_u = abs(Tu_out - Tu_in)
                    T_calc = Tu_out
                    if dT_u > 0.1:
                        outputs["推算流量_kg_h"] = round(Q_W / (Cp_u_J * dT_u) * 3600)
                    outputs["未知侧温差_C"] = round(dT_u, 1)
                elif Wu is not None and Wu > 0:
                    dT_u = Q_W / (Cp_u_J * Wu / 3600)
                    T_calc = Tu_in + dT_u if is_heating else Tu_in - dT_u
                    outputs["推算出口温度_C"] = round(T_calc, 1)
                    outputs["未知侧温差_C"] = round(abs(dT_u), 1)

                # LMTD（t2 优先用给定出口温度，否则用推算值）
                if is_heating:
                    T1, T2 = Tk_in, Tk_out
                    t1 = Tu_in
                    t2 = Tu_out if Tu_out else T_calc
                else:
                    T1, T2 = Tu_in, (Tu_out if Tu_out else T_calc)
                    t1, t2 = Tk_in, Tk_out

                if flow_arrangement == "逆流":
                    dT1 = T1 - t2
                    dT2 = T2 - t1
                else:
                    dT1 = T1 - t1
                    dT2 = T2 - t2

                if dT1 > 0 and dT2 > 0 and K and Q_W > 0:
                    lmtd = (dT1 - dT2) / math.log(dT1 / dT2) if dT1 != dT2 else dT1
                    A_theo = Q_W / (K * lmtd)
                    A_design = A_theo * safety_factor
                    outputs.update({
                        "LMTD_C": round(lmtd, 1),
                        "理论面积_m2": round(A_theo, 3),
                        "设计面积_m2": round(A_design, 3),
                    })
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def calculate_mode_0(self):
        """模式0：直接计算法"""
        # 获取输入值
        Q_heat = self.get_widget_value("heat_load")  # kW
        K = self.get_widget_value("k_value")  # W/m²·K
        T1 = self.get_widget_value("hot_in_temp")  # °C
        T2 = self.get_widget_value("hot_out_temp")  # °C
        t1 = self.get_widget_value("cold_in_temp")  # °C
        t2 = self.get_widget_value("cold_out_temp")  # °C
        flow_arrangement = self.get_widget_value("flow_arrangement", "逆流")
        safety_factor = self.get_advanced_value("safety_factor", 1.15)
        
        # 验证输入
        required_fields = ["heat_load", "k_value", "hot_in_temp", "hot_out_temp", 
                          "cold_in_temp", "cold_out_temp"]
        inputs = {
            "heat_load": Q_heat, "k_value": K, "hot_in_temp": T1, 
            "hot_out_temp": T2, "cold_in_temp": t1, "cold_out_temp": t2
        }
        
        is_valid, error_msg = self.validate_inputs(inputs, required_fields)
        if not is_valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            return
        
        # 数学公式计算
        try:
            # 热负荷单位转换: kW → W
            Q = Q_heat * 1000
            
            # 计算对数平均温差
            if flow_arrangement == "逆流":
                ΔT1 = T1 - t2
                ΔT2 = T2 - t1
            else:  # 并流
                ΔT1 = T1 - t1
                ΔT2 = T2 - t2
            
            if ΔT1 <= 0 or ΔT2 <= 0:
                raise ValueError(f"温度差出现负值：ΔT1={ΔT1:.1f}°C，ΔT2={ΔT2:.1f}°C")
            
            # 对数平均温差
            if abs(ΔT1 - ΔT2) < 1e-10:
                ΔT_m = ΔT1
            else:
                ΔT_m = (ΔT1 - ΔT2) / math.log(ΔT1 / ΔT2)
            
            # 传热面积
            A_theoretical = Q / (K * ΔT_m)
            A_design = A_theoretical * safety_factor
            
            # 计算面积裕度
            margin_percent = ((A_design / A_theoretical) - 1) * 100
            
            # 准备结果
            result_text = f"""═══════════
 输入参数
══════════

    计算模式: 直接计算法
    热负荷: {Q_heat:.1f} kW
    总传热系数: {K:.0f} W/(m²·K)
    热流体温度: {T1:.1f} → {T2:.1f} °C
    冷流体温度: {t1:.1f} → {t2:.1f} °C
    流动方式: {flow_arrangement}
    安全系数: {safety_factor:.2f}

══════════
计算结果
══════════

    温差分析:
    • ΔT1 = {ΔT1:.1f} °C
    • ΔT2 = {ΔT2:.1f} °C
    • 对数平均温差 ΔT_m = {ΔT_m:.1f} °C

    面积计算:
    • 理论传热面积: {A_theoretical:.3f} m²
    • 设计传热面积: {A_design:.3f} m²
    • 面积裕量: {A_design - A_theoretical:.3f} m²
    • 面积裕度: {margin_percent:.1f}%

    单位换算:
    • 理论面积: {A_theoretical * 10.7639:.1f} ft²
    • 设计面积: {A_design * 10.7639:.1f} ft²

══════════
计算说明
══════════

    • 使用对数平均温差法计算
    • 设计面积已考虑{safety_factor:.2f}倍安全系数
    • 面积裕度{margin_percent:.1f}%确保长期运行可靠性
    • 结果仅供参考，实际选型需考虑设备制造标准
"""
            
            self.result_text.setText(result_text)
            
        except ValueError as e:
            QMessageBox.warning(self, "计算错误", str(e))
    
    def calculate_mode_1(self):
        """模式1：流体参数法"""
        # 获取输入值
        W1 = self.get_widget_value("hot_flow")  # kg/h
        T1 = self.get_widget_value("hot_in_temp")  # °C
        T2 = self.get_widget_value("hot_out_temp")  # °C
        Cp1 = self.get_widget_value("hot_cp")  # kJ/kg·K
        W2 = self.get_widget_value("cold_flow")  # kg/h
        t1 = self.get_widget_value("cold_in_temp")  # °C
        t2 = self.get_widget_value("cold_out_temp")  # °C
        Cp2 = self.get_widget_value("cold_cp")  # kJ/kg·K
        K = self.get_widget_value("k_value")  # W/m²·K
        flow_arrangement = self.get_widget_value("flow_arrangement", "逆流")
        safety_factor = self.get_advanced_value("safety_factor", 1.15)
        
        # 验证输入
        required_fields = ["hot_flow", "hot_in_temp", "hot_out_temp", "hot_cp",
                          "cold_flow", "cold_in_temp", "cold_out_temp", "cold_cp", "k_value"]
        inputs = {
            "hot_flow": W1, "hot_in_temp": T1, "hot_out_temp": T2, "hot_cp": Cp1,
            "cold_flow": W2, "cold_in_temp": t1, "cold_out_temp": t2, "cold_cp": Cp2, 
            "k_value": K
        }
        
        is_valid, error_msg = self.validate_inputs(inputs, required_fields)
        if not is_valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            return
        
        # 数学公式计算
        try:
            # 单位转换
            W1_kg_s = W1 / 3600  # kg/h → kg/s
            W2_kg_s = W2 / 3600
            Cp1_J = Cp1 * 1000  # kJ/kg·K → J/kg·K
            Cp2_J = Cp2 * 1000
            
            # 热负荷计算
            Q_hot = W1_kg_s * Cp1_J * (T1 - T2)  # W
            Q_cold = W2_kg_s * Cp2_J * (t2 - t1)  # W
            
            # 检查能量平衡
            if Q_hot > 0 and Q_cold > 0:
                balance_error = abs(Q_hot - Q_cold) / max(Q_hot, Q_cold) * 100
            else:
                balance_error = 100.0
            
            # 热平衡警告
            if balance_error > 15:
                reply = QMessageBox.warning(
                    self, 
                    "热负荷不平衡",
                    f"热平衡误差较大: {balance_error:.1f}%\n"
                    f"热侧放热: {Q_hot/1000:.1f} kW\n"
                    f"冷侧吸热: {Q_cold/1000:.1f} kW\n\n"
                    "是否继续计算？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            # 设计热负荷取较小值（安全原则）
            Q_design = min(Q_hot, Q_cold)
            
            # 计算对数平均温差
            if flow_arrangement == "逆流":
                ΔT1 = T1 - t2
                ΔT2 = T2 - t1
            else:  # 并流
                ΔT1 = T1 - t1
                ΔT2 = T2 - t2
            
            if ΔT1 <= 0 or ΔT2 <= 0:
                raise ValueError("温度差出现负值，请检查进出口温度设置")
            
            # 对数平均温差
            if abs(ΔT1 - ΔT2) < 1e-10:
                ΔT_m = ΔT1
            else:
                ΔT_m = (ΔT1 - ΔT2) / math.log(ΔT1 / ΔT2)
            
            # 传热面积
            A_theoretical = Q_design / (K * ΔT_m)
            A_design = A_theoretical * safety_factor
            
            # 准备结果
            result_text = f"""═══════════
 输入参数
══════════

    计算模式: 流体参数法
    热流体流量: {W1:.0f} kg/h
    热流体温度: {T1:.1f} → {T2:.1f} °C
    热流体比热容: {Cp1:.3f} kJ/(kg·K)
    冷流体流量: {W2:.0f} kg/h
    冷流体温度: {t1:.1f} → {t2:.1f} °C
    冷流体比热容: {Cp2:.3f} kJ/(kg·K)
    总传热系数: {K:.0f} W/(m²·K)
    流动方式: {flow_arrangement}
    安全系数: {safety_factor:.2f}

══════════
计算结果
══════════

    热负荷分析:
    • 热流体放热量: {Q_hot/1000:.2f} kW
    • 冷流体吸热量: {Q_cold/1000:.2f} kW
    • 设计热负荷: {Q_design/1000:.2f} kW
    • 热平衡误差: {balance_error:.1f}%

    温差分析:
    • ΔT1 = {ΔT1:.1f} °C
    • ΔT2 = {ΔT2:.1f} °C
    • 对数平均温差 ΔT_m = {ΔT_m:.1f} °C

    面积计算:
    • 理论传热面积: {A_theoretical:.3f} m²
    • 设计传热面积: {A_design:.3f} m²
    • 面积裕量: {A_design - A_theoretical:.3f} m²

══════════
计算说明
══════════

    • 采用较小热负荷值进行设计以确保安全
    • 安全系数{safety_factor:.2f}考虑污垢及运行波动
    • 推荐定期清洗维护以保证换热效率
"""
            
            self.result_text.setText(result_text)
            
        except ValueError as e:
            QMessageBox.warning(self, "计算错误", str(e))
    
    def calculate_mode_2(self):
        """模式2：蒸汽加热法 - 修正逻辑"""
        try:
            # 获取计算类型
            calculation_type = self.get_widget_value("calculation_type", "设计计算（计算蒸汽消耗）")
            is_design_calculation = "设计计算" in calculation_type
            
            # 获取输入值
            steam_pressure = self.get_widget_value("steam_pressure")  # MPa（表压）
            
            if not is_design_calculation:
                # 校核计算：获取蒸汽流量
                steam_flow = self.get_widget_value("steam_flow")
                if steam_flow is None:
                    QMessageBox.warning(self, "输入错误", "校核计算需要输入蒸汽流量")
                    return
            
            W2 = self.get_widget_value("cold_flow")  # kg/h
            t1 = self.get_widget_value("cold_in_temp")  # °C
            t2 = self.get_widget_value("cold_out_temp")  # °C
            Cp2 = self.get_widget_value("cold_cp")  # kJ/kg·K
            K = self.get_widget_value("k_value")  # W/m²·K
            safety_factor = self.get_advanced_value("safety_factor", 1.15)
            
            # 验证输入
            required_fields = ["steam_pressure", "cold_flow", "cold_in_temp", 
                            "cold_out_temp", "cold_cp", "k_value"]
            
            if not is_design_calculation:
                required_fields.append("steam_flow")
            
            inputs = {
                "steam_pressure": steam_pressure, 
                "cold_flow": W2, "cold_in_temp": t1, "cold_out_temp": t2, 
                "cold_cp": Cp2, "k_value": K
            }
            
            if not is_design_calculation:
                inputs["steam_flow"] = steam_flow
            
            is_valid, error_msg = self.validate_inputs(inputs, required_fields)
            if not is_valid:
                QMessageBox.warning(self, "输入错误", error_msg)
                return
            
            # 1. 计算蒸汽物性（使用表压）
            steam_props = self.calculate_steam_properties_from_gauge(steam_pressure)
            T_steam = steam_props["saturation_temp"]
            steam_latent_heat = steam_props["latent_heat"]  # kJ/kg
            
            # 2. 单位转换
            W2_kg_s = W2 / 3600  # kg/h → kg/s
            Cp2_J = Cp2 * 1000  # kJ/kg·K → J/kg·K
            steam_latent_heat_J = steam_latent_heat * 1000  # kJ/kg → J/kg
            
            # 3. 计算冷流体热负荷
            Q_cold = W2_kg_s * Cp2_J * (t2 - t1)  # W
            
            if is_design_calculation:
                # 设计计算：计算理论蒸汽消耗量
                steam_consumption = Q_cold * 3600 / steam_latent_heat_J  # kg/h
                Q_steam = steam_consumption / 3600 * steam_latent_heat_J  # W
                balance_error = 0.0  # 设计计算时假设完美平衡
                design_q = Q_cold
                steam_flow_used = steam_consumption
                calculation_note = "设计计算：根据冷流体需求计算蒸汽消耗"
            else:
                # 校核计算：使用输入的蒸汽流量
                steam_flow_kg_s = steam_flow / 3600  # kg/h → kg/s
                Q_steam = steam_flow_kg_s * steam_latent_heat_J  # W
                steam_consumption = steam_flow  # 使用输入的蒸汽流量
                
                # 计算热平衡误差
                if Q_steam > 0 and Q_cold > 0:
                    balance_error = abs(Q_steam - Q_cold) / max(Q_steam, Q_cold) * 100
                else:
                    balance_error = 100.0
                
                # 设计热负荷取较小值（安全原则）
                design_q = min(Q_steam, Q_cold)
                steam_flow_used = steam_flow
                calculation_note = f"校核计算：给定蒸汽流量{steam_flow:.0f} kg/h"
            
            # 4. 检查冷流体出口温度
            if t2 >= T_steam:
                QMessageBox.warning(self, "温度错误", 
                    f"冷流体出口温度{t2:.1f}°C不能高于蒸汽饱和温度{T_steam:.1f}°C")
                return
            
            # 5. 温差计算
            ΔT1 = T_steam - t1
            ΔT2 = T_steam - t2
            
            # 对数平均温差
            if abs(ΔT1 - ΔT2) < 1e-10:
                ΔT_m = ΔT1
            else:
                ΔT_m = (ΔT1 - ΔT2) / math.log(ΔT1 / ΔT2)
            
            # 6. 传热面积计算
            A_theoretical = design_q / (K * ΔT_m)
            A_design = A_theoretical * safety_factor
            
            # 7. 准备结果
            mode_text = "蒸汽加热法（设计计算）" if is_design_calculation else "蒸汽加热法（校核计算）"
            P_abs = steam_pressure + 0.101325  # 表压转绝对压力
            steam_method = steam_props.get("method", "未知")
            
            result_text = f"""═══════════
 输入参数
══════════

    计算模式: {mode_text}
    蒸汽压力: {steam_pressure:.3f} MPa（表压）
    蒸汽绝对压力: {P_abs:.3f} MPa（绝对）
{f"    蒸汽流量: {steam_flow_used:.0f} kg/h" if not is_design_calculation else ""}
    冷流体流量: {W2:.0f} kg/h
    冷流体温度: {t1:.1f} → {t2:.1f} °C
    冷流体比热容: {Cp2:.3f} kJ/(kg·K)
    总传热系数: {K:.0f} W/(m²·K)
    安全系数: {safety_factor:.2f}

══════════
计算结果
══════════

    蒸汽参数:
    • 饱和温度: {T_steam:.1f} °C
    • 汽化潜热: {steam_latent_heat:.0f} kJ/kg

    热负荷分析:
    • 冷流体吸热量: {Q_cold/1000:.2f} kW
    • 蒸汽放热量: {Q_steam/1000:.2f} kW
    • 设计热负荷: {design_q/1000:.2f} kW
{f"    • 热平衡误差: {balance_error:.1f}%" if not is_design_calculation else ""}
    • 理论蒸汽消耗: {steam_consumption:.0f} kg/h

    温差分析:
    • ΔT1 (蒸汽-冷流体进口): {ΔT1:.1f} °C
    • ΔT2 (蒸汽-冷流体出口): {ΔT2:.1f} °C
    • 对数平均温差 ΔT_m = {ΔT_m:.1f} °C

    面积计算:
    • 理论传热面积: {A_theoretical:.3f} m²
    • 设计传热面积: {A_design:.3f} m²
    • 面积裕量: {A_design - A_theoretical:.3f} m²
    • 面积裕度: {((A_design/A_theoretical)-1)*100:.1f}%

══════════
计算说明
══════════

    • 蒸汽压力为表压，绝对压力 = 表压 + 0.101325 MPa
    • 设计面积已考虑{safety_factor:.2f}倍安全系数
    • 面积裕度{((A_design/A_theoretical)-1)*100:.1f}%确保长期运行可靠性
    • 蒸汽加热器设计时需考虑冷凝水排放问题
    • 蒸汽物性数据来源: {steam_method}
"""
            
            self.result_text.setText(result_text)
            
        except ValueError as e:
            QMessageBox.warning(self, "计算错误", str(e))
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"蒸汽加热计算失败: {str(e)}")
    
    def perform_intelligent_selection(self):
        """智能选型"""
        # 获取输入值
        pressure = self.get_widget_value("operating_pressure")  # MPa
        temperature = self.get_widget_value("operating_temperature")  # °C
        flow_rate = self.get_widget_value("flow_rate")  # kg/h
        fluid_type = self.get_widget_value("fluid_type", "水/液体")
        fouling_tendency = self.get_widget_value("fouling_tendency", False)
        high_pressure = self.get_widget_value("high_pressure", False)
        corrosive = self.get_widget_value("corrosive", False)
        phase_change = self.get_widget_value("phase_change", False)
        
        # 验证输入
        required_fields = ["operating_pressure", "operating_temperature", "flow_rate"]
        inputs = {
            "operating_pressure": pressure, 
            "operating_temperature": temperature, 
            "flow_rate": flow_rate
        }
        
        is_valid, error_msg = self.validate_inputs(inputs, required_fields)
        if not is_valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            return
        
        # 智能选型逻辑
        recommendations = []
        
        for ex_type, data in self.exchanger_types_data.items():
            score = 0
            reasons = []
            
            # 压力适应性评分
            k_min, k_max = data["k_range"]
            pressure_limit = 10.0 if ex_type in ["管壳式换热器", "套管式换热器"] else 2.5
            
            if pressure <= pressure_limit:
                score += 3
                reasons.append(f"压力适应性好")
            elif pressure <= pressure_limit * 1.5:
                score += 1
                reasons.append(f"压力适应性一般")
            
            # 温度适应性评分
            temp_limit = 500 if ex_type == "管壳式换热器" else 200
            if temperature <= temp_limit:
                score += 3
                reasons.append(f"温度适应性好")
            
            # 流体类型匹配
            if "蒸汽" in fluid_type and "容积式" in ex_type:
                score += 2
                reasons.append("蒸汽加热专用")
            
            if "液体" in fluid_type and ex_type in ["板式换热器", "螺旋板式换热器"]:
                score += 1
                reasons.append("液体传热效率高")
            
            # 特殊条件处理
            if fouling_tendency and ex_type in ["螺旋板式换热器", "套管式换热器"]:
                score += 2
                reasons.append("防结垢设计")
            
            if high_pressure and ex_type in ["管壳式换热器", "套管式换热器"]:
                score += 2
                reasons.append("耐高压结构")
            
            if corrosive and ex_type in ["板式换热器"]:
                score += 1
                reasons.append("可选用耐蚀材料")
            
            if phase_change and ex_type == "管壳式换热器":
                score += 2
                reasons.append("相变传热适用")
            
            recommendations.append({
                "type": ex_type,
                "score": score,
                "reasons": reasons,
                "k_range": data["k_range"],
                "description": data["desc"]
            })
        
        # 排序并筛选
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        top_recommendations = [r for r in recommendations if r["score"] > 0][:4]
        
        # 准备结果
        result_text = f"""═══════════
 输入工况
══════════

    操作压力: {pressure:.2f} MPa
    操作温度: {temperature:.0f} °C
    流量: {flow_rate:.0f} kg/h
    流体类型: {fluid_type}
    特殊条件: {f"易结垢 " if fouling_tendency else ""}{f"高压 " if high_pressure else ""}{f"腐蚀性 " if corrosive else ""}{f"相变 " if phase_change else ""}

══════════
推荐换热器类型
══════════

"""
        
        if not top_recommendations:
            result_text += "未找到合适的换热器类型，请调整工况条件。\n"
        else:
            for i, rec in enumerate(top_recommendations, 1):
                score_percent = rec["score"] / 12 * 100
                result_text += f"{i}. {rec['type']} (匹配度: {score_percent:.0f}%)\n"
                result_text += f"   传热系数范围: {rec['k_range'][0]}-{rec['k_range'][1]} W/(m²·K)\n"
                result_text += f"   特点: {rec['description']}\n"
                if rec['reasons']:
                    result_text += f"   推荐理由: {', '.join(rec['reasons'])}\n"
                result_text += "\n"
        
        result_text += """══════════
选型建议
══════════

    通用原则:
    • 匹配度>80%的类型可作为首选
    • 考虑设备投资和运行维护成本
    • 腐蚀性介质需特别关注材料选择
    • 易结垢流体优先选择易清洗结构

    下一步:
    • 根据推荐类型返回相应模式进行详细计算
    • 咨询设备制造商获取具体技术参数
    • 考虑安装空间和管道布置限制
"""
        
        self.result_text.setText(result_text)
    
    def calculate_mode_3(self):
        """模式3：未知侧设计——一侧参数完整，另一侧仅知入口"""
        try:
            # ── 读取输入 ──
            # 自动判断换热方向：已知侧温度高 → 加热；已知侧温度低 → 冷却
            W_known = self.get_widget_value("known_flow")      # kg/h
            T_known_in = self.get_widget_value("known_in_temp")   # °C
            T_known_out = self.get_widget_value("known_out_temp") # °C
            Cp_known = self.get_widget_value("known_cp")          # kJ/kg·K

            T_unknown_in = self.get_widget_value("unknown_in_temp")  # °C
            Cp_unknown = self.get_widget_value("unknown_cp")          # kJ/kg·K

            is_heating = T_known_in > T_unknown_in  # 已知侧进口温度 > 未知侧进口 → 加热

            # 推断方式
            infer_mode = self.get_widget_value("unknown_infer", "给定出口温度 → 计算流量")
            guess_temp = infer_mode.startswith("给定出口温度")

            T_unknown_out = None
            W_unknown = None
            if guess_temp:
                T_unknown_out = self.get_widget_value("unknown_out_temp")
            else:
                W_unknown = self.get_widget_value("unknown_flow")

            # 系统参数
            K = self.get_widget_value("k_value")  # W/m²·K
            flow_arrangement = self.get_widget_value("flow_arrangement", "逆流")
            safety_factor = self.get_advanced_value("safety_factor", 1.15)

            # ── 验证 ──
            required = ["known_flow", "known_in_temp", "known_out_temp", "known_cp",
                       "unknown_in_temp", "unknown_cp", "k_value"]
            if guess_temp:
                required.append("unknown_out_temp")
            else:
                required.append("unknown_flow")

            inputs = {
                "known_flow": W_known, "known_in_temp": T_known_in,
                "known_out_temp": T_known_out, "known_cp": Cp_known,
                "unknown_in_temp": T_unknown_in, "unknown_cp": Cp_unknown, "k_value": K
            }
            if guess_temp:
                inputs["unknown_out_temp"] = T_unknown_out
            else:
                inputs["unknown_flow"] = W_unknown

            is_valid, error_msg = self.validate_inputs(inputs, required)
            if not is_valid:
                QMessageBox.warning(self, "输入错误", error_msg)
                return

            # ── 单位转换 ──
            W_known_kg_s = W_known / 3600
            Cp_known_J = Cp_known * 1000
            Cp_unknown_J = Cp_unknown * 1000

            # ── 已知侧热负荷 ──
            Q_design_W = abs(W_known_kg_s * Cp_known_J * (T_known_in - T_known_out))
            Q_design_kW = Q_design_W / 1000

            if Q_design_kW < 0.001:
                QMessageBox.warning(self, "输入错误", "已知侧进出口温差为零，热负荷为零")
                return

            # ── 推算未知侧 ──
            if guess_temp:
                # 给定出口温度 → 反算流量
                dT_unknown = abs(T_unknown_out - T_unknown_in)
                if dT_unknown < 0.1:
                    QMessageBox.warning(self, "输入错误",
                        f"未知侧进出口温差仅 {dT_unknown:.1f}°C，"
                        f"计算出的流量会极大。请增大目标温差。")
                    return
                W_unknown = Q_design_W / (Cp_unknown_J * dT_unknown) * 3600  # kg/h
            else:
                # 给定流量 → 反算出口温度
                W_unknown_kg_s = W_unknown / 3600
                dT_unknown = Q_design_W / (Cp_unknown_J * W_unknown_kg_s)
                if is_heating:
                    T_unknown_out = T_unknown_in + dT_unknown  # 未知侧是冷侧，升温
                else:
                    T_unknown_out = T_unknown_in - dT_unknown  # 未知侧是热侧，降温

            # ── 检查温度合理性（出口温度不能反向超过进口） ──
            if is_heating and T_unknown_out <= T_unknown_in:
                QMessageBox.warning(self, "温度不合理",
                    f"未知侧出口温度 {T_unknown_out:.1f}°C 低于进口 {T_unknown_in:.1f}°C。\n"
                    f"(加热模式下冷侧应升温，请检查流量是否过大)")
                return
            if (not is_heating) and T_unknown_out >= T_unknown_in:
                QMessageBox.warning(self, "温度不合理",
                    f"未知侧出口温度 {T_unknown_out:.1f}°C 高于进口 {T_unknown_in:.1f}°C。\n"
                    f"(冷却模式下热侧应降温，请检查流量是否过大)")
                return

            # ── 分配冷热侧变量名（统一后续计算） ──
            if is_heating:
                T1, T2 = T_known_in, T_known_out      # 热侧
                t1, t2 = T_unknown_in, T_unknown_out   # 冷侧
                side_label, unknow_label = "热侧（已知）", "冷侧（推算）"
            else:
                T1, T2 = T_unknown_in, T_unknown_out   # 热侧
                t1, t2 = T_known_in, T_known_out       # 冷侧
                side_label, unknow_label = "冷侧（已知）", "热侧（推算）"

            # ── LMTD ──
            if flow_arrangement == "逆流":
                dT1 = T1 - t2
                dT2 = T2 - t1
            else:
                dT1 = T1 - t1
                dT2 = T2 - t2

            if dT1 <= 0 or dT2 <= 0:
                QMessageBox.warning(self, "温度交叉",
                    f"温差出现负值（ΔT1={dT1:.1f}, ΔT2={dT2:.1f}）。\n"
                    f"请调整出口温度或流量参数。")
                return

            if abs(dT1 - dT2) < 1e-10:
                dT_m = dT1
            else:
                dT_m = (dT1 - dT2) / math.log(dT1 / dT2)

            # ── 面积 ──
            A_theo = Q_design_W / (K * dT_m)
            A_design = A_theo * safety_factor

            # ── 结果输出 ──
            if guess_temp:
                infer_note = f"给定出口温度 {T_unknown_out:.1f}°C，推算所需流量 {W_unknown:.0f} kg/h"
            else:
                infer_note = f"给定流量 {W_unknown:.0f} kg/h，推算出口温度 {T_unknown_out:.1f}°C"

            direction_text = "加热" if is_heating else "冷却"

            result_text = f"""═══════════
  输入参数
══════════

    计算模式: 未知侧设计
    换热方向: {direction_text}
    {side_label}:
    • 流量: {W_known:.0f} kg/h
    • 温度: {T_known_in:.1f} → {T_known_out:.1f} °C
    • 比热容: {Cp_known:.3f} kJ/(kg·K)
    {unknow_label}:
    • 进口温度: {T_unknown_in:.1f} °C
    • 比热容: {Cp_unknown:.3f} kJ/(kg·K)
    • {infer_note}
    总传热系数: {K:.0f} W/(m²·K)
    流动方式: {flow_arrangement}
    安全系数: {safety_factor:.2f}

══════════
  计算结果
══════════

    热负荷:
    • 计算热负荷: {Q_design_kW:.1f} kW

    未知侧推算:
    • 推算流量: {W_unknown:.0f} kg/h
    • 推算出口温度: {T_unknown_out:.1f} °C
    • 温差: {abs(T_unknown_out - T_unknown_in):.1f} °C

    温差分析:
    • ΔT1 = {dT1:.1f} °C
    • ΔT2 = {dT2:.1f} °C
    • LMTD = {dT_m:.1f} °C

    面积:
    • 理论面积: {A_theo:.3f} m²
    • 设计面积: {A_design:.3f} m²
    • 裕量: {A_design - A_theo:.3f} m²

══════════
  计算说明
══════════

    • 已知侧热负荷 Q = W × Cp × |ΔT|
    • 未知侧参数由 Q 和给定条件反推
    • 采用逆流/并流 LMTD 法计算面积
    • 安全系数 {safety_factor:.2f} 考虑污垢和波动
    • 实际选型时应咨询设备厂家确认
"""

            self.result_text.setText(result_text)

        except ValueError as e:
            QMessageBox.warning(self, "计算错误", str(e))
        except ZeroDivisionError:
            QMessageBox.warning(self, "计算错误", "出现除零错误，请检查输入参数")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算异常: {str(e)}")
    
    # ==================== 报告生成功能 ====================
    
    def get_project_info(self):
        """获取工程信息"""
        try:
            # 简化的工程信息对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("工程信息")
            dialog.setFixedSize(400, 300)
            
            layout = QVBoxLayout(dialog)
            
            title = QLabel("请输入工程信息")
            title.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
            layout.addWidget(title)
            
            company_layout = QHBoxLayout()
            company_label = QLabel("公司名称:")
            company_label.setFixedWidth(80)
            company_input = QLineEdit()
            company_input.setPlaceholderText("例如：XX工程公司")
            company_layout.addWidget(company_label)
            company_layout.addWidget(company_input)
            layout.addLayout(company_layout)
            
            project_layout = QHBoxLayout()
            project_label = QLabel("项目名称:")
            project_label.setFixedWidth(80)
            project_input = QLineEdit()
            project_input.setPlaceholderText("例如：化工厂换热系统")
            project_layout.addWidget(project_label)
            project_layout.addWidget(project_input)
            layout.addLayout(project_layout)
            
            designer_layout = QHBoxLayout()
            designer_label = QLabel("设计人员:")
            designer_label.setFixedWidth(80)
            designer_input = QLineEdit()
            designer_input.setPlaceholderText("例如：张工")
            designer_layout.addWidget(designer_label)
            designer_layout.addWidget(designer_input)
            layout.addLayout(designer_layout)
            
            date_layout = QHBoxLayout()
            date_label = QLabel("计算日期:")
            date_label.setFixedWidth(80)
            date_input = QLineEdit()
            date_input.setText(datetime.now().strftime('%Y-%m-%d'))
            date_input.setReadOnly(True)
            date_layout.addWidget(date_label)
            date_layout.addWidget(date_input)
            layout.addLayout(date_layout)
            
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            if dialog.exec() == QDialog.Accepted:
                return {
                    'company_name': company_input.text().strip() or "未填写",
                    'project_name': project_input.text().strip() or "换热器设计",
                    'designer': designer_input.text().strip() or "设计人员",
                    'date': date_input.text()
                }
            else:
                return None
                    
        except Exception as e:
            print(f"获取工程信息失败: {e}")
            return {
                'company_name': "换热器设计",
                'project_name': "换热器计算",
                'designer': "设计人员",
                'date': datetime.now().strftime('%Y-%m-%d')
            }
    
    def generate_report(self):
        """生成计算书"""
        try:
            result_text = self.result_text.toPlainText()
            
            if not result_text or "计算结果" not in result_text:
                QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
                return None
                
            project_info = self.get_project_info()
            if not project_info:
                return None
            
            current_mode = self.get_current_mode()
            
            report = f"""工程计算书 - 换热器面积计算
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
计算工具: ChemCal 工程计算模块
========================================

"""
            report += result_text
            
            # 添加工程信息部分
            report += f"""══════════
 工程信息
══════════

    公司名称: {project_info['company_name']}
    项目名称: {project_info['project_name']}
    设计人员: {project_info['designer']}
    计算日期: {project_info['date']}

══════════
计算书标识
══════════

    计算书编号: HE-{datetime.now().strftime('%Y%m%d')}-001
    版本: 1.0
    状态: 正式计算书

══════════
备注说明
══════════

    1. 本计算书基于《传热技术、设备与工业应用》原理
    2. 计算结果仅供参考，实际设计需考虑详细工况
    3. 重要工程参数应经专业工程师审核确认
    4. 计算条件变更时应重新进行计算

---
生成于 ChemCal 工程计算模块
"""
            return report
            
        except Exception as e:
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "换热器面积")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "换热器面积")
    def process_content_for_pdf(self, content):
        """处理内容，使其适合PDF显示"""
        # 替换单位符号
        content = content.replace("m²", "m2")
        content = content.replace("W/(m²·K)", "W/(m2·K)")
        content = content.replace("kJ/(kg·K)", "kJ/(kg·K)")
        
        return content

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = 换热器面积()
    calculator.resize(1200, 800)
    calculator.setWindowTitle("换热器面积计算器 v2.0")
    calculator.show()
    
    sys.exit(app.exec())