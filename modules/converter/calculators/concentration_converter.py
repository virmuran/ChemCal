# -*- coding: utf-8 -*-
"""浓度换算 —— 三组单位，跨组需要辅助参数。

基准：kg 溶质 / m³ 溶液

    ① 质量分数类（每千克溶液）：%、ppm、ppb           —— 换算需溶液密度 ρ
    ② 质量浓度类（每立方米溶液）：kg/m³、mg/L、g/100mL  —— 自身即可互换
    ③ 物质的量浓度类：mol/L、mmol/L、kmol/m³          —— 换算需摩尔质量 M

为什么这么分组：% 与 mg/L 不是同一回事（一个是"每千克溶液"、一个是"每升溶液"），
不填密度就换算是错的。所以缺辅助参数时对应的一列留空，而不是给个看似合理的数字。
"""
try:
    from .unit_converter_base import UnitConverterPage, unit_in_aux
except ImportError:                                   # 独立路径导入时
    from unit_converter_base import UnitConverterPage, unit_in_aux


class ConcentrationConverter(UnitConverterPage):
    """溶液浓度换算器（质量分数 / 质量浓度 / 物质的量浓度）"""

    TITLE = "浓度换算"
    NOTE = ("三组单位：%、ppm、ppb 是「每千克溶液」；kg/m³、mg/L、g/100mL 是「每立方米溶液」，"
            "两组互换需要溶液密度；mol/L、mmol/L、kmol/m³ 是「物质的量浓度」，与质量浓度互换需要"
            "摩尔质量（未填时该组留空）。")
    AUX_FIELDS = [
        ("rho", "溶液密度 (kg/m³)", 1000, "默认水 1000"),
        ("M", "摩尔质量 (g/mol)", "", "如 NaCl 58.44"),
    ]
    LABEL_WIDTH = 165
    UNITS = [
        # ── ① 质量分数类（需密度 ρ）──
        ("质量分数 (%)", "pct", unit_in_aux("rho", 0.01)),
        ("ppm (mg/kg 溶液)", "ppm", unit_in_aux("rho", 1e-6)),
        ("ppb (μg/kg 溶液)", "ppb", unit_in_aux("rho", 1e-9)),

        # ── ② 质量浓度类（自身可互换）──
        ("kg/m³ (= g/L = mg/mL)", "kg_m3", 1.0),
        ("mg/L (= μg/mL)", "mg_L", 1e-3),
        ("g/100mL", "g_100mL", 10.0),

        # ── ③ 物质的量浓度类（需摩尔质量 M）──
        ("mol/L", "mol_L", unit_in_aux("M", 1.0)),
        ("mmol/L", "mmol_L", unit_in_aux("M", 1e-3)),
        ("μmol/L", "umol_L", unit_in_aux("M", 1e-6)),
        ("mol/m³", "mol_m3", unit_in_aux("M", 1e-3)),
        ("kmol/m³", "kmol_m3", unit_in_aux("M", 1.0)),
    ]
