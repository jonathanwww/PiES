import os
import logging
from lark import Lark

from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeyEvent
from PyQt6.QtWidgets import QFileDialog, QToolTip
from PyQt6.Qsci import QsciScintilla, QsciLexerPython

from validation.lexer import LexerEquation
from validation.grammar import GRAMMAR


class BaseEditor(QsciScintilla):
    def __init__(self, parent=None, styles=None):
        super().__init__(parent)
        # Default styles 
        self.styles = {
            "font-family": "Courier",
            "font-size": 15,
            "caret-color": QColor(247, 247, 241),
            "caret-width": 2,
            "selection-background-color": QColor(61, 61, 52),
            "error-indicator-color": QColor("red"),
        }

        # if a styles dictionary was passed, update our styles with it
        if styles is not None:
            self.styles.update(styles)

        # Set the default font
        font = QFont(self.styles['font-family'], self.styles['font-size'], QFont.Weight.Normal)
        self.setFont(font)

        # Enable auto completion
        # todo: current only suggest based on what is present in the document
        # todo: incorporate with linting
        # todo: suggestions should also come from pywindow, functions and defined variables (only if var is list[int/float]/int or float)
        # should suggest python functions for example and should also do linting so if we do from numpy import ..
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
        self.setAutoCompletionThreshold(1)

        # Enable brace matching
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)

        # Set margin for line numbers
        self.setMarginsFont(font)
        # todo: bugged, needs to be set dynamically. set also so numbers starts all the way to the left
        self.setMarginWidth(0, 20)
        self.setMarginLineNumbers(0, True)
        self.setMarginsBackgroundColor(QColor("#cccccc"))

        # Enable current line highlighting
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor(15, 15, 15))

        # Set indentation defaults
        self.setIndentationsUseTabs(False)
        self.setIndentationWidth(4)
        self.setBackspaceUnindents(True)
        self.setIndentationGuides(True)

        # Set caret defaults
        self.setCaretForegroundColor(QColor(247, 247, 241))
        self.setCaretWidth(2)

        # Set selection color defaults
        self.setSelectionBackgroundColor(QColor(60, 60, 60))
        self.resetSelectionForegroundColor()
        
        # Set multiselection defaults
        self.SendScintilla(QsciScintilla.SCI_SETMULTIPLESELECTION, True)
        self.SendScintilla(QsciScintilla.SCI_SETMULTIPASTE, 1)
        self.SendScintilla(QsciScintilla.SCI_SETADDITIONALSELECTIONTYPING, True)

        # Indicator for error highlighting
        self.error_indicator = 8
        self.indicatorDefine(QsciScintilla.IndicatorStyle.SquiggleIndicator, self.error_indicator)
        self.setIndicatorForegroundColor(QColor("red"), self.error_indicator)

        # Indicator for warning highlighting
        self.warning_indicator = 9
        self.indicatorDefine(QsciScintilla.IndicatorStyle.SquiggleIndicator, self.warning_indicator)
        self.setIndicatorForegroundColor(QColor("yellow"), self.warning_indicator)
        
        # for storing errors/warnings in editor
        self.errors = {}
        self.warnings = {}

    def setTextFromDialog(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
        dlg.setFilter("Python files (*.py)")

        if dlg.exec():
            filenames = dlg.selectedFiles()
            if filenames:
                self.setTextFromFile(filenames[0])
            if len(filenames) > 1:
                logging.warn("Too many files selected.")

    def setTextFromFile(self, pth: str):
        try:
            with open(pth, "r") as file:
                self.setText(file.read())
        except Exception as ex:
            logging.exception(ex)
            self.clear()

    def set_indicator(self, line_num, start, end, message, is_error=True):
        # Currently just styles the whole line
        if is_error:
            self.errors[line_num] = message
            indicator = self.error_indicator
        else:
            self.warnings[line_num] = message
            indicator = self.warning_indicator

        self.fillIndicatorRange(line_num, 0, line_num, self.lineLength(line_num), indicator)

    def keyPressEvent(self, event):
        """
        Auto completes quotes, parentheses, brackets and braces, and moves cursor into the middle 
        """
        key = event.key()

        # Dictionary of keys and their corresponding closing characters
        wrap_pairs = {
            QtCore.Qt.Key.Key_QuoteDbl: '"',
            QtCore.Qt.Key.Key_Apostrophe: "'",
            QtCore.Qt.Key.Key_ParenLeft: ')'
        }

        if key in wrap_pairs:
            selected_text = self.selectedText()

            # Check if next character is whitespace, end of document, or closing bracket/parentheses/brace
            pos = self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
            next_char = self.SendScintilla(QsciScintilla.SCI_GETCHARAT, pos)
            next_is_empty_or_closing = next_char in (0, 32, 9, 10, 13, 41)  # 0 for end of document, 32 for ' ', 9 for '\t', 10 for '\n', 13 for '\r', for ')'

            if selected_text:  # if there's a text selection
                self.replaceSelectedText(f'{chr(key)}{selected_text}{wrap_pairs[key]}')
                return
            elif next_is_empty_or_closing:  # if the next character is a whitespace, end of document, or closing bracket/parentheses/brace
                super().keyPressEvent(event)
                self.insert(wrap_pairs[key])
                return

        super().keyPressEvent(event)

    def mouseMoveEvent(self, e):
        """
        Shows error message tool tip on hovering error indicator 
        """
        x = int(e.position().x())
        y = int(e.position().y())
        pos = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMPOINTCLOSE, x, y)
        if pos != -1:
            line_num, index = self.lineIndexFromPosition(pos)
            if line_num in self.errors:
                error_message = self.errors[line_num]
                QToolTip.showText(e.globalPosition().toPoint(), error_message)
            elif line_num in self.warnings:
                warning_message = self.warnings[line_num]
                QToolTip.showText(e.globalPosition().toPoint(), warning_message)
            else:
                QToolTip.hideText()
        super(BaseEditor, self).mouseMoveEvent(e)


class PythonEditor(BaseEditor):
    textChangedSignal = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)

        # Set the Python lexer
        self.lexer = QsciLexerPython(self)
        self.lexer.setDefaultFont(self.font())
        self.setLexer(self.lexer)

        # Load the default content
        pth = os.path.dirname(__file__)
        pth = os.path.join(pth, "../default_text/editor.default.python.txt")
        self.setTextFromFile(pth)

        # Emit signal on text change
        self.textChanged.connect(self._emit_text)

    def _emit_text(self):
        self.textChangedSignal.emit(self.text())


class EquationEditor(BaseEditor):
    textChangedSignal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Parser and lexer
        self.parser = Lark(GRAMMAR, parser='lalr', lexer='basic')
        self.lexer = LexerEquation(self)
        
        # set parser
        self.lexer.parser = self.parser
        self.lexer.setDefaultFont(self.font())
        
        # set lexer
        self.setLexer(self.lexer)

        # Load the default content
        pth = os.path.dirname(__file__)
        pth = os.path.join(pth, "../default_text/editor.default.equation.txt")
        self.setTextFromFile(pth)

        # Emit signal on text change for controller to create objects
        self.textChanged.connect(self.emit_text)
        
        # Send all lines to lexer for styling
        self.textChanged.connect(self.send_to_lexer)
        
        # on error in lexer
        self.lexer.error_signal.connect(self.set_indicator)

    def emit_text(self):
        self.textChangedSignal.emit(self.text())

    def send_to_lexer(self):
        """
        Works by styling each line of the whole document on text change .. 
        """
        text = self.text()
        lines = text.splitlines(keepends=True)  # we need to style all characters in text
        start = 0  # start of document

        # reset dictionaries
        self.errors = {}

        for i, line in enumerate(lines):
            # clear line of error indicators
            self.clearIndicatorRange(i, 0, i, self.lineLength(i), self.error_indicator)

            # previous byteposition in stream + byte length of the line
            end = start + len(bytearray(line, "utf-8"))

            # send it to styling
            self.lexer.styleText(start, end, line_num=i, line=line)
            start = end


class ConsoleEditor(BaseEditor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        
    def insert(self, text):
        self.append(text + "\n")
