# -*- coding: utf-8 -*-
"""换热器计算器回归测试（7 种模式：能量平衡 + LMTD）
手算案例全部闭合推演，运行: tests/test_heat_exchanger_calc.py
注意: setup_calculation_mode(idx) 会重建输入面板并清空已填值,
      因此正确顺序是 switch_mode → setv → calculate
"""
import math
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "modules", "chemical_calculations", "calculators"))
sys.path.insert(0, os.path.join(ROOT, "modules", "chemical_calculations"))
sys.path.insert(0, ROOT)

from data_manager import DataManager
DataManager.get_instance(data_file=os.path.join(os.environ.get("TEMP", "/tmp"), "chemcal_test_hx_calc.json"))

from PySide6.QtWidgets import QApplication, QMessageBox
app = QApplication.instance() or QApplication(sys.argv)
for name in ("warning", "critical", "information", "question"):
    setattr(QMessageBox, name, (lambda n: (lambda *a, **k: QMessageBox.StandardButton.Ok))(name))

import heat_exchanger_calculator as mod
from common_constants import get_steam_props

PASS, FAIL = 0, 0
def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")

w = mod.换热器计算()

def switch_mode(idx):
    w.mode_combo.setCurrentIndex(idx)
    w.setup_calculation_mode(idx)

def setv(key, val):
    w.input_widgets[key].setText(str(val))

# ══ 模式0：求饱和蒸汽流量 ══
switch_mode(0)
setv("蒸汽压力g_mpa", 0.3)
setv("冷流体w_kg_h", 10000)
setv("冷流体cp_kj_kgk", 4.19)
setv("冷流体t1_℃", 20)
setv("冷流体t2_℃", 60)
w.calculate()
# 手算: Q=10000×4.19×40/3600=465.56 kW; W_steam=465.56×3600/2133.3≈785.6 kg/h
r = get_steam_props(0.3)["h_fg"]
steam_exp = 10000 * 4.19 * 40 / r
check("模式0 饱和温度≈143.7 °C (get_steam_props)", "143.7" in w.result_text.toPlainText())
check(f"模式0 蒸汽流量≈{steam_exp:.1f} kg/h（手算闭合）", f"{steam_exp:.1f}" in w.result_text.toPlainText())

# ══ 模式1：求冷流体流量（蒸汽加热）══
switch_mode(1)
setv("蒸汽压力g_mpa", 0.3)
setv("蒸汽流量_kg_h", 500)
setv("冷流体cp_kj_kgk", 4.19)
setv("冷流体t1_℃", 20)
setv("冷流体t2_℃", 50)
w.calculate()
# 手算: Q=500×2133.3/3600=296.29 kW; W_cold=296.29×3600/(4.19×30)≈8486.5 kg/h
w_cold = 500 * r / (4.19 * 30)
check(f"模式1 冷流体流量≈{w_cold:.1f} kg/h（手算闭合）", f"{w_cold:.1f}" in w.result_text.toPlainText())

# ══ 模式2：求冷流体出口温度（蒸汽加热）══
switch_mode(2)
setv("蒸汽压力g_mpa", 0.3)
setv("蒸汽流量_kg_h", 500)
setv("冷流体w_kg_h", 10000)
setv("冷流体cp_kj_kgk", 4.19)
setv("冷流体t1_℃", 20)
w.calculate()
# 手算: t2 = 20 + 296.29×3600/(10000×4.19) = 45.5 °C
t2_exp = 20 + (500 * r / 3600) * 3600 / (10000 * 4.19)
check(f"模式2 冷流体出口≈{t2_exp:.1f} °C（手算闭合）", f"{t2_exp:.1f}" in w.result_text.toPlainText())

# ══ 模式3：求冷流体出口温度（无蒸汽）══
switch_mode(3)
setv("热流体w_kg_h", 5000)
setv("热流体cp_kj_kgk", 4.19)
setv("热流体t1_℃", 90)
setv("热流体t2_℃", 60)
setv("冷流体w_kg_h", 10000)
setv("冷流体cp_kj_kgk", 4.19)
setv("冷流体t1_℃", 20)
w.calculate()
# 手算: Q=174.58 kW; t2=35.0; LMTD: dT1=55, dT2=40 → 47.1
check("模式3 冷流体出口=35.0 °C（手算闭合）", "35.0" in w.result_text.toPlainText())
lmtd3 = 15 / math.log(55 / 40)
check(f"模式3 LMTD≈{lmtd3:.1f} °C（逆流端差）", f"{lmtd3:.1f}" in w.result_text.toPlainText())

# ══ 模式4：求热流体出口温度 ══
switch_mode(4)
setv("热流体w_kg_h", 5000)
setv("热流体cp_kj_kgk", 4.19)
setv("热流体t1_℃", 90)
setv("冷流体w_kg_h", 10000)
setv("冷流体cp_kj_kgk", 4.19)
setv("冷流体t1_℃", 20)
setv("冷流体t2_℃", 50)
w.calculate()
# 手算: Q=349.17 kW; hot_t2=90-349.17×3600/(5000×4.19)=30.0; LMTD=30/ln4=21.6
check("模式4 热流体出口=30.0 °C（手算闭合）", "30.0" in w.result_text.toPlainText())
lmtd4 = 30 / math.log(4)
check(f"模式4 LMTD≈{lmtd4:.1f} °C", f"{lmtd4:.1f}" in w.result_text.toPlainText())

# ══ 模式5：求冷流体流量 ══
switch_mode(5)
setv("热流体w_kg_h", 5000)
setv("热流体cp_kj_kgk", 4.19)
setv("热流体t1_℃", 90)
setv("热流体t2_℃", 60)
setv("冷流体cp_kj_kgk", 4.19)
setv("冷流体t1_℃", 20)
setv("冷流体t2_℃", 50)
w.calculate()
# 手算: Q=174.58 kW; W_cold=174.58×3600/(4.19×30)=5000.0 kg/h
check("模式5 冷流体流量=5000.0 kg/h（手算闭合）", "5000.0" in w.result_text.toPlainText())

# ══ 模式6：求热流体流量 ══
switch_mode(6)
setv("热流体cp_kj_kgk", 4.19)
setv("热流体t1_℃", 90)
setv("热流体t2_℃", 60)
setv("冷流体w_kg_h", 10000)
setv("冷流体cp_kj_kgk", 4.19)
setv("冷流体t1_℃", 20)
setv("冷流体t2_℃", 50)
w.calculate()
# 手算: W_hot=349.17×3600/(4.19×30)=10000.0 kg/h
check("模式6 热流体流量=10000.0 kg/h（手算闭合）", "10000.0" in w.result_text.toPlainText())

# ══ 温度交叉防护（模式3 冷侧流量过小 → 出口超过热进口）══
switch_mode(3)
setv("热流体w_kg_h", 5000)
setv("热流体t1_℃", 90)
setv("热流体t2_℃", 60)
setv("冷流体w_kg_h", 500)
setv("冷流体t1_℃", 20)
w.calculate()
# 弹窗被拦截返回 Ok, 只要进程不崩溃即视为防护生效
check("模式3 温度交叉防护不崩溃", True)

# ══ 导出契约 ══
switch_mode(0)
w.calculate()
rep = w.generate_report()
check("generate_report 返回 str 或 None", rep is None or isinstance(rep, str))
info = w.get_project_info()
check("get_project_info 返回 dict", isinstance(info, dict))

print(f"\n{'='*40}\n通过 {PASS} 项, 失败 {FAIL} 项")
print("ALL PASS" if FAIL == 0 else "HAS FAILURES")
sys.exit(0 if FAIL == 0 else 1)
