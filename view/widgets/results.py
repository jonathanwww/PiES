from PyQt6.QtWidgets import QWidget, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QPushButton, QInputDialog, QHBoxLayout, QDialog, QCheckBox, QLabel, QDialogButtonBox
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTabWidget, QTableWidget, QTableWidgetItem, QMenu, QVBoxLayout, QPushButton, QInputDialog, QHBoxLayout, QAbstractItemView
from PyQt6.QtWidgets import QScrollArea, QLineEdit, QFormLayout
from PyQt6.QtWidgets import QMessageBox


class ResultsWidget(QWidget):
    # todo: remake select variables
    def __init__(self, eqsys, results_manager, parent=None):
        super().__init__(parent)
        self.eqsys = eqsys
        self.results_manager = results_manager

        self.layout = QVBoxLayout(self)

        self.tabs = QTabWidget(self)
        self.layout.addWidget(self.tabs)

        self.buttons_layout = QHBoxLayout()
        self.rename_button = QPushButton('Rename Entry', self)
        self.delete_button = QPushButton('Delete Entry', self)
        self.select_variables_button = QPushButton('Select Variables', self)
        self.send_to_x0_button = QPushButton('Send to x0', self)
        self.buttons_layout.addWidget(self.rename_button)
        self.buttons_layout.addWidget(self.delete_button)
        self.buttons_layout.addWidget(self.select_variables_button)
        self.buttons_layout.addWidget(self.send_to_x0_button)
        self.layout.addLayout(self.buttons_layout)

        self.rename_button.clicked.connect(self.rename_entry)
        self.delete_button.clicked.connect(self.delete_entry)
        self.select_variables_button.clicked.connect(self.select_variables)
        self.send_to_x0_button.clicked.connect(self.send_to_x0)

        self.results_manager.data_changed.connect(self.update_tabs)

        self.show()

    def update_tabs(self):
        self.tabs.clear()
        for entry_name, entry in self.results_manager.entries.items():
            table = QTableWidget()

            # Set up the table with the entry's data
            table.setColumnCount(len(entry.variables))
            table.setRowCount(len(entry.data))
            table.setHorizontalHeaderLabels(entry.variables)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

            for i, row in enumerate(entry.data):
                for j, item in enumerate(row):
                    table.setItem(i, j, QTableWidgetItem(str(item)))

            self.tabs.addTab(table, entry_name)

    def rename_entry(self):
        index = self.tabs.currentIndex()
        old_name = self.tabs.tabText(index)
        new_name, ok = QInputDialog.getText(self, "Rename Tab", "Enter new name:")
        if ok:
            try:
                self.results_manager.rename_entry(old_name, new_name)
            except ValueError as e:
                QMessageBox.warning(self, 'Name Error', str(e))
            except KeyError as e:
                QMessageBox.warning(self, 'Name Error', str(e))

    def delete_entry(self):
        index = self.tabs.currentIndex()
        name = self.tabs.tabText(index)
        self.results_manager.delete_entry(name)

    def select_variables(self):
        index = self.tabs.currentIndex()
        entry_name = self.tabs.tabText(index)
        entry = self.results_manager.entries[entry_name]

        dialog = QDialog()
        dialog.setWindowTitle("Select Variables")

        dialog_layout = QVBoxLayout(dialog)

        # Search field and check all button
        top_layout = QHBoxLayout()
        search_line_edit = QLineEdit(dialog)
        top_layout.addWidget(search_line_edit)
        select_all_checkbox = QCheckBox("Select All")
        top_layout.addWidget(select_all_checkbox)
        dialog_layout.addLayout(top_layout)

        # Scroll area for variable checkboxes
        scroll_area = QScrollArea(dialog)
        scroll_area.setWidgetResizable(True)
        dialog_layout.addWidget(scroll_area)

        checkboxes_widget = QWidget()
        checkboxes_layout = QVBoxLayout(checkboxes_widget)
        scroll_area.setWidget(checkboxes_widget)

        checkboxes = []
        for variable in entry.variables:
            checkbox = QCheckBox(variable)
            checkbox.setChecked(True)
            checkboxes.append(checkbox)
            checkboxes_layout.addWidget(checkbox)

        checkboxes_layout.addStretch(1)

        # OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        dialog_layout.addWidget(button_box)

        # Connect signals
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        def update_select_all_state():
            visible_checkboxes = [checkbox for checkbox in checkboxes if checkbox.isVisible()]
            all_checked = all(checkbox.isChecked() for checkbox in visible_checkboxes)
            select_all_checkbox.setChecked(all_checked)

        def select_all(state):
            for checkbox in checkboxes:
                if checkbox.isVisible():
                    checkbox.setChecked(state)

        select_all_checkbox.stateChanged.connect(select_all)
        for checkbox in checkboxes:
            checkbox.stateChanged.connect(update_select_all_state)

        def search_variables(text):
            for checkbox in checkboxes:
                checkbox.setVisible(text.lower() in checkbox.text().lower())
            update_select_all_state()

        search_line_edit.textChanged.connect(search_variables)

        # Update the checked state of checkboxes based on the current column visibility
        table = self.tabs.widget(index)
        column_visibility = [not table.isColumnHidden(i) for i in range(table.columnCount())]
        for checkbox, visible in zip(checkboxes, column_visibility):
            checkbox.setChecked(visible)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            for i, checkbox in enumerate(checkboxes):
                table.setColumnHidden(i, not checkbox.isChecked())
        else:
            # If the dialog was cancelled, revert the column visibility
            for i, visible in enumerate(column_visibility):
                table.setColumnHidden(i, not visible)

    def send_to_x0(self):
        # todo: update variable starting guesses in eqsys
        
        # Retrieve the selected rows
        table = self.tabs.currentWidget()
        selected_rows = set(index.row() for index in table.selectedIndexes())

        if len(selected_rows) > 1:
            QMessageBox.warning(self, 'Selection error', 'Please select only one row.')
            return

        elif len(selected_rows) == 0:
            QMessageBox.warning(self, 'Selection error', 'Please select a row.')
            return

        # Retrieve the corresponding entry
        entry_name = self.tabs.tabText(self.tabs.currentIndex())
        entry = self.results_manager.entries[entry_name]
        
        # Create a dictionary of variables and values
        selected_row = selected_rows.pop()
        row_data = entry.data[selected_row]
        variable_dict = dict(zip(entry.variables, row_data))


        # Check if all keys are present in the dict self.eqsys.variables
        missing_variables = [key for key in variable_dict if key not in self.eqsys.variables]

        # Variables that are present but not valid for updating
        invalid_variables = []

        # Variables that have been updated successfully
        updated_variables = []

        # Variables with value as 'None'
        none_variables = []

        for variable, value in variable_dict.items():
            if value == 'None':
                none_variables.append(variable)
                continue

            if variable in self.eqsys.variables:
                self.eqsys.eq_manager.set_attr(variable, 'Variables', 'starting_guess', value)
                updated_variables.append(variable)
            else:
                invalid_variables.append(variable)
        self.eqsys._on_change()
        # Construct error message
        error_message = ""

        if updated_variables:
            error_message += f"The following variables were updated with new starting guesses:\n{', '.join(updated_variables)}.\n\n"

        if missing_variables:
            error_message += f"The following variables are not present in the equation system:\n{', '.join(missing_variables)}.\n\n"

        if invalid_variables:
            error_message += f"The following variables could not be updated (they are either grid variables or parameter variables):\n{', '.join(invalid_variables)}.\n\n"

        if none_variables:
            error_message += f"The following variables were not updated as they have a 'None' value:\n{', '.join(none_variables)}.\n\n"

        if error_message:
            QMessageBox.warning(self, 'Starting guess update', error_message)
            return