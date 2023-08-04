from PyQt6.QtCore import pyqtSlot
from PyQt6.QtCore import QTimer, QElapsedTimer
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel


class StatusBarWidget(QWidget):
    def __init__(self, solver_interface, parent=None):
        super().__init__(parent)
        
        self.solver_interface = solver_interface
        self.solver_interface.solve_status.connect(self.update_solve_status)
        
        # layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(7, 1, 0, 4)

        # time elapsed while solving
        self.time_label = QLabel()
        self.layout.addWidget(self.time_label)
        
        # Status for solving
        self.status_label = QLabel()
        self.layout.addWidget(self.status_label)
        self.layout.addStretch(1)

        # Change font size and color
        font = self.status_label.font()
        font.setPointSize(12)
        self.status_label.setFont(font)

        self.status_label.setStyleSheet("color: #ccc;")

        # Timer variables
        self.timer = QTimer()
        self.elapsed_timer = QElapsedTimer()

        # Connect timer timeout signal to update time label
        self.timer.timeout.connect(self.update_time_label)

    def stop_timer(self):
        # Stop the timer
        self.timer.stop()

    def start_timer(self):
        # Start the timer and record the start time
        self.elapsed_timer.start()
        self.time_label.setText('00:00')
        self.timer.start(100)  # Update the time label every second (1000 milliseconds)

    def update_time_label(self):
        # Calculate the elapsed time since the process started
        elapsed_time = self.elapsed_timer.elapsed()
        formatted_time = self.format_time(elapsed_time)

        # Update the time label with the elapsed time
        self.time_label.setText(formatted_time)

    @staticmethod
    def format_time(milliseconds: int) -> str:
        # Format the elapsed time in hours, minutes, and seconds
        seconds = (milliseconds // 1000) % 60
        minutes = (milliseconds // (1000 * 60))
        # hours = (milliseconds // (1000 * 60 * 60))

        return "{:02d}:{:02d}".format(minutes, seconds)
    
    @pyqtSlot(str)
    def update_solve_status(self, message: str):
        # Updates status bar with solving status: run 1/n, block ..
        self.status_label.setText(message)
