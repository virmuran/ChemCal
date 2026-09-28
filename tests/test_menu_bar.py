# -*- coding: utf-8 -*-
"""菜单栏结构回归测试（v1.13.1 精简版）

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_menu_bar.py

背景
════════════════════════════════════════════════════════════════════════
菜单栏原先 14 项，其中多项属于「点开没价值 / 点了没反馈」：

    「备份数据」      备份写到 ~/.ChemCal/data/ 隐藏目录里，用户找不到
    「刷新所有模块」  开发期调试功能，点了弹「已刷新 4 个模块」但界面无变化
    「常见问题」      数据路径写成 AppData\Roaming、教安装包用户 pip install
    「用户手册」      还写「压降计算支持导出 PDF」（实际全部计算器都能出）
    主题菜单          切完没有勾选标记，不看状态栏不知道当前是哪套

v1.13.1 精简为 9 项（文件 3 / 主题 3 / 帮助 4）并补齐「打开数据目录」入口，
本测试把新结构钉死，防止回退。

Part A  菜单结构
    A1 三个顶级菜单：文件 / 主题 / 帮助
    A2 文件菜单 = 工程信息... / 打开数据目录 / 分隔符 / 退出
    A3 帮助菜单 = 检查更新 / 使用说明 / 诊断信息 / 关于 ChemCal
    A4 全部菜单项已连接槽（triggered 有接收器）
Part B  主题菜单勾选
    B1 三个主题项、均可勾选、互斥
    B2 当前主题项已勾选（且只勾一个）
    B3 切换主题后勾选跟随
Part C  已移除项不再存在
    C1 「备份数据」「刷新所有模块」不在文件菜单
    C2 「用户手册」「常见问题」「系统信息」「查看日志」「开源许可」不在帮助菜单
Part D  说明类内容与实际一致（原先写错的正是这里）
    D1 使用说明：四个标签页 + 52 计算器 + 21 类换算
    D2 使用说明：已清除 AppData 路径 / pip 安装 / reportlab 等过时内容
    D3 诊断信息：版本 + 数据目录 + 日志
    D4 关于：含 MIT 与 LICENSE 指引，不再宣传已删模块
════════════════════════════════════════════════════════════════════════
"""
import os
import sys
import tempfile

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
for p in [ROOT, os.path.join(ROOT, 'modules'),
          os.path.join(ROOT, 'modules', 'chemical_calculations')]:
    sys.path.insert(0, p)

from PySide6.QtWidgets import QApplication, QMessageBox   # noqa: E402


def _mk(_kind):
    def f(parent=None, title='', text='', *a, **k):
        return QMessageBox.StandardButton.Ok
    return staticmethod(f)


QMessageBox.warning = _mk('warning')
QMessageBox.critical = _mk('critical')
QMessageBox.information = _mk('info')

from data_manager import DataManager                      # noqa: E402
from version import VERSION                               # noqa: E402
from PySide6.QtCore import SIGNAL                         # noqa: E402

# DataManager 单例必须**先**指向临时文件，否则 ChemCal() 会用默认路径
# （~/.ChemCal/data/）—— 那会污染用户真实数据文件
TMPDIR = tempfile.mkdtemp()
DM = DataManager.get_instance(
    data_file=os.path.join(TMPDIR, 'menu_bar_test.json'))

app = QApplication(sys.argv)

FAILED = 0


def check(name, cond, detail=''):
    global FAILED
    mark = 'PASS' if cond else 'FAIL'
    print(f'{mark}  {name}' + (f'   [{detail}]' if detail and not cond else ''))
    if not cond:
        FAILED += 1


from main import ChemCal                                 # noqa: E402

win = ChemCal()


# 菜单栏对象必须**一次性取好并永久持有**。
# 实测 PySide6 offscreen 下，win.menuBar() / act.menu() / menu.actions() 返回的
# wrapper 一旦离开作用域就会连带删除底层 C++ 对象（QMenuBar 是懒创建、QMenu 归
# Python 所有、顶级 QAction 被删还会连带删掉它的子菜单），表现为
# RuntimeError: Internal C++ object already deleted。所以这里全部存进模块级容器。
_MENUBAR = win.menuBar()
_TOP = list(_MENUBAR.actions())
_MENUS, _ITEMS = {}, {}
for _a in _TOP:
    _m = _a.menu()
    if _m is not None:
        _MENUS[_a.text()] = _m
        _ITEMS[_a.text()] = list(_m.actions())


def _menu_actions(title):
    """某顶级菜单的动作列表（已永久持有）"""
    return _ITEMS.get(title, [])


def _texts(title):
    """菜单项文本（含空串代表的分隔符）"""
    return [a.text() for a in _menu_actions(title)]


def _labels(title):
    """非分隔符项文本"""
    return [a.text() for a in _menu_actions(title) if not a.isSeparator()]


# ── Part A 菜单结构 ───────────────────────────────────────────────────
print('Part A  菜单结构')
tops = [a.text() for a in _TOP]
check('A1 三个顶级菜单：文件 / 主题 / 帮助',
      tops == ['文件', '主题', '帮助'], str(tops))

check('A2 文件菜单 = 工程信息... / 打开数据目录 / ─ / 退出',
      _texts('文件') == ['工程信息...', '打开数据目录', '', '退出'],
      str(_texts('文件')))

check('A3 帮助菜单 = 检查更新 / 使用说明 / 诊断信息 / 关于 ChemCal',
      _labels('帮助') == ['检查更新', '使用说明', '诊断信息', '关于 ChemCal'],
      str(_labels('帮助')))

all_acts = [a for a in _menu_actions('文件') if not a.isSeparator()] \
    + _menu_actions('主题') + _menu_actions('帮助')
no_recv = [a.text() for a in all_acts
           if a.receivers(SIGNAL('triggered()')) == 0]
check('A4 全部菜单项已连接槽（triggered 有接收器）', not no_recv, str(no_recv))

# ── Part B 主题菜单勾选 ───────────────────────────────────────────────
print('Part B  主题菜单勾选')
t_acts = _menu_actions('主题')
# Qt6 的 QAction 没有 group()/actionGroup() 反向查询，改从 QActionGroup 侧核对
_grp = win._theme_group                       # win 自身持有该对象，安全
_grp_texts = [a.text() for a in _grp.actions()]
check('B1 三个主题项、均可勾选、互斥（同一 QActionGroup）',
      len(t_acts) == 3 and all(a.isCheckable() for a in t_acts)
      and _grp.isExclusive()
      and _grp_texts == [a.text() for a in t_acts],
      str(_grp_texts))

cur = win.theme_manager.current_theme
checked = [a.text() for a in t_acts if a.isChecked()]
want = dict(ChemCal.THEME_LABELS)[cur]
check(f'B2 当前主题（{cur}）项已勾选且只勾一个',
      checked == [want], str(checked))

win.theme_manager.set_theme('dark')
checked2 = [a.text() for a in _menu_actions('主题') if a.isChecked()]
check('B3 切换主题（dark）后勾选跟随',
      checked2 == ['深色主题'], str(checked2))
win.theme_manager.set_theme(cur)          # 还原

# ── Part C 已移除项不再存在 ───────────────────────────────────────────
print('Part C  已移除项不再存在')
f_labels, h_labels = _labels('文件'), _labels('帮助')
check('C1 「备份数据」「刷新所有模块」已从文件菜单移除',
      not ({'备份数据', '刷新所有模块'} & set(f_labels)), str(f_labels))

gone = {'用户手册', '常见问题', '系统信息', '查看日志', '开源许可'}
check('C2 五项已合并/移除项不在帮助菜单',
      not (gone & set(h_labels)), str(h_labels))

# ── Part D 说明类内容与实际一致 ───────────────────────────────────────
print('Part D  说明类内容与实际一致')
captured = {}
_orig = ChemCal._show_scrollable_dialog


def _cap(self, title, content):
    """拦下对话框内容（真 exec() 在离屏环境会永久阻塞）"""
    captured[title] = content


ChemCal._show_scrollable_dialog = _cap
try:
    win._show_usage_guide()
    g = captured.get('使用说明', '')
    check('D1 使用说明含四个标签页 / 52 计算器 / 21 类换算',
          all(k in g for k in ('工程计算', '计算历史', '换算器', '资料库',
                               '52 个计算器', '21 类单位换算')), g[:120])

    bad = [k for k in ('AppData', 'pip install', 'reportlab',
                       'requirements.txt') if k in g]
    check('D2 使用说明已清除与实现不符的旧内容（AppData/pip/reportlab）',
          not bad, str(bad))

    win._show_diagnostics()
    d = captured.get('诊断信息', '')
    check('D3 诊断信息含版本 / 数据目录 / 日志',
          VERSION in d and '数据目录' in d and '最近 50 条日志' in d, d[:120])

    win._show_about()
    a = captured.get('关于 ChemCal', '')
    check('D4 关于含 MIT 与 LICENSE 指引，且不再宣传已删模块',
          'MIT' in a and 'LICENSE' in a
          and not any(k in a for k in ('结晶罐', '待办事项', '笔记')), a[:120])
finally:
    ChemCal._show_scrollable_dialog = _orig

# ── 汇总 ─────────────────────────────────────────────────────────────
total = 4 + 3 + 2 + 4
print(f'\n共 {total} 项，通过 {total - FAILED}，失败 {FAILED}')
sys.exit(1 if FAILED else 0)
