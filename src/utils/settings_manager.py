"""
Settings Manager - Handles application settings persistence using QSettings
"""

import os
from PySide6.QtCore import QSettings


class SettingsManager:
    """Manages application settings using QSettings"""
    
    ORGANIZATION = "Acoustic Solutions"
    APPLICATION = "Acoustic Analysis Tool"
    
    # Settings keys
    KEY_DATABASE_CUSTOM_PATH = "database/custom_path"
    KEY_DATABASE_USE_CUSTOM_PATH = "database/use_custom_path"
    
    def __init__(self):
        """Initialize the settings manager"""
        self.settings = QSettings(SettingsManager.ORGANIZATION, SettingsManager.APPLICATION)
    
    def get_database_path(self):
        """
        Get the custom database path from settings, or None if not set
        
        Returns:
            str or None: Custom database path, or None if using default
        """
        use_custom = self.settings.value(self.KEY_DATABASE_USE_CUSTOM_PATH, False, type=bool)
        if use_custom:
            custom_path = self.settings.value(self.KEY_DATABASE_CUSTOM_PATH, None, type=str)
            if custom_path and os.path.exists(os.path.dirname(custom_path)):
                return custom_path
        return None
    
    def set_database_path(self, db_path):
        """
        Set the custom database path in settings
        
        Args:
            db_path (str): Full path to the database file
        """
        if db_path:
            self.settings.setValue(self.KEY_DATABASE_CUSTOM_PATH, db_path)
            self.settings.setValue(self.KEY_DATABASE_USE_CUSTOM_PATH, True)
        else:
            # Clear custom path and use default
            self.settings.remove(self.KEY_DATABASE_CUSTOM_PATH)
            self.settings.setValue(self.KEY_DATABASE_USE_CUSTOM_PATH, False)
        self.settings.sync()
    
    def clear_database_path(self):
        """Clear the custom database path and revert to default"""
        self.settings.remove(self.KEY_DATABASE_CUSTOM_PATH)
        self.settings.setValue(self.KEY_DATABASE_USE_CUSTOM_PATH, False)
        self.settings.sync()
    
    def is_using_custom_path(self):
        """
        Check if a custom database path is configured
        
        Returns:
            bool: True if custom path is set, False otherwise
        """
        return self.settings.value(self.KEY_DATABASE_USE_CUSTOM_PATH, False, type=bool)


# Global instance
_settings_manager = None


def get_settings_manager():
    """Get the global settings manager instance"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager

