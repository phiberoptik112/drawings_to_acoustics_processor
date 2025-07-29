#!/usr/bin/env python3
"""
MVP Test Script - Test core functionality of the Acoustic Analysis Tool
"""

import sys
import os
import tempfile
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all core modules can be imported"""
    print("Testing imports...")
    
    try:
        # Core models
        from models import get_session, Project, Drawing, Space
        from models.hvac import HVACPath, HVACComponent, HVACSegment
        print("✓ Database models imported successfully")
        
        # Calculation engines
        from calculations import RT60Calculator, NoiseCalculator, HVACPathCalculator, NCRatingAnalyzer
        print("✓ Calculation engines imported successfully")
        
        # Data libraries
        from data import STANDARD_COMPONENTS, STANDARD_MATERIALS, ExcelExporter, EXCEL_EXPORT_AVAILABLE
        print(f"✓ Data libraries imported successfully (Excel available: {EXCEL_EXPORT_AVAILABLE})")
        
        # Drawing components
        from drawing import PDFViewer, DrawingOverlay, ScaleManager
        print("✓ Drawing components imported successfully")
        
        # UI components
        from ui.splash_screen import SplashScreen
        from ui.project_dashboard import ProjectDashboard
        from ui.drawing_interface import DrawingInterface
        from ui.results_widget import ResultsWidget
        print("✓ UI components imported successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False

def test_database_operations():
    """Test basic database operations"""
    print("\nTesting database operations...")
    
    try:
        from models import init_database, get_session, Project, Space
        from models.hvac import HVACPath
        
        # Initialize database in memory
        init_database("sqlite:///:memory:")
        session = get_session()
        
        # Create test project
        project = Project(
            name="Test Project",
            description="MVP Test Project"
        )
        session.add(project)
        session.flush()
        
        # Create test space
        space = Space(
            project_id=project.id,
            name="Test Office",
            floor_area=200.0,
            ceiling_height=9.0,
            volume=1800.0,
            target_rt60=0.6
        )
        session.add(space)
        
        # Create test HVAC path
        hvac_path = HVACPath(
            project_id=project.id,
            name="Test Supply Path",
            description="Test HVAC path for noise analysis"
        )
        session.add(hvac_path)
        
        session.commit()
        
        # Verify data
        projects = session.query(Project).all()
        spaces = session.query(Space).all()
        paths = session.query(HVACPath).all()
        
        session.close()
        
        assert len(projects) == 1
        assert len(spaces) == 1
        assert len(paths) == 1
        assert projects[0].name == "Test Project"
        
        print("✓ Database operations successful")
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        traceback.print_exc()
        return False

def test_calculation_engines():
    """Test calculation engines"""
    print("\nTesting calculation engines...")
    
    try:
        from calculations import RT60Calculator, NoiseCalculator, NCRatingAnalyzer
        
        # Test RT60 Calculator
        rt60_calc = RT60Calculator()
        
        space_data = {
            'volume': 1000,  # cubic feet
            'ceiling_area': 200,
            'wall_area': 400,
            'floor_area': 200,
            'ceiling_material': 'acoustic_tile',
            'wall_material': 'painted_concrete',
            'floor_material': 'carpet'
        }
        
        rt60_result = rt60_calc.calculate_space_rt60(space_data)
        assert rt60_result is not None
        assert 'rt60' in rt60_result
        assert rt60_result['rt60'] > 0
        
        print(f"✓ RT60 calculation: {rt60_result['rt60']:.2f} seconds")
        
        # Test Noise Calculator
        noise_calc = NoiseCalculator()
        
        path_data = {
            'source_component': {'component_type': 'ahu', 'noise_level': 65.0},
            'terminal_component': {'component_type': 'diffuser', 'noise_level': 30.0},
            'segments': [
                {
                    'length': 50.0,
                    'duct_width': 12,
                    'duct_height': 8,
                    'duct_type': 'sheet_metal',
                    'fittings': []
                }
            ]
        }
        
        noise_result = noise_calc.calculate_hvac_path_noise(path_data)
        assert noise_result is not None
        assert 'terminal_noise' in noise_result
        assert 'nc_rating' in noise_result
        
        print(f"✓ HVAC noise calculation: {noise_result['terminal_noise']:.1f} dB(A), NC-{noise_result['nc_rating']}")
        
        # Test NC Rating Analyzer
        nc_analyzer = NCRatingAnalyzer()
        
        # Test simple NC rating
        nc_rating = nc_analyzer.determine_nc_rating([60, 52, 45, 40, 36, 34, 33, 32])
        assert nc_rating == 35  # This should match NC-35 curve
        
        # Test octave band estimation
        octave_data = nc_analyzer.estimate_octave_bands_from_dba(40.0, "typical_hvac")
        assert octave_data is not None
        
        print(f"✓ NC analysis: Determined rating NC-{nc_rating}")
        
        return True
        
    except Exception as e:
        print(f"✗ Calculation engines test failed: {e}")
        traceback.print_exc()
        return False

def test_data_libraries():
    """Test data libraries"""
    print("\nTesting data libraries...")
    
    try:
        from data import STANDARD_COMPONENTS, STANDARD_MATERIALS, STANDARD_FITTINGS
        
        # Test component library
        assert 'ahu' in STANDARD_COMPONENTS
        assert 'diffuser' in STANDARD_COMPONENTS
        assert STANDARD_COMPONENTS['ahu']['noise_level'] > 0
        
        print(f"✓ Component library: {len(STANDARD_COMPONENTS)} components")
        
        # Test materials library
        assert 'acoustic_tile' in STANDARD_MATERIALS
        assert 'carpet' in STANDARD_MATERIALS
        assert len(STANDARD_MATERIALS['acoustic_tile']['absorption_coeffs']) == 6
        
        print(f"✓ Materials library: {len(STANDARD_MATERIALS)} materials")
        
        # Test fittings library
        assert 'elbow_90' in STANDARD_FITTINGS
        assert STANDARD_FITTINGS['elbow_90']['noise_adjustment'] > 0
        
        print(f"✓ Fittings library: {len(STANDARD_FITTINGS)} fittings")
        
        return True
        
    except Exception as e:
        print(f"✗ Data libraries test failed: {e}")
        traceback.print_exc()
        return False

def test_excel_export():
    """Test Excel export functionality"""
    print("\nTesting Excel export...")
    
    try:
        from data import ExcelExporter, EXCEL_EXPORT_AVAILABLE
        
        if not EXCEL_EXPORT_AVAILABLE:
            print("⚠ Excel export not available (openpyxl not installed)")
            return True
        
        # Create test database
        from models import init_database, get_session, Project, Space
        
        init_database("sqlite:///:memory:")
        session = get_session()
        
        # Create test project with data
        project = Project(name="Export Test", description="Test export functionality")
        session.add(project)
        session.flush()
        
        space = Space(
            project_id=project.id,
            name="Test Room",
            floor_area=150.0,
            ceiling_height=9.0,
            calculated_rt60=0.65
        )
        session.add(space)
        session.commit()
        session.close()
        
        # Test export summary
        exporter = ExcelExporter()
        summary = exporter.get_export_summary(project.id)
        
        assert 'project_name' in summary
        assert summary['project_name'] == "Export Test"
        assert summary['total_spaces'] == 1
        
        print("✓ Excel export summary generated successfully")
        
        # Test actual export to temporary file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            success = exporter.export_project_analysis(project.id, tmp_path)
            assert success, "Export should succeed"
            
            # Verify file was created
            assert os.path.exists(tmp_path), "Export file should exist"
            assert os.path.getsize(tmp_path) > 1000, "Export file should have content"
            
            print("✓ Excel export file created successfully")
            
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        return True
        
    except Exception as e:
        print(f"✗ Excel export test failed: {e}")
        traceback.print_exc()
        return False

def test_gui_components():
    """Test GUI components (without actually showing them)"""
    print("\nTesting GUI components...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from ui.splash_screen import SplashScreen
        from ui.results_widget import ResultsWidget
        
        # Create QApplication if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Test splash screen creation
        splash = SplashScreen()
        assert splash is not None
        print("✓ Splash screen created successfully")
        
        # Test results widget (requires project)
        from models import init_database, get_session, Project
        
        init_database("sqlite:///:memory:")
        session = get_session()
        
        project = Project(name="GUI Test", description="Test GUI components")
        session.add(project)
        session.flush()
        project_id = project.id
        session.commit()
        session.close()
        
        results_widget = ResultsWidget(project_id)
        assert results_widget is not None
        print("✓ Results widget created successfully")
        
        # Clean up
        splash.close()
        results_widget.close()
        
        return True
        
    except Exception as e:
        print(f"✗ GUI components test failed: {e}")
        traceback.print_exc()
        return False

def run_mvp_tests():
    """Run all MVP tests"""
    print("=" * 60)
    print("ACOUSTIC ANALYSIS TOOL - MVP TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Core Imports", test_imports),
        ("Database Operations", test_database_operations),
        ("Calculation Engines", test_calculation_engines),
        ("Data Libraries", test_data_libraries),
        ("Excel Export", test_excel_export),
        ("GUI Components", test_gui_components)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n[{test_name}]")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                failed += 1
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Passed: {passed}")
    print(f"Tests Failed: {failed}")
    print(f"Total Tests: {passed + failed}")
    
    if failed > 0:
        print("\n⚠ Some tests failed. Review the output above for details.")
        return False
    else:
        print("\n🎉 All tests passed! MVP is ready for use.")
        return True

if __name__ == "__main__":
    success = run_mvp_tests()
    sys.exit(0 if success else 1)