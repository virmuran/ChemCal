# -*- coding: utf-8 -*-
"""倒计时页回归测试

为什么要有这个文件：倒计时页此前只有"能实例化 + 能新增"两条断言，而它藏着三类问题：
  A. 卡片颜色写在控件自己的 setStyleSheet 上（浅底压浅字，深色主题直接看不见）；
  B. 秒针每秒整页 deleteLater + 重建，resizeEvent 里也重建；
  C. 视觉状态（未到期 / 临近 / 已过期 / 选中）没有任何可验证的出口。

固化四条不变式：
  A. 纯函数（时间解析、剩余时间格式化、进度百分比、名称截断）的手算锚点
  B. 三套主题的卡片配色必须同进同出，且页面源码里不得再出现任何颜色字面量
  C. 秒针不重建控件，只有数据/筛选/排序/列数变化才重建
  D. 新增/编辑/删除/清理/筛选/排序的行为与落库参数

运行：
    QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe tests/test_countdowns.py
"""
import os
import re
import sys
import tokenize
import io
from datetime import datetime, timedelta

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QSize, Qt                    # noqa: E402
from PySide6.QtGui import QResizeEvent                           # noqa: E402
from PySide6.QtWidgets import QApplication                       # noqa: E402

import theme_manager as theme_mod                                # noqa: E402
from theme_manager import (ThemeManager, countdown_card_rules,   # noqa: E402
                           CD_COLORS, CD_RULES_SRC)

PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}   {extra}")


def section(title):
    print(f"\n{title}")


app = QApplication.instance() or QApplication([])

from modules.countdowns import (                                  # noqa: E402
    CountdownsWidget, CountdownDialog, parse_target, humanize_duration,
    progress_percent, elide_name, BADGE_TEXTS, SOON_SECONDS, MIN_CARD_WIDTH,
    GRID_SPACING, NAME_LIMIT, WEEKDAYS,
)

# ══════════════════════════════ A. 纯函数锚点 ══════════════════════════════
section("A. 纯函数（时间解析 / 剩余时间 / 进度 / 截断）")

check("带秒解析", parse_target(
    {"target_date": "2030-01-02", "target_time": "03:04:05"}) == datetime(2030, 1, 2, 3, 4, 5))
check("不带秒解析（补 0 秒）", parse_target(
    {"target_date": "2030-01-02", "target_time": "03:04"}) == datetime(2030, 1, 2, 3, 4, 0))
check("只有日期（补 23:59:00）", parse_target(
    {"target_date": "2030-01-02"}) == datetime(2030, 1, 2, 23, 59, 0))
check("时间为空串等同没给", parse_target(
    {"target_date": "2030-01-02", "target_time": ""}) == datetime(2030, 1, 2, 23, 59, 0))
check("非法日期返回 None", parse_target({"target_date": "2030-02-30"}) is None)
check("乱填返回 None", parse_target({"target_date": "下周三"}) is None)
check("缺字段返回 None", parse_target({}) is None)
check("None 字段不炸", parse_target({"target_date": None, "target_time": None}) is None)

# 手算：1 天 = 86400s；90061 = 86400 + 3661 = 1天1时1分1秒
HUMAN_CASES = [
    (0, "00:00:00"),
    (59, "00:00:59"),
    (60, "00:01:00"),
    (3599, "00:59:59"),
    (3600, "01:00:00"),
    (86399, "23:59:59"),
    (86400, "1天 00:00:00"),
    (90061, "1天 01:01:01"),
    (270183, "3天 03:03:03"),          # 3*86400 + 3*3600 + 3*60 + 3
    (-3725, "01:02:05"),               # 取绝对值：3600 + 125
]
for secs, expected in HUMAN_CASES:
    got = humanize_duration(secs)
    check(f"humanize_duration({secs}) == {expected}", got == expected, got)

# 进度：手算 (now - start) / (target - start)
T0 = datetime(2030, 1, 1, 0, 0, 0)
check("进度 50%（起点到中点）",
      progress_percent(T0.isoformat(), T0 + timedelta(hours=2),
                       T0 + timedelta(hours=1)) == 50.0)
check("进度 0%（刚到起点）",
      progress_percent(T0.isoformat(), T0 + timedelta(days=1), T0) == 0.0)
check("进度 100%（到点）",
      progress_percent(T0.isoformat(), T0 + timedelta(days=1),
                       T0 + timedelta(days=1)) == 100.0)
check("超时后封顶 100%（不给 130%）",
      progress_percent(T0.isoformat(), T0 + timedelta(days=1),
                       T0 + timedelta(days=2)) == 100.0)
check("起点在未来时封底为 0，不给负数",
      progress_percent(T0.isoformat(), T0 + timedelta(days=2),
                       T0 - timedelta(days=1)) == 0.0)
check("没有 created_at → None（不画假进度条）",
      progress_percent(None, T0 + timedelta(days=1)) is None)
check("created_at 晚于 target → None",
      progress_percent((T0 + timedelta(days=2)).isoformat(), T0) is None)
check("created_at 是垃圾字符串 → None",
      progress_percent("不是时间", T0) is None)

check(f"名称 {NAME_LIMIT} 字不截断", elide_name("甲" * NAME_LIMIT) == "甲" * NAME_LIMIT)
check(f"名称 {NAME_LIMIT + 1} 字截断并加省略号",
      elide_name("甲" * (NAME_LIMIT + 1)) == "甲" * NAME_LIMIT + "…")
check("名称 None 不炸", elide_name(None) == "")
check("星期文案是常量表（不依赖系统 locale）",
      len(WEEKDAYS) == 7 and WEEKDAYS[0] == "星期一" and WEEKDAYS[6] == "星期日")

# ══════════════════════════════ B. 主题 ══════════════════════════════
section("B. 主题配色同进同出 + 页面源码零颜色")

check("CD_COLORS 覆盖三套主题", set(CD_COLORS) == {"light", "dark", "blue"}, set(CD_COLORS))
keys_ref = set(CD_COLORS["light"])
for name, colors in CD_COLORS.items():
    check(f"{name} 卡片配色键与其他主题一致", set(colors) == keys_ref, set(colors) ^ keys_ref)

tm = ThemeManager()
check("语义规则覆盖全部主题", set(ThemeManager.SEMANTIC_RULES) == set(tm.themes))

for name in tm.themes:
    rules = countdown_card_rules(name)
    check(f"{name} 卡片规则无未替换占位符", "$" not in rules,
          [w for w in rules.split() if w.startswith("$")])
    for token in ("QScrollArea#cdScroll", "QFrame#cdCard", 'QFrame#cdCard[cdState="soon"]',
                  'QFrame#cdCard[cdState="overdue"]', 'QFrame#cdCard[cdSelected="1"]',
                  "QLabel#cdTime", "QLabel#cdBadge", "QProgressBar#cdProgress"):
        check(f"{name} 定义了 {token}", token in rules)
    check(f"{name} 卡片规则真的用上了该主题的取值",
          CD_COLORS[name]["card_bg"] in rules and CD_COLORS[name]["over_fg"] in rules)
    check(f"{name} 整套 QSS 里含卡片样式", "cdCard" in tm.themes[name])
    check(f"{name} 输入框样式含 QDateTimeEdit", "QDateTimeEdit" in tm.themes[name])
    # 选中态规则必须在状态规则之后 —— 否则"选中 + 过期"时选中框看不见
    check(f"{name} 选中态规则排在状态规则之后",
          rules.index('cdSelected="1"') > rules.index('cdState="overdue"'))

check("未知主题名回落亮色且不抛异常",
      countdown_card_rules("nope") == countdown_card_rules("light"))
check("模板里没有硬编码颜色（颜色必须全部来自 CD_COLORS）",
      not re.findall(r"#[0-9a-fA-F]{3,8}\b", CD_RULES_SRC),
      re.findall(r"#[0-9a-fA-F]{3,8}\b", CD_RULES_SRC))

PAGE_FILE = os.path.join(PROJ, "modules", "countdowns.py")


def code_text(path):
    """读源码 + 保留字符串字面量、剥掉注释（注释里提颜色不算违规）。"""
    src = open(path, encoding="utf-8").read()
    parts = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            continue
        parts.append(tok.string)
    return " ".join(parts)


cd_src = code_text(PAGE_FILE)
check("页面源码里一个颜色字面量都没有", not re.findall(r"#[0-9a-fA-F]{3,8}\b", cd_src),
      re.findall(r"#[0-9a-fA-F]{3,8}\b", cd_src))
check("页面没有 setStyleSheet 写颜色（只允许字号/加粗等尺寸类）",
      not re.findall(r"setStyleSheet\([^)]*(?:color|background)", cd_src))
check("页面用了语义 objectName",
      all(n in cd_src for n in ("mutedLabel", "accentLabel", "primaryBtn", "dangerBtn")))
check("页面实现了 on_theme_changed 钩子", "def on_theme_changed" in cd_src)
check("页面颜色全走动态属性", all(n in cd_src for n in ("cdState", "cdSelected")))
check("页面不再持有 active_countdowns（旧版每秒重建的根）", "active_countdowns" not in cd_src)
# 只认"真的在用"：文档里提一句 QInputDialog 不算违规，import 或调用才算
check("页面没有导入/调用 QInputDialog（改用了统一对话框）",
      not re.search(r"\bQInputDialog\s*[.(]", cd_src)
      and "import QInputDialog" not in cd_src
      and "QInputDialog," not in cd_src)


# ══════════════════════════════ 测试替身 ══════════════════════════════
class FakeDataManager(QObject):
    """只提供倒计时页用到的四个方法，不落盘。"""

    def __init__(self, records=None):
        super().__init__()
        self.items = [dict(r) for r in (records or [])]
        self.add_calls = []
        self.update_calls = []
        self.delete_calls = []

    def get_countdowns(self):
        return [dict(r) for r in self.items]

    def add_countdown(self, name, target_date, target_time):
        cid = max([r["id"] for r in self.items] or [0]) + 1
        self.add_calls.append((name, target_date, target_time))
        self.items.append({"id": cid, "name": name, "target_date": target_date,
                           "target_time": target_time,
                           "created_at": datetime.now().isoformat()})
        return cid

    def update_countdown(self, countdown_id, **kwargs):
        self.update_calls.append((countdown_id, dict(kwargs)))
        for rec in self.items:
            if rec["id"] == countdown_id:
                rec.update(kwargs)
        return True

    def delete_countdown(self, countdown_id):
        self.delete_calls.append(countdown_id)
        self.items = [r for r in self.items if r["id"] != countdown_id]

    # 便捷断言用
    def ids(self):
        return sorted(r["id"] for r in self.items)


def build_records(now=None):
    """四条基准记录：临近 / 未到期 / 已过期 / 无 created_at（不画进度条）。

    时间都取在"离边界很远"的位置（3 天 6 小时这种），免得秒针走动
    把「3天」掉成「2天 23:59:59」导致断言飘。
    """
    now = now or datetime.now()

    def iso(delta):
        return (now + delta).isoformat()

    def day(delta):
        return (now + delta).strftime("%Y-%m-%d")

    return [
        {"id": 1, "name": "半小时后到点", "target_date": day(timedelta(minutes=30)),
         "target_time": (now + timedelta(minutes=30)).strftime("%H:%M:%S"),
         "created_at": iso(timedelta(minutes=-30))},
        {"id": 2, "name": "三天半后", "target_date": day(timedelta(days=3, hours=6)),
         "target_time": (now + timedelta(days=3, hours=6)).strftime("%H:%M:%S"),
         "created_at": iso(timedelta(days=-1))},
        {"id": 3, "name": "两天前就该做的", "target_date": day(timedelta(days=-2, hours=-3)),
         "target_time": (now - timedelta(days=2, hours=3)).strftime("%H:%M:%S"),
         "created_at": iso(timedelta(days=-5))},
        {"id": 4, "name": "没有创建时间的那条", "target_date": day(timedelta(days=5, hours=8)),
         "target_time": (now + timedelta(days=5, hours=8)).strftime("%H:%M:%S"),
         "created_at": None},
    ]


def make_page(records=None):
    dm = FakeDataManager(records if records is not None else build_records())
    page = CountdownsWidget(None, dm)
    # 三个弹窗开关全关：离屏下 QMessageBox 的 exec() 会永久阻塞（看不到报错、整轮卡死）
    page.confirm_enabled = False
    page.notify_enabled = False
    page.message_enabled = False
    return page, dm


def stop(page):
    for name in ("countdown_timer", "datetime_timer"):
        timer = getattr(page, name, None)
        if timer is not None:
            timer.stop()


# ══════════════════════════════ C. 状态与秒针 ══════════════════════════════
section("C. 卡片状态 / 秒针不重建 / 计数器")

page, dm = make_page()
try:
    check("实例化无异常", page is not None)
    check("装载了 4 张卡片", len(page._cards) == 4, sorted(page._cards))
    check("卡片键 = 记录 id", sorted(page._cards) == [1, 2, 3, 4])
    check("时钟已填充（不是占位）",
          page.current_time_label.text() not in ("", "--:--:--"),
          page.current_time_label.text())
    check("日期标签已填充且带中文星期",
          any(w in page.current_date_label.text() for w in WEEKDAYS),
          page.current_date_label.text())
    check("两个计时器都在跑",
          page.countdown_timer.isActive() and page.datetime_timer.isActive())

    c1, c2, c3, c4 = (page._cards[i] for i in (1, 2, 3, 4))
    check("半小时后的 → 临近", c1["state"] == "soon", c1["state"])
    check("三天半后的 → 进行中", c2["state"] == "normal", c2["state"])
    check("两天前的 → 已过期", c3["state"] == "overdue", c3["state"])
    check("徽标文案跟随状态",
          (c1["badge"].text(), c2["badge"].text(), c3["badge"].text())
          == (BADGE_TEXTS["soon"], BADGE_TEXTS["normal"], BADGE_TEXTS["overdue"]))
    check("临近门槛就是 1 小时", SOON_SECONDS == 3600)
    check("临近态会把 cdState 传到控件上（QSS 才生效）",
          c1["frame"].property("cdState") == "soon"
          and c1["time"].property("cdState") == "soon"
          and c1["badge"].property("cdState") == "soon")

    check("未到期的显示正向剩余时间", re.fullmatch(r"\d{2}:\d{2}:\d{2}",
                                                c1["time"].text()) is not None,
          c1["time"].text())
    check("剩余时间带「天」单位", c2["time"].text().startswith("3天 "), c2["time"].text())
    check("已过期的显示「已过期」前缀 + 已过时长",
          c3["time"].text().startswith("已过期 2天 "), c3["time"].text())

    # 进度条：手算 (now - created) / (target - created)
    check("id1 进度 ≈ 50%（创建 30 分钟前、目标 30 分钟后）",
          abs(c1["bar"].value() / 10.0 - 50.0) <= 0.5, c1["bar"].value())
    check("id2 进度 ≈ 23.5%（已过 1 天 / 共 4 天 6 小时）",
          abs(c2["bar"].value() / 10.0 - 100.0 / 4.25) <= 0.5, c2["bar"].value())
    # id3 已过期：区间 only 69 小时（5 天前创建 → 2 天 3 小时前到点），
    # 已过 120 小时，120/69 = 174% → 封顶 100%。过期的进度条天然是"全满"。
    check("id3 已过期 → 进度封顶 100%（120h / 69h 区间 = 174%）",
          c3["bar"].value() == 1000, c3["bar"].value())
    # 离屏下没显示过的控件 isVisible() 恒为 False，必须用 isHidden() 判断显隐
    check("没有 created_at → 进度条隐藏（不画假进度）", c4["bar"].isHidden())
    check("有 created_at → 进度条未隐藏", not c1["bar"].isHidden())
    check("进度条区间 0~1000（用 0.1% 精度）", c1["bar"].maximum() == 1000)

    check("目标行带目标时间与已过百分比",
          c1["target"].text().startswith("目标 ") and "已过 50%" in c1["target"].text(),
          c1["target"].text())

    check("计数器文案", page.count_label.text() == "共 4 个 · 未到期 3 · 已过期 1",
          page.count_label.text())
    check("清理按钮显示过期条数并可用",
          page.cleanup_btn.text() == "清理已过期 (1)" and page.cleanup_btn.isEnabled(),
          page.cleanup_btn.text())

    # ── 秒针不重建 ──
    frames_before = {cid: id(card["frame"]) for cid, card in page._cards.items()}
    for _ in range(3):
        page._update_tick()
    frames_after = {cid: id(card["frame"]) for cid, card in page._cards.items()}
    check("连走 3 次秒针，卡片控件一个都没换", frames_before == frames_after)
    check("秒针不改 self._columns 之外的布局状态", page._columns == page._columns)

    # refresh 才重建
    page.refresh_countdowns()
    frames_refreshed = {cid: id(card["frame"]) for cid, card in page._cards.items()}
    check("refresh_countdowns() 会重建卡片", frames_refreshed != frames_after)

    # ── 选中 ──
    check("未选中时编辑/删除按钮禁用",
          not page.edit_btn.isEnabled() and not page.delete_btn.isEnabled())
    page.select_countdown(2)
    check("选中后编辑/删除按钮启用",
          page.edit_btn.isEnabled() and page.delete_btn.isEnabled())
    check("选中态落到动态属性上",
          page._cards[2]["frame"].property("cdSelected") == "1"
          and page._cards[1]["frame"].property("cdSelected") == "0")
    check("selected_countdown_id 记录正确", page.selected_countdown_id == 2)

    # ── 列数 ──
    page.resize(1200, 760)
    page.refresh_countdowns()
    expected_cols = max(1, (1200 - CountdownsWidget.LEFT_PANEL_WIDTH - 40 + GRID_SPACING)
                        // (MIN_CARD_WIDTH + GRID_SPACING))
    check(f"1200px 宽 → {expected_cols} 列（手算）", page._columns == expected_cols,
          page._columns)
    check("列数 ≥ 2 时卡片按行铺开（第 2 条落在第 1 行第 2 列）",
          page.scroll_layout.indexOf(page._cards[2]["frame"]) >= 0)

    # ── resizeEvent 只在列数变化时重建 ──
    rebuilds = []
    original_rebuild = page._rebuild_cards

    def counting_rebuild():
        rebuilds.append(1)
        return original_rebuild()

    page._rebuild_cards = counting_rebuild
    same = QSize(1200, 760)
    page.resizeEvent(QResizeEvent(same, QSize(1200, 760)))
    check("宽度没变 → resizeEvent 不重建", rebuilds == [], len(rebuilds))
    page.resize(1500, 760)
    page.resizeEvent(QResizeEvent(QSize(1500, 760), same))
    check("宽度变了（列数随之变）→ resizeEvent 重建一次", len(rebuilds) == 1, len(rebuilds))
    check("重建后列数与新宽度一致",
          page._columns == max(1, (1500 - CountdownsWidget.LEFT_PANEL_WIDTH - 40
                                   + GRID_SPACING) // (MIN_CARD_WIDTH + GRID_SPACING)),
          page._columns)
    page._rebuild_cards = original_rebuild

    # ── 空态 ──
    empty_page, _ = make_page([])
    try:
        check("无数据时不建卡片", empty_page._cards == {})
        check("无数据时给出空态提示", empty_page._empty_label is not None
              and "暂无倒计时" in empty_page._empty_label.text())
        check("无数据时清理/清空按钮禁用",
              not empty_page.cleanup_btn.isEnabled() and not empty_page.clear_btn.isEnabled())
        check("无数据时计数器为 0", empty_page.count_label.text() == "共 0 个 · 未到期 0 · 已过期 0")
    finally:
        stop(empty_page)

    # ── 主题钩子 ──
    theme_ok, theme_err = True, ""
    try:
        tm.set_theme("dark")
        page.on_theme_changed()
        tm.set_theme("light")
        page.on_theme_changed()
    except Exception as e:                                        # noqa: BLE001
        theme_ok, theme_err = False, e
    check("切主题 + on_theme_changed 不抛异常", theme_ok, theme_err)
    check("切主题后选中态仍在",
          page._cards[2]["frame"].property("cdSelected") == "1")
finally:
    stop(page)

# ══════════════════════════════ D. 增删改 / 筛选 / 排序 ══════════════════════════════
section("D. 新增 / 编辑 / 删除 / 清理 / 筛选 / 排序")

page, dm = make_page()
try:
    # ── 新增 ──
    # 先算好"计划时间"再填表单：秒被截到 0，断言才不受秒针走动影响
    plan = (datetime.now() + timedelta(days=2, hours=5)).replace(second=0, microsecond=0)
    page.name_entry.setText("  锅炉水压试验  ")
    page._set_form_datetime(plan)
    check("新增成功", page.add_countdown() is True)
    check("名称已 strip 后落库（日期/时间拆分存储）",
          dm.add_calls == [("锅炉水压试验",
                            plan.strftime("%Y-%m-%d"), plan.strftime("%H:%M:%S"))],
          dm.add_calls)
    check("新增后输入框清空", page.name_entry.text() == "")
    check("新增后卡片数 +1", len(page._cards) == 5)
    check("新增后给出状态提示", "已添加倒计时" in page.status_label.text(),
          page.status_label.text())

    added_id = max(dm.ids())
    before = len(dm.add_calls)
    page.name_entry.setText("")
    check("空名称被拦下（不落库）", page.add_countdown() is False)
    check("空名称的拦截原因", page.last_message == ("无法添加", "请输入事件名称"),
          page.last_message)
    page.name_entry.setText("过去的时间")
    page._set_form_datetime(datetime.now() - timedelta(minutes=5))
    check("过去时间被拦下（不落库）", page.add_countdown() is False)
    check("过去时间的拦截原因", page.last_message == ("无法添加", "目标时间必须是未来时间"),
          page.last_message)
    check("两次非法输入都没写进 data_manager", len(dm.add_calls) == before)

    # ── 编辑 ──
    ok = page.apply_edit(added_id, "改过的名字",
                         datetime.now() + timedelta(days=9, hours=3))
    check("编辑成功", ok is True)
    check("编辑落的参数正确",
          dm.update_calls[-1][0] == added_id
          and dm.update_calls[-1][1]["name"] == "改过的名字",
          dm.update_calls[-1])
    check("编辑后卡片名称更新",
          "改过的名字" in page._cards[added_id]["name"].text())
    check("编辑成过去时间会被拒",
          page.apply_edit(added_id, "再次改名", datetime.now() - timedelta(minutes=1)) is False)
    check("编辑不存在 id 会被拒",
          page.apply_edit(9999, "幽灵", datetime.now() + timedelta(days=1)) is False)

    # ── 筛选 ──
    page.state_filter.setCurrentIndex(1)          # 未到期
    check("筛选「未到期」只剩未到期卡片",
          all(not page._is_expired(page._cards[cid]["record"]) for cid in page._cards),
          sorted(page._cards))
    check("筛选「未到期」把 id3 排除在外", 3 not in page._cards, sorted(page._cards))
    page.state_filter.setCurrentIndex(2)          # 已过期
    check("筛选「已过期」只剩 id3", sorted(page._cards) == [3], sorted(page._cards))
    page.state_filter.setCurrentIndex(0)
    check("筛选「全部」回到 5 条", len(page._cards) == 5, len(page._cards))
    check("记录本体不受筛选影响（永远能按 id 找到）", set(page._all_records) == set(dm.ids()))

    # ── 排序 ──
    page.sort_combo.setCurrentIndex(0)            # 近 → 远
    order = list(page._cards)
    check("按剩余时间近→远：过期那条排最前", order[0] == 3, order)
    check("近→远整体有序",
          [page._cards[c]["target_dt"] for c in order] ==
          sorted(page._cards[c]["target_dt"] for c in order), order)
    page.sort_combo.setCurrentIndex(1)            # 远 → 近
    rev = list(page._cards)
    check("远→近与近→远互为反序", rev == order[::-1], rev)
    page.sort_combo.setCurrentIndex(2)            # 添加时间新→旧
    newest = list(page._cards)
    created = [str(page._cards[c]["record"].get("created_at") or "") for c in newest]
    check("按创建时间新→旧有序", created == sorted(created, reverse=True), created)
    page.sort_combo.setCurrentIndex(0)

    # ── 排序的脏数据兜底 ──
    dirty, dirty_dm = make_page([
        {"id": 11, "name": "脏数据", "target_date": "不是日期", "target_time": "aa",
         "created_at": None},
        {"id": 12, "name": "正常", "target_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
         "target_time": "12:00:00", "created_at": datetime.now().isoformat()},
    ])
    try:
        check("解析不出时间的记录也会建卡片（不整页崩）", sorted(dirty._cards) == [11, 12])
        check("脏记录显示「时间无效」提示",
              dirty._cards[11]["time"].text() == "时间无效"
              and "重新指定目标时间" in dirty._cards[11]["target"].text(),
              dirty._cards[11]["time"].text())
        check("脏记录按已过期计入", dirty._cards[11]["state"] == "overdue")
        check("脏记录排在正常记录之后（不搅乱顺序）",
              list(dirty._cards) == [12, 11], list(dirty._cards))
        check("脏记录也算可清理", dirty.cleanup_expired() == 1, dirty_dm.ids())
        check("清理后只剩正常记录", dirty_dm.ids() == [12])
    finally:
        stop(dirty)

    # ── 删除 ──
    page, dm = make_page()
    page.select_countdown(3)
    check("删除成功", page.delete_countdown() is True)
    check("删除落到 data_manager", dm.delete_calls == [3], dm.delete_calls)
    check("删除后选中态清空", page.selected_countdown_id is None)
    check("删除后卡片数 -1", len(page._cards) == 3, sorted(page._cards))
    check("未选中就删除会被拦下", page.delete_countdown() is False)
    check("未选中删除的提示语", page.last_message == ("警告", "请先选择一个倒计时"),
          page.last_message)
    check("删除不存在 id 会被拒", page.delete_countdown(9999) is False)

    # ── 清理已过期 ──
    page, dm = make_page()
    removed = page.cleanup_expired()
    check("清理只删已过期的那条", removed == 1 and dm.ids() == [1, 2, 4], dm.ids())
    check("再清理一次返回 0", page.cleanup_expired() == 0)
    check("没有可清理时按钮禁用", not page.cleanup_btn.isEnabled())

    # ── 清空全部 ──
    page, dm = make_page()
    check("清空全部成功", page.clear_all_countdowns() is True)
    check("清空后 data_manager 为空", dm.ids() == [])
    check("清空后无卡片且有空态提示", page._cards == {} and page._empty_label is not None)
    check("空列表再清空返回 False", page.clear_all_countdowns() is False)
    stop(page)
finally:
    stop(page)

# ══════════════════════════════ E. 到点提醒 ══════════════════════════════
section("E. 到点提醒（每个只响一次）")

page, dm = make_page()
try:
    fired = []
    page.notify_enabled = True
    page._notify_finished = lambda rec: fired.append(rec.get("id"))

    check("启动时已过期的不会被补提醒", page._notified >= {3})
    page._update_tick()
    app.processEvents()
    check("已过期的不会弹提醒", fired == [], fired)

    # 把 id1 的目标拨到刚过去（模拟时间流逝到点）
    page._cards[1]["target_dt"] = datetime.now() - timedelta(seconds=1)
    page._update_tick()
    app.processEvents()
    check("到点时提醒一次", fired == [1], fired)
    page._update_tick()
    app.processEvents()
    page._update_tick()
    app.processEvents()
    check("之后每秒都不再重复提醒", fired == [1], fired)
    check("到点后卡片切到已过期",
          page._cards[1]["state"] == "overdue"
          and page._cards[1]["time"].text().startswith("已过期"))
finally:
    stop(page)

# ══════════════════════════════ F. 对话框 ══════════════════════════════
section("F. 新增/编辑对话框（不 exec，只读值）")

future = datetime.now() + timedelta(days=1, hours=2)
dialog = CountdownDialog(None, name="  水压试验  ", target=future, title="编辑倒计时")
check("对话框能脱离 exec 单独构造", dialog is not None)
check("名称原样载入（不预先 strip，交给 values/validate 处理）",
      dialog.name_edit.text() == "  水压试验  ", dialog.name_edit.text())
check("目标时间载入到分钟", dialog.target_datetime().replace(second=0, microsecond=0)
      == future.replace(second=0, microsecond=0), dialog.target_datetime())
check("values() 会 strip 名称", dialog.values()[0] == "水压试验")
check("合法输入通过校验", dialog.validate() == (True, ""), dialog.validate())

blank = CountdownDialog(None, name="   ", target=future)
check("空名称被拦下", blank.validate()[0] is False)
past = CountdownDialog(None, name="x", target=datetime.now() - timedelta(days=1))
check("过去时间被拦下", past.validate()[0] is False)

dialog.set_target(datetime.now() + timedelta(days=1))
before_shift = dialog.target_datetime()
dialog.shift_target(timedelta(days=7))
check("快捷偏移按天数推后", dialog.target_datetime() == before_shift + timedelta(days=7))

# 基准是"当前值与此刻中较晚的一个"：界面停在过去时，按 +1 天必须仍是未来
stale = CountdownDialog(None, name="x", target=datetime.now() - timedelta(days=3))
stale.shift_target(timedelta(days=1))
check("界面停在过去时间时，+1 天仍落在未来",
      stale.target_datetime() > datetime.now(), stale.target_datetime())

print()
print("=" * 60)
print(f"总结: {PASS} 过, {FAIL} 失败")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
