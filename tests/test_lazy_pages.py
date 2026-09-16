# -*- coding: utf-8 -*-
"""页面惰性加载回归测试（2026-09-16）

**为什么有这个文件**：45 个计算器 + 21 个换算页原先在启动时**全部实例化**，
全窗口 5293 个控件。Qt 每次 `setStyleSheet` 都要给每个控件重算样式，实测：
    启动 7.14s、切主题 5.5s（见 .workbuddy/_perf_theme.py 的实测输出）
改成"登记导航 + 占位页，首次打开才建真页面"后：启动 0.41s、切主题 0.84s。

固化五类不变式（防止有人"顺手改回全量实例化"或让索引错位）：
  A. 惰性契约 —— 构造后只有首行是真页面，其余是带 `_lazy_spec` 的占位页
  B. 索引对齐 —— nav 行号 == pages 索引 == content_stack 索引（搜索过滤不能破坏）
  C. 元数据完整 —— 占位页也带 `_calc_meta`（右键隐藏 / 管理面板靠它）
  D. 按需与缓存 —— 打开即实例化、二次打开不重建、堆栈里换的正是那个控件
  E. 规模闸门 —— 常驻控件数上限 + 切主题耗时上限（两者互为因果）

运行：
    QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe tests/test_lazy_pages.py
"""
import os
import sys
import tempfile
import time

PROJ = r"C:\Users\Administrator\Desktop\ChemCal"
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject                              # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget             # noqa: E402

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


app = QApplication.instance() or QApplication([])
TMPDIR = tempfile.mkdtemp(prefix="chemcal_lazy_")

# ── 把历史库指到临时文件，别碰用户真实库 ──
from modules.history_db import HistoryDB                        # noqa: E402

_db = HistoryDB()
_db.db_path = os.path.join(TMPDIR, "lazy.db")
_db._init_db()


class FakeDataManager(QObject):
    """只提供显隐/排序配置读写，不落盘。"""

    def __init__(self):
        super().__init__()
        self.settings = {}

    def get_settings(self):
        return dict(self.settings)

    def update_settings(self, s):
        self.settings = dict(s)
        return True


def is_placeholder(page):
    return hasattr(page, "_lazy_spec")


# ══════════════════════════════ A. 工程计算容器 ══════════════════════════════
section("A. 工程计算：惰性加载契约")

from modules.chemical_calculations.chemical_calculations_widget import (  # noqa: E402
    ChemicalCalculationsWidget)

cc = ChemicalCalculationsWidget(None, FakeDataManager())
app.processEvents()

NAV = cc.nav_list.count()
check("导航项数 == 页面数", NAV == len(cc.pages), f"nav={NAV} pages={len(cc.pages)}")
check("导航项数 == 内容堆栈页数",
      NAV == cc.content_stack.count(), cc.content_stack.count())
check("导航项数为 45（45 个计算器）", NAV == 45, NAV)

built = [i for i, p in enumerate(cc.pages) if not is_placeholder(p)]
check("构造后只有 1 个真页面（首行）", built == [0], built)
check("其余 44 页都是占位页", sum(1 for p in cc.pages if is_placeholder(p)) == 44)
check("占位页也带 _calc_meta（右键隐藏/管理面板依赖它）",
      all(getattr(p, "_calc_meta", None) for p in cc.pages))
check("占位页元数据键齐全（id/name/category）",
      all({"id", "name", "category"} <= set(p._calc_meta) for p in cc.pages))
check("首行默认已实例化且已显示",
      cc.content_stack.currentIndex() == 0 and not is_placeholder(cc.pages[0]))

cc_widgets = len(cc.findChildren(QWidget))
check("工程计算常驻控件数 < 800（全量实例化时为 4274）",
      cc_widgets < 800, cc_widgets)

# ── B. 索引对齐 ──
section("B. 索引对齐（搜索过滤不得破坏行号）")

cc.nav_search.setText("泵")
app.processEvents()
hidden_rows = [i for i in range(NAV) if cc.nav_list.item(i).isHidden()]
check("搜索只是隐藏行，不删除行（行号不变）",
      cc.nav_list.count() == NAV and len(hidden_rows) > 0, hidden_rows)
check("过滤后 pages 索引仍与行号一一对应", len(cc.pages) == NAV)
cc.nav_search.setText("")
app.processEvents()
check("清空搜索后全部行恢复显示",
      not any(cc.nav_list.item(i).isHidden() for i in range(NAV)))

# ── C. 按需实例化 + 缓存 ──
section("C. 按需实例化、切回不重建")

TARGET = 20
title20 = cc.nav_list.item(TARGET).text()
t0 = time.perf_counter()
cc.nav_list.setCurrentRow(TARGET)
app.processEvents()
cost = time.perf_counter() - t0

page20 = cc.pages[TARGET]
check(f"切到第 {TARGET} 行后该页已实例化", not is_placeholder(page20), title20)
check("content_stack 当前索引跟随", cc.content_stack.currentIndex() == TARGET)
check("堆栈里的控件就是 pages 里那个（未错位）",
      cc.content_stack.widget(TARGET) is page20)
check("实例化后控件数 > 20（是真页面不是空壳）",
      len(page20.findChildren(QWidget)) > 20,
      len(page20.findChildren(QWidget)))
check("页面拿到了 _calc_meta", bool(getattr(page20, "_calc_meta", None)),
      getattr(page20, "_calc_meta", None))
check(f"按需实例化耗时 < 1s（实测 {cost*1000:.0f} ms）", cost < 1.0, cost)

cc.nav_list.setCurrentRow(2)
app.processEvents()
check("切走后第 2 行也按需实例化", not is_placeholder(cc.pages[2]))
cc.nav_list.setCurrentRow(TARGET)
app.processEvents()
check("二次打开同一行不重建（对象同一）", cc.pages[TARGET] is page20)

# ── D. 公开 API ──
section("D. 公开 API：open_calculator")

p = cc.open_calculator("safety_valve_calculator")
check("按模块 id 打开计算器并实例化", p is not None and not is_placeholder(p))
check("返回的页面 id 正确",
      getattr(p, "_calc_meta", {}).get("id") == "safety_valve_calculator")
check("未知 id 返回 None", cc.open_calculator("no_such_calculator") is None)

# ── E. 全量打开（模拟用户逐个点完）──
section("E. 逐个打开全部计算器")

err = ""
for i in range(NAV):
    try:
        cc.nav_list.setCurrentRow(i)
        app.processEvents()
    except Exception as e:                                       # noqa: BLE001
        err = f"第 {i} 行: {e}"
        break
check("45 页逐个打开无异常", err == "", err)
check("全部页面都已是真页面",
      all(not is_placeholder(p) for p in cc.pages))
check("每页都自带 _calc_meta",
      all(getattr(p, "_calc_meta", None) for p in cc.pages))
launched_widgets = len(cc.findChildren(QWidget))
check(f"全量打开后控件数 {launched_widgets}（相当于改造前常驻量，属预期）",
      launched_widgets > 3000, launched_widgets)

# ══════════════════════════════ F. 换算器容器 ══════════════════════════════
section("F. 换算器：惰性加载 + ensure_all_pages")

from modules.converter.converter_widget import ConverterWidget   # noqa: E402

conv = ConverterWidget()
app.processEvents()
check("导航项数 == 页面数 == 21",
      conv.nav_list.count() == len(conv.pages) == 21)
check("构造后只有 1 个真页面",
      sum(1 for p in conv.pages if not hasattr(p, "_lazy_spec")) == 1)

conv.ensure_all_pages()
check("ensure_all_pages() 后 21 页全部实例化",
      all(not hasattr(p, "_lazy_spec") for p in conv.pages))

from modules.converter import converter_widget                    # noqa: E402
from modules.converter.calculators.unit_converter_base import UnitConverterPage  # noqa: E402

#: 2026-09-15 扩充的 10 个（继承通用基类）；原生 11 个是各自独立实现的老页面。
#: 注意不能用 pages[-10:] 取——扩充的 10 个里"流量换算"在基础量段（第 5 个），
#: 按位置切片会把原生的 ForceConverter 混进来（实测踩到）。
NEW_CLASSES = ["FlowConverter", "DensityConverter", "DynamicViscosityConverter",
               "KinematicViscosityConverter", "SurfaceTensionConverter",
               "ThermalConductivityConverter", "HeatTransferCoefficientConverter",
               "SpecificHeatConverter", "CalorificValueConverter",
               "ConcentrationConverter"]
_row_of_class = {c: i for i, (_m, c, _t) in
                 enumerate(converter_widget.CALCULATOR_MODULES)}
check("扩充的 10 个换算页都是 UnitConverterPage 子类",
      all(issubclass(type(conv.pages[_row_of_class[c]]), UnitConverterPage)
          for c in NEW_CLASSES),
      [c for c in NEW_CLASSES
       if not issubclass(type(conv.pages[_row_of_class[c]]), UnitConverterPage)])
conv.open_converter("长度换算")
check("open_converter 能按标题定位", conv.nav_list.currentRow() == 0)

# ══════════════════════════════ G. 规模闸门 ══════════════════════════════
section("G. 规模闸门：常驻控件数与切主题耗时")

from theme_manager import ThemeManager                           # noqa: E402
from PySide6.QtCore import QEvent                                # noqa: E402
from PySide6.QtWidgets import QVBoxLayout                        # noqa: E402

# 关键：前面的 cc / conv 已被全量展开（4360+ 控件）且仍然存活，
# 而 setStyleSheet 会作用到**所有顶层 widget** —— 不先销毁它们，
# 这里测到的就不是"惰性加载后的代价"，而是"全量展开后的代价"（实测差 4 倍）。
for _w in (cc, conv):
    _w.setParent(None)
    _w.close()
    _w.deleteLater()
QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
app.processEvents()
leftover = len(QApplication.allWidgets())
check(f"销毁旧容器后残留控件已释放（{leftover} 个）", leftover < 800, leftover)

tm = ThemeManager()
cc2 = ChemicalCalculationsWidget(None, FakeDataManager())
conv2 = ConverterWidget()
holder = QWidget()
lay = QVBoxLayout(holder)
lay.addWidget(cc2)
lay.addWidget(conv2)
holder.resize(1200, 700)
holder.show()
app.processEvents()

total = len(holder.findChildren(QWidget))
check(f"两页常驻控件总数 {total} < 900（改造前 5293）", total < 900, total)

tm.set_theme("dark")
app.setStyleSheet(tm.get_theme())
app.processEvents()
tm.set_theme("light")
t0 = time.perf_counter()
app.setStyleSheet(tm.get_theme())
app.processEvents()
cost = time.perf_counter() - t0
check(f"切主题耗时 {cost*1000:.0f} ms < 3000 ms（改造前 5500 ms）", cost < 3.0, cost)

holder.close()

print(f"\n总结: {PASS} 过, {FAIL} 失败")
sys.exit(1 if FAIL else 0)
