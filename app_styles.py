"""
ChemCal 全局样式常量
集中管理所有跨计算器共享的 Qt 样式表，避免 39 个文件各自定义 COMBOBOX_STYLE。
"""

# ── QComboBox 样式 ────────────────────────────────────────────
COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #888;
        border-radius: 4px;
        padding: 6px 10px;
    }
    QComboBox QAbstractItemView {
        border: 1px solid #888;
        selection-background-color: #3498db;
        selection-color: black;
    }
    QComboBox QAbstractItemView::item {
        padding: 3px 8px;
    }
"""

# ── QGroupBox 样式 ────────────────────────────────────────────
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

# ── 计算按钮样式 ───────────────────────────────────────────────
CALC_BUTTON_STYLE = """
    QPushButton {
        background-color: #27ae60;
        color: white;
        font-size: 14px;
        font-weight: bold;
        border-radius: 8px;
        padding: 0px;
        min-height: 50px;
    }
    QPushButton:hover {
        background-color: #219955;
    }
"""

# ── 模式按钮（QPushButton 可选中模式） ──────────────────────
MODE_BUTTON_STYLE = """
    QPushButton {
        background-color: #ffffff;
        color: black;
        border: 1px solid #888;
        border-radius: 4px;
        padding: 8px;
        font-weight: bold;
    }
    QPushButton:checked {
        background-color: #4b5cc4;
        color: white;
    }
    QPushButton:hover:!checked {
        background-color: #c0ebd7;
        color: black;
    }
"""

# ── 下载/清空按钮（QPushButton 平面色块） ─────────────────────
def download_btn_style(color="#3498db", hover_color="#2980b9"):
    """生成下载按钮样式"""
    return f"""
        QPushButton {{
            background-color: {color};
            color: white;
            padding: 8px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
    """

CLEAR_BTN_STYLE = download_btn_style("#95a5a6", "#7f8c8d")
DOCX_BTN_STYLE = download_btn_style("#3498db", "#2980b9")
PDF_BTN_STYLE = download_btn_style("#e74c3c", "#c0392b")

# ── QScrollArea 透明内边 + 窄滚动条 ──────────────────────────
SCROLL_AREA_STYLE = """
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

# ── QLabel 标签样式（输入参数网格） ───────────────────────────
INPUT_LABEL_STYLE = "font-weight: bold; padding-right: 10px; text-align: right;"
