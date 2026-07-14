<p align="center">
  <img src="ChemCal.ico" alt="ChemCal Logo" width="128" />
</p>

<h1 align="center">ChemCal · 化算</h1>

<p align="center">
  <strong>化工工程师的桌面生产力工具</strong>
</p>

<p align="center">
  <a href="https://github.com/virmuran/ChemCal/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.13-blue.svg" alt="Python">
  </a>
  <a href="https://github.com/virmuran/ChemCal">
    <img src="https://img.shields.io/badge/version-1.5.0-green.svg" alt="Version">
    <!-- 更新版本号时，同时修改 version.py 中的 VERSION -->
  </a>
  <a href="https://github.com/virmuran/ChemCal">
    <img src="https://img.shields.io/badge/platform-Windows-lightgrey.svg" alt="Platform">
  </a>
</p>

---

**ChemCal（化算）** 是一款面向化工工程师的专业桌面应用，集成了 44 种工程计算器、参考资料库、单位换算、计算历史记录和可视化倒计时。基于 Python 3.13 + PySide6 构建，支持三套主题（亮色 / 暗色 / 蓝色），所有数据本地存储，不上传任何服务器。

---

## 功能概览

### 工程计算

ChemCal 提供六大类共 44 个工程计算器，覆盖化工设计核心场景：

| 类别     | 计算器                                                                                                                                                                                                      | 数量 |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--: |
| 物性查询 | 水蒸气性质（IAPWS-IF97）、湿空气计算、制冷剂物性、纯物质物性、溶液密度、固体溶解度、腐蚀查询、危险化学品、气体状态转换、EOS 状态方程、气体混合物 EOS、汽液平衡（活度系数）、混合液体闪点、发酵废水 COD 估算 |  14  |
| 管道系统 | 管径计算、管道压降、管道壁厚、管道跨距、管道间距、管道补偿、压力管道定义、可压缩流体压降、离心泵功率、NPSHa 汽蚀余量、蒸汽管径流量、长输蒸汽管道温降、循环水用水量、法兰尺寸、蒸汽管道压降温降、蒸汽空消    |  16  |
| 换热设备 | 换热器计算、换热器面积（含"未知侧设计"模式）、风机功率、保温厚度、夹套盘管换热                                                                                                                              |  5   |
| 容器设备 | 设备尺寸计算、罐体重量、篮式过滤器设计、发酵搅拌功率、容器贮罐设计                                                                                                                                          |  5   |
| 安全消防 | 安全阀计算（模式驱动/6种工况/Kd分类）、消火栓、消防水池容积                                                                                                                                                 |  3   |
| 制冷热工 | 制冷循环（工业级精度）                                                                                                                                                                                      |  1   |

每个计算器均支持 **DOCX/PDF 计算书导出**，方便存档和审查。导出逻辑由 `utils/docx_utils.py` 中的 `ReportExporter` 统一管理。

### 参考资料库

内置化工设计常用规范数据，分门别类，全文搜索，告别翻书查表：

| 分类     | 内容                                               | 条目数 |
| -------- | -------------------------------------------------- | :----: |
| 设备布置 | 储罐间距、塔容器间距、操作通道、平台梯子、防火间距 |   5    |
| 管道设计 | 推荐流速、管径选型、支吊架间距、壁厚公式、管道材料 |   5    |
| 安全规范 | 安全阀整定压力、泄放量公式、防爆区域、安全色标志   |   4    |
| 计算依据 | 换热器/泵/压降/循环水公式及参数来源                |   4    |
| 物性数据 | 液体物性、汽化潜热、结晶热、污垢热阻               |   4    |
| 材料规范 | 法兰标准、垫片选型、阀门选型、密封材料             |   4    |

- **全文搜索**：输入关键词即时匹配分类名、标题、内容、来源
- **表格展示**：规范数据以表格呈现，交替行色，来源标注
- **公式展示**：计算公式自动排版，变量定义加粗高亮
- **数据存储**：JSON 格式（`data/reference_db.json`），方便扩展和导入

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

| 主题  | 主色调             | 适用场景 |
| ----- | ------------------ | -------- |
| Light | 白底灰字 `#f5f7fa` | 白天办公 |
| Dark  | 深灰背景 `#2d2d2d` | 夜间低光 |
| Blue  | 淡蓝风格 `#e6f2ff` | 护眼阅读 |

---

## 快速开始

### 环境要求

- Python 3.13+
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

| 库                                                   | 用途               |
| ---------------------------------------------------- | ------------------ |
| [PySide6](https://pypi.org/project/PySide6/)         | Qt6 GUI 框架       |
| [NumPy](https://pypi.org/project/numpy/)             | 数值计算           |
| [SciPy](https://pypi.org/project/scipy/)             | 科学计算与方程求解 |
| [ReportLab](https://pypi.org/project/reportlab/)     | PDF 报告生成       |
| [python-docx](https://pypi.org/project/python-docx/) | DOCX 报告生成      |
| [Loguru](https://pypi.org/project/loguru/)           | 日志系统           |
| [psutil](https://pypi.org/project/psutil/)           | 进程监控（看门狗） |

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
├── data/                       # 数据文件
│   └── reference_db.json         # 参考资料库数据
│
├── utils/                      # 公共工具模块
│   ├── __init__.py
│   └── docx_utils.py            # DOCX 报告生成（ReportExporter）
│
├── scripts/                    # 迁移/维护脚本
│   └── migrate_reports.py       # 批量迁移导出方法
│
├── modules/
│   ├── chemical_calculations/
│   │   ├── calculators/        # 44 个计算器实现
│   │   │   ├── steam_property_calculator.py
│   │   │   ├── pressure_drop_calculator.py
│   │   │   ├── heat_exchanger_area_calculator.py
│   │   │   ├── cooling_water_calculator.py  # 循环水用水量（含多效蒸发器/结晶罐）
│   │   │   ├── agitator_calculator.py       # 发酵搅拌功率 & kLa
│   │   │   ├── vessel_design_calculator.py   # 容器/贮罐设计（GB 150）
│   │   │   └── ...
│   │   ├── steam_iapws.py      # IAPWS-IF97 水蒸气物性
│   │   ├── refrigerant_eos.py  # 制冷剂 PR 状态方程
│   │   └── chemical_calculations_widget.py
│   │
│   ├── reference/              # 参考资料库
│   │   ├── __init__.py
│   │   └── reference_widget.py # 树形导航 + 搜索 + 表格/公式展示
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

### 参考资料库

化工设计中的规范数据（设备间距、流速范围、安全阀整定压力、物性数据等）往往散落在多本规范手册中，查找费时。ChemCal 将这些数据电子化、结构化，支持全文搜索，一键定位。每条数据均标注来源（GB/HG/TSG/API 标准），方便溯源。

后续计划：导入 GB 国家标准全文、MSDS 化学品安全技术说明书。

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

### NPSHa 汽蚀余量计算

支持敞口/密闭容器（液面压力 kPaA），内置 12 种泵型安全裕量推荐值（一般离心泵 0.6~1.0m、锅炉给水泵/釜液泵 2.1m 等），泵吸入安装 SVG 示意图，扣除裕量后四档安全评估。

### 安全阀泄放面积计算

模式驱动架构，6 种计算类型（饱和/过热水蒸汽、气体、空气、火灾已知/未知润湿面积）。支持已知/未知泄放量双模态，Kd 流量系数按阀型分类（全启式 0.65 / 带调节圈微启 0.45 / 不带调节圈微启 0.30）。火灾工况自动估算润湿面积（卧式/立式/球罐）。

### 循环水用水量计算

10 种设备模式一键切换：发酵罐（7种发酵类型+产热率预设）、结晶罐（分项计算：结晶放热+显热降温+搅拌热）、化学反应釜、脱色罐、换热器、冷凝器、蒸馏釜/蒸发器、多效蒸发器（1~5效系数+汽化潜热自动匹配）、气体冷却器、直接输入。冷却水类型预设（循环水/冷冻水/深冷水），自动计算循环水量并推荐管径（DN25~500）。

### DOCX 报告导出

v1.3 将全局报告导出从 TXT 升级为 DOCX，提取 `utils/docx_utils.py` 公共模块（ReportExporter），批量迁移 34 个计算器，净减少 ~3200 行重复代码。新计算器只需 4 行调用即可实现 DOCX/PDF 双格式导出。

---

## 更新日志

### v1.4.20260623 (2026-06-23)

- 新增发酵搅拌功率计算器（不通气/通气功率衰减、kLa 传氧系数、电机选型）
- 新增蒸汽空消计算器（发酵罐/种子罐/管道灭菌蒸汽量估算）
- 新增发酵废水 COD 估算器
- 新增蒸汽管道压降/温降计算器（架空/地沟/直埋三种敷设方式）
- 新增法兰尺寸计算器
- 新增夹套/盘管换热面积核算计算器
- 新增容器/贮罐设计计算器（GB 150 压力容器标准）
- 新增消防水池容积计算器（GB 50974-2014）

### v1.4 (2026-06-02)

- 新增「参考资料库」标签页：6 大类 26 条规范数据，树形导航 + 全文搜索 + 表格/公式展示
- 循环水计算器增强：新增多效蒸发器模式（1~5效系数，效数自动匹配末效汽化潜热）
- 结晶罐增强：从单一热负荷改为分项计算（结晶放热+显热降温+搅拌热），溶液量拆分为罐有效体积×物料密度
- 新增物料密度预设（9种）、结晶热预设（10种）、溶液比热容预设（9种）
- SVG 参数化示意图箭头优化，解决文字与箭头重叠问题

### v1.3 (2026-06-01)

- 全局报告导出升级（TXT → DOCX，提取 ReportExporter 公共模块）
- 新增循环水用水量计算器（9种设备模式）
- 安全阀模式驱动重构（6种计算类型 / Kd阀型分类 / 火灾工况）
- NPSHa增强（液面压力 / 12种泵型安全裕量 / 泵吸入SVG）
- 新增"未知侧设计"换热器模式
- 防闪退保护层 + 看门狗自动重启
- UI 全面规范化 + 主题系统全面优化

### v1.2

- 新增查询类计算器；历史记录系统上线；IAPWS-IF97 蒸汽物性精度升级

### v1.1

- 帮助菜单、水蒸气性质模块、日志系统

### v1.0

- 初始版本发布

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
- 参考数据：参考 `data/reference_db.json` 中的数据格式，追加新条目即可

---

## 许可证

[MIT License](LICENSE) © 2025-2026 ChemCal Team

联系方式：virmuran@163.com
