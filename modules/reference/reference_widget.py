# ChemCal/modules/reference/reference_widget.py
"""参考资料库 — 左侧树形分类导航 + 右侧内容展示 + 全局搜索"""

import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QTextEdit, QSplitter, QFrame, QAbstractItemView, QHeaderView,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor, QBrush


# ── 加载参考数据 ──────────────────────────────────────────────
def _load_reference_data():
    """从 JSON 文件加载参考数据库"""
    json_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "reference_db.json"
    )
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


class ReferenceWidget(QWidget):
    """参考资料库模块"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.ref_data = _load_reference_data()
        self._all_sections = []  # 扁平化的搜索索引
        self._build_search_index()
        self._setup_ui()

    # ── 搜索索引 ───────────────────────────────────────────

    def _build_search_index(self):
        """将所有条目扁平化，方便全文搜索"""
        self._all_sections = []
        for cat in self.ref_data:
            cat_name = cat.get("category", "")
            for sec in cat.get("sections", []):
                # 收集可搜索文本
                searchable = [cat_name, sec.get("title", ""), sec.get("description", ""),
                              sec.get("source", "")]
                if sec.get("type") == "table":
                    for row in sec.get("rows", []):
                        searchable.extend(str(c) for c in row)
                elif sec.get("type") == "text":
                    searchable.append(sec.get("content", ""))
                self._all_sections.append({
                    "category": cat_name,
                    "section": sec,
                    "search_text": " ".join(searchable).lower(),
                })

    # ── UI 构建 ────────────────────────────────────────────

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(0)

        # 分割器：左侧树 | 右侧内容
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # ── 左侧面板 ──
        left_frame = QFrame()
        left_frame.setObjectName("refLeftPanel")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        # 标题
        title = QLabel("资料库")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索关键词...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setMinimumHeight(36)
        left_layout.addWidget(self.search_input)

        # 搜索结果计数
        self.search_count_label = QLabel("")
        self.search_count_label.setStyleSheet("color: #888; font-size: 11px; padding-left: 4px;")
        left_layout.addWidget(self.search_count_label)

        # 树形导航
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setObjectName("refNavTree")
        self.tree.setIndentation(20)
        self.tree.setAnimated(True)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.itemClicked.connect(self._on_tree_click)
        self.tree.setMinimumWidth(200)
        left_layout.addWidget(self.tree)

        splitter.addWidget(left_frame)

        # ── 右侧面板 ──
        right_frame = QFrame()
        right_frame.setObjectName("refRightPanel")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_layout.setSpacing(0)

        # 内容标题
        self.content_title = QLabel("选择左侧条目查看详情")
        self.content_title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self.content_title.setWordWrap(True)
        right_layout.addWidget(self.content_title)

        # 描述
        self.content_desc = QLabel("")
        self.content_desc.setWordWrap(True)
        self.content_desc.setStyleSheet("color: #555; font-size: 12px; margin-top: 4px;")
        right_layout.addWidget(self.content_desc)

        # 来源
        self.content_source = QLabel("")
        self.content_source.setWordWrap(True)
        self.content_source.setStyleSheet("color: #888; font-size: 11px; margin-top: 2px; margin-bottom: 8px;")
        right_layout.addWidget(self.content_source)

        # 内容区域（表格或文本）
        self.content_stack = QStackedWidget()
        right_layout.addWidget(self.content_stack)

        # 表格页
        self.table_widget = QTableWidget()
        self.table_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setStyleSheet(
            "QTableWidget { font-size: 12px; }"
            "QTableWidget::item { padding: 6px 8px; }"
            "QHeaderView::section { font-weight: bold; padding: 6px 8px; "
            "  background: #f0f0f0; border: 1px solid #ddd; }"
        )
        self.content_stack.addWidget(self.table_widget)

        # 文本页
        self.text_widget = QTextEdit()
        self.text_widget.setReadOnly(True)
        self.text_widget.setStyleSheet(
            "QTextEdit { font-size: 12px; font-family: 'Consolas', 'Microsoft YaHei'; "
            "  padding: 12px; line-height: 1.6; }"
        )
        self.content_stack.addWidget(self.text_widget)

        # 空白页
        empty_label = QLabel("从左侧选择条目，或使用搜索框查找数据")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("color: #aaa; font-size: 14px;")
        self.content_stack.addWidget(empty_label)

        self.content_stack.setCurrentIndex(2)
        splitter.addWidget(right_frame)

        # 分割比例
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 7)

        main_layout.addWidget(splitter)

        # 填充树
        self._populate_tree()

    # ── 树形导航 ────────────────────────────────────────────

    def _populate_tree(self):
        """根据数据填充树形导航"""
        self.tree.clear()
        self._tree_items = {}  # item -> section data

        icon_map = {
            "设备布置": "🏭", "管道设计": "🔧", "安全规范": "🛡️",
            "计算依据": "📐", "物性数据": "📊", "材料规范": "🔩",
        }

        for cat in self.ref_data:
            cat_name = cat.get("category", "")
            icon = icon_map.get(cat_name, "📁")
            cat_item = QTreeWidgetItem(self.tree, [f"{icon} {cat_name}"])
            cat_item.setFont(0, QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
            cat_item.setExpanded(True)

            for sec in cat.get("sections", []):
                sec_title = sec.get("title", "")
                sec_item = QTreeWidgetItem(cat_item, [f"  {sec_title}"])
                sec_item.setFont(0, QFont("Microsoft YaHei", 10))
                self._tree_items[id(sec_item)] = sec

        self.tree.expandAll()

    # ── 搜索 ────────────────────────────────────────────────

    def _on_search(self, keyword):
        """搜索框文本变化 → 过滤树形导航"""
        keyword = keyword.strip().lower()
        self.tree.clear()
        self._tree_items = {}

        icon_map = {
            "设备布置": "🏭", "管道设计": "🔧", "安全规范": "🛡️",
            "计算依据": "📐", "物性数据": "📊", "材料规范": "🔩",
        }

        match_count = 0

        if not keyword:
            # 空搜索 → 恢复完整树
            self._populate_tree()
            self.search_count_label.setText("")
            return

        # 按分类分组匹配结果
        matched_cats = {}
        for entry in self._all_sections:
            if keyword in entry["search_text"]:
                cat = entry["category"]
                if cat not in matched_cats:
                    matched_cats[cat] = []
                matched_cats[cat].append(entry["section"])
                match_count += 1

        # 填充搜索结果树
        for cat_name, sections in matched_cats.items():
            icon = icon_map.get(cat_name, "📁")
            cat_item = QTreeWidgetItem(self.tree, [f"{icon} {cat_name}"])
            cat_item.setFont(0, QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
            cat_item.setExpanded(True)

            for sec in sections:
                sec_title = sec.get("title", "")
                sec_item = QTreeWidgetItem(cat_item, [f"  {sec_title}"])
                sec_item.setFont(0, QFont("Microsoft YaHei", 10))
                self._tree_items[id(sec_item)] = sec

        self.tree.expandAll()
        self.search_count_label.setText(f"匹配 {match_count} 条")

        # 自动选中第一条
        if self.tree.topLevelItemCount() > 0:
            top = self.tree.topLevelItem(0)
            if top.childCount() > 0:
                first = top.child(0)
                self.tree.setCurrentItem(first)
                self._show_section(first)

    # ── 点击导航 ────────────────────────────────────────────

    def _on_tree_click(self, item, column):
        """点击树节点 → 显示对应内容"""
        self._show_section(item)

    def _show_section(self, item):
        """根据树节点显示对应的参考内容"""
        sec = self._tree_items.get(id(item))
        if sec is None:
            # 点击了分类节点，不切换内容
            return

        title = sec.get("title", "")
        desc = sec.get("description", "")
        source = sec.get("source", "")
        sec_type = sec.get("type", "")

        self.content_title.setText(title)
        self.content_desc.setText(desc)
        self.content_source.setText(f"来源: {source}" if source else "")

        if sec_type == "table":
            self._show_table(sec)
        elif sec_type == "text":
            self._show_text(sec)
        else:
            self.content_stack.setCurrentIndex(2)

    def _show_table(self, sec):
        """展示表格型数据"""
        headers = sec.get("headers", [])
        rows = sec.get("rows", [])

        self.table_widget.setRowCount(len(rows))
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)

        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                item = QTableWidgetItem(str(cell))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # 偶数行浅底色
                if r % 2 == 0:
                    item.setBackground(QBrush(QColor("#f8f9fa")))
                self.table_widget.setItem(r, c, item)

        # 自适应列宽
        self.table_widget.resizeColumnsToContents()
        header = self.table_widget.horizontalHeader()
        for i in range(self.table_widget.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        self.content_stack.setCurrentIndex(0)

    def _show_text(self, sec):
        """展示文本型数据"""
        content = sec.get("content", "")
        # 简单的文本 → HTML 格式化
        html = self._format_text_to_html(content)
        self.text_widget.setHtml(html)
        self.content_stack.setCurrentIndex(1)

    def _format_text_to_html(self, text):
        """将纯文本格式化为美观的 HTML"""
        lines = text.split("\n")
        html_parts = []
        in_formula = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                html_parts.append("<br>")
                continue

            # 一级标题：一、二、三…
            if len(stripped) > 2 and stripped[0] in "一二三四五六七八九十" and stripped[1] in "、. ":
                html_parts.append(f"<h3 style='color:#2c3e50; margin-top:16px; margin-bottom:6px;'>{stripped}</h3>")
                continue

            # 公式行：含 = 或希腊字母
            if "=" in stripped and ("×" in stripped or "÷" in stripped or "/" in stripped or "√" in stripped or "λ" in stripped or "Δ" in stripped or "≥" in stripped or "≤" in stripped):
                html_parts.append(
                    f"<div style='background:#f4f6f7; padding:8px 12px; margin:4px 0; "
                    f"border-radius:4px; font-family:Consolas,\"Microsoft YaHei\"; font-size:13px;'>{stripped}</div>"
                )
                continue

            # 列表项：以 — 或 · 开头
            if stripped.startswith("—") or stripped.startswith("·"):
                html_parts.append(f"<div style='margin-left:20px; padding:2px 0;'>{stripped}</div>")
                continue

            # 注释行：以 // 或 # 开头
            if stripped.startswith("//") or stripped.startswith("#"):
                html_parts.append(f"<div style='color:#888; font-style:italic;'>{stripped}</div>")
                continue

            # 普通行
            # 对变量定义做简单高亮：如 "Q — 传热量"
            if "—" in stripped and len(stripped) < 80:
                parts = stripped.split("—", 1)
                html_parts.append(
                    f"<div style='margin-left:20px; padding:2px 0;'>"
                    f"<b style='color:#2c3e50;'>{parts[0].strip()}</b>"
                    f" — {parts[1].strip()}</div>"
                )
                continue

            html_parts.append(f"<div style='padding:2px 0;'>{stripped}</div>")

        return "".join(html_parts)

    # ── 激活回调 ────────────────────────────────────────────

    def on_activate(self):
        """标签页切换时回调"""
        pass

    def refresh(self):
        """刷新数据"""
        self.ref_data = _load_reference_data()
        self._build_search_index()
        self._populate_tree()
