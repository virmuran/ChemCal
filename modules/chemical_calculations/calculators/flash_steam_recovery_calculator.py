"""
闪蒸蒸汽回收计算器 —— 二次蒸汽冷凝换热的回收热量与可加热物料量

适用：闪蒸罐二次蒸汽（低压饱和汽）**不直接放空**、而是进换热器把热量回收
      用来预热冷水/调浆稀乳液的工段。与「闪蒸降温浓缩」页通过计算链衔接：
      闪蒸页算出闪蒸汽量 D_f → 本页算这股汽能回收多少热、能加热多少物料。

═══════════════ 1. 回收的是什么热 ═══════════════
    闪蒸汽（压力 p 的饱和汽）进换热器，走三步放热：
        ① 在饱和温度 t_sat(p) 下凝结，放出汽化潜热 r
        ② 凝结水（同压饱和水，显热 h_f(p)）继续降温到热水（凝水）温度 t_hot，
           再放出显热 h_f(p) − h_f(t_hot)
    两步合计，以换热器为系统（0 °C 液态水焓基准）：

        **Q = D_f · [ h_g(p) − h_f(t_hot) ]**                       [kJ/h]

    · h_g(p) = 闪蒸气压力下的饱和蒸汽总焓（= r + h_f，即表格里
      「蒸汽焓」列）；h_f(t_hot) = 热水温度下的饱和水焓（表格「热水显热」列，
      = 热水温度行的「蒸汽焓 − 汽化热」）。
    · 平均换热功率（工程常用 kW）= Q / 3600。
    · 冷水流（显热 h_f(t_cold)，表格「冷水显热」列）只是被加热的一方，
      不进入本式——它通过水量平衡式体现（见 §3）。

═══════════════ 2. 与设计表格的对照 ═══════════════
    表格式：Q_tab = D_f · ( r + h_f − 热水显热 )
    与严格式逐项对应：r + h_f = h_g(p)，「热水显热」= h_f(t_hot)。
    · r（蒸汽潜热）、h_f（饱和水显热）在本页为**可选手填**：填了按填值算
      （表格口径，并列输出对照），留空按 IAPWS-IF97 自动取。
    · 手填值与自动值差超 1 % 时提示核对是否查错蒸汽表（仍按填值算，
      不静默改数）。
    · 项目自带「饱和水蒸气表（按压力排列）」7 列在本页全部对应：
        绝对压力 p / 温度 t_sat / 蒸汽比容 v_g / 蒸汽密度 ρ_g /
        液体焓 h_f（= 饱和水显热 / 冷水·热水显热的查表来源）/
        蒸汽焓 h_g / 汽化热 r（= 蒸汽潜热）。

═══════════════ 3. 蒸汽体积与可加热物料量 ═══════════════
    蒸汽体积流量（选风机/管道/换热器口径用）：
        V = D_f · v_g = D_f / ρ_g                                  [m³/h]
    · 比容与密度二选一填，或留空自动（二者互为倒数，本页自动换算）。
      ⚠ 设计表格「蒸汽体积 = 闪蒸汽用量 × 密度 × 1000」按量纲只能解读为
      「用量(t/h) × 1000(kg/t) × **比容**(m³/kg)」——若那格填的真是密度
      (kg/m³)，正确式是「用量 ÷ 密度」。本页两种都支持，按量纲算，不会错。

    可加热物料量（把闪蒸汽回收的热全部用于预热冷水/稀浆）：
        G_m = Q / ( c · (t_hot − t_cold) )                         [kg/h]
        体积流量 = G_m / ρ_m                                       [m³/h]
    · c = 物料比热（表格「水的比热-物料」：稀浆/热水的比热，可取上游
      喷射液化器的物料比热）；ρ_m = 物料密度（取喷射器的修正比重，t/m³）。
    · 表格把这栏叫「水量」——当被加热的是清水时 c = 4.18、ρ_m = 1.0，
      结果就是加热水量；本页统一按物料算，清水只是特例。

═══════════════ 4. 硬约束与提示 ═══════════════
    · t_hot ＞ t_cold（否则无加热意义）；
    · t_hot ＜ t_sat(p)：压力 p 的蒸汽最多把冷流加热到 t_sat(p)，
      且换热需要温差，t_hot 逼近 t_sat 时提示「换热面积激增，不经济」；
    · 凝结水量 = D_f（闪蒸汽全部凝结），凝水温度按 t_hot 计。

═══════════════ 5. 计算链联动 ═══════════════
    本页可取上游结果，不必手抄：
        闪蒸汽用量 ← 闪蒸降温浓缩「闪蒸汽量」     (kg/h)
        闪蒸气压力 ← 闪蒸降温浓缩「闪蒸压力」     (MPa → kPa 自动换算)
        物料比热   ← 喷射液化器「物料比热」       (kJ/(kg·K))
        物料密度   ← 喷射液化器「浆料比重」       (20 °C 修正比重，t/m³)
    取值后仍可手工修改；上游重算后提示「数据可能已过期」。

    **向下游提供**：「闪蒸罐计算」页要用罐压下的饱和汽密度定罐径，本页把
    「蒸汽密度」(kg/m³) 与「蒸汽比容」(m³/kg) 一并登记，下游一键即可取到
    ——即设计表格里的「闪蒸汽密度 = 1 ÷ 闪蒸蒸汽回收那边的密度」。

═══════════════ 6. 数据来源与口径 ═══════════════
    · 饱和蒸汽总焓 / 饱和水焓 / 汽化潜热 / 比容：IAPWS-IF97（steam_iapws），
      与「饱和水蒸气表（按压力排列）」同源；工程表（如 4~1500 kPa 排表）
      与 IF97 差异多在 0.5 % 以内，手填对照可发现查表/抄录错误。
    · 冷凝换热式为化工原理通用式；未计换热器热损、不凝气与闪蒸汽过热，
      结果仅供参考，实际工程须经专业工程师审核确认。
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
# 计算链：与闪蒸降温浓缩 / 喷射液化器等页面共享「上游输出」
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


class FlashSteamRecoveryCalculator(CalculatorBase):
    """闪蒸蒸汽回收计算器：回收热量 / 蒸汽体积 / 可加热物料量"""

    #: 计算链标识（供更下游的页面取用本页输出）
    CHAIN_MODULE = "flash_steam_recovery_calculator"
    CHAIN_PAGE = "闪蒸蒸汽回收"

    #: 取上游值时的字段映射：上游输出键 → (本页输入控件属性名, 换算系数, 单位)
    CHAIN_MAP = [
        ("闪蒸汽量", "df_input", 1.0, "kg/h"),
        ("闪蒸压力", "p_input", 1000.0, "kPa"),      # 上游 MPa → 本页 kPa
        ("物料比热", "cp_input", 1.0, "kJ/(kg·K)"),
        ("浆料比重", "rho_input", 1.0, "t/m³"),
    ]

    #: 取上游值时打标记的行 key ↔ 控件属性名
    _MARK_ROWS = {
        "df_input": "df", "p_input": "p", "cp_input": "cp", "rho_input": "rho",
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
            "闪蒸汽（二次蒸汽）回收核算：闪蒸汽进换热器冷凝放热 → 回收热量 → "
            "蒸汽体积 → 可加热物料量。点「取上游值」一次取全整链："
            "物料比热 / 浆料比重 ← 喷射液化器用汽量，闪蒸汽量 / 闪蒸压力 ← 闪蒸降温浓缩，"
            "不必手抄、也不用分两次取（下拉里可改为只取某一段）。")
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

        # ── 闪蒸汽（可取上游）──
        g1 = CalculatorBase.make_group_box("闪蒸汽（可取上游）")
        g1g = new_grid(g1)
        r = 0

        self.df_input = QLineEdit("145")
        self.df_input.setValidator(QDoubleValidator(0.01, 1000000.0, 2))
        r = add_row(g1g, "df", "闪蒸汽用量 D_f (kg/h):", self.df_input,
                    "取闪蒸页「闪蒸汽量」", r)

        self.p_input = QLineEdit("101.325")
        self.p_input.setValidator(QDoubleValidator(1.0, 1600.0, 3))
        r = add_row(g1g, "p", "闪蒸气压力 p (kPa 绝压):", self.p_input,
                    "取闪蒸页「闪蒸压力」（自动 MPa→kPa）；常压 101.325", r)

        ll.addWidget(g1)

        # ── 蒸汽物性（可手填对照）──
        g2 = CalculatorBase.make_group_box("蒸汽物性（留空 = 按 p 自动查表）")
        g2g = new_grid(g2)
        r = 0

        self.r_input = QLineEdit("")
        self.r_input.setValidator(QDoubleValidator(100.0, 4000.0, 2))
        self.r_input.setPlaceholderText("留空 = 自动")
        r = add_row(g2g, "r", "蒸汽潜热 r (kJ/kg):", self.r_input,
                    "表格「汽化热」列；常压 ≈ 2257", r)

        self.hf_input = QLineEdit("")
        self.hf_input.setValidator(QDoubleValidator(0.0, 2500.0, 2))
        self.hf_input.setPlaceholderText("留空 = 自动")
        r = add_row(g2g, "hf", "饱和水显热 h_f (kJ/kg):", self.hf_input,
                    "表格「液体焓」列；常压 ≈ 419", r)

        self.vg_mode = QComboBox()
        self.vg_mode.addItems(["按比容 v_g (m³/kg)", "按密度 ρ_g (kg/m³)"])
        self.vg_mode.setStyleSheet(COMBOBOX_STYLE)
        g2g.addWidget(lbl("蒸汽比容/密度:"), r, 0)
        g2g.addWidget(self.vg_mode, r, 1)
        g2g.addWidget(hint("二选一；量纲按所选方式算"), r, 2)
        self._rows.setdefault("vg", []).extend([None, self.vg_mode, None])
        r += 1

        self.vg_input = QLineEdit("")
        self.vg_input.setValidator(QDoubleValidator(0.05, 100.0, 5))
        self.vg_input.setPlaceholderText("留空 = 自动")
        r = add_row(g2g, "vg", "比容/密度数值:", self.vg_input,
                    "常压饱和汽比容 ≈ 1.673 m³/kg（密度 ≈ 0.598 kg/m³）", r)

        ll.addWidget(g2)

        # ── 换热条件 ──
        g3 = CalculatorBase.make_group_box("换热条件")
        g3g = new_grid(g3)
        r = 0

        self.tc_input = QLineEdit("20")
        self.tc_input.setValidator(QDoubleValidator(0.0, 200.0, 2))
        r = add_row(g3g, "tc", "冷水温度 t_cold (°C):", self.tc_input,
                    "被加热流体的进口温度", r)

        self.th_input = QLineEdit("80")
        self.th_input.setValidator(QDoubleValidator(1.0, 200.0, 2))
        r = add_row(g3g, "th", "热水温度 t_hot (°C):", self.th_input,
                    "被加热流体出口温度；凝水也按此温度排出", r)

        self.cp_input = QLineEdit("3.90")
        self.cp_input.setValidator(QDoubleValidator(1.0, 5.0, 4))
        r = add_row(g3g, "cp", "物料比热 c (kJ/(kg·K)):", self.cp_input,
                    "表格「水的比热-物料」；清水 4.18", r)

        self.rho_input = QLineEdit("1.03")
        self.rho_input.setValidator(QDoubleValidator(0.5, 2.0, 4))
        r = add_row(g3g, "rho", "物料密度 ρ_m (t/m³):", self.rho_input,
                    "取喷射器「修正比重」；清水 1.0", r)

        ll.addWidget(g3)
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

        本页的输入分属两个上游 —— 物料比热 / 浆料比重来自喷射液化器的出口状态，
        闪蒸汽量 / 闪蒸压力来自闪蒸降温浓缩。所以**不选来源**直接点按钮时，
        按工艺链顺序把线上所有上游一次填全（同名键先到先得，上游优先）；
        只想重取某一段时再在下拉里选中它。
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
                "当前没有可用上游 —— 请先到上游页（喷射液化器 / 闪蒸降温浓缩）点「计算」。")
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

    @staticmethod
    def _sat_from_temp(t_c):
        if _STEAM is None:
            raise ValueError("IAPWS-IF97 模块不可用，无法计算饱和蒸汽物性")
        return _STEAM.saturation_properties(T_C=t_c)

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
            "回收热量": r.get("Q_kW", 0.0),                   # kW
            "凝结水量": r.get("D_f", 0.0),                    # kg/h（闪蒸汽全凝）
            "可加热物料量": r.get("G_m_t", 0.0),              # t/h
            "蒸汽体积": r.get("V_steam", 0.0),                # m³/h
            # 闪蒸罐定径要用罐压下的饱和汽密度：本页按比容反算后一并登记，
            # 下游「闪蒸罐计算」页可直接取（表格口径「1 ÷ 本页密度」）
            "蒸汽密度": (1.0 / r["v_g"]) if r.get("v_g") else 0.0,   # kg/m³
            "蒸汽比容": r.get("v_g", 0.0),                           # m³/kg
        }
        units = {"回收热量": "kW", "凝结水量": "kg/h",
                 "可加热物料量": "t/h", "蒸汽体积": "m³/h",
                 "蒸汽密度": "kg/m³", "蒸汽比容": "m³/kg"}
        try:
            entry = ChainContext.publish(self.CHAIN_MODULE, self.CHAIN_PAGE,
                                         values=vals, units=units,
                                         note=f"回收 {r.get('Q_kW', 0):.0f} kW")
            r["chain_published"] = bool(entry)
            r["chain_values"] = vals
            r["chain_units"] = units
            r["chain_time_str"] = entry["time_str"] if entry else ""
        except Exception as e:                                   # noqa: BLE001
            print(f"计算链登记失败（不影响计算）: {e}")
            r["chain_published"] = False

    def _compute(self):
        # ── 闪蒸汽 ──
        D_f = self._num(self.df_input, "闪蒸汽用量")
        p_kpa = self._num(self.p_input, "闪蒸气压力")
        # ── 物性（可手填）──
        r_in = self._num_opt(self.r_input, "蒸汽潜热")
        hf_in = self._num_opt(self.hf_input, "饱和水显热")
        vg_in = self._num_opt(self.vg_input, "比容/密度")
        by_volume = (self.vg_mode.currentIndex() == 0)   # True=按比容
        # ── 换热条件 ──
        t_cold = self._num(self.tc_input, "冷水温度")
        t_hot = self._num(self.th_input, "热水温度")
        c_m = self._num(self.cp_input, "物料比热")
        rho_m = self._num(self.rho_input, "物料密度")

        # ── 校验 ──
        if D_f <= 0:
            raise ValueError("闪蒸汽用量必须大于 0")
        if not (1.0 <= p_kpa <= 1600.0):
            raise ValueError(f"闪蒸气压力 {p_kpa:.1f} kPa 超出饱和蒸汽表常用范围"
                             f"（1~1600 kPa）")
        p_abs = p_kpa / 1000.0                            # MPa 绝压
        if r_in is not None and r_in <= 0:
            raise ValueError("蒸汽潜热必须大于 0（留空则自动查表）")
        if hf_in is not None and hf_in <= 0:
            raise ValueError("饱和水显热必须大于 0（留空则自动查表）")
        if t_hot <= t_cold:
            raise ValueError(
                f"热水温度 {t_hot:.1f} °C 必须高于冷水温度 {t_cold:.1f} °C"
                f"——否则没有加热温差")
        if not (1.0 <= c_m <= 5.0):
            raise ValueError("物料比热应在 1.0~5.0 kJ/(kg·K) 之间")
        if not (0.5 <= rho_m <= 2.0):
            raise ValueError("物料密度应在 0.5~2.0 t/m³ 之间（清水 1.0）")

        # ── 闪蒸气压力下的饱和态（IAPWS）──
        sat_p = self._sat_from_abs(p_abs)
        t_sat = sat_p["T_C"]
        h_f_auto = sat_p["h_f"]
        h_g_auto = sat_p["h_g"]
        r_auto = sat_p["h_fg"]
        v_g_auto = sat_p["v_g"]
        rho_auto = 1.0 / v_g_auto if v_g_auto > 0 else 0.0

        warn = []
        # 硬约束：热水温度须低于闪蒸气饱和温度（否则蒸汽无法凝结放热）
        if t_hot >= t_sat:
            raise ValueError(
                f"热水温度 {t_hot:.1f} °C 不低于闪蒸气压力 {p_kpa:.1f} kPa 下的饱和温度 "
                f"{t_sat:.2f} °C ——压力 p 的蒸汽只能把冷流加热到 t_sat(p) 以下。\n"
                f"  要加热到 {t_hot:.1f} °C 须提高闪蒸气压力到约 "
                f"{self._p_sat_of(t_hot) * 1000.0:.0f} kPa（绝压），"
                f"或降低热水温度。")
        elif t_sat - t_hot < 5.0:
            warn.append(
                f"热水温度 {t_hot:.1f} °C 已逼近闪蒸气饱和温度 {t_sat:.2f} °C"
                f"（换热温差不足 5 °C）——实际所需换热面积会急剧增大，不经济；"
                f"热水温度通常取比 t_sat 低 10~20 °C 以上")

        # ── 物性取值：手填优先（表格口径），自动兜底（严格口径）──
        r_v = r_in if r_in is not None else r_auto
        r_src = "表格填值" if r_in is not None else "自动（IAPWS）"
        h_f_v = hf_in if hf_in is not None else h_f_auto
        hf_src = "表格填值" if hf_in is not None else "自动（IAPWS）"
        h_g_tab = h_f_v + r_v                            # 表格口径总焓 = r + h_f
        #: 蒸汽比容：按比容填/按密度填/自动
        if vg_in is not None:
            v_g = vg_in if by_volume else 1.0 / vg_in
            vg_src = "填值（比容）" if by_volume else "填值（密度倒数）"
        else:
            v_g = v_g_auto
            vg_src = "自动（IAPWS）"
        if v_g <= 0:
            raise ValueError("蒸汽比容必须大于 0")

        # 手填值与自动值对照（同喷射器/闪蒸页「查错蒸汽表」处理）
        if r_in is not None and abs(r_v - r_auto) > 0.01 * r_auto:
            warn.append(
                f"你填的蒸汽潜热 {r_v:.1f} kJ/kg 与按 p = {p_kpa:.1f} kPa 自动查算的 "
                f"{r_auto:.1f} kJ/kg 相差 {abs(r_v - r_auto) / r_auto * 100:.2f} %"
                f"——请核对是否查错了蒸汽表（本器按你填的值计算）")
        if hf_in is not None and abs(h_f_v - h_f_auto) > 0.01 * h_f_auto:
            warn.append(
                f"你填的饱和水显热 {h_f_v:.1f} kJ/kg 与按 p 自动查算的 "
                f"{h_f_auto:.1f} kJ/kg 相差 {abs(h_f_v - h_f_auto) / h_f_auto * 100:.2f} %"
                f"——请核对是否查错了蒸汽表（本器按你填的值计算）")

        # ── 回收热量 ──
        h_f_hot = self._sat_from_temp(t_hot)["h_f"]      # 热水显热 = h_f(t_hot)
        h_f_cold = self._sat_from_temp(t_cold)["h_f"]    # 冷水显热 = h_f(t_cold)
        #: 严格口径：Q = D_f × [h_g(p) − h_f(t_hot)]
        dh = h_g_auto - h_f_hot
        if dh <= 0:
            raise ValueError(
                f"焓差 (h_g(p) − h_f(t_hot)) = {dh:.1f} kJ/kg ≤ 0，参数不自洽")
        Q_kjh = D_f * dh                                  # kJ/h
        Q_kW = Q_kjh / 3600.0
        #: 表格口径：Q_tab = D_f × (r + h_f − 热水显热)
        dh_tab = h_g_tab - h_f_hot
        Q_tab_kjh = D_f * dh_tab if dh_tab > 0 else 0.0
        d_q_pct = (Q_tab_kjh - Q_kjh) / Q_kjh * 100.0 if Q_kjh > 0 else 0.0
        if (r_in is not None or hf_in is not None) and abs(d_q_pct) > 1.0:
            warn.append(
                f"表格口径（r + h_f − 热水显热 = {dh_tab:.1f}）与严格口径"
                f"（h_g(p) − h_f(t_hot) = {dh:.1f}）相差 {d_q_pct:+.2f} %"
                f"——由手填潜热/显热引起，请核对查表行")

        # ── 蒸汽体积 ──
        V_steam = D_f * v_g                               # m³/h

        # ── 可加热物料量 ──
        dT_m = t_hot - t_cold
        G_m_kgh = Q_kjh / (c_m * dT_m)                    # kg/h
        G_m_t = G_m_kgh / 1000.0
        V_m = G_m_t / rho_m                               # m³/h（t/h ÷ t/m³）
        cond_kg = D_f                                     # 凝结水量 = 闪蒸汽全凝

        #: 表格公式的「蒸汽体积 = 用量×密度×1000」按量纲解读提示
        if vg_in is not None and not by_volume and vg_in > 10.0:
            warn.append(
                f"你选了「按密度」但填的值 {vg_in:g} kg/m³ 偏大（低压饱和汽密度 "
                f"通常 < 2 kg/m³）——若是表格里的「密度」列，请确认那格是不是"
                f"**蒸汽比容**（m³/kg）")

        return {
            # 输入回显
            "D_f": D_f, "p_kpa": p_kpa, "p_abs": p_abs,
            "r_in": r_in, "hf_in": hf_in, "vg_in": vg_in, "by_volume": by_volume,
            "t_cold": t_cold, "t_hot": t_hot, "c_m": c_m, "rho_m": rho_m,
            # 饱和态
            "t_sat": t_sat, "h_f_auto": h_f_auto, "h_g_auto": h_g_auto,
            "r_auto": r_auto, "v_g_auto": v_g_auto, "rho_auto": rho_auto,
            "r_v": r_v, "r_src": r_src, "h_f_v": h_f_v, "hf_src": hf_src,
            "h_g_tab": h_g_tab, "v_g": v_g, "vg_src": vg_src,
            # 显热查表值（表格「冷水/热水显热」两列）
            "h_f_cold": h_f_cold, "h_f_hot": h_f_hot,
            # 回收热量
            "dh": dh, "dh_tab": dh_tab, "Q_kjh": Q_kjh, "Q_kW": Q_kW,
            "Q_tab_kjh": Q_tab_kjh, "d_q_pct": d_q_pct,
            # 体积与物料
            "V_steam": V_steam, "cond_kg": cond_kg,
            "G_m_kgh": G_m_kgh, "G_m_t": G_m_t, "V_m": V_m, "dT_m": dT_m,
            # 计算链来源
            "chain_src": ChainContext.describe_refs(self._chain_refs),
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
        L.append("闪蒸蒸汽回收计算")
        L.append("=" * 58)
        if r.get("chain_src"):
            L.append(f"【计算链来源】{r['chain_src']}（各项引用上游结果，可手工修改）")
            L.append("")
        L.append("【一、闪蒸汽（二次蒸汽）】")
        L.append(f"  闪蒸汽用量 D_f    = {r['D_f']:.1f} kg/h = {r['D_f'] / 1000:.4f} t/h")
        L.append(f"  闪蒸气压力 p      = {r['p_kpa']:.1f} kPa 绝压"
                 f"（{r['p_abs']:.5f} MPa）")
        L.append(f"  该压力下饱和温度  = {r['t_sat']:.2f} °C")
        L.append("")
        L.append("【二、蒸汽物性（饱和水蒸气表 7 列对应）】")
        L.append(f"  蒸汽潜热 r        = {r['r_v']:.2f} kJ/kg   [{r['r_src']}]"
                 + ("" if r['r_in'] is None else f"（自动值 {r['r_auto']:.2f}）"))
        L.append(f"  饱和水显热 h_f    = {r['h_f_v']:.2f} kJ/kg   [{r['hf_src']}]"
                 + ("" if r['hf_in'] is None else f"（自动值 {r['h_f_auto']:.2f}）"))
        L.append(f"  → 表格总焓 r+h_f  = {r['h_g_tab']:.2f} kJ/kg"
                 f"　（自动总焓 h_g = {r['h_g_auto']:.2f}）")
        L.append(f"  蒸汽比容 v_g      = {r['v_g']:.4f} m³/kg   [{r['vg_src']}]"
                 f"　密度 ρ_g = {1.0 / r['v_g']:.4f} kg/m³")
        L.append(f"  → 蒸汽体积流量    = D_f × v_g = {r['V_steam']:.0f} m³/h")
        L.append("")
        L.append("【三、回收热量（本计算器核心）】★")
        L.append("      严格口径：Q = D_f · [ h_g(p) − h_f(t_hot) ]")
        L.append(f"  热水显热 h_f(t_hot)= {r['h_f_hot']:.2f} kJ/kg"
                 f"   [热水 {r['t_hot']:.1f} °C 查表「蒸汽焓−汽化热」]")
        L.append(f"  回收焓差          = {r['h_g_auto']:.2f} − {r['h_f_hot']:.2f}"
                 f" = {r['dh']:.2f} kJ/kg")
        L.append(f"  → 平均换热功率 Q  = {r['D_f']:.1f} × {r['dh']:.2f}"
                 f" = {r['Q_kjh']:.4g} kJ/h = {r['Q_kW']:.1f} kW")
        L.append("")
        L.append("【四、表格口径对照】")
        L.append("      表格式：Q_tab = D_f · ( r + h_f − 热水显热 )")
        L.append(f"  表格焓差          = {r['r_v']:.2f} + {r['h_f_v']:.2f}"
                 f" − {r['h_f_hot']:.2f} = {r['dh_tab']:.2f} kJ/kg")
        L.append(f"  → 表格口径功率    = {r['Q_tab_kjh']:.4g} kJ/h"
                 f"（与严格口径差 {r['d_q_pct']:+.2f} %）")
        L.append(f"  冷水显热 h_f(t_cold)= {r['h_f_cold']:.2f} kJ/kg"
                 f"   [冷水 {r['t_cold']:.1f} °C 查表，供热平衡参考]")
        L.append("")
        L.append("【五、可加热物料量】")
        L.append(f"  冷水温度 t_cold   = {r['t_cold']:.1f} °C → 热水温度 t_hot = "
                 f"{r['t_hot']:.1f} °C（ΔT = {r['dT_m']:.1f} °C）")
        L.append(f"  物料比热 c        = {r['c_m']:.3f} kJ/(kg·K)"
                 f"　物料密度 ρ_m = {r['rho_m']:.3f} t/m³")
        L.append("      G_m = Q / ( c·ΔT )")
        L.append(f"  → 可加热物料量    = {r['Q_kjh']:.4g} / ({r['c_m']:.3f}×"
                 f"{r['dT_m']:.1f}) = {r['G_m_kgh']:.0f} kg/h = {r['G_m_t']:.3f} t/h")
        L.append(f"  → 体积流量        = {r['G_m_t']:.3f} / {r['rho_m']:.3f}"
                 f" = {r['V_m']:.3f} m³/h")
        L.append(f"  凝结水量          = {r['cond_kg']:.1f} kg/h"
                 f"   [闪蒸汽全部凝结，按 {r['t_hot']:.1f} °C 排出]")
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
        L.append("  口径说明：闪蒸汽在压力 p 下凝结放潜热 r，凝水再降到热水温度")
        L.append("  t_hot 放显热 (h_f − h_f(t_hot))，合计 Q = D_f·[h_g(p) − h_f(t_hot)]；")
        L.append("  与表格式 D_f·(r + h_f − 热水显热) 逐项等价（r + h_f = h_g）。")
        L.append("  「蒸汽体积 = 用量×密度×1000」按量纲应解读为 用量(t/h)×1000×")
        L.append("  比容(m³/kg)；若那格填的真是密度，则应为 用量 ÷ 密度。")
        L.append("  未计换热器热损、不凝气与过热，结果仅供参考，实际工程须经")
        L.append("  专业工程师审核确认。")
        L.append("=" * 58)
        self.result_text.setPlainText("\n".join(L))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"错误：{msg}")
        self._last_result = {}

    # ═══════════════════════ 默认值 / 清空 ═══════════════════════
    def setup_default_values(self):
        self.df_input.setText("145")
        self.p_input.setText("101.325")
        self.r_input.setText("")
        self.hf_input.setText("")
        self.vg_input.setText("")
        self.vg_mode.setCurrentIndex(0)
        self.tc_input.setText("20")
        self.th_input.setText("80")
        self.cp_input.setText("3.90")
        self.rho_input.setText("1.03")

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
            "闪蒸汽用量_kg_h": r.get("D_f", 0),
            "闪蒸气压力_kPa": r.get("p_kpa", 0),
            "蒸汽潜热_kJ_kg": round(r.get("r_v", 0), 2),
            "饱和水显热_kJ_kg": round(r.get("h_f_v", 0), 2),
            "冷水温度_C": r.get("t_cold", 0),
            "热水温度_C": r.get("t_hot", 0),
            "物料比热_kJ_kgK": r.get("c_m", 0),
            "物料密度_t_m3": r.get("rho_m", 0),
            "数据来源": r.get("chain_src", "") or "手填",
        }
        outputs = {
            "回收热量_kW": round(r.get("Q_kW", 0), 2),
            "蒸汽体积_m3_h": round(r.get("V_steam", 0), 1),
            "凝结水量_kg_h": round(r.get("cond_kg", 0), 1),
            "可加热物料量_t_h": round(r.get("G_m_t", 0), 3),
            "可加热物料量_m3_h": round(r.get("V_m", 0), 3),
            "表格口径功率_kJ_h": round(r.get("Q_tab_kjh", 0), 1),
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
            "calculation_type": "闪蒸蒸汽回收计算",
        }

    def generate_report(self):
        """生成计算书文本（str；无结果返回 None）"""
        try:
            body = self.result_text.toPlainText()
            if not body or "闪蒸蒸汽回收" not in body:
                return None
            info = self.get_project_info()
            head = "\n".join([
                "═" * 58,
                "        闪蒸蒸汽回收计算书",
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
                "  1. 回收热量（冷凝换热，0 °C 液态水焓基准）",
                "     严格口径：Q = D_f · [ h_g(p) − h_f(t_hot) ]      kJ/h",
                "     表格口径：Q = D_f · ( r + h_f − 热水显热 )",
                "     两式逐项等价（r + h_f = h_g(p)，热水显热 = h_f(t_hot)）。",
                "     r/h_f 可手填（表格口径），留空按 IAPWS-IF97 自动取；",
                "     手填与自动差 >1 % 提示核对（仍按填值算，不静默改数）。",
                "  2. 蒸汽体积流量 V = D_f · v_g = D_f / ρ_g        m³/h",
                "     比容与密度互为倒数，按所选方式按量纲换算；",
                "     表格「用量×密度×1000」按量纲应解读为 用量(t/h)×1000×比容。",
                "  3. 可加热物料量 G_m = Q / ( c·(t_hot − t_cold) )  kg/h",
                "     体积流量 = G_m / ρ_m；清水时 c = 4.18、ρ_m = 1.0。",
                "  4. 显热查表：热水/冷水显热 = 各自温度下的「蒸汽焓 − 汽化热」",
                "     （即该温度的饱和水焓 h_f）；冷水显热为热平衡参考项。",
                "  5. 硬约束：t_hot ＞ t_cold；t_hot ＜ t_sat(p)",
                "     （压力 p 的蒸汽最多把冷流加热到 t_sat 以下，且需换热温差）。",
                "  6. 凝结水量 = D_f（闪蒸汽全部凝结），按热水温度排出。",
                "",
                "═" * 58,
                " 数据来源与假设",
                "═" * 58,
                "",
                "  1. 饱和蒸汽物性（总焓/液体焓/汽化热/比容/温度）取自 IAPWS-IF97，",
                "     与项目所附「饱和水蒸气表（按压力排列，SI 单位）」同源；",
                "  2. 与闪蒸降温浓缩页通过项目内「计算链」传递闪蒸汽量与压力，",
                "     与喷射液化器传递物料比热与浆料比重；取值后可手工修改；",
                "  3. 未计换热器热损、不凝气与雾沫夹带，结果仅供参考，",
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
        ReportExporter.export_docx(self, "闪蒸蒸汽回收")

    def download_pdf_report(self):
        ReportExporter.export_pdf(self, "闪蒸蒸汽回收")

    # ═══════════════════════ SVG 示意图 ═══════════════════════
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        return svg_text(x, y, text, size, color, bold, center)

    def _update_svg_diagram(self):
        """换热器流程示意（闪蒸汽 + 冷水 → 换热器 → 凝结水 + 热水）"""
        w, h = 380, 250
        try:
            t_cold = float(self.tc_input.text())
            t_hot = float(self.th_input.text())
        except (TypeError, ValueError):
            t_cold, t_hot = 20.0, 80.0
        try:
            p_show = float(self.p_input.text())
        except (TypeError, ValueError):
            p_show = 101.325

        p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
             f'width="{w}" height="{h}">',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']

        # 换热器（中）
        x0, y0, tw, th = 150, 76, 96, 108
        p.append(f'<rect x="{x0}" y="{y0}" width="{tw}" height="{th}" fill="#eaf3fb" '
                 f'stroke="#2c6fa5" stroke-width="1.8" rx="6"/>')
        # 盘管示意
        p.append(f'<path d="M {x0 + 12} {y0 + 28} q 18 -14 36 0 q 18 14 36 0" '
                 f'fill="none" stroke="#e67e22" stroke-width="2.2"/>')
        p.append(f'<path d="M {x0 + 12} {y0 + 58} q 18 -14 36 0 q 18 14 36 0" '
                 f'fill="none" stroke="#e67e22" stroke-width="2.2"/>')
        p.append(self._text(x0 + tw / 2, y0 + th - 14, "换热器", size=10,
                            color="#1b4f72", bold=True))

        # 闪蒸汽（上进，橙色）
        p.append(f'<line x1="{x0 + tw / 2}" y1="30" x2="{x0 + tw / 2}" y2="{y0 - 3}" '
                 f'stroke="#e67e22" stroke-width="2.5"/>')
        p.append(self._text(x0 + tw / 2 + 6, 26, "闪蒸汽", size=8,
                            color="#a06010", bold=True, center=False))
        p.append(self._text(x0 + tw / 2 + 6, 40, f"{p_show:.0f} kPa", size=8,
                            color="#a06010", center=False))

        # 冷水（左进，蓝）
        p.append(f'<line x1="40" y1="116" x2="{x0 - 3}" y2="116" '
                 f'stroke="#2980b9" stroke-width="2.5"/>')
        p.append(self._text(44, 108, "冷水", size=8, color="#1b4f72", bold=True,
                            center=False))
        p.append(self._text(44, 132, f"{t_cold:.0f} °C", size=9, color="#1b4f72",
                            bold=True, center=False))

        # 热水（右出，红）
        p.append(f'<line x1="{x0 + tw + 3}" y1="116" x2="{w - 40}" y2="116" '
                 f'stroke="#c0392b" stroke-width="2.5"/>')
        p.append(self._text(w - 96, 108, "热水", size=8, color="#c0392b",
                            bold=True, center=False))
        p.append(self._text(w - 96, 132, f"{t_hot:.0f} °C", size=9,
                            color="#c0392b", bold=True, center=False))

        # 凝结水（下出）
        p.append(f'<line x1="{x0 + tw / 2}" y1="{y0 + th + 3}" x2="{x0 + tw / 2}" '
                 f'y2="204" stroke="#7f8c8d" stroke-width="2.5"/>')
        p.append(self._text(x0 + tw / 2 + 6, 220, "凝结水", size=8,
                            color="#555", bold=True, center=False))

        # 底部结果摘要
        rr = self._last_result
        if rr:
            p.append(self._text(w / 2, h - 40,
                                f"回收热量 {rr['Q_kW']:.1f} kW　"
                                f"蒸汽体积 {rr['V_steam']:.0f} m³/h",
                                size=9, color="#1d6f42", bold=True))
            p.append(self._text(w / 2, h - 22,
                                f"可加热物料 {rr['G_m_t']:.2f} t/h"
                                f"（{rr['V_m']:.2f} m³/h）",
                                size=9, color="#333", bold=True))
        else:
            p.append(self._text(w / 2, h - 30, "点击「计 算」查看结果",
                                size=9, color="#888"))
        p.append("</svg>")
        self.svg_widget.load("".join(p).encode("utf-8"))


# 为动态导入提供简洁别名
flash_steam_recovery_calculator = FlashSteamRecoveryCalculator
