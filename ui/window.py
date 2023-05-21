import traceback
import logging
import os
from pathlib import Path

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMenu, QFrame, QWidget, QStatusBar, QToolBar, QSplitter, QLabel, QVBoxLayout
from PyQt6.QtGui import QAction

from logic.equationsystem import EquationSystem, NormalVariable, ParameterVariable, LoopVariable, solve, blocking

import re
from PyQt6.QtGui import QTextCharFormat, QSyntaxHighlighter, QColor, QFont

from ui.editor import PythonEditor, EquationEditor, ConsoleEditor
from ui.table import VariableTable

import json

class Window(QMainWindow):
    def __init__(self, eqsys: EquationSystem, parent=None, flags=Qt.WindowType.Window):
        super().__init__(parent, flags)
        self.eqsys = eqsys

        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)

        self.python_edit = PythonEditor(self)
        self.text_edit = EquationEditor(self)
        self.console_output = ConsoleEditor(self)

        self.variables_table = VariableTable(self)
        self.variables_table.cellChanged.connect(self.update_variable)

        self.toolbar = QToolBar("ToolBar", self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        toolbar_solve = QAction("Solve", self)
        toolbar_solve.triggered.connect(self.solve_eqsys)
        self.toolbar.addAction(toolbar_solve)

        toolbar_update_guess_values = QAction("Update Guess Values", self)
        toolbar_update_guess_values.triggered.connect(self.update_guess_values)
        self.toolbar.addAction(toolbar_update_guess_values)

        toolbar_remove_unused_variables = QAction("Remove unused variables", self)
        toolbar_remove_unused_variables.triggered.connect(self.remove_unused_variables)
        self.toolbar.addAction(toolbar_remove_unused_variables)

        self.addToolBarBreak()

        self.toolbar_console = QToolBar("Console toolbar", self)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.toolbar_console)

        toolbar_clear_console = QAction("Clear Console", self)
        toolbar_clear_console.triggered.connect(self.clear_console)
        self.toolbar_console.addAction(toolbar_clear_console)

        toolbar_show_equations = QAction("Show Equations", self)
        toolbar_show_equations.triggered.connect(self.show_all_equations)
        self.toolbar_console.addAction(toolbar_show_equations)

        toolbar_show_blocks = QAction("Show Blocks", self)
        toolbar_show_blocks.triggered.connect(self.show_blocks)
        self.toolbar_console.addAction(toolbar_show_blocks)

        console = QFrame()
        console.setFrameStyle(QFrame.Shape.Box)
        label_console = QLabel('Console')
        label_console.setFixedHeight(25)
        layout_console = QVBoxLayout()
        layout_console.addWidget(label_console, 1)
        layout_console.addWidget(self.console_output, 2)
        layout_console.addWidget(self.toolbar_console, 3)
        console.setLayout(layout_console)
        layout_console.setContentsMargins(5, 0, 5, 0)

        python_editor = QFrame()
        python_editor.setFrameStyle(QFrame.Shape.Box)
        label_python_editor = QLabel('Python Editor')
        label_python_editor.setFixedHeight(25)
        layout_python_editor = QVBoxLayout()
        layout_python_editor.addWidget(label_python_editor, 1)
        layout_python_editor.addWidget(self.python_edit, 2)
        python_editor.setLayout(layout_python_editor)
        layout_python_editor.setContentsMargins(5, 0, 5, 5)

        text_editor = QFrame()
        text_editor.setFrameStyle(QFrame.Shape.Box)
        label_text_editor = QLabel('Equation Editor')
        label_text_editor.setFixedHeight(25)
        layout_text_editor = QVBoxLayout()
        layout_text_editor.addWidget(label_text_editor, 1)
        layout_text_editor.addWidget(self.text_edit, 2)
        text_editor.setLayout(layout_text_editor)
        layout_text_editor.setContentsMargins(5, 0, 5, 5)

        variable_table = QFrame()
        variable_table.setFrameStyle(QFrame.Shape.Box)
        label_variable_table = QLabel('Variable Table')
        label_variable_table.setFixedHeight(25)
        layout_variable_table = QVBoxLayout()
        layout_variable_table.addWidget(label_variable_table, 1)
        layout_variable_table.addWidget(self.variables_table, 2)
        variable_table.setLayout(layout_variable_table)
        layout_variable_table.setContentsMargins(5, 0, 5, 5)

        splitter1 = QSplitter(Qt.Orientation.Horizontal) #splits left-right left side includes editors and console  right side variable table
        splitter2 = QSplitter(Qt.Orientation.Vertical) #splits up-down editors and console
        splitter3 = QSplitter(Qt.Orientation.Horizontal) #splits left-right between python and equation editors

        # Add editors to splitter 3
        splitter3.addWidget(python_editor)
        splitter3.addWidget(text_editor)

        # Add splitter 3 and console to splitter 2
        splitter2.addWidget(splitter3)
        splitter2.addWidget(console)

        #add splitter 2 and table to splitter 1
        splitter1.addWidget(splitter2)
        splitter1.addWidget(variable_table)

        splitter1.setHandleWidth(5)
        splitter2.setHandleWidth(5)
        splitter3.setHandleWidth(5)

        self.setCentralWidget(splitter1)
        self.setContentsMargins(5, 0, 5, 0)

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
        selectedFile = QFileDialog.getSaveFileName(self, self.tr("Save file"), self.lastDir,
                                                   self.tr("JSON files (*.json)"))
        if selectedFile[0]:
            filename = selectedFile[0]
            self.saveTextToJson(filename)
            self.lastDir = os.path.dirname(filename)

    def loadTextDialog(self):
        selectedFile = QFileDialog.getOpenFileName(self, self.tr("Open file"), self.lastDir,
                                                   self.tr("JSON files (*.json)"))
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
            vars_in_use = len([var for var in self.eqsys.variables.values() 
                               if (isinstance(var, NormalVariable) and var.used) 
                               or isinstance(var, (LoopVariable, ParameterVariable))])
            
            self.statusBar.showMessage(f'{"[✓]" if vars_in_use == len(self.eqsys.equations) else "[x]"} '
                                      f'Variables in use: {vars_in_use} - Equations: {len(self.eqsys.equations)}')

            # update var window
            self.variables_table.clear()
            self.variables_table.setHorizontalHeaderLabels(
                ["Name", "x0", "Lower b", "Upper b", "Used", "Loopvar", "Paramvar", "Unit"])  # clear() removes headers
            self.variables_table.setRowCount(len(self.eqsys.variables))

            for i, variable in enumerate(self.eqsys.variables.values()):
                self.variables_table.setItem(i, 0, QtWidgets.QTableWidgetItem(variable.name))
                self.variables_table.setItem(i, 7, QtWidgets.QTableWidgetItem(variable.unit))
                
                if isinstance(variable, NormalVariable):
                    self.variables_table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(variable.starting_guess)))
                    self.variables_table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(variable.lower_bound)))
                    self.variables_table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(variable.upper_bound)))
                    self.variables_table.setItem(i, 4, QtWidgets.QTableWidgetItem(str(variable.used)))

                if isinstance(variable, LoopVariable):
                    self.variables_table.setItem(i, 5, QtWidgets.QTableWidgetItem(str(variable.loop_values)))
                else:
                    self.variables_table.setItem(i, 5, QtWidgets.QTableWidgetItem(''))

                if isinstance(variable, ParameterVariable):
                    self.variables_table.setItem(i, 6, QtWidgets.QTableWidgetItem(str(variable.param_value)))
                else:
                    self.variables_table.setItem(i, 6, QtWidgets.QTableWidgetItem(''))

                for j in range(self.variables_table.columnCount()):
                    item = self.variables_table.item(i, j)
                    if item is not None:
                        if isinstance(variable, NormalVariable) and not variable.used:
                            item.setBackground(QColor(38, 38, 38, 150))
                        if isinstance(variable, LoopVariable) and isinstance(variable, ParameterVariable):
                            item.setBackground(QColor(110, 90, 90, 150))

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
        variable = list(self.eqsys.variables.values())[row]
        if col == 1:
            variable.starting_guess = float(item.text())
        elif col == 2:
            variable.lower_bound = float(item.text())
        elif col == 3:
            variable.upper_bound = float(item.text())
        elif col == 7:
            variable.unit = str(item.text())

    def remove_unused_variables(self):
        self.sync_gui_and_eqsys()
        self.eqsys.remove_unused_variables()
        self.sync_gui_and_eqsys()

    def show_all_equations(self):
        self.sync_gui_and_eqsys()
        equations = [eq.string for eq in self.eqsys.equations]
        self.update_console_output(str(equations))

    def show_blocks(self):
        self.sync_gui_and_eqsys()
        try:
            blocks = blocking(self.eqsys)
            for block in blocks:
                eqs = [eq.string for eq in self.eqsys.equations if eq.id in block]
                string = f"eq ids: {str(block)}, eqs: {str(eqs)}"
                self.update_console_output(string)

        except Exception:
            error_message = "Solving eq sys failed with message: " + traceback.format_exc()
            self.update_console_output(error_message)

    def solve_eqsys(self):
        self.sync_gui_and_eqsys()
        try:
            self.solutions = solve(self.eqsys)
            # {i: (gridvals, solutions)}
            for entry in self.solutions.values():
                self.update_console_output('Loop var vals' + str(entry[0]) + '\nVariable solutions:')
                post = [k for k in entry[1].items()]
                self.update_console_output(str(post))

        except Exception:
            error_message = "Solving eq sys failed with message: " + traceback.format_exc()
            self.update_console_output(error_message)

    def update_guess_values(self):
        variables = self.eqsys.variables
        solutions = self.solutions
        for var in variables:
            if isinstance(variables[var], NormalVariable):
                variables[var].starting_guess = solutions[len(solutions)-1][1][var]

        self.sync_gui_and_eqsys()


