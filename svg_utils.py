"""
基础 SVG 辅助工具 — 所有计算器的 SVG 示意图共享此模块

提供 SVG TEXT/矩形/箭头/流道等基础图元，各计算器在此基础上
构建自己的 SVG 示意图内容字符串。
"""


def svg_text(x, y, text, size=9, color="#333", bold=False, center=True):
    """SVG 文本"""
    extra = 'font-weight="bold"' if bold else ""
    anchor = 'text-anchor="middle"' if center else ""
    return f'<text x="{x}" y="{y}" {anchor} font-size="{size}" fill="{color}" {extra}>{text}</text>'


def svg_rect(x, y, w, h, fill="#e8edf2", stroke="#4a6fa5", stroke_width=2, rx=6):
    """SVG 圆角矩形"""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" rx="{rx}"/>'


def svg_line(x1, y1, x2, y2, stroke="#7f8c8d", stroke_width=1.5, dasharray=None):
    """SVG 线段"""
    dash = f' stroke-dasharray="{dasharray}"' if dasharray else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{stroke_width}"{dash}/>'


def svg_circle(cx, cy, r, fill="none", stroke="#4a6fa5", stroke_width=1.5):
    """SVG 圆形"""
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'


def svg_ellipse(cx, cy, rx, ry, fill="#dce4ec", stroke="#4a6fa5", stroke_width=2):
    """SVG 椭圆"""
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'


def svg_arrow_marker(name, color="#4a6fa5"):
    """SVG 箭头标记定义"""
    return (
        f'<defs><marker id="{name}" markerWidth="8" markerHeight="8" '
        f'refX="8" refY="4" orient="auto">'
        f'<path d="M0,0 L8,4 L0,8 Z" fill="{color}" /></marker></defs>'
    )


def svg_start(w=680, h=220):
    """SVG 文档开头"""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
    )


def svg_end():
    """SVG 文档结尾"""
    return "</svg>"
