from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QStackedWidget, QFrame, QPushButton
)
from PySide6.QtCore import Qt, QSize, QEvent, QTimer
from PySide6.QtGui import QFont
import sys
import os
import importlib.util

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
        self.nav_list.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                outline: none;
                font-size: 13px;
                padding: 5px 0px;
            }
            QListWidget::item {
                height: 40px;
                border: none;
                padding-left: 15px;
                color: #495057;
                border-bottom: 1px solid #e9ecef;
                margin: 2px 8px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-left: 4px solid #2980b9;
                border-bottom: 1px solid #2980b9;
            }
            QListWidget::item:hover:!selected {
                background-color: #e9ecef;
                color: #212529;
            }
        """)
        
        # 创建右侧内容区域
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin-left: 10px;
            }
        """)
        
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
        title_label = QLabel("工程计算")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 0px; padding: 10px;")
        
        # 说明文本
        desc_label = QLabel("专业工程计算工具集\n逐步完善中...")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #7f8c8d; font-size: 12px; margin: 0px;")
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
            # ===== 一、物性查询 =====
            ("水蒸气性质", "SteamPropertyCalculator", "steam_property_calculator", True),
            ("湿空气计算", "WetAirCalculator", "wet_air_calculator", True),
            ("制冷剂物性", "RefrigerantPropertiesCalculator", "refrigerant_properties_calculator", True),
            ("纯物质物性查询", "PureSubstanceProperties", "pure_substance_properties", True),
            ("溶液密度计算", "SolutionDensityCalculator", "solution_density_calculator", True),
            ("固体溶解度", "SolidSolubilityCalculator", "solid_solubility_calculator", True),
            ("腐蚀查询", "CorrosionDataQuery", "corrosion_data_query", True),
            ("危险化学品", "HazardousChemicalsQuery", "hazardous_chemicals_query", True),
            ("气体标态转压缩态", "气体标态转压缩态", "gas_state_converter", True),
            ("EOS状态方程", "EOSCalculator", "eos_calculator", True),
            ("气体混合物(EOS)", "GasMixturePropertiesCalculator", "gas_mixture_properties_calculator", True),
            ("汽液平衡(活度系数)", "VLEActivityCoefficientCalculator", "vle_activity_coefficient_calculator", True),
            ("混合液体闪点", "MixedLiquidFlashPointCalculator", "mixed_liquid_flash_point_calculator", True),
            # ===== 二、管道系统 =====
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
            # ===== 三、换热设备 =====
            ("换热器计算", "换热器计算", "heat_exchanger_calculator", True),
            ("换热器面积", "换热器面积", "heat_exchanger_area_calculator", True),
            ("风机功率计算", "FanPowerCalculator", "fan_power_calculator", True),
            ("保温厚度计算", "InsulationThicknessCalculator", "insulation_thickness_calculator", True),
            # ===== 四、容器与设备 =====
            ("设备尺寸计算", "设备尺寸计算", "vessel_sizing_calculator", True),
            ("罐体重量", "罐体重量", "tank_weight_calculator", True),
            ("篮式过滤器", "篮式过滤器", "basket_filter_design_calculator", True),
            # ===== 五、安全 =====
            ("安全阀计算", "SafetyValveCalculator", "safety_valve_calculator", True),
            ("泄压面积计算", "ReliefAreaCalculator", "relief_area_calculator", True),
            ("消火栓计算", "消火栓计算", "fire_hydrant_calculator", True),
            # ===== 六、制冷 =====
            ("制冷循环计算", "RefrigerationCycleCalculator", "refrigeration_cycle_calculator", True),
        ]
        
        # 添加所有页面
        success_count = 0
        for title, calculator_name, module_name, supports_data_manager in page_configs:
            try:
                widget = self.create_calculator_widget(calculator_name, module_name, supports_data_manager, title)
                self.add_page(title, widget)
                success_count += 1
            except Exception as e:
                print(f"FAIL: {title} 页面创建失败: {e}")
                # 创建错误页面
                error_widget = self.create_error_widget(title, str(e))
                self.add_page(f"{title} (错误)", error_widget)
        
        # 如果没有成功添加任何页面，添加一个提示页面
        if len(self.pages) == 0:
            self.add_fallback_page()

    def create_calculator_widget(self, calculator_name, module_name, supports_data_manager, display_name=None):
        """动态创建计算器部件"""
        try:
            # 获取当前文件所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 构建计算器模块的完整路径
            calculator_path = os.path.join(current_dir, "calculators", f"{module_name}.py")

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

            # 安装事件过滤器作为备用方案
            widget.installEventFilter(self)

            return widget

        except Exception as e:
            print(f"创建 {calculator_name} 失败: {e}")
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
        desc_label.setStyleSheet("color: #7f8c8d; font-size: 14px; padding: 10px;")
        layout.addWidget(desc_label)
        
        return widget

    def add_fallback_page(self):
        """添加回退页面（当没有计算器可用时）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title_label = QLabel("工程计算模块")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; padding: 30px;")
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
        desc_label.setStyleSheet("color: #7f8c8d; font-size: 14px; padding: 20px;")
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

    def eventFilter(self, obj, event):
        """拦截计算器子控件事件，保存历史记录"""
        if event.type() == QEvent.Type.MouseButtonPress:
            child = obj.childAt(event.position().toPoint())
            if isinstance(child, QPushButton) and self._is_calculate_button(child):
                print(f"[历史] 捕获到计算按钮点击: {child.text()}")
                QTimer.singleShot(100, lambda w=obj: self._save_history_for(w))
        return super().eventFilter(obj, event)

    def _is_calculate_button(self, btn):
        text = btn.text().strip()
        # 匹配计算和查询类按钮
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
        """为指定计算器部件保存历史记录"""
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
            from modules.history_db import HistoryDB
            HistoryDB().save(
                calculator_id=meta["id"],
                calculator_name=meta["name"],
                calculator_category=meta.get("category", ""),
                inputs=data.get("inputs", {}),
                outputs=data.get("outputs", {}),
                notes=data.get("notes", ""),
            )
            print(f"[历史] 已保存: {meta['name']} | inputs={data.get('inputs')}")
        except Exception as e:
            print(f"[历史] 保存失败: {e}")
            import traceback; traceback.print_exc()

    # 计算器分类映射
    _CALC_CATEGORIES = {
        "basket_filter_design_calculator": "容器/结构",
        "pressure_drop_calculator": "管道",
        "pipe_diameter_calculator": "管道",
        "pipe_span_calculator": "管道",
        "pipe_spacing_calculator": "管道",
        "pipe_compensation_calculator": "管道",
        "pipe_thickness_calculator": "管道",
        "steam_pipe_calculator": "管道",
        "gas_state_converter": "热工/制冷",
        "pressure_pipe_definition": "管道",
        "fire_hydrant_calculator": "安全/消防",
        "heat_exchanger_calculator": "换热",
        "heat_exchanger_area_calculator": "换热",
        "tank_weight_calculator": "容器/结构",
        "vessel_sizing_calculator": "容器/结构",
        "insulation_thickness_calculator": "换热",
        "flange_size_calculator": "其他",
        "safety_valve_calculator": "安全/消防",
        "long_distance_steam_pipe_calculator": "管道",
        "relief_area_calculator": "安全/消防",
        "fan_power_calculator": "流体设备",
        "steam_property_calculator": "热工/制冷",
        "pure_substance_properties": "热力学",
        "wet_air_calculator": "热工/制冷",
        "mixed_liquid_flash_point_calculator": "热力学",
        "eos_calculator": "热力学",
        "vle_activity_coefficient_calculator": "热力学",
        "gas_mixture_properties_calculator": "热力学",
        "corrosion_data_query": "安全/消防",
        "solid_solubility_calculator": "热力学",
        "refrigerant_properties_calculator": "热工/制冷",
        "refrigeration_cycle_calculator": "热工/制冷",
        "hazardous_chemicals_query": "安全/消防",
        "pump_power_calculator": "流体设备",
        "npsha_calculator": "流体设备",
        "compressible_flow_pressure_drop": "管道",
        "solution_density_calculator": "热力学",
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