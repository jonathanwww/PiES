import sys
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QSlider
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np


class InteractiveGraph(QWidget):
    def __init__(self, parent=None):
        super(InteractiveGraph, self).__init__(parent)

        # Create the plot
        self.plot = pg.PlotWidget()

        # Create a vertical box layout
        layout = QVBoxLayout()
        layout.addWidget(self.plot)

        # Add a slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(-10, 10)
        self.slider.valueChanged.connect(self.update_plot)

        layout.addWidget(self.slider)

        # Set the widget layout
        self.setLayout(layout)

        # Initialize data
        self.x = np.arange(100)
        self.y = np.sin(self.x / 10)
        self.curve = self.plot.plot(self.x, self.y)

    def update_plot(self):
        ''' Update the plot based on the slider value '''
        # Compute new y values
        self.y = np.sin((self.x + self.slider.value()) / 10)
        # Update the plot data
        self.curve.setData(self.x, self.y)
