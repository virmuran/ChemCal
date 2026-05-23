import os
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QGridLayout, QFileDialog, QMessageBox,
    QScrollArea, QSizePolicy,

)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator


COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #888;
        border-radius: 4px;
        padding: 6px 10px;
        /* background via theme */
        /* color via theme */
    }
    QComboBox QAbstractItemView {
        /* background-color via theme */
        /* color via theme */
        border: 1px solid #888;
        selection-background-color: #3498db;
        selection-color: black;
    }
    QComboBox QAbstractItemView::item {
        padding: 3px 8px;
    }
"""

LINEEDIT_STYLE = "padding: 6px 10px; border: 1px solid #888; border-radius: 4px;"

class WetAirCalculator(QWidget):
    """湿空气计算器"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.data_manager = None
        self._last_results = {}
        self.setup_ui()

    # ─────────────────────────── UI ─────────────────────────────
    def setup_ui(self):
        group_style = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
            }
        """

        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ───────── 左侧输入区 ─────────
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        scroll_left.setWidgetResizable(True)

        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 说明文字
        desc = QLabel("计算湿空气的各种物性参数：相对湿度、绝对湿度、露点温度、比焓、比容等。"
                       "至少需要输入干球温度，并提供相对湿度、绝对湿度、湿球温度或露点温度之一。")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px;")
        left_layout.addWidget(desc)

        # ── 输入参数组 ──
        input_group = QGroupBox("输入参数")
        input_group.setStyleSheet(group_style)
        grid = QGridLayout(input_group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 4)  # 标签列
        grid.setColumnStretch(1, 8)  # 输入框列
        grid.setColumnStretch(2, 5)  # 提示列


        label_style = "font-weight: bold; padding-right: 10px;"

        def make_label(text):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet(label_style)
            return lbl

        # 行0：干球温度 + 大气压力
        self.temp_input = QLineEdit()
        self.temp_input.setPlaceholderText("例如：25")
        self.temp_input.setValidator(QDoubleValidator(-50, 200, 2))
        self.temp_input.setStyleSheet(LINEEDIT_STYLE)
        self.temp_unit = QComboBox()
        self.temp_unit.setStyleSheet(COMBOBOX_STYLE)
        self.temp_unit.addItems(["°C", "K"])
        grid.addWidget(make_label("干球温度:"), 0, 0)
        grid.addWidget(self.temp_input, 0, 1)
        grid.addWidget(self.temp_unit, 0, 2)

        # 行1：大气压力
        self.pressure_input = QLineEdit("101.325")
        self.pressure_input.setValidator(QDoubleValidator(50, 2000, 3))
        self.pressure_input.setStyleSheet(LINEEDIT_STYLE)
        self.pressure_unit = QComboBox()
        self.pressure_unit.setStyleSheet(COMBOBOX_STYLE)
        self.pressure_unit.addItems(["kPa", "bar", "atm"])
        grid.addWidget(make_label("大气压力:"), 1, 0)
        grid.addWidget(self.pressure_input, 1, 1)
        grid.addWidget(self.pressure_unit, 1, 2)

        # 分隔说明
        hint = QLabel("── 以下四个参数，至少输入其中一个 ──")
        hint.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        hint.setAlignment(Qt.AlignCenter)
        grid.addWidget(hint, 2, 0, 1, 3)

        # 行3：相对湿度
        self.rh_input = QLineEdit()
        self.rh_input.setPlaceholderText("例如：60（0~100）")
        self.rh_input.setValidator(QDoubleValidator(0, 100, 2))
        self.rh_input.setStyleSheet(LINEEDIT_STYLE)
        grid.addWidget(make_label("相对湿度:"), 3, 0)
        grid.addWidget(self.rh_input, 3, 1)
        hint_rh = QLabel("%")
        grid.addWidget(hint_rh, 3, 2)

        # 行4：绝对湿度
        self.humidity_input = QLineEdit()
        self.humidity_input.setPlaceholderText("例如：0.012 或 12")
        self.humidity_input.setValidator(QDoubleValidator(0, 9999, 6))
        self.humidity_input.setStyleSheet(LINEEDIT_STYLE)
        self.humidity_unit = QComboBox()
        self.humidity_unit.setStyleSheet(COMBOBOX_STYLE)
        self.humidity_unit.addItems(["kg/kg干空气", "g/kg干空气"])
        grid.addWidget(make_label("绝对湿度:"), 4, 0)
        grid.addWidget(self.humidity_input, 4, 1)
        grid.addWidget(self.humidity_unit, 4, 2)

        # 行5：湿球温度
        self.wet_bulb_input = QLineEdit()
        self.wet_bulb_input.setPlaceholderText("例如：20")
        self.wet_bulb_input.setValidator(QDoubleValidator(-50, 200, 2))
        self.wet_bulb_input.setStyleSheet(LINEEDIT_STYLE)
        hint_wb = QLabel("°C（需 ≤ 干球温度）")
        grid.addWidget(make_label("湿球温度:"), 5, 0)
        grid.addWidget(self.wet_bulb_input, 5, 1)
        grid.addWidget(hint_wb, 5, 2)

        # 行6：露点温度
        self.dew_point_input = QLineEdit()
        self.dew_point_input.setPlaceholderText("例如：15")
        self.dew_point_input.setValidator(QDoubleValidator(-50, 200, 2))
        self.dew_point_input.setStyleSheet(LINEEDIT_STYLE)
        hint_dp = QLabel("°C（需 ≤ 干球温度）")
        grid.addWidget(make_label("露点温度:"), 6, 0)
        grid.addWidget(self.dew_point_input, 6, 1)
        grid.addWidget(hint_dp, 6, 2)

        left_layout.addWidget(input_group)

        # ── 计算按钮 ──
        calc_btn = QPushButton("查询")
        calc_btn.setFont(QFont("Arial", 12))
        calc_btn.setMinimumHeight(50)
        calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                min-height: 50px; padding: 0px;
            }
            QPushButton:hover { background-color: #219955; }
        """)
        calc_btn.clicked.connect(self.calculate)
        left_layout.addWidget(calc_btn)

        # ── 底部按钮行 ──
        btn_row = QHBoxLayout()

        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6; color: white;
                font-weight: bold; border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        clear_btn.clicked.connect(self.clear_inputs)

        dl_txt_btn = QPushButton("下载计算书(TXT)")
        dl_txt_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white;
                font-weight: bold; border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #219a52; }
        """)
        dl_txt_btn.clicked.connect(self.download_txt_report)

        dl_pdf_btn = QPushButton("下载计算书(PDF)")
        dl_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; color: white;
                font-weight: bold; border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        dl_pdf_btn.clicked.connect(self.generate_pdf_report)

        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(dl_txt_btn)
        btn_row.addWidget(dl_pdf_btn)
        left_layout.addLayout(btn_row)
        left_layout.addStretch()

        # ───────── 右侧结果区 ─────────
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)

        result_group = QGroupBox("计算结果")
        result_group.setStyleSheet(group_style)
        result_vbox = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet("""
            QTextEdit {
                /* bg via theme */border: 1px solid #ecf0f1;
                border-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 13px;
                padding: 8px;
            }
        """)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        result_vbox.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # 拼合左右
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

    # ─────────────────────────── 计算 ─────────────────────────────
    def calculate(self):
        """执行湿空气计算"""
        try:
            # 干球温度
            temp_str = self.temp_input.text().strip()
            if not temp_str:
                self._show_error("请输入干球温度")
                return
            temp = float(temp_str)
            if self.temp_unit.currentText() == "K":
                temp -= 273.15

            # 大气压力 → kPa
            if not self.pressure_input.text().strip():
                self._show_error("请输入大气压力")
                return
            pressure = float(self.pressure_input.text())
            pu = self.pressure_unit.currentText()
            if pu == "bar":
                pressure_kpa = pressure * 100.0
            elif pu == "atm":
                pressure_kpa = pressure * 101.325
            else:
                pressure_kpa = pressure

            # 已知湿度参数
            known = {}
            if self.rh_input.text().strip():
                known["rh"] = float(self.rh_input.text())
            if self.humidity_input.text().strip():
                w = float(self.humidity_input.text())
                if self.humidity_unit.currentText() == "g/kg干空气":
                    w /= 1000.0
                known["abs_humidity"] = w
            if self.wet_bulb_input.text().strip():
                known["wet_bulb"] = float(self.wet_bulb_input.text())
            if self.dew_point_input.text().strip():
                known["dew_point"] = float(self.dew_point_input.text())

            if not known:
                self._show_error("请至少输入：相对湿度、绝对湿度、湿球温度、露点温度 中的一个")
                return

            r = self._calc_wet_air(temp, pressure_kpa, known)
            self._last_results = r
            self._last_temp = temp
            self._last_pressure = pressure
            self._last_pressure_unit = pu
            self._last_known = known

            # 保存历史

            self._display(r, temp, pressure_kpa, pu, known)

        except ValueError:
            self._show_error("输入参数格式错误，请检查数值")
        except Exception as e:
            self._show_error(f"计算错误：{e}")

    # ─────────────────────── 核心计算 ──────────────────────────────
    @staticmethod
    def _psat(t_c):
        """饱和水蒸气压（kPa），Magnus近似"""
        return 0.61078 * math.exp(17.27 * t_c / (t_c + 237.3))

    def _calc_wet_air(self, temp, pressure, known):
        """湿空气物性计算，返回结果字典"""
        psat = self._psat

        if "rh" in known:
            rh = known["rh"] / 100.0
            p_v = rh * psat(temp)
        elif "abs_humidity" in known:
            W = known["abs_humidity"]
            p_v = W * pressure / (0.622 + W)
            rh = p_v / psat(temp)
        elif "dew_point" in known:
            p_v = psat(known["dew_point"])
            rh = p_v / psat(temp)
        elif "wet_bulb" in known:
            # Newton-Raphson 迭代（能量平衡方程）
            wet_bulb = known["wet_bulb"]
            p_v = psat(wet_bulb) * 0.9
            for _ in range(60):
                W_g = 0.622 * p_v / (pressure - p_v)
                W_s = 0.622 * psat(wet_bulb) / (pressure - psat(wet_bulb))
                lv = 2501.0 - 2.361 * wet_bulb   # kJ/kg
                f = (W_s - W_g) * lv - (temp - wet_bulb) * (1.006 + W_g * 1.86)
                dp = p_v * 0.001 + 1e-9
                W_g2 = 0.622 * (p_v + dp) / (pressure - (p_v + dp))
                f2 = (W_s - W_g2) * lv - (temp - wet_bulb) * (1.006 + W_g2 * 1.86)
                df = (f2 - f) / dp
                if abs(df) < 1e-15:
                    break
                p_v_new = p_v - f / df
                if abs(p_v_new - p_v) < 1e-6:
                    p_v = p_v_new
                    break
                p_v = p_v_new
            rh = p_v / psat(temp)
        else:
            raise ValueError("未提供湿度条件")

        # 限制 p_v 在合理范围
        p_v = max(1e-9, min(p_v, psat(temp)))
        rh = max(0.0, min(rh, 1.0))

        # 湿度比 W (kg水/kg干空气)
        W = 0.622 * p_v / (pressure - p_v)

        # 露点温度
        if p_v > 0:
            dew_pt = 237.3 * math.log(p_v / 0.61078) / (17.27 - math.log(p_v / 0.61078))
        else:
            dew_pt = -100.0

        # 比焓 (kJ/kg干空气)
        h = 1.006 * temp + W * (2501.0 + 1.86 * temp)

        # 比容 (m³/kg干空气)
        v = 0.287 * (temp + 273.15) * (1.0 + 1.608 * W) / pressure

        # 湿球温度（Newton-Raphson反求）
        wb = min(temp, dew_pt + (temp - dew_pt) * 0.7)  # 初始猜测
        for _ in range(100):
            p_vs_w = psat(wb)
            W_s_w = 0.622 * p_vs_w / (pressure - p_vs_w)
            lv_j = (2501.0 - 2.361 * wb) * 1000.0
            f = (W_s_w - W) * lv_j - (temp - wb) * (1006.0 + W * 1860.0)
            dt = 0.01
            p_vs_w2 = psat(wb + dt)
            W_s_w2 = 0.622 * p_vs_w2 / (pressure - p_vs_w2)
            f2 = (W_s_w2 - W) * lv_j - (temp - wb - dt) * (1006.0 + W * 1860.0)
            df = (f - f2) / dt
            if abs(df) < 1e-10:
                break
            wb_new = wb - f / df
            if abs(wb_new - wb) < 0.001:
                wb = wb_new
                break
            wb = wb_new
        wb = max(dew_pt, min(wb, temp))

        return {
            "rh": rh * 100.0,
            "W": W,
            "dew_point": dew_pt,
            "wet_bulb": wb,
            "enthalpy": h,
            "specific_volume": v,
            "p_v": p_v,
        }

    # ───────────────────────── 显示 ────────────────────────────────
    def _display(self, r, temp, pressure_kpa, pressure_unit, known):
        known_map = {
            "rh": f"相对湿度 = {known.get('rh', ''):.2f} %",
            "abs_humidity": f"绝对湿度 = {known.get('abs_humidity', 0)*1000:.3f} g/kg",
            "wet_bulb": f"湿球温度 = {known.get('wet_bulb', ''):.2f} °C",
            "dew_point": f"露点温度 = {known.get('dew_point', ''):.2f} °C",
        }
        known_str = "  ".join(known_map[k] for k in known if k in known_map)

        lines = [
            "=" * 50,
            "         湿空气计算结果",
            "=" * 50,
            "",
            "【输入参数】",
            f"  干球温度              : {temp:.2f} °C",
            f"  大气压力              : {pressure_kpa:.3f} kPa",
            f"  已知条件              : {known_str}",
            "",
            "【计算结果】",
            f"  相对湿度              : {r['rh']:.2f} %",
            f"  绝对湿度 (湿度比)     : {r['W']*1000:.4f} g/kg干空气",
            f"                        : {r['W']:.6f} kg/kg干空气",
            f"  露点温度              : {r['dew_point']:.2f} °C",
            f"  湿球温度              : {r['wet_bulb']:.2f} °C",
            f"  比焓                  : {r['enthalpy']:.3f} kJ/kg干空气",
            f"  比容                  : {r['specific_volume']:.4f} m³/kg干空气",
            f"  水蒸气分压            : {r['p_v']:.4f} kPa",
            "",
            "【计算依据】",
            "  饱和蒸气压  : Magnus 近似公式",
            "  比焓        : h = 1.006·T + W·(2501 + 1.86·T)",
            "  比容        : v = 0.287·T_K·(1+1.608W) / P",
            "  湿球温度    : Newton-Raphson 迭代（能量平衡方程）",
            "  标准依据    : ASHRAE Fundamentals Handbook",
            "",
            "【工程参考】",
        ]

        # 舒适度
        rh_v = r["rh"]
        t = temp
        if 18 <= t <= 26 and 40 <= rh_v <= 65:
            lines.append("  舒适度  : ✅ 温湿度处于舒适区间（ASHRAE 55）")
        elif rh_v > 70:
            lines.append("  舒适度  : ⚠️  相对湿度偏高（>70%），注意防潮防霉")
        elif rh_v < 30:
            lines.append("  舒适度  : ⚠️  相对湿度偏低（<30%），建议增湿")
        else:
            lines.append(f"  舒适度  : 相对湿度 {rh_v:.1f}%，温度 {t:.1f}°C")

        # 结露风险
        if r["dew_point"] > t - 2:
            lines.append("  结露风险: ⚠️  露点温度接近干球温度，管道/设备表面易结露")
        else:
            lines.append(f"  结露风险: 露点 {r['dew_point']:.1f}°C，干球 {t:.1f}°C，差 {t-r['dew_point']:.1f}K，无结露风险")

        lines.append("=" * 50)
        self.result_text.setPlainText("\n".join(lines))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"⚠️  错误：{msg}")

    # ──────────────────────── 清空 ─────────────────────────────────
    def clear_inputs(self):
        self.temp_input.clear()
        self.pressure_input.setText("101.325")
        self.rh_input.clear()
        self.humidity_input.clear()
        self.wet_bulb_input.clear()
        self.dew_point_input.clear()
        self.result_text.clear()
        self._last_results = {}

    # ──────────────────────── 历史 ─────────────────────────────────
    def _get_history_data(self):
        r = self._last_results
        return {
            "inputs": {
                "干球温度_C": getattr(self, "_last_temp", 0),
                "压力_kPa": getattr(self, "_last_pressure", 101.325),
            },
            "outputs": {
                "相对湿度_%": round(r.get("rh", 0), 2),
                "绝对湿度_g_kg": round(r.get("W", 0) * 1000, 4),
                "露点温度_C": round(r.get("dew_point", 0), 2),
                "湿球温度_C": round(r.get("wet_bulb", 0), 2),
                "比焓_kJ_kg": round(r.get("enthalpy", 0), 3),
                "比容_m3_kg": round(r.get("specific_volume", 0), 4),
                "水蒸气分压_kPa": round(r.get("p_v", 0), 4),
            }
        }

    def get_project_info(self):
        return {"calculator": "WetAirCalculator", "name": "湿空气计算"}

    # ──────────────────────── 报告 ─────────────────────────────────
    def generate_report(self):
        return self.result_text.toPlainText()

    def download_txt_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先执行计算，再下载报告。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存TXT报告", "湿空气计算报告.txt", "文本文件 (*.txt)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "成功", f"报告已保存到：\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败：{e}")

    def generate_pdf_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先执行计算，再下载PDF。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存PDF报告", "湿空气计算报告.pdf", "PDF文件 (*.pdf)"
        )
        if not path:
            return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.enums import TA_LEFT
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            # 注册中文字体（兼容Windows）
            font_paths = [
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simsun.ttc",
            ]
            font_registered = False
            for fp in font_paths:
                if os.path.exists(fp):
                    try:
                        pdfmetrics.registerFont(TTFont("ChineseFont", fp))
                        font_registered = True
                        break
                    except Exception:
                        continue
            font_name = "ChineseFont" if font_registered else "Helvetica"

            doc = SimpleDocTemplate(path, pagesize=A4,
                                    leftMargin=20*mm, rightMargin=20*mm,
                                    topMargin=20*mm, bottomMargin=20*mm)
            styles = getSampleStyleSheet()
            body_style = ParagraphStyle(
                "Body", fontName=font_name, fontSize=10,
                leading=16, alignment=TA_LEFT
            )
            story = []
            for line in content.split("\n"):
                safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(safe if safe.strip() else "&nbsp;", body_style))
                story.append(Spacer(1, 1))
            doc.build(story)
            QMessageBox.information(self, "成功", f"PDF已保存到：\n{path}")
        except ImportError:
            QMessageBox.critical(self, "错误", "缺少 reportlab 库，请运行：pip install reportlab")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"PDF生成失败：{e}")


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = WetAirCalculator()
    w.resize(1200, 750)
    w.show()
    sys.exit(app.exec())
