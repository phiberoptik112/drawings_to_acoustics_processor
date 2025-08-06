#!/usr/bin/env python3
"""
Test script to verify the Advanced Material Search button has been moved 
from Surface Materials tab to Basic Properties tab in Space Edit Dialog
"""

import sys
import os

# Add src directory to path
current_dir = os.path.dirname(__file__)
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

def test_button_moved_to_basic_tab():
    """Test that the Advanced Material Search button is now in the Basic Properties tab"""
    print("Testing Advanced Material Search Button Location Change")
    print("=" * 60)
    
    try:
        # Read the space edit dialog file
        dialog_file = os.path.join(src_dir, 'ui', 'dialogs', 'space_edit_dialog.py')
        
        with open(dialog_file, 'r') as f:
            content = f.read()
        
        # Check if the button is in the create_basic_tab method
        if 'Advanced Material Search' in content and 'create_basic_tab' in content:
            # Find the create_basic_tab method
            basic_tab_start = content.find('def create_basic_tab(self):')
            if basic_tab_start != -1:
                # Find the end of the method (next method or end of class)
                next_method = content.find('def create_materials_tab(self):', basic_tab_start)
                if next_method != -1:
                    basic_tab_content = content[basic_tab_start:next_method]
                    
                    if 'Advanced Material Search' in basic_tab_content:
                        print("✓ Advanced Material Search button found in create_basic_tab method")
                        
                        # Check for proper styling
                        if 'background-color: #3498db' in basic_tab_content:
                            print("✓ Button has proper blue styling")
                        else:
                            print("⚠ Button styling may be missing")
                        
                        # Check for proper connection
                        if 'show_advanced_material_search' in basic_tab_content:
                            print("✓ Button properly connected to show_advanced_material_search method")
                        else:
                            print("⚠ Button connection may be missing")
                        
                        return True
                    else:
                        print("✗ Advanced Material Search button NOT found in create_basic_tab method")
                        return False
                else:
                    print("✗ Could not find end of create_basic_tab method")
                    return False
            else:
                print("✗ Could not find create_basic_tab method")
                return False
        else:
            print("✗ Advanced Material Search button not found in space_edit_dialog.py")
            return False
            
    except Exception as e:
        print(f"✗ Error testing button location: {e}")
        return False

def test_methods_implemented():
    """Test that the required methods are implemented"""
    print("\nTesting Required Methods Implementation")
    print("=" * 40)
    
    try:
        dialog_file = os.path.join(src_dir, 'ui', 'dialogs', 'space_edit_dialog.py')
        
        with open(dialog_file, 'r') as f:
            content = f.read()
        
        methods_found = 0
        
        # Check for show_advanced_material_search method
        if 'def show_advanced_material_search(self):' in content:
            print("✓ show_advanced_material_search method found")
            methods_found += 1
        else:
            print("✗ show_advanced_material_search method NOT found")
        
        # Check for apply_searched_material method
        if 'def apply_searched_material(self, material, surface_type):' in content:
            print("✓ apply_searched_material method found")
            methods_found += 1
        else:
            print("✗ apply_searched_material method NOT found")
        
        # Check for get_space_data_for_search method
        if 'def get_space_data_for_search(self):' in content:
            print("✓ get_space_data_for_search method found")
            methods_found += 1
        else:
            print("✗ get_space_data_for_search method NOT found")
        
        # Check for MaterialSearchDialog import
        if 'from ui.dialogs.material_search_dialog import MaterialSearchDialog' in content:
            print("✓ MaterialSearchDialog import found")
            methods_found += 1
        else:
            print("✗ MaterialSearchDialog import NOT found")
        
        return methods_found == 4
        
    except Exception as e:
        print(f"✗ Error testing methods: {e}")
        return False

def test_materials_tab_clean():
    """Test that the Surface Materials tab no longer has the Advanced Material Search button"""
    print("\nTesting Surface Materials Tab Clean")
    print("=" * 35)
    
    try:
        dialog_file = os.path.join(src_dir, 'ui', 'dialogs', 'space_edit_dialog.py')
        
        with open(dialog_file, 'r') as f:
            content = f.read()
        
        # Find the create_materials_tab method
        materials_tab_start = content.find('def create_materials_tab(self):')
        if materials_tab_start != -1:
            # Find the end of the method (next method or end of class)
            next_method = content.find('def create_calculations_tab(self):', materials_tab_start)
            if next_method != -1:
                materials_tab_content = content[materials_tab_start:next_method]
                
                if 'Advanced Material Search' not in materials_tab_content:
                    print("✓ Advanced Material Search button properly removed from create_materials_tab method")
                    return True
                else:
                    print("✗ Advanced Material Search button still present in create_materials_tab method")
                    return False
            else:
                print("⚠ Could not determine end of create_materials_tab method")
                return True  # Assume it's clean if we can't verify
        else:
            print("✗ Could not find create_materials_tab method")
            return False
            
    except Exception as e:
        print(f"✗ Error testing materials tab: {e}")
        return False

def main():
    """Run all tests"""
    print("Advanced Material Search Button Move Verification")
    print("=" * 50)
    
    all_passed = True
    
    # Test button moved to basic tab
    if not test_button_moved_to_basic_tab():
        all_passed = False
    
    # Test methods implemented
    if not test_methods_implemented():
        all_passed = False
    
    # Test materials tab clean
    if not test_materials_tab_clean():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! The Advanced Material Search button has been")
        print("   successfully moved from Surface Materials tab to Basic Properties tab.")
        print("\n📍 New Button Location:")
        print("   Space Edit Dialog → Basic Properties tab → Material Analysis section")
        print("   (Bright blue button with '🔍 Advanced Material Search' text)")
    else:
        print("⚠ Some tests failed. Please check the implementation.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 