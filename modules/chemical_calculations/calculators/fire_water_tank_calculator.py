"""
室外消防水池容积计算器

依据 GB 50974-2014 消防给水及消火栓系统技术规范：
  - 计算室外消防用水量 (L/s)
  - 计算室内消防用水量
  - 确定火灾延续时间
  - 计算消防水池有效容积

参考表 3.3.2（室外消火栓设计流量）和表 3.5.2（室内消火栓设计流量）
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QScrollArea,
    QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator

from calculator_base import CalculatorBase
from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, SCROLL_AREA_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

# ── 建筑类型 → 室外消防用水量 (L/s) ──
# 依据 GB 50974 表 3.3.2
BUILDING_TYPES = {
    "甲/乙类厂房（V≤3000m³）": 15,
    "甲/乙类厂房（3000<V≤5000）": 20,
    "甲/乙类厂房（5000<V≤20000）": 30,
    "甲/乙类厂房（20000<V≤50000）": 35,
    "甲/乙类厂房（V>50000）": 45,
    "丙类厂房（V≤5000）": 20,
    "丙类厂房（5000<V≤20000）": 30,
    "丙类厂房（20000<V≤50000）": 40,
    "丙类厂房（V>50000）": 45,
    "丁/戊类厂房": 15,
    "仓库（甲/乙类）": 25,
    "仓库（丙类）": 35,
    "仓库（丁/戊类）": 20,
    "民用建筑（高层）": 40,
    "民用建筑（多层）": 25,
    "罐区": 45,
}

# ── 室内消防用水量 (L/s) ──
# 依据 GB 50974 表 3.5.2
INDOOR_FIRE_FLOW = {
    "无室内消火栓": 0,
    "丙类厂房（h≤24m,V≤5000）": 10,
    "丙类厂房（h≤24m,V>5000）": 20,
    "丙类厂房（24<h≤50）": 30,
    "丙类厂房（h>50）": 40,
    "丁/戊类厂房": 10,
    "仓库": 15,
    "高层民用建筑": 40,
    "多层民用建筑": 15,
}

# ── 火灾延续时间 (h) ──
FIRE_DURATION = {
    "甲/乙/丙类厂房": 3,
    "丁/戊类厂房": 2,
    "仓库（甲/乙/丙类）": 3,
    "仓库（丁/戊类）": 2,
    "民用建筑": 2,
    "罐区": 4,
}


class FireWaterTankCalculator(CalculatorBase):
    """室外消防水池容积计算器"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent, data_manager)
        self.inputs = {}
        self.setup_ui()
        self.setup_wheel_blocker()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(SCROLL_AREA_STYLE)
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(12)

        self._create_building_group(left_layout)
        self._create_fire_group(left_layout)

        calc_btn = QPushButton("计  算")
        calc_btn.setStyleSheet(CALC_BUTTON_STYLE)
        calc_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calc_btn.setMinimumHeight(50)
        calc_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        calc_btn.clicked.connect(self.calculate)
        left_layout.addWidget(calc_btn)
        left_layout.addStretch()
        scroll_left.setWidget(left_widget)

        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(12)

        result_group = QGroupBox("计算结果")
        result_group.setStyleSheet(GROUP_STYLE)
        rl = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setStyleSheet("font-size: 13px; font-family: Consolas, 'Microsoft YaHei';")
        rl.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        for label, style, slot in [
            ("清空", CLEAR_BTN_STYLE, self.clear),
            ("DOCX", DOCX_BTN_STYLE, self._on_download_txt),
            ("PDF", PDF_BTN_STYLE, self._on_download_pdf),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        right_layout.addLayout(btn_layout)

        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

    def _add_grid(self, parent):
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)
        parent.setLayout(grid)
        return grid

    def _add_row(self, grid, row, label, default, unit, vld=None):
        grid.addWidget(QLabel(label), row, 0)
        le = QLineEdit(default)
        if vld:
            le.setValidator(vld)
        grid.addWidget(le, row, 1)
        grid.addWidget(QLabel(unit), row, 2)
        return le

    def _create_building_group(self, parent):
        group = QGroupBox("建筑参数")
        group.setStyleSheet(GROUP_STYLE)
        grid = self._add_grid(group)

        grid.addWidget(QLabel("建筑类型"), 0, 0)
        self.inputs["building_type"] = QComboBox()
        self.inputs["building_type"].addItems(list(BUILDING_TYPES.keys()))
        self.inputs["building_type"].setStyleSheet(COMBOBOX_STYLE)
        grid.addWidget(self.inputs["building_type"], 0, 1, 1, 2)

        grid.addWidget(QLabel("室内消火栓等级"), 1, 0)
        self.inputs["indoor_type"] = QComboBox()
        self.inputs["indoor_type"].addItems(list(INDOOR_FIRE_FLOW.keys()))
        self.inputs["indoor_type"].setStyleSheet(COMBOBOX_STYLE)
        grid.addWidget(self.inputs["indoor_type"], 1, 1, 1, 2)

        self.inputs["building_volume"] = self._add_row(
            grid, 2, "建筑体积", "10000",
            "m³", QDoubleValidator(100, 1e6, 1))

        self.inputs["building_height"] = self._add_row(
            grid, 3, "建筑高度 h", "12",
            "m", QDoubleValidator(2, 300, 1))

    def _create_fire_group(self, parent):
        group = QGroupBox("消防参数")
        group.setStyleSheet(GROUP_STYLE)
        grid = self._add_grid(group)

        grid.addWidget(QLabel("火灾类别"), 2, 0)
        self.inputs["fire_category"] = QComboBox()
        self.inputs["fire_category"].addItems(list(FIRE_DURATION.keys()))
        self.inputs["fire_category"].setStyleSheet(COMBOBOX_STYLE)
        grid.addWidget(self.inputs["fire_category"], 2, 1, 1, 2)

        self.inputs["sprinkler_flow"] = self._add_row(
            grid, 3, "自动喷淋流量", "30",
            "L/s（无喷淋填0）", QDoubleValidator(0, 200, 1))

        self.inputs["sprinkler_duration"] = self._add_row(
            grid, 4, "喷淋延续时间", "1",
            "h", QDoubleValidator(0.5, 3, 1))

        self.inputs["safety_factor"] = self._add_row(
            grid, 5, "安全系数", "1.1",
            "—", QDoubleValidator(1.0, 1.5, 2))

    def calculate(self):
        try:
            bld_type = self.inputs["building_type"].currentText()
            indoor_type = self.inputs["indoor_type"].currentText()
            fire_cat = self.inputs["fire_category"].currentText()

            # 室外消防用水量
            Q_outdoor = BUILDING_TYPES.get(bld_type, 25)

            # 室内消火栓用水量
            Q_indoor = INDOOR_FIRE_FLOW.get(indoor_type, 0)

            # 火灾延续时间
            T_fire = FIRE_DURATION.get(fire_cat, 2)

            # 喷淋
            Q_sprinkler = float(self.inputs["sprinkler_flow"].text())
            T_sprinkler = float(self.inputs["sprinkler_duration"].text())
            safety = float(self.inputs["safety_factor"].text())

            # 消防水量 (m³) = 流量(L/s) × 时间(h) × 3.6
            V_outdoor = Q_outdoor * T_fire * 3.6
            V_indoor = Q_indoor * T_fire * 3.6
            V_sprinkler = Q_sprinkler * T_sprinkler * 3.6

            V_total = (V_outdoor + V_indoor + V_sprinkler) * safety

            lines = []
            lines.append("═══ 消防水池容积计算 ═══")
            lines.append(f"依据: GB 50974-2014 消防给水及消火栓系统技术规范")
            lines.append(f"")
            lines.append(f"【设计参数】")
            lines.append(f"  建筑类型: {bld_type}")
            lines.append(f"  建筑体积: {self.inputs['building_volume'].text()} m³")
            lines.append(f"  建筑高度: {self.inputs['building_height'].text()} m")
            lines.append(f"  火灾类别: {fire_cat}")
            lines.append(f"  火灾延续时间: {T_fire} h")
            lines.append(f"")
            lines.append(f"【消防用水量】")
            lines.append(f"  室外消火栓: Q={Q_outdoor} L/s × {T_fire}h = {V_outdoor:.0f} m³")
            lines.append(f"  室内消火栓: Q={Q_indoor} L/s × {T_fire}h = {V_indoor:.0f} m³")
            lines.append(f"  自动喷淋:   Q={Q_sprinkler:.0f} L/s × {T_sprinkler}h = {V_sprinkler:.0f} m³")
            lines.append(f"")
            lines.append(f"【水池容积】")
            lines.append(f"  设计用水量: {V_outdoor + V_indoor + V_sprinkler:.0f} m³")
            lines.append(f"  安全系数: {safety:.2f}")
            lines.append(f"  水池有效容积: {V_total:.0f} m³")
            lines.append(f"")
            lines.append(f"  建议水池尺寸 (L×W×H):")
            vol = V_total
            if vol <= 100:
                lines.append(f"    5m × 5m × {max(2, math.ceil(vol/25*10)/10):.1f}m")
            elif vol <= 500:
                lines.append(f"    10m × 8m × {max(3, math.ceil(vol/80*10)/10):.1f}m")
            else:
                lines.append(f"    15m × 10m × {max(4, math.ceil(vol/150*10)/10):.1f}m")

            self.result_text.setText("\n".join(lines))

        except Exception as e:
            QMessageBox.critical(self, "计算错误", str(e))

    def clear(self):
        for w in self.inputs.values():
            if isinstance(w, QLineEdit):
                w.clear()
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(0)
        self.result_text.clear()

    def _get_history_data(self):
        return {"inputs": {}, "outputs": {}}

    def generate_report(self):
        return self.result_text.toPlainText()

    def _on_download_txt(self):
        import os
        from datetime import datetime
        self.download_docx_report(
            self.generate_report(),
            os.path.join(os.path.expanduser("~"), "Desktop",
                         f"消防水池_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"))

    def _on_download_pdf(self):
        import os
        from datetime import datetime
        self.download_pdf_report(
            self.generate_report(),
            os.path.join(os.path.expanduser("~"), "Desktop",
                         f"消防水池_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"))
