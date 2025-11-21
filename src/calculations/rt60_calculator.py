"""
RT60 Calculator - Reverberation time calculation engine using Sabine and Eyring formulas
"""

import math
try:
    from ..data.materials import STANDARD_MATERIALS
except ImportError:
    try:
        from data.materials import STANDARD_MATERIALS
    except ImportError:
        import sys
        import os
        # Add src directory to path for testing
        current_dir = os.path.dirname(__file__)
        src_dir = os.path.dirname(current_dir)
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from data.materials import STANDARD_MATERIALS


class RT60Calculator:
    """Calculator for reverberation time (RT60) using acoustic absorption"""
    
    def __init__(self):
        # Use get_all_materials() to ensure we have the latest materials from all sources
        self.refresh_materials_db()
    
    def refresh_materials_db(self):
        """Refresh the materials database to get latest materials"""
        try:
            from ..data.materials_database import get_all_materials
            self.materials_db = get_all_materials()
        except ImportError:
            try:
                from data.materials_database import get_all_materials
                self.materials_db = get_all_materials()
            except ImportError:
                # Fallback to STANDARD_MATERIALS
                self.materials_db = STANDARD_MATERIALS
        
    def _find_material_by_key_or_name(self, material_key):
        """Find material by key or by name if key doesn't match"""
        if not material_key:
            return None
        
        # First try exact key match
        if material_key in self.materials_db:
            return material_key
        
        # Try to find by name (case-insensitive)
        material_key_lower = material_key.lower()
        for key, material in self.materials_db.items():
            if material.get('name', '').lower() == material_key_lower:
                return key
        
        # Try partial name match
        for key, material in self.materials_db.items():
            if material_key_lower in material.get('name', '').lower():
                return key
        
        return None
    
    def calculate_surface_absorption(self, area, material_key, frequency=None, absorption_coefficients=None):
        """
        Calculate absorption for a surface
        
        Args:
            area: Surface area in square feet
            material_key: Material identifier
            frequency: Optional frequency (125, 250, 500, 1000, 2000, 4000) for specific calculation
            absorption_coefficients: Optional direct coefficients (for doors/windows)
        
        Returns:
            float: Absorption in sabins
        """
        # If direct coefficients provided (for doors/windows), use those
        if absorption_coefficients:
            if frequency and frequency in absorption_coefficients:
                absorption_coeff = absorption_coefficients[frequency]
            else:
                # Use NRC-equivalent (average of 250, 500, 1000, 2000 Hz)
                nrc_frequencies = [250, 500, 1000, 2000]
                nrc_coeffs = [absorption_coefficients.get(f, 0) for f in nrc_frequencies]
                absorption_coeff = sum(nrc_coeffs) / 4.0
            
            return area * absorption_coeff
        
        # Standard material lookup with fallback to name matching
        actual_key = self._find_material_by_key_or_name(material_key)
        if not actual_key:
            print(f"WARNING: Material '{material_key}' not found in materials database")
            return 0.0
        
        material_key = actual_key  # Use the found key
            
        material = self.materials_db[material_key]
        
        # Use frequency-specific coefficient if available and requested  
        if frequency and 'coefficients' in material:
            freq_str = str(frequency)
            if freq_str in material['coefficients']:
                absorption_coeff = material['coefficients'][freq_str]
            else:
                # Fallback to general absorption coefficient
                absorption_coeff = material['absorption_coeff']
        else:
            # Use NRC or general absorption coefficient
            absorption_coeff = material.get('nrc', material['absorption_coeff'])
        
        return area * absorption_coeff
        
    def calculate_total_absorption(self, surfaces, frequency=None):
        """
        Calculate total absorption from multiple surfaces
        
        Args:
            surfaces: List of dicts with 'area', 'material_key', and optional 'absorption_coefficients'
            frequency: Optional frequency for frequency-specific calculation
        
        Returns:
            float: Total absorption in sabins
        """
        total_absorption = 0.0
        
        for surface in surfaces:
            area = surface.get('area', 0)
            material_key = surface.get('material_key')
            absorption_coefficients = surface.get('absorption_coefficients')
            
            if area > 0 and material_key:
                absorption = self.calculate_surface_absorption(
                    area, material_key, frequency, absorption_coefficients
                )
                total_absorption += absorption
                
        return total_absorption
        
    def calculate_rt60_sabine(self, volume, total_absorption):
        """
        Calculate RT60 using Sabine formula
        
        RT60 = 0.049 * V / A (imperial units)
        where V = volume (cubic feet), A = total absorption (sabins)
        
        Args:
            volume: Room volume in cubic feet
            total_absorption: Total absorption in sabins
            
        Returns:
            float: RT60 in seconds
        """
        if total_absorption <= 0:
            return float('inf')  # Infinite reverberation
            
        return 0.049 * volume / total_absorption
        
    def calculate_rt60_eyring(self, volume, surfaces, frequency=None):
        """
        Calculate RT60 using Eyring formula (more accurate for high absorption)
        
        RT60 = 0.049 * V / (-S * ln(1 - α_avg)) (imperial units)
        where α_avg is the average absorption coefficient
        
        Args:
            volume: Room volume in cubic feet
            surfaces: List of surface dicts with area and material_key
            frequency: Optional frequency for frequency-specific calculation
            
        Returns:
            float: RT60 in seconds
        """
        total_area = 0.0
        weighted_absorption = 0.0
        
        for surface in surfaces:
            area = surface.get('area', 0)
            material_key = surface.get('material_key')
            
            if area > 0 and material_key and material_key in self.materials_db:
                material = self.materials_db[material_key]
                
                # Get appropriate absorption coefficient
                if frequency and 'coefficients' in material:
                    freq_str = str(frequency)
                    if freq_str in material['coefficients']:
                        absorption_coeff = material['coefficients'][freq_str]
                    else:
                        absorption_coeff = material['absorption_coeff']
                else:
                    absorption_coeff = material.get('nrc', material['absorption_coeff'])
                
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
                    
                return 0.049 * volume / denominator
            except (ValueError, ZeroDivisionError):
                return float('inf')
            
    def calculate_space_rt60(self, space_data, method='sabine'):
        """
        Calculate RT60 for a space
        
        Args:
            space_data: Dict with volume, areas, materials, and optional doors/windows
            method: 'sabine' or 'eyring'
            
        Returns:
            dict: Calculation results
        """
        # Refresh materials database to ensure we have latest materials
        self.refresh_materials_db()
        
        # Extract space properties
        volume = space_data.get('volume', 0)
        floor_area = space_data.get('floor_area', 0)
        wall_area = space_data.get('wall_area', 0)
        ceiling_area = space_data.get('ceiling_area', floor_area)  # Default to floor area
        
        # Support new materials_data format with specific square footages
        ceiling_materials_data = space_data.get('ceiling_materials_data', [])
        wall_materials_data = space_data.get('wall_materials_data', [])
        floor_materials_data = space_data.get('floor_materials_data', [])
        
        # Fallback to legacy multiple materials format
        ceiling_materials = space_data.get('ceiling_materials', [])
        wall_materials = space_data.get('wall_materials', [])
        floor_materials = space_data.get('floor_materials', [])
        
        # Fallback to legacy single material fields if no multiple materials
        if not ceiling_materials and space_data.get('ceiling_material'):
            ceiling_materials = [space_data.get('ceiling_material')]
        if not wall_materials and space_data.get('wall_material'):
            wall_materials = [space_data.get('wall_material')]
        if not floor_materials and space_data.get('floor_material'):
            floor_materials = [space_data.get('floor_material')]
        
        # Get doors/windows data
        doors_windows = space_data.get('doors_windows', [])
        include_doors_windows = space_data.get('include_doors_windows', True)
        
        if volume <= 0:
            return {
                'rt60': 0,
                'method': method,
                'error': 'Invalid volume'
            }
            
        # Calculate total doors/windows area to subtract from wall area
        doors_windows_area = 0
        if include_doors_windows and doors_windows:
            doors_windows_area = sum(item.get('total_area', 0) for item in doors_windows)
        
        # Adjust wall area to account for doors/windows
        effective_wall_area = max(0, wall_area - doors_windows_area)
            
        # Prepare surfaces for calculation - now handling specific square footages
        surfaces = []
        
        # Add ceiling surfaces with specific square footages
        if ceiling_materials_data:
            for i, material_data in enumerate(ceiling_materials_data):
                material_key = material_data.get('material_key')
                area = material_data.get('square_footage', 0)
                if material_key and area > 0:
                    # Find material by key or name
                    actual_key = self._find_material_by_key_or_name(material_key)
                    if not actual_key:
                        print(f"WARNING: Material '{material_key}' not found in materials database for ceiling surface")
                        continue
                    surfaces.append({
                        'area': area,
                        'material_key': actual_key,
                        'type': f'ceiling_{i+1}' if len(ceiling_materials_data) > 1 else 'ceiling'
                    })
        elif ceiling_area > 0 and ceiling_materials:
            # Fallback to equal distribution
            area_per_material = ceiling_area / len(ceiling_materials)
            for i, material_key in enumerate(ceiling_materials):
                if material_key:  # Skip None/empty materials
                    # Find material by key or name
                    actual_key = self._find_material_by_key_or_name(material_key)
                    if not actual_key:
                        print(f"WARNING: Material '{material_key}' not found in materials database for ceiling surface")
                        continue
                    surfaces.append({
                        'area': area_per_material,
                        'material_key': actual_key,
                        'type': f'ceiling_{i+1}' if len(ceiling_materials) > 1 else 'ceiling'
                    })
            
        # Add wall surfaces with specific square footages
        if wall_materials_data:
            for i, material_data in enumerate(wall_materials_data):
                material_key = material_data.get('material_key')
                area = material_data.get('square_footage', 0)
                if material_key and area > 0:
                    # Find material by key or name
                    actual_key = self._find_material_by_key_or_name(material_key)
                    if not actual_key:
                        print(f"WARNING: Material '{material_key}' not found in materials database for wall surface")
                        continue
                    surfaces.append({
                        'area': area, 
                        'material_key': actual_key,
                        'type': f'wall_{i+1}' if len(wall_materials_data) > 1 else 'wall'
                    })
        elif effective_wall_area > 0 and wall_materials:
            # Fallback to equal distribution
            area_per_material = effective_wall_area / len(wall_materials)
            for i, material_key in enumerate(wall_materials):
                if material_key:  # Skip None/empty materials
                    # Find material by key or name
                    actual_key = self._find_material_by_key_or_name(material_key)
                    if not actual_key:
                        print(f"WARNING: Material '{material_key}' not found in materials database for wall surface")
                        continue
                    surfaces.append({
                        'area': area_per_material,
                        'material_key': actual_key,
                        'type': f'wall_{i+1}' if len(wall_materials) > 1 else 'wall'
                    })
            
        # Add floor surfaces with specific square footages
        if floor_materials_data:
            for i, material_data in enumerate(floor_materials_data):
                material_key = material_data.get('material_key')
                area = material_data.get('square_footage', 0)
                if material_key and area > 0:
                    # Find material by key or name
                    actual_key = self._find_material_by_key_or_name(material_key)
                    if not actual_key:
                        print(f"WARNING: Material '{material_key}' not found in materials database for floor surface")
                        continue
                    surfaces.append({
                        'area': area,
                        'material_key': actual_key,
                        'type': f'floor_{i+1}' if len(floor_materials_data) > 1 else 'floor'
                    })
        elif floor_area > 0 and floor_materials:
            # Fallback to equal distribution  
            area_per_material = floor_area / len(floor_materials)
            for i, material_key in enumerate(floor_materials):
                if material_key:  # Skip None/empty materials
                    # Find material by key or name
                    actual_key = self._find_material_by_key_or_name(material_key)
                    if not actual_key:
                        print(f"WARNING: Material '{material_key}' not found in materials database for floor surface")
                        continue
                    surfaces.append({
                        'area': area_per_material,
                        'material_key': actual_key,
                        'type': f'floor_{i+1}' if len(floor_materials) > 1 else 'floor'
                    })
        
        # Add doors/windows as separate surfaces
        if include_doors_windows and doors_windows:
            for i, dw_item in enumerate(doors_windows):
                material_key = dw_item.get('material_key')
                area = dw_item.get('total_area', 0)
                element_type = dw_item.get('type', 'door')
                
                if material_key and area > 0:
                    # For doors/windows, we need to get absorption coefficients differently
                    # since they may not be in STANDARD_MATERIALS
                    surfaces.append({
                        'area': area,
                        'material_key': material_key,
                        'type': f'{element_type}_{i+1}',
                        'absorption_coefficients': dw_item.get('absorption_coefficients', {}),
                        'is_door_window': True
                    })
            
        if not surfaces:
            print(f"ERROR: No valid surfaces found for RT60 calculation")
            print(f"  Ceiling materials data: {ceiling_materials_data}")
            print(f"  Wall materials data: {wall_materials_data}")
            print(f"  Floor materials data: {floor_materials_data}")
            print(f"  Materials DB size: {len(self.materials_db)}")
            return {
                'rt60': 999.9,
                'method': method,
                'error': 'No valid surfaces defined',
                'rt60_by_frequency': {f: 999.9 for f in [125, 250, 500, 1000, 2000, 4000]}
            }
            
        # Calculate RT60
        frequency = space_data.get('frequency')  # Optional frequency for specific calculations
        if method.lower() == 'eyring':
            rt60 = self.calculate_rt60_eyring(volume, surfaces, frequency)
        else:
            total_absorption = self.calculate_total_absorption(surfaces, frequency)
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
            is_door_window = surface.get('is_door_window', False)
            absorption_coefficients = surface.get('absorption_coefficients')
            
            if is_door_window and absorption_coefficients:
                # Handle doors/windows with direct coefficients
                frequency = space_data.get('frequency')
                if frequency and frequency in absorption_coefficients:
                    absorption_coeff = absorption_coefficients[frequency]
                else:
                    # Use NRC-equivalent
                    nrc_frequencies = [250, 500, 1000, 2000]
                    nrc_coeffs = [absorption_coefficients.get(f, 0) for f in nrc_frequencies]
                    absorption_coeff = sum(nrc_coeffs) / 4.0
                
                absorption = area * absorption_coeff
                
                # Try to get material name from enhanced materials or use key
                try:
                    from ..data.enhanced_materials import ENHANCED_MATERIALS
                    material_name = ENHANCED_MATERIALS.get(material_key, {}).get('name', material_key)
                except ImportError:
                    material_name = material_key
                
                results['surfaces'].append({
                    'type': surface_type,
                    'area': area,
                    'material_name': material_name,
                    'material_key': material_key,
                    'absorption_coeff': absorption_coeff,
                    'absorption': absorption,
                    'is_door_window': True
                })
                
                total_area += area
                total_absorption += absorption
                
            elif material_key in self.materials_db:
                # Handle standard materials
                material = self.materials_db[material_key]
                
                # Get appropriate absorption coefficient
                frequency = space_data.get('frequency')
                if frequency and 'coefficients' in material:
                    freq_str = str(frequency)
                    if freq_str in material['coefficients']:
                        absorption_coeff = material['coefficients'][freq_str]
                    else:
                        absorption_coeff = material['absorption_coeff']
                else:
                    absorption_coeff = material.get('nrc', material['absorption_coeff'])
                
                absorption = area * absorption_coeff
                
                results['surfaces'].append({
                    'type': surface_type,
                    'area': area,
                    'material_name': material['name'],
                    'material_key': material_key,
                    'absorption_coeff': absorption_coeff,
                    'absorption': absorption,
                    'is_door_window': False
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
        required_absorption = 0.049 * volume / target_rt60
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
        
    def calculate_rt60_frequency_response(self, space_data, method='sabine'):
        """
        Calculate RT60 across all frequency bands
        
        Args:
            space_data: Dict with volume, areas, and materials 
            method: 'sabine' or 'eyring'
            
        Returns:
            dict: RT60 values by frequency
        """
        frequencies = [125, 250, 500, 1000, 2000, 4000]
        rt60_by_frequency = {}
        
        for frequency in frequencies:
            # Add frequency to space data for this calculation
            freq_space_data = space_data.copy()
            freq_space_data['frequency'] = frequency
            
            # Calculate RT60 for this frequency
            results = self.calculate_space_rt60(freq_space_data, method)
            rt60_by_frequency[frequency] = results.get('rt60', 0)
        
        return {
            'rt60_by_frequency': rt60_by_frequency,
            'frequencies': frequencies,
            'method': method,
            'space_data': space_data
        }


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