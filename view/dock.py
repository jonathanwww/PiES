from PyQt6.QtWidgets import QMainWindow, QTextEdit, QDockWidget, QSizePolicy, QStatusBar, QMessageBox, QLabel, QStyle, \
    QWidget, QToolBar, QVBoxLayout, QPushButton, QFrame, QHBoxLayout
from PyQt6.QtGui import QFont
from .menu import MenuManager
from PyQt6.QtGui import QColor, QPainter, QBrush, QIcon
from PyQt6.QtCore import Qt, QSize


class DockManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.docks_map = {
            "Script": (Qt.DockWidgetArea.LeftDockWidgetArea, main_window.left_toolbar, False),
            "Plot": (Qt.DockWidgetArea.LeftDockWidgetArea, main_window.left_toolbar, False),
            "Output": (Qt.DockWidgetArea.BottomDockWidgetArea, main_window.left_toolbar, False),
            "Objects": (Qt.DockWidgetArea.RightDockWidgetArea, main_window.right_toolbar, False),
            "Namespace": (Qt.DockWidgetArea.RightDockWidgetArea, main_window.right_toolbar, False),
            "Graph": (Qt.DockWidgetArea.RightDockWidgetArea, main_window.right_toolbar, False),
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
        # for changing button bg color
        dock.visibilityChanged.connect(lambda visible: self.on_dock_visibility_changed(dock_name, visible))

        dock_widget_content = QWidget()
        dock_widget_content.setLayout(dock_layout)
        dock.setWidget(dock_widget_content)
        dock.setProperty('re_dock_button', re_dock_button)
        dock.widget().re_dock_button = re_dock_button

        if dock_name == "Output":
            dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        else:
            dock.setAllowedAreas(position)

        dock.topLevelChanged.connect(lambda top_level: self.on_dock_floating(dock, top_level))

        self.main_window.addDockWidget(position, dock)
        dock.setVisible(is_visible)
        self.docks_map[dock_name] = dock

    def on_dock_visibility_changed(self, dock_name, visible):
        dock = self.docks_map[dock_name]
        re_dock_button = dock.property('re_dock_button')  # Get the button
        is_floating = dock.isFloating()  # Check if the dock is floating
        re_dock_button.setVisible(is_floating)
        
        if visible:
            self.main_window.change_button_bg(dock_name, '#222222')
        else:
            self.main_window.reset_button_bg(dock_name)
        
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
            if other_dock != dock and not other_dock.isFloating() and self.main_window.dockWidgetArea(
                    other_dock) == position:
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
                    if self.main_window.dockWidgetArea(
                            dock) == toggle_dock_position and dock.isVisible() and not dock.isFloating():
                        dock.setVisible(False)

