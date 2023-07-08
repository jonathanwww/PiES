from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt6 import QtCore


class StatusBarWidget(QWidget):
    def __init__(self, equation_system, solver_interface, parent=None):
        super().__init__(parent)
        self.equation_system = equation_system
        self.solver_interface = solver_interface

        # refresh on eq sys update
        self.equation_system.data_changed.connect(self.update_widget)
        
        # shows the status during solving
        self.solver_interface.solve_status.connect(self.update_solving_status)
        
        # layout
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # Status for solving
        self.status_label = QLabel()
        self.layout.addWidget(self.status_label)

        self.layout.addStretch(1)

        # Equation system stats
        self.data_label = QLabel()
        self.layout.addWidget(self.data_label)
    
    @QtCore.pyqtSlot()
    def update_widget(self):
        # Update display based on new model data
        # todo: finish ready status. needs to check for compile as well
        status = 'Ready' if self.equation_system.valid else 'Not ready'
        self.status_label.setText(status)
        
        num_eq = len(self.equation_system.equations)
        num_var = len(self.equation_system.variables)
        num_grid = len(self.equation_system.grid.variables)
        num_param = len(self.equation_system.parameter_variables)
        num_norm = max(num_var - num_grid - num_param, 0)
        self.data_label.setText(
            f"Equations: {num_eq} - Variables: {num_var} ({num_norm} norm {num_param} param {num_grid} grid)")
    
    def update_solving_status(self, message: str):
        # Updates status bar with solving status: run 1/n, block ..
        self.status_label.setText(message)
