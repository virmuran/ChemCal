# -*- coding: utf-8 -*-
"""导热系数换算（基准：W/(m·K)）。

卡按国际蒸汽表卡：1 cal = 4.1868 J，故 1 kcal/(h·m·℃) = 1.163 W/(m·K)，
与《化工原理》附表一致。（热化学卡 4.184 J 会得到 1.1622，差 0.07%。）
"""
try:
    from .unit_converter_base import UnitConverterPage
except ImportError:                                   # 独立路径导入时
    from unit_converter_base import UnitConverterPage


class ThermalConductivityConverter(UnitConverterPage):
    """导热系数单位换算器"""

    TITLE = "导热系数换算"
    NOTE = ("卡按国际蒸汽表卡 1 cal = 4.1868 J，即 1 kcal/(h·m·℃) = 1.163 W/(m·K)。"
            "常见量级：保温棉 0.04、水 0.6、碳钢 45 W/(m·K)。")
    UNITS = [
        ("瓦/(米·开) (W/(m·K))", "W_mK", 1.0),
        ("毫瓦/(米·开) (mW/(m·K))", "mW_mK", 1e-3),
        ("千瓦/(米·开) (kW/(m·K))", "kW_mK", 1000.0),
        ("卡/(秒·厘米·℃)", "cal_s_cm", 418.68),
        ("千卡/(小时·米·℃)", "kcal_h_m", 1.163),
        ("英热/(小时·英尺·°F)", "BTU_h_ft", 1.7307),
        ("英热·英寸/(小时·英尺²·°F)", "BTU_in", 0.14422),
    ]
