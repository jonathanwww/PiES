from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QSortFilterProxyModel
from pint import UndefinedUnitError
from PyQt6.QtWidgets import QComboBox, QPushButton, QHBoxLayout


class CustomTableModel(QtCore.QAbstractTableModel):
    def __init__(self, type, data, headers, parent=None):
        super().__init__(parent)
        self.type = type
        self._data = data
        self._headers = headers

    def data(self, index, role):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            item = self._data[index.row()]
            return item[self._headers[index.column()]]

        return None

    def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
        mapping = {
            "Starting Guess": "starting_guess",
            "Lower Bound": "lower_bound",
            "Upper Bound": "upper_bound",
            "Unit": "unit",
        }
        if index.isValid() and role == QtCore.Qt.ItemDataRole.EditRole:
            row = index.row()
            column = self._headers[index.column()]
            item_name = self._data[row]["Name"]

            if column in ["Starting Guess", "Lower Bound", "Upper Bound"]:
                try:
                    value = float(value)
                except ValueError:
                    QMessageBox.warning(None, 'Invalid Input', 'Input needs to be a floating point number.')
                    return False

            if column == "Unit":
                try:
                    value = self.parent().eqsys.ureg.parse_units(value)
                except UndefinedUnitError:
                    QMessageBox.warning(None, 'Invalid Input', f'Input for variable {item_name} is not a valid unit.')
                    return False

            # attribute update in eqsys
            if self.type == "Variables":
                object_type = "Variables"
            elif self.type == "Parameters":
                object_type = "Parameters"
            elif self.type == "Functions":
                object_type = "Functions"

            self.parent().eqsys.eq_manager.set_attr(item_name, object_type, mapping[column], value)

            self._data[row][column] = str(value)
            self.dataChanged.emit(index, index)
            return True
        return False

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.ItemDataRole.DisplayRole and orientation == QtCore.Qt.Orientation.Horizontal:
            return self._headers[section]

        return None

    def flags(self, index):
        if self._headers[index.column()] != "Name":
            return QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEditable
        else:
            return QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable

    def insertRow(self, row_data, parent=QtCore.QModelIndex()):
        # Here we're assuming that we're always appending to the end of the list
        self.beginInsertRows(parent, self.rowCount(), self.rowCount())
        self._data.append(row_data)
        self.endInsertRows()

    def removeRow(self, row, parent=QtCore.QModelIndex()):
        self.beginRemoveRows(parent, row, row)
        del self._data[row]
        self.endRemoveRows()


class ObjectTableWidget(QtWidgets.QWidget):
    def __init__(self, eqsys, parent=None):
        super().__init__(parent)
        self.eqsys = eqsys

        self.tab_widget = QtWidgets.QTabWidget(self)

        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.textChanged.connect(self.search_in_table)
        self.search_bar.setPlaceholderText("Search by attribute")

        self.variables_table = QtWidgets.QTableView(self.tab_widget)
        self.variables_table.setSortingEnabled(True)
        self.variables_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.variables_proxy_model = QSortFilterProxyModel()
        self.variables_proxy_model.setFilterKeyColumn(-1)  # Search in all columns

        self.parameters_table = QtWidgets.QTableView(self.tab_widget)
        self.parameters_table.setSortingEnabled(True)
        self.parameters_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.parameters_proxy_model = QSortFilterProxyModel()
        self.parameters_proxy_model.setFilterKeyColumn(-1)  # Search in all columns

        self.functions_table = QtWidgets.QTableView(self.tab_widget)
        self.functions_table.setSortingEnabled(True)
        self.functions_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.functions_proxy_model = QSortFilterProxyModel()
        self.functions_proxy_model.setFilterKeyColumn(-1)  # Search in all columns

        self.tab_widget.addTab(self.variables_table, "Variables")
        self.tab_widget.addTab(self.parameters_table, "Parameters")
        self.tab_widget.addTab(self.functions_table, "Functions")

        self.eqsys.data_changed.connect(self.update_functions_table)
        self.eqsys.data_changed.connect(self.update_variable_table)
        self.eqsys.data_changed.connect(self.update_parameter_table)
        
        # todo: make it work just by the  variables being added, or if too slow with so many calls, instead collect on_change variables
        #self.eqsys.variable_manager.variable_added.connect(self.add_variable)
        #self.eqsys.variable_manager.variable_removed.connect(self.remove_variable)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.search_bar)
        layout.addWidget(self.tab_widget)

        # batch update
        self.tab_widget.currentChanged.connect(self.update_attribute_selector)

        self.attribute_selector = QComboBox()
        self.attribute_selector.addItems(["Starting Guess", "Lower Bound", "Upper Bound", "Unit"])
        self.new_value_input = QtWidgets.QLineEdit()
        self.update_button = QPushButton("Update Selected")
        self.update_button.clicked.connect(self.update_selected_objects)

        self.update_layout = QHBoxLayout()
        self.update_layout.addWidget(self.attribute_selector)
        self.update_layout.addWidget(self.new_value_input)
        self.update_layout.addWidget(self.update_button)

        layout.addLayout(self.update_layout)
    
    def update_attribute_selector(self, index):
        if index == 0:  # Variables tab
            self.attribute_selector.clear()
            self.attribute_selector.addItems(["Starting Guess", "Lower Bound", "Upper Bound", "Unit"])
        elif index == 1:  # Parameters tab
            self.attribute_selector.clear()
            self.attribute_selector.addItem("Unit")
        elif index == 2:  # Functions tab
            self.attribute_selector.clear()
            self.attribute_selector.addItem("Unit")

    def update_selected_objects(self):
        attribute_to_update = self.attribute_selector.currentText()
        new_value = self.new_value_input.text()

        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:
            selected_rows = self.variables_table.selectionModel().selectedRows()
            model = self.variables_proxy_model
        elif current_tab == 1:
            selected_rows = self.parameters_table.selectionModel().selectedRows()
            model = self.parameters_proxy_model
        else:
            selected_rows = self.functions_table.selectionModel().selectedRows()
            model = self.functions_proxy_model

        error_occurred = False
        for index in selected_rows:
            if error_occurred:
                break

            source_index = model.mapToSource(index)
            column = model.sourceModel()._headers.index(attribute_to_update)
            attribute_index = source_index.sibling(source_index.row(), column)

            if not model.sourceModel().setData(attribute_index, new_value, QtCore.Qt.ItemDataRole.EditRole):
                error_occurred = True

    def search_in_table(self, text):
        search = QtCore.QRegularExpression(text, QtCore.QRegularExpression.PatternOption.CaseInsensitiveOption)
        self.variables_proxy_model.setFilterRegularExpression(search)
        self.parameters_proxy_model.setFilterRegularExpression(search)
        self.functions_proxy_model.setFilterRegularExpression(search)

    def add_variable(self, var: str):
        var = self.eqsys.variable_manager.variables[var]
        if var.name not in self.eqsys.variable_manager.parameter_variables:
            new_row = {
                "Name": var.name,
                "Starting Guess": str(var.starting_guess),
                "Lower Bound": str(var.lower_bound),
                "Upper Bound": str(var.upper_bound),
                "Unit": str(var.unit)
            }
            self.variables_proxy_model.sourceModel().insertRow(new_row)

    def remove_variable(self, var_name):
        model = self.variables_proxy_model.sourceModel()
        for row in range(model.rowCount()):
            if model.data(model.index(row, 0)) == var_name:
                model.removeRow(row)
                break
                
    def update_variable_table(self):
        variables_data = [
            {
                "Name": var.name,
                "Starting Guess": str(var.starting_guess),
                "Lower Bound": str(var.lower_bound),
                "Upper Bound": str(var.upper_bound),
                "Unit": str(var.unit)
            }
            for var in self.eqsys.variables.values()
        ]
        model = CustomTableModel('Variables', variables_data,
                                 ["Name", "Starting Guess", "Lower Bound", "Upper Bound", "Unit"], 
                                 self)
        self.variables_proxy_model.setSourceModel(model)
        self.variables_table.setModel(self.variables_proxy_model)

    def update_parameter_table(self):
        parameters_data = [
            {
                "Name": param.name,
                "Unit": str(param.unit)
            }
            for param in self.eqsys.parameters.values()
        ]
        model = CustomTableModel('Parameters', parameters_data, ["Name", "Unit"], self)
        self.parameters_proxy_model.setSourceModel(model)
        self.parameters_table.setModel(self.parameters_proxy_model)

    def update_functions_table(self):
        functions_data = [
            {
                "Name": func.name,
                "Unit": str(func.unit)
            }
            for func in self.eqsys.functions.values()
        ]
        model = CustomTableModel('Functions', functions_data, ["Name", "Unit"], self)
        self.functions_proxy_model.setSourceModel(model)
        self.functions_table.setModel(self.functions_proxy_model)
