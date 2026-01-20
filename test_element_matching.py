"""
Comprehensive test suite for Element Matching Service and Coordinate Normalizer.

Tests the robustness, error isolation, and performance of the refactored element matching system.
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from drawing.coordinate_normalizer import (
    CoordinateNormalizer, NormalizedCoordinates, CoordinateTransform
)
from drawing.element_matching_service import (
    ElementMatchingService, MatchingStrategy, MatchingResult, MatchingContext,
    DatabaseIdMatcher, ElementIdMatcher, CoordinateBasedMatcher, HybridFuzzyMatcher
)


class TestCoordinateNormalizer(unittest.TestCase):
    """Test coordinate normalization functionality"""

    def setUp(self):
        self.normalizer = CoordinateNormalizer(tolerance=10.0)

    def test_basic_coordinate_normalization(self):
        """Test basic coordinate normalization"""
        element = {
            'x': 100.0,
            'y': 200.0,
            'width': 50.0,
            'height': 75.0,
            'saved_zoom': 2.0
        }

        result = self.normalizer.normalize_element_coordinates(element, target_zoom=1.0)

        self.assertTrue(result.is_valid)
        self.assertEqual(result.x, 50.0)  # 100 / 2
        self.assertEqual(result.y, 100.0)  # 200 / 2
        self.assertEqual(result.width, 25.0)  # 50 / 2
        self.assertEqual(result.height, 37.5)  # 75 / 2

    def test_coordinate_normalization_with_invalid_zoom(self):
        """Test normalization handles invalid zoom gracefully"""
        element = {
            'x': 100.0,
            'y': 200.0,
            'saved_zoom': 0  # Invalid zoom
        }

        result = self.normalizer.normalize_element_coordinates(element, target_zoom=1.0)

        self.assertTrue(result.is_valid)
        # Should use default zoom of 1.0
        self.assertEqual(result.x, 100.0)
        self.assertEqual(result.y, 200.0)

    def test_coordinate_matching_within_tolerance(self):
        """Test coordinate matching within tolerance"""
        coord1 = {'x': 100, 'y': 200, 'saved_zoom': 1.0}
        coord2 = {'x': 105, 'y': 198, 'saved_zoom': 1.0}

        self.assertTrue(self.normalizer.coordinates_match(coord1, coord2, tolerance=10.0))
        self.assertFalse(self.normalizer.coordinates_match(coord1, coord2, tolerance=2.0))

    def test_coordinate_matching_different_zooms(self):
        """Test coordinate matching with different zoom levels"""
        coord1 = {'x': 100, 'y': 200, 'saved_zoom': 1.0}
        coord2 = {'x': 200, 'y': 400, 'saved_zoom': 2.0}  # Same normalized coordinates

        self.assertTrue(self.normalizer.coordinates_match(coord1, coord2, tolerance=5.0))

    def test_invalid_element_structure(self):
        """Test handling of invalid element structure"""
        invalid_element = {'invalid': 'data'}

        result = self.normalizer.normalize_element_coordinates(invalid_element)

        self.assertFalse(result.is_valid)
        self.assertIn("Invalid element structure", result.error_message)

    def test_denormalize_coordinates(self):
        """Test coordinate denormalization"""
        normalized = NormalizedCoordinates(
            x=50.0, y=100.0, width=25.0, height=37.5,
            normalized_zoom=1.0, is_valid=True
        )

        result = self.normalizer.denormalize_coordinates(normalized, target_zoom=2.0)

        self.assertEqual(result['x'], 100.0)
        self.assertEqual(result['y'], 200.0)
        self.assertEqual(result['width'], 50.0)
        self.assertEqual(result['height'], 75.0)

    def test_cache_functionality(self):
        """Test coordinate caching functionality"""
        element = {'x': 100, 'y': 200, 'id': 'test_element', 'saved_zoom': 1.0}

        # First call should populate cache
        result1 = self.normalizer.normalize_element_coordinates(element, use_cache=True)
        cache_stats1 = self.normalizer.get_cache_stats()

        # Second call should use cache
        result2 = self.normalizer.normalize_element_coordinates(element, use_cache=True)
        cache_stats2 = self.normalizer.get_cache_stats()

        self.assertEqual(result1.x, result2.x)
        self.assertEqual(result1.y, result2.y)
        self.assertEqual(cache_stats1['coordinate_cache_size'], cache_stats2['coordinate_cache_size'])


class TestElementMatchingStrategies(unittest.TestCase):
    """Test individual matching strategies"""

    def setUp(self):
        self.normalizer = CoordinateNormalizer()
        self.sample_elements = [
            {
                'id': 'elem_1',
                'db_id': 'db_1',
                'type': 'component',
                'x': 100, 'y': 200,
                'component_type': 'ahu'
            },
            {
                'id': 'elem_2',
                'db_id': 'db_2',
                'type': 'segment',
                'x': 150, 'y': 250,
                'length': 50
            }
        ]

    def test_database_id_matcher_success(self):
        """Test successful database ID matching"""
        matcher = DatabaseIdMatcher(self.normalizer)
        context = MatchingContext(
            available_elements=self.sample_elements,
            element_indexes={'by_db_id': {'db_1': self.sample_elements[0]}}
        )

        target = {'db_id': 'db_1', 'x': 102, 'y': 198}  # Close coordinates
        result = matcher.match(target, context)

        self.assertTrue(result.success)
        self.assertEqual(result.matched_element['id'], 'elem_1')
        self.assertEqual(result.strategy_used, MatchingStrategy.DATABASE_ID)
        self.assertGreater(result.confidence, 0.8)

    def test_database_id_matcher_no_match(self):
        """Test database ID matcher with no matching ID"""
        matcher = DatabaseIdMatcher(self.normalizer)
        context = MatchingContext(
            available_elements=self.sample_elements,
            element_indexes={'by_db_id': {}}
        )

        target = {'db_id': 'nonexistent', 'x': 100, 'y': 200}
        result = matcher.match(target, context)

        self.assertFalse(result.success)
        self.assertIn("No element found", result.error_message)

    def test_element_id_matcher_success(self):
        """Test successful element ID matching"""
        matcher = ElementIdMatcher(self.normalizer)
        context = MatchingContext(
            available_elements=self.sample_elements,
            element_indexes={'by_element_id': {'elem_1': self.sample_elements[0]}}
        )

        target = {'id': 'elem_1', 'x': 100, 'y': 200}
        result = matcher.match(target, context)

        self.assertTrue(result.success)
        self.assertEqual(result.matched_element['id'], 'elem_1')
        self.assertEqual(result.strategy_used, MatchingStrategy.ELEMENT_ID)

    def test_coordinate_based_matcher_success(self):
        """Test successful coordinate-based matching"""
        matcher = CoordinateBasedMatcher(self.normalizer)
        context = MatchingContext(
            available_elements=self.sample_elements,
            element_indexes={},
            coordinate_tolerance=10.0
        )

        target = {'x': 105, 'y': 195}  # Close to elem_1
        result = matcher.match(target, context)

        self.assertTrue(result.success)
        self.assertEqual(result.matched_element['id'], 'elem_1')
        self.assertEqual(result.strategy_used, MatchingStrategy.COORDINATE_BASED)

    def test_coordinate_based_matcher_no_match(self):
        """Test coordinate-based matcher with no close matches"""
        matcher = CoordinateBasedMatcher(self.normalizer)
        context = MatchingContext(
            available_elements=self.sample_elements,
            element_indexes={},
            coordinate_tolerance=5.0
        )

        target = {'x': 500, 'y': 600}  # Far from any element
        result = matcher.match(target, context)

        self.assertFalse(result.success)
        self.assertIn("No coordinate-based match", result.error_message)

    def test_hybrid_fuzzy_matcher_success(self):
        """Test successful fuzzy matching"""
        matcher = HybridFuzzyMatcher(self.normalizer)
        context = MatchingContext(
            available_elements=self.sample_elements,
            element_indexes={},
            coordinate_tolerance=20.0
        )

        target = {
            'type': 'component',
            'x': 95, 'y': 205,  # Close coordinates
            'component_type': 'ahu'  # Matching type
        }
        result = matcher.match(target, context)

        self.assertTrue(result.success)
        self.assertEqual(result.matched_element['id'], 'elem_1')
        self.assertEqual(result.strategy_used, MatchingStrategy.HYBRID_FUZZY)

    def test_strategy_error_isolation(self):
        """Test that strategy errors don't propagate"""
        matcher = DatabaseIdMatcher(self.normalizer)

        # Create context that will cause internal errors
        invalid_context = MatchingContext(
            available_elements=[{'invalid': 'element'}],
            element_indexes={}
        )

        target = {'db_id': 'test'}
        result = matcher.match(target, invalid_context)

        # Should fail gracefully without raising exception
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)


class TestElementMatchingService(unittest.TestCase):
    """Test the main element matching service"""

    def setUp(self):
        self.service = ElementMatchingService()
        self.sample_elements = [
            {
                'id': 'elem_1',
                'db_id': 'db_1',
                'type': 'component',
                'x': 100, 'y': 200,
                'saved_zoom': 1.0
            },
            {
                'id': 'elem_2',
                'db_id': 'db_2',
                'type': 'segment',
                'x': 150, 'y': 250,
                'saved_zoom': 1.0
            }
        ]

    def test_successful_element_matching(self):
        """Test successful element matching with fallback"""
        target = {
            'db_id': 'db_1',
            'x': 100,
            'y': 200,
            'saved_zoom': 1.0
        }

        result = self.service.match_element(target, self.sample_elements)

        self.assertTrue(result.success)
        self.assertEqual(result.matched_element['id'], 'elem_1')
        self.assertIn('match_time_ms', result.debug_info)

    def test_fallback_strategy_usage(self):
        """Test that service falls back to other strategies"""
        target = {
            'db_id': 'nonexistent',  # Will fail database ID match
            'id': 'elem_2',          # Should succeed with element ID match
            'x': 150,
            'y': 250,
            'saved_zoom': 1.0
        }

        result = self.service.match_element(target, self.sample_elements)

        self.assertTrue(result.success)
        self.assertEqual(result.matched_element['id'], 'elem_2')
        self.assertEqual(result.strategy_used, MatchingStrategy.ELEMENT_ID)

    def test_batch_element_matching(self):
        """Test batch element matching"""
        targets = [
            {'db_id': 'db_1', 'x': 100, 'y': 200},
            {'db_id': 'db_2', 'x': 150, 'y': 250}
        ]

        results = self.service.batch_match_elements(targets, self.sample_elements)

        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.success for result in results))

    def test_no_match_found(self):
        """Test behavior when no match is found"""
        target = {
            'db_id': 'nonexistent',
            'id': 'nonexistent',
            'x': 999,
            'y': 999,
            'saved_zoom': 1.0
        }

        result = self.service.match_element(target, self.sample_elements)

        self.assertFalse(result.success)
        self.assertIn("All matching strategies failed", result.error_message)

    def test_statistics_tracking(self):
        """Test that service tracks statistics properly"""
        initial_stats = self.service.get_matching_statistics()

        # Perform some matches
        targets = [
            {'db_id': 'db_1', 'x': 100, 'y': 200},
            {'db_id': 'nonexistent', 'x': 999, 'y': 999}
        ]

        for target in targets:
            self.service.match_element(target, self.sample_elements)

        final_stats = self.service.get_matching_statistics()

        self.assertEqual(final_stats['total_matches'], initial_stats['total_matches'] + 2)
        self.assertEqual(final_stats['successful_matches'], initial_stats['successful_matches'] + 1)
        self.assertGreater(final_stats['strategy_usage']['database_id'], 0)

    def test_error_recovery(self):
        """Test service error recovery with malformed data"""
        malformed_elements = [
            {'completely': 'invalid'},
            None,
            {'partial': 'data', 'x': 'not_a_number'}
        ]

        target = {'db_id': 'test', 'x': 100, 'y': 200}

        # Should not raise exception
        result = self.service.match_element(target, malformed_elements)

        # Should fail gracefully
        self.assertFalse(result.success)


class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios that might occur in real usage"""

    def setUp(self):
        self.normalizer = CoordinateNormalizer()
        self.service = ElementMatchingService(self.normalizer)

    def test_complex_coordinate_scenario(self):
        """Test complex scenario with multiple zoom levels and coordinate transformations"""
        elements_at_different_zooms = [
            {'id': 'elem_1', 'x': 100, 'y': 200, 'saved_zoom': 1.0},
            {'id': 'elem_2', 'x': 300, 'y': 600, 'saved_zoom': 1.5},  # Same normalized coords as (200, 400)
            {'id': 'elem_3', 'x': 800, 'y': 1200, 'saved_zoom': 4.0}  # Same normalized coords as (200, 300)
        ]

        target = {'x': 200, 'y': 300, 'saved_zoom': 1.0}

        result = self.service.match_element(target, elements_at_different_zooms)

        self.assertTrue(result.success)
        self.assertEqual(result.matched_element['id'], 'elem_3')

    def test_performance_with_large_element_set(self):
        """Test performance with large number of elements"""
        large_element_set = []
        for i in range(1000):
            large_element_set.append({
                'id': f'elem_{i}',
                'db_id': f'db_{i}',
                'x': i * 10,
                'y': i * 20,
                'saved_zoom': 1.0
            })

        target = {'db_id': 'db_500', 'x': 5000, 'y': 10000, 'saved_zoom': 1.0}

        import time
        start_time = time.time()
        result = self.service.match_element(target, large_element_set)
        end_time = time.time()

        self.assertTrue(result.success)
        self.assertEqual(result.matched_element['id'], 'elem_500')
        self.assertLess(end_time - start_time, 1.0)  # Should complete in under 1 second

    def test_edge_case_coordinate_precision(self):
        """Test edge cases with coordinate precision"""
        elements = [
            {'id': 'elem_1', 'x': 100.0000001, 'y': 200.0000001, 'saved_zoom': 1.0}
        ]

        target = {'x': 100.0000002, 'y': 200.0000002, 'saved_zoom': 1.0}

        result = self.service.match_element(target, elements)

        self.assertTrue(result.success)  # Should match despite tiny differences


def run_element_matching_tests():
    """Run all element matching tests and return results"""
    print("🧪 Running Element Matching Service Tests...")
    print("=" * 50)

    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test cases
    test_classes = [
        TestCoordinateNormalizer,
        TestElementMatchingStrategies,
        TestElementMatchingService,
        TestIntegrationScenarios
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)

    # Print summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"❌ {test}: {traceback}")

    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"💥 {test}: {traceback}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ ALL TESTS PASSED' if success else '❌ SOME TESTS FAILED'}")

    return success


if __name__ == '__main__':
    success = run_element_matching_tests()
    sys.exit(0 if success else 1)