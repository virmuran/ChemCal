# -*- coding: utf-8 -*-
"""流量换算 —— 体积流量直接互换；质量流量需要密度（默认水 1000 kg/m³）。

基准：m³/s
"""
try:
    from .unit_converter_base import UnitConverterPage, factor_over_aux
except ImportError:                                   # 独立路径导入时
    from unit_converter_base import UnitConverterPage, factor_over_aux


class FlowConverter(UnitConverterPage):
    """流量单位换算器（含质量流量）"""

    TITLE = "流量换算"
    NOTE = ("体积流量各行可直接互换；质量流量（kg/h、t/d 等）需要按实际流体的密度换算，"
            "密度默认按水 1000 kg/m³。")
    AUX_FIELDS = [
        ("rho", "密度 (kg/m³)", 1000, "默认水 1000"),
    ]
    UNITS = [
        # ── 体积流量（基准 m³/s）──
        ("立方米/秒 (m³/s)", "m3_s", 1.0),
        ("立方米/小时 (m³/h)", "m3_h", 1 / 3600),
        ("立方米/分钟 (m³/min)", "m3_min", 1 / 60),
        ("升/秒 (L/s)", "L_s", 1e-3),
        ("升/分钟 (L/min)", "L_min", 1 / 60000),
        ("升/小时 (L/h)", "L_h", 1 / 3600000),
        ("立方英尺/分钟 (ft³/min)", "ft3_min", 4.71947e-4),
        ("加仑(美)/分钟 (gpm)", "gpm_us", 6.30902e-5),

        # ── 质量流量（需密度）──
        ("千克/秒 (kg/s)", "kg_s", factor_over_aux("rho", 1.0)),
        ("千克/小时 (kg/h)", "kg_h", factor_over_aux("rho", 1 / 3600)),
        ("千克/分钟 (kg/min)", "kg_min", factor_over_aux("rho", 1 / 60)),
        ("吨/小时 (t/h)", "t_h", factor_over_aux("rho", 1000 / 3600)),
        ("吨/天 (t/d)", "t_d", factor_over_aux("rho", 1000 / 86400)),
        ("克/秒 (g/s)", "g_s", factor_over_aux("rho", 1e-3)),
        ("磅/小时 (lb/h)", "lb_h", factor_over_aux("rho", 0.45359237 / 3600)),
        ("磅/秒 (lb/s)", "lb_s", factor_over_aux("rho", 0.45359237)),
    ]
