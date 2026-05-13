from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox, QFrame,
    QScrollArea, QDialog, QSpinBox, QButtonGroup, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy
)
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
class ComponentDialog(QDialog):
    """组分添加/编辑对话框"""
    
    def __init__(self, parent=None, component_data=None):
        super().__init__(parent)
        self.component_data = component_data or {}
        self.setWindowTitle("添加/编辑组分" if component_data else "添加组分")
        self.setModal(True)
        self.resize(500, 400)
        self.setup_ui()
    
    def setup_ui(self):
        """设置组分对话框UI"""
        layout = QVBoxLayout(self)
        
        # 输入表单
        form_layout = QGridLayout()
        form_layout.setVerticalSpacing(12)
        form_layout.setHorizontalSpacing(10)
        
        label_style = "QLabel { font-weight: bold; padding-right: 10px; }"
        
        # 组分名称
        name_label = QLabel("组分名称:")
        name_label.setStyleSheet(label_style)
        form_layout.addWidget(name_label, 0, 0)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如: 乙醇")
        form_layout.addWidget(self.name_input, 0, 1)
        
        # 闪点
        flash_label = QLabel("闪点 (°C):")
        flash_label.setStyleSheet(label_style)
        form_layout.addWidget(flash_label, 1, 0)
        
        self.flash_input = QLineEdit()
        self.flash_input.setPlaceholderText("例如: 12.8")
        self.flash_input.setValidator(QDoubleValidator(-100.0, 500.0, 2))
        form_layout.addWidget(self.flash_input, 1, 1)
        
        # 沸点
        boiling_label = QLabel("沸点 (°C):")
        boiling_label.setStyleSheet(label_style)
        form_layout.addWidget(boiling_label, 2, 0)
        
        self.boiling_input = QLineEdit()
        self.boiling_input.setPlaceholderText("例如: 78.4")
        self.boiling_input.setValidator(QDoubleValidator(-273.0, 500.0, 2))
        form_layout.addWidget(self.boiling_input, 2, 1)
        
        # 分子量
        mw_label = QLabel("分子量 (g/mol):")
        mw_label.setStyleSheet(label_style)
        form_layout.addWidget(mw_label, 3, 0)
        
        self.mw_input = QLineEdit()
        self.mw_input.setPlaceholderText("例如: 46.07")
        self.mw_input.setValidator(QDoubleValidator(1.0, 1000.0, 3))
        form_layout.addWidget(self.mw_input, 3, 1)
        
        # 质量分数
        fraction_label = QLabel("质量分数 (%):")
        fraction_label.setStyleSheet(label_style)
        form_layout.addWidget(fraction_label, 4, 0)
        
        self.fraction_input = QLineEdit()
        self.fraction_input.setPlaceholderText("例如: 50.0")
        self.fraction_input.setValidator(QDoubleValidator(0.0, 100.0, 3))
        form_layout.addWidget(self.fraction_input, 4, 1)
        
        layout.addLayout(form_layout)
        
        # 常见溶剂选择
        common_solvents_group = QGroupBox("常见溶剂快速选择")
        solvents_layout = QVBoxLayout(common_solvents_group)
        
        self.solvents_combo = QComboBox()
        self.solvents_combo.setStyleSheet(COMBOBOX_STYLE)
        self.setup_solvents_options()
        self.solvents_combo.currentTextChanged.connect(self.on_solvent_selected)
        solvents_layout.addWidget(self.solvents_combo)
        
        layout.addWidget(common_solvents_group)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_form)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        
        confirm_btn = QPushButton("确认")
        confirm_btn.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(confirm_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 如果编辑模式，填充数据
        if self.component_data:
            self.fill_form_data()
    
    def setup_solvents_options(self):
        """设置常见溶剂选项"""
        solvents = [
            "选择常见溶剂...",
            "甲醇 - 闪点: 11.1°C, 沸点: 64.7°C, 分子量: 32.04",
            "乙醇 - 闪点: 12.8°C, 沸点: 78.4°C, 分子量: 46.07",
            "丙酮 - 闪点: -17.8°C, 沸点: 56.1°C, 分子量: 58.08",
            "苯 - 闪点: -11.1°C, 沸点: 80.1°C, 分子量: 78.11",
            "甲苯 - 闪点: 4.4°C, 沸点: 110.6°C, 分子量: 92.14",
            "二甲苯 - 闪点: 25°C, 沸点: 138-144°C, 分子量: 106.16",
            "正己烷 - 闪点: -22°C, 沸点: 68.7°C, 分子量: 86.18",
            "环己烷 - 闪点: -18°C, 沸点: 80.7°C, 分子量: 84.16",
            "乙酸乙酯 - 闪点: -4°C, 沸点: 77.1°C, 分子量: 88.11",
            "二氯甲烷 - 闪点: 无, 沸点: 39.8°C, 分子量: 84.93",
            "三氯甲烷 - 闪点: 无, 沸点: 61.2°C, 分子量: 119.38",
            "四氯化碳 - 闪点: 无, 沸点: 76.7°C, 分子量: 153.82",
            "水 - 闪点: 无, 沸点: 100°C, 分子量: 18.02"
        ]
        self.solvents_combo.addItems(solvents)
    
    def on_solvent_selected(self, text):
        """处理溶剂选择变化"""
        if text == "选择常见溶剂...":
            return
        
        try:
            parts = text.split(" - ")
            name = parts[0]
            properties = parts[1]
            
            # 提取闪点
            flash_match = [s for s in properties.split(", ") if "闪点:" in s]
            if flash_match:
                flash_text = flash_match[0].replace("闪点:", "").strip()
                if flash_text != "无":
                    self.flash_input.setText(flash_text.replace("°C", ""))
                else:
                    self.flash_input.clear()
            
            # 提取沸点
            boiling_match = [s for s in properties.split(", ") if "沸点:" in s]
            if boiling_match:
                boiling_text = boiling_match[0].replace("沸点:", "").strip()
                # 处理沸点范围
                if "-" in boiling_text:
                    boiling_text = boiling_text.split("-")[0]
                self.boiling_input.setText(boiling_text.replace("°C", ""))
            
            # 提取分子量
            mw_match = [s for s in properties.split(", ") if "分子量:" in s]
            if mw_match:
                mw_text = mw_match[0].replace("分子量:", "").strip()
                self.mw_input.setText(mw_text)
            
            # 设置名称
            self.name_input.setText(name)
            
        except Exception as e:
            print(f"解析溶剂数据错误: {e}")
    
    def fill_form_data(self):
        """填充表单数据"""
        self.name_input.setText(self.component_data.get("name", ""))
        self.flash_input.setText(str(self.component_data.get("flash_point", "")))
        self.boiling_input.setText(str(self.component_data.get("boiling_point", "")))
        self.mw_input.setText(str(self.component_data.get("molecular_weight", "")))
        self.fraction_input.setText(str(self.component_data.get("mass_fraction", "")))
    
    def clear_form(self):
        """清空表单"""
        self.name_input.clear()
        self.flash_input.clear()
        self.boiling_input.clear()
        self.mw_input.clear()
        self.fraction_input.clear()
        self.solvents_combo.setCurrentIndex(0)
    
    def validate_and_accept(self):
        """验证表单并接受"""
        name = self.name_input.text().strip()
        flash_text = self.flash_input.text().strip()
        fraction_text = self.fraction_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "输入错误", "请输入组分名称")
            return
        
        if not flash_text:
            QMessageBox.warning(self, "输入错误", "请输入闪点")
            return
        
        if not fraction_text:
            QMessageBox.warning(self, "输入错误", "请输入质量分数")
            return
        
        try:
            flash_point = float(flash_text)
            mass_fraction = float(fraction_text)
            
            if mass_fraction <= 0 or mass_fraction > 100:
                QMessageBox.warning(self, "输入错误", "质量分数必须在0-100%之间")
                return
                
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的数值")
            return
        
        self.accept()
    
    def get_component_data(self):
        """获取组分数据"""
        return {
            "name": self.name_input.text().strip(),
            "flash_point": float(self.flash_input.text() or 0),
            "boiling_point": float(self.boiling_input.text() or 0),
            "molecular_weight": float(self.mw_input.text() or 0),
            "mass_fraction": float(self.fraction_input.text() or 0)
        }


class MixedLiquidFlashPointCalculator(QWidget):
    """混合液体闪点计算器"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self.components = []
        self.setup_ui()

    def init_data_manager(self):
        """初始化数据管理器"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
        except Exception:
            self.data_manager = None

    def setup_ui(self):
        """设置混合液体闪点计算UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧：输入参数区域
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        scroll_left.setWidgetResizable(True)

        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("QWidget { background: transparent; }")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # 说明文本
        description = QLabel(
            "计算混合液体的闪点，支持多种计算方法。闪点是液体安全性评估的重要参数。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #7f8c8d; font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 计算方法选择
        method_group = QGroupBox("计算方法")
        method_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
            }
        """)
        method_layout = QVBoxLayout(method_group)
        
        self.method_combo = QComboBox()
        self.method_combo.setStyleSheet(COMBOBOX_STYLE)
        self.method_combo.addItems([
            "Le Chatelier 法则 - 适用于理想混合物",
            "最低闪点法 - 保守估计，取最低组分闪点",
            "质量加权平均法 - 基于质量分数的加权平均",
            "摩尔加权平均法 - 基于摩尔分数的加权平均",
            "Cox 图表法 - 基于沸点的经验方法"
        ])
        self.method_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        method_layout.addWidget(self.method_combo)
        
        left_layout.addWidget(method_group)
        
        # 组分管理
        components_group = QGroupBox("混合物组分")
        components_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
            }
        """)
        components_layout = QVBoxLayout(components_group)
        
        # 组分表格
        self.components_table = QTableWidget()
        self.components_table.setColumnCount(6)
        self.components_table.setHorizontalHeaderLabels([
            "组分名称", "闪点(°C)", "沸点(°C)", "分子量", "质量分数(%)", "操作"
        ])
        self.components_table.horizontalHeader().setStretchLastSection(True)
        self.components_table.setAlternatingRowColors(True)
        self.components_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dcdcdc;
                background-color: white;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
        """)
        components_layout.addWidget(self.components_table)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加组分")
        add_btn.clicked.connect(self.add_component)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219955;
            }
        """)
        button_layout.addWidget(add_btn)
        
        clear_btn = QPushButton("清空所有")
        clear_btn.clicked.connect(self.clear_all_components)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        components_layout.addLayout(button_layout)
        
        left_layout.addWidget(components_group)
        
        # 计算按钮
        calculate_btn = QPushButton("查询")
        calculate_btn.setFont(QFont("Arial", 12, QFont.Bold))
        calculate_btn.clicked.connect(self.calculate_flash_point)
        calculate_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                min-height: 50px; padding: 0px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219955;
            }
        """)
        calculate_btn.setMinimumHeight(50)
        calculate_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        left_layout.addWidget(calculate_btn)
        
        # 右侧：结果显示区域
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)
        
        # 结果显示
        self.result_group = QGroupBox("计算结果")
        self.result_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
            }
        """)
        result_layout = QVBoxLayout(self.result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ecf0f1;
                border-radius: 6px;
                padding: 8px;
                background-color: #f8f9fa;
                min-height: 500px;
            }
        """)
        result_layout.addWidget(self.result_text)
        
        right_layout.addWidget(self.result_group)
        
        # 将左右两部分添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)
        main_layout.addWidget(right_widget, 1)
    
    def add_component(self, component_data=None):
        """添加组分"""
        try:
            dialog = ComponentDialog(self, component_data)
            if dialog.exec():
                data = dialog.get_component_data()

                if component_data:
                    # 编辑模式，更新现有数据
                    index = self.components.index(component_data)
                    self.components[index] = data
                else:
                    # 添加模式
                    self.components.append(data)

                self.update_components_table()
        except Exception as e:
            print(f"[闪点计算器] add_component 异常: {e}")
            import traceback
            traceback.print_exc()
    
    def edit_component(self, row):
        """编辑组分"""
        if 0 <= row < len(self.components):
            component_data = self.components[row]
            self.add_component(component_data)
    
    def delete_component(self, row):
        """删除组分"""
        if 0 <= row < len(self.components):
            self.components.pop(row)
            self.update_components_table()
    
    def clear_all_components(self):
        """清空所有组分"""
        if self.components:
            reply = QMessageBox.question(
                self, "确认清空", 
                "确定要清空所有组分数据吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.components.clear()
                self.update_components_table()
    
    def update_components_table(self):
        """更新组分表格"""
        self.components_table.setRowCount(len(self.components))
        
        total_fraction = sum(comp["mass_fraction"] for comp in self.components)
        
        for row, component in enumerate(self.components):
            # 组分名称
            name_item = QTableWidgetItem(component["name"])
            name_item.setTextAlignment(Qt.AlignCenter)
            self.components_table.setItem(row, 0, name_item)
            
            # 闪点
            flash_item = QTableWidgetItem(f"{component['flash_point']:.1f}")
            flash_item.setTextAlignment(Qt.AlignCenter)
            self.components_table.setItem(row, 1, flash_item)
            
            # 沸点
            boiling_item = QTableWidgetItem(f"{component['boiling_point']:.1f}")
            boiling_item.setTextAlignment(Qt.AlignCenter)
            self.components_table.setItem(row, 2, boiling_item)
            
            # 分子量
            mw_item = QTableWidgetItem(f"{component['molecular_weight']:.2f}")
            mw_item.setTextAlignment(Qt.AlignCenter)
            self.components_table.setItem(row, 3, mw_item)
            
            # 质量分数
            fraction_item = QTableWidgetItem(f"{component['mass_fraction']:.2f}")
            fraction_item.setTextAlignment(Qt.AlignCenter)
            self.components_table.setItem(row, 4, fraction_item)
            
            # 操作按钮
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.setContentsMargins(4, 4, 4, 4)
            
            edit_btn = QPushButton("编辑")
            edit_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            edit_btn.clicked.connect(lambda checked, r=row: self.edit_component(r))
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            
            delete_btn = QPushButton("删除")
            delete_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            delete_btn.clicked.connect(lambda checked, r=row: self.delete_component(r))
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            
            button_layout.addWidget(edit_btn)
            button_layout.addWidget(delete_btn)
            button_layout.addStretch()
            
            self.components_table.setCellWidget(row, 5, button_widget)
        
        # 调整列宽
        self.components_table.resizeColumnsToContents()
        
        # 显示总质量分数
        if self.components:
            status_text = f"总质量分数: {total_fraction:.2f}%"
            if abs(total_fraction - 100.0) > 0.1:
                status_text += f" (建议调整为100%)"
            
            # 在表格下方显示状态
            if hasattr(self, 'fraction_label'):
                self.fraction_label.setText(status_text)
            else:
                self.fraction_label = QLabel(status_text)
                self.fraction_label.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 5px;")
                self.components_table.parent().layout().addWidget(self.fraction_label)
    
    def calculate_flash_point(self):
        """计算混合闪点"""
        try:
            if not self.components:
                QMessageBox.warning(self, "计算错误", "请至少添加一个组分")
                return
            
            # 检查质量分数总和
            total_fraction = sum(comp["mass_fraction"] for comp in self.components)
            if abs(total_fraction - 100.0) > 0.1:
                reply = QMessageBox.question(
                    self, "质量分数警告",
                    f"总质量分数为 {total_fraction:.2f}%，不等于100%。是否继续计算？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            method = self.method_combo.currentText()
            
            # 根据不同方法计算闪点
            if "Le Chatelier" in method:
                flash_point = self.calculate_le_chatelier()
            elif "最低闪点法" in method:
                flash_point = self.calculate_minimum_flash()
            elif "质量加权平均法" in method:
                flash_point = self.calculate_weighted_average_mass()
            elif "摩尔加权平均法" in method:
                flash_point = self.calculate_weighted_average_molar()
            elif "Cox 图表法" in method:
                flash_point = self.calculate_cox_method()
            else:
                flash_point = self.calculate_weighted_average_mass()
            
            # 显示结果
            result = self.format_results(method, flash_point, total_fraction)
            self.result_text.setText(result)
            
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def _get_history_data(self):
        """提供历史记录数据"""
        method = self.method_combo.currentText()
        total_fraction = sum(comp["mass_fraction"] for comp in self.components)

        inputs = {
            "计算方法": method,
            "组分数量": len(self.components),
            "总质量分数_%": round(total_fraction, 2)
        }

        # 添加每个组分的信息
        for i, comp in enumerate(self.components):
            inputs[f"组分{i+1}_名称"] = comp.get("name", f"组分{i+1}")
            inputs[f"组分{i+1}_质量分数_%"] = comp.get("mass_fraction", 0)
            inputs[f"组分{i+1}_闪点_C"] = comp.get("flash_point", 0)

        outputs = {}
        # 没有组分时不执行计算，避免空数据处理
        if not self.components:
            return {"inputs": inputs, "outputs": outputs}

        try:
            if "Le Chatelier" in method:
                flash_point = self.calculate_le_chatelier()
            elif "最低闪点法" in method:
                flash_point = self.calculate_minimum_flash()
            elif "质量加权平均法" in method:
                flash_point = self.calculate_weighted_average_mass()
            elif "摩尔加权平均法" in method:
                flash_point = self.calculate_weighted_average_molar()
            elif "Cox 图表法" in method:
                flash_point = self.calculate_cox_method()
            else:
                flash_point = self.calculate_weighted_average_mass()

            outputs = {"混合液体闪点_C": round(flash_point, 1)}
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def calculate_le_chatelier(self):
        """Le Chatelier 法则计算"""
        # 对于理想混合物，使用Le Chatelier公式
        # 1/FP_mix = Σ (y_i / FP_i) 其中y_i是气相摩尔分数
        
        # 首先计算摩尔分数
        total_moles = 0
        for comp in self.components:
            if comp["molecular_weight"] > 0:
                moles = comp["mass_fraction"] / comp["molecular_weight"]
                total_moles += moles
        
        if total_moles == 0:
            return self.calculate_weighted_average_mass()
        
        # 计算混合闪点 (绝对温度)
        sum_reciprocal = 0
        for comp in self.components:
            if comp["molecular_weight"] > 0 and comp["flash_point"] != 0:
                moles = comp["mass_fraction"] / comp["molecular_weight"]
                mole_fraction = moles / total_moles
                
                # 将闪点转换为绝对温度 (K)
                flash_k = comp["flash_point"] + 273.15
                sum_reciprocal += mole_fraction / flash_k
        
        if sum_reciprocal == 0:
            return self.calculate_weighted_average_mass()
        
        flash_mix_k = 1 / sum_reciprocal
        return flash_mix_k - 273.15  # 转换回°C
    
    def calculate_minimum_flash(self):
        """最低闪点法计算"""
        # 取所有组分中的最低闪点
        min_flash = float('inf')
        for comp in self.components:
            if comp["flash_point"] < min_flash:
                min_flash = comp["flash_point"]
        return min_flash
    
    def calculate_weighted_average_mass(self):
        """质量加权平均法计算"""
        total_fraction = sum(comp["mass_fraction"] for comp in self.components)
        if total_fraction == 0:
            return 0
        
        weighted_sum = 0
        for comp in self.components:
            weighted_sum += comp["flash_point"] * comp["mass_fraction"]
        
        return weighted_sum / total_fraction
    
    def calculate_weighted_average_molar(self):
        """摩尔加权平均法计算"""
        total_moles = 0
        weighted_sum = 0
        
        for comp in self.components:
            if comp["molecular_weight"] > 0:
                moles = comp["mass_fraction"] / comp["molecular_weight"]
                total_moles += moles
                weighted_sum += comp["flash_point"] * moles
        
        if total_moles == 0:
            return self.calculate_weighted_average_mass()
        
        return weighted_sum / total_moles
    
    def calculate_cox_method(self):
        """Cox 图表法计算 (基于沸点的经验方法)"""
        # Cox图表法是基于混合物的平均沸点来估算闪点
        # 这里使用简化的经验公式
        
        # 计算质量加权平均沸点
        total_fraction = sum(comp["mass_fraction"] for comp in self.components)
        if total_fraction == 0:
            return 0
        
        avg_boiling = 0
        for comp in self.components:
            avg_boiling += comp["boiling_point"] * comp["mass_fraction"]
        avg_boiling /= total_fraction
        
        # 简化的Cox关系式: 闪点 ≈ 0.7 * 沸点 - 50 (经验公式)
        estimated_flash = 0.7 * avg_boiling - 50
        
        # 限制在合理范围内
        return max(estimated_flash, -50)
    
    def format_results(self, method, flash_point, total_fraction):
        """格式化计算结果"""
        # 安全等级评估
        if flash_point < 0:
            safety_level = "极度危险 (易燃液体)"
            safety_color = "#e74c3c"
        elif flash_point < 23:
            safety_level = "高度危险 (易燃液体)"
            safety_color = "#e67e22"
        elif flash_point < 60:
            safety_level = "中等危险 (可燃液体)"
            safety_color = "#f39c12"
        else:
            safety_level = "相对安全 (难燃液体)"
            safety_color = "#27ae60"
        
        return f"""═══════════════════════════════════════════════════
                         输入参数
═══════════════════════════════════════════════════

计算方法: {method}
组分数量: {len(self.components)} 个
总质量分数: {total_fraction:.2f} %

组分列表:
{self.format_components_list()}

═══════════════════════════════════════════════════
                        计算结果
═══════════════════════════════════════════════════

混合液体闪点: {flash_point:.1f} °C

安全评估:
• 安全等级: <span style="color: {safety_color}; font-weight: bold">{safety_level}</span>
• 闪点分类: {self.get_flash_point_classification(flash_point)}

不同方法对比:
• Le Chatelier 法则: {self.calculate_le_chatelier():.1f} °C
• 最低闪点法: {self.calculate_minimum_flash():.1f} °C
• 质量加权平均: {self.calculate_weighted_average_mass():.1f} °C
• 摩尔加权平均: {self.calculate_weighted_average_molar():.1f} °C

═══════════════════════════════════════════════════
                        计算说明
═══════════════════════════════════════════════════

• Le Chatelier法则适用于理想混合物
• 最低闪点法提供最保守的安全估计
• 质量/摩尔加权平均法适用于相似组分
• Cox图表法基于沸点经验关系
• 实际闪点可能因非理想性而有所不同
• 建议进行实验验证重要应用"""
    
    def format_components_list(self):
        """格式化组分列表"""
        components_text = ""
        for i, comp in enumerate(self.components, 1):
            components_text += f"{i}. {comp['name']}: 闪点{comp['flash_point']}°C, 质量分数{comp['mass_fraction']}%\\n"
        return components_text
    
    def get_flash_point_classification(self, flash_point):
        """获取闪点分类"""
        if flash_point < 0:
            return "Class I A (极度易燃)"
        elif flash_point < 23:
            return "Class I B (高度易燃)" 
        elif flash_point < 60:
            return "Class I C (易燃)"
        else:
            return "Class II/III (可燃/难燃)"


if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = MixedLiquidFlashPointCalculator()
    widget.resize(900, 700)
    widget.show()
    
    sys.exit(app.exec())