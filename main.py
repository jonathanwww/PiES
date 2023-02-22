import sys
from PyQt6.QtWidgets import QApplication

from logic.equationsystem import EquationSystem
from ui.gui import Editor


def main():
    eq_sys = EquationSystem()
    app = QApplication(sys.argv)
    ex = Editor(eq_sys)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
