from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QLabel, QLineEdit, QPushButton, QComboBox,
                              QTextEdit, QGridLayout, QScrollArea, QFileDialog, QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math
import os
import importlib.util

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

# 统一 QGroupBox 样式
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

# 统一滚动条样式
SCROLLBAR_STYLE = """
    QScrollBar:vertical {
        border: none;
        background: #e8e8e8;
        width: 8px;
        margin: 0;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background: #c0c0c0;
        min-height: 30px;
        border-radius: 4px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
    QScrollBar:horizontal {
        border: none;
        background: #e8e8e8;
        height: 8px;
        margin: 0;
        border-radius: 4px;
    }
    QScrollBar::handle:horizontal {
        background: #c0c0c0;
        min-width: 30px;
        border-radius: 4px;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
    }
"""

# 计算按钮样式
CALC_BUTTON_STYLE = """
    QPushButton {
        background-color: #3498db;
        color: white;
        border: none;
        border-radius: 8px;
        min-height: 50px;
        font-size: 14px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #2980b9;
    }
"""

# 清空按钮样式
CLEAR_BUTTON_STYLE = """
    QPushButton {
        background-color: #95a5a6;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #7f8c8d;
    }
"""

# 下载TXT按钮样式
TXT_BUTTON_STYLE = """
    QPushButton {
        background-color: #27ae60;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px;
    }
    QPushButton:hover {
        background-color: #219653;
    }
"""

# 下载PDF按钮样式
PDF_BUTTON_STYLE = """
    QPushButton {
        background-color: #e74c3c;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px;
    }
    QPushButton:hover {
        background-color: #c0392b;
    }
"""
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


class LongDistanceSteamPipeCalculator(QWidget):
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
        scroll_area.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            + SCROLLBAR_STYLE
        )
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumWidth(900)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)

        # 顶部说明文字
        desc_label = QLabel("计算长距离蒸汽管道的温度降、压力损失和热损失，基于能量平衡和动量平衡方程进行分段计算。")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: inherit; font-size: 12px; padding: 5px;")
        scroll_layout.addWidget(desc_label)

        # --- 蒸汽参数组 ---
        steam_group = QGroupBox("蒸汽参数")
        steam_group.setStyleSheet(GROUP_STYLE)
        steam_layout = QGridLayout(steam_group)
        steam_layout.setVerticalSpacing(12)
        steam_layout.setHorizontalSpacing(10)
        steam_layout.setColumnStretch(0, 4)
        steam_layout.setColumnStretch(1, 8)
        steam_layout.setColumnStretch(2, 5)

        row = 0
        lbl = QLabel("蒸汽类型:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
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
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
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
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
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
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
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
        pipe_group = QGroupBox("管道参数")
        pipe_group.setStyleSheet(GROUP_STYLE)
        pipe_layout = QGridLayout(pipe_group)
        pipe_layout.setVerticalSpacing(12)
        pipe_layout.setHorizontalSpacing(10)
        pipe_layout.setColumnStretch(0, 4)
        pipe_layout.setColumnStretch(1, 8)
        pipe_layout.setColumnStretch(2, 5)

        row = 0
        lbl = QLabel("管道长度:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
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
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
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
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
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
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
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
        insulation_group = QGroupBox("保温参数")
        insulation_group.setStyleSheet(GROUP_STYLE)
        insulation_layout = QGridLayout(insulation_group)
        insulation_layout.setVerticalSpacing(12)
        insulation_layout.setHorizontalSpacing(10)
        insulation_layout.setColumnStretch(0, 4)
        insulation_layout.setColumnStretch(1, 8)
        insulation_layout.setColumnStretch(2, 5)

        row = 0
        lbl = QLabel("保温厚度:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
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
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
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
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
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
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
        self.ambient_temp_input = QLineEdit()
        self.ambient_temp_input.setText("20")
        self.ambient_temp_input.setValidator(QDoubleValidator(-50, 50, 1))
        self.ambient_temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hint = QLabel("单位：°C")
        insulation_layout.addWidget(lbl, row, 0)
        insulation_layout.addWidget(self.ambient_temp_input, row, 1)
        insulation_layout.addWidget(hint, row, 2)

        scroll_layout.addWidget(insulation_group)

        # 计算按钮
        self.calc_btn = QPushButton("计 算")
        self.calc_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.calc_btn.setMinimumHeight(50)
        self.calc_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                min-height: 50px; padding: 0px;
            }
            QPushButton:hover {
                background-color: #219955;
            }
        """)
        self.calc_btn.clicked.connect(self.calculate)
        scroll_layout.addWidget(self.calc_btn)

        # 底部按钮行：清空 → Stretch → 下载TXT → 下载PDF
        bottom_btn_layout = QHBoxLayout()

        self.clear_btn = QPushButton("清 空")
        self.clear_btn.setStyleSheet(CLEAR_BUTTON_STYLE)
        self.clear_btn.clicked.connect(self.clear_inputs)

        self.download_txt_btn = QPushButton("下载计算书(TXT)")
        self.download_txt_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_txt_btn.setStyleSheet(TXT_BUTTON_STYLE)
        self.download_txt_btn.clicked.connect(self.download_txt_report)

        self.download_pdf_btn = QPushButton("下载计算书(PDF)")
        self.download_pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_pdf_btn.setStyleSheet(PDF_BUTTON_STYLE)
        self.download_pdf_btn.clicked.connect(self.generate_pdf_report)

        bottom_btn_layout.addWidget(self.clear_btn)
        bottom_btn_layout.addStretch()
        bottom_btn_layout.addWidget(self.download_txt_btn)
        bottom_btn_layout.addWidget(self.download_pdf_btn)

        scroll_layout.addLayout(bottom_btn_layout)
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)

        # ===== 右侧结果区 =====
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        self.result_group = QGroupBox("计算结果")
        self.result_group.setStyleSheet(GROUP_STYLE)
        result_inner = QVBoxLayout(self.result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet(
            "QTextEdit {"
            "  /* bg via theme */"
            "  border: 1px solid #ecf0f1;"
            "  border-radius: 6px;"
            "  padding: 8px;"
            "}"
        )
        result_inner.addWidget(self.result_text)
        right_layout.addWidget(self.result_group)

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
        """获取项目信息"""
        return {
            "calculation_type": self.calculation_type,
            "title": "长输蒸汽管道温降计算"
        }

    def generate_report(self):
        """生成报告文本"""
        try:
            steam_type = self.steam_type.currentText()
            flow_rate = float(self.flow_rate_input.text())
            flow_unit = self.flow_rate_unit.currentText()

            inlet_temp = float(self.inlet_temp_input.text())
            inlet_pressure = float(self.inlet_pressure_input.text())
            pressure_unit = self.pressure_unit.currentText()

            pipe_length = float(self.pipe_length_input.text())
            pipe_diameter = float(self.pipe_diameter_input.text())
            pipe_mat = self.pipe_material.currentText()
            roughness = float(self.roughness_input.text())

            insulation_thickness = float(self.insulation_thickness_input.text())
            insulation_mat = self.insulation_material.currentText()
            insulation_conductivity = float(self.insulation_conductivity_input.text())
            ambient_temp = float(self.ambient_temp_input.text())

            # 执行计算获取结果
            if flow_unit == "t/h":
                mass_flow = flow_rate * 1000 / 3600
            else:
                mass_flow = flow_rate
            inlet_pressure_mpa = inlet_pressure / 10 if pressure_unit == "bar" else inlet_pressure
            results = self.calculate_steam_pipe_loss(
                steam_type, mass_flow, inlet_temp, inlet_pressure_mpa,
                pipe_length, pipe_diameter / 1000, roughness / 1000,
                insulation_thickness / 1000, insulation_conductivity, ambient_temp
            )

            report = "=" * 60 + "\n"
            report += "          长输蒸汽管道温降计算报告\n"
            report += "=" * 60 + "\n\n"

            report += "【输入参数】\n"
            report += f"  蒸汽类型：{steam_type}\n"
            report += f"  蒸汽流量：{flow_rate} {flow_unit}\n"
            report += f"  入口温度：{inlet_temp} °C\n"
            report += f"  入口压力：{inlet_pressure} {pressure_unit}\n"
            report += f"  管道长度：{pipe_length} m\n"
            report += f"  管道内径：{pipe_diameter} mm\n"
            report += f"  管道材料：{pipe_mat}\n"
            report += f"  粗糙度：{roughness} mm\n"
            report += f"  保温厚度：{insulation_thickness} mm\n"
            report += f"  保温材料：{insulation_mat}\n"
            report += f"  导热系数：{insulation_conductivity} W/(m·K)\n"
            report += f"  环境温度：{ambient_temp} °C\n\n"

            report += "【计算结果】\n"
            report += f"  出口温度：{results['outlet_temp']:.1f} °C\n"
            report += f"  出口压力：{results['outlet_pressure']:.3f} MPa\n"
            report += f"  温度降：{results['temp_drop']:.1f} °C\n"
            report += f"  压力降：{results['pressure_drop']:.3f} MPa\n"
            report += f"  总热损失：{results['heat_loss']:.1f} kW\n"
            report += f"  蒸汽流速：{results['velocity']:.1f} m/s\n"
            report += f"  雷诺数：{results['reynolds']:.0f}\n"
            report += f"  流动状态：{results['flow_regime']}\n\n"

            report += "=" * 60 + "\n"
            return report

        except Exception as e:
            return f"生成报告失败: {str(e)}"

    def download_txt_report(self):
        """下载TXT报告"""
        report = self.generate_report()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存TXT报告", "长输蒸汽管道温降计算报告.txt", "Text Files (*.txt)"
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report)

    def generate_pdf_report(self):
        """生成并下载PDF报告"""
        try:
            from fpdf import FPDF

            report = self.generate_report()
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存PDF报告", "长输蒸汽管道温降计算报告.pdf", "PDF Files (*.pdf)"
            )
            if not file_path:
                return

            pdf = FPDF()
            pdf.add_page()

            # 注册中文字体
            font_path = "C:/Windows/Fonts/msyh.ttc"
            pdf.add_font("msyh", "", font_path, uni=True)
            pdf.set_font("msyh", size=10)

            # 写入报告内容
            for line in report.split("\n"):
                pdf.cell(0, 8, line, new_x="LMARGIN", new_y="NEXT")

            pdf.output(file_path)

        except ImportError:
            print("错误: 未安装 fpdf 库，请运行 pip install fpdf2")
        except Exception as e:
            print(f"生成PDF报告失败: {str(e)}")

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
                density = pressure_mpa * 100 / (0.4615 * (temp_c + 273.15))
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
