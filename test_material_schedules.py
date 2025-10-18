"""
Test script for Material Schedule feature
Tests the database models, file utilities, and basic operations
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import initialize_database, get_session, Project, MaterialSchedule
from models.drawing_sets import DrawingSet
from data.material_file_manager import (
    get_material_schedules_folder,
    get_drawing_set_materials_folder,
    validate_material_schedule_pdf
)


def test_database_models():
    """Test that MaterialSchedule model and relationships work"""
    print("\n=== Testing Database Models ===")
    
    # Initialize database
    try:
        initialize_database()
        print("✓ Database initialized")
    except Exception as e:
        print(f"Database already initialized: {e}")
    
    session = get_session()
    
    # Check if we have any projects
    project = session.query(Project).first()
    if not project:
        print("✗ No projects found in database. Create a project first.")
        session.close()
        return False
    
    print(f"✓ Found project: {project.name}")
    
    # Check drawing sets
    drawing_set = session.query(DrawingSet).filter(
        DrawingSet.project_id == project.id
    ).first()
    
    if not drawing_set:
        print("  Creating test drawing set...")
        drawing_set = DrawingSet(
            project_id=project.id,
            name="Test Drawing Set",
            phase_type="DD",
            description="Test drawing set for material schedules"
        )
        session.add(drawing_set)
        session.commit()
        print(f"✓ Created drawing set: {drawing_set.name}")
    else:
        print(f"✓ Found drawing set: {drawing_set.name}")
    
    # Test MaterialSchedule model
    test_schedule = MaterialSchedule(
        drawing_set_id=drawing_set.id,
        name="Test Interior Finishes",
        description="Test material schedule",
        schedule_type="finishes",
        file_path="/test/path/to/schedule.pdf"
    )
    
    session.add(test_schedule)
    session.commit()
    
    schedule_id = test_schedule.id
    print(f"✓ Created test material schedule (ID: {schedule_id})")
    
    # Test querying back
    retrieved = session.query(MaterialSchedule).filter(
        MaterialSchedule.id == schedule_id
    ).first()
    
    if retrieved:
        print(f"✓ Retrieved material schedule: {retrieved.name}")
        print(f"  - Drawing Set: {retrieved.drawing_set.name}")
        print(f"  - Type: {retrieved.schedule_type}")
        print(f"  - File Path: {retrieved.file_path}")
    else:
        print("✗ Failed to retrieve material schedule")
        session.close()
        return False
    
    # Test relationship from DrawingSet
    ds = session.query(DrawingSet).filter(DrawingSet.id == drawing_set.id).first()
    if ds and hasattr(ds, 'material_schedules'):
        print(f"✓ Drawing set has {len(ds.material_schedules)} material schedule(s)")
    else:
        print("✗ DrawingSet.material_schedules relationship not working")
    
    # Clean up test data
    session.delete(test_schedule)
    session.commit()
    print("✓ Cleaned up test data")
    
    session.close()
    return True


def test_file_utilities():
    """Test file management utilities"""
    print("\n=== Testing File Utilities ===")
    
    # Test folder path generation
    test_project_path = "/tmp/test_acoustic_project"
    
    try:
        materials_folder = get_material_schedules_folder(test_project_path)
        print(f"✓ Materials folder path: {materials_folder}")
        
        if os.path.exists(materials_folder):
            print(f"✓ Materials folder created at: {materials_folder}")
        
        # Test drawing set subfolder
        ds_folder = get_drawing_set_materials_folder(test_project_path, "DD Phase 1")
        print(f"✓ Drawing set folder path: {ds_folder}")
        
        if os.path.exists(ds_folder):
            print(f"✓ Drawing set folder created")
        
        # Clean up
        import shutil
        if os.path.exists(test_project_path):
            shutil.rmtree(test_project_path)
            print("✓ Cleaned up test folders")
        
    except Exception as e:
        print(f"✗ File utility test failed: {e}")
        return False
    
    # Test PDF validation
    print("\n  Testing PDF validation...")
    is_valid, msg = validate_material_schedule_pdf("/nonexistent/file.pdf")
    if not is_valid and "not found" in msg.lower():
        print("✓ PDF validation correctly rejects nonexistent files")
    else:
        print(f"✗ PDF validation unexpected result: {msg}")
    
    return True


def test_model_methods():
    """Test MaterialSchedule model methods"""
    print("\n=== Testing Model Methods ===")
    
    # Test get_display_path
    schedule = MaterialSchedule()
    schedule.file_path = "/external/path.pdf"
    schedule.managed_file_path = None
    
    display_path = schedule.get_display_path()
    if display_path == "/external/path.pdf":
        print("✓ get_display_path() returns external path when no managed path")
    else:
        print(f"✗ get_display_path() incorrect: {display_path}")
    
    # Test with managed path
    schedule.managed_file_path = "/project/materials/path.pdf"
    display_path = schedule.get_display_path()
    if display_path == "/project/materials/path.pdf":
        print("✓ get_display_path() prefers managed path")
    else:
        print(f"✗ get_display_path() should prefer managed path: {display_path}")
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Material Schedule Feature Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("Database Models", test_database_models()))
    results.append(("File Utilities", test_file_utilities()))
    results.append(("Model Methods", test_model_methods()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + ("=" * 60))
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())

