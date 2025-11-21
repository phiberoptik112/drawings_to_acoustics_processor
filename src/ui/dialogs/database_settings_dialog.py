"""
Database Settings Dialog - Manage database path and location
"""

import os
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QProgressDialog,
    QCheckBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from models import initialize_database, close_database
from utils.settings_manager import get_settings_manager
from utils.database_manager import (
    get_database_info,
    validate_database_path,
    copy_database,
    format_file_size
)


class DatabaseCopyThread(QThread):
    """Thread for copying database to avoid blocking UI"""
    progress = Signal(int, int)  # current, total
    finished = Signal(bool, str)  # success, error_message
    
    def __init__(self, source_path, dest_path):
        super().__init__()
        self.source_path = source_path
        self.dest_path = dest_path
    
    def run(self):
        """Run the database copy operation"""
        def progress_callback(current, total):
            self.progress.emit(current, total)
        
        success, error_msg = copy_database(
            self.source_path,
            self.dest_path,
            progress_callback
        )
        self.finished.emit(success, error_msg or "")


class DatabaseSettingsDialog(QDialog):
    """Dialog for managing database path and location"""
    
    def __init__(self, parent=None, current_db_path=None):
        super().__init__(parent)
        self.current_db_path = current_db_path
        self.settings_manager = get_settings_manager()
        self.copy_thread = None
        self.progress_dialog = None
        
        self.setWindowTitle("Database Settings")
        self.setModal(True)
        self.resize(700, 500)
        
        self.init_ui()
        self.refresh_info()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Database Settings")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_info)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Current Database Information
        current_group = QGroupBox("Current Database")
        current_layout = QFormLayout()
        
        self.current_path_label = QLabel()
        self.current_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.current_path_label.setWordWrap(True)
        current_layout.addRow("Path:", self.current_path_label)
        
        self.size_label = QLabel()
        current_layout.addRow("Size:", self.size_label)
        
        self.modified_label = QLabel()
        current_layout.addRow("Last Modified:", self.modified_label)
        
        self.projects_label = QLabel()
        current_layout.addRow("Projects:", self.projects_label)
        
        current_group.setLayout(current_layout)
        layout.addWidget(current_group)
        
        # Change Database Location
        change_group = QGroupBox("Change Database Location")
        change_layout = QVBoxLayout()
        
        info_label = QLabel(
            "Copy the current database to a new location. The original database will remain unchanged."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        change_layout.addWidget(info_label)
        
        path_layout = QHBoxLayout()
        self.new_path_edit = QLineEdit()
        self.new_path_edit.setPlaceholderText("Select a new database location...")
        path_layout.addWidget(self.new_path_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_new_location)
        path_layout.addWidget(browse_btn)
        
        change_layout.addLayout(path_layout)
        
        # Options
        self.create_new_checkbox = QCheckBox("Create new empty database instead of copying")
        self.create_new_checkbox.setToolTip(
            "If checked, creates a new empty database at the selected location instead of copying the existing one."
        )
        change_layout.addWidget(self.create_new_checkbox)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.copy_btn = QPushButton("Copy Database")
        self.copy_btn.clicked.connect(self.copy_database_to_new_location)
        self.copy_btn.setEnabled(False)
        button_layout.addWidget(self.copy_btn)
        
        change_layout.addLayout(button_layout)
        
        change_group.setLayout(change_layout)
        layout.addWidget(change_group)
        
        # Reset to Default
        reset_group = QGroupBox("Reset to Default")
        reset_layout = QVBoxLayout()
        
        reset_info = QLabel(
            "Clear the custom database path and use the default location:\n"
            "~/Documents/AcousticAnalysis/acoustic_analysis.db"
        )
        reset_info.setWordWrap(True)
        reset_info.setStyleSheet("color: #666; margin-bottom: 10px;")
        reset_layout.addWidget(reset_info)
        
        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(self.reset_to_default)
        reset_layout.addWidget(reset_btn)
        
        reset_group.setLayout(reset_layout)
        layout.addWidget(reset_group)
        
        # Dialog buttons
        dialog_buttons = QHBoxLayout()
        dialog_buttons.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        dialog_buttons.addWidget(close_btn)
        
        layout.addLayout(dialog_buttons)
        
        # Connect path edit changes
        self.new_path_edit.textChanged.connect(self.on_path_changed)
    
    def refresh_info(self):
        """Refresh database information display"""
        if not self.current_db_path:
            # Try to get current path from database engine
            try:
                from models.database import engine
                if engine:
                    db_url = str(engine.url)
                    # Extract path from sqlite:///path format
                    if db_url.startswith('sqlite:///'):
                        self.current_db_path = db_url[10:]  # Remove 'sqlite:///'
            except Exception:
                pass
        
        if not self.current_db_path:
            # Fall back to default
            self.current_db_path = os.path.expanduser("~/Documents/AcousticAnalysis/acoustic_analysis.db")
        
        # Display current path
        self.current_path_label.setText(self.current_db_path)
        
        # Get database info
        info = get_database_info(self.current_db_path)
        
        if info['exists']:
            self.size_label.setText(format_file_size(info['size']))
            
            if info['modified_date']:
                self.modified_label.setText(
                    info['modified_date'].strftime('%Y-%m-%d %H:%M:%S')
                )
            else:
                self.modified_label.setText("Unknown")
            
            self.projects_label.setText(f"{info['project_count']} project(s)")
        else:
            self.size_label.setText("Database not found")
            self.modified_label.setText("N/A")
            self.projects_label.setText("0 projects")
    
    def browse_new_location(self):
        """Browse for a new database location"""
        # Get default directory
        default_dir = os.path.expanduser("~/Documents")
        if self.current_db_path:
            default_dir = os.path.dirname(self.current_db_path)
        
        # Open file dialog to select location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select New Database Location",
            os.path.join(default_dir, "acoustic_analysis.db"),
            "Database Files (*.db);;All Files (*)"
        )
        
        if file_path:
            self.new_path_edit.setText(file_path)
    
    def on_path_changed(self):
        """Handle path edit text change"""
        new_path = self.new_path_edit.text().strip()
        if new_path:
            # Validate path
            is_valid, error_msg = validate_database_path(new_path)
            if is_valid:
                self.copy_btn.setEnabled(True)
                self.copy_btn.setToolTip("")
            else:
                self.copy_btn.setEnabled(False)
                self.copy_btn.setToolTip(error_msg or "Invalid path")
        else:
            self.copy_btn.setEnabled(False)
            self.copy_btn.setToolTip("")
    
    def copy_database_to_new_location(self):
        """Copy database to the new location"""
        new_path = self.new_path_edit.text().strip()
        if not new_path:
            QMessageBox.warning(self, "Invalid Path", "Please select a valid database location.")
            return
        
        # Validate path
        is_valid, error_msg = validate_database_path(new_path)
        if not is_valid:
            QMessageBox.warning(self, "Invalid Path", error_msg or "The selected path is invalid.")
            return
        
        # Check if creating new or copying
        create_new = self.create_new_checkbox.isChecked()
        
        if create_new:
            # Create new empty database
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                
                # Close current database
                close_database()
                
                # Initialize new database
                initialize_database(new_path)
                
                # Save settings
                self.settings_manager.set_database_path(new_path)
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"New database created at:\n{new_path}\n\n"
                    "The application will use this database on next startup."
                )
                
                # Refresh info
                self.current_db_path = new_path
                self.refresh_info()
                self.new_path_edit.clear()
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create new database:\n{str(e)}"
                )
        else:
            # Copy existing database
            if not os.path.exists(self.current_db_path):
                QMessageBox.warning(
                    self,
                    "Source Not Found",
                    f"Current database not found:\n{self.current_db_path}"
                )
                return
            
            # Check if destination exists
            if os.path.exists(new_path):
                reply = QMessageBox.question(
                    self,
                    "File Exists",
                    f"A file already exists at:\n{new_path}\n\n"
                    "Do you want to overwrite it?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
                try:
                    os.remove(new_path)
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Cannot remove existing file:\n{str(e)}"
                    )
                    return
            
            # Get file size for progress
            file_size = os.path.getsize(self.current_db_path)
            
            # Show progress dialog
            self.progress_dialog = QProgressDialog(
                "Copying database...",
                "Cancel",
                0,
                file_size,
                self
            )
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setValue(0)
            
            # Create and start copy thread
            self.copy_thread = DatabaseCopyThread(self.current_db_path, new_path)
            self.copy_thread.progress.connect(self.on_copy_progress)
            self.copy_thread.finished.connect(self.on_copy_finished)
            self.copy_thread.start()
    
    def on_copy_progress(self, current, total):
        """Handle copy progress update"""
        if self.progress_dialog:
            self.progress_dialog.setValue(current)
            if current >= total:
                self.progress_dialog.setValue(total)
    
    def on_copy_finished(self, success, error_msg):
        """Handle copy completion"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        if success:
            # Save new path to settings
            new_path = self.new_path_edit.text().strip()
            self.settings_manager.set_database_path(new_path)
            
            QMessageBox.information(
                self,
                "Success",
                f"Database copied successfully to:\n{new_path}\n\n"
                "The application will use this database on next startup.\n"
                "Please restart the application for the change to take effect."
            )
            
            # Refresh info
            self.current_db_path = new_path
            self.refresh_info()
            self.new_path_edit.clear()
        else:
            QMessageBox.critical(
                self,
                "Copy Failed",
                f"Failed to copy database:\n{error_msg}"
            )
    
    def reset_to_default(self):
        """Reset database path to default"""
        reply = QMessageBox.question(
            self,
            "Reset to Default",
            "This will clear the custom database path and use the default location.\n\n"
            "The current database will not be moved or deleted.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.settings_manager.clear_database_path()
            QMessageBox.information(
                self,
                "Reset Complete",
                "Database path reset to default.\n"
                "The application will use the default location on next startup."
            )

