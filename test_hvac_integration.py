#!/usr/bin/env python3
"""
Test script for HVAC integration in Project Dashboard
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from models import get_session, Project
from ui.project_dashboard import ProjectDashboard


def test_hvac_integration():
    """Test the HVAC integration in the project dashboard"""
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    try:
        # Get a test project
        session = get_session()
        project = session.query(Project).first()
        session.close()
        
        if not project:
            print("No projects found in database. Please create a project first.")
            return
        
        print(f"Testing HVAC integration with project: {project.name}")
        
        # Create project dashboard
        dashboard = ProjectDashboard(project.id)
        dashboard.show()
        
        print("Project Dashboard opened successfully!")
        print("HVAC Paths tab should now contain the comprehensive HVAC management interface.")
        print("Features available:")
        print("- Create and edit HVAC paths")
        print("- Manage HVAC components")
        print("- Configure duct segments with fittings")
        print("- Analyze HVAC noise paths")
        print("- Export analysis results")
        
        # Run the application
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"Error testing HVAC integration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_hvac_integration() 