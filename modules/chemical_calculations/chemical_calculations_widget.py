from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QStackedWidget, QFrame, QPushButton,
    QLineEdit, QDialog, QMessageBox
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont
import sys
import os
import importlib.util
from modules.history_db import HistoryDB

# 日志记录器（延迟初始化，避免循环导入）
_logger = None
def _get_logger():
    global _logger
    if _logger is None:
        try:
            from loguru import logger as _l
            _logger = _l
        except ImportError:
            _logger = None
    return _logger

class ChemicalCalculationsWidget(QWidget):
    """工程计算模块 - 左侧导航布局"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)

        # 使用传入的数据管理器或单例
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            try:
                from data_manager import DataManager
                self.data_manager = DataManager.get_instance()
                print("工程计算模块使用单例数据管理器")
            except ImportError:
                self.data_manager = None
                print("工程计算模块: 数据管理器不可用")

        # 初始化页面列表
        self.pages = []

        # 预初始化历史记录数据库，避免首次按钮点击时做 I/O
        try:
            HistoryDB()
        except Exception as e:
            print(f"[历史] 历史数据库预初始化失败: {e}")

        # 设置UI
        self.setup_ui()

    def setup_ui(self):
        """设置工程计算UI - 左侧导航布局"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 创建左侧导航列表
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(220)
        self.nav_list.setObjectName("calcNavList")  # 样式由主题 QSS 提供
        self.nav_list.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        # 右键菜单（隐藏计算器 / 打开管理面板）
        self.nav_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.nav_list.customContextMenuRequested.connect(self._show_nav_menu)

        # 导航顶部：搜索框 + 管理按钮
        nav_tools = QHBoxLayout()
        nav_tools.setSpacing(6)
        self.nav_search = QLineEdit()
        self.nav_search.setPlaceholderText("搜索计算器…")
        self.nav_search.setClearButtonEnabled(True)
        self.nav_search.textChanged.connect(self._apply_nav_filter)
        self.manage_btn = QPushButton("⚙")
        self.manage_btn.setFixedWidth(36)
        self.manage_btn.setToolTip("管理计算器（显示/隐藏、排序）")
        self.manage_btn.clicked.connect(self._open_manager)
        nav_tools.addWidget(self.nav_search, 1)
        nav_tools.addWidget(self.manage_btn)
        
        # 创建右侧内容区域
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("calcContentStack")  # 样式由主题 QSS 提供
        
        # 添加导航项和对应的页面
        self.add_calculator_pages()
        
        # 连接选择事件（先按需实例化页面，再切换显示）
        self.nav_list.currentRowChanged.connect(self._on_nav_row_changed)
        
        # 创建左侧区域（包含标题和导航列表）
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # 主标题
        title_label = QLabel("ChemCal - 化算")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px 0px 10px 0px;")

        # 说明文本
        desc_label = QLabel("专业工程计算工具集")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("font-size: 12px; margin: 0px;")
        desc_label.setWordWrap(True)
        
        left_layout.addWidget(title_label)
        left_layout.addWidget(desc_label)
        left_layout.addLayout(nav_tools)
        left_layout.addWidget(self.nav_list)
        
        # 添加到主布局
        main_layout.addWidget(left_widget)
        main_layout.addWidget(self.content_stack, 1)
        
        # 默认选择第一项
        if self.nav_list.count() > 0:
            self.nav_list.setCurrentRow(0)

    def add_calculator_pages(self):
        """添加所有计算器页面"""
        # 定义计算器页面配置
        page_configs = [
            # （显示名称, 计算器类名, 模块文件名, 是否支持data_manager）
            #
            # ══════════════════════════════════════════
            # 一、物性数据
            # ══════════════════════════════════════════
            ("水蒸气性质", "SteamPropertyCalculator", "steam_property_calculator", True),
            ("湿空气计算", "WetAirCalculator", "wet_air_calculator", True),
            ("制冷剂物性", "RefrigerantPropertiesCalculator", "refrigerant_properties_calculator", True),
            ("纯物质物性查询", "PureSubstanceProperties", "pure_substance_properties", True),
            ("溶液密度计算", "SolutionDensityCalculator", "solution_density_calculator", True),
            ("固体溶解度", "SolidSolubilityCalculator", "solid_solubility_calculator", True),
            ("气体标态转压缩态", "气体标态转压缩态", "gas_state_converter", True),
            ("EOS状态方程", "EOSCalculator", "eos_calculator", True),
            ("气体混合物(EOS)", "GasMixturePropertiesCalculator", "gas_mixture_properties_calculator", True),
            ("汽液平衡(活度系数)", "VLEActivityCoefficientCalculator", "vle_activity_coefficient_calculator", True),
            ("混合液体闪点", "MixedLiquidFlashPointCalculator", "mixed_liquid_flash_point_calculator", True),
            ("pH 计算", "PHCalculator", "ph_calculator", True),
            #
            # ══════════════════════════════════════════
            # 二、工艺设备
            # ══════════════════════════════════════════
            ("换热器计算", "换热器计算", "heat_exchanger_calculator", True),
            ("换热器面积", "换热器面积", "heat_exchanger_area_calculator", True),
            ("夹套/盘管换热面积", "JacketCoilCalculator", "jacket_coil_calculator", True),
            ("搅拌功率 & kLa", "AgitatorCalculator", "agitator_calculator", True),
            ("设备尺寸计算", "设备尺寸计算", "vessel_sizing_calculator", True),
            ("罐体重量", "罐体重量", "tank_weight_calculator", True),
            ("容器设计计算", "VesselDesignCalculator", "vessel_design_calculator", True),
            ("常压储罐壁厚", "AtmosphericTankThicknessCalculator", "atmospheric_tank_thickness_calculator", True),
            ("篮式过滤器", "篮式过滤器", "basket_filter_design_calculator", True),
            ("板框压滤机面积", "FilterPressAreaCalculator", "filter_press_area_calculator", True),
            ("浓缩蒸发器计算", "EvaporatorCalculator", "evaporator_calculator", True),
            ("喷射液化器用汽量", "InjectionLiquefierCalculator", "injection_liquefier_calculator", True),
            ("闪蒸降温浓缩", "FlashEvaporationCalculator", "flash_evaporation_calculator", True),
            ("闪蒸蒸汽回收", "FlashSteamRecoveryCalculator", "flash_steam_recovery_calculator", True),
            ("闪蒸罐计算", "FlashTankCalculator", "flash_tank_calculator", True),
            ("脱色柱计算", "DecolorizationCalculator", "decolorization_column_calculator", True),
            ("风机功率计算", "FanPowerCalculator", "fan_power_calculator", True),
            #
            # ══════════════════════════════════════════
            # 三、流体输送
            # ══════════════════════════════════════════
            ("管径计算", "管径计算", "pipe_diameter_calculator", True),
            ("管道壁厚", "管道壁厚", "pipe_thickness_calculator", True),
            ("管道跨距", "管道跨距", "pipe_span_calculator", True),
            ("管道间距", "管道间距", "pipe_spacing_calculator", True),
            ("管道补偿", "管道补偿", "pipe_compensation_calculator", True),
            ("压力管道定义", "压力管道定义", "pressure_pipe_definition", True),
            ("压降计算", "压降计算", "pressure_drop_calculator", True),
            ("可压缩流体压降", "CompressibleFlowPressureDrop", "compressible_flow_pressure_drop", True),
            ("离心泵功率计算", "CentrifugalPumpCalculator", "pump_power_calculator", True),
            ("离心泵NPSHa计算", "NPSHaCalculator", "npsha_calculator", True),
            ("蒸汽管径流量", "蒸汽管径流量", "steam_pipe_calculator", True),
            ("长输蒸汽管道温降计算", "LongDistanceSteamPipeCalculator", "long_distance_steam_pipe_calculator", True),
            ("蒸汽管道压降计算", "SteamPipePressureDropCalculator", "steam_pipe_pressure_drop_calculator", True),
            ("循环水用水量计算", "CoolingWaterCalculator", "cooling_water_calculator", True),
            #
            # ══════════════════════════════════════════
            # 四、热工制冷
            # ══════════════════════════════════════════
            ("蒸汽空消计算", "SteamSterilizationCalculator", "steam_sterilization_calculator", True),
            ("制冷循环计算", "RefrigerationCycleCalculator", "refrigeration_cycle_calculator", True),
            ("保温厚度计算", "InsulationThicknessCalculator", "insulation_thickness_calculator", True),
            #
            # ══════════════════════════════════════════
            # 五、安全环保
            # ══════════════════════════════════════════
            ("安全阀计算", "SafetyValveCalculator", "safety_valve_calculator", True),
            ("消火栓计算", "消火栓计算", "fire_hydrant_calculator", True),
            ("消防水池容积", "FireWaterTankCalculator", "fire_water_tank_calculator", True),
            ("腐蚀查询", "CorrosionDataQuery", "corrosion_data_query", True),
            ("危险化学品", "HazardousChemicalsQuery", "hazardous_chemicals_query", True),
            ("废水COD估算", "CODEstimator", "cod_estimator", True),
        ]
        
        # 记录完整注册表（含被隐藏的），供管理面板使用
        self._calc_registry = list(page_configs)

        # 读取用户配置：隐藏清单 + 排序（按模块名标识）
        prefs = self._load_calc_prefs()
        registry_modules = [c[2] for c in page_configs]
        hidden = {m for m in prefs["hidden"] if m in registry_modules}
        order = [m for m in prefs["order"] if m in registry_modules]

        # 防呆：全部隐藏时视为未隐藏，至少保留一个
        if len(page_configs) - len(hidden) < 1:
            hidden = set()

        # 排序：order 里排在前面的模块提前，未提及的保持默认顺序（稳定排序）
        def sort_key(cfg):
            try:
                return order.index(cfg[2])
            except ValueError:
                return len(order)

        configs = sorted(page_configs, key=sort_key)

        # 登记导航项 + 轻量占位页（真正的计算器等首次打开时才建），隐藏的直接跳过
        for title, calculator_name, module_name, supports_data_manager in configs:
            if module_name in hidden:
                continue
            self.add_lazy_page(title, calculator_name, module_name,
                               supports_data_manager, title)

        # 如果没有成功添加任何页面，添加一个提示页面
        if len(self.pages) == 0:
            self.add_fallback_page()

    def create_calculator_widget(self, calculator_name, module_name, supports_data_manager, display_name=None):
        """动态创建计算器部件"""
        try:
            # 获取当前文件所在目录（兼容 PyInstaller 打包）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            calculator_path = os.path.join(current_dir, "calculators", f"{module_name}.py")

            # PyInstaller 打包后 __file__ 可能不指向 _MEIPASS，回退查找
            if not os.path.exists(calculator_path):
                _meipass = getattr(sys, '_MEIPASS', None)
                if _meipass:
                    calculator_path = os.path.join(
                        _meipass, "modules", "chemical_calculations",
                        "calculators", f"{module_name}.py"
                    )

            # 检查文件是否存在
            if not os.path.exists(calculator_path):
                raise FileNotFoundError(f"计算器文件不存在: {calculator_path}")

            # 使用 importlib 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, calculator_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 获取计算器类
            calculator_class = getattr(module, calculator_name)

            # 根据是否支持data_manager选择初始化方式
            if supports_data_manager and self.data_manager is not None:
                widget = calculator_class(data_manager=self.data_manager)
            else:
                widget = calculator_class()

            # 注入计算器元数据（用于历史记录）
            widget._calc_meta = {
                "id": module_name,
                "name": display_name or calculator_name,
                "category": self._get_category_from_module(module_name),
            }

            # 连接所有"计算"按钮的 clicked 信号以保存历史
            self._connect_calculate_buttons(widget)

            return widget

        except Exception as e:
            import traceback as _tb
            err_msg = f"创建 {calculator_name} 失败: {e}"
            print(err_msg)
            _tb.print_exc()
            _log = _get_logger()
            if _log:
                _log.error("计算器加载失败: {} | 路径: {} | 错误: {} | 详情:\n{}", calculator_name, calculator_path if 'calculator_path' in dir() else "未知", e, _tb.format_exc())
            # 返回占位符部件
            return self.create_placeholder_widget(calculator_name)

    def create_placeholder_widget(self, calculator_name):
        """创建占位符部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title_label = QLabel(f"{calculator_name}")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #3498db; padding: 20px;")
        layout.addWidget(title_label)
        
        desc_label = QLabel("该计算器正在开发中...\n敬请期待！")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: inherit; font-size: 14px; padding: 10px;")
        layout.addWidget(desc_label)
        
        return widget

    def add_fallback_page(self):
        """添加回退页面（当没有计算器可用时）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title_label = QLabel("工程计算模块")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: inherit; padding: 30px;")
        layout.addWidget(title_label)
        
        desc_label = QLabel(
            "工程计算模块正在初始化...\n\n"
            "如果长时间显示此页面，请检查：\n"
            "• calculators 目录是否存在\n"
            "• 计算器模块文件是否完整\n"
            "• 是否有Python语法错误\n"
            "• 模块导入路径是否正确"
        )
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: inherit; font-size: 14px; padding: 20px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        self.add_page("欢迎", widget)

    def create_error_widget(self, title, error_msg):
        """创建错误显示组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        error_label = QLabel(f"{title}\n加载失败\n错误: {error_msg}")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("color: red; font-size: 14px; padding: 20px;")
        layout.addWidget(error_label)
        
        return widget

    def add_page(self, title, widget):
        """添加页面到导航和堆栈"""
        # 添加到导航列表
        self.nav_list.addItem(title)

        # 添加到堆栈窗口
        self.content_stack.addWidget(widget)

        # 保存页面引用
        self.pages.append(widget)

    # ══════════════════════════════════════════
    # 惰性加载（页面按需实例化）
    #
    # 为什么：47 个计算器全量实例化 ≈ 4200 个控件，Qt 每次换 QSS 都要给每个控件
    # 重算样式 —— 实测「切主题 5.5s、启动 8s」。改成"先登记导航 + 轻量占位页，
    # 首次打开才建真页面"后，常驻控件数降一个数量级，切主题/启动随之变快。
    # 占位页同样带 _calc_meta，因此右键隐藏、管理面板、显隐排序逻辑无需改动。
    # ══════════════════════════════════════════

    def add_lazy_page(self, title, calculator_name, module_name,
                      supports_data_manager, display_name=None):
        """登记导航项 + 占位页（不导入模块、不建控件）"""
        placeholder = QWidget()
        lay = QVBoxLayout(placeholder)
        lay.setContentsMargins(0, 0, 0, 0)
        hint = QLabel(f"{title}\n\n首次打开时加载…")
        hint.setObjectName("mutedLabel")     # 颜色交给主题，勿写死
        hint.setAlignment(Qt.AlignCenter)
        lay.addWidget(hint)

        placeholder._calc_meta = {
            "id": module_name,
            "name": display_name or calculator_name,
            "category": self._get_category_from_module(module_name),
        }
        placeholder._lazy_spec = (calculator_name, module_name,
                                  supports_data_manager, display_name or title)

        self.add_page(title, placeholder)
        return placeholder

    def _on_nav_row_changed(self, row):
        """导航切换：先把该行页面实例化出来，再切显示"""
        if row < 0:
            return
        try:
            self._ensure_page_built(row)
        except Exception as e:
            print(f"[惰性加载] 行 {row} 实例化失败: {e}")
            _log = _get_logger()
            if _log:
                _log.error("计算器实例化失败: row={} | {}", row, e)
        self.content_stack.setCurrentIndex(row)

    def _ensure_page_built(self, row):
        """若该行还是占位页则换成真页面，返回当前页控件"""
        if not (0 <= row < len(self.pages)):
            return None
        page = self.pages[row]
        spec = getattr(page, "_lazy_spec", None)
        if spec is None:
            return page                        # 已经建好了

        calculator_name, module_name, supports_dm, display_name = spec
        widget = self.create_calculator_widget(calculator_name, module_name,
                                              supports_dm, display_name)
        # 占位页上的元数据原样继承（create_calculator_widget 也会写一份，这里兜底）
        meta = getattr(page, "_calc_meta", None)
        if meta is not None:
            widget._calc_meta = meta

        self.content_stack.removeWidget(page)
        self.content_stack.insertWidget(row, widget)
        self.pages[row] = widget
        page.deleteLater()
        return widget

    def open_calculator(self, module_name):
        """按模块名打开计算器（含实例化），成功返回页面控件"""
        for row, page in enumerate(self.pages):
            meta = getattr(page, "_calc_meta", None)
            if meta and meta.get("id") == module_name:
                self.nav_list.setCurrentRow(row)      # 触发按需实例化 + 显示
                return self.pages[row]
        return None

    # ══════════════════════════════════════════
    # 计算器显隐与排序（配置存 settings.calculator_hidden / calculator_order）
    # ══════════════════════════════════════════

    def _load_calc_prefs(self):
        """读取计算器显隐/排序配置"""
        prefs = {"hidden": [], "order": []}
        try:
            if self.data_manager is not None:
                s = self.data_manager.get_settings()
                if isinstance(s.get("calculator_hidden"), list):
                    prefs["hidden"] = [str(m) for m in s["calculator_hidden"]]
                if isinstance(s.get("calculator_order"), list):
                    prefs["order"] = [str(m) for m in s["calculator_order"]]
        except Exception as e:
            print(f"[设置] 读取计算器配置失败: {e}")
        return prefs

    def _save_calc_prefs(self, hidden, order):
        """保存计算器显隐/排序配置"""
        try:
            if self.data_manager is None:
                return
            s = self.data_manager.get_settings()
            s["calculator_hidden"] = list(hidden)
            s["calculator_order"] = list(order)
            self.data_manager.update_settings(s)
        except Exception as e:
            print(f"[设置] 保存计算器配置失败: {e}")

    def _rebuild_pages(self):
        """按最新配置重建导航和页面（隐藏的计算器不实例化）"""
        self.nav_list.blockSignals(True)
        self.nav_list.clear()
        self.nav_list.blockSignals(False)
        while self.content_stack.count():
            w = self.content_stack.widget(0)
            self.content_stack.removeWidget(w)
            w.deleteLater()
        self.pages.clear()
        self.add_calculator_pages()
        self._apply_nav_filter()
        if self.nav_list.count() > 0:
            self.nav_list.setCurrentRow(0)

    def _apply_nav_filter(self):
        """按搜索关键词过滤导航项（仅隐藏行，行号不变）"""
        kw = self.nav_search.text().strip().lower()
        for i in range(self.nav_list.count()):
            it = self.nav_list.item(i)
            it.setHidden(bool(kw) and kw not in it.text().lower())

    def _show_nav_menu(self, pos):
        """导航右键菜单：隐藏此计算器 / 管理计算器"""
        from PySide6.QtWidgets import QMenu
        item = self.nav_list.itemAt(pos)
        row = self.nav_list.row(item) if item else -1
        menu = QMenu(self)
        can_hide = False
        if item is not None and 0 <= row < len(self.pages):
            meta = getattr(self.pages[row], "_calc_meta", None)
            if meta is not None:
                visible_count = sum(1 for p in self.pages if getattr(p, "_calc_meta", None))
                can_hide = visible_count > 1
        act_hide = menu.addAction("隐藏此计算器")
        act_hide.setEnabled(can_hide)
        menu.addSeparator()
        act_manage = menu.addAction("管理计算器…")
        chosen = menu.exec(self.nav_list.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == act_hide and item is not None:
            self._hide_calculator_at(row)
        elif chosen == act_manage:
            self._open_manager()

    def _hide_calculator_at(self, row):
        """隐藏指定行的计算器并持久化"""
        if not (0 <= row < len(self.pages)):
            return
        meta = getattr(self.pages[row], "_calc_meta", None)
        if meta is None:
            return
        prefs = self._load_calc_prefs()
        hidden = set(prefs["hidden"])
        hidden.add(meta["id"])
        order = list(prefs["order"])
        if meta["id"] not in order:
            order.append(meta["id"])
        self._save_calc_prefs(sorted(hidden), order)
        self._rebuild_pages()

    def _open_manager(self):
        """管理面板：勾选显隐 + 上移/下移排序 + 恢复默认"""
        if not getattr(self, "_calc_registry", None):
            return
        prefs = self._load_calc_prefs()
        registry = self._calc_registry
        modules = [c[2] for c in registry]
        title_of = {c[2]: c[0] for c in registry}
        hidden = {m for m in prefs["hidden"] if m in modules}
        order = [m for m in prefs["order"] if m in modules]
        effective = order + [m for m in modules if m not in order]

        dlg = QDialog(self)
        dlg.setWindowTitle("管理计算器")
        dlg.resize(380, 540)
        v = QVBoxLayout(dlg)
        tip = QLabel("勾选 = 在导航中显示；选中行后用按钮调整顺序。")
        tip.setWordWrap(True)
        v.addWidget(tip)

        lst = QListWidget()
        for m in effective:
            it = QListWidgetItem(title_of.get(m, m))
            it.setData(Qt.ItemDataRole.UserRole, m)
            it.setToolTip(f"分类：{self._get_category_from_module(m)}")
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked if m in hidden else Qt.CheckState.Checked)
            lst.addItem(it)
        v.addWidget(lst, 1)

        row_btns = QHBoxLayout()
        def move_item(delta):
            r = lst.currentRow()
            if r < 0:
                return
            if (delta < 0 and r == 0) or (delta > 0 and r == lst.count() - 1):
                return
            it = lst.takeItem(r)
            lst.insertItem(r + delta, it)
            lst.setCurrentRow(r + delta)
        up_btn = QPushButton("上移")
        up_btn.clicked.connect(lambda: move_item(-1))
        down_btn = QPushButton("下移")
        down_btn.clicked.connect(lambda: move_item(1))
        restore_btn = QPushButton("恢复默认")
        def restore_default():
            lst.clear()
            for c in registry:
                it = QListWidgetItem(c[0])
                it.setData(Qt.ItemDataRole.UserRole, c[2])
                it.setToolTip(f"分类：{self._get_category_from_module(c[2])}")
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Checked)
                lst.addItem(it)
        restore_btn.clicked.connect(restore_default)
        row_btns.addWidget(up_btn)
        row_btns.addWidget(down_btn)
        row_btns.addStretch()
        row_btns.addWidget(restore_btn)
        v.addLayout(row_btns)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dlg.reject)
        ok_btn = QPushButton("确定")
        def apply():
            checked = sum(1 for i in range(lst.count())
                          if lst.item(i).checkState() == Qt.CheckState.Checked)
            if checked == 0:
                QMessageBox.information(dlg, "提示", "至少保留一个计算器可见。")
                return
            order_new = [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())]
            hidden_new = [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())
                          if lst.item(i).checkState() == Qt.CheckState.Unchecked]
            self._save_calc_prefs(hidden_new, order_new)
            self._rebuild_pages()
            dlg.accept()
        ok_btn.clicked.connect(apply)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        v.addLayout(btn_row)

        dlg.exec()

    def _is_calculate_button(self, btn):
        text = ''.join(btn.text().split())  # 移除所有空白字符（"计 算"/"查 询"均可匹配）
        return text in ("计算", "查询")

    def _connect_calculate_buttons(self, widget):
        """查找并连接所有计算按钮的 clicked 信号"""
        try:
            # 查找所有按钮
            for btn in widget.findChildren(QPushButton):
                if self._is_calculate_button(btn):
                    # 使用 lambda 捕获 widget 引用
                    btn.clicked.connect(lambda checked, w=widget: self._save_history_for(w))
                    print(f"[历史] 已连接按钮: {btn.text()} -> {widget._calc_meta['name']}")
        except Exception as e:
            print(f"[历史] 连接按钮失败: {e}")

    def _save_history_for(self, widget):
        """为指定计算器部件保存历史记录（捕获数据后延迟执行 I/O）"""
        meta = getattr(widget, "_calc_meta", None)
        if meta is None:
            print(f"[历史] 无 _calc_meta，跳过: {widget}")
            return
        get_data = getattr(widget, "_get_history_data", None)
        if get_data is None:
            print(f"[历史] 计算器 '{meta['name']}' 未实现 _get_history_data，无法保存")
            return
        try:
            data = get_data()
            if not data or not data.get("inputs"):
                print(f"[历史] _get_history_data 返回空，跳过")
                return
            # 延迟保存，避免在 clicked 信号处理链中做 I/O 和触发 Qt 控件操作
            QTimer.singleShot(0, lambda m=meta, d=data: self._do_save(m, d))
        except Exception as e:
            print(f"[历史] 准备保存失败: {e}")

    def _do_save(self, meta, data):
        """在事件循环空闲时执行实际保存"""
        try:
            HistoryDB().save(
                calculator_id=meta["id"],
                calculator_name=meta["name"],
                calculator_category=meta.get("category", ""),
                inputs=data.get("inputs", {}),
                outputs=data.get("outputs", {}),
                notes=data.get("notes", ""),
            )
        except Exception as e:
            print(f"[历史] 保存失败: {e}")
            import traceback; traceback.print_exc()

    # 计算器分类映射 — 五大分类体系
    _CALC_CATEGORIES = {
        # 一、物性数据
        "steam_property_calculator": "物性数据",
        "wet_air_calculator": "物性数据",
        "refrigerant_properties_calculator": "物性数据",
        "pure_substance_properties": "物性数据",
        "solution_density_calculator": "物性数据",
        "solid_solubility_calculator": "物性数据",
        "gas_state_converter": "物性数据",
        "eos_calculator": "物性数据",
        "gas_mixture_properties_calculator": "物性数据",
        "vle_activity_coefficient_calculator": "物性数据",
        "mixed_liquid_flash_point_calculator": "物性数据",
        "ph_calculator": "物性数据",
        # 二、工艺设备
        "heat_exchanger_calculator": "工艺设备",
        "heat_exchanger_area_calculator": "工艺设备",
        "jacket_coil_calculator": "工艺设备",
        "agitator_calculator": "工艺设备",
        "vessel_sizing_calculator": "工艺设备",
        "tank_weight_calculator": "工艺设备",
        "vessel_design_calculator": "工艺设备",
        "atmospheric_tank_thickness_calculator": "工艺设备",
        "basket_filter_design_calculator": "工艺设备",
        "filter_press_area_calculator": "工艺设备",
        "evaporator_calculator": "工艺设备",
        "injection_liquefier_calculator": "工艺设备",
        "flash_evaporation_calculator": "工艺设备",
        "flash_steam_recovery_calculator": "工艺设备",
        "flash_tank_calculator": "工艺设备",
        "decolorization_column_calculator": "工艺设备",
        "fan_power_calculator": "工艺设备",
        # 三、流体输送
        "pipe_diameter_calculator": "流体输送",
        "pipe_thickness_calculator": "流体输送",
        "pipe_span_calculator": "流体输送",
        "pipe_spacing_calculator": "流体输送",
        "pipe_compensation_calculator": "流体输送",
        "pressure_pipe_definition": "流体输送",
        "pressure_drop_calculator": "流体输送",
        "compressible_flow_pressure_drop": "流体输送",
        "pump_power_calculator": "流体输送",
        "npsha_calculator": "流体输送",
        "steam_pipe_calculator": "流体输送",
        "long_distance_steam_pipe_calculator": "流体输送",
        "steam_pipe_pressure_drop_calculator": "流体输送",
        "cooling_water_calculator": "流体输送",
        # 四、热工制冷
        "steam_sterilization_calculator": "热工制冷",
        "refrigeration_cycle_calculator": "热工制冷",
        "insulation_thickness_calculator": "热工制冷",
        # 五、安全环保
        "safety_valve_calculator": "安全环保",
        "fire_hydrant_calculator": "安全环保",
        "fire_water_tank_calculator": "安全环保",
        "corrosion_data_query": "安全环保",
        "hazardous_chemicals_query": "安全环保",
        "cod_estimator": "安全环保",
    }

    def _get_category_from_module(self, module_name):
        return self._CALC_CATEGORIES.get(module_name, "其他")


if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = ChemicalCalculationsWidget()
    widget.showMaximized()
    
    sys.exit(app.exec())