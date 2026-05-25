# ChemCal/modules/history_viewer.py
"""计算历史记录查看器"""
import json
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QTextEdit, QLineEdit, QComboBox, QPushButton,
    QGroupBox, QMessageBox, QSplitter, QSizePolicy, QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


class HistoryViewer(QWidget):
    """历史记录查看器"""

    PAGE_SIZE = 50

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self._db = None
        self._current_page = 0
        self._current_keyword = ""
        self._current_calculator = ""
        self._current_record = None
        self._total = 0
        self.setup_ui()

    @property
    def db(self):
        if self._db is None:
            from modules.history_db import HistoryDB
            self._db = HistoryDB()
            # 监听新记录，自动刷新列表
            self._db.record_added.connect(self._on_record_added)
        return self._db

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 左侧：筛选 + 列表
        left_widget = QWidget()
        left_widget.setFixedWidth(320)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 标题
        title = QLabel("计算历史")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("font-weight: bold; padding: 5px 0;")
        left_layout.addWidget(title)

        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索输入、输出、备注...")
        self.search_edit.setFixedHeight(32)
        self.search_edit.textChanged.connect(self._on_search_changed)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #666;
                border-radius: 6px;
                padding: 0 10px;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #3498db; }
        """)
        left_layout.addWidget(self.search_edit)

        # 计算器筛选
        self.calc_filter = QComboBox()
        self.calc_filter.setFixedHeight(32)
        self.calc_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.calc_filter.setStyleSheet("""
            QComboBox {
                border: 1px solid #666;
                border-radius: 6px;
                padding: 0 10px;
                font-size: 13px;
            }
        """)
        left_layout.addWidget(self.calc_filter)

        # 历史列表
        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        self.history_list.setAlternatingRowColors(True)
        self.history_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_list.itemClicked.connect(self._on_item_clicked)
        left_layout.addWidget(self.history_list, 1)

        # 分页信息
        self.page_label = QLabel("共 0 条记录")
        self.page_label.setStyleSheet("font-size: 12px; padding: 4px;")
        left_layout.addWidget(self.page_label)

        # 右侧：详情
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(8)
        right_layout.setContentsMargins(0, 0, 0, 0)

        detail_title = QLabel("记录详情")
        detail_title.setFont(QFont("Arial", 14, QFont.Bold))
        detail_title.setStyleSheet("font-weight: bold; padding: 5px 0;")
        right_layout.addWidget(detail_title)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setObjectName("historyDetailText")
        right_layout.addWidget(self.detail_text, 1)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.load_more_btn = QPushButton("加载更多")
        self.load_more_btn.setFixedHeight(32)
        self.load_more_btn.clicked.connect(self._load_more)
        self.load_more_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
            }
            QPushButton:hover { background: #2980b9; }
        """)
        btn_layout.addWidget(self.load_more_btn)

        self.delete_btn = QPushButton("删除此条")
        self.delete_btn.setFixedHeight(32)
        self.delete_btn.clicked.connect(self._delete_record)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
            }
            QPushButton:hover { background: #c0392b; }
        """)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)

        right_layout.addLayout(btn_layout)

        # 添加到主布局
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget, 1)

        self._refresh_filter()
        self._load_history()

    def _refresh_filter(self):
        """刷新计算器筛选下拉"""
        self.calc_filter.blockSignals(True)
        self.calc_filter.clear()
        self.calc_filter.addItem("全部计算器", "")
        calcs = self.db.get_calculator_ids()
        for cid, cname in sorted(calcs.items(), key=lambda x: x[1]):
            self.calc_filter.addItem(cname, cid)
        self.calc_filter.blockSignals(False)

    def _load_history(self, append=False):
        """加载历史记录"""
        if not append:
            self._current_page = 0
            # 不用 clear()——PySide6 在某些条件下 clear() 会触发 access violation
            # 改为逐条 takeItem 安全移除（takeItem 不触发内部 mass-deletion）
            self.history_list.blockSignals(True)
            while self.history_list.count() > 0:
                item = self.history_list.takeItem(0)
                del item
            self.history_list.blockSignals(False)

        records, total = self.db.get_all(
            calculator_id=self._current_calculator or None,
            keyword=self._current_keyword,
            limit=self.PAGE_SIZE,
            offset=self._current_page * self.PAGE_SIZE
        )
        self._total = total

        for rec in records:
            item = QListWidgetItem()
            dt = datetime.fromisoformat(rec["created_at"])
            label = dt.strftime("%m-%d %H:%M")
            inputs_preview = self._format_inputs_preview(rec["inputs"])
            item.setText(f"{rec['calculator_name']}  {label}\n{inputs_preview}")
            item.setData(Qt.UserRole, rec["id"])
            item.setSizeHint(item.sizeHint())
            self.history_list.addItem(item)

        self._update_page_label()
        return records

    def _load_more(self):
        self._current_page += 1
        self._load_history(append=True)

    def _update_page_label(self):
        shown = self.history_list.count()
        self.page_label.setText(f"共 {self._total} 条记录 (显示 {shown} 条)")

    def _on_record_added(self):
        """收到新记录信号时刷新列表（延迟执行，避免在信号链中操作 Qt 控件）"""
        QTimer.singleShot(0, self._load_history)

    def _on_search_changed(self, text):
        self._current_keyword = text
        self._current_page = 0
        self._load_history()
        self.detail_text.clear()
        self._current_record = None
        self.delete_btn.setEnabled(False)

    def _on_filter_changed(self, index):
        self._current_calculator = self.calc_filter.currentData()
        self._current_page = 0
        self._load_history()
        self.detail_text.clear()
        self._current_record = None
        self.delete_btn.setEnabled(False)

    def _on_item_clicked(self, item):
        record_id = item.data(Qt.UserRole)
        records, _ = self.db.get_all(keyword="", limit=1000, offset=0)
        rec = next((r for r in records if r["id"] == record_id), None)
        if rec is None:
            # 从当前页找
            rec = self._find_record_in_list(record_id)

        self._current_record = rec
        self.delete_btn.setEnabled(rec is not None)
        if rec:
            self.detail_text.setHtml(self._format_detail(rec))

    def _find_record_in_list(self, record_id):
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            if item.data(Qt.UserRole) == record_id:
                records, _ = self.db.get_all(
                    keyword=self._current_keyword,
                    calculator_id=self._current_calculator or None,
                    limit=1000,
                    offset=0
                )
                return next((r for r in records if r["id"] == record_id), None)
        return None

    def _format_inputs_preview(self, inputs):
        if not inputs:
            return ""
        parts = [f"{k}={v}" for k, v in list(inputs.items())[:3]]
        suffix = " ..." if len(inputs) > 3 else ""
        return " | ".join(parts) + suffix

    def _format_detail(self, rec):
        dt = datetime.fromisoformat(rec["created_at"])
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <div style="font-family: Arial; font-size: 14px; color: #2c3e50;">
            <div style="background: #3498db; color: white; padding: 10px 14px;
                        border-radius: 6px; margin-bottom: 12px; font-size: 15px; font-weight: bold;">
                {rec['calculator_name']}
            </div>
            <div style="color: #7f8c8d; font-size: 12px; margin-bottom: 12px;">
                {dt_str} &nbsp;|&nbsp; {rec['calculator_category'] or '未分类'}
            </div>
        """

        if rec.get("inputs"):
            html += """
            <div style="margin-bottom: 12px;">
                <div style="font-weight: bold; color: #2980b9; margin-bottom: 6px;
                            border-left: 3px solid #3498db; padding-left: 8px;">输入参数</div>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
            """
            for k, v in rec["inputs"].items():
                html += f"""
                    <tr style="border-bottom: 1px solid #ecf0f1;">
                        <td style="padding: 4px 8px; color: #7f8c8d; white-space: nowrap;">{k}</td>
                        <td style="padding: 4px 8px; color: #2c3e50; font-weight: bold;">{v}</td>
                    </tr>
                """
            html += "</table></div>"

        if rec.get("outputs"):
            html += """
            <div style="margin-bottom: 12px;">
                <div style="font-weight: bold; color: #27ae60; margin-bottom: 6px;
                            border-left: 3px solid #27ae60; padding-left: 8px;">计算结果</div>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
            """
            for k, v in rec["outputs"].items():
                v_html = str(v).replace("\n", "<br>")
                html += f"""
                    <tr style="border-bottom: 1px solid #ecf0f1;">
                        <td style="padding: 4px 8px; color: #7f8c8d; white-space: nowrap;">{k}</td>
                        <td style="padding: 4px 8px; color: #27ae60; font-weight: bold;">{v_html}</td>
                    </tr>
                """
            html += "</table></div>"

        if rec.get("notes"):
            html += f"""
            <div>
                <div style="font-weight: bold; color: #e67e22; margin-bottom: 6px;
                            border-left: 3px solid #e67e22; padding-left: 8px;">备注</div>
                <div style="background: #fef9e7; border-radius: 6px; padding: 8px;
                            font-size: 13px; color: #2c3e50;">{rec['notes']}</div>
            </div>
            """

        html += "</div>"
        return html

    def _delete_record(self):
        if self._current_record is None:
            return
        record_id = self._current_record["id"]
        name = self._current_record["calculator_name"]
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除这条「{name}」记录吗？\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self.db.delete(record_id)
        self.detail_text.clear()
        self._current_record = None
        self.delete_btn.setEnabled(False)
        self._current_page = 0
        self._load_history()
        self._refresh_filter()

    def refresh(self):
        """外部刷新调用"""
        self._current_page = 0
        self._refresh_filter()
        self._load_history()
