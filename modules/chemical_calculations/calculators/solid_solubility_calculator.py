import os
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QProgressBar,
    QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QDoubleValidator
import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K, G, ATM_PRESSURE_MPA, WATER_DENSITY, WATER_CP, load_steam_iapws, get_steam_props
# DOCX 报告导出
from utils.docx_utils import ReportExporter



class SolubilityWorker(QThread):
    """溶解度查询工作线程"""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, compound, solvent, temperature):
        super().__init__()
        self.compound = compound
        self.solvent = solvent
        self.temperature = temperature

    def run(self):
        try:
            self.msleep(400)
            result = self.query_solubility_data(
                self.compound, self.solvent, self.temperature)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def query_solubility_data(self, compound, solvent, temperature):
        """查询溶解度数据"""
        db = self.get_solubility_database()
        key = f"{compound}_{solvent}"
        if key in db:
            base = db[key]
            sol = self.calculate_temperature_effect(base, temperature)
            # 置信度：多锚点查表 High；单点/定性 Medium
            n_anchor = len(base.get("table", [])) if base.get("table") else 0
            if base.get("unit") == "定性":
                confidence, method = "Medium", "定性判断"
            elif n_anchor >= 3:
                confidence, method = "High", "手册数据查表插值"
            elif n_anchor >= 2:
                confidence, method = "Medium", "两点插值"
            else:
                confidence, method = "Medium", "单点基准值"
            # 判断是否区间外推
            extrapolated = False
            if base.get("table"):
                ts = [p[0] for p in base["table"]]
                if temperature < ts[0] or temperature > ts[-1]:
                    extrapolated = True
            return {
                "compound": compound,
                "solvent": solvent,
                "temperature": temperature,
                "solubility": sol,
                "unit": base["unit"],
                "temperature_range": base.get("temperature_range", "0-100"),
                "source": base.get("source", "Handbook"),
                "notes": base.get("notes", ""),
                "method": method,
                "extrapolated": extrapolated,
                "confidence": confidence,
            }
        return {
            "compound": compound,
            "solvent": solvent,
            "temperature": temperature,
            "solubility": "N/A",
            "unit": "g/100g",
            "temperature_range": "N/A",
            "source": "Not Found",
            "notes": "内置数据库暂无该化合物-溶剂组合的数据，请查 CRC Handbook 等手册",
            "method": "",
            "extrapolated": False,
            "confidence": "Low",
        }

    @staticmethod
    def _interp_solubility(table, temperature):
        """锚点表线性插值；区间外用端部两点斜率外推"""
        if not table:
            return None
        if len(table) == 1:
            return table[0][1]
        xs = [p[0] for p in table]
        ys = [p[1] for p in table]
        if temperature <= xs[0]:
            k = (ys[1] - ys[0]) / (xs[1] - xs[0])
            return max(0.0, ys[0] + k * (temperature - xs[0]))
        if temperature >= xs[-1]:
            k = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
            return max(0.0, ys[-1] + k * (temperature - xs[-1]))
        for i in range(len(table) - 1):
            if xs[i] <= temperature <= xs[i + 1]:
                f = (temperature - xs[i]) / (xs[i + 1] - xs[i])
                return ys[i] + f * (ys[i + 1] - ys[i])
        return None

    def calculate_temperature_effect(self, base_data, temperature):
        """温度修正

        ⚠ 2026-09-13 重写：旧实现"单点 + 指数外推"误差极大
        （NaCl 100°C 算出 53.3，实际 39.1；Na2SO4 在 32.4°C 转折点
        完全无法表达，偏差 -26），改为"多锚点 + 线性插值"。
        table 数据来源: CRC Handbook / 大学化学教材溶解度表。
        """
        table = base_data.get("table")
        if table:
            return self._interp_solubility(table, temperature)
        if "solubility" not in base_data:
            return "N/A"
        base_temp = base_data.get("base_temperature", 25)
        base_sol = base_data["solubility"]
        if abs(temperature - base_temp) < 0.1:
            return base_sol
        if not isinstance(base_sol, (int, float)):
            return base_sol
        tc = base_data.get("temperature_coefficient", 0.02)
        tc = max(-0.05, min(0.10, tc))
        return max(0, base_sol * math.exp(tc * (temperature - base_temp)))

    @staticmethod
    def get_solubility_database():
        """内置溶解度数据库（2026-09-13 扩充：多锚点查表）

        table: [(温度°C, 溶解度 g/100g 水), ...] 多锚点，线性插值
        数据来源: CRC Handbook 化学与物理手册 / 大学化学教材溶解度表
        （KNO3/NaCl/KCl/NH4Cl/CuSO4/Na2SO4 等为教材级经典数据）
        """
        return {
            # ── 水溶液（多锚点，教材级数据） ──
            "氯化钠_水": {
                "table": [(0,35.7),(10,35.8),(20,36.0),(30,36.3),(40,36.6),
                          (50,37.0),(60,37.3),(70,37.8),(80,38.4),(90,39.0),(100,39.8)],
                "unit": "g/100g", "temperature_range": "0-100",
                "source": "CRC Handbook",
                "notes": "溶解度随温度变化很小；100°C 实际 39.8（旧模型算 53.3）"
            },
            "氯化钾_水": {
                "table": [(0,28.0),(20,34.2),(40,40.1),(60,45.8),(80,51.3),(100,56.3)],
                "unit": "g/100g", "temperature_range": "0-100",
                "source": "CRC Handbook",
                "notes": "溶解度随温度升高明显增加"
            },
            "硝酸钾_水": {
                "table": [(0,13.3),(10,20.9),(20,31.6),(30,45.8),(40,63.9),
                          (50,85.5),(60,110.0),(70,138.0),(80,169.0),(90,202.0),(100,246.0)],
                "unit": "g/100g", "temperature_range": "0-100",
                "source": "CRC Handbook / 教材溶解度表",
                "notes": "温度敏感性最强的常见盐之一，适用于冷却结晶"
            },
            "氯化铵_水": {
                "table": [(0,29.4),(20,37.2),(40,45.8),(60,55.3),(80,65.6),(100,77.3)],
                "unit": "g/100g", "temperature_range": "0-100",
                "source": "CRC Handbook",
                "notes": "溶解度随温度升高增加"
            },
            "硫酸钠_水": {
                "table": [(0,4.9),(10,9.6),(20,19.5),(30,40.8),(32.4,49.6),
                          (40,48.8),(50,46.7),(60,45.3),(80,43.7),(100,42.5)],
                "unit": "g/100g", "temperature_range": "0-100",
                "source": "CRC Handbook",
                "notes": "32.4°C 出现峰值（十水物→无水物转变点），此后随温度略降"
            },
            "硫酸铜_水": {
                "table": [(0,14.3),(10,17.4),(20,20.7),(30,25.0),(40,28.5),
                          (60,40.0),(80,55.0),(100,75.4)],
                "unit": "g/100g", "temperature_range": "0-100",
                "source": "CRC Handbook",
                "notes": "以无水 CuSO4 计；五水物结晶析出温度约 25°C 以下"
            },
            "碳酸氢钠_水": {
                "table": [(0,6.9),(20,9.6),(40,12.7),(60,16.4)],
                "unit": "g/100g", "temperature_range": "0-60",
                "source": "CRC Handbook",
                "notes": ">60°C 逐渐分解为 Na2CO3，慎用于高温"
            },
            "氢氧化钙_水": {
                "table": [(0,0.185),(20,0.165),(40,0.141),(60,0.116),(80,0.094),(100,0.077)],
                "unit": "g/100g", "temperature_range": "0-100",
                "source": "CRC Handbook",
                "notes": "典型的逆溶解度（温度升高溶解度下降）"
            },
            "碳酸钙_水": {
                "table": [(25,0.0014)],
                "unit": "g/100g", "temperature_range": "0-100",
                "source": "CRC Handbook",
                "notes": "方解石；随温度升高略降；值极小，工程上按不溶处理"
            },
            "硫酸钡_水": {
                "table": [(25,0.00023)],
                "unit": "g/100g", "temperature_range": "0-100",
                "source": "CRC Handbook",
                "notes": "极难溶（Ksp≈1.1×10⁻¹⁰），水处理/钡餐常用"
            },
            "蔗糖_水": {
                "table": [(0,179.2),(20,203.9),(30,219.5),(40,238.1),
                          (50,260.4),(60,287.3),(70,320.5),(80,362.1)],
                "unit": "g/100g", "temperature_range": "0-80",
                "source": "ICUMSA",
                "notes": "20°C 溶解度 203.9（旧库误标 211.5/20°C）"
            },
            "苯甲酸_水": {
                "table": [(20,0.29),(25,0.34),(40,0.56),(60,1.16),(80,2.71),(95,6.80)],
                "unit": "g/100g", "temperature_range": "20-95",
                "source": "Merck Index / CRC",
                "notes": "微溶于冷水，热水重结晶常用体系"
            },
            "阿司匹林_水": {
                "table": [(25,0.33)],
                "unit": "g/100g", "temperature_range": "15-40",
                "source": "Merck Index",
                "notes": "微溶于水；>40°C 缓慢水解"
            },
            "咖啡因_水": {
                "table": [(25,2.17),(80,18.2)],
                "unit": "g/100g", "temperature_range": "25-80",
                "source": "Merck Index",
                "notes": "溶解度随温度显著增加"
            },
            # ── 非水溶剂（单点基准，精度有限） ──
            "氯化钠_乙醇": {
                "table": [(25,0.065)],
                "unit": "g/100g", "temperature_range": "0-78",
                "source": "Handbook",
                "notes": "在乙醇中溶解度很低"
            },
            "蔗糖_乙醇": {
                "table": [(25,0.6)],
                "unit": "g/100g", "temperature_range": "0-78",
                "source": "Handbook",
                "notes": "在乙醇中微溶"
            },
            "碘_乙醇": {
                "table": [(25,20.5)],
                "unit": "g/100g", "temperature_range": "0-78",
                "source": "Handbook",
                "notes": "易溶于乙醇"
            },
            "萘_乙醇": {
                "table": [(25,19.5)],
                "unit": "g/100g", "temperature_range": "0-78",
                "source": "Handbook",
                "notes": "在乙醇中溶解度较高（近似值）"
            },
            # ── 定性条目 ──
            "碳酸钙_盐酸": {
                "solubility": "可溶", "unit": "定性",
                "base_temperature": 25, "temperature_range": "0-100",
                "source": "Chemical Properties",
                "notes": "与酸反应生成可溶性盐"
            },
            "氢氧化铝_氢氧化钠": {
                "solubility": "可溶", "unit": "定性",
                "base_temperature": 25, "temperature_range": "0-100",
                "source": "Chemical Properties",
                "notes": "两性氢氧化物，溶于强碱"
            },
        }

class SolidSolubilityCalculator(CalculatorBase):
    """固体溶解度查询计算器（统一 UI 规范版）"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.data_manager = None
        self.worker = None
        self._last_result = {}
        self._query_pending = False
        self.setup_ui()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

    # ─────────────────────────── UI ─────────────────────────────
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ──────────────── 左侧输入区 ────────────────
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 说明文字
        desc = QLabel(
            "查询固体在不同溶剂和温度条件下的溶解度数据。"
            "数据来源包括 CRC Handbook、Merck Index 等。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc)

        # ── 查询条件组 ──
        query_group = QGroupBox("查询条件")
        grid = QGridLayout(query_group)
        grid.setSpacing(12)
        grid.setHorizontalSpacing(10)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)

        label_style = "font-weight: bold; padding-right: 10px;"
        hint_style = "font-style: italic;"

        def make_lbl(text):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet(label_style)
            return lbl

        # 行0：化合物
        self.compound_input = QComboBox()
        self.compound_input.setStyleSheet(COMBOBOX_STYLE)
        self.compound_input.setEditable(True)
        self.compound_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.compound_input.addItems([
            "氯化钠", "氯化钾", "硝酸钾", "氯化铵", "硫酸钠", "硫酸铜",
            "碳酸氢钠", "氢氧化钙", "碳酸钙", "硫酸钡",
            "蔗糖", "苯甲酸", "阿司匹林", "咖啡因",
            "碘", "萘", "氢氧化铝",
        ])
        grid.addWidget(make_lbl("化合物:"), 0, 0)
        grid.addWidget(self.compound_input, 0, 1)
        hint_c = QLabel("可选列表或手动输入")
        hint_c.setStyleSheet(hint_style)
        grid.addWidget(hint_c, 0, 2)

        # 行1：溶剂
        self.solvent_input = QComboBox()
        self.solvent_input.setStyleSheet(COMBOBOX_STYLE)
        self.solvent_input.setEditable(True)
        self.solvent_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.solvent_input.addItems([
            "水", "乙醇", "甲醇", "丙酮",
            "乙醚", "苯", "氯仿", "盐酸",
            "氢氧化钠", "硫酸",
        ])
        grid.addWidget(make_lbl("溶剂:"), 1, 0)
        grid.addWidget(self.solvent_input, 1, 1)
        hint_s = QLabel("可选列表或手动输入")
        hint_s.setStyleSheet(hint_style)
        grid.addWidget(hint_s, 1, 2)

        # 行2：温度
        self.temperature_input = QLineEdit("25")
        self.temperature_input.setValidator(QDoubleValidator(-273, 500, 1))
        self.temperature_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(make_lbl("温度:"), 2, 0)
        grid.addWidget(self.temperature_input, 2, 1)
        hint_t = QLabel("°C")
        hint_t.setStyleSheet(hint_style)
        grid.addWidget(hint_t, 2, 2)

        left_layout.addWidget(query_group)

        # ── 参考数据表 ──
        ref_group = QGroupBox("常见固体溶解度参考表")
        ref_vbox = QVBoxLayout(ref_group)

        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(
            ["化合物", "溶剂", "温度(°C)", "溶解度", "单位"])
        ref_header = self.data_table.horizontalHeader()
        ref_header.setSectionResizeMode(QHeaderView.Stretch)
        self._populate_reference_table()
        ref_vbox.addWidget(self.data_table)
        left_layout.addWidget(ref_group)

        # ──────────────── 右侧结果区 ────────────────
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        result_group = QGroupBox("查询结果")
        result_vbox = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setStyleSheet(
            "QTextEdit { "
            "font-family: Consolas, 'Microsoft YaHei', monospace; "
            "font-size: 13px; "
            "}"
        )
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        result_vbox.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # ── 下载按钮行（右侧）：清空 → DOCX → PDF ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        for label, style, slot in [
            ("清空", CLEAR_BTN_STYLE, self.clear_inputs),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        right_layout.addLayout(btn_layout)

        # 进度条（查询中显示）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        # 计算按钮（最底部）
        calc_btn = self.make_calc_button("查 询")
        calc_btn.clicked.connect(self.query_solubility)
        right_layout.addWidget(calc_btn)

        # 拼合
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

    # ──────────────────── 参考表 ────────────────────────────────
    def _populate_reference_table(self):
        rows = [
            ["氯化钠", "水", "20", "36.0", "g/100g"],
            ["氯化钾", "水", "20", "34.2", "g/100g"],
            ["硝酸钾", "水", "20", "31.6", "g/100g"],
            ["氯化铵", "水", "20", "37.2", "g/100g"],
            ["硫酸钠", "水", "20", "19.5", "g/100g"],
            ["硫酸铜", "水", "20", "20.7", "g/100g"],
            ["氢氧化钙", "水", "20", "0.165", "g/100g"],
            ["碳酸钙", "水", "25", "0.0014", "g/100g"],
            ["硫酸钡", "水", "25", "0.00023", "g/100g"],
            ["蔗糖", "水", "20", "203.9", "g/100g"],
            ["苯甲酸", "水", "25", "0.34", "g/100g"],
            ["咖啡因", "水", "25", "2.17", "g/100g"],
            ["氯化钠", "乙醇", "25", "0.065", "g/100g"],
            ["碘", "乙醇", "25", "20.5", "g/100g"],
            ["萘", "乙醇", "25", "19.5", "g/100g"],
        ]
        self.data_table.setRowCount(len(rows))
        for i, rd in enumerate(rows):
            for j, v in enumerate(rd):
                self.data_table.setItem(i, j, QTableWidgetItem(str(v)))

    # ──────────────────── 单次查询 ──────────────────────────────
    def query_solubility(self):
        compound = self.compound_input.currentText().strip()
        solvent = self.solvent_input.currentText().strip()
        try:
            temperature = float(self.temperature_input.text())
        except ValueError:
            self._show_error("请输入有效的温度数值")
            return
        if not compound or not solvent:
            self._show_error("请输入化合物和溶剂名称")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        # 禁用所有按钮，查询中
        sender = self.sender()
        if sender:
            sender.setEnabled(False)

        # ⚠ 防重入：上一次查询线程仍在运行时不能再新建线程。
        # 否则 self.worker 引用被覆盖，仍在运行的 QThread 被 Python GC 回收，
        # 会在 C++ 层直接崩溃（整个软件闪退，无异常可捕获）。
        old = getattr(self, "worker", None)
        if old is not None and old.isRunning():
            if sender:
                sender.setEnabled(True)
            self.progress_bar.setVisible(False)
            self._show_error("上一次查询尚未完成，请稍候再试")
            return

        self._query_pending = True
        self.worker = SolubilityWorker(compound, solvent, temperature)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self._query_btn_ref = sender
        self.worker.start()

    def _on_finished(self, result):
        self._query_pending = False
        self.progress_bar.setVisible(False)
        if hasattr(self, "_query_btn_ref") and self._query_btn_ref:
            self._query_btn_ref.setEnabled(True)
        self._last_result = result
        self._display(result)

        # 异步查询完成后保存历史记录
        meta = getattr(self, "_calc_meta", None)
        if meta:
            try:
                from modules.history_db import HistoryDB
                data = self._get_history_data()
                if data and data.get("inputs"):
                    HistoryDB().save(
                        calculator_id=meta["id"],
                        calculator_name=meta["name"],
                        calculator_category=meta.get("category", ""),
                        inputs=data.get("inputs", {}),
                        outputs=data.get("outputs", {}),
                        notes=data.get("notes", ""),
                    )
            except Exception:
                pass

        

    def _on_error(self, msg):
        self.progress_bar.setVisible(False)
        if hasattr(self, "_query_btn_ref") and self._query_btn_ref:
            self._query_btn_ref.setEnabled(True)
        self._show_error(f"查询错误：{msg}")

    # ──────────────────── 结果显示 ──────────────────────────────
    def _display(self, r):
        sol_val = r["solubility"]
        sol_str = (f"{sol_val:.4f}" if isinstance(sol_val, (int, float))
                   else str(sol_val))

        # 溶解度分级
        grade = ""
        if isinstance(sol_val, (int, float)):
            if sol_val >= 10:
                grade = "易溶"
            elif sol_val >= 1:
                grade = "可溶"
            elif sol_val >= 0.1:
                grade = "微溶"
            elif sol_val > 0:
                grade = "难溶"
            else:
                grade = "不溶"

        conf_icon = {"High": "✅", "Medium": "⚠️", "Low": "❌"}.get(
            r["confidence"], "")

        lines = [
            "=" * 50,
            "       固体溶解度查询结果",
            "=" * 50,
            "",
            "【查询条件】",
            f"  化合物       : {r['compound']}",
            f"  溶剂         : {r['solvent']}",
            f"  温度         : {r['temperature']} °C",
            "",
            "【查询结果】",
            f"  溶解度       : {sol_str} {r['unit']}",
        ]
        if grade:
            lines.append(f"  溶解度分级   : {grade}")
        lines += [
            f"  适用温度范围 : {r['temperature_range']} °C",
            f"  查询方式     : {r.get('method', '')}",
        ]
        if r.get("extrapolated"):
            lines.append("  ⚠ 查询温度超出锚点区间，已按端部斜率外推，精度下降")
        lines += [
            f"  数据来源     : {r['source']}",
            f"  置信度       : {conf_icon} {r['confidence']}",
            f"  备注         : {r['notes']}",
            "",
            "【溶解度分级标准】",
            "  易溶  : > 10 g/100g 溶剂",
            "  可溶  : 1 ~ 10 g/100g 溶剂",
            "  微溶  : 0.1 ~ 1 g/100g 溶剂",
            "  难溶  : < 0.1 g/100g 溶剂",
            "",
            "【数据说明】",
            "  多锚点数据按温度线性插值；区间外按端部斜率外推",
            "  锚点来源: CRC Handbook / 教材溶解度表 / ICUMSA",
            "=" * 50,
        ]
        self.result_text.setPlainText("\n".join(lines))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"⚠️  错误：{msg}")

    # ──────────────────── 清空 ───────────────────────────────────
    def clear_inputs(self):
        self.compound_input.setCurrentIndex(0)
        self.solvent_input.setCurrentIndex(0)
        self.temperature_input.setText("25")
        self.result_text.clear()
        self._last_result = {}

    # ──────────────────── 历史数据 ──────────────────────────────
    def _get_history_data(self):
        # 异步查询未完成时，返回空数据阻止 _save_history_for 保存
        if getattr(self, "_query_pending", False):
            return {"inputs": {}, "outputs": {}}
        r = self._last_result
        return {
            "inputs": {
                "化合物": r.get("compound", ""),
                "溶剂": r.get("solvent", ""),
                "温度_C": r.get("temperature", 0),
            },
            "outputs": {
                "溶解度": r.get("solubility", "N/A"),
                "单位": r.get("unit", ""),
                "数据来源": r.get("source", ""),
                "置信度": r.get("confidence", ""),
            }
        }

    def get_project_info(self):
        return {
            "calculator": "SolidSolubilityCalculator",
            "name": "固体溶解度查询",
        }

    # ──────────────────── 报告 ───────────────────────────────────
    def generate_report(self):
        return self.result_text.toPlainText()

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "固液溶解度")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "固液溶解度")
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = SolidSolubilityCalculator()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
