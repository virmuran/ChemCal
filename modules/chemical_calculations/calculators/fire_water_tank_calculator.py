"""
室外消防水池容积计算器

依据 GB 50974-2014 消防给水及消火栓系统技术规范：
  - 计算室外消防用水量 (L/s)
  - 计算室内消防用水量
  - 确定火灾延续时间
  - 计算消防水池有效容积

参考表 3.3.2（室外消火栓设计流量）和表 3.5.2（室内消火栓设计流量）
"""

import math
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QScrollArea,
    QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator

from calculator_base import CalculatorBase
from app_styles import (COMBOBOX_STYLE, SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)
from utils.docx_utils import ReportExporter

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
        self._last_results = {}
        self.setup_ui()
        self.setup_wheel_blocker()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ════════ 左侧输入区 ════════
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet(SCROLL_AREA_STYLE)
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        desc = QLabel(
            "室外消防水池容积计算 — 依据 GB 50974-2014，"
            "按室外/室内消火栓及自动喷淋用水量与火灾延续时间计算水池有效容积。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc)

        self._create_building_group(left_layout)
        self._create_fire_group(left_layout)

        left_layout.addStretch()
        scroll_left.setWidget(left_widget)

        # ════════ 右侧结果区 ════════
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        result_group = CalculatorBase.make_group_box("计算结果")
        rl = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        # 结果框统一标准：边框/背景/文字色交给主题系统，仅指定等宽字体
        self.result_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: 13px;
            } """)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        rl.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # ── 底部按钮行：清空 | DOCX | PDF ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        for label, style, slot in [
            ("清空", CLEAR_BTN_STYLE, self.clear),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        right_layout.addLayout(btn_layout)

        # ── 计算按钮（最底部） ──
        calc_btn = self.make_calc_button("计 算")
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)

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
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(INPUT_LABEL_STYLE)
        grid.addWidget(lbl, row, 0)
        le = QLineEdit(default)
        if vld:
            le.setValidator(vld)
        grid.addWidget(le, row, 1)
        unit_lbl = QLabel(unit)
        unit_lbl.setStyleSheet("font-style: italic;")
        grid.addWidget(unit_lbl, row, 2)
        return le

    def _create_building_group(self, parent):
        group = CalculatorBase.make_group_box("建筑参数")
        grid = self._add_grid(group)

        lbl1 = QLabel("建筑类型")
        lbl1.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl1.setStyleSheet(INPUT_LABEL_STYLE)
        grid.addWidget(lbl1, 0, 0)
        self.inputs["building_type"] = QComboBox()
        self.inputs["building_type"].addItems(list(BUILDING_TYPES.keys()))
        self.inputs["building_type"].setStyleSheet(COMBOBOX_STYLE)
        grid.addWidget(self.inputs["building_type"], 0, 1, 1, 2)

        lbl2 = QLabel("室内消火栓等级")
        lbl2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl2.setStyleSheet(INPUT_LABEL_STYLE)
        grid.addWidget(lbl2, 1, 0)
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

        # ⚠ 关键：必须把组框加进布局，否则函数返回后组框连同子控件被 GC 删除
        parent.addWidget(group)

    def _create_fire_group(self, parent):
        group = CalculatorBase.make_group_box("消防参数")
        grid = self._add_grid(group)

        lbl3 = QLabel("火灾类别")
        lbl3.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl3.setStyleSheet(INPUT_LABEL_STYLE)
        grid.addWidget(lbl3, 0, 0)
        self.inputs["fire_category"] = QComboBox()
        self.inputs["fire_category"].addItems(list(FIRE_DURATION.keys()))
        self.inputs["fire_category"].setStyleSheet(COMBOBOX_STYLE)
        grid.addWidget(self.inputs["fire_category"], 0, 1, 1, 2)

        self.inputs["sprinkler_flow"] = self._add_row(
            grid, 1, "自动喷淋流量", "30",
            "L/s（无喷淋填0）", QDoubleValidator(0, 200, 1))

        self.inputs["sprinkler_duration"] = self._add_row(
            grid, 2, "喷淋延续时间", "1",
            "h", QDoubleValidator(0.5, 3, 1))

        self.inputs["safety_factor"] = self._add_row(
            grid, 3, "安全系数", "1.1",
            "—", QDoubleValidator(1.0, 1.5, 2))

        # ⚠ 关键：必须把组框加进布局，否则函数返回后组框连同子控件被 GC 删除
        parent.addWidget(group)

    # ── 默认值表（清空时复位） ──
    DEFAULTS = {
        "building_volume": "10000",
        "building_height": "12",
        "sprinkler_flow": "30",
        "sprinkler_duration": "1",
        "safety_factor": "1.1",
    }

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
            Q_sprinkler = float(self.inputs["sprinkler_flow"].text() or 0)
            T_sprinkler = float(self.inputs["sprinkler_duration"].text() or 1)
            safety = float(self.inputs["safety_factor"].text() or 1.1)

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

            self._last_results = {
                "building_type": bld_type,
                "indoor_type": indoor_type,
                "fire_category": fire_cat,
                "building_volume": self.inputs["building_volume"].text(),
                "building_height": self.inputs["building_height"].text(),
                "q_outdoor": Q_outdoor,
                "q_indoor": Q_indoor,
                "t_fire": T_fire,
                "q_sprinkler": Q_sprinkler,
                "t_sprinkler": T_sprinkler,
                "safety": safety,
                "v_outdoor": V_outdoor,
                "v_indoor": V_indoor,
                "v_sprinkler": V_sprinkler,
                "v_total": V_total,
            }

        except Exception as e:
            QMessageBox.critical(self, "计算错误", str(e))

    def clear(self):
        for key, w in self.inputs.items():
            if isinstance(w, QLineEdit):
                w.setText(self.DEFAULTS.get(key, ""))
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(0)
        self.result_text.clear()
        self._last_results = {}

    def _get_history_data(self):
        """提供历史记录数据"""
        r = self._last_results
        if not r:
            return {"inputs": {}, "outputs": {}}
        return {
            "inputs": {
                "建筑类型": r.get("building_type", ""),
                "室内消火栓等级": r.get("indoor_type", ""),
                "火灾类别": r.get("fire_category", ""),
                "建筑体积_m3": r.get("building_volume", ""),
                "建筑高度_m": r.get("building_height", ""),
                "喷淋流量_L_s": r.get("q_sprinkler", 0),
                "喷淋延续时间_h": r.get("t_sprinkler", 0),
                "安全系数": r.get("safety", 0),
            },
            "outputs": {
                "水池有效容积_m3": round(r.get("v_total", 0), 1),
                "室外消防用水量_L_s": r.get("q_outdoor", 0),
                "室内消防用水量_L_s": r.get("q_indoor", 0),
                "火灾延续时间_h": r.get("t_fire", 0),
            }
        }

    # ═══════════════════════ 报告 ═══════════════════════
    def get_project_info(self):
        """获取工程信息 - 返回 dict"""
        try:
            saved_info = {}
            if self.data_manager:
                saved_info = self.data_manager.get_project_info()
            return {
                'company_name': saved_info.get('company_name', ''),
                'project_number': saved_info.get('project_number', ''),
                'project_name': saved_info.get('project_name', ''),
                'subproject_name': saved_info.get('subproject_name', ''),
                'report_number': ''
            }
        except Exception as e:
            print(f"获取工程信息失败: {e}")
            return {}

    def generate_report(self):
        """生成计算书文本（str）"""
        try:
            result_text = self.result_text.toPlainText()
            if not result_text or ("水池有效容积" not in result_text):
                return None

            project_info = self.get_project_info()
            report = f"""══════════════════════════════════════════
          消防水池容积计算计算书
══════════════════════════════════════════

{result_text}

══════════════════════════════════════════
 工程信息
══════════════════════════════════════════

  公司名称: {project_info.get('company_name', '')}
  工程编号: {project_info.get('project_number', '')}
  工程名称: {project_info.get('project_name', '')}
  子项名称: {project_info.get('subproject_name', '')}
  计算日期: {datetime.now().strftime('%Y-%m-%d')}

══════════════════════════════════════════
备注说明
══════════════════════════════════════════

  1. 计算依据 GB 50974-2014 表 3.3.2（室外）及表 3.5.2（室内）消火栓设计流量
  2. 消防用水量 V = Q(L/s) × t(h) × 3.6，含安全系数
  3. 建议水池尺寸为初步估算，实际设计需结合总图布置及结构专业确认

---
生成于 ChemCal 工程计算模块
"""
            return report

        except Exception as e:
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "消防水池容积")

    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "消防水池容积")

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = FireWaterTankCalculator()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
