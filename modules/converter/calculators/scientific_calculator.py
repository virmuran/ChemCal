from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QGridLayout, QGroupBox, 
                               QTextEdit, QApplication, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import math

class ScientificCalculator(QWidget):
    """科学计算器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.calc_history = []
        self.second_function = False
        self.deg_mode = True
        self.new_input_required = False  # 标记是否需要开始新的输入
        self.setup_ui()
    
    def setup_ui(self):
        """设置科学计算器UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        
        # 左侧计算器
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(5)
        
        # 显示框
        self.calc_display = QLineEdit()
        self.calc_display.setFont(QFont("Arial", 16))
        self.calc_display.setAlignment(Qt.AlignRight)
        self.calc_display.setText("0")
        self.calc_display.setMinimumHeight(50)
        left_layout.addWidget(self.calc_display)
        
        # 状态显示
        status_layout = QHBoxLayout()
        self.status_label = QLabel("DEG")
        self.status_label.setFont(QFont("Arial", 10))
        self.status_label.setStyleSheet("color: blue; font-weight: bold;")
        status_layout.addStretch()
        status_layout.addWidget(self.status_label)
        left_layout.addLayout(status_layout)
        
        # 科学计算器按钮网格
        grid_layout = QGridLayout()
        grid_layout.setSpacing(3)
        grid_layout.setContentsMargins(2, 2, 2, 2)
        
        # 重新设计按钮布局，让按钮更大更紧凑
        buttons = [
            # 第一行：2nd, deg, sin, cos, tan
            ['2nd', 'deg', 'sin', 'cos', 'tan'],
            # 第二行：x^y, lg, ln, (, )
            ['x^y', 'lg', 'ln', '(', ')'],
            # 第三行：√x, x², 1/x, %, /
            ['√x', 'x²', '1/x', '%', '/'],
            # 第四行：x!, 7, 8, 9, *
            ['x!', '7', '8', '9', '*'],
            # 第五行：π, 4, 5, 6, -
            ['π', '4', '5', '6', '-'],
            # 第六行：e, 1, 2, 3, +
            ['e', '1', '2', '3', '+'],
            # 第七行：±, 0, ., AC, =
            ['±', '0', '.', 'AC', '=']
        ]
        
        # 创建按钮
        for row, button_row in enumerate(buttons):
            for col, text in enumerate(button_row):
                if not text:
                    continue
                
                btn = QPushButton(text)
                # 增大按钮尺寸
                btn.setMinimumSize(70, 55)
                btn.setFont(QFont("Arial", 12))
                
                # 设置特殊按钮样式
                if text in ['AC', '=']:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #4a6fa5;
                            color: white;
                            font-weight: bold;
                            border-radius: 5px;
                        }
                        QPushButton:hover:!checked {
                            background-color: #3a5a8c;
                        }
                    """)
                elif text in ['sin', 'cos', 'tan', 'x^y', 'lg', 'ln', '√x', 'x²', '1/x', 'x!', 'π', 'e', '±']:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #e0e0e0;
                            color: #333;
                            border-radius: 5px;
                        }
                        QPushButton:hover:!checked {
                            background-color: #d0d0d0;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #f0f0f0;
                            color: #333;
                            border-radius: 5px;
                        }
                        QPushButton:hover:!checked {
                            background-color: #e0e0e0;
                        }
                    """)
                
                btn.clicked.connect(lambda checked, t=text: self.calc_button_click(t))
                grid_layout.addWidget(btn, row, col)
        
        left_layout.addLayout(grid_layout)
        
        # 右侧历史记录
        right_widget = QGroupBox("计算历史")
        right_layout = QVBoxLayout(right_widget)
        
        self.history_text = QTextEdit()
        self.history_text.setFont(QFont("Arial", 10))
        self.history_text.setMinimumWidth(250)
        right_layout.addWidget(self.history_text)
        
        history_btn_layout = QHBoxLayout()
        clear_btn = QPushButton("清空历史")
        clear_btn.clicked.connect(self.clear_history)
        history_btn_layout.addWidget(clear_btn)
        
        copy_btn = QPushButton("复制历史")
        copy_btn.clicked.connect(self.copy_history)
        history_btn_layout.addWidget(copy_btn)
        
        right_layout.addLayout(history_btn_layout)
        
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget)
    
    def calc_button_click(self, text):
        """计算器按钮点击处理"""
        current = self.calc_display.text()
        
        if text == 'AC':
            self.calc_display.setText("0")
            self.second_function = False
            self.new_input_required = False
            self.update_button_labels()
        elif text == '删除':
            if current == "0" or current == "错误" or len(current) == 1:
                self.calc_display.setText("0")
                self.new_input_required = False
            else:
                self.calc_display.setText(current[:-1])
        elif text == '2nd':
            self.second_function = not self.second_function
            self.update_button_labels()
        elif text == 'deg':
            self.deg_mode = not self.deg_mode
            self.status_label.setText("DEG" if self.deg_mode else "RAD")
        elif text == '=':
            try:
                # 替换特殊符号
                expression = current.replace('×', '*').replace('÷', '/')
                
                # 处理函数和常数
                expression = expression.replace('π', 'math.pi').replace('e', 'math.e')
                
                # 处理三角函数
                if self.deg_mode:
                    # 角度制：需要将角度转换为弧度
                    expression = expression.replace('sin', 'math.sin(math.radians')
                    expression = expression.replace('cos', 'math.cos(math.radians')
                    expression = expression.replace('tan', 'math.tan(math.radians')
                    expression = expression.replace('asin', 'math.degrees(math.asin')
                    expression = expression.replace('acos', 'math.degrees(math.acos')
                    expression = expression.replace('atan', 'math.degrees(math.atan')
                else:
                    # 弧度制：直接使用
                    expression = expression.replace('sin', 'math.sin')
                    expression = expression.replace('cos', 'math.cos')
                    expression = expression.replace('tan', 'math.tan')
                    expression = expression.replace('asin', 'math.asin')
                    expression = expression.replace('acos', 'math.acos')
                    expression = expression.replace('atan', 'math.atan')
                
                # 处理其他函数
                expression = expression.replace('lg', 'math.log10')
                expression = expression.replace('ln', 'math.log')
                expression = expression.replace('√x', 'math.sqrt')
                expression = expression.replace('x^y', '**')
                expression = expression.replace('1/x', '1/')
                expression = expression.replace('x²', '**2')
                
                # 处理阶乘
                if 'x!' in expression:
                    # 简单的阶乘处理
                    expression = expression.replace('x!', '')
                    try:
                        num = float(expression)
                        result = math.factorial(int(num))
                    except:
                        result = "错误"
                else:
                    result = eval(expression)
                
                self.calc_display.setText(str(result))
                
                # 添加到历史记录
                history_entry = f"{current} = {result}\n"
                self.calc_history.append(history_entry)
                self.update_history_display()
                
                # 设置标志，表示下次输入应该开始新的计算
                self.new_input_required = True
                
            except Exception as e:
                self.calc_display.setText("错误")
                self.new_input_required = True
        elif text == '±':
            if current and current != "0":
                if current[0] == '-':
                    self.calc_display.setText(current[1:])
                else:
                    self.calc_display.setText('-' + current)
        elif text == '%':
            try:
                result = float(current) / 100
                self.calc_display.setText(str(result))
                self.new_input_required = True
            except:
                pass
        elif text in ['π', 'e']:
            # 如果需要新输入，先清空显示
            if self.new_input_required or current == "0" or current == "错误":
                self.calc_display.setText("")
                self.new_input_required = False
            if text == 'π':
                self.calc_display.setText(current + 'π')
            else:
                self.calc_display.setText(current + 'e')
        elif text in ['sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'lg', 'ln', '√x', 'x^y', '1/x', 'x!', 'x²']:
            # 如果需要新输入，先清空显示
            if self.new_input_required or current == "0" or current == "错误":
                self.calc_display.setText("")
                self.new_input_required = False
            self.calc_display.setText(current + text)
        else:
            # 数字和小数点处理
            if self.new_input_required or current == "0" or current == "错误":
                self.calc_display.setText(text)
                self.new_input_required = False
            else:
                self.calc_display.setText(current + text)
    
    def update_button_labels(self):
        """更新按钮标签（第二功能）"""
        # 这里可以添加第二功能切换的按钮标签更新
        # 例如：sin -> asin, cos -> acos, 等等
        pass
    
    def update_history_display(self):
        """更新历史记录显示"""
        self.history_text.clear()
        for entry in self.calc_history[-20:]:
            self.history_text.append(entry)
    
    def clear_history(self):
        """清空历史记录"""
        self.calc_history.clear()
        self.history_text.clear()
    
    def copy_history(self):
        """复制历史记录到剪贴板"""
        history_text = self.history_text.toPlainText().strip()
        if history_text:
            QApplication.clipboard().setText(history_text)
            QMessageBox.information(self, "成功", "历史记录已复制到剪贴板")