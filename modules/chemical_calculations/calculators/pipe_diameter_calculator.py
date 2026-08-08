from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QFrame,
    QScrollArea, QDialog, QSpinBox, QButtonGroup, QGridLayout,
    QFileDialog, QDialogButtonBox, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
from PySide6.QtSvgWidgets import QSvgWidget
import math
import re
from datetime import datetime
import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K, G, ATM_PRESSURE_MPA, WATER_DENSITY, WATER_CP, load_steam_iapws, get_steam_props
from svg_utils import svg_text
# DOCX 报告导出

class 管径计算(CalculatorBase):
    """管道直径计算器 - 基于表格数据（统一UI风格版）"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.fluid_ranges = {}
        self.fluid_data = {}
        
        # 使用传入的数据管理器或创建新的
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        
        self.setup_ui()
        self.setup_fluid_ranges()
        self.setup_fluid_options()
        self.setup_mode_dependencies()
        self._update_svg_diagram()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    def init_data_manager(self):
        """初始化数据管理器 - 使用单例模式"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
            print("使用共享的数据管理器实例")
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None
    
    def setup_fluid_ranges(self):
        """根据化工管路设计手册表1.3-1设置流体对应的参数范围"""
        self.fluid_ranges["饱和蒸汽"] = {
            "DN>200": {"velocity": (30, 40), "flow": (0, 0), "pressure": (0.1, 12), "flow_unit": "t/h"},
            "100<DN<200": {"velocity": (25, 35), "flow": (0, 0), "pressure": (0.1, 12), "flow_unit": "t/h"},
            "DN<100": {"velocity": (15, 30), "flow": (0, 0), "pressure": (0.1, 12), "flow_unit": "t/h"},
            "P<1MPa": {"velocity": (15, 20), "flow": (0, 0), "pressure": (0.1, 1), "flow_unit": "t/h"},
            "1MPa<P<4MPa": {"velocity": (20, 40), "flow": (0, 0), "pressure": (1, 4), "flow_unit": "t/h"},
            "4MPa<P<12MPa": {"velocity": (40, 60), "flow": (0, 0), "pressure": (4, 12), "flow_unit": "t/h"}
        }

        self.fluid_ranges["水及粘度相似的液体"] = {
            "P=0.1~0.3MPa": {"velocity": (0.5, 2), "flow": (0, 0), "pressure": (0.1, 0.3), "flow_unit": "m³/h"},
            "P≤1MPa": {"velocity": (0.5, 3), "flow": (0, 0), "pressure": (0.1, 1), "flow_unit": "m³/h"},
            "P≤8MPa": {"velocity": (2, 3), "flow": (0, 0), "pressure": (0.1, 8), "flow_unit": "m³/h"},
            "P≤20~30MPa": {"velocity": (2, 3.5), "flow": (0, 0), "pressure": (20, 30), "flow_unit": "m³/h"},
            "往复式泵吸入管": {"velocity": (0.5, 1.5), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "往复式泵排出管": {"velocity": (1, 2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "离心泵吸入管(常温)": {"velocity": (1.5, 2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "离心泵排出管(70~110℃)": {"velocity": (0.5, 1.5), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "离心泵排出管": {"velocity": (1.5, 3), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "高压离心泵排出管": {"velocity": (3, 3.5), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "齿轮泵吸入管": {"velocity": (0, 1), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "齿轮泵排出管": {"velocity": (1, 2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        self.fluid_ranges["自来水"] = {
            "主管P=0.3MPa": {"velocity": (1.5, 3.5), "flow": (0, 0), "pressure": (0.3, 0.3), "flow_unit": "m³/h"},
            "支管P=0.3MPa": {"velocity": (1, 1.5), "flow": (0, 0), "pressure": (0.3, 0.3), "flow_unit": "m³/h"}
        }
        
        self.fluid_ranges["压缩气体"] = {
            "P≤0.3MPa": {"velocity": (8, 12), "flow": (0, 0), "pressure": (0.1, 0.3), "flow_unit": "Nm³/h"},
            "P=0.3~0.6MPa": {"velocity": (10, 20), "flow": (0, 0), "pressure": (0.3, 0.6), "flow_unit": "Nm³/h"},
            "P=0.6~1MPa": {"velocity": (10, 15), "flow": (0, 0), "pressure": (0.6, 1), "flow_unit": "Nm³/h"},
            "P=1~2MPa": {"velocity": (8, 12), "flow": (0, 0), "pressure": (1, 2), "flow_unit": "Nm³/h"},
            "P=2~3MPa": {"velocity": (3, 8), "flow": (0, 0), "pressure": (2, 3), "flow_unit": "Nm³/h"},
            "P=3~30MPa": {"velocity": (0.5, 3), "flow": (0, 0), "pressure": (3, 30), "flow_unit": "Nm³/h"}
        }
        
        self.fluid_ranges["锅炉给水"] = {
            "P>0.8MPa": {"velocity": (1.2, 3.5), "flow": (0, 0), "pressure": (0.8, 10), "flow_unit": "m³/h"}
        }
        
        self.fluid_ranges["蒸汽冷凝液"] = {
            "蒸汽冷凝液": {"velocity": (0.5, 1.5), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        self.fluid_ranges["冷凝水"] = {
            "自流": {"velocity": (0.2, 0.5), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 过热蒸汽
        self.fluid_ranges["过热蒸汽"] = {
            "DN>200": {"velocity": (40, 60), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "t/h"},
            "100<DN<200": {"velocity": (30, 50), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "t/h"},
            "DN<100": {"velocity": (20, 40), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "t/h"}
        }
        
        # 二次蒸汽
        self.fluid_ranges["二次蒸汽"] = {
            "二次蒸汽受利用时": {"velocity": (15, 30), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "t/h"},
            "二次蒸汽不利用时": {"velocity": (60, 60), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "t/h"}
        }
        
        # 高压乏汽
        self.fluid_ranges["高压乏汽"] = {
            "高压乏汽": {"velocity": (80, 100), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "t/h"}
        }
        
        # 乏汽
        self.fluid_ranges["乏汽"] = {
            "排气管,从受压容器排出": {"velocity": (80, 80), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "t/h"},
            "从无压容器排出": {"velocity": (15, 30), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "t/h"}
        }

        # 氧气
        self.fluid_ranges["氧气"] = {
            "P=0~0.05MPa": {"velocity": (5, 10), "flow": (0, 0), "pressure": (0.1, 0.1), "flow_unit": "Nm³/h"},
            "P=0.05~0.6MPa": {"velocity": (6, 8), "flow": (0, 0), "pressure": (0.05, 0.6), "flow_unit": "Nm³/h"},
            "P=0.6~1MPa": {"velocity": (4, 6), "flow": (0, 0), "pressure": (0.6, 1), "flow_unit": "Nm³/h"},
            "P=2~3MPa": {"velocity": (3, 4), "flow": (0, 0), "pressure": (2, 3), "flow_unit": "Nm³/h"}
        }
        
        # 煤气
        self.fluid_ranges["煤气"] = {
            "管道长50~100m": {"velocity": (0.75, 3), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "Nm³/h"},
            "P≤0.027MPa": {"velocity": (8, 12), "flow": (0, 0), "pressure": (0.1, 0.1), "flow_unit": "Nm³/h"},
            "P≤0.27MPa": {"velocity": (3, 12), "flow": (0, 0), "pressure": (0.1, 0.27), "flow_unit": "Nm³/h"}
        }
        
        # 半水煤气
        self.fluid_ranges["半水煤气"] = {
            "P=0.1~0.15MPa": {"velocity": (10, 15), "flow": (0, 0), "pressure": (0.1, 0.15), "flow_unit": "Nm³/h"}
        }
        
        # 天然气
        self.fluid_ranges["天然气"] = {
            "天然气": {"velocity": (30, 30), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "Nm³/h"}
        }
        
        # 烟道气
        self.fluid_ranges["烟道气"] = {
            "烟道内": {"velocity": (3, 6), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "Nm³/h"}
        }
        
        # 石灰窑窑气
        self.fluid_ranges["石灰窑窑气"] = {
            "管道内": {"velocity": (3, 4), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "Nm³/h"}
        }
        
        # 氮气
        self.fluid_ranges["氮气"] = {
            "P=5~10MPa": {"velocity": (2, 5), "flow": (0, 0), "pressure": (5, 10), "flow_unit": "Nm³/h"},
            "P=20~30MPa": {"velocity": (5, 10), "flow": (0, 0), "pressure": (20, 30), "flow_unit": "Nm³/h"}
        }
        
        # 氢氮混合气
        self.fluid_ranges["氢氮混合气"] = {
            "P=真空": {"velocity": (15, 25), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "Nm³/h"},
            "P<0.3MPa": {"velocity": (8, 15), "flow": (0, 0), "pressure": (0.1, 0.3), "flow_unit": "Nm³/h"},
            "P<0.6MPa": {"velocity": (10, 20), "flow": (0, 0), "pressure": (0.1, 0.6), "flow_unit": "Nm³/h"},
            "P<2MPa": {"velocity": (3, 8), "flow": (0, 0), "pressure": (0.1, 2), "flow_unit": "Nm³/h"},
            "P=22~150MPa": {"velocity": (5, 6), "flow": (0, 0), "pressure": (22, 150), "flow_unit": "Nm³/h"}
        }
        
        # 氨气
        self.fluid_ranges["氨气"] = {
            "气体": {"velocity": (10, 25), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "Nm³/h"},
            "液体": {"velocity": (1.5, 1.5), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "t/h"}
        }
        
        # 乙炔气
        self.fluid_ranges["乙炔气"] = {
            "P<0.15MPa": {"velocity": (4, 8), "flow": (0, 0), "pressure": (0.1, 0.15), "flow_unit": "Nm³/h"},
            "P<2.5MPa": {"velocity": (4, 4), "flow": (0, 0), "pressure": (0.1, 2.5), "flow_unit": "Nm³/h"}
        }
        
        # 乙烯气
        self.fluid_ranges["乙烯气"] = {
            "P<0.01MPa": {"velocity": (3, 4), "flow": (0, 0), "pressure": (0.1, 0.1), "flow_unit": "Nm³/h"}
        }

        # 过热水
        self.fluid_ranges["过热水"] = {
            "过热水": {"velocity": (2, 2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 海水，微碱水
        self.fluid_ranges["海水，微碱水"] = {
            "P<0.6MPa": {"velocity": (1.5, 2.5), "flow": (0, 0), "pressure": (0.1, 0.6), "flow_unit": "m³/h"}
        }
        
        # 粘度较大的液体
        self.fluid_ranges["粘度较大的液体"] = {
            "粘度0.05Pa·s DN25": {"velocity": (0.5, 0.9), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "粘度0.05Pa·s DN50": {"velocity": (0.7, 1.0), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "粘度0.05Pa·s DN100": {"velocity": (1.0, 1.6), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "粘度0.1Pa·s DN25": {"velocity": (0.3, 0.6), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "粘度0.1Pa·s DN50": {"velocity": (0.5, 0.7), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "粘度0.1Pa·s DN100": {"velocity": (0.7, 1.0), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "粘度0.1Pa·s DN200": {"velocity": (1.2, 1.6), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "粘度1Pa·s DN25": {"velocity": (0.1, 0.2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "粘度1Pa·s DN50": {"velocity": (0.16, 0.25), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "粘度1Pa·s DN100": {"velocity": (0.25, 0.35), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "粘度1Pa·s DN200": {"velocity": (0.35, 0.55), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 液氨
        self.fluid_ranges["液氨"] = {
            "P=真空": {"velocity": (0.05, 0.3), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "t/h"},
            "P≤0.6MPa": {"velocity": (0.3, 0.8), "flow": (0, 0), "pressure": (0.1, 0.6), "flow_unit": "t/h"},
            "P≤2MPa": {"velocity": (0.8, 1.5), "flow": (0, 0), "pressure": (0.1, 2), "flow_unit": "t/h"}
        }
        
        # 氢氧化钠
        self.fluid_ranges["氢氧化钠"] = {
            "浓度0~30%": {"velocity": (2, 2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "浓度30%~50%": {"velocity": (1.5, 1.5), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "浓度50%~73%": {"velocity": (1.2, 1.2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 四氯化碳
        self.fluid_ranges["四氯化碳"] = {
            "浓度88%~93%（铅管）": {"velocity": (1.2, 1.2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "93%~100%（铬铁管、钢管）": {"velocity": (1.2, 1.2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 硫酸
        self.fluid_ranges["硫酸"] = {
            "硫酸": {"velocity": (1.2, 1.2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 盐酸
        self.fluid_ranges["盐酸"] = {
            "（衬胶管）": {"velocity": (1.5, 1.5), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 氯化钠
        self.fluid_ranges["氯化钠"] = {
            "带有固体": {"velocity": (2, 4.5), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "无固体": {"velocity": (1.5, 1.5), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 排除废水
        self.fluid_ranges["排除废水"] = {
            "排除废水": {"velocity": (0.4, 0.8), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 泥状混合物
        self.fluid_ranges["泥状混合物"] = {
            "浓度15%": {"velocity": (2.5, 3), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "浓度25%": {"velocity": (3, 4), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"},
            "浓度65%": {"velocity": (2.5, 3), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 乙二醇
        self.fluid_ranges["乙二醇"] = {
            "乙二醇": {"velocity": (2, 2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 苯乙烯
        self.fluid_ranges["苯乙烯"] = {
            "苯乙烯": {"velocity": (2, 2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 二溴乙烯
        self.fluid_ranges["二溴乙烯"] = {
            "玻璃管": {"velocity": (1, 1), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 二氯乙烷
        self.fluid_ranges["二氯乙烷"] = {
            "二氯乙烷": {"velocity": (2, 2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }
        
        # 三氯乙烷
        self.fluid_ranges["三氯乙烷"] = {
            "三氯乙烷": {"velocity": (2, 2), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }

        # 氯仿
        self.fluid_ranges["氯仿"] = {
            "液体": {"velocity": (1.5, 2.0), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }

        # 氯化氢
        self.fluid_ranges["氯化氢"] = {
            "气体": {"velocity": (10, 15), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "Nm³/h"}
        }

        # 溴
        self.fluid_ranges["溴"] = {
            "液体": {"velocity": (1.0, 1.5), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }

        # 氯化甲烷
        self.fluid_ranges["氯化甲烷"] = {
            "气体": {"velocity": (10, 15), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "Nm³/h"},
            "液体": {"velocity": (1.5, 2.0), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }

        # 氯乙烷
        self.fluid_ranges["氯乙烷"] = {
            "气体": {"velocity": (10, 15), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "Nm³/h"},
            "液体": {"velocity": (1.5, 2.0), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "m³/h"}
        }

        # 气体（通用）
        self.fluid_ranges["气体"] = {
            "一般": {"velocity": (10, 20), "flow": (0, 0), "pressure": (0, 0), "flow_unit": "Nm³/h"}
        }

        # 氢气
        self.fluid_ranges["氢气"] = {
            "P≤0.1MPa": {"velocity": (8, 15), "flow": (0, 0), "pressure": (0.1, 0.1), "flow_unit": "Nm³/h"},
            "高压": {"velocity": (15, 25), "flow": (0, 0), "pressure": (0.1, 30), "flow_unit": "Nm³/h"}
        }

        # 氮（同氮气参数）
        self.fluid_ranges["氮"] = {
            "P=5~10MPa": {"velocity": (2, 5), "flow": (0, 0), "pressure": (5, 10), "flow_unit": "Nm³/h"},
            "P=20~30MPa": {"velocity": (5, 10), "flow": (0, 0), "pressure": (20, 30), "flow_unit": "Nm³/h"}
        }
    
    def setup_ui(self):
        """设置UI界面 - 统一风格布局"""
        # 定义标签样式 - 根据UI规范
        label_style = "font-weight: bold; padding-right: 10px;"

        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧：输入参数区域 (占2/3宽度)
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        scroll_left.setWidgetResizable(True)

        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # 1. 说明文本
        description = QLabel(
            "根据流体类型和计算条件计算管道直径或流量，依据《化工管路设计手册》表1.3-1推荐值。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 2. 计算模式选择
        mode_group = QGroupBox("计算模式")
        mode_layout = QHBoxLayout(mode_group)
        
        self.mode_button_group = QButtonGroup(self)
        self.mode_buttons = {}
        
        modes = [
            ("由流量计算管径", "已知流量，计算合适管径"),
            ("由管径计算流量", "已知管径，计算最大流量")
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
        self.mode_buttons["由流量计算管径"].setChecked(True)
        self.mode_button_group.buttonClicked.connect(self.on_mode_button_clicked)
        
        mode_layout.addStretch()
        left_layout.addWidget(mode_group)
        
        # 3. 输入参数组 - 使用GridLayout实现整齐的布局
        input_group = QGroupBox("输入参数")
        
        # 使用GridLayout确保整齐排列
        input_layout = QGridLayout(input_group)
        self.input_layout = input_layout  # 保存引用，供模式切换使用
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)
        
        row = 0

        # ── 第1行：流体类型 ──
        fluid_label = QLabel("流体类型:")
        fluid_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fluid_label.setStyleSheet(label_style)
        input_layout.addWidget(fluid_label, row, 0)

        self.fluid_combo = QComboBox()
        self.fluid_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_fluid_options()
        self.fluid_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.fluid_combo.currentTextChanged.connect(self.on_fluid_changed)
        input_layout.addWidget(self.fluid_combo, row, 1)

        self.fluid_hint = QLabel("")
        self.fluid_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.fluid_hint, row, 2)

        row += 1

        # ── 第2行：计算条件 ──
        condition_label = QLabel("计算条件:")
        condition_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        condition_label.setStyleSheet(label_style)
        input_layout.addWidget(condition_label, row, 0)

        self.condition_combo = QComboBox()
        self.condition_combo.setStyleSheet(COMBOBOX_STYLE)
        self.condition_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.condition_combo.currentTextChanged.connect(self.on_condition_changed)
        input_layout.addWidget(self.condition_combo, row, 1)

        self.condition_hint = QLabel("选择流体后出现")
        self.condition_hint.setStyleSheet("font-style: italic;")
        self.condition_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.condition_hint, row, 2)

        row += 1

        # ── 第3行：流速（始终显示）──
        velocity_label = QLabel("流速 (m/s):")
        velocity_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        velocity_label.setStyleSheet(label_style)
        input_layout.addWidget(velocity_label, row, 0)

        self.velocity_input = QLineEdit()
        self.velocity_input.setPlaceholderText("选择流体后自动填入")
        self.velocity_input.setValidator(QDoubleValidator(0.1, 150.0, 2))
        self.velocity_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.velocity_input, row, 1)

        row += 1

        # ── 第4行：流量（默认模式）──
        self.flow_label = QLabel("流量:")
        self.flow_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.flow_label.setStyleSheet(label_style)

        self.flow_input = QLineEdit()
        self.flow_input.setPlaceholderText("请填写流量值")
        self.flow_input.setValidator(QDoubleValidator(0.1, 100000.0, 2))

        self.diameter_label = QLabel("管道内径 (mm):")
        self.diameter_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.diameter_label.setStyleSheet(label_style)

        self.diameter_input = QLineEdit()
        self.diameter_input.setPlaceholderText("例如: 80")
        self.diameter_input.setValidator(QDoubleValidator(1.0, 2000.0, 1))

        self.diameter_combo = QComboBox()
        self.diameter_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_diameter_options()
        self.diameter_combo.currentTextChanged.connect(self.on_diameter_changed)

        # 默认：流量控件放入网格
        self._flow_diameter_row = row
        input_layout.addWidget(self.flow_label, row, 0)
        input_layout.addWidget(self.flow_input, row, 1)
        self._current_row_widgets = [self.flow_label, self.flow_input]
        row += 1

        # ── 第5行：压力（部分流体显示）──
        self.pressure_label = QLabel("压力 (MPa):")
        self.pressure_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.pressure_label.setStyleSheet(label_style)

        self.pressure_input = QLineEdit()
        self.pressure_input.setPlaceholderText("选择流体后自动填入")
        self.pressure_input.setValidator(QDoubleValidator(0.0, 150.0, 2))
        self.pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.pressure_range_label = QLabel("")
        self.pressure_range_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        self.pressure_range_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # 压力行初始显示（默认可见）
        self._add_pressure_row(input_layout, row)
        self._pressure_row = row

        row += 1

        # ── 第6行：温度（仅过热蒸汽显示）──
        self.temp_label = QLabel("温度 (°C):")
        self.temp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.temp_label.setStyleSheet(label_style)

        self.temp_input = QLineEdit()
        self.temp_input.setPlaceholderText("例如: 350")
        self.temp_input.setValidator(QDoubleValidator(100.0, 600.0, 1))
        self.temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.temp_hint = QLabel("过热蒸汽输入温度")
        self.temp_hint.setStyleSheet("font-style: italic;")
        self.temp_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._add_temp_row(input_layout, row)
        self._temp_row = row
        self._hide_temp_row()

        left_layout.addWidget(input_group)
        
        left_layout.addStretch()
        
        # 右侧：结果显示区域 (占1/3宽度)
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        # 管道截面示意图
        self.svg_widget = QSvgWidget()
        self.svg_widget.setMinimumHeight(220)
        self.svg_widget.setMaximumHeight(280)
        self.svg_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.svg_widget.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
        right_layout.addWidget(self.svg_widget)
        
        # 结果显示
        self.result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(self.result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #666;
                border-radius: 6px;
                padding: 8px;
                /* bg via theme */min-height: 500px;
            }
        """)
        result_layout.addWidget(self.result_text)
        
        right_layout.addWidget(self.result_group)
        
        # 下载按钮布局
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
        
        # 下载DOCX按钮
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
        right_layout.addLayout(bottom_layout)
        
        # 计算按钮
        calculate_btn = CalculatorBase.make_calc_button("计 算")
        calculate_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calculate_btn)
        
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 将左右两部分添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)  # 左侧占2/3
        main_layout.addWidget(right_widget, 1)  # 右侧占1/3
        
        # 设置默认值
        self.set_default_values()
    
    def _add_pressure_row(self, layout, row):
        """将压力行控件添加到布局（便于后续显示/隐藏切换）"""
        layout.addWidget(self.pressure_label, row, 0)
        layout.addWidget(self.pressure_input, row, 1)
        layout.addWidget(self.pressure_range_label, row, 2)

    def _remove_pressure_row(self):
        """从布局中移除压力行"""
        self.pressure_input.clear()  # 隐藏时顺手清空，避免旧值残留
        for w in [self.pressure_label, self.pressure_input, self.pressure_range_label]:
            w.setVisible(False)

    def _show_pressure_row(self):
        """显示压力行"""
        for w in [self.pressure_label, self.pressure_input, self.pressure_range_label]:
            w.setVisible(True)

    def _add_temp_row(self, layout, row):
        layout.addWidget(self.temp_label, row, 0)
        layout.addWidget(self.temp_input, row, 1)
        layout.addWidget(self.temp_hint, row, 2)

    def _show_temp_row(self):
        for w in [self.temp_label, self.temp_input, self.temp_hint]:
            w.setVisible(True)
        if not self.temp_input.text():
            self.temp_input.setText("200")

    def _hide_temp_row(self):
        for w in [self.temp_label, self.temp_input, self.temp_hint]:
            w.setVisible(False)
        self.temp_input.clear()

    # ------------------------------------------------------------
    #  模式 / 流体 / 条件联动
    # ------------------------------------------------------------

    def setup_mode_dependencies(self):
        """设置计算模式的依赖关系"""
        self.on_mode_changed("由流量计算管径")
    
    def on_mode_button_clicked(self, button):
        """处理计算模式按钮点击"""
        mode_text = button.text()
        self.on_mode_changed(mode_text)

    def get_current_mode(self):
        """获取当前选择的计算模式"""
        checked_button = self.mode_button_group.checkedButton()
        if checked_button:
            return checked_button.text()
        return "由流量计算管径"  # 默认值
    
    def on_mode_changed(self, mode):
        """处理计算模式变化 - 在网格中直接替换流量/内径行控件"""
        layout = self.input_layout
        row = self._flow_diameter_row

        # 先隐藏当前行所有控件（removeWidget 只会移除布局管理，不会隐藏）
        for w in self._current_row_widgets:
            layout.removeWidget(w)
            w.hide()
        self._current_row_widgets.clear()

        if mode == "由流量计算管径":
            # 放入流量控件
            layout.addWidget(self.flow_label, row, 0)
            layout.addWidget(self.flow_input, row, 1)
            # 确保显示
            self.flow_label.show()
            self.flow_input.show()
            self._current_row_widgets = [self.flow_label, self.flow_input]
        else:
            # 放入内径控件
            layout.addWidget(self.diameter_label, row, 0)
            layout.addWidget(self.diameter_input, row, 1)
            layout.addWidget(self.diameter_combo, row, 2)
            # 确保显示
            self.diameter_label.show()
            self.diameter_input.show()
            self.diameter_combo.show()
            self._current_row_widgets = [self.diameter_label, self.diameter_input, self.diameter_combo]
            if not self.diameter_input.text():
                self.diameter_input.setText("80")
    
    def setup_fluid_options(self):
        """设置流体选项"""
        # 更新流体选项列表
        fluid_options = [
            "- 请选择流体类型 -",
            "饱和蒸汽",
            "水及粘度相似的液体",
            "自来水",
            "压缩气体",
            "锅炉给水",
            "蒸汽冷凝液",
            "冷凝水",
            "过热水",
            "过热蒸汽",
            "二次蒸汽",
            "高压乏汽",
            "乏汽",
            "氧气",
            "煤气",
            "半水煤气",
            "天然气",
            "烟道气",
            "石灰窑窑气",
            "氮气",
            "氢氮混合气",
            "氨气",
            "乙炔气",
            "氮",
            "氯仿",
            "氯化氢",
            "溴",
            "氯化甲烷",
            "氯乙烷",
            "二氯乙烷",
            "三氯乙烷",
            "乙二醇",
            "苯乙烯",
            "二溴乙烯",
            "海水，微碱水",
            "粘度较大的液体",
            "液氨",
            "氢氧化钠",
            "四氯化碳",
            "硫酸",
            "盐酸",
            "氯化钠",
            "排除废水",
            "泥状混合物",
            "气体",
            "氢气"
        ]
        
        self.fluid_combo.clear()
        self.fluid_combo.addItems(fluid_options)
        
        # 设置流体数据字典（密度值）
        self.fluid_data = {
            # 蒸汽类
            "饱和蒸汽": 5.16,  # 0.9MPa(G)下的近似密度
            "过热蒸汽": 4.8,
            "二次蒸汽": 3.2,
            "高压乏汽": 6.5,
            "乏汽": 2.8,
            "压缩空气": 1.29,
            
            # 气体类 (20°C, 101.3kPa)
            "压缩气体": 1.29,
            "氧气": 1.43,
            "煤气": 0.6,
            "半水煤气": 0.75,
            "天然气": 0.7,
            "烟道气": 1.3,
            "石灰窑窑气": 1.35,
            "氮气": 1.25,
            "氢氮混合气": 0.3,
            "氨气": 0.77,
            "乙炔气": 1.17,
            "乙烯气": 1.26,
            
            # 液体类 (20°C)
            "水及粘度相似的液体": 1000,
            "自来水": 1000,
            "锅炉给水": 1000,
            "蒸汽冷凝水": 1000,
            "冷凝水": 1000,
            "过热水": 1000,
            "海水，微碱水": 1025,
            "粘度较大的液体": 1200,
            "液氨": 682,
            "氢氧化钠": 2130,
            "四氯化碳": 1594,
            "硫酸": 1830,
            "盐酸": 1200,
            "氯化钠": 2160,
            "排除废水": 1100,
            "泥状混合物": 1500,
            "乙二醇": 1115,
            "苯乙烯": 909,
            "二溴乙烯": 2179,
            "二氯乙烷": 1256,
            "三氯乙烷": 1320,
            "氯仿": 1490,
            "氯化氢": 1.64,
            "溴": 3120,
            "氯化甲烷": 2.3,
            "氯乙烷": 2.6,
            "氮": 1.25,
            "气体": 1.29,
            "氢气": 0.09
        }

        # 标态密度数据 (0°C, 101.325 kPa, kg/Nm³)
        # 用于 Nm³/h 流量单位的质量换算
        self.std_density_data = {
            "压缩空气": 1.293,
            "压缩气体": 1.293,
            "氧气": 1.429,
            "煤气": 0.46,
            "半水煤气": 0.75,
            "天然气": 0.717,
            "烟道气": 1.34,
            "石灰窑窑气": 1.35,
            "氮气": 1.251,
            "氢氮混合气": 0.292,
            "氨气": 0.771,
            "乙炔气": 1.171,
            "乙烯气": 1.264,
            "氯化氢": 1.639,
            "氯化甲烷": 2.307,
            "氯乙烷": 2.867,
            "氮": 1.251,
            "气体": 1.293,
            "氢气": 0.090
        }
    
    def on_fluid_changed(self, text):
        """处理流体选择变化"""
        if text.startswith("-") or not text.strip():
            self.condition_combo.clear()
            self.condition_combo.addItem("- 请先选择流体类型 -")
            self.velocity_input.clear()
            self.velocity_input.setToolTip("")
            self.pressure_input.clear()
            self.pressure_input.setReadOnly(False)
            self.pressure_range_label.setText("")
            self.flow_input.clear()
            self.flow_input.setToolTip("")
            self.condition_hint.setText("选择流体后出现")
            self._show_pressure_row()
            self._hide_temp_row()
            return

        # 清空旧值，设置默认值
        self.velocity_input.clear()
        self.pressure_input.clear()
        self.pressure_input.setReadOnly(False)
        self.pressure_range_label.setText("")
        self.flow_input.clear()
        self.flow_input.setText("70")  # 默认流量

        self.update_condition_options(text)
        self.update_density(text)
        self.condition_hint.setText("请选择计算条件")

        # 默认为全部流体显示压力行
        self._show_pressure_row()

        # 过热蒸汽 → 显示温度行
        if text == "过热蒸汽":
            self._show_temp_row()
        else:
            self._hide_temp_row()
    
    def update_condition_options(self, fluid):
        """根据流体更新条件选项，并自动选择第一个条件"""
        self.condition_combo.blockSignals(True)
        self.condition_combo.clear()

        if fluid in self.fluid_ranges:
            conditions = list(self.fluid_ranges[fluid].keys())
            self.condition_combo.addItems(conditions)
            self.condition_combo.blockSignals(False)
            # 自动选择第一个条件并触发更新
            self.condition_combo.setCurrentIndex(0)
            self.on_condition_changed(conditions[0])
        else:
            self.condition_combo.addItem("- 请选择计算条件 -")
            self.condition_combo.setCurrentIndex(0)
            self.condition_combo.blockSignals(False)
    
    def update_density(self, fluid):
        """更新密度值（存入内部变量，不在UI显示）"""
        if fluid in self.fluid_data:
            self._current_density = self.fluid_data[fluid]
        else:
            self._current_density = 1000.0
    
    def on_condition_changed(self, text):
        """处理条件变化 - 自动填入推荐值并控制压力/温度可见性"""
        if text.startswith("-") or not text.strip():
            self.velocity_input.clear()
            self.velocity_input.setToolTip("")
            self.pressure_range_label.setText("")
            self.pressure_input.clear()
            self.pressure_input.setReadOnly(False)
            self._show_pressure_row()
            self.flow_input.clear()
            self.flow_input.setToolTip("")
            return

        if text:
            self.update_parameter_ranges()
            self.condition_hint.setText("推荐值已自动填入")
    
    def update_parameter_ranges(self):
        """更新参数范围并自动填入推荐值"""
        fluid = self.fluid_combo.currentText()
        condition = self.condition_combo.currentText()

        if fluid.startswith("-") or condition.startswith("-"):
            return

        if fluid in self.fluid_ranges and condition in self.fluid_ranges[fluid]:
            ranges = self.fluid_ranges[fluid][condition]

            # 自动填入推荐流速：在范围内随机取值
            vel_min, vel_max = ranges["velocity"]
            if vel_min > 0 and vel_max > 0:
                if vel_min == vel_max:
                    vel = vel_min  # 固定值
                else:
                    vel = (vel_min + vel_max) / 2  # 使用推荐值（中点）
                self.velocity_input.setText(f"{vel:.1f}")
                self.velocity_input.setToolTip(f"推荐范围: {vel_min}~{vel_max} m/s（已随机填入 {vel:.1f}）")

        # 更新压力范围/自动填入/隐藏
        pressure_min, pressure_max = ranges["pressure"]
        if pressure_min == 0 and pressure_max == 0:
            # 不需要压力 → 隐藏压力行
            self._remove_pressure_row()
        else:
            self._show_pressure_row()
            if pressure_min == pressure_max and pressure_min > 0:
                self.pressure_range_label.setText(f"固定值: {pressure_min} MPa")
                self.pressure_input.setText(f"{pressure_min}")
                self.pressure_input.setReadOnly(True)
            elif pressure_min > 0 or pressure_max > 0:
                self.pressure_range_label.setText(f"适用范围: {pressure_min}~{pressure_max} MPa")
                self.pressure_input.setReadOnly(False)
                # 只有上下限都有效时才填中值
                if pressure_min > 0 and pressure_max > 0:
                    p_mid = (pressure_min + pressure_max) / 2
                    self.pressure_input.setText(f"{p_mid:.2f}")

            # 更新流量标签和默认值
            flow_unit = ranges["flow_unit"]
            self.flow_label.setText(f"流量 ({flow_unit}):")

            # 默认填入 70
            if not self.flow_input.text():
                self.flow_input.setText("70")
    
    def setup_diameter_options(self):
        """设置管道内径选项"""
        diameter_options = [
            "- 请选择管道内径 -",  # 添加空选项
            "6.0 mm - DN6 [1/8\"]",
            "7.8 mm - DN8 [1/4\"]", 
            "10.3 mm - DN10 [3/8\"]",
            "15.8 mm - DN15 [1/2\"]",
            "21.0 mm - DN20 [3/4\"]",
            "26.6 mm - DN25 [1.00\"]",
            "35.1 mm - DN32 [1.25\"]",
            "40.9 mm - DN40 [1.50\"]",
            "52.5 mm - DN50 [2.00\"]",
            "62.7 mm - DN65 [2.50\"]",
            "77.9 mm - DN80 [3.00\"]",
            "90.1 mm - DN90 [3.50\"]",
            "102.3 mm - DN100 [4.00\"]",
            "128.2 mm - DN125 [5.00\"]",
            "154.1 mm - DN150 [6.00\"]",
            "202.7 mm - DN200 [8.00\"]",
            "254.5 mm - DN250 [10.00\"]", 
            "303.3 mm - DN300 [12.00\"]"
        ]
        self.diameter_combo.addItems(diameter_options)
        # 设置默认值为空选项
        self.diameter_combo.setCurrentIndex(0)
    
    def on_diameter_changed(self, text):
        """处理直径选择变化"""
        # 检查是否为空选项
        if text.startswith("-") or not text.strip():
            self.diameter_input.clear()
            return
            
        try:
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                diameter_value = float(match.group(1))
                self.diameter_input.setText(f"{diameter_value}")
        except:
            pass
    
    def set_default_values(self):
        """设置默认值"""
        # 初始化下拉框默认选项
        self.fluid_combo.setCurrentIndex(0)  # 请选择流体类型
        self.diameter_combo.setCurrentIndex(0)  # 请选择管道内径
    
    def clear_inputs(self):
        """清空输入"""
        self.set_default_values()
        self.velocity_input.clear()
        self.flow_input.clear()
        self.diameter_input.clear()
        self.temp_input.clear()
        self.result_text.clear()
    
    # ───────────────── SVG 管路示意图 ─────────────────
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        extra = 'font-weight="bold"' if bold else ''
        anchor = 'text-anchor="middle"' if center else ''
        return f'<text x="{x}" y="{y}" {anchor} font-size="{size}" fill="{color}" {extra}>{text}</text>'

    def _generate_pipe_svg(self, diameter=None, flow=None, velocity=None, pressure=None, fluid=""):
        """管道截面示意图：正方形画布确保正圆"""
        w, h = 360, 260
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
                 f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']

        cx, cy = w/2, h/2 - 5
        r_outer = 70
        r_inner = r_outer * 0.78

        # 外圆（管壁）
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r_outer}" fill="#e8edf2" stroke="#4a6fa5" stroke-width="3"/>')
        # 内圆（通径）
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r_inner}" fill="#dce4ec" stroke="#7f8c8d" stroke-width="1.5"/>')

        # 流向箭头（横穿管道）
        arr_l = cx - r_outer - 25
        arr_r = cx + r_outer + 25
        parts.append(f'<line x1="{arr_l}" y1="{cy}" x2="{arr_r}" y2="{cy}" stroke="#3498db" stroke-width="3" '
                     f'marker-start="url(#arrowIn)" marker-end="url(#arrowOut)"/>')
        v_text = f"{velocity} m/s" if velocity else "? m/s"
        parts.append(self._text(cx, cy-18, v_text, size=11, color="#3498db", bold=True))

        # 直径标注
        dia_y = cy + r_outer + 30
        d = f"{float(diameter):.1f}" if diameter else "?"
        d_text = f"φ{d}mm"
        parts.append(f'<line x1="{cx-r_outer}" y1="{dia_y}" x2="{cx+r_outer}" y2="{dia_y}" '
                     f'stroke="#7f8c8d" stroke-width="1" marker-start="url(#arrowL)" marker-end="url(#arrowR)"/>')
        parts.append(self._text(cx, dia_y+16, d_text, size=10, color="#555"))

        # 底部信息
        info_y = h - 14
        if flow:
            parts.append(self._text(40, info_y, f"流量: {flow}", size=10, color="#444", center=False))
        if pressure:
            parts.append(self._text(w-40, info_y, f"压力: {pressure} MPa", size=10, color="#444", center=False))
        if fluid:
            parts.append(self._text(cx, 12, f"介质: {fluid}", size=10, color="#4a6fa5", bold=True))
        else:
            parts.append(self._text(cx, 12, "管道截面示意", size=10, color="#4a6fa5", bold=True))

        parts.append("""<defs>
            <marker id="arrowOut" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#3498db"/></marker>
            <marker id="arrowIn" markerWidth="8" markerHeight="8" refX="0" refY="4" orient="auto"><path d="M8,0 L0,4 L8,8 Z" fill="#3498db"/></marker>
            <marker id="arrowL" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M8,0 L0,4 L8,8 Z" fill="#7f8c8d"/></marker>
            <marker id="arrowR" markerWidth="8" markerHeight="8" refX="0" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#7f8c8d"/></marker>
        </defs>""")
        parts.append("</svg>")
        return "".join(parts)

    def _update_svg_diagram(self):
        try:
            kwargs = {}
            # 优先用计算后存储的值
            if hasattr(self, '_last_fluid') and self._last_fluid:
                kwargs['fluid'] = self._last_fluid
            else:
                fluid = self.fluid_combo.currentText()
                if fluid and not fluid.startswith("-"):
                    kwargs['fluid'] = fluid
            for key, attr in [('diameter', '_last_diameter'), ('flow', '_last_flow'),
                              ('velocity', '_last_velocity'), ('pressure', '_last_pressure')]:
                if hasattr(self, attr) and getattr(self, attr):
                    kwargs[key] = str(getattr(self, attr))
                elif hasattr(self, key + '_input'):
                    try:
                        val = getattr(self, key + '_input').text().strip()
                        if val: kwargs[key] = val
                    except: pass
            svg = self._generate_pipe_svg(**kwargs)
            self.svg_widget.load(svg.encode("utf-8"))
        except: pass

    def calculate(self):
        """执行计算"""
        try:
            # 获取当前模式
            mode = self.get_current_mode()
            
            # 获取输入参数
            fluid = self.fluid_combo.currentText()
            condition = self.condition_combo.currentText()
            
            # 验证流体选择
            if fluid.startswith("-") or not fluid.strip():
                QMessageBox.warning(self, "选择错误", "请选择流体类型")
                return
            
            # 验证计算条件选择
            if condition.startswith("-") or not condition.strip():
                QMessageBox.warning(self, "选择错误", "请选择计算条件")
                return
            
            # 获取数值输入
            pressure_text = self.pressure_input.text()
            velocity_text = self.velocity_input.text()

            if not velocity_text:
                QMessageBox.warning(self, "输入错误", "请输入流速")
                return

            velocity = float(velocity_text)

            pressure = 0.0
            if pressure_text and self.pressure_label.isVisible():
                pressure = float(pressure_text)

            density = getattr(self, '_current_density', 1000.0)
            
            # 验证参数范围
            self.validate_parameters(fluid, condition, velocity, pressure)
            
            if mode == "由流量计算管径":
                # 由流量计算管径
                flow_text = self.flow_input.text()
                if not flow_text:
                    QMessageBox.warning(self, "输入错误", "请输入流量")
                    return
                
                flow_rate = float(flow_text)
                diameter_mm = self.calculate_diameter_from_flow(flow_rate, velocity, density, fluid, condition)
                self.show_diameter_result(fluid, condition, flow_rate, velocity, 
                                        diameter_mm, density, pressure, mode)
            else:
                # 由管径计算流量
                diameter_mm = float(self.diameter_input.text() or 0)
                if not diameter_mm:
                    QMessageBox.warning(self, "输入错误", "请输入管道内径")
                    return
                
                flow_rate = self.calculate_flow_from_diameter(diameter_mm, velocity, density, fluid, condition)
                self.show_flow_result(fluid, condition, diameter_mm, velocity, 
                                    flow_rate, density, pressure, mode)

            # 存储计算结果供 SVG 使用
            self._last_diameter = diameter_mm
            self._last_flow = flow_rate
            self._last_velocity = velocity
            self._last_pressure = pressure
            self._last_fluid = fluid
            self._update_svg_diagram()

        except ValueError as e:
            QMessageBox.critical(self, "输入错误", f"参数格式错误: {str(e)}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "密度或流速不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")
    
    def validate_parameters(self, fluid, condition, velocity, pressure):
        """验证参数是否在推荐范围内"""
        if fluid in self.fluid_ranges and condition in self.fluid_ranges[fluid]:
            ranges = self.fluid_ranges[fluid][condition]
            
            # 验证流速
            vel_min, vel_max = ranges["velocity"]
            if velocity < vel_min or velocity > vel_max:
                QMessageBox.warning(self, "输入警告", 
                                  f"当前流速 {velocity} m/s 不在推荐范围内 ({vel_min}~{vel_max} m/s)")
            
            # 验证压力
            pressure_min, pressure_max = ranges["pressure"]
            if pressure_min > 0 and (pressure < pressure_min or pressure > pressure_max):
                QMessageBox.warning(self, "输入警告", 
                                  f"当前压力 {pressure} MPa 不在推荐范围内 ({pressure_min}~{pressure_max} MPa)")
    
    def calculate_diameter_from_flow(self, flow_rate, velocity, density, fluid, condition):
        """由流量计算管径，使用手册公式"""
        # 获取流量单位
        flow_unit = self.fluid_ranges[fluid][condition]["flow_unit"]
        
        # 将流量转换为kg/h
        if flow_unit == "t/h":
            W = flow_rate * 1000  # t/h → kg/h
        elif flow_unit == "m³/h":
            W = flow_rate * density  # m³/h → kg/h
        elif flow_unit == "Nm³/h":
            # Nm³/h → kg/h，使用该气体的标态密度
            std_rho = self.std_density_data.get(fluid, 1.293)
            W = flow_rate * std_rho
        else:
            W = flow_rate * 1000  # 默认按t/h处理
        
        # 使用手册公式计算管径
        diameter_mm = 18.81 * (W ** 0.5) * (velocity ** -0.5) * (density ** -0.5)
        return diameter_mm
    
    def calculate_flow_from_diameter(self, diameter_mm, velocity, density, fluid, condition):
        """由管径计算流量，使用手册公式"""
        # 获取流量单位
        flow_unit = self.fluid_ranges[fluid][condition]["flow_unit"]
        
        # 使用手册公式反推质量流量 (kg/h)
        W = (diameter_mm / 18.81) ** 2 * velocity * density
        
        # 根据流量单位转换
        if flow_unit == "t/h":
            flow_rate = W / 1000  # kg/h → t/h
        elif flow_unit == "m³/h":
            flow_rate = W / density  # kg/h → m³/h
        elif flow_unit == "Nm³/h":
            # kg/h → Nm³/h，使用该气体的标态密度
            std_rho = self.std_density_data.get(fluid, 1.293)
            flow_rate = W / std_rho
        else:
            flow_rate = W / 1000  # 默认按t/h处理
        
        return flow_rate
    
    def show_diameter_result(self, fluid, condition, flow_rate, velocity, diameter_mm, density, pressure, mode):
        """显示管径计算结果"""
        # 获取流量单位
        flow_unit = self.fluid_ranges[fluid][condition]["flow_unit"]
        
        # 将流量转换为kg/h用于公式显示
        if flow_unit == "t/h":
            W = flow_rate * 1000
        elif flow_unit == "m³/h":
            W = flow_rate * density
        elif flow_unit == "Nm³/h":
            std_rho = self.std_density_data.get(fluid, 1.293)
            W = flow_rate * std_rho
        else:
            W = flow_rate * 1000
        
        # 推荐标准管径
        standard_diameters = [6, 8, 10, 15, 20, 25, 32, 40, 50, 65, 80, 100, 
                            125, 150, 200, 250, 300, 350, 400, 450, 500]
        
        # 找到最接近的标准管径
        closest_diam = min(standard_diameters, key=lambda x: abs(x - diameter_mm))
        
        result = f"""═══════════
 输入参数
══════════

    计算模式: {mode}
    流体类型: {fluid}
    计算条件: {condition}
    压力: {pressure} MPa(G)
    流量: {flow_rate} {flow_unit}
    流速: {velocity} m/s
    密度: {density:.2f} kg/m³

══════════
计算结果
══════════

    理论计算管径: {diameter_mm:.1f} mm

    推荐标准管径: DN{closest_diam}
    • 实际流速: {self.calculate_actual_velocity(flow_rate, closest_diam, density, fluid, condition):.2f} m/s

══════════
计算公式 (HG/T 20570.6—1995)
══════════

    d = 18.81 × W^0.5 × u^-0.5 × ρ^-0.5

    其中:
    d = 管道内径, mm
    W = 质量流量 = {W:.0f} kg/h
    u = 流速 = {velocity} m/s
    ρ = 密度 = {density:.2f} kg/m³

    计算过程:
    d = 18.81 × ({W:.0f}^0.5) × ({velocity}^-0.5) × ({density:.2f}^-0.5)
    = 18.81 × {W**0.5:.2f} × {velocity**-0.5:.4f} × {density**-0.5:.4f}
    = {diameter_mm:.1f} mm

══════════
工程建议
══════════

    • 推荐使用标准管径 DN{closest_diam}
    • 考虑管道材质、压力等级和安装条件
    • 计算结果仅供参考，实际选择需考虑具体工况"""
        
        self.result_text.setText(result)
    
    def show_flow_result(self, fluid, condition, diameter_mm, velocity, flow_rate, density, pressure, mode):
        """显示流量计算结果"""
        # 获取流量单位
        flow_unit = self.fluid_ranges[fluid][condition]["flow_unit"]
        
        # 将流量转换为kg/h用于公式显示
        if flow_unit == "t/h":
            W = flow_rate * 1000
        elif flow_unit == "m³/h":
            W = flow_rate * density
        elif flow_unit == "Nm³/h":
            std_rho = self.std_density_data.get(fluid, 1.293)
            W = flow_rate * std_rho
        else:
            W = flow_rate * 1000
        
        result = f"""══════════
 输入参数
══════════

    计算模式: {mode}
    流体类型: {fluid}
    计算条件: {condition}
    压力: {pressure} MPa(G)
    管道内径: {diameter_mm} mm
    流速: {velocity} m/s
    密度: {density:.2f} kg/m³

══════════
计算结果
══════════

    理论计算流量:
    • {flow_rate:.2f} {flow_unit}"""

    # 根据流量单位显示不同的转换
        if flow_unit == "t/h":
            result += f"""
    • {flow_rate * 1000:.0f} kg/h
    • {flow_rate * 1000 / 3600:.2f} kg/s"""
        elif flow_unit == "m³/h":
            result += f"""
    • {flow_rate * 1000:.0f} L/h
    • {flow_rate / 3600:.4f} m³/s"""
        elif flow_unit == "Nm³/h":
            std_rho = self.std_density_data.get(fluid, 1.293)
            result += f"""
    • {flow_rate * std_rho:.0f} kg/h
    • {flow_rate * std_rho / 3600:.2f} kg/s"""

        result += f"""

══════════
计算公式 (HG/T 20570.6—1995)
══════════

    由管径计算流量的反推公式:
    W = (d / 18.81)^2 × u × ρ

    其中:
    d = 管道内径 = {diameter_mm} mm
    u = 流速 = {velocity} m/s
    ρ = 密度 = {density:.2f} kg/m³
    W = 质量流量, kg/h

    计算过程:
    W = ({diameter_mm} / 18.81)^2 × {velocity} × {density:.2f}
    = {diameter_mm/18.81:.2f}^2 × {velocity} × {density:.2f}
    = {(diameter_mm/18.81)**2:.2f} × {velocity} × {density:.2f}
    = {W:.0f} kg/h
    = {flow_rate:.2f} {flow_unit}

══════════
工程建议
══════════

    • 当前流速和流量在推荐范围内
    • 根据实际流量需求调整管道尺寸或流速
    • 计算结果仅供参考，实际应用请考虑安全系数"""
        
        self.result_text.setText(result)
    
    def calculate_actual_velocity(self, flow_rate, diameter_mm, density, fluid, condition):
        """计算实际流速"""
        # 获取流量单位
        flow_unit = self.fluid_ranges[fluid][condition]["flow_unit"]
        
        # 将流量转换为kg/s
        if flow_unit == "t/h":
            flow_kg_s = flow_rate * 1000 / 3600  # t/h → kg/s
        elif flow_unit == "m³/h":
            flow_kg_s = flow_rate * density / 3600  # m³/h → kg/s
        elif flow_unit == "Nm³/h":
            std_rho = self.std_density_data.get(fluid, 1.293)
            flow_kg_s = flow_rate * std_rho / 3600
        else:
            flow_kg_s = flow_rate * 1000 / 3600  # 默认按t/h处理
        
        area = math.pi * ((diameter_mm / 1000) / 2) ** 2
        return flow_kg_s / (density * area)

    def _get_history_data(self):
        """提供历史记录数据"""
        mode = self.get_current_mode()
        fluid = self.fluid_combo.currentText()
        condition = self.condition_combo.currentText()
        velocity = float(self.velocity_input.text() or 0)
        density = getattr(self, '_current_density', 1000.0)
        pressure = float(self.pressure_input.text() or 0)

        inputs = {
            "计算模式": mode,
            "流体类型": fluid,
            "计算条件": condition,
            "流速_m_s": velocity,
            "密度_kg_m3": density,
            "压力_MPa": pressure
        }
        outputs = {}

        try:
            flow_unit = ""
            if fluid in self.fluid_ranges and condition in self.fluid_ranges[fluid]:
                flow_unit = self.fluid_ranges[fluid][condition]["flow_unit"]

            if mode == "由流量计算管径":
                flow_rate = float(self.flow_input.text() or 0)
                inputs["流量"] = flow_rate
                if flow_unit:
                    inputs["流量单位"] = flow_unit
                diameter_mm = self.calculate_diameter_from_flow(flow_rate, velocity, density, fluid, condition)
                standard_diameters = [6, 8, 10, 15, 20, 25, 32, 40, 50, 65, 80, 100,
                                      125, 150, 200, 250, 300, 350, 400, 450, 500]
                closest_diam = min(standard_diameters, key=lambda x: abs(x - diameter_mm))
                outputs["理论管径_mm"] = round(diameter_mm, 1)
                outputs["推荐标准管径"] = f"DN{closest_diam}"
                outputs["实际流速_m_s"] = round(self.calculate_actual_velocity(flow_rate, closest_diam, density, fluid, condition), 2)
            else:
                diameter_mm = float(self.diameter_input.text() or 0)
                inputs["管道内径_mm"] = diameter_mm
                flow_rate = self.calculate_flow_from_diameter(diameter_mm, velocity, density, fluid, condition)
                outputs["理论流量"] = round(flow_rate, 2)
                if flow_unit:
                    outputs["流量单位"] = flow_unit
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        """获取工程信息 - 使用共享的项目信息"""
        try:
            from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                        QLineEdit, QPushButton, QDialogButtonBox)
            
            class ProjectInfoDialog(QDialog):
                def __init__(self, parent=None, default_info=None, report_number=""):
                    super().__init__(parent)
                    self.default_info = default_info or {}
                    self.report_number = report_number
                    self.setWindowTitle("工程信息")
                    self.setFixedSize(400, 350)
                    self.setup_ui()
                    
                def setup_ui(self):
                    layout = QVBoxLayout(self)
                    
                    # 标题
                    title_label = QLabel("请输入工程信息")
                    title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
                    layout.addWidget(title_label)
                    
                    # 公司名称
                    company_layout = QHBoxLayout()
                    company_label = QLabel("公司名称:")
                    company_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    self.company_input = QLineEdit()
                    self.company_input.setPlaceholderText("例如：XX建筑工程有限公司")
                    self.company_input.setText(self.default_info.get('company_name', ''))
                    company_layout.addWidget(company_label)
                    company_layout.addWidget(self.company_input)
                    layout.addLayout(company_layout)
                    
                    # 工程编号
                    number_layout = QHBoxLayout()
                    number_label = QLabel("工程编号:")
                    number_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    self.project_number_input = QLineEdit()
                    self.project_number_input.setPlaceholderText("例如：2024-PD-001")
                    self.project_number_input.setText(self.default_info.get('project_number', ''))
                    number_layout.addWidget(number_label)
                    number_layout.addWidget(self.project_number_input)
                    layout.addLayout(number_layout)
                    
                    # 工程名称
                    project_layout = QHBoxLayout()
                    project_label = QLabel("工程名称:")
                    project_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    self.project_input = QLineEdit()
                    self.project_input.setPlaceholderText("例如：化工厂管道系统")
                    self.project_input.setText(self.default_info.get('project_name', ''))
                    project_layout.addWidget(project_label)
                    project_layout.addWidget(self.project_input)
                    layout.addLayout(project_layout)
                    
                    # 子项名称
                    subproject_layout = QHBoxLayout()
                    subproject_label = QLabel("子项名称:")
                    subproject_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    self.subproject_input = QLineEdit()
                    self.subproject_input.setPlaceholderText("例如：主生产区管道")
                    self.subproject_input.setText(self.default_info.get('subproject_name', ''))
                    subproject_layout.addWidget(subproject_label)
                    subproject_layout.addWidget(self.subproject_input)
                    layout.addLayout(subproject_layout)
                    
                    # 计算书编号
                    report_number_layout = QHBoxLayout()
                    report_number_label = QLabel("计算书编号:")
                    report_number_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    self.report_number_input = QLineEdit()
                    self.report_number_input.setText(self.report_number)
                    report_number_layout.addWidget(report_number_label)
                    report_number_layout.addWidget(self.report_number_input)
                    layout.addLayout(report_number_layout)
                    
                    # 按钮
                    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                    button_box.accepted.connect(self.accept)
                    button_box.rejected.connect(self.reject)
                    layout.addWidget(button_box)
                    
                def get_info(self):
                    return {
                        'company_name': self.company_input.text().strip(),
                        'project_number': self.project_number_input.text().strip(),
                        'project_name': self.project_input.text().strip(),
                        'subproject_name': self.subproject_input.text().strip(),
                        'report_number': self.report_number_input.text().strip()
                    }
            
            # 从数据管理器获取共享的项目信息
            saved_info = {}
            if self.data_manager:
                saved_info = self.data_manager.get_project_info()
            
            # 获取下一个报告编号
            report_number = ""
            if self.data_manager:
                report_number = self.data_manager.get_next_report_number("PD")
            
            dialog = ProjectInfoDialog(self, saved_info, report_number)
            if dialog.exec() == QDialog.Accepted:
                info = dialog.get_info()
                # 验证必填字段
                if not info['company_name']:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "输入错误", "公司名称不能为空")
                    return self.get_project_info()  # 重新弹出对话框
                
                # 保存项目信息到数据管理器
                if self.data_manager:
                    # 只保存项目信息，不保存报告编号
                    info_to_save = {
                        'company_name': info['company_name'],
                        'project_number': info['project_number'],
                        'project_name': info['project_name'],
                        'subproject_name': info['subproject_name']
                    }
                    self.data_manager.update_project_info(info_to_save)
                    print("项目信息已保存")
                
                return info
            else:
                return None  # 用户取消了
                
        except Exception as e:
            print(f"获取工程信息失败: {e}")
            return None
    
    def generate_report(self):
        """生成计算书"""
        try:
            # 获取当前结果文本
            result_text = self.result_text.toPlainText()
            
            # 更宽松的检查条件：只要结果文本不为空且包含计算结果的关键字
            if not result_text or ("计算结果" not in result_text and "理论计算管径" not in result_text and "理论计算流量" not in result_text):
                QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
                return None
                
            # 获取工程信息
            project_info = self.get_project_info()
            if not project_info:
                return None  # 用户取消了输入
            
            # 添加报告头信息
            report = f"""工程计算书 - 管道直径计算
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
    工程编号: {project_info['project_number']}
    工程名称: {project_info['project_name']}
    子项名称: {project_info['subproject_name']}
    计算日期: {datetime.now().strftime('%Y-%m-%d')}

══════════
计算书标识
══════════

    计算书编号: {project_info['report_number']}
    版本: 1.0
    状态: 正式计算书

══════════
备注说明
══════════

    1. 本计算书基于《化工管路设计手册》及相关标准规范
    2. 计算结果仅供参考，实际应用需考虑安全系数
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
        ReportExporter.export_docx(self, "管径计算")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "管径计算")
    def process_content_for_pdf(self, content):
        """处理内容，使其适合PDF显示"""
        # 清理bullet符号
        content = content.replace("•", "")

        # 替换单位符号
        content = content.replace("m³", "m3")
        content = content.replace("g/100g", "g/100g")
        content = content.replace("kg/m³", "kg/m3")
        content = content.replace("Nm³/h", "Nm3/h")
        content = content.replace("Pa·s", "Pa.s")
        
        return content

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = 管径计算()
    calculator.resize(1200, 800)
    calculator.show()
    
    sys.exit(app.exec())