from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
                              QLabel, QLineEdit, QComboBox, QPushButton,
                              QTextEdit, QTableWidget, QTableWidgetItem,
                              QHeaderView, QMessageBox, QTabWidget,
                              QScrollArea, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
import datetime

from app_styles import (COMBOBOX_STYLE, SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from utils.docx_utils import ReportExporter

# ═══════════════════════════════════════════════════════════════
#  腐蚀速率分级
# ═══════════════════════════════════════════════════════════════
# 主分级 —— 左景伊《腐蚀数据与选材手册》（化工设备选材的主要依据，4 级制）：
#     1级 优良      < 0.05 mm/a
#     2级 良好      0.05 ~ 0.5
#     3级 可用（腐蚀较重）  0.5 ~ 1.5
#     4级 不适用（腐蚀严重）> 1.5
#
# 参考细分级 —— 中国腐蚀与防护学会《金属防腐蚀手册》（10 级制，源自前苏联体系，
#     现已少用，此处仅作细分参考）。
#
# ⚠ 注意：GB/T 10123 是【术语】标准，只定义腐蚀的基本术语，**并不规定耐蚀性分级区间**。
#   原实现在分级表后面紧跟着列 GB/T 10123 / ASTM G31 / NACE MR0175，容易被读成
#   "分级区间出自这些标准"，属出处误导，现已分列更正。
CORROSION_GRADES_ZUO = [          # (速率上限 mm/a, 等级, 选材建议)
    (0.05, "优良", "完全耐蚀，可用于关键设备与薄壁件"),
    (0.50, "良好", "耐蚀，一般可用于连续操作设备"),
    (1.50, "可用（腐蚀较重）", "尚可用，须计入腐蚀裕量并加强定期检测"),
    (float("inf"), "不适用（腐蚀严重）", "不推荐使用，应改用其他材料"),
]

CORROSION_GRADES_10 = [           # (速率上限 mm/a, 细分级)
    (0.001, "1级 完全耐蚀"), (0.005, "2级 很耐蚀"), (0.010, "3级 很耐蚀"),
    (0.050, "4级 耐腐"), (0.100, "5级 耐蚀"), (0.500, "6级 尚耐腐"),
    (1.000, "7级 尚耐腐"), (5.000, "8级 欠耐腐"), (10.00, "9级 欠耐腐"),
    (float("inf"), "10级 不耐腐"),
]


def classify_corrosion_rate(rate):
    """按腐蚀速率返回 (等级, 选材建议, 细分级)。

    等级由速率唯一派生 —— 原实现把 rate 与 rating 分别手写在数据表里，
    出现同一速率对应两个等级（0.05 既标"良好"又标"可用"）、以及 0.02 标"良好"、
    1.2 标"差"（按自身分级表应属"很差"）等自相矛盾，故改为单一数据源派生。
    """
    try:
        rate = float(rate)
    except (TypeError, ValueError):
        return "未知", "速率数据无效", "—"
    if rate < 0:
        return "未知", "速率数据无效", "—"
    grade = desc = CORROSION_GRADES_ZUO[-1][1], CORROSION_GRADES_ZUO[-1][2]
    for limit, g, d in CORROSION_GRADES_ZUO:
        if rate < limit:
            grade, desc = g, d
            break
    grade10 = CORROSION_GRADES_10[-1][1]
    for limit, g10 in CORROSION_GRADES_10:
        if rate < limit:
            grade10 = g10
            break
    return grade, desc, grade10


# ═══════════════════════════════════════════════════════════════
#  腐蚀数据（内置参考数据，非实测值）
# ═══════════════════════════════════════════════════════════════
# 每条数据的 rate 均为【指定参考工况】下的均匀腐蚀速率，必须连同 t_ref / conc_ref
# 一起使用；工况偏离时结果不可直接外推（查询界面会给出提示）。
# 数据整理自常用腐蚀数据手册（左景伊《腐蚀数据与选材手册》、《化工设备设计全书》
# 材料耐腐蚀章节）的量级参考，用于初步选材筛选；工程设计前应查具体工况的腐蚀曲线
# 或做挂片试验。
CORROSION_DB = {
    # ── 碳钢 ──
    "Q235-盐酸": {
        "rate": 12.5, "t_ref": 25, "conc_ref": 10,
        "notes": "碳钢在盐酸中迅速腐蚀，禁止使用；应选 PVC/PP/PTFE 或哈氏合金 C276"},
    "Q235-硫酸": {
        "rate": 1.2, "t_ref": 25, "conc_ref": 10,
        "notes": "稀硫酸中腐蚀严重；仅浓度>70% 的低温硫酸能使碳钢钝化，方可有限使用"},
    "Q235-氢氧化钠": {
        "rate": 0.02, "t_ref": 25, "conc_ref": 10,
        "notes": "常温稀碱中耐蚀良好；浓碱高温下须防碱脆（应力腐蚀），焊后应消除应力"},
    "Q235-海水": {
        "rate": 0.15, "t_ref": 25, "conc_ref": None,
        "notes": "须配合涂层或阴极保护；流速高时冲刷腐蚀明显加剧"},

    # ── 不锈钢 ──
    "304-盐酸": {
        "rate": 2.5, "t_ref": 25, "conc_ref": 10,
        "notes": "氯离子破坏钝化膜并引发点蚀，不推荐使用"},
    "304-硫酸": {
        "rate": 0.08, "t_ref": 25, "conc_ref": 10,
        "notes": "仅低浓度常温可用；浓度或温度升高时腐蚀率迅速上升"},
    "304-硝酸": {
        "rate": 0.01, "t_ref": 25, "conc_ref": 10,
        "notes": "耐硝酸性能优良（氧化性酸有利于钝化）"},
    "304-海水": {
        "rate": 0.05, "t_ref": 25, "conc_ref": None,
        "notes": "存在点蚀与缝隙腐蚀风险，静止海水中尤甚；建议改用 316L/2205"},
    "316-盐酸": {
        "rate": 1.8, "t_ref": 25, "conc_ref": 10,
        "notes": "钼提高耐点蚀能力但抵抗不住盐酸，不推荐使用"},
    "316-硫酸": {
        "rate": 0.05, "t_ref": 25, "conc_ref": 10,
        "notes": "耐蚀性优于 304，可用于低浓度硫酸"},
    "316-海水": {
        "rate": 0.02, "t_ref": 25, "conc_ref": None,
        "notes": "耐海水性能较好，但缝隙处仍有局部腐蚀风险"},

    # ── 钛 ──
    "纯钛-盐酸": {
        # ⚠ 勘误（2026-09-14）：原填 rate=0.001 / "优秀" / "优良的耐盐酸性能"，是
        #   材料学错误。盐酸为【还原性酸】，会溶解钛的钝化膜：
        #   《化工设备设计全书》—— 常温 <3% 不反应，>5% 时"耐腐蚀性不好"，
        #   60°C/5% 约 2.5 mm/a；常温 10% 腐蚀率已达 1 mm/a 量级。
        #   钛的真正优势介质是氧化性酸（硝酸）与含氯溶液（海水/次氯酸盐）。
        "rate": 1.0, "t_ref": 25, "conc_ref": 10,
        "notes": "盐酸为还原性酸，破坏钛钝化膜：常温 10% 已达约 1 mm/a。"
                 "钛仅适用于常温 ≤3% 稀盐酸（60°C 以下）；需耐盐酸请选 "
                 "Ti-0.2Pd、Ti-32Mo 或哈氏合金 C276"},
    "纯钛-海水": {
        "rate": 0.0001, "t_ref": 25, "conc_ref": None,
        "notes": "极佳的耐海水性能，无点蚀、缝隙腐蚀与氯离子应力腐蚀"},
    "纯钛-硝酸": {
        "rate": 0.001, "t_ref": 25, "conc_ref": 10,
        "notes": "优良的耐硝酸性能（氧化性酸使钝化膜稳定）"},

    # ── 镍基合金 ──
    "哈氏合金C276-盐酸": {
        "rate": 0.05, "t_ref": 25, "conc_ref": 10,
        "notes": "少数能耐盐酸的金属材料，较高温度与浓度下仍可用"},
    "哈氏合金C276-硫酸": {
        "rate": 0.02, "t_ref": 25, "conc_ref": 10,
        "notes": "优良的耐硫酸性能，宽浓度温度范围适用"},

    # ── 塑料 ──
    "PVC-盐酸": {
        "rate": 0.001, "t_ref": 25, "conc_ref": 10,
        "notes": "优良的耐盐酸性能（非金属，无电化学腐蚀）；适用温度约 <60°C"},
    "PVC-硫酸": {
        "rate": 0.001, "t_ref": 25, "conc_ref": 10,
        "notes": "优良的耐硫酸性能；适用温度约 <60°C"},
    "PTFE-盐酸": {
        "rate": 0.0001, "t_ref": 25, "conc_ref": 10,
        "notes": "几乎不腐蚀；适用温度上限约 260°C"},
}

DATA_SOURCE_NOTE = (
    "数据来源：内置参考数据（非实测），整理自左景伊《腐蚀数据与选材手册》、"
    "《化工设备设计全书》材料耐腐蚀章节的量级值，用于初步选材筛选。"
    "分级依据：左景伊《腐蚀数据与选材手册》4 级制（优良<0.05 / 良好0.05~0.5 / "
    "可用0.5~1.5 / 不适用>1.5 mm/a）；速率恰落在分界值上时归入腐蚀更重的一级"
    "（偏安全取值，故 0.05 判为「良好」、1.5 判为「不适用」）。"
    "工程设计前请查具体工况腐蚀曲线或做挂片试验。"
)

class CorrosionDataQuery(CalculatorBase):
    """腐蚀数据查询计算器"""

    # 计算类型标识
    calculation_type = "腐蚀数据查询"

    def __init__(self, parent=None, data_manager=None):
        """构造函数

        Args:
            parent: 父窗口
            data_manager: 数据管理器（可选）
        """
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_results = {}
        self.corrosion_data = self.load_corrosion_data()
        self.setup_ui()

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
        """构建统一风格的UI布局"""
        # 外层主布局：水平布局，间距15，边距10
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ========= 左侧输入区（QScrollArea包裹） =========
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } "
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        # 左侧内部容器
        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 顶部说明文字
        desc_label = QLabel("查询工程材料和腐蚀介质的组合腐蚀数据，提供腐蚀速率、耐蚀评级和使用建议。支持多种材料和介质的腐蚀性能查询。")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc_label)

        # 查询条件组 — QGridLayout 三列 stretch(4,8,5)
        query_group = CalculatorBase.make_group_box("查询条件")
        query_grid = QGridLayout(query_group)
        query_grid.setSpacing(12)
        query_grid.setHorizontalSpacing(10)
        query_grid.setColumnStretch(0, 4)
        query_grid.setColumnStretch(1, 8)
        query_grid.setColumnStretch(2, 5)

        hint_style = "font-style: italic;"

        def make_lbl(text, row, col):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet(INPUT_LABEL_STYLE)
            query_grid.addWidget(lbl, row, col)
            return lbl

        # 行0：材料类别
        make_lbl("材料类别:", 0, 0)
        self.material_category_combo = QComboBox()
        self.material_category_combo.setStyleSheet(COMBOBOX_STYLE)
        self.material_category_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.material_category_combo.addItems([
            "碳钢", "不锈钢", "合金钢", "铜及铜合金", "铝及铝合金",
            "钛及钛合金", "镍基合金", "塑料", "橡胶", "陶瓷"
        ])
        self.material_category_combo.currentTextChanged.connect(self.on_material_category_changed)
        query_grid.addWidget(self.material_category_combo, 0, 1)
        hint_0 = QLabel("选择材料大类")
        hint_0.setStyleSheet(hint_style)
        query_grid.addWidget(hint_0, 0, 2)

        # 行1：具体材料
        make_lbl("具体材料:", 1, 0)
        self.material_combo = QComboBox()
        self.material_combo.setStyleSheet(COMBOBOX_STYLE)
        self.material_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_grid.addWidget(self.material_combo, 1, 1)
        hint_1 = QLabel("选择具体材料")
        hint_1.setStyleSheet(hint_style)
        query_grid.addWidget(hint_1, 1, 2)

        # 行2：介质类别
        make_lbl("介质类别:", 2, 0)
        self.medium_category_combo = QComboBox()
        self.medium_category_combo.setStyleSheet(COMBOBOX_STYLE)
        self.medium_category_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.medium_category_combo.addItems([
            "酸类", "碱类", "盐类", "有机溶剂", "气体", "水及水溶液"
        ])
        self.medium_category_combo.currentTextChanged.connect(self.on_medium_category_changed)
        query_grid.addWidget(self.medium_category_combo, 2, 1)
        hint_2 = QLabel("选择介质大类")
        hint_2.setStyleSheet(hint_style)
        query_grid.addWidget(hint_2, 2, 2)

        # 行3：具体介质
        make_lbl("具体介质:", 3, 0)
        self.medium_combo = QComboBox()
        self.medium_combo.setStyleSheet(COMBOBOX_STYLE)
        self.medium_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_grid.addWidget(self.medium_combo, 3, 1)
        hint_3 = QLabel("选择具体介质")
        hint_3.setStyleSheet(hint_style)
        query_grid.addWidget(hint_3, 3, 2)

        # 行4：温度
        make_lbl("温度 (°C):", 4, 0)
        self.temperature_input = QLineEdit("25")
        self.temperature_input.setValidator(QDoubleValidator(-50, 500, 1))
        self.temperature_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_grid.addWidget(self.temperature_input, 4, 1)
        hint_4 = QLabel("操作温度条件")
        hint_4.setStyleSheet(hint_style)
        query_grid.addWidget(hint_4, 4, 2)

        # 行5：浓度
        make_lbl("浓度 (%):", 5, 0)
        self.concentration_input = QLineEdit("10")
        self.concentration_input.setValidator(QDoubleValidator(0, 100, 1))
        self.concentration_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_grid.addWidget(self.concentration_input, 5, 1)
        hint_5 = QLabel("介质浓度")
        hint_5.setStyleSheet(hint_style)
        query_grid.addWidget(hint_5, 5, 2)

        # 行6：pH值（可选，留空时不做酸碱一致性校验）
        make_lbl("pH值:", 6, 0)
        self.ph_input = QLineEdit("")
        self.ph_input.setValidator(QDoubleValidator(0, 14, 1))
        self.ph_input.setPlaceholderText("可选，留空不校验")
        self.ph_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        query_grid.addWidget(self.ph_input, 6, 1)
        hint_6 = QLabel("可选 (0-14)")
        hint_6.setStyleSheet(hint_style)
        query_grid.addWidget(hint_6, 6, 2)

        left_layout.addWidget(query_group)

        # 搜索功能
        search_group = CalculatorBase.make_group_box("快速搜索")
        search_layout = QHBoxLayout(search_group)

        search_label = QLabel("搜索关键词:")
        search_label.setStyleSheet("font-weight: bold;")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit("")   # 原遗留调试默认值 "碳钢"，清掉
        self.search_input.setPlaceholderText("输入材料或介质名称进行搜索...")
        self.search_input.returnPressed.connect(self.on_search)
        search_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self.on_search)
        self.search_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #27ae60; "
            "color: white; "
            "font-weight: bold; "
            "padding: 8px 16px; "
            "border: none; "
            "border-radius: 8px; "
            "}"
            "QPushButton:hover:!checked { background-color: #219955; }"
        )
        search_layout.addWidget(self.search_btn)
        left_layout.addWidget(search_group)

        # 标签页组件（材料库、腐蚀类型）——样式交给主题系统
        self.tab_widget = QTabWidget()

        # 添加材料库标签页
        self.material_tab = self.create_material_tab()
        self.tab_widget.addTab(self.material_tab, "材料库")

        # 添加腐蚀类型标签页
        self.corrosion_types_tab = self.create_corrosion_types_tab()
        self.tab_widget.addTab(self.corrosion_types_tab, "腐蚀类型")

        left_layout.addWidget(self.tab_widget)

        # 弹性空间填充底部
        left_layout.addStretch()

        left_scroll.setWidget(left_widget)

        # ========= 右侧结果区 =========
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        result_group = CalculatorBase.make_group_box("查询结果")
        result_vbox = QVBoxLayout(result_group)

        # 结果框统一标准：边框/背景/文字色交给主题系统，仅指定等宽字体
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: 13px;
            } """)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        result_vbox.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # 底部按钮行（右侧）：清空（灰）→ 下载DOCX（蓝）→ 下载PDF（红）→ 查询按钮
        bottom_layout = QHBoxLayout()

        # 清空按钮
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setStyleSheet(CLEAR_BTN_STYLE)
        self.clear_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.clear_btn.clicked.connect(self.clear_inputs)

        # 下载DOCX按钮
        self.download_docx_btn = QPushButton("下载计算书(DOCX)")
        self.download_docx_btn.setStyleSheet(DOCX_BTN_STYLE)
        self.download_docx_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_docx_btn.clicked.connect(self.download_docx_report)

        # 下载PDF按钮
        self.download_pdf_btn = QPushButton("下载计算书(PDF)")
        self.download_pdf_btn.setStyleSheet(PDF_BTN_STYLE)
        self.download_pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.download_pdf_btn.clicked.connect(self.download_pdf_report)

        bottom_layout.addWidget(self.clear_btn)
        bottom_layout.addWidget(self.download_docx_btn)
        bottom_layout.addWidget(self.download_pdf_btn)
        right_layout.addLayout(bottom_layout)

        # 查询按钮（绿色，置底）
        self.query_btn = self.make_calc_button("查 询")
        self.query_btn.clicked.connect(self.calculate)
        right_layout.addWidget(self.query_btn)

        # ========= 按比例添加到主布局 =========
        main_layout.addWidget(left_scroll, 2)   # 左侧占2份
        main_layout.addWidget(right_widget, 1)  # 右侧占1份

        # 初始化下拉框选项
        self.on_material_category_changed(self.material_category_combo.currentText())
        self.on_medium_category_changed(self.medium_category_combo.currentText())

    def calculate(self):
        """执行计算 - 查询腐蚀数据"""
        try:
            # 获取查询条件
            material = self.material_combo.currentText()
            medium = self.medium_combo.currentText()
            try:
                temperature = float(self.temperature_input.text())
            except ValueError:
                temperature = 25.0
            try:
                concentration = float(self.concentration_input.text())
            except ValueError:
                concentration = 10.0
            try:
                ph = float(self.ph_input.text())
            except ValueError:
                ph = None      # 留空 = 不校验酸碱一致性

            # 构建查询键
            query_key = f"{material}-{medium}"

            # 精确匹配查询
            if query_key in self.corrosion_data:
                data = self.corrosion_data[query_key]
                self.display_results(data, material, medium, temperature,
                                     concentration, ph)
            else:
                # 无精确匹配时尝试模糊查询
                self.fuzzy_query(material, medium, temperature, concentration)

        except Exception as e:
            QMessageBox.warning(self, "查询错误", f"查询过程中发生错误: {str(e)}")

    def on_material_category_changed(self, category):
        """材料类别改变时更新具体材料下拉框"""
        materials = {
            "碳钢": ["Q235", "Q345", "20#钢", "45#钢", "A36", "A53"],
            "不锈钢": ["304", "304L", "316", "316L", "321", "310S", "2205", "2507"],
            "合金钢": ["15CrMo", "12Cr1MoV", "P91", "P92", "4130", "4140"],
            "铜及铜合金": ["纯铜", "黄铜", "青铜", "白铜", "铜镍合金"],
            "铝及铝合金": ["1060", "3003", "5052", "6061", "7075"],
            "钛及钛合金": ["纯钛", "Ti-6Al-4V", "Ti-0.2Pd"],
            "镍基合金": ["Inconel 600", "Inconel 625", "Hastelloy C276", "Monel 400"],
            "塑料": ["PVC", "PP", "PE", "PTFE", "PVDF"],
            "橡胶": ["NBR", "EPDM", "FKM", "CR", "SBR"],
            "陶瓷": ["氧化铝", "碳化硅", "氧化锆", "氮化硅"]
        }

        self.material_combo.clear()
        if category in materials:
            self.material_combo.addItems(materials[category])

    def on_medium_category_changed(self, category):
        """介质类别改变时更新具体介质下拉框"""
        mediums = {
            "酸类": ["盐酸", "硫酸", "硝酸", "磷酸", "醋酸", "氢氟酸", "柠檬酸"],
            "碱类": ["氢氧化钠", "氢氧化钾", "氨水", "碳酸钠", "石灰水"],
            "盐类": ["氯化钠", "氯化钾", "硫酸钠", "碳酸氢钠", "氯化钙", "硫酸铜"],
            "有机溶剂": ["甲醇", "乙醇", "丙酮", "苯", "甲苯", "二甲苯", "氯仿"],
            "气体": ["氧气", "氯气", "硫化氢", "二氧化碳", "氨气", "二氧化硫"],
            "水及水溶液": ["纯水", "自来水", "海水", "河水", "冷却水", "锅炉水"]
        }

        self.medium_combo.clear()
        if category in mediums:
            self.medium_combo.addItems(mediums[category])

    def create_material_tab(self):
        """创建材料库标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # 材料库说明
        info_group = QGroupBox("常用工程材料耐腐蚀性能参考")
        info_layout = QVBoxLayout(info_group)

        # 材料参数表
        material_table = QTableWidget()
        material_table.setColumnCount(6)
        material_table.setHorizontalHeaderLabels(["材料", "主要成分", "适用温度(°C)", "主要耐腐蚀介质", "不耐腐蚀介质", "应用领域"])

        material_data = [
            ["304不锈钢", "Cr18Ni9", "-196~600", "硝酸、有机酸、碱", "盐酸、氯化物（点蚀）", "化工、食品、医药"],
            ["316不锈钢", "Cr17Ni12Mo2", "-196~700", "硫酸、磷酸、有机酸", "盐酸、氢氟酸", "化工、海洋、医药"],
            ["碳钢Q235", "Fe-C", "-20~400", "碱、大气、水", "酸、氧化性介质", "建筑、结构、管道"],
            ["哈氏合金C276", "Ni-Mo-Cr", "-196~675", "盐酸、硫酸、氯化物", "强氧化性酸、>675°C", "化工、环保、海洋"],
            ["钛TA2", "Ti", "-270~300", "氯化物、海水、硝酸（氧化性）", "盐酸、硫酸等还原性酸、氢氟酸", "化工、海洋、航空"],
            ["聚四氟乙烯", "C2F4", "-200~260", "几乎所有化学品", "熔融碱金属", "化工、电子、医疗"],
            ["聚丙烯", "C3H6", "0~100", "酸、碱、盐溶液", "氧化性酸、溶剂", "化工、水处理"],
            ["丁腈橡胶", "NBR", "-30~120", "油类、脂肪烃", "酮、酯、臭氧", "密封、油管"]
        ]
        # 「适用温度」为连续使用参考上限（受氧化、强度与组织稳定性共同限制），
        # 非绝对熔点；超出时须逐案核算。

        material_table.setRowCount(len(material_data))
        for i, row_data in enumerate(material_data):
            for j, data in enumerate(row_data):
                item = QTableWidgetItem(data)
                item.setTextAlignment(Qt.AlignCenter)
                material_table.setItem(i, j, item)

        # 表格列宽 Stretch 铺满
        header = material_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        material_table.verticalHeader().setVisible(False)

        info_layout.addWidget(material_table)
        layout.addWidget(info_group)

        return tab

    def create_corrosion_types_tab(self):
        """创建腐蚀类型标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        corrosion_group = QGroupBox("常见腐蚀类型知识")
        group_layout = QVBoxLayout(corrosion_group)

        corrosion_text = QTextEdit()
        corrosion_text.setReadOnly(True)
        corrosion_text.setPlainText(self.get_corrosion_types_text())
        group_layout.addWidget(corrosion_text)
        layout.addWidget(corrosion_group)

        return tab

    def get_corrosion_types_text(self):
        """获取腐蚀类型的文本内容"""
        text = "常见腐蚀类型\n\n"
        text += "1. 均匀腐蚀\n"
        text += "   特征：整个金属表面均匀减薄\n"
        text += "   原因：化学或电化学反应在整个表面均匀发生\n"
        text += "   防护：选用耐腐蚀材料、涂层、缓蚀剂\n\n"

        text += "2. 点蚀\n"
        text += "   特征：局部区域形成小孔或凹坑\n"
        text += "   原因：局部破坏钝化膜，形成腐蚀电池\n"
        text += "   易发材料：不锈钢、铝、钛在含氯离子环境中\n\n"

        text += "3. 缝隙腐蚀\n"
        text += "   特征：在缝隙或遮蔽区域发生\n"
        text += "   原因：缝隙内外氧浓度差异形成浓差电池\n"
        text += "   防护：避免缝隙设计、使用密封剂\n\n"

        text += "4. 电偶腐蚀\n"
        text += "   特征：两种不同金属接触处的腐蚀\n"
        text += "   原因：电位差驱动电子流动\n"
        text += "   防护：避免异种金属接触、使用绝缘材料\n\n"

        text += "5. 应力腐蚀开裂\n"
        text += "   特征：在拉应力和特定介质共同作用下开裂\n"
        text += "   原因：应力加速局部腐蚀\n"
        text += "   典型组合：奥氏体不锈钢-氯离子、碳钢-硝酸盐\n\n"

        text += "6. 晶间腐蚀\n"
        text += "   特征：沿晶界选择性腐蚀\n"
        text += "   原因：晶界区与晶内成分差异\n"
        text += "   典型材料：不锈钢敏化态、铝合金\n\n"

        text += "7. 腐蚀疲劳\n"
        text += "   特征：交变应力与腐蚀介质共同作用\n"
        text += "   原因：腐蚀降低材料疲劳强度\n"
        text += "   防护：降低应力集中、表面处理\n\n"

        text += "8. 冲刷腐蚀\n"
        text += "   特征：流体冲刷加速腐蚀\n"
        text += "   原因：机械磨损与化学腐蚀协同作用\n"
        text += "   防护：降低流速、选用耐磨材料\n\n"

        text += "腐蚀速率等级（主分级）\n"
        text += "   依据：左景伊《腐蚀数据与选材手册》——化工设备选材的主要依据，4 级制\n"
        text += "     1级 优良            < 0.05 mm/a    可用于关键设备与薄壁件\n"
        text += "     2级 良好            0.05 ~ 0.5     一般可用于连续操作设备\n"
        text += "     3级 可用（腐蚀较重）0.5 ~ 1.5      须计入腐蚀裕量并加强定期检测\n"
        text += "     4级 不适用（严重）  > 1.5         不推荐使用，应改用其他材料\n\n"
        text += "   细分级（参考）：中国腐蚀与防护学会《金属防腐蚀手册》10 级制\n"
        text += "     1级 <0.001 / 2级 0.001~0.005 / 3级 0.005~0.01 / 4级 0.01~0.05\n"
        text += "     5级 0.05~0.1 / 6级 0.1~0.5 / 7级 0.5~1.0 / 8级 1.0~5.0\n"
        text += "     9级 5.0~10.0 / 10级 >10.0  （单位 mm/a）\n\n"
        text += "   ⚠ 局部腐蚀（点蚀、缝隙腐蚀、应力腐蚀开裂、晶间腐蚀）即使平均速率很低\n"
        text += "      也可能导致穿孔或突发失效，不能只凭平均速率判定可用性。\n\n"

        text += "参考标准\n"
        text += "   术语类（只定义术语，不规定分级区间）：\n"
        text += "     GB/T 10123-2022 金属和合金的腐蚀 术语（等同采用 ISO 8044:2020，\n"
        text += "                     已全部代替 GB/T 10123-2001）\n"
        text += "   试验/评定方法类：\n"
        text += "     GB/T 18590 金属和合金的腐蚀 点蚀评定方法\n"
        text += "     ASTM G31 金属材料实验室浸渍腐蚀试验标准实施规程\n"
        text += "     ASTM G1  腐蚀试样制备、清洗与评价\n"
        text += "     ANSI/NACE MR0175 / ISO 15156 油气工业用抗硫化物应力开裂材料\n"
        text += "   分级/选材类（腐蚀速率等级的真正出处）：\n"
        text += "     左景伊《腐蚀数据与选材手册》（4 级制，化工选材主要依据）\n"
        text += "     中国腐蚀与防护学会《金属防腐蚀手册》（10 级制）\n"

        return text

    def load_corrosion_data(self):
        """加载腐蚀数据库（模块级 CORROSION_DB，返回副本避免被就地修改）"""
        return {k: dict(v) for k, v in CORROSION_DB.items()}

    def query_corrosion_data(self):
        """执行腐蚀数据查询（保留旧接口）"""
        self.calculate()

    def fuzzy_query(self, material, medium, temperature, concentration):
        """模糊查询：查找相关腐蚀数据"""
        related_data = []
        for key, value in self.corrosion_data.items():
            if material in key and medium in key:
                related_data.append((key, value))

        if related_data:
            result = "=== 相关腐蚀数据 ===\n\n"
            result += f"未找到精确匹配「{material}-{medium}」，以下是相关数据：\n\n"
            result += self._format_data_table(related_data)
            result += (f"\n提示：上表为模糊匹配结果，未包含工况适用性判定。\n"
                       f"      需要精确工况判定时，请在左侧选定「{material}」与「{medium}」后点查询。\n\n")
            result += f"── {DATA_SOURCE_NOTE} ──\n"
            self.result_text.setPlainText(result)
        else:
            self.result_text.setPlainText(
                f"未找到包含「{material}」和「{medium}」的相关腐蚀数据。\n\n"
                f"说明：本模块为内置参考数据集，仅收录了 {len(self.corrosion_data)} 组常见\n"
                f"材料-介质组合；未收录不等于该组合可用或不可用。请查阅\n"
                f"左景伊《腐蚀数据与选材手册》或做挂片试验后确定。\n\n"
                f"── {DATA_SOURCE_NOTE} ──\n")

    @staticmethod
    def _format_data_table(rows):
        """把 [(key, data), …] 排成表；用 ' | ' 分隔避免中文全角字符导致的对齐错位"""
        lines = [f"{'材料-介质':<22} | {'速率(mm/a)':>10} | {'等级':<12} | 说明",
                 "-" * 96]
        for key, data in rows:
            rate = data.get("rate", 0)
            grade = classify_corrosion_rate(rate)[0]
            lines.append(f"{key:<22} | {rate:>10} | {grade:<12} | {data.get('notes', '')}")
        return "\n".join(lines) + "\n"

    def _condition_warnings(self, data, temperature, concentration, ph):
        """工况偏离提示：数据只在参考工况下有效，偏离时必须提示不可外推"""
        warns = []
        t_ref = data.get("t_ref", 25)
        conc_ref = data.get("conc_ref")

        if temperature > 60:
            warns.append(
                f"所查温度 {temperature:g}°C 远高于数据参考温度 {t_ref:g}°C："
                "金属腐蚀率通常随温度成倍上升（多数体系每升高 10°C 增大 1~3 倍），"
                "本表速率不可外推，须查该温度下的腐蚀曲线或做挂片试验。")
        elif abs(temperature - t_ref) > 15:
            warns.append(
                f"所查温度 {temperature:g}°C 与数据参考温度 {t_ref:g}°C 相差超过 15°C，"
                "速率可能已有明显变化。")

        if conc_ref is not None and abs(concentration - conc_ref) > max(2.0, 0.2 * conc_ref):
            warns.append(
                f"所查浓度 {concentration:g}% 与数据参考浓度 {conc_ref:g}% 不符："
                "腐蚀率对浓度高度敏感（酸类尤其如此，部分体系存在浓度极值点），"
                "该速率不能代表所查浓度。")

        if ph is not None:
            # 酸/碱介质与 pH 自相矛盾时提示
            medium_is_acid = conc_ref is not None and "酸" in str(data.get("_medium", ""))
            if medium_is_acid and ph >= 7:
                warns.append(
                    f"介质为酸性而所填 pH={ph:g} 偏中性/碱性，两者不符，请核对查询条件。")
        return warns

    def display_results(self, data, material, medium, temperature, concentration, ph=None):
        """显示精确匹配的查询结果"""
        data = dict(data)          # 局部副本，避免把 _medium 等临时键写回数据库
        data["_medium"] = medium
        rate = data["rate"]
        grade, advice, grade10 = classify_corrosion_rate(rate)

        cond = f"{data.get('t_ref', 25):g}°C"
        if data.get("conc_ref") is not None:
            cond += f"、{data['conc_ref']:g}%"
        else:
            cond += "、介质本身（浓度不适用）"

        result = "=== 腐蚀数据查询结果 ===\n\n"
        result += f"材料-介质: {material} - {medium}\n"
        result += f"★ 腐蚀速率: {rate} mm/年（均匀腐蚀）\n"
        result += f"  耐蚀等级: {grade}   〔左景伊《腐蚀数据与选材手册》4 级制〕\n"
        result += f"  细分级:   {grade10}   〔《金属防腐蚀手册》10 级制，参考〕\n"
        result += f"  选材建议: {advice}\n\n"
        result += "── 查询工况 ──\n"
        ph_txt = f"{ph:g}" if ph is not None else "未填"
        result += f"  温度: {temperature:g} °C    浓度: {concentration:g} %    pH: {ph_txt}\n"
        result += f"  数据参考工况: {cond}\n\n"
        result += "── 说明与建议 ──\n"
        result += f"  {data['notes']}\n\n"

        warns = self._condition_warnings(data, temperature, concentration, ph)
        if warns:
            result += "── ⚠ 工况适用性提示 ──\n"
            for w in warns:
                result += f"  • {w}\n"
            result += "\n"

        # 理论穿透时间（未计腐蚀裕量，仅供量级参考）
        if rate > 0:
            result += "── 理论穿透时间（按均匀腐蚀、未计腐蚀裕量）──\n"
            for thickness in (3, 5, 8, 10):
                result += f"  {thickness}mm 壁厚: 约 {thickness / rate:.1f} 年\n"
            result += ("  注：实际设计须另留腐蚀裕量（通常 1~3mm）、并按年腐蚀率不超过\n"
                       "      0.1~0.5 mm/a 控制；点蚀/应力腐蚀等局部腐蚀不受此估算保护。\n\n")

        result += f"── {DATA_SOURCE_NOTE} ──\n"

        self.result_text.setPlainText(result)

        self._last_results = {
            "material": material,
            "medium": medium,
            "rate": rate,
            "grade": grade,
            "advice": advice,
            "grade10": grade10,
            "temperature": temperature,
            "concentration": concentration,
            "ph": ph,
            "cond": cond,
            "notes": data.get("notes", ""),
            "warnings": warns,
        }

    def on_search(self):
        """快速搜索功能"""
        keyword = self.search_input.text().strip().lower()
        if not keyword:
            return

        results = []
        for key, value in self.corrosion_data.items():
            if keyword in key.lower():
                results.append((key, value))

        if results:
            result_text = f"=== 搜索结果：「{keyword}」 ===\n\n"
            result_text += self._format_data_table(results)
            result_text += (f"\n共匹配 {len(results)} 条。等级由速率按左景伊《腐蚀数据与选材手册》\n"
                            f"4 级制自动派生；逐条工况适用性请在左侧按材料/介质查询。\n\n")
            result_text += f"── {DATA_SOURCE_NOTE} ──\n"
            self.result_text.setPlainText(result_text)
        else:
            self.result_text.setPlainText(f"未找到包含「{keyword}」的相关数据。")

    def clear_inputs(self):
        """清空所有输入和结果（恢复默认查询条件）"""
        self.material_category_combo.setCurrentIndex(0)
        self.medium_category_combo.setCurrentIndex(0)
        self.temperature_input.setText("25")
        self.concentration_input.setText("10")
        self.ph_input.setText("")
        self.result_text.clear()
        self.search_input.clear()
        self._last_results = {}

    def _get_history_data(self):
        """获取当前查询的历史记录数据（供外部调用）

        Returns:
            dict: 包含inputs和outputs的字典
        """
        material = self.material_combo.currentText()
        medium = self.medium_combo.currentText()
        try:
            temperature = float(self.temperature_input.text())
        except ValueError:
            temperature = 25.0
        try:
            concentration = float(self.concentration_input.text())
        except ValueError:
            concentration = 10.0
        try:
            ph = float(self.ph_input.text())
        except ValueError:
            ph = None      # 留空 = 未填，不做酸碱一致性校验

        inputs = {
            "材料类别": self.material_category_combo.currentText(),
            "具体材料": material,
            "介质类别": self.medium_category_combo.currentText(),
            "具体介质": medium,
            "温度_C": temperature,
            "浓度_%": concentration,
            "pH值": ph
        }

        outputs = {}
        # 优先取结构化结果（不解析显示文本，避免格式改动即失效）
        r = self._last_results
        if r:
            outputs = {
                "腐蚀速率_mm_a": r["rate"],
                "耐蚀等级": r["grade"],
                "细分级_10级制": r["grade10"],
                "数据参考工况": r["cond"],
                "选材建议": r["advice"],
                "工况提示条数": len(r.get("warnings") or []),
            }
        else:
            result_text = self.result_text.toPlainText()
            if result_text and "腐蚀速率:" in result_text:
                for line in result_text.split("\n"):
                    if "腐蚀速率:" in line:
                        outputs["腐蚀速率"] = line.split(":", 1)[1].strip()

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
            "project_name": saved.get("project_name", "腐蚀数据查询"),
            "subproject_name": saved.get("subproject_name", ""),
            "calculation_type": self.calculation_type,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def generate_report(self):
        """生成完整的查询报告内容（未查询时返回 None，不产出空壳报告）"""
        if not self._last_results:
            return None

        history = self._get_history_data()
        project = self.get_project_info()

        report_lines = [
            "=" * 60,
            "              腐蚀数据查询报告",
            "=" * 60,
            "",
            f"生成时间：{project['timestamp']}",
            f"计算类型：{project['calculation_type']}",
            "",
            "-" * 40,
            "【查询条件】",
            "-" * 40,
        ]
        for k, v in history["inputs"].items():
            report_lines.append(f"  {k}: {v}")

        report_lines.extend([
            "",
            "-" * 40,
            "【查询结果】",
            "-" * 40,
        ])
        for k, v in history["outputs"].items():
            report_lines.append(f"  {k}: {v}")

        # 补充详情文本
        detail_content = self.result_text.toPlainText().strip()
        if detail_content:
            report_lines.extend([
                "",
                "-" * 40,
                "【详细信息】",
                "-" * 40,
                detail_content
            ])

        report_lines.extend([
            "",
            "=" * 60,
            "                      工程信息",
            "=" * 60,
            f"    公司名称: {project.get('company_name', '')}",
            f"    工程编号: {project.get('project_number', '')}",
            f"    工程名称: {project.get('project_name', '')}",
            f"    子项名称: {project.get('subproject_name', '')}",
            f"    计算日期: {datetime.datetime.now().strftime('%Y-%m-%d')}",
            "",
            "=" * 60,
            "                     报告结束",
            "=" * 60,
        ])

        return "\n".join(report_lines)

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "腐蚀数据查询")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "腐蚀数据查询")
if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = CorrosionDataQuery()
    widget.resize(1300, 700)
    widget.show()

    sys.exit(app.exec())
