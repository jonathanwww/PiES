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
from model.equationsystem import EquationSystem
from model.variable import Variable
from model.equation import Equation
from validation.validation import EquationTransformer
from controller.util import check_grid, get_grid, check_function_units, get_function_units, SolverThread
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
        
        # when updating variable attribute
        self.model.variable_manager.attribute_updated.connect(self.attribute_updated)

        # X0 from results manager
        self.results_widget.update_starting_guess.connect(self.update_starting_guess)
        
        # send errors in solving to console
        self.solver_intf.solve_error.connect(self.console_message)
    
    def _on_start(self):
        # todo: fininsh, should load the text etc into eqsys
        self.refresh_solve_button()
        
    def func_unit_updated(self):
        # todo: revalidate all equations which has that func unit
        pass
    
    def attribute_updated(self, variable_name, attribute_name):
        # if changing unit revalidate equations with that variable 
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

    def update_starting_guess(self, variable_dict):
        # Check if all keys are present in the dict self.model.variables
        missing_variables = [key for key in variable_dict if key not in self.model.variables]
        
        # warning about missing variables
        if missing_variables:
            self.view.show_error_message(f"The following variables are not present in the equation system: {missing_variables}")
        
        # insert starting guesses
        for variable, value in variable_dict.items():
            if variable in self.model.variables and variable:
                # do not update starting guess for parameters and grid variables
                if variable not in self.model.grid.variables and variable not in self.model.parameter_variables:
                    self.model.variable_manager.update_variable(variable, 'starting_guess', value)
            
    def refresh_solve_button(self):
        # update number of runs
        grid_len = len(self.model.grid.get_grid())
        if grid_len == 1:
            message = "Solve: 1 Run"
        else:
            message = f"Solve: {grid_len} Runs"
        self.view.change_solve_button_text(message)
        
        # set enabled/disabled if compiled and validated
        print(self.compiled, self.validated)
        self.view.solve_button.setEnabled(self.compiled and self.validated)
        
    def update_status(self, status, light):
        print(status)
        if light == 'validate':
            light = self.view.validate_light
            if status in [-1, 0]:
                self.validated = False
            elif status == 1:
                self.validated = True

        elif light == 'compile':
            light = self.view.compile_light
            if status in [-1, 0]:
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
        # TODO: should we clear grid/funcunits/namespace if failing compile?
        text = self.python_edit.text()
        code = str(text)
        namespace = {}

        # try to compile the code
        try:
            compiled_code = compile(code, '<string>', 'exec')
            exec(compiled_code, namespace)
        except (SyntaxError, Exception) as e:
            if isinstance(e, SyntaxError):
                compile_error = str(e)
            else:
                compile_error = f"Unexpected error: {traceback.format_exc()}"
            self.console_message(compile_error)
            self.update_status(-1, 'compile')
            return
        
        # check if function units has valid unit
        func_units = get_function_units(namespace)
        if func_units:
            unit_errors = check_function_units(func_units, self.ureg)
        else:
            unit_errors = None
            
        # check if grid is valid
        grid = get_grid(namespace)
        if grid:
            grid_errors = check_grid(grid, self.model)
        else:
            grid_errors = None
        
        # set data and update status
        if not (grid_errors or unit_errors):
            del namespace['__builtins__']
            
            self.solver_intf.set_namespace(namespace)
            self.model.set_function_units(func_units)
            self.model.set_grid(grid)
            
            self.update_status(1, 'compile')
        else:
            for message in grid_errors + unit_errors:
                self.console_message(message)
            self.update_status(-1, 'compile')
        
