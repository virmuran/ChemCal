from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox,
    QScrollArea, QButtonGroup, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtSvgWidgets import QSvgWidget
import math
import re

from utils.docx_utils import ReportExporter
from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        MODE_BUTTON_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase

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

        # ── 淀粉糖物料档（2026-10-30 新增）──────────────────────────
        # 粘度/密度为行业典型经验值[E]，随浓度与温度变化很大，仅作选型起点；
        # 来源：酶制剂厂商工艺数据（液化液 60℃ Brookfield：DE10~15 为 1200~1800、
        # DE16~18 为 400~800 mPa·s；90℃ 下 DE12~15 <100）、葡萄糖浆粘度-温度
        # 关系（75%DS：15℃ 9220 / 60℃ 237.5 mPa·s；35℃ 下 75~80%DS 为
        # 1228~10900 mPa·s）、商品葡萄糖浆规格（43℃、80%DS：8000~30000）。
        # 推荐流速参考：熟化淀粉管道设计指南（DN50 0.8~1.5、DN100 1.2~2.5 m/s，
        # 防沉降最低 0.3 m/s）与电磁流量计选型惯例（含颗粒介质 <3 m/s）。
        # "viscosity" 键为该档典型粘度范围（Pa·s），供压降估算取中值。
        self.fluid_ranges["淀粉调浆液"] = {
            "淀粉乳30~35%DS(50~65℃未糊化)": {
                "velocity": (0.8, 1.5), "flow": (0, 0), "pressure": (0, 0),
                "flow_unit": "m³/h", "viscosity": (0.05, 1.0)}
        }
        self.fluid_ranges["液化液"] = {
            "DE10~15(60℃)": {
                "velocity": (0.5, 1.0), "flow": (0, 0), "pressure": (0, 0),
                "flow_unit": "m³/h", "viscosity": (1.2, 1.8)},
            "DE16~18(60℃)": {
                "velocity": (0.6, 1.2), "flow": (0, 0), "pressure": (0, 0),
                "flow_unit": "m³/h", "viscosity": (0.4, 0.8)},
            "DE10~15(90℃出喷射器)": {
                "velocity": (0.8, 1.5), "flow": (0, 0), "pressure": (0, 0),
                "flow_unit": "m³/h", "viscosity": (0.05, 0.1)}
        }
        self.fluid_ranges["糖化液"] = {
            "DE>95(35~40%DS,55~60℃)": {
                "velocity": (1.0, 2.0), "flow": (0, 0), "pressure": (0, 0),
                "flow_unit": "m³/h", "viscosity": (0.02, 0.1)}
        }
        self.fluid_ranges["脱色液"] = {
            "40~50%DS(40~60℃)": {
                "velocity": (1.0, 2.0), "flow": (0, 0), "pressure": (0, 0),
                "flow_unit": "m³/h", "viscosity": (0.01, 0.06)}
        }
        self.fluid_ranges["葡萄糖浆"] = {
            "75~80%DS(40~50℃)": {
                "velocity": (0.2, 0.5), "flow": (0, 0), "pressure": (0, 0),
                "flow_unit": "m³/h", "viscosity": (2.0, 15.0)},
            "75%DS(60℃保温)": {
                "velocity": (0.5, 1.0), "flow": (0, 0), "pressure": (0, 0),
                "flow_unit": "m³/h", "viscosity": (0.24, 1.2)}
        }
        # 自定义档：粘度/密度由用户输入，流速按粘度分级规则自动推荐
        self.fluid_ranges["自定义粘性液体(按粘度推荐)"] = {
            "输入粘度自动推荐流速": {
                "velocity": (0.1, 3.0), "flow": (0, 0), "pressure": (0, 0),
                "flow_unit": "m³/h"}
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
    
    # ══════════════════════════════════════════════════════════
    # 与资料库互取数据（打通「查到数据要手抄到另一个页签」）
    # ══════════════════════════════════════════════════════════

    def apply_reference_value(self, field, value):
        """接收资料库「送入计算器」的值。

        field 取值见 modules/reference/ref_exchange.TARGETS
        （velocity_input / flow_input / diameter_input / pressure_input / temp_input）。
        """
        widget = getattr(self, field, None)
        if widget is None or not hasattr(widget, "setText"):
            return False
        text = ("%g" % value) if isinstance(value, (int, float)) else str(value)
        widget.setText(text)
        return True

    def _open_reference(self, title):
        """📚 快捷入口：请主窗口切到资料库并定位到该节。"""
        try:
            from modules.reference.ref_exchange import EXCHANGE
        except Exception:
            try:
                from ref_exchange import EXCHANGE
            except Exception:
                return False
        EXCHANGE.open_section(title)
        return True

    def setup_ui(self):
        """设置UI界面 - 统一风格布局"""
        # 定义标签样式 - 统一标准
        label_style = INPUT_LABEL_STYLE

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
            "根据流体类型和计算条件计算管道直径或流量，依据《化工管路设计手册》表1.3-1推荐值。\n"
            "粘性物料（淀粉糖浆等）可选专用档，或选「自定义粘性液体」输入粘度自动推荐流速；"
            "带粘度的介质在结果页附每100m直管压降估算。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)

        # ── 资料库快捷入口（与资料库互取数据：点一下即定位到对应数据节）──
        ref_row = QHBoxLayout()
        ref_row.setSpacing(6)
        ref_hint = QLabel("查资料库:")
        ref_hint.setStyleSheet(label_style)
        ref_row.addWidget(ref_hint)
        for _label, _title in (("推荐流速", "常用流体推荐流速"),
                               ("管径选型", "管径快速选型"),
                               ("管道粗糙度", "管道粗糙度"),
                               ("液体物性", "常用液体物性（25°C）"),
                               ("饱和蒸汽", "饱和蒸汽压力-温度对照")):
            _btn = QPushButton(_label)
            _btn.setObjectName("iconBtn")      # 轻型按钮样式交主题
            _btn.setToolTip(f"在资料库中打开「{_title}」")
            _btn.clicked.connect(lambda _=False, t=_title: self._open_reference(t))
            ref_row.addWidget(_btn)
        ref_row.addStretch()
        left_layout.addLayout(ref_row)

        # 2. 计算模式选择
        mode_group = CalculatorBase.make_group_box("计算模式")
        mode_layout = QHBoxLayout(mode_group)
        
        self.mode_button_group = QButtonGroup(self)
        self.mode_buttons = {}
        
        modes = [
            ("由流量计算管径", "已知流量，计算合适管径"),
            ("由管径计算流量", "已知管径，计算最大流量")
        ]
        
        for i, (mode_name, tooltip) in enumerate(modes):
            btn = CalculatorBase.make_mode_button(mode_name, tooltip)
            self.mode_button_group.addButton(btn, i)
            mode_layout.addWidget(btn)
            self.mode_buttons[mode_name] = btn
        
        # 默认选择第一个
        self.mode_buttons["由流量计算管径"].setChecked(True)
        self.mode_button_group.buttonClicked.connect(self.on_mode_button_clicked)
        
        left_layout.addWidget(mode_group)
        
        # 3. 输入参数组 - 使用GridLayout实现整齐的布局
        input_group = CalculatorBase.make_group_box("输入参数")
        
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

        self.temp_input = QLineEdit("20")
        self.temp_input.setPlaceholderText("例如: 350")
        self.temp_input.setValidator(QDoubleValidator(100.0, 600.0, 1))
        self.temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.temp_hint = QLabel("过热蒸汽输入温度")
        self.temp_hint.setStyleSheet("font-style: italic;")
        self.temp_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._add_temp_row(input_layout, row)
        self._temp_row = row
        self._hide_temp_row()

        row += 1

        # ── 第7行：粘度（仅「自定义粘性液体」显示）──
        self.viscosity_label = QLabel("粘度 (mPa·s):")
        self.viscosity_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.viscosity_label.setStyleSheet(label_style)

        self.viscosity_input = QLineEdit()
        self.viscosity_input.setPlaceholderText("例如: 1500")
        self.viscosity_input.setValidator(QDoubleValidator(0.01, 100000.0, 2))
        self.viscosity_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.viscosity_input.textChanged.connect(self._on_viscosity_changed)

        self.viscosity_hint = QLabel("输入后自动推荐流速并估算压降")
        self.viscosity_hint.setStyleSheet("font-style: italic;")
        self.viscosity_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._add_viscosity_row(input_layout, row)
        self._viscosity_row = row
        self._hide_viscosity_row()

        row += 1

        # ── 第8行：密度（仅「自定义粘性液体」显示，供压降估算）──
        self.density_label = QLabel("密度 (kg/m³):")
        self.density_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.density_label.setStyleSheet(label_style)

        self.density_input = QLineEdit("1200")
        self.density_input.setPlaceholderText("例如: 1200")
        self.density_input.setValidator(QDoubleValidator(1.0, 20000.0, 1))
        self.density_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.density_input.textChanged.connect(self._on_custom_density_changed)

        self.density_hint = QLabel("淀粉糖浆类典型 1100~1450，随浓度变化")
        self.density_hint.setStyleSheet("font-style: italic;")
        self.density_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._add_density_row(input_layout, row)
        self._density_row = row
        self._hide_density_row()

        left_layout.addWidget(input_group)
        
        # 4. 在底部添加拉伸因子
        left_layout.addStretch()
        
        # 右侧：结果显示区域 (占1/3宽度)
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        # 管道截面示意图 (SVG)
        self.svg_widget = QSvgWidget()
        self.svg_widget.setMinimumSize(280, 220)
        self.svg_widget.setMaximumHeight(280)
        self.svg_widget.setStyleSheet("background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 4px;")
        self.svg_widget.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
        right_layout.addWidget(self.svg_widget)
        
        # 计算结果
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
        
        # 底部按钮行：清空 | DOCX | PDF
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(CLEAR_BTN_STYLE)
        clear_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        clear_btn.clicked.connect(self.clear_inputs)
        docx_btn = QPushButton("DOCX")
        docx_btn.setStyleSheet(DOCX_BTN_STYLE)
        docx_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        docx_btn.clicked.connect(self.download_docx_report)
        pdf_btn = QPushButton("PDF")
        pdf_btn.setStyleSheet(PDF_BTN_STYLE)
        pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pdf_btn.clicked.connect(self.download_pdf_report)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(docx_btn)
        btn_layout.addWidget(pdf_btn)
        right_layout.addLayout(btn_layout)
        
        # 计算按钮（最底部）
        calc_btn = CalculatorBase.make_calc_button()
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)
        
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

    def _add_viscosity_row(self, layout, row):
        layout.addWidget(self.viscosity_label, row, 0)
        layout.addWidget(self.viscosity_input, row, 1)
        layout.addWidget(self.viscosity_hint, row, 2)

    def _show_viscosity_row(self):
        for w in [self.viscosity_label, self.viscosity_input, self.viscosity_hint]:
            w.setVisible(True)

    def _hide_viscosity_row(self):
        for w in [self.viscosity_label, self.viscosity_input, self.viscosity_hint]:
            w.setVisible(False)
        self.viscosity_input.clear()

    def _add_density_row(self, layout, row):
        layout.addWidget(self.density_label, row, 0)
        layout.addWidget(self.density_input, row, 1)
        layout.addWidget(self.density_hint, row, 2)

    def _show_density_row(self):
        for w in [self.density_label, self.density_input, self.density_hint]:
            w.setVisible(True)

    def _hide_density_row(self):
        for w in [self.density_label, self.density_input, self.density_hint]:
            w.setVisible(False)

    # ------------------------------------------------------------
    #  粘度 → 推荐流速 / 压降估算
    # ------------------------------------------------------------

    #: 粘度分级推荐流速（m/s），经验值[E]：
    #: 锚点 = 化工管路设计手册粘度档（0.05/0.1/1 Pa·s）与熟化淀粉管道
    #: 设计指南（防沉降最低 0.3 m/s），分级间平滑过渡。
    VISCOSITY_VELOCITY_BANDS = [
        (50,        1.5, 3.0),   # 类水稀液
        (500,       0.8, 1.5),   # 稀糖液/糖化液
        (2000,      0.5, 1.0),   # 液化液
        (10000,     0.3, 0.6),   # 浓糖浆（容积泵）
        (float("inf"), 0.1, 0.3) # 超高粘（冷糖膏）
    ]

    @classmethod
    def recommend_velocity_by_viscosity(cls, mu_mpa_s):
        """按动力粘度(mPa·s)返回推荐流速范围 (lo, hi) m/s"""
        for upper, lo, hi in cls.VISCOSITY_VELOCITY_BANDS:
            if mu_mpa_s < upper:
                return lo, hi
        return cls.VISCOSITY_VELOCITY_BANDS[-1][1], cls.VISCOSITY_VELOCITY_BANDS[-1][2]

    def _on_viscosity_changed(self, text):
        """自定义档：输入粘度 → 自动填入推荐流速"""
        fluid = self.fluid_combo.currentText()
        if fluid != "自定义粘性液体(按粘度推荐)":
            return
        try:
            mu = float(text)
        except ValueError:
            return
        if mu <= 0:
            return
        lo, hi = self.recommend_velocity_by_viscosity(mu)
        vel = (lo + hi) / 2
        self.velocity_input.setText(f"{vel:.2f}")
        self.velocity_input.setToolTip(
            f"按粘度 {mu:g} mPa·s 推荐: {lo}~{hi} m/s（经验值，可手动修改）")

    def _on_custom_density_changed(self, text):
        """自定义档：密度输入实时生效（供流量换算与压降估算）"""
        fluid = self.fluid_combo.currentText()
        if fluid != "自定义粘性液体(按粘度推荐)":
            return
        try:
            rho = float(text)
            if rho > 0:
                self._current_density = rho
        except ValueError:
            pass

    def _current_viscosity(self):
        """当前粘度 (Pa·s)；无粘度数据时返回 None。

        自定义档取用户输入（mPa·s → Pa·s）；预设档取典型范围中值。
        """
        fluid = self.fluid_combo.currentText()
        if fluid == "自定义粘性液体(按粘度推荐)":
            try:
                return float(self.viscosity_input.text()) / 1000.0
            except ValueError:
                return None
        condition = self.condition_combo.currentText()
        rng = self.fluid_ranges.get(fluid, {}).get(condition)
        if rng and "viscosity" in rng:
            lo, hi = rng["viscosity"]
            return (lo + hi) / 2.0
        return None

    def _estimate_pressure_drop(self, diameter_mm, velocity, density, mu_pa_s):
        """Darcy-Weisbach 压降估算（每 100m 直管），返回 dict 或 None。

        摩阻系数：层流 λ=64/Re；湍流 Swamee-Jain 显式式，
        粗糙度取 0.05 mm（食品级 304/316 无缝不锈钢管典型值）。
        """
        if not (mu_pa_s and mu_pa_s > 0 and diameter_mm > 0
                and velocity > 0 and density > 0):
            return None
        d_m = diameter_mm / 1000.0
        re = density * velocity * d_m / mu_pa_s
        roughness = 0.00005  # m
        if re < 2300:
            lam = 64.0 / re
        else:
            lam = 0.25 / (math.log10(roughness / (3.7 * d_m)
                                     + 5.74 / re ** 0.9) ** 2)
        dp_pa = lam * (100.0 / d_m) * (density * velocity ** 2 / 2.0)  # Pa/100m
        head_m = lam * (100.0 / d_m) * velocity ** 2 / (2 * 9.81)      # m液柱/100m
        regime = "层流" if re < 2300 else ("过渡区" if re < 4000 else "湍流")
        return {"re": re, "lambda": lam, "dp_kpa": dp_pa / 1000.0,
                "head_m": head_m, "regime": regime}

    def _pressure_drop_text(self, diameter_mm, velocity, density):
        """生成压降估算文本段（无粘度数据时返回空串）"""
        mu = self._current_viscosity()
        if mu is None:
            return ""
        dp = self._estimate_pressure_drop(diameter_mm, velocity, density, mu)
        if dp is None:
            return ""
        return f"""
────────────
压降估算 (每100m直管, Darcy-Weisbach)
────────────

    粘度: {mu * 1000:g} mPa·s   流态: {dp['regime']} (Re = {dp['re']:,.0f})
    摩阻系数 λ = {dp['lambda']:.4f}

    • 压降: {dp['dp_kpa']:.1f} kPa/100m
    • 水力坡降: {dp['head_m']:.2f} m液柱/100m

    注：仅计直管摩擦，未含弯头/阀门局部阻力（工程上通常另加
    10%~50%）；粘度为典型经验值，重要管路请以实测粘度复核。"""

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
            "淀粉调浆液",
            "液化液",
            "糖化液",
            "脱色液",
            "葡萄糖浆",
            "自定义粘性液体(按粘度推荐)",
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
        # 默认选"水及粘度相似的液体"，自动填充推荐流速/温度/流量
        self.fluid_combo.setCurrentIndex(2)
        
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
            # 修正记录（2026-09-16）：fluid_ranges / 下拉框里叫「蒸汽冷凝液」，
            # 本表此前只登记了「蒸汽冷凝水」，导致选中它时 update_density() 落空
            # 静默退回 1000 —— 与 fluid_data 同义的三个名字必须都在。
            "蒸汽冷凝液": 1000,
            "过热水": 1000,
            "海水，微碱水": 1025,
            "粘度较大的液体": 1200,
            # 淀粉糖物料典型密度[E]（随干物浓度变化：调浆液/液化液/糖化液按
            # 32~40%DS 取值，脱色液按 40~50%DS，葡萄糖浆按 75~80%DS）
            "淀粉调浆液": 1130,
            "液化液": 1140,
            "糖化液": 1160,
            "脱色液": 1190,
            "葡萄糖浆": 1390,
            "自定义粘性液体(按粘度推荐)": 1200,
            # 液氨 20°C 饱和液氨密度 610 kg/m³。
            # 修正记录（2026-09-16）：原值 682 是 −33°C（常压沸点）的密度，
            # 被误置于「液体类 (20°C)」下，使液氨管径计算偏小约 6%。
            # 依据：本项目 pure_substance_properties.DENS_TABLES["氨"] = (20, 610.3)。
            "液氨": 610,
            # 氢氧化钠溶液：原值 2130 是**固体烧碱**的密度（CRC 2.13 g/cm³），
            # 与液氨同类错误 —— 被误置于「液体类 (20°C)」下，会使碱液管径偏小约 43%。
            # 修正为 20°C、20% 溶液的 1219 kg/m³（化学化工物性数据手册 表5.2.6：
            # 20°C 20% = 1.2191 g/cm³；ChemLin / ProTank 同值）。
            # ⚠ 本表一种流体只存一个密度，不随 fluid_ranges 的
            #   「浓度0~30% / 30~50% / 50~73%」分档变化。
            "氢氧化钠": 1219,
            "四氯化碳": 1594,
            "硫酸": 1830,
            "盐酸": 1200,
            # 氯化钠溶液：原值 2160 是**固体食盐**的密度，非液体 —— 与液氨/烧碱同类错误。
            # 修正为 20°C、25% 盐水的 1190 kg/m³（与本项目 pressure_drop_calculator 的
            # 「氯化钠(25%溶液) (20°C) - 密度 1190.0」一致；资料库「饱和食盐水」25°C 为 1200）。
            "氯化钠": 1190,
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
            self._hide_viscosity_row()
            self._hide_density_row()
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

        # 自定义粘性液体 → 显示粘度/密度行，流速由粘度推荐
        if text == "自定义粘性液体(按粘度推荐)":
            self._show_viscosity_row()
            self._show_density_row()
            self.velocity_input.setPlaceholderText("输入粘度后自动推荐")
            self.condition_hint.setText("输入粘度后流速自动推荐")
        else:
            self._hide_viscosity_row()
            self._hide_density_row()
            self.velocity_input.setPlaceholderText("选择流体后自动填入")
    
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
                tip = f"推荐范围: {vel_min}~{vel_max} m/s（已自动填入 {vel:.1f}）"
                if "viscosity" in ranges:
                    mu_lo, mu_hi = ranges["viscosity"]
                    tip += (f"；典型粘度 {mu_lo * 1000:g}~{mu_hi * 1000:g} mPa·s"
                            f"（经验值[E]，压降按中值估算）")
                self.velocity_input.setToolTip(tip)

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
        self.viscosity_input.clear()
        self.density_input.setText("1200")
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
        actual_vel = self.calculate_actual_velocity(flow_rate, closest_diam, density, fluid, condition)

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
    • 实际流速: {actual_vel:.2f} m/s

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
    • 计算结果仅供参考，实际选择需考虑具体工况""" + self._pressure_drop_text(
            closest_diam, actual_vel, density)

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
    • 计算结果仅供参考，实际应用请考虑安全系数""" + self._pressure_drop_text(
            diameter_mm, velocity, density)

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
        mu = self._current_viscosity()

        inputs = {
            "计算模式": mode,
            "流体类型": fluid,
            "计算条件": condition,
            "流速_m_s": velocity,
            "密度_kg_m3": density,
            "压力_MPa": pressure
        }
        if mu:
            inputs["粘度_mPa_s"] = round(mu * 1000, 1)
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
                actual_vel = self.calculate_actual_velocity(flow_rate, closest_diam, density, fluid, condition)
                outputs["实际流速_m_s"] = round(actual_vel, 2)
                dp = self._estimate_pressure_drop(closest_diam, actual_vel, density, mu) if mu else None
                if dp:
                    outputs["压降_kPa_100m"] = round(dp["dp_kpa"], 1)
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
        return {
            "project_name": "管道直径计算",
            "calculator_name": "管径计算器",
            "version": "1.0",
            "description": "根据流体类型和计算条件计算管道直径或流量"
        }
    
    def generate_report(self):
        """生成计算书"""
        content = self.result_text.toPlainText().strip()
        if not content:
            return "尚未进行计算。"
        lines = ["工程计算书 - 管道直径计算", "=" * 50, "", content]
        return "\n".join(lines)
    
    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "管径计算")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "管径计算")

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = 管径计算()
    calculator.resize(1200, 800)
    calculator.show()
    
    sys.exit(app.exec())