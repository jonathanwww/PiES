import os
from PyQt6.QtGui import QAction
from view.editor.editor import PythonEditor
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout, QMenuBar, QFileDialog
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtWidgets import QMainWindow, QMenu
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QDialog, QPushButton, QGroupBox, QGridLayout
from PyQt6.QtGui import QIcon


class MenuManager(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        # self.file_operations = file_operations
        self._setup_menu_bar()

    def _setup_menu_bar(self):
        # Create the menu bar
        menu_bar = QMenuBar(self.main_window)
        self.main_window.setMenuBar(menu_bar)

        self._create_app_menu(menu_bar)
        self._create_file_menu(menu_bar)
        self._create_help_menu(menu_bar)

    def _create_app_menu(self, menu_bar):
        app_menu = menu_bar.addMenu("PiES")

        about_action = QAction("_About PiES", self.main_window)
        app_menu.addAction(about_action)
        update_action = QAction("Check for updates", self.main_window)
        app_menu.addAction(update_action)
        
        app_menu.addSeparator()

        settings_action = QAction("_Settings", self.main_window)
        settings_action.triggered.connect(self.open_settings)
        app_menu.addAction(settings_action)
    
        app_menu.addSeparator()
        quit_action = QAction("_Quit", self.main_window)
        quit_action.triggered.connect(self.open_solver_settings)
        app_menu.addAction(quit_action)
        
    def open_settings(self):
        self.settings_dialog = SettingsDialog(self.main_window)
        self.settings_dialog.exec()
    
    def _create_file_menu(self, menu_bar):
        file_menu = menu_bar.addMenu("File")

        new_file_action = QAction("New..", self.main_window)
        # new_file_action.triggered.connect(self.file_operations.new_file)
        file_menu.addAction(new_file_action)

        load_file_action = QAction("Open..", self.main_window)
        # load_file_action.triggered.connect(self.file_operations.load_file)
        file_menu.addAction(load_file_action)

        save_file_action = QAction("Save as..", self.main_window)
        # save_file_action.triggered.connect(self.file_operations.save_file)
        file_menu.addAction(save_file_action)

        # Create 'Recent' submenu
        recent_menu = QMenu('Recent', self.main_window)

        # Create actions for 'Recent' submenu
        recent_action1 = QAction('Recent File 1', self.main_window)
        recent_action2 = QAction('Recent File 2', self.main_window)

        # Connect actions to some functions if needed
        # recent_action1.triggered.connect(self.some_function1)
        # recent_action2.triggered.connect(self.some_function2)

        # Add actions to 'Recent' submenu
        recent_menu.addAction(recent_action1)
        recent_menu.addAction(recent_action2)

        # Add 'Recent' submenu to 'File' menu
        file_menu.addMenu(recent_menu)

        file_menu.addSeparator()
        export_file_action = QAction("Export results", self.main_window)
        file_menu.addAction(export_file_action)

    def _create_help_menu(self, menu_bar): 
        help_menu = menu_bar.addMenu("Help")

        help_action = QAction("Python help", self.main_window)
        help_action.triggered.connect(self.open_help)
        help_menu.addAction(help_action)
    
    def open_general_settings(self):
        dialog = EditorSettingsDialog(self.main_window)
        dialog.exec()
        
    def open_solver_settings(self):
        dialog = SolverSettingsDialog(self.main_window)
        dialog.exec()

    def open_help(self):
        dialog = HelpDialog(self.main_window)
        dialog.exec()


class EditorSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Editor Settings')

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.font_size = QLineEdit()
        self.font_family = QLineEdit()

        self.form_layout.addRow(QLabel('Font Size'), self.font_size)
        self.form_layout.addRow(QLabel('Font Family'), self.font_family)

        self.save_button = QPushButton('Save', self)
        self.save_button.clicked.connect(self.save_settings)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_button)

        self.setLayout(self.layout)

    def save_settings(self):
        # Implement the saving of the configs here
        font_size = self.font_size.text()
        font_family = self.font_family.text()

        # Emit the signal with new configs
        self.parent().settings_changed.emit(font_size, font_family)

        self.close()

# TODO: broken
class FileOperations:
    def __init__(self, text_editor, status_bar, window_title):
        self.text_editor = text_editor
        self.status_bar = status_bar
        self.window_title = window_title
        self.current_file_path = None
        self.is_saved = True

    def new_file(self):
        self.centralWidget().clear()
        self.setWindowTitle("Untitled")
        self.current_file_path = None
        self.is_saved = True
        self.update_save_status()  # Update the save status after clearing the text editor

    def save_file(self):
        if self.current_file_path:
            self.save_to_path(self.current_file_path)
        else:
            self.save_file_as()

    def save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File")
        if file_path:
            self.save_to_path(file_path)

    def save_to_path(self, file_path):
        try:
            with open(file_path, "w") as file:
                file.write(self.text_editor.toPlainText())
                self.setWindowTitle(f"{file_path}{'*' if not self.is_saved else ''}")
                self.current_file_path = file_path
                self.is_saved = True
                self.update_save_status()  # Update the save status after saving the file
        except Exception as e:
            self.statusBar().showMessage(f"Error: {str(e)}")

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File")
        if file_path:
            try:
                with open(file_path, "r") as file:
                    self.text_editor.setPlainText(file.read())
                    self.setWindowTitle(f"{file_path}{'*' if not self.is_saved else ''}")
                    self.current_file_path = file_path
                    self.is_saved = True
                    self.update_save_status()  # Update the save status after loading the file
            except Exception as e:
                self.statusBar().showMessage(f"Error: {str(e)}")

    def update_save_status(self):
        if self.centralWidget().text():
            self.is_saved = False
            self.setWindowTitle(f"{self.current_file_path or 'Untitled'}{'*' if not self.is_saved else ''}")
        else:
            self.is_saved = True
            self.setWindowTitle(self.current_file_path or "Untitled")

class SolverSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Settings')

        self.layout = QVBoxLayout()

        self.solver_label = QLabel('Solver')
        self.solver_editor = PythonEditor()
        self.solver_editor.clear()
        self.layout.addWidget(self.solver_label)
        self.layout.addWidget(self.solver_editor)

        self.diff_eq_solver_label = QLabel('Differential Equation Solver')
        self.diff_eq_solver_editor = PythonEditor()
        self.diff_eq_solver_editor.clear()
        self.layout.addWidget(self.diff_eq_solver_label)
        self.layout.addWidget(self.diff_eq_solver_editor)

        self.setLayout(self.layout)


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Help')

        self.layout = QVBoxLayout()

        self.help_label = QLabel('Python tips')
        self.help_box = PythonEditor()
        self.help_box.clear()
        self.layout.addWidget(self.help_label)
        self.layout.addWidget(self.help_box)

        # set help text
        pth = os.path.dirname(__file__)
        pth = os.path.join(pth, "default_text/editor.default.python.help.txt")
        self.help_box.setTextFromFile(pth)

        self.setLayout(self.layout)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)

        self.setWindowTitle("Settings")

        self.tab_widget = QTabWidget(self)
        self.general_settings_tab = QGroupBox("General")
        self.style_settings_tab = QGroupBox("Style")
        self.shortcut_settings_tab = QGroupBox("Shortcuts")
        self.editor_settings_tab = QGroupBox("Editor")
        self.solver_settings_tab = QGroupBox("Solver")
        self.equation_system_settings_tab = QGroupBox("Equation System")

        self.tab_widget.addTab(self.general_settings_tab, "General")
        self.tab_widget.addTab(self.style_settings_tab, "Style")
        self.tab_widget.addTab(self.shortcut_settings_tab, "Shortcuts")
        self.tab_widget.addTab(self.editor_settings_tab, "Editor")
        self.tab_widget.addTab(self.solver_settings_tab, "Solver")
        self.tab_widget.addTab(self.equation_system_settings_tab, "Equation System")

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.tab_widget)

        self.setLayout(self.layout)