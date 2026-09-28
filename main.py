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
    QHBoxLayout, QProgressBar, QDialogButtonBox, QTextEdit,
    QFormLayout, QLineEdit
)
from PySide6.QtGui import QAction, QActionGroup, QFont, QDesktopServices
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


class ProjectInfoDialog(QDialog):
    """工程信息录入对话框 —— 计算书抬头的唯一录入入口

    各计算器的计算书（DOCX / PDF）抬头通过 DataManager.get_project_info()
    读取 company_name / project_number / project_name / subproject_name
    四个标准键；此前只有读没有写，本对话框补上写入口。
    """

    FIELDS = [
        ("company_name", "公司名称"),
        ("project_number", "工程编号"),
        ("project_name", "工程名称"),
        ("subproject_name", "子项名称"),
    ]

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("工程信息")
        self.setMinimumWidth(400)
        self._dm = data_manager

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._edits = {}
        placeholders = {
            "company_name": "如：XX 生物科技股份有限公司",
            "project_number": "如：2026-071",
            "project_name": "如：10 万吨/年麦芽糖醇项目",
            "subproject_name": "如：脱色工段",
        }
        for key, label in self.FIELDS:
            edit = QLineEdit(self)
            edit.setPlaceholderText(placeholders[key])
            self._edits[key] = edit
            form.addRow(label + "：", edit)
        layout.addLayout(form)

        hint = QLabel(
            "以上信息将作为所有计算书（DOCX / PDF）的抬头，\n"
            "保存后对全部计算器立即生效。"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load()

    def _load(self):
        """从 DataManager 预填当前工程信息"""
        info = self._dm.get_project_info() or {}
        for key, _ in self.FIELDS:
            self._edits[key].setText(str(info.get(key, "") or ""))

    def values(self):
        """当前各字段值（已去首尾空白）"""
        return {key: self._edits[key].text().strip()
                for key, _ in self.FIELDS}

    def accept(self):
        """保存到 DataManager 并关闭"""
        self._dm.update_project_info(self.values())
        super().accept()


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

    #: 主题 key → 菜单显示名（中文界面里不混英文；顺序固定 浅/深/蓝）
    THEME_LABELS = (("light", "浅色主题"), ("dark", "深色主题"),
                    ("blue", "蓝色主题"))

    def _setup_menu(self):
        """菜单栏 —— 只放「设置与元信息」，高频动作都在标签页里

        精简原则（v1.13.1）：菜单项必须「点开有东西、点了有反馈」。
            删「备份数据」     → 备份文件落在隐藏目录里找不到，改用「打开数据目录」自己拷
            删「刷新所有模块」 → 开发期调试功能，界面看不出变化
            删「常见问题」     → 与「用户手册」合并为「使用说明」（原文案中的
                                数据路径、pip 安装说明均与本项目实现不符）
            删「开源许可」     → 并入「关于」
            「系统信息」+「查看日志」 → 合并为「诊断信息」
            主题菜单加勾选标记 → 原先切完看不出当前用的是哪套
        """
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")
        self._add_action(file_menu, "工程信息...", self._edit_project_info)
        self._add_action(file_menu, "打开数据目录", self._open_data_dir)
        file_menu.addSeparator()
        exit_act = self._add_action(file_menu, "退出", self.close)
        exit_act.setShortcut("Ctrl+Q")

        # 主题菜单 —— 互斥勾选，一眼看出当前用的是哪套
        theme_menu = menubar.addMenu("主题")
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        labels = dict(self.THEME_LABELS)
        self._theme_actions = {}
        for key in self.theme_manager.get_theme_names():
            act = QAction(labels.get(key, f"{key.capitalize()}主题"), self)
            act.setCheckable(True)
            act.setChecked(key == self.theme_manager.current_theme)
            act.triggered.connect(
                lambda checked, k=key: self.theme_manager.set_theme(k))
            self._theme_group.addAction(act)
            theme_menu.addAction(act)
            self._theme_actions[key] = act
        # 主题若经其它入口（状态栏等）改变，勾选同步
        self.theme_manager.theme_changed.connect(self._sync_theme_check)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        self._add_action(help_menu, "检查更新",
                         lambda: self._check_version(silent=False))
        self._add_action(help_menu, "使用说明", self._show_usage_guide)
        self._add_action(help_menu, "诊断信息", self._show_diagnostics)
        self._add_action(help_menu, "关于 ChemCal", self._show_about)

    def _sync_theme_check(self, theme_name):
        """同步主题菜单勾选状态（与当前主题保持一致）"""
        act = getattr(self, "_theme_actions", {}).get(theme_name)
        if act is not None and not act.isChecked():
            act.setChecked(True)

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

    def _edit_project_info(self):
        """工程信息录入（计算书抬头的唯一写入口）"""
        dlg = ProjectInfoDialog(DataManager.get_instance(), self)
        if dlg.exec():
            self.statusBar().showMessage(
                "工程信息已保存，计算书抬头已更新", 5000)

    def _open_data_dir(self):
        """在文件管理器里打开本地数据目录（~/.ChemCal，内含 data/ 与 logs/）

        取代原「备份数据」：那个只把 JSON 复制到同目录，用户既找不到备份文件、
        也无从确认备份去了哪。直接打开目录，看得到、拷得走、可整个备份。
        """
        data_dir = os.path.dirname(self.data_manager.data_file)
        # 打开父目录（~/.ChemCal），data 与 logs 都一览无余
        target = os.path.dirname(data_dir) or data_dir
        if not os.path.isdir(target):
            QMessageBox.warning(
                self, "打开失败",
                f"数据目录不存在：\n{target}\n\n首次保存数据后会自动创建。")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(target))
        logger.info("打开数据目录: {}", target)
        self.statusBar().showMessage(f"已打开数据目录：{target}", 6000)

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

    def _show_usage_guide(self):
        """使用说明 —— 由原「用户手册」+「常见问题」两篇合并重写

        原文案与本项目实现多处不符：数据目录写成 AppData\\Roaming（实际在
        用户主目录的 .ChemCal 下）、教安装包用户 `pip install -r requirements.txt`、
        提早已不需要的 reportlab 手动安装、且还在宣传"压降计算支持导出 PDF"
        （实际全部计算器都能出 DOCX/PDF）。两篇各说各话也难维护，故合一。
        """
        text = """<h2>ChemCal 使用说明</h2><br>

<b>一、四个标签页</b><br>
· <b>工程计算</b> —— 52 个计算器，分物性数据 / 工艺设备 / 流体输送 / 热工制冷 / 安全环保 五类<br>
· <b>计算历史</b> —— 每次计算的记录（输入、结果、时间），可按计算器筛选、看使用统计、导出计算书<br>
· <b>换算器</b> —— 21 类单位换算<br>
· <b>资料库</b> —— 化工设计常用规范数据（16 大类 69 小节），支持搜索、数值反查与送入计算器<br><br>

<b>二、算一个东西</b><br>
1. 在「工程计算」左侧列表里选计算器（列表可用右键或管理入口调整顺序、隐藏暂时不用的）<br>
2. 右侧填参数 —— 有默认值的输入框可以直接改成你的工况值<br>
3. 点绿色「计算」，结果显示在下方<br>
4. 需要存档就点「下载 DOCX」或「下载 PDF」，抬头取自「文件 → 工程信息」<br><br>

<b>三、跨计算器取数（计算链）</b><br>
工艺参数往往一环扣一环（例如 喷射液化器用汽量 → 闪蒸降温浓缩 → 闪蒸蒸汽回收 → 闪蒸罐 → 脱色柱）。
下游页面的「<b>取上游值</b>」下拉里能直接选上游算出的结果，一键填进输入框，不用手抄；
结果页会标明这个值取自哪一页。上游参数改了，旧值会被标记为过期。<br><br>

<b>四、资料库怎么用</b><br>
· 搜索框输关键词，结果直接<b>定位到具体数据行</b>，命中的单元格会高亮<br>
· 输<b>纯数值</b>（如 <code>0.6</code> / <code>143.7</code> / <code>0.6MPa</code>）自动切换为<b>全库反查</b>，
  在 ±1% 容差内找这个数出现在哪张表里 —— 手里只有实测数据时特别好用<br>
· 查到数据后点「<b>送入计算器</b>」，自动跳到对应计算器并填进输入框；
  计算器里的 📚 按钮则反向跳到数据出处<br><br>

<b>五、数据存在哪 / 怎么备份</b><br>
· 数据目录：<code>用户主目录 / .ChemCal /</code><br>
　　├ <code>data / ChemCal_data.json</code> —— 工程信息抬头与界面设置<br>
　　├ <code>history / calc_history.db</code> —— 计算历史记录<br>
　　└ <code>logs /</code> —— 运行日志（按天记录，保留 7 天）<br>
· 备份：菜单「<b>文件 → 打开数据目录</b>」直接打开上面这个文件夹，
  把整个 <code>.ChemCal</code> 目录拷走即完成备份（含工程信息、历史记录与日志）<br><br>

<b>六、改计算书抬头</b><br>
菜单「<b>文件 → 工程信息...</b>」填公司名称 / 工程编号 / 工程名称 / 子项名称，
保存后对全部计算器的计算书立即生效，重启软件也会保留。<br><br>

<b>七、检查更新</b><br>
菜单「帮助 → 检查更新」。启动时也会自动静默检查一次，
发现新版本会在状态栏右侧提示，点它可看更新说明并下载。<br><br>

<b>八、出问题怎么办</b><br>
1. 菜单「<b>帮助 → 诊断信息</b>」：显示版本、系统环境、数据文件位置与最近的运行日志，
   反馈问题时把这里的内容一并附上，定位最快<br>
2. 某个计算器打不开或界面空白：多为安装不完整，重新安装一次通常即可解决<br>
3. 数据文件损坏：程序<b>不会删除</b>它，而是改名成 <code>ChemCal_data.corrupt-时间戳.json</code>
   留在同一目录，可从里面手工找回内容<br><br>

<b>九、免责</b><br>
计算结果仅供参考，实际工程应用须由专业工程师审核确认。<br><br>

<b>反馈 / 建议：</b> virmuran@163.com　|　源码：https://github.com/virmuran/ChemCal"""
        self._show_scrollable_dialog("使用说明", text)

    def _show_diagnostics(self):
        """诊断信息 —— 由原「系统信息」与「查看日志」两项合并

        原先拆成两个菜单项，实际是同一件事的两半（运行环境 + 日志），报错时
        用户得点两次、看两处；合并为一屏，便于整体复制反馈。
        顺带修一处深色主题缺陷：原日志块只写了浅色底、没写深色字，
        深色主题下浅底压浅字不可读（浅底必须配深色字）。
        """
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
            mt = (datetime.fromtimestamp(os.path.getmtime(data_file))
                  .strftime("%Y-%m-%d %H:%M:%S"))
            file_info = (f"- 数据文件：{data_file}<br>"
                         f"- 文件大小：{sz} 字节（{sz / 1024:.1f} KB）<br>"
                         f"- 最后修改：{mt}<br>")
        loaded = sum(1 for ok in self._module_status.values() if ok)
        total = len(self._module_status)

        # 以下为原「查看日志」菜单项的内容
        log_dir = os.path.join(os.path.expanduser("~"), ".ChemCal", "logs")
        log_file = os.path.join(
            log_dir, f"ChemCal_{datetime.now().strftime('%Y-%m-%d')}.log")
        if os.path.exists(log_file):
            try:
                with open(log_file, encoding="utf-8") as f:
                    recent = f.readlines()[-50:]
                log_content = ("".join(recent).replace("<", "&lt;")
                               .replace(">", "&gt;").replace("\n", "<br>"))
            except Exception:
                log_content = "读取日志文件失败"
        else:
            log_content = "今日暂无日志记录"

        status_lines = "".join(
            f"- {name}：{'已加载' if ok else '加载失败'}<br>"
            for name, ok in self._module_status.items())

        text = f"""<h2>诊断信息</h2>
<i>反馈问题时，请把本页内容整体复制一并附上。</i><br><br>

<b>版本与运行环境：</b><br>
- ChemCal：v{CHEMICAL_VERSION}<br>
- 操作系统：{platform.system()} {platform.release()}（{platform.machine()}）<br>
- 系统版本：{platform.version()}<br>
- Python：{platform.python_version()}（{platform.python_implementation()}）<br>
- 处理器：{platform.processor() or '未知'}<br>
- 当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br><br>

<b>硬件：</b><br>
{hw}<br>

<b>标签页加载状态：</b> {loaded}/{total}<br>
{status_lines}<br>

<b>数据与日志位置：</b><br>
{file_info}- 数据目录：<code>{os.path.dirname(data_file)}</code><br>
- 日志文件：<code>{log_file}</code><br>
- 日志目录：<code>{log_dir}</code><br><br>

<b>最近 50 条日志：</b><br>
<pre style="font-size:11px; background:#f5f5f5; color:#1f2937; padding:8px; border-radius:4px;">{log_content}</pre>"""
        self._show_scrollable_dialog("诊断信息", text)

    def _show_about(self):
        """关于 —— 并入原「开源许可」菜单项

        许可全文太长不宜塞进对话框，改为：版权与许可名称 + 第三方依赖清单
        + 指向随包分发的 LICENSE 文件（安装目录 / 便携包根目录），
        菜单项少一个、信息反而不缺。
        """
        text = f"""<h2>ChemCal · 化算</h2>
<h3>v{CHEMICAL_VERSION}</h3>
化工工程师的桌面计算工具集 —— 公式对照 GB / HG / NB/T / IAPWS 等标准逐项核对，
每个计算器都带手算锚点回归测试。<br><br>

<b>四个标签页：</b><br>
- <b>工程计算</b>：52 个计算器（物性数据 / 工艺设备 / 流体输送 / 热工制冷 / 安全环保）<br>
- <b>计算历史</b>：记录查询、筛选、统计与计算书复导出<br>
- <b>换算器</b>：21 类单位换算<br>
- <b>资料库</b>：16 大类 69 小节规范数据，可搜索、可数值反查、可送入计算器<br><br>

<b>数据与隐私：</b><br>
- 全部计算在本机完成，数据仅存于本机 <code>.ChemCal</code> 目录，不上传、不收集<br>
- 唯一联网行为是检查更新（GitHub Releases），且下载由你手动触发<br><br>

<b>许可：</b><br>
- ChemCal 本体：<b>MIT License</b>　Copyright 2025-2026 ChemCal Team<br>
　完整协议见安装目录（或便携包根目录）的 <code>LICENSE</code> 文件<br>
- 第三方依赖：PySide6（LGPLv3）、NumPy（BSD-3）、SciPy（BSD-3）、
  ReportLab（BSD-like）、psutil（BSD-3）、Loguru（MIT）<br><br>

<b>更新日志：</b> 见项目 README 的「更新日志」章节或 GitHub Releases 页面<br>
<b>源码 / 反馈：</b> https://github.com/virmuran/ChemCal　|　virmuran@163.com<br>
<b>使用帮助：</b> 菜单「帮助 → 使用说明」；遇到故障用「帮助 → 诊断信息」<br><br>

<b>免责声明：</b> 计算结果仅供参考，实际工程应用须由专业工程师审核确认。"""
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
