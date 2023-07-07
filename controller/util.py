from PyQt6.QtCore import QThread, pyqtSignal


class SolverThread(QThread):
    # Define a new signal that can deliver strings.
    update_signal = pyqtSignal(str)

    def __init__(self, solver, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.solver = solver

    def run(self):
        """Long-running task."""
        # Call the solver's solve method.
        self.solver.solve()
