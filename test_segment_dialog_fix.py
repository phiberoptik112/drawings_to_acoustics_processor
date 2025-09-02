#!/usr/bin/env python3
"""
Test that segment dialog can handle integer segment IDs properly
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_segment_dialog_with_id():
    """Test that HVACSegmentDialog can handle integer segment ID"""
    os.environ['HVAC_DEBUG_EXPORT'] = '1'
    
    try:
        from models.database import initialize_database, get_hvac_session
        from models.hvac import HVACSegment
        from ui.dialogs.hvac_segment_dialog import HVACSegmentDialog
        from PySide6.QtWidgets import QApplication
        
        print("=== SEGMENT DIALOG INTEGER ID TEST ===")
        
        # Initialize database
        initialize_database()
        
        # Create minimal QApplication for dialog testing
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Get a segment ID to test with
        with get_hvac_session() as session:
            segment = session.query(HVACSegment).first()
            if not segment:
                print("❌ No segments found for testing")
                return False
                
            segment_id = segment.id
            expected_length = segment.length
            expected_width = segment.duct_width
            expected_height = segment.duct_height
            
            print(f"Testing with segment ID {segment_id}")
            print(f"Expected values: {expected_length} ft, {expected_width}x{expected_height} inches")
        
        # Test 1: Create dialog with integer segment ID (simulating the bug)
        print(f"\nTest 1: Creating dialog with integer segment ID {segment_id}...")
        try:
            dialog = HVACSegmentDialog(
                parent=None,
                hvac_path_id=1,
                from_component=None,
                to_component=None,
                segment=segment_id  # Pass integer ID instead of segment object
            )
            
            # Check if the dialog loaded the segment correctly
            if dialog.segment is not None:
                actual_length = dialog.segment.length
                actual_width = dialog.segment.duct_width
                actual_height = dialog.segment.duct_height
                
                print(f"✅ Dialog created successfully")
                print(f"Loaded values: {actual_length} ft, {actual_width}x{actual_height} inches")
                
                # Verify the values match expected
                length_ok = abs(actual_length - expected_length) < 0.1
                width_ok = actual_width == expected_width
                height_ok = actual_height == expected_height
                
                if length_ok and width_ok and height_ok:
                    print("✅ All values loaded correctly from database!")
                    return True
                else:
                    print(f"❌ Values don't match expected:")
                    print(f"   Length: {actual_length} vs {expected_length} (OK: {length_ok})")
                    print(f"   Width: {actual_width} vs {expected_width} (OK: {width_ok})")
                    print(f"   Height: {actual_height} vs {expected_height} (OK: {height_ok})")
                    return False
            else:
                print("❌ Dialog segment is None after creation")
                return False
                
        except Exception as e:
            print(f"❌ Dialog creation failed: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
            
    except Exception as e:
        print(f"ERROR in segment dialog test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("Testing segment dialog integer ID handling...\n")
    
    result = test_segment_dialog_with_id()
    
    print(f"\n=== TEST RESULT ===")
    if result:
        print("✅ Segment dialog can now handle integer IDs correctly!")
        print("This should fix the 'int' object has no attribute 'length' error.")
    else:
        print("❌ Test failed - the integer ID handling needs more work")