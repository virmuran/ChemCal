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

# ══ 室外消火栓设计流量 (L/s)，依据 GB 50974-2014 表3.3.2（一、二级耐火等级）══
# 每类为 [(体积上限_m3, 流量), ...]，None 表示规范未规定（需另行确定）
OUTDOOR_FLOW_TIERS = {
    "厂房（甲/乙类）": [(1500, 15), (3000, 20), (5000, 25), (20000, 25), (50000, 30), (float("inf"), 35)],
    "厂房（丙类）": [(1500, 15), (3000, 20), (5000, 20), (20000, 25), (50000, 30), (float("inf"), 40)],
    "厂房（丁/戊类）": [(1500, 15), (float("inf"), 20)],
    "仓库（甲/乙类）": [(1500, 15), (3000, 25), (float("inf"), None)],
    "仓库（丙类）": [(1500, 15), (3000, 25), (20000, 25), (50000, 35), (float("inf"), 45)],
    "仓库（丁/戊类）": [(1500, 15), (float("inf"), 20)],
    "民用建筑（住宅）": [(float("inf"), 15)],
    "民用建筑（公共，单层及多层）": [(1500, 15), (3000, 25), (20000, 25), (50000, 30), (float("inf"), 40)],
    "民用建筑（公共，高层）": [(1500, None), (3000, 25), (20000, 30), (50000, 40), (float("inf"), 40)],
    "地下建筑（含地铁）/人防工程": [(1500, 15), (3000, 20), (20000, 25), (float("inf"), 30)],
    "汽车库/修车库（独立）": [(1500, 15), (float("inf"), 20)],
}

# ══ 室内消火栓设计流量 (L/s)，依据 GB 50974-2014 表3.5.2（按建筑高度分档）══
# 每类为 [(高度上限_m, 流量), ...]，同时给出规范同时使用水枪数
INDOOR_FLOW_TIERS = {
    "无室内消火栓": {"tiers": [(float("inf"), 0)], "guns": 0},
    "厂房（甲/乙/丁/戊类）": {"tiers": [(24, 10), (50, 25), (float("inf"), 25)], "guns": 2},
    "厂房（丙类）": {"tiers": [(24, 20), (50, 30), (float("inf"), 40)], "guns": 4},
    "仓库（甲/乙/丁/戊类）": {"tiers": [(24, 10), (float("inf"), 30)], "guns": 2},
    "仓库（丙类）": {"tiers": [(24, 20), (float("inf"), 40)], "guns": 4},
    "民用建筑（高层）": {"tiers": [(50, 30), (float("inf"), 40)], "guns": 6},
    "民用建筑（多层）": {"tiers": [(float("inf"), 15)], "guns": 2},
}

# ── 火灾延续时间 (h)，依据 GB 50974-2014 表3.6.2 ──
FIRE_DURATION = {
    "甲/乙/丙类厂房": 3,
    "丁/戊类厂房": 2,
    "仓库（甲/乙/丙类）": 3,
    "仓库（丁/戊类）": 2,
    "民用建筑": 2,
    "罐区": 4,  # 简化取值：罐区应按表3.4.2-3/3.4.5-2及对应延续时间另行计算
}


def _tier_lookup(tiers, value):
    """按 [(上限, 流量), ...] 查流量；None 表示规范未规定"""
    for upper, flow in tiers:
        if value <= upper:
            return flow
    return tiers[-1][1]


class FireWaterTankCalculator(CalculatorBase):
    """室外消防水池容积计算器"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent, data_manager)
        self.inputs = {}
        self._last_results = {}
        self.setup_ui()
        self.setup_wheel_blocker()
        # 建筑类型 → 火灾类别（火灾延续时间）自动联动，表3.6.2
        self.inputs["building_type"].currentTextChanged.connect(self._on_building_type_changed)
        self._on_building_type_changed(self.inputs["building_type"].currentText())

    def _on_building_type_changed(self, bld_type):
        mapping = {
            "厂房（甲/乙类）": "甲/乙/丙类厂房",
            "厂房（丙类）": "甲/乙/丙类厂房",
            "厂房（丁/戊类）": "丁/戊类厂房",
            "仓库（甲/乙类）": "仓库（甲/乙/丙类）",
            "仓库（丙类）": "仓库（甲/乙/丙类）",
            "仓库（丁/戊类）": "仓库（丁/戊类）",
        }
        fire_cat = mapping.get(bld_type, "民用建筑")
        if fire_cat in FIRE_DURATION:
            self.inputs["fire_category"].setCurrentText(fire_cat)

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
        self.inputs["building_type"].addItems(list(OUTDOOR_FLOW_TIERS.keys()))
        self.inputs["building_type"].setStyleSheet(COMBOBOX_STYLE)
        grid.addWidget(self.inputs["building_type"], 0, 1, 1, 2)

        lbl2 = QLabel("室内消火栓类别")
        lbl2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl2.setStyleSheet(INPUT_LABEL_STYLE)
        grid.addWidget(lbl2, 1, 0)
        self.inputs["indoor_type"] = QComboBox()
        self.inputs["indoor_type"].addItems(list(INDOOR_FLOW_TIERS.keys()))
        self.inputs["indoor_type"].setStyleSheet(COMBOBOX_STYLE)
        self.inputs["indoor_type"].setCurrentText("厂房（丙类）")
        grid.addWidget(self.inputs["indoor_type"], 1, 1, 1, 2)

        self.inputs["building_volume"] = self._add_row(
            grid, 2, "建筑总体积 V（含地下室）", "10000",
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
            grid, 3, "工程安全余量（非规范要求）", "1.1",
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

            building_volume = float(self.inputs["building_volume"].text() or 10000)
            building_height = float(self.inputs["building_height"].text() or 12)

            # 室外消防用水量（表3.3.2，按建筑总体积查档）
            Q_outdoor = _tier_lookup(OUTDOOR_FLOW_TIERS.get(bld_type, []), building_volume)

            # 室内消火栓用水量（表3.5.2，按建筑高度查档）
            indoor_cfg = INDOOR_FLOW_TIERS.get(indoor_type, INDOOR_FLOW_TIERS["无室内消火栓"])
            Q_indoor = _tier_lookup(indoor_cfg["tiers"], building_height)
            indoor_guns = indoor_cfg["guns"]

            # 火灾延续时间（表3.6.2）
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
            lines.append(f"  建筑总体积: {building_volume:.0f} m³（表3.3.2 查档依据）")
            lines.append(f"  建筑高度: {building_height:.1f} m（表3.5.2 查档依据）")
            lines.append(f"  室内消火栓类别: {indoor_type}")
            lines.append(f"  火灾类别: {fire_cat}")
            lines.append(f"  火灾延续时间: {T_fire} h（表3.6.2）")
            lines.append(f"")
            lines.append(f"【消防用水量】")
            lines.append(f"  室外消火栓: Q={Q_outdoor} L/s × {T_fire}h = {V_outdoor:.0f} m³（表3.3.2）")
            lines.append(f"  室内消火栓: Q={Q_indoor} L/s × {T_fire}h = {V_indoor:.0f} m³（表3.5.2，{indoor_guns}支水枪）")
            lines.append(f"  自动喷淋:   Q={Q_sprinkler:.0f} L/s × {T_sprinkler}h = {V_sprinkler:.0f} m³")
            lines.append(f"")
            lines.append(f"【水池容积】")
            lines.append(f"  设计用水量: {V_outdoor + V_indoor + V_sprinkler:.0f} m³")
            lines.append(f"  工程安全余量: {safety:.2f}（工程习惯，规范无此项；")
            lines.append(f"              规范做法是在延续时间内扣除连续补水量）")
            lines.append(f"  水池有效容积: {V_total:.0f} m³")

            # 规范校核提示
            notes = []
            if Q_outdoor is None:
                notes.append("⚠ 该类别室外流量规范未规定，应按相邻类别或专项论证确定")
            if "仓库（甲/乙" in bld_type and building_volume > 3000:
                notes.append("⚠ 甲/乙类仓库 V>3000m³ 室外流量表3.3.2未规定，应按规范3.1.4确定")
            if fire_cat == "罐区":
                notes.append("⚠ 罐区应按表3.4.2-3 / 3.4.5-2 另行计算室外流量与延续时间")
            if V_total < 100:
                notes.append("提示: 规范4.3.4 — 两路补水可靠时，有效容积不应小于100m³（仅消火栓系统50m³）")
            if notes:
                lines.append("")
                lines.append("【规范校核】")
                lines.extend(f"  {n}" for n in notes)

            lines.append("")
            lines.append(f"  建议水池尺寸 (L×W×H):")
            vol = V_total
            if vol <= 100:
                lines.append(f"    5m × 5m × {max(2, math.ceil(vol/25*10)/10):.1f}m")
            elif vol <= 500:
                lines.append(f"    10m × 8m × {max(3, math.ceil(vol/80*10)/10):.1f}m")
            else:
                lines.append(f"    15m × 10m × {max(4, math.ceil(vol/150*10)/10):.1f}m")

            # 分格提示（规范4.3.6）
            if V_total > 1000:
                lines.append("    （>1000m³ 应设两座独立水池，4.3.6）")
            elif V_total > 500:
                lines.append("    （>500m³ 宜设两个能独立使用的分格，4.3.6）")

            self.result_text.setText("\n".join(lines))

            self._last_results = {
                "building_type": bld_type,
                "indoor_type": indoor_type,
                "fire_category": fire_cat,
                "building_volume": self.inputs["building_volume"].text(),
                "building_height": self.inputs["building_height"].text(),
                "q_outdoor": Q_outdoor,
                "q_indoor": Q_indoor,
                "indoor_guns": indoor_guns,
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
                "室外消防用水量_L_s": r.get("q_outdoor") or 0,
                "室内消防用水量_L_s": r.get("q_indoor") or 0,
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

  1. 计算依据 GB 50974-2014 表 3.3.2（室外，按建筑总体积查档）及表 3.5.2（室内，按建筑高度查档）
  2. 消防用水量 V = Q(L/s) × t(h) × 3.6；火灾延续时间按表 3.6.2
  3. 工程安全余量为工程习惯做法，规范无此项；规范做法是扣除火灾延续时间内的连续补水量（4.3.5）
  4. 两路补水可靠时水池有效容积不应小于 100m³（仅消火栓系统 50m³，4.3.4）
  5. 建议水池尺寸为初步估算，实际设计需结合总图布置及结构专业确认

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
