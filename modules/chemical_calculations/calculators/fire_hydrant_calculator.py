"""
消火栓计算器 — 消火栓系统计算（消防用水量、管径流速、水泵参数、水箱容量、消火栓数量）

设计依据：GB 50016-2014 / GB 50974-2014 / GB 50084-2017
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QLabel, QLineEdit, QComboBox, QPushButton,
                              QTextEdit, QTableWidget, QTableWidgetItem,
                              QHeaderView, QGridLayout,
                              QScrollArea, QSpinBox,
                              QDoubleSpinBox, QCheckBox, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
import math
from datetime import datetime

from app_styles import (COMBOBOX_STYLE, SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import G
from utils.docx_utils import ReportExporter


class 消火栓计算(CalculatorBase):
    """消火栓计算器"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_results = {}
        self.setup_ui()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception:
            self.data_manager = None

    def setup_ui(self):
        """设置UI — 标准左右分栏"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ════════ 左侧输入区 ════════
        scroll = QScrollArea()
        scroll.setStyleSheet(SCROLL_AREA_STYLE)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        lw = QWidget()
        lw.setStyleSheet("")
        ll = QVBoxLayout(lw)
        ll.setSpacing(15)

        desc = QLabel(
            "消火栓系统计算 — 计算消防用水量、管径流速、水泵参数、水箱容量及消火栓数量。\n"
            "依据 GB 50016-2014 / GB 50974-2014。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        ll.addWidget(desc)

        # ── 建筑信息组 ──
        building_group = CalculatorBase.make_group_box("建筑信息")
        bg = QGridLayout(building_group)
        bg.setHorizontalSpacing(10)
        bg.setVerticalSpacing(12)
        bg.setColumnStretch(0, 4)
        bg.setColumnStretch(1, 8)
        bg.setColumnStretch(2, 5)
        r = 0

        def blbl(text):
            w = QLabel(text)
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            w.setStyleSheet(INPUT_LABEL_STYLE)
            bg.addWidget(w, r, 0)
            return w

        def bhint(text):
            w = QLabel(text)
            w.setStyleSheet("font-style: italic;")
            bg.addWidget(w, r, 2)
            return w

        blbl("建筑类型:")
        self.building_type_combo = QComboBox()
        self.building_type_combo.setStyleSheet(COMBOBOX_STYLE)
        self.building_type_combo.addItems([
            "民用建筑", "工业建筑", "仓库", "高层建筑", "超高层建筑", "地下建筑"
        ])
        self.building_type_combo.currentTextChanged.connect(self.on_building_type_changed)
        bg.addWidget(self.building_type_combo, r, 1)
        bhint("自动联动危险等级")

        r += 1
        blbl("建筑高度 (m):")
        self.building_height_input = QDoubleSpinBox()
        self.building_height_input.setRange(0, 500)
        self.building_height_input.setValue(24)
        self.building_height_input.setSuffix(" m")
        bg.addWidget(self.building_height_input, r, 1)
        bhint("")

        r += 1
        blbl("建筑面积 (m²):")
        self.building_area_input = QDoubleSpinBox()
        self.building_area_input.setRange(0, 1000000)
        self.building_area_input.setValue(5000)
        self.building_area_input.setSuffix(" m²")
        bg.addWidget(self.building_area_input, r, 1)
        bhint("")

        r += 1
        blbl("火灾危险等级:")
        self.danger_level_combo = QComboBox()
        self.danger_level_combo.setStyleSheet(COMBOBOX_STYLE)
        self.danger_level_combo.addItems(["轻危险级", "中危险级Ⅰ级", "中危险级Ⅱ级", "严重危险级"])
        bg.addWidget(self.danger_level_combo, r, 1)
        bhint("")

        r += 1
        blbl("防火分区数量:")
        self.fire_zone_spin = QSpinBox()
        self.fire_zone_spin.setRange(1, 50)
        self.fire_zone_spin.setValue(1)
        bg.addWidget(self.fire_zone_spin, r, 1)
        bhint("")

        ll.addWidget(building_group)

        # ── 消火栓参数组 ──
        hydrant_group = CalculatorBase.make_group_box("消火栓参数")
        hg = QGridLayout(hydrant_group)
        hg.setHorizontalSpacing(10)
        hg.setVerticalSpacing(12)
        hg.setColumnStretch(0, 4)
        hg.setColumnStretch(1, 8)
        hg.setColumnStretch(2, 5)
        r = 0

        def hlbl(text):
            w = QLabel(text)
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            w.setStyleSheet(INPUT_LABEL_STYLE)
            hg.addWidget(w, r, 0)
            return w

        def hhint(text):
            w = QLabel(text)
            w.setStyleSheet("font-style: italic;")
            hg.addWidget(w, r, 2)
            return w

        hlbl("同时使用水枪数:")
        self.gun_count_spin = QSpinBox()
        self.gun_count_spin.setRange(1, 10)
        self.gun_count_spin.setValue(2)
        hg.addWidget(self.gun_count_spin, r, 1)
        hhint("")

        r += 1
        hlbl("水枪流量 (L/s):")
        self.gun_flow_input = QDoubleSpinBox()
        self.gun_flow_input.setRange(2, 10)
        self.gun_flow_input.setValue(5)
        self.gun_flow_input.setSuffix(" L/s")
        hg.addWidget(self.gun_flow_input, r, 1)
        hhint("规范要求 ≥5 L/s")

        r += 1
        hlbl("充实水柱 (m):")
        self.water_column_input = QDoubleSpinBox()
        self.water_column_input.setRange(7, 17)
        self.water_column_input.setValue(13)
        self.water_column_input.setSuffix(" m")
        hg.addWidget(self.water_column_input, r, 1)
        hhint("高层≥13m")

        r += 1
        hlbl("最不利点压力 (MPa):")
        self.min_pressure_input = QDoubleSpinBox()
        self.min_pressure_input.setRange(0.1, 1.0)
        self.min_pressure_input.setValue(0.35)
        self.min_pressure_input.setSuffix(" MPa")
        hg.addWidget(self.min_pressure_input, r, 1)
        hhint("")

        r += 1
        hlbl("水泵扬程 (m):")
        self.pump_head_input = QDoubleSpinBox()
        self.pump_head_input.setRange(10, 200)
        self.pump_head_input.setValue(80)
        self.pump_head_input.setSuffix(" m")
        hg.addWidget(self.pump_head_input, r, 1)
        hhint("")

        r += 1
        hlbl("主管直径 (mm):")
        self.main_pipe_diameter_combo = QComboBox()
        self.main_pipe_diameter_combo.setStyleSheet(COMBOBOX_STYLE)
        self.main_pipe_diameter_combo.addItems(["100", "125", "150", "200"])
        self.main_pipe_diameter_combo.setCurrentText("150")
        hg.addWidget(self.main_pipe_diameter_combo, r, 1)
        hhint("水平干管≥DN150")

        r += 1
        hlbl("计算选项:")
        opt_w = QWidget()
        opt_l = QHBoxLayout(opt_w)
        opt_l.setContentsMargins(0, 0, 0, 0)
        self.auto_calc_check = QCheckBox("自动计算参数")
        self.auto_calc_check.setChecked(True)
        self.high_rise_check = QCheckBox("高层建筑")
        self.sprinkler_check = QCheckBox("喷淋系统")
        for cb in [self.auto_calc_check, self.high_rise_check, self.sprinkler_check]:
            opt_l.addWidget(cb)
        hg.addWidget(opt_w, r, 1)
        hhint("")

        ll.addWidget(hydrant_group)

        # ── 消防规范参考 ──
        standard_group = CalculatorBase.make_group_box("消防规范参考")
        sg = QVBoxLayout(standard_group)
        standard_text = QTextEdit()
        standard_text.setReadOnly(True)
        standard_text.setHtml(self.get_standard_html())
        standard_text.setFixedHeight(220)
        sg.addWidget(standard_text)
        ll.addWidget(standard_group)

        ll.addStretch()
        scroll.setWidget(lw)

        # ════════ 右侧结果区 ════════
        rw = QWidget()
        rw.setMinimumWidth(300)
        rl = QVBoxLayout(rw)
        rl.setSpacing(15)

        result_group = CalculatorBase.make_group_box("计算结果")
        rvl = QVBoxLayout(result_group)
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
        rvl.addWidget(self.result_text)
        rl.addWidget(result_group)

        # ── 推荐配置表 ──
        config_group = CalculatorBase.make_group_box("推荐配置")
        config_layout = QVBoxLayout(config_group)
        self.config_table = QTableWidget()
        self.config_table.setColumnCount(3)
        self.config_table.setHorizontalHeaderLabels(["项目", "推荐值", "说明"])
        config_layout.addWidget(self.config_table)
        rl.addWidget(config_group)

        # ── 底部按钮行：清空 | DOCX | PDF ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        for name, style, cb in [
            ("清空", CLEAR_BTN_STYLE, self.clear_inputs),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(name)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(cb)
            btn_layout.addWidget(btn)
        rl.addLayout(btn_layout)

        # ── 计算按钮（最底部） ──
        calc_btn = self.make_calc_button("计 算")
        calc_btn.clicked.connect(self.calculate)
        rl.addWidget(calc_btn)

        main_layout.addWidget(scroll, 2)
        main_layout.addWidget(rw, 1)

    def on_building_type_changed(self, building_type):
        """建筑类型改变事件"""
        if building_type in ["高层建筑", "超高层建筑"]:
            self.high_rise_check.setChecked(True)
            self.building_height_input.setValue(50)
        else:
            self.high_rise_check.setChecked(False)
            self.building_height_input.setValue(24)

        # 自动设置危险等级
        if building_type == "仓库":
            self.danger_level_combo.setCurrentText("严重危险级")
        elif building_type in ["工业建筑", "高层建筑"]:
            self.danger_level_combo.setCurrentText("中危险级Ⅱ级")
        else:
            self.danger_level_combo.setCurrentText("中危险级Ⅰ级")

    def get_standard_html(self):
        """获取标准说明HTML内容"""
        return """
        <h2>消火栓系统设计规范</h2>

        <h3>设计依据</h3>
        <ul>
            <li>GB 50016-2014《建筑设计防火规范》</li>
            <li>GB 50974-2014《消防给水及消火栓系统技术规范》</li>
            <li>GB 50084-2017《自动喷水灭火系统设计规范》</li>
        </ul>

        <h3>消防用水量标准</h3>
        <p><b>民用建筑：</b>普通住宅（≤21m）室外15/室内10 L/s·2h；高层住宅（＞21m）室外15/室内20 L/s·2h；办公楼（≤50m）室外20/室内15 L/s·2h。</p>
        <p><b>工业建筑：</b>轻危险级 15/10 L/s·2h；中危险级Ⅰ级 20/15 L/s·2h；中危险级Ⅱ级 25/20 L/s·2h；严重危险级 30-40/25-30 L/s·3h。</p>

        <h3>消火栓布置要求</h3>
        <ul>
            <li><b>室内消火栓间距：</b>高层建筑≤30m，其他建筑≤50m</li>
            <li><b>保护半径：</b>水带长度×0.8 + 充实水柱水平投影</li>
            <li><b>充实水柱长度：</b>一般建筑≥7m，高层建筑≥13m</li>
            <li><b>出水压力：</b>0.35MPa（最不利点）</li>
            <li><b>水枪流量：</b>≥5L/s</li>
        </ul>

        <h3>管道设计要求</h3>
        <ul>
            <li><b>管材：</b>热镀锌钢管、不锈钢管等</li>
            <li><b>管径：</b>室内立管≥DN100，水平干管≥DN150</li>
            <li><b>流速限制：</b>一般≤2.5m/s，经济流速1.5-2.0m/s</li>
            <li><b>工作压力：</b>≤2.4MPa</li>
        </ul>

        <h3>注意事项</h3>
        <p>本计算工具仅供参考，实际工程设计应遵循最新国家标准和当地消防部门的要求。重要项目应聘请专业消防设计单位进行设计。</p>
        """

    # ═══════════════════════ 计算 ═══════════════════════
    def calculate(self):
        """计算消火栓系统"""
        try:
            # 获取输入值
            building_type = self.building_type_combo.currentText()
            building_height = self.building_height_input.value()
            building_area = self.building_area_input.value()
            danger_level = self.danger_level_combo.currentText()
            fire_zones = self.fire_zone_spin.value()
            gun_count = self.gun_count_spin.value()
            gun_flow = self.gun_flow_input.value()
            water_column = self.water_column_input.value()
            min_pressure = self.min_pressure_input.value()
            pump_head = self.pump_head_input.value()
            main_diameter = int(self.main_pipe_diameter_combo.currentText())
            is_high_rise = self.high_rise_check.isChecked()
            has_sprinkler = self.sprinkler_check.isChecked()
            auto_calc = self.auto_calc_check.isChecked()

            # 自动计算参数
            if auto_calc:
                self.auto_calculate_parameters(building_type, building_height, danger_level)
                # 重新读取联动后的值
                gun_count = self.gun_count_spin.value()
                water_column = self.water_column_input.value()
                min_pressure = self.min_pressure_input.value()

            # 计算消防用水量
            total_flow = self.calculate_total_flow(gun_count, gun_flow, building_type, danger_level)

            # 计算管径和流速
            pipe_results = self.calculate_pipe_parameters(total_flow, main_diameter)

            # 计算水泵参数
            pump_results = self.calculate_pump_parameters(pump_head, total_flow, building_height)

            # 计算水箱容量
            tank_capacity = self.calculate_tank_capacity(total_flow, building_type, danger_level)

            # 计算消火栓数量
            hydrant_count = self.calculate_hydrant_count(building_area, building_type)

            # 显示结果
            self.display_results(total_flow, pipe_results, pump_results, tank_capacity, hydrant_count)

            # 更新配置表
            self.update_config_table(total_flow, pipe_results, pump_results, tank_capacity, hydrant_count)

            self._last_results = {
                "building_type": building_type,
                "building_height": building_height,
                "building_area": building_area,
                "danger_level": danger_level,
                "gun_count": gun_count,
                "gun_flow": gun_flow,
                "total_flow": total_flow,
                "main_diameter": main_diameter,
                "pipe_results": pipe_results,
                "pump_results": pump_results,
                "tank_capacity": tank_capacity,
                "hydrant_count": hydrant_count,
            }

        except Exception as e:
            QMessageBox.warning(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def _get_history_data(self):
        """提供历史记录数据"""
        r = self._last_results
        if not r:
            return {"inputs": {}, "outputs": {}}

        inputs = {
            "建筑类型": r.get("building_type", ""),
            "建筑高度_m": r.get("building_height", 0),
            "建筑面积_m2": r.get("building_area", 0),
            "危险等级": r.get("danger_level", ""),
            "水枪数量": r.get("gun_count", 0),
            "水枪流量_L_s": r.get("gun_flow", 0),
            "主管管径_mm": r.get("main_diameter", 0),
        }
        pr = r.get("pipe_results", {})
        pm = r.get("pump_results", {})
        outputs = {
            "消防总流量_L_s": round(r.get("total_flow", 0), 1),
            "管道流速_m_s": round(pr.get("velocity", 0), 2),
            "水泵流量_L_s": round(pm.get("flow", 0), 1),
            "水箱容量_m3": round(r.get("tank_capacity", 0), 1),
            "消火栓数量": r.get("hydrant_count", 0)
        }
        return {"inputs": inputs, "outputs": outputs}

    def auto_calculate_parameters(self, building_type, height, danger_level):
        """自动计算参数"""
        # 自动设置水枪数
        if building_type in ["高层建筑", "超高层建筑"]:
            self.gun_count_spin.setValue(4)
        elif building_type == "仓库":
            self.gun_count_spin.setValue(3)
        else:
            self.gun_count_spin.setValue(2)

        # 自动设置充实水柱
        if height > 24:
            self.water_column_input.setValue(13)
        else:
            self.water_column_input.setValue(10)

        # 自动设置最不利点压力
        if height > 50:
            self.min_pressure_input.setValue(0.45)
        else:
            self.min_pressure_input.setValue(0.35)

    def calculate_total_flow(self, gun_count, gun_flow, building_type, danger_level):
        """计算总消防用水量"""
        base_flow = gun_count * gun_flow

        # 根据建筑类型和危险等级调整
        flow_factors = {
            "民用建筑": 1.0,
            "工业建筑": 1.2,
            "仓库": 1.5,
            "高层建筑": 1.3,
            "超高层建筑": 1.5,
            "地下建筑": 1.2
        }

        danger_factors = {
            "轻危险级": 0.8,
            "中危险级Ⅰ级": 1.0,
            "中危险级Ⅱ级": 1.2,
            "严重危险级": 1.5
        }

        factor = flow_factors.get(building_type, 1.0) * danger_factors.get(danger_level, 1.0)
        total_flow = base_flow * factor

        # 最小流量限制
        min_flows = {
            "民用建筑": 10,
            "工业建筑": 15,
            "仓库": 20,
            "高层建筑": 20,
            "超高层建筑": 30,
            "地下建筑": 15
        }

        return max(total_flow, min_flows.get(building_type, 15))

    def calculate_pipe_parameters(self, total_flow, main_diameter):
        """计算管道参数"""
        # 计算流速
        area = math.pi * (main_diameter / 1000) ** 2 / 4  # m²
        flow_m3s = total_flow / 1000  # m³/s
        velocity = flow_m3s / area  # m/s

        # 计算沿程水头损失 (简化计算)
        length = 100  # 假设管道长度100m
        friction_factor = 0.02  # 摩擦系数
        head_loss = friction_factor * (length / (main_diameter / 1000)) * (velocity ** 2) / (2 * G)

        return {
            "diameter": main_diameter,
            "velocity": velocity,
            "head_loss": head_loss,
            "recommended_diameter": self.get_recommended_diameter(total_flow)
        }

    def get_recommended_diameter(self, flow):
        """获取推荐管径"""
        if flow <= 15:
            return 100
        elif flow <= 25:
            return 125
        elif flow <= 40:
            return 150
        else:
            return 200

    def calculate_pump_parameters(self, pump_head, total_flow, building_height):
        """计算水泵参数"""
        # 计算所需扬程
        required_head = building_height + 10 + 5  # 建筑高度 + 最不利点高度 + 余量

        # 计算水泵功率 P = ρ·g·Q·H/η，ρ_水=1000 kg/m³
        efficiency = 0.75
        power_w = 1000 * G * (total_flow / 1000) * required_head / efficiency
        power_kw = power_w / 1000  # W → kW

        return {
            "required_head": required_head,
            "actual_head": pump_head,
            "power": power_kw,
            "flow": total_flow,
            "efficiency": efficiency
        }

    def calculate_tank_capacity(self, total_flow, building_type, danger_level):
        """计算消防水箱容量"""
        # 火灾延续时间 (小时)
        duration_factors = {
            "民用建筑": 2,
            "工业建筑": 2,
            "仓库": 3,
            "高层建筑": 2,
            "超高层建筑": 3,
            "地下建筑": 2
        }

        duration = duration_factors.get(building_type, 2)

        # 容量计算 (m³)
        capacity = total_flow * 3.6 * duration  # L/s * 3.6 = m³/h

        # 最小容量限制
        min_capacities = {
            "民用建筑": 12,
            "工业建筑": 18,
            "仓库": 36,
            "高层建筑": 18,
            "超高层建筑": 36,
            "地下建筑": 12
        }

        return max(capacity, min_capacities.get(building_type, 12))

    def calculate_hydrant_count(self, building_area, building_type):
        """计算消火栓数量"""
        # 消火栓保护面积 (m²)
        coverage_areas = {
            "民用建筑": 400,
            "工业建筑": 300,
            "仓库": 200,
            "高层建筑": 300,
            "超高层建筑": 250,
            "地下建筑": 200
        }

        coverage = coverage_areas.get(building_type, 300)
        count = math.ceil(building_area / coverage)

        # 最小数量限制
        min_counts = {
            "民用建筑": 2,
            "工业建筑": 3,
            "仓库": 4,
            "高层建筑": 4,
            "超高层建筑": 6,
            "地下建筑": 3
        }

        return max(count, min_counts.get(building_type, 2))

    def display_results(self, total_flow, pipe_results, pump_results, tank_capacity, hydrant_count):
        """显示计算结果"""
        vel_ok = pipe_results['velocity'] <= 2.5
        lines = [
            "=" * 44,
            "        消火栓系统计算结果",
            "=" * 44,
            "",
            "【消防用水量】",
            f"  总消防用水量   : {total_flow:.1f} L/s",
            f"                   （同时使用水枪的总流量）",
            "",
            "【管道参数】",
            f"  主管道直径     : DN{pipe_results['diameter']}（推荐 DN{pipe_results['recommended_diameter']}）",
            f"  管道流速       : {pipe_results['velocity']:.2f} m/s {'✓ 正常' if vel_ok else '⚠ 流速偏高（>2.5 m/s）'}",
            f"  沿程水头损失   : {pipe_results['head_loss']:.2f} m（100m 管长估算）",
            "",
            "【水泵参数】",
            f"  水泵扬程       : {pump_results['actual_head']:.0f} m（需求 {pump_results['required_head']:.0f} m）",
            f"  水泵轴功率     : {pump_results['power']:.1f} kW（效率 {pump_results['efficiency']*100:.0f}%）",
            "",
            "【储存与布置】",
            f"  消防水箱容量   : {tank_capacity:.0f} m³（火灾延续时间用水量）",
            f"  消火栓数量     : {hydrant_count} 个（按保护半径计算）",
            "",
            "【设计建议】",
            f"  1. 主管道建议采用 DN{pipe_results['recommended_diameter']} 管道",
            f"  2. 水泵选型应满足 {pump_results['required_head']:.0f} m 扬程和 {total_flow:.1f} L/s 流量要求",
            f"  3. 消防水箱容量不应小于 {tank_capacity:.0f} m³",
            "  4. 消火栓布置间距应符合规范要求",
            "=" * 44,
        ]

        self.result_text.setPlainText("\n".join(lines))

    def update_config_table(self, total_flow, pipe_results, pump_results, tank_capacity, hydrant_count):
        """更新配置表"""
        config_data = [
            ["消防用水量", f"{total_flow:.1f} L/s", "总设计流量"],
            ["主管道直径", f"DN{pipe_results['recommended_diameter']}", "推荐主管直径"],
            ["管道流速", f"{pipe_results['velocity']:.2f} m/s", "经济流速范围: 1.5-2.5 m/s"],
            ["水泵扬程", f"{pump_results['required_head']:.0f} m", "最小需求扬程"],
            ["水泵流量", f"{pump_results['flow']:.1f} L/s", "设计流量"],
            ["水箱容量", f"{tank_capacity:.0f} m³", "消防储水量"],
            ["消火栓数量", f"{hydrant_count} 个", "按保护面积计算"],
            ["充实水柱", f"{self.water_column_input.value()} m", "有效灭火长度"]
        ]

        self.config_table.setRowCount(len(config_data))
        for i, row_data in enumerate(config_data):
            for j, data in enumerate(row_data):
                item = QTableWidgetItem(data)
                item.setTextAlignment(Qt.AlignCenter)
                self.config_table.setItem(i, j, item)

        # 调整表格列宽
        header = self.config_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

    def clear_inputs(self):
        """清空输入"""
        self.building_type_combo.setCurrentIndex(0)
        self.building_height_input.setValue(24)
        self.building_area_input.setValue(5000)
        self.danger_level_combo.setCurrentIndex(0)
        self.fire_zone_spin.setValue(1)
        self.gun_count_spin.setValue(2)
        self.gun_flow_input.setValue(5)
        self.water_column_input.setValue(13)
        self.min_pressure_input.setValue(0.35)
        self.pump_head_input.setValue(80)
        self.main_pipe_diameter_combo.setCurrentText("150")
        self.auto_calc_check.setChecked(True)
        self.high_rise_check.setChecked(False)
        self.sprinkler_check.setChecked(False)
        self.result_text.clear()
        self.config_table.setRowCount(0)
        self._last_results = {}
        # 触发建筑类型联动复位
        self.on_building_type_changed(self.building_type_combo.currentText())

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
            if not result_text or ("消防用水量" not in result_text):
                return None

            project_info = self.get_project_info()
            report = f"""══════════════════════════════════════════
          消火栓计算计算书
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

  1. 计算依据 GB 50016-2014、GB 50974-2014 及 GB 50084-2017
  2. 沿程水头损失按 100m 管长、摩擦系数 0.02 简化估算
  3. 实际工程设计应遵循最新国家标准和当地消防部门要求，由专业消防设计单位确认

---
生成于 ChemCal 工程计算模块
"""
            return report

        except Exception as e:
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "消火栓计算")

    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "消火栓计算")

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = 消火栓计算()
    widget.resize(1200, 800)
    widget.show()

    sys.exit(app.exec())
