import types
import traceback
import pint
from lark import UnexpectedCharacters, UnexpectedToken
from PyQt6.QtCore import QObject
from ui.window import MainWindow
from ui.widgets.results import ResultsWidget
from ui.widgets.variabletable import VariableTableWidget 
from ui.widgets.equationsystem import EquationSystemWidget
from ui.widgets.statusbar import StatusBarWidget
from ui.widgets.plot import InteractiveGraph
from ui.widgets.editor import PythonEditor, EquationEditor, ConsoleEditor
from model.solver_interface import SolverInterface
from model.util import Grid
from model.equationsystem import EquationSystem
from model.variable import Variable
from model.equation import Equation
from validation.validation import EquationTransformer
from controller.util import SolverThread
from model.result import ResultsManager


class MainController(QObject):
    def __init__(self, eqsys: EquationSystem, view: MainWindow):
        super().__init__()
        self.model = eqsys
        self.view = view

        self.results = ResultsManager()
        self.solver_intf = SolverInterface(equation_system=self.model, results_manager=self.results)
        
        # set unit registry
        self.ureg = pint.UnitRegistry()
        self.model.set_ureg_validation(self.ureg)
                
        # set widgets in view and connect to signals        
        self._set_widgets()
        self._set_signals()

        # status flags for allowing solving
        self.compiled = False
        self.validated = False
        
        # Make sure buttons turned off, widgets refreshed etc
        self._on_start()

    def _set_widgets(self):
        # init widgets
        self.variable_widget = VariableTableWidget(self.model, self.ureg, self.view)
        self.eqsys_widget = EquationSystemWidget(self.model, self.view)
        self.status_bar_widget = StatusBarWidget(self.model, self.solver_intf, self.view)
        self.plot_widget = InteractiveGraph(self.view)
        self.results_widget = ResultsWidget(self.results, self.view)
 
        # init editors
        self.console = ConsoleEditor(self.view)
        self.python_edit = PythonEditor(self.view)
        self.equation_edit = EquationEditor(self.view)
        
        # set widgets/editors to docks
        self.view.dock_manager.set_dock_widget('Results', self.results_widget)
        self.view.dock_manager.set_dock_widget('Variables', self.variable_widget)
        self.view.dock_manager.set_dock_widget('Eqsys', self.eqsys_widget)
        self.view.dock_manager.set_dock_widget('Plot', self.plot_widget)
        self.view.dock_manager.set_dock_widget('Python', self.python_edit)
        self.view.dock_manager.set_dock_widget('Output', self.console)
        
        # set central widget and status bar
        self.view.setCentralWidget(self.equation_edit)
        self.view.status_bar.addPermanentWidget(self.status_bar_widget)

    def _set_signals(self):        
        # editor text change
        self.equation_edit.textChangedSignal.connect(self.equation_editor_change)
        self.python_edit.textChangedSignal.connect(self.python_editor_change)

        # signal from top bar buttons
        self.view.solve_button.clicked.connect(self.run_solve)
        self.view.compile_button.clicked.connect(self.run_compile)
        self.view.validate_button.clicked.connect(self.run_validation)
        
        # TODO: on unit change, revalidate, on compile, revalidate (function units, maybe also grid?)
        # when updating variable attribute
        self.model.variable_manager.attribute_updated.connect(self._attribute_updated)
        
        # send errors in solving to console
        self.solver_intf.solve_error.connect(self.console_message)
    
    def _on_start(self):
        self.refresh_solve_button()
        
    def _attribute_updated(self, variable_name, attribute_name):
        """
        if changing unit revalidate equations with that variable 
        """
        if attribute_name == 'unit':
            for eq in self.model.equations.values():
                if variable_name in eq.variables:
                    line_num = int(eq.id)  # only works because we save eqs with line num
                    # remove line warnings from dictionary
                    if line_num in self.equation_edit.warnings: 
                        del self.equation_edit.warnings[line_num]
                    # clear line of warnings
                    self.equation_edit.clearIndicatorRange(line_num, 0, line_num, self.equation_edit.lineLength(line_num), self.equation_edit.warning_indicator)
                    results = self.model.validate_equation(eq.id)
                    if results:
                        self.equation_edit.set_indicator(line_num, 0, 0, str(results), False)

    def refresh_solve_button(self):
        self.view.solve_button.setEnabled(self.compiled and self.validated)

    def update_status(self, status, light):
        if light == 'validate':
            light = self.view.validate_light
            if status == -1 or 0:
                self.validated = False
            elif status == 1:
                self.validated = True

        elif light == 'compile':
            light = self.view.compile_light
            if status == -1 or 0:
                self.compiled = False
            elif status == 1:
                self.compiled = True

        if status == -1:
            self.view.set_light_color(light, 'red')
        elif status == 0:
            self.view.set_light_color(light, 'yellow')
        elif status == 1:
            self.view.set_light_color(light, 'green')

        self.refresh_solve_button()
    
    def console_message(self, message: str, widget_alerts=None):
        # send message to console and update console button with alert
        self.console.insert(message)
        self.view.change_button_text('Output', 'Output (!)')
        
        if widget_alerts is not None:
            # If widget_alerts is a string, convert it into a list.
            if not isinstance(widget_alerts, list):
                widget_alerts = [widget_alerts]
    
            for alert in widget_alerts:
                self.view.change_button_text(alert, f'{alert} (!)')

    # Triggers on text change in the editors
    def equation_editor_change(self, text):        
        # Empty eqsys
        for eq in list(self.model.equations.values()):
            self.model.delete_equation(eq.id)

        # empty warnings in eq editor
        self.equation_edit.warnings = {}

        # add all lines if they can parse
        current_text = text.split()

        for i, line in enumerate(current_text):
            # clear this line of warnings
            self.equation_edit.clearIndicatorRange(i, 0, i, self.equation_edit.lineLength(i), self.equation_edit.warning_indicator)
            try:
                eq_tree = self.equation_edit.parser.parse(line)
                
                # find equation and variables 
                eqtransform = EquationTransformer()
                variable_names, function_names = eqtransform.validate(eq_tree)
                
                # check for unit errors
                
                # create objects
                unique_id = str(i)  # line number as id for now
                equation = Equation(eq_id=unique_id,
                                    equation=line,
                                    variables=list(variable_names),
                                    functions=list(function_names),
                                    tree=eq_tree)

                variables = []
                for variable_name in variable_names:
                    # only add variables which are not present in eqsys
                    if variable_name not in self.model.variables:
                        unit = self.ureg.dimensionless  # set basic unit
                        variables.append(Variable(name=variable_name, unit=unit))

                # insert equation and variables
                self.model.insert_equation(equation, variables)
                results = self.model.validate_equation(unique_id)

                if results:
                    self.equation_edit.set_indicator(i, 0, 0, str(results), False)
            except (UnexpectedCharacters, UnexpectedToken) as e:
                # continue to next line
                pass

        self.update_status(0, 'validate')     
 
    def python_editor_change(self, text):
        self.update_status(0, 'validate')
        self.update_status(0, 'compile')

    # Triggers on button clicks in GUI
    def run_solve(self):
        self.solver_thread = SolverThread(self.solver_intf)
        self.solver_thread.start()
        
    def run_validation(self):
        val_results = self.model.validate_equation_system()
        
        # Check if eqsys was succesfully validated
        if self.model.valid:
            self.update_status(1, 'validate')
        else:
            self.update_status(-1, 'validate')
            
            message = str(val_results)
            self.console_message(message, 'Eqsys')
            
        self.eqsys_widget.refresh_web_widget()

    def run_compile(self):
        # TODO: we need to only run the last commands if nothing fails
        text = self.python_edit.text()
        code = str(text)
        namespace = {}
        
        try:
            compiled_code = compile(code, '<string>', 'exec')
            exec(compiled_code, namespace)
        except SyntaxError as e:
            self.console_message(str(e))
            self.update_status(-1, 'compile')
            return e
        except Exception as e:
            message = f"Unexpected error: {traceback.format_exc()}"
            self.console_message(message)

            self.update_status(-1, 'compile')
            return e
        
        del namespace['__builtins__']  # remove built-ins from the namespace
        
        self.solver_intf.set_namespace(namespace)
        
        func_units = {}
        
        for name, value in namespace.items():
            if isinstance(value, types.FunctionType):
                if hasattr(value, 'unit'):
                    unit_value = getattr(value, 'unit')
                    try:
                        self.ureg[unit_value]
                    except Exception as e:
                        message = f"Cannot convert {unit_value} to a unit"
                        self.console_message(message)
                        self.update_status(-1, 'compile')
                        
                    func_units[name] = unit_value
               
        # add to eqsys if we can convert
        self.model.function_units = func_units
                    
        # check if grid is valid
        if any(isinstance(obj, Grid) for obj in namespace.values()):
            # Find the Grid instance within the namespace
            for obj in namespace.values():
                if isinstance(obj, Grid):
                    valid_grid = self.model.validate_grid(obj)
                    
                    if valid_grid:
                        self.model.set_grid(obj)
                    else:
                        message = "Grid does not match variables in equation system or is overlapping parameter variable"
                        self.console_message(message)
                        self.update_status(-1, 'compile')
                        raise Exception("Grid does not match variables in equation system or is overlapping parameter variable")
                    break
            # There is an instance of the Grid class within the namespace
            self.view.change_solve_button_text(f"Solve: {len(self.model.grid.get_grid())} Runs")
        else:
            # There is no instance of the Grid class within the namespace
            self.view.change_solve_button_text("Solve: 1 Run")
        
        # if we pass everything
        self.update_status(1, 'compile')
