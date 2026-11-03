from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox,
    QScrollArea, QButtonGroup, QGridLayout, QSizePolicy, QCheckBox
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
        # 预设/手改状态：程序填值期间 _filling=True，避免把预设值误判成「已手动修改」
        self._filling = False
        self._density_manual = False
        self._velocity_preset = None      # (lo, hi, text) 当前预设流速
        self._current_density = 1000.0
        
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
        """根据 HG/T 20570-95《工艺系统工程设计技术规定》设置流体对应的参数范围。

        推荐流速、压力适用范围、粘度档（0.05/0.1/1 Pa·s）与泵进出口流速
        均取自该标准的常用介质流速表，统一按标准原文标注，便于审图时追溯依据。
        """
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
        # ── 固液浆料档（2026-11-02 新增）──────────────────────────
        # 单相预设对含固物料是错的：管径由「不淤流速」控制而不是推荐流速，
        # 密度随含固量变，压降随表观粘度非线性上升。本档只给占位区间，
        # 真正的流速/密度由固相+浓度+粒径算出（见 _refresh_slurry）。
        self.fluid_ranges[self.SLURRY_FLUID] = {
            "按固相与浓度自动推荐": {
                "velocity": (0.6, 2.5), "flow": (0, 0), "pressure": (0, 0),
                "flow_unit": "m³/h", "slurry": True}
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
            "根据流体类型和计算条件计算管道直径或流量，推荐流速取自"
            " HG/T 20570-95《工艺系统工程设计技术规定》。\n"
            "含固物料（硅藻土、活性炭、白土、树脂等）选「浆料/悬浮液」档，按固相、浓度、粒径"
            "算防沉积流速与浆料压降；粘性物料（淀粉糖浆等）可选专用档或「自定义粘性液体」。"
            "结果页附每 100m 直管压降，并按该标准的百米压降控制值给出校核结论。"
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
        
        # 3. 预设组：只负责把手册默认值填进下方参数，填完可改
        preset_group = CalculatorBase.make_group_box("预设（选完自动填下方参数，填完可改）")
        preset_layout = QGridLayout(preset_group)
        preset_layout.setVerticalSpacing(10)
        preset_layout.setHorizontalSpacing(10)
        preset_layout.setColumnStretch(0, 4)
        preset_layout.setColumnStretch(1, 8)
        preset_layout.setColumnStretch(2, 5)

        prow = 0

        # ── 流体类型 ──
        fluid_label = QLabel("流体类型:")
        fluid_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fluid_label.setStyleSheet(label_style)
        preset_layout.addWidget(fluid_label, prow, 0)

        self.fluid_combo = QComboBox()
        self.fluid_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_fluid_options()
        self.fluid_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.fluid_combo.currentTextChanged.connect(self.on_fluid_changed)
        preset_layout.addWidget(self.fluid_combo, prow, 1)

        # 流体决定密度与可选条件清单
        self.fluid_hint = QLabel("决定密度与可选条件")
        self.fluid_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        preset_layout.addWidget(self.fluid_hint, prow, 2)

        prow += 1

        # ── 查找流体（不改下拉可编辑性：可编辑 QComboBox 的
        #    setCurrentText 对不存在的项会静默新建条目，联动会读到假档）──
        filter_label = QLabel("查找:")
        filter_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        filter_label.setStyleSheet(label_style)
        preset_layout.addWidget(filter_label, prow, 0)

        self.fluid_filter = QLineEdit()
        self.fluid_filter.setPlaceholderText("输入关键字过滤，如「糖」「蒸汽」「炭」")
        self.fluid_filter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.fluid_filter.textChanged.connect(self._filter_fluids)
        preset_layout.addWidget(self.fluid_filter, prow, 1)

        self.filter_hint = QLabel("")
        self.filter_hint.setStyleSheet("font-size: 10px;")
        self.filter_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        preset_layout.addWidget(self.filter_hint, prow, 2)

        prow += 1

        # ── 计算条件 ──
        condition_label = QLabel("计算条件:")
        condition_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        condition_label.setStyleSheet(label_style)
        preset_layout.addWidget(condition_label, prow, 0)

        self.condition_combo = QComboBox()
        self.condition_combo.setStyleSheet(COMBOBOX_STYLE)
        self.condition_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.condition_combo.currentTextChanged.connect(self.on_condition_changed)
        preset_layout.addWidget(self.condition_combo, prow, 1)

        # 条件决定推荐流速与压力适用范围
        self.condition_hint = QLabel("决定推荐流速与压力范围")
        self.condition_hint.setStyleSheet("font-style: italic;")
        self.condition_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        preset_layout.addWidget(self.condition_hint, prow, 2)

        prow += 1

        left_layout.addWidget(preset_group)

        # 4. 参数组：全部可编辑，预设只提供默认值
        input_group = CalculatorBase.make_group_box("参数（预设填入后仍可修改）")
        
        # 使用GridLayout确保整齐排列
        input_layout = QGridLayout(input_group)
        self.input_layout = input_layout  # 保存引用，供模式切换使用
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)
        
        row = 0

        # ── 第1行：流速（始终显示）──
        velocity_label = QLabel("流速 (m/s):")
        velocity_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        velocity_label.setStyleSheet(label_style)
        input_layout.addWidget(velocity_label, row, 0)

        self.velocity_input = QLineEdit()
        self.velocity_input.setPlaceholderText("选流体后自动填入，可改")
        self.velocity_input.setValidator(QDoubleValidator(0.1, 150.0, 2))
        self.velocity_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.velocity_input.textChanged.connect(self._on_velocity_changed)
        input_layout.addWidget(self.velocity_input, row, 1)

        # 第三列：来源标注（预设值 / 已手动修改）
        self.velocity_hint = QLabel("")
        self.velocity_hint.setStyleSheet("font-size: 10px;")
        self.velocity_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.velocity_hint, row, 2)

        row += 1

        # ── 第2行：流量 / 管道内径（按模式切换）──
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

        # ── 泵配管联算（仅「由流量计算管径」+ 液体时显示）──
        # 属输出口径的参数：勾了就不只给一排管径，而是排出/吸入成对给
        self.pump_pair_check = QCheckBox("同时计算泵吸入管")
        self.pump_pair_check.setToolTip(
            "勾选后一次给出排出管与吸入管两套推荐管径。\n"
            "吸入流速自动取低值：手册有成对吸入档的按手册取中值，\n"
            "否则取排出管流速的 0.6 倍且不低于 0.3 m/s（防汽蚀，经验取法[E]）。\n"
            "吸入管径保证不小于排出管径（相等时升一档）。仅液体（m³/h）可用。")
        self.pump_pair_check.setVisible(False)
        input_layout.addWidget(self.pump_pair_check, row, 1, 1, 2)

        row += 1

        # ── 压力（部分流体显示）──
        self.pressure_label = QLabel("压力 (MPa):")
        self.pressure_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.pressure_label.setStyleSheet(label_style)

        self.pressure_input = QLineEdit()
        self.pressure_input.setPlaceholderText("选流体后自动填入，可改")
        self.pressure_input.setValidator(QDoubleValidator(0.0, 150.0, 2))
        self.pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # 压力变化要重算气体的工况密度（标态流量按此折算）
        self.pressure_input.textChanged.connect(self._on_pressure_changed)

        self.pressure_range_label = QLabel("")
        self.pressure_range_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        self.pressure_range_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # 压力行初始显示（默认可见）
        self._add_pressure_row(input_layout, row)
        self._pressure_row = row

        row += 1

        # ── 温度（仅过热蒸汽显示）──
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

        # ── 粘度（仅「自定义粘性液体」显示）──
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

        # ── 浆料四行（仅「浆料/悬浮液(含固)」显示）──
        # 行号连续占 4 行，隐藏时整块折叠
        self.solid_label = QLabel("固相:")
        self.solid_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.solid_label.setStyleSheet(label_style)
        self.solid_combo = QComboBox()
        self.solid_combo.setStyleSheet(COMBOBOX_STYLE)
        self.solid_combo.addItems(list(self.SLURRY_SOLIDS.keys()))
        self.solid_combo.setCurrentText("硅藻土(助滤剂)")
        self.solid_combo.currentTextChanged.connect(self._on_solid_changed)

        # 液相密度（第三列）：糖液脱色时液相不是水，必须能改
        self.liquid_rho_input = QLineEdit("1000")
        self.liquid_rho_input.setPlaceholderText("液相密度 kg/m³")
        self.liquid_rho_input.setValidator(QDoubleValidator(500.0, 3000.0, 1))
        self.liquid_rho_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.liquid_rho_input.textChanged.connect(self._refresh_slurry)

        self.solid_pct_label = QLabel("固相浓度 (wt%):")
        self.solid_pct_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.solid_pct_label.setStyleSheet(label_style)
        self.solid_pct_input = QLineEdit("3")
        self.solid_pct_input.setPlaceholderText("例如: 3（车间说的 3% 炭浆）")
        self.solid_pct_input.setValidator(QDoubleValidator(0.1, 60.0, 2))
        self.solid_pct_input.textChanged.connect(self._refresh_slurry)

        self.solid_d50_label = QLabel("粒径 d50 (μm):")
        self.solid_d50_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.solid_d50_label.setStyleSheet(label_style)
        self.solid_d50_input = QLineEdit("")
        self.solid_d50_input.setPlaceholderText("选固相后自动填入，可按实测改")
        self.solid_d50_input.setValidator(QDoubleValidator(0.5, 50000.0, 1))
        self.solid_d50_input.textChanged.connect(self._refresh_slurry)

        self.slurry_hint = QLabel("")
        self.slurry_hint.setStyleSheet("font-size: 10px; color: #7f8c8d;")
        self.slurry_hint.setWordWrap(True)
        self.slurry_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._add_slurry_rows(input_layout, row)
        self._slurry_row = row
        self._hide_slurry_rows()
        row += 4

        # ── 密度（常显、可改；不同流量单位下作用不同）──
        self.density_label = QLabel("密度 (kg/m³):")
        self.density_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.density_label.setStyleSheet(label_style)

        self.density_input = QLineEdit("1200")
        self.density_input.setPlaceholderText("例如: 1200")
        self.density_input.setValidator(QDoubleValidator(1.0, 20000.0, 1))
        self.density_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.density_input.textChanged.connect(self._on_density_changed)

        self.density_hint = QLabel("")
        self.density_hint.setStyleSheet("font-size: 10px;")
        self.density_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._add_density_row(input_layout, row)
        self._density_row = row

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

    # ── 浆料四行：固相 / 固相浓度 / 粒径 / 提示（占 4 个连续行号）──
    def _add_slurry_rows(self, layout, row):
        layout.addWidget(self.solid_label, row, 0)
        layout.addWidget(self.solid_combo, row, 1)
        layout.addWidget(self.liquid_rho_input, row, 2)

        layout.addWidget(self.solid_pct_label, row + 1, 0)
        layout.addWidget(self.solid_pct_input, row + 1, 1)

        layout.addWidget(self.solid_d50_label, row + 2, 0)
        layout.addWidget(self.solid_d50_input, row + 2, 1)

        layout.addWidget(self.slurry_hint, row + 3, 0, 1, 3)

    def _show_slurry_rows(self):
        for w in [self.solid_label, self.solid_combo, self.liquid_rho_input,
                  self.solid_pct_label, self.solid_pct_input,
                  self.solid_d50_label, self.solid_d50_input, self.slurry_hint]:
            w.setVisible(True)

    def _hide_slurry_rows(self):
        for w in [self.solid_label, self.solid_combo, self.liquid_rho_input,
                  self.solid_pct_label, self.solid_pct_input,
                  self.solid_d50_label, self.solid_d50_input, self.slurry_hint]:
            w.setVisible(False)

    # ------------------------------------------------------------
    #  粘度 → 推荐流速 / 压降估算
    # ------------------------------------------------------------

    #: 粘度分级推荐流速（m/s），经验值[E]：
    #: 锚点 = HG/T 20570-95 粘度档（0.05/0.1/1 Pa·s）与熟化淀粉管道
    #: 设计指南（防沉降最低 0.3 m/s），分级间平滑过渡。
    VISCOSITY_VELOCITY_BANDS = [
        (50,        1.5, 3.0),   # 类水稀液
        (500,       0.8, 1.5),   # 稀糖液/糖化液
        (2000,      0.5, 1.0),   # 液化液
        (10000,     0.3, 0.6),   # 浓糖浆（容积泵）
        (float("inf"), 0.1, 0.3) # 超高粘（冷糖膏）
    ]

    #: 百米直管允许压降（kPa/100m），HG/T 20570-95《工艺系统工程设计技术规定》
    #: 表 2.0.2-2「每 100m 管长的压力降控制值」。标准给的区间照录，
    #: 判合格时与区间**上限**比较（不超过上限即可接受）。
    #: 顺序按允许值由严到宽排列，便于结果页直接读出「能达到哪一档」。
    DP_ALLOW_KPA_100M = [
        ("自流液体",              5.0,  5.0),
        ("泵吸入（饱和液体）",    10.0, 11.0),
        ("泵吸入（不饱和液体）",  20.0, 22.0),
        ("循环冷却水",            30.0, 30.0),
        ("泵排出（≥150 m³/h）",   45.0, 45.0),
        ("泵排出（<150 m³/h）",   45.0, 50.0),
    ]

    @classmethod
    def check_pressure_drop(cls, dp_kpa):
        """按 HG/T 20570-95 逐类别校核百米压降，返回 (明细, 结论)。

        明细：[{name, lo, hi, ok}]；结论：可直接写进结果页/历史的一句话。
        判据：dp ≤ hi 即满足该类别。dp 为 None 时返回 (None, "")。
        """
        if dp_kpa is None:
            return None, ""
        rows = []
        for name, lo, hi in cls.DP_ALLOW_KPA_100M:
            rows.append({"name": name, "lo": lo, "hi": hi,
                         "ok": dp_kpa <= hi + 1e-9})
        passed = [r["name"] for r in rows if r["ok"]]
        if len(passed) == len(rows):
            note = "各类别均满足，可作泵吸入管使用"
        elif passed:
            # 满足的最宽一档 = 可安全用作该类别；更严的类别需放大管径
            note = f"可作「{passed[-1]}」；更严格的类别不满足，需放大管径"
        else:
            note = "所有类别均超出控制值，建议放大一档管径后复核"
        return rows, note

    # ══════════════════════════════════════════════════════════
    #  固液浆料（含固）模型
    # ══════════════════════════════════════════════════════════
    #: 浆料档名称（多处判断用，避免字符串散落）
    SLURRY_FLUID = "浆料/悬浮液(含固)"

    #: 固相库：名称 → (真密度 kg/m³, d50 典型 μm)
    #: 真密度取手册值（硅藻土 2.1~2.3、活性炭 1.8~2.0、白土 2.4~2.6、
    #: 湿树脂 1.15~1.25、石灰石 2.7、淀粉 1.5、玉米芯渣 1.3~1.5）；
    #: d50 为行业典型值[E]，实际以激光粒度实测为准，界面可改。
    SLURRY_SOLIDS = {
        "硅藻土(助滤剂)":   (2200.0, 25.0),
        "活性炭(粉末)":     (1900.0, 20.0),
        "活性炭(颗粒)":     (1900.0, 1200.0),
        "白土(脱色)":       (2500.0, 30.0),
        "离子交换树脂":     (1200.0, 600.0),
        "石灰石粉(石灰乳)": (2700.0, 50.0),
        "淀粉(未糊化)":     (1500.0, 30.0),
        "玉米芯渣":         (1400.0, 1500.0),
        "自定义":           (None, None),
    }

    #: 临界流速判据分界（μm）：< 该值颗粒受粘性支配，用 Thomas(1979)；
    #: ≥ 该值用 Oroskar-Turian(1980)。两者都算、取大者（PNNL-37669 实践）。
    SLURRY_FINE_LIMIT_UM = 74.0
    #: 设计流速 = 临界流速 × 安全系数（PNNL 取 1.2~1.3，此处取中）
    SLURRY_SAFETY = 1.25
    #: 经验最小流速下限（m/s）：细颗粒 1.2（4 ft/s，HDPE 浆管手册）、粗颗粒 1.5
    SLURRY_MIN_VEL_FINE = 1.2
    SLURRY_MIN_VEL_COARSE = 1.5
    #: 磨损流速上限（m/s）：活性炭等硬颗粒 >2.5 对 304 弯头冲刷明显；树脂取 2.0
    SLURRY_MAX_WEAR_VEL = 2.5
    SLURRY_MAX_WEAR_VEL_SOFT = 2.0
    #: 最大堆积体积分数（Krieger-Dougherty 用）
    SLURRY_PHI_MAX = 0.63

    @staticmethod
    def slurry_volume_fraction(w_pct, rho_s, rho_l):
        """固相质量浓度(wt%) → 体积分数 φ。参数无效返回 None。"""
        if not (rho_s and rho_l and 0 < w_pct < 100):
            return None
        w = w_pct / 100.0
        v_s = w / rho_s
        v_l = (1.0 - w) / rho_l
        tot = v_s + v_l
        return (v_s / tot) if tot > 0 else None

    @staticmethod
    def slurry_density(w_pct, rho_s, rho_l):
        """浆料密度 ρm (kg/m³) = 1/(w/ρs + (1-w)/ρl)。"""
        if not (rho_s and rho_l and 0 < w_pct < 100):
            return None
        w = w_pct / 100.0
        return 1.0 / (w / rho_s + (1.0 - w) / rho_l)

    @classmethod
    def slurry_apparent_viscosity(cls, phi, mu_l):
        """Krieger-Dougherty 相对粘度 → 表观粘度 (Pa·s)。

        η_r = (1 − φ/φmax)^(−2.5·φmax)，φmax = 0.63，本征粘度取 2.5。
        细颗粒均质浆液（硅藻土、活性炭、白土）用它把含固量折进压降计算；
        粗颗粒浆料本式会低估，结果页另有附加系数提示。
        """
        if phi is None or mu_l is None or not (0 <= phi < cls.SLURRY_PHI_MAX):
            return None
        eta_r = (1.0 - phi / cls.SLURRY_PHI_MAX) ** (-2.5 * cls.SLURRY_PHI_MAX)
        return mu_l * eta_r

    @classmethod
    def slurry_critical_velocity(cls, d_um, D_mm, rho_s, rho_l, mu_l, phi):
        """临界不淤流速 (m/s)，返回 (v, 依据)；无法计算返回 (None, "")。

        细颗粒 Thomas(1979)：v = 9.0·[μ·g(S−1)/ρ]^0.37·(ρD/μ)^0.11
        粗颗粒 Oroskar-Turian(1980)：含粒径、体积分数、d/D、雷诺数项
        d ≥ 74μm 时两式都算取大者（单一关联式在不同浓度下误差都很大）；
        d < 74μm 只用 Thomas —— OT 式在细颗粒域外推不可靠。
        """
        if not (d_um and d_um > 0 and D_mm and D_mm > 0
                and rho_s and rho_l and mu_l and mu_l > 0):
            return None, ""
        s_rel = rho_s / rho_l
        if s_rel <= 1.0:
            return None, ""
        g = 9.81
        d_m = d_um * 1e-6
        D_m = D_mm / 1000.0
        cands = []
        # Thomas(1979) —— 细颗粒受粘性支配，式中不含粒径；
        # 粗颗粒时偏保守，作为下限一起参与取大
        try:
            v_t = (9.0 * (mu_l * g * (s_rel - 1.0) / rho_l) ** 0.37
                   * (rho_l * D_m / mu_l) ** 0.11)
            cands.append((v_t, "Thomas 式"))
        except (ValueError, ZeroDivisionError, OverflowError):
            pass
        # Oroskar-Turian(1980) —— 名义适用 d ≥ 74μm，细颗粒不套用
        if d_um >= cls.SLURRY_FINE_LIMIT_UM and phi is not None and 0 < phi < 1:
            try:
                base = math.sqrt(g * d_m * (s_rel - 1.0))
                v_ot = (1.85 * base
                        * phi ** 0.1536
                        * (1.0 - phi) ** 0.3564
                        * (d_m / D_m) ** -0.378
                        * (rho_l * D_m * base / mu_l) ** 0.09
                        * (0.95 ** 0.30))
                cands.append((v_ot, "Oroskar-Turian 式"))
            except (ValueError, ZeroDivisionError, OverflowError):
                pass
        cands = [(v, n) for v, n in cands if v and v > 0]
        if not cands:
            return None, ""
        v, name = max(cands, key=lambda x: x[0])
        return v, name

    @classmethod
    def slurry_velocity(cls, d_um, rho_s, rho_l, mu_l, phi, solid_name=None):
        """浆料推荐流速（不依赖管径的预填值）：经验下限起，浓度高时上浮。

        真正的临界流速要等管径定了才能算（Thomas/OT 都含 D），
        所以这里只给工程下限，结果页再用实际 DN 回算校核。
        """
        fine = (d_um or 0) < cls.SLURRY_FINE_LIMIT_UM
        v = cls.SLURRY_MIN_VEL_FINE if fine else cls.SLURRY_MIN_VEL_COARSE
        # 体积分数超过 10% 的浓浆需要更高流速防沉积（经验[E]）
        if phi and phi > 0.10:
            v *= 1.0 + min(0.5, (phi - 0.10) * 3.0)
        return min(v, cls.slurry_max_velocity(solid_name))

    @classmethod
    def slurry_max_velocity(cls, solid_name=None):
        """磨损流速上限 (m/s)：树脂等软颗粒 2.0，其余 2.5。"""
        if solid_name and "树脂" in solid_name:
            return cls.SLURRY_MAX_WEAR_VEL_SOFT
        return cls.SLURRY_MAX_WEAR_VEL

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
        self._fill(self.velocity_input, f"{vel:.2f}")
        self._velocity_preset = (lo, hi, f"{vel:.2f}")
        self.velocity_hint.setText(f"按粘度 {mu:g} mPa·s 推荐 {lo:g}~{hi:g} m/s")

    # ------------------------------------------------------------
    #  浆料档：固相 + 浓度 → 流速 / 密度 / 表观粘度
    # ------------------------------------------------------------

    def _is_slurry(self):
        """当前是否为浆料档。"""
        return self.fluid_combo.currentText() == self.SLURRY_FLUID

    def _slurry_inputs(self):
        """读浆料输入 → dict；非浆料档或关键输入不全返回 None。"""
        if not self._is_slurry():
            return None
        name = self.solid_combo.currentText()
        rho_s, d50_def = self.SLURRY_SOLIDS.get(name, (None, None))
        if not rho_s:
            return None
        try:
            w = float(self.solid_pct_input.text())
        except (ValueError, AttributeError):
            return None
        if not (0 < w < 100):
            return None
        d50 = d50_def
        d50_txt = self.solid_d50_input.text().strip()
        if d50_txt:
            try:
                d50 = float(d50_txt)
            except ValueError:
                pass
        try:
            rho_l = float(self.liquid_rho_input.text())
        except (ValueError, AttributeError):
            rho_l = 1000.0
        if rho_l <= 0:
            rho_l = 1000.0
        try:
            mu_l = float(self.viscosity_input.text()) / 1000.0
        except (ValueError, AttributeError):
            mu_l = None
        if not mu_l or mu_l <= 0:
            mu_l = 0.001          # 缺省按 20°C 水
        return {"name": name, "rho_s": rho_s, "d50": d50, "w": w,
                "rho_l": rho_l, "mu_l": mu_l}

    def _slurry_state(self):
        """浆料完整状态：φ、ρm、μ_app、推荐流速。输入不全返回 None。"""
        inp = self._slurry_inputs()
        if inp is None:
            return None
        phi = self.slurry_volume_fraction(inp["w"], inp["rho_s"], inp["rho_l"])
        rho_m = self.slurry_density(inp["w"], inp["rho_s"], inp["rho_l"])
        mu_app = self.slurry_apparent_viscosity(phi, inp["mu_l"])
        v = self.slurry_velocity(inp["d50"], inp["rho_s"], inp["rho_l"],
                                 inp["mu_l"], phi, inp["name"])
        return {**inp, "phi": phi, "rho_m": rho_m,
                "mu_app": mu_app, "velocity": v}

    def _refresh_slurry(self, *_):
        """浆料参数变化 → 重算流速 / 密度 / 提示（不触发联动重入）。"""
        if self._filling or not self._is_slurry():
            return
        st = self._slurry_state()
        if st is None:
            self.slurry_hint.setText("填齐固相、浓度与液相密度后自动推荐流速")
            return
        vmax = self.slurry_max_velocity(st["name"])
        v = min(st["velocity"], vmax)
        self._fill(self.velocity_input, f"{v:.2f}")
        self._velocity_preset = (v, vmax, f"{v:.2f}")
        self.velocity_hint.setText(f"防沉积下限 {v:.2f}（磨损上限 {vmax:g}）")
        # 密度按含固量算：改浓度必然重算，手填值只在浓度不变时保留
        self._current_density = st["rho_m"]
        self._fill(self.density_input, f"{st['rho_m']:.1f}")
        self.density_hint.setText("浆料密度（按含固量算，可改）")
        self.slurry_hint.setText(
            f"固相体积分数 {st['phi'] * 100:.1f}%"
            f" · 表观粘度 {st['mu_app'] * 1000:.2f} mPa·s"
            f" · 液相 {st['rho_l']:g} kg/m³")

    def _on_solid_changed(self, text):
        """切换固相：d50 填回典型值后刷新。"""
        _rho_s, d50 = self.SLURRY_SOLIDS.get(text, (None, None))
        if d50 is not None:
            self._fill(self.solid_d50_input, f"{d50:g}")
        self._refresh_slurry()

    # ───────────────── 参数填写 / 手改标记 ─────────────────
    def _fill(self, widget, text):
        """程序填值：不触发「已手动修改」判定，也不触发联动重入。"""
        self._filling = True
        try:
            widget.setText(text)
        finally:
            self._filling = False

    def _flow_unit_of(self, fluid=None, condition=None):
        """当前（或指定）流体·条件的流量单位；查不到返回 None。

        条件不属于该流体时（结果页可能只给流体名），回退取该流体任一条件的单位。
        """
        fluid = fluid if fluid is not None else self.fluid_combo.currentText()
        condition = condition if condition is not None else self.condition_combo.currentText()
        rng = self.fluid_ranges.get(fluid, {}).get(condition)
        if rng:
            return rng.get("flow_unit")
        for r in self.fluid_ranges.get(fluid, {}).values():
            if r.get("flow_unit"):
                return r["flow_unit"]
        return None

    def _on_velocity_changed(self, text):
        """流速手改：第三列标注来源（预设 / 已改）"""
        if self._filling:
            return
        self.velocity_hint.setText(self._velocity_hint_text(text, manual=True))

    def _velocity_hint_text(self, text=None, manual=False):
        """流速行的来源说明文案。"""
        text = (self.velocity_input.text() if text is None else text).strip()
        if not self._velocity_preset:
            return "手动输入" if text else ""
        lo, hi, preset = self._velocity_preset
        if not text:
            return f"手册 {lo:g}~{hi:g} m/s"
        if manual:
            return f"已改 {text} m/s（手册 {lo:g}~{hi:g}）"
        return f"预设 {text} m/s（手册 {lo:g}~{hi:g}）"

    def _on_pressure_changed(self, text):
        """压力手改：气体档工况密度要跟着重算（密度被手改过则不覆盖）。"""
        if self._filling:
            return
        if self._flow_unit_of() == "Nm³/h":
            self._refresh_density()

    def _on_density_changed(self, text):
        """密度手改：无论哪个档位都实时生效，并标记为手动值。"""
        if self._filling:
            return
        try:
            rho = float(text)
        except ValueError:
            return
        if rho > 0:
            self._current_density = rho
            self._density_manual = True
            self.density_hint.setText("已改（手动值，切预设会重置）")

    def _read_density(self):
        """计算时取密度：优先输入框，无效则回退内部值。"""
        try:
            rho = float(self.density_input.text())
            if rho > 0:
                return rho
        except (ValueError, AttributeError):
            pass
        return self._current_density

    def _current_viscosity(self):
        """当前粘度 (Pa·s)；无粘度数据时返回 None。

        自定义档取用户输入（mPa·s → Pa·s）；预设档取典型范围中值；
        浆料档返回含固后的表观粘度（Krieger-Dougherty）。
        """
        fluid = self.fluid_combo.currentText()
        if fluid == self.SLURRY_FLUID:
            st = self._slurry_state()
            return st["mu_app"] if st else None
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
        rows, note = self.check_pressure_drop(dp["dp_kpa"])
        check_lines = []
        for r in rows:
            allow = (f"{r['lo']:g}" if r["lo"] == r["hi"]
                     else f"{r['lo']:g}~{r['hi']:g}")
            mark = "✓" if r["ok"] else "✗"
            check_lines.append(f"    {mark} {r['name']}  允许 {allow} kPa/100m")
        check_block = "\n".join(check_lines)
        return f"""
────────────
压降估算 (每100m直管, Darcy-Weisbach)
────────────

    粘度: {round(mu * 1000, 2):g} mPa·s   流态: {dp['regime']} (Re = {dp['re']:,.0f})
    摩阻系数 λ = {dp['lambda']:.4f}

    • 压降: {dp['dp_kpa']:.1f} kPa/100m
    • 水力坡降: {dp['head_m']:.2f} m液柱/100m

────────────
压降校核 (HG/T 20570-95 每100m管长压力降控制值)
────────────

    本工况 {dp['dp_kpa']:.1f} kPa/100m（未含局部阻力）

{check_block}

    结论: {note}

    注：仅计直管摩擦，未含弯头/阀门局部阻力（工程上通常另加
    10%~50%）；粘度为典型经验值，重要管路请以实测粘度复核。"""

    def _slurry_check_text(self, diameter_mm, velocity):
        """浆料专属校核段：临界不淤流速 / 磨损上限。非浆料档返回空串。

        顺序很重要：临界流速两式都含管径 D，所以必须等 DN 定下来再回算，
        不能反过来用临界流速定管径（会循环依赖）。
        """
        st = self._slurry_state()
        if st is None:
            return ""
        vc, method = self.slurry_critical_velocity(
            st["d50"], diameter_mm, st["rho_s"], st["rho_l"],
            st["mu_l"], st["phi"])
        if vc is None:
            return ""
        v_req = vc * self.SLURRY_SAFETY
        vmax = self.slurry_max_velocity(st["name"])
        ok_settle = velocity >= v_req - 1e-9
        ok_wear = velocity <= vmax + 1e-9
        coarse = (st["d50"] or 0) >= self.SLURRY_FINE_LIMIT_UM
        wear_note = "未超" if ok_wear else "已超，建议放大管径或降流量"
        coarse_note = (
            "\n    注：粗颗粒（d50 ≥ 74 μm）实际压降可能再高 10%~30%，"
            "\n    弯头取 R/D≥5 并做耐磨处理（陶瓷/超高分子量聚乙烯）。"
            if coarse else "")
        return f"""
────────────
浆料校核 (固液两相, 管径定后回算)
────────────

    固相: {st['name']}   浓度 {st['w']:g} wt%   d50 {st['d50']:g} μm
    浆料密度: {st['rho_m']:.1f} kg/m³   固相体积分数: {st['phi'] * 100:.1f}%
    表观粘度: {st['mu_app'] * 1000:.2f} mPa·s（Krieger-Dougherty）

    临界不淤流速: {vc:.2f} m/s（{method}，按内径 {diameter_mm:.0f} mm 回算）
    设计最低流速: {v_req:.2f} m/s（×{self.SLURRY_SAFETY:g} 安全系数）

    {'✓' if ok_settle else '✗'} 实际流速 {velocity:.2f} m/s {'≥' if ok_settle else '<'} 设计最低 {v_req:.2f}
    {'✓' if ok_wear else '✗'} 磨损上限 {vmax:g} m/s（{wear_note}）

    注：低浓度时经验下限（细颗粒 1.2 / 粗颗粒 1.5 m/s）通常起控制作用，
    公式值只在浓浆或粗颗粒时才反超。{coarse_note}"""

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
        # 泵吸入管联算只在「由流量计算管径」模式下有意义
        self.pump_pair_check.setVisible(mode == "由流量计算管径")
    
    #: 流体下拉分组（工艺常用在前，手册冷门品归最后一组）。
    #: "- xxx -" 为分组标题，界面置灰不可选；分组只决定显示顺序，
    #: 数据源仍是 setup_fluid_ranges 里的 fluid_ranges（此处不重复定义参数）。
    FLUID_GROUPS = [
        ("- 水与蒸汽 -", [
            "水及粘度相似的液体", "过热水", "锅炉给水", "蒸汽冷凝液", "冷凝水",
            "饱和蒸汽", "过热蒸汽", "二次蒸汽", "乏汽", "高压乏汽",
            "自来水", "海水，微碱水", "排除废水"]),
        ("- 淀粉糖与糖醇 -", [
            "淀粉调浆液", "液化液", "糖化液", "脱色液", "葡萄糖浆",
            "浆料/悬浮液(含固)", "粘度较大的液体"]),
        ("- 酸碱盐溶液 -", [
            "氢氧化钠", "硫酸", "盐酸", "氯化钠", "液氨"]),
        ("- 气体 -", [
            "压缩气体", "气体", "氧气", "氮气", "氢气", "氮",
            "天然气", "煤气", "半水煤气", "烟道气", "石灰窑窑气",
            "氨气", "乙炔气", "乙烯气", "氢氮混合气"]),
        ("- 有机溶剂 -", [
            "乙二醇", "氯仿", "氯化氢", "溴", "氯化甲烷", "氯乙烷",
            "二氯乙烷", "三氯乙烷", "苯乙烯", "二溴乙烯", "四氯化碳"]),
        ("- 其他 -", ["泥状混合物", "自定义粘性液体(按粘度推荐)"]),
    ]

    #: 搜索别名：流体名 → 车间常用叫法/成分名。
    #: 名字里搜不到的（如「活性炭」在浆料档名下）靠别名命中，
    #: 否则用户按物料名找必然落空。
    FLUID_ALIASES = {
        "浆料/悬浮液(含固)": ["浆料", "悬浮液", "含固", "固液", "活性炭", "炭浆",
                              "硅藻土", "助滤剂", "白土", "树脂", "石灰乳", "石灰石"],
        "水及粘度相似的液体": ["水", "清水", "工艺水", "低粘度"],
        "淀粉调浆液": ["淀粉乳", "调浆", "淀粉浆"],
        "液化液": ["液化", "喷射液化"],
        "糖化液": ["糖化", "糖化醪"],
        "脱色液": ["脱色", "糖液", "脱色糖液"],
        "葡萄糖浆": ["糖浆", "葡萄糖", "淀粉糖", "糖醇"],
        "粘度较大的液体": ["高粘", "粘稠", "稠液"],
        "蒸汽冷凝液": ["冷凝水", "凝结水"],
        "冷凝水": ["凝结水", "冷凝液"],
        "氢氧化钠": ["碱液", "烧碱", "NaOH"],
        "液氨": ["氨", "氨水"],
        "饱和蒸汽": ["蒸汽", "低压蒸汽"],
        "过热蒸汽": ["蒸汽", "高温蒸汽"],
        "自来水": ["水", "市政水"],
        "海水，微碱水": ["海水", "微碱水"],
        "排除废水": ["废水", "排污"],
    }

    @classmethod
    def _fluid_matches(cls, name, kw):
        """流体名或其别名命中关键字。"""
        if kw in name.lower():
            return True
        return any(kw in a.lower() for a in cls.FLUID_ALIASES.get(name, ()))

    @classmethod
    def _fluid_options(cls):
        """下拉实际项 = 占位项 + 各组标题 + 组内流体（顺序即显示顺序）。"""
        out = ["- 请选择流体类型 -"]
        for title, items in cls.FLUID_GROUPS:
            out.append(title)
            out.extend(items)
        return out

    def _filter_fluids(self, text):
        """按关键字过滤流体下拉（只改显示项，不动 fluid_ranges）。

        当前选中的流体永远置顶保留：否则过滤后 currentText 会跳到别的档，
        而参数还是旧流体的，显示与计算就对不上了。
        与下拉「可编辑 + completer」方案相比，这样做不会让 setCurrentText
        静默新建不存在的条目（那会喂给联动逻辑一个假档）。
        """
        kw = (text or "").strip().lower()
        cur = self.fluid_combo.currentText()

        if not kw:
            items = self._fluid_options()
        else:
            items = []
            for title, group in self.FLUID_GROUPS:
                hits = [f for f in group if self._fluid_matches(f, kw)]
                if hits:
                    items.append(title)
                    items.extend(hits)
            if not items:
                self.filter_hint.setText("无匹配（清空可恢复全部）")
                return
        # 当前项不在结果里时置顶保留：包括「- 请选择流体类型 -」占位项，
        # 否则过滤后 currentIndex 会落到不可选的分组标题上，显示与参数状态打架
        if cur and cur not in items:
            items = [cur] + items

        n_hit = len([x for x in items if not x.startswith("-")])
        self.filter_hint.setText("" if not kw else f"{n_hit} 项")

        self.fluid_combo.blockSignals(True)
        try:
            self.fluid_combo.clear()
            self.fluid_combo.addItems(items)
            for _i in range(self.fluid_combo.count()):
                if self.fluid_combo.itemText(_i).startswith("-"):
                    _item = self.fluid_combo.model().item(_i)
                    if _item is not None:
                        _item.setEnabled(False)
            if cur in items:
                self.fluid_combo.setCurrentIndex(items.index(cur))
        finally:
            self.fluid_combo.blockSignals(False)

    def setup_fluid_options(self):
        """设置流体选项"""
        # 更新流体选项列表
        self.fluid_combo.clear()
        self.fluid_combo.addItems(self._fluid_options())
        # 分组标题（"- xxx -"）置灰不可选，避免误点后参数被清空
        for _i in range(self.fluid_combo.count()):
            if self.fluid_combo.itemText(_i).startswith("-"):
                _item = self.fluid_combo.model().item(_i)
                if _item is not None:
                    _item.setEnabled(False)
        # 默认选「水及粘度相似的液体」（此时尚未连信号，不会触发联动）
        self.fluid_combo.setCurrentText("水及粘度相似的液体")
        
        # 设置流体数据字典（密度值）
        self.fluid_data = {
            # 浆料档：密度随含固量变，由 _refresh_slurry 按 1/(w/ρs+(1-w)/ρl) 覆盖，
            # 此处只作查表占位（fluid_ranges/fluid_data 必须一一对应）
            "浆料/悬浮液(含固)": 1000.0,
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
            self._clear_preset_marks()
            self._fill(self.velocity_input, "")
            self.velocity_input.setToolTip("")
            self.velocity_hint.setText("")
            self._fill(self.pressure_input, "")
            self.pressure_input.setReadOnly(False)
            self.pressure_range_label.setText("")
            self._fill(self.flow_input, "")
            self.flow_input.setToolTip("")
            self.condition_hint.setText("决定推荐流速与压力范围")
            self._show_pressure_row()
            self._hide_temp_row()
            self._hide_viscosity_row()
            self._fill(self.density_input, "")
            self.density_hint.setText("选流体后自动填入，可改")
            self.pump_pair_check.setEnabled(False)
            self.pump_pair_check.setChecked(False)
            return

        # 切预设 = 重填：先复位手改标记，再按新预设填参数
        self._clear_preset_marks()
        self._fill(self.velocity_input, "")
        self.velocity_hint.setText("")
        self._fill(self.pressure_input, "")
        self.pressure_input.setReadOnly(False)
        self.pressure_range_label.setText("")
        self._fill(self.flow_input, "")
        self._fill(self.flow_input, "70")  # 默认流量

        self.update_condition_options(text)
        self.update_density(text)
        self.condition_hint.setText("决定推荐流速与压力范围")

        # 默认为全部流体显示压力行
        self._show_pressure_row()

        # 过热蒸汽 → 显示温度行
        if text == "过热蒸汽":
            self._show_temp_row()
        else:
            self._hide_temp_row()

        # 自定义粘性液体 → 显示粘度行，流速由粘度推荐
        if text == "自定义粘性液体(按粘度推荐)":
            self._hide_slurry_rows()
            self._show_viscosity_row()
            self.viscosity_label.setText("粘度 (mPa·s):")
            self.viscosity_hint.setText("输入后自动推荐流速并估算压降")
            self.velocity_input.setPlaceholderText("输入粘度后自动推荐")
            self.condition_hint.setText("输入粘度后流速自动推荐")
        elif text == self.SLURRY_FLUID:
            # 浆料：粘度框改作「液相粘度」，另有三行固相参数；
            # 压力不参与选型（按 m³/h 计），隐藏避免误导
            self._hide_slurry_rows()
            self._show_viscosity_row()
            self.viscosity_label.setText("液相粘度 (mPa·s):")
            self.viscosity_hint.setText("液相粘度（水=1），用于算临界流速")
            if not self.viscosity_input.text().strip():
                self._fill(self.viscosity_input, "1.0")
            self._show_slurry_rows()
            self._remove_pressure_row()
            self.velocity_input.setPlaceholderText("按固相与浓度自动推荐")
            self.condition_hint.setText("按固相、浓度、粒径自动推荐流速")
            self._refresh_slurry()
        else:
            self._hide_slurry_rows()
            self._hide_viscosity_row()
            self.viscosity_label.setText("粘度 (mPa·s):")
            self.viscosity_hint.setText("输入后自动推荐流速并估算压降")
            self.velocity_input.setPlaceholderText("选流体后自动填入，可改")
    
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
        """切换流体：重置为「自动」状态并按预设重填密度框。"""
        self._density_manual = False
        if fluid == "自定义粘性液体(按粘度推荐)":
            # 自定义档的密度由用户填：切过来时给个淀粉糖典型起点，之后不再自动覆盖
            rho = self.fluid_data.get(fluid, 1200.0)
            self._current_density = rho
            self._fill(self.density_input, f"{rho:.2f}")
            self.density_hint.setText("淀粉糖浆类典型 1100~1450，随浓度变化")
            return
        self._refresh_density()

    def _density_preset(self, fluid=None):
        """按当前预设算出的密度值 + 说明文字，返回 (rho, hint)。

        - m³/h（液体 / 按体积计的气体）：fluid_data 的典型密度。
          体积流量法管径与密度无关（d 只取决于 Q 与 u），密度仅供压降估算。
        - t/h（蒸汽、液氨等按质量计）：fluid_data 的密度，直接进管径公式。
        - Nm³/h（按标态体积计的气体）：按表压折算工况密度
          ρ = ρ_N × (273.15/293.15) × ((P+0.1013)/0.1013)，20°C 口径。
          原来的实现直接把标态密度当工况密度用，加压后管径偏大（0.5MPa 约偏大 2.35 倍）。
        """
        fluid = fluid if fluid is not None else self.fluid_combo.currentText()
        rho_n = self.fluid_data.get(fluid, 1000.0)
        unit = self._flow_unit_of(fluid)

        if unit == "Nm³/h":
            try:
                p = float(self.pressure_input.text())
            except (ValueError, AttributeError):
                p = 0.0
            rho = rho_n * (273.15 / 293.15) * ((p + 0.1013) / 0.1013)
            return rho, f"工况密度（按 {p:g} MPa 表压折算，20°C）"
        if unit == "t/h":
            return rho_n, "影响管径；随压力/温度变化，可按实际值改"
        return rho_n, "仅影响压降估算（体积流量法管径与密度无关）"

    def _density_note(self, fluid=None):
        """结果页里「密度」后面的口径说明（避免把气体工况密度当成标态密度）。"""
        fluid = fluid if fluid is not None else self.fluid_combo.currentText()
        unit = self._flow_unit_of(fluid)
        if unit == "Nm³/h":
            rho_n = self.fluid_data.get(fluid)
            if rho_n:
                return f"（工况密度，标态 {rho_n:g} kg/Nm³）"
        elif unit == "m³/h":
            return "（体积流量法，管径与密度无关；密度用于压降）"
        return ""

    def _refresh_density(self):
        """按预设重算密度框；用户手改过、或自定义档（密度由用户填）就不覆盖。"""
        if self._density_manual:
            return
        if self.fluid_combo.currentText() == "自定义粘性液体(按粘度推荐)":
            return
        rho, hint = self._density_preset()
        self._current_density = rho
        self._fill(self.density_input, f"{rho:.2f}")
        self.density_hint.setText(hint)

    def _clear_preset_marks(self):
        """切预设前的复位：清「手改」标记。"""
        self._density_manual = False
        self._velocity_preset = None


    def on_condition_changed(self, text):
        """处理条件变化 - 自动填入推荐值并控制压力/温度可见性"""
        if text.startswith("-") or not text.strip():
            self._fill(self.velocity_input, "")
            self.velocity_input.setToolTip("")
            self.velocity_hint.setText("")
            self.pressure_range_label.setText("")
            self._fill(self.pressure_input, "")
            self.pressure_input.setReadOnly(False)
            self._show_pressure_row()
            self._fill(self.flow_input, "")
            self.flow_input.setToolTip("")
            return

        if text:
            # 切条件也算切预设：复位手改标记，按新条件的预设重填
            self._clear_preset_marks()
            self.update_parameter_ranges()
            self.condition_hint.setText("推荐值已自动填入")
    
    def update_parameter_ranges(self):
        """更新参数范围并自动填入推荐值"""
        fluid = self.fluid_combo.currentText()
        condition = self.condition_combo.currentText()

        if fluid.startswith("-") or condition.startswith("-"):
            return

        ranges = self.fluid_ranges.get(fluid, {}).get(condition)
        if not ranges:
            return

        # 泵吸入管联算仅对液体（体积流量 m³/h）有意义
        if ranges.get("flow_unit") == "m³/h":
            self.pump_pair_check.setEnabled(True)
        else:
            self.pump_pair_check.setEnabled(False)
            self.pump_pair_check.setChecked(False)

        # 自动填入推荐流速（预设中点，填完可改）
        vel_min, vel_max = ranges["velocity"]
        if vel_min > 0 and vel_max > 0:
            if vel_min == vel_max:
                vel = vel_min  # 固定值
            else:
                vel = (vel_min + vel_max) / 2  # 使用推荐值（中点）
            _vtext = f"{vel:.1f}"
            self._fill(self.velocity_input, _vtext)
            self._velocity_preset = (vel_min, vel_max, _vtext)
            self.velocity_hint.setText(self._velocity_hint_text(_vtext))
            tip = f"推荐范围: {vel_min}~{vel_max} m/s（预设 {_vtext}，可改）"
            if "viscosity" in ranges:
                mu_lo, mu_hi = ranges["viscosity"]
                tip += (f"；典型粘度 {mu_lo * 1000:g}~{mu_hi * 1000:g} mPa·s"
                        f"（经验值[E]，压降按中值估算）")
            self.velocity_input.setToolTip(tip)

        # 更新压力范围 / 自动填入 / 显示与否
        pressure_min, pressure_max = ranges["pressure"]
        flow_unit = ranges["flow_unit"]
        if pressure_min == 0 and pressure_max == 0 and flow_unit != "Nm³/h":
            # 手册没给压力范围、且不需要压力折算 → 隐藏压力行
            self._remove_pressure_row()
        else:
            self._show_pressure_row()
            if pressure_min == pressure_max and pressure_min > 0:
                self.pressure_range_label.setText(f"固定值: {pressure_min} MPa")
                self._fill(self.pressure_input, f"{pressure_min}")
                self.pressure_input.setReadOnly(True)
            elif pressure_min > 0 or pressure_max > 0:
                self.pressure_range_label.setText(f"适用范围: {pressure_min}~{pressure_max} MPa")
                self.pressure_input.setReadOnly(False)
                # 只有上下限都有效时才填中值
                if pressure_min > 0 and pressure_max > 0:
                    p_mid = (pressure_min + pressure_max) / 2
                    self._fill(self.pressure_input, f"{p_mid:.2f}")
            else:
                # 手册无范围但气体折算必须知道压力 → 默认 0.1 MPa 表压，可改
                self.pressure_range_label.setText("标态流量按此表压折算工况体积")
                self.pressure_input.setReadOnly(False)
                if not self.pressure_input.text():
                    self._fill(self.pressure_input, "0.10")

        # 流量标签与单位（原来嵌在压力 else 分支里，无压力范围的档位会漏更新）
        self.flow_label.setText(f"流量 ({flow_unit}):")
        if not self.flow_input.text():
            self._fill(self.flow_input, "70")

        # 密度随预设/压力刷新（手改过则保留）
        self._refresh_density()
    
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
        self._clear_preset_marks()
        self._fill(self.velocity_input, "")
        self._fill(self.flow_input, "")
        self._fill(self.diameter_input, "")
        self._fill(self.temp_input, "")
        self._fill(self.viscosity_input, "")
        self._fill(self.density_input, "1200")
        # 浆料档参数复位（d50 会随固相选择自动带回典型值）
        self.solid_combo.setCurrentText("硅藻土(助滤剂)")
        self._fill(self.solid_pct_input, "3")
        self._fill(self.liquid_rho_input, "1000")
        self.velocity_hint.setText("")
        self.density_hint.setText("选流体后自动填入，可改")
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

            density = self._read_density()
            
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
    
    # 手册里「排出管 ↔ 吸入管」成对给出的条件（同一流体内的条件名）
    PUMP_SUCTION_PAIRS = {
        ("水及粘度相似的液体", "离心泵排出管"): "离心泵吸入管(常温)",
        ("水及粘度相似的液体", "离心泵排出管(70~110℃)"): "离心泵吸入管(常温)",
        ("水及粘度相似的液体", "高压离心泵排出管"): "离心泵吸入管(常温)",
        ("水及粘度相似的液体", "往复式泵排出管"): "往复式泵吸入管",
        ("水及粘度相似的液体", "齿轮泵排出管"): "齿轮泵吸入管",
    }

    def _pump_suction_velocity(self, fluid, condition, u_discharge):
        """吸入管流速取值（返回 (流速, 来源说明)）。

        优先级：① 手册成对吸入档的中值；② 排出管流速 × 0.6 且 ≥0.3 m/s
        （防汽蚀/防沉降，经验取法[E]）。
        """
        pair = self.PUMP_SUCTION_PAIRS.get((fluid, condition))
        if pair and pair in self.fluid_ranges.get(fluid, {}):
            lo, hi = self.fluid_ranges[fluid][pair]["velocity"]
            if lo > 0 and hi > 0:
                return (lo + hi) / 2, f"手册吸入档「{pair}」推荐 {lo:g}~{hi:g} m/s 取中值"
        return max(0.3, u_discharge * 0.6), "取排出管流速的 0.6 倍且不低于 0.3 m/s（防汽蚀，经验取法[E]）"

    def _pump_suction_dn(self, flow_rate, u_suction, density, fluid, condition, discharge_dn):
        """由同一流量算吸入管理论管径并圆整；保证吸入管径 > 排出管径（相等则升一档）。"""
        d_s = self.calculate_diameter_from_flow(flow_rate, u_suction, density, fluid, condition)
        sizes = [6, 8, 10, 15, 20, 25, 32, 40, 50, 65, 80, 100,
                 125, 150, 200, 250, 300, 350, 400, 450, 500]
        s_dn = min(sizes, key=lambda x: abs(x - d_s))
        if s_dn <= discharge_dn:
            bigger = [s for s in sizes if s > discharge_dn]
            s_dn = bigger[0] if bigger else s_dn
        return d_s, s_dn

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
        _dn = self._density_note(fluid)

        result = f"""═══════════
 输入参数
══════════

    计算模式: {mode}
    流体类型: {fluid}
    计算条件: {condition}
    压力: {pressure} MPa(G)
    流量: {flow_rate} {flow_unit}
    流速: {velocity} m/s
    密度: {density:.2f} kg/m³{_dn}

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
    • 计算结果仅供参考，实际选择需考虑具体工况"""

        # 泵吸入管联算：与排出管同流量、更低的吸入流速
        if self.pump_pair_check.isChecked():
            u_s, src = self._pump_suction_velocity(fluid, condition, velocity)
            d_s, s_dn = self._pump_suction_dn(flow_rate, u_s, density, fluid, condition, closest_diam)
            v_s = self.calculate_actual_velocity(flow_rate, s_dn, density, fluid, condition)
            result += f"""

══════════
泵吸入管配管（与排出管同流量一次算出）
══════════

    吸入管流速: {u_s:.2f} m/s（{src}）
    理论计算管径: {d_s:.1f} mm
    推荐标准管径: DN{s_dn}
    • 实际流速: {v_s:.2f} m/s

    说明:
    • 泵铭牌流量即进出口共同的流量（稳定工况下相等），吸入管按同一流量、更低流速选大管
    • 吸入管路应短而直、少弯头变径，阻力越小越不易汽蚀
    • 汽蚀余量校核请用「离心泵NPSHa计算」"""

        result += self._pressure_drop_text(closest_diam, actual_vel, density)
        result += self._slurry_check_text(closest_diam, actual_vel)

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
    密度: {density:.2f} kg/m³{self._density_note(fluid)}

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
            diameter_mm, velocity, density) + self._slurry_check_text(
            diameter_mm, velocity)

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
        density = self._read_density()
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
            inputs["表观粘度_mPa_s" if self._is_slurry() else "粘度_mPa_s"] = \
                round(mu * 1000, 2)
        # 浆料档：固相/浓度/粒径是复现结果的关键参数，必须入史
        _st = self._slurry_state() if self._is_slurry() else None
        if _st:
            inputs["固相"] = _st["name"]
            inputs["固相浓度_wt%"] = _st["w"]
            inputs["粒径_d50_um"] = _st["d50"]
            inputs["浆料密度_kg_m3"] = round(_st["rho_m"], 1)
            inputs["液相粘度_mPa_s"] = round(_st["mu_l"] * 1000, 2)
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
                    # 压降校核（HG/T 20570-95）：记「能达到的最宽类别」而不是整段说明，
                    # 历史列表放得下；完整对照见结果页与计算书
                    _rows, _ = self.check_pressure_drop(dp["dp_kpa"])
                    _passed = [r["name"] for r in _rows if r["ok"]]
                    outputs["压降校核"] = (
                        "全部满足" if len(_passed) == len(_rows)
                        else (_passed[-1] if _passed else "全部超出"))
                # 浆料：临界流速随管径变，按选定的 DN 回算后入史
                if _st:
                    _vc, _m = self.slurry_critical_velocity(
                        _st["d50"], closest_diam, _st["rho_s"],
                        _st["rho_l"], _st["mu_l"], _st["phi"])
                    if _vc:
                        outputs["临界不淤流速_m_s"] = round(_vc, 2)
                # 泵吸入管联算：吸入管径与吸入流速一并入史
                if self.pump_pair_check.isChecked():
                    u_s, _src = self._pump_suction_velocity(fluid, condition, velocity)
                    d_s, s_dn = self._pump_suction_dn(flow_rate, u_s, density, fluid, condition, closest_diam)
                    outputs["吸入管径"] = f"DN{s_dn}"
                    outputs["吸入管流速_m_s"] = round(
                        self.calculate_actual_velocity(flow_rate, s_dn, density, fluid, condition), 2)
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