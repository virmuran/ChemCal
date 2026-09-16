<!-- markdownlint-disable -->

<div align="center">

<img alt="ChemCal" src="ChemCal.png" width="128" height="128" />

# ChemCal · 化算

<br>
<div>
    <img alt="Python" src="https://img.shields.io/badge/Python-3.13-%233776AB?logo=python">
    <img alt="platform" src="https://img.shields.io/badge/platform-Windows-lightgrey">
    <img alt="license" src="https://img.shields.io/badge/license-MIT-blue">
</div>
<div>
    <img alt="version" src="https://img.shields.io/badge/version-1.6.0-green">
    <img alt="stars" src="https://img.shields.io/github/stars/virmuran/ChemCal?style=social">
</div>
<br>

化工工程师的桌面生产力工具

基于 Python + PySide6，集成 45 种工程计算器、参考资料库、单位换算、计算历史与可视化倒计时。

</div>

## 下载与安装

前往 [Releases](https://github.com/virmuran/ChemCal/releases)，按需选择：

| 文件 | 适合谁 | 说明 |
|---|---|---|
| `ChemCal_vX.X.X_setup.exe` | 普通用户 | 安装向导（简体中文），下一步装完，开始菜单/桌面快捷方式、控制面板卸载 |
| `ChemCal_vX.X.X_portable.zip` | 便携党 | 解压即用，免安装，适合 U 盘 / 无权限环境 |

两种发行均无需安装 Python 环境。用户数据保存在用户目录 `.ChemCal/`，安装版卸载不会删除你的计算历史与数据。

> **安装报错“错误 5：拒绝访问”怎么办？** 少数受管控的电脑（公司终端安全软件、收紧的 Temp 权限）双击安装包会提示“安装程序无法创建目录 …\Temp\is-XXXX.tmp，错误 5：拒绝访问”。
> 请**右键 → 以管理员身份运行**；仍不行则在 cmd 中执行 `set TEMP=C:\Windows\Temp` 后运行；或直接改用上面的**便携版**（免安装、不写临时目录、无需管理员权限）。

如需从源码运行：

```bash
git clone https://github.com/virmuran/ChemCal.git
cd ChemCal
pip install -r requirements.txt
python main.py
```

## 亮点功能

- 🧪 **45 种工程计算器** — 覆盖物性查询、管道系统、换热设备、容器设计、安全消防、制冷热工六大类，每个计算器均支持 DOCX / PDF 计算书一键导出，公式均对照 GB / HG / NB/T 等标准逐项核对并固化回归测试
- 📚 **内置参考资料库** — 化工设计常用规范数据电子化，全文搜索，14 大类 65 小节（262 条表格数据 + 30 条公式与规范说明），告别翻书查表
- 🔄 **21 类单位换算** — 基础量（长度、重量、面积、体积、流量、温度、速度、进制）+ 力学热工（热能、压强、功率、力）+ 化工物性（密度、动力/运动粘度、表面张力、导热系数、传热系数、比热容、热值、浓度），即输即算
- 📝 **自动计算历史** — SQLite 数据库全程记录，支持按模块筛选和关键词搜索
- 🎨 **三套主题配色** — 亮色 / 暗色 / 蓝色，白天办公不刺眼，夜间低光不伤眼
- 🔒 **数据本地存储** — 不联网、不上传、不收集任何隐私信息，所有数据仅保存在用户目录 `.ChemCal/` 下

<!-- markdownlint-disable -->

<details><summary>点我看截图</summary>

<p align="center">
  <em>截图待补充 — 欢迎提交 PR！</em>
</p>

</details>

<!-- markdownlint-restore -->

## 使用说明

### 工程计算

启动后默认进入「工程计算」标签页，左侧导航树按六大类展开，点击即可进入对应计算器。输入参数后点击绿色「计算」按钮，结果实时显示；点击底部「下载 DOCX」或「下载 PDF」导出计算书。

### 参考资料库

切换到「资料库」标签页，左侧按分类浏览，顶部搜索栏支持全文关键词匹配。数据来源标注 GB / HG / TSG / API 规范编号，方便溯源。

### 计算历史

每次计算自动存入「计算历史」标签页，可按计算器类型筛选、按关键词搜索，点击查看完整输入输出详情。

### 自动更新

启动时自动检查 GitHub Releases，发现新版本后状态栏提示，点击一键下载安装。

## 加入我们

### 主要关联项目

- 本项目基于 [ChemCal](https://github.com/virmuran/ChemCal) 持续迭代
- 化工计算核心：[IAPWS-IF97](http://www.iapws.org/) 工业用水蒸气性质标准
- PDF 报告：[fpdf2](https://github.com/py-pdf/fpdf2) / [ReportLab](https://www.reportlab.com/)
- DOCX 报告：[python-docx](https://github.com/python-openxml/python-docx)
- GUI 框架：[PySide6](https://wiki.qt.io/Qt_for_Python)

### 参与开发

欢迎提交 Issue 和 Pull Request！

- **代码规范**：中文注释 + Python 类型注解
- **新增计算器**：参照 `modules/chemical_calculations/calculators/` 中的现有实现，继承 `CalculatorBase`
- **版本号规范**：版本号采用 `主.次.修订` 三段式，**只允许手改 `version.py`**，其余位置由脚本同步。完整标准与升号判定见 [VERSIONING.md](VERSIONING.md)。升号命令：
  `.venv/Scripts/python.exe bump_version.py patch "修复 xxx"`（patch / minor / major 三选一；`--dry-run` 可先预览）
- **发版打包**：升号后运行 `.venv/Scripts/python.exe build_release.py`，一键完成 PyInstaller + Inno Setup 安装包 + 便携 zip，产物在 `installer/` 与 `dist/`。
  脚本内置**版本号闸门**：格式不合法、版本号没前进、与已有 tag 撞号，都会直接中断打包。
  ⚠ **发布时 Release 的 tag 必须与 `version.py` 完全一致**（如 `v1.6.0`）：客户端自动更新只读 tag，资产文件名不参与比较；tag 写错版本号（例如资产是 1.5.51、tag 仍写 v1.5.50），所有老用户都会显示"已是最新版本"。tag 也不要写成 `update` 这类自由文本，解析不出数字会让更新通道整体静默失效。脚本末尾会做一次远端一致性检查，发现不一致会直接提示。另外 Draft / Pre-release 不会被更新器识别，必须 Publish。
- **新增参考数据**：按 `data/reference_db.json` 格式追加条目

### 贡献/参与者

感谢所有参与到开发中的朋友们！

[![Contributors](https://contributors-img.web.app/image?repo=virmuran/ChemCal&max=105&columns=15)](https://github.com/virmuran/ChemCal/graphs/contributors)

## 致谢

### 开源库

- GUI 框架：[PySide6](https://wiki.qt.io/Qt_for_Python)
- 数值计算：[NumPy](https://github.com/numpy/numpy) / [SciPy](https://github.com/scipy/scipy)
- PDF 生成：[fpdf2](https://github.com/py-pdf/fpdf2) / [ReportLab](https://www.reportlab.com/)
- DOCX 生成：[python-docx](https://github.com/python-openxml/python-docx)
- 日志系统：[Loguru](https://github.com/Delgan/loguru)
- 系统监控：[psutil](https://github.com/giampaolo/psutil)
- 打包工具：[PyInstaller](https://github.com/pyinstaller/pyinstaller)

### 数据源

- 水蒸气性质：IAPWS-IF97 工业标准
- 制冷剂物性：Peng-Robinson 状态方程 + REFPROP 参考数据
- 设计规范：GB 150 / GB 50316 / GB 50974 / HG/T 20570 / TSG 21 / API 520 等

## 版本号规范

版本号采用 **`主版本.次版本.修订号`** 三段式（如 `1.6.0`），完整标准见 **[VERSIONING.md](VERSIONING.md)**。

| 升哪位 | 什么时候 | 举例 |
|---|---|---|
| 修订号 | 修 bug、公式勘误、默认值、文案、依赖与打包配置 | `1.6.1` |
| 次版本 | 新增功能：新增/恢复计算器、新增标签页或发行方式（向后兼容） | `1.7.0` |
| 主版本 | 不兼容变更：数据存储结构破坏性调整、用户必须手动迁移 | `2.0.0` |

三条最容易踩的规矩：

1. `version.py` 是**唯一**手写版本号的地方 —— 升号用 `bump_version.py`，别手改其他文件
2. Release 的 **tag 必须等于 `version.py` 的版本号**（`v1.6.0`）—— 更新器只读 tag
3. 版本号**只增不减、绝不复用**；**修订号每次只 +1**，禁止跳号，禁止把 `1.6.0.1` 写成 `1.6.01`

> 历史遗留说明：`1.4.202606xx`（日期当版本号）与 `1.5.21/1.5.41/1.5.50`（四段丢点、跳号）属旧命名，
> 已不再沿用。`1.5.51` 作为旧序列收尾保留，规范自 `1.6.0` 起生效。

## 更新日志

### v1.6.0 (2026-09-15)

- 🎨 **主题一致性专项**：清除计算历史（22 处）与资料库（8 处）的硬编码颜色 —— 此前深色主题下历史详情弹窗与资料库内容是"深底压深字"，基本看不见
- 🎨 主题新增**语义组件规则**（`mutedLabel` / `accentLabel` / `primaryBtn` / `dangerBtn`）与 **HTML 内容配色**（`theme_manager.CONTENT_COLORS`），三套主题同进同出；切换主题时页面自动重渲染
- 🛠 资料库数据内嵌表格 HTML 的浅色底/浅色边框（`#ecf0f1` × 50、`#ddd` × 582）在渲染时归一化为主题色，数据文件无需改动
- ✅ **其余 4 个标签页首次拥有回归测试**（`tests/test_pages_theme.py`，94 项）：页面功能 + 主题配色对比度闸门（≥4.0:1）+ 源码硬编码颜色黑名单
- 📋 **版本号规范落地**：新增 [VERSIONING.md](VERSIONING.md) 与 `bump_version.py` 升号工具，`build_release.py` 增加版本号闸门，`tests/test_versioning.py`（73 项）固化三处版本号一致性
- 📄 README 与实物对齐：参考资料库实为 **14 大类 65 小节**（262 条表格数据 + 30 条公式与规范说明），单位换算原为 **11 类**（下条已扩充）
- 🔄 单位换算由 11 类扩至 **21 类**：新增流量、密度、动力粘度、运动粘度、表面张力、导热系数、传热系数、比热容、热值、浓度（含 % ↔ mol/L 跨组换算，需密度与摩尔质量）
- 🧱 换算器新增通用基类 `unit_converter_base.UnitConverterPage`：新换算器只声明一张单位表，布局/清空/实时换算/辅助参数重算全部复用（原 11 个换算器每个约 150 行重复代码，改一处要改 11 个文件）
- 🕘 **计算历史增强**：新增时间范围筛选（今天/近 7 天/近 30 天/本月）、列表多选与**批量删除**、按筛选**清空**（二次确认）、**使用统计**（总量/分类分布/计算器排行/日期趋势）、**导出**（CSV 供 Excel 直接打开；Word/PDF 计算书）
- 🛠 历史库层（`history_db.py`）配套扩展：统一筛选口径的查询/计数/统计/删除，时间端点闭合（当天的记录不会被漏掉），批量删除走单条 SQL；新增 `tests/test_history.py`（134 项）直接打真实 SQLite 固化以上行为
- 🛠 资料库补全 5 个新分类的图标（消防安全/水质标准/热工设备/防爆区域/投资估算），分类图标表去重
- ⏱ **倒计时页改造**：卡片颜色改为主题 QSS 驱动（动态属性 `cdState`/`cdSelected`，配色集中在 `theme_manager`）—— 此前背景/边框/文字色写死在控件上，深色主题下卡片文字看不清；**秒针不再整页重建卡片**（此前每秒 deleteLater + 重建全部卡片，拖窗口时更狠），只在数据/筛选/列数变化时重建；日期时间输入改用日历选择器 + 快捷按钮（+1小时/+1天/+7天/+30天）；新增/编辑合并为一个对话框（替代连弹三个输入框）；新增状态筛选（全部/未到期/已过期）、排序（剩余时间/添加时间）、**一键清理已过期**、卡片进度条（创建 → 目标的已等待比例）、到点提醒只响一次；星期文案不再依赖系统 locale；新增 `tests/test_countdowns.py`（183 项）

### v1.5.51 (2026-09-14)

- 🛠 **自动更新机制修复**：客户端只认 Release 的 tag，此前 tag（v1.5.50）与资产名（1.5.51）不一致导致所有老用户都显示"已是最新版本"，更新通道静默失效
- 🛠 下载的资产按原名存盘；安装包（setup.exe）与历史单文件 exe 的升级动作分流，修复自更新把 `ChemCal.exe` 覆盖成安装包的问题
- 🛠 更新临时目录在 `%TEMP%` 被 ACL 限制时自动回退用户目录，配合"以管理员身份运行"解决受控电脑上的"错误 5：拒绝访问"
- 📋 新增 `tests/test_updater.py`（44 项），固化 tag/资产一致性等易错点
- 📄 **版本号规范落地**：新增 [VERSIONING.md](VERSIONING.md) 与 `bump_version.py`，`build_release.py` 增加版本号闸门

### v1.5.50 (2026-09-14)

- ✅ **全量公式核对收官**：45 个计算器的公式、单位、默认值逐批对照 GB 150 / GB 50341 / GB/T 20801 / HG/T 20592 / IAPWS-IF97 / GB 30000 (GHS) 等标准核对修正，19 个回归测试文件固化手算锚点
- ➕ **恢复「常压储罐壁厚」计算器**（工艺设备类）：GB 50341 一英尺法逐圈计算 + NB/T 47003，固定顶/浮顶/内浮顶，底板顶板厚度
- ➖ **移除「法兰查询」演示模块**：原数据仅 4 条 DN100 且与管道间距计算器重复，法兰外径权威数据（PN10~100 × DN10~500）保留于管道间距计算器
- 🛠 **安全阀**：修复 Kd 阀型映射错位（"不带调节圈微启式"误填 0.45，正确 0.30）及初始化顺序异常
- 🛠 **查询类修正**：危险化学品 GHS 分类按 GB 30000 核对（硫酸不再标"毒性物质"，补全 H 语句）；腐蚀速率等级由速率唯一派生（左景伊 4 级制）；发酵废水 COD 物料平衡重复计入修复；L-蛋氨酸 COD 当量 1.073→1.609（含硫氨基酸）
- 🛠 水蒸气物性 steam_iapws 对照 IAPWS-IF97 官方验证表全网格校验（偏差 ≤0.04%），高压区判域修正
- 📦 **分发改版**：剔除死重依赖 scipy / pandas（~200MB），打包由 onefile 单文件改为 onedir + Inno Setup 安装包（52.8MB）与便携 zip（54.6MB）双发行，告别 344MB 单 exe 与临时目录解压

### v1.5.0 (2026-07-14)

- 新增自动更新系统（GitHub Releases API + 静默检测 + 一键下载安装）
- 补充缺失的 fpdf2 依赖

### v1.4.20260623 (2026-06-23)

- 新增发酵搅拌功率、蒸汽空消、发酵废水 COD 估算、蒸汽管道压降/温降、法兰尺寸、夹套/盘管换热、容器贮罐设计、消防水池容积 8 个计算器

### v1.4 (2026-06-02)

- 新增「参考资料库」标签页，全文搜索 + 树形导航
- 循环水计算器增强：多效蒸发器、结晶罐分项计算

### v1.3 (2026-06-01)

- DOCX 报告导出（替代 TXT）、安全阀模式驱动重构、防闪退保护层

### v1.2

- 查询类计算器、历史记录系统

### v1.1

- 水蒸气性质模块、日志系统

### v1.0

- 初始版本发布

## 项目结构

```
ChemCal/
├── main.py                     # 主入口，窗口框架与菜单
├── crash_shield.py             # 防闪退保护层 + 看门狗
├── launcher.py                 # 启动器（异常重启）
├── data_manager.py             # 数据管理（JSON 单例）
├── theme_manager.py            # 主题管理（亮色 / 暗色 / 蓝色）
├── module_loader.py            # 模块动态加载器
├── history_db.py               # 历史记录（SQLite）
├── updater.py                  # 自动更新（GitHub Releases）
├── version.py                  # 版本号唯一来源 + 规范校验
├── VERSIONING.md               # 版本号规范（权威文档）
├── bump_version.py             # 升版本号（校验 + 同步 iss / README）
├── ChemCal.spec                # PyInstaller 打包配置（onedir）
├── ChemCal.iss                 # Inno Setup 安装包脚本
├── build_release.py            # 一键发版（版本闸门 + 打包 + 双产物）
├── requirements.txt
├── ChemCal.ico                 # 应用图标
├── ChemCal.png                 # Logo
│
├── data/                       # 数据文件
│   └── reference_db.json       # 参考资料库
│
├── utils/                      # 公共工具
│   ├── __init__.py
│   └── docx_utils.py           # DOCX 报告生成（ReportExporter）
│
├── modules/
│   ├── chemical_calculations/
│   │   ├── calculators/        # 45 个计算器
│   │   │   ├── steam_property_calculator.py
│   │   │   ├── pressure_drop_calculator.py
│   │   │   ├── heat_exchanger_area_calculator.py
│   │   │   ├── cooling_water_calculator.py  # 循环水（多效蒸发 / 结晶罐）
│   │   │   ├── agitator_calculator.py       # 搅拌功率 & kLa
│   │   │   ├── vessel_design_calculator.py   # 容器设计（GB 150）
│   │   │   └── ...
│   │   ├── steam_iapws.py      # IAPWS-IF97 水蒸气物性
│   │   ├── refrigerant_eos.py  # 制冷剂 PR 状态方程
│   │   └── chemical_calculations_widget.py
│   │
│   ├── reference/              # 参考资料库
│   ├── converter/              # 单位换算器（21 类）
│   ├── history_viewer.py       # 计算历史
│   └── countdowns.py           # 倒计时
│
└── docs/                       # 文档（计划中）
```

## 免责声明

计算结果仅供参考，实际工程应用请由专业工程师审核确认。本软件开源、免费，仅供学习交流使用。

## 许可证

[MIT License](LICENSE) © 2025-2026 ChemCal Team

联系方式：virmuran@163.com
