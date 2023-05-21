import os
import logging

from PyQt6.QtWidgets import QTextEdit, QFileDialog, QFrame
from PyQt6.QtGui import QFont
from ui.syntax import PythonHighlighter, EquationHighlighter


class BaseEditor(QTextEdit):
    def __init__(self, parent = None):
        super().__init__(parent)
        # Apply some basic formatting
        textFont = QFont()
        textFont.setFamily("Courier")
        textFont.setFixedPitch(True)
        textFont.setStyleHint(QFont.StyleHint.TypeWriter)
        self.setCurrentFont(textFont)
        # Other variables
        self.highlighter = None
        # Set frame stye
        self.setFrameShape(QFrame.Shape.NoFrame)


    def setTextFromDialog(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
        dlg.setFilter("Text files (*.txt)")
        filename = None
        if dlg.exec():
            selectedFiles = dlg.selectedFiles()
            if len(selectedFiles) > 0:
                filename = selectedFiles[0]
                self.setTexFromFile(filename)
            if len(selectedFiles) > 1:
                logging.warn("Too many files elected.")


    def setTextFromFile(self, pth: str):
        try:
            with open(pth, "r") as file:
                text = file.read()
                self.setText(text)
        except Exception as ex:
            logging.exception(ex)
            self.clear()



class PythonEditor(BaseEditor):
    def __init__(self, parent = None):
        super().__init__(parent)
        # Use our hightlighter
        self.highlighter = PythonHighlighter(self.document())
        # Load the default content
        pth = os.path.dirname(__file__)
        pth = os.path.join(pth, "editor.default.python.txt")
        self.setTextFromFile(pth)



class EquationEditor(BaseEditor):
    def __init__(self, parent = None):
        super().__init__(parent)
        # Use our hightlighter
        self.highlighter = EquationHighlighter(self.document())
        # Load the default content
        pth = os.path.dirname(__file__)
        pth = os.path.join(pth, "editor.default.equation.txt")
        self.setTextFromFile(pth)



class ConsoleEditor(BaseEditor):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setReadOnly(True)
