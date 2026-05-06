from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                              QLabel, QLineEdit, QPushButton, QComboBox, 
                              QFormLayout, QTextEdit, QGridLayout, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
import math


class FanPowerCalculator(QWidget):
    """风机功率计算器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置风机功率计算界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("风机功率计算")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # 说明文本
        desc_label = QLabel("计算风机的轴功率、电机功率、能耗和运行成本")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #7f8c8d; margin: 5px;")
        main_layout.addWidget(desc_label)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # 风机参数组
        fan_group = QGroupBox("风机参数")
        fan_layout = QGridLayout(fan_group)
        
        self.fan_type = QComboBox()
        self.fan_type.addItems(["离心风机", "轴流风机", "混流风机", "罗茨风机"])
        
        self.flow_rate_input = QLineEdit()
        self.flow_rate_input.setPlaceholderText("例如：10000")
        self.flow_rate_input.setValidator(QDoubleValidator(1, 1000000, 1))
        
        self.flow_rate_unit = QComboBox()
        self.flow_rate_unit.addItems(["m³/h", "m³/min", "m³/s"])
        
        self.pressure_input = QLineEdit()
        self.pressure_input.setPlaceholderText("例如：1000")
        self.pressure_input.setValidator(QDoubleValidator(10, 50000, 1))
        
        self.pressure_unit = QComboBox()
        self.pressure_unit.addItems(["Pa", "kPa", "mmH₂O"])

        self.temperature_input = QLineEdit()
        self.temperature_input.setText("20")
        self.temperature_input.setValidator(QDoubleValidator(-50, 200, 1))

        self.altitude_input = QLineEdit()
        self.altitude_input.setText("0")
        self.altitude_input.setValidator(QDoubleValidator(-100, 5000, 0))
        
        fan_layout.addWidget(QLabel("风机类型:"), 0, 0)
        fan_layout.addWidget(self.fan_type, 0, 1)
        fan_layout.addWidget(QLabel(""), 0, 2)  # 占位
        
        fan_layout.addWidget(QLabel("风量:"), 0, 3)
        fan_layout.addWidget(self.flow_rate_input, 0, 4)
        fan_layout.addWidget(self.flow_rate_unit, 0, 5)
        
        fan_layout.addWidget(QLabel("风压:"), 1, 0)
        fan_layout.addWidget(self.pressure_input, 1, 1)
        fan_layout.addWidget(self.pressure_unit, 1, 2)
        
        fan_layout.addWidget(QLabel("介质温度:"), 1, 3)
        fan_layout.addWidget(self.temperature_input, 1, 4)
        fan_layout.addWidget(QLabel("°C"), 1, 5)
        
        fan_layout.addWidget(QLabel("海拔高度:"), 2, 0)
        fan_layout.addWidget(self.altitude_input, 2, 1)
        fan_layout.addWidget(QLabel("m"), 2, 2)
        
        scroll_layout.addWidget(fan_group)
        
        # 效率参数组
        efficiency_group = QGroupBox("效率参数")
        efficiency_layout = QGridLayout(efficiency_group)
        
        self.fan_efficiency_input = QLineEdit()
        self.fan_efficiency_input.setPlaceholderText("例如：75")
        self.fan_efficiency_input.setValidator(QDoubleValidator(10, 95, 1))
        
        self.motor_efficiency_input = QLineEdit()
        self.motor_efficiency_input.setPlaceholderText("例如：92")
        self.motor_efficiency_input.setValidator(QDoubleValidator(50, 98, 1))
        
        self.transmission_efficiency_input = QLineEdit()
        self.transmission_efficiency_input.setText("98")
        self.transmission_efficiency_input.setValidator(QDoubleValidator(80, 100, 1))
        
        self.transmission_type = QComboBox()
        self.transmission_type.addItems(["直联", "皮带传动", "联轴器"])
        
        efficiency_layout.addWidget(QLabel("风机效率:"), 0, 0)
        efficiency_layout.addWidget(self.fan_efficiency_input, 0, 1)
        efficiency_layout.addWidget(QLabel("%"), 0, 2)
        
        efficiency_layout.addWidget(QLabel("电机效率:"), 0, 3)
        efficiency_layout.addWidget(self.motor_efficiency_input, 0, 4)
        efficiency_layout.addWidget(QLabel("%"), 0, 5)
        
        efficiency_layout.addWidget(QLabel("传动效率:"), 1, 0)
        efficiency_layout.addWidget(self.transmission_efficiency_input, 1, 1)
        efficiency_layout.addWidget(QLabel("%"), 1, 2)
        
        efficiency_layout.addWidget(QLabel("传动方式:"), 1, 3)
        efficiency_layout.addWidget(self.transmission_type, 1, 4)
        efficiency_layout.addWidget(QLabel(""), 1, 5)
        
        scroll_layout.addWidget(efficiency_group)
        
        # 运行参数组
        operation_group = QGroupBox("运行参数")
        operation_layout = QGridLayout(operation_group)
        
        self.operation_hours_input = QLineEdit()
        self.operation_hours_input.setPlaceholderText("例如：24")
        self.operation_hours_input.setValidator(QDoubleValidator(1, 8760, 1))
        
        self.days_per_year_input = QLineEdit()
        self.days_per_year_input.setPlaceholderText("例如：365")
        self.days_per_year_input.setValidator(QDoubleValidator(1, 365, 0))
        
        self.electricity_price_input = QLineEdit()
        self.electricity_price_input.setPlaceholderText("例如：0.8")
        self.electricity_price_input.setValidator(QDoubleValidator(0.1, 10, 3))
        
        operation_layout.addWidget(QLabel("日运行时间:"), 0, 0)
        operation_layout.addWidget(self.operation_hours_input, 0, 1)
        operation_layout.addWidget(QLabel("小时/天"), 0, 2)
        
        operation_layout.addWidget(QLabel("年运行天数:"), 0, 3)
        operation_layout.addWidget(self.days_per_year_input, 0, 4)
        operation_layout.addWidget(QLabel("天/年"), 0, 5)
        
        operation_layout.addWidget(QLabel("电价:"), 1, 0)
        operation_layout.addWidget(self.electricity_price_input, 1, 1)
        operation_layout.addWidget(QLabel("元/kWh"), 1, 2)
        
        scroll_layout.addWidget(operation_group)
        
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
        
        # 功率计算结果
        power_result_group = QGroupBox("功率计算结果")
        power_result_layout = QFormLayout(power_result_group)
        
        self.shaft_power_result = QLabel("--")
        self.motor_power_result = QLabel("--")
        self.selected_motor_result = QLabel("--")
        self.specific_power_result = QLabel("--")
        self.air_density_result = QLabel("--")
        
        power_result_layout.addRow("轴功率:", self.shaft_power_result)
        power_result_layout.addRow("电机功率:", self.motor_power_result)
        power_result_layout.addRow("建议电机规格:", self.selected_motor_result)
        power_result_layout.addRow("比功率:", self.specific_power_result)
        power_result_layout.addRow("空气密度:", self.air_density_result)
        
        scroll_layout.addWidget(power_result_group)
        
        # 能耗计算结果
        energy_result_group = QGroupBox("能耗与成本")
        energy_result_layout = QFormLayout(energy_result_group)
        
        self.hourly_energy_result = QLabel("--")
        self.daily_energy_result = QLabel("--")
        self.yearly_energy_result = QLabel("--")
        self.hourly_cost_result = QLabel("--")
        self.daily_cost_result = QLabel("--")
        self.yearly_cost_result = QLabel("--")
        
        energy_result_layout.addRow("小时耗电量:", self.hourly_energy_result)
        energy_result_layout.addRow("日耗电量:", self.daily_energy_result)
        energy_result_layout.addRow("年耗电量:", self.yearly_energy_result)
        energy_result_layout.addRow("小时电费:", self.hourly_cost_result)
        energy_result_layout.addRow("日电费:", self.daily_cost_result)
        energy_result_layout.addRow("年电费:", self.yearly_cost_result)
        
        scroll_layout.addWidget(energy_result_group)
        
        # 计算说明
        info_text = QTextEdit()
        info_text.setMaximumHeight(150)
        info_text.setHtml("""
        <h4>计算说明:</h4>
        <ul>
        <li>轴功率 = (风量 × 风压) / (3600 × 1000 × 风机效率)</li>
        <li>电机功率 = 轴功率 / (传动效率 × 电机效率)</li>
        <li>空气密度根据温度和海拔高度进行修正</li>
        <li>标准空气密度: 1.2 kg/m³ (20°C, 海平面)</li>
        <li>建议电机规格按1.1-1.2倍安全系数选择</li>
        </ul>
        """)
        info_text.setReadOnly(True)
        scroll_layout.addWidget(info_text)
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
    def clear_inputs(self):
        """清空所有输入"""
        self.flow_rate_input.clear()
        self.pressure_input.clear()
        self.temperature_input.setText("20")
        self.altitude_input.setText("0")
        self.fan_efficiency_input.clear()
        self.motor_efficiency_input.clear()
        self.transmission_efficiency_input.setText("98")
        self.operation_hours_input.clear()
        self.days_per_year_input.clear()
        self.electricity_price_input.clear()
        
        # 清空结果
        for label in [self.shaft_power_result, self.motor_power_result, 
                     self.selected_motor_result, self.specific_power_result,
                     self.air_density_result, self.hourly_energy_result,
                     self.daily_energy_result, self.yearly_energy_result,
                     self.hourly_cost_result, self.daily_cost_result,
                     self.yearly_cost_result]:
            label.setText("--")
    
    def calculate(self):
        """执行风机功率计算"""
        try:
            # 获取输入值
            flow_rate = float(self.flow_rate_input.text())
            flow_unit = self.flow_rate_unit.currentText()
            # 转换为m³/h
            if flow_unit == "m³/min":
                flow_rate_m3h = flow_rate * 60
            elif flow_unit == "m³/s":
                flow_rate_m3h = flow_rate * 3600
            else:  # m³/h
                flow_rate_m3h = flow_rate
                
            pressure = float(self.pressure_input.text())
            pressure_unit = self.pressure_unit.currentText()
            # 转换为Pa
            if pressure_unit == "kPa":
                pressure_pa = pressure * 1000
            elif pressure_unit == "mmH₂O":
                pressure_pa = pressure * 9.80665
            else:  # Pa
                pressure_pa = pressure
                
            temperature = float(self.temperature_input.text())
            altitude = float(self.altitude_input.text())
            
            fan_efficiency = float(self.fan_efficiency_input.text()) / 100
            motor_efficiency = float(self.motor_efficiency_input.text()) / 100
            transmission_efficiency = float(self.transmission_efficiency_input.text()) / 100
            
            operation_hours = float(self.operation_hours_input.text())
            days_per_year = float(self.days_per_year_input.text())
            electricity_price = float(self.electricity_price_input.text())
            
            # 执行计算
            results = self.calculate_fan_power(
                flow_rate_m3h, pressure_pa, temperature, altitude,
                fan_efficiency, motor_efficiency, transmission_efficiency,
                operation_hours, days_per_year, electricity_price
            )
            
            # 显示结果
            self.display_results(results)
            
        except ValueError as e:
            self.show_error("输入参数格式错误，请检查输入值")
        except Exception as e:
            self.show_error(f"计算错误: {str(e)}")

    def _get_history_data(self):
        """提供历史记录数据"""
        flow_rate = float(self.flow_rate_input.text() or 0)
        flow_unit = self.flow_rate_unit.currentText()
        if flow_unit == "m³/min":
            flow_rate_m3h = flow_rate * 60
        elif flow_unit == "m³/s":
            flow_rate_m3h = flow_rate * 3600
        else:
            flow_rate_m3h = flow_rate

        pressure = float(self.pressure_input.text() or 0)
        pressure_unit = self.pressure_unit.currentText()
        if pressure_unit == "kPa":
            pressure_pa = pressure * 1000
        elif pressure_unit == "mmH₂O":
            pressure_pa = pressure * 9.80665
        else:
            pressure_pa = pressure

        temperature = float(self.temperature_input.text() or 0)
        altitude = float(self.altitude_input.text() or 0)
        fan_efficiency = float(self.fan_efficiency_input.text() or 0) / 100
        motor_efficiency = float(self.motor_efficiency_input.text() or 0) / 100
        transmission_efficiency = float(self.transmission_efficiency_input.text() or 0) / 100
        operation_hours = float(self.operation_hours_input.text() or 0)
        days_per_year = float(self.days_per_year_input.text() or 0)
        electricity_price = float(self.electricity_price_input.text() or 0)

        inputs = {
            f"流量_{flow_unit}": flow_rate,
            f"全压_{pressure_unit}": pressure,
            "温度_C": temperature,
            "海拔_m": altitude,
            "风机效率_%": fan_efficiency * 100,
            "电机效率_%": motor_efficiency * 100,
            "传动效率_%": transmission_efficiency * 100,
            "年运行小时_h": operation_hours * days_per_year if days_per_year else 0,
            "电费_元_kWh": electricity_price
        }

        outputs = {}
        try:
            # 空气密度计算：以标准状态(0°C, 101.325kPa)为基准
            T_kelvin = temperature + 273.15
            rho_temp = 1.293 * (273.15 / T_kelvin)  # 温度修正
            # 海拔修正：国际标准大气(ISA)幂律公式
            rho_altitude = (1 - altitude / 44300) ** 5.255 if altitude < 44300 else 0.01
            rho = rho_temp * rho_altitude
            flow_m3s = flow_rate_m3h / 3600
            shaft_power = flow_m3s * pressure_pa / fan_efficiency if fan_efficiency > 0 else 0
            motor_power = shaft_power / motor_efficiency if motor_efficiency > 0 else 0
            total_efficiency = fan_efficiency * motor_efficiency * transmission_efficiency
            power_consumption = flow_m3s * pressure_pa / total_efficiency if total_efficiency > 0 else 0
            annual_energy = power_consumption * operation_hours * days_per_year / 1000 if days_per_year else 0
            annual_cost = annual_energy * electricity_price

            outputs = {
                "实际空气密度_kg_m3": round(rho, 3),
                "轴功率_kW": round(shaft_power / 1000, 2),
                "电机功率_kW": round(motor_power / 1000, 2),
                "年耗电量_kWh": round(annual_energy, 0),
                "年电费_万元": round(annual_cost / 10000, 2)
            }
        except Exception as e:
            outputs["计算错误"] = str(e)

        return {"inputs": inputs, "outputs": outputs}

    def calculate_fan_power(self, flow_rate, pressure, temperature, altitude,
                           fan_efficiency, motor_efficiency, transmission_efficiency,
                           operation_hours, days_per_year, electricity_price):
        """计算风机功率和能耗"""
        # 计算空气密度修正
        # 标准空气密度 (0°C, 101.325kPa): 1.293 kg/m³

        # 温度修正
        T_kelvin = temperature + 273.15
        rho_temp = 1.293 * (273.15 / T_kelvin)

        # 海拔修正：国际标准大气(ISA)幂律公式
        rho_altitude = (1 - altitude / 44300) ** 5.255 if altitude < 44300 else 0.01
        rho_actual = rho_temp * rho_altitude
        
        # 计算轴功率 (kW)
        # P_shaft = (Q × p) / (3600 × 1000 × η_fan)
        shaft_power = (flow_rate * pressure) / (3600 * 1000 * fan_efficiency)
        
        # 计算电机功率 (kW)
        motor_power = shaft_power / (transmission_efficiency * motor_efficiency)
        
        # 选择标准电机规格
        standard_motors = [0.75, 1.1, 1.5, 2.2, 3, 4, 5.5, 7.5, 11, 15, 18.5, 22, 
                          30, 37, 45, 55, 75, 90, 110, 132, 160, 200, 250, 315, 355]
        selected_motor = min([m for m in standard_motors if m >= motor_power * 1.15], 
                            default=standard_motors[-1])
        
        # 计算比功率 (kW/(m³/s))
        flow_rate_m3s = flow_rate / 3600
        specific_power = motor_power / flow_rate_m3s
        
        # 计算能耗
        hourly_energy = motor_power  # kWh
        daily_energy = hourly_energy * operation_hours
        yearly_energy = daily_energy * days_per_year
        
        # 计算电费
        hourly_cost = hourly_energy * electricity_price
        daily_cost = daily_energy * electricity_price
        yearly_cost = yearly_energy * electricity_price
        
        return {
            'shaft_power': shaft_power,
            'motor_power': motor_power,
            'selected_motor': selected_motor,
            'specific_power': specific_power,
            'air_density': rho_actual,
            'hourly_energy': hourly_energy,
            'daily_energy': daily_energy,
            'yearly_energy': yearly_energy,
            'hourly_cost': hourly_cost,
            'daily_cost': daily_cost,
            'yearly_cost': yearly_cost
        }
    
    def display_results(self, results):
        """显示计算结果"""
        self.shaft_power_result.setText(f"{results['shaft_power']:.2f} kW")
        self.motor_power_result.setText(f"{results['motor_power']:.2f} kW")
        self.selected_motor_result.setText(f"{results['selected_motor']} kW")
        self.specific_power_result.setText(f"{results['specific_power']:.2f} kW/(m³/s)")
        self.air_density_result.setText(f"{results['air_density']:.3f} kg/m³")
        
        self.hourly_energy_result.setText(f"{results['hourly_energy']:.2f} kWh")
        self.daily_energy_result.setText(f"{results['daily_energy']:.2f} kWh")
        self.yearly_energy_result.setText(f"{results['yearly_energy']:.0f} kWh")
        
        self.hourly_cost_result.setText(f"{results['hourly_cost']:.2f} 元")
        self.daily_cost_result.setText(f"{results['daily_cost']:.2f} 元")
        self.yearly_cost_result.setText(f"{results['yearly_cost']:.0f} 元")
    
    def show_error(self, message):
        """显示错误信息"""
        for label in [self.shaft_power_result, self.motor_power_result, 
                     self.selected_motor_result, self.specific_power_result,
                     self.air_density_result, self.hourly_energy_result,
                     self.daily_energy_result, self.yearly_energy_result,
                     self.hourly_cost_result, self.daily_cost_result,
                     self.yearly_cost_result]:
            label.setText("计算错误")
        
        # 在实际应用中，这里可以显示一个错误对话框
        print(f"错误: {message}")


if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    calculator = FanPowerCalculator()
    calculator.resize(700, 800)
    calculator.show()
    
    sys.exit(app.exec())