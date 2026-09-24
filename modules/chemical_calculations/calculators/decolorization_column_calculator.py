"""
脱色柱计算器 —— 活性炭脱色柱：柱体装炭 / 接触时间校核 / 酸洗再生循环 / 洗水分流 / 投酸配酸

适用：玉米芯（淀粉）酸水解液经活性炭柱脱色，柱子饱和后需「放料 → 酸洗 → 水洗」
      再生。本页把公司工艺工作簿「13.脱色」页里**已经算不出数**的那套表格重建为
      自洽的计算：柱体与装炭量 → 过柱接触时间校核 → 7 次洗水递推（可反算洗水量）
      → 洗水分流去向 → 投酸（配酸）计算，并附原表的罐容 / 泵选型参照。

═══════════════ 1. 本页算什么 ═══════════════

  ① 柱体与装炭
        直筒体积（单柱） V_cyl = π/4 · D² · H                    [m³]
        床层体积（单柱） V_bed = V_cyl × 装填率 f                 [m³]
        装炭体积（全套） V_ac  = V_cyl × f × 柱数 n               [m³]
        装炭重量         W     = V_ac × 堆密度 ρ_b                [t]
        床层空隙率（校核）ε    = 1 − ρ_b / ρ_t                   [-]（净密度填了才算）
            典型活性炭床 ε ≈ 0.35~0.55；堆密度 0.45~0.65（椰壳/木质）、
            0.5~0.55（煤质）——对照照片备注。

  ② 过柱接触时间校核
        空塔接触时间 t = V_bed(单柱) / 单柱进料量 Q               [h]
        判据：t ≥ 30 min（原表「对比 >30min」，照片值 1.5 H）。

  ③ 酸洗再生循环（混合-置换递推）
        柱内持液（酸液比例） V_r = V_ac × 持液率 w                [m³]
            （照片口径：「酸液比例（水分）40%」「活性炭里面酸液体积」）
        每次洗水与柱内持液**完全混合后顶出同体积**，酸度按
            C_i = C_{i-1} × V_r / (V_r + V_w)
        递减。两条路二选一：
            · 手填每次洗水量 V_w → 递推 N 次得各次酸度，与目标最终酸度对比；
            · 每次洗水量**留空** → 按目标反算：
                  k = (C_t / C₀)^(1/N)，V_w = V_r × (1/k − 1)
              （例：C₀=60%、C_t=0.30%、N=7 → k=0.4077、V_w=1.453·V_r）
        酸量衡算：第 i 次洗水带出酸量 = C_i × V_w（与递推式严格自洽），
        全部洗水混合酸度 = (C₀ − C_t) · V_r / (N · V_w)。

  ④ 洗水分流去向（照片口径）
        第 1 次        → 酸解液储罐 或 向下一级脱色柱（酸度最高，回收价值大）
        第 2~3 次      → 浓酸储罐回用（作下一周期预洗）
        第 4~N 次      → 去中和（近水，进污水处理/中和罐）
        每股给出体积、平均酸度与折纯酸量。

  ⑤ 投酸（配酸）计算
        把料液从现有酸度 C_x 配到目标酸度 C_y 所需浓酸（浓度 C_a）：
            M_a = M × (C_y − C_x) / (C_a − C_y)                  [t]
        配酸后总量 = M + M_a；加水量 = M + M_a − M − M_a（浓酸已含水时
        以浓酸质量计，本式按浓酸质量计，不再另加水）。

  ⑥ 罐容 / 泵选型参照
        原表那两张设备表（8 种罐 + 7 种泵）的选型数已不可复算（引用链断），
        本页按**本页算得的体积需求**给出一列「需求体积」供自行定罐容，
        并原样附上原表单线 / 母液两套选型数作参照。

═══════════════ 2. 单位与假设 ═══════════════
    · 酸度一律为**质量分数 %**；稀酸密度按 ≈1 t/m³ 折算（结果区已注明）。
    · 递推模型假设每次洗水与柱内持液完全混合——实际柱内存在返混与沟流，
      达到同样最终酸度实际洗水量通常比理想值大，结果偏理想侧，仅供参考。
    · 洗水分流次数边界（1 / 2~3 / 4~N）取自照片，可在结果区按需调整口径。

═══════════════ 3. 计算链 ═══════════════
    本页无上游取值；本页输出（柱径 / 柱高 / 全容积 / 装炭体积 / 装炭重量）
    已登记计算链，下游页面（如罐容选型）可「取上游值」引用。
"""

import math

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
from chain_context import ChainContext

#: 堆密度常用区间（t/m³）：椰壳/木质炭 0.45~0.65，煤质炭 0.5~0.55
RHO_B_LO, RHO_B_HI = 0.40, 0.70
#: 床层空隙率常用区间
EPS_LO, EPS_HI = 0.33, 0.60
#: 空塔接触时间下限（h）——原表判据「>30 min」
T_CONTACT_MIN = 0.5


class DecolorizationCalculator(CalculatorBase):
    """脱色柱计算：活性炭柱体装炭 + 酸洗再生循环 + 洗水分流 + 投酸配酸"""

    #: 计算链标识
    CHAIN_MODULE = "decolorization_column_calculator"
    CHAIN_PAGE = "脱色柱计算"

    #: 本页无上游取值（CHAIN_MAP 留空）
    CHAIN_MAP = []
    _MARK_ROWS = {}

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self._last_result = {}
        self._rows = {}
        self._hint_base = {}
        self._chain_refs = []
        self._chain_detail = ""
        self._chain_status_fallback = False
        self._chain_sources = []
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
            "活性炭脱色柱（水解液/母液脱色）：柱体装炭 → 过柱接触时间校核 → "
            "酸洗再生 7 次洗水递推（每次洗水量留空即按目标最终酸度反算）→ "
            "洗水分流去向 → 投酸（配酸）计算。空塔接触时间判据 ≥30 min。")
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

        def num_edit(default, lo, hi, dec=6, placeholder=None):
            e = QLineEdit(default)
            e.setValidator(QDoubleValidator(lo, hi, dec))
            if placeholder:
                e.setPlaceholderText(placeholder)
            return e

        # ── 计算链 ──
        g0 = CalculatorBase.make_group_box("计算链（输出登记，供下游页面取用）")
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

        # ── 柱体与装炭 ──
        g1 = CalculatorBase.make_group_box("柱体与装炭（照片「中脱单套」口径）")
        g1g = new_grid(g1)
        r = 0

        self.d_input = num_edit("3.5", 0.3, 8.0)
        r = add_row(g1g, "d", "柱内径 D (m):", self.d_input,
                    "照片值 3.5（单线）/ 2.4；常用系列另见 ⑥", r)

        self.h_input = num_edit("6.5", 1.0, 20.0)
        r = add_row(g1g, "h", "直筒高度 H (m):", self.h_input,
                    "照片值 6.5（单线）/ 5.8", r)

        self.n_input = num_edit("6", 1, 60, 2)
        r = add_row(g1g, "n", "柱数量 n (个):", self.n_input,
                    "照片值 6（单线）/ 3；可含备用柱", r)

        self.f_input = num_edit("66", 10, 100, 4)
        r = add_row(g1g, "f", "装填率 f (%):", self.f_input,
                    "照片注「直筒高度的 2/3」≈66.7%，按体积分数填 66", r)

        self.rb_input = num_edit("0.5", 0.1, 2.0)
        r = add_row(g1g, "rb", "活性炭堆密度 ρ_b (t/m³):", self.rb_input,
                    "椰壳/木质 0.45~0.65，煤质 0.5~0.55（照片备注）", r)

        self.rt_input = num_edit("1.12", 0.5, 3.0)
        r = add_row(g1g, "rt", "活性炭净密度 ρ_t (t/m³):", self.rt_input,
                    "照片值 1.12；用于校核床层空隙率 ε = 1 − ρ_b/ρ_t", r)

        ll.addWidget(g1)

        # ── 操作与校核 ──
        g2 = CalculatorBase.make_group_box("操作与校核")
        g2g = new_grid(g2)
        r = 0

        self.q_input = num_edit("27.5", 0.1, 2000.0)
        r = add_row(g2g, "q", "单柱进料量 Q (m³/h):", self.q_input,
                    "空塔接触时间 t = 床层体积 ÷ Q，判据 ≥30 min（原表 1.5 H）", r)

        ll.addWidget(g2)

        # ── 酸洗再生循环 ──
        g3 = CalculatorBase.make_group_box("酸洗再生循环（混合-置换递推）")
        g3g = new_grid(g3)
        r = 0

        self.w_input = num_edit("40", 1, 100, 4)
        r = add_row(g3g, "w", "持液率 w (%装炭体积):", self.w_input,
                    "照片「酸液比例（水分）40%」→ 柱内持液 V_r = 装炭体积 × w", r)

        self.c0_input = num_edit("60", 0.01, 100, 4)
        r = add_row(g3g, "c0", "初始酸度 C₀ (%):", self.c0_input,
                    "水洗开始时柱内持液的酸度（照片「酸解液酸度等于 60%」）", r)

        self.ct_input = num_edit("0.30", 0.001, 100, 4)
        r = add_row(g3g, "ct", "目标最终酸度 C_t (%):", self.ct_input,
                    "照片值 0.30%；N 次洗水后柱内残液须降到它以下", r)

        self.nw_input = num_edit("7", 1, 50, 2)
        r = add_row(g3g, "nw", "洗水次数 N (次):", self.nw_input,
                    "照片值 7 次", r)

        self.vw_input = num_edit("", 0.0001, 100000.0, 6, "留空 = 按目标酸度反算")
        r = add_row(g3g, "vw", "每次洗水量 V_w (m³/次):", self.vw_input,
                    "留空则反算 V_w = V_r × (1/k − 1)，k = (C_t/C₀)^(1/N)", r)

        ll.addWidget(g3)

        # ── 投酸（配酸）计算 ──
        g4 = CalculatorBase.make_group_box("投酸（配酸）计算（可选）")
        g4g = new_grid(g4)
        r = 0

        self.m_input = num_edit("100", 0.01, 1000000.0, 4)
        r = add_row(g4g, "m", "料液量 M (t):", self.m_input,
                    "待配酸的酸解液/母液量（照片「总酸取值 8400 吨」量级）", r)

        self.cx_input = num_edit("0", 0, 100, 4)
        r = add_row(g4g, "cx", "现有酸度 C_x (%):", self.cx_input,
                    "配酸前料液的酸度（质量分数）", r)

        self.cy_input = num_edit("60", 0.01, 100, 4)
        r = add_row(g4g, "cy", "目标酸度 C_y (%):", self.cy_input,
                    "照片「酸解液酸度等于 60%」（母液线 70%）", r)

        self.ca_input = num_edit("98", 1, 100, 4)
        r = add_row(g4g, "ca", "浓酸浓度 C_a (%):", self.ca_input,
                    "工业浓硫酸 98%；若用 60~65% 回收酸回配请改此值", r)

        ll.addWidget(g4)
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

        # 控件全部建好后再连信号、再填下拉项（避免早发信号访问未建控件）
        self.chain_btn.clicked.connect(self._apply_chain_source)
        self._reload_chain_sources()
        self.chain_combo.currentIndexChanged.connect(self._refresh_chain_status)
        self._update_svg_diagram()

    # ═══════════════════════ 计算链 ═══════════════════════
    def _reload_chain_sources(self):
        """刷新可用上游来源下拉（本页暂无 CHAIN_MAP，仅展示来源）"""
        self.chain_combo.blockSignals(True)
        self.chain_combo.clear()
        self.chain_combo.addItem("（本页暂无上游取值项）")
        self._chain_sources = []
        try:
            for e in ChainContext.sources():
                if e.get("module") == self.CHAIN_MODULE:
                    continue
                note = f" · {e['note']}" if e.get("note") else ""
                self.chain_combo.addItem(f"{e['page']}  {e['time_str']}{note}")
                self._chain_sources.append(e)
        except Exception as ex:                                   # noqa: BLE001
            print(f"读取计算链来源失败: {ex}")
        self.chain_combo.blockSignals(False)

    def _apply_chain_source(self):
        """取上游值：本页 CHAIN_MAP 为空，给出提示（保留按钮以统一交互）"""
        self.chain_status.setText(
            "本页暂无可取的上游项——柱体/酸洗参数均为本工段手填；"
            "本页输出已登记计算链，供下游页面取用。")

    def _refresh_chain_status(self, *_a):
        if not self._chain_refs:
            return
        try:
            stale = ChainContext.stale_refs(self._chain_refs)
            src = ChainContext.describe_refs(self._chain_refs)
            if stale:
                self.chain_status.setText(
                    f"⚠ 数据来源 {src}，但上游已重算——输入可能已过期。")
            else:
                self.chain_status.setText(f"已取用：{src}（最新，未过期）")
        except Exception:                                        # noqa: BLE001
            pass

    def showEvent(self, event):                                  # noqa: N802
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
        txt = (widget.text() or "").strip()
        if not txt:
            return None
        try:
            return float(txt)
        except (TypeError, ValueError):
            raise ValueError(f"{name} 不是数字")

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
            "脱色柱直径": r.get("D", 0.0),                 # m
            "脱色柱高度": r.get("H", 0.0),                 # m
            "柱全容积": r.get("V_cyl", 0.0),               # m³/柱
            "装炭体积": r.get("V_ac", 0.0),                # m³
            "装炭重量": r.get("W_ac", 0.0),                # t
        }
        units = {"脱色柱直径": "m", "脱色柱高度": "m", "柱全容积": "m³",
                 "装炭体积": "m³", "装炭重量": "t"}
        try:
            entry = ChainContext.publish(
                self.CHAIN_MODULE, self.CHAIN_PAGE, values=vals, units=units,
                note=f"{r.get('n', 0):g} 柱 φ{r.get('D', 0):.2f}×{r.get('H', 0):.2f}")
            r["chain_published"] = bool(entry)
            r["chain_values"] = vals
            r["chain_units"] = units
            r["chain_time_str"] = entry["time_str"] if entry else ""
        except Exception as e:                                   # noqa: BLE001
            print(f"计算链登记失败（不影响计算）: {e}")
            r["chain_published"] = False

    def _compute(self):
        # ── 柱体与装炭 ──
        D = self._num(self.d_input, "柱内径")
        H = self._num(self.h_input, "直筒高度")
        n = self._num(self.n_input, "柱数量")
        f_pct = self._num(self.f_input, "装填率")
        rho_b = self._num(self.rb_input, "堆密度")
        rho_t = self._num_opt(self.rt_input, "净密度")
        # ── 操作 ──
        Q = self._num(self.q_input, "单柱进料量")
        # ── 酸洗 ──
        w_pct = self._num(self.w_input, "持液率")
        C0 = self._num(self.c0_input, "初始酸度")
        Ct = self._num(self.ct_input, "目标最终酸度")
        N = self._num(self.nw_input, "洗水次数")
        Vw_in = self._num_opt(self.vw_input, "每次洗水量")
        # ── 配酸（可选）──
        M = self._num(self.m_input, "料液量")
        Cx = self._num(self.cx_input, "现有酸度")
        Cy = self._num(self.cy_input, "目标酸度")
        Ca = self._num(self.ca_input, "浓酸浓度")

        # ── 校验 ──
        if D <= 0 or H <= 0:
            raise ValueError("柱内径与直筒高度必须大于 0")
        if n < 1:
            raise ValueError("柱数量至少 1 个")
        if not (1.0 <= f_pct <= 100.0):
            raise ValueError("装填率应在 1~100 % 之间（照片口径 66 = 直筒高的 2/3）")
        if rho_b <= 0:
            raise ValueError("堆密度必须大于 0")
        if Q <= 0:
            raise ValueError("单柱进料量必须大于 0")
        if not (0.0 < w_pct <= 100.0):
            raise ValueError("持液率应在 0~100 % 之间（照片口径 40）")
        if not (0.0 < Ct < C0 <= 100.0):
            raise ValueError("酸度须满足 0 < C_t < C₀ ≤ 100（目标必须低于初始）")
        if N < 1:
            raise ValueError("洗水次数至少 1 次")
        if Vw_in is not None and Vw_in <= 0:
            raise ValueError("每次洗水量必须大于 0（留空则按目标酸度反算）")
        if not (0.0 <= Cx < Cy <= 100.0):
            raise ValueError("配酸须满足 0 ≤ C_x < C_y ≤ 100")
        if not (Cy < Ca <= 100.0):
            raise ValueError("浓酸浓度 C_a 必须高于目标酸度 C_y")

        warn = []

        f = f_pct / 100.0
        w = w_pct / 100.0

        # ── ① 柱体与装炭 ──
        A_cyl = math.pi / 4.0 * D * D
        V_cyl = A_cyl * H                       # m³/柱
        V_cyl_total = V_cyl * n
        V_bed = V_cyl * f                       # m³/柱（床层）
        V_ac = V_bed * n                        # m³（全套装炭体积）
        W_ac = V_ac * rho_b                     # t
        eps = None
        if rho_t is not None and rho_t > 0:
            eps = 1.0 - rho_b / rho_t

        # ── ② 接触时间 ──
        t_contact = V_bed / Q                   # h
        if t_contact < T_CONTACT_MIN:
            warn.append(
                f"空塔接触时间 t = {t_contact:.3f} h（{t_contact * 60:.0f} min）低于判据"
                f" {T_CONTACT_MIN * 60:.0f} min——脱色不充分，请减小单柱进料量或"
                f"增大装填率/柱径")
        if rho_b < RHO_B_LO or rho_b > RHO_B_HI:
            warn.append(
                f"堆密度 {rho_b:.3g} t/m³ 超出常用区间 {RHO_B_LO}~{RHO_B_HI}"
                f"（椰壳/木质 0.45~0.65，煤质 0.5~0.55）——请核对牌号")
        if eps is not None and not (EPS_LO <= eps <= EPS_HI):
            warn.append(
                f"床层空隙率 ε = 1 − ρ_b/ρ_t = {eps:.3f} 超出常用区间 "
                f"{EPS_LO}~{EPS_HI}——请核对堆密度与净密度是否匹配（同一种炭）")

        # ── ③ 酸洗递推 ──
        V_r = V_ac * w                          # m³（柱内持液）
        if V_r <= 0:
            raise ValueError("柱内持液体积为 0——请检查装填率与持液率")
        vw_mode = "手填"
        if Vw_in is None:
            k_ratio = (Ct / C0) ** (1.0 / N)    # 每次剩余比
            Vw = V_r * (1.0 / k_ratio - 1.0)    # m³/次
            vw_mode = "反算（按目标酸度）"
        else:
            Vw = Vw_in
            k_ratio = V_r / (V_r + Vw)
        C_list = []                             # 各次洗后酸度
        C = C0
        for _i in range(int(N)):
            C = C * V_r / (V_r + Vw)
            C_list.append(C)
        C_end = C_list[-1]
        V_wash_total = Vw * N
        C_mix = (C0 - C_end) * V_r / V_wash_total if V_wash_total > 0 else 0.0
        acid_out_total = (C0 - C_end) / 100.0 * V_r          # t 折纯（ρ≈1）
        if Vw_in is not None and C_end > Ct:
            warn.append(
                f"按手填每次洗水量 {Vw:.3f} m³ 递推 {N:.0f} 次后酸度 "
                f"{C_end:.3f} % 仍高于目标 {Ct:.3f} %——需增大每次洗水量"
                f"（留空可自动反算）或增加洗水次数")

        # ── ④ 洗水分流（1 / 2~3 / 4~N）──
        groups = []
        n1 = min(1, len(C_list))
        if n1:
            groups.append(("第 1 次 → 酸解液储罐 / 向下一级脱色柱",
                           C_list[0:n1], 1))
        n2 = min(2, max(0, len(C_list) - 1))
        if n2:
            groups.append(("第 2~3 次 → 浓酸储罐回用",
                           C_list[1:1 + n2], 2))
        n3 = max(0, len(C_list) - 3)
        if n3:
            groups.append((f"第 4~{int(N)} 次 → 去中和", C_list[3:], 3))
        split = []
        for label, cs, _gi in groups:
            vol = Vw * len(cs)
            acid = sum(cs) / 100.0 * Vw         # t 折纯
            c_avg = sum(cs) / len(cs) if cs else 0.0
            split.append({"label": label, "count": len(cs), "vol": vol,
                          "c_avg": c_avg, "acid": acid})
        split_acid = sum(s["acid"] for s in split)
        if abs(split_acid - acid_out_total) > 1e-6 * max(1.0, acid_out_total):
            warn.append("洗水分流的酸量合计与总量不符——请检查洗水次数")

        # ── ⑤ 配酸 ──
        Ma = M * (Cy - Cx) / (Ca - Cy)          # t 浓酸
        M_total = M + Ma
        acid_pure = Ma * Ca / 100.0

        return {
            # 输入回显
            "D": D, "H": H, "n": n, "f_pct": f_pct, "f": f, "rho_b": rho_b,
            "rho_t": rho_t, "Q": Q, "w_pct": w_pct, "w": w,
            "C0": C0, "Ct": Ct, "N": N, "Vw_in": Vw_in, "vw_mode": vw_mode,
            "M": M, "Cx": Cx, "Cy": Cy, "Ca": Ca,
            # ① 柱体
            "A_cyl": A_cyl, "V_cyl": V_cyl, "V_cyl_total": V_cyl_total,
            "V_bed": V_bed, "V_ac": V_ac, "W_ac": W_ac, "eps": eps,
            # ② 接触时间
            "t_contact": t_contact,
            # ③ 递推
            "V_r": V_r, "k_ratio": k_ratio, "Vw": Vw,
            "C_list": C_list, "C_end": C_end,
            "V_wash_total": V_wash_total, "C_mix": C_mix,
            "acid_out_total": acid_out_total,
            # ④ 分流
            "split": split,
            # ⑤ 配酸
            "Ma": Ma, "M_total": M_total, "acid_pure": acid_pure,
            "chain_src": ChainContext.describe_refs(self._chain_refs),
            "warn": warn,
        }

    # ═══════════════════════ 结果渲染 ═══════════════════════
    def _render(self, r):
        L = []
        L.append("脱色柱计算（活性炭柱与酸洗再生）")
        L.append("=" * 58)
        if r.get("chain_src"):
            L.append(f"【计算链来源】{r['chain_src']}（可手工修改）")
            L.append("")
        L.append("【一、柱体与装炭】")
        L.append("      直筒体积 V = π/4 · D² · H　　床层 = V × 装填率 f")
        L.append(f"  柱内径 D          = {r['D']:.4g} m")
        L.append(f"  直筒高度 H        = {r['H']:.4g} m")
        L.append(f"  柱数量 n          = {r['n']:.4g} 个")
        L.append(f"  装填率 f          = {r['f_pct']:.4g} %"
                 f"（照片注「直筒高度的 2/3」≈66.7%）")
        L.append(f"  → 直筒体积(单柱)  = π/4 × {r['D']:.4g}² × {r['H']:.4g}"
                 f" = {r['V_cyl']:.4f} m³")
        L.append(f"  → 床层体积(单柱)  = {r['V_cyl']:.4f} × {r['f']:.4f}"
                 f" = {r['V_bed']:.4f} m³")
        L.append(f"  → 直筒体积(全套)  = {r['V_cyl_total']:.2f} m³"
                 f"　装炭体积 = {r['V_ac']:.2f} m³")
        L.append(f"  堆密度 ρ_b        = {r['rho_b']:.4g} t/m³"
                 f"（椰壳/木质 0.45~0.65，煤质 0.5~0.55）")
        L.append(f"  → 装炭重量 W      = {r['V_ac']:.2f} × {r['rho_b']:.4g}"
                 f" = {r['W_ac']:.2f} t")
        if r["eps"] is not None:
            L.append(f"  床层空隙率 ε      = 1 − {r['rho_b']:.4g}/{r['rho_t']:.4g}"
                     f" = {r['eps']:.4f}（常用 0.33~0.60）")
        L.append("")
        L.append("【二、过柱接触时间校核】")
        L.append(f"  单柱进料量 Q      = {r['Q']:.4g} m³/h")
        L.append("      t = 床层体积(单柱) / Q　　判据 ≥ 30 min")
        L.append(f"  → 接触时间 t      = {r['V_bed']:.4f} ÷ {r['Q']:.4g}"
                 f" = {r['t_contact']:.3f} h = {r['t_contact'] * 60:.0f} min"
                 f"（原表照片值 1.5 H）")
        L.append("")
        L.append("【三、酸洗再生循环（混合-置换递推）】")
        L.append(f"  持液率 w          = {r['w_pct']:.4g} %（照片「酸液比例（水分）」）")
        L.append(f"  → 柱内持液 V_r    = {r['V_ac']:.2f} × {r['w']:.4f}"
                 f" = {r['V_r']:.2f} m³")
        L.append(f"  初始酸度 C₀       = {r['C0']:.4g} %　"
                 f"目标最终酸度 C_t = {r['Ct']:.4g} %　"
                 f"洗水次数 N = {r['N']:.4g}")
        L.append(f"  每次洗水量 V_w    = {r['Vw']:.3f} m³/次   [{r['vw_mode']}]")
        L.append(f"     （递推式 C_i = C_(i-1) × V_r/(V_r+V_w)，"
                 f"每次剩余比 k = {r['k_ratio']:.4f}）")
        L.append(f"  → 总洗水量        = {r['Vw']:.3f} × {r['N']:.0f}"
                 f" = {r['V_wash_total']:.1f} m³")
        L.append(f"  → 洗完残液酸度    = {r['C_end']:.3f} %"
                 f"（目标 {r['Ct']:.3g} %）")
        L.append(f"  → 全部洗水混合酸度= (C₀−C_t)·V_r / 总洗水量"
                 f" = {r['C_mix']:.3f} %")
        L.append(f"  → 带出折纯酸量    = {r['acid_out_total']:.2f} t"
                 f"（稀酸按 ρ≈1 t/m³ 折）")
        L.append("")
        L.append("  逐次递推表：")
        L.append("      次    洗后酸度(%)   该次带出酸(t)   累计(t)")
        acc = 0.0
        for i, c in enumerate(r["C_list"], 1):
            d_acid = c / 100.0 * r["Vw"]
            acc += d_acid
            L.append(f"      {i:>2d}    {c * 100:>10.3f}   {d_acid:>12.3f}"
                     f"   {acc:>10.3f}")
        L.append("")
        L.append("【四、洗水分流去向（照片口径：1 / 2~3 / 4~N）】")
        for s in r["split"]:
            L.append(f"  {s['label']}")
            L.append(f"      体积 {s['vol']:.1f} m³（{s['count']} 次 ×"
                     f" {r['Vw']:.2f}）　平均酸度 {s['c_avg'] * 100:.3f} %"
                     f"　折纯酸 {s['acid']:.2f} t")
        L.append("")
        L.append("【五、投酸（配酸）计算】")
        L.append("      M_a = M × (C_y − C_x) / (C_a − C_y)")
        L.append(f"  料液量 M          = {r['M']:.4g} t（现有酸度 C_x ="
                 f" {r['Cx']:.4g} %）")
        L.append(f"  目标酸度 C_y      = {r['Cy']:.4g} %　"
                 f"浓酸浓度 C_a = {r['Ca']:.4g} %")
        L.append(f"  → 需投浓酸 M_a    = {r['M']:.4g} × ({r['Cy']:.4g} −"
                 f" {r['Cx']:.4g}) / ({r['Ca']:.4g} − {r['Cy']:.4g})"
                 f" = {r['Ma']:.3f} t")
        L.append(f"  → 配酸后总量      = {r['M_total']:.3f} t"
                 f"（其中折纯酸 {r['acid_pure']:.3f} t）")
        L.append("")
        L.append("【六、罐容 / 泵选型参照】")
        L.append("  本页体积需求（供定罐容；原表选型数已不可复算，附后作参照）：")
        L.append(f"      每次洗水量（洗水罐/反冲水罐）   {r['Vw']:.1f} m³")
        L.append(f"      2~3 次回用酸（浓酸罐）          "
                 f"{r['Vw'] * min(2, max(0, r['N'] - 1)):.1f} m³")
        L.append(f"      总洗水量（回收/中和系统）       {r['V_wash_total']:.1f} m³")
        L.append(f"      单柱全容积（配酸/置换）         {r['V_cyl']:.1f} m³")
        L.append("  原表选型参照（单线 / 母液共用，单位 m³）：")
        L.append("      脱色柱 6×? / 10×3柱　水罐 20 / 110　浓酸罐10% 6 / 40")
        L.append("      洗酸罐1~2% 10 / 80　配酸储罐 3 / 20　回收酸罐 3 / 20")
        L.append("      配酸碱罐 3 / 20　回收碱罐 3 / 20　回收反冲水罐 6 / 30")
        L.append("  原表泵参照（7 种）：脱色进料 / 脱色水 / 盐酸进料 / 碱进料 /")
        L.append("      碱回收 / 脱色浓酸 / 脱色浓碱（含备用 ×2 套）——流量按本页")
        L.append("      体积需求 ÷ 操作窗口估，扬程按管路另计。")
        if r["warn"]:
            L.append("")
            L.append("【提示与警告】")
            for i, w_ in enumerate(r["warn"], 1):
                L.append(f"  {i}) {w_}")
        if r.get("chain_published"):
            L.append("")
            L.append("【计算链】本页输出已登记，下游页面可用「取上游值」引用：")
            for k, v in (r.get("chain_values") or {}).items():
                u_ = (r.get("chain_units") or {}).get(k, "")
                L.append(f"      {k:<10s} = {v:>10.4f} {u_}")
            L.append(f"      登记时间：{r.get('chain_time_str', '')}")
        L.append("")
        L.append("=" * 58)
        L.append("  口径说明：酸度为质量分数 %；稀酸按 ρ≈1 t/m³ 折算。递推模型假设")
        L.append("  每次洗水与柱内持液完全混合——实际柱内存在返混与沟流，达到同样最终")
        L.append("  酸度实际洗水量通常比理想值大。洗水分流次数边界（1 / 2~3 / 4~N）")
        L.append("  取自原表照片，可按车间实际调整。结果仅供参考，实际工程须经专业")
        L.append("  工程师审核确认。")
        L.append("=" * 58)
        self.result_text.setPlainText("\n".join(L))

    def _show_error(self, msg):
        self.result_text.setPlainText(f"错误：{msg}")
        self._last_result = {}

    # ═══════════════════════ 默认值 / 清空 ═══════════════════════
    def setup_default_values(self):
        self.d_input.setText("3.5")
        self.h_input.setText("6.5")
        self.n_input.setText("6")
        self.f_input.setText("66")
        self.rb_input.setText("0.5")
        self.rt_input.setText("1.12")
        self.q_input.setText("27.5")
        self.w_input.setText("40")
        self.c0_input.setText("60")
        self.ct_input.setText("0.30")
        self.nw_input.setText("7")
        self.vw_input.setText("")
        self.m_input.setText("100")
        self.cx_input.setText("0")
        self.cy_input.setText("60")
        self.ca_input.setText("98")

    def clear_inputs(self):
        """恢复出厂默认值（可直接重算）；同时解除上游引用"""
        self.setup_default_values()
        self._chain_refs = []
        self._chain_detail = ""
        self._chain_status_fallback = False
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
            "柱内径_m": r.get("D", 0),
            "直筒高度_m": r.get("H", 0),
            "柱数量": r.get("n", 0),
            "装填率_pct": r.get("f_pct", 0),
            "堆密度_t_m3": r.get("rho_b", 0),
            "净密度_t_m3": r.get("rho_t", 0) or 0,
            "单柱进料量_m3_h": r.get("Q", 0),
            "持液率_pct": r.get("w_pct", 0),
            "初始酸度_pct": r.get("C0", 0),
            "目标最终酸度_pct": r.get("Ct", 0),
            "洗水次数": r.get("N", 0),
            "每次洗水量_m3": r.get("Vw", 0),
            "料液量_t": r.get("M", 0),
            "现有酸度_pct": r.get("Cx", 0),
            "目标酸度_pct": r.get("Cy", 0),
            "浓酸浓度_pct": r.get("Ca", 0),
        }
        outputs = {
            "直筒体积_m3": round(r.get("V_cyl", 0), 4),
            "装炭体积_m3": round(r.get("V_ac", 0), 2),
            "装炭重量_t": round(r.get("W_ac", 0), 2),
            "接触时间_h": round(r.get("t_contact", 0), 3),
            "柱内持液_m3": round(r.get("V_r", 0), 2),
            "每次洗水量_m3": round(r.get("Vw", 0), 3),
            "洗完残液酸度_pct": round(r.get("C_end", 0), 4),
            "总洗水量_m3": round(r.get("V_wash_total", 0), 1),
            "需投浓酸_t": round(r.get("Ma", 0), 3),
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
            "calculation_type": "脱色柱计算",
        }

    def generate_report(self):
        """生成计算书文本（str；无结果返回 None）"""
        try:
            body = self.result_text.toPlainText()
            if not body or "脱色柱计算" not in body:
                return None
            info = self.get_project_info()
            head = "\n".join([
                "═" * 58,
                "        脱色柱计算书（活性炭柱与酸洗再生）",
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
                "  1. 直筒体积  V_cyl = π/4 · D² · H                    m³/柱",
                "     床层体积 V_bed = V_cyl × f；装炭体积 = V_cyl × f × n",
                "     装炭重量 W = 装炭体积 × 堆密度 ρ_b                  t",
                "  2. 空塔接触时间 t = V_bed / Q ≥ 30 min（原表判据）     h",
                "  3. 酸洗递推（混合-置换）：C_i = C_(i-1) · V_r/(V_r+V_w)",
                "     反算每次洗水量：V_w = V_r · (1/k − 1)，k = (C_t/C₀)^(1/N)",
                "     酸量衡算：第 i 次带出酸 = C_i · V_w（严格自洽）",
                "  4. 洗水分流：第1次→酸解液储罐/下一级柱；2~3次→浓酸罐回用；",
                "     4~N次→去中和（照片口径）",
                "  5. 投酸配酸：M_a = M(C_y−C_x)/(C_a−C_y)                t",
                "",
                "═" * 58,
                " 数据来源与假设",
                "═" * 58,
                "",
                "  1. 柱体/装炭/酸洗参数照片取自公司工艺工作簿「13.脱色」页",
                "     （中脱单套 φ3.5×6.5×6 柱、装填率 66%、堆密度 0.5、",
                "     持液率 40%、洗水 7 次、最终酸度 0.30%、接触时间 1.5 H）；",
                "  2. 递推模型假设每次洗水与柱内持液完全混合，实际存在返混与",
                "     沟流，达到同样最终酸度实际洗水量通常偏大；",
                "  3. 酸度为质量分数 %，稀酸按 ρ≈1 t/m³ 折算；",
                "  4. 结果仅供参考，实际工程须经专业工程师审核确认。",
                "",
                "---",
                "生成于 ChemCal 工程计算模块",
            ])
            return f"{head}\n\n{body}\n\n{foot}"
        except Exception as e:                                   # noqa: BLE001
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        ReportExporter.export_docx(self, "脱色柱计算")

    def download_pdf_report(self):
        ReportExporter.export_pdf(self, "脱色柱计算")

    # ═══════════════════════ SVG 示意图 ═══════════════════════
    def _text(self, x, y, text, size=9, color="#333", bold=False, center=True):
        return svg_text(x, y, text, size, color, bold, center)

    def _update_svg_diagram(self):
        """流程示意：脱色柱装炭层 + 进料/出料 + 洗水分流三股去向"""
        w, h = 380, 250
        rr = self._last_result or {}
        D_show = rr.get("D", 3.5)
        H_show = rr.get("H", 6.5)

        p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
             f'width="{w}" height="{h}">',
             f'<rect x="0" y="0" width="{w}" height="{h}" fill="#fafbfc" rx="6"/>']

        cx = 120
        rw_ = 46
        top, bot = 46, 176
        cap = 14
        p.append(f'<rect x="{cx - rw_}" y="{top}" width="{2 * rw_}" '
                 f'height="{bot - top}" fill="#eef5fb" stroke="#2c6fa5" '
                 f'stroke-width="1.8"/>')
        p.append(f'<path d="M {cx - rw_} {top} q {rw_} -{cap} {2 * rw_} 0" '
                 f'fill="#eef5fb" stroke="#2c6fa5" stroke-width="1.8"/>')
        p.append(f'<path d="M {cx - rw_} {bot} q {rw_} {cap} {2 * rw_} 0" '
                 f'fill="#eef5fb" stroke="#2c6fa5" stroke-width="1.8"/>')
        # 装炭层（床层）
        bed_top = top + 16
        p.append(f'<rect x="{cx - rw_ + 4}" y="{bed_top}" width="{2 * rw_ - 8}" '
                 f'height="{bot - bed_top - 8}" fill="#d9e7d4" stroke="#7aa87a" '
                 f'stroke-width="1.2"/>')
        for yy in range(bed_top + 8, bot - 12, 10):
            p.append(f'<line x1="{cx - rw_ + 8}" y1="{yy}" x2="{cx + rw_ - 8}" '
                     f'y2="{yy}" stroke="#a8c8a2" stroke-width="0.7"/>')
        p.append(self._text(cx, (bed_top + bot) / 2 + 4, "活性炭床",
                            size=9, color="#2f5233", bold=True))
        p.append(self._text(cx, top + 8, "脱色柱", size=10, color="#1b4f72",
                            bold=True))

        # 进料（左上）
        p.append(f'<line x1="30" y1="70" x2="{cx - rw_}" y2="70" '
                 f'stroke="#27ae60" stroke-width="2.5"/>')
        p.append(f'<path d="M {cx - rw_} 70 l -10 -5 l 0 10 z" fill="#27ae60"/>')
        p.append(self._text(32, 62, "酸解液进料", size=8, color="#1d6f42",
                            bold=True, center=False))

        # 底部出料 → 下一工段
        p.append(f'<line x1="{cx}" y1="{bot + cap}" x2="{cx}" y2="216" '
                 f'stroke="#c0392b" stroke-width="2.5"/>')
        p.append(f'<path d="M {cx} 216 l -5 -10 l 10 0 z" fill="#c0392b"/>')
        p.append(self._text(cx + 8, 212, "脱色液 → 离交", size=8, color="#c0392b",
                            bold=True, center=False))

        # 再生循环（右侧）：洗水进 + 三股分流
        rx = 250
        p.append(f'<line x1="{rx}" y1="60" x2="{cx + rw_}" y2="60" '
                 f'stroke="#2980b9" stroke-width="2.2"/>')
        p.append(f'<path d="M {cx + rw_} 60 l 10 -5 l 0 10 z" fill="#2980b9"/>')
        p.append(self._text(rx + 6, 54, "洗水 / 酸洗", size=8, color="#1b4f72",
                            bold=True, center=False))

        outs = [
            (96, "第1次 → 酸解液罐/下一级柱", "#8e44ad"),
            (128, "第2~3次 → 浓酸罐回用", "#e67e22"),
            (160, "第4~N次 → 去中和", "#7f8c8d"),
        ]
        for yy, txt, col in outs:
            p.append(f'<line x1="{cx + rw_}" y1="{yy}" x2="{rx + 40}" y2="{yy}" '
                     f'stroke="{col}" stroke-width="2"/>')
            p.append(f'<path d="M {rx + 40} {yy} l 10 -5 l 0 10 z" '
                     f'fill="{col}"/>')
            p.append(self._text(rx + 56, yy + 4, txt, size=7.5, color=col,
                                center=False))

        # 尺寸与结果摘要
        p.append(f'<line x1="{cx - rw_ - 10}" y1="{top}" x2="{cx - rw_ - 10}" '
                 f'y2="{bot}" stroke="#7f8c8d" stroke-width="1"/>')
        p.append(self._text(cx - rw_ - 44, (top + bot) / 2, f"H={H_show:g} m",
                            size=8, color="#555"))
        p.append(self._text(cx - rw_ - 44, (top + bot) / 2 + 14,
                            f"D=φ{D_show:g}", size=8, color="#555"))
        if rr:
            p.append(self._text(w / 2, h - 40,
                                f"{rr.get('n', 0):g} 柱 φ{D_show:g}×{H_show:g} m　"
                                f"装炭 {rr.get('W_ac', 0):.1f} t",
                                size=9, color="#1d6f42", bold=True))
            p.append(self._text(w / 2, h - 22,
                                f"洗水 {rr.get('Vw', 0):.1f} m³/次 ×"
                                f" {rr.get('N', 0):.0f} 次　洗后酸度 "
                                f"{rr.get('C_end', 0) * 100:.2f} %",
                                size=9, color="#333", bold=True))
        else:
            p.append(self._text(w / 2, h - 30, "点击「计 算」查看结果",
                                size=9, color="#888"))
        p.append("</svg>")
        self.svg_widget.load("".join(p).encode("utf-8"))


# 为动态导入提供简洁别名
decolorization_column_calculator = DecolorizationCalculator
