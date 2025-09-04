#!/usr/bin/env python3
"""
Test Segment Update and Debugging

This script tests and validates the HVAC segment update mechanism with debugging output
to ensure database saves and UI updates work correctly.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Enable debug output
os.environ['HVAC_DEBUG_EXPORT'] = '1'

def test_segment_database_operations():
    """Test segment database operations with debugging"""
    print("=== Testing Segment Database Operations ===")
    
    try:
        # Initialize database
        from models.database import initialize_database, get_hvac_session
        initialize_database()
        print("Database initialized successfully")
        from models.hvac import HVACSegment, HVACComponent, HVACPath
        from models.project import Project
        from models.drawing import Drawing
        
        with get_hvac_session() as session:
            # Find an existing project or create one
            project = session.query(Project).first()
            if not project:
                print("No project found - creating test project")
                project = Project(name="Test Project for Segment Updates")
                session.add(project)
                session.flush()
            
            print(f"Using project: {project.name} (ID: {project.id})")
            
            # Find an existing drawing or create one
            drawing = session.query(Drawing).filter_by(project_id=project.id).first()
            if not drawing:
                print("No drawing found - creating test drawing")
                drawing = Drawing(
                    project_id=project.id,
                    filename="test_drawing.pdf",
                    file_path="/tmp/test.pdf"
                )
                session.add(drawing)
                session.flush()
            
            print(f"Using drawing: {drawing.filename} (ID: {drawing.id})")
            
            # Create test components
            comp1 = HVACComponent(
                project_id=project.id,
                drawing_id=drawing.id,
                name="TEST-AHU-1",
                component_type="ahu",
                x_position=100,
                y_position=100,
                cfm=2000
            )
            
            comp2 = HVACComponent(
                project_id=project.id,
                drawing_id=drawing.id,
                name="TEST-DIFF-1",
                component_type="diffuser",
                x_position=200,
                y_position=200,
                cfm=500
            )
            
            session.add_all([comp1, comp2])
            session.flush()
            
            print(f"Created components: {comp1.name} (ID: {comp1.id}), {comp2.name} (ID: {comp2.id})")
            
            # Create test path
            hvac_path = HVACPath(
                project_id=project.id,
                name="Test Path for Segment Updates",
                description="Testing segment update functionality",
                primary_source_id=comp1.id
            )
            session.add(hvac_path)
            session.flush()
            
            print(f"Created path: {hvac_path.name} (ID: {hvac_path.id})")
            
            # Create test segment
            segment = HVACSegment(
                hvac_path_id=hvac_path.id,
                from_component_id=comp1.id,
                to_component_id=comp2.id,
                length=25.5,
                segment_order=1,
                duct_width=12.0,
                duct_height=8.0,
                duct_shape='rectangular',
                duct_type='sheet_metal',
                flow_rate=2000.0
            )
            session.add(segment)
            session.flush()
            
            print(f"Created segment: ID {segment.id}")
            print(f"  Initial values: length={segment.length}, width={segment.duct_width}, height={segment.duct_height}")
            
            # Test update
            print("\n--- Testing Segment Update ---")
            segment.length = 30.0
            segment.duct_width = 14.0
            segment.duct_height = 10.0
            session.commit()
            
            # Verify update
            session.refresh(segment)
            print(f"  Updated values: length={segment.length}, width={segment.duct_width}, height={segment.duct_height}")
            
            # Test path calculator integration
            print("\n--- Testing Path Calculator Integration ---")
            from calculations.hvac_path_calculator import HVACPathCalculator
            
            calculator = HVACPathCalculator(project.id)
            result = calculator.calculate_path_noise(hvac_path.id)
            
            print(f"  Path calculation result:")
            print(f"    Valid: {result.calculation_valid}")
            print(f"    Source noise: {result.source_noise} dB(A)")
            print(f"    Terminal noise: {result.terminal_noise} dB(A)")
            print(f"    Segments analyzed: {len(result.segment_results)}")
            
            # Clean up test data
            print("\n--- Cleaning up test data ---")
            session.delete(segment)
            session.delete(hvac_path)
            session.delete(comp1)
            session.delete(comp2)
            session.commit()
            
            print("Test completed successfully!")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_segment_dialog_operations():
    """Test segment dialog operations (non-GUI parts)"""
    print("\n=== Testing Segment Dialog Data Operations ===")
    
    try:
        # Initialize database if not already done
        from models.database import initialize_database
        try:
            initialize_database()
        except Exception:
            pass  # Already initialized
            
        # Test data loading and caching mechanisms
        from ui.dialogs.hvac_segment_dialog import HVACSegmentDialog
        from models.database import get_hvac_session
        from models.hvac import HVACSegment
        
        with get_hvac_session() as session:
            # Find any existing segment for testing
            segment = session.query(HVACSegment).first()
            if not segment:
                print("No existing segments found - skipping dialog test")
                return True
            
            print(f"Testing with segment ID: {segment.id}")
            print(f"  Database values: length={segment.length}, width={segment.duct_width}, height={segment.duct_height}")
            
            # Test the data caching mechanism
            dialog = HVACSegmentDialog(segment=segment.id)  # Pass as int ID
            
            if hasattr(dialog, '_segment_data'):
                cached = dialog._segment_data
                print(f"  Cached values: length={cached.get('length')}, width={cached.get('duct_width')}, height={cached.get('duct_height')}")
                
                # Verify cache matches database
                if (cached.get('length') == segment.length and 
                    cached.get('duct_width') == segment.duct_width and
                    cached.get('duct_height') == segment.duct_height):
                    print("  ✓ Cache matches database values")
                else:
                    print("  ✗ Cache does not match database values")
                    return False
            else:
                print("  ✗ No cached data found")
                return False
            
        print("Dialog test completed successfully!")
        
    except Exception as e:
        print(f"Dialog test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """Run all segment update tests"""
    print("HVAC Segment Update Debug Test Suite")
    print("=====================================")
    
    results = []
    
    # Test database operations
    results.append(test_segment_database_operations())
    
    # Test dialog operations
    results.append(test_segment_dialog_operations())
    
    # Summary
    print(f"\n=== Test Summary ===")
    print(f"Tests run: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())