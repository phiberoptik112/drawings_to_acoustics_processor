#!/usr/bin/env python3
"""
Test script to programmatically create a project and verify the application works.
This demonstrates the "New Project" functionality when GUI interaction is not available.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import initialize_database, get_session, Project
from sqlalchemy import inspect

def create_test_project():
    """Create a test project programmatically"""
    print("Initializing database...")
    db_path = initialize_database()
    print(f"Database initialized at: {db_path}")
    
    print("\nCreating 'Test Project'...")
    session = get_session()
    
    # Create new project
    project = Project(
        name="Test Project",
        description="Test project created programmatically for demonstration",
        location="Test Location",
        default_scale=0.25,  # 1/4" = 1'
        default_units="imperial"
    )
    
    session.add(project)
    session.commit()
    
    print(f"✓ Project created successfully!")
    print(f"  - ID: {project.id}")
    print(f"  - Name: {project.name}")
    print(f"  - Description: {project.description}")
    print(f"  - Location: {project.location}")
    print(f"  - Scale: {project.default_scale}")
    print(f"  - Units: {project.default_units}")
    print(f"  - Created: {project.created_date}")
    
    # Verify project exists
    print("\nVerifying project in database...")
    all_projects = session.query(Project).all()
    print(f"Total projects in database: {len(all_projects)}")
    for p in all_projects:
        print(f"  - {p.name} (ID: {p.id})")
    
    session.close()
    
    print("\n✓ Test completed successfully!")
    print(f"\nThe project 'Test Project' has been created and can be opened")
    print(f"from the splash screen by clicking on it in the Recent Projects list,")
    print(f"or by using the project dashboard functionality.")
    
    return project.id

if __name__ == "__main__":
    try:
        project_id = create_test_project()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
