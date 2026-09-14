from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit, QComboBox, QGridLayout, QMessageBox,
    QFrame, QScrollArea, QDialog, QSpinBox, QButtonGroup,
    QFileDialog, QDialogButtonBox, QSizePolicy
)
from PySide6.QtGui import QDoubleValidator
from PySide6.QtCore import Qt
import math
import re
from datetime import datetime
import sys
from pathlib import Path


from app_styles import (COMBOBOX_STYLE, GROUP_STYLE,
                        CALC_BUTTON_STYLE, MODE_BUTTON_STYLE,
                        SCROLL_AREA_STYLE, INPUT_LABEL_STYLE,
                        CLEAR_BTN_STYLE, DOCX_BTN_STYLE, PDF_BTN_STYLE)

from calculator_base import CalculatorBase
from common_constants import C_TO_K, G, ATM_PRESSURE_MPA, WATER_DENSITY, WATER_CP, load_steam_iapws, get_steam_props
# DOCX 报告导出
from utils.docx_utils import ReportExporter


class 气体标态转压缩态(CalculatorBase):
    """气体标准状态转压缩状态（左右布局优化版）"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        
        # 使用传入的数据管理器或创建新的
        if data_manager is not None:
            self.data_manager = data_manager
        else:
            self.init_data_manager()
        
        self.setup_ui()

        # 禁止未展开时鼠标滚轮切换下拉菜单
        self.setup_wheel_blocker()
    
    def init_data_manager(self):
        """初始化数据管理器 - 使用单例模式"""
        try:
            from data_manager import DataManager
            self.data_manager = DataManager.get_instance()
            print("使用共享的数据管理器实例")
        except Exception as e:
            print(f"数据管理器初始化失败: {e}")
            self.data_manager = None
    
    def setup_ui(self):
        """设置左右布局的气体状态转换UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧：输入参数区域 (占2/3宽度)
        scroll_left = QScrollArea()
        scroll_left.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 8px; margin: 0; } QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        scroll_left.setWidgetResizable(True)

        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_widget.setStyleSheet("")  # 限制最大宽度
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # 1. 首先添加说明文本
        description = QLabel(
            "将气体从标准状态(0°C, 101.325kPa)转换为实际状态(压缩状态)，用于工程设计和设备选型。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; padding: 5px;")
        left_layout.addWidget(description)
        
        # 2. 输入参数组 - 使用GridLayout实现整齐的布局
        input_group = QGroupBox("输入参数")
        
        # 使用GridLayout确保整齐排列
        input_layout = QGridLayout(input_group)
        input_layout.setVerticalSpacing(12)
        input_layout.setHorizontalSpacing(10)
        input_layout.setColumnStretch(0, 4)
        input_layout.setColumnStretch(1, 8)
        input_layout.setColumnStretch(2, 5)
        
        # 标签样式 - 右对齐
        label_style = """
            QLabel {
                font-weight: bold;
                padding-right: 10px;
            }
        """
        
        # 输入框和下拉菜单不设置固定宽度，由SizePolicy和stretch控制
        
        row = 0
        
        # 标准状态流量
        flow_label = QLabel("标准状态流量 (Nm³/h):")
        flow_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        flow_label.setStyleSheet(label_style)
        input_layout.addWidget(flow_label, row, 0)
        
        self.flow_input = QLineEdit("1000")
        self.flow_input.setPlaceholderText("例如: 1000")
        self.flow_input.setValidator(QDoubleValidator(0.1, 1000000.0, 6))
        self.flow_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.flow_input, row, 1)
        
        # 流量输入不需要下拉，替换为提示标签
        self.flow_hint = QLabel("直接输入标准状态流量")
        self.flow_hint.setStyleSheet("font-style: italic;")
        self.flow_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.flow_hint, row, 2)
        
        row += 1
        
        # 标准状态定义
        standard_label = QLabel("标准状态:")
        standard_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        standard_label.setStyleSheet(label_style)
        input_layout.addWidget(standard_label, row, 0)
        
        self.standard_combo = QComboBox()
        self.standard_combo.setStyleSheet(COMBOBOX_STYLE)
        self.standard_combo.addItems([
            "- 请选择标准状态 -",
            "0°C, 101.325 kPa (国际标准)",
            "15°C, 101.325 kPa (欧美标准)",
            "20°C, 101.325 kPa (中国标准)",
            "自定义标准状态"
        ])
        self.standard_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.standard_combo.currentTextChanged.connect(self.on_standard_changed)
        input_layout.addWidget(self.standard_combo, row, 1)
        
        # 标准状态提示标签
        self.standard_hint = QLabel("选择标准状态定义")
        self.standard_hint.setStyleSheet("font-style: italic;")
        self.standard_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.standard_hint, row, 2)
        
        row += 1
        
        # 自定义标准状态（隐藏时占用一行但不显示）
        self.custom_standard_group = QGroupBox("自定义标准状态")
        custom_layout = QGridLayout(self.custom_standard_group)
        
        # 标准温度
        std_temp_label = QLabel("标准温度 (°C):")
        std_temp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        std_temp_label.setStyleSheet(label_style)
        custom_layout.addWidget(std_temp_label, 0, 0)
        
        self.std_temp_input = QLineEdit("0")
        self.std_temp_input.setPlaceholderText("例如: 0")
        self.std_temp_input.setValidator(QDoubleValidator(-50.0, 100.0, 6))
        self.std_temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        custom_layout.addWidget(self.std_temp_input, 0, 1)
        
        # 标准温度提示
        self.std_temp_hint = QLabel("输入标准温度")
        self.std_temp_hint.setStyleSheet("font-style: italic;")
        self.std_temp_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        custom_layout.addWidget(self.std_temp_hint, 0, 2)
        
        # 标准压力
        std_pressure_label = QLabel("标准压力 (kPa):")
        std_pressure_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        std_pressure_label.setStyleSheet(label_style)
        custom_layout.addWidget(std_pressure_label, 1, 0)
        
        self.std_pressure_input = QLineEdit("101.325")
        self.std_pressure_input.setPlaceholderText("例如: 101.325")
        self.std_pressure_input.setValidator(QDoubleValidator(50.0, 200.0, 6))
        self.std_pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        custom_layout.addWidget(self.std_pressure_input, 1, 1)
        
        # 标准压力提示
        self.std_pressure_hint = QLabel("输入标准压力")
        self.std_pressure_hint.setStyleSheet("font-style: italic;")
        self.std_pressure_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        custom_layout.addWidget(self.std_pressure_hint, 1, 2)
        custom_layout.setColumnStretch(0, 4)
        custom_layout.setColumnStretch(1, 8)
        custom_layout.setColumnStretch(2, 5)
        
        # 将自定义标准状态组添加到主布局
        input_layout.addWidget(self.custom_standard_group, row, 0, 1, 3)
        self.custom_standard_group.setVisible(False)
        
        row += 1
        
        # 实际状态压力
        actual_pressure_label = QLabel("实际状态压力 (kPa):")
        actual_pressure_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        actual_pressure_label.setStyleSheet(label_style)
        input_layout.addWidget(actual_pressure_label, row, 0)

        self.actual_pressure_input = QLineEdit("500")
        self.actual_pressure_input.setPlaceholderText("例如: 500")
        self.actual_pressure_input.setValidator(QDoubleValidator(0.1, 10000.0, 6))
        self.actual_pressure_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.actual_pressure_input, row, 1)

        # 压力制式：绝压/表压（表压自动 +101.325 kPa）
        self.pressure_type_combo = QComboBox()
        self.pressure_type_combo.setStyleSheet(COMBOBOX_STYLE)
        self.pressure_type_combo.addItems(["绝压", "表压"])
        self.pressure_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.pressure_type_combo, row, 2)
        
        row += 1
        
        # 实际状态温度
        actual_temp_label = QLabel("实际状态温度 (°C):")
        actual_temp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        actual_temp_label.setStyleSheet(label_style)
        input_layout.addWidget(actual_temp_label, row, 0)
        
        self.actual_temp_input = QLineEdit("20")
        self.actual_temp_input.setPlaceholderText("例如: 20")
        self.actual_temp_input.setValidator(QDoubleValidator(-50.0, 500.0, 6))
        self.actual_temp_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.actual_temp_input, row, 1)
        
        # 温度输入不需要下拉，替换为提示标签
        self.temp_hint = QLabel("直接输入实际温度值")
        self.temp_hint.setStyleSheet("font-style: italic;")
        self.temp_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.temp_hint, row, 2)
        
        row += 1
        
        # 气体压缩因子
        compress_label = QLabel("气体压缩因子 Z:")
        compress_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        compress_label.setStyleSheet(label_style)
        input_layout.addWidget(compress_label, row, 0)
        
        self.compress_input = QLineEdit()
        self.compress_input.setPlaceholderText("例如: 1.0")
        self.compress_input.setReadOnly(True)
        self.compress_input.setText("1.0")
        self.compress_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        input_layout.addWidget(self.compress_input, row, 1)
        
        self.compress_combo = QComboBox()
        self.compress_combo.setStyleSheet(COMBOBOX_STYLE)
        self.compress_combo.addItems([
            "- 请选择压缩因子 -",
            "1.0 - 理想气体",
            "0.9 - 轻微可压缩气体",
            "0.8 - 中等可压缩气体",
            "自定义压缩因子"
        ])
        self.compress_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.compress_combo.currentTextChanged.connect(self.on_compress_changed)
        input_layout.addWidget(self.compress_combo, row, 2)
        
        left_layout.addWidget(input_group)
        
        # 3. 在底部添加拉伸因子
        left_layout.addStretch()
        
        # 右侧：结果显示区域 (占1/3宽度)
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
        calc_btn.clicked.connect(self.calculate)
        right_layout.addWidget(calc_btn)
        
        # 将左右两部分添加到主布局
        scroll_left.setWidget(left_widget)
        main_layout.addWidget(scroll_left, 2)  # 左侧占2/3
        main_layout.addWidget(right_widget, 1)  # 右侧占1/3
    
    def on_standard_changed(self, text):
        """处理标准状态选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            self.custom_standard_group.setVisible(False)
            return
            
        if "自定义" in text:
            self.custom_standard_group.setVisible(True)
        else:
            self.custom_standard_group.setVisible(False)
    
    def on_compress_changed(self, text):
        """处理压缩因子选择变化"""
        # 检查是否选择了空值选项
        if text.startswith("-") or not text.strip():
            # 恢复可编辑，避免永久只读
            self.compress_input.setReadOnly(False)
            self.compress_input.setPlaceholderText("输入压缩因子，如 0.95")
            return
            
        if "自定义" in text:
            self.compress_input.setReadOnly(False)
            self.compress_input.setPlaceholderText("输入自定义值")
            self.compress_input.clear()
        else:
            self.compress_input.setReadOnly(True)
            try:
                # 从文本中提取数字
                import re
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    compress_value = float(match.group(1))
                    self.compress_input.setText(f"{compress_value:.1f}")
            except:
                pass
    
    def get_standard_conditions(self):
        """获取标准状态条件"""
        text = self.standard_combo.currentText()
        
        # 检查是否为空值选项
        if text.startswith("-") or not text.strip():
            # 如果没有选择，返回国际标准
            return 0.0, 101.325
        
        if "自定义" in text:
            try:
                std_temp = float(self.std_temp_input.text() or 0)
                std_pressure = float(self.std_pressure_input.text() or 0)
                return std_temp, std_pressure
            except ValueError:
                return 0.0, 101.325  # 默认国际标准
        elif "0°C" in text:
            return 0.0, 101.325
        elif "15°C" in text:
            return 15.0, 101.325
        elif "20°C" in text:
            return 20.0, 101.325
        else:
            return 0.0, 101.325  # 默认国际标准
    
    def clear_inputs(self):
        """清空所有输入"""
        self.flow_input.clear()
        self.standard_combo.setCurrentIndex(0)
        self.actual_pressure_input.clear()
        self.actual_temp_input.clear()
        self.compress_combo.setCurrentIndex(0)
        self.compress_input.setText("1.0")
        self.compress_input.setReadOnly(False)
        self.compress_input.setPlaceholderText("输入压缩因子，如 0.95")
        self.custom_standard_group.setVisible(False)
        self.result_text.clear()
    
    def calculate(self):
        """转换气体状态"""
        try:
            # 获取输入值
            std_flow = float(self.flow_input.text() or 0)
            actual_pressure = float(self.actual_pressure_input.text() or 0)
            actual_temp = float(self.actual_temp_input.text() or 0)
            compress_factor = float(self.compress_input.text() or 0)
            
            std_temp, std_pressure = self.get_standard_conditions()
            
            # 验证输入
            std_temp_k = std_temp + C_TO_K
            actual_temp_k = actual_temp + C_TO_K
            if std_flow <= 0 or actual_pressure <= 0 or std_temp_k <= 0 or actual_temp_k <= 0:
                QMessageBox.warning(self, "输入错误", f"请填写有效的参数（流量和压力必须大于0，温度不能低于{-273.15:.2f}°C）")
                return
            if compress_factor <= 0:
                QMessageBox.warning(self, "输入错误", "压缩因子必须大于0")
                return

            # 压力制式：表压自动换算为绝压（+101.325 kPa）
            pressure_type = self.pressure_type_combo.currentText()
            if pressure_type == "表压":
                actual_pressure_abs = actual_pressure + 101.325
            else:
                actual_pressure_abs = actual_pressure
            if actual_pressure_abs <= 0:
                QMessageBox.warning(self, "输入错误", "换算后的绝对压力必须大于0")
                return

            std_pressure_abs = std_pressure
            
            # 计算实际状态流量
            # 使用理想气体状态方程: P1·V1/T1 = P2·V2/T2 (考虑压缩因子)
            actual_flow = std_flow * (std_pressure_abs / actual_pressure_abs) * (actual_temp_k / std_temp_k) * compress_factor
            
            # 计算密度变化
            # 密度与压力成正比，与温度成反比
            std_density_factor = 1.0  # 相对密度
            actual_density_factor = std_density_factor * (actual_pressure_abs / std_pressure_abs) * (std_temp_k / actual_temp_k) / compress_factor
            
            # 显示结果 - 使用格式化的输出
            result = f"""═══════════
 输入参数
═══════════

标准状态:
• 流量: {std_flow} Nm³/h
• 温度: {std_temp} °C ({std_temp_k:.2f} K)
• 压力: {std_pressure} kPa

实际状态:
• 压力: {actual_pressure} kPa ({pressure_type})
• 绝对压力: {actual_pressure_abs:.3f} kPa
• 温度: {actual_temp} °C ({actual_temp_k:.2f} K)
• 压缩因子 Z: {compress_factor}

═══════════
转换结果
═══════════

流量转换:
• 实际状态流量: {actual_flow:.2f} m³/h
• 实际状态流量: {actual_flow/60:.4f} m³/min

密度变化:
• 相对密度变化: {actual_density_factor:.4f} 倍

流量对比:
"""
            
            if actual_flow < std_flow:
                result += f"• 实际状态流量比标准状态小 {std_flow/actual_flow:.2f} 倍"
            else:
                result += f"• 实际状态流量比标准状态大 {actual_flow/std_flow:.2f} 倍"

            result += f"""

═══════════
计算公式
═══════════

Q_actual = Q_std × (P_std / P_actual) × (T_actual / T_std) × Z

其中:
• Q = 体积流量
• P = 绝对压力 (kPa)
• T = 绝对温度 (K)  
• Z = 压缩因子

详细计算:
{std_flow} × ({std_pressure_abs} / {actual_pressure_abs}) × ({actual_temp_k:.2f} / {std_temp_k:.2f}) × {compress_factor}
= {actual_flow:.2f} m³/h

═══════════
应用说明
═══════════

• 标准状态通常指 0°C, 101.325 kPa
• 实际工程中需根据具体气体性质确定压缩因子
• 对于高压气体，压缩因子对结果影响显著
• 计算结果仅供参考，实际应用请考虑安全系数"""
            
            self.result_text.setText(result)
            
        except ValueError as e:
            QMessageBox.critical(self, "计算错误", f"参数输入格式错误: {str(e)}")
        except ZeroDivisionError:
            QMessageBox.critical(self, "计算错误", "压力或温度不能为零")
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")

    def _get_history_data(self):
        """提供历史记录数据"""
        std_flow = float(self.flow_input.text() or 0)
        actual_pressure = float(self.actual_pressure_input.text() or 0)
        actual_temp = float(self.actual_temp_input.text() or 0)
        compress_factor = float(self.compress_input.text() or 0)
        std_temp, std_pressure = self.get_standard_conditions()
        pressure_type = self.pressure_type_combo.currentText()
        if pressure_type == "表压":
            actual_pressure_abs = actual_pressure + 101.325
        else:
            actual_pressure_abs = actual_pressure

        inputs = {
            "标况流量_Nm3_h": std_flow,
            "标况温度_C": std_temp,
            "标况压力_kPa": std_pressure,
            "实际压力_kPa": actual_pressure,
            "压力制式": pressure_type,
            "实际温度_C": actual_temp,
            "压缩因子Z": compress_factor
        }

        outputs = {}
        try:
            std_temp_k = std_temp + C_TO_K
            actual_temp_k = actual_temp + C_TO_K
            if actual_pressure_abs > 0 and actual_pressure > 0:
                actual_flow = std_flow * (std_pressure / actual_pressure_abs) * (actual_temp_k / std_temp_k) * compress_factor
                actual_density_factor = (actual_pressure_abs / std_pressure) * (std_temp_k / actual_temp_k) / compress_factor
                outputs = {
                    "绝对压力_kPa": round(actual_pressure_abs, 3),
                    "实际流量_m3_h": round(actual_flow, 2),
                    "实际流量_m3_min": round(actual_flow / 60, 4),
                    "密度变化倍数": round(actual_density_factor, 4)
                }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def get_project_info(self):
        """获取工程信息 - 返回 dict（标准写法，无模态弹窗）"""
        try:
            saved_info = {}
            if self.data_manager:
                saved_info = self.data_manager.get_project_info()
            return {
                'company_name': saved_info.get('company_name', ''),
                'project_number': saved_info.get('project_number', ''),
                'project_name': saved_info.get('project_name', ''),
                'subproject_name': saved_info.get('subproject_name', ''),
                'report_number': ''
            }
        except Exception:
            return {
                'company_name': '', 'project_number': '',
                'project_name': '', 'subproject_name': '', 'report_number': ''
            }

    def generate_report(self):
        """生成计算书"""
        try:
            # 获取当前结果文本
            result_text = self.result_text.toPlainText()
            
            # 更宽松的检查条件
            if not result_text or ("转换结果" not in result_text):
                QMessageBox.warning(self, "生成失败", "请先进行计算再生成计算书")
                return None
                
            # 获取工程信息
            project_info = self.get_project_info()
            if not project_info:
                return None  # 用户取消了输入
            
            # 添加报告头信息
            report = f"""工程计算书 - 气体状态转换计算
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
计算工具: ChemCal 工程计算模块
========================================

"""
            report += result_text
            
            # 添加工程信息部分
            report += f"""══════════
 工程信息
══════════

    公司名称: {project_info['company_name']}
    工程编号: {project_info['project_number']}
    工程名称: {project_info['project_name']}
    子项名称: {project_info['subproject_name']}
    计算日期: {datetime.now().strftime('%Y-%m-%d')}

══════════
计算书标识
══════════

    计算书编号: {project_info['report_number']}
    版本: 1.0
    状态: 正式计算书

══════════
备注说明
══════════

    1. 本计算书基于理想气体状态方程及相关标准规范
    2. 计算结果仅供参考，实际应用需考虑安全系数
    3. 重要工程参数应经专业工程师审核确认
    4. 计算条件变更时应重新进行计算

---
生成于 ChemCal 工程计算模块
"""
            return report
            
        except Exception as e:
            print(f"生成计算书失败: {e}")
            return None

    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "气体标态转压缩态")
    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "气体标态转压缩态")
    def process_content_for_pdf(self, content):
        """处理内容，使其适合PDF显示"""
        # 清理bullet符号
        content = content.replace("•", "")
        
        # 替换单位符号
        content = content.replace("m³", "m3")
        content = content.replace("g/100g", "g/100g")
        content = content.replace("kg/m³", "kg/m3")
        content = content.replace("Nm³/h", "Nm3/h")
        content = content.replace("Pa·s", "Pa.s")
        
        return content

if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    converter = 气体标态转压缩态()
    converter.resize(1200, 800)
    converter.show()
    
    sys.exit(app.exec())
