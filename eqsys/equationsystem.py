import ast
import networkx as nx
from ast import AST
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from pint import UnitRegistry
from eqsys.util import Counter
from eqsys.objects import Factory


class EquationManager(QObject):
    """
    object hiearchy (objects will be created in this order):
        namespace
        parameters
        variables
    """

    def __init__(self):
        super().__init__()
        self.namespace = {}

        self.factory = Factory()

        # count of objects
        self.object_counter = Counter()
        self.function_counter = Counter()

        self.object_counter.name_added.connect(self._add_variable)
        self.object_counter.name_removed.connect(self._remove_variable)
        self.function_counter.name_added.connect(self._add_function)
        self.function_counter.name_removed.connect(self._remove_function)

        # added from manager on insert
        self.equations = {}
        self.parameters = {}

        # added from counters when new counter is created
        self.variables = {}
        self.functions = {}
        
    @pyqtSlot(str)
    def _add_variable(self, variable_name):
        """ call factory to create a normal variable if name not in namespace and parameters """
        if variable_name not in (self.namespace or self.parameters):
            self.variables[variable_name] = self.factory.create_variable(variable_name)

    @pyqtSlot(str)
    def _add_function(self, function_name):
        """ call factory to create a function and add to functions, functions require no check since they are not part of the hiearchy """
        self.functions[function_name] = self.factory.create_function(function_name)

    @pyqtSlot(str)
    def _remove_variable(self, variable_name):
        """ if name in variables remove it. can potentially be an object in the namespace or a parameter """
        if variable_name in self.variables:
            del self.variables[variable_name]

    @pyqtSlot(str)
    def _remove_function(self, function_name):
        """ removes a function from functions. Technically the if exists should not be necessary """
        if function_name in self.functions:
            del self.functions[function_name]

    def sync_variables(self):
        # all potential variables
        object_names = set(self.object_counter.counter.keys())

        namespace_keys = set(self.namespace.keys())
        parameter_keys = set(self.parameters.keys())

        # all those which are not in parameters and namespace
        for variable_name in object_names - namespace_keys - parameter_keys:
            self._add_variable(variable_name)

        # all those which are in parameters or namespace
        for variable_name in object_names & (namespace_keys | parameter_keys):
            self._remove_variable(variable_name)
    
    def increase_counters(self, object_names: set, function_names: set) -> None:
        for object_name in object_names:
            self.object_counter.insert(object_name)

        for function_name in function_names:
            self.function_counter.insert(function_name)

    def decrease_counters(self, object_names: set, function_names: set) -> None:
        for object_name in object_names:
            self.object_counter.delete(object_name)

        for function_name in function_names:
            self.function_counter.delete(function_name)    

    def set_attr(self, object_name: str, object_type: str, attribute_name: str, value):
        # if object_name not in self.variables or not hasattr(self.variables[object_name], attribute_name):
        #    raise ValueError(f'Failed to update variable: attribute "{attribute_name}" is not a valid attribute')
        if object_type == "Variables":
            setattr(self.variables[object_name], attribute_name, value)
        elif object_type == "Parameters":
            setattr(self.parameters[object_name], attribute_name, value)
        elif object_type == "Functions":
            setattr(self.functions[object_name], attribute_name, value)
            
        # self.attribute_updated.emit(variable_name, attribute_name)
        # if attribute_name == 'unit':
        #     self.unit_updated.emit(variable_name)


class EquationSystem(QObject):
    data_changed = pyqtSignal()
    equation_error = pyqtSignal()
    equation_warning = pyqtSignal()
    equation_system_error = pyqtSignal()

    def __init__(self, ureg: UnitRegistry):
        super().__init__()
        # unit registry
        self.ureg = ureg

        # name space for functions, objects, constants, parameters
        self._namespace = {}

        # manages equations and objects in the equations
        self.eq_manager = EquationManager()

        # for accessing objects through equation system
        self.equations = self.eq_manager.equations
        self.variables = self.eq_manager.variables
        self.parameters = self.eq_manager.parameters
        self.functions = self.eq_manager.functions

    @property
    def namespace(self):
        return self._namespace

    @namespace.setter
    def namespace(self, value: dict) -> None:
        # todo: insert one item at a time?
        self._namespace.clear()
        self._namespace.update(value)
        self.eq_manager.namespace.clear()
        self.eq_manager.namespace.update(value)
        self.eq_manager.sync_variables()
        self._on_change()
    
    def insert_equation(self, equation: str, equation_tree: ast.Expression) -> None:
        """ an equation on the form lhs=rhs, the AST for that string"""
        equation_object = self.eq_manager.factory.create_equation(equation, equation_tree)
        self.eq_manager.equations[equation] = equation_object
        self.eq_manager.increase_counters(equation_object.objects, equation_object.functions)
        self._on_change()

    def insert_parameter(self, parameter_name: str, parameter_tree: ast.Assign) -> None:
        """ name of the parameter and the AST for value of the parameter: param=value """
        parameter = self.eq_manager.factory.create_parameter(parameter_name, parameter_tree)
        self.eq_manager.parameters[parameter_name] = parameter
        self.eq_manager.increase_counters(parameter.objects, parameter.functions)
        self.eq_manager.sync_variables()
        self._on_change()

    def delete_equation(self, name: str) -> None:
        object_names, function_names = self.eq_manager.equations[name].objects, self.eq_manager.equations[name].functions
        self.eq_manager.decrease_counters(object_names, function_names)
        del self.equations[name]
        self._on_change()

    def delete_parameter(self, name: str) -> None:
        object_names, function_names = self.eq_manager.parameters[name].objects, self.eq_manager.parameters[name].functions
        self.eq_manager.decrease_counters(object_names, function_names)
        del self.eq_manager.parameters[name]
        self.eq_manager.sync_variables()
        self._on_change()

    def _on_change(self):
        """ emits data_updated signal, validates eqsys and validate the list of eqs or all eqs if validate_all"""
        self.data_changed.emit()
    
    def blocking(self, return_graph=False):
        # Get eqs
        eqs = [eq for eq in self.equations.values()]

        # Get nodes
        eq_nodes = [eq.equation for eq in eqs]
        var_nodes = list(self.variables.keys())

        # Bipartite graph
        B = nx.Graph()
        B.add_nodes_from(eq_nodes, bipartite=0)
        B.add_nodes_from(var_nodes, bipartite=1)
        B.add_edges_from([(eq.equation, var) for eq in eqs for var in eq.objects if var in self.variables])

        # Matching; associate one variable with one equation
        matching = nx.algorithms.bipartite.hopcroft_karp_matching(B, top_nodes=eq_nodes)  # todo: contains both ways, remove one

        # Directed graph
        DG = nx.DiGraph()
        DG.add_nodes_from(eq_nodes)

        for eq, var in matching.items():
            shared_equations = [eq.equation for eq in self.equations.values() if var in eq.objects]
            for shared_eq in shared_equations:
                DG.add_edge(eq, shared_eq)

        # Remove self loops
        DG.remove_edges_from(nx.selfloop_edges(DG))

        sccs = list(nx.strongly_connected_components(DG))
        sccs.reverse()

        if return_graph:
            return sccs, DG
        else:    
            return sccs
