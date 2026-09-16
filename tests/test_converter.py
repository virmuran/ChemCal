# -*- coding: utf-8 -*-
"""换算器回归测试（21 类，2026-09-15 由 11 类扩充而来）

为什么单独建这个文件：换算器此前一个锚点都没有 —— 45 个计算器都有"手算值与标准值比对"
的测试固化，换算器却只测过"能不能实例化"。而换算系数的错误是最难被用户发现的：
它不报错、不崩溃，只是**安静地给出错 1000 倍的答案**。本次扩充时就实抓到一个
（`mol/L` 的系数写成了 1e-3，导致 1 mol/L NaCl 被算成 0.05844 kg/m³ 而非 58.44）。

固化三类不变式：
  A. 覆盖率 —— 21 个类目全部实例化，且清单/导航/包导出三处一致
  B. 数值锚点 —— 每个换算器都有手算可复现的锚点值（含非线性单位、跨组辅助参数）
  C. 交互不变式 —— 实时换算、清空传播、辅助参数改动后重算、缺辅助参数留空
     （"缺参数就给个看似合理的数字"是这类页面的头号坑）

运行：
    QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe tests/test_converter.py
"""
import os
import sys

PROJ = r"C:\Users\Administrator\Desktop\ChemCal"
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication                       # noqa: E402

from modules.converter.calculators.unit_converter_base import UnitConverterPage  # noqa: E402
from modules.converter import converter_widget                    # noqa: E402

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


def close(actual, expected, rel=2e-4):
    """相对误差比较（换算系数取的是 6 位有效数字，故不能要求完全相等）。"""
    if actual is None:
        return False
    if expected == 0:
        return abs(actual) < 1e-12
    return abs(actual - expected) / abs(expected) <= rel


app = QApplication.instance() or QApplication([])

# ══════════════════════════════ A. 覆盖率与清单一致性 ══════════════════════════════
section("A. 覆盖率与清单一致性")

from modules.converter.calculators import __all__ as CALC_ALL       # noqa: E402

MODULE_LIST = [m for m, _c, _t in converter_widget.CALCULATOR_MODULES]
TITLE_LIST = [t for _m, _c, t in converter_widget.CALCULATOR_MODULES]

check("换算器清单为 21 类", len(MODULE_LIST) == 21, len(MODULE_LIST))
check("模块路径无重复", len(set(MODULE_LIST)) == len(MODULE_LIST))
check("导航标题无重复", len(set(TITLE_LIST)) == len(TITLE_LIST))
check("包导出（__all__）与清单条目数一致", len(CALC_ALL) == 21, len(CALC_ALL))
check("清单里每个类名都出现在 __all__ 中",
      all(c in CALC_ALL for _m, c, _t in converter_widget.CALCULATOR_MODULES),
      [c for _m, c, _t in converter_widget.CALCULATOR_MODULES if c not in CALC_ALL])

conv_widget = converter_widget.ConverterWidget()
check("ConverterWidget 实例化无异常", conv_widget is not None)
check("导航项数 == 页面数 == 清单条目数",
      conv_widget.nav_list.count() == len(conv_widget.pages) == 21,
      f"nav={conv_widget.nav_list.count()} pages={len(conv_widget.pages)}")
check("页面标题与清单顺序一致",
      [conv_widget.nav_list.item(i).text() for i in range(21)] == TITLE_LIST)
# 页面是**按需实例化**的（首次打开才建真页面）——本文件后续要直接读各页控件，
# 这里统一点亮全部页面；惰性行为本身由 tests/test_lazy_pages.py 专门验证。
check("惰性加载：构造后只有首行是真页面",
      sum(1 for p in conv_widget.pages if not hasattr(p, "_lazy_spec")) == 1)
conv_widget.ensure_all_pages()
check("ensure_all_pages() 后全部 21 页都是真页面",
      all(not hasattr(p, "_lazy_spec") for p in conv_widget.pages))

SUB_MODULES = [
    "flow_converter", "density_converter", "dynamic_viscosity_converter",
    "kinematic_viscosity_converter", "surface_tension_converter",
    "thermal_conductivity_converter", "heat_transfer_coefficient_converter",
    "specific_heat_converter", "calorific_value_converter",
    "concentration_converter",
]
check("新增的 10 个换算器都继承通用基类 UnitConverterPage",
      all(issubclass(type(conv_widget.pages[TITLE_LIST.index(t)]), UnitConverterPage)
          for t in ["流量换算", "密度换算", "动力粘度换算", "运动粘度换算",
                    "表面张力换算", "导热系数换算", "传热系数换算",
                    "比热容换算", "热值换算", "浓度换算"]))

# ══════════════════════════════ B. 数值锚点 ══════════════════════════════
section("B. 数值锚点（手算可复现）")

# (标题, 辅助参数, [(来源单位, 输入值, 目标单位, 期望值, 说明)])
CASES = [
    ("流量换算", {"rho": "1000"}, [
        ("m3_h", 3600, "m3_s", 1.0, "3600 m³/h = 1 m³/s"),
        ("m3_h", 3600, "L_s", 1000.0, "1 m³/s = 1000 L/s"),
        ("L_min", 60, "m3_h", 3.6, "60 L/min = 1 L/s = 3.6 m³/h"),
        ("gpm_us", 1, "L_min", 3.785411784, "1 美加仑/min = 3.7854 L/min"),
        ("ft3_min", 1, "m3_h", 1.6990108, "1 ft³/min = 0.0283168 m³/min"),
        ("t_h", 1, "m3_s", 2.7777778e-4, "1 t/h 水 = 1 m³/h"),
        ("kg_h", 1000, "m3_h", 1.0, "1000 kg/h 水 = 1 m³/h"),
    ]),
    ("密度换算", {}, [
        ("g_cm3", 1, "kg_m3", 1000.0, "1 g/cm³ = 1000 kg/m³"),
        ("g_cm3", 1, "sg", 1.0, "水相对密度 = 1"),
        ("g_cm3", 1, "api", 10.0, "SG=1 → °API = 141.5/1 − 131.5 = 10"),
        ("kg_m3", 1000, "be", 0.0, "SG=1 → °Bé = 145 − 145/1 = 0"),
        ("api", 35, "kg_m3", 849.84985, "°API35 → SG=141.5/166.5=0.84985"),
        ("lb_ft3", 1, "kg_m3", 16.0185, "0.45359237 / 0.028316846"),
        ("kg_m3", 1000, "lb_gal", 8.345428, "1000 / 119.826"),
    ]),
    ("动力粘度换算", {}, [
        ("mPa_s", 1, "Pa_s", 1e-3, "1 mPa·s = 1e-3 Pa·s"),
        ("mPa_s", 1, "P", 0.01, "1 cP = 0.01 P"),
        ("P", 1, "mPa_s", 100.0, "1 P = 100 cP"),
        ("Pa_s", 1, "mPa_s", 1000.0, "1 Pa·s = 1000 cP"),
        ("kgf_s_m2", 1, "Pa_s", 9.80665, "1 kgf·s/m² = 9.80665 Pa·s"),
    ]),
    ("运动粘度换算", {}, [
        ("mm2_s", 1, "m2_s", 1e-6, "1 mm²/s（=1 cSt）= 1e-6 m²/s"),
        ("St", 1, "mm2_s", 100.0, "1 St = 100 cSt = 100 mm²/s"),
        ("m2_h", 1, "mm2_s", 277.77778, "1 m²/h = /3600 → /1e-6"),
    ]),
    ("表面张力换算", {}, [
        ("mN_m", 72, "N_m", 0.072, "水的表面张力约 72 mN/m"),
        ("N_m", 1, "mN_m", 1000.0, "1 N/m = 1000 mN/m"),
        ("kgf_m", 1, "N_m", 9.80665, "1 kgf/m = 9.80665 N/m"),
        ("gf_cm", 1, "N_m", 0.980665, "1 gf/cm = 0.980665 N/m"),
    ]),
    ("导热系数换算", {}, [
        ("kcal_h_m", 1, "W_mK", 1.163, "4186.8 J / 3600 s（国际蒸汽表卡）"),
        ("cal_s_cm", 1, "W_mK", 418.68, "1 cal/(s·cm·℃)"),
        ("BTU_h_ft", 1, "W_mK", 1.730735, "1 BTU/(h·ft·°F)"),
        ("W_mK", 45, "kcal_h_m", 38.6930, "碳钢 45 W/(m·K)"),
    ]),
    ("传热系数换算", {}, [
        ("kcal_h_m2", 1, "W_m2K", 1.163, "1 kcal/(h·m²·℃) = 1.163 W/(m²·K)"),
        ("BTU_h_ft2", 1, "W_m2K", 5.678263, "1 BTU/(h·ft²·°F)"),
        ("W_m2K", 1000, "kW_m2K", 1.0, "1000 W/(m²·K) = 1 kW/(m²·K)"),
        ("cal_s_cm2", 1, "W_m2K", 41868.0, "1 cal/(s·cm²·℃)"),
    ]),
    ("比热容换算", {}, [
        ("kcal_kgC", 1, "kJ_kgK", 4.1868, "1 kcal/(kg·℃) = 4.1868 kJ/(kg·K)"),
        ("BTU_lbF", 1, "kJ_kgK", 4.1868, "1 BTU/(lb·°F) = 4.1868 kJ/(kg·K)"),
        ("Wh_kgK", 1, "kJ_kgK", 3.6, "1 W·h/(kg·K) = 3.6 kJ/(kg·K)"),
        ("kJ_kgK", 4.18, "kcal_kgC", 0.998374, "20 ℃ 水的比热"),
    ]),
    ("热值换算", {}, [
        ("MJ_kg", 29.31, "kJ_kg", 29310.0, "标准煤 29.31 MJ/kg"),
        ("BTU_lb", 1, "kJ_kg", 2.32602, "1 BTU/lb = 2.326 kJ/kg"),
        ("kWh_kg", 1, "kJ_kg", 3600.0, "1 kW·h/kg = 3600 kJ/kg"),
        ("kJ_kg", 26800, "MJ_kg", 26.8, "无水乙醇低位热值"),
    ]),
    ("浓度换算", {"rho": "1000", "M": "58.44"}, [
        ("pct", 1, "kg_m3", 10.0, "1% × 1000 kg/m³ = 10 kg/m³"),
        ("pct", 0.9, "kg_m3", 9.0, "0.9% 生理盐水 ≈ 9 kg/m³"),
        ("ppm", 1000, "kg_m3", 1.0, "1000 ppm × 1000 = 1 kg/m³"),
        ("kg_m3", 1, "mg_L", 1000.0, "1 kg/m³ = 1000 mg/L"),
        ("kg_m3", 1, "g_100mL", 0.1, "1 kg/m³ = 0.1 g/100mL"),
        ("mol_L", 1, "kg_m3", 58.44, "1 mol/L NaCl → 58.44 kg/m³（曾误算为 0.058）"),
        ("kmol_m3", 1, "kg_m3", 58.44, "1 kmol/m³ → 58.44 kg/m³"),
        ("mol_m3", 1, "kg_m3", 0.05844, "1 mol/m³ → 0.05844 kg/m³"),
        ("mmol_L", 1, "kg_m3", 0.05844, "1 mmol/L = 1 mol/m³（曾误算为 5.8e-5）"),
        ("umol_L", 1000, "kg_m3", 0.05844, "1000 μmol/L = 1 mmol/L"),
        ("kg_m3", 58.44, "mol_L", 1.0, "反向：58.44 kg/m³ → 1 mol/L"),
    ]),
]

index = {t: i for i, t in enumerate(TITLE_LIST)}
for title, aux, cases in CASES:
    page = conv_widget.pages[index[title]]
    for key, value in aux.items():
        page.aux_widgets[key].setText(value)
    codes = {u[1] for u in page.UNITS}
    for from_unit, value, to_unit, expected, why in cases:
        label = f"{title}·{why}"
        if from_unit not in codes or to_unit not in codes:
            check(label, False, f"单位代号不存在: {from_unit if from_unit not in codes else to_unit}")
            continue
        got = page.do_conversion(value, from_unit, to_unit)
        check(label, close(got, expected), f"得到 {got} 期望 {expected}")

section("B2. 往返一致性（任取一对单位，来回换算应回到原值）")
for title, aux, _cases in CASES:
    page = conv_widget.pages[index[title]]
    for key, value in aux.items():
        page.aux_widgets[key].setText(value)
    units = [u[1] for u in page.UNITS]
    worst, bad_pair = 0.0, ""
    for a in units:
        for b in units:
            if a == b:
                continue
            round_trip = page.do_conversion(page.do_conversion(123.456, a, b), b, a)
            if round_trip is None:
                continue
            err = abs(round_trip - 123.456) / 123.456
            if err > worst:
                worst, bad_pair = err, f"{a}->{b}->{a}"
    check(f"{title}·全单位两两往返误差 < 1e-6", worst < 1e-6, f"最差 {bad_pair} 误差 {worst:.2e}")

section("B3. 组内比值（1 a = ? b）—— 与辅助参数无关，专抓千倍级系数错误")

# 为什么单列这一节：往返一致性对"整体差 1000 倍"是**瞎的**（错得自洽，来回能回到原值）。
# 组内比值则与密度/摩尔质量无关，只要系数写错一档就一定暴露。
# 本次扩充就是这样抓到 mmol/L（1e-6→1e-3）与 μmol/L（1e-9→1e-6）两处千倍错误。
RATIO_CASES = [
    ("流量换算", {}, [("m3_h", "L_h", 1000.0), ("m3_h", "L_s", 1000 / 3600),
                      ("t_h", "kg_h", 1000.0), ("L_s", "L_min", 60.0)]),
    ("密度换算", {}, [("g_cm3", "kg_m3", 1000.0), ("t_m3", "kg_m3", 1000.0),
                      ("g_L", "kg_m3", 1.0), ("kg_m3", "g_L", 1.0)]),
    ("动力粘度换算", {}, [("Pa_s", "mPa_s", 1000.0), ("P", "mPa_s", 100.0),
                          ("Pa_s", "P", 10.0)]),
    ("运动粘度换算", {}, [("St", "mm2_s", 100.0), ("m2_s", "mm2_s", 1e6),
                          ("m2_s", "St", 1e4)]),
    ("表面张力换算", {}, [("N_m", "mN_m", 1000.0), ("kgf_m", "gf_cm", 10.0)]),
    ("导热系数换算", {}, [("kW_mK", "W_mK", 1000.0), ("W_mK", "mW_mK", 1000.0)]),
    ("传热系数换算", {}, [("kW_m2K", "W_m2K", 1000.0)]),
    ("比热容换算", {}, [("kJ_kgK", "J_kgK", 1000.0), ("kcal_kgC", "BTU_lbF", 1.0)]),
    ("热值换算", {}, [("MJ_kg", "kJ_kg", 1000.0), ("kWh_kg", "kJ_kg", 3600.0)]),
    ("浓度换算", {"rho": "1000", "M": "58.44"},
     [("mol_L", "mmol_L", 1000.0), ("mmol_L", "umol_L", 1000.0),
      ("mol_L", "mol_m3", 1000.0), ("kmol_m3", "mol_m3", 1000.0),
      ("mol_L", "umol_L", 1e6), ("pct", "ppm", 10000.0), ("ppm", "ppb", 1000.0),
      ("kg_m3", "mg_L", 1000.0), ("g_100mL", "kg_m3", 10.0)]),
]

for title, aux, ratios in RATIO_CASES:
    page = conv_widget.pages[index[title]]
    for key, value in aux.items():
        page.aux_widgets[key].setText(value)
    codes = {u[1] for u in page.UNITS}
    for a, b, expected in ratios:
        label = f"{title}·1 {a} = {expected:g} {b}"
        if a not in codes or b not in codes:
            check(label, False, f"单位代号不存在: {a if a not in codes else b}")
            continue
        got = page.from_base(b, page.to_base(a, 1.0))
        check(label, close(got, expected), f"得到 {got}")

# ══════════════════════════════ C. 交互不变式 ══════════════════════════════
section("C. 交互不变式")

# C1 输入一格 → 其余全部填上
flow = conv_widget.pages[index["流量换算"]]
flow.clear_all()
flow.unit_vars["m3_h"].setText("3600")
filled = [c for c, e in flow.unit_vars.items() if c != "m3_h" and e.text()]
check("输入一格后其余全部自动填充", len(filled) == len(flow.unit_vars) - 1,
      f"仅 {len(filled)}/{len(flow.unit_vars) - 1}")
check("自动填充值正确（3600 m³/h → 1000 L/s）",
      close(float(flow.unit_vars["L_s"].text()), 1000.0), flow.unit_vars["L_s"].text())

# C2 清空一格 → 其余全部清空（不能留旧结果）
flow.unit_vars["m3_h"].setText("")
leftovers = [c for c, e in flow.unit_vars.items() if c != "m3_h" and e.text()]
check("清空输入格后其余全部清空", not leftovers, leftovers)

# C3 非法输入不打断、不残留
flow.unit_vars["m3_h"].setText("1e-")
flow.unit_vars["m3_h"].setText("abc")
check("非法输入时不填出结果", not flow.unit_vars["L_s"].text())
flow.unit_vars["m3_h"].setText("nan")
check("nan 输入被挡下（不显示 inf/nan）", not flow.unit_vars["L_s"].text())
flow.unit_vars["m3_h"].setText("inf")
check("inf 输入被挡下", not flow.unit_vars["L_s"].text())

# C4 辅助参数改动 → 按上一次输入自动重算
conc = conv_widget.pages[index["浓度换算"]]
conc.clear_all()
conc.aux_widgets["rho"].setText("1000")
conc.unit_vars["pct"].setText("10")
before = conc.unit_vars["kg_m3"].text()
conc.aux_widgets["rho"].setText("1200")
after = conc.unit_vars["kg_m3"].text()
check("改密度后自动重算（10% @1000→100，@1200→120）",
      close(float(before), 100.0) and close(float(after), 120.0),
      f"{before} -> {after}")

# C5 缺辅助参数 → 对应一组留空（不给看似合理的数字）
conc.clear_all()
conc.aux_widgets["M"].setText("")          # 摩尔质量留空
conc.unit_vars["mol_L"].setText("1")
check("缺摩尔质量时物质的量浓度组留空", not conc.unit_vars["kg_m3"].text(),
      conc.unit_vars["kg_m3"].text())
conc.aux_widgets["M"].setText("58.44")     # 补上后应自动出现结果
check("补上摩尔质量后自动算出结果",
      close(float(conc.unit_vars["kg_m3"].text()), 58.44), conc.unit_vars["kg_m3"].text())

conc.clear_all()
conc.aux_widgets["rho"].setText("")        # 密度留空
conc.unit_vars["pct"].setText("1")
check("缺密度时质量分数组留空（不给错数字）", not conc.unit_vars["kg_m3"].text(),
      conc.unit_vars["kg_m3"].text())
conc.unit_vars["kg_m3"].setText("1")       # 质量浓度组自身可互换，不受密度影响
check("缺密度不影响自身可互换的质量浓度组（1 kg/m³ = 1000 mg/L）",
      close(float(conc.unit_vars["mg_L"].text() or "0"), 1000.0)
      and close(float(conc.unit_vars["g_100mL"].text() or "0"), 0.1),
      f"mg/L={conc.unit_vars['mg_L'].text()} g/100mL={conc.unit_vars['g_100mL'].text()}")
check("缺密度时物质的量浓度组仍可算（只需摩尔质量）",
      close(float(conc.unit_vars["mol_L"].text() or "0"), 1 / 58.44),
      conc.unit_vars["mol_L"].text())
conc.aux_widgets["rho"].setText("1000")

# C6 除零不产生 inf
density = conv_widget.pages[index["密度换算"]]
density.clear_all()
density.unit_vars["api"].setText("-131.5")          # 分母为 0
check("°API = −131.5（分母为零）不产生 inf/nan",
      not any("inf" in e.text().lower() or "nan" in e.text().lower()
              for e in density.unit_vars.values()))
density.clear_all()
density.unit_vars["be"].setText("145")              # 波美度分母为零
check("波美度 = 145（分母为零）不产生 inf/nan",
      not any("inf" in e.text().lower() or "nan" in e.text().lower()
              for e in density.unit_vars.values()))

# C7 clear_all 后可直接重算
flow.clear_all()
flow.unit_vars["m3_h"].setText("36")
check("clear_all 后可直接重算", close(float(flow.unit_vars["L_s"].text()), 10.0),
      flow.unit_vars["L_s"].text())

# C8 全部 21 页都能实例化并切换（含原生 11 个换算器）
ok, err = True, ""
for i in range(conv_widget.nav_list.count()):
    try:
        conv_widget.nav_list.setCurrentRow(i)
    except Exception as e:      # noqa: BLE001
        ok, err = False, f"第 {i} 页: {e}"
        break
check("21 个换算页面逐个切换不抛异常", ok, err)

# ══════════════════════════════ D. 源码不写颜色 ══════════════════════════════
section("D. 源码不写颜色（三套主题才可读）")

import re                                                                  # noqa: E402
CALC_DIR = os.path.join(PROJ, "modules", "converter")
offenders = {}
for root, _dirs, files in os.walk(CALC_DIR):
    if "__pycache__" in root:
        continue
    for fname in files:
        if not fname.endswith(".py"):
            continue
        path = os.path.join(root, fname)
        with open(path, encoding="utf-8") as fh:
            hits = re.findall(r"#[0-9a-fA-F]{3,8}\b", fh.read())
        if hits:
            offenders[fname] = hits
check("换算器源码零硬编码颜色", not offenders, offenders)

# ══════════════════════════════ 汇总 ══════════════════════════════
print()
print("=" * 60)
print(f"总结: {PASS} 过, {FAIL} 失败")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
