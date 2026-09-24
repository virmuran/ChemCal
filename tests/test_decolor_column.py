# -*- coding: utf-8 -*-
"""脱色柱计算（活性炭柱与酸洗再生）回归测试

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_decolor_column.py

核对依据（照片 = 公司工艺工作簿「13.脱色」页「中脱单套」口径）
════════════════════════════════════════════════════════════════════════
默认输入：φ3.5×6.5、6 柱、装填率 66%、堆密度 0.5、净密度 1.12、
Q=27.5 m³/h、持液率 40%、C₀=60%、C_t=0.30%、N=7、V_w 留空、
配酸 M=100/C_x=0/C_y=60/C_a=98

Part A  柱体与装炭（手算锚点）
    A1 直筒体积(单柱) = π/4×3.5²×6.5 = 62.5373 m³（照片值 62.5 ✓）
    A2 床层体积(单柱) = 62.5373×0.66 = 41.2746 m³
    A3 装炭体积       = 41.2746×6 = 247.6478 m³
    A4 装炭重量       = 247.6478×0.5 = 123.8239 t
    A5 空隙率 ε = 1 − 0.5/1.12 = 0.553571（照片 195.33×1.12=218.77 的正解）
    A6 线性性：柱数 ×2 → 装炭体积/重量 ×2
    A7 净密度留空 → ε = None 不参与

Part B  接触时间
    B1 t = 41.2746/27.5 = 1.5009 h（原表照片值 1.5 H ✓）
    B2 判据：Q 加大 4 倍 → t=0.375 h < 30 min → 警告

Part C  酸洗递推（混合-置换模型）
    C1 反算 V_w：k = (0.30/60)^(1/7) = 0.469117
       V_w = 99.0591×(1/k−1) = 112.1016 m³/次
    C2 C_end = 60×k^7 = 0.30 % 精确
    C3 逐次严格递减；C_i = C_(i-1)×k
    C4 酸量衡算闭合：Σ C_i·V_w = (C₀−C_end)·V_r（1e-9）
    C5 混合酸度 = (C₀−C_end)·V_r/(N·V_w) = 7.5363 %
    C6 手填 V_w=100 → k=0.497661、C_end≈0.454% > 目标 → 警告点名

Part D  洗水分流（1 / 2~3 / 4~N）
    D1 三股、次数 1/2/4；D2 各股体积 = 次数×V_w；D3 酸量合计 = 总带出量

Part E  投酸（配酸）
    E1 M_a = 100×(60−0)/(98−60) = 157.8947 t
    E2 配酸后总量 = 257.8947 t；E3 线性：M×2 → M_a×2

Part F  硬约束
    C_t ≥ C₀ / C_a ≤ C_y / V_w≤0 / 柱数 0 → 报错

Part G  契约与 UI
    generate_report() → str / get_project_info() → dict（5 标准键）
    _get_history_data() → {"inputs","outputs"}；clear 后可直接重算；
    已注册进导航与分类字典（工艺设备）；SVG 刷新不抛异常；
    计算链 publish：ChainContext.get 本页含「装炭重量」
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

spec = importlib.util.spec_from_file_location(
    'decolor', os.path.join(CALC_DIR, 'decolorization_column_calculator.py'))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
DC = M.DecolorizationCalculator

FAILED = 0


def check(name, cond, detail=''):
    global FAILED
    mark = 'PASS' if cond else 'FAIL'
    print(f'{mark}  {name}' + (f'   [{detail}]' if detail and not cond else ''))
    if not cond:
        FAILED += 1


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(b))


def mk(**over):
    w = DC()
    defaults = dict(d='3.5', h='6.5', n='6', f='66', rb='0.5', rt='1.12',
                    q='27.5', w='40', c0='60', ct='0.30', nw='7', vw='',
                    m='100', cx='0', cy='60', ca='98')
    defaults.update(over)
    for k, v in defaults.items():
        getattr(w, f'{k}_input').setText(str(v))
    return w


# ── Part A 柱体与装炭 ─────────────────────────────────────────────────
print('Part A  柱体与装炭')
w = mk()
w.calculate()
r = w._last_result
check('A0 默认值算出结果且无警告', r and r['warn'] == [], str(r.get('warn')))
check('A1 直筒体积(单柱) = π/4×3.5²×6.5 = 62.5373 m³（照片 62.5）',
      close(r['V_cyl'], math.pi / 4 * 3.5 ** 2 * 6.5, 1e-12)
      and close(r['V_cyl'], 62.5373, 1e-4), f"{r['V_cyl']:.6f}")
check('A2 床层体积 = ×0.66 = 41.2746 m³',
      close(r['V_bed'], r['V_cyl'] * 0.66, 1e-12), f"{r['V_bed']:.6f}")
check('A3 装炭体积 = ×6 = 247.6478 m³',
      close(r['V_ac'], r['V_bed'] * 6, 1e-12), f"{r['V_ac']:.6f}")
check('A4 装炭重量 = ×0.5 = 123.8239 t',
      close(r['W_ac'], r['V_ac'] * 0.5, 1e-12), f"{r['W_ac']:.6f}")
check('A5 空隙率 ε = 1−0.5/1.12 = 0.553571',
      close(r['eps'], 1 - 0.5 / 1.12, 1e-12), f"{r['eps']:.7f}")

w2 = mk(n='12')
w2.calculate()
r2 = w2._last_result
check('A6 线性性：柱数 ×2 → 装炭体积/重量 ×2',
      close(r2['V_ac'], r['V_ac'] * 2, 1e-12)
      and close(r2['W_ac'], r['W_ac'] * 2, 1e-12))

w3 = mk(rt='')
w3.calculate()
check('A7 净密度留空 → ε 不算（None）且无警告',
      w3._last_result['eps'] is None
      and w3._last_result['warn'] == [])

# ── Part B 接触时间 ───────────────────────────────────────────────────
print('Part B  接触时间')
check('B1 t = 41.2746/27.5 = 1.5009 h（原表 1.5 H）',
      close(r['t_contact'], r['V_bed'] / 27.5, 1e-12)
      and close(r['t_contact'], 1.5009, 1e-4), f"{r['t_contact']:.6f}")
w4 = mk(q='110')
w4.calculate()
r4 = w4._last_result
check('B2 t=0.375 h < 30 min → 警告点名判据',
      close(r4['t_contact'], 0.375, 1e-3)
      and any('30 min' in x for x in r4['warn']), str(r4['warn']))

# ── Part C 酸洗递推 ───────────────────────────────────────────────────
print('Part C  酸洗递推')
K = (0.30 / 60.0) ** (1.0 / 7.0)
check('C1 反算 V_w：k=0.469117、V_w = V_r×(1/k−1) = 112.1016 m³',
      close(r['k_ratio'], K, 1e-12)
      and close(r['V_r'], r['V_ac'] * 0.40, 1e-12)
      and close(r['Vw'], r['V_r'] * (1 / K - 1), 1e-12)
      and close(r['Vw'], 112.1016, 1e-4),
      f"k={r['k_ratio']:.7f} Vw={r['Vw']:.4f}")
check('C2 洗完残液酸度 = 60×k^7 = 0.30 % 精确',
      close(r['C_end'], 0.30, 1e-9), f"{r['C_end']:.9f}")
cl = r['C_list']
check('C3 逐次严格递减且 C_i = C_(i-1)×k',
      all(cl[i] < cl[i - 1] for i in range(1, len(cl)))
      and all(close(cl[i], cl[i - 1] * K, 1e-12) for i in range(1, len(cl))))
acid_sum = sum(c / 100.0 * r['Vw'] for c in cl)
check('C4 酸量衡算闭合 Σ C_i·V_w = (C₀−C_end)·V_r',
      close(acid_sum, r['acid_out_total'], 1e-9)
      and close(r['acid_out_total'], (60.0 - 0.30) / 100.0 * r['V_r'], 1e-9),
      f"{acid_sum:.6f} vs {r['acid_out_total']:.6f}")
check('C5 混合酸度 = (C₀−C_end)·V_r/(N·V_w) = 7.5363 %',
      close(r['C_mix'], (60.0 - 0.30) * r['V_r'] / (7 * r['Vw']), 1e-12)
      and close(r['C_mix'], 7.5363, 1e-4), f"{r['C_mix']:.6f}")
w5 = mk(vw='100')
w5.calculate()
r5 = w5._last_result
k5 = r5['V_r'] / (r5['V_r'] + 100.0)
check('C6 手填 V_w=100 → C_end=60×k^7≈0.454% > 目标 → 警告',
      close(r5['k_ratio'], k5, 1e-12) and r5['C_end'] > 0.30
      and close(r5['C_end'], 60.0 * k5 ** 7, 1e-9)
      and any('增大每次洗水量' in x for x in r5['warn']),
      f"C_end={r5['C_end']:.5f} warn={r5['warn']}")

# ── Part D 洗水分流 ───────────────────────────────────────────────────
print('Part D  洗水分流')
sp = r['split']
check('D1 N=7 → 三股、次数 1/2/4',
      len(sp) == 3 and [s['count'] for s in sp] == [1, 2, 4],
      str([s['count'] for s in sp]))
check('D2 各股体积 = 次数×V_w',
      all(close(s['vol'], s['count'] * r['Vw'], 1e-9) for s in sp))
check('D3 酸量合计 = 总带出量（衡算闭合）',
      close(sum(s['acid'] for s in sp), r['acid_out_total'], 1e-9))
check('D4 平均酸度逐股递减（先浓后稀）',
      sp[0]['c_avg'] > sp[1]['c_avg'] > sp[2]['c_avg'])

# ── Part E 投酸（配酸）────────────────────────────────────────────────
print('Part E  投酸（配酸）')
check('E1 M_a = 100×(60−0)/(98−60) = 157.8947 t',
      close(r['Ma'], 100.0 * 60.0 / 38.0, 1e-12)
      and close(r['Ma'], 157.8947, 1e-4), f"{r['Ma']:.6f}")
check('E2 配酸后总量 = 257.8947 t',
      close(r['M_total'], 100.0 + r['Ma'], 1e-12))
w6 = mk(m='200')
w6.calculate()
check('E3 线性：M×2 → M_a×2',
      close(w6._last_result['Ma'], r['Ma'] * 2, 1e-12))

# ── Part F 硬约束 ─────────────────────────────────────────────────────
print('Part F  硬约束')


def expect_error(**over):
    wx = mk(**over)
    wx.calculate()
    return (not wx._last_result)
    # _show_error 清空 _last_result


check('F1 C_t ≥ C₀ → 报错', expect_error(ct='60'))
check('F2 C_a ≤ C_y → 报错', expect_error(ca='50'))
check('F3 每次洗水量 ≤0 → 报错', expect_error(vw='0'))
check('F4 柱数量 <1 → 报错', expect_error(n='0'))

# ── Part G 契约与 UI ──────────────────────────────────────────────────
print('Part G  契约与 UI')
rep = w.generate_report()
check('G1 generate_report() → str（含标题与工程信息）',
      isinstance(rep, str) and '脱色柱计算' in rep and '工程信息' in rep)
info = w.get_project_info()
check('G2 get_project_info() → 5 个标准键',
      isinstance(info, dict)
      and set(info) == {'company_name', 'project_number', 'project_name',
                        'subproject_name', 'calculation_type'}
      and info['calculation_type'] == '脱色柱计算')
hd = w._get_history_data()
check('G3 _get_history_data() → inputs/outputs 且非空',
      isinstance(hd, dict) and hd.get('inputs') and hd.get('outputs'))
w.clear_inputs()
w.calculate()
check('G4 clear 后可直接重算（默认锚点仍在）',
      close(w._last_result['V_cyl'], 62.5373, 1e-4)
      and w._last_result['warn'] == [])
try:
    w._update_svg_diagram()
    svg_ok = True
except Exception as e:                                            # noqa: BLE001
    svg_ok = False
    print('   SVG 异常:', e)
check('G5 SVG 刷新不抛异常', svg_ok)
try:
    from chain_context import ChainContext                        # noqa: E402
    entry = ChainContext.get('decolorization_column_calculator')
    ok_chain = bool(entry) and '装炭重量' in (entry.get('values') or {})
except Exception:                                                 # noqa: BLE001
    ok_chain = False
check('G6 计算链已登记（含装炭重量）', ok_chain)

# ── 汇总 ─────────────────────────────────────────────────────────────
total = 7 + 2 + 6 + 4 + 3 + 4 + 6
print(f'\n共 {total} 项，通过 {total - FAILED}，失败 {FAILED}')
sys.exit(1 if FAILED else 0)
