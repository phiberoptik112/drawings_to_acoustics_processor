"""
Demonstration of Enhanced Calculator Flow Tracer
Shows how to use the comprehensive calculator validation and tracing system
"""

import os
import sys
from typing import List, Dict, Any

# Set up environment for tracing
os.environ["HVAC_CALC_TRACE"] = "1"
os.environ["HVAC_TRACE_LEVEL"] = "DETAILED"
os.environ["HVAC_DEBUG_EXPORT"] = "1"

def demo_basic_calculator_tracing():
    """Demonstrate basic calculator tracing functionality"""
    print("🔍 DEMO: Basic Calculator Tracing")
    print("="*60)

    try:
        # Import and setup the tracing system
        from .calculator_tracer_integration import quick_setup_calculator_tracing
        from .calculator_flow_tracer import flow_tracer, get_calculator_usage_report

        # Setup tracing
        setup_results = quick_setup_calculator_tracing()

        # Test rectangular duct calculator
        print("\n📊 Testing Rectangular Duct Calculator...")
        from .rectangular_duct_calculations import RectangularDuctCalculator

        calc = RectangularDuctCalculator()

        # This call should be traced
        result = calc.get_2inch_lining_attenuation(width=24, height=12, length=10.5)
        print(f"Result: {[f'{x:.1f}' for x in result]}")

        # Test with invalid parameters to see validation
        print("\n⚠️ Testing with invalid parameters...")
        try:
            bad_result = calc.get_2inch_lining_attenuation(width=-5, height=0, length=10.5)
        except Exception as e:
            print(f"Expected error with invalid parameters: {e}")

        # Get usage report
        report = get_calculator_usage_report()
        print(f"\n📈 Calculator Usage Report:")
        print(f"Total calls: {report['total_calls']}")
        print(f"Calculator usage: {report['calculator_usage']}")

        return True

    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def demo_flow_tracing():
    """Demonstrate flow-level tracing through multiple calculators"""
    print("\n🔄 DEMO: Flow-Level Tracing")
    print("="*60)

    try:
        from .calculator_flow_tracer import flow_tracer
        from .hvac_noise_engine import HVACNoiseEngine, PathElement

        # Start a calculation flow
        flow_id = "demo_hvac_calculation"
        flow_tracer.start_flow(flow_id)

        # Log a decision point
        flow_tracer.log_decision_point(
            flow_id,
            "duct_type_selection",
            {"options": ["circular", "rectangular"], "criteria": "geometry"},
            "rectangular",
            "Rectangular duct selected based on width/height parameters"
        )

        # Create sample path elements
        elements = [
            PathElement(
                element_type="source",
                element_id="AHU-1",
                flow_rate=1000.0,
                source_noise_level=65.0
            ),
            PathElement(
                element_type="duct",
                element_id="duct-1",
                length=25.0,
                width=24.0,
                height=12.0,
                lining="2inch"
            ),
            PathElement(
                element_type="junction",
                element_id="junction-1",
                width=24.0,
                height=12.0,
                branch_width=12.0,
                branch_height=8.0,
                flow_rate=600.0
            ),
            PathElement(
                element_type="terminal",
                element_id="diffuser-1",
                flow_rate=600.0
            )
        ]

        # Process through noise engine (this should trigger multiple calculator calls)
        engine = HVACNoiseEngine()
        result = engine.calculate_path_noise(elements)

        # End the flow
        flow_tracer.end_flow(flow_id, result)

        print(f"✅ Flow completed with result: {result}")
        return True

    except Exception as e:
        print(f"❌ Flow demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def demo_validation_system():
    """Demonstrate the validation system with various edge cases"""
    print("\n✅ DEMO: Validation System")
    print("="*60)

    try:
        from .calculator_flow_tracer import CalculatorValidator, CalculatorRegistry, CalculatorType

        registry = CalculatorRegistry()
        validator = CalculatorValidator(registry)

        # Test valid parameters
        print("Testing valid parameters...")
        valid_params = {"width": 24.0, "height": 12.0, "length": 10.5}
        results = validator.validate_input_parameters(
            CalculatorType.RECTANGULAR_DUCT,
            "get_2inch_lining_attenuation",
            valid_params
        )
        print(f"Valid parameters validation: {len([r for r in results if not r.is_valid])} errors")

        # Test invalid parameters
        print("\nTesting invalid parameters...")
        invalid_params = {"width": -5.0, "height": 0.0, "length": 10000.0}
        results = validator.validate_input_parameters(
            CalculatorType.RECTANGULAR_DUCT,
            "get_2inch_lining_attenuation",
            invalid_params
        )
        print(f"Invalid parameters validation: {len([r for r in results if not r.is_valid])} errors")
        for result in results[:3]:  # Show first 3 errors
            if not result.is_valid:
                print(f"  ❌ {result.message}")

        # Test output validation
        print("\nTesting output validation...")
        # Valid spectrum
        valid_spectrum = [2.4, 4.2, 5.8, 6.1, 4.5, 3.2, 1.8, 0.9]
        results = validator.validate_output_result(
            CalculatorType.RECTANGULAR_DUCT,
            "get_2inch_lining_attenuation",
            valid_spectrum
        )
        print(f"Valid spectrum validation: {len([r for r in results if not r.is_valid])} errors")

        # Invalid spectrum with NaN
        import numpy as np
        invalid_spectrum = [2.4, 4.2, np.nan, 6.1, float('inf'), 3.2, 1.8, 0.9]
        results = validator.validate_output_result(
            CalculatorType.RECTANGULAR_DUCT,
            "get_2inch_lining_attenuation",
            invalid_spectrum
        )
        print(f"Invalid spectrum validation: {len([r for r in results if not r.is_valid])} errors")
        for result in results[:2]:  # Show first 2 errors
            if not result.is_valid:
                print(f"  ❌ {result.message}")

        return True

    except Exception as e:
        print(f"❌ Validation demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def demo_calculator_selection_tracing():
    """Demonstrate calculator selection decision tracing"""
    print("\n🎯 DEMO: Calculator Selection Tracing")
    print("="*60)

    try:
        from .calculator_flow_tracer import flow_tracer

        # Start a flow for calculator selection demo
        flow_id = "calculator_selection_demo"
        flow_tracer.start_flow(flow_id)

        # Simulate different calculator selection scenarios
        scenarios = [
            {
                "element_type": "duct",
                "geometry": {"diameter": 18.0},
                "expected_calculator": "circular_duct",
                "reasoning": "Circular geometry detected"
            },
            {
                "element_type": "duct",
                "geometry": {"width": 24.0, "height": 12.0},
                "expected_calculator": "rectangular_duct",
                "reasoning": "Rectangular geometry detected"
            },
            {
                "element_type": "duct",
                "geometry": {"diameter": 12.0, "is_flexible": True},
                "expected_calculator": "flex_duct",
                "reasoning": "Flexible duct material detected"
            },
            {
                "element_type": "junction",
                "geometry": {"junction_type": "branch_takeoff_90"},
                "expected_calculator": "junction_elbow",
                "reasoning": "Junction element requires specialized noise calculation"
            }
        ]

        for i, scenario in enumerate(scenarios):
            print(f"\nScenario {i+1}: {scenario['element_type']} element")

            # Log the calculator selection decision
            flow_tracer.log_decision_point(
                flow_id,
                "calculator_selection",
                {
                    "element_type": scenario["element_type"],
                    "geometry": scenario["geometry"],
                    "available_calculators": ["circular_duct", "rectangular_duct", "flex_duct", "junction_elbow"]
                },
                scenario["expected_calculator"],
                scenario["reasoning"]
            )

            # Log data transformation for this calculator
            flow_tracer.log_data_transformation(
                flow_id,
                "geometry_to_parameters",
                scenario["geometry"],
                {"calculator": scenario["expected_calculator"], "validated": True},
                "geometry_analyzer"
            )

            print(f"  ✅ Selected {scenario['expected_calculator']}: {scenario['reasoning']}")

        # End the flow
        flow_tracer.end_flow(flow_id, {"scenarios_processed": len(scenarios)})

        print(f"\n✅ Calculator selection demo completed")
        return True

    except Exception as e:
        print(f"❌ Calculator selection demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def demo_performance_monitoring():
    """Demonstrate performance monitoring capabilities"""
    print("\n⚡ DEMO: Performance Monitoring")
    print("="*60)

    try:
        from .calculator_flow_tracer import get_calculator_usage_report
        from .rectangular_duct_calculations import RectangularDuctCalculator
        import time

        # Perform multiple calculations to generate performance data
        calc = RectangularDuctCalculator()

        print("Performing calculations for performance analysis...")

        # Fast calculations
        for i in range(5):
            result = calc.get_2inch_lining_attenuation(width=24, height=12, length=10.0)

        # Simulate slower calculation
        print("Simulating slower calculation...")
        time.sleep(0.1)  # Add artificial delay
        result = calc.get_2inch_lining_attenuation(width=48, height=24, length=100.0)

        # Get performance report
        report = get_calculator_usage_report()
        performance = report.get("performance_summary", {})

        print(f"\n📊 Performance Summary:")
        print(f"Total calls: {performance.get('total_calls', 0)}")
        print(f"Average execution time: {performance.get('avg_execution_time_ms', 0):.2f}ms")
        print(f"Max execution time: {performance.get('max_execution_time_ms', 0):.2f}ms")
        print(f"Min execution time: {performance.get('min_execution_time_ms', 0):.2f}ms")
        print(f"Slow calls (>100ms): {performance.get('slow_calls', 0)}")

        validation_summary = report.get("validation_summary", {})
        print(f"\n🔍 Validation Summary:")
        print(f"Total validations: {validation_summary.get('total_validations', 0)}")
        print(f"Error rate: {validation_summary.get('error_rate', 0):.2%}")
        print(f"Warning rate: {validation_summary.get('warning_rate', 0):.2%}")

        return True

    except Exception as e:
        print(f"❌ Performance monitoring demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_comprehensive_demo():
    """Run all demonstration scenarios"""
    print("🚀 COMPREHENSIVE CALCULATOR FLOW TRACER DEMONSTRATION")
    print("="*80)

    demos = [
        ("Basic Calculator Tracing", demo_basic_calculator_tracing),
        ("Flow-Level Tracing", demo_flow_tracing),
        ("Validation System", demo_validation_system),
        ("Calculator Selection Tracing", demo_calculator_selection_tracing),
        ("Performance Monitoring", demo_performance_monitoring)
    ]

    results = {}
    for demo_name, demo_func in demos:
        print(f"\n🎯 Running: {demo_name}")
        try:
            success = demo_func()
            results[demo_name] = success
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n{status}: {demo_name}")
        except Exception as e:
            print(f"\n❌ FAILED: {demo_name} - {str(e)}")
            results[demo_name] = False

    # Summary
    print("\n" + "="*80)
    print("📊 DEMONSTRATION SUMMARY")
    print("="*80)

    passed = sum(1 for success in results.values() if success)
    total = len(results)

    for demo_name, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {demo_name}")

    print(f"\n🎯 Overall: {passed}/{total} demonstrations passed")

    if passed == total:
        print("🎉 All demonstrations passed! The enhanced calculator flow tracer is working correctly.")
    else:
        print("⚠️ Some demonstrations failed. Check the error messages above for details.")

    return results


if __name__ == "__main__":
    run_comprehensive_demo()