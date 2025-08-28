"""
Material Search Engine - Advanced material searching with frequency-specific analysis
"""

import sqlite3
import os
from typing import Dict, List, Optional, Tuple, Any
import math
from .materials import get_database_path, STANDARD_MATERIALS, categorize_material


class MaterialSearchEngine:
    """Advanced search engine for acoustic materials with frequency-specific analysis"""
    
    def __init__(self):
        self.db_path = get_database_path()
        self.materials_cache = STANDARD_MATERIALS
        self.frequencies = [125, 250, 500, 1000, 2000, 4000]
        
    def search_materials_by_text(self, query: str, category: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        Search materials by text query
        
        Args:
            query: Search text
            category: Optional category filter ('ceiling', 'wall', 'floor')  
            limit: Maximum results to return
            
        Returns:
            List of material dictionaries
        """
        if not os.path.exists(self.db_path):
            return self._search_fallback_materials(query, category, limit)
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            sql = """
                SELECT name, coeff_125, coeff_250, coeff_500, coeff_1000, coeff_2000, coeff_4000, nrc
                FROM acoustic_materials
                WHERE name LIKE ?
            """
            params = [f"%{query}%"]
            
            if category:
                sql += " AND (name LIKE ? OR name LIKE ? OR name LIKE ?)"
                if category == 'ceiling':
                    params.extend(["%ceiling%", "%tile%", "%panel%"])
                elif category == 'floor':
                    params.extend(["%carpet%", "%floor%", "%vinyl%"])
                else:  # wall
                    params.extend(["%wall%", "%drywall%", "%acoustic%"])
            
            sql += " ORDER BY nrc DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
            
            return self._format_search_results(rows)
            
        except Exception as e:
            print(f"Error searching materials: {e}")
            return self._search_fallback_materials(query, category, limit)
    
    def search_by_frequency_absorption(self, frequency: int, min_absorption: float = 0.0, 
                                     max_absorption: float = 1.0, category: Optional[str] = None,
                                     limit: int = 50) -> List[Dict]:
        """
        Search materials by absorption coefficient at specific frequency
        
        Args:
            frequency: Frequency in Hz (125, 250, 500, 1000, 2000, 4000)
            min_absorption: Minimum absorption coefficient
            max_absorption: Maximum absorption coefficient
            category: Optional category filter
            limit: Maximum results to return
            
        Returns:
            List of materials sorted by absorption at frequency
        """
        if frequency not in self.frequencies:
            raise ValueError(f"Frequency must be one of {self.frequencies}")
            
        if not os.path.exists(self.db_path):
            return self._search_fallback_by_frequency(frequency, min_absorption, max_absorption, category, limit)
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            freq_column = f"coeff_{frequency}"
            sql = f"""
                SELECT name, coeff_125, coeff_250, coeff_500, coeff_1000, coeff_2000, coeff_4000, nrc
                FROM acoustic_materials
                WHERE {freq_column} >= ? AND {freq_column} <= ?
                ORDER BY {freq_column} DESC
                LIMIT ?
            """
            
            cursor.execute(sql, [min_absorption, max_absorption, limit])
            rows = cursor.fetchall()
            conn.close()
            
            results = self._format_search_results(rows)
            
            # Filter by category if specified
            if category:
                results = [r for r in results if r['category'] == category]
                
            return results
            
        except Exception as e:
            print(f"Error searching by frequency: {e}")
            return self._search_fallback_by_frequency(frequency, min_absorption, max_absorption, category, limit)
    
    def rank_materials_for_treatment_gap(self, current_rt60: float, target_rt60: float, 
                                       frequency: int, volume: float, surface_area: float,
                                       category: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """
        Rank materials by their effectiveness at closing an RT60 gap at specific frequency
        
        Args:
            current_rt60: Current RT60 at frequency
            target_rt60: Target RT60 at frequency
            frequency: Frequency in Hz
            volume: Room volume in cubic feet
            surface_area: Available surface area for treatment
            category: Optional category filter
            limit: Maximum results to return
            
        Returns:
            List of materials ranked by treatment effectiveness
        """
        if current_rt60 <= target_rt60:
            # Room already meets target, suggest materials with lower absorption
            return self.search_by_frequency_absorption(frequency, 0.0, 0.3, category, limit)
        
        # Calculate required additional absorption
        current_absorption = 0.161 * volume / current_rt60 if current_rt60 > 0 else 0
        target_absorption = 0.161 * volume / target_rt60 if target_rt60 > 0 else float('inf')
        additional_absorption_needed = target_absorption - current_absorption
        
        # Get all materials at this frequency
        materials = self.search_by_frequency_absorption(frequency, 0.0, 1.0, category, 200)
        
        # Score materials by effectiveness
        scored_materials = []
        for material in materials:
            freq_str = str(frequency)
            # Be robust to fallback entries without 'coefficients'
            coefficients = material.get('coefficients', {}) or {}
            absorption_coeff = coefficients.get(freq_str, material.get('absorption_coeff', material.get('nrc', 0)))
            
            if absorption_coeff <= 0:
                continue
                
            # Calculate how much absorption this material would add if applied to available area
            potential_absorption = surface_area * absorption_coeff
            
            # Score based on how well it closes the gap
            if additional_absorption_needed <= 0:
                score = 0
            else:
                # Prefer materials that get close to the needed absorption without overdoing it
                effectiveness = min(potential_absorption / additional_absorption_needed, 1.0)
                overshoot_penalty = max(0, (potential_absorption - additional_absorption_needed) / additional_absorption_needed)
                score = effectiveness - (overshoot_penalty * 0.5)
                
            material['treatment_score'] = max(0, score)
            material['potential_absorption'] = potential_absorption
            material['absorption_at_frequency'] = absorption_coeff
            scored_materials.append(material)
        
        # Sort by treatment score
        scored_materials.sort(key=lambda x: x['treatment_score'], reverse=True)
        
        return scored_materials[:limit]
    
    def find_optimal_material_combinations(self, space_data: Dict, problem_frequencies: List[int],
                                         available_surfaces: Dict[str, float]) -> Dict[str, Any]:
        """
        Find optimal material combinations to address multiple frequency problems
        
        Args:
            space_data: Current space configuration
            problem_frequencies: List of frequencies needing treatment
            available_surfaces: Dict of surface_type -> available_area
            
        Returns:
            Dict with optimization results and recommendations
        """
        volume = space_data.get('volume', 0)
        if volume <= 0:
            return {'error': 'Invalid volume'}
        
        recommendations = {
            'problem_frequencies': problem_frequencies,
            'surface_recommendations': {},
            'overall_improvement': {},
            'material_suggestions': []
        }
        
        for surface_type, available_area in available_surfaces.items():
            if available_area <= 0:
                continue
                
            category = self._surface_type_to_category(surface_type)
            surface_recommendations = []
            
            for frequency in problem_frequencies:
                # Get current RT60 at this frequency (simplified)
                current_rt60 = space_data.get(f'rt60_{frequency}', space_data.get('rt60', 1.0))
                target_rt60 = space_data.get('target_rt60', 0.6)
                
                # Find best materials for this frequency and surface
                materials = self.rank_materials_for_treatment_gap(
                    current_rt60, target_rt60, frequency, volume, available_area, category, 5
                )
                
                if materials:
                    best_material = materials[0]
                    surface_recommendations.append({
                        'frequency': frequency,
                        'material': best_material,
                        'improvement_potential': best_material.get('treatment_score', 0)
                    })
            
            if surface_recommendations:
                # Find material that works best across all problem frequencies
                material_scores = {}
                for rec in surface_recommendations:
                    material_key = rec['material']['key']
                    if material_key not in material_scores:
                        material_scores[material_key] = {
                            'material': rec['material'],
                            'total_score': 0,
                            'frequency_count': 0
                        }
                    material_scores[material_key]['total_score'] += rec['improvement_potential']
                    material_scores[material_key]['frequency_count'] += 1
                
                # Find best overall material for this surface
                best_overall = max(material_scores.values(), key=lambda x: x['total_score'])
                
                recommendations['surface_recommendations'][surface_type] = {
                    'recommended_material': best_overall['material'],
                    'average_score': best_overall['total_score'] / best_overall['frequency_count'],
                    'addresses_frequencies': best_overall['frequency_count'],
                    'frequency_details': surface_recommendations
                }
        
        return recommendations
    
    def get_material_frequency_response(self, material_key: str) -> Dict[int, float]:
        """Get absorption coefficients across all frequencies for a material"""
        if material_key in self.materials_cache:
            material = self.materials_cache[material_key]
            if 'coefficients' in material:
                return {int(freq): coeff for freq, coeff in material['coefficients'].items()}
        
        return {}
    
    def compare_materials_at_frequency(self, material_keys: List[str], frequency: int) -> List[Dict]:
        """Compare multiple materials at a specific frequency"""
        results = []
        
        for key in material_keys:
            if key in self.materials_cache:
                material = self.materials_cache[key].copy()
                freq_str = str(frequency)
                
                if 'coefficients' in material and freq_str in material['coefficients']:
                    absorption = material['coefficients'][freq_str]
                else:
                    absorption = material.get('absorption_coeff', 0)
                
                material['absorption_at_frequency'] = absorption
                material['frequency'] = frequency
                results.append(material)
        
        # Sort by absorption at frequency
        results.sort(key=lambda x: x['absorption_at_frequency'], reverse=True)
        return results
    
    def _format_search_results(self, rows: List[Tuple]) -> List[Dict]:
        """Format database rows into material dictionaries"""
        results = []
        
        for row in rows:
            name, coeff_125, coeff_250, coeff_500, coeff_1000, coeff_2000, coeff_4000, nrc = row
            
            key = name.lower().replace(' ', '_').replace(',', '').replace('(', '').replace(')', '').replace('&', 'and')
            category = categorize_material(name)
            
            material = {
                'key': key,
                'name': name,
                'nrc': nrc,
                'absorption_coeff': nrc or coeff_1000,
                'coefficients': {
                    '125': coeff_125,
                    '250': coeff_250,
                    '500': coeff_500,
                    '1000': coeff_1000,
                    '2000': coeff_2000,
                    '4000': coeff_4000
                },
                'category': category,
                'description': f"{name} - NRC: {nrc:.2f}" if nrc else name
            }
            
            results.append(material)
        
        return results
    
    def _search_fallback_materials(self, query: str, category: Optional[str], limit: int) -> List[Dict]:
        """Search fallback materials when database is unavailable"""
        results = []
        query_lower = query.lower()
        
        for key, material in self.materials_cache.items():
            if query_lower in material['name'].lower():
                if not category or material.get('category') == category:
                    material_copy = material.copy()
                    material_copy['key'] = key
                    results.append(material_copy)
        
        # Sort by NRC if available
        results.sort(key=lambda x: x.get('nrc', x.get('absorption_coeff', 0)), reverse=True)
        return results[:limit]
    
    def _search_fallback_by_frequency(self, frequency: int, min_abs: float, max_abs: float,
                                    category: Optional[str], limit: int) -> List[Dict]:
        """Search fallback materials by frequency when database unavailable"""
        results = []
        freq_str = str(frequency)
        
        for key, material in self.materials_cache.items():
            if 'coefficients' in material and freq_str in material['coefficients']:
                absorption = material['coefficients'][freq_str]
            else:
                absorption = material.get('absorption_coeff', 0)
            
            if min_abs <= absorption <= max_abs:
                if not category or material.get('category') == category:
                    material_copy = material.copy()
                    material_copy['key'] = key
                    material_copy['absorption_at_frequency'] = absorption
                    results.append(material_copy)
        
        results.sort(key=lambda x: x['absorption_at_frequency'], reverse=True)
        return results[:limit]
    
    def _surface_type_to_category(self, surface_type: str) -> str:
        """Convert surface type to material category"""
        if 'ceiling' in surface_type.lower():
            return 'ceiling'
        elif 'floor' in surface_type.lower():
            return 'floor'
        else:
            return 'wall'


# Convenience functions
def search_materials(query: str, **kwargs) -> List[Dict]:
    """Quick material search"""
    engine = MaterialSearchEngine()
    return engine.search_materials_by_text(query, **kwargs)

def find_best_materials_at_frequency(frequency: int, category: Optional[str] = None, limit: int = 10) -> List[Dict]:
    """Find best materials at specific frequency"""
    engine = MaterialSearchEngine()
    return engine.search_by_frequency_absorption(frequency, 0.0, 1.0, category, limit)

def suggest_treatment_materials(current_rt60: float, target_rt60: float, frequency: int,
                              volume: float, surface_area: float, category: Optional[str] = None) -> List[Dict]:
    """Suggest materials for RT60 treatment"""
    engine = MaterialSearchEngine()
    return engine.rank_materials_for_treatment_gap(current_rt60, target_rt60, frequency, volume, surface_area, category)