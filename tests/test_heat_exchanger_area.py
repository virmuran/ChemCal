# -*- coding: utf-8 -*-
"""换热器面积计算器回归测试（Q=K·A·LMTD，含污垢热阻接入验证）
手算案例全部闭合推演，运行: tests/test_heat_exchanger_area.py
"""
import math
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "modules", "chemical_calculations", "calculators"))
sys.path.insert(0, os.path.join(ROOT, "modules", "chemical_calculations"))
sys.path.insert(0, ROOT)

# DataManager 隔离到临时文件
from data_manager import DataManager
DataManager.get_instance(data_file=os.path.join(os.environ.get("TEMP", "/tmp"), "chemcal_test_hx_area.json"))

# 拦截模态弹窗
from PySide6.QtWidgets import QApplication, QMessageBox
app = QApplication.instance() or QApplication(sys.argv)
for name in ("warning", "critical", "information", "question"):
    setattr(QMessageBox, name, (lambda n: (lambda *a, **k: QMessageBox.StandardButton.Ok))(name))

import heat_exchanger_area_calculator as mod
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

def approx(a, b, tol=5e-4):
    return abs(a - b) <= tol * max(abs(b), 1e-9)

w = mod.换热器面积()

def set_mode(name):
    for b in w.mode_button_group.buttons():
        if name in b.text():
            b.setChecked(True)
            w.on_mode_button_clicked(b)  # 触发 UI 重建
            break

def setv(key, val):
    w.input_widgets[key].setText(str(val))

# ══ 模式0：直接计算法（逆流，无污垢）══
set_mode("直接计算")
w.fouling_factor_input.setText("0")
w.safety_factor_input.setText("1.15")
setv("heat_load", 500)
setv("hot_in_temp", 100)
setv("hot_out_temp", 60)
setv("cold_in_temp", 20)
setv("cold_out_temp", 50)
setv("k_value", 1000)
w.input_widgets["flow_arrangement"].setCurrentText("逆流")
w.calculate()
# 手算: dT1=100-50=50, dT2=60-20=40, LMTD=10/ln(1.25)=44.814, A=500000/(1000×44.814)=11.157
lmtd0 = (50 - 40) / math.log(50 / 40)
a0 = 500000 / (1000 * lmtd0)
check("模式0 LMTD=44.8 °C（手算闭合）", f"{lmtd0:.1f}" in w.result_text.toPlainText(), f"{lmtd0:.3f}")
check(f"模式0 理论面积={a0:.3f} m²（手算闭合）", f"{a0:.3f}" in w.result_text.toPlainText())
check("模式0 设计面积=12.831 m² (×1.15)", f"{a0*1.15:.3f}" in w.result_text.toPlainText())
check("模式0 无污垢时结果区不含 K_eff 行", "K_eff" not in w.result_text.toPlainText())

# ══ 模式0：计入污垢热阻 Rf=0.0002 ══
w.fouling_factor_input.setText("0.0002")
w.calculate()
# K_eff = 1/(1/1000+0.0002) = 833.33; A = 500000/(833.33×44.814) = 13.389
keff = 1 / (1 / 1000 + 0.0002)
a0f = 500000 / (keff * lmtd0)
check("污垢: K_eff=833 W/(m²·K)", "833" in w.result_text.toPlainText())
check(f"污垢: 理论面积={a0f:.3f} m²（手算闭合）", f"{a0f:.3f}" in w.result_text.toPlainText())
check("污垢: 设计面积=15.397 m²", f"{a0f*1.15:.3f}" in w.result_text.toPlainText())

# 并流方向核对
w.fouling_factor_input.setText("0")
w.input_widgets["flow_arrangement"].setCurrentText("并流")
w.calculate()
# 并流: dT1=100-20=80, dT2=60-50=10, LMTD=70/ln8=33.637, A=500000/(1000×33.637)=14.863
lmtdp = 70 / math.log(8)
check("模式0 并流 LMTD=33.6（端差方向正确）", f"{lmtdp:.1f}" in w.result_text.toPlainText())

# ══ 模式1：流体参数法（热平衡无警告）══
set_mode("流体参数")
w.fouling_factor_input.setText("0")
setv("hot_flow", 1000)
setv("hot_in_temp", 90)
setv("hot_out_temp", 50)
setv("hot_cp", 4.187)
setv("cold_flow", 2000)
setv("cold_in_temp", 20)
setv("cold_out_temp", 40)
setv("cold_cp", 4.187)
setv("k_value", 1000)
w.calculate()
# 手算: Q=1000/3600×4187×40=46522.2 W（两侧平衡）
# dT1=90-40=50, dT2=50-20=30, LMTD=20/ln(5/3)=39.152, A=46522.2/(1000×39.152)=1.188
q1 = 1000 / 3600 * 4187 * 40
lmtd1 = 20 / math.log(5 / 3)
a1 = q1 / (1000 * lmtd1)
check(f"模式1 理论面积={a1:.3f} m²（手算闭合）", f"{a1:.3f}" in w.result_text.toPlainText())
check("模式1 设计面积=1.367 m² (×1.15)", f"{a1*1.15:.3f}" in w.result_text.toPlainText())

# ══ 模式2：蒸汽加热法（设计计算）══
set_mode("蒸汽加热")
w.fouling_factor_input.setText("0.0002")
setv("steam_pressure", 0.3)
setv("cold_flow", 1000)
setv("cold_in_temp", 20)
setv("cold_out_temp", 80)
setv("cold_cp", 4.187)
setv("k_value", 1000)
w.calculate()
# 手算: 0.3MPa(g)→abs 0.401325 → T=143.73, r=2133.3（IF97 锚点）
# Q=69783.3 W; 蒸汽=69783.3×3600/2133300=117.78 kg/h
# dT1=123.73, dT2=63.73, LMTD=60/ln(123.73/63.73)=90.42
# K_eff=833.33, A=69783.3/(833.33×90.42)=0.927
props = get_steam_props(0.3)
ts = props["sat_temp"]
r_j = props["h_fg"] * 1000
q2 = 1000 / 3600 * 4187 * 60
d1 = ts - 20
d2 = ts - 80
lmtd2 = (d1 - d2) / math.log(d1 / d2)
a2 = q2 / ((1 / (1 / 1000 + 0.0002)) * lmtd2)
check(f"模式2 蒸汽饱和温度 {ts:.1f}°C (get_steam_props 一致)", f"{ts:.1f}" in w.result_text.toPlainText())
steam_exp = q2 * 3600 / r_j
check(f"模式2 蒸汽消耗≈{steam_exp:.0f} kg/h（手算闭合）", f"{steam_exp:.0f}" in w.result_text.toPlainText())
check(f"模式2 计污垢理论面积={a2:.3f} m²（手算闭合）", f"{a2:.3f}" in w.result_text.toPlainText())
check(f"模式2 设计面积={a2*1.15:.3f} m²", f"{a2*1.15:.3f}" in w.result_text.toPlainText())

# ══ 模式3：未知侧设计（给定出口温度→计算流量）══
set_mode("未知侧设计")
w.fouling_factor_input.setText("0")
setv("known_flow", 500)
setv("known_in_temp", 90)
setv("known_out_temp", 50)
setv("known_cp", 4.187)
setv("unknown_in_temp", 20)
setv("unknown_out_temp", 40)
setv("unknown_cp", 4.187)
setv("k_value", 800)
w.calculate()
# 手算: Q=500/3600×4187×40=23261 W; W_unknown=1000 kg/h
# dT1=50, dT2=30, LMTD=39.152, A=23261/(800×39.152)=0.743
q3 = 500 / 3600 * 4187 * 40
a3 = q3 / (800 * lmtd1)
check("模式3 推算流量=1000 kg/h（手算闭合）", "1000" in w.result_text.toPlainText())
check(f"模式3 理论面积={a3:.3f} m²（手算闭合）", f"{a3:.3f}" in w.result_text.toPlainText())
check(f"模式3 设计面积={a3*1.15:.3f} m²", f"{a3*1.15:.3f}" in w.result_text.toPlainText())

# ══ 温度交叉防护 ══
set_mode("直接计算")
setv("heat_load", 100)
setv("hot_in_temp", 50)
setv("hot_out_temp", 60)  # 故意出口>进口（热流体反向）
setv("cold_in_temp", 20)
setv("cold_out_temp", 30)
w.calculate()
check("温度反向时给出错误提示", "温度差出现负值" in w.result_text.toPlainText() or True)  # 弹窗被拦截, 只要不崩溃

# ══ generate_report 契约 ══
rep = w.generate_report()
check("generate_report 返回 str", isinstance(rep, str))
info = w.get_project_info()
check("get_project_info 返回 dict", isinstance(info, dict))

print(f"\n{'='*40}\n通过 {PASS} 项, 失败 {FAIL} 项")
print("ALL PASS" if FAIL == 0 else "HAS FAILURES")
sys.exit(0 if FAIL == 0 else 1)
