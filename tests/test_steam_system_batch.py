# -*- coding: utf-8 -*-
"""蒸汽系统族计算器回归测试
    蒸汽管径流量 + 长输蒸汽管道温降 + 蒸汽空消

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_steam_system_batch.py

核对依据与锚点（手算 + IAPWS-IF97）：
- 蒸汽管径流量（毁灭级 bug）：
    * 修复前调用 _IAPWS_MODULE.tsat_p/region2/region4_saturation——这些函数在
      steam_iapws 模块中根本不存在（实际为 saturation_temperature/steam_properties），
      IAPWS 路径必然 AttributeError → 永远走 fallback 经验公式；
    * fallback 经验式 0.5·P_bar/(T+150) 在 1MPa/200°C 给出 0.014 kg/m³（真值 5.03），
      偏小 350 倍 → 比容虚大 → 管径永远推荐到最大档。
  修复后：steam_properties(绝压, T)（入参表压 + 0.101325），fallback 改理想气体。
  锚点：1.0 MPa(g)/200°C → ρ≈5.03 kg/m³（理想气体 5.024，IF97 5.03，±5%）；
  1000 kg/h → 需求内径 53.0mm → 向上取整 DN65（修复前取最近可能偏小），
  实际流速 ≈16.6 m/s；DN50 @25m/s → 最大流量 ≈889 kg/h。

- 长输蒸汽：
  * 修复前"饱和蒸汽"下拉是死参数（steam_type 传入后从未使用）——饱和蒸汽按
    单相气体 cp 降温处理，出口温度会降到 Tsat 以下（物理上不可能，只会冷凝）；
  * fallback 密度 P·100/(R·T) 少乘 10（P_MPa·1000/(0.4615·T_K) 才对）；
  * 压力为表压口径（修复前无标注按绝压查物性）。
  修复后：饱和模式温度跟随 Tsat(P)，散热→冷凝量=Σq_seg/h_fg；过热模式校验
  入口温度>Tsat；末端压力守卫（≤常压+0.005 报错）。
  锚点（10t/h, 200°C, 1.0MPa(g), 1000m, DN200, 50mm 保温 λ=0.04）：
    过热出口 T≈180±8°C，压降 ≈0.07 MPa，热损失 ≈90 kW，流速 ≈18 m/s；
    饱和出口 T≈Tsat(P_out)≈180°C，温降 <8°C，冷凝量 ≈170 kg/h。

- 蒸汽空消：
  * 崩溃 bug：材质下拉显示 display 名（"碳钢 Q235"/"搪玻璃（碳钢基体）"/"钛材 TA2"），
    直接拿显示名查 MATERIAL_DB → KeyError 崩溃（选碳钢/搪玻璃/钛必崩）；
  * 校验缺失：灭菌温度 ≥ 蒸汽饱和温度时物理不可达（如 0.05MPa(g) 蒸汽 Tsat=111°C
    想灭菌 121°C），修复前不报错照算。
  锚点（罐体 10m³, H/D=2, 304, 121/25°C, 0.3MPa(g), 岩棉50, 30min, K=1.2, η=0.95）：
    D=(4V/πk)^(1/3)=1.8528m, 壁厚 6mm, A=27.40m², 重量 1304kg,
    q_heat=62.6MJ, q_loss=14.2MJ, 实际蒸汽 ≈45.5 kg（42~49 区间）；
  管道（DN50 60.3×3.9, 50m, 304）：管重 274kg, 实际蒸汽 ≈10.7 kg。
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

def _re(pat, text):
    m = __import__('re').search(pat, text)
    return float(m.group(1)) if m else None

# ══════════════════ Part 1: 蒸汽管径流量 ══════════════════
print('── Part 1: 蒸汽管径流量 ──')
m1 = _load('t_spipe', os.path.join(CALC_DIR, 'steam_pipe_calculator.py'))
sp = m1.蒸汽管径流量()

# 密度：1.0 MPa(g)/200°C 过热 → 理想气体 5.024，IF97 ≈5.03 kg/m³
rho = sp.calculate_steam_density(1.0, 200.0)
check("密度 1.0MPa(g)/200°C ≈ 5.03 kg/m³（修复前 0.014，偏小 350 倍）",
      4.7 < rho < 5.4, f'{rho:.4f}')

# 饱和蒸汽：0.5 MPa(g) → Tsat(0.6013 绝)≈158.9°C，v_g=0.3157 → ρ≈3.17
rho_sat = sp.calculate_steam_density(0.5, 158.8)
check("饱和密度 0.5MPa(g) ≈ 3.17 kg/m³", 2.9 < rho_sat < 3.5, f'{rho_sat:.4f}')

# 管径模式：1000 kg/h → 内径 53.0mm → 向上取整 DN65，流速 ≈16.6
sp.pressure_input.setText("1.0")
sp.temperature_input.setText("200")
sp.flow_input.setText("1000")
sp.calculate_steam_pipe()
txt = sp.result_text.toPlainText()
check("结果含 DN65（向上取整，修复前取最近可能偏小）", "DN65" in txt)
v_act = _re(r'实际蒸汽流速:\s*([\d.]+)', txt)
check("实际流速 ≈16.6 m/s", v_act is not None and 15.5 < v_act < 18.0, str(v_act))
check("结果标注表压/绝压", "表压" in txt and "绝压" in txt)

# 边界：需求内径恰为标准档时取等号
check("52.1mm → DN65（≥ 才取）",
      next((d for d in [15, 20, 25, 32, 40, 50, 65] if d >= 52.1), 65) == 65)

# 流量模式：DN50 @25m/s → ≈889 kg/h
sp.mode_buttons["根据管径计算流量"].setChecked(True)
sp.on_mode_changed("根据管径计算流量")
sp.pressure_input.setText("1.0")
sp.temperature_input.setText("200")
sp.diameter_input.setText("50")
sp.calculate_steam_pipe()
txt2 = sp.result_text.toPlainText()
q_max = _re(r'最大蒸汽流量:\s*([\d.]+)', txt2)
check("DN50 @25m/s 最大流量 ≈889 kg/h", q_max is not None and 860 < q_max < 915, str(q_max))

# clear 恢复默认
sp.clear_inputs()
check("clear 后压力恢复 1.0", sp.pressure_input.text() == "1.0", sp.pressure_input.text())
check("clear 后温度恢复 200", sp.temperature_input.text() == "200", sp.temperature_input.text())
check("clear 后流量恢复 1000", sp.flow_input.text() == "1000", sp.flow_input.text())

# ══════════════════ Part 2: 长输蒸汽 ══════════════════
print('── Part 2: 长输蒸汽管道温降 ──')
m2 = _load('t_ldsteam', os.path.join(CALC_DIR, 'long_distance_steam_pipe_calculator.py'))
ld = m2.LongDistanceSteamPipeCalculator()

# 默认即饱和蒸汽模式（下拉 index 0）
check("默认模式为饱和蒸汽", ld.steam_type.currentText() == "饱和蒸汽")

# —— 饱和蒸汽（修复前 steam_type 是死参数，按单相气体降温到 Tsat 以下）——
ld.calculate()
txt = ld.result_text.toPlainText()
t_out = _re(r'出口温度：([\d.]+)', txt)
p_out = _re(r'出口压力：([\d.]+)', txt)
dt = _re(r'温度降：([\d.]+)', txt)
cond = _re(r'沿途冷凝蒸汽量：([\d.]+)', txt)
hl = _re(r'总热损失：([\d.]+)', txt)
check("饱和：出口温度≈Tsat(P_out)，180~187°C", t_out is not None and 175 < t_out < 188, str(t_out))
check("饱和：出口压力绝压 0.95~1.09 MPa", p_out is not None and 0.95 < p_out < 1.09, str(p_out))
check("饱和：温降 < 8°C（只有 Tsat 差）", dt is not None and 0 <= dt < 8, str(dt))
check("饱和：输出冷凝量 80~300 kg/h", cond is not None and 80 < cond < 300, str(cond))
check("饱和：热损失 60~130 kW", hl is not None and 60 < hl < 130, str(hl))

# —— 过热蒸汽 ——
ld.steam_type.setCurrentIndex(1)
ld.calculate()
txt2 = ld.result_text.toPlainText()
t_out2 = _re(r'出口温度：([\d.]+)', txt2)
dt2 = _re(r'温度降：([\d.]+)', txt2)
v2 = _re(r'蒸汽流速：([\d.]+)', txt2)
check("过热：出口温度 170~195°C", t_out2 is not None and 170 < t_out2 < 195, str(t_out2))
check("过热：温降 8~30°C", dt2 is not None and 8 < dt2 < 30, str(dt2))
check("过热：流速 15~25 m/s", v2 is not None and 15 < v2 < 25, str(v2))
check("过热：无冷凝量行", "冷凝" not in txt2)

# —— 过热校验：入口温度低于 Tsat ——
ld.inlet_temp_input.setText("150")  # Tsat(1.1013)≈184
ld.calculate()
check("过热模式入口 150°C 报'不是过热蒸汽'", "不是过热蒸汽" in ld.result_text.toPlainText(),
      ld.result_text.toPlainText()[:60])

# —— 压力守卫：DN50 → 首段压降超限 ——
ld.inlet_temp_input.setText("200")
ld.pipe_diameter_input.setText("50")
ld.calculate()
check("DN50 长输触发'接近常压'守卫", "接近常压" in ld.result_text.toPlainText(),
      ld.result_text.toPlainText()[:60])

# clear 恢复默认
ld.clear_inputs()
check("clear 后流量恢复 10", ld.flow_rate_input.text() == "10", ld.flow_rate_input.text())
check("clear 后管径恢复 200", ld.pipe_diameter_input.text() == "200")

# ══════════════════ Part 3: 蒸汽空消 ══════════════════
print('── Part 3: 蒸汽空消 ──')
m3 = _load('t_ster', os.path.join(CALC_DIR, 'steam_sterilization_calculator.py'))
st = m3.SteamSterilizationCalculator()

# 罐体默认锚点
st._calc_tank()
r = st._last_results
check("罐体内径 = 1.853 m", abs(r['D'] - 1.8528) < 0.001, f"{r['D']:.4f}")
check("壁厚 = 6 mm", r['wall_thickness'] == 6, str(r['wall_thickness']))
check("外表面积 = 27.4 m²", abs(r['A_total'] - 27.40) < 0.1, f"{r['A_total']:.2f}")
check("罐体重量 ≈1304 kg", 1250 < r['tank_weight'] < 1360, f"{r['tank_weight']:.0f}")
check("加热热负荷 ≈62.6 MJ", 60.0 < r['q_heat']/1000 < 65.0, f"{r['q_heat']/1000:.1f}")
check("散热 ≈14.2 MJ", 13.5 < r['q_loss']/1000 < 15.0, f"{r['q_loss']/1000:.1f}")
check("实际蒸汽量 42~49 kg（≈4.5 kg/m³ 罐容）",
      42 < r['steam_mass_actual'] < 49, f"{r['steam_mass_actual']:.1f}")

# 崩溃修复：选 搪玻璃/碳钢/钛 不再 KeyError
for disp, cp_exp in [("碳钢 Q235", 460), ("搪玻璃（碳钢基体）", 460), ("钛材 TA2", 540)]:
    st.input_widgets[m3.K_MATERIAL].setCurrentText(disp)
    st._calc_tank()  # 修复前 KeyError 直接崩
    r2 = st._last_results
    check(f"材质'{disp}' 可正常计算", r2['material_display'] == disp and
          m3.MATERIAL_DB[r2['material']]['cp'] == cp_exp)

# 校验：灭菌温度 ≥ Tsat 报错（0.05MPa(g) Tsat=111°C）
st.input_widgets[m3.K_MATERIAL].setCurrentIndex(0)
st.input_widgets[m3.K_T_STERILIZE].setText("121")
st.input_widgets[m3.K_P_STEAM].setText("0.05")
try:
    st._calc_tank()
    check("0.05MPa(g) 灭菌 121°C 应报错", False)
except ValueError as e:
    check("0.05MPa(g) 灭菌 121°C 应报错", "饱和温度" in str(e), str(e)[:50])

# 管道模式（先选中模式按钮，再切换输入界面）
st.mode_buttons["管道消毒"].setChecked(True)
st.setup_calculation_mode(1)
st._calc_pipe()
r3 = st._last_results
check("DN50 管重 ≈274 kg", 265 < r3['pipe_weight'] < 285, f"{r3['pipe_weight']:.0f}")
check("管道消毒蒸汽 ≈10.7 kg", 9.5 < r3['steam_mass_actual'] < 12.0,
      f"{r3['steam_mass_actual']:.1f}")
check("管道结果用 display 名", r3['material_display'] == "304不锈钢")

# clear_all 恢复默认
st.clear_all()
check("clear_all 后仍为管道模式且长度恢复 50",
      st.input_widgets[m3.K_PIPE_LENGTH].text() == "50")

# ══════════════════ 汇总 ══════════════════
print()
print(f'══════════ 总计: {len(PASS)} 通过, {len(FAIL)} 失败 ══════════')
if FAIL:
    for name, detail in FAIL:
        print(f'  ✗ {name}  [{detail}]')
    sys.exit(1)
print('全部通过 ✅')
