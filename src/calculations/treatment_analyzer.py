"""
Treatment Deficiency Analyzer - Analyze acoustic treatment gaps and suggest improvements
"""

import math
from typing import Dict, List, Optional, Tuple, Any

try:
    from ..calculations.rt60_calculator import RT60Calculator
    from ..data.material_search import MaterialSearchEngine
except ImportError:
    import sys
    import os
    current_dir = os.path.dirname(__file__)
    src_dir = os.path.dirname(current_dir)
    sys.path.insert(0, src_dir)
    from calculations.rt60_calculator import RT60Calculator
    from data.material_search import MaterialSearchEngine


class TreatmentAnalyzer:
    """Analyze acoustic treatment deficiencies and suggest optimal materials"""
    
    def __init__(self):
        self.rt60_calculator = RT60Calculator()
        self.search_engine = MaterialSearchEngine()
        self.frequencies = [125, 250, 500, 1000, 2000, 4000]
        
    def analyze_treatment_gaps(self, space_data: Dict) -> Dict[str, Any]:
        """
        Analyze treatment gaps across frequency spectrum
        
        Args:
            space_data: Current space configuration with RT60 data
            
        Returns:
            Dict with gap analysis results
        """
        # Calculate current RT60 across frequencies
        rt60_results = self.rt60_calculator.calculate_rt60_frequency_response(space_data)
        current_rt60 = rt60_results['rt60_by_frequency']
        
        target_rt60 = space_data.get('target_rt60', 0.6)
        volume = space_data.get('volume', 0)
        
        if volume <= 0:
            return {'error': 'Invalid volume'}
        
        analysis = {
            'current_rt60': current_rt60,
            'target_rt60': target_rt60,
            'frequency_gaps': {},
            'problem_frequencies': [],
            'severity_scores': {},
            'overall_assessment': {},
            'treatment_priorities': []
        }
        
        # Analyze each frequency
        total_gap_severity = 0
        max_gap = 0
        
        for frequency in self.frequencies:
            current = current_rt60.get(frequency, 0)
            gap = current - target_rt60
            gap_percentage = (gap / target_rt60) * 100 if target_rt60 > 0 else 0
            
            # Calculate severity (0-100 scale)
            severity = min(100, abs(gap_percentage) * 2)  # 50% gap = 100 severity
            
            analysis['frequency_gaps'][frequency] = {
                'current_rt60': current,
                'target_rt60': target_rt60,
                'gap': gap,
                'gap_percentage': gap_percentage,
                'severity': severity,
                'needs_treatment': abs(gap) > 0.1,
                'treatment_type': 'more_absorption' if gap > 0 else 'less_absorption'
            }
            
            if abs(gap) > 0.1:
                analysis['problem_frequencies'].append(frequency)
                
            analysis['severity_scores'][frequency] = severity
            total_gap_severity += severity
            max_gap = max(max_gap, abs(gap))
        
        # Overall assessment
        avg_severity = total_gap_severity / len(self.frequencies)
        analysis['overall_assessment'] = {
            'average_severity': avg_severity,
            'max_gap': max_gap,
            'problem_frequency_count': len(analysis['problem_frequencies']),
            'needs_treatment': avg_severity > 20 or max_gap > 0.2,
            'treatment_urgency': self._classify_urgency(avg_severity, max_gap)
        }
        
        # Create treatment priorities
        analysis['treatment_priorities'] = self._prioritize_treatments(analysis['frequency_gaps'])
        
        return analysis
    
    def suggest_optimal_materials(self, space_data: Dict, surface_types: List[str],
                                available_areas: Dict[str, float]) -> Dict[str, Any]:
        """
        Suggest optimal materials for multiple surfaces to address treatment gaps
        
        Args:
            space_data: Current space configuration
            surface_types: Types of surfaces to optimize ('ceiling', 'wall', 'floor')
            available_areas: Available area for each surface type
            
        Returns:
            Dict with material recommendations
        """
        # Analyze current gaps
        gap_analysis = self.analyze_treatment_gaps(space_data)
        
        if 'error' in gap_analysis:
            return gap_analysis
            
        problem_frequencies = gap_analysis['problem_frequencies']
        if not problem_frequencies:
            return {
                'message': 'No significant treatment gaps found',
                'current_performance': gap_analysis['overall_assessment']
            }
        
        volume = space_data.get('volume', 0)
        recommendations = {
            'gap_analysis': gap_analysis,
            'surface_recommendations': {},
            'material_combinations': [],
            'expected_improvements': {},
            'implementation_priority': []
        }
        
        # Get recommendations for each surface type
        for surface_type in surface_types:
            available_area = available_areas.get(surface_type, 0)
            if available_area <= 0:
                continue
                
            category = self._surface_type_to_category(surface_type)
            surface_recommendations = []
            
            # Find best materials for each problem frequency
            for frequency in problem_frequencies:
                gap_info = gap_analysis['frequency_gaps'][frequency]
                current_rt60 = gap_info['current_rt60']
                target_rt60 = gap_info['target_rt60']
                
                # Get ranked materials for this frequency
                materials = self.search_engine.rank_materials_for_treatment_gap(
                    current_rt60, target_rt60, frequency, volume, available_area, category, 10
                )
                
                if materials:
                    surface_recommendations.append({
                        'frequency': frequency,
                        'gap_severity': gap_info['severity'],
                        'top_materials': materials[:3],  # Top 3 materials
                        'treatment_type': gap_info['treatment_type']
                    })
            
            # Find materials that work well across multiple frequencies
            if surface_recommendations:
                best_overall = self._find_best_overall_material(surface_recommendations)
                
                recommendations['surface_recommendations'][surface_type] = {
                    'best_overall_material': best_overall,
                    'available_area': available_area,
                    'frequency_specific': surface_recommendations,
                    'expected_impact': self._calculate_expected_impact(
                        best_overall, available_area, gap_analysis, volume
                    )
                }
        
        # Generate material combinations
        recommendations['material_combinations'] = self._generate_material_combinations(
            recommendations['surface_recommendations'], gap_analysis
        )
        
        # Calculate expected improvements
        recommendations['expected_improvements'] = self._calculate_system_improvements(
            recommendations['material_combinations'], space_data, gap_analysis
        )
        
        # Prioritize implementations
        recommendations['implementation_priority'] = self._prioritize_implementations(
            recommendations['surface_recommendations']
        )
        
        return recommendations
    
    def simulate_material_changes(self, space_data: Dict, material_changes: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Simulate the effect of material changes on RT60
        
        Args:
            space_data: Current space configuration
            material_changes: Dict of surface_type -> {'material_key': str, 'area': float}
            
        Returns:
            Simulation results with before/after RT60 comparison
        """
        # Create modified space data
        modified_space_data = space_data.copy()
        
        # Apply material changes
        for surface_type, change in material_changes.items():
            material_key = change['material_key']
            area = change['area']
            
            # Update space data with new material
            if surface_type == 'ceiling':
                modified_space_data['ceiling_materials'] = [material_key]
                modified_space_data['ceiling_area'] = area
            elif surface_type == 'wall':
                modified_space_data['wall_materials'] = [material_key]
                modified_space_data['wall_area'] = area
            elif surface_type == 'floor':
                modified_space_data['floor_materials'] = [material_key]
                modified_space_data['floor_area'] = area
        
        # Calculate new RT60
        original_rt60 = self.rt60_calculator.calculate_rt60_frequency_response(space_data)
        modified_rt60 = self.rt60_calculator.calculate_rt60_frequency_response(modified_space_data)
        
        # Compare results
        improvements = {}
        for frequency in self.frequencies:
            original = original_rt60['rt60_by_frequency'].get(frequency, 0)
            modified = modified_rt60['rt60_by_frequency'].get(frequency, 0)
            improvement = original - modified
            improvement_percent = (improvement / original * 100) if original > 0 else 0
            
            improvements[frequency] = {
                'original_rt60': original,
                'modified_rt60': modified,
                'improvement': improvement,
                'improvement_percent': improvement_percent
            }
        
        return {
            'material_changes': material_changes,
            'frequency_improvements': improvements,
            'original_rt60_response': original_rt60,
            'modified_rt60_response': modified_rt60,
            'overall_improvement': self._calculate_overall_improvement(improvements)
        }
    
    def _classify_urgency(self, avg_severity: float, max_gap: float) -> str:
        """Classify treatment urgency"""
        if avg_severity > 60 or max_gap > 0.5:
            return 'critical'
        elif avg_severity > 40 or max_gap > 0.3:
            return 'high'
        elif avg_severity > 20 or max_gap > 0.15:
            return 'medium'
        else:
            return 'low'
    
    def _prioritize_treatments(self, frequency_gaps: Dict) -> List[Dict]:
        """Prioritize frequency treatments by severity"""
        priorities = []
        
        for frequency, gap_info in frequency_gaps.items():
            if gap_info['needs_treatment']:
                priorities.append({
                    'frequency': frequency,
                    'severity': gap_info['severity'],
                    'gap': gap_info['gap'],
                    'treatment_type': gap_info['treatment_type'],
                    'priority_rank': None  # Will be set after sorting
                })
        
        # Sort by severity
        priorities.sort(key=lambda x: x['severity'], reverse=True)
        
        # Add priority ranks
        for i, priority in enumerate(priorities):
            priority['priority_rank'] = i + 1
            
        return priorities
    
    def _surface_type_to_category(self, surface_type: str) -> str:
        """Convert surface type to material category"""
        if 'ceiling' in surface_type.lower():
            return 'ceiling'
        elif 'floor' in surface_type.lower():
            return 'floor'
        else:
            return 'wall'
    
    def _find_best_overall_material(self, surface_recommendations: List[Dict]) -> Dict:
        """Find material that performs best across multiple frequencies"""
        material_scores = {}
        
        for freq_rec in surface_recommendations:
            severity_weight = freq_rec['gap_severity'] / 100.0  # Normalize to 0-1
            
            for material in freq_rec['top_materials']:
                material_key = material['key']
                treatment_score = material.get('treatment_score', 0)
                weighted_score = treatment_score * severity_weight
                
                if material_key not in material_scores:
                    material_scores[material_key] = {
                        'material': material,
                        'total_weighted_score': 0,
                        'frequency_count': 0,
                        'frequencies_addressed': []
                    }
                
                material_scores[material_key]['total_weighted_score'] += weighted_score
                material_scores[material_key]['frequency_count'] += 1
                material_scores[material_key]['frequencies_addressed'].append(freq_rec['frequency'])
        
        if not material_scores:
            return None
            
        # Find best overall material
        best_material_key = max(material_scores.keys(), 
                               key=lambda k: material_scores[k]['total_weighted_score'])
        
        best_info = material_scores[best_material_key]
        best_info['average_score'] = (best_info['total_weighted_score'] / 
                                     best_info['frequency_count'])
        
        return best_info
    
    def _calculate_expected_impact(self, best_material_info: Dict, available_area: float,
                                 gap_analysis: Dict, volume: float) -> Dict:
        """Calculate expected impact of applying a material"""
        if not best_material_info or not best_material_info.get('material'):
            return {'error': 'No material provided'}
            
        material = best_material_info['material']
        impact = {
            'frequencies_improved': best_material_info.get('frequencies_addressed', []),
            'frequency_impacts': {},
            'overall_rt60_reduction': 0
        }
        
        total_reduction = 0
        freq_count = 0
        
        for frequency in impact['frequencies_improved']:
            # Get material absorption at this frequency
            freq_str = str(frequency)
            if 'coefficients' in material and freq_str in material['coefficients']:
                absorption_coeff = material['coefficients'][freq_str]
            else:
                absorption_coeff = material.get('absorption_coeff', 0)
            
            # Calculate additional absorption
            additional_absorption = available_area * absorption_coeff
            
            # Estimate RT60 reduction (simplified)
            gap_info = gap_analysis['frequency_gaps'].get(frequency, {})
            current_rt60 = gap_info.get('current_rt60', 0)
            
            if current_rt60 > 0:
                current_absorption = 0.161 * volume / current_rt60
                new_absorption = current_absorption + additional_absorption
                new_rt60 = 0.161 * volume / new_absorption if new_absorption > 0 else current_rt60
                rt60_reduction = current_rt60 - new_rt60
                
                impact['frequency_impacts'][frequency] = {
                    'current_rt60': current_rt60,
                    'estimated_new_rt60': new_rt60,
                    'rt60_reduction': rt60_reduction,
                    'additional_absorption': additional_absorption
                }
                
                total_reduction += rt60_reduction
                freq_count += 1
        
        if freq_count > 0:
            impact['overall_rt60_reduction'] = total_reduction / freq_count
            
        return impact
    
    def _generate_material_combinations(self, surface_recommendations: Dict, gap_analysis: Dict) -> List[Dict]:
        """Generate optimal material combinations"""
        combinations = []
        
        # Single surface treatments
        for surface_type, rec in surface_recommendations.items():
            if rec.get('best_overall_material'):
                combinations.append({
                    'type': 'single_surface',
                    'surfaces': {surface_type: rec['best_overall_material']['material']},
                    'expected_impact': rec.get('expected_impact', {}),
                    'cost_effectiveness': self._calculate_cost_effectiveness(rec),
                    'description': f"Optimize {surface_type} only"
                })
        
        # Multi-surface combinations (if multiple surfaces available)
        if len(surface_recommendations) > 1:
            all_materials = {}
            for surface_type, rec in surface_recommendations.items():
                if rec.get('best_overall_material'):
                    all_materials[surface_type] = rec['best_overall_material']['material']
            
            if len(all_materials) > 1:
                combinations.append({
                    'type': 'multi_surface',
                    'surfaces': all_materials,
                    'expected_impact': self._combine_impacts(surface_recommendations),
                    'cost_effectiveness': self._calculate_combined_cost_effectiveness(surface_recommendations),
                    'description': f"Optimize {len(all_materials)} surfaces together"
                })
        
        return combinations
    
    def _calculate_system_improvements(self, combinations: List[Dict], space_data: Dict,
                                     gap_analysis: Dict) -> Dict:
        """Calculate system-wide improvements for each combination"""
        improvements = {}
        
        for i, combination in enumerate(combinations):
            combo_key = f"combination_{i+1}"
            
            # Simulate this combination
            material_changes = {}
            for surface_type, material in combination['surfaces'].items():
                # Get available area for this surface
                if surface_type == 'ceiling':
                    area = space_data.get('ceiling_area', space_data.get('floor_area', 0))
                elif surface_type == 'floor':
                    area = space_data.get('floor_area', 0)
                else:  # wall
                    area = space_data.get('wall_area', 0)
                
                material_changes[surface_type] = {
                    'material_key': material['key'],
                    'area': area
                }
            
            # Simulate the changes
            if material_changes:
                simulation = self.simulate_material_changes(space_data, material_changes)
                improvements[combo_key] = {
                    'combination': combination,
                    'simulation_results': simulation,
                    'effectiveness_score': self._calculate_effectiveness_score(simulation)
                }
        
        return improvements
    
    def _prioritize_implementations(self, surface_recommendations: Dict) -> List[Dict]:
        """Prioritize implementation order"""
        priorities = []
        
        for surface_type, rec in surface_recommendations.items():
            if rec.get('expected_impact'):
                impact = rec['expected_impact']
                overall_reduction = impact.get('overall_rt60_reduction', 0)
                freq_count = len(impact.get('frequencies_improved', []))
                
                priorities.append({
                    'surface_type': surface_type,
                    'material': rec['best_overall_material']['material'],
                    'expected_reduction': overall_reduction,
                    'frequencies_addressed': freq_count,
                    'cost_effectiveness': rec.get('cost_effectiveness', 0),
                    'priority_score': overall_reduction * freq_count  # Simple scoring
                })
        
        # Sort by priority score
        priorities.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return priorities
    
    def _calculate_cost_effectiveness(self, recommendation: Dict) -> float:
        """Calculate cost effectiveness score (simplified)"""
        impact = recommendation.get('expected_impact', {})
        reduction = impact.get('overall_rt60_reduction', 0)
        freq_count = len(impact.get('frequencies_improved', []))
        
        # Simple cost effectiveness based on impact per frequency
        return reduction * freq_count if freq_count > 0 else 0
    
    def _calculate_combined_cost_effectiveness(self, surface_recommendations: Dict) -> float:
        """Calculate combined cost effectiveness"""
        total_effectiveness = 0
        for rec in surface_recommendations.values():
            total_effectiveness += self._calculate_cost_effectiveness(rec)
        return total_effectiveness
    
    def _combine_impacts(self, surface_recommendations: Dict) -> Dict:
        """Combine impacts from multiple surfaces"""
        combined = {
            'frequencies_improved': set(),
            'overall_rt60_reduction': 0,
            'frequency_impacts': {}
        }
        
        surface_count = 0
        for rec in surface_recommendations.values():
            impact = rec.get('expected_impact', {})
            if impact:
                combined['frequencies_improved'].update(impact.get('frequencies_improved', []))
                combined['overall_rt60_reduction'] += impact.get('overall_rt60_reduction', 0)
                surface_count += 1
        
        # Average the overall reduction
        if surface_count > 0:
            combined['overall_rt60_reduction'] /= surface_count
            
        combined['frequencies_improved'] = list(combined['frequencies_improved'])
        return combined
    
    def _calculate_overall_improvement(self, frequency_improvements: Dict) -> Dict:
        """Calculate overall improvement metrics"""
        total_improvement = 0
        positive_improvements = 0
        max_improvement = 0
        
        for freq_data in frequency_improvements.values():
            improvement = freq_data['improvement']
            total_improvement += improvement
            if improvement > 0:
                positive_improvements += 1
            max_improvement = max(max_improvement, improvement)
        
        return {
            'average_improvement': total_improvement / len(frequency_improvements),
            'max_improvement': max_improvement,
            'frequencies_improved': positive_improvements,
            'improvement_effectiveness': positive_improvements / len(frequency_improvements)
        }
    
    def _calculate_effectiveness_score(self, simulation: Dict) -> float:
        """Calculate effectiveness score for a simulation"""
        overall = simulation.get('overall_improvement', {})
        return overall.get('improvement_effectiveness', 0) * overall.get('average_improvement', 0)


# Convenience functions
def analyze_treatment_gaps(space_data: Dict) -> Dict:
    """Quick treatment gap analysis"""
    analyzer = TreatmentAnalyzer()
    return analyzer.analyze_treatment_gaps(space_data)

def suggest_materials_for_space(space_data: Dict, surface_types: List[str] = None) -> Dict:
    """Quick material suggestions for a space"""
    if surface_types is None:
        surface_types = ['ceiling', 'wall', 'floor']
    
    # Estimate available areas
    floor_area = space_data.get('floor_area', 500)
    available_areas = {
        'ceiling': floor_area,
        'wall': space_data.get('wall_area', floor_area * 2),
        'floor': floor_area
    }
    
    analyzer = TreatmentAnalyzer()
    return analyzer.suggest_optimal_materials(space_data, surface_types, available_areas)