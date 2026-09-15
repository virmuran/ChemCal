"""ChemCal 一键发版脚本
用法:  .venv/Scripts/python.exe build_release.py [--skip-build]
流程:  同步版本号 -> PyInstaller onedir -> Inno Setup 安装包 -> 便携 zip
产物:  installer/ChemCal_<版号>_setup.exe
       dist/ChemCal_<版号>_portable.zip
发新版前只需改 version.py，其余全自动。
"""
import os
import re
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

ISCC = r"C:\Program Files\Inno Setup 7\ISCC.exe"


def step(msg):
    print(f"\n=== {msg} ===", flush=True)


def run(cmd):
    print("  $", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        sys.exit(f"步骤失败: {cmd[0]}")


def main():
    # 0) 版本号
    sys.path.insert(0, ROOT)
    from version import VERSION  # noqa: E402
    ver = VERSION
    print(f"ChemCal v{ver}")

    # 1) 同步 ChemCal.iss 的 AppVersion（防两处不同步）
    step("同步 ChemCal.iss 版本号")
    iss = os.path.join(ROOT, "ChemCal.iss")
    text = open(iss, encoding="utf-8").read()
    new = re.sub(r'#define MyAppVersion "[^"]*"', f'#define MyAppVersion "{ver}"', text)
    if new != text:
        open(iss, "w", encoding="utf-8").write(new)
        print(f"  ChemCal.iss AppVersion -> {ver}")
    else:
        print(f"  已一致: {ver}")

    # 2) PyInstaller onedir
    if "--skip-build" not in sys.argv:
        step("PyInstaller 打包（约 2~3 分钟）")
        run([os.path.join(ROOT, ".venv", "Scripts", "python.exe"),
             "-m", "PyInstaller", "ChemCal.spec", "--noconfirm"])

    # 3) Inno Setup 安装包
    step("Inno Setup 编译安装包")
    run([ISCC, "ChemCal.iss"])

    # 4) 便携 zip（ZIP_LZMA；勿用 bsdtar 默认 deflate，体积差 3 倍）
    step("制作便携 zip")
    src = os.path.join(ROOT, "dist", "ChemCal")
    out = os.path.join(ROOT, "dist", f"ChemCal_{ver}_portable.zip")
    if os.path.exists(out):
        os.remove(out)
    n = 0
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_LZMA, compresslevel=9) as z:
        for root, _dirs, files in os.walk(src):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, os.path.join(ROOT, "dist")))
                n += 1

    # 5) 汇总
    setup = os.path.join(ROOT, "installer", f"ChemCal_{ver}_setup.exe")
    mb = lambda p: round(os.path.getsize(p) / 1048576, 1)
    print("\n=== 打包完成 ===")
    print(f"  安装包  {setup}  ({mb(setup)} MB)")
    print(f"  便携包  {out}  ({mb(out)} MB, {n} 文件)")
    print("\n发布步骤:")
    print("  1. VS Code 提交并推送本次全部改动")
    print(f"  2. git tag v{ver} && git push origin v{ver}")
    print("  3. GitHub 仓库页 -> Releases -> Draft a new release")
    print(f"     选 tag v{ver}，标题 v{ver}，粘贴更新日志")
    print(f"     上传 installer/ChemCal_{ver}_setup.exe 和 dist/ChemCal_{ver}_portable.zip")
    print("  4. Publish release（发布后软件内自动更新即会提示新版本）")


if __name__ == "__main__":
    main()
