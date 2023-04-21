import os
import logging

from PyQt6.QtWidgets import QTableWidget

class VariableTable(QTableWidget):
      def __init__(self, parent = None):
            super().__init__(parent)
            self.setColumnCount(8)
            self.setHorizontalHeaderLabels([self.tr("Name"), self.tr("x0"), self.tr("Lower b"), self.tr("Upper b"), self.tr("Used"), self.tr("Loopvar"), self.tr("Paramvar"), self.tr("Unit")])
            for col in range(self.columnCount()):
                self.setColumnWidth(col, 65)

            # Sorting the table breaks the equations. Consider using a
            # properly defined table model. Such a model does not change
            # the internal index when the view is sorted.
            #self.horizontalHeader().sectionClicked.connect(self.sortItems)
