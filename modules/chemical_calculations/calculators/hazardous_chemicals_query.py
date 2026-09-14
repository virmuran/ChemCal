"""
危险化学品查询系统 - Tab式查询计算器
提供化学品搜索、分类浏览、详细信息查看和报告生成功能
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox,
    QScrollArea, QDialog, QGridLayout,
    QTabWidget, QListWidget, QListWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
import datetime

from app_styles import (COMBOBOX_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from utils.docx_utils import ReportExporter

# ═══════════════════════════════════════════════════════════════
#  危险性类别（按 GB 30000 系列 / GHS 的危险性种类命名）
# ═══════════════════════════════════════════════════════════════
# 危险化学品查询的"危险性筛选"下拉框选项【必须由数据库实际出现的类别派生】，
# 不能写死列表——写死会留下永远匹配不到记录的"死"筛选项（曾出现 4 项）。
HAZARD_RANK = [
    "爆炸物", "易燃气体", "氧化性气体", "毒性气体",
    "易燃液体", "易燃固体", "自燃物质", "遇水放出易燃气体的物质",
    "氧化性物质", "有机过氧化物", "毒性物质", "致癌物",
    "腐蚀性物质", "健康危害物质", "环境危害物质",
]
ALL_HAZARDS_LABEL = "所有危险性"

DATA_SOURCE_NOTE = (
    "数据来源：内置参考数据，物性取自常用化学品手册（沸点/熔点/密度/闪点/自燃温度/"
    "爆炸极限）；危险性分类与 GHS 象形图、危险性说明（H 语句）、防范说明（P 语句）"
    "按 GB 30000《化学品分类和标签规范》系列（等同 GHS）整理，用于现场安全操作的"
    "快速查询。正式 SDS / 安全标签编制、危险化学品登记与运输分类，须以供应商 SDS 和"
    "《危险化学品目录》《危险货物品名表》(GB 12268) 的最新版本为准。"
)


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
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
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

        # GHS 分类（类别号，比"危险性类别"更细）
        if self.chemical_data.get('ghs_classification'):
            cls_group = QGroupBox("GHS 危险性分类")
            cls_layout = QVBoxLayout(cls_group)
            for item in self.chemical_data['ghs_classification'].split(';'):
                if item.strip():
                    label = QLabel(f"• {item.strip()}")
                    label.setWordWrap(True)
                    cls_layout.addWidget(label)
            layout.addWidget(cls_group)

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

class HazardousChemicalsQuery(CalculatorBase):
    """危险化学品查询系统 - Tab式查询计算器"""
    calculation_type = "危险化学品查询"

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
        self.setup_wheel_blocker()

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
        left_widget.setStyleSheet("background: transparent;")

        # 搜索类型
        type_layout = QHBoxLayout()
        type_label = QLabel("搜索类型:")
        type_label.setStyleSheet(INPUT_LABEL_STYLE)
        type_layout.addWidget(type_label)

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
        # 默认必须为空：曾遗留调试默认值 "乙醇"，导致模块打开时 7 种化学品只列出 1 种
        self.search_input = QLineEdit("")
        self.search_input.setPlaceholderText("输入化学品名称、CAS号或分子式...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        left_layout.addWidget(self.search_input)

        # 危险性筛选
        hazard_layout = QHBoxLayout()
        hazard_label = QLabel("危险性筛选:")
        hazard_label.setStyleSheet(INPUT_LABEL_STYLE)
        hazard_layout.addWidget(hazard_label)

        self.hazard_filter_combo = QComboBox()
        self.hazard_filter_combo.setStyleSheet(COMBOBOX_STYLE)
        # 选项在 load_chemicals_database() 中按数据库实际危险性类别动态生成，
        # 避免写死列表出现永远匹配不到任何记录的"死"筛选项
        self.hazard_filter_combo.addItem(ALL_HAZARDS_LABEL)
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
        result_group = CalculatorBase.make_group_box("查询结果")
        result_layout = QVBoxLayout(result_group)

        # 结果框统一标准：边框/背景/文字色交给主题系统，仅指定等宽字体
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMinimumHeight(300)
        self.detail_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.detail_text.setStyleSheet(f"""
            QTextEdit {{
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: 13px;
            }}
            {SCROLLBAR_STYLE}
        """)
        self.detail_text.setPlaceholderText("计算结果将在此显示……")
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
        bottom_layout = QHBoxLayout()
        
        # 清空按钮
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setStyleSheet(CLEAR_BTN_STYLE)
        self.clear_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.clear_btn.clicked.connect(self.clear_search)
        
        # 下载TXT按钮
        self.download_docx_btn = QPushButton("下载计算书(DOCX)")
        self.download_docx_btn.setStyleSheet(DOCX_BTN_STYLE)
        self.download_docx_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_docx_btn.clicked.connect(self.download_docx_report)
        self.download_docx_btn.setEnabled(False)
        
        # 下载PDF按钮
        self.download_pdf_btn = QPushButton("下载计算书(PDF)")
        self.download_pdf_btn.setStyleSheet(PDF_BTN_STYLE)
        self.download_pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_pdf_btn.clicked.connect(self.download_pdf_report)
        self.download_pdf_btn.setEnabled(False)
        
        bottom_layout.addWidget(self.clear_btn)
        bottom_layout.addWidget(self.download_docx_btn)
        bottom_layout.addWidget(self.download_pdf_btn)
        right_layout.addLayout(bottom_layout)

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
                "ghs_classification": "易燃液体 类别2;急性毒性-经口 类别3;"
                                      "急性毒性-经皮 类别3;急性毒性-吸入 类别3;"
                                      "特异性靶器官毒性-一次接触 类别1（视神经）",
                "ghs_symbols": "易燃;健康危害;毒性",
                "hazard_statements": "H225 高度易燃液体和蒸气;H301 吞咽会中毒;"
                                     "H311 皮肤接触会中毒;H331 吸入会中毒;"
                                     "H370 会对器官造成损害（视神经、中枢神经系统）",
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
                "ghs_classification": "易燃液体 类别2;严重眼损伤/眼刺激 类别2A",
                "ghs_symbols": "易燃",
                "hazard_statements": "H225 高度易燃液体和蒸气;H319 造成严重眼刺激",
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
                "ghs_classification": "易燃液体 类别2;严重眼损伤/眼刺激 类别2A;"
                                      "特异性靶器官毒性-一次接触 类别3（麻醉作用）",
                "ghs_symbols": "易燃;健康危害",
                "hazard_statements": "H225 高度易燃液体和蒸气;H319 造成严重眼刺激;"
                                     "H336 可能造成困倦或眩晕",
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
                "ghs_classification": "易燃液体 类别2;致癌性 类别1A;生殖细胞致突变性 类别1B;"
                                      "特异性靶器官毒性-反复接触 类别1;"
                                      "皮肤腐蚀/刺激 类别2;严重眼损伤/眼刺激 类别2A",
                "ghs_symbols": "易燃;健康危害;腐蚀性",
                "hazard_statements": "H225 高度易燃液体和蒸气;H304 吞咽并进入呼吸道可能致命;"
                                     "H315 造成皮肤刺激;H319 造成严重眼刺激;"
                                     "H340 可能造成遗传性缺陷;H350 可能致癌;"
                                     "H372 长期或反复接触会对器官造成损害（血液系统）",
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
                # GHS 勘误（2026-09-14）：原标"腐蚀性物质;毒性物质"。硫酸按 GB 30000.2/.19/
                # .28 应分类为【皮肤腐蚀/刺激 类别1A】【严重眼损伤/眼刺激 类别1】，
                # 急性经口 LD50(大鼠) 约 2140 mg/kg 仅属急性毒性类别5，中国不采用类别5，
                # 因此【不标"毒性物质"】，原标注属夸大。
                "hazard_class": "腐蚀性物质",
                "ghs_classification": "皮肤腐蚀/刺激 类别1A;严重眼损伤/眼刺激 类别1",
                "ghs_symbols": "腐蚀性",
                "hazard_statements": "H314 造成严重皮肤灼伤和眼损伤;H290 可能腐蚀金属",
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
                "ghs_classification": "皮肤腐蚀/刺激 类别1A;严重眼损伤/眼刺激 类别1",
                "ghs_symbols": "腐蚀性",
                "hazard_statements": "H314 造成严重皮肤灼伤和眼损伤;H290 可能腐蚀金属",
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
                "hazard_class": "毒性气体;氧化性气体;腐蚀性物质;环境危害物质",
                "ghs_classification": "氧化性气体 类别1;加压气体（液化气体）;"
                                      "急性毒性-吸入 类别2;皮肤腐蚀/刺激 类别2;"
                                      "严重眼损伤/眼刺激 类别2;"
                                      "特异性靶器官毒性-一次接触 类别3（呼吸道刺激）;"
                                      "危害水生环境-急性 类别1",
                "ghs_symbols": "氧化性;毒性;腐蚀性;环境危害",
                "hazard_statements": "H270 可能导致或加剧燃烧（氧化剂）;"
                                     "H330 吸入致命;H315 造成皮肤刺激;"
                                     "H319 造成严重眼刺激;H335 可能引起呼吸道刺激;"
                                     "H400 对水生生物毒性极大",
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
        self._rebuild_hazard_filters()
        self.filter_chemicals()

    def _rebuild_hazard_filters(self):
        """按数据库实际出现的危险性类别重建筛选下拉选项

        修复：原下拉框选项为写死列表，其中"易燃气体/易燃固体/爆炸性物质/
        健康危害物质"在数据库中没有任何记录能匹配，属永远查不到结果的死选项；
        "氧化性物质"与实际使用的"氧化性气体"也不一致。改为完全由数据派生。
        """
        present = set()
        for chem in self.chemicals_data:
            for token in str(chem.get("hazard_class", "")).split(";"):
                token = token.strip()
                if token:
                    present.add(token)

        # 按 HAZARD_RANK 排序，未列入排序表的新类别追加在末尾（不遗漏）
        ordered = [h for h in HAZARD_RANK if h in present]
        ordered += sorted(present - set(HAZARD_RANK))

        keep = self.hazard_filter_combo.currentText()
        self.hazard_filter_combo.blockSignals(True)
        self.hazard_filter_combo.clear()
        self.hazard_filter_combo.addItem(ALL_HAZARDS_LABEL)
        self.hazard_filter_combo.addItems(ordered)
        idx = self.hazard_filter_combo.findText(keep)
        self.hazard_filter_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.hazard_filter_combo.blockSignals(False)

    def on_search_text_changed(self, text):
        """处理搜索文本变化（延迟 300ms 触发，避免每次按键都全量过滤）"""
        # 定时器只创建一次：原实现每次输入都新建 QTimer 并覆盖 self.search_timer，
        # 旧对象失去引用被 GC（在运行的 QTimer 被回收属隐患）
        if getattr(self, 'search_timer', None) is None:
            self.search_timer = QTimer(self)
            self.search_timer.setSingleShot(True)
            self.search_timer.timeout.connect(self.filter_chemicals)

        self.search_timer.stop()
        self.search_timer.start(300)

    def filter_chemicals(self):
        """过滤化学品列表"""
        search_text = self.search_input.text().strip().lower()
        hazard_filter = self.hazard_filter_combo.currentText()
        search_type = self.search_type_combo.currentText()

        self.filtered_chemicals = []

        for chemical in self.chemicals_data:
            # 危险性筛选
            if hazard_filter != ALL_HAZARDS_LABEL and hazard_filter not in chemical.get('hazard_class', ''):
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

    def _hazard_style(self, hazard_class):
        """按危险性返回 (底色, 字色, 前缀标记)

        底色为浅色系且【字色必须显式给深色】——否则深色主题下 QListWidget 会用
        白色系统文字，落在这几个浅底色上几乎不可读（原代码只 setBackground）。
        """
        if "易燃" in hazard_class and "毒性" in hazard_class:
            return QColor(255, 200, 200), QColor(31, 41, 51), "🔥☠"
        if "易燃" in hazard_class:
            return QColor(255, 230, 200), QColor(31, 41, 51), "🔥"
        if "毒性" in hazard_class or "致癌" in hazard_class:
            return QColor(228, 200, 255), QColor(31, 41, 51), "☠"
        if "腐蚀性" in hazard_class:
            return QColor(200, 230, 255), QColor(31, 41, 51), "⚠"
        if "氧化性" in hazard_class:
            return QColor(255, 245, 190), QColor(31, 41, 51), "⭕"
        return None, None, ""

    def update_chemicals_list(self):
        """更新化学品列表"""
        self.chemicals_list.clear()

        for chemical in self.filtered_chemicals:
            hazard_class = chemical.get('hazard_class', '')

            # 列表项文本同时给出危险性，避免必须悬停才能看到分类
            item = QListWidgetItem(f"{chemical['name']}    [{hazard_class}]")
            # 化学品数据挂在 UserRole 上，按名字反查在重名/文本改动时会失效
            item.setData(Qt.UserRole, chemical)

            bg, fg, mark = self._hazard_style(hazard_class)
            if bg is not None:
                item.setBackground(bg)
                item.setForeground(fg)

            # 设置提示信息
            tooltip = f"{mark} {chemical['name']}\n"
            tooltip += f"CAS: {chemical.get('cas', '未知')}\n"
            tooltip += f"分子式: {chemical.get('formula', '未知')}\n"
            tooltip += f"危险性: {hazard_class}"
            item.setToolTip(tooltip)

            self.chemicals_list.addItem(item)

        # 更新统计信息
        self.stats_label.setText(f"找到 {len(self.filtered_chemicals)} 种化学品")

    def show_chemical_detail(self, item):
        """显示化学品详情"""
        chemical = item.data(Qt.UserRole)
        if chemical is None:      # 兜底：按名称反查
            chemical = next((c for c in self.filtered_chemicals
                             if c['name'] == item.text()), None)

        if chemical:
            self.current_chemical = chemical
            self.detail_btn.setEnabled(True)
            self.download_docx_btn.setEnabled(True)
            self.download_pdf_btn.setEnabled(True)
            self.update_detail_display(chemical)

    def _format_detail_text(self, chemical):
        """把化学品数据格式化为纯文本详情

        修复：原实现用 setHtml 拼硬编码浅色表格（#f8f9fa 底 + #ddd 边框 +
        #2c3e50 标题），深色主题下白字压浅底完全不可读；现改为纯文本，
        由主题系统统一接管文字色，与其余计算器的结果框一致。
        """
        def bullet(field, indent="  "):
            raw = str(chemical.get(field, "") or "").strip()
            if not raw or raw == "无":
                return f"{indent}无\n"
            parts = [p.strip() for p in raw.split(";") if p.strip()]
            return "".join(f"{indent}• {p}\n" for p in parts)

        def val(field, unit=""):
            v = chemical.get(field, None)
            if v is None or v == "":
                return "未知"
            # "无"/非数值时不再拼单位，避免出现"无 °C"这种读不通的写法
            if isinstance(v, (int, float)):
                return f"{v}{unit}"
            return str(v)

        out = f"=== {chemical.get('name', '未知')} ===\n"
        out += f"  CAS号   : {val('cas')}\n"
        out += f"  分子式  : {val('formula')}\n"
        out += f"  分子量  : {val('molecular_weight')}\n"
        out += f"  外观    : {val('appearance')}\n"
        out += f"  熔点    : {val('melting_point', ' °C')}\n"
        out += f"  沸点    : {val('boiling_point', ' °C')}\n"
        out += f"  密度    : {val('density', ' g/cm³')}\n"
        out += f"  水溶性  : {val('water_solubility')}\n"
        out += f"  闪点    : {val('flash_point', ' °C')}\n"
        out += f"  自燃温度: {val('autoignition_temp', ' °C')}\n"
        out += f"  爆炸极限: {val('explosion_limits')}\n\n"

        out += "── 危险性 ──\n"
        out += f"  危险性类别: {val('hazard_class')}\n"
        if chemical.get("ghs_classification"):
            out += f"  GHS 分类  : {chemical['ghs_classification']}\n"
        out += f"  GHS 象形图: {val('ghs_symbols')}\n\n"

        out += "  危险性说明（H 语句）:\n"
        out += bullet("hazard_statements")
        out += "\n  防范说明（P 语句）:\n"
        out += bullet("precautionary_statements")
        out += "\n── 安全措施 ──\n"
        out += "  操作处置:\n"
        out += f"    {chemical.get('handling', '无')}\n"
        out += "  储存条件:\n"
        out += f"    {chemical.get('storage', '无')}\n"
        out += "  个人防护:\n"
        out += bullet("personal_protection", "    ")
        out += "  工程控制:\n"
        out += bullet("engineering_controls", "    ")
        out += "\n── 数据来源 ──\n"
        out += f"  {DATA_SOURCE_NOTE}\n"
        out += "\n  提示：双击列表项或点「查看完整详情」查看火灾/泄漏/急救等应急措施。\n"

        return out

    def update_detail_display(self, chemical):
        """更新详情显示（纯文本，文字色交由主题系统）"""
        self.detail_text.setPlainText(self._format_detail_text(chemical))

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
        self.download_docx_btn.setEnabled(False)
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
                "GHS分类": chem.get("ghs_classification", ""),
                "闪点": str(chem.get("flash_point", "")),
                "沸点": str(chem.get("boiling_point", "")),
                "爆炸极限": chem.get("explosion_limits", "")
            }
        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        """获取项目信息（报告生成用，返回标准工程信息 dict）"""
        saved = {}
        try:
            if self.data_manager:
                saved = self.data_manager.get_project_info() or {}
        except Exception:
            saved = {}
        return {
            "company_name": saved.get("company_name", ""),
            "project_number": saved.get("project_number", ""),
            "project_name": saved.get("project_name", "危险化学品查询"),
            "subproject_name": saved.get("subproject_name", ""),
            "calculation_type": self.calculation_type,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def generate_report(self):
        """生成报告内容（返回 str；未选择化学品时返回 None，不生成空文件）"""
        if not hasattr(self, 'current_chemical') or not self.current_chemical:
            return None

        chem = self.current_chemical
        project = self.get_project_info()
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
GHS分类: {chem.get('ghs_classification', '未标注')}
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

--------------------------------------------------------------------------------
                              工程信息
--------------------------------------------------------------------------------
公司名称: {project['company_name'] or '—'}
项目名称: {project['project_name'] or '—'}
项目编号: {project['project_number'] or '—'}
子项名称: {project['subproject_name'] or '—'}
查询时间: {project['timestamp']}

--------------------------------------------------------------------------------
                              数据来源
--------------------------------------------------------------------------------
{DATA_SOURCE_NOTE}

================================================================================
                    本报告由 ChemCal 工程计算模块生成
================================================================================
"""
        return report

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "危险化学品查询")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "危险化学品查询")
if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = HazardousChemicalsQuery()
    widget.resize(1200, 800)
    widget.show()

    sys.exit(app.exec())
