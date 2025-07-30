"""
Surface Area Calculator - Automatic area calculation with manual override capabilities
"""

import math
from typing import Dict, List, Optional, Tuple


class SurfaceAreaCalculator:
    """Calculator for automatic surface area calculations with manual override support"""
    
    def __init__(self, space):
        """
        Initialize calculator for a specific space
        
        Args:
            space: Space model instance with geometry data
        """
        self.space = space
        self.floor_area = space.floor_area or 0.0
        self.ceiling_height = space.ceiling_height or 9.0
        self.perimeter = space.calculate_perimeter()
        
    def calculate_basic_surfaces(self) -> Dict[str, float]:
        """
        Calculate areas for basic surface types
        
        Returns:
            Dict with surface type keys and calculated areas
        """
        areas = {}
        
        # Floor and ceiling areas (same as floor area)
        areas['floor'] = self.floor_area
        areas['ceiling'] = self.floor_area
        
        # Total wall area (perimeter × height)
        total_wall_area = self.perimeter * self.ceiling_height
        areas['total_walls'] = total_wall_area
        
        # Room volume
        areas['volume'] = self.floor_area * self.ceiling_height
        
        return areas
    
    def estimate_surface_areas_by_type(self, surface_type_name: str, instance_number: int = 1) -> float:
        """
        Estimate area for specific surface type and instance
        
        Args:
            surface_type_name: Name of surface type (e.g., 'Primary Wall', 'Secondary Wall')
            instance_number: Instance number for multiple instances of same type
            
        Returns:
            Estimated area in square feet
        """
        basic_areas = self.calculate_basic_surfaces()
        surface_name_lower = surface_type_name.lower()
        
        # Floor surfaces
        if 'floor' in surface_name_lower:
            return basic_areas['floor']
            
        # Ceiling surfaces
        elif 'ceiling' in surface_name_lower:
            return basic_areas['ceiling']
            
        # Wall surfaces - distribute total wall area
        elif 'wall' in surface_name_lower:
            if 'primary' in surface_name_lower:
                # Primary walls get larger share (assume 2 primary walls)
                return basic_areas['total_walls'] * 0.6  # 60% for primary walls
            elif 'secondary' in surface_name_lower:
                # Secondary walls get smaller share
                return basic_areas['total_walls'] * 0.3  # 30% for secondary walls
            elif 'accent' in surface_name_lower:
                # Accent walls are typically smaller
                return basic_areas['total_walls'] * 0.1  # 10% for accent walls
            else:
                # Generic wall - assume equal distribution among 4 walls
                return basic_areas['total_walls'] / 4
                
        # Door surfaces - estimate standard door sizes
        elif 'door' in surface_name_lower:
            if 'entry' in surface_name_lower or 'exterior' in surface_name_lower:
                return 21.0  # 3' × 7' = 21 sf
            else:
                return 18.67  # 2'8" × 7' = ~18.67 sf
                
        # Window surfaces - estimate based on room size
        elif 'window' in surface_name_lower or 'glazed' in surface_name_lower:
            # Estimate 15% of floor area as window area (typical office building)
            return self.floor_area * 0.15
            
        # Specialty surfaces require manual input
        else:
            return 0.0
    
    def calculate_wall_distribution(self, num_primary: int = 2, num_secondary: int = 2, 
                                  num_accent: int = 0) -> Dict[str, float]:
        """
        Calculate wall area distribution among different wall types
        
        Args:
            num_primary: Number of primary wall instances
            num_secondary: Number of secondary wall instances  
            num_accent: Number of accent wall instances
            
        Returns:
            Dict with wall type distribution
        """
        total_wall_area = self.perimeter * self.ceiling_height
        total_instances = num_primary + num_secondary + num_accent
        
        if total_instances == 0:
            return {'primary': 0, 'secondary': 0, 'accent': 0}
        
        # Calculate weights (primary walls typically larger)
        primary_weight = 1.5  # Primary walls get 50% more area
        secondary_weight = 1.0
        accent_weight = 0.5   # Accent walls typically smaller
        
        total_weight = (num_primary * primary_weight + 
                       num_secondary * secondary_weight + 
                       num_accent * accent_weight)
        
        return {
            'primary': (total_wall_area * primary_weight * num_primary / total_weight) / num_primary if num_primary > 0 else 0,
            'secondary': (total_wall_area * secondary_weight * num_secondary / total_weight) / num_secondary if num_secondary > 0 else 0,
            'accent': (total_wall_area * accent_weight * num_accent / total_weight) / num_accent if num_accent > 0 else 0
        }
    
    def get_calculated_area_for_instance(self, surface_type, instance_number: int = 1) -> float:
        """
        Get calculated area for a specific surface instance
        
        Args:
            surface_type: SurfaceType model instance
            instance_number: Instance number for this surface type
            
        Returns:
            Calculated area in square feet
        """
        if not surface_type:
            return 0.0
            
        surface_name = surface_type.name
        calculation_method = surface_type.default_calculation_method
        
        # Use different calculation methods based on surface type
        if calculation_method == 'perimeter_height':
            return self.estimate_surface_areas_by_type(surface_name, instance_number)
        elif calculation_method == 'floor_area':
            return self.floor_area
        elif calculation_method == 'percentage':
            # Custom percentage-based calculation
            return self._calculate_percentage_area(surface_type, instance_number)
        else:
            # Manual calculation required
            return 0.0
    
    def _calculate_percentage_area(self, surface_type, instance_number: int) -> float:
        """
        Calculate area based on percentage of total room surfaces
        
        Args:
            surface_type: SurfaceType model instance
            instance_number: Instance number
            
        Returns:
            Calculated area based on percentage
        """
        # This could be expanded with surface-type-specific percentage rules
        surface_name_lower = surface_type.name.lower()
        
        if 'treatment' in surface_name_lower or 'acoustic' in surface_name_lower:
            # Acoustic treatments typically cover 20-40% of wall area
            total_wall_area = self.perimeter * self.ceiling_height
            return total_wall_area * 0.3  # 30% coverage
        elif 'cloud' in surface_name_lower or 'baffle' in surface_name_lower:
            # Ceiling clouds typically cover 40-60% of ceiling area
            return self.floor_area * 0.5  # 50% coverage
        else:
            return 0.0
    
    def validate_area_calculation(self, calculated_area: float, surface_type_name: str) -> Tuple[bool, str]:
        """
        Validate calculated area for reasonableness
        
        Args:
            calculated_area: Calculated area value
            surface_type_name: Name of surface type
            
        Returns:
            Tuple of (is_valid, warning_message)
        """
        surface_name_lower = surface_type_name.lower()
        warnings = []
        
        # Check for negative or zero areas
        if calculated_area <= 0:
            return False, "Calculated area must be greater than zero"
        
        # Check against room geometry limits
        total_surface_area = 2 * self.floor_area + (self.perimeter * self.ceiling_height)
        
        if calculated_area > total_surface_area:
            warnings.append(f"Area ({calculated_area:.0f} sf) exceeds total room surface area ({total_surface_area:.0f} sf)")
        
        # Surface-specific validations
        if 'floor' in surface_name_lower or 'ceiling' in surface_name_lower:
            if calculated_area > self.floor_area * 1.1:  # Allow 10% tolerance
                warnings.append(f"Floor/ceiling area seems too large compared to room floor area ({self.floor_area:.0f} sf)")
        
        elif 'wall' in surface_name_lower:
            total_wall_area = self.perimeter * self.ceiling_height
            if calculated_area > total_wall_area * 0.8:  # Single wall shouldn't exceed 80% of total
                warnings.append(f"Wall area seems too large compared to total wall area ({total_wall_area:.0f} sf)")
        
        elif 'door' in surface_name_lower:
            if calculated_area > 50:  # Typical door max ~35 sf
                warnings.append("Door area seems unusually large (typical doors: 18-35 sf)")
            elif calculated_area < 10:
                warnings.append("Door area seems unusually small (typical doors: 18-35 sf)")
        
        elif 'window' in surface_name_lower:
            max_window_area = self.floor_area * 0.5  # 50% of floor area is very high
            if calculated_area > max_window_area:
                warnings.append(f"Window area seems very large compared to room size")
        
        if warnings:
            return True, "; ".join(warnings)  # Valid but with warnings
        
        return True, ""
    
    def get_area_calculation_notes(self, surface_type_name: str, calculated_area: float) -> str:
        """
        Generate explanatory notes for area calculation
        
        Args:
            surface_type_name: Name of surface type
            calculated_area: Calculated area
            
        Returns:
            Explanatory text for the calculation
        """
        surface_name_lower = surface_type_name.lower()
        
        if 'floor' in surface_name_lower:
            return f"Floor area from room geometry: {self.floor_area:.0f} sf"
        elif 'ceiling' in surface_name_lower:
            return f"Ceiling area equals floor area: {self.floor_area:.0f} sf"
        elif 'wall' in surface_name_lower:
            total_wall_area = self.perimeter * self.ceiling_height
            percentage = (calculated_area / total_wall_area * 100) if total_wall_area > 0 else 0
            return f"Wall area: {calculated_area:.0f} sf ({percentage:.0f}% of total wall area {total_wall_area:.0f} sf)"
        elif 'door' in surface_name_lower:
            return f"Estimated door area: {calculated_area:.0f} sf (standard door size)"
        elif 'window' in surface_name_lower:
            percentage = (calculated_area / self.floor_area * 100) if self.floor_area > 0 else 0
            return f"Estimated window area: {calculated_area:.0f} sf ({percentage:.0f}% of floor area)"
        else:
            return f"Calculated area: {calculated_area:.0f} sf"
    
    def suggest_surface_instances(self) -> List[Dict[str, any]]:
        """
        Suggest typical surface instances for this room
        
        Returns:
            List of suggested surface configurations
        """
        suggestions = []
        
        # Basic surfaces that every room should have
        suggestions.extend([
            {
                'surface_type': 'Primary Ceiling',
                'category': 'ceilings',
                'instances': 1,
                'area_per_instance': self.floor_area,
                'calculation_method': 'floor_area',
                'priority': 'required'
            },
            {
                'surface_type': 'Floor Surface', 
                'category': 'floors',
                'instances': 1,
                'area_per_instance': self.floor_area,
                'calculation_method': 'floor_area',
                'priority': 'required'
            }
        ])
        
        # Wall suggestions based on room size
        if self.floor_area < 150:  # Small room
            suggestions.append({
                'surface_type': 'Primary Wall',
                'category': 'walls', 
                'instances': 4,
                'area_per_instance': (self.perimeter * self.ceiling_height) / 4,
                'calculation_method': 'perimeter_height',
                'priority': 'recommended'
            })
        else:  # Larger room - separate primary/secondary
            wall_dist = self.calculate_wall_distribution(2, 2, 0)
            suggestions.extend([
                {
                    'surface_type': 'Primary Wall',
                    'category': 'walls',
                    'instances': 2, 
                    'area_per_instance': wall_dist['primary'],
                    'calculation_method': 'perimeter_height',
                    'priority': 'recommended'
                },
                {
                    'surface_type': 'Secondary Wall',
                    'category': 'walls',
                    'instances': 2,
                    'area_per_instance': wall_dist['secondary'], 
                    'calculation_method': 'perimeter_height',
                    'priority': 'recommended'
                }
            ])
        
        # Optional surfaces based on room size/type
        if self.floor_area > 200:  # Larger rooms likely have doors/windows
            suggestions.extend([
                {
                    'surface_type': 'Entry Doors',
                    'category': 'doors',
                    'instances': 1,
                    'area_per_instance': 21,  # 3' × 7'
                    'calculation_method': 'manual',
                    'priority': 'optional'
                },
                {
                    'surface_type': 'Windows',
                    'category': 'windows', 
                    'instances': 1,
                    'area_per_instance': self.floor_area * 0.15,
                    'calculation_method': 'percentage',
                    'priority': 'optional'
                }
            ])
        
        return suggestions
    
    def update_space_geometry(self, floor_area: float = None, ceiling_height: float = None):
        """
        Update space geometry and recalculate dependent values
        
        Args:
            floor_area: New floor area in square feet
            ceiling_height: New ceiling height in feet
        """
        if floor_area is not None:
            self.floor_area = floor_area
            if self.space:
                self.space.floor_area = floor_area
        
        if ceiling_height is not None:
            self.ceiling_height = ceiling_height
            if self.space:
                self.space.ceiling_height = ceiling_height
        
        # Recalculate dependent geometry
        if self.space:
            self.space.calculate_volume()
            self.perimeter = self.space.calculate_perimeter()
    
    def get_geometry_summary(self) -> Dict[str, any]:
        """
        Get summary of room geometry for UI display
        
        Returns:
            Dictionary with geometry information
        """
        basic_areas = self.calculate_basic_surfaces()
        
        return {
            'floor_area': self.floor_area,
            'ceiling_height': self.ceiling_height,
            'volume': basic_areas['volume'],
            'perimeter': self.perimeter,
            'total_wall_area': basic_areas['total_walls'],
            'total_surface_area': basic_areas['floor'] + basic_areas['ceiling'] + basic_areas['total_walls'],
            'wall_to_floor_ratio': basic_areas['total_walls'] / self.floor_area if self.floor_area > 0 else 0,
            'volume_to_area_ratio': basic_areas['volume'] / (basic_areas['floor'] + basic_areas['ceiling'] + basic_areas['total_walls']) if (basic_areas['floor'] + basic_areas['ceiling'] + basic_areas['total_walls']) > 0 else 0
        }


def create_surface_area_calculator(space) -> SurfaceAreaCalculator:
    """
    Factory function to create a SurfaceAreaCalculator instance
    
    Args:
        space: Space model instance
        
    Returns:
        SurfaceAreaCalculator instance
    """
    return SurfaceAreaCalculator(space)


def estimate_room_surface_area(floor_area: float, ceiling_height: float, 
                              perimeter: float = None) -> Dict[str, float]:
    """
    Standalone function to estimate surface areas for a room
    
    Args:
        floor_area: Floor area in square feet
        ceiling_height: Ceiling height in feet
        perimeter: Room perimeter in feet (estimated if not provided)
        
    Returns:
        Dictionary with estimated surface areas
    """
    if perimeter is None:
        # Estimate perimeter assuming square room
        perimeter = 4 * math.sqrt(floor_area)
    
    return {
        'floor_area': floor_area,
        'ceiling_area': floor_area,
        'wall_area': perimeter * ceiling_height,
        'total_area': floor_area * 2 + perimeter * ceiling_height,
        'volume': floor_area * ceiling_height,
        'perimeter': perimeter
    }