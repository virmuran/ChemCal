import os, sys, importlib.util
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:/Users/Administrator/Desktop/ChemCal")
sys.path.insert(0, r"C:/Users/Administrator/Desktop/ChemCal/modules/chemical_calculations/calculators")
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
spec = importlib.util.spec_from_file_location("spc", r"C:/Users/Administrator/Desktop/ChemCal/modules/chemical_calculations/calculators/steam_pipe_calculator.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
w = m.蒸汽管径流量()
w.pressure_input.setText("1.0"); w.temperature_input.setText("200")
w.on_mode_changed("根据管径计算流量")
w.diameter_input.setText("100")
w.calculate_steam_pipe()
print(repr(w.result_text.toPlainText()[:150]))
