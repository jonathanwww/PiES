from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QCheckBox, QPushButton, QLineEdit, 
                             QTreeView, QTableWidget, QTableWidgetItem, QGroupBox, 
                             QHBoxLayout, QAbstractItemView, QComboBox, QTabWidget)
from PyQt6.QtCore import Qt, QSortFilterProxyModel, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem


class ResultsWidget(QWidget):
    update_starting_guess = pyqtSignal(dict)  # Emit a list of column contents for the selected row

    def __init__(self, results_manager, parent=None):
        super().__init__(parent)
        self.results_manager = results_manager

        # refresh on change in results manager
        self.results_manager.data_changed.connect(self.update)
        
        # Layout for the widget
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Add a QPushButton for hiding/showing the variable selector
        self.toggle_button = QPushButton("Hide/Show Select Variables")
        self.toggle_button.clicked.connect(self.toggle_variable_selector)
        self.layout.addWidget(self.toggle_button)
        
        # GroupBox for the variable selector
        self.variable_groupbox = QGroupBox("Select Variables")
        self.variable_layout = QVBoxLayout()
        self.variable_groupbox.setLayout(self.variable_layout)
        self.layout.addWidget(self.variable_groupbox)

        # Hide the variable selector by default
        self.variable_groupbox.hide()

        # Add CheckAll checkbox
        self.check_all = QCheckBox('Check All')
        self.check_all.setChecked(True)
        self.check_all.stateChanged.connect(self.check_uncheck_all)
        self.variable_layout.addWidget(self.check_all)

        # Check the 'Check All' checkbox by default        
        self.check_all.stateChanged.connect(self.check_uncheck_all)
        self.variable_layout.addWidget(self.check_all)
        
        # Add a filter QLineEdit
        self.search_line_edit = QLineEdit()
        self.search_line_edit.setPlaceholderText('Search...')
        self.search_line_edit.textChanged.connect(self.filter_variables)
        self.variable_layout.addWidget(self.search_line_edit)

        # QTreeView for variable list
        self.model = self.create_model_from_solver_variables()

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.proxy_model)
        self.variable_layout.addWidget(self.tree_view)
        
        # QTabWidget for displaying the solver results
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)

        # QPushButton for the required functionalities
        self.delete_button = QPushButton("Delete entry")
        self.delete_button.clicked.connect(self.delete_selected_entry)
        self.copy_button = QPushButton("Copy results from Selected Runs")
        self.send_button = QPushButton("Send Run Result to x0")
        self.send_button.clicked.connect(self.send_run_result)

        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.delete_button)
        self.button_layout.addWidget(self.copy_button)
        self.button_layout.addWidget(self.send_button)
        self.layout.addLayout(self.button_layout)

        # Format selection
        self.format_combobox = QComboBox()
        self.format_combobox.addItem('Float')
        self.format_combobox.addItem('Scientific')
        self.format_combobox.currentTextChanged.connect(self.update_solver_results)
        self.variable_layout.addWidget(self.format_combobox)

        # Decimal places selection
        self.decimal_combobox = QComboBox()
        for i in range(10):
            self.decimal_combobox.addItem(str(i))
        self.decimal_combobox.setCurrentIndex(3)  # Set default to 3 digits
        self.decimal_combobox.currentTextChanged.connect(self.update_solver_results)
        self.variable_layout.addWidget(self.decimal_combobox)
        
        # Connect itemChanged signal to on_variable_changed method
        self.model.itemChanged.connect(self.on_variable_changed)
        # Connect the textChanged signal to uncheck_all
        self.search_line_edit.textChanged.connect(self.uncheck_check_all_checkbox)

    def send_run_result(self):
        # Get the currently active table widget
        table_widget = self.tab_widget.widget(self.tab_widget.currentIndex())

        # Get selected rows
        selected_rows = list({index.row() for index in table_widget.selectionModel().selectedIndexes()})
        
        if len(selected_rows) == 0:
            self.parent().parent().parent().show_error_message("Please select a row.")
        elif len(selected_rows) > 1:
            self.parent().parent().parent().show_error_message("Please select only one row.")
        elif selected_rows:
            row = selected_rows[0]
            # Get the contents of the columns in the selected row
            contents = {table_widget.horizontalHeaderItem(column).text(): table_widget.item(row, column).text()
                        for column in range(table_widget.columnCount())}
            print(contents)
            # Emit the signal with the contents of the columns in the selected row
            self.update_starting_guess.emit(contents)
            
    def delete_selected_entry(self):
        index = self.tab_widget.currentIndex()
        if index != -1:  # No tab is selected if currentIndex returns -1
            self.results_manager.delete_entry(index)
            self.tab_widget.removeTab(index)
            self.update()
            
    def toggle_variable_selector(self):
        # If the variable selector is visible, hide it. Otherwise, show it.
        if self.variable_groupbox.isVisible():
            self.variable_groupbox.hide()
        else:
            self.variable_groupbox.show()
            
    def uncheck_check_all_checkbox(self):
        # Temporarily block signals
        self.check_all.blockSignals(True)

        # Uncheck the 'Check All' checkbox
        self.check_all.setChecked(False)

        # Resume signals
        self.check_all.blockSignals(False)

    def on_variable_changed(self, item):
        # If a variable's check state has changed, update the solver results
        if item.isCheckable():
            self.update_solver_results()

    def create_model_from_solver_variables(self):
        model = QStandardItemModel()
        for var in self.results_manager.all_variables:
            item = QStandardItem(var)
            item.setCheckable(True)
            # Set the check state to checked by default
            item.setCheckState(Qt.CheckState.Checked)
            model.appendRow(item)
        return model

    def filter_variables(self, text):
        self.proxy_model.setFilterRegularExpression(text)

    def check_uncheck_all(self):
        state = self.check_all.checkState()
        for index in range(self.proxy_model.rowCount()):
            source_index = self.proxy_model.mapToSource(self.proxy_model.index(index, 0))
            item = self.model.itemFromIndex(source_index)
            item.setCheckState(state)

    def update_solver_results(self):
        # Save the current tab index
        current_tab_index = self.tab_widget.currentIndex()

        # Clear the tab widget
        self.tab_widget.clear()

        # For each list of results, create a table widget and add it as a tab
        for i, results in enumerate(self.results_manager.entries):
            table_widget = self.create_table_widget(results)
            self.tab_widget.addTab(table_widget, f'Entry {i + 1}')

        # Restore the current tab index
        self.tab_widget.setCurrentIndex(current_tab_index)
    
    def format_value(self, value):
        format_type = self.format_combobox.currentText()
        decimals = int(self.decimal_combobox.currentText())
        if format_type == 'Float':
            return f'{value:.{decimals}f}'
        elif format_type == 'Scientific':
            return f'{value:.{decimals}e}'
    
    def get_selected_variables(self):
        selected_variables = []
        for index in range(self.model.rowCount()):
            item = self.model.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                selected_variables.append(item.text())
        return selected_variables

    def update_solver_variables(self):
        self.model.clear()
        for var in self.results_manager.all_variables:
            item = QStandardItem(var)
            item.setCheckable(True)
            item.setCheckState(Qt.CheckState.Checked)
            self.model.appendRow(item)
        self.proxy_model.setSourceModel(self.model)
    
    def create_table_widget(self, results):
        table_widget = QTableWidget()
        table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        table_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        selected_variables = self.get_selected_variables()

        # Set column count and headers
        table_widget.setColumnCount(len(selected_variables))
        table_widget.setHorizontalHeaderLabels(selected_variables)

        # Set row count and data
        table_widget.setRowCount(len(results))
        for i, result in enumerate(results):
            # Set row header (run name)
            table_widget.setVerticalHeaderItem(i, QTableWidgetItem(f"Run {i + 1}"))

            # Set cell values
            for j, var in enumerate(selected_variables):
                value = result.get(var, 0.0)
                formatted_value = self.format_value(value)
                table_widget.setItem(i, j, QTableWidgetItem(formatted_value))

        return table_widget
    
    def update(self):
        self.update_solver_variables()
        self.update_solver_results()
