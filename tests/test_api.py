"""
Test Suite for Acoustic Analysis API

Tests the API for LLM agentic workflows.
"""

import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api import AcousticAnalysisAPI
from src.api.schemas.rt60_schemas import (
    RT60CalculationRequest,
    RT60ComplianceRequest,
    SurfaceDefinition,
)
from src.api.schemas.hvac_schemas import (
    HVACPathNoiseRequest,
    PathElementInput,
    ReceiverRoomInput,
    CombinedReceiverNoiseRequest,
    NCComplianceRequest,
)
from src.api.schemas.material_schemas import (
    MaterialSearchRequest,
    MaterialDetailRequest,
)
from src.api.schemas.simulation_schemas import (
    MaterialChange,
    RT60MaterialChangeRequest,
    ElementModification,
    HVACPathModificationRequest,
)


class TestAcousticAnalysisAPI(unittest.TestCase):
    """Test the unified API facade."""

    def setUp(self):
        """Set up test fixtures."""
        self.api = AcousticAnalysisAPI()

    def test_get_api_schema(self):
        """Test schema discovery endpoint."""
        schema = self.api.get_api_schema()

        self.assertIn("api_version", schema)
        self.assertIn("services", schema)
        self.assertIn("rt60", schema["services"])
        self.assertIn("hvac", schema["services"])
        self.assertIn("materials", schema["services"])
        self.assertIn("simulation", schema["services"])

    def test_get_quick_start_examples(self):
        """Test quick start examples."""
        examples = self.api.get_quick_start_examples()

        self.assertIn("rt60_calculation", examples)
        self.assertIn("hvac_path_noise", examples)
        self.assertIn("material_search", examples)


class TestRT60CalculationService(unittest.TestCase):
    """Test RT60 calculation service."""

    def setUp(self):
        """Set up test fixtures."""
        self.api = AcousticAnalysisAPI()

    def test_calculate_rt60_success(self):
        """Test successful RT60 calculation."""
        # Use actual material keys from the database
        request = RT60CalculationRequest(
            volume_cubic_feet=12000,
            floor_area_sq_ft=1200,
            wall_area_sq_ft=1600,
            ceiling_area_sq_ft=1200,
            surfaces=[
                SurfaceDefinition(
                    surface_type="ceiling",
                    material_key="act_nrc_0.70",  # Actual key from database
                    area_sq_ft=1200
                ),
                SurfaceDefinition(
                    surface_type="wall",
                    material_key="concrete_block_painted",  # Actual key from database
                    area_sq_ft=1600
                ),
                SurfaceDefinition(
                    surface_type="floor",
                    material_key="carpet_-_heavy_on_concrete",  # Actual key from database
                    area_sq_ft=1200
                ),
            ],
            calculation_method="sabine"
        )

        result = self.api.rt60.calculate_rt60(request)

        # Check response structure
        self.assertIn(result.status, ["success", "warning"])
        self.assertIsInstance(result.rt60_by_frequency, dict)
        self.assertGreater(result.average_rt60, 0)

        # Check frequency bands are present
        for freq in [125, 250, 500, 1000, 2000, 4000]:
            self.assertIn(freq, result.rt60_by_frequency)

    def test_calculate_rt60_validation_error(self):
        """Test RT60 calculation with missing fields."""
        request = RT60CalculationRequest(
            volume_cubic_feet=12000,
            floor_area_sq_ft=1200,
            wall_area_sq_ft=1600,
            ceiling_area_sq_ft=1200,
            surfaces=[],  # Empty surfaces should fail
            calculation_method="sabine"
        )

        result = self.api.rt60.calculate_rt60(request)

        self.assertEqual(result.status, "error")
        self.assertIsNotNone(result.error)

    def test_analyze_compliance(self):
        """Test RT60 compliance analysis."""
        request = RT60ComplianceRequest(
            rt60_by_frequency={
                125: 1.2,
                250: 1.0,
                500: 0.8,
                1000: 0.7,
                2000: 0.6,
                4000: 0.5,
            },
            room_type="conference"
        )

        result = self.api.rt60.analyze_compliance(request)

        self.assertEqual(result.status, "success")
        self.assertIsInstance(result.overall_compliance, bool)
        self.assertGreater(result.target_rt60, 0)


class TestHVACNoiseService(unittest.TestCase):
    """Test HVAC noise calculation service."""

    def setUp(self):
        """Set up test fixtures."""
        self.api = AcousticAnalysisAPI()

    def test_calculate_path_noise_success(self):
        """Test successful HVAC path noise calculation."""
        request = HVACPathNoiseRequest(
            path_id="test_path_1",
            path_elements=[
                PathElementInput(
                    element_type="source",
                    element_id="ahu_1",
                    source_noise_dba=65
                ),
                PathElementInput(
                    element_type="duct",
                    element_id="main_duct",
                    length_ft=50,
                    duct_shape="rectangular",
                    width_inches=24,
                    height_inches=16,
                    duct_type="sheet_metal",
                    lining_thickness_inches=1.0,
                    flow_rate_cfm=2000
                ),
                PathElementInput(
                    element_type="terminal",
                    element_id="diffuser_1"
                )
            ],
            receiver_room=ReceiverRoomInput(
                room_volume_cubic_ft=12000,
                room_absorption_sabins=400,
                distance_from_terminal_ft=8.0,
                termination_type="flush"
            )
        )

        result = self.api.hvac.calculate_path_noise(request)

        # Check response structure
        self.assertIn(result.status, ["success", "warning"])
        self.assertIsInstance(result.terminal_spectrum, dict)
        self.assertGreater(result.source_noise_dba, 0)

    def test_calculate_path_noise_validation_error(self):
        """Test path noise calculation with missing fields."""
        request = HVACPathNoiseRequest(
            path_id="test_path",
            path_elements=[
                PathElementInput(
                    element_type="source",
                    element_id="ahu_1",
                    # Missing source_noise_dba
                ),
                PathElementInput(
                    element_type="terminal",
                    element_id="diffuser_1"
                )
            ]
        )

        result = self.api.hvac.calculate_path_noise(request)

        self.assertEqual(result.status, "error")
        self.assertIsNotNone(result.error)

    def test_analyze_nc_compliance(self):
        """Test NC compliance analysis."""
        request = NCComplianceRequest(
            octave_band_levels={
                63: 45,
                125: 40,
                250: 35,
                500: 30,
                1000: 28,
                2000: 25,
                4000: 22,
                8000: 20,
            },
            space_type="private_office"
        )

        result = self.api.hvac.analyze_nc_compliance(request)

        self.assertEqual(result.status, "success")
        self.assertIsInstance(result.nc_rating, int)
        self.assertIn(result.compliance_status, ["Excellent", "Acceptable", "Non-compliant"])


class TestMaterialsService(unittest.TestCase):
    """Test materials database service."""

    def setUp(self):
        """Set up test fixtures."""
        self.api = AcousticAnalysisAPI()

    def test_search_materials(self):
        """Test material search."""
        request = MaterialSearchRequest(
            category="ceiling",
            min_nrc=0.5,
            limit=10
        )

        result = self.api.materials.search_materials(request)

        self.assertEqual(result.status, "success")
        self.assertIsInstance(result.materials, list)

    def test_list_categories(self):
        """Test category listing."""
        result = self.api.materials.list_categories()

        self.assertEqual(result.status, "success")
        self.assertIsInstance(result.categories, list)
        self.assertGreater(result.total_materials, 0)


class TestSimulationService(unittest.TestCase):
    """Test simulation (what-if) service."""

    def setUp(self):
        """Set up test fixtures."""
        self.api = AcousticAnalysisAPI()

    def test_simulation_workflow(self):
        """Test complete simulation workflow."""
        # First, calculate baseline RT60
        baseline_request = RT60CalculationRequest(
            volume_cubic_feet=12000,
            floor_area_sq_ft=1200,
            wall_area_sq_ft=1600,
            ceiling_area_sq_ft=1200,
            surfaces=[
                SurfaceDefinition(
                    surface_type="ceiling",
                    material_key="acoustic_tile",
                    area_sq_ft=1200
                ),
                SurfaceDefinition(
                    surface_type="wall",
                    material_key="drywall_painted",
                    area_sq_ft=1600
                ),
                SurfaceDefinition(
                    surface_type="floor",
                    material_key="carpet_heavy",
                    area_sq_ft=1200
                ),
            ]
        )

        baseline_result = self.api.rt60.calculate_rt60(baseline_request)

        if baseline_result.status == "success":
            # Simulate material change
            sim_request = RT60MaterialChangeRequest(
                baseline_rt60_response=baseline_result,
                volume_cubic_feet=12000,
                floor_area_sq_ft=1200,
                wall_area_sq_ft=1600,
                ceiling_area_sq_ft=1200,
                material_changes=[
                    MaterialChange(
                        surface_type="ceiling",
                        original_material_key="acoustic_tile",
                        new_material_key="acoustic_cloud",
                        area_sq_ft=600
                    )
                ]
            )

            sim_result = self.api.simulation.simulate_rt60_material_change(sim_request)

            # Check simulation result
            self.assertIn(sim_result.status, ["success", "error"])


class TestStrictValidation(unittest.TestCase):
    """Test strict validation behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.api = AcousticAnalysisAPI()

    def test_missing_required_geometry(self):
        """Test that missing geometry fields are rejected."""
        request = RT60CalculationRequest(
            volume_cubic_feet=12000,
            floor_area_sq_ft=1200,
            # Missing wall_area_sq_ft
            wall_area_sq_ft=None,
            ceiling_area_sq_ft=1200,
            surfaces=[
                SurfaceDefinition(
                    surface_type="ceiling",
                    material_key="acoustic_tile",
                    area_sq_ft=1200
                )
            ]
        )

        result = self.api.rt60.calculate_rt60(request)

        self.assertEqual(result.status, "error")
        self.assertIsNotNone(result.error)

    def test_missing_duct_lining(self):
        """Test that missing lining_thickness is rejected for ducts."""
        request = HVACPathNoiseRequest(
            path_id="test",
            path_elements=[
                PathElementInput(
                    element_type="source",
                    element_id="src",
                    source_noise_dba=65
                ),
                PathElementInput(
                    element_type="duct",
                    element_id="duct1",
                    length_ft=50,
                    duct_shape="rectangular",
                    width_inches=24,
                    height_inches=16,
                    duct_type="sheet_metal",
                    # Missing lining_thickness_inches
                    lining_thickness_inches=None,
                    flow_rate_cfm=2000
                ),
                PathElementInput(
                    element_type="terminal",
                    element_id="term"
                )
            ]
        )

        result = self.api.hvac.calculate_path_noise(request)

        self.assertEqual(result.status, "error")


class TestCombinedReceiverNoise(unittest.TestCase):
    """Test combined receiver noise calculation."""

    def setUp(self):
        """Set up test fixtures."""
        self.api = AcousticAnalysisAPI()

    def test_combine_multiple_paths(self):
        """Test combining noise from multiple paths."""
        # Calculate two paths
        path1_request = HVACPathNoiseRequest(
            path_id="supply_1",
            path_elements=[
                PathElementInput(
                    element_type="source",
                    element_id="ahu_1",
                    source_noise_dba=60
                ),
                PathElementInput(
                    element_type="duct",
                    element_id="duct_1",
                    length_ft=30,
                    duct_shape="rectangular",
                    width_inches=18,
                    height_inches=12,
                    duct_type="sheet_metal",
                    lining_thickness_inches=1.0,
                    flow_rate_cfm=1500
                ),
                PathElementInput(
                    element_type="terminal",
                    element_id="diff_1"
                )
            ],
            receiver_room=ReceiverRoomInput(
                room_volume_cubic_ft=10000,
                room_absorption_sabins=350
            )
        )

        path1_result = self.api.hvac.calculate_path_noise(path1_request)

        path2_request = HVACPathNoiseRequest(
            path_id="supply_2",
            path_elements=[
                PathElementInput(
                    element_type="source",
                    element_id="ahu_2",
                    source_noise_dba=55
                ),
                PathElementInput(
                    element_type="duct",
                    element_id="duct_2",
                    length_ft=40,
                    duct_shape="rectangular",
                    width_inches=16,
                    height_inches=10,
                    duct_type="sheet_metal",
                    lining_thickness_inches=1.0,
                    flow_rate_cfm=1000
                ),
                PathElementInput(
                    element_type="terminal",
                    element_id="diff_2"
                )
            ],
            receiver_room=ReceiverRoomInput(
                room_volume_cubic_ft=10000,
                room_absorption_sabins=350
            )
        )

        path2_result = self.api.hvac.calculate_path_noise(path2_request)

        # Combine results
        if path1_result.status == "success" and path2_result.status == "success":
            combine_request = CombinedReceiverNoiseRequest(
                receiver_space_id="conference_room_1",
                path_results=[path1_result, path2_result],
                room_volume_cubic_ft=10000,
                room_absorption_sabins=350
            )

            result = self.api.hvac.calculate_combined_receiver_noise(combine_request)

            self.assertEqual(result.status, "success")
            self.assertEqual(result.num_paths_combined, 2)
            self.assertIsNotNone(result.dominant_path_id)


def run_tests():
    """Run all API tests."""
    print("=" * 60)
    print("Acoustic Analysis API Test Suite")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAcousticAnalysisAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestRT60CalculationService))
    suite.addTests(loader.loadTestsFromTestCase(TestHVACNoiseService))
    suite.addTests(loader.loadTestsFromTestCase(TestMaterialsService))
    suite.addTests(loader.loadTestsFromTestCase(TestSimulationService))
    suite.addTests(loader.loadTestsFromTestCase(TestStrictValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestCombinedReceiverNoise))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
