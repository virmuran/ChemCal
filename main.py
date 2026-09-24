# ChemCal/main.py
import sys
import os
import threading
import traceback
from datetime import datetime

# 版本号常量和防闪退保护层
from version import VERSION as CHEMICAL_VERSION
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
    QHBoxLayout, QProgressBar, QDialogButtonBox, QTextEdit
)
from PySide6.QtGui import QAction, QFont, QDesktopServices
from PySide6.QtCore import Qt, QTimer, QUrl, QMetaObject, Q_ARG, Slot, QThread, Signal

from data_manager import DataManager
from theme_manager import ThemeManager
from module_loader import ModuleLoader

try:
    from modules.reference.ref_exchange import EXCHANGE
except Exception:                                    # 资料库缺失时不影响主程序
    EXCHANGE = None
from updater import (
    check_for_updates, download_update, create_update_bat,
    is_frozen, get_app_dir, GITHUB_REPO,
    classify_asset, get_last_check, get_temp_dir,
    DownloadIncomplete, human_size
)

# 配置日志：输出到控制台 + 写入文件
_log_dir = os.path.join(os.path.expanduser("~"), ".ChemCal", "logs")
os.makedirs(_log_dir, exist_ok=True)
logger.add(
    os.path.join(_log_dir, "ChemCal_{time:YYYY-MM-DD}.log"),
    rotation="1 day",
    retention="7 days",
    encoding="utf-8",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)


class ChemCal(QMainWindow):
    """ChemCal 主窗口"""

    # 模块配置：(模块路径, 类名, 标签名)
    MODULES_CONFIG = [
        ("modules.chemical_calculations", "ChemicalCalculationsWidget", "工程计算"),
        ("modules.history_viewer", "HistoryViewer", "计算历史"),
        ("modules.converter.converter_widget", "ConverterWidget", "换算器"),
        ("modules.reference.reference_widget", "ReferenceWidget", "资料库"),
    ]

    def __init__(self):
        super().__init__()
        self.hide()  # 立刻隐藏，避免原生窗口句柄闪现
        self.setWindowTitle("ChemCal - 化算")
        # 设置窗口图标
        from PySide6.QtGui import QIcon
        self.setWindowIcon(QIcon(resource_path("ChemCal.ico")))
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
        # 启动后延迟1秒检查更新（确保 UI 就绪）
        QTimer.singleShot(1000, lambda: self._check_version(silent=True))
        logger.info("ChemCal 启动成功，加载模块数: {}", len(self.modules))

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

        # 资料库 ↔ 计算器 的取值交接（详见 modules/reference/ref_exchange.py）
        if EXCHANGE is not None:
            EXCHANGE.fill_requested.connect(self._on_reference_fill)
            EXCHANGE.section_requested.connect(self._on_reference_section)

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
        self._add_action(help_menu, "检查更新", lambda: self._check_version(silent=False))
        self._add_action(help_menu, "用户手册", self._show_user_manual)
        self._add_action(help_menu, "常见问题", self._show_faq)
        self._add_action(help_menu, "系统信息", self._show_system_info)
        self._add_action(help_menu, "查看日志", self._show_logs)
        self._add_action(help_menu, "开源许可", self._show_license)
        self._add_action(help_menu, "关于 ChemCal", self._show_about)

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

        bar.addWidget(QLabel("ChemCal - 化工工程师的桌面生产力工具"))
        bar.addPermanentWidget(QLabel("|"))
        self.theme_label = QLabel(f"主题: {self.theme_manager.current_theme.capitalize()}")
        bar.addPermanentWidget(self.theme_label)
        bar.addPermanentWidget(QLabel("|"))
        self.update_label = QLabel()
        self.update_label.setStyleSheet("font-size:11px; padding:0 4px;")
        bar.addPermanentWidget(self.update_label)
        bar.addPermanentWidget(QLabel("|"))
        self.time_label = QLabel()
        bar.addPermanentWidget(self.time_label)

        self._update_time()
        self._time_timer = QTimer(self)
        self._time_timer.timeout.connect(self._update_time)
        self._time_timer.start(1000)

    def _update_time(self):
        self.time_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # ------------------------------------------------------------------ 版本检查

    def _check_version(self, silent=False):
        """后台线程检查 GitHub 是否有新版本。

        silent=True: 静默检查（启动时），仅状态栏提示
        silent=False: 手动检查，弹出对话框
        """
        if silent:
            threading.Thread(target=self._do_version_check, args=(silent,), daemon=True).start()
        else:
            self.statusBar().showMessage("正在检查更新...", 3000)
            threading.Thread(target=self._do_version_check, args=(silent,), daemon=True).start()

    def _do_version_check(self, silent):
        has_update, latest, url, notes = check_for_updates()
        if has_update:
            if silent:
                QMetaObject.invokeMethod(
                    self, "_show_update_banner",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, latest), Q_ARG(str, url)
                )
            else:
                QMetaObject.invokeMethod(
                    self, "_show_update_dialog",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, latest), Q_ARG(str, url), Q_ARG(str, notes)
                )
        else:
            if not silent:
                msg = notes or "当前已是最新版本 v" + CHEMICAL_VERSION
                if not notes:
                    # 无更新时把远端 tag 一并显示，便于发现「tag 写错」这类发布失误
                    info = get_last_check()
                    tag = info.get("tag", "")
                    if tag:
                        msg += f"\n\nGitHub 最新发布：v{tag}"
                    if info.get("version_mismatch"):
                        msg += (
                            "\n\n⚠ 该 Release 的资产名为「"
                            f"{info.get('asset_name')}」（版本 {info.get('asset_version')}），"
                            f"与 tag v{tag} 不一致。\n"
                            "自动更新只识别 tag，请在 Releases 页把 tag 改为对应版本。"
                        )
                QMetaObject.invokeMethod(
                    self, "_show_no_update",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, msg)
                )

    @Slot(str, str)
    def _show_update_banner(self, latest, url):
        """状态栏新版本提示"""
        self.update_label.setText(f"⬆ v{latest} 可用")
        self.update_label.setStyleSheet(
            "color:#e67e22; font-size:11px; font-weight:bold;"
            "padding:0 4px; text-decoration:underline;"
        )
        self.update_label.setToolTip(f"GitHub: {GITHUB_REPO} — v{latest}\n点击查看详情")
        self.update_label.mousePressEvent = lambda e: self._show_update_dialog(latest, url, "")
        self.update_label.setCursor(Qt.PointingHandCursor)

    @Slot(str)
    def _show_no_update(self, msg):
        """没有更新的提示"""
        QMessageBox.information(self, "检查更新", msg)

    @Slot(str, str, str)
    def _show_update_dialog(self, latest, url, notes):
        """弹出更新对话框"""

        # 注意：pack 和 col 这种简单的二维布局，直接用 QVBoxLayout 即可
        # 无需引入复杂的 grid 依赖
        update_dialog = QDialog(self)
        update_dialog.setWindowTitle("发现新版本")
        update_dialog.setMinimumSize(480, 360)

        layout = QVBoxLayout(update_dialog)
        layout.setSpacing(12)

        # 标题行
        title_lbl = QLabel(f"<h2>发现新版本 v{latest}</h2>")
        title_lbl.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title_lbl)

        cur_lbl = QLabel(f"当前版本：v{CHEMICAL_VERSION}")
        layout.addWidget(cur_lbl)

        # 更新方式（安装包 / 便携包的动作不同，提前告知）
        _info = get_last_check()
        _kind = _info.get("asset_kind", "")
        _kind_text = {
            "installer": "安装包 — 下载后启动安装向导，自动覆盖升级",
            "portable": "便携压缩包 — 下载后解压覆盖原目录",
        }.get(_kind, "更新文件")
        _size_text = f"（{human_size(_info.get('asset_size'))}）" if _info.get("asset_size") else ""
        kind_lbl = QLabel(f"更新方式：{_kind_text}{_size_text}")
        layout.addWidget(kind_lbl)

        # 更新日志（截取前 2000 字）
        if notes:
            notes_lbl = QTextEdit()
            notes_lbl.setReadOnly(True)
            notes_lbl.setPlainText(notes[:2000])
            notes_lbl.setMaximumHeight(180)
            layout.addWidget(notes_lbl)

        # 按钮区
        btn_layout = QHBoxLayout()
        later_btn = QPushButton("稍后提醒")
        later_btn.clicked.connect(update_dialog.reject)
        update_btn = QPushButton("立即更新")
        update_btn.setStyleSheet(
            "QPushButton { background:#27ae60; color:white; font-weight:bold;"
            "padding:8px 20px; border-radius:4px; }"
            "QPushButton:hover { background:#219955; }"
        )
        update_btn.clicked.connect(lambda: self._start_download_update(update_dialog, latest, url))
        btn_layout.addStretch()
        btn_layout.addWidget(later_btn)
        btn_layout.addWidget(update_btn)
        layout.addLayout(btn_layout)

        update_dialog.exec()

    def _start_download_update(self, parent_dialog, latest, url):
        """开始下载更新，切换为进度视图"""
        # 旧下载线程仍在跑则不重复启动（QThread 新建后旧线程被 GC 会导致段错误闪退）
        if getattr(self, "_download_thread", None) is not None and self._download_thread.isRunning():
            return

        parent_dialog.setWindowTitle(f"正在下载 v{latest}...")

        # 沿用 Release 里的资产文件名：setup.exe 与便携 zip 的后续动作不同，名字必须留住
        asset_name = get_last_check().get("asset_name") or f"ChemCal_v{latest}.exe"
        # 资产真实字节数：下载后据此校验完整性（企业网络出口会把长响应截断在 50 MiB）
        expected_size = int(get_last_check().get("asset_size") or 0)
        self._pending_latest = latest

        # 清空旧内容，换成进度界面
        layout = parent_dialog.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # 递归清除子布局
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        status_lbl = QLabel(f"正在下载 v{latest}（{asset_name}）...")
        status_lbl.setStyleSheet("font-size:13px;")
        layout.addWidget(status_lbl)

        size_lbl = QLabel(
            f"文件大小：{human_size(expected_size)}" if expected_size
            else "文件大小：未知（将按响应头校验）"
        )
        size_lbl.setObjectName("mutedLabel")          # 由主题接管颜色，避免硬编码
        layout.addWidget(size_lbl)

        progress = QProgressBar()
        progress.setMinimum(0)
        progress.setMaximum(100)
        progress.setTextVisible(True)
        progress.setStyleSheet(
            "QProgressBar { border:1px solid #ddd; border-radius:4px; text-align:center; }"
            "QProgressBar::chunk { background:#27ae60; border-radius:3px; }"
        )
        layout.addWidget(progress)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(parent_dialog.reject)
        cancel_layout = QHBoxLayout()
        cancel_layout.addStretch()
        cancel_layout.addWidget(cancel_btn)
        layout.addLayout(cancel_layout)

        # 下载线程
        class DownloadThread(QThread):
            progress = Signal(int, int)  # current, total
            finished_path = Signal(str)
            error = Signal(str)

            def __init__(self, url, save_path, expected_size=0):
                super().__init__()
                self.url = url
                self.save_path = save_path
                self.expected_size = expected_size

            def run(self):
                try:
                    def cb(done, total):
                        self.progress.emit(done, total)
                    download_update(self.url, self.save_path,
                                    progress_callback=cb,
                                    expected_size=self.expected_size)
                    self.finished_path.emit(self.save_path)
                except DownloadIncomplete as e:
                    # 用前缀区分「下载不完整」与普通网络错误，好给出不同处置建议
                    self.error.emit(f"TRUNCATED|{e}")
                except Exception as e:
                    self.error.emit(str(e))

        save_path = os.path.join(get_temp_dir(), asset_name)
        self._download_thread = DownloadThread(url, save_path, expected_size)

        self._download_thread.progress.connect(
            lambda cur, tot: progress.setValue(int(cur / tot * 100)) if tot > 0 else None
        )
        self._download_thread.finished_path.connect(
            lambda p: self._on_download_complete(parent_dialog, p)
        )
        self._download_thread.error.connect(
            lambda e: self._on_download_error(parent_dialog, e)
        )
        self._download_thread.start()

    def _on_download_complete(self, dialog, filepath):
        """下载完成，按资产类型选择落地方式（安装包 / 便携 zip / 单文件 exe）"""
        dialog.close()

        kind = classify_asset(os.path.basename(filepath))
        new_ver = getattr(self, "_pending_latest", "")

        # 便携 zip：整目录替换无法自动完成，打开所在目录引导手工解压
        if kind == "portable":
            QMessageBox.information(
                self, "下载完成",
                f"便携版已下载到：\n{filepath}\n\n"
                "便携版是压缩包：解压后覆盖原程序目录即可完成升级。\n"
                "（安装版用户请改下载 Releases 页的 setup.exe，可自动升级）"
            )
            os.startfile(os.path.dirname(filepath))
            return

        if not is_frozen():
            # Python 源码运行模式：无法自我替换
            if kind == "installer":
                reply = QMessageBox.question(
                    self, "下载完成",
                    f"安装包已下载到：\n{filepath}\n\n当前为源码运行模式，是否直接运行安装包？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    os.startfile(filepath)
                return
            reply = QMessageBox.question(
                self, "下载完成",
                f"更新文件已下载到：\n{filepath}\n\n"
                "当前为源码运行模式，无法自动替换。\n是否打开文件所在目录？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                os.startfile(os.path.dirname(filepath))
            return

        # 安装包：交给安装向导覆盖升级（不能把 setup.exe 当成 ChemCal.exe 去替换）
        if kind == "installer":
            reply = QMessageBox.question(
                self, "下载完成",
                f"ChemCal v{CHEMICAL_VERSION} → v{new_ver} 安装包已就绪\n\n"
                "点击「安装并重启」将关闭当前程序并启动安装向导，\n"
                "由安装向导自动覆盖升级（计算历史与设置不受影响）。",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                bat = create_update_bat(filepath, get_app_dir())
                os.startfile(bat)
                self.close()
            return

        # 历史发行的单文件 exe：关闭后自动替换并重启
        reply = QMessageBox.question(
            self, "下载完成",
            f"ChemCal v{CHEMICAL_VERSION} → 新版本已就绪\n\n"
            "点击「安装并重启」将关闭当前程序，\n自动替换并启动新版本。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            bat = create_update_bat(filepath, get_app_dir())
            os.startfile(bat)
            self.close()

    def _on_download_error(self, dialog, error_msg):
        """下载失败：区分「网络截断」与普通错误，给不同的处置建议"""
        dialog.close()

        # 下载不完整（企业网络出口常把长响应掐断在固定大小）：
        # 残件已保留，重试会自动续传，也可直接去 Releases 页手动下载
        if error_msg.startswith("TRUNCATED|"):
            detail = error_msg.split("|", 1)[1]
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("下载不完整")
            box.setText("更新包下载不完整，已中止（不会启动残缺的安装程序）")
            box.setInformativeText(
                f"{detail}\n\n"
                "常见原因：公司网络出口/代理会把较大的下载掐断。\n"
                "已下载的部分会保留，点「立即更新」重试即可自动接着下；\n"
                "也可以直接打开 Releases 页面手动下载。"
            )
            retry_btn = box.addButton("重试", QMessageBox.AcceptRole)
            open_btn = box.addButton("打开下载页", QMessageBox.ActionRole)
            box.addButton("关闭", QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is retry_btn:
                self._check_version(silent=False)
            elif box.clickedButton() is open_btn:
                QDesktopServices.openUrl(
                    QUrl(f"https://github.com/{GITHUB_REPO}/releases/latest"))
            return

        QMessageBox.warning(self, "下载失败", f"更新下载失败：\n{error_msg}\n\n请稍后重试或手动访问 GitHub 下载。")

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

    # ── 资料库 ↔ 计算器 取值交接 ──────────────────────────────────

    def _on_reference_fill(self, module_name, field, value):
        """资料库「送入计算器」：切到工程计算 → 打开目标计算器 → 填进输入框。"""
        page = self.modules.get("工程计算")
        if page is None:
            return
        try:
            self.tab_widget.setCurrentWidget(page)          # 触发 on_activate
            calc = page.open_calculator(module_name)        # 含惰性实例化
            if calc is not None and hasattr(calc, "apply_reference_value"):
                calc.apply_reference_value(field, value)
                self.statusBar().showMessage(
                    f"已从资料库取值 {value} → {getattr(calc, '_calc_meta', {}).get('name', module_name)}",
                    4000)
        except Exception as e:
            logger.error("资料库→计算器 失败: {} {} {} | {}", module_name, field, value, e)

    def _on_reference_section(self, category, title):
        """计算器 📚 按钮：切到资料库并定位到该节。"""
        ref = self.modules.get("资料库")
        if ref is None:
            return
        try:
            self.tab_widget.setCurrentWidget(ref)
            if hasattr(ref, "focus_section"):
                ok = ref.focus_section(title, category)
                if not ok:
                    logger.warning("资料库未找到条目: {} / {}", category, title)
        except Exception as e:
            logger.error("计算器→资料库 失败: {} {} | {}", category, title, e)

    def _apply_theme(self, theme_name):
        QApplication.instance().setStyleSheet(self.theme_manager.get_theme())
        self.theme_label.setText(f"主题: {theme_name.capitalize()}")

        # 通知各页面重渲染富文本内容（HTML 里的颜色取自主题，换了主题必须重画，
        # 否则已显示的详情会留着旧主题的配色 —— 深色下就成了"深底压深字"）
        for _name, _widget in getattr(self, "modules", {}).items():
            hook = getattr(_widget, "on_theme_changed", None)
            if callable(hook):
                try:
                    hook()
                except Exception as e:
                    logger.warning("{} 主题重渲染失败: {}", _name, e)
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
        logger.info("ChemCal 正常退出")
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
        text = """<h2>ChemCal 用户手册</h2>
<h3>欢迎使用 ChemCal 化工工程师生产力工具！</h3><br>

<b>功能模块：</b><br>
- <b>工程计算</b>：化工计算器集 —— 覆盖管道、换热、泵、容器、固液分离、蒸发浓缩、淀粉糖液化、安全消防、制冷热工等<br>
- <b>计算历史</b>：记录查询、筛选、详情查看，支持计算书导出<br>
- <b>换算器</b>：长度、重量、温度、压力、浓度等多类单位换算<br>
- <b>资料库</b>：规范数据全文搜索，快速查表<br><br>

<b>基本操作：</b><br>
- 顶部标签页切换功能模块<br>
- 菜单「主题」切换亮/暗/蓝三套主题，自动保存<br>
- 菜单「文件→备份数据」备份 JSON 数据文件<br>
- 数据自动保存在 <code>~/.ChemCal/</code> 目录<br><br>

<b>工程计算使用：</b><br>
1. 选择计算类别（左侧列表）<br>
2. 在右侧填写参数<br>
3. 点击「计算」查看结果<br>
4. 压降计算支持导出 PDF 计算书<br><br>

<b>数据安全：</b><br>
- 所有数据仅本地存储，不上传任何服务器<br>
- 日志保存在 <code>~/.ChemCal/logs/</code>，保留 7 天<br><br>

<b>联系方式：</b> virmuran@163.com"""
        self._show_scrollable_dialog("用户手册", text)

    def _show_faq(self):
        text = """<h2>常见问题</h2><br>

<b>Q: 依赖怎么安装？</b><br>
A: <code>pip install -r requirements.txt</code>，需要 Python 3.8+ 和 PySide6 6.5+。<br><br>

<b>Q: 数据存在哪里？</b><br>
A: Windows 下存储在 <code>C:\\Users\\[用户名]\\AppData\\Roaming\\ChemCal\\ChemCal_data.json</code>。<br><br>

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

<b>ChemCal 信息：</b><br>
- 版本：v{CHEMICAL_VERSION}<br>
- 数据目录：{os.path.dirname(data_file)}<br>
- 已加载模块：{loaded}/{total}<br>
- 运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br><br>

<b>数据文件：</b><br>
{file_info}"""
        self._show_scrollable_dialog("系统信息", text)

    def _show_logs(self):
        log_dir = os.path.join(os.path.expanduser("~"), ".ChemCal", "logs")
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"ChemCal_{today}.log")

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
<b>ChemCal - MIT License</b><br>
Copyright 2025 ChemCal Team<br><br>

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

<b>源码：</b> https://github.com/virmuran/ChemCal<br>
<b>联系：</b> virmuran@163.com"""
        self._show_scrollable_dialog("开源许可", text)

    def _show_about(self):
        text = f"""<h2>ChemCal - 化工工程师个人生产力工具</h2>
<h3>v{CHEMICAL_VERSION}</h3><br>
Copyright 2025-2026 ChemCal Team | virmuran@163.com<br><br>

<b>核心功能：</b><br>
- 工程计算（换热、管道、泵、安全阀、循环水、结晶罐等）<br>
- 自动更新（GitHub Releases，帮助→检查更新）<br>
- 参考资料库（设备布置、管道设计、安全规范、计算依据、物性数据、材料规范）<br>
- 计算历史（记录查询、筛选、详情查看）<br>
- 换算器（多类单位换算）<br>
- 计算书导出（DOCX/PDF）<br><br>

<b>数据安全：</b><br>
- 数据仅本地存储，不联网，不收集隐私<br>
- 代码 MIT 开源：https://github.com/virmuran/ChemCal<br><br>

<b>更新日志：</b><br>
最新改动见项目 README 的「更新日志」章节，或 GitHub Releases 页面<br><br>

<b>免责声明：</b> 计算结果仅供参考，实际工程应用请由专业工程师审核确认。"""
        self._show_scrollable_dialog("关于 ChemCal", text)


def resource_path(relative_path):
    """获取资源文件的绝对路径（兼容 PyInstaller 打包和直接运行）"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def main():
    app = SafeApplication(sys.argv)
    app.setApplicationName("ChemCal")
    app.setApplicationVersion(CHEMICAL_VERSION)  # 完整版本号，便于诊断定位
    app.setOrganizationName("ChemCal")

    try:
        window = ChemCal()
        window.show()
        return app.run()
    except Exception as e:
        logger.critical("应用程序启动失败: {}", e)
        traceback.print_exc()
        QMessageBox.critical(None, "启动失败", f"应用程序启动失败:\n{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
