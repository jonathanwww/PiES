import ast
import itertools
from collections import defaultdict
from collections import OrderedDict
from PyQt6.QtCore import QObject, pyqtSignal


class CreateResidual(ast.NodeTransformer):
    # todo: finish
    def visit_Compare(self, node):
        if isinstance(node.ops[0], ast.Eq) and len(node.comparators) == 1:
            new_node = ast.BinOp(left=node.left, op=ast.Sub(), right=node.comparators[0])
            new_node.lineno = node.lineno
            new_node.col_offset = node.col_offset
            return new_node
        return self.generic_visit(node)
    

class NameCollector(ast.NodeVisitor):
    """
    Collects the object names in the expression 
    there can be overlap between function and variable names
    """
    def __init__(self):
        self.var_names = set()
        self.func_names = set()
        self.current_function = None

    def _reset(self):
        self.var_names = set()
        self.func_names = set()

    def get_names(self, tree: ast.AST):
        self._reset()
        self.visit(tree)
        return self.var_names, self.func_names

    def visit_Name(self, node):
        if self.current_function is None:
            self.var_names.add(node.id)
        self.generic_visit(node)

    def visit_Call(self, node):
        self.current_function = node
        if isinstance(node.func, ast.Name):
            self.func_names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.func_names.add(node.func.attr)
        self.generic_visit(node)
        self.current_function = None


class Counter(QObject):
    # todo: check if we can optimize
    """ 
    Keeps a count of the number of times the name is inserted
    Emits a signal the first time a name is added
    Emits a signal when an object name counter reaches 0 and removes that entry
    """
    name_added = pyqtSignal(str)
    name_removed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.counter = defaultdict(int)
        self.objects = defaultdict()

    def _increase_counter(self, name: str):
        """ increases the counter by 1, or inserts if non-existing, since we have default dict """
        self.counter[name] += 1
        if self.counter[name] == 1:
            self.name_added.emit(name)

    def _decrease_counter(self, name: str):
        # todo: bug can decrease key which does not exist, so it goes to negative
        """ decrease the counter by 1 and removes if counter reaches 0 """
        self.counter[name] -= 1
        if self.counter[name] == 0:
            del self.counter[name]
            self.name_removed.emit(name)
            
            # check if there is an associated object
            if name in self.objects:
                del self.objects[name]

    def insert(self, name: str, obj=None):
        """ add an object to be assoicated with the name """
        if obj:
            self.objects[name] = obj
        self._increase_counter(name)

    def delete(self, name: str):
        self._decrease_counter(name)

    def get_object(self, name: str):
        return self.objects[name]


class LRUCache(OrderedDict):
    def __init__(self, capacity):
        self.capacity = capacity
        super().__init__()

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        elif len(self) >= self.capacity:
            self.popitem(last=False)
        super().__setitem__(key, value)


class GridManager(QObject):
    data_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.variables = {}

    def _data_updated(self):
        self.data_updated.emit()

    def assign(self, var_name, values):
        self.variables[var_name] = values
        self._data_updated()

    def remove(self, var_name):
        del self.variables[var_name]
        self._data_updated()

    def get_grid(self):
        product = list(itertools.product(*self.variables.values()))
        keys = list(self.variables.keys())
        grid_list = []

        for values in product:
            grid_dict = {key: value for key, value in zip(keys, values)}
            grid_list.append(grid_dict)

        return grid_list
