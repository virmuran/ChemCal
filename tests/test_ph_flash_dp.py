# -*- coding: utf-8 -*-
"""压降计算 + pH 计算 + 混合液体闪点 回归测试

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_ph_flash_dp.py

核对依据与手算锚点：

一、压降计算（pressure_drop_calculator.py）
  1) 自定义绝热系数被忽略：原 get_adiabatic_value 先解析下拉文本，"自定义绝热系数"
     取不到数字 → 回落 1.4，用户输入完全无效。锚点：填入 1.3 → 必须返回 1.3。
  2) 气体密度口径：流体表气体密度是 101.325kPa/20°C 标准状态值，原实现直接用于
     高压入口算声速；等温式又用起始压力反推 R（高压下 R 被同步放大）→ 压降失真。
     现统一 _gas_R / _gas_inlet_density，并按标准状态反推 R。
  3) 阻塞流：原 mach≥1 分支拍 0.5·P1；管长超 L* 分支拍 P1(1−M²)。现统一按声速
     截面 P* = P1·M·√((γ+1)/(2+(γ−1)M²)) 计算。
  4) 历史记录原用另一套公式（等温模式竟用不可压缩 Darcy 式、绝热模式用
     287·293 与线性化压比）。现主计算与 _get_history_data 共用
     _friction_and_reynolds / _adiabatic_dp / _isothermal_dp。
  锚点（水 50 m³/h, DN100, 300 m, ε=0.2mm, 20°C）：
    v = (50/3600)/(π·0.05²) = 1.7685 m/s
    Re = 998×1.7685×0.1/0.001004 ≈ 1.758×10⁵，f(Colebrook, ε/D=0.002) ≈ 0.02442
    Δp_沿程 = f·(L/D)·ρv²/2 ≈ 114.4 kPa；ξ=5 → 局部 7.80 kPa；Δz=10m → 静压 97.90 kPa
  锚点（空气 100 m³/h, DN100, 300 m, P=101.3 kPa）：R≈286.9，ρ_in≈1.2045，
    v=3.537 m/s，Re≈2.82×10⁴，f≈0.02832
    等温 Δp = P1−√(P1²−(fL/D)G²RT) ≈ 0.64 kPa
    绝热(Fanno) Δp ≈ 2.55 kPa
  锚点（空气 1000 m³/h, DN50, 2000 m, P=101.3 kPa）：v=141.5 m/s，
    M=0.4124，L*≈185m < 2000m → 阻塞，Δp = P1(1−P*/P1) ≈ 56.3 kPa

二、pH 计算（ph_calculator.py）
  1) pK 表约定错乱：Tris 填的是 pKa(8.07) 却放在"碱"（pKb）栏 → pH 偏低 2 个单位。
     现统一约定"碱→pKb"，Tris = 14−8.06 = 5.94。锚点：[BH⁺]/[B]=1 → pH = 8.06。
  2) 弱电解稀释公式错：原 (-pk+√(pk²+4·pk·Ca))/2 把 pK 当 Ka、把 10^-pH 当浓度，
     数值上退化为 pH2 = pH1 + log(factor)（等同强酸），pKa 实际未起作用。
     现按 [H⁺]²+Ka[H⁺]−Ka·Ca=0 求解：Ca = x1²/Ka + x1。
     锚点（pH1=3, 10 倍稀释）：pKa=4.76 → Ca=0.05854 → pH2 = 3.508（修复前 4.00）
                               pKa=3.00 → Ca=0.00200 → pH2 = 3.767
  3) "自定义液体"参数缺失：液体模式隐藏分子量且无密度输入 → C 用占位 ρ=1、M=1，
     算出 10×wt% 的荒谬浓度。现液体模式开放 ρ 与 M 输入。
  4) 调节剂方向不校验：从 pH 7 降到 5 却选液碱照样出结果。现直接拒绝。
  5) 加碱方向用量算错 100 倍：原实现不分方向都用 |10^-pH1 − 10^-pH0|（即 Δ[H⁺]）。
     加酸时该式恰好正确；加碱时它算的是 H⁺ 的减少量，pH 7→9 仅 9.9e-8 mol/L，
     而实际需补充的 OH⁻ 增量为 9.9e-6 mol/L。现加碱方向改用 Δ[OH⁻]。
  锚点：pH 7→5，V=2500 L，ΔH = |10⁻⁵−10⁻⁷|×2500 = 0.02475 mol
        盐酸 31%（ρ=1.16, M=36.46）→ C = 9.8628 mol/L → 2.509 mL
        pH 7→9（加碱），ΔH = |10⁻⁵−10⁻⁷|×2500 = 0.02475 mol（与加酸同量级；修复前 2.475e-4）
        NaOH 片碱 99%（M=40, n=1）→ 0.99/40 = 0.02475 mol/g → 1.000 g（修复前 0.010 g）
        含缓冲（总酸 0.063 mol/L）→ 157.5 mol → 液碱 30%（9.975 mol/L）→ 15.79 L

三、混合液体闪点（mixed_liquid_flash_point_calculator.py）
  1) 结果框 HTML 污染：format_results 里带 <span style=...> 却用 setText()，
     Qt 判定为富文本 → 整段换行丢失。现改纯文本 + setPlainText。
  2) 不燃组分无法录入：对话框强制要求闪点，"水（闪点:无）"选不了 → 稀释剂完全
     无法建模。现闪点留空 = 不燃（None）。
  3) 沸点关联式：原 0.7×BP(°C)−50 属无出处经验式；现按 Riazi（Alqaheem & Riazi,
     Energy & Fuels 2017, 31, 3578；AIChE 2015）：T_fp = 0.7·T_bp（绝对温度）。
  4) 分级阈值错：原 <0/<23/<60 套 Class IA/IB/IC/II，与 GB 13690、GB 50016、
     GB 30000.7（GHS）边界均不符。现按三套标准分别标注。
  锚点（乙醇 50% + 甲醇 50%，乙醇 FP12.8/BP78.4/M46.07，甲醇 FP11.1/BP64.7/M32.04）：
    x_EtOH = (50/46.07)/(50/46.07+50/32.04) = 0.41018
    1/T = 0.41018/285.95 + 0.58982/284.25 = 3.50946e-3 → Le Chatelier = 11.79 °C
    最低闪点法 11.1；质量加权 11.95；摩尔加权 11.80
    沸点关联式 = 0.7×(0.5×78.4+0.5×64.7+273.15) − 273.15 = −31.86 °C
  锚点（乙醇 50% + 水 50%，水闪点留空）：最低闪点 12.8，且必须出现
    "含不燃稀释剂"适用性警示（Le Chatelier 简化式会严重高估）。
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

WARNINGS = []


def _rec(kind):
    def f(parent=None, title='', text='', *a, **k):
        WARNINGS.append((kind, title, str(text)))
        return QMessageBox.StandardButton.Ok
    return staticmethod(f)


QMessageBox.warning = _rec('warning')
QMessageBox.critical = _rec('critical')
QMessageBox.information = _rec('info')

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
    print(('PASS' if cond else 'FAIL') + f'  {name}' +
          (f'  [{detail}]' if detail and not cond else ''))


def _re(pat, text):
    import re
    m = re.search(pat, text)
    return float(m.group(1)) if m else None


# ══════════════════ Part 1: 压降计算 ══════════════════
print('── Part 1: 压降计算 ──')
m1 = _load('t_pdrop', os.path.join(CALC_DIR, 'pressure_drop_calculator.py'))
pd = m1.压降计算()

# ---- 自定义绝热系数（修复前恒 1.4） ----
pd.adiabatic_combo.setCurrentText("自定义绝热系数")
pd.adiabatic_input.setText("1.3")
check("自定义绝热系数 1.3 生效（修复前被忽略恒返回 1.4）",
      abs(pd.get_adiabatic_value() - 1.3) < 1e-9, str(pd.get_adiabatic_value()))
pd.adiabatic_combo.setCurrentText("1.40 - 双原子气体")
check("预设绝热系数 1.40 正常", abs(pd.get_adiabatic_value() - 1.40) < 1e-9,
      str(pd.get_adiabatic_value()))
pd.adiabatic_combo.setCurrentText("1.30 - 三原子气体")
check("预设绝热系数 1.30 正常", abs(pd.get_adiabatic_value() - 1.30) < 1e-9,
      str(pd.get_adiabatic_value()))

# ---- 不可压缩：水 ----
pd.fluid_combo.setCurrentText("水 (20°C) - 密度: 998.0, 粘度: 1.004")
pd.diameter_input.setText("100")
pd.length_input.setText("300")
pd.flow_input.setText("50")
pd.roughness_input.setText("0.2")
pd.elevation_input.setText("0")
pd.local_resistance_coeff = 0.0
pd.calculate_pressure_drop()
txt = pd.result_text.toPlainText()
v = _re(r'流速:\s*([\d.]+)\s*m/s', txt)
re_n = _re(r'雷诺数:\s*([\d.]+)', txt)
f = _re(r'摩擦系数:\s*([\d.]+)', txt)
dp_f = _re(r'沿程阻力损失:\s*([\d.]+)', txt)
check("水 DN100/50m³/h 流速 ≈1.769 m/s", v is not None and abs(v - 1.7685) < 0.01, str(v))
check("雷诺数 ≈1.758×10⁵", re_n is not None and abs(re_n - 175800) / 175800 < 0.01, str(re_n))
check("Colebrook 摩擦系数 ≈0.02442", f is not None and abs(f - 0.02442) / 0.02442 < 0.01, str(f))
check("沿程阻力 ≈114.4 kPa", dp_f is not None and abs(dp_f - 114.4) / 114.4 < 0.02, str(dp_f))

# 局部阻力 ξ=5 → 5·ρv²/2 = 7.80 kPa
pd.local_resistance_coeff = 5.0
pd.calculate_pressure_drop()
txt = pd.result_text.toPlainText()
dp_l = _re(r'局部阻力损失:\s*([\d.]+)', txt)
check("局部阻力 ξ=5 → 7.80 kPa", dp_l is not None and abs(dp_l - 7.803) / 7.803 < 0.02, str(dp_l))

# 标高 +10 m → 静压 998×9.81×10 = 97.90 kPa
pd.elevation_input.setText("10")
pd.calculate_pressure_drop()
txt = pd.result_text.toPlainText()
dp_z = _re(r'静压头变化:\s*([\d.]+)', txt)
dp_tot = _re(r'总压力损失:\s*([\d.]+)', txt)
check("标高 +10m → 静压头 97.90 kPa", dp_z is not None and abs(dp_z - 97.90) / 97.90 < 0.02, str(dp_z))
check("总损失 = 沿程+局部+静压（三项相加自洽）",
      dp_tot is not None and abs(dp_tot - (114.4 + 7.803 + 97.90)) / dp_tot < 0.03, str(dp_tot))
pd.elevation_input.setText("0")
pd.local_resistance_coeff = 0.0

# ---- 可压缩模式 + 液体 → 必须拒绝 ----
WARNINGS.clear()
pd.mode_buttons["可压缩流体（等温）"].setChecked(True)
pd.calculate_pressure_drop()
check("液体选可压缩模式被拒绝（提示仅适用于气体）",
      any('仅适用于气体' in w[2] for w in WARNINGS), str(WARNINGS[:1]))

# ---- 等温可压缩：空气 ----
pd.mode_buttons["可压缩流体（等温）"].setChecked(True)
pd.fluid_combo.setCurrentText("空气 (20°C) - 密度: 1.2047, 粘度: 0.0151")
pd.diameter_input.setText("100")
pd.length_input.setText("300")
pd.flow_input.setText("100")
pd.pressure_input.setText("101.3")
pd.calculate_pressure_drop()
txt = pd.result_text.toPlainText()
dpi = _re(r'总压力损失:\s*([\d.]+)', txt)
check("等温(空气 DN100/100m³/h/300m) Δp ≈0.64 kPa",
      dpi is not None and abs(dpi - 0.643) / 0.643 < 0.05, str(dpi))
check("结果标注 R 由标准状态反推/入口密度",
      "入口密度" in txt and "标准状态密度" in txt)
hist = pd._get_history_data()["outputs"]
check("历史记录与主计算同口径（等温）",
      abs(hist["总压降(kPa)"] - dpi) / dpi < 0.01,
      f'hist={hist.get("总压降(kPa)")} shown={dpi}')

# ---- 绝热 Fanno 小马赫数 ----
pd.mode_buttons["可压缩流体（绝热）"].setChecked(True)
pd.adiabatic_combo.setCurrentText("1.40 - 双原子气体")
pd.calculate_pressure_drop()
txt = pd.result_text.toPlainText()
dpa = _re(r'总压力损失:\s*([\d.]+)', txt)
ma = _re(r'马赫数:\s*([\d.]+)', txt)
check("绝热(空气 DN100/300m) 马赫数 ≈0.0103", ma is not None and abs(ma - 0.01031) < 0.002, str(ma))
check("绝热 Fanno Δp ≈2.55 kPa", dpa is not None and abs(dpa - 2.55) / 2.55 < 0.05, str(dpa))
hist = pd._get_history_data()["outputs"]
check("历史记录与主计算同口径（绝热）",
      abs(hist["总压降(kPa)"] - dpa) / dpa < 0.01,
      f'hist={hist.get("总压降(kPa)")} shown={dpa}')

# ---- 绝热阻塞流：空气 DN50 / 1000 m³/h / 2000 m ----
pd.mode_buttons["可压缩流体（绝热）"].setChecked(True)
pd.diameter_input.setText("50")
pd.length_input.setText("2000")
pd.flow_input.setText("1000")
pd.calculate_pressure_drop()
txt = pd.result_text.toPlainText()
dpa2 = _re(r'总压力损失:\s*([\d.]+)', txt)
check("阻塞流被识别并提示 L*", "阻塞" in txt)
check("阻塞流 Δp ≈56.3 kPa（修复前线性式给 101.3 kPa 全压损失）",
      dpa2 is not None and abs(dpa2 - 56.3) / 56.3 < 0.05, str(dpa2))
h2 = pd._get_history_data()["outputs"]
check("阻塞工况历史记录同步为 56 kPa 量级（不再走 max(0,…)=0 的旧式）",
      abs(h2["总压降(kPa)"] - dpa2) / dpa2 < 0.01, str(h2.get("总压降(kPa)")))

# ---- clear 恢复默认（不再清空成空值） ----
pd.clear_inputs()
check("清空后 length 恢复默认 300", pd.length_input.text() == "300",
      repr(pd.length_input.text()))
check("清空后 diameter 恢复默认 100", pd.diameter_input.text() == "100",
      repr(pd.diameter_input.text()))
check("清空后 pressure 恢复默认 101.3", pd.pressure_input.text() == "101.3",
      repr(pd.pressure_input.text()))
pd.mode_buttons["不可压缩流体"].setChecked(True)
pd.fluid_combo.setCurrentText("水 (20°C) - 密度: 998.0, 粘度: 1.004")
pd.flow_input.setText("50")
pd.calculate_pressure_drop()
check("clear 后可直接重算（不报缺少参数）",
      "总压力损失" in pd.result_text.toPlainText())


# ══════════════════ Part 2: pH 计算 ══════════════════
print('── Part 2: pH 计算 ──')
m2 = _load('t_ph', os.path.join(CALC_DIR, 'ph_calculator.py'))
ph = m2.PHCalculator()

# pK 表约定
check("Tris pKb 修正为 5.94（原填 pKa 8.07 放在 pKb 栏）",
      abs(m2.PK_TABLE["Tris-HCl"][1] - 5.94) < 1e-9,
      str(m2.PK_TABLE["Tris-HCl"]))

# ---- 酸碱中和 ----
ph._all_inputs["n_C"].setText("1.0")
ph._all_inputs["n_V"].setText("1.0")
ph._all_inputs["n_val"].setText("1")
ph._all_inputs["n_other_C"].setText("2.0")
ph._all_inputs["n_other_val"].setText("1")
ph.calculate()
r = ph._last_results
check("中和：1mol/L×1L 需 2mol/L 碱 0.5 L", abs(r.get("V2", 0) - 0.5) < 1e-6, str(r.get("V2")))

# ---- 缓冲溶液（Henderson-Hasselbalch） ----
ph.mode_btns["缓冲溶液 pH"].setChecked(True)
ph._all_inputs["buf_system"].setCurrentIndex(0)      # 手动输入 pKa
ph._all_inputs["buf_pk"].setText("4.76")
ph._all_inputs["buf_type"].setCurrentIndex(0)        # 酸型
ph._all_inputs["buf_salt"].setText("0.1")
ph._all_inputs["buf_acid"].setText("0.1")
ph.calculate()
check("缓冲：[A⁻]=[HA] → pH = pKa = 4.76",
      abs(ph._last_results.get("pH", 0) - 4.76) < 1e-6, str(ph._last_results.get("pH")))
ph._all_inputs["buf_salt"].setText("0.05")
ph.calculate()
check("缓冲：比值 0.5 → pH = 4.76 − 0.301 = 4.459",
      abs(ph._last_results.get("pH", 0) - 4.459) < 1e-3, str(ph._last_results.get("pH")))

# Tris 修正后的 pH
ph._all_inputs["buf_system"].setCurrentText("Tris-HCl")
ph._all_inputs["buf_type"].setCurrentIndex(1)        # 碱型
ph._all_inputs["buf_salt"].setText("0.1")
ph._all_inputs["buf_acid"].setText("0.1")
ph.calculate()
check("Tris 碱型 [BH⁺]/[B]=1 → pH = 14−5.94 = 8.06（修复前 5.93）",
      abs(ph._last_results.get("pH", 0) - 8.06) < 0.01, str(ph._last_results.get("pH")))

# ---- 稀释：弱酸必须体现 pKa（修复前退化为强酸） ----
ph.mode_btns["稀释后 pH"].setChecked(True)
ph._all_inputs["dil_type"].setCurrentIndex(0)        # 强酸
ph._all_inputs["dil_pH1"].setText("3.0")
ph._all_inputs["dil_V1"].setText("1.0")
ph._all_inputs["dil_V2"].setText("10.0")
ph.calculate()
check("强酸 10 倍稀释 pH 3.0 → 4.00",
      abs(ph._last_results.get("pH2", 0) - 4.0) < 1e-6, str(ph._last_results.get("pH2")))

ph._all_inputs["dil_type"].setCurrentIndex(2)        # 弱酸（需 pKa）
ph._all_inputs["dil_pk"].setText("4.76")
ph.calculate()
pka476 = ph._last_results.get("pH2", 0)
check("弱酸(pKa=4.76) 稀释 pH 3.0 → 3.508（修复前等同强酸给 4.00）",
      abs(pka476 - 3.508) < 0.01, str(pka476))
ph._all_inputs["dil_pk"].setText("3.0")
ph.calculate()
pka300 = ph._last_results.get("pH2", 0)
check("弱酸(pKa=3.00) 稀释 pH 3.0 → 3.767（pKa 确实参与计算）",
      abs(pka300 - 3.767) < 0.01, str(pka300))
check("pKa 不同 → 结果不同（旧式两者皆为 4.00）", abs(pka476 - pka300) > 0.2,
      f'{pka476:.3f} vs {pka300:.3f}')

# 不合理输入守卫
ph._all_inputs["dil_pk"].setText("4.76")
ph._all_inputs["dil_pH1"].setText("1.0")
ph.calculate()
check("弱酸 pH1=1.0 与 pKa=4.76 不匹配 → 报错而非给出荒谬结果",
      "计算错误" in ph.result_text.toPlainText(), ph.result_text.toPlainText()[:60])
ph._all_inputs["dil_pH1"].setText("3.0")

# ---- pH 调节 ----
ph.mode_btns["pH 调节"].setChecked(True)
ph._all_inputs["adj_pH0"].setText("7.0")
ph._all_inputs["adj_pH1"].setText("5.0")
ph._all_inputs["adj_V"].setText("2500")
ph._all_inputs["adj_reagent"].setCurrentText("盐酸 31% (工业)")
check("液体试剂自动填充 ρ=1.16", abs(ph._get("adj_rho") - 1.16) < 1e-9,
      str(ph._get("adj_rho")))
check("液体试剂自动填充 M=36.46", abs(ph._get("adj_mw") - 36.46) < 1e-9,
      str(ph._get("adj_mw")))
ph.calculate()
rr = ph._last_results
check("调节 7→5：ΔH = 0.02475 mol", abs(rr.get("delta_H_mol", 0) - 0.02475) < 1e-6,
      str(rr.get("delta_H_mol")))
check("盐酸 31% C ≈9.863 mol/L", abs(rr.get("conc_molL", 0) - 9.8628) < 0.01,
      str(rr.get("conc_molL")))
check("需盐酸 31% ≈2.509 mL", abs(rr.get("amount", 0) - 2.509) < 0.02,
      str(rr.get("amount")))

# 固体试剂
ph._all_inputs["adj_reagent"].setCurrentText("NaOH 片碱 (99%)")
ph._all_inputs["adj_pH1"].setText("9.0")
ph.calculate()
rr = ph._last_results
check("加碱方向 ΔH 按 Δ[OH⁻] 计：7→9 = 9.9e-6×2500 = 0.02475 mol（修复前 2.475e-4）",
      abs(rr.get("delta_H_mol", 0) - 0.02475) < 1e-6, str(rr.get("delta_H_mol")))
check("调节 7→9（固体 NaOH 99%）需 1.000 g",
      abs(rr.get("amount", 0) - 1.0) < 0.005, str(rr.get("amount")))
check("方向识别为加碱", "加碱" in rr.get("direction", ""), rr.get("direction"))

# 方向不符 → 拒绝
ph._all_inputs["adj_pH1"].setText("5.0")
ph._all_inputs["adj_reagent"].setCurrentText("液碱 NaOH 30%")
ph.calculate()
check("需加酸却选液碱 → 明确拒绝（修复前照算）",
      "请更换调节剂" in ph.result_text.toPlainText(),
      ph.result_text.toPlainText()[:60])

# 含缓冲体系（加碱方向：pH1 必须 > pH0，否则会被方向校验拦下）
ph._adj_buf_cb.setChecked(True)
ph._all_inputs["adj_total_acid"].setText("0.063")
ph._all_inputs["adj_pH1"].setText("9.0")
ph._all_inputs["adj_reagent"].setCurrentText("液碱 NaOH 30%")
ph.calculate()
rr = ph._last_results
check("含缓冲：ΔH = 0.063×2500 = 157.5 mol", abs(rr.get("delta_H_mol", 0) - 157.5) < 0.1,
      str(rr.get("delta_H_mol")))
check("含缓冲：液碱 30%(9.975 mol/L) → 15.79 L",
      abs(rr.get("amount", 0) - 15789) / 15789 < 0.01, str(rr.get("amount")))
ph._adj_buf_cb.setChecked(False)

# ---- 导出契约 ----
m2b = _load('t_ph2', os.path.join(CALC_DIR, 'ph_calculator.py'))
ph2 = m2b.PHCalculator()
check("pH 未计算时 generate_report 返回 None", ph2.generate_report() is None)
pi = ph2.get_project_info()
check("pH get_project_info 用标准键（company_name 等）",
      all(k in pi for k in ("company_name", "project_number",
                            "project_name", "subproject_name")), str(list(pi)))
check("pH 已计算后 generate_report 返回非空文本",
      isinstance(ph.generate_report(), str) and len(ph.generate_report()) > 100)

# ---- clear 恢复默认 ----
ph.clear()
check("pH clear 后 n_C 恢复 1.0", ph._all_inputs["n_C"].text() == "1.0",
      repr(ph._all_inputs["n_C"].text()))
check("pH clear 后试剂参数重新联动（ρ 非空）", ph._get("adj_rho") > 0,
      str(ph._get("adj_rho")))
check("pH clear 后 adj_mw 恢复 40（液碱）", abs(ph._get("adj_mw") - 40.0) < 1e-9,
      str(ph._get("adj_mw")))
hist = ph._get_history_data()
check("pH 历史记录含输入参数与输出", "inputs" in hist and "outputs" in hist
      and hist["inputs"].get("计算模式"), str(list(hist.get("inputs", {}))[:5]))


# ══════════════════ Part 3: 混合液体闪点 ══════════════════
print('── Part 3: 混合液体闪点 ──')
m3 = _load('t_flash', os.path.join(CALC_DIR, 'mixed_liquid_flash_point_calculator.py'))

# 对话框：闪点留空 = 不燃
dlg = m3.ComponentDialog()
dlg.name_input.setText("水")
dlg.flash_input.clear()
dlg.fraction_input.setText("50")
dlg.boiling_input.setText("100")
dlg.mw_input.setText("18.02")
dlg.validate_and_accept()
cd = dlg.get_component_data()
check("对话框允许闪点留空（不燃组分）", cd["flash_point"] is None, str(cd))

fp_calc = m3.MixedLiquidFlashPointCalculator()
fp_calc.components = [
    {"name": "乙醇", "flash_point": 12.8, "boiling_point": 78.4,
     "molecular_weight": 46.07, "mass_fraction": 50.0},
    {"name": "甲醇", "flash_point": 11.1, "boiling_point": 64.7,
     "molecular_weight": 32.04, "mass_fraction": 50.0},
]
fp_calc.update_components_table()

lc = fp_calc.calculate_le_chatelier()
check("Le Chatelier 乙醇/甲醇 = 11.79 °C", abs(lc - 11.79) < 0.05, str(lc))
check("最低闪点法 = 11.1", abs(fp_calc.calculate_minimum_flash() - 11.1) < 1e-9)
check("质量加权平均 = 11.95", abs(fp_calc.calculate_weighted_average_mass() - 11.95) < 0.01,
      str(fp_calc.calculate_weighted_average_mass()))
check("摩尔加权平均 = 11.80", abs(fp_calc.calculate_weighted_average_molar() - 11.797) < 0.01,
      str(fp_calc.calculate_weighted_average_molar()))
cox = fp_calc.calculate_cox_method()
check("沸点关联式 T_fp=0.7·T_bp(K) = −31.86 °C（原 0.7BP−50 给 0.09）",
      abs(cox - (-31.86)) < 0.05, str(cox))

# 结果输出：纯文本、无 HTML、多行
fp_calc.calculate_flash_point()
txt = fp_calc.result_text.toPlainText()
check("结果不含 HTML 标签（修复前 setText 会整段按 HTML 渲染）", "<span" not in txt)
check("结果为多行文本（换行未丢失）", txt.count("\n") > 10, str(txt.count("\n")))
check("结果含 GB 13690 分档", "GB 13690" in txt)
check("结果含 GB 50016 火灾危险性分类", "GB 50016" in txt)
check("FP=11.79 → 中闪点液体 / 甲类 / GHS 类别2（初沸点 64.7>35）",
      "中闪点液体" in txt and "甲类" in txt and "类别 2" in txt)

# 分级单元校验
check("GB13690 −20°C → 低闪点液体", "低闪点" in m3.MixedLiquidFlashPointCalculator.classify_gb13690(-20))
check("GB13690 0°C → 中闪点液体", "中闪点" in m3.MixedLiquidFlashPointCalculator.classify_gb13690(0))
check("GB13690 40°C → 高闪点液体", "高闪点" in m3.MixedLiquidFlashPointCalculator.classify_gb13690(40))
check("GB13690 70°C → 不属易燃液体", "不属易燃" in m3.MixedLiquidFlashPointCalculator.classify_gb13690(70))
check("GB50016 40°C → 乙类", "乙类" in m3.MixedLiquidFlashPointCalculator.classify_gb50016(40))
check("GB50016 70°C → 丙类", "丙类" in m3.MixedLiquidFlashPointCalculator.classify_gb50016(70))
check("GHS 类别1（FP<23 且初沸点 ≤35）",
      "类别 1" in fp_calc.get_flash_point_classification(11.8, 30.0))
check("GHS 类别3（23≤FP≤60）",
      "类别 3" in fp_calc.get_flash_point_classification(40.0, 90.0))
check("GHS 类别4（60<FP≤93）",
      "类别 4" in fp_calc.get_flash_point_classification(70.0, 150.0))

# 不燃组分（水）参与
fp_calc.components = [
    {"name": "乙醇", "flash_point": 12.8, "boiling_point": 78.4,
     "molecular_weight": 46.07, "mass_fraction": 50.0},
    {"name": "水", "flash_point": None, "boiling_point": 100.0,
     "molecular_weight": 18.02, "mass_fraction": 50.0},
]
fp_calc.update_components_table()
check("组分表把不燃组分显示为「不燃」",
      fp_calc.components_table.item(1, 1).text() == "不燃",
      fp_calc.components_table.item(1, 1).text())
check("最低闪点法仅取可燃组分 = 12.8",
      abs(fp_calc.calculate_minimum_flash() - 12.8) < 1e-9)
check("质量加权平均仅在可燃组分间归一 = 12.8",
      abs(fp_calc.calculate_weighted_average_mass() - 12.8) < 1e-9)
fp_calc.method_combo.setCurrentText("最低闪点法 - 保守估计，取最低组分闪点")
fp_calc.calculate_flash_point()
txt = fp_calc.result_text.toPlainText()
check("含水体系出现「含不燃稀释剂」适用性警示", "不燃稀释剂" in txt)
check("含水体系结果给出保守值 12.8 °C", "12.8" in txt)

# 全部不燃 → 无闪点
fp_calc.components = [
    {"name": "水", "flash_point": None, "boiling_point": 100.0,
     "molecular_weight": 18.02, "mass_fraction": 100.0},
]
fp_calc.calculate_flash_point()
check("全部不燃 → 提示无闪点而非崩溃",
      "无闪点" in fp_calc.result_text.toPlainText(),
      fp_calc.result_text.toPlainText()[:40])

# 导出契约
m3b = _load('t_flash2', os.path.join(CALC_DIR, 'mixed_liquid_flash_point_calculator.py'))
fp2 = m3b.MixedLiquidFlashPointCalculator()
check("闪点未计算时 generate_report 返回 None", fp2.generate_report() is None)
pi2 = fp2.get_project_info()
check("闪点 get_project_info 用标准键",
      all(k in pi2 for k in ("company_name", "project_number",
                             "project_name", "subproject_name")), str(list(pi2)))

fp_calc.components = [
    {"name": "乙醇", "flash_point": 12.8, "boiling_point": 78.4,
     "molecular_weight": 46.07, "mass_fraction": 100.0},
]
fp_calc.calculate_flash_point()
check("闪点已计算后 generate_report 返回非空文本",
      isinstance(fp_calc.generate_report(), str) and len(fp_calc.generate_report()) > 100)
h3 = fp_calc._get_history_data()
check("闪点历史记录含混合闪点输出", "混合液体闪点_C" in h3["outputs"], str(h3["outputs"]))
fp_calc.clear_inputs()
check("闪点 clear 后 generate_report 回到 None", fp_calc.generate_report() is None)


# ══════════════════ 汇总 ══════════════════
print()
print(f'通过 {len(PASS)} / {len(PASS) + len(FAIL)}')
if FAIL:
    print('失败项:')
    for n, d in FAIL:
        print(f'  ✗ {n}  [{d}]')
sys.exit(1 if FAIL else 0)
