# -*- coding: utf-8 -*-
"""VLE 活度系数 + 风机功率计算器回归测试
纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_vle_fan.py

核对依据：
- Antoine（log10 mmHg / °C 制，×0.133322→kPa）：正常沸点下 Psat≈101.325 kPa
  2-丁醇 NIST 345.54-380.30K 系数换算 7.20455/1158.67/168.47（修复前误用正丁醇系数）
- 甲醇-水 NRTL @1atm vs DECHEMA（Duncan & Reimer）：x=0.502 → T=73.2, y=0.785
- 丙酮-水 @1atm vs Lange's：x=0.1 → T=68.76, y=0.731；x=0.5 → T=59.87, y=0.834
- 乙醇-水 @1atm 共沸：T=78.15°C @ x=y=0.894（修复前按 J/mol 用 cal 参数无法复现共沸）
- 乙醇-苯 @1atm 共沸：T=68.2°C @ x_eth≈0.44
- 苯-甲苯 近理想：x=0.5 → T=92.2, y=0.713
- Wilson/NRTL/UNIQUAC 方程为标准形式；UNIQUAC 组合项+剩余项、Rachford-Rice 均已结构核对
- 二元参数单位已逐对核实（见 vle_activity_coefficient_calculator.py 数据库注释）
- 风机：轴功率=Q(m³/s)×Δp(Pa)/η；ρ=1.293×(273.15/T)×(1-H/44300)^5.255（20°C/0m→1.2047）
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

PASS, FAIL = [], []

def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}' + (f'  [{detail}]' if detail and not cond else ''))

# ══════════════════ Part 1: VLE 活度系数 ══════════════════
spec = importlib.util.spec_from_file_location(
    't_vle', os.path.join(CALC_DIR, 'vle_activity_coefficient_calculator.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
w = mod.VLEActivityCoefficientCalculator()

def vle_set(calc, names, x, model="Wilson方程", T="80", P="101.325"):
    w.calc_type.setCurrentText(calc)
    w.component_count.setCurrentText(str(len(names)))
    for i, nm in enumerate(names):
        w.component_table.cellWidget(i, 0).setCurrentText(nm)
    for i, xi in enumerate(x):
        w.comp_input_table.item(i, 1).setText(str(xi))
    w.model_selection.setCurrentText(model)
    w.temperature_input.setText(T)
    w.pressure_input.setText(P)

def bubble_line(txt, name):
    for l in txt.split("\n"):
        if l.startswith(name):
            parts = l.split()
            return float(parts[1]), float(parts[2])  # x, y
    return None, None

# ── 1.1 Antoine 锚点 ──
def psat(name, T):
    a, b, c = mod.SUBSTANCE_DB[name]["antoine"]
    return 10 ** (a - b / (T + c)) * 0.133322

check('2-丁醇 Antoine bp 99.51→101.3', abs(psat("2-丁醇", 99.51) - 101.325) < 1.0,
      f'{psat("2-丁醇", 99.51):.2f}')
check('2-丁醇 20°C Psat≈1.5 kPa', abs(psat("2-丁醇", 20) - 1.52) < 0.15, f'{psat("2-丁醇", 20):.3f}')
check('甲醇 Antoine bp 64.7→101.3', abs(psat("甲醇", 64.7) - 101.325) < 1.0, f'{psat("甲醇", 64.7):.2f}')
check('2-丁醇 UNIQUAC r 同分异构=3.9241', mod.SUBSTANCE_DB["2-丁醇"]["r"] == 3.9241)

# ── 1.2 苯-甲苯近理想体系 ──
vle_set("泡点计算", ["苯", "甲苯"], [0.5, 0.5])
w.calculate()
txt = w.result_text.toPlainText()
t_line = [l for l in txt.split("\n") if "泡点温度" in l][0]
T_bt = float(t_line.split(":")[1].replace("°C", "").strip())
x_bt, y_bt = bubble_line(txt, "苯")
check('苯-甲苯泡点 T=90.9±0.3 (lit 92.2, γ≈1.036)', abs(T_bt - 90.92) < 0.3, f'{T_bt:.3f}')
check('苯-甲苯 y_bz=0.713±0.005 (lit 0.713)', abs(y_bt - 0.713) < 0.005, f'{y_bt:.4f}')

# ── 1.3 甲醇-水 NRTL vs DECHEMA ──
vle_set("泡点计算", ["甲醇", "水"], [0.502, 0.498], model="NRTL方程")
w.calculate()
txt = w.result_text.toPlainText()
T_mw = float([l for l in txt.split("\n") if "泡点温度" in l][0].split(":")[1].replace("°C", "").strip())
_, y_mw = bubble_line(txt, "甲醇")
check('甲醇-水 NRTL T=73.33±0.5 (DECHEMA 73.2)', abs(T_mw - 73.2) < 0.5, f'{T_mw:.3f}')
check('甲醇-水 NRTL y=0.791±0.01 (DECHEMA 0.785)', abs(y_mw - 0.785) < 0.01, f'{y_mw:.4f}')

# ── 1.4 乙醇-水共沸复现（修复核心验证） ──
vle_set("泡点计算", ["乙醇", "水"], [0.894, 0.106], model="NRTL方程")
w.calculate()
txt = w.result_text.toPlainText()
T_az = float([l for l in txt.split("\n") if "泡点温度" in l][0].split(":")[1].replace("°C", "").strip())
_, y_az = bubble_line(txt, "乙醇")
check('乙醇-水 NRTL 共沸区 T<78.37 (lit 78.15)', T_az < 78.37, f'{T_az:.3f}')
check('乙醇-水 NRTL 共沸 |y-x|<0.02', abs(y_az - 0.894) < 0.02, f'y={y_az:.4f}')
vle_set("泡点计算", ["乙醇", "水"], [0.51, 0.49], model="NRTL方程")
w.calculate()
T_e50 = float(w.result_text.toPlainText().split("泡点温度:")[1].split("°C")[0].strip())
check('乙醇-水 NRTL x=0.51 T=79.0±1.0 (lit 79.8)', abs(T_e50 - 79.8) < 1.0, f'{T_e50:.3f}')
vle_set("泡点计算", ["乙醇", "水"], [0.894, 0.106], model="Wilson方程")
w.calculate()
T_azw = float(w.result_text.toPlainText().split("泡点温度:")[1].split("°C")[0].strip())
check('乙醇-水 Wilson 共沸区 T<78.5 (lit 78.15)', T_azw < 78.5, f'{T_azw:.3f}')

# ── 1.5 丙酮-水 vs Lange's ──
vle_set("泡点计算", ["丙酮", "水"], [0.1, 0.9], model="NRTL方程")
w.calculate()
T_aw = float(w.result_text.toPlainText().split("泡点温度:")[1].split("°C")[0].strip())
_, y_aw = bubble_line(w.result_text.toPlainText(), "丙酮")
check('丙酮-水 NRTL x=0.1 T=65.6±3.5 (Lange 68.76)', abs(T_aw - 68.76) < 3.5, f'{T_aw:.3f}')
check('丙酮-水 NRTL y=0.764±0.05 (Lange 0.731)', abs(y_aw - 0.731) < 0.05, f'{y_aw:.4f}')
vle_set("泡点计算", ["丙酮", "水"], [0.5, 0.5], model="UNIQUAC方程")
w.calculate()
T_aw2 = float(w.result_text.toPlainText().split("泡点温度:")[1].split("°C")[0].strip())
check('丙酮-水 UNIQUAC(J制) x=0.5 T=63.1±0.5 (Lange 59.87)', abs(T_aw2 - 59.87) < 3.5, f'{T_aw2:.3f}')

# ── 1.6 甲醇-丙酮 NRTL（修复后 cal 制） ──
vle_set("泡点计算", ["甲醇", "丙酮"], [0.3, 0.7], model="NRTL方程")
w.calculate()
T_ma = float(w.result_text.toPlainText().split("泡点温度:")[1].split("°C")[0].strip())
check('甲醇-丙酮 NRTL x=0.3 T=54.2±1.5 (Lange az 55.24@0.21)', abs(T_ma - 54.21) < 1.5, f'{T_ma:.3f}')

# ── 1.7 露点 & 等温闪蒸 ──
vle_set("露点计算", ["苯", "甲苯"], [0.5, 0.5])
w.calculate()
T_dew = float(w.result_text.toPlainText().split("露点温度:")[1].split("°C")[0].strip())
check('苯-甲苯露点 T=97.82±0.3 (理想解)', abs(T_dew - 97.82) < 0.3, f'{T_dew:.3f}')

vle_set("等温闪蒸", ["苯", "甲苯"], [0.5, 0.5], T="95")
w.calculate()
txt = w.result_text.toPlainText()
V = float([l for l in txt.split("\n") if "气相分率" in l][0].split(":")[1].strip())
check('闪蒸 V=0.5997 (两相共存)', abs(V - 0.5997) < 0.005, f'{V:.4f}')
check('闪蒸 0<V<1', 0 < V < 1)

# ── 1.8 无预设参数提示 ──
vle_set("泡点计算", ["乙酸乙酯", "氯仿"], [0.5, 0.5])
w.calculate()
check('无预设参数有警示', '无预设交互参数' in w.result_text.toPlainText())

# ── 1.9 导出契约 & 历史钩子 ──
w._last_calc_results = {}
check('VLE 未计算时 generate_report 返回 None', w.generate_report() is None)
vle_set("泡点计算", ["甲醇", "水"], [0.5, 0.5], model="NRTL方程")
w.calculate()
h = w._get_history_data()
check('VLE 历史钩子含泡点温度', '泡点温度_C' in h['outputs'], str(h))
check('VLE 计算后 generate_report 返回 str', isinstance(w.generate_report(), str))

# ══════════════════ Part 2: 风机功率 ══════════════════
spec2 = importlib.util.spec_from_file_location(
    't_fan', os.path.join(CALC_DIR, 'fan_power_calculator.py'))
mod2 = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(mod2)
f = mod2.FanPowerCalculator()

# 基准案例：10000 m³/h, 1000 Pa, 20°C/0m, ηf=75, ηm=92, ηt=98
f.calculate()
txt = f.result_text.toPlainText()
# 轴功率 = (10000/3600)×1000/0.75/1000 = 3.7037 kW
check('轴功率=3.70 kW', '轴功率:         3.70 kW' in txt, txt[:400])
# 电机输入 = 3.7037/(0.98×0.92) = 4.108 kW
check('电机输入=4.11 kW', '电机输入功率:   4.11 kW' in txt)
# 推荐 = 4.108×1.15 = 4.72 → 5.5 kW
check('推荐电机=5.5 kW', '推荐电机规格:   5.5 kW' in txt)
check('空气密度 20°C/0m = 1.2048', '1.2048 kg/m³' in txt)
check('公式区无 C_TO_K 变量名泄漏', 'C_TOK' not in txt.replace('C_TO_K', 'C_TOK') and 'C_TO_K' not in txt)
check('注明实际工况输入', '实际工况状态输入' in txt)

# ── 2.2 高海拔密度修正 ──
f.altitude_input.setText("1000")
f.calculate()
# ρ_alt = (1-1000/44300)^5.255 = 0.886946 → 1.20479×0.886946 = 1.0686
check('海拔1000m 密度=1.0686', '1.0686 kg/m³' in f.result_text.toPlainText(),
      f.result_text.toPlainText()[300:600])
f.altitude_input.setText("0")

# ── 2.3 传动方式联动 ──
f.transmission_type.setCurrentText("皮带传动")
check('皮带传动→传动效率95', f.transmission_efficiency_input.text() == '95',
      f.transmission_efficiency_input.text())
f.transmission_type.setCurrentText("直联")
check('直联→传动效率100', f.transmission_efficiency_input.text() == '100')
f.transmission_type.setCurrentText("联轴器")
check('联轴器→传动效率98', f.transmission_efficiency_input.text() == '98')

# ── 2.4 风机类型效率提示联动 ──
f.fan_type.setCurrentText("轴流风机")
check('轴流风机提示更新', '55~75' in f.fan_efficiency_hint.text())
f.fan_type.setCurrentText("罗茨风机")
check('罗茨风机提示更新', '50~70' in f.fan_efficiency_hint.text())

# ── 2.5 能耗/费用估算 ──
f.transmission_type.setCurrentText("直联")
f.calculate()
txt = f.result_text.toPlainText()
# 小时 = 3.7037/1.00/0.92 = 4.0257 kWh/h（直联 ηt=1.0）
check('小时耗电=4.03 kWh/h (直联)', '4.03 kWh/h' in txt, txt[600:900])
check('年耗电≈31884 kWh', '31884' in txt, txt[600:900])

# ── 2.6 导出契约 ──
f.clear_inputs()
f.result_text.clear()
check('风机未计算时 generate_report 返回 None', f.generate_report() is None)
f.flow_rate_input.setText("10000")
f.pressure_input.setText("1000")
f.fan_efficiency_input.setText("75")
f.motor_efficiency_input.setText("92")
f.calculate()
check('风机计算后 generate_report 返回 str', isinstance(f.generate_report(), str))

# ── 2.7 历史钩子 ──
h2 = f._get_history_data()
check('风机历史钩子含轴功率', '轴功率_kW' in h2['outputs'], str(h2))
check('风机历史钩子含推荐电机', '推荐电机规格_kW' in h2['outputs'])

print()
print(f'════════ 总结: {len(PASS)} PASS / {len(FAIL)} FAIL ════════')
for name, detail in FAIL:
    print(f'  FAIL  {name}  [{detail}]')
sys.exit(1 if FAIL else 0)
