# CalcE/main.py
import sys
import os
import traceback
from datetime import datetime

# 先安装防闪退保护层（必须在 QApplication 创建之前）
from crash_shield import install_crash_shield, SafeApplication
install_crash_shield()

# 将项目根目录加入 sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
for path in [ROOT_DIR, os.path.join(ROOT_DIR, "modules"), os.path.join(ROOT_DIR, "modules", "converter")]:
    if path not in sys.path:
        sys.path.insert(0, path)

from loguru import logger
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QMessageBox, QStatusBar, QLabel, QDialog, QScrollArea, QPushButton,
    QHBoxLayout
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QFont, QDesktopServices

from data_manager import DataManager
from theme_manager import ThemeManager
from module_loader import ModuleLoader

# 配置日志：输出到控制台 + 写入文件
_log_dir = os.path.join(os.path.expanduser("~"), ".calce", "logs")
os.makedirs(_log_dir, exist_ok=True)
logger.add(
    os.path.join(_log_dir, "calce_{time:YYYY-MM-DD}.log"),
    rotation="1 day",
    retention="7 days",
    encoding="utf-8",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)


class CalcE(QMainWindow):
    """CalcE 主窗口"""

    # 模块配置：(模块路径, 类名, 标签名)
    MODULES_CONFIG = [
        ("modules.chemical_calculations", "ChemicalCalculationsWidget", "工程计算"),
        ("modules.history_viewer", "HistoryViewer", "计算历史"),
        ("modules.converter.converter_widget", "ConverterWidget", "换算器"),
        ("modules.countdowns", "CountdownsWidget", "倒计时"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CalcE - 个人生产力工具")
        # 设置窗口图标
        from PySide6.QtGui import QIcon
        self.setWindowIcon(QIcon(resource_path("CalcE.ico")))
        # 自适应屏幕大小，留出边距避免超出
        from PySide6.QtGui import QScreen
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = min(1600, avail.width() - 80)
            h = min(970, avail.height() - 80)
            x = (avail.width() - w) // 2
            y = (avail.height() - h) // 2
            self.setGeometry(x, y, w, h)
        else:
            self.setGeometry(160, 50, 1600, 970)

        self.theme_manager = ThemeManager()
        self.data_manager = DataManager.get_instance()
        self.modules = {}          # tab_name -> widget
        self._module_status = {}   # tab_name -> bool (加载成功与否)

        self._setup_ui()
        self._load_settings()
        logger.info("CalcE 启动成功，加载模块数: {}", len(self.modules))

    # ------------------------------------------------------------------ UI

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        self._create_modules()
        self._setup_menu()
        self._setup_status_bar()

        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.theme_manager.theme_changed.connect(self._apply_theme)

    def _create_modules(self):
        for module_file, class_name, tab_name in self.MODULES_CONFIG:
            try:
                widget = ModuleLoader.load_module(module_file, class_name, self, self.data_manager)
                self.tab_widget.addTab(widget, tab_name)
                self.modules[tab_name] = widget
                self._module_status[tab_name] = True
                logger.info("模块加载成功: {}", tab_name)
            except Exception as e:
                logger.error("模块加载失败: {} | {}", tab_name, e)
                error_widget = ModuleLoader.create_error_widget(f"{tab_name} 加载失败", str(e))
                self.tab_widget.addTab(error_widget, tab_name)
                self._module_status[tab_name] = False

    # ------------------------------------------------------------------ 菜单

    def _setup_menu(self):
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")
        self._add_action(file_menu, "备份数据", self._backup_data)
        self._add_action(file_menu, "刷新所有模块", self._refresh_all_modules)
        file_menu.addSeparator()
        exit_act = self._add_action(file_menu, "退出", self.close)
        exit_act.setShortcut("Ctrl+Q")

        # 主题菜单
        theme_menu = menubar.addMenu("主题")
        for name in self.theme_manager.get_theme_names():
            act = QAction(f"{name.capitalize()}主题", self)
            act.triggered.connect(lambda checked, n=name: self.theme_manager.set_theme(n))
            theme_menu.addAction(act)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        self._add_action(help_menu, "用户手册", self._show_user_manual)
        self._add_action(help_menu, "常见问题", self._show_faq)
        self._add_action(help_menu, "系统信息", self._show_system_info)
        self._add_action(help_menu, "查看日志", self._show_logs)
        self._add_action(help_menu, "开源许可", self._show_license)
        self._add_action(help_menu, "关于 CalcE", self._show_about)

    @staticmethod
    def _add_action(menu, text, slot):
        act = QAction(text, menu.parent() if hasattr(menu, 'parent') else None)
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    # ------------------------------------------------------------------ 状态栏

    def _setup_status_bar(self):
        bar = QStatusBar()
        self.setStatusBar(bar)

        bar.addWidget(QLabel("CalcE - 您的个人生产力助手"))
        bar.addPermanentWidget(QLabel("|"))
        self.theme_label = QLabel(f"主题: {self.theme_manager.current_theme.capitalize()}")
        bar.addPermanentWidget(self.theme_label)
        bar.addPermanentWidget(QLabel("|"))
        self.time_label = QLabel()
        bar.addPermanentWidget(self.time_label)

        self._update_time()
        self._time_timer = QTimer(self)
        self._time_timer.timeout.connect(self._update_time)
        self._time_timer.start(1000)

    def _update_time(self):
        self.time_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # ------------------------------------------------------------------ 设置

    def _load_settings(self):
        settings = self.data_manager.get_settings()
        self.theme_manager.set_theme(settings.get("theme", "light"))
        QApplication.setFont(QFont("Microsoft YaHei", 10))
        self.tab_widget.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))

    # ------------------------------------------------------------------ 事件

    def _on_tab_changed(self, index):
        if index >= 0:
            self.statusBar().showMessage(f"当前标签页: {self.tab_widget.tabText(index)}", 3000)
            widget = self.tab_widget.widget(index)
            if hasattr(widget, "on_activate"):
                widget.on_activate()

    def _apply_theme(self, theme_name):
        QApplication.instance().setStyleSheet(self.theme_manager.get_theme())
        self.theme_label.setText(f"主题: {theme_name.capitalize()}")
        settings = self.data_manager.get_settings()
        settings["theme"] = theme_name
        self.data_manager.update_settings(settings)
        logger.info("主题切换为: {}", theme_name)

    # ------------------------------------------------------------------ 功能

    def _refresh_all_modules(self):
        count = 0
        for name, widget in self.modules.items():
            if hasattr(widget, "refresh"):
                try:
                    widget.refresh()
                    count += 1
                except Exception as e:
                    logger.error("模块刷新失败: {} | {}", name, e)
        QMessageBox.information(self, "刷新完成", f"已刷新 {count} 个模块")

    def _backup_data(self):
        import shutil
        src = self.data_manager.data_file
        if not os.path.exists(src):
            QMessageBox.warning(self, "备份失败", "数据文件不存在")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = src.replace(".json", f"_backup_{ts}.json")
        try:
            shutil.copy2(src, dst)
            logger.info("数据备份成功: {}", dst)
            QMessageBox.information(self, "备份成功", f"数据已备份至:\n{dst}")
        except Exception as e:
            logger.error("数据备份失败: {}", e)
            QMessageBox.warning(self, "备份失败", str(e))

    def closeEvent(self, event):
        if hasattr(self, "_time_timer"):
            self._time_timer.stop()
        for name, widget in self.modules.items():
            if hasattr(widget, "save_data"):
                try:
                    widget.save_data()
                except Exception as e:
                    logger.error("保存模块数据失败: {} | {}", name, e)
        try:
            self.data_manager._save_data()
        except Exception as e:
            logger.error("主数据保存失败: {}", e)
        logger.info("CalcE 正常退出")
        event.accept()

    # ------------------------------------------------------------------ 对话框

    def _show_scrollable_dialog(self, title, content):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(700, 500)
        layout = QVBoxLayout(dialog)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        label = QLabel()
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setText(content)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        scroll.setWidget(label)

        btn = QPushButton("确定")
        btn.clicked.connect(dialog.accept)

        layout.addWidget(scroll)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        dialog.exec()

    def _show_user_manual(self):
        text = """<h2>CalcE 用户手册</h2>
<h3>欢迎使用 CalcE 化工工程师生产力工具！</h3><br>

<b>功能模块：</b><br>
- <b>工程计算</b>：38+ 化工计算器，涵盖管道、换热、泵、制冷等<br>
- <b>换算器</b>：长度、重量、温度、压力等多类单位换算<br>

- <b>待办事项</b>：任务管理，优先级标记<br>
- <b>笔记</b>：分文件夹笔记管理，支持搜索<br>
- <b>倒计时</b>：多事件倒计时，实时更新<br>
- <b>今年余额</b>：年度时间进度可视化<br><br>

<b>基本操作：</b><br>
- 顶部标签页切换功能模块<br>
- 菜单「主题」切换亮/暗/蓝三套主题，自动保存<br>
- 菜单「文件→备份数据」备份 JSON 数据文件<br>
- 数据自动保存在 <code>~/.calce/</code> 目录<br><br>

<b>工程计算使用：</b><br>
1. 选择计算类别（左侧列表）<br>
2. 在右侧填写参数<br>
3. 点击「计算」查看结果<br>
4. 压降计算支持导出 PDF 计算书<br><br>

<b>数据安全：</b><br>
- 所有数据仅本地存储，不上传任何服务器<br>
- 日志保存在 <code>~/.calce/logs/</code>，保留 7 天<br><br>

<b>联系方式：</b> virmuran@163.com"""
        self._show_scrollable_dialog("用户手册", text)

    def _show_faq(self):
        text = """<h2>常见问题</h2><br>

<b>Q: 依赖怎么安装？</b><br>
A: <code>pip install -r requirements.txt</code>，需要 Python 3.8+ 和 PySide6 6.5+。<br><br>

<b>Q: 数据存在哪里？</b><br>
A: Windows 下存储在 <code>C:\\Users\\[用户名]\\AppData\\Roaming\\CalcE\\CalcE_data.json</code>。<br><br>

<b>Q: 如何备份数据？</b><br>
A: 菜单「文件→备份数据」，备份文件与原文件同目录，带时间戳命名。<br><br>

<b>Q: 某个模块加载失败怎么办？</b><br>
A: 查看「帮助→查看日志」确认错误原因，通常是依赖未安装或文件缺失。<br><br>

<b>Q: PDF 计算书生成失败？</b><br>
A: 需要安装 reportlab：<code>pip install reportlab</code>。<br><br>

<b>Q: 支持哪些操作系统？</b><br>
A: 主要在 Windows 10/11 测试，理论上支持 macOS 和 Linux（PySide6 跨平台）。<br><br>

<b>Q: 计算结果能用于实际工程吗？</b><br>
A: 结果仅供参考，实际工程须由专业工程师审核确认。<br><br>

<b>反馈问题：</b> virmuran@163.com"""
        self._show_scrollable_dialog("常见问题", text)

    def _show_system_info(self):
        import platform
        try:
            import psutil
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(os.path.expanduser("~"))
            hw = (
                f"- 物理内存：{mem.total / 1024**3:.1f} GB（可用 {mem.available / 1024**3:.1f} GB，使用率 {mem.percent}%）<br>"
                f"- 磁盘总量：{disk.total / 1024**3:.1f} GB（可用 {disk.free / 1024**3:.1f} GB，使用率 {disk.percent}%）<br>")
        except ImportError:
            hw = "- psutil 未安装，硬件信息不可用<br>"
        data_file = self.data_manager.data_file
        file_info = ""
        if os.path.exists(data_file):
            sz = os.path.getsize(data_file)
            mt = datetime.fromtimestamp(os.path.getmtime(data_file)).strftime("%Y-%m-%d %H:%M:%S")
            file_info = f"- 数据文件：{data_file}<br>- 文件大小：{sz} 字节 ({sz/1024:.1f} KB)<br>- 最后修改：{mt}<br>"
        loaded = sum(1 for ok in self._module_status.values() if ok)
        total = len(self._module_status)

        text = f"""<h2>系统信息</h2><br>
<b>操作系统：</b><br>
- {platform.system()} {platform.release()}（{platform.machine()}）<br>
- {platform.version()}<br><br>

<b>Python 环境：</b><br>
- Python {platform.python_version()}（{platform.python_implementation()}）<br><br>

<b>硬件信息：</b><br>
- 处理器：{platform.processor() or '未知'}<br>
{hw}<br>

<b>CalcE 信息：</b><br>
- 版本：v1.3.20260522<br>
- 数据目录：{os.path.dirname(data_file)}<br>
- 已加载模块：{loaded}/{total}<br>
- 运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br><br>

<b>数据文件：</b><br>
{file_info}"""
        self._show_scrollable_dialog("系统信息", text)

    def _show_logs(self):
        log_dir = os.path.join(os.path.expanduser("~"), ".calce", "logs")
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"calce_{today}.log")

        status_lines = "".join(
            f"- {name}：{'已加载' if ok else '加载失败'}<br>" for name, ok in self._module_status.items()
        )

        if os.path.exists(log_file):
            try:
                with open(log_file, encoding="utf-8") as f:
                    recent = f.readlines()[-50:]
                log_content = "".join(recent).replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            except Exception:
                log_content = "读取日志文件失败"
        else:
            log_content = "今日暂无日志记录"
        text = f"""<h2>运行日志</h2><br>
<b>模块加载状态：</b><br>
{status_lines}<br>

<b>日志文件：</b> <code>{log_file}</code><br>
<b>日志目录：</b> <code>{log_dir}</code><br><br>

<b>最近 50 条日志：</b><br>
<pre style="font-size:11px; background:#f5f5f5; padding:8px; border-radius:4px;">{log_content}</pre>"""
        self._show_scrollable_dialog("查看日志", text)

    def _show_license(self):
        text = """<h2>开源许可协议</h2><br>
<b>CalcE - MIT License</b><br>
Copyright 2025 CalcE Team<br><br>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:<br><br>

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.<br><br>

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.<br><br>

<b>第三方依赖许可：</b><br>
- PySide6 - LGPLv3（https://doc.qt.io/qt-6/licensing.html）<br>
- NumPy - BSD-3-Clause<br>
- SciPy - BSD-3-Clause<br>
- ReportLab - BSD-like（https://www.reportlab.com/docs/reportlab-userguide.pdf）<br>
- psutil - BSD-3-Clause<br>
- Loguru - MIT<br><br>

<b>源码：</b> https://github.com/virmuran/CalcE<br>
<b>联系：</b> virmuran@163.com"""
        self._show_scrollable_dialog("开源许可", text)

    def _show_about(self):
        text = """<h2>CalcE - 化工工程师个人生产力工具</h2>
<h3>v1.3.20260522</h3><br>
Copyright 2025-2026 CalcE Team | virmuran@163.com<br><br>

<b>核心功能：</b><br>
- 工程计算（换热、管道、泵、换热器面积/未知侧设计、安全阀等）<br>
- 计算历史（记录查询、筛选、详情查看）<br>
- 换算器（多类单位换算）<br>
- 倒计时<br><br>

<b>数据安全：</b><br>
- 数据仅本地存储，不联网，不收集隐私<br>
- 代码 MIT 开源：https://github.com/virmuran/CalcE<br><br>

<b>更新日志：</b><br>
<b>v1.3</b> - 新增"未知侧设计"换热器模式；防闪退保护层 crash_shield；看门狗自动重启；修复 QListWidget 内存违例；UI 全面规范化<br>
<b>v1.2</b> - 新增查询类计算器（溶解度/闪点/腐蚀）；历史记录系统上线；精度升级（IAPWS-IF97 蒸汽物性）<br>
<b>v1.1</b> - 帮助菜单、水蒸气性质模块、真实日志系统<br>
<b>v1.0</b> - 初始版本发布<br><br>

<b>免责声明：</b> 计算结果仅供参考，实际工程应用请由专业工程师审核确认。"""
        self._show_scrollable_dialog("关于 CalcE", text)


def resource_path(relative_path):
    """获取资源文件的绝对路径（兼容 PyInstaller 打包和直接运行）"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def main():
    app = SafeApplication(sys.argv)
    app.setApplicationName("CalcE")
    app.setApplicationVersion("1.3")
    app.setOrganizationName("CalcE")

    try:
        window = CalcE()
        window.show()
        return app.run()
    except Exception as e:
        logger.critical("应用程序启动失败: {}", e)
        traceback.print_exc()
        QMessageBox.critical(None, "启动失败", f"应用程序启动失败:\n{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
