# -*- coding: utf-8 -*-
"""工程信息录入入口（计算书抬头写入口）回归测试

纯 PySide6 offscreen 运行：
    .venv/Scripts/python.exe tests/test_project_info.py

背景
════════════════════════════════════════════════════════════════════════
51 个计算器的计算书（DOCX / PDF）抬头通过 DataManager.get_project_info()
读取 company_name / project_number / project_name / subproject_name 四个
标准键，但此前**只有读、没有写**——项目里没有任何界面能录入公司名 /
工程编号，抬头永远是空的。v1.12.1 清遗骸时确认 update_project_info()
全项目零调用，本版补上写入口：

    文件菜单 → 「工程信息...」→ ProjectInfoDialog → update_project_info()

Part A  数据层（update_project_info 的既有契约）
    A1 get_project_info() → dict 且 4 标准键齐全
    A2 写入后读回一致；A3 落盘（新开实例读到同一份 JSON）
    A4 缺省键补空（部分字段不丢）

Part B  ProjectInfoDialog
    B1 构造后控件可访问；B2 预填当前工程信息
    B3 values() 去首尾空白；B4 accept() → 写入 DataManager（不 exec）
    B5 重开对话框 → 预填上次保存值；B6 FIELDS 键与标准键严格一致

Part C  主窗口集成
    C1 主窗口可构造（4 标签）；C2 文件菜单含「工程信息...」动作
    C3 动作已连接槽（triggered 有接收器）

Part D  重启持久化（v1.13.1 修的回归缺陷）
    D1 重启后四项工程信息完整保留 ← 核心回归
    D2 落盘内容与内存一致；D3 旧格式仍能正确迁移；D4 迁移幂等
    D5 已移除模块的遗留数据键被丢弃（并固化到磁盘）
    D6 数据文件损坏时另存为 .corrupt-*.json（不就地覆盖）

背景（Part D）：_migrate_project_info_data() 位于每次启动的加载路径上，判据误写成
「存在 project_info 键」—— 新格式同样有这个键，于是**每次启动都把新格式数据当旧格式
重迁一遍**：company_name 取自旧键 design_unit（新格式没有）被清空、project_number 取
project_name 中的阿拉伯数字（中文工程名一律抠不到）被清空、subproject_name 硬编码为空。
用户实测现象：录入四项 → 关闭软件 → 重开，只有工程名称还在（3/4 字段丢失）。
════════════════════════════════════════════════════════════════════════
"""
import os
import sys
import json
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

import tempfile as _tf                                    # noqa: E402
from data_manager import DataManager                      # noqa: E402

TMPDIR = _tf.mkdtemp()
DATA_FILE = os.path.join(TMPDIR, 'proj_info_test.json')
DM = DataManager.get_instance(data_file=DATA_FILE)

app = QApplication(sys.argv)

# ── Part A 数据层 ──────────────────────────────────────────────────────
print('Part A  数据层契约')
info0 = DM.get_project_info()
STD_KEYS = ['company_name', 'project_number', 'project_name', 'subproject_name']


def check(name, cond, detail=''):
    mark = 'PASS' if cond else 'FAIL'
    print(f'{mark}  {name}' + (f'   [{detail}]' if detail and not cond else ''))
    if not cond:
        globals()['FAILED'] = globals().get('FAILED', 0) + 1


check('A1 get_project_info 返回 dict 且 4 标准键齐全',
      isinstance(info0, dict) and all(k in info0 for k in STD_KEYS),
      str(info0))

sample = {
    'company_name': '测试生物科技股份有限公司',
    'project_number': '2026-071',
    'project_name': '10 万吨/年麦芽糖醇项目',
    'subproject_name': '脱色工段',
}
DM.update_project_info(sample)
info1 = DM.get_project_info()
check('A2 写入后读回一致', info1 == sample, str(info1))

with open(DATA_FILE, encoding='utf-8') as f:
    on_disk = json.load(f).get('project_info', {})
check('A3 已落盘（JSON 文件里 project_info 一致）', on_disk == sample,
      str(on_disk))

DM.update_project_info({'project_number': '2026-099'})
info2 = DM.get_project_info()
check('A4 部分键更新时其余键不丢',
      info2['project_number'] == '2026-099'
      and info2['company_name'] == sample['company_name']
      and info2['project_name'] == sample['project_name']
      and info2['subproject_name'] == sample['subproject_name'],
      str(info2))

# ── Part B ProjectInfoDialog ──────────────────────────────────────────
print('Part B  ProjectInfoDialog')
from main import ProjectInfoDialog, ChemCal                # noqa: E402

dlg = ProjectInfoDialog(DM)
check('B1 构造后控件可访问（QLineEdit 不抛 RuntimeError）',
      dlg._edits['company_name'].text() == sample['company_name']
      and dlg._edits['project_number'].text() == '2026-099'
      and dlg._edits['project_name'].text() == sample['project_name']
      and dlg._edits['subproject_name'].text() == sample['subproject_name'])
check('B2 预填当前工程信息（B1 的另一半：四个框全非空）',
      all(dlg._edits[k].text() for k in STD_KEYS))

for k in STD_KEYS:
    dlg._edits[k].setText(f'  {k}-值  ')
vals = dlg.values()
check('B3 values() 返回 4 键且去首尾空白',
      set(vals) == set(STD_KEYS)
      and all(vals[k] == f'{k}-值' for k in STD_KEYS), str(vals))

new_vals = {
    'company_name': ' ACME 生物工程 ',
    'project_number': ' 2026-099 ',
    'project_name': ' 1 万吨/年木糖醇项目 ',
    'subproject_name': ' 液化工段 ',
}
for k, v in new_vals.items():
    dlg._edits[k].setText(v)
dlg.accept()                                    # 不 exec()（离屏会挂死）
info3 = DM.get_project_info()
check('B4 accept() 写入 DataManager（含去空白）',
      info3 == {k: v.strip() for k, v in new_vals.items()}, str(info3))

dlg2 = ProjectInfoDialog(DM)
check('B5 重开对话框预填上次保存值',
      dlg2._edits['company_name'].text() == new_vals['company_name'].strip()
      and dlg2._edits['project_number'].text() == '2026-099')

check('B6 FIELDS 键与 4 标准键严格一致（顺序：公司/编号/工程/子项）',
      [k for k, _ in ProjectInfoDialog.FIELDS] == STD_KEYS)

# ── Part C 主窗口集成 ─────────────────────────────────────────────────
print('Part C  主窗口集成')
win = ChemCal()
check('C1 主窗口可构造且为 4 标签', win.tab_widget.count() == 4,
      str([win.tab_widget.tabText(i) for i in range(win.tab_widget.count())]))

file_menu = None
for act in win.menuBar().actions():
    if act.text() == '文件':
        file_menu = act.menu()
        break
acts = [a.text() for a in file_menu.actions()] if file_menu else []
check('C2 文件菜单含「工程信息...」且在第一项',
      bool(file_menu) and acts and acts[0] == '工程信息...', str(acts))

target = next((a for a in file_menu.actions() if a.text() == '工程信息...'), None)
from PySide6.QtCore import SIGNAL as _SIG                       # noqa: E402
check('C3 动作已连接槽（triggered 有接收器且启用）',
      target is not None and target.isEnabled()
      and target.receivers(_SIG('triggered()')) > 0)

# ── Part D 重启持久化 ─────────────────────────────────────────────────
# v1.13.1 修的回归缺陷：_migrate_project_info_data() 位于每次启动的加载路径上，
# 判据误写成「存在 project_info 键」（新格式同样有），于是新格式数据每次启动都被
# 当旧格式重迁一遍 —— 公司名/编号/子项被静默清空，只剩 project_name。
# 用户实测现象：录入四项 → 关闭软件 → 重开，只有工程名称还在。
print('Part D  重启持久化（模拟关闭软件再打开）')


def _restart(data_file):
    """模拟「关闭软件再打开」：清掉单例，重走 _load_or_create_data"""
    DataManager._instance = None
    DataManager._initialized = False
    return DataManager.get_instance(data_file=data_file)


R_FILE = os.path.join(TMPDIR, 'restart_test.json')
dm_r = _restart(R_FILE)
FULL = {
    'company_name': '沐然生物科技股份有限公司',
    'project_number': '2026-071',
    'project_name': '一万吨木糖醇项目',
    'subproject_name': '脱色工段',
}
dm_r.update_project_info(FULL)

dm_r2 = _restart(R_FILE)
back = dm_r2.get_project_info()
check('D1 重启后四项工程信息完整保留（本次修复的核心回归）',
      back == FULL, str(back))

with open(R_FILE, encoding='utf-8') as f:
    disk_r = json.load(f).get('project_info', {})
check('D2 落盘内容与内存一致（未被迁移篡改后写回）', disk_r == FULL,
      str(disk_r))

# 旧格式仍能迁移（迁移能力本身不能被修掉）
L_FILE = os.path.join(TMPDIR, 'legacy_test.json')
with open(L_FILE, 'w', encoding='utf-8') as f:
    json.dump({'project_info': {'design_unit': '旧设计院',
                                'project_name': '2026-088 老项目'}}, f,
              ensure_ascii=False)
dm_l = _restart(L_FILE)
legacy = dm_l.get_project_info()
check('D3 旧格式（design_unit）仍正确迁移为新格式',
      legacy['company_name'] == '旧设计院'
      and legacy['project_name'] == '2026-088 老项目'
      and legacy['project_number'] == '2026-088 老项目'
      and legacy['subproject_name'] == '', str(legacy))

dm_l2 = _restart(L_FILE)
check('D4 迁移结果幂等（再启动一次不被二次迁移）',
      dm_l2.get_project_info() == legacy, str(dm_l2.get_project_info()))

# 已移除模块的遗留键应在加载时丢弃
G_FILE = os.path.join(TMPDIR, 'legacy_keys_test.json')
with open(G_FILE, 'w', encoding='utf-8') as f:
    json.dump({'project_info': dict(FULL),
               'countdowns': [{'name': '2027年'}], 'folders': ['工作'],
               'report_counter': {'count': 0},
               'process_design': {'projects': []}}, f, ensure_ascii=False)
dm_g = _restart(G_FILE)
with open(G_FILE, encoding='utf-8') as f:
    after_g = json.load(f)
check('D5 已移除模块的遗留数据键被丢弃（且立即固化到磁盘）',
      not any(k in after_g for k in ('countdowns', 'folders',
                                     'report_counter', 'process_design'))
      and after_g.get('project_info') == FULL, str(list(after_g)))

# 坏文件必须另存保留，绝不就地覆盖
B_FILE = os.path.join(TMPDIR, 'broken_test.json')
with open(B_FILE, 'w', encoding='utf-8') as f:
    f.write('{"project_info": { 这不是合法 JSON')
dm_b = _restart(B_FILE)
import glob as _glob                                            # noqa: E402
kept = _glob.glob(os.path.join(TMPDIR, 'broken_test.corrupt-*.json'))
check('D6 数据文件损坏时另存为 .corrupt-*.json（不就地覆盖用户数据）',
      len(kept) == 1
      and dm_b.get_project_info() == dict.fromkeys(STD_KEYS, ''),
      str(kept))

# ── 汇总 ─────────────────────────────────────────────────────────────
failed = globals().get('FAILED', 0)
total = 3 + 6 + 3 + 6
print(f'\n共 {total} 项，通过 {total - failed}，失败 {failed}')
sys.exit(1 if failed else 0)
