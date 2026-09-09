from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QStackedWidget, QFrame, QPushButton
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
        
        # 创建右侧内容区域
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("calcContentStack")  # 样式由主题 QSS 提供
        
        # 添加导航项和对应的页面
        self.add_calculator_pages()
        
        # 连接选择事件
        self.nav_list.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        
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
            ("篮式过滤器", "篮式过滤器", "basket_filter_design_calculator", True),
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
        
        # 添加所有页面
        success_count = 0
        for title, calculator_name, module_name, supports_data_manager in page_configs:
            try:
                widget = self.create_calculator_widget(calculator_name, module_name, supports_data_manager, title)
                self.add_page(title, widget)
                success_count += 1
            except Exception as e:
                err_msg = f"FAIL: {title} 页面创建失败: {e}"
                print(err_msg)
                _log = _get_logger()
                if _log:
                    _log.error("计算器页面创建失败: {} | {}", title, e)
                # 创建错误页面
                error_widget = self.create_error_widget(title, str(e))
                self.add_page(f"{title} (错误)", error_widget)
        
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
        "basket_filter_design_calculator": "工艺设备",
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
        # 遗留（存量兼容）
        "flange_size_calculator": "其他",
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