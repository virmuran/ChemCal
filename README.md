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
    <img alt="version" src="https://img.shields.io/badge/version-1.14.2-green">
    <img alt="stars" src="https://img.shields.io/github/stars/virmuran/ChemCal?style=social">
</div>
<br>

化工工程师的桌面生产力工具

基于 Python + PySide6，集成工程计算器、参考资料库、单位换算与计算历史。

</div>

## 下载与安装

前往 [Releases](https://github.com/virmuran/ChemCal/releases)，按需选择：

| 文件 | 适合谁 | 说明 |
|---|---|---|
| `ChemCal_X.X.X_setup.exe` | 普通用户 | 安装向导（简体中文），下一步装完，开始菜单/桌面快捷方式、控制面板卸载 |
| `ChemCal_X.X.X_portable.zip` | 便携党 | 解压即用，免安装，适合 U 盘 / 无权限环境 |

两种发行均无需安装 Python 环境。用户数据保存在用户目录 `.ChemCal/`，安装版卸载不会删除用户的计算历史与数据。

> **安装时提示“错误 5：拒绝访问”**：少数受管控的电脑（装有终端安全软件、Temp 权限收紧）双击安装包时会提示“安装程序无法创建目录 …\Temp\is-XXXX.tmp，错误 5：拒绝访问”。
> 处理方式：**右键 → 以管理员身份运行**；仍不行则在 cmd 中执行 `set TEMP=C:\Windows\Temp` 后运行；或改用**便携版**（免安装、不写临时目录、无需管理员权限）。

如需从源码运行：

```bash
git clone https://github.com/virmuran/ChemCal.git
cd ChemCal
pip install -r requirements.txt
python main.py
```

## 亮点功能

- 🧪 **工程计算器** — 覆盖物性查询、管道系统、换热设备、容器设计、固液分离、蒸发浓缩与淀粉糖液化、脱色再生、安全消防、制冷热工等类别，每个计算器均支持 DOCX / PDF 计算书一键导出，公式均对照 GB / HG / NB/T 等标准逐项核对并固化回归测试
- 📚 **内置参考资料库** — 化工设计常用规范数据电子化，搜索可**定位到具体数据行**、输入数值可跨全库**反查**，选中数据一键**送入计算器**；含**设备投资报价速查**（常用设备一台设备一节、一行一个规格；网查 + 企业实报价的低 / 中 / 高三档已填好作参考，**「询价实价」列可双击自行填写**，只存本机、可导出备份；另附海外工程附加系数与整线实价参考）与**比重每 0.001 的波美度-糖度换算详表**（糖厂 / 淀粉糖车间可直接用比重计读数查糖度）
- 🔄 **单位换算** — 基础量（长度、重量、面积、体积、流量、温度、速度、进制）+ 力学热工（热能、压强、功率、力）+ 化工物性（密度、动力/运动粘度、表面张力、导热系数、传热系数、比热容、热值、浓度），即输即算
- 📝 **自动计算历史** — SQLite 数据库全程记录，支持按模块筛选和关键词搜索
- 🖥️ **右下角托盘常驻** — 点关闭时可选择**最小化到系统托盘**（程序继续在后台运行）或**直接退出**，可勾选记住选择；托盘图标单击 / 双击唤回窗口，右键可显示主窗口、改工程信息或彻底退出
- 🎨 **三套主题配色** — 亮色 / 暗色 / 蓝色，白天办公不刺眼，夜间低光不伤眼
- 🔒 **数据本地存储** — 不联网、不上传、不收集任何隐私信息，所有数据仅保存在用户目录 `.ChemCal/` 下

<!-- markdownlint-disable -->

<details><summary>展开查看截图</summary>

<p align="center">
  <em>截图待补充 — 欢迎提交 PR！</em>
</p>

</details>

<!-- markdownlint-restore -->

## 使用说明

### 工程计算

启动后默认进入「工程计算」标签页，左侧列表按 物性数据 / 工艺设备 / 流体输送 / 热工制冷 / 安全环保 分类列出全部计算器（右键或管理入口可调整顺序、隐藏暂时不用的），点击即可进入对应计算器。输入参数后点击绿色「计算」按钮，结果实时显示；点击底部「下载 DOCX」或「下载 PDF」导出计算书。

### 参考资料库

切换到「资料库」标签页，左侧按**分组 → 分类 → 小节**浏览，可用**标签**快速筛选。顶部搜索栏有两种用法：

- 输**关键词**：结果树展开到命中的**具体行**并显示片段，选中后表格里命中单元格高亮
- 输**纯数值**（`0.6`、`143.7`、`0.6MPa`）：自动切换**数值反查**，±1% 容差在全库中定位该数值的出处

查到数据后点右侧「**送入计算器**」，可直接填进计算器的对应输入框；计算器里的 📚 按钮则反向跳到对应数据节。数据来源标注 GB / HG / TSG / API 规范编号，方便溯源。

**设备投资报价**（「投资估算」分组）里每台设备一张表，**一行一个规格**：

| 列 | 含义 |
| --- | --- |
| **询价实价** | **供用户自行填写** —— 双击单元格输入询价得到的确定价格（单位：万元） |
| 低 / 中 / 高 | 同规格下的三档参考：低 = 经济配置、中 = 主流配置、高 = 高端配置 |
| 来源与备注 | 该档价格的出处（网查整理 / 行业经验值折算基准） |

「询价实价」是**唯一可编辑的一列**，其余全部只读（资料库数据不会被误改）。填了实价的行，低 / 中 / 高会转灰，表示以实价为准。

> ⚠ **实价仅保存在用户本机** —— 询价结果属于商业信息，软件既不预置也不上传。
> 数据落 `~/.ChemCal/data/equipment_prices.json`，不进安装包、升级不覆盖。
> 标题栏的「**导出实价 / 导入实价**」可备份或换机迁移（导入为并入，不会覆盖本机其它已填的行）。
> 输入只接受数字；「万元」为表格统一口径，请勿填写 `4500元` 这类带单位的写法。

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

欢迎提交 Issue 和 Pull Request。

- **代码规范**：中文注释 + Python 类型注解
- **新增计算器**：参照 `modules/chemical_calculations/calculators/` 中的现有实现，继承 `CalculatorBase`
- **版本号规范**：版本号采用 `主.次.修订` 三段式，**只允许手改 `version.py`**，其余位置由脚本同步。完整标准与升号判定见 [VERSIONING.md](VERSIONING.md)。升号命令：
  `.venv/Scripts/python.exe bump_version.py patch "修复 xxx"`（patch / minor / major 三选一；`--dry-run` 可先预览）
- **发版打包**：升号后运行 `.venv/Scripts/python.exe build_release.py`，一键完成 PyInstaller + Inno Setup 安装包 + 便携 zip，产物在 `installer/` 与 `dist/`。
  脚本内置**版本号闸门**：格式不合法、版本号没前进、与已有 tag 撞号，都会直接中断打包。
  ⚠ **发布时 Release 的 tag 必须与 `version.py` 完全一致**（如 `v1.6.0`）：客户端自动更新只读 tag，资产文件名不参与比较；tag 写错版本号（例如资产是 1.5.51、tag 仍写 v1.5.50），所有老用户都会显示"已是最新版本"。tag 也不要写成 `update` 这类自由文本，解析不出数字会让更新通道整体静默失效。脚本末尾会做一次远端一致性检查，发现不一致会直接提示。另外 Draft / Pre-release 不会被更新器识别，必须 Publish。
- **新增参考数据**：按 `data/reference_db.json` 格式追加条目

### 贡献/参与者

感谢所有参与开发的朋友。

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

## 更新日志

完整更新日志见 [`CHANGELOG.md`](CHANGELOG.md)。

## 免责声明

计算结果仅供参考，实际工程应用请由专业工程师审核确认。本软件开源、免费，仅供学习交流使用。

## 许可证

[MIT License](LICENSE) © 2025-2026 ChemCal Team

联系方式：virmuran@163.com
