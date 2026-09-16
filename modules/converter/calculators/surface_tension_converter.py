# -*- coding: utf-8 -*-
"""表面张力换算（基准：N/m）。

1 mN/m = 1 dyn/cm（数值相同）。20 ℃ 水的表面张力约 72 mN/m。
"""
try:
    from .unit_converter_base import UnitConverterPage
except ImportError:                                   # 独立路径导入时
    from unit_converter_base import UnitConverterPage


class SurfaceTensionConverter(UnitConverterPage):
    """表面张力单位换算器"""

    TITLE = "表面张力换算"
    NOTE = "1 mN/m = 1 dyn/cm（数值相同）。20 ℃ 水的表面张力约 72 mN/m。"
    UNITS = [
        ("牛顿/米 (N/m)", "N_m", 1.0),
        ("毫牛/米 (mN/m = dyn/cm)", "mN_m", 1e-3),
        ("公斤力/米 (kgf/m)", "kgf_m", 9.80665),
        ("克力/厘米 (gf/cm)", "gf_cm", 0.980665),
        ("磅力/英尺 (lbf/ft)", "lbf_ft", 14.5939),
        ("磅力/英寸 (lbf/in)", "lbf_in", 175.127),
    ]
