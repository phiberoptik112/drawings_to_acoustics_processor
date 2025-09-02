#!/usr/bin/env python3
"""
Debug script to investigate segment data in database vs. what should be there
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def debug_segment_data():
    """Debug actual segment data in the database"""
    os.environ['HVAC_DEBUG_EXPORT'] = '1'
    
    try:
        from models.database import initialize_database, get_hvac_session
        from models.hvac import HVACPath, HVACSegment, HVACComponent
        from sqlalchemy.orm import selectinload
        
        print("=== SEGMENT DATA DEBUG ===")
        
        # Initialize database
        initialize_database()
        
        with get_hvac_session() as session:
            # Get all segments with their actual stored values
            segments = (
                session.query(HVACSegment)
                .options(
                    selectinload(HVACSegment.from_component),
                    selectinload(HVACSegment.to_component),
                    selectinload(HVACSegment.hvac_path),
                    selectinload(HVACSegment.fittings)
                )
                .all()
            )
            
            print(f"Found {len(segments)} segments in database:")
            
            for seg in segments:
                print(f"\nSegment ID {seg.id}:")
                print(f"  Path: {seg.hvac_path.name if seg.hvac_path else 'Unknown'}")
                print(f"  Length: {seg.length} ft")
                print(f"  Duct dimensions: {seg.duct_width} x {seg.duct_height} inches")
                print(f"  Shape: {seg.duct_shape}")
                print(f"  Type: {seg.duct_type}")
                print(f"  Flow rate: {seg.flow_rate} CFM")
                print(f"  Flow velocity: {seg.flow_velocity} FPM")
                print(f"  From: {seg.from_component.name if seg.from_component else 'None'}")
                print(f"  To: {seg.to_component.name if seg.to_component else 'None'}")
                
                # Check if this is the problematic segment (showing 0.0 length, 1x1 dimensions)
                if seg.length == 0.0 or seg.duct_width == 1.0:
                    print(f"  *** PROBLEMATIC SEGMENT FOUND ***")
                    print(f"  Raw database values:")
                    print(f"    length={repr(seg.length)}")
                    print(f"    duct_width={repr(seg.duct_width)}")
                    print(f"    duct_height={repr(seg.duct_height)}")
                    print(f"    created_date={seg.created_date}")
                    
                    # Try to find if there's a corresponding debug export to compare
                    try:
                        import glob
                        debug_files = glob.glob("debug_data/debug_exports/hvac_debug_Path*.json")
                        if debug_files:
                            print(f"  Debug files available for comparison: {len(debug_files)}")
                    except Exception as e:
                        print(f"  Could not check debug files: {e}")
                        
        return True
        
    except Exception as e:
        print(f"ERROR in segment data debug: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def compare_segment_with_drawing_data():
    """Compare segment database values with what should be from drawing interface"""
    os.environ['HVAC_DEBUG_EXPORT'] = '1'
    
    try:
        from models.database import get_hvac_session
        from models.hvac import HVACSegment
        
        print("\n=== DRAWING DATA COMPARISON ===")
        
        with get_hvac_session() as session:
            # Get a problematic segment (likely ID 19 from the debug output)
            segment = session.query(HVACSegment).filter_by(id=19).first()
            
            if segment:
                print(f"Segment 19 database values:")
                print(f"  Length: {segment.length}")
                print(f"  Duct width: {segment.duct_width}")  
                print(f"  Duct height: {segment.duct_height}")
                
                # Show what the values SHOULD be based on debug JSON
                print(f"\nExpected values (from debug JSON and UI):")
                print(f"  Length: ~12.2 ft (visible in Path Segments list)")
                print(f"  Duct width: 12.0 inches (DEFAULT_DUCT_WIDTH_IN)")
                print(f"  Duct height: 8.0 inches (DEFAULT_DUCT_HEIGHT_IN)")
                
                # Calculate difference
                expected_length = 12.2
                expected_width = 12.0
                expected_height = 8.0
                
                print(f"\nDiscrepancy analysis:")
                print(f"  Length diff: {segment.length - expected_length:.1f} ft")
                print(f"  Width diff: {segment.duct_width - expected_width:.1f} inches")
                print(f"  Height diff: {segment.duct_height - expected_height:.1f} inches")
                
            else:
                print("Segment 19 not found - using first available segment")
                segment = session.query(HVACSegment).first()
                if segment:
                    print(f"First segment (ID {segment.id}):")
                    print(f"  Length: {segment.length}")
                    print(f"  Duct dimensions: {segment.duct_width} x {segment.duct_height}")
                    
        return True
        
    except Exception as e:
        print(f"ERROR in drawing data comparison: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("Starting segment data debugging...\n")
    
    # Run debug analysis
    result1 = debug_segment_data()
    result2 = compare_segment_with_drawing_data()
    
    print(f"\n=== DEBUG SUMMARY ===")
    print(f"Segment data debug: {'PASS' if result1 else 'FAIL'}")
    print(f"Drawing comparison: {'PASS' if result2 else 'FAIL'}")
    
    if result1 and result2:
        print("✓ Debug analysis completed - check output above for problematic segments")
    else:
        print("✗ Some debug steps failed - check error messages above")