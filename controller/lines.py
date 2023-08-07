import ast
import difflib
from collections import defaultdict
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from view.editor.editor import EquationEditor
from eqsys.util import Counter


class LinesManager(QObject):
    """
    keeps a count of unique lines
    keeps a count to unique parsed lines 
    emits signals on eq/param added/removed
    """
    add_equation = pyqtSignal(str, object)
    remove_equation = pyqtSignal(str)
    add_parameter = pyqtSignal(str, object)
    remove_parameter = pyqtSignal(str)

    def __init__(self, editor: EquationEditor, parent=None):
        super().__init__(parent)
        self.editor = editor
                
        self.editor.linesChanged.connect(self.on_lines_changed)
        self.editor.textChanged.connect(self.on_line_changed)

        self.previous_state = []
        
        # keeps a count of unique lines in the editor
        # signals when a name is added or removed from the count
        # key name is the line str 
        self.line_counter = Counter()
        self.line_counter.name_added.connect(self.unique_line_added)
        self.line_counter.name_removed.connect(self.unique_line_removed)
        
        # keeps a count of unique parsed lines
        # key name is the unparsed line
        self.parsed_line_counter = Counter()
        self.parsed_line_counter.name_added.connect(self.unique_parsed_line_added)
        self.parsed_line_counter.name_removed.connect(self.unique_parsed_line_removed)

        # map from unique lines to parsed lines
        # multiple lines could result in the same line; a =1, a=1
        self.map_line_to_parsed = defaultdict(str)

    @pyqtSlot(str)
    def unique_parsed_line_added(self, name):
        """ when a unique parsed line is added to the parsed_line_counter """        
        tree = self.parsed_line_counter.get_object(name)
        
        # Comparison
        if isinstance(tree.body[0].value, ast.Compare):
            ast_expression = ast.Expression(tree.body[0].value)
            self.add_equation.emit(name, ast_expression)
            
        # Assignment
        elif isinstance(tree.body[0], ast.Assign):
            parameter_name = ast.unparse(tree.body[0].targets[0])
            self.add_parameter.emit(parameter_name, tree.body[0])

    @pyqtSlot(str)
    def unique_parsed_line_removed(self, name):
        """ when a unique parsed line is removed from the parsed_line_counter """
        tree = self.parsed_line_counter.get_object(name)

        # Comparison
        if isinstance(tree.body[0].value, ast.Compare):
            self.remove_equation.emit(name)

        # Assignment
        elif isinstance(tree.body[0], ast.Assign):
            parameter_name = ast.unparse(tree.body[0].targets[0])
            self.remove_parameter.emit(parameter_name)
    
    @pyqtSlot(str)
    def unique_line_added(self, name):
        """ new unique line added in editor, try to parse it and add to unique parsed lines"""
        try:
            # todo: issue with empty and isistance check
            tree = ast.parse(name, mode='exec')
            # only add assignments and comparisons
            if isinstance(tree.body[0].value, ast.Compare) or isinstance(tree.body[0], ast.Assign):
                equation_string = ast.unparse(tree)
                
                # increase counter and associate expression object with equation_string
                self.parsed_line_counter.insert(equation_string, tree)
    
                # add unique line name to map
                self.map_line_to_parsed[name] = equation_string
            
        except SyntaxError as e:
            pass
            # print(e.text, " " * (e.offset-2) + "^", str(e))

    @pyqtSlot(str)
    def unique_line_removed(self, name):
        """ line removed from editor, check if it needs to be deleted """
        if name in self.map_line_to_parsed:
            equation_string = self.map_line_to_parsed.pop(name)
            self.parsed_line_counter.delete(equation_string)

    @pyqtSlot()
    def on_line_changed(self):
        """ updates the counter for a single line """
        current_line_num = self.editor.getCursorPosition()[0]
        old_line = self.previous_state[current_line_num].rstrip('\n')
        new_line = self.editor.text(current_line_num).rstrip('\n').strip()
        
        if old_line != new_line:
            self.line_counter.insert(new_line)
            self.line_counter.delete(old_line)
        
        self.previous_state[current_line_num] = new_line

    @pyqtSlot()
    def on_lines_changed(self):
        """ updates the counter for all changes in the editor """
        
        new_content = [self.editor.text(i).rstrip('\n').strip() for i in range(self.editor.lines())]
        diff = list(difflib.ndiff(self.previous_state, new_content))
        
        added_lines = [l.lstrip('+ ') for l in diff if l.startswith('+ ')]
        removed_lines = [l.lstrip('- ') for l in diff if l.startswith('- ')]
        
        for line in added_lines:
            self.line_counter.insert(line)
        for line in removed_lines:
            self.line_counter.delete(line)

        self.previous_state = new_content
