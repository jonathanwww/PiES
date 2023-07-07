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
from model.solver_interface import Solver
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
        self.solver = Solver(equation_system=self.model, results_manager=self.results)
        
        # set unit registry
        self.ureg = pint.UnitRegistry()
        self.model.set_ureg_validation(self.ureg)
                
        # set widgets in view and connect to signals        
        self._set_widgets()
        self._set_signals()

        # status flags for allowing solving
        self.compiled = False
        self.validated = False
        self.update_solve_button()  # So it's turned off at start
        self._refresh_gui()

    def _set_widgets(self):
        # init widgets
        self.variable_widget = VariableTableWidget(self.model, self.ureg, self.view)
        self.eqsys_widget = EquationSystemWidget(self.model, self.view)
        self.status_bar_widget = StatusBarWidget(self.model, self.view)
        self.plot_widget = InteractiveGraph(self.view)
        self.results_widget = ResultsWidget(self.results)
 
        # init editors
        self.console_output = ConsoleEditor(self.view)
        self.python_edit = PythonEditor(self.view)
        self.equation_edit = EquationEditor(self.view)
        
        # set widgets/editors to docks
        self.view.dock_manager.set_dock_widget('Results', self.results_widget)
        self.view.dock_manager.set_dock_widget('Variables', self.variable_widget)
        self.view.dock_manager.set_dock_widget('Eqsys', self.eqsys_widget)
        self.view.dock_manager.set_dock_widget('Plot', self.plot_widget)
        self.view.dock_manager.set_dock_widget('Python', self.python_edit)
        self.view.dock_manager.set_dock_widget('Output', self.console_output)

        self.view.setCentralWidget(self.equation_edit)
        self.view.status_bar.addPermanentWidget(self.status_bar_widget)

    def _set_signals(self):
        # refresh results widget when results manager changes 
        self.results.data_changed.connect(self.results_widget.update)
        
        # shows the status during solving
        self.solver.solve_status.connect(self.update_solving_status)
        
        # send errors from solving to console errors from solving
        self.solver.solve_error.connect(self.send_to_console)

        # editor text change
        self.equation_edit.textChangedSignal.connect(self.equation_editor_change)
        self.python_edit.textChangedSignal.connect(self.python_editor_change)

        # signal from top bar buttons
        self.view.solve_button.clicked.connect(self.run_solve)
        self.view.compile_button.clicked.connect(self.run_compile)
        self.view.validate_button.clicked.connect(self.run_validation)
        
        # variable table
        self.variable_widget.table_model.error.connect(self.view.show_error_message)  # when wrong input in variable table
        self.variable_widget.table_model.attribute_update.connect(self.model.variable_manager.update_variable)
        
        # when updating variable attribute
        self.model.variable_manager.attribute_updated.connect(self._attribute_updated)
        # on changes in py window or equation system, update widgets
        self.model.data_changed.connect(self._refresh_gui)
        
        # todo: should it just be on pressing compile? If we cant compile, delete grid/funcion units?
        # we cant solve though, since not compiled, but stats will show grids from previous compile hmm
        self.view.compile_button.clicked.connect(self._refresh_gui)
        self.view.validate_button.clicked.connect(self._refresh_gui)
        
    def _refresh_gui(self):
        # update status bar
        self.status_bar_widget.update_widget()

        # update eqsys widget
        self.eqsys_widget.update_widget()

        # update variables table
        self.variable_widget.updateData()

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
        
        self.view.set_light_color(self.view.validate_light, 'yellow')
        self.validated = False
        self.update_solve_button()
                
    def python_editor_change(self, text):
        self.view.set_light_color(self.view.compile_light, 'yellow')
        self.view.set_light_color(self.view.validate_light, 'yellow')
        self.compiled = False
        self.validated = False
        self.update_solve_button()

    # Triggers on button clicks in GUI
    def run_validation(self):
        val_results = self.model.validate_equation_system()
        
        # Check if eqsys was succesfully validated
        if self.model.valid:
            self.view.set_light_color(self.view.validate_light, 'green')
            self.validated = True
        else:
            self.view.set_light_color(self.view.validate_light, 'red')
            self.validated = False
            self.console_output.insert(str(val_results) + "\n")
            self.view.change_button_text('Output', 'Output (!)')
            self.view.change_button_text('Eqsys', 'Eqsys (!)')
        
        self.eqsys_widget.refresh_web_widget()
        self.update_solve_button()

    def run_compile(self):
        # TODO: we need to only run the last commands if nothing fails
        text = self.python_edit.text()
        code = str(text)
        namespace = {'__builtins__': __builtins__}
        try:
            compiled_code = compile(code, '<string>', 'exec')
            exec(compiled_code, namespace)
        except SyntaxError as e:
            self.console_output.insert(str(e) + "\n")
            self.view.change_button_text('Output', 'Output (!)')
            self.view.set_light_color(self.view.compile_light, 'red')
            return e
        except Exception as e:
            self.console_output.insert(f"Unexpected error: {traceback.format_exc()}" + "\n")
            self.view.change_button_text('Output', 'Output (!)')
            self.view.set_light_color(self.view.compile_light, 'red')
            return e
        else:
            del namespace['__builtins__']  # remove built-ins from the namespace

        # Look for functions which has units set
        func_units = {}
        
        for name, value in namespace.items():
            if isinstance(value, types.FunctionType):
                if hasattr(value, 'unit'):
                    unit_value = getattr(value, 'unit')
                    try:
                        self.ureg[unit_value]
                    except Exception as e:
                        self.console_output.insert(f"Cannot convert {unit_value} to a unit" + "\n")
                        self.view.change_button_text('Output', 'Output (!)')
                        self.view.set_light_color(self.view.compile_light, 'red')
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
                        self.console_output.insert("Grid does not match variables in equation system" + "\n")
                        self.view.change_button_text('Output', 'Output (!)')
                        self.view.set_light_color(self.view.compile_light, 'red')
                        raise Exception("Grid does not match variables in equation system")
                    break
            # There is an instance of the Grid class within the namespace
            self.view.change_solve_button_text(f"Solve: {len(self.model.grid.get_grid())} Runs")
        else:
            # There is no instance of the Grid class within the namespace
            self.view.change_solve_button_text("Solve: 1 Run")
        
        # if we pass everything
        self.compiled = True
        self.view.set_light_color(self.view.compile_light, 'green')
        self.update_solve_button()
        # todo: this might have to be moved depending on if we store old py on fail compile
        self.eqsys_widget.refresh_web_widget()

    def run_solve(self):
        self.solver_thread = SolverThread(self.solver)
        self.solver_thread.start()
    
    def update_solve_button(self):
        self.view.solve_button.setEnabled(self.compiled and self.validated)

    # Updates status bar with solving status: run 1/n, block ..
    def update_solving_status(self, message: str):
        # update status bar
        self.status_bar_widget.status_label.setText(message)
    
    def send_to_console(self, message: str):
        self.console_output.insert(message + "\n")
        # todo: make a system for setting the window alert also
        self.view.change_button_text('Output', 'Output (!)')
        