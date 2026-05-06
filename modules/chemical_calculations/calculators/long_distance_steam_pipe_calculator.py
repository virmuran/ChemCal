from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QLabel, QLineEdit, QPushButton, QComboBox,
                              QFormLayout, QTextEdit, QGridLayout, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math
import os
import importlib.util

# IAPWS-IF97 工业标准蒸汽物性（动态导入，避免 relative import 失败）
try:
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _parent_dir = os.path.dirname(_current_dir)
    _spec = importlib.util.spec_from_file_location(
        "steam_iapws",
        os.path.join(_parent_dir, "steam_iapws.py")
    )
    _steam_iapws = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_steam_iapws)

    iapws_steam = _steam_iapws.steam_properties
    iapws_mu = _steam_iapws.viscosity
    iapws_k = _steam_iapws.thermal_conductivity
except Exception as e:
    print(f"警告: 无法加载 IAPWS-IF97 模块: {e}")
    iapws_steam = iapws_mu = iapws_k = None


class LongDistanceSteamPipeCalculator(QWidget):
    """长输蒸汽管道温降计算器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置长输蒸汽管道温降计算界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("长输蒸汽管道温降计算")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # 说明文本
        desc_label = QLabel("计算长距离蒸汽管道的温度降、压力损失和热损失")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #7f8c8d; margin: 5px;")
        main_layout.addWidget(desc_label)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # 蒸汽参数组
        steam_group = QGroupBox("蒸汽参数")
        steam_layout = QGridLayout(steam_group)
        
        self.steam_type = QComboBox()
        self.steam_type.addItems(["饱和蒸汽", "过热蒸汽"])
        
        self.flow_rate_input = QLineEdit()
        self.flow_rate_input.setPlaceholderText("例如：10")
        self.flow_rate_input.setValidator(QDoubleValidator(0.1, 1000, 2))
        
        self.flow_rate_unit = QComboBox()
        self.flow_rate_unit.addItems(["t/h", "kg/s"])
        
        self.inlet_temp_input = QLineEdit()
        self.inlet_temp_input.setPlaceholderText("例如：200")
        self.inlet_temp_input.setValidator(QDoubleValidator(100, 600, 1))
        
        self.inlet_pressure_input = QLineEdit()
        self.inlet_pressure_input.setPlaceholderText("例如：1.0")
        self.inlet_pressure_input.setValidator(QDoubleValidator(0.1, 10, 2))
        
        self.pressure_unit = QComboBox()
        self.pressure_unit.addItems(["MPa", "bar"])
        
        steam_layout.addWidget(QLabel("蒸汽类型:"), 0, 0)
        steam_layout.addWidget(self.steam_type, 0, 1)
        steam_layout.addWidget(QLabel(""), 0, 2)  # 占位
        
        steam_layout.addWidget(QLabel("流量:"), 0, 3)
        steam_layout.addWidget(self.flow_rate_input, 0, 4)
        steam_layout.addWidget(self.flow_rate_unit, 0, 5)
        
        steam_layout.addWidget(QLabel("入口温度:"), 1, 0)
        steam_layout.addWidget(self.inlet_temp_input, 1, 1)
        steam_layout.addWidget(QLabel("°C"), 1, 2)
        
        steam_layout.addWidget(QLabel("入口压力:"), 1, 3)
        steam_layout.addWidget(self.inlet_pressure_input, 1, 4)
        steam_layout.addWidget(self.pressure_unit, 1, 5)
        
        scroll_layout.addWidget(steam_group)
        
        # 管道参数组
        pipe_group = QGroupBox("管道参数")
        pipe_layout = QGridLayout(pipe_group)
        
        self.pipe_length_input = QLineEdit()
        self.pipe_length_input.setPlaceholderText("例如：1000")
        self.pipe_length_input.setValidator(QDoubleValidator(10, 50000, 0))
        
        self.pipe_diameter_input = QLineEdit()
        self.pipe_diameter_input.setPlaceholderText("例如：200")
        self.pipe_diameter_input.setValidator(QDoubleValidator(10, 2000, 1))
        
        self.pipe_material = QComboBox()
        self.pipe_material.addItems(["碳钢", "不锈钢", "铜"])
        
        self.roughness_input = QLineEdit()
        self.roughness_input.setText("0.2")
        self.roughness_input.setValidator(QDoubleValidator(0.01, 5, 3))
        
        pipe_layout.addWidget(QLabel("管道长度:"), 0, 0)
        pipe_layout.addWidget(self.pipe_length_input, 0, 1)
        pipe_layout.addWidget(QLabel("m"), 0, 2)
        
        pipe_layout.addWidget(QLabel("管道内径:"), 0, 3)
        pipe_layout.addWidget(self.pipe_diameter_input, 0, 4)
        pipe_layout.addWidget(QLabel("mm"), 0, 5)
        
        pipe_layout.addWidget(QLabel("管道材料:"), 1, 0)
        pipe_layout.addWidget(self.pipe_material, 1, 1)
        pipe_layout.addWidget(QLabel(""), 1, 2)
        
        pipe_layout.addWidget(QLabel("粗糙度:"), 1, 3)
        pipe_layout.addWidget(self.roughness_input, 1, 4)
        pipe_layout.addWidget(QLabel("mm"), 1, 5)
        
        scroll_layout.addWidget(pipe_group)
        
        # 保温参数组
        insulation_group = QGroupBox("保温参数")
        insulation_layout = QGridLayout(insulation_group)
        
        self.insulation_thickness_input = QLineEdit()
        self.insulation_thickness_input.setPlaceholderText("例如：50")
        self.insulation_thickness_input.setValidator(QDoubleValidator(0, 500, 1))
        
        self.insulation_material = QComboBox()
        self.insulation_material.addItems(["岩棉", "玻璃棉", "硅酸铝", "聚氨酯"])
        
        self.insulation_conductivity_input = QLineEdit()
        self.insulation_conductivity_input.setText("0.04")
        self.insulation_conductivity_input.setValidator(QDoubleValidator(0.01, 1, 3))
        
        self.ambient_temp_input = QLineEdit()
        self.ambient_temp_input.setText("20")
        self.ambient_temp_input.setValidator(QDoubleValidator(-50, 50, 1))
        
        insulation_layout.addWidget(QLabel("保温厚度:"), 0, 0)
        insulation_layout.addWidget(self.insulation_thickness_input, 0, 1)
        insulation_layout.addWidget(QLabel("mm"), 0, 2)
        
        insulation_layout.addWidget(QLabel("保温材料:"), 0, 3)
        insulation_layout.addWidget(self.insulation_material, 0, 4)
        insulation_layout.addWidget(QLabel(""), 0, 5)
        
        insulation_layout.addWidget(QLabel("导热系数:"), 1, 0)
        insulation_layout.addWidget(self.insulation_conductivity_input, 1, 1)
        insulation_layout.addWidget(QLabel("W/(m·K)"), 1, 2)
        
        insulation_layout.addWidget(QLabel("环境温度:"), 1, 3)
        insulation_layout.addWidget(self.ambient_temp_input, 1, 4)
        insulation_layout.addWidget(QLabel("°C"), 1, 5)
        
        scroll_layout.addWidget(insulation_group)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        self.calc_btn = QPushButton("计算")
        self.calc_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; padding: 8px; border-radius: 4px; }"
                                  "QPushButton:hover { background-color: #2980b9; }")
        self.calc_btn.clicked.connect(self.calculate)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; padding: 8px; border-radius: 4px; }"
                                   "QPushButton:hover { background-color: #7f8c8d; }")
        self.clear_btn.clicked.connect(self.clear_inputs)
        
        button_layout.addWidget(self.calc_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        scroll_layout.addLayout(button_layout)
        
        # 结果显示
        result_group = QGroupBox("计算结果")
        result_layout = QFormLayout(result_group)
        
        self.outlet_temp_result = QLabel("--")
        self.outlet_pressure_result = QLabel("--")
        self.temp_drop_result = QLabel("--")
        self.pressure_drop_result = QLabel("--")
        self.heat_loss_result = QLabel("--")
        self.velocity_result = QLabel("--")
        self.reynolds_result = QLabel("--")
        self.flow_regime_result = QLabel("--")
        
        result_layout.addRow("出口温度:", self.outlet_temp_result)
        result_layout.addRow("出口压力:", self.outlet_pressure_result)
        result_layout.addRow("温度降:", self.temp_drop_result)
        result_layout.addRow("压力降:", self.pressure_drop_result)
        result_layout.addRow("热损失:", self.heat_loss_result)
        result_layout.addRow("蒸汽流速:", self.velocity_result)
        result_layout.addRow("雷诺数:", self.reynolds_result)
        result_layout.addRow("流动状态:", self.flow_regime_result)
        
        scroll_layout.addWidget(result_group)
        
        # 计算说明
        info_text = QTextEdit()
        info_text.setMaximumHeight(150)
        info_text.setHtml("""
        <h4>计算说明:</h4>
        <ul>
        <li>基于能量平衡和动量平衡方程计算蒸汽在长距离输送过程中的温降和压降</li>
        <li>考虑管道摩擦阻力、局部阻力和热损失的影响</li>
        <li>适用于过热蒸汽和饱和蒸汽的长距离输送计算</li>
        <li>计算结果为近似值，实际工程中建议使用专业软件进行详细计算</li>
        </ul>
        """)
        info_text.setReadOnly(True)
        scroll_layout.addWidget(info_text)
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
    def clear_inputs(self):
        """清空所有输入"""
        self.flow_rate_input.clear()
        self.inlet_temp_input.clear()
        self.inlet_pressure_input.clear()
        self.pipe_length_input.clear()
        self.pipe_diameter_input.clear()
        self.roughness_input.setText("0.2")
        self.insulation_thickness_input.clear()
        self.insulation_conductivity_input.setText("0.04")
        self.ambient_temp_input.setText("20")
        
        # 清空结果
        for label in [self.outlet_temp_result, self.outlet_pressure_result,
                     self.temp_drop_result, self.pressure_drop_result, self.heat_loss_result,
                     self.velocity_result, self.reynolds_result, self.flow_regime_result]:
            label.setText("--")
    
    def calculate(self):
        """执行长输蒸汽管道温降计算"""
        try:
            # 获取输入值
            steam_type = self.steam_type.currentText()
            
            flow_rate = float(self.flow_rate_input.text())
            flow_unit = self.flow_rate_unit.currentText()
            if flow_unit == "t/h":
                mass_flow = flow_rate * 1000 / 3600  # 转换为kg/s
            else:  # kg/s
                mass_flow = flow_rate
                
            inlet_temp = float(self.inlet_temp_input.text())
            inlet_pressure = float(self.inlet_pressure_input.text())
            pressure_unit = self.pressure_unit.currentText()
            if pressure_unit == "bar":
                inlet_pressure_mpa = inlet_pressure / 10
            else:  # MPa
                inlet_pressure_mpa = inlet_pressure
                
            pipe_length = float(self.pipe_length_input.text())
            pipe_diameter = float(self.pipe_diameter_input.text()) / 1000  # 转换为m
            roughness = float(self.roughness_input.text()) / 1000  # 转换为m
            
            insulation_thickness = float(self.insulation_thickness_input.text()) / 1000  # 转换为m
            insulation_conductivity = float(self.insulation_conductivity_input.text())
            ambient_temp = float(self.ambient_temp_input.text())
            
            # 执行计算
            results = self.calculate_steam_pipe_loss(
                steam_type, mass_flow, inlet_temp, inlet_pressure_mpa,
                pipe_length, pipe_diameter, roughness,
                insulation_thickness, insulation_conductivity, ambient_temp
            )
            
            # 显示结果
            self.display_results(results)
            
        except ValueError as e:
            self.show_error("输入参数格式错误，请检查输入值")
        except Exception as e:
            self.show_error(f"计算错误: {str(e)}")

    def _get_history_data(self):
        """提供历史记录数据"""
        steam_type = self.steam_type.currentText()
        flow_rate = float(self.flow_rate_input.text() or 0)
        flow_unit = self.flow_rate_unit.currentText()
        if flow_unit == "t/h":
            mass_flow = flow_rate * 1000 / 3600
        else:
            mass_flow = flow_rate
        inlet_temp = float(self.inlet_temp_input.text() or 0)
        inlet_pressure = float(self.inlet_pressure_input.text() or 0)
        pressure_unit = self.pressure_unit.currentText()
        inlet_pressure_mpa = inlet_pressure / 10 if pressure_unit == "bar" else inlet_pressure
        pipe_length = float(self.pipe_length_input.text() or 0)
        pipe_diameter = float(self.pipe_diameter_input.text() or 0)
        roughness = float(self.roughness_input.text() or 0)
        insulation_thickness = float(self.insulation_thickness_input.text() or 0)
        insulation_conductivity = float(self.insulation_conductivity_input.text() or 0)
        ambient_temp = float(self.ambient_temp_input.text() or 0)

        inputs = {
            "蒸汽类型": steam_type,
            "流量": flow_rate,
            "流量单位": flow_unit,
            "入口温度_C": inlet_temp,
            "入口压力": inlet_pressure,
            "压力单位": pressure_unit,
            "管道长度_m": pipe_length,
            "管道直径_mm": pipe_diameter,
            "粗糙度_mm": roughness,
            "保温厚度_mm": insulation_thickness,
            "保温导热系数_W_mK": insulation_conductivity,
            "环境温度_C": ambient_temp
        }

        outputs = {}
        try:
            results = self.calculate_steam_pipe_loss(
                steam_type, mass_flow, inlet_temp, inlet_pressure_mpa,
                pipe_length, pipe_diameter / 1000, roughness / 1000,
                insulation_thickness / 1000, insulation_conductivity, ambient_temp
            )
            outputs = {
                "出口温度_C": round(results.get('outlet_temp', 0), 1),
                "出口压力_MPa": round(results.get('outlet_pressure', 0), 3),
                "温降_C": round(results.get('temp_drop', 0), 1),
                "压降_MPa": round(results.get('pressure_drop', 0), 3),
                "总热损失_kW": round(results.get('total_heat_loss', 0), 1)
            }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def calculate_steam_pipe_loss(self, steam_type, mass_flow, inlet_temp, inlet_pressure,
                                 pipe_length, pipe_diameter, roughness,
                                 insulation_thickness, insulation_conductivity, ambient_temp):
        """计算蒸汽管道温降和压降"""
        # 蒸汽物性参数 (IAPWS-IF97 工业标准)
        def get_steam_properties(temp_c, pressure_mpa):
            try:
                props = iapws_steam(pressure_mpa, temp_c)
                density = props['rho']  # kg/m³
                specific_heat = props['cp']  # kJ/(kg·K)
                # 动力粘度 [Pa·s]
                viscosity = iapws_mu(pressure_mpa, temp_c)
                # 导热系数 [W/(m·K)]
                thermal_cond = iapws_k(pressure_mpa, temp_c)
                return density, viscosity, specific_heat, thermal_cond
            except Exception:
                # 降级处理
                density = pressure_mpa * 100 / (0.4615 * (temp_c + 273.15))
                return density, 1.2e-5, 2.0, 0.03
        
        # 初始参数
        current_temp = inlet_temp
        current_pressure = inlet_pressure
        
        # 分段计算 (将管道分成若干段)
        num_segments = 10
        segment_length = pipe_length / num_segments
        
        total_heat_loss = 0
        
        for i in range(num_segments):
            # 获取当前段的蒸汽物性
            density, viscosity, specific_heat, steam_conductivity = get_steam_properties(
                current_temp, current_pressure
            )
            
            # 计算流速
            cross_area = math.pi * (pipe_diameter / 2) ** 2
            velocity = mass_flow / (density * cross_area)
            
            # 计算雷诺数
            reynolds = density * velocity * pipe_diameter / viscosity
            
            # 计算摩擦系数 (Churchill公式)
            f = self.calculate_friction_factor(reynolds, pipe_diameter, roughness)
            
            # 计算压力降 (Darcy-Weisbach公式)
            pressure_drop_segment = f * (segment_length / pipe_diameter) * (density * velocity ** 2) / 2
            pressure_drop_mpa = pressure_drop_segment / 1e6
            
            # 更新压力
            current_pressure -= pressure_drop_mpa
            
            # 计算热损失
            if insulation_thickness > 0:
                # 有保温层
                inner_radius = pipe_diameter / 2
                outer_radius = inner_radius + insulation_thickness
                
                # 热阻计算
                r_pipe = math.log((inner_radius + 0.001) / inner_radius) / (2 * math.pi * 50 * segment_length)  # 管道热阻
                r_insulation = math.log(outer_radius / inner_radius) / (2 * math.pi * insulation_conductivity * segment_length)
                r_total = r_pipe + r_insulation
                
                heat_loss_segment = (current_temp - ambient_temp) / r_total  # W
            else:
                # 无保温层
                heat_loss_segment = 2 * math.pi * (pipe_diameter / 2) * segment_length * 10 * (current_temp - ambient_temp)  # 估算
            
            total_heat_loss += heat_loss_segment
            
            # 计算温度降
            temp_drop_segment = heat_loss_segment / (mass_flow * specific_heat * 1000)  # kJ/s to °C
            current_temp -= temp_drop_segment
        
        # 最终结果
        outlet_temp = current_temp
        outlet_pressure = current_pressure
        temp_drop = inlet_temp - outlet_temp
        pressure_drop = inlet_pressure - outlet_pressure
        
        # 计算最终段的流速和雷诺数
        density_out, viscosity_out, _, _ = get_steam_properties(outlet_temp, outlet_pressure)
        velocity_out = mass_flow / (density_out * cross_area)
        reynolds_out = density_out * velocity_out * pipe_diameter / viscosity_out
        
        # 判断流动状态
        if reynolds_out < 2300:
            flow_regime = "层流"
        elif reynolds_out < 4000:
            flow_regime = "过渡流"
        else:
            flow_regime = "湍流"
        
        return {
            'outlet_temp': outlet_temp,
            'outlet_pressure': outlet_pressure,
            'temp_drop': temp_drop,
            'pressure_drop': pressure_drop,
            'heat_loss': total_heat_loss / 1000,  # 转换为kW
            'velocity': velocity_out,
            'reynolds': reynolds_out,
            'flow_regime': flow_regime
        }
    
    def calculate_friction_factor(self, reynolds, diameter, roughness):
        """计算摩擦系数"""
        if reynolds < 2300:
            # 层流
            return 64 / reynolds
        else:
            # 湍流 (Colebrook-White方程简化)
            relative_roughness = roughness / diameter
            # 使用Swamee-Jain近似公式
            f = 0.25 / (math.log10(relative_roughness / 3.7 + 5.74 / reynolds ** 0.9)) ** 2
            return f
    
    def display_results(self, results):
        """显示计算结果"""
        self.outlet_temp_result.setText(f"{results['outlet_temp']:.1f} °C")
        self.outlet_pressure_result.setText(f"{results['outlet_pressure']:.3f} MPa")
        self.temp_drop_result.setText(f"{results['temp_drop']:.1f} °C")
        self.pressure_drop_result.setText(f"{results['pressure_drop']:.3f} MPa")
        self.heat_loss_result.setText(f"{results['heat_loss']:.1f} kW")
        self.velocity_result.setText(f"{results['velocity']:.1f} m/s")
        self.reynolds_result.setText(f"{results['reynolds']:.0f}")
        self.flow_regime_result.setText(results['flow_regime'])
    
    def show_error(self, message):
        """显示错误信息"""
        for label in [self.outlet_temp_result, self.outlet_pressure_result,
                     self.temp_drop_result, self.pressure_drop_result, self.heat_loss_result,
                     self.velocity_result, self.reynolds_result, self.flow_regime_result]:
            label.setText("计算错误")
        
        # 在实际应用中，这里可以显示一个错误对话框
        print(f"错误: {message}")


if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = LongDistanceSteamPipeCalculator()
    calculator.resize(700, 800)
    calculator.show()
    
    sys.exit(app.exec())