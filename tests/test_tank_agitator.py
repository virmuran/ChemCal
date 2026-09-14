# -*- coding: utf-8 -*-
"""罐体/搅拌/法兰类计算器回归测试（搅拌功率&kLa + 罐体重量 + 常压罐壁厚 + 法兰查询）
纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_tank_agitator.py

核对依据：
- 搅拌功率：P0 = Np·ρ·n³·d⁵·层数（默认锚点 5.5×1050×2.5³×1×2 = 180.47 kW）
- 通气功率：Michel & Miller Pg = 0.706·(P0²·n·d³/Q^0.56)^0.45（SI）
  修复前：漏 0.706 系数且错乘在 P0 上 → 数值爆炸 → 被 min(P0·0.7) 钳位成恒 0.7·P0
  锚点：默认参数 Pg ≈ 60.0 kW（≈0.33·P0，工程合理区间 1/3~2/3·P0）
- kLa：van't Riet kLa = 0.026·(Pg/V)^0.4·vs^0.5，vs 单位必须 m/s
  修复前误用 m/h → kLa 偏小 60 倍。锚点：默认参数 kLa ≈ 548 /h
- 需求通气量：OTR ∝ vvm^0.5 → vvm_req = vvm·(OUR/OTRmax)²（修复前线性外推偏不安全）
- 罐体重量（锥体罐锚点 D=3, H=5, t=6, 锥高1.2, 锥口0.1, ρ=7930）：
  筒体 π·D·H·t + 锥台侧 π(R+r)·l·t + 顶盖 πR²·t = 3014.7 kg
  液体（圆台公式 V=(πh/3)(R²+Rr+r²)，修复前漏 Rr+r² 项）= 38267.7 kg
- 球罐液位: h=D 全容积 (4/3)πR³; h=R 半球 (2/3)πR³
- 常压罐壁厚 GB 50341-2014:
  一英尺法 t = 4.9·D·(H−0.3)·G/([σ]·E)；锚点 D=12/H=12/液位11/Q235B(148)/E0.85 → 底圈 5.00mm → 名义 7
  许用应力 [σ]=min(2/3·ReL, 2/5·Rm)，S_t=min(3/4·ReL, 3/7·Rm)（§4.2.2 条文说明）
  修复前 Q235B 157/345R 208 混乱取值；最小壁厚表改为 GB 50341 表 6.3.4（D≤12:5, ≤24:6, ≤60:8, >60:10）
- 法兰：HG/T 20592-2009 PN16 DN100 WN 标准尺寸 D220/K180/L18/8×M16/C20/d158/f2
  修复前 215/24/148 错值 + 线性外推"估算"（DN200 会算出 265 外径，实际 340）
"""
import os
import sys
import math
import tempfile
import importlib.util

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CALC_DIR = os.path.join(ROOT, 'modules', 'chemical_calculations', 'calculators')
for p in [ROOT, os.path.join(ROOT, 'modules'),
          os.path.join(ROOT, 'modules', 'chemical_calculations')]:
    sys.path.insert(0, p)

from PySide6.QtWidgets import QApplication, QMessageBox

def _mk(kind):
    def f(parent=None, title='', text='', *a, **k):
        return QMessageBox.StandardButton.Ok
    return staticmethod(f)
QMessageBox.warning = _mk('warning')
QMessageBox.critical = _mk('critical')
QMessageBox.information = _mk('info')

from data_manager import DataManager
DataManager.get_instance(data_file=os.path.join(tempfile.mkdtemp(), 'test.json'))

app = QApplication(sys.argv)

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

PASS, FAIL = [], []

def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}' + (f'  [{detail}]' if detail and not cond else ''))

# ══════════════════ Part 1: 搅拌功率 & kLa ══════════════════
m1 = _load('t_agitator', os.path.join(CALC_DIR, 'agitator_calculator.py'))
ag = m1.AgitatorCalculator()
ag.calculate()   # 默认：功率模式, V=50, D=3.0, d=1.0, N=150, 2层, ρ=1050, μ=50
r = ag._last_results

check("Re = 52500", abs(r["Re"] - 52500) < 1, f'{r["Re"]}')
check("P0 = 180.47 kW (Np·ρ·n³·d⁵×2)", abs(r["P0_kW"] - 180.469) < 0.1, f'{r["P0_kW"]}')

# Michel-Miller: Pg = 0.706·(P0²·n·d³/Q^0.56)^0.45, Q=50/60 m³/s → ≈60.0 kW
check("Pg ≈ 60.0 kW (Michel-Miller)", 50 < r["Pg_kW"] < 70, f'{r["Pg_kW"]}')
check("Pg < P0 (物理上限)", r["Pg_kW"] < r["P0_kW"])

# kLa: vs = (50/60)/(π·9/4) = 0.11790 m/s; 0.026·(1201)^0.4·0.11790^0.5 ≈ 0.1522 /s → 548 /h
ag.mode_btns["kLa 传氧系数"].setChecked(True)
ag._group_aeration.setVisible(True)
ag.calculate()
rk = ag._last_results
check("vs = 0.118 m/s", abs(rk["vs_m_s"] - 0.11789) < 0.001, f'{rk["vs_m_s"]}')
check("kLa ≈ 548 /h (van't Riet, vs 用 m/s)", 450 < rk["kLa_per_h"] < 650, f'{rk["kLa_per_h"]}')
check("OTRmax ≈ 122 mmol/(L·h)", 100 < rk["OTR_max"] < 145, f'{rk["OTR_max"]}')
# OUR=100 → vvm_req = 1.0×(100/OTR)² ≈ 0.67（平方外推）
check("需求通气量 ≈ 0.67 vvm (平方外推)", 0.5 < rk["q_vvm_req"] < 0.85, f'{rk["q_vvm_req"]}')

# 清空后重算不崩（修复前 Q=0 → ZeroDivisionError），且恢复默认值
ag.clear_all()
ag.mode_btns["搅拌功率计算"].setChecked(True)
ag.calculate()
r2 = ag._last_results
check("clear_all 后重算不除零", abs(r2.get("P0_kW", 0) - 180.469) < 0.1, str(r2))
check("clear_all 恢复默认体积 50", ag.volume_input.text() == "50", ag.volume_input.text())

# ══════════════════ Part 2: 罐体重量 ══════════════════
m2 = _load('t_tank_weight', os.path.join(CALC_DIR, 'tank_weight_calculator.py'))
tw = m2.罐体重量()

# 锥体罐壳体（手算锚点 3014.7 kg）
w_shell = tw.calculate_cone_tank_weight(3.0, 5.0, 0.006, 1.2, 0.1, 7930)
check("锥体罐壳体 3014.7 kg", abs(w_shell - 3014.7) < 1.0, f'{w_shell:.1f}')

# 锥体液体（圆台公式含 Rr+r² 项 → 38267.7 kg；旧纯锥公式 37070）
w_liq = tw.calculate_cone_liquid_weight(3.0, 5.0, 1.2, 0.1, 1000)
check("锥体罐液体 38267.7 kg (圆台)", abs(w_liq - 38267.7) < 2.0, f'{w_liq:.1f}')

# 球罐液体：h=D 满球, h=R 半球
check("球罐 h=D 满球 14137 kg", abs(tw.calculate_sphere_liquid_weight(3.0, 3.0, 1000) - 14137.2) < 1.0)
check("球罐 h=R 半球 7068.6 kg", abs(tw.calculate_sphere_liquid_weight(3.0, 1.5, 1000) - 7068.6) < 1.0)

# 卧式罐液位 h=R 弓形=半圆
check("卧式罐 h=R 半筒", abs(tw.calculate_horizontal_liquid_weight(3.0, 5.0, 1.5, 1000) - 17671.5) < 1.0)

# 默认（锥体罐）整体计算 → 结果量级正常（修复前 clear_inputs 填米值 → 结果缩小 1e9 倍）
tw.calculate_weight()
txt = tw.result_text.toPlainText()
check("默认锥体罐空重 ≈ 3014.7 kg", "3,014.7 kg" in txt or "3,014.6 kg" in txt, txt[:400])

# 清空恢复 mm 默认值
tw.clear_inputs()
check("clear 后直径恢复 3000 mm", tw.diameter_input.text() == "3000", tw.diameter_input.text())
tw.calculate_weight()
check("clear 后重算量级正常", "总重量" in tw.result_text.toPlainText() and "kg" in tw.result_text.toPlainText())

# 球罐历史记录读球壁厚（修复前误读 shell_thickness_input）
tw.sphere_thickness_input.setText("8")
btns = tw.type_button_group.buttons()
for b in btns:
    if b.text() == "球罐":
        b.setChecked(True)
tw.on_tank_type_changed(b)
hist = tw._get_history_data()
check("球罐历史用 sphere_thickness (t=8mm→1793.7kg)",
      abs(hist["outputs"]["罐体重量_kg"] - 1793.7) < 1.0, str(hist["outputs"]))

# ══════════════════ Part 3: 常压罐壁厚 (GB 50341) ══════════════════
m3 = _load('t_atm_tank', os.path.join(CALC_DIR, 'atmospheric_tank_thickness_calculator.py'))
at = m3.AtmosphericTankThicknessCalculator()

# 初始许用应力自动填充（修复前 addItems 早于 connect → 初始为空）
check("初始许用应力自动填充 148", at._input_widgets["allowable_stress_d"].text() == "148",
      at._input_widgets["allowable_stress_d"].text())

w = at._input_widgets
w["tank_diameter"].setText("12")
w["tank_height"].setText("12")
w["liquid_level"].setText("11")
w["num_courses"].setText("6")
at.calculate()
txt = at.result_text.toPlainText()
# 底圈: t = 4.9·12·10.7·1.0/(148·0.85) = 5.001 → +1.5 → 名义 7
check("底圈计算壁厚 5.00 mm (一英尺法)", "5.001" in txt or "5.000" in txt, txt[:600])
check("底圈名义壁厚 7 mm", "7.0" in txt, txt)
# GB 50341 表 6.3.4: D=12 → 最小 5 mm
check("最小壁厚(不含CA) 5mm", "5mm" in txt, txt)

# 材质切换 → Q345R 204（GB 50341/API 650 规则）
w["material_grade"].setCurrentText("Q345R")
check("Q345R S_d = 204", w["allowable_stress_d"].text() == "204", w["allowable_stress_d"].text())
check("Q345R S_t = 219", w["allowable_stress_t"].text() == "219", w["allowable_stress_t"].text())

# NB/T 47003 模式：压力组显示 + 复核提醒
w["standard"].setCurrentText("NB/T 47003.1-2009  (压力容器·圆筒公式)")
check("NB 模式压力组可见", not at.pressure_group.isHidden())
w["tank_diameter"].setText("2")
w["tank_height"].setText("2")
w["liquid_level"].setText("1.8")
w["num_courses"].setText("1")
w["design_pressure_pc"].setText("0.1")
at.calculate()
txt = at.result_text.toPlainText()
check("NB 模式输出许用应力复核提醒", "GB/T 150.2" in txt, txt[:400])
# 常温取值提示（两种模式都有）
check("常温取值提示", "常温取值" in txt, txt[:300])

# clear 后 standard/tank_type 复位、许用应力重新填充
at.clear()
check("clear 后标准复位 GB 50341", at._input_widgets["standard"].currentIndex() == 0)
check("clear 后许用应力重填 148", at._input_widgets["allowable_stress_d"].text() == "148")

# 导出契约
at._input_widgets["tank_diameter"].setText("12")
at._input_widgets["tank_height"].setText("12")
at._input_widgets["liquid_level"].setText("11")
at.calculate()
rep = at.generate_report()
check("generate_report 返回 str 且非空壳", isinstance(rep, str) and len(rep) > 200, f'len={len(rep) if isinstance(rep,str) else type(rep)}')
info = at.get_project_info()
check("get_project_info 返回 dict", isinstance(info, dict))

# （Part 4 法兰查询已随模块删除移除：flange_size_calculator 为空壳演示模块
#   （数据仅 4 条 DN100、螺栓计算无视 DN），2026-09-14 经用户确认删除；
#   法兰外径权威数据保留在 pipe_spacing_calculator（PN10~100 × DN10~500））

# ══════════════════ 汇总 ══════════════════
print("\n" + "=" * 50)
print(f"通过 {len(PASS)} 项, 失败 {len(FAIL)} 项")
if FAIL:
    print("失败项:")
    for name, detail in FAIL:
        print(f"  ✗ {name}  [{detail}]")
sys.exit(1 if FAIL else 0)
