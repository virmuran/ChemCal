# -*- coding: utf-8 -*-
"""计算历史增强的回归测试（筛选 / 批量删除 / 统计 / 导出）

背景：历史页此前只有"看 / 搜 / 删单条"，2026-09-15 做了增强：
时间范围筛选、多选批量删除、使用统计、CSV/Word/PDF 导出。

这个文件与 tests/test_pages_theme.py 的分工：
  - test_pages_theme.py 管"页面外观与主题可读性"（那 4 个页面的配色不变式）
  - 本文件管"历史页的功能正确性"，并且**直接打真实 SQLite**（落临时库，不碰
    ~/.ChemCal 的真实数据），因此它同时是历史库层的测试。

固化四类不变式：
  A. 库层 —— 时间范围端点闭合（date_from/date_to 当天的记录必须被包含）、
     筛选口径在"列表 / 计数 / 统计 / 导出"四处必须完全一致
  B. 统计 —— 计数必须与逐条数出来的结果相等（不是"看着差不多"）
  C. 导出 —— CSV 能被 Excel 正确解码（BOM + 列序）；generate_report() 必须返回
     str 或 None（dict 会让 ReportExporter 直接 AttributeError）；
     get_project_info() 必须返回 dict；DOCX 导出链路端到端可产出真实文件
  D. 页面 —— 多选/筛选/加载更多的状态机正确；统计 HTML 颜色全部取自主题，
     深色主题下不得出现亮色主题专用色

运行：
    QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe tests/test_history.py
"""
import csv
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt                                  # noqa: E402
from PySide6.QtWidgets import QApplication                       # noqa: E402

app = QApplication.instance() or QApplication([])

from theme_manager import ThemeManager, get_content_colors       # noqa: E402
from modules.history_db import HistoryDB                         # noqa: E402

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


def reset_filters(hist):
    """把页面筛选恢复到"全部时间 + 全部计算器 + 无关键词"。

    页面是有状态的 —— 段落之间必须显式复位，否则上一段的筛选条件会静默
    影响下一段（这次的"CSV 只导出 2 条"就是这么来的）。
    """
    hist.search_edit.setText("")
    hist.calc_filter.setCurrentIndex(0)
    hist.time_filter.setCurrentIndex(hist.time_filter.findData("all"))
    hist._current_page = 0


#: "亮色主题专用"颜色黑名单 —— 与 test_pages_theme.py 同源
LIGHT_ONLY_COLORS = {
    "#2c3e50", "#7f8c8d", "#ecf0f1", "#fef9e7", "#f8f9fa", "#f0f0f0",
    "#f4f6f7", "#e67e22", "#3498db", "#2980b9", "#e74c3c", "#c0392b",
    "#aaa", "#888", "#555", "#666", "#ddd", "#333", "#95a5a6",
}


def hex_colors(text):
    return {m.lower() for m in
            __import__("re").findall(r"#[0-9a-fA-F]{3,8}\b", text)}


def contrast(fg, bg):
    """WCAG 相对亮度对比度。"""
    def _lum(h):
        h = h.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        vals = []
        for i in (0, 2, 4):
            v = int(h[i:i + 2], 16) / 255.0
            vals.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
        r, g, b = vals
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    l1, l2 = _lum(fg), _lum(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


# ══════════════════════════════════════════════════════════════════
# 准备：临时库 + 覆盖各种时间落点的样例数据
# ══════════════════════════════════════════════════════════════════

TMPDIR = tempfile.mkdtemp(prefix="chemcal_hist_test_")
DB_PATH = os.path.join(TMPDIR, "history.db")

db = HistoryDB()
db.db_path = DB_PATH          # 单例指向临时文件，绝不碰用户真实历史
db._init_db()

TODAY = datetime.now().date()


def ts(days_ago, hh=10, mm=0):
    d = TODAY - timedelta(days=days_ago)
    return f"{d.isoformat()}T{hh:02d}:{mm:02d}:00"


#: (calculator_id, 名称, 分类, created_at, notes)
#: 注意 notes 之间不能互为子串 —— "十天前" 是 "四十天前" 的子串，会让关键词命中数
#: 变得反直觉（这正是安全阀 Kd 那次踩过的同一类坑）。
SAMPLES = [
    ("steam_property_calculator", "水蒸气性质", "物性数据", ts(0, 9), "今天"),
    ("steam_property_calculator", "水蒸气性质", "物性数据", ts(0, 15), "今天"),
    ("pump_power_calculator", "离心泵功率计算", "流体输送", ts(3), "三天前"),
    ("safety_valve_calculator", "安全阀计算", "安全泄放", ts(10), "十天前"),
    ("heat_exchanger_calculator", "换热器计算", "换热设备", ts(40), "早期记录"),
]


def seed():
    """重建样例数据（每个用到库的段落都从干净状态开始）。"""
    db.delete_filtered()
    for cid, name, cat, created, note in SAMPLES:
        db.save(cid, name, cat, {"介质": "水", "流量 t/h": 12.5},
                {"结果": 8.5, "多行": "a\nb"}, notes=note, created_at=created)


# ══════════════════════════════════════════════════════════════════
section("A. 历史库层：写入 / 读取 / 筛选 / 时间端点")

seed()
check("save 后可读回全部记录", db.count() == len(SAMPLES), db.count())
check("save 返回自增 id", isinstance(db.save(
    "x", "X", "cat", {}, {}, created_at=ts(1)), int))
db.delete_filtered()
seed()

recs, total = db.get_all(limit=100)
check("get_all 返回 (列表, 总数)", isinstance(recs, list) and total == len(SAMPLES))
check("get_all 按时间倒序", recs[0]["created_at"] >= recs[-1]["created_at"])
check("记录字段完整",
      {"id", "calculator_id", "calculator_name", "calculator_category",
       "inputs", "outputs", "notes", "created_at"} <= set(recs[0].keys()))
check("inputs/outputs 已从 JSON 还原成 dict",
      isinstance(recs[0]["inputs"], dict) and isinstance(recs[0]["outputs"], dict))
check("多行输出原样保留", any("\n" in str(r["outputs"].get("多行", "")) for r in recs))

check("分页 limit 生效", len(db.get_all(limit=2)[0]) == 2)
check("分页 offset 生效",
      db.get_all(limit=2, offset=2)[0][0]["id"] != db.get_all(limit=2)[0][0]["id"])
check("总数与分页无关", db.get_all(limit=1)[1] == len(SAMPLES))

# 关键词
check("关键词命中计算器名", db.count(keyword="泵") == 1, db.count(keyword="泵"))
check("关键词命中备注", db.count(keyword="十天前") == 1)
check("关键词命中输入参数（中文键）", db.count(keyword="介质") == len(SAMPLES))
check("关键词无命中", db.count(keyword="不存在的东西") == 0)
check("关键词命中输出值", db.count(keyword="8.5") == len(SAMPLES))

# 计算器筛选
check("按 calculator_id 筛选",
      db.count("steam_property_calculator") == 2,
      db.count("steam_property_calculator"))
check("计算器筛选 + 关键词 叠加",
      db.count("steam_property_calculator", keyword="今天") == 2)

# 时间范围（端点闭合是这里最容易错的地方）
d0 = TODAY.isoformat()
check("单日筛选：date_from=date_to=今天",
      db.count(date_from=d0, date_to=d0) == 2, db.count(date_from=d0, date_to=d0))

db.save("edge", "端点", "测试", {}, {}, created_at=f"{d0}T00:00:00")
db.save("edge", "端点", "测试", {}, {}, created_at=f"{d0}T23:59:59.999999")
check("时间下端点闭合（当天 00:00:00 被包含）",
      db.count(date_from=d0, date_to=d0) == 4, db.count(date_from=d0, date_to=d0))
check("时间上端点闭合（当天 23:59:59.999999 被包含）",
      db.count(date_from=d0, date_to=d0) == 4)
db.delete_filtered(calculator_id="edge")
check("按条件删除清理干净", db.count(calculator_id="edge") == 0)

check("只给 date_from",
      db.count(date_from=(TODAY - timedelta(days=3)).isoformat()) == 3,
      db.count(date_from=(TODAY - timedelta(days=3)).isoformat()))
check("只给 date_to（40 天前那天及以前）",
      db.count(date_to=(TODAY - timedelta(days=40)).isoformat()) == 1)
check("时间倒挂区间返回 0 条",
      db.count(date_from=d0, date_to=(TODAY - timedelta(days=5)).isoformat()) == 0)

# 筛选口径一致性：列表 / 计数 / 导出 三处必须同数
kw = "今天"
n_list = len(db.get_all(keyword=kw, limit=1000)[0])
n_count = db.count(keyword=kw)
n_export = len(db.get_all_records(keyword=kw))
check("列表 / 计数 / 导出 三处口径一致",
      n_list == n_count == n_export, f"{n_list}/{n_count}/{n_export}")

# ══════════════════════════════════════════════════════════════════
section("B. 历史库层：统计口径")

seed()
st = db.get_statistics()
check("统计总数 == 库内总条数", st["total"] == len(SAMPLES), st["total"])
check("按分类计数之和 == 总数",
      sum(n for _c, n in st["by_category"]) == len(SAMPLES), st["by_category"])
check("按计算器计数之和 == 总数",
      sum(n for _c, n in st["by_calculator"]) + st["other_count"] == len(SAMPLES))
check("按日计数之和 == 总数",
      sum(n for _d, n in st["by_day"]) == len(SAMPLES), st["by_day"])
check("分类数正确", st["category_count"] == 4, st["category_count"])
check("计算器数正确", st["calculator_count"] == 4, st["calculator_count"])
check("活跃天数正确（5 条数据跨 4 个不同日期）", st["active_days"] == 4, st["active_days"])
check("时间跨度首尾正确",
      st["first_at"].startswith(ts(40)) and st["last_at"].startswith(ts(0, 15)),
      f"{st['first_at']} / {st['last_at']}")

# 逐条数出来的"真值"对比 —— 不以函数自己的输出为准
expect_cat = {}
expect_calc = {}
for cid, name, cat, created, _n in SAMPLES:
    expect_cat[cat] = expect_cat.get(cat, 0) + 1
    expect_calc[name] = expect_calc.get(name, 0) + 1
check("按分类分布与人工统计一致",
      dict(st["by_category"]) == expect_cat,
      f"{dict(st['by_category'])} != {expect_cat}")
check("计算器排行与人工统计一致",
      dict(st["by_calculator"]) == expect_calc,
      f"{dict(st['by_calculator'])} != {expect_calc}")
check("排行按条数降序",
      [n for _c, n in st["by_calculator"]] ==
      sorted([n for _c, n in st["by_calculator"]], reverse=True))
check("按日序列升序", [d for d, _n in st["by_day"]] == sorted(d for d, _n in st["by_day"]))

st_pump = db.get_statistics(calculator_id="pump_power_calculator")
check("统计受筛选影响", st_pump["total"] == 1, st_pump["total"])

st_range = db.get_statistics(date_from=(TODAY - timedelta(days=3)).isoformat(),
                             date_to=d0)
check("统计受时间范围影响", st_range["total"] == 3, st_range["total"])

st_empty = db.get_statistics(keyword="不存在的东西")
check("空结果统计不崩且 total=0", st_empty["total"] == 0)
check("空结果各列表为空",
      st_empty["by_category"] == [] and st_empty["by_day"] == [])

st_top = db.get_statistics(top_n=1)
check("top_n 限制排行长度", len(st_top["by_calculator"]) <= 1)
check("被截断的条数进 other_count",
      sum(n for _c, n in st_top["by_calculator"]) + st_top["other_count"] == len(SAMPLES))

# ══════════════════════════════════════════════════════════════════
section("C. 历史库层：删除")

seed()
ids = [r["id"] for r in db.get_all_records(calculator_id="steam_property_calculator")]
check("批量删除返回实际条数", db.delete_many(ids) == 2)
check("批量删除后剩余正确", db.count() == len(SAMPLES) - 2, db.count())
check("批量删除不存在的 id 返回 0", db.delete_many([999999]) == 0)
check("批量删除空列表返回 0", db.delete_many([]) == 0)

seed()
check("按条件删除返回条数", db.delete_filtered(calculator_id="pump_power_calculator") == 1)
check("按条件删除后剩余正确", db.count() == len(SAMPLES) - 1)

seed()
check("清空整库返回条数", db.clear_all() == len(SAMPLES))
check("清空后库为空", db.count() == 0)
check("单条删除已不存在的记录返回 False", db.delete(999999) is False)
check("空库统计 total=0", db.get_statistics()["total"] == 0)
check("空库导出返回空列表", db.get_all_records() == [])

seed()
one = db.get_all_records(limit=1)[0]["id"]
check("单条删除返回 True", db.delete(one) is True)
check("单条删除后总数 -1", db.count() == len(SAMPLES) - 1)
check("get_record 能按 id 取回", db.get_record(db.get_all_records(limit=1)[0]["id"]) is not None)
check("get_record 取不存在的 id 返回 None", db.get_record(999999) is None)

# ══════════════════════════════════════════════════════════════════
section("D. 历史页面：筛选状态 / 多选 / 加载更多")

from modules.history_viewer import HistoryViewer, TIME_RANGES   # noqa: E402

seed()
# HistoryDB 是单例，页面会用同一个 db；这里显式注入我们的临时库实例
hist = HistoryViewer()
hist._db = db                       # 绕过单例，确保读写的是临时库
hist.confirm_enabled = False        # 离屏下 QMessageBox 会永久阻塞
hist._refresh_filter()
hist._load_history()

check("实例化无异常", hist is not None)
check("时间范围下拉项齐全", hist.time_filter.count() == len(TIME_RANGES))
check("时间范围默认「全部时间」", hist.time_filter.currentData() == "all")
check("列表载入全部记录",
      hist.history_list.count() == len(SAMPLES), hist.history_list.count())
check("未选任何记录时「删除选中」禁用", not hist.delete_selected_btn.isEnabled())
check("有记录时「清空筛选结果」可用", hist.clear_btn.isEnabled())
check("有记录时导出按钮可用", hist.export_csv_btn.isEnabled())
check("列表项已挂载记录本体（避免点击时全表扫描）",
      hist.history_list.item(0).data(Qt.UserRole + 1) is not None)

# 多选
hist.history_list.item(0).setSelected(True)
hist.history_list.item(1).setSelected(True)
check("多选后能取出两个 id", len(hist._selected_ids()) == 2, len(hist._selected_ids()))
check("多选后「删除选中」可用", hist.delete_selected_btn.isEnabled())
check("按钮文案带选中条数", "2" in hist.delete_selected_btn.text(),
      hist.delete_selected_btn.text())
check("状态标签显示已选条数", "已选 2" in hist.page_label.text(), hist.page_label.text())

hist.history_list.clearSelection()
check("清空选择后按钮回到禁用", not hist.delete_selected_btn.isEnabled())
check("清空选择后文案复位",
      hist.delete_selected_btn.text() == "删除选中", hist.delete_selected_btn.text())

# 时间范围筛选
hist.time_filter.setCurrentIndex(hist.time_filter.findData("today"))
check("切「今天」后只显示今天的记录",
      hist.history_list.count() == 2, hist.history_list.count())
check("切「今天」后总数同步", hist._total == 2, hist._total)

hist.time_filter.setCurrentIndex(hist.time_filter.findData("7d"))
expected_7d = sum(1 for _c, _n, _ca, created, _no in SAMPLES
                  if 0 <= (TODAY - datetime.fromisoformat(created).date()).days <= 6)
check("切「近 7 天」条数与独立算法一致",
      hist._total == expected_7d, f"{hist._total} != {expected_7d}")

hist.time_filter.setCurrentIndex(hist.time_filter.findData("30d"))
expected_30d = sum(1 for _c, _n, _ca, created, _no in SAMPLES
                   if (TODAY - datetime.fromisoformat(created).date()).days <= 29)
check("切「近 30 天」排除 40 天前的记录",
      hist._total == expected_30d == 4, f"{hist._total} != {expected_30d}")

hist.time_filter.setCurrentIndex(hist.time_filter.findData("month"))
expected_month = sum(1 for _c, _n, _ca, created, _no in SAMPLES
                     if datetime.fromisoformat(created).date().replace(day=1)
                     == TODAY.replace(day=1))
check("切「本月」条数与独立算法一致",
      hist._total == expected_month, f"{hist._total} != {expected_month}")

hist.time_filter.setCurrentIndex(hist.time_filter.findData("all"))
check("切回「全部时间」恢复全量", hist._total == len(SAMPLES), hist._total)

# 计算器筛选
hist.calc_filter.setCurrentIndex(hist.calc_filter.findData("steam_property_calculator"))
check("按计算器筛选生效", hist._total == 2, hist._total)
hist.calc_filter.setCurrentIndex(0)
check("回落「全部计算器」恢复全量", hist._total == len(SAMPLES))

# 关键词
hist.search_edit.setText("泵")
check("关键词搜索生效", hist._total == 1, hist._total)
hist.search_edit.setText("")
check("清空关键词恢复全量", hist._total == len(SAMPLES))

# 加载更多
hist._load_more()
check("加载更多不改变总数标签", hist._total == len(SAMPLES))
check("记录不足一页时「加载更多」禁用", not hist.load_more_btn.isEnabled())

# 批量删除（真实走库）
hist.history_list.item(0).setSelected(True)
hist.history_list.item(1).setSelected(True)
sel = hist._selected_ids()
hist._delete_selected()
check("批量删除后库内条数下降",
      db.count() == len(SAMPLES) - len(sel), db.count())
check("批量删除后列表刷新", hist.history_list.count() == db.count())
check("批量删除后清空详情", hist.detail_text.toPlainText() == "")

seed()
hist.refresh()
hist.time_filter.setCurrentIndex(hist.time_filter.findData("today"))
hist._clear_filtered()
check("清空筛选结果只删筛选内的记录",
      db.count() == len(SAMPLES) - 2, db.count())
check("筛选外的记录仍在库中", db.count(keyword="早期记录") == 1)

seed()
hist.refresh()
hist._current_record = db.get_all_records(limit=1)[0]
hist._delete_record()
check("单条删除后库内条数 -1", db.count() == len(SAMPLES) - 1, db.count())

# ══════════════════════════════════════════════════════════════════
section("E. 导出：CSV / 报告契约 / DOCX 链路")

seed()
hist.refresh()
reset_filters(hist)

CSV_PATH = os.path.join(TMPDIR, "hist.csv")
written = hist._write_csv(CSV_PATH)
check("CSV 写入条数 == 库内条数", written == len(SAMPLES), written)
check("CSV 文件已生成", os.path.exists(CSV_PATH))

with open(CSV_PATH, "rb") as fp:
    raw = fp.read()
check("CSV 带 UTF-8 BOM（Excel 双击不乱码）", raw.startswith(b"\xef\xbb\xbf"))

with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as fp:
    rows = list(csv.reader(fp))
check("CSV 表头正确",
      rows[0] == ["序号", "时间", "分类", "计算器", "输入参数", "计算结果", "备注"],
      rows[0])
check("CSV 行数 == 记录数 + 表头", len(rows) == len(SAMPLES) + 1, len(rows))
check("CSV 含中文计算器名",
      any("水蒸气性质" in r[3] for r in rows[1:]), rows[1:3])
check("CSV 输入参数已展开成 k=v",
      any("介质=水" in r[4] for r in rows[1:]), rows[1][4])
check("CSV 单元格内多行值已折成单行（不撑破表格）",
      all("\n" not in cell for r in rows[1:] for cell in r), "存在换行")
check("CSV 时间列为可读格式",
      all(len(r[1]) == 19 and r[1][4] == "-" for r in rows[1:]), rows[1][1])

# 导出受筛选影响
hist.time_filter.setCurrentIndex(hist.time_filter.findData("today"))
CSV2 = os.path.join(TMPDIR, "hist_today.csv")
n2 = hist._write_csv(CSV2)
check("CSV 导出遵循当前筛选", n2 == 2, n2)
with open(CSV2, "r", encoding="utf-8-sig", newline="") as fp:
    rows2 = list(csv.reader(fp))
check("筛选后的 CSV 只含今天的记录", len(rows2) == 3, len(rows2))
hist.time_filter.setCurrentIndex(hist.time_filter.findData("all"))

# 报告契约
report = hist.generate_report()
check("generate_report() 返回 str（dict 会让 ReportExporter 崩溃）",
      isinstance(report, str), type(report).__name__)
check("报告含标题与筛选条件", "计算历史记录清单" in report and "筛选条件" in report)
check("报告含记录条数", f"记录条数：{len(SAMPLES)}" in report)
check("报告含每条计算器名与分类",
      all(name in report for _c, name, _ca, _t, _n in SAMPLES))
check("报告含输入参数明细", "介质 = 水" in report)

hist.search_edit.setText("不存在的东西")
check("无记录时 generate_report() 返回 None", hist.generate_report() is None)
hist.search_edit.setText("")

info = hist.get_project_info()
check("get_project_info() 返回 dict", isinstance(info, dict), type(info).__name__)
check("项目信息含标准键",
      {"company_name", "project_number", "project_name",
       "subproject_name", "calculation_type"} <= set(info.keys()), list(info))

# DOCX 端到端（不经过文件对话框，直接走生成函数）
try:
    from utils.docx_utils import generate_report_docx
    DOCX_PATH = os.path.join(TMPDIR, "hist.docx")
    generate_report_docx(hist.generate_report(), DOCX_PATH, title="计算历史记录")
    check("DOCX 链路产出真实文件",
          os.path.exists(DOCX_PATH) and os.path.getsize(DOCX_PATH) > 1000,
          os.path.getsize(DOCX_PATH) if os.path.exists(DOCX_PATH) else "缺失")
    import docx as _docx
    text = "\n".join(p.text for p in _docx.Document(DOCX_PATH).paragraphs)
    check("DOCX 正文含计算器名", "水蒸气性质" in text)
    check("DOCX 正文含输入参数", "介质" in text)
except ImportError as e:                                    # pragma: no cover
    check(f"python-docx 可用（{e}）", False, "缺少 python-docx")

# ══════════════════════════════════════════════════════════════════
section("F. 统计视图：主题可读性与切换")

seed()
hist.refresh()
reset_filters(hist)
tm = ThemeManager()
tm.set_theme("light")

#: 各主题的原始调色板 —— get_content_colors() 只返回"当前主题"的扁平表，
#: 要对比两套主题得从 ThemeManager.CONTENT_COLORS 取。
LIGHT_MUTED = ThemeManager.CONTENT_COLORS["light"]["muted"]

hist._show_statistics()
check("统计模式已切换", hist._right_mode == "statistics")
check("标题改为「使用统计」", hist.detail_title.text() == "使用统计")
check("按钮变为「返回详情」", hist.stats_btn.text() == "返回详情")

stats = db.get_statistics()
html_light = hist._format_statistics(stats)
check("统计 HTML 不含亮色专用色",
      not (hex_colors(html_light) & LIGHT_ONLY_COLORS),
      hex_colors(html_light) & LIGHT_ONLY_COLORS)
check("统计 HTML 使用主题色",
      get_content_colors()["banner_bg"].lower() in html_light.lower())
check("统计 HTML 含全部计算器名",
      all(name in html_light for _c, name, _ca, _t, _n in SAMPLES))
check("统计 HTML 含分类名", all(cat in html_light for cat in
                            {s[2] for s in SAMPLES}))
check("统计 HTML 含百分号", "%" in html_light)
check("统计 HTML 含记录总数", f">{len(SAMPLES)}<" in html_light)

tm.set_theme("dark")
html_dark = hist._format_statistics(stats)
check("深色下统计 HTML 改用深色配色",
      get_content_colors()["muted"].lower() in html_dark.lower())
check("深色下不含亮色主题的次要文字色",
      LIGHT_MUTED.lower() not in html_dark.lower())
ratio = contrast(get_content_colors()["muted"], "#2d2d2d")
check(f"深色下次要文字对比度 {ratio:.2f}:1 ≥ 4.0", ratio >= 4.0)

hist.on_theme_changed()
check("深色下 on_theme_changed 重渲染统计",
      hist._right_mode == "statistics"
      and get_content_colors()["muted"].lower() in hist.detail_text.toHtml().lower())

# 空结果统计
hist.search_edit.setText("不存在的东西")
empty_stats = db.get_statistics(keyword="不存在的东西")
html_empty = hist._format_statistics(empty_stats)
check("空结果统计 HTML 不崩且提示无记录",
      "没有记录" in html_empty and "Traceback" not in html_empty)
check("空结果统计 HTML 无亮色专用色",
      not (hex_colors(html_empty) & LIGHT_ONLY_COLORS))
hist.search_edit.setText("")

tm.set_theme("light")
hist._toggle_statistics()
check("再点统计按钮切回详情", hist._right_mode == "detail")
check("切回详情后标题复位", hist.detail_title.text() == "记录详情")

hist._current_record = db.get_all_records(limit=1)[0]
hist._show_statistics()
hist.on_theme_changed()
check("统计模式下重渲染不抛异常", hist.detail_text.toPlainText() != "")

# 详情仍走主题（回归：不能因为这次改造又写死颜色）
detail_html = hist._format_detail(hist._current_record)
check("详情 HTML 仍不含亮色专用色",
      not (hex_colors(detail_html) & LIGHT_ONLY_COLORS),
      hex_colors(detail_html) & LIGHT_ONLY_COLORS)

XSS_REC = {
    "calculator_name": "<script>x</script>", "calculator_category": "",
    "created_at": "2026-09-15T10:00:00", "inputs": {}, "outputs": {},
    "notes": "<b>加粗</b>",
}
xss_html = hist._format_detail(XSS_REC)
check("详情 HTML 转义尖括号（记录内容破坏不了结构）",
      "&lt;script&gt;" in xss_html and "<script>" not in xss_html)
check("备注里的 HTML 标签也被转义",
      "&lt;b&gt;" in xss_html and "<b>加粗</b>" not in xss_html)

stats_xss = hist._format_statistics({
    "total": 1, "first_at": None, "last_at": None, "active_days": 1,
    "category_count": 1, "calculator_count": 1,
    "by_category": [("<img src=x>", 1)], "by_calculator": [("<i>", 1)],
    "other_count": 0, "by_day": [("2026-09-15", 1)], "by_month": [],
})
check("统计 HTML 转义分类名/计算器名",
      "&lt;img src=x&gt;" in stats_xss and "<img src=x>" not in stats_xss)

# ══════════════════════════════════════════════════════════════════
shutil.rmtree(TMPDIR, ignore_errors=True)

print()
print("=" * 60)
print(f"总结: {PASS} 过, {FAIL} 失败")
print("=" * 60)
sys.exit(1 if FAIL else 0)
