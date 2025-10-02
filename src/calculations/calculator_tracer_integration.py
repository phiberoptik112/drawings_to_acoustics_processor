"""
Calculator Tracer Integration - Automatically applies flow tracing to all calculator modules
This script instruments existing calculator classes with tracing decorators
"""

import sys
import os
import importlib
import inspect
import time
from typing import Dict, List, Type, Any

# Import the flow tracer components
from .calculator_flow_tracer import (
    calculator_method_tracer,
    flow_tracer,
    CalculatorType,
    enable_calculator_tracing,
    disable_calculator_tracing
)


class CalculatorTracerIntegration:
    """Handles automatic integration of calculator tracing with existing modules"""

    def __init__(self):
        self.instrumented_classes: Dict[str, Type] = {}
        self.calculator_mappings = self._get_calculator_mappings()

    def _get_calculator_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Define mappings between calculator classes and their tracing configuration"""
        return {
            # Circular Duct Calculator
            "CircularDuctCalculator": {
                "module": "circular_duct_calculations",
                "calculator_type": CalculatorType.CIRCULAR_DUCT,
                "methods_to_trace": [
                    "calculate_unlined_attenuation",
                    "calculate_lined_insertion_loss",
                    "get_unlined_attenuation_spectrum",
                    "get_lined_insertion_loss_spectrum"
                ]
            },

            # Rectangular Duct Calculator
            "RectangularDuctCalculator": {
                "module": "rectangular_duct_calculations",
                "calculator_type": CalculatorType.RECTANGULAR_DUCT,
                "methods_to_trace": [
                    "get_unlined_attenuation",
                    "get_1inch_lining_attenuation",
                    "get_2inch_lining_attenuation",
                    "calculate_attenuation"
                ]
            },

            # Flex Duct Calculator
            "FlexDuctCalculator": {
                "module": "flex_duct_calculations",
                "calculator_type": CalculatorType.FLEX_DUCT,
                "methods_to_trace": [
                    "get_insertion_loss",
                    "calculate_average_insertion_loss"
                ]
            },

            # Junction/Elbow Noise Calculator
            "JunctionElbowNoiseCalculator": {
                "module": "junction_elbow_generated_noise_calculations",
                "calculator_type": CalculatorType.JUNCTION_ELBOW,
                "methods_to_trace": [
                    "calculate_junction_noise_spectrum",
                    "calculate_noise_for_junction_type",
                    "calculate_branch_takeoff_noise",
                    "calculate_converging_flow_noise",
                    "calculate_diverging_flow_noise"
                ]
            },

            # Elbow Turning Vane Calculator
            "ElbowTurningVaneCalculator": {
                "module": "elbow_turning_vane_generated_noise_calculations",
                "calculator_type": CalculatorType.ELBOW_TURNING_VANE,
                "methods_to_trace": [
                    "calculate_complete_spectrum",
                    "calculate_sound_power_level",
                    "calculate_constriction_velocity"
                ]
            },

            # Rectangular Elbows Calculator
            "RectangularElbowsCalculator": {
                "module": "rectangular_elbows_calculations",
                "calculator_type": CalculatorType.RECTANGULAR_ELBOW,
                "methods_to_trace": [
                    "calculate_elbow_insertion_loss",
                    "get_table_22_insertion_loss",
                    "get_table_23_insertion_loss",
                    "get_table_24_insertion_loss"
                ]
            },

            # Receiver Room Sound Correction
            "ReceiverRoomSoundCorrection": {
                "module": "receiver_room_sound_correction_calculations",
                "calculator_type": CalculatorType.RECEIVER_ROOM_CORRECTION,
                "methods_to_trace": [
                    "calculate_receiver_room_correction",
                    "get_room_correction_factors"
                ]
            },

            # RT60 Calculator
            "RT60Calculator": {
                "module": "rt60_calculator",
                "calculator_type": CalculatorType.RT60,
                "methods_to_trace": [
                    "calculate_space_rt60",
                    "calculate_rt60_sabine",
                    "calculate_rt60_eyring",
                    "calculate_total_absorption"
                ]
            },

            # Enhanced RT60 Calculator
            "EnhancedRT60Calculator": {
                "module": "enhanced_rt60_calculator",
                "calculator_type": CalculatorType.ENHANCED_RT60,
                "methods_to_trace": [
                    "calculate_frequency_dependent_rt60",
                    "calculate_comprehensive_rt60",
                    "calculate_advanced_absorption"
                ]
            },

            # NC Rating Analyzer
            "NCRatingAnalyzer": {
                "module": "nc_rating_analyzer",
                "calculator_type": CalculatorType.NC_RATING,
                "methods_to_trace": [
                    "analyze_noise_levels",
                    "determine_nc_rating",
                    "calculate_compliance"
                ]
            },

            # Treatment Analyzer
            "TreatmentAnalyzer": {
                "module": "treatment_analyzer",
                "calculator_type": CalculatorType.TREATMENT_ANALYZER,
                "methods_to_trace": [
                    "analyze_acoustic_treatment",
                    "calculate_material_effectiveness",
                    "suggest_treatment_options"
                ]
            },

            # Surface Area Calculator
            "SurfaceAreaCalculator": {
                "module": "surface_area_calculator",
                "calculator_type": CalculatorType.SURFACE_AREA,
                "methods_to_trace": [
                    "calculate_total_surface_area",
                    "calculate_room_geometry",
                    "calculate_wall_areas"
                ]
            },

            # HVAC Noise Engine
            "HVACNoiseEngine": {
                "module": "hvac_noise_engine",
                "calculator_type": CalculatorType.HVAC_NOISE_ENGINE,
                "methods_to_trace": [
                    "calculate_path_noise",
                    "_calculate_element_effect",
                    "_calculate_duct_effect",
                    "_calculate_junction_effect",
                    "_calculate_terminal_effect",
                    "_estimate_spectrum_from_dba"
                ]
            },

            # Path Data Builder
            "SourceComponentBuilder": {
                "module": "path_data_builder",
                "calculator_type": CalculatorType.PATH_DATA_BUILDER,
                "methods_to_trace": [
                    "build_source_from_component",
                    "build_mechanical_unit_data"
                ]
            }
        }

    def instrument_all_calculators(self) -> Dict[str, bool]:
        """Instrument all calculator classes with tracing decorators"""
        results = {}

        for class_name, config in self.calculator_mappings.items():
            try:
                success = self._instrument_calculator_class(class_name, config)
                results[class_name] = success
                if success:
                    print(f"✅ Successfully instrumented {class_name}")
                else:
                    print(f"❌ Failed to instrument {class_name}")
            except Exception as e:
                print(f"❌ Error instrumenting {class_name}: {str(e)}")
                results[class_name] = False

        return results

    def _instrument_calculator_class(self, class_name: str, config: Dict[str, Any]) -> bool:
        """Instrument a specific calculator class with tracing"""
        try:
            # Import the module
            module_name = f"calculations.{config['module']}"

            # Handle relative imports when this is run from within the calculations package
            if module_name.startswith("calculations."):
                module_name = "." + config['module']

            try:
                module = importlib.import_module(module_name, package="calculations")
            except ImportError:
                # Fallback to absolute import
                module_name = f"src.calculations.{config['module']}"
                module = importlib.import_module(module_name)

            # Get the calculator class
            if not hasattr(module, class_name):
                print(f"⚠️ Class {class_name} not found in module {config['module']}")
                return False

            calc_class = getattr(module, class_name)

            # Instrument the specified methods
            calculator_type = config['calculator_type']
            methods_to_trace = config['methods_to_trace']

            instrumented_methods = []
            for method_name in methods_to_trace:
                if hasattr(calc_class, method_name):
                    original_method = getattr(calc_class, method_name)

                    # Only instrument if not already instrumented
                    if not hasattr(original_method, '_is_traced'):
                        # Apply the tracing decorator
                        traced_method = calculator_method_tracer(calculator_type)(original_method)
                        traced_method._is_traced = True
                        traced_method._tracer = flow_tracer

                        # Replace the method on the class
                        setattr(calc_class, method_name, traced_method)
                        instrumented_methods.append(method_name)

            if instrumented_methods:
                self.instrumented_classes[class_name] = calc_class
                print(f"  📊 Instrumented methods: {', '.join(instrumented_methods)}")
                return True
            else:
                print(f"  ⚠️ No methods found to instrument in {class_name}")
                return False

        except Exception as e:
            print(f"  ❌ Error instrumenting {class_name}: {str(e)}")
            return False

    def instrument_hvac_noise_engine_specifically(self):
        """Special instrumentation for HVACNoiseEngine with enhanced tracing"""
        try:
            from .hvac_noise_engine import HVACNoiseEngine

            # Store original methods for enhanced logging
            original_calculate_path_noise = HVACNoiseEngine.calculate_path_noise
            original_calculate_element_effect = HVACNoiseEngine._calculate_element_effect

            def enhanced_calculate_path_noise(self, path_elements, source_spectrum=None, **kwargs):
                """Enhanced version with flow tracing"""
                # Start a calculation flow
                flow_id = f"path_noise_{id(path_elements)}_{int(time.time() * 1000) % 10000}"
                flow_tracer.start_flow(flow_id)

                try:
                    # Log the path elements being processed
                    flow_tracer.log_decision_point(
                        flow_id,
                        "path_processing",
                        {"num_elements": len(path_elements), "has_source_spectrum": source_spectrum is not None},
                        "process_path",
                        f"Processing {len(path_elements)} path elements"
                    )

                    # Call original method
                    result = original_calculate_path_noise(self, path_elements, source_spectrum, **kwargs)

                    # End the flow
                    flow_tracer.end_flow(flow_id, result)
                    return result

                except Exception as e:
                    flow_tracer.end_flow(flow_id, None)
                    raise

            def enhanced_calculate_element_effect(self, element, **kwargs):
                """Enhanced element processing with detailed logging"""
                element_type = getattr(element, 'element_type', 'unknown')
                element_id = getattr(element, 'element_id', 'unknown')

                # Log calculator selection decision
                for flow in flow_tracer.active_flows.values():
                    calculator_options = {
                        "element_type": element_type,
                        "available_calculators": self._get_available_calculators_for_element(element)
                    }

                    chosen_calculator = self._determine_calculator_for_element(element)

                    flow_tracer.log_decision_point(
                        flow.flow_id,
                        "calculator_selection",
                        calculator_options,
                        chosen_calculator,
                        f"Selected {chosen_calculator} for {element_type}"
                    )

                    # Log data transformation
                    flow_tracer.log_data_transformation(
                        flow.flow_id,
                        "element_processing",
                        {"element": element_type, "element_id": element_id},
                        None,  # Will be filled after processing
                        f"{element_type}_processor"
                    )

                # Call original method
                result = original_calculate_element_effect(self, element, **kwargs)

                # Log the result transformation
                for flow in flow_tracer.active_flows.values():
                    flow_tracer.log_data_transformation(
                        flow.flow_id,
                        "element_result",
                        {"element": element_type, "element_id": element_id},
                        result,
                        f"{element_type}_processor"
                    )

                return result

            # Helper methods for the enhanced tracing
            def _get_available_calculators_for_element(self, element):
                """Get list of available calculators for an element type"""
                element_type = getattr(element, 'element_type', 'unknown')
                calculator_map = {
                    'duct': ['circular_duct', 'rectangular_duct'],
                    'flex_duct': ['flex_duct'],
                    'elbow': ['rectangular_elbow', 'elbow_turning_vane'],
                    'junction': ['junction_elbow'],
                    'terminal': ['receiver_room_correction']
                }
                return calculator_map.get(element_type, ['unknown'])

            def _determine_calculator_for_element(self, element):
                """Determine which calculator will be used for an element"""
                element_type = getattr(element, 'element_type', 'unknown')
                if element_type == 'duct':
                    # Logic to determine circular vs rectangular
                    if hasattr(element, 'diameter') and element.diameter:
                        return 'circular_duct'
                    else:
                        return 'rectangular_duct'
                elif element_type == 'junction':
                    return 'junction_elbow'
                elif element_type == 'flex_duct':
                    return 'flex_duct'
                else:
                    return element_type

            # Apply enhanced methods
            HVACNoiseEngine.calculate_path_noise = enhanced_calculate_path_noise
            HVACNoiseEngine._calculate_element_effect = enhanced_calculate_element_effect
            HVACNoiseEngine._get_available_calculators_for_element = _get_available_calculators_for_element
            HVACNoiseEngine._determine_calculator_for_element = _determine_calculator_for_element

            print("✅ Enhanced instrumentation applied to HVACNoiseEngine")
            return True

        except Exception as e:
            print(f"❌ Failed to apply enhanced instrumentation to HVACNoiseEngine: {str(e)}")
            return False

    def create_test_scenario(self) -> str:
        """Create a test scenario to validate the tracing system"""
        test_code = '''
# Test Calculator Flow Tracing
import os
from calculations.calculator_tracer_integration import CalculatorTracerIntegration
from calculations.calculator_flow_tracer import enable_calculator_tracing, get_calculator_usage_report

# Enable tracing
enable_calculator_tracing()
os.environ["HVAC_TRACE_LEVEL"] = "DETAILED"

# Initialize integration
integration = CalculatorTracerIntegration()
results = integration.instrument_all_calculators()
integration.instrument_hvac_noise_engine_specifically()

print("\\n=== INSTRUMENTATION RESULTS ===")
for class_name, success in results.items():
    status = "✅" if success else "❌"
    print(f"{status} {class_name}")

# Test with some sample calculations
try:
    from calculations.rectangular_duct_calculations import RectangularDuctCalculator

    calc = RectangularDuctCalculator()
    result = calc.get_2inch_lining_attenuation(width=24, height=12, length=10.5)

    print("\\n=== SAMPLE CALCULATION COMPLETED ===")
    print(f"Result: {result}")

except Exception as e:
    print(f"Sample calculation failed: {e}")

# Get usage report
report = get_calculator_usage_report()
print("\\n=== CALCULATOR USAGE REPORT ===")
for key, value in report.items():
    print(f"{key}: {value}")
'''

        return test_code

    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of calculator integration"""
        return {
            "total_calculators": len(self.calculator_mappings),
            "instrumented_calculators": len(self.instrumented_classes),
            "instrumented_classes": list(self.instrumented_classes.keys()),
            "tracing_enabled": flow_tracer.tracing_enabled,
            "trace_level": flow_tracer.trace_level
        }


# Global integration instance
tracer_integration = CalculatorTracerIntegration()


def quick_setup_calculator_tracing():
    """Quick setup function to enable tracing on all calculators"""
    print("🚀 Setting up comprehensive calculator tracing...")

    # Enable tracing
    enable_calculator_tracing()
    os.environ["HVAC_TRACE_LEVEL"] = "DETAILED"

    # Instrument all calculators
    results = tracer_integration.instrument_all_calculators()

    # Apply enhanced instrumentation to key classes
    tracer_integration.instrument_hvac_noise_engine_specifically()

    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)

    print(f"✅ Calculator tracing setup complete!")
    print(f"📊 Instrumented {success_count}/{total_count} calculator classes")
    print(f"🔍 Trace level: {os.environ.get('HVAC_TRACE_LEVEL', 'SUMMARY')}")
    print(f"🎯 Use environment variable HVAC_CALC_TRACE=1 to enable tracing")
    print(f"🎯 Use environment variable HVAC_TRACE_LEVEL=FULL for maximum detail")

    return results


if __name__ == "__main__":
    # Run integration when this module is executed directly
    quick_setup_calculator_tracing()