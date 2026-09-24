"""ChemCal 版本号 — 唯一来源，所有地方从这里读

版本规范见 VERSIONING.md，摘要（三段式：主版本.次版本.修订号，如 1.6.0）：

    主版本 MAJOR   不兼容变更 —— 数据格式/存储破坏性调整、技术栈更换、用户必须人工迁移
    次版本 MINOR   新增功能 —— 新增或恢复计算器、新增标签页/发行方式，向后兼容
    修订号 PATCH   修 bug、公式勘误、默认值调整、文案、依赖与打包配置

硬性约束（本文件是唯一手写版本号的地方，其余文件由 bump_version.py 自动同步）：
    · 必须严格三段纯数字，段内禁止前导零（写 1.6.1，不写 1.6.01）
    · 禁止把日期当版本号（1.4.20260623 这类，修订号位数超过 3 位即判非法）
    · 禁止"四段丢点"写法：本意 1.5.4.1 却写成 1.5.41，会被解析成"修订 41"，
      进而造成 1.5.23 被判为比 1.5.3 更新 的比较倒挂（本项目真实踩过）
    · 版本号只增不减；已发布过的号永不复用，即使撤包也发更高号
    · 升号一律通过 `python bump_version.py <major|minor|patch> "说明"` 完成，不手改
"""

VERSION = "1.12.1"

#: 规范版本号：三段，无前导零，主/次 1~2 位、修订 1~3 位
VERSION_PATTERN = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"

__all__ = [
    "VERSION",
    "VERSION_PATTERN",
    "parse_version",
    "compare_versions",
    "is_valid_version",
    "version_info",
]


# ------------------------------------------------------------------ 解析与比较
# 注意：parse_version / compare_versions 故意写得"宽容"，支持任意多段数字，
# 因为要能跟 GitHub 上历史遗留的 tag（如 v1.4.20260623）做比较。
# 严格校验用 is_valid_version()，只有发版工具才需要严格。

def parse_version(version_str: str) -> tuple:
    """将版本号字符串解析为可比较的元组（宽容解析，不校验合法性）。

    '1.6.0'        -> (1, 6, 0)
    'v1.5.51'      -> (1, 5, 51)     v 前缀自动去掉
    '1.4.20260623' -> (1, 4, 20260623)   历史格式仍可比较
    非数字段按 0 处理，保证比较不抛异常
    """
    parts = (version_str or "").strip().lstrip("vV").split(".")
    return tuple(int(p) if p.isdigit() else 0 for p in parts)


def compare_versions(current_str: str, latest_str: str) -> int:
    """比较两个版本号：1 = 后者更新，-1 = 后者更旧，0 = 相同。

    逐段按数值比较（不是按字符串），段数不足时补 0：1.5 == 1.5.0
    """
    cur = parse_version(current_str)
    lat = parse_version(latest_str)
    max_len = max(len(cur), len(lat))
    cur = cur + (0,) * (max_len - len(cur))
    lat = lat + (0,) * (max_len - len(lat))
    if lat > cur:
        return 1
    if lat < cur:
        return -1
    return 0


# ------------------------------------------------------------------ 严格校验

def is_valid_version(version_str: str) -> bool:
    """校验是否符合本项目的版本号规范（发版前必须通过）。

    合法：'1.6.0' '1.5.51' '2.0.0'
    非法：'v1.6.0'(带前缀)  '1.6'(两段)  '1.6.0.1'(四段)
          '1.6.01'(前导零)  '1.5.1000'(修订超3位)  '1.4.20260623'(日期当号)
    """
    import re

    if not version_str or not isinstance(version_str, str):
        return False
    if not re.match(VERSION_PATTERN, version_str):
        return False
    major, minor, patch = (int(x) for x in version_str.split("."))
    if major < 1:
        return False
    if major > 99 or minor > 99:      # 主/次超过两位基本是写错了
        return False
    if patch > 999:                   # 修订超过三位 = 混进了日期，如 20260623
        return False
    return True


def version_info() -> dict:
    """返回当前版本的结构化信息，供界面/诊断使用。"""
    major, minor, patch = (int(x) for x in VERSION.split("."))
    return {
        "version": VERSION,
        "major": major,
        "minor": minor,
        "patch": patch,
        "valid": is_valid_version(VERSION),
        "tag": f"v{VERSION}",
    }
