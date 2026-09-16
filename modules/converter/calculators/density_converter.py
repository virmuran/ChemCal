# -*- coding: utf-8 -*-
"""密度换算 —— 含相对密度、API 度、波美度三个非线性单位。

基准：kg/m³

· API 度（石油标准，60 °F）：  °API = 141.5 / SG − 131.5
· 波美度（美制重表）：        °Bé = 145 − 145 / SG     （适用于比水重的液体：糖液、碱液等）
  两者都不是线性比例，所以按"转基准 / 反基准"两个函数给出。
"""
try:
    from .unit_converter_base import UnitConverterPage
except ImportError:                                   # 独立路径导入时
    from unit_converter_base import UnitConverterPage


def _api_to_base(value, aux):
    """°API → kg/m³。"""
    denominator = value + 131.5
    if denominator == 0:
        return None
    return 141.5 / denominator * 1000.0               # SG → ×1000 得 kg/m³


def _api_from_base(base, aux):
    """kg/m³ → °API。"""
    sg = base / 1000.0
    if sg == 0:
        return None
    return 141.5 / sg - 131.5


def _be_to_base(value, aux):
    """波美度（重表）→ kg/m³。"""
    denominator = 145.0 - value
    if denominator == 0:
        return None
    return 145.0 / denominator * 1000.0


def _be_from_base(base, aux):
    """kg/m³ → 波美度（重表）。"""
    sg = base / 1000.0
    if sg == 0:
        return None
    return 145.0 - 145.0 / sg


class DensityConverter(UnitConverterPage):
    """密度 / 相对密度单位换算器"""

    TITLE = "密度换算"
    NOTE = ("相对密度以 4 ℃ 水的密度 1000 kg/m³ 为基准。API 度按石油标准 "
            "°API = 141.5/SG − 131.5；波美度按美制重表 °Bé = 145 − 145/SG，"
            "适用于比水重的液体（糖液、碱液等）。")
    UNITS = [
        ("千克/立方米 (kg/m³)", "kg_m3", 1.0),
        ("克/立方厘米 (g/cm³ = kg/L)", "g_cm3", 1000.0),
        ("吨/立方米 (t/m³)", "t_m3", 1000.0),
        ("克/升 (g/L)", "g_L", 1.0),
        ("磅/立方英尺 (lb/ft³)", "lb_ft3", 16.0185),
        ("磅/加仑(美) (lb/gal)", "lb_gal", 119.826),
        ("磅/立方英寸 (lb/in³)", "lb_in3", 27679.9),
        ("相对密度 SG (水=1)", "sg", 1000.0),
        ("API 度 (°API)", "api", _api_to_base, _api_from_base),
        ("波美度 (°Bé 重表)", "be", _be_to_base, _be_from_base),
    ]
