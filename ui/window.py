import traceback
import logging
import os

from pathlib import Path

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMenu, QWidget, QStatusBar
from PyQt6.QtGui import QAction

from logic.equationsystem import EquationSystem, solve
from logic.util import blocking

import re
from PyQt6.QtGui import QTextCharFormat, QSyntaxHighlighter, QColor, QFont

from ui.editor import PythonEditor, EquationEditor, ConsoleEditor
from ui.table import VariableTable

import json

class Window(QMainWindow):
    def __init__(self, eqsys: EquationSystem, parent = None, flags = Qt.WindowType.Window):
        super().__init__(parent, flags)
        self.eqsys = eqsys

        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)

        self.python_edit = PythonEditor(self)        
        self.text_edit = EquationEditor(self)
        self.console_output = ConsoleEditor(self)
        
        self.variables_table = VariableTable(self)
        self.variables_table.cellChanged.connect(self.update_variable)

        self.solve_button = QtWidgets.QPushButton('Solve', self)
        self.solve_button.clicked.connect(self.solve_eqsys)

        self.remove_unused_vars_button = QtWidgets.QPushButton('Remove unused variables', self)
        self.remove_unused_vars_button.clicked.connect(self.remove_unused_variables)

        self.show_blocks_button = QtWidgets.QPushButton('Show blocks', self)
        self.show_blocks_button.clicked.connect(self.show_blocks)

        self.show_all_eqs_button = QtWidgets.QPushButton('Show equations', self)
        self.show_all_eqs_button.clicked.connect(self.show_all_equations)
        
        self.clear_console_button = QtWidgets.QPushButton('Clear console', self)
        self.clear_console_button.clicked.connect(self.clear_console)
        
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.python_edit, 0, 0)
        layout.addWidget(self.text_edit, 0, 1)
        layout.addWidget(self.variables_table, 0, 2)
        layout.addWidget(self.console_output, 1, 0, 1, 3)
        
        layout.addWidget(self.remove_unused_vars_button, 2, 0)
        layout.addWidget(self.show_all_eqs_button, 3, 0)
        layout.addWidget(self.show_blocks_button, 4, 0)
        layout.addWidget(self.solve_button, 2, 1)
        layout.addWidget(self.clear_console_button, 3, 1)
        
        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 3)
        layout.setColumnStretch(2, 3)

        layout.setRowStretch(0, 2)
        layout.setRowStretch(1, 1)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self._createActions()
        self._createMenu()

        self.lastDir = str(Path.home())

        self.sync_gui_and_eqsys()

    def _createActions(self):
        self.openAction = QAction("&Open", self)
        self.openAction.triggered.connect(self.loadTextDialog)
        self.saveAction = QAction("&Save", self)
        self.saveAction.triggered.connect(self.saveTextDialog)
        self.exitAction = QAction("&Exit", self)
        self.exitAction.triggered.connect(self.close)
    
    def _createMenu(self):
        menuBar = self.menuBar()
        fileMenu = QMenu("&File", self)
        menuBar.addMenu(fileMenu)
        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addAction(self.exitAction)

    def saveTextDialog(self):
        selectedFile = QFileDialog.getSaveFileName(self, self.tr("Save file"), self.lastDir, self.tr("JSON files (*.json)"))
        if selectedFile[0]:
            filename = selectedFile[0]
            self.saveTextToJson(filename)        
            self.lastDir = os.path.dirname(filename)

    def loadTextDialog(self):
        selectedFile = QFileDialog.getOpenFileName(self, self.tr("Open file"), self.lastDir, self.tr("JSON files (*.json)"))
        if selectedFile[0]:
            filename = selectedFile[0]
            self.loadTextFromJson(filename)
            self.lastDir = os.path.dirname(filename)

    def saveTextToJson(self, path: str):
        dataDict = {}
        dataDict["pythonStr"] = self.python_edit.toPlainText()
        dataDict["equationStr"] = self.text_edit.toPlainText()
        with open(path, "w") as outfile:
            json.dump(dataDict, outfile, sort_keys=True, indent=4)

    def loadTextFromJson(self, path: str):
        dataDict = {}
        with open(path, "r") as infile:
            dataDict = dict(json.load(infile))
        self.python_edit.setPlainText(dataDict.get("pythonStr", ""))
        self.text_edit.setPlainText(dataDict.get("equationStr", ""))
        
    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key.Key_Return:
            self.sync_gui_and_eqsys()
        # Respect the normal behaviour
        super().keyReleaseEvent(e)
        
    def sync_gui_and_eqsys(self):  # syncs the equation system object with the ui input
        try:
            # gets the code from python window
            text = self.text_edit.toPlainText()
            code = self.python_edit.toPlainText()
    
            # update eqsys with input from windows
            self.eqsys.update_eqsys(text, code)
            
            # update status bar
            vars_in_use = len([var for var in self.eqsys.variables if var.used])
            self.statusBar.showMessage(f'{"[✓]" if vars_in_use == len(self.eqsys.equations) else "[x]"} '
                                      f'Variables in use: {vars_in_use} - Equations: {len(self.eqsys.equations)}')
            
            # update var window
            self.variables_table.clear()
            self.variables_table.setHorizontalHeaderLabels(["Name", "x0", "Lower b", "Upper b", "Used", "Loopvar", "Paramvar"])  # clear() removes headers
            self.variables_table.setRowCount(len(self.eqsys.variables))
    
            for i, variable in enumerate(self.eqsys.variables):  # if var -> eq.variable == 1, param var, else normal var
                self.variables_table.setItem(i, 0, QtWidgets.QTableWidgetItem(variable.name))
                self.variables_table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(variable.starting_guess)))
                self.variables_table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(variable.lower_bound)))
                self.variables_table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(variable.upper_bound)))
                self.variables_table.setItem(i, 4, QtWidgets.QTableWidgetItem(str(variable.used)))
                self.variables_table.setItem(i, 5, QtWidgets.QTableWidgetItem(str(variable.loop_var)))
                self.variables_table.setItem(i, 6, QtWidgets.QTableWidgetItem(str(variable.param_var)))
                
                # color the whole row
                for j in range(self.variables_table.columnCount()):
                    if not variable.used:
                        self.variables_table.item(i, j).setBackground(QColor(38, 38, 38, 150))
                    if variable.loop_var and variable.param_var:
                        self.variables_table.item(i, j).setBackground(QColor(110, 90, 90, 150))
                
                # color columns           
                if variable.loop_var:
                    self.variables_table.item(i, 5).setBackground(QColor(109, 115, 108, 150))
                if variable.param_var:
                    self.variables_table.item(i, 6).setBackground(QColor(109, 110, 98, 150))
                        
        except Exception:
            error_message = "Updating eq sys failed with message: " + traceback.format_exc()
            self.update_console_output(error_message)
    
    def clear_console(self):
        self.console_output.clear()
        
    def update_console_output(self, output_text):
        old_output = self.console_output.toPlainText() + '\n\n'
        updated_text = old_output + output_text
        self.console_output.setPlainText(updated_text)
        
    def update_variable(self, row, col):
        item = self.variables_table.item(row, col)
        variable = self.eqsys.variables[row]
        if col == 1:
            variable.starting_guess = float(item.text())
        elif col == 2:
            variable.lower_bound = float(item.text())
        elif col == 3:
            variable.upper_bound = float(item.text())
    
    def remove_unused_variables(self):
        self.sync_gui_and_eqsys()
        self.eqsys.variables = [var for var in self.eqsys.variables if var.used]
        self.sync_gui_and_eqsys()
    
    def show_all_equations(self):
        self.sync_gui_and_eqsys()
        equations = [eq.residual for eq in self.eqsys.equations]
        self.update_console_output(str(equations))
        
    def show_blocks(self):
        self.sync_gui_and_eqsys()
        try:
            self.update_console_output(str(blocking(self.eqsys)))
        except Exception:
            error_message = "Solving eq sys failed with message: " + traceback.format_exc()
            self.update_console_output(error_message)
    
    def solve_eqsys(self):
        self.sync_gui_and_eqsys()
        try:
            solutions = solve(self.eqsys)
            for entry in solutions:
                self.update_console_output('Loop var vals' + str(entry[0]) + '\nVariable solutions:')
                post = [i for i in entry[1]]
                self.update_console_output(str(post))
                    
        except Exception:
            error_message = "Solving eq sys failed with message: " + traceback.format_exc()
            self.update_console_output(error_message)
