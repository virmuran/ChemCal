# ChemCal/launcher.py
"""
ChemCal 看门狗启动器

原理：将 ChemCal 作为子进程运行。当子进程因任何原因崩溃（包括 access violation、
segfault 等无法被 Python 捕获的 C 级错误）时，看门狗检测到非零退出码，
自动重启 ChemCal 并提示用户。

运行方式：
    python launcher.py

架构：
    launcher.py (看门狗进程，无 Qt 依赖，不易崩溃)
        │
        ├── subprocess.Popen → calc_main.py (ChemCal GUI)
        ├── wait → 等待子进程退出
        ├── exit_code == 0 → 用户正常关闭，看门狗也退出
        ├── exit_code != 0 → 崩溃检测：
        │   ├── 显示 Windows 消息框提示
        │   ├── 写崩溃日志
        │   ├── 检查重启频率（防无限循环）
        │   └── 自动重启 ChemCal
        └── 最多 3 次/5分钟，超限则停止
"""

import sys
import os
import subprocess
import time
import ctypes
from datetime import datetime, timedelta

# ── 配置 ──
MAX_RESTARTS = 3          # 5分钟内最多重启次数
WINDOW_SECONDS = 300      # 时间窗口（秒）
CRASH_DIR = os.path.join(os.path.expanduser("~"), ".ChemCal", "crashes")

# ── Windows API 消息框 ──
MB_OK = 0
MB_ICONWARNING = 0x00000030
MB_ICONERROR = 0x00000010
MB_ICONINFORMATION = 0x00000040

def _win_message_box(text, title, style=MB_OK | MB_ICONINFORMATION):
    """使用 Windows API 显示消息框（无 Qt 依赖）"""
    try:
        ctypes.windll.user32.MessageBoxW(0, text, title, style)
    except Exception:
        pass  # 无法显示消息框也就算了

def _write_launcher_log(message):
    """写看门狗自己的日志"""
    os.makedirs(CRASH_DIR, exist_ok=True)
    log_path = os.path.join(CRASH_DIR, "launcher.log")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass

def _find_main_script():
    """查找 main.py（和 launcher.py 同目录）"""
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, "main.py"),
        os.path.join(base, "calc_app.py"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]  # 默认返回 main.py

def run_watchdog():
    """看门狗主循环"""
    python_exe = sys.executable
    main_script = _find_main_script()
    crash_history = []  # [(timestamp, exit_code), ...]
    restart_count = 0

    _write_launcher_log(f"ChemCal 看门狗启动，主程序: {main_script}")

    while True:
        # ── 启动 ChemCal ──
        startup_msg = "正在启动 ChemCal..."
        if restart_count > 0:
            startup_msg = f"正在重启 ChemCal（第 {restart_count} 次）..."
        print(f"[launcher] {startup_msg}")

        try:
            process = subprocess.Popen(
                [python_exe, main_script],
                cwd=os.path.dirname(main_script),
                # 不继承父进程控制台，避免混乱
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
        except Exception as e:
            _write_launcher_log(f"启动 ChemCal 失败: {e}")
            _win_message_box(
                f"无法启动 ChemCal:\n{e}",
                "ChemCal 启动失败",
                MB_ICONERROR
            )
            return 1

        # ── 等待 ChemCal 退出 ──
        try:
            exit_code = process.wait()
        except Exception as e:
            _write_launcher_log(f"等待进程退出出错: {e}")
            exit_code = -1

        # ── 检查退出码 ──
        # 正常退出（exit code 0）
        if exit_code == 0:
            _write_launcher_log("ChemCal 正常退出")
            print("[launcher] ChemCal 正常退出")
            return 0

        # 用户通过 Ctrl+C 中断
        if exit_code == -1 or exit_code == 3221225786:  # 0xC000013A = Ctrl+C
            _write_launcher_log("ChemCal 被用户中断")
            return 0

        # ── 崩溃处理 ──
        now = datetime.now()
        crash_history.append((now, exit_code))
        # 清理 5 分钟前的记录
        crash_history = [(t, c) for t, c in crash_history
                         if (now - t).total_seconds() < WINDOW_SECONDS]
        restart_count = len(crash_history)

        # 检查崩溃频率
        if restart_count > MAX_RESTARTS:
            msg = (
                f"ChemCal 在短时间内连续崩溃 {restart_count} 次，"
                f"已停止自动重启。\n\n"
                f"请尝试：\n"
                f"1. 更新 ChemCal 到最新版本\n"
                f"2. 检查 ~/.ChemCal/crashes/ 中的崩溃日志\n"
                f"3. 联系开发者 virmuran@163.com"
            )
            _win_message_box(msg, "ChemCal 连续崩溃", MB_ICONERROR)
            _write_launcher_log(f"连续崩溃 {restart_count} 次，停止重启")
            return 1

        # ── 记录崩溃并重启 ──
        exit_code_str = f"0x{exit_code & 0xFFFFFFFF:08X}" if exit_code < 0 else str(exit_code)
        _write_launcher_log(f"ChemCal 崩溃 (exit code: {exit_code_str})，第 {restart_count} 次重启")

        # 显示重启提示
        _win_message_box(
            f"ChemCal 遇到意外错误，正在自动重启...\n"
            f"(第 {restart_count}/{MAX_RESTARTS} 次)\n\n"
            f"退出码: {exit_code_str}",
            "ChemCal",
            MB_ICONWARNING
        )

        # 短暂等待，避免立即重启时系统资源未释放
        time.sleep(1)


def main():
    """入口"""
    if sys.platform != "win32":
        print("[launcher] 看门狗启动器目前仅支持 Windows")
        return 1

    # 先显示一个提示
    print("=" * 50)
    print("  ChemCal 看门狗启动器")
    print("  崩溃后自动重启 (最多 3 次/5 分钟)")
    print("=" * 50)

    exit_code = run_watchdog()

    if exit_code != 0:
        input("\n按 Enter 键退出...")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
