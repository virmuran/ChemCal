from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QMessageBox,
    QScrollArea, QDialog, QGridLayout,
    QTableWidget, QTableWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator


from app_styles import (COMBOBOX_STYLE, CLEAR_BTN_STYLE,
                        DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K
from utils.docx_utils import ReportExporter

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
        self.flash_input.setPlaceholderText("例如: 12.8（留空 = 不燃组分，如水）")
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
        fp = self.component_data.get("flash_point")
        self.name_input.setText(self.component_data.get("name", ""))
        self.flash_input.setText("" if fp is None else str(fp))
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
        """验证表单并接受

        修复：原实现强制要求填闪点，"水/二氯甲烷"这类不燃组分（下拉里闪点为"无"）
        根本无法录入，而稀释剂恰恰是影响混合闪点的关键组分。
        现允许闪点留空 = 不燃组分。
        """
        name = self.name_input.text().strip()
        flash_text = self.flash_input.text().strip()
        fraction_text = self.fraction_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "输入错误", "请输入组分名称")
            return
        
        if not fraction_text:
            QMessageBox.warning(self, "输入错误", "请输入质量分数")
            return
        
        try:
            if flash_text:
                float(flash_text)
            mass_fraction = float(fraction_text)
            
            if mass_fraction <= 0 or mass_fraction > 100:
                QMessageBox.warning(self, "输入错误", "质量分数必须在0-100%之间")
                return
                
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的数值")
            return
        
        self.accept()
    
    def get_component_data(self):
        """获取组分数据（闪点留空记为 None，表示不燃组分）"""
        flash_text = self.flash_input.text().strip()
        return {
            "name": self.name_input.text().strip(),
            "flash_point": float(flash_text) if flash_text else None,
            "boiling_point": float(self.boiling_input.text() or 0),
            "molecular_weight": float(self.mw_input.text() or 0),
            "mass_fraction": float(self.fraction_input.text() or 0)
        }


class MixedLiquidFlashPointCalculator(CalculatorBase):
    """混合液体闪点计算器"""

    # 方法名（下拉文本含说明后缀，用 _resolve_method 做包含匹配）
    METHOD_ORDER = ["Le Chatelier 法则", "最低闪点法", "质量加权平均法",
                    "摩尔加权平均法", "沸点关联式(Riazi)"]

    def _resolve_method(self, text: str) -> str:
        """把下拉文本解析为标准方法名"""
        for name in self.METHOD_ORDER:
            if name in text:
                return name
        return "质量加权平均法"
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        self.components = []
        self._last_results = {}
        self.setup_ui()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()

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
        left_widget.setStyleSheet("")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # 说明文本
        description = QLabel(
            "计算混合液体的闪点，支持多种计算方法。闪点是液体安全性评估的重要参数。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 计算方法选择
        method_group = QGroupBox("计算方法")
        method_layout = QVBoxLayout(method_group)
        
        self.method_combo = QComboBox()
        self.method_combo.setStyleSheet(COMBOBOX_STYLE)
        self.method_combo.addItems([
            "Le Chatelier 法则 - 适用于理想混合物",
            "最低闪点法 - 保守估计，取最低组分闪点",
            "质量加权平均法 - 基于质量分数的加权平均",
            "摩尔加权平均法 - 基于摩尔分数的加权平均",
            # 原标签"Cox 图表法"名不符实：实际采用的是 Riazi 沸点关联式
            "沸点关联式(Riazi) - T_fp = 0.7×T_bp(K)，仅需沸点数据"
        ])
        self.method_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        method_layout.addWidget(self.method_combo)
        
        left_layout.addWidget(method_group)
        
        # 组分管理
        components_group = QGroupBox("混合物组分")
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
                /* background-color via theme */
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
            QPushButton:hover:!checked {
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
            QPushButton:hover:!checked {
                background-color: #c0392b;
            }
        """)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        components_layout.addLayout(button_layout)
        
        left_layout.addWidget(components_group)
        
        left_layout.addStretch()

        # 右侧：结果显示区域
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(15)

        # 结果显示
        self.result_group = QGroupBox("计算结果")
        result_layout = QVBoxLayout(self.result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setPlaceholderText("计算结果将在此显示……")
        self.result_text.setStyleSheet(
            "QTextEdit { "
            "font-family: Consolas, 'Microsoft YaHei', monospace; "
            "font-size: 13px; "
            "}"
        )
        result_layout.addWidget(self.result_text)

        right_layout.addWidget(self.result_group)

        # 下载按钮行：清空 → DOCX → PDF
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        for label, style, slot in [
            ("清空", CLEAR_BTN_STYLE, self.clear_inputs),
            ("DOCX", DOCX_BTN_STYLE, self.download_docx_report),
            ("PDF", PDF_BTN_STYLE, self.download_pdf_report),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        right_layout.addLayout(btn_layout)

        # 计算按钮（最底部）
        calc_btn = self.make_calc_button("查 询")
        calc_btn.clicked.connect(self.calculate_flash_point)
        right_layout.addWidget(calc_btn)

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
            
            # 闪点（None = 不燃组分）
            fp = component.get("flash_point")
            flash_item = QTableWidgetItem("不燃" if fp is None else f"{fp:.1f}")
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
                QPushButton:hover:!checked {
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
                QPushButton:hover:!checked {
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
            
            # 不燃组分（闪点留空）不参与闪点计算
            flammable = [c for c in self.components
                         if c.get("flash_point") is not None]
            if not flammable:
                self.result_text.setPlainText(
                    "所有组分均标记为不燃（闪点留空），混合物无闪点。")
                self._last_results = {}
                return

            method = self.method_combo.currentText()

            # 五种方法一次算齐，供结果区与"不同方法对比"共用同一口径
            results = self.compute_all_methods()
            flash_point = results.get(self._resolve_method(method))

            # 初沸点（取可燃组分最低沸点）→ GHS 类别 1 与 2 的区分依据
            bps = [c["boiling_point"] for c in flammable
                   if (c.get("boiling_point") or 0) > 0]
            ibp = min(bps) if bps else None

            self._last_results = {"method": method, "flash_point": flash_point,
                                  **results}
            # 必须用 setPlainText：原 setText 会把含 HTML 标签的结果整段按 HTML 渲染，
            # 换行全部丢失，结果框变成一坨没有换行的文字
            self.result_text.setPlainText(
                self.format_results(method, flash_point, total_fraction, results,
                                    ibp=ibp,
                                    n_nonflammable=len(self.components) - len(flammable)))
            
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
            inputs[f"组分{i+1}_闪点_C"] = ("不燃" if comp.get("flash_point") is None
                                          else comp.get("flash_point"))

        outputs = {}
        # 没有可燃组分时不执行计算，避免空数据处理
        if not [c for c in self.components if c.get("flash_point") is not None]:
            outputs["提示"] = "无可燃组分（全部标记为不燃），混合物无闪点"
            return {"inputs": inputs, "outputs": outputs}

        try:
            # 与主计算共用同一套方法（原实现另抄一份 dispatch，已同步为统一入口）
            results = self.compute_all_methods()
            flash_point = results.get(self._resolve_method(method))
            outputs = {f"{k}_C": (round(v, 1) if v is not None else None)
                       for k, v in results.items()}
            outputs["采用方法"] = self._resolve_method(method)
            outputs["混合液体闪点_C"] = round(flash_point, 1) if flash_point is not None else None
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def calculate_le_chatelier(self):
        """Le Chatelier 混合法则：1/T_f,mix = Σ(x_i / T_f,i)

        出处：Le Chatelier 混合规则（Coward & Jones 1952；Liaw 模型；Alqaheem & Riazi 2017
        等一致采用），x_i 为液相摩尔分数，T 为绝对温度。
        仅对可燃组分求和；不燃组分仍计入摩尔分数分母 —— 稀释效应由此体现。
        """
        # 摩尔分数（全部组分参与分母，含不燃组分）
        total_moles = 0.0
        for comp in self.components:
            mw = comp.get("molecular_weight") or 0
            if mw > 0:
                total_moles += comp["mass_fraction"] / mw

        if total_moles <= 0:
            return self.calculate_weighted_average_mass()

        sum_reciprocal = 0.0
        for comp in self.components:
            fp = comp.get("flash_point")
            mw = comp.get("molecular_weight") or 0
            if fp is None or mw <= 0:
                continue
            x_i = (comp["mass_fraction"] / mw) / total_moles
            sum_reciprocal += x_i / (fp + C_TO_K)

        if sum_reciprocal <= 0:
            return None
        return 1.0 / sum_reciprocal - C_TO_K

    def calculate_minimum_flash(self):
        """最低闪点法：取可燃组分中的最低闪点（最保守的安全估计）"""
        fps = [c["flash_point"] for c in self.components
               if c.get("flash_point") is not None]
        return min(fps) if fps else None

    def calculate_weighted_average_mass(self):
        """质量加权平均法（仅在可燃组分之间归一，不燃组分不参与）"""
        pairs = [(c["flash_point"], c["mass_fraction"]) for c in self.components
                 if c.get("flash_point") is not None]
        total = sum(f for _, f in pairs)
        if total <= 0:
            return None
        return sum(fp * f for fp, f in pairs) / total

    def calculate_weighted_average_molar(self):
        """摩尔加权平均法（仅在可燃组分之间归一）"""
        total_moles = 0.0
        weighted_sum = 0.0
        for comp in self.components:
            fp = comp.get("flash_point")
            mw = comp.get("molecular_weight") or 0
            if fp is None or mw <= 0:
                continue
            n = comp["mass_fraction"] / mw
            total_moles += n
            weighted_sum += fp * n

        if total_moles <= 0:
            return self.calculate_weighted_average_mass()
        return weighted_sum / total_moles

    def calculate_cox_method(self):
        """沸点关联式估算：T_fp = 0.7 × T_bp（绝对温度，Riazi 关联式）

        出处：Alqaheem & Riazi, Energy & Fuels 2017, 31, 3578（AIChE 2015 年会论文同结论）：
        烃类及其混合物的闪点/沸点（K）之比近似为常数 0.7，纯烃 AAD 1.7%、石油馏分 2.8%，
        为"只有沸点数据时"公认最简关联式。
        修复：原实现用 0.7×沸点(°C) − 50，属无出处的经验式，且对芳烃偏不安全
        （苯、甲苯会被估到比实测值高 10~25 °C）。
        注意：该关联式源自烃类，含醇/水等极性组分时偏差可能明显偏大。
        """
        pairs = [(c["boiling_point"], c["mass_fraction"]) for c in self.components
                 if (c.get("boiling_point") or 0) > 0]
        total = sum(f for _, f in pairs)
        if total <= 0:
            return None
        avg_boiling = sum(bp * f for bp, f in pairs) / total
        return 0.7 * (avg_boiling + C_TO_K) - C_TO_K

    def compute_all_methods(self):
        """一次算出全部方法结果（避免展示时各算一遍、口径打架）"""
        return {
            "Le Chatelier 法则": self.calculate_le_chatelier(),
            "最低闪点法": self.calculate_minimum_flash(),
            "质量加权平均法": self.calculate_weighted_average_mass(),
            "摩尔加权平均法": self.calculate_weighted_average_molar(),
            "沸点关联式(Riazi)": self.calculate_cox_method(),
        }
    
    def format_results(self, method, flash_point, total_fraction, results=None,
                       ibp=None, n_nonflammable=0):
        """格式化计算结果

        纯文本输出。原实现把带 <span style="..."> 的 HTML 片段交给 setText()，
        Qt 会判定为富文本整段渲染，换行全部丢失。
        """
        results = results or self.compute_all_methods()

        # 安全等级（按 GB 13690 低/中/高闪点液体分档）
        if flash_point < -18:
            safety_level = "极度危险（低闪点液体）"
        elif flash_point < 23:
            safety_level = "高度危险（中闪点液体）"
        elif flash_point <= 61:
            safety_level = "中等危险（高闪点液体）"
        else:
            safety_level = "相对安全（不属易燃液体）"

        cmp_lines = []
        for name in self.METHOD_ORDER:
            v = results.get(name)
            txt = "—（无有效数据）" if v is None else f"{v:.1f} °C"
            extra = "（仅需沸点的粗略估算，源自烃类）" if name.startswith("沸点关联式") else ""
            cmp_lines.append(f"• {name}: {txt}{extra}")

        excluded = ""
        caution = ""
        if n_nonflammable:
            excluded = (f"  注: {n_nonflammable} 个不燃组分（如水）不参与闪点加权平均，\n"
                        f"      但仍计入 Le Chatelier 摩尔分数的分母 —— 稀释效应由此体现\n")
            # 该式假定各组分汽化潜热相近；含水等不燃稀释剂时会严重高估闪点
            # （水+乙醇体系可估出数百 °C），必须明确提示，否则会被误读为"更安全"
            caution = ("""
═══════════════════════════════════════════════════
            ⚠ 含不燃稀释剂时的适用性提示
═══════════════════════════════════════════════════

• Le Chatelier 简化式假定各组分汽化潜热相近、且不燃组分不参与
  可燃蒸气分压 —— 含水/不燃稀释剂时会严重高估闪点（水+乙醇可估出数百 °C），
  该值绝不可单独作为安全依据
• 稀释剂对闪点的真实影响需汽液平衡数据（Antoine + 活度系数）或实测
• 安全设计请以"最低闪点法"数值为准，或按 GB/T 261-2021 闭杯法实测
""")

        # 安全相关场合应以最低值为准
        valid = [v for v in results.values() if v is not None]
        min_note = f"最低估计值 = {min(valid):.1f} °C（安全设计建议取值）" if valid else "无"

        return f"""═══════════════════════════════════════════════════
                         输入参数
═══════════════════════════════════════════════════

计算方法: {method}
组分数量: {len(self.components)} 个（其中不燃组分 {n_nonflammable} 个）
总质量分数: {total_fraction:.2f} %
{excluded}
组分列表:
{self.format_components_list()}

═══════════════════════════════════════════════════
                        计算结果
═══════════════════════════════════════════════════

混合液体闪点: {flash_point:.1f} °C

安全评估:
• 安全等级: {safety_level}
• GB 13690-2009 易燃液体分档: {self.classify_gb13690(flash_point)}
• GB 50016-2014 火灾危险性分类: {self.classify_gb50016(flash_point)}
• GHS / GB 30000.7-2013 类别: {self.get_flash_point_classification(flash_point, ibp)}

不同方法对比:
{chr(10).join(cmp_lines)}

• {min_note}
{caution}
═══════════════════════════════════════════════════
                        计算说明
═══════════════════════════════════════════════════

• Le Chatelier 法则: 1/T_mix = Σ(x_i/T_i)，x 为液相摩尔分数，T 为绝对温度
• 最低闪点法提供最保守的安全估计，安全评价优先采用
• 质量/摩尔加权平均法适用于组分性质相近的混合物
• 沸点关联式 T_fp = 0.7×T_bp(K) 源自烃类（Riazi/AIChE 2015），
  含醇、水等极性组分时偏差可能明显偏大
• 实际闪点受非理想性影响，重要场合应做实验测定（闭杯法 GB/T 261）"""

    def format_components_list(self):
        """格式化组分列表"""
        components_text = ""
        for i, comp in enumerate(self.components, 1):
            fp_txt = "不燃" if comp.get("flash_point") is None else f"{comp['flash_point']}°C"
            components_text += f"{i}. {comp['name']}: 闪点{fp_txt}, 质量分数{comp['mass_fraction']}%\\n"
        return components_text
    
    @staticmethod
    def classify_gb13690(flash_point):
        """GB 13690-2009《化学品分类和危险性公示 通则》/ 危险化学品名录：低/中/高闪点液体"""
        if flash_point < -18:
            return "低闪点液体（闭杯 < −18 °C）"
        if flash_point < 23:
            return "中闪点液体（−18 ≤ 闭杯 < 23 °C）"
        if flash_point <= 61:
            return "高闪点液体（23 ≤ 闭杯 ≤ 61 °C）"
        return "不属易燃液体（闭杯 > 61 °C）"

    @staticmethod
    def classify_gb50016(flash_point):
        """GB 50016-2014《建筑设计防火规范》火灾危险性分类"""
        if flash_point < 28:
            return "甲类（闪点 < 28 °C）"
        if flash_point < 60:
            return "乙类（28 ≤ 闪点 < 60 °C）"
        return "丙类（闪点 ≥ 60 °C）"

    def get_flash_point_classification(self, flash_point, ibp=None):
        """GHS / GB 30000.7-2013 易燃液体类别（与 NFPA 30 的 Class I/II/III 对应）

        类别1: 闪点 < 23 °C 且 初沸点 ≤ 35 °C
        类别2: 闪点 < 23 °C 且 初沸点 > 35 °C
        类别3: 23 ≤ 闪点 ≤ 60 °C
        类别4: 60 < 闪点 ≤ 93 °C
        修复：原实现按 <0 / <23 / <60 直接套 Class I A / I B / I C / II，
        与 GHS 及 NFPA 30 的分档边界都不符（IC 实为 22.8~37.8 °C，
        且 IA / IB 还必须用初沸点区分），会把甲类易燃液体误标成低风险档。
        """
        if flash_point < 23:
            if ibp is None:
                return "类别 1 或 2（闪点 < 23 °C；填入沸点后可区分）"
            if ibp <= 35:
                return f"类别 1（H224：闪点 < 23 °C 且初沸点 {ibp:.0f} °C ≤ 35 °C）"
            return f"类别 2（H225：闪点 < 23 °C 且初沸点 {ibp:.0f} °C > 35 °C）"
        if flash_point <= 60:
            return "类别 3（H226：23 ≤ 闪点 ≤ 60 °C）"
        if flash_point <= 93:
            return "类别 4（H227：60 < 闪点 ≤ 93 °C）"
        return "非易燃液体（闪点 > 93 °C）"

    # ------------------------------------------------------------------
    #  清空 / 历史数据 / 报告
    # ------------------------------------------------------------------

    def clear_inputs(self):
        """清空所有输入与结果"""
        self.components.clear()
        self._last_results = {}
        self.update_components_table()
        self.result_text.clear()

    def get_project_info(self):
        """工程信息（导出契约：company_name / project_number / project_name / subproject_name）"""
        try:
            saved = {}
            dm = getattr(self, "data_manager", None)
            if dm is not None:
                saved = dm.get_project_info() or {}
            return {
                "company_name": saved.get("company_name", ""),
                "project_number": saved.get("project_number", ""),
                "project_name": saved.get("project_name", ""),
                "subproject_name": saved.get("subproject_name", ""),
            }
        except Exception:
            return {}

    def generate_report(self):
        """生成计算书（返回纯文本；未计算返回 None，不产出空壳报告）"""
        if not self._last_results:
            return None
        content = self.result_text.toPlainText().strip()
        if not content:
            return None
        from datetime import datetime
        pi = self.get_project_info()
        lines = [
            "混合液体闪点计算书",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "计算工具: ChemCal 工程计算模块",
            "=" * 50,
            "",
            content,
            "",
            "══════════",
            " 工程信息",
            "══════════",
            "",
            f"    公司名称: {pi.get('company_name', '')}",
            f"    工程编号: {pi.get('project_number', '')}",
            f"    工程名称: {pi.get('project_name', '')}",
            f"    子项名称: {pi.get('subproject_name', '')}",
            f"    计算日期: {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "══════════",
            "备注说明",
            "══════════",
            "",
            "    1. Le Chatelier 法则、最低闪点法、质量/摩尔加权平均法、沸点关联式",
            "       五种方法原理不同，结果存在差异，安全评价应以最低值为准",
            "    2. 危险等级按 GB 13690-2009、GB 50016-2014、GB 30000.7-2013 标注",
            "    3. 闪点计算为理论估算，重要场合应实测（闭杯法 GB/T 261-2021）",
            "",
            "---",
            "生成于 ChemCal 工程计算模块",
        ]
        return "\n".join(lines)

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "混合液体闪点")

    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "混合液体闪点")


if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = MixedLiquidFlashPointCalculator()
    widget.resize(900, 700)
    widget.show()
    
    sys.exit(app.exec())