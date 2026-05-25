# ChemCal/crash_shield.py
"""
全局防闪退保护层
- faulthandler: 在 C 级段错误时输出 Python traceback
- sys.excepthook: 捕获所有未处理的 Python 异常
- SafeApplication: 自定义 QApplication，捕获 Qt 事件处理链中的异常
- 自动保存崩溃日志到 ~/.calce/crashes/
"""

import sys
import os
import traceback
import faulthandler
from datetime import datetime

# ── 1. 启用 faulthandler（段错误时输出 traceback 到 stderr 和崩溃日志） ──
_CRASH_DIR = os.path.join(os.path.expanduser("~"), ".calce", "crashes")
os.makedirs(_CRASH_DIR, exist_ok=True)

# 将 faulthandler 输出定向到崩溃日志文件
_fault_log_path = os.path.join(_CRASH_DIR, "faulthandler.log")
try:
    with open(_fault_log_path, "a") as f:
        faulthandler.enable(file=f, all_threads=True)
except Exception:
    faulthandler.enable(all_threads=True)


# ── 2. 崩溃日志写入 ──

def write_crash_log(exc_type, exc_value, exc_tb):
    """将异常信息写入崩溃日志文件，返回文件路径"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    crash_file = os.path.join(_CRASH_DIR, f"crash_{ts}.log")
    try:
        with open(crash_file, "w", encoding="utf-8") as f:
            f.write(f"=== ChemCal Crash Report ===\n")
            f.write(f"Time: {datetime.now().isoformat()}\n")
            f.write(f"Exception Type: {exc_type.__name__}\n")
            f.write(f"Exception Value: {exc_value}\n")
            f.write("Traceback:\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass
    return crash_file


def _safe_show_crash_message(exc_type_name, exc_value, crash_file):
    """安全地显示崩溃弹窗（捕获 Qt 不可用的情况）"""
    try:
        from PySide6.QtWidgets import QMessageBox, QApplication
        app = QApplication.instance()
        if app is not None and not app.closingDown():
            QMessageBox.critical(
                None, "意外错误",
                f"程序遇到意外错误，已记录崩溃日志。\n\n"
                f"错误类型: {exc_type_name}\n"
                f"错误信息: {exc_value}\n\n"
                f"崩溃日志路径:\n{crash_file}\n\n"
                f"建议重启 ChemCal。"
            )
    except Exception:
        pass  # Qt 不可用时静默处理


def _safe_save_data():
    """尝试保存紧急数据"""
    try:
        from data_manager import DataManager
        dm = DataManager.get_instance()
        dm._save_data()
    except Exception:
        pass


# ── 3. sys.excepthook ──

def _global_excepthook(exc_type, exc_value, exc_tb):
    """全局未捕获异常处理"""
    # 跳过 KeyboardInterrupt
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    crash_file = write_crash_log(exc_type, exc_value, exc_tb)
    traceback.print_exception(exc_type, exc_value, exc_tb)
    _safe_save_data()
    _safe_show_crash_message(exc_type.__name__, str(exc_value), crash_file)


def _global_unraisablehook(unraisable):
    """处理不可抛出的异常（如析构函数、__del__ 中的异常）"""
    exc_type = unraisable.exc_type
    exc_value = unraisable.exc_value
    exc_tb = unraisable.exc_traceback
    if exc_type is not None:
        crash_file = write_crash_log(exc_type, exc_value, exc_tb)
        print(f"[crash_shield] Unraisable exception logged: {crash_file}", file=sys.stderr)
        _safe_save_data()


# ── 4. SafeApplication（轻量包装，不覆盖 notify） ──

class SafeApplication:
    """
    SafeApplication 轻量包装——替代 QApplication 的入口点。

    用法：
        app = SafeApplication(sys.argv)
        app.run()   # 替代 app.exec()

    注意：不覆盖 notify()，因为 PySide6 的类型检查会导致 QWidgetItem
    （非 QObject）被传递给 notify 时抛出 TypeError 并崩溃。
    异常捕获完全由 sys.excepthook / blockSignals 等机制处理。
    """

    def __init__(self, argv):
        from PySide6.QtWidgets import QApplication
        self._app = QApplication(argv)

    def __getattr__(self, name):
        return getattr(self._app, name)

    def run(self):
        """运行应用（替代 app.exec()）"""
        return self._app.exec()


# ── 5. 安装函数 ──

def install_crash_shield():
    """安装防闪退保护层（应在创建 QApplication 之前调用）"""
    sys.excepthook = _global_excepthook
    if hasattr(sys, "unraisablehook"):
        sys.unraisablehook = _global_unraisablehook
    print(f"[crash_shield] 防闪退保护层已安装")
    print(f"[crash_shield] 崩溃日志目录: {_CRASH_DIR}")
    print(f"[crash_shield] faulthandler 日志: {_fault_log_path}")
