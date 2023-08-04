import json
import os
from PyQt6.QtCore import QSettings, pyqtSignal


class SettingsManager:
    settings_changed = pyqtSignal()

    def __init__(self, default_settings_path):
        self.settings = QSettings()
        self.default_settings = self.load_default_settings(default_settings_path)
        self.current_settings = {}

    def load_default_settings(self, default_settings_path):
        with open(default_settings_path, 'r') as f:
            return json.load(f)

    def load_settings(self):
        for key, value in self.default_settings.items():
            self.current_settings[key] = self.settings.value(key, defaultValue=value)
        self.settings_changed.emit()

    def apply_settings(self):
        for key, value in self.current_settings.items():
            self.settings.setValue(key, value)

    def get_value(self, key):
        return self.current_settings.get(key, None)

    def set_value(self, key, value):
        self.current_settings[key] = value
        self.settings_changed.emit()
