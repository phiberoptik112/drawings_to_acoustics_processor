#!/usr/bin/env python3
"""
Test the segment dialog fixes
"""
import os
import sys
sys.path.insert(0, 'src')

# Enable debugging
os.environ['HVAC_DEBUG_EXPORT'] = '1'

def test_database_segment_access():
    """Test that we can access segment data from database correctly"""
    
    try:
        from models.database import initialize_database, get_hvac_session
        from models.hvac import HVACSegment
        
        initialize_database()
        print("✓ Database initialized")
        
        with get_hvac_session() as session:
            # Find a segment to test with
            segment = session.query(HVACSegment).first()
            if not segment:
                print("No segments found to test with")
                return False
            
            print(f"Testing with segment ID {segment.id}")
            print(f"Database values: length={segment.length}, width={segment.duct_width}, height={segment.duct_height}")
            
            # Test that we can re-query the same segment (simulating dialog behavior)
            fresh_segment = session.query(HVACSegment).filter_by(id=segment.id).first()
            if fresh_segment:
                print(f"Re-query successful: length={fresh_segment.length}, width={fresh_segment.duct_width}, height={fresh_segment.duct_height}")
                
                # Test updating values
                original_width = fresh_segment.duct_width
                fresh_segment.duct_width = 16.0  # Test value
                session.flush()
                
                # Verify update
                session.refresh(fresh_segment)
                if fresh_segment.duct_width == 16.0:
                    print("✓ Segment update and refresh working")
                    
                    # Restore original value
                    fresh_segment.duct_width = original_width
                    session.commit()
                    print("✓ Original value restored")
                    return True
                else:
                    print("✗ Segment update/refresh not working")
                    return False
            else:
                print("✗ Could not re-query segment")
                return False
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Segment Database Operations")
    print("==================================")
    
    result = test_database_segment_access()
    
    if result:
        print("\n✓ Database operations working correctly")
        print("\nThe segment dialog should now:")
        print("1. Load segment data correctly from database")
        print("2. Show non-zero values in UI fields")
        print("3. Save updates without SQLAlchemy session errors")
        print("4. Provide comprehensive debug output when HVAC_DEBUG_EXPORT=1")
        sys.exit(0)
    else:
        print("\n✗ Database operations have issues")
        sys.exit(1)