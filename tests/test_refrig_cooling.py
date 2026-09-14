# -*- coding: utf-8 -*-
"""制冷循环 + 循环冷却水 回归测试
纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_refrig_cooling.py

核对依据：
- R134a 理想循环 (-10°C 蒸发 / 40°C 冷凝, ASHRAE 表):
  P_evap=200.7 kPa, P_cond=1017 kPa, h1≈396.7, h2s≈430.5, h3≈256.5
  q0≈140 kJ/kg, w≈34 kJ/kg, COP≈4.15, Carnot COP=263.15/50=5.263
- 等熵压缩必须用熵迭代 (s2s=s1)；修复前 γ=(cp+R)/R 公式+单位双错 → γ=11.5
  → T2s=885°C、压缩功高估 25 倍、COP≈0.12（毁灭性错误）
- 冷却水: Q=m·cp·ΔT；500 kW×1.2 安全系数 / (4.18×5) = 28.71 kg/s = 103.35 m³/h
  管径推荐按 PIPE_VELOCITY 档位（DN100~200 限 2.5 m/s → DN125@2.34）
- 结晶罐显热 q = M·cp·ΔT/(3600×降温时间)，降温时间默认 1 h
- 搅拌热 95% 转化（保守）；CO₂ 跨临界不支持应阻断而非静默用 R410A
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

_POPUPS = []
def _mk(kind):
    def f(parent=None, title='', text='', *a, **k):
        _POPUPS.append((kind, title, text))
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

# ══════════════════ Part 1: 制冷循环 ══════════════════
m1 = _load('t_refrig', os.path.join(CALC_DIR, 'refrigeration_cycle_calculator.py'))
w = m1.RefrigerationCycleCalculator()

w.cycle_button_group.button(0).setChecked(True)   # 理想循环
w.on_cycle_type_changed()
w.refrigerant_combo.setCurrentIndex(0)            # R134a
w.evap_temp_input.setText("-10")
w.cond_temp_input.setText("40")
w.mass_flow_input.setText("0.1")
w.comp_eff_input.setText("100")
_POPUPS.clear()
w.calculate()
t1 = w.result_text.toPlainText()

check("理想循环: 结果生成", "COP" in t1, t1[:120])
# COP ≈ 4.15~4.35 (等熵迭代)
import re
mm = re.search(r'COP\):\s*([\d.]+)', t1)
cop = float(mm.group(1)) if mm else 0
check("理想循环 COP≈4.15~4.35 (修复前≈0.12)", 4.05 <= cop <= 4.35, f"COP={cop}")
mm = re.search(r'压缩功:\s*([\d.]+)', t1)
w_kg = float(mm.group(1)) if mm else 0
check("单位压缩功≈31~36 kJ/kg (修复前≈950)", 30.0 <= w_kg <= 36.0, f"w={w_kg}")
mm = re.search(r'点2 \(压缩机出口[^\n]*\n\s*温度:\s*([\d.]+)', t1)
T2 = float(mm.group(1)) if mm else 0
check("排气温度 45~80°C (修复前885°C)", 45.0 <= T2 <= 80.0, f"T2={T2}")
check("计算说明含等熵迭代", "等熵迭代" in t1)
mm = re.search(r'制冷量:\s*([\d.]+)', t1)
qc = float(mm.group(1)) if mm else 0
check("制冷量≈14 kW (0.1kg/s×140kJ/kg)", 13.0 <= qc <= 15.0, f"Q0={qc}")
mm = re.search(r'卡诺循环COP:\s*([\d.]+)', t1)
carnot = float(mm.group(1)) if mm else 0
check("卡诺COP=5.263", abs(carnot - 263.15/50.0) < 0.01, f"{carnot}")
mm = re.search(r'循环效率:\s*([\d.]+)', t1)
eta = float(mm.group(1)) if mm else 0
check("循环效率≈78~82%", 75.0 <= eta <= 85.0, f"η={eta}")
mm = re.search(r'干度:\s*([\d.]+)', t1)
x4 = float(mm.group(1)) if mm else -1
check("节流后干度≈0.30~0.35", 0.25 <= x4 <= 0.40, f"x4={x4}")

# 实际循环 (过冷5 过热5, η=80%)
w.cycle_button_group.button(1).setChecked(True)
w.on_cycle_type_changed()
w.subcool_input.setText("5")
w.superheat_input.setText("5")
w.comp_eff_input.setText("80")
w.calculate()
t2 = w.result_text.toPlainText()
mm = re.search(r'COP\):\s*([\d.]+)', t2)
cop80 = float(mm.group(1)) if mm else 0
check("实际循环(η=80%) COP≈3.0~3.7", 3.0 <= cop80 <= 3.7, f"COP={cop80}")
check("实际循环: 过冷/过热度入结果", "过冷度: 5" in t2 and "过热度: 5" in t2)

# CO₂ 阻断
w.refrigerant_combo.setCurrentIndex(5)  # R744 (CO₂)
_POPUPS.clear()
w.calculate()
check("CO₂: 弹警告阻断", len(_POPUPS) > 0 and "跨临界" in _POPUPS[0][2],
      str(_POPUPS[:1]))
check("CO₂: 不产出结果", "COP" not in w.result_text.toPlainText() or "R744" not in w.result_text.toPlainText()[:200])
w.refrigerant_combo.setCurrentIndex(0)

# 历史记录钩子
w.cycle_button_group.button(0).setChecked(True)
w.on_cycle_type_changed()
w.comp_eff_input.setText("100")
hd = w._get_history_data()
check("历史: COP 非零且≈4.15", abs(hd["outputs"]["COP"] - cop) < 0.05, str(hd["outputs"]))

# 报告契约
w.calculate()
rep = w.generate_report()
check("报告: str 且含工程信息", isinstance(rep, str) and "工程编号" in rep)

# ══════════════════ Part 2: 循环冷却水 ══════════════════
m2 = _load('t_cw', os.path.join(CALC_DIR, 'cooling_water_calculator.py'))
cw = m2.CoolingWaterCalculator()

# 换热器模式: 500 kW, 32→37, safety 1.2 → 103.35 m³/h
cw.mode_combo.setCurrentText("换热器")
cw.heat_load_input.setText("500")
cw.cw_tin_input.setText("32")
cw.cw_tout_input.setText("37")
cw.safety_factor_input.setText("1.2")
cw.calculate()
tc = cw.result_text.toPlainText()
check("换热器: 循环水量 103.35 m³/h", "103.35" in tc or "103.3" in tc, tc[tc.find("循环水量"):tc.find("循环水量")+60] if "循环水量" in tc else tc[:200])
check("换热器: 推荐 DN125@2.3m/s (档位流速表)", "DN125" in tc, tc[tc.find("推荐管径"):tc.find("推荐管径")+40] if "推荐管径" in tc else "")

r = cw._last_result
check("手算 m=28.71 kg/s", abs(r["m_cw_kgs"] - 28.71) < 0.05, f"{r['m_cw_kgs']:.3f}")
check("手算 V=103.35 m³/h", abs(r["v_cw_m3h"] - 103.348) < 0.1, f"{r['v_cw_m3h']:.3f}")

# 发酵罐搅拌热 95%
cw.mode_combo.setCurrentText("发酵罐")
cw.ferm_type_combo.setCurrentText("氨基酸发酵(缬氨酸/谷氨酸等)")
cw.heat_rate_input.setText("15")
cw.work_vol_input.setText("100")
cw.stir_power_input.setText("100")
cw.calculate()
tf = cw.result_text.toPlainText()
check("发酵罐: 搅拌热 ×95% 显示", "× 95%" in tf, "")
r = cw._last_result
# q_metab = 15*100*1000/3600 = 416.7 kW; q_stir = 95 kW
check("发酵罐: 代谢热+搅拌热=511.7 kW", abs(r["q_total"] - (416.67 + 95.0)) < 0.5, f"{r['q_total']:.1f}")

# 结晶罐显热降温时间
cw.mode_combo.setCurrentText("结晶罐")
cw.crystal_amount_input.setText("500")
cw.crystal_heat_input.setText("80")
cw.tank_volume_input.setText("10")
cw.material_density_input.setText("1080")
cw.solution_cp_input.setText("3.80")
cw.crystal_dt_input.setText("15")
cw.crystal_hours_input.setText("1.0")
cw.stir_power_input.setText("0")
cw.calculate()
r1 = cw._last_result
# q_sensible = 10*1080*3.8*15/3600 = 171.0 kW; q_crystal = 500*80/3600 = 11.11 kW
check("结晶罐: 显热(1h)=171 kW", abs(r1["q_total"] - (171.0 + 11.11)) < 0.5, f"{r1['q_total']:.2f}")
cw.crystal_hours_input.setText("4.0")
cw.calculate()
r4 = cw._last_result
check("结晶罐: 显热(4h)=42.75 kW", abs(r4["q_total"] - (42.75 + 11.11)) < 0.5, f"{r4['q_total']:.2f}")

# 深冷水低温警示
cw.mode_combo.setCurrentText("换热器")
cw.heat_load_input.setText("100")
cw.cw_preset_combo.setCurrentText("深冷水(进-5°C,出0°C,ΔT=5)")
cw.calculate()
td = cw.result_text.toPlainText()
check("深冷水: 低温载冷剂警示", "盐水" in td, td[tc.find("⚠") if "⚠" in td else 0:][:80])

# 多效蒸发器独立路径 + 历史记录
cw.mode_combo.setCurrentText("多效蒸发器")
cw.evap_effect_combo.setCurrentText("三效蒸发器")
cw.evap_water_input.setText("1000")
cw.evap_dt_input.setText("5")
cw.evap_cp_input.setText("4.18")
cw.calculate()
r = cw._last_result
# coeff = 0.34, latent = 2358 → tt = 0.34*2358/(4.18*5) = 38.32
check("多效蒸发器: t/t≈38.3", abs(r["tt"] - 38.32) < 0.2, f"{r['tt']:.2f}")
check("多效蒸发器: 循环液量≈38320 kg/h", abs(r["total_cw"] - 38320) < 100, f"{r['total_cw']:.0f}")
hd = cw._get_history_data()
check("蒸发器历史: 循环液量非零", hd["outputs"]["循环液量_m3h"] > 30, str(hd["outputs"]))
check("蒸发器历史: 冷却水倍率非零", hd["outputs"]["冷却水倍率_t_t"] > 30, str(hd["outputs"]))

# 报告契约 (含蒸发器模式)
cw.calculate()
rep = cw.generate_report()
check("报告: str 且含工程信息", isinstance(rep, str) and "工程编号" in rep)

# ══════════════════ 汇总 ══════════════════
print()
print(f"总结: {len(PASS)} pass, {len(FAIL)} fail")
if FAIL:
    print("失败项:")
    for name, d in FAIL:
        print(f"  - {name}: {d}")
sys.exit(1 if FAIL else 0)
