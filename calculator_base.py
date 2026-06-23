"""
ChemCal 计算器基类

所有计算器均可继承此类获得：
  - init_data_manager()：数据管理器注入
  - setup_wheel_blocker()：QComboBox 滚轮拦截
  - download_docx_report() / download_pdf_report()：报告导出
  - 公共样式常量引用
"""

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QWidget, QComboBox
from PySide6.QtCore import Qt

# 确保项目根在 sys.path 中（兼容动态加载）
_root = str(Path(__file__).parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from utils.docx_utils import ReportExporter
from modules.combo_box_utils import ComboBoxWheelBlocker
from app_styles import (
    COMBOBOX_STYLE, GROUP_STYLE, CALC_BUTTON_STYLE,
    MODE_BUTTON_STYLE, SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
    CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE,
)


class CalculatorBase(QWidget):
    """计算器基类"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = None
        self._wheel_blocker = None
        if data_manager is not None:
            self.init_data_manager(data_manager)

    # ── 数据管理器 ────────────────────────────────────────────

    def init_data_manager(self, data_manager=None):
        """初始化数据管理器（单例模式）"""
        if data_manager is not None:
            self.data_manager = data_manager
            return
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception:
            self.data_manager = None

    # ── ComboBox 滚轮拦截 ──────────────────────────────────────

    def setup_wheel_blocker(self):
        """拦截所有 QComboBox 的鼠标滚轮事件"""
        self._wheel_blocker = ComboBoxWheelBlocker(self)
        for combo in self.findChildren(QComboBox):
            combo.installEventFilter(self._wheel_blocker)

    # ── 报告导出 ──────────────────────────────────────────────

    def download_docx_report(self, title=None):
        """生成 DOCX 计算书"""
        t = title or self.__class__.__name__
        ReportExporter.export_docx(self, t)

    def download_pdf_report(self, title=None):
        """生成 PDF 计算书"""
        t = title or self.__class__.__name__
        ReportExporter.export_pdf(self, t)

    # ── 模式按钮组工具 ────────────────────────────────────────

    @staticmethod
    def make_mode_button(text, tooltip=""):
        """创建可选中模式按钮，并应用 MODE_BUTTON_STYLE"""
        from PySide6.QtWidgets import QPushButton
        from PySide6.QtWidgets import QSizePolicy
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setToolTip(tooltip)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setStyleSheet(MODE_BUTTON_STYLE)
        return btn

    @staticmethod
    def make_calc_button(text="计 算"):
        """创建计算按钮，应用 CALC_BUTTON_STYLE"""
        from PySide6.QtWidgets import QPushButton
        from PySide6.QtWidgets import QSizePolicy
        btn = QPushButton(text)
        btn.setMinimumHeight(50)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setStyleSheet(CALC_BUTTON_STYLE)
        return btn

    @staticmethod
    def make_combo_box():
        """创建带 COMBOBOX_STYLE 的 QComboBox"""
        from PySide6.QtWidgets import QComboBox
        cb = QComboBox()
        cb.setStyleSheet(COMBOBOX_STYLE)
        return cb

    @staticmethod
    def make_group_box(title):
        """创建带 GROUP_STYLE 的 QGroupBox"""
        from PySide6.QtWidgets import QGroupBox
        gb = QGroupBox(title)
        gb.setStyleSheet(GROUP_STYLE)
        return gb
