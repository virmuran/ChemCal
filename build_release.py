"""ChemCal 一键发版脚本
用法:  .venv/Scripts/python.exe build_release.py [--skip-build]
流程:  校验版本号 -> 同步版本号 -> PyInstaller onedir -> Inno Setup 安装包 -> 便携 zip
产物:  installer/ChemCal_<版号>_setup.exe
       dist/ChemCal_<版号>_portable.zip

升版本号请用 bump_version.py（不要手改 version.py）：
    .venv/Scripts/python.exe bump_version.py patch "修复 xxx"
版本规范见 VERSIONING.md。
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


def remote_health_check():
    """查询 GitHub 上的 Release，检查 tag 与资产文件名版本是否一致。

    自动更新只认 Release 的 tag：资产名写 1.5.51、tag 仍是 v1.5.50 时，
    所有老用户都会看到"已是最新版本"。此检查把这类失误直接指出来。
    """
    step("远端 Release 健康检查")
    import json
    import urllib.request

    from updater import extract_asset_version

    url = "https://api.github.com/repos/virmuran/ChemCal/releases"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ChemCal-build"})
        with urllib.request.urlopen(req, timeout=10) as r:
            rels = json.loads(r.read().decode())
    except Exception as e:
        print(f"  跳过（无法访问 GitHub API：{e}）")
        return

    for rel in rels[:5]:
        tag = rel.get("tag_name", "").lstrip("v")
        assets = rel.get("assets", [])
        if not extract_asset_version(tag):
            print(f"  · {rel.get('tag_name')}: 非版本号 tag（跳过一致性检查）")
            continue
        bad = []
        for a in assets:
            av = extract_asset_version(a.get("name", ""))
            if av and av != tag:
                bad.append(f"{a['name']}({av})")
        if bad:
            print(f"  ⚠ {rel.get('tag_name')}: tag 与资产版本不一致 -> {', '.join(bad)}")
            print("     （自动更新只认 tag，请到 Releases 页把 tag 改成资产对应版本）")
        else:
            print(f"  ✓ {rel.get('tag_name')}: {len(assets)} 个资产，tag 与资产版本一致")


def version_gate(ver: str):
    """发版前的版本号闸门 —— 不合规直接中断打包。

    拦三类真实踩过的坑：
      ① 格式不合法（1.4.20260623 日期当号 / 四段 / 前导零 / 带 v 前缀）
      ② 版本号没升（改了代码却忘了升号，会覆盖已发布版本）
      ③ 与已有 git tag 撞号（版本号复用）
    """
    step("校验版本号")
    from version import is_valid_version, compare_versions

    if not is_valid_version(ver):
        sys.exit(f"✗ 版本号 '{ver}' 不符合规范（须为三段纯数字 X.Y.Z，禁止日期/四段/前导零）。\n"
                 f"  规范见 VERSIONING.md；升号用 bump_version.py")

    try:
        r = subprocess.run(["git", "tag", "-l", "v*"], cwd=ROOT,
                           capture_output=True, text=True, timeout=15)
        tags = [t.strip().lstrip("v") for t in r.stdout.splitlines() if t.strip()]
        tags = [t for t in tags if t and t[0].isdigit()]
    except Exception:
        tags = []

    if not tags:
        print(f"  v{ver} 格式合法；无历史 tag 可比对")
        return

    latest = sorted(tags, key=lambda t: tuple(int(x) if x.isdigit() else 0
                                              for x in t.split(".")))[-1]
    if ver in tags:
        sys.exit(f"✗ git 中已存在 tag v{ver}（版本号不可复用）。\n"
                 f"  已发布的号即使撤包也要换更高的号，请跑 bump_version.py 升号")
    if compare_versions(latest, ver) <= 0:
        sys.exit(f"✗ 版本号没有前进：最新 tag 是 v{latest}，当前 version.py 是 v{ver}。\n"
                 f"  请先跑 bump_version.py（patch/minor/major）升号再打包")
    print(f"  v{ver} 格式合法，且高于最新 tag v{latest}")


def main():
    # 0) 版本号
    sys.path.insert(0, ROOT)
    from version import VERSION  # noqa: E402
    ver = VERSION
    print(f"ChemCal v{ver}")
    version_gate(ver)

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
    print(f"     ★ tag 必须填 v{ver}（自动更新只读 tag，写错版本号就永远测不到更新）")
    print(f"       标题 v{ver}，粘贴更新日志")
    print(f"       上传 installer/ChemCal_{ver}_setup.exe 和 dist/ChemCal_{ver}_portable.zip")
    print("  4. Publish release（不要留成 Draft，Draft/Pre-release 不会被更新器识别）")

    remote_health_check()


if __name__ == "__main__":
    main()
