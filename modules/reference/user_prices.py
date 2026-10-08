# ChemCal/modules/reference/user_prices.py
"""用户自填「询价实价」的本地存储 —— 只落本机用户目录，不进安装包、升级不覆盖。

## 为什么单独一个文件，而不是塞进 ChemCal_data.json

  * 「询价实价」是**用户自己的商业信息**（供应商报价、议价结果），与工程信息 /
    界面设置的生命周期完全不同：用户可能想单独备份、单独清空，或只把这一份
    给同事，不想连主题偏好、公司抬头一起打包带走；
  * 导出 / 导入备份只需搬这一个文件，语义干净。

## 键结构（三层，与资料库的树一致）

    {"version": 1, "updated": "2026-10-08T12:00:00", "prices": {分类: {小节: {规格: "3.2"}}}}

**为什么用「规格」文本而不用行号做键**：行号会随资料库更新而整体移位
（某节中间插一行 → 后面所有价格串位，且不会报错）。规格文本是稳定的业务主键，
即使资料库调整了顺序也仍然对得上。

## 容错

解析失败时**绝不就地覆盖**用户文件：先改名 `*.corrupt-<时间戳>.json` 保留
（与 data_manager._quarantine_broken_file 同一套做法），再以空表继续运行 ——
用户手填的价格至少还能从坏文件里抢救出来。
"""

import json
import os
import re
from datetime import datetime

#: 存储格式版本（将来结构变化时据此迁移）
STORE_VERSION = 1

#: 数据文件名（放在 ~/.ChemCal/data/ 下，与 ChemCal_data.json 同目录）
STORE_FILENAME = "equipment_prices.json"

#: 价格文本：只接受纯数字（单位由表格约定为「万元」）。
#: 不接受「3.2万」「4500元」这类带单位的写法 —— 带单位就会有两种口径混在一列里，
#: 排序、求和、导出到 Excel 全部失真。宁可在输入时挡掉并给出提示。
_PRICE_RE = re.compile(r"^\d+(?:\.\d+)?$")

#: 视为「空」的占位符（表格里未填的格子）
PLACEHOLDER = "—"


def clean_price(text):
    """把用户输入归一化成价格文本。

    返回 ``(归一化文本, 是否合法)``：

    * 空串 / 空白 / ``—`` → ``("", True)``，语义是「清除这一行的实价」；
    * 纯数字（可带小数）→ ``(去掉首尾空白的原文本, True)``；
    * 其它 → ``(原文本, False)``，调用方应拒绝并给出提示。
    """
    s = " ".join(str(text or "").split())
    if not s or s == PLACEHOLDER:
        return "", True
    if _PRICE_RE.match(s):
        return s, True
    return s, False


def default_store_path():
    """默认存储路径：``~/.ChemCal/data/equipment_prices.json``"""
    data_dir = os.path.join(os.path.expanduser("~"), ".ChemCal", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, STORE_FILENAME)


class UserPriceStore:
    """「询价实价」的三层字典 + 落盘。改动即时保存（文件很小，无需攒批）。"""

    def __init__(self, path=None):
        self.path = path or default_store_path()
        self.prices = {}          # {分类: {小节: {规格: 价格文本}}}
        self.last_error = ""
        self._load()

    # ── 读写盘 ────────────────────────────────────────────

    def _load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:                             # noqa: BLE001
            self.last_error = f"读取失败: {e}"
            self._quarantine()
            return
        if isinstance(data, dict) and isinstance(data.get("prices"), dict):
            self.prices = self._sanitize(data["prices"])
        elif isinstance(data, dict):
            # 兼容「直接就是三层字典」的手写文件（无 version/prices 外壳）
            self.prices = self._sanitize(data)
        else:
            self.last_error = "文件结构不是对象，已忽略"
            self._quarantine()

    def _sanitize(self, raw):
        """只保留 str→str→str→str 的四层结构，脏值一律丢弃（不猜、不修）。"""
        out = {}
        for cat, secs in (raw or {}).items():
            if not isinstance(secs, dict):
                continue
            keep = {}
            for sec, specs in secs.items():
                if not isinstance(specs, dict):
                    continue
                rows = {}
                for spec, val in specs.items():
                    cleaned, ok = clean_price(val)
                    if ok and cleaned:
                        rows[str(spec)] = cleaned
                if rows:
                    keep[str(sec)] = rows
            if keep:
                out[str(cat)] = keep
        return out

    def _quarantine(self):
        """把解析不了的文件改名保留（不删、不覆盖）。"""
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            broken = "%s.corrupt-%s.json" % (os.path.splitext(self.path)[0], ts)
            os.replace(self.path, broken)
            self.last_error += f"（原文件已保留为 {os.path.basename(broken)}）"
        except Exception as e:                             # noqa: BLE001
            self.last_error += f"（保留原文件也失败: {e}）"
        self.prices = {}

    def _save(self):
        """原子落盘：先写临时文件再 os.replace，避免写一半断电留下半截 JSON。"""
        payload = {
            "version": STORE_VERSION,
            "updated": datetime.now().isoformat(timespec="seconds"),
            "prices": self.prices,
        }
        tmp = self.path + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
            self.last_error = ""
            return True
        except Exception as e:                             # noqa: BLE001
            self.last_error = f"保存失败: {e}"
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
            return False

    # ── 查询 ──────────────────────────────────────────────

    def get(self, category, section, spec):
        """取某行实价；无则返回空串（调用方据此显示「—」）。"""
        return (self.prices.get(category, {})
                .get(section, {})
                .get(str(spec), ""))

    def count(self):
        """全库已填条数。"""
        return sum(len(specs) for secs in self.prices.values()
                   for specs in secs.values())

    def count_in(self, category, section):
        """某一节已填条数（表格下方「已填 n/m 行」用）。"""
        return len(self.prices.get(category, {}).get(section, {}))

    def has_any(self):
        return self.count() > 0

    # ── 写入 ──────────────────────────────────────────────

    def set(self, category, section, spec, text):
        """写入一行实价。``text`` 归一化后为空 → 等价于 remove()。返回是否落盘成功。"""
        cleaned, ok = clean_price(text)
        if not ok:
            self.last_error = "只接受数字（单位：万元）"
            return False
        if not cleaned:
            return self.remove(category, section, spec)
        spec = str(spec)
        self.prices.setdefault(category, {}).setdefault(section, {})[spec] = cleaned
        return self._save()

    def remove(self, category, section, spec):
        """清除一行实价，并顺手清掉空掉的父层（保持文件干净）。"""
        spec = str(spec)
        secs = self.prices.get(category)
        if secs:
            specs = secs.get(section)
            if specs and spec in specs:
                specs.pop(spec, None)
            if not specs:
                secs.pop(section, None)
            if not secs:
                self.prices.pop(category, None)
        return self._save()

    def clear_all(self):
        self.prices = {}
        return self._save()

    # ── 导出 / 导入（换机迁移与备份）────────────────────────

    def export_to(self, path):
        """导出为 JSON。返回 ``(ok, 条数, 错误信息)``。"""
        payload = {
            "version": STORE_VERSION,
            "exported": datetime.now().isoformat(timespec="seconds"),
            "unit": "万元",
            "prices": self.prices,
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:                             # noqa: BLE001
            return False, self.count(), f"写入失败: {e}"
        return True, self.count(), ""

    def import_from(self, path):
        """**并入**（不整体替换）另一个导出文件里的价格。

        返回 ``(ok, 新增数, 覆盖数, 导入文件总条数, 错误信息)``。
        选择并入而不是替换：替换会静默丢掉用户本机其它已填的行，而导出的多半只是
        一部分（或来自另一台机器）。同名键按导入文件为准，其余原样保留。
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:                             # noqa: BLE001
            return False, 0, 0, 0, f"读取失败: {e}"

        raw = data.get("prices") if isinstance(data, dict) else None
        if raw is None and isinstance(data, dict):
            raw = data
        incoming = self._sanitize(raw)
        added = updated = total = 0
        for cat, secs in incoming.items():
            for sec, specs in secs.items():
                for spec, val in specs.items():
                    total += 1
                    tgt = self.prices.setdefault(cat, {}).setdefault(sec, {})
                    if spec in tgt:
                        if tgt[spec] != val:
                            tgt[spec] = val
                            updated += 1
                    else:
                        tgt[spec] = val
                        added += 1
        if total:
            self._save()
        return True, added, updated, total, ""

    # ── 与资料库对表 ──────────────────────────────────────

    def orphan_keys(self, known_specs):
        """返回**对不上当前资料库**的键 ``[(分类, 小节, 规格)]``。

        用于导入后提示「有 n 条在本机资料库里找不到对应行」—— 那种情况通常是
        导入了一份来自更早/更新版本资料库的备份，属实、但不该静默。
        """
        bad = []
        for cat, secs in self.prices.items():
            for sec, specs in secs.items():
                for spec in specs:
                    if (cat, sec, spec) not in known_specs:
                        bad.append((cat, sec, spec))
        return bad
