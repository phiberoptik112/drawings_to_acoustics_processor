"""
RT60 Calculator - Reverberation time calculation engine using Sabine and Eyring formulas
"""

import math
from data import STANDARD_MATERIALS


class RT60Calculator:
    """Calculator for reverberation time (RT60) using acoustic absorption"""
    
    def __init__(self):
        self.materials_db = STANDARD_MATERIALS
        
    def calculate_surface_absorption(self, area, material_key):
        """Calculate absorption for a surface"""
        if material_key not in self.materials_db:
            return 0.0
            
        material = self.materials_db[material_key]
        absorption_coeff = material['absorption_coeff']
        
        return area * absorption_coeff
        
    def calculate_total_absorption(self, surfaces):
        """
        Calculate total absorption from multiple surfaces
        
        Args:
            surfaces: List of dicts with 'area' and 'material_key'
        
        Returns:
            float: Total absorption in sabins
        """
        total_absorption = 0.0
        
        for surface in surfaces:
            area = surface.get('area', 0)
            material_key = surface.get('material_key')
            
            if area > 0 and material_key:
                absorption = self.calculate_surface_absorption(area, material_key)
                total_absorption += absorption
                
        return total_absorption
        
    def calculate_rt60_sabine(self, volume, total_absorption):
        """
        Calculate RT60 using Sabine formula
        
        RT60 = 0.161 * V / A
        where V = volume (cubic feet), A = total absorption (sabins)
        
        Args:
            volume: Room volume in cubic feet
            total_absorption: Total absorption in sabins
            
        Returns:
            float: RT60 in seconds
        """
        if total_absorption <= 0:
            return float('inf')  # Infinite reverberation
            
        return 0.161 * volume / total_absorption
        
    def calculate_rt60_eyring(self, volume, surfaces):
        """
        Calculate RT60 using Eyring formula (more accurate for high absorption)
        
        RT60 = 0.161 * V / (-S * ln(1 - α_avg))
        where α_avg is the average absorption coefficient
        
        Args:
            volume: Room volume in cubic feet
            surfaces: List of surface dicts with area and material_key
            
        Returns:
            float: RT60 in seconds
        """
        total_area = 0.0
        weighted_absorption = 0.0
        
        for surface in surfaces:
            area = surface.get('area', 0)
            material_key = surface.get('material_key')
            
            if area > 0 and material_key and material_key in self.materials_db:
                absorption_coeff = self.materials_db[material_key]['absorption_coeff']
                total_area += area
                weighted_absorption += area * absorption_coeff
                
        if total_area <= 0:
            return float('inf')
            
        avg_absorption_coeff = weighted_absorption / total_area
        
        # Avoid log(0) or log(negative)
        if avg_absorption_coeff >= 1.0:
            avg_absorption_coeff = 0.99
        elif avg_absorption_coeff <= 0:
            return float('inf')
            
        try:
            denominator = -total_area * math.log(1 - avg_absorption_coeff)
            if denominator <= 0:
                return float('inf')
                
            return 0.161 * volume / denominator
        except (ValueError, ZeroDivisionError):
            return float('inf')
            
    def calculate_space_rt60(self, space_data, method='sabine'):
        """
        Calculate RT60 for a space
        
        Args:
            space_data: Dict with volume, areas, and materials
            method: 'sabine' or 'eyring'
            
        Returns:
            dict: Calculation results
        """
        # Extract space properties
        volume = space_data.get('volume', 0)
        floor_area = space_data.get('floor_area', 0)
        wall_area = space_data.get('wall_area', 0)
        ceiling_area = space_data.get('ceiling_area', floor_area)  # Default to floor area
        
        ceiling_material = space_data.get('ceiling_material')
        wall_material = space_data.get('wall_material')
        floor_material = space_data.get('floor_material')
        
        if volume <= 0:
            return {
                'rt60': 0,
                'method': method,
                'error': 'Invalid volume'
            }
            
        # Prepare surfaces for calculation
        surfaces = []
        
        if ceiling_area > 0 and ceiling_material:
            surfaces.append({
                'area': ceiling_area,
                'material_key': ceiling_material,
                'type': 'ceiling'
            })
            
        if wall_area > 0 and wall_material:
            surfaces.append({
                'area': wall_area,
                'material_key': wall_material,
                'type': 'wall'
            })
            
        if floor_area > 0 and floor_material:
            surfaces.append({
                'area': floor_area,
                'material_key': floor_material,
                'type': 'floor'
            })
            
        if not surfaces:
            return {
                'rt60': 0,
                'method': method,
                'error': 'No valid surfaces defined'
            }
            
        # Calculate RT60
        if method.lower() == 'eyring':
            rt60 = self.calculate_rt60_eyring(volume, surfaces)
        else:
            total_absorption = self.calculate_total_absorption(surfaces)
            rt60 = self.calculate_rt60_sabine(volume, total_absorption)
            
        # Prepare detailed results
        results = {
            'rt60': rt60 if rt60 != float('inf') else 999.9,
            'method': method,
            'volume': volume,
            'surfaces': [],
            'total_area': 0,
            'total_absorption': 0,
            'avg_absorption_coeff': 0
        }
        
        # Calculate surface details
        total_area = 0
        total_absorption = 0
        
        for surface in surfaces:
            area = surface['area']
            material_key = surface['material_key']
            surface_type = surface['type']
            
            if material_key in self.materials_db:
                material = self.materials_db[material_key]
                absorption_coeff = material['absorption_coeff']
                absorption = area * absorption_coeff
                
                results['surfaces'].append({
                    'type': surface_type,
                    'area': area,
                    'material_name': material['name'],
                    'material_key': material_key,
                    'absorption_coeff': absorption_coeff,
                    'absorption': absorption
                })
                
                total_area += area
                total_absorption += absorption
                
        results['total_area'] = total_area
        results['total_absorption'] = total_absorption
        
        if total_area > 0:
            results['avg_absorption_coeff'] = total_absorption / total_area
            
        return results
        
    def get_material_info(self, material_key):
        """Get material information"""
        if material_key in self.materials_db:
            return self.materials_db[material_key].copy()
        return None
        
    def suggest_materials_for_target(self, current_rt60, target_rt60, volume, surfaces):
        """
        Suggest material changes to achieve target RT60
        
        Args:
            current_rt60: Current calculated RT60
            target_rt60: Desired RT60
            volume: Room volume
            surfaces: Current surface configuration
            
        Returns:
            dict: Suggestions for material changes
        """
        if current_rt60 <= 0 or target_rt60 <= 0:
            return {'error': 'Invalid RT60 values'}
            
        # Calculate required total absorption for target RT60
        required_absorption = 0.161 * volume / target_rt60
        current_absorption = self.calculate_total_absorption(surfaces)
        
        absorption_needed = required_absorption - current_absorption
        
        suggestions = {
            'current_rt60': current_rt60,
            'target_rt60': target_rt60,
            'current_absorption': current_absorption,
            'required_absorption': required_absorption,
            'additional_absorption_needed': absorption_needed,
            'recommendations': []
        }
        
        if abs(current_rt60 - target_rt60) <= 0.1:
            suggestions['recommendations'].append({
                'type': 'status',
                'message': 'Current RT60 is within acceptable range of target'
            })
        elif current_rt60 > target_rt60:
            # Need more absorption
            suggestions['recommendations'].append({
                'type': 'increase_absorption',
                'message': f'RT60 is too high. Need {absorption_needed:.1f} more sabins of absorption.',
                'suggestion': 'Consider more absorptive materials (higher α values)'
            })
        else:
            # Need less absorption
            suggestions['recommendations'].append({
                'type': 'decrease_absorption',
                'message': f'RT60 is too low. Need {abs(absorption_needed):.1f} less sabins of absorption.',
                'suggestion': 'Consider more reflective materials (lower α values)'
            })
            
        return suggestions
        
    def format_rt60_report(self, results):
        """Format RT60 calculation results as a readable report"""
        if 'error' in results:
            return f"Calculation Error: {results['error']}"
            
        rt60 = results['rt60']
        method = results['method'].title()
        volume = results['volume']
        
        report = f"RT60 Calculation Report ({method} Method)\n"
        report += "=" * 50 + "\n\n"
        
        report += f"Room Volume: {volume:,.0f} cubic feet\n"
        report += f"Calculated RT60: {rt60:.2f} seconds\n\n"
        
        report += "Surface Analysis:\n"
        report += "-" * 20 + "\n"
        
        for surface in results['surfaces']:
            report += f"{surface['type'].title()}: {surface['area']:.0f} sf\n"
            report += f"  Material: {surface['material_name']}\n"
            report += f"  Absorption Coeff: {surface['absorption_coeff']:.2f}\n"
            report += f"  Absorption: {surface['absorption']:.1f} sabins\n\n"
            
        report += f"Total Surface Area: {results['total_area']:.0f} sf\n"
        report += f"Total Absorption: {results['total_absorption']:.1f} sabins\n"
        report += f"Average Absorption Coeff: {results['avg_absorption_coeff']:.3f}\n"
        
        return report


# Convenience functions for common calculations
def calculate_simple_rt60(volume, floor_area, ceiling_height, materials):
    """
    Simple RT60 calculation for rectangular rooms
    
    Args:
        volume: Room volume in cubic feet
        floor_area: Floor area in square feet
        ceiling_height: Ceiling height in feet
        materials: Dict with 'ceiling', 'wall', 'floor' material keys
        
    Returns:
        dict: RT60 calculation results
    """
    calculator = RT60Calculator()
    
    # Calculate wall area (simplified as perimeter × height)
    # This assumes a square room for simplicity
    perimeter = 4 * math.sqrt(floor_area)  # Approximate perimeter
    wall_area = perimeter * ceiling_height
    
    space_data = {
        'volume': volume,
        'floor_area': floor_area,
        'wall_area': wall_area,
        'ceiling_area': floor_area,
        'ceiling_material': materials.get('ceiling'),
        'wall_material': materials.get('wall'),
        'floor_material': materials.get('floor')
    }
    
    return calculator.calculate_space_rt60(space_data)


def get_material_absorption_coeff(material_key):
    """Get absorption coefficient for a material"""
    if material_key in STANDARD_MATERIALS:
        return STANDARD_MATERIALS[material_key]['absorption_coeff']
    return 0.0