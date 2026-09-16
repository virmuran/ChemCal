# ChemCal/modules/history_viewer.py
"""计算历史记录查看器

功能：筛选（关键词 / 计算器 / 时间范围）、多选、详情、使用统计、
      导出（CSV / DOCX / PDF）、单条删除 / 批量删除 / 按筛选清空。

颜色约定：页面控件一律不写颜色（交给 theme_manager 的 QSS），
富文本（详情、统计）从 get_content_colors() 取色 —— Qt 富文本读不到 QSS。
"""
import csv
from datetime import datetime, timedelta
from html import escape as _esc

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QTextEdit, QLineEdit, QComboBox, QPushButton,
    QMessageBox, QAbstractItemView, QFileDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from theme_manager import get_content_colors


#: 时间范围预设：(显示文本, 编码)。编码由 _current_range() 解释。
TIME_RANGES = [
    ("全部时间", "all"),
    ("今天", "today"),
    ("近 7 天", "7d"),
    ("近 30 天", "30d"),
    ("本月", "month"),
]


class HistoryViewer(QWidget):
    """历史记录查看器"""

    PAGE_SIZE = 50
    #: 导出上限 —— 与 HistoryDB.MAX_ROWS 一致，避免一次导出把内存和 Word 拖死
    EXPORT_LIMIT = 100000
    #: 统计条形的最大像素宽。Qt 富文本对"百分比宽度"支持不可靠（实测 50% 可能被
    #: 渲染成 33%~100% 之间任何值），所以条长一律按像素算、由这里统一缩放。
    BAR_MAX_PX = 360

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self._db = None
        self._current_page = 0
        self._current_keyword = ""
        self._current_calculator = ""
        self._range_code = "all"
        self._current_record = None
        self._total = 0
        #: 右栏当前模式："detail" 详情 / "statistics" 统计
        self._right_mode = "detail"
        #: 危险操作二次确认开关。测试里置 False 以便离屏直接跑逻辑
        #: （离屏环境下 QMessageBox.exec() 会永久阻塞）。
        self.confirm_enabled = True
        self.setup_ui()

    # ── 数据层 ────────────────────────────────────────────────────

    @property
    def db(self):
        if self._db is None:
            from modules.history_db import HistoryDB
            self._db = HistoryDB()
            self._db.record_added.connect(self._on_record_added)
            self._db.records_changed.connect(self._on_record_added)
        return self._db

    # ── 界面 ──────────────────────────────────────────────────────

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        main_layout.addWidget(self._build_left_panel())
        main_layout.addWidget(self._build_right_panel(), 1)

        self._refresh_filter()
        self._load_history()

    def _build_left_panel(self):
        """左栏：标题 → 搜索 → 计算器筛选 → 时间范围 → 列表 → 状态。"""
        left_widget = QWidget()
        left_widget.setFixedWidth(340)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("计算历史")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("font-weight: bold; padding: 5px 0;")
        left_layout.addWidget(title)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索输入、输出、备注...")
        self.search_edit.setFixedHeight(32)
        self.search_edit.textChanged.connect(self._on_search_changed)
        # 只保留尺寸相关设置，边框/文字交给主题（否则深色下浅边框会"划"在深底上）
        self.search_edit.setStyleSheet(
            "QLineEdit { border-radius: 6px; padding: 0 10px; font-size: 13px; }")
        left_layout.addWidget(self.search_edit)

        self.calc_filter = QComboBox()
        self.calc_filter.setFixedHeight(32)
        self.calc_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.calc_filter.setStyleSheet(
            "QComboBox { border-radius: 6px; padding: 0 10px; font-size: 13px; }")
        left_layout.addWidget(self.calc_filter)

        self.time_filter = QComboBox()
        self.time_filter.setFixedHeight(32)
        self.time_filter.setStyleSheet(
            "QComboBox { border-radius: 6px; padding: 0 10px; font-size: 13px; }")
        for text, code in TIME_RANGES:
            self.time_filter.addItem(text, code)
        # 先填好默认项、再连信号 —— 否则 addItem 触发的信号会在控件就绪前打到槽里
        self.time_filter.currentIndexChanged.connect(self._on_filter_changed)
        left_layout.addWidget(self.time_filter)

        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        self.history_list.setAlternatingRowColors(True)
        self.history_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.history_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_list.itemClicked.connect(self._on_item_clicked)
        self.history_list.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.history_list, 1)

        self.page_label = QLabel("共 0 条记录")
        self.page_label.setObjectName("mutedLabel")
        self.page_label.setStyleSheet("font-size: 12px; padding: 4px;")

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        bottom_row.addWidget(self.page_label, 1)
        self.load_more_btn = QPushButton("加载更多")
        self.load_more_btn.setObjectName("primaryBtn")
        self.load_more_btn.setFixedHeight(28)
        self.load_more_btn.clicked.connect(self._load_more)
        bottom_row.addWidget(self.load_more_btn)
        left_layout.addLayout(bottom_row)

        return left_widget

    def _build_right_panel(self):
        """右栏：标题+导出按钮 → 详情/统计 → 操作按钮。"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(8)
        right_layout.setContentsMargins(0, 0, 0, 0)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        self.detail_title = QLabel("记录详情")
        self.detail_title.setFont(QFont("Arial", 14, QFont.Bold))
        self.detail_title.setStyleSheet("font-weight: bold; padding: 5px 0;")
        title_row.addWidget(self.detail_title)
        title_row.addStretch()

        self.stats_btn = QPushButton("统计")
        self.stats_btn.setFixedHeight(30)
        self.stats_btn.setToolTip("按当前筛选条件查看使用统计")
        self.stats_btn.clicked.connect(self._toggle_statistics)
        title_row.addWidget(self.stats_btn)

        self.export_csv_btn = QPushButton("导出 CSV")
        self.export_csv_btn.setFixedHeight(30)
        self.export_csv_btn.setToolTip("把当前筛选结果导出为 CSV（Excel 可直接打开）")
        self.export_csv_btn.clicked.connect(self._export_csv)
        title_row.addWidget(self.export_csv_btn)

        self.export_docx_btn = QPushButton("导出 Word")
        self.export_docx_btn.setFixedHeight(30)
        self.export_docx_btn.setToolTip("把当前筛选结果导出为 DOCX 计算书")
        self.export_docx_btn.clicked.connect(self._export_docx)
        title_row.addWidget(self.export_docx_btn)

        self.export_pdf_btn = QPushButton("导出 PDF")
        self.export_pdf_btn.setFixedHeight(30)
        self.export_pdf_btn.setToolTip("把当前筛选结果导出为 PDF（需本机安装 Word 或 LibreOffice）")
        self.export_pdf_btn.clicked.connect(self._export_pdf)
        title_row.addWidget(self.export_pdf_btn)

        right_layout.addLayout(title_row)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setObjectName("historyDetailText")
        right_layout.addWidget(self.detail_text, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.delete_btn = QPushButton("删除此条")
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.setFixedHeight(32)
        self.delete_btn.clicked.connect(self._delete_record)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)

        self.delete_selected_btn = QPushButton("删除选中")
        self.delete_selected_btn.setObjectName("dangerBtn")
        self.delete_selected_btn.setFixedHeight(32)
        self.delete_selected_btn.clicked.connect(self._delete_selected)
        self.delete_selected_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_selected_btn)

        btn_layout.addStretch()

        self.clear_btn = QPushButton("清空筛选结果")
        self.clear_btn.setObjectName("dangerBtn")
        self.clear_btn.setFixedHeight(32)
        self.clear_btn.clicked.connect(self._clear_filtered)
        self.clear_btn.setEnabled(False)
        btn_layout.addWidget(self.clear_btn)

        right_layout.addLayout(btn_layout)
        return right_widget

    # ── 筛选状态 ──────────────────────────────────────────────────

    def _current_range(self):
        """把时间范围编码换成 (date_from, date_to)，均为 'YYYY-MM-DD' 或 None。"""
        code = self._range_code
        if not code or code == "all":
            return None, None
        today = datetime.now().date()
        if code == "today":
            return today.isoformat(), today.isoformat()
        if code == "month":
            return today.replace(day=1).isoformat(), today.isoformat()
        days = 7 if code == "7d" else 30
        return (today - timedelta(days=days - 1)).isoformat(), today.isoformat()

    def _filter_kwargs(self):
        """当前筛选条件 —— 列表、统计、导出共用同一口径。"""
        date_from, date_to = self._current_range()
        return {
            "calculator_id": self._current_calculator or None,
            "keyword": self._current_keyword,
            "date_from": date_from,
            "date_to": date_to,
        }

    def _filter_summary(self):
        parts = []
        parts.append(self.calc_filter.currentText() or "全部计算器")
        parts.append(self.time_filter.currentText() or "全部时间")
        if self._current_keyword:
            parts.append(f"关键词「{self._current_keyword}」")
        return " · ".join(parts)

    def _refresh_filter(self):
        """刷新计算器筛选下拉。"""
        self.calc_filter.blockSignals(True)
        self.calc_filter.clear()
        self.calc_filter.addItem("全部计算器", "")
        calcs = self.db.get_calculator_ids()
        for cid, cname in sorted(calcs.items(), key=lambda x: x[1]):
            self.calc_filter.addItem(cname, cid)
        # 保持原选择（如果没有对应项则回落"全部"）
        idx = self.calc_filter.findData(self._current_calculator)
        self.calc_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.calc_filter.blockSignals(False)

    # ── 列表加载 ──────────────────────────────────────────────────

    def _load_history(self, append=False):
        """加载历史记录（append=True 时追加下一页）。"""
        if not append:
            self._current_page = 0
            # 不用 clear()——PySide6 在某些条件下 clear() 会触发 access violation，
            # 改为逐条 takeItem 安全移除。
            self.history_list.blockSignals(True)
            while self.history_list.count() > 0:
                item = self.history_list.takeItem(0)
                del item
            self.history_list.blockSignals(False)

        records, total = self.db.get_all(
            limit=self.PAGE_SIZE,
            offset=self._current_page * self.PAGE_SIZE,
            **self._filter_kwargs()
        )
        self._total = total

        for rec in records:
            item = QListWidgetItem()
            dt = datetime.fromisoformat(rec["created_at"])
            label = dt.strftime("%m-%d %H:%M")
            inputs_preview = self._format_inputs_preview(rec["inputs"])
            item.setText(f"{rec['calculator_name']}  {label}\n{inputs_preview}")
            item.setData(Qt.UserRole, rec["id"])
            # 记录本体直接挂在 item 上 —— 以前点击时用 get_all(limit=1000) 全表捞一次，
            # 既慢又在"已筛选"时可能捞不到（自己给自己挖坑）。
            item.setData(Qt.UserRole + 1, rec)
            self.history_list.addItem(item)

        self._update_page_label()
        self._on_selection_changed()
        return records

    def _load_more(self):
        self._current_page += 1
        self._load_history(append=True)

    def _update_page_label(self):
        shown = self.history_list.count()
        selected = len(self._selected_ids())
        text = f"共 {self._total} 条记录 (显示 {shown} 条)"
        if selected:
            text += f" · 已选 {selected} 条"
        self.page_label.setText(text)
        self.load_more_btn.setEnabled(shown < self._total)
        self.clear_btn.setEnabled(self._total > 0)
        has_any = self._total > 0
        for btn in (self.export_csv_btn, self.export_docx_btn, self.export_pdf_btn,
                    self.stats_btn):
            btn.setEnabled(has_any)

    # ── 选择与详情 ────────────────────────────────────────────────

    def _selected_ids(self):
        return [it.data(Qt.UserRole) for it in self.history_list.selectedItems()]

    def _on_selection_changed(self):
        n = len(self._selected_ids())
        self.delete_selected_btn.setEnabled(n > 0)
        self.delete_selected_btn.setText(f"删除选中 ({n})" if n else "删除选中")
        self._update_page_label()

    def _on_item_clicked(self, item):
        rec = item.data(Qt.UserRole + 1)
        if rec is None:
            # 兜底：老版本塞进去的 item 只有 id
            rec = self.db.get_record(item.data(Qt.UserRole))
        self._current_record = rec
        self.delete_btn.setEnabled(rec is not None)
        if rec:
            self._right_mode = "detail"
            self.detail_title.setText("记录详情")
            self.stats_btn.setText("统计")
            self.detail_text.setHtml(self._format_detail(rec))

    def _find_record_in_list(self, record_id):
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            if item.data(Qt.UserRole) == record_id:
                return item.data(Qt.UserRole + 1) or self.db.get_record(record_id)
        return None

    def _format_inputs_preview(self, inputs):
        if not inputs:
            return ""
        parts = [f"{k}={v}" for k, v in list(inputs.items())[:3]]
        suffix = " ..." if len(inputs) > 3 else ""
        return " | ".join(parts) + suffix

    def _format_detail(self, rec):
        """生成详情 HTML。

        颜色一律取自主题（`get_content_colors()`）—— Qt 富文本读不到 QSS，
        以前写死的深蓝灰正文色在深色主题下就是"深底压深字"，正文基本看不见。
        """
        c = get_content_colors()
        dt = datetime.fromisoformat(rec["created_at"])
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <div style="font-family: 'Microsoft YaHei', Arial; font-size: 14px;">
            <div style="background: {c['banner_bg']}; color: {c['banner_fg']};
                        padding: 10px 14px; border-radius: 6px; margin-bottom: 12px;
                        font-size: 15px; font-weight: bold;">
                {_esc(rec['calculator_name'])}
            </div>
            <div style="color: {c['muted']}; font-size: 12px; margin-bottom: 12px;">
                {dt_str} &nbsp;|&nbsp; {_esc(rec['calculator_category'] or '未分类')}
            </div>
        """

        if rec.get("inputs"):
            html += f"""
            <div style="margin-bottom: 12px;">
                <div style="font-weight: bold; margin-bottom: 6px;
                            border-left: 3px solid {c['banner_bg']}; padding-left: 8px;">输入参数</div>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
            """
            for k, v in rec["inputs"].items():
                html += f"""
                    <tr style="border-bottom: 1px solid {c['rule']};">
                        <td style="padding: 4px 8px; color: {c['muted']}; white-space: nowrap;">{_esc(str(k))}</td>
                        <td style="padding: 4px 8px; font-weight: bold;">{_esc(str(v))}</td>
                    </tr>
                """
            html += "</table></div>"

        if rec.get("outputs"):
            html += f"""
            <div style="margin-bottom: 12px;">
                <div style="font-weight: bold; color: {c['ok']}; margin-bottom: 6px;
                            border-left: 3px solid {c['ok']}; padding-left: 8px;">计算结果</div>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
            """
            for k, v in rec["outputs"].items():
                v_html = _esc(str(v)).replace("\n", "<br>")
                html += f"""
                    <tr style="border-bottom: 1px solid {c['rule']};">
                        <td style="padding: 4px 8px; color: {c['muted']}; white-space: nowrap;">{_esc(str(k))}</td>
                        <td style="padding: 4px 8px; color: {c['ok']}; font-weight: bold;">{v_html}</td>
                    </tr>
                """
            html += "</table></div>"

        if rec.get("notes"):
            html += f"""
            <div>
                <div style="font-weight: bold; color: {c['accent']}; margin-bottom: 6px;
                            border-left: 3px solid {c['accent']}; padding-left: 8px;">备注</div>
                <div style="border: 1px solid {c['rule']}; border-radius: 6px;
                            padding: 8px; font-size: 13px;">{_esc(str(rec['notes']))}</div>
            </div>
            """

        html += "</div>"
        return html

    # ── 统计 ──────────────────────────────────────────────────────

    def _toggle_statistics(self):
        if self._right_mode == "statistics":
            self._right_mode = "detail"
            self.detail_title.setText("记录详情")
            self.stats_btn.setText("统计")
            if self._current_record:
                self.detail_text.setHtml(self._format_detail(self._current_record))
            else:
                self.detail_text.clear()
        else:
            self._show_statistics()

    def _show_statistics(self):
        self._right_mode = "statistics"
        self.detail_title.setText("使用统计")
        self.stats_btn.setText("返回详情")
        stats = self.db.get_statistics(**self._filter_kwargs())
        self.detail_text.setHtml(self._format_statistics(stats))

    @staticmethod
    def _bar_table(rows, c, base):
        """横向条形：一行一个条目，条长按像素精确控制。

        实测结论（.workbuddy/probe_bar.py / probe_bar2.py，逐像素验证）：
        1. Qt 富文本里"嵌套表格/百分比宽度"不可靠 —— 50% 会被渲染成 121~590px
           之间的任意值，唯有【填充格写死像素宽 + 余量格弹性】按指定值精确渲染；
        2. 列宽是**整表共享**的：多行共用一张表时各行想用不同的像素宽不可能，
           Qt 会把所有行叠画在同一处（A/B/C 三个变体全中招）；
        3. 所以每根条形单独一张单行表，行间用 2px 小字号占位行隔开（margin 被
           Qt 忽略，占位行有效）。
        """
        parts = []
        for i, (label, value) in enumerate(rows):
            pct = (value / base * 100.0) if base else 0.0
            fill = int(round(HistoryViewer.BAR_MAX_PX * pct / 100.0))
            if i:
                parts.append('<div style="font-size:2px;line-height:2px;">&nbsp;</div>')
            parts.append(
                '<table width="100%" cellspacing="0" cellpadding="0" '
                'style="border-collapse:collapse;"><tr>'
                f'<td width="190" style="padding:0 8px 0 0;color:{c["muted"]};'
                f'font-size:12px;">{_esc(str(label))}</td>'
                f'<td width="{fill}" style="background-color:{c["banner_bg"]};'
                f'height:10px;"></td>'
                f'<td style="background-color:{c["rule"]};height:10px;"></td>'
                f'<td width="48" align="right" style="padding:0 0 0 8px;'
                f'font-weight:bold;font-size:12px;">{value}</td>'
                f'<td width="52" align="right" style="color:{c["muted"]};'
                f'font-size:12px;">{pct:.1f}%</td>'
                '</tr></table>'
            )
        return "".join(parts)

    def _format_statistics(self, stats):
        """统计 HTML（颜色全部取自主题，深色主题下同样可读）。"""
        c = get_content_colors()
        total = stats.get("total", 0)

        def _fmt_dt(value):
            if not value:
                return "—"
            try:
                return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
            except ValueError:
                return str(value)

        span = "—"
        if stats.get("first_at") and stats.get("last_at"):
            span = f"{_fmt_dt(stats['first_at'])} ~ {_fmt_dt(stats['last_at'])}"

        html = f"""
        <div style="font-family: 'Microsoft YaHei', Arial; font-size: 13px;">
            <div style="background: {c['banner_bg']}; color: {c['banner_fg']};
                        padding: 10px 14px; border-radius: 6px; margin-bottom: 10px;
                        font-size: 15px; font-weight: bold;">使用统计</div>
            <div style="color: {c['muted']}; font-size: 12px; margin-bottom: 12px;">
                筛选：{_esc(self._filter_summary())} &nbsp;|&nbsp;
                统计于 {datetime.now().strftime('%Y-%m-%d %H:%M')}
            </div>
        """

        cards = [
            ("记录总数", f"{total}"),
            ("计算器", f"{stats.get('calculator_count', 0)}"),
            ("分类", f"{stats.get('category_count', 0)}"),
            ("活跃天数", f"{stats.get('active_days', 0)}"),
        ]
        html += '<table style="width:100%; border-collapse:separate; border-spacing:6px 0; margin-bottom:12px;"><tr>'
        for name, value in cards:
            html += (
                f'<td width="25%" style="border:1px solid {c["rule"]}; border-radius:6px; padding:8px 10px;">'
                f'<div style="font-size:19px; font-weight:bold;">{value}</div>'
                f'<div style="font-size:11px; color:{c["muted"]};">{name}</div></td>'
            )
        html += "</tr></table>"

        html += (
            f'<div style="color:{c["muted"]}; font-size:12px; margin-bottom:14px;">'
            f'时间跨度：{_esc(span)}</div>'
        )

        if total == 0:
            html += (
                f'<div style="color:{c["muted"]}; font-size:13px; padding:16px 0;">'
                "当前筛选条件下没有记录。</div></div>"
            )
            return html

        # 按分类分布
        html += (
            '<div style="font-weight:bold; margin-bottom:6px; margin-top:4px; '
            f'border-left:3px solid {c["banner_bg"]}; padding-left:8px;">按分类分布</div>'
            + self._bar_table(stats.get("by_category", []), c, total)
            # 空段落/纯高度 div 在 Qt 富文本里不占位，用小字号占位行撑出间距
            + '<div style="font-size:10px;line-height:10px;">&nbsp;</div>'
        )

        # 计算器排行
        calc_rows = list(stats.get("by_calculator", []))
        if stats.get("other_count"):
            calc_rows.append(("其他", stats["other_count"]))
        html += (
            '<div style="font-weight:bold; margin-bottom:6px; '
            f'border-left:3px solid {c["banner_bg"]}; padding-left:8px;">计算器使用排行</div>'
            + self._bar_table(calc_rows, c, total)
            + '<div style="font-size:10px;line-height:10px;">&nbsp;</div>'
        )

        # 近 N 天趋势（条长按当日最大值缩放，占比也相对最大值）
        by_day = stats.get("by_day", [])
        if by_day:
            day_max = max(n for _d, n in by_day) or 1
            html += (
                f'<div style="font-weight:bold; margin-bottom:6px; '
                f'border-left:3px solid {c["banner_bg"]}; padding-left:8px;">'
                f'近 {len(by_day)} 个有记录的日期（相对峰值）</div>'
                + self._bar_table(by_day, c, day_max)
            )

        html += "</div>"
        return html

    # ── 导出 ──────────────────────────────────────────────────────

    def _query_for_export(self):
        return self.db.get_all_records(
            limit=self.EXPORT_LIMIT, **self._filter_kwargs())

    @staticmethod
    def _kv_text(mapping):
        """把 {名称: 值} 压成一行文本（多行值折成 ' / '，避免撑破 CSV 单元格）。"""
        if not mapping:
            return ""
        return "; ".join(
            f"{k}={str(v).replace(chr(10), ' / ').replace(chr(13), ' ')}"
            for k, v in mapping.items()
        )

    def _export_csv(self):
        records = self._query_for_export()
        if not records:
            QMessageBox.information(self, "无可导出内容", "当前筛选条件下没有记录。")
            return
        default_name = f"ChemCal计算历史_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出计算历史", default_name, "CSV 文件 (*.csv)")
        if not file_path:
            return
        try:
            written = self._write_csv(file_path, records)
        except OSError as e:
            QMessageBox.critical(self, "导出失败", f"写入文件失败：\n{e}")
            return
        QMessageBox.information(
            self, "导出成功",
            f"已导出 {written} 条记录到：\n{file_path}\n\n可直接用 Excel 打开。")

    def _write_csv(self, file_path, records=None):
        """写 CSV 并返回写入条数。拆分出来是为了能在离屏测试里直接验证内容。"""
        records = self._query_for_export() if records is None else records
        # utf-8-sig：带 BOM，Excel 双击打开才不会把中文显示成乱码
        with open(file_path, "w", newline="", encoding="utf-8-sig") as fp:
            writer = csv.writer(fp)
            writer.writerow(["序号", "时间", "分类", "计算器",
                             "输入参数", "计算结果", "备注"])
            for i, rec in enumerate(records, 1):
                writer.writerow([
                    i,
                    datetime.fromisoformat(rec["created_at"]).strftime("%Y-%m-%d %H:%M:%S"),
                    rec["calculator_category"] or "未分类",
                    rec["calculator_name"],
                    self._kv_text(rec["inputs"]),
                    self._kv_text(rec["outputs"]),
                    rec["notes"] or "",
                ])
        return len(records)

    def _export_docx(self):
        from utils.docx_utils import ReportExporter
        ReportExporter.export_docx(self, "计算历史记录")

    def _export_pdf(self):
        from utils.docx_utils import ReportExporter
        ReportExporter.export_pdf(self, "计算历史记录")

    # ── 导出契约（ReportExporter / 统一报告接口要求）────────────────

    def get_project_info(self):
        """项目信息（统一报告接口契约，必须是 dict —— 不能弹 QDialog）。"""
        return {
            "company_name": "",
            "project_number": "",
            "project_name": "计算历史记录",
            "subproject_name": "",
            "calculation_type": "计算历史导出",
            "calculator_name": "计算历史查看器",
            "version": "1.0",
            "description": "按当前筛选条件导出的计算历史清单",
        }

    def generate_report(self):
        """生成历史记录清单（纯文本）—— 返回 str 或 None。"""
        records = self._query_for_export()
        if not records:
            return None

        lines = [
            "ChemCal 计算历史记录清单",
            "=" * 52,
            f"导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"筛选条件：{self._filter_summary()}",
            f"记录条数：{len(records)}",
            "",
        ]
        for i, rec in enumerate(records, 1):
            dt = datetime.fromisoformat(rec["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
            lines.append("-" * 52)
            lines.append(f"[{i}] {rec['calculator_name']}    {dt}")
            lines.append(f"    分类：{rec['calculator_category'] or '未分类'}")
            if rec.get("inputs"):
                lines.append("    输入参数：")
                for k, v in rec["inputs"].items():
                    lines.append(f"        {k} = {str(v).replace(chr(10), ' / ')}")
            if rec.get("outputs"):
                lines.append("    计算结果：")
                for k, v in rec["outputs"].items():
                    lines.append(f"        {k} = {str(v).replace(chr(10), ' / ')}")
            if rec.get("notes"):
                lines.append(f"    备注：{rec['notes']}")
        lines.append("")
        return "\n".join(lines)

    # ── 主题 ──────────────────────────────────────────────────────

    def on_theme_changed(self):
        """主题切换后重渲染当前右栏内容（HTML 颜色取自主题，换了必须重画）。"""
        if self._right_mode == "statistics":
            self._show_statistics()
        elif self._current_record:
            self.detail_text.setHtml(self._format_detail(self._current_record))

    # ── 删除 ──────────────────────────────────────────────────────

    def _confirm(self, title, message):
        """危险操作二次确认。confirm_enabled=False（测试）时直接放行。"""
        if not self.confirm_enabled:
            return True
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    def _after_delete(self):
        self.detail_text.clear()
        self._current_record = None
        self.delete_btn.setEnabled(False)
        self._current_page = 0
        self._load_history()
        self._refresh_filter()

    def _delete_record(self):
        if self._current_record is None:
            return
        record_id = self._current_record["id"]
        name = self._current_record["calculator_name"]
        if not self._confirm(
                "确认删除",
                f"确定要删除这条「{name}」记录吗？\n此操作不可撤销。"):
            return
        self.db.delete(record_id)
        self._after_delete()

    def _delete_selected(self):
        """批量删除列表中选中的记录。"""
        ids = self._selected_ids()
        if not ids:
            return
        if not self._confirm(
                "确认批量删除",
                f"确定要删除选中的 {len(ids)} 条记录吗？\n此操作不可撤销。"):
            return
        self.db.delete_many(ids)
        self._after_delete()

    def _clear_filtered(self):
        """清空"当前筛选结果"——筛选为全部时即清空整库，文案必须说清楚。"""
        n = self._total
        if n <= 0:
            return
        scope = self._filter_summary()
        if not self._confirm(
                "确认清空",
                f"将删除当前筛选结果的全部 {n} 条记录。\n"
                f"筛选条件：{scope}\n\n此操作不可撤销！"):
            return
        self.db.delete_filtered(**self._filter_kwargs())
        self._after_delete()

    # ── 外部刷新 ──────────────────────────────────────────────────

    def _on_record_added(self):
        """收到数据库变更信号时刷新（延迟执行，避免在信号链中操作 Qt 控件）。"""
        QTimer.singleShot(0, self._load_history)

    def _on_search_changed(self, text):
        self._current_keyword = text
        self._current_page = 0
        self._current_record = None
        self.delete_btn.setEnabled(False)
        self._load_history()
        self.detail_text.clear()

    def _on_filter_changed(self, index):
        self._current_calculator = self.calc_filter.currentData() or ""
        self._range_code = self.time_filter.currentData() or "all"
        self._current_page = 0
        self._current_record = None
        self.delete_btn.setEnabled(False)
        self._load_history()
        self.detail_text.clear()

    def refresh(self):
        """外部刷新调用"""
        self._current_page = 0
        self._refresh_filter()
        self._load_history()
