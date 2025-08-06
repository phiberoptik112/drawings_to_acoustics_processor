#!/usr/bin/env python3
"""
Test script to verify the Advanced Material Search button structure without GUI
"""

import sys
import os

# Add src directory to path
current_dir = os.path.dirname(__file__)
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

def test_room_properties_structure():
    """Test Room Properties Dialog structure"""
    print("Testing Room Properties Dialog structure...")
    
    try:
        # Import the class
        from ui.dialogs.room_properties import RoomPropertiesDialog
        
        # Check class methods
        methods = dir(RoomPropertiesDialog)
        
        required_methods = [
            'create_materials_tab',
            'show_advanced_material_search',
            'apply_searched_material'
        ]
        
        for method in required_methods:
            if method in methods:
                print(f"✓ Method exists: {method}")
            else:
                print(f"✗ Method missing: {method}")
                return False
        
        # Try to inspect the create_materials_tab method
        import inspect
        source = inspect.getsource(RoomPropertiesDialog.create_materials_tab)
        
        if 'advanced_search_btn' in source:
            print("✓ advanced_search_btn found in create_materials_tab method")
        else:
            print("✗ advanced_search_btn NOT found in create_materials_tab method")
            return False
            
        if 'Advanced Material Search' in source:
            print("✓ Button text 'Advanced Material Search' found")
        else:
            print("✗ Button text 'Advanced Material Search' NOT found")
            return False
            
        if 'show_advanced_material_search' in source:
            print("✓ Button click handler 'show_advanced_material_search' found")
        else:
            print("✗ Button click handler 'show_advanced_material_search' NOT found")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing Room Properties Dialog: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_space_edit_structure():
    """Test Space Edit Dialog structure"""
    print("\nTesting Space Edit Dialog structure...")
    
    try:
        # Import the class
        from ui.dialogs.space_edit_dialog import SpaceEditDialog
        
        # Check class methods
        methods = dir(SpaceEditDialog)
        
        required_methods = [
            'create_materials_tab',
            'show_advanced_material_search',
            'apply_searched_material',
            'get_current_space_data'
        ]
        
        for method in required_methods:
            if method in methods:
                print(f"✓ Method exists: {method}")
            else:
                print(f"✗ Method missing: {method}")
                return False
        
        # Try to inspect the create_materials_tab method
        import inspect
        source = inspect.getsource(SpaceEditDialog.create_materials_tab)
        
        if 'advanced_search_btn' in source:
            print("✓ advanced_search_btn found in create_materials_tab method")
        else:
            print("✗ advanced_search_btn NOT found in create_materials_tab method")
            return False
            
        if 'Advanced Material Search' in source:
            print("✓ Button text 'Advanced Material Search' found")
        else:
            print("✗ Button text 'Advanced Material Search' NOT found")
            return False
            
        if 'show_advanced_material_search' in source:
            print("✓ Button click handler 'show_advanced_material_search' found")
        else:
            print("✗ Button click handler 'show_advanced_material_search' NOT found")
            return FALSE
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing Space Edit Dialog: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dialog_tab_structure():
    """Test that both dialogs have materials tabs"""
    print("\nTesting dialog tab structure...")
    
    try:
        from ui.dialogs.room_properties import RoomPropertiesDialog
        from ui.dialogs.space_edit_dialog import SpaceEditDialog
        
        # Check Room Properties Dialog
        import inspect
        room_init_source = inspect.getsource(RoomPropertiesDialog.init_ui)
        
        if 'Surface Materials' in room_init_source:
            print("✓ Room Properties Dialog has 'Surface Materials' tab")
        else:
            print("✗ Room Properties Dialog missing 'Surface Materials' tab")
            return False
            
        if 'create_materials_tab' in room_init_source:
            print("✓ Room Properties Dialog calls create_materials_tab")
        else:
            print("✗ Room Properties Dialog doesn't call create_materials_tab")
            return False
        
        # Check Space Edit Dialog  
        space_init_source = inspect.getsource(SpaceEditDialog.init_ui)
        
        if 'Surface Materials' in space_init_source:
            print("✓ Space Edit Dialog has 'Surface Materials' tab")
        else:
            print("✗ Space Edit Dialog missing 'Surface Materials' tab")
            return False
            
        if 'create_materials_tab' in space_init_source:
            print("✓ Space Edit Dialog calls create_materials_tab")
        else:
            print("✗ Space Edit Dialog doesn't call create_materials_tab")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing dialog tab structure: {e}")
        return False

def main():
    """Run structure tests"""
    print("Advanced Material Search Button Structure Test")
    print("=" * 60)
    
    all_passed = True
    
    # Test Room Properties Dialog structure
    if not test_room_properties_structure():
        all_passed = False
    
    # Test Space Edit Dialog structure
    if not test_space_edit_structure():
        all_passed = False
        
    # Test dialog tab structure
    if not test_dialog_tab_structure():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All structure tests passed!")
        print("\nThe Advanced Material Search button SHOULD be visible in:")
        print("  • Room Properties Dialog -> 'Surface Materials' tab -> Header area")
        print("  • Space Edit Dialog -> 'Surface Materials' tab -> Header area")
        print("\nIf you still can't see the button, please check:")
        print("  1. Are you looking in the 'Surface Materials' tab (not Basic Properties)?")
        print("  2. Is the button in the header area above the material selection sections?")
        print("  3. Try resizing the dialog window to ensure it's not cut off")
        print("  4. The button text is '🔍 Advanced Material Search'")
    else:
        print("⚠ Some structure tests failed.")
        print("The button integration may have issues.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)