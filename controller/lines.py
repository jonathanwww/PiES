from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from controller.util import clean_text
from view.editor.editor import EquationEditor
import ast
from collections import defaultdict


class LinesManager(QObject):
    """ emits a list of all equations which has been changed"""
    add_equation = pyqtSignal(str, object)
    remove_equation = pyqtSignal(str)
    add_parameter = pyqtSignal(str, object)
    remove_parameter = pyqtSignal(str)

    def __init__(self, editor: EquationEditor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.editor.textChanged.connect(self.single_update)
        self.editor.linesChanged.connect(self.multiple_update)
        
        # map: name -> value, tree ; a=2
        self.assignments = {}
        # map expression -> line number, tree
        self.comparisons = {}
        
    def _process_line(self, line: str):
        """ Tries to parse a line and return either a comparison expresion, assignment or none """
        line_type = None
        tree = None
        
        # check for comparisons
        try:
            tree = ast.parse(line, mode='eval')
            if isinstance(tree.body, ast.Compare):
                line_type = 'expression'
                return line_type, tree
        except SyntaxError as e:
            pass
        
        # check for assignments
        try:
            tree = ast.parse(line, mode='exec')
            if isinstance(tree.body[0], ast.Assign):
                line_type = 'statement'
                return line_type, tree
        except Exception as e:
            pass

        return line_type, tree

    def single_update(self):
        line_number, _ = self.editor.getCursorPosition()
        line_text = self.editor.text(line_number)
        
        # Remove old line if it was parsed
        # Check and remove from assignments
        for key, values in list(self.assignments.items()):
            for value_tuple in values[:]:
                old_line_number, _ = value_tuple
                if old_line_number == line_number:
                    values.remove(value_tuple)
                    self.remove_parameter.emit(key)
                    if not values:
                        self.assignments.pop(key, None)
                    break

        # Check and remove from comparisons
        for key, values in list(self.comparisons.items()):
            for value_tuple in values[:]:
                old_line_number, _ = value_tuple
                if old_line_number == line_number:
                    values.remove(value_tuple)
                    self.remove_equation.emit(key)
                    if not values:
                        self.comparisons.pop(key, None)
                    break
                    
        # Process the current line
        line_type, tree = self._process_line(line_text)
        if line_type:
            line_key = ast.unparse(tree)
    
            # Add the new line
            if line_type == 'expression':
                self.comparisons[line_key].append((line_number, tree))
                self.add_equation.emit(line_key, tree)
    
            # Handle assignments
            elif line_type == 'statement':
                key = tree.body[0].targets[0].id
                self.assignments[key].append((line_number, tree))
                self.add_parameter.emit(key, tree)

    def multiple_update(self):
        new_assignments = defaultdict(list)  # Will store keys along with line numbers and trees
        new_comparisons = defaultdict(list)  # Will store expressions along with line numbers and trees

        # get all lines
        editor_lines = self.editor.text().split('\n')

        # try to parse and add to new dictionary
        for i, line in enumerate(editor_lines):
            line_type, tree = self._process_line(line)
            # removes spaces/comments etc
            if line_type:
                line = ast.unparse(tree)
                if line_type == 'expression':
                    new_comparisons[line].append((i, tree))  # Store line number and tree
                elif line_type == 'statement':
                    key = tree.body[0].targets[0].id
                    new_assignments[key].append((i, tree))  # Store line number and tree

        # Compare with the old dictionaries and emit signals
        for key, values in new_assignments.items():
            if key not in self.assignments:
                for line_num, value_tree in values:
                    self.add_parameter.emit(key, value_tree)

        for key in self.assignments.keys():
            if key not in new_assignments:
                self.remove_parameter.emit(key)

        for line, values in new_comparisons.items():
            if line not in self.comparisons:
                for line_num, value_tree in values:
                    self.add_equation.emit(line, value_tree)

        for line in self.comparisons.keys():
            if line not in new_comparisons:
                self.remove_equation.emit(line)

        # Update the assignments and comparisons with the new ones
        self.assignments = new_assignments
        self.comparisons = new_comparisons


class LinesManager_old(QObject):
    """ emits a list of all equations which has been changed"""
    add_equation = pyqtSignal(str, object)
    remove_equation = pyqtSignal(str)
    add_parameter = pyqtSignal(str, object)
    remove_parameter = pyqtSignal(str)
    
    error = pyqtSignal(object)
    
    def __init__(self, editor: EquationEditor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.editor.textChanged.connect(self.single_update)
        self.editor.linesChanged.connect(self.multiple_update)
        
        # map unique strings in editor -> (parsed:0/1, tree/none, line_numbers: list[int])
        self.string_map = {}

        # Keep the previous state of the editor's text
        self.old_editor_text = self.editor.text()
    
    def _remove_equation(self, string):
        self.remove_equation.emit(string)

    def _remove_parameter(self, string):
        self.remove_parameter.emit(string)
    
    def _process_lines(self, lines: list[tuple[str, list[int]]]):
        for line, line_numbers in lines:
            try:
                line_type = None
                
                try:
                    tree = ast.parse(line, mode='eval')
                    if isinstance(tree.body, ast.Compare):
                        line_type = 'expression'
                    print(type(tree))
                    print(ast.dump(tree))
                except SyntaxError:
                    tree = ast.parse(line, mode='exec')
                    if isinstance(tree.body[0], ast.Assign):
                        line_type = 'statement'

                self.string_map[line] = [1, tree, line_numbers]

                if line_type == "statement":
                    self.add_parameter.emit(line, tree)
                elif line_type == "expression":
                    self.add_equation.emit(line, tree)
                elif line_type is None:
                    print('Not added')
            except Exception as e:
                print(e)
                self.string_map[line] = [0, None, line_numbers]

    def single_update(self):
        """triggers on text change"""
        # get line number, get text and clean text
        line_number, _ = self.editor.getCursorPosition()
        line_text = self.editor.text(line_number)
        # line_text = clean_text(line_text)

        # Get old line
        old_line_text = clean_text(self.old_editor_text.split("\n")[line_number])
        
        # If old line was in the map, remove it
        if old_line_text in self.string_map:
            self.string_map[old_line_text][2].remove(line_number)
            if not self.string_map[old_line_text][2]:  # if no line number is left for this equation
                parsed_status, _, _ = self.string_map[old_line_text]
                if parsed_status == 1:
                    self._remove_equation(old_line_text)
                del self.string_map[old_line_text]

        # if not present try to parse
        if line_text not in self.string_map:
            self._process_lines([(line_text, [line_number])])
        # add the line number since its already present
        else:
            self.string_map[line_text][2].append(line_number)
        
        # Update old_editor_text
        self.old_editor_text = self.editor.text()

    def multiple_update(self):
        """triggers on line change"""
        editor_lines = self.editor.text().split('\n')
        editor_lines = [clean_text(x) for x in editor_lines]

        # remove lines from map no longer present in editor
        keys_to_remove = set(self.string_map.keys()) - set(editor_lines)
        eqs_to_rmove = []
        for key in keys_to_remove:
            parsed_status, _, _ = self.string_map[key]
            if parsed_status == 1:
                eqs_to_rmove.append(key)
                # self._remove_equation([key])
            del self.string_map[key]

            self._remove_equation(key)
        
        # find all unique lines in editor and their line numbers
        unique_editor_lines = {}
        for i, line in enumerate(editor_lines):
            if line in unique_editor_lines:
                unique_editor_lines[line].append(i)
            else:
                unique_editor_lines[line] = [i]

        # add new news lines from the editor to the map and try to parse them
        # update the line numbers if it's already present. parse status cannot change
        new_lines = []  # send in a batch
        for unique_line, line_numbers in unique_editor_lines.items():
            if unique_line not in self.string_map:
                new_lines.append((unique_line, line_numbers))
                # self._process_line(unique_line, line_numbers)
            if unique_line in self.string_map:
                self.string_map[unique_line][2] = line_numbers
        
        self._process_lines(new_lines)
        
        # Update old_editor_text
        self.old_editor_text = self.editor.text()