# vessel_sizing_calculator.py
# 设备尺寸计算模块（支持正向/反向计算，填充系数，高径比，液位报警推荐）

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QScrollArea, QDialog,
    QSpinBox, QButtonGroup, QGridLayout, QFileDialog, QDialogButtonBox,
    QSizePolicy, QCheckBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QDoubleValidator
import math
import re
from datetime import datetime

# 附件选择对话框 -------------------------------------------------
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
class AccessoriesDialog(QDialog):
    """设备附件（支腿、挂耳等）选择对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择设备附件")
        self.setModal(True)
        self.resize(500, 600)
        self.accessory_data = {
            'legs': {'count': 0, 'height': 0, 'section': '圆管', 'size': 0},
            'lugs': {'count': 0, 'type': 'A型', 'size': 0},
            'platform': False
        }
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        desc = QLabel("设置设备附件参数：")
        layout.addWidget(desc)

        scroll = QScrollArea()
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("")
        scroll_layout = QVBoxLayout(scroll_widget)

        # ----- 支腿 -----
        leg_group = QGroupBox("支腿")
        leg_layout = QGridLayout(leg_group)

        leg_layout.addWidget(QLabel("数量:"), 0, 0)
        self.leg_count = QSpinBox()
        self.leg_count.setRange(0, 8)
        self.leg_count.setValue(0)
        self.leg_count.valueChanged.connect(self.on_leg_changed)
        leg_layout.addWidget(self.leg_count, 0, 1)

        leg_layout.addWidget(QLabel("高度 (mm):"), 1, 0)
        self.leg_height = QDoubleSpinBox()
        self.leg_height.setRange(0, 5000)
        self.leg_height.setValue(500)
        self.leg_height.setSuffix(" mm")
        self.leg_height.valueChanged.connect(self.on_leg_changed)
        leg_layout.addWidget(self.leg_height, 1, 1)

        leg_layout.addWidget(QLabel("截面形状:"), 2, 0)
        self.leg_section = QComboBox()
        self.leg_section.setStyleSheet(COMBOBOX_STYLE)
        self.leg_section.addItems(["圆管", "方钢", "工字钢"])
        self.leg_section.currentTextChanged.connect(self.on_leg_changed)
        leg_layout.addWidget(self.leg_section, 2, 1)

        leg_layout.addWidget(QLabel("截面尺寸 (mm):"), 3, 0)
        self.leg_size = QDoubleSpinBox()
        self.leg_size.setRange(10, 500)
        self.leg_size.setValue(100)
        self.leg_size.setSuffix(" mm")
        self.leg_size.valueChanged.connect(self.on_leg_changed)
        leg_layout.addWidget(self.leg_size, 3, 1)

        leg_layout.setColumnStretch(2, 1)
        scroll_layout.addWidget(leg_group)

        # ----- 挂耳 -----
        lug_group = QGroupBox("挂耳")
        lug_layout = QGridLayout(lug_group)

        lug_layout.addWidget(QLabel("数量:"), 0, 0)
        self.lug_count = QSpinBox()
        self.lug_count.setRange(0, 4)
        self.lug_count.setValue(0)
        self.lug_count.valueChanged.connect(self.on_lug_changed)
        lug_layout.addWidget(self.lug_count, 0, 1)

        lug_layout.addWidget(QLabel("类型:"), 1, 0)
        self.lug_type = QComboBox()
        self.lug_type.setStyleSheet(COMBOBOX_STYLE)
        self.lug_type.addItems(["A型（顶部）", "B型（侧壁）"])
        self.lug_type.currentTextChanged.connect(self.on_lug_changed)
        lug_layout.addWidget(self.lug_type, 1, 1)

        lug_layout.addWidget(QLabel("尺寸 (mm):"), 2, 0)
        self.lug_size = QDoubleSpinBox()
        self.lug_size.setRange(50, 1000)
        self.lug_size.setValue(200)
        self.lug_size.setSuffix(" mm")
        self.lug_size.valueChanged.connect(self.on_lug_changed)
        lug_layout.addWidget(self.lug_size, 2, 1)

        scroll_layout.addWidget(lug_group)

        # ----- 操作平台 -----
        platform_group = QGroupBox("操作平台")
        platform_layout = QHBoxLayout(platform_group)
        self.platform_check = QCheckBox("包含操作平台")
        self.platform_check.stateChanged.connect(self.on_platform_changed)
        platform_layout.addWidget(self.platform_check)
        scroll_layout.addWidget(platform_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # 按钮
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("清空所有")
        clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        confirm_btn = QPushButton("确认")
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def on_leg_changed(self):
        self.accessory_data['legs'] = {
            'count': self.leg_count.value(),
            'height': self.leg_height.value(),
            'section': self.leg_section.currentText(),
            'size': self.leg_size.value()
        }

    def on_lug_changed(self):
        self.accessory_data['lugs'] = {
            'count': self.lug_count.value(),
            'type': self.lug_type.currentText(),
            'size': self.lug_size.value()
        }

    def on_platform_changed(self, state):
        self.accessory_data['platform'] = (state == Qt.Checked)

    def clear_all(self):
        self.leg_count.setValue(0)
        self.lug_count.setValue(0)
        self.platform_check.setChecked(False)
        self.accessory_data = {
            'legs': {'count': 0, 'height': 500, 'section': '圆管', 'size': 100},
            'lugs': {'count': 0, 'type': 'A型', 'size': 200},
            'platform': False
        }

    def get_accessory_data(self):
        return self.accessory_data


# 主计算类 -------------------------------------------------------
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


class 设备尺寸计算(QWidget):
    """设备直径和高度计算模块，支持多种容器形式和反向计算"""
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)

        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()

        self.accessory_data = {
            'legs': {'count': 0, 'height': 0, 'section': '', 'size': 0},
            'lugs': {'count': 0, 'type': '', 'size': 0},
            'platform': False
        }
        self.setup_ui()
        self.setup_defaults()

    def init_data_manager(self):
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
            print("使用共享的数据管理器实例")
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None

    def setup_ui(self):
        """创建左右布局的UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 左侧输入区域
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        scroll_left.setWidgetResizable(True)

        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 说明
        desc = QLabel("计算设备的直径、高度、容积、重量等参数，支持正向/反向计算。")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc)

        # ----- 计算模式选择（按钮组）-----
        mode_group = QGroupBox("计算模式")
        mode_group.setStyleSheet(GROUP_STYLE)
        mode_layout = QHBoxLayout(mode_group)

        self.mode_button_group = QButtonGroup(self)
        self.mode_buttons = {}

        # 定义模式按钮（反向计算、正向计算）
        modes = [
            ("反向计算", "根据目标工作容积求解直径和高度"),
            ("正向计算", "根据直径和圆柱高度计算容积")
        ]

        for i, (mode_name, tooltip) in enumerate(modes):
            btn = QPushButton(mode_name)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet("""
                QPushButton {
                    /* unselected bg via theme */
                    border: 1px solid #666;
                    border-radius: 4px;
                    padding: 8px;
                    text-align: center;
                    /* color via theme */
                }
                QPushButton:checked {
                    background-color: #3498db;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #d5dbdb;
                    color: green;
                }
            """)
            self.mode_button_group.addButton(btn, i)
            mode_layout.addWidget(btn)
            self.mode_buttons[mode_name] = btn

        # 默认选中反向计算
        self.mode_buttons["反向计算"].setChecked(True)
        self.mode_button_group.buttonClicked.connect(self.on_mode_button_clicked)

        mode_layout.addStretch()
        left_layout.addWidget(mode_group)

        # ----- 输入参数组 -----
        input_group = QGroupBox("设备参数")
        input_group.setStyleSheet(GROUP_STYLE)
        grid = QGridLayout(input_group)
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(10)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)

        row = 0

        # 填充系数
        grid.addWidget(self._create_label("填充系数 φ:"), row, 0)
        self.fill_factor_input = QLineEdit()
        self.fill_factor_input.setValidator(QDoubleValidator(0.1, 1.0, 3))
        self.fill_factor_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.fill_factor_input.setText("0.85")
        self.fill_factor_input.setPlaceholderText("0.85")
        grid.addWidget(self.fill_factor_input, row, 1)
        self.fill_hint = QLabel("工作容积 / 几何容积")
        self.fill_hint.setStyleSheet("font-style: italic;")
        grid.addWidget(self.fill_hint, row, 2)
        row += 1

        # 高径比 H/D（圆柱部分）
        grid.addWidget(self._create_label("高径比 H/D:"), row, 0)
        self.hd_ratio_input = QLineEdit()
        self.hd_ratio_input.setValidator(QDoubleValidator(0.2, 10.0, 2))
        self.hd_ratio_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.hd_ratio_input.setText("2.0")
        self.hd_ratio_input.setPlaceholderText("例如 2.0")
        grid.addWidget(self.hd_ratio_input, row, 1)
        self.hd_combo = QComboBox()
        self.hd_combo.setStyleSheet(COMBOBOX_STYLE)
        self.hd_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.hd_combo.addItems(["1:1", "1.5:1", "2:1", "3:1", "自定义"])
        self.hd_combo.currentTextChanged.connect(self.on_hd_combo_changed)
        grid.addWidget(self.hd_combo, row, 2)
        row += 1

        # 目标工作容积（反向模式）
        self.target_vol_label = self._create_label("目标工作容积 (m³):")
        grid.addWidget(self.target_vol_label, row, 0)
        self.target_vol_input = QLineEdit()
        self.target_vol_input.setValidator(QDoubleValidator(0.001, 10000, 3))
        self.target_vol_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.target_vol_input.setPlaceholderText("例如 10.0")
        grid.addWidget(self.target_vol_input, row, 1)
        self.target_vol_hint = QLabel("用户期望的工作容积")
        self.target_vol_hint.setStyleSheet("font-style: italic;")
        grid.addWidget(self.target_vol_hint, row, 2)
        row += 1

        # 设备直径（正向模式）
        self.diameter_label = self._create_label("直径 D (mm):")
        grid.addWidget(self.diameter_label, row, 0)
        self.diameter_input = QLineEdit()
        self.diameter_input.setValidator(QDoubleValidator(1, 10000, 2))
        self.diameter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.diameter_input.setPlaceholderText("例如 1000")
        grid.addWidget(self.diameter_input, row, 1)
        self.diameter_hint = QLabel("标准直径参考")
        self.diameter_hint.setStyleSheet("font-style: italic;")
        grid.addWidget(self.diameter_hint, row, 2)
        row += 1

        # 圆柱高度（正向模式）
        self.cyl_height_label = self._create_label("圆柱高度 H (mm):")
        grid.addWidget(self.cyl_height_label, row, 0)
        self.cyl_height_input = QLineEdit()
        self.cyl_height_input.setValidator(QDoubleValidator(0, 50000, 2))
        self.cyl_height_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cyl_height_input.setPlaceholderText("例如 2000")
        grid.addWidget(self.cyl_height_input, row, 1)
        self.cyl_height_hint = QLabel("圆柱部分高度")
        self.cyl_height_hint.setStyleSheet("font-style: italic;")
        grid.addWidget(self.cyl_height_hint, row, 2)
        row += 1

        # 顶部类型
        grid.addWidget(self._create_label("顶部封头:"), row, 0)
        self.top_type = QComboBox()
        self.top_type.setStyleSheet(COMBOBOX_STYLE)
        self.top_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.top_type.addItems(["平顶", "椭圆封头", "锥形封头", "碟形封头"])
        self.top_type.currentTextChanged.connect(self.on_top_type_changed)
        grid.addWidget(self.top_type, row, 1)

        # 顶部封头深度关联选项（移到第二列右侧，第三列留空）
        self.top_auto_check = QCheckBox("深度与直径成比例")
        self.top_auto_check.setChecked(True)
        self.top_auto_check.stateChanged.connect(self.on_top_auto_changed)
        grid.addWidget(self.top_auto_check, row, 2)
        row += 1

        # 顶部参数输入（深度或角度）
        self.top_param_label = QLabel("深度/角度:")
        self.top_param_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.top_param_label, row, 0)
        self.top_param_input = QLineEdit()
        self.top_param_input.setPlaceholderText("输入深度或角度")
        self.top_param_input.setValidator(QDoubleValidator(0, 90, 2))
        self.top_param_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.top_param_input, row, 1)
        self.top_param_unit = QLabel("mm 或 °")
        self.top_param_unit.setStyleSheet("color: #7f8c8d;")
        grid.addWidget(self.top_param_unit, row, 2)
        row += 1

        # 底部类型
        grid.addWidget(self._create_label("底部封头:"), row, 0)
        self.bottom_type = QComboBox()
        self.bottom_type.setStyleSheet(COMBOBOX_STYLE)
        self.bottom_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.bottom_type.addItems(["平底", "椭圆封头", "锥形封头", "碟形封头", "斜底"])
        self.bottom_type.currentTextChanged.connect(self.on_bottom_type_changed)
        grid.addWidget(self.bottom_type, row, 1)

        # 底部封头深度关联选项
        self.bottom_auto_check = QCheckBox("深度与直径成比例")
        self.bottom_auto_check.setChecked(True)
        self.bottom_auto_check.stateChanged.connect(self.on_bottom_auto_changed)
        grid.addWidget(self.bottom_auto_check, row, 2)
        row += 1

        # 底部参数输入
        self.bottom_param_label = QLabel("深度/角度:")
        grid.addWidget(self.bottom_param_label, row, 0)
        self.bottom_param_input = QLineEdit()
        self.bottom_param_input.setPlaceholderText("输入深度或角度")
        self.bottom_param_input.setValidator(QDoubleValidator(0, 90, 2))
        self.bottom_param_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.bottom_param_input, row, 1)
        self.bottom_param_unit = QLabel("mm 或 °")
        self.bottom_param_unit.setStyleSheet("color: #7f8c8d;")
        grid.addWidget(self.bottom_param_unit, row, 2)
        row += 1

        # 材料密度
        grid.addWidget(self._create_label("材料密度 (kg/m³):"), row, 0)
        self.density_input = QLineEdit()
        self.density_input.setValidator(QDoubleValidator(100, 20000, 2))
        self.density_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.density_input.setPlaceholderText("例如 7850 (碳钢)")
        self.density_input.setText("7850")
        grid.addWidget(self.density_input, row, 1)
        self.density_combo = QComboBox()
        self.density_combo.setStyleSheet(COMBOBOX_STYLE)
        self.density_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.density_combo.addItems(["碳钢 7850", "不锈钢 7930", "铝 2700", "自定义"])
        self.density_combo.currentTextChanged.connect(self.on_density_combo_changed)
        grid.addWidget(self.density_combo, row, 2)
        row += 1

        # 壁厚
        grid.addWidget(self._create_label("壁厚 (mm):"), row, 0)
        self.wall_thickness = QLineEdit()
        self.wall_thickness.setValidator(QDoubleValidator(0.5, 100, 2))
        self.wall_thickness.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.wall_thickness.setPlaceholderText("例如 8")
        self.wall_thickness.setText("8")
        grid.addWidget(self.wall_thickness, row, 1)
        self.wall_hint = QLabel("用于重量计算")
        self.wall_hint.setStyleSheet("color: #7f8c8d;")
        grid.addWidget(self.wall_hint, row, 2)
        row += 1

        left_layout.addWidget(input_group)

        # 附件选择按钮
        self.accessory_btn = QPushButton("选择附件 (支腿/挂耳)")
        self.accessory_btn.setFont(QFont("Arial", 10))
        self.accessory_btn.clicked.connect(self.select_accessories)
        self.accessory_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6; color: white; border: none;
                border-radius: 6px; padding: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        left_layout.addWidget(self.accessory_btn)

        # 计算按钮
        calc_btn = QPushButton("计算")
        calc_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calc_btn.clicked.connect(self.calculate)
        calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; border: none;
                border-radius: 8px; min-height: 50px; padding: 0px; font-weight: bold;
            }
            QPushButton:hover { background-color: #219955; }
        """)
        calc_btn.setMinimumHeight(50)
        calc_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        left_layout.addWidget(calc_btn)

        # 下载按钮
        download_layout = QHBoxLayout()
        txt_btn = QPushButton("下载计算书(TXT)")
        txt_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        txt_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; border: none;
                border-radius: 6px; padding: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #219653; }
        """)
        txt_btn.clicked.connect(self.download_txt_report)
        pdf_btn = QPushButton("下载计算书(PDF)")
        pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; color: white; border: none;
                border-radius: 6px; padding: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        pdf_btn.clicked.connect(self.generate_pdf_report)
        download_layout.addWidget(txt_btn)
        download_layout.addWidget(pdf_btn)
        left_layout.addLayout(download_layout)
        left_layout.addStretch()

        # 右侧结果显示区域
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        self.result_group = QGroupBox("计算结果")
        self.result_group.setStyleSheet(GROUP_STYLE)
        result_layout = QVBoxLayout(self.result_group)

        self.result_text = QTextEdit()
        self.result_text.setMinimumHeight(500)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #666;
                padding: 8px; /* bg via theme */min-height: 500px;
            }
        """)
        result_layout.addWidget(self.result_text)
        right_layout.addWidget(self.result_group)

        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

    def _create_label(self, text):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet("font-weight: bold; padding-right: 10px;")
        return lbl

    def setup_defaults(self):
        # 默认模式为反向计算
        self.on_mode_button_clicked(self.mode_buttons["反向计算"])
        self.on_top_type_changed("椭圆封头")
        self.on_bottom_type_changed("椭圆封头")
        self.top_auto_check.setChecked(True)
        self.bottom_auto_check.setChecked(True)
        self.top_param_input.setEnabled(False)
        self.bottom_param_input.setEnabled(False)

    def on_mode_button_clicked(self, button):
        """处理模式按钮点击"""
        mode_text = button.text()
        self.on_mode_changed(mode_text)

    def on_mode_changed(self, mode):
        """根据模式显示/隐藏输入框"""
        if mode == "反向计算":
            self.target_vol_label.setVisible(True)
            self.target_vol_input.setVisible(True)
            self.target_vol_hint.setVisible(True)
            self.diameter_label.setVisible(False)
            self.diameter_input.setVisible(False)
            self.diameter_hint.setVisible(False)
            self.cyl_height_label.setVisible(False)
            self.cyl_height_input.setVisible(False)
            self.cyl_height_hint.setVisible(False)
        else:  # 正向计算
            self.target_vol_label.setVisible(False)
            self.target_vol_input.setVisible(False)
            self.target_vol_hint.setVisible(False)
            self.diameter_label.setVisible(True)
            self.diameter_input.setVisible(True)
            self.diameter_hint.setVisible(True)
            self.cyl_height_label.setVisible(True)
            self.cyl_height_input.setVisible(True)
            self.cyl_height_hint.setVisible(True)

    def on_hd_combo_changed(self, text):
        if text == "自定义":
            self.hd_ratio_input.setReadOnly(False)
            self.hd_ratio_input.clear()
        else:
            self.hd_ratio_input.setReadOnly(True)
            ratio = text.replace(":", "").strip()
            try:
                val = float(ratio)
                self.hd_ratio_input.setText(f"{val:.2f}")
            except:
                pass

    def on_top_type_changed(self, text):
        self.update_head_ui('top', text)
    def on_bottom_type_changed(self, text):
        self.update_head_ui('bottom', text)

    def update_head_ui(self, which, head_type):
        """根据封头类型更新UI：是否启用深度输入，单位等"""
        if which == 'top':
            auto_check = self.top_auto_check
            param_input = self.top_param_input
            param_label = self.top_param_label
            param_unit = self.top_param_unit
        else:
            auto_check = self.bottom_auto_check
            param_input = self.bottom_param_input
            param_label = self.bottom_param_label
            param_unit = self.bottom_param_unit

        if head_type in ["平顶", "平底"]:
            auto_check.setEnabled(False)
            param_input.setEnabled(False)
            param_label.setText("无参数")
            param_unit.setText("")
        else:
            auto_check.setEnabled(True)
            # 如果勾选自动比例，则禁用输入；否则启用
            enabled = not auto_check.isChecked()
            param_input.setEnabled(enabled)

            if head_type == "锥形封头":
                param_label.setText("锥角 (°):")
                param_unit.setText("°")
            elif head_type in ["椭圆封头", "碟形封头"]:
                param_label.setText("深度 (mm):")
                param_unit.setText("mm")
            elif head_type == "斜底":
                param_label.setText("倾斜角 (°):")
                param_unit.setText("°")
            else:
                param_label.setText("深度/角度:")

    def on_top_auto_changed(self, state):
        enabled = not (state == Qt.Checked)
        self.top_param_input.setEnabled(enabled)
        if enabled and self.top_type.currentText() == "锥形封头":
            self.top_param_unit.setText("°")
        elif enabled:
            self.top_param_unit.setText("mm")

    def on_bottom_auto_changed(self, state):
        enabled = not (state == Qt.Checked)
        self.bottom_param_input.setEnabled(enabled)
        if enabled and self.bottom_type.currentText() == "锥形封头":
            self.bottom_param_unit.setText("°")
        elif enabled:
            self.bottom_param_unit.setText("mm")

    def on_density_combo_changed(self, text):
        if "碳钢" in text:
            self.density_input.setText("7850")
        elif "不锈钢" in text:
            self.density_input.setText("7930")
        elif "铝" in text:
            self.density_input.setText("2700")
        # 自定义保持原值

    def select_accessories(self):
        dialog = AccessoriesDialog(self)
        if dialog.exec():
            self.accessory_data = dialog.get_accessory_data()
            leg = self.accessory_data['legs']
            lug = self.accessory_data['lugs']
            msg = f"已选择: 支腿{leg['count']}个, 挂耳{lug['count']}个"
            if self.accessory_data['platform']:
                msg += ", 含操作平台"
            self.result_text.append(f"\n[附件信息] {msg}")

    # 计算核心 ----------------------------------------------------
    def calculate(self):
        try:
            mode = self.mode_button_group.checkedButton().text()
            fill_factor = float(self.fill_factor_input.text())
            hd_ratio = float(self.hd_ratio_input.text())
            rho_mat = float(self.density_input.text())
            t = float(self.wall_thickness.text()) / 1000   # 壁厚 m

            # 读取封头类型及深度/角度
            top_type = self.top_type.currentText()
            bottom_type = self.bottom_type.currentText()

            if mode == "反向计算":
                # 反向计算模式下D未知，get_head_depth使用比例标记
                top_head_h = self.get_head_depth('top', top_type)
                bottom_head_h = self.get_head_depth('bottom', bottom_type)
                target_work_vol = float(self.target_vol_input.text())   # m³
                # 几何容积 = 工作容积 / 填充系数
                target_geo_vol = target_work_vol / fill_factor

                # 求解直径 D (m) 和圆柱高度 H (m)
                D, H_cyl = self.solve_dimensions(target_geo_vol, hd_ratio,
                                                  top_type, top_head_h,
                                                  bottom_type, bottom_head_h)
            else:  # 正向计算
                D = float(self.diameter_input.text()) / 1000
                H_cyl = float(self.cyl_height_input.text()) / 1000
                # 正向计算模式下传入实际直径D
                top_head_h = self.get_head_depth('top', top_type, D=D)
                bottom_head_h = self.get_head_depth('bottom', bottom_type, D=D)
                # 几何容积
                geo_vol = self.calc_total_volume(D, H_cyl, top_type, top_head_h,
                                                   bottom_type, bottom_head_h)
                target_work_vol = geo_vol * fill_factor

            # 计算总高
            total_height = H_cyl + top_head_h + bottom_head_h

            # 容积
            geo_vol = self.calc_total_volume(D, H_cyl, top_type, top_head_h,
                                               bottom_type, bottom_head_h)
            work_vol = geo_vol * fill_factor

            # 内表面积（近似）
            area = self.calc_total_area(D, H_cyl, top_type, top_head_h,
                                         bottom_type, bottom_head_h)

            # 重量（材料体积 * 密度）
            steel_volume = area * t
            weight = steel_volume * rho_mat

            # 附件信息
            leg_info = self.accessory_data['legs']
            lug_info = self.accessory_data['lugs']
            platform = self.accessory_data['platform']

            # 总高（含支腿）
            total_height_with_legs = total_height
            if leg_info['count'] > 0 and leg_info['height'] > 0:
                total_height_with_legs += leg_info['height'] / 1000

            # 液位报警推荐（近似）
            alarms = self.recommend_alarms(D, H_cyl, top_head_h, bottom_head_h, fill_factor)

            # 格式化输出
            result = self._format_result(
                D_m=D, H_cyl_m=H_cyl, top_type=top_type, top_h=top_head_h,
                bottom_type=bottom_type, bottom_h=bottom_head_h,
                total_h=total_height, total_h_legs=total_height_with_legs,
                geo_vol=geo_vol, work_vol=work_vol, area=area, weight=weight,
                rho=rho_mat, t=t,
                leg_info=leg_info, lug_info=lug_info, platform=platform,
                alarms=alarms
            )
            self.result_text.setText(result)

        except ValueError as e:
            QMessageBox.warning(self, "输入错误", f"请填写有效的数字: {e}")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"发生未知错误: {e}")

    def _get_history_data(self):
        """提供历史记录数据"""
        mode = self.mode_button_group.checkedButton().text()
        fill_factor = float(self.fill_factor_input.text() or 0)
        hd_ratio = float(self.hd_ratio_input.text() or 0)
        rho_mat = float(self.density_input.text() or 0)
        t = float(self.wall_thickness.text() or 0) / 1000
        top_type = self.top_type.currentText()
        bottom_type = self.bottom_type.currentText()

        inputs = {
            "计算模式": mode,
            "填充系数": fill_factor,
            "高径比": hd_ratio,
            "材料密度_kg_m3": rho_mat,
            "壁厚_mm": t * 1000,
            "顶部封头类型": top_type,
            "底部封头类型": bottom_type
        }

        outputs = {}
        try:
            top_head_h = self.get_head_depth('top', top_type)
            bottom_head_h = self.get_head_depth('bottom', bottom_type)

            if mode == "反向计算":
                target_work_vol = float(self.target_vol_input.text() or 0)
                inputs["目标工作容积_m3"] = target_work_vol
                D, H_cyl = self.solve_dimensions(target_work_vol / fill_factor, hd_ratio,
                                                   top_type, top_head_h, bottom_type, bottom_head_h)
            else:
                D = float(self.diameter_input.text() or 0) / 1000
                H_cyl = float(self.cyl_height_input.text() or 0) / 1000
                inputs["直径_mm"] = D * 1000
                inputs["筒体高度_mm"] = H_cyl * 1000

            geo_vol = self.calc_total_volume(D, H_cyl, top_type, top_head_h, bottom_type, bottom_head_h)
            work_vol = geo_vol * fill_factor
            area = self.calc_total_area(D, H_cyl, top_type, top_head_h, bottom_type, bottom_head_h)
            steel_volume = area * t
            weight = steel_volume * rho_mat
            total_height = H_cyl + top_head_h + bottom_head_h

            outputs = {
                "直径_mm": round(D * 1000, 1),
                "筒体高度_mm": round(H_cyl * 1000, 1),
                "总高度_mm": round(total_height * 1000, 1),
                "几何容积_m3": round(geo_vol, 3),
                "工作容积_m3": round(work_vol, 3),
                "内表面积_m2": round(area, 2),
                "容器重量_kg": round(weight, 1)
            }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def get_head_depth(self, which, head_type, D=None):
        """获取封头深度（m）

        参数:
            which: 'top' 或 'bottom'
            head_type: 封头类型
            D: 筒体直径(m)。正向计算时传入实际值，反向计算时内部由resolve_head_depth动态计算
        """
        if head_type in ["平顶", "平底"]:
            return 0.0

        auto = (self.top_auto_check if which == 'top' else self.bottom_auto_check).isChecked()
        param_input = self.top_param_input if which == 'top' else self.bottom_param_input
        if D is None:
            D = 1.0  # 仅用于比例计算，实际会在求解时动态更新

        if auto:
            # 根据类型返回与直径的比例
            if head_type == "椭圆封头":
                return 0.25 * D   # 标准椭圆深度 = D/4
            elif head_type == "碟形封头":
                return 0.2 * D    # 近似
            elif head_type == "锥形封头":
                # 锥形默认给一个比例，或用户输入角度，这里先返回0.3D作为默认
                return 0.3 * D
            elif head_type == "斜底":
                return 0.0        # 斜底不影响总高？暂时返回0
            else:
                return 0.0
        else:
            # 用户输入值，可能是深度(mm)或角度(°)
            if not param_input.text():
                return 0.0
            val = float(param_input.text()) / 1000  # 转换为m
            if head_type == "锥形封头" and param_input.isEnabled():
                # 此时val是角度（°），需转换为深度：深度 = (D/2) * tan(angle_rad)
                # 如果D未知（反向计算模式D=None），返回角度标记由resolve_head_depth处理
                if D is None or D == 1.0:
                    return -val  # 负值表示角度
                else:
                    angle_rad = math.radians(val)
                    return (D / 2.0) * math.tan(angle_rad)
            else:
                return val   # 深度，单位m

    def head_volume(self, head_type, D, h):
        """计算单个封头容积 (m³)"""
        if head_type == "平顶" or head_type == "平底" or h <= 0:
            return 0.0
        if head_type == "椭圆封头":
            # 椭圆封头（半椭球）：V = π/24 * D³ 当 h = D/4
            # 一般情况：V = 2π/3 * a² * b（半椭球），其中 a=D/2, b=h
            a = D / 2.0
            b = h
            return (2.0 / 3.0) * math.pi * a**2 * b
        elif head_type == "碟形封头":
            # 碟形封头由球面段 + 折边段组成
            # 标准碟形封头：球面半径 R ≈ D，折边半径 r ≈ 0.1D，深度 h ≈ 0.1935D
            R_s = D       # 球面半径
            r_k = 0.1 * D  # 折边半径
            # 球面段（球缺）高度
            if R_s > D / 2:
                h_s = R_s - math.sqrt(R_s**2 - (D / 2 - r_k)**2)
            else:
                h_s = h * 0.7  # 近似
            # 球缺容积
            vol_sphere = math.pi * h_s**2 * (3 * R_s - h_s) / 3.0
            # 折边段容积（近似为截头锥体）
            h_k = h - h_s
            if h_k > 0 and r_k > 0:
                r_top = D / 2 - r_k + r_k * math.sin(math.acos((D/2 - r_k) / R_s)) if R_s > D/2 - r_k else D / 2 - r_k
                vol_knuckle = math.pi * h_k * ((D/2)**2 + r_top**2 + (D/2) * r_top) / 3.0
            else:
                vol_knuckle = 0.0
            return vol_sphere + vol_knuckle
        elif head_type == "锥形封头":
            # 圆锥体积 = 1/3 * π * r^2 * h
            return (1.0/3.0) * math.pi * (D/2)**2 * h
        elif head_type == "斜底":
            # 斜底不增加容积
            return 0.0
        else:
            return 0.0

    def head_area(self, head_type, D, h):
        """计算单个封头内表面积 (m²)"""
        if head_type == "平顶" or head_type == "平底":
            return math.pi * (D/2)**2
        if h <= 0:
            return math.pi * (D/2)**2
        if head_type == "椭圆封头":
            # 半椭球壳表面积（椭圆封头为半个旋转椭球）
            a = D / 2.0  # 赤道半径
            b = h        # 深度（极半径）
            if a <= 0 or b <= 0:
                return math.pi * (D/2)**2
            if abs(a - b) < 1e-10:
                # 半球
                return 2.0 * math.pi * a**2
            # 使用近似公式: A = π * (a² + b²/e * ln((1+e)/(1-e)))
            # 其中 e = sqrt(1 - (b/a)²)
            ratio = b / a
            if ratio >= 1.0:
                # b >= a，近似为半球
                return 2.0 * math.pi * a**2
            e = math.sqrt(1.0 - ratio**2)
            if e < 1e-10:
                return math.pi * a**2
            area = math.pi * (a**2 + (b**2 / e) * math.log((1 + e) / (1 - e)))
            return area
        elif head_type == "碟形封头":
            # 碟形封头由球面段+折边段组成，近似按等效椭圆封头计算
            # 近似面积 = 球面段 + 折边段（简化为1.15*半球面积*修正）
            R_s = D  # 球面半径约等于D
            r_k = 0.1 * D  # 折边半径
            # 球面段面积（球缺）：2π*R*h_s，其中h_s为球缺高度
            h_s = R_s - math.sqrt(R_s**2 - (D/2)**2) if R_s > D/2 else h
            area_sphere = 2 * math.pi * R_s * h_s
            # 折边段近似面积
            area_knuckle = 2 * math.pi * r_k * (D/2 - r_k) * math.pi / 2
            return area_sphere + area_knuckle
        elif head_type == "锥形封头":
            r = D/2
            l = math.sqrt(r**2 + h**2)
            return math.pi * r * l
        else:
            return math.pi * (D/2)**2

    def calc_total_volume(self, D, H_cyl, top_type, top_h, bottom_type, bottom_h):
        """计算总几何容积"""
        vol_cyl = math.pi * (D/2)**2 * H_cyl
        vol_top = self.head_volume(top_type, D, top_h)
        vol_bottom = self.head_volume(bottom_type, D, bottom_h)
        return vol_cyl + vol_top + vol_bottom

    def calc_total_area(self, D, H_cyl, top_type, top_h, bottom_type, bottom_h):
        """计算总内表面积"""
        area_cyl = math.pi * D * H_cyl
        area_top = self.head_area(top_type, D, top_h)
        area_bottom = self.head_area(bottom_type, D, bottom_h)
        return area_cyl + area_top + area_bottom

    def solve_dimensions(self, target_vol, hd_ratio,
                         top_type, top_head_h,
                         bottom_type, bottom_head_h):
        """
        反向求解直径 D 和圆柱高度 H_cyl
        参数:
            target_vol: 目标几何容积 (m³)
            hd_ratio: 高径比 H_cyl/D
            top_type, top_head_h: 顶部封头类型和深度（若为负值表示角度）
            bottom_type, bottom_head_h: 底部封头类型和深度
        返回:
            D (m), H_cyl (m)
        """
        # 定义目标函数 f(D) = 当前容积 - target_vol
        def f(D):
            # 根据封头类型计算实际深度
            top_h = self.resolve_head_depth(top_type, top_head_h, D)
            bottom_h = self.resolve_head_depth(bottom_type, bottom_head_h, D)
            H_cyl = hd_ratio * D
            vol = self.calc_total_volume(D, H_cyl, top_type, top_h, bottom_type, bottom_h)
            return vol - target_vol

        # 二分法求解 D
        D_low = 0.1   # 最小直径 0.1 m
        D_high = 10.0 # 最大直径 10 m
        f_low = f(D_low)
        f_high = f(D_high)

        # 检查符号
        if f_low * f_high > 0:
            # 同号，可能范围不够，尝试扩展
            D_high = 20.0
            f_high = f(D_high)
            if f_low * f_high > 0:
                raise ValueError("无法在合理直径范围内找到解，请检查输入参数")

        for _ in range(100):
            D_mid = (D_low + D_high) / 2
            f_mid = f(D_mid)
            if abs(f_mid) < 1e-6:
                D = D_mid
                H_cyl = hd_ratio * D
                return D, H_cyl
            if f_mid * f_low < 0:
                D_high = D_mid
                f_high = f_mid
            else:
                D_low = D_mid
                f_low = f_mid

        D = (D_low + D_high) / 2
        H_cyl = hd_ratio * D
        return D, H_cyl

    def resolve_head_depth(self, head_type, h_value, D):
        """
        根据封头类型和h_value（可能为负角度）返回实际深度（m）
        """
        if head_type in ["平顶", "平底"]:
            return 0.0
        if h_value >= 0:
            return h_value  # 直接为深度
        else:
            # 负值表示角度（°），仅对锥形封头有意义
            angle_deg = -h_value
            angle_rad = math.radians(angle_deg)
            # 锥段高度 = (D/2) * tan(angle)  （假设角度是从水平起算的锥角？通常锥角是顶角，这里简化）
            return (D / 2.0) * math.tan(angle_rad)

    def recommend_alarms(self, D, H_cyl, top_h, bottom_h, fill_factor):
        """
        推荐液位报警值 (mm, 从底部起算)
        返回字典: {'HH': , 'H': , 'L': , 'LL': }
        """
        # 总高
        total_h = H_cyl + top_h + bottom_h

        # 底部封头深度作为基准
        bottom_extra = bottom_h

        # 圆柱部分高度
        cyl_h = H_cyl

        # 安全余量
        bottom_margin = 0.1   # 100 mm
        top_margin = 0.2      # 200 mm

        # 工作容积对应的液位高度需要积分，这里简化：
        # 假设容积与液位近似线性（实际上封头部分非线性，但粗略）
        # 估算20%和80%工作容积对应的液位高度比例
        # 忽略封头非线性，取线性比例
        L_percent = 0.2
        H_percent = 0.8

        # 液位高度计算
        LL = bottom_extra + bottom_margin
        L = bottom_extra + cyl_h * L_percent
        H = bottom_extra + cyl_h * H_percent
        HH = total_h - top_margin

        # 转换为 mm
        alarms = {
            'LL': LL * 1000,
            'L': L * 1000,
            'H': H * 1000,
            'HH': HH * 1000
        }
        return alarms

    def _format_result(self, D_m, H_cyl_m, top_type, top_h, bottom_type, bottom_h,
                       total_h, total_h_legs, geo_vol, work_vol, area, weight,
                       rho, t, leg_info, lug_info, platform, alarms):
        """格式化计算结果"""
        lines = []
        lines.append("══════════════════════════════════════")
        lines.append(" 输入参数")
        lines.append("══════════════════════════════════════")
        lines.append(f"    填充系数: {float(self.fill_factor_input.text()):.2f}")
        lines.append(f"    高径比 H/D: {float(self.hd_ratio_input.text()):.2f}")
        # 根据模式显示不同的输入
        mode = self.mode_button_group.checkedButton().text()
        if mode == "反向计算":
            lines.append(f"    目标工作容积: {float(self.target_vol_input.text()) if self.target_vol_input.text() else 0:.3f} m³")
        else:
            lines.append(f"    直径: {D_m*1000:.1f} mm")
            lines.append(f"    圆柱高度: {H_cyl_m*1000:.1f} mm")
        lines.append(f"    顶部封头: {top_type}" + (f" (深度 {top_h*1000:.1f} mm)" if top_h>0 else ""))
        lines.append(f"    底部封头: {bottom_type}" + (f" (深度 {bottom_h*1000:.1f} mm)" if bottom_h>0 else ""))
        lines.append(f"    材料密度: {rho:.0f} kg/m³")
        lines.append(f"    壁厚: {t*1000:.1f} mm")

        lines.append("\n══════════════════════════════════════")
        lines.append("计算结果")
        lines.append("══════════════════════════════════════")
        lines.append(f"    设备直径: {D_m*1000:.1f} mm")
        lines.append(f"    圆柱高度: {H_cyl_m*1000:.1f} mm")
        lines.append(f"    设备总高（本体）: {total_h*1000:.1f} mm")
        if leg_info['count'] > 0:
            lines.append(f"    设备总高（含支腿）: {total_h_legs*1000:.1f} mm")
        lines.append(f"    几何容积: {geo_vol:.3f} m³")
        lines.append(f"    工作容积: {work_vol:.3f} m³")
        lines.append(f"    内表面积: {area:.2f} m²")
        lines.append(f"    设备重量（近似）: {weight:.1f} kg")

        lines.append("\n══════════════════════════════════════")
        lines.append("液位报警推荐值 (mm，从底部起算)")
        lines.append("══════════════════════════════════════")
        lines.append(f"    低低位 LL: {alarms['LL']:.0f} mm")
        lines.append(f"    低位 L:   {alarms['L']:.0f} mm")
        lines.append(f"    高位 H:   {alarms['H']:.0f} mm")
        lines.append(f"    高高位 HH: {alarms['HH']:.0f} mm")
        lines.append("    (仅供参考，请根据工艺最终确定)")

        lines.append("\n══════════════════════════════════════")
        lines.append("附件信息")
        lines.append("══════════════════════════════════════")
        if leg_info['count'] > 0:
            lines.append(f"    支腿: {leg_info['count']}个, 高{leg_info['height']:.0f} mm, 截面{leg_info['section']} {leg_info['size']:.0f} mm")
        else:
            lines.append("    支腿: 无")
        if lug_info['count'] > 0:
            lines.append(f"    挂耳: {lug_info['count']}个, 类型{lug_info['type']}, 尺寸{lug_info['size']:.0f} mm")
        else:
            lines.append("    挂耳: 无")
        lines.append(f"    操作平台: {'有' if platform else '无'}")

        lines.append("\n══════════════════════════════════════")
        lines.append("计算说明")
        lines.append("══════════════════════════════════════")
        lines.append("    • 反向计算采用二分法求解直径")
        lines.append("    • 容积和表面积基于几何公式近似计算")
        lines.append("    • 重量按均匀壁厚估算，未扣除开孔等")
        lines.append("    • 液位报警为线性近似值，仅供参考")
        lines.append("    • 结果仅供参考，详细设计请咨询专业人员")
        lines.append("\n--- 生成于 CalcE 设备尺寸模块 ---")

        return "\n".join(lines)

    # 报告生成相关 -------------------------------------------------
    def get_project_info(self):
        """获取工程信息（复用压降模块的方法）"""
        try:
            class ProjectInfoDialog(QDialog):
                def __init__(self, parent=None, default_info=None, report_number=""):
                    super().__init__(parent)
                    self.default_info = default_info or {}
                    self.report_number = report_number
                    self.setWindowTitle("工程信息")
                    self.setFixedSize(400, 300)
                    self.setup_ui()

                def setup_ui(self):
                    layout = QVBoxLayout(self)
                    title = QLabel("请输入工程信息")
                    title.setStyleSheet("font-weight: bold; font-size: 14px;")
                    layout.addWidget(title)

                    hbox = QHBoxLayout()
                    hbox.addWidget(QLabel("公司名称:"))
                    self.company = QLineEdit()
                    self.company.setText(self.default_info.get('company_name', ''))
                    hbox.addWidget(self.company)
                    layout.addLayout(hbox)

                    hbox = QHBoxLayout()
                    hbox.addWidget(QLabel("工程编号:"))
                    self.proj_no = QLineEdit()
                    self.proj_no.setText(self.default_info.get('project_number', ''))
                    hbox.addWidget(self.proj_no)
                    layout.addLayout(hbox)

                    hbox = QHBoxLayout()
                    hbox.addWidget(QLabel("工程名称:"))
                    self.proj_name = QLineEdit()
                    self.proj_name.setText(self.default_info.get('project_name', ''))
                    hbox.addWidget(self.proj_name)
                    layout.addLayout(hbox)

                    hbox = QHBoxLayout()
                    hbox.addWidget(QLabel("子项名称:"))
                    self.subproj = QLineEdit()
                    self.subproj.setText(self.default_info.get('subproject_name', ''))
                    hbox.addWidget(self.subproj)
                    layout.addLayout(hbox)

                    hbox = QHBoxLayout()
                    hbox.addWidget(QLabel("计算书编号:"))
                    self.report_no = QLineEdit()
                    self.report_no.setText(self.report_number)
                    hbox.addWidget(self.report_no)
                    layout.addLayout(hbox)

                    btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                    btn_box.accepted.connect(self.accept)
                    btn_box.rejected.connect(self.reject)
                    layout.addWidget(btn_box)

                def get_info(self):
                    return {
                        'company_name': self.company.text().strip(),
                        'project_number': self.proj_no.text().strip(),
                        'project_name': self.proj_name.text().strip(),
                        'subproject_name': self.subproj.text().strip(),
                        'report_number': self.report_no.text().strip()
                    }

            saved_info = self.data_manager.get_project_info() if self.data_manager else {}
            report_no = self.data_manager.get_next_report_number("VS") if self.data_manager else ""
            dialog = ProjectInfoDialog(self, saved_info, report_no)
            if dialog.exec() == QDialog.Accepted:
                info = dialog.get_info()
                if not info['project_name']:
                    QMessageBox.warning(self, "输入错误", "工程名称不能为空")
                    return self.get_project_info()
                if self.data_manager:
                    self.data_manager.update_project_info(info)
                return info
            return None
        except Exception as e:
            print(f"获取工程信息失败: {e}")
            return None

    def generate_report(self):
        """生成完整计算书"""
        result_text = self.result_text.toPlainText()
        if not result_text or "计算结果" not in result_text:
            QMessageBox.warning(self, "生成失败", "请先进行计算")
            return None

        proj_info = self.get_project_info()
        if not proj_info:
            return None

        header = f"""工程计算书 - 设备尺寸计算
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
计算工具: CalcE 工程计算模块
========================================

"""
        footer = f"""
══════════
 工程信息
══════════

    公司名称: {proj_info['company_name']}
    工程编号: {proj_info['project_number']}
    工程名称: {proj_info['project_name']}
    子项名称: {proj_info['subproject_name']}
    计算日期: {datetime.now().strftime('%Y-%m-%d')}

══════════
计算书标识
══════════

    计算书编号: {proj_info.get('report_number', 'VS-'+datetime.now().strftime('%Y%m%d')+'-001')}
    版本: 1.0
    状态: 正式计算书

══════════
备注说明
══════════

    1. 本计算书基于相关设计规范
    2. 计算结果仅供参考，需经专业工程师审核
    3. 变更条件应重新计算

--- 生成于 CalcE 工程计算模块
"""
        return header + result_text + footer

    def download_txt_report(self):
        try:
            content = self.generate_report()
            if not content:
                return
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"设备尺寸计算书_{timestamp}.txt"
            path, _ = QFileDialog.getSaveFileName(self, "保存计算书", default_name, "Text Files (*.txt)")
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                QMessageBox.information(self, "成功", f"计算书已保存至:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def generate_pdf_report(self):
        try:
            content = self.generate_report()
            if not content:
                return False
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"设备尺寸计算书_{timestamp}.pdf"
            path, _ = QFileDialog.getSaveFileName(self, "保存PDF", default_name, "PDF Files (*.pdf)")
            if not path:
                return False

            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.units import inch
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                import os

                font_registered = False
                font_paths = [
                    "C:/Windows/Fonts/simhei.ttf",
                    "C:/Windows/Fonts/msyh.ttc",
                    "/System/Library/Fonts/Arial.ttf",
                ]
                for fp in font_paths:
                    if os.path.exists(fp):
                        try:
                            pdfmetrics.registerFont(TTFont('ChineseFont', fp))
                            font_registered = True
                            break
                        except:
                            continue
                if not font_registered:
                    pdfmetrics.registerFont(TTFont('ChineseFont', 'Helvetica'))

                doc = SimpleDocTemplate(path, pagesize=A4)
                styles = getSampleStyleSheet()
                chinese_style = ParagraphStyle(
                    'ChineseStyle',
                    parent=styles['Normal'],
                    fontName='ChineseFont',
                    fontSize=10,
                    leading=14,
                )
                story = []
                for line in content.split('\n'):
                    if line.strip():
                        line = line.replace('═', '=').replace('─', '-')
                        line = line.replace(' ', '&nbsp;')
                        p = Paragraph(line, chinese_style)
                        story.append(p)
                        story.append(Spacer(1, 0.05*inch))
                doc.build(story)
                QMessageBox.information(self, "成功", f"PDF已保存至:\n{path}")
                return True
            except ImportError:
                QMessageBox.warning(self, "功能缺失", "请安装reportlab: pip install reportlab")
                return False
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成PDF失败: {e}")
            return False


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = 设备尺寸计算()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())