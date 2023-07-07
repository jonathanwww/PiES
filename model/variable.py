from typing import Any
import numpy as np
import pint
from model.util import LRUCache, VariableManagerError
from PyQt6.QtCore import QObject, pyqtSignal


class Variable:
    def __init__(self, name: str,
                 unit: pint.Unit,
                 starting_guess: int = 1,
                 lower_bound: int = -np.inf,
                 upper_bound: int = np.inf):

        self._name = name
        self._starting_guess = starting_guess
        self._lower_bound = lower_bound
        self._upper_bound = upper_bound
        self._unit = unit
    
    def __repr__(self):
        return f'Variable({self.name}, {self.unit}, x0={self.starting_guess}, lb={self.lower_bound}, ub={self.upper_bound})'

    def __eq__(self, other: Any):
        if isinstance(other, Variable):
            return self._name == other._name
        return False
    
    @property
    def name(self):
        return self._name

    @property
    def starting_guess(self):
        return self._starting_guess

    @starting_guess.setter
    def starting_guess(self, value):
        self._starting_guess = value

    @property
    def lower_bound(self):
        return self._lower_bound

    @lower_bound.setter
    def lower_bound(self, value):
        self._lower_bound = value

    @property
    def upper_bound(self):
        return self._upper_bound

    @upper_bound.setter
    def upper_bound(self, value):
        self._upper_bound = value

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, value):
        self._unit = value


class VariableManager(QObject):
    data_changed = pyqtSignal()
    attribute_updated = pyqtSignal(str, str)  # str, variable name, str: attribute name
    
    def __init__(self, cache_size=100):
        super().__init__()
        self.ureg = None
        self.variables = {}
        self.variables_cache = LRUCache(cache_size)
    
    def _modified(self, variable: Variable):
        return variable.upper_bound != np.inf \
            or variable.lower_bound != -np.inf \
            or variable.starting_guess != 1 \
            or variable.unit is not self.ureg.dimensionless

    def update_variable(self, variable_name: str, attribute_name: str, value: Any):
        if variable_name not in self.variables:
            raise VariableManagerError(f'Failed to update variable: "{variable_name}" does not exist')

        variable = self.variables[variable_name]

        if not hasattr(variable, attribute_name):
            raise VariableManagerError(f'Failed to update variable: attribute "{attribute_name}" does not exist')

        setattr(variable, attribute_name, value)

        self.attribute_updated.emit(variable_name, attribute_name)
        
    def insert_variable(self, variable: Variable):
        if variable.name in self.variables:
            raise VariableManagerError(f'Failed to insert variable: "{variable.name}" already exists')

        if variable.name in self.variables_cache:
            self.variables[variable.name] = self.variables_cache[variable.name]
        else:
            self.variables[variable.name] = variable
        self.data_changed.emit()

    def delete_variable(self, variable_name: str):
        if variable_name not in self.variables:
            raise VariableManagerError(f'Failed to delete variable: "{variable_name}" does not exist')

        if self._modified(self.variables[variable_name]):
            self.variables_cache[variable_name] = self.variables[variable_name]

        del self.variables[variable_name]
        self.data_changed.emit()
