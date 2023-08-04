from collections import OrderedDict
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal


class ResultsEntry:
    def __init__(self, variables: list):
        self.variables = variables
        self.information = {}  # todo: additional information, grid vars/parameters/block/solve time etc
        self.data = np.empty((0, len(variables)))
        self.temp_results = np.empty(len(variables))


class ResultsManager(QObject):
    data_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.base_name = "Entry"
        self.entries = OrderedDict()

    def _updated(self):
        self.data_changed.emit()

    def create_entry(self, variables: list[str]):
        # Determine the name for the new entry
        highest_number = 0
        for name in self.entries.keys():
            if name.startswith(self.base_name):
                try:
                    number = int(name[len(self.base_name):])
                    highest_number = max(highest_number, number)
                except ValueError:
                    continue
        new_name = f"{self.base_name} {highest_number + 1}"

        self.entries[new_name] = ResultsEntry(variables)
        self._updated()
        return new_name

    def delete_entry(self, name):
        # Remove an entry from the dictionary by name
        if name not in self.entries:
            raise KeyError(f"No entry named '{name}' found.")

        del self.entries[name]
        self._updated()

    def rename_entry(self, old_name, new_name):
        if new_name in self.entries:
            raise ValueError(f"Entry '{new_name}' already exists.")
        elif old_name not in self.entries:
            raise KeyError(f"No entry named '{old_name}' found.")

        keys = list(self.entries.keys())
        values = list(self.entries.values())

        index = keys.index(old_name)

        keys[index] = new_name

        self.entries = OrderedDict(zip(keys, values))
        self._updated()
        
    def commit_results(self, name):
        """ commit the row to the entry once all variables is solved"""
        self.entries[name].data = np.vstack([self.entries[name].data, self.entries[name].temp_results])
        self.entries[name].temp_results = np.empty(len(self.entries[name].variables))
        self._updated()
    
    def add_results(self, name, variables: list[str], results: list[float]):
        """ build a result row """
        for variable, result in zip(variables, results):
            if variable not in self.entries[name].variables:
                raise ValueError(f"The variable '{variable}' is not in the variables list.")
            index = self.entries[name].variables.index(variable)
            self.entries[name].temp_results[index] = result
