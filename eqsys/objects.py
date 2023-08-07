import ast
import numpy as np
from types import CodeType
from PyQt6.QtCore import QObject
from ast import AST
from pint import Unit
from eqsys.util import LRUCache, NameCollector, CreateResidual


class Equation:
    """
    Equation is lhs=rhs, residual is lhs-rhs
    Residual tree is used for unit validation, residual code is used in the residual function 
    """
    def __init__(self,  
                 equation: str,
                 residual_tree: AST,
                 residual_code: CodeType,
                 object_names: set[str],
                 function_names: set[str]):
        
        self.equation = equation
        self.tree = residual_tree,
        self.residual = residual_code

        self.objects = object_names
        self.functions = function_names

    def __repr__(self):
        return f"Equation(name={self.equation}, tree=residual_tree, residual=code, objects={self.objects}, functions={self.functions})"

    def __str__(self):
        return f"{self.equation}"


class Parameter:
    """
    # todo: make a system for setting type
    tree is for the complete assignment
    name is lhs of assignment
    value is the compiled rhs of the assignment
    object names contains the name of the parameter
    must be of type: 
        numeric value
        string
        or a list of any of those
    """

    def __init__(self, 
                 name: str,
                 tree: AST,
                 value_code: CodeType,
                 object_names: set[str], 
                 function_names: set[str],
                 unit: Unit = None):
        
        self.name = name
        self.tree = tree
        self.code = value_code
        self.objects = object_names
        self.functions = function_names
        self.unit = unit
        
        self._grid = False
        
    def __repr__(self):
        return f"Parameter(name={self.name}, tree=tree, code=rhs, objects={self.objects}, " \
               f"functions={self.functions}, unit={self.unit}, grid={self.grid})"
    
    def __str__(self):
        return f"{self.name}"
    
    @property
    def grid(self):
        return self._grid

    @grid.setter
    def grid(self, status: bool):
        self._grid = status


class Variable:
    def __init__(self, 
                 name: str,
                 starting_guess: int | float | complex = 1,
                 lower_bound: int | float | complex = -np.inf,
                 upper_bound: int | float | complex = np.inf,
                 unit: Unit = None):

        self._name = name
        self.starting_guess = starting_guess
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.unit = unit

    def __repr__(self) -> str:
        return f'Variable(name={self._name}, x0={self.starting_guess}, lb={self.lower_bound}, ub={self.upper_bound}, unit={self.unit})'
    
    def __str__(self):
        return f"{self._name}"
    
    @property
    def name(self) -> str:
        return self._name


class Function:
    def __init__(self, 
                 name: str, 
                 unit: Unit = None):
        
        self.name = name
        self.unit = unit

    def __repr__(self) -> str:
        return f'Function(name={self.name}, unit={self.unit})'

    def __str__(self):
        return f"{self.name}"


class Factory(QObject):
    """ 
    Returns the object specified: equations, parameters, variables, functions
    Keeps a cache for objects which can be modified: parameters, variables, functions
    """

    def __init__(self, cache_size=1000):
        super().__init__()
        self.parameter_cache = LRUCache(cache_size)
        self.variable_cache = LRUCache(cache_size)
        self.function_cache = LRUCache(cache_size)

        self.collector = NameCollector()
        self.residual_transformer = CreateResidual()

    def create_equation(self, equation: str, equation_tree: ast.Expression) -> Equation:
        object_names, func_names = self.collector.get_names(equation_tree)
        residual_tree = self.residual_transformer.visit(equation_tree)
        residual_code = compile(residual_tree, filename='<string>', mode='eval')
        return Equation(equation, residual_tree, residual_code, object_names, func_names)

    def create_parameter(self, parameter_name: str, parameter_tree: ast.Assign) -> Parameter:
        object_names, func_names = self.collector.get_names(parameter_tree)
        
        # extract the assignment value
        rhs = ast.Expression(parameter_tree.value)
        compiled_rhs = compile(rhs, filename="", mode='eval')
        
        return Parameter(parameter_name, parameter_tree, compiled_rhs, object_names, func_names)
        
        # todo: we cannot do cache this way, since the objects will change, but the cache object will not
        # return self.parameter_cache.setdefault(name, Parameter(name, tree, compiled_rhs, object_names, func_names))
        
    def create_variable(self, name: str) -> Variable:
        return self.variable_cache.setdefault(name, Variable(name))

    def create_function(self, name: str) -> Function:
        return self.function_cache.setdefault(name, Function(name))
    