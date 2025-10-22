#!/usr/bin/env python3
"""
Test script to verify that the Component Library dialog is now non-modal
and allows users to interact with other windows while it's open.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QLabel, QListWidget
from PySide6.QtCore import Qt

from models import get_session, init_db, Project
from ui.dialogs.component_library_dialog import ComponentLibraryDialog


class TestWindow(QMainWindow):
    """Test window to demonstrate non-modal behavior of Component Library"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Window - Main Application")
        self.resize(700, 500)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Instructions
        instructions = QLabel(
            "Instructions:\n"
            "1. Click 'Open Component Library' to open the library\n"
            "2. The library should open as an independent window\n"
            "3. You should be able to interact with this window while the library is open\n"
            "4. Try typing in the text area below while the library is open\n"
            "5. Try clicking the 'Open Component Library' button again - it should bring the existing window to front\n"
            "6. Try arranging both windows side by side\n"
            "7. Make changes in the library and verify the update counter increments"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Button to open library
        self.open_btn = QPushButton("Open Component Library")
        self.open_btn.clicked.connect(self.open_library)
        layout.addWidget(self.open_btn)
        
        # Update counter
        self.update_count = 0
        self.update_label = QLabel(f"Library updates received: {self.update_count}")
        layout.addWidget(self.update_label)
        
        # Text area to test interactivity
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "Type here while the Component Library is open to test non-modal behavior...\n\n"
            "If this is non-modal, you should be able to type here, select from the list below, "
            "and interact with any part of this window while the Component Library is open."
        )
        layout.addWidget(self.text_edit)
        
        # Test list
        self.test_list = QListWidget()
        self.test_list.addItems([
            "Test Item 1 - Click me while library is open",
            "Test Item 2 - Selection should work",
            "Test Item 3 - Everything should be interactive",
            "Test Item 4 - Library is non-modal!",
            "Test Item 5 - You can interact with both windows"
        ])
        layout.addWidget(self.test_list)
        
        # Status label
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)
        
        # Store library reference
        self.component_library_dialog = None
        
        # Get a project ID for testing
        self.project_id = self.get_test_project_id()
        
    def get_test_project_id(self):
        """Get or create a test project"""
        try:
            session = get_session()
            project = session.query(Project).first()
            if not project:
                # Create a test project
                project = Project(name="Test Project", location="Test Location")
                session.add(project)
                session.commit()
            project_id = project.id
            session.close()
            return project_id
        except Exception as e:
            self.status_label.setText(f"Status: Error getting project - {str(e)}")
            return None
    
    def open_library(self):
        """Open the Component Library dialog"""
        if not self.project_id:
            self.status_label.setText("Status: No project available. Please create a project first.")
            return
        
        try:
            # If dialog already exists and is visible, just raise it to front
            if self.component_library_dialog and self.component_library_dialog.isVisible():
                self.component_library_dialog.raise_()
                self.component_library_dialog.activateWindow()
                self.status_label.setText(
                    "Status: Component Library already open - brought to front (singleton pattern works!)"
                )
                return
            
            # Create the dialog
            dialog = ComponentLibraryDialog(self, project_id=self.project_id)
            
            # Connect signals
            dialog.library_updated.connect(self.on_library_updated)
            dialog.finished.connect(self.on_library_closed)
            
            # Store reference
            self.component_library_dialog = dialog
            
            # Show as non-modal
            dialog.show()
            
            self.status_label.setText(
                "Status: Component Library opened as non-modal window. "
                "Try interacting with this window!"
            )
            
        except Exception as e:
            self.status_label.setText(f"Status: Error - {str(e)}")
    
    def on_library_updated(self):
        """Handle when library is updated"""
        self.update_count += 1
        self.update_label.setText(f"Library updates received: {self.update_count}")
        self.status_label.setText(
            f"Status: Library data updated! Total updates: {self.update_count}"
        )
    
    def on_library_closed(self):
        """Handle library cleanup"""
        self.component_library_dialog = None
        self.status_label.setText("Status: Component Library closed")


def main():
    # Initialize database
    init_db()
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create test window
    window = TestWindow()
    window.show()
    
    # Show helpful message
    print("\n" + "="*70)
    print("Component Library Non-Modal Test")
    print("="*70)
    print("This test demonstrates the non-modal behavior of the Component Library.")
    print("\nWhat to test:")
    print("1. Open the library and verify you can still interact with the main window")
    print("2. Type in the text area while the library is open")
    print("3. Select items from the list while the library is open")
    print("4. Click 'Open Component Library' again to test singleton pattern")
    print("5. Make changes in the library (add/edit/delete) to test update signals")
    print("6. Position windows side-by-side to simulate real workflow")
    print("="*70 + "\n")
    
    # Run
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

