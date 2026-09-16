# -*- coding: utf-8 -*-
"""比热容换算（基准：kJ/(kg·K)）。

1 kcal/(kg·℃) = 1 cal/(g·℃) = 1 BTU/(lb·°F) = 4.1868 kJ/(kg·K)（数值相同）。
20 ℃ 水的比热约 4.18 kJ/(kg·K)。
"""
try:
    from .unit_converter_base import UnitConverterPage
except ImportError:                                   # 独立路径导入时
    from unit_converter_base import UnitConverterPage


class SpecificHeatConverter(UnitConverterPage):
    """比热容单位换算器"""

    TITLE = "比热容换算"
    NOTE = ("1 kcal/(kg·℃) = 1 cal/(g·℃) = 1 BTU/(lb·°F) = 4.1868 kJ/(kg·K)，三者数值相同。"
            "20 ℃ 水的比热约 4.18 kJ/(kg·K)。")
    UNITS = [
        ("千焦/(千克·开) (kJ/(kg·K))", "kJ_kgK", 1.0),
        ("焦/(千克·开) (J/(kg·K))", "J_kgK", 1e-3),
        ("千卡/(千克·℃) = 卡/(克·℃)", "kcal_kgC", 4.1868),
        ("英热/(磅·°F)", "BTU_lbF", 4.1868),
        ("瓦·时/(千克·开) (W·h/(kg·K))", "Wh_kgK", 3.6),
    ]
