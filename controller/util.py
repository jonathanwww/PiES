import types
import pint
import re
from PyQt6.QtCore import QThread, pyqtSignal
from model.util import Grid


def clean_text(text):
    # remove comments
    text = re.split('#', text)[0]
    # Remove spaces
    text = text.replace(' ', '')
    return text


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


def check_function_units(functions_dict, ureg):
    errors = []
    for name, unit in functions_dict.items():
        try:
            ureg[unit]
        except pint.UndefinedUnitError as e:
            message = f"Cannot convert {unit} to a unit"
            errors.append(message)
    return errors


def get_function_units(namespace):
    func_units = {}
    for name, value in namespace.items():
        if isinstance(value, types.FunctionType):
            if hasattr(value, 'unit'):
                unit_value = getattr(value, 'unit')
                func_units[name] = unit_value
    return func_units


def check_grid(grid, eqsys):
    errors = []
    grid_valid = eqsys.validate_grid(grid)
    if not grid_valid:
        message = "Grid does not match variables in equation system or is overlapping parameter variable"
        errors.append(message)
    return errors


def get_grid(namespace):
    # Find the Grid instance within the namespace
    if any(isinstance(obj, Grid) for obj in namespace.values()):
        for obj in namespace.values():
            if isinstance(obj, Grid):
                grid = obj
                return grid
    else:
        return None
