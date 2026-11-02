# -*- coding: utf-8 -*-
"""Qt 内置文字（右键菜单 / 标准按钮）汉化回归测试

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_qt_i18n.py

背景
════════════════════════════════════════════════════════════════════════
应用自己的文案全是中文，但 Qt **内置**的那批字符串默认跟随英文：

    输入框/结果框右键菜单   Undo / Redo / Cut / Copy / Paste / Delete / Select All
    标准对话框按钮          OK / Cancel / Yes / No
    文件对话框、下拉框空提示

这些不是我们写的字符串，靠改控件样式改不掉，只能装 QTranslator
（qtbase_zh_CN，随 PySide6 分发）。本测试把「装了才会中文化」这件事钉住：

Part A  反证：不装翻译时菜单是英文 —— 证明下面的断言真能判失败
Part B  装上 qtbase_zh_CN 后，输入框右键菜单变中文
Part C  结果框（QTextEdit）右键菜单同样变中文
Part D  标准按钮变中文（QDialogButtonBox）
Part E  卸载翻译后回到英文 —— 证明生效的确实是翻译器，不是环境碰巧
Part F  入口钉住：main() 里真的调了这个安装函数、翻译文件找得到
════════════════════════════════════════════════════════════════════════
"""
import os
import sys
import ast
import tempfile

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
for p in [ROOT, os.path.join(ROOT, 'modules'),
          os.path.join(ROOT, 'modules', 'chemical_calculations')]:
    sys.path.insert(0, p)

from PySide6.QtWidgets import (                          # noqa: E402
    QApplication, QMessageBox, QLineEdit, QTextEdit, QDialogButtonBox
)

QMessageBox.warning = staticmethod(
    lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(
    lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.information = staticmethod(
    lambda *a, **k: QMessageBox.StandardButton.Ok)

from data_manager import DataManager                      # noqa: E402

# DataManager 单例先指向临时文件，别碰用户真实数据
TMPDIR = tempfile.mkdtemp()
DataManager.get_instance(data_file=os.path.join(TMPDIR, 'i18n_test.json'))

app = QApplication(sys.argv)

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
    print(('PASS' if cond else 'FAIL') + f'  {name}'
          + (f'   [{detail}]' if detail and not cond else ''))


def menu_texts(widget):
    """取控件默认右键菜单里的动作文本（空动作与分隔线跳过）"""
    menu = widget.createStandardContextMenu()
    texts = [a.text() for a in menu.actions() if a.text().strip()]
    menu.deleteLater()
    return texts


def has_cjk(s):
    return any('\u4e00' <= ch <= '\u9fff' for ch in s)


# ── A. 反证：不装翻译时是英文 ──
edit = QLineEdit()
before = menu_texts(edit)
check('A1 未装翻译时右键菜单有 Copy（英文原样）',
      any('Copy' in t for t in before), before)
check('A2 未装翻译时菜单里没有中文',
      not any(has_cjk(t) for t in before), before)

# ── 加载被测模块（模块级不自动装翻译，由 main() 触发）──
import main                                              # noqa: E402

check('A4 导入 main 不会静默装上翻译（装翻译只在 main() 里）',
      main._QT_TRANSLATOR is None, main._QT_TRANSLATOR)

# ── F1/F2 先把「找得到翻译文件」这件事验掉，后面才谈加载 ──
dirs = main._qt_translation_dirs()
check('F1 能定位到 Qt 翻译目录', bool(dirs), dirs)
found = [d for d in dirs
         if os.path.isfile(os.path.join(d, 'qtbase_zh_CN.qm'))]
check('F2 目录里有 qtbase_zh_CN.qm', bool(found), dirs)

# ── B. 装上翻译后输入框菜单中文化 ──
t = main.install_qt_chinese_translations(app)
check('B0 安装函数返回翻译器（非 None）', t is not None)
after = menu_texts(edit)
check('B1 输入框右键菜单出现「复制」',
      any('复制' in x for x in after), after)
check('B2 输入框右键菜单出现「粘贴」',
      any('粘贴' in x for x in after), after)
check('B3 输入框右键菜单出现「全选」',
      any('全选' in x for x in after), after)
check('B4 已建控件也立即生效（无需重建）',
      not any('Copy' in x for x in after), after)

# ── C. 结果框（QTextEdit）同样中文化 ──
result = QTextEdit()
result.setReadOnly(True)
rtexts = menu_texts(result)
check('C1 结果框右键菜单中文化（含「复制」）',
      any('复制' in x for x in rtexts), rtexts)
check('C2 结果框菜单不再出现 Copy', 
      not any('Copy' in x for x in rtexts), rtexts)

# ── D. 标准按钮中文化 ──
box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
ok_text = box.button(QDialogButtonBox.Ok).text()
cancel_text = box.button(QDialogButtonBox.Cancel).text()
check('D1 「确定」按钮显示中文', '确定' in ok_text, ok_text)
check('D2 「取消」按钮显示中文', '取消' in cancel_text, cancel_text)

# ── E. 卸载翻译 → 回到英文（证明起作用的是翻译器本身）──
QApplication.instance().removeTranslator(t)
back = menu_texts(edit)
check('E1 卸载翻译后菜单回到英文 Copy',
      any('Copy' in x for x in back) and not any('复制' in x for x in back), back)

# 装回去，保持与真实运行一致
main.install_qt_chinese_translations(app)
again = menu_texts(edit)
check('E2 可重复安装，第二次同样生效',
      main._QT_TRANSLATOR is not None and any('复制' in x for x in again), again)

# ── F3 入口钉住：main() 里真的调了 ──
src = open(os.path.join(ROOT, 'main.py'), encoding='utf-8').read()
tree = ast.parse(src)
main_fn = next((n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == 'main'), None)
calls = []
if main_fn is not None:
    for n in ast.walk(main_fn):
        if isinstance(n, ast.Call):
            fn = n.func
            calls.append(fn.id if isinstance(fn, ast.Name)
                         else getattr(fn, 'attr', ''))
check('F3 main() 函数里调用了 install_qt_chinese_translations',
      'install_qt_chinese_translations' in calls, calls)

# 调用点必须在建窗口（ChemCal()）之前 —— 否则已建控件不会重译
order_ok = False
if main_fn is not None:
    lines = src.splitlines()
    start = main_fn.lineno
    end = max(getattr(n, 'end_lineno', start) for n in ast.walk(main_fn))
    body = '\n'.join(lines[start - 1:end])
    i_tr = body.find('install_qt_chinese_translations(')
    i_win = body.find('ChemCal()')
    order_ok = 0 <= i_tr < i_win
check('F4 装翻译发生在创建主窗口之前', order_ok)

# 翻译器必须被长期持有（否则被回收后菜单会退回英文）
check('F5 翻译器有模块级引用（_QT_TRANSLATOR 非 None）',
      main._QT_TRANSLATOR is not None)

# ── 汇总 ──
print('\n' + '=' * 50)
print(f'通过 {len(PASS)} 项, 失败 {len(FAIL)} 项')
if FAIL:
    for name, detail in FAIL:
        print(f'  FAIL: {name}  {detail}')
    sys.exit(1)
print('ALL PASS')
