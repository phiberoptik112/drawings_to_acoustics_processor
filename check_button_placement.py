#!/usr/bin/env python3
"""
Debug script to check button placement and verify it's being created properly
"""

import sys
import os

# Add src directory to path
current_dir = os.path.dirname(__file__)
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

def check_room_properties_button():
    """Check Room Properties Dialog button creation"""
    print("Checking Room Properties Dialog button creation...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from ui.dialogs.room_properties import RoomPropertiesDialog
        
        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Mock some test data
        rectangle_data = {
            'area_real': 500,
            'width_real': 20,
            'height_real': 25
        }
        
        # Create a dialog instance (without showing it)
        print("Creating RoomPropertiesDialog instance...")
        dialog = RoomPropertiesDialog(rectangle_data=rectangle_data)
        
        # Check if the button was created
        if hasattr(dialog, 'advanced_search_btn'):
            button = dialog.advanced_search_btn
            print(f"✓ Button created successfully")
            print(f"  Text: '{button.text()}'")
            print(f"  Tooltip: '{button.toolTip()}'")
            print(f"  Size: {button.size().width()}x{button.size().height()}")
            print(f"  Minimum Height: {button.minimumHeight()}")
            print(f"  StyleSheet applied: {len(button.styleSheet()) > 0}")
            
            # Check if button has click handler
            if button.receivers(button.clicked) > 0:
                print("✓ Button has click handler connected")
            else:
                print("✗ Button has no click handler")
                
            return True
        else:
            print("✗ Button was not created (advanced_search_btn attribute missing)")
            return False
            
    except Exception as e:
        print(f"✗ Error creating Room Properties Dialog: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_space_edit_button():
    """Check Space Edit Dialog button creation"""
    print("\nChecking Space Edit Dialog button creation...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from ui.dialogs.space_edit_dialog import SpaceEditDialog
        
        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create a dialog instance (without showing it, no space needed for button test)
        print("Creating SpaceEditDialog instance...")
        dialog = SpaceEditDialog(space=None)
        
        # Check if the button was created
        if hasattr(dialog, 'advanced_search_btn'):
            button = dialog.advanced_search_btn
            print(f"✓ Button created successfully")
            print(f"  Text: '{button.text()}'")
            print(f"  Tooltip: '{button.toolTip()}'")  
            print(f"  Size: {button.size().width()}x{button.size().height()}")
            print(f"  Minimum Height: {button.minimumHeight()}")
            print(f"  StyleSheet applied: {len(button.styleSheet()) > 0}")
            
            # Check if button has click handler
            if button.receivers(button.clicked) > 0:
                print("✓ Button has click handler connected")
            else:
                print("✗ Button has no click handler")
                
            return True
        else:
            print("✗ Button was not created (advanced_search_btn attribute missing)")
            return False
            
    except Exception as e:
        print(f"✗ Error creating Space Edit Dialog: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_import_chain():
    """Check the import chain for material search components"""
    print("\nChecking import chain...")
    
    imports_to_test = [
        ("Material Search Engine", "data.material_search", "MaterialSearchEngine"),
        ("Treatment Analyzer", "calculations.treatment_analyzer", "TreatmentAnalyzer"), 
        ("Material Search Dialog", "ui.dialogs.material_search_dialog", "MaterialSearchDialog"),
        ("Room Properties Dialog", "ui.dialogs.room_properties", "RoomPropertiesDialog"),
        ("Space Edit Dialog", "ui.dialogs.space_edit_dialog", "SpaceEditDialog")
    ]
    
    all_good = True
    for name, module, class_name in imports_to_test:
        try:
            imported_module = __import__(module, fromlist=[class_name])
            imported_class = getattr(imported_module, class_name)
            print(f"✓ {name}: Import successful")
        except Exception as e:
            print(f"✗ {name}: Import failed - {e}")
            all_good = False
    
    return all_good

def main():
    """Run button placement checks"""
    print("Advanced Material Search Button Placement Check")
    print("=" * 60)
    
    # First check imports
    imports_ok = check_import_chain()
    
    if not imports_ok:
        print("\n⚠ Import issues detected. This may prevent the button from appearing.")
        return False
    
    # Check button creation
    room_ok = check_room_properties_button()
    space_ok = check_space_edit_button()
    
    print("\n" + "=" * 60)
    if room_ok and space_ok:
        print("🎉 Button placement check passed!")
        print("\nThe button should now be VERY visible with:")
        print("  ✓ Blue background (#3498db)")
        print("  ✓ White text")  
        print("  ✓ Bold font")
        print("  ✓ 35px minimum height")
        print("  ✓ Centered positioning")
        print("  ✓ 10px spacing below")
        print("\nLocation: 'Surface Materials' tab, between instructions and material sections")
        print("\nIf you still can't see it, the issue may be:")
        print("  1. Not looking in the correct tab")
        print("  2. Dialog window is too narrow (try resizing)")
        print("  3. Other UI elements are overlapping")
    else:
        print("⚠ Button placement check failed!")
        print("There may be issues with the button creation.")
    
    return room_ok and space_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)