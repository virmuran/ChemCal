# -*- coding: utf-8 -*-
"""动力粘度换算（基准：Pa·s）。

1 mPa·s = 1 cP（厘泊）；1 P（泊）= 100 cP = 0.1 Pa·s。
20 ℃ 水的动力粘度约 1.00 mPa·s。
"""
try:
    from .unit_converter_base import UnitConverterPage
except ImportError:                                   # 独立路径导入时
    from unit_converter_base import UnitConverterPage


class DynamicViscosityConverter(UnitConverterPage):
    """动力粘度单位换算器"""

    TITLE = "动力粘度换算"
    NOTE = "1 mPa·s = 1 cP（厘泊）；1 P（泊）= 100 cP。20 ℃ 水的动力粘度约 1.00 mPa·s。"
    UNITS = [
        ("帕斯卡·秒 (Pa·s)", "Pa_s", 1.0),
        ("毫帕·秒 (mPa·s = cP)", "mPa_s", 1e-3),
        ("泊 (P = g/(cm·s))", "P", 0.1),
        ("公斤力·秒/米² (kgf·s/m²)", "kgf_s_m2", 9.80665),
        ("磅/(英尺·秒) (lb/(ft·s))", "lb_ft_s", 1.4881639),
        ("磅/(英尺·小时) (lb/(ft·h))", "lb_ft_h", 4.13379e-4),
        ("磅力·秒/英尺² (lbf·s/ft²)", "lbf_s_ft2", 47.88026),
    ]
