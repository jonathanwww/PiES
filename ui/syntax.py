import re
from PyQt6.QtGui import QTextCharFormat, QSyntaxHighlighter, QColor


class EquationHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(93, 179, 231))
        keywords = ['=', 'gen_eqs']
        self.keyword_patterns = [re.compile(r""+keyword) for keyword in keywords]

        self.red_format = QTextCharFormat()
        self.red_format.setBackground(QColor(230, 101, 101))
        self.red_pattern = re.compile(r"^[^=]+$|^=|=$")

    def highlightBlock(self, text):
        for pattern in self.keyword_patterns:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)

        for match in self.red_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.red_format)


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(93, 179, 231))
        keywords = ["and", "as", "assert", "break", "class", "continue", "def", "del", "elif", "else", "except", "False", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "None", "not", "or", "pass", "raise", "return", "True", "try", "while", "with", "yield"]
        self.keyword_patterns = [re.compile(r"\b" + keyword + r"\b") for keyword in keywords]

        self.patterns = []

    def highlightBlock(self, text):
        for pattern in self.keyword_patterns:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)
