"""
ChemCal 自动更新模块 — GitHub Releases API

用法：
    from updater import check_for_updates, download_update, create_update_bat, GITHUB_REPO

    has_update, version, url, notes = check_for_updates()
    if has_update:
        path = download_update(url, "new.exe", callback=progress_fn)
        bat = create_update_bat(path, app_dir)
        os.startfile(bat)  # 应用关闭后自动安装 / 替换

⚠ 版本号只认 Release 的 **tag**（形如 v1.5.51），资产文件名不参与比较。
   所以发版时 tag 必须与 version.py 完全一致：资产名写了 1.5.51、tag 仍写 v1.5.50，
   客户端拉到 tag=1.5.50 就认为"已是最新"，永远测不到更新。
   check_for_updates() 会把 tag / 资产名 / 是否不一致记进 LAST_CHECK，供界面提示。

版本号规范：**主版本.次版本.修订号**（如 1.6.0），详见 VERSIONING.md。
   解析函数对历史 tag 保持宽容（1.4.20260623 这类旧格式仍能比较），
   但新发布的版本号必须通过 version.is_valid_version() 校验。
"""

import json
import os
import re
import sys
import tempfile
import urllib.request

from version import VERSION, parse_version, compare_versions  # noqa: F401  (re-export)

GITHUB_REPO = "virmuran/ChemCal"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
USER_AGENT = f"ChemCal/{VERSION}"

# 最近一次 check_for_updates 的诊断信息（tag、资产名、是否 tag 与资产版本不一致）
LAST_CHECK = {}


# ------------------------------------------------------------------ 资产识别

# 发行资产分两类：安装包（Inno Setup 的 *_setup.exe，需运行安装）
# 与便携包（*_portable.zip，解压即用）。两者的升级动作完全不同，必须区分。
INSTALLER_HINTS = ("setup", "install", "installer")


def is_installer_asset(name: str) -> bool:
    """判断资产是否为安装包（Inno Setup 生成的 *setup.exe）。"""
    low = (name or "").lower()
    return low.endswith(".exe") and any(h in low for h in INSTALLER_HINTS)


def classify_asset(name: str) -> str:
    """资产类型：'installer'（安装包）/ 'portable'（便携 zip）/ 'file'（其他单文件）。"""
    low = (name or "").lower()
    if is_installer_asset(low):
        return "installer"
    if low.endswith(".zip"):
        return "portable"
    return "file"


def extract_asset_version(name: str) -> str:
    """从资产文件名里提取版本号：'ChemCal_1.5.51_setup.exe' → '1.5.51'。

    用于发现「tag 与资产文件名版本不一致」这类发布失误（客户端只认 tag）。
    """
    m = re.search(r"(\d+(?:\.\d+)+)", name or "")
    return m.group(1) if m else ""


def get_last_check() -> dict:
    """返回最近一次 check_for_updates 的诊断信息（副本）。"""
    return dict(LAST_CHECK)


def get_temp_dir() -> str:
    """返回一个确实可写的临时目录。

    受控电脑上 %TEMP% 常被 ACL 限制（安装时报"错误 5：拒绝访问"即此因），
    依次退到用户目录、当前目录，避免更新在下载/写脚本阶段就失败。
    """
    candidates = [tempfile.gettempdir(), os.path.expanduser("~"), os.getcwd()]
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, ".chemcal_write_test")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("")
            os.remove(probe)
            return d
        except Exception:
            continue
    return tempfile.gettempdir()


# ------------------------------------------------------------------ API 查询

def check_for_updates():
    """检查 GitHub Releases 是否有新版本。

    版本号取自 Release 的 tag（v 前缀自动去掉），与本地 VERSION 逐段比较。

    Returns:
        (has_update: bool, latest_version: str, download_url: str, release_notes: str)
        检查失败返回 (False, "", "", "错误说明")；无更新返回 (False, "", "", "")
        详细诊断见 get_last_check()
    """
    LAST_CHECK.clear()
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        latest_tag = data.get("tag_name", "").lstrip("v")
        asset = _pick_asset(data)
        asset_name = asset.get("name", "")
        asset_ver = extract_asset_version(asset_name)

        LAST_CHECK.update({
            "ok": True,
            "tag": latest_tag,
            "asset_name": asset_name,
            "asset_kind": classify_asset(asset_name),
            "asset_url": asset.get("browser_download_url", ""),
            "asset_version": asset_ver,
            # tag 与资产名版本不一致 = 发布配置错误，客户端只认 tag
            "version_mismatch": bool(asset_ver) and asset_ver != latest_tag,
        })

        if not latest_tag:
            return False, "", "", ""

        # 智能版本对比，支持 1.4.20260623 格式
        if compare_versions(VERSION, latest_tag) <= 0:
            return False, "", "", ""

        download_url = asset.get("browser_download_url", "") or data.get("html_url", "")
        release_notes = data.get("body", "")
        return True, latest_tag, download_url, release_notes

    except urllib.error.HTTPError as e:
        if e.code == 403:
            return False, "", "", "API 速率限制，请稍后再试"
        if e.code == 404:
            return False, "", "", "仓库暂无正式 Release（草稿/预发布不会被识别）"
        return False, "", "", f"网络错误 (HTTP {e.code})"
    except urllib.error.URLError:
        return False, "", "", "网络连接失败，请检查网络"
    except Exception as e:
        return False, "", "", f"检查失败: {e}"


def _pick_asset(data: dict) -> dict:
    """从 Release 资产列表中选出最合适的资产（返回资产 dict，无则空 dict）。

    优先：setup.exe（安装包）> 其他 exe > msi > zip，排除含 mac/linux 的。
    """
    assets = data.get("assets", [])
    if not assets:
        return {}

    # 优先级排序
    def score(name: str) -> int:
        low = name.lower()
        if any(kw in low for kw in ("mac", "macos", "linux", "ubuntu", "debian")):
            return -1          # 排除
        if is_installer_asset(low):
            return 110         # 安装包最优（自动更新走安装向导）
        if low.endswith(".exe"):
            return 100
        if low.endswith(".msi"):
            return 80
        if low.endswith(".zip"):
            return 60
        return 50              # 其他

    best = None
    best_score = -1
    for asset in assets:
        s = score(asset.get("name", ""))
        if s > best_score:
            best_score = s
            best = asset

    return best or {}


# ------------------------------------------------------------------ 下载

def download_update(url: str, save_path: str, progress_callback=None):
    """下载更新文件，支持进度回调。

    Args:
        url: 下载地址
        save_path: 保存路径（含文件名）
        progress_callback: fn(downloaded_bytes, total_bytes)，在下载线程中调用

    Returns:
        save_path — 下载完成后的文件路径

    Raises:
        urllib.error.URLError / HTTPError
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=600) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        block_size = 65536  # 64 KB
        with open(save_path, "wb") as f:
            while True:
                chunk = resp.read(block_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total > 0:
                    progress_callback(downloaded, total)
    return save_path


# ------------------------------------------------------------------ 安装（Windows 批处理）

def create_update_bat(new_file_path: str, target_dir: str, kind: str = "") -> str:
    """生成安装/替换用的批处理脚本，应用关闭后由它完成收尾。

    按资产类型分两条路：
      installer —— 下载的是 Inno 安装包，**只启动安装向导**，由安装向导覆盖升级
                   （绝不能把 setup.exe 改名成 ChemCal.exe，那会毁掉主程序）
      file      —— 历史发行的单文件 exe，直接 move 覆盖 ChemCal.exe 后重启

    Args:
        new_file_path: 已下载文件的完整路径
        target_dir: 应用程序所在目录
        kind: 'installer' / 'file'，留空则按文件名自动判断

    Returns:
        .bat 文件路径
    """
    if not kind:
        kind = classify_asset(os.path.basename(new_file_path))

    bat_path = os.path.join(get_temp_dir(), "ChemCal_update.bat")

    # CRLF 行尾（Windows 批处理要求）
    header = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "title ChemCal 自动更新\r\n"
        'echo ========================================\r\n'
    )

    if kind == "installer":
        content = (
            header
            + 'echo   ChemCal 更新安装包已下载完成\r\n'
            'echo   即将启动安装向导，请按提示完成升级...\r\n'
            'echo ========================================\r\n'
            "echo.\r\n"
            # 等待主程序完全退出，避免文件占用
            "ping 127.0.0.1 -n 4 >nul\r\n"
            f'start "" "{new_file_path}"\r\n'
            'del "%~f0"\r\n'
        )
        with open(bat_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        return bat_path

    target_exe = os.path.join(target_dir, "ChemCal.exe")
    content = (
        header
        + 'echo   ChemCal 自动更新中，请稍候...\r\n'
        'echo ========================================\r\n'
        "echo.\r\n"
        # 等待主程序完全退出
        "ping 127.0.0.1 -n 3 >nul\r\n"
        # 替换 exe
        f'move /Y "{new_file_path}" "{target_exe}"\r\n'
        "if %errorlevel% equ 0 (\r\n"
        "    echo 更新成功！正在启动 ChemCal...\r\n"
        f'    start "" "{target_exe}"\r\n'
        ") else (\r\n"
        "    echo.\r\n"
        "    echo 自动替换失败（程序目录可能需要管理员权限），请手动操作：\r\n"
        f'    echo 1. 将 "{new_file_path}" 复制到\r\n'
        f'    echo    "{target_dir}"\r\n'
        f'    echo 2. 运行 "{target_exe}"\r\n'
        "    echo.\r\n"
        "    pause\r\n"
        ")\r\n"
        'del "%~f0"\r\n'
    )

    with open(bat_path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

    return bat_path


# ------------------------------------------------------------------ 辅助

def is_frozen() -> bool:
    """判断当前是否运行在 PyInstaller 打包后的 exe 中。"""
    return getattr(sys, "frozen", False)


def get_app_dir() -> str:
    """获取应用程序所在目录。"""
    if is_frozen():
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))
