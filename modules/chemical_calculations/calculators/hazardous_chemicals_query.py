"""
危险化学品查询系统 - Tab式查询计算器
提供化学品搜索、分类浏览、详细信息查看和报告生成功能
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QFrame,
    QScrollArea, QDialog, QSpinBox, QButtonGroup, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QListWidget, QListWidgetItem, QProgressBar, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QDoubleValidator, QColor
import json
import re
import os
from modules.combo_box_utils import ComboBoxWheelBlocker

# QGroupBox统一样式

# 统一滚动条样式
SCROLLBAR_STYLE = """
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #c0c0c0;
        border-radius: 4px;
        min-height: 30px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }
    QScrollBar:horizontal {
        background: transparent;
        height: 8px;
        margin: 0;
    }
    QScrollBar::handle:horizontal {
        background: #c0c0c0;
        border-radius: 4px;
        min-width: 30px;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
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


class ChemicalDetailDialog(QDialog):
    """化学品详细信息对话框"""

    def __init__(self, parent=None, chemical_data=None):
        super().__init__(parent)
        self.chemical_data = chemical_data or {}
        self.setWindowTitle(f"危险化学品详情 - {chemical_data.get('name', '未知')}")
        self.setModal(True)
        self.resize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        """设置化学品详情UI"""
        layout = QVBoxLayout(self)

        # 创建标签页
        self.tab_widget = QTabWidget()

        # 基本信息标签页
        basic_info_tab = QWidget()
        basic_layout = QVBoxLayout(basic_info_tab)
        basic_layout.addWidget(self.create_basic_info_widget())
        self.tab_widget.addTab(basic_info_tab, " 基本信息")

        # 危险性标签页
        hazard_tab = QWidget()
        hazard_layout = QVBoxLayout(hazard_tab)
        hazard_layout.addWidget(self.create_hazard_info_widget())
        self.tab_widget.addTab(hazard_tab, "危险性")

        # 安全措施标签页
        safety_tab = QWidget()
        safety_layout = QVBoxLayout(safety_tab)
        safety_layout.addWidget(self.create_safety_info_widget())
        self.tab_widget.addTab(safety_tab, "安全措施")

        # 应急处理标签页
        emergency_tab = QWidget()
        emergency_layout = QVBoxLayout(emergency_tab)
        emergency_layout.addWidget(self.create_emergency_info_widget())
        self.tab_widget.addTab(emergency_tab, "应急处理")

        layout.addWidget(self.tab_widget)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover:!checked {
                background-color: #7f8c8d;
            }
        """)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def create_basic_info_widget(self):
        """创建基本信息部件"""
        widget = QScrollArea()
        widget.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }} {SCROLLBAR_STYLE}")
        content = QWidget()
        content.setStyleSheet("")
        layout = QGridLayout(content)
        layout.setVerticalSpacing(8)
        layout.setHorizontalSpacing(15)

        # 标题
        title_label = QLabel(f"{self.chemical_data.get('name', '未知化学品')}")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin: 10px;")
        layout.addWidget(title_label, 0, 0, 1, 2)

        row = 1

        # CAS号
        if self.chemical_data.get('cas'):
            layout.addWidget(QLabel("CAS号:"), row, 0)
            layout.addWidget(QLabel(self.chemical_data['cas']), row, 1)
            row += 1

        # 分子式
        if self.chemical_data.get('formula'):
            layout.addWidget(QLabel("分子式:"), row, 0)
            layout.addWidget(QLabel(self.chemical_data['formula']), row, 1)
            row += 1

        # 分子量
        if self.chemical_data.get('molecular_weight'):
            layout.addWidget(QLabel("分子量:"), row, 0)
            layout.addWidget(QLabel(str(self.chemical_data['molecular_weight'])), row, 1)
            row += 1

        # 外观
        if self.chemical_data.get('appearance'):
            layout.addWidget(QLabel("外观:"), row, 0)
            layout.addWidget(QLabel(self.chemical_data['appearance']), row, 1)
            row += 1

        # 沸点
        if self.chemical_data.get('boiling_point'):
            layout.addWidget(QLabel("沸点:"), row, 0)
            layout.addWidget(QLabel(f"{self.chemical_data['boiling_point']} °C"), row, 1)
            row += 1

        # 熔点
        if self.chemical_data.get('melting_point'):
            layout.addWidget(QLabel("熔点:"), row, 0)
            layout.addWidget(QLabel(f"{self.chemical_data['melting_point']} °C"), row, 1)
            row += 1

        # 密度
        if self.chemical_data.get('density'):
            layout.addWidget(QLabel("密度:"), row, 0)
            layout.addWidget(QLabel(f"{self.chemical_data['density']} g/cm³"), row, 1)
            row += 1

        # 水溶性
        if self.chemical_data.get('water_solubility'):
            layout.addWidget(QLabel("水溶性:"), row, 0)
            layout.addWidget(QLabel(self.chemical_data['water_solubility']), row, 1)
            row += 1

        # 闪点
        if self.chemical_data.get('flash_point'):
            flash_point = self.chemical_data['flash_point']
            layout.addWidget(QLabel("闪点:"), row, 0)
            flash_label = QLabel(f"{flash_point} °C")
            if flash_point < 23:
                flash_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            elif flash_point < 60:
                flash_label.setStyleSheet("color: #e67e22; font-weight: bold;")
            layout.addWidget(flash_label, row, 1)
            row += 1

        # 自燃温度
        if self.chemical_data.get('autoignition_temp'):
            layout.addWidget(QLabel("自燃温度:"), row, 0)
            layout.addWidget(QLabel(f"{self.chemical_data['autoignition_temp']} °C"), row, 1)
            row += 1

        # 爆炸极限
        if self.chemical_data.get('explosion_limits'):
            layout.addWidget(QLabel("爆炸极限:"), row, 0)
            layout.addWidget(QLabel(self.chemical_data['explosion_limits']), row, 1)
            row += 1

        layout.setRowStretch(row, 1)
        widget.setWidget(content)
        return widget

    def create_hazard_info_widget(self):
        """创建危险性信息部件"""
        widget = QScrollArea()
        widget.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }} {SCROLLBAR_STYLE}")
        content = QWidget()
        content.setStyleSheet("")
        layout = QVBoxLayout(content)

        # 危险性类别
        if self.chemical_data.get('hazard_class'):
            class_group = QGroupBox("危险性类别")
            class_layout = QVBoxLayout(class_group)
            hazards = self.chemical_data['hazard_class'].split(';')
            for hazard in hazards:
                if hazard.strip():
                    label = QLabel(f"• {hazard.strip()}")
                    class_layout.addWidget(label)
            layout.addWidget(class_group)

        # GHS象形图
        if self.chemical_data.get('ghs_symbols'):
            ghs_group = QGroupBox("GHS象形图")
            ghs_layout = QVBoxLayout(ghs_group)
            symbols = self.chemical_data['ghs_symbols'].split(';')
            for symbol in symbols:
                if symbol.strip():
                    label = QLabel(f"{symbol.strip()}")
                    ghs_layout.addWidget(label)
            layout.addWidget(ghs_group)

        # 危险性说明
        if self.chemical_data.get('hazard_statements'):
            state_group = QGroupBox("危险性说明")
            state_layout = QVBoxLayout(state_group)
            statements = self.chemical_data['hazard_statements'].split(';')
            for statement in statements:
                if statement.strip():
                    label = QLabel(f"• {statement.strip()}")
                    label.setWordWrap(True)
                    state_layout.addWidget(label)
            layout.addWidget(state_group)

        # 防范说明
        if self.chemical_data.get('precautionary_statements'):
            prec_group = QGroupBox("防范说明")
            prec_layout = QVBoxLayout(prec_group)
            statements = self.chemical_data['precautionary_statements'].split(';')
            for statement in statements:
                if statement.strip():
                    label = QLabel(f"• {statement.strip()}")
                    label.setWordWrap(True)
                    prec_layout.addWidget(label)
            layout.addWidget(prec_group)

        layout.addStretch()
        widget.setWidget(content)
        return widget

    def create_safety_info_widget(self):
        """创建安全措施部件"""
        widget = QScrollArea()
        widget.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }} {SCROLLBAR_STYLE}")
        content = QWidget()
        content.setStyleSheet("")
        layout = QVBoxLayout(content)

        # 操作处置
        if self.chemical_data.get('handling'):
            handle_group = QGroupBox("操作处置")
            handle_layout = QVBoxLayout(handle_group)
            handle_layout.addWidget(QLabel(self.chemical_data['handling']))
            layout.addWidget(handle_group)

        # 储存
        if self.chemical_data.get('storage'):
            storage_group = QGroupBox("储存条件")
            storage_layout = QVBoxLayout(storage_group)
            storage_layout.addWidget(QLabel(self.chemical_data['storage']))
            layout.addWidget(storage_group)

        # 个人防护
        if self.chemical_data.get('personal_protection'):
            protect_group = QGroupBox("个人防护")
            protect_layout = QVBoxLayout(protect_group)
            protections = self.chemical_data['personal_protection'].split(';')
            for protection in protections:
                if protection.strip():
                    label = QLabel(f"• {protection.strip()}")
                    protect_layout.addWidget(label)
            layout.addWidget(protect_group)

        # 工程控制
        if self.chemical_data.get('engineering_controls'):
            control_group = QGroupBox("工程控制")
            control_layout = QVBoxLayout(control_group)
            controls = self.chemical_data['engineering_controls'].split(';')
            for control in controls:
                if control.strip():
                    label = QLabel(f"• {control.strip()}")
                    control_layout.addWidget(label)
            layout.addWidget(control_group)

        layout.addStretch()
        widget.setWidget(content)
        return widget

    def create_emergency_info_widget(self):
        """创建应急处理部件"""
        widget = QScrollArea()
        widget.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }} {SCROLLBAR_STYLE}")
        content = QWidget()
        content.setStyleSheet("")
        layout = QVBoxLayout(content)

        # 火灾爆炸措施
        if self.chemical_data.get('fire_fighting'):
            fire_group = QGroupBox("火灾爆炸措施")
            fire_layout = QVBoxLayout(fire_group)
            fire_layout.addWidget(QLabel(self.chemical_data['fire_fighting']))
            layout.addWidget(fire_group)

        # 泄漏应急处理
        if self.chemical_data.get('spill_handling'):
            spill_group = QGroupBox("泄漏应急处理")
            spill_layout = QVBoxLayout(spill_group)
            spill_layout.addWidget(QLabel(self.chemical_data['spill_handling']))
            layout.addWidget(spill_group)

        # 急救措施
        if self.chemical_data.get('first_aid'):
            aid_group = QGroupBox("急救措施")
            aid_layout = QVBoxLayout(aid_group)
            aid_measures = self.chemical_data['first_aid'].split(';')
            for measure in aid_measures:
                if measure.strip():
                    label = QLabel(f"• {measure.strip()}")
                    aid_layout.addWidget(label)
            layout.addWidget(aid_group)

        layout.addStretch()
        widget.setWidget(content)
        return widget


class HazardousChemicalsQuery(QWidget):
    """危险化学品查询系统 - Tab式查询计算器"""
    calculation_type = "hazardous_chemicals_query"

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self.chemicals_data = []
        self.filtered_chemicals = []
        self.current_chemical = None
        self.setup_ui()
        self.load_chemicals_database()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self._wheel_blocker = ComboBoxWheelBlocker(self)
        for combo in self.findChildren(QComboBox):
            combo.installEventFilter(self._wheel_blocker)

    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from modules.data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception:
            self.data_manager = None

    def setup_ui(self):
        """设置危险化学品查询UI"""
        # 主布局：QHBoxLayout，间距15，边距10
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ========== 左侧输入区 ==========
        # 使用QScrollArea包裹，maxWidth=900
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent; }}
            {SCROLLBAR_STYLE}
        """)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_widget.setStyleSheet("background: transparent;")

        # 搜索类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("搜索类型:"))

        self.search_type_combo = QComboBox()
        self.search_type_combo.setStyleSheet(COMBOBOX_STYLE)
        self.search_type_combo.addItems([
            "按名称搜索",
            "按CAS号搜索",
            "按分子式搜索",
            "按危险性搜索"
        ])
        type_layout.addWidget(self.search_type_combo)
        left_layout.addLayout(type_layout)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入化学品名称、CAS号或分子式...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        left_layout.addWidget(self.search_input)

        # 危险性筛选
        hazard_layout = QHBoxLayout()
        hazard_layout.addWidget(QLabel("危险性筛选:"))

        self.hazard_filter_combo = QComboBox()
        self.hazard_filter_combo.setStyleSheet(COMBOBOX_STYLE)
        self.hazard_filter_combo.addItems([
            "所有危险性",
            "易燃液体",
            "易燃气体",
            "易燃固体",
            "氧化性物质",
            "毒性物质",
            "腐蚀性物质",
            "爆炸性物质",
            "健康危害物质"
        ])
        self.hazard_filter_combo.currentTextChanged.connect(self.filter_chemicals)
        hazard_layout.addWidget(self.hazard_filter_combo)
        left_layout.addLayout(hazard_layout)

        # ========== 化学品列表 ==========
        self.chemicals_list = QListWidget()
        self.chemicals_list.itemDoubleClicked.connect(self.show_chemical_detail)
        self.chemicals_list.itemClicked.connect(self.show_chemical_detail)
        self.chemicals_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.chemicals_list.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid #ecf0f1;
                border-radius: 6px;
                /* background-color via theme */
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }}
            QListWidget::item:selected {{
                background-color: #3498db;
                color: white;
            }}
            {SCROLLBAR_STYLE}
        """)
        left_layout.addWidget(self.chemicals_list)

        # 统计信息
        self.stats_label = QLabel("共加载 0 种化学品")
        self.stats_label.setStyleSheet("font-style: italic; padding: 5px;")
        left_layout.addWidget(self.stats_label)

        # 设置左侧scroll area的内容
        left_scroll.setWidget(left_widget)

        # ========== 右侧结果区 ==========
        # minWidth=300
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        # 结果详情GroupBox
        result_group = QGroupBox("查询结果")
        result_layout = QVBoxLayout(result_group)

        # 右侧QTextEdit：readOnly=True，背景#f8f9fa，圆角6px，minHeight=500px
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.detail_text.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid #ecf0f1;
                border-radius: 6px;
                padding: 8px;
                /* bg via theme */min-height: 500px;
            }}
            {SCROLLBAR_STYLE}
        """)
        result_layout.addWidget(self.detail_text)

        # result_text 属性别名，用于模板兼容
        self.result_text = self.detail_text

        # 查看详情按钮（绿色，与计算按钮一致）
        self.detail_btn = QPushButton("查看完整详情")
        self.detail_btn.clicked.connect(self.show_full_detail)
        self.detail_btn.setMinimumHeight(50)
        self.detail_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover:!checked {
                background-color: #219955;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.detail_btn.setEnabled(False)
        result_layout.addWidget(self.detail_btn)

        right_layout.addWidget(result_group)

        # ========== 底部按钮行（清空/下载TXT/下载PDF）==========
        button_layout = QHBoxLayout()

        # 清空按钮（灰色）
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_search)
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
                background-color: #a59695;
            } """)
        button_layout.addWidget(self.clear_btn)

        # 下载TXT按钮（绿色）
        self.download_txt_btn = QPushButton("下载计算书(TXT)")
        self.download_txt_btn.clicked.connect(self.download_txt_report)
        self.download_txt_btn.setMinimumHeight(50)
        self.download_txt_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_txt_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover:!checked {
                background-color: #219653;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.download_txt_btn.setEnabled(False)
        button_layout.addWidget(self.download_txt_btn)

        # 下载PDF按钮（红色）
        self.download_pdf_btn = QPushButton("下载计算书(PDF)")
        self.download_pdf_btn.clicked.connect(self.generate_pdf_report)
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
            QPushButton:hover:!checked {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.download_pdf_btn.setEnabled(False)
        button_layout.addWidget(self.download_pdf_btn)

        right_layout.addLayout(button_layout)

        # ========== 将左右两部分添加到主布局 ==========
        # 比例：addWidget(left, 2) / addWidget(right, 1)
        main_layout.addWidget(left_scroll, 2)
        main_layout.addWidget(right_widget, 1)

        # 初始显示
        self.update_chemicals_list()

    def load_chemicals_database(self):
        """加载化学品数据库"""
        # 这里构建一个危险化学品数据库
        self.chemicals_data = [
            {
                "name": "甲醇",
                "cas": "67-56-1",
                "formula": "CH3OH",
                "molecular_weight": 32.04,
                "appearance": "无色透明液体",
                "boiling_point": 64.7,
                "melting_point": -97.6,
                "density": 0.791,
                "water_solubility": "易溶",
                "flash_point": 11.1,
                "autoignition_temp": 464,
                "explosion_limits": "6.0%-36.5%",
                "hazard_class": "易燃液体;毒性物质",
                "ghs_symbols": "易燃;健康危害",
                "hazard_statements": "高度易燃液体和蒸气;吞咽有毒;对眼睛有害",
                "precautionary_statements": "远离热源/火花/明火/热表面;保持容器密闭;戴防护手套/防护眼镜",
                "handling": "在通风良好的地方操作。消除所有火源。",
                "storage": "储存于阴凉、通风处。远离火种、热源。",
                "personal_protection": "防毒面具;化学安全防护眼镜;防静电工作服;橡胶手套",
                "engineering_controls": "局部排风;防爆电器",
                "fire_fighting": "使用抗溶性泡沫、干粉、二氧化碳灭火。用水灭火无效。",
                "spill_handling": "用砂土或其它不燃材料吸收。收集回收或运至废物处理场所。",
                "first_aid": "吸入:迅速脱离现场至空气新鲜处;皮肤接触:脱去污染的衣着，用肥皂水和清水彻底冲洗皮肤;眼睛接触:提起眼睑，用流动清水或生理盐水冲洗"
            },
            {
                "name": "乙醇",
                "cas": "64-17-5",
                "formula": "C2H5OH",
                "molecular_weight": 46.07,
                "appearance": "无色透明液体",
                "boiling_point": 78.4,
                "melting_point": -114.1,
                "density": 0.789,
                "water_solubility": "易溶",
                "flash_point": 12.8,
                "autoignition_temp": 423,
                "explosion_limits": "3.3%-19%",
                "hazard_class": "易燃液体",
                "ghs_symbols": "易燃",
                "hazard_statements": "高度易燃液体和蒸气",
                "precautionary_statements": "远离热源/火花/明火/热表面;保持容器密闭",
                "handling": "在通风良好的地方操作。消除所有火源。",
                "storage": "储存于阴凉、通风处。远离火种、热源。",
                "personal_protection": "化学安全防护眼镜;防静电工作服",
                "engineering_controls": "局部排风;防爆电器",
                "fire_fighting": "使用抗溶性泡沫、干粉、二氧化碳灭火。",
                "spill_handling": "用砂土或其它不燃材料吸收。",
                "first_aid": "吸入:脱离现场至空气新鲜处;皮肤接触:脱去污染的衣着，用流动清水冲洗"
            },
            {
                "name": "丙酮",
                "cas": "67-64-1",
                "formula": "C3H6O",
                "molecular_weight": 58.08,
                "appearance": "无色透明液体",
                "boiling_point": 56.1,
                "melting_point": -94.7,
                "density": 0.791,
                "water_solubility": "易溶",
                "flash_point": -17.8,
                "autoignition_temp": 465,
                "explosion_limits": "2.5%-12.8%",
                "hazard_class": "易燃液体",
                "ghs_symbols": "易燃",
                "hazard_statements": "高度易燃液体和蒸气",
                "precautionary_statements": "远离热源/火花/明火/热表面;保持容器密闭",
                "handling": "在通风良好的地方操作。消除所有火源。",
                "storage": "储存于阴凉、通风处。远离火种、热源。",
                "personal_protection": "化学安全防护眼镜;防静电工作服",
                "engineering_controls": "局部排风;防爆电器",
                "fire_fighting": "使用抗溶性泡沫、干粉、二氧化碳灭火。",
                "spill_handling": "用砂土或其它不燃材料吸收。",
                "first_aid": "吸入:脱离现场至空气新鲜处;皮肤接触:用肥皂水和清水彻底冲洗皮肤"
            },
            {
                "name": "苯",
                "cas": "71-43-2",
                "formula": "C6H6",
                "molecular_weight": 78.11,
                "appearance": "无色透明液体",
                "boiling_point": 80.1,
                "melting_point": 5.5,
                "density": 0.879,
                "water_solubility": "微溶",
                "flash_point": -11.1,
                "autoignition_temp": 498,
                "explosion_limits": "1.2%-7.8%",
                "hazard_class": "易燃液体;致癌物;毒性物质",
                "ghs_symbols": "易燃;健康危害",
                "hazard_statements": "高度易燃液体和蒸气;吞咽会中毒;吸入会中毒;可能致癌",
                "precautionary_statements": "远离热源/火花/明火/热表面;戴防护手套/防护眼镜/面部防护罩",
                "handling": "在通风橱内操作。避免吸入蒸气。",
                "storage": "储存于阴凉、通风处。远离火种、热源。",
                "personal_protection": "防毒面具;化学安全防护眼镜;防渗透手套",
                "engineering_controls": "局部排风;防爆电器",
                "fire_fighting": "使用泡沫、干粉、二氧化碳灭火。",
                "spill_handling": "用砂土或其它不燃材料吸收。收集回收或运至废物处理场所。",
                "first_aid": "吸入:迅速脱离现场至空气新鲜处，就医;皮肤接触:脱去污染的衣着，用肥皂水和清水彻底冲洗皮肤"
            },
            {
                "name": "硫酸",
                "cas": "7664-93-9",
                "formula": "H2SO4",
                "molecular_weight": 98.08,
                "appearance": "无色透明油状液体",
                "boiling_point": 337,
                "melting_point": 10.4,
                "density": 1.84,
                "water_solubility": "易溶",
                "flash_point": "无",
                "autoignition_temp": "无",
                "explosion_limits": "无",
                "hazard_class": "腐蚀性物质;毒性物质",
                "ghs_symbols": "腐蚀性",
                "hazard_statements": "导致严重皮肤灼伤和眼损伤",
                "precautionary_statements": "戴防护手套/防护眼镜/面部防护罩;如进入眼睛：用水小心冲洗几分钟",
                "handling": "在通风良好的地方操作。避免与皮肤和眼睛接触。",
                "storage": "储存于阴凉、干燥、通风处。与碱类、易燃物分开存放。",
                "personal_protection": "防毒面具;防酸碱服;橡胶手套;防护面罩",
                "engineering_controls": "局部排风",
                "fire_fighting": "本品不燃。根据着火原因选择适当灭火剂。",
                "spill_handling": "用砂土、干燥石灰或苏打灰混合。收集回收或运至废物处理场所。",
                "first_aid": "皮肤接触:立即脱去污染的衣着，用大量流动清水冲洗至少15分钟，就医;眼睛接触:立即提起眼睑，用大量流动清水或生理盐水彻底冲洗至少15分钟，就医"
            },
            {
                "name": "氢氧化钠",
                "cas": "1310-73-2",
                "formula": "NaOH",
                "molecular_weight": 40.00,
                "appearance": "白色片状或颗粒",
                "boiling_point": 1390,
                "melting_point": 318,
                "density": 2.13,
                "water_solubility": "易溶",
                "flash_point": "无",
                "autoignition_temp": "无",
                "explosion_limits": "无",
                "hazard_class": "腐蚀性物质",
                "ghs_symbols": "腐蚀性",
                "hazard_statements": "导致严重皮肤灼伤和眼损伤",
                "precautionary_statements": "戴防护手套/防护眼镜/面部防护罩",
                "handling": "在通风良好的地方操作。避免与皮肤和眼睛接触。",
                "storage": "储存于阴凉、干燥、通风处。与酸类分开存放。",
                "personal_protection": "防毒面具;防酸碱服;橡胶手套;防护面罩",
                "engineering_controls": "局部排风",
                "fire_fighting": "本品不燃。根据着火原因选择适当灭火剂。",
                "spill_handling": "用砂土、干燥石灰或苏打灰混合。收集回收或运至废物处理场所。",
                "first_aid": "皮肤接触:立即脱去污染的衣着，用大量流动清水冲洗至少15分钟，就医;眼睛接触:立即提起眼睑，用大量流动清水或生理盐水彻底冲洗至少15分钟，就医"
            },
            {
                "name": "氯气",
                "cas": "7782-50-5",
                "formula": "Cl2",
                "molecular_weight": 70.90,
                "appearance": "黄绿色气体",
                "boiling_point": -34.0,
                "melting_point": -101.0,
                "density": 3.21,
                "water_solubility": "可溶",
                "flash_point": "无",
                "autoignition_temp": "无",
                "explosion_limits": "无",
                "hazard_class": "毒性气体;氧化性气体;腐蚀性物质",
                "ghs_symbols": "毒性;腐蚀性;氧化性",
                "hazard_statements": "吸入会中毒;导致严重皮肤灼伤和眼损伤;可能导致呼吸道刺激",
                "precautionary_statements": "戴防护手套/防护眼镜/面部防护罩;避免吸入气体",
                "handling": "在通风橱内操作。使用适当的呼吸防护装置。",
                "storage": "储存于阴凉、通风处。与可燃物、还原剂分开存放。",
                "personal_protection": "正压自给式呼吸器;防毒面具;防护服",
                "engineering_controls": "局部排风",
                "fire_fighting": "本品不燃。根据着火原因选择适当灭火剂。",
                "spill_handling": "迅速撤离泄漏污染区人员至上风处，并进行隔离。建议应急处理人员戴正压自给式呼吸器。",
                "first_aid": "吸入:迅速脱离现场至空气新鲜处，保持呼吸道通畅，如呼吸困难，给输氧，如呼吸停止，立即进行人工呼吸，就医"
            }
        ]

        self.filtered_chemicals = self.chemicals_data.copy()
        self.filter_chemicals()

    def on_search_text_changed(self, text):
        """处理搜索文本变化"""
        # 使用定时器延迟搜索，避免频繁更新
        if hasattr(self, 'search_timer'):
            self.search_timer.stop()

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(lambda: self.filter_chemicals())
        self.search_timer.start(300)  # 300ms延迟

    def filter_chemicals(self):
        """过滤化学品列表"""
        search_text = self.search_input.text().strip().lower()
        hazard_filter = self.hazard_filter_combo.currentText()
        search_type = self.search_type_combo.currentText()

        self.filtered_chemicals = []

        for chemical in self.chemicals_data:
            # 危险性筛选
            if hazard_filter != "所有危险性" and hazard_filter not in chemical.get('hazard_class', ''):
                continue

            # 搜索筛选
            if search_text:
                if search_type == "按名称搜索":
                    if search_text not in chemical['name'].lower():
                        continue
                elif search_type == "按CAS号搜索":
                    if search_text not in chemical.get('cas', '').lower():
                        continue
                elif search_type == "按分子式搜索":
                    if search_text not in chemical.get('formula', '').lower():
                        continue
                elif search_type == "按危险性搜索":
                    if (search_text not in chemical['name'].lower() and
                        search_text not in chemical.get('hazard_class', '').lower()):
                        continue
            self.filtered_chemicals.append(chemical)

        self.update_chemicals_list()

    def update_chemicals_list(self):
        """更新化学品列表"""
        self.chemicals_list.clear()

        for chemical in self.filtered_chemicals:
            item = QListWidgetItem(chemical['name'])

            # 根据危险性设置颜色
            hazard_class = chemical.get('hazard_class', '')
            if '易燃' in hazard_class and '毒性' in hazard_class:
                item.setBackground(QColor(255, 200, 200))  # 浅红色
            elif '易燃' in hazard_class:
                item.setBackground(QColor(255, 230, 200))  # 浅橙色
            elif '毒性' in hazard_class or '致癌' in hazard_class:
                item.setBackground(QColor(255, 200, 255))  # 浅紫色
            elif '腐蚀性' in hazard_class:
                item.setBackground(QColor(200, 230, 255))  # 浅蓝色

            # 设置提示信息
            tooltip = f"CAS: {chemical.get('cas', '未知')}\n"
            tooltip += f"分子式: {chemical.get('formula', '未知')}\n"
            tooltip += f"危险性: {hazard_class}"
            item.setToolTip(tooltip)

            self.chemicals_list.addItem(item)

        # 更新统计信息
        self.stats_label.setText(f"找到 {len(self.filtered_chemicals)} 种化学品")

    def show_chemical_detail(self, item):
        """显示化学品详情"""
        chemical_name = item.text()
        chemical = next((chem for chem in self.filtered_chemicals if chem['name'] == chemical_name), None)

        if chemical:
            self.current_chemical = chemical
            self.detail_btn.setEnabled(True)
            self.download_txt_btn.setEnabled(True)
            self.download_pdf_btn.setEnabled(True)
            self.update_detail_display(chemical)

    def update_detail_display(self, chemical):
        """更新详情显示"""
        detail_html = f"""
        <div style="font-family: Arial, sans-serif;">
            <h2 style="color: #2c3e50;">{chemical['name']}</h2>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background-color: #f8f9fa; width: 30%;"><strong>CAS号</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{chemical.get('cas', '未知')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background-color: #f8f9fa;"><strong>分子式</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{chemical.get('formula', '未知')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background-color: #f8f9fa;"><strong>分子量</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{chemical.get('molecular_weight', '未知')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background-color: #f8f9fa;"><strong>危险性类别</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{chemical.get('hazard_class', '未知')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background-color: #f8f9fa;"><strong>闪点</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{chemical.get('flash_point', '未知')} °C</td>
                </tr>
            </table>

            <h3 style="color: #e74c3c;">危险性说明</h3>
            <p>{chemical.get('hazard_statements', '无').replace(';', '<br>• ')}</p>

            <h3 style="color: #3498db;">主要防范措施</h3>
            <p>{chemical.get('precautionary_statements', '无').replace(';', '<br>• ')}</p>
        </div>
        """

        self.detail_text.setHtml(detail_html)

    def show_full_detail(self):
        """显示完整详情对话框"""
        if hasattr(self, 'current_chemical') and self.current_chemical:
            dialog = ChemicalDetailDialog(self, self.current_chemical)
            dialog.exec()

    def clear_search(self):
        """清空搜索条件"""
        self.search_input.clear()
        self.hazard_filter_combo.setCurrentIndex(0)
        self.search_type_combo.setCurrentIndex(0)
        self.filtered_chemicals = self.chemicals_data.copy()
        self.update_chemicals_list()
        self.detail_text.clear()
        self.current_chemical = None
        self.detail_btn.setEnabled(False)
        self.download_txt_btn.setEnabled(False)
        self.download_pdf_btn.setEnabled(False)

    def _get_history_data(self):
        """提供历史记录数据"""
        inputs = {}
        outputs = {}
        if hasattr(self, 'current_chemical') and self.current_chemical:
            chem = self.current_chemical
            inputs["化学品名称"] = chem.get("name", "")
            inputs["CAS号"] = chem.get("cas", "")
            inputs["危险性筛选"] = self.hazard_filter_combo.currentText()
            outputs = {
                "分子式": chem.get("formula", ""),
                "分子量": str(chem.get("molecular_weight", "")),
                "危险性类别": chem.get("hazard_class", ""),
                "闪点": str(chem.get("flash_point", "")),
                "沸点": str(chem.get("boiling_point", "")),
                "爆炸极限": chem.get("explosion_limits", "")
            }
        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        """获取项目信息"""
        info = {
            "calculation_type": self.calculation_type,
            "title": "危险化学品查询报告"
        }
        if hasattr(self, 'current_chemical') and self.current_chemical:
            chem = self.current_chemical
            info["chemical_name"] = chem.get("name", "")
            info["cas_number"] = chem.get("cas", "")
        return info

    def generate_report(self):
        """生成报告内容"""
        if not hasattr(self, 'current_chemical') or not self.current_chemical:
            return "请先选择一种化学品进行查询"

        chem = self.current_chemical
        report = f"""
================================================================================
                         危险化学品安全技术说明书
================================================================================

化学品名称: {chem.get('name', '未知')}
CAS号: {chem.get('cas', '未知')}
分子式: {chem.get('formula', '未知')}
分子量: {chem.get('molecular_weight', '未知')}

--------------------------------------------------------------------------------
                              基本信息
--------------------------------------------------------------------------------
外观: {chem.get('appearance', '未知')}
熔点: {chem.get('melting_point', '未知')} °C
沸点: {chem.get('boiling_point', '未知')} °C
密度: {chem.get('density', '未知')} g/cm³
水溶性: {chem.get('water_solubility', '未知')}
闪点: {chem.get('flash_point', '未知')} °C
自燃温度: {chem.get('autoignition_temp', '未知')} °C
爆炸极限: {chem.get('explosion_limits', '未知')}

--------------------------------------------------------------------------------
                              危险性信息
--------------------------------------------------------------------------------
危险性类别: {chem.get('hazard_class', '未知')}
GHS象形图: {chem.get('ghs_symbols', '未知')}

危险性说明:
{chem.get('hazard_statements', '无').replace(';', '\n')}

防范说明:
{chem.get('precautionary_statements', '无').replace(';', '\n')}

--------------------------------------------------------------------------------
                              安全措施
--------------------------------------------------------------------------------
操作处置:
{chem.get('handling', '无')}

储存条件:
{chem.get('storage', '无')}

个人防护:
{chem.get('personal_protection', '无').replace(';', '\n')}

工程控制:
{chem.get('engineering_controls', '无').replace(';', '\n')}

--------------------------------------------------------------------------------
                              应急处理
--------------------------------------------------------------------------------
火灾爆炸措施:
{chem.get('fire_fighting', '无')}

泄漏应急处理:
{chem.get('spill_handling', '无')}

急救措施:
{chem.get('first_aid', '无').replace(';', '\n')}

================================================================================
                              报告生成完成
================================================================================
"""
        return report

    def download_txt_report(self):
        """下载TXT报告"""
        from PySide6.QtWidgets import QFileDialog

        if not hasattr(self, 'current_chemical') or not self.current_chemical:
            QMessageBox.warning(self, "提示", "请先选择一种化学品进行查询")
            return

        chem = self.current_chemical
        default_filename = f"化学品安全技术说明书_{chem.get('name', '未知')}.txt"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存TXT报告",
            default_filename,
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                report = self.generate_report()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                QMessageBox.information(self, "成功", f"报告已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件时出错:\n{str(e)}")

    def generate_pdf_report(self):
        """生成PDF报告"""
        from PySide6.QtWidgets import QFileDialog

        if not hasattr(self, 'current_chemical') or not self.current_chemical:
            QMessageBox.warning(self, "提示", "请先选择一种化学品进行查询")
            return

        chem = self.current_chemical
        default_filename = f"化学品安全技术说明书_{chem.get('name', '未知')}.pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存PDF报告",
            default_filename,
            "PDF Files (*.pdf);;All Files (*)"
        )

        if file_path:
            try:
                from fpdf import FPDF

                pdf = FPDF()
                pdf.add_page()
                pdf.add_font('msyh', '', 'C:/Windows/Fonts/msyh.ttc', uni=True)
                pdf.set_font('msyh', '', 10)

                # 标题
                pdf.set_font('msyh', '', 16)
                pdf.cell(0, 15, f"危险化学品安全技术说明书 - {chem.get('name', '未知')}", ln=True, align='C')
                pdf.ln(10)

                # 基本信息
                pdf.set_font('msyh', '', 12)
                pdf.cell(0, 8, "基本信息", ln=True)
                pdf.set_font('msyh', '', 10)
                pdf.cell(60, 6, f"CAS号: {chem.get('cas', '未知')}", ln=True)
                pdf.cell(60, 6, f"分子式: {chem.get('formula', '未知')}", ln=True)
                pdf.cell(60, 6, f"分子量: {chem.get('molecular_weight', '未知')}", ln=True)
                pdf.cell(60, 6, f"危险性类别: {chem.get('hazard_class', '未知')}", ln=True)
                pdf.ln(5)

                # 危险性说明
                pdf.set_font('msyh', '', 12)
                pdf.cell(0, 8, "危险性说明", ln=True)
                pdf.set_font('msyh', '', 10)
                hazard_text = chem.get('hazard_statements', '无').replace(';', '\n')
                pdf.multi_cell(0, 6, hazard_text)
                pdf.ln(5)

                # 防范说明
                pdf.set_font('msyh', '', 12)
                pdf.cell(0, 8, "防范说明", ln=True)
                pdf.set_font('msyh', '', 10)
                precaution_text = chem.get('precautionary_statements', '无').replace(';', '\n')
                pdf.multi_cell(0, 6, precaution_text)
                pdf.ln(5)

                # 急救措施
                pdf.set_font('msyh', '', 12)
                pdf.cell(0, 8, "急救措施", ln=True)
                pdf.set_font('msyh', '', 10)
                first_aid_text = chem.get('first_aid', '无').replace(';', '\n')
                pdf.multi_cell(0, 6, first_aid_text)

                pdf.output(file_path)
                QMessageBox.information(self, "成功", f"PDF报告已保存到:\n{file_path}")

            except ImportError:
                QMessageBox.critical(self, "错误", "请先安装fpdf库:\npip install fpdf")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"生成PDF时出错:\n{str(e)}")


if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = HazardousChemicalsQuery()
    widget.resize(1200, 800)
    widget.show()

    sys.exit(app.exec())
