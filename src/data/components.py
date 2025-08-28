"""
Standard HVAC component library for acoustic analysis
"""

# Standard HVAC Components with typical noise levels and CFM values
STANDARD_COMPONENTS = {
    'ahu': {
        'name': 'Air Handling Unit',
        'noise_level': 65.0,  # dB(A)
        'cfm': 5000.0,  # Typical CFM
        'cfm_range': (500, 50000),  # (min, max) CFM range
        'description': 'Central air handling unit with fan'
    },
    'vav': {
        'name': 'VAV Box',
        'noise_level': 45.0,
        'cfm': 500.0,
        'cfm_range': (50, 2000),
        'description': 'Variable air volume terminal box'
    },
    'diffuser': {
        'name': 'Ceiling Diffuser',
        'noise_level': 30.0,
        'cfm': 150.0,
        'cfm_range': (25, 500),
        'description': 'Supply air diffuser'
    },
    'grille': {
        'name': 'Return Grille',
        'noise_level': 25.0,
        'cfm': 200.0,
        'cfm_range': (50, 1000),
        'description': 'Return air grille'
    },
    'fan': {
        'name': 'Exhaust Fan',
        'noise_level': 55.0,
        'cfm': 2000.0,
        'cfm_range': (100, 20000),
        'description': 'Centrifugal exhaust fan'
    },
    'silencer': {
        'name': 'Duct Silencer',
        'noise_level': -15.0,  # Negative = attenuation
        'cfm': 1000.0,
        'cfm_range': (100, 10000),
        'description': 'Acoustic duct silencer'
    },
    'damper': {
        'name': 'Volume Damper',
        'noise_level': 5.0,
        'cfm': 100.0,
        'cfm_range': (10, 5000),
        'description': 'Manual volume damper'
    },
    'coil': {
        'name': 'Heating/Cooling Coil',
        'noise_level': 35.0,
        'cfm': 800.0,
        'cfm_range': (100, 5000),
        'description': 'Heat exchanger coil'
    },
    'elbow': {
        'name': 'Duct Elbow',
        'noise_level': 2.0,  # Low noise, mainly for direction change
        'cfm': 100.0,
        'cfm_range': (10, 10000),
        'description': 'Ductwork elbow for direction changes'
    },
    'branch': {
        'name': 'Duct Branch',
        'noise_level': 3.0,  # Slightly higher noise due to flow splitting
        'cfm': 300.0,
        'cfm_range': (50, 5000),
        'description': 'Ductwork branch for flow distribution'
    }
}

# Standard duct fittings and their typical noise additions
STANDARD_FITTINGS = {
    'elbow_90': {
        'name': '90° Elbow',
        'noise_adjustment': 3.0,  # dB addition
        'description': '90 degree ductwork elbow'
    },
    'elbow_45': {
        'name': '45° Elbow',
        'noise_adjustment': 2.0,
        'description': '45 degree ductwork elbow'
    },
    'tee_branch': {
        'name': 'Tee Branch',
        'noise_adjustment': 2.0,
        'description': 'Ductwork tee junction'
    },
    'tee_straight': {
        'name': 'Tee Straight',
        'noise_adjustment': 1.0,
        'description': 'Straight through tee junction'
    },
    'reducer': {
        'name': 'Duct Reducer',
        'noise_adjustment': 1.5,
        'description': 'Duct size transition'
    },
    'fire_damper': {
        'name': 'Fire Damper',
        'noise_adjustment': 2.0,
        'description': 'Fire safety damper'
    },
    'balancing_damper': {
        'name': 'Balancing Damper',
        'noise_adjustment': 1.0,
        'description': 'Airflow balancing damper'
    }
}

# Standard duct sizes (rectangular: width x height in inches)
STANDARD_DUCT_SIZES = [
    "6x4", "8x4", "8x6", "10x4", "10x6", "10x8",
    "12x4", "12x6", "12x8", "12x10", "14x6", "14x8", "14x10",
    "16x6", "16x8", "16x10", "16x12", "18x8", "18x10", "18x12",
    "20x8", "20x10", "20x12", "20x14", "22x10", "22x12", "22x14",
    "24x10", "24x12", "24x14", "24x16", "26x12", "26x14", "26x16",
    "28x12", "28x14", "28x16", "30x14", "30x16", "30x18"
]

# Round duct sizes (diameter in inches)
STANDARD_ROUND_DUCT_SIZES = [
    "4", "5", "6", "7", "8", "9", "10", "12", "14", "16", "18", "20", "22", "24"
]