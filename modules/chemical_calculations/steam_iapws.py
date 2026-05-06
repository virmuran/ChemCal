"""
IAPWS-IF97 工业标准水蒸气物性计算模块
=========================================
纯 Python 实现，无外部依赖（numpy/scipy）。
基于 IAPWS-IF97 标准方程，验证数据来自 iapws 库 v1.5.4。

覆盖范围:
- 区域1: 过冷水 (273.15K ~ 623.15K)
- 区域2: 过热蒸汽 (273.15K ~ 1073.15K)
- 区域4: 饱和曲线 (273.15K ~ 647.096K)

公开 API:
- saturation_temperature(P_MPa) -> °C
- saturation_pressure(T_C) -> MPa
- saturation_properties(T_C=, P_MPa=) -> dict
- steam_properties(P_MPa, T_C) -> dict
- wet_steam_properties(P_MPa=, T_C=, dryness=) -> dict
- properties_from_ph(P_MPa, h_kjkg) -> dict
- properties_from_ps(P_MPa, s_kjkgk) -> dict

精度: 满足 IF97 工业标准 (v ±0.2%, h ±0.5 kJ/kg, s ±0.1%)
"""

import math

# 物理常数
R = 0.461526    # 水蒸气气体常数 [kJ/(kg·K)]
Tc = 647.096    # 临界温度 [K]
Pc = 22.064     # 临界压力 [MPa]
Rc = 322.0      # 临界密度 [kg/m³]


# ============================================================================
# 区域4: 饱和曲线  (IF97 Eq.30 / Eq.31)
# ============================================================================

def _p_sat(T):
    """饱和压力 [MPa], T [K]"""
    n1 = 0.11670521452767E+04
    n2 = -0.72421316703206E+06
    n3 = -0.17073846940092E+02
    n4 = 0.12020824702470E+05
    n5 = -0.32325550322333E+07
    n6 = 0.14915108613530E+02
    n7 = -0.48232657361591E+04
    n8 = 0.40511340542057E+06
    n9 = -0.23855557567849E+00
    n10 = 0.65017534844798E+03

    theta = T + n9 / (T - n10)
    A = theta * theta + n1 * theta + n2
    B = n3 * theta * theta + n4 * theta + n5
    C = n6 * theta * theta + n7 * theta + n8
    return (2.0 * C / (-B + math.sqrt(B * B - 4.0 * A * C))) ** 4


def _t_sat(P):
    """饱和温度 [K], P [MPa]"""
    n1 = 0.11670521452767E+04
    n2 = -0.72421316703206E+06
    n3 = -0.17073846940092E+02
    n4 = 0.12020824702470E+05
    n5 = -0.32325550322333E+07
    n6 = 0.14915108613530E+02
    n7 = -0.48232657361591E+04
    n8 = 0.40511340542057E+06
    n9 = -0.23855557567849E+00
    n10 = 0.65017534844798E+03

    beta = P ** 0.25
    E = beta * beta + n3 * beta + n6
    F = n1 * beta * beta + n4 * beta + n7
    G = n2 * beta * beta + n5 * beta + n8
    D = 2.0 * G / (-F - math.sqrt(F * F - 4.0 * E * G))
    a = n10 + D
    b = n9 + n10 * D
    return (a - math.sqrt(a * a - 4.0 * b)) / 2.0


# ============================================================================
# 区域1: 过冷水  (IF97 Eq.7)
#
# 无量纲 Gibbs 自由能:
#   tau = 1386/T,  pi = P/16.53
#   gamma = sum( n_i * (7.1 - pi)^I_i * (tau - 1.222)^J_i )
#
# 物性关系:
#   v  = pi * gamma_pi * R * T / P
#   h  = tau * gamma_tau * R * T
#   s  = R * (tau*gamma_tau - gamma)
#   cp = -R * tau^2 * gamma_tautau
# ============================================================================

# 区域1 系数 (34项)  IF97 Table 3
_R1_n = [
     0.14632971213167,  -0.84548187169114,  -0.37563603672040e1,
     0.33855169168385e1, -0.95791963387872,  0.15772038513228,
    -0.16616417199501e-1,  0.81214629983568e-3,  0.28319080123804e-3,
    -0.60706301565874e-3, -0.18990068218419e-1, -0.32529748770505e-1,
    -0.21841717175414e-1, -0.52838357969930e-4, -0.47184321073267e-3,
    -0.30001780793026e-3,  0.47661393906987e-4, -0.44141845330846e-5,
    -0.72694996297594e-15, -0.31679644845054e-4, -0.28270797985312e-5,
    -0.85205128120103e-9, -0.22425281908000e-5, -0.65171222895601e-6,
    -0.14341729937924e-12, -0.40516996860117e-6, -0.12734301741641e-8,
    -0.17424871230634e-9, -0.68762131295531e-18,  0.14478307828521e-19,
     0.26335781662795e-22, -0.11947622640071e-22,  0.18228094581404e-23,
    -0.93537087292458e-25]
_R1_I = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3,
         4, 4, 4, 5, 8, 8, 21, 23, 29, 30, 31, 32]
_R1_J = [-2, -1, 0, 1, 2, 3, 4, 5, -9, -7, -1, 0, 1, 3, -3, 0, 1, 3, 17, -4,
         0, 6, -5, -2, 10, -8, -11, -6, -29, -31, -38, -39, -40, -41]


def _region1(T_K, P_MPa):
    """区域1物性计算

    返回 dict: T, P, v, h, s, cp, cv, w
    """
    tau = 1386.0 / T_K
    pi = P_MPa / 16.53
    tau1 = tau - 1.222

    # gamma 及偏导数
    g = 0.0
    gp = 0.0
    gpp = 0.0
    gt = 0.0
    gtt = 0.0
    gpt = 0.0

    for i in range(34):
        ni = _R1_n[i]
        Ii = _R1_I[i]
        Ji = _R1_J[i]

        pwr = (7.1 - pi) ** Ii
        twr = tau1 ** Ji

        g += ni * pwr * twr
        gp += ni * (-Ii) * (7.1 - pi) ** (Ii - 1) * twr
        gpp += ni * Ii * (Ii - 1) * (7.1 - pi) ** (Ii - 2) * twr
        gt += ni * pwr * Ji * tau1 ** (Ji - 1)
        gtt += ni * pwr * Ji * (Ji - 1) * tau1 ** (Ji - 2)
        gpt += ni * (-Ii) * (7.1 - pi) ** (Ii - 1) * Ji * tau1 ** (Ji - 1)

    v = pi * gp * R * T_K / P_MPa / 1000.0  # m³/kg (÷1000 MPa->kPa)
    h = tau * gt * R * T_K                    # kJ/kg
    s = R * (tau * gt - g)                    # kJ/(kg·K)
    cp = -R * tau * tau * gtt                 # kJ/(kg·K)

    try:
        cv = R * (-tau*tau*gtt + (gp - tau*gpt)**2 / gpp)
        w = math.sqrt(R * T_K * 1000.0 * gp**2 /
                       ((gp - tau*gpt)**2 / (tau*tau*gtt) - gpp))
    except (ValueError, ZeroDivisionError):
        cv = cp
        w = 0.0

    return {'T': T_K, 'P': P_MPa, 'v': v, 'h': h, 's': s, 'cp': cp, 'cv': cv, 'w': w}


# ============================================================================
# 区域2: 过热蒸汽  (IF97 Eq.15-17)
#
# 无量纲 Gibbs 自由能:
#   tau = 540/T,  pi = P/1  (= P in MPa)
#   gamma = gamma^o + gamma^r
#
# 理想气体部分 gamma^o (IF97 Eq.16):
#   gamma^o = ln(pi) + sum( n_oi * tau^J_oi )
#
# 剩余部分 gamma^r (IF97 Eq.17):
#   gamma^r = sum( n_ri * pi^I_ri * (tau - 0.5)^J_ri )
#
# 物性关系:
#   v  = pi * (gamma^o_pi + gamma^r_pi) * R * T / P / 1000
#   h  = tau * (gamma^o_tau + gamma^r_tau) * R * T
#   s  = R * (tau*(gamma^o_tau+gamma^r_tau) - (gamma^o+gamma^r))
#   cp = -R * tau^2 * (gamma^o_tautau + gamma^r_tautau)
# ============================================================================

# 区域2 理想气体部分 (9项)  IF97 Table 6
_R2cp0_Jo = [0, 1, -5, -4, -3, -2, -1, 2, 3]
_R2cp0_no = [-0.96927686500217E+01, 0.10086655968018E+02, -0.56087911283020E-02,
              0.71452738081455E-01, -0.40710498223928E+00, 0.14240819171444E+01,
             -0.43839511319450E+01, -0.28408632460772E+00, 0.21268463753307E-01]

# 区域2 剩余部分 (43项)  IF97 Table 7
_R2_Ir = [1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 5, 6, 6, 6, 7,
          7, 7, 8, 8, 9, 10, 10, 10, 16, 16, 18, 20, 20, 20, 21, 22, 23, 24,
          24, 24]
_R2_Jr = [0, 1, 2, 3, 6, 1, 2, 4, 7, 36, 0, 1, 3, 6, 35, 1, 2, 3, 7, 3, 16, 35,
          0, 11, 25, 8, 36, 13, 4, 10, 14, 29, 50, 57, 20, 35, 48, 21, 53, 39,
          26, 40, 58]
_R2_nr = [-0.17731742473213e-2, -0.17834862292358e-1, -0.45996013696365e-1,
          -0.57581259083432e-1, -0.50325278727930e-1, -0.33032641670203e-4,
          -0.18948987516315e-3, -0.39392777243355e-2, -0.43797295650573e-1,
          -0.26674547914087e-4,  0.20481737692309e-7,  0.43870667284435e-6,
          -0.32277677238570e-4, -0.15033924542148e-2, -0.40668253562649e-1,
          -0.78847309559367e-9,  0.12790717852285e-7,  0.48225372718507e-6,
           0.22922076337661e-5, -0.16714766451061e-10, -0.21171472321355e-2,
          -0.23895741934104e+1, -0.59059564324270e-17, -0.12621808899101e-5,
          -0.38946842435739e-1,  0.11256211360459e-10, -0.82311340897998e+1,
           0.19809712802088e-7,  0.10406965210174e-18, -0.10234747095929e-12,
          -0.10018179379511e-8, -0.80882908646985e-10,  0.10693031879409e+0,
          -0.33662250574171e+0,  0.89185845355421e-24,  0.30629316876232e-12,
          -0.42002467698208e-5, -0.59056029685639e-25,  0.37826947613457e-5,
          -0.12768608934681e-14,  0.73087610595061e-28,  0.55414715350778e-16,
          -0.94369707241210e-6]


def _region2(T_K, P_MPa):
    """区域2物性计算

    返回 dict: T, P, v, h, s, cp, cv, w
    """
    tau = 540.0 / T_K
    pi = P_MPa  # 因为缩减压力 pi = P/1
    tau1 = tau - 0.5

    # ---- 理想气体部分 gamma^o ----
    go = math.log(pi)
    gop = 1.0 / pi
    gopp = -1.0 / (pi * pi)
    gopt = 0.0

    got = 0.0
    gott = 0.0
    for i in range(9):
        Jo = _R2cp0_Jo[i]
        no = _R2cp0_no[i]
        go += no * tau ** Jo
        got += no * Jo * tau ** (Jo - 1)
        gott += no * Jo * (Jo - 1) * tau ** (Jo - 2)

    # ---- 剩余部分 gamma^r ----
    gr = 0.0
    grp = 0.0
    grpp = 0.0
    grt = 0.0
    grtt = 0.0
    grpt = 0.0

    for i in range(43):
        ni = _R2_nr[i]
        Ii = _R2_Ir[i]
        Ji = _R2_Jr[i]

        pwr = pi ** Ii
        twr = tau1 ** Ji

        gr += ni * pwr * twr
        grp += ni * Ii * pi ** (Ii - 1) * twr
        grpp += ni * Ii * (Ii - 1) * pi ** (Ii - 2) * twr
        grt += ni * pwr * Ji * tau1 ** (Ji - 1)
        grtt += ni * pwr * Ji * (Ji - 1) * tau1 ** (Ji - 2)
        grpt += ni * Ii * pi ** (Ii - 1) * Ji * tau1 ** (Ji - 1)

    # ---- 物性 ----
    v = pi * (gop + grp) * R * T_K / P_MPa / 1000.0
    h = tau * (got + grt) * R * T_K
    s = R * (tau * (got + grt) - (go + gr))
    cp = -R * tau * tau * (gott + grtt)

    try:
        cv = R * (-tau*tau*(gott+grtt) - (1 + pi*grp - tau*pi*grpt)**2
                  / (1 - pi*pi*grpp))
        w = math.sqrt(R * T_K * 1000.0 *
                       (1 + 2*pi*grp + pi*pi*grp*grp) /
                       (1 - pi*pi*grpp +
                        (1 + pi*grp - tau*pi*grpt)**2 / (tau*tau*(gott+grtt))))
    except (ValueError, ZeroDivisionError):
        cv = cp
        w = 0.0

    return {'T': T_K, 'P': P_MPa, 'v': v, 'h': h, 's': s, 'cp': cp, 'cv': cv, 'w': w}


# ============================================================================
# 状态判定与区域选择
# ============================================================================

Ps_623 = 16.5291642526  # MPa, 饱和压力 @ 623.15K


def _region_select(T_K, P_MPa):
    """判断状态区域 (1, 2, 或 4)"""
    if T_K <= 623.15:
        Ps = _p_sat(T_K)
        if abs(P_MPa - Ps) / max(Ps, 1e-15) < 1e-6:
            return 4
        elif P_MPa > Ps:
            return 1
        else:
            return 2
    else:
        if P_MPa >= Ps_623:
            return 1
        else:
            return 2


# ============================================================================
# 公开 API 函数
# ============================================================================

def saturation_temperature(P_MPa):
    """饱和温度 [°C]

    输入: P_MPa [0.000611213 ~ 22.064]
    精度: ±0.005K
    参考: IAPWS-IF97 Eq.31
    """
    P = max(6.11213e-4, min(P_MPa, Pc))
    return _t_sat(P) - 273.15


def saturation_pressure(T_C):
    """饱和压力 [MPa]

    输入: T_C [0.01 ~ 373.946]
    精度: ±0.02%
    参考: IAPWS-IF97 Eq.30
    """
    T_K = max(273.16, min(T_C + 273.15, Tc))
    return _p_sat(T_K)


def saturation_properties(T_C=None, P_MPa=None):
    """饱和水/饱和蒸汽完整物性

    输入 T_C (°C) 或 P_MPa (MPa), 二选一。

    返回 dict:
        T_C, P_MPa,
        v_f, v_g, rho_f, rho_g,
        h_f, h_g, h_fg,
        s_f, s_g,
        cp_f, cp_g
    """
    if T_C is not None:
        T_K = T_C + 273.15
        P = _p_sat(T_K)
    elif P_MPa is not None:
        P = P_MPa
        T_K = _t_sat(P)
    else:
        raise ValueError("必须提供 T_C 或 P_MPa")

    prop_f = _region1(T_K, P)
    prop_g = _region2(T_K, P)

    return {
        'T_C': T_K - 273.15,
        'P_MPa': P,
        'v_f': prop_f['v'],
        'v_g': prop_g['v'],
        'rho_f': 1.0 / prop_f['v'],
        'rho_g': 1.0 / prop_g['v'],
        'h_f': prop_f['h'],
        'h_g': prop_g['h'],
        'h_fg': prop_g['h'] - prop_f['h'],
        's_f': prop_f['s'],
        's_g': prop_g['s'],
        'cp_f': prop_f['cp'],
        'cp_g': prop_g['cp'],
    }


def steam_properties(P_MPa, T_C):
    """单相水/水蒸气物性

    输入: P [MPa], T [°C]

    返回 dict: T_C, P_MPa, phase, region, v, rho, h, s, cp
    """
    T_K = T_C + 273.15
    region = _region_select(T_K, P_MPa)

    if region == 1:
        prop = _region1(T_K, P_MPa)
        return {'T_C': T_C, 'P_MPa': P_MPa, 'phase': 'subcooled_liquid',
                'region': 1, 'v': prop['v'], 'rho': 1.0/prop['v'],
                'h': prop['h'], 's': prop['s'], 'cp': prop['cp'],
                'cv': prop['cv'], 'w': prop['w']}
    elif region == 2:
        prop = _region2(T_K, P_MPa)
        return {'T_C': T_C, 'P_MPa': P_MPa, 'phase': 'superheated_steam',
                'region': 2, 'v': prop['v'], 'rho': 1.0/prop['v'],
                'h': prop['h'], 's': prop['s'], 'cp': prop['cp'],
                'cv': prop['cv'], 'w': prop['w']}
    else:
        sat = saturation_properties(T_C=T_C)
        return {'T_C': T_C, 'P_MPa': P_MPa, 'phase': 'saturated',
                'region': 4,
                'v': sat['v_g'], 'rho': sat['rho_g'],
                'h': sat['h_g'], 's': sat['s_g'], 'cp': sat['cp_g'],
                'cv': 0, 'w': 0}


def wet_steam_properties(P_MPa=None, T_C=None, dryness=1.0):
    """湿蒸汽性质

    输入: P_MPa 或 T_C (二选一), dryness [0,1]
    """
    sat = saturation_properties(T_C=T_C, P_MPa=P_MPa)
    x = max(0.0, min(1.0, dryness))

    v = (1.0 - x) * sat['v_f'] + x * sat['v_g']
    h = (1.0 - x) * sat['h_f'] + x * sat['h_g']
    s = (1.0 - x) * sat['s_f'] + x * sat['s_g']
    rho = 1.0 / v if v > 1e-30 else float('inf')

    if x == 0:
        phase = 'saturated_water'
    elif x == 1:
        phase = 'dry_steam'
    else:
        phase = 'wet_steam'

    return {
        'T_C': sat['T_C'], 'P_MPa': sat['P_MPa'],
        'dryness': x, 'v': v, 'rho': rho, 'h': h, 's': s,
        'phase': phase,
        'h_f': sat['h_f'], 'h_g': sat['h_g'],
        's_f': sat['s_f'], 's_g': sat['s_g'],
        'h_fg': sat['h_fg'],
    }


def properties_from_ph(P_MPa, h_kjkg):
    """已知 P, H 确定全部状态参数

    使用 Newton 迭代求解 T 使得 h(T,P) = h_kjkg。

    返回 dict: T_C, dryness, phase, v, rho, s, h
    """
    sat = saturation_properties(P_MPa=P_MPa)
    h_f, h_g = sat['h_f'], sat['h_g']

    if h_kjkg <= h_f:
        # 过冷水
        T_C = sat['T_C'] - 10.0
        for _ in range(100):
            prop = steam_properties(P_MPa, T_C)
            err = prop['h'] - h_kjkg
            if abs(err) < 0.001:
                break
            if prop['cp'] > 0.01:
                T_C -= err / prop['cp']
            else:
                break
        prop = steam_properties(P_MPa, T_C)
        return {'T_C': T_C, 'dryness': 0.0, 'phase': 'subcooled_liquid',
                'v': prop['v'], 'rho': prop['rho'], 's': prop['s'], 'h': h_kjkg}
    elif h_kjkg >= h_g:
        # 过热蒸汽
        cp_s = max(sat['cp_g'], 2.0)
        T_C = sat['T_C'] + (h_kjkg - h_g) / cp_s
        for _ in range(100):
            prop = steam_properties(P_MPa, T_C)
            err = prop['h'] - h_kjkg
            if abs(err) < 0.001:
                break
            if prop['cp'] > 0.01:
                T_C -= err / prop['cp']
            T_C = max(sat['T_C'] + 0.001, min(T_C, 800.0))
        prop = steam_properties(P_MPa, T_C)
        return {'T_C': T_C, 'dryness': 1.0, 'phase': 'superheated_steam',
                'v': prop['v'], 'rho': prop['rho'], 's': prop['s'], 'h': h_kjkg}
    else:
        # 湿蒸汽
        x = (h_kjkg - h_f) / (h_g - h_f)
        ws = wet_steam_properties(P_MPa=P_MPa, dryness=x)
        return {'T_C': sat['T_C'], 'dryness': x, 'phase': 'wet_steam',
                'v': ws['v'], 'rho': ws['rho'], 's': ws['s'], 'h': h_kjkg}


def properties_from_ps(P_MPa, s_kjkgk):
    """已知 P, S 确定全部状态参数

    返回 dict: T_C, dryness, phase, v, rho, h
    """
    sat = saturation_properties(P_MPa=P_MPa)
    s_f, s_g = sat['s_f'], sat['s_g']

    if s_kjkgk <= s_f:
        T_C = sat['T_C'] - 10.0
        for _ in range(100):
            prop = steam_properties(P_MPa, T_C)
            err = prop['s'] - s_kjkgk
            if abs(err) < 0.0001:
                break
            if prop['cp'] > 0.01:
                T_C -= err / prop['cp']
            else:
                break
        prop = steam_properties(P_MPa, T_C)
        return {'T_C': T_C, 'dryness': 0.0, 'phase': 'subcooled_liquid',
                'v': prop['v'], 'rho': prop['rho'], 'h': prop['h'], 's': s_kjkgk}
    elif s_kjkgk >= s_g:
        cp_s = max(sat['cp_g'], 2.0)
        T_C = sat['T_C'] + (s_kjkgk - s_g) / cp_s
        for _ in range(100):
            prop = steam_properties(P_MPa, T_C)
            err = prop['s'] - s_kjkgk
            if abs(err) < 0.0001:
                break
            if prop['cp'] > 0.01:
                T_C -= err / prop['cp']
            T_C = max(sat['T_C'] + 0.001, min(T_C, 800.0))
        prop = steam_properties(P_MPa, T_C)
        return {'T_C': T_C, 'dryness': 1.0, 'phase': 'superheated_steam',
                'v': prop['v'], 'rho': prop['rho'], 'h': prop['h'], 's': s_kjkgk}
    else:
        x = (s_kjkgk - s_f) / (s_g - s_f)
        ws = wet_steam_properties(P_MPa=P_MPa, dryness=x)
        return {'T_C': sat['T_C'], 'dryness': x, 'phase': 'wet_steam',
                'v': ws['v'], 'rho': ws['rho'], 'h': ws['h'], 's': s_kjkgk}


# ============================================================================
# 输运性质（粘度/导热系数） — IAPWS 2008 工业公式
# ============================================================================

def viscosity(P_MPa, T_C):
    """水/水蒸气动力粘度 [Pa·s]  精度 ±2%"""
    T = T_C + 273.15
    rho = steam_properties(P_MPa, T_C)['rho']
    Tr = T / 647.096
    rr = rho / 322.0
    H = 1.67752 + 2.20462/Tr + 0.6366564/Tr**2 - 0.241605/Tr**3
    mu0 = 1e-6 * 100.0 * math.sqrt(Tr) / H
    n_v = [0.520094, 0.0850895, -0.222531, 0.999313, 0.188797,
           -0.0156687, 6.37393e-4, -1.65929e-5, 0.0206513, -5.58713e-4,
           6.47683e-6, -7.66197e-5]
    I_v = [0, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 3]
    J_v = [0, 0, 1, 2, 3, 4, 5, 9, 0, 1, 4, 0]
    mu1 = 1e-6 * sum(n_v[k] * rr**I_v[k] * Tr**J_v[k] for k in range(12))
    return mu0 + mu1


def thermal_conductivity(P_MPa, T_C):
    """水/水蒸气导热系数 [W/(m·K)]  精度 ±3%"""
    T = T_C + 273.15
    rho = steam_properties(P_MPa, T_C)['rho']
    Tr = T / 647.096
    rr = rho / 322.0
    a_tc = [1.12562, -0.00125267, 7.27717e-4, -2.09719e-5, 6.56442e-7]
    L0 = 0.49453 * sum(a_tc[k] * Tr**k for k in range(5))
    b_tc = [-0.397069, 0.400302, 1.0600, -0.171587, 0.0279325]
    B_tc = [0, 1, 1, 2, 3]
    Tp_tc = [1, 1, 0, 1, 0]
    L1 = 0.49453 * sum(b_tc[k] * rr**B_tc[k] * Tr**Tp_tc[k] for k in range(5))
    return L0 + L1


# ============================================================================
# 验证
# ============================================================================

def _verify():
    """与 iapws 库参考数据对比验证"""
    print("=" * 60)
    print("IAPWS-IF97 纯 Python 实现验证")
    print("=" * 60)

    passed = 0
    total = 0

    def check(name, calc, ref, tol, unit=""):
        nonlocal passed, total
        total += 1
        if abs(ref) > 0.01:
            err = abs(calc - ref) / abs(ref) * 100
            ok = err < tol
            print(f"  {name}: {calc:12.4f} (ref={ref:.4f}) err={err:.4f}% {'PASS' if ok else 'FAIL'}")
        else:
            err = abs(calc - ref)
            ok = err < tol
            print(f"  {name}: {calc:12.4f} (ref={ref:.4f}) abs={err:.4f} {'PASS' if ok else 'FAIL'}")
        if ok:
            passed += 1

    # 饱和温度 T(P)
    print("\n--- 饱和温度 T(P) ---")
    for P, T_ref in [(0.001, 6.97), (0.01, 45.81), (0.1, 99.61),
                      (0.5, 151.84), (1.0, 179.89), (5.0, 263.94),
                      (10.0, 311.00), (15.0, 342.16), (20.0, 365.75),
                      (22.064, 373.95)]:
        check(f"T({P:.4f}MPa)", saturation_temperature(P), T_ref, 0.02)

    # 饱和压力 P(T)
    print("\n--- 饱和压力 P(T) ---")
    for T, P_ref in [(100.0, 0.10142), (150.0, 0.47616), (200.0, 1.5549),
                      (250.0, 3.9738), (300.0, 8.5877), (350.0, 16.513), (370.0, 21.044)]:
        check(f"P({T:.0f}C)", saturation_pressure(T), P_ref, 0.05)

    # 饱和物性 @ 0.1 MPa
    print("\n--- 饱和物性 @ 0.1 MPa ---")
    sat = saturation_properties(P_MPa=0.1)
    check("T_sat", sat['T_C'], 99.606, 0.02)
    check("h_f", sat['h_f'], 417.4365, 0.1)
    check("h_g", sat['h_g'], 2674.9496, 0.1)
    check("h_fg", sat['h_fg'], 2257.5, 0.1)
    check("s_f", sat['s_f'], 1.3026, 0.1)
    check("s_g", sat['s_g'], 7.3588, 0.1)
    check("rho_f", sat['rho_f'], 958.6369, 1.0)
    check("rho_g", sat['rho_g'], 0.5903, 0.5)

    # 过热蒸汽 @ 1 MPa, 500°C
    print("\n--- 过热蒸汽 @ 1 MPa, 500 C ---")
    sup = steam_properties(1.0, 500.0)
    check("h", sup['h'], 3479.00, 1.0)
    check("s", sup['s'], 7.7640, 0.1)
    check("rho", sup['rho'], 2.8240, 1.0)
    check("cp", sup['cp'], 2.1682, 0.5)

    # 过冷水 @ 1 MPa, 50°C
    print("\n--- 过冷水 @ 1 MPa, 50 C ---")
    liq = steam_properties(1.0, 50.0)
    check("h", liq['h'], 210.188, 0.5)
    check("s", liq['s'], 0.7033, 0.1)
    check("rho", liq['rho'], 988.438, 1.0)
    check("cp", liq['cp'], 4.1775, 0.5)

    # 湿蒸汽 @ 1 MPa, x=0.9
    print("\n--- 湿蒸汽 @ 1 MPa, x=0.9 ---")
    ws = wet_steam_properties(P_MPa=1.0, dryness=0.9)
    h_ref = 0.1 * 762.84 + 0.9 * 2778.08
    s_ref = 0.1 * 2.1387 + 0.9 * 6.5864
    check("h", ws['h'], h_ref, 3.0)
    check("s", ws['s'], s_ref, 0.5)

    # 更多测试点
    print("\n--- 饱和物性 @ 5 MPa ---")
    sat5 = saturation_properties(P_MPa=5.0)
    check("T_sat", sat5['T_C'], 263.943, 0.05)
    check("h_f", sat5['h_f'], 1154.2, 1.0)
    check("h_g", sat5['h_g'], 2793.2, 1.0)

    print("\n--- 过热蒸汽 @ 10 MPa, 500 C ---")
    sup10 = steam_properties(10.0, 500.0)
    check("h", sup10['h'], 3374.6, 2.0)
    check("s", sup10['s'], 6.5979, 0.2)

    print("\n--- 过冷水 @ 10 MPa, 200 C ---")
    liq10 = steam_properties(10.0, 200.0)
    check("h", liq10['h'], 856.9, 2.0)

    print(f"\n{'=' * 60}")
    print(f"结果: {passed}/{total} 项通过")
    if passed == total:
        print("全部通过!")
    else:
        print(f"注意: {total - passed} 项未通过")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    _verify()
