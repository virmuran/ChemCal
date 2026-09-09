from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QLabel, QLineEdit, QPushButton, QComboBox,
                              QTextEdit, QGridLayout, QScrollArea, QFileDialog, QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math
import os
import importlib.util
import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K, G, ATM_PRESSURE_MPA, WATER_DENSITY, WATER_CP, load_steam_iapws, get_steam_props
from utils.docx_utils import ReportExporter
# DOCX 报告导出

# IAPWS-IF97 工业标准蒸汽物性（动态导入，避免 relative import 失败）
try:
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _parent_dir = os.path.dirname(_current_dir)
    _spec = importlib.util.spec_from_file_location(
        "steam_iapws",
        os.path.join(_parent_dir, "steam_iapws.py")
    )
    _steam_iapws = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_steam_iapws)

    iapws_steam = _steam_iapws.steam_properties
    iapws_mu = _steam_iapws.viscosity
    iapws_k = _steam_iapws.thermal_conductivity
except Exception as e:
    print(f"警告: 无法加载 IAPWS-IF97 模块: {e}")
    iapws_steam = iapws_mu = iapws_k = None

class LongDistanceSteamPipeCalculator(CalculatorBase):
    """长输蒸汽管道温降计算器"""

    # 计算类型类属性
    calculation_type = "长输蒸汽管道温降计算"

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
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None

    def setup_ui(self):
        """设置长输蒸汽管道温降计算界面"""
        # 主布局：水平布局
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ===== 左侧输入区 =====
        scroll_area = QScrollArea()
        scroll_area.setStyleSheet(SCROLL_AREA_STYLE)
        scroll_area.setWidgetResizable(True)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)

        # 顶部说明文字
        desc_label = QLabel("计算长距离蒸汽管道的温度降、压力损失和热损失，基于能量平衡和动量平衡方程进行分段计算。")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 12px; padding: 5px;")
        scroll_layout.addWidget(desc_label)

        # --- 蒸汽参数组 ---
        steam_group = CalculatorBase.make_group_box("蒸汽参数")
        steam_layout = QGridLayout(steam_group)
        steam_layout.setVerticalSpacing(12)
        steam_layout.setHorizontalSpacing(10)
        steam_layout.setColumnStretch(0, 4)
        steam_layout.setColumnStretch(1, 8)
        steam_layout.setColumnStretch(2, 5)

        row = 0
        lbl = QLabel("蒸汽类型:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        self.steam_type = QComboBox()
        self.steam_type.setStyleSheet(COMBOBOX_STYLE)
        self.steam_type.addItems(["饱和蒸汽", "过热蒸汽"])
        hint = QLabel("")
        steam_layout.addWidget(lbl, row, 0)
        steam_layout.addWidget(self.steam_type, row, 1)
        steam_layout.addWidget(hint, row, 2)

        row = 1
        lbl = QLabel("流量:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        self.flow_rate_input = QLineEdit()
        self.flow_rate_input.setPlaceholderText("例如：10")
        self.flow_rate_input.setValidator(QDoubleValidator(0.1, 1000, 2))
        self.flow_rate_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.flow_rate_unit = QComboBox()
        self.flow_rate_unit.setStyleSheet(COMBOBOX_STYLE)
        self.flow_rate_unit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.flow_rate_unit.addItems(["t/h", "kg/s"])
        steam_layout.addWidget(lbl, row, 0)
        steam_layout.addWidget(self.flow_rate_input, row, 1)
        steam_layout.addWidget(self.flow_rate_unit, row, 2)

        row = 2
        lbl = QLabel("入口温度:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        self.inlet_temp_input = QLineEdit()
        self.inlet_temp_input.setPlaceholderText("例如：200")
        self.inlet_temp_input.setValidator(QDoubleValidator(100, 600, 1))
        self.inlet_temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hint = QLabel("单位：°C")
        steam_layout.addWidget(lbl, row, 0)
        steam_layout.addWidget(self.inlet_temp_input, row, 1)
        steam_layout.addWidget(hint, row, 2)

        row = 3
        lbl = QLabel("入口压力:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        self.inlet_pressure_input = QLineEdit()
        self.inlet_pressure_input.setPlaceholderText("例如：1.0")
        self.inlet_pressure_input.setValidator(QDoubleValidator(0.1, 10, 2))
        self.inlet_pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.pressure_unit = QComboBox()
        self.pressure_unit.setStyleSheet(COMBOBOX_STYLE)
        self.pressure_unit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.pressure_unit.addItems(["MPa", "bar"])
        steam_layout.addWidget(lbl, row, 0)
        steam_layout.addWidget(self.inlet_pressure_input, row, 1)
        steam_layout.addWidget(self.pressure_unit, row, 2)

        scroll_layout.addWidget(steam_group)

        # --- 管道参数组 ---
        pipe_group = CalculatorBase.make_group_box("管道参数")
        pipe_layout = QGridLayout(pipe_group)
        pipe_layout.setVerticalSpacing(12)
        pipe_layout.setHorizontalSpacing(10)
        pipe_layout.setColumnStretch(0, 4)
        pipe_layout.setColumnStretch(1, 8)
        pipe_layout.setColumnStretch(2, 5)

        row = 0
        lbl = QLabel("管道长度:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        self.pipe_length_input = QLineEdit()
        self.pipe_length_input.setPlaceholderText("例如：1000")
        self.pipe_length_input.setValidator(QDoubleValidator(10, 50000, 0))
        self.pipe_length_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hint = QLabel("单位：m")
        pipe_layout.addWidget(lbl, row, 0)
        pipe_layout.addWidget(self.pipe_length_input, row, 1)
        pipe_layout.addWidget(hint, row, 2)

        row = 1
        lbl = QLabel("管道内径:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        self.pipe_diameter_input = QLineEdit()
        self.pipe_diameter_input.setPlaceholderText("例如：200")
        self.pipe_diameter_input.setValidator(QDoubleValidator(10, 2000, 1))
        self.pipe_diameter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hint = QLabel("单位：mm")
        pipe_layout.addWidget(lbl, row, 0)
        pipe_layout.addWidget(self.pipe_diameter_input, row, 1)
        pipe_layout.addWidget(hint, row, 2)

        row = 2
        lbl = QLabel("管道材料:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        self.pipe_material = QComboBox()
        self.pipe_material.setStyleSheet(COMBOBOX_STYLE)
        self.pipe_material.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.pipe_material.addItems(["碳钢", "不锈钢", "铜"])
        hint = QLabel("")
        pipe_layout.addWidget(lbl, row, 0)
        pipe_layout.addWidget(self.pipe_material, row, 1)
        pipe_layout.addWidget(hint, row, 2)

        row = 3
        lbl = QLabel("粗糙度:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        self.roughness_input = QLineEdit()
        self.roughness_input.setText("0.2")
        self.roughness_input.setValidator(QDoubleValidator(0.01, 5, 3))
        self.roughness_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hint = QLabel("单位：mm")
        pipe_layout.addWidget(lbl, row, 0)
        pipe_layout.addWidget(self.roughness_input, row, 1)
        pipe_layout.addWidget(hint, row, 2)

        scroll_layout.addWidget(pipe_group)

        # --- 保温参数组 ---
        insulation_group = CalculatorBase.make_group_box("保温参数")
        insulation_layout = QGridLayout(insulation_group)
        insulation_layout.setVerticalSpacing(12)
        insulation_layout.setHorizontalSpacing(10)
        insulation_layout.setColumnStretch(0, 4)
        insulation_layout.setColumnStretch(1, 8)
        insulation_layout.setColumnStretch(2, 5)

        row = 0
        lbl = QLabel("保温厚度:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        self.insulation_thickness_input = QLineEdit()
        self.insulation_thickness_input.setPlaceholderText("例如：50")
        self.insulation_thickness_input.setValidator(QDoubleValidator(0, 500, 1))
        self.insulation_thickness_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hint = QLabel("单位：mm")
        insulation_layout.addWidget(lbl, row, 0)
        insulation_layout.addWidget(self.insulation_thickness_input, row, 1)
        insulation_layout.addWidget(hint, row, 2)

        row = 1
        lbl = QLabel("保温材料:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        self.insulation_material = QComboBox()
        self.insulation_material.setStyleSheet(COMBOBOX_STYLE)
        self.insulation_material.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.insulation_material.addItems(["岩棉", "玻璃棉", "硅酸铝", "聚氨酯"])
        hint = QLabel("")
        insulation_layout.addWidget(lbl, row, 0)
        insulation_layout.addWidget(self.insulation_material, row, 1)
        insulation_layout.addWidget(hint, row, 2)

        row = 2
        lbl = QLabel("导热系数:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        self.insulation_conductivity_input = QLineEdit()
        self.insulation_conductivity_input.setText("0.04")
        self.insulation_conductivity_input.setValidator(QDoubleValidator(0.01, 1, 3))
        self.insulation_conductivity_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hint = QLabel("单位：W/(m·K)")
        insulation_layout.addWidget(lbl, row, 0)
        insulation_layout.addWidget(self.insulation_conductivity_input, row, 1)
        insulation_layout.addWidget(hint, row, 2)

        row = 3
        lbl = QLabel("环境温度:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        self.ambient_temp_input = QLineEdit()
        self.ambient_temp_input.setText("20")
        self.ambient_temp_input.setValidator(QDoubleValidator(-50, 50, 1))
        self.ambient_temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hint = QLabel("单位：°C")
        insulation_layout.addWidget(lbl, row, 0)
        insulation_layout.addWidget(self.ambient_temp_input, row, 1)
        insulation_layout.addWidget(hint, row, 2)

        scroll_layout.addWidget(insulation_group)

        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)

        # ===== 右侧结果区 =====
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        self.result_group = CalculatorBase.make_group_box("计算结果")
        result_inner = QVBoxLayout(self.result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: 13px;
            } """)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        result_inner.addWidget(self.result_text)
        right_layout.addWidget(self.result_group)

        # 底部按钮行：清空 | DOCX | PDF
        bottom_layout = QHBoxLayout()
        for label, style, slot in [
            ("清空", CLEAR_BTN_STYLE, self.clear_inputs),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(slot)
            bottom_layout.addWidget(btn)
        right_layout.addLayout(bottom_layout)

        # 计算按钮
        self.calc_btn = self.make_calc_button("计 算")
        self.calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(self.calc_btn)

        # 按比例添加到主布局
        main_layout.addWidget(scroll_area, 2)
        main_layout.addWidget(right_widget, 1)

    def clear_inputs(self):
        """清空所有输入"""
        self.flow_rate_input.clear()
        self.inlet_temp_input.clear()
        self.inlet_pressure_input.clear()
        self.pipe_length_input.clear()
        self.pipe_diameter_input.clear()
        self.roughness_input.setText("0.2")
        self.insulation_thickness_input.clear()
        self.insulation_conductivity_input.setText("0.04")
        self.ambient_temp_input.setText("20")
        self.result_text.clear()

    def calculate(self):
        """执行长输蒸汽管道温降计算"""
        try:
            # 获取输入值
            steam_type = self.steam_type.currentText()

            flow_rate = float(self.flow_rate_input.text())
            flow_unit = self.flow_rate_unit.currentText()
            if flow_unit == "t/h":
                mass_flow = flow_rate * 1000 / 3600  # 转换为kg/s
            else:  # kg/s
                mass_flow = flow_rate

            inlet_temp = float(self.inlet_temp_input.text())
            inlet_pressure = float(self.inlet_pressure_input.text())
            pressure_unit = self.pressure_unit.currentText()
            if pressure_unit == "bar":
                inlet_pressure_mpa = inlet_pressure / 10
            else:  # MPa
                inlet_pressure_mpa = inlet_pressure

            pipe_length = float(self.pipe_length_input.text())
            pipe_diameter = float(self.pipe_diameter_input.text()) / 1000  # 转换为m
            roughness = float(self.roughness_input.text()) / 1000  # 转换为m

            insulation_thickness = float(self.insulation_thickness_input.text()) / 1000  # 转换为m
            insulation_conductivity = float(self.insulation_conductivity_input.text())
            ambient_temp = float(self.ambient_temp_input.text())

            # 执行计算
            results = self.calculate_steam_pipe_loss(
                steam_type, mass_flow, inlet_temp, inlet_pressure_mpa,
                pipe_length, pipe_diameter, roughness,
                insulation_thickness, insulation_conductivity, ambient_temp
            )

            # 显示结果
            self.display_results(results)

        except ValueError:
            self.result_text.setPlainText("输入参数格式错误，请检查输入值")
        except Exception as e:
            self.result_text.setPlainText(f"计算错误: {str(e)}")

    def _get_history_data(self):
        """提供历史记录数据"""
        steam_type = self.steam_type.currentText()
        flow_rate = float(self.flow_rate_input.text() or 0)
        flow_unit = self.flow_rate_unit.currentText()
        if flow_unit == "t/h":
            mass_flow = flow_rate * 1000 / 3600
        else:
            mass_flow = flow_rate
        inlet_temp = float(self.inlet_temp_input.text() or 0)
        inlet_pressure = float(self.inlet_pressure_input.text() or 0)
        pressure_unit = self.pressure_unit.currentText()
        inlet_pressure_mpa = inlet_pressure / 10 if pressure_unit == "bar" else inlet_pressure
        pipe_length = float(self.pipe_length_input.text() or 0)
        pipe_diameter = float(self.pipe_diameter_input.text() or 0)
        roughness = float(self.roughness_input.text() or 0)
        insulation_thickness = float(self.insulation_thickness_input.text() or 0)
        insulation_conductivity = float(self.insulation_conductivity_input.text() or 0)
        ambient_temp = float(self.ambient_temp_input.text() or 0)

        inputs = {
            "蒸汽类型": steam_type,
            "流量": flow_rate,
            "流量单位": flow_unit,
            "入口温度_C": inlet_temp,
            "入口压力": inlet_pressure,
            "压力单位": pressure_unit,
            "管道长度_m": pipe_length,
            "管道直径_mm": pipe_diameter,
            "粗糙度_mm": roughness,
            "保温厚度_mm": insulation_thickness,
            "保温导热系数_W_mK": insulation_conductivity,
            "环境温度_C": ambient_temp
        }

        outputs = {}
        try:
            results = self.calculate_steam_pipe_loss(
                steam_type, mass_flow, inlet_temp, inlet_pressure_mpa,
                pipe_length, pipe_diameter / 1000, roughness / 1000,
                insulation_thickness / 1000, insulation_conductivity, ambient_temp
            )
            outputs = {
                "出口温度_C": round(results.get('outlet_temp', 0), 1),
                "出口压力_MPa": round(results.get('outlet_pressure', 0), 3),
                "温降_C": round(results.get('temp_drop', 0), 1),
                "压降_MPa": round(results.get('pressure_drop', 0), 3),
                "总热损失_kW": round(results.get('total_heat_loss', 0), 1)
            }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

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
            if not result_text or "计算结果" not in result_text:
                return None

            project_info = self.get_project_info()
            report = f"""══════════════════════════════════════════
          长输蒸汽管道温降计算计算书
══════════════════════════════════════════

【输入参数】
  蒸汽类型：{self.steam_type.currentText()}
  蒸汽流量：{self.flow_rate_input.text()} {self.flow_rate_unit.currentText()}
  入口温度：{self.inlet_temp_input.text()} °C
  入口压力：{self.inlet_pressure_input.text()} {self.pressure_unit.currentText()}
  管道长度：{self.pipe_length_input.text()} m
  管道内径：{self.pipe_diameter_input.text()} mm
  管道材料：{self.pipe_material.currentText()}
  粗糙度：{self.roughness_input.text()} mm
  保温厚度：{self.insulation_thickness_input.text()} mm
  保温材料：{self.insulation_material.currentText()}
  导热系数：{self.insulation_conductivity_input.text()} W/(m·K)
  环境温度：{self.ambient_temp_input.text()} °C

【计算结果】
{result_text}

══════════════════════════════════════════
 工程信息
══════════════════════════════════════════

  公司名称: {project_info.get('company_name', '')}
  工程编号: {project_info.get('project_number', '')}
  工程名称: {project_info.get('project_name', '')}
  子项名称: {project_info.get('subproject_name', '')}
  计算日期: {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}

══════════════════════════════════════════
备注说明
══════════════════════════════════════════

  1. 本计算书基于能量平衡和动量平衡方程分段计算
  2. 蒸汽物性采用 IAPWS-IF97 工业标准
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
        ReportExporter.export_docx(self, "长输蒸汽管道温降")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "长输蒸汽管道温降")
    def calculate_steam_pipe_loss(self, steam_type, mass_flow, inlet_temp, inlet_pressure,
                                 pipe_length, pipe_diameter, roughness,
                                 insulation_thickness, insulation_conductivity, ambient_temp):
        """计算蒸汽管道温降和压降"""
        # 蒸汽物性参数 (IAPWS-IF97 工业标准)
        def get_steam_properties(temp_c, pressure_mpa):
            try:
                props = iapws_steam(pressure_mpa, temp_c)
                density = props['rho']  # kg/m³
                specific_heat = props['cp']  # kJ/(kg·K)
                # 动力粘度 [Pa·s]
                viscosity = iapws_mu(pressure_mpa, temp_c)
                # 导热系数 [W/(m·K)]
                thermal_cond = iapws_k(pressure_mpa, temp_c)
                return density, viscosity, specific_heat, thermal_cond
            except Exception:
                # 降级处理
                density = pressure_mpa * 100 / (0.4615 * (temp_c + C_TO_K))
                return density, 1.2e-5, 2.0, 0.03

        # 初始参数
        current_temp = inlet_temp
        current_pressure = inlet_pressure

        # 分段计算 (将管道分成若干段)
        num_segments = 10
        segment_length = pipe_length / num_segments

        total_heat_loss = 0

        for i in range(num_segments):
            # 获取当前段的蒸汽物性
            density, viscosity, specific_heat, steam_conductivity = get_steam_properties(
                current_temp, current_pressure
            )

            # 计算流速
            cross_area = math.pi * (pipe_diameter / 2) ** 2
            velocity = mass_flow / (density * cross_area)

            # 计算雷诺数
            reynolds = density * velocity * pipe_diameter / viscosity

            # 计算摩擦系数 (Churchill公式)
            f = self.calculate_friction_factor(reynolds, pipe_diameter, roughness)

            # 计算压力降 (Darcy-Weisbach公式)
            pressure_drop_segment = f * (segment_length / pipe_diameter) * (density * velocity ** 2) / 2
            pressure_drop_mpa = pressure_drop_segment / 1e6

            # 更新压力
            current_pressure -= pressure_drop_mpa

            # 计算热损失
            if insulation_thickness > 0:
                # 有保温层
                inner_radius = pipe_diameter / 2
                outer_radius = inner_radius + insulation_thickness

                # 热阻计算
                r_pipe = math.log((inner_radius + 0.001) / inner_radius) / (2 * math.pi * 50 * segment_length)  # 管道热阻
                r_insulation = math.log(outer_radius / inner_radius) / (2 * math.pi * insulation_conductivity * segment_length)
                r_total = r_pipe + r_insulation

                heat_loss_segment = (current_temp - ambient_temp) / r_total  # W
            else:
                # 无保温层
                heat_loss_segment = 2 * math.pi * (pipe_diameter / 2) * segment_length * 10 * (current_temp - ambient_temp)  # 估算

            total_heat_loss += heat_loss_segment

            # 计算温度降
            temp_drop_segment = heat_loss_segment / (mass_flow * specific_heat * 1000)  # kJ/s to °C
            current_temp -= temp_drop_segment

        # 最终结果
        outlet_temp = current_temp
        outlet_pressure = current_pressure
        temp_drop = inlet_temp - outlet_temp
        pressure_drop = inlet_pressure - outlet_pressure

        # 计算最终段的流速和雷诺数
        density_out, viscosity_out, _, _ = get_steam_properties(outlet_temp, outlet_pressure)
        velocity_out = mass_flow / (density_out * cross_area)
        reynolds_out = density_out * velocity_out * pipe_diameter / viscosity_out

        # 判断流动状态
        if reynolds_out < 2300:
            flow_regime = "层流"
        elif reynolds_out < 4000:
            flow_regime = "过渡流"
        else:
            flow_regime = "湍流"

        return {
            'outlet_temp': outlet_temp,
            'outlet_pressure': outlet_pressure,
            'temp_drop': temp_drop,
            'pressure_drop': pressure_drop,
            'heat_loss': total_heat_loss / 1000,  # 转换为kW
            'velocity': velocity_out,
            'reynolds': reynolds_out,
            'flow_regime': flow_regime
        }

    def calculate_friction_factor(self, reynolds, diameter, roughness):
        """计算摩擦系数"""
        if reynolds < 2300:
            # 层流
            return 64 / reynolds
        else:
            # 湍流 (Colebrook-White方程简化)
            relative_roughness = roughness / diameter
            # 使用Swamee-Jain近似公式
            f = 0.25 / (math.log10(relative_roughness / 3.7 + 5.74 / reynolds ** 0.9)) ** 2
            return f

    def display_results(self, results):
        """显示计算结果到右侧结果区"""
        text = ""
        text += "【计算结果】\n\n"
        text += f"  出口温度：{results['outlet_temp']:.1f} °C\n\n"
        text += f"  出口压力：{results['outlet_pressure']:.3f} MPa\n\n"
        text += f"  温度降：{results['temp_drop']:.1f} °C\n\n"
        text += f"  压力降：{results['pressure_drop']:.3f} MPa\n\n"
        text += f"  总热损失：{results['heat_loss']:.1f} kW\n\n"
        text += f"  蒸汽流速：{results['velocity']:.1f} m/s\n\n"
        text += f"  雷诺数：{results['reynolds']:.0f}\n\n"
        text += f"  流动状态：{results['flow_regime']}\n"
        self.result_text.setPlainText(text)

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    calculator = LongDistanceSteamPipeCalculator()
    calculator.resize(1200, 800)
    calculator.show()

    sys.exit(app.exec())
