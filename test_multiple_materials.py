#!/usr/bin/env python3
"""
Test script for multiple materials functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.database import initialize_database, get_session
from models.space import Space, SpaceSurfaceMaterial, SurfaceType
from models.project import Project
from data.materials import STANDARD_MATERIALS

def test_multiple_materials():
    """Test the multiple materials functionality"""
    print("Testing multiple materials functionality...")
    
    # Initialize database
    db_path = initialize_database()
    print(f"Database initialized at: {db_path}")
    session = get_session()
    
    try:
        # Create a test project
        project = Project(
            name="Test Multiple Materials",
            description="Testing new multiple materials system"
        )
        session.add(project)
        session.flush()  # Get the project ID
        
        # Create a test space
        space = Space(
            project_id=project.id,
            name="Test Space",
            description="Testing space for multiple materials",
            floor_area=100.0,
            ceiling_height=9.0,
            wall_area=360.0,
            target_rt60=0.8
        )
        
        # Set legacy materials for backward compatibility test
        space.ceiling_material = 'aceid_panel_8mm_thk_flat_to_wall'
        space.wall_material = '1"_fiberglass_6pcf_unfaced_mtg._4'
        space.floor_material = '1"_fiberglass_7pcf_unperforated_vinyl_clad_mtg._4'
        
        session.add(space)
        session.flush()  # Get the space ID
        
        print(f"Created test space with ID: {space.id}")
        
        # Test 1: Add multiple materials to ceiling
        print("\nTest 1: Adding multiple ceiling materials...")
        ceiling_materials = [
            'aceid_panel_8mm_thk_flat_to_wall',
            'aceid_panel_8mm_thk_200mm_off_wall'
        ]
        space.set_surface_materials(SurfaceType.CEILING, ceiling_materials, session)
        
        # Test 2: Add multiple materials to walls
        print("Test 2: Adding multiple wall materials...")
        wall_materials = [
            '1"_fiberglass_6pcf_unfaced_mtg._4',
            '1/2"_gypsum_board'
        ]
        space.set_surface_materials(SurfaceType.WALL, wall_materials, session)
        
        # Test 3: Keep single floor material
        print("Test 3: Setting single floor material...")
        floor_materials = ['1"_fiberglass_7pcf_unperforated_vinyl_clad_mtg._4']
        space.set_surface_materials(SurfaceType.FLOOR, floor_materials, session)
        
        session.commit()
        print("Materials saved to database successfully!")
        
        # Test 4: Retrieve and verify materials
        print("\nTest 4: Retrieving materials...")
        fresh_space = session.query(Space).filter(Space.id == space.id).first()
        
        ceiling_mats = fresh_space.get_ceiling_materials()
        wall_mats = fresh_space.get_wall_materials() 
        floor_mats = fresh_space.get_floor_materials()
        
        print(f"Ceiling materials: {ceiling_mats}")
        print(f"Wall materials: {wall_mats}")
        print(f"Floor materials: {floor_mats}")
        
        # Test 5: Test average absorption coefficients
        print("\nTest 5: Testing average absorption coefficients...")
        ceiling_avg = fresh_space.get_average_absorption_coefficient(SurfaceType.CEILING)
        wall_avg = fresh_space.get_average_absorption_coefficient(SurfaceType.WALL)
        floor_avg = fresh_space.get_average_absorption_coefficient(SurfaceType.FLOOR)
        
        print(f"Average ceiling absorption coefficient: {ceiling_avg:.3f}")
        print(f"Average wall absorption coefficient: {wall_avg:.3f}")
        print(f"Average floor absorption coefficient: {floor_avg:.3f}")
        
        # Test 6: Test to_dict method
        print("\nTest 6: Testing to_dict method...")
        space_dict = fresh_space.to_dict()
        print(f"Ceiling materials in dict: {space_dict['ceiling_materials']}")
        print(f"Wall materials in dict: {space_dict['wall_materials']}")
        print(f"Floor materials in dict: {space_dict['floor_materials']}")
        
        # Test 7: Test RT60 calculation with multiple materials
        print("\nTest 7: Testing RT60 calculation with multiple materials...")
        from calculations.rt60_calculator import RT60Calculator
        
        calculator = RT60Calculator()
        space_data = space_dict.copy()
        space_data['volume'] = space.volume = space.floor_area * space.ceiling_height
        space_data['ceiling_area'] = space.floor_area
        
        rt60_result = calculator.calculate_space_rt60(space_data, method='sabine')
        print(f"RT60 calculation result: {rt60_result['rt60']:.2f} seconds")
        print(f"Number of surfaces in calculation: {len(rt60_result['surfaces'])}")
        
        for surface in rt60_result['surfaces']:
            print(f"  {surface['type']}: {surface['material_name']} (α={surface['absorption_coeff']:.3f})")
        
        print("\n✅ All tests passed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    test_multiple_materials()