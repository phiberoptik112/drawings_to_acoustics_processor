"""
Enhanced Calculator Flow Tracer - Comprehensive validation and tracing for ALL calculation modules
Validates data in/out of every calculator and ensures correct calculator selection throughout the program flow
"""

import os
import time
import inspect
import functools
import traceback
import json
from typing import Dict, List, Tuple, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import numpy as np

from .debug_logger import debug_logger
from .hvac_constants import NUM_OCTAVE_BANDS, FREQUENCY_BAND_LABELS, MIN_NC_RATING, MAX_NC_RATING


class CalculatorType(Enum):
    """Enumeration of all calculator types in the system"""
    CIRCULAR_DUCT = "circular_duct"
    RECTANGULAR_DUCT = "rectangular_duct"
    FLEX_DUCT = "flex_duct"
    ELBOW_TURNING_VANE = "elbow_turning_vane"
    JUNCTION_ELBOW = "junction_elbow"
    RECTANGULAR_ELBOW = "rectangular_elbow"
    RECEIVER_ROOM_CORRECTION = "receiver_room_correction"
    END_REFLECTION = "end_reflection"
    RT60 = "rt60"
    ENHANCED_RT60 = "enhanced_rt60"
    NC_RATING = "nc_rating"
    TREATMENT_ANALYZER = "treatment_analyzer"
    SURFACE_AREA = "surface_area"
    HVAC_NOISE_ENGINE = "hvac_noise_engine"
    PATH_DATA_BUILDER = "path_data_builder"
    HVAC_PATH = "hvac_path"


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of input/output validation"""
    is_valid: bool
    severity: ValidationSeverity
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class CalculatorCall:
    """Detailed information about a calculator method call"""
    calculator_type: CalculatorType
    method_name: str
    start_time: float
    end_time: Optional[float] = None
    input_params: Dict[str, Any] = field(default_factory=dict)
    output_result: Any = None
    validation_results: List[ValidationResult] = field(default_factory=list)
    execution_time_ms: Optional[float] = None
    success: bool = True
    error: Optional[Exception] = None
    call_stack: List[str] = field(default_factory=list)


@dataclass
class CalculatorFlow:
    """Complete flow trace through multiple calculators"""
    flow_id: str
    start_time: float
    end_time: Optional[float] = None
    calculator_calls: List[CalculatorCall] = field(default_factory=list)
    decision_points: List[Dict[str, Any]] = field(default_factory=list)
    data_transformations: List[Dict[str, Any]] = field(default_factory=list)
    final_result: Any = None


class CalculatorRegistry:
    """Registry of all available calculators and their metadata"""

    def __init__(self):
        self.calculators: Dict[CalculatorType, Dict[str, Any]] = {}
        self.method_registry: Dict[str, CalculatorType] = {}
        self._register_all_calculators()

    def _register_all_calculators(self):
        """Register all calculator types with their expected methods and parameters"""

        # Circular Duct Calculator
        self.calculators[CalculatorType.CIRCULAR_DUCT] = {
            "class_name": "CircularDuctCalculator",
            "methods": {
                "get_unlined_attenuation": {
                    "required_params": ["diameter", "length"],
                    "optional_params": ["material", "thickness"],
                    "expected_output": "octave_band_spectrum",
                    "param_ranges": {"diameter": (1.0, 144.0), "length": (0.1, 1000.0)}
                },
                "get_1inch_lining_attenuation": {
                    "required_params": ["diameter", "length"],
                    "expected_output": "octave_band_spectrum",
                    "param_ranges": {"diameter": (6.0, 48.0), "length": (0.1, 1000.0)}
                },
                "get_2inch_lining_attenuation": {
                    "required_params": ["diameter", "length"],
                    "expected_output": "octave_band_spectrum",
                    "param_ranges": {"diameter": (6.0, 48.0), "length": (0.1, 1000.0)}
                }
            }
        }

        # Rectangular Duct Calculator
        self.calculators[CalculatorType.RECTANGULAR_DUCT] = {
            "class_name": "RectangularDuctCalculator",
            "methods": {
                "get_unlined_attenuation": {
                    "required_params": ["width", "height", "length"],
                    "expected_output": "octave_band_spectrum",
                    "param_ranges": {"width": (1.0, 144.0), "height": (1.0, 144.0), "length": (0.1, 1000.0)}
                },
                "get_1inch_lining_attenuation": {
                    "required_params": ["width", "height", "length"],
                    "expected_output": "octave_band_spectrum",
                    "param_ranges": {"width": (6.0, 48.0), "height": (6.0, 144.0), "length": (0.1, 1000.0)}
                },
                "get_2inch_lining_attenuation": {
                    "required_params": ["width", "height", "length"],
                    "expected_output": "octave_band_spectrum",
                    "param_ranges": {"width": (6.0, 48.0), "height": (6.0, 144.0), "length": (0.1, 1000.0)}
                }
            }
        }

        # Flex Duct Calculator
        self.calculators[CalculatorType.FLEX_DUCT] = {
            "class_name": "FlexDuctCalculator",
            "methods": {
                "calculate_attenuation": {
                    "required_params": ["diameter", "length"],
                    "expected_output": "octave_band_spectrum",
                    "param_ranges": {"diameter": (4.0, 24.0), "length": (1.0, 100.0)}
                }
            }
        }

        # Junction/Elbow Calculator
        self.calculators[CalculatorType.JUNCTION_ELBOW] = {
            "class_name": "JunctionElbowNoiseCalculator",
            "methods": {
                "calculate_junction_noise_spectrum": {
                    "required_params": ["junction_type", "main_area", "branch_area", "main_velocity", "branch_velocity"],
                    "expected_output": "generated_noise_spectrum",
                    "param_ranges": {
                        "main_area": (0.1, 100.0), "branch_area": (0.1, 100.0),
                        "main_velocity": (100.0, 6000.0), "branch_velocity": (100.0, 6000.0)
                    }
                }
            }
        }

        # Elbow Turning Vane Calculator
        self.calculators[CalculatorType.ELBOW_TURNING_VANE] = {
            "class_name": "ElbowTurningVaneCalculator",
            "methods": {
                "calculate_generated_noise": {
                    "required_params": ["width", "height", "velocity"],
                    "expected_output": "generated_noise_spectrum",
                    "param_ranges": {"width": (6.0, 72.0), "height": (6.0, 72.0), "velocity": (500.0, 4000.0)}
                }
            }
        }

        # RT60 Calculator
        self.calculators[CalculatorType.RT60] = {
            "class_name": "RT60Calculator",
            "methods": {
                "calculate_rt60": {
                    "required_params": ["room_volume", "surface_areas", "absorption_coefficients"],
                    "expected_output": "rt60_values",
                    "param_ranges": {"room_volume": (10.0, 1000000.0)}
                }
            }
        }

        # NC Rating Analyzer
        self.calculators[CalculatorType.NC_RATING] = {
            "class_name": "NCRatingAnalyzer",
            "methods": {
                "calculate_nc_rating": {
                    "required_params": ["octave_band_levels"],
                    "expected_output": "nc_rating",
                    "param_ranges": {}
                }
            }
        }

        # HVAC Noise Engine
        self.calculators[CalculatorType.HVAC_NOISE_ENGINE] = {
            "class_name": "HVACNoiseEngine",
            "methods": {
                "calculate_path_noise": {
                    "required_params": ["path_elements"],
                    "expected_output": "path_noise_analysis",
                    "param_ranges": {}
                },
                "process_element": {
                    "required_params": ["element", "input_spectrum"],
                    "expected_output": "element_result",
                    "param_ranges": {}
                }
            }
        }

        # Build reverse lookup for method to calculator mapping
        for calc_type, calc_info in self.calculators.items():
            for method_name in calc_info["methods"].keys():
                self.method_registry[method_name] = calc_type


class CalculatorValidator:
    """Validates calculator inputs and outputs"""

    def __init__(self, registry: CalculatorRegistry):
        self.registry = registry

    def validate_input_parameters(self, calculator_type: CalculatorType, method_name: str,
                                 params: Dict[str, Any]) -> List[ValidationResult]:
        """Validate input parameters for a calculator method"""
        results = []

        if calculator_type not in self.registry.calculators:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Unknown calculator type: {calculator_type}",
                details={"calculator_type": calculator_type.value}
            ))
            return results

        calc_info = self.registry.calculators[calculator_type]
        if method_name not in calc_info["methods"]:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Unknown method {method_name} for calculator {calculator_type.value}",
                details={"method_name": method_name, "calculator_type": calculator_type.value}
            ))
            return results

        method_info = calc_info["methods"][method_name]

        # Check required parameters
        required_params = method_info.get("required_params", [])
        for param in required_params:
            if param not in params:
                results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Missing required parameter: {param}",
                    details={"parameter": param, "method": method_name}
                ))
            elif params[param] is None:
                results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"Required parameter {param} is None",
                    details={"parameter": param, "value": None}
                ))

        # Check parameter ranges
        param_ranges = method_info.get("param_ranges", {})
        for param, (min_val, max_val) in param_ranges.items():
            if param in params and params[param] is not None:
                value = params[param]
                if isinstance(value, (int, float)):
                    if value < min_val or value > max_val:
                        results.append(ValidationResult(
                            is_valid=False,
                            severity=ValidationSeverity.WARNING,
                            message=f"Parameter {param} value {value} outside expected range [{min_val}, {max_val}]",
                            details={"parameter": param, "value": value, "range": [min_val, max_val]}
                        ))

        # Check for suspicious values
        for param, value in params.items():
            if isinstance(value, float):
                if np.isnan(value):
                    results.append(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"Parameter {param} is NaN",
                        details={"parameter": param, "value": "NaN"}
                    ))
                elif np.isinf(value):
                    results.append(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"Parameter {param} is infinite",
                        details={"parameter": param, "value": "Infinite"}
                    ))

        return results

    def validate_output_result(self, calculator_type: CalculatorType, method_name: str,
                              result: Any) -> List[ValidationResult]:
        """Validate output result from a calculator method"""
        validation_results = []

        if result is None:
            validation_results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message="Calculator returned None result",
                details={"result": None}
            ))
            return validation_results

        # Validate octave band spectra
        if isinstance(result, (list, tuple)) and len(result) == NUM_OCTAVE_BANDS:
            for i, value in enumerate(result):
                if isinstance(value, float):
                    if np.isnan(value):
                        validation_results.append(ValidationResult(
                            is_valid=False,
                            severity=ValidationSeverity.ERROR,
                            message=f"Octave band {i} ({FREQUENCY_BAND_LABELS[i]}) is NaN",
                            details={"band_index": i, "frequency": FREQUENCY_BAND_LABELS[i]}
                        ))
                    elif np.isinf(value):
                        validation_results.append(ValidationResult(
                            is_valid=False,
                            severity=ValidationSeverity.ERROR,
                            message=f"Octave band {i} ({FREQUENCY_BAND_LABELS[i]}) is infinite",
                            details={"band_index": i, "frequency": FREQUENCY_BAND_LABELS[i]}
                        ))
                    elif value < -100.0 or value > 200.0:
                        validation_results.append(ValidationResult(
                            is_valid=False,
                            severity=ValidationSeverity.WARNING,
                            message=f"Octave band {i} ({FREQUENCY_BAND_LABELS[i]}) value {value:.1f} seems unrealistic",
                            details={"band_index": i, "frequency": FREQUENCY_BAND_LABELS[i], "value": value}
                        ))

        # Validate dictionary results
        elif isinstance(result, dict):
            # Check for spectrum data in dictionary
            for key in ['spectrum', 'octave_bands', 'attenuation_spectrum', 'generated_spectrum']:
                if key in result:
                    spectrum = result[key]
                    if isinstance(spectrum, (list, tuple)) and len(spectrum) == NUM_OCTAVE_BANDS:
                        for i, value in enumerate(spectrum):
                            if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                                validation_results.append(ValidationResult(
                                    is_valid=False,
                                    severity=ValidationSeverity.ERROR,
                                    message=f"Dictionary key '{key}' band {i} has invalid value",
                                    details={"key": key, "band_index": i, "value": str(value)}
                                ))

            # Check NC rating values
            if 'nc_rating' in result:
                nc_rating = result['nc_rating']
                if isinstance(nc_rating, (int, float)):
                    if nc_rating < MIN_NC_RATING or nc_rating > MAX_NC_RATING:
                        validation_results.append(ValidationResult(
                            is_valid=False,
                            severity=ValidationSeverity.WARNING,
                            message=f"NC rating {nc_rating} outside typical range [{MIN_NC_RATING}, {MAX_NC_RATING}]",
                            details={"nc_rating": nc_rating, "expected_range": [MIN_NC_RATING, MAX_NC_RATING]}
                        ))

        return validation_results


class CalculatorFlowTracer:
    """Main calculator flow tracing system"""

    def __init__(self):
        self.registry = CalculatorRegistry()
        self.validator = CalculatorValidator(self.registry)
        self.active_flows: Dict[str, CalculatorFlow] = {}
        self.completed_flows: List[CalculatorFlow] = []
        self.call_history: List[CalculatorCall] = []
        self.calculator_usage_stats: Dict[CalculatorType, int] = defaultdict(int)

        # Enable/disable tracing based on environment
        env_val = str(os.environ.get("HVAC_CALC_TRACE", "")).strip().lower()
        self.tracing_enabled = env_val in {"1", "true", "yes", "on"}

        # Detailed tracing level
        trace_level = os.environ.get("HVAC_TRACE_LEVEL", "SUMMARY").upper()
        self.trace_level = trace_level  # SUMMARY, DETAILED, FULL

    def start_flow(self, flow_id: str) -> CalculatorFlow:
        """Start a new calculation flow trace"""
        if not self.tracing_enabled:
            return None

        flow = CalculatorFlow(
            flow_id=flow_id,
            start_time=time.time()
        )
        self.active_flows[flow_id] = flow

        if self.trace_level in ["DETAILED", "FULL"]:
            print(f"[CALC_FLOW_START] {flow_id} at {time.time():.3f}")

        return flow

    def end_flow(self, flow_id: str, final_result: Any = None):
        """End a calculation flow trace"""
        if not self.tracing_enabled or flow_id not in self.active_flows:
            return

        flow = self.active_flows[flow_id]
        flow.end_time = time.time()
        flow.final_result = final_result

        self.completed_flows.append(flow)
        del self.active_flows[flow_id]

        if self.trace_level in ["DETAILED", "FULL"]:
            duration = flow.end_time - flow.start_time
            print(f"[CALC_FLOW_END] {flow_id} completed in {duration*1000:.1f}ms with {len(flow.calculator_calls)} calculator calls")

        # Print flow summary
        self._print_flow_summary(flow)

    def log_decision_point(self, flow_id: str, decision_type: str, options: Dict[str, Any],
                          chosen: str, reasoning: str):
        """Log a calculator selection decision point"""
        if not self.tracing_enabled or flow_id not in self.active_flows:
            return

        decision = {
            "decision_type": decision_type,
            "options": options,
            "chosen": chosen,
            "reasoning": reasoning,
            "timestamp": time.time()
        }

        self.active_flows[flow_id].decision_points.append(decision)

        if self.trace_level == "FULL":
            print(f"[CALC_DECISION] {flow_id}: {decision_type} -> {chosen} ({reasoning})")

    def log_data_transformation(self, flow_id: str, transformation_type: str,
                               input_data: Any, output_data: Any, transformer: str):
        """Log data transformation between calculators"""
        if not self.tracing_enabled or flow_id not in self.active_flows:
            return

        transformation = {
            "transformation_type": transformation_type,
            "transformer": transformer,
            "input_summary": self._summarize_data(input_data),
            "output_summary": self._summarize_data(output_data),
            "timestamp": time.time()
        }

        self.active_flows[flow_id].data_transformations.append(transformation)

        if self.trace_level == "FULL":
            print(f"[CALC_TRANSFORM] {flow_id}: {transformation_type} by {transformer}")


def calculator_method_tracer(calculator_type: CalculatorType, expected_output_type: str = None):
    """Decorator to trace calculator method calls with validation"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get global tracer instance
            tracer = getattr(wrapper, '_tracer', None)
            if not tracer or not tracer.tracing_enabled:
                return func(*args, **kwargs)

            # Create calculator call record
            call = CalculatorCall(
                calculator_type=calculator_type,
                method_name=func.__name__,
                start_time=time.time(),
                call_stack=[frame.function for frame in inspect.stack()[:5]]
            )

            # Extract parameters (skip 'self' for instance methods)
            func_signature = inspect.signature(func)
            bound_args = func_signature.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Remove 'self' parameter for cleaner logging
            params = dict(bound_args.arguments)
            if 'self' in params:
                del params['self']
            call.input_params = params

            # Validate input parameters
            call.validation_results.extend(
                tracer.validator.validate_input_parameters(calculator_type, func.__name__, params)
            )

            # Log method entry
            if tracer.trace_level in ["DETAILED", "FULL"]:
                param_summary = tracer._summarize_data(params)
                print(f"[CALC_TRACE] {calculator_type.value}:{func.__name__} → ENTER {param_summary}")

            # Validate inputs before execution
            input_errors = [r for r in call.validation_results if r.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
            if input_errors and tracer.trace_level in ["DETAILED", "FULL"]:
                for error in input_errors:
                    print(f"[CALC_INPUT_ERROR] {calculator_type.value}:{func.__name__} → {error.message}")

            try:
                # Execute the actual calculation
                result = func(*args, **kwargs)
                call.output_result = result
                call.success = True

                # Validate output
                output_validations = tracer.validator.validate_output_result(calculator_type, func.__name__, result)
                call.validation_results.extend(output_validations)

                # Log successful completion
                if tracer.trace_level in ["DETAILED", "FULL"]:
                    result_summary = tracer._summarize_data(result)
                    print(f"[CALC_TRACE] {calculator_type.value}:{func.__name__} → SUCCESS {result_summary}")

                # Check for output validation issues
                output_errors = [r for r in output_validations if r.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
                if output_errors and tracer.trace_level in ["DETAILED", "FULL"]:
                    for error in output_errors:
                        print(f"[CALC_OUTPUT_ERROR] {calculator_type.value}:{func.__name__} → {error.message}")

            except Exception as e:
                call.error = e
                call.success = False
                call.validation_results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Calculator method failed with exception: {str(e)}",
                    details={"exception_type": type(e).__name__, "traceback": traceback.format_exc()}
                ))

                if tracer.trace_level in ["DETAILED", "FULL"]:
                    print(f"[CALC_ERROR] {calculator_type.value}:{func.__name__} → FAILED: {str(e)}")

                raise

            finally:
                # Complete the call record
                call.end_time = time.time()
                call.execution_time_ms = (call.end_time - call.start_time) * 1000

                # Update statistics
                tracer.calculator_usage_stats[calculator_type] += 1
                tracer.call_history.append(call)

                # Add to active flows if any
                for flow in tracer.active_flows.values():
                    flow.calculator_calls.append(call)

            return result

        return wrapper
    return decorator


# Global tracer instance
flow_tracer = CalculatorFlowTracer()


def _summarize_data(self, data: Any) -> str:
    """Create a concise summary of data for logging"""
    if data is None:
        return "None"
    elif isinstance(data, (list, tuple)):
        if len(data) == NUM_OCTAVE_BANDS and all(isinstance(x, (int, float)) for x in data):
            # Octave band spectrum
            avg_level = sum(data) / len(data)
            return f"spectrum[avg={avg_level:.1f}dB]"
        else:
            return f"list[{len(data)}]"
    elif isinstance(data, dict):
        keys = list(data.keys())[:3]  # Show first 3 keys
        return f"dict{{{', '.join(keys)}{'...' if len(data) > 3 else ''}}}"
    elif isinstance(data, (int, float)):
        return f"{data:.2f}"
    else:
        return str(type(data).__name__)


def _print_flow_summary(self, flow: CalculatorFlow):
    """Print a summary of the completed flow"""
    if self.trace_level == "SUMMARY":
        return

    print("\n" + "="*80)
    print(f"CALCULATOR FLOW SUMMARY: {flow.flow_id}")
    print("="*80)

    duration = (flow.end_time - flow.start_time) * 1000 if flow.end_time else 0
    print(f"Duration: {duration:.1f}ms")
    print(f"Calculator calls: {len(flow.calculator_calls)}")
    print(f"Decision points: {len(flow.decision_points)}")

    # Show calculator usage in this flow
    calc_usage = defaultdict(int)
    for call in flow.calculator_calls:
        calc_usage[call.calculator_type] += 1

    print("\nCalculator Usage:")
    for calc_type, count in calc_usage.items():
        print(f"  {calc_type.value}: {count} calls")

    # Show validation issues
    all_validations = []
    for call in flow.calculator_calls:
        all_validations.extend(call.validation_results)

    error_validations = [v for v in all_validations if v.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
    warning_validations = [v for v in all_validations if v.severity == ValidationSeverity.WARNING]

    if error_validations:
        print(f"\nValidation Errors: {len(error_validations)}")
        for validation in error_validations[:5]:  # Show first 5
            print(f"  ❌ {validation.message}")

    if warning_validations:
        print(f"\nValidation Warnings: {len(warning_validations)}")
        for validation in warning_validations[:3]:  # Show first 3
            print(f"  ⚠️ {validation.message}")

    # Show decision points
    if flow.decision_points:
        print("\nKey Decisions:")
        for decision in flow.decision_points:
            print(f"  {decision['decision_type']}: {decision['chosen']} ({decision['reasoning']})")

    print("="*80 + "\n")


# Monkey patch the methods to the CalculatorFlowTracer class
CalculatorFlowTracer._summarize_data = _summarize_data
CalculatorFlowTracer._print_flow_summary = _print_flow_summary


def enable_calculator_tracing():
    """Enable calculator method tracing globally"""
    flow_tracer.tracing_enabled = True
    os.environ["HVAC_CALC_TRACE"] = "1"


def disable_calculator_tracing():
    """Disable calculator method tracing globally"""
    flow_tracer.tracing_enabled = False
    os.environ.pop("HVAC_CALC_TRACE", None)


def get_calculator_usage_report() -> Dict[str, Any]:
    """Get a comprehensive report of calculator usage and validation results"""
    return {
        "total_calls": len(flow_tracer.call_history),
        "completed_flows": len(flow_tracer.completed_flows),
        "active_flows": len(flow_tracer.active_flows),
        "calculator_usage": dict(flow_tracer.calculator_usage_stats),
        "validation_summary": _get_validation_summary(),
        "performance_summary": _get_performance_summary()
    }


def _get_validation_summary() -> Dict[str, Any]:
    """Get summary of all validation results"""
    all_validations = []
    for call in flow_tracer.call_history:
        all_validations.extend(call.validation_results)

    severity_counts = defaultdict(int)
    for validation in all_validations:
        severity_counts[validation.severity.value] += 1

    return {
        "total_validations": len(all_validations),
        "by_severity": dict(severity_counts),
        "error_rate": severity_counts["error"] / max(len(all_validations), 1),
        "warning_rate": severity_counts["warning"] / max(len(all_validations), 1)
    }


def _get_performance_summary() -> Dict[str, Any]:
    """Get performance summary of calculator calls"""
    execution_times = [call.execution_time_ms for call in flow_tracer.call_history if call.execution_time_ms]

    if not execution_times:
        return {"message": "No performance data available"}

    return {
        "total_calls": len(execution_times),
        "avg_execution_time_ms": sum(execution_times) / len(execution_times),
        "max_execution_time_ms": max(execution_times),
        "min_execution_time_ms": min(execution_times),
        "slow_calls": len([t for t in execution_times if t > 100.0])  # Calls over 100ms
    }


# Export the decorator and tracer for use throughout the system
__all__ = [
    'calculator_method_tracer',
    'flow_tracer',
    'CalculatorType',
    'enable_calculator_tracing',
    'disable_calculator_tracing',
    'get_calculator_usage_report'
]