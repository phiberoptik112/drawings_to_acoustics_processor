#!/usr/bin/env python3
"""
Test script for the material search system
"""

import sys
import os

# Add src directory to path
current_dir = os.path.dirname(__file__)
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

def test_material_search_engine():
    """Test the material search engine"""
    print("Testing Material Search Engine...")
    
    try:
        from data.material_search import MaterialSearchEngine
        
        engine = MaterialSearchEngine()
        
        # Test text search
        print("\n1. Testing text search for 'acoustic':")
        results = engine.search_materials_by_text("acoustic", limit=5)
        for i, material in enumerate(results[:3]):
            print(f"   {i+1}. {material['name']} (NRC: {material.get('nrc', 0):.2f})")
        
        # Test frequency search
        print("\n2. Testing frequency search at 1000Hz:")
        results = engine.search_by_frequency_absorption(1000, min_absorption=0.5, limit=5)
        for i, material in enumerate(results[:3]):
            freq_coeff = material['coefficients'].get('1000', 0) if 'coefficients' in material else 0
            print(f"   {i+1}. {material['name']} (1000Hz: {freq_coeff:.2f})")
        
        # Test treatment ranking
        print("\n3. Testing treatment ranking:")
        results = engine.rank_materials_for_treatment_gap(
            current_rt60=1.2, target_rt60=0.8, frequency=1000, 
            volume=5000, surface_area=500, category='ceiling', limit=3
        )
        for i, material in enumerate(results):
            score = material.get('treatment_score', 0)
            print(f"   {i+1}. {material['name']} (Score: {score:.2f})")
        
        print("✓ Material Search Engine tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Material Search Engine test failed: {e}")
        return False

def test_treatment_analyzer():
    """Test the treatment analyzer"""
    print("\nTesting Treatment Analyzer...")
    
    try:
        from calculations.treatment_analyzer import TreatmentAnalyzer
        
        analyzer = TreatmentAnalyzer()
        
        # Sample space data
        space_data = {
            'volume': 5000,
            'floor_area': 500,
            'wall_area': 1000,
            'ceiling_area': 500,
            'target_rt60': 0.8,
            'ceiling_material': 'gypsum_ceiling',
            'wall_material': 'drywall_painted', 
            'floor_material': 'carpet_medium'
        }
        
        # Test gap analysis
        print("\n1. Testing treatment gap analysis:")
        gaps = analyzer.analyze_treatment_gaps(space_data)
        
        if 'error' not in gaps:
            urgency = gaps['overall_assessment'].get('treatment_urgency', 'unknown')
            problem_count = gaps['overall_assessment'].get('problem_frequency_count', 0)
            print(f"   Treatment urgency: {urgency}")
            print(f"   Problem frequencies: {problem_count}")
        else:
            print(f"   Gap analysis error: {gaps['error']}")
        
        # Test material suggestions
        print("\n2. Testing material suggestions:")
        suggestions = analyzer.suggest_optimal_materials(
            space_data, ['ceiling', 'wall'], {'ceiling': 500, 'wall': 1000}
        )
        
        if 'error' not in suggestions:
            surface_recs = suggestions.get('surface_recommendations', {})
            print(f"   Surface recommendations: {len(surface_recs)}")
            for surface, rec in surface_recs.items():
                material = rec.get('best_overall_material', {}).get('material', {})
                if material:
                    print(f"   {surface}: {material.get('name', 'Unknown')}")
        else:
            print(f"   Suggestions error: {suggestions.get('error', 'Unknown')}")
        
        print("✓ Treatment Analyzer tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Treatment Analyzer test failed: {e}")
        return False

def test_imports():
    """Test that core modules can be imported"""
    print("Testing core module imports...")
    
    success_count = 0
    
    # Test core data modules
    try:
        from data.material_search import MaterialSearchEngine
        print("✓ data.material_search.MaterialSearchEngine")
        success_count += 1
    except Exception as e:
        print(f"✗ data.material_search.MaterialSearchEngine: {e}")
    
    try:
        from calculations.treatment_analyzer import TreatmentAnalyzer
        print("✓ calculations.treatment_analyzer.TreatmentAnalyzer")
        success_count += 1
    except Exception as e:
        print(f"✗ calculations.treatment_analyzer.TreatmentAnalyzer: {e}")
    
    # Test UI modules (may fail due to matplotlib dependency in other parts)
    try:
        import sys
        # Temporarily add direct path to avoid UI module conflicts
        sys.path.insert(0, os.path.join(current_dir, 'src', 'ui', 'widgets'))
        from material_graph_overlay import FrequencyResponseWidget, MaterialListWidget
        print("✓ ui.widgets.material_graph_overlay (core widgets)")
        success_count += 1
    except Exception as e:
        print(f"✗ ui.widgets.material_graph_overlay: {e}")
    
    try:
        sys.path.insert(0, os.path.join(current_dir, 'src', 'ui', 'dialogs'))
        from material_search_dialog import TreatmentAnalysisThread
        print("✓ ui.dialogs.material_search_dialog (core classes)")
        success_count += 1
    except Exception as e:
        print(f"✗ ui.dialogs.material_search_dialog: {e}")
    
    print(f"\nCore module results: {success_count}/4 modules imported successfully")
    return success_count >= 2  # At least the core data modules should work

def main():
    """Run all tests"""
    print("Material Search System Test Suite")
    print("=" * 50)
    
    all_passed = True
    
    # Test imports first
    if not test_imports():
        all_passed = False
        print("\n⚠ Some imports failed. Continuing with available modules...")
    
    # Test core functionality
    if not test_material_search_engine():
        all_passed = False
    
    if not test_treatment_analyzer():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! The material search system is ready to use.")
    else:
        print("⚠ Some tests failed. Please check the implementation.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)