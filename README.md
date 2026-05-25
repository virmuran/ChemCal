<p align="center">
  <img src="ChemCal.png" alt="ChemCal Logo" width="128" />
</p>

<h1 align="center">ChemCal</h1>

<p align="center">
  <strong>化工工程师的桌面生产力工具</strong>
</p>

<p align="center">
  <a href="https://github.com/virmuran/ChemCal/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg" alt="Python">
  </a>
  <a href="https://github.com/virmuran/ChemCal">
    <img src="https://img.shields.io/badge/version-1.3.20260523-green.svg" alt="Version">
  </a>
  <a href="https://github.com/virmuran/ChemCal">
    <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Platform">
  </a>
</p>

---

**ChemCal** 是一款面向化工工程师的专业桌面应用，集成了 37 种工程计算器、单位换算、计算历史记录和可视化倒计时。基于 PySide6 构建，支持三套主题（亮色 / 暗色 / 蓝色），所有数据本地存储，不上传任何服务器。

---

## 功能概览

### 工程计算

ChemCal 提供六大类共 37 个工程计算器，覆盖化工设计核心场景：

| 类别 | 计算器 | 数量 |
|------|--------|:--:|
| 物性查询 | 水蒸气性质（IAPWS-IF97）、湿空气计算、制冷剂物性、纯物质物性、溶液密度、固体溶解度、腐蚀查询、危险化学品、气体状态转换、EOS 状态方程、气体混合物 EOS、汽液平衡（活度系数）、混合液体闪点 | 13 |
| 管道系统 | 管径计算、管道压降、管道壁厚、管道跨距、管道间距、管道补偿、压力管道定义、可压缩流体压降、离心泵功率、NPSHa 汽蚀余量、蒸汽管径流量、长输蒸汽管道温降 | 12 |
| 换热设备 | 换热器计算、换热器面积（含"未知侧设计"模式）、风机功率、保温厚度 | 4 |
| 容器设备 | 设备尺寸计算、罐体重量、篮式过滤器设计 | 3 |
| 安全消防 | 安全阀计算、泄压面积、消火栓 | 3 |
| 制冷热工 | 制冷循环（工业级精度） | 1 |

每个计算器均支持 **TXT/PDF 计算书导出**，方便存档和审查。

### 单位换算

内置 14 类单位换算器：长度、重量、温度、压力、体积、面积、能量、功率、速度、力、流量、密度、粘度等。

### 计算历史

每次计算自动存入 SQLite 数据库，支持：
- 按计算器类型筛选
- 关键词搜索输入/输出
- 查看完整输入输出详情
- 逐条删除

### 主题系统

三套精心设计的主题配色：

| 主题 | 主色调 | 适用场景 |
|------|--------|----------|
| Light | 白底灰字 `#f5f7fa` | 白天办公 |
| Dark | 深灰背景 `#2d2d2d` | 夜间低光 |
| Blue | 淡蓝风格 `#e6f2ff` | 护眼阅读 |

---

## 快速开始

### 环境要求

- Python 3.8+
- pip（包管理器）

### 安装

```bash
# 克隆仓库
git clone https://github.com/virmuran/ChemCal.git
cd ChemCal

# 安装依赖
pip install -r requirements.txt

# 启动应用
python main.py
```

### 依赖清单

```txt
PySide6 >= 6.5
NumPy
SciPy
ReportLab
Loguru
psutil
```

---

## 项目结构

```
ChemCal/
├── main.py                     # 主入口，窗口框架与菜单
├── crash_shield.py             # 防闪退保护层 + 看门狗
├── launcher.py                 # 启动器（异常重启）
├── data_manager.py             # 数据管理（JSON 单例）
├── theme_manager.py            # 主题管理（亮色/暗色/蓝色）
├── module_loader.py            # 模块动态加载器
├── history_db.py               # 历史记录 SQLite 数据库
├── requirements.txt
├── ChemCal.ico                   # 应用图标（多分辨率）
├── ChemCal.png                   # Logo
│
├── modules/
│   ├── chemical_calculations/
│   │   ├── calculators/        # 37 个计算器实现
│   │   │   ├── steam_property_calculator.py
│   │   │   ├── pressure_drop_calculator.py
│   │   │   ├── heat_exchanger_area_calculator.py
│   │   │   └── ...
│   │   ├── steam_iapws.py      # IAPWS-IF97 水蒸气物性
│   │   ├── refrigerant_eos.py  # 制冷剂 PR 状态方程
│   │   └── chemical_calculations_widget.py
│   │
│   ├── converter/              # 单位换算器（14 类）
│   │   ├── converters.py
│   │   └── converter_widget.py
│   │
│   ├── history_viewer.py       # 计算历史查看器
│   └── countdowns.py           # 倒计时模块
│
└── docs/                       # 文档（计划中）
```

---

## 特色亮点

### 防闪退保护

针对 PySide6 常见的 access violation 和 QWidgetItem 类型错误，实现了三层防护：

- `crash_shield.py` --- 安装全局异常钩子，捕获 C++ 级崩溃
- `launcher.py` --- 看门狗进程，异常退出后自动重启
- 代码层面 --- QListWidget 使用 `takeItem()` 代替 `clear()`，`blockSignals()` 阻断信号风暴

详见 [pyside6-crash-prevention](https://github.com/virmuran/ChemCal) 技能文档。

### 计算精度

- **水蒸气**：IAPWS-IF97 工业标准，覆盖区域 1/2/4
- **制冷剂**：Peng-Robinson EOS + Antoine 蒸气压 + Dippel 液相输运，支持 15 种工质
- **气体混合物**：Lee-Kesler 压缩因子 + Chapman-Enskog 粘度 + Mason-Saxena 混合规则
- **汽液平衡**：真实 UNIQUAC + Wilson/NRTL 活度系数模型，7 组预设二元参数

### 压降计算器参数库

内置 80 种流体物性数据（水、空气、有机液体、油类、气体），14 种管道粗糙度，29 个标准管径（DN6~DN1500 Sch 40），支持不可压缩/可压缩（绝热/等温）三种模式。

---

## 数据安全

- 所有数据仅保存在本地 **`%APPDATA%/ChemCal/`** 目录
- 不联网、不上传、不收集任何隐私信息
- 支持数据备份（菜单 → 文件 → 备份数据，自动带时间戳）

---

## 免责声明

计算结果仅供参考，实际工程应用请由专业工程师审核确认。

---

## 贡献

欢迎提交 Issue 和 Pull Request。

- 代码规范：中文注释 + Python 类型注解
- 计算器开发：参考 `modules/chemical_calculations/calculators/` 中的现有实现
- UI 规范：遵循 ChemCal UI 标准（QGridLayout 三列、按比例伸缩）

---

## 许可证

[MIT License](LICENSE)  © 2025-2026 ChemCal Team

联系方式：virmuran@163.com
