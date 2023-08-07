from PyQt6.QtWidgets import QApplication, QStyle, QSizePolicy, QMainWindow, QToolBar, QPushButton, QPlainTextEdit, QWidget, QVBoxLayout, QTabWidget, QMenu, QWidgetAction, QLabel, QHBoxLayout, QVBoxLayout, QSplitter, QToolButton
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPalette, QAction, QPixmap, QPainter
from PyQt6.QtWidgets import QSpacerItem
from PyQt6.QtCore import pyqtSlot


class EquationSystemInfoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create elements
        self.layout = QHBoxLayout(self)
        self.light = QLabel()
        self.light.setAutoFillBackground(True)

        # Create labels and their layout
        self.label_layout = QVBoxLayout()
        self.name_label = QLabel("Equation System DOF: 0")
        self.label_layout.addWidget(self.name_label)

        # Create a QToolButton and use its arrow down icon
        self.arrow_icon = QToolButton(self)
        self.arrow_icon.setStyleSheet("border: none;")
        self.arrow_icon.setArrowType(Qt.ArrowType.DownArrow)

        # Add light and labels layout to main layout
        self.layout.addWidget(self.light)
        self.layout.addLayout(self.label_layout)
        self.layout.addWidget(self.arrow_icon)

        # Set initial light color
        self.change_light_color(Qt.GlobalColor.green)

        # Create labels for the attributes
        self.equations_label = QLabel("Equations: ")
        self.variables_label = QLabel("Variables: ")
        self.parameters_label = QLabel("Parameters: ")
        self.functions_label = QLabel("Functions: ")

        self.error_display = QPlainTextEdit()
        self.warning_display = QPlainTextEdit()
        self.error_display.setReadOnly(True)
        self.warning_display.setReadOnly(True)

    def change_light_color(self, color):
        # Change the background color of the light label
        self.light.setStyleSheet(f"background-color: {QColor(color).name()}")

    def mousePressEvent(self, event):
        # Open the tab widget on mouse press
        self.open_tab_widget()

    def open_tab_widget(self):
        self.splitter = QSplitter()
        self.label_widget = QWidget()
        self.label_layout = QVBoxLayout()

        # Add attribute labels to the layout
        self.label_layout.addWidget(self.equations_label)
        self.label_layout.addWidget(self.variables_label)
        self.label_layout.addWidget(self.parameters_label)
        self.label_layout.addWidget(self.functions_label)

        self.label_widget.setLayout(self.label_layout)
        self.splitter.addWidget(self.label_widget)

        # Create a QTabWidget for the tabs
        self.tab_widget = QTabWidget()

        self.tab_widget.addTab(self.error_display, f"Errors")
        self.tab_widget.addTab(self.warning_display, f"Warnings")
        self.splitter.addWidget(self.tab_widget)

        self.popup_menu = QMenu(self)

        # Add the QSplitter to the menu
        widget_action = QWidgetAction(self.popup_menu)
        widget_action.setDefaultWidget(self.splitter)
        self.popup_menu.addAction(widget_action)

        # Open the menu below the widget
        self.popup_menu.popup(self.mapToGlobal(QPoint(0, self.height())))


class TopBarWidget(QWidget):
    def __init__(self, eqsys, parent=None):
        super().__init__(parent)
        
        self.eqsys = eqsys
        # signals from equation system
        self.eqsys.data_changed.connect(self.update_labels)
        
        # Create a layout for the top bar
        self.layout = QHBoxLayout(self)

        # Create the equation system info widget
        self.eq_info_widget = EquationSystemInfoWidget()
        self.layout.addWidget(self.eq_info_widget)
        
        # Add a spacer to push subsequent widgets to the right
        self.layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Add the solve button and labelx4
        self.solve_button = QPushButton('Solve')
        pixmapi = QStyle.StandardPixmap.SP_MediaPlay
        
        icon = self.style().standardIcon(pixmapi)
        self.solve_button.setIcon(QIcon(icon))
        self.solve_button.setObjectName("solveButton")

        self.solve_runs_label = QLabel('1 run')
        self.solve_runs_label.setObjectName("solveLabel")

        self.layout.addWidget(self.solve_runs_label)
        self.layout.addWidget(self.solve_button)

        # Add the solve button and labelx4
        self.stop_button = QPushButton()
        pixmapi = QStyle.StandardPixmap.SP_MediaStop
        icon = self.style().standardIcon(pixmapi)
        self.stop_button.setIcon(QIcon(icon))
        self.stop_button.setObjectName("stopButton")
        self.layout.addWidget(self.stop_button)
        
        # Add the tool button
        self.toolButton = QToolButton(self)
        pixmap = QPixmap(3, 15)
        pixmap.fill(self.palette().color(self.backgroundRole()))
        painter = QPainter(pixmap)
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.setBrush(self.palette().color(self.foregroundRole()))
        painter.drawEllipse(0, 0, 3, 3)
        painter.drawEllipse(0, 6, 3, 3)
        painter.drawEllipse(0, 12, 3, 3)
        painter.end()
        icon = QIcon(pixmap)
        self.toolButton.setIcon(icon)
        self.toolButton.setObjectName("solverSettingsButton")
        self.toolButton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.toolButton.setStyleSheet('QToolButton::menu-indicator { image: none; }')
        
        self.menu = QMenu(self)

        # Add 'Selected solver' action to the main menu
        self.selected_solver_action = QAction('Solver: Newton-Raphson', self.menu)
        self.selected_solver_action.setEnabled(False) # to make it non-interactive
        self.menu.addAction(self.selected_solver_action)
        
        # Add 'Edit solver' to the main menu
        self.menu.addAction(QAction('    Edit', self.menu))
        
        # Create a sub-menu for 'Select solver'
        self.solverMenu = QMenu('Change solver', self)

        # Add actions to the 'Select solver' sub-menu
        self.add_solver('Newton')
        self.add_solver('mse')
        self.add_solver('test')

        # Add 'Select solver' sub-menu to the main menu
        self.menu.addMenu(self.solverMenu)

        # Add a separator to create space before 'Transform residual'
        self.menu.addSeparator()

        # Add 'Transform residual' to the main menu
        self.menu.addAction(QAction('Transform residual', self.menu))

        self.toolButton.setMenu(self.menu)
        self.layout.addWidget(self.toolButton)
    
    def add_solver(self, name):
        action = QAction(name, self.solverMenu)
        action.triggered.connect(lambda: self.set_solver(name))
        self.solverMenu.addAction(action)

    def set_solver(self, name):
        self.selected_solver_action.setText(f'Solver: {name}')
        
    @pyqtSlot()
    def update_labels(self):
        self.eq_info_widget.error_display.clear()
        self.eq_info_widget.warning_display.clear()
        
        # error = self.eqsys.errors
        # warnings = self.eqsys.warnings
        
        equations = len(self.eqsys.equations)
        variables = len(self.eqsys.variables)
        parameters = len(self.eqsys.parameters)
        functions = len(self.eqsys.functions)
        
        self.eq_info_widget.equations_label.setText(f"Equations: {equations}")
        self.eq_info_widget.variables_label.setText(f"Variables: {variables}")
        self.eq_info_widget.parameters_label.setText(f"Parameters: {parameters}")
        # self.eq_info_widget.grid_label.setText(f"Grid: {grid_vars}")
        self.eq_info_widget.functions_label.setText(f"Functions: {functions}")

        # DoF is equations - (variables-grid) - parameters already have their own equation
        dof = variables - equations
        if dof > 0:
            self.eq_info_widget.name_label.setText(f"Equation System DOF: {dof} (UD)")
        elif dof < 0:
            self.eq_info_widget.name_label.setText(f"Equation System DOF: {dof} (OD)")
        else:
            self.eq_info_widget.name_label.setText(f"Equation System DOF: {dof}")

        # if len(error) != 0:  # add errors
        #     self.eq_info_widget.change_light_color('red')
        #     for key, value in error.items():
        #         self.eq_info_widget.error_display.insertPlainText(f'{key}\n{value}\n\n')
        # elif dof == 0:
        #     self.eq_info_widget.change_light_color('green')
        # elif dof > 0 or dof < 0:  # possibly over/under determined
        #     self.eq_info_widget.change_light_color('yellow')
        # 
        # if len(warnings) != 0:  # add unit warnings
        #     for key, value in warnings.items():
        #         self.eq_info_widget.warning_display.insertPlainText(f'{key}\n{value}\n\n')
        #         self.eq_info_widget.change_light_color('yellow')
        grid_len = len(self.eqsys.grid.get_grid())
        self.refresh_solve_button(grid_len)

    def refresh_solve_button(self, runs: int):
        if runs == 1:
            message = "1 Run"
        else:
            message = f"{runs} Runs"
        self.solve_runs_label.setText(message)
        # set enabled/disabled if equation system is valid
        # self.solve_button.setEnabled(enabled)

    def set_light_color(self, status: int):
        if status == -1:
            color_name = 'red'
        elif status == 0:
            color_name = 'yellow'
        elif status == 1:
            color_name = 'green'
        self.validate_light.setStyleSheet(f"background-color: {color_name};")
        self.validate_light.update()