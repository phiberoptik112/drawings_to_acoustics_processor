#!/usr/bin/env python3
"""
Test script to verify project structure and imports
Run this to test the foundation without requiring PyQt5 installation
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_database_models():
    """Test database model imports and structure"""
    print("Testing database models...")
    
    try:
        from models.database import Base, initialize_database
        from models.project import Project
        from models.drawing import Drawing
        from models.space import Space, RoomBoundary
        from models.hvac import HVACComponent, HVACPath, HVACSegment, SegmentFitting
        print("✅ Database models imported successfully")
        
        # Test model attributes
        project = Project(name="Test Project", description="Test")
        print(f"✅ Project model: {project}")
        
        return True
    except Exception as e:
        print(f"❌ Database models failed: {e}")
        return False

def test_data_libraries():
    """Test standard data libraries"""
    print("\nTesting data libraries...")
    
    try:
        from data import STANDARD_COMPONENTS, STANDARD_MATERIALS, ROOM_TYPE_DEFAULTS
        
        print(f"✅ Standard components: {len(STANDARD_COMPONENTS)} items")
        print(f"✅ Standard materials: {len(STANDARD_MATERIALS)} items")
        print(f"✅ Room type defaults: {len(ROOM_TYPE_DEFAULTS)} types")
        
        # Test a few items
        ahu = STANDARD_COMPONENTS['ahu']
        print(f"   Example component: {ahu['name']} - {ahu['noise_level']} dB(A)")
        
        carpet = STANDARD_MATERIALS['carpet_heavy']
        print(f"   Example material: {carpet['name']} - {carpet['absorption_coeff']} absorption")
        
        return True
    except Exception as e:
        print(f"❌ Data libraries failed: {e}")
        return False

def test_file_structure():
    """Test that all expected files exist"""
    print("\nTesting file structure...")
    
    expected_files = [
        'src/main.py',
        'src/models/__init__.py',
        'src/models/database.py',
        'src/models/project.py',
        'src/models/drawing.py',
        'src/models/space.py',
        'src/models/hvac.py',
        'src/ui/__init__.py',
        'src/ui/splash_screen.py',
        'src/ui/project_dashboard.py',
        'src/ui/drawing_interface.py',
        'src/ui/dialogs/__init__.py',
        'src/ui/dialogs/project_dialog.py',
        'src/ui/dialogs/scale_dialog.py',
        'src/data/__init__.py',
        'src/data/components.py',
        'src/data/materials.py',
        'src/drawing/__init__.py',
        'src/drawing/pdf_viewer.py',
        'src/drawing/scale_manager.py',
        'src/drawing/drawing_tools.py',
        'src/drawing/drawing_overlay.py',
        'requirements.txt',
        'setup.py'
    ]
    
    missing_files = []
    for file_path in expected_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print(f"✅ All {len(expected_files)} expected files exist")
        return True

def main():
    """Run all tests"""
    print("🔍 Testing Acoustic Analysis Tool Project Structure\n")
    
    tests = [
        test_file_structure,
        test_database_models,
        test_data_libraries
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n📊 Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All tests passed! Project structure is ready.")
        print("\n📝 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run application: cd src && python main.py")
        print("3. Continue with Phase 2 implementation")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    return all(results)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)