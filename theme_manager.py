# CalcE/theme_manager.py
from PySide6.QtCore import QObject, Signal

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
    
    def get_light_theme(self):
        """浅色主题"""
        return """
        /* 主窗口样式 */
        QMainWindow {
            background-color: #f5f7fa;
        }

        /* 基础控件背景 */
        QWidget {
            background-color: #ffffff;
            color: #374151;
        }

        QScrollArea {
            background-color: #ffffff;
        }
        QScrollArea > QWidget > QWidget {
            background-color: #ffffff;
        }
        
        /* 标签页样式 */
        QTabWidget::pane {
            border: 1px solid #c4c7c5;
            background-color: white;
            border-radius: 8px;
        }
        
        QTabBar::tab {
            background-color: #e1e5e9;
            border: 1px solid #c4c7c5;
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 8px 16px;
            margin-right: 2px;
            min-width: 80px;
            color: #374151;
        }
        
        QTabBar::tab:selected {
            background-color: white;
            border-color: #c4c7c5;
            border-bottom-color: white;
            color: #111827;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #f0f2f5;
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
        
        QPushButton:hover {
            background-color: #3a5a8c;
        }
        
        QPushButton:pressed {
            background-color: #2a4a7c;
        }
        
        QPushButton:disabled {
            background-color: #cccccc;
            color: #666666;
        }
        
        /* 分组框样式 */
        QGroupBox {
            font-weight: bold;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: white;
            color: #374151;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: #4a6fa5;
        }
        
        /* 输入框样式 */
        QLineEdit, QTextEdit, QComboBox {
            border: 1px solid #d1d5db;
            border-radius: 6px;
            padding: 6px 10px;
            background-color: white;
            selection-background-color: #4a6fa5;
            color: #374151;
        }
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
            border-color: #4a6fa5;
        }

        /* QComboBox 下拉列表样式 */
        QComboBox QAbstractItemView {
            background-color: white;
            color: #374151;
            border: 1px solid #d1d5db;
            selection-background-color: #4a6fa5;
            selection-color: black;
        }
        QComboBox QAbstractItemView::item {
            min-height: 28px;
            padding: 4px 8px;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #e8edf2;
        }

        /* 列表和树状视图 */
        QListWidget, QTreeWidget {
            border: 1px solid #d1d5db;
            border-radius: 6px;
            background-color: white;
            alternate-background-color: #f8f9fa;
            color: #374151;
        }
        
        QListWidget::item:selected, QTreeWidget::item:selected {
            background-color: #4a6fa5;
            color: white;
        }
        
        /* 菜单栏 */
        QMenuBar {
            background-color: white;
            border-bottom: 1px solid #e5e7eb;
            color: #374151;
        }
        
        QMenuBar::item {
            padding: 6px 12px;
            background-color: transparent;
        }
        
        QMenuBar::item:selected {
            background-color: #e5e7eb;
        }
        
        /* 状态栏 */
        QStatusBar {
            background-color: white;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
        }
        
        /* 标签 */
        QLabel {
            color: #374151;
        }
        
        /* 滚动条 */
        QScrollBar:vertical {
            border: none;
            background-color: #f0f0f0;
            width: 12px;
            margin: 0px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #c0c0c0;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #a0a0a0;
        }
        """
    
    def get_dark_theme(self):
        """深色主题"""
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
        
        QPushButton:hover {
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
            border: 1px solid #444;
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
        QLineEdit, QTextEdit, QComboBox {
            border: 1px solid #555;
            border-radius: 6px;
            padding: 6px 10px;
            background-color: #333;
            selection-background-color: #4a6fa5;
            color: #e0e0e0;
        }
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
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
        
        /* 菜单栏 */
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
        """蓝色主题"""
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
        
        QPushButton:hover {
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
            border: 1px solid #bee3f8;
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
        QLineEdit, QTextEdit, QComboBox {
            border: 1px solid #bee3f8;
            border-radius: 6px;
            padding: 6px 10px;
            background-color: white;
            selection-background-color: #3182ce;
            color: #2d3748;
        }
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
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

        /* 列表和树状视图 */
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
        
        /* 菜单栏 */
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
            self.theme_changed.emit(theme_name)
    
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