"""
闪蒸罐计算器 —— 闪蒸罐（汽液分离罐）筒体尺寸：截面积 / 直径 / 高度 / 体积

适用：料液经喷射液化（或蒸发、结晶前）减压闪蒸后，二次蒸汽必须与料液分离，
      闪蒸罐就是这台**汽液分离设备**。本页按**二次蒸汽在罐内的允许上升速度**
      确定罐内径，再按长径比定高、算筒体容积。

═══════════════ 1. 本页算的六步 ═══════════════
    闪蒸罐的尺寸由**汽相**控制（不是由液相停留时间控制，这一点与下游层流罐不同）：

        ① 闪蒸汽质量流量   m = D_f(t/h) × 1000 / 3600                 [kg/s]
        ② 罐内有效截面积   A = m / ρ_g / u                            [m²]
        ③ 理论内径         D₀ = √(4A / π)                             [m]
        ④ 设计内径         D  = D₀ × 保险系数 k，再向上圆整到常用直径系列
        ⑤ 罐高             H  = D × 长径比 (H/D)                      [m]
        ⑥ 筒体容积         V  = π/4 · D² · H                          [m³]

    与设计表格逐项对照（表格里那几个格子就是这么来的）：
        「闪蒸汽流量」   = 闪蒸汽用量(t/h) × 1000 / 3600      → m
        「闪蒸罐内侧截面积」= 闪蒸汽流量 ÷ 闪蒸汽密度 ÷ 蒸汽流速 → A
        「闪蒸罐直径」   = (4 × 截面积 / π)^0.5              → D₀
        「闪蒸汽密度」   = 1 ÷ 闪蒸蒸汽回收页的密度值（= 1 ÷ 蒸汽比容）
    ⚠ 那一格「闪蒸汽用量」是 **t/h 口径**：只有 t/h 乘 1000 再除 3600 才是 kg/s。
      若按 kg/h 填进去，结果会差 1000 倍（直径差 √1000 ≈ 31.6 倍）。本页按 t/h
      输入，结果区同时回显 t/h / kg/h / kg/s 三个口径，并对异常直径给出提示。

═══════════════ 2. 三个手填参数怎么取 ═══════════════
    · 蒸汽流速 u（罐内二次蒸汽的允许上升速度）
        常用 **0.5~1.5 m/s**。取大了会把液滴夹带进二次蒸汽（雾沫夹带、跑料、
        后工段带料、回收换热器结垢）；取小了罐径偏大、造价与占地都上去了。
    · 保险系数 k
        设计裕量，常用 **1.1~1.2**。直径放大 k 倍 → 截面积放大 k² 倍 →
        实际气速降到约 1/k²（这就是"保险"的物理含义）。
    · 长径比 H/D
        闪蒸罐常用 **1.5~3**。太矮则汽液分离空间不足、易夹带；太高则浪费材料。

═══════════════ 3. 单位换算与量纲核对 ═══════════════
        m [kg/s] = D_f [t/h] × 1000 [kg/t] ÷ 3600 [s/h]
        A [m²]   = m [kg/s] ÷ ρ_g [kg/m³] ÷ u [m/s]
        D₀ [m]   = √(4A/π)
    · 密度 ρ_g 可手填（表格口径，取回收页「密度」列的倒数），留空则按罐内压力
      用 IAPWS-IF97 自动查饱和汽密度；两者相差 > 1 % 时提示核对查表行。
    · 圆整会**再放大**直径，所以实际气速一定低于手填的 u——本页把实际气速
      一并算出来校核（过低说明白选了大罐，可下调保险系数或选小一档）。

═══════════════ 4. 罐高与停留时间（本页不算停留时间）═══════════════
    · 本页**不核算停留时间**——闪蒸罐只做汽液分离，料液在罐内的停留时间由液位
      与出料泵流量决定，不是罐体尺寸的控制因素。
    · 液化（或反应）所需的**维持时间**是下游**层流罐**的职责，典型顺序：
          淀粉乳 → 喷射液化器（升温到 105~110 °C）→ 闪蒸降温 →
          **层流罐**（维持液化时间）→ 后续糖化 / 过滤
      所以这页只出"筒体尺寸"，罐容不是按停留时间倒推的。
    · 体积口径 = **筒体**（π/4·D²·H），**不含**上下封头；要按含封头的总容积
      或按液位算有效容积，另计。

═══════════════ 5. 计算链联动 ═══════════════
    本页可取上游结果，不必手抄：
        闪蒸汽量 ← 闪蒸降温浓缩 / 闪蒸蒸汽回收「闪蒸汽量」 (kg/h → 自动 ÷1000 得 t/h)
        闪蒸压力 ← 闪蒸降温浓缩「闪蒸压力」               (MPa → 自动换 kPa)
        蒸汽密度 ← 闪蒸蒸汽回收「蒸汽密度」               (kg/m³，= 该页比容的倒数)
    点「取上游值」默认**一次取全整链**（按链序，同名键上游优先），也可在下拉里
    限定单个来源；取值后仍可手工修改；上游重算后提示「数据可能已过期」。

═══════════════ 6. 数据来源与口径 ═══════════════
    · 饱和蒸汽密度 / 比容 / 饱和温度：IAPWS-IF97（steam_iapws），与项目资料库
      「饱和水蒸气表（按压力排列，SI 单位）」同源；
    · 常用直径系列取 300~4000 mm 每 100/200 mm 一档的工程常用值；
    · 公式为化工原理通用式（汽液分离器按允许气速定径），未计除沫器、
      进出口管嘴、液位波动与雾沫夹带的定量影响，结果仅供参考，
      实际工程须经专业工程师审核确认。
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
# 计算链：与喷射液化器 / 闪蒸降温浓缩 / 闪蒸蒸汽回收共享「上游输出」
from chain_context import ChainContext

# IAPWS-IF97 完整物性（动态导入，写法与喷射液化器/闪蒸页一致）
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


#: 工程常用直径系列（m）—— 按此向上圆整（300~4000 mm，逐档递增）
STD_DIAMETERS = [
    0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00,
    1.20, 1.40, 1.60, 1.80, 2.00, 2.20, 2.40, 2.60, 2.80, 3.00,
    3.20, 3.40, 3.60, 3.80, 4.00,
]

#: 二次蒸汽允许上升速度的常用区间（m/s）—— 区间外给提示
U_LO, U_HI = 0.5, 1.5

#: 长径比常用区间
LD_LO, LD_HI = 1.5, 3.0

#: 保险系数常用区间
K_LO, K_HI = 1.1, 1.2


def round_up_diameter(d):
    """把理论/放大后直径向上圆整到工程常用系列（超出系列按 0.2 m 档向上取）"""
    for s in STD_DIAMETERS:
        if s >= d - 1e-9:
            return s
    return math.ceil(d / 0.2) * 0.2


class FlashTankCalculator(CalculatorBase):
    """闪蒸罐计算器：按二次蒸汽允许上升速度定罐径、罐高与筒体容积"""

    #: 计算链标识（供更下游的页面取用本页输出）
    CHAIN_MODULE = "flash_tank_calculator"
    CHAIN_PAGE = "闪蒸罐计算"

    #: 取上游值时的字段映射：上游输出键 → (本页输入控件属性名, 换算系数, 单位)
    CHAIN_MAP = [
        ("闪蒸汽量", "df_input", 0.001, "t/h"),      # 上游 kg/h → 本页 t/h
        ("闪蒸压力", "p_input", 1000.0, "kPa"),       # 上游 MPa → 本页 kPa
        ("蒸汽密度", "rho_input", 1.0, "kg/m³"),      # 回收页按比容反算的密度
    ]

    #: 取上游值时打标记的行 key ↔ 控件属性名
    _MARK_ROWS = {
        "df_input": "df", "p_input": "p", "rho_input": "rho",
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
        self._chain_refs = []                 # 本次引用的上游标记（**列表**：可多个来源）
        self._chain_detail = ""               # 本次取用的字段明细（供状态行显示）
        self._chain_status_fallback = False   # 「无可用传递值」提示已直接给出
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
            "闪蒸罐（汽液分离罐）筒体尺寸：按二次蒸汽在罐内的允许上升速度定内径 → "
            "保险系数放大并圆整 → 按长径比定高 → 算筒体容积。点「取上游值」一次取全整链"
            "（闪蒸汽量 / 闪蒸压力 ← 闪蒸降温浓缩，蒸汽密度 ← 闪蒸蒸汽回收）。"
            "本页不核算停留时间——闪蒸罐只做汽液分离，维持时间在层流罐。")
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

        # ── 二次蒸汽（可取上游）──
        g1 = CalculatorBase.make_group_box("二次蒸汽（可取上游）")
        g1g = new_grid(g1)
        r = 0

        self.df_input = QLineEdit("0.145")
        self.df_input.setValidator(QDoubleValidator(0.0001, 100000.0, 6))
        r = add_row(g1g, "df", "闪蒸汽量 D_f (t/h):", self.df_input,
                    "取闪蒸页「闪蒸汽量」（kg/h 自动 ÷1000）；表格那一格即 t/h 口径", r)

        self.p_input = QLineEdit("101.325")
        self.p_input.setValidator(QDoubleValidator(1.0, 1600.0, 3))
        r = add_row(g1g, "p", "闪蒸罐压力 p (kPa 绝压):", self.p_input,
                    "取闪蒸页「闪蒸压力」（自动 MPa→kPa）；用于自动取蒸汽密度", r)

        self.rho_input = QLineEdit("")
        self.rho_input.setValidator(QDoubleValidator(0.001, 100.0, 6))
        self.rho_input.setPlaceholderText("留空 = 按 p 自动")
        r = add_row(g1g, "rho", "闪蒸汽密度 ρ_g (kg/m³):", self.rho_input,
                    "= 1 ÷ 回收页密度（比容）；常压饱和汽 ≈ 0.5977", r)

        ll.addWidget(g1)

        # ── 设计参数 ──
        g2 = CalculatorBase.make_group_box("设计参数（手填）")
        g2g = new_grid(g2)
        r = 0

        self.u_input = QLineEdit("1.0")
        self.u_input.setValidator(QDoubleValidator(0.05, 20.0, 4))
        r = add_row(g2g, "u", "蒸汽流速 u (m/s):", self.u_input,
                    "允许上升速度，常用 0.5~1.5；过大易雾沫夹带", r)

        self.k_input = QLineEdit("1.2")
        self.k_input.setValidator(QDoubleValidator(1.0, 3.0, 4))
        r = add_row(g2g, "k", "保险系数 k (-):", self.k_input,
                    "常用 1.1~1.2；直径放大 k 倍，气速约降到 1/k²", r)

        self.ld_input = QLineEdit("2.0")
        self.ld_input.setValidator(QDoubleValidator(0.5, 8.0, 4))
        r = add_row(g2g, "ld", "长径比 H/D (-):", self.ld_input,
                    "罐高 = 内径 × 长径比；闪蒸罐常用 1.5~3", r)

        self.round_mode = QComboBox()
        self.round_mode.addItems(["向上圆整到常用直径系列",
                                  "不圆整（保留计算值）"])
        self.round_mode.setStyleSheet(COMBOBOX_STYLE)
        g2g.addWidget(lbl("直径取整:"), r, 0)
        g2g.addWidget(self.round_mode, r, 1)
        g2g.addWidget(hint("常用系列 300~4000 mm（模拟取标准罐径）"), r, 2)
        self._rows.setdefault("round", []).extend([None, self.round_mode, None])
        r += 1

        ll.addWidget(g2)
        ll.addStretch()
        scroll.setWidget(lw)

        # ── 右栏：结果 ──
        rw = QWidget()
        rw.setMinimumWidth(300)
        rl = QVBoxLayout(rw)

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
        self._update_svg_diagram()

    # ═══════════════════════ 计算链 ═══════════════════════
    def _reload_chain_sources(self):
        """刷新可用上游来源下拉（保留当前选中项）"""
        self.chain_combo.blockSignals(True)
        self.chain_combo.clear()
        self.chain_combo.addItem("（自动：取全部上游，整链一键取全）")
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
        """取上游值：默认取**全部上游**（整链一键取全），也可下拉限定单个来源

        本页的输入分属两段上游 —— 闪蒸汽量 / 闪蒸压力来自闪蒸降温浓缩（或回收页的
        闪蒸汽量），蒸汽密度来自闪蒸蒸汽回收。所以不选来源直接点按钮时，按工艺链
        顺序把线上所有上游一次填全（同名键先到先得，上游优先）；只想重取某一段时
        再在下拉里选中它。
        """
        idx = self.chain_combo.currentIndex()
        whole_chain = idx <= 0
        if whole_chain:
            entries = ChainContext.ordered_sources(exclude=(self.CHAIN_MODULE,))
        else:
            if idx - 1 >= len(self._chain_sources):
                self.chain_status.setText("未选择上游来源（可直接手填各项）。")
                return
            entries = [self._chain_sources[idx - 1]]
        if not entries:
            self.chain_status.setText(
                "当前没有可用上游 —— 请先到上游页（喷射液化器 / 闪蒸降温浓缩 / "
                "闪蒸蒸汽回收）点「计算」。")
            return

        keys = [k for k, _attr, _f, _u in self.CHAIN_MAP]
        merged = ChainContext.merge_values(entries, keys)      # 先到先得：上游优先
        applied, used = {}, []
        for key, attr, factor, unit in self.CHAIN_MAP:
            hit = merged.get(key)
            w = getattr(self, attr, None)
            if not hit or w is None:
                continue
            try:
                v = float(hit[0]) * factor
            except (TypeError, ValueError):
                continue
            w.setText(f"{v:.10g}")
            self._set_row_mark(attr, "←上游")
            src = hit[1]
            applied[key] = src["page"]
            if all(u["module"] != src["module"] for u in used):
                used.append(src)

        self._chain_refs = ChainContext.make_refs([e["module"] for e in used])
        self._chain_detail = "、".join(f"{k}←{p}" for k, p in applied.items())
        if not applied:
            self._chain_refs = ChainContext.make_refs([e["module"] for e in entries])
            self._chain_status_fallback = True
            self.chain_status.setText(
                f"{ChainContext.describe_refs(self._chain_refs)} 没有可用的传递值。")
            return
        self._chain_status_fallback = False
        self._refresh_chain_status()

    def _refresh_chain_status(self, *_a):
        """渲染状态行：已取来源 + 字段明细 + 过期提示（覆盖**全部**来源）"""
        if not self._chain_refs:
            return
        if getattr(self, "_chain_status_fallback", False):
            return                          # 「无可用传递值」提示由取数函数直接给出
        try:
            stale = ChainContext.stale_refs(self._chain_refs)
            src = ChainContext.describe_refs(self._chain_refs)
            detail = f"　→　{self._chain_detail}" if self._chain_detail else ""
            if stale:
                latest = "；".join(
                    f"{ChainContext.describe_ref(r)} 最新 "
                    f"{(ChainContext.get(r.get('module')) or {}).get('time_str', '')}"
                    for r in stale)
                self.chain_status.setText(
                    f"⚠ 数据来源 {src}{detail}，但其中 {latest} 已重算"
                    f"——当前输入可能已过期，建议重新「取上游值」。")
            else:
                self.chain_status.setText(
                    f"已取用：{src}{detail}（最新，未过期）")
        except Exception:                                        # noqa: BLE001
            pass

    def _set_row_mark(self, attr, mark):
        """在对应输入的提示列打/清「←上游」标记"""
        key = self._MARK_ROWS.get(attr)
        if not key:
            return
        rows = self._rows.get(key, ())
        if len(rows) < 3 or rows[2] is None:
            return
        base = self._hint_base.get(key, "")
        rows[2].setText(f"{base}　[{mark}]" if mark else base)

    def _clear_row_mark(self, attr):
        """用户手改输入后撤掉该行的上游标记（引用只是填值，不做绑定）"""
        self._set_row_mark(attr, "")

    def showEvent(self, event):                                  # noqa: N802
        """页面显示时刷新来源列表与过期状态（上游可能刚重算过）"""
        try:
            self._reload_chain_sources()
            self._refresh_chain_status()
        except Exception as e:                                   # noqa: BLE001
            print(f"刷新计算链状态失败: {e}")
        super().showEvent(event)

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
    def _sat_from_abs(p_abs):
        """饱和参数（绝压 MPa）→ dict（IAPWS-IF97）"""
        if _STEAM is None:
            raise ValueError("IAPWS-IF97 模块不可用，无法计算饱和蒸汽物性")
        return _STEAM.saturation_properties(P_MPa=p_abs)

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
            "闪蒸罐直径": r.get("D", 0.0),                 # m
            "闪蒸罐高度": r.get("H", 0.0),                 # m
            "闪蒸罐体积": r.get("V", 0.0),                 # m³
            "罐内截面积": r.get("A_act", 0.0),             # m²
            "蒸汽上升速度": r.get("u_act", 0.0),           # m/s
        }
        units = {"闪蒸罐直径": "m", "闪蒸罐高度": "m", "闪蒸罐体积": "m³",
                 "罐内截面积": "m²", "蒸汽上升速度": "m/s"}
        try:
            entry = ChainContext.publish(
                self.CHAIN_MODULE, self.CHAIN_PAGE, values=vals, units=units,
                note=f"φ{r.get('D', 0) * 1000:.0f}×{r.get('H', 0) * 1000:.0f}")
            r["chain_published"] = bool(entry)
            r["chain_values"] = vals
            r["chain_units"] = units
            r["chain_time_str"] = entry["time_str"] if entry else ""
        except Exception as e:                                   # noqa: BLE001
            print(f"计算链登记失败（不影响计算）: {e}")
            r["chain_published"] = False

    def _compute(self):
        # ── 二次蒸汽 ──
        D_f_t = self._num(self.df_input, "闪蒸汽量")
        p_kpa = self._num(self.p_input, "闪蒸罐压力")
        rho_in = self._num_opt(self.rho_input, "闪蒸汽密度")
        # ── 设计参数 ──
        u = self._num(self.u_input, "蒸汽流速")
        k = self._num(self.k_input, "保险系数")
        ld = self._num(self.ld_input, "长径比")
        do_round = (self.round_mode.currentIndex() == 0)

        # ── 校验 ──
        if D_f_t <= 0:
            raise ValueError("闪蒸汽量必须大于 0")
        if not (1.0 <= p_kpa <= 1600.0):
            raise ValueError(f"闪蒸罐压力 {p_kpa:.1f} kPa 超出饱和蒸汽表常用范围"
                             f"（1~1600 kPa）")
        if not (0.05 <= u <= 20.0):
            raise ValueError("蒸汽流速应在 0.05~20 m/s 之间（常用 0.5~1.5）")
        if not (1.0 <= k <= 3.0):
            raise ValueError("保险系数应不小于 1.0（常用 1.1~1.2）")
        if not (0.5 <= ld <= 8.0):
            raise ValueError("长径比 H/D 应在 0.5~8 之间（闪蒸罐常用 1.5~3）")

        p_abs = p_kpa / 1000.0                            # MPa 绝压
        sat = self._sat_from_abs(p_abs)
        t_sat = sat["T_C"]
        v_g_auto = sat["v_g"]
        rho_auto = 1.0 / v_g_auto if v_g_auto > 0 else 0.0

        warn = []
        #: 密度：手填优先（表格口径），留空按压力自动（IAPWS）
        if rho_in is not None:
            if rho_in <= 0:
                raise ValueError("闪蒸汽密度必须大于 0（留空则按压力自动查表）")
            rho_g = rho_in
            rho_src = "表格填值（= 1 ÷ 回收页密度）"
            if rho_auto > 0 and abs(rho_g - rho_auto) > 0.01 * rho_auto:
                warn.append(
                    f"你填的闪蒸汽密度 {rho_g:.6g} kg/m³ 与按 p = {p_kpa:.1f} kPa 自动"
                    f"查算的 {rho_auto:.6g} kg/m³ 相差 "
                    f"{abs(rho_g - rho_auto) / rho_auto * 100:.2f} %"
                    f"——请核对是否取反了（回收页那一列若是**比容** m³/kg，"
                    f"密度应是它的倒数）")
        else:
            rho_g = rho_auto
            rho_src = "自动（IAPWS，p 下的饱和汽）"
        if rho_g <= 0:
            raise ValueError("闪蒸汽密度必须大于 0")

        # ── ① 闪蒸汽质量流量：t/h × 1000 / 3600 = kg/s ──
        m_kgh = D_f_t * 1000.0                            # kg/h
        m_dot = m_kgh / 3600.0                            # kg/s

        # ── ② 罐内有效截面积 A = m / ρ / u ──
        A_calc = m_dot / rho_g / u                        # m²

        # ── ③ 理论内径 D₀ = √(4A/π) ──
        D0 = math.sqrt(4.0 * A_calc / math.pi)            # m

        # ── ④ 设计内径 = D₀ × k（可选向上圆整）──
        D_need = D0 * k
        D = round_up_diameter(D_need) if do_round else D_need
        A_act = math.pi / 4.0 * D * D
        u_act = m_dot / (rho_g * A_act) if A_act > 0 else 0.0
        d_grow_pct = (D - D_need) / D_need * 100.0 if D_need > 0 else 0.0
        k_total = D / D0 if D0 > 0 else 0.0

        # ── ⑤ 罐高 H = D × 长径比 ──
        H = D * ld

        # ── ⑥ 筒体容积 V = π/4·D²·H ──
        V = A_act * H

        # ── 提示与校核 ──
        if D_need < 0.15:
            warn.append(
                f"保险放大后内径只有 {D_need * 1000:.1f} mm——过小（连最小常用规格"
                f" φ300 都不到），请核对闪蒸汽量的**单位**：本页按 **t/h** 输入，"
                f"若你是从 kg/h 那栏抄来的，请先 ÷1000")
        if u < U_LO:
            warn.append(
                f"蒸汽流速 {u:.3f} m/s 低于常用下限 {U_LO} m/s——罐径会偏大、"
                f"造价与占地上升，一般取 {U_LO}~{U_HI} m/s")
        elif u > U_HI:
            warn.append(
                f"蒸汽流速 {u:.3f} m/s 高于常用上限 {U_HI} m/s——雾沫夹带风险大"
                f"（料液被带进二次蒸汽、后工段带料/回收换热器结垢），"
                f"一般取 {U_LO}~{U_HI} m/s")
        if k < K_LO or k > K_HI:
            warn.append(f"保险系数 {k:.3f} 超出常用区间 {K_LO}~{K_HI}"
                        f"（直径放大 k 倍 → 截面积放大 k² 倍）")
        if ld < LD_LO or ld > LD_HI:
            warn.append(f"长径比 {ld:.3f} 超出常用区间 {LD_LO}~{LD_HI}"
                        f"——太矮汽液分离空间不足，太高浪费材料")
        if abs(d_grow_pct) > 1e-9 and d_grow_pct > 25.0:
            warn.append(
                f"向上圆整把直径从 {D_need:.4f} m 放大到 {D:.2f} m"
                f"（+{d_grow_pct:.1f} %）——档位跨度较大，若嫌大可直接按 "
                f"{D_need:.3f} m 定制（把「直径取整」改为不圆整）")
        if u > 0 and u_act < 0.5 * u:
            warn.append(
                f"圆整+保险后实际上升速度只有 {u_act:.3f} m/s（手填 {u:.3f} m/s 的 "
                f"{u_act / u * 100:.1f} %，内径共放大 {k_total:.3f} 倍、气速按平方"
                f"反比下降）——这是「保险」的代价，但偏差过半时说明保险系数或"
                f"圆整档位取得过大，可下调 k 或选小一档直径")
        if D > 4.0:
            warn.append(
                f"设计内径 φ{D * 1000:.0f} mm 超出常用直径系列（≤4000 mm）"
                f"——请核对闪蒸汽量的**单位**（本页按 t/h 输入，若抄的是 kg/h 需先"
                f"÷1000）以及蒸汽流速取值是否合理")

        return {
            # 输入回显
            "D_f_t": D_f_t, "p_kpa": p_kpa, "rho_in": rho_in,
            "u": u, "k": k, "ld": ld, "do_round": do_round,
            # 饱和态
            "p_abs": p_abs, "t_sat": t_sat,
            "v_g_auto": v_g_auto, "rho_auto": rho_auto,
            # 密度取值
            "rho_g": rho_g, "rho_src": rho_src, "v_g": 1.0 / rho_g,
            # ① 质量流量
            "m_kgh": m_kgh, "m_dot": m_dot,
            # ② 截面积
            "A_calc": A_calc,
            # ③ 理论直径
            "D0": D0,
            # ④ 设计直径
            "D_need": D_need, "D": D, "A_act": A_act,
            "u_act": u_act, "d_grow_pct": d_grow_pct, "k_total": k_total,
            # ⑤⑥ 高度与体积
            "H": H, "V": V,
            # 计算链来源
            "chain_src": ChainContext.describe_refs(self._chain_refs),
            "warn": warn,
        }

    # ═══════════════════════ 结果渲染 ═══════════════════════
    def _render(self, r):
        L = []
        L.append("闪蒸罐计算（汽液分离罐筒体尺寸）")
        L.append("=" * 58)
        if r.get("chain_src"):
            L.append(f"【计算链来源】{r['chain_src']}（各项引用上游结果，可手工修改）")
            L.append("")
        L.append("【一、二次蒸汽（口径核对）】")
        L.append(f"  闪蒸汽量 D_f      = {r['D_f_t']:.6g} t/h"
                 f" = {r['m_kgh']:.1f} kg/h")
        L.append(f"  → 闪蒸汽流量      = {r['D_f_t']:.6g} × 1000 ÷ 3600"
                 f" = {r['m_dot']:.6f} kg/s")
        L.append(f"  闪蒸罐压力 p      = {r['p_kpa']:.3f} kPa 绝压"
                 f"（{r['p_abs']:.6f} MPa，饱和温度 {r['t_sat']:.2f} °C）")
        L.append(f"  闪蒸汽密度 ρ_g    = {r['rho_g']:.6f} kg/m³   [{r['rho_src']}]"
                 + ("" if r['rho_in'] is None else f"（自动值 {r['rho_auto']:.6f}）"))
        L.append(f"  （比容 v_g        = {r['v_g']:.6f} m³/kg）")
        L.append(f"  蒸汽流速 u        = {r['u']:.4f} m/s   [手填，常用 0.5~1.5]")
        L.append("")
        L.append("【二、罐内有效截面积】")
        L.append("      A = m / ρ_g / u")
        L.append(f"  → A               = {r['m_dot']:.6f} ÷ {r['rho_g']:.6f}"
                 f" ÷ {r['u']:.4f} = {r['A_calc']:.6f} m²")
        L.append("")
        L.append("【三、罐内径】★")
        L.append("      D₀ = √(4A/π)")
        L.append(f"  → 理论内径 D₀     = √(4 × {r['A_calc']:.6f} / π)"
                 f" = {r['D0']:.4f} m = {r['D0'] * 1000:.0f} mm")
        L.append(f"  保险系数 k        = {r['k']:.4f}   [手填，常用 1.1~1.2]")
        L.append(f"  → 放大后内径      = {r['D0']:.4f} × {r['k']:.4f}"
                 f" = {r['D_need']:.4f} m")
        if r["do_round"]:
            L.append(f"  → 圆整后设计内径  = **{r['D']:.2f} m"
                     f"（φ{r['D'] * 1000:.0f}）**"
                     + (f"，圆整放大 {r['d_grow_pct']:+.2f} %"
                        if abs(r['d_grow_pct']) > 1e-9 else "，无需圆整"))
        else:
            L.append(f"  → 设计内径（不圆整）= **{r['D']:.4f} m"
                     f"（φ{r['D'] * 1000:.0f}）**")
        L.append(f"  实际截面积 A′     = π/4 × {r['D']:.4f}² = {r['A_act']:.6f} m²")
        L.append(f"  → 实际上升速度 u′ = {r['m_dot']:.6f} ÷ ({r['rho_g']:.6f} ×"
                 f" {r['A_act']:.6f}) = {r['u_act']:.4f} m/s")
        L.append(f"     （内径共放大 {r['k_total']:.3f} 倍（保险×圆整），"
                 f"气速按平方反比降为手填值的 "
                 f"{r['u_act'] / r['u'] * 100:.1f} %）")
        L.append("")
        L.append("【四、罐高与筒体容积】")
        L.append(f"  长径比 H/D        = {r['ld']:.4f}   [手填，常用 1.5~3]")
        L.append("      H = D × (H/D)　　V = π/4·D²·H")
        L.append(f"  → 罐高 H          = {r['D']:.4f} × {r['ld']:.4f}"
                 f" = {r['H']:.4f} m = {r['H'] * 1000:.0f} mm")
        L.append(f"  → 筒体容积 V      = {r['A_act']:.6f} × {r['H']:.4f}"
                 f" = {r['V']:.6f} m³ = {r['V'] * 1000:.2f} L")
        L.append(f"  → 设备规格        = φ{r['D'] * 1000:.0f} × {r['H'] * 1000:.0f} mm"
                 f"（筒体，不含封头）")
        if r["warn"]:
            L.append("")
            L.append("【提示与警告】")
            for i, w in enumerate(r["warn"], 1):
                L.append(f"  {i}) {w}")
        if r.get("chain_published"):
            L.append("")
            L.append("【计算链】本页输出已登记，下游页面可用「取上游值」引用：")
            for k, v in (r.get("chain_values") or {}).items():
                u_ = (r.get("chain_units") or {}).get(k, "")
                L.append(f"      {k:<10s} = {v:>10.4f} {u_}")
            L.append(f"      登记时间：{r.get('chain_time_str', '')}")
        L.append("")
        L.append("=" * 58)
        L.append("  口径说明：闪蒸罐只做**汽液分离**，尺寸由二次蒸汽的允许上升速度")
        L.append("  控制，故本页不核算停留时间；液化所需的维持时间是**层流罐**的职责")
        L.append("  （喷射液化 → 闪蒸降温 → 层流罐维持 → 后续糖化/过滤）。")
        L.append("  体积口径为**筒体** π/4·D²·H，不含上下封头。")
        L.append("  未计除沫器、管嘴、液位波动与雾沫夹带的定量影响，结果仅供参考，")
        L.append("  实际工程须经专业工程师审核确认。")
        L.append("=" * 58)
        self.result_text.setPlainText("\n".join(L))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"错误：{msg}")
        self._last_result = {}

    # ═══════════════════════ 默认值 / 清空 ═══════════════════════
    def setup_default_values(self):
        self.df_input.setText("0.145")
        self.p_input.setText("101.325")
        self.rho_input.setText("")
        self.u_input.setText("1.0")
        self.k_input.setText("1.2")
        self.ld_input.setText("2.0")
        self.round_mode.setCurrentIndex(0)

    def clear_inputs(self):
        """恢复出厂默认值（可直接重算）；同时解除上游引用"""
        self.setup_default_values()
        self._chain_refs = []
        self._chain_detail = ""
        self._chain_status_fallback = False
        for attr in self._MARK_ROWS:
            self._set_row_mark(attr, "")
        self.chain_combo.blockSignals(True)
        self.chain_combo.setCurrentIndex(0)
        self.chain_combo.blockSignals(False)
        self.chain_status.setText("")
        self.result_text.clear()
        self._last_result = {}
        self._update_svg_diagram()

    # ═══════════════════════ 历史 ═══════════════════════
    def _get_history_data(self):
        r = self._last_result
        if not r:
            return {"inputs": {}, "outputs": {}}
        inputs = {
            "闪蒸汽量_t_h": r.get("D_f_t", 0),
            "闪蒸罐压力_kPa": r.get("p_kpa", 0),
            "闪蒸汽密度_kg_m3": round(r.get("rho_g", 0), 6),
            "蒸汽流速_m_s": r.get("u", 0),
            "保险系数": r.get("k", 0),
            "长径比": r.get("ld", 0),
            "直径取整": "向上圆整" if r.get("do_round") else "不圆整",
            "数据来源": r.get("chain_src", "") or "手填",
        }
        outputs = {
            "罐内截面积_m2": round(r.get("A_act", 0), 6),
            "理论内径_m": round(r.get("D0", 0), 4),
            "设计内径_m": round(r.get("D", 0), 4),
            "罐高_m": round(r.get("H", 0), 4),
            "筒体容积_m3": round(r.get("V", 0), 6),
            "实际上升速度_m_s": round(r.get("u_act", 0), 4),
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
            "calculation_type": "闪蒸罐计算",
        }

    def generate_report(self):
        """生成计算书文本（str；无结果返回 None）"""
        try:
            body = self.result_text.toPlainText()
            if not body or "闪蒸罐计算" not in body:
                return None
            info = self.get_project_info()
            head = "\n".join([
                "═" * 58,
                "        闪蒸罐计算书（汽液分离罐筒体尺寸）",
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
                "  1. 闪蒸汽质量流量  m = D_f · 1000 / 3600                kg/s",
                "     （D_f 单位 **t/h**，×1000 换 kg，÷3600 换 s）",
                "  2. 罐内有效截面积  A = m / ( ρ_g · u )                   m²",
                "     ρ_g = 罐压下饱和汽密度（kg/m³）；u = 允许上升速度（m/s）",
                "  3. 理论内径        D₀ = √( 4A / π )                      m",
                "  4. 设计内径        D  = D₀ × k，再向上圆整到常用直径系列",
                "     k = 保险系数（常用 1.1~1.2）；实际截面积 A′ = π/4·D²",
                "     实际上升速度 u′ = m / ( ρ_g · A′ )（小于手填 u，即「保险」的代价）",
                "  5. 罐高            H = D × (H/D)                          m",
                "  6. 筒体容积        V = π/4 · D² · H = A′ · H               m³",
                "     体积口径为筒体，不含上下封头。",
                "",
                "═" * 58,
                " 数据来源与假设",
                "═" * 58,
                "",
                "  1. 饱和蒸汽密度/比容/饱和温度取自 IAPWS-IF97，与项目所附",
                "     「饱和水蒸气表（按压力排列，SI 单位）」同源；密度可手填对照",
                "     （表格口径 = 1 ÷ 闪蒸蒸汽回收页的密度值），差 >1 % 提示核对；",
                "  2. 常用直径系列 300~4000 mm，圆整方向为**向上**（取标准罐径）；",
                "  3. 本页**不核算停留时间**：闪蒸罐只做汽液分离，尺寸由汽相允许",
                "     上升速度控制；液化维持时间为下游**层流罐**的职责；",
                "  4. 未计除沫器、进出管嘴、液位波动与雾沫夹带的定量影响，",
                "     结果仅供参考，实际工程须经专业工程师审核确认。",
                "",
                "---",
                "生成于 ChemCal 工程计算模块",
            ])
            return f"{head}\n\n{body}\n\n{foot}"
        except Exception as e:                                   # noqa: BLE001
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        ReportExporter.export_docx(self, "闪蒸罐计算")

    def download_pdf_report(self):
        ReportExporter.export_pdf(self, "闪蒸罐计算")

    # ═══════════════════════ SVG 示意图 ═══════════════════════
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        return svg_text(x, y, text, size, color, bold, center)

    def _update_svg_diagram(self):
        """流程示意：二级蒸汽出口（上）/ 进料（侧）/ 出料去层流罐（下）"""
        w, h = 380, 250
        rr = self._last_result or {}
        D_show = rr.get("D", 0.4)
        H_show = rr.get("H", 0.8)

        p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
             f'width="{w}" height="{h}">',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']

        # 罐体（立式圆筒 + 上下椭圆封头）
        cx = 150
        rw_ = 54                                   # 半宽
        top, bot = 74, 176                         # 筒体上下端
        cap = 16                                   # 封头高度
        p.append(f'<rect x="{cx - rw_}" y="{top}" width="{2 * rw_}" '
                 f'height="{bot - top}" fill="#eef5fb" stroke="#2c6fa5" '
                 f'stroke-width="1.8"/>')
        p.append(f'<path d="M {cx - rw_} {top} q {rw_} -{cap} {2 * rw_} 0" '
                 f'fill="#eef5fb" stroke="#2c6fa5" stroke-width="1.8"/>')
        p.append(f'<path d="M {cx - rw_} {bot} q {rw_} {cap} {2 * rw_} 0" '
                 f'fill="#eef5fb" stroke="#2c6fa5" stroke-width="1.8"/>')
        # 液位线
        p.append(f'<line x1="{cx - rw_}" y1="{bot - 26}" x2="{cx + rw_}" '
                 f'y2="{bot - 26}" stroke="#2980b9" stroke-width="1.2" '
                 f'stroke-dasharray="4 3"/>')
        p.append(self._text(cx, bot - 18, "液位", size=7, color="#1b4f72"))
        p.append(self._text(cx, (top + bot) / 2 + 4, "闪蒸罐", size=10,
                            color="#1b4f72", bold=True))

        # 蒸汽出口（上，去回收/放空）
        p.append(f'<line x1="{cx}" y1="{top - cap}" x2="{cx}" y2="32" '
                 f'stroke="#e67e22" stroke-width="2.5"/>')
        p.append(f'<path d="M {cx} 32 l -5 10 l 10 0 z" fill="#e67e22"/>')
        p.append(self._text(cx + 8, 30, "二次蒸汽", size=8, color="#a06010",
                            bold=True, center=False))
        p.append(self._text(cx + 8, 44, "去回收/放空", size=7, color="#a06010",
                            center=False))

        # 进料（左上侧）
        p.append(f'<line x1="34" y1="112" x2="{cx - rw_}" y2="112" '
                 f'stroke="#27ae60" stroke-width="2.5"/>')
        p.append(f'<path d="M {cx - rw_} 112 l -10 -5 l 0 10 z" fill="#27ae60"/>')
        p.append(self._text(38, 104, "闪蒸进料", size=8, color="#1d6f42",
                            bold=True, center=False))
        p.append(self._text(38, 128, "105 °C 料液", size=8, color="#1d6f42",
                            center=False))

        # 出料（下，去层流罐）
        p.append(f'<line x1="{cx}" y1="{bot + cap}" x2="{cx}" y2="218" '
                 f'stroke="#c0392b" stroke-width="2.5"/>')
        p.append(f'<path d="M {cx} 218 l -5 -10 l 10 0 z" fill="#c0392b"/>')
        p.append(self._text(cx + 8, 214, "出料 → 层流罐", size=8, color="#c0392b",
                            bold=True, center=False))

        # 尺寸标注
        p.append(f'<line x1="{cx + rw_ + 10}" y1="{top}" x2="{cx + rw_ + 10}" '
                 f'y2="{bot}" stroke="#7f8c8d" stroke-width="1"/>')
        p.append(self._text(cx + rw_ + 40, (top + bot) / 2, f"H={H_show:.2f} m",
                            size=8, color="#555"))
        p.append(self._text(cx + rw_ + 40, (top + bot) / 2 + 14,
                            f"D=φ{D_show * 1000:.0f}", size=8, color="#555"))

        # 底部结果摘要
        if rr:
            p.append(self._text(w / 2, h - 40,
                                f"φ{D_show * 1000:.0f} × {H_show * 1000:.0f} mm　"
                                f"V={rr.get('V', 0):.3f} m³",
                                size=9, color="#1d6f42", bold=True))
            p.append(self._text(w / 2, h - 22,
                                f"截面积 {rr.get('A_act', 0):.4f} m²　"
                                f"实际气速 {rr.get('u_act', 0):.3f} m/s",
                                size=9, color="#333", bold=True))
        else:
            p.append(self._text(w / 2, h - 30, "点击「计 算」查看结果",
                                size=9, color="#888"))
        p.append("</svg>")
        self.svg_widget.load("".join(p).encode("utf-8"))


# 为动态导入提供简洁别名
flash_tank_calculator = FlashTankCalculator
