import sys
from PySide6.QtWidgets import QApplication, QMainWindow


app = QApplication(sys.argv)

window = QMainWindow()
window.setWindowTitle("System Resource Monitor")
window.resize(1200, 700)

window.show()

sys.exit(app.exec())