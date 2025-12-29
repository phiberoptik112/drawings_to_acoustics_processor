"""
Standard STC (Sound Transmission Class) requirements for partition assemblies.

This module provides default minimum STC requirements based on space type adjacencies,
following common acoustic design standards and LEED requirements.

References:
- ANSI/ASA S12.60: Acoustical Performance Criteria for Schools
- LEED v4.1 BD+C: Acoustic Performance Credit
- FGI Guidelines for Healthcare Facilities
- IBC (International Building Code) Section 1207
"""

# Common space types for dropdown menus
SPACE_TYPES = [
    "Office",
    "Open Office",
    "Conference Room",
    "Classroom",
    "Corridor",
    "Lobby",
    "Restroom",
    "Mechanical Room",
    "Storage",
    "Exam Room",
    "Patient Room",
    "Waiting Area",
    "Theater/Auditorium",
    "Music Room",
    "Library",
    "Laboratory",
    "Residential Unit",
    "Hotel Room",
    "Restaurant",
    "Kitchen",
    "Gym/Fitness",
    "Other",
]

# Common building locations
BUILDING_LOCATIONS = [
    "Level 1",
    "Level 2",
    "Level 3",
    "Level 4",
    "Level 5",
    "Basement",
    "Ground Floor",
    "Mezzanine",
    "Penthouse",
    "Roof",
]

# Assembly locations (partition surfaces)
ASSEMBLY_LOCATIONS = [
    "Wall",
    "Floor",
    "Ceiling",
    "Floor/Ceiling",  # For rated floor-ceiling assemblies
]

# Default minimum STC requirements by space type adjacency
# Key: (space_type, adjacent_type) -> minimum STC rating
STC_REQUIREMENTS = {
    # ===================
    # OFFICE BUILDINGS
    # ===================
    
    # Standard offices
    ('office', 'office'): 45,
    ('office', 'corridor'): 40,
    ('office', 'conference room'): 50,
    ('office', 'open office'): 40,
    ('office', 'restroom'): 45,
    ('office', 'mechanical room'): 55,
    
    # Conference rooms (higher privacy needs)
    ('conference room', 'conference room'): 50,
    ('conference room', 'corridor'): 45,
    ('conference room', 'office'): 50,
    ('conference room', 'open office'): 50,
    ('conference room', 'mechanical room'): 55,
    
    # Open office
    ('open office', 'corridor'): 40,
    ('open office', 'mechanical room'): 50,
    
    # ===================
    # EDUCATIONAL
    # ===================
    
    # Standard classrooms (ANSI S12.60 compliant)
    ('classroom', 'classroom'): 50,
    ('classroom', 'corridor'): 45,
    ('classroom', 'mechanical room'): 55,
    ('classroom', 'restroom'): 50,
    ('classroom', 'gym/fitness'): 55,
    ('classroom', 'music room'): 60,
    
    # Music rooms (high isolation needs)
    ('music room', 'music room'): 60,
    ('music room', 'classroom'): 60,
    ('music room', 'corridor'): 55,
    ('music room', 'mechanical room'): 60,
    
    # Libraries
    ('library', 'corridor'): 45,
    ('library', 'classroom'): 50,
    ('library', 'mechanical room'): 55,
    
    # ===================
    # HEALTHCARE
    # ===================
    
    # Patient rooms (FGI Guidelines)
    ('patient room', 'patient room'): 50,
    ('patient room', 'corridor'): 45,
    ('patient room', 'restroom'): 50,
    ('patient room', 'mechanical room'): 55,
    
    # Exam rooms
    ('exam room', 'exam room'): 50,
    ('exam room', 'corridor'): 45,
    ('exam room', 'waiting area'): 50,
    ('exam room', 'restroom'): 50,
    
    # Waiting areas
    ('waiting area', 'corridor'): 40,
    ('waiting area', 'mechanical room'): 50,
    
    # ===================
    # RESIDENTIAL/HOSPITALITY
    # ===================
    
    # Residential units (IBC 1207)
    ('residential unit', 'residential unit'): 50,
    ('residential unit', 'corridor'): 50,
    ('residential unit', 'mechanical room'): 55,
    ('residential unit', 'lobby'): 50,
    
    # Hotel rooms
    ('hotel room', 'hotel room'): 50,
    ('hotel room', 'corridor'): 50,
    ('hotel room', 'mechanical room'): 55,
    ('hotel room', 'lobby'): 50,
    
    # ===================
    # ASSEMBLY/ENTERTAINMENT
    # ===================
    
    # Theaters/Auditoriums
    ('theater/auditorium', 'lobby'): 55,
    ('theater/auditorium', 'corridor'): 55,
    ('theater/auditorium', 'mechanical room'): 60,
    ('theater/auditorium', 'theater/auditorium'): 60,
    
    # ===================
    # SERVICE SPACES
    # ===================
    
    # Restrooms
    ('restroom', 'corridor'): 45,
    ('restroom', 'office'): 45,
    
    # Mechanical rooms (high noise sources)
    ('mechanical room', 'corridor'): 50,
    ('mechanical room', 'office'): 55,
    
    # Kitchens/Food service
    ('kitchen', 'restaurant'): 45,
    ('kitchen', 'corridor'): 45,
    ('kitchen', 'office'): 50,
    
    # ===================
    # GENERAL DEFAULTS
    # ===================
    ('default', 'default'): 45,
    ('default', 'corridor'): 40,
    ('default', 'mechanical room'): 50,
    ('default', 'restroom'): 45,
}

# IIC (Impact Insulation Class) requirements for floor/ceiling assemblies
IIC_REQUIREMENTS = {
    # Residential
    ('residential unit', 'residential unit'): 50,  # IBC minimum
    ('hotel room', 'hotel room'): 50,
    
    # Healthcare
    ('patient room', 'patient room'): 50,
    
    # Educational
    ('classroom', 'classroom'): 45,
    
    # Default
    ('default', 'default'): 45,
}


def get_minimum_stc(space_type: str, adjacent_type: str) -> int:
    """
    Get recommended minimum STC rating for a space-to-adjacent-space adjacency.
    
    Args:
        space_type: Type of the primary space (e.g., "Classroom")
        adjacent_type: Type of the adjacent space (e.g., "Corridor")
    
    Returns:
        Minimum recommended STC rating (integer)
    
    Examples:
        >>> get_minimum_stc("Classroom", "Corridor")
        45
        >>> get_minimum_stc("Conference Room", "Office")
        50
    """
    # Normalize to lowercase
    space_lower = space_type.lower().strip() if space_type else 'default'
    adjacent_lower = adjacent_type.lower().strip() if adjacent_type else 'default'
    
    # Try exact match first
    key = (space_lower, adjacent_lower)
    if key in STC_REQUIREMENTS:
        return STC_REQUIREMENTS[key]
    
    # Try reverse match (space types are often symmetric)
    reverse_key = (adjacent_lower, space_lower)
    if reverse_key in STC_REQUIREMENTS:
        return STC_REQUIREMENTS[reverse_key]
    
    # Try with space_type as default
    default_key = ('default', adjacent_lower)
    if default_key in STC_REQUIREMENTS:
        return STC_REQUIREMENTS[default_key]
    
    # Try with adjacent_type as default
    default_key = (space_lower, 'default')
    if default_key in STC_REQUIREMENTS:
        return STC_REQUIREMENTS[default_key]
    
    # Final fallback to default-default
    return STC_REQUIREMENTS.get(('default', 'default'), 45)


def get_minimum_iic(space_type: str, adjacent_type: str) -> int:
    """
    Get recommended minimum IIC rating for floor/ceiling assemblies.
    
    Args:
        space_type: Type of the upper space
        adjacent_type: Type of the lower space
    
    Returns:
        Minimum recommended IIC rating (integer)
    """
    space_lower = space_type.lower().strip() if space_type else 'default'
    adjacent_lower = adjacent_type.lower().strip() if adjacent_type else 'default'
    
    key = (space_lower, adjacent_lower)
    if key in IIC_REQUIREMENTS:
        return IIC_REQUIREMENTS[key]
    
    reverse_key = (adjacent_lower, space_lower)
    if reverse_key in IIC_REQUIREMENTS:
        return IIC_REQUIREMENTS[reverse_key]
    
    return IIC_REQUIREMENTS.get(('default', 'default'), 45)


def get_stc_requirement_info(space_type: str, adjacent_type: str) -> dict:
    """
    Get detailed STC requirement information including source reference.
    
    Args:
        space_type: Type of the primary space
        adjacent_type: Type of the adjacent space
    
    Returns:
        Dictionary with 'stc', 'source', and 'notes' keys
    """
    stc = get_minimum_stc(space_type, adjacent_type)
    
    space_lower = space_type.lower().strip() if space_type else ''
    adjacent_lower = adjacent_type.lower().strip() if adjacent_type else ''
    
    # Determine source reference
    if 'classroom' in space_lower or 'classroom' in adjacent_lower:
        source = "ANSI/ASA S12.60"
        notes = "Acoustical Performance Criteria for Schools"
    elif any(t in space_lower or t in adjacent_lower 
             for t in ['patient', 'exam', 'waiting']):
        source = "FGI Guidelines"
        notes = "Guidelines for Design and Construction of Healthcare Facilities"
    elif any(t in space_lower or t in adjacent_lower 
             for t in ['residential', 'hotel']):
        source = "IBC Section 1207"
        notes = "International Building Code - Sound Transmission"
    elif stc >= 55:
        source = "LEED v4.1 BD+C"
        notes = "Enhanced acoustic performance recommendation"
    else:
        source = "Industry Standard"
        notes = "Common acoustic design practice"
    
    return {
        'stc': stc,
        'source': source,
        'notes': notes
    }


def validate_stc_compliance(actual_stc: int, required_stc: int) -> dict:
    """
    Validate if an actual STC rating meets the required minimum.
    
    Args:
        actual_stc: Actual STC rating of the assembly
        required_stc: Minimum required STC rating
    
    Returns:
        Dictionary with compliance status and margin
    """
    if actual_stc is None or required_stc is None:
        return {
            'compliant': None,
            'margin': None,
            'status': 'N/A',
            'message': 'Missing STC data'
        }
    
    margin = actual_stc - required_stc
    compliant = margin >= 0
    
    if margin >= 5:
        status = 'Exceeds'
        message = f'Exceeds requirement by {margin} points'
    elif margin >= 0:
        status = 'Meets'
        message = f'Meets requirement (margin: {margin} points)'
    else:
        status = 'Below'
        message = f'Below requirement by {abs(margin)} points'
    
    return {
        'compliant': compliant,
        'margin': margin,
        'status': status,
        'message': message
    }

