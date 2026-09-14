from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox,
    QGridLayout, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
import math

from utils.docx_utils import ReportExporter
from app_styles import (COMBOBOX_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K


class FanPowerCalculator(CalculatorBase):
    """风机功率计算器（统一UI风格版）"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)

        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()

        self.setup_ui()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    def init_data_manager(self):
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None

    # ────────────────────────────────────────────────────────────
    # UI 构建
    # ────────────────────────────────────────────────────────────
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ── 左侧：输入区 ──────────────────────────────────────────
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        scroll_left.setWidgetResizable(True)

        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        desc = QLabel(
            "根据风量、风压、效率参数计算风机轴功率和电机功率，并估算能耗与运行成本。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc)

        # ── 输入参数 GroupBox ─────────────────────────────────────
        input_group = CalculatorBase.make_group_box("输入参数")
        grid = QGridLayout(input_group)
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(10)

        lbl = INPUT_LABEL_STYLE

        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)

        row = 0

        # 风机类型
        self._add_label(grid, row, "风机类型:", lbl)
        self.fan_type = QComboBox()
        self.fan_type.setStyleSheet(COMBOBOX_STYLE)
        self.fan_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.fan_type.addItems(["离心风机", "轴流风机", "混流风机", "罗茨风机"])
        self.fan_type.currentTextChanged.connect(self._on_fan_type_changed)
        grid.addWidget(self.fan_type, row, 1)
        row += 1

        # 风量
        self._add_label(grid, row, "风量:", lbl)
        self.flow_rate_input = QLineEdit("10000")
        self.flow_rate_input.setPlaceholderText("例如：10000")
        self.flow_rate_input.setValidator(QDoubleValidator(1, 1000000, 1))
        grid.addWidget(self.flow_rate_input, row, 1)
        self.flow_rate_unit = QComboBox()
        self.flow_rate_unit.setStyleSheet(COMBOBOX_STYLE)
        self.flow_rate_unit.addItems(["m³/h", "m³/min", "m³/s"])
        self.flow_rate_unit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.flow_rate_unit, row, 2)
        row += 1

        # 全压
        self._add_label(grid, row, "全压:", lbl)
        self.pressure_input = QLineEdit("1000")
        self.pressure_input.setPlaceholderText("例如：1000")
        self.pressure_input.setValidator(QDoubleValidator(10, 50000, 1))
        grid.addWidget(self.pressure_input, row, 1)
        self.pressure_unit = QComboBox()
        self.pressure_unit.setStyleSheet(COMBOBOX_STYLE)
        self.pressure_unit.addItems(["Pa", "kPa", "mmH₂O"])
        self.pressure_unit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.pressure_unit, row, 2)
        row += 1

        # 介质温度
        self._add_label(grid, row, "介质温度 (°C):", lbl)
        self.temperature_input = QLineEdit()
        self.temperature_input.setText("20")
        self.temperature_input.setValidator(QDoubleValidator(-50, 200, 1))
        self.temperature_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.temperature_input, row, 1)
        grid.addWidget(self._hint("标准：20 °C"), row, 2)
        row += 1

        # 海拔高度
        self._add_label(grid, row, "海拔高度 (m):", lbl)
        self.altitude_input = QLineEdit()
        self.altitude_input.setText("0")
        self.altitude_input.setValidator(QDoubleValidator(-100, 5000, 0))
        self.altitude_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.altitude_input, row, 1)
        grid.addWidget(self._hint("影响空气密度"), row, 2)
        row += 1

        # 风机效率
        self._add_label(grid, row, "风机效率 (%):", lbl)
        self.fan_efficiency_input = QLineEdit("75")
        self.fan_efficiency_input.setPlaceholderText("例如：75")
        self.fan_efficiency_input.setValidator(QDoubleValidator(10, 95, 1))
        self.fan_efficiency_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.fan_efficiency_input, row, 1)
        self.fan_efficiency_hint = self._hint("离心风机典型：70~85 %")
        grid.addWidget(self.fan_efficiency_hint, row, 2)
        row += 1

        # 电机效率
        self._add_label(grid, row, "电机效率 (%):", lbl)
        self.motor_efficiency_input = QLineEdit("92")
        self.motor_efficiency_input.setPlaceholderText("例如：92")
        self.motor_efficiency_input.setValidator(QDoubleValidator(50, 98, 1))
        self.motor_efficiency_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.motor_efficiency_input, row, 1)
        grid.addWidget(self._hint("典型值：88~95 %"), row, 2)
        row += 1

        # 传动效率
        self._add_label(grid, row, "传动效率 (%):", lbl)
        self.transmission_efficiency_input = QLineEdit()
        self.transmission_efficiency_input.setText("98")
        self.transmission_efficiency_input.setValidator(QDoubleValidator(80, 100, 1))
        self.transmission_efficiency_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.transmission_efficiency_input, row, 1)
        self.transmission_type = QComboBox()
        self.transmission_type.setStyleSheet(COMBOBOX_STYLE)
        self.transmission_type.addItems(["直联", "皮带传动", "联轴器"])
        self.transmission_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.transmission_type.currentTextChanged.connect(self._on_transmission_changed)
        grid.addWidget(self.transmission_type, row, 2)
        row += 1

        # 日运行时间
        self._add_label(grid, row, "日运行时间 (h/天):", lbl)
        self.operation_hours_input = QLineEdit("24")
        self.operation_hours_input.setPlaceholderText("例如：24")
        self.operation_hours_input.setValidator(QDoubleValidator(1, 24, 1))
        self.operation_hours_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.operation_hours_input, row, 1)
        grid.addWidget(self._hint("用于能耗估算（可选）"), row, 2)
        row += 1

        # 年运行天数
        self._add_label(grid, row, "年运行天数 (天/年):", lbl)
        self.days_per_year_input = QLineEdit("330")
        self.days_per_year_input.setPlaceholderText("例如：330")
        self.days_per_year_input.setValidator(QDoubleValidator(1, 365, 0))
        self.days_per_year_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.days_per_year_input, row, 1)
        grid.addWidget(self._hint("用于能耗估算（可选）"), row, 2)
        row += 1

        # 电价
        self._add_label(grid, row, "电价 (元/kWh):", lbl)
        self.electricity_price_input = QLineEdit("0.8")
        self.electricity_price_input.setPlaceholderText("例如：0.8")
        self.electricity_price_input.setValidator(QDoubleValidator(0.1, 10, 3))
        self.electricity_price_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(self.electricity_price_input, row, 1)
        grid.addWidget(self._hint("用于费用估算（可选）"), row, 2)

        left_layout.addWidget(input_group)
        left_layout.addStretch()

        # ── 右侧：结果区 ──────────────────────────────────────────
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        result_group = CalculatorBase.make_group_box("计算结果")
        rlayout = QVBoxLayout(result_group)

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
        rlayout.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # 底部按钮行：清空 | DOCX | PDF
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(CLEAR_BTN_STYLE)
        clear_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        clear_btn.clicked.connect(self.clear_inputs)
        docx_btn = QPushButton("DOCX")
        docx_btn.setStyleSheet(DOCX_BTN_STYLE)
        docx_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        docx_btn.clicked.connect(self.download_docx_report)
        pdf_btn = QPushButton("PDF")
        pdf_btn.setStyleSheet(PDF_BTN_STYLE)
        pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pdf_btn.clicked.connect(self.download_pdf_report)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(docx_btn)
        btn_layout.addWidget(pdf_btn)
        right_layout.addLayout(btn_layout)

        # 计算按钮（最底部）
        calc_btn = CalculatorBase.make_calc_button()
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)

        # ── 组装主布局 ────────────────────────────────────────────
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

    # ── 辅助函数 ─────────────────────────────────────────────────
    def _add_label(self, grid, row, text, style):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(style)
        grid.addWidget(lbl, row, 0)

    def _hint(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-style: italic;")
        return lbl

    # 传动方式典型效率（手册值）：直联 100%、联轴器 98%、皮带 95%
    TRANSMISSION_EFFICIENCY = {"直联": "100", "联轴器": "98", "皮带传动": "95"}
    # 风机类型典型效率提示
    FAN_EFFICIENCY_HINTS = {
        "离心风机": "离心风机典型：70~85 %",
        "轴流风机": "轴流风机典型：55~75 %",
        "混流风机": "混流风机典型：60~80 %",
        "罗茨风机": "罗茨风机（容积式）典型：50~70 %",
    }

    def _on_transmission_changed(self, text):
        """传动方式变化→自动填充典型传动效率"""
        eff = self.TRANSMISSION_EFFICIENCY.get(text)
        if eff:
            self.transmission_efficiency_input.setText(eff)

    def _on_fan_type_changed(self, text):
        """风机类型变化→更新效率提示"""
        hint = self.FAN_EFFICIENCY_HINTS.get(text)
        if hint:
            self.fan_efficiency_hint.setText(hint)

    # ────────────────────────────────────────────────────────────
    # 清空
    # ────────────────────────────────────────────────────────────
    def clear_inputs(self):
        self.flow_rate_input.clear()
        self.pressure_input.clear()
        self.temperature_input.setText("20")
        self.altitude_input.setText("0")
        self.fan_efficiency_input.clear()
        self.motor_efficiency_input.clear()
        self.transmission_efficiency_input.setText("98")
        self.operation_hours_input.clear()
        self.days_per_year_input.clear()
        self.electricity_price_input.clear()
        self.result_text.clear()

    # ────────────────────────────────────────────────────────────
    # 核心计算
    # ────────────────────────────────────────────────────────────
    def _parse_flow_to_m3h(self):
        """解析风量，统一转为 m³/h"""
        q = float(self.flow_rate_input.text())
        unit = self.flow_rate_unit.currentText()
        if unit == "m³/min":
            return q * 60
        elif unit == "m³/s":
            return q * 3600
        return q  # m³/h

    def _parse_pressure_to_pa(self):
        """解析风压，统一转为 Pa"""
        p = float(self.pressure_input.text())
        unit = self.pressure_unit.currentText()
        if unit == "kPa":
            return p * 1000
        elif unit == "mmH₂O":
            return p * 9.80665
        return p  # Pa

    def _calc_air_density(self, temperature, altitude):
        """ISA 幂律修正空气密度 (kg/m³)"""
        T_K = temperature + C_TO_K
        rho_temp = 1.293 * (C_TO_K / T_K)
        rho_alt = (1 - altitude / 44300) ** 5.255 if altitude < 44300 else 0.01
        return rho_temp * rho_alt

    def calculate(self):
        try:
            # ── 读取输入 ──────────────────────────────────────────
            if not self.flow_rate_input.text():
                QMessageBox.warning(self, "输入错误", "请输入风量")
                return
            if not self.pressure_input.text():
                QMessageBox.warning(self, "输入错误", "请输入全压")
                return
            if not self.fan_efficiency_input.text():
                QMessageBox.warning(self, "输入错误", "请输入风机效率")
                return
            if not self.motor_efficiency_input.text():
                QMessageBox.warning(self, "输入错误", "请输入电机效率")
                return

            Q_m3h = self._parse_flow_to_m3h()
            P_pa  = self._parse_pressure_to_pa()
            T     = float(self.temperature_input.text())
            alt   = float(self.altitude_input.text())
            eta_f = float(self.fan_efficiency_input.text()) / 100
            eta_m = float(self.motor_efficiency_input.text()) / 100
            eta_t = float(self.transmission_efficiency_input.text()) / 100

            # 可选能耗/成本参数
            has_energy = bool(self.operation_hours_input.text() and
                              self.days_per_year_input.text())
            has_cost   = has_energy and bool(self.electricity_price_input.text())

            # ── 计算 ──────────────────────────────────────────────
            rho   = self._calc_air_density(T, alt)
            rho_alt = (1 - alt / 44300) ** 5.255 if alt < 44300 else 0.01
            Q_m3s = Q_m3h / 3600

            # 轴功率 = Q × p / η_fan  (W → kW)
            shaft_kW  = Q_m3s * P_pa / eta_f / 1000

            # 电机功率 = 轴功率 / (η_trans × η_motor)
            motor_kW  = shaft_kW / (eta_t * eta_m)

            # 推荐电机规格（1.15 安全系数）
            std_motors = [0.75, 1.1, 1.5, 2.2, 3, 4, 5.5, 7.5, 11, 15, 18.5, 22,
                          30, 37, 45, 55, 75, 90, 110, 132, 160, 200, 250, 315, 355]
            candidates = [m for m in std_motors if m >= motor_kW * 1.15]
            selected   = candidates[0] if candidates else std_motors[-1]

            # 比功率 kW/(m³/s)
            spec_power = motor_kW / Q_m3s

            # 能耗/成本（可选）
            energy_lines = ""
            if has_energy:
                op_h   = float(self.operation_hours_input.text())
                op_d   = float(self.days_per_year_input.text())
                hourly = motor_kW            # kWh/h
                daily  = hourly * op_h       # kWh/d
                yearly = daily * op_d        # kWh/a
                energy_lines = f"""
══════════
能耗估算
══════════

    小时耗电量: {hourly:.2f} kWh/h
    日耗电量:   {daily:.2f} kWh/d
    年耗电量:   {yearly:.0f} kWh/a"""

                if has_cost:
                    price = float(self.electricity_price_input.text())
                    energy_lines += f"""

══════════
费用估算
══════════

    小时电费: {hourly * price:.2f} 元/h
    日电费:   {daily * price:.2f} 元/d
    年电费:   {yearly * price:.0f} 元/a"""

            fan_type = self.fan_type.currentText()
            trans    = self.transmission_type.currentText()
            q_disp   = f"{self.flow_rate_input.text()} {self.flow_rate_unit.currentText()}"
            p_disp   = f"{self.pressure_input.text()} {self.pressure_unit.currentText()}"

            result = f"""══════════
 输入参数
══════════

    风机类型:   {fan_type}
    风量:       {q_disp}  ({Q_m3h:.1f} m³/h)
    全压:       {p_disp}  ({P_pa:.1f} Pa)
    介质温度:   {T:.1f} °C
    海拔高度:   {alt:.0f} m
    风机效率:   {eta_f*100:.1f} %
    电机效率:   {eta_m*100:.1f} %
    传动效率:   {eta_t*100:.1f} %  [{trans}]

══════════
计算结果
══════════

    实际空气密度:   {rho:.4f} kg/m³
    轴功率:         {shaft_kW:.2f} kW
    电机输入功率:   {motor_kW:.2f} kW
    推荐电机规格:   {selected} kW  (安全系数 1.15)
    比功率:         {spec_power:.2f} kW/(m³/s)

══════════
计算公式
══════════

    轴功率  P_s = Q × p / η_fan
          = {Q_m3s:.4f} × {P_pa:.1f} / {eta_f:.3f}
          = {shaft_kW:.2f} kW

    电机功率 P_m = P_s / (η_trans × η_motor)
           = {shaft_kW:.2f} / ({eta_t:.3f} × {eta_m:.3f})
           = {motor_kW:.2f} kW

    空气密度 ρ = 1.293 × ({C_TO_K:.2f}/{T + C_TO_K:.2f}) × ({rho_alt:.4f})
           = {rho:.4f} kg/m³{energy_lines}

══════════
工程建议
══════════

    • 推荐选用 {selected} kW 电机（已含 1.15 安全系数）
    • 高温或高海拔工况下，密度修正对轴功率有显著影响
    • 风量与全压应按实际工况状态输入（非标准状态换算值）
    • 计算结果仅供参考，实际选型应结合厂家特性曲线"""

            self.result_text.setText(result)

        except ValueError:
            QMessageBox.critical(self, "输入错误", "参数格式错误，请检查输入值")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "效率参数不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    # ────────────────────────────────────────────────────────────
    # 历史记录数据
    # ────────────────────────────────────────────────────────────
    def _get_history_data(self):
        try:
            Q_m3h = self._parse_flow_to_m3h()
            P_pa  = self._parse_pressure_to_pa()
            T     = float(self.temperature_input.text() or 20)
            alt   = float(self.altitude_input.text() or 0)
            eta_f = float(self.fan_efficiency_input.text() or 0) / 100
            eta_m = float(self.motor_efficiency_input.text() or 0) / 100
            eta_t = float(self.transmission_efficiency_input.text() or 98) / 100

            inputs = {
                "风机类型": self.fan_type.currentText(),
                f"风量_{self.flow_rate_unit.currentText()}": float(self.flow_rate_input.text() or 0),
                f"全压_{self.pressure_unit.currentText()}": float(self.pressure_input.text() or 0),
                "温度_C": T,
                "海拔_m": alt,
                "风机效率_%": eta_f * 100,
                "电机效率_%": eta_m * 100,
                "传动效率_%": eta_t * 100,
            }

            rho = self._calc_air_density(T, alt)
            Q_m3s = Q_m3h / 3600
            shaft_kW = Q_m3s * P_pa / eta_f / 1000
            motor_kW = shaft_kW / (eta_t * eta_m)
            std_motors = [0.75, 1.1, 1.5, 2.2, 3, 4, 5.5, 7.5, 11, 15, 18.5, 22,
                          30, 37, 45, 55, 75, 90, 110, 132, 160, 200, 250, 315, 355]
            candidates = [m for m in std_motors if m >= motor_kW * 1.15]
            selected = candidates[0] if candidates else std_motors[-1]

            outputs = {
                "实际空气密度_kg_m3": round(rho, 4),
                "轴功率_kW": round(shaft_kW, 2),
                "电机输入功率_kW": round(motor_kW, 2),
                "推荐电机规格_kW": selected,
                "比功率_kW_m3_s": round(motor_kW / Q_m3s, 2),
            }
        except Exception as e:
            inputs = {}
            outputs = {"计算错误": str(e)}

        return {"inputs": inputs, "outputs": outputs}

    # ────────────────────────────────────────────────────────────
    # 工程信息 & 报告
    # ────────────────────────────────────────────────────────────
    def get_project_info(self):
        return {
            "project_name": "风机功率计算",
            "calculator_name": "风机功率计算器",
            "version": "1.0",
            "description": "根据风量、风压、效率参数计算风机轴功率和电机功率，并估算能耗与运行成本"
        }

    def generate_report(self):
        """生成计算书 - 返回 str/None（None 表示尚未计算，不生成空文件）"""
        content = self.result_text.toPlainText().strip()
        if not content or "计算结果" not in content:
            QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
            return None
        lines = ["风机功率计算报告", "=" * 50, "", content]
        return "\n".join(lines)

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "风机功率")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "风机功率")

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = FanPowerCalculator()
    w.resize(1200, 800)
    w.setWindowTitle("风机功率计算器")
    w.show()
    sys.exit(app.exec())
