# -*- coding: utf-8 -*-
"""系统托盘 / 关闭行为回归测试（v1.14.0 新增）

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_tray.py

背景
════════════════════════════════════════════════════════════════════════
原先点窗口「X」直接退出，没有任何后台常驻方式。v1.14.0 增加右下角托盘：

    · 点 X → 三选一（最小化到托盘 / 退出 ChemCal / 取消），可勾选「记住我的选择」
    · 记住后写入 settings.close_action，之后点 X 直接照办、不再打扰
    · 改回来的唯一入口：托盘右键 → 「关闭窗口时」子菜单
    · 托盘右键：显示主窗口 / 工程信息... / 关闭窗口时 ▸ / 退出 ChemCal
    · 单击或双击托盘图标唤回窗口

两个易漏的坑，本测试专门钉住：
    ① **无托盘可用时绝不能把窗口藏起来** —— 否则「窗口没了、程序还在」，
       用户找不回来。此时必须退回真退出。
    ② **「退出」类入口一律不能走「收进托盘」** —— 菜单「文件→退出」与更新的
       「安装并重启」都必须真退出（后者若不退出，安装向导要覆盖的 exe 仍被占用）。

离屏环境说明：offscreen 平台的 `QSystemTrayIcon.isSystemTrayAvailable()` 恒为
False，故本测试覆写 `ChemCal._tray_available()` 造出真实 QSystemTrayIcon 对象，
另用一个独立窗口覆盖「无托盘」降级路径。

对象持有提示：PySide6 里 QMenu/QAction 的 wrapper 一被回收就连带删除底层 C++
对象（RuntimeError: Internal C++ object already deleted），故所有取到的菜单、
动作、子菜单一律存进**模块级容器**长期持有（见 tests/test_menu_bar.py 顶部）。

Part A  关闭行为偏好（settings.close_action）
    A1 出厂默认「每次询问」；A2 写入并生效；A3 已落盘；A4 非法值被拒
    A5 文件里存垃圾值时退回默认；A6 三个合法取值齐备且不重复
Part B  托盘右键菜单结构
    B1 托盘对象就绪 + 顶级项顺序；B2「关闭窗口时」子菜单三项可勾选且互斥
    B3 当前偏好项已勾选（只勾一个）；B4 改偏好后勾选跟随
    B5 全部可点项已连槽；B6 菜单被长期持有（防 GC 连带删 C++ 对象）
Part C  收进托盘 / 唤回
    C1 tooltip 含版本号；C2 点 X 收进托盘（进程不退）；C3 首次收托盘才提示一次
    C4 唤回后窗口可见、计时器恢复；C5 收托盘时计时器停掉；C6 收托盘时数据已落盘
    C7 单击 / 双击托盘图标唤回
Part D  无托盘环境降级
    D1 离屏构造后无托盘；D2 无托盘时 `_minimize_to_tray` 不藏窗口、转为真退出
Part E  真退出入口不经过询问
    E1 文件菜单「退出」即真退出；E2 托盘「退出 ChemCal」即真退出
    E3 更新「安装并重启」不再用 self.close()（否则文件被占用）
Part F  状态栏主题短名
    F1 三套主题短名；F2 未知 key 回退不崩；F3 状态栏不再出现英文主题名
Part G  点 X 选「直接退出」必须真的结束进程（**真跑事件循环**）
    G1 事件循环已结束 —— 不是「窗口关了、托盘摘了、进程还在」的后台僵尸
    G2/G3 结构性约束：结束进程只有 _quit_app 一个出口，closeEvent 不自带 quit

⚠ Part G 是 v1.14.1 补的。v1.14.0 的 closeEvent「直接退出」分支只调了
`event.accept()`、没调 `QApplication.quit()`，配合 `setQuitOnLastWindowClosed(False)`
就是僵尸进程。它之所以逃过早先的测试，原因有两条，都很容易再犯：
    ① 前面所有 Part 都**不启动 `app.exec()`** —— 不跑事件循环，就看不出进程没结束；
    ② 测试自建的 QApplication **没设** `setQuitOnLastWindowClosed(False)`（只在
       `main()` 里设），前提不成立，即使跑了循环也会假通过。
另外注意：`QApplication.quit()` 在 exec() 尚未启动时是**空操作**，所以必须
「先 exec、再由定时器触发点 X」，写成「先 close 再 exec」会得到假阳性。
════════════════════════════════════════════════════════════════════════
"""
import ast
import json
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
from PySide6.QtCore import QTimer, SIGNAL                   # noqa: E402
from PySide6.QtWidgets import QSystemTrayIcon             # noqa: E402

# DataManager 单例必须**先**指向临时文件，否则 ChemCal() 会用默认路径
# （~/.ChemCal/data/）—— 那会污染用户真实数据文件
TMPDIR = tempfile.mkdtemp()
DATA_FILE = os.path.join(TMPDIR, 'tray_test.json')
DM = DataManager.get_instance(data_file=DATA_FILE)

app = QApplication(sys.argv)
# 与 main() 保持一致 —— 这正是「点 X 选直接退出」那条缺陷的前提条件：
# 设了 setQuitOnLastWindowClosed(False) 之后，关掉窗口**不会**结束进程，
# 「直接退出」这一支必须自己调 QApplication.quit()。测试若不设，Part G 会假通过。
app.setQuitOnLastWindowClosed(False)

FAILED = 0
TOTAL = 0


def check(name, cond, detail=''):
    global FAILED, TOTAL
    TOTAL += 1
    mark = 'PASS' if cond else 'FAIL'
    print(f'{mark}  {name}' + (f'   [{detail}]' if detail and not cond else ''))
    if not cond:
        FAILED += 1


from main import ChemCal                                 # noqa: E402

win = ChemCal()


# ── Part A 关闭行为偏好 ───────────────────────────────────────────────
print('Part A  关闭行为偏好')
check('A1 出厂默认「每次询问」', win._resolve_close_action() == 'ask',
      win._resolve_close_action())

check('A2 写入 tray 后立即生效并返回 True',
      win._set_close_action('tray') is True
      and win._resolve_close_action() == 'tray',
      win._resolve_close_action())

with open(DATA_FILE, encoding='utf-8') as f:
    _on_disk = json.load(f)
check('A3 偏好已落盘到 settings.close_action',
      _on_disk.get('settings', {}).get('close_action') == 'tray',
      str(_on_disk.get('settings')))

check('A4 非法取值被拒且不改变现值',
      win._set_close_action('nuke') is False
      and win._resolve_close_action() == 'tray',
      win._resolve_close_action())

# 模拟用户手工把配置文件改坏：取值不认识时必须退回「每次询问」而不是炸掉
DM.data['settings'] = {'close_action': 'garbage'}
check('A5 配置文件里是垃圾值时退回「每次询问」',
      win._resolve_close_action() == 'ask', win._resolve_close_action())
DM.data['settings'] = {'close_action': 'tray'}

_labels = [k for k, _ in ChemCal.CLOSE_LABELS]
check('A6 三个合法取值齐备且不重复',
      sorted(_labels) == ['ask', 'quit', 'tray'], str(_labels))


# ── 造真实托盘对象（离屏平台默认判定为「无托盘」） ────────────────────
win._tray_available = lambda: True
win._setup_tray()
_TRAY = win._tray
# 模块级长期持有，防 wrapper 被 GC 连带删掉底层 C++ 对象
_TRAY_MENU = win._tray_menu
_TRAY_ACTS = list(_TRAY_MENU.actions())
_BEHAVIOR = [a.menu() for a in _TRAY_ACTS if a.menu() is not None][0]
_BEHAVIOR_ITEMS = list(_BEHAVIOR.actions())


# ── Part B 托盘右键菜单结构 ───────────────────────────────────────────
print('Part B  托盘右键菜单结构')
check('B1 托盘对象已就绪', _TRAY is not None)
check('B1 顶级项 = 显示主窗口 / 工程信息... / ─ / 关闭窗口时 ▸ / ─ / 退出 ChemCal',
      [a.text() for a in _TRAY_ACTS]
      == ['显示主窗口', '工程信息...', '', '关闭窗口时', '', '退出 ChemCal'],
      str([a.text() for a in _TRAY_ACTS]))

check('B2 子菜单 = 每次询问 / 最小化到托盘 / 直接退出，均可勾选',
      [a.text() for a in _BEHAVIOR_ITEMS]
      == ['每次询问', '最小化到托盘', '直接退出']
      and all(a.isCheckable() for a in _BEHAVIOR_ITEMS),
      str([(a.text(), a.isCheckable()) for a in _BEHAVIOR_ITEMS]))

# Qt6 的 QAction 没有 group()，互斥要从 QActionGroup 侧核对
_grp = win._close_group
check('B2 三项互斥（同一 QActionGroup 且 setExclusive）',
      _grp.isExclusive()
      and [a.text() for a in _grp.actions()]
      == ['每次询问', '最小化到托盘', '直接退出'],
      str([a.text() for a in _grp.actions()]))

_checked = [a.text() for a in _BEHAVIOR_ITEMS if a.isChecked()]
check('B3 当前偏好（tray）项已勾选且只勾一个',
      _checked == ['最小化到托盘'], str(_checked))

win._set_close_action('quit')
_checked2 = [a.text() for a in _BEHAVIOR_ITEMS if a.isChecked()]
check('B4 改偏好后勾选跟随（quit → 直接退出）',
      _checked2 == ['直接退出'], str(_checked2))
win._set_close_action('tray')

_clickable = ([a for a in _TRAY_ACTS
               if not a.isSeparator() and a.menu() is None]
              + list(_BEHAVIOR_ITEMS))
_no_recv = [a.text() for a in _clickable
            if a.receivers(SIGNAL('triggered()')) == 0]
check('B5 全部可点项已连槽（triggered 有接收器）', not _no_recv, str(_no_recv))

check('B6 菜单被 self._tray_menu 长期持有', win._tray_menu is _TRAY_MENU)


# ── Part C 收进托盘 / 唤回 ────────────────────────────────────────────
print('Part C  收进托盘 / 唤回')
check('C1 托盘 tooltip 含版本号',
      f'v{VERSION}' in _TRAY.toolTip(), _TRAY.toolTip())

win.show()
win._really_quit = False
win._tray_tip_shown = False
win.close()                                  # 等价于点右上角 X
check('C2 偏好为 tray 时点 X 收进托盘（窗口隐藏）', win.isHidden())
check('C2 收进托盘不等于退出进程（_really_quit 仍为 False）',
      win._really_quit is False)
check('C3 首次收托盘已提示一次（_tray_tip_shown）', win._tray_tip_shown is True)
check('C5 收托盘时状态栏计时器已停',
      win._time_timer is not None and not win._time_timer.isActive())

with open(DATA_FILE, encoding='utf-8') as f:
    _disk_after = json.load(f)
check('C6 收托盘时数据已落盘（临时数据文件可解析）',
      _disk_after.get('settings', {}).get('close_action') == 'tray',
      str(_disk_after.get('settings')))

win._restore_from_tray()
check('C4 唤回后窗口不再隐藏', not win.isHidden())
check('C4 唤回后状态栏计时器恢复',
      win._time_timer is not None and win._time_timer.isActive())

win.close()                                  # 再次收进托盘
win._on_tray_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
check('C7 双击托盘图标唤回窗口', not win.isHidden())
win.close()
win._on_tray_activated(QSystemTrayIcon.ActivationReason.Context)
check('C7 右键（Context）不误唤回窗口', win.isHidden())
win._restore_from_tray()


# ── Part D 无托盘环境降级 ─────────────────────────────────────────────
print('Part D  无托盘环境降级')
win2 = ChemCal()
check('D1 离屏（无系统托盘）构造后 _tray 为 None 且不崩', win2._tray is None)

win2.show()
win2._really_quit = False
win2._minimize_to_tray()
check('D2 无托盘时不隐藏窗口（否则「窗口没了、程序还在」）', not win2.isHidden())
check('D2 无托盘时转为真退出（_really_quit = True）', win2._really_quit is True)


# ── Part E 真退出入口不经过询问 ───────────────────────────────────────
print('Part E  真退出入口不经过询问')
_MENUBAR = win.menuBar()
_TOP_ACTS = list(_MENUBAR.actions())
_FILE_MENU = [a.menu() for a in _TOP_ACTS if a.text() == '文件'][0]
_FILE_ITEMS = list(_FILE_MENU.actions())
_exit_act = [a for a in _FILE_ITEMS if a.text() == '退出'][0]
_quit_act = [a for a in _TRAY_ACTS if a.text() == '退出 ChemCal'][0]

win._really_quit = False
_exit_act.trigger()
check('E1 菜单「文件 → 退出」即真退出（不进托盘、不询问）',
      win._really_quit is True, f'_really_quit={win._really_quit}')

win._really_quit = False
_quit_act.trigger()
check('E2 托盘「退出 ChemCal」即真退出', win._really_quit is True)

with open(os.path.join(ROOT, 'main.py'), encoding='utf-8') as f:
    _SRC = f.read()
check('E3 更新「安装并重启」不再用 self.close()（否则文件被占用）',
      'self.close()' not in _SRC and _SRC.count('self._quit_app()') >= 2,
      f"self.close()={_SRC.count('self.close()')} "
      f"_quit_app={_SRC.count('self._quit_app()')}")


# ── Part F 状态栏主题短名 ─────────────────────────────────────────────
print('Part F  状态栏主题短名')
_short = [ChemCal.theme_short_name(k) for k, _ in ChemCal.THEME_LABELS]
check('F1 三套主题短名 = 浅色 / 深色 / 蓝色',
      _short == ['浅色', '深色', '蓝色'], str(_short))
check('F2 未知 key 回退不崩',
      ChemCal.theme_short_name('neon') == 'Neon',
      ChemCal.theme_short_name('neon'))
check('F3 状态栏不再出现英文主题名',
      '主题: 浅色' in win.theme_label.text()
      and 'Light' not in win.theme_label.text(),
      win.theme_label.text())


# ── Part G 点 X 选「直接退出」必须真的结束进程（真跑事件循环） ─────────
print('Part G  点 X 选「直接退出」真的结束进程')
win3 = ChemCal()
win3._tray_available = lambda: True
win3._setup_tray()
win3.show()
win3._set_close_action('quit')             # 等价于勾过「记住 → 直接退出」

_G = {}


def _g_watchdog():
    """1.2 s 后仍在跑 ⇒ 事件循环没被结束 ⇒ 后台僵尸（顺手收尾，别挂住测试）"""
    _G['zombie'] = True
    _G['hidden'] = win3.isHidden()
    _G['tray'] = None if win3._tray is None else win3._tray.isVisible()
    app.quit()


# 点 X 必须发生在**事件循环已在运行**时：quit() 先于 exec() 是空操作
QTimer.singleShot(0, win3.close)
QTimer.singleShot(1200, _g_watchdog)
app.exec()                                 # ← 真跑事件循环（前面各 Part 都不跑）

check('G1 点 X 选「直接退出」后事件循环已结束（不是后台僵尸）',
      'zombie' not in _G,
      f"循环仍在运行：窗口isHidden={_G.get('hidden')} "
      f"托盘isVisible={_G.get('tray')}")

with open(os.path.join(ROOT, 'main.py'), encoding='utf-8') as f:
    _TREE = ast.parse(f.read())
_quit_calls = [n.lineno for n in ast.walk(_TREE)
               if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Attribute)
               and n.func.attr == 'quit'
               and getattr(n.func.value, 'id', '') == 'QApplication']
_quit_fn = next(n for n in ast.walk(_TREE)
                if isinstance(n, ast.FunctionDef) and n.name == '_quit_app')
check('G2 结束进程只有 _quit_app 一个出口（唯一一处 QApplication.quit()）',
      len(_quit_calls) == 1 and _quit_fn.lineno < _quit_calls[0] <= _quit_fn.end_lineno,
      f'calls={_quit_calls} _quit_app=L{_quit_fn.lineno}-{_quit_fn.end_lineno}')

_ce = next(n for n in ast.walk(_TREE)
           if isinstance(n, ast.FunctionDef) and n.name == 'closeEvent')
_ce_calls = {n.func.attr for n in ast.walk(_ce)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
check('G3 closeEvent 走 self._quit_app() 退出、不自带 quit 逻辑',
      '_quit_app' in _ce_calls and 'quit' not in _ce_calls, str(sorted(_ce_calls)))


# ── 汇总 ─────────────────────────────────────────────────────────────
print(f'\n共 {TOTAL} 项，通过 {TOTAL - FAILED}，失败 {FAILED}')
sys.exit(1 if FAILED else 0)
