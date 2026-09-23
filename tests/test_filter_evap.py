# -*- coding: utf-8 -*-
"""板框压滤机过滤面积 + 浓缩蒸发器 回归测试

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_filter_evap.py

核对依据
════════════════════════════════════════════════════════════════════════
Part 1  板框压滤机过滤面积（filter_press_area_calculator.py）
  几何恒等式（与厂商样本互校）
      A = n·2·a（一室两面过滤）、V = n·a·δ  ⇒  V = A·δ/2
      800×800 / A=50 m² / δ=30 mm → 750 L（厂商标称 750 L）
      1000×1000 / A=60 m² / δ=30 mm → 900 L（厂商标称 0.90 m³）
  物料衡算（默认 A=50, δ=30, φ=0.95, x_s=10%, w=60%, ρ_c=1300, ρ_f=1000）
      V_室=0.75 m³ → V_饼=0.7125 m³ → m_饼=926.25 kg → 干渣=370.5 kg → 料浆=3705 kg
      → 滤液=2778.75 kg / 2.77875 m³
  Ruth 恒压过滤   t = μ·α·c·(V²+2V·V_e)/(2A²Δp)
      默认 (Δp=0.6 MPa, μ=1 mPa·s, α=1e12)：
        c = 干渣/滤液 = 133.32 kg/m³；V_e=0 时 t_f = μ·α·m_solid·V_f/(2A²Δp)
        = 1e-3·1e12·370.5·2.77875/(2·50²·0.6e6) = 343.2 s = 5.72 min
  洗涤（板框经典假定：洗涤速率 = 终了过滤速率 1/4）
      (dV/dt)_end = A²Δp/(μ·α·m_solid) = 4.0486e-3 m³/s
      V_w = 0.10·V_f = 0.277875 m³；t_w = 4·V_w/(dV/dt)_end = 274.5 s = 4.58 min
  循环周期  T = t_f + t_w + t_aux = 5.72 + 4.58 + 45 = 55.30 min
      产能 = 370.5 kg × 1440/55.30 = 9.649 t/d（干渣）；单位面积 192.98 kg/(m²·d)
  ★ 关键性质：V ∝ A ⇒ t_f ∝ V²/A² 与 A 无关、t_w 亦然
      ⇒ 循环周期与面积无关，产能 ∝ 面积（滤饼厚度不变）
      反算：目标 10 t/d ÷ 0.19298 t/(m²·d) = 51.82 m² → 推荐 XAZ60/1000-U（60 m²）
  ⚠ 出厂默认值曾写 QLineEdit("乙醇")/"碳钢" 之类文字（本页无此坑，一并守卫）
════════════════════════════════════════════════════════════════════════
Part 2  浓缩蒸发器（evaporator_calculator.py）
  物料衡算   W = F·(1 − x0/x1) = 10000·(1 − 12/60) = 8000 kg/h；P = 2000 kg/h
  单效热量衡算（默认 F=10000, x0=12%, x1=60%, T_f=25, Cp=3.8, p_s=0.4 MPa(g),
                η_h=0.97, t_b=70, BPE=1.5, K=2000, 裕量 1.15）
      p_s=0.4 MPa(g) ≈ 0.5013 MPa(a) → T_s ≈ 151.9 °C、λ_s ≈ 2108 kJ/kg
        （蒸汽表 0.5 MPa(a) → 151.83 °C / 2108.2 kJ/kg；表压换算加 1 atm）
      t_v = t_b − BPE = 68.5 °C → λ'_b = 2336.8 kJ/kg（蒸汽表 68.5 °C）
      Q_蒸发 = 8000×2336.8 = 18 694.4 MJ/h = 5192.9 kW
      Q_显热 = 10000×3.8×(70−25) = 1 710 000 kJ/h = 475.0 kW
      Q_总 = 5667.9 kW
      D = Q_总/(λ_s·η_h) = 20 404 384/(2108.03×0.97) = 9978.6 kg/h
      经济性 W/D = 0.802；ΔT = 151.94 − 70 = 81.94 °C
      A = Q/(K·ΔT)·裕量 = 5667.88×1000/(2000×81.94)×1.15 = 39.78 m²
  多效（并流，3 效，K₁=2500, r=0.8, Δ'''=1.0 °C/效，末效 70 °C）
      ΣΔT = T_s − t_n − (n−1)·Δ''' = 151.94 − 70 − 2×1.0 = 79.94 °C
      ΔT_i ∝ 1/K_i（K_i = K₁·r^(i−1)）⇒ ΔT_i·K_i 逐效相等
      热量衡算对 D₁ 线性 ⇒ ΣW_i = W（物料守恒自检）
      蒸汽经济性应落在 1.5~2.5（3 效工程常用区间）
   MVR（π=1.8, η_is=0.75, η_m=0.95）
      p₁ = p_sat(68.5) = 0.02923 MPa(a)；p₂ = p₁·π = 0.05262 MPa(a)
      T₂sat = 82.6 °C（蒸汽表 0.0526 MPa → 82.6 °C）；有效温差 = 82.6 − 70 = 12.59 °C
      h₁ = h_g(p₁)、s₁ = s_g(p₁)（IAPWS-IF97）
      h_2s = h(p₂, s = s₁)（properties_from_ps 反算）；w_is = h_2s − h₁
      w_act = w_is/η_is；P_轴 = W·w_act/3600；P_电机 = P_轴/η_m
      单位电耗 = P_电机/(W/1000)，工程常见 10~40 kWh/t
   TVR（引射系数 u=0.8）
      生蒸汽 D → D/(1+u)；蒸汽经济性 ×(1+u)
════════════════════════════════════════════════════════════════════════
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

from PySide6.QtWidgets import QApplication, QMessageBox          # noqa: E402


def _mk(_kind):
    def f(parent=None, title='', text='', *a, **k):
        return QMessageBox.StandardButton.Ok
    return staticmethod(f)


QMessageBox.warning = _mk('warning')
QMessageBox.critical = _mk('critical')
QMessageBox.information = _mk('info')

from data_manager import DataManager                              # noqa: E402

DataManager.get_instance(data_file=os.path.join(tempfile.mkdtemp(), 'test.json'))

app = QApplication(sys.argv)

from common_constants import get_steam_props, WATER_CP           # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# IAPWS-IF97（与蒸发器计算器同一份模块，用于独立复算）
_spec = importlib.util.spec_from_file_location(
    'steam_iapws', os.path.join(ROOT, 'modules', 'chemical_calculations', 'steam_iapws.py'))
IAPWS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(IAPWS)

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}'
          + (f'  [{detail}]' if detail and not cond else ''))


def close(a, b, rel=1e-9):
    """相对误差比较（b 为期望值）"""
    if b == 0:
        return abs(a) < 1e-12
    return abs(a - b) / abs(b) <= rel


def close_abs(a, b, tol):
    return abs(a - b) <= tol


# ══════════════════════════════ Part 1: 板框压滤机 ══════════════════════════════
print('── Part 1: 板框压滤机过滤面积 ──')
m_fp = _load('t_filter_press', os.path.join(CALC_DIR, 'filter_press_area_calculator.py'))
fp = m_fp.FilterPressAreaCalculator()

# ── 1.1 出厂默认值 ──
check("默认过滤面积 50 m²", fp.area_input.text() == "50", fp.area_input.text())
check("默认滤饼厚度 30 mm", fp.cake_thk_input.text() == "30", fp.cake_thk_input.text())
check("默认计算模式为「面积核算」", fp.mode_combo.currentIndex() == 0)
check("默认机型预设非「自定义」", fp.PRESS_PRESETS[fp.preset_combo.currentText()] is not None,
      fp.preset_combo.currentText())

# 遗留调试默认值守卫：输入框不得预填文字（铁律：QLineEdit("乙醇") 会静默过滤数据）
_txt_defaults = {
    'area_input': fp.area_input.text(), 'cake_thk_input': fp.cake_thk_input.text(),
    'solid_input': fp.solid_input.text(), 'cake_water_input': fp.cake_water_input.text(),
    'dp_input': fp.dp_input.text(), 'mu_input': fp.mu_input.text(),
}
check("输入框默认值均为数字（无遗留文字默认值）",
      all(v.replace('.', '', 1).replace('e', '', 1).lstrip('+-').isdigit() for v in _txt_defaults.values()),
      str(_txt_defaults))

# ── 1.2 几何恒等式与厂商样本复核 ──
fp.calculate()
r = fp._last_result
check("计算成功且未回落错误框", bool(r), fp.result_text.toPlainText()[:60])
check("滤室总容积 V = A·δ/2 = 0.75 m³", close_abs(r["V_chamber"], 0.75, 1e-9),
      f'{r["V_chamber"]}')
check("样本复核 800×800/50 m²/30 mm → 750 L（厂商标称 750 L）",
      close_abs(r["V_chamber"] * 1000, 750.0, 1e-9))
# 换 1000×1000 机型（A=60）→ 900 L
fp.preset_combo.setCurrentText("XAZ60/1000-U  1000×1000 60 m²  30 mm")
fp.calculate()
check("选预设自动填面积 60", fp.area_input.text() == "60", fp.area_input.text())
check("样本复核 1000×1000/60 m²/30 mm → 900 L（厂商标称 0.90 m³）",
      close_abs(fp._last_result["V_chamber"] * 1000, 900.0, 1e-9),
      f'{fp._last_result["V_chamber"]*1000}')

# 回到默认
fp.preset_combo.setCurrentText("XAZ50/800-U   800×800  50 m²  30 mm")
fp.calculate()
r = fp._last_result

# ── 1.3 每批物料衡算（独立手算）──
check("充满系数 φ=0.95 → 实收滤饼容积 0.7125 m³", close(r["V_cake"], 0.7125, 1e-12),
      f'{r["V_cake"]}')
check("湿滤饼质量 = 0.7125×1300 = 926.25 kg", close(r["m_cake"], 926.25, 1e-12),
      f'{r["m_cake"]}')
check("干渣 = 926.25×(1−0.60) = 370.5 kg", close(r["m_solid"], 370.5, 1e-12), f'{r["m_solid"]}')
check("滤饼带液 = 926.25×0.60 = 555.75 kg", close(r["m_liquid_cake"], 555.75, 1e-12))
check("每批料浆 = 370.5/0.10 = 3705 kg", close(r["m_slurry"], 3705.0, 1e-12), f'{r["m_slurry"]}')
check("每批滤液 = 3705 − 926.25 = 2778.75 kg", close(r["m_filtrate"], 2778.75, 1e-12))
check("滤液体积 = 2778.75/1000 = 2.77875 m³", close(r["V_filtrate"], 2.77875, 1e-12),
      f'{r["V_filtrate"]}')
check("干渣/滤液比 c = 370.5/2.77875 = 133.32 kg/m³",
      close(r["c_ratio"], 370.5 / 2.77875, 1e-12), f'{r["c_ratio"]:.4f}')

# ── 1.4 Ruth 恒压过滤时间（两种写法互校）──
mu, alpha, dp = 1e-3, 1e12, 0.6e6
t_f_exp_s = mu * alpha * r["c_ratio"] * (r["V_filtrate"] ** 2) / (2 * 50.0 ** 2 * dp)
check("t_f = μ·α·c·V²/(2A²Δp) = 343.2 s = 5.72 min",
      close_abs(r["t_f"], t_f_exp_s / 60.0, 1e-6), f'{r["t_f"]:.4f} min')
# 化简式：c·V² = 干渣×滤液体积 → t_f = μ·α·m_solid·V_f/(2A²Δp)
t_f_alt = mu * alpha * 370.5 * 2.77875 / (2 * 50.0 ** 2 * dp)
check("化简式 t_f = μ·α·m_干渣·V_滤液/(2A²Δp) 与上式一致",
      close_abs(r["t_f"], t_f_alt / 60.0, 1e-6))

# ── 1.5 洗涤时间（1/4 速率经典假定）──
dVdt_end_exp = 50.0 ** 2 * dp / (mu * alpha * 370.5)
check("终了过滤速率 (dV/dt)_end = A²Δp/(μ·α·m_干渣) = 4.0486e-3 m³/s",
      close_abs(r["dVdt_end"], dVdt_end_exp, 1e-9), f'{r["dVdt_end"]:.6e}')
V_wash_exp = 0.10 * 2.77875
t_wash_exp = 4.0 * V_wash_exp / dVdt_end_exp / 60.0
check("洗涤液量 = 0.10×滤液 = 0.277875 m³", close(r["V_wash"], V_wash_exp, 1e-12))
check("洗涤时间 t_w = 4·V_w/(dV/dt)_end = 4.58 min",
      close_abs(r["t_wash"], t_wash_exp, 1e-6), f'{r["t_wash"]:.4f} min')
check("洗涤时间 < 过滤时间（1/4 速率下 V_w 仅 0.1V）", r["t_wash"] < r["t_f"] * 1.2,
      f't_w={r["t_wash"]:.3f} t_f={r["t_f"]:.3f}')

# ── 1.6 循环周期与产能 ──
T_exp = t_f_exp_s / 60.0 + t_wash_exp + 45.0
check("循环周期 T = t_f + t_w + 45 = 55.30 min", close_abs(r["T_cycle"], T_exp, 1e-6),
      f'{r["T_cycle"]:.4f}')
batches_exp = 1440.0 / T_exp
check("日循环次数 = 1440/55.30 = 26.04 次/d", close_abs(r["batches_per_day"], batches_exp, 1e-6),
      f'{r["batches_per_day"]:.4f}')
check("干渣产量 = 370.5×26.04/1000 = 9.65 t/d",
      close_abs(r["solid_per_day"], 370.5 * batches_exp / 1000.0, 1e-6), f'{r["solid_per_day"]:.4f}')
check("单位面积产能 = 9.649/50 = 192.98 kg/(m²·d)",
      close_abs(r["cap_per_area"] * 1000, 370.5 * batches_exp / 1000.0 / 50.0 * 1000, 1e-6),
      f'{r["cap_per_area"]*1000:.3f}')
check("料浆处理量 ≈ 4020 kg/h",
      close_abs(r["slurry_per_hour"], 3705.0 * (60.0 / T_exp), 1e-3), f'{r["slurry_per_hour"]:.1f}')

# ── 1.7 ★ 关键性质：循环周期与面积无关、产能 ∝ 面积 ──
cap = r["cap_per_area"]
T_50 = r["T_cycle"]
fp.area_input.setText("100")
fp.calculate()
r100 = fp._last_result
check("面积翻倍后循环周期不变（V ∝ A ⇒ t_f、t_w 与 A 无关）",
      close_abs(r100["T_cycle"], T_50, 1e-6), f'{T_50:.4f} → {r100["T_cycle"]:.4f}')
check("面积翻倍后单位面积产能不变",
      close(r100["cap_per_area"], cap, 1e-9), f'{cap:.6f} → {r100["cap_per_area"]:.6f}')
check("面积翻倍后干渣产量翻倍（产能 ∝ 面积）",
      close(r100["solid_per_day"], 2.0 * r["solid_per_day"], 1e-9))
fp.area_input.setText("50")
fp.calculate()
r = fp._last_result

# ── 1.8 反算选型 ──
fp.mode_combo.setCurrentIndex(1)
fp.target_input.setText("10")
fp.calculate()
rr = fp._last_result
A_req_exp = 10.0 / cap
check("反算：目标 10 t/d ÷ 0.192983 = 51.82 m²",
      close_abs(rr["A_req"], A_req_exp, 1e-6), f'{rr["A_req"]:.4f}')
check("推荐机型为满足面积需求的最小预设 XAZ60/1000-U（60 m²）",
      rr["recommend"] == "XAZ60/1000-U", rr["recommend"])
check("反算模式给出并联台数提示", any("台并联" in w for w in rr["warn"]), str(rr["warn"]))

# 超出样本最大机型
fp.target_input.setText("100000")
fp.calculate()
check("目标远超样本产能时给出「超出样本最大机型」提示",
      "超出样本最大机型" in fp._last_result["recommend"],
      fp._last_result["recommend"])
fp.mode_combo.setCurrentIndex(0)

# ── 1.9 参数校验（静默偏不安全）──
fp.solid_input.setText("70")          # 料浆固含量 70% > 滤饼固体分数 40%
fp.cake_water_input.setText("60")
fp.calculate()
check("料浆固含量 > 滤饼固体分数 → 报错（物料守恒不成立）",
      fp.result_text.toPlainText().startswith("错误") or "不匹配" in fp.result_text.toPlainText(),
      fp.result_text.toPlainText()[:50])
fp.solid_input.setText("10")
fp.fill_factor_input.setText("1.5")
fp.calculate()
check("滤室充满系数 > 1 → 报错", fp.result_text.toPlainText().startswith("错误"),
      fp.result_text.toPlainText()[:50])
fp.clear_inputs()

# ── 1.10 clear 后可重算 ──
check("clear 后面积恢复 50", fp.area_input.text() == "50", fp.area_input.text())
check("clear 后滤饼厚度恢复 30", fp.cake_thk_input.text() == "30")
check("clear 后模式恢复「面积核算」", fp.mode_combo.currentIndex() == 0)
check("clear 后结果框清空", fp.result_text.toPlainText() == "")
fp.calculate()
check("clear 后可直接重算（无残留状态）", bool(fp._last_result)
      and close_abs(fp._last_result["V_chamber"], 0.75, 1e-9))

# ── 1.11 报告与历史契约 ──
check("generate_report 返回 str", isinstance(fp.generate_report(), str),
      type(fp.generate_report()).__name__)
rep = fp.generate_report()
check("报告含标题与关键公式", "板框压滤机过滤面积计算书" in rep
      and "V = A·δ/2" in rep and "Ruth" in rep)
check("报告含厂商样本复核说明", "750 L" in rep and "900 L" in rep)
check("报告区分经验取值（α/φ/含水率）", "经验取值" in rep or "经验/试验取值" in rep)
info = fp.get_project_info()
check("get_project_info 返回 dict 且标准键齐全",
      isinstance(info, dict) and {"company_name", "project_number", "project_name",
                                  "subproject_name", "calculation_type"} <= set(info),
      str(sorted(info)))
check("get_project_info 的 calculation_type 已按页命名",
      info["calculation_type"] == "板框压滤机过滤面积核算", info["calculation_type"])
h = fp._get_history_data()
check("历史钩子命名为 _get_history_data 且为 dict", isinstance(h, dict))
check("历史 inputs 含过滤面积/滤饼厚度", "过滤面积_m2" in h["inputs"]
      and "滤饼厚度_mm" in h["inputs"], str(h["inputs"]))
check("历史 outputs 含循环周期与产能", "循环周期_min" in h["outputs"]
      and "干渣产量_t_d" in h["outputs"], str(h["outputs"]))
check("SVG 示意图已加载", fp.svg_widget.renderer().isValid())

# 620 系列不入预设（厂商样本口径矛盾）
check("预设不含 630 系列（样本滤饼厚度与滤室容积互不吻合）",
      not any("630" in k for k in fp.PRESS_PRESETS), str(list(fp.PRESS_PRESETS)))


# ══════════════════════════════ Part 2: 浓缩蒸发器 ══════════════════════════════
print('── Part 2: 浓缩蒸发器（单效/多效/MVR/TVR）──')
m_ev = _load('t_evaporator', os.path.join(CALC_DIR, 'evaporator_calculator.py'))
ev = m_ev.EvaporatorCalculator()

# ── 2.1 出厂默认值与模式清单 ──
check("四种计算模式齐备",
      ev.MODES == ["单效蒸发", "多效蒸发（并流）", "MVR 机械蒸汽再压缩", "TVR 热力蒸汽再压缩"],
      str(ev.MODES))
check("默认模式为单效蒸发", ev.mode_combo.currentIndex() == 0)
check("默认效数 3 效", ev.effects_combo.currentText() == "3 效", ev.effects_combo.currentText())
check("默认加热室为降膜式（清洁物料）", ev.heater_combo.currentIndex() == 0)
check("单效模式下 MVR 参数组整体隐藏（不留空标题框）", ev._g4.isHidden())
check("单效模式下 TVR 参数组整体隐藏", ev._g5.isHidden())
check("默认进料量 10000、x0=12、x1=60",
      (ev.feed_input.text(), ev.x0_input.text(), ev.x1_input.text()) == ("10000", "12", "60"))
# BPE 由用户填入、不做关联式推算（醒目契约）
check("BPE 为可编辑输入框（不做关联式推算）", isinstance(ev.bpe_input.text(), str)
      and ev.bpe_input.text() == "1.5")

# ── 2.2 物料衡算 ──
ev.calculate()
s = ev._last_result
check("单效计算成功", bool(s), ev.result_text.toPlainText()[:80])
check("蒸发水量 W = 10000(1−12/60) = 8000 kg/h", close(s["W_calc"], 8000.0, 1e-12),
      f'{s["W_calc"]}')
check("浓缩液量 P = F − W = 2000 kg/h", close(s["P_calc"], 2000.0, 1e-12))
check("浓缩倍数 = x1/x0 = 5.00", close_abs(s["x1_calc"] / s["x0_calc"], 5.0, 1e-12))

# ── 2.3 生蒸汽侧独立锚点（蒸汽表）──
Ts, lam_s = get_steam_props(0.4)["sat_temp"], get_steam_props(0.4)["h_fg"]
check("0.4 MPa(g) ≈ 0.5013 MPa(a) → 饱和温度 ≈ 151.9 °C（蒸汽表 0.5 MPa → 151.83 °C）",
      close_abs(Ts, 151.9, 0.4), f'{Ts:.3f}')
check("0.4 MPa(g) 汽化潜热 ≈ 2108 kJ/kg", close_abs(lam_s, 2108.0, 2.0), f'{lam_s:.2f}')
check("0.3 MPa(g) 锚点 143.7 °C（记忆口径）", close_abs(get_steam_props(0.3)['sat_temp'],
                                                    143.7, 0.2),
      f"{get_steam_props(0.3)['sat_temp']:.2f}")
check("程序回显的 T_s/λ_s 与 get_steam_props 一致",
      close_abs(s["T_s_calc"], Ts, 1e-9) and close_abs(s["lam_s_calc"], lam_s, 1e-9))

# ── 2.4 单效热量衡算（独立手算）──
t_v_exp = 70.0 - 1.5
lam_b_exp = IAPWS.saturation_properties(P_MPa=IAPWS.saturation_pressure(t_v_exp))["h_fg"]
check("二次蒸汽温度 = t_b − BPE = 68.5 °C", close_abs(s["t_v_last"], t_v_exp, 1e-9))
check("68.5 °C 汽化潜热 ≈ 2336.8 kJ/kg（蒸汽表）", close_abs(lam_b_exp, 2336.8, 0.5),
      f'{lam_b_exp:.2f}')
Q_evap_exp = 8000.0 * lam_b_exp / 3600.0
Q_sens_exp = 10000.0 * 3.80 * (70.0 - 25.0) / 3600.0
Q_tot_exp = Q_evap_exp + Q_sens_exp
check("Q_蒸发 = 8000×2336.8/3600 ≈ 5193 kW", close_abs(s["Q_evap_kW"], Q_evap_exp, 1e-6),
      f'{s["Q_evap_kW"]:.2f}')
check("Q_显热 = 10000×3.8×45/3600 = 475 kW", close_abs(s["Q_sens_kW"], Q_sens_exp, 1e-6),
      f'{s["Q_sens_kW"]:.2f}')
check("Q_总 = 5668 kW", close_abs(s["Q_total_kW"], Q_tot_exp, 1e-6), f'{s["Q_total_kW"]:.2f}')
D_exp = (8000.0 * lam_b_exp + 10000.0 * 3.80 * 45.0) / (lam_s * 0.97)
check("生蒸汽耗量 D = Q_总/(λ_s·η_h) ≈ 9979 kg/h", close_abs(s["D"], D_exp, 1e-6),
      f'{s["D"]:.1f}')
check("蒸汽经济性 W/D ≈ 0.802（单效 < 1，因含进料显热）",
      close_abs(s["economy"], 8000.0 / D_exp, 1e-6), f'{s["economy"]:.4f}')
check("单位汽耗 = D/W ≈ 1.247 t/t", close_abs(s["steam_per_water"], D_exp / 8000.0, 1e-6))
check("有效温差 ΔT = T_s − t_b = 81.94 °C", close_abs(s["dt_eff_total"], Ts - 70.0, 1e-9),
      f'{s["dt_eff_total"]:.3f}')
A_exp = (Q_tot_exp * 1000.0 / (2000.0 * (Ts - 70.0))) * 1.15
check("面积 A = Q/(K·ΔT)·裕量 ≈ 39.78 m²", close_abs(s["A_design"], A_exp, 1e-6),
      f'{s["A_design"]:.3f}')
cw_exp = (8000.0 * lam_b_exp / 3600.0) / (WATER_CP * 8.0) * 3600.0 / 1000.0
check("末效冷凝器冷却水 ≈ 559 m³/h（ΔT=8 °C）", close_abs(s["cw_m3h"], cw_exp, 1e-6),
      f'{s["cw_m3h"]:.1f}')

# ── 2.5 多效（并流）──
ev.mode_combo.setCurrentText("多效蒸发（并流）")
ev.effects_combo.setCurrentText("3 效")
ev.calculate()
m = ev._last_result
check("多效计算成功", bool(m) and len(m["effects"]) == 3, str(len(m.get("effects", []))))
check("多效物料守恒 ΣW_i = W = 8000 kg/h",
      close_abs(sum(e["W"] for e in m["effects"]), 8000.0, 1e-6),
      f'{sum(e["W"] for e in m["effects"]):.4f}')
check("ΣΔT = T_s − t_n − (n−1)·Δ''' = 151.94 − 70 − 2×1.0 = 79.94 °C",
      close_abs(m["dt_eff_total"], Ts - 70.0 - 2 * 1.0, 1e-9), f'{m["dt_eff_total"]:.4f}')
check("温差之和 = ΣΔT", close_abs(sum(m["dT"]), m["dt_eff_total"], 1e-9))
check("ΔT_i ∝ 1/K_i ⇒ ΔT_i·K_i 逐效相等",
      max(abs(m["dT"][i] * m["K"][i] - m["dT"][0] * m["K"][0]) for i in range(3))
      < 1e-9 * m["dT"][0] * m["K"][0])
check("K_i = K₁·r^(i−1)（2500 / 2000 / 1600）",
      [round(k) for k in m["K"]] == [2500, 2000, 1600], str([round(k) for k in m["K"]]))
check("末效浓度 = x1 = 60 wt%", close_abs(m["effects"][-1]["x"], 60.0, 1e-6),
      f'{m["effects"][-1]["x"]:.4f}')
check("设计面积取各效最大", close_abs(m["A_design"], max(e["A"] for e in m["effects"]), 1e-12))
check("各效面积之和 ≥ 设计面积", m["A_total"] >= m["A_design"] - 1e-9)
check("3 效蒸汽经济性落在工程常用区间 1.5~2.5",
      1.5 <= m["economy"] <= 2.5, f'{m["economy"]:.3f}')
check("多效经济性显著优于单效（约 2 倍）", m["economy"] > 2.0 * 0.8017 * 0.95,
      f'{m["economy"]:.3f} vs {s["economy"]:.3f}')
check("多效生蒸汽 D₁ < W", m["D"] < 8000.0, f'{m["D"]:.1f}')
check("多效结果不含 MVR 段", "mvr" not in m)

# 4 效：经济性应进一步上升
ev.effects_combo.setCurrentText("4 效")
ev.calculate()
m4 = ev._last_result
check("4 效经济性 > 3 效经济性", m4["economy"] > m["economy"],
      f'{m4["economy"]:.3f} > {m["economy"]:.3f}')
ev.effects_combo.setCurrentText("3 效")
ev.calculate()
m = ev._last_result

# ── 2.6 MVR ──
ev.mode_combo.setCurrentText("MVR 机械蒸汽再压缩")
ev.calculate()
v = ev._last_result
check("MVR 计算成功且含 mvr 段", bool(v) and v.get("mvr") is not None,
      ev.result_text.toPlainText()[:80])
check("MVR 模式下 MVR 参数组显示", not ev._g4.isHidden())
check("MVR 模式下 TVR 参数组仍隐藏", ev._g5.isHidden())
mv = v["mvr"]
p1_exp = IAPWS.saturation_pressure(68.5)
p2_exp = p1_exp * 1.8
check("压缩前压力 p₁ = p_sat(68.5 °C) = 0.02923 MPa(a)", close_abs(mv["p1"], p1_exp, 1e-12),
      f'{mv["p1"]:.6f}')
check("压缩后压力 p₂ = p₁·π = 0.05262 MPa(a)", close_abs(mv["p2"], p2_exp, 1e-12),
      f'{mv["p2"]:.6f}')
check("压缩后饱和温度 ≈ 82.6 °C（蒸汽表 0.0526 MPa → 82.6 °C）",
      close_abs(mv["T2_sat"], 82.60, 0.3), f'{mv["T2_sat"]:.2f}')
check("有效传热温差 = T₂sat − t_b = 12.59 °C", close_abs(v["dt_eff_total"],
                                                    mv["T2_sat"] - 70.0, 1e-12),
      f'{v["dt_eff_total"]:.3f}')
h1_exp = IAPWS.saturation_properties(P_MPa=p1_exp)["h_g"]
s1_exp = IAPWS.saturation_properties(P_MPa=p1_exp)["s_g"]
h2s_exp = IAPWS.properties_from_ps(p2_exp, s1_exp)["h"]
check("h₁ = h_g(p₁) 取饱和蒸汽焓", close_abs(mv["h1"], h1_exp, 1e-9), f'{mv["h1"]:.3f}')
check("h_2s = h(p₂, s=s₁) 等熵反算", close_abs(mv["h2s"], h2s_exp, 1e-9), f'{mv["h2s"]:.3f}')
check("等熵焓升 w_is = h_2s − h₁ ≈ 41.5 kJ/kg", close_abs(mv["w_is"], h2s_exp - h1_exp, 1e-9),
      f'{mv["w_is"]:.3f}')
check("实际比功 w_act = w_is/η_is = w_is/0.75", close_abs(mv["w_act"], mv["w_is"] / 0.75, 1e-9),
      f'{mv["w_act"]:.3f}')
check("压缩机轴功率 = W·w_act/3600 ≈ 123 kW",
      close_abs(mv["P_shaft"], 8000.0 * mv["w_act"] / 3600.0, 1e-9), f'{mv["P_shaft"]:.2f}')
check("电机输入功率 = 轴功率/η_m = 轴功率/0.95",
      close_abs(mv["P_motor"], mv["P_shaft"] / 0.95, 1e-9), f'{mv["P_motor"]:.2f}')
check("单位电耗 = P_电机/(W/1000) 落在 10~40 kWh/t",
      10.0 <= mv["unit_kwh"] <= 40.0, f'{mv["unit_kwh"]:.2f}')
check("MVR 段电耗远优于单效汽耗（无生蒸汽主耗）", mv["unit_kwh"] < 40.0)
check("过热度 ≥ 0", mv["superheat"] >= 0.0, f'{mv["superheat"]:.2f}')
check("供热/需热差额与补充生蒸汽逻辑自洽",
      (mv["delta_kw"] < 0) == (mv["D_supply"] > 0), f'{mv["delta_kw"]:.1f}/{mv["D_supply"]:.1f}')
# 渲染缺口守卫：MVR 正文也必须出现「四、面积与校核」（曾因 else 分支吞掉该段而缺设计面积）
_mvr_txt = ev.result_text.toPlainText()
check("MVR 正文含「四、面积与校核」段（设计面积不因模式缺失）",
      "四、面积与校核" in _mvr_txt and "设计面积" in _mvr_txt,
      _mvr_txt[-300:].replace(chr(10), ' | '))

# ── 2.7 TVR ──
ev.mode_combo.setCurrentText("TVR 热力蒸汽再压缩")
ev.ejector_input.setText("0.8")
ev.calculate()
t = ev._last_result
check("TVR 计算成功且含 tvr 段", bool(t) and t.get("tvr") is not None,
      ev.result_text.toPlainText()[:80])
tv = t["tvr"]
check("TVR 在多效基础上叠加（3 效）", t["n"] == 3, str(t["n"]))
check("生蒸汽 = D_多效/(1+u) = D_多效/1.8", close_abs(tv["D_new"], tv["D_raw"] / 1.8, 1e-9),
      f'{tv["D_new"]:.1f}')
check("引射二次蒸汽 = D_多效 − D_新", close_abs(tv["D_eject"], tv["D_raw"] - tv["D_new"], 1e-12))
check("蒸汽经济性 ×(1+u) = ×1.8", close_abs(tv["economy_new"], tv["economy_raw"] * 1.8, 1e-9),
      f'{tv["economy_new"]:.4f}')
check("TVR 经济性优于同效数多效", t["economy"] > tv["economy_raw"],
      f'{t["economy"]:.3f} > {tv["economy_raw"]:.3f}')
check("TVR 结果 D 已更新为引射后生蒸汽量", close_abs(t["D"], tv["D_new"], 1e-12))
check("TVR 给出「引射系数随压比升高迅速下降」提示",
      any("喷射器" in w for w in t["warn"]), str(t["warn"])[:120])
ev.ejector_input.setText("1.6")
ev.calculate()
check("引射系数 > 1.2 → 提示核实喷射器选型",
      any("1.2" in w for w in ev._last_result["warn"]), str(ev._last_result["warn"])[:150])
ev.ejector_input.setText("0.8")

# ── 2.8 四方案能耗对比 ──
ev.mode_combo.setCurrentText("多效蒸发（并流）")
ev.calculate()
rows = ev._last_result["compare"]["rows"]
check("对比表含 4 个方案", len(rows) == 4, str([r[0] for r in rows]))
names = [r[0] for r in rows]
check("对比表含 单效/多效/MVR/TVR",
      any("单效" in n for n in names) and any("多效" in n for n in names)
      and any("MVR" in n for n in names) and any("TVR" in n for n in names), str(names))
spw = {n: r[2] for n, r in zip(names, rows)}
single_k = [n for n in names if "单效" in n][0]
mvr_k = [n for n in names if "MVR" in n][0]
check("对比口径自洽：单效汽耗 ≈ 1.247 t/t",
      close_abs(rows[names.index(single_k)][2], D_exp / 8000.0, 1e-6),
      f'{rows[names.index(single_k)][2]:.3f}')
check("MVR 汽耗（补热）最低", spw[mvr_k] == min(spw.values()), str(spw))

# ── 2.9 加热室形式 → K 联动 ──
ev.heater_combo.setCurrentText("强制循环/外循环")
check("选强制循环 → K₁ 自动填 1200", ev.k1_input.text() == "1200", ev.k1_input.text())
check("选强制循环 → 单效/MVR 用 K 同步填 1200", ev.k_single_input.text() == "1200")
ev.heater_combo.setCurrentText("升膜式")
check("选升膜式 → K 自动填 2000", ev.k1_input.text() == "2000", ev.k1_input.text())
ev.heater_combo.setCurrentText("降膜式（清洁物料）")
check("回落降膜清洁 → K 自动填 2500", ev.k1_input.text() == "2500")

# ── 2.10 参数校验与清空 ──
ev.mode_combo.setCurrentText("单效蒸发")
ev.x1_input.setText("10")            # x1 < x0
ev.calculate()
check("出料浓度 ≤ 进料浓度 → 报错", ev.result_text.toPlainText().startswith("错误"),
      ev.result_text.toPlainText()[:60])
ev.x1_input.setText("60")
ev.tb_input.setText("160")            # 单效蒸发温度高于生蒸汽饱和温度 151.9 °C
ev.calculate()
check("单效蒸发温度高于生蒸汽饱和温度 → 报「有效温差 ≤ 0」",
      ev.result_text.toPlainText().startswith("错误")
      and "温差" in ev.result_text.toPlainText(), ev.result_text.toPlainText()[:70])
ev.tb_input.setText("70")
ev.mode_combo.setCurrentText("多效蒸发（并流）")
ev.tb_input.setText("175")            # 末效沸点 175 °C > 生蒸汽 151.9 °C
ev.calculate()
check("多效末效沸点高于生蒸汽饱和温度 → 报「有效总温差不足」",
      ev.result_text.toPlainText().startswith("错误")
      and "温差" in ev.result_text.toPlainText(), ev.result_text.toPlainText()[:70])
ev.tb_input.setText("70")
ev.clear_inputs()
check("clear 后模式恢复单效", ev.mode_combo.currentIndex() == 0)
check("clear 后效数恢复 3 效", ev.effects_combo.currentText() == "3 效")
check("clear 后加热室恢复降膜清洁", ev.heater_combo.currentIndex() == 0)
check("clear 后进料量恢复 10000", ev.feed_input.text() == "10000")
check("clear 后结果框清空", ev.result_text.toPlainText() == "")
ev.calculate()
check("clear 后可直接重算", bool(ev._last_result)
      and close(ev._last_result["W_calc"], 8000.0, 1e-12))

# ── 2.11 报告与历史契约 ──
rep2 = ev.generate_report()
check("蒸发器 generate_report 返回 str", isinstance(rep2, str), type(rep2).__name__)
check("报告含标题与物料/热量公式", "浓缩蒸发器计算书" in rep2 and "W = F·(1 − x0/x1)" in rep2
      and "λ'" in rep2)
check("报告标注 BPE 不做关联式推算", "不做关联式推算" in rep2)
check("报告含蒸发强度与 K 的经验区间",
      "20~35" in rep2 and "1500~3500" in rep2)
info2 = ev.get_project_info()
check("蒸发器 get_project_info 为 dict 且标准键齐全",
      isinstance(info2, dict) and {"company_name", "project_number", "project_name",
                                   "subproject_name", "calculation_type"} <= set(info2),
      str(sorted(info2)))
h2 = ev._get_history_data()
check("蒸发器历史 inputs 含进料量/出料浓度/效数",
      {"进料量_kg_h", "出料浓度_wt%", "效数"} <= set(h2["inputs"]), str(h2["inputs"]))
check("蒸发器历史 outputs 含蒸发水量/生蒸汽耗量/设计面积",
      {"蒸发水量_kg_h", "生蒸汽耗量_kg_h", "设计面积_m2"} <= set(h2["outputs"]),
      str(h2["outputs"]))
check("蒸发器 SVG 示意图已加载", ev.svg_widget.renderer().isValid())
ev.mode_combo.setCurrentText("MVR 机械蒸汽再压缩")
ev.calculate()
h3 = ev._get_history_data()
check("MVR 模式历史增加电耗条目", "单位电耗_kWh_t" in h3["outputs"], str(h3["outputs"]))

# ══════════════════════════════ Part 3: 注册表口径 ══════════════════════════════
print('── Part 3: 注册表与分类口径 ──')
_widget_src = open(os.path.join(ROOT, 'modules', 'chemical_calculations',
                                'chemical_calculations_widget.py'), encoding='utf-8').read()
check("filter_press_area_calculator 已登记到 page_configs",
      '"filter_press_area_calculator"' in _widget_src)
check("evaporator_calculator 已登记到 page_configs",
      '"evaporator_calculator"' in _widget_src)
check("两页均归入「工艺设备」分类",
      '"filter_press_area_calculator": "工艺设备"' in _widget_src
      and '"evaporator_calculator": "工艺设备"' in _widget_src)

# ══════════════════════════════ 汇总 ══════════════════════════════
print('=' * 60)
print(f'通过 {len(PASS)} / {len(PASS) + len(FAIL)}')
if FAIL:
    print('失败项：')
    for n, d in FAIL:
        print(f'  ✗ {n}  [{d}]')
    sys.exit(1)
print('全部通过')
