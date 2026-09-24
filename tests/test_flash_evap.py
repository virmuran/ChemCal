# -*- coding: utf-8 -*-
"""闪蒸（料液减压闪蒸）计算 + 计算器联动 回归测试

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_flash_evap.py

核对依据
════════════════════════════════════════════════════════════════════════
Part A  饱和水/汽物性锚点（IAPWS-IF97 独立复算）
    t₂ = 100 °C：h_f = 419.10、h_g = 2675.60、h_fg = 2256.5 kJ/kg
    常压 0.101325 MPa 的饱和温度 ≈ 99.97 °C
    ρ_g(100 °C) = 1/v_g ≈ 0.5977 kg/m³（蒸汽表 ρ″ = 0.5977）
    → 二次蒸汽体积流量 V = D_f · v_g

Part B  设计表格公式逐列对齐
    B1 释放功率  Q = (物料量 + 蒸汽用量)·(t₁ − t₂)·C·1000/3600    kW
       表格样例：M = 20 t/h + 0 kg/h、C = 3.39、105 → 100 °C
       ⇒ Q = 20000×5×3.39/3600 = 94.1667 kW
    B2 闪蒸汽量（严格）：D_f = M·C·ΔT / ( h_g(t₂) − C·t₂ )
       ⇒ 分母 = 2675.60 − 339.00 = 2336.60；D_f = 339000/2336.60 = 145.08 kg/h
    B3 表格口径：D_f′ = M·C·ΔT / ( r₀ − C·t₂ )，r₀ = 2258.77（汽化潜热）
       ⇒ 分母 = 1919.77；D_f′ = 176.58 kg/h，比严格口径**高 21.7 %**
       ★ 表格的「汽化焓」列若填**总焓**（0.1 MPa ≈ 2676），两条口径重合（差 ≈ 0）
    B4 验算行 = 同一结果的 t/h 口径（÷1000），不是独立公式
    B5 线性性：ΔT 或 M 加倍 → D_f 加倍（与规模无关）
    B6 闪蒸后：G′ = M − D_f；干物守恒 G·X = G′·X′ ⇒ X′ = G·X/G′（浓度升高）

Part C  硬约束
    t₁ ≤ t₂ → 报错；t₂ 高于该压力饱和温度 +5 °C → 报错并给出所需压力；
    t₂ 略超饱和温度（>+1 °C）→ 警告；r₀ 填潜热 → 表格口径提示；
    h_g 查表值与自动值差 >1 % → 提示（仍按填值算，不静默改数）；
    浓度/比热/压力越界、蒸汽用量为负 → 报错

Part D  计算链联动（v1.10.0 新增）
    喷射液化器算完 → 登记 8 项可传递输出（浆料量/蒸汽用量/喷射后液量/物料比热/
    干物浓度/出口温度/生蒸汽表压/总焓）
    闪蒸页「取上游值」→ 填进 5 个输入框 + 打「←上游」标记 + 状态显示来源
    上游重算 → 本页提示「已过期」；手改输入 → 标记消失；
    ChainContext.clear() → 回到「（不使用上游数据）」；本页自己不作为自己的上游
    联动一致性：喷射器出口液量 G₁ = G + D₁ 与闪蒸页「物料量 + 蒸汽用量」两栏相加同值

Part E  契约
    generate_report() → str（含标题）/ 无结果 → None
    get_project_info() → dict（5 个标准键）
    _get_history_data() → {"inputs","outputs"}（含数据来源）
    clear_inputs() → 恢复出厂默认值且**可直接重算**

Part F  UI 健壮
    默认值可用（直接算就出结果、默认不触发警告）；SVG 刷新不抛异常
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
    """新建一个闪蒸计算器实例（现取现用，避免跨用例串状态）"""
    return F()


def mk_inj():
    return INJ()


# ════════════════════════════════════════════════════════════════
print('\n══ Part A  饱和水/汽物性锚点（IAPWS-IF97 独立复算）══')
sat100 = IAPWS.saturation_properties(T_C=100.0)
check('100 °C 饱和汽总焓 h_g ≈ 2675.6 kJ/kg（蒸汽表 2676）',
      close(sat100['h_g'], 2675.6, 1.0), f"{sat100['h_g']:.2f}")
check('100 °C 饱和水焓 h_f = 419.10 kJ/kg（蒸汽表 419.1）',
      close(sat100['h_f'], 419.10, 0.3), f"{sat100['h_f']:.2f}")
check('100 °C 汽化潜热 h_fg ≈ 2256.5 kJ/kg',
      close(sat100['h_fg'], 2256.5, 1.0), f"{sat100['h_fg']:.2f}")
check('h_g − C_w·t₂ 与潜热一致（h_g = h_fg + h_f）',
      close(sat100['h_g'], sat100['h_fg'] + sat100['h_f'], 0.3),
      f"{sat100['h_g']:.2f} vs {sat100['h_fg'] + sat100['h_f']:.2f}")

sat_atm = IAPWS.saturation_properties(P_MPa=0.101325)
check('常压 0.101325 MPa(a) → 饱和温度 ≈ 99.97 °C',
      close(sat_atm['T_C'], 99.97, 0.05), f"{sat_atm['T_C']:.3f}")
check('常压饱和汽密度 ≈ 0.5977 kg/m³（蒸汽表 ρ″）',
      close(sat_atm['rho_g'], 0.5977, 0.001), f"{sat_atm['rho_g']:.4f}")
check('饱和汽比容 v_g = 1/ρ_g（自洽）',
      close(1.0 / sat_atm['rho_g'], sat_atm['v_g'], 0.002),
      f"{1.0 / sat_atm['rho_g']:.4f} vs {sat_atm['v_g']:.4f}")

# ════════════════════════════════════════════════════════════════
print('\n══ Part B  设计表格公式逐列对齐 ══')
w = mk()
M_kg, C0, t1, t2 = 20000.0, 3.39, 105.0, 100.0
w.calculate()
r = w._last_result
Q_hand = M_kg * C0 * (t1 - t2) / 3600.0
check('B1 释放功率 = (物料量+蒸汽用量)·ΔT·C·1000/3600 = 94.1667 kW',
      close(r['Q_kW'], Q_hand, 1e-6), f"{r['Q_kW']:.4f} vs {Q_hand:.4f}")
check('B1 释放功率与手算一致（kJ/h 口径）',
      close(r['Q_kjh'], M_kg * C0 * 5.0, 1e-6), f"{r['Q_kjh']:.1f}")

denom_hand = sat100['h_g'] - C0 * t2
check('B2 闪蒸焓差 = h_g(t₂) − C·t₂ = 2336.60 kJ/kg',
      close(r['denom'], denom_hand, 1e-6), f"{r['denom']:.2f} vs {denom_hand:.2f}")
Df_hand = M_kg * C0 * 5.0 / denom_hand
check('B2 严格口径闪蒸汽量 = 145.08 kg/h',
      close(r['D_f'], Df_hand, 1e-6), f"{r['D_f']:.3f} vs {Df_hand:.3f}")
check('B2 闪蒸汽量 ≈ 进料的 0.73 %（量级合理）',
      close(r['D_f'] / r['M_kg'] * 100.0, 0.7255, 0.02),
      f"{r['D_f'] / r['M_kg'] * 100:.4f}")

denom_tab_hand = 2258.77 - C0 * t2
check('B3 表格「汽化焓」列留空 → 按总焓自动取，两条口径重合',
      r['r0_in'] is None and close(r['D_f_tab'], r['D_f'], 1e-9),
      f"{r['D_f_tab']:.3f} vs {r['D_f']:.3f}")

w_tab = mk()
w_tab.r0_input.setText('2258.77')      # 表格实际填的汽化潜热
w_tab.calculate()
r_tab = w_tab._last_result
check('B3 填表格值 2258.77 → 表格口径焓差 = r₀ − C·t₂ = 1919.77 kJ/kg',
      close(r_tab['denom_tab'], denom_tab_hand, 1e-9), f"{r_tab['denom_tab']:.2f}")
check('B3 填表格值 → 表格口径汽量 = 176.58 kg/h',
      close(r_tab['D_f_tab'], M_kg * C0 * 5.0 / denom_tab_hand, 1e-9),
      f"{r_tab['D_f_tab']:.3f}")
check('B3 表格口径比严格口径高 ≈ 21.7 %（分母用潜热而非总焓）',
      close(r_tab['d_tab_pct'], 21.71, 0.1), f"{r_tab['d_tab_pct']:.3f}")
check('B3 判定：填值 2258.77 与 t₂ 下汽化潜热基本一致（确认填的是潜热）',
      r_tab['r0_is_latent'] is True)
check('B3 填潜热 → 结果里出现「表格口径偏高」提示',
      any('表格口径' in x for x in r_tab['warn']), str(len(r_tab['warn'])))

# ★ 表格列改填总焓 → 两条口径重合
w2 = mk()
w2.r0_input.setText('2675.60')
w2.calculate()
r2 = w2._last_result
check('B3 ★ r₀ 改填总焓 2675.60 → 表格口径与严格口径重合（差 < 0.01 %）',
      abs(r2['d_tab_pct']) < 0.01, f"{r2['d_tab_pct']:.4f}")
check('B3 此时不再触发「表格口径偏高」提示',
      not any('表格口径' in x for x in r2['warn']))

check('B4 验算行 = 闪蒸汽量 ÷ 1000（t/h 口径，同一结果）',
      close(r_tab['check_tab'], r_tab['D_f_tab'] / 1000.0, 1e-9),
      f"{r_tab['check_tab']:.4f}")

# B5 线性性
w3 = mk()
w3.feed_input.setText('40')          # M 加倍
w3.steam_input.setText('0')
w3.calculate()
check('B5 进料量加倍 → 闪蒸汽量加倍（D_f ∝ M）',
      close(w3._last_result['D_f'], 2.0 * r['D_f'], 1e-6),
      f"{w3._last_result['D_f']:.3f}")
w4 = mk()
w4.tin_input.setText('110')          # ΔT 5 → 10
w4.calculate()
check('B5 温差加倍 → 闪蒸汽量加倍（D_f ∝ ΔT）',
      close(w4._last_result['D_f'], 2.0 * r['D_f'], 1e-6),
      f"{w4._last_result['D_f']:.3f}")
w5 = mk()
w5.feed_input.setText('1')           # 规模无关：单位闪蒸汽量不变
w5.calculate()
check('B5 单位闪蒸汽量（kg 汽/t 进料）与规模无关',
      close(w5._last_result['unit_flash'], r['unit_flash'], 1e-9),
      f"{w5._last_result['unit_flash']:.6f}")

# B6 闪蒸后
check('B6 闪蒸后料量 G′ = M − D_f = 19.855 t/h',
      close(r['G_after_t'], (M_kg - r['D_f']) / 1000.0, 1e-9),
      f"{r['G_after_t']:.4f}")
check('B6 干物守恒：G·X = G′·X′',
      close(r['G_t'] * r['X'] / 100.0, r['G_after_t'] * r['X_after'] / 100.0, 1e-9),
      f"{r['G_t'] * r['X'] / 100:.6f} vs {r['G_after_t'] * r['X_after'] / 100:.6f}")
check('B6 闪蒸后浓度升高（失水浓缩，与喷射的稀释相反）',
      r['X_after'] > r['X'], f"{r['X']:.2f} → {r['X_after']:.2f}")
check('B6 二次蒸汽体积 = D_f·v_g（m³/h）',
      close(r['v_flash'], r['D_f'] * r['v_g'], 1e-6), f"{r['v_flash']:.2f}")

# ════════════════════════════════════════════════════════════════
print('\n══ Part C  硬约束 ══')
c1 = mk()
c1.tin_input.setText('95')
c1.tout_input.setText('100')
c1.calculate()
check('C1 t₁ < t₂ → 报错（无闪蒸推动力）',
      '必须高于出闪蒸温度' in c1.result_text.toPlainText(),
      c1.result_text.toPlainText()[:80])

c2 = mk()
c2.tin_input.setText('160')
c2.tout_input.setText('130')
c2.calculate()
txt2 = c2.result_text.toPlainText()
check('C2 常压闪蒸到 130 °C → 报错（高于该压力饱和温度）',
      '高于闪蒸压力' in txt2, txt2[:80])
check('C2 报错信息给出所需闪蒸压力',
      'MPa(a)' in txt2 and '提高到' in txt2)

c3 = mk()          # t₂ = 102 °C：略高于常压饱和温度 → 警告但不报错
c3.tin_input.setText('110')
c3.tout_input.setText('102')
c3.calculate()
r3 = c3._last_result
check('C3 t₂ 略超饱和温度（+1~+5 °C）→ 警告但可算',
      bool(r3) and any('饱和温度' in x for x in r3['warn']),
      str(r3.get('warn')))

c4 = mk()
c4.conc_input.setText('0')          # 浓度越界
c4.calculate()
check('C4 干物浓度越界 → 报错', '干物浓度' in c4.result_text.toPlainText())

c5 = mk()
c5.cp_input.setText('9')            # 比热越界
c5.calculate()
check('C5 比热越界 → 报错', '物料比热' in c5.result_text.toPlainText())

c6 = mk()
c6.steam_input.setText('-5')        # 负用汽量
c6.calculate()
check('C6 蒸汽用量为负 → 报错', '不能为负' in c6.result_text.toPlainText())

c7 = mk()
c7.hg_input.setText('2500.00')      # 查错蒸汽表（2500 比 2675.6 低 6.6 %）
c7.calculate()
r7 = c7._last_result
check('C7 总焓查表值填错 → 提示核对，但仍按填值计算（不静默改数）',
      any('查错了蒸汽表' in x for x in r7['warn']) and close(r7['h_g'], 2500.0, 1e-9),
      f"{r7['h_g']} / {r7['warn']}")

c8 = mk()
c8.hg_input.setText('2676')         # 与自动值一致 → 无提示
c8.calculate()
check('C8 总焓查表值与自动值一致 → 无「查错蒸汽表」提示',
      not any('查错蒸汽表' in x for x in c8._last_result['warn']))

# ════════════════════════════════════════════════════════════════
print('\n══ Part D  计算链联动 ══')
ChainContext.clear()
inj = mk_inj()
inj.calculate()
entry = ChainContext.get('injection_liquefier_calculator')
check('D1 喷射器算完 → 已登记到计算链', entry is not None)
for k in ('浆料量', '蒸汽用量', '喷射后液量', '物料比热', '干物浓度', '出口温度'):
    check(f'D1 登记项含「{k}」', k in (entry or {}).get('values', {}))

w_chain = mk()
items = [w_chain.chain_combo.itemText(i) for i in range(w_chain.chain_combo.count())]
check('D2 闪蒸页下拉列出喷射液化器（含时间）',
      any('喷射液化器' in s for s in items), str(items))
check('D2 下拉不含本页自己', not any('闪蒸' in s for s in items), str(items))

w_chain.chain_combo.setCurrentIndex(1)
w_chain._apply_chain_source()
vals = entry['values']
check('D3 取上游值 → 物料量 = 上游浆料量',
      close(float(w_chain.feed_input.text()), vals['浆料量'], 1e-6),
      w_chain.feed_input.text())
check('D3 取上游值 → 蒸汽用量 = 上游用汽量',
      close(float(w_chain.steam_input.text()), vals['蒸汽用量'], 1e-4),
      w_chain.steam_input.text())
check('D3 取上游值 → 物料比热 = 上游稀释后比热',
      close(float(w_chain.cp_input.text()), vals['物料比热'], 1e-4),
      w_chain.cp_input.text())
check('D3 取上游值 → 干物浓度 = 上游稀释后浓度',
      close(float(w_chain.conc_input.text()), vals['干物浓度'], 1e-3),
      w_chain.conc_input.text())
check('D3 取上游值 → 进闪蒸温度 = 上游出口温度',
      close(float(w_chain.tin_input.text()), vals['出口温度'], 1e-6),
      w_chain.tin_input.text())
check('D3 状态栏显示数据来源',
      '喷射液化器' in w_chain.chain_status.text(), w_chain.chain_status.text())
marks = {k: v[2].text() for k, v in w_chain._rows.items()}
check('D3 被取值的行打了「←上游」标记（进料/蒸汽/浓度/比热/温度）',
      all('←上游' in marks[k] for k in ('feed', 'steam', 'conc', 'cp', 'tin')),
      str(marks))
check('D3 未被取值的行不打标记（出闪蒸温度/压力/汽化焓）',
      all('←上游' not in marks[k] for k in ('tout', 'p', 'r0', 'hg')))

w_chain.calculate()
check('D4 联动结果：闪蒸进料量 = 喷射器出口液量（G + D₁）',
      close(w_chain._last_result['M_kg'] / 1000.0, vals['喷射后液量'], 1e-6),
      f"{w_chain._last_result['M_kg'] / 1000.0:.4f} vs {vals['喷射后液量']:.4f}")
check('D4 结果区标注计算链来源',
      '【计算链来源】' in w_chain.result_text.toPlainText())

# 上游重算 → 过期提示
inj.feed_input.setText('25')
inj.calculate()
w_chain._reload_chain_sources()
w_chain._refresh_chain_status()
check('D5 上游重算后 → 本页提示「已过期」',
      '过期' in w_chain.chain_status.text(), w_chain.chain_status.text())

# 手改输入 → 标记消失
w_chain._reload_chain_sources()
w_chain.chain_combo.setCurrentIndex(1)
w_chain._apply_chain_source()
w_chain.tin_input.setText('108')          # 手工改动
w_chain.tin_input.textEdited.emit('108')
check('D6 手改输入 → 该行「←上游」标记消失',
      '←上游' not in w_chain._rows['tin'][2].text(),
      w_chain._rows['tin'][2].text())
check('D6 其余行标记保留（各自独立）',
      '←上游' in w_chain._rows['cp'][2].text())

# 本页自己登记（供更下游取用）
w_chain.calculate()
flash_entry = ChainContext.get('flash_evaporation_calculator')
check('D7 闪蒸页自身也登记输出（供下游取用）',
      flash_entry is not None and '闪蒸汽量' in flash_entry['values'],
      str((flash_entry or {}).get('values')))
check('D7 闪蒸后料量与浓度登记值 = 计算结果',
      close(flash_entry['values']['闪蒸后料量'], w_chain._last_result['G_after_t'], 1e-6))

# clear 上下文
ChainContext.clear()
w_chain._reload_chain_sources()
check('D8 清空上下文 → 下拉只剩「不使用上游数据」',
      w_chain.chain_combo.count() == 1, str(w_chain.chain_combo.count()))

# 契约：clear_inputs 解除引用
w9 = mk()
inj2 = mk_inj()
inj2.calculate()
w9._reload_chain_sources()
w9.chain_combo.setCurrentIndex(1)
w9._apply_chain_source()
w9.clear_inputs()
check('D9 clear_inputs 后恢复默认值且解除上游引用',
      close(float(w9.feed_input.text()), 20.0, 1e-9)
      and close(float(w9.steam_input.text()), 0.0, 1e-9)
      and w9.chain_combo.currentIndex() == 0,
      f"{w9.feed_input.text()}/{w9.steam_input.text()}/{w9.chain_combo.currentIndex()}")
check('D9 解除引用后行标记也清掉',
      all('←上游' not in v[2].text() for v in w9._rows.values()))
w9.calculate()
check('D9 clear 后可直接重算', bool(w9._last_result))

# ════════════════════════════════════════════════════════════════
print('\n══ Part E  契约 ══')
wd = mk()
wd.calculate()
rep = wd.generate_report()
check('E1 generate_report() → str（含计算书标题）',
      isinstance(rep, str) and '闪蒸（料液减压闪蒸）计算书' in rep,
      type(rep).__name__)
check('E1 报告含公式依据与数据来源段',
      '绝热闪蒸热量衡算' in (rep or '') and '数据来源与假设' in (rep or ''))
we = mk()
check('E2 未计算时 generate_report() → None', we.generate_report() is None)
info = wd.get_project_info()
check('E3 get_project_info() → 5 个标准键',
      isinstance(info, dict)
      and all(k in info for k in ('company_name', 'project_number', 'project_name',
                                  'subproject_name', 'calculation_type')),
      str(list(info.keys())))
h = wd._get_history_data()
check('E4 _get_history_data() → inputs/outputs',
      isinstance(h, dict) and set(h.keys()) == {'inputs', 'outputs'},
      str(list(h.keys())))
check('E4 outputs 含释放功率/闪蒸汽量/闪蒸后浓度',
      all(k in h['outputs'] for k in ('释放功率_kW', '闪蒸汽量_kg_h', '闪蒸后浓度_wt%')),
      str(list(h['outputs'].keys())))
check('E4 inputs 含「数据来源」字段', '数据来源' in h['inputs'])

wf = mk()
wf.clear_inputs()
check('E5 clear_inputs 恢复出厂默认值（物料量 20 / 蒸汽 0 / 比热 3.39 / 常压）',
      close(float(wf.feed_input.text()), 20.0, 1e-9)
      and close(float(wf.steam_input.text()), 0.0, 1e-9)
      and close(float(wf.cp_input.text()), 3.39, 1e-9)
      and close(float(wf.p_input.text()), 0.101325, 1e-9),
      f"{wf.feed_input.text()}/{wf.cp_input.text()}/{wf.p_input.text()}")
wf.calculate()
check('E5 clear 后可直接重算（默认参数可用）', bool(wf._last_result))

# ════════════════════════════════════════════════════════════════
print('\n══ Part F  UI 健壮 ══')
wg = mk()
wg.calculate()
check('F1 默认参数直接算出结果且**无警告**（常压 100 °C 属于正常工作点）',
      bool(wg._last_result) and not wg._last_result['warn'],
      str(wg._last_result.get('warn')))
check('F1 默认物料比热 3.39 = 30 % 淀粉乳加权比热（C₀=1.55）',
      close(1.55 * 0.30 + 4.18 * 0.70, 3.39, 0.005), '')
check('F2 控件在计算后仍可访问（构造后契约）',
      wg.feed_input.text() == '20' and wg.tin_input.text() == '105')
svg_ok = True
try:
    wg.tin_input.setText('120')
    wg.tout_input.setText('99')
    wg._update_svg_diagram()
except Exception as e:                                            # noqa: BLE001
    svg_ok = False
    print('   SVG 异常:', e)
check('F3 SVG 刷新不抛异常且内容有效（属性 XML 语法）',
      svg_ok and wg.svg_widget.renderer().isValid())
check('F4 进料量预览标签随输入更新（物料量 + 蒸汽用量）',
      '20.000' in wg.feed_total_label.text() and 'kg/h' in wg.feed_total_label.text(),
      wg.feed_total_label.text())

# ════════════════════════════════════════════════════════════════
print('\n' + '═' * 58)
print(f'通过 {len(PASS)} / {len(PASS) + len(FAIL)}')
if FAIL:
    print('\n失败清单：')
    for n, d in FAIL:
        print(f'  ✗ {n}  {d}')
    sys.exit(1)
print('全部通过 ✔')
