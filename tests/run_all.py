# -*- coding: utf-8 -*-
"""一次跑完所有测试 —— 发版闸门（本机与 GitHub Actions 共用）

用法：
    .venv/Scripts/python.exe tests/run_all.py                    # 全部跑
    .venv/Scripts/python.exe tests/run_all.py test_reference.py  # 只跑指定的

为什么要有这个脚本（而不是在终端里一条条敲）：
  1. 每个测试文件都会各自开 QApplication，在同一个进程里连着跑会互相污染
     （Qt 全局状态、QSettings、各种单例），所以每个文件起独立子进程，互不干扰。
  2. 离屏跑 GUI 必须设 QT_QPA_PLATFORM=offscreen，不设就找不到显示器直接失败。
  3. 输出里有 ✓ ✗ 这类符号，Windows 下被别的工具转手调起时 stdout 常是 GBK
     管道 —— 不强制 UTF-8 会在打印报告时直接 UnicodeEncodeError 崩掉。
     顺带落一份到 tests/_last_run.txt（Windows 下 stdout 经常拿不到内容，落盘再读才可靠）。

之所以放在 tests/ 而**不是** .workbuddy/（那里虽也有一份 run_tests.py）：
  .workbuddy/ 整个目录在 .gitignore 里，云端 checkout 后根本不存在 ——
  所以 GitHub Actions 的打包前自检只认这个入库的版本。

退出码：全绿 0，有失败 1。
"""
import glob
import os
import subprocess
import sys
import time

# 输出里有 ✓ ✗ 这类符号，Windows 下被别的工具转手调起时 stdout 常是 GBK 管道 ——
# 不强制 UTF-8 会在 print 报告时直接崩，连 _last_run.txt 都来不及写。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPORT = os.path.join(HERE, "_last_run.txt")


def discover():
    """按文件名排序收集 tests/test_*.py（加测试文件不用改这里）。"""
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "test_*.py")))


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("-")]
    files = names or discover()

    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")   # 中文不设会渲染成方块
    env["PYTHONIOENCODING"] = "utf-8"

    lines, failed = [], []
    for name in files:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            lines.append(f"!! 找不到 {name}\n")
            failed.append(name)
            continue
        t0 = time.time()
        r = subprocess.run([sys.executable, path], cwd=ROOT, env=env, capture_output=True)
        out = r.stdout.decode("utf-8", "replace")
        err = r.stderr.decode("utf-8", "replace")
        tail = [ln for ln in out.strip().splitlines() if ln.strip()][-2:]
        lines.append(f"--- {name}  rc={r.returncode}  {time.time() - t0:.1f}s")
        lines.extend("    " + ln for ln in tail)
        if r.returncode != 0:
            failed.append(name)
            # 失败时把带 ✗ / FAIL 的行挑出来，省得翻整份输出
            for ln in out.strip().splitlines():
                if "✗" in ln or "FAIL" in ln:
                    lines.append("    " + ln)
            if err.strip():
                lines.append("    stderr: " + err.strip()[-1500:])
        lines.append("")

    text = "\n".join(lines)
    print(text)
    total = f"合计 {len(files)} 个测试文件，失败 {len(failed)} 个" + \
            (f"：{', '.join(failed)}" if failed else " —— 全部通过 ✅")
    print(total)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(text + "\n" + total + "\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
