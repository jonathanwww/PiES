import re
from PyQt6.QtCore import QThread, pyqtSignal


class SolverThread(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, solver, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.solver = solver

    def run(self):
        # Call the solver's solve method.
        self.solver.solve()


def clean_text(text):
    # remove comments
    text = re.split('#', text)[0]
    # Remove spaces and line shift
    text = text.replace(' ', '')
    text = text.replace('\n', '')
    return text
