import traceback

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt 
from PyQt6.QtWidgets import QWidget

from logic.equationsystem import EquationSystem, solve
from logic.util import blocking

import re
from PyQt6.QtGui import QTextCharFormat, QSyntaxHighlighter, QColor, QFont


class EquationHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(93, 179, 231))
        keywords = ['=', 'gen_eqs']
        self.keyword_patterns = [re.compile(r""+keyword) for keyword in keywords]

        self.red_format = QTextCharFormat()
        self.red_format.setBackground(QColor(230, 101, 101))
        self.red_pattern = re.compile(r"^[^=]+$|^=|=$")

    def highlightBlock(self, text):
        for pattern in self.keyword_patterns:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)

        for match in self.red_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.red_format)


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(93, 179, 231))
        keywords = ["and", "as", "assert", "break", "class", "continue", "def", "del", "elif", "else", "except", "False", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "None", "not", "or", "pass", "raise", "return", "True", "try", "while", "with", "yield"]
        self.keyword_patterns = [re.compile(r"\b" + keyword + r"\b") for keyword in keywords]

        self.patterns = []

    def highlightBlock(self, text):
        for pattern in self.keyword_patterns:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)


class Editor(QWidget):
    def __init__(self, eqsys: EquationSystem):
        super().__init__()
        self.eqsys = eqsys
        self.status_label = QtWidgets.QLabel(self)

        self.python_edit = QtWidgets.QTextEdit(self)
        self.python_edit_highlighter = PythonHighlighter(self.python_edit.document())
        
        self.text_edit = QtWidgets.QTextEdit(self)
        self.text_edit_highlighter = EquationHighlighter(self.text_edit.document())
        
        self.console_output = QtWidgets.QTextEdit(self)
        self.console_output.setReadOnly(True)
        
        self.variables_table = QtWidgets.QTableWidget(self)
        self.variables_table.setColumnCount(7)
        self.variables_table.setHorizontalHeaderLabels(["Name", "x0", "Lower b", "Upper b", "Used", "Loopvar", "Paramvar"])
        self.variables_table.cellChanged.connect(self.update_variable)
        self.variables_table.horizontalHeader().sectionClicked.connect(self.sort_table)

        for col in range(self.variables_table.columnCount()):
            self.variables_table.setColumnWidth(col, 65)

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
        
        self.layout = QtWidgets.QGridLayout(self)
        self.layout.addWidget(self.python_edit, 0, 0)
        self.layout.addWidget(self.text_edit, 0, 1)
        self.layout.addWidget(self.variables_table, 0, 2)
        
        self.layout.addWidget(self.console_output, 1, 0, 1, 3)
        
        self.layout.addWidget(self.remove_unused_vars_button, 2, 0)
        self.layout.addWidget(self.show_all_eqs_button, 3, 0)
        self.layout.addWidget(self.show_blocks_button, 4, 0)
        self.layout.addWidget(self.solve_button, 2, 1)
        self.layout.addWidget(self.clear_console_button, 3, 1)
        self.layout.addWidget(self.status_label, 4, 1)
        
        self.layout.setColumnStretch(0, 2)
        self.layout.setColumnStretch(1, 3)
        self.layout.setColumnStretch(2, 3)

        self.layout.setRowStretch(0, 2)
        self.layout.setRowStretch(1, 1)

        font = QFont("monaco", 12)
        self.python_edit.setFont(font)
        self.text_edit.setFont(font)
        self.console_output.setFont(font)
        
        self.initUI()
        self.sync_gui_and_eqsys()
        
    def initUI(self):
        self.python_edit.setText("from numpy import cos, sin\nfrom CoolProp.CoolProp import PropsSI\n\ndef test(x,y,str_input):\n return x+y if str_input == 'add' else 0")
        self.text_edit.setText("# Example of equation generator\ngen_eqs([f'x_{i}+cos(5*{i})=12*{i}+w' for i in range(10)])\n\n# Example of loop variable\na=loop_var([i*2+1 for i in range(1)])\ny=loop_var([i+1 for i in range(1)])\n\nx = 6*w \nz = x*y \nw = z*x+test(x,z,'add') \nb = 4*a \nc = a*b")
        self.setGeometry(1350, 800, 1350, 750)
        self.setWindowTitle('freese')
        self.show()
        
    def sort_table(self, column):
        self.variables_table.sortItems(column)
        
    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key.Key_Return:
            self.sync_gui_and_eqsys()
        
    def sync_gui_and_eqsys(self):  # syncs the equation system object with the ui input
        try:
            # gets the code from python window
            text = self.text_edit.toPlainText()
            code = self.python_edit.toPlainText()
    
            # update eqsys with input from windows
            self.eqsys.update_eqsys(text, code)
            
            # update status bar
            vars_in_use = len([var for var in self.eqsys.variables if var.used])
            self.status_label.setText(f'{"[✓]" if vars_in_use == len(self.eqsys.equations) else "[x]"} '
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
                    color = QColor(0, 0, 0)
                    if not variable.used:
                        color = QColor(38, 38, 38)
                    if variable.loop_var and variable.param_var:
                        color = QColor(110, 90, 90)
                    self.variables_table.item(i, j).setBackground(color)
                
                # color columns           
                if variable.loop_var:
                    color = QColor(109, 115, 108)
                    self.variables_table.item(i, 5).setBackground(color)
                if variable.param_var:
                    color = QColor(109, 110, 98)
                    self.variables_table.item(i, 6).setBackground(color)
                        
        except Exception:
            error_message = "Updating eq sys failed with message: " + traceback.format_exc()
            self.update_console_output(error_message)
    
    def clear_console(self):
        self.console_output.setPlainText("")
        
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
