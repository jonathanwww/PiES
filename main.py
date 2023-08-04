import sys
from PyQt6.QtWidgets import QApplication
from app import MainApp

if __name__ == '__main__':
    app = QApplication(sys.argv)
    PiES = MainApp()
    PiES.run()
    sys.exit(app.exec())
