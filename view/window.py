from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtWidgets import QMainWindow, QSizePolicy, QStatusBar, QMessageBox, QToolBar, QWidget, QPushButton
from PyQt6.QtGui import QIcon
from view.menu import MenuManager
from view.dock import DockManager


class MainWindow(QMainWindow):
    settings_changed = pyqtSignal()
    console_update = pyqtSignal(str)
    
    def __init__(self, dock_manager: DockManager=None, menu_manager: MenuManager=None, parent=None, flags=Qt.WindowType.Window):
        super().__init__(parent, flags)
        # file
        self.current_file_path = None
        self.is_saved = True
        
        # set toolbars
        self.top_toolbar = self.create_toolbar(Qt.ToolBarArea.TopToolBarArea)
        self.left_toolbar = self.create_toolbar(Qt.ToolBarArea.LeftToolBarArea)
        self.right_toolbar = self.create_toolbar(Qt.ToolBarArea.RightToolBarArea)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.toolbar_buttons = {}
        
        # init managers
        self.dock_manager = dock_manager
        self.menu_manager = menu_manager
            
    def create_toolbar(self, position):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(position, toolbar)
        return toolbar

    def add_button_to_toolbar(self, dock_name, toolbar):
        button = QPushButton()
        button.setIcon(QIcon("resources/icons/" + dock_name + ".png"))
        button.setIconSize(QSize(25, 25))
        button.setFixedSize(40, 40)  # Set button width to 100 and height to 50
        button.clicked.connect(lambda: self.reset_button_bg(dock_name))
        button.clicked.connect(lambda: self.dock_manager.toggle_dock(dock_name))

        if dock_name == "Output":
            spacer = QWidget()
            spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            toolbar.addWidget(spacer)

        toolbar.addWidget(button)
        self.toolbar_buttons[dock_name] = button

    def reset_button_bg(self, dock_name):
        if dock_name in self.toolbar_buttons:
            self.toolbar_buttons[dock_name].setStyleSheet('')
        
    def change_button_bg(self, button_name, color):
        if button_name in self.toolbar_buttons:
            self.toolbar_buttons[button_name].setStyleSheet(f'background-color: {color}')
            
    def button_notification(self, widget_alerts: list[str]):
        for alert in widget_alerts:
            if alert == 'Output':
                color = '#ca4f4f'  # red
            else:
                color = '#3a5a9c'  # blue

            self.change_button_bg(alert, color)

    def closeEvent(self, event):
        if not self.is_saved:
            reply = QMessageBox.question(self, "Unsaved Changes",
                                         "There are unsaved changes. Are you sure you want to exit?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    def console_message(self, message: str, buttons: list[str]):
        self.button_notification(buttons)
        self.console_update.emit(message)
    
    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)