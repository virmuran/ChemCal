# -*- coding: utf-8 -*-
"""运动粘度换算（基准：m²/s）。

1 cSt（厘斯）= 1 mm²/s = 1e-6 m²/s；1 St（斯）= 1 cm²/s = 100 cSt。
运动粘度 = 动力粘度 ÷ 密度。
"""
try:
    from .unit_converter_base import UnitConverterPage
except ImportError:                                   # 独立路径导入时
    from unit_converter_base import UnitConverterPage


class KinematicViscosityConverter(UnitConverterPage):
    """运动粘度单位换算器"""

    TITLE = "运动粘度换算"
    NOTE = "1 cSt（厘斯）= 1 mm²/s；1 St（斯）= 100 cSt。运动粘度 = 动力粘度 ÷ 密度。"
    UNITS = [
        ("平方米/秒 (m²/s)", "m2_s", 1.0),
        ("平方毫米/秒 (mm²/s = cSt)", "mm2_s", 1e-6),
        ("斯 (St = cm²/s)", "St", 1e-4),
        ("平方英尺/秒 (ft²/s)", "ft2_s", 0.09290304),
        ("平方英寸/秒 (in²/s)", "in2_s", 6.4516e-4),
        ("平方米/小时 (m²/h)", "m2_h", 1 / 3600),
    ]
