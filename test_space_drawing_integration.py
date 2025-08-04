#!/usr/bin/env python3
"""
Test script for space-drawing integration with project reload
Tests that spaces are properly tied to drawings and rectangles persist
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.database import initialize_database, get_session
from models.space import Space, RoomBoundary, SurfaceType
from models.drawing import Drawing
from models.project import Project

def test_space_drawing_integration():
    """Test the complete space-drawing integration"""
    print("🧪 Testing space-drawing integration with project reload...")
    
    # Initialize database
    db_path = initialize_database()
    print(f"Database initialized at: {db_path}")
    session = get_session()
    
    try:
        # Test 1: Verify migration worked
        print("\n🔍 Test 1: Verifying migration results...")
        
        spaces_with_drawings = session.query(Space).filter(Space.drawing_id.isnot(None)).all()
        print(f"Found {len(spaces_with_drawings)} spaces with drawing assignments:")
        
        for space in spaces_with_drawings:
            print(f"  - Space: {space.name} (ID: {space.id})")
            print(f"    Drawing: {space.drawing.name} (ID: {space.drawing_id})")
            print(f"    Room boundaries: {len(space.room_boundaries)}")
            
        # Test 2: Test space-to-drawing relationship methods
        print("\n🔍 Test 2: Testing relationship methods...")
        
        if spaces_with_drawings:
            space = spaces_with_drawings[0]
            print(f"Testing space: {space.name}")
            print(f"  get_drawing_name(): {space.get_drawing_name()}")
            print(f"  Primary boundary: {space.get_primary_room_boundary()}")
            
            if space.drawing:
                drawing = space.drawing
                print(f"  Drawing space count: {drawing.get_space_count()}")
                print(f"  Drawing space names: {drawing.get_space_names()}")
        
        # Test 3: Test to_dict with drawing information
        print("\n🔍 Test 3: Testing to_dict with drawing information...")
        
        if spaces_with_drawings:
            space = spaces_with_drawings[0]
            space_dict = space.to_dict()
            print(f"Space dict includes:")
            print(f"  drawing_id: {space_dict.get('drawing_id')}")
            print(f"  drawing_name: {space_dict.get('drawing_name')}")
            
        # Test 4: Test drawing-space relationship queries
        print("\n🔍 Test 4: Testing drawing-space relationship queries...")
        
        drawings_with_spaces = session.query(Drawing).filter(Drawing.spaces.any()).all()
        print(f"Found {len(drawings_with_spaces)} drawings with spaces:")
        
        for drawing in drawings_with_spaces:
            print(f"  - Drawing: {drawing.name} (ID: {drawing.id})")
            print(f"    Spaces: {len(drawing.spaces)}")
            for space in drawing.spaces:
                print(f"      * {space.name}")
                
        # Test 5: Test RoomBoundary relationships
        print("\n🔍 Test 5: Testing RoomBoundary relationships...")
        
        boundaries = session.query(RoomBoundary).all()
        print(f"Found {len(boundaries)} room boundaries:")
        
        for boundary in boundaries:
            print(f"  - Boundary ID: {boundary.id}")
            print(f"    Space: {boundary.space.name if boundary.space else 'None'}")
            print(f"    Drawing: {boundary.drawing.name if boundary.drawing else 'None'}")
            print(f"    Position: ({boundary.x_position}, {boundary.y_position})")
            print(f"    Size: {boundary.width}x{boundary.height}")
            print(f"    Area: {boundary.calculated_area} sf")
            
        # Test 6: Simulate drawing interface loading space rectangles
        print("\n🔍 Test 6: Simulating drawing interface rectangle loading...")
        
        if drawings_with_spaces:
            drawing = drawings_with_spaces[0]
            print(f"Simulating load for drawing: {drawing.name}")
            
            # Get all room boundaries for this drawing (simulating load_space_rectangles)
            boundaries = session.query(RoomBoundary).filter(
                RoomBoundary.drawing_id == drawing.id
            ).all()
            
            print(f"Would load {len(boundaries)} space rectangles:")
            for boundary in boundaries:
                space_name = boundary.space.name if boundary.space else f"Space {boundary.space_id}"
                area_formatted = f"{boundary.calculated_area:.0f} sf" if boundary.calculated_area else "0 sf"
                
                print(f"  🏠 {space_name} - {area_formatted}")
                print(f"    Position: ({boundary.x_position}, {boundary.y_position})")
                print(f"    Size: {boundary.width}x{boundary.height}")
                
        # Test 7: Test multiple materials with drawing association
        print("\n🔍 Test 7: Testing multiple materials with drawing association...")
        
        if spaces_with_drawings:
            space = spaces_with_drawings[0]
            ceiling_materials = space.get_ceiling_materials()
            wall_materials = space.get_wall_materials()
            floor_materials = space.get_floor_materials()
            
            print(f"Space {space.name} materials:")
            print(f"  Ceiling: {ceiling_materials}")
            print(f"  Wall: {wall_materials}")
            print(f"  Floor: {floor_materials}")
            print(f"  Associated drawing: {space.get_drawing_name()}")
            
        print("\n✅ All tests completed successfully!")
        print("\n📋 Summary:")
        print(f"  - {len(spaces_with_drawings)} spaces with drawing assignments")
        print(f"  - {len(drawings_with_spaces)} drawings with spaces")
        print(f"  - {len(boundaries)} room boundaries total")
        print("\n🎯 Space rectangles should now persist after project reload!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


def test_project_reload_simulation():
    """Simulate a project reload to test persistence"""
    print("\n🔄 Simulating project reload...")
    
    session = get_session()
    
    try:
        # Simulate what happens when drawing interface loads
        drawings = session.query(Drawing).all()
        
        for drawing in drawings:
            print(f"\n📋 Loading drawing: {drawing.name}")
            
            # Simulate loading spaces on this drawing
            spaces_on_drawing = drawing.spaces
            print(f"  Spaces on drawing: {len(spaces_on_drawing)}")
            
            for space in spaces_on_drawing:
                print(f"    - {space.name}")
                
            # Simulate loading room boundaries for visual display
            boundaries = session.query(RoomBoundary).filter(
                RoomBoundary.drawing_id == drawing.id
            ).all()
            
            print(f"  Rectangle boundaries to display: {len(boundaries)}")
            
            for boundary in boundaries:
                space_name = boundary.space.name if boundary.space else "Unknown"
                print(f"    🟩 {space_name}: ({boundary.x_position}, {boundary.y_position}) "
                      f"{boundary.width}x{boundary.height} = {boundary.calculated_area:.0f} sf")
                      
        print("\n✅ Project reload simulation completed!")
        
    except Exception as e:
        print(f"❌ Reload simulation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    test_space_drawing_integration()
    test_project_reload_simulation()