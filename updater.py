"""
ChemCal 自动更新模块 — GitHub Releases API

用法：
    from updater import check_for_updates, download_update, create_update_bat, GITHUB_REPO

    has_update, version, url, notes = check_for_updates()
    if has_update:
        path = download_update(url, "new.exe", callback=progress_fn)
        bat = create_update_bat(path, app_dir)
        os.startfile(bat)  # 应用关闭后自动替换

版本号格式：1.4.20260623（主.次.日期），支持任意多段数字对比
"""

import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

from version import VERSION

GITHUB_REPO = "virmuran/ChemCal"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
USER_AGENT = f"ChemCal/{VERSION}"


# ------------------------------------------------------------------ 版本工具

def parse_version(version_str: str) -> tuple:
    """将版本号字符串转为可比较的元组。

    '1.4.20260623' → (1, 4, 20260623)
    'v2.1.0'       → (2, 1, 0)
    非数字段转为 0，确保对比不崩溃
    """
    parts = version_str.strip().lstrip("v").split(".")
    return tuple(int(p) if p.isdigit() else 0 for p in parts)


def compare_versions(current_str: str, latest_str: str) -> int:
    """比较两个版本号：返回 -1(旧), 0(相同), 1(新)。

    逐段对比，段数不足时补 0。"""
    cur = parse_version(current_str)
    lat = parse_version(latest_str)
    # 补齐长度
    max_len = max(len(cur), len(lat))
    cur = cur + (0,) * (max_len - len(cur))
    lat = lat + (0,) * (max_len - len(lat))
    if lat > cur:
        return 1    # 有新版本
    elif lat < cur:
        return -1
    return 0


# ------------------------------------------------------------------ API 查询

def check_for_updates():
    """检查 GitHub Releases 是否有新版本。

    Returns:
        (has_update: bool, latest_version: str, download_url: str, release_notes: str)
        检查失败返回 (False, "", "", "")
    """
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        latest_tag = data.get("tag_name", "").lstrip("v")
        if not latest_tag:
            return False, "", "", ""

        # 智能版本对比，支持 1.4.20260623 格式
        if compare_versions(VERSION, latest_tag) <= 0:
            return False, "", "", ""

        # 查找最佳下载资产
        download_url = _pick_asset(data)
        if not download_url:
            download_url = data.get("html_url", "")

        release_notes = data.get("body", "")
        return True, latest_tag, download_url, release_notes

    except urllib.error.HTTPError as e:
        if e.code == 403:
            return False, "", "", "API 速率限制，请稍后再试"
        return False, "", "", f"网络错误 (HTTP {e.code})"
    except urllib.error.URLError:
        return False, "", "", "网络连接失败，请检查网络"
    except Exception as e:
        return False, "", "", f"检查失败: {e}"


def _pick_asset(data: dict) -> str:
    """从 Release 资产列表中选出最合适的下载链接。

    优先：exe > msi > zip，排除含 mac/linux 的。
    """
    assets = data.get("assets", [])
    if not assets:
        return ""

    # 优先级排序
    def score(name: str) -> int:
        low = name.lower()
        if any(kw in low for kw in ("mac", "macos", "linux", "ubuntu", "debian")):
            return -1          # 排除
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
        name = asset.get("name", "")
        s = score(name)
        if s > best_score:
            best_score = s
            best = asset.get("browser_download_url", "")

    return best or ""


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


# ------------------------------------------------------------------ 安装（Windows 批处理替换）

def create_update_bat(new_exe_path: str, target_dir: str) -> str:
    """生成自替换批处理脚本。

    应用关闭后运行此 .bat，将新 exe 替换旧 exe 并重新启动。

    Args:
        new_exe_path: 新下载的 .exe 文件完整路径
        target_dir: 应用程序所在目录

    Returns:
        .bat 文件路径
    """
    bat_path = os.path.join(tempfile.gettempdir(), "ChemCal_update.bat")
    target_exe = os.path.join(target_dir, "ChemCal.exe")

    # CRLF 行尾（Windows 批处理要求）
    bat_content = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "title ChemCal 自动更新\r\n"
        'echo ========================================\r\n'
        'echo   ChemCal 自动更新中，请稍候...\r\n'
        'echo ========================================\r\n'
        "echo.\r\n"
        # 等待主程序完全退出
        "ping 127.0.0.1 -n 3 >nul\r\n"
        # 替换 exe
        f'move /Y "{new_exe_path}" "{target_exe}"\r\n'
        "if %errorlevel% equ 0 (\r\n"
        "    echo 更新成功！正在启动 ChemCal...\r\n"
        f'    start "" "{target_exe}"\r\n'
        ") else (\r\n"
        "    echo.\r\n"
        "    echo 自动替换失败，请手动操作：\r\n"
        f'    echo 1. 将 "{new_exe_path}" 复制到\r\n'
        f'    echo    "{target_dir}"\r\n'
        f'    echo 2. 运行 "{target_exe}"\r\n'
        "    echo.\r\n"
        "    pause\r\n"
        ")\r\n"
        "del \"%~f0\"\r\n"
    )

    with open(bat_path, "w", encoding="utf-8", newline="") as f:
        f.write(bat_content)

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
