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

# ── 9. 泵吸入管联算（一次给出进出口管径）──
# 9.1 勾选框存在性与模式显隐
check('9.1 勾选框存在且默认不勾', hasattr(w, 'pump_pair_check') and not w.pump_pair_check.isChecked())
check('9.2 管径模式下可见', not w.pump_pair_check.isHidden())
w.mode_buttons['由管径计算流量'].setChecked(True)
w.on_mode_changed('由管径计算流量')
check('9.3 流量模式下自动隐藏', w.pump_pair_check.isHidden())
w.mode_buttons['由流量计算管径'].setChecked(True)
w.on_mode_changed('由流量计算管径')

# 9.4 气体禁用、液体可用
w.fluid_combo.setCurrentText('压缩气体')
check('9.4 气体条件勾选框禁用', not w.pump_pair_check.isEnabled())
w.fluid_combo.setCurrentText('水及粘度相似的液体')
w.condition_combo.setCurrentText('离心泵排出管')
check('9.5 液体条件勾选框可用', w.pump_pair_check.isEnabled())

# 9.6 手册成对吸入档：水 25m³/h，排出管 u=2.25 → 排 DN65，吸入按手册 1.75 → DN80（比排出大）
rho = w.fluid_data['水及粘度相似的液体']
d_th = w.calculate_diameter_from_flow(25, 2.25, rho, '水及粘度相似的液体', '离心泵排出管')
w.pump_pair_check.setChecked(True)
w.show_diameter_result('水及粘度相似的液体', '离心泵排出管', 25, 2.25, d_th, rho, 0.5, '由流量计算管径')
txt = w.result_text.toPlainText()
u_s, src = w._pump_suction_velocity('水及粘度相似的液体', '离心泵排出管', 2.25)
d_s, s_dn = w._pump_suction_dn(25, u_s, rho, '水及粘度相似的液体', '离心泵排出管', 65)
check('9.6 吸入流速取手册成对档中值 1.75', approx(u_s, 1.75), f'{u_s}')
check('9.7 来源说明指向手册吸入档', '手册吸入档' in src, src)
check('9.8 吸入管径 DN80 且大于排出 DN65', s_dn == 80 and 'DN80' in txt, f'{s_dn}')
check('9.9 结果页含吸入管配整段', '泵吸入管配管' in txt and 'NPSHa' in txt)

# 9.7 无成对档：0.6 倍经验取法（糖化液）
cond_s = list(w.fluid_ranges['糖化液'].keys())[0]
rho_s = w.fluid_data['糖化液']
u_s2, src2 = w._pump_suction_velocity('糖化液', cond_s, 1.5)
check('9.10 无成对档时取 0.6 倍', approx(u_s2, 0.9), f'{u_s2}')
check('9.11 来源说明标注经验取法', '0.6 倍' in src2 and '[E]' in src2, src2)
d_th2 = w.calculate_diameter_from_flow(20, 1.5, rho_s, '糖化液', cond_s)
w.show_diameter_result('糖化液', cond_s, 20, 1.5, d_th2, rho_s, 0.5, '由流量计算管径')
txt2 = w.result_text.toPlainText()
check('9.12 糖化液结果页含吸入管段且吸入流速更低', '泵吸入管配管' in txt2 and '0.90 m/s' in txt2)

# 9.8 防沉降/防汽蚀下限 0.3 m/s
u_s3, _ = w._pump_suction_velocity('糖化液', cond_s, 0.4)
check('9.13 0.6×0.4=0.24 → 下限托底 0.3', approx(u_s3, 0.3), f'{u_s3}')

# 9.9 不勾选时结果页无吸入段（回归保护）
w.pump_pair_check.setChecked(False)
w.show_diameter_result('水及粘度相似的液体', '离心泵排出管', 25, 2.25, d_th, rho, 0.5, '由流量计算管径')
check('9.14 不勾选无吸入段', '泵吸入管配管' not in w.result_text.toPlainText())

# 9.10 历史记录：勾选时吸入管径/流速入史
w.pump_pair_check.setChecked(True)
w.flow_input.setText('25')
w.velocity_input.setText('2.25')
hd = w._get_history_data()
check('9.15 历史含吸入管径 DN80', hd['outputs'].get('吸入管径') == 'DN80', str(hd['outputs']))
check('9.16 历史含吸入管流速 1.38（DN80 实际值圆整）', approx(hd['outputs'].get('吸入管流速_m_s', 0), round(25/3600/(math.pi*(0.08)**2/4), 2), 1e-2), str(hd['outputs'].get('吸入管流速_m_s')))
w.pump_pair_check.setChecked(False)

# ── 10. 预设/参数分区：密度常显可改、切预设重填、气体标态折算 ──
# 依据：体积流量法 d = 18.81√(Q/u)（密度抵消），质量流量法 d = 18.81√(W/(u·ρ))；
#      标态流量须按表压折算工况密度：ρ = ρ_N × 273.15/293.15 × (P+0.1013)/0.1013
w.pump_pair_check.setChecked(False)

# 10.1 密度行常显（此前只在「自定义粘性液体」出现）
w.fluid_combo.setCurrentText('水及粘度相似的液体')
w.condition_combo.setCurrentText('P≤1MPa')
check('10.1 液体档密度行可见且自动填 1000',
      not w.density_input.isHidden() and w.density_input.text().startswith('1000'),
      w.density_input.text())
check('10.2 液体档密度说明写「仅影响压降」',
      '仅影响压降' in w.density_hint.text(), w.density_hint.text())

# 10.3 体积流量法：改密度不改管径（ρ 分子分母抵消）
_d_a = w.calculate_diameter_from_flow(10, 2, 800, '水及粘度相似的液体', 'P≤1MPa')
_d_b = w.calculate_diameter_from_flow(10, 2, 1400, '水及粘度相似的液体', 'P≤1MPa')
check('10.3 液体体积流量档：改密度管径不变（42.06）',
      approx(_d_a, 42.06, 1e-3) and approx(_d_b, 42.06, 1e-3), f'{_d_a:.2f}/{_d_b:.2f}')

# 10.4 质量流量法：密度直接进管径
_d_t3 = w.calculate_diameter_from_flow(10, 30, 3.0, '饱和蒸汽', 'DN>200')
_d_t9 = w.calculate_diameter_from_flow(10, 30, 9.0, '饱和蒸汽', 'DN>200')
check('10.4 蒸汽质量流量档：密度 3→198.27 / 9→114.47',
      approx(_d_t3, 198.27, 1e-2) and approx(_d_t9, 114.47, 1e-2), f'{_d_t3:.2f}/{_d_t9:.2f}')

# 10.5 流速来源标注：预设 → 手改
w.fluid_combo.setCurrentText('水及粘度相似的液体')
w.condition_combo.setCurrentText('P≤1MPa')
check('10.5 流速标注含「预设」与手册范围',
      '预设' in w.velocity_hint.text() and '手册' in w.velocity_hint.text(), w.velocity_hint.text())
w.velocity_input.setText('2.5')
check('10.6 手改流速后标注变「已改」', '已改 2.5' in w.velocity_hint.text(), w.velocity_hint.text())

# 10.7 切预设（条件）= 重填，手改值被覆盖
w.velocity_input.setText('2.5')
w.condition_combo.setCurrentText('P≤20~30MPa')
check('10.7 切条件后流速按新预设重填（2~3.5 中点 2.75→2.8，覆盖手改的 2.5）',
      w.velocity_input.text() == '2.8', w.velocity_input.text())
w.condition_combo.setCurrentText('离心泵排出管')
check('10.8 切到离心泵排出管后流速重填为 2.2（1.5~3.0 中点）',
      w.velocity_input.text() == '2.2', w.velocity_input.text())

# 10.9 手改密度 → 切预设复位
w.density_input.setText('1150')
check('10.9 手改密度生效', approx(w._read_density(), 1150, 1e-6), f'{w._read_density()}')
check('10.10 手改密度后说明标「已改」', '已改' in w.density_hint.text(), w.density_hint.text())
w.fluid_combo.setCurrentText('自来水')
check('10.11 切流体后密度复位为预设值（1000）',
      w.density_input.text().startswith('1000'), w.density_input.text())

# 10.12 气体：按压力折算工况密度
w.fluid_combo.setCurrentText('压缩气体')
w.condition_combo.setCurrentText('P=0.3~0.6MPa')
_p = float(w.pressure_input.text())
_rho_gas = w._read_density()
_rho_expect = 1.29 * (273.15 / 293.15) * ((_p + 0.1013) / 0.1013)
check(f'10.12 压缩气体 0.45MPa 工况密度 {_rho_expect:.2f}（不再是标态 1.29）',
      approx(_rho_gas, _rho_expect, 1e-2), f'{_rho_gas:.3f}')
check('10.13 气体密度说明提到「工况密度」', '工况密度' in w.density_hint.text(), w.density_hint.text())

# 10.14 修正后管径：1000 Nm³/h @0.45MPa u=15 → 68.3mm（修正前 153.8mm）
_d_gas = w.calculate_diameter_from_flow(1000, 15, _rho_gas, '压缩气体', 'P=0.3~0.6MPa')
check('10.14 气体 1000Nm³/h@0.45MPa u=15 → 68.3mm（修正前 153.8）',
      approx(_d_gas, 68.3, 0.2), f'{_d_gas:.2f}')

# 10.15 压力变化 → 工况密度跟着变（密度未被手改时）
_rho_lo = w._read_density()
w.pressure_input.setText('1.0')
check('10.15 压力升到 1.0MPa 密度变大', w._read_density() > _rho_lo, f'{w._read_density():.2f}')

# 10.16 手改密度后，压力变化不覆盖
w.density_input.setText('9.0')
w.pressure_input.setText('0.2')
check('10.16 手改密度后压力变化不覆盖（仍 9.0）',
      approx(w._read_density(), 9.0, 1e-6), f'{w._read_density()}')

# 10.17 手册无压力范围的气体档：压力行强制显示（折算必须用到）
w.fluid_combo.setCurrentText('天然气')
w.condition_combo.setCurrentText('天然气')
check('10.17 天然气压力行仍显示且默认 0.10',
      not w.pressure_input.isHidden() and w.pressure_input.text() == '0.10', w.pressure_input.text())
check('10.18 天然气流量单位标签为 Nm³/h', 'Nm³/h' in w.flow_label.text(), w.flow_label.text())

# 10.19 结果页密度口径说明
_note_gas = w._density_note('压缩气体')
_note_liq = w._density_note('水及粘度相似的液体')
check('10.19 气体结果页注明「工况密度，标态 x」',
      '工况密度' in _note_gas and '标态' in _note_gas, _note_gas)
check('10.20 液体结果页注明「管径与密度无关」', '无关' in _note_liq, _note_liq)

# 10.21 自定义档：密度由用户填，切条件不被刷新覆盖
w.fluid_combo.setCurrentText('自定义粘性液体(按粘度推荐)')
check('10.21 自定义档切过来密度填淀粉糖典型 1200',
      w.density_input.text().startswith('1200'), w.density_input.text())
w.density_input.setText('1350')
w._refresh_density()
check('10.22 自定义档密度不被自动刷新覆盖（仍 1350）',
      approx(w._read_density(), 1350, 1e-6), w.density_input.text())

# 10.23 清空复位
w.clear_inputs()
check('10.23 清空后密度回 1200 且手改标记复位',
      w.density_input.text() == '1200' and w._density_manual is False, w.density_input.text())

# ══════════════════ Part 11: 固液浆料档（Thomas/OT 临界流速 + K-D 表观粘度）══════════════════
print('\n── Part 11: 浆料档 ──')
SF = mod.管径计算.SLURRY_FLUID

check('11.1 浆料档已注册到 fluid_ranges', SF in w.fluid_ranges)
check('11.2 浆料档出现在流体下拉里',
      SF in [w.fluid_combo.itemText(i) for i in range(w.fluid_combo.count())])

# 含固换算：质量浓度 → 体积分数 / 浆料密度（手算锚点）
phi_coal = w.slurry_volume_fraction(20, 1900, 1000)
rho_coal = w.slurry_density(20, 1900, 1000)
check('11.3 活性炭 20wt% → 体积分数 0.11628',
      approx(phi_coal, 0.116279, 1e-4), f'{phi_coal:.6f}')
check('11.4 活性炭 20wt% → 浆料密度 1104.65',
      approx(rho_coal, 1104.651, 1e-5), f'{rho_coal:.3f}')
check('11.5 0.5% 稀浆密度 1002.37（接近水）',
      approx(w.slurry_density(0.5, 1900, 1000), 1002.374, 1e-5),
      f"{w.slurry_density(0.5, 1900, 1000):.3f}")

# Krieger-Dougherty：η_r = (1−φ/0.63)^(−1.575)
_eta = w.slurry_apparent_viscosity(phi_coal, 0.001)
_eta_ref = 0.001 * (1 - phi_coal / 0.63) ** (-2.5 * 0.63)
check('11.6 表观粘度 = 水 1mPa·s × K-D 系数 → 1.379 mPa·s',
      approx(_eta, _eta_ref, 1e-9) and approx(_eta * 1000, 1.379, 1e-3),
      f'{_eta * 1000:.4f}')
check('11.7 K-D 在 φ→φmax 处失效（返回 None 而非无穷）',
      w.slurry_apparent_viscosity(0.70, 0.001) is None)

# Thomas(1979) 独立手算：9.0·[μg(S−1)/ρ]^0.37·(ρD/μ)^0.11
_vc40, _m40 = w.slurry_critical_velocity(20, 40, 1900, 1000, 0.001, phi_coal)
_vc40_ref = 9.0 * (0.001 * 9.81 * 0.9 / 1000) ** 0.37 * (1000 * 0.04 / 0.001) ** 0.11
check('11.8 活性炭 d50=20μm DN40 临界流速 = Thomas 0.3896 m/s',
      approx(_vc40, _vc40_ref, 1e-9) and approx(_vc40, 0.3896, 1e-3),
      f'{_vc40:.4f}')
check('11.9 细颗粒（<74μm）用 Thomas 式', _m40 == 'Thomas 式', _m40)

# 临界流速随管径单调增（Thomas 含 D^0.11）
_vcs = [w.slurry_critical_velocity(20, D, 1900, 1000, 0.001, phi_coal)[0]
        for D in (25, 50, 100, 200)]
check('11.10 临界流速随管径单调增', all(b > a for a, b in zip(_vcs, _vcs[1:])),
      str([round(v, 3) for v in _vcs]))

# 粗颗粒：OT 式参与取大，且浓度升高时临界流速上升
_vc_dry500, _m_dry = w.slurry_critical_velocity(1500, 100, 1400, 1000, 0.001, 0.05)
_vc_dry500_hi, _ = w.slurry_critical_velocity(1500, 100, 1400, 1000, 0.001, 0.25)
check('11.11 粗颗粒（≥74μm）走 OT 参与取大', _m_dry == 'Oroskar-Turian 式', _m_dry)
check('11.12 浓浆临界流速高于稀浆（OT 浓度项生效）',
      _vc_dry500_hi > _vc_dry500,
      f'{_vc_dry500:.3f} → {_vc_dry500_hi:.3f}')

# 推荐流速：经验下限主导（低浓度），且有磨损上限
check('11.13 细颗粒稀浆推荐流速 = 经验下限 1.2 m/s',
      approx(w.slurry_velocity(20, 1900, 1000, 0.001, 0.01), 1.2, 1e-6))
check('11.14 粗颗粒推荐流速上限 = 1.5 m/s',
      approx(w.slurry_velocity(1500, 1400, 1000, 0.001, 0.02), 1.5, 1e-6))
check('11.15 树脂磨损上限 2.0，其余 2.5',
      w.slurry_max_velocity('离子交换树脂') == 2.0
      and w.slurry_max_velocity('硅藻土(助滤剂)') == 2.5)

# 页面联动
w.clear_inputs()
w.fluid_combo.setCurrentText(SF)
check('11.16 切浆料档：条件为「按固相与浓度自动推荐」',
      w.condition_combo.currentText() == '按固相与浓度自动推荐',
      w.condition_combo.currentText())
check('11.17 切浆料档：固相行显示', not w.solid_combo.isHidden())
check('11.18 切浆料档：压力行隐藏（浆料按 m³/h 选型）', w.pressure_input.isHidden())
check('11.19 切浆料档：粘度框改作「液相粘度」',
      '液相' in w.viscosity_label.text(), w.viscosity_label.text())
check('11.20 默认硅藻土 3% → 密度自动填 1016.6',
      approx(w._read_density(), 1016.6, 1e-3), w.density_input.text())
check('11.21 默认推荐流速 = 1.20 m/s（细颗粒防沉积下限）',
      approx(float(w.velocity_input.text()), 1.2, 1e-6), w.velocity_input.text())

w.solid_combo.setCurrentText('活性炭(粉末)')
check('11.22 换固相：d50 自动带回 20 μm', w.solid_d50_input.text() == '20',
      w.solid_d50_input.text())
w.solid_pct_input.setText('20')
check('11.23 改浓度 20%：浆料密度跟到 1104.7',
      approx(w._read_density(), 1104.651, 1e-3), w.density_input.text())
check('11.24 改浓度 20%：表观粘度入压降口径（1.38 mPa·s）',
      approx(w._current_viscosity() * 1000, 1.379, 1e-3),
      f'{w._current_viscosity() * 1000:.4f}')

# 结果页
w.flow_input.setText('5')
w.calculate()
_txt = w.result_text.toPlainText()
check('11.25 浆料结果页含「浆料校核」段', '浆料校核' in _txt)
check('11.26 结果页给出临界不淤流速与设计最低流速',
      '临界不淤流速' in _txt and '设计最低流速' in _txt)
check('11.27 结果页给出磨损上限判定', '磨损上限' in _txt)
check('11.28 结果页含压降校核（HG/T 20570-95）',
      '压降校核' in _txt and 'HG/T 20570-95' in _txt)

# 历史记录
_h = w._get_history_data()
check('11.29 历史记录含固相/浓度/粒径',
      _h['inputs'].get('固相') == '活性炭(粉末)'
      and _h['inputs'].get('固相浓度_wt%') == 20
      and _h['inputs'].get('粒径_d50_um') == 20, str(_h['inputs'])[:120])
check('11.30 历史记录含临界不淤流速',
      '临界不淤流速_m_s' in _h['outputs'], str(_h['outputs']))
check('11.31 历史记录粘度键改称「表观粘度」',
      '表观粘度_mPa_s' in _h['inputs'], str(list(_h['inputs'].keys())))

# 切回普通档：浆料段不再出现
w.fluid_combo.setCurrentText('葡萄糖浆')
w.condition_combo.setCurrentIndex(1)
w.flow_input.setText('50')
w.calculate()
_txt2 = w.result_text.toPlainText()
check('11.32 非浆料档结果页不含浆料校核', '浆料校核' not in _txt2)
check('11.33 非浆料档固相行隐藏', w.solid_combo.isHidden())

# 清空复位
w.clear_inputs()
check('11.34 清空后固相参数复位',
      w.solid_combo.currentText() == '硅藻土(助滤剂)'
      and w.solid_pct_input.text() == '3'
      and w.liquid_rho_input.text() == '1000',
      f'{w.solid_combo.currentText()}/{w.solid_pct_input.text()}/{w.liquid_rho_input.text()}')

# ══════════════════ Part 12: 流体下拉分组 + 搜索 ══════════════════
print('\n── Part 12: 分组与搜索 ──')
w.clear_inputs()
w.fluid_combo.setCurrentText('水及粘度相似的液体')   # 确定起点，便于断言「不跳档」

_GROUPED = set()
for _title, _items in mod.管径计算.FLUID_GROUPS:
    _GROUPED.update(_items)
check('12.1 分组覆盖全部 fluid_ranges（无漏项）',
      set(w.fluid_ranges) - _GROUPED == set(), sorted(set(w.fluid_ranges) - _GROUPED))
check('12.2 分组不含 fluid_ranges 之外的名字（无野项）',
      _GROUPED - set(w.fluid_ranges) == set(), sorted(_GROUPED - set(w.fluid_ranges)))
check('12.3 分组内无重复',
      sum(len(i) for _t, i in mod.管径计算.FLUID_GROUPS) == len(_GROUPED))

_ALL = [w.fluid_combo.itemText(i) for i in range(w.fluid_combo.count())]
check('12.4 每个 fluid_ranges 项都能在下拉里选到',
      all(f in _ALL for f in w.fluid_ranges),
      sorted(set(w.fluid_ranges) - set(_ALL)))

# 分组标题置灰不可选
_titles = [t for t in _ALL if t.startswith('-')]
check('12.5 占位项与分组标题都置灰不可选',
      all(w.fluid_combo.model().item(i).isEnabled() is False
          for i in range(w.fluid_combo.count())
          if w.fluid_combo.itemText(i).startswith('-')),
      _titles)
check('12.6 组数为 6（水/淀粉糖/酸碱盐/气体/有机溶剂/其他）',
      len(mod.管径计算.FLUID_GROUPS) == 6,
      [t for t, _ in mod.管径计算.FLUID_GROUPS])

# 关键字搜索
w.fluid_filter.setText('糖')
_hit = [w.fluid_combo.itemText(i) for i in range(w.fluid_combo.count())]
check('12.7 搜「糖」命中糖化液/脱色液/葡萄糖浆',
      {'糖化液', '脱色液', '葡萄糖浆'} <= set(_hit), _hit)
check('12.8 搜索后当前流体仍保留（不跳档）',
      w.fluid_combo.currentText() == '水及粘度相似的液体', w.fluid_combo.currentText())

w.fluid_filter.setText('炭')
_hit = [w.fluid_combo.itemText(i) for i in range(w.fluid_combo.count())]
check('12.9 搜「活性炭」的「炭」经别名命中浆料档',
      '浆料/悬浮液(含固)' in _hit, _hit)
w.fluid_filter.setText('硅藻土')
_hit = [w.fluid_combo.itemText(i) for i in range(w.fluid_combo.count())]
check('12.10 搜「硅藻土」也命中浆料档（别名）', '浆料/悬浮液(含固)' in _hit, _hit)
w.fluid_filter.setText('蒸汽')
_hit = [w.fluid_combo.itemText(i) for i in range(w.fluid_combo.count())]
check('12.11 搜「蒸汽」命中饱和/过热/二次蒸汽',
      {'饱和蒸汽', '过热蒸汽', '二次蒸汽'} <= set(_hit), _hit)

# 无匹配：不清空下拉，只给提示
_n_before = w.fluid_combo.count()
w.fluid_filter.setText('zzzz')
check('12.12 无匹配时不清空下拉（避免误以为可用）',
      w.fluid_combo.count() == _n_before and '无匹配' in w.filter_hint.text(),
      f'{w.fluid_combo.count()} / {w.filter_hint.text()}')

# 清空恢复
w.fluid_filter.setText('')
check('12.13 清空关键字恢复全部项',
      w.fluid_combo.count() == len(_ALL), f'{w.fluid_combo.count()} vs {len(_ALL)}')

# 关键回归：不可编辑下拉不会因 setCurrentText 静默新建条目
_n0 = w.fluid_combo.count()
w.fluid_combo.setCurrentText('不存在的流体XYZ')
check('12.14 setCurrentText 不存在的名字不会新建条目（防假档）',
      w.fluid_combo.count() == _n0 and w.fluid_combo.currentText() != '不存在的流体XYZ',
      f'{w.fluid_combo.count()} / {w.fluid_combo.currentText()}')

# 过滤后照常算
w.fluid_filter.setText('葡萄糖')
w.fluid_combo.setCurrentText('葡萄糖浆')
w.condition_combo.setCurrentIndex(1)
w.flow_input.setText('50')
w.calculate()
_t3 = w.result_text.toPlainText()
check('12.15 过滤状态下计算正常且流体类型正确',
      '葡萄糖浆' in _t3 and '推荐标准管径' in _t3)
w.fluid_filter.setText('')

# ── 汇总 ──
print('\n' + '=' * 50)
print(f'通过 {len(PASS)} 项, 失败 {len(FAIL)} 项')
if FAIL:
    for name, detail in FAIL:
        print(f'  FAIL: {name}  {detail}')
    sys.exit(1)
print('ALL PASS')
