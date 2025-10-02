"""
Enhanced RT60 Calculator - Frequency-band analysis with target compliance checking
"""

import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from data.enhanced_materials import (
    ENHANCED_MATERIALS, MATERIALS_WITH_NRC, OCTAVE_BANDS, 
    ROOM_TYPE_PRESETS, get_material_info
)


class EnhancedRT60Calculator:
    """Enhanced RT60 calculator with frequency-band analysis and compliance checking"""
    
    def __init__(self):
        self.materials_db = MATERIALS_WITH_NRC
        self.octave_bands = OCTAVE_BANDS
        self.room_presets = ROOM_TYPE_PRESETS
        
    def calculate_surface_absorption_by_frequency(self, area: float, material_key: str) -> Dict[int, float]:
        """
        Calculate absorption for a surface across all frequency bands
        
        Args:
            area: Surface area in square feet
            material_key: Material identifier
            
        Returns:
            Dict of frequency: absorption_sabins
        """
        if material_key not in self.materials_db:
            return {freq: 0.0 for freq in self.octave_bands}
        
        material = self.materials_db[material_key]
        absorption_coeffs = material.get('absorption_coefficients', {})
        
        return {freq: area * absorption_coeffs.get(freq, 0.0) 
                for freq in self.octave_bands}
    
    def calculate_total_absorption_by_frequency(self, surface_instances: List[Dict]) -> Dict[int, float]:
        """
        Calculate total absorption from multiple surface instances by frequency
        
        Args:
            surface_instances: List of surface dicts with area and material_key
            
        Returns:
            Dict of frequency: total_absorption_sabins
        """
        total_absorption = {freq: 0.0 for freq in self.octave_bands}
        
        for surface in surface_instances:
            area = surface.get('area', 0)
            material_key = surface.get('material_key')
            
            if area > 0 and material_key:
                surface_absorption = self.calculate_surface_absorption_by_frequency(area, material_key)
                for freq in self.octave_bands:
                    total_absorption[freq] += surface_absorption[freq]
        
        return total_absorption
    
    def calculate_rt60_sabine_by_frequency(self, volume: float, 
                                         total_absorption: Dict[int, float]) -> Dict[int, float]:
        """
        Calculate RT60 using Sabine formula for each frequency band
        
        RT60 = 0.049 * V / A (imperial units)
        
        Args:
            volume: Room volume in cubic feet
            total_absorption: Dict of frequency: absorption_sabins
            
        Returns:
            Dict of frequency: rt60_seconds
        """
        rt60_values = {}
        
        for freq in self.octave_bands:
            absorption = total_absorption.get(freq, 0)
            if absorption <= 0:
                rt60_values[freq] = 999.9  # Very high RT60 for no absorption
            else:
                rt60_values[freq] = 0.049 * volume / absorption
                
        return rt60_values
    
    def calculate_rt60_eyring_by_frequency(self, volume: float, 
                                          surface_instances: List[Dict]) -> Dict[int, float]:
        """
        Calculate RT60 using Eyring formula for each frequency band
        
        RT60 = 0.049 * V / (-S * ln(1 - α_avg)) (imperial units)
        
        Args:
            volume: Room volume in cubic feet
            surface_instances: List of surface dicts with area and material_key
            
        Returns:
            Dict of frequency: rt60_seconds
        """
        rt60_values = {}
        
        for freq in self.octave_bands:
            total_area = 0.0
            weighted_absorption = 0.0
            
            # Calculate average absorption coefficient for this frequency
            for surface in surface_instances:
                area = surface.get('area', 0)
                material_key = surface.get('material_key')
                
                if area > 0 and material_key and material_key in self.materials_db:
                    material = self.materials_db[material_key]
                    absorption_coeff = material.get('absorption_coefficients', {}).get(freq, 0)
                    total_area += area
                    weighted_absorption += area * absorption_coeff
            
            if total_area <= 0:
                rt60_values[freq] = 999.9
                continue
            
            avg_absorption_coeff = weighted_absorption / total_area
            
            # Avoid log(0) or log(negative)
            if avg_absorption_coeff >= 1.0:
                avg_absorption_coeff = 0.99
            elif avg_absorption_coeff <= 0:
                rt60_values[freq] = 999.9
                continue
            
            try:
                denominator = -total_area * math.log(1 - avg_absorption_coeff)
                if denominator <= 0:
                    rt60_values[freq] = 999.9
                else:
                    rt60_values[freq] = 0.049 * volume / denominator
            except (ValueError, ZeroDivisionError):
                rt60_values[freq] = 999.9
        
        return rt60_values
    
    def calculate_space_rt60_enhanced(self, space_data: Dict, method: str = 'sabine') -> Dict:
        """
        Calculate enhanced RT60 analysis for a space with frequency-band results
        
        Args:
            space_data: Dict with space properties and surface instances
            method: 'sabine' or 'eyring'
            
        Returns:
            Comprehensive RT60 calculation results
        """
        volume = space_data.get('volume', 0)
        surface_instances = space_data.get('surface_instances', [])
        target_rt60 = space_data.get('target_rt60', 0.8)
        target_tolerance = space_data.get('target_tolerance', 0.1)
        room_type = space_data.get('room_type', 'custom')
        
        if volume <= 0:
            return self._create_error_result('Invalid volume', method)
        
        if not surface_instances:
            return self._create_error_result('No valid surfaces defined', method)
        
        # Calculate RT60 by frequency
        if method.lower() == 'eyring':
            rt60_by_freq = self.calculate_rt60_eyring_by_frequency(volume, surface_instances)
        else:
            total_absorption = self.calculate_total_absorption_by_frequency(surface_instances)
            rt60_by_freq = self.calculate_rt60_sabine_by_frequency(volume, total_absorption)
        
        # Calculate total absorption for reporting
        total_absorption = self.calculate_total_absorption_by_frequency(surface_instances)
        
        # Check compliance for each frequency
        compliance_by_freq = self._check_frequency_compliance(
            rt60_by_freq, target_rt60, target_tolerance
        )
        
        # Calculate summary statistics
        average_rt60 = self._calculate_average_rt60(rt60_by_freq)
        total_surface_area = sum(surface.get('area', 0) for surface in surface_instances)
        avg_absorption_coeff = self._calculate_average_absorption_coefficient(
            surface_instances, total_surface_area
        )
        
        # Determine overall compliance
        overall_compliance = all(compliance_by_freq.values())
        compliance_notes = self._generate_compliance_notes(compliance_by_freq, rt60_by_freq, target_rt60)
        
        # Prepare detailed surface analysis
        surface_analysis = self._analyze_surfaces(surface_instances)
        
        # Create comprehensive results
        results = {
            'calculation_date': datetime.utcnow(),
            'method': method,
            'room_volume': volume,
            'target_rt60': target_rt60,
            'target_tolerance': target_tolerance,
            'room_type': room_type,
            
            # Frequency-specific results
            'rt60_by_frequency': rt60_by_freq,
            'absorption_by_frequency': total_absorption,
            'compliance_by_frequency': compliance_by_freq,
            
            # Summary statistics
            'average_rt60': average_rt60,
            'total_surface_area': total_surface_area,
            'avg_absorption_coeff': avg_absorption_coeff,
            'overall_compliance': overall_compliance,
            'compliance_notes': compliance_notes,
            
            # Detailed analysis
            'surface_analysis': surface_analysis,
            'recommendations': self._generate_recommendations(
                rt60_by_freq, target_rt60, surface_instances, volume
            )
        }
        
        return results
    
    def _create_error_result(self, error_message: str, method: str) -> Dict:
        """Create error result structure"""
        return {
            'error': error_message,
            'method': method,
            'rt60_by_frequency': {freq: 0 for freq in self.octave_bands},
            'absorption_by_frequency': {freq: 0 for freq in self.octave_bands},
            'compliance_by_frequency': {freq: False for freq in self.octave_bands},
            'average_rt60': 0,
            'overall_compliance': False,
            'calculation_date': datetime.utcnow()
        }
    
    def _check_frequency_compliance(self, rt60_by_freq: Dict[int, float], 
                                  target_rt60: float, tolerance: float) -> Dict[int, bool]:
        """Check compliance for each frequency band"""
        compliance = {}
        lower_bound = target_rt60 - tolerance
        upper_bound = target_rt60 + tolerance
        
        for freq, rt60 in rt60_by_freq.items():
            compliance[freq] = lower_bound <= rt60 <= upper_bound
            
        return compliance
    
    def _calculate_average_rt60(self, rt60_by_freq: Dict[int, float]) -> float:
        """Calculate average RT60 across speech frequencies (250-4000 Hz)"""
        speech_frequencies = [250, 500, 1000, 2000, 4000]
        valid_values = [rt60_by_freq.get(freq, 0) for freq in speech_frequencies 
                       if rt60_by_freq.get(freq, 0) > 0 and rt60_by_freq.get(freq, 0) < 999]
        
        if valid_values:
            return round(sum(valid_values) / len(valid_values), 2)
        return 0.0
    
    def _calculate_average_absorption_coefficient(self, surface_instances: List[Dict], 
                                                total_area: float) -> float:
        """Calculate average absorption coefficient across all surfaces"""
        if total_area <= 0:
            return 0.0
        
        # Calculate NRC-weighted average
        total_weighted_nrc = 0.0
        
        for surface in surface_instances:
            area = surface.get('area', 0)
            material_key = surface.get('material_key')
            
            if area > 0 and material_key and material_key in self.materials_db:
                material = self.materials_db[material_key]
                nrc = material.get('nrc', 0)
                total_weighted_nrc += area * nrc
        
        return round(total_weighted_nrc / total_area, 3) if total_area > 0 else 0.0
    
    def _generate_compliance_notes(self, compliance_by_freq: Dict[int, bool], 
                                 rt60_by_freq: Dict[int, float], target_rt60: float) -> str:
        """Generate compliance notes text"""
        failed_frequencies = [str(freq) + 'Hz' for freq, compliant in compliance_by_freq.items() 
                            if not compliant]
        
        if not failed_frequencies:
            return "All frequencies meet target RT60 ± tolerance"
        
        notes = f"Target not met at: {', '.join(failed_frequencies)}"
        
        # Add specific insights
        low_freq_issues = any(not compliance_by_freq.get(freq, False) 
                             for freq in [125, 250] 
                             if rt60_by_freq.get(freq, 0) > target_rt60)
        
        high_freq_issues = any(not compliance_by_freq.get(freq, False) 
                              for freq in [2000, 4000] 
                              if rt60_by_freq.get(freq, 0) > target_rt60)
        
        if low_freq_issues:
            notes += ". Consider bass traps or thicker absorptive materials for low frequencies"
        
        if high_freq_issues:
            notes += ". Consider additional absorptive materials for high frequencies"
        
        return notes
    
    def _analyze_surfaces(self, surface_instances: List[Dict]) -> List[Dict]:
        """Analyze each surface for detailed reporting"""
        analysis = []
        
        for surface in surface_instances:
            area = surface.get('area', 0)
            material_key = surface.get('material_key')
            surface_type = surface.get('surface_type', 'Unknown')
            
            if material_key and material_key in self.materials_db:
                material = self.materials_db[material_key]
                
                # Calculate absorption by frequency for this surface
                surface_absorption = self.calculate_surface_absorption_by_frequency(area, material_key)
                
                analysis.append({
                    'surface_type': surface_type,
                    'material_name': material['name'],
                    'material_key': material_key,
                    'area': area,
                    'nrc': material.get('nrc', 0),
                    'absorption_by_frequency': surface_absorption,
                    'absorption_coefficients': material.get('absorption_coefficients', {}),
                    'total_absorption_nrc': area * material.get('nrc', 0)
                })
        
        return analysis
    
    def _generate_recommendations(self, rt60_by_freq: Dict[int, float], target_rt60: float,
                                surface_instances: List[Dict], volume: float) -> List[Dict]:
        """Generate material and design recommendations"""
        recommendations = []
        
        # Calculate current average RT60
        current_avg = self._calculate_average_rt60(rt60_by_freq)
        
        if abs(current_avg - target_rt60) <= 0.1:
            recommendations.append({
                'type': 'status',
                'priority': 'info',
                'message': 'Current RT60 is within acceptable range of target'
            })
            return recommendations
        
        # Analyze frequency-specific issues
        problem_frequencies = []
        for freq, rt60 in rt60_by_freq.items():
            if abs(rt60 - target_rt60) > 0.2:  # More than 0.2s deviation
                problem_frequencies.append((freq, rt60))
        
        if current_avg > target_rt60:
            # RT60 too high - need more absorption
            required_absorption = 0.049 * volume / target_rt60
            current_absorption = sum(self.calculate_total_absorption_by_frequency(surface_instances).values()) / len(self.octave_bands)
            additional_needed = required_absorption - current_absorption
            
            recommendations.append({
                'type': 'increase_absorption',
                'priority': 'high',
                'message': f'RT60 is {current_avg - target_rt60:.1f}s too high. Need approximately {additional_needed:.0f} more sabins of absorption.',
                'suggestion': 'Consider adding acoustic panels, carpet, or other absorptive materials'
            })
            
            # Frequency-specific recommendations
            if any(freq <= 250 for freq, _ in problem_frequencies):
                recommendations.append({
                    'type': 'low_frequency',
                    'priority': 'medium',
                    'message': 'Low frequency RT60 is elevated',
                    'suggestion': 'Consider bass traps, thick panels, or cavity-backed absorbers for 125-250 Hz'
                })
            
            if any(freq >= 2000 for freq, _ in problem_frequencies):
                recommendations.append({
                    'type': 'high_frequency',
                    'priority': 'medium', 
                    'message': 'High frequency RT60 is elevated',
                    'suggestion': 'Standard acoustic panels or ceiling tiles will help with 2000-4000 Hz'
                })
        
        elif current_avg < target_rt60:
            # RT60 too low - need less absorption or more reflective surfaces
            recommendations.append({
                'type': 'decrease_absorption',
                'priority': 'medium',
                'message': f'RT60 is {target_rt60 - current_avg:.1f}s too low.',
                'suggestion': 'Consider more reflective materials or reducing absorptive treatments'
            })
        
        # Material-specific recommendations
        total_area = sum(surface.get('area', 0) for surface in surface_instances)
        highly_absorptive_area = sum(
            surface.get('area', 0) for surface in surface_instances
            if surface.get('material_key') in self.materials_db 
            and self.materials_db[surface.get('material_key')].get('nrc', 0) > 0.7
        )
        
        if highly_absorptive_area / total_area > 0.6:  # More than 60% highly absorptive
            recommendations.append({
                'type': 'material_balance',
                'priority': 'low',
                'message': 'Room has high percentage of absorptive materials',
                'suggestion': 'Consider balancing with some reflective surfaces for natural acoustics'
            })
        
        return recommendations
    
    def suggest_materials_for_target(self, current_results: Dict, target_rt60: float,
                                   surface_type: str = None) -> List[Dict]:
        """
        Suggest alternative materials to achieve target RT60
        
        Args:
            current_results: Current RT60 calculation results
            target_rt60: Desired RT60 value
            surface_type: Specific surface type to modify (optional)
            
        Returns:
            List of material suggestions with expected impact
        """
        suggestions = []
        current_avg = current_results.get('average_rt60', 0)
        
        if abs(current_avg - target_rt60) <= 0.1:
            return [{'message': 'Current materials are appropriate for target RT60'}]
        
        volume = current_results.get('room_volume', 0)
        surface_analysis = current_results.get('surface_analysis', [])
        
        # Calculate required absorption change
        if current_avg > target_rt60:
            # Need more absorption
            required_total_absorption = 0.049 * volume / target_rt60
            current_total_absorption = sum(current_results.get('absorption_by_frequency', {}).values()) / len(self.octave_bands)
            additional_absorption_needed = required_total_absorption - current_total_absorption
            
            # Find materials with higher absorption
            for surface in surface_analysis:
                current_material = surface.get('material_key')
                current_nrc = self.materials_db.get(current_material, {}).get('nrc', 0)
                surface_area = surface.get('area', 0)
                
                # Suggest materials with higher NRC in same category
                better_materials = self._find_better_materials(
                    current_material, 'higher', surface_area, additional_absorption_needed
                )
                
                for material_key, impact in better_materials:
                    suggestions.append({
                        'surface_type': surface.get('surface_type'),
                        'current_material': current_material,
                        'suggested_material': material_key,
                        'current_nrc': current_nrc,
                        'suggested_nrc': self.materials_db[material_key].get('nrc', 0),
                        'absorption_increase': impact,
                        'estimated_rt60_reduction': self._estimate_rt60_change(impact, volume, current_avg)
                    })
        
        else:
            # Need less absorption (more reflective materials)
            for surface in surface_analysis:
                current_material = surface.get('material_key')
                current_nrc = self.materials_db.get(current_material, {}).get('nrc', 0)
                surface_area = surface.get('area', 0)
                
                # Suggest materials with lower NRC
                better_materials = self._find_better_materials(
                    current_material, 'lower', surface_area, 0
                )
                
                for material_key, impact in better_materials:
                    suggestions.append({
                        'surface_type': surface.get('surface_type'),
                        'current_material': current_material,
                        'suggested_material': material_key,
                        'current_nrc': current_nrc,
                        'suggested_nrc': self.materials_db[material_key].get('nrc', 0),
                        'absorption_decrease': abs(impact),
                        'estimated_rt60_increase': self._estimate_rt60_change(impact, volume, current_avg)
                    })
        
        # Sort by estimated impact
        suggestions.sort(key=lambda x: abs(x.get('estimated_rt60_reduction', 0) + 
                                          x.get('estimated_rt60_increase', 0)), reverse=True)
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _find_better_materials(self, current_material: str, direction: str, 
                              area: float, target_change: float) -> List[Tuple[str, float]]:
        """Find materials with better absorption characteristics"""
        if current_material not in self.materials_db:
            return []
        
        current_category = self.materials_db[current_material].get('category')
        current_nrc = self.materials_db[current_material].get('nrc', 0)
        
        candidates = []
        
        for material_key, material in self.materials_db.items():
            if (material.get('category') == current_category and 
                material_key != current_material):
                
                material_nrc = material.get('nrc', 0)
                
                if direction == 'higher' and material_nrc > current_nrc:
                    absorption_increase = (material_nrc - current_nrc) * area
                    candidates.append((material_key, absorption_increase))
                elif direction == 'lower' and material_nrc < current_nrc:
                    absorption_decrease = (current_nrc - material_nrc) * area
                    candidates.append((material_key, -absorption_decrease))
        
        # Sort by impact magnitude
        candidates.sort(key=lambda x: abs(x[1]), reverse=True)
        return candidates[:3]  # Top 3 candidates
    
    def _estimate_rt60_change(self, absorption_change: float, volume: float, 
                             current_rt60: float) -> float:
        """Estimate RT60 change from absorption change"""
        if current_rt60 <= 0:
            return 0
        
        current_absorption = 0.049 * volume / current_rt60
        new_absorption = current_absorption + absorption_change
        
        if new_absorption <= 0:
            return 999  # Very high RT60
        
        new_rt60 = 0.049 * volume / new_absorption
        return round(new_rt60 - current_rt60, 2)
    
    def format_frequency_report(self, results: Dict) -> str:
        """Format comprehensive frequency analysis report"""
        if 'error' in results:
            return f"Calculation Error: {results['error']}"
        
        report = "Enhanced RT60 Calculation Report\n"
        report += "=" * 50 + "\n\n"
        
        # Basic information
        report += f"Room Volume: {results['room_volume']:,.0f} cubic feet\n"
        report += f"Calculation Method: {results['method'].title()}\n"
        report += f"Target RT60: {results['target_rt60']:.1f} seconds\n"
        report += f"Target Tolerance: ±{results['target_tolerance']:.1f} seconds\n"
        report += f"Average RT60: {results['average_rt60']:.2f} seconds\n"
        report += f"Overall Compliance: {'✅ PASS' if results['overall_compliance'] else '❌ FAIL'}\n\n"
        
        # Frequency analysis table
        report += "Frequency Analysis:\n"
        report += "-" * 70 + "\n"
        report += f"{'Freq (Hz)':<8} {'RT60 (s)':<8} {'Target':<8} {'Status':<8} {'Absorption':<12}\n"
        report += "-" * 70 + "\n"
        
        for freq in self.octave_bands:
            rt60 = results['rt60_by_frequency'].get(freq, 0)
            absorption = results['absorption_by_frequency'].get(freq, 0)
            compliant = results['compliance_by_frequency'].get(freq, False)
            status = "✅ PASS" if compliant else "❌ FAIL"
            
            report += f"{freq:<8} {rt60:<8.2f} {results['target_rt60']:<8.1f} {status:<8} {absorption:<12.0f}\n"
        
        report += "\n"
        
        # Surface analysis
        if 'surface_analysis' in results:
            report += "Surface Analysis:\n"
            report += "-" * 50 + "\n"
            
            for surface in results['surface_analysis']:
                report += f"{surface['surface_type']}: {surface['area']:.0f} sf\n"
                report += f"  Material: {surface['material_name']}\n"
                report += f"  NRC: {surface['nrc']:.2f}\n"
                report += f"  Total Absorption (NRC): {surface['total_absorption_nrc']:.1f} sabins\n\n"
        
        # Compliance notes
        if results.get('compliance_notes'):
            report += f"Notes: {results['compliance_notes']}\n\n"
        
        # Recommendations
        if 'recommendations' in results and results['recommendations']:
            report += "Recommendations:\n"
            report += "-" * 20 + "\n"
            for rec in results['recommendations']:
                report += f"• {rec['message']}\n"
                if 'suggestion' in rec:
                    report += f"  → {rec['suggestion']}\n"
        
        return report
    
    def export_results_to_dict(self, results: Dict) -> Dict:
        """Export results in a format suitable for database storage"""
        if 'error' in results:
            return results
        
        return {
            'calculation_date': results['calculation_date'],
            'method': results['method'],
            'room_volume': results['room_volume'],
            'target_rt60': results['target_rt60'],
            'target_tolerance': results['target_tolerance'],
            'room_type': results.get('room_type', 'custom'),
            
            # RT60 values by frequency
            'rt60_125': results['rt60_by_frequency'].get(125, 0),
            'rt60_250': results['rt60_by_frequency'].get(250, 0),
            'rt60_500': results['rt60_by_frequency'].get(500, 0),
            'rt60_1000': results['rt60_by_frequency'].get(1000, 0),
            'rt60_2000': results['rt60_by_frequency'].get(2000, 0),
            'rt60_4000': results['rt60_by_frequency'].get(4000, 0),
            
            # Absorption values by frequency
            'total_sabines_125': results['absorption_by_frequency'].get(125, 0),
            'total_sabines_250': results['absorption_by_frequency'].get(250, 0),
            'total_sabines_500': results['absorption_by_frequency'].get(500, 0),
            'total_sabines_1000': results['absorption_by_frequency'].get(1000, 0),
            'total_sabines_2000': results['absorption_by_frequency'].get(2000, 0),
            'total_sabines_4000': results['absorption_by_frequency'].get(4000, 0),
            
            # Compliance by frequency
            'meets_target_125': results['compliance_by_frequency'].get(125, False),
            'meets_target_250': results['compliance_by_frequency'].get(250, False),
            'meets_target_500': results['compliance_by_frequency'].get(500, False),
            'meets_target_1000': results['compliance_by_frequency'].get(1000, False),
            'meets_target_2000': results['compliance_by_frequency'].get(2000, False),
            'meets_target_4000': results['compliance_by_frequency'].get(4000, False),
            
            # Summary
            'overall_compliance': results['overall_compliance'],
            'compliance_notes': results['compliance_notes'],
            'average_rt60': results['average_rt60'],
            'total_surface_area': results['total_surface_area'],
            'average_absorption_coeff': results['avg_absorption_coeff']
        }


# Convenience functions
def calculate_enhanced_rt60(space_data: Dict, method: str = 'sabine') -> Dict:
    """
    Convenience function for enhanced RT60 calculation
    
    Args:
        space_data: Space configuration data
        method: Calculation method ('sabine' or 'eyring')
        
    Returns:
        Enhanced RT60 calculation results
    """
    calculator = EnhancedRT60Calculator()
    return calculator.calculate_space_rt60_enhanced(space_data, method)


def get_room_type_target(room_type: str) -> Dict:
    """Get target RT60 parameters for room type"""
    return ROOM_TYPE_PRESETS.get(room_type, ROOM_TYPE_PRESETS['custom'])


def create_enhanced_calculator() -> EnhancedRT60Calculator:
    """Factory function to create enhanced RT60 calculator"""
    return EnhancedRT60Calculator()