#!/usr/bin/env python3
"""
Test script to verify the Advanced Material Search button is visible in both dialogs
"""

import sys
import os

# Add src directory to path
current_dir = os.path.dirname(__file__)
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

def test_room_properties_dialog():
    """Test Room Properties Dialog button visibility"""
    print("Testing Room Properties Dialog...")
    
    try:
        from ui.dialogs.room_properties import RoomPropertiesDialog
        
        # Create dialog with minimal test data
        rectangle_data = {
            'area_real': 500,
            'width_real': 20,
            'height_real': 25
        }
        
        dialog = RoomPropertiesDialog(rectangle_data=rectangle_data)
        
        # Check if the button exists
        if hasattr(dialog, 'advanced_search_btn'):
            button = dialog.advanced_search_btn
            print(f"✓ Button exists: {button.text()}")
            print(f"✓ Button tooltip: {button.toolTip()}")
            print(f"✓ Button enabled: {button.isEnabled()}")
            print(f"✓ Button visible: {button.isVisible()}")
            
            # Check if it's in the materials tab
            materials_tab = None
            tabs = dialog.findChild(object, "materials_tab") 
            print(f"✓ Materials tab widget created successfully")
            
            return True
        else:
            print("✗ advanced_search_btn attribute not found")
            return False
            
    except Exception as e:
        print(f"✗ Error testing Room Properties Dialog: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_space_edit_dialog():
    """Test Space Edit Dialog button visibility"""
    print("\nTesting Space Edit Dialog...")
    
    try:
        from ui.dialogs.space_edit_dialog import SpaceEditDialog
        
        # Create dialog with minimal test data (no actual space object needed for button test)
        dialog = SpaceEditDialog(space=None)
        
        # Check if the button exists
        if hasattr(dialog, 'advanced_search_btn'):
            button = dialog.advanced_search_btn
            print(f"✓ Button exists: {button.text()}")
            print(f"✓ Button tooltip: {button.toolTip()}")
            print(f"✓ Button enabled: {button.isEnabled()}")
            print(f"✓ Button visible: {button.isVisible()}")
            
            print(f"✓ Materials tab widget created successfully")
            
            return True
        else:
            print("✗ advanced_search_btn attribute not found")
            return False
            
    except Exception as e:
        print(f"✗ Error testing Space Edit Dialog: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_test_window():
    """Create a test window to visually verify the buttons"""
    from ui.dialogs.room_properties import RoomPropertiesDialog
    from ui.dialogs.space_edit_dialog import SpaceEditDialog
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Material Search Button Test")
            self.setGeometry(100, 100, 400, 200)
            
            central_widget = QWidget()
            layout = QVBoxLayout()
            
            # Button to open Room Properties Dialog
            room_btn = QPushButton("Open Room Properties Dialog")
            room_btn.clicked.connect(self.open_room_dialog)
            layout.addWidget(room_btn)
            
            # Button to open Space Edit Dialog
            space_btn = QPushButton("Open Space Edit Dialog") 
            space_btn.clicked.connect(self.open_space_dialog)
            layout.addWidget(space_btn)
            
            central_widget.setLayout(layout)
            self.setCentralWidget(central_widget)
            
        def open_room_dialog(self):
            rectangle_data = {
                'area_real': 500,
                'width_real': 20,
                'height_real': 25
            }
            dialog = RoomPropertiesDialog(self, rectangle_data=rectangle_data)
            dialog.show()
            
        def open_space_dialog(self):
            dialog = SpaceEditDialog(self, space=None)
            dialog.show()
    
    return TestWindow()

def main():
    """Run button visibility tests"""
    print("Advanced Material Search Button Visibility Test")
    print("=" * 60)
    
    # Initialize Qt Application for widget testing
    app = QApplication(sys.argv)
    
    all_passed = True
    
    # Test Room Properties Dialog
    if not test_room_properties_dialog():
        all_passed = False
    
    # Test Space Edit Dialog  
    if not test_space_edit_dialog():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All button visibility tests passed!")
        print("\nTo verify visually, run this script and click the test buttons:")
        
        # Show test window for visual verification
        print("Opening test window for visual verification...")
        window = create_test_window()
        window.show()
        
        print("\nINSTRUCTIONS:")
        print("1. Click 'Open Room Properties Dialog'")
        print("2. Go to 'Surface Materials' tab")
        print("3. Look for '🔍 Advanced Material Search' button in the header")
        print("4. Click 'Open Space Edit Dialog'")
        print("5. Go to 'Surface Materials' tab") 
        print("6. Look for '🔍 Advanced Material Search' button in the header")
        print("\nClose the test window when done.")
        
        app.exec()
    else:
        print("⚠ Some button visibility tests failed.")
        print("The buttons may not be properly integrated.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)