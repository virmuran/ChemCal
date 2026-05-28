"""
ComboBox 辅助工具
- ComboBoxWheelBlocker：阻止 QComboBox 在收起状态时响应鼠标滚轮
"""

from PySide6.QtCore import QObject, QEvent


class ComboBoxWheelBlocker(QObject):
    """事件过滤器：QComboBox 仅在弹出下拉列表时允许鼠标滚轮切换选项。

    用法（每个计算器 __init__ 或 setup_ui 中）：

        self._wheel_blocker = ComboBoxWheelBlocker(self)
        self.some_combo.installEventFilter(self._wheel_blocker)
    """

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            if not obj.view().isVisible():
                return True  # 拦截，滚轮事件不上传给 combo
        return super().eventFilter(obj, event)
