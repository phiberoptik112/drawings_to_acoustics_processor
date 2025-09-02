#!/usr/bin/env python3
"""
Test script to verify segment dialog functionality with database session handling
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_segment_dialog_opening():
    """Test that the segment dialog can open without DetachedInstanceError"""
    # Enable debug export for this test
    os.environ['HVAC_DEBUG_EXPORT'] = '1'
    
    try:
        from models.database import initialize_database, get_hvac_session
        from models.hvac import HVACPath, HVACSegment, HVACComponent
        from sqlalchemy.orm import selectinload
        
        print("=== SEGMENT DIALOG TEST ===")
        
        # Initialize database
        initialize_database()
        
        with get_hvac_session() as session:
            # Check if we have any existing HVAC paths with segments
            paths = session.query(HVACPath).all()
            print(f"Found {len(paths)} HVAC paths in database")
            
            if not paths:
                print("No HVAC paths found, segment dialog test cannot proceed")
                return False
            
            # Get the first path with segments
            path_with_segments = None
            for path in paths:
                segments = session.query(HVACSegment).filter_by(hvac_path_id=path.id).count()
                if segments > 0:
                    path_with_segments = path
                    break
            
            if not path_with_segments:
                print("No HVAC paths with segments found")
                return False
                
            print(f"Testing with path ID: {path_with_segments.id}")
            
            # Load segments with proper eager loading like the dialog does
            segments = (
                session.query(HVACSegment)
                .options(
                    selectinload(HVACSegment.from_component),
                    selectinload(HVACSegment.to_component),
                    selectinload(HVACSegment.fittings)
                )
                .filter_by(hvac_path_id=path_with_segments.id)
                .order_by(HVACSegment.segment_order)
                .all()
            )
            
            print(f"Found {len(segments)} segments")
            
            # Test that we can access segment properties without DetachedInstanceError
            for i, seg in enumerate(segments):
                print(f"Segment {i+1}:")
                print(f"  ID: {seg.id}")
                print(f"  Length: {seg.length}")
                print(f"  Width: {seg.duct_width}")
                print(f"  Height: {seg.duct_height}")
                print(f"  Flow rate: {seg.flow_rate}")
                
                # Test component relationships
                try:
                    from_comp = seg.from_component
                    to_comp = seg.to_component
                    print(f"  From component: {from_comp.name if from_comp else 'None'}")
                    print(f"  To component: {to_comp.name if to_comp else 'None'}")
                except Exception as e:
                    print(f"  ERROR accessing components: {e}")
                    return False
                
                # Test fittings
                try:
                    fittings = seg.fittings
                    print(f"  Fittings: {len(fittings) if fittings else 0}")
                except Exception as e:
                    print(f"  ERROR accessing fittings: {e}")
                    return False
            
            print("✓ All segment properties accessible without DetachedInstanceError")
            return True
            
    except Exception as e:
        print(f"ERROR in segment dialog test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_segment_refresh_logic():
    """Test the segment refresh logic that fixes DetachedInstanceError"""
    os.environ['HVAC_DEBUG_EXPORT'] = '1'
    
    try:
        from models.database import get_hvac_session
        from models.hvac import HVACSegment
        from sqlalchemy.orm import selectinload
        
        print("\n=== SEGMENT REFRESH LOGIC TEST ===")
        
        with get_hvac_session() as session:
            # Find a segment
            segment = session.query(HVACSegment).first()
            if not segment:
                print("No segments found for refresh test")
                return False
            
            print(f"Testing refresh logic with segment ID: {segment.id}")
            
            # Simulate the refresh logic from edit_segment method
            refreshed_segment = (
                session.query(HVACSegment)
                .options(
                    selectinload(HVACSegment.from_component),
                    selectinload(HVACSegment.to_component),
                    selectinload(HVACSegment.fittings)
                )
                .filter_by(id=segment.id)
                .first()
            )
            
            if refreshed_segment:
                print(f"✓ Successfully refreshed segment")
                print(f"  Length: {refreshed_segment.length}")
                print(f"  Duct dimensions: {refreshed_segment.duct_width}x{refreshed_segment.duct_height}")
                
                # Test component access
                from_comp = refreshed_segment.from_component
                to_comp = refreshed_segment.to_component
                print(f"  From: {from_comp.name if from_comp else 'None'}")
                print(f"  To: {to_comp.name if to_comp else 'None'}")
                
                return True
            else:
                print("✗ Failed to refresh segment")
                return False
                
    except Exception as e:
        print(f"ERROR in refresh logic test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("Starting segment dialog functionality tests...\n")
    
    # Run tests
    test1_result = test_segment_dialog_opening()
    test2_result = test_segment_refresh_logic()
    
    print(f"\n=== TEST SUMMARY ===")
    print(f"Segment dialog access test: {'PASS' if test1_result else 'FAIL'}")
    print(f"Segment refresh logic test: {'PASS' if test2_result else 'FAIL'}")
    
    if test1_result and test2_result:
        print("✓ All segment dialog tests PASSED - DetachedInstanceError fixes are working")
    else:
        print("✗ Some tests FAILED - check the debug output above")