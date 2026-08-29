"""
ChemCal 公共物理常数 & 工具函数

所有计算器共享的常数和加载函数。
改一个值就是全部生效，不用翻十几个文件。
"""

import os
import sys
import importlib.util

# ═══════════════════════════════════════════════
# 物理常数
# ═══════════════════════════════════════════════

C_TO_K = 273.15               # 摄氏度 → 开尔文
G = 9.81                      # 重力加速度 m/s²
ATM_PRESSURE_MPA = 0.101325   # 标准大气压 MPa
ATM_PRESSURE_PA = 101325      # 标准大气压 Pa
R = 8.314                      # 通用气体常数 J/(mol·K)
BAR_TO_MPA = 0.1               # 工程单位换算：1 bar = 0.1 MPa
KW_TO_KCALH = 859.845          # 功率→热量换算：1 kW = 859.845 kcal/h

# ═══════════════════════════════════════════════
# 空气物性（标准状态：0°C, 101.325 kPa）
# ═══════════════════════════════════════════════

STD_AIR_DENSITY = 1.293        # kg/m³
CP_AIR = 1.005                 # kJ/(kg·K)
AIR_MOLAR_MASS = 28.96         # g/mol

# ═══════════════════════════════════════════════
# 水物性（20°C，标准工程值）
# ═══════════════════════════════════════════════

WATER_DENSITY = 997.0          # kg/m³
WATER_CP = 4.181               # kJ/(kg·K)  — 统一用 4.181
WATER_LATENT_HEAT = 2257       # kJ/kg (100°C 常压汽化潜热)

# ═══════════════════════════════════════════════
# IAPWS-IF97 蒸汽物性模块加载器
# ═══════════════════════════════════════════════

_steam_iapws_cache = {"loaded": False, "available": False, "module": None}


def load_steam_iapws():
    """加载 IAPWS-IF97 蒸汽物性模块（全局一次，后续缓存）"""
    if _steam_iapws_cache["loaded"]:
        return _steam_iapws_cache["available"]

    _steam_iapws_cache["loaded"] = True
    try:
        # 从 common_constants.py 定位 steam_iapws.py
        base = os.path.dirname(os.path.abspath(__file__))
        iapws_path = os.path.join(base, "modules", "chemical_calculations", "steam_iapws.py")
        if not os.path.exists(iapws_path):
            # 回退：PyInstaller 打包路径
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                iapws_path = os.path.join(meipass, "modules", "chemical_calculations", "steam_iapws.py")

        spec = importlib.util.spec_from_file_location("steam_iapws", iapws_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _steam_iapws_cache["module"] = module
        _steam_iapws_cache["available"] = True
    except Exception as e:
        _steam_iapws_cache["available"] = False
        print(f"[common_constants] 警告: 无法加载 IAPWS-IF97 模块: {e}")

    return _steam_iapws_cache["available"]


def get_steam_props(p_gauge_mpa):
    """由表压 MPa(g) 获取饱和蒸汽物性（温度 + 汽化潜热）"""
    if not load_steam_iapws():
        # 回退：内置近似值 @0.3MPa
        return {"sat_temp": 143.6, "h_fg": 2133.0, "method": "内置近似值"}

    try:
        module = _steam_iapws_cache.get("module")
        p_abs = p_gauge_mpa + ATM_PRESSURE_MPA
        sat = module.saturation_properties(P_MPa=p_abs)
        return {
            "sat_temp": sat["T_C"],
            "h_fg": sat["h_fg"],
            "method": "IAPWS-IF97"
        }
    except Exception:
        return {"sat_temp": 143.6, "h_fg": 2133.0, "method": "IAPWS-IF97(备用)"}
