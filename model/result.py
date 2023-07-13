from PyQt6.QtCore import QObject, pyqtSignal


class ResultsManager(QObject):
    data_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.entries = []
        self.all_variables = set()  # a set of all the key elements in the dictionaries in all_results

    def _updated(self):
        self.all_variables.clear()
        for entry in self.entries:
            for result in entry:
                self.all_variables.update(result.keys())
        self.data_changed.emit()
        
    def create_entry(self) -> int:
        # returns the index of the new entry
        self.entries.append([])
        self._updated()
        return len(self.entries) - 1

    def delete_entry(self, index: int):
        # Remove an entry from the list by index
        if index < 0 or index >= len(self.entries):
            raise IndexError('Index out of range.')
        
        del self.entries[index]
        self._updated()

    def update_entry(self, index: int, run_result: dict):
        if index < 0 or index >= len(self.entries):
            raise IndexError('Index out of range.')
        
        self.entries[index].append(run_result)
        self._updated()
