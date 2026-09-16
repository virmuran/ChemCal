# -*- coding: utf-8 -*-
"""热值（发热量）换算（基准：kJ/kg）。

1 kcal/kg = 1 cal/g = 4.1868 kJ/kg；1 BTU/lb = 2.326 kJ/kg。
参照：标准煤热值 29.31 MJ/kg；无水乙醇低位热值约 26.8 MJ/kg。
"""
try:
    from .unit_converter_base import UnitConverterPage
except ImportError:                                   # 独立路径导入时
    from unit_converter_base import UnitConverterPage


class CalorificValueConverter(UnitConverterPage):
    """热值 / 发热量单位换算器"""

    TITLE = "热值换算"
    NOTE = ("1 kcal/kg = 1 cal/g = 4.1868 kJ/kg；1 BTU/lb = 2.326 kJ/kg。"
            "参照值：标准煤 29.31 MJ/kg，无水乙醇低位热值约 26.8 MJ/kg。")
    UNITS = [
        ("千焦/千克 (kJ/kg = J/g)", "kJ_kg", 1.0),
        ("兆焦/千克 (MJ/kg)", "MJ_kg", 1000.0),
        ("千卡/千克 (kcal/kg = cal/g)", "kcal_kg", 4.1868),
        ("英热/磅 (BTU/lb)", "BTU_lb", 2.32602),
        ("千瓦·时/千克 (kWh/kg)", "kWh_kg", 3600.0),
    ]
