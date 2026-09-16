"""ChemCal 升版本号工具 —— 版本规范的执行者

用法（在项目根目录，用项目自带的 Python 运行）：

    .venv/Scripts/python.exe bump_version.py                       # 看当前版本 + 历史 tag
    .venv/Scripts/python.exe bump_version.py patch "修复安全阀 Kd 映射"
    .venv/Scripts/python.exe bump_version.py minor "新增 3 个管道计算器"
    .venv/Scripts/python.exe bump_version.py major "计算历史库结构不兼容调整"
    .venv/Scripts/python.exe bump_version.py --set 1.6.0 "全量核对收官"
    .venv/Scripts/python.exe bump_version.py patch "说明" --dry-run # 只看会改什么

它做三件事：
    1. 校验 —— 新版本号必须符合规范、必须严格大于当前版本、必须未被 git tag 占用
    2. 改写 —— version.py（唯一手写处）+ ChemCal.iss AppVersion + README 徽章与更新日志
    3. 交底 —— 打印后续发版步骤（打包、打 tag、传 Release）

版本语义（详见 VERSIONING.md）：
    major  不兼容变更：数据破坏性调整、技术栈更换、用户必须手动迁移
    minor  新增功能：新增/恢复计算器、新增标签页或发行方式，向后兼容
    patch  修 bug、公式勘误、默认值、文案、依赖与打包配置
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------ 读取

def read_version(root: str = ROOT) -> str:
    """从 version.py 读出当前版本号（正则读，避免模块缓存读到旧值）。"""
    path = os.path.join(root, "version.py")
    text = open(path, encoding="utf-8").read()
    m = re.search(r'^VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        sys.exit(f"✗ 无法从 {path} 解析出 VERSION，请检查文件是否被改动")
    return m.group(1)


# ------------------------------------------------------------------ 计算新版本

def next_version(current: str, kind: str) -> str:
    """按 major/minor/patch 规则算出下一个版本号（各自只 +1，绝不跳号）。"""
    major, minor, patch = (int(x) for x in current.split("."))
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"未知的升号类型: {kind}")


def validate_target(current: str, target: str, force: bool) -> list:
    """校验目标版本号，返回警告列表；不合法则直接退出。"""
    sys.path.insert(0, ROOT)
    from version import compare_versions, is_valid_version

    problems = []
    if not is_valid_version(target):
        problems.append(f"版本号 '{target}' 不符合规范（必须三段纯数字、无前导零、"
                        f"主/次≤2位、修订≤3位；禁止 v 前缀与日期当号）")
    if problems:
        sys.exit("✗ " + "\n✗ ".join(problems) + "\n  规范详见 VERSIONING.md")

    cmp = compare_versions(current, target)
    if cmp == 0:
        sys.exit(f"✗ 目标版本与当前版本相同（{target}），无需升号")
    if cmp < 0:
        sys.exit(f"✗ 版本号只能增大：当前 {current}，目标 {target} 更小。\n"
                 f"  版本号只增不减，已发布过的号永不复用")

    warns = []
    cur = current.split(".")
    new = target.split(".")
    # 同一主.次段内修订号跳跃 > 1：历史上正是这样把 1.5.4.1 写成 1.5.41 的
    if cur[0] == new[0] and cur[1] == new[1]:
        jump = int(new[2]) - int(cur[2])
        if jump > 1 and not force:
            sys.exit(f"✗ 修订号从 {cur[2]} 跳到 {new[2]}（跨 {jump} 格）。\n"
                     f"  规范要求修订号每次只 +1；确实需要跳号请显式加 --force")
        if jump > 1:
            warns.append(f"修订号跨了 {jump} 格（--force 已放行），请确认不是"
                         f"'四段丢点'写法（1.5.4.1 误写成 1.5.41）")
    return warns


# ------------------------------------------------------------------ 改写各文件

def sync_version_py(root: str, ver: str) -> bool:
    path = os.path.join(root, "version.py")
    text = open(path, encoding="utf-8").read()
    new, n = re.subn(r'^(VERSION\s*=\s*)"[^"]+"', rf'\g<1>"{ver}"', text, count=1,
                     flags=re.MULTILINE)
    if n:
        open(path, "w", encoding="utf-8").write(new)
    return bool(n)


def sync_iss(root: str, ver: str) -> bool:
    path = os.path.join(root, "ChemCal.iss")
    if not os.path.exists(path):
        return False
    text = open(path, encoding="utf-8").read()
    new, n = re.subn(r'#define MyAppVersion "[^"]*"',
                     f'#define MyAppVersion "{ver}"', text)
    if n:
        open(path, "w", encoding="utf-8").write(new)
    return bool(n)


def sync_readme(root: str, ver: str, note: str, date: str) -> list:
    """改 README 徽章版本号，并在「## 更新日志」下插入新条目骨架。"""
    path = os.path.join(root, "README.md")
    if not os.path.exists(path):
        return []
    text = open(path, encoding="utf-8").read()
    done = []

    new, n = re.subn(r"(badge/version-)([0-9.]+)(-)", rf"\g<1>{ver}\g<3>", text, count=1)
    if n:
        text = new
        done.append("README 徽章")

    head = "## 更新日志"
    if head in text and f"### v{ver} " not in text:
        entry = f"### v{ver} ({date})\n\n- {note}\n\n"
        idx = text.index(head) + len(head)
        # 跳过标题后的换行，把新条目插在最前面（最新在上）
        rest = text[idx:].lstrip("\n")
        text = text[:idx] + "\n\n" + entry + rest
        done.append("README 更新日志条目")

    open(path, "w", encoding="utf-8").write(text)
    return done


def check_git_tag(root: str, ver: str) -> bool:
    """检查 git 里是否已存在同名 tag（版本号复用检测）。返回 True 表示已存在。"""
    try:
        r = subprocess.run(["git", "tag", "-l", f"v{ver}"], cwd=root,
                           capture_output=True, text=True, timeout=15)
    except Exception:
        return False
    return bool(r.stdout.strip())


def list_git_tags(root: str) -> list:
    try:
        r = subprocess.run(["git", "tag", "-l", "v*"], cwd=root,
                           capture_output=True, text=True, timeout=15)
    except Exception:
        return []
    return [t.strip() for t in r.stdout.splitlines() if t.strip()]


# ------------------------------------------------------------------ 主流程

def bump(kind: str, note: str, target: str = None, force: bool = False,
         dry: bool = False, root: str = ROOT) -> dict:
    """执行升号。返回 dict（便于测试断言）。"""
    current = read_version(root)
    new = target or next_version(current, kind)

    warns = validate_target(current, new, force)
    if check_git_tag(root, new):
        sys.exit(f"✗ git 中已存在 tag v{new}，版本号不可复用。\n"
                 f"  已发布的号即使撤包也不能再用，请换更高版本号")

    date = datetime.date.today().isoformat()
    if dry:
        return {"from": current, "to": new, "dry": True, "changed": [], "warns": warns}

    changed = []
    if sync_version_py(root, new):
        changed.append("version.py")
    if sync_iss(root, new):
        changed.append("ChemCal.iss AppVersion")
    changed += sync_readme(root, new, note, date)

    return {"from": current, "to": new, "dry": False, "changed": changed, "warns": warns}


def show(root: str = ROOT):
    cur = read_version(root)
    sys.path.insert(0, root)
    from version import is_valid_version
    flag = "✓ 符合规范" if is_valid_version(cur) else "⚠ 不符合现行规范"
    print(f"当前版本：v{cur}  {flag}")
    tags = list_git_tags(root)
    if tags:
        print(f"历史 tag（{len(tags)} 个）：")
        for t in tags:
            print(f"  {t}")
    else:
        print("历史 tag：无")
    print("\n下一个版本号建议：")
    print(f"  patch -> {next_version(cur, 'patch')}   修 bug / 勘误 / 文案 / 打包配置")
    print(f"  minor -> {next_version(cur, 'minor')}   新增功能（计算器、标签页、发行方式）")
    print(f"  major -> {next_version(cur, 'major')}   不兼容变更（数据破坏性调整等）")


def main():
    ap = argparse.ArgumentParser(
        description="ChemCal 升版本号工具（规范见 VERSIONING.md）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="不传参数时只显示当前版本与建议的下一版本号。\n"
               "示例：bump_version.py patch \"修复安全阀 Kd 映射\"\n"
               "      bump_version.py --set 1.6.0 \"45 个计算器核对收官\"")
    # 位置参数收成列表再手工解释：这样 `--set 1.6.0 "说明"` 不会把说明误当成升号类型
    ap.add_argument("rest", nargs="*", metavar="[major|minor|patch] [说明]",
                    help="升号类型，以及一句话改动说明")
    ap.add_argument("--set", dest="target", metavar="X.Y.Z",
                    help="直接指定目标版本号（仍会校验规范、递增与跳号）")
    ap.add_argument("-m", "--note", help="改动说明（也可作为第二个位置参数给出）")
    ap.add_argument("--force", action="store_true",
                    help="放行修订号跳号（默认禁止跳号）")
    ap.add_argument("--dry-run", action="store_true", help="只显示将要做的事，不写文件")
    a = ap.parse_args()

    kind, rest = None, list(a.rest)
    if rest and rest[0] in ("major", "minor", "patch"):
        kind = rest.pop(0)
    elif rest and not a.target:
        sys.exit(f"✗ 未知的升号类型 '{rest[0]}'：只能是 major / minor / patch，"
                 f"或改用 --set X.Y.Z 指定")

    note = a.note or (" ".join(rest) if rest else "")

    if not kind and not a.target:
        show()
        return

    res = bump(kind or "patch", note or "（待补充）", target=a.target,
               force=a.force, dry=a.dry_run)

    for w in res["warns"]:
        print(f"⚠ {w}")
    if res["dry"]:
        print(f"[dry-run] v{res['from']} -> v{res['to']}，未写入任何文件")
        return

    print(f"✓ 版本号 v{res['from']} -> v{res['to']}")
    for c in res["changed"]:
        print(f"  · 已更新 {c}")
    print("\n后续步骤：")
    print(f"  1. 编辑 README「更新日志」的 v{res['to']} 条目，把改动写详细")
    print(f"  2. .venv/Scripts/python.exe build_release.py   # 打包安装包 + 便携 zip")
    print(f"  3. VS Code 提交推送，然后 git tag v{res['to']} && git push origin v{res['to']}")
    print(f"  4. GitHub Releases 新建 Release，tag 填 v{res['to']}（必须与 version.py 一致）")
    print(f"     上传 installer/ChemCal_{res['to']}_setup.exe 与 dist/ChemCal_{res['to']}_portable.zip")
    print("  5. Publish release（Draft / Pre-release 更新器识别不到）")


if __name__ == "__main__":
    main()
