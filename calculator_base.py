"""
ChemCal 计算器基类

所有计算器均可继承此类获得：
  - init_data_manager()：数据管理器注入
  - setup_wheel_blocker()：QComboBox 滚轮拦截
  - download_docx_report() / download_pdf_report()：报告导出
  - 结论条：把「答案」钉在结果区最上方（solve 完不用再翻）
  - 公共样式常量引用
"""

import re
import html
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QComboBox, QLabel, QVBoxLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer

# 确保项目根在 sys.path 中（兼容动态加载）
_root = str(Path(__file__).parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from utils.docx_utils import ReportExporter
from modules.combo_box_utils import ComboBoxWheelBlocker
from app_styles import (
    COMBOBOX_STYLE, GROUP_STYLE, CALC_BUTTON_STYLE,
    MODE_BUTTON_STYLE, SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
    CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE,
)


# ══════════════════════════════════════════════════════════════
#  结论提取：从结果文本里把「答案」拎出来
# ══════════════════════════════════════════════════════════════

#: 结论节标题的优先级（越靠前越优先）。结果文本的节由 ═══ 分隔线包裹。
CONCLUSION_SECTIONS = (
    "计算结果", "选型结果", "转换结果", "设计结果", "汇总结果",
    "结论", "性能参数", "状态点参数", "查询结果",
)

#: 节分隔线：三个以上的 ═ / = 独占一行
_SECTION_RULE = re.compile(r"^[═=]{3,}$")

#: 方括号小节标题，如「【计算结果】」「【一、柱体与装炭】」
_BRACKET_TITLE = re.compile(r"^【[^】]{2,40}】$")

#: 行首的列表符号（只剥这些，避免把负号「-15 °C」当成 bullet 剥掉）
_BULLETS = ("•", "·", "★", "→")

#: 行首的编号（「1. 」「2、」「（1）」），结论条里不需要
_NUMBERING = re.compile(r"^[\(（]?\d{1,2}[\.、\)）]\s*")

#: 页面类名 → 结论行关键词（按优先级排列，最多取 3 行）。
#: 页面不改代码，只在这一张表里登记「这页的答案长什么样」；
#: 没有登记的页面回退到「按节标题自动提取」。
CONCLUSION_KEYS = {
    # ── 一、物性数据 ──
    "PHCalculator": ("需要体积",),
    "MixedLiquidFlashPointCalculator": ("闪点",),
    # ── 二、工艺设备 ──
    "换热器计算": ("所需饱和蒸汽流量", "冷流体吸热量"),
    "换热器面积": ("设计传热面积", "面积裕度", "理论传热面积"),
    "JacketCoilCalculator": ("所需换热面积", "面积裕量"),
    "AgitatorCalculator": ("推荐电机功率", "通气功率"),
    "设备尺寸计算": ("设备直径", "设备总高（本体）", "工作容积"),
    "罐体重量": ("总重量",),
    "VesselDesignCalculator": ("筒体名义壁厚", "封头名义壁厚", "水压试验压力"),
    "AtmosphericTankThicknessCalculator": ("最小壁厚", "名义厚度"),
    "篮式过滤器": ("有效过滤面积", "滤网内径", "滤网高度"),
    "FilterPressAreaCalculator": ("过滤面积", "干渣产量", "日循环次数"),
    "EvaporatorCalculator": ("蒸发水量", "生蒸汽耗量", "设计面积"),
    "InjectionLiquefierCalculator": ("蒸汽消耗", "蒸汽用量", "喷射出口温度"),
    "FlashEvaporationCalculator": ("闪蒸汽量", "闪蒸后料量"),
    "FlashSteamRecoveryCalculator": ("回收热量", "可加热物料量"),
    "FlashTankCalculator": ("设备规格", "罐高", "筒体容积"),
    "DecolorizationCalculator": ("装炭重量", "接触时间", "带出折纯酸量"),
    "FanPowerCalculator": ("轴功率", "推荐电机规格"),
    # ── 三、流体输送 ──
    "管径计算": ("推荐标准管径", "实际流速", "压降"),
    "管道壁厚": ("推荐取用壁厚", "推荐管道规格", "强度状态"),
    "管道跨距": ("推荐最大跨距",),
    "管道间距": ("最终最小中心距",),
    "管道补偿": ("热膨胀量", "完全约束时的热推力"),
    "压降计算": ("压降百分比", "总压降"),
    "CompressibleFlowPressureDrop": ("压降", "出口压力"),
    "CentrifugalPumpCalculator": ("轴功率", "配套电机功率", "推荐电机"),
    "NPSHaCalculator": ("可用汽蚀余量", "推荐裕量"),
    "蒸汽管径流量": ("推荐标准管径", "实际蒸汽流速", "计算所需管径"),
    "LongDistanceSteamPipeCalculator": ("出口温度", "温度降", "压力降"),
    "CoolingWaterCalculator": ("推荐管径",),
    # ── 四、热工制冷 ──
    "SteamSterilizationCalculator": ("实际蒸汽用量", "单位罐容蒸汽耗量"),
    "RefrigerationCycleCalculator": ("制冷量", "压缩机功率", "性能系数"),
    "InsulationThicknessCalculator": ("推荐保温厚度",),
    # ── 五、安全环保 ──
    "SafetyValveCalculator": ("所需泄放面积", "等效喉径", "推荐标准规格"),
    "消火栓计算": ("主管道直径", "所需扬程", "水泵轴功率"),
    "FireWaterTankCalculator": ("水池有效容积", "设计用水量"),
    "CODEstimator": ("COD浓度", "COD负荷"),
}


def _clean_line(s):
    """把结果行清洗成结论条里该显示的样子：去缩进/项目符号/编号。"""
    s = s.strip()
    for b in _BULLETS:
        if s.startswith(b):
            s = s[len(b):].strip()
            break
    s = _NUMBERING.sub("", s)
    return s.strip()


def _is_formula(s):
    """纯公式行判据：等号右边既不是数字、整行也找不到单位 → 是公式不是结果。"""
    if "=" not in s:
        return False
    if re.search(r"=\s*[-+]?[\d.]", s):
        return False                       # 等号右边直接接数字，是结果
    return not re.search(
        r"(mm|cm|kg|kW|kPa|MPa|GPa|kJ|Pa|W|m²|m³|m/s|kg/h|t/h|m³/h|"
        r"°C|℃|%|min|h|s|L|N|t)\b", s)


def rows_by_keys(lines, keys, max_lines=3):
    """按关键词从前到后捞结果行。

    命中行带数字 → 直接用它；命中行只是个标题（如「1. 有效过滤面积:」）
    → 取下面两行里第一个数值行，拼成「标题：数值」。
    """
    rows = []
    for key in keys:
        for idx, ln in enumerate(lines):
            s = _clean_line(ln)
            if not s.startswith(key):
                continue
            if re.search(r"\d", s) and not _is_formula(s):
                if s not in rows:
                    rows.append(s)
                break
            # 标题行：往下找第一个数值行
            label = s.rstrip("：: ").strip()
            for nxt in lines[idx + 1: idx + 4]:
                t = _clean_line(nxt)
                if not t or not re.search(r"\d", t) or _is_formula(t):
                    continue
                rows.append(f"{label}：{t}")
                break
            break
        if len(rows) >= max_lines:
            break
    return rows[:max_lines]


def _find_titles(lines):
    """找出结果文本里所有节标题，返回 [(行号, 标题)]，按出现顺序。

    兼容两种写法（页面里两种都有）：
      1) ``═══`` / 标题 / ``═══`` 包裹的节
      2) ``【标题】`` 独占一行的节（常作为子节）
    """
    out = []
    i, n = 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if _SECTION_RULE.match(s):
            # ═══ / 标题 / ═══ 三段式：中间那行才是标题
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and not _SECTION_RULE.match(lines[j].strip()):
                nxt = lines[j].strip()
                k = j + 1
                while k < n and not lines[k].strip():
                    k += 1
                if k < n and _SECTION_RULE.match(lines[k].strip()):
                    out.append((j, nxt))
                    i = k + 1
                    continue
            i += 1
            continue
        if _BRACKET_TITLE.match(s):
            out.append((i, s))
        i += 1
    return out


def _section_body(lines, start):
    """取标题之后的节体行：到下一个═══分隔线为止（方括号子标题不算节界）。

    三段式标题后面紧跟着的那条分隔线是下边框，要跳过，不能当成节界。
    """
    body = []
    skipped_leader = False
    for ln in lines[start + 1:]:
        s = ln.strip()
        if _SECTION_RULE.match(s):
            if not skipped_leader:
                skipped_leader = True
                continue
            break
        if _BRACKET_TITLE.match(s):
            continue
        if not s:
            continue
        for b in _BULLETS:
            if s.startswith(b):
                s = s[len(b):].strip()
                break
        if s:
            body.append(s)
    return body


def extract_conclusion(text, max_lines=3):
    """从结果纯文本里取出「结论节」的前若干行。

    返回 ``(标题, [行, ...])``；识别不到结论节时返回 ``(None, [])``。
    宁可返回空也不猜 —— 抓错一行答案比不给答案更糟。
    """
    if not text or not text.strip():
        return None, []
    lines = text.splitlines()
    titles = _find_titles(lines)
    if not titles:
        return None, []
    for want in CONCLUSION_SECTIONS:
        for pos, title in titles:
            if want not in title:
                continue
            rows = _section_body(lines, pos)[:max_lines]
            if rows:
                return title, rows
    return None, []


def build_conclusion_html(title, rows):
    """把结论行渲染成结论条的富文本（首行放大，其余行常规）。"""
    if not rows:
        return ""
    parts = []
    if title:
        shown = title if title.startswith("【") else f"【{title}】"
        parts.append(f'<span style="font-size:11px;">{html.escape(shown)}</span>')
    parts.append(f'<span style="font-size:16px; font-weight:700;">{html.escape(rows[0])}</span>')
    for r in rows[1:]:
        parts.append(f'<span style="font-size:13px;">{html.escape(r)}</span>')
    return "<br>".join(parts)


class CalculatorBase(QWidget):
    """计算器基类"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = None
        self._wheel_blocker = None
        self._conclusion_bar = None
        self._explicit_conclusion = ""
        if data_manager is not None:
            self.init_data_manager(data_manager)
        # 子类的控件在自己 __init__ 里创建，这里只能等事件循环起来再装配
        QTimer.singleShot(0, self._ensure_conclusion_bar)

    # ── 结论条（把答案钉在结果区最上方） ──────────────────────

    @staticmethod
    def _find_result_layout(result_text):
        """找能插到 result_text 上方的那层布局，返回 (layout, 索引)。"""
        w = result_text
        while w is not None:
            lay = w.layout()
            if isinstance(lay, QVBoxLayout):
                idx = lay.indexOf(result_text)
                if idx >= 0:
                    return lay, idx
            w = w.parentWidget()
        return None, -1

    def _ensure_conclusion_bar(self):
        """惰性装配结论条：插在结果框正上方，不改变页面原有布局。"""
        if self._conclusion_bar is not None:
            return self._conclusion_bar
        rt = getattr(self, "result_text", None)
        if rt is None:
            return None
        layout, idx = self._find_result_layout(rt)
        if layout is None:
            return None
        bar = QLabel()
        bar.setObjectName("conclusionBar")
        bar.setTextFormat(Qt.RichText)
        bar.setWordWrap(True)
        bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        bar.hide()
        layout.insertWidget(idx, bar)
        self._conclusion_bar = bar
        rt.textChanged.connect(self._refresh_conclusion)
        self._refresh_conclusion()
        return bar

    def _refresh_conclusion(self):
        """按「显式结论 > 自动提取」的优先级刷新结论条；结果为空则收起。"""
        bar = self._conclusion_bar
        if bar is None:
            return
        rt = getattr(self, "result_text", None)
        text = rt.toPlainText() if rt is not None else ""
        if not text.strip():
            self._explicit_conclusion = ""
            bar.clear()
            bar.hide()
            return
        if self._explicit_conclusion:
            bar.setText(self._explicit_conclusion)
            bar.show()
            return
        # ① 页面登记过「答案长什么样」→ 按关键词捞行（最准）
        keys = CONCLUSION_KEYS.get(type(self).__name__, ())
        if keys:
            rows = rows_by_keys(text.splitlines(), keys)
            if rows:
                bar.setText(build_conclusion_html("计算结果", rows))
                bar.show()
                return
        # ② 没登记 → 按节标题自动提取兜底
        title, rows = extract_conclusion(text)
        if not rows:
            bar.clear()
            bar.hide()
            return
        bar.setText(build_conclusion_html(title, rows))
        bar.show()

    def set_conclusion(self, body, title="结论"):
        """页面显式指定结论（纯文本，可多行），优先于自动提取。

        在 ``result_text`` 写入之后调用；不调用则自动取「计算结果」节的前几行。
        """
        rows = [ln.strip() for ln in str(body or "").splitlines() if ln.strip()]
        self._explicit_conclusion = build_conclusion_html(title, rows) if rows else ""
        self._ensure_conclusion_bar()
        self._refresh_conclusion()

    def clear_conclusion(self):
        """清掉显式结论，回到自动提取。"""
        self._explicit_conclusion = ""
        self._refresh_conclusion()

    @property
    def conclusion_text(self):
        """结论条当前显示的纯文本（供测试断言）。"""
        bar = self._conclusion_bar
        return bar.text() if bar is not None else ""


    # ── 数据管理器 ────────────────────────────────────────────

    def init_data_manager(self, data_manager=None):
        """初始化数据管理器（单例模式）"""
        if data_manager is not None:
            self.data_manager = data_manager
            return
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception:
            self.data_manager = None

    # ── ComboBox 滚轮拦截 ──────────────────────────────────────

    def setup_wheel_blocker(self):
        """拦截所有 QComboBox 的鼠标滚轮事件"""
        self._wheel_blocker = ComboBoxWheelBlocker(self)
        for combo in self.findChildren(QComboBox):
            combo.installEventFilter(self._wheel_blocker)

    # ── 报告导出 ──────────────────────────────────────────────

    def download_docx_report(self, title=None):
        """生成 DOCX 计算书"""
        t = title or self.__class__.__name__
        ReportExporter.export_docx(self, t)

    def download_pdf_report(self, title=None):
        """生成 PDF 计算书"""
        t = title or self.__class__.__name__
        ReportExporter.export_pdf(self, t)

    # ── 模式按钮组工具 ────────────────────────────────────────

    @staticmethod
    def make_mode_button(text, tooltip=""):
        """创建可选中模式按钮，并应用 MODE_BUTTON_STYLE"""
        from PySide6.QtWidgets import QPushButton
        from PySide6.QtWidgets import QSizePolicy
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setToolTip(tooltip)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setStyleSheet(MODE_BUTTON_STYLE)
        return btn

    @staticmethod
    def make_calc_button(text="计 算"):
        """创建计算按钮，应用 CALC_BUTTON_STYLE"""
        from PySide6.QtWidgets import QPushButton
        from PySide6.QtWidgets import QSizePolicy
        btn = QPushButton(text)
        btn.setMinimumHeight(50)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setStyleSheet(CALC_BUTTON_STYLE)
        return btn

    @staticmethod
    def make_combo_box():
        """创建带 COMBOBOX_STYLE 的 QComboBox"""
        from PySide6.QtWidgets import QComboBox
        cb = QComboBox()
        cb.setStyleSheet(COMBOBOX_STYLE)
        return cb

    @staticmethod
    def make_group_box(title):
        """创建带 GROUP_STYLE 的 QGroupBox"""
        from PySide6.QtWidgets import QGroupBox
        gb = QGroupBox(title)
        gb.setStyleSheet(GROUP_STYLE)
        return gb
