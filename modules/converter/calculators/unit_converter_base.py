# -*- coding: utf-8 -*-
"""换算器通用基类 —— 新换算器只声明数据，不写布局、也不写换算循环。

为什么要它：原有 11 个换算器每个约 150 行，真正有用的只有一张单位表，其余
"两列网格布局 + 清空其他格 + 逐格换算"逐字重复了 11 遍 —— 一处写错（例如清空时
忘了 blockSignals）就要改 11 个文件。这里把重复部分收敛进基类，新换算器只剩一张表：

    class FlowConverter(UnitConverterPage):
        TITLE = "流量换算"
        NOTE = "..."
        AUX_FIELDS = [("rho", "密度 (kg/m³)", 1000, "默认水 1000")]
        UNITS = [
            ("立方米/小时 (m³/h)", "m3_h", 1 / 3600),
            ("千克/小时 (kg/h)", "kg_h", factor_over_aux("rho", 1 / 3600)),
        ]

单位表每项四选一：
    (显示名, 代号, 系数)              系数 = 1 个该单位等于多少个基准单位
    (显示名, 代号, 系数函数)          系数函数(aux) -> float；返回 None 表示"当前不可换算"（留空）
    (显示名, 代号, 转基准, 反基准)    非线性单位（如 °API、波美度）
    (显示名, 代号, 函数对)            直接放 unit_in_aux() 的返回值（跨组换算，需辅助参数）

与既有 11 个换算器保持一致的交互约定：
    · 任一格输入 → 实时换算其余全部；清空某格 → 其余全部清空
    · 辅助参数（密度、摩尔质量）改动后，按上一次的输入自动重算
    · 一律不写颜色，交给主题 QSS（深色主题下才不会"深底压深字"）
"""
import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QScrollArea, QVBoxLayout, QWidget)


# ------------------------------------------------------------------ 系数工厂

def unit_in_aux(key, k):
    """"数值 × k × aux[key]"式的单位（如 质量分数 × 密度 = 质量浓度）。

    辅助参数缺失时返回 None → 该格留空，不显示错误数字。
    """
    def to_base(value, aux):
        f = aux.get(key)
        return None if f is None else value * k * f

    def from_base(base, aux):
        f = aux.get(key)
        if f is None or f == 0 or k == 0:
            return None
        return base / (k * f)

    return to_base, from_base


def factor_over_aux(key, k):
    """系数 = k / aux[key] 的单位（如 质量流量 → 体积流量需要除以密度）。"""
    def factor(aux):
        a = aux.get(key)
        if not a:
            return None
        return k / a

    return factor


# ------------------------------------------------------------------ 基类

class UnitConverterPage(QWidget):
    """单位换算页通用实现。子类只声明类属性。"""

    TITLE = ""
    UNITS = ()
    AUX_FIELDS = ()          # [(键, 标签, 默认值, 占位提示)]
    NOTE = ""                # 顶部说明（次要色，自动换行）
    COLUMNS = 2
    LABEL_WIDTH = 140
    ENTRY_WIDTH = 170
    VALUE_FMT = "{:.6g}"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.unit_vars = {}
        self.aux_widgets = {}
        self._last_input = None      # (来源单位, 原始文本)，供辅助参数变化后重算
        self.setup_ui()

    # ── 布局 ──────────────────────────────────────────────
    def setup_ui(self):
        root = QVBoxLayout(self)
        self._build_header(root)
        root.addWidget(self._build_units(), 1)
        # 所有控件建好之后再连信号：槽函数要用到 unit_vars / aux_widgets，
        # 先连信号会在 setText 时打到尚未创建的控件上（异常被 Qt 吞掉，表现为静默失效）
        for code, entry in self.unit_vars.items():
            entry.textChanged.connect(
                lambda text, c=code: self.on_unit_input(text, c))
        for entry in self.aux_widgets.values():
            entry.textChanged.connect(self._on_aux_changed)

    def _build_header(self, root):
        if self.NOTE:
            note = QLabel(self.NOTE)
            note.setWordWrap(True)
            note.setObjectName("mutedLabel")     # 颜色由主题提供
            root.addWidget(note)
        for key, label_text, default, tip in self.AUX_FIELDS:
            row = QFrame()
            row.setFrameStyle(QFrame.NoFrame)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(5, 2, 5, 2)
            row_layout.setSpacing(10)

            label = QLabel(label_text)
            label.setFixedWidth(self.LABEL_WIDTH)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label.setObjectName("mutedLabel")
            row_layout.addWidget(label)

            entry = QLineEdit()
            entry.setFixedWidth(self.ENTRY_WIDTH)
            if default not in ("", None):
                entry.setText(str(default))
            if tip:
                entry.setPlaceholderText(tip)
            row_layout.addWidget(entry)
            row_layout.addStretch()

            root.addWidget(row)
            self.aux_widgets[key] = entry

    def _build_units(self):
        scroll_area = QScrollArea()
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setSpacing(5)

        units = list(self.UNITS)
        columns = max(1, int(self.COLUMNS))
        per_column = math.ceil(len(units) / columns) or 1
        for index, unit in enumerate(units):
            frame, entry = self._make_row(unit[0])
            grid.addWidget(frame, index % per_column, index // per_column)
            self.unit_vars[unit[1]] = entry

        for col in range(columns):
            grid.setColumnStretch(col, 1)
        grid.setHorizontalSpacing(15)

        scroll_area.setWidget(inner)
        scroll_area.setWidgetResizable(True)
        return scroll_area

    def _make_row(self, display_name):
        frame = QFrame()
        frame.setFrameStyle(QFrame.NoFrame)
        row = QHBoxLayout(frame)
        row.setContentsMargins(5, 2, 5, 2)
        row.setSpacing(10)

        label = QLabel(display_name)
        label.setFixedWidth(self.LABEL_WIDTH)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        entry = QLineEdit()
        entry.setFixedWidth(self.ENTRY_WIDTH)

        row.addWidget(label)
        row.addWidget(entry)
        return frame, entry

    # ── 换算核心 ──────────────────────────────────────────
    def aux_values(self):
        """辅助参数的数值；空或非法一律 None（不猜、不默认）。"""
        values = {}
        for key, entry in self.aux_widgets.items():
            text = (entry.text() or "").strip()
            try:
                value = float(text)
            except ValueError:
                values[key] = None
                continue
            values[key] = value if math.isfinite(value) else None
        return values

    def _spec(self, code):
        for unit in self.UNITS:
            if unit[1] == code:
                return unit
        return None

    def _pair(self, code, aux):
        """把单位表解析成 (转基准, 反基准) 两个函数；当前不可换算时返回 (None, None)。

        第 3 项允许三种写法，全部归一到这里 —— 新换算器不该被写法绊住：
            · 数字                    线性系数（1 个该单位 = 多少个基准单位）
            · 系数函数 factor(aux)    系数依赖辅助参数；返回 None 表示当前不可换算
            · (转, 反) 两个函数       非线性（°API/波美度）或跨组（unit_in_aux 的返回值）
        最后一种此前没被识别到，导致 unit_in_aux 的换算器一调用就
        "元组除浮点"报错 —— 已在此统一处理，两种写法（内联或 * 展开）都支持。
        """
        unit = self._spec(code)
        if unit is None:
            return None, None
        if len(unit) >= 4:                       # (名, 代号, 转基准, 反基准)
            return unit[2], unit[3]
        spec = unit[2]
        if isinstance(spec, tuple):              # unit_in_aux() 直接写在第 3 项
            return spec[0], spec[1]
        factor = spec(aux) if callable(spec) else spec
        if not factor:
            return None, None
        return (lambda v, a: v * factor), (lambda b, a: b / factor)

    def to_base(self, code, value):
        """某单位的数值 → 基准单位数值；当前不可换算时返回 None。"""
        aux = self.aux_values()
        to_base, _unused = self._pair(code, aux)
        return None if to_base is None else to_base(value, aux)

    def from_base(self, code, base):
        """基准单位数值 → 某单位的数值；当前不可换算时返回 None。"""
        aux = self.aux_values()
        _unused, from_base = self._pair(code, aux)
        return None if from_base is None else from_base(base, aux)

    def do_conversion(self, value, from_unit, to_unit):
        """换算（供测试与外部调用）。"""
        base = self.to_base(from_unit, value)
        if base is None:
            return None
        return self.from_base(to_unit, base)

    def on_unit_input(self, text, source_unit):
        """某个输入框被编辑 —— 实时换算其余全部单位。"""
        self._last_input = (source_unit, text or "")
        source = (text or "").strip()

        base = None
        if source:
            try:
                value = float(source)
            except ValueError:
                return                       # 输入到一半（如 "1e-"）不打断
            if not math.isfinite(value):
                return                       # nan / inf 由 float() 放行，必须挡掉
            base = self.to_base(source_unit, value)

        for code, entry in self.unit_vars.items():
            if code == source_unit:
                continue
            result = None if base is None else self.from_base(code, base)
            if result is not None and not math.isfinite(result):
                result = None                # 除零等异常结果留空，不显示 inf
            entry.blockSignals(True)
            entry.setText("" if result is None else self.VALUE_FMT.format(result))
            entry.blockSignals(False)

    def _on_aux_changed(self, *_):
        """辅助参数变了 —— 按上一次的输入重算（否则页面会停留在旧结果）。"""
        if self._last_input:
            code, text = self._last_input
            self.on_unit_input(text, code)

    def clear_all(self):
        """清空全部输入（辅助参数保持原值，便于连续换算）。"""
        for entry in self.unit_vars.values():
            entry.blockSignals(True)
            entry.setText("")
            entry.blockSignals(False)
        self._last_input = None
