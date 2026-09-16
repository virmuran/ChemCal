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
    download_update, DownloadIncomplete, human_size, _file_magic_ok,
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


ASSET_SIZE = 52950018      # 真实资产大小（ChemCal_1.6.0_setup.exe）


def make_release(tag, assets, body="notes"):
    return {
        "tag_name": tag,
        "body": body,
        "html_url": f"https://github.com/virmuran/ChemCal/releases/tag/{tag}",
        "assets": [{"name": n, "size": ASSET_SIZE,
                    "browser_download_url": f"https://example/{n}"}
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

# ══════════════ E. 下载完整性：网络截断 + 断点续传（loopback，无需外网）══════════════
# 2026-09-16 用户实测：自动升级下到 52 428 800 字节（正好 50 MiB）就被掐断，
# 拿到的是完整安装包的逐字节前缀，安装向导一跑就报 "The setup files are corrupted"。
# 根因在网络出口，但 updater 当时没有完整性校验——残缺文件被当成功交付。
# 下面用本地 HTTP 服务复现"截断 + 支持 Range"的代理行为。
import hashlib                                                         # noqa: E402
import tempfile                                                        # noqa: E402
import threading                                                       # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer    # noqa: E402

print("\nE. 下载完整性校验与断点续传")

PAYLOAD = b"MZ" + bytes(range(256)) * 400          # 102 402 字节，头部是合法 PE 魔术字节
CUT = 40000                                        # 首次响应只发这么多（模拟被掐断）


class _Handler(BaseHTTPRequestHandler):
    """按模式模拟网络出口行为。"""

    mode = "truncate"          # truncate=截断但支持续传 / norange=不支持续传 / html=返回错误页
    hits = []                  # 记录每次请求的 Range 头

    def log_message(self, *a):
        pass

    def do_GET(self):
        type(self).hits.append(self.headers.get("Range"))
        rng = self.headers.get("Range")
        start = 0
        if rng and self.mode != "norange":
            start = int(rng.split("=")[1].split("-")[0])

        if self.mode == "html":
            body = b"<html><body>403 Forbidden</body></html>"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        rest = PAYLOAD[start:]
        # 每次响应最多再发 CUT 字节（模拟固定上限）；支持续传时返回 206
        chunk = rest[:CUT]
        if rng and self.mode != "norange":
            self.send_response(206)
            self.send_header("Content-Range",
                             f"bytes {start}-{start + len(chunk) - 1}/{len(PAYLOAD)}")
        else:
            self.send_response(200)
        self.send_header("Content-Length", str(len(chunk)))
        self.end_headers()
        self.wfile.write(chunk)


srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"


def fresh(name):
    return os.path.join(tempfile.mkdtemp(), name)


# E1. 截断 → 自动续传 → 文件与源逐字节一致
_Handler.mode = "truncate"
_Handler.hits = []
dl = fresh("ChemCal_1.6.0_setup.exe")
prog = []
r = download_update(f"{BASE}/x/ChemCal_1.6.0_setup.exe", dl,
                    progress_callback=lambda d, t: prog.append((d, t)),
                    expected_size=len(PAYLOAD), retries=4)
_blob = open(dl, "rb").read()
check("E1 被截断的下载能自动续传补齐（多轮 Range 拼接）", _blob == PAYLOAD,
      f"got {len(_blob)} / want {len(PAYLOAD)}")
check("E1 确实发生了多次请求（第一次被截断，后续带 Range）", len(_Handler.hits) >= 2,
      _Handler.hits)
check("E1 续传请求带了 Range 头", any(h for h in _Handler.hits), _Handler.hits)
check("E1 首次请求无 Range（从头下）", _Handler.hits[0] is None, _Handler.hits)
check("E1 文件大小 = 期望值", os.path.getsize(dl) == len(PAYLOAD))
_last = prog[-1][0] if prog else 0
check("E1 进度回调最终值 = 文件总大小（不是单次响应大小）",
      _last == len(PAYLOAD), f"{_last} vs {len(PAYLOAD)}")

# E2. 残件续传：已存在的半截文件不会被白白重下
_Handler.hits = []
dl2 = fresh("ChemCal_1.6.0_setup.exe")
open(dl2, "wb").write(PAYLOAD[:CUT])               # 预置上次留下的残件
r = download_update(f"{BASE}/x/setup.exe", dl2, expected_size=len(PAYLOAD), retries=4)
check("E2 从已有残件续传，结果仍逐字节一致", open(dl2, "rb").read() == PAYLOAD)
check("E2 首个请求就带 Range（断点续传，不重头下）",
      _Handler.hits and _Handler.hits[0] == f"bytes={CUT}-", _Handler.hits)

# E3. 服务器不支持续传 → 明确报错，绝不返回残缺文件
_Handler.mode = "norange"
dl3 = fresh("ChemCal_1.6.0_setup.exe")
try:
    download_update(f"{BASE}/x/setup.exe", dl3, expected_size=len(PAYLOAD), retries=2)
    _e3 = None
except DownloadIncomplete as e:
    _e3 = e
check("E3 无法补齐时抛 DownloadIncomplete（不静默交付残缺文件）",
      _e3 is not None, _e3)
check("E3 报错文案里带上了「只收到多少 / 期望多少」",
      _e3 is not None and "截断" in str(_e3) and "," in str(_e3), _e3)

# E4. 响应被换成错误页（HTML）→ 文件头校验拦住
_Handler.mode = "html"
dl4 = fresh("ChemCal_1.6.0_setup.exe")
try:
    download_update(f"{BASE}/x/setup.exe", dl4, retries=1)     # expected=0，靠文件头兜底
    _e4 = None
except DownloadIncomplete as e:
    _e4 = e
check("E4 返回 HTML 错误页时被文件头校验拦住", _e4 is not None, _e4)
check("E4 报错点明不是有效的 exe/zip",
      _e4 is not None and "文件头" in str(_e4), _e4)

srv.shutdown()

# E5. 文件头校验单元锚点
_fd, _fp = tempfile.mkstemp(suffix=".exe")
os.write(_fd, b"MZ\x90\x00rest")
os.close(_fd)
check("E5 exe 魔术字节 MZ 判定通过", _file_magic_ok(_fp))
with open(_fp, "wb") as f:
    f.write(b"<html>not an installer</html>")
check("E5 HTML 内容冒充 exe 判定失败", not _file_magic_ok(_fp))
_fz = _fp[:-4] + ".zip"
with open(_fz, "wb") as f:
    f.write(b"PK\x03\x04xxxx")
check("E5 zip 魔术字节 PK\\x03\\x04 判定通过", _file_magic_ok(_fz))
check("E5 未知扩展名不做魔术字节校验（放行）", _file_magic_ok(_fp[:-4] + ".txt"))

# E6. 大小可读化
check("E6 human_size(52950018) = 50.5 MB", human_size(52950018) == "50.5 MB",
      human_size(52950018))
check("E6 human_size(0) 不崩", human_size(0) == "0 B", human_size(0))
check("E6 human_size(None) 返回「未知大小」", human_size(None) == "未知大小")

# E7. 检测更新时记下资产大小（供下载后比对）
has, latest, url, notes = with_release("v1.6.0", ["ChemCal_1.6.0_setup.exe"], "1.5.51")
check("E7 check_for_updates 记下 asset_size", get_last_check().get("asset_size") == ASSET_SIZE,
      get_last_check().get("asset_size"))

# ══════════════════════════════ 汇总 ══════════════════════════════
print()
print("=" * 60)
print(f"总结: {PASS} 过, {FAIL} 失败")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
