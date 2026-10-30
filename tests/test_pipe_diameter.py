# -*- coding: utf-8 -*-
"""管径计算器回归测试
纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_pipe_diameter.py

核对依据（化工工艺设计手册，流速法管径公式）：
    d = 18.81 × √( W/(u·ρ) )   [W: kg/h, u: m/s, ρ: kg/m³, d: mm]
    系数 18.81 = 1000×√(4/(3600·π)) = 18.809
    标况密度（kg/Nm³）为手册标准值
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
    't_pipe_diameter', os.path.join(CALC_DIR, 'pipe_diameter_calculator.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

w = mod.管径计算()

PASS, FAIL = [], []

def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}' + (f'  [{detail}]' if detail and not cond else ''))

def approx(a, b, rel=1e-3):
    return abs(a - b) <= rel * abs(b)

# ── 1. 公式系数量纲核对（手册圆整值 18.81，精确 18.8063）──
coef = 1000 * math.sqrt(4 / (3600 * math.pi))
check('精确系数 = 18.8063 (1000×√(4/3600π))', approx(coef, 18.8063, 1e-4), f'{coef:.4f}')
check('代码系数 18.81 为手册圆整值', '18.81' in open(
    os.path.join(CALC_DIR, 'pipe_diameter_calculator.py'), encoding='utf-8').read())

# ── 2. 水 m³/h：10 m³/h, u=2 m/s, ρ=1000 → d=42.06 mm ──
# W = 10×1000 = 10000 kg/h; d = 18.81√(10000/2000)
d1 = w.calculate_diameter_from_flow(10, 2, 1000, '水及粘度相似的液体', 'P≤1MPa')
check('水 10m³/h u=2 → d=42.06mm', approx(d1, 42.06, 1e-3), f'{d1:.3f}')
# 往返一致
f1 = w.calculate_flow_from_diameter(d1, 2, 1000, '水及粘度相似的液体', 'P≤1MPa')
check('水 往返计算还原流量 10 m³/h', approx(f1, 10, 1e-6), f'{f1:.4f}')

# ── 3. 蒸汽 t/h：10 t/h, u=35 m/s, ρ=2.1 → d=219.40 mm ──
# W = 10000 kg/h; d = 18.81√(10000/(35×2.1)) = 18.81×11.664
d2 = w.calculate_diameter_from_flow(10, 35, 2.1, '饱和蒸汽', 'DN>200')
check('蒸汽 10t/h u=35 ρ=2.1 → d≈219.4mm', approx(d2, 219.40, 1e-3), f'{d2:.3f}')
f2 = w.calculate_flow_from_diameter(d2, 35, 2.1, '饱和蒸汽', 'DN>200')
check('蒸汽 往返计算还原流量 10 t/h', approx(f2, 10, 1e-6), f'{f2:.4f}')

# ── 4. 压缩气体 Nm³/h：100 Nm³/h, u=10 m/s, 操作态 ρ=1.293 → d≈59.48 mm ──
# W = 100×1.293 = 129.3 kg/h; d = 18.81√(129.3/12.93) = 18.81√10
d3 = w.calculate_diameter_from_flow(100, 10, 1.293, '压缩气体', 'P≤0.3MPa')
check('压缩气体 100Nm³/h u=10 → d≈59.48mm (√10×18.81)', approx(d3, 59.48, 1e-3), f'{d3:.3f}')
f3 = w.calculate_flow_from_diameter(d3, 10, 1.293, '压缩气体', 'P≤0.3MPa')
check('压缩气体 往返计算还原流量 100 Nm³/h', approx(f3, 100, 1e-6), f'{f3:.4f}')

# ── 5. 标况密度表锚点核对（kg/Nm³，手册值）──
for gas, expect in [('压缩空气', 1.293), ('氧气', 1.429), ('氮气', 1.251),
                    ('天然气', 0.717), ('氨气', 0.771), ('乙炔气', 1.171)]:
    got = w.std_density_data.get(gas)
    check(f'标况密度 {gas}={expect}', got == expect, str(got))

# ── 6. 实际流速核对：圆整后流速重算 ──
# d=50mm, 水 10 m³/h: u = (10×1000/3600)/(1000×π×0.025²) = 2.7778/1.9635 = 1.4147 m/s
u = w.calculate_actual_velocity(10, 50, 1000, '水及粘度相似的液体', 'P≤1MPa')
check('实际流速 d=50mm 水10m³/h → 1.4147 m/s', approx(u, 1.4147, 1e-3), f'{u:.4f}')

# ── 7. 淀粉糖物料档（2026-10-30 新增）：注册 / 联动 / 粘度中值 ──
for _f in ['淀粉调浆液', '液化液', '糖化液', '脱色液', '葡萄糖浆',
           '自定义粘性液体(按粘度推荐)']:
    check(f'新介质下拉框注册: {_f}', w.fluid_combo.findText(_f) >= 0)
    check(f'新介质流量档注册: {_f}', _f in w.fluid_ranges)

w.fluid_combo.setCurrentText('液化液')
_conds = [w.condition_combo.itemText(i) for i in range(w.condition_combo.count())]
check('液化液条件 = DE10~15/DE16~18/90℃ 三档',
      _conds == ['DE10~15(60℃)', 'DE16~18(60℃)', 'DE10~15(90℃出喷射器)'], str(_conds))
check('液化液推荐流速自动填入 0.8', w.velocity_input.text() == '0.8', w.velocity_input.text())
check('液化液粘度中值 1.5 Pa·s', approx(w._current_viscosity() or 0, 1.5, 1e-9))
check('液化液密度 1140', w._current_density == 1140, str(w._current_density))

w.fluid_combo.setCurrentText('葡萄糖浆')
check('葡萄糖浆 75~80%DS 档流速 0.3', w.velocity_input.text() == '0.3', w.velocity_input.text())
check('葡萄糖浆粘度中值 8.5 Pa·s', approx(w._current_viscosity() or 0, 8.5, 1e-9))

# 自定义档：粘度 → 推荐流速（分级规则锚点）
w.fluid_combo.setCurrentText('自定义粘性液体(按粘度推荐)')
check('自定义档显示粘度行', not w.viscosity_input.isHidden())
check('自定义档显示密度行', not w.density_input.isHidden())
_band_cases = [(49, (1.5, 3.0)), (50, (0.8, 1.5)), (499, (0.8, 1.5)),
               (999, (0.5, 1.0)), (9999, (0.3, 0.6)), (10000, (0.1, 0.3))]
for _mu, _exp in _band_cases:
    check(f'粘度分级锚点 {_mu} → {_exp}',
          w.recommend_velocity_by_viscosity(_mu) == _exp,
          str(w.recommend_velocity_by_viscosity(_mu)))
w.viscosity_input.setText('1500')
check('输入粘度1500 → 流速0.75', w.velocity_input.text() == '0.75', w.velocity_input.text())
w.density_input.setText('1400')
check('自定义密度输入生效 1400', w._current_density == 1400, str(w._current_density))

# ── 8. 压降估算（Darcy-Weisbach）数值锚点 ──
# 水 20℃ DN50(52.5mm) u=1.5: Re≈78750 湍流, 压降经验 35~55 kPa/100m
_dp = w._estimate_pressure_drop(52.5, 1.5, 1000.0, 0.001)
check('水 DN50 u=1.5 → 湍流', _dp['regime'] == '湍流', _dp['regime'])
check('水 DN50 u=1.5 → 压降 35~55 kPa/100m', 35 < _dp['dp_kpa'] < 55, f"{_dp['dp_kpa']:.1f}")
# 层流 λ=64/Re 精确锚点: Re=1575
_dp3 = w._estimate_pressure_drop(52.5, 0.3, 1000.0, 0.01)
check('粘性低速 Re=1575 → 层流', _dp3['regime'] == '层流', f"Re={_dp3['re']:.0f}")
check('层流 λ=64/Re', approx(_dp3['lambda'], 64.0 / 1575.0, 1e-6), f"{_dp3['lambda']:.5f}")

# 结果页压降段：带粘度介质显示、无粘度介质不显示
w.fluid_combo.setCurrentText('液化液')
w.flow_input.setText('10')
w.calculate()
check('液化液结果页含压降估算段',
      '压降估算' in w.result_text.toPlainText() and 'kPa/100m' in w.result_text.toPlainText())
w.fluid_combo.setCurrentText('自来水')
w.flow_input.setText('10')
w.calculate()
check('自来水结果页无压降段', '压降估算' not in w.result_text.toPlainText())

# 回归保护：原有锚点不被新功能破坏
check('回归: 水 10m³/h u=2 → d≈42.06',
      approx(w.calculate_diameter_from_flow(10, 2, 1000, '水及粘度相似的液体', 'P≤1MPa'), 42.06, 1e-3))

# ── 汇总 ──
print('\n' + '=' * 50)
print(f'通过 {len(PASS)} 项, 失败 {len(FAIL)} 项')
if FAIL:
    for name, detail in FAIL:
        print(f'  FAIL: {name}  {detail}')
    sys.exit(1)
print('ALL PASS')
