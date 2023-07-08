from typing import Any
from enum import Enum
from PyQt6.QtWidgets import QWidget, QTableView, QVBoxLayout, QLineEdit, QPushButton, QComboBox, QCheckBox
from PyQt6.QtCore import QSortFilterProxyModel, QAbstractTableModel, Qt, pyqtSignal, QRegularExpression
from PyQt6.QtGui import QColor
from pint import UndefinedUnitError


# map columns to variable attribute names
class VariableAttributes(Enum):
    name = 0
    starting_guess = 1
    lower_bound = 2
    upper_bound = 3
    unit = 4


class VariableTableWidget(QWidget):
    def __init__(self, equation_system, ureg, parent=None):
        super().__init__(parent)
        self.ureg = ureg

        self.equation_system = equation_system
        
        # update table on changes in eq sys
        self.equation_system.data_changed.connect(self.updateData)
        
        self._create_widgets()
        self._setup_layout()
        
        # on change attribute send to variable manager
        self.table_model.attribute_update.connect(self.equation_system.variable_manager.update_variable)
        
        # send error messages from table to view
        self.table_model.error.connect(self.parent().show_error_message)

    def _create_widgets(self):
        self.table_model = VariableTable(self.ureg, self)
        self.proxy_model = VariableFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.variables_table = QTableView()
        self.variables_table.setModel(self.proxy_model)
        self.variables_table.setSortingEnabled(True)
        self.variables_table.setSelectionMode(QTableView.SelectionMode.MultiSelection)
        self.variables_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search by variable name..")
        self.search_bar.textChanged.connect(self.proxy_model.setFilterString)

        self.batch_update_input = QLineEdit()
        self.batch_update_button = QPushButton("Update Selected")
        self.column_select_combo = QComboBox()
        self.column_select_combo.addItems(["starting_guess", "lower_bound", "upper_bound", "unit"])
        self.batch_update_button.clicked.connect(self.batch_update)

        self.show_params_grid_check = QCheckBox("Show parameter/grid variables")
        self.show_params_grid_check.setChecked(True)
        self.show_params_grid_check.stateChanged.connect(self.update_params_grid_visibility)

    def _setup_layout(self):
        layout = QVBoxLayout()
        layout.addWidget(self.search_bar)
        layout.addWidget(self.variables_table)
        layout.addWidget(self.show_params_grid_check)
        layout.addWidget(self.batch_update_input)
        layout.addWidget(self.batch_update_button)
        layout.addWidget(self.column_select_combo)
        self.setLayout(layout)

    def update_params_grid_visibility(self, state):
        show_params_grid = state == 2  # state 2 is checked
        self.table_model.set_params_grid_visibility(show_params_grid)

        variables = list(self.equation_system.variables.values())
        grid = list(self.equation_system.grid.variables.keys())
        params = list(self.equation_system.parameter_variables.keys())

        if not show_params_grid:
            variables = [var for var in variables if var.name not in params and var.name not in grid]
            self.table_model.updateData(variables, [], [])
        else:
            self.table_model.updateData(variables, params, grid)

    def batch_update(self):
        new_value = self.batch_update_input.text()
        column_to_update = self.column_select_combo.currentIndex() + 1

        selected_indexes = map(self.proxy_model.mapToSource, self.variables_table.selectedIndexes())
        selected_rows = set(index.row() for index in selected_indexes)

        for row in selected_rows:
            index = self.table_model.index(row, column_to_update)
            # todo: show pop up warning if trying to edit uneditable column 
            # Only update if the cell is editable
            if self.table_model.flags(index) & Qt.ItemFlag.ItemIsEditable:
                self.table_model.setData(index, new_value, Qt.ItemDataRole.EditRole)

    def updateData(self):
        variables = list(self.equation_system.variables.values())
        grid = list(self.equation_system.grid.variables.keys())
        params = list(self.equation_system.parameter_variables.keys())
        self.table_model.updateData(variables, params, grid)


class VariableFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterKeyColumn(VariableAttributes.name.value)

    def setFilterString(self, text):
        regex = QRegularExpression(text)
        self.setFilterRegularExpression(regex)


class VariableTable(QAbstractTableModel):
    error = pyqtSignal(str)
    attribute_update = pyqtSignal(str, str, object)  # variable name, attribute name, new value

    def __init__(self, ureg, parent=None):
        super().__init__(parent)

        self.headers = {
            VariableAttributes.name: "Name",
            VariableAttributes.starting_guess: "Starting Guess",
            VariableAttributes.lower_bound: "Lower Bound",
            VariableAttributes.upper_bound: "Upper Bound",
            VariableAttributes.unit: "Unit",
        }
        self.ureg = ureg
        self.variable_data = []

        self.parameters = []
        self.grid = []

        self.params_grid_visibility = True

    def rowCount(self, parent=None):
        return len(self.variable_data)

    def columnCount(self, parent=None):
        return len(VariableAttributes)

    def data(self, index, role):
        variable = self.variable_data[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            attr_name = VariableAttributes(index.column()).name
            attr_value = getattr(variable, attr_name)
            return f"{attr_value}"
        elif role == Qt.ItemDataRole.BackgroundRole:
            if variable.name in self.parameters:
                return QColor('green')  # Change 'red' to any color you want.
            elif variable.name in self.grid:
                return QColor('red')  # Change 'blue' to any color you want.
            else:
                return None
        return None

    def set_params_grid_visibility(self, visibility):
        self.params_grid_visibility = visibility

    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            variable = self.variable_data[index.row()]
            column = index.column()

            if column in [VariableAttributes.starting_guess.value, VariableAttributes.lower_bound.value,
                          VariableAttributes.upper_bound.value]:
                try:
                    num_value = int(value) if '.' not in value else float(value)
                    value = num_value
                except ValueError:
                    self.error.emit(f"Input for variable {variable.name} should be a number.")
                    return False
            elif column == VariableAttributes.unit.value:
                try:
                    value = self.ureg.parse_units(value)
                except UndefinedUnitError:
                    self.error.emit(f"Input for variable {variable.name} is not a valid unit.")
                    return False

            self.updateVariableAttribute(variable.name, column, value)
            self.dataChanged.emit(index, index)
            return True
        return False

    def updateVariableAttribute(self, variable_name, column, value):
        self.attribute_update.emit(variable_name, VariableAttributes(column).name, value)

    def updateData(self, variables: list, parameters: list, grid: list):
        self.layoutAboutToBeChanged.emit()
        if not self.params_grid_visibility:
            variables = [var for var in variables if var.name not in parameters and var.name not in grid]
        self.variable_data = variables
        self.parameters = parameters
        self.grid = grid
        self.layoutChanged.emit()

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[VariableAttributes(section)]

    def flags(self, index):
        if not index.isValid():
            return None

        variable = self.variable_data[index.row()]

        # If the current column is the last column, make it editable
        if index.column() == self.columnCount() - 1:
            return super().flags(index) | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable

        # If the variable name is in self.parameters or self.grid, make the row uneditable
        if variable.name in self.parameters or variable.name in self.grid:
            return Qt.ItemFlag.ItemIsEnabled

        # If none of the above conditions are met, keep the row editable
        else:
            return super().flags(index) | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable

    def sort(self, column, order):
        self.layoutAboutToBeChanged.emit()
        attr = VariableAttributes(column).name
        self.variable_data.sort(key=lambda x: getattr(x, attr),
                                reverse=order == Qt.SortOrder.DescendingOrder)
        self.layoutChanged.emit()
