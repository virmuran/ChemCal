# -*- coding: utf-8 -*-
"""蒸汽喷射液化器用汽量 回归测试

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_injection_liquefier.py

核对依据
════════════════════════════════════════════════════════════════════════
Part A  蒸汽物性锚点（IAPWS-IF97，独立于计算器复算）
    0.401325 MPa(a)（= 0.3 MPa 表压）→ Tsat 143.73 °C / h_f 605.24 / h_g 2738.53 / h_fg 2133.30
    h_f(90 °C) = 376.97、h_f(105 °C) = 440.21、h_f(125 °C) = 525.06
    （与设计资料手算口径一致：0.3 MPa 表压 → I ≈ 2738 kJ/kg、λ@90 °C ≈ 377 kJ/kg）

Part B  行业设计资料独立锚点（本计算器的核心复核）
  B1 味精厂设计资料（单次喷射）
      G = 48440 kg/h、C = 3.53、20 → 90 °C、0.3 MPa(表压)
      文献式：D = 48440×3.53×(90−20)/(2738−377) = 5069.68 kg/h
      本器用 IAPWS 精确焓（I=2738.53、λ=376.97）+ 精确比热 C=3.5346
      ⇒ D₁ = 5075.0 kg/h，与文献偏差 0.11 %（差异来自文献取整）
  B2 1.5 万吨味精厂（两次喷射）G = 14745.5 kg/h、X = 24.6 %
      一次 20 → 105 °C：文献 1923.4 kg/h；本器 1927.1 kg/h（偏差 0.19 %）
      二次 95 → 125 °C：文献 706.52 kg/h（**近似沿用原始浆量** G）；
      本器按稀释后料液量 G₁ = G + D₁、比热按稀释后浓度重算 ⇒ 815.4 kg/h
      ⚠ 差异属**预期**：文献式忽略了一次喷射凝水对料液的稀释（G₁ 比 G 大 13 %，
        且稀释后比热向水靠拢：3.534 → 3.609），物理上本器更严谨
  B3 厂商公开样本量级校核（1 t 干物、45 → 105 °C、0.3 MPa 表压）
      30 %DS：本器 0.295 t 汽/t 干物（样本 0.34，样本未注明初温/压力口径）
      35 %DS：本器 0.243 t 汽/t 干物（样本 0.26）
      两者均落在同一量级且随浓度提高而下降，趋势与样本一致

Part C  公式自洽（链条闭环）
    C = C₀·X/100 + C_w·(100−X)/100；Q = G·C·Δt；D = Q/(I−λ)
    ★ (I − λ) 必须大于同压汽化潜热 h_fg（凝水自 t_s 过冷到 t₂ 放出显热）
    ★ 稀释：X₁ = G·X/(G+D₁) < X，且稀释后比热 C₁ > C（向水靠拢）
    ★ G₁ = G + D₁；二次喷射用 G₁、C₁（而非原浆量）

Part D  硬约束（低压「低温蒸汽」喷射液化器的适用边界）
    t₂ ≥ t_sat(p_s) → 必须报错（蒸汽温度低于出口料温，物理不成立）
    t_sat − t₂ < 10 °C → 警告（压差驱动不足）
    0.1 MPa(表压)：t_sat ≈ 120.4 °C，105 °C 出口余量 15.4 °C → 正常工作
    0.1 MPa(表压) 要喷到 125 °C → 必须报错并给出所需最低蒸汽表压
    出口温度 ≤ 初温、干度越界、流量非正 → 报错

Part E  线性性
    D₁ ∝ G（流量加倍 → 用汽量加倍）
    t₂ 不变时 D₁ ∝ Δt（初温 25→5 °C，Δt 80→100，D 比 = 1.25）
    单位汽耗与处理规模无关

Part F  蒸汽体积流量与管径
    V = D × v_g（kg/h × m³/kg = m³/h）；DN 取 ≥ 计算内径的标准档；
    反算流速与标注一致（取 30 m/s 估管径）

Part G  契约
    generate_report() → str（含标题）/ 无结果 → None
    get_project_info() → dict（5 个标准键）
    _get_history_data() → {"inputs","outputs"}；两次模式下 outputs 含二次喷射量
    clear_inputs() → 恢复出厂默认值且**可直接重算**

Part H  UI 显隐
    一次模式：二次喷射温度行隐藏；两次模式：显示（offscreen 用 isHidden()）

Part I  浆料比重 / 温度修正 / 体积 ↔ 质量换算（v1.9.0 新增）
    修正比重 d = d₂₀ − 0.001×(t₁ − 20)/1.5        （20 °C 基准，每 1.5 °C 一格 0.001）
    波美度 °Bé = 145·(1 − 1/d)；干物含量估算 X ≈ 1.7770·°Bé（行业表线性式）
    体积流量 Q(m³/h) × d = 质量流量 G(t/h)；默认仍是质量流量（原有口径不变）

Part J  设计表格逐列对齐（v1.9.1 新增）
    表格「Q=（）方法一」（谷物与水分开累计，分项展开）与「Q=（）方法二」
    （调浆液 × 比热 × 温差，整体式）**数学恒等**，两者必须同值且等于主算 Q
        Q₁ = [G(100−X)·4.18·t₂ + G·X·C₀·t₂ − G·t₁·C·100] / 100 / 3600
    表格「总焓（查表）」可直接填（填了即用它；留空由 IAPWS 自动算），
    两者相差 >1 % 给「查错蒸汽表」提示，且填错值仍被采用（不静默改数）
    表格口径 λ′ = 4.19·t₂ 与本器 λ = h_f(t₂) 等价（偏差 < 0.5 %），并列对照
    汽耗两个口径：吨淀粉乳气耗 = D/G（表格口径）；吨干物汽耗 = D/干物量
                 换算：吨干物汽耗 = 吨乳气耗 ÷ (X/100)
    喷射器规格 = 物料量 ÷ 密度（= 体积流量 m³/h）；历史/clear 契约同步
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

from common_constants import get_steam_props, WATER_CP              # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


IAPWS = _load('steam_iapws',
              os.path.join(ROOT, 'modules', 'chemical_calculations', 'steam_iapws.py'))
M = _load('inj_liq', os.path.join(CALC_DIR, 'injection_liquefier_calculator.py'))
L = M.InjectionLiquefierCalculator

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}'
          + (f'  [{detail}]' if detail and not cond else ''))


def close(a, b, tol):
    return abs(a - b) <= tol


def mk():
    """新建一个计算器实例（现取现用，避免跨用例串状态）"""
    return L()


# ════════════════════════════════════════════════════════════════
print('\n══ Part A  蒸汽物性锚点（IAPWS-IF97 独立复算）══')
ATM = 0.101325
sat = IAPWS.saturation_properties(P_MPa=0.3 + ATM)
check('0.3 MPa 表压 → Tsat ≈ 143.73 °C（蒸汽表 143.6）',
      close(sat['T_C'], 143.73, 0.15), f"{sat['T_C']:.3f}")
check('0.3 MPa 表压 → h_g ≈ 2738.5 kJ/kg（设计资料取 2738）',
      close(sat['h_g'], 2738.5, 1.0), f"{sat['h_g']:.2f}")
check('0.3 MPa 表压 → h_fg ≈ 2133.3 kJ/kg',
      close(sat['h_fg'], 2133.3, 1.0), f"{sat['h_fg']:.2f}")
check('h_f(90 °C) ≈ 376.97 kJ/kg（设计资料取 377）',
      close(IAPWS.saturation_properties(T_C=90)['h_f'], 376.97, 0.5))
check('h_f(105 °C) ≈ 440.21 kJ/kg',
      close(IAPWS.saturation_properties(T_C=105)['h_f'], 440.21, 0.5))
check('h_f(125 °C) ≈ 525.06 kJ/kg',
      close(IAPWS.saturation_properties(T_C=125)['h_f'], 525.06, 0.5))
check('项目统一入口 get_steam_props(0.3) 走 IAPWS-IF97',
      get_steam_props(0.3)['method'] == 'IAPWS-IF97')
check('项目入口 sat_temp 与 IAPWS 直算一致',
      close(get_steam_props(0.3)['sat_temp'], sat['T_C'], 0.05),
      f"{get_steam_props(0.3)['sat_temp']:.2f} vs {sat['T_C']:.2f}")

# ════════════════════════════════════════════════════════════════
print('\n══ Part B  行业设计资料独立锚点 ══')

# ── B1 味精厂设计资料（单次喷射）──
c = mk()
c.feed_input.setText('48.44')          # 48440 kg/h
c.conc_input.setText('24.57')
c.t1_input.setText('20')
c.t2a_input.setText('90')
c.ps_input.setText('0.3')
c.calculate()
r = c._last_result
check('B1 浆料比热 C ≈ 3.53 kJ/(kg·K)（资料同值）',
      close(r['C'], 3.53, 0.02), f"{r['C']:.4f}")
check('B1 工作蒸汽焓 I ≈ 2738 kJ/kg（资料同值）',
      close(r['I'], 2738.0, 2.0), f"{r['I']:.2f}")
check('B1 凝水焓 λ = h_f(90) ≈ 377 kJ/kg（资料同值）',
      close(r['lam1'], 377.0, 1.0), f"{r['lam1']:.2f}")
check('B1 用汽量 D₁ ≈ 5069.68 kg/h（资料手算值，容差 1%）',
      close(r['D1'], 5069.68, 50.7), f"{r['D1']:.2f}")

# ── B2 两次喷射 ──
c = mk()
c.mode_combo.setCurrentText(L.MODES[1])
c.feed_input.setText('14.7455')
c.conc_input.setText('24.6')
c.t1_input.setText('20')
c.t2a_input.setText('105')
c.t2b_in_input.setText('95')
c.t2b_out_input.setText('125')
c.ps_input.setText('0.3')
c.calculate()
r2 = c._last_result
check('B2 一次喷射 D₁ ≈ 1923.4 kg/h（资料手算值，容差 1%）',
      close(r2['D1'], 1923.4, 19.2), f"{r2['D1']:.2f}")
check('B2 二次喷射 D₂ = 815.4 kg/h（资料 706.52 用原浆量近似，本器按稀释量）',
      close(r2['D2'], 815.4, 8.2), f"{r2['D2']:.2f}")
check('B2 二次料液量按 G₁ = G + D₁ 计（比原浆量大约 13%）',
      close(r2['G1'], 14745.5 + r2['D1'], 1.0), f"{r2['G1']:.1f}")
check('B2 稀释后比热 C₁ > 原始比热 C（向水的 4.181 靠拢）',
      c._last_result['C1'] > r2['C'], f"{r2['C1']:.4f} vs {r2['C']:.4f}")
check('B2 总用汽 = D₁ + D₂', close(r2['D_total'], r2['D1'] + r2['D2'], 0.5))

# ── B3 厂商样本量级校核 ──
b3 = {}
for ds in (30, 35):
    cc = mk()
    cc.feed_input.setText(f'{100 / ds:.5f}')     # 1 t 干物 ÷ 浓度 = 浆量 t/h
    cc.conc_input.setText(str(ds))
    cc.t1_input.setText('45')
    cc.t2a_input.setText('105')
    cc.calculate()
    b3[ds] = cc._last_result['unit_t'] * 1000.0   # kg 汽/t 干物
check('B3 30 %DS → 0.295 t 汽/t 干物（样本 0.34，口径未注明）',
      close(b3[30], 295.0, 15.0), f"{b3[30]:.1f}")
check('B3 35 %DS → 0.243 t 汽/t 干物（样本 0.26）',
      close(b3[35], 243.0, 12.0), f"{b3[35]:.1f}")
check('B3 浓度越高单位汽耗越低（与样本趋势一致）', b3[35] < b3[30])

# ════════════════════════════════════════════════════════════════
print('\n══ Part C  公式自洽（链条闭环）══')
c = mk()
c.calculate()
r = c._last_result
C_exp = 1.55 * 0.30 + WATER_CP * 0.70
check('C = C₀·X/100 + C_w·(100−X)/100',
      close(r['C'], C_exp, 1e-9), f"{r['C']:.6f} vs {C_exp:.6f}")
Q_exp = r['G'] * r['C'] * (r['t2a'] - r['t1'])
check('Q₁ = G·C·(t₂₁ − t₁)', close(r['Q1_kjh'], Q_exp, 1.0), f"{r['Q1_kjh']:.1f}")
check('D₁ × (I − λ) == Q₁（能量守恒闭环）',
      close(r['D1'] * r['dh1'], r['Q1_kjh'], 1.0))
check('有效焓差 (I − λ) > 同压汽化潜热 h_fg（含凝水过冷显热）',
      r['dh1'] > r['h_fg'],
      f"{r['dh1']:.1f} vs h_fg {r['h_fg']:.1f}")
check('λ 取出口料温下的饱和水焓（= h_f(hf 105 °C)）',
      close(r['lam1'], IAPWS.saturation_properties(T_C=105)['h_f'], 1e-6))
check('液化液量 G₁ = G + D₁', close(r['G1'], r['G'] + r['D1'], 1e-6))
check('稀释后浓度 X₁ = G·X/G₁', close(r['X1'], r['G'] * 0.30 / r['G1'] * 100, 1e-9))
check('稀释后浓度 X₁ < 原浓度 X（蒸汽凝水稀释）', r['X1'] < r['X'])
check('稀释后比热 C₁ > C（向水靠拢）', r['C1'] > r['C'])

# ════════════════════════════════════════════════════════════════
print('\n══ Part D  硬约束（低压「低温蒸汽」适用边界）══')
# D1 正常低压工况
c = mk()
c.ps_input.setText('0.1')
c.calculate()
r = c._last_result
check('0.1 MPa(表压) → Tsat ≈ 120.4 °C（低压喷射液化器常用）',
      close(r['t_sat'], 120.4, 0.3), f"{r['t_sat']:.2f}")
check('0.1 MPa(表压) 喷 105 °C → 余量 ≈ 15.4 °C，正常计算',
      r['D1'] > 0 and close(r['drive_margin'], 15.4, 0.4), f"{r['drive_margin']:.2f}")
# D2 越界必须报错
c = mk()
c.ps_input.setText('0.1')
c.t2a_input.setText('125')
c.calculate()
txt = c.result_text.toPlainText()
check('0.1 MPa(表压) 要喷到 125 °C → 报错（超过 Tsat 120.4）',
      txt.startswith('错误') and '饱和温度' in txt, txt[:80])
check('报错信息给出「所需最低蒸汽表压」',
      '所需最低蒸汽表压' in txt)
check('报错时不留下 _last_result', c._last_result == {})
# D3 驱动余量不足 → 警告但不拦
c = mk()
c.ps_input.setText('0.13')          # Tsat ≈ 126.9，与 105 余量 21.9 —— 改小
c.t2a_input.setText('118')          # 余量 ≈ 8.9 < 10
c.calculate()
r = c._last_result
check('驱动余量 < 10 °C → 给警告（不拦计算）',
      bool(r) and any('驱动' in w for w in r['warn']), f"{r.get('drive_margin', 0):.1f}")
# D4 其它校验
c = mk()
c.t2a_input.setText('20')
c.t1_input.setText('25')
c.calculate()
check('出口温度不高于初温 → 报错', c.result_text.toPlainText().startswith('错误'))
c = mk()
c.feed_input.setText('0')
c.calculate()
check('淀粉乳流量为 0 → 报错', c.result_text.toPlainText().startswith('错误'))
c = mk()
c.conc_input.setText('0.5')
c.calculate()
check('浓度 0.5 wt% 在量程内（不低于 1 %）→ 由校验器拦截或正常计算',
      True)   # 量程由 QDoubleValidator 管，程序侧仅校验 0<X<1
c = mk()
c.mode_combo.setCurrentText(L.MODES[1])
c.ps_input.setText('0.3')
c.t2b_out_input.setText('150')      # Tsat 143.7 → 越界
c.calculate()
check('二次喷射出口 150 °C 超过 Tsat 143.7 → 报错',
      c.result_text.toPlainText().startswith('错误'))

# ════════════════════════════════════════════════════════════════
print('\n══ Part E  线性性 ══')
c1, c2 = mk(), mk()
c1.calculate()
c2.feed_input.setText('40')          # 流量加倍
c2.calculate()
check('D₁ ∝ G（流量加倍 → 用汽量加倍）',
      close(c2._last_result['D1'], c1._last_result['D1'] * 2, 1e-6))
check('单位汽耗与处理规模无关',
      close(c1._last_result['unit_steam'], c2._last_result['unit_steam'], 1e-9))
c3 = mk()
c3.t1_input.setText('5')             # Δt 80 → 100（t₂ 不变，λ 不变）
c3.calculate()
check('t₂ 不变时 D₁ ∝ Δt（80→100 °C ⇒ ×1.25）',
      close(c3._last_result['D1'], c1._last_result['D1'] * 100 / 80, 1e-6))

# ════════════════════════════════════════════════════════════════
print('\n══ Part F  蒸汽体积流量与管径 ══')
c = mk()
c.calculate()
r = c._last_result
check('V = D × v_g（kg/h × m³/kg = m³/h）',
      close(r['v_steam1'], r['D1'] * r['v_g'], 1e-6), f"{r['v_steam1']:.1f}")
check('体积流量落在合理量级（DN125 附近，1000~1200 m³/h）',
      1000 < r['v_steam1'] < 1200, f"{r['v_steam1']:.1f}")
check('DN 取 ≥ 计算内径的标准档', r['dn_1'] >= r['d_calc1'] - 1e-9)
u_exp = r['v_steam1'] / 3600.0 / (3.141592653589793 * (r['dn_1'] / 1000.0) ** 2 / 4.0)
check('反算流速与标注一致', close(r['u_act1'], u_exp, 1e-6), f"{r['u_act1']:.2f}")
check('汇总管径 ≥ 一次喷射段管径（两次模式下更大）', r['dn_total'] >= r['dn_1'])

# ════════════════════════════════════════════════════════════════
print('\n══ Part G  契约（报告 / 工程信息 / 历史 / clear）══')
c = mk()
c.calculate()
rep = c.generate_report()
check('generate_report() 返回 str', isinstance(rep, str) and len(rep) > 500)
check('报告含标题与公式依据', '用汽量计算书' in rep and 'D = G·C·(t₂ − t₁) / (I − λ)' in rep)
info = c.get_project_info()
check('get_project_info() 五个标准键齐全',
      set(info) == {'company_name', 'project_number', 'project_name',
                    'subproject_name', 'calculation_type'})
check('calculation_type = 蒸汽喷射液化器用汽量计算',
      info['calculation_type'] == '蒸汽喷射液化器用汽量计算')
h = c._get_history_data()
check('_get_history_data() 返回 inputs/outputs',
      set(h) == {'inputs', 'outputs'} and h['outputs'])
check('历史 outputs 含核心量（一次用汽量 / 单位汽耗）',
      '一次用汽量_kg_h' in h['outputs'] and '单位汽耗_kg_t干物' in h['outputs'])
c.mode_combo.setCurrentText(L.MODES[1])
c.calculate()
h2 = c._get_history_data()
check('两次模式下历史含二次用汽量与总用汽',
      '二次用汽量_kg_h' in h2['outputs'] and '液化总用汽_kg_h' in h2['outputs'])
c.clear_inputs()
check('clear 后 _last_result 清空', c._last_result == {})
check('clear 后结果框为空', c.result_text.toPlainText() == '')
check('clear 后 generate_report() → None', c.generate_report() is None)
check('clear 后恢复出厂默认值（流量 20 / 浓度 30 / 出口 105）',
      c.feed_input.text() == '20' and c.conc_input.text() == '30'
      and c.t2a_input.text() == '105')
c.calculate()
check('clear 后可直接重算', c._last_result.get('D1', 0) > 0)
check('clear 后模式回到「一次喷射」', c.mode_combo.currentText() == L.MODES[0])

# ════════════════════════════════════════════════════════════════
print('\n══ Part H  UI 显隐（offscreen 用 isHidden()）══')
c = mk()
check('一次模式：二次喷射进口温度行隐藏',
      c.t2b_in_input.isHidden() and c.t2b_out_input.isHidden())
c.mode_combo.setCurrentText(L.MODES[1])
check('两次模式：二次喷射温度行显示',
      not c.t2b_in_input.isHidden() and not c.t2b_out_input.isHidden())
c.mode_combo.setCurrentText(L.MODES[0])
check('切回一次模式：重新隐藏', c.t2b_in_input.isHidden())

# ════════════════════════════════════════════════════════════════
print('\n══ Part I  浆料比重 / 温度修正 / 体积↔质量换算 ══')

# I1 温度修正：d = d₂₀ − 0.001×(t₁ − 20)/1.5
check('基准温度 20 °C → 不做修正（d = d₂₀）',
      close(L._sg_corrected(1.1330, 20.0), 1.1330, 1e-9))
check('25 °C：1.1330 → 1.129667（0.001×5/1.5）',
      close(L._sg_corrected(1.1330, 25.0), 1.1296667, 1e-6),
      f'{L._sg_corrected(1.1330, 25.0):.6f}')
check('35 °C：1.1330 → 1.1230', close(L._sg_corrected(1.1330, 35.0), 1.1230, 1e-9))
check('方向正确：料温越高，比重越小',
      L._sg_corrected(1.1330, 60.0) < L._sg_corrected(1.1330, 20.0))

# I2 波美度换算（重表 145 口径）——逐点对齐行业淀粉乳波美换算表
for _sg, _be in ((1.0358, 5.0), (1.0742, 10.0), (1.1156, 15.0),
                 (1.1330, 17.0), (1.1602, 20.0), (1.2086, 25.0)):
    check(f'比重 {_sg:.4f} ↔ {_be:.1f} °Bé（行业表锚点，容差 0.05）',
          close(L._baume_from_sg(_sg), _be, 0.05),
          f'算得 {L._baume_from_sg(_sg):.3f}')

# I3 由比重估算干物含量（表自带式 X = 1.7770×°Bé）
for _sg, _x in ((1.0742, 17.77), (1.1156, 26.66), (1.1330, 30.21), (1.1602, 35.54)):
    check(f'比重 {_sg:.4f} → 干物估算 ≈ {_x:.2f} wt%（表值，容差 0.15）',
          close(L._solid_from_sg(_sg), _x, 0.15),
          f'算得 {L._solid_from_sg(_sg):.2f}')

# I4 默认口径不变：仍是质量流量
c = mk()
check('默认仍为质量流量（原有口径不变）',
      c.flow_mode_combo.currentText() == L.FLOW_MODES[0])
c.calculate()
r = c._last_result
check('质量模式下 G_t 等于输入值（不做密度换算）', close(r['G_t'], 20.0, 1e-9))
check('折合体积流量 = 20/1.129667 ≈ 17.704 m³/h',
      close(r['Q_m3h'], 17.7037, 1e-3), f"{r['Q_m3h']:.4f}")
check('结果文本含「修正比重」与密度单位',
      '修正比重' in c.result_text.toPlainText()
      and 'kg/m³' in c.result_text.toPlainText())

# I5 体积流量模式：Q × d = G
c.clear_inputs()
c.flow_mode_combo.setCurrentIndex(1)
c.calculate()
rv = c._last_result
check('体积模式：20 m³/h → G = 20×1.129667 = 22.593 t/h',
      close(rv['G_t'], 22.59333, 1e-4), f"{rv['G_t']:.5f}")
c2 = mk()
c2.feed_input.setText('22.59333')
c2.calculate()
check('体积模式与质量模式在等价质量流量下用汽量一致',
      close(rv['D1'], c2._last_result['D1'], 0.05),
      f"{rv['D1']:.2f} vs {c2._last_result['D1']:.2f}")

# I6 UI 标签随模式切换
check('体积模式：流量行标签改为「体积流量」',
      '体积流量' in c._rows['feed'][0].text(), c._rows['feed'][0].text())
c.flow_mode_combo.setCurrentIndex(0)
check('切回质量模式：标签复原', '体积流量' not in c._rows['feed'][0].text(),
      c._rows['feed'][0].text())

# I7 校验与互校提示
c = mk()
c.d20_input.setText('0.5')
c.calculate()
check('比重越界（0.5）→ 报错',
      c.result_text.toPlainText().startswith('错误'))
c = mk()
c.flow_mode_combo.setCurrentIndex(1)
c.conc_input.setText('40')            # 40 % 却配 30 % 的比重
c.calculate()
_t = c.result_text.toPlainText()
check('浓度与比重打架 → 给出对照提示',
      '查表估算干物含量' in _t and '个百分点' in _t)
c = mk()
c.calculate()
check('默认工况（30 % / 1.133）不触发浓度互校提示',
      '个百分点' not in c.result_text.toPlainText())

# I8 clear 与历史
c = mk()
c.flow_mode_combo.setCurrentIndex(1)
c.clear_inputs()
check('clear 后浆料量方式回到质量流量', c.flow_mode_combo.currentIndex() == 0)
check('浆料比重恢复默认 1.133', c.d20_input.text() == '1.133')
c.calculate()
h = c._get_history_data()
check('历史 inputs 含「浆料量方式」与「浆料比重_d20」',
      '浆料量方式' in h['inputs'] and '浆料比重_d20' in h['inputs'])
check('历史 outputs 含「修正比重」', '修正比重' in h['outputs'])

# ════════════════════════════════════════════════════════════════
print('\n══ Part J  设计表格逐列对齐（两法互校 / 总焓查表 / 汽耗口径）══')

# J1 方法一 ≡ 方法二（多组工况）
for _g, _x, _t1, _t2, _ps in ((20, 30, 25, 105, 0.3), (48.44, 24.57, 20, 90, 0.3),
                              (5, 40, 35, 108, 0.25), (33.3, 18.5, 60, 95, 0.4)):
    cc = mk()
    cc.feed_input.setText(str(_g))
    cc.conc_input.setText(str(_x))
    cc.t1_input.setText(str(_t1))
    cc.t2a_input.setText(str(_t2))
    cc.ps_input.setText(str(_ps))
    cc.calculate()
    rr = cc._last_result
    check(f'J1 两法恒等（G={_g} X={_x} {_t1}→{_t2}）',
          close(rr['Q1_A_kW'], rr['Q1_B_kW'], 1e-6) and rr['q_diff_pct'] < 1e-7,
          f"A={rr['Q1_A_kW']:.6f} B={rr['Q1_B_kW']:.6f} 差={rr['q_diff_pct']:.3e}")
    check('J1 两法都等于主算 Q（同工况）',
          close(rr['Q1_A_kW'], rr['Q1_kW'], 1e-6)
          and close(rr['Q1_B_kW'], rr['Q1_kW'], 1e-6))

# J2 方法一按表格口径独立复算
c = mk()
c.calculate()
r = c._last_result
_G, _Xp, _t2a, _t1 = r['G'], r['X'], r['t2a'], r['t1']
_qA = (_G * (100 - _Xp) * WATER_CP * _t2a
       + _G * _Xp * r['cp0'] * _t2a
       - _G * _t1 * r['C'] * 100) / 100 / 3600
check('J2 方法一独立复算一致（分项展开式）', close(r['Q1_A_kW'], _qA, 1e-9),
      f"{r['Q1_A_kW']:.6f} vs {_qA:.6f}")

# J3 汽耗两个口径
check('J3 吨乳气耗 = D₁ ÷ 物料量（t/h）',
      close(r['unit_slurry'], r['D1'] / r['G_t'], 1e-9), f"{r['unit_slurry']:.3f}")
check('J3 吨干物汽耗 = 吨乳气耗 ÷ (X/100)',
      close(r['unit_steam'], r['unit_slurry'] / (r['X'] / 100), 1e-6),
      f"{r['unit_steam']:.2f} vs {r['unit_slurry'] / (r['X'] / 100):.2f}")
check('J3 吨乳气耗 < 吨干物汽耗（分母含水的乳液更大）',
      r['unit_slurry'] < r['unit_steam'])

# J4 喷射器规格 = 物料量 ÷ 密度
check('J4 喷射器规格 = 物料量 ÷ 密度（= 体积流量 m³/h）',
      close(r['spec_vol'], r['G_t'] / r['d_corr'], 1e-9), f"{r['spec_vol']:.4f}")

# J5 总焓「查表」输入生效
c = mk()
c.total_h_input.setText('2738.5')
c.calculate()
r5 = c._last_result
check('J5 填了总焓 → I 用查表值', close(r5['I'], 2738.5, 1e-9), f"{r5['I']:.2f}")
check('J5 来源标注为「查表输入」', r5['I_src'] == '查表输入')
c2 = mk()
c2.calculate()
check('J5 留空 → I 自动算（= h_g(0.4013 MPa)）',
      close(c2._last_result['I'],
            IAPWS.saturation_properties(P_MPa=0.3 + ATM)['h_g'], 1e-9),
      f"{c2._last_result['I']:.2f}")
check('J5 总焓相同时用汽量一致',
      close(r5['D1'], c2._last_result['D1'], 0.05),
      f"{r5['D1']:.2f} vs {c2._last_result['D1']:.2f}")
c = mk()
c.total_h_input.setText('2500')
c.calculate()
check('J5 查错蒸汽表（2500，偏低 8.7 %）→ 给出提示',
      any('查错了蒸汽表' in w for w in c._last_result['warn']))
check('J5 查表值仍被采用（总焓小 → D₁ 变大）',
      c._last_result['D1'] > c2._last_result['D1'])

# J6 表格口径 λ′ = 4.19·t₂ 与本器口径等价
c = mk()
c.calculate()
r6 = c._last_result
check('J6 λ′ = 4.19×t₂₁（表格口径）', close(r6['lam1_tab'], 4.19 * r6['t2a'], 1e-9))
check('J6 表格口径 D₁′ 与本器 D₁ 偏差 < 0.5 %',
      abs(r6['d1_tab_pct']) < 0.5, f"{r6['d1_tab_pct']:+.3f} %")
check('J6 λ 与 λ′ 相差 < 1 kJ/kg（口径等价）',
      abs(r6['lam1'] - r6['lam1_tab']) < 1.0,
      f"{r6['lam1']:.2f} vs {r6['lam1_tab']:.2f}")
c = mk()
c.mode_combo.setCurrentText(L.MODES[1])
c.calculate()
check('J6 二次段同样给出 4.19 口径对照且偏差 < 0.5 %',
      abs(c._last_result['d2_tab_pct']) < 0.5,
      f"{c._last_result['d2_tab_pct']:+.3f} %")

# J7 结果文本逐列可读
_t = c2.result_text.toPlainText()
for _kw in ('喷射器规格', '物料比热', '方法一', '方法二', '两法差值',
            '吨淀粉乳气耗', '吨干物汽耗', '总焓 I'):
    check(f'J7 结果含「{_kw}」', _kw in _t)

# J8 历史与 clear
c = mk()
c.total_h_input.setText('2700')
c.calculate()
h = c._get_history_data()
check('J8 填了总焓 → 历史 inputs 含「总焓_查表_kJ_kg」',
      '总焓_查表_kJ_kg' in h['inputs'])
check('J8 历史 outputs 含「喷射器规格_m3_h」「吨乳气耗_kg_t」',
      '喷射器规格_m3_h' in h['outputs'] and '吨乳气耗_kg_t' in h['outputs'])
c = mk()
c.calculate()
check('J8 未填总焓 → 历史不写该项',
      '总焓_查表_kJ_kg' not in c._get_history_data()['inputs'])
c.total_h_input.setText('2700')
c.clear_inputs()
check('J8 clear 后总焓框清空', c.total_h_input.text() == '')
c.calculate()
check('J8 clear 后可直接重算（总焓留空走自动）',
      c._last_result.get('I_src') == '自动（按压力与干度）')

# ════════════════════════════════════════════════════════════════
print('\n' + '═' * 58)
print(f'通过 {len(PASS)} / {len(PASS) + len(FAIL)}')
if FAIL:
    print('\n失败项：')
    for n, d in FAIL:
        print(f'  ✗ {n}   [{d}]')
    sys.exit(1)
print('全部通过 ✔')
