from PyQt6 import QtWidgets, QtGui, QtCore
import traceback


# todo: we need to add error handling for attributes etc, when using the py window
# todo: refresh view and validate eqsys so that things such as attribute changes is seen and validation is done on grid etc 
# todo: send output to console, print etc
# todo: send solver output to console as well
# todo: add some success/failure indictation after run

class PythonWidget(QtWidgets.QWidget):
    def __init__(self, eqsys, python_editor, parent=None):
        super().__init__(parent)
        self.view = parent
        
        self.eqsys = eqsys
        self.editor = python_editor

        self.run_button = QtWidgets.QPushButton('Run', self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.run_button)
        layout.addWidget(self.editor)

        self.run_button.clicked.connect(self.run_code)

    def run_code(self):
        code = self.editor.text()
        # add eqsys object to namespace so we can manipulate it in py
        namespace = {'EquationSystem': self.eqsys}

        try:
            compiled_code = compile(code, '<string>', 'exec')
            exec(compiled_code, namespace)
        except (SyntaxError, Exception) as e:
            if isinstance(e, SyntaxError):
                compile_error = str(e)
            else:
                compile_error = f"Unexpected error: {traceback.format_exc()}"
            self.view.console_message(compile_error, ['Output'])
