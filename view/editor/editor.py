import os
import logging
from PyQt6 import QtCore
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QFileDialog
from PyQt6.Qsci import QsciScintilla, QsciLexerPython


class BaseEditor(QsciScintilla):
    def __init__(self, parent=None, styles=None):
        super().__init__(parent)
        # todo: fix so that horizontal scroll bar does not appear until needed 
        # self.setWrapMode(QsciScintilla.WrapMode.WrapWord)
        
        # Default styles 
        self.styles = {
            "font-family": "Courier",
            "font-size": 13,
            "caret-color": QColor(247, 247, 241),
            
            "paper_color": QColor(43, 43, 43),
            "selection-background-color": QColor(61, 61, 52),
            "error-indicator-color": QColor("red"),
            
            "margins_foreground": QColor(95, 97, 100),
            "margins_background": QColor(49, 51, 53),
            
            "caret_line_background": QColor(15, 15, 15),
            "caret_foreground": QColor(247, 247, 241),
            
            "select_bg": QColor(60, 60, 60),
        }

        # if a styles dictionary was passed, update our styles with it
        if styles is not None:
            self.styles.update(styles)

        # Set the default font
        font = QFont(self.styles['font-family'], self.styles['font-size'], QFont.Weight.Normal)
        self.setFont(font)
        
        # default paper
        self.setPaper(self.styles['paper_color'])
        
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
        self.setMarginsForegroundColor(self.styles['margins_foreground'])
        self.setMarginsBackgroundColor(self.styles['margins_background'])
        self.linesChanged.connect(self._updateMarginWidth)
        self._updateMarginWidth()

        # Enable current line highlighting
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(self.styles['caret_line_background'])

        # Set indentation defaults
        self.setIndentationsUseTabs(False)
        self.setIndentationWidth(4)
        self.setBackspaceUnindents(True)
        self.setIndentationGuides(True)

        # Set caret defaults
        self.setCaretForegroundColor(self.styles['caret_foreground'])
        self.setCaretWidth(2)

        # Set selection color defaults
        self.setSelectionBackgroundColor(self.styles['select_bg'])
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

    def _updateMarginWidth(self):
        line_count = self.lines()
        digits = len(str(line_count)) if line_count > 0 else 1
        margin_width = self.fontMetrics().horizontalAdvance('9') * (digits + 1)
        self.setMarginWidth(0, margin_width)
        
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
    
    # def mouseMoveEvent(self, e):
    #     """
    #     Shows error message tool tip on hovering error indicator 
    #     """
    #     x = int(e.position().x())
    #     y = int(e.position().y())
    #     pos = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMPOINTCLOSE, x, y)
    #     if pos != -1:
    #         line_num, index = self.lineIndexFromPosition(pos)
    #         if line_num in self.errors:
    #             error_message = self.errors[line_num]
    #             QToolTip.showText(e.globalPosition().toPoint(), error_message)
    #         elif line_num in self.warnings:
    #             warning_message = self.warnings[line_num]
    #             QToolTip.showText(e.globalPosition().toPoint(), warning_message)
    #         else:
    #             QToolTip.hideText()
    #     super(BaseEditor, self).mouseMoveEvent(e)


class PythonEditor(BaseEditor):    
    def __init__(self, parent=None):
        super().__init__(parent)

        # Set the Python lexer
        self.lexer = QsciLexerPython(self)
        self.lexer.setDefaultFont(self.font())
        self.setLexer(self.lexer)
        #self.lexer.setDefaultFont(self.font())
        self.lexer.setFont(self.font())
        
        # Styling
        self.lexer.setColor(QColor("darkgrey"), QsciLexerPython.Comment)
        self.lexer.setColor(QColor("orange"), QsciLexerPython.Keyword)
        self.lexer.setColor(QColor("yellow"), QsciLexerPython.FunctionMethodName)
        self.lexer.setColor(QColor("green"), QsciLexerPython.SingleQuotedString)
        self.lexer.setColor(QColor("green"), QsciLexerPython.DoubleQuotedString)
        
        # Load the default content
        pth = os.path.dirname(__file__)
        pth = os.path.join(pth, "./default_text/editor.default.python.txt")
        self.setTextFromFile(pth)


class FunctionsEditor(BaseEditor):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Set the Python lexer
        self.lexer = QsciLexerPython(self)
        self.lexer.setDefaultFont(self.font())
        self.setLexer(self.lexer)
        # self.lexer.setDefaultFont(self.font())
        self.lexer.setFont(self.font())

        # Styling
        self.lexer.setColor(QColor("darkgrey"), QsciLexerPython.Comment)
        self.lexer.setColor(QColor("orange"), QsciLexerPython.Keyword)
        self.lexer.setColor(QColor("yellow"), QsciLexerPython.FunctionMethodName)
        self.lexer.setColor(QColor("green"), QsciLexerPython.SingleQuotedString)
        self.lexer.setColor(QColor("green"), QsciLexerPython.DoubleQuotedString)

        # Load the default content
        pth = os.path.dirname(__file__)
        pth = os.path.join(pth, "./default_text/editor.default.function.txt")
        self.setTextFromFile(pth)


class EquationEditor(BaseEditor):
    def __init__(self, parent=None):
        super().__init__(parent)
        # # Parser and lexer
        # self.parser = Lark(GRAMMAR, parser='lalr', lexer='basic')
        # self.lexer = LexerEquation(self)
        # 
        # # set parser
        # self.lexer.parser = self.parser
        # self.lexer.setDefaultFont(self.font())
        # self.lexer.setFont(self.font())
        # set lexer
        # self.setLexer(self.lexer)
        
        # Set the Python lexer
        self.lexer = QsciLexerPython(self)
        self.lexer.setDefaultFont(self.font())
        self.setLexer(self.lexer)
        # self.lexer.setDefaultFont(self.font())
        self.lexer.setFont(self.font())
        
        # Styling
        self.lexer.setColor(QColor("darkgrey"), QsciLexerPython.Comment)
        self.lexer.setColor(QColor("orange"), QsciLexerPython.Keyword)
        self.lexer.setColor(QColor("yellow"), QsciLexerPython.FunctionMethodName)
        
        # Load the default content
        pth = os.path.dirname(__file__)
        pth = os.path.join(pth, "./default_text/editor.default.equation.txt")
        self.setTextFromFile(pth)
        

class ConsoleEditor(BaseEditor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        
        # listen to mesasges from the view
        self.parent().console_update.connect(self.insert)
        
    def insert(self, text):
        self.append(text + "\n")
