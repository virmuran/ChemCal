# [file name]: calculators/pressure_pipe_definition.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                              QLabel, QLineEdit, QComboBox, QPushButton, 
                              QTextEdit, QTableWidget, QTableWidgetItem,
                              QHeaderView, QMessageBox, QTabWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math

COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 6px 10px;
        background: white;
        color: black;
    }
    QComboBox QAbstractItemView {
        background-color: white;
        color: black;
        border: 1px solid #bdc3c7;
        selection-background-color: #3498db;
        selection-color: black;
    }
    QComboBox QAbstractItemView::item {
        padding: 3px 8px;
    }
"""
class 压力管道定义(QWidget):
    """压力管道定义计算器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("压力管道定义计算")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 添加计算标签页
        self.calculation_tab = self.create_calculation_tab()
        self.tab_widget.addTab(self.calculation_tab, "管道定义计算")
        
        # 添加标准说明标签页
        self.standard_tab = self.create_standard_tab()
        self.tab_widget.addTab(self.standard_tab, "标准说明")
        
        main_layout.addWidget(self.tab_widget)
    
    def create_calculation_tab(self):
        """创建计算标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 输入参数组
        input_group = QGroupBox(" 输入参数")
        input_layout = QVBoxLayout(input_group)
        
        # 压力输入
        pressure_layout = QHBoxLayout()
        pressure_layout.addWidget(QLabel("设计压力 (MPa):"))
        self.pressure_input = QLineEdit()
        self.pressure_input.setPlaceholderText("请输入设计压力")
        self.pressure_input.setValidator(QDoubleValidator(0.0, 100.0, 2))
        pressure_layout.addWidget(self.pressure_input)
        pressure_layout.addWidget(QLabel("工作压力 (MPa):"))
        self.working_pressure_input = QLineEdit()
        self.working_pressure_input.setPlaceholderText("请输入工作压力")
        self.working_pressure_input.setValidator(QDoubleValidator(0.0, 100.0, 2))
        pressure_layout.addWidget(self.working_pressure_input)
        input_layout.addLayout(pressure_layout)
        
        # 温度输入
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("设计温度 (°C):"))
        self.temp_input = QLineEdit()
        self.temp_input.setPlaceholderText("请输入设计温度")
        self.temp_input.setValidator(QDoubleValidator(-200.0, 1000.0, 1))
        temp_layout.addWidget(self.temp_input)
        temp_layout.addWidget(QLabel("工作温度 (°C):"))
        self.working_temp_input = QLineEdit()
        self.working_temp_input.setPlaceholderText("请输入工作温度")
        self.working_temp_input.setValidator(QDoubleValidator(-200.0, 1000.0, 1))
        temp_layout.addWidget(self.working_temp_input)
        input_layout.addLayout(temp_layout)
        
        # 介质和直径
        media_layout = QHBoxLayout()
        media_layout.addWidget(QLabel("介质类型:"))
        self.media_combo = QComboBox()
        self.media_combo.setStyleSheet(COMBOBOX_STYLE)
        self.media_combo.addItems(["气体", "液化气体", "蒸汽", "可燃液体", "有毒介质", "一般液体"])
        media_layout.addWidget(self.media_combo)
        media_layout.addWidget(QLabel("公称直径 (mm):"))
        self.diameter_input = QLineEdit()
        self.diameter_input.setPlaceholderText("请输入公称直径")
        self.diameter_input.setValidator(QDoubleValidator(0.0, 5000.0, 1))
        media_layout.addWidget(self.diameter_input)
        input_layout.addLayout(media_layout)
        
        layout.addWidget(input_group)
        
        # 按钮组
        button_layout = QHBoxLayout()
        self.calculate_btn = QPushButton("计算")
        self.calculate_btn.clicked.connect(self.calculate_pipe_definition)
        self.calculate_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; }")
        button_layout.addWidget(self.calculate_btn)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_inputs)
        self.clear_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; }")
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # 结果显示组
        result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(200)
        result_layout.addWidget(self.result_text)
        
        layout.addWidget(result_group)
        
        # 压力管道分类表
        classification_group = QGroupBox(" 压力管道分类参考")
        classification_layout = QVBoxLayout(classification_group)
        
        self.classification_table = QTableWidget()
        self.classification_table.setColumnCount(4)
        self.classification_table.setHorizontalHeaderLabels(["类别", "代号", "适用范围", "主要特征"])
        self.setup_classification_table()
        classification_layout.addWidget(self.classification_table)
        
        layout.addWidget(classification_group)
        
        return tab
    
    def setup_classification_table(self):
        """设置分类表数据"""
        classifications = [
            ["GA类", "GA1", "长输管道", "输送有毒、可燃、易爆气体，设计压力>1.6MPa"],
            ["GA类", "GA2", "长输管道", "GA1以外的长输管道"],
            ["GB类", "GB1", "公用管道", "城镇燃气管道"],
            ["GB类", "GB2", "公用管道", "城镇热力管道"],
            ["GC类", "GC1", "工业管道", "输送极度危害、高度危害介质，或设计压力≥4.0MPa"],
            ["GC类", "GC2", "工业管道", "除GC3外的其他工业管道"],
            ["GC类", "GC3", "工业管道", "输送无毒、非可燃介质，设计压力≤1.0MPa"]
        ]
        
        self.classification_table.setRowCount(len(classifications))
        for i, row_data in enumerate(classifications):
            for j, data in enumerate(row_data):
                item = QTableWidgetItem(data)
                item.setTextAlignment(Qt.AlignCenter)
                self.classification_table.setItem(i, j, item)
        
        # 调整表格列宽
        header = self.classification_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
    
    def create_standard_tab(self):
        """创建标准说明标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 标准说明文本
        standard_text = QTextEdit()
        standard_text.setReadOnly(True)
        standard_text.setHtml(self.get_standard_html())
        layout.addWidget(standard_text)
        
        return tab
    
    def get_standard_html(self):
        """获取标准说明HTML内容"""
        return """
        <h2>压力管道定义与分类标准</h2>
        
        <h3>压力管道定义</h3>
        <p>根据《压力管道安全技术监察规程》，压力管道是指利用一定的压力，用于输送气体或者液体的管状设备，其范围规定为最高工作压力大于或者等于0.1MPa（表压）的气体、液化气体、蒸汽介质或者可燃、易爆、有毒、有腐蚀性、最高工作温度高于或者等于标准沸点的液体介质，且公称直径大于25mm的管道。</p>
        
        <h3>压力管道分类</h3>
        
        <h4>GA类 - 长输管道</h4>
        <ul>
            <li><b>GA1级：</b>
                <ul>
                    <li>输送有毒、可燃、易爆气体介质，设计压力大于1.6MPa的管道</li>
                    <li>输送有毒、可燃、易爆液体介质，输送距离≥200km且公称直径≥300mm的管道</li>
                    <li>输送浆体介质，输送距离≥50km且公称直径≥150mm的管道</li>
                </ul>
            </li>
            <li><b>GA2级：</b>GA1级以外的长输管道</li>
        </ul>
        
        <h4>GB类 - 公用管道</h4>
        <ul>
            <li><b>GB1级：</b>城镇燃气管道</li>
            <li><b>GB2级：</b>城镇热力管道</li>
        </ul>
        
        <h4>GC类 - 工业管道</h4>
        <ul>
            <li><b>GC1级：</b>
                <ul>
                    <li>输送毒性程度为极度危害介质、高度危害气体介质和工作温度高于标准沸点的高度危害液体介质的管道</li>
                    <li>输送火灾危险性为甲、乙类可燃气体或者甲类液体（包括液化烃）的管道，并且设计压力≥4.0MPa的管道</li>
                    <li>输送流体介质并且设计压力≥10.0MPa，或者设计压力≥4.0MPa且设计温度≥400℃的管道</li>
                </ul>
            </li>
            <li><b>GC2级：</b>除GC3级以外的其他工业管道</li>
            <li><b>GC3级：</b>输送无毒、非可燃流体介质，设计压力≤1.0MPa且设计温度>-20℃但不大于185℃的管道</li>
        </ul>
        
        <h3>主要参考标准</h3>
        <ul>
            <li>TSG D0001-2009《压力管道安全技术监察规程—工业管道》</li>
            <li>GB/T 20801-2020《压力管道规范 工业管道》</li>
            <li>GB 50160-2018《石油化工企业设计防火标准》</li>
            <li>GB 50028-2006《城镇燃气设计规范》</li>
        </ul>
        
        <h3>注意事项</h3>
        <p>本计算工具仅供参考，实际工程应用请以相关标准和规范为准。压力管道的定义和分类可能因具体项目要求和地方规定而有所不同。</p>
        """
    
    def calculate_pipe_definition(self):
        """计算压力管道定义"""
        try:
            # 获取输入值
            design_pressure = float(self.pressure_input.text() or 0)
            working_pressure = float(self.working_pressure_input.text() or 0)
            design_temp = float(self.temp_input.text() or 0)
            working_temp = float(self.working_temp_input.text() or 0)
            diameter = float(self.diameter_input.text() or 0)
            media_type = self.media_combo.currentText()
            
            # 验证输入
            if design_pressure <= 0 or diameter <= 0:
                QMessageBox.warning(self, "输入错误", "请填写设计压力和公称直径！")
                return
            
            # 判断是否为压力管道
            is_pressure_pipe = self.is_pressure_pipe(design_pressure, diameter, media_type, working_temp)
            
            # 确定管道类别
            pipe_class = self.determine_pipe_class(design_pressure, design_temp, media_type, diameter)
            
            # 显示结果
            self.display_results(is_pressure_pipe, pipe_class, design_pressure, diameter, media_type)
            
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的数值！")
    
    def is_pressure_pipe(self, pressure, diameter, media_type, temp):
        """判断是否为压力管道"""
        # 基本条件：压力≥0.1MPa且直径>25mm
        if pressure < 0.1 or diameter <= 25:
            return False
        
        # 介质条件
        gaseous_media = ["气体", "液化气体", "蒸汽"]
        hazardous_liquid = ["可燃液体", "有毒介质"]
        
        if media_type in gaseous_media:
            return True
        elif media_type in hazardous_liquid:
            return True
        elif media_type == "一般液体" and temp >= 100:  # 假设标准沸点为100°C
            return True
        
        return False
    
    def determine_pipe_class(self, pressure, temp, media_type, diameter):
        """确定管道类别（简化算法）"""
        hazardous_media = ["有毒介质", "可燃液体"]
        
        # GC1级条件
        if (media_type == "有毒介质" and pressure >= 0.1) or \
           (media_type == "可燃液体" and pressure >= 4.0) or \
           (pressure >= 10.0) or \
           (pressure >= 4.0 and temp >= 400):
            return "GC1"
        
        # GC3级条件
        if media_type == "一般液体" and pressure <= 1.0 and -20 < temp <= 185:
            return "GC3"
        
        # 默认GC2级
        return "GC2"
    
    def display_results(self, is_pressure_pipe, pipe_class, pressure, diameter, media_type):
        """显示计算结果"""
        result_text = f"""
        <h3>计算结果</h3>
        
        <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr style="background-color: #f8f9fa;">
            <td style="padding: 8px; font-weight: bold;">项目</td>
            <td style="padding: 8px;">结果</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">是否为压力管道</td>
            <td style="padding: 8px; {'color: green;' if is_pressure_pipe else 'color: red;'}">
                {'是压力管道' if is_pressure_pipe else '不是压力管道'}
            </td>
        </tr>
        """
        
        if is_pressure_pipe:
            result_text += f"""
        <tr>
            <td style="padding: 8px; font-weight: bold;">管道类别</td>
            <td style="padding: 8px; color: #e74c3c; font-weight: bold;">{pipe_class}级</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">设计压力</td>
            <td style="padding: 8px;">{pressure} MPa</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">公称直径</td>
            <td style="padding: 8px;">{diameter} mm</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">介质类型</td>
            <td style="padding: 8px;">{media_type}</td>
        </tr>
        """
        
        result_text += "</table>"
        
        if is_pressure_pipe:
            result_text += f"""
            <h4> {pipe_class}级管道说明</h4>
            <p>{self.get_class_description(pipe_class)}</p>
            
            <h4>注意事项</h4>
            <ul>
                <li>请按照相关规范进行设计、制造和检验</li>
                <li>需要相应的资质和许可</li>
                <li>定期进行安全检查和维护</li>
            </ul>
            """
        
        self.result_text.setHtml(result_text)
    
    def get_class_description(self, pipe_class):
        """获取类别说明"""
        descriptions = {
            "GC1": "属于GC1级工业管道，输送介质具有高度危险性，需要严格的设计、制造和检验要求。",
            "GC2": "属于GC2级工业管道，为一般工业管道，需按照相关规范进行设计和检验。",
            "GC3": "属于GC3级工业管道，危险性较低，但仍需按照规范进行设计和施工。"
        }
        return descriptions.get(pipe_class, "未知类别")
    
    def clear_inputs(self):
        """清空输入"""
        self.pressure_input.clear()
        self.working_pressure_input.clear()
        self.temp_input.clear()
        self.working_temp_input.clear()
        self.diameter_input.clear()
        self.media_combo.setCurrentIndex(0)
        self.result_text.clear()

    def _get_history_data(self):
        """提供历史记录数据"""
        design_pressure = float(self.pressure_input.text() or 0)
        working_pressure = float(self.working_pressure_input.text() or 0)
        design_temp = float(self.temp_input.text() or 0)
        working_temp = float(self.working_temp_input.text() or 0)
        diameter = float(self.diameter_input.text() or 0)
        media_type = self.media_combo.currentText()

        inputs = {
            "设计压力_MPa": design_pressure,
            "工作压力_MPa": working_pressure,
            "设计温度_C": design_temp,
            "工作温度_C": working_temp,
            "公称直径_mm": diameter,
            "介质类型": media_type
        }

        outputs = {}
        result_text = self.result_text.toPlainText()
        if "管道类别" in result_text or "GC" in result_text:
            import re
            class_match = re.search(r'(GC[123])', result_text)
            if class_match:
                outputs["判定管道类别"] = class_match.group(1)

        return {"inputs": inputs, "outputs": outputs}

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = 压力管道定义()
    widget.resize(800, 600)
    widget.show()
    
    sys.exit(app.exec())