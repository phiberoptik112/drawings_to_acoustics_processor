"""
Project Dialog - Create new project dialog
"""

import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, QComboBox,
                             QFileDialog, QFormLayout, QMessageBox)
from PyQt5.QtCore import Qt


class ProjectDialog(QDialog):
    """Dialog for creating new projects"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("New Project")
        self.setModal(True)
        self.setFixedSize(500, 350)
        
        # Main layout
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        # Project name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter project name (required)")
        form_layout.addRow("Project Name:", self.name_edit)
        
        # Project description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Optional project description")
        form_layout.addRow("Description:", self.description_edit)
        
        # Project location
        location_layout = QHBoxLayout()
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Project database location")
        
        # Set default location
        default_location = os.path.expanduser("~/Documents/AcousticAnalysis")
        self.location_edit.setText(default_location)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_location)
        
        location_layout.addWidget(self.location_edit)
        location_layout.addWidget(self.browse_btn)
        
        form_layout.addRow("Location:", location_layout)
        
        # Default scale
        self.scale_combo = QComboBox()
        self.scale_combo.addItems([
            "1:50", "1:100", "1:200", "1:400", "1:500", "1:1000"
        ])
        self.scale_combo.setCurrentText("1:100")
        form_layout.addRow("Default Scale:", self.scale_combo)
        
        # Default units
        self.units_combo = QComboBox()
        self.units_combo.addItems(["feet", "meters"])
        form_layout.addRow("Default Units:", self.units_combo)
        
        layout.addLayout(form_layout)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("Create Project")
        self.create_btn.clicked.connect(self.accept_project)
        self.create_btn.setDefault(True)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.create_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Set focus to name field
        self.name_edit.setFocus()
        
    def browse_location(self):
        """Browse for project location"""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Select Project Location", 
            self.location_edit.text()
        )
        
        if directory:
            self.location_edit.setText(directory)
            
    def accept_project(self):
        """Validate and accept project creation"""
        name = self.name_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Project name is required.")
            self.name_edit.setFocus()
            return
            
        location = self.location_edit.text().strip()
        if not location:
            QMessageBox.warning(self, "Validation Error", "Project location is required.")
            return
            
        # Create directory if it doesn't exist
        try:
            os.makedirs(location, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create directory:\n{str(e)}")
            return
            
        # Check if we can write to the location
        if not os.access(location, os.W_OK):
            QMessageBox.critical(self, "Error", "Cannot write to the selected location.")
            return
            
        self.accept()
        
    def get_project_data(self):
        """Get the project data from the dialog"""
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'location': self.location_edit.text().strip(),
            'scale': self.scale_combo.currentText(),
            'units': self.units_combo.currentText()
        }