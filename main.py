import sys
from PyQt6.QtWidgets import QApplication
from model.equationsystem import EquationSystem
from ui.window import MainWindow
from controller.controller import MainController


def main():
    app = QApplication(sys.argv)
    
    model = EquationSystem()
    view = MainWindow()
    controller = MainController(model, view)
    
    view.resize(1300, 800)
    view.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
