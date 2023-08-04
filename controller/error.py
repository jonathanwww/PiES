from PyQt6.QtCore import QObject, pyqtSignal
from view.editor.editor import BaseEditor


class ErrorHandler(QObject):
    error_occurred = pyqtSignal(str, str, int)

    def __init__(self, editor: BaseEditor):
        super().__init__()
        self.editor = editor
        # on error in lexer
        # todo: move to error handler
        # self.python_edit.lexer.error_signal.connect(self.python_edit.set_indicator)
        # self.controller.warning_signal.connect(self.set_indicator)
        
        # key: line, start, end
        # value: message
        self.errors = {}
        self.warnings = {}

    def set_indicator(self, line_num, start, end, message, is_error=True):
        # Currently just styles the whole line
        if is_error:
            self.errors[line_num] = message
            indicator = self.editor.error_indicator
        else:
            self.warnings[line_num] = message
            indicator = self.editor.warning_indicator

        self.editor.fillIndicatorRange(line_num, 0, line_num, self.editor.lineLength(line_num), indicator)

    def clear_indicator(self, line_num, start, end, is_error=True):
        if is_error:
            del self.errors[line_num]
            indicator = self.editor.error_indicator
        else:
            del self.warnings[line_num]
            indicator = self.editor.warning_indicator

        self.editor.clearIndicatorRange(line_num, 0, line_num, self.editor.lineLength(line_num), indicator)
    