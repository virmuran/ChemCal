# -*- coding: utf-8 -*-
"""管件/管路类计算器回归测试
    篮式过滤器 + 管道跨距 + 管道间距 + 可压缩流体压降 + 压力管道定义

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_pipe_filter_batch.py

核对依据：
- 篮式过滤器：kLa 无关；有效面积 A=Q/(3600v)；筛网内径 D=√(A/(π·1.2))；
  压降 Δp=32μvδ/(ε·d_w²)；应力系数 = P·D/(2δ[σ])
  默认锚点(150m³/h, 0.1m/s, 3000μm, 35%, 2mm, 1.6MPa, 137MPa)：
    A=0.4167 m², D=332.5mm→圆整340, H=398.9→400, 压降0.0127kPa, 应力系数0.971, 管径162.9mm
  重量：底(上下)πR²·0.005×8000、筒体 πDL·0.005×8000、篮筐 πDL·0.003×8000+πR²·0.003×8000
    + 法兰重量（HG/T 20592 档位表）
- 管道跨距：简支梁均布载荷
    应力控制 L=√(8σZ/w)；挠度控制 δ=5wL⁴/(384EI)=L/360 → L=(384EI/(1800w))^(1/3)
  默认(DN100 SCH40 碳钢, 水, 50mm 硅酸铝保温, σ=137.9MPa)：
    w=288.91 N/m, L_应力=14.18m, L_挠度=7.63m, 推荐7.63m，挠度利用率≈100%
  修复前挠度利用率漏乘 5（显示 ~20%）
- 管道间距（SH 3012）：基础间距=(OD1+OD2)/2+50；法兰间距=(FD1+FD2)/2+25；取大者
  法兰外径必须用 HG/T 20592 的【法兰外径 D】，修复前把【螺栓孔中心圆直径 K】当 D 用
    → DN100 PN16 用 180 而不是 220，法兰间距偏小 40mm，相邻法兰实际会干涉
  默认锚点：DN100/PN100 均为 PN16 → 基础 164.3 / 法兰 245 → 最终 245mm
- 可压缩流体压降：Weymouth / Panhandle A 公制式（Menon）
    Q[m³/d]=3.7435e-3·(Tb/Pb)·[(P1²−P2²)/(G·T·Le·Z)]^0.5·D^2.667·E
    修复前系数 0.0330 且缺 G、T、Z 归一化 → 100mm 管算出数百万 m³/h（偏 6 个数量级）
  默认(P1=500,P2=400kPa,T=20℃,D=100mm,Le=150m,air)：
    G=1.0, Q_Weymouth≈4406 m³/h, Q_Panhandle≈7308 m³/h（同为 10³ 量级）
- 压力管道定义（TSG D0001-2009）：判据是【最高工作压力】≥0.1MPa(表压) 且 DN>25mm，
  修复前误用【设计压力】判定（设计压力>工作压力 → 把非压力管道误判为压力管道）
  GC1 需含甲/乙类可燃气体与液化烃（修复前完全缺失 → 可燃气体 5MPa 漏判为 GC2）
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

from PySide6.QtWidgets import QApplication, QMessageBox, QRadioButton

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

# ══════════════════ Part 1: 篮式过滤器 ══════════════════
print('── Part 1: 篮式过滤器 ──')
m1 = _load('t_basket', os.path.join(CALC_DIR, 'basket_filter_design_calculator.py'))
bf = m1.篮式过滤器()

# 默认输入：150 m³/h, v=0.1 m/s, 3000 μm, 开孔率 35%, 支撑网 2mm, 1.6MPa, [σ]=137MPa
A_exp = 150.0 / (3600 * 0.1)
check("有效面积 = 0.4167 m²", abs(bf.calculate_effective_area(150.0, 0.1) - A_exp) < 1e-6,
      f'{bf.calculate_effective_area(150.0, 0.1):.6f}')

D_exp = math.sqrt(A_exp / (math.pi * 1.2)) * 1000
check("筛网内径 = 332.5 mm", abs(bf.calculate_screen_diameter(A_exp) - D_exp) < 0.01,
      f'{bf.calculate_screen_diameter(A_exp):.2f}')
check("筛网高度 = 1.2×D = 398.9 mm", abs(bf.calculate_screen_height(D_exp) - 1.2 * D_exp) < 0.01)

dw = bf.calculate_wire_diameter(3000.0)
check("丝径 = 0.4×3000/1e6 = 0.0012 m", abs(dw - 0.0012) < 1e-9, f'{dw}')

# 压降 32·μ·v·δ / (ε·d_w²) = 6.4128e-6/5.04e-7 = 12.724 Pa = 0.012724 kPa
dp_exp = 32 * 0.001002 * 0.1 * 0.002 / ((35.0 / 100) * dw ** 2) / 1000
check("压降 = 0.01272 kPa", abs(bf.calculate_pressure_drop(0.001002, 0.1, 0.002, 35.0, dw) - dp_exp) < 1e-6,
      f'{bf.calculate_pressure_drop(0.001002, 0.1, 0.002, 35.0, dw):.6f}')
check("压降远小于允许压降 50 kPa", dp_exp < 50)

# 应力系数 = P·D / (2·δ·[σ]) = 1600×0.33245/(2×0.002×137000) = 0.971
sf = bf.calculate_stress_factor(1.6, D_exp, 0.002, 137.0)
sf_exp = (1.6 * 1000 * (D_exp / 1000)) / (2 * 0.002 * 137.0 * 1000)
check("应力系数 = 0.971", abs(sf - sf_exp) < 1e-6, f'{sf:.4f}')
check("应力系数 ≤ 1.0", sf <= 1.0, f'{sf:.4f}')

# 管径 √(4Q/(3600πv)) = 162.9 mm
pd = bf.calculate_pipe_diameter(150.0)
check("进出口管径 = 162.9 mm", abs(pd - math.sqrt(4 * 150.0 / (3600 * math.pi * 2.0)) * 1000) < 0.01,
      f'{pd:.2f}')
check("法兰口径选 DN200", bf.get_flange_from_pipe_diameter(pd) == "DN200 [200mm]")

# 圆整规则
check("圆整 332.4→340 (尺寸10mm档)", bf.round_value(332.4, 'dimension') == 340)
check("圆整 0.41666→0.417 (面积0.001档)", abs(bf.round_value(0.4166667, 'area') - 0.417) < 1e-9)
check("过滤器内径 340+60=400 → 取值400", bf.get_filter_diameter_value(340) == 400)

# 重量锚点：底 11 / 筒 24 / 法兰 48.9 / 篮筐 17 / 进出口法兰 14.8 → 115.7
w = bf.calculate_weight(400, 460, pd)
check("底(上+下) = 11 kg", w["bottom"] == 11, f'{w["bottom"]}')
check("筒体 = 24 kg", w["shell"] == 24, f'{w["shell"]}')
check("封头法兰 = 48.9 kg", abs(w["head_flange"] - 48.9) < 1e-9, f'{w["head_flange"]}')
check("篮筐 = 17 kg（原式底板漏×1000 密度单位）", w["basket"] == 17, f'{w["basket"]}')
check("进出料法兰 = 14.8 kg", abs(w["inlet_outlet_flange"] - 14.8) < 1e-9)
check("总重 = 115.7 kg", abs(w["total"] - 115.7) < 1e-9, f'{w["total"]}')
price = bf.calculate_price(w["total"], 20.0, 0.13, 0.05, 0.2)
check("价格 = 115.7×20×1.38 = 3193.32", abs(price - 3193.32) < 1e-6, f'{price:.2f}')

# 全流程：不崩 + 历史记录钩子
bf.perform_design_calculation()
h = bf._get_history_data()
check("历史记录丝径 = 1.2 mm（不放大 1000 倍）", abs(h["outputs"]["丝径_mm"] - 1.2) < 1e-6,
      str(h["outputs"]))
check("历史记录筛网直径 = 332.5 mm", abs(h["outputs"]["筛网直径_mm"] - D_exp) < 0.2,
      str(h["outputs"]))
check("历史记录管道直径 = 162.9 mm", abs(h["outputs"]["管道直径_mm"] - pd) < 0.2)
check("全流程结果非空", len(bf.result_text.toPlainText()) > 100)

# 报告契约
check("get_project_info 返回 dict", isinstance(bf.get_project_info(), dict))
rep = bf.generate_report()
check("generate_report 返回 str（导出契约）", isinstance(rep, str) and len(rep) > 50, type(rep).__name__)
bf.clear_inputs()
bf.result_text.clear()
check("未计算时 generate_report 返回 None（不生成空文件）", bf.generate_report() is None)
check("clear_inputs 恢复默认流量 150", bf.flow_input.text() == "150.0", bf.flow_input.text())

# ══════════════════ Part 2: 管道跨距 ══════════════════
print('── Part 2: 管道跨距 ──')
m2 = _load('t_span', os.path.join(CALC_DIR, 'pipe_span_calculator.py'))
ps = m2.管道跨距()

od, t = ps.get_od_value(), ps.get_thickness_value()
check("默认外径 = DN100 114.3mm", abs(od - 0.1143) < 1e-9, f'{od}')
check("默认壁厚 = SCH40 6.02mm", abs(t - 0.00602) < 1e-9, f'{t}')
md, E = ps.get_material_properties()
check("默认材料 = 碳钢 7850 / 200GPa", (md, E) == (7850, 200e9), f'{md},{E}')

idv = od - 2 * t
I = math.pi * (od ** 4 - idv ** 4) / 64
Z = math.pi * (od ** 4 - idv ** 4) / (32 * od)
G = 9.81
w_exp = (math.pi * (od ** 2 - idv ** 2) / 4 * md * G
         + math.pi * idv ** 2 / 4 * 1000.0 * G
         + math.pi * ((od + 0.1) ** 2 - od ** 2) / 4 * 200.0 * G)
check("单位长度总重 = 288.91 N/m", abs(w_exp - 288.91) < 0.05, f'{w_exp:.2f}')

L_sig_exp = math.sqrt(8 * 137.9e6 * Z / w_exp)
L_def_exp = (384 * E * I / (1800 * w_exp)) ** (1 / 3)
check("应力控制跨距 = 14.18 m", abs(L_sig_exp - 14.18) < 0.01, f'{L_sig_exp:.3f}')
check("挠度控制跨距 = 7.63 m", abs(L_def_exp - 7.63) < 0.01, f'{L_def_exp:.3f}')
check("推荐跨距取挠度控制 = 7.63 m", abs(min(L_sig_exp, L_def_exp) - 7.63) < 0.01)

h2 = ps._get_history_data()["outputs"]
check("钩子 管道内径 = 102.3 mm", abs(h2["管道内径_mm"] - 102.3) < 0.05, str(h2))
check("钩子 总重量 ≈ 288.91 N/m", abs(h2["总重量_N_m"] - 288.91) < 0.05, str(h2))
check("钩子 推荐跨距 ≈ 7.63 m", abs(h2["推荐最大跨距_m"] - 7.63) < 0.01, str(h2))

ps.calculate_span()
txt = ps.result_text.toPlainText()
import re as _re
m_def = _re.search(r'挠度利用率:\s*([\d.]+)%', txt)
m_sig = _re.search(r'应力利用率:\s*([\d.]+)%', txt)
check("挠度利用率 ≈ 100%（修复前漏乘 5 → ~20%）",
      m_def and abs(float(m_def.group(1)) - 100.0) < 0.5, m_def.group(1) if m_def else 'N/A')
u_sig_exp = w_exp * L_def_exp ** 2 / (8 * Z) / 137.9e6 * 100
check(f"应力利用率 ≈ {u_sig_exp:.1f}%",
      m_sig and abs(float(m_sig.group(1)) - u_sig_exp) < 0.2, m_sig.group(1) if m_sig else 'N/A')

rep2 = ps.generate_report()
check("管道跨距 generate_report 返回 str", isinstance(rep2, str) and "跨距" in rep2, type(rep2).__name__)
ps.clear_inputs()
check("clear_inputs 后外径仍为 114.3（恢复默认而非清空）",
      abs(ps.get_od_value() - 0.1143) < 1e-9, f'{ps.get_od_value()}')
ps.calculate_span()
check("clear 后重算不崩", "推荐最大跨距" in ps.result_text.toPlainText())

# ══════════════════ Part 3: 管道间距 ══════════════════
print('── Part 3: 管道间距 ──')
m3 = _load('t_spacing', os.path.join(CALC_DIR, 'pipe_spacing_calculator.py'))
sp = m3.管道间距()

# 法兰外径必须是 D 不是 K：HG/T 20592-2009 PN16 DN100 → D=220 (K=180)
check("PN16 DN100 法兰外径 = 220 (D，不是K=180)", sp.get_flange_od(100, 'PN16') == 220,
      str(sp.get_flange_od(100, 'PN16')))
check("PN10 DN100 法兰外径 = 220", sp.get_flange_od(100, 'PN10') == 220)
check("PN25 DN100 法兰外径 = 235", sp.get_flange_od(100, 'PN25') == 235)
check("PN16 DN200 法兰外径 = 340（修复前 K 值 295）", sp.get_flange_od(200, 'PN16') == 340)
check("PN16 DN500 法兰外径 = 715", sp.get_flange_od(500, 'PN16') == 715)
check("管子外径 DN100 = 114.3（修复前 DN+9=109）", sp.get_pipe_od(100) == 114.3,
      str(sp.get_pipe_od(100)))
check("管子外径 DN200 = 219.1", sp.get_pipe_od(200) == 219.1)

# 未收录组合 → 保守取值 + 提示
od_note, note = sp.lookup_flange_od(450, 'PN63')
check("PN63 DN450 未收录 → 按同口径最大已知 685 保守取值", od_note == 685, f'{od_note}')
check("未收录时给出数据提示", bool(note), note)
od_note2, note2 = sp.lookup_flange_od(1000, 'PN16')
check("非常用口径 DN1000 → 2.2×DN 估算 2200", od_note2 == 2200, f'{od_note2}')
check("非常用口径给出提示", bool(note2), note2)

# 默认工况：DN100/DN100 PN16，无保温，无热位移，管廊
sp.dn_input1.setCurrentText("100"); sp.dn_input2.setCurrentText("100")
sp.flange_combo1.setCurrentText("PN16"); sp.flange_combo2.setCurrentText("PN16")
sp.insulation_check1.setChecked(False); sp.insulation_check2.setChecked(False)
sp.thermal_check.setChecked(False)
sp.rack_type_combo.setCurrentIndex(0)   # 管廊（无附加）
sp.valve_check1.setChecked(False); sp.valve_check2.setChecked(False)
sp.instrument_check.setChecked(False); sp.flange_face_check.setChecked(False)
sp.calculate_spacing()
r = sp.results
check("基础间距 = (114.3+114.3)/2+50 = 164.3", abs(r['spacing_basic'] - 164.3) < 0.01, f"{r['spacing_basic']}")
check("法兰间距 = (220+220)/2+25 = 245", abs(r['spacing_flange'] - 245.0) < 0.01, f"{r['spacing_flange']}")
check("最终最小中心距 = 245（修复前用 K 值只有 205）", abs(r['spacing_final'] - 245.0) < 0.01,
      f"{r['spacing_final']}")
check("默认工况无数据提示", not r.get('notes'), str(r.get('notes')))

# 热位移叠加
sp.thermal_check.setChecked(True); sp.thermal_input.setText("10")
sp.calculate_spacing()
check("叠加热位移 10mm → 255", abs(sp.results['spacing_final'] - 255.0) < 0.01,
      f"{sp.results['spacing_final']}")

# 保温后管径变大
sp.thermal_check.setChecked(False)
sp.insulation_check1.setChecked(True); sp.insulation_input1.setText("50")
sp.calculate_spacing()
check("管道1保温50mm → 基础间距 214.3", abs(sp.results['spacing_basic'] - 214.3) < 0.01,
      f"{sp.results['spacing_basic']}")

# 数据提示透出到界面
sp.insulation_check1.setChecked(False)
sp.dn_input1.setCurrentText("450"); sp.flange_combo1.setCurrentText("PN63")
sp.calculate_spacing()
check("未收录组合的计算结果带提示", bool(sp.results.get('notes')), str(sp.results.get('notes')))
check("提示同步显示在详情标签", "数据提示" in sp.result_detail_label.text())

# 报告契约
sp.dn_input1.setCurrentText("100"); sp.flange_combo1.setCurrentText("PN16")
sp.calculate_spacing()
rep3 = sp.generate_report()
check("管道间距 generate_report 返回 str", isinstance(rep3, str) and "最小中心距" in rep3,
      type(rep3).__name__)
check("get_project_info 返回 dict", isinstance(sp.get_project_info(), dict))
check("clear_inputs 委托 reset_inputs 不崩", sp.clear_inputs() is None)
check("reset 后 DN 回到 100", sp.dn_input1.currentText() == "100", sp.dn_input1.currentText())
check("reset 后结果清零", sp.results['spacing_final'] == 0)
sp.result_main_label.setText("点击计算按钮开始计算")
check("reset 后未计算 → generate_report 返回 None", sp.generate_report() is None)

# ══════════════════ Part 4: 可压缩流体压降 ══════════════════
print('── Part 4: 可压缩流体压降 ──')
m4 = _load('t_comp', os.path.join(CALC_DIR, 'compressible_flow_pressure_drop.py'))
cf = m4.CompressibleFlowPressureDrop()

def _pick_method(widget, keyword):
    for rb in widget.findChildren(QRadioButton):
        if keyword in rb.text():
            rb.setChecked(True)
            return True
    return False

# 默认 Darcy 等温积分法
check("默认方法 = Darcy 等温积分", cf._method() == "darcy_integral", cf._method())
cf.calculate_pressure_drop()
r4 = cf._last_result
check("等温积分法有压降结果", r4.get("dp_kPa", 0) > 0, str(r4))
check("雷诺数 > 0", r4.get("Re", 0) > 0)

# Weymouth：Q = 3.7435e-3·(Tb/Pb)·[(P1²−P2²)/(G·T·Le·Z)]^0.5·D^2.667·E
check("切到 Weymouth", _pick_method(cf, "Weymouth"))
cf.calculate_pressure_drop()
txt4 = cf.result_text.toPlainText()
m_q = _re.search(r'标准体积流量 \(m3/h\)\s*:\s*([\d.]+)', txt4)
q_w = float(m_q.group(1)) if m_q else -1
check("Weymouth 容量 > 1000 m³/h（修复前为 1e9 量级）", q_w > 1000, f'{q_w}')
check("Weymouth 容量 ≈ 4406 m³/h（±5%）", abs(q_w - 4406) / 4406 < 0.05, f'{q_w}')
G_calc = ((500.0 ** 2 - 400.0 ** 2) / (1.0 * 293.15 * 0.15)) ** 0.5
q_w_exp = 3.7435e-3 * (293.15 / 101.325) * G_calc * 100 ** 2.667 / 24
check("Weymouth 与手算一致（±0.5%）", abs(q_w - q_w_exp) / q_w_exp < 0.005,
      f'{q_w} vs {q_w_exp:.1f}')
check("结果含经验公式基准状态说明", "20 °C / 101.325 kPa" in txt4)
check("气体相对密度 G = 1.0", "气体相对密度 G  : 1.0000" in txt4, txt4[:400])

# Panhandle A
check("切到 Panhandle A", _pick_method(cf, "Panhandle"))
cf.calculate_pressure_drop()
m_q2 = _re.search(r'标准体积流量 \(m3/h\)\s*:\s*([\d.]+)', cf.result_text.toPlainText())
q_p = float(m_q2.group(1)) if m_q2 else -1
# Panhandle A: D 指数 2.6182（不是 Weymouth 的 2.667），E=0.92
q_p_exp = (4.5965e-3 * (293.15 / 101.325) ** 1.0788
           * (90000.0 / (1.0 * 293.15 * 0.15)) ** 0.5394
           * 100 ** 2.6182 * 0.92 / 24)
check(f"Panhandle 容量 ≈ {q_p_exp:.0f} m³/h（手算一致 ±0.5%）",
      abs(q_p - q_p_exp) / q_p_exp < 0.005, f'{q_p} vs {q_p_exp:.1f}')
check("Panhandle 容量落在 10³ 量级（修复前 1e9）", 1000 < q_p < 20000, f'{q_p}')
check("结果含效率因子 E = 0.92", "效率因子 E" in cf.result_text.toPlainText())

# 口径放大 → 按 D^2.667 增长
check("切回 Weymouth", _pick_method(cf, "Weymouth"))
cf.dia_in.setText("200")
cf.calculate_pressure_drop()
m_q3 = _re.search(r'标准体积流量 \(m3/h\)\s*:\s*([\d.]+)', cf.result_text.toPlainText())
q_w2 = float(m_q3.group(1)) if m_q3 else -1
check("D 100→200 容量按 2^2.667=6.35 倍增长", abs(q_w2 / q_w - 2 ** 2.667) / 2 ** 2.667 < 0.01,
      f'{q_w2 / q_w:.3f}')
cf.dia_in.setText("100")

# 报告契约
rep4 = cf.generate_report()
check("可压缩压降 generate_report 返回 str", isinstance(rep4, str) and "可压缩" in rep4, type(rep4).__name__)
check("get_project_info 返回 dict", isinstance(cf.get_project_info(), dict))
cf.clear_inputs()
cf.result_text.clear()
check("未计算时 generate_report 返回 None", cf.generate_report() is None)
check("clear_inputs 恢复出厂默认 P1=500", cf.P1_in.text() == "500", cf.P1_in.text())
cf.calculate_pressure_drop()
check("clear 后重算不崩", "压降" in cf.result_text.toPlainText())

# ══════════════════ Part 5: 压力管道定义 ══════════════════
print('── Part 5: 压力管道定义 ──')
m5 = _load('t_ppd', os.path.join(CALC_DIR, 'pressure_pipe_definition.py'))
pp = m5.压力管道定义()

# 判据：最高工作压力 ≥0.1MPa(表压) 且 DN>25mm
check("P=1.2MPa DN100 气体 → 是压力管道", pp.is_pressure_pipe(1.2, 100, "气体", 180, 100) is True)
check("P=0.08MPa → 不是压力管道（<0.1）", pp.is_pressure_pipe(0.08, 100, "气体", 180, 100) is False)
check("DN=25 → 不是压力管道（须 >25）", pp.is_pressure_pipe(1.2, 25, "气体", 180, 100) is False)
check("DN=32 → 是压力管道", pp.is_pressure_pipe(1.2, 32, "气体", 180, 100) is True)
check("可燃气体 → 是压力管道", pp.is_pressure_pipe(1.2, 100, "可燃气体", 25, 100) is True)
check("液化气体 → 是压力管道", pp.is_pressure_pipe(1.2, 100, "液化气体", 25, 100) is True)
check("可燃液体 → 是压力管道", pp.is_pressure_pipe(1.2, 100, "可燃液体", 25, 100) is True)
check("有毒介质 → 是压力管道", pp.is_pressure_pipe(1.2, 100, "有毒介质", 25, 100) is True)
check("腐蚀性液体 → 是压力管道", pp.is_pressure_pipe(1.2, 100, "腐蚀性液体", 25, 100) is True)
check("一般液体 T=99 < 沸点100 → 不是", pp.is_pressure_pipe(1.2, 100, "一般液体", 99, 100) is False)
check("一般液体 T=100 ≥ 沸点100 → 是", pp.is_pressure_pipe(1.2, 100, "一般液体", 100, 100) is True)
check("一般液体 沸点 78（乙醇）T=80 → 是", pp.is_pressure_pipe(1.2, 100, "一般液体", 80, 78) is True)

# GC 类别判定
check("1.6MPa/200℃ 气体 → GC2", pp.determine_pipe_class(1.6, 200, "气体", 100) == "GC2")
check("5.0MPa 可燃气体 → GC1（修复前漏判为 GC2）",
      pp.determine_pipe_class(5.0, 50, "可燃气体", 100) == "GC1",
      pp.determine_pipe_class(5.0, 50, "可燃气体", 100))
check("5.0MPa 液化气体 → GC1", pp.determine_pipe_class(5.0, 50, "液化气体", 100) == "GC1")
check("5.0MPa 可燃液体 → GC1", pp.determine_pipe_class(5.0, 50, "可燃液体", 100) == "GC1")
check("10.0MPa 气体 → GC1", pp.determine_pipe_class(10.0, 50, "气体", 100) == "GC1")
check("4.0MPa/420℃ → GC1", pp.determine_pipe_class(4.0, 420, "气体", 100) == "GC1")
check("4.0MPa/300℃ → GC2", pp.determine_pipe_class(4.0, 300, "气体", 100) == "GC2")
check("有毒介质 → GC1（从严）", pp.determine_pipe_class(1.6, 100, "有毒介质", 100) == "GC1")
check("一般液体 1.0MPa/100℃ → GC3", pp.determine_pipe_class(1.0, 100, "一般液体", 100) == "GC3")
check("一般液体 2.0MPa → GC2（>1.0MPa）", pp.determine_pipe_class(2.0, 100, "一般液体", 100) == "GC2")
check("腐蚀性液体 1.0MPa → GC2（腐蚀性不在 GC1 判据内）",
      pp.determine_pipe_class(1.0, 100, "腐蚀性液体", 100) == "GC2")

# ★ 核心回归：判据必须用【最高工作压力】而不是【设计压力】
pp.pressure_input.setText("0.10")
pp.working_pressure_input.setText("0.08")
pp.temp_input.setText("200")
pp.working_temp_input.setText("180")
pp.diameter_input.setText("100")
pp.media_combo.setCurrentText("气体")
pp.calculate_pipe_definition()
out = pp.result_text.toPlainText()
check("★ 设计压力0.10/工作压力0.08 → 不是压力管道（修复前误判为是）",
      "不是压力管道" in out and "是压力管道" not in out.replace("不是压力管道", ""), out[:200])

# 反向：工作压力达标即成立
pp.working_pressure_input.setText("0.20")
pp.calculate_pipe_definition()
out2 = pp.result_text.toPlainText()
check("工作压力 0.20MPa → 是压力管道", "是压力管道" in out2.replace("不是压力管道", ""), out2[:200])
check("结果列出最高工作压力（判定依据）", "最高工作压力" in out2)

# 液体介质时结果表列出标准沸点（一般液体 T≥沸点 → 压力管道）
pp.media_combo.setCurrentText("一般液体")
pp.working_temp_input.setText("105")
pp.boiling_point_input.setText("100")
pp.calculate_pipe_definition()
out3 = pp.result_text.toPlainText()
check("一般液体工况结果列出标准沸点（液体判据）", "标准沸点" in out3, out3[:300])
check("一般液体 105℃ ≥ 沸点 100℃ → 是压力管道", "是压力管道" in out3.replace("不是压力管道", ""))
check("结果标注 最高工作压力为判定依据", "判定依据" in out3)

# 介质下拉含新增项
items = [pp.media_combo.itemText(i) for i in range(pp.media_combo.count())]
check("介质下拉含可燃气体/腐蚀性液体", "可燃气体" in items and "腐蚀性液体" in items, str(items))

# 清空恢复默认
pp.clear_inputs()
check("clear_inputs 恢复设计压力 1.6", pp.pressure_input.text() == "1.6", pp.pressure_input.text())
check("clear_inputs 恢复最高工作压力 1.2", pp.working_pressure_input.text() == "1.2")
check("clear_inputs 恢复沸点 100", pp.boiling_point_input.text() == "100")

# 报告契约
check("未计算时 generate_report 返回 None", pp.generate_report() is None)
pp.calculate_pipe_definition()
rep5 = pp.generate_report()
check("压力管道 generate_report 返回 str", isinstance(rep5, str) and "压力管道定义" in rep5,
      type(rep5).__name__)
check("报告含判定结论段", "判定结论" in rep5 and "TSG D0001-2009" in rep5)
check("get_project_info 返回 dict", isinstance(pp.get_project_info(), dict))
h5 = pp._get_history_data()
check("历史记录含标准沸点", "标准沸点_C" in h5["inputs"], str(h5["inputs"]))
check("历史记录含是否压力管道", "是否压力管道" in h5["outputs"], str(h5["outputs"]))

# 分类参考表描述已更新
tbl = pp.classification_table
gc1_desc = tbl.item(4, 3).text()
check("GC1 描述含可燃气体/液化烃条件", "可燃气体" in gc1_desc and "液化烃" in gc1_desc, gc1_desc)
gc3_desc = tbl.item(6, 3).text()
check("GC3 描述含温度条件 185℃", "185" in gc3_desc, gc3_desc)

# ══════════════════ 汇总 ══════════════════
print('=' * 60)
print(f'通过 {len(PASS)} / {len(PASS) + len(FAIL)}')
if FAIL:
    print('失败项：')
    for n, d in FAIL:
        print(f'  ✗ {n}  [{d}]')
    sys.exit(1)
print('全部通过')
