# -*- coding: utf-8 -*-
"""
自动更新器回归测试（纯逻辑，无需 Qt / 无需联网）

2026-09-15 修复两个问题后固化锚点：
  ① 版本号只认 Release 的 **tag**：资产名写 1.5.51、tag 仍是 v1.5.50 时，
     客户端拉到 tag=1.5.50 认为"已是最新"，更新永远弹不出来（实际踩到）。
  ② 自动更新的落地动作必须按资产类型分流：安装包只能"启动安装向导"，
     绝不能把 setup.exe 改名成 ChemCal.exe 替换主程序。

运行：
    .venv/Scripts/python.exe tests/test_updater.py
"""
import json
import os
import sys
import urllib.error

PROJ = r"C:\Users\Administrator\Desktop\ChemCal"
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

import updater
from updater import (
    parse_version, compare_versions, classify_asset, is_installer_asset,
    extract_asset_version, _pick_asset, check_for_updates, create_update_bat,
    get_last_check, get_temp_dir, LAST_CHECK,
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


# ---------------------------------------------------------------- 假 GitHub 响应

class _Resp:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def make_release(tag, assets, body="notes"):
    return {
        "tag_name": tag,
        "body": body,
        "html_url": f"https://github.com/virmuran/ChemCal/releases/tag/{tag}",
        "assets": [{"name": n, "browser_download_url": f"https://example/{n}"}
                   for n in assets],
    }


def with_release(tag, assets, current, exc=None):
    """在指定本地版本下跑一次 check_for_updates（替换 urlopen），返回四元组"""
    old_open, old_ver = updater.urllib.request.urlopen, updater.VERSION

    def _fake(req, timeout=None):
        if exc is not None:
            raise exc
        return _Resp(make_release(tag, assets))

    updater.urllib.request.urlopen = _fake
    updater.VERSION = current
    try:
        return check_for_updates()
    finally:
        updater.urllib.request.urlopen = old_open
        updater.VERSION = old_ver


# ══════════════════════════════ A. 版本比较 ══════════════════════════════
print("\nA. 版本号解析与比较")
check("parse_version('1.5.51') -> (1,5,51)", parse_version("1.5.51") == (1, 5, 51))
check("parse_version('v1.5.51') 去 v 前缀", parse_version("v1.5.51") == (1, 5, 51))
check("parse_version('1.4.20260623') -> (1,4,20260623)",
      parse_version("1.4.20260623") == (1, 4, 20260623))
check("compare 1.5.50 vs 1.5.51 -> 1(有新版本)",
      compare_versions("1.5.50", "1.5.51") == 1)
check("compare 1.5.51 vs 1.5.50 -> -1(本地更新)",
      compare_versions("1.5.51", "1.5.50") == -1)
check("compare 1.5.51 vs 1.5.51 -> 0", compare_versions("1.5.51", "1.5.51") == 0)
check("逐段数值比较(非字符串)：1.5.5 旧于 1.5.50（5 < 50）",
      compare_versions("1.5.5", "1.5.50") == 1)
check("段数不足补 0：1.5 == 1.5.0", compare_versions("1.5", "1.5.0") == 0)

# ══════════════════════════════ B. 资产识别 ══════════════════════════════
print("\nB. 资产类型识别")
check("setup.exe 判定为安装包", is_installer_asset("ChemCal_1.5.51_setup.exe"))
check("portable.zip 不是安装包", not is_installer_asset("ChemCal_1.5.51_portable.zip"))
check("裸 ChemCal.exe 不是安装包", not is_installer_asset("ChemCal.exe"))
check("classify setup -> installer",
      classify_asset("ChemCal_1.5.51_setup.exe") == "installer")
check("classify zip -> portable",
      classify_asset("ChemCal_1.5.51_portable.zip") == "portable")
check("classify 裸 exe -> file", classify_asset("ChemCal.exe") == "file")
check("classify 历史资产 CalcE.v1.3.exe -> file",
      classify_asset("CalcE.v1.3.exe") == "file")
check("从资产名提取版本 ChemCal_1.5.51_setup.exe -> 1.5.51",
      extract_asset_version("ChemCal_1.5.51_setup.exe") == "1.5.51")
check("资产名无版本号返回空串", extract_asset_version("ChemCal.exe") == "")

pick = _pick_asset(make_release("v1.5.51", ["ChemCal_1.5.51_portable.zip",
                                            "ChemCal_1.5.51_setup.exe"]))
check("资产挑选：安装包优先于便携 zip", pick.get("name") == "ChemCal_1.5.51_setup.exe",
      pick.get("name"))
pick2 = _pick_asset(make_release("v1.5.51", ["ChemCal_1.5.51_setup.exe",
                                             "ChemCal_macos_setup.exe"]))
check("资产挑选：排除 mac/linux 包", pick2.get("name") == "ChemCal_1.5.51_setup.exe")
pick3 = _pick_asset(make_release("v1.5.51", ["ChemCal_1.5.51_portable.zip"]))
check("资产挑选：只有 zip 时选 zip", pick3.get("name") == "ChemCal_1.5.51_portable.zip")
check("资产挑选：无资产返回空 dict",
      _pick_asset({"assets": []}) == {})

# ══════════════════════════ C. 本次 bug 的核心场景 ══════════════════════════
print("\nC. 更新检测（tag 才是版本号来源）")
ASSETS_151 = ["ChemCal_1.5.51_portable.zip", "ChemCal_1.5.51_setup.exe"]

# 用户实际踩到的：Release 的 tag 写成 v1.5.50，资产却是 1.5.51
has, latest, url, notes = with_release("v1.5.50", ASSETS_151, "1.5.50")
check("① 复现场景：tag=v1.5.50 + 资产1.5.51 + 本地1.5.50 -> 检测不到更新",
      has is False, f"has={has} latest={latest}")
info = get_last_check()
check("① 但 LAST_CHECK 记下 tag=v1.5.50", info.get("tag") == "1.5.50", info.get("tag"))
check("① 并标记 version_mismatch=True（可据此提示用户改 tag）",
      info.get("version_mismatch") is True, info)
check("① 不一致时 asset_version=1.5.51", info.get("asset_version") == "1.5.51")

# tag 修正为 v1.5.51 后应当正常检出
has, latest, url, notes = with_release("v1.5.51", ASSETS_151, "1.5.50")
check("② tag 改为 v1.5.51 后：本地 1.5.50 能检出更新", has is True)
check("② 返回的远端版本号 = 1.5.51", latest == "1.5.51", latest)
check("② 下载地址指向 setup.exe（自动更新走安装向导）",
      url.endswith("ChemCal_1.5.51_setup.exe"), url)
check("② 更新日志透传 release body", notes == "notes")
check("② 一致时 version_mismatch=False",
      get_last_check().get("version_mismatch") is False)
check("② asset_kind=installer", get_last_check().get("asset_kind") == "installer")

has, latest, *_ = with_release("v1.5.51", ASSETS_151, "1.5.51")
check("③ 同版本不提示更新", has is False)
has, latest, *_ = with_release("v1.5.51", ASSETS_151, "1.5.52")
check("④ 开发版(1.5.52)高于发布版(1.5.51) 不提示", has is False)
has, latest, *_ = with_release("v1.4.20260623", ["ChemCal.exe"], "1.5.50")
check("⑤ 旧 tag 格式 1.4.20260623 正确识别为更旧", has is False)

has, latest, url, notes = with_release("v1.5.51", ASSETS_151, "1.5.50",
                                      exc=urllib.error.URLError("boom"))
check("⑥ 网络失败返回提示文案（不静默当成最新）",
      has is False and notes == "网络连接失败，请检查网络", notes)
check("⑥ 网络失败时 LAST_CHECK 为空（不会残留上次的 tag）",
      get_last_check() == {}, get_last_check())

# ══════════════════════════════ D. 安装脚本分流 ══════════════════════════════
print("\nD. 落地动作按资产类型分流")
tmpdir = get_temp_dir()
setup_path = os.path.join(tmpdir, "ChemCal_1.5.51_setup.exe")
bat_i = create_update_bat(setup_path, r"C:\Program Files\ChemCal", kind="installer")
content_i = open(bat_i, encoding="utf-8").read()
check("安装包脚本：不含 move /Y（不得覆盖主程序）", "move /Y" not in content_i)
check("安装包脚本：不出现 ChemCal.exe 覆盖动作", "ChemCal.exe" not in content_i)
check("安装包脚本：启动的是下载下来的 setup.exe", setup_path in content_i)
check("安装包脚本：等待主程序退出后再启动", "ping 127.0.0.1" in content_i)
check("安装包脚本：CRLF 行尾（二进制读，文本模式会把 \\r\\n 归一化）",
      b"\r\n" in open(bat_i, "rb").read())

bat_f = create_update_bat(os.path.join(tmpdir, "ChemCal.exe"),
                          r"C:\Program Files\ChemCal", kind="file")
content_f = open(bat_f, encoding="utf-8").read()
check("单文件脚本：保留 move /Y 覆盖 ChemCal.exe",
      "move /Y" in content_f and "ChemCal.exe" in content_f)

bat_a = create_update_bat(setup_path, r"C:\Program Files\ChemCal")   # 不传 kind，按名自动判断
check("不传 kind 时按文件名自动识别为安装包",
      "move /Y" not in open(bat_a, encoding="utf-8").read())

check("get_temp_dir 可写", os.path.isdir(tmpdir) and os.access(tmpdir, os.W_OK), tmpdir)

# ══════════════════════════════ 汇总 ══════════════════════════════
print()
print("=" * 60)
print(f"总结: {PASS} 过, {FAIL} 失败")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
