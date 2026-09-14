# -*- coding: utf-8 -*-
"""容器/储罐类计算器回归测试（容器设计 GB150 + 设备尺寸）
纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_vessel_calculators.py

核对依据：
- GB 150.3 圆筒 δ = pc·Di/(2[σ]ᵗφ − pc)；标准椭圆封头 δ = pc·Di/(2[σ]ᵗφ − 0.5pc)
- GB 150.3 半球形封头 δ = pc·Ri/(2[σ]ᵗφ − 0.5pc) = pc·Di/(4[σ]ᵗφ − pc)
- GB 150.3 平盖 δ = Dc·√(K·pc/([σ]ᵗ·φ))（修复前漏 φ，偏薄 ~8%）
- GB 150.1 水压试验 pt = 1.25·pc·[σ]/[σ]t（修复前 [σ]/[σ] 恒 1）
- 设备尺寸反向计算：椭圆封头深度必须随求解直径缩放（修复前固定 0.25 m）
  锚点: 目标工作 10 m³, fill 0.85, H/D=2, EHA → V(D)=πD³·7/12 → D=1.8577 m，封头深 464 mm
- 修复前 bug：
  1) vessel_design 平盖漏焊缝系数（偏不安全）
  2) vessel_design 水压试验 σ/σ 死代码
  3) vessel_sizing 反向计算封头深度不随 D 缩放（容积几何失真）
  4) vessel_sizing 未计算时 generate_report 返回字符串 → 空壳计算书
  5) vessel_sizing clear_inputs 清成空值丢默认
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

# ══════════════════ Part 1: 容器设计 (GB 150) ══════════════════
m1 = _load('t_vessel_design', os.path.join(CALC_DIR, 'vessel_design_calculator.py'))
vd = m1.VesselDesignCalculator()

# 默认: Q235B, p=0.6, T=120°C, C2=1.5, C1=0.3, φ=0.85, Di=2400, H/D=2
vd.calculate()
txt = vd.result_text.toPlainText()

# δ_calc = 0.6*2.4/(2*111*0.85-0.6) = 7.66 mm（T=120 自动填 σ=111）→ 名义 9.46 → 9.5
check("圆筒名义壁厚 9.5 mm", "筒体名义壁厚: 9.5 mm" in txt, txt[:300])
check("圆筒计算壁厚 7.66 mm", "7.66 mm" in txt)
# 椭圆封头 δ = 1.44/(188.1-0.3) = 7.67 → 9.5
check("椭圆封头名义壁厚 9.5 mm", "封头名义壁厚: 9.5 mm" in txt)
# V = π·1.44·4.8 + 2·0.1309·13.824 = 25.33
check("全容积 25.33 m³", "25.33 m³" in txt, txt)
# Pt = 1.25*0.6*(113/111) = 0.76 (T=120: σ=111 插值)
check("水压试验 0.76 MPa (含[σ]比)", "0.76 MPa" in txt and "1.018" in txt, txt[:400])

# 平盖含 φ: δ = 2.4·√(0.3·0.6/(111·0.85)) = 104.83 + 1.53(蚀C2+C1=1.8... 实为 C2+C1=1.8) → 106.63 → 0.5mm 圆整 107.0
vd.inputs["head_type"].setCurrentText("平盖")
vd.calculate()
txt2 = vd.result_text.toPlainText()
check("平盖名义壁厚 107.0 mm (含φ修复)", "封头名义壁厚: 107.0 mm" in txt2, txt2[:400])

# 材料切换自动填应力: Q345R @120°C → 189−0.4·6=186.6 → 显示 187
vd.inputs["material"].setCurrentText("Q345R")
check("Q345R @120°C 自动填 187", vd.inputs["allow_stress"].text() == "187",
      vd.inputs["allow_stress"].text())

# 半球形封头: δ = 0.6*2.4/(4*111*0.85-0.6) = 3.82 mm → +1.8 = 5.62 → 0.5mm 圆整 6.0
vd.inputs["head_type"].setCurrentText("半球形封头")
vd.inputs["material"].setCurrentText("Q235B")
vd.calculate()
txt3 = vd.result_text.toPlainText()
check("半球封头壁厚 6.0 mm", "封头名义壁厚: 6.0 mm" in txt3, txt3[:400])

# 历史记录钩子
vd.inputs["head_type"].setCurrentText("标准椭圆封头 (EHA)")
vd.calculate()
h = vd._get_history_data()
check("设计历史: 壁厚 9.5", h["outputs"].get("筒体名义壁厚_mm") == 9.5, str(h["outputs"]))

# 未计算时报告返回 None
vd.clear()
vd.result_text.clear()
check("未计算 → generate_report None", vd.generate_report() is None)

# ══════════════════ Part 2: 设备尺寸 ══════════════════
m2 = _load('t_vessel_sizing', os.path.join(CALC_DIR, 'vessel_sizing_calculator.py'))
vs = m2.设备尺寸计算()

# 未计算 → 报告 None（修复前返回"尚未进行计算。"字符串）
check("未计算 → generate_report None", vs.generate_report() is None,
      repr(vs.generate_report()))

# 反向计算默认: 目标工作 10 m³, fill 0.85, H/D=2, EHA×2 auto
vs.calculate()
t = vs.result_text.toPlainText()
# V(D)=πD³·7/12 → D=1.8577 m, H=3.7154, 封头深 0.25·D=464.4 mm（旧 bug 下固定 250 mm）
check("反向 D≈1858 mm", "1857" in t or "1858" in t, t[:400])
check("封头深度随 D 缩放 464 mm (核心修复)", "464" in t, t[:500])
check("工作容积 ≈10.0 m³", "10.0" in t, t)

# 手算锚点: geo = π·D³·7/12
D, H = vs.solve_dimensions(10/0.85, 2.0, '椭圆封头', ('ratio', 0.25),
                           '椭圆封头', ('ratio', 0.25))
geo = math.pi * D**3 * 7/12
check("solve_dimensions 收敛 geo=11.765", abs(geo - 11.7647) < 0.01, f"{geo:.4f}")
check("D=1.8577", abs(D - 1.8577) < 0.002, f"{D:.4f}")

# 正向: D=1.0, H=2.0, EHA×2 → geo = 1.5708+0.2618 = 1.8326
vs.mode_buttons["正向计算"].setChecked(True)
vs.on_mode_changed("正向计算")
vs.calculate()
t2 = vs.result_text.toPlainText()
check("正向 geo=1.833 m³", "1.833" in t2, t2[:400])
check("正向工作容积 1.558", "1.558" in t2, t2)

# 锥形手动 30°: depth = 0.5·tan30 = 288.7 mm, V锥 = π/3·0.25·0.2887 = 0.0756
vs.bottom_type.setCurrentText("锥形封头")
vs.bottom_auto_check.setChecked(False)
vs.bottom_param_input.setEnabled(True)
vs.bottom_param_input.setText("30")
vs.calculate()
t3 = vs.result_text.toPlainText()
# geo = 1.5708 + 0.1309 + 0.0756 = 1.7773
check("锥形30° geo=1.777", "1.777" in t3, t3[:400])

# 历史记录（切回反向模式，恢复默认椭圆封头）
vs.mode_buttons["反向计算"].setChecked(True)
vs.on_mode_changed("反向计算")
vs.bottom_type.setCurrentText("椭圆封头")
vs.bottom_auto_check.setChecked(True)
vs.calculate()
h2 = vs._get_history_data()
check("历史: 直径≈1857.7", abs(h2["outputs"].get("直径_mm", 0) - 1857.7) < 2,
      str(h2["outputs"].get("直径_mm")))

# clear_inputs 恢复默认（修复前清成空值+下拉归零）
vs.fill_factor_input.setText("0.5")
vs.hd_ratio_input.setText("5.0")
vs.clear_inputs()
check("清空后 fill 恢复 0.85", vs.fill_factor_input.text() == "0.85",
      vs.fill_factor_input.text())
check("清空后 H/D 恢复 2.0", vs.hd_ratio_input.text() == "2.0",
      vs.hd_ratio_input.text())
check("清空后材料密度恢复 7850", vs.density_input.text() == "7850",
      vs.density_input.text())

# ══════════════════ 总结 ══════════════════
print("=" * 50)
print(f"总结: {len(PASS)} 通过, {len(FAIL)} 失败")
if FAIL:
    for name, d in FAIL:
        print(f"  FAIL: {name}  [{d[:120]}]")
    sys.exit(1)
sys.exit(0)
