import sys
from PyQt6.QtWidgets import QApplication

from logic.equationsystem import EquationSystem
from ui.window import Window


def main():
    eq_sys = EquationSystem()
    app = QApplication(sys.argv)
    ex = Window(eq_sys)
    ex.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
