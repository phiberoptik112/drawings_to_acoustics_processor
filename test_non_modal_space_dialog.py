#!/usr/bin/env python3
"""
Test script to verify that the Edit Space Properties dialog is now non-modal
and allows users to interact with other windows while it's open.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QLabel
from PySide6.QtCore import Qt

from models import get_session, init_db
from models.space import Space
from ui.dialogs.space_edit_dialog import SpaceEditDialog


class TestWindow(QMainWindow):
    """Test window to demonstrate non-modal behavior"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Window - Main Application")
        self.resize(600, 400)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Instructions
        instructions = QLabel(
            "Instructions:\n"
            "1. Click 'Open Edit Space Dialog' to open the space properties dialog\n"
            "2. The dialog should open as an independent window\n"
            "3. You should be able to interact with this window while the dialog is open\n"
            "4. Try typing in the text area below while the dialog is open\n"
            "5. Try arranging both windows side by side\n"
            "6. This simulates viewing a PDF reference while editing space properties"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Button to open dialog
        self.open_btn = QPushButton("Open Edit Space Dialog")
        self.open_btn.clicked.connect(self.open_dialog)
        layout.addWidget(self.open_btn)
        
        # Text area to test interactivity
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "Type here while the dialog is open to test non-modal behavior...\n\n"
            "If this is non-modal, you should be able to type here while the "
            "Edit Space Properties dialog is open."
        )
        layout.addWidget(self.text_edit)
        
        # Status label
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)
        
        # Store dialog references
        self.dialogs = []
        
    def open_dialog(self):
        """Open the Edit Space Properties dialog"""
        try:
            # Get or create a test space
            session = get_session()
            space = session.query(Space).first()
            
            if not space:
                self.status_label.setText("Status: No spaces found in database. Please create a project first.")
                session.close()
                return
            
            # Create the dialog
            dialog = SpaceEditDialog(self, space)
            
            # Connect signals
            dialog.space_updated.connect(self.on_space_updated)
            dialog.finished.connect(lambda: self.on_dialog_closed(dialog))
            
            # Store reference
            self.dialogs.append(dialog)
            
            # Show as non-modal
            dialog.show()
            
            self.status_label.setText(
                f"Status: Edit Space dialog opened for '{space.name}'. "
                f"Try interacting with this window!"
            )
            
            session.close()
            
        except Exception as e:
            self.status_label.setText(f"Status: Error - {str(e)}")
    
    def on_space_updated(self):
        """Handle when space is updated"""
        self.status_label.setText("Status: Space updated successfully!")
    
    def on_dialog_closed(self, dialog):
        """Handle dialog cleanup"""
        if dialog in self.dialogs:
            self.dialogs.remove(dialog)
        self.status_label.setText("Status: Dialog closed")


def main():
    # Initialize database
    init_db()
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create test window
    window = TestWindow()
    window.show()
    
    # Run
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

