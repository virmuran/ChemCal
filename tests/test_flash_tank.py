# -*- coding: utf-8 -*-
"""闪蒸罐计算（汽液分离罐筒体尺寸）+ 全链联动 回归测试

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_flash_tank.py

核对依据
════════════════════════════════════════════════════════════════════════
Part A  物性锚点（IAPWS-IF97 独立复算）
    p = 101.325 kPa：t_sat = 99.97 °C、v_g = 1.67333 m³/kg
    ⇒ ρ_g = 1 / v_g = 0.597610 kg/m³

Part B  逐列对齐设计表格（默认 0.145 t/h、101.325 kPa、ρ 自动、u = 1.0 m/s、
        k = 1.2、H/D = 2.0、向上圆整）—— 手算锚点：
    B1 「闪蒸汽流量」  m = 0.145 t/h × 1000 ÷ 3600 = 0.0402778 kg/s
    B2 「截面积」      A = 0.0402778 ÷ 0.597610 ÷ 1.0 = 0.0673981 m²
    B3 「闪蒸罐直径」  D₀ = √(4 × 0.0673981 / π) = 0.292940 m = 293 mm
    B4 放大 0.292940 × 1.2 = 0.351528 m → 向上圆整 **φ400**
    B5 实际截面积 A′ = π/4 × 0.4² = 0.1256637 m²
       实际上升速度 u′ = 0.0402778 ÷ (0.597610 × 0.1256637) = 0.536337 m/s
       （= 手填 1.0 m/s ÷ 内径放大倍数 1.36547² ⇒ 53.6 %）
    B6 罐高 H = 0.4 × 2.0 = 0.800 m；筒体容积 V = 0.1256637 × 0.8 = 0.100531 m³
    B7 线性性：D_f 加倍 → m、A 加倍 → D₀ × √2
    B8 「闪蒸汽密度 = 1 ÷ 回收页密度」：手填 1/v_g 与自动值一致、无提示
    B9 若把那格填成**比容**（1.6733）→ 差 -99 %，给「是否取反了」提示
    B10 不圆整模式 → D = 0.351528，H = 0.703056
    B11 圆整函数：0.2929→0.3、0.3515→0.4、0.91→1.0、2.05→2.2、4.5→4.6

Part C  硬约束与提示（报错 / 警告）
    流速越界、保险系数越界、长径比越界 → 警告；
    误按 kg/h 填写 → 直径超常用系列 → 警告点名单位；
    直径过小 → 警告点名单位；压力越界 / 流速 ≤0 / 长径比越界 → 报错

Part D  计算链（喷射器 → 闪蒸 → 回收 → 闪蒸罐）
    D2 闪蒸汽量 kg/h → t/h（×0.001）；闪蒸压力 MPa → kPa（×1000）
    D3 蒸汽密度 ← 回收页「蒸汽密度」（本页新增登记项，= 1/比容）
    D4 一键取全链：两个上游页一起取、状态栏点名两页
    D5 同名键**上游优先**：下游桩页也发布「闪蒸压力」(kPa) 时仍取闪蒸页的 MPa
    D6 上游重算 → 「已过期」；D7 手改 → 标记消失；D8 clear → 解绑并回默认
    D9 本页不作为自己的上游；D10 CHAIN_ORDER 链序；D11 无上游 → 提示

Part E  契约
    generate_report() → str / get_project_info() → dict（5 标准键）
    _get_history_data() → {"inputs","outputs"}；clear 后可直接重算；
    已注册进导航与分类字典（工艺设备）

Part F  UI 健壮
    默认值直接算出结果且**无警告**；SVG 刷新不抛异常
════════════════════════════════════════════════════════════════════════
"""
import os
import sys
import math
import importlib.util

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CALC_DIR = os.path.join(ROOT, 'modules', 'chemical_calculations', 'calculators')
for p in [ROOT, os.path.join(ROOT, 'modules'),
          os.path.join(ROOT, 'modules', 'chemical_calculations')]:
    sys.path.insert(0, p)

from PySide6.QtWidgets import QApplication, QMessageBox          # noqa: E402


def _mk(_kind):
    def f(parent=None, title='', text='', *a, **k):
        return QMessageBox.StandardButton.Ok
    return staticmethod(f)


QMessageBox.warning = _mk('warning')
QMessageBox.critical = _mk('critical')
QMessageBox.information = _mk('info')

import tempfile                                                    # noqa: E402
from data_manager import DataManager                               # noqa: E402

DataManager.get_instance(data_file=os.path.join(tempfile.mkdtemp(), 'test.json'))

app = QApplication(sys.argv)

from chain_context import ChainContext                             # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


IAPWS = _load('steam_iapws',
              os.path.join(ROOT, 'modules', 'chemical_calculations', 'steam_iapws.py'))
TANK_M = _load('flash_tank', os.path.join(CALC_DIR, 'flash_tank_calculator.py'))
RC_M = _load('flash_rec', os.path.join(CALC_DIR, 'flash_steam_recovery_calculator.py'))
FL_M = _load('flash_evap', os.path.join(CALC_DIR, 'flash_evaporation_calculator.py'))
INJ_M = _load('inj_liq', os.path.join(CALC_DIR, 'injection_liquefier_calculator.py'))
T = TANK_M.FlashTankCalculator
RC = RC_M.FlashSteamRecoveryCalculator
FL = FL_M.FlashEvaporationCalculator
INJ = INJ_M.InjectionLiquefierCalculator

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}'
          + (f'  [{detail}]' if detail and not cond else ''))


def close(a, b, tol):
    return abs(a - b) <= tol


def mk():
    """新建一个罐页实例（每次都用全新的，避免相互污染）"""
    return T()


def sec(t):
    print('\n' + '─' * 68)
    print(t)
    print('─' * 68)


# ══════════════════════════════════════════════════════════════════
sec('Part A  物性锚点（IAPWS-IF97）')

sat = IAPWS.saturation_properties(P_MPa=0.101325)
V_G = sat['v_g']
RHO = 1.0 / V_G
check('A1 p=101.325 kPa 饱和温度 = 99.97 °C', close(sat['T_C'], 99.97, 0.05),
      f"{sat['T_C']:.4f}")
check('A2 饱和汽比容 v_g = 1.67333 m³/kg', close(V_G, 1.67333, 0.0005),
      f'{V_G:.6f}')
check('A3 ρ_g = 1/v_g = 0.597610 kg/m³', close(RHO, 0.597610, 0.0005),
      f'{RHO:.6f}')

# ══════════════════════════════════════════════════════════════════
sec('Part B  逐列对齐设计表格（默认参数）')

w = mk()
w.calculate()
r = w._last_result
check('B0 默认参数直接算出结果', bool(r), str(r.get('warn')))

M_ = 0.145 * 1000.0 / 3600.0
A_ = M_ / RHO / 1.0
D0_ = math.sqrt(4.0 * A_ / math.pi)
D_NEED_ = D0_ * 1.2
A_ACT_ = math.pi / 4.0 * 0.4 ** 2
U_ACT_ = M_ / (RHO * A_ACT_)

check('B1 闪蒸汽流量 m = 0.145×1000÷3600 = 0.0402778 kg/s',
      close(r['m_dot'], 0.040277778, 1e-9), f"{r['m_dot']:.9f}")
check('B1 同时回显 kg/h 口径 = 145.0 kg/h',
      close(r['m_kgh'], 145.0, 1e-9), f"{r['m_kgh']:.3f}")
check('B2 罐内截面积 A = m/ρ/u = 0.0673981 m²',
      close(r['A_calc'], 0.0673981, 1e-7), f"{r['A_calc']:.7f}")
check('B3 理论内径 D₀ = √(4A/π) = 0.292940 m（293 mm）',
      close(r['D0'], 0.292940, 1e-6), f"{r['D0']:.6f}")
check('B3 D₀ 独立复算一致', close(r['D0'], D0_, 1e-12), f'{D0_:.6f}')
check('B4 放大后内径 = D₀×1.2 = 0.351528 m',
      close(r['D_need'], 0.351528, 1e-6), f"{r['D_need']:.6f}")
check('B4 向上圆整 → 设计内径 φ400 mm',
      close(r['D'], 0.40, 1e-12) and r['do_round'] is True, f"{r['D']}")
check('B5 实际截面积 A′ = π/4×0.4² = 0.1256637 m²',
      close(r['A_act'], 0.1256637, 1e-7), f"{r['A_act']:.7f}")
check('B5 实际上升速度 u′ = 0.536337 m/s',
      close(r['u_act'], 0.536337, 1e-6), f"{r['u_act']:.6f}")
check('B5 u′ 独立复算一致', close(r['u_act'], U_ACT_, 1e-12), f'{U_ACT_:.6f}')
check('B5 u′ = u / 内径放大²（1.36547² ⇒ 53.6 %）',
      close(r['u_act'] / r['u'], 1.0 / (r['k_total'] ** 2), 1e-9),
      f"{r['u_act'] / r['u']:.6f} vs {1.0 / r['k_total'] ** 2:.6f}")
check('B5 内径总放大 = 0.4/0.292940 = 1.36547',
      close(r['k_total'], 1.365467, 1e-5), f"{r['k_total']:.6f}")
check('B6 罐高 H = 0.4×2.0 = 0.800 m', close(r['H'], 0.8, 1e-12), f"{r['H']}")
check('B6 筒体容积 V = 0.1256637×0.8 = 0.100531 m³',
      close(r['V'], 0.100531, 1e-6), f"{r['V']:.6f}")
check('B6 体积 = 实际截面积 × 罐高（口径一致）',
      close(r['V'], r['A_act'] * r['H'], 1e-12))
check('B6 结果区给出设备规格 φ400 × 800',
      'φ400 × 800' in w.result_text.toPlainText())

# B7 线性性
w2 = mk()
w2.df_input.setText('0.29')            # 加倍
w2.calculate()
r2 = w2._last_result
check('B7 D_f 加倍 → 质量流量加倍',
      close(r2['m_dot'], 2 * r['m_dot'], 1e-9), f"{r2['m_dot']:.9f}")
check('B7 D_f 加倍 → 截面积加倍',
      close(r2['A_calc'], 2 * r['A_calc'], 1e-9), f"{r2['A_calc']:.9f}")
check('B7 D_f 加倍 → 理论内径 × √2',
      close(r2['D0'], r['D0'] * math.sqrt(2), 1e-9), f"{r2['D0']:.6f}")

# B8 密度手填 = 1/回收页密度（表格口径）
w3 = mk()
w3.rho_input.setText(f'{RHO:.10g}')
w3.calculate()
r3 = w3._last_result
check('B8 手填密度 = 1/v_g（= 1÷回收页密度）→ 与自动一致',
      close(r3['rho_g'], RHO, 1e-9) and close(r3['A_calc'], r['A_calc'], 1e-9),
      f"{r3['A_calc']:.9f} vs {r['A_calc']:.9f}")
check('B8 密度自洽时不给「取反了」提示',
      not any('取反' in s for s in r3['warn']), str(r3['warn']))

# B9 填成比容 → 提示取反
w4 = mk()
w4.rho_input.setText(f'{V_G:.6f}')
w4.calculate()
r4 = w4._last_result
check('B9 密度填成比容(1.6733) → 提示核对/取反',
      any('取反' in s for s in r4['warn']), str(r4['warn']))
check('B9 仍按填值算（ρ 填成 1.6733 ⇒ 直径 ×√(ρ_g/1.6733) = 0.5976 倍）',
      close(r4['D0'] / r['D0'], math.sqrt(RHO / V_G), 1e-6),
      f"{r4['D0'] / r['D0']:.4f} vs {math.sqrt(RHO / V_G):.4f}")

# B10 不圆整
w5 = mk()
w5.round_mode.setCurrentIndex(1)
w5.calculate()
r5 = w5._last_result
check('B10 不圆整 → D = D_need = 0.351528 m',
      close(r5['D'], 0.351528, 1e-6) and r5['do_round'] is False, f"{r5['D']:.6f}")
check('B10 不圆整 → H = D×H/D = 0.703056 m',
      close(r5['H'], 0.351528 * 2.0, 1e-6), f"{r5['H']:.6f}")
check('B10 不圆整 → u′ = u/k² = 1/1.2² = 0.694444 m/s（保险单独作用）',
      close(r5['u_act'], 1.0 / 1.2 ** 2, 1e-6), f"{r5['u_act']:.6f}")

# B11 圆整函数
for src, exp in [(0.292940, 0.3), (0.351528, 0.4), (0.91, 1.0), (2.05, 2.2),
                 (4.5, 4.6), (0.29, 0.3), (4.0, 4.0)]:
    check(f'B11 圆整 {src} → {exp}',
          close(TANK_M.round_up_diameter(src), exp, 1e-9),
          str(TANK_M.round_up_diameter(src)))
check('B11 常用直径系列首项 0.30 / 末项 4.00',
      TANK_M.STD_DIAMETERS[0] == 0.30 and TANK_M.STD_DIAMETERS[-1] == 4.00,
      str(TANK_M.STD_DIAMETERS[:3]))
check('B11 系列严格递增',
      all(b > a for a, b in zip(TANK_M.STD_DIAMETERS, TANK_M.STD_DIAMETERS[1:])))

# ══════════════════════════════════════════════════════════════════
sec('Part C  硬约束与提示')

w6 = mk()
w6.u_input.setText('0.3')
w6.calculate()
check('C1 流速 0.3 低于常用下限 → 警告',
      any('低于常用下限' in s for s in w6._last_result['warn']),
      str(w6._last_result['warn']))

w7 = mk()
w7.u_input.setText('2.0')
w7.calculate()
check('C2 流速 2.0 高于常用上限 → 警告（雾沫夹带）',
      any('雾沫夹带' in s for s in w7._last_result['warn']),
      str(w7._last_result['warn']))

w8 = mk()
w8.k_input.setText('1.05')
w8.calculate()
wa = w8._last_result['warn']
check('C3 保险系数 1.05 越界 → 警告', any('保险系数' in s for s in wa), str(wa))
check('C3 圆整放大 30 % → 另给「档位跨度较大」提示',
      any('档位跨度较大' in s for s in wa), str(wa))

w9 = mk()
w9.ld_input.setText('1.0')
w9.calculate()
check('C4 长径比 1.0 越界 → 警告',
      any('长径比' in s for s in w9._last_result['warn']),
      str(w9._last_result['warn']))

w10 = mk()          # 误把 kg/h 当 t/h 填 → 直径大 31.6 倍
w10.df_input.setText('145')
w10.calculate()
r10 = w10._last_result
check('C5 闪蒸汽量误按 kg/h 填 145 → 直径超 4000 mm 系列',
      r10['D'] > 4.0, f"{r10['D']:.2f}")
check('C5 警告点名单位（t/h 口径）',
      any('单位' in s and 't/h' in s for s in r10['warn']), str(r10['warn']))
check('C5 仍给出结果（不静默、不报错）', bool(r10.get('D')))

w11 = mk()          # 极小流量 → 直径过小提示
w11.df_input.setText('0.0001')
w11.calculate()
check('C6 闪蒸汽量 0.0001 t/h → 直径过小警告（点名单位）',
      any('过小' in s for s in w11._last_result['warn']),
      str(w11._last_result['warn']))

w12 = mk()          # 保险系数过大 → 气速折半以上
w12.k_input.setText('1.8')
w12.calculate()
check('C10 保险系数 1.8 → 气速降到 50 % 以下 → 警告',
      any('平方' in s for s in w12._last_result['warn']),
      str(w12._last_result['warn']))

# 报错类
errs = [('压力越界', 'p_input', '3000', '压力'),
        ('流速为 0', 'u_input', '0', '流速'),
        ('长径比过小', 'ld_input', '0.2', '长径比'),
        ('保险系数 <1', 'k_input', '0.9', '保险系数')]
for label, attr, val, kw in errs:
    wx = mk()
    getattr(wx, attr).setText(val)
    wx.calculate()
    txt = wx.result_text.toPlainText()
    check(f'C7 报错：{label}',
          txt.startswith('错误：') and kw in txt, txt[:60])

wx = mk()
wx.df_input.setText('0')
wx.calculate()
check('C7 报错：闪蒸汽量为 0',
      wx.result_text.toPlainText().startswith('错误：'),
      wx.result_text.toPlainText()[:40])

# ══════════════════════════════════════════════════════════════════
sec('Part D  计算链（喷射器 → 闪蒸 → 回收 → 闪蒸罐）')

ChainContext.clear()

# 上游 1：喷射液化器
inj = INJ()
inj.calculate()
check('D1 喷射器已登记', ChainContext.has('injection_liquefier_calculator'))

# 上游 2：闪蒸降温浓缩
wf = FL()
wf.calculate()
flash_entry = ChainContext.get('flash_evaporation_calculator')
check('D1 闪蒸页登记含「闪蒸汽量」(kg/h) 与「闪蒸压力」(MPa)',
      flash_entry is not None
      and '闪蒸汽量' in flash_entry['values']
      and '闪蒸压力' in flash_entry['values'],
      str((flash_entry or {}).get('values')))
check('D1 闪蒸压力是 MPa 口径（0.001~1.0）',
      0.001 < flash_entry['values']['闪蒸压力'] < 1.0,
      str(flash_entry['values'].get('闪蒸压力')))

# 上游 3：闪蒸蒸汽回收
wr = RC()
wr.chain_combo.setCurrentIndex(0)          # 整链一键取全
wr._apply_chain_source()
wr.calculate()
rec_entry = ChainContext.get('flash_steam_recovery_calculator')
check('D3 回收页新增登记「蒸汽密度」(kg/m³) 与「蒸汽比容」(m³/kg)',
      rec_entry is not None
      and '蒸汽密度' in rec_entry['values'] and '蒸汽比容' in rec_entry['values'],
      str((rec_entry or {}).get('values')))
check('D3 蒸汽密度 = 1 ÷ 蒸汽比容',
      close(rec_entry['values']['蒸汽密度'],
            1.0 / rec_entry['values']['蒸汽比容'], 1e-9))
check('D3 回收页原有的 4 项输出仍在（未被破坏）',
      all(k in rec_entry['values'] for k in
          ('回收热量', '凝结水量', '可加热物料量', '蒸汽体积')),
      str(sorted(rec_entry['values'])))

# 罐页取上游
wt = mk()
wt._reload_chain_sources()
items = [wt.chain_combo.itemText(i) for i in range(wt.chain_combo.count())]
check('D2 下拉列出三个上游页',
      all(any(n in s for s in items) for n in
          ('喷射液化器', '闪蒸降温浓缩', '闪蒸蒸汽回收')), str(items))
check('D9 下拉不含本页自己',
      not any('闪蒸罐' in s for s in items), str(items))

wt.chain_combo.setCurrentIndex(0)          # 整链一键取全
wt._apply_chain_source()
fv = flash_entry['values']
check('D2 闪蒸汽量 ← 闪蒸页 kg/h → 本页 t/h（×0.001）',
      close(float(wt.df_input.text()), fv['闪蒸汽量'] * 0.001, 1e-9),
      f"{wt.df_input.text()} vs {fv['闪蒸汽量'] * 0.001}")
check('D2 闪蒸压力 ← 闪蒸页 MPa → 本页 kPa（×1000）',
      close(float(wt.p_input.text()), fv['闪蒸压力'] * 1000.0, 1e-6),
      wt.p_input.text())
check('D3 蒸汽密度 ← 回收页「蒸汽密度」',
      close(float(wt.rho_input.text()), rec_entry['values']['蒸汽密度'], 1e-9),
      wt.rho_input.text())
marks = {k: v[2].text() for k, v in wt._rows.items() if v[0] is not None}
check('D2 三行都打「←上游」标记（df/p/rho）',
      all('←上游' in marks[k] for k in ('df', 'p', 'rho')), str(marks))
check('D4 状态栏点名两个来源页',
      '闪蒸降温浓缩' in wt.chain_status.text()
      and '闪蒸蒸汽回收' in wt.chain_status.text(), wt.chain_status.text())
check('D4 明细显示字段归属',
      '闪蒸汽量←' in wt.chain_status.text()
      and '蒸汽密度←' in wt.chain_status.text(), wt.chain_status.text())

wt.calculate()
check('D4 取上游后结果区标注计算链来源',
      '【计算链来源】' in wt.result_text.toPlainText())
check('D4 取上游后计算结果与「同一组数手填」一致',
      close(wt._last_result['m_dot'], float(wt.df_input.text()) * 1000 / 3600, 1e-12))

# D5 同名键上游优先
ChainContext.publish('zzz_stub_page', '桩页（下游）',
                     values={'闪蒸压力': 101.325},
                     units={'闪蒸压力': 'kPa'})
wt._reload_chain_sources()
wt.chain_combo.setCurrentIndex(0)
wt._apply_chain_source()
check('D5 同名键上游优先：闪蒸压力仍取闪蒸页(MPa→kPa)，不被下游桩页覆盖',
      close(float(wt.p_input.text()), fv['闪蒸压力'] * 1000.0, 1e-6),
      f"{wt.p_input.text()}（若被桩页覆盖会是 101.325）")
ChainContext.clear_page('zzz_stub_page')

# D6 上游重算 → 过期
wf.tout_input.setText('98')
wf.calculate()
wt._reload_chain_sources()
wt._refresh_chain_status()
check('D6 上游重算后 → 提示「已过期」/「已重算」',
      '已重算' in wt.chain_status.text(), wt.chain_status.text())

# D7 手改 → 标记消失
wt._reload_chain_sources()
wt.chain_combo.setCurrentIndex(0)
wt._apply_chain_source()
wt.df_input.setText('0.2')
wt.df_input.textEdited.emit('0.2')
check('D7 手改输入 → 该行标记消失',
      '←上游' not in wt._rows['df'][2].text(), wt._rows['df'][2].text())
check('D7 其余行标记不受影响',
      '←上游' in wt._rows['rho'][2].text(), wt._rows['rho'][2].text())

# D8 clear → 解绑并回默认
wt.clear_inputs()
check('D8 clear 后闪蒸汽量回默认 0.145', wt.df_input.text() == '0.145',
      wt.df_input.text())
check('D8 clear 后密度回空（恢复自动查表）', wt.rho_input.text() == '',
      wt.rho_input.text())
check('D8 clear 后引用清空、状态行清空',
      wt._chain_refs == [] and wt.chain_status.text() == '')

# D11 无上游
ChainContext.clear()
wt2 = mk()
wt2.chain_combo.setCurrentIndex(0)
wt2._apply_chain_source()
check('D11 无可用上游 → 提示去上游页点计算',
      '没有可用上游' in wt2.chain_status.text(), wt2.chain_status.text())

check('D10 CHAIN_ORDER 链序：喷射器 < 闪蒸 < 回收 < 闪蒸罐',
      ChainContext.CHAIN_ORDER.index('injection_liquefier_calculator')
      < ChainContext.CHAIN_ORDER.index('flash_evaporation_calculator')
      < ChainContext.CHAIN_ORDER.index('flash_steam_recovery_calculator')
      < ChainContext.CHAIN_ORDER.index('flash_tank_calculator'),
      str(ChainContext.CHAIN_ORDER))

# 罐页自身登记
ChainContext.clear()
wt3 = mk()
wt3.calculate()
tank_entry = ChainContext.get('flash_tank_calculator')
check('D12 罐页登记 5 项输出（直径/高度/体积/截面积/气速）',
      tank_entry is not None
      and all(k in tank_entry['values'] for k in
              ('闪蒸罐直径', '闪蒸罐高度', '闪蒸罐体积', '罐内截面积',
               '蒸汽上升速度')),
      str((tank_entry or {}).get('values')))
check('D12 登记直径 = 计算结果 0.4 m',
      close(tank_entry['values']['闪蒸罐直径'], wt3._last_result['D'], 1e-12))
check('D12 备注含规格 φ400×800',
      'φ400×800' in tank_entry['note'], tank_entry['note'])

# ══════════════════════════════════════════════════════════════════
sec('Part E  契约')

wp = mk()
check('E2 未计算 → generate_report() 返回 None', wp.generate_report() is None)
wp.calculate()
rep = wp.generate_report()
check('E1 generate_report() → str', isinstance(rep, str))
check('E1 计算书含标题与公式段',
      '闪蒸罐计算书' in rep and 'D₀ = √( 4A / π )' in rep)
info = wp.get_project_info()
check('E3 get_project_info() → dict 且 5 个标准键',
      isinstance(info, dict)
      and {'company_name', 'project_number', 'project_name',
           'subproject_name', 'calculation_type'} <= set(info), str(info))
check('E3 calculation_type = 闪蒸罐计算',
      info.get('calculation_type') == '闪蒸罐计算')

hd = wp._get_history_data()
check('E4 _get_history_data() → inputs/outputs 非空',
      isinstance(hd, dict) and hd.get('inputs') and hd.get('outputs'), str(hd)[:80])
check('E4 历史输出含设计内径',
      '设计内径_m' in hd['outputs'], str(list(hd['outputs'])))
check('E4 历史输入含数据来源',
      '数据来源' in hd['inputs'], str(list(hd['inputs'])))

wq = mk()
wq.u_input.setText('1.3')
wq.calculate()
first = dict(wq._last_result)
wq.clear_inputs()
wq.calculate()
check('E5 clear 后可直接重算且回到默认结果',
      close(wq._last_result['D'], first['D'] * 0 + 0.4, 1e-12)
      and close(wq._last_result['u'], 1.0, 1e-12),
      f"{wq._last_result['D']}")

W_M = _load('ccw', os.path.join(ROOT, 'modules', 'chemical_calculations',
                               'chemical_calculations_widget.py'))
check('E6 已注册进分类字典（工艺设备）',
      W_M.ChemicalCalculationsWidget._CALC_CATEGORIES.get(
          'flash_tank_calculator') == '工艺设备',
      str(W_M.ChemicalCalculationsWidget._CALC_CATEGORIES.get(
          'flash_tank_calculator')))
check('E6 类名与模块名匹配（动态加载契约）',
      getattr(TANK_M, 'flash_tank_calculator', None) is T,
      str(getattr(TANK_M, 'flash_tank_calculator', None)))
check('E6 CHAIN_MODULE 与文件名一致',
      T.CHAIN_MODULE == 'flash_tank_calculator', T.CHAIN_MODULE)

# ══════════════════════════════════════════════════════════════════
sec('Part F  UI 健壮')

wu = mk()
check('F2 构造后控件可访问', not isinstance(wu.df_input.text(), type(None)))
check('F2 密度留空 + 占位提示', wu.rho_input.text() == ''
      and '自动' in wu.rho_input.placeholderText(), wu.rho_input.placeholderText())
wu.calculate()
check('F1 默认值算出结果且**无警告**', wu._last_result['warn'] == [],
      str(wu._last_result['warn']))
wu._update_svg_diagram()
check('F3 默认工况 SVG 是合法 XML（renderer 可用）',
      wu.svg_widget.renderer().isValid(), 'invalid svg')
svg_ok, svg_txt = True, ''
try:
    wv = mk()
    wv.calculate()
    wv._update_svg_diagram()
    captured = {}
    _orig = wv.svg_widget.load
    wv.svg_widget.load = lambda b: captured.setdefault('svg', b)
    wv.df_input.setText('0.4')
    wv.calculate()
    wv._update_svg_diagram()
    wv.svg_widget.load = _orig
    svg_txt = captured.get('svg', b'').decode('utf-8')
except Exception as e:                                            # noqa: BLE001
    svg_ok = False
    print('   SVG 异常:', e)
check('F3 换工况后 SVG 刷新不抛异常', svg_ok)
check('F3 SVG 含罐体 / 去向层流罐 / 规格标注（0.4 t/h ⇒ φ600）',
      all(k in svg_txt for k in ('闪蒸罐', '层流罐', 'φ600')), svg_txt[:80])
check('F4 结果区含「层流罐」去向说明（本页不算停留时间）',
      '层流罐' in wv.result_text.toPlainText())

# ══════════════════════════════════════════════════════════════════
print('\n' + '=' * 68)
print(f'共 {len(PASS) + len(FAIL)} 项，通过 {len(PASS)}，失败 {len(FAIL)}')
if FAIL:
    print('\n失败清单：')
    for n, d in FAIL:
        print(f'  ✗ {n}  {d}')
sys.exit(1 if FAIL else 0)
