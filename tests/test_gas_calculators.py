# -*- coding: utf-8 -*-
"""气体类计算器回归测试（状态换算 + 混合气体 + EOS + 湿空气 + 制冷剂物性）
纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_gas_calculators.py

核对依据与修复前 bug：
- 气体状态换算: Q_act = Q_std·(P_s/P_a)·(T_a/T_s)·Z；新增绝压/表压切换（表压+101.325）
  锚点: 1000 Nm³/h → 500kPa(绝)/20°C/Z=1 → 217.47 m³/h
- 混合气体: NASA cp (N2 300K=29.12 J/molK)、CE 粘度 (N2 300K≈17.7 μPa·s)、
  LK 压缩因子（与 PR 交叉验证 Δ<0.06）
  修复: cp 偏离项原为拍脑袋公式且 Pr 硬编码 101.325 与实际压力无关 → LK 数值积分偏离
- EOS: 立方求根/逸度系数原本正确（与积分恒等式偏差<1%）；
  修复: 剩余焓/熵解析式错误（PR/SRK/RK 的 α(T) 因子错）→
  H^R = RT(Z−1)−(a−Ta')·I(V)，统一因子 (1−β̄)，β̄=−κ√Tr/(1+κ(1−√Tr))；
  S^R=(H^R−RT·lnφ)/T 恒等式，G^R=RT·lnφ
  锚点: PR 甲烷 350K/2MPa H_R=−276.2 J/mol（独立数值积分 −275.9）
- 湿空气: Magnus psat、焓/比容/湿球能量平衡方程原本正确；
  修复: 湿球正向牛顿差分方向反了 → 永远收敛到干球温度
- 制冷剂: 修复 h_fg 恒为常数（Watson 关联式 0.6% 内命中 ASHRAE 三锚点）、
  T=0°C 被 `if T` 判为缺失、干度输入零引用、R1234yf 等借用参数无警示、
  ReportExporter 未导入（DOCX/PDF 按钮崩溃）
"""
import os
import sys
import math
import tempfile
import importlib.util

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CALC_DIR = os.path.join(ROOT, 'modules', 'chemical_calculations', 'calculators')
CHEM_DIR = os.path.join(ROOT, 'modules', 'chemical_calculations')
for p in [ROOT, os.path.join(ROOT, 'modules'), CHEM_DIR, CALC_DIR]:
    if p not in sys.path:
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

# ══════════════════ Part 1: 气体状态换算 ══════════════════
m1 = _load('t_gascv', os.path.join(CALC_DIR, 'gas_state_converter.py'))
w1 = m1.气体标态转压缩态()

w1.flow_input.setText("1000")
w1.standard_combo.setCurrentIndex(1)          # 0°C, 101.325 kPa
w1.pressure_type_combo.setCurrentIndex(0)     # 绝压
w1.actual_pressure_input.setText("500")
w1.actual_temp_input.setText("20")
w1.compress_combo.setCurrentIndex(1)          # Z=1.0
w1.calculate()
t1 = w1.result_text.toPlainText()
# 1000·(101.325/500)·(293.15/273.15) = 217.47
check("状态换算 绝压500→217.5 m³/h", "217.4" in t1 or "217.5" in t1, t1[:200])
check("状态换算 显示绝对压力", "绝对压力" in t1)

# 表压: 500 表压 → 601.325 绝压 → 1000·101.325/601.325·1.07320 = 180.9
w1.pressure_type_combo.setCurrentIndex(1)
w1.calculate()
t1b = w1.result_text.toPlainText()
check("状态换算 表压500→180.9 m³/h", "180.9" in t1b or "180.8" in t1b, t1b[:200])

# 压缩因子下拉切"请选择"后应保持可编辑（防永久只读）
w1.compress_combo.setCurrentIndex(0)
check("状态换算 请选择后可编辑", not w1.compress_input.isReadOnly())

# 历史记录
h1 = w1._get_history_data()
check("状态换算 历史含压力制式", h1["outputs"].get("绝对压力_kPa") == 601.325, str(h1))

# ══════════════════ Part 2: 气体混合物 ══════════════════
m2 = _load('t_gasmix', os.path.join(CALC_DIR, 'gas_mixture_properties_calculator.py'))

# 纯函数锚点
mu = m2._pure_viscosity_CE('氮气(N2)', 28.013, 300) * 1e6
check("CE 粘度 N2 300K≈17.7", abs(mu - 17.7) < 1.5, f"{mu:.2f}")
cp = m2._nasa_cp('氮气(N2)', 300)
check("NASA cp N2 300K=29.12", abs(cp - 29.12) < 0.3, f"{cp:.3f}")
z_lk = m2._lee_kesler_z(1.2, 1.0, 0.0)
check("LK Z(1.2,1,0)≈0.79", 0.70 < z_lk < 0.88, f"{z_lk:.3f}")

w2 = m2.GasMixturePropertiesCalculator()
w2.calculate()  # 默认 N2/O2 各 50%，25°C，101.325 kPa，理想气体
t2 = w2.result_text.toPlainText()
mw_mix = 0.5 * 28.013 + 0.5 * 31.999
rho_ideal = 101.325 * mw_mix / (8.314 * 298.15)
check("混合物 理想密度≈1.2265", "1.226" in t2, f"期望{rho_ideal:.4f}\n{t2[:300]}")

# 真实气体 8 MPa：密度应用 LK Z 修正，cp 偏离随压力变化
w2.mixture_type.setCurrentIndex(1)
w2.pressure_input.setText("8000")
w2.calculate()
t2b = w2.result_text.toPlainText()
r = w2._last_calc_results
check("混合物 真实Z<1 (8MPa)", 0.7 < r['z_factor'] < 1.0, f"Z={r['z_factor']:.3f}")
check("混合物 真实密度>理想", r['density'] > rho_ideal, f"ρ={r['density']:.4f}")
# cp 偏离: 8MPa 应大于常压
cp_low = m2.GasMixturePropertiesCalculator._cp_departure(298.15, r['tc_mix'], r['pc_mix'], r['omega_mix'], 101.325)
cp_hi = m2.GasMixturePropertiesCalculator._cp_departure(298.15, r['tc_mix'], r['pc_mix'], r['omega_mix'], 8000.0)
check("混合物 cp偏离随压力增大", cp_hi > cp_low + 0.3, f"低={cp_low:.3f} 高={cp_hi:.3f}")

# 摩尔分数校验
w2.pressure_input.setText("101.325")
w2.component_table.item(0, 1).setText("0.7")
w2.calculate()
check("混合物 摩尔分数和≠1 有提示", "摩尔分数" in w2.result_text.toPlainText())

# ══════════════════ Part 3: EOS ══════════════════
m3 = _load('t_eos', os.path.join(CALC_DIR, 'eos_calculator.py'))

params = m3.EOSCalculator._eos_params("Peng-Robinson方程", 190.56, 4599, 0.0115, 300, 300 / 190.56)
Z = m3.EOSCalculator._solve_Z("Peng-Robinson方程", params, 300, 101.325)
check("EOS PR 甲烷常压 Z≈0.998", abs(Z - 0.998) < 0.005, f"Z={Z:.5f}")

# 剩余性质锚点（独立数值积分验证过的值）
params350 = m3.EOSCalculator._eos_params("Peng-Robinson方程", 190.56, 4599, 0.0115, 350, 350 / 190.56)
Z350 = m3.EOSCalculator._solve_Z("Peng-Robinson方程", params350, 350, 2000.0)
HR, SR, GR = m3.EOSCalculator._residual_properties(
    "Peng-Robinson方程", params350, Z350, 350.0, 2000.0, 190.56, 0.0115)
check("EOS PR甲烷350/2MPa H_R≈-276", abs(HR - (-276.2)) < 5, f"{HR:.1f}")
check("EOS PR甲烷350/2MPa S_R≈-0.585", abs(SR - (-0.5849)) < 0.02, f"{SR:.4f}")
phi350 = m3.EOSCalculator._fugacity_coeff("Peng-Robinson方程", params350, Z350, 350, 2000)
GR_expect = 8.314 * 350 * math.log(phi350)
check("EOS G_R=RT·lnφ", abs(GR - GR_expect) < 1, f"{GR:.1f} vs {GR_expect:.1f}")

# RK 教科书锚点: H_R/RT = Z-1-(3A/2B)ln(1+B/Z)
params_rk = m3.EOSCalculator._eos_params("Redlich-Kwong方程", 304.21, 7383, 0.2236, 350, 350 / 304.21)
Z_rk = m3.EOSCalculator._solve_Z("Redlich-Kwong方程", params_rk, 350, 8000.0)
a, b = params_rk['a'], params_rk['b']
A = a * 8e6 / (8.314 * 350) ** 2
B = b * 8e6 / (8.314 * 350)
HR_rk = 8.314 * 350 * (Z_rk - 1 - 1.5 * (A / B) * math.log(1 + B / Z_rk))
HR_rk_mod, _, _ = m3.EOSCalculator._residual_properties(
    "Redlich-Kwong方程", params_rk, Z_rk, 350.0, 8000.0, 304.21, 0.2236)
check("EOS RK 教科书 3A/2B 锚点", abs(HR_rk_mod - HR_rk) < 2, f"{HR_rk_mod:.1f} vs {HR_rk:.1f}")

# UI 全链路
w3 = m3.EOSCalculator()
check("EOS 默认甲烷参数填充", w3.tc_input.text() == "190.56", w3.tc_input.text())
w3.eos_type.setCurrentIndex(4)  # PR
w3.temperature_input.setText("350")
w3.pressure_input.setText("2000")
w3.calculate()
t3 = w3.result_text.toPlainText()
check("EOS UI 输出 H^R≈-276", "-276" in t3 or "-275" in t3, t3[:300])
check("EOS UI 输出逸度", "逸度系数" in t3)

# 未计算时生成报告 → None
w3b = m3.EOSCalculator()
check("EOS 未计算报告=None", w3b.generate_report() is None)

# ══════════════════ Part 4: 湿空气 ══════════════════
m4 = _load('t_wetair', os.path.join(CALC_DIR, 'wet_air_calculator.py'))

check("湿空气 ReportExporter 已导入", hasattr(m4, 'ReportExporter'))

w4 = m4.WetAirCalculator()
w4.rh_input.setText("60")
w4.humidity_input.clear()
w4.wet_bulb_input.clear()
w4.dew_point_input.clear()
w4.calculate()
t4 = w4.result_text.toPlainText()
check("湿空气 W=0.0119", "11.89" in t4, t4[:200])
check("湿空气 露点16.7", "16.7" in t4)
check("湿空气 湿球19.5±0.5", "19.0" in t4 or "19.1" in t4 or "19.2" in t4
      or "19.3" in t4 or "19.4" in t4 or "19.5" in t4 or "19.6" in t4 or "19.7" in t4, t4)
check("湿空气 焓≈55.4", "55.4" in t4 or "55.5" in t4)

# 多参数时显示基准说明（单独实例保留多个输入）
w4m = m4.WetAirCalculator()  # 默认 RH/绝对湿度/湿球/露点 全部有值
w4m.calculate()
check("湿空气 基准说明(多参数)", "基准" in w4m.result_text.toPlainText()
      and "相对湿度" in w4m.result_text.toPlainText())

# 湿球反向（原 bug: 正向牛顿方向反 → 永远等于干球）
w4b = m4.WetAirCalculator()
w4b.rh_input.clear()
w4b.wet_bulb_input.setText("19.3")
w4b.calculate()
rh_back = w4b._last_results['rh']
check("湿空气 湿球19.3反求RH≈59", abs(rh_back - 58.9) < 2.5, f"RH={rh_back:.1f}")

# 正向湿球不再是干球温度
w4c = m4.WetAirCalculator()
w4c.calculate()  # 默认 25°C / 60%RH
wb_fwd = w4c._last_results['wet_bulb']
check("湿空气 正向湿球≈19.5(≠25)", abs(wb_fwd - 19.5) < 0.8, f"tw={wb_fwd:.2f}")

# 未计算报告=None
w4d = m4.WetAirCalculator()
w4d.rh_input.clear(); w4d.humidity_input.clear(); w4d.wet_bulb_input.clear(); w4d.dew_point_input.clear()
check("湿空气 未计算报告=None", w4d.generate_report() is None)

# ══════════════════ Part 5: 制冷剂物性 ══════════════════
m5 = _load('t_refprop', os.path.join(CALC_DIR, 'refrigerant_properties_calculator.py'))

check("制冷剂 ReportExporter 已导入", hasattr(m5, 'ReportExporter'))

# Watson 潜热锚点
L25 = m5.refrigerant_eos._latent_heat(m5.refrigerant_eos.REFRIGERANTS['R134a'], 298.15)
check("制冷剂 Watson hfg(25°C)≈178", abs(L25 - 178.3) < 2.0, f"{L25:.1f}")
Ltb = m5.refrigerant_eos._latent_heat(m5.refrigerant_eos.REFRIGERANTS['R717'], 239.82)
check("制冷剂 氨 hfg(Tb)=1369", abs(Ltb - 1369.0) < 1.0, f"{Ltb:.1f}")

w5 = m5.RefrigerantPropertiesCalculator()
w5.calculation_type.setCurrentIndex(0)  # 饱和性质
w5.temperature_input.setText("25")
w5.calculate()
t5 = w5.result_text.toPlainText()
check("制冷剂 R134a 25°C Psat≈666.7", "666." in t5 or "667." in t5, t5[:300])
check("制冷剂 R134a hfg≈178", "178." in t5 or "177." in t5, t5)

# 干度接入
w5.quality_input.setText("0.5")
w5.calculate()
t5b = w5.result_text.toPlainText()
check("制冷剂 湿蒸汽混合物显示", "湿蒸汽混合物" in t5b and "x=0.500" in t5b, t5b[:400])
r5b = w5._last_calc_results
hf, hfg = r5b['hf'], r5b['hfg']
check("制冷剂 mixture_h=hf+0.5hfg", abs(r5b['mixture_h'] - (hf + 0.5 * hfg)) < 0.5,
      f"{r5b['mixture_h']:.2f} vs {hf + 0.5 * hfg:.2f}")

# T=0°C 不再被判为缺失
w5.quality_input.setText("1.0")
w5.temperature_input.setText("0")
w5.calculate()
check("制冷剂 T=0°C 正常计算", "计算错误" not in w5.result_text.toPlainText()
      and w5._last_calc_results.get('temperature') == 0.0,
      w5.result_text.toPlainText()[:200])

# 借用参数警示（R1234yf→R134a 参数）
w5c = m5.RefrigerantPropertiesCalculator()
w5c.refrigerant_selection.setCurrentText("R1234yf")
w5c.temperature_input.setText("25")
w5c.calculate()
check("制冷剂 借用参数警示", "借用相近工质参数" in w5c.result_text.toPlainText(),
      w5c.result_text.toPlainText()[:200])
# 正常工质无警示
w5d = m5.RefrigerantPropertiesCalculator()
w5d.refrigerant_selection.setCurrentText("R717 (氨)")
w5d.temperature_input.setText("25")
w5d.calculate()
check("制冷剂 氨无警示", "借用相近工质参数" not in w5d.result_text.toPlainText())

# 循环分析 COP 合理性
w5e = m5.RefrigerantPropertiesCalculator()
w5e.calculation_type.setCurrentIndex(4)
w5e.temperature_input.setText("-5")
w5e.cond_temp_input.setText("40")
w5e.calculate()
cop = w5e._last_calc_results.get('cop', 0)
check("制冷剂 COP(-5/40)≈3.67 合理", 3.0 < cop < 6.5, f"COP={cop:.2f}")

# ══════════════════ 汇总 ══════════════════
print("=" * 60)
print(f"总结: {len(PASS)} 通过, {len(FAIL)} 失败")
if FAIL:
    for name, detail in FAIL:
        print(f"  FAIL: {name}  [{detail}]")
    sys.exit(1)
print("全部通过")
