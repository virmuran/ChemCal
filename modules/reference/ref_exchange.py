# ChemCal/modules/reference/ref_exchange.py
"""资料库 ↔ 计算器 的取值交接总线（打通数据的关键件）

为什么要这条总线：计算器是「按需实例化 + 45 个互不相识的小部件」结构，
如果给每个计算器都注入「资料库引用 / 主窗口引用」，就要动 45 个构造函数；
反过来资料库也不该知道「哪个计算器叫什么、字段叫什么」。所以中间放一条
信号总线，只连三个地方：

    资料库 ──fill_requested──▶ 主窗口 ──▶ 计算器容器.open_calculator()
                                            └─▶ 计算器.apply_reference_value()
    计算器 ──section_requested▶ 主窗口 ──▶ 资料库.focus_section()

两个方向各只有一个入口，新增目标只需往 `TARGETS` 里加一行。
"""
from PySide6.QtCore import QObject, Signal


class RefExchange(QObject):
    """模块级单例（EXCHANGE）。"""

    #: 资料库 → 计算器：把值送到某个计算器的某个字段
    fill_requested = Signal(str, str, object)      # module_name, field, value
    #: 计算器 → 资料库：请主窗口定位到某一节
    section_requested = Signal(str, str)           # category, title

    def __init__(self):
        super().__init__()
        #: 计算器尚未实例化时的暂存（打开后再取走）
        self._pending = {}

    # ── 方向 A：资料库 → 计算器 ──────────────────────────
    def send_to_calculator(self, module_name, field, value):
        self._pending[(module_name, field)] = value
        self.fill_requested.emit(module_name, field, value)

    def take_pending(self, module_name, field):
        """取走暂存值（取过即清，避免下次打开又被填一次）。"""
        return self._pending.pop((module_name, field), None)

    # ── 方向 B：计算器 → 资料库 ──────────────────────────
    def open_section(self, title, category=""):
        self.section_requested.emit(category, title)


#: 全局单例 —— 页面与计算器都 import 它，不再各自持有引用
EXCHANGE = RefExchange()


#: 「送入计算器」可选目标：(显示名, 计算器模块名, 字段键, 值说明)
#:   模块名 = 计算器文件名（= _calc_meta["id"] = 历史记录的 calculator_id）
#:   字段键 = 计算器 apply_reference_value() 认识的键
TARGETS = [
    ("管径计算器 · 流速 (m/s)", "pipe_diameter_calculator", "velocity_input", "推荐流速 / 经验流速"),
    ("管径计算器 · 流量 (m³/h)", "pipe_diameter_calculator", "flow_input", "推荐流量范围"),
    ("管径计算器 · 管道内径 (mm)", "pipe_diameter_calculator", "diameter_input", "管径选型内径"),
    ("管径计算器 · 压力 (MPa)", "pipe_diameter_calculator", "pressure_input", "压力范围"),
    ("管径计算器 · 温度 (°C)", "pipe_diameter_calculator", "temp_input", "温度"),
]


def targets_for_value(value):
    """值 → 可送入的目标清单（目前全部目标都接受数值，保留接口便于后续按类型过滤）。"""
    return list(TARGETS)
