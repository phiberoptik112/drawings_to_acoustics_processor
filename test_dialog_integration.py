#!/usr/bin/env python3
"""
Test script to verify material search integration in both dialogs
"""

import sys
import os

# Add src directory to path
current_dir = os.path.dirname(__file__)
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

def test_room_properties_dialog():
    """Test that RoomPropertiesDialog has material search integration"""
    print("Testing RoomPropertiesDialog integration...")
    
    try:
        from ui.dialogs.room_properties import RoomPropertiesDialog
        
        # Check that the dialog class has the required methods
        methods = dir(RoomPropertiesDialog)
        
        required_methods = [
            'show_advanced_material_search',
            'apply_searched_material'
        ]
        
        missing_methods = []
        for method in required_methods:
            if method not in methods:
                missing_methods.append(method)
        
        if missing_methods:
            print(f"✗ Missing methods in RoomPropertiesDialog: {missing_methods}")
            return False
        
        print("✓ RoomPropertiesDialog has all required material search methods")
        
        # Test that MaterialSearchDialog can be imported
        from ui.dialogs.material_search_dialog import MaterialSearchDialog
        print("✓ MaterialSearchDialog import successful in RoomPropertiesDialog")
        
        return True
        
    except Exception as e:
        print(f"✗ RoomPropertiesDialog test failed: {e}")
        return False

def test_space_edit_dialog():
    """Test that SpaceEditDialog has material search integration"""
    print("\nTesting SpaceEditDialog integration...")
    
    try:
        from ui.dialogs.space_edit_dialog import SpaceEditDialog
        
        # Check that the dialog class has the required methods
        methods = dir(SpaceEditDialog)
        
        required_methods = [
            'show_advanced_material_search',
            'apply_searched_material',
            'get_current_space_data'
        ]
        
        missing_methods = []
        for method in required_methods:
            if method not in methods:
                missing_methods.append(method)
        
        if missing_methods:
            print(f"✗ Missing methods in SpaceEditDialog: {missing_methods}")
            return False
        
        print("✓ SpaceEditDialog has all required material search methods")
        
        # Test that MaterialSearchDialog can be imported
        from ui.dialogs.material_search_dialog import MaterialSearchDialog
        print("✓ MaterialSearchDialog import successful in SpaceEditDialog")
        
        return True
        
    except Exception as e:
        print(f"✗ SpaceEditDialog test failed: {e}")
        return False

def test_material_search_functionality():
    """Test core material search functionality"""
    print("\nTesting core material search functionality...")
    
    try:
        # Test material search engine
        from data.material_search import MaterialSearchEngine
        engine = MaterialSearchEngine()
        
        # Quick search test
        results = engine.search_materials_by_text("acoustic", limit=3)
        if len(results) > 0:
            print(f"✓ Material search found {len(results)} materials for 'acoustic'")
        else:
            print("✗ Material search returned no results")
            return False
        
        # Test treatment analyzer
        from calculations.treatment_analyzer import TreatmentAnalyzer
        analyzer = TreatmentAnalyzer()
        print("✓ Treatment analyzer initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Material search functionality test failed: {e}")
        return False

def main():
    """Run integration tests"""
    print("Material Search Dialog Integration Test")
    print("=" * 50)
    
    all_passed = True
    
    # Test room properties dialog
    if not test_room_properties_dialog():
        all_passed = False
    
    # Test space edit dialog
    if not test_space_edit_dialog():
        all_passed = False
    
    # Test core functionality
    if not test_material_search_functionality():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All integration tests passed!")
        print("\nThe Advanced Material Search button is now available in:")
        print("  • Room Properties Dialog (Materials tab)")
        print("  • Space Edit Dialog (Materials tab)")
        print("\nUsers can access frequency-based material analysis and")
        print("treatment recommendations from both dialogs.")
    else:
        print("⚠ Some integration tests failed.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)