import pint
import itertools
from collections import OrderedDict


class VariableManagerError(Exception):
    pass


class EquationManagerError(Exception):
    pass


class LRUCache(OrderedDict):
    def __init__(self, capacity):
        self.capacity = capacity
        super().__init__()

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.capacity:
            oldest = next(iter(self))
            del self[oldest]


def create_residual(eq_str: str) -> str:
    lhs, rhs = eq_str.split('=')
    return f"{lhs} - ({rhs})"


class Grid:
    def __init__(self):
        self.variables = {}

    def assign(self, var_name, values):
        self.variables[var_name] = values

    def get_grid(self):
        product = list(itertools.product(*self.variables.values()))
        keys = list(self.variables.keys())
        grid_list = []

        for values in product:
            grid_dict = {key: value for key, value in zip(keys, values)}
            grid_list.append(grid_dict)

        return grid_list


def output_unit(unit: pint.Unit):
    # Decorator for setting function output unit in python window
    def unit_decorator(func):
        func.unit = unit
        return func
    return unit_decorator
