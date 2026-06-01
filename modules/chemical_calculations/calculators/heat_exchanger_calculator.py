from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QFrame,
    QScrollArea, QDialog, QSpinBox, QButtonGroup, QGridLayout,
    QFileDialog, QDialogButtonBox, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math
import random
import re
import os
import sys
import importlib.util
from datetime import datetime
from pathlib import Path
from modules.combo_box_utils import ComboBoxWheelBlocker

# DOCX 报告导出
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.docx_utils import ReportExporter

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

class 换热器计算(QWidget):
    """换热器计算器（统一UI风格版）"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        
        # 使用传入的数据管理器或创建新的
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        
        # 流体比热容数据
        self.specific_heat_data = self.setup_specific_heat_data()
        
        # 传热系数数据
        self.heat_transfer_coeff_data = self.setup_heat_transfer_coeff_data()
        
        # 初始化输入控件字典
        self.input_widgets = {}
        
        self.setup_ui()
        self.setup_calculation_mode(0)  # 默认第一种模式

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self._wheel_blocker = ComboBoxWheelBlocker(self)
        for combo in self.findChildren(QComboBox):
            combo.installEventFilter(self._wheel_blocker)
    
    def init_data_manager(self):
        """初始化数据管理器 - 使用单例模式"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
            print("使用共享的数据管理器实例")
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None
    
    def setup_specific_heat_data(self):
        """设置流体比热容数据"""
        return {
            "水": 4.19,
            "乙醇": 2.4,
            "95%乙醇": 2.51,
            "90%乙醇": 2.72,
            "乙二醇": 2.35,
            "丙三醇": 2.46,
            "导热油": 2.9,
            "乙酸": 2.01,
            "10%乙酸": 4.02,
            "丙酮": 2.15,
            "蜂蜜": 1.42,
            "31%盐酸": 2.51,
            "10%盐酸": 3.14,
            "90%硫酸": 1.47,
            "60%硫酸": 2.18,
            "20%硫酸": 3.52,
            "蔗糖(60%糖浆)": 3.1,
            "蔗糖(40%糖浆)": 2.76,
            "汽油": 2.22,
            "空气": 1.0,
            "氨气": 2.26,
            "苯": 1.36,
            "丁烷": 1.91,
            "二氧化碳": 0.88,
            "一氧化碳": 1.07,
            "氯气": 0.5
        }
    
    def setup_heat_transfer_coeff_data(self):
        """设置传热系数数据"""
        data = []
        
        # 板式换热器数据
        data.append({"hot_fluid": "水", "cold_fluid": "水", "range": (4500.0, 6500.0), "exchanger": "板式换热器"})
        data.append({"hot_fluid": "油", "cold_fluid": "水", "range": (500.0, 700.0), "exchanger": "板式换热器"})
        
        # 螺旋板式换热器数据
        data.append({"hot_fluid": "水", "cold_fluid": "水", "range": (1750.0, 2210.0), "exchanger": "螺旋板式换热器"})
        data.append({"hot_fluid": "废液", "cold_fluid": "水", "range": (1400.0, 2100.0), "exchanger": "螺旋板式换热器"})
        data.append({"hot_fluid": "有机液", "cold_fluid": "有机液", "range": (350.0, 580.0), "exchanger": "螺旋板式换热器"})
        data.append({"hot_fluid": "中焦油", "cold_fluid": "中焦油", "range": (160.0, 200.0), "exchanger": "螺旋板式换热器"})
        data.append({"hot_fluid": "中焦油", "cold_fluid": "水", "range": (270.0, 310.0), "exchanger": "螺旋板式换热器"})
        data.append({"hot_fluid": "高粘度油", "cold_fluid": "水", "range": (230.0, 350.0), "exchanger": "螺旋板式换热器"})
        data.append({"hot_fluid": "油", "cold_fluid": "油", "range": (90.0, 140.0), "exchanger": "螺旋板式换热器"})
        data.append({"hot_fluid": "气体", "cold_fluid": "气体", "range": (30.0, 47.0), "exchanger": "螺旋板式换热器"})
        data.append({"hot_fluid": "变压器油", "cold_fluid": "水", "range": (327.0, 550.0), "exchanger": "螺旋板式换热器"})
        data.append({"hot_fluid": "电解液", "cold_fluid": "水", "range": (600.0, 1900.0), "exchanger": "螺旋板式换热器"})
        data.append({"hot_fluid": "浓碱液", "cold_fluid": "水", "range": (350.0, 650.0), "exchanger": "螺旋板式换热器"})
        
        # 管壳式换热器数据
        data.append({"hot_fluid": "水", "cold_fluid": "芳香族蒸气共沸物", "range": (250.0, 460.0), "exchanger": "管壳式换热器"})
        data.append({"hot_fluid": "空气", "cold_fluid": "水或盐水", "range": (57.0, 280.0), "exchanger": "管壳式换热器"})
        data.append({"hot_fluid": "水或盐水", "cold_fluid": "空气等（压缩）", "range": (110.0, 230.0), "exchanger": "管壳式换热器"})
        data.append({"hot_fluid": "水或盐水", "cold_fluid": "空气等（大气压）", "range": (30.0, 110.0), "exchanger": "管壳式换热器"})
        data.append({"hot_fluid": "道生油", "cold_fluid": "气体", "range": (20.0, 200.0), "exchanger": "管壳式换热器"})
        data.append({"hot_fluid": "水", "cold_fluid": "水", "range": (3000.0, 4500.0), "exchanger": "板翅式换热器"})
        data.append({"hot_fluid": "水", "cold_fluid": "油", "range": (400.0, 600.0), "exchanger": "板翅式换热器"})
        data.append({"hot_fluid": "油", "cold_fluid": "油", "range": (170.0, 350.0), "exchanger": "板翅式换热器"})
        data.append({"hot_fluid": "气体", "cold_fluid": "气体", "range": (70.0, 200.0), "exchanger": "板翅式换热器"})
        data.append({"hot_fluid": "空气", "cold_fluid": "水", "range": (80.0, 200.0), "exchanger": "板翅式换热器"})
        data.append({"hot_fluid": "硫酸", "cold_fluid": "水", "range": (870.0, 870.0), "exchanger": "石墨管壳式换热器-冷却器"})
        data.append({"hot_fluid": "氯气（除水）", "cold_fluid": "水", "range": (35.0, 170.0), "exchanger": "石墨管壳式换热器-冷却器"})
        data.append({"hot_fluid": "焙烧SO2气体", "cold_fluid": "水", "range": (350.0, 470.0), "exchanger": "石墨管壳式换热器-冷却器"})
        
        return data
    
    def setup_ui(self):
        """设置左右布局的换热器计算UI"""
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
        
        # 1. 首先添加说明文本
        description = QLabel(
            "换热器计算器 - 支持多种计算模式，包含流体比热容和传热系数选择，可用于热负荷、流量、温度等参数计算。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 2. 计算模式选择
        mode_group = QGroupBox("计算模式")
        mode_layout = QHBoxLayout(mode_group)
        
        # 模式选择下拉菜单
        mode_label = QLabel("选择计算模式:")
        mode_label.setStyleSheet("font-weight: bold;")
        mode_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet(COMBOBOX_STYLE)
        modes = [
            ("求饱和蒸汽流量", "根据冷流体参数计算所需饱和蒸汽流量"),
            ("求冷流体流量(蒸汽加热)", "已知蒸汽参数和冷流体温度变化，计算冷流体流量"),
            ("求冷流体出口温度t2(蒸汽加热)", "已知蒸汽和冷流体参数，计算冷流体出口温度"),
            ("求冷流体出口温度t2", "已知热流体和冷流体参数，计算冷流体出口温度"),
            ("求热流体出口温度t2", "已知热流体和冷流体参数，计算热流体出口温度"),
            ("求冷流体流量", "已知热流体和冷流体温度变化，计算冷流体流量"),
            ("求热流体流量", "已知热流体和冷流体参数，计算热流体流量")
        ]
        
        for mode_name, tooltip in modes:
            self.mode_combo.addItem(mode_name)
            self.mode_combo.setItemData(self.mode_combo.count()-1, tooltip, Qt.ToolTipRole)
        
        self.mode_combo.setCurrentIndex(0)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.mode_combo.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #666;
                border-radius: 4px;
                /* background-color via theme */
                min-width: 350px;
            }
            QComboBox:hover {
                border-color: #3498db;
            }
        """)
        
        mode_layout.addWidget(self.mode_combo)
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
        
        
        left_layout.addWidget(input_group)
        
        # 4. 计算按钮
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
        
        # 5. 下载按钮布局
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
        left_layout.addLayout(bottom_layout)
        
        # 6. 在底部添加拉伸因子
        left_layout.addStretch()
        
        # 右侧：结果显示区域 (占1/3宽度)
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        
        # 结果显示
        self.result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(self.result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
        
        # 将左右两部分添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)  # 左侧占2/3
        main_layout.addWidget(right_widget, 1)  # 右侧占1/3
    
    def on_mode_changed(self, index):
        """处理计算模式变化"""
        self.setup_calculation_mode(index)
    
    def setup_calculation_mode(self, mode_index):
        """设置计算模式的输入界面"""
        # 清除现有输入控件
        for widget in self.input_widgets.values():
            if widget and widget.parent():
                widget.setParent(None)
        self.input_widgets.clear()
        
        # 清除布局中的所有项目
        while self.input_layout.count():
            item = self.input_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # 标签样式
        label_style = """
            QLabel {
                font-weight: bold;
                padding-right: 10px;
            }
        """
        
        # 根据模式设置输入界面
        if mode_index == 0:  # 求饱和蒸汽流量
            self.setup_mode_0_inputs()
        elif mode_index == 1:  # 求冷流体流量（蒸汽加热）
            self.setup_mode_1_inputs()
        elif mode_index == 2:  # 求冷流体出口温度t2（蒸汽加热）
            self.setup_mode_2_inputs()
        elif mode_index == 3:  # 求冷流体出口温度t2
            self.setup_mode_3_inputs()
        elif mode_index == 4:  # 求热流体出口温度t2
            self.setup_mode_4_inputs()
        elif mode_index == 5:  # 求冷流体流量
            self.setup_mode_5_inputs()
        elif mode_index == 6:  # 求热流体流量
            self.setup_mode_6_inputs()
    
    def add_input_field(self, row, label_text, default_value="", placeholder="", validator=None):
        """添加输入字段"""
        # 标签 - 右对齐，第0列
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet("QLabel { font-weight: bold; padding-right: 10px; }")
        self.input_layout.addWidget(label, row, 0)

        # 输入框 - 第1列
        widget = QLineEdit()
        if default_value:
            widget.setText(str(default_value))
        if placeholder:
            widget.setPlaceholderText(placeholder)
        if validator:
            widget.setValidator(validator)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_layout.addWidget(widget, row, 1)

        # 提示标签 - 第2列
        hint_label = QLabel("直接输入数值")
        hint_label.setStyleSheet("font-style: italic;")
        self.input_layout.addWidget(hint_label, row, 2)
        
        # 存储控件引用
        key = label_text.replace(":", "").replace("(", "").replace(")", "").replace(" ", "_").replace("·", "").replace("/", "_").lower()
        self.input_widgets[key] = widget
        
        return widget
    
    def add_cp_input_field(self, row, label_text, default_value=""):
        """添加比热容输入字段 - 左侧输入框，右侧下拉菜单"""
        # 标签 - 右对齐，第0列
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet("QLabel { font-weight: bold; padding-right: 10px; }")
        self.input_layout.addWidget(label, row, 0)

        # 输入框 - 第1列
        lineedit = QLineEdit()
        if default_value:
            lineedit.setText(str(default_value))
        lineedit.setPlaceholderText("输入或选择后自动填充")
        lineedit.setValidator(QDoubleValidator(0.1, 100.0, 2))
        lineedit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_layout.addWidget(lineedit, row, 1)

        # 下拉菜单 - 第2列
        combobox = QComboBox()
        combobox.setStyleSheet(COMBOBOX_STYLE)
        combobox.addItem("- 请选择流体比热容 -")
        for fluid in self.specific_heat_data.keys():
            combobox.addItem(fluid)
        combobox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        combobox.currentTextChanged.connect(lambda text, le=lineedit: self.on_cp_selected(text, le))
        self.input_layout.addWidget(combobox, row, 2)
        
        # 存储控件引用
        key = label_text.replace(":", "").replace("(", "").replace(")", "").replace(" ", "_").replace("·", "").replace("/", "_").lower()
        self.input_widgets[key] = lineedit
        self.input_widgets[f"{key}_combo"] = combobox
        
        return lineedit, combobox
    
    def add_k_input_field(self, row, label_text):
        """添加传热系数输入字段"""
        # 标签 - 右对齐，第0列
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet("QLabel { font-weight: bold; padding-right: 10px; }")
        self.input_layout.addWidget(label, row, 0)
        
        # 输入框 - 第1列
        manual_input = QLineEdit()
        manual_input.setPlaceholderText("输入或选择后自动填充")
        manual_input.setValidator(QDoubleValidator(1, 10000, 1))
        manual_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_layout.addWidget(manual_input, row, 1)
        self.input_widgets["k_manual"] = manual_input
        
        # 下拉框 - 第2列
        combo = QComboBox()
        combo.setStyleSheet(COMBOBOX_STYLE)
        combo.addItem("- 请选择流体组合 -")
        
        # 添加传热系数选项
        for item in self.heat_transfer_coeff_data:
            hot_fluid = item["hot_fluid"]
            cold_fluid = item["cold_fluid"]
            min_val = item["range"][0]
            max_val = item["range"][1]
            exchanger = item["exchanger"]
            
            option_text = f"{hot_fluid} → {cold_fluid} | {min_val:.1f}~{max_val:.1f} W/K·m² | {exchanger}"
            combo.addItem(option_text)
        
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        combo.currentTextChanged.connect(self.on_heat_transfer_coeff_selected)
        self.input_layout.addWidget(combo, row, 2)
        self.input_widgets["k_combo"] = combo
        
        return combo
    
    def setup_mode_0_inputs(self):
        """模式0：求饱和蒸汽流量"""
        row = 0
        
        # 蒸汽压力(G) MPa
        self.add_input_field(row, "蒸汽压力(G) MPa:", "0.5", "例如：0.5", QDoubleValidator(0.01, 10.0, 2))
        row += 1
        
        # 冷流体W kg/h
        self.add_input_field(row, "冷流体W kg/h:", "10000", "例如：10000", QDoubleValidator(1, 1000000, 1))
        row += 1
        
        # 冷流体Cp kJ/kg.K
        self.add_cp_input_field(row, "冷流体Cp kJ/(kg·K):", "4.19")
        row += 1
        
        # 冷流体t1 ℃
        self.add_input_field(row, "冷流体t1 ℃:", "20", "例如：20", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 冷流体t2 ℃
        self.add_input_field(row, "冷流体t2 ℃:", "60", "例如：60", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 总传热系数K W/K.㎡
        self.add_k_input_field(row, "总传热系数K W/(K·m²):")
    
    def setup_mode_1_inputs(self):
        """模式1：求冷流体流量（蒸汽加热）"""
        row = 0
        
        # 蒸汽压力(G) MPa
        self.add_input_field(row, "蒸汽压力(G) MPa:", "0.5", "例如：0.5", QDoubleValidator(0.01, 10.0, 2))
        row += 1
        
        # 蒸汽流量 kg/h
        self.add_input_field(row, "蒸汽流量 kg/h:", "1000", "例如：1000", QDoubleValidator(1, 1000000, 1))
        row += 1
        
        # 冷流体Cp kJ/kg.K
        self.add_cp_input_field(row, "冷流体Cp kJ/(kg·K):", "4.19")
        row += 1
        
        # 冷流体t1 ℃
        self.add_input_field(row, "冷流体t1 ℃:", "20", "例如：20", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 冷流体t2 ℃
        self.add_input_field(row, "冷流体t2 ℃:", "60", "例如：60", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 总传热系数K W/K.㎡
        self.add_k_input_field(row, "总传热系数K W/(K·m²):")
    
    def setup_mode_2_inputs(self):
        """模式2：求冷流体出口温度t2（蒸汽加热）"""
        row = 0
        
        # 蒸汽压力(G) MPa
        self.add_input_field(row, "蒸汽压力(G) MPa:", "0.5", "例如：0.5", QDoubleValidator(0.01, 10.0, 2))
        row += 1
        
        # 蒸汽流量 kg/h
        self.add_input_field(row, "蒸汽流量 kg/h:", "1000", "例如：1000", QDoubleValidator(1, 1000000, 1))
        row += 1
        
        # 冷流体W kg/h
        self.add_input_field(row, "冷流体W kg/h:", "10000", "例如：10000", QDoubleValidator(1, 1000000, 1))
        row += 1
        
        # 冷流体Cp kJ/kg.K
        self.add_cp_input_field(row, "冷流体Cp kJ/(kg·K):", "4.19")
        row += 1
        
        # 冷流体t1 ℃
        self.add_input_field(row, "冷流体t1 ℃:", "20", "例如：20", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 总传热系数K W/K.㎡
        self.add_k_input_field(row, "总传热系数K W/(K·m²):")
    
    def setup_mode_3_inputs(self):
        """模式3：求冷流体出口温度t2"""
        row = 0
        
        # 热流体W kg/h
        self.add_input_field(row, "热流体W kg/h:", "5000", "例如：5000", QDoubleValidator(1, 1000000, 1))
        row += 1
        
        # 热流体Cp kJ/kg.K
        self.add_cp_input_field(row, "热流体Cp kJ/(kg·K):", "4.19")
        row += 1
        
        # 热流体t1 ℃
        self.add_input_field(row, "热流体t1 ℃:", "90", "例如：90", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 热流体t2 ℃
        self.add_input_field(row, "热流体t2 ℃:", "60", "例如：60", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 冷流体W kg/h
        self.add_input_field(row, "冷流体W kg/h:", "10000", "例如：10000", QDoubleValidator(1, 1000000, 1))
        row += 1
        
        # 冷流体Cp kJ/kg.K
        self.add_cp_input_field(row, "冷流体Cp kJ/(kg·K):", "4.19")
        row += 1
        
        # 冷流体t1 ℃
        self.add_input_field(row, "冷流体t1 ℃:", "20", "例如：20", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 总传热系数K W/K.㎡
        self.add_k_input_field(row, "总传热系数K W/(K·m²):")
    
    def setup_mode_4_inputs(self):
        """模式4：求热流体出口温度t2"""
        row = 0
        
        # 热流体W kg/h
        self.add_input_field(row, "热流体W kg/h:", "5000", "例如：5000", QDoubleValidator(1, 1000000, 1))
        row += 1
        
        # 热流体Cp kJ/kg.K
        self.add_cp_input_field(row, "热流体Cp kJ/(kg·K):", "4.19")
        row += 1
        
        # 热流体t1 ℃
        self.add_input_field(row, "热流体t1 ℃:", "90", "例如：90", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 冷流体W kg/h
        self.add_input_field(row, "冷流体W kg/h:", "10000", "例如：10000", QDoubleValidator(1, 1000000, 1))
        row += 1
        
        # 冷流体Cp kJ/kg.K
        self.add_cp_input_field(row, "冷流体Cp kJ/(kg·K):", "4.19")
        row += 1
        
        # 冷流体t1 ℃
        self.add_input_field(row, "冷流体t1 ℃:", "20", "例如：20", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 冷流体t2 ℃
        self.add_input_field(row, "冷流体t2 ℃:", "50", "例如：50", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 总传热系数K W/K.㎡
        self.add_k_input_field(row, "总传热系数K W/(K·m²):")
    
    def setup_mode_5_inputs(self):
        """模式5：求冷流体流量"""
        row = 0
        
        # 热流体W kg/h
        self.add_input_field(row, "热流体W kg/h:", "5000", "例如：5000", QDoubleValidator(1, 1000000, 1))
        row += 1
        
        # 热流体Cp kJ/kg.K
        self.add_cp_input_field(row, "热流体Cp kJ/(kg·K):", "4.19")
        row += 1
        
        # 热流体t1 ℃
        self.add_input_field(row, "热流体t1 ℃:", "90", "例如：90", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 热流体t2 ℃
        self.add_input_field(row, "热流体t2 ℃:", "60", "例如：60", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 冷流体Cp kJ/kg.K
        self.add_cp_input_field(row, "冷流体Cp kJ/(kg·K):", "4.19")
        row += 1
        
        # 冷流体t1 ℃
        self.add_input_field(row, "冷流体t1 ℃:", "20", "例如：20", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 冷流体t2 ℃
        self.add_input_field(row, "冷流体t2 ℃:", "50", "例如：50", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 总传热系数K W/K.㎡
        self.add_k_input_field(row, "总传热系数K W/(K·m²):")
    
    def setup_mode_6_inputs(self):
        """模式6：求热流体流量"""
        row = 0
        
        # 热流体Cp kJ/kg.K
        self.add_cp_input_field(row, "热流体Cp kJ/(kg·K):", "4.19")
        row += 1
        
        # 热流体t1 ℃
        self.add_input_field(row, "热流体t1 ℃:", "90", "例如：90", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 热流体t2 ℃
        self.add_input_field(row, "热流体t2 ℃:", "60", "例如：60", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 冷流体W kg/h
        self.add_input_field(row, "冷流体W kg/h:", "10000", "例如：10000", QDoubleValidator(1, 1000000, 1))
        row += 1
        
        # 冷流体Cp kJ/kg.K
        self.add_cp_input_field(row, "冷流体Cp kJ/(kg·K):", "4.19")
        row += 1
        
        # 冷流体t1 ℃
        self.add_input_field(row, "冷流体t1 ℃:", "20", "例如：20", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 冷流体t2 ℃
        self.add_input_field(row, "冷流体t2 ℃:", "50", "例如：50", QDoubleValidator(-273, 1000, 1))
        row += 1
        
        # 总传热系数K W/K.㎡
        self.add_k_input_field(row, "总传热系数K W/(K·m²):")
    
    def on_cp_selected(self, text, lineedit):
        """处理比热容选择"""
        if text.startswith("-") or not text.strip():
            return
        
        if text in self.specific_heat_data:
            cp_value = self.specific_heat_data[text]
            lineedit.setText(f"{cp_value:.2f}")
    
    def on_heat_transfer_coeff_selected(self, text):
        """处理传热系数选择"""
        if text.startswith("-") or not text.strip():
            return
        
        # 从选项文本中提取范围
        try:
            # 查找范围部分
            match = re.search(r'(\d+\.?\d*)~(\d+\.?\d*)', text)
            if match:
                min_val = float(match.group(1))
                max_val = float(match.group(2))
                
                # 生成范围内的随机数
                random_k = random.uniform(min_val, max_val)
                
                # 如果存在手动输入框，填充随机值
                if "k_manual" in self.input_widgets:
                    self.input_widgets["k_manual"].setText(f"{random_k:.1f}")
        except Exception as e:
            print(f"解析传热系数范围失败: {e}")
    
    def get_steam_latent_heat(self, pressure_mpa):
        """根据蒸汽表压获取汽化潜热 (kJ/kg)
        
        pressure_mpa: 表压 (MPa)，自动转为绝对压力
        使用 IAPWS-IF97 标准计算，若不可用则回退到查表法
        """
        P_abs = pressure_mpa + 0.101325  # 表压 → 绝对压力
        
        if _iapws_available and 0.001 <= P_abs <= 22.064:
            try:
                sat = _steam_iapws.saturation_properties(P_MPa=P_abs)
                return sat['h_fg']
            except Exception:
                pass
        
        # 回退：查表法
        return self._steam_latent_heat_fallback(P_abs)
    
    def get_steam_sat_temperature(self, pressure_mpa):
        """根据蒸汽表压获取饱和温度 (°C)"""
        P_abs = pressure_mpa + 0.101325
        if _iapws_available and 0.001 <= P_abs <= 22.064:
            try:
                sat = _steam_iapws.saturation_properties(P_MPa=P_abs)
                return sat['T_C']
            except Exception:
                pass
        return None
    
    @staticmethod
    def _steam_latent_heat_fallback(P_abs):
        """回退查表法：绝对压力(MPa) → 汽化潜热(kJ/kg)"""
        if P_abs <= 0.1:
            return 2257.0
        elif P_abs <= 0.2:
            return 2202.0
        elif P_abs <= 0.3:
            return 2164.0
        elif P_abs <= 0.4:
            return 2133.0
        elif P_abs <= 0.5:
            return 2108.0
        elif P_abs <= 0.6:
            return 2085.0
        elif P_abs <= 0.7:
            return 2065.0
        elif P_abs <= 0.8:
            return 2047.0
        elif P_abs <= 0.9:
            return 2030.0
        else:
            return 2015.0
    
    def get_input_value(self, key, default=0.0):
        """获取输入值"""
        if key in self.input_widgets:
            widget = self.input_widgets[key]
            if isinstance(widget, QLineEdit):
                text = widget.text().strip()
                if text:
                    try:
                        return float(text)
                    except:
                        return default
            elif isinstance(widget, QComboBox):
                text = widget.currentText()
                if text in self.specific_heat_data:
                    return self.specific_heat_data[text]
        return default
    
    def calculate(self):
        """执行计算"""
        try:
            # 获取当前选中的模式索引
            mode = self.mode_combo.currentIndex()
            
            if mode == 0:  # 求饱和蒸汽流量
                self.calculate_mode_0()
            elif mode == 1:  # 求冷流体流量（蒸汽加热）
                self.calculate_mode_1()
            elif mode == 2:  # 求冷流体出口温度t2（蒸汽加热）
                self.calculate_mode_2()
            elif mode == 3:  # 求冷流体出口温度t2
                self.calculate_mode_3()
            elif mode == 4:  # 求热流体出口温度t2
                self.calculate_mode_4()
            elif mode == 5:  # 求冷流体流量
                self.calculate_mode_5()
            elif mode == 6:  # 求热流体流量
                self.calculate_mode_6()
            else:
                QMessageBox.warning(self, "计算错误", "请选择计算模式")
                
        except ValueError as e:
            QMessageBox.critical(self, "输入错误", f"参数输入格式错误: {str(e)}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "参数不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")
    
    def calculate_mode_0(self):
        """模式0：求饱和蒸汽流量"""
        # 获取输入值
        steam_pressure = self.get_input_value("蒸汽压力g_mpa", 0.5)
        cold_flow = self.get_input_value("冷流体w_kg/h", 10000)
        cold_cp = self.get_input_value("冷流体cp_kj/(kg·k)", 4.19)
        cold_t1 = self.get_input_value("冷流体t1_℃", 20)
        cold_t2 = self.get_input_value("冷流体t2_℃", 60)
        
        # 验证输入
        if cold_t2 <= cold_t1:
            QMessageBox.warning(self, "输入错误", "冷流体出口温度必须大于进口温度")
            return
        
        # 获取蒸汽物性
        latent_heat = self.get_steam_latent_heat(steam_pressure)
        sat_temp = self.get_steam_sat_temperature(steam_pressure)
        
        # 验证冷流体出口温度不超过蒸汽饱和温度
        if sat_temp is not None and cold_t2 >= sat_temp:
            QMessageBox.warning(self, "输入错误", 
                f"冷流体出口温度({cold_t2:.1f}°C)不能高于蒸汽饱和温度({sat_temp:.1f}°C)")
            return
        
        # 计算冷流体吸热量 (kW)
        Q_cold = cold_flow * cold_cp * (cold_t2 - cold_t1) / 3600  # 转换为kW
        
        # 计算所需蒸汽流量 (kg/h)
        steam_flow = Q_cold * 3600 / latent_heat
        
        # 构建结果文本
        P_abs = steam_pressure + 0.101325
        method_note = "IAPWS-IF97 标准" if _iapws_available else "查表法(回退)"
        
        result = f"""
═══════════
 输入参数
═══════════

    计算模式: {self.mode_combo.currentText()}
    蒸汽压力: {steam_pressure:.2f} MPa（表压）
    蒸汽绝对压力: {P_abs:.3f} MPa
    冷流体流量: {cold_flow:.0f} kg/h
    冷流体比热容: {cold_cp:.2f} kJ/(kg·K)
    冷流体进口温度: {cold_t1:.1f} °C
    冷流体出口温度: {cold_t2:.1f} °C

══════════
计算结果
══════════

    蒸汽饱和温度: {sat_temp:.1f} °C
    蒸汽汽化潜热: {latent_heat:.1f} kJ/kg
    冷流体吸热量: {Q_cold:.1f} kW
    所需饱和蒸汽流量: {steam_flow:.1f} kg/h

══════════
计算说明
══════════

    计算公式:
    1. 冷流体吸热量: Q = W_cold × Cp_cold × (t2 - t1) / 3600 [kW]
    2. 蒸汽流量: W_steam = Q × 3600 / r [kg/h]
    其中: r - 蒸汽汽化潜热 (kJ/kg)

    蒸汽物性数据来源: {method_note}
    注意: 实际应用应考虑换热效率和安全系数"""
        
        self.result_text.setText(result)
    
    def calculate_mode_1(self):
        """模式1：求冷流体流量（蒸汽加热）"""
        # 获取输入值
        steam_pressure = self.get_input_value("蒸汽压力g_mpa", 0.5)
        steam_flow = self.get_input_value("蒸汽流量_kg/h", 1000)
        cold_cp = self.get_input_value("冷流体cp_kj/(kg·k)", 4.19)
        cold_t1 = self.get_input_value("冷流体t1_℃", 20)
        cold_t2 = self.get_input_value("冷流体t2_℃", 60)
        
        # 验证输入
        if cold_t2 <= cold_t1:
            QMessageBox.warning(self, "输入错误", "冷流体出口温度必须大于进口温度")
            return
        
        # 获取蒸汽物性
        latent_heat = self.get_steam_latent_heat(steam_pressure)
        sat_temp = self.get_steam_sat_temperature(steam_pressure)
        
        if sat_temp is not None and cold_t2 >= sat_temp:
            QMessageBox.warning(self, "输入错误", 
                f"冷流体出口温度({cold_t2:.1f}°C)不能高于蒸汽饱和温度({sat_temp:.1f}°C)")
            return
        
        # 计算蒸汽放热量 (kW)
        Q_steam = steam_flow * latent_heat / 3600  # 转换为kW
        
        # 计算冷流体流量 (kg/h)
        cold_flow = Q_steam * 3600 / (cold_cp * (cold_t2 - cold_t1))
        
        P_abs = steam_pressure + 0.101325
        method_note = "IAPWS-IF97 标准" if _iapws_available else "查表法(回退)"
        
        # 显示结果
        result = f"""
═══════════
 输入参数
═══════════

    计算模式: {self.mode_combo.currentText()}
    蒸汽压力: {steam_pressure:.2f} MPa（表压）
    蒸汽绝对压力: {P_abs:.3f} MPa
    蒸汽流量: {steam_flow:.0f} kg/h
    冷流体比热容: {cold_cp:.2f} kJ/(kg·K)
    冷流体进口温度: {cold_t1:.1f} °C
    冷流体出口温度: {cold_t2:.1f} °C

══════════
计算结果
══════════

    蒸汽饱和温度: {sat_temp:.1f} °C
    蒸汽汽化潜热: {latent_heat:.1f} kJ/kg
    蒸汽放热量: {Q_steam:.1f} kW
    冷流体流量: {cold_flow:.1f} kg/h

══════════
计算说明
══════════

    计算公式:
    1. 蒸汽放热量: Q = W_steam × r / 3600 [kW]
    2. 冷流体流量: W_cold = Q × 3600 / [Cp_cold × (t2 - t1)] [kg/h]
    其中: r - 蒸汽汽化潜热 (kJ/kg)

    蒸汽物性数据来源: {method_note}
    注意: 实际应用应考虑换热效率和安全系数"""
        
        self.result_text.setText(result)
    
    def calculate_mode_2(self):
        """模式2：求冷流体出口温度t2（蒸汽加热）"""
        # 获取输入值
        steam_pressure = self.get_input_value("蒸汽压力g_mpa", 0.5)
        steam_flow = self.get_input_value("蒸汽流量_kg/h", 1000)
        cold_flow = self.get_input_value("冷流体w_kg/h", 10000)
        cold_cp = self.get_input_value("冷流体cp_kj/(kg·k)", 4.19)
        cold_t1 = self.get_input_value("冷流体t1_℃", 20)
        
        # 获取蒸汽物性
        latent_heat = self.get_steam_latent_heat(steam_pressure)
        sat_temp = self.get_steam_sat_temperature(steam_pressure)
        
        # 计算蒸汽放热量 (kW)
        Q_steam = steam_flow * latent_heat / 3600  # 转换为kW
        
        # 计算冷流体出口温度 (°C)
        cold_t2 = cold_t1 + (Q_steam * 3600) / (cold_flow * cold_cp)
        
        # 校验出口温度不超过蒸汽饱和温度
        if sat_temp is not None and cold_t2 >= sat_temp:
            QMessageBox.warning(self, "温度警告", 
                f"计算出口温度{cold_t2:.1f}°C已达或超过蒸汽饱和温度{sat_temp:.1f}°C\n"
                f"请检查蒸汽流量是否过大或冷流体流量是否过小")
        
        P_abs = steam_pressure + 0.101325
        method_note = "IAPWS-IF97 标准" if _iapws_available else "查表法(回退)"
        
        # 显示结果
        result = f"""
═══════════
 输入参数
═══════════

    计算模式: {self.mode_combo.currentText()}
    蒸汽压力: {steam_pressure:.2f} MPa（表压）
    蒸汽绝对压力: {P_abs:.3f} MPa
    蒸汽流量: {steam_flow:.0f} kg/h
    冷流体流量: {cold_flow:.0f} kg/h
    冷流体比热容: {cold_cp:.2f} kJ/(kg·K)
    冷流体进口温度: {cold_t1:.1f} °C

══════════
计算结果
══════════

    蒸汽饱和温度: {sat_temp:.1f} °C
    蒸汽汽化潜热: {latent_heat:.1f} kJ/kg
    蒸汽放热量: {Q_steam:.1f} kW
    冷流体出口温度: {cold_t2:.1f} °C
    冷流体温升: {cold_t2 - cold_t1:.1f} °C

══════════
计算说明
══════════

    计算公式:
    1. 蒸汽放热量: Q = W_steam × r / 3600 [kW]
    2. 冷流体出口温度: t2 = t1 + (Q × 3600) / (W_cold × Cp_cold) [°C]
    其中: r - 蒸汽汽化潜热 (kJ/kg)

    蒸汽物性数据来源: {method_note}
    注意: 实际应用应考虑换热效率和安全系数"""
        
        self.result_text.setText(result)
    
    def calculate_mode_3(self):
        """模式3：求冷流体出口温度t2"""
        # 获取输入值
        hot_flow = self.get_input_value("热流体w_kg/h", 5000)
        hot_cp = self.get_input_value("热流体cp_kj/(kg·k)", 4.19)
        hot_t1 = self.get_input_value("热流体t1_℃", 90)
        hot_t2 = self.get_input_value("热流体t2_℃", 60)
        cold_flow = self.get_input_value("冷流体w_kg/h", 10000)
        cold_cp = self.get_input_value("冷流体cp_kj/(kg·k)", 4.19)
        cold_t1 = self.get_input_value("冷流体t1_℃", 20)
        
        # 验证输入
        if hot_t2 >= hot_t1:
            QMessageBox.warning(self, "输入错误", "热流体出口温度必须小于进口温度")
            return
        
        # 计算热流体放热量 (kW)
        Q_hot = hot_flow * hot_cp * (hot_t1 - hot_t2) / 3600  # 转换为kW
        
        # 计算冷流体出口温度 (°C)
        cold_t2 = cold_t1 + (Q_hot * 3600) / (cold_flow * cold_cp)
        
        # 计算对数平均温差
        delta_t1 = hot_t1 - cold_t2
        delta_t2 = hot_t2 - cold_t1
        if delta_t1 == delta_t2:
            lmtd = delta_t1
        else:
            lmtd = (delta_t1 - delta_t2) / math.log(delta_t1 / delta_t2)
        
        # 显示结果
        result = f"""
═══════════
 输入参数
═══════════

    计算模式: {self.mode_combo.currentText()}
    热流体流量: {hot_flow:.0f} kg/h
    热流体比热容: {hot_cp:.2f} kJ/(kg·K)
    热流体进口温度: {hot_t1:.1f} °C
    热流体出口温度: {hot_t2:.1f} °C
    冷流体流量: {cold_flow:.0f} kg/h
    冷流体比热容: {cold_cp:.2f} kJ/(kg·K)
    冷流体进口温度: {cold_t1:.1f} °C

══════════
计算结果
══════════

    热流体放热量: {Q_hot:.1f} kW
    冷流体出口温度: {cold_t2:.1f} °C
    冷流体温升: {cold_t2 - cold_t1:.1f} °C
    对数平均温差(LMTD): {lmtd:.1f} °C

══════════
计算说明
══════════

    计算公式:
    1. 热流体放热量: Q = W_hot × Cp_hot × (t1_hot - t2_hot) / 3600 [kW]
    2. 冷流体出口温度: t2_cold = t1_cold + (Q × 3600) / (W_cold × Cp_cold) [°C]
    3. 对数平均温差: LMTD = (ΔT1 - ΔT2) / ln(ΔT1/ΔT2)

    注意: 实际应用应考虑换热效率和安全系数"""
        
        self.result_text.setText(result)
    
    def calculate_mode_4(self):
        """模式4：求热流体出口温度t2"""
        # 获取输入值
        hot_flow = self.get_input_value("热流体w_kg/h", 5000)
        hot_cp = self.get_input_value("热流体cp_kj/(kg·k)", 4.19)
        hot_t1 = self.get_input_value("热流体t1_℃", 90)
        cold_flow = self.get_input_value("冷流体w_kg/h", 10000)
        cold_cp = self.get_input_value("冷流体cp_kj/(kg·k)", 4.19)
        cold_t1 = self.get_input_value("冷流体t1_℃", 20)
        cold_t2 = self.get_input_value("冷流体t2_℃", 50)
        
        # 验证输入
        if cold_t2 <= cold_t1:
            QMessageBox.warning(self, "输入错误", "冷流体出口温度必须大于进口温度")
            return
        
        # 计算冷流体吸热量 (kW)
        Q_cold = cold_flow * cold_cp * (cold_t2 - cold_t1) / 3600  # 转换为kW
        
        # 计算热流体出口温度 (°C)
        hot_t2 = hot_t1 - (Q_cold * 3600) / (hot_flow * hot_cp)
        
        # 计算对数平均温差
        delta_t1 = hot_t1 - cold_t2
        delta_t2 = hot_t2 - cold_t1
        if delta_t1 == delta_t2:
            lmtd = delta_t1
        else:
            lmtd = (delta_t1 - delta_t2) / math.log(delta_t1 / delta_t2)
        
        # 显示结果
        result = f"""
═══════════
 输入参数
═══════════

    计算模式: {self.mode_combo.currentText()}
    热流体流量: {hot_flow:.0f} kg/h
    热流体比热容: {hot_cp:.2f} kJ/(kg·K)
    热流体进口温度: {hot_t1:.1f} °C
    冷流体流量: {cold_flow:.0f} kg/h
    冷流体比热容: {cold_cp:.2f} kJ/(kg·K)
    冷流体进口温度: {cold_t1:.1f} °C
    冷流体出口温度: {cold_t2:.1f} °C

══════════
计算结果
══════════

    冷流体吸热量: {Q_cold:.1f} kW
    热流体出口温度: {hot_t2:.1f} °C
    热流体温降: {hot_t1 - hot_t2:.1f} °C
    对数平均温差(LMTD): {lmtd:.1f} °C

══════════
计算说明
══════════

    计算公式:
    1. 冷流体吸热量: Q = W_cold × Cp_cold × (t2_cold - t1_cold) / 3600 [kW]
    2. 热流体出口温度: t2_hot = t1_hot - (Q × 3600) / (W_hot × Cp_hot) [°C]
    3. 对数平均温差: LMTD = (ΔT1 - ΔT2) / ln(ΔT1/ΔT2)

    注意: 实际应用应考虑换热效率和安全系数"""
        
        self.result_text.setText(result)
    
    def calculate_mode_5(self):
        """模式5：求冷流体流量"""
        # 获取输入值
        hot_flow = self.get_input_value("热流体w_kg/h", 5000)
        hot_cp = self.get_input_value("热流体cp_kj/(kg·k)", 4.19)
        hot_t1 = self.get_input_value("热流体t1_℃", 90)
        hot_t2 = self.get_input_value("热流体t2_℃", 60)
        cold_cp = self.get_input_value("冷流体cp_kj/(kg·k)", 4.19)
        cold_t1 = self.get_input_value("冷流体t1_℃", 20)
        cold_t2 = self.get_input_value("冷流体t2_℃", 50)
        
        # 验证输入
        if hot_t2 >= hot_t1:
            QMessageBox.warning(self, "输入错误", "热流体出口温度必须小于进口温度")
            return
        
        if cold_t2 <= cold_t1:
            QMessageBox.warning(self, "输入错误", "冷流体出口温度必须大于进口温度")
            return
        
        # 计算热流体放热量 (kW)
        Q_hot = hot_flow * hot_cp * (hot_t1 - hot_t2) / 3600  # 转换为kW
        
        # 计算冷流体流量 (kg/h)
        cold_flow = Q_hot * 3600 / (cold_cp * (cold_t2 - cold_t1))
        
        # 计算对数平均温差
        delta_t1 = hot_t1 - cold_t2
        delta_t2 = hot_t2 - cold_t1
        if delta_t1 == delta_t2:
            lmtd = delta_t1
        else:
            lmtd = (delta_t1 - delta_t2) / math.log(delta_t1 / delta_t2)
        
        # 显示结果
        result = f"""
═══════════
 输入参数
═══════════

    计算模式: {self.mode_combo.currentText()}
    热流体流量: {hot_flow:.0f} kg/h
    热流体比热容: {hot_cp:.2f} kJ/(kg·K)
    热流体进口温度: {hot_t1:.1f} °C
    热流体出口温度: {hot_t2:.1f} °C
    冷流体比热容: {cold_cp:.2f} kJ/(kg·K)
    冷流体进口温度: {cold_t1:.1f} °C
    冷流体出口温度: {cold_t2:.1f} °C

══════════
计算结果
══════════

    热流体放热量: {Q_hot:.1f} kW
    冷流体流量: {cold_flow:.1f} kg/h
    对数平均温差(LMTD): {lmtd:.1f} °C

══════════
计算说明
══════════

    计算公式:
    1. 热流体放热量: Q = W_hot × Cp_hot × (t1_hot - t2_hot) / 3600 [kW]
    2. 冷流体流量: W_cold = Q × 3600 / [Cp_cold × (t2_cold - t1_cold)] [kg/h]
    3. 对数平均温差: LMTD = (ΔT1 - ΔT2) / ln(ΔT1/ΔT2)

    注意: 实际应用应考虑换热效率和安全系数"""
        
        self.result_text.setText(result)
    
    def calculate_mode_6(self):
        """模式6：求热流体流量"""
        # 获取输入值
        hot_cp = self.get_input_value("热流体cp_kj/(kg·k)", 4.19)
        hot_t1 = self.get_input_value("热流体t1_℃", 90)
        hot_t2 = self.get_input_value("热流体t2_℃", 60)
        cold_flow = self.get_input_value("冷流体w_kg/h", 10000)
        cold_cp = self.get_input_value("冷流体cp_kj/(kg·k)", 4.19)
        cold_t1 = self.get_input_value("冷流体t1_℃", 20)
        cold_t2 = self.get_input_value("冷流体t2_℃", 50)
        
        # 验证输入
        if hot_t2 >= hot_t1:
            QMessageBox.warning(self, "输入错误", "热流体出口温度必须小于进口温度")
            return
        
        if cold_t2 <= cold_t1:
            QMessageBox.warning(self, "输入错误", "冷流体出口温度必须大于进口温度")
            return
        
        # 计算冷流体吸热量 (kW)
        Q_cold = cold_flow * cold_cp * (cold_t2 - cold_t1) / 3600  # 转换为kW
        
        # 计算热流体流量 (kg/h)
        hot_flow = Q_cold * 3600 / (hot_cp * (hot_t1 - hot_t2))
        
        # 计算对数平均温差
        delta_t1 = hot_t1 - cold_t2
        delta_t2 = hot_t2 - cold_t1
        if delta_t1 == delta_t2:
            lmtd = delta_t1
        else:
            lmtd = (delta_t1 - delta_t2) / math.log(delta_t1 / delta_t2)
        
        # 显示结果
        result = f"""
═══════════
 输入参数
═══════════

    计算模式: {self.mode_combo.currentText()}
    热流体比热容: {hot_cp:.2f} kJ/(kg·K)
    热流体进口温度: {hot_t1:.1f} °C
    热流体出口温度: {hot_t2:.1f} °C
    冷流体流量: {cold_flow:.0f} kg/h
    冷流体比热容: {cold_cp:.2f} kJ/(kg·K)
    冷流体进口温度: {cold_t1:.1f} °C
    冷流体出口温度: {cold_t2:.1f} °C

══════════
计算结果
══════════

    冷流体吸热量: {Q_cold:.1f} kW
    热流体流量: {hot_flow:.1f} kg/h
    对数平均温差(LMTD): {lmtd:.1f} °C

══════════
计算说明
══════════

    计算公式:
    1. 冷流体吸热量: Q = W_cold × Cp_cold × (t2_cold - t1_cold) / 3600 [kW]
    2. 热流体流量: W_hot = Q × 3600 / [Cp_hot × (t1_hot - t2_hot)] [kg/h]
    3. 对数平均温差: LMTD = (ΔT1 - ΔT2) / ln(ΔT1/ΔT2)

    注意: 实际应用应考虑换热效率和安全系数"""
        
        self.result_text.setText(result)
    
    def clear_inputs(self):
        """清空输入"""
        for widget in self.input_widgets.values():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
        
        self.result_text.clear()

    def _get_history_data(self):
        """提供历史记录数据"""
        mode = self.mode_combo.currentIndex()
        mode_name = self.mode_combo.currentText()

        inputs = {"计算模式": mode_name}

        # 根据模式收集不同的输入
        if mode == 0:
            inputs["蒸汽压力_MPa"] = self.get_input_value("蒸汽压力g_mpa", 0)
            inputs["冷流体流量_kg_h"] = self.get_input_value("冷流体w_kg/h", 0)
            inputs["冷流体cp"] = self.get_input_value("冷流体cp_kj/(kg·k)", 0)
            inputs["冷流体进口温度_C"] = self.get_input_value("冷流体t1_℃", 0)
            inputs["冷流体出口温度_C"] = self.get_input_value("冷流体t2_℃", 0)
        elif mode == 1:
            inputs["蒸汽压力_MPa"] = self.get_input_value("蒸汽压力g_mpa", 0)
            inputs["冷流体cp"] = self.get_input_value("冷流体cp_kj/(kg·k)", 0)
            inputs["冷流体进口温度_C"] = self.get_input_value("冷流体t1_℃", 0)
            inputs["冷流体出口温度_C"] = self.get_input_value("冷流体t2_℃", 0)
            inputs["换热面积_m2"] = self.get_input_value("换热面积m2", 0)
        elif mode == 2:
            inputs["蒸汽压力_MPa"] = self.get_input_value("蒸汽压力g_mpa", 0)
            inputs["冷流体流量_kg_h"] = self.get_input_value("冷流体w_kg/h", 0)
            inputs["冷流体cp"] = self.get_input_value("冷流体cp_kj/(kg·k)", 0)
            inputs["冷流体进口温度_C"] = self.get_input_value("冷流体t1_℃", 0)
            inputs["换热面积_m2"] = self.get_input_value("换热面积m2", 0)
        elif mode == 3:
            inputs["热流体流量_kg_h"] = self.get_input_value("热流体w_kg/h", 0)
            inputs["热流体cp"] = self.get_input_value("热流体cp_kj/(kg·k)", 0)
            inputs["热流体进口温度_C"] = self.get_input_value("热流体t1_℃", 0)
            inputs["热流体出口温度_C"] = self.get_input_value("热流体t2_℃", 0)
            inputs["冷流体cp"] = self.get_input_value("冷流体cp_kj/(kg·k)", 0)
            inputs["冷流体进口温度_C"] = self.get_input_value("冷流体t1_℃", 0)
            inputs["换热面积_m2"] = self.get_input_value("换热面积m2", 0)
        elif mode == 4:
            inputs["热流体流量_kg_h"] = self.get_input_value("热流体w_kg/h", 0)
            inputs["热流体cp"] = self.get_input_value("热流体cp_kj/(kg·k)", 0)
            inputs["热流体进口温度_C"] = self.get_input_value("热流体t1_℃", 0)
            inputs["冷流体流量_kg_h"] = self.get_input_value("冷流体w_kg/h", 0)
            inputs["冷流体cp"] = self.get_input_value("冷流体cp_kj/(kg·k)", 0)
            inputs["冷流体进口温度_C"] = self.get_input_value("冷流体t1_℃", 0)
            inputs["换热面积_m2"] = self.get_input_value("换热面积m2", 0)
        elif mode == 5:
            inputs["热流体流量_kg_h"] = self.get_input_value("热流体w_kg/h", 0)
            inputs["热流体cp"] = self.get_input_value("热流体cp_kj/(kg·k)", 0)
            inputs["热流体进口温度_C"] = self.get_input_value("热流体t1_℃", 0)
            inputs["热流体出口温度_C"] = self.get_input_value("热流体t2_℃", 0)
            inputs["冷流体cp"] = self.get_input_value("冷流体cp_kj/(kg·k)", 0)
            inputs["冷流体进口温度_C"] = self.get_input_value("冷流体t1_℃", 0)
            inputs["冷流体出口温度_C"] = self.get_input_value("冷流体t2_℃", 0)
        elif mode == 6:
            inputs["热流体cp"] = self.get_input_value("热流体cp_kj/(kg·k)", 0)
            inputs["热流体进口温度_C"] = self.get_input_value("热流体t1_℃", 0)
            inputs["热流体出口温度_C"] = self.get_input_value("热流体t2_℃", 0)
            inputs["冷流体流量_kg_h"] = self.get_input_value("冷流体w_kg/h", 0)
            inputs["冷流体cp"] = self.get_input_value("冷流体cp_kj/(kg·k)", 0)
            inputs["冷流体进口温度_C"] = self.get_input_value("冷流体t1_℃", 0)
            inputs["冷流体出口温度_C"] = self.get_input_value("冷流体t2_℃", 0)

        # 添加总传热系数
        k_combo_idx = self.input_widgets.get("k_combo").currentIndex() if "k_combo" in self.input_widgets else 0
        inputs["传热系数选择"] = k_combo_idx
        if k_combo_idx == 0:
            inputs["传热系数_W_m2K"] = self.get_input_value("k_manual", 0)

        outputs = {}
        result_text = self.result_text.toPlainText()
        if "计算结果" in result_text:
            try:
                import re
                q_match = re.search(r'换热量[：:]\s*([\d.]+)\s*kW', result_text)
                if q_match:
                    outputs["换热量_kW"] = float(q_match.group(1))
                lmtd_match = re.search(r'对数平均温差[（(]LMTD[）)][：:]\s*([\d.]+)\s*°C', result_text)
                if lmtd_match:
                    outputs["LMTD_C"] = float(lmtd_match.group(1))
            except Exception:
                pass

        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        """获取工程信息 - 使用共享的项目信息"""
        try:
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
                    company_label.setFixedWidth(80)
                    self.company_input = QLineEdit()
                    self.company_input.setPlaceholderText("例如：XX建筑工程有限公司")
                    self.company_input.setText(self.default_info.get('company_name', ''))
                    company_layout.addWidget(company_label)
                    company_layout.addWidget(self.company_input)
                    layout.addLayout(company_layout)
                    
                    # 工程编号
                    number_layout = QHBoxLayout()
                    number_label = QLabel("工程编号:")
                    number_label.setFixedWidth(80)
                    self.project_number_input = QLineEdit()
                    self.project_number_input.setPlaceholderText("例如：2024-HE-001")
                    self.project_number_input.setText(self.default_info.get('project_number', ''))
                    number_layout.addWidget(number_label)
                    number_layout.addWidget(self.project_number_input)
                    layout.addLayout(number_layout)
                    
                    # 工程名称
                    project_layout = QHBoxLayout()
                    project_label = QLabel("工程名称:")
                    project_label.setFixedWidth(80)
                    self.project_input = QLineEdit()
                    self.project_input.setPlaceholderText("例如：化工厂换热系统")
                    self.project_input.setText(self.default_info.get('project_name', ''))
                    project_layout.addWidget(project_label)
                    project_layout.addWidget(self.project_input)
                    layout.addLayout(project_layout)
                    
                    # 子项名称
                    subproject_layout = QHBoxLayout()
                    subproject_label = QLabel("子项名称:")
                    subproject_label.setFixedWidth(80)
                    self.subproject_input = QLineEdit()
                    self.subproject_input.setPlaceholderText("例如：主生产区换热器")
                    self.subproject_input.setText(self.default_info.get('subproject_name', ''))
                    subproject_layout.addWidget(subproject_label)
                    subproject_layout.addWidget(self.subproject_input)
                    layout.addLayout(subproject_layout)
                    
                    # 计算书编号
                    report_number_layout = QHBoxLayout()
                    report_number_label = QLabel("计算书编号:")
                    report_number_label.setFixedWidth(80)
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
                report_number = self.data_manager.get_next_report_number("HEAT")
            
            dialog = ProjectInfoDialog(self, saved_info, report_number)
            if dialog.exec() == QDialog.Accepted:
                info = dialog.get_info()
                # 验证必填字段
                if not info['project_name']:
                    QMessageBox.warning(self, "输入错误", "工程名称不能为空")
                    return self.get_project_info()  # 重新弹出对话框
                
                # 保存项目信息到数据管理器
                if self.data_manager:
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
            
            # 更宽松的检查条件
            if not result_text or ("计算结果" not in result_text and "输入参数" not in result_text):
                QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
                return None
                
            # 获取工程信息
            project_info = self.get_project_info()
            if not project_info:
                return None  # 用户取消了输入
            
            # 获取当前计算模式
            current_mode = self.mode_combo.currentText()
            
            # 添加报告头信息
            report = f"""工程计算书 - 换热器计算
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
计算工具: ChemCal 工程计算模块
计算模式: {current_mode}
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

    1. 本计算书基于热力学原理及相关标准规范
    2. 计算结果仅供参考，实际应用需考虑安全系数
    3. 重要工程参数应经专业工程师审核确认
    4. 计算条件变更时应重新进行计算
    5. 蒸汽参数计算为简化计算，实际应用请参考蒸汽表

---
生成于 ChemCal 工程计算模块
"""
            return report
            
        except Exception as e:
            print(f"生成计算书失败: {e}")
            return None
    
    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "换热器计算")
    
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "换热器计算")

    def process_content_for_pdf(self, content):
        """处理内容，使其适合PDF显示"""
        # 清理bullet符号
        content = content.replace("•", "")
        # 替换表情图标
        for emoji, text in replacements.items():
            content = content.replace(emoji, text)
        
        # 替换单位符号
        content = content.replace("m³", "m3")
        content = content.replace("g/100g", "g/100g")
        content = content.replace("kg/m³", "kg/m3")
        content = content.replace("Nm³/h", "Nm3/h")
        content = content.replace("Pa·s", "Pa.s")
        content = content.replace("kJ/(kg·K)", "kJ/(kg.K)")
        content = content.replace("W/(K·m²)", "W/(K.m2)")
        
        return content


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = 换热器计算()
    calculator.resize(1200, 800)
    calculator.setWindowTitle("换热器计算器")
    calculator.show()
    
    sys.exit(app.exec())