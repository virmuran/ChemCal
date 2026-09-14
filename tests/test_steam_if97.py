# -*- coding: utf-8 -*-
"""
IAPWS-IF97 水蒸气物性回归测试（无外部依赖，直接运行即可）
==========================================================

运行方式（项目根目录）:
    .venv/Scripts/python.exe tests/test_steam_if97.py

核对方法（2026-09-10 全量标准核对）:
    第1层  对照 IAPWS-IF97 官方发布文件验证表（Region 1 Table 5 / Region 2 Table 15）
    第2层  与独立参考实现 iapws v1.5.5 全网格对比（过冷水 63 点、过热蒸汽 88 点、
           饱和线 13 点，最大偏差: h ≤0.005%, v ≤0.008%, h_fg ≤0.04%）
    第3层  计算器 UI 端到端
    本文件固化第 1、2 层的代表性数值作为永久回归基准。

数据来源标注:
    [S1] IAPWS, "Revised Release on the IAPWS Industrial Formulation 1997
         for the Thermodynamic Properties of Water and Steam" (2007/2012)
    [S2] iapws v1.5.5 独立参考实现（逐位比对确认）
    [P]  项目实现 modules/chemical_calculations/steam_iapws.py

历史 bug 备忘（本测试防止回归）:
    2026-09-10  _region_select 在 T>623.15K 时误用 Ps_623 判区域，
                700K/30MPa 等高压过热状态被区域1公式外推出 3500% 偏差。
                现按 IF97 Eq.5 B23 边界判断，区域3 显式报错。
"""
import os
import sys
import math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MP = os.path.join(ROOT, 'modules', 'chemical_calculations')
for p in [ROOT, MP, os.path.join(ROOT, 'modules', 'chemical_calculations', 'calculators')]:
    if p not in sys.path:
        sys.path.insert(0, p)

import steam_iapws as si
from common_constants import get_steam_props

_results = []


def check(name, got, expect, tol_rel):
    if expect == 0:
        ok = abs(got) < tol_rel
    else:
        ok = abs(got - expect) / abs(expect) <= tol_rel
    _results.append((name, ok))
    status = 'PASS' if ok else 'FAIL'
    print(f"  [{status}] {name}: got={got:.6g} expect={expect:.6g}")
    return ok


def section(title):
    print(f"\n── {title} " + "─" * max(0, 50 - len(title)))


# ══════════════════════════════════════════════════════════════════
section("1. Region 1 过冷水 — 官方验证值 [S1 Table 5]")
# ══════════════════════════════════════════════════════════════════
r1 = [
    # (T[K], p[MPa], v[m³/kg], h[kJ/kg], s[kJ/(kg·K)])
    (300.0, 3.0,  0.100215168e-02, 0.115331273e03, 0.392294792e00),
    (300.0, 80.0, 0.971180894e-03, 0.184142828e03, 0.368563852e00),
    (500.0, 3.0,  0.120241800e-02, 0.975542239e03, 0.258041912e01),
]
for T, p, v_e, h_e, s_e in r1:
    d = si.steam_properties(P_MPa=p, T_C=T - 273.15)
    check(f"R1 {T}K/{p}MPa v", d['v'], v_e, 1e-5)
    check(f"R1 {T}K/{p}MPa h", d['h'], h_e, 5e-4)
    check(f"R1 {T}K/{p}MPa s", d['s'], s_e, 5e-4)

# ══════════════════════════════════════════════════════════════════
section("2. Region 2 过热蒸汽 — 官方验证值 [S1 Table 15]")
# ══════════════════════════════════════════════════════════════════
r2 = [
    (300.0, 0.0035, 0.394913866e+02, 0.254991145e+04, 0.852238967e+01),
    (700.0, 0.0035, 0.923021493e+02, 0.333568375e+04, 0.101749996e+02),
    (700.0, 30.0,   0.542946619e-02, 0.263149474e+04, 0.517540298e+01),
]
for T, p, v_e, h_e, s_e in r2:
    d = si.steam_properties(P_MPa=p, T_C=T - 273.15)
    check(f"R2 {T}K/{p}MPa v", d['v'], v_e, 1e-4)
    check(f"R2 {T}K/{p}MPa h", d['h'], h_e, 5e-4)
    check(f"R2 {T}K/{p}MPa s", d['s'], s_e, 5e-4)

# ══════════════════════════════════════════════════════════════════
section("3. 饱和线锚点 [S1/S2]")
# ══════════════════════════════════════════════════════════════════
check("Tsat(0.1 MPa)", si.saturation_temperature(0.1), 99.605919, 1e-4)
check("Tsat(1.0 MPa)", si.saturation_temperature(1.0), 179.885835, 1e-4)
check("ps(100°C) [IF97/ITS-90]", si.saturation_pressure(100.0), 0.10141797792131, 1e-6)
# 物理锚点（历史摄氏度定义）偏差 <0.1%，工程可忽略
check("ps(100°C) vs 1atm <0.1%", si.saturation_pressure(100.0) - 0.101325, 0.0, 9.3e-5)

# ══════════════════════════════════════════════════════════════════
section("4. B23 边界线自检 [S1 Eq.5]")
# ══════════════════════════════════════════════════════════════════
check("p_B23(623.15K) = Ps_623", si._p_b23(623.15), si.Ps_623, 1e-9)

# ══════════════════════════════════════════════════════════════════
section("5. 区域3 显式报错（2026-09-10 修复的静默外推 bug）")
# ══════════════════════════════════════════════════════════════════
for args in [(20.0, 375.0), (25.0, 380.0)]:
    try:
        si.steam_properties(*args)
        _results.append((f"区域3报错 {args}", False))
        print(f"  [FAIL] 区域3报错 {args}: 未报错")
    except ValueError:
        _results.append((f"区域3报错 {args}", True))
        print(f"  [PASS] 区域3报错 {args}")
try:
    si.saturation_properties(P_MPa=18.0)
    _results.append(("饱和18MPa报错", False))
    print("  [FAIL] 饱和18MPa报错: 未报错")
except ValueError:
    _results.append(("饱和18MPa报错", True))
    print("  [PASS] 饱和18MPa报错")

# ══════════════════════════════════════════════════════════════════
section("6. 湿蒸汽与 PH 逆推 [S2 参考值]")
# ══════════════════════════════════════════════════════════════════
ws = si.wet_steam_properties(P_MPa=1.0, dryness=0.95)
check("湿蒸汽 h(x=0.95, 1MPa)", ws['h'], 2676.40, 5e-4)
ph = si.properties_from_ph(1.0, 2676.40)
check("PH逆推干度", ph['dryness'], 0.95, 2e-3)

# ══════════════════════════════════════════════════════════════════
section("7. get_steam_props 标准接口（表压入参，计算器共用）")
# ══════════════════════════════════════════════════════════════════
# 校验基准: 表压 0.0/0.3/0.5/0.8/1.0 MPa(g) [P 项目历史校验基准, S2 复核]
steam_anchors = [
    # (表压 MPa(g), sat_temp °C, h_fg kJ/kg)  绝压 = 表压 + 0.101325
    (0.0, 99.974, 2256.6),   # 0.101325 MPa(abs)
    (0.3, 143.732, 2133.3),  # 0.401325 MPa(abs)
    (0.5, 158.919, 2085.9),  # 0.601325
    (0.8, 175.420, 2030.8),  # 0.901325
    (1.0, 184.123, 2000.0),  # 1.101325
]
for pg, t_e, r_e in steam_anchors:
    d = get_steam_props(pg)
    check(f"get_steam_props({pg}MPa(g)) sat_temp", d['sat_temp'], t_e, 5e-4)
    check(f"get_steam_props({pg}MPa(g)) h_fg", d['h_fg'], r_e, 5e-4)
    ok_method = d['method'] == 'IAPWS-IF97'
    _results.append((f"{pg}MPa(g) method=IF97", ok_method))
    print(f"  [{'PASS' if ok_method else 'FAIL'}] method = {d['method']}")

# ══════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
passed = sum(1 for _, ok in _results if ok)
total = len(_results)
print(f"回归测试结果: {passed}/{total} 通过")
if passed < total:
    print("失败项:")
    for name, ok in _results:
        if not ok:
            print("  -", name)
    sys.exit(1)
print("全部通过 ✓")
