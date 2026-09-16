# -*- coding: utf-8 -*-
"""
版本号规范回归测试（纯逻辑，无需 Qt / 无需联网）

锁定的规矩（详见 VERSIONING.md）：
  ① 版本号必须严格三段纯数字：禁止日期当号（1.4.20260623）、四段、前导零
  ② 比较按段位数值：历史上 1.5.23 被写成"1.5.2 的第 3 次修订"，
     结果被判为比 1.5.3 更新，会把用户往降级方向引（真实踩到，此处固化）
  ③ 升号工具只 +1、不跳号；同步 version.py / ChemCal.iss / README 三处
  ④ 一致性：version.py 的版本号必须与 ChemCal.iss、README 徽章完全一致
     （自动更新只读 tag，三处不一致就是事故起点）

运行：
    .venv/Scripts/python.exe tests/test_versioning.py
"""
import os
import re
import sys
import tempfile

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

import version as version_mod
import bump_version
from version import (
    VERSION, parse_version, compare_versions, is_valid_version, version_info,
)

PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}   {extra}")


def raises(exc, fn, *a, **kw):
    """执行 fn，若抛出 exc 返回 True。"""
    try:
        fn(*a, **kw)
    except exc:
        return True
    except Exception:
        return False
    return False


# ══════════════════════════════ A. 格式校验 ══════════════════════════════
print("\nA. 版本号格式校验（严格三段）")

for good in ["1.6.0", "1.5.51", "2.0.0", "1.10.3", "10.0.0", "1.6.1"]:
    check(f"合法：{good}", is_valid_version(good))

bad_cases = [
    ("v1.6.0", "带 v 前缀"),
    ("1.6", "只有两段"),
    ("1.6.0.1", "四段"),
    ("1.4.20260623", "日期当版本号"),
    ("1.6.01", "修订号前导零"),
    ("01.6.0", "主版本前导零"),
    ("1.5.1000", "修订号超过 3 位"),
    ("1.6.0-beta", "带后缀"),
    ("", "空字符串"),
    ("1.6.0 ", "带空格"),
]
for bad, why in bad_cases:
    check(f"非法：{bad!r}（{why}）", not is_valid_version(bad))

check("VERSION 常量本身符合规范", is_valid_version(VERSION), VERSION)
check("版本号无前导零（逐段）",
      all(seg == str(int(seg)) for seg in VERSION.split(".")))
check("version_info 结构正确",
      version_info()["tag"] == f"v{VERSION}" and version_info()["valid"] is True)


# ══════════════════════════════ B. 比较规则与历史倒挂 ══════════════════════════════
print("\nB. 版本比较（按段位数值，非字符串）")

check("1.6.0 < 1.7.0", compare_versions("1.6.0", "1.7.0") == 1)
check("1.6.1 < 1.7.0", compare_versions("1.6.1", "1.7.0") == 1)
check("1.6.9 < 1.6.10（数值比较，不是字符串）",
      compare_versions("1.6.9", "1.6.10") == 1)
check("1.6.0 > 1.5.51（新序列高于旧序列，用户能收到更新）",
      compare_versions("1.5.51", "1.6.0") == 1)
check("相同版本 = 0", compare_versions("1.6.0", "1.6.0") == 0)
check("本地更新时返回 -1", compare_versions("1.6.1", "1.6.0") == -1)
check("段数不足补 0：1.6 == 1.6.0", compare_versions("1.6", "1.6.0") == 0)
check("兼容历史 tag：1.4.20260623 仍可比较",
      compare_versions("1.4.20260623", "1.5.0") == 1)

# 历史事故固化：这条断言是"为什么要立规范"的证据，不要删
check("⚠ 历史倒挂证据：旧写法下 1.5.23 被判为比 1.5.3 新（规范禁止此写法）",
      compare_versions("1.5.3", "1.5.23") == 1)
check("⚠ 历史倒挂证据：1.5.46 被判为比 1.5.5 新",
      compare_versions("1.5.5", "1.5.46") == 1)
check("规范写法下不会倒挂：1.5.5 -> 1.5.6 方向正确",
      compare_versions("1.5.5", "1.5.6") == 1)


# ══════════════════════════════ C. 升号计算规则 ══════════════════════════════
print("\nC. 升号计算（每次只 +1，后段归零）")

check("patch: 1.5.51 -> 1.5.52", bump_version.next_version("1.5.51", "patch") == "1.5.52")
check("minor: 1.5.51 -> 1.6.0（修订号归零）",
      bump_version.next_version("1.5.51", "minor") == "1.6.0")
check("major: 1.5.51 -> 2.0.0（后两段归零）",
      bump_version.next_version("1.5.51", "major") == "2.0.0")
check("minor: 1.6.7 -> 1.7.0", bump_version.next_version("1.6.7", "minor") == "1.7.0")
check("升号结果永远合法",
      all(is_valid_version(bump_version.next_version("1.5.51", k))
          for k in ("patch", "minor", "major")))

# 位数自然进位：1.6.9 之后就是 1.6.10，不需要"控制"位数，但绝不能补零
check("自然进位：1.6.9 -> 1.6.10",
      bump_version.next_version("1.6.9", "patch") == "1.6.10")
check("自然进位：1.6.99 -> 1.6.100",
      bump_version.next_version("1.6.99", "patch") == "1.6.100")
check("位数上限是防错网：1.6.999 合法、1.6.1000 非法",
      is_valid_version("1.6.999") and not is_valid_version("1.6.1000"))
check("禁补零：1.6.09 非法，且与 1.6.9 解析结果相同（会被当成同一版）",
      not is_valid_version("1.6.09")
      and parse_version("1.6.09") == parse_version("1.6.9"))
check("丢点残网：1.6.1 误写成 1.6.123 被跳号规则拦住",
      raises(SystemExit, bump_version.validate_target, "1.6.1", "1.6.123", False))

check("目标非法格式被拒（1.6.0.1）",
      raises(SystemExit, bump_version.validate_target, "1.5.51", "1.6.0.1", False))
check("目标非法格式被拒（日期当号）",
      raises(SystemExit, bump_version.validate_target, "1.5.51", "1.4.20260623", False))
check("版本号倒着走被拒",
      raises(SystemExit, bump_version.validate_target, "1.6.0", "1.5.9", False))
check("同版本号被拒",
      raises(SystemExit, bump_version.validate_target, "1.6.0", "1.6.0", False))
check("修订号跳号被拒（1.6.0 -> 1.6.9）",
      raises(SystemExit, bump_version.validate_target, "1.6.0", "1.6.9", False))
check("跳号加 --force 放行（但会给警告）",
      len(bump_version.validate_target("1.6.0", "1.6.9", True)) == 1)
check("正常 +1 无警告",
      bump_version.validate_target("1.6.0", "1.6.1", False) == [])
check("跨次版本升号不算跳号（1.6.9 -> 1.7.0）",
      bump_version.validate_target("1.6.9", "1.7.0", False) == [])


# ══════════════════════════════ D. 文件同步（临时副本上演练） ══════════════════════════════
print("\nD. 升号工具的四处同步（在临时副本上，不碰真实仓库）")

tmp = tempfile.mkdtemp(prefix="chemcal_ver_")
open(os.path.join(tmp, "version.py"), "w", encoding="utf-8").write(
    '"""fake"""\nVERSION = "1.6.0"\n')
open(os.path.join(tmp, "ChemCal.iss"), "w", encoding="utf-8").write(
    '#define MyAppVersion "1.6.0"\n')
open(os.path.join(tmp, "README.md"), "w", encoding="utf-8").write(
    '# T\n<img alt="version" src="https://img.shields.io/badge/version-1.6.0-green">\n\n'
    '## 更新日志\n\n### v1.6.0 (2026-01-01)\n\n- 旧条目\n')

# dry-run 不得改文件
before = open(os.path.join(tmp, "version.py"), encoding="utf-8").read()
res_dry = bump_version.bump("patch", "试跑", dry=True, root=tmp)
check("dry-run 返回目标版本", res_dry["to"] == "1.6.1" and res_dry["dry"] is True)
check("dry-run 不写文件",
      open(os.path.join(tmp, "version.py"), encoding="utf-8").read() == before)

res = bump_version.bump("patch", "修复示例问题", root=tmp)
check("升号结果 1.6.0 -> 1.6.1", res["from"] == "1.6.0" and res["to"] == "1.6.1")

vpy = open(os.path.join(tmp, "version.py"), encoding="utf-8").read()
iss = open(os.path.join(tmp, "ChemCal.iss"), encoding="utf-8").read()
rdm = open(os.path.join(tmp, "README.md"), encoding="utf-8").read()

check("version.py 已更新", 'VERSION = "1.6.1"' in vpy, vpy.strip())
check("ChemCal.iss AppVersion 已更新", '#define MyAppVersion "1.6.1"' in iss, iss)
check("README 徽章已更新", "badge/version-1.6.1-green" in rdm)
check("README 插入了新更新日志条目", "### v1.6.1 (" in rdm)
check("README 新条目含说明文字", "修复示例问题" in rdm)
check("README 新条目排在旧条目之上",
      rdm.index("### v1.6.1 ") < rdm.index("### v1.6.0 "))
check("旧条目未被破坏", "### v1.6.0 (2026-01-01)" in rdm)
check("同步清单包含三处", len(res["changed"]) >= 3, res["changed"])

# 重复升同一号不应产生重复条目
bump_version.bump("patch", "第二次", root=tmp)
rdm2 = open(os.path.join(tmp, "README.md"), encoding="utf-8").read()
check("重复执行不产生重复条目（v1.6.2 只出现一次）",
      rdm2.count("### v1.6.2 ") == 1)
check("version.py 二次升号 -> 1.6.2", 'VERSION = "1.6.2"' in
      open(os.path.join(tmp, "version.py"), encoding="utf-8").read())


# ══════════════════════════════ E. 真实仓库一致性 ══════════════════════════════
print("\nE. 真实仓库一致性（三处版本号必须一致）")

real_iss = open(os.path.join(PROJ, "ChemCal.iss"), encoding="utf-8").read()
m = re.search(r'#define MyAppVersion "([^"]+)"', real_iss)
check("ChemCal.iss AppVersion 存在", m is not None)
check(f"ChemCal.iss 版本号 == version.py（{VERSION}）", m and m.group(1) == VERSION,
      m.group(1) if m else "未找到")

real_readme = open(os.path.join(PROJ, "README.md"), encoding="utf-8").read()
mb = re.search(r"badge/version-([0-9.]+)-", real_readme)
check("README 徽章存在", mb is not None)
check(f"README 徽章版本 == version.py（{VERSION}）", mb and mb.group(1) == VERSION,
      mb.group(1) if mb else "未找到")
check("README 说明了版本规范", "VERSIONING.md" in real_readme)
check("README 更新日志含当前版本条目",
      f"### v{VERSION} " in real_readme or f"### v{VERSION}(" in real_readme)

real_main = open(os.path.join(PROJ, "main.py"), encoding="utf-8").read()
check("main.py 不再手写逐版本更新日志（避免多处重复必然过期）",
      "<b>v1.5.50</b>" not in real_main and "<b>v1.4</b>" not in real_main)
check("main.py 使用完整版本号（不再截断成主版本）",
      "setApplicationVersion(CHEMICAL_VERSION)" in real_main)

check("version.py 存在（唯一手写版本号处）",
      os.path.exists(os.path.join(PROJ, "version.py")))
check("VERSIONING.md 存在（规范文档）",
      os.path.exists(os.path.join(PROJ, "VERSIONING.md")))
check("bump_version.py 存在（升号工具）",
      os.path.exists(os.path.join(PROJ, "bump_version.py")))

# 单一实现：更新器复用 version.py 的解析函数，不再各写一份
check("updater.parse_version 就是 version.parse_version（无重复实现）",
      __import__("updater").parse_version is version_mod.parse_version)

# ══════════════════════════════ 汇总 ══════════════════════════════
print()
print("=" * 60)
print(f"总结: {PASS} 过, {FAIL} 失败")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
