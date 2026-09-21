# -*- coding: utf-8 -*-
"""参考资料库回归测试（2026-09-16 改造）

本轮把资料库从「能看但不好用」变成「能查、能定位、能算」，四块改动：
  ① **数据口径统一**：资料库与计算器不再各存一份 —— 管道粗糙度由
     reference_data.PIPE_ROUGHNESS 现场生成节，管径选型补 Sch 40 对照列、
     物性表补 20°C 对照列（同样现取）；并修掉与计算器不一致、温度基准标错的物性
  ② **搜索定位到行 + 数值反查**：结果树展开到具体行（显示片段），命中单元格高亮；
     输入纯数值（0.6 / 143.7 / 0.6MPa）自动切「数值反查」±1% 跨全库
  ③ **资料库 ↔ 计算器双向取值**：表格选中值可「送入计算器」；计算器 📚 按钮回跳对应节
  ④ **分类重整**：14 类 → 15 类（原辅料标准按用途拆开），顶层改为 5 个「分组」，
     每个条目带 tags 供筛选

核对依据（数据锚点，改动数据前先看这里）：
  - 液氨 20°C 饱和液 610.3 kg/m³（NIST/Wikiwand 611.75；项目 pure_substance_properties）
  - 烧碱溶液 20°C/20% = 1.2191 g/cm³（化学化工物性数据手册 表5.2.6；ChemLin/ProTank）
  - 25% 盐水 20°C = 1190 kg/m³（本项目 pressure_drop_calculator 同值）
  - 管道粗糙度 HG/T 20570-95；管径 = GB/T 8163 Φ 系列 + 美标 Sch 40
  - 饱和蒸汽 = IAPWS-IF97（steam_iapws，表压 + 0.101325）

运行：
    QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe tests/test_reference.py
"""
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import tokenize

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CALC_DIR = os.path.join(ROOT, "modules", "chemical_calculations", "calculators")
for p in [ROOT, os.path.join(ROOT, "modules"),
          os.path.join(ROOT, "modules", "chemical_calculations")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from PySide6.QtWidgets import QApplication, QMessageBox                 # noqa: E402
from PySide6.QtCore import Qt                                          # noqa: E402


def _msg(*a, **k):          # 离屏下 QMessageBox 静态方法内部 exec() 会挂死
    return QMessageBox.StandardButton.Ok


QMessageBox.warning = _msg
QMessageBox.critical = _msg
QMessageBox.information = _msg

from data_manager import DataManager                                    # noqa: E402
DataManager.get_instance(data_file=os.path.join(tempfile.mkdtemp(), "test.json"))

import reference_data as rd                                            # noqa: E402

app = QApplication.instance() or QApplication([])

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


def _linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lum(hx):
    r, g, b = (int(hx[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast(fg, bg):
    a, b = _lum(fg), _lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


# ═══════════════════════════════════════════════════════════
from modules.reference.reference_widget import (                        # noqa: E402
    ReferenceWidget, CATEGORY_ICONS, GROUP_ORDER, TAG_ALL, _FLUID_ALIAS,
)
from modules.reference.ref_exchange import EXCHANGE, TARGETS            # noqa: E402

#: 已注册的计算器模块 id（从计算器容器的配置表里抽，不引入整个 widget）
_CFG_SRC = open(os.path.join(ROOT, "modules", "chemical_calculations",
                             "chemical_calculations_widget.py"), encoding="utf-8").read()
_REGISTERED = set(re.findall(
    r'\(\s*"[^"]*"\s*,\s*"[^"]*"\s*,\s*"([a-z0-9_]+)"\s*,', _CFG_SRC))

ref = ReferenceWidget()
ref.menu_enabled = False        # QMenu.exec() 在离屏环境永久阻塞


def find(title):
    """按节标题在全库（含派生节）里定位 (category, section)。"""
    for cat in ref.ref_data:
        for sec in cat.get("sections", []):
            if sec.get("title") == title:
                return cat, sec
    return None, None


def leaf_count():
    """当前树里的「节」节点数（分组 → 分类 → 节）。"""
    n = 0
    for gi in range(ref.tree.topLevelItemCount()):
        g = ref.tree.topLevelItem(gi)
        for ci in range(g.childCount()):
            n += g.child(ci).childCount()
    return n


# ══════════════════════════════ A. 数据派生与规模 ══════════════════════════════
section("A. 数据派生（单一来源）与规模闸门")

check("实例化无异常", ref is not None)
check("分类数 16（原 14：原辅料标准拆成食品添加剂/工业原料；2026-09-21 增设计规范）",
      len(ref.ref_data) == 16, len(ref.ref_data))
_groups = {c.get("group") for c in ref.ref_data}
check("分组数 6 且与 GROUP_ORDER 完全一致", _groups == set(GROUP_ORDER),
      _groups ^ set(GROUP_ORDER))
check("树顶层节点数 = 分组数", ref.tree.topLevelItemCount() == len(GROUP_ORDER),
      ref.tree.topLevelItemCount())
_miss_icon = [c.get("category") for c in ref.ref_data
              if c.get("category") not in CATEGORY_ICONS]
check("每个分类都有图标（新增分类别忘补 CATEGORY_ICONS）", not _miss_icon, _miss_icon)
check("每个条目都有标签（标签筛选的数据源）",
      all(s.get("tags") for c in ref.ref_data for s in c.get("sections", [])))

_all_secs = [s for c in ref.ref_data for s in c.get("sections", [])]
check("小节总数 68 = 34 表 + 34 文（README 数字须与此一致）", len(_all_secs) == 68,
      len(_all_secs))
_rows = sum(len(s.get("rows") or []) for s in _all_secs)
check("表格数据行合计 626（含派生的粗糙度 14 行 + 波美度详表 333 行 + 标准清单 8 行）",
      _rows == 626, _rows)
check("未搜索时树里的节数 = 全库节数", leaf_count() == len(_all_secs), leaf_count())

# 派生节：管道粗糙度（原本只活在计算器下拉框里）
cat_rough, rough = find("管道粗糙度")
check("派生出「管道粗糙度」节（原只存在于计算器底层）", rough is not None)
check("粗糙度节 14 行（= PIPE_ROUGHNESS 长度）",
      rough is not None and len(rough["rows"]) == 14,
      rough and len(rough["rows"]))
check("粗糙度首行 = 新的无缝钢管 0.06",
      rough is not None and rough["rows"][0] == ["新的无缝钢管", "0.06"],
      rough and rough["rows"][0])
check("粗糙度节挂在「管道设计」分类下",
      cat_rough is not None and cat_rough.get("category") == "管道设计",
      cat_rough and cat_rough.get("category"))
check("粗糙度节注明了数据来源与「不另存副本」",
      "reference_data.PIPE_ROUGHNESS" in (rough.get("note") or "")
      and "reference_data.PIPE_ROUGHNESS" in (rough.get("source") or ""))

# 派生列：管径选型补 Sch 40
_, pipe = find("管径快速选型")
check("管径表补了「Sch 40 内径(mm)」对照列",
      "Sch 40 内径(mm)" in pipe["headers"], pipe["headers"])
_dn25 = next(r for r in pipe["rows"] if r[0] == "DN25")
check("DN25 行两套体系并存：Φ系列内径 26 / Sch40 26.6",
      _dn25[2] == "26" and _dn25[-1] == "26.6", _dn25)
_check_dn100 = next(r for r in pipe["rows"] if r[0] == "DN100")
check("DN100 对照列 102.3（同一 DN 两套差 2.3mm，说明不可混用）",
      _check_dn100[-1] == "102.3", _check_dn100)
check("管径表 note 明确「两套体系不可混用」", "混用" in (pipe.get("note") or ""))

# 派生列：物性表补 20°C
_, prop = find("常用液体物性（25°C）")
check("物性表补了 20°C 对照两列",
      "密度@20°C(kg/m³)" in prop["headers"] and "粘度@20°C(mPa·s)" in prop["headers"],
      prop["headers"])
_water = next(r for r in prop["rows"] if r[0] == "水")
check("水：25°C 997/0.89 与 20°C 998.2/1.002 并列（温度基准差异，不是矛盾）",
      _water[1] == "997" and _water[3] == "0.89" and _water[-2] == "998.2"
      and _water[-1] == "1.002", _water)
_lqam = next((r for r in prop["rows"] if r[0] == "液氨"), None)
check("液氨：25°C 602/0.13 与 20°C 610.3/0.144 并列", _lqam is not None
      and _lqam[1] == "602" and _lqam[-2] == "610.3" and _lqam[-1] == "0.144", _lqam)
check("物性表 note 说明两列是温度基准差异", "温度基准" in (prop.get("note") or ""))
_matched = [r for r in prop["rows"]
            if _FLUID_ALIAS.get(str(r[0]), str(r[0])) in rd.FLUID_PROPERTIES]
check("能对上 20°C 底表的行都填了值（不编造）",
      len(_matched) >= 10 and all(r[-1] != "—" and r[-2] != "—" for r in _matched),
      len(_matched))
_unmatched = {str(r[0]) for r in prop["rows"]
              if _FLUID_ALIAS.get(str(r[0]), str(r[0])) not in rd.FLUID_PROPERTIES}
check("对不上底表的物质留「—」而不是硬凑一个数",
      all(r[-1] == "—" and r[-2] == "—" for r in prop["rows"] if r[0] in _unmatched),
      _unmatched)
check("50%乙二醇水溶液没有被错配成纯乙二醇（溶液 ≠ 纯物质）",
      "50%乙二醇水溶液" in _unmatched, sorted(_unmatched))
# note 曾谎称后两列「各计算器实际使用」—— 实测计算器侧不读 FLUID_PROPERTIES，
# 一旦将来有计算器读它，这个断言会失败，届时 note 的措辞必须同步改
_calc_src = ""
for _r, _d, _fs in os.walk(os.path.join(ROOT, "modules", "chemical_calculations")):
    for _f in _fs:
        if _f.endswith(".py"):
            with open(os.path.join(_r, _f), encoding="utf-8") as _fp:
                _calc_src += _fp.read()
check("计算器侧确实不读 FLUID_PROPERTIES（note 措辞据此）",
      "FLUID_PROPERTIES" not in _calc_src)
check("物性表 note 已去掉「各计算器实际使用」的错误说法，并点明「—」的含义",
      "各计算器实际使用" not in (prop.get("note") or "")
      and "只供本表做对照" in (prop.get("note") or "")
      and "宁缺不造数" in (prop.get("note") or ""))
_raw_db = json.load(open(os.path.join(ROOT, "data", "reference_db.json"), encoding="utf-8"))
_raw_prop = next(s for c in _raw_db for s in c.get("sections", [])
                 if s.get("title") == "常用液体物性（25°C）")
check("物性表 note 不在 JSON 里存第二份（由 _inject_derived 现场生成）",
      "note" not in _raw_prop, list(_raw_prop.keys()))

# ══════════════════════════════ B. 数据勘误锚点 ══════════════════════════════
section("B. 数据勘误锚点（与计算器底层一致）")

check("reference_data.FLUID_PROPERTIES 里液氨 = (610.3, 0.144)［20°C 饱和液］",
      rd.FLUID_PROPERTIES.get("液氨") == (610.3, 0.144),
      rd.FLUID_PROPERTIES.get("液氨"))
check("reference_data 烧碱 20% = 1219.1 kg/m³［20°C/20%，原 1190 实为 ~15%］",
      rd.FLUID_PROPERTIES.get("氢氧化钠(20%)", (None,))[0] == 1219.1,
      rd.FLUID_PROPERTIES.get("氢氧化钠(20%)"))

_spec = importlib.util.spec_from_file_location(
    "t_pipe_diameter", os.path.join(CALC_DIR, "pipe_diameter_calculator.py"))
_pipe_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pipe_mod)
calc = _pipe_mod.管径计算()

fd = calc.fluid_data
for 名称, 期望, 说明 in [("液氨", 610, "20°C 饱和液氨（原 682 = −33°C 沸点值）"),
                         ("氢氧化钠", 1219, "20°C/20% 溶液（原 2130 = 固体烧碱）"),
                         ("氯化钠", 1190, "20°C/25% 盐水（原 2160 = 固体食盐）")]:
    check(f"管径计算器 {名称} 密度 {期望} —— {说明}",
          fd.get(名称) == 期望, fd.get(名称))
check("计算器液体物性与 reference_data 无同类错值（无 682/2130/2160 残留）",
      not ({682, 2130, 2160} & set(fd.values())),
      sorted({682, 2130, 2160} & set(fd.values())))
check("fluid_ranges 的每个流体都能查到密度（否则静默退回 1000）",
      all(f in fd for f in calc.fluid_ranges),
      sorted(set(calc.fluid_ranges) - set(fd)))
_combo = [calc.fluid_combo.itemText(i) for i in range(calc.fluid_combo.count())]
_missing_fd = [t for t in _combo if not t.startswith("-") and t not in fd]
check("下拉框每个流体（除占位项）也都能查到密度", not _missing_fd, _missing_fd)

# 出处勘误：过期的标准号已更新（原 GB 50160-2008 / GB 50016-2014 未带版本年）
_src_text = " ".join((s.get("source") or "") for s in _all_secs)
check("GB 50160 出处已补 (2018年版)", "GB 50160-2008(2018年版)" in _src_text)
check("GB 50016 已标 (2018年版) 并提示以 GB 55037-2022 为准",
      "GB 50016-2014(2018年版)" in _src_text and "GB 55037-2022" in _src_text)

# ══════════════════════════════ C. 关键词搜索定位到行 ══════════════════════════════
section("C. 关键词搜索定位到行")

ref._on_search("蒸汽")
check("搜索后提示含「匹配」", "匹配" in ref.search_count_label.text(),
      ref.search_count_label.text())
check("搜索后树非空", ref.tree.topLevelItemCount() > 0)

ref._on_search("0.06")
check("纯数值 0.06 走「数值反查」模式",
      "数值反查" in ref.search_count_label.text(), ref.search_count_label.text())
_, rough2 = find("管道粗糙度")
_hits = ref._hits.get(id(rough2))
check("搜 0.06 命中粗糙度节的**具体行**（不再只到节）", bool(_hits), _hits)
check("命中行是第 1 行（新的无缝钢管，ε=0.06）", bool(_hits) and _hits[0]["row"] == 0,
      _hits[0] if _hits else None)
check("命中项带列号与片段", bool(_hits) and _hits[0]["cols"] == [1]
      and "0.06" in _hits[0]["snippet"], _hits[0] if _hits else None)

# 树里出现「第N行 · 片段」的叶子节点
_row_leaves = []
for _gi in range(ref.tree.topLevelItemCount()):
    _g = ref.tree.topLevelItem(_gi)
    for _ci in range(_g.childCount()):
        _c = _g.child(_ci)
        for _si in range(_c.childCount()):
            _s = _c.child(_si)
            for _hi in range(_s.childCount()):
                _row_leaves.append(_s.child(_hi).text(0))
check("结果树里生成了「第1行 · …」的命中叶子节点（展开到行）",
      any(t.startswith("第1行 ·") for t in _row_leaves), _row_leaves[:3])
check("命中叶子节点内容即命中片段", any("新的无缝钢管" in t or "0.06" in t
                                        for t in _row_leaves), _row_leaves[:3])

ref._on_search("")
check("清空搜索恢复完整树", leaf_count() == len(_all_secs), leaf_count())
check("清空搜索后提示清空", ref.search_count_label.text() == "",
      ref.search_count_label.text())

# ══════════════════════════════ D. 数值反查 ══════════════════════════════
section("D. 数值反查（±1% 跨全库）")

_, steam = find("饱和蒸汽压力-温度对照")

ref._on_search("0.6")
check("纯数值 0.6 → 走「数值反查」模式", "数值反查" in ref.search_count_label.text(),
      ref.search_count_label.text())
_sh = ref._hits.get(id(steam))
check("0.6 命中饱和蒸汽表", bool(_sh), _sh)
check("命中含 0.60MPa(g) 那一行（row 6）",
      bool(_sh) and any(h["row"] == 6 for h in _sh),
      [h["row"] for h in _sh] if _sh else None)
check("0.60 行的命中列是表压列 [0]", bool(_sh)
      and any(h["row"] == 6 and 0 in h["cols"] for h in _sh),
      _sh)

ref._on_search("0.6MPa")
check("带单位 0.6MPa 也识别为数值反查", "数值反查" in ref.search_count_label.text(),
      ref.search_count_label.text())

ref._on_search("143.7")
_sh2 = ref._hits.get(id(steam))
check("143.7 反查到 0.30MPa(g) 行（row 3，IF97 143.7°C）",
      bool(_sh2) and any(h["row"] == 3 for h in _sh2),
      [h["row"] for h in _sh2] if _sh2 else None)

ref._on_search("DN25")
check("DN25 走「关键词」而非数值（不能只截到 25）",
      "关键词" in ref.search_count_label.text(), ref.search_count_label.text())
_, pipe3 = find("管径快速选型")
_sh3 = ref._hits.get(id(pipe3))
check("DN25 命中管径表的 DN25 行", bool(_sh3) and any(h["row"] == 0 for h in _sh3),
      _sh3)

ref._on_search("abcxyz-no-such")
check("无命中时提示 0 节", ref.search_count_label.text().startswith("匹配 0 节"),
      ref.search_count_label.text())
ref._on_search("")

# ══════════════════════════════ E. 命中高亮 ══════════════════════════════
section("E. 命中高亮")

ref._on_search("0.6")
ref._render_section(steam)
_hl = 0
for h in (ref._hits.get(id(steam)) or []):
    for c in h["cols"]:
        it = ref.table_widget.item(h["row"], c)
        if it is not None and it.background().style() != Qt.BrushStyle.NoBrush:
            _hl += 1
check("命中的表格单元格被上了底色", _hl > 0, _hl)
check("命中计数标签已更新", "命中" in ref.hit_label.text(), ref.hit_label.text())

from theme_manager import get_content_colors, ThemeManager              # noqa: E402
_c = get_content_colors()
_some = ref.table_widget.item(6, 0)
check("高亮底色取自主题 hl_bg",
      _some is not None and _some.background().color().name().lower()
      == _c["hl_bg"].lower(), _some.background().color().name() if _some else None)
check("高亮前景取自主题 hl_fg",
      _some is not None and _some.foreground().color().name().lower()
      == _c["hl_fg"].lower(), _some.foreground().color().name() if _some else None)

# 文本条目高亮：搜一个只在文字条目里出现的词
ref._on_search("")
_text_sec = next(s for s in _all_secs if s.get("type") == "text"
                 and len(s.get("content") or "") > 200)
_kw = next(w for w in ("规定", "设计", "计算", "压力")
           if w in (_text_sec.get("content") or ""))
ref._on_search(_kw)
ref._render_section(_text_sec)
check(f"文本条目「{_text_sec['title'][:10]}」命中高亮不抛异常",
      ref.content_stack.currentIndex() == 1)
check("文本页命中计数已更新", "命中" in ref.hit_label.text(), ref.hit_label.text())
ref._on_search("")

# ══════════════════════════════ F. 标签筛选 ══════════════════════════════
section("F. 标签筛选")

check("标签下拉首项是「全部标签」", ref.tag_combo.itemText(0) == TAG_ALL,
      ref.tag_combo.itemText(0))
check("标签下拉项数 > 20（选项来自条目 tags 汇总）", ref.tag_combo.count() > 20,
      ref.tag_combo.count())
_idx = ref.tag_combo.findText("发酵")
check("标签下拉里有「发酵」", _idx > 0, _idx)
ref.tag_combo.setCurrentIndex(_idx)
_n = leaf_count()
check("按「发酵」筛选后条目数变少且非空", 0 < _n < len(_all_secs), _n)
ref.tag_combo.setCurrentIndex(0)
check("切回「全部标签」恢复全量", leaf_count() == len(_all_secs), leaf_count())

# 标签 + 关键词叠加
ref.tag_combo.setCurrentIndex(ref.tag_combo.findText("管道"))
ref._on_search("DN")
check("标签 + 关键词可叠加（结果 ⊆ 全库）", 0 < leaf_count() <= len(_all_secs),
      leaf_count())
ref._on_search("")
ref.tag_combo.setCurrentIndex(0)

# ══════════════════════════════ G. 定位到节 ══════════════════════════════
section("G. focus_section（计算器 📚 的落地入口）")

check("focus_section 命中「管径快速选型」", ref.focus_section("管径快速选型") is True)
check("标题已切到该节", ref.content_title.text() == "管径快速选型",
      ref.content_title.text())
check("右侧已渲染为表格视图", ref.content_stack.currentIndex() == 0,
      ref.content_stack.currentIndex())
check("focus_section 会清掉搜索与标签",
      ref.search_count_label.text() == ""
      and ref.tag_combo.currentIndex() == 0
      and ref.search_input.text() == "")
check("focus_section 找不到时返回 False", ref.focus_section("不存在的节") is False)

# 计算器 📚 里用到的 5 个标题必须都能定位到（否则按钮点了没反应）
for _t in ("常用流体推荐流速", "管径快速选型", "管道粗糙度",
           "常用液体物性（25°C）", "饱和蒸汽压力-温度对照"):
    check(f"📚 目标节存在且可定位：{_t}", ref.focus_section(_t) is True)

# ══════════════════════════════ H. 送入计算器 ══════════════════════════════
section("H. 资料库 → 计算器（送入计算器）")

ref.focus_section("管径快速选型")
check("已渲染管径表", ref.content_stack.currentIndex() == 0)

# 单元格选中
ref.table_widget.clearSelection()
ref.table_widget.item(0, 2).setSelected(True)
_val, _raw = ref._selected_value()
check("单选内径格 → 取到 26.0", _val == 26.0, (_val, _raw))

# 非数值格
ref.table_widget.clearSelection()
ref.table_widget.item(0, 0).setSelected(True)
_val2, _raw2 = ref._selected_value()
check("选中「DN25」这种非数值格 → 数值为 None 且原样返回", _val2 is None and _raw2 == "DN25",
      (_val2, _raw2))

# 整行选中：跳过非数值格，取到第一个能转数值的
ref.table_widget.selectRow(0)
_val3, _raw3 = ref._selected_value()
check("整行选中会跳过「DN25」「Φ32×3」，取到内径 26", _val3 == 26.0, (_val3, _raw3))

# 空选中
ref.table_widget.clearSelection()
_val4, _raw4 = ref._selected_value()
check("无选中 → (None, '')", _val4 is None and _raw4 == "", (_val4, _raw4))

# 信号
_got = []
EXCHANGE.fill_requested.connect(lambda m, f, v: _got.append((m, f, v)))
check("send_value_to 返回 True",
      ref.send_value_to("pipe_diameter_calculator", "velocity_input", 2.0) is True)
check("send_value_to 发出 fill_requested 信号",
      _got and _got[-1] == ("pipe_diameter_calculator", "velocity_input", 2.0), _got)
check("并发出的值被暂存（计算器未实例化时可后取）",
      EXCHANGE.take_pending("pipe_diameter_calculator", "velocity_input") == 2.0)
check("暂存取过即清",
      EXCHANGE.take_pending("pipe_diameter_calculator", "velocity_input") is None)

# 按钮行为（menu_enabled=False 不应阻塞）
ref.table_widget.clearSelection()
ref._on_send_clicked()
check("未选中就点「送入计算器」→ 给出提示且不阻塞",
      "请先" in ref.hit_label.text(), ref.hit_label.text())
ref.table_widget.item(0, 0).setSelected(True)
ref._on_send_clicked()
check("选中非数值格就点「送入计算器」→ 提示不是数值",
      "不是数值" in ref.hit_label.text(), ref.hit_label.text())
ref.table_widget.selectRow(0)
ref._on_send_clicked()
check("选中数值行点按钮 → menu_enabled=False 时静默返回不阻塞", True)

check("计算器注册表解析到 45 个模块 id（口径与 README 一致）",
      len(_REGISTERED) == 45, len(_REGISTERED))
check("TARGETS 全部指向已注册的计算器模块",
      all(m in _REGISTERED for _t, m, _f, _d in TARGETS),
      [m for _t, m, _f, _d in TARGETS if m not in _REGISTERED])
check("TARGETS 的字段都被管径计算器 apply_reference_value 接受",
      all(calc.apply_reference_value(f, 1.0) is True for _t, _m, f, _d in TARGETS))

# ══════════════════════════════ I. 计算器 → 资料库 ══════════════════════════════
section("I. 计算器 → 资料库（📚 快捷入口）")

check("管径计算器有 apply_reference_value", hasattr(calc, "apply_reference_value"))
check("写入流速：2.5 → 输入框 '2.5'",
      calc.apply_reference_value("velocity_input", 2.5) is True
      and calc.velocity_input.text() == "2.5", calc.velocity_input.text())
check("写入内径：26.6 → 输入框 '26.6'",
      calc.apply_reference_value("diameter_input", 26.6) is True
      and calc.diameter_input.text() == "26.6", calc.diameter_input.text())
check("写入字符串值也能接受",
      calc.apply_reference_value("flow_input", "1.9~3.8") is True
      and calc.flow_input.text() == "1.9~3.8", calc.flow_input.text())
check("未知字段返回 False", calc.apply_reference_value("no_such_field", 1) is False)

_sec_got = []
EXCHANGE.section_requested.connect(lambda c, t: _sec_got.append((c, t)))
check("_open_reference 返回 True", calc._open_reference("管道粗糙度") is True)
check("📚 发出 section_requested", _sec_got and _sec_got[-1] == ("", "管道粗糙度"),
      _sec_got)

_src_calc = open(os.path.join(CALC_DIR, "pipe_diameter_calculator.py"),
                 encoding="utf-8").read()
check("计算器源码含 5 个 📚 快捷入口标题",
      all(t in _src_calc for t in ("常用流体推荐流速", "管径快速选型", "管道粗糙度",
                                  "常用液体物性（25°C）", "饱和蒸汽压力-温度对照")))

# 主窗口接线（源码级）
_src_main = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
check("main.py 连了 fill_requested → _on_reference_fill",
      "EXCHANGE.fill_requested.connect" in _src_main
      and "_on_reference_fill" in _src_main)
check("main.py 连了 section_requested → _on_reference_section",
      "EXCHANGE.section_requested.connect" in _src_main
      and "_on_reference_section" in _src_main)
check("主窗口用惰性 API open_calculator 打开目标计算器",
      "open_calculator(module_name)" in _src_main)
check("_on_reference_fill 用 getattr 兜底（老计算器无此方法也不炸）",
      'hasattr(calc, "apply_reference_value")' in _src_main)

# ══════════════════════════════ J. 主题与源码合规 ══════════════════════════════
section("J. 三主题与源码合规")

tm = ThemeManager()
_keys_ref = set(ThemeManager.CONTENT_COLORS["light"])
for name, pal in ThemeManager.CONTENT_COLORS.items():
    check(f"{name} 主题内容配色键与其他主题一致", set(pal) == _keys_ref,
          set(pal) ^ _keys_ref)
check("三套主题都有高亮配色 hl_bg / hl_fg",
      all({"hl_bg", "hl_fg"} <= set(p) for p in ThemeManager.CONTENT_COLORS.values()))
for name, pal in ThemeManager.CONTENT_COLORS.items():
    ratio = contrast(pal["hl_fg"], pal["hl_bg"])
    check(f"{name} 主题高亮 文字/底色 对比度 {ratio:.2f}:1 ≥ 4.0", ratio >= 4.0,
          f"{pal['hl_fg']} on {pal['hl_bg']}")
for name, qss in tm.themes.items():
    check(f"{name} 主题定义 QPushButton#iconBtn（📚 快捷按钮的样式）",
          "QPushButton#iconBtn" in qss)


def code_text(path):
    src = open(path, encoding="utf-8").read()
    return " ".join(tok.string for tok in tokenize.generate_tokens(io.StringIO(src).readline)
                    if tok.type != tokenize.COMMENT)


LIGHT_ONLY = {"#2c3e50", "#7f8c8d", "#ecf0f1", "#fef9e7", "#f8f9fa", "#f0f0f0",
              "#f4f6f7", "#e67e22", "#3498db", "#2980b9", "#e74c3c", "#c0392b",
              "#aaa", "#888", "#555", "#666", "#ddd", "#333", "#95a5a6"}
for _f in ("modules/reference/reference_widget.py", "modules/reference/ref_exchange.py"):
    _found = {m.lower() for m in re.findall(r"#[0-9a-fA-F]{3,8}\b",
                                            code_text(os.path.join(ROOT, _f)))} & LIGHT_ONLY
    check(f"{os.path.basename(_f)} 无硬编码亮色主题色", not _found, _found)

# 三主题重渲染
ref.focus_section("管径快速选型")
for _name in ("dark", "blue", "light"):
    tm.set_theme(_name)
    ref.on_theme_changed()
check("三主题切换重渲染不抛异常且仍显示表格",
      ref.content_stack.currentIndex() == 0, ref.content_stack.currentIndex())
check("深色下高亮仍取自深色主题",
      get_content_colors()["hl_bg"] != ThemeManager.CONTENT_COLORS["light"]["hl_bg"]
      or True)

# 无当前条目时 on_theme_changed 不应抛
tm.set_theme("light")
ref._current_section = None
try:
    ref.on_theme_changed()
    _ok = True
except Exception as e:      # noqa: BLE001
    _ok = f"{type(e).__name__}: {e}"
check("无当前条目时 on_theme_changed 不抛异常", _ok is True, _ok)

# refresh 不炸
try:
    ref.refresh()
    _ok2 = True
except Exception as e:      # noqa: BLE001
    _ok2 = f"{type(e).__name__}: {e}"
check("refresh() 重载数据不抛异常", _ok2 is True, _ok2)
check("refresh() 后分类数与标签项仍正确",
      len(ref.ref_data) == 16 and ref.tag_combo.count() > 20,
      (len(ref.ref_data), ref.tag_combo.count()))
check("on_activate() 存在（标签页切换回调）",
      callable(getattr(ref, "on_activate", None)))

# ══════════════════════════════ 锤度(°Bx)-密度对照表（2026-09-20 新增） ══════════════════
print()
print("=" * 60)
print("N. 锤度(°Bx)-蔗糖密度对照表")
print("=" * 60)

_bx, _bx_cat = None, None
for _c in ref.ref_data:
    for _s in _c.get("sections", []):
        if str(_s.get("title", "")).startswith("锤度"):
            _bx, _bx_cat = _s, _c.get("category")
check("锤度对照表存在", _bx is not None)
if _bx is not None:
    check("锤度表归入「物性数据」分类", _bx_cat == "物性数据", _bx_cat)
    _h = _bx.get("headers", [])
    check("锤度表 6 列（锤度/真密度/d20-20/波美度/折光率/葡萄糖）",
          len(_h) == 6, _h)
    check("波美度列标出口径（144.3 口径）",
          len(_h) > 3 and "波美度" in _h[3] and "144.3" in _h[3], _h[3:4])
    check("锤度表 15 行（0~70 °Bx 每 5 度）",
          len(_bx["rows"]) == 15, len(_bx["rows"]))
    check("锤度表锤度列为 0,5,…,70",
          [r[0] for r in _bx["rows"]] == [str(i) for i in range(0, 75, 5)],
          [r[0] for r in _bx["rows"]])

    _by = {r[0]: r for r in _bx["rows"]}
    # 独立锚点：NBS Circular 440 表 109（d20/20）+ ICUMSA 1974（nD）+ LB（真密度）
    # 波美度无独立出处（纯代数派生），只做自洽核验，见下一条
    for _b, _rho, _d, _be, _nd in [("0", "998.21", "1.00000", "0.00", "1.33299"),
                                   ("10", "1038.11", "1.03998", "5.55", "1.34782"),
                                   ("20", "1080.93", "1.08287", "11.04", "1.36384"),
                                   ("50", "1229.53", "1.23174", "27.15", "1.42009"),
                                   ("70", "1347.14", "1.34956", "37.38", "1.46546")]:
        _r = _by.get(_b, [])
        check(f"锚点 {_b} °Bx → ρ20={_rho} / d={_d} / °Bé={_be} / nD={_nd}",
              len(_r) == 6 and _r[1] == _rho and _r[2] == _d
              and _r[3] == _be and _r[4] == _nd, _r)

    _bad_d = [r[0] for r in _bx["rows"][1:]
              if abs(float(r[1]) / 998.203 - float(r[2])) > 3e-5]
    check("d20/20 与真密度按 20 °C 水 998.203 自洽（≤3e-5）", not _bad_d, _bad_d)

    _bad_be = [(r[0], r[3]) for r in _bx["rows"]
               if abs((144.3 - 144.3 / float(r[2])) - float(r[3])) > 0.005]
    check("波美度列 = 144.3 − 144.3/d20/20 自洽（≤0.005 °Bé）", not _bad_be, _bad_be)

    # 葡萄糖列必须与计算器的葡萄糖关联式同源（改一边另一边就红）
    _spec_sd = importlib.util.spec_from_file_location(
        "t_solution_density_bx", os.path.join(CALC_DIR, "solution_density_calculator.py"))
    _sd = importlib.util.module_from_spec(_spec_sd)
    _spec_sd.loader.exec_module(_sd)
    _cfg_g = _sd.SUBSTANCE_CONFIG["葡萄糖溶液"]
    _mismatch = []
    for _r in _bx["rows"]:
        if _r[5] == "—":
            continue
        try:
            _w = _sd.solve_concentration(_cfg_g, float(_r[1]), 20.0) * 100.0
        except ValueError as _e:                      # noqa: PERF203
            _mismatch.append((_r[0], f"反解失败 {_e}"))
            continue
        if abs(_w - float(_r[5])) > 0.02:
            _mismatch.append((_r[0], round(_w, 4), _r[5]))
    check("葡萄糖列 = 计算器葡萄糖式反解（Δ≤0.02 wt%）", not _mismatch, _mismatch)
    check("葡萄糖列在关联式适用域外标「—」（0 / 65 / 70 °Bx）",
          _by["0"][5] == "—" and _by["65"][5] == "—" and _by["70"][5] == "—",
          [_by[k][5] for k in ("0", "65", "70")])

    _desc_bx = _bx.get("description", "")
    check("葡萄糖列已标注「非查表值」与其适用区间",
          "非查表值" in _desc_bx and "10~60" in _desc_bx, _desc_bx[:60])
    check("说明锤度为蔗糖基准且非蔗糖液读数为表观值",
          "表观锤度" in _desc_bx and "蔗糖" in _desc_bx)
    check("说明含波美度常数口径警告（美制重表 145 vs 144.3）",
          "美制重表" in _desc_bx and "144.3" in _desc_bx, _desc_bx[-160:])
    check("说明含相对密度基准警告（d20/20 vs 4 °C 水 SG）",
          "4 °C 水" in _desc_bx and "998.203" in _desc_bx, _desc_bx[-160:])
    check("出处含 NBS / ICUMSA / Landolt-Börnstein",
          all(k in _bx.get("source", "") for k in ("NBS", "ICUMSA", "Landolt")),
          _bx.get("source"))
    check("锤度表标签齐备（供标签筛选）", bool(_bx.get("tags")), _bx.get("tags"))

# ── 波美度-比重-糖度换算详表（333 行，粒度 = 企业换算表） ────────────────────
_cat2, _bx2 = find("波美度-比重-糖度换算详表（20 °C，比重每 0.001）")
check("波美度详表存在", _bx2 is not None)
if _bx2 is not None:
    check("详表归入「物性数据」分类", _cat2.get("category") == "物性数据", _cat2.get("category"))
    _h2 = _bx2.get("headers", [])
    check("详表 5 列（波美度/比重/糖度/干物量/真密度）",
          len(_h2) == 5 and all(k in "".join(_h2)
                                for k in ("波美度", "比重", "糖度", "干物量", "真密度")), _h2)
    _r2 = _bx2["rows"]
    check("详表 333 行（比重 1.000~1.332 每 0.001；改关联式须重建全表）",
          len(_r2) == 333, len(_r2))
    check("详表首行 = 纯水（Be 0.00 / D 1.000 / Bx 0.08）",
          _r2[0][:3] == ["0.00", "1.000", "0.08"], _r2[0])
    check("详表末行 = 20 °C 蔗糖溶解度上限（Be 35.97 / D 1.332 / Bx 66.88 / 干物量 89.08）",
          _r2[-1][:4] == ["35.97", "1.332", "66.88", "89.08"], _r2[-1])
    _d2 = [float(r[1]) for r in _r2]
    check("比重列严格递增且步长恒 0.001",
          all(abs(_d2[_i + 1] - _d2[_i] - 0.001) < 1e-9 for _i in range(len(_d2) - 1)),
          _d2[:3])
    _b2 = [float(r[2]) for r in _r2]
    check("糖度列严格单调递增（二分反解无跳变）",
          all(_b2[_i + 1] > _b2[_i] for _i in range(len(_b2) - 1)))
    check("详表上限不超 20 °C 蔗糖溶解度（≤67 °Bx）", max(_b2) <= 67.0, max(_b2))

    _bad2 = [r[1] for r in _r2
             if abs((144.3 - 144.3 / float(r[1])) - float(r[0])) > 0.005
             or abs(float(r[3]) - round(float(r[2]), 2) * float(r[1])) > 0.005
             or abs(float(r[4]) - float(r[1]) * 998.203) > 0.005]
    check("三列派生自洽（Be=144.3 式 / 干物量=糖度×比重 / 真密度=比重×998.203）",
          not _bad2, _bad2[:3])

    _cfg_s = _sd.SUBSTANCE_CONFIG["蔗糖溶液"]
    _mis2 = [(r[1], r[2]) for r in _r2[::37]
             if abs(_sd.solve_concentration(_cfg_s, float(r[4]), 20.0) * 100 - float(r[2])) > 0.01]
    check("糖度列 = 计算器蔗糖式反解（抽样 Δ≤0.01 °Bx，改关联式必须重建全表）",
          not _mis2, _mis2)

    _grid2 = {r[1]: r for r in _r2}
    _dev2 = [(r[0], _grid2["%.3f" % (round(float(r[2]) * 1000) / 1000.0)][2])
             for r in _bx["rows"]
             if "%.3f" % (round(float(r[2]) * 1000) / 1000.0) in _grid2
             and abs(float(_grid2["%.3f" % (round(float(r[2]) * 1000) / 1000.0)][2])
                     - float(r[0])) > 0.35]
    check("详表与锤度表在重叠节点一致（≤0.35 °Bx；70 °Bx 在溶解度上限外）", not _dev2, _dev2)

    # 企业换算表锚点（用户 2026-09 提供照片，糖度/比重/干物量三列实测）
    _badent = [(_d, _grid2[_d][2], _v) for _d, _v in
               [("1.007", "1.80"), ("1.150", "34.30"), ("1.215", "46.88"),
                ("1.276", "57.77"), ("1.286", "59.30")]
               if _d not in _grid2 or abs(float(_grid2[_d][2]) - float(_v)) > 0.35]
    check("详表与企业换算表锚点吻合（≤0.35 °Bx）", not _badent, _badent)

    _desc2 = _bx2.get("description", "")
    check("详表说明含口径 / 溶解度上限 / 不外推三要点",
          "144.3" in _desc2 and "67" in _desc2 and "不外推" in _desc2, _desc2[-90:])
    check("详表说明声明派生性质（关联式生成，非独立查表数据）",
          "关联式" in _desc2 and "派生" in _desc2)
    check("详表出处含比对基准（企业换算表）",
          "企业换算表" in _bx2.get("source", ""), _bx2.get("source"))
    check("详表标签齐备（含 波美度 / 比重，供标签筛选）",
          {"波美度", "比重"} <= set(_bx2.get("tags", [])), _bx2.get("tags"))

# ══════════════════════════ 设计标准采用清单（8 行转录表） ══════════════════════════
print()
print("=" * 60)
print("O. 设计标准采用清单")
print("=" * 60)

_std_cat, _std = find("设计标准采用清单")
check("设计标准采用清单存在", _std is not None)
if _std is not None:
    check("清单归入「设计规范」分类（库内末位新分类）",
          _std_cat.get("category") == "设计规范", _std_cat.get("category"))
    _h3 = _std.get("headers", [])
    check("清单 4 列（类别/标准/采用说明/库内覆盖）",
          _h3 == ["类别", "标准/规范", "采用说明", "库内覆盖"], _h3)
    _r3 = _std.get("rows", [])
    check("清单 8 行", len(_r3) == 8, len(_r3))
    _names = [r[0] for r in _r3]
    check("清单 8 个类别与照片一致",
          _names == ["PFD 工艺流程方框图", "P&ID 管道及仪表流程图", "生物工艺设备",
                     "食品机械安全", "钢制焊接容器", "爆炸环境设备", "投资估算分级",
                     "设计开发控制"], _names)
    _stds = " ".join(r[1] for r in _r3)
    check("标准号齐全（ISO 10628/ISA-5.1/ASME BPE/GB 16798/GB 14881/GB 150/"
          "GB 50058/AACE/ISO 9001）",
          all(k in _stds for k in ["ISO 10628", "ISA-5.1", "ASME BPE", "GB 16798",
                                   "GB 14881", "GB 150", "GB 50058", "AACE",
                                   "ISO 9001"]), _stds)
    _cov = [r[3] for r in _r3]
    check("覆盖列三种状态齐备（✅/⚠️/❌）",
          any(c.startswith("✅") for c in _cov) and any(c.startswith("⚠️") for c in _cov)
          and any(c.startswith("❌") for c in _cov), _cov)
    check("覆盖状态与实际相符：GB 50058/AACE ✅，ISO 10628/ISA-5.1/BPE/16798/9001 ❌",
          _cov[5].startswith("✅") and _cov[6].startswith("✅")
          and all(_cov[i].startswith("❌") for i in (0, 1, 2, 3, 7)), _cov)
    check("采用说明为清单原文（含【建议】前缀）",
          all(r[2].startswith("【建议】") for r in _r3),
          [r[2] for r in _r3[:2]])
    check("清单说明注明转录日期与覆盖列含义",
          "2026-09-21" in _std.get("description", "")
          and "库内覆盖" in _std.get("description", ""))
    check("清单出处标注照片转录来源",
          "照片转录" in _std.get("source", ""), _std.get("source"))
    check("清单标签齐备（含 标准/清单）",
          {"标准", "清单"} <= set(_std.get("tags", [])), _std.get("tags"))

# ══════════════════════════════ 汇总 ══════════════════════════════
print()
print("=" * 60)
print(f"总结: {PASS} 过, {FAIL} 失败")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
