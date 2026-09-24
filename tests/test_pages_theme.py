# -*- coding: utf-8 -*-
"""其余标签页的页面级回归测试（资料库 / 计算历史 / 换算器）

为什么要有这个文件：这 3 个页面此前**零测试覆盖**，而它们各自藏着一类"发布时看不见、
用户切到深色主题才炸"的硬编码颜色（2026-09-15 实测：计算历史详情 22 处、资料库 8 处）。

固化三条不变式：
  A. 主题侧 —— 三套主题的语义规则与 HTML 内容配色必须同进同出；且内容配色的
     对比度必须达标（≥4.0:1），否则就是"深底压深字 / 浅底压浅字"
  B. 页面侧 —— 这 3 个页面的源码里不得再出现"亮色主题专用"的硬编码颜色，
     而且必须真的用上语义 objectName（防止又被改回 inline 颜色）
  C. 页面功能 —— 实例化、搜索、渲染、交互不抛异常（这次改造正是在资料库
     搜索路径上踩到一个漏改的变量引用）

运行：
    QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe tests/test_pages_theme.py
"""
import io
import os
import re
import sys
import tokenize
from datetime import datetime, timedelta

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal, Qt                    # noqa: E402
from PySide6.QtWidgets import QApplication                       # noqa: E402

from theme_manager import ThemeManager, get_content_colors, get_active_theme  # noqa: E402

PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}   {extra}")


def section(title):
    print(f"\n{title}")


#: "亮色主题专用"颜色黑名单 —— 出现即代表有页面回到了硬编码配色
LIGHT_ONLY_COLORS = {
    "#2c3e50", "#7f8c8d", "#ecf0f1", "#fef9e7", "#f8f9fa", "#f0f0f0",
    "#f4f6f7", "#e67e22", "#3498db", "#2980b9", "#e74c3c", "#c0392b",
    "#aaa", "#888", "#555", "#666", "#ddd", "#333", "#95a5a6",
}

PAGE_FILES = {
    "资料库": "modules/reference/reference_widget.py",
    "计算历史": "modules/history_viewer.py",
    "换算器": "modules/converter/converter_widget.py",
}


def code_text(path):
    """读取源码并剥掉注释（避免"注释里提了颜色"造成误报）。"""
    src = open(path, encoding="utf-8").read()
    parts = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            continue
        parts.append(tok.string)
    return " ".join(parts)


def hex_colors(text):
    return {m.lower() for m in re.findall(r"#[0-9a-fA-F]{3,8}\b", text)}


def _linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast(fg, bg):
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


app = QApplication.instance() or QApplication([])

# ══════════════════════════════ A. 主题侧 ══════════════════════════════
section("A. 主题语义规则与内容配色")

tm = ThemeManager()
check("语义规则覆盖全部主题", set(ThemeManager.SEMANTIC_RULES) == set(tm.themes),
      set(tm.themes) ^ set(ThemeManager.SEMANTIC_RULES))

for name, qss in tm.themes.items():
    for sel in ("QLabel#mutedLabel", "QLabel#accentLabel",
                "QPushButton#primaryBtn", "QPushButton#dangerBtn"):
        check(f"{name} 主题定义了 {sel}", sel in qss)

keys_ref = set(ThemeManager.CONTENT_COLORS["light"])
for name, pal in ThemeManager.CONTENT_COLORS.items():
    check(f"{name} 内容配色键与其他主题一致", set(pal) == keys_ref,
          set(pal) ^ keys_ref)

# HTML 内容配色是硬编码在字典里的，必须守住可读性 —— 用对比度量化
THEME_BG = {"light": "#ffffff", "dark": "#2d2d2d", "blue": "#f0f7ff"}
for name, pal in ThemeManager.CONTENT_COLORS.items():
    bg = THEME_BG[name]
    for key in ("muted", "accent", "ok"):
        ratio = contrast(pal[key], bg)
        check(f"{name} 主题 {key} 色对比度 {ratio:.2f}:1 ≥ 4.0", ratio >= 4.0,
              f"{pal[key]} on {bg}")
    banner = contrast(pal["banner_fg"], pal["banner_bg"])
    check(f"{name} 主题 banner 文字对比度 {banner:.2f}:1 ≥ 4.0", banner >= 4.0,
          f"{pal['banner_fg']} on {pal['banner_bg']}")

check("默认取色 = 亮色主题", get_content_colors()["muted"] == "#6b7280")
tm.set_theme("dark")
check("切到深色后取到深色配色", get_content_colors()["muted"] == "#a3a3a3")
check("模块级当前主题同步为 dark", get_active_theme() == "dark")
check("实例方法取色一致", tm.get_content_colors()["muted"] == "#a3a3a3")
tm.set_theme("light")
check("切回亮色后恢复", get_content_colors()["muted"] == "#6b7280")
check("未知主题名不会崩", get_content_colors("nope")["muted"] == "#6b7280")

# ══════════════════════════════ B. 页面源码黑名单 ══════════════════════════════
section("B. 页面源码不得再有亮色主题专用颜色")

for label, rel in PAGE_FILES.items():
    path = os.path.join(PROJ, rel)
    found = hex_colors(code_text(path)) & LIGHT_ONLY_COLORS
    check(f"{label} 无硬编码亮色 {sorted(found) if found else ''}", not found, found)

ref_src = code_text(os.path.join(PROJ, PAGE_FILES["资料库"]))
his_src = code_text(os.path.join(PROJ, PAGE_FILES["计算历史"]))
check("资料库用了语义 objectName（mutedLabel/accentLabel/primaryBtn）",
      all(n in ref_src for n in ("mutedLabel", "accentLabel", "primaryBtn")))
check("计算历史用了语义 objectName（primaryBtn/dangerBtn）",
      all(n in his_src for n in ("primaryBtn", "dangerBtn")))
check("资料库 / 计算历史两页都实现了 on_theme_changed 钩子",
      all("def on_theme_changed" in s for s in (ref_src, his_src)))
check("主窗口会在主题切换时通知各页面",
      "on_theme_changed" in code_text(os.path.join(PROJ, "main.py")))

# ══════════════════════════════ C. 资料库 ══════════════════════════════
section("C. 资料库页面")

from modules.reference.reference_widget import (              # noqa: E402
    ReferenceWidget, CATEGORY_ICONS, GROUP_ORDER,
)

ref = ReferenceWidget()
check("实例化无异常，数据已加载", len(ref.ref_data) > 0, len(ref.ref_data))
# 2026-09-16 资料库整理：原辅料标准(19) 拆成 食品添加剂标准(10)+工业原料标准(9)，
# 由 14 类变为 15 类；树顶层改为「分组」（5 个），分类降为第二层。
check("分类数为 16（README 数字须与此一致）", len(ref.ref_data) == 16, len(ref.ref_data))
check("分组数为 6", len({c.get("group") for c in ref.ref_data}) == 6)
check("树顶层节点数 = 分组数", ref.tree.topLevelItemCount() == len(GROUP_ORDER),
      ref.tree.topLevelItemCount())

missing_icons = [c.get("category") for c in ref.ref_data
                 if c.get("category") not in CATEGORY_ICONS]
check("每个分类都有图标（新增分类别忘了补 CATEGORY_ICONS）",
      not missing_icons, missing_icons)
check("每个条目都有标签（标签筛选的数据源）",
      all(s.get("tags") for c in ref.ref_data for s in c.get("sections", [])))

# 搜索路径
ref._on_search("蒸汽")
check("搜索不抛异常且命中", "匹配" in ref.search_count_label.text(),
      ref.search_count_label.text())
check("搜索后树非空", ref.tree.topLevelItemCount() > 0)
ref._on_search("")
check("清空搜索后恢复完整树", ref.tree.topLevelItemCount() == len(GROUP_ORDER),
      ref.tree.topLevelItemCount())

# 渲染两类内容
table_sec = text_sec = None
for cat in ref.ref_data:
    for sec in cat.get("sections", []):
        if sec.get("type") == "table" and table_sec is None:
            table_sec = sec
        if sec.get("type") == "text" and text_sec is None:
            text_sec = sec

ref._show_table(table_sec)
check("表格页渲染：切换到表格视图", ref.content_stack.currentIndex() == 0)
check("表格页渲染：表头非空", ref.table_widget.columnCount() > 0)
check("表格页渲染：有数据行", ref.table_widget.rowCount() > 0)
check("表格单元格没有手写背景色（隔行色交给主题的 alternate-background-color）",
      ref.table_widget.item(0, 0).background().style() == Qt.BrushStyle.NoBrush,
      ref.table_widget.item(0, 0).background().style())

ref._show_text(text_sec)
check("文本页渲染：切换到文本视图", ref.content_stack.currentIndex() == 1)
html = ref.text_widget.toHtml()
check("文本页 HTML 不含亮色专用颜色",
      not (hex_colors(html) & LIGHT_ONLY_COLORS), hex_colors(html) & LIGHT_ONLY_COLORS)

# 对 HTML 生成器做确定性断言（真实条目不一定含公式行/注释行；
# 且 QTextEdit.toHtml() 会归一化掉 border-left，不能拿来验配色）
sample = "换热器设计公式\nQ = K × A × ΔT\n// 说明：K 为总传热系数"
gen_light = ref._format_text_to_html(sample)
check("公式块用主题强调色描边",
      get_content_colors()["banner_bg"].lower() in gen_light.lower())
check("注释行用主题次要色",
      get_content_colors()["muted"].lower() in gen_light.lower())
check("生成的 HTML 不含亮色专用颜色",
      not (hex_colors(gen_light) & LIGHT_ONLY_COLORS), hex_colors(gen_light) & LIGHT_ONLY_COLORS)

tm.set_theme("dark")
gen_dark = ref._format_text_to_html(sample)
check("切换主题后生成的 HTML 配色随之变化", gen_light != gen_dark)
check("深色主题下用的是深色配色",
      get_content_colors()["muted"].lower() in gen_dark.lower())
tm.set_theme("light")

bad = [s.get("title") for cat in ref.ref_data for s in cat.get("sections", [])
       if s.get("type") == "text"
       and (hex_colors(ref._format_text_to_html(s.get("content", ""))) & LIGHT_ONLY_COLORS)]
check(f"全部 {sum(1 for c in ref.ref_data for s in c.get('sections', []) if s.get('type') == 'text')} "
      f"个文字条目渲染后都无亮色专用颜色", not bad, bad)

ref._current_section = text_sec
ref.on_theme_changed()
check("on_theme_changed 不抛异常且仍有内容", ref.content_stack.currentIndex() == 1)

copy_ok, copy_err = True, ""
try:
    ref._copy_content()
except Exception as e:      # noqa: BLE001
    copy_ok, copy_err = False, e
check("复制文本页内容不抛异常", copy_ok, copy_err)
ref._current_section = table_sec
try:
    ref._copy_content()
except Exception as e:      # noqa: BLE001
    copy_ok, copy_err = False, e
check("复制表格内容不抛异常", copy_ok, copy_err)

# ══════════════════════════════ D. 计算历史 ══════════════════════════════
section("D. 计算历史页面")

import modules.history_db as history_db                        # noqa: E402


class FakeHistoryDB(QObject):
    """替代真实 HistoryDB —— 避免测试触碰用户目录 ~/.ChemCal 的真实历史库。

    接口须与 modules/history_db.py 保持同步（多出的筛选参数用 **kwargs 吃掉，
    免得页面一加筛选条件就在这里 TypeError）。
    """

    record_added = Signal()
    records_changed = Signal()

    def __init__(self, records=None):
        super().__init__()
        self.records = records or []

    def get_calculator_ids(self):
        return {"demo_calc": "演示计算器"}

    def get_all(self, calculator_id=None, keyword="", limit=50, offset=0,
                date_from=None, date_to=None, **kwargs):
        recs = self.records[offset:offset + limit]
        return recs, len(self.records)

    def get_record(self, record_id):
        return next((r for r in self.records if r["id"] == record_id), None)

    def get_all_records(self, calculator_id=None, keyword="", date_from=None,
                        date_to=None, limit=None, **kwargs):
        return list(self.records)

    def get_statistics(self, calculator_id=None, keyword="", date_from=None,
                       date_to=None, top_n=10, trend_days=14, **kwargs):
        by_calc = {}
        by_cat = {}
        by_day = {}
        for r in self.records:
            by_calc[r["calculator_name"]] = by_calc.get(r["calculator_name"], 0) + 1
            cat = r["calculator_category"] or "未分类"
            by_cat[cat] = by_cat.get(cat, 0) + 1
            day = r["created_at"][:10]
            by_day[day] = by_day.get(day, 0) + 1
        return {
            "total": len(self.records),
            "first_at": self.records[0]["created_at"] if self.records else None,
            "last_at": self.records[-1]["created_at"] if self.records else None,
            "active_days": len(by_day),
            "category_count": len(by_cat),
            "calculator_count": len(by_calc),
            "by_category": sorted(by_cat.items(), key=lambda x: -x[1]),
            "by_calculator": sorted(by_calc.items(), key=lambda x: -x[1])[:top_n],
            "other_count": 0,
            "by_day": sorted(by_day.items()),
            "by_month": [],
        }

    def delete(self, record_id):
        self.records = [r for r in self.records if r["id"] != record_id]

    def delete_many(self, record_ids):
        ids = set(record_ids or [])
        before = len(self.records)
        self.records = [r for r in self.records if r["id"] not in ids]
        return before - len(self.records)

    def delete_filtered(self, calculator_id=None, keyword="", date_from=None,
                        date_to=None, **kwargs):
        before = len(self.records)
        self.records = []
        return before


FAKE_RECORDS = [{
    "id": 1,
    "calculator_id": "demo_calc",
    "calculator_name": "演示计算器",
    "calculator_category": "工艺设备",
    "created_at": "2026-09-15T10:30:00",
    "inputs": {"直径 mm": 1000, "材料": "Q345R"},
    "outputs": {"壁厚 mm": 8.5},
    "notes": "备注内容",
}]

_real_db = history_db.HistoryDB
history_db.HistoryDB = FakeHistoryDB
try:
    from modules.history_viewer import HistoryViewer            # noqa: E402
    hist = HistoryViewer()
    hist._db = FakeHistoryDB(FAKE_RECORDS)
    hist._refresh_filter()
    hist._load_history()
    check("实例化无异常", hist is not None)
    check("筛选下拉含「全部计算器」", hist.calc_filter.itemText(0) == "全部计算器")
    check("列表载入 1 条记录", hist.history_list.count() == 1, hist.history_list.count())
    check("分页标签已更新", "1" in hist.page_label.text(), hist.page_label.text())

    html = hist._format_detail(FAKE_RECORDS[0])
    c_light = get_content_colors()
    check("详情 HTML 不含亮色专用颜色",
          not (hex_colors(html) & LIGHT_ONLY_COLORS), hex_colors(html) & LIGHT_ONLY_COLORS)
    check("详情 HTML 无写死深色正文（正文继承主题）", "#2c3e50" not in html.lower())
    check("详情 HTML 使用亮色主题色", c_light["banner_bg"].lower() in html.lower())
    check("详情含计算器名与输出", "演示计算器" in html and "8.5" in html)

    hist._current_record = FAKE_RECORDS[0]
    hist.on_theme_changed()
    check("亮色下 on_theme_changed 正常",
          c_light["banner_bg"].lower() in hist.detail_text.toHtml().lower())

    tm.set_theme("dark")
    dark_html = hist._format_detail(FAKE_RECORDS[0])
    check("深色主题下详情改用深色配色",
          get_content_colors()["muted"].lower() in dark_html.lower())
    check("深色主题下不含亮色主题的正文色",
          c_light["muted"].lower() not in dark_html.lower())
    ratio = contrast(get_content_colors()["muted"], "#2d2d2d")
    check(f"深色主题下次要文字对比度 {ratio:.2f}:1 ≥ 4.0", ratio >= 4.0)

    hist.on_theme_changed()
    check("深色下 on_theme_changed 重渲染成功",
          get_content_colors()["muted"].lower() in hist.detail_text.toHtml().lower())
    tm.set_theme("light")

    check("删除按钮未选中记录时禁用", not hist.delete_btn.isEnabled())
    hist._current_record = FAKE_RECORDS[0]
    hist.delete_btn.setEnabled(True)
    check("删除按钮可启用", hist.delete_btn.isEnabled())
finally:
    history_db.HistoryDB = _real_db

# ══════════════════════════════ E. 换算器 ══════════════════════════════
section("E. 换算器页面")

from modules.converter.converter_widget import ConverterWidget   # noqa: E402

conv = ConverterWidget()
check("实例化无异常", conv is not None)
check("换算器类目数为 21（README 数字须与此一致）", len(conv.pages) == 21, len(conv.pages))
check("导航项数与页面数一致", conv.nav_list.count() == len(conv.pages))
switch_ok, switch_err = True, ""
for i in range(conv.nav_list.count()):
    try:
        conv.nav_list.setCurrentRow(i)
    except Exception as e:      # noqa: BLE001
        switch_ok, switch_err = False, f"第 {i} 页: {e}"
        break
check("逐个切换全部换算页面不抛异常", switch_ok, switch_err)
check("换算器页面无硬编码亮色",
      not (hex_colors(code_text(os.path.join(PROJ, PAGE_FILES["换算器"])))
           & LIGHT_ONLY_COLORS))

# ══════════════════════════════ 汇总 ══════════════════════════════
print()
print("=" * 60)
print(f"总结: {PASS} 过, {FAIL} 失败")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
