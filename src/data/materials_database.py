"""
Materials Database Utility - Centralized access to all acoustic materials
"""

from typing import Dict, List, Optional, Tuple, Union
import os

try:
    from .materials import STANDARD_MATERIALS, load_materials_from_database, get_materials_by_category, categorize_material
    from .enhanced_materials import ENHANCED_MATERIALS
except ImportError:
    try:
        from materials import STANDARD_MATERIALS, load_materials_from_database, get_materials_by_category, categorize_material
        from enhanced_materials import ENHANCED_MATERIALS
    except ImportError:
        import sys
        sys.path.append(os.path.dirname(__file__))
        from materials import STANDARD_MATERIALS, load_materials_from_database, get_materials_by_category, categorize_material
        from enhanced_materials import ENHANCED_MATERIALS


class MaterialsDatabase:
    """Centralized interface for accessing all acoustic materials"""
    
    def __init__(self):
        """Initialize the materials database"""
        self.standard_materials = STANDARD_MATERIALS
        self.enhanced_materials = ENHANCED_MATERIALS
        self.frequencies = [125, 250, 500, 1000, 2000, 4000]
        self._sqlalchemy_materials_cache = None
        
    def load_materials_from_sqlalchemy(self) -> Dict[str, Dict]:
        """Load materials from SQLAlchemy AcousticMaterial model (Component Library)
        
        Returns:
            Dictionary of materials in standard format, keyed by material key
        """
        materials = {}
        
        try:
            from models import get_session
            from models.rt60_models import AcousticMaterial
            
            session = get_session()
            try:
                acoustic_materials = session.query(AcousticMaterial).all()
                
                for mat in acoustic_materials:
                    # Generate key from material name (same format as SQLite loader)
                    key = mat.name.lower().replace(' ', '_').replace(',', '').replace('(', '').replace(')', '').replace('&', 'and')
                    
                    # Determine category
                    if mat.category:
                        # Map SurfaceCategory name to standard category
                        cat_name = mat.category.name.lower()
                        if 'ceiling' in cat_name or 'ceiling' in mat.name.lower():
                            category = 'ceiling'
                        elif 'floor' in cat_name or any(term in mat.name.lower() for term in ['carpet', 'floor', 'vinyl', 'concrete', 'wood', 'rubber', 'ceramic']):
                            category = 'floor'
                        else:
                            category = 'wall'
                    else:
                        # Fallback to name-based categorization
                        category = categorize_material(mat.name)
                    
                    # Build description
                    desc_parts = [mat.name]
                    if mat.nrc is not None:
                        desc_parts.append(f"NRC: {mat.nrc:.2f}")
                    if mat.manufacturer:
                        desc_parts.append(f"Mfr: {mat.manufacturer}")
                    description = " - ".join(desc_parts)
                    
                    # Convert to standard format
                    materials[key] = {
                        'name': mat.name,
                        'absorption_coeff': mat.nrc or (mat.absorption_1000 if mat.absorption_1000 is not None else 0.0),
                        'coefficients': {
                            '125': mat.absorption_125 or 0.0,
                            '250': mat.absorption_250 or 0.0,
                            '500': mat.absorption_500 or 0.0,
                            '1000': mat.absorption_1000 or 0.0,
                            '2000': mat.absorption_2000 or 0.0,
                            '4000': mat.absorption_4000 or 0.0
                        },
                        'nrc': mat.nrc,
                        'description': description,
                        'category': category,
                        'manufacturer': mat.manufacturer,
                        'mounting_type': mat.mounting_type,
                        'thickness': mat.thickness,
                        'source': 'component_library'  # Mark as from Component Library
                    }
                
            finally:
                session.close()
                
        except Exception as e:
            # Silently fail if SQLAlchemy models aren't available or database isn't initialized
            # This allows the system to work even if Component Library isn't set up
            pass
        
        return materials
        
    def get_all_materials(self) -> Dict[str, Dict]:
        """Get all materials from SQLite database, SQLAlchemy Component Library, and enhanced materials
        
        Merges all sources with priority:
        1. SQLAlchemy Component Library materials (highest priority - can override)
        2. Enhanced materials
        3. Standard SQLite materials (lowest priority)
        """
        all_materials = {}
        
        # Start with standard SQLite materials (lowest priority)
        all_materials.update(self.standard_materials)
        
        # Add enhanced materials (medium priority - can override standard)
        for key, material in self.enhanced_materials.items():
            # Convert enhanced material format to standard format
            standardized = self._standardize_enhanced_material(key, material)
            all_materials[key] = standardized
        
        # Add SQLAlchemy Component Library materials (highest priority - can override both)
        sqlalchemy_materials = self.load_materials_from_sqlalchemy()
        for key, material in sqlalchemy_materials.items():
            all_materials[key] = material
            
        return all_materials
        
    def _standardize_enhanced_material(self, key: str, enhanced_material: Dict) -> Dict:
        """Convert enhanced material format to standard material format"""
        # Calculate NRC from absorption coefficients
        coefficients = enhanced_material.get('absorption_coefficients', {})
        nrc = self.calculate_nrc_from_coefficients(coefficients)
        
        # Use 1000Hz coefficient as default absorption coefficient
        default_coeff = coefficients.get(1000, nrc)
        
        # Convert to standard format
        standardized = {
            'name': enhanced_material.get('name', key),
            'absorption_coeff': default_coeff,
            'coefficients': {str(freq): coefficients.get(freq, default_coeff) for freq in self.frequencies},
            'nrc': nrc,
            'description': enhanced_material.get('description', enhanced_material.get('name', key)),
            'category': enhanced_material.get('category', 'wall'),
            'manufacturer': enhanced_material.get('manufacturer', 'Generic'),
            'mounting_type': enhanced_material.get('mounting_type', 'direct')
        }
        
        return standardized
        
    def get_materials_by_category(self, category: str) -> Dict[str, Dict]:
        """Get materials filtered by category (ceiling, wall, floor, doors, windows)"""
        all_materials = self.get_all_materials()
        
        if category in ['doors', 'windows']:
            # For doors and windows, get from enhanced materials
            return {k: v for k, v in all_materials.items() 
                   if v.get('category') == category}
        else:
            # For standard categories, use the existing function but merge with enhanced
            standard_filtered = get_materials_by_category(category)
            enhanced_filtered = {k: v for k, v in all_materials.items() 
                               if v.get('category') == category and k in self.enhanced_materials}
            
            # Merge and return
            result = {}
            result.update(standard_filtered)
            result.update(enhanced_filtered)
            return result
            
    def get_material(self, material_key: str) -> Optional[Dict]:
        """Get a specific material by key"""
        all_materials = self.get_all_materials()
        return all_materials.get(material_key)
        
    def get_material_coefficient(self, material_key: str, frequency: int) -> float:
        """Get absorption coefficient for a material at specific frequency"""
        material = self.get_material(material_key)
        if not material:
            return 0.0
            
        # Check for frequency-specific coefficient
        if 'coefficients' in material:
            coeff = material['coefficients'].get(str(frequency))
            if coeff is not None:
                return coeff
                
        # Fall back to NRC or general absorption coefficient
        return material.get('nrc', material.get('absorption_coeff', 0.0))
        
    def calculate_nrc_from_coefficients(self, coefficients: Dict[int, float]) -> float:
        """Calculate NRC (Noise Reduction Coefficient) from octave band coefficients"""
        if not coefficients:
            return 0.0
            
        # NRC is the average of 250, 500, 1000, and 2000 Hz coefficients
        nrc_frequencies = [250, 500, 1000, 2000]
        total = sum(coefficients.get(freq, 0) for freq in nrc_frequencies)
        return total / 4.0
        
    def get_frequency_response(self, material_key: str) -> Dict[int, float]:
        """Get frequency response for a material across all octave bands"""
        material = self.get_material(material_key)
        if not material:
            return {freq: 0.0 for freq in self.frequencies}
            
        response = {}
        for freq in self.frequencies:
            response[freq] = self.get_material_coefficient(material_key, freq)
            
        return response
        
    def search_materials(self, search_term: str, category: Optional[str] = None) -> Dict[str, Dict]:
        """Search materials by name or description"""
        search_lower = search_term.lower()
        
        if category:
            materials = self.get_materials_by_category(category)
        else:
            materials = self.get_all_materials()
            
        results = {}
        for key, material in materials.items():
            name_match = search_lower in material['name'].lower()
            desc_match = search_lower in material.get('description', '').lower()
            
            if name_match or desc_match:
                results[key] = material
                
        return results
        
    def get_material_categories(self) -> List[str]:
        """Get list of all available material categories"""
        all_materials = self.get_all_materials()
        categories = set()
        
        for material in all_materials.values():
            category = material.get('category', 'wall')
            categories.add(category)
            
        return sorted(list(categories))
        
    def validate_material_key(self, material_key: str) -> bool:
        """Check if a material key exists in the database"""
        return material_key in self.get_all_materials()
        
    def get_material_summary(self, material_key: str) -> str:
        """Get a formatted summary of a material's properties"""
        material = self.get_material(material_key)
        if not material:
            return f"Material '{material_key}' not found"
            
        summary = f"Material: {material['name']}\n"
        summary += f"Category: {material.get('category', 'Unknown').title()}\n"
        summary += f"NRC: {material.get('nrc', 0):.2f}\n"
        
        if 'coefficients' in material:
            summary += "Absorption Coefficients:\n"
            for freq in self.frequencies:
                coeff = material['coefficients'].get(str(freq), 0)
                summary += f"  {freq}Hz: {coeff:.2f}\n"
                
        if 'description' in material:
            summary += f"Description: {material['description']}\n"
            
        if 'manufacturer' in material:
            summary += f"Manufacturer: {material['manufacturer']}\n"
            
        return summary
        
    def export_materials_list(self, category: Optional[str] = None, 
                            include_coefficients: bool = True) -> List[Dict]:
        """Export materials list for external use (e.g., Excel export)"""
        if category:
            materials = self.get_materials_by_category(category)
        else:
            materials = self.get_all_materials()
            
        export_list = []
        for key, material in materials.items():
            export_item = {
                'key': key,
                'name': material['name'],
                'category': material.get('category', 'Unknown'),
                'nrc': material.get('nrc', 0),
                'absorption_coeff': material.get('absorption_coeff', 0),
                'description': material.get('description', ''),
                'manufacturer': material.get('manufacturer', 'Generic')
            }
            
            if include_coefficients and 'coefficients' in material:
                for freq in self.frequencies:
                    export_item[f'coeff_{freq}hz'] = material['coefficients'].get(str(freq), 0)
                    
            export_list.append(export_item)
            
        return export_list
        
    def get_doors_windows_materials(self) -> Dict[str, Dict]:
        """Get all door and window materials"""
        doors = self.get_materials_by_category('doors')
        windows = self.get_materials_by_category('windows')
        
        result = {}
        result.update(doors)
        result.update(windows)
        return result
        
    def calculate_surface_absorption(self, material_key: str, area: float, 
                                   frequency: Optional[int] = None) -> Union[float, Dict[int, float]]:
        """Calculate absorption for a surface area with given material"""
        if frequency:
            # Calculate for specific frequency
            coeff = self.get_material_coefficient(material_key, frequency)
            return area * coeff
        else:
            # Calculate for all frequencies
            result = {}
            for freq in self.frequencies:
                coeff = self.get_material_coefficient(material_key, freq)
                result[freq] = area * coeff
            return result
            
    def get_material_recommendations(self, target_nrc: float, 
                                   category: Optional[str] = None,
                                   tolerance: float = 0.1) -> List[Tuple[str, Dict, float]]:
        """Get materials that match a target NRC within tolerance"""
        if category:
            materials = self.get_materials_by_category(category)
        else:
            materials = self.get_all_materials()
            
        recommendations = []
        for key, material in materials.items():
            material_nrc = material.get('nrc', 0)
            difference = abs(material_nrc - target_nrc)
            
            if difference <= tolerance:
                recommendations.append((key, material, difference))
                
        # Sort by closest match
        recommendations.sort(key=lambda x: x[2])
        return recommendations


# Global instance for easy access
_materials_db = None

def get_materials_database() -> MaterialsDatabase:
    """Get the global materials database instance"""
    global _materials_db
    if _materials_db is None:
        _materials_db = MaterialsDatabase()
    return _materials_db

def get_material_coefficient(material_key: str, frequency: int) -> float:
    """Convenience function to get material coefficient"""
    db = get_materials_database()
    return db.get_material_coefficient(material_key, frequency)

def get_all_materials() -> Dict[str, Dict]:
    """Convenience function to get all materials"""
    db = get_materials_database()
    return db.get_all_materials()

def search_materials(search_term: str, category: Optional[str] = None) -> Dict[str, Dict]:
    """Convenience function to search materials"""
    db = get_materials_database()
    return db.search_materials(search_term, category)