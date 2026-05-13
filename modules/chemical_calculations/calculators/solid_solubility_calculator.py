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


COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 6px 10px;
        background: white;
        color: black;
    }
    QComboBox QAbstractItemView {
        background-color: white;
        color: black;
        border: 1px solid #bdc3c7;
        selection-background-color: #3498db;
        selection-color: black;
    }
    QComboBox QAbstractItemView::item {
        padding: 3px 8px;
    }
"""

GROUP_STYLE = """
    QGroupBox {
        font-weight: bold;
        border: 1px solid #bdc3c7;
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
            return {
                "compound": compound,
                "solvent": solvent,
                "temperature": temperature,
                "solubility": sol,
                "unit": base["unit"],
                "temperature_range": base.get("temperature_range", "0-100"),
                "source": base.get("source", "Handbook"),
                "notes": base.get("notes", ""),
                "confidence": "High",
            }
        return {
            "compound": compound,
            "solvent": solvent,
            "temperature": temperature,
            "solubility": "N/A",
            "unit": "g/100g",
            "temperature_range": "N/A",
            "source": "Not Found",
            "notes": "No data available for this compound-solvent pair",
            "confidence": "Low",
        }

    def calculate_temperature_effect(self, base_data, temperature):
        """温度修正（指数型模型）"""
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
        """内置溶解度数据库"""
        return {
            "氯化钠_水": {
                "solubility": 35.7, "unit": "g/100g",
                "base_temperature": 20, "temperature_coefficient": 0.005,
                "temperature_range": "0-100", "source": "CRC Handbook",
                "notes": "温度对溶解度影响较小"
            },
            "氯化钾_水": {
                "solubility": 34.0, "unit": "g/100g",
                "base_temperature": 20, "temperature_coefficient": 0.008,
                "temperature_range": "0-100", "source": "CRC Handbook",
                "notes": "溶解度随温度升高而增加"
            },
            "硫酸钠_水": {
                "solubility": 19.5, "unit": "g/100g",
                "base_temperature": 20, "temperature_coefficient": 0.015,
                "temperature_range": "0-32.4", "source": "CRC Handbook",
                "notes": "在32.4°C时溶解度最大"
            },
            "碳酸钙_水": {
                "solubility": 0.0014, "unit": "g/100g",
                "base_temperature": 25, "temperature_coefficient": -0.02,
                "temperature_range": "0-100", "source": "CRC Handbook",
                "notes": "溶解度随温度升高而降低"
            },
            "蔗糖_水": {
                "solubility": 211.5, "unit": "g/100g",
                "base_temperature": 20, "temperature_coefficient": 0.025,
                "temperature_range": "0-100", "source": "CRC Handbook",
                "notes": "溶解度随温度显著增加"
            },
            "苯甲酸_水": {
                "solubility": 0.34, "unit": "g/100g",
                "base_temperature": 25, "temperature_coefficient": 0.03,
                "temperature_range": "0-100", "source": "Merck Index",
                "notes": "微溶于冷水，易溶于热水"
            },
            "阿司匹林_水": {
                "solubility": 0.33, "unit": "g/100g",
                "base_temperature": 25, "temperature_coefficient": 0.02,
                "temperature_range": "15-40", "source": "Merck Index",
                "notes": "微溶于水"
            },
            "咖啡因_水": {
                "solubility": 2.17, "unit": "g/100g",
                "base_temperature": 25, "temperature_coefficient": 0.04,
                "temperature_range": "0-100", "source": "Merck Index",
                "notes": "溶解度随温度显著增加"
            },
            "氯化钠_乙醇": {
                "solubility": 0.065, "unit": "g/100g",
                "base_temperature": 25, "temperature_coefficient": 0.01,
                "temperature_range": "0-78", "source": "Handbook",
                "notes": "在乙醇中溶解度很低"
            },
            "蔗糖_乙醇": {
                "solubility": 0.6, "unit": "g/100g",
                "base_temperature": 20, "temperature_coefficient": 0.015,
                "temperature_range": "0-78", "source": "Handbook",
                "notes": "在乙醇中微溶"
            },
            "碘_乙醇": {
                "solubility": 20.5, "unit": "g/100g",
                "base_temperature": 25, "temperature_coefficient": 0.02,
                "temperature_range": "0-78", "source": "Handbook",
                "notes": "易溶于乙醇"
            },
            "萘_乙醇": {
                "solubility": 19.5, "unit": "g/100g",
                "base_temperature": 25, "temperature_coefficient": 0.025,
                "temperature_range": "0-78", "source": "Handbook",
                "notes": "在乙醇中溶解度较高"
            },
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


class SolidSolubilityCalculator(QWidget):
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
        left_widget.setStyleSheet("QWidget { background: transparent; }")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        # 说明文字
        desc = QLabel(
            "查询固体在不同溶剂和温度条件下的溶解度数据。"
            "数据来源包括 CRC Handbook、Merck Index 等。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; font-size: 12px; padding: 5px;")
        left_layout.addWidget(desc)

        # ── 查询条件组 ──
        query_group = QGroupBox("查询条件")
        query_group.setStyleSheet(GROUP_STYLE)
        grid = QGridLayout(query_group)
        grid.setSpacing(12)
        grid.setHorizontalSpacing(10)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 5)

        label_style = "font-weight: bold; padding-right: 10px;"
        hint_style = "color: #7f8c8d; font-style: italic;"

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
            "氯化钠", "氯化钾", "硫酸钠", "碳酸钙",
            "蔗糖", "苯甲酸", "阿司匹林", "咖啡因",
            "碘", "萘", "氢氧化铝", "硫酸钡",
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

        # ── 查询按钮 ──
        calc_btn = QPushButton("查询")
        calc_btn.setFont(QFont("Arial", 12))
        calc_btn.setMinimumHeight(50)
        calc_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        calc_btn.clicked.connect(self.query_solubility)
        left_layout.addWidget(calc_btn)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        # ── 参考数据表 ──
        ref_group = QGroupBox("常见固体溶解度参考表")
        ref_group.setStyleSheet(GROUP_STYLE)
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
        result_group.setStyleSheet(GROUP_STYLE)
        result_vbox = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(500)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #ecf0f1;
                border-radius: 6px;
                font-size: 13px;
                padding: 8px;
            }
        """)
        self.result_text.setPlaceholderText("查询结果将在此显示……")
        result_vbox.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        # ── 底部按钮行（右侧） ──
        btn_row = QHBoxLayout()

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_inputs)
        self.clear_btn.setMinimumHeight(50)
        self.clear_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.clear_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #95a5a6; color: white; "
            "font-weight: bold; border: none; border-radius: 6px; padding: 8px; "
            "}"
            "QPushButton:hover { background-color: #7f8c8d; }"
        )

        self.dl_txt_btn = QPushButton("下载计算书(TXT)")
        self.dl_txt_btn.clicked.connect(self.download_txt_report)
        self.dl_txt_btn.setMinimumHeight(50)
        self.dl_txt_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.dl_txt_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #27ae60; color: white; "
            "font-weight: bold; border: none; border-radius: 6px; padding: 8px; "
            "}"
            "QPushButton:hover { background-color: #219653; }"
        )

        self.dl_pdf_btn = QPushButton("下载计算书(PDF)")
        self.dl_pdf_btn.clicked.connect(self.generate_pdf_report)
        self.dl_pdf_btn.setMinimumHeight(50)
        self.dl_pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.dl_pdf_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #e74c3c; color: white; "
            "font-weight: bold; border: none; border-radius: 6px; padding: 8px; "
            "}"
            "QPushButton:hover { background-color: #c0392b; }"
        )

        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.dl_txt_btn)
        btn_row.addWidget(self.dl_pdf_btn)
        right_layout.addLayout(btn_row)

        # 拼合
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)

    # ──────────────────── 参考表 ────────────────────────────────
    def _populate_reference_table(self):
        rows = [
            ["氯化钠", "水", "20", "35.7", "g/100g"],
            ["氯化钾", "水", "20", "34.0", "g/100g"],
            ["硫酸钠", "水", "20", "19.5", "g/100g"],
            ["碳酸钙", "水", "25", "0.0014", "g/100g"],
            ["蔗糖", "水", "20", "211.5", "g/100g"],
            ["苯甲酸", "水", "25", "0.34", "g/100g"],
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
            "  温度修正模型 : S(T) = S(T0) * exp(α·(T - T0))",
            "  α 为温度系数，基于基准温度 T0 处的溶解度值",
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

    def download_txt_report(self):
        content = self.result_text.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "请先查询，再下载报告。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存TXT报告", "溶解度查询报告.txt", "文本文件 (*.txt)")
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
            QMessageBox.warning(self, "提示", "请先查询，再下载PDF。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存PDF报告", "溶解度查询报告.pdf", "PDF文件 (*.pdf)")
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

            font_paths = [
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simsun.ttc",
            ]
            font_name = "Helvetica"
            for fp in font_paths:
                if os.path.exists(fp):
                    try:
                        pdfmetrics.registerFont(TTFont("CF", fp))
                        font_name = "CF"
                        break
                    except Exception:
                        continue

            doc = SimpleDocTemplate(
                path, pagesize=A4,
                leftMargin=20 * mm, rightMargin=20 * mm,
                topMargin=20 * mm, bottomMargin=20 * mm)
            styles = getSampleStyleSheet()
            st = ParagraphStyle(
                "Body", fontName=font_name, fontSize=10,
                leading=16, alignment=TA_LEFT)
            story = []
            for line in content.split("\n"):
                safe = line.replace("&", "&amp;").replace(
                    "<", "&lt;").replace(">", "&gt;")
                story.append(
                    Paragraph(safe if safe.strip() else "&nbsp;", st))
                story.append(Spacer(1, 1))
            doc.build(story)
            QMessageBox.information(self, "成功", f"PDF已保存到：\n{path}")
        except ImportError:
            QMessageBox.critical(
                self, "错误", "缺少 reportlab 库，请运行：pip install reportlab")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"PDF生成失败：{e}")


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = SolidSolubilityCalculator()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
