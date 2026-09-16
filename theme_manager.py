# ChemCal/theme_manager.py
import re

from PySide6.QtCore import QObject, Signal

#: 当前生效的主题名（由 ThemeManager 实例同步，供拿不到实例的页面读取）
_ACTIVE_THEME = "light"

#: 历史数据（如 data/reference_db.json 里内嵌的表格 HTML）中残留的"亮色主题专用"颜色。
#: 它们会压过主题：`#ecf0f1` 这种浅色表头底在深色主题下就是"浅底压浅字"，表格头看不见。
#: 渲染时统一归一化 —— 数据可保持原样，新加数据即便又写了浅色也不会再炸。
LEGACY_LIGHT_FILLS = ("#ecf0f1", "#f8f9fa", "#f0f0f0", "#fef9e7", "#ffffff")
LEGACY_LIGHT_BORDERS = ("#ddd", "#dddddd", "#ccc", "#cccccc", "#e0e0e0")


def normalize_legacy_content_colors(html: str, colors: dict = None) -> str:
    """把富文本里残留的亮色主题专用颜色改写成主题色。

    浅色填充块 → 主题强调色底 + 反白文字（保证任何主题下都读得清）；
    浅色边框 → 主题边框色。
    """
    c = colors or get_content_colors()
    out = html
    for light in LEGACY_LIGHT_FILLS:
        out = re.sub(r"(?i)background\s*:\s*" + re.escape(light) + r"\s*;?",
                     f"background: {c['banner_bg']}; color: {c['banner_fg']};", out)
    for light in LEGACY_LIGHT_BORDERS:
        out = re.sub(r"(?i)(1px\s+solid\s+)" + re.escape(light),
                     r"\g<1>" + c["rule"], out)
    return out


def get_active_theme() -> str:
    """当前生效的主题名。"""
    return _ACTIVE_THEME


def get_content_colors(theme_name: str = None) -> dict:
    """取当前主题的 HTML 内容配色。

    Qt 富文本（QTextEdit / QTextBrowser 里的 HTML）**读不到 QSS 变量**，
    所以正文色、强调色必须由主题提供。页面在渲染 HTML 时调用本函数，
    并在 on_theme_changed() 里重渲染，避免出现"深底压深字""浅底压浅字"。
    """
    name = theme_name or _ACTIVE_THEME
    palettes = ThemeManager.CONTENT_COLORS
    return dict(palettes.get(name, palettes["light"]))


#: ── 倒计时卡片状态配色 ────────────────────────────────────────────
#: 三套主题必须给全**同样的键**（缺一个键 → 该主题下卡片那一块就没颜色）。
#: 状态由控件动态属性驱动：cdState = normal|soon|overdue，cdSelected = 0|1。
CD_COLORS = {
    "light": {
        "muted": "#6b7280",
        "card_bg": "#f7f9fc", "card_border": "#d1d5db", "card_hover": "#9db4d0",
        "sel_bg": "#eaf1fa", "sel_border": "#4a6fa5",
        "soon_bg": "#fef6e7", "soon_border": "#d97706", "soon_fg": "#b45309",
        "over_bg": "#fdf2f2", "over_border": "#b91c1c", "over_fg": "#b91c1c",
        "time": "#2f5d94",
        "badge_fg": "#4b5563", "badge_bg": "#eceff3",
        "soon_badge_bg": "#fbe3bd", "over_badge_bg": "#f7d9d9",
        "track": "#e3e8ef",
    },
    "dark": {
        "muted": "#a3a3a3",
        "card_bg": "#333333", "card_border": "#555555", "card_hover": "#7f9fc4",
        "sel_bg": "#3a4453", "sel_border": "#6ba1e0",
        "soon_bg": "#3a352a", "soon_border": "#e0a94a", "soon_fg": "#e0a94a",
        "over_bg": "#3a2b2b", "over_border": "#d4513f", "over_fg": "#f08a8a",
        "time": "#8ab6e8",
        "badge_fg": "#c9c9c9", "badge_bg": "#444444",
        "soon_badge_bg": "#4a3d24", "over_badge_bg": "#4a2f2f",
        "track": "#4a4a4a",
    },
    "blue": {
        "muted": "#5b6b7c",
        "card_bg": "#ffffff", "card_border": "#bee3f8", "card_hover": "#7fb8e6",
        "sel_bg": "#e8f2fd", "sel_border": "#3182ce",
        "soon_bg": "#fff8ec", "soon_border": "#d97706", "soon_fg": "#b45309",
        "over_bg": "#fdf2f2", "over_border": "#b91c1c", "over_fg": "#b91c1c",
        "time": "#2b6cb0",
        "badge_fg": "#2c5282", "badge_bg": "#e2eefa",
        "soon_badge_bg": "#fbe3bd", "over_badge_bg": "#f7d9d9",
        "track": "#d6e8f7",
    },
}

#: 倒计时卡片样式模板 —— `$key` 用 CD_COLORS 对应主题的值替换。
#: 之所以用 $ 占位而不是 str.format：QSS 里全是花括号，转义起来必错。
CD_RULES_SRC = """
        /* ═══════ 倒计时卡片（cdState: normal/soon/overdue，cdSelected: 0/1） ═══════ */
        QScrollArea#cdScroll { border: none; }
        /* 全局 QWidget 规则会把背景铺到 QLabel 上，卡片里的文字标签必须显式透明，
           否则浅色主题下白色标签盖住卡片底色、深色主题下深灰标签盖住卡片底色 */
        QFrame#cdCard { background-color: $card_bg; border: 1px solid $card_border;
                        border-radius: 8px; }
        QFrame#cdCard:hover { border-color: $card_hover; }
        QFrame#cdCard[cdState="soon"] { background-color: $soon_bg; border-color: $soon_border; }
        QFrame#cdCard[cdState="overdue"] { background-color: $over_bg;
                                           border-color: $over_border; }
        /* 选中态规则放最后：与状态规则同优先级，靠后生效 —— 保证选中永远看得见 */
        QFrame#cdCard[cdSelected="1"] { background-color: $sel_bg; border: 2px solid $sel_border; }
        QLabel#cdName { font-weight: bold; font-size: 13px; background-color: transparent; }
        QLabel#cdTarget { font-size: 11px; color: $muted; background-color: transparent; }
        QLabel#cdTime { color: $time; background-color: transparent; }
        QLabel#cdTime[cdState="soon"] { color: $soon_fg; }
        QLabel#cdTime[cdState="overdue"] { color: $over_fg; }
        QLabel#cdBadge { color: $badge_fg; background-color: $badge_bg; border-radius: 8px;
                         padding: 1px 8px; font-size: 11px; }
        QLabel#cdBadge[cdState="soon"] { color: $soon_fg; background-color: $soon_badge_bg; }
        QLabel#cdBadge[cdState="overdue"] { color: $over_fg; background-color: $over_badge_bg; }
        QLabel#cdEmpty { color: $muted; font-size: 13px; background-color: transparent; }
        QProgressBar#cdProgress { background-color: $track; border: none; border-radius: 3px;
                                  min-height: 6px; max-height: 6px; }
        QProgressBar#cdProgress::chunk { background-color: $time; border-radius: 3px; }
"""


def countdown_card_rules(theme_name: str) -> str:
    """取某主题的倒计时卡片样式。

    占位符必须全部替换掉 —— 漏一个就会在 QSS 里留下 `$xxx`，Qt 解析整段规则失败，
    卡片会静默变成"没有样式"。所以这里自己守一道，宁可报错也不要静默降级。
    """
    colors = CD_COLORS.get(theme_name, CD_COLORS["light"])
    out = CD_RULES_SRC
    for key, value in colors.items():
        out = out.replace(f"${key}", value)
    leftover = [w for w in out.split() if w.startswith("$")]
    if leftover:
        raise ValueError(f"倒计时卡片样式存在未替换占位符: {leftover}")
    return out


class ThemeManager(QObject):
    """主题管理器 - 管理应用程序主题"""
    
    theme_changed = Signal(str)  # 主题改变信号
    
    def __init__(self):
        super().__init__()
        self.current_theme = "light"
        self.themes = {
            "light": self.get_light_theme(),
            "dark": self.get_dark_theme(),
            "blue": self.get_blue_theme()
        }
        # 语义组件规则集中追加到三套主题 —— 保证永远同步，别只在某一套里加规则
        for _name in list(self.themes):
            self.themes[_name] += self.SEMANTIC_RULES[_name]
        # 同步模块级当前主题（页面通过 theme_manager.get_content_colors() 取色）
        global _ACTIVE_THEME
        _ACTIVE_THEME = self.current_theme
    
    #: ── HTML 富文本内容配色 ─────────────────────────────────────
    #: Qt 富文本读不到 QSS，页面渲染 HTML 时从这里取色（三套主题必须给全同样的键）
    CONTENT_COLORS = {
        "light": {
            "muted": "#6b7280",       # 次要文字（时间、来源、说明）
            "accent": "#b45309",      # 强调小标签
            "ok": "#15803d",          # 计算结果 / 正向
            "danger": "#b91c1c",      # 警示
            "rule": "#d1d5db",        # 表格分隔线（与主题边框同色）
            "banner_bg": "#4a6fa5",   # 顶部色块背景
            "banner_fg": "#ffffff",   # 顶部色块文字
        },
        "dark": {
            "muted": "#a3a3a3",
            "accent": "#e0a94a",
            "ok": "#6fcf97",
            "danger": "#f08a8a",
            "rule": "#555555",
            "banner_bg": "#4a6fa5",
            "banner_fg": "#ffffff",
        },
        "blue": {
            "muted": "#5b6b7c",
            "accent": "#b45309",
            "ok": "#15803d",
            "danger": "#b91c1c",
            "rule": "#bee3f8",
            "banner_bg": "#3182ce",
            "banner_fg": "#ffffff",
        },
    }

    #: ── 语义组件规则（集中追加，保证三套主题一致） ──────────────
    #: 页面用法：控件 setObjectName("mutedLabel" / "primaryBtn" / "dangerBtn" ...)，
    #: 不要把颜色写进控件自己的 setStyleSheet —— 那会压过主题，深色下就看不见了
    SEMANTIC_RULES = {
        "light": """
        /* ═══════ 语义组件（三套主题同步，详见 theme_manager.SEMANTIC_RULES） ═══════ */
        QLabel#mutedLabel { color: #6b7280; }
        QLabel#accentLabel { color: #b45309; font-weight: bold; }
        QPushButton#primaryBtn { background-color: #4a6fa5; color: white;
                                 border: none; border-radius: 6px; padding: 0 16px; }
        QPushButton#primaryBtn:hover:!checked { background-color: #3d5c8a; }
        QPushButton#dangerBtn { background-color: #c0392b; color: white;
                                border: none; border-radius: 6px; padding: 0 16px; }
        QPushButton#dangerBtn:hover:!checked { background-color: #a03024; }
        QPushButton#primaryBtn:disabled, QPushButton#dangerBtn:disabled {
            background-color: #c4c7c5; color: #8a8a8a; }
        QLineEdit[roField="true"] { background-color: #f0f0f0; color: #6b7280; }
        QLabel[unitLabel="true"] { color: #6b7280; }
        """ + countdown_card_rules("light"),
        "dark": """
        /* ═══════ 语义组件（三套主题同步，详见 theme_manager.SEMANTIC_RULES） ═══════ */
        QLabel#mutedLabel { color: #a3a3a3; }
        QLabel#accentLabel { color: #e0a94a; font-weight: bold; }
        QPushButton#primaryBtn { background-color: #4a6fa5; color: white;
                                 border: none; border-radius: 6px; padding: 0 16px; }
        QPushButton#primaryBtn:hover:!checked { background-color: #5b82bd; }
        QPushButton#dangerBtn { background-color: #c0392b; color: white;
                                border: none; border-radius: 6px; padding: 0 16px; }
        QPushButton#dangerBtn:hover:!checked { background-color: #d4513f; }
        QPushButton#primaryBtn:disabled, QPushButton#dangerBtn:disabled {
            background-color: #4a4a4a; color: #8a8a8a; }
        QLineEdit[roField="true"] { background-color: #2b2b2b; color: #a3a3a3; }
        QLabel[unitLabel="true"] { color: #a3a3a3; }
        """ + countdown_card_rules("dark"),
        "blue": """
        /* ═══════ 语义组件（三套主题同步，详见 theme_manager.SEMANTIC_RULES） ═══════ */
        QLabel#mutedLabel { color: #5b6b7c; }
        QLabel#accentLabel { color: #b45309; font-weight: bold; }
        QPushButton#primaryBtn { background-color: #3182ce; color: white;
                                 border: none; border-radius: 6px; padding: 0 16px; }
        QPushButton#primaryBtn:hover:!checked { background-color: #2b6cb0; }
        QPushButton#dangerBtn { background-color: #c0392b; color: white;
                                border: none; border-radius: 6px; padding: 0 16px; }
        QPushButton#dangerBtn:hover:!checked { background-color: #a03024; }
        QPushButton#primaryBtn:disabled, QPushButton#dangerBtn:disabled {
            background-color: #bee3f8; color: #8a8a8a; }
        QLineEdit[roField="true"] { background-color: #edf2f7; color: #5b6b7c; }
        QLabel[unitLabel="true"] { color: #5b6b7c; }
        """ + countdown_card_rules("blue"),
    }

    def get_light_theme(self):
        """浅色主题 — 白色底色 + 蓝灰色控件"""
        return """
        /* ═══════ 主窗口 ═══════ */
        QMainWindow {
            background-color: #f5f7fa;                      /* 窗口底色 */
        }

        /* ═══════ 基础控件 ═══════ */
        QWidget {
            background-color: #ffffff;                      /* 控件背景 */
            color: #374151;                                 /* 文字颜色 */
        }

        QScrollArea {
            background-color: #ffffff;                      /* 滚动区域背景 */
        }

        QScrollArea > QWidget > QWidget {
            background-color: #ffffff;                      /* 滚动区域内层背景 */
        }

        /* ═══════ 标签页 (QTabWidget) ═══════ */
        QTabWidget::pane {
            border: 1px solid #c4c7c5;                     /* 边框 */
            background-color: white;                        /* 背景 */
            border-radius: 8px;                             /* 圆角 */
        }

        QTabBar::tab {
            background-color: #e1e5e9;                     /* 未选中标签背景 */
            border: 1px solid #c4c7c5;                     /* 边框 */
            border-bottom: none;                            /* 底部无边框，与页面连在一起 */
            border-top-left-radius: 8px;                    /* 左上圆角 */
            border-top-right-radius: 8px;                   /* 右上圆角 */
            padding: 8px 16px;                              /* 内边距 */
            margin-right: 2px;                              /* 标签间距 */
            min-width: 80px;                                /* 最小宽度 */
            color: #374151;                                 /* 文字颜色 */
        }

        QTabBar::tab:selected {
            background-color: white;                        /* 选中标签背景 */
            border-color: #c4c7c5;                         /* 边框颜色 */
            border-bottom-color: white;                     /* 底部与页面同色，消除分割线 */
            color: #111827;                                 /* 选中文字加深 */
        }

        QTabBar::tab:hover:!selected {
            background-color: #f0f2f5;                     /* 未选中标签悬停 */
        }

        /* ═══════ 通用按钮 ═══════ */
        QPushButton {
            background-color: #4a6fa5;                     /* 按钮背景 */
            color: white;                                   /* 按钮文字 */
            border: none;                                   /* 无边框 */
            border-radius: 6px;                             /* 圆角 */
            padding: 8px 16px;                              /* 内边距 */
            font-weight: bold;                              /* 加粗 */
            min-height: 20px;                               /* 最小高度 */
        }

        QPushButton:hover:!checked {
            background-color: #3a5a8c;                     /* 悬停变深 */
        }

        QPushButton:pressed {
            background-color: #2a4a7c;                     /* 按下更深 */
        }

        QPushButton:disabled {
            background-color: #cccccc;                     /* 禁用灰色 */
            color: #666666;                                 /* 禁用文字 */
        }

        /* ═══════ 分组框 (QGroupBox) ═══════ */
        QGroupBox {
            font-weight: bold;                              /* 标题加粗 */
            border: 1px solid #333333;                      /* 边框 */
            border-radius: 8px;                             /* 圆角 */
            margin-top: 10px;                               /* 上边距（给标题留空间） */
            padding-top: 10px;                              /* 上内边距 */
            background-color: white;                        /* 背景 */
            color: #374151;                                 /* 文字颜色 */
        }

        QGroupBox::title {
            subcontrol-origin: margin;                      /* 标题定位基准 margin */
            left: 10px;                                     /* 标题左偏移 */
            padding: 0 8px 0 8px;                           /* 标题两侧留空 */
            color: #4a6fa5;                                 /* 标题颜色 */
        }

        /* ═══════ 输入框 (单行/多行/下拉) ═══════ */
        QLineEdit, QTextEdit, QComboBox, QDateTimeEdit, QDateEdit, QTimeEdit, QSpinBox {
            border: 1px solid #d1d5db;                      /* 边框 */
            border-radius: 6px;                             /* 圆角 */
            padding: 6px 10px;                              /* 内边距 */
            background-color: white;                        /* 背景 */
            selection-background-color: #4a6fa5;            /* 选中文字背景色 */
            color: #374151;                                 /* 文字颜色 */
        }

        QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
        QDateTimeEdit:focus, QSpinBox:focus {
            border-color: #4a6fa5;                          /* 获焦时边框高亮 */
        }

        /* QComboBox 下拉列表样式 */
        QComboBox QAbstractItemView {
            background-color: white;                        /* 下拉列表背景 */
            color: #374151;                                 /* 文字 */
            border: 1px solid #d1d5db;                      /* 边框 */
            selection-background-color: #4a6fa5;            /* 选中项背景 */
            selection-color: black;                         /* 选中项文字 */
        }

        QComboBox QAbstractItemView::item {
            min-height: 28px;                               /* 选项高度 */
            padding: 4px 8px;                               /* 选项内边距 */
        }

        QComboBox QAbstractItemView::item:hover {
            background-color: #e8edf2;                     /* 悬停背景 */
        }

        /* ═══════ 列表/树控件 ═══════ */
        QListWidget, QTreeWidget {
            border: 1px solid #d1d5db;                      /* 边框 */
            border-radius: 6px;                             /* 圆角 */
            background-color: white;                        /* 背景 */
            alternate-background-color: #f8f9fa;            /* 交替行背景 */
            color: #374151;                                 /* 文字 */
        }

        QListWidget::item:selected, QTreeWidget::item:selected {
            background-color: #4a6fa5;                      /* 选中项背景 */
            color: white;                                   /* 选中项文字 */
        }

        /* ═══════ 表格 (QTableWidget) ═══════ */
        QTableWidget {
            border: 1px solid #d1d5db;                      /* 边框 */
            border-radius: 6px;                             /* 圆角 */
            background-color: white;                        /* 背景 */
            alternate-background-color: #f8f9fa;            /* 交替行背景 */
            color: #374151;                                 /* 文字 */
        }

        QHeaderView::section {
            background-color: #f8f9fa;                      /* 表头背景 */
            color: #374151;                                 /* 表头文字 */
            border: 1px solid #d1d5db;                      /* 表头边框 */
            padding: 5px;                                   /* 内边距 */
            font-weight: bold;                              /* 加粗 */
        }

        QTableWidget::item:selected {
            background-color: #4a6fa5;                      /* 选中单元格 */
            color: white;
        }

        /* ======== 以下为 objectName 驱动的专用控件样式 ======== */

        /* ── 工程计算-左侧导航列表 ── */
        QListWidget#calcNavList {
            border: 1px solid #d1d5db;                      /* 边框 */
            border-radius: 8px;                             /* 圆角 */
            font-size: 13px;                                /* 字号 */
            padding: 5px 0px;                               /* 上下内边距 */
            background-color: #f8f9fa;                      /* 背景 */
            color: #374151;                                 /* 文字 */
            outline: none;                                  /* 去除焦点虚线框 */
        }

        QListWidget#calcNavList::item {
            height: 40px;                                   /* 列表项高度 */
            padding-left: 15px;                             /* 左侧缩进 */
            border-bottom: 1px solid #e9ecef;               /* 底部分割线 */
            margin: 2px 8px;                                /* 外边距 */
            border-radius: 6px;                             /* 圆角 */
            color: #495057;                                 /* 文字 */
        }

        QListWidget#calcNavList::item:selected {
            background-color: #4b5cc4;                      /* 选中背景 */
            color: white;                                   /* 选中文字 */
            font-weight: bold;                              /* 加粗 */
            border-radius: 6px;                             /* 圆角 */
            outline: none;                                  /* 去除焦点虚线框 */
        }

        QListWidget#calcNavList::item:hover:!selected {
            background-color: #e9ecef;                      /* 未选中项悬停 */
            color: #212529;                                 /* 悬停文字加深 */
        }

        /* ── 工程计算-右侧内容区 ── */
        QStackedWidget#calcContentStack {
            background-color: #ffffff;                      /* 背景 */
            border: 1px solid #d1d5db;                      /* 边框 */
            border-radius: 8px;                             /* 圆角 */
            margin-left: 10px;                              /* 左侧间距 */
        }

        /* ── 换算器-左侧导航列表 ── */
        QListWidget#converterNavList {
            border: none;                                   /* 无边框 */
            border-right: 1px solid #dee2e6;                /* 仅右侧分割线 */
            font-size: 13px;                                /* 字号 */
            background-color: #f8f9fa;                      /* 背景 */
            color: #374151;                                 /* 文字 */
        }

        QListWidget#converterNavList::item {
            height: 35px;                                   /* 列表项高度 */
            padding-left: 15px;                             /* 左侧缩进 */
            border-bottom: 1px solid #e9ecef;               /* 底部分割线 */
            color: #495057;                                 /* 文字 */
        }

        QListWidget#converterNavList::item:selected {
            background-color: #4a6fa5;                      /* 选中背景 */
            color: white;                                   /* 选中文字 */
            font-weight: bold;                              /* 加粗 */
            border-left: 4px solid #3a5f95;                 /* 左侧强调条 */
            border-bottom: 1px solid #e9ecef;               /* 底部分割线 */
        }

        QListWidget#converterNavList::item:hover:!selected {
            background-color: #e9ecef;                      /* 悬停背景 */
        }

        /* ── 换算器-右侧内容区 ── */
        QStackedWidget#converterContentStack {
            background-color: #ffffff;                      /* 背景 */
            border: none;                                   /* 无边框 */
        }

        /* ── 计算历史-列表 ── */
        QListWidget#historyList {
            border: 1px solid #d1d5db;                      /* 边框 */
            border-radius: 6px;                             /* 圆角 */
            font-size: 13px;                                /* 字号 */
            background-color: #ffffff;                      /* 背景 */
            color: #374151;                                 /* 文字 */
        }

        QListWidget#historyList::item {
            padding: 8px;                                   /* 内边距 */
            border-bottom: 1px solid #f1f3f4;               /* 底部分割线 */
        }

        QListWidget#historyList::item:selected {
            background-color: #4a6fa5;                      /* 选中背景 */
            color: white;                                   /* 选中文字 */
        }

        QListWidget#historyList::item:hover:!selected {
            background-color: #e9ecef;                      /* 悬停背景 */
        }

        /* ── 计算历史-详情文本框 ── */
        QTextEdit#historyDetailText {
            border: 1px solid #d1d5db;                      /* 边框 */
            border-radius: 6px;                             /* 圆角 */
            font-size: 13px;                                /* 字号 */
            padding: 8px;                                   /* 内边距 */
            background-color: #ffffff;                      /* 背景 */
            color: #374151;                                 /* 文字 */
        }

        /* ═══════ 菜单栏 ═══════ */
        QMenuBar {
            background-color: white;                        /* 背景 */
            border-bottom: 1px solid #e5e7eb;               /* 底部分割线 */
            color: #374151;                                 /* 文字 */
        }

        QMenuBar::item {
            padding: 6px 12px;                              /* 内边距 */
            background-color: transparent;                  /* 默认透明 */
        }

        QMenuBar::item:selected {
            background-color: #e5e7eb;                      /* 选中背景 */
        }

        /* ═══════ 状态栏 ═══════ */
        QStatusBar {
            background-color: white;                        /* 背景 */
            color: #6b7280;                                 /* 文字 */
            border-top: 1px solid #e5e7eb;                  /* 顶部分割线 */
        }

        /* ═══════ 标签 (QLabel) ═══════ */
        QLabel {
            color: #374151;                                 /* 全局标签文字色 */
        }

        /* ═══════ 滚动条 ═══════ */
        QScrollBar:vertical {
            border: none;                                   /* 无边框 */
            background-color: #f0f0f0;                      /* 滑道背景 */
            width: 12px;                                    /* 宽度 */
            margin: 0px;                                    /* 外边距 */
            border-radius: 6px;                             /* 圆角 */
        }

        QScrollBar::handle:vertical {
            background-color: #c0c0c0;                      /* 滑块颜色 */
            border-radius: 6px;                             /* 滑块圆角 */
            min-height: 20px;                               /* 最小高度 */
        }

        QScrollBar::handle:vertical:hover {
            background-color: #a0a0a0;                      /* 滑块悬停变深 */
        }
        """
    def get_dark_theme(self):
        """深色主题 — 结构同浅色主题，仅颜色值不同（浅底变深底、浅字变浅字）"""
        return """
        /* 主窗口样式 */
        QMainWindow {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }

        /* 基础控件背景（防止白色透出） */
        QWidget {
            background-color: #2d2d2d;
            color: #e0e0e0;
        }

        QScrollArea {
            background-color: #2d2d2d;
        }
        QScrollArea > QWidget > QWidget {
            background-color: #2d2d2d;
        }
        
        /* 标签页样式 */
        QTabWidget::pane {
            border: 1px solid #444;
            background-color: #2d2d2d;
            border-radius: 8px;
        }
        
        QTabBar::tab {
            background-color: #3d3d3d;
            color: #b0b0b0;
            border: 1px solid #444;
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 8px 16px;
            margin-right: 2px;
            min-width: 80px;
        }
        
        QTabBar::tab:selected {
            background-color: #2d2d2d;
            color: #ffffff;
            border-color: #444;
            border-bottom-color: #2d2d2d;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #4d4d4d;
        }
        
        /* 按钮样式 */
        QPushButton {
            background-color: #4a6fa5;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            min-height: 20px;
        }
        
        QPushButton:hover:!checked {
            background-color: #3a5a8c;
        }
        
        QPushButton:pressed {
            background-color: #2a4a7c;
        }
        
        QPushButton:disabled {
            background-color: #555555;
            color: #888888;
        }
        
        /* 分组框样式 */
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: #2d2d2d;
            color: #e0e0e0;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: #6ba1e0;
        }
        
        /* 输入框样式 */
        QLineEdit, QTextEdit, QComboBox, QDateTimeEdit, QDateEdit, QTimeEdit, QSpinBox {
            border: 1px solid #555;
            border-radius: 6px;
            padding: 6px 10px;
            background-color: #333;
            selection-background-color: #4a6fa5;
            color: #e0e0e0;
        }
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
        QDateTimeEdit:focus, QSpinBox:focus {
            border-color: #4a6fa5;
        }

        /* QComboBox 下拉列表样式 */
        QComboBox QAbstractItemView {
            background-color: #3a3a3a;
            color: #e0e0e0;
            border: 1px solid #555;
            selection-background-color: #4a6fa5;
            selection-color: black;
        }
        QComboBox QAbstractItemView::item {
            min-height: 28px;
            padding: 4px 8px;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #4a4a4a;
        }

        /* 列表和树状视图 */
        QListWidget, QTreeWidget {
            border: 1px solid #555;
            border-radius: 6px;
            background-color: #333;
            alternate-background-color: #3a3a3a;
            color: #e0e0e0;
        }

        QListWidget::item:selected, QTreeWidget::item:selected {
            background-color: #4a6fa5;
            color: white;
        }

        /* 表格样式 */
        QTableWidget {
            border: 1px solid #555;
            border-radius: 6px;
            background-color: #333;
            alternate-background-color: #3a3a3a;
            color: #e0e0e0;
        }

        QHeaderView::section {
            background-color: #3a3a3a;
            color: #e0e0e0;
            border: 1px solid #555;
            padding: 5px;
            font-weight: bold;
        }

        QTableWidget::item:selected {
            background-color: #4a6fa5;
            color: white;
        }

        /* ======== 框架控件（objectName 驱动） ======== */

        /* 工程计算-左侧导航 */
        QListWidget#calcNavList {
            border: 1px solid #555;
            border-radius: 8px;
            font-size: 13px;
            padding: 5px 0px;
            background-color: #2d2d2d;
            color: #e0e0e0;
            outline: none;
        }
        QListWidget#calcNavList::item {
            height: 40px;
            padding-left: 15px;
            border-bottom: 1px solid #444;
            margin: 2px 8px;
            border-radius: 6px;
            color: #e0e0e0;
        }
        QListWidget#calcNavList::item:selected {
            background-color: #4b5cc4;
            color: white;
            font-weight: bold;
            border-radius: 6px;
            outline: none;
        }
        QListWidget#calcNavList::item:hover:!selected {
            background-color: #3a3a3a;
            color: #ffffff;
        }

        /* 工程计算-右侧内容 */
        QStackedWidget#calcContentStack {
            background-color: #2d2d2d;
            border: 1px solid #555;
            border-radius: 8px;
            margin-left: 10px;
        }

        /* 换算器-左侧导航 */
        QListWidget#converterNavList {
            border: none;
            border-right: 1px solid #555;
            font-size: 13px;
            background-color: #2d2d2d;
            color: #e0e0e0;
        }
        QListWidget#converterNavList::item {
            height: 35px;
            padding-left: 15px;
            border-bottom: 1px solid #444;
            color: #e0e0e0;
        }
        QListWidget#converterNavList::item:selected {
            background-color: #4a6fa5;
            color: white;
            font-weight: bold;
            border-left: 4px solid #5a8fc5;
            border-bottom: 1px solid #444;
        }
        QListWidget#converterNavList::item:hover:!selected {
            background-color: #3a3a3a;
        }

        /* 换算器-右侧内容 */
        QStackedWidget#converterContentStack {
            background-color: #2d2d2d;
            border: none;
        }

        /* 计算历史 */
        QListWidget#historyList {
            border: 1px solid #555; border-radius: 6px; font-size: 13px;
            background-color: #2d2d2d; color: #e0e0e0;
        }
        QListWidget#historyList::item {
            padding: 8px; border-bottom: 1px solid #444;
        }
        QListWidget#historyList::item:selected {
            background-color: #4a6fa5; color: white;
        }
        QListWidget#historyList::item:hover:!selected {
            background-color: #3a3a3a;
        }
        QTextEdit#historyDetailText {
            border: 1px solid #555; border-radius: 6px; font-size: 13px;
            padding: 8px; background-color: #2d2d2d; color: #e0e0e0;
        }

        /* ======== 菜单栏 ======== */
        QMenuBar {
            background-color: #2d2d2d;
            border-bottom: 1px solid #444;
            color: #e0e0e0;
        }
        
        QMenuBar::item {
            padding: 6px 12px;
            background-color: transparent;
        }
        
        QMenuBar::item:selected {
            background-color: #444;
        }
        
        /* 状态栏 */
        QStatusBar {
            background-color: #2d2d2d;
            color: #b0b0b0;
            border-top: 1px solid #444;
        }
        
        /* 标签 */
        QLabel {
            color: #e0e0e0;
        }
        
        /* 滚动条 */
        QScrollBar:vertical {
            border: none;
            background-color: #333;
            width: 12px;
            margin: 0px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #666;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #888;
        }
        """
    
    def get_blue_theme(self):
        """蓝色主题 — 结构同浅色主题，色调偏蓝"""
        return """
        /* 主窗口样式 */
        QMainWindow {
            background-color: #e6f2ff;
        }

        /* 基础控件背景 */
        QWidget {
            background-color: #f0f7ff;
            color: #2d3748;
        }

        QScrollArea {
            background-color: #f0f7ff;
        }
        QScrollArea > QWidget > QWidget {
            background-color: #f0f7ff;
        }
        
        /* 标签页样式 */
        QTabWidget::pane {
            border: 1px solid #a8c6e0;
            background-color: white;
            border-radius: 8px;
        }
        
        QTabBar::tab {
            background-color: #c2d9f0;
            border: 1px solid #a8c6e0;
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 8px 16px;
            margin-right: 2px;
            min-width: 80px;
            color: #2c5282;
        }
        
        QTabBar::tab:selected {
            background-color: white;
            border-color: #a8c6e0;
            border-bottom-color: white;
            color: #1a365d;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #d8e8f8;
        }
        
        /* 按钮样式 */
        QPushButton {
            background-color: #3182ce;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            min-height: 20px;
        }
        
        QPushButton:hover:!checked {
            background-color: #2b6cb0;
        }
        
        QPushButton:pressed {
            background-color: #2c5282;
        }
        
        QPushButton:disabled {
            background-color: #a0aec0;
            color: #718096;
        }
        
        /* 分组框样式 */
        QGroupBox {
            font-weight: bold;
            border: 1px solid #3182ce;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: white;
            color: #2d3748;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: #3182ce;
        }
        
        /* 输入框样式 */
        QLineEdit, QTextEdit, QComboBox, QDateTimeEdit, QDateEdit, QTimeEdit, QSpinBox {
            border: 1px solid #bee3f8;
            border-radius: 6px;
            padding: 6px 10px;
            background-color: white;
            selection-background-color: #3182ce;
            color: #2d3748;
        }
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
        QDateTimeEdit:focus, QSpinBox:focus {
            border-color: #3182ce;
        }

        /* QComboBox 下拉列表样式 */
        QComboBox QAbstractItemView {
            background-color: white;
            color: #2d3748;
            border: 1px solid #bee3f8;
            selection-background-color: #3182ce;
            selection-color: black;
        }
        QComboBox QAbstractItemView::item {
            min-height: 28px;
            padding: 4px 8px;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #ebf4ff;
        }

        /* 列表和树状视图 (blue) */
        QListWidget, QTreeWidget {
            border: 1px solid #bee3f8;
            border-radius: 6px;
            background-color: white;
            alternate-background-color: #f7fafc;
            color: #2d3748;
        }

        QListWidget::item:selected, QTreeWidget::item:selected {
            background-color: #3182ce;
            color: white;
        }

        /* 表格样式 */
        QTableWidget {
            border: 1px solid #bee3f8;
            border-radius: 6px;
            background-color: white;
            alternate-background-color: #f7fafc;
            color: #2d3748;
        }

        QHeaderView::section {
            background-color: #f7fafc;
            color: #2d3748;
            border: 1px solid #bee3f8;
            padding: 5px;
            font-weight: bold;
        }

        QTableWidget::item:selected {
            background-color: #3182ce;
            color: white;
        }

        /* ======== 框架控件（objectName 驱动） ======== */
        QListWidget#calcNavList {
            border: 1px solid #bee3f8; border-radius: 8px; font-size: 13px;
            padding: 5px 0px; background-color: #f0f7ff; color: #2d3748;
            outline: none;
        }
        QListWidget#calcNavList::item {
            height: 40px; padding-left: 15px; border-bottom: 1px solid #c8ddf0;
            margin: 2px 8px; border-radius: 6px; color: #2d3748;
        }
        QListWidget#calcNavList::item:selected {
            background-color: #4b5cc4; color: white; font-weight: bold;
            border-radius: 6px; outline: none;
        }
        QListWidget#calcNavList::item:hover:!selected {
            background-color: #d8e8f8; color: #1a365d;
        }
        QStackedWidget#calcContentStack {
            background-color: #ffffff; border: 1px solid #bee3f8;
            border-radius: 8px; margin-left: 10px;
        }
        QListWidget#converterNavList {
            border: none; border-right: 1px solid #bee3f8; font-size: 13px;
            background-color: #f0f7ff; color: #2d3748;
        }
        QListWidget#converterNavList::item {
            height: 35px; padding-left: 15px; border-bottom: 1px solid #c8ddf0; color: #2d3748;
        }
        QListWidget#converterNavList::item:selected {
            background-color: #3182ce; color: white; font-weight: bold;
            border-left: 4px solid #2c5282; border-bottom: 1px solid #c8ddf0;
        }
        QListWidget#converterNavList::item:hover:!selected {
            background-color: #d8e8f8;
        }
        QStackedWidget#converterContentStack {
            background-color: #ffffff; border: none;
        }

        /* 计算历史 (blue) */
        QListWidget#historyList {
            border: 1px solid #bee3f8; border-radius: 6px; font-size: 13px;
            background-color: #ffffff; color: #2d3748;
        }
        QListWidget#historyList::item {
            padding: 8px; border-bottom: 1px solid #c8ddf0;
        }
        QListWidget#historyList::item:selected {
            background-color: #3182ce; color: white;
        }
        QListWidget#historyList::item:hover:!selected {
            background-color: #d8e8f8;
        }
        QTextEdit#historyDetailText {
            border: 1px solid #bee3f8; border-radius: 6px; font-size: 13px;
            padding: 8px; background-color: #ffffff; color: #2d3748;
        }

        /* 菜单栏 (blue) */
        QMenuBar {
            background-color: white;
            border-bottom: 1px solid #bee3f8;
            color: #2d3748;
        }
        
        QMenuBar::item {
            padding: 6px 12px;
            background-color: transparent;
        }
        
        QMenuBar::item:selected {
            background-color: #e6f2ff;
        }
        
        /* 状态栏 */
        QStatusBar {
            background-color: white;
            color: #4a5568;
            border-top: 1px solid #bee3f8;
        }
        
        /* 标签 */
        QLabel {
            color: #2d3748;
        }
        
        /* 滚动条 */
        QScrollBar:vertical {
            border: none;
            background-color: #e6f2ff;
            width: 12px;
            margin: 0px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #90cdf4;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #63b3ed;
        }
        """
    
    def set_theme(self, theme_name):
        """设置主题"""
        if theme_name in self.themes:
            self.current_theme = theme_name
            # 同步模块级当前主题，页面在渲染 HTML 时据此取色
            global _ACTIVE_THEME
            _ACTIVE_THEME = theme_name
            self.theme_changed.emit(theme_name)

    def get_content_colors(self, theme_name=None) -> dict:
        """当前主题的 HTML 内容配色（模块级 get_content_colors 的实例版入口）。"""
        return get_content_colors(theme_name or self.current_theme)
    
    def get_theme(self):
        """获取当前主题"""
        return self.themes.get(self.current_theme, self.themes["light"])
    
    def get_theme_names(self):
        """获取所有可用主题名称"""
        return list(self.themes.keys())
    
    def add_theme(self, theme_name, theme_style):
        """添加自定义主题"""
        self.themes[theme_name] = theme_style
    
    def remove_theme(self, theme_name):
        """移除主题（不能移除默认主题）"""
        if theme_name in ["light", "dark", "blue"]:
            return False
        if theme_name in self.themes:
            del self.themes[theme_name]
            return True
        return False