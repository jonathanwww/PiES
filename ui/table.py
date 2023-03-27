import os
import logging

from PyQt6.QtWidgets import QTableWidget

class VariableTable(QTableWidget):
      def __init__(self, parent = None):
            super().__init__(parent)
            self.setColumnCount(7)
            self.setHorizontalHeaderLabels([self.tr("Name"), self.tr("x0"), self.tr("Lower b"), self.tr("Upper b"), self.tr("Used"), self.tr("Loopvar"), self.tr("Paramvar")])
            for col in range(self.columnCount()):
                self.setColumnWidth(col, 65)