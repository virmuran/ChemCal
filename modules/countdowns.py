# ChemCal/modules/countdowns.py
"""倒计时页

功能：添加 / 编辑 / 删除倒计时、每秒刷新剩余时间、按状态筛选与排序、
      到点提醒（每个只响一次）、一键清理已过期。

两条设计约束 —— 都是上一版踩过的坑：

1. **卡片只在数据 / 筛选 / 列数变化时重建。** 上一版每秒整页 deleteLater 再重建，
   一次刷新要毁掉再建 N 个卡片；resizeEvent 里还重建一次，拖窗口就是一串重建。
   现在秒针只改文字与状态（`_update_tick`），重建只走 `refresh_countdowns()`。
2. **颜色一律不写在本文件。** 卡片状态由动态属性 cdState / cdSelected 驱动，
   配色集中在 theme_manager.SEMANTIC_RULES 里按主题给。
   上一版把背景色、边框色、文字色写在控件自己的 setStyleSheet 上，
   换到深色主题就是「浅底压浅字」，卡片上的字直接看不见。
"""
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QGridLayout, QFrame, QMessageBox, QGroupBox, QComboBox,
    QDateTimeEdit, QProgressBar, QDialog, QDialogButtonBox,
)
from PySide6.QtCore import Qt, QTimer, QDateTime
from PySide6.QtGui import QFont


#: 剩余时间进入「临近」状态的门槛（秒）
SOON_SECONDS = 3600
#: 卡片最小宽度 —— 列数由可用宽度整除它得到（不写死卡片宽度，随窗口自适应）
MIN_CARD_WIDTH = 260
#: 卡片高度固定，网格才整齐（内容约 103px，留一点余量给高 DPI 字体）
CARD_HEIGHT = 112
GRID_SPACING = 10
#: 名称过长时截断的字符数（完整名称挂 tooltip）
NAME_LIMIT = 22
#: 解析 target_date + target_time 的容错格式（老数据可能带/不带秒）
TARGET_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")

#: 状态筛选：(显示文本, 编码)
STATE_FILTERS = (("全部", "all"), ("未到期", "active"), ("已过期", "overdue"))
#: 排序方式：(显示文本, 编码)
SORT_MODES = (
    ("剩余时间（近 → 远）", "soonest"),
    ("剩余时间（远 → 近）", "latest"),
    ("添加时间（新 → 旧）", "created_desc"),
)
#: 快捷偏移按钮：(显示文本, 偏移量)
QUICK_OFFSETS = (
    ("+1 小时", timedelta(hours=1)),
    ("+1 天", timedelta(days=1)),
    ("+7 天", timedelta(days=7)),
    ("+30 天", timedelta(days=30)),
)
#: 徽标文案（按状态）
BADGE_TEXTS = {"normal": "进行中", "soon": "即将到点", "overdue": "已过期"}
#: 星期文案 —— 不用 QDateTime 的 dddd：那依赖系统 locale，
#: 未装中文字体/区域的机器上会渲染出 "Tuesday"。
WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


# ── 纯函数（无 Qt 依赖，方便直接拿手算锚点验） ─────────────────────

def parse_target(countdown):
    """把一条倒计时记录解析成目标 datetime；无法解析时返回 None。

    容错顺序：带秒 → 不带秒 → 只有日期（补 23:59:00）。
    老数据里三种都出现过，任何一条读不出来都不该让整页崩掉。
    """
    date_str = str(countdown.get("target_date") or "").strip()
    time_str = str(countdown.get("target_time") or "").strip()
    if date_str:
        for fmt in TARGET_FORMATS:
            try:
                return datetime.strptime(f"{date_str} {time_str or '23:59:00'}", fmt)
            except ValueError:
                continue
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(
                hour=23, minute=59, second=0)
        except ValueError:
            return None
    return None


def humanize_duration(seconds):
    """秒 → '3天 04:12:07' / '04:12:07'（取绝对值，前缀由调用方决定）。"""
    total = int(abs(seconds))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}天 {hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def progress_percent(created_at, target, now=None):
    """已等待比例（0~100）。

    没有 created_at / 区间无效（创建晚于目标）时返回 None ——
    宁可这一条不画进度条，也不要画一根假的。
    """
    if not created_at or target is None:
        return None
    try:
        start = datetime.fromisoformat(str(created_at))
    except (TypeError, ValueError):
        return None
    if start >= target:
        return None
    span = (target - start).total_seconds()
    elapsed = ((now or datetime.now()) - start).total_seconds()
    return max(0.0, min(100.0, elapsed / span * 100.0))


def elide_name(name, limit=NAME_LIMIT):
    """超长名称截断（完整名称由调用方挂到 tooltip 上）。"""
    text = str(name or "")
    return text if len(text) <= limit else text[:limit] + "…"


def set_state_property(widget, name, value):
    """改动态属性并让 QSS 重新生效。

    不做 unpolish/polish 的话，属性选择器（QFrame#cdCard[cdState="soon"]）
    在控件已经 polish 过之后**不会重算**，状态色就不跟着变。
    """
    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class CountdownDialog(QDialog):
    """新增 / 编辑倒计时对话框（两处共用，避免上一版连弹三个 QInputDialog）。

    单独成类的另一个原因：页面里的 `dialog.exec()` 在离屏测试下会**永久阻塞**，
    所以校验逻辑必须能从外面直接调（`validate()` / `values()`）——
    测试只构造对话框、读值，绝不 exec。
    """

    def __init__(self, parent=None, name="", target=None, title="添加倒计时"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        #: 弹窗开关（离屏测试置 False —— QMessageBox 内部 exec() 会永久阻塞）
        self.message_enabled = True

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(QLabel("事件名称"))
        self.name_edit = QLineEdit(str(name or ""))
        self.name_edit.setPlaceholderText("如：锅炉水压试验")
        self.name_edit.setFixedHeight(32)
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("目标时间"))
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.datetime_edit.setFixedHeight(32)
        self.set_target(target or (datetime.now() + timedelta(hours=1)))
        layout.addWidget(self.datetime_edit)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(4)
        for text, delta in QUICK_OFFSETS:
            btn = QPushButton(text)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda _=False, d=delta: self.shift_target(d))
            quick_row.addWidget(btn)
        layout.addLayout(quick_row)

        self.hint_label = QLabel("")
        self.hint_label.setObjectName("accentLabel")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确定")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── 取值 ──

    def target_datetime(self):
        """控件当前值 → datetime（秒截到 0，界面只到分钟）。"""
        value = self.datetime_edit.dateTime().toPython()
        return value.replace(second=0, microsecond=0)

    def set_target(self, value):
        self.datetime_edit.setDateTime(
            QDateTime(value.year, value.month, value.day, value.hour, value.minute, 0))

    def shift_target(self, delta):
        """按偏移量推后目标时间。

        基准取「当前值」与「此刻」中较晚的一个 —— 界面上已经是过去时间的
        时候，再按 +1 天，结果必须仍然是未来，否则用户按了等于没按。
        """
        current = self.target_datetime()
        now = datetime.now()
        base = current if current > now else now
        self.set_target(base + delta)

    def values(self):
        return self.name_edit.text().strip(), self.target_datetime()

    def validate(self):
        """返回 (是否合法, 提示语)。"""
        name, target = self.values()
        if not name:
            return False, "请输入事件名称"
        if target <= datetime.now():
            return False, "目标时间必须是未来时间"
        return True, ""

    def _on_accept(self):
        ok, message = self.validate()
        if not ok:
            self.hint_label.setText(message)
            if self.message_enabled:
                QMessageBox.warning(self, "无法保存", message)
            return
        self.accept()


class CountdownsWidget(QWidget):
    """倒计时模块"""

    #: 左栏固定宽度（列数计算要用，别在两处各写一个数）
    LEFT_PANEL_WIDTH = 340

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.selected_countdown_id = None
        #: id → 卡片控件引用（只含当前筛选下可见的）
        self._cards = {}
        #: id → 记录本体（**不受筛选影响**，编辑/删除按它找）
        self._all_records = {}
        #: 已经提醒过到点的 id（避免每秒重复弹窗；启动时已过期的直接记入）
        self._notified = set()
        self._columns = 0
        self._empty_label = None
        self._rebuilding = False
        #: 危险操作二次确认开关（离屏测试置 False —— QMessageBox.exec() 会永久阻塞）
        self.confirm_enabled = True
        #: 到点弹窗开关（同上）
        self.notify_enabled = True
        #: 提示弹窗开关（同上：QMessageBox 的静态方法内部就是 exec()，离屏下会挂死）
        self.message_enabled = True
        #: 最近一次被拦下的原因（message_enabled=False 时也能断言"拦住了、为什么"）
        self.last_message = None

        self.setup_ui()
        self.refresh_countdowns()
        self.start_datetime_updater()

    # ══════════════════════════ 界面骨架 ══════════════════════════

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(self._build_left_panel())
        main_layout.addWidget(self._build_right_panel(), 1)

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._update_tick)
        self.countdown_timer.start(1000)

    def _build_left_panel(self):
        """左栏：时钟 → 添加 → 筛选与操作 → 状态。"""
        panel = QWidget()
        panel.setFixedWidth(self.LEFT_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("倒计时")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("font-weight: bold; padding: 5px 0;")
        layout.addWidget(title)

        self.current_time_label = QLabel("--:--:--")
        self.current_time_label.setObjectName("accentLabel")
        self.current_time_label.setStyleSheet("font-size: 22px;")
        layout.addWidget(self.current_time_label)

        self.current_date_label = QLabel("")
        self.current_date_label.setObjectName("mutedLabel")
        self.current_date_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.current_date_label)

        # ── 添加 ──
        add_group = QGroupBox("添加倒计时")
        form = QVBoxLayout(add_group)
        form.setSpacing(6)

        self.name_entry = QLineEdit()
        self.name_entry.setPlaceholderText("事件名称")
        self.name_entry.setFixedHeight(32)
        self.name_entry.returnPressed.connect(self.add_countdown)
        form.addWidget(self.name_entry)

        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.datetime_edit.setFixedHeight(32)
        self._set_form_datetime(datetime.now() + timedelta(hours=1))
        form.addWidget(self.datetime_edit)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(4)
        for text, delta in QUICK_OFFSETS:
            btn = QPushButton(text)
            btn.setFixedHeight(26)
            btn.setToolTip("把目标时间在当前值基础上推后 " + text.lstrip("+ "))
            btn.clicked.connect(lambda _=False, d=delta: self._shift_form(d))
            quick_row.addWidget(btn)
        form.addLayout(quick_row)

        self.add_btn = QPushButton("添加倒计时")
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.setFixedHeight(38)
        self.add_btn.clicked.connect(self.add_countdown)
        form.addWidget(self.add_btn)
        layout.addWidget(add_group)

        # ── 筛选与操作 ──
        ctrl_group = QGroupBox("筛选与操作")
        ctrl = QVBoxLayout(ctrl_group)
        ctrl.setSpacing(6)

        self.state_filter = QComboBox()
        self.state_filter.setFixedHeight(32)
        self.state_filter.setToolTip("按状态筛选")
        for text, code in STATE_FILTERS:
            self.state_filter.addItem(text, code)
        # 先填项、再连信号 —— 否则 addItem 触发的信号会打到还没建好的控件上
        self.state_filter.currentIndexChanged.connect(self._on_view_changed)
        ctrl.addWidget(self.state_filter)

        self.sort_combo = QComboBox()
        self.sort_combo.setFixedHeight(32)
        self.sort_combo.setToolTip("排序方式")
        for text, code in SORT_MODES:
            self.sort_combo.addItem(text, code)
        self.sort_combo.currentIndexChanged.connect(self._on_view_changed)
        ctrl.addWidget(self.sort_combo)

        btn_grid = QGridLayout()
        btn_grid.setSpacing(6)

        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setFixedHeight(32)
        self.edit_btn.setToolTip("编辑选中的倒计时（也可双击卡片）")
        self.edit_btn.clicked.connect(self.edit_countdown)

        self.delete_btn = QPushButton("删除")
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.setFixedHeight(32)
        self.delete_btn.clicked.connect(self.delete_countdown)

        self.cleanup_btn = QPushButton("清理已过期")
        self.cleanup_btn.setFixedHeight(32)
        self.cleanup_btn.setToolTip("删除全部已过期的倒计时")
        self.cleanup_btn.clicked.connect(self.cleanup_expired)

        self.clear_btn = QPushButton("清空全部")
        self.clear_btn.setObjectName("dangerBtn")
        self.clear_btn.setFixedHeight(32)
        self.clear_btn.clicked.connect(self.clear_all_countdowns)

        btn_grid.addWidget(self.edit_btn, 0, 0)
        btn_grid.addWidget(self.delete_btn, 0, 1)
        btn_grid.addWidget(self.cleanup_btn, 1, 0)
        btn_grid.addWidget(self.clear_btn, 1, 1)
        ctrl.addLayout(btn_grid)
        layout.addWidget(ctrl_group)

        layout.addStretch(1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("mutedLabel")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.status_label)
        return panel

    def _build_right_panel(self):
        """右栏：计数 + 刷新 → 卡片网格。"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(8)
        head_title = QLabel("倒计时列表")
        head_title.setFont(QFont("Arial", 14, QFont.Bold))
        head_title.setStyleSheet("font-weight: bold; padding: 5px 0;")
        head.addWidget(head_title)
        head.addStretch()

        self.count_label = QLabel("共 0 个")
        self.count_label.setObjectName("mutedLabel")
        self.count_label.setStyleSheet("font-size: 12px;")
        head.addWidget(self.count_label)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedHeight(30)
        self.refresh_btn.setToolTip("重新读取倒计时数据")
        self.refresh_btn.clicked.connect(self.refresh_countdowns)
        head.addWidget(self.refresh_btn)
        layout.addLayout(head)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("cdScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_widget = QWidget()
        self.scroll_layout = QGridLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(GRID_SPACING)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area, 1)
        return panel

    # ══════════════════════════ 数据准备 ══════════════════════════

    def _column_count(self):
        """可用宽度能放几列卡片。

        刻意用**整页宽度减左栏**，而不是 scroll_area.viewport().width()：
        后者会被滚动条的出现/消失改变，于是「列数变 → 重建 → 滚动条变 → 列数变」
        来回共振。整页宽度与滚动条无关，稳定。
        """
        avail = self.width() - self.LEFT_PANEL_WIDTH - 40
        return max(1, (avail + GRID_SPACING) // (MIN_CARD_WIDTH + GRID_SPACING))

    def _is_expired(self, record, now=None):
        target = parse_target(record)
        return target is None or target <= (now or datetime.now())

    def _apply_filter(self, rows, now):
        code = self.state_filter.currentData() or "all"
        if code == "active":
            return [(r, t) for r, t in rows if t is not None and t > now]
        if code == "overdue":
            return [(r, t) for r, t in rows if t is None or t <= now]
        return rows

    def _apply_sort(self, rows):
        code = self.sort_combo.currentData() or "soonest"
        if code == "created_desc":
            return sorted(
                rows,
                key=lambda rt: (str(rt[0].get("created_at") or ""), str(rt[0].get("id"))),
                reverse=True)
        # 解析不出时间的放最后 —— 不能因为一条脏数据把整页顺序打乱
        dated = [rt for rt in rows if rt[1] is not None]
        undated = [rt for rt in rows if rt[1] is None]
        dated.sort(key=lambda rt: rt[1], reverse=(code == "latest"))
        return dated + undated

    # ══════════════════════════ 卡片构建与刷新 ══════════════════════════

    def _clear_cards(self):
        """清空网格（含空态提示），卡片里的控件交给 deleteLater。"""
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._cards.clear()
        self._empty_label = None
        for col in range(12):
            self.scroll_layout.setColumnStretch(col, 0)

    def refresh_countdowns(self):
        """重新读取数据并重建卡片。

        只在数据 / 筛选 / 排序 / 列数变化时调用 —— 秒针不走这里（走 `_update_tick`）。
        重建期间置 `_rebuilding`：resizeEvent 里的重建判断必须让路，否则
        「重建 → 布局变化 → resizeEvent → 再重建」会自己套自己。
        """
        if self._rebuilding:
            return len(self._all_records)
        self._rebuilding = True
        try:
            return self._rebuild_cards()
        finally:
            self._rebuilding = False

    def _rebuild_cards(self):
        records = list(self.data_manager.get_countdowns() or [])
        self._all_records = {rec.get("id"): rec for rec in records}

        now = datetime.now()
        rows = []
        for rec in records:
            target = parse_target(rec)
            if target is not None and target <= now:
                # 打开软件时就已经过期的，不再补提醒（只提醒"运行期间到点"的）
                self._notified.add(rec.get("id"))
            rows.append((rec, target))

        rows = self._apply_sort(self._apply_filter(rows, now))

        self._clear_cards()
        self._columns = self._column_count()

        if not rows:
            self._empty_label = QLabel(
                "暂无倒计时" if not self._all_records else "当前筛选条件下没有倒计时")
            self._empty_label.setObjectName("cdEmpty")
            self._empty_label.setAlignment(Qt.AlignCenter)
            self.scroll_layout.addWidget(self._empty_label, 0, 0)
            self.scroll_layout.setColumnStretch(0, 1)
        else:
            for index, (rec, target) in enumerate(rows):
                row, col = divmod(index, self._columns)
                card = self._make_card(rec, target)
                self.scroll_layout.addWidget(card["frame"], row, col)
            for col in range(self._columns):
                self.scroll_layout.setColumnStretch(col, 1)

        if self.selected_countdown_id not in self._cards:
            # 选中的那条被删了 / 被筛选掉了 —— 清掉选中态
            self.selected_countdown_id = None
        self._apply_selection()
        self._update_tick()
        self._update_count_label()
        self._update_buttons()
        return len(records)

    def _make_card(self, record, target):
        """建一张卡片 —— 只在这里 setObjectName / 挂动态属性，颜色全交给主题 QSS。"""
        cid = record.get("id")

        frame = QFrame()
        frame.setObjectName("cdCard")
        frame.setMinimumWidth(MIN_CARD_WIDTH)
        frame.setFixedHeight(CARD_HEIGHT)
        frame.setCursor(Qt.PointingHandCursor)
        set_state_property(frame, "cdSelected", "0")
        frame.mousePressEvent = lambda event, c=cid: self.select_countdown(c)
        frame.mouseDoubleClickEvent = lambda event, c=cid: self._edit_card(c)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        name = QLabel(elide_name(record.get("name")))
        name.setObjectName("cdName")
        name.setToolTip(str(record.get("name") or ""))
        top_row.addWidget(name, 1)
        badge = QLabel(BADGE_TEXTS["normal"])
        badge.setObjectName("cdBadge")
        badge.setAlignment(Qt.AlignCenter)
        top_row.addWidget(badge, 0)
        layout.addLayout(top_row)

        time_label = QLabel("--:--:--")
        time_label.setObjectName("cdTime")
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setFont(QFont("Consolas", 18, QFont.Bold))
        layout.addWidget(time_label)

        target_label = QLabel("")
        target_label.setObjectName("cdTarget")
        target_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(target_label)

        bar = QProgressBar()
        bar.setObjectName("cdProgress")
        bar.setTextVisible(False)
        bar.setRange(0, 1000)
        bar.setFixedHeight(6)
        layout.addWidget(bar)

        # 子控件不吃鼠标事件 —— 点哪儿都是点卡片，不用给每个 label 挂一遍 lambda
        for child in (name, badge, time_label, target_label, bar):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._cards[cid] = {
            "frame": frame, "name": name, "badge": badge, "time": time_label,
            "target": target_label, "bar": bar, "record": record,
            "target_dt": target, "state": None,
        }
        return self._cards[cid]

    def _update_tick(self):
        """秒针：只改文字 / 状态 / 进度，不重建任何控件。"""
        now = datetime.now()
        for cid, card in list(self._cards.items()):
            record = card["record"]
            target = card["target_dt"]

            if target is None:
                card["time"].setText("时间无效")
                card["target"].setText("请编辑这条记录，重新指定目标时间")
                card["bar"].setVisible(False)
                self._switch_state(card, "overdue")
                continue

            seconds = (target - now).total_seconds()
            if seconds <= 0:
                card["time"].setText("已过期 " + humanize_duration(seconds))
                state = "overdue"
            else:
                card["time"].setText(humanize_duration(seconds))
                state = "soon" if seconds <= SOON_SECONDS else "normal"

            pct = progress_percent(record.get("created_at"), target, now)
            text = "目标 " + target.strftime("%Y-%m-%d %H:%M")
            if pct is not None:
                text += f" · 已过 {pct:.0f}%"
            card["target"].setText(text)

            if pct is None:
                card["bar"].setVisible(False)
            else:
                card["bar"].setVisible(True)
                card["bar"].setValue(int(round(pct * 10)))

            self._switch_state(card, state)

            if state == "overdue" and cid not in self._notified:
                self._notified.add(cid)
                # 延到事件循环下一轮 —— 免得在遍历卡片的过程中弹出模态框
                QTimer.singleShot(0, lambda r=dict(record): self._notify_finished(r))

    def _switch_state(self, card, state):
        if card["state"] == state:
            return
        card["state"] = state
        set_state_property(card["frame"], "cdState", state)
        set_state_property(card["time"], "cdState", state)
        set_state_property(card["badge"], "cdState", state)
        card["badge"].setText(BADGE_TEXTS[state])

    def _apply_selection(self):
        for cid, card in self._cards.items():
            set_state_property(card["frame"], "cdSelected",
                               "1" if cid == self.selected_countdown_id else "0")
        self._update_buttons()

    def _update_count_label(self):
        now = datetime.now()
        total = len(self._all_records)
        expired = sum(1 for rec in self._all_records.values() if self._is_expired(rec, now))
        self.count_label.setText(
            f"共 {total} 个 · 未到期 {total - expired} · 已过期 {expired}")

    def _update_buttons(self):
        has_selection = self.selected_countdown_id in self._all_records
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.clear_btn.setEnabled(bool(self._all_records))
        expired = sum(1 for rec in self._all_records.values() if self._is_expired(rec))
        self.cleanup_btn.setText(f"清理已过期 ({expired})" if expired else "清理已过期")
        self.cleanup_btn.setEnabled(expired > 0)

    # ══════════════════════════ 选择 ══════════════════════════

    def select_countdown(self, countdown_id):
        if self.selected_countdown_id == countdown_id:
            return
        self.selected_countdown_id = countdown_id
        self._apply_selection()

    # ══════════════════════════ 添加 ══════════════════════════

    def _set_form_datetime(self, value):
        self.datetime_edit.setDateTime(
            QDateTime(value.year, value.month, value.day, value.hour, value.minute, 0))

    def _form_datetime(self):
        value = self.datetime_edit.dateTime().toPython()
        return value.replace(second=0, microsecond=0)

    def _shift_form(self, delta):
        current = self._form_datetime()
        now = datetime.now()
        self._set_form_datetime((current if current > now else now) + delta)

    def add_countdown(self):
        """把左栏表单的倒计时存进去。全部字段校验通过才落盘。"""
        name, target = self._form_name_target()
        error = ""
        if not name:
            error = "请输入事件名称"
        elif target <= datetime.now():
            error = "目标时间必须是未来时间"
        if error:
            self._error("无法添加", error)
            return False

        self.data_manager.add_countdown(
            name, target.strftime("%Y-%m-%d"), target.strftime("%H:%M:%S"))
        self.name_entry.clear()
        self.refresh_countdowns()
        self._flash(f"已添加倒计时：{name}")
        return True

    def _form_name_target(self):
        return self.name_entry.text().strip(), self._form_datetime()

    # ══════════════════════════ 编辑 / 删除 ══════════════════════════

    def _edit_card(self, countdown_id):
        self.select_countdown(countdown_id)
        self.edit_countdown()

    def edit_countdown(self, countdown_id=None):
        cid = self.selected_countdown_id if countdown_id is None else countdown_id
        record = self._all_records.get(cid)
        if record is None:
            self._warn("警告", "请先选择一个倒计时")
            return False

        dialog = CountdownDialog(
            self, name=record.get("name", ""),
            target=parse_target(record) or (datetime.now() + timedelta(hours=1)),
            title="编辑倒计时")
        if dialog.exec() != QDialog.Accepted:
            return False
        name, target = dialog.values()
        return self.apply_edit(cid, name, target)

    def apply_edit(self, countdown_id, name, target):
        """落库（对话框确认后调用）。

        单独拆出来是为了能在离屏测试里直接验：`dialog.exec()` 在离屏下永久阻塞，
        走不到这行。
        """
        if countdown_id not in self._all_records:
            return False
        name = str(name or "").strip()
        if not name or target <= datetime.now():
            return False
        self.data_manager.update_countdown(
            countdown_id, name=name,
            target_date=target.strftime("%Y-%m-%d"),
            target_time=target.strftime("%H:%M:%S"))
        # 改过时间就重新允许提醒（把已过期的往未来挪，该再响一次）
        self._notified.discard(countdown_id)
        self.refresh_countdowns()
        self._flash(f"已更新倒计时：{name}")
        return True

    def delete_countdown(self, countdown_id=None):
        cid = self.selected_countdown_id if countdown_id is None else countdown_id
        record = self._all_records.get(cid)
        if record is None:
            self._warn("警告", "请先选择一个倒计时")
            return False
        if not self._confirm("确认删除",
                             f"确定要删除倒计时「{record.get('name')}」吗？"):
            return False
        self.data_manager.delete_countdown(cid)
        self._notified.discard(cid)
        if self.selected_countdown_id == cid:
            self.selected_countdown_id = None
        self.refresh_countdowns()
        self._flash(f"已删除倒计时：{record.get('name')}")
        return True

    def cleanup_expired(self):
        """一键清理已过期（含时间解析失败、编辑不回来的那几条）。"""
        expired = [rec for rec in self._all_records.values() if self._is_expired(rec)]
        if not expired:
            self._flash("没有已过期的倒计时")
            return 0
        if not self._confirm(
                "确认清理",
                f"将删除 {len(expired)} 个已过期的倒计时。\n此操作不可撤销。"):
            return 0
        for rec in expired:
            self.data_manager.delete_countdown(rec.get("id"))
            self._notified.discard(rec.get("id"))
        self.refresh_countdowns()
        self._flash(f"已清理 {len(expired)} 个过期倒计时")
        return len(expired)

    def clear_all_countdowns(self):
        if not self._all_records:
            self._info("提示", "倒计时列表已为空")
            return False
        count = len(self._all_records)
        if not self._confirm("确认清空", f"确定要清空全部 {count} 个倒计时吗？"):
            return False
        for record in list(self._all_records.values()):
            self.data_manager.delete_countdown(record.get("id"))
        self._notified.clear()
        self.selected_countdown_id = None
        self.refresh_countdowns()
        self._flash(f"已清空 {count} 个倒计时")
        return True

    def _confirm(self, title, message):
        """危险操作二次确认。confirm_enabled=False（测试）时直接放行。"""
        if not self.confirm_enabled:
            return True
        reply = QMessageBox.question(
            self, title, message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    # ══════════════════════════ 提示弹窗 ══════════════════════════
    # 统一从这三个入口出弹窗：一是 message_enabled=False 时能整体静音（离屏测试下
    # QMessageBox 的静态方法内部会 exec()，没有事件循环喂它就会**永久阻塞**，整轮测试
    # 卡死且看不到任何报错）；二是拦截原因留一份在 last_message 里，便于断言。

    def _error(self, title, message):
        self.last_message = (title, message)
        if self.message_enabled:
            QMessageBox.critical(self, title, message)

    def _warn(self, title, message):
        self.last_message = (title, message)
        if self.message_enabled:
            QMessageBox.warning(self, title, message)

    def _info(self, title, message):
        self.last_message = (title, message)
        if self.message_enabled:
            QMessageBox.information(self, title, message)

    # ══════════════════════════ 到点提醒 / 状态提示 ══════════════════════════

    def _notify_finished(self, record):
        if not self.notify_enabled:
            return
        QMessageBox.information(
            self, "倒计时结束", f"「{record.get('name')}」的时间到了！")
        self.last_message = ("倒计时结束", record.get("name"))

    def _flash(self, text, msec=4000):
        self.status_label.setText(text)
        QTimer.singleShot(msec, lambda t=text: self._clear_flash(t))

    def _clear_flash(self, text):
        if self.status_label.text() == text:
            self.status_label.setText("")

    # ══════════════════════════ 时钟 / 事件 ══════════════════════════

    def update_datetime(self):
        now = QDateTime.currentDateTime()
        self.current_time_label.setText(now.toString("HH:mm:ss"))
        weekday = WEEKDAYS[now.date().dayOfWeek() - 1]
        self.current_date_label.setText(
            now.toString("yyyy年MM月dd日") + " " + weekday)

    def start_datetime_updater(self):
        self.datetime_timer = QTimer(self)
        self.datetime_timer.timeout.connect(self.update_datetime)
        self.datetime_timer.start(1000)
        self.update_datetime()

    def _on_view_changed(self, _index=None):
        """筛选/排序变了 —— 重建（顺序和可见集合都变了）。"""
        self.refresh_countdowns()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 只有列数真的变了才重建（拖窗口时 resize 会连发，不能每次都重建）
        if self._rebuilding:
            return
        if self._column_count() != self._columns:
            self.refresh_countdowns()

    def on_theme_changed(self):
        """主题切换钩子。

        卡片颜色全在主题 QSS 里（由 cdState / cdSelected 属性选择），
        Qt 换全局样式表时会自动重新 polish，这里无需重画 ——
        只把选中态再套一遍，防止属性在别处被改坏。
        """
        self._apply_selection()

    def on_activate(self):
        """切到本标签页时刷新（外部改动能立刻看到）。"""
        self.refresh_countdowns()
