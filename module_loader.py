# ChemCal/module_loader.py
import importlib
import traceback
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PySide6.QtCore import Qt


class ModuleLoader:
    """模块加载器 - 统一管理模块的动态导入和初始化"""

    @staticmethod
    def load_module(module_path: str, class_name: str, parent=None, data_manager=None):
        """
        动态加载模块并实例化。
        :param module_path: 模块路径，如 "modules.history_viewer"
        :param class_name: 类名，如 "HistoryViewer"
        :param parent: Qt 父部件
        :param data_manager: DataManager 实例
        :return: 模块实例（加载失败时返回错误部件）
        """
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            return cls(parent, data_manager) if data_manager is not None else cls(parent)
        except Exception as e:
            print(f"[ModuleLoader] 加载失败: {module_path}.{class_name} — {e}")
            traceback.print_exc()
            return ModuleLoader.create_error_widget(f"模块加载失败: {module_path}", str(e))

    @staticmethod
    def create_error_widget(title: str, error_msg: str) -> QWidget:
        """创建模块加载失败时的占位部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        title_label = QLabel(f"{title}")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: red; font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)

        detail = QTextEdit()
        detail.setPlainText(f"错误详情:\n{error_msg}")
        detail.setReadOnly(True)
        detail.setStyleSheet(
            "QTextEdit { background: #f8f9fa; border: 1px solid #e9ecef; "
            "border-radius: 5px; padding: 10px; font-family: monospace; font-size: 10px; }"
        )
        layout.addWidget(detail)

        hint = QLabel("请检查：1. 模块文件是否存在  2. 是否有语法错误  3. 依赖是否安装")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: gray; font-size: 12px; padding: 10px;")
        layout.addWidget(hint)

        return widget
