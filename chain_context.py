# -*- coding: utf-8 -*-
"""计算链上下文 —— 页面之间的数据传递（会话级缓存）

═══════════════ 解决什么问题 ═══════════════
    一条工艺路线上的多个计算器常常是**串起来**的，上一段的输出就是下一段的输入：

        喷射液化器用汽量 ──→ 闪蒸（降温/浓缩）──→ 后续工段
           · 出口温度 t₂            · 进闪蒸温度
           · 蒸汽用量 D₁            · 蒸汽用量（与物料量相加）
           · 喷射后液量 G₁          · 物料量
           · 稀释后比热 C₁          · 物料比热
           · 稀释后浓度 X₁          · 干物浓度

    以前只能靠**手抄**：抄错一位数、单位看错（kg/h 与 t/h）、上游改了数忘了
    同步下游，都是这类多段表格的高发错误。本模块提供一个**会话级**的共享缓存：

        · 上游页面每次算完，把「可传递输出」登记进来（`publish`），
          连同**页面名 + 时间戳**（谁算的、几点算的）；
        · 下游页面的「取上游值」下拉从缓存里列出可用来源，一键填进输入框
          （`sources` / `get`）；
        · 下游填过之后仍**可手工修改**（引用只是填值，不做绑定）；
        · 上游重算后，下游引用的时间戳会比上游的新时间戳旧，即 `is_stale`
          → 下游给出「上游已重算，数据可能已过期」提示。

═══════════════ 设计取舍 ═══════════════
    · **值语义、非绑定**：引用一次即把数值填进输入框，之后各自独立。
      不做双向绑定——下游改了数不该反过来改上游，也不会因为上游重算而
      **静默**改变已经算好的下游结果（过期只提示，不自动改写）。
    · **内存态**：只在本次运行内有效，不落盘。计算链是「一次设计、连算几段」
      的工作方式，关掉程序重来本来就是新的一组工况，避免把旧数当新数。
    · **模块零依赖**：本文件不依赖 PySide6/Qt，测试可直接导入。
    · **单例入口**：全项目统一用裸名 `from chain_context import ChainContext`
      导入（本文件位于项目根，与 calculator_base / common_constants 同级），
      避免同一文件被两条导入路径加载成两个互不相干的单例。
"""

from datetime import datetime

__all__ = ["ChainContext"]


class ChainContext:
    """页面间数据传递的会话级上下文（类方法即接口，无需实例化）"""

    #: 最多保留的来源页数量（超出淘汰最旧的），避免长期运行后无限增长
    MAX_SOURCES = 12

    #: module_id → entry；entry = {
    #:     "module": module_id, "page": 页面名, "time": float(epoch),
    #:     "time_str": "09-24 08:45", "values": {键: 数值}, "units": {键: 单位},
    #:     "note": 备注（如计算模式）, "runs": 该页累计计算次数}
    _entries = {}

    #: 累计计算次数（按 module_id）
    _runs = {}

    # ═══════════════════ 写入 ═══════════════════
    @classmethod
    def publish(cls, module_id, page_name, values, units=None, note=""):
        """登记一页的计算结果（同一页重复计算时**覆盖**为最新一次）

        参数
        ----
        module_id : str   模块标识（如 "injection_liquefier_calculator"）
        page_name : str   页面显示名（如 "喷射液化器用汽量"）
        values    : dict  可传递输出 {键: 数值}，键用中文语义名
        units     : dict  可选 {键: 单位}
        note      : str   备注（如计算模式），仅供展示

        返回 entry（dict）。同一次计算重复登记会覆盖上一次（只留最新）。
        """
        if not module_id or not isinstance(values, dict) or not values:
            return None
        now = datetime.now()
        cls._runs[module_id] = cls._runs.get(module_id, 0) + 1
        entry = {
            "module": module_id,
            "page": page_name or module_id,
            "time": now.timestamp(),
            "time_str": now.strftime("%m-%d %H:%M"),
            "values": dict(values),
            "units": dict(units or {}),
            "note": note or "",
            "runs": cls._runs[module_id],
        }
        cls._entries[module_id] = entry
        cls._trim()
        return entry

    @classmethod
    def _trim(cls):
        """超出上限时淘汰最旧的来源"""
        if len(cls._entries) <= cls.MAX_SOURCES:
            return
        ordered = sorted(cls._entries.values(), key=lambda e: e["time"])
        for e in ordered[:len(cls._entries) - cls.MAX_SOURCES]:
            cls._entries.pop(e["module"], None)

    # ═══════════════════ 读取 ═══════════════════
    @classmethod
    def sources(cls):
        """可用来源列表（按时间从新到旧），供下游「取上游值」下拉使用"""
        return sorted(cls._entries.values(), key=lambda e: e["time"], reverse=True)

    @classmethod
    def get(cls, module_id):
        """取某一页的最新登记项；无则 None"""
        return cls._entries.get(module_id)

    @classmethod
    def value(cls, module_id, key, default=None):
        """取某一页的某个输出值"""
        entry = cls._entries.get(module_id)
        if not entry:
            return default
        return entry["values"].get(key, default)

    @classmethod
    def has(cls, module_id):
        return module_id in cls._entries

    # ═══════════════════ 过期检测 ═══════════════════
    @classmethod
    def is_stale(cls, ref):
        """下游引用是否已过期：上游在本次引用之后又算过

        ref 形如 {"module": module_id, "time": 引用时的 epoch}；
        上游条目不存在（例如已淘汰）时返回 False（不做无依据的提示）。
        """
        if not ref:
            return False
        entry = cls._entries.get(ref.get("module"))
        if not entry:
            return False
        return entry["time"] > float(ref.get("time") or 0.0) + 1e-6

    @classmethod
    def make_ref(cls, module_id):
        """按当前状态生成引用标记（下游取上游值时调用）"""
        entry = cls._entries.get(module_id)
        if not entry:
            return {}
        return {"module": module_id, "time": entry["time"],
                "page": entry["page"], "time_str": entry["time_str"]}

    @classmethod
    def describe_ref(cls, ref):
        """引用标记 → 展示文本，如「喷射液化器用汽量 09-24 08:45」"""
        if not ref:
            return ""
        return f"{ref.get('page', ref.get('module', ''))} {ref.get('time_str', '')}".strip()

    # ═══════════════════ 维护 ═══════════════════
    @classmethod
    def clear(cls):
        """清空全部登记（测试与「重新开始一组工况」用）"""
        cls._entries.clear()
        cls._runs.clear()

    @classmethod
    def clear_page(cls, module_id):
        """只清掉某一页的登记"""
        cls._entries.pop(module_id, None)
