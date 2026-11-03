# -*- coding: utf-8 -*-
"""结论条（答案置顶）回归测试
纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_conclusion_bar.py

钉住：
  A. 结论提取（═══ 三段式 / 【】小节式 / 嵌套子标题 / 宁缺勿错）
  B. 关键词捞行（数值行 / 标题行拼接下一行 / 公式行跳过 / 单位行不算公式）
  C. 结论条 UI（自动装配到结果框上方 / 计算后显示 / 清空后收起 / 显式结论优先）
  D. 主题 QSS：三套主题都必须有 conclusionBar 规则（缺了深色下会看不清）
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

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}' + (f'  [{detail}]' if detail and not cond else ''))


# ── 纯函数部分（不依赖 Qt）──
from calculator_base import (
    extract_conclusion, rows_by_keys, build_conclusion_html,
    _find_titles, _is_formula, CONCLUSION_KEYS,
)

# ══════════════ A. 结论提取 ══════════════
print('── A. extract_conclusion ──')

t1 = """═══════════
 输入参数
══════════

    流量: 70.0 m³/h

══════════
计算结果
══════════

    理论计算管径: 143.7 mm

    推荐标准管径: DN150
    • 实际流速: 1.10 m/s

══════════
计算公式
══════════
    d = 18.81 × ...
"""
title, rows = extract_conclusion(t1)
check('A1 三段式取到计算结果节', title == '计算结果', str(title))
check('A2 取前 3 行', rows == ['理论计算管径: 143.7 mm', '推荐标准管径: DN150', '实际流速: 1.10 m/s'], str(rows))

t2 = """闪蒸罐计算（汽液分离罐筒体尺寸）
==========================================================
【一、二次蒸汽（口径核对）】
闪蒸汽量 D_f      = 0.145 t/h

【二、罐体尺寸】
→ 圆整后设计内径  = 0.3515 m
→ 设备规格        = φ400 × 800 mm（筒体，不含封头）
罐高 H            = 0.8 m

口径说明：……
"""
title, rows = extract_conclusion(t2)
check('A3 【】式文本无计算结果节 → 空（宁缺勿错）', (title, rows) == (None, []), str((title, rows)))

t3 = """【计算结果】
理论内径 D₀     = 293 mm
保险系数 k        = 1.20
【圆整说明】
→ 放大后内径      = 0.3515 m
"""
title, rows = extract_conclusion(t3)
check('A4 【】节命中且子标题后的行继续算节体', title == '【计算结果】' and rows == [
    '理论内径 D₀     = 293 mm', '保险系数 k        = 1.20',
    '放大后内径      = 0.3515 m'], str((title, rows)))

t4 = "没有分节的普通文本"
check('A5 无分节 → 空', extract_conclusion(t4) == (None, []))
check('A6 空文本 → 空', extract_conclusion('') == (None, []))
check('A7 None 安全', extract_conclusion(None) == (None, []))

t5 = """════
计算结果
════
• 推荐标准管径: DN80
"""
title, rows = extract_conclusion(t5)
check('A8 项目符号被剥掉', rows == ['推荐标准管径: DN80'], str(rows))

t6 = """════
安全评估
════
结论: ❌ 面积不足！
════
计算结果
════
面积: 73 m²
"""
title, rows = extract_conclusion(t6)
check('A9 优先级：计算结果 > 安全评估', title == '计算结果', str(title))

# ══════════════ B. 关键词捞行 ══════════════
print('── B. rows_by_keys ──')

lines = [
    '计算条件: P=0.1~0.3MPa',
    '理论计算管径: 143.7 mm',
    '推荐标准管径: DN150',
    '• 实际流速: 1.10 m/s',
]
check('B1 三个关键词各取一行',
      rows_by_keys(lines, ('推荐标准管径', '实际流速', '压降')) ==
      ['推荐标准管径: DN150', '实际流速: 1.10 m/s'])

lines2 = ['管道重量: 157.70 N/m', '总重量: 288.91 N/m', '总重量: 288.9 N/m']
check('B2 同名行只取第一个', rows_by_keys(lines2, ('总重量',)) == ['总重量: 288.91 N/m'])

lines3 = ['1. 有效过滤面积:', '• 计算值: 0.4167 m²', '• 取值: 0.4170 m²']
check('B3 标题行拼下一行数值', rows_by_keys(lines3, ('有效过滤面积',)) ==
      ['有效过滤面积：计算值: 0.4167 m²'])

check('B4 纯公式行跳过', rows_by_keys(
    ['有效过滤面积: A = Q/(3600*v)'], ('有效过滤面积',)) == [])
check('B5 等号右边是数字 → 不是公式', not _is_formula('过滤面积 A = 50.00 m²'))
check('B6 单位结尾的等式不算公式', not _is_formula('设备规格 = φ400 × 800 mm'))
check('B7 公式行（无单位结尾）', _is_formula('滤网内径: D = √(A/(π*1.2)) * 1000'))

check('B8 无命中 → 空', rows_by_keys(['流量: 5 m³/h'], ('推荐管径',)) == [])
check('B9 中文类名也登记了', '管径计算' in CONCLUSION_KEYS and '换热器计算' in CONCLUSION_KEYS)

# ══════════════ C. 结论条 UI（真实页面） ══════════════
print('── C. 结论条 UI ──')
import tempfile
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

_mk = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = _mk
QMessageBox.critical = _mk
QMessageBox.information = _mk
QMessageBox.question = _mk

from data_manager import DataManager
DataManager.get_instance(data_file=os.path.join(tempfile.mkdtemp(), 'concl.json'))
app = QApplication(sys.argv)


def _load(mod_name, cls_name):
    spec = importlib.util.spec_from_file_location(
        't_concl_' + mod_name, os.path.join(CALC_DIR, mod_name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, cls_name)


def _norm(s):
    return ''.join(str(s).split())


def _click_calc(w):
    for b in w.findChildren(QPushButton):
        if _norm(b.text()) in ('计算', '开始计算'):
            b.click()
            app.processEvents()
            return True
    return False


pipe = _load('pipe_diameter_calculator', '管径计算')()
pipe.resize(1280, 900)
pipe.show()
app.processEvents()
bar = pipe._conclusion_bar
check('C1 singleShot(0) 装配结论条', bar is not None)
check('C2 计算前结论条隐藏', bar.isHidden())
_bar_y = bar.mapTo(pipe, bar.rect().topLeft()).y()
_rt_y = pipe.result_text.mapTo(pipe, pipe.result_text.rect().topLeft()).y()
check('C3 结论条在 result_text 正上方', 0 <= _bar_y < _rt_y,
      f'bar_y={_bar_y} rt_y={_rt_y}')

_click_calc(pipe)
check('C4 计算后结论条显示', not bar.isHidden())
check('C5 结论含推荐管径 DN150', 'DN150' in bar.text(), bar.text())
plain = _strip = bar.text().replace('&nbsp;', ' ')
import re as _re
plain = _re.sub(r'<[^>]+>', '', plain)
check('C6 结论是「计算结果」口径', '计算结果' in plain, plain)

pipe.result_text.clear()
app.processEvents()
check('C7 结果清空 → 结论条收起', bar.isHidden())

# 显式结论优先
pipe2 = _load("pipe_diameter_calculator", "管径计算")()
pipe2.show()
app.processEvents()
app.processEvents()
pipe2.result_text.setPlainText('随便一段结果 42')
app.processEvents()
pipe2.set_conclusion('推荐管径 DN80（显式）')
check('C8 显式结论优先于自动提取', '显式' in pipe2.conclusion_text, pipe2.conclusion_text)
pipe2.result_text.setPlainText('另一段结果 7')
app.processEvents()
check('C9 文本变化后显式结论仍在（页面负责更新）', '显式' in pipe2.conclusion_text)
pipe2.clear_conclusion()
check('C10 clear_conclusion 回到自动提取（空文本→隐藏）', pipe2._conclusion_bar.isHidden())

# ══════════════ D. 主题 QSS ══════════════
print('── D. 主题 QSS ──')
sys.path.insert(0, ROOT)
from theme_manager import ThemeManager
_tm = ThemeManager()
for name in ('light', 'dark', 'blue'):
    qss = getattr(ThemeManager, 'SEMANTIC_RULES', {}).get(name, '')
    check(f'D1 {name} 主题有 conclusionBar 规则', 'QLabel#conclusionBar' in qss)
    # __init__ 会把 SEMANTIC_RULES 追加进三套主题 —— 实际下发的是 themes 里的
    check(f'D2 {name} 实际生效的主题串含语义规则',
          'QLabel#conclusionBar' in _tm.themes[name])

# ── 汇总 ──
print(f'\n{"═" * 50}')
print(f'通过 {len(PASS)}  /  失败 {len(FAIL)}')
if FAIL:
    print('失败清单:')
    for n, d in FAIL:
        print('  ✗', n, d)
    sys.exit(1)
