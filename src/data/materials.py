"""
Standard acoustic materials library for RT60 calculations
"""
import sqlite3
import os
from typing import Dict, List, Optional, Tuple

def get_database_path():
    """Get the path to the acoustic materials database
    
    Handles both development and bundled deployment scenarios
    
    Returns:
        str: Absolute path to the materials database file
    """
    try:
        # Try to use the deployment-aware utility
        from utils import get_materials_database_path
        db_path = get_materials_database_path()
        return db_path
    except ImportError:
        # Fallback for development or if utils not available
        try:
            from utils.general_utils import get_materials_database_path
            db_path = get_materials_database_path()
            return db_path
        except ImportError:
            # Final fallback: construct path manually
            current_dir = os.path.dirname(__file__)
            project_root = os.path.dirname(os.path.dirname(current_dir))
            db_path = os.path.join(project_root, 'materials', 'acoustic_materials.db')
            return db_path

def load_materials_from_database() -> Dict[str, Dict]:
    """Load materials from the acoustic_materials.db database
    
    Returns:
        Dict[str, Dict]: Dictionary of materials keyed by material key
        
    Note:
        Falls back to get_fallback_materials() if database is not found or error occurs
    """
    db_path = get_database_path()
    materials = {}
    
    try:
        if not os.path.exists(db_path):
            print(f"Warning: Materials database not found at {db_path}")
            print(f"  Expected location: {os.path.abspath(db_path)}")
            print(f"  Using fallback materials ({len(get_fallback_materials())} materials)")
            return get_fallback_materials()
        
        # Check if file is readable
        if not os.access(db_path, os.R_OK):
            print(f"Warning: Materials database exists but is not readable: {db_path}")
            print(f"  Using fallback materials")
            return get_fallback_materials()
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='acoustic_materials'
            """)
            if not cursor.fetchone():
                print(f"Warning: Materials database exists but 'acoustic_materials' table not found")
                print(f"  Using fallback materials")
                return get_fallback_materials()
            
            cursor.execute("""
                SELECT name, coeff_125, coeff_250, coeff_500, coeff_1000, coeff_2000, coeff_4000, nrc
                FROM acoustic_materials
                ORDER BY name
            """)
            
            rows = cursor.fetchall()
            
            for row in rows:
                name, coeff_125, coeff_250, coeff_500, coeff_1000, coeff_2000, coeff_4000, nrc = row
                
                # Skip rows with None or empty names
                if not name or not name.strip():
                    continue
                
                # Create a clean key from the material name
                key = name.lower().replace(' ', '_').replace(',', '').replace('(', '').replace(')', '').replace('&', 'and')
                
                # Categorize materials based on their names
                category = categorize_material(name)
                
                materials[key] = {
                    'name': name,
                    'absorption_coeff': nrc or coeff_1000 or 0.0,  # Use NRC or 1000Hz coefficient
                    'coefficients': {
                        '125': coeff_125 or 0.0,
                        '250': coeff_250 or 0.0,
                        '500': coeff_500 or 0.0,
                        '1000': coeff_1000 or 0.0,
                        '2000': coeff_2000 or 0.0,
                        '4000': coeff_4000 or 0.0
                    },
                    'nrc': nrc,
                    'description': f"{name} - NRC: {nrc:.2f}" if nrc else name,
                    'category': category,
                    'source': 'sqlite_database'  # Mark as from SQLite database
                }
                
            print(f"Loaded {len(materials)} materials from database: {db_path}")
            return materials
            
        except sqlite3.Error as e:
            print(f"SQLite error loading materials from database: {e}")
            print(f"  Database path: {db_path}")
            return get_fallback_materials()
        finally:
            conn.close()
        
    except Exception as e:
        print(f"Error loading materials from database: {e}")
        print(f"  Database path: {db_path}")
        import traceback
        traceback.print_exc()
        return get_fallback_materials()

def categorize_material(name: str) -> str:
    """Categorize a material based on its name"""
    name_lower = name.lower()
    
    # Ceiling materials
    if any(term in name_lower for term in ['ceiling', 'tile', 'panel', 'acoustic tile', 'suspended']):
        return 'ceiling'
    
    # Floor materials  
    elif any(term in name_lower for term in ['carpet', 'floor', 'vinyl', 'concrete', 'wood', 'rubber', 'ceramic']):
        return 'floor'
        
    # Wall materials (default)
    else:
        return 'wall'

def get_materials_by_category(category: str) -> Dict[str, Dict]:
    """Get materials filtered by category"""
    all_materials = get_all_materials()
    return {k: v for k, v in all_materials.items() if v['category'] == category}

def get_fallback_materials() -> Dict[str, Dict]:
    """Fallback materials if database is not available"""
    return {
        # Ceiling Materials
        'act_standard': {
            'name': 'Acoustic Ceiling Tile (Standard)',
            'absorption_coeff': 0.70,
            'description': 'Standard acoustic ceiling tile',
            'category': 'ceiling'
        },
        'act_high_performance': {
            'name': 'Acoustic Ceiling Tile (High Performance)',
            'absorption_coeff': 0.85,
            'description': 'High-performance acoustic ceiling tile',
            'category': 'ceiling'
        },
        'gypsum_ceiling': {
            'name': 'Gypsum Board Ceiling',
            'absorption_coeff': 0.10,
            'description': 'Painted gypsum board ceiling',
            'category': 'ceiling'
        },
        'metal_deck': {
            'name': 'Metal Deck',
            'absorption_coeff': 0.05,
            'description': 'Exposed metal deck ceiling',
            'category': 'ceiling'
        },
        
        # Wall Materials
        'drywall_painted': {
            'name': 'Painted Drywall',
            'absorption_coeff': 0.10,
            'description': 'Painted gypsum board wall',
            'category': 'wall'
        },
        'drywall_fabric': {
            'name': 'Fabric-Covered Drywall',
            'absorption_coeff': 0.35,
            'description': 'Fabric-wrapped gypsum board',
            'category': 'wall'
        },
        'concrete_block': {
            'name': 'Concrete Block (Painted)',
            'absorption_coeff': 0.07,
            'description': 'Painted concrete masonry unit',
            'category': 'wall'
        },
        'brick_painted': {
            'name': 'Brick (Painted)',
            'absorption_coeff': 0.08,
            'description': 'Painted brick wall',
            'category': 'wall'
        },
        'acoustic_panels': {
            'name': 'Acoustic Wall Panels',
            'absorption_coeff': 0.80,
            'description': 'Specialized acoustic wall treatment',
            'category': 'wall'
        },
        
        # Floor Materials
        'carpet_heavy': {
            'name': 'Carpet (Heavy)',
            'absorption_coeff': 0.55,
            'description': 'Heavy carpet with padding',
            'category': 'floor'
        },
        'carpet_medium': {
            'name': 'Carpet (Medium)',
            'absorption_coeff': 0.40,
            'description': 'Medium-weight carpet',
            'category': 'floor'
        },
        'carpet_tile': {
            'name': 'Carpet Tile',
            'absorption_coeff': 0.30,
            'description': 'Modular carpet tile',
            'category': 'floor'
        },
        'vinyl_tile': {
            'name': 'Vinyl Tile',
            'absorption_coeff': 0.05,
            'description': 'Vinyl composition tile',
            'category': 'floor'
        },
        'ceramic_tile': {
            'name': 'Ceramic Tile',
            'absorption_coeff': 0.02,
            'description': 'Ceramic floor tile',
            'category': 'floor'
        },
        'concrete_sealed': {
            'name': 'Concrete (Sealed)',
            'absorption_coeff': 0.02,
            'description': 'Sealed concrete floor',
            'category': 'floor'
        },
        'wood_floor': {
            'name': 'Wood Floor',
            'absorption_coeff': 0.10,
            'description': 'Hardwood flooring',
            'category': 'floor'
        },
        'rubber_floor': {
            'name': 'Rubber Flooring',
            'absorption_coeff': 0.04,
            'description': 'Rubber sheet flooring',
            'category': 'floor'
        }
    }

def get_all_materials() -> Dict[str, Dict]:
    """Get all materials, loading from database if available"""
    return load_materials_from_database()

# Initialize materials on module import
STANDARD_MATERIALS = get_all_materials()

# Room type defaults for quick setup - materials should be None to remain unassigned
ROOM_TYPE_DEFAULTS = {
    'office': {
        'name': 'Office',
        'target_rt60': 0.6,
        'ceiling_material': None,
        'wall_material': None,
        'floor_material': None
    },
    'conference': {
        'name': 'Conference Room',
        'target_rt60': 0.8,
        'ceiling_material': None,
        'wall_material': None,
        'floor_material': None
    },
    'classroom': {
        'name': 'Classroom',
        'target_rt60': 0.6,
        'ceiling_material': None,
        'wall_material': None,
        'floor_material': None
    },
    'auditorium': {
        'name': 'Auditorium',
        'target_rt60': 1.5,
        'ceiling_material': None,
        'wall_material': None,
        'floor_material': None
    },
    'lobby': {
        'name': 'Lobby',
        'target_rt60': 1.2,
        'ceiling_material': None,
        'wall_material': None,
        'floor_material': None
    },
    'corridor': {
        'name': 'Corridor',
        'target_rt60': 1.0,
        'ceiling_material': None,
        'wall_material': None,
        'floor_material': None
    }
}