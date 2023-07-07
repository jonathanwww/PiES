from lark import Lark, UnexpectedCharacters, UnexpectedToken
from PyQt6.QtGui import QColor
from PyQt6.Qsci import QsciLexerCustom
from PyQt6.QtCore import pyqtSignal


class LexerEquation(QsciLexerCustom):
    # line num, start, end, message, error?
    error_signal = pyqtSignal(int, int, int, str, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parser = None
        self.create_styles()
        
    def create_styles(self):
        deeppink = QColor(249, 38, 114)
        khaki = QColor(230, 219, 116)
        yellow = QColor(229, 192, 123)
        blue = QColor(97, 173, 235)
        darkgrey = QColor(92, 99, 112)
        green = QColor(152, 195, 121)
        error_color = QColor(220, 20, 60)  # red color for errors
        grey = QColor(171, 178, 191)
        purple = QColor(171, 71, 188)
        orange = QColor(255, 167, 38)

        styles = {
            0: blue,
            1: yellow,
            2: grey,
            3: darkgrey,
            4: green,
            5: deeppink,
            6: khaki,
            7: error_color,
            8: purple,
            9: orange
        }

        for style, color in styles.items():
            self.setColor(color, style)

        self.token_styles = {
            "NUMBER": 0,
            "CNAME": 1,
            "WS": 3,  # White Space
            "STRING": 4,
            "DOTTED_NAME": 6,
            "COMMENT": 2,
            'EQUAL': 2,
            'PLUS': 8,
            'MINUS': 8,
            'STAR': 8,
            'SLASH': 8,
            'POW': 5,  # Power
            'CIRCUMFLEX': 8,
            'LPAR': 9,  # Left parenthesis
            'RPAR': 9,  # Right parenthesis
            'COMMA': 9,
            'ERROR': 7  # dummy token, color has to be in use by a token, else it wont be created?
        }

    def description(self, style):
        return {v: k for k, v in self.token_styles.items()}.get(style, "")

    def styleText(self, start, end, line_num=None, line=None):
        """
        start/end of text in stream, not in line 
        """
        if line is not None:
            self.startStyling(start)
            text = line
            last_pos = start
            
            try:
                # check tokens
                for token in self.parser.lex(text, dont_ignore=True):
                    
                    token_len = len(bytearray(token, "utf-8"))
                    self.setStyling(
                        token_len, self.token_styles.get(token.type, 0))

                    last_pos = last_pos + token_len
                
                # todo: optimize
                # if empty line or comment do not try to parse
                tokens = [token for token in self.parser.lex(text, dont_ignore=True)]
                if all(token.type in ('WS', 'COMMENT') for token in tokens):
                    return
                # try to parse
                else:
                    tree = self.parser.parse(text)
                    
            except UnexpectedCharacters as e:
                # handle unexpected characters by styling rest of line red
                self.setStyling(end-last_pos, 7)
                # send error information for indicators. currently just whole line
                self.error_signal.emit(line_num, start, end, str(e), True)
            except UnexpectedToken as e:
                self.parent()
                # send error information for indicators. currently just whole line 
                self.error_signal.emit(line_num, start, end, str(e), True)
