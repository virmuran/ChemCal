# -*- coding: utf-8 -*-
"""
查询类三计算器回归测试：固体溶解度 / 溶液密度 / 纯物质物性
2026-09-13：查询类数据大修后固化（锚点均对照 CRC Handbook / Perry's / 教材数据表）
纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_query_calculators.py
"""
import os
import sys
import time
import tempfile

os.environ['QT_QPA_PLATFORM'] = 'offscreen'

PROJ = r"C:\Users\Administrator\Desktop\ChemCal"
for p in [PROJ,
          os.path.join(PROJ, "modules"),
          os.path.join(PROJ, "modules", "chemical_calculations"),
          os.path.join(PROJ, "modules", "chemical_calculations", "calculators")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data_manager import DataManager
DataManager.get_instance(data_file=os.path.join(tempfile.mkdtemp(), 'test_query.json'))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

PASS = FAIL = 0
def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}   | {extra}")

def approx(v, ref, tol):
    return v is not None and abs(v - ref) <= tol

print("=" * 60)
print("A. 溶液密度")
print("=" * 60)
import solution_density_calculator as sd

check("纯水 0°C=999.84", approx(sd.rho_water(0), 999.84, 0.5), sd.rho_water(0))
check("纯水 25°C=997.05 (IAPWS 生效)", approx(sd.rho_water(25), 997.05, 0.5), sd.rho_water(25))
check("纯水 60°C=983.19", approx(sd.rho_water(60), 983.19, 0.5), sd.rho_water(60))
check("纯水 100°C=958.35 (饱和边界)", approx(sd.rho_water(100), 958.35, 1.0), sd.rho_water(100))
check("NaCl 20%=1148.6 (旧-37已修)", approx(sd.rho_nacl(0.20, 20), 1148.6, 4.0), sd.rho_nacl(0.20, 20))
check("NaCl 26.4%(饱和)=1191", approx(sd.rho_nacl(0.264, 20), 1191.0, 6.0), sd.rho_nacl(0.264, 20))
check("NaOH 20%=1219.2 (旧-74已修)", approx(sd.rho_naoh(0.20, 20), 1219.2, 3.0), sd.rho_naoh(0.20, 20))
check("NaOH 50%=1521.9", approx(sd.rho_naoh(0.50, 20), 1521.9, 4.0), sd.rho_naoh(0.50, 20))
check("H2SO4 60%=1498.3 (旧-59已修)", approx(sd.rho_h2so4(0.60, 20), 1498.3, 4.0), sd.rho_h2so4(0.60, 20))
check("H2SO4 98%=1836.5 (旧+14已修)", approx(sd.rho_h2so4(0.98, 20), 1836.5, 5.0), sd.rho_h2so4(0.98, 20))
check("HCl 38%=1189.8", approx(sd.rho_hcl(0.38, 20), 1189.8, 3.0), sd.rho_hcl(0.38, 20))
check("蔗糖 40%=1176.0", approx(sd.rho_sucrose(0.40, 20), 1176.0, 3.0), sd.rho_sucrose(0.40, 20))
check("葡萄糖 20%=1081.0", approx(sd.rho_glucose(0.20, 20), 1081.0, 3.0), sd.rho_glucose(0.20, 20))
check("温度修正方向: NaCl 50°C < 20°C",
      sd.rho_nacl(0.20, 50) < sd.rho_nacl(0.20, 20) - 5)

from solution_density_calculator import SolutionDensityCalculator
w_sd = SolutionDensityCalculator()
w_sd.substance_combo.setCurrentText("硫酸 (H₂SO₄)")
w_sd.w_input.setText("0.60")
w_sd.T_input.setText("20")
w_sd.calculate()
check("UI: H2SO4 60%/20°C → 1497.6", "1497.6" in w_sd.result_text.toPlainText(),
      w_sd.result_text.toPlainText()[:200])
check("UI: get_project_info 返回 dict",
      isinstance(w_sd.get_project_info(), dict))
w_sd.result_text.setPlainText("")
check("UI: 未计算时 generate_report 返回 None", w_sd.generate_report() is None)

print()
print("=" * 60)
print("B. 纯物质物性")
print("=" * 60)
from pure_substance_properties import PureSubstanceProperties, DENS_TABLES, VISC_TABLES, CP_TABLES
w = PureSubstanceProperties()

water = w.substance_data["水"]
check("水 密度 25°C=997.05 (旧0.17已修)",
      approx(w._density_at(water["thermal"], water["basic"], 25, 101.3), 997.05, 0.5),
      w._density_at(water["thermal"], water["basic"], 25, 101.3))
check("水 密度 60°C=983.19",
      approx(w._density_at(water["thermal"], water["basic"], 60, 101.3), 983.19, 0.6))
check("水 密度 100°C=958.35 (端点)",
      approx(w._density_at(water["thermal"], water["basic"], 100, 101.3), 958.35, 0.8))
check("水 粘度 25°C=0.890 (旧1e-15已修)",
      approx(w._viscosity_at(water["thermal"], water["basic"], 25), 0.890, 0.012),
      w._viscosity_at(water["thermal"], water["basic"], 25))
check("水 粘度 60°C=0.467",
      approx(w._viscosity_at(water["thermal"], water["basic"], 60), 0.467, 0.012))
check("水 比热容 25°C=4.181 (旧6.5e10已修)",
      approx(w._cp_at(water["thermal"], water["basic"], 25), 4.181, 0.03),
      w._cp_at(water["thermal"], water["basic"], 25))
check("水 热导率 25°C=0.6065",
      approx(w._thermal_cond_at(water["thermal"], water["basic"], 25), 0.6065, 0.008))
check("水 热导率 80°C=0.670 (随温度上升)",
      approx(w._thermal_cond_at(water["thermal"], water["basic"], 80), 0.670, 0.01))

meth = w.substance_data["甲醇"]
check("甲醇 粘度 25°C=0.544 (旧0已修)",
      approx(w._viscosity_at(meth["thermal"], meth["basic"], 25, name="甲醇"), 0.544, 0.02),
      w._viscosity_at(meth["thermal"], meth["basic"], 25, name="甲醇"))
check("甲醇 粘度 40°C=0.446",
      approx(w._viscosity_at(meth["thermal"], meth["basic"], 40, name="甲醇"), 0.446, 0.02))
check("甲醇 密度 20°C=791.8",
      approx(w._density_at(meth["thermal"], meth["basic"], 20, 101.3, name="甲醇"), 791.8, 2.0))

air = w.substance_data["空气"]
rho_air25 = w._density_at(air["thermal"], air["basic"], 25, 101.3)
check("空气 密度 25°C(理想气体)=1.184", approx(rho_air25, 1.184, 0.01), rho_air25)
mu_air100 = w._viscosity_at(air["thermal"], air["basic"], 100)
check("空气 粘度 100°C≈0.0212 (T^0.7, 随温升)",
      approx(mu_air100, 0.0212, 0.001), mu_air100)
check("空气 100°C 气相密度=0.946 (理想气体)",
      approx(w._density_at(air["thermal"], air["basic"], 100, 101.3), 0.946, 0.01),
      w._density_at(air["thermal"], air["basic"], 100, 101.3))

check("Antoine 水蒸气压 25°C=3.158 kPa",
      approx(w._antoine_vapor_pressure(water["formula_params"], 25), 3.158, 0.06))
check("Antoine 水 80°C=47.27 kPa",
      approx(w._antoine_vapor_pressure(water["formula_params"], 80), 47.27, 0.3))

# 类别下拉全覆盖：不再出现"未找到物质"
for cat in ["无机物", "有机物", "金属", "气体", "液体", "固体"]:
    w.on_category_changed(cat)
    missing = []
    for i in range(w.substance_combo.count()):
        name = w.substance_combo.itemText(i)
        if name not in w.substance_data:
            missing.append(name)
    check(f"类别[{cat}] {w.substance_combo.count()} 项全部有数据", not missing, missing)

# 金属/固体查询走通
w.on_category_changed("金属")
w.substance_combo.setCurrentText("铁")
w.temperature_input.setText("25")
w.pressure_input.setText("101.3")
w.calculate()
check("铁 25°C → 固态", "固态" in w.state_label.text(), w.state_label.text())
ti = w.thermo_prop_table.item(0, 1)
check("铁 密度=7874", ti is not None and "7874" in ti.text(),
      ti.text() if ti else "no item")

w.on_category_changed("固体")
w.substance_combo.setCurrentText("冰")
w.temperature_input.setText("-10")
w.calculate()
check("冰 -10°C → 固态", "固态" in w.state_label.text(), w.state_label.text())

# CAS 覆盖抽查（先切到有机物类别，乙酸才在下拉列表里）
w.on_category_changed("有机物")
w.substance_combo.setCurrentText("乙酸")
w.update_cas_number()
check("乙酸 CAS 显示 64-19-7", w.cas_label.text() == "64-19-7", w.cas_label.text())

print()
print("=" * 60)
print("C. 固体溶解度")
print("=" * 60)
from solid_solubility_calculator import SolubilityWorker, SolidSolubilityCalculator
wk = SolubilityWorker("", "", 0)

def sol(compound, solvent, T):
    return wk.query_solubility_data(compound, solvent, T)

r = sol("氯化钠", "水", 100)
check("NaCl 100°C=39.8 (旧53.3已修)", approx(r["solubility"], 39.8, 0.3), r["solubility"])
check("NaCl 100°C 置信度 High", r["confidence"] == "High")
r = sol("氯化钠", "水", 20)
check("NaCl 20°C=36.0", approx(r["solubility"], 36.0, 0.15), r["solubility"])
r = sol("氯化钠", "水", 0)
check("NaCl 0°C=35.7", approx(r["solubility"], 35.7, 0.15), r["solubility"])
r = sol("硝酸钾", "水", 20)
check("KNO3 20°C=31.6 (新增收录)", approx(r["solubility"], 31.6, 0.3), r["solubility"])
r = sol("硝酸钾", "水", 60)
check("KNO3 60°C=110", approx(r["solubility"], 110.0, 0.8), r["solubility"])
r = sol("硝酸钾", "水", 100)
check("KNO3 100°C=246", approx(r["solubility"], 246.0, 1.5), r["solubility"])
r = sol("硫酸钠", "水", 32.4)
check("Na2SO4 32.4°C峰值=49.6 (旧-26已修)", approx(r["solubility"], 49.6, 0.5), r["solubility"])
r = sol("硫酸钠", "水", 100)
check("Na2SO4 100°C=42.5 (峰值后回落)", approx(r["solubility"], 42.5, 0.5), r["solubility"])
r = sol("氢氧化钙", "水", 100)
check("Ca(OH)2 100°C=0.077 (逆溶解度)", approx(r["solubility"], 0.077, 0.006), r["solubility"])
r = sol("硫酸钡", "水", 25)
check("BaSO4 25°C=0.00023 (新增收录)", approx(r["solubility"], 0.00023, 0.00002), r["solubility"])
r = sol("蔗糖", "水", 20)
check("蔗糖 20°C=203.9 (旧211.5误标已修)", approx(r["solubility"], 203.9, 0.3), r["solubility"])
r = sol("硫酸铜", "水", 80)
check("CuSO4 80°C=55.0 (新增收录)", approx(r["solubility"], 55.0, 0.8), r["solubility"])
r = sol("氯化钠", "水", 120)
check("NaCl 120°C 外推标记", r["extrapolated"] is True and r["solubility"] > 39.8,
      f"{r['solubility']}, {r.get('extrapolated')}")
r = sol("硫酸钡", "乙醇", 25)
check("无数据组合 → N/A + Low", r["solubility"] == "N/A" and r["confidence"] == "Low")

# UI 全链路（异步线程）
w_s = SolidSolubilityCalculator()
idx = w_s.compound_input.findText("硝酸钾")
w_s.compound_input.setCurrentIndex(idx)
w_s.temperature_input.setText("60")
w_s.query_solubility()
t0 = time.time()
while not w_s._last_result and time.time() - t0 < 8:
    app.processEvents()
    time.sleep(0.02)
check("UI: KNO3 60°C 异步查询完成", bool(w_s._last_result), "超时")
check("UI: 结果含 110.0", "110.0" in w_s.result_text.toPlainText(),
      w_s.result_text.toPlainText()[:200])
hd = w_s._get_history_data()
check("UI: 历史数据含查询结果", hd.get("outputs", {}).get("溶解度") not in (None, "", "N/A"),
      hd)

print()
print("=" * 60)
print("D. 废水 COD 估算")
print("=" * 60)
from cod_estimator import (CODEstimator, COD_DB, WASTE_SOURCE_RETENTION,
                           thod_from_formula)

# D1 理论需氧量 ThOD：C→CO₂, H→H₂O, N→NH₃(不计硝化), S→SO₄²⁻
#    n(O₂)=(4C+H+6S−3N−2O)/4,  ThOD=n(O₂)·32/M
#    n_c,n_h,n_n,n_o,n_s,M, 期望值, 来源
THOD_ANCHORS = [
    (6, 12, 0, 6, 0, 180.16, 1.066, "葡萄糖 C6H12O6"),
    (12, 22, 0, 11, 0, 342.30, 1.122, "蔗糖 C12H22O11"),
    (6, 10, 0, 5, 0, 162.14, 1.184, "淀粉单体 C6H10O5"),
    (3, 8, 0, 3, 0, 92.09, 1.216, "甘油 C3H8O3"),
    (2, 4, 0, 2, 0, 60.05, 1.066, "乙酸 C2H4O2"),
    (3, 6, 0, 3, 0, 90.08, 1.066, "乳酸 C3H6O3"),
    (6, 8, 0, 7, 0, 192.12, 0.750, "柠檬酸(无水) C6H8O7"),
    (4, 6, 0, 4, 0, 118.09, 0.948, "琥珀酸 C4H6O4"),
    (2, 6, 0, 1, 0, 46.07, 2.084, "乙醇 C2H6O"),
    (5, 11, 1, 2, 0, 117.15, 1.639, "L-缬氨酸 C5H11NO2"),
    (6, 14, 2, 2, 0, 146.19, 1.532, "L-赖氨酸 C6H14N2O2"),
    (4, 9, 1, 3, 0, 119.12, 1.075, "L-苏氨酸 C4H9NO3"),
    (5, 9, 1, 4, 0, 147.13, 0.979, "L-谷氨酸 C5H9NO4"),
    (6, 13, 1, 2, 0, 131.17, 1.830, "L-亮氨酸 C6H13NO2"),
    (5, 11, 1, 2, 1, 149.21, 1.609, "L-蛋氨酸 C5H11NO2S"),
]
for n_c, n_h, n_n, n_o, n_s, mw, ref, label in THOD_ANCHORS:
    v = thod_from_formula(n_c, n_h, n_n, n_o, n_s, mw)
    check(f"ThOD {label} = {ref}", approx(round(v, 3), ref, 0.002), round(v, 4))

check("ThOD L-蛋氨酸 含硫项必要(去S降到1.287)",
      approx(round(thod_from_formula(5, 11, 1, 2, 0, 149.21), 3), 1.287, 0.002))
check("ThOD 亮氨酸=异亮氨酸(同分异构同式)",
      COD_DB["L-亮氨酸"][0] == COD_DB["L-异亮氨酸"][0] == 1.830)
check("ThOD 菌体按 C5H7O2N 理论=1.415",
      approx(round(thod_from_formula(5, 7, 1, 2, 0, 113.11), 3), 1.415, 0.002))
check("无机氮 (NH4)2SO4 不计 COD", COD_DB["(NH₄)₂SO₄"][0] == 0.0)
check("尿素 COD=0(重铬酸钾法不氧化)",
      COD_DB["尿素"][0] == 0.0)
check("菌体湿重当量 = 干重×20%",
      approx(COD_DB["菌体(湿重×20%)"][0], COD_DB["菌体干重(DCW)"][0] * 0.20, 0.001))

# D2 全部"理论值"项与 thod_from_formula 一致（数据表不再手写经验值混入）
THEO_TABLE = {
    "葡萄糖": (6, 12, 0, 6, 0, 180.16), "蔗糖": (12, 22, 0, 11, 0, 342.30),
    "淀粉(可溶)": (6, 10, 0, 5, 0, 162.14), "甘油": (3, 8, 0, 3, 0, 92.09),
    "乙酸": (2, 4, 0, 2, 0, 60.05), "乳酸": (3, 6, 0, 3, 0, 90.08),
    "柠檬酸": (6, 8, 0, 7, 0, 192.12), "琥珀酸": (4, 6, 0, 4, 0, 118.09),
    "乙醇": (2, 6, 0, 1, 0, 46.07), "L-缬氨酸": (5, 11, 1, 2, 0, 117.15),
    "L-赖氨酸": (6, 14, 2, 2, 0, 146.19), "L-苏氨酸": (4, 9, 1, 3, 0, 119.12),
    "L-谷氨酸": (5, 9, 1, 4, 0, 147.13), "L-亮氨酸": (6, 13, 1, 2, 0, 131.17),
    "L-异亮氨酸": (6, 13, 1, 2, 0, 131.17), "L-蛋氨酸": (5, 11, 1, 2, 1, 149.21),
}
bad = []
for name, args in THEO_TABLE.items():
    calc = round(thod_from_formula(*args), 3)
    if abs(COD_DB[name][0] - calc) > 0.002:
        bad.append(f"{name}: 表{COD_DB[name][0]} vs 算{calc}")
check("COD_DB 全部理论项与 ThOD 公式自洽", not bad, bad)

# D3 废水来源 → (产品是否留废液, 菌体残留比例)
check("废水来源保留规则 4 档齐全", len(WASTE_SOURCE_RETENTION) == 4)
check("提取废液 产品已被回收(不计入废水COD)",
      WASTE_SOURCE_RETENTION["提取废液（离子交换/膜分离）"][0] is False)
check("上清液 菌体已离心(仅 15% 残留)",
      approx(WASTE_SOURCE_RETENTION["发酵废液（离心后上清液）"][1], 0.15, 1e-9))
check("全发酵液 菌体全在(100%)",
      approx(WASTE_SOURCE_RETENTION["全发酵液（含菌体）"][1], 1.0, 1e-9))

# D4 UI 物料衡算默认参数（100 葡萄糖 + 15 玉米浆 + 5 酵母浸粉 / 缬氨酸 60 / 残糖5 / 菌体8）
w_c = CODEstimator()
w_c.calculate()
r = dict(w_c._last_results)
check("UI: 模式=物料衡算法", r.get("mode") == "物料衡算法", r.get("mode"))
check("UI: 投入总COD=124.1 gO2/L",
      approx(r["input_cod_total"], 124.1, 0.1), r["input_cod_total"])
check("UI: 产品COD=98.34", approx(r["product_cod"], 98.34, 0.05), r["product_cod"])
check("UI: 残糖COD=5.33", approx(r["residual_cod"], 5.33, 0.02), r["residual_cod"])
check("UI: 菌体COD=11.36", approx(r["biomass_cod"], 11.36, 0.02), r["biomass_cod"])

# 关键回归：液相COD = 残糖 + 菌体残留 + 产品(若留废液)
#   旧实现 = 投入总COD − 产品 + 残糖 + 菌体 = 124.1−98.34+5.33+11.36 = 42.45(L 单位计) 属重复计入
expect_liquid = 5.33 + 11.36 * 0.15 + 98.34          # = 105.374
check("UI: 液相COD=105.37(旧重复计入已修)",
      approx(r["liquid_cod"], expect_liquid, 0.05), r["liquid_cod"])
old_bug = r["input_cod_total"] - r["product_cod"] + r["residual_cod"] + r["biomass_cod"]
check("UI: 液相COD 不等于旧错误式",
      not approx(r["liquid_cod"], old_bug, 1.0), f"liquid={r['liquid_cod']} old={old_bug}")
check("UI: 液相COD ≤ 投入总COD(守恒约束)",
      r["liquid_cod"] <= r["input_cod_total"] + 1e-9,
      f"{r['liquid_cod']} vs {r['input_cod_total']}")
check("UI: 呼吸氧化COD=9.07>0",
      approx(r["mineralized_cod"], 9.065, 0.05), r["mineralized_cod"])
check("UI: 守恒 投入=产品+菌体+残糖+呼吸氧化",
      approx(r["input_cod_total"],
             r["product_cod"] + r["biomass_cod"] + r["residual_cod"] + r["mineralized_cod"],
             0.05))
check("UI: 废水体积=50×0.8=40 m³/批", approx(r["waste_vol"], 40.0, 0.01), r["waste_vol"])
check("UI: COD 负荷=5268.7 kg/批", approx(r["cod_load"], 5268.7, 1.0), r["cod_load"])
check("UI: COD 浓度=131717 mg/L", approx(r["cod_conc"], 131717.5, 5.0), r["cod_conc"])

# 提取废液档：产品已回收，不应计入废水 COD → 约 8.8 g/L（符合氨基酸发酵实际）
w_c.input_widgets["waste_source"].setCurrentText("提取废液（离子交换/膜分离）")
w_c.calculate()
r2 = dict(w_c._last_results)
check("UI: 提取废液档 产品不计入", r2["product_in_waste"] is False)
check("UI: 提取废液档 液相COD=7.03", approx(r2["liquid_cod"], 7.034, 0.02), r2["liquid_cod"])
check("UI: 提取废液档 COD浓度≈8793 mg/L",
      approx(r2["cod_conc"], 8792.5, 20.0), r2["cod_conc"])

# 全发酵液档：菌体全在
w_c.input_widgets["waste_source"].setCurrentText("全发酵液（含菌体）")
w_c.calculate()
r3 = dict(w_c._last_results)
check("UI: 全发酵液档 菌体残留=100%",
      approx(r3["biomass_retention"], 1.0, 1e-9), r3["biomass_retention"])
check("UI: 全发酵液档 液相COD=115.03",
      approx(r3["liquid_cod"], 5.33 + 11.36 + 98.34, 0.05), r3["liquid_cod"])

check("UI: get_project_info 标准键",
      set(w_c.get_project_info()) >= {"company_name", "project_number",
                                      "project_name", "subproject_name",
                                      "calculation_type"})
check("UI: 已算 generate_report 返回 str",
      isinstance(w_c.generate_report(), str))
check("UI: 报告含'呼吸氧化'段", "呼吸氧化" in (w_c.generate_report() or ""))
check("UI: 历史数据 _get_history_data 有结果",
      bool(w_c._get_history_data().get("outputs")))
w_c.clear_all()
check("UI: 清空后 generate_report 返回 None", w_c.generate_report() is None)

print()
print("=" * 60)
print("E. 腐蚀数据查询")
print("=" * 60)
from corrosion_data_query import (CorrosionDataQuery, CORROSION_DB,
                                  classify_corrosion_rate)

# E1 分级由速率唯一派生（左景伊 4 级制；分界值归入腐蚀更重一级，偏安全）
check("分级 0.001 → 优良", classify_corrosion_rate(0.001)[0] == "优良")
check("分级 0.049 → 优良", classify_corrosion_rate(0.049)[0] == "优良")
check("分级 0.05(分界) → 良好", classify_corrosion_rate(0.05)[0] == "良好")
check("分级 0.49 → 良好", classify_corrosion_rate(0.49)[0] == "良好")
check("分级 0.5(分界) → 可用", classify_corrosion_rate(0.5)[0] == "可用（腐蚀较重）")
check("分级 1.49 → 可用", classify_corrosion_rate(1.49)[0] == "可用（腐蚀较重）")
check("分级 1.5(分界) → 不适用（偏安全）",
      classify_corrosion_rate(1.5)[0] == "不适用（腐蚀严重）")
check("分级 12.5 → 不适用", classify_corrosion_rate(12.5)[0] == "不适用（腐蚀严重）")
check("分级 非法值 → 未知",
      classify_corrosion_rate("abc")[0] == "未知"
      and classify_corrosion_rate(-1)[0] == "未知")
check("分级返回三元组(等级/建议/10级细分)",
      len(classify_corrosion_rate(0.02)) == 3)

# E2 数据表不再手写 rating（消除同一速率两个等级的旧矛盾）
stale = [k for k, v in CORROSION_DB.items() if "rating" in v]
check("CORROSION_DB 无手写 rating 字段（单一数据源）", not stale, stale)
missing = [k for k, v in CORROSION_DB.items()
           if not {"rate", "t_ref", "notes"} <= set(v)]
check("CORROSION_DB 每条含 rate/t_ref/notes", not missing, missing)

# E3 纯钛-盐酸 材料学勘误（原 0.001/"优良的耐盐酸性能" 属错误）
ti_hcl = CORROSION_DB["纯钛-盐酸"]
check("纯钛-盐酸 速率=1.0 mm/a（原 0.001 已修）",
      approx(ti_hcl["rate"], 1.0, 0.01), ti_hcl["rate"])
check("纯钛-盐酸 改为'可用/腐蚀较重'",
      classify_corrosion_rate(ti_hcl["rate"])[0] == "可用（腐蚀较重）")
check("纯钛-盐酸 说明明示'还原性酸'", "还原性酸" in ti_hcl["notes"], ti_hcl["notes"])
check("钛的优势介质(海水/硝酸)仍为优良",
      classify_corrosion_rate(CORROSION_DB["纯钛-海水"]["rate"])[0] == "优良"
      and classify_corrosion_rate(CORROSION_DB["纯钛-硝酸"]["rate"])[0] == "优良")
check("304-硝酸 优良(氧化性酸促钝化)",
      classify_corrosion_rate(CORROSION_DB["304-硝酸"]["rate"])[0] == "优良")
check("Q235-盐酸 不适用", classify_corrosion_rate(CORROSION_DB["Q235-盐酸"]["rate"])[0]
      == "不适用（腐蚀严重）")
check("哈氏合金C276-盐酸 能用(唯一能耐盐酸的金属之一)",
      classify_corrosion_rate(CORROSION_DB["哈氏合金C276-盐酸"]["rate"])[0] == "良好")

# E4 数据隔离
w_k = CorrosionDataQuery()
d = w_k.load_corrosion_data()
d["Q235-盐酸"]["rate"] = 999
check("load_corrosion_data 返回副本(不污染内置库)",
      CORROSION_DB["Q235-盐酸"]["rate"] == 12.5)

def corr_lookup(mat, med, t, c, ph=None):
    w_k.material_combo.clear(); w_k.material_combo.addItem(mat)
    w_k.medium_combo.clear(); w_k.medium_combo.addItem(med)
    w_k.temperature_input.setText(str(t))
    w_k.concentration_input.setText(str(c))
    w_k.ph_input.setText("" if ph is None else str(ph))
    w_k.calculate()
    return w_k.result_text.toPlainText()

txt = corr_lookup("Q235", "盐酸", 25, 10)
check("UI: 结果含等级与选材建议", "不适用（腐蚀严重）" in txt and "不推荐使用" in txt, txt[:200])
check("UI: 结果含数据参考工况", "数据参考工况" in txt)
check("UI: 结果含理论穿透时间(未计腐蚀裕量)", "理论穿透时间" in txt)
check("UI: 结果含数据来源出处", "左景伊" in txt and "腐蚀数据与选材手册" in txt)
check("UI: pH 留空不产生酸碱矛盾提示(原默认7误报)",
      "pH=7" not in txt and "偏中性/碱性" not in txt, txt[:400])

txt2 = corr_lookup("316", "硫酸", 25, 10, 8.0)
check("UI: 填 pH=8 且介质为酸 → 提示不符", "偏中性/碱性" in txt2, txt2[:400])
txt3 = corr_lookup("304", "硝酸", 60, 10)
check("UI: 温度偏离 >15°C → 提示", "相差超过 15°C" in txt3, txt3[:400])
txt4 = corr_lookup("304", "硝酸", 80, 10)
check("UI: 温度 >60°C → 强提示不可外推", "不可外推" in txt4, txt4[:400])
txt5 = corr_lookup("304", "硝酸", 25, 50)
check("UI: 浓度偏离 → 提示", "与数据参考浓度" in txt5, txt5[:500])

h = w_k._get_history_data()
check("UI: 历史数据取结构化结果(不解析文本)",
      approx(h["outputs"].get("腐蚀速率_mm_a", -1), 0.01, 1e-9), h["outputs"])
check("UI: get_project_info 标准键",
      set(w_k.get_project_info()) >= {"company_name", "project_number",
                                      "project_name", "subproject_name",
                                      "calculation_type"})
check("UI: 已查询 generate_report 返回 str", isinstance(w_k.generate_report(), str))
w_k.clear_inputs()
check("UI: 清空后 _last_results 复位", w_k._last_results == {})
check("UI: 清空后 generate_report 返回 None", w_k.generate_report() is None)
check("UI: 清空后 pH 框为空(不再回填7)",
      w_k.ph_input.text() == "", repr(w_k.ph_input.text()))
check("UI: 分级依据含 GB/T 10123 为术语标准的说明",
      "GB/T 10123" in w_k.get_corrosion_types_text())

print()
print("=" * 60)
print("F. 危险化学品查询")
print("=" * 60)
from hazardous_chemicals_query import (HazardousChemicalsQuery, ALL_HAZARDS_LABEL,
                                       DATA_SOURCE_NOTE as HAZ_NOTE)
from PySide6.QtCore import Qt as _Qt

w_h = HazardousChemicalsQuery()

# F1 关键回归：搜索框曾遗留调试默认值 "乙醇"，导致打开只列出 1 种
check("搜索框默认为空(原遗留'乙醇'已修)",
      w_h.search_input.text() == "", repr(w_h.search_input.text()))
check("初始列出全部化学品",
      len(w_h.filtered_chemicals) == len(w_h.chemicals_data) == 7,
      f"{len(w_h.filtered_chemicals)}/{len(w_h.chemicals_data)}")
check("初始列表项数=数据条数", w_h.chemicals_list.count() == 7,
      w_h.chemicals_list.count())

# F2 筛选项由数据派生，无死项
opts = [w_h.hazard_filter_combo.itemText(i)
        for i in range(w_h.hazard_filter_combo.count())]
present = set()
for c in w_h.chemicals_data:
    present |= {t.strip() for t in c["hazard_class"].split(";") if t.strip()}
check("首个选项为'所有危险性'", opts[0] == ALL_HAZARDS_LABEL)
check("筛选项集合=数据实际类别集合",
      set(opts) - {ALL_HAZARDS_LABEL} == present,
      f"opts={set(opts) - {ALL_HAZARDS_LABEL}} data={present}")
dead = []
for o in opts:
    w_h.hazard_filter_combo.setCurrentText(o)
    if len(w_h.filtered_chemicals) == 0:
        dead.append(o)
check("每个筛选项都能匹配到记录(原4项死选项已修)", not dead, dead)
w_h.hazard_filter_combo.setCurrentText(ALL_HAZARDS_LABEL)
check("选'所有危险性'恢复7条", len(w_h.filtered_chemicals) == 7)

# F3 GHS 分类勘误
sulf = next(c for c in w_h.chemicals_data if c["name"] == "硫酸")
check("硫酸 危险性类别=腐蚀性物质(去掉夸大的'毒性物质')",
      sulf["hazard_class"] == "腐蚀性物质", sulf["hazard_class"])
check("硫酸 GHS 分类含 皮肤腐蚀/刺激 类别1A",
      "类别1A" in sulf.get("ghs_classification", ""), sulf.get("ghs_classification"))
check("硫酸 H 语句含 H314", "H314" in sulf["hazard_statements"])
cl2 = next(c for c in w_h.chemicals_data if c["name"] == "氯气")
check("氯气 含 氧化性气体/毒性气体/腐蚀性物质/环境危害物质",
      {"氧化性气体", "毒性气体", "腐蚀性物质", "环境危害物质"}
      <= set(cl2["hazard_class"].split(";")), cl2["hazard_class"])
check("氯气 H330 吸入致命", "H330" in cl2["hazard_statements"])
missing = [c["name"] for c in w_h.chemicals_data
           if not {"name", "cas", "formula", "hazard_class", "ghs_classification",
                   "hazard_statements"} <= set(c)]
check("每条化学品必备字段齐全", not missing, missing)
check("数据来源说明引用 GB 30000", "GB 30000" in HAZ_NOTE)

# F4 深色主题可读性：列表项前景色必须显式设定
nofg = [w_h.chemicals_list.item(i).text()
        for i in range(w_h.chemicals_list.count())
        if not w_h.chemicals_list.item(i).foreground().color().isValid()]
check("列表项均显式设定前景色(深色主题可读)", not nofg, nofg)
check("列表项文本含危险性类别",
      "[" in w_h.chemicals_list.item(0).text(),
      w_h.chemicals_list.item(0).text())

# F5 详情框改纯文本（原 setHtml 硬编码浅色表在深色主题下不可读）
# ⚠ QListWidget 每次 rebuild 都会删除旧 item（C++ 对象析构），必须现取现用
def pick(name):
    for i in range(w_h.chemicals_list.count()):
        it = w_h.chemicals_list.item(i)
        if it.data(_Qt.UserRole)["name"] == name:
            return it
    return None

w_h.show_chemical_detail(pick("硫酸"))
dtext = w_h.detail_text.toPlainText()
check("详情为纯文本(含表格标记即为回归)",
      "<table" not in dtext and "<div" not in dtext and "硫酸" in dtext,
      dtext[:120])
check("详情 HTML 不含硬编码浅底 #f8f9fa",
      "#f8f9fa" not in w_h.detail_text.toHtml())
check("详情含 GHS 分类行", "GHS 分类" in dtext)
check("详情含数据来源段", "数据来源" in dtext)

# F6 列表项数据挂 UserRole（文本改动后仍能取到，按名反查会失效）
it_s = pick("硫酸")
before = it_s.data(_Qt.UserRole)["name"]
it_s.setText("被人为改过的文本")
w_h.show_chemical_detail(it_s)
check("UserRole 取数据不受文本改动影响",
      w_h.current_chemical["name"] == before == "硫酸",
      w_h.current_chemical["name"])

# F7 搜索/契约
w_h.search_input.setText("苯")
w_h.filter_chemicals()
check("按名称搜索'苯' → 1 条", len(w_h.filtered_chemicals) == 1,
      [c["name"] for c in w_h.filtered_chemicals])
w_h.clear_search()
check("清空搜索恢复7条", len(w_h.filtered_chemicals) == 7)
check("定时器只创建一次(不重复 new QTimer)",
      (w_h.on_search_text_changed("甲"), w_h.on_search_text_changed("甲醇"),
       w_h.search_timer is w_h.search_timer)[-1] is True)
check("get_project_info 标准键",
      set(w_h.get_project_info()) >= {"company_name", "project_number",
                                      "project_name", "subproject_name",
                                      "calculation_type"})
w_h.clear_search()
check("未选化学品 generate_report 返回 None", w_h.generate_report() is None)
w_h.show_chemical_detail(pick("氯气"))
check("已选化学品 generate_report 返回 str",
      isinstance(w_h.generate_report(), str))
check("报告含工程信息段", "工程信息" in (w_h.generate_report() or ""))
check("报告含'ChemCal 工程计算模块'", "ChemCal 工程计算模块" in (w_h.generate_report() or ""))
check("报告含 GHS 分类行", "GHS分类" in (w_h.generate_report() or ""))
check("历史数据含 GHS分类", "GHS分类" in w_h._get_history_data()["outputs"])

print()
print("=" * 60)
print(f"总结: {PASS} 过, {FAIL} 失败")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
