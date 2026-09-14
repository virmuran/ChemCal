# -*- coding: utf-8 -*-
"""安全阀泄放面积计算器回归测试（API 520 Part I §5.6 SI 制核对）
纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_safety_valve.py

核对依据：
- API 520 Part I §5.6.2（SI）：临界流 A[mm²] = W[kg/h]/(C·Kd·P1[kPaa])·√(T·Z/M)
  C = 0.03948·√(γ·(2/(γ+1))^((γ+1)/(γ-1)))，仅适用于 kg/h + kPaa + mm² 单位组合
- 亚临界：A = 17.9·W·√(T·Z/M)/(F·Kd·P1)，F=√((γ/(γ-1))·(r^(2/γ)−r^((γ+1)/γ)))
- API 521 火灾工况：Q = 43200·F·A^0.82 (W，A[m²])
- 修复前 bug：C 常数（kg/h/kPa 制）被误配到 kg/s/Pa 单位，面积偏小 3.6 倍（临界流）
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
    't_safety_valve', os.path.join(CALC_DIR, 'safety_valve_calculator.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

w = mod.SafetyValveCalculator()

PASS, FAIL = [], []

def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}' + (f'  [{detail}]' if detail and not cond else ''))

def approx(a, b, rel):
    return abs(a - b) <= rel * abs(b)

def set_mode(mode, source='已知泄放量'):
    w.mode_combo.setCurrentText(mode)
    w.relief_source_combo.setCurrentText(source)
    w._on_mode_changed(mode)

# ── 1. C 系数锚点（API 520）──
def C_of(g):
    return 0.03948 * math.sqrt(g * (2 / (g + 1)) ** ((g + 1) / (g - 1)))
check('C(γ=1.4)=0.02703', approx(C_of(1.4), 0.027033, 1e-3), f'{C_of(1.4):.6f}')
check('C(γ=1.33)=0.02655', approx(C_of(1.33), 0.026552, 1e-3), f'{C_of(1.33):.6f}')

# ── 2. 案例1：空气临界流 ──
# W=1000 kg/h, MAWP=1.0 MPa(g), 超压10% → P1=1201.3 kPaa, T=293.15K, M=29, γ=1.4, Kd=1
# A = 1000×3.1794/(0.027033×1201.3) = 97.90 mm²
set_mode('空气')
w.mawp_input.setText('1.0')
w.overpressure_input.setText('10')
w.back_pressure_input.setText('0')
w.kd_input.setText('1.0')
w.relief_flow_input.setText('1000')
w.temp_input.setText('20')
w.mw_input.setText('29')
w.gamma_input.setText('1.4')
w.z_input.setText('1.0')
w.calculate()
r = w._last_result
check('案例1 临界流判定', r['is_choked'], str(r.get('actual_ratio')))
check('案例1 面积≈97.90mm²', approx(r['area_mm2'], 97.90, 0.01), f"{r['area_mm2']:.3f}")
check('案例1 泄放压力 1.2013 MPaa', approx(r['relief_p_mpaa'], 1.2013, 1e-4), str(r['relief_p_mpaa']))

# ── 3. 案例2：饱和水蒸汽临界流（温度自动取饱和温度）──
# MAWP=1.0 MPa(g)+10% → P1=1.2013 MPaa → Tsat≈188.0°C；W=1000 kg/h, M=18, γ=1.33
# A = 1000×√(461.3/18)/(0.026552×1201.3) ≈ 158.8 mm²
set_mode('饱和水蒸汽')
w.mawp_input.setText('1.0')
w.overpressure_input.setText('10')
w.back_pressure_input.setText('0')
w.kd_input.setText('1.0')
w.relief_flow_input.setText('1000')
w.mw_input.setText('18')
w.gamma_input.setText('1.33')
w.z_input.setText('1.0')
w.calculate()
r2 = w._last_result
t_auto = float(w.temp_input.text())
check('案例2 饱和温度自动填入≈188°C', abs(t_auto - 188.0) < 3.0, f'{t_auto}')
a2_expect = 1000 * math.sqrt((t_auto + 273.15) / 18) / (C_of(1.33) * 1.0 * 1201.3)
check(f'案例2 面积≈{a2_expect:.1f}mm²', approx(r2['area_mm2'], a2_expect, 0.005),
      f"{r2['area_mm2']:.3f} vs {a2_expect:.3f}")

# ── 4. 案例3：空气亚临界流（高背压）──
# 背压 0.9 MPa(g) → r=0.83346 > 0.52828 亚临界；F=0.36952
# A = 17.9×1000×3.1794/(0.36952×1201.3) = 128.2 mm²
set_mode('空气')
w.back_pressure_input.setText('0.9')
w.temp_input.setText('20')          # 模式切换不重置温度，手动恢复案例1取值
w.calculate()
r3 = w._last_result
check('案例3 亚临界流判定', not r3['is_choked'], str(r3.get('actual_ratio')))
check('案例3 面积≈128.2mm²', approx(r3['area_mm2'], 128.2, 0.01), f"{r3['area_mm2']:.3f}")
check('案例3 Kb<1 且与 F/17.9 一致', approx(r3['kb'], 0.369522 / 17.9, 0.01), str(r3.get('kb')))

# ── 5. 案例4：火灾工况泄放量（API 521）──
# 润湿面积 50 m², F=1.0, 潜热 2000 kJ/kg：Q=43200×50^0.82=1068.2 kW → W=1922.8 kg/h
set_mode('火灾工况(已知润湿面积)')
w.mawp_input.setText('1.0')
w.overpressure_input.setText('10')
w.back_pressure_input.setText('0')
w.kd_input.setText('1.0')
w.env_factor_input.setText('1.0')
w.latent_heat_input.setText('2000')
w.wetted_area_input.setText('50')
w.calculate()
r4 = w._last_result
w_expect = 43200 * (50 ** 0.82) / (2000 * 1000) * 3600
check(f'案例4 火灾泄放量≈{w_expect:.0f} kg/h', approx(r4['relief_rate_kgh'], w_expect, 0.005),
      f"{r4['relief_rate_kgh']:.1f}")
check('案例4 泄放面积与蒸汽公式一致',
      approx(r4['area_mm2'],
             w_expect * math.sqrt((float(w.temp_input.text()) + 273.15) / 18)
             / (C_of(1.33) * 1.0 * 1201.3), 0.01),
      f"{r4['area_mm2']:.3f}")

# ── 6. 结果文本含修正后公式 ──
txt = w.result_text.toPlainText()
check('结果含 API 520 SI 公式与 Kb', '17.9' in txt and 'Kb' in txt)

# ══════════════════════════════════════════════════════════════
#  7. Kd 阀型映射（2026-09-14 修复）
# ══════════════════════════════════════════════════════════════
# 修复前两个 bug：
#  ① _on_kd_type_changed 用 `key in text` 子串判断，而"不带调节圈微启式"本身
#     含子串"带调节圈微启式"（dict 保序，先命中后者）→ 选 0.30 被误填成 0.45。
#     Kd 高估 50%，泄放面积 A ∝ 1/Kd 偏小约 33% → 安全阀选型偏小（安全风险）。
#  ② kd_input 的创建晚于 setCurrentIndex(1)，setCurrentIndex 立即发信号 →
#     实例化必抛 AttributeError（被 Qt 吞进 stderr，不弹窗），默认值填充静默失效。
import io as _io
import contextlib as _ctx

_buf = _io.StringIO()
with _ctx.redirect_stderr(_buf):
    w_kd = mod.SafetyValveCalculator()
check('实例化无 AttributeError（kd_input 先于信号连接创建）',
      'AttributeError' not in _buf.getvalue(), _buf.getvalue().strip()[-80:])
check('默认工况为全启式且 Kd=0.65（下拉与输入框一致）',
      w_kd.kd_type_combo.currentText().startswith('全启式')
      and w_kd.kd_input.text() == '0.65',
      f'{w_kd.kd_type_combo.currentText()} / {w_kd.kd_input.text()}')

for _idx, _expect in [(1, '0.65'), (2, '0.45'), (3, '0.30')]:
    w_kd.kd_type_combo.setCurrentIndex(_idx)
    check(f'阀型「{w_kd.kd_type_combo.currentText()}」→ Kd = {_expect}',
          w_kd.kd_input.text() == _expect, f'实际 {w_kd.kd_input.text()}')

# 子串陷阱守卫：单独再点一次"不带调节圈"，确认不会再落到 0.45
w_kd.kd_type_combo.setCurrentIndex(2)
w_kd.kd_type_combo.setCurrentIndex(3)
check('子串陷阱守卫：不带调节圈微启式 ≠ 0.45',
      w_kd.kd_input.text() == '0.30', w_kd.kd_input.text())

# 下拉每一项都必须有对应 Kd，防止将来新增阀型漏配（漏配则 Kd 保持上一个值）
for _i in range(1, w_kd.kd_type_combo.count()):
    _t = w_kd.kd_type_combo.itemText(_i)
    w_kd.kd_input.setText('')
    w_kd._on_kd_type_changed(_t)
    check(f'下拉项「{_t}」有对应 Kd（无漏配）',
          w_kd.kd_input.text() != '', '未匹配到映射，Kd 未被填充')

w_kd.clear_inputs()
check('清空后下拉与 Kd 一致（同回全启式 0.65）',
      w_kd.kd_type_combo.currentText().startswith('全启式')
      and w_kd.kd_input.text() == '0.65',
      f'{w_kd.kd_type_combo.currentText()} / {w_kd.kd_input.text()}')

# ── 汇总 ──
print('\n' + '=' * 50)
print(f'通过 {len(PASS)} 项, 失败 {len(FAIL)} 项')
if FAIL:
    for name, detail in FAIL:
        print(f'  FAIL: {name}  {detail}')
    sys.exit(1)
print('ALL PASS')
