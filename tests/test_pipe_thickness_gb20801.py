# -*- coding: utf-8 -*-
"""管道壁厚计算器回归测试（GB/T 20801.3-2020 核对）
纯 PySide6 offscreen 运行，不依赖 pytest：
    .venv/Scripts/python.exe tests/test_pipe_thickness_gb20801.py

核对依据：
- GB/T 20801.3-2020 式(10)（同 ASME B31.3 §304.1.2）: t = P·D/(2·(S·Φ + P·Y))
- GB/T 20801.3-2020 表3  纵向焊接接头系数 Φ
- GB/T 20801.3-2020 表16 Y 系数（铁素体: ≤482→0.4、≥538→0.7；奥氏体: ≤566→0.4、≥621→0.7）
- ASME B36.10M 管表 Sch 壁厚
"""
import os
import sys
import tempfile
import importlib.util

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CALC_DIR = os.path.join(ROOT, 'modules', 'chemical_calculations', 'calculators')
for p in [ROOT, os.path.join(ROOT, 'modules'),
          os.path.join(ROOT, 'modules', 'chemical_calculations')]:
    sys.path.insert(0, p)

from PySide6.QtWidgets import QApplication, QMessageBox

# 拦截模态弹窗（离屏下 exec() 会永久阻塞）
def _mk(kind):
    def f(parent=None, title='', text='', *a, **k):
        return QMessageBox.StandardButton.Ok
    return staticmethod(f)
QMessageBox.warning = _mk('warning')
QMessageBox.critical = _mk('critical')
QMessageBox.information = _mk('info')

# DataManager 隔离到临时文件，避免污染 ~/.ChemCal/data/
from data_manager import DataManager
DataManager.get_instance(data_file=os.path.join(tempfile.mkdtemp(), 'test.json'))

app = QApplication(sys.argv)

spec = importlib.util.spec_from_file_location(
    't_pipe_thickness', os.path.join(CALC_DIR, 'pipe_thickness_calculator.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

w = mod.管道壁厚()

PASS, FAIL = [], []

def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}' + (f'  [{detail}]' if detail and not cond else ''))

def run_calc(p, t, d, s, ej, y, c1, c2):
    w.pressure_input.setText(str(p))
    w.temp_input.setText(str(t))
    w.diameter_input.setText(str(d))
    w.stress_input.setText(str(s))
    w.weld_input.setText(str(ej))
    w.y_input.setText(str(y))
    w.thinning_input.setText(str(c1))
    w.corrosion_input.setText(str(c2))
    w.calculate()
    return w.result_text.toPlainText()

def fmt(x, n=4):
    return f'{x:.{n}f}'

# ── 1. 公式核对：GB/T 20801.3-2020 式(10) ──
# 手算案例 A：P=1.0, D=168.3, S=130, Φ=1.0, Y=0.4, C=2.0
tA = 1.0 * 168.3 / (2 * 130 * 1.0 + 2 * 1.0 * 0.4)   # = 0.6452 mm
txtA = run_calc(1.0, 180, 168.3, 130, 1.0, 0.4, 0.5, 1.5)
check('案例A 理论壁厚 t=0.65mm (手算0.6452)', f'{tA:.2f}' in txtA and '0.65' in txtA, tA)
check('案例A 设计壁厚=2.65mm (0.6452+2.0)', f'{tA + 2.0:.2f}' in txtA)
# 查找逻辑取第一个满足要求的标准壁厚：2.65mm → Sch5S(2.77)
lookupA = w._lookup_pipe_schedule(168.3, round(tA + 2.0, 2))
check('案例A Sch匹配 第一个满足项=Sch5S/2.77',
      lookupA is not None and lookupA[0] == 'Sch5S' and lookupA[1] == 2.77, str(lookupA))
check('案例A 薄壁条件满足', '满足' in txtA)

# ── 2. Y 系数表核对（GB/T 20801.3-2020 表16）──
# 奥氏体 316 @500°C：应取 Y=0.4（≤566°C），修复前错误取 0.7
w.material_combo.setCurrentText('316(0Cr17Ni12Mo2) (500°C) - GB/T1220 奥氏体不锈钢')
check('Y自动匹配: 奥氏体500°C→0.4（修复前为0.7）', w.y_input.text() == '0.4', w.y_input.text())
# 铁素体 @500°C：应取 Y=0.5（482<T<538）
w.temp_input.setText('500')
w.on_material_changed('20# (400°C) - GB/T699 优质碳素结构钢')
check('Y自动匹配: 铁素体500°C→0.5', w.y_input.text() == '0.5', w.y_input.text())
# 铁素体 @550°C：应取 Y=0.7（≥538°C）
w.temp_input.setText('550')
w.on_material_changed('20# (400°C) - GB/T699 优质碳素结构钢')
check('Y自动匹配: 铁素体550°C→0.7', w.y_input.text() == '0.7', w.y_input.text())
# 铁素体 20# @300°C → 0.4
w.temp_input.setText('300')
w.on_material_changed('20# (300°C) - GB/T699 优质碳素结构钢')
check('Y自动匹配: 铁素体300°C→0.4', w.y_input.text() == '0.4', w.y_input.text())
# Y 影响方向核对：奥氏体 316 @500°C（Y=0.4），手算 t=0.9786
w.temp_input.setText('500')
w.material_combo.setCurrentText('316(0Cr17Ni12Mo2) (500°C) - GB/T1220 奥氏体不锈钢')
tB = 2.0 * 114.3 / (2 * 116 * 1.0 + 2 * 2.0 * 0.4)   # = 0.9786 mm
txtB = run_calc(2.0, 500, 114.3, 116, 1.0, 0.4, 0.5, 0.5)
check('案例B 奥氏体Y=0.4 理论壁厚=0.98mm', f'{tB:.2f}' in txtB, txtB[:200])

# ── 3. 焊接接头系数核对（GB/T 20801.3-2020 表3）──
w.weld_combo.setCurrentText('1.0 - 电熔焊 单面对接焊 100%无损检测')
check('表3: 单面对接焊 100%RT → 1.0', w.weld_input.text() == '1.0', w.weld_input.text())
w.weld_combo.setCurrentText('0.8 - 电熔焊 单面对接焊 不作无损检测')
check('表3: 单面对接焊 不作RT → 0.80', w.weld_input.text() == '0.8', w.weld_input.text())
w.weld_combo.setCurrentText('0.85 - 电熔焊 双面对接焊 不作无损检测')
check('表3: 双面对接焊 不作RT → 0.85', w.weld_input.text() == '0.85', w.weld_input.text())
# Φ=0.8 影响核对：P=4.0, D=114.3, S=130, Φ=0.8, Y=0.4 → t=2.1648
tC = 4.0 * 114.3 / (2 * 130 * 0.8 + 2 * 4.0 * 0.4)   # = 2.1648 mm
txtC = run_calc(4.0, 300, 114.3, 130, 0.8, 0.4, 0.5, 1.5)
check('案例C Φ=0.8 理论壁厚=2.16mm', f'{tC:.2f}' in txtC, txtC[:200])

# ── 4. 薄壁适用条件（t≤D/6 且 P/(S·Φ)≤0.385）──
tD = 55.0 * 168.3 / (2 * 130 * 1.0 + 2 * 55.0 * 0.4)  # = 30.45 mm > D/6=28.05
txtD = run_calc(55.0, 300, 168.3, 130, 1.0, 0.4, 0.5, 1.5)
check('厚壁工况 t=30.45>D/6=28.05 触发警告', '不满足' in txtD and '厚壁' in txtD)

# ── 5. Sch 管表锚点核对（ASME B36.10M）──
anchors = [
    ((50, 60.3),  'Sch40', 3.91),
    ((80, 88.9),  'Sch40', 5.49),
    ((100, 114.3), 'Sch40', 6.02),
    ((100, 114.3), 'Sch80', 8.56),
    ((150, 168.3), 'Sch40', 7.11),
    ((150, 168.3), 'Sch80', 10.97),
    ((200, 219.1), 'Sch40', 8.18),
]
for key, sch, thk in anchors:
    table = dict((n, v) for n, v in w.PIPE_SCHEDULES[key])
    check(f'Sch锚点 DN{key[0]} {sch}={thk}mm', table.get(sch) == thk,
          str(table.get(sch)))

# ── 6. 历史记录钩子 ──
h = w._get_history_data()
check('历史钩子 _get_history_data 非空', bool(h and h.get('inputs') and h.get('outputs')))

# ── 汇总 ──
print('\n' + '=' * 50)
print(f'通过 {len(PASS)} 项, 失败 {len(FAIL)} 项')
if FAIL:
    for name, detail in FAIL:
        print(f'  FAIL: {name}  {detail}')
    sys.exit(1)
print('ALL PASS')
