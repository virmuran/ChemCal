# ChemCal/modules/reference/reference_widget.py
"""参考资料库 — 分组树导航 + 标签筛选 + 行级搜索 / 数值反查 + 送入计算器

本次（2026-09-16）改造解决四件事：
  1. **分类维度混乱**：14 类混着「按专业/按资料类型/按物料」三套维度，
     19 节全挤在「原辅料标准」而「水质标准」只有 1 节。现在数据侧多了
     `group`（5 个顶层分组，统一按用途）与 `tags`（条目标签，可筛选），
     「原辅料标准」按用途拆成「食品添加剂标准 / 工业原料标准」。
  2. **搜索只到节**：搜「0.8」只告诉你哪一节可能有，还得自己在表里肉眼找。
     现在结果树展开到**具体行**并显示命中片段，选中后表格里命中单元格黄底高亮；
     输入纯数值（0.6 / 143.7 / 0.6MPa）自动切「数值反查」，±1% 容差跨全库找。
  3. **与计算器脱钩**：查到「推荐流速 2 m/s」想算管径得手抄到另一个页签。
     现在表格选中值可「送入计算器」；反过来计算器的 📚 按钮能跳到对应节。
  4. **两份真相**：粗糙度只活在计算器下拉里、管径/物性两套数据互不知道。
     现在粗糙度由 reference_data.PIPE_ROUGHNESS 现场生成节，
     管径选型表补 Sch 40 对照列、物性表补 20°C 对照列（同样现场取），
     不在 JSON 里再抄一份。
"""

import os
import re
import sys
import json

from PySide6.QtWidgets import (
    QApplication,
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QTextEdit, QSplitter, QFrame, QAbstractItemView, QHeaderView,
    QPushButton, QComboBox, QMenu,
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QColor, QBrush, QTextCharFormat, QTextCursor

from theme_manager import get_content_colors, normalize_legacy_content_colors

try:
    from modules.reference.ref_exchange import EXCHANGE, TARGETS
except ImportError:                                  # 兼容以文件路径直接导入
    from ref_exchange import EXCHANGE, TARGETS


# ── 分类图标（新增分类记得补，否则会掉到默认文件夹图标）─────────────
CATEGORY_ICONS = {
    "设备布置": "🏭", "管道设计": "🔧", "安全规范": "🛡️",
    "计算依据": "📐", "物性数据": "📊", "材料规范": "🔩",
    "原辅料标准": "🧪", "食品添加剂标准": "🧴", "工业原料标准": "⚗️",
    "蒸汽参数": "♨️", "压缩空气": "💨",
    "消防安全": "🚒", "水质标准": "💧", "热工设备": "🔥",
    "防爆区域": "⚡", "投资估算": "💰",
}
DEFAULT_CATEGORY_ICON = "📁"

#: 顶层分组（统一维度 = 按用途）。顺序即展示顺序。
GROUP_ICONS = {
    "设计计算数据": "📐", "材料与设备": "🔩", "布置与安全": "🛡️",
    "原料与水质": "🧪", "投资估算": "💰",
}
GROUP_ORDER = list(GROUP_ICONS)
FALLBACK_GROUP = "其他"

#: 标签筛选下拉的固定项
TAG_ALL = "全部标签"

#: 数值反查：相对容差 1%（0.6 → ±0.006）
_NUM_TOL_RATIO = 0.01
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_PURE_NUM_RE = re.compile(r"^[-+]?\d+(?:\.\d+)?$")
_NUM_UNIT_RE = re.compile(r"^([-+]?\d+(?:\.\d+)?)\s*[a-zA-Z%°℃³²/().·]*$")

#: 数据文件里「资料库 ↔ 计算器底层表」同名但叫法不同的物质
_FLUID_ALIAS = {"醋酸": "乙酸", "盐酸(31%)": "盐酸(30%)"}


def _num_tol(v):
    return abs(v) * _NUM_TOL_RATIO


def _as_number(text):
    """能把整串解析成数值就返回 float，否则 None（用于判断走数值反查还是关键词搜索）。"""
    s = (text or "").strip()
    if not s:
        return None
    if _PURE_NUM_RE.match(s):
        return float(s)
    m = _NUM_UNIT_RE.match(s)          # 0.6MPa / 143.7℃ 这类带单位写法
    return float(m.group(1)) if m else None


def _cell_has_number(text, num):
    for m in _NUM_RE.findall(str(text)):
        try:
            v = float(m)
        except ValueError:
            continue
        if abs(v - num) <= _num_tol(num):
            return True
    return False


def _clip(text, limit=64):
    s = " ".join(str(text).split())
    return s if len(s) <= limit else s[:limit] + "…"


def _iter_text_hits(text, keyword, num):
    """在纯文本里迭代命中区间，产出 (start, end)。"""
    if num is None:
        low, key = text.lower(), keyword.lower()
        start = 0
        while True:
            i = low.find(key, start)
            if i < 0:
                return
            yield i, i + len(key)
            start = i + max(1, len(key))
    else:
        for m in _NUM_RE.finditer(text):
            try:
                v = float(m.group())
            except ValueError:
                continue
            if abs(v - num) <= _num_tol(num):
                yield m.start(), m.end()


# ══════════════════════════════════════════════════════════════
# 数据加载 + 派生（「单一来源」的实现处）
# ══════════════════════════════════════════════════════════════

def _read_reference_json():
    """读取 data/reference_db.json（兼容 PyInstaller 打包路径）"""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    json_path = os.path.join(base, "data", "reference_db.json")
    if not os.path.exists(json_path):
        json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "reference_db.json"
        )
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _find_section(db, title):
    for cat in db:
        for sec in cat.get("sections", []):
            if sec.get("title") == title:
                return cat, sec
    return None, None


def _inject_derived(db):
    """把「只活在计算器底层表里」的数据补成资料库条目/对照列。

    为什么在代码里生成而不是写进 JSON：一旦抄进 JSON 就是第二份真相，
    改了计算器忘了改 JSON 就会重演本次「液氨 682 被当成 20°C」那类事故。
    这里全部现取 reference_data.py，只做展示。
    """
    try:
        from reference_data import PIPE_ROUGHNESS, PIPE_SCH40, FLUID_PROPERTIES
    except Exception:
        return db

    # ① 管道粗糙度 —— 原本只存在于计算器下拉框，资料库里查不到
    cat, sec = _find_section(db, "管径快速选型")
    if cat is not None and _find_section(db, "管道粗糙度")[1] is None:
        cat.setdefault("sections", []).append({
            "title": "管道粗糙度",
            "description": "常用管材的绝对粗糙度 ε（管径/压降计算器下拉框的数据源）",
            "source": "HG/T 20570-95《工艺系统工程设计规定》；数据源 reference_data.PIPE_ROUGHNESS",
            "type": "table",
            "tags": ["管道", "粗糙度", "查表"],
            "note": "本表由计算器底层 reference_data.PIPE_ROUGHNESS 现场生成 —— "
                    "改那一处即可同时生效，此处不另存副本。",
            "headers": ["管材", "绝对粗糙度 ε (mm)"],
            "rows": [[name, ("%g" % val)] for name, val in PIPE_ROUGHNESS],
        })

    # ② 管径快速选型 补 Sch 40 对照列（两套体系并存，必须让人看得见）
    _, sec = _find_section(db, "管径快速选型")
    if sec is not None and "Sch 40 内径(mm)" not in (sec.get("headers") or []):
        sch = {dn: id_ for dn, id_, _od, _wt in PIPE_SCH40}
        sec.setdefault("headers", []).append("Sch 40 内径(mm)")
        for row in sec.get("rows", []):
            v = sch.get(row[0])
            row.append(("—" if v is None else "%g" % v))
        sec["note"] = ("本表内径为 GB/T 8163《输送流体用无缝钢管》Φ 系列（中国体系）；"
                       "对照列为美标 Sch 40。**两套体系不可混用**：同一 DN 的内径可差 0.6~20mm"
                       "（DN25：26 vs 26.6；DN100：100 vs 102.3）。"
                       "对照列现取 reference_data.PIPE_SCH40。")

    # ③ 常用液体物性 补 20°C 对照列（解释「同一物质两个数」其实是温度基准不同）
    _, sec = _find_section(db, "常用液体物性（25°C）")
    add_headers = ["密度@20°C(kg/m³)", "粘度@20°C(mPa·s)"]
    if sec is not None and not set(add_headers) & set(sec.get("headers") or []):
        sec.setdefault("headers", []).extend(add_headers)
        for row in sec.get("rows", []):
            key = _FLUID_ALIAS.get(str(row[0]), str(row[0]))
            pair = FLUID_PROPERTIES.get(key)
            if pair:
                row.extend(["%g" % pair[0], "%g" % pair[1]])
            else:
                row.extend(["—", "—"])
        sec["note"] = ("前 4 列为 25°C 值（《化工工艺设计手册》/Perry's）；"
                       "后 2 列为计算器底层 reference_data.FLUID_PROPERTIES 的 20°C 值"
                       "（各计算器实际使用）。同一物质两处数值不同是**温度基准差异**，"
                       "不是矛盾 —— 例如水 997/0.89（25°C）与 998.2/1.002（20°C）。")

    return db


def _load_reference_data():
    return _inject_derived(_read_reference_json())


# ══════════════════════════════════════════════════════════════

class ReferenceWidget(QWidget):
    """参考资料库模块"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.ref_data = _load_reference_data()
        self._all_sections = []      # 扁平化索引（标签集合 / 兼容旧接口）
        self._keyword = ""
        self._hits = {}              # id(section) -> [{"row","line","cols","snippet"}]
        self._tree_items = {}        # id(item) -> section
        self._row_items = {}         # id(item) -> (section, row, is_text)
        self._current_section = None
        #: QMenu.exec() 在离屏环境会永久阻塞 —— 测试里置 False
        self.menu_enabled = True
        self._build_search_index()
        self._setup_ui()

    # ── 索引 ───────────────────────────────────────────────

    def _build_search_index(self):
        """扁平化所有条目（供标签集合与兼容旧接口用）"""
        self._all_sections = []
        for cat in self.ref_data:
            cat_name = cat.get("category", "")
            for sec in cat.get("sections", []):
                searchable = [cat_name, cat.get("group", ""), sec.get("title", ""),
                              sec.get("description", ""), sec.get("source", ""),
                              " ".join(sec.get("tags") or [])]
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

    def _all_tags(self):
        tags = set()
        for cat in self.ref_data:
            for sec in cat.get("sections", []):
                tags.update(sec.get("tags") or [])
        return sorted(tags)

    # ── UI ────────────────────────────────────────────────

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # ── 左侧面板 ──
        left_frame = QFrame()
        left_frame.setObjectName("refLeftPanel")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        title = QLabel("资料库")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索关键词，或直接输数值反查（0.6 / 143.7 / 0.6MPa）")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setMinimumHeight(36)
        left_layout.addWidget(self.search_input)

        # 命中/模式提示（颜色交给主题的 mutedLabel，勿写死颜色）
        self.search_count_label = QLabel("")
        self.search_count_label.setObjectName("mutedLabel")
        self.search_count_label.setStyleSheet("font-size: 11px; padding-left: 4px;")
        left_layout.addWidget(self.search_count_label)

        # 标签筛选
        tag_row = QHBoxLayout()
        tag_row.setSpacing(6)
        tag_label = QLabel("标签")
        tag_label.setObjectName("mutedLabel")
        tag_label.setStyleSheet("font-size: 11px;")
        self.tag_combo = QComboBox()
        self.tag_combo.setObjectName("refTagCombo")
        self.tag_combo.addItem(TAG_ALL)
        self.tag_combo.addItems(self._all_tags())
        self.tag_combo.currentIndexChanged.connect(lambda _i: self._rebuild_tree())
        tag_row.addWidget(tag_label)
        tag_row.addWidget(self.tag_combo, 1)
        left_layout.addLayout(tag_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setObjectName("refNavTree")
        self.tree.setIndentation(16)
        self.tree.setAnimated(True)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.itemClicked.connect(self._on_tree_click)
        self.tree.setMinimumWidth(210)
        left_layout.addWidget(self.tree)

        # 展开 / 折叠
        tree_tools = QHBoxLayout()
        tree_tools.setSpacing(6)
        expand_btn = QPushButton("全部展开")
        expand_btn.setObjectName("iconBtn")
        expand_btn.setToolTip("展开全部分组")
        expand_btn.clicked.connect(self.tree.expandAll)
        collapse_btn = QPushButton("全部折叠")
        collapse_btn.setObjectName("iconBtn")
        collapse_btn.setToolTip("只留分组标题")
        collapse_btn.clicked.connect(self.tree.collapseAll)
        tree_tools.addWidget(expand_btn)
        tree_tools.addWidget(collapse_btn)
        left_layout.addLayout(tree_tools)

        splitter.addWidget(left_frame)

        # ── 右侧面板 ──
        right_frame = QFrame()
        right_frame.setObjectName("refRightPanel")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_layout.setSpacing(0)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.content_title = QLabel("选择左侧条目查看详情")
        self.content_title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self.content_title.setWordWrap(True)
        title_row.addWidget(self.content_title, 1)

        # 双语提示标志（颜色交给主题的 accentLabel）
        self.bilingual_label = QLabel("")
        self.bilingual_label.setObjectName("accentLabel")
        self.bilingual_label.setStyleSheet("font-size: 11px; padding: 0 6px;")
        title_row.addWidget(self.bilingual_label)

        self.send_btn = QPushButton("送入计算器")
        self.send_btn.setObjectName("primaryBtn")
        self.send_btn.setFixedHeight(30)
        self.send_btn.setToolTip("先在表格里选中一个数值（或整行），再点这里送到计算器输入框")
        self.send_btn.clicked.connect(self._on_send_clicked)
        title_row.addWidget(self.send_btn)

        copy_btn = QPushButton("复制")
        copy_btn.setObjectName("primaryBtn")
        copy_btn.setToolTip("复制 → Tab分隔直接粘贴Excel\n文本页：自动复制关联参数表\n表格页：选中行→复制选中 | 无选中→复制全部\n小技巧：直接鼠标选中文字后 Ctrl+C 也可复制")
        copy_btn.setFixedHeight(30)
        copy_btn.clicked.connect(self._copy_content)
        title_row.addWidget(copy_btn)

        right_layout.addLayout(title_row)

        self.content_desc = QLabel("")
        self.content_desc.setWordWrap(True)
        self.content_desc.setObjectName("mutedLabel")
        self.content_desc.setStyleSheet("font-size: 12px; margin-top: 4px;")
        right_layout.addWidget(self.content_desc)

        self.content_source = QLabel("")
        self.content_source.setWordWrap(True)
        self.content_source.setObjectName("mutedLabel")
        self.content_source.setStyleSheet("font-size: 11px; margin-top: 2px;")
        right_layout.addWidget(self.content_source)

        self.content_note = QLabel("")
        self.content_note.setWordWrap(True)
        self.content_note.setObjectName("accentLabel")
        self.content_note.setStyleSheet("font-size: 11px; margin-top: 2px; margin-bottom: 8px;")
        self.content_note.setVisible(False)
        right_layout.addWidget(self.content_note)

        self.hit_label = QLabel("")
        self.hit_label.setObjectName("mutedLabel")
        self.hit_label.setStyleSheet("font-size: 11px; margin-top: 4px;")
        right_layout.addWidget(self.hit_label)

        self.content_stack = QStackedWidget()
        right_layout.addWidget(self.content_stack)

        self.table_widget = QTableWidget()
        self.table_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.verticalHeader().setVisible(False)
        # 表头背景/边框交给主题的 QHeaderView::section 规则，这里只留字号与内边距
        self.table_widget.setStyleSheet(
            "QTableWidget { font-size: 12px; }"
            "QTableWidget::item { padding: 6px 8px; }"
            "QHeaderView::section { font-weight: bold; padding: 6px 8px; }"
        )
        self.content_stack.addWidget(self.table_widget)

        self.text_widget = QTextEdit()
        self.text_widget.setReadOnly(True)
        self.text_widget.setStyleSheet(
            "QTextEdit { font-size: 12px; font-family: 'Consolas', 'Microsoft YaHei'; "
            "  padding: 12px; line-height: 1.6; }"
        )
        self.content_stack.addWidget(self.text_widget)

        empty_label = QLabel("从左侧选择条目，或使用搜索框查找数据\n"
                             "（直接输入数值可跨全库反查，如 0.6 / 143.7 / 682）")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setObjectName("mutedLabel")
        empty_label.setStyleSheet("font-size: 14px;")
        self.content_stack.addWidget(empty_label)

        self.content_stack.setCurrentIndex(2)
        splitter.addWidget(right_frame)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 7)
        main_layout.addWidget(splitter)

        self._rebuild_tree()

    # ── 树构建（唯一入口：分组 → 分类 → 节 → 命中行）───────

    def _rebuild_tree(self):
        self.tree.clear()
        self._tree_items = {}
        self._row_items = {}
        self._hits = {}

        kw = self._keyword
        num = _as_number(kw) if kw else None
        searching = bool(kw)
        tag = self.tag_combo.currentText() if hasattr(self, "tag_combo") else TAG_ALL

        groups = list(GROUP_ORDER)
        if any((c.get("group") or FALLBACK_GROUP) not in GROUP_ORDER for c in self.ref_data):
            groups.append(FALLBACK_GROUP)

        for group in groups:
            gitem = None
            for cat in self.ref_data:
                if (cat.get("group") or FALLBACK_GROUP) != group:
                    continue
                picked = []
                for sec in cat.get("sections", []):
                    if tag != TAG_ALL and tag not in (sec.get("tags") or []):
                        continue
                    if searching:
                        matched, hits = self._match_section(sec, kw, num)
                        if not matched:
                            continue
                    else:
                        hits = []
                    picked.append((sec, hits))
                if not picked:
                    continue

                if gitem is None:
                    gitem = QTreeWidgetItem(self.tree, [f"{GROUP_ICONS.get(group, '📁')} {group}"])
                    gitem.setFont(0, QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
                    gitem.setExpanded(True)

                cname = cat.get("category", "")
                clabel = f"{CATEGORY_ICONS.get(cname, DEFAULT_CATEGORY_ICON)} {cname}"
                if searching:
                    clabel += f"  ({len(picked)})"
                citem = QTreeWidgetItem(gitem, [clabel])
                citem.setFont(0, QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
                citem.setExpanded(True)

                for sec, hits in picked:
                    sitem = QTreeWidgetItem(citem, [sec.get("title", "")])
                    sitem.setFont(0, QFont("Microsoft YaHei", 10))
                    self._tree_items[id(sitem)] = sec
                    if hits:
                        self._hits[id(sec)] = hits
                        sitem.setExpanded(True)
                        for h in hits[:12]:
                            is_text = h["row"] < 0
                            no = (h["line"] + 1) if is_text else (h["row"] + 1)
                            ritem = QTreeWidgetItem(sitem, [f"第{no}行 · {h['snippet']}"])
                            ritem.setFont(0, QFont("Microsoft YaHei", 9))
                            self._row_items[id(ritem)] = (sec, h["row"], is_text)
        self.tree.expandAll()

    # ── 匹配 ──────────────────────────────────────────────

    def _match_section(self, sec, kw, num):
        """返回 (是否命中, 命中列表)。

        命中项: {"row": 表格行号(文本条目为 -1), "line": 文本行号,
                 "cols": [命中列号], "snippet": 片段}
        关键词只命中标题/描述/来源时也算命中（列表里能看到这一节），只是没有行级命中。
        """
        meta = " ".join([sec.get("title", ""), sec.get("description", ""),
                         sec.get("source", ""), " ".join(sec.get("tags") or [])])
        sec_level = kw.lower() in meta.lower()

        if sec.get("type") == "text":
            hits = []
            for i, line in enumerate((sec.get("content", "") or "").split("\n")):
                ok = (kw.lower() in line.lower()) if num is None else _cell_has_number(line, num)
                if ok:
                    hits.append({"row": -1, "line": i, "cols": [], "snippet": _clip(line)})
            return (bool(hits) or sec_level), hits[:30]

        headers = [str(h) for h in (sec.get("headers") or [])]
        head_hit = any(kw.lower() in h.lower() for h in headers)
        hits = []
        for r, row in enumerate(sec.get("rows") or []):
            cols = []
            for c, cell in enumerate(row):
                text = str(cell)
                ok = (kw.lower() in text.lower()) if num is None else _cell_has_number(text, num)
                if ok:
                    cols.append(c)
            if cols:
                snippet = " | ".join(str(row[c]) for c in cols[:3])
                hits.append({"row": r, "line": -1, "cols": cols, "snippet": _clip(snippet)})
        return (bool(hits) or sec_level or head_hit), hits[:60]

    # ── 搜索 ──────────────────────────────────────────────

    def _on_search(self, keyword):
        """搜索框文本变化 → 重建树（关键词 / 数值反查两模式）"""
        self._keyword = (keyword or "").strip()
        self._rebuild_tree()

        if not self._keyword:
            self.search_count_label.setText("")
            self.hit_label.setText("")
            self._current_section = None
            self.content_stack.setCurrentIndex(2)
            self.content_title.setText("选择左侧条目查看详情")
            self.content_desc.setText("")
            self.content_source.setText("")
            self.content_note.setVisible(False)
            return

        n_sec = len(self._hits)
        n_row = sum(len(v) for v in self._hits.values())
        mode = "数值反查" if _as_number(self._keyword) is not None else "关键词"
        self.search_count_label.setText(f"匹配 {n_sec} 节 / {n_row} 处 · {mode}")

        first = self._first_leaf()
        if first is not None:
            self.tree.setCurrentItem(first[0])
            self._render_section(first[1])

    def _first_leaf(self):
        """返回第一个「节」节点 (item, section)。"""
        for gi in range(self.tree.topLevelItemCount()):
            g = self.tree.topLevelItem(gi)
            for ci in range(g.childCount()):
                c = g.child(ci)
                for si in range(c.childCount()):
                    s = c.child(si)
                    sec = self._tree_items.get(id(s))
                    if sec is not None:
                        return s, sec
        return None

    # ── 点击导航 ──────────────────────────────────────────

    def _on_tree_click(self, item, column):
        pair = self._row_items.get(id(item))
        if pair is not None:
            sec, row, is_text = pair
            self._render_section(sec)
            self._focus_hit(sec, row, is_text)
            return
        sec = self._tree_items.get(id(item))
        if sec is not None:
            self._render_section(sec)

    def _focus_hit(self, sec, row, is_text):
        """点命中行 → 表格选中该行 / 文本滚动到该行"""
        if is_text:
            return
        if self.content_stack.currentIndex() != 0:
            return
        if 0 <= row < self.table_widget.rowCount():
            self.table_widget.selectRow(row)
            self.table_widget.scrollToItem(self.table_widget.item(row, 0))

    # ── 渲染 ──────────────────────────────────────────────

    def _render_section(self, sec):
        self._current_section = sec

        self.content_title.setText(sec.get("title", ""))
        self.content_desc.setText(sec.get("description", ""))
        src = sec.get("source", "")
        self.content_source.setText(f"来源: {src}" if src else "")
        note = (sec.get("note") or "").replace("**", "")
        self.content_note.setText(f"⚠ {note}" if note else "")
        self.content_note.setVisible(bool(note))

        sec_type = sec.get("type", "")
        if sec_type == "bilingual_table":
            self.bilingual_label.setText("EN↗ 复制为英文")
            self.bilingual_label.setVisible(True)
        else:
            self.bilingual_label.setVisible(False)

        if sec_type in ("table", "bilingual_table"):
            self._show_table(sec)
        elif sec_type == "text":
            self._show_text(sec)
        else:
            self.content_stack.setCurrentIndex(2)

    def _show_table(self, sec):
        headers = sec.get("headers", [])
        rows = sec.get("rows", [])

        self.table_widget.setRowCount(len(rows))
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)

        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                item = QTableWidgetItem(str(cell))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # 隔行底色交给主题（主题的 QTableWidget 已有 alternate-background-color）
                self.table_widget.setItem(r, c, item)

        self.table_widget.resizeColumnsToContents()
        header = self.table_widget.horizontalHeader()
        for i in range(self.table_widget.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        self._apply_cell_highlight(sec)
        self.content_stack.setCurrentIndex(0)

    def _apply_cell_highlight(self, sec):
        hits = self._hits.get(id(sec)) or []
        if not hits or self.content_stack.currentIndex() != 0:
            if not hits:
                self.hit_label.setText("")
            return
        c = get_content_colors()
        bg = QBrush(QColor(c.get("hl_bg", "#fde68a")))
        fg = QBrush(QColor(c.get("hl_fg", "#1f2937")))
        n = 0
        for h in hits:
            if h["row"] < 0:
                continue
            for col in h["cols"]:
                it = self.table_widget.item(h["row"], col)
                if it is not None:
                    it.setBackground(bg)
                    it.setForeground(fg)
                    n += 1
        self.hit_label.setText(f"↳ 命中 {n} 个单元格（高亮显示）" if n else "")

    def _show_text(self, sec):
        content = sec.get("content", "")
        html = self._format_text_to_html(content)
        self.text_widget.setHtml(html)
        self._apply_text_highlight(sec)
        self.content_stack.setCurrentIndex(1)

    def _apply_text_highlight(self, sec):
        sels = []
        n = 0
        if self._keyword:
            c = get_content_colors()
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(c.get("hl_bg", "#fde68a")))
            fmt.setForeground(QColor(c.get("hl_fg", "#1f2937")))
            num = _as_number(self._keyword)
            text = self.text_widget.toPlainText()
            for start, end in _iter_text_hits(text, self._keyword, num):
                sel = QTextEdit.ExtraSelection()
                cur = QTextCursor(self.text_widget.document())
                cur.setPosition(start)
                cur.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
                sel.cursor = cur
                sel.format = fmt
                sels.append(sel)
                n += 1
        self.text_widget.setExtraSelections(sels)
        self.hit_label.setText(f"↳ 命中 {n} 处（高亮显示）" if n else "")

    def _format_text_to_html(self, text):
        """将纯文本格式化为美观的 HTML（支持 [TABLE_START]/[TABLE_END] 内嵌表格）

        颜色取自主题（`get_content_colors()`）：富文本读不到 QSS，
        写死浅色主题的颜色会让深色主题出现"深底压深字"。
        公式块用左侧强调条而非浅色填充块，这样在任何主题底色上都成立。
        """
        c = get_content_colors()
        lines = text.split("\n")
        html_parts = []
        in_table = False

        for line in lines:
            stripped = line.strip()

            if stripped == "[TABLE_END]":
                in_table = False
                html_parts.append("</table></div>")
                continue

            if stripped == "[TABLE_START]":
                in_table = True
                html_parts.append(
                    '<div style="overflow-x:auto; margin:8px 0 16px 0;">'
                    '<table border="1" cellpadding="6" cellspacing="0" '
                    'style="border-collapse:collapse; width:100%; font-size:12px;">'
                )
                continue

            if in_table:
                html_parts.append(stripped)
                continue

            if not stripped:
                html_parts.append("<br>")
                continue

            # 一级标题：一、二、三…
            if len(stripped) > 2 and stripped[0] in "一二三四五六七八九十" and stripped[1] in "、. ":
                html_parts.append(f"<h3 style='margin-top:16px; margin-bottom:6px;'>{stripped}</h3>")
                continue

            # 公式行：含 = 或希腊字母
            if "=" in stripped and ("×" in stripped or "÷" in stripped or "/" in stripped or "√" in stripped or "λ" in stripped or "Δ" in stripped or "≥" in stripped or "≤" in stripped):
                html_parts.append(
                    f"<div style='border-left:3px solid {c['banner_bg']}; padding:4px 12px; "
                    f"margin:6px 0; font-family:Consolas,\"Microsoft YaHei\"; font-size:13px;'>{stripped}</div>"
                )
                continue

            # 列表项：以 — 或 · 开头
            if stripped.startswith("—") or stripped.startswith("·"):
                html_parts.append(f"<div style='margin-left:20px; padding:2px 0;'>{stripped}</div>")
                continue

            # 注释行：以 // 或 # 开头
            if stripped.startswith("//") or stripped.startswith("#"):
                html_parts.append(f"<div style='color:{c['muted']}; font-style:italic;'>{stripped}</div>")
                continue

            # 普通行 —— 对变量定义做简单高亮：如 "Q — 传热量"
            if "—" in stripped and len(stripped) < 80:
                parts = stripped.split("—", 1)
                html_parts.append(
                    f"<div style='margin-left:20px; padding:2px 0;'>"
                    f"<b>{parts[0].strip()}</b>"
                    f" — {parts[1].strip()}</div>"
                )
                continue

            html_parts.append(f"<div style='padding:2px 0;'>{stripped}</div>")

        # 数据文件里的内嵌表格 HTML 带历史遗留的浅色主题专用颜色，统一归一化
        return normalize_legacy_content_colors("".join(html_parts), c)

    def on_theme_changed(self):
        """主题切换后重渲染当前条目（HTML/高亮里的颜色取自主题，必须重画）。"""
        sec = getattr(self, "_current_section", None)
        if not sec:
            return
        self._render_section(sec)

    # ── 定位到某一节（供计算器的 📚 按钮调用）──────────────

    def focus_section(self, title, category=""):
        """清空搜索/标签筛选，展开并选中指定条目。找到返回 True。"""
        try:
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)
            self._keyword = ""
            if hasattr(self, "tag_combo"):
                self.tag_combo.setCurrentIndex(0)
            self._rebuild_tree()
            self.search_count_label.setText("")
            self.hit_label.setText("")

            for gi in range(self.tree.topLevelItemCount()):
                g = self.tree.topLevelItem(gi)
                for ci in range(g.childCount()):
                    c = g.child(ci)
                    if category and category not in c.text(0):
                        continue
                    for si in range(c.childCount()):
                        s = c.child(si)
                        sec = self._tree_items.get(id(s))
                        if sec is None or sec.get("title") != title:
                            continue
                        g.setExpanded(True)
                        c.setExpanded(True)
                        self.tree.setCurrentItem(s)
                        self.tree.scrollToItem(s)
                        self._render_section(sec)
                        return True
        except Exception:
            return False
        return False

    # ── 送入计算器 ────────────────────────────────────────

    def _selected_value(self):
        """取当前表格选中值 → (数值 or None, 原始文本)"""
        if self.content_stack.currentIndex() != 0:
            return None, ""
        items = self.table_widget.selectedItems()
        if not items:
            return None, ""
        if len(items) > 1:                       # 整行/多选：取该行第一个能转数值的格
            row = items[0].row()
            for c in range(self.table_widget.columnCount()):
                it = self.table_widget.item(row, c)
                if it is None:
                    continue
                v = _as_number(it.text())
                if v is not None:
                    return v, it.text()
            return None, ""
        v = _as_number(items[0].text())
        return (v, items[0].text()) if v is not None else (None, items[0].text())

    def send_value_to(self, module_name, field, value):
        """把值送到计算器（公开方法，便于测试与后续扩展）。"""
        EXCHANGE.send_to_calculator(module_name, field, value)
        return True

    def _on_send_clicked(self):
        value, raw = self._selected_value()
        if value is None:
            if raw:
                self.hit_label.setText(f"↳ 「{_clip(raw, 24)}」不是数值，无法送入计算器")
            else:
                self.hit_label.setText("↳ 请先在表格里选中一个数值单元格（或整行）")
            return
        if not self.menu_enabled:
            return
        menu = QMenu(self)
        for text, module, field, desc in TARGETS:
            act = menu.addAction(f"{text}    （{desc}）")
            act.setData((module, field))
        chosen = menu.exec(self.send_btn.mapToGlobal(QPoint(0, self.send_btn.height())))
        if chosen is not None:
            module, field = chosen.data()
            self.send_value_to(module, field, value)

    # ── 复制 ──────────────────────────────────────────────

    def _copy_content(self):
        """将当前展示的内容以纯文本格式复制到剪贴板（Tab分隔，直接粘贴Excel）"""
        if not self._current_section:
            return

        sec = self._current_section
        sec_type = sec.get("type", "")
        lines = []

        copy_table = sec.get("copy_table")
        if copy_table:
            entries = copy_table if isinstance(copy_table, list) else copy_table.get("rows", [])
            headers = [] if isinstance(copy_table, list) else copy_table.get("headers", [])
            lines.append("")
            if headers:
                lines.append("\t".join(headers))
            for row in entries:
                lines.append("\t".join(str(c) for c in row))

        elif sec_type == "bilingual_table" or sec_type == "table":
            lines.append("")
            headers_row = []
            for c in range(self.table_widget.columnCount()):
                h = self.table_widget.horizontalHeaderItem(c)
                headers_row.append(h.text() if h else "")
            lines.append("\t".join(headers_row))
            selected = {it.row() for it in self.table_widget.selectedItems()}
            row_range = sorted(selected) if selected else range(self.table_widget.rowCount())
            for r in row_range:
                row_data = []
                for c in range(self.table_widget.columnCount()):
                    item = self.table_widget.item(r, c)
                    row_data.append(item.text() if item and item.text() else "")
                lines.append("\t".join(row_data))

        elif sec_type == "text":
            raw = self.text_widget.toPlainText()
            if raw.strip():
                lines.append(raw)

        text = "\n".join(lines)
        if not text.strip():
            return
        QApplication.clipboard().setText(text)

    # ── 激活回调 ──────────────────────────────────────────

    def on_activate(self):
        """标签页切换时回调"""
        pass

    def refresh(self):
        """刷新数据"""
        self.ref_data = _load_reference_data()
        self._build_search_index()
        tags_cur = self.tag_combo.currentText() if hasattr(self, "tag_combo") else TAG_ALL
        if hasattr(self, "tag_combo"):
            self.tag_combo.blockSignals(True)
            self.tag_combo.clear()
            self.tag_combo.addItem(TAG_ALL)
            self.tag_combo.addItems(self._all_tags())
            idx = self.tag_combo.findText(tags_cur)
            self.tag_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.tag_combo.blockSignals(False)
        self._rebuild_tree()
