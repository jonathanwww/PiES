import os
from PyQt6.QtGui import QAction
from ui.widgets.editor import PythonEditor
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout, QMenuBar, QFileDialog


class MenuManager:
    def __init__(self, main_window):
        self.main_window = main_window
        # self.file_operations = file_operations
        self._setup_menu_bar()

    def _setup_menu_bar(self):
        # Create the menu bar
        menu_bar = QMenuBar(self.main_window)
        self.main_window.setMenuBar(menu_bar)

        # File Menu
        # self._create_file_menu(menu_bar)

        # Settings Menu
        self._create_settings_menu(menu_bar)

        # Help Menu
        self._create_help_menu(menu_bar)

    def _create_file_menu(self, menu_bar):
        file_menu = menu_bar.addMenu("File")

        new_file_action = QAction("New", self.main_window)
        new_file_action.triggered.connect(self.file_operations.new_file)
        file_menu.addAction(new_file_action)

        save_file_action = QAction("Save", self.main_window)
        save_file_action.triggered.connect(self.file_operations.save_file)
        file_menu.addAction(save_file_action)

        load_file_action = QAction("Load", self.main_window)
        load_file_action.triggered.connect(self.file_operations.load_file)
        file_menu.addAction(load_file_action)

        file_menu.addSeparator()
        export_file_action = QAction("Export results as csv", self.main_window)
        file_menu.addAction(export_file_action)

    def _create_settings_menu(self, menu_bar):
        settings_menu = menu_bar.addMenu("Settings")

        solver_action = QAction("Solver", self.main_window)
        solver_action.triggered.connect(self.open_solver_settings)
        settings_menu.addAction(solver_action)

        equationsystem_action = QAction("Equation system", self.main_window)
        settings_menu.addAction(equationsystem_action)

        styles_action = QAction("Styles", self.main_window)
        settings_menu.addAction(styles_action)

    def _create_help_menu(self, menu_bar):
        help_menu = menu_bar.addMenu("Help")

        help_action = QAction("Python help", self.main_window)
        help_action.triggered.connect(self.open_help)
        help_menu.addAction(help_action)

    def open_solver_settings(self):
        dialog = SolverSettingsDialog(self.main_window)
        dialog.exec()

    def open_help(self):
        dialog = HelpDialog(self.main_window)
        dialog.exec()


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
