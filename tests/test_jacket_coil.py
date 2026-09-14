# -*- coding: utf-8 -*-
"""夹套/盘管换热计算器回归测试（搅拌釜关联式 + Dittus-Boelter + K 组装）
在测试中按相同公式复算并与结果区比对（单位一致性闭环），关键锚点手算闭合。
运行: tests/test_jacket_coil.py
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
DataManager.get_instance(data_file=os.path.join(os.environ.get("TEMP", "/tmp"), "chemcal_test_jc.json"))

from PySide6.QtWidgets import QApplication, QMessageBox
app = QApplication.instance() or QApplication(sys.argv)
for name in ("warning", "critical", "information", "question"):
    setattr(QMessageBox, name, (lambda n: (lambda *a, **k: QMessageBox.StandardButton.Ok))(name))

import jacket_coil_calculator as mod
from jacket_coil_calculator import JacketCoilCalculator
from common_constants import get_steam_props, WATER_CP, WATER_DENSITY

PASS, FAIL = 0, 0
def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")

def result_num(text, label):
    """从结果区取 '标签: 数值' 形式的数"""
    for line in text.splitlines():
        if label in line:
            for tok in line.replace(":", ":").split():
                try:
                    return float(tok.replace(",", ""))
                except ValueError:
                    continue
    return None

w = JacketCoilCalculator()

# ══ 夹套模式 · 蒸汽加热（默认参数）══
txt = ""
w.calculate()
txt = w.result_text.toPlainText()
# 默认: D=1.6, H/D=2.0 → H=3.2; ratio=0.75 → H_j=2.4
A_exp = math.pi * 1.6 * (3.2 * 0.75) + math.pi * 1.6**2 / 4
check(f"夹套 可用面积={A_exp:.2f} m²（手算闭合）", f"{A_exp:.2f}" in txt, txt[:200])
# 蒸汽 0.3 MPa(g): Ts=143.7, 釜内 60 → LMTD=83.7（等温冷凝）
props = get_steam_props(0.3)
check(f"夹套 LMTD={props['sat_temp']-60:.1f} °C（蒸汽等温）", f"{props['sat_temp']-60:.1f}" in txt)

# 复算搅拌侧给热系数（默认 水, D=1.6, d_i=0.53, n=120 rpm）
mdata = mod.VESSEL_MEDIA["水"]
rho, cp, k_v, mu = mdata["rho"], mdata["cp"], mdata["k"], mdata["mu"]
Re = rho * (120 / 60) * 0.53**2 / mu
Pr = cp * 1000 * mu / k_v
Nu = 0.36 * Re**0.67 * Pr**0.33
h_i_exp = Nu * k_v / 1.6
hi_got = result_num(txt, "釜内侧 h_i")
check(f"搅拌侧 h_i={h_i_exp:.0f}（关联式复算一致）",
      hi_got is not None and abs(hi_got - h_i_exp) < 1, f"exp={h_i_exp:.1f} got={hi_got}")

# ══ 夹套模式 · 热水加热（手工闭合案例）══
w.inputs["media_type"].setCurrentText([k for k in mod.MEDIA_TYPES if "水" in k][0])
w.inputs["media_in_temp"].setText("80")
w.inputs["media_out_temp"].setText("50")
w.inputs["media_flow"].setText("5000")
w.inputs["vessel_temp"].setText("20")
w.inputs["diameter"].setText("1.0")
w.inputs["aspect_ratio"].setText("1.0")
w.inputs["jacket_height_ratio"].setText("0.8")
w.inputs["impeller_d"].setText("0.35")
w.inputs["impeller_n"].setText("100")
w.inputs["wall_thickness"].setText("0.008")
w.inputs["wall_lambda"].setText("50")
w.inputs["fouling_inner"].setText("0.0002")
w.inputs["fouling_outer"].setText("0.0002")
w.inputs["safety_factor"].setText("1.1")
w.calculate()
txt = w.result_text.toPlainText()

# 手工复算（物性取 VESSEL_MEDIA["水"] 表值）
D, H = 1.0, 1.0
A_exp = math.pi * D * (H * 0.8) + math.pi * D**2 / 4      # 3.299
Q_exp = 5000 * WATER_CP * 30 / 3600                        # kW
dT1, dT2 = 80 - 20, 50 - 20
LMTD_exp = (dT1 - dT2) / math.log(dT1 / dT2)               # 43.28
k_v, mu_v = 0.599, 1.005e-3                                # VESSEL_MEDIA["水"]
Re_i = WATER_DENSITY * (100 / 60) * 0.35**2 / mu_v
Pr_i = WATER_CP * 1000 * mu_v / k_v
h_i_exp = 0.36 * Re_i**0.67 * Pr_i**0.33 * k_v / D
gap = 0.05
v = 5000 / (3600 * WATER_DENSITY * math.pi * D * gap)
Re_o = WATER_DENSITY * v * 2 * gap / 0.001
Pr_o = WATER_CP * 1000 * 0.001 / 0.6
h_o_exp = 0.023 * Re_o**0.8 * Pr_o**0.4 * 0.6 / (2 * gap)
K_exp = 1 / (1 / h_i_exp + 0.008 / 50 + 1 / h_o_exp + 0.0004)
A_req_exp = Q_exp * 1000 / (K_exp * LMTD_exp) * 1.1

check(f"夹套热水 可用面积={A_exp:.3f} m²", f"{A_exp:.3f}" in txt)
check(f"夹套热水 热负荷={Q_exp:.1f} kW（手算闭合）", f"{Q_exp:.1f}" in txt)
check(f"夹套热水 LMTD={LMTD_exp:.1f} °C", f"{LMTD_exp:.1f}" in txt)
hi_got = result_num(txt, "釜内侧 h_i")
check("夹套热水 h_i 关联式复算一致", hi_got is not None and abs(hi_got - h_i_exp) < 1,
      f"exp={h_i_exp:.1f} got={hi_got}")
ho_got = result_num(txt, "介质侧 h_o")
check("夹套热水 h_o Dittus-Boelter 复算一致", ho_got is not None and abs(ho_got - h_o_exp) < 1,
      f"exp={h_o_exp:.1f} got={ho_got}")
k_got = result_num(txt, "总传热系数 K")
check("夹套热水 K 组装复算一致（含污垢热阻）", k_got is not None and abs(k_got - K_exp) < 1,
      f"exp={K_exp:.1f} got={k_got}")
ar_got = result_num(txt, "所需换热面积 A")
check("夹套热水 所需面积复算一致", ar_got is not None and abs(ar_got - A_req_exp) < 0.05,
      f"exp={A_req_exp:.2f} got={ar_got}")
check("夹套热水 低流速 Re 警告出现（v≈0.009 m/s → Re≈884）",
      "层流/过渡区" in txt or "Re≈" in txt)

# ══ 盘管模式 · 蒸汽加热（恢复默认几何）══
btns = w.mode_group.buttons()
btns[0].setChecked(False)
btns[1].setChecked(True)
w.inputs["diameter"].setText("1.6")
w.inputs["aspect_ratio"].setText("2.0")
w.inputs["media_type"].setCurrentText([k for k in mod.MEDIA_TYPES if "蒸汽" in k][0])
w.inputs["steam_pressure"].setText("0.3")
w.inputs["vessel_temp"].setText("60")
w.calculate()
txt = w.result_text.toPlainText()
# 盘管几何: D=1.6, H=3.2, H_eff=2.24, pitch=0.08 → 28圈; L=28×π×1.2=105.6 m
n_coils = 3.2 * 0.7 / 0.08
L_coil = n_coils * math.pi * 1.2
do = 0.057
A_exp = math.pi * do * L_coil
check(f"盘管 可用面积={A_exp:.2f} m²（手算闭合）", f"{A_exp:.2f}" in txt, txt[:300])
check(f"盘管 圈数={n_coils:.0f}", f"{n_coils:.0f}" in txt)
# 蒸汽 LMTD = 143.7-60 = 83.7
check("盘管 蒸汽 LMTD=83.7 °C", f"{props['sat_temp']-60:.1f}" in txt)

# ══ 盘管内给热系数（弯曲修正 1+3.5d/Dc，热水介质）══
w.inputs["media_type"].setCurrentText([k for k in mod.MEDIA_TYPES if "热水" in k][0])
w.inputs["media_in_temp"].setText("95")
w.inputs["media_out_temp"].setText("70")
w.inputs["media_flow"].setText("5000")
w.calculate()
txt = w.result_text.toPlainText()
# 介质水 5000 kg/h, di=0.053: v≈6.29 m/s, Re≈3.3e5 湍流
di = 0.057 - 0.004
v_c = 5000 / (3600 * WATER_DENSITY * math.pi * di**2 / 4)
Re_c = WATER_DENSITY * v_c * di / 0.001
Pr_c = WATER_CP * 1000 * 0.001 / 0.6
Nu_c = 0.023 * Re_c**0.8 * Pr_c**0.4 * (1 + 3.5 * di / 1.2)
h_o_exp = Nu_c * 0.6 / di
ho_got = result_num(txt, "介质侧 h_o")
check("盘管内 h_o（含弯曲修正）复算一致",
      ho_got is not None and abs(ho_got - h_o_exp) / h_o_exp < 0.01,
      f"exp={h_o_exp:.0f} got={ho_got}")
# 热负荷闭合: Q=5000×4.187×25/3600=145.1 kW
Q_coil_exp = 5000 * WATER_CP * 25 / 3600
check(f"盘管热水 热负荷={Q_coil_exp:.1f} kW（手算闭合）", f"{Q_coil_exp:.1f}" in txt)

# ══ 自然对流路径（无搅拌）══
w.inputs["impeller_d"].setText("0")
w.inputs["impeller_n"].setText("0")
w.calculate()
check("无搅拌时走自然对流路径不崩溃", "总传热系数" in w.result_text.toPlainText())

# ══ 导出契约 ══
rep = w.generate_report()
check("generate_report 返回 str 或 None", rep is None or isinstance(rep, str))
info = w.get_project_info()
check("get_project_info 返回 dict", isinstance(info, dict))

print(f"\n{'='*40}\n通过 {PASS} 项, 失败 {FAIL} 项")
print("ALL PASS" if FAIL == 0 else "HAS FAILURES")
sys.exit(0 if FAIL == 0 else 1)
