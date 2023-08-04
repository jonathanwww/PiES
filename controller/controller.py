from PyQt6.QtCore import QObject, pyqtSlot
from view.window import MainWindow
from view.editor.editor import EquationEditor
from eqsys.equationsystem import EquationSystem
from eqsys.solve.solver_interface import SolverInterface
from controller.util import SolverThread
from controller.error import ErrorHandler
from controller.lines import LinesManager


class EquationSystemController(QObject):
    """
    Handles the communication between the editor and the equation system
    Error_handler sets indicators in editors 
    """

    def __init__(self,
                 equation_system: EquationSystem,
                 equation_editor: EquationEditor,
                 parent=None):
        super().__init__(parent)

        # connect lines manager to equation system
        self.equation_system = equation_system
        self.equation_editor = equation_editor
        self.lines_manager = LinesManager(self.equation_editor)
        
        self.lines_manager.add_equation.connect(self.equation_system.insert_equation)
        self.lines_manager.remove_equation.connect(self.equation_system.delete_equation)

        self.lines_manager.add_parameter.connect(self.equation_system.insert_parameter)
        self.lines_manager.remove_parameter.connect(self.equation_system.delete_parameter)
        
        # setup equation error handling
        # self.error_handler = ErrorHandler(self.equation_editor)
        # 
        # # connect errors and warnings to error handler
        # self.equation_system.warning.connect(self.error_handler.set_indicator)  # unit operation warnings
        # self.equation_system.error.connect(self.error_handler.set_indicator)  # undefined functions, duplicate parameters and grid errors todo move grid errors since its pyW?
        # self.equation_editor.lexer.error.connect(self.error_handler.set_indicator)  # unexpected character and token errors
        # self.lines_manager.error.connect(self.error_handler.set_indicator)  # duplicate lines
    

class MainController(QObject):
    """handles communication between buttons/status bar and solving thread"""

    def __init__(self,
                 top_bar,
                 status_bar,
                 view: MainWindow,
                 eqsys_controller: EquationSystemController,
                 solver_interface: SolverInterface):

        super().__init__()
        self.top_bar = top_bar
        self.status_bar = status_bar
        self.view = view
        self.eqsys_controller = eqsys_controller
        self.solver_interface = solver_interface
        
        # signal from top bar buttons
        self.top_bar.solve_button.clicked.connect(self.run_solve)
        self.top_bar.stop_button.clicked.connect(self.stop_solve)

        # todo: add output from solver
        # send errors in solving to console
        self.solver_interface.solve_error.connect(self.view.console_message)
        
        # disable stop button
        self.top_bar.stop_button.setEnabled(False)

    @pyqtSlot()
    def run_solve(self):
        self.status_bar.start_timer()
        self.top_bar.solve_button.setEnabled(False)
        self.top_bar.stop_button.setEnabled(True)
        
        self.solver_thread = SolverThread(self.solver_interface)
        # signals from solver thread
        self.solver_thread.finished.connect(self.status_bar.stop_timer)
        self.solver_thread.finished.connect(self.enable_solve_button)
        
        self.solver_thread.start()
    
    def enable_solve_button(self):
        self.top_bar.solve_button.setEnabled(True)
        self.top_bar.stop_button.setEnabled(False)
        
    @pyqtSlot()
    def stop_solve(self):
        # todo: not working
        self.solver_thread.exit()
        print('thread ended')
