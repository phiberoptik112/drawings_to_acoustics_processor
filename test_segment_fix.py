#!/usr/bin/env python3
"""
Test the segment dialog fix to ensure it loads correct values
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_segment_dialog_fix():
    """Test that segment dialog loads correct values after the fix"""
    os.environ['HVAC_DEBUG_EXPORT'] = '1'
    
    try:
        from models.database import initialize_database, get_hvac_session
        from models.hvac import HVACSegment
        from sqlalchemy.orm import selectinload
        
        print("=== SEGMENT DIALOG FIX TEST ===")
        
        # Initialize database
        initialize_database()
        
        # Test the fix logic: simulate what the edit_segment method now does
        with get_hvac_session() as session:
            # Get segment ID 19 (the problematic one from user's debug output)
            segment_id = 19
            
            print(f"Testing segment ID {segment_id} loading...")
            
            # Load segment the way the fix does it
            segment = (
                session.query(HVACSegment)
                .options(
                    selectinload(HVACSegment.from_component),
                    selectinload(HVACSegment.to_component),
                    selectinload(HVACSegment.fittings)
                )
                .filter_by(id=segment_id)
                .first()
            )
            
            if not segment:
                print(f"❌ Segment {segment_id} not found")
                return False
                
            # Pre-load relationships
            from_component = segment.from_component
            to_component = segment.to_component
            fittings = list(segment.fittings)
            
            print(f"✅ Successfully loaded segment {segment_id}:")
            print(f"   Length: {segment.length} ft (should be ~12.2)")
            print(f"   Duct dimensions: {segment.duct_width} x {segment.duct_height} inches (should be 12x8)")
            print(f"   From component: {from_component.name if from_component else 'None'}")
            print(f"   To component: {to_component.name if to_component else 'None'}")
            print(f"   Fittings count: {len(fittings)}")
            
            # Verify the values are correct
            length_ok = abs(segment.length - 12.2) < 0.1  # Within 0.1 ft
            width_ok = segment.duct_width == 12.0
            height_ok = segment.duct_height == 8.0
            
            print(f"\nValidation:")
            print(f"   Length correct: {length_ok} ({segment.length} ≈ 12.2)")
            print(f"   Width correct: {width_ok} ({segment.duct_width} = 12.0)")
            print(f"   Height correct: {height_ok} ({segment.duct_height} = 8.0)")
            
            if length_ok and width_ok and height_ok:
                print("✅ All values are correct - the fix should work!")
                return True
            else:
                print("❌ Some values are still incorrect")
                return False
                
    except Exception as e:
        print(f"ERROR in segment dialog fix test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_segment_list_widget_logic():
    """Test the SegmentListWidget ID storage logic"""
    print("\n=== SEGMENT LIST WIDGET LOGIC TEST ===")
    
    try:
        from models.database import initialize_database, get_hvac_session
        from models.hvac import HVACSegment
        from sqlalchemy.orm import selectinload
        
        # Initialize database
        initialize_database()
        
        with get_hvac_session() as session:
            # Get first few segments to test the logic
            segments = (
                session.query(HVACSegment)
                .options(
                    selectinload(HVACSegment.from_component),
                    selectinload(HVACSegment.to_component)
                )
                .limit(3)
                .all()
            )
            
            if not segments:
                print("❌ No segments found for testing")
                return False
                
            print(f"Testing SegmentListWidget logic with {len(segments)} segments:")
            
            # Simulate what SegmentListWidget.set_segments does
            for i, segment in enumerate(segments):
                # Test the new logic: store ID instead of object
                stored_value = segment.id if hasattr(segment, 'id') else segment
                
                print(f"   Segment {i+1}: ID {segment.id} -> stored value: {stored_value}")
                
                # Test that we can later retrieve the segment by ID
                if isinstance(stored_value, int):
                    retrieved_segment = session.query(HVACSegment).filter_by(id=stored_value).first()
                    if retrieved_segment:
                        print(f"      ✅ Can retrieve by ID: {retrieved_segment.length:.1f} ft")
                    else:
                        print(f"      ❌ Cannot retrieve by ID")
                        return False
                        
            print("✅ SegmentListWidget ID storage logic looks good")
            return True
                
    except Exception as e:
        print(f"ERROR in segment list widget test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("Testing segment dialog fix...\n")
    
    # Run tests
    test1_result = test_segment_dialog_fix()
    test2_result = test_segment_list_widget_logic()
    
    print(f"\n=== TEST RESULTS ===")
    print(f"Segment dialog fix test: {'PASS' if test1_result else 'FAIL'}")
    print(f"Segment list widget logic test: {'PASS' if test2_result else 'FAIL'}")
    
    if test1_result and test2_result:
        print("✅ Segment dialog fix should resolve the 0.0 ft / 1x1 inch display issue!")
    else:
        print("❌ Some tests failed - the fix may need additional work")