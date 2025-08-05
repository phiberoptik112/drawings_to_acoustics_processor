#!/usr/bin/env python3
"""
Test script to simulate the dialog functionality with multiple materials
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.database import initialize_database, get_session
from models.space import Space, SurfaceType
from data.materials import STANDARD_MATERIALS

def simulate_dialog_save():
    """Simulate what happens in the SpaceEditDialog.save_changes method"""
    print("Simulating SpaceEditDialog.save_changes functionality...")
    
    # Initialize database
    db_path = initialize_database()
    print(f"Database initialized at: {db_path}")
    session = get_session()
    
    try:
        # Get the migrated space (ID 1)
        space = session.query(Space).filter(Space.id == 1).first()
        if not space:
            print("❌ No space found with ID 1")
            return
            
        print(f"Found space: {space.name}")
        
        # Simulate loading materials (like load_space_data does)
        print("\nSimulating load_space_data...")
        ceiling_materials = space.get_ceiling_materials()
        wall_materials = space.get_wall_materials()
        floor_materials = space.get_floor_materials()
        
        print(f"Loaded materials:")
        print(f"  ceiling_materials: {ceiling_materials}")
        print(f"  wall_materials: {wall_materials}")
        print(f"  floor_materials: {floor_materials}")
        
        # Simulate adding a second material to ceiling (like UI would do)
        print("\nSimulating adding second ceiling material...")
        ceiling_materials.append('aceid_panel_8mm_thk_200mm_off_wall')
        wall_materials.append('1/2"_gypsum_board')
        
        print(f"Materials after user adds more:")
        print(f"  ceiling_materials: {ceiling_materials}")
        print(f"  wall_materials: {wall_materials}")
        print(f"  floor_materials: {floor_materials}")
        
        # Simulate saving (like save_changes does)
        print("\nSimulating save_changes...")
        
        # Update materials using new system
        space.set_surface_materials(SurfaceType.CEILING, ceiling_materials, session)
        space.set_surface_materials(SurfaceType.WALL, wall_materials, session)
        space.set_surface_materials(SurfaceType.FLOOR, floor_materials, session)
        
        # Update legacy fields for backward compatibility
        space.ceiling_material = ceiling_materials[0] if ceiling_materials else None
        space.wall_material = wall_materials[0] if wall_materials else None
        space.floor_material = floor_materials[0] if floor_materials else None
        
        session.commit()
        print("Changes committed successfully!")
        
        # Verify the changes (like the debug output does)
        fresh_space = session.query(Space).filter(Space.id == space.id).first()
        print("\nVerification - Fresh query results:")
        print(f"  fresh_space ceiling materials: {fresh_space.get_ceiling_materials()}")
        print(f"  fresh_space wall materials: {fresh_space.get_wall_materials()}")
        print(f"  fresh_space floor materials: {fresh_space.get_floor_materials()}")
        
        # Test the RT60 calculation with multiple materials
        print("\nTesting RT60 calculation with updated materials...")
        space_dict = fresh_space.to_dict()
        space_dict['volume'] = fresh_space.floor_area * fresh_space.ceiling_height if fresh_space.floor_area and fresh_space.ceiling_height else 900
        space_dict['ceiling_area'] = fresh_space.floor_area or 100
        
        from calculations.rt60_calculator import RT60Calculator
        calculator = RT60Calculator()
        rt60_result = calculator.calculate_space_rt60(space_dict, method='sabine')
        
        print(f"RT60 with multiple materials: {rt60_result['rt60']:.2f} seconds")
        print(f"Surfaces in calculation:")
        for surface in rt60_result['surfaces']:
            print(f"  {surface['type']}: {surface['material_name']} (α={surface['absorption_coeff']:.3f})")
        
        print("\n✅ Dialog simulation completed successfully!")
        print("✅ The issue with multiple materials should now be resolved!")
        
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    simulate_dialog_save()