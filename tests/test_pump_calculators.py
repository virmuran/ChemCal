# -*- coding: utf-8 -*-
"""泵类计算器回归测试（NPSHa + 离心泵功率）
纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_pump_calculators.py

核对依据：
- NPSHa = (P_s - P_v)/(ρ·g) + H_static - H_f（离心泵汽蚀基础式，液面至泵中心线高差灌注为正）
- 水饱和蒸汽压锚点：20°C→2.34 kPa，60°C→19.92 kPa（对照 steam table）
- 海拔气压锚点：0m→101.3，300m→97.6，500m→95.5，1000m→89.9 kPa（标准大气压公式）
- 泵功率：Pe = ρgQH/3.6e6 kW（Q m³/h）；P轴=Pe/η泵；配套电机 ≥ P轴/η传动×K（不含电机效率）；
  电网输入功率 P_in = P轴/η传动/η电机×K
- 修复前 bug：
  1) S/SH 双吸泵效率分档键不统一 → 选型 KeyError
  2) 电机效率输入框零引用（永远查表）
  3) 泵型自动估算效率死代码（效率框默认值恒非空）
  4) 历史记录正则与结果文本不匹配 → 输出恒空
  5) NPSHa 安全裕量下拉切回"请选择"后输入框永久只读
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

G = 9.81
PASS, FAIL = [], []

def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}' + (f'  [{detail}]' if detail and not cond else ''))

def approx(a, b, rel=1e-3):
    return abs(a - b) <= rel * abs(b)

# ══════════════════ Part 1: NPSHa ══════════════════
m1 = _load('t_npsha', os.path.join(CALC_DIR, 'npsha_calculator.py'))
w = m1.NPSHaCalculator()

def npsha_set(ps, pv, hs, hf, rho):
    w.surface_pressure_input.setText(str(ps))
    w.vapor_pressure_input.setText(str(pv))
    w.static_head_input.setText(str(hs))
    w.friction_loss_input.setText(str(hf))
    w.density_input.setText(str(rho))
    w.npshr_input.clear()
    w.safety_margin_input.clear()

# ── 1.1 敞口水 20°C 基准案例 ──
# Ps=101.3, Pv=2.34, ρ=1000, Hs=+2, Hf=1.5
npsha_set(101.3, 2.34, 2, 1.5, 1000)
w.calculate_npsha()
exp = 101300/(1000*G) - 2340/(1000*G) + 2 - 1.5
check('NPSHa 敞口水≈10.588 m', approx(exp, 10.588, 1e-3), f'{exp:.4f}')
check('NPSHa 结果文本含结果', f'{exp:.3f}' in w.result_text.toPlainText(),
      w.result_text.toPlainText()[:200])

# ── 1.2 抽吸工况（负高差） ──
# Ps=101.3, Pv=2.34, ρ=998, Hs=-3, Hf=1.0 → 6.108 m
npsha_set(101.3, 2.34, -3, 1.0, 998)
w.calculate_npsha()
exp2 = 101300/(998*G) - 2340/(998*G) - 3 - 1.0
check('NPSHa 抽吸工况≈6.108 m', approx(exp2, 6.108, 2e-3), f'{exp2:.4f}')
check('抽吸工况结果一致', f'{exp2:.3f}' in w.result_text.toPlainText())

# ── 1.3 密闭加压容器 60°C 水 ──
# Ps=500, Pv=19.92, ρ=983, Hs=2, Hf=1.5 → ≈50.29 m
npsha_set(500, 19.92, 2, 1.5, 983)
w.calculate_npsha()
exp3 = 500000/(983*G) - 19920/(983*G) + 0.5
check('NPSHa 密闭容器≈50.29 m', approx(exp3, 50.286, 1e-3), f'{exp3:.4f}')

# ── 1.4 NPSHr + 安全裕量评估 ──
npsha_set(101.3, 2.34, 2, 1.5, 1000)
w.npshr_input.setText('3.0')
w.safety_margin_input.setText('0.6')
w.calculate_npsha()
txt = w.result_text.toPlainText()
check('含 NPSHa-NPSHr 行', 'NPSHa - NPSHr' in txt)
check('含扣除裕量后余量', '扣除裕量后余量' in txt)
check('比值 NPSHa/(NPSHr+裕量)=2.94', '2.94' in txt)

# ── 1.5 下拉联动 ──
w.on_surface_pressure_changed('97.6 kPaA - 海拔300米')
check('海拔300m→97.6', w.surface_pressure_input.text() == '97.6', w.surface_pressure_input.text())
w.on_vapor_pressure_changed('19.92 kPa - 水在60°C')
check('60°C蒸汽压→19.92', w.vapor_pressure_input.text() == '19.92', w.vapor_pressure_input.text())
w.on_friction_loss_changed('1.0-2.0 m - 中等管路')
check('管路损失取中值1.5', w.friction_loss_input.text() == '1.5', w.friction_loss_input.text())
w.on_safety_margin_changed('0.6-1.0 m - 一般离心泵')
check('安全裕量取中值0.8', w.safety_margin_input.text() == '0.8', w.safety_margin_input.text())
# 修复点：切回"请选择"后应恢复可编辑
w.on_safety_margin_changed('请选择泵型获取推荐安全裕量')
check('裕量切回请选择后可编辑', not w.safety_margin_input.isReadOnly())

# ── 1.6 历史记录钩子 ──
npsha_set(101.3, 2.34, 2, 1.5, 1000)
w.calculate_npsha()
h = w._get_history_data()
check('NPSHa 历史钩子含 NPSHa_m', abs(h['outputs'].get('NPSHa_m', 0) - exp) < 1e-3, str(h))

# ── 1.7 汽蚀预警 ──
npsha_set(101.3, 95.0, 1, 1.0, 958)  # 90°C 热水抽吸
w.npshr_input.setText('3.0')
w.safety_margin_input.setText('0.6')
w.calculate_npsha()
check('汽蚀不足有预警', '不足' in w.result_text.toPlainText() or '危险' in w.result_text.toPlainText())

# ══════════════════ Part 2: 离心泵功率 ══════════════════
m2 = _load('t_pump_power', os.path.join(CALC_DIR, 'pump_power_calculator.py'))
p = m2.CentrifugalPumpCalculator()

def pump_set(q, h, rho, eff='75', motor_eff='', drive='直联传动 (η=1.00)', k='1.1'):
    p.pump_type_combo.setCurrentIndex(0)
    p.drive_combo.setCurrentText(drive)
    p.flow_input.setText(str(q))
    p.head_input.setText(str(h))
    p.density_input.setText(str(rho))
    p.efficiency_input.setText(str(eff))
    p.motor_efficiency_input.setText(motor_eff)
    p.safety_input.setText(k)

# ── 2.1 基准案例：Q=100,H=50,ρ=1000,η=75%,直联,K=1.1 ──
# Pe=13.625 kW, P轴=18.167, 电机需求=19.98→匹配22kW, 表查22→0.91, P_in=18.167/0.91*1.1=21.96
pump_set(100, 50, 1000)
p.calculate()
txt = p.result_text.toPlainText()
check('Pe=13.62 kW', '有效功率 Pe: 13.62 kW' in txt, txt[:100])
check('轴功率=18.17 kW', '轴功率 P: 18.17 kW' in txt)
check('配套电机=22 kW', '配套电机功率: 22 kW' in txt)
check('电机效率按表91%', '91.0 %' in txt, txt)
check('电网输入=21.96 kW', '电机输入功率 P_in: 21.96 kW' in txt)

# ── 2.2 修复点：S/SH 双吸泵不再 KeyError ──
p.pump_type_combo.setCurrentText('S/SH 单级双吸离心泵 (大流量)')
p.efficiency_input.clear()   # 清空 → 走自动估算 0.65
p.motor_efficiency_input.clear()
p.calculate()
txt2 = p.result_text.toPlainText()
check('S/SH 选型无错误弹窗', '计算过程中发生错误' not in txt2 and len(txt2) > 100)
check('S/SH 自动效率65%', '65.0 %' in txt2, txt2[:300])
# P轴=13.625/0.65=20.96，需求=23.06→匹配30kW
check('S/SH 匹配30 kW', '配套电机功率: 30 kW' in txt2)

# ── 2.3 修复点：电机效率用户输入生效 ──
pump_set(100, 50, 1000, motor_eff='95')
p.calculate()
txt3 = p.result_text.toPlainText()
check('电机效率显示用户输入95%', '95.0 %' in txt3 and '(用户输入)' in txt3, txt3)
check('P_in=18.167/0.95*1.1=21.04', '电机输入功率 P_in: 21.04 kW' in txt3, txt3)

# ── 2.4 皮带传动 η=0.95 ──
pump_set(100, 50, 1000, drive='皮带传动 (η=0.95)')
p.calculate()
# 需求=18.167/0.95*1.1=21.03→匹配22kW
check('皮带传动匹配22 kW', '配套电机功率: 22 kW' in p.result_text.toPlainText())

# ── 2.5 效率分档估算（每型独立） ──
check('IS Q=25→0.55', p._estimate_pump_efficiency('IS 单级单吸', 25) == 0.55)
check('IS Q=200→0.78', p._estimate_pump_efficiency('IS 单级单吸', 200) == 0.78)
check('S/SH Q=100→0.65', p._estimate_pump_efficiency('S/SH 单级双吸', 100) == 0.65)
check('S/SH Q=1000→0.82', p._estimate_pump_efficiency('S/SH 单级双吸', 1000) == 0.82)
check('AY Q=400→0.75', p._estimate_pump_efficiency('AY 油泵', 400) == 0.75)
check('未知泵型→None', p._estimate_pump_efficiency('不存在', 100) is None)

# ── 2.6 修复点：泵型选择自动填充效率 ──
pump_set(100, 50, 1000)
p.efficiency_combo.setCurrentIndex(0)   # 未选择
p.pump_type_combo.setCurrentText('IH 化工流程泵 (耐腐蚀)')
check('选IH自动填62%', p.efficiency_input.text() == '62', p.efficiency_input.text())
# 用户已从下拉选择时不覆盖
p.efficiency_combo.setCurrentText('80-90% - 超高效泵')
p.pump_type_combo.setCurrentText('AY 离心油泵 (石油化工)')
check('已选效率不被覆盖', p.efficiency_input.text() == '85.0', p.efficiency_input.text())

# ── 2.7 修复点：历史记录输出非空 ──
pump_set(100, 50, 1000)
p.calculate()
h2 = p._get_history_data()
check('泵功率历史含有效功率', '有效功率 (kW)' in h2['outputs'], str(h2))
check('泵功率历史含配套电机', '配套电机功率 (kW)' in h2['outputs'], str(h2))
check('泵功率历史含轴功率', h2['outputs'].get('轴功率 (kW)') == '18.17', str(h2))

# ── 2.8 输入校验 ──
p.result_text.clear()
pump_set(0, 50, 1000)
p.calculate()
check('流量为0有警告', len(p.result_text.toPlainText()) == 0)

print()
print(f'════════ 总结: {len(PASS)} PASS / {len(FAIL)} FAIL ════════')
for name, detail in FAIL:
    print(f'  FAIL  {name}  [{detail}]')
sys.exit(1 if FAIL else 0)
