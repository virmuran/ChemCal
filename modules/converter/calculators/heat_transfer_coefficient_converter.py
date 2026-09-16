# -*- coding: utf-8 -*-
"""传热系数换算（基准：W/(m²·K)）。

卡按国际蒸汽表卡：1 cal = 4.1868 J，故 1 kcal/(h·m²·℃) = 1.163 W/(m²·K)。
换热器设计里 K 值的常用换算，与《化工原理》附表一致。
"""
try:
    from .unit_converter_base import UnitConverterPage
except ImportError:                                   # 独立路径导入时
    from unit_converter_base import UnitConverterPage


class HeatTransferCoefficientConverter(UnitConverterPage):
    """传热系数（总传热系数 K）单位换算器"""

    TITLE = "传热系数换算"
    NOTE = ("卡按国际蒸汽表卡 1 cal = 4.1868 J，即 1 kcal/(h·m²·℃) = 1.163 W/(m²·K)。"
            "常见量级：空气 10~30、水 200~1000、冷凝蒸汽 5000~15000 W/(m²·K)。")
    UNITS = [
        ("瓦/(米²·开) (W/(m²·K))", "W_m2K", 1.0),
        ("千瓦/(米²·开) (kW/(m²·K))", "kW_m2K", 1000.0),
        ("千卡/(小时·米²·℃)", "kcal_h_m2", 1.163),
        ("卡/(秒·厘米²·℃)", "cal_s_cm2", 41868.0),
        ("英热/(小时·英尺²·°F)", "BTU_h_ft2", 5.6783),
    ]
