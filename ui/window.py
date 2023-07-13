from PyQt6.QtWidgets import QMainWindow, QTextEdit, QDockWidget, QSizePolicy, QStatusBar, QMessageBox, QStyle

from ui.menu import MenuManager
from PyQt6.QtWidgets import QWidget, QToolBar, QVBoxLayout, QPushButton, QFrame
from PyQt6.QtGui import QColor, QPainter, QBrush, QIcon
from PyQt6.QtCore import Qt


class Light(QFrame):
    def __init__(self, parent=None):
        super(Light, self).__init__(parent)
        self.color = QColor()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(QBrush(self.color))
        painter.drawEllipse(0, 0, self.width(), self.height())


class DockManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.docks_map = {
            "Python": (Qt.DockWidgetArea.LeftDockWidgetArea, main_window.left_toolbar, False),
            "Plot": (Qt.DockWidgetArea.LeftDockWidgetArea, main_window.left_toolbar, False),
            "Output": (Qt.DockWidgetArea.BottomDockWidgetArea, main_window.left_toolbar, False),
            "Variables": (Qt.DockWidgetArea.RightDockWidgetArea, main_window.right_toolbar, True),
            "Eqsys": (Qt.DockWidgetArea.RightDockWidgetArea, main_window.right_toolbar, False),
            "Results": (Qt.DockWidgetArea.RightDockWidgetArea, main_window.right_toolbar, False),
        }

        for dock_name, (position, toolbar, is_visible) in self.docks_map.items():
            self.main_window.add_button_to_toolbar(dock_name, toolbar)
            self.add_dock(dock_name, position, is_visible)

    def add_dock(self, dock_name, position, is_visible):
        dock = QDockWidget(dock_name)
        dock_layout = QVBoxLayout()

        re_dock_button = QPushButton("re-dock")
        re_dock_button.clicked.connect(lambda: self.re_dock(dock, position))
        dock_layout.addWidget(re_dock_button)

        text_edit = QTextEdit()
        dock_layout.addWidget(text_edit)

        dock_widget_content = QWidget()
        dock_widget_content.setLayout(dock_layout)
        dock.setWidget(dock_widget_content)

        dock.widget().re_dock_button = re_dock_button

        if dock_name == "Output":
            dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        else:
            dock.setAllowedAreas(position)

        dock.topLevelChanged.connect(lambda top_level: self.on_dock_floating(dock, top_level))
        self.main_window.addDockWidget(position, dock)
        dock.setVisible(is_visible)
        self.docks_map[dock_name] = dock

    def set_dock_widget(self, dock_name, new_widget):
        dock = self.docks_map[dock_name]

        dock_layout = QVBoxLayout()

        re_dock_button = QPushButton("re-dock")
        re_dock_button.clicked.connect(lambda: self.re_dock(dock, self.main_window.dockWidgetArea(dock)))

        dock_layout.addWidget(re_dock_button)
        dock_layout.addWidget(new_widget)

        dock_widget_content = QWidget()
        dock_widget_content.setLayout(dock_layout)

        dock.setWidget(dock_widget_content)

    def re_dock(self, dock, position):
        dock.setFloating(False)
        self.main_window.addDockWidget(position, dock)

        # Close other docks on the same side that are not floating
        for name, other_dock in self.docks_map.items():
            if other_dock != dock and not other_dock.isFloating() and self.main_window.dockWidgetArea(other_dock) == position:
                other_dock.setVisible(False)

    def on_dock_floating(self, dock, top_level):
        if top_level:
            dock.setAllowedAreas(Qt.DockWidgetArea.NoDockWidgetArea)
        else:
            dock.setAllowedAreas(self.main_window.dockWidgetArea(dock))

    def toggle_dock(self, dock_name):
        dock_to_toggle = self.docks_map[dock_name]
        dock_to_toggle.setVisible(not dock_to_toggle.isVisible())

        toggle_dock_position = self.main_window.dockWidgetArea(dock_to_toggle)

        if dock_to_toggle.isFloating():
            return
        else:
            for name, dock in self.docks_map.items():
                if name != dock_name:
                    if self.main_window.dockWidgetArea(dock) == toggle_dock_position and dock.isVisible() and not dock.isFloating():
                        dock.setVisible(False)
        
        
class MainWindow(QMainWindow):
    def __init__(self, parent=None, flags=Qt.WindowType.Window):
        super().__init__(parent, flags)
        # file
        self.current_file_path = None
        self.is_saved = True

        # self.setStyleSheet("""
        #         QMainWindow{
        #             background-color: black;
        #             color: white;
        #             border: 0.1px solid black;
        #         }
        #         QWidget{
        #             background-color: black;
        #             color: white;
        #             border: 0.1px solid black;
        #         }
        #         QPushButton{
        #             background-color: black;
        #             color: white;
        #             border: 0.1px solid black;
        #             padding: 10px;
        #         }
        #         """
        #                   )

        # set toolbars
        self.top_toolbar = self.create_toolbar(Qt.ToolBarArea.TopToolBarArea)
        self._setup_top_bar()
        
        self.left_toolbar = self.create_toolbar(Qt.ToolBarArea.LeftToolBarArea)
        self.right_toolbar = self.create_toolbar(Qt.ToolBarArea.RightToolBarArea)
        self.toolbar_buttons = {}
        
        # init managers
        self.dock_manager = DockManager(self)
        self.menu_manager = MenuManager(self)
        
        # status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _setup_top_bar(self):
        # Create the first status light and button
        self.compile_light = Light()
        self.compile_light.setFixedSize(15, 15)
        self.set_light_color(self.compile_light, 'yellow')  # Set initial color

        self.compile_button = QPushButton("Compile")

        self.top_toolbar.addWidget(self.compile_light)
        self.top_toolbar.addWidget(self.compile_button)

        # Create the second status light and button
        self.validate_light = Light()
        self.validate_light.setFixedSize(15, 15)
        self.set_light_color(self.validate_light, 'yellow')  # Set initial color

        self.validate_button = QPushButton("Validate")

        self.top_toolbar.addWidget(self.validate_light)
        self.top_toolbar.addWidget(self.validate_button)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.top_toolbar.addWidget(spacer)

        self.solve_button = QPushButton()
        pixmapi = QStyle.StandardPixmap.SP_MediaPlay
        icon = self.style().standardIcon(pixmapi)
        self.solve_button.setIcon(QIcon(icon))
        self.top_toolbar.addWidget(self.solve_button)

    def set_light_color(self, light, color_name):
        color = QColor(color_name)
        light.color = color
        light.update()  # Necessary to trigger a repaint after changing the color
    
    def create_toolbar(self, position):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(position, toolbar)
        return toolbar

    def add_button_to_toolbar(self, dock_name, toolbar):
        button = QPushButton()
        button.setIcon(QIcon("ui/icons/" + dock_name + ".png"))
        button.clicked.connect(lambda: self.reset_button_text(dock_name))
        button.clicked.connect(lambda: self.dock_manager.toggle_dock(dock_name))
        #button.setProperty("original_text", dock_name)

        if dock_name == "Output":
            spacer = QWidget()
            spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            toolbar.addWidget(spacer)

        toolbar.addWidget(button)
        self.toolbar_buttons[dock_name] = button

    def reset_button_text(self, dock_name):
        if dock_name in self.toolbar_buttons:
            button = self.toolbar_buttons[dock_name]
            original_text = button.property("original_text")
            button.setText(original_text)
        
    def change_button_text(self, button_name, new_text):
        if button_name in self.toolbar_buttons:
            self.toolbar_buttons[button_name].setText(new_text)
            
    def change_solve_button_text(self, text):
        self.solve_button.setText(text)
        
    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)

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
