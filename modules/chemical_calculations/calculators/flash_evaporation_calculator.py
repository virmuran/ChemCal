"""
闪蒸（料液减压闪蒸）计算器 —— 降温 / 闪蒸汽量 / 浓缩

适用：淀粉糖、味精、酒精、氨基酸等行业的**液化液维持后减压闪蒸**工段，
      以及各类热料液进常压/真空闪蒸罐的降温、二次蒸汽回收核算。

═══════════════ 1. 闪蒸在工艺上干什么 ═══════════════
    喷射液化后的料液（105~140 °C）必须在进入糖化/发酵前**快速降温**到工艺温度。
    直接把料液送进**低压（常压或真空）闪蒸罐**，罐内压力低于料液温度对应的
    饱和压力，一部分水立刻汽化（闪蒸），靠汽化潜热把余下料液**自行降到**
    该压力下的平衡温度——不用换热器、降温快、兼得二次蒸汽。

    本计算器算三件事：
        ① 释放功率（料液降温放出的热）        Q
        ② 闪蒸汽量（这部分热汽化掉多少水）    D_f
        ③ 闪蒸后的料液量与浓度                G' / X'

═══════════════ 2. 释放功率（设计表格口径）═══════════════
        Q = (物料量 + 蒸汽用量) · (t进 − t出) · C · 1000 / 3600      [kW]

    · 「物料量 + 蒸汽用量」= 闪蒸进料量：喷射器出口的料液 = 原始淀粉乳 G
      **加上**喷射用的蒸汽 D（蒸汽凝水留在了料液里），故两列相加。
      ⚠ 两列单位常不一致（物料量 t/h、蒸汽用量 kg/h），相加前必须统一，
      本计算器内部一律折成 kg/h 再相加。
    · C = 物料比热（= 喷射器算出的**稀释后**比热），ΔT = 进/出闪蒸温度之差。

═══════════════ 3. 闪蒸汽量（本计算器核心）═══════════════
    绝热闪蒸的热量衡算（以 0 °C 液态水为焓基准）：

        M·C·(t进 − t出) = D_f · [ h_g(t出) − C·t出 ]
        ⇒  **D_f = M·C·(t进 − t出) / ( h_g(t出) − C·t出 )**          [kg/h]

    · h_g(t出) = t出 温度下的**饱和蒸汽总焓**（≈ 2676 kJ/kg @100 °C）
    · C·t出    = 闪蒸掉的那部分水在料液里原本的显热（按料液加权比热计）
    · 分母 = 总焓 − 显热 = 水从「料液中 t出 的液态」变成「t出 的汽态」所需焓差，
      在 100 °C 时约 2337 kJ/kg，**比同压汽化潜热 r = 2258.77 大 3.5 %**。

    ⚠⚠ 设计表格里的写法是「汽化焓 − t出·C」，**分母只减了显热、没把汽化焓
       换成总焓**。若「0.1 MPa 蒸汽汽化焓」一栏填的是**汽化潜热 2258.77**，
       则分母偏小约 18 %、闪蒸汽量被**高估约 22 %**。本计算器两条口径并列输出
       并给出差值百分比：
           主算（严格）  = M·C·ΔT / (h_g(t出) − C·t出)
           表格口径      = M·C·ΔT / (r₀ − C·t出)      ← r₀ = 你填的汽化焓
       表格里正确的填法是把这一栏当**总焓**用（0.1 MPa 下 ≈ 2676 kJ/kg），
       或直接把该栏留空由本器按 t出 自动取 IAPWS 总焓。

    「验算」行 = 与「闪蒸汽用量」同一个分子分母，只是把 ×1000/3600 约掉了，
    即同一结果的 **t/h 口径**（闪蒸汽用量 kg/h ÷ 1000），用于单位互校，
    不是第三个公式。

═══════════════ 4. 闪蒸后的料液（量减、浓度升）═══════════════
        G' = M − D_f                              （闪蒸汽带走了一部分水）
        X' = G·X / G'                             （干物量不变，水少了 → 浓度升）

    ⚠ 与喷射液化器**相反**：喷射是加蒸汽凝水**稀释**，闪蒸是汽化失水**浓缩**。

═══════════════ 5. 适用边界 ═══════════════
        t进 ＞ t出（否则无闪蒸推动力）；t出 应 ≈ 该压力下的饱和温度
        · 常压闪蒸（0.101325 MPa）：t出 ≈ 100 °C，再低就得抽真空
        · 出闪蒸温度高于该压力饱和温度 → 提示核对（多余热量只会多蒸水，
          料液温度会被钉在饱和温度附近）

═══════════════ 6. 计算链联动（与喷射液化器复用数据）══════════════
    本页「进料」各项可取**上游页面**的计算结果，不必手抄：
        物料量     ← 喷射液化器「浆料量」        (t/h)
        蒸汽用量   ← 喷射液化器「蒸汽用量」      (kg/h)
        物料比热   ← 喷射液化器「物料比热」      (kJ/(kg·K)，已含稀释后浓度)
        干物浓度   ← 喷射液化器「干物浓度」      (wt%)
        进闪蒸温度 ← 喷射液化器「出口温度」      (°C)
    取值后仍可手工修改；上游若重新计算过，本页会提示「数据可能已过期」。

═══════════════ 7. 数据来源与口径 ═══════════════
    · 饱和蒸汽总焓 / 饱和水焓 / 饱和温度：项目自带 IAPWS-IF97（steam_iapws）。
    · 绝热闪蒸热量衡算式为化工原理与淀粉糖行业设计资料通用式；
      设计表格的「汽化焓 − t出·C」写法与之同源，差别只在分母取潜热还是总焓（见 §3）。
    · 物料比热取自喷射液化器（加权式 C = C₀·X/100 + C_w·(100−X)/100）；
      若单独使用本页，请填物料实测比热。
"""

import math
import os
import importlib.util

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QGridLayout, QTextEdit, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtSvgWidgets import QSvgWidget

from app_styles import (COMBOBOX_STYLE, SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)
from utils.docx_utils import ReportExporter
from svg_utils import svg_text
from datetime import datetime

from calculator_base import CalculatorBase
from common_constants import WATER_CP
# 计算链：与喷射液化器等页面共享「上游输出」，一键取用
from chain_context import ChainContext

# IAPWS-IF97 完整物性（动态导入，写法与喷射液化器/浓缩蒸发器一致）
try:
    _cur = os.path.dirname(os.path.abspath(__file__))
    _parent = os.path.dirname(_cur)
    _spec = importlib.util.spec_from_file_location(
        "steam_iapws", os.path.join(_parent, "steam_iapws.py"))
    _STEAM = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_STEAM)
except Exception as _e:                                          # noqa: BLE001
    print(f"警告: 无法加载 IAPWS-IF97 模块: {_e}")
    _STEAM = None


#: 常压闪蒸的绝压（MPa）—— 设计表格默认口径
ATM_ABS_MPA = 0.101325

#: 设计表格里「0.1 MPa 蒸汽汽化焓」的常见填值（汽化潜热，kJ/kg）
R0_TAB_DEFAULT = 2258.77

#: 蒸汽管道标准公称通径系列（mm）
_DN_SERIES = [15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200,
              250, 300, 350, 400, 450, 500, 600]

#: 闪蒸二次蒸汽的管内流速按低压饱和蒸汽取（m/s）
U_STEAM_FLASH = 25.0


class FlashEvaporationCalculator(CalculatorBase):
    """闪蒸（料液减压闪蒸）计算器：降温 / 闪蒸汽量 / 浓缩"""

    #: 计算链标识（供更下游的页面取用本页输出）
    CHAIN_MODULE = "flash_evaporation_calculator"
    CHAIN_PAGE = "闪蒸降温浓缩"

    #: 取上游值时的字段映射：上游输出键 → (本页输入控件属性名, 换算系数, 单位)
    #: 「浆料量」与「物料量」是同一栏在不同页面的叫法，都接受
    CHAIN_MAP = [
        ("浆料量", "feed_input", 1.0, "t/h"),
        ("物料量", "feed_input", 1.0, "t/h"),
        ("蒸汽用量", "steam_input", 1.0, "kg/h"),
        ("物料比热", "cp_input", 1.0, "kJ/(kg·K)"),
        ("干物浓度", "conc_input", 1.0, "wt%"),
        ("出口温度", "tin_input", 1.0, "°C"),
    ]

    #: 取上游值时打标记的行 key ↔ 控件属性名
    _MARK_ROWS = {
        "feed_input": "feed", "steam_input": "steam", "cp_input": "cp",
        "conc_input": "conc", "tin_input": "tin",
    }

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_result = {}
        self._rows = {}                       # 行控件登记（供标记/显隐）
        self._hint_base = {}                  # 提示文本原值（标记还原用）
        self._chain_ref = {}                  # 本次引用的上游标记
        self._chain_sources = []              # 下拉里可用的来源（与序号对应）
        self.setup_ui()
        self.setup_default_values()
        self.setup_wheel_blocker()

    # ═══════════════════════ UI ═══════════════════════
    def setup_ui(self):
        main = QHBoxLayout(self)
        main.setSpacing(15)
        main.setContentsMargins(10, 10, 10, 10)

        # ── 左栏：输入 ──
        scroll = QScrollArea()
        scroll.setStyleSheet(SCROLL_AREA_STYLE)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setSpacing(10)

        desc = QLabel(
            "料液减压闪蒸核算：喷射液化后的高温料液进闪蒸罐 → 绝热闪蒸降温 → "
            "闪蒸汽量（二次蒸汽）→ 闪蒸后料液量与浓度。"
            "「进料」各项可取上游（喷射液化器）的计算结果，不必手抄。")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size:12px;padding:5px;")
        ll.addWidget(desc)

        ls = INPUT_LABEL_STYLE

        def lbl(t):
            w = QLabel(t)
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            w.setStyleSheet(ls)
            return w

        def hint(t):
            w = QLabel(t)
            w.setStyleSheet("font-style:italic;color:#666;")
            return w

        def add_row(grid, key, text, widget, hint_text, row):
            """建一行「标签 + 控件 + 提示」，并按 key 登记"""
            a, b, c = lbl(text), widget, hint(hint_text)
            grid.addWidget(a, row, 0)
            grid.addWidget(b, row, 1)
            grid.addWidget(c, row, 2)
            self._rows.setdefault(key, []).extend([a, b, c])
            self._hint_base[key] = hint_text
            return row + 1

        def new_grid(box):
            g = QGridLayout(box)
            g.setHorizontalSpacing(10)
            g.setVerticalSpacing(10)
            g.setColumnStretch(0, 4)
            g.setColumnStretch(1, 8)
            g.setColumnStretch(2, 6)
            return g

        # ── 计算链：取上游值 ──
        g0 = CalculatorBase.make_group_box("计算链（与上游页面联动）")
        g0g = new_grid(g0)
        g0g.setColumnStretch(3, 2)

        self.chain_combo = QComboBox()
        self.chain_combo.setStyleSheet(COMBOBOX_STYLE)
        self.chain_combo.setMinimumWidth(230)
        g0g.addWidget(lbl("上游来源:"), 0, 0)
        g0g.addWidget(self.chain_combo, 0, 1, 1, 2)

        self.chain_btn = QPushButton("取上游值")
        self.chain_btn.setStyleSheet(CLEAR_BTN_STYLE)
        g0g.addWidget(self.chain_btn, 0, 3)

        self.chain_status = QLabel("")
        self.chain_status.setWordWrap(True)
        self.chain_status.setStyleSheet("font-size:12px;color:#666;")
        g0g.addWidget(self.chain_status, 1, 1, 1, 3)
        ll.addWidget(g0)

        # ── 进料（可取上游）──
        g1 = CalculatorBase.make_group_box("进料（可取上游）")
        g1g = new_grid(g1)
        r = 0

        self.feed_input = QLineEdit("20")
        self.feed_input.setValidator(QDoubleValidator(0.01, 10000.0, 3))
        r = add_row(g1g, "feed", "物料量 G (t/h):", self.feed_input,
                    "原始淀粉乳量；闪蒸进料 = 物料量 + 蒸汽用量", r)

        self.steam_input = QLineEdit("0")
        self.steam_input.setValidator(QDoubleValidator(0.0, 1000000.0, 2))
        r = add_row(g1g, "steam", "蒸汽用量 D (kg/h):", self.steam_input,
                    "喷射器总用汽量；不含喷射时填 0", r)

        self.conc_input = QLineEdit("30")
        self.conc_input.setValidator(QDoubleValidator(0.5, 70.0, 2))
        r = add_row(g1g, "conc", "干物浓度 X (wt%):", self.conc_input,
                    "取喷射器「稀释后浓度」（闪蒸前）", r)

        self.cp_input = QLineEdit("3.39")
        self.cp_input.setValidator(QDoubleValidator(1.0, 5.0, 4))
        r = add_row(g1g, "cp", "物料比热 C (kJ/(kg·K)):", self.cp_input,
                    "取喷射器「物料比热」；单独算时填实测值", r)

        self.feed_total_label = QLabel("")
        self.feed_total_label.setStyleSheet("font-size:12px;color:#444;")
        g1g.addWidget(self.feed_total_label, r, 0, 1, 3)
        r += 1

        ll.addWidget(g1)

        # ── 闪蒸条件 ──
        g2 = CalculatorBase.make_group_box("闪蒸条件")
        g2g = new_grid(g2)
        r = 0

        self.tin_input = QLineEdit("105")
        self.tin_input.setValidator(QDoubleValidator(5.0, 200.0, 2))
        r = add_row(g2g, "tin", "进闪蒸温度 t₁ (°C):", self.tin_input,
                    "喷射器出口温度", r)

        self.tout_input = QLineEdit("100")
        self.tout_input.setValidator(QDoubleValidator(1.0, 200.0, 2))
        r = add_row(g2g, "tout", "出闪蒸温度 t₂ (°C):", self.tout_input,
                    "常压闪蒸 ≈ 100；真空更低", r)

        self.p_input = QLineEdit("0.101325")
        self.p_input.setValidator(QDoubleValidator(0.001, 1.0, 6))
        r = add_row(g2g, "p", "闪蒸压力 p (MPa 绝压):", self.p_input,
                    "常压 0.101325；抽真空填更小", r)

        self.r0_input = QLineEdit("")
        self.r0_input.setValidator(QDoubleValidator(100.0, 4000.0, 2))
        self.r0_input.setPlaceholderText("留空 = 按总焓算")
        r = add_row(g2g, "r0", "表格「汽化焓」列 (kJ/kg):", self.r0_input,
                    f"填表格值可对照（如 {R0_TAB_DEFAULT:g} 会提示偏高）", r)

        self.hg_input = QLineEdit("")
        self.hg_input.setValidator(QDoubleValidator(1000.0, 4000.0, 2))
        self.hg_input.setPlaceholderText("留空 = 按 t₂ 自动算")
        r = add_row(g2g, "hg", "总焓 h_g 查表值 (kJ/kg):", self.hg_input,
                    "主算用；0.1MPa ≈ 2676，留空自动", r)

        ll.addWidget(g2)
        ll.addStretch()
        scroll.setWidget(lw)

        # ── 右栏：结果 ──
        rw = QWidget()
        rw.setMinimumWidth(300)
        rl = QVBoxLayout(rw)
        rl.setSpacing(15)

        self.svg_widget = QSvgWidget()
        self.svg_widget.setMinimumHeight(200)
        self.svg_widget.setMaximumHeight(260)
        self.svg_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rl.addWidget(self.svg_widget)
        self.svg_widget.renderer().setAspectRatioMode(Qt.KeepAspectRatio)

        rg = CalculatorBase.make_group_box("计算结果")
        rvl = QVBoxLayout(rg)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setStyleSheet(
            "QTextEdit { font-family: Consolas, 'Microsoft YaHei', monospace; font-size: 13px; }")
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        rvl.addWidget(self.result_text)
        rl.addWidget(rg)

        bl = QHBoxLayout()
        bl.setSpacing(8)
        for name, style, cb in [
            ("清空", CLEAR_BTN_STYLE, self.clear_inputs),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(name)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(cb)
            bl.addWidget(btn)
        rl.addLayout(bl)

        calc_btn = self.make_calc_button("计 算")
        calc_btn.clicked.connect(self.calculate)
        rl.addWidget(calc_btn)

        main.addWidget(scroll, 2)
        main.addWidget(rw, 1)

        # 控件全部建好后再连信号、再填下拉项（避免早发信号时访问未建控件）
        self.chain_btn.clicked.connect(self._apply_chain_source)
        for attr in self._MARK_ROWS:
            w = getattr(self, attr, None)
            if w is not None:
                w.textEdited.connect(lambda _t, a=attr: self._clear_row_mark(a))
        self._reload_chain_sources()
        self.chain_combo.currentIndexChanged.connect(self._refresh_chain_status)
        # 输入变化时刷新「闪蒸进料量」预览
        for attr in ("feed_input", "steam_input"):
            getattr(self, attr).textChanged.connect(self._update_feed_total_label)
        self._update_feed_total_label()
        self._update_svg_diagram()

    # ═══════════════════════ 计算链 ═══════════════════════
    def _reload_chain_sources(self):
        """刷新可用上游来源下拉（保留当前选中项）"""
        self.chain_combo.blockSignals(True)
        self.chain_combo.clear()
        self.chain_combo.addItem("（不使用上游数据）")
        self._chain_sources = []
        try:
            for e in ChainContext.sources():
                if e.get("module") == self.CHAIN_MODULE:
                    continue                     # 不把本页自己列为上游
                note = f" · {e['note']}" if e.get("note") else ""
                self.chain_combo.addItem(f"{e['page']}  {e['time_str']}{note}")
                self._chain_sources.append(e)
        except Exception as ex:                                   # noqa: BLE001
            print(f"读取计算链来源失败: {ex}")
        self.chain_combo.blockSignals(False)

    def _apply_chain_source(self):
        """把选中上游页的可传递输出填进本页输入框"""
        idx = self.chain_combo.currentIndex()
        if idx <= 0 or idx - 1 >= len(self._chain_sources):
            self.chain_status.setText("未选择上游来源（可直接手填各项）。")
            return
        entry = self._chain_sources[idx - 1]
        vals = entry.get("values", {})
        filled = []
        for key, attr, factor, unit in self.CHAIN_MAP:
            if key not in vals:
                continue
            try:
                v = float(vals[key]) * factor
            except (TypeError, ValueError):
                continue
            w = getattr(self, attr, None)
            if w is None:
                continue
            w.setText(f"{v:.10g}")
            self._set_row_mark(attr, "←上游")
            filled.append(key)
        self._chain_ref = ChainContext.make_ref(entry.get("module"))
        self._update_feed_total_label()
        if filled:
            self.chain_status.setText(
                f"已取用：{ChainContext.describe_ref(self._chain_ref)}"
                f"　→　{('、'.join(filled))}"
                f"（填进输入框后仍可手工修改）")
        else:
            self.chain_status.setText(
                f"{ChainContext.describe_ref(self._chain_ref)} 没有可用的传递值。")
        self._refresh_chain_status()

    def _set_row_mark(self, attr, mark):
        """在对应输入的提示列打/清「←上游」标记"""
        key = self._MARK_ROWS.get(attr)
        if not key:
            return
        rows = self._rows.get(key, ())
        if len(rows) < 3:
            return
        base = self._hint_base.get(key, "")
        rows[2].setText(f"{base}　[{mark}]" if mark else base)

    def _clear_row_mark(self, attr):
        """用户手改输入后撤掉该行的上游标记（引用只是填值，不做绑定）"""
        self._set_row_mark(attr, "")

    def _refresh_chain_status(self, *_a):
        """检查上游是否在本页引用之后又重算过（过期提示）"""
        if not self._chain_ref:
            return
        try:
            if ChainContext.is_stale(self._chain_ref):
                now = ChainContext.get(self._chain_ref.get("module")) or {}
                self.chain_status.setText(
                    f"⚠ 数据来源 {ChainContext.describe_ref(self._chain_ref)}"
                    f"，但该页之后已重算（最新 {now.get('time_str', '')}）"
                    f"——当前输入可能已过期，建议重新「取上游值」。")
            else:
                self.chain_status.setText(
                    f"数据来源：{ChainContext.describe_ref(self._chain_ref)}（最新，未过期）")
        except Exception:                                        # noqa: BLE001
            pass

    def showEvent(self, event):                                  # noqa: N802
        """页面显示时刷新来源列表与过期状态（上游可能刚重算过）"""
        try:
            self._reload_chain_sources()
            self._refresh_chain_status()
        except Exception as e:                                   # noqa: BLE001
            print(f"刷新计算链状态失败: {e}")
        super().showEvent(event)

    def _update_feed_total_label(self):
        """预览闪蒸进料量 = 物料量 + 蒸汽用量（折成 kg/h 相加）"""
        try:
            g_t = float(self.feed_input.text().strip() or 0)
            d_kg = float(self.steam_input.text().strip() or 0)
        except (TypeError, ValueError):
            self.feed_total_label.setText("")
            return
        m_kg = g_t * 1000.0 + d_kg
        self.feed_total_label.setText(
            f"闪蒸进料量 = 物料量 + 蒸汽用量 = {g_t:.3f} t/h + {d_kg:.1f} kg/h"
            f" = {m_kg:.0f} kg/h = {m_kg / 1000.0:.3f} t/h")

    # ═══════════════════════ 工具 ═══════════════════════
    @staticmethod
    def _num(widget, name):
        try:
            return float(widget.text().strip())
        except (TypeError, ValueError):
            raise ValueError(f"{name} 未填写或不是数字")

    @staticmethod
    def _num_opt(widget, name):
        """可留空的数值输入：空串 → None；非空但不是数字 → 报错"""
        txt = (widget.text() or "").strip()
        if not txt:
            return None
        try:
            return float(txt)
        except (TypeError, ValueError):
            raise ValueError(f"{name} 不是数字")

    @staticmethod
    def _sat_from_temp(t_c):
        """饱和参数（温度 °C）→ dict（IAPWS-IF97）"""
        if _STEAM is None:
            raise ValueError("IAPWS-IF97 模块不可用，无法计算饱和蒸汽物性")
        return _STEAM.saturation_properties(T_C=t_c)

    @staticmethod
    def _sat_from_abs(p_abs):
        """饱和参数（绝压 MPa）→ dict（IAPWS-IF97）"""
        if _STEAM is None:
            raise ValueError("IAPWS-IF97 模块不可用，无法计算饱和蒸汽物性")
        return _STEAM.saturation_properties(P_MPa=p_abs)

    @staticmethod
    def _dn_for(q_m3h, u_ms=U_STEAM_FLASH):
        """按体积流量与流速估管径，返回 (标准 DN, 计算内径 mm, 实际流速 m/s)"""
        if q_m3h <= 0:
            return 0, 0.0, 0.0
        area = q_m3h / 3600.0 / u_ms
        d_mm = math.sqrt(4.0 * area / math.pi) * 1000.0
        dn = next((d for d in _DN_SERIES if d >= d_mm), _DN_SERIES[-1])
        u_act = q_m3h / 3600.0 / (math.pi * (dn / 1000.0) ** 2 / 4.0)
        return dn, d_mm, u_act

    # ═══════════════════════ 计算 ═══════════════════════
    def calculate(self):
        try:
            res = self._compute()
            self._last_result = res
            self._publish_chain(res)
            self._render(res)
            self._refresh_chain_status()
            self._update_svg_diagram()
        except ValueError as e:
            self._show_error(str(e))
        except Exception as e:                                   # noqa: BLE001
            self._show_error(f"计算错误：{e}")

    def _publish_chain(self, r):
        """把本页输出登记到计算链（供更下游的页面取用）"""
        vals = {
            "闪蒸汽量": r.get("D_f", 0.0),                    # kg/h
            "闪蒸压力": r.get("p_abs", 0.0),                  # MPa 绝压（下游换 kPa）
            "闪蒸后料量": r.get("G_after_t", 0.0),            # t/h
            "闪蒸后浓度": r.get("X_after", 0.0),              # wt%
            "出闪蒸温度": r.get("t2", 0.0),                   # °C
            "释放功率": r.get("Q_kW", 0.0),                   # kW
        }
        units = {"闪蒸汽量": "kg/h", "闪蒸压力": "MPa 绝压",
                 "闪蒸后料量": "t/h", "闪蒸后浓度": "wt%",
                 "出闪蒸温度": "°C", "释放功率": "kW"}
        try:
            entry = ChainContext.publish(self.CHAIN_MODULE, self.CHAIN_PAGE,
                                         values=vals, units=units,
                                         note=f"→{r.get('t2', 0):.0f}°C")
            r["chain_published"] = bool(entry)
            r["chain_values"] = vals
            r["chain_units"] = units
            r["chain_time_str"] = entry["time_str"] if entry else ""
        except Exception as e:                                   # noqa: BLE001
            print(f"计算链登记失败（不影响计算）: {e}")
            r["chain_published"] = False

    def _compute(self):
        # ── 进料 ──
        G_t = self._num(self.feed_input, "物料量")
        D_kg = self._num(self.steam_input, "蒸汽用量")
        X = self._num(self.conc_input, "干物浓度") / 100.0
        C = self._num(self.cp_input, "物料比热")
        # ── 闪蒸条件 ──
        t1 = self._num(self.tin_input, "进闪蒸温度")
        t2 = self._num(self.tout_input, "出闪蒸温度")
        p_abs = self._num(self.p_input, "闪蒸压力")
        r0_in = self._num_opt(self.r0_input, "表格「汽化焓」")
        hg_in = self._num_opt(self.hg_input, "总焓（查表值）")

        # ── 校验 ──
        if G_t <= 0:
            raise ValueError("物料量必须大于 0")
        if D_kg < 0:
            raise ValueError("蒸汽用量不能为负（不含喷射时填 0）")
        if not (0.0 < X < 1.0):
            raise ValueError("干物浓度应在 0~100 wt% 之间")
        if not (1.0 <= C <= 5.0):
            raise ValueError("物料比热应在 1.0~5.0 kJ/(kg·K) 之间")
        if t2 <= 0:
            raise ValueError("出闪蒸温度必须大于 0 °C")
        if t1 <= t2:
            raise ValueError(
                f"进闪蒸温度 {t1:.1f} °C 必须高于出闪蒸温度 {t2:.1f} °C"
                f"——否则没有闪蒸推动力（温差 ΔT = {t1 - t2:.1f} °C ≤ 0）")
        if r0_in is not None and r0_in <= 0:
            raise ValueError("表格「汽化焓」必须大于 0（留空则按总焓算）")
        if not (0.001 < p_abs < 16.5):
            raise ValueError(f"闪蒸压力 {p_abs:.5f} MPa(a) 超出 IAPWS-IF97 饱和线范围")

        # ── 闪蒸压力下的饱和温度（边界校核用）──
        sat_p = self._sat_from_abs(p_abs)
        t_sat_p = sat_p["T_C"]

        warn = []
        if t2 > t_sat_p + 5.0:
            raise ValueError(
                f"出闪蒸温度 {t2:.1f} °C 高于闪蒸压力 {p_abs:.5f} MPa(a) 下的饱和温度 "
                f"{t_sat_p:.2f} °C ——闪蒸罐内的料液温度会被钉在饱和温度附近，"
                f"到不了你填的出料温度。\n"
                f"  常压闪蒸（0.101325 MPa）的出料温度上限约 100 °C；"
                f"要到 {t2:.1f} °C 须把闪蒸压力提高到 "
                f"{self._p_sat_of(t2):.4f} MPa(a)；反之要更低的出料温度则须抽真空。")
        elif t2 > t_sat_p + 1.0:
            warn.append(
                f"出闪蒸温度 {t2:.1f} °C 略高于该压力下饱和温度 {t_sat_p:.2f} °C"
                f"——实际闪蒸罐内料液会稳定在饱和温度附近，多出的热量只会多蒸一点水。"
                f"请核对该温度取值")

        # ── 进料与释放功率（设计表格口径）──
        M_kg = G_t * 1000.0 + D_kg                    # 闪蒸进料量 kg/h
        dT = t1 - t2
        Q_kjh = M_kg * C * dT                         # kJ/h
        Q_kW = Q_kjh / 3600.0

        # ── 闪蒸汽量：严格口径（总焓 − 显热）──
        sat_t = self._sat_from_temp(t2)
        h_g_auto = sat_t["h_g"]
        if hg_in is not None:
            h_g = hg_in
            hg_src = "查表输入"
        else:
            h_g = h_g_auto
            hg_src = "自动（按 t₂ 取 IAPWS 饱和汽总焓）"
        c_t2 = C * t2                                 # 料液中 t2 温度水的显热 kJ/kg
        denom = h_g - c_t2
        if denom <= 0:
            raise ValueError(
                f"闪蒸焓差 (h_g(t₂) − C·t₂) = {denom:.1f} kJ/kg ≤ 0："
                f"总焓 {h_g:.1f} 不大于显热 {c_t2:.1f}，参数不自洽")
        D_f = Q_kjh / denom                           # kg/h（严格口径）

        # 「总焓（查表）」与自动算值对照（同喷射液化器的总焓处理）
        if hg_in is not None and h_g_auto > 0 and abs(h_g - h_g_auto) > 0.01 * h_g_auto:
            warn.append(
                f"你填的总焓 {h_g:.1f} kJ/kg 与按 t₂ = {t2:.1f} °C 自动算的饱和汽总焓 "
                f"{h_g_auto:.1f} kJ/kg 相差 {abs(h_g - h_g_auto) / h_g_auto * 100:.2f} %"
                f"——请核对是否查错了蒸汽表（本器按你填的值计算）")

        # ── 表格口径对照（汽化焓 − 显热）──
        # 「表格汽化焓」留空时按 t₂ 下总焓处理（此时两条口径相同，无提示）
        if r0_in is not None:
            r0 = r0_in
            r0_src = "表格填值"
        else:
            r0 = h_g
            r0_src = "自动（= t₂ 下饱和汽总焓）"
        denom_tab = r0 - c_t2
        D_f_tab = Q_kjh / denom_tab if denom_tab > 0 else 0.0
        d_tab_pct = (D_f_tab - D_f) / D_f * 100.0 if D_f > 0 else 0.0
        r_at_t2 = sat_t["h_fg"]                       # t₂ 下的汽化潜热（IAPWS）
        #: 表格填值 r₀ 是否≈ 潜热（而不是总焓）
        r0_is_latent = abs(r0 - r_at_t2) <= 0.01 * r_at_t2
        r0_vs_hg_pct = (h_g - r0) / r0 * 100.0 if r0 > 0 else 0.0

        if r0_in is not None and abs(d_tab_pct) > 1.0:
            warn.append(
                f"表格口径（汽化焓 {r0:.1f} − C·t₂）算得闪蒸汽量 {D_f_tab:.1f} kg/h，"
                f"比严格口径（总焓 {h_g:.1f} − C·t₂）的 {D_f:.1f} kg/h "
                f"{'高' if d_tab_pct > 0 else '低'} {abs(d_tab_pct):.1f} %。"
                f"原因：闪蒸掉的水是在 **t₂ 温度下汽化**的，分母应取该温度下蒸汽的"
                f"**总焓 h_g**（≈{h_g_auto:.0f}）而不是汽化潜热（≈{r_at_t2:.0f}）；"
                f"两者差 {r0_vs_hg_pct:.1f} %（含水的显热 h_f = {sat_t['h_f']:.1f}）。"
                f"建议把表格「汽化焓」列改为总焓或直接留空由本器自动取"
                f"（本器按严格口径给结果，表格口径仅作对照）")

        # ── 闪蒸后料液 ──
        G_after_kg = M_kg - D_f
        if G_after_kg <= 0:
            raise ValueError(
                f"闪蒸汽量 {D_f:.1f} kg/h 已不小于进料量 {M_kg:.1f} kg/h——"
                f"参数不合理（温差过大或比热/汽化焓口径有误）")
        G_after_t = G_after_kg / 1000.0
        solid_t = G_t * X                              # 干物量 t/h
        X_after = solid_t / G_after_t * 100.0 if G_after_t > 0 else 0.0
        if X_after >= 100.0:
            raise ValueError(f"闪蒸后干物浓度 {X_after:.1f} wt% 已达 100 %，参数不合理")
        C_after = 1.55 * (X_after / 100.0) + WATER_CP * (1.0 - X_after / 100.0)

        # ── 闪蒸二次蒸汽体积与管径 ──
        v_g = sat_t["v_g"]                             # m³/kg @ t₂
        v_flash = D_f * v_g                            # m³/h
        dn, d_calc, u_act = self._dn_for(v_flash)
        #: 单位气耗：每吨进料闪蒸出的汽量（kg 汽/t 进料）
        unit_flash = D_f / (M_kg / 1000.0) if M_kg > 0 else 0.0
        #: 验算行（表格口径 t/h）：与表格「验算」列同式，×1000/3600 约掉
        check_tab = D_f_tab / 1000.0
        conc_ratio = X_after / (X * 100.0) if X > 0 else 0.0

        return {
            # 输入回显
            "G_t": G_t, "D_kg": D_kg, "M_kg": M_kg, "X": X * 100.0, "C": C,
            "t1": t1, "t2": t2, "dT": dT, "p_abs": p_abs,
            "r0": r0, "r0_in": r0_in, "r0_src": r0_src,
            "hg_in": hg_in, "hg_src": hg_src,
            # 压力与饱和态
            "t_sat_p": t_sat_p, "h_g": h_g, "h_g_auto": h_g_auto,
            "h_f": sat_t["h_f"], "r_at_t2": r_at_t2, "v_g": v_g,
            "c_t2": c_t2, "denom": denom,
            # 释放功率与闪蒸汽
            "Q_kjh": Q_kjh, "Q_kW": Q_kW,
            "D_f": D_f, "denom_tab": denom_tab, "D_f_tab": D_f_tab,
            "d_tab_pct": d_tab_pct, "r0_is_latent": r0_is_latent,
            "r0_vs_hg_pct": r0_vs_hg_pct, "check_tab": check_tab,
            "unit_flash": unit_flash,
            # 闪蒸后料液
            "G_after_kg": G_after_kg, "G_after_t": G_after_t,
            "solid_t": solid_t, "X_after": X_after, "C_after": C_after,
            "conc_ratio": conc_ratio,
            # 二次蒸汽
            "v_flash": v_flash, "dn": dn, "d_calc": d_calc, "u_act": u_act,
            # 计算链来源
            "chain_src": ChainContext.describe_ref(self._chain_ref),
            "warn": warn,
        }

    @staticmethod
    def _p_sat_of(t_c):
        """由饱和温度求绝压 MPa（IAPWS-IF97）"""
        if _STEAM is None:
            raise ValueError("IAPWS-IF97 模块不可用，无法计算饱和压力")
        return _STEAM.saturation_pressure(t_c)

    # ═══════════════════════ 结果渲染 ═══════════════════════
    def _render(self, r):
        L = []
        L.append("闪蒸（料液减压闪蒸）计算")
        L.append("=" * 58)
        if r.get("chain_src"):
            L.append(f"【计算链来源】{r['chain_src']}（进料各项引用上游结果，可手工修改）")
            L.append("")
        L.append("【一、进料与物料比热】")
        L.append(f"  物料量 G          = {r['G_t']:.3f} t/h = {r['G_t'] * 1000:.0f} kg/h")
        L.append(f"  蒸汽用量 D        = {r['D_kg']:.1f} kg/h = {r['D_kg'] / 1000:.3f} t/h"
                 f"   [喷射器总用汽，凝水留在料液里]")
        L.append(f"  → 闪蒸进料量 M    = G + D = {r['M_kg']:.0f} kg/h = {r['M_kg'] / 1000:.3f} t/h")
        L.append(f"  干物浓度 X        = {r['X']:.2f} wt%（闪蒸前）")
        L.append(f"  干物量            = {r['solid_t']:.3f} t/h   [闪蒸前后不变]")
        L.append(f"  物料比热 C        = {r['C']:.4f} kJ/(kg·K)")
        L.append("")
        L.append("【二、闪蒸条件】")
        L.append(f"  进闪蒸温度 t₁     = {r['t1']:.2f} °C")
        L.append(f"  出闪蒸温度 t₂     = {r['t2']:.2f} °C")
        L.append(f"  闪蒸温差 ΔT       = {r['dT']:.2f} °C")
        L.append(f"  闪蒸压力 p        = {r['p_abs']:.5f} MPa(a)"
                 f"　[该压力下饱和温度 {r['t_sat_p']:.2f} °C]")
        L.append("")
        L.append("【三、释放功率（表格口径）】")
        L.append("      Q = (物料量 + 蒸汽用量)·(t₁ − t₂)·C·1000 / 3600")
        L.append(f"        = ({r['G_t']:.3f}×1000 + {r['D_kg']:.1f})×({r['t1']:.2f}−{r['t2']:.2f})"
                 f"×{r['C']:.4f}·1000/3600")
        L.append(f"        = {r['M_kg']:.0f}×{r['dT']:.2f}×{r['C']:.4f}/3600"
                 f" = {r['Q_kW']:.2f} kW = {r['Q_kjh']:.4g} kJ/h")
        L.append("")
        L.append("【四、闪蒸汽量（本计算器核心）】★")
        L.append("      严格口径：D_f = M·C·ΔT / ( h_g(t₂) − C·t₂ )")
        L.append(f"  t₂ 下饱和汽总焓   = {r['h_g']:.2f} kJ/kg   [{r['hg_src']}]")
        L.append(f"  t₂ 下饱和水焓     = {r['h_f']:.2f} kJ/kg"
                 f"　（潜热 r(t₂) = {r['r_at_t2']:.2f}）")
        L.append(f"  料液中水的显热    = C·t₂ = {r['C']:.4f}×{r['t2']:.2f}"
                 f" = {r['c_t2']:.2f} kJ/kg")
        L.append(f"  → 闪蒸焓差        = h_g(t₂) − C·t₂ = {r['denom']:.2f} kJ/kg")
        L.append(f"  → 闪蒸汽量 D_f    = {r['Q_kjh']:.4g} / {r['denom']:.2f}"
                 f" = {r['D_f']:.1f} kg/h = {r['D_f'] / 1000:.4f} t/h")
        L.append(f"  单位闪蒸汽量      = {r['unit_flash']:.2f} kg 汽/t 进料"
                 f"（{r['D_f'] / r['M_kg'] * 100:.2f} % 的进料被汽化）")
        L.append("")
        L.append("【五、表格口径对照】")
        L.append("      表格式：D_f′ = M·C·ΔT / ( r₀ − C·t₂ )")
        L.append(f"  r₀                = {r['r0']:.2f} kJ/kg   [{r['r0_src']}]")
        L.append(f"  表格焓差          = r₀ − C·t₂ = {r['denom_tab']:.2f} kJ/kg")
        L.append(f"  → 表格口径汽量    = {r['D_f_tab']:.1f} kg/h"
                 f"（与严格口径差 {r['d_tab_pct']:+.2f} %）")
        L.append(f"  → 验算行（t/h 口径）= {r['check_tab']:.4f} t/h"
                 f"　[= 闪蒸汽量 ÷ 1000，同一结果，仅单位不同]")
        if r.get('r0_in') is None:
            L.append("  说明：表格「汽化焓」列留空 → 按 t₂ 下总焓自动取，两条口径重合；")
            L.append(f"        若填表格里的汽化潜热（如 {R0_TAB_DEFAULT:g}），本器会给出偏高的对照值。")
        elif abs(r['d_tab_pct']) > 1.0:
            L.append(f"  ⚠ r₀ 与 t₂ 下总焓差 {(r['h_g'] - r['r0']) / r['r0'] * 100:+.1f} %："
                     f"表格分母用的是**汽化潜热**，闪蒸掉的水是在 t₂ 下汽化的，"
                     f"焓差应取**总焓 h_g**（含水的显热 h_f）——否则汽量偏高。"
                     f"{'（r₀ 与 t₂ 下的汽化潜热基本一致，确认填的是潜热）' if r['r0_is_latent'] else ''}")
            L.append("  → 本器按严格口径给结果，表格口径仅作对照；建议把表格该列改为总焓。")
        L.append("")
        L.append("【六、闪蒸后料液（失水浓缩）】")
        L.append(f"  闪蒸后料量 G′     = M − D_f = {r['G_after_kg']:.0f} kg/h"
                 f" = {r['G_after_t']:.3f} t/h")
        L.append(f"  闪蒸后浓度 X′     = 干物量/G′ = {r['X_after']:.2f} wt%"
                 f"（闪蒸前 {r['X']:.2f}%，提高 {r['X_after'] - r['X']:+.2f} 个百分点，"
                 f"为原来的 {r['conc_ratio'] * 100:.1f}%）")
        L.append(f"  闪蒸后比热 C′     = {r['C_after']:.3f} kJ/(kg·K)   [供下游用]")
        L.append("")
        L.append("【七、闪蒸二次蒸汽（可回收利用）】")
        L.append(f"  二次蒸汽比容      = {r['v_g']:.4f} m³/kg   [t₂ 下饱和汽]")
        L.append(f"  体积流量          = {r['v_flash']:.0f} m³/h")
        if r['dn']:
            L.append(f"  → 参考管径        = DN{r['dn']}"
                     f"（计算内径 {r['d_calc']:.1f} mm，流速 {r['u_act']:.1f} m/s，"
                     f"按 {U_STEAM_FLASH:g} m/s 估）")
        if r["warn"]:
            L.append("")
            L.append("【提示与警告】")
            for i, w in enumerate(r["warn"], 1):
                L.append(f"  {i}) {w}")
        if r.get("chain_published"):
            L.append("")
            L.append("【计算链】本页输出已登记，下游页面可用「取上游值」引用：")
            for k, v in (r.get("chain_values") or {}).items():
                u = (r.get("chain_units") or {}).get(k, "")
                L.append(f"      {k:<8s} = {v:>10.4f} {u}")
            L.append(f"      登记时间：{r.get('chain_time_str', '')}")
        L.append("")
        L.append("=" * 58)
        L.append("  口径说明：闪蒸掉的水是在 **t₂ 温度下汽化**的，分母取该温度下蒸汽的")
        L.append("  **总焓 h_g(t₂)** 减去它在料液中原有的显热 C·t₂；等价于用 t₂ 下的")
        L.append("  汽化潜热再加「水的显热 − 料液显热」的修正项。若把分母当成 0.1 MPa 的")
        L.append("  汽化潜热（2258.77）且只减显热，闪蒸汽量会高估约 20 %。")
        L.append("  物料比热宜取喷射液化器算出的**稀释后**比热（或本厂实测值）；")
        L.append("  本计算器结果仅供参考，实际工程须经专业工程师审核确认。")
        L.append("=" * 58)
        self.result_text.setPlainText("\n".join(L))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"错误：{msg}")
        self._last_result = {}

    # ═══════════════════════ 默认值 / 清空 ═══════════════════════
    def setup_default_values(self):
        self.feed_input.setText("20")
        self.steam_input.setText("0")
        self.conc_input.setText("30")
        self.cp_input.setText("3.39")
        self.tin_input.setText("105")
        self.tout_input.setText("100")
        self.p_input.setText("0.101325")
        self.r0_input.setText("")
        self.hg_input.setText("")

    def clear_inputs(self):
        """恢复出厂默认值（可直接重算）；同时解除上游引用"""
        self.setup_default_values()
        self._chain_ref = {}
        for attr in self._MARK_ROWS:
            self._set_row_mark(attr, "")
        self.chain_combo.blockSignals(True)
        self.chain_combo.setCurrentIndex(0)
        self.chain_combo.blockSignals(False)
        self.chain_status.setText("")
        self.result_text.clear()
        self._last_result = {}
        self._update_feed_total_label()
        self._update_svg_diagram()

    # ═══════════════════════ 历史 ═══════════════════════
    def _get_history_data(self):
        r = self._last_result
        if not r:
            return {"inputs": {}, "outputs": {}}
        inputs = {
            "物料量_t_h": r.get("G_t", 0),
            "蒸汽用量_kg_h": r.get("D_kg", 0),
            "闪蒸进料量_t_h": round(r.get("M_kg", 0) / 1000.0, 4),
            "干物浓度_wt%": r.get("X", 0),
            "物料比热_kJ_kgK": r.get("C", 0),
            "进闪蒸温度_C": r.get("t1", 0),
            "出闪蒸温度_C": r.get("t2", 0),
            "闪蒸压力_MPa_绝压": r.get("p_abs", 0),
            "数据来源": r.get("chain_src", "") or "手填",
        }
        outputs = {
            "释放功率_kW": round(r.get("Q_kW", 0), 2),
            "闪蒸汽量_kg_h": round(r.get("D_f", 0), 1),
            "闪蒸汽量_t_h": round(r.get("D_f", 0) / 1000.0, 4),
            "闪蒸焓差_kJ_kg": round(r.get("denom", 0), 2),
            "闪蒸后料量_t_h": round(r.get("G_after_t", 0), 3),
            "闪蒸后浓度_wt%": round(r.get("X_after", 0), 2),
            "二次蒸汽体积_m3_h": round(r.get("v_flash", 0), 1),
            "表格口径汽量_kg_h": round(r.get("D_f_tab", 0), 1),
        }
        return {"inputs": inputs, "outputs": outputs}

    # ═══════════════════════ 工程信息 / 报告 ═══════════════════════
    def get_project_info(self):
        """获取工程信息（dict，标准键）"""
        try:
            saved = {}
            if self.data_manager:
                saved = self.data_manager.get_project_info() or {}
        except Exception:                                        # noqa: BLE001
            saved = {}
        return {
            "company_name": saved.get("company_name", ""),
            "project_number": saved.get("project_number", ""),
            "project_name": saved.get("project_name", ""),
            "subproject_name": saved.get("subproject_name", ""),
            "calculation_type": "闪蒸（料液减压闪蒸）计算",
        }

    def generate_report(self):
        """生成计算书文本（str；无结果返回 None）"""
        try:
            body = self.result_text.toPlainText()
            if not body or "闪蒸" not in body:
                return None
            info = self.get_project_info()
            head = "\n".join([
                "═" * 58,
                "        闪蒸（料液减压闪蒸）计算书",
                "═" * 58,
            ])
            foot = "\n".join([
                "═" * 58,
                " 工程信息",
                "═" * 58,
                "",
                f"  公司名称: {info.get('company_name', '')}",
                f"  工程编号: {info.get('project_number', '')}",
                f"  工程名称: {info.get('project_name', '')}",
                f"  子项名称: {info.get('subproject_name', '')}",
                f"  计算类型: {info.get('calculation_type', '')}",
                f"  计算日期: {datetime.now().strftime('%Y-%m-%d')}",
                "",
                "═" * 58,
                " 计算公式与依据",
                "═" * 58,
                "",
                "  1. 闪蒸进料量（设计表格口径）",
                "     M = 物料量 G + 蒸汽用量 D",
                "     喷射用蒸汽的凝水留在料液里，故喷射器出口料液 = 原始浆料 + 用汽量；",
                "     两列单位常不一致（t/h 与 kg/h），相加前统一折成 kg/h。",
                "  2. 释放功率（料液降温放出的热）",
                "     Q = M·(t₁ − t₂)·C / 3600                    kW",
                "     C = 物料比热（取喷射器算出的稀释后比热或本厂实测值）",
                "  3. 闪蒸汽量（绝热闪蒸热量衡算，以 0 °C 液态水为焓基准）",
                "     M·C·(t₁ − t₂) = D_f·[ h_g(t₂) − C·t₂ ]",
                "     ⇒ D_f = M·C·(t₁ − t₂) / ( h_g(t₂) − C·t₂ )   kg/h",
                "     h_g(t₂) = t₂ 下饱和蒸汽总焓（IAPWS-IF97；0.1 MPa/100 °C ≈ 2676 kJ/kg）",
                "     C·t₂    = 闪蒸掉的水在料液中原有的显热",
                "     ⚠ 分母若误取 0.1 MPa 的**汽化潜热**（2258.77，仅减去显热），",
                "       闪蒸汽量会高估约 20 %；本器按 h_g 严格计算，表格口径并列对照。",
                "  4. 验算行（设计表格）",
                "     与闪蒸汽用量同一个分子分母，×1000/3600 约掉 → 同一结果的 t/h 口径，",
                "     用于单位互校，不是独立公式。",
                "  5. 闪蒸后料液",
                "     G′ = M − D_f（闪蒸汽带走一部分水）；X′ = G·X / G′（干物量不变 → 浓度升）",
                "  6. 二次蒸汽：V = D_f · v_g(t₂)（m³/h）；管径按低压饱和汽 25 m/s 估",
                "  7. 硬约束：t₁ ＞ t₂；t₂ 不应高于该压力下的饱和温度",
                "     （常压闪蒸 0.101325 MPa → 出料温度上限 ≈ 100 °C，更低须抽真空）",
                "",
                "═" * 58,
                " 数据来源与假设",
                "═" * 58,
                "",
                "  1. 饱和蒸汽总焓/饱和水焓/饱和温度取自 IAPWS-IF97（项目自带 steam_iapws）；",
                "  2. 绝热闪蒸热量衡算式为化工原理与淀粉糖行业设计资料通用式，",
                "     与设计表格「汽化焓 − t出·C」写法同源，差别仅在分母取潜热还是总焓；",
                "  3. 与喷射液化器通过项目内「计算链」传递进料数据（物料量/蒸汽用量/",
                "     物料比热/干物浓度/出口温度），取值后可手工修改；",
                "  4. 本计算器未计闪蒸罐的热损、不凝气与雾沫夹带，结果仅供参考，",
                "     实际工程须经专业工程师审核确认。",
                "",
                "---",
                "生成于 ChemCal 工程计算模块",
            ])
            return f"{head}\n\n{body}\n\n{foot}"
        except Exception as e:                                   # noqa: BLE001
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        ReportExporter.export_docx(self, "闪蒸降温浓缩")

    def download_pdf_report(self):
        ReportExporter.export_pdf(self, "闪蒸降温浓缩")

    # ═══════════════════════ SVG 示意图 ═══════════════════════
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        return svg_text(x, y, text, size, color, bold, center)

    def _update_svg_diagram(self):
        """闪蒸罐流程示意图（喷射液化液 → 闪蒸罐 → 二次蒸汽 / 闪蒸后料液）"""
        w, h = 380, 250
        try:
            t1 = float(self.tin_input.text())
            t2 = float(self.tout_input.text())
        except (TypeError, ValueError):
            t1, t2 = 105.0, 100.0
        try:
            p_show = float(self.p_input.text())
        except (TypeError, ValueError):
            p_show = 0.101325

        p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
             f'width="{w}" height="{h}">',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']

        # 进料（左）
        p.append('<rect x="26" y="92" width="74" height="48" fill="#dbe7f5" '
                 'stroke="#4a6fa5" stroke-width="1.5" rx="4"/>')
        p.append(self._text(63, 110, "喷射液化液", size=8, color="#2c3e50", bold=True))
        p.append(self._text(63, 126, f"{t1:.0f} °C", size=9, color="#2c3e50", bold=True))

        # 闪蒸罐（中，立式带液位）
        x0, y0, tw, th = 150, 76, 96, 108
        p.append(f'<rect x="{x0}" y="{y0}" width="{tw}" height="{th}" fill="#eaf3fb" '
                 f'stroke="#2c6fa5" stroke-width="1.8" rx="6"/>')
        p.append(f'<rect x="{x0 + 4}" y="{y0 + th * 0.55:.0f}" width="{tw - 8}" '
                 f'height="{th * 0.45 - 4:.0f}" fill="#bcd8ef" opacity="0.85"/>')
        p.append(self._text(x0 + tw / 2, y0 + 26, "闪蒸罐", size=10,
                            color="#1b4f72", bold=True))
        p.append(self._text(x0 + tw / 2, y0 + 44, f"p = {p_show:.3f} MPa", size=8,
                            color="#1b4f72"))
        p.append(self._text(x0 + tw / 2, y0 + th - 16, f"{t2:.0f} °C", size=9,
                            color="#1b4f72", bold=True))

        # 进料箭头
        p.append(f'<line x1="100" y1="116" x2="{x0 - 3}" y2="116" '
                 f'stroke="#4a6fa5" stroke-width="2.2"/>')

        # 二次蒸汽（右上）
        p.append(f'<line x1="{x0 + tw / 2}" y1="{y0 - 3}" x2="{x0 + tw / 2}" y2="42" '
                 f'stroke="#e67e22" stroke-width="2.5"/>')
        p.append(f'<line x1="{x0 + tw / 2}" y1="42" x2="{w - 26}" y2="42" '
                 f'stroke="#e67e22" stroke-width="2.5"/>')
        p.append(self._text(x0 + tw / 2 + 6, 34, "闪蒸汽（二次蒸汽）", size=8,
                            color="#a06010", bold=True, center=False))
        p.append(self._text(w - 28, 58, "去回收/利用", size=8, color="#a06010",
                            center=False))

        # 出料（下 → 右）
        p.append(f'<line x1="{x0 + tw / 2}" y1="{y0 + th + 3}" x2="{x0 + tw / 2}" y2="204" '
                 f'stroke="#2980b9" stroke-width="2.5"/>')
        p.append(f'<line x1="{x0 + tw / 2}" y1="204" x2="{w - 26}" y2="204" '
                 f'stroke="#2980b9" stroke-width="2.5"/>')
        p.append(self._text(w - 28, 220, "闪蒸后料液", size=8, color="#2980b9",
                            bold=True, center=False))

        # 底部结果摘要
        r = self._last_result
        if r:
            p.append(self._text(w / 2, h - 40,
                                f"释放功率 {r['Q_kW']:.1f} kW　"
                                f"闪蒸汽量 {r['D_f']:.0f} kg/h",
                                size=9, color="#1d6f42", bold=True))
            p.append(self._text(w / 2, h - 22,
                                f"料液 {r['G_t']:.2f} → {r['G_after_t']:.2f} t/h"
                                f"　浓度 {r['X']:.1f} → {r['X_after']:.1f} wt%",
                                size=9, color="#333", bold=True))
        else:
            p.append(self._text(w / 2, h - 30, "点击「计 算」查看结果",
                                size=9, color="#888"))
        p.append("</svg>")
        self.svg_widget.load("".join(p).encode("utf-8"))


# 为动态导入提供简洁别名
flash_evaporation_calculator = FlashEvaporationCalculator
