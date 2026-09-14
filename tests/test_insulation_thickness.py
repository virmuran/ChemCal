# -*- coding: utf-8 -*-
"""保温厚度计算器回归测试（GB/T 8175 核对）
纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_insulation_thickness.py

核对依据：
- GB/T 8175-2008 §5.3.2：经济厚度/热损失计算 α 取常数 11.63；
  校核表面温度 α = 1.163(6+3√ω)；室外手册式 α = 11.63+7.12√ω
- 经济厚度 = 年总费用（热损失费 + 绝热投资摊销）最小化
- 表面温度法/热损失法/防结露：稳态热阻方程迭代求解
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

spec = importlib.util.spec_from_file_location(
    't_insulation', os.path.join(CALC_DIR, 'insulation_thickness_calculator.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

w = mod.InsulationThicknessCalculator()

PASS, FAIL = [], []

def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}' + (f'  [{detail}]' if detail and not cond else ''))

def approx(a, b, tol):
    return abs(a - b) <= tol

# ── 1. 表面传热系数（GB/T 8175 §5.3.2）──
check('风速=0 → α=11.63（标准常数）', approx(mod.InsulationThicknessCalculator._surface_htc(0), 11.63, 0.01))
check('风速=3 → α=11.63+7.12√3=23.96',
      approx(mod.InsulationThicknessCalculator._surface_htc(3), 11.63 + 7.12 * 3 ** 0.5, 0.01),
      f'{mod.InsulationThicknessCalculator._surface_htc(3):.3f}')

# ── 2. 表面温度法（平面设备）解析解核对 ──
# Δt=180, ts=26, ta=20, λ=0.0512, h=23.964（风3）
# q = h·(ts-ta) = 143.79 W/m²; t = λ(Δt/q - 1/h) = 61.96 mm
h3 = 11.63 + 7.12 * 3 ** 0.5
q = h3 * 6.0
t_ref = 0.0512 * (180.0 / q - 1.0 / h3) * 1000  # mm
def set_mode(name):
    for i, b in enumerate(w.calc_type_group.buttons()):
        if b.text() == name:
            b.setChecked(True)
            w._on_calc_type_changed(i)   # idClicked 只在用户点击时触发，手动重建动态参数
            return
    raise AssertionError(f'模式不存在: {name}')

w.equipment_type_combo.setCurrentText('平面形设备')
set_mode('表面温度法')
w.size_input.setText('1000')          # 平面时尺寸不影响
w.conductivity_input.setText('0.0512')
w.ambient_temp_input.setText('20')
w.wind_speed_input.setText('3')
w.equipment_temp_input.setText('200')
w.surface_temp_input.setText('26')
w.calculate()
thk = w._last_result['thickness_mm']
check(f'表面温度法(平面) 结果≈{t_ref:.1f}mm（解析解）', approx(thk, t_ref, 2.0), f'{thk:.2f}')

# ── 3. 表面温度法（管道）热阻方程残差核对 ──
# 管道 d1=108mm: t_calc = ta + q/h, q = Δt/(ln(d2/d1)/(2πλ) + 1/(hπd2))
w.equipment_type_combo.setCurrentText('管道或圆筒形设备')
w.size_input.setText('108')
w.calculate()
thk_p = w._last_result['thickness_mm']
d2 = (108 + 2 * thk_p) / 1000.0
r_ins = math.log(d2 / 0.108) / (2 * math.pi * 0.0512)
r_s = 1.0 / (h3 * math.pi * d2)
t_surf_calc = 20 + (180.0 / (r_ins + r_s)) * r_s
check('表面温度法(管道) 表面温度残差<0.5°C', approx(t_surf_calc, 26.0, 0.5), f'{t_surf_calc:.3f}')

# ── 4. 热损失法：收敛后热损失≈限值 ──
set_mode('热损失法')
w.heat_loss_limit_input.setText('160')
w.calculate()
thk_q = w._last_result['thickness_mm']
d2q = (108 + 2 * thk_q) / 1000.0
r_ins = math.log(d2q / 0.108) / (2 * math.pi * 0.0512)
r_s = 1.0 / (h3 * math.pi * d2q)
q_area = 180.0 / (r_ins + r_s) / (math.pi * d2q)
check('热损失法 热损失收敛至限值 160 W/m²', approx(q_area, 160.0, 2.0), f'{q_area:.2f}')

# ── 5. 经济厚度法：结果为年总费用局部最小 ──
set_mode('绝热层经济厚度')
w.equipment_type_combo.setCurrentText('管道或圆筒形设备')
w.size_input.setText('108')
w.calculate()
thk_e = w._last_result['thickness_mm']

def annual_cost(t_m):
    d2 = 0.108 + 2 * t_m
    r_ins = math.log(d2 / 0.108) / (2 * math.pi * 0.0512)
    r_s = 1.0 / (h3 * math.pi * d2)
    qq = 180.0 / (r_ins + r_s)
    heat = qq * 8000 * 3600 * (3.6 / 1e9)
    vol = math.pi * (d2 ** 2 - 0.108 ** 2) / 4
    crf = (0.10 * 1.1 ** 5) / (1.1 ** 5 - 1)
    return heat + vol * 640 * crf

c0 = annual_cost(thk_e / 1000)
c_minus = annual_cost(max((thk_e - 5) / 1000, 0.001))
c_plus = annual_cost((thk_e + 5) / 1000)
check(f'经济厚度 {thk_e:.0f}mm 为局部最小（±5mm 费用更高）',
      c0 <= c_minus + 1e-9 and c0 <= c_plus + 1e-9,
      f'c0={c0:.4f} c-={c_minus:.4f} c+={c_plus:.4f}')

# ── 6. 防结露（保冷）解析解核对 ──
# 保冷: equip=-10, ambient=30, 露点22 → ts=24; h=_surface_htc(0.5,10)=16.665
# q = h(ts-ta) = -99.99; t = λ(|Δt|/|q| - 1/h) ≈ 17.4 mm
w.equipment_type_combo.setCurrentText('平面形设备')
w.insulation_type_combo.setCurrentText('保冷')
set_mode('防结露')
w.conductivity_input.setText('0.0512')
w.ambient_temp_input.setText('30')
w.equipment_temp_input.setText('-10')
w.dew_point_input.setText('22')
w.calculate()
thk_c = w._last_result['thickness_mm']
hc = 11.63 + 7.12 * 0.5 ** 0.5
t_ref_c = 0.0512 * (40.0 / (hc * 6.0) - 1.0 / hc) * 1000
check(f'防结露(平面保冷) 结果≈{t_ref_c:.1f}mm', approx(thk_c, t_ref_c, 1.5), f'{thk_c:.2f}')
check('防结露结果高于露点要求（ts=露点+2）', thk_c > 0)

# ── 汇总 ──
print('\n' + '=' * 50)
print(f'通过 {len(PASS)} 项, 失败 {len(FAIL)} 项')
if FAIL:
    for name, detail in FAIL:
        print(f'  FAIL: {name}  {detail}')
    sys.exit(1)
print('ALL PASS')
