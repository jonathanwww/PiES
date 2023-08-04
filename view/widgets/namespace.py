from PyQt6 import QtWidgets
import traceback


# todo: add some success/failure indictation after run
# todo: some way to see all defined functions?
# todo: set gui button as yellow when uncompiled content
# todo: finish as namespace, currently only functions

class NamespaceWidget(QtWidgets.QWidget):
    """ updates the equation system namespace based on the content in the editor"""

    def __init__(self, eqsys, python_editor, parent=None):
        super().__init__(parent)
        self.view = parent

        self.eqsys = eqsys
        self.editor = python_editor
        self.editor.textChanged.connect(self.change_button_background)  # Connect textChanged signal

        self.run_button = QtWidgets.QPushButton('Update namespace', self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.run_button)
        layout.addWidget(self.editor)

        self.run_button.clicked.connect(self.run_code)
        self.run_button.clicked.connect(self.reset_button_background)  # Reset background on click

    def run_code(self):
        code = self.editor.text()
        namespace = {}
        try:
            compiled_code = compile(code, '<string>', 'exec')
            exec(compiled_code, namespace)
            del namespace['__builtins__']
            self.eqsys.namespace = namespace
        except (SyntaxError, Exception) as e:
            if isinstance(e, SyntaxError):
                compile_error = str(e)
            else:
                compile_error = f"Unexpected error: {traceback.format_exc()}"
            self.view.console_message(compile_error, ['Output'])
            self.eqsys.namespace = {}

    def change_button_background(self):
        """Changes the run button background when there are changes in the editor"""
        self.run_button.setStyleSheet("background-color: yellow")

    def reset_button_background(self):
        """Resets the run button background to default when clicked"""
        self.run_button.setStyleSheet("")