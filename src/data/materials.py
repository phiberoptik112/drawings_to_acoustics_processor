"""
Standard acoustic materials library for RT60 calculations
"""

# Standard acoustic materials with absorption coefficients
# Values are typical mid-frequency (500-1000 Hz) coefficients
STANDARD_MATERIALS = {
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

# Room type defaults for quick setup
ROOM_TYPE_DEFAULTS = {
    'office': {
        'name': 'Office',
        'target_rt60': 0.6,
        'ceiling_material': 'act_standard',
        'wall_material': 'drywall_painted',
        'floor_material': 'carpet_medium'
    },
    'conference': {
        'name': 'Conference Room',
        'target_rt60': 0.8,
        'ceiling_material': 'act_high_performance',
        'wall_material': 'drywall_fabric',
        'floor_material': 'carpet_heavy'
    },
    'classroom': {
        'name': 'Classroom',
        'target_rt60': 0.6,
        'ceiling_material': 'act_standard',
        'wall_material': 'drywall_painted',
        'floor_material': 'carpet_tile'
    },
    'auditorium': {
        'name': 'Auditorium',
        'target_rt60': 1.5,
        'ceiling_material': 'gypsum_ceiling',
        'wall_material': 'acoustic_panels',
        'floor_material': 'carpet_heavy'
    },
    'lobby': {
        'name': 'Lobby',
        'target_rt60': 1.2,
        'ceiling_material': 'act_standard',
        'wall_material': 'drywall_painted',
        'floor_material': 'ceramic_tile'
    },
    'corridor': {
        'name': 'Corridor',
        'target_rt60': 1.0,
        'ceiling_material': 'act_standard',
        'wall_material': 'drywall_painted',
        'floor_material': 'vinyl_tile'
    }
}