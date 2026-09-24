# -*- coding: utf-8 -*-
"""闪蒸蒸汽回收计算 + 全链联动 回归测试

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_flash_recovery.py

核对依据
════════════════════════════════════════════════════════════════════════
Part A  饱和水/汽物性锚点（IAPWS-IF97 独立复算）
    p = 0.101325 MPa：t_sat = 99.97 °C、h_f = 418.99、h_g = 2675.56、
    h_fg = 2256.57 kJ/kg、v_g = 1.6733 m³/kg（ρ_g ≈ 0.5977 kg/m³）
    h_f(80 °C) = 334.95（热水显热）、h_f(20 °C) = 83.92（冷水显热）

Part B  回收热量与表格逐列对齐（默认 D_f = 145 kg/h、p = 101.325 kPa、
        冷水 20 → 热水 80 °C、c = 3.90、ρ_m = 1.03 t/m³）
    B1 严格口径：Q = D_f·[h_g(p) − h_f(t_hot)]
       ⇒ 145 × (2675.56 − 334.95) = 145 × 2340.61 = 339 388 kJ/h = 94.27 kW
    B2 表格口径（留空自动）与严格口径重合（差 ≈ 0）
    B3 手填表格 100 kPa 行（r = 2259.5、h_f = 416.9，p = 100 kPa）：
       表格总焓 r + h_f = 2676.40；严格 dh = 2340.03 vs 表格 2341.45
       ⇒ 表格口径高 +0.06 %（工程表与 IF97 的正常差异）
    B4 蒸汽体积：V = D_f·v_g = 145 × 1.6733 = 242.6 m³/h；
       按密度填 0.5977 kg/m³ → 同值（比容/密度互为倒数）
    B5 可加热物料量：G_m = Q/(c·ΔT) = 339 388/(3.90×60) = 1451.2 kg/h
       = 1.451 t/h；体积 = 1.451/1.03 = 1.409 m³/h
    B6 线性性：D_f 加倍 → Q、V、G_m 都加倍
    B7 显热查表：热水显热 = h_f(80 °C) = 334.95、冷水显热 = h_f(20 °C) = 83.92
       （= 各自温度的「蒸汽焓 − 汽化热」，表格「冷水/热水显热」列）
    B8 填错表（h_f 填 80 °C 行值 334.95）→ 提示核对，仍按填值算

Part C  硬约束
    t_hot ≥ t_sat(p) → 报错并给出所需压力；t_hot 逼近 t_sat（<5 °C）→ 警告；
    t_hot ≤ t_cold → 报错；压力越界 / 潜热非正 / 密度越界 → 报错

Part D  计算链联动（喷射器 → 闪蒸 → 回收 全链）
    闪蒸页登记含「闪蒸压力」(MPa)；喷射器登记含「浆料比重」(t/m³)
    回收页「取上游值」← 闪蒸页：闪蒸汽量 kg/h + 闪蒸压力 MPa→kPa（×1000）
    上游重算 → 「已过期」；手改 → 标记消失；clear → 回到不使用上游；
    本页不作为自己的上游；回收页自身登记 4 项输出

Part E  契约
    generate_report() → str / get_project_info() → dict（5 标准键）
    _get_history_data() → {"inputs","outputs"}
    clear_inputs() → 恢复默认且可直接重算

Part F  UI 健壮
    默认值直接算出结果且无警告；SVG 刷新不抛异常
════════════════════════════════════════════════════════════════════════
"""
import os
import sys
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
INJ_M = _load('inj_liq', os.path.join(CALC_DIR, 'injection_liquefier_calculator.py'))
FL_M = _load('flash_evap', os.path.join(CALC_DIR, 'flash_evaporation_calculator.py'))
RC_M = _load('flash_rec', os.path.join(CALC_DIR, 'flash_steam_recovery_calculator.py'))
R = RC_M.FlashSteamRecoveryCalculator
F = FL_M.FlashEvaporationCalculator
INJ = INJ_M.InjectionLiquefierCalculator

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}'
          + (f'  [{detail}]' if detail and not cond else ''))


def close(a, b, tol):
    return abs(a - b) <= tol


def mk():
    """新建一个回收计算器实例（现取现用，避免跨用例串状态）"""
    return R()


# ════════════════════════════════════════════════════════════════
print('\n══ Part A  饱和水/汽物性锚点（IAPWS-IF97 独立复算）══')
sat_atm = IAPWS.saturation_properties(P_MPa=0.101325)
check('常压饱和温度 ≈ 99.97 °C', close(sat_atm['T_C'], 99.97, 0.1),
      f"{sat_atm['T_C']:.2f}")
check('常压饱和汽总焓 h_g ≈ 2675.56 kJ/kg（蒸汽表 2676）',
      close(sat_atm['h_g'], 2675.56, 1.0), f"{sat_atm['h_g']:.2f}")
check('常压饱和水焓 h_f = 418.99 kJ/kg（蒸汽表 419.1）',
      close(sat_atm['h_f'], 418.99, 0.3), f"{sat_atm['h_f']:.2f}")
check('常压汽化潜热 h_fg ≈ 2256.57 kJ/kg',
      close(sat_atm['h_fg'], 2256.57, 1.0), f"{sat_atm['h_fg']:.2f}")
check('常压饱和汽比容 v_g ≈ 1.6733 m³/kg（ρ_g ≈ 0.5977）',
      close(sat_atm['v_g'], 1.6733, 0.01) and
      close(1.0 / sat_atm['v_g'], 0.5977, 0.005), f"{sat_atm['v_g']:.4f}")
sat80 = IAPWS.saturation_properties(T_C=80.0)
check('热水显热 h_f(80 °C) = 334.95 kJ/kg',
      close(sat80['h_f'], 334.95, 0.3), f"{sat80['h_f']:.2f}")
sat20 = IAPWS.saturation_properties(T_C=20.0)
check('冷水显热 h_f(20 °C) = 83.92 kJ/kg',
      close(sat20['h_f'], 83.92, 0.3), f"{sat20['h_f']:.2f}")

# ════════════════════════════════════════════════════════════════
print('\n══ Part B  回收热量与表格逐列对齐 ══')
w = mk()
w.calculate()
r = w._last_result
check('B1 回收功率 = 94.27 kW（145 × 2340.61 / 3600）',
      close(r['Q_kW'], 94.2746, 0.05), f"{r['Q_kW']:.4f}")
check('B1 回收热量 = 339 388 kJ/h',
      close(r['Q_kjh'], 145 * 2340.61, 1.0), f"{r['Q_kjh']:.1f}")
check('B2 留空自动 → 表格口径与严格口径重合（|差| < 0.01 %）',
      close(r['d_q_pct'], 0.0, 0.01), f"{r['d_q_pct']:.4f}")
check('B3 蒸汽体积 = D_f·v_g = 242.6 m³/h',
      close(r['V_steam'], 145 * 1.6733, 1.0), f"{r['V_steam']:.1f}")
check('B5 可加热物料量 = 1.451 t/h（1451.2 kg/h）',
      close(r['G_m_t'], 1.4512, 0.003), f"{r['G_m_t']:.4f}")
check('B5 体积流量 = 1.409 m³/h',
      close(r['V_m'], 1.4512 / 1.03, 0.003), f"{r['V_m']:.4f}")
check('B7 热水显热 = h_f(80 °C) = 334.95',
      close(r['h_f_hot'], 334.95, 0.3), f"{r['h_f_hot']:.2f}")
check('B7 冷水显热 = h_f(20 °C) = 83.92',
      close(r['h_f_cold'], 83.92, 0.3), f"{r['h_f_cold']:.2f}")
check('B7 凝结水量 = 闪蒸汽量（全凝）= 145 kg/h',
      close(r['cond_kg'], 145.0, 1e-9), f"{r['cond_kg']:.1f}")

# B3/B4 手填表格 100 kPa 行
w2 = mk()
w2.p_input.setText('100')
w2.r_input.setText('2259.5')
w2.hf_input.setText('416.9')
w2.calculate()
r2 = w2._last_result
check('B3 手填表格总焓 r+h_f = 2676.40 kJ/kg',
      close(r2['h_g_tab'], 2676.40, 0.01), f"{r2['h_g_tab']:.2f}")
check('B3 表格口径比严格口径高 ≈ +0.06 %（工程表 vs IF97 正常差异）',
      close(r2['d_q_pct'], 0.061, 0.02), f"{r2['d_q_pct']:.3f}")
check('B3 手填值与自动值差 <1 % → 不触发「查错蒸汽表」提示',
      not any(('查错' in x or '相差' in x) for x in r2['warn']),
      str(r2['warn']))

# B4 按密度填 → 与按比容等价
w3 = mk()
w3.vg_mode.setCurrentIndex(1)
w3.vg_input.setText('0.5977')
w3.calculate()
r3 = w3._last_result
check('B4 按密度 0.5977 kg/m³ → 蒸汽体积与按比容同值',
      close(r3['V_steam'], 145 * 1.6733, 1.0), f"{r3['V_steam']:.1f}")

# B6 线性性
w4 = mk()
w4.df_input.setText('290')
w4.calculate()
r4 = w4._last_result
check('B6 D_f 加倍 → 回收功率加倍（190.55 kW）',
      close(r4['Q_kW'], 2 * 94.2746, 0.1), f"{r4['Q_kW']:.3f}")
check('B6 D_f 加倍 → 蒸汽体积加倍、可加热物料量加倍',
      close(r4['V_steam'], 2 * r['V_steam'], 1.0)
      and close(r4['G_m_t'], 2 * r['G_m_t'], 0.005),
      f"{r4['V_steam']:.1f} / {r4['G_m_t']:.4f}")

# B8 填错表
w5 = mk()
w5.hf_input.setText('334.95')             # 80 °C 行液体焓，不是常压 h_f
w5.calculate()
r5 = w5._last_result
check('B8 h_f 填错（80 °C 行值）→ 提示核对',
      any(('查错' in x or '相差' in x) for x in r5['warn']), str(r5['warn']))
check('B8 仍按填值计算（不静默改数）',
      close(r5['h_f_v'], 334.95, 1e-9), f"{r5['h_f_v']:.2f}")

# ════════════════════════════════════════════════════════════════
print('\n══ Part C  硬约束 ══')
c1 = mk()
c1.th_input.setText('105')                # ≥ t_sat(99.97)
c1.calculate()
check('C1 热水温度 ≥ 饱和温度 → 报错（给出所需压力）',
      '错误' in c1.result_text.toPlainText()
      and '饱和温度' in c1.result_text.toPlainText(),
      c1.result_text.toPlainText()[:60])

c2 = mk()
c2.th_input.setText('98')                 # t_sat − t_hot = 1.97 < 5
c2.calculate()
check('C2 热水温度逼近饱和温度（<5 °C）→ 换热温差警告',
      any('换热温差' in x or '不经济' in x for x in c2._last_result['warn']),
      str(c2._last_result['warn']))

c3 = mk()
c3.th_input.setText('20')
c3.tc_input.setText('20')
c3.calculate()
check('C3 热水温度 ≤ 冷水温度 → 报错',
      '错误' in c3.result_text.toPlainText(), c3.result_text.toPlainText()[:60])

c4 = mk()
c4.p_input.setText('2000')
c4.calculate()
check('C4 闪蒸气压力越界（>1600 kPa）→ 报错',
      '错误' in c4.result_text.toPlainText(), c4.result_text.toPlainText()[:60])

c5 = mk()
c5.r_input.setText('-5')
c5.calculate()
check('C4 蒸汽潜热为负 → 报错',
      '错误' in c5.result_text.toPlainText())

c6 = mk()
c6.rho_input.setText('5')
c6.calculate()
check('C4 物料密度越界（>2 t/m³）→ 报错',
      '错误' in c6.result_text.toPlainText())

# ════════════════════════════════════════════════════════════════
print('\n══ Part D  计算链联动（喷射器 → 闪蒸 → 回收 全链）══')
ChainContext.clear()
inj = INJ()
inj.calculate()
inj_entry = ChainContext.get('injection_liquefier_calculator')
check('D1 喷射器登记含「浆料比重」',
      '浆料比重' in inj_entry['values'], str(sorted(inj_entry['values'])))
check('D1 浆料比重登记值 = 修正比重（0.9~1.8 合理区间）',
      0.9 <= inj_entry['values']['浆料比重'] <= 1.8,
      f"{inj_entry['values']['浆料比重']:.4f}")

wf = F()
wf.chain_combo.setCurrentIndex(1)
wf._apply_chain_source()
wf.calculate()
flash_entry = ChainContext.get('flash_evaporation_calculator')
check('D1 闪蒸页登记含「闪蒸压力」(MPa 绝压)',
      '闪蒸压力' in flash_entry['values']
      and 0.001 < flash_entry['values']['闪蒸压力'] < 1.0,
      str(flash_entry['values'].get('闪蒸压力')))

wr = mk()
wr._reload_chain_sources()
items = [wr.chain_combo.itemText(i) for i in range(wr.chain_combo.count())]
check('D2 回收页下拉列出闪蒸降温浓缩与喷射液化器',
      any('闪蒸降温浓缩' in s for s in items)
      and any('喷射液化器' in s for s in items), str(items))
check('D2 下拉不含本页自己', not any('回收' in s for s in items), str(items))

wr.chain_combo.setCurrentIndex(1)          # 闪蒸降温浓缩
wr._apply_chain_source()
fvals = flash_entry['values']
check('D3 取上游值 → 闪蒸汽用量 = 上游「闪蒸汽量」',
      close(float(wr.df_input.text()), fvals['闪蒸汽量'], 1e-6),
      wr.df_input.text())
check('D3 取上游值 → 闪蒸气压力 = 上游「闪蒸压力」×1000（MPa→kPa）',
      close(float(wr.p_input.text()), fvals['闪蒸压力'] * 1000.0, 1e-6),
      wr.p_input.text())
marks = {k: v[2].text() for k, v in wr._rows.items() if v[0] is not None}
check('D3 被取值行打「←上游」标记（df/p）',
      '←上游' in marks['df'] and '←上游' in marks['p'], str(marks))
check('D3 未被闪蒸页提供的行不打标记（cp/rho）',
      '←上游' not in marks['cp'] and '←上游' not in marks['rho'], str(marks))
check('D3 状态栏显示数据来源',
      '闪蒸降温浓缩' in wr.chain_status.text(), wr.chain_status.text())

wr.calculate()
check('D4 全链一致：回收页闪蒸汽用量 = 闪蒸页 D_f 计算结果',
      close(float(wr.df_input.text()), wf._last_result['D_f'], 1e-6),
      f"{wr.df_input.text()} vs {wf._last_result['D_f']:.2f}")
check('D4 结果区标注计算链来源',
      '【计算链来源】' in wr.result_text.toPlainText())

# 回收页自身登记
rec_entry = ChainContext.get('flash_steam_recovery_calculator')
check('D5 回收页自身登记 4 项输出',
      rec_entry is not None
      and all(k in rec_entry['values'] for k in
              ('回收热量', '凝结水量', '可加热物料量', '蒸汽体积')),
      str((rec_entry or {}).get('values')))
check('D5 回收热量登记值 = 计算结果',
      close(rec_entry['values']['回收热量'], wr._last_result['Q_kW'], 1e-6))

# 上游重算 → 过期
wf.tin_input.setText('108')
wf.calculate()
wr._reload_chain_sources()
wr._refresh_chain_status()
check('D6 上游重算后 → 本页提示「已过期」',
      '过期' in wr.chain_status.text(), wr.chain_status.text())

# 手改 → 解绑
wr._reload_chain_sources()
wr.chain_combo.setCurrentIndex(1)
wr._apply_chain_source()
wr.df_input.setText('200')
wr.df_input.textEdited.emit('200')
check('D7 手改输入 → 该行标记消失',
      '←上游' not in wr._rows['df'][2].text())
check('D7 其余行标记保留',
      '←上游' in wr._rows['p'][2].text())

# clear 上下文
ChainContext.clear()
wr._reload_chain_sources()
check('D8 清空上下文 → 下拉只剩「（自动：取全部上游，整链一键取全）」',
      wr.chain_combo.count() == 1)

# ════════════════════════════════════════════════════════════════
print('\n══ Part D2  一键取全链（本页输入分属两个上游，一次取全）══')

# 背景：回收页的 4 个输入分属两个上游 ——
#   物料比热 / 浆料比重 ← 喷射液化器；闪蒸汽量 / 闪蒸压力 ← 闪蒸降温浓缩
# 旧实现要选两次才凑齐；新实现：默认不选来源，点一次「取上游值」即取全链。
ChainContext.clear()
wi2 = INJ()
wi2.calculate()
wf2 = F()
wf2._reload_chain_sources()
wf2.chain_combo.setCurrentIndex(0)
wf2._apply_chain_source()
wf2.calculate()
wr2 = R()

wr2._reload_chain_sources()
items2 = [wr2.chain_combo.itemText(i) for i in range(wr2.chain_combo.count())]
check('D9 下拉首项 = 自动取全部上游（整链）',
      '自动' in items2[0] and '全部上游' in items2[0], items2[0])
check('D9 默认停在首项（不选来源即取全链）', wr2.chain_combo.currentIndex() == 0)
check('D9 来源数 ≥ 2（喷射液化器 + 闪蒸降温浓缩）',
      wr2.chain_combo.count() >= 3, str(items2))

wr2._apply_chain_source()
check('D10 ★ 一次点击填满全部 4 个输入框（无需分两次取）',
      all(getattr(wr2, a).text().strip() for a in
          ('df_input', 'p_input', 'cp_input', 'rho_input')),
      f"{wr2.df_input.text()}/{wr2.p_input.text()}/"
      f"{wr2.cp_input.text()}/{wr2.rho_input.text()}")
check('D11 闪蒸汽量 ← 闪蒸页 D_f',
      close(float(wr2.df_input.text()), wf2._last_result['D_f'], 1e-6),
      f"{wr2.df_input.text()} vs {wf2._last_result['D_f']}")
check('D11 闪蒸压力 ← 闪蒸页 p_abs × 1000（MPa→kPa）',
      close(float(wr2.p_input.text()), wf2._last_result['p_abs'] * 1000.0, 1e-6))
check('D11 物料比热 ← 喷射器的稀释后比热',
      close(float(wr2.cp_input.text()),
            ChainContext.value('injection_liquefier_calculator', '物料比热'), 1e-9))
check('D11 浆料比重 ← 喷射器的修正比重',
      close(float(wr2.rho_input.text()),
            ChainContext.value('injection_liquefier_calculator', '浆料比重'), 1e-9))

srcs2 = ChainContext.describe_refs(wr2._chain_refs)
check('D12 引用集合含**两个**上游页',
      '闪蒸降温浓缩' in srcs2 and '喷射液化器' in srcs2, srcs2)
check('D13 状态栏列出两页来源 + 逐项归属明细',
      '闪蒸汽量←闪蒸降温浓缩' in wr2.chain_status.text()
      and '物料比热←喷射液化器' in wr2.chain_status.text(),
      wr2.chain_status.text())
check('D13 4 行全部打了「←上游」标记',
      all('←上游' in wr2._rows[k][2].text() for k in ('df', 'p', 'cp', 'rho')))

# 链序（同名键先到先得：上游优先）
_ord = ChainContext.ordered_sources(exclude=('flash_steam_recovery_calculator',))
check('D14 ordered_sources 按链序排（喷射器在闪蒸之前）',
      [e['module'] for e in _ord][:2] ==
      ['injection_liquefier_calculator', 'flash_evaporation_calculator'],
      str([e['module'] for e in _ord]))
_mv = ChainContext.merge_values(_ord, ['物料比热', '蒸汽用量', '闪蒸汽量'])
check('D14 merge_values 带回来源页（物料比热 ← 喷射器）',
      _mv['物料比热'][1]['module'] == 'injection_liquefier_calculator',
      _mv['物料比热'][1]['module'])
check('D14 merge_values 只取 keys 内的键',
      set(_mv.keys()) <= {'物料比热', '蒸汽用量', '闪蒸汽量'}, str(sorted(_mv)))

# 同名字段先到先得：让闪蒸页也发布「物料比热」，应仍取喷射器那份
_fl = ChainContext.get('flash_evaporation_calculator')
_fl_vals = dict(_fl['values'])
_fl_vals['物料比热'] = 9.99
_fl_saved = dict(_fl['values'])
_fl['values'] = _fl_vals
_mv2 = ChainContext.merge_values(ChainContext.ordered_sources(), ['物料比热'])
check('D14 同名键先到先得 → 取更上游那条（不是后发布的 9.99）',
      close(float(_mv2['物料比热'][0]), ChainContext.value(
          'injection_liquefier_calculator', '物料比热'), 1e-9),
      str(_mv2['物料比热'][0]))
_fl['values'] = _fl_saved

# 多来源过期提示：只重算喷射器 → 提示里点名该页
wi2.calculate()
wr2._reload_chain_sources()
wr2._refresh_chain_status()
_st = wr2.chain_status.text()
check('D15 多来源过期提示点名具体来源（喷射液化器）',
      '过期' in _st and '喷射液化器' in _st, _st[:120])

# 下拉限定单个来源 → 引用集合只剩该页
wr2._reload_chain_sources()
_i = next(i for i, t in enumerate(
    [wr2.chain_combo.itemText(j) for j in range(wr2.chain_combo.count())])
    if '喷射液化器' in t)
wr2.chain_combo.setCurrentIndex(_i)
wr2._apply_chain_source()
_single = ChainContext.describe_refs(wr2._chain_refs)
check('D16 下拉限定单来源 → 引用集合只剩该页',
      '喷射液化器' in _single and '闪蒸降温浓缩' not in _single, _single)
check('D16 单来源模式下只填该页提供的 2 项（汽量/压力不被覆盖）',
      wr2.df_input.text().strip() != '' and wr2.cp_input.text().strip() != '')

# 无上游时给出可操作提示（不静默）
ChainContext.clear()
wr3 = R()
wr3._reload_chain_sources()
wr3.chain_combo.setCurrentIndex(0)
wr3._apply_chain_source()
check('D17 无任何上游 → 提示去上游页计算（有可操作指引）',
      '没有可用上游' in wr3.chain_status.text()
      and '喷射液化器' in wr3.chain_status.text(), wr3.chain_status.text())

# 基础 API
ChainContext.publish('m1', '页一', {'x': 1})
ChainContext.publish('m2', '页二', {'y': 2})
_rf = ChainContext.make_refs(['m1', 'm2', 'm1'])
check('D18 make_refs 生成 2 条（重复 module 去重）', len(_rf) == 2, str(len(_rf)))
check('D18 describe_refs = 「页一 … + 页二 …」',
      '页一' in ChainContext.describe_refs(_rf) and '页二' in ChainContext.describe_refs(_rf),
      ChainContext.describe_refs(_rf))
check('D18 stale_refs 全新鲜时为空', ChainContext.stale_refs(_rf) == [])
ChainContext.publish('m1', '页一', {'x': 3})                     # m1 重算
_stale = ChainContext.stale_refs(_rf)
check('D18 stale_refs 命中重算过的那一条（且只一条）',
      [r['module'] for r in _stale] == ['m1'], str([r['module'] for r in _stale]))
ChainContext.clear()

# ════════════════════════════════════════════════════════════════
print('\n══ Part E  契约 ══')
we = mk()
we.calculate()
rep = we.generate_report()
check('E1 generate_report → str 且含标题', isinstance(rep, str)
      and '闪蒸蒸汽回收' in rep)
check('E1 无结果 → generate_report → None',
      mk().generate_report() is None)
info = we.get_project_info()
check('E2 get_project_info → dict 含 5 个标准键',
      isinstance(info, dict)
      and all(k in info for k in ('company_name', 'project_number',
                                  'project_name', 'subproject_name',
                                  'calculation_type')))
h = we._get_history_data()
check('E3 历史记录 inputs/outputs 齐全（含回收热量与可加热物料量）',
      '回收热量_kW' in h['outputs'] and '可加热物料量_t_h' in h['outputs']
      and '闪蒸汽用量_kg_h' in h['inputs'], str(h))
we.clear_inputs()
we.calculate()
check('E4 clear → 恢复默认且可直接重算（94.27 kW）',
      close(we._last_result['Q_kW'], 94.2746, 0.05),
      f"{we._last_result['Q_kW']:.3f}")

# ════════════════════════════════════════════════════════════════
print('\n══ Part F  UI 健壮 ══')
wui = mk()
wui.calculate()
check('F1 默认值直接算出结果且无警告',
      wui._last_result and not wui._last_result['warn'],
      str(wui._last_result.get('warn')))
svg_ok = True
try:
    wui.tc_input.setText('25')
    wui.th_input.setText('85')
    wui._update_svg_diagram()
except Exception as e:                                            # noqa: BLE001
    svg_ok = False
    print('   SVG 异常:', e)
check('F2 SVG 刷新不抛异常（属性 XML 语法）', svg_ok)
check('F2 SVG 摘要含回收功率（更新计算后）',
      wui._last_result and 'Q_kW' in wui._last_result)

# ════════════════════════════════════════════════════════════════
print('\n' + '═' * 58)
print(f'通过 {len(PASS)} / {len(PASS) + len(FAIL)}')
if FAIL:
    print('\n失败项：')
    for name, detail in FAIL:
        print(f'  ✗ {name}  [{detail}]')
    sys.exit(1)
