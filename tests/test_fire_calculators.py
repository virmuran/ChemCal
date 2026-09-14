# -*- coding: utf-8 -*-
"""
消防类计算器回归测试（GB 50974-2014）

运行方式（纯 Python，无需 pytest）:
    .venv/Scripts/python.exe tests/test_fire_calculators.py
"""
import os
import sys
import math

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# DataManager 隔离到临时文件，避免污染真实数据
_tmpdir = os.environ.setdefault("CHEMCAL_DATA_DIR", os.path.join(os.path.dirname(__file__), "_tmp_fire"))
os.makedirs(_tmpdir, exist_ok=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "modules", "chemical_calculations", "calculators"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "modules", "chemical_calculations"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")


def approx(a, b, tol=1e-3):
    return abs(a - b) <= tol * max(1.0, abs(b))


# ══════════════════ 1. 消防水池容积 ══════════════════
print("\n【消防水池容积计算器 FireWaterTankCalculator】")
import fire_water_tank_calculator as fwt

# 表3.3.2 室外流量查档锚点
look = fwt._tier_lookup
check("厂房甲乙 V=10000 → 25 L/s（修复前为30错档/20偏不安全）", look(fwt.OUTDOOR_FLOW_TIERS["厂房（甲/乙类）"], 10000) == 25)
check("厂房甲乙 V=500 → 15 L/s", look(fwt.OUTDOOR_FLOW_TIERS["厂房（甲/乙类）"], 500) == 15)
check("厂房甲乙 V=60000 → 35 L/s", look(fwt.OUTDOOR_FLOW_TIERS["厂房（甲/乙类）"], 60000) == 35)
check("厂房丙 V=10000 → 25 L/s", look(fwt.OUTDOOR_FLOW_TIERS["厂房（丙类）"], 10000) == 25)
check("厂房丙 V=60000 → 40 L/s", look(fwt.OUTDOOR_FLOW_TIERS["厂房（丙类）"], 60000) == 40)
check("仓库丙 V=60000 → 45 L/s", look(fwt.OUTDOOR_FLOW_TIERS["仓库（丙类）"], 60000) == 45)
check("仓库丙 V=10000 → 25 L/s", look(fwt.OUTDOOR_FLOW_TIERS["仓库（丙类）"], 10000) == 25)
check("仓库甲乙 V=5000 → None（规范未规定）", look(fwt.OUTDOOR_FLOW_TIERS["仓库（甲/乙类）"], 5000) is None)
check("公共单层多层 V=10000 → 25 L/s", look(fwt.OUTDOOR_FLOW_TIERS["民用建筑（公共，单层及多层）"], 10000) == 25)
check("公共单层多层 V=60000 → 40 L/s", look(fwt.OUTDOOR_FLOW_TIERS["民用建筑（公共，单层及多层）"], 60000) == 40)

# 表3.5.2 室内流量查档锚点（修复前丙类 V≤5000 给 10，规范按高度 20）
ti = fwt.INDOOR_FLOW_TIERS
check("丙类厂房 h=12 → 20 L/s（修复前10，偏不安全）", look(ti["厂房（丙类）"]["tiers"], 12) == 20)
check("丙类厂房 h=30 → 30 L/s", look(ti["厂房（丙类）"]["tiers"], 30) == 30)
check("丙类厂房 h=60 → 40 L/s", look(ti["厂房（丙类）"]["tiers"], 60) == 40)
check("乙/丁/戊厂房 h=30 → 25 L/s（修复前一律10）", look(ti["厂房（甲/乙/丁/戊类）"]["tiers"], 30) == 25)
check("丙类仓库 h=30 → 40 L/s（修复前一律15）", look(ti["仓库（丙类）"]["tiers"], 30) == 40)
check("高层民用 h=40 → 30 L/s", look(ti["民用建筑（高层）"]["tiers"], 40) == 30)

# 整机手算案例：丙类厂房 V=10000, h=12, 喷淋 30L/s×1h, 余量1.1, 类别=甲/乙/丙类厂房(3h)
w = fwt.FireWaterTankCalculator()
w.inputs["building_type"].setCurrentText("厂房（丙类）")
w.inputs["indoor_type"].setCurrentText("厂房（丙类）")
w.inputs["building_volume"].setText("10000")
w.inputs["building_height"].setText("12")
# 联动应把火灾类别设为 甲/乙/丙类厂房 (3h)
check("建筑类型→火灾类别自动联动(3h)", w.inputs["fire_category"].currentText() == "甲/乙/丙类厂房")
w.calculate()
txt = w.result_text.toPlainText()
# 手算: 室外 25×3×3.6=270; 室内 20×3×3.6=216; 喷淋 30×1×3.6=108; 合计 594; ×1.1=653.4
check("室外用水 270 m³", "270" in txt)
check("室内用水 216 m³", "216" in txt)
check("喷淋用水 108 m³", "108" in txt)
check("水池有效容积 653 m³ (手算653.4)", "653" in txt)
check("水枪数提示 4 支", "4支水枪" in txt)

# 居民楼案例: 住宅 V=8000 → 室外15, 室内多层15, 2h, 无喷淋
w.inputs["building_type"].setCurrentText("民用建筑（住宅）")
w.inputs["indoor_type"].setCurrentText("民用建筑（多层）")
w.inputs["fire_category"].setCurrentText("民用建筑")
w.inputs["sprinkler_flow"].setText("0")
w.calculate()
# 手算: (15+15)×2×3.6 = 216; ×1.1 = 237.6 → 显示 238
check("住宅案例 水池容积 238 m³ (手算237.6)", "238" in w.result_text.toPlainText())
w.inputs["sprinkler_flow"].setText("30")

# ══════════════════ 2. 消火栓计算 ══════════════════
print("\n【消火栓计算器】")
import fire_hydrant_calculator as fh

w2 = fh.消火栓计算()

# 总流量: 规范逻辑 N×q 且≥表3.5.2最小值（修复前乘1.3/1.5等编造系数）
check("民用 2枪×5 = 10 L/s", w2.calculate_total_flow(2, 5, "民用建筑", "中危险级Ⅰ级") == 10)
check("高层 4枪×5 = 20 L/s（修复前 20×1.3=26）", w2.calculate_total_flow(4, 5, "高层建筑", "中危险级Ⅱ级") == 20)
check("高层 2枪×5 → 规范最小 20 L/s", w2.calculate_total_flow(2, 5, "高层建筑", "中危险级Ⅰ级") == 20)
check("超高层 最小 30 L/s", w2.calculate_total_flow(2, 5, "超高层建筑", "中危险级Ⅰ级") == 30)

# 水泵扬程: H = 标高差 + 栓口压力水柱 + 管损（修复前 = 高度+15，漏掉 0.35MPa≈35.7m）
pr = w2.calculate_pipe_parameters(20, 150)
hf = pr["head_loss"]
pm = w2.calculate_pump_parameters(80, 20, 24, 0.35, hf)
h_p = 0.35e6 / (1000 * 9.81)  # = 35.68 m
check("栓口压力水柱 35.68 m", approx(pm["pressure_head"], h_p, 1e-4), f'{pm["pressure_head"]:.2f}')
check("所需扬程 = 24 + 35.68 + 管损", approx(pm["required_head"], 24 + h_p + hf, 1e-4),
      f'{pm["required_head"]:.2f}')
check("修复前扬程 39m 被低估 ≈21m", pm["required_head"] > 55)

# 高位水箱（表5.2.1）
t1, s1, d1 = w2.calculate_tank_capacity(20, "高层建筑", 50)
check("高层 h=50 → 水箱 ≥36 m³（修复前按延续时间算）", t1 == 36)
t2, s2, d2 = w2.calculate_tank_capacity(20, "高层建筑", 120)
check("高层 h>100 → 水箱 ≥50 m³", t2 == 50)
t3, s3, d3 = w2.calculate_tank_capacity(20, "超高层建筑", 160)
check("超高层 h>150 → 水箱 ≥100 m³", t3 == 100)
t4, s4, d4 = w2.calculate_tank_capacity(10, "工业建筑", 12)
check("工业建筑 室内10L/s → 水箱 ≥12 m³", t4 == 12)
t5, s5, d5 = w2.calculate_tank_capacity(30, "工业建筑", 12)
check("工业建筑 室内30L/s → 水箱 ≥18 m³", t5 == 18)
# 消防储水量: 20 L/s × 2h × 3.6 = 144
check("高层储水量 144 m³ (20L/s×2h)", approx(s2, 144), f"{s2:.0f}")

# 整机运行（默认输入应能直接出结果且不崩）
w2.auto_calc_check.setChecked(False)
w2.building_type_combo.setCurrentText("民用建筑")
w2.building_height_input.setValue(24)
w2.calculate()
txt2 = w2.result_text.toPlainText()
check("默认输入一键计算出结果", "室内消火栓设计流量" in txt2 and "高位消防水箱" in txt2)
check("结果含扬程分解式", "栓口压力" in txt2)

# 二次计算（历史记录钩子）
hd = w2._get_history_data()
check("历史记录含新字段", "高位水箱最小容积_m3" in hd["outputs"] and "水泵所需扬程_m" in hd["outputs"])

# ══════════════════ 汇总 ══════════════════
fails = [n for n, ok, _ in RESULTS if not ok]
print("\n" + "=" * 50)
print(f"共 {len(RESULTS)} 项，通过 {len(RESULTS) - len(fails)}，失败 {len(fails)}")
for n in fails:
    print(f"  FAIL: {n}")
sys.exit(1 if fails else 0)
