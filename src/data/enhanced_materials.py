"""
Enhanced acoustic materials library with frequency-dependent absorption coefficients
Based on industry standards and manufacturer data
"""

# Standard octave band center frequencies for acoustic analysis
OCTAVE_BANDS = [125, 250, 500, 1000, 2000, 4000]

# Surface categories for material organization 
SURFACE_CATEGORIES = {
    'walls': {
        'name': 'Wall Materials',
        'description': 'Materials typically used on walls',
        'types': ['Primary Wall', 'Secondary Wall', 'Accent Wall', 'Acoustic Treatment']
    },
    'ceilings': {
        'name': 'Ceiling Materials', 
        'description': 'Materials used for ceiling installations',
        'types': ['Primary Ceiling', 'Secondary Ceiling', 'Clouds/Baffles', 'Mechanical']
    },
    'floors': {
        'name': 'Floor Materials',
        'description': 'Floor covering materials',
        'types': ['Floor Surface', 'Raised Floor', 'Floor Treatment']
    },
    'doors': {
        'name': 'Door Materials',
        'description': 'Door and opening materials',
        'types': ['Entry Doors', 'Interior Doors', 'Glazed Doors']
    },
    'windows': {
        'name': 'Window Materials',
        'description': 'Glazing and window materials', 
        'types': ['Windows', 'Glazed Partitions', 'Curtain Wall']
    },
    'specialty': {
        'name': 'Specialty Materials',
        'description': 'Custom and specialty acoustic materials',
        'types': ['Custom Surface', 'Equipment', 'Furniture']
    }
}

# Room type presets with target RT60 values
ROOM_TYPE_PRESETS = {
    'conference': {
        'name': 'Conference Room',
        'target_rt60': 0.8,
        'tolerance': 0.1,
        'description': 'Meeting and conference spaces'
    },
    'office_private': {
        'name': 'Private Office',
        'target_rt60': 0.6,
        'tolerance': 0.1,
        'description': 'Individual office spaces'
    },
    'office_open': {
        'name': 'Open Office',
        'target_rt60': 0.8,
        'tolerance': 0.15,
        'description': 'Open plan office areas'
    },
    'classroom': {
        'name': 'Classroom',
        'target_rt60': 0.6,
        'tolerance': 0.1,
        'description': 'Educational spaces'
    },
    'auditorium': {
        'name': 'Auditorium',
        'target_rt60': 1.2,
        'tolerance': 0.2,
        'description': 'Large presentation spaces'
    },
    'gym': {
        'name': 'Gymnasium',
        'target_rt60': 2.0,
        'tolerance': 0.3,
        'description': 'Sports and recreation facilities'
    },
    'lobby': {
        'name': 'Lobby',
        'target_rt60': 1.5,
        'tolerance': 0.2,
        'description': 'Reception and waiting areas'
    },
    'corridor': {
        'name': 'Corridor',
        'target_rt60': 1.0,
        'tolerance': 0.15,
        'description': 'Circulation spaces'
    },
    'custom': {
        'name': 'Custom',
        'target_rt60': None,
        'tolerance': 0.1,
        'description': 'User-defined target'
    }
}

# Enhanced materials database with frequency-dependent coefficients
# Absorption coefficients for 125, 250, 500, 1000, 2000, 4000 Hz
ENHANCED_MATERIALS = {
    # CEILING MATERIALS
    'act_standard': {
        'name': 'Acoustic Ceiling Tile (Standard)',
        'category': 'ceilings',
        'manufacturer': 'Generic',
        'description': 'Standard mineral fiber acoustic ceiling tile',
        'absorption_coefficients': {
            125: 0.29, 250: 0.42, 500: 0.71, 1000: 0.87, 2000: 0.89, 4000: 0.83
        },
        'mounting_type': 'suspended',
        'thickness': '3/4"',
        'source': 'ASTM C423 Test Data'
    },
    'act_high_performance': {
        'name': 'Acoustic Ceiling Tile (High Performance)',
        'category': 'ceilings',
        'manufacturer': 'Generic',
        'description': 'High-performance mineral fiber with enhanced absorption',
        'absorption_coefficients': {
            125: 0.55, 250: 0.75, 500: 0.95, 1000: 0.99, 2000: 0.96, 4000: 0.93
        },
        'mounting_type': 'suspended',
        'thickness': '3/4"',
        'source': 'Manufacturer Test Data'
    },
    'act_metal': {
        'name': 'Metal Pan Ceiling Tile',
        'category': 'ceilings',
        'manufacturer': 'Generic',
        'description': 'Perforated metal pan with acoustic backing',
        'absorption_coefficients': {
            125: 0.15, 250: 0.35, 500: 0.55, 1000: 0.72, 2000: 0.70, 4000: 0.65
        },
        'mounting_type': 'suspended',
        'thickness': '1"',
        'source': 'Industry Standard'
    },
    'gypsum_ceiling': {
        'name': 'Gypsum Board Ceiling',
        'category': 'ceilings',
        'manufacturer': 'Generic',
        'description': 'Painted gypsum board ceiling',
        'absorption_coefficients': {
            125: 0.05, 250: 0.07, 500: 0.09, 1000: 0.11, 2000: 0.08, 4000: 0.04
        },
        'mounting_type': 'direct',
        'thickness': '5/8"',
        'source': 'Building Acoustics Handbook'
    },
    'metal_deck': {
        'name': 'Metal Deck',
        'category': 'ceilings',
        'manufacturer': 'Generic',
        'description': 'Exposed painted metal deck ceiling',
        'absorption_coefficients': {
            125: 0.02, 250: 0.02, 500: 0.03, 1000: 0.04, 2000: 0.05, 4000: 0.05
        },
        'mounting_type': 'direct',
        'thickness': '1.5"',
        'source': 'ASHRAE Handbook'
    },
    'clouds_baffles': {
        'name': 'Acoustic Clouds/Baffles',
        'category': 'ceilings',
        'manufacturer': 'Generic',
        'description': 'Suspended acoustic clouds or vertical baffles',
        'absorption_coefficients': {
            125: 0.85, 250: 1.14, 500: 1.07, 1000: 1.02, 2000: 0.99, 4000: 0.98
        },
        'mounting_type': 'suspended',
        'thickness': '2"',
        'source': 'Manufacturer Test Data'
    },

    # WALL MATERIALS
    'drywall_painted': {
        'name': 'Painted Drywall',
        'category': 'walls',
        'manufacturer': 'Generic',
        'description': 'Painted gypsum board wall',
        'absorption_coefficients': {
            125: 0.05, 250: 0.07, 500: 0.09, 1000: 0.11, 2000: 0.08, 4000: 0.04
        },
        'mounting_type': 'direct',
        'thickness': '5/8"',
        'source': 'Building Acoustics Handbook'
    },
    'drywall_fabric': {
        'name': 'Fabric-Covered Drywall',
        'category': 'walls',
        'manufacturer': 'Generic',
        'description': 'Fabric-wrapped gypsum board with air space',
        'absorption_coefficients': {
            125: 0.14, 250: 0.35, 500: 0.55, 1000: 0.72, 2000: 0.70, 4000: 0.65
        },
        'mounting_type': 'direct',
        'thickness': '5/8" + fabric',
        'source': 'Industry Standard'
    },
    'concrete_block': {
        'name': 'Concrete Block (Painted)',
        'category': 'walls',
        'manufacturer': 'Generic',
        'description': 'Painted concrete masonry unit',
        'absorption_coefficients': {
            125: 0.05, 250: 0.06, 500: 0.07, 1000: 0.09, 2000: 0.08, 4000: 0.08
        },
        'mounting_type': 'direct',
        'thickness': '8"',
        'source': 'ASHRAE Handbook'
    },
    'brick_painted': {
        'name': 'Brick (Painted)',
        'category': 'walls',
        'manufacturer': 'Generic',
        'description': 'Painted brick wall',
        'absorption_coefficients': {
            125: 0.02, 250: 0.03, 500: 0.04, 1000: 0.05, 2000: 0.07, 4000: 0.07
        },
        'mounting_type': 'direct',
        'thickness': '4"',
        'source': 'Building Acoustics Handbook'
    },
    'acoustic_panels_1in': {
        'name': 'Acoustic Wall Panels (1")',
        'category': 'walls',
        'manufacturer': 'Generic',
        'description': '1" thick fabric-wrapped acoustic panels',
        'absorption_coefficients': {
            125: 0.25, 250: 0.65, 500: 0.90, 1000: 0.95, 2000: 0.85, 4000: 0.80
        },
        'mounting_type': 'direct',
        'thickness': '1"',
        'source': 'Manufacturer Test Data'
    },
    'acoustic_panels_2in': {
        'name': 'Acoustic Wall Panels (2")',
        'category': 'walls',
        'manufacturer': 'Generic',
        'description': '2" thick fabric-wrapped acoustic panels',
        'absorption_coefficients': {
            125: 0.85, 250: 1.14, 500: 1.07, 1000: 1.02, 2000: 0.99, 4000: 0.98
        },
        'mounting_type': 'direct',
        'thickness': '2"',
        'source': 'Manufacturer Test Data'
    },
    'wood_paneling_thick': {
        'name': 'Wood Paneling (Thick)',
        'category': 'walls',
        'manufacturer': 'Generic',
        'description': 'Thick wood paneling over air space',
        'absorption_coefficients': {
            125: 0.19, 250: 0.14, 500: 0.09, 1000: 0.06, 2000: 0.06, 4000: 0.05
        },
        'mounting_type': 'spaced',
        'thickness': '3/4"',
        'source': 'Building Acoustics Handbook'
    },

    # FLOOR MATERIALS
    'carpet_heavy_pad': {
        'name': 'Carpet, Heavy (3/8" pile + pad)',
        'category': 'floors',
        'manufacturer': 'Generic',
        'description': 'Heavy carpet with 3/8" pile on pad',
        'absorption_coefficients': {
            125: 0.08, 250: 0.24, 500: 0.57, 1000: 0.69, 2000: 0.71, 4000: 0.73
        },
        'mounting_type': 'direct',
        'thickness': '3/8" + pad',
        'source': 'ASTM C423 Test Data'
    },
    'carpet_medium': {
        'name': 'Carpet, Medium Weight',
        'category': 'floors',
        'manufacturer': 'Generic',
        'description': 'Medium-weight carpet',
        'absorption_coefficients': {
            125: 0.05, 250: 0.15, 500: 0.30, 1000: 0.40, 2000: 0.50, 4000: 0.55
        },
        'mounting_type': 'direct',
        'thickness': '1/4"',
        'source': 'Industry Standard'
    },
    'carpet_tile': {
        'name': 'Carpet Tile',
        'category': 'floors',
        'manufacturer': 'Generic',
        'description': 'Modular carpet tile',
        'absorption_coefficients': {
            125: 0.02, 250: 0.06, 500: 0.14, 1000: 0.37, 2000: 0.60, 4000: 0.65
        },
        'mounting_type': 'direct',
        'thickness': '1/4"',
        'source': 'Manufacturer Data'
    },
    'vinyl_tile': {
        'name': 'Vinyl Tile',
        'category': 'floors',
        'manufacturer': 'Generic',
        'description': 'Vinyl composition tile on concrete',
        'absorption_coefficients': {
            125: 0.02, 250: 0.03, 500: 0.03, 1000: 0.03, 2000: 0.03, 4000: 0.02
        },
        'mounting_type': 'direct',
        'thickness': '1/8"',
        'source': 'ASHRAE Handbook'
    },
    'ceramic_tile': {
        'name': 'Ceramic Tile',
        'category': 'floors',
        'manufacturer': 'Generic',
        'description': 'Ceramic floor tile on concrete',
        'absorption_coefficients': {
            125: 0.01, 250: 0.01, 500: 0.01, 1000: 0.02, 2000: 0.02, 4000: 0.02
        },
        'mounting_type': 'direct',
        'thickness': '1/2"',
        'source': 'Building Acoustics Handbook'
    },
    'concrete_sealed': {
        'name': 'Concrete (Sealed)',
        'category': 'floors',
        'manufacturer': 'Generic',
        'description': 'Sealed concrete floor',
        'absorption_coefficients': {
            125: 0.01, 250: 0.01, 500: 0.02, 1000: 0.02, 2000: 0.02, 4000: 0.02
        },
        'mounting_type': 'direct',
        'thickness': '4"',
        'source': 'ASHRAE Handbook'
    },
    'wood_floor': {
        'name': 'Wood Floor',
        'category': 'floors',
        'manufacturer': 'Generic',
        'description': 'Hardwood flooring on joists',
        'absorption_coefficients': {
            125: 0.15, 250: 0.11, 500: 0.10, 1000: 0.07, 2000: 0.06, 4000: 0.07
        },
        'mounting_type': 'direct',
        'thickness': '3/4"',
        'source': 'Building Acoustics Handbook'
    },
    'rubber_floor': {
        'name': 'Rubber Flooring',
        'category': 'floors',
        'manufacturer': 'Generic',
        'description': 'Rubber sheet flooring',
        'absorption_coefficients': {
            125: 0.02, 250: 0.03, 500: 0.03, 1000: 0.04, 2000: 0.05, 4000: 0.05
        },
        'mounting_type': 'direct',
        'thickness': '1/4"',
        'source': 'Industry Standard'
    },

    # DOOR MATERIALS
    'solid_wood_doors': {
        'name': 'Solid Wood Doors',
        'category': 'doors',
        'manufacturer': 'Generic',
        'description': 'Solid wood doors',
        'absorption_coefficients': {
            125: 0.14, 250: 0.10, 500: 0.06, 1000: 0.08, 2000: 0.10, 4000: 0.10
        },
        'mounting_type': 'direct',
        'thickness': '1.75"',
        'source': 'Building Acoustics Handbook'
    },
    'hollow_wood_doors': {
        'name': 'Hollow Wood Doors',
        'category': 'doors',
        'manufacturer': 'Generic',
        'description': 'Hollow core wood doors',
        'absorption_coefficients': {
            125: 0.30, 250: 0.25, 500: 0.20, 1000: 0.15, 2000: 0.10, 4000: 0.10
        },
        'mounting_type': 'direct',
        'thickness': '1.375"',
        'source': 'Industry Standard'
    },
    'metal_doors': {
        'name': 'Metal Doors',
        'category': 'doors',
        'manufacturer': 'Generic',
        'description': 'Hollow metal doors',
        'absorption_coefficients': {
            125: 0.05, 250: 0.05, 500: 0.05, 1000: 0.05, 2000: 0.05, 4000: 0.05
        },
        'mounting_type': 'direct',
        'thickness': '1.75"',
        'source': 'ASHRAE Handbook'
    },

    # WINDOW MATERIALS
    'glass_window': {
        'name': 'Glass, Window',
        'category': 'windows',
        'manufacturer': 'Generic',
        'description': 'Standard window glass',
        'absorption_coefficients': {
            125: 0.18, 250: 0.06, 500: 0.04, 1000: 0.03, 2000: 0.02, 4000: 0.02
        },
        'mounting_type': 'direct',
        'thickness': '1/4"',
        'source': 'Building Acoustics Handbook'
    },
    'glass_thick': {
        'name': 'Glass, Thick',
        'category': 'windows',
        'manufacturer': 'Generic',
        'description': 'Thick plate glass',
        'absorption_coefficients': {
            125: 0.09, 250: 0.03, 500: 0.02, 1000: 0.02, 2000: 0.03, 4000: 0.02
        },
        'mounting_type': 'direct',
        'thickness': '1/2"',
        'source': 'ASHRAE Handbook'
    },

    # SPECIALTY MATERIALS
    'upholstered_seating': {
        'name': 'Upholstered Seating',
        'category': 'specialty',
        'manufacturer': 'Generic',
        'description': 'Fabric upholstered seating (per unit)',
        'absorption_coefficients': {
            125: 0.60, 250: 0.74, 500: 0.88, 1000: 0.96, 2000: 0.93, 4000: 0.85
        },
        'mounting_type': 'direct',
        'thickness': 'Variable',
        'source': 'ASTM C423 Test Data'
    },
    'audience_fabric': {
        'name': 'Audience (Fabric Seats)',
        'category': 'specialty',
        'manufacturer': 'Generic',
        'description': 'Occupied fabric-upholstered seating per person',
        'absorption_coefficients': {
            125: 0.60, 250: 0.74, 500: 0.88, 1000: 0.96, 2000: 0.93, 4000: 0.85
        },
        'mounting_type': 'direct',
        'thickness': 'Per person',
        'source': 'Industry Standard'
    },
    'air_medium': {
        'name': 'Air (Medium Humidity)',
        'category': 'specialty',
        'manufacturer': 'N/A',
        'description': 'Air absorption coefficient per 1000 cubic feet',
        'absorption_coefficients': {
            125: 0.0, 250: 0.0, 500: 0.0, 1000: 0.9, 2000: 2.8, 4000: 9.3
        },
        'mounting_type': 'N/A',
        'thickness': 'N/A',
        'source': 'ASHRAE Handbook'
    }
}

def calculate_nrc(absorption_coeffs):
    """Calculate NRC (Noise Reduction Coefficient) from frequency coefficients"""
    # NRC is the average of 250, 500, 1000, 2000 Hz coefficients, rounded to nearest 0.05
    if all(freq in absorption_coeffs for freq in [250, 500, 1000, 2000]):
        nrc = (absorption_coeffs[250] + absorption_coeffs[500] + 
               absorption_coeffs[1000] + absorption_coeffs[2000]) / 4
        return round(nrc * 20) / 20  # Round to nearest 0.05
    return 0.0

def get_materials_by_category(category):
    """Get all materials for a specific category"""
    return {key: material for key, material in ENHANCED_MATERIALS.items() 
            if material.get('category') == category}

def get_material_info(material_key):
    """Get complete material information including calculated NRC"""
    if material_key not in ENHANCED_MATERIALS:
        return None
    
    material = ENHANCED_MATERIALS[material_key].copy()
    material['nrc'] = calculate_nrc(material['absorption_coefficients'])
    return material

def search_materials(search_term, category=None):
    """Search materials by name or description"""
    search_term = search_term.lower()
    results = {}
    
    for key, material in ENHANCED_MATERIALS.items():
        if category and material.get('category') != category:
            continue
            
        if (search_term in material['name'].lower() or 
            search_term in material['description'].lower()):
            results[key] = material
    
    return results

def get_room_type_defaults(room_type):
    """Get default room configuration for a room type"""
    return ROOM_TYPE_PRESETS.get(room_type, ROOM_TYPE_PRESETS['custom'])

def get_frequency_bands():
    """Get standard octave band frequencies"""
    return OCTAVE_BANDS.copy()

# Create enhanced materials with calculated NRC values
def create_enhanced_materials_with_nrc():
    """Create materials dictionary with calculated NRC values"""
    enhanced = {}
    for key, material in ENHANCED_MATERIALS.items():
        enhanced[key] = material.copy()
        enhanced[key]['nrc'] = calculate_nrc(material['absorption_coefficients'])
    return enhanced

# Pre-calculate NRC values for all materials
MATERIALS_WITH_NRC = create_enhanced_materials_with_nrc()

# Export the main materials database
__all__ = [
    'ENHANCED_MATERIALS',
    'MATERIALS_WITH_NRC', 
    'SURFACE_CATEGORIES',
    'ROOM_TYPE_PRESETS',
    'OCTAVE_BANDS',
    'calculate_nrc',
    'get_materials_by_category',
    'get_material_info',
    'search_materials',
    'get_room_type_defaults',
    'get_frequency_bands'
]