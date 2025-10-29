#!/usr/bin/env python3
"""
Test script for the enhanced Acoustic Treatment tab in Component Library Dialog
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from ui.dialogs.component_library_dialog import ComponentLibraryDialog
from models import get_session
from models.project import Project

def main():
    app = QApplication(sys.argv)
    
    # Get a project ID for testing
    session = get_session()
    project = session.query(Project).first()
    session.close()
    
    if not project:
        print("No projects found in database. Create a project first.")
        return 1
    
    print(f"Testing Component Library Dialog with project: {project.name} (ID: {project.id})")
    
    # Create and show the dialog
    dialog = ComponentLibraryDialog(project_id=project.id)
    dialog.show()
    
    print("\n=== Test Instructions ===")
    print("1. Open the 'Acoustic Treatment' tab")
    print("2. Verify the left side shows 'Acoustic Materials' with a filter checkbox")
    print("3. Verify the right side shows 'Material Schedules by Drawing Set'")
    print("4. Check that materials list loads (or shows placeholder text)")
    print("5. Click 'Manual Treatment Add' to test the add dialog")
    print("6. Try selecting a material to see absorption coefficients")
    print("7. Test editing absorption values in the table")
    print("8. Test the 'Show only project materials' filter")
    print("9. Test Edit and Delete buttons")
    print("========================\n")
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

