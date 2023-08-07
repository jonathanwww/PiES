import os
import qdarktheme
import pint
from PyQt6.QtWidgets import QWidget
from view.dock import DockManager
from view.menu import MenuManager
from view.window import MainWindow
from view.widgets.results import ResultsWidget
from view.widgets.graph import GraphWidget
from view.widgets.namespace import NamespaceWidget
from view.widgets.statusbar import StatusBarWidget
from view.widgets.topbar import TopBarWidget
from view.widgets.python import PythonWidget
from view.widgets.object_table import ObjectTableWidget
from view.widgets.plot import InteractiveGraph
from view.editor.editor import PythonEditor, FunctionsEditor, EquationEditor, ConsoleEditor
from eqsys.equationsystem import EquationSystem
from eqsys.solve.result import ResultsManager
from eqsys.solve.solver_interface import SolverInterface
from controller.controller import MainController, EquationSystemController
from configs.settings import SettingsManager
from resources.css import QSS


class MainApp(QWidget):

    def __init__(self):
        super().__init__()
        # todo: implement save eqsys and editor state
        # todo: implement saving configs with qsetting
        # todo: implmenet applying configs and theme
        
        # Settings
        settings_file = os.path.join(os.path.dirname(__file__), 'configs/default_settings.json')
        self.settings_manager = SettingsManager(settings_file)
        #self.settings_manager.load_settings()
        #self.settings_manager.settings_changed.connect(self.update_settings)
        
        # apply theme
        qdarktheme.setup_theme(additional_qss=QSS)
        
        self._setup_view()
        self._setup_model()
        self._setup_widgets()
        self._setup_controller()
        self._apply_settings()
        
        # load content in editor
        self.eqsys_controller.lines_manager.on_lines_changed()
        
    def update_settings(self):
        # Update your app's configs here

        # Update editor configs
        font_size = self.settings_manager.get_value('editor/font_size')
        font_family = self.settings_manager.get_value('editor/font_family')
        self.equation_edit.setFont(QFont(font_family, font_size))
        self.python_edit.setFont(QFont(font_family, font_size))

        # Update eqsys configs
        cache_size = self.settings_manager.get_value('eqsys/cache_size')
        self.model.cache_size = cache_size

    def _setup_view(self):
        # todo: requires general configs
        self.view = MainWindow()
        self.view.resize(1200, 800)

        self.view.dock_manager = DockManager(self.view)
        self.view.menu_manager = MenuManager(self.view)

    def _setup_model(self):
        # setup editors
        # todo: requires general configs, wrap, autocomplete etc        
        self.equation_edit = EquationEditor(self.view)
        self.namespace_edit = FunctionsEditor(self.view)
        self.python_edit = PythonEditor(self.view)
        self.console = ConsoleEditor(self.view)

        # todo: Needs eqsys configs: cache and ureg
        # setup eqsys
        self.ureg = pint.UnitRegistry()
        self.model = EquationSystem(self.ureg)
        
        # solver controller
        # todo: needs settings for float/scientific/digits
        self.results_manager = ResultsManager()
        # todo: Needs solver configs: Solver, residual, iterations etc
        self.solver_interface = SolverInterface(equation_system=self.model,
                                                results_manager=self.results_manager)
    
    def _setup_widgets(self):
        # widgets listen for changes in model/interface etc. and applies changes to objects directly from widget
        self.top_bar_widget = TopBarWidget(self.model, self.view)
        self.status_bar_widget = StatusBarWidget(self.solver_interface, self.view)
        
        self.view.top_toolbar.addWidget(self.top_bar_widget)
        self.view.status_bar.addWidget(self.status_bar_widget)
        self.view.setCentralWidget(self.equation_edit)
        
        # init widgets
        self.object_widget = ObjectTableWidget(self.model, self.view)
        self.namespace_widget = NamespaceWidget(self.model, self.namespace_edit, self.view)
        self.graph_widget = GraphWidget(self.model, self.view)
        self.plot_widget = InteractiveGraph(self.view)
        self.python_widget = PythonWidget(self.model, self.results_manager, self.python_edit, self.view)
        self.results_widget = ResultsWidget(self.model, self.results_manager, self.view)

        # set widgets/editors to docks
        self.view.dock_manager.set_dock_widget('Objects', self.object_widget)
        self.view.dock_manager.set_dock_widget('Namespace', self.namespace_widget)
        self.view.dock_manager.set_dock_widget('Graph', self.graph_widget)
        self.view.dock_manager.set_dock_widget('Results', self.results_widget)
        self.view.dock_manager.set_dock_widget('Plot', self.plot_widget)
        self.view.dock_manager.set_dock_widget('Script', self.python_widget)
        self.view.dock_manager.set_dock_widget('Output', self.console)

    def _setup_controller(self):
        self.eqsys_controller = EquationSystemController(equation_system=self.model,
                                                         equation_editor=self.equation_edit)
        self.controller = MainController(top_bar=self.top_bar_widget,
                                         status_bar=self.status_bar_widget,
                                         view=self.view,
                                         eqsys_controller=self.eqsys_controller,
                                         solver_interface=self.solver_interface)
        
    def _apply_settings(self):
        pass
    
    def run(self):
        self.view.show()

    # def save_state(self):
    #     state = {
    #         'eqsys': {
    #             'equations': self.eqsys.equations,
    #             'variables': self.eqsys.variables,
    #             'parameter_variables': self.eqsys.parameter_variables,
    #             'variable_counter': self.eqsys.variable_counter,
    #         },
    #         'editor': self.editor.text()
    #     }
    #     filename, _ = QtWidgets.QFileDialog.getSaveFileName(self.main_window, "Save State")
    #     if filename:
    #         with open(filename, 'wb') as file:
    #             pickle.dump(state, file)
    # 
    # 
    # def load_state(self):
    #     filename, _ = QtWidgets.QFileDialog.getOpenFileName(self.main_window, "Load State")
    #     if filename:
    #         with open(filename, 'rb') as file:
    #             state = pickle.load(file)
    #             self.eqsys.equations = state['eqsys']['equations']
    #             self.eqsys.variables = state['eqsys']['variables']
    #             self.eqsys.parameter_variables = state['eqsys']['parameter_variables']
    #             self.eqsys.variable_counter = state['eqsys']['variable_counter']
    #             self.editor.setText(state['editor'])
    